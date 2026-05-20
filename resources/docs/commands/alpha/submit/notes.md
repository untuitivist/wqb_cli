# Notes

Submit is not a single POST-only action. The platform may accept the initial request and then keep `/alphas/{alpha_id}/submit` pending with `Retry-After`.

Agent rules:

- Do not judge final submission from POST status alone.
- Use the default `--max-wait-seconds 1800` for real submissions.
- Use a shorter wait only for CLI behavior verification.
- If the CLI returns `submit_code=408`, the submit request was accepted but did not finish in the wait window; continue checking the same alpha instead of repeatedly resubmitting.
- If the CLI returns `submit_code=403`, inspect `classification.checks`; the output keeps the full checks object.
