# community search

Search the online forum through the native Community Posts search endpoint.

```text
wqb community search wqb_cli --sort updated_at --limit 10
wqb community search wqb_cli --topic 18910956638743 --page 2 --limit 10
```

--sort supports created_at and updated_at. Native date filters are available through --param. Pagination links and raw results are retained. Upstream search has a 1000-result cap; use sqlitecom sync to build a complete local index.

For the old offline behavior use sqlitecom search instead, including --scope, --author, --since and --sort.
