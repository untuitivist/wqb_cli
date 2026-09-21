# community

Online access to https://support.worldquantbrain.com/hc/zh-cn/community.

Use list, topics, topic, get, comments, search, user-posts or user-comments for live reads. Results retain the JSON body, HTTP status, pagination and retry information. --param adds native query parameters; --output writes JSON.

```text
wqb community list --sort updated_at --limit 10
wqb community list --topic 18910956638743 --limit 10
wqb community get 41706827651991
wqb community comments 41706827651991
wqb community search wqb_cli --sort created_at
wqb community user-posts me
wqb community api stats
wqb community api show /api/v2/community/posts.json
wqb community api params /api/v2/community/posts.json
wqb community api call GET /api/v2/community/posts.json --param sort_by=updated_at
```

The packaged registry is resources/community_api/api_inventory.json. Native API access and high-level commands use one CommunityClient; sqlitecom sync reuses it. Forum topics are sections; forum posts are the legacy database's forum_topics rows.

Authentication reuses BRAIN credentials/cookies, follows support SSO with HTML request headers, and preserves cookie domains in a separate forum session. --config selects the BRAIN authentication configuration. Expired sessions have bounded renewal; read requests honor Retry-After with a bounded wait budget.

create/update/delete and comment-create/comment-update/comment-delete are explicit remote mutations. Supply the native JSON body through --input or --json for create/update. --dry-run previews any request without authentication or HTTP. The client obtains CSRF before writes and never automatically resends a write, including after 429 or a timeout. Actual write permissions and responses have not been live-tested in this release.

Local commands moved to sqlitecom in 0.6.0. community search now searches online; use sqlitecom search for the existing database. Local export/import is now sqlitecom import and merges records rather than replacing the entire database.
