# `/competitions/spc/submissions/{submission_id}`

- URL template: `https://api.worldquantbrain.com/competitions/spc/submissions/{submission_id}`
- Methods: `GET`, `PUT`, `PATCH` (plus `HEAD`, `OPTIONS` metadata methods)
- Authentication: required
- Sources: current platform frontend and authenticated live probes

`GET` returns a paginated weight history with `date` and `weight`; it does not return the collection's full submission object. `PUT` replaces a submission, while `PATCH` supports partial updates. The current frontend uses `PATCH` with a weight-only body.

The current `Allow` header is `GET, PUT, PATCH, HEAD, OPTIONS`; `DELETE` is not available.

```text
wqb competition spc submission-history SUBMISSION_ID --limit 20
wqb competition spc submission-options SUBMISSION_ID
wqb competition spc update-submission SUBMISSION_ID --method PATCH --json "{\"weight\":0.5}"
```

`PUT` and `PATCH` mutate platform state and were not executed during inventory validation.
