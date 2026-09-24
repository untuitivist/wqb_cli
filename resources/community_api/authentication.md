# Community authentication

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
`cf-mitigated: challenge`. It stops immediately without password refresh, proxy
switching or challenge solving. Use a normal browser to verify the account. If the
CLI remains challenged, ask platform support about supported API authentication;
browser verification is not guaranteed to carry over to an HTTP client.
`community_login_required` identifies a restricted/login redirect.
`support_sso_failed` identifies other SSO HTTP failures.

Live observation on 2026-09-24: BRAIN login 201; Zendesk /access/jwt 302;
support /access/return_to 302; /hc/en-us 403 with cf-mitigated: challenge.
No authenticated read or write success is claimed for that session.

Official Help Center sessions documentation:
https://developer.zendesk.com/api-reference/help_center/help-center-api/help_center_sessions/
This endpoint also serves anonymous users, so receiving its CSRF token alone is
not proof of account authentication. Its token is not a substitute for the shared
CSRF token used by existing community write support.
