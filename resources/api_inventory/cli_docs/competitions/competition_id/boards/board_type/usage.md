# `/competitions/{competition_id}/boards/{board_type}` CLI

```text
wqb competition leaderboard PAC2026 --board-type leader --method OPTIONS
wqb competition leaderboard PAC2026 --board-type leader --limit 20 --offset 0
```

Raw form:

```text
wqb api call GET /competitions/{competition_id}/boards/{board_type} --var competition_id=PAC2026 --var board_type=leader --param limit=20 --param offset=0
```
