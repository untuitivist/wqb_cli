# Community API verification

2026-09-22: successful authenticated reads for posts ordered by created_at/updated_at, topics, keyword search, comments and author sideloads. Native cursor pagination was verified. Returned next links use /api/v2/help_center/community/... aliases without .json; the client validates origin and canonical resource before following them.

SSO uses HTML Accept headers and the BRAIN user agent. Cookie domain/path information is preserved; signed redirects and CSRF values are not logged. BRAIN's existing authentication renewal is reused, with a bounded retry when the support endpoint redirects to the platform login page.

## 0.6.1 publishing correction

2026-09-22: the installed WQBRAIN `wqb community create --html` command created the user-approved [release announcement](https://support.worldquantbrain.com/hc/zh-cn/community/posts/43657620679319) and returned HTTP 201 with a post ID. Its original local PNG was registered through the CLI image-upload path (HTTP 201); a subsequent image GET returned HTTP 200 with the expected 372,981-byte PNG. Image HEAD returned 404, so GET is the verification evidence.

The published HTML page returned HTTP 200. The shared verification parser matched its title, complete body text and image references against the server's saved post. Zendesk sanitizes some HTML styles and expands relative image sources, so raw byte identity is not required.

The post's JSON GET returned 404, including canonical endpoint aliases and a new authenticated session. The cause of the JSON/page discrepancy is not established. The CLI preserves the JSON verification result and adds a separate `page_verification` when that read fails; it does not treat a failed read as permission to replay creation. The live create was sent exactly once. Comment, update and delete mutations remain untested live.

The initial image upload failed with HTTP 401 when it used the Help Center session API's CSRF token. The corrected client reads `HelpCenter.internal.current_session.shared_csrf_token` and `current_brand_id` from authenticated HTML, matching the current forum editor. Image upload uses the official ticket, binary-transfer and registration sequence. Signed upload URLs, tokens and cookies are omitted from receipts and packaged resources.

The corrected source passes 172 unit tests. Release verification includes offline HTML/image previews and independent wheel installation. Per-account API data and source-content snapshots are excluded from the published package.
