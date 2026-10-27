# Community API verification

2026-09-22: successful authenticated reads for posts ordered by created_at/updated_at, topics, keyword search, comments and author sideloads. Native cursor pagination was verified. Returned next links use /api/v2/help_center/community/... aliases without .json; the client validates origin and canonical resource before following them.

SSO uses HTML Accept headers and the BRAIN user agent. Cookie domain/path information is preserved; signed redirects and CSRF values are not logged. BRAIN's existing authentication renewal is reused, with a bounded retry when the support endpoint redirects to the platform login page.

## 0.6.1 publishing correction

2026-09-22: the installed WQBRAIN `wqb community create --html` command created the user-approved [release announcement](https://support.worldquantbrain.com/hc/zh-cn/community/posts/43657620679319) and returned HTTP 201 with a post ID. Its original local PNG was registered through the CLI image-upload path (HTTP 201); a subsequent image GET returned HTTP 200 with the expected 372,981-byte PNG. Image HEAD returned 404, so GET is the verification evidence.

The published HTML page returned HTTP 200. The shared verification parser matched its title, complete body text and image references against the server's saved post. Zendesk sanitizes some HTML styles and expands relative image sources, so raw byte identity is not required.

The post's JSON GET returned 404, including canonical endpoint aliases and a new authenticated session. The cause of the JSON/page discrepancy is not established. The CLI preserves the JSON verification result and adds a separate `page_verification` when that read fails; it does not treat a failed read as permission to replay creation. The live create was sent exactly once. Comment, update and delete mutations remain untested live.

The initial image upload failed with HTTP 401 when it used the Help Center session API's CSRF token. The corrected client reads `HelpCenter.internal.current_session.shared_csrf_token` and `current_brand_id` from authenticated HTML, matching the current forum editor. Image upload uses the official ticket, binary-transfer and registration sequence. Signed upload URLs, tokens and cookies are omitted from receipts and packaged resources.

The corrected source passes 172 unit tests. Release verification includes offline HTML/image previews and independent wheel installation. Per-account API data and source-content snapshots are excluded from the published package.

## API-only write context correction (2026-10-24)

The current-user API returned HTTP 200 with an authenticated identity and the
documented `user.authenticity_token`, while the HTML editor returned a 403
challenge. The Help Center sessions token still returned 401 for upload
preparation. The identity token returned 201 through the same official upload
endpoint without browser headers, challenge cookies or alternate proxies.

After supplying the site's brand ID from a previously saved official page, the
installed `community create --html --brand-id ...` command uploaded the approved
PNG, registered its user-image path with HTTP 201, and created the approved post
exactly once with HTTP 201. The create response retained the complete body text,
eight section headings, five tables and the registered image reference. It
retained 167 of the input's 174 inline style attributes.

Independent visibility remains unconfirmed at this checkpoint: single-post API
reads returned 404, author/topic listings did not yet contain the post, and the
image GET returned 403. The client preserves the created ID and does not resend
creation. These results verify the write path, not public visibility or a
moderation decision. No cause is inferred from a 404 alone.

The change passed 85 community tests and 31 Help Center tests. The installed
package uses the normal WQBRAIN site-packages path; all 46 unrelated Python
runtime modules matched their pre-install normalized source hashes. Private
diagnostic data, credentials and publication receipts are excluded from the wheel.
