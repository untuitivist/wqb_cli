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

## Publish HTML and images

```text
wqb community create --html post.html --title "Research notes" --topic 18910956638743 --dry-run
wqb community create --html post.html --title "Research notes" --topic 18910956638743 --prepared-output prepared.json --output published.json
wqb community update POST_ID --html revised.html --output updated.json
wqb community image-upload chart.png --output image.json
```

Use a UTF-8 HTML body file. With `--html`, local `<img src="chart.png">` files are resolved relative to that file's directory and uploaded automatically. Matching image links are replaced too; other HTML is preserved. Images must be PNG, JPEG, GIF or WebP, at most 2,000,000 bytes each. All referenced files are checked before uploading. External images and files outside the input directory are rejected; existing forum `/hc/user_images/...` images are reused.

The default image receipt file is `post.html.assets.json`. Override it with `--assets-manifest`; it caches completed uploads by SHA-256 so a retry does not upload the same image again. Keep it with the source HTML. `--prepared-output` saves the exact JSON sent after image paths are replaced. The response includes the published post and a separate JSON GET `verification`. If that read fails, the CLI checks the saved HTML page and returns `page_verification` with title, body and image comparisons. These are separate results: a new post can be visible on its page while the JSON endpoint returns 404. Inspect the saved post URL or retry its GET; do not create it again.

HTML creation requires `--title` and `--topic` and does not notify subscribers unless `--notify-subscribers` is supplied. Update changes only supplied fields. Native JSON remains supported via `--input` or `--json`; add `--upload-images` to prepare local images in JSON input.

`--dry-run` validates files and previews requests without authentication, uploads or HTTP. Actual publishing is explicit. The client uses the forum page's `shared_csrf_token` and brand context; the Help Center session API's different CSRF token cannot authorize these writes. Image upload follows Zendesk's upload-ticket, byte-transfer and registration steps, without exposing signed URLs or copying authentication cookies to the upload host.

`create/update/delete` and comment commands never automatically resend a write, including after 429 or a timeout. Inspect the target before retrying any unknown outcome. Live verification is recorded in `resources/community_api/reports/verification.md`; it does not imply permission to use every mutation.

Local commands moved to sqlitecom in 0.6.0. community search now searches online; use sqlitecom search for the existing database. Local export/import is now sqlitecom import and merges records rather than replacing the entire database.
