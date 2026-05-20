# Notes

Authentication must persist cookies to `wqb_cli/local/auth/cookies.json`.
Otherwise `POST /authentication` can succeed while the next `sim create` still fails with `401 Incorrect authentication credentials`.

Do not write `wqb_cli/local/.env` values to examples, run directories, or docs.

After login, run `auth/status` to verify the persisted session.
