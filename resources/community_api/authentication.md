# Community authentication

## Request headers

Default sessions identify themselves as `wqb-cli/<package version>`. SSO redirect
pages request HTML/XHTML; identity validation and API calls request JSON.
Both specify `Accept-Language: en-US,en;q=0.9`, matching the SSO landing
locale. These are content-negotiation settings, not a browser identity or a
solution to Cloudflare challenges. No Chrome fingerprint or browser headers are
emulated. An injected session retains its own User-Agent.

## Persistent sessions

Validated community cookies are stored separately from BRAIN cookies in
`local/auth/community_sessions.sqlite3`. Treat this file as private authentication
data; it is excluded from release artifacts. Profiles are hashed from the configured
email, configuration path and BRAIN cookie path. When no configured identity can be
resolved, persistent caching is disabled instead of mixing accounts.

Only known Zendesk session cookies from their original allowed domains are retained,
including path, expiry, secure and host/domain flags. Browser-challenge cookies and
BRAIN API credentials are not copied to the cache. Session cookies without an expiry
have a local maximum idle age of six hours. Every new client validates the saved
forum user with `GET /api/v2/users/me.json` before reuse. Identity requires a positive
user ID and the end-user, agent or admin role. SSO requests this API as its return
target; a help-center HTML redirect is normalized to the identity API. Its
`user.authenticity_token` is retained only in memory for writes and is never saved
in the session cache or included in authentication command output. A new session
obtains a fresh token from its verified identity response.
No JavaScript is evaluated. A missing or different user identity causes fresh SSO.
An anonymous HTTP 200 response never establishes an authenticated session.

Successful requests save rotated cookies. Expiry invalidates the cache and renews
once for reads. Revision-checked transactions prevent older clients from overwriting
or resurrecting a newer/invalidated session. Temporary validation outages preserve
the cache. An unreadable/unwritable cache is nonfatal to otherwise successful SSO.
`community auth` reports `session_cache`: reused, saved, miss, disabled, or a
diagnostic such as read_failed/write_failed/concurrent_update. It never prints cookies.

Run `wqb community auth --max-wait-seconds 30` to exercise the normal SSO flow.
The command changes only authentication state; it does not create a community post.
`--dry-run` performs no authentication or HTTP requests.

The BRAIN session and Zendesk session are separate. Reads that receive 401, 403 or
302 can renew SSO once. Post-page verification and write-context reads use the same
bounded renewal policy. A failed refresh clears authentication/CSRF state.
Login and support endpoint 429 responses honor Retry-After with a bounded retry
count and sleep budget; SSO redirects also retry transient 5xx responses.
The sleep budget applies per BRAIN request phase and across the SSO redirect loop;
it is not a wall-clock deadline for all network requests.

Errors contain `code`, `stage`, and `status_code` without cookies, JWTs or CSRF tokens.
`browser_verification_required` identifies a response carrying
`cf-mitigated: challenge`. A challenged HTML post or write-context page does not
invalidate a separately validated API session. The challenged operation stops
immediately without password refresh, proxy
switching or challenge solving. Use a normal browser to verify the account. If the
CLI remains challenged, ask platform support about supported API authentication;
browser verification is not guaranteed to carry over to an HTTP client.
`community_login_required` identifies a restricted/login redirect.
`support_sso_failed` identifies other SSO HTTP failures.

Live diagnosis on 2026-09-25: after Zendesk /access/jwt 302 and support
/access/return_to 302, the current-user API and a restricted forum post returned
200 with the authenticated account. Independently, /hc/en-us returned 403 with
cf-mitigated: challenge. The previous HTML-based identity check rejected a valid
API session and discarded its cookies. JSON identity verification removes that
unnecessary dependency; it does not solve HTML-page challenges or assert write access.

Official Help Center sessions documentation:
https://developer.zendesk.com/api-reference/help_center/help-center-api/help_center_sessions/
This endpoint also serves anonymous users, so receiving its CSRF token alone is
not proof of account authentication. Its token returned HTTP 401 for image upload
preparation on both 2026-09-22 and 2026-10-24, and is not used by this client.

## API write context

Zendesk documents `user.authenticity_token` from `/api/v2/users/me.json` as the
token to send in `X-CSRF-Token` for cookie-authenticated writes:
https://developer.zendesk.com/documentation/help_center/help-center-api/secured-requests/

On 2026-10-24, the authenticated identity API returned 200 and image upload
preparation with this token returned 201, while the editor/home HTML returned a
403 challenge. The CLI now separates API write authentication from HTML brand
discovery. This removes the unnecessary HTML dependency; it does not solve or
disable the challenge. Mutations still have no automatic retry.

User-image registration additionally requires the site's brand ID. A verified
`--brand-id` on `community create`, `update` or `image-upload` supplies this public
site metadata without reading the editor page. Without it, the existing HTML
lookup remains available and stops immediately on a challenge. Missing brand IDs
are not guessed from topic/community IDs; registration without a brand returned
400 in the live diagnostic. An HTML challenge preserves the independently
validated API session and identity token.
