# `/consultant/boards/{board_type}`

- URL template: `https://api.worldquantbrain.com/consultant/boards/{board_type}`
- Methods: `GET` (use `OPTIONS` for live metadata)
- Authentication: required
- Permission: consultant
- Sources: current platform frontend and authenticated live probes

This is the generic consultant-board namespace. Live `GET` and `OPTIONS` probes returned `200` for `leader`, `spc`, `power-pool`, and `referral`. Each board advertises its own fields, filters, periods, and aggregations through `OPTIONS`.

```text
wqb competition leaderboard spc --scope consultant --method OPTIONS
wqb competition leaderboard power-pool --scope consultant --method OPTIONS
wqb competition leaderboard referral --scope consultant --limit 20
```

This resource is separate from `/competitions/{competition_id}/boards/{board_type}`. The difference is namespace/scope, not a one-off SPC model.
