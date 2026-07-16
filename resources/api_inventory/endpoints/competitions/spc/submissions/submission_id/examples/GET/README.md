# Read SPC Submission Weight History

```text
wqb competition spc submission-history SUBMISSION_ID --limit 20 --offset 0
```

Equivalent raw call:

```text
wqb api call GET /competitions/spc/submissions/{submission_id} --var submission_id=SUBMISSION_ID --param limit=20 --param offset=0
```
