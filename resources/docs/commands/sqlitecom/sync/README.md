# sqlitecom sync

See sqlitecom for full behavior. A standard run is `wqb sqlitecom sync --sqlite community.sqlite3 --log sync.log`. Re-run it to resume saved work or incrementally update after completion. Use `--max-pages 1` for a bounded trial, `--since 2026-09-17` for an initial date boundary, and `--reconcile` for a periodic complete-index scan. Do not use online search as a substitute for the posts index.
