# config

Local CLI configuration commands.

Default config path:

```text
wqb_cli/local/config.json
```

Commands:

- `wqb config init`: create default local config.
- `wqb config list`: print config.
- `wqb config get <key>`: read one dot-key.
- `wqb config set <key> <value>`: set one dot-key.
- `wqb config set-secret auth.password <value>`: store password in keyring.
- `wqb config platform`: call platform `GET /configuration`.
- `wqb config competition-levels`: call `GET /competition-levels`.

Secrets are not written into `config.json`.
The config only stores keyring service and username metadata.

