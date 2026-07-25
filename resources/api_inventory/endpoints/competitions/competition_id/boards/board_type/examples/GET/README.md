# Generic Competition Leaderboard Example

Inspect a board's live metadata before relying on its columns:

```text
wqb competition leaderboard PAC2026 --board-type leader --method OPTIONS
```

Read one page:

```text
wqb competition leaderboard PAC2026 --board-type leader --limit 20 --offset 0 --order=-score
```

Equivalent raw call:

```text
wqb api call GET /competitions/{competition_id}/boards/{board_type} --var competition_id=PAC2026 --var board_type=leader --param limit=20 --param offset=0 --param order=-score
```
