# /api/v2/guide/user_images/uploads

Create a temporary signed upload URL and token for one community image.

Methods: POST.

Source: https://developer.zendesk.com/api-reference/help_center/help-center-api/user_images/

https://static.zdassets.com/hc/assets/wysiwyg-8f31b01345d86b9077ebae6bc623dbbe.js

Mutating. Follow with a binary PUT to the returned signed URL using only the returned upload headers.

The temporary upload token and signed URL must not enter public logs.

Live verification: Successful authenticated upload preparation using shared_csrf_token; bytes transferred and image registered on 2026-09-22.
