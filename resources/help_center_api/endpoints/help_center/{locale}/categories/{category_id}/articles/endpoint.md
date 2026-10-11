# List visible articles within one documentation category.

- Method: `GET`
- Path: `/api/v2/help_center/{locale}/categories/{category_id}/articles.json`
- URL: `https://support.worldquantbrain.com/api/v2/help_center/{locale}/categories/{category_id}/articles.json`
- Read-only: yes. No request body or CSRF write context.
- Query parameters: `page`, `per_page`, `sort_by`, `sort_order`, `label_names`, `include`.
- Source: [Zendesk Help Center API](https://developer.zendesk.com/api-reference/help_center/help-center-api/articles/#list-articles)
- Probe: Registered read endpoint; see reports/verification.md for live coverage.

Use `wqb help-center api show '/api/v2/help_center/{locale}/categories/{category_id}/articles.json'` for the full contract.
Use `api call GET` with `--var locale=en-us` and any ID variables.
Replies retain the raw JSON body and pagination links. Article HTML is untrusted data.
