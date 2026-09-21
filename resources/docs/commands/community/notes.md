# Online forum notes

Online Community API operations are separate from the BRAIN simulation API. The forum has its own SSO session and, for explicit writes, a CSRF token. Do not log signed SSO URLs or cookies.

GET reads can retry transient failures and renew an expired session. POST/PUT/DELETE are sent once. A transport failure during a write reports an unknown outcome; inspect the target before manually retrying.

Search is limited by the upstream search API (up to 1000 matches) and must not be used as the synchronization index. sqlitecom sync uses the posts list with cursor pagination and updated_at ordering.
