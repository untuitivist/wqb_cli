# Help Center API Verification - 2026-10-10

## Scope

Verified through the native `python -m wqb_cli help-center` entry point in an
isolated 0.6.2 source checkout, with an existing BRAIN cookie/config profile.
Only Help Center GET requests were performed. The existing community SSO and
identity/cache transport was reused. No browser UI, article/forum writes,
Alpha submissions, database imports or simulation changes were performed.

Raw authenticated response bodies remain in private ignored `local/` storage;
they are not included in the repository or distribution. This report records
only endpoint coverage and non-secret status metadata.

## Live Endpoint Coverage

| Registered GET path | Native command | Result |
| --- | --- | --- |
| `/api/v2/help_center/{locale}/categories.json` | `help-center categories --limit 1` | 200 |
| `/api/v2/help_center/{locale}/categories/{category_id}.json` | `help-center category 37443642117783` | 200 |
| `/api/v2/help_center/{locale}/categories/{category_id}/sections.json` | `help-center sections --category 37443642117783 --limit 1` | 200 |
| `/api/v2/help_center/{locale}/sections.json` | `help-center sections --limit 1` | 200 |
| `/api/v2/help_center/{locale}/sections/{section_id}.json` | `help-center section 37443780196375` | 200 |
| `/api/v2/help_center/{locale}/articles.json` | `help-center articles --limit 1` | 200 |
| `/api/v2/help_center/{locale}/articles/{article_id}.json` | `help-center get 38927747787031` | 200 |
| `/api/v2/help_center/{locale}/sections/{section_id}/articles.json` | `help-center articles --section 37443780196375 --limit 1` | 200 |
| `/api/v2/help_center/{locale}/categories/{category_id}/articles.json` | `help-center articles --category 37443642117783 --limit 1` | 200 |
| `/api/v2/help_center/articles/search.json` | `help-center search Themes --sort updated_at --limit 1` | 200 |

All localized success probes used `en-us`. The article probe returned
`Current month Power Pool Themes`, `updated_at=2026-10-09T02:15:54Z`, with the
original HTML body. A separate raw `api call GET` of the same article also
returned 200.

The explicit `zh-cn` version of that article returned 404, `ok=false`, and exit 1.
No English fallback or redundant authentication was triggered by the 404.
This confirms locale-specific availability, not that every account or article
supports the same languages.

## Pagination

- Section article collection: `--limit 5 --all-pages --max-pages 10` fetched 12 articles across three pages, `complete=true`, exit 0.
- Category section collection: the same options fetched three sections on one page, `complete=true`, exit 0.
- Search with `--limit 1 --all-pages --max-pages 2` retained two result pages, `complete=false`, `stop_reason=max_pages`, a resume link and exit 1, as expected.
- Fifteen native CLI verification cases, including the expected 404 and partial-result exit 1, all matched their expected outcomes.

## Automated Regression

The full offline `unittest` suite passed 253 tests, including 31 dedicated Help
Center tests and a subprocess CLI/doc-discovery smoke test. Coverage includes:

- inventory consistency, locale/ID validation and offline request previews;
- preservation of article HTML and failed HTTP envelopes;
- GET-only enforcement before authentication, including raw/direct transport calls;
- bounded 429/5xx retry handling, one expiry refresh, persistent 403, missing translations and browser challenges;
- offset/cursor pagination, budget exhaustion, later HTTP failure, repeated links, missing cursor links, changed query/locale/filter links and untrusted origins/resources;
- existing forum publishing, authentication/session caching, SQLite and simulation command behavior.

Live coverage is an observation at this date, not a promise of future access.

## Distribution Verification

Both `wqb_cli-0.6.2-py3-none-any.whl` and `wqb_cli-0.6.2.tar.gz` built successfully.
Archive checks confirmed all ten endpoint contracts, both inventories and command
documentation are included, without `local/`, runtime databases, credentials or
live verification logs. New packaged source/resource files use UTF-8 without BOM.

An isolated extraction of the built wheel reported `wqb 0.6.2`, exposed ten GET
endpoints, loaded the bundled Help Center documentation and read the PPA calendar
with HTTP 200. The installed research CLI was not overwritten and no remote
package release was performed.
