# WQB Research Desk

This directory contains the browser assets served by the local WQB application.
It is not a standalone mock and must be opened through the CLI so API requests,
run polling, authentication, model configuration, and approval actions work.

```powershell
wqb app
```

The server binds to `127.0.0.1:8765` by default. Use `wqb app --no-open` to
start it without opening the default browser.
