# Create an SPC Prompt Submission

First inspect current model and update-frequency choices:

```text
wqb competition spc submission-options
```

Then explicitly create the remote submission:

```text
wqb competition spc create-submission --input spc-submission.json
```

This is a mutating request.
