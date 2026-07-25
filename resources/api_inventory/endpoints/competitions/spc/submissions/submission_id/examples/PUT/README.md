# Replace an SPC Prompt Submission

```text
wqb competition spc update-submission SUBMISSION_ID --method PUT --input spc-submission.json
```

`PUT` expects the full submission object described by `/competitions/spc/submissions` and replaces remote state. Inspect `OPTIONS` first and use current model choices.
