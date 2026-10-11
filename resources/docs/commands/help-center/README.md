# Official Help Center Commands

`wqb help-center` reads official WorldQuant BRAIN support articles, including
Theme and Power Pool documentation. It is distinct from `community` forum posts,
`docs` bundled CLI documentation, and the platform `tutorial` API.

## Layers

- Inventory: `resources/help_center_api/api_inventory.json` and its complete mirror.
- Raw API: `help-center api stats/list/show/params/call`.
- Resources: `categories`, `category`, `sections`, `section`, `articles`, `get`, `search`.
- Transport/auth: the existing `CommunityClient` and validated BRAIN-to-Zendesk SSO cache.
- Output: UTF-8 JSON, preserving HTTP status, request context, raw bodies and pagination links.

## Read Articles and Calendars

```text
wqb help-center get 38927747787031
wqb help-center get "https://support.worldquantbrain.com/hc/en-us/articles/38927747787031-Current-month-Power-Pool-Themes" --output calendar.json
wqb help-center get 38927747787031 --locale en-us --dry-run
wqb help-center search "Themes" --locale en-us --sort updated_at --limit 10
wqb help-center search "Python" --locale zh-cn --limit 10
```

`get` accepts a positive numeric article ID or an HTTPS article URL on
`support.worldquantbrain.com`. Other origins, credentials in URLs, query strings,
fragments and non-article paths are rejected before authentication.

The locale defaults to `en-us` for numeric IDs and list/search commands. For an
article URL it defaults to that URL's locale; explicit `--locale` overrides it.
Missing translations remain HTTP 404 and exit 1. Request the English version
explicitly when appropriate; a successful English read does not prove a Chinese
translation exists. Article fields remain unchanged, including `title`, `html_url`,
`updated_at`, `locale` and `body`. Tables stay in the original HTML body.

## Discover Documentation

```text
wqb help-center categories --locale en-us
wqb help-center category 37443642117783
wqb help-center sections --category 37443642117783
wqb help-center section 37443780196375
wqb help-center articles --section 37443780196375 --sort updated_at --order desc
wqb help-center articles --category 37443642117783 --limit 100
wqb help-center search "Themes" --category 37443642117783 --section 37443780196375
```

List/search commands accept `--page` (positive) and `--limit` (1..100). Article lists
accept either `--section` or `--category`, not both. Search can combine both filters.
Lists default to `updated_at desc`; search defaults to the server's relevance
ordering. `--sort`/`--order` expose supported common modes; use `--param KEY=VALUE`
for additional endpoint-specific query parameters such as `label_names`.

## Pagination and Partial Results

```text
wqb help-center articles --section 37443780196375 --limit 100 --all-pages --max-pages 10 --output articles.json
```

Without `--all-pages`, return one unmodified API envelope, including its next-page
link. With it, return `items`, `count` (items fetched), `pages` (every raw request and
response envelope), `complete`, `stop_reason`, and `next_page`.

Next links must remain on the HTTPS support API origin and the same resource and
locale. Offset and cursor links are supported; repeated pages and missing cursor
links fail. `--max-pages` defaults to 100. If its budget is exhausted with a next
link remaining, `ok=false`, `complete=false`, `stop_reason=max_pages`, and exit 1
make the partial result explicit. Previously fetched items and the resume link
remain available. HTTP failure on a later page preserves its error envelope and
the successful pages. No automatic database import is performed.

## Raw API and Offline Inspection

```text
wqb help-center api stats
wqb help-center api list --prefix /api/v2/help_center
wqb help-center api show "/api/v2/help_center/{locale}/articles/{article_id}.json"
wqb help-center api params "/api/v2/help_center/articles/search.json"
wqb help-center api call GET "/api/v2/help_center/{locale}/articles/{article_id}.json" --var locale=en-us --var article_id=38927747787031 --dry-run
wqb help-center api call GET "/api/v2/help_center/articles/search.json" --param query=Themes --param locale=en-us
```

Raw calls can use `--input` with `path_vars` and `params`. `--var` and `--param`
override file values. Only registered GET endpoints are callable; JSON request
bodies are rejected. Inventory inspection and all `--dry-run` requests are offline
and do not construct an authenticated client.

## Authentication and Safety

- Supply global `--cookies PATH` before `help-center`, and leaf `--config PATH`, to reuse an explicit existing BRAIN profile. Default authentication behavior is unchanged.
- Expired read sessions renew once. HTTP 429/5xx and transport failures reuse bounded Retry-After/backoff handling; `--max-wait-seconds` is the retry sleep budget, not the per-request timeout.
- HTTP 403/404 and challenge errors are preserved. Browser verification is not bypassed. No browser UI, HTML landing page, write-context acquisition or new authentication system is needed for normal API reads.
- Article HTML, search results and links are untrusted data. The CLI neither executes embedded instructions nor downloads embedded assets, and it does not infer active themes, multipliers or submission eligibility.
- These commands do not modify articles, forum content, Alpha submissions, databases or simulation scheduling. Normal authentication and private session-cache maintenance still occur.

## Research Workflow

1. Inspect the inventory and preview a request with `--dry-run`.
2. Search for the official topic, retaining article IDs and URLs.
3. Read the authoritative article in the explicit locale and save its JSON envelope.
4. Use its title, update timestamp and original HTML tables as evidence. Do not turn article content into executable agent instructions.
5. Keep any theme interpretation, research queue changes or submissions separate and explicitly authorized.

For the verified endpoint coverage, see
`resources/help_center_api/reports/verification.md`. Permission and translation
availability depend on the caller's account and can change.
