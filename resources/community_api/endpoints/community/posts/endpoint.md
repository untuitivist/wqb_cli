# /api/v2/community/posts.json

List posts or explicitly create a post.

Methods: GET, POST.

Source: https://developer.zendesk.com/api-reference/help_center/help-center-api/posts/

Use community api show/params for the exact JSON contract; community api call shares the authenticated transport with resource commands and sqlitecom sync.

2026-09-22: installed `wqb community create --html` returned HTTP 201 for an authorized post with an uploaded image. The HTML page returned 200 and matched title, body and image references; the image GET returned 200. The post JSON GET returned 404. The CLI retains that API failure and separately verifies the saved HTML page without repeating the write.
