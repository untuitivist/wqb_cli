# config Notes

Credential resolution order for `wqb auth login --execute`:

- explicit `--email` / `--password`
- JSON `--input`
- keyring password using `auth.keyring_service` and `auth.keyring_username`
- `wqb_cli/local/.env`
- legacy root `.env` fallback

Recommended setup:

1. `wqb config init`
2. `wqb config set auth.email <email>`
3. `wqb config set-secret auth.password <password>`
4. `wqb auth login --execute`

