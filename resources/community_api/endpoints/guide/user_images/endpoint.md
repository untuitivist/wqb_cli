# /api/v2/guide/user_images

Register a completed image upload and obtain its /hc/user_images/ path.

Methods: POST.

Source: https://developer.zendesk.com/api-reference/help_center/help-center-api/user_images/

https://static.zdassets.com/hc/assets/wysiwyg-8f31b01345d86b9077ebae6bc623dbbe.js

Mutating. Call only after the binary upload succeeds.

Use the returned relative path in post HTML. External and local image URLs are not a substitute.

Live verification: HTTP 201 on 2026-09-22; the registered image subsequently returned HTTP 200 and image/png.
