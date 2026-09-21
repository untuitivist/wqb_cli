# `/competitions/{competition_id}/boards/{board_type}`

- URL template: `https://api.worldquantbrain.com/competitions/{competition_id}/boards/{board_type}`
- Methods: `GET` (use `OPTIONS` for live metadata)
- Authentication: required
- Sources: current platform frontend and authenticated live probes

This is the generic leaderboard resource for a competition. The platform currently constructs board types such as `leader`, `university`, `prize`, `referral`, and `power-pool`, but each competition exposes only the boards it supports.

## Query Parameters

- `limit`, `offset`: pagination
- `aggregate`: an aggregation advertised by `OPTIONS`, commonly `user` or `team`
- `order`: field name, with `-` for descending order
- `property` and `<property>~`: prefix-search fields used by the frontend
- `board`: a period or region value when advertised by `OPTIONS`

## Verified Behavior

`GET /competitions/PAC2026/boards/leader?limit=1&offset=0` returned `200` with a paginated leaderboard. `OPTIONS` returned the competition-specific columns, filters, and aggregation choices. Other board types returned `404` when that competition did not expose them.

The CLI keeps this generic:

```text
wqb competition leaderboard PAC2026 --board-type leader --limit 20
wqb competition leaderboard PAC2026 --board-type leader --method OPTIONS
```

Consultant boards are a parallel generic namespace and use `--scope consultant`.

## API refresh 2026-09-22

Generic competition leaderboard. Use OPTIONS to discover the fields, filters, and aggregations available for a competition and board type.

- Advertised methods: GET.
- Live OPTIONS status: SKIPPED_NO_OBSERVED_ID. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
