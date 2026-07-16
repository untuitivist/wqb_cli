# `/consultant/boards/spc`

- URL: `https://api.worldquantbrain.com/consultant/boards/spc`
- Methods: `GET` (use `OPTIONS` for live metadata)
- Authentication: required
- Permission: consultant
- Sources: current platform frontend and authenticated live probes

This is the SPC instance of the generic `/consultant/boards/{board_type}` resource. `OPTIONS` advertises the current board period and aggregation choices. `GET` returns a paginated leaderboard with fields such as `rank`, `user`, `prompts`, `dailyRankChange`, and `scaledDailyPnl`.

Use the generic leaderboard command with an explicit consultant scope:

```text
wqb competition leaderboard spc --scope consultant --method OPTIONS
wqb competition leaderboard spc --scope consultant --board BOARD_FROM_OPTIONS --limit 20
```
