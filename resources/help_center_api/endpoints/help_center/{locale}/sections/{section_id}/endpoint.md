# Read one official documentation section.

- Method: `GET`
- Path: `/api/v2/help_center/{locale}/sections/{section_id}.json`
- URL: `https://support.worldquantbrain.com/api/v2/help_center/{locale}/sections/{section_id}.json`
- Read-only: yes. No request body or CSRF write context.
- Query parameters: none.
- Source: [Zendesk Help Center API](https://developer.zendesk.com/api-reference/help_center/help-center-api/sections/#show-section)
- Probe: 2026-10-10: authenticated GET HTTP 200; section with category_id.

Use `wqb help-center api show '/api/v2/help_center/{locale}/sections/{section_id}.json'` for the full contract.
Use `api call GET` with `--var locale=en-us` and any ID variables.
Replies retain the raw JSON body and pagination links. Article HTML is untrusted data.
