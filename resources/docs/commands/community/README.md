# community

Local community database commands.

The community database is built from WebDataScope community data and stored as SQLite.
Source plugin: [leetesla/WebDataScope-WorldQuant](https://github.com/leetesla/WebDataScope-WorldQuant)

Data source boundary:

- This command does not call `api.worldquantbrain.com`.
- It reads WebDataScope community exports from `wqb_cli/local/community/`.
- The exports are derived from plugin/browser cached community data.

The CLI currently exposes three operations:

- `wqb community export`: import `WQPCommunityState_*.json` or `WQPCommunityState_*.wqcs` into SQLite.
- `wqb community stats`: inspect local table counts.
- `wqb community search`: search forum topics, forum comments, and documentation articles.

Default SQLite path:

```text
wqb_cli/local/community/community.sqlite3
```

Expected local layout:

```text
wqb_cli/local/community/
  WQPCommunityState_*.json
  WQPCommunityState_*.wqcs
  community.sqlite3
```

Use `--sqlite <path>` when testing against another generated database.
Do not commit generated SQLite files because the database is large local data.
