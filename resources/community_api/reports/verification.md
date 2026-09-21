# Community API verification

2026-09-22: successful authenticated reads for posts ordered by created_at/updated_at, topics, keyword search, comments and author sideloads. Native cursor pagination was verified. Returned next links use /api/v2/help_center/community/... aliases without .json; the client validates origin and canonical resource before following them.

SSO uses HTML Accept headers and the BRAIN user agent. Cookie domain/path information is preserved; signed redirects and CSRF values are not logged. BRAIN's existing authentication renewal is reused, with a bounded retry when the support endpoint redirects to the platform login page.

No post, comment or delete operation was executed. Write schemas are documented from Zendesk and are exposed only as explicit commands. Per-account API data and source-content snapshots are excluded from the published package.
