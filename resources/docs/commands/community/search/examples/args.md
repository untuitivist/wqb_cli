# Argument Example

Real command:

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\Scripts\wqb.exe community search alpha --limit 3 --output "wqb_cli\docs\commands\community\search\outputs\search_alpha_output.json"
```

Real output:

```text
wqb_cli/docs/commands/community/search/outputs/search_alpha_output.json
```

Observed result:

```json
{
  "ok": true,
  "query": "alpha",
  "scope": "all",
  "forum_topics": 3,
  "forum_comments": 3,
  "docs_articles": 3
}
```

