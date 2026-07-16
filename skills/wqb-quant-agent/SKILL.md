---
name: wqb-quant-agent
description: Use when starting, resuming, inspecting, approving, or rejecting bounded multi-model WorldQuant BRAIN REGULAR FASTEXPR research through wqb-cli.
---

# WQB Quant Agent

Use `wqb agent` as the only orchestration entry point. The Planner model makes research-direction decisions; the Operator model performs bounded transformations.

1. Run `wqb agent models list`; configure missing roles with `models set` and `models set-key`.
2. Start a manual scope with all four scope values, or explicitly choose `--scope-mode auto`. A run performs real simulations within its budget.
3. Inspect with `wqb agent status RUN_ID` and continue with `wqb agent resume RUN_ID`. Do not reproduce or bypass the A-M workflow in conversation.
4. When state is `AWAITING_APPROVAL`, present the exact final report and recommended Alpha ID.
5. After explicit user approval of that report, call `wqb agent approve RUN_ID`; otherwise call `wqb agent reject RUN_ID --reason TEXT`.

Never call `wqb alpha submit` directly. Never expose API keys, cookies, `.env` content, or keyring values. Never bypass budgets, Planner/Operator roles, scope locks, or the approval hash.
