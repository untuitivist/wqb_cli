"""
功能概述
`wqb_core.simulation.concurrent_simulate` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `concurrent_simulate(...)`

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.simulation"

import asyncio
from collections.abc import Coroutine, Iterable, Sized
from typing import Any

from requests import Response

from ..foundation.async_utils import concurrent_await
from ..foundation.defines import Alpha, MultiAlpha

_SLOT_SETTING_KEYS = ('language', 'instrumentType', 'region', 'delay')


def _slot_signature(alpha: Alpha) -> tuple[Any, Any, Any, Any]:
    if not isinstance(alpha, dict):
        raise ValueError(f'alpha must be a dict when packing slots: {alpha!r}')
    settings = alpha.get('settings')
    if not isinstance(settings, dict):
        raise ValueError(f'alpha.settings must be a dict when packing slots: {alpha!r}')
    missing = [key for key in _SLOT_SETTING_KEYS if key not in settings]
    if missing:
        raise ValueError(
            f"alpha.settings missing required slot keys {missing}: {alpha!r}"
        )
    return tuple(settings[key] for key in _SLOT_SETTING_KEYS)


def _is_multi_alpha(target: Alpha | MultiAlpha) -> bool:
    return isinstance(target, (list, tuple))


def _validate_multi_alpha(target: MultiAlpha) -> None:
    iterator = iter(target)
    try:
        first = next(iterator)
    except StopIteration:
        return
    expected = _slot_signature(first)
    for alpha in iterator:
        if _slot_signature(alpha) != expected:
            raise ValueError(
                'all alphas in the same slot must share '
                'language/instrumentType/region/delay'
            )


def _slot_size(slot_count: int | Iterable[int]) -> int:
    if isinstance(slot_count, int):
        return slot_count
    return len(tuple(slot_count))


def _pack_targets_by_slot(
    targets: list[Alpha],
    slot_count: int | Iterable[int],
) -> list[MultiAlpha]:
    size = _slot_size(slot_count)
    if size <= 0:
        raise ValueError(f'slot_count must be positive: {slot_count!r}')
    packed: list[MultiAlpha] = []
    open_slots: dict[tuple[Any, Any, Any, Any], list[Alpha]] = {}
    for alpha in targets:
        signature = _slot_signature(alpha)
        bucket = open_slots.setdefault(signature, [])
        bucket.append(alpha)
        if len(bucket) >= size:
            packed.append(bucket)
            del open_slots[signature]
    packed.extend(open_slots.values())
    return packed


class ConcurrentSimulateMixin:
    async def concurrent_simulate(
        self,
        targets: Iterable[Alpha | MultiAlpha],
        concurrency: int | asyncio.Semaphore,
        *args,
        slot_count: int | Iterable[int] = 10,
        auto_pack: bool = True,
        return_exceptions: bool = False,
        log: str | None = '',
        log_gap: int = 100,
        **kwargs,
    ) -> Coroutine[None, None, list[Response | BaseException]]:
        """
        并发提交 simulation 任务。
        
        该方法通过 `WQBSession.concurrent_simulate(...)` 暴露。
        
        这是一个异步方法；若直接在脚本中运行，入口会自动处理事件循环。
        """
        if not isinstance(targets, Sized):
            targets = list(targets)
        original_total = len(targets)
        if 0 < original_total:
            if auto_pack and not _is_multi_alpha(targets[0]):
                targets = _pack_targets_by_slot(targets, slot_count)
            elif _is_multi_alpha(targets[0]):
                for target in targets:
                    _validate_multi_alpha(target)
        if log is None:
            log_gap = 0
        if isinstance(concurrency, int):
            concurrency = asyncio.Semaphore(value=concurrency)
        total = len(targets)
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_simulate(...) [start {original_total}->{total}, {concurrency._value}]: {log}"
            )
        resp = await concurrent_await(
            (
                self.simulate(
                    target,
                    *args,
                    log=(
                        f"{idx}/{total} = {int(100*idx/total)}%"
                        if 0 != log_gap and 0 == idx % log_gap
                        else None
                    ),
                    **kwargs,
                )
                for idx, target in enumerate(targets, start=1)
            ),
            concurrency=concurrency,
            return_exceptions=return_exceptions,
        )
        if log is not None:
            self.logger.info(
                f"{self}.concurrent_simulate(...) [finish {original_total}->{total}, {concurrency._value}]: {log}"
            )
        return resp

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json
    import sys
    from pathlib import Path

    from wqb_core import WQBSession
    from requests import Response

    def _cli_parse_value(text: str):
        lowered = text.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        if text.startswith("@file:"):
            return json.loads(Path(text[6:]).read_text(encoding="utf-8-sig"))
        if text.startswith("@jsonfile:"):
            return json.loads(Path(text[10:]).read_text(encoding="utf-8-sig"))
        if text.startswith("@json:"):
            return json.loads(text[6:])
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    def _cli_collect_unknown(tokens: list[str]) -> dict[str, object]:
        data: dict[str, object] = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if not token.startswith("--"):
                raise SystemExit(f"Unsupported positional argument: {token!r}")
            if "=" in token:
                key_text, value_text = token.split("=", 1)
                key = key_text[2:].replace("-", "_")
                value = _cli_parse_value(value_text)
                if key in data:
                    current = data[key]
                    if isinstance(current, list):
                        current.append(value)
                    else:
                        data[key] = [current, value]
                else:
                    data[key] = value
                i += 1
                continue
            key = token[2:].replace("-", "_")
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                value = True
                i += 1
            else:
                value = _cli_parse_value(tokens[i + 1])
                i += 2
            if key in data:
                current = data[key]
                if isinstance(current, list):
                    current.append(value)
                else:
                    data[key] = [current, value]
            else:
                data[key] = value
        return data

    def _cli_serialize(value):
        if isinstance(value, Response):
            payload = {
                "status_code": value.status_code,
                "reason": value.reason,
                "url": value.url,
                "headers": dict(value.headers),
            }
            try:
                payload["json"] = value.json()
            except ValueError:
                payload["text"] = value.text
            return payload
        if isinstance(value, dict):
            return {str(k): _cli_serialize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_cli_serialize(v) for v in value]
        if inspect.isgenerator(value):
            return [_cli_serialize(v) for v in list(value)]
        return value

    def _cli_write_json(path: str | None, value) -> None:
        if not path:
            return
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(_cli_serialize(value), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _normalize_cli_targets(value):
        if isinstance(value, dict):
            for key in ("targets", "payloads", "simulation_batch", "candidates"):
                nested = value.get(key)
                if isinstance(nested, list):
                    return nested
            if {"type", "settings", "regular"}.issubset(value):
                return [value]
        return value

    def _candidate_payload(candidate):
        if isinstance(candidate, dict) and {"type", "settings", "regular"}.issubset(candidate):
            return {
                "type": candidate["type"],
                "settings": candidate["settings"],
                "regular": candidate["regular"],
            }
        return candidate

    def _candidate_id(candidate, index: int) -> str:
        if isinstance(candidate, dict):
            for key in ("id", "candidate_id", "name"):
                value = candidate.get(key)
                if value:
                    return str(value)
        return f"candidate_{index:03d}"

    def _preview_artifacts(targets, payload_output_dir: str | None):
        payloads = []
        submitted = []
        if targets is None:
            return payloads, submitted
        for index, candidate in enumerate(targets, start=1):
            candidate_id = _candidate_id(candidate, index)
            payload = _candidate_payload(candidate)
            payload_record = {
                "candidate_id": candidate_id,
                "payload": payload,
            }
            payloads.append(payload_record)
            submitted.append(
                {
                    "candidate_id": candidate_id,
                    "language": (
                        payload.get("settings", {}).get("language")
                        if isinstance(payload, dict)
                        else None
                    ),
                    "type": payload.get("type") if isinstance(payload, dict) else None,
                    "status": "preview",
                    "payload_file": f"{candidate_id}.json" if payload_output_dir else None,
                }
            )
            if payload_output_dir:
                output_path = Path(payload_output_dir) / f"{candidate_id}.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
        return payloads, submitted

    parser = argparse.ArgumentParser(description=inspect.getdoc(ConcurrentSimulateMixin.concurrent_simulate) or "")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--prefer-dotenv")
    parser.add_argument("--dotenv-path")
    parser.add_argument(
        "--mode",
        choices=("preview", "submit_and_poll"),
        default="submit_and_poll",
        help="preview writes node artifacts without API submission.",
    )
    parser.add_argument("--output", help="Write serialized JSON result to this path instead of stdout.")
    parser.add_argument("--payload-output-dir", help="Write each submitted payload to this directory.")
    parser.add_argument("--submitted-output", help="Write submitted batch metadata to this path.")
    parser.add_argument("--resume-output", help="Write resumable run state to this path.")
    args, unknown = parser.parse_known_args()

    session_kwargs = {}
    if args.prefer_dotenv is not None:
        session_kwargs["prefer_dotenv"] = _cli_parse_value(args.prefer_dotenv)
    if args.dotenv_path is not None:
        session_kwargs["dotenv_path"] = args.dotenv_path
    if args.username is not None or args.password is not None:
        if args.username is None or args.password is None:
            raise SystemExit("--username and --password must be provided together")
        session_kwargs["wqb_auth"] = (args.username, args.password)

    kwargs = _cli_collect_unknown(unknown)
    kwargs["targets"] = _normalize_cli_targets(kwargs.get("targets"))
    payloads, submitted = _preview_artifacts(kwargs.get("targets"), args.payload_output_dir)
    _cli_write_json(
        args.resume_output,
        {
            "mode": args.mode,
            "status": "started",
            "submitted_count": len(submitted),
        },
    )
    _cli_write_json(args.submitted_output, submitted)
    if args.mode == "preview":
        result = {
            "mode": "preview",
            "submitted_count": len(submitted),
            "results": [],
            "payloads": payloads,
        }
        _cli_write_json(
            args.resume_output,
            {
                "mode": args.mode,
                "status": "preview_complete",
                "submitted_count": len(submitted),
            },
        )
        serialized = _cli_serialize(result)
        text = json.dumps(serialized, ensure_ascii=False, indent=2, default=str)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text, encoding="utf-8")
        else:
            print(text)
        raise SystemExit(0)

    session = WQBSession(**session_kwargs)
    target = getattr(session, "concurrent_simulate")
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    _cli_write_json(
        args.resume_output,
        {
            "mode": args.mode,
            "status": "complete",
            "submitted_count": len(submitted),
        },
    )
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    serialized = _cli_serialize(result)
    text = json.dumps(serialized, ensure_ascii=False, indent=2, default=str)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text)
