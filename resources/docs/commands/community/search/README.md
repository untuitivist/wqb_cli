# community search

Search the local community SQLite database.

Command:

```powershell
wqb community search <query> --scope <scope> --limit <n> --output <output.json>
```

Scopes:

- `all`
- `forum`
- `topics`
- `comments`
- `docs`
- `articles`

Default SQLite path:

```text
wqb_cli/local/community/community.sqlite3
```

Use `--sqlite <path>` to search another database.
