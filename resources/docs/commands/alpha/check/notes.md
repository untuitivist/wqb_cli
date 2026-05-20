# Notes

`alpha check` can initially return `Retry-After` with an empty body.
That is not a failure.
Wait and repeat the same command until the response contains `body.is.checks`.

Platform PASS does not necessarily satisfy user research hard metrics.
In the real example, `YPNOpk3W` passes platform checks but has `margin = 0.000828`, below a user hard target of `0.001`.

