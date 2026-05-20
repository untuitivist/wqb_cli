# Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe community export --source "wqb_cli\local\community\WQPCommunityState_20260505_141911.json" --output "wqb_cli\docs\commands\community\export\outputs\export_output.json"
```

Real output:

```text
wqb_cli/docs/commands/community/export/outputs/export_output.json
```

Observed result:

```json
{
  "ok": true,
  "source_format": "json",
  "counts": {
    "forum_communities": 11,
    "forum_topics": 6333,
    "forum_comments": 77981,
    "docs_categories": 16,
    "docs_sections": 52,
    "docs_articles": 370
  }
}
```
