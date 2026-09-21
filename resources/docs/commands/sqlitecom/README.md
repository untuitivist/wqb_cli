# sqlitecom

Local community storage with a durable incremental sync worker. All commands except sync run without network access or authentication.

Choose a database with --sqlite. WQB_COMMUNITY_SQLITE provides an environment default; otherwise the historical package-local community.sqlite3 path is used.

```text
wqb sqlitecom sync --sqlite community.sqlite3 --since 2026-09-17 --log sync.log
wqb sqlitecom status --sqlite community.sqlite3
wqb sqlitecom search --sqlite community.sqlite3 --author JL40454 --scope topics --sort newest
wqb sqlitecom get 41706827651991 --sqlite community.sqlite3
wqb sqlitecom import --source export.json --sqlite community.sqlite3
wqb sqlitecom schema --sqlite community.sqlite3
wqb sqlitecom sql --sqlite community.sqlite3 --file author_posts.sql --param author=JL40454
```

sync resumes saved pages and unfinished post/comment work automatically. --max-pages bounds new index pages in one invocation and leaves a resumable PAUSED run. Defaults: 48-hour overlap, seven-day comment refresh age. --since limits the initial scan; without a prior watermark or since, the first run builds a full baseline. --reconcile scans the full index to revisit old comments and older visibility changes. Invoke it periodically because editing an old comment may not update the parent post's timestamp.

Completed boundaries advance only after selected posts and all fetched comments are stored. A writer lock prevents overlapping sync/import processes. Short SQLite transactions leave read-only research access available between writes. Failed work remains pending. Remote omissions/deletions are not interpreted as instructions to delete stored history or documentation.

Plugin JSON/WQCS imports remain supported and merge into existing tables. The legacy names forum_communities/forum_topics/forum_comments are retained for SQL compatibility. Source timestamps, original HTML, API metadata, author labels, sync receipts and existing full-text indexes remain available.
