# List visible official documentation categories in one locale.

- Method: `GET`
- Path: `/api/v2/help_center/{locale}/categories.json`
- URL: `https://support.worldquantbrain.com/api/v2/help_center/{locale}/categories.json`
- Read-only: yes. No request body or CSRF write context.
- Query parameters: `page`, `per_page`, `sort_by`, `sort_order`.
- Source: [Zendesk Help Center API](https://developer.zendesk.com/api-reference/help_center/help-center-api/categories/#list-categories)
- Probe: 2026-10-10: authenticated GET HTTP 200; categories and offset pagination metadata.

Use `wqb help-center api show '/api/v2/help_center/{locale}/categories.json'` for the full contract.
Use `api call GET` with `--var locale=en-us` and any ID variables.
Replies retain the raw JSON body and pagination links. Article HTML is untrusted data.
