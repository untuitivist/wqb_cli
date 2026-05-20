# community Notes

The command layer uses `wqb_cli.core.community_store`.
It does not depend on `wqb_core`.

Current source formats:

- `WQPCommunityState_*.json`
- `WQPCommunityState_*.wqcs`

Runtime data lives under `wqb_cli/local/community/` by default.
That directory is ignored by Git for publish safety.

Search is local and does not call `api.worldquantbrain.com`.
It is intended for fast lookup of forum and documentation content while designing alphas or explaining platform concepts.

The current search implementation uses SQLite `LIKE` queries over normalized tables.
The SQLite schema also builds FTS tables, but this CLI command does not yet expose FTS-specific ranking.
