# Local Data

community reads the live support.worldquantbrain.com forum. sqlitecom stores and queries community content locally; sync is its only network operation. scope still reads local WebDataScope data_all files.

```text
wqb sqlitecom import --source export.json --sqlite community.sqlite3
wqb sqlitecom sync --sqlite community.sqlite3 --log sync.log
wqb sqlitecom stats --sqlite community.sqlite3
wqb sqlitecom search alpha --sqlite community.sqlite3 --limit 3
wqb scope files
wqb scope list
```

Existing WebDataScope JSON/WQCS imports remain valid. Incremental sync removes the requirement to manually download a fresh plugin export before every research session. Imports and sync preserve documentation tables and omitted records.

Database files, cookies, logs and exported content are user-local runtime data and are excluded from release packages. Packaged API inventories and command documentation contain no account snapshots.
