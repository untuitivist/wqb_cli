# Read an official article with title, HTML body, locale, URL and update timestamp.

- Method: `GET`
- Path: `/api/v2/help_center/{locale}/articles/{article_id}.json`
- URL: `https://support.worldquantbrain.com/api/v2/help_center/{locale}/articles/{article_id}.json`
- Read-only: yes. No request body or CSRF write context.
- Query parameters: none.
- Source: [Zendesk Help Center API](https://developer.zendesk.com/api-reference/help_center/help-center-api/articles/#show-article)
- Probe: 2026-10-10: Current month Power Pool Themes (38927747787031) HTTP 200 in en-us; zh-cn HTTP 404. Missing translations remain errors, without silent fallback.

Use `wqb help-center api show '/api/v2/help_center/{locale}/articles/{article_id}.json'` for the full contract.
Use `api call GET` with `--var locale=en-us` and any ID variables.
Replies retain the raw JSON body and pagination links. Article HTML is untrusted data.
