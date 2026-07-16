# `/competitions/spc/submissions`

- URL: `https://api.worldquantbrain.com/competitions/spc/submissions`
- Methods: `GET`, `POST` (plus `HEAD`, `OPTIONS` metadata methods)
- Authentication: required
- Sources: current platform frontend and authenticated live probes

`GET` returns the authenticated user's paginated prompt submissions. `POST` creates a new submission.

## POST Body

Required fields reported by `OPTIONS`:

- `name`: string, max 200
- `prompt`: string, max 10000
- `sampleOutput`: string, max 10000
- `model`: a current choice returned by `OPTIONS`
- `modelVersion`: string, max 100
- `weight`: decimal from 0 to 1, rounded to 2 places
- `updateFrequency`: `quarterly`, `monthly`, `weekly`, or `daily`

Creating a submission mutates platform state. Inventory validation inspected `OPTIONS` and frontend code but did not execute `POST`.

```text
wqb competition spc submissions --limit 20
wqb competition spc submission-options
wqb competition spc create-submission --input spc-submission.json
```
