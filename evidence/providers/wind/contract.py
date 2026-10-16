from __future__ import annotations

from dataclasses import dataclass


WIND_PROVIDER_NAME = "wind"
WIND_EVIDENCE_CONTRACT_VERSION = "1.0"

# Workflow standing is intentionally asymmetric. G is the primary call site;
# H may request bounded clarification; K is diagnosis-only. The execution path
# remains BRAIN-authoritative.
WIND_WORKFLOW_STANDING = {
    "F": "forbidden",
    "G": "primary",
    "H": "supplemental",
    "I": "forbidden",
    "J": "forbidden",
    "K": "diagnostic",
    "L": "forbidden",
    "M": "forbidden",
}

WIND_SERVER_TYPES = frozenset(
    {
        "stock_data",
        "fund_data",
        "index_data",
        "bond_data",
        "financial_docs",
        "economic_data",
        "analytics_data",
    }
)


@dataclass(frozen=True)
class WindAccessDecision:
    allowed: bool
    node: str
    standing: str
    purpose: str
    reason: str


def decide_wind_access(node: str, purpose: str) -> WindAccessDecision:
    normalized_node = node.strip().upper()
    standing = WIND_WORKFLOW_STANDING.get(normalized_node, "forbidden")
    normalized_purpose = purpose.strip().lower()

    if standing == "primary":
        allowed = normalized_purpose in {"research", "reality_check"}
    elif standing == "supplemental":
        allowed = normalized_purpose in {"clarification", "reality_check"}
    elif standing == "diagnostic":
        allowed = normalized_purpose == "diagnosis"
    else:
        allowed = False

    return WindAccessDecision(
        allowed=allowed,
        node=normalized_node,
        standing=standing,
        purpose=normalized_purpose,
        reason=(
            "allowed_by_workflow_standing"
            if allowed
            else "wind_not_allowed_for_node_or_purpose"
        ),
    )


def require_wind_access(node: str, purpose: str) -> WindAccessDecision:
    decision = decide_wind_access(node, purpose)
    if not decision.allowed:
        raise PermissionError(
            f"Wind evidence is not allowed at node={decision.node} purpose={decision.purpose} "
            f"standing={decision.standing}"
        )
    return decision
