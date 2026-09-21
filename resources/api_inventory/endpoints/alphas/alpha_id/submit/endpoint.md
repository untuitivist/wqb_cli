# `/alphas/{alpha_id}/submit`

- URL template: `https://api.worldquantbrain.com/alphas/{alpha_id}/submit`
- Methods: `POST`
- Sources: `rocky-d/wqb`
- Safe probe: `False`
- Description: Submit alpha.
- Request body: Submission action. Has side effect.

## Probe

- Skipped

## Endpoint Tests

### `POST /alphas/{alpha_id}/submit`

- Status: `skipped_mutating`
- Tested path: `/alphas/vR5p8vqb/submit`
- Reason: POST may mutate remote state; not executed by inventory test.

## API refresh 2026-09-22

Submit alpha.

- Advertised methods: GET, HEAD, OPTIONS, PATCH, POST, PUT.
- Live OPTIONS status: 200. Mutation methods were not executed.
- Account-specific option values are omitted; use `wqb api call` with OPTIONS for current metadata.
