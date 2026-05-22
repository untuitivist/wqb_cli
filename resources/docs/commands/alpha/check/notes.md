# Notes

`alpha check` can initially return `Retry-After` with an empty body.
That is not a failure.
The CLI now waits automatically up to `--max-wait-seconds 900` until the response contains a final body.
If the cap is reached, the output contains `classification.reason = alpha_wait_timed_out` and exits non-zero.

Platform PASS does not necessarily satisfy user research hard metrics.
In the real example, `YPNOpk3W` passes platform checks but has `margin = 0.000828`, below a user hard target of `0.001`.
