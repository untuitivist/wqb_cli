from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from types import MappingProxyType
from typing import Mapping


TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<string>'(?:\\.|[^'\\])*')|"
    r"(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|"
    r"(?P<identifier>[A-Za-z_][A-Za-z0-9_.]*)|(?P<punct>[(),=+\-*/<>])"
)

MAX_EXPRESSION_CHARS = 20_000
MAX_TOKENS = 2_048
MAX_NESTING = 32
MAX_NUMBER_CHARS = 256
MAX_NUMBER_EXPONENT = 1_024
MAX_OPERATOR_CALLS = 5
MAX_FIELDS = 2
MAX_CANDIDATE_DEPTH = 64
MAX_CANDIDATE_NODES = 10_000


class ExpressionViolation(ValueError):
    """Raised when a FASTEXPR candidate is syntactically or semantically unsafe."""


@dataclass(frozen=True)
class ValidatedCandidate:
    canonical_expression: str
    fingerprint: str
    fields: tuple[str, ...]
    operators: tuple[str, ...]
    original_candidate: Mapping[str, object]


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    offset: int


@dataclass(frozen=True)
class _Identifier:
    name: str


@dataclass(frozen=True)
class _Literal:
    kind: str
    text: str


@dataclass(frozen=True)
class _Unary:
    operator: str
    value: _Expression


@dataclass(frozen=True)
class _Binary:
    operator: str
    left: _Expression
    right: _Expression


@dataclass(frozen=True)
class _Call:
    name: str
    positional: tuple[_Expression, ...]
    named: tuple[tuple[str, _Expression], ...]


_Expression = _Identifier | _Literal | _Unary | _Binary | _Call

_BINARY_PRECEDENCE = {"=": 1, "<": 2, ">": 2, "+": 3, "-": 3, "*": 4, "/": 4}
_REQUIRED_NAMED_PARAMETERS = {
    "kth_element": ("k",),
    "ts_weighted_decay": ("k",),
    "hump_decay": ("p",),
    "group_mean": ("weight",),
    "ts_target_tvr_decay": ("lambda_min", "lambda_max", "target_tvr"),
    "ts_target_tvr_hump": ("lambda_min", "lambda_max", "target_tvr"),
    "ts_poly_regression": ("k",),
}
_ALLOWED_NAMED_PARAMETERS = {
    "kth_element": frozenset({"k"}),
    "ts_weighted_decay": frozenset({"k"}),
    "hump_decay": frozenset({"p"}),
    "group_mean": frozenset({"weight"}),
    "ts_target_tvr_decay": frozenset({"lambda_min", "lambda_max", "target_tvr"}),
    "ts_target_tvr_hump": frozenset({"lambda_min", "lambda_max", "target_tvr"}),
    "ts_poly_regression": frozenset({"k"}),
    "ts_quantile": frozenset({"driver"}),
}


def _normalized_number(text: str) -> str:
    if len(text) > MAX_NUMBER_CHARS:
        raise ExpressionViolation("numeric literal exceeds length limit")
    exponent_marker = max(text.rfind("e"), text.rfind("E"))
    if exponent_marker >= 0:
        exponent_text = text[exponent_marker + 1 :]
        signless = exponent_text.lstrip("+-")
        if len(signless) > 4:
            raise ExpressionViolation("numeric literal exponent exceeds limit")
        try:
            if abs(int(exponent_text)) > MAX_NUMBER_EXPONENT:
                raise ExpressionViolation("numeric literal exponent exceeds limit")
        except ValueError:
            raise ExpressionViolation("invalid numeric literal") from None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        raise ExpressionViolation("invalid numeric literal") from None
    if not value.is_finite() or abs(value.adjusted()) > MAX_NUMBER_EXPONENT:
        raise ExpressionViolation("numeric literal exponent exceeds limit")
    normalized = format(value.normalize(), "f")
    return "0" if normalized in {"-0", ""} else normalized


def _tokenize(expression: str) -> tuple[_Token, ...]:
    if type(expression) is not str:
        raise TypeError("expression must be a string")
    if not expression or not expression.strip():
        raise ExpressionViolation("expression is empty")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ExpressionViolation("expression exceeds length limit")

    position = 0
    tokens: list[_Token] = []
    whitespace_after_token = False
    while position < len(expression):
        match = TOKEN.match(expression, position)
        if match is None:
            if expression[position] == "'":
                raise ExpressionViolation("unterminated string literal")
            raise ExpressionViolation(f"invalid character at offset {position}")
        kind = match.lastgroup
        if kind is None:
            raise ExpressionViolation(f"invalid token at offset {position}")
        text = match.group()
        token_offset = position
        position = match.end()
        if kind == "space":
            whitespace_after_token = bool(tokens)
            continue
        if kind == "number":
            text = _normalized_number(text)
        elif kind == "identifier":
            text = text.lower()
        if (
            whitespace_after_token
            and tokens[-1].kind in {"identifier", "number", "string"}
            and kind in {"identifier", "number", "string"}
        ):
            raise ExpressionViolation("whitespace cannot separate lexical tokens")
        tokens.append(_Token(kind, text, token_offset))
        whitespace_after_token = False
        if len(tokens) > MAX_TOKENS:
            raise ExpressionViolation("expression exceeds token limit")
    if not tokens:
        raise ExpressionViolation("expression is empty")
    return tuple(tokens)


def normalize_expression(expression: str) -> str:
    tokens = _tokenize(expression)
    depth = 0
    for token in tokens:
        if token.text == "(":
            depth += 1
            if depth > MAX_NESTING:
                raise ExpressionViolation("expression exceeds nesting limit")
        elif token.text == ")":
            depth -= 1
            if depth < 0:
                raise ExpressionViolation("unbalanced parentheses")
    if depth != 0:
        raise ExpressionViolation("unbalanced parentheses")
    return "".join(token.text for token in tokens)


def fingerprint_expression(expression: str) -> str:
    canonical = normalize_expression(expression)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _Parser:
    def __init__(self, tokens: tuple[_Token, ...]) -> None:
        self._tokens = tokens
        self._position = 0
        self._expression_depth = 0

    def parse(self) -> _Expression:
        expression = self._parse_expression(0)
        if self._peek() is not None:
            raise ExpressionViolation(f"unexpected token at offset {self._peek().offset}")
        return expression

    def _peek(self, distance: int = 0) -> _Token | None:
        position = self._position + distance
        return self._tokens[position] if position < len(self._tokens) else None

    def _take(self) -> _Token:
        token = self._peek()
        if token is None:
            raise ExpressionViolation("unexpected end of expression")
        self._position += 1
        return token

    def _parse_expression(self, minimum_precedence: int) -> _Expression:
        self._expression_depth += 1
        if self._expression_depth > MAX_NESTING:
            self._expression_depth -= 1
            raise ExpressionViolation("expression exceeds parser nesting limit")
        try:
            left = self._parse_prefix()
            while True:
                token = self._peek()
                precedence = _BINARY_PRECEDENCE.get(token.text) if token is not None else None
                if precedence is None or precedence < minimum_precedence:
                    return left
                operator = self._take().text
                right = self._parse_expression(precedence + 1)
                left = _Binary(operator, left, right)
        finally:
            self._expression_depth -= 1

    def _parse_prefix(self) -> _Expression:
        unary: list[str] = []
        while self._peek() is not None and self._peek().text in {"+", "-"}:
            unary.append(self._take().text)
            if len(unary) > MAX_NESTING:
                raise ExpressionViolation("expression exceeds unary operator limit")
        token = self._take()
        if token.kind == "number" or token.kind == "string":
            expression: _Expression = _Literal(token.kind, token.text)
        elif token.kind == "identifier":
            if self._peek() is not None and self._peek().text == "(":
                expression = self._parse_call(token.text)
            else:
                expression = _Identifier(token.text)
        elif token.text == "(":
            grouped = self._parse_expression(0)
            closing = self._take()
            if closing.text != ")":
                raise ExpressionViolation(f"expected ')' at offset {closing.offset}")
            expression = grouped
        else:
            raise ExpressionViolation(f"unexpected token at offset {token.offset}")
        for operator in reversed(unary):
            expression = _Unary(operator, expression)
        return expression

    def _parse_call(self, name: str) -> _Call:
        opening = self._take()
        if opening.text != "(":
            raise ExpressionViolation(f"expected '(' at offset {opening.offset}")
        positional: list[_Expression] = []
        named: list[tuple[str, _Expression]] = []
        named_seen: set[str] = set()
        seen_named = False
        if self._peek() is not None and self._peek().text == ")":
            self._take()
            return _Call(name, (), ())
        while True:
            first = self._peek()
            second = self._peek(1)
            if first is not None and first.kind == "identifier" and second is not None and second.text == "=":
                seen_named = True
                parameter = self._take().text
                self._take()
                if parameter in named_seen:
                    raise ExpressionViolation(f"duplicate named argument: {parameter}")
                named_seen.add(parameter)
                named.append((parameter, self._parse_expression(0)))
            else:
                if seen_named:
                    raise ExpressionViolation("positional argument follows named argument")
                positional.append(self._parse_expression(0))
            separator = self._take()
            if separator.text == ")":
                return _Call(name, tuple(positional), tuple(named))
            if separator.text != ",":
                raise ExpressionViolation(f"expected ',' or ')' at offset {separator.offset}")
            if self._peek() is None or self._peek().text == ")":
                raise ExpressionViolation("missing function argument")


def _parse_canonical_expression(canonical_expression: str) -> _Expression:
    return _Parser(_tokenize(canonical_expression)).parse()


def _normalize_name_set(values: object, label: str) -> frozenset[str]:
    if not isinstance(values, (set, frozenset, tuple, list)):
        raise TypeError(f"{label} must be a collection of strings")
    normalized: set[str] = set()
    for value in values:
        if type(value) is not str or not value.strip():
            raise TypeError(f"{label} must contain non-empty strings")
        normalized.add(value.lower())
    return frozenset(normalized)


def _normalize_operator_metadata(operators: object) -> Mapping[str, Mapping[str, object]]:
    if not isinstance(operators, Mapping):
        raise TypeError("operators must be a mapping")
    normalized: dict[str, Mapping[str, object]] = {}
    for name, metadata in operators.items():
        if type(name) is not str or not name.strip():
            raise TypeError("operators must use non-empty string names")
        if not isinstance(metadata, Mapping):
            raise TypeError("operator metadata must be mappings")
        arity = metadata.get("arity")
        if type(arity) is not int or arity < 0:
            raise ExpressionViolation(f"operator metadata arity is invalid: {name}")
        normalized_name = name.lower()
        if normalized_name in normalized:
            raise ExpressionViolation(f"duplicate operator metadata: {normalized_name}")
        normalized[normalized_name] = metadata
    return MappingProxyType(normalized)


def _walk_expression(
    expression: _Expression,
    *,
    operator_metadata: Mapping[str, Mapping[str, object]],
    fields: list[str],
    field_seen: set[str],
    operators: list[str],
) -> None:
    pending = [expression]
    while pending:
        current = pending.pop()
        if isinstance(current, _Identifier):
            if current.name not in field_seen:
                field_seen.add(current.name)
                fields.append(current.name)
            continue
        if isinstance(current, _Literal):
            continue
        if isinstance(current, _Unary):
            pending.append(current.value)
            continue
        if isinstance(current, _Binary):
            pending.append(current.right)
            pending.append(current.left)
            continue
        if current.name not in operator_metadata:
            raise ExpressionViolation(f"unknown operator: {current.name}")
        named = dict(current.named)
        allowed_named = _ALLOWED_NAMED_PARAMETERS.get(current.name, frozenset())
        unknown_named = sorted(set(named) - allowed_named)
        if unknown_named:
            raise ExpressionViolation(
                f"operator {current.name} does not allow named argument {unknown_named[0]}"
            )
        for parameter in _REQUIRED_NAMED_PARAMETERS.get(current.name, ()):
            if parameter not in named:
                raise ExpressionViolation(f"operator {current.name} requires parameter {parameter}")
        if current.name == "ts_quantile":
            driver = named.get("driver")
            if not isinstance(driver, _Literal) or driver.kind != "string":
                raise ExpressionViolation("operator ts_quantile requires string literal driver")
        expected_arity = operator_metadata[current.name]["arity"]
        if len(current.positional) != expected_arity:
            raise ExpressionViolation(
                f"operator {current.name} arity requires {expected_arity} positional arguments"
            )
        operators.append(current.name)
        if len(operators) > MAX_OPERATOR_CALLS:
            raise ExpressionViolation("expression exceeds operator call limit")
        arguments = (*current.positional, *(value for _, value in current.named))
        pending.extend(reversed(arguments))


def validate_candidate(
    candidate: object,
    *,
    allowed_fields: object,
    banned_fields: object,
    operators: object,
) -> ValidatedCandidate:
    """Validate one model-proposed REGULAR FASTEXPR candidate without executing it."""

    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be a mapping")
    expression = candidate.get("expression")
    if type(expression) is not str:
        raise ExpressionViolation("candidate.expression must be a string")
    if candidate.get("single_mechanism") is not True:
        raise ExpressionViolation("candidate.single_mechanism must be exactly true")
    field_id = candidate.get("field_id")
    if type(field_id) is not str or not field_id.strip():
        raise ExpressionViolation("candidate.field_id must be a non-empty string")

    normalized_allowed = _normalize_name_set(allowed_fields, "allowed_fields")
    normalized_banned = _normalize_name_set(banned_fields, "banned_fields")
    if not normalized_allowed:
        raise ExpressionViolation("allowed_fields must not be empty")
    metadata = _normalize_operator_metadata(operators)
    canonical_expression = normalize_expression(expression)
    parsed = _parse_canonical_expression(canonical_expression)
    fields: list[str] = []
    used_operators: list[str] = []
    _walk_expression(
        parsed,
        operator_metadata=metadata,
        fields=fields,
        field_seen=set(),
        operators=used_operators,
    )
    if len(fields) > MAX_FIELDS:
        raise ExpressionViolation("expression exceeds field limit")
    candidate_field = field_id.lower()
    all_fields = set(fields) | {candidate_field}
    banned = sorted(all_fields & normalized_banned)
    if banned:
        raise ExpressionViolation(f"banned field: {banned[0]}")
    unknown = sorted(all_fields - normalized_allowed)
    if unknown:
        raise ExpressionViolation(f"unknown field: {unknown[0]}")
    if candidate_field not in fields:
        raise ExpressionViolation("candidate.field_id is not referenced by expression")
    return ValidatedCandidate(
        canonical_expression=canonical_expression,
        fingerprint=hashlib.sha256(canonical_expression.encode("utf-8")).hexdigest(),
        fields=tuple(fields),
        operators=tuple(used_operators),
        original_candidate=_immutable_candidate_snapshot(candidate),
    )


def _immutable_candidate_snapshot(candidate: Mapping[object, object]) -> Mapping[str, object]:
    nodes = 0
    active: set[int] = set()

    def freeze(value: object, depth: int) -> object:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_CANDIDATE_NODES or depth > MAX_CANDIDATE_DEPTH:
            raise ExpressionViolation("candidate snapshot exceeds structural limit")
        if value is None or type(value) in {bool, int, str}:
            return value
        if type(value) is float:
            if not isfinite(value):
                raise ExpressionViolation("candidate snapshot numbers must be finite")
            return value
        if isinstance(value, Mapping):
            identity = id(value)
            if identity in active:
                raise ExpressionViolation("candidate snapshot must not contain cycles")
            active.add(identity)
            copied: dict[str, object] = {}
            for key, child in value.items():
                if type(key) is not str:
                    raise ExpressionViolation("candidate snapshot keys must be strings")
                copied[key] = freeze(child, depth + 1)
            active.remove(identity)
            return MappingProxyType(copied)
        if isinstance(value, (list, tuple)):
            identity = id(value)
            if identity in active:
                raise ExpressionViolation("candidate snapshot must not contain cycles")
            active.add(identity)
            copied_items = tuple(freeze(child, depth + 1) for child in value)
            active.remove(identity)
            return copied_items
        raise ExpressionViolation("candidate snapshot must contain JSON-native values")

    frozen = freeze(candidate, 0)
    if not isinstance(frozen, Mapping):
        raise ExpressionViolation("candidate snapshot must be an object")
    return frozen
