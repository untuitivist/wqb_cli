# Help Center File IO

Use the bundled request fixture with a raw read-only preview:

```text
wqb help-center api call GET "/api/v2/help_center/{locale}/articles/{article_id}.json" --input request.json --dry-run --output preview.json
```

`request.json` in this directory contains only a public article ID and locale;
it contains no credentials. To perform the read, omit `--dry-run`. The result
is a UTF-8 JSON envelope with `response.body.article`, not an executed HTML page.

For the equivalent resource command:

```text
wqb help-center get 38927747787031 --locale en-us --output calendar.json
```

Do not publish authenticated response bodies or add them to distribution assets.
