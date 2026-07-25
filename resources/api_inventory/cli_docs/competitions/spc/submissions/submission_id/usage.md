# `/competitions/spc/submissions/{submission_id}` CLI

```text
wqb competition spc submission-history SUBMISSION_ID --limit 20
wqb competition spc submission-options SUBMISSION_ID
wqb competition spc update-submission SUBMISSION_ID --method PATCH --json "{\"weight\":0.5}"
wqb competition spc update-submission SUBMISSION_ID --method PUT --input spc-submission.json
```

`PUT` and `PATCH` mutate remote state.
