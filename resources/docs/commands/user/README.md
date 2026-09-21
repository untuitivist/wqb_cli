# Current user resources

New read commands use the shared registry, transport and JSON output:

```text
wqb user activity base-payment --user-id self --param limit=20
wqb user activity other-payment --user-id self
wqb user osmosis-summary --user-id self
wqb user osmosis-scale-status --user-id self
wqb user streak
wqb user tags --param limit=20
wqb user submission-activity --param limit=20
```

`user user-activities self` lists activity names supported by the account. Generic `--param KEY=VALUE` preserves date filters and pagination without guessing a new schema.

`osmosis-scale-status` reads status once. HTTP 204 is a normal empty terminal response; Retry-After indicates work in progress. It does not start or change point scaling. The separate POST scaling endpoint is available through `api call` and is documented as untested by the read-only inventory refresh.

Use `wqb api show PATH` to inspect live-probe evidence and `wqb api call OPTIONS PATH` for fresh server metadata. Some endpoints reject OPTIONS even while their Allow headers advertise methods. Advertised mutation methods are not a guarantee of account permission.
