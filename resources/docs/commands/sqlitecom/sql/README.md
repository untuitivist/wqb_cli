# sqlitecom sql

Run one read-only SQLite statement. Alias: sqlitecom query. Use --file for UTF-8 SQL or --sql for an inline statement. Named parameters use --param name=value; JSON numbers, booleans and null are parsed, while other values remain strings.

Example author_posts.sql:

```sql
SELECT topic_id, title, url,
       json_extract(raw_json, '$.datetime') AS created_at
FROM forum_topics
WHERE json_extract(raw_json, '$.author') = :author
ORDER BY created_at DESC;
```

```text
wqb sqlitecom sql --sqlite community.sqlite3 --file author_posts.sql --param author=JL40454 --max-rows 100 --output posts.json
wqb sqlitecom schema --sqlite community.sqlite3
```

The response includes columns, positional rows, row_count and truncated. Duplicate column names remain unambiguous because rows are arrays. Default output is limited to 200 rows (maximum 10000); --timeout defaults to 10 seconds and interrupts long-running SQL. SELECT, CTEs, joins, aggregates and SQLite JSON functions are supported. An authorizer and a read-only database connection reject writes, ATTACH, extension loading and multiple statements. Use schema for table definitions.
