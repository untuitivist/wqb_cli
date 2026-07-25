# Generic Consultant Leaderboard Example

Inspect a board's schema:

```text
wqb competition leaderboard spc --scope consultant --method OPTIONS
```

Read one page after supplying any required `board` value returned by `OPTIONS`:

```text
wqb competition leaderboard spc --scope consultant --board BOARD_FROM_OPTIONS --limit 20 --offset 0
```

Equivalent raw call:

```text
wqb api call GET /consultant/boards/{board_type} --var board_type=spc --param limit=20 --param offset=0 --param board=BOARD_FROM_OPTIONS
```
