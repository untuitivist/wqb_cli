SELECT topic_id, title, url, json_extract(raw_json, '$.datetime') AS created_at
FROM forum_topics
WHERE json_extract(raw_json, '$.author') = :author
ORDER BY created_at DESC;
