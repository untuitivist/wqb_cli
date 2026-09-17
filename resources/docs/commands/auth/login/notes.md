# Notes

Authentication must persist cookies to `wqb_cli/local/auth/cookies.json`.
Otherwise `POST /authentication` can succeed while the next `sim create` still fails with `401 Incorrect authentication credentials`.

Do not write `wqb_cli/local/.env` values to examples, run directories, or docs.

Current platform login uses HTTP Basic credentials with `Accept: application/json;version=2.0`. The JSON request body must not contain `email`, `password`, or legacy `expiry`; when a CAPTCHA token is supplied, send only `{\"captcha\": ...}`.

After login, run `auth/status` to verify the persisted session.
