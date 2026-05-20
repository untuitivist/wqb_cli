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
