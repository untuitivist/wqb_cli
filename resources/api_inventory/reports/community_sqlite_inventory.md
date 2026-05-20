# Community SQLite Inventory

- SQLite path: `U:\Project\MainCode\3.Work\WQB\wqb_cli\wqb_core\dataset\forum\community.sqlite3`
- Exists: `True`

## `docs_articles`

- Type: `table`
- Rows: `370`
- Columns:
  - `category_id` `TEXT`
  - `section_id` `TEXT`
  - `article_id` `TEXT`
  - `title` `TEXT`
  - `url` `TEXT`
  - `author` `TEXT`
  - `datetime` `TEXT`
  - `article_content` `TEXT`
  - `last_crawled_at` `TEXT`
  - `raw_json` `TEXT`

## `docs_articles_fts`

- Type: `table`
- Rows: `370`
- Columns:
  - `category_id` ``
  - `section_id` ``
  - `article_id` ``
  - `title` ``
  - `author` ``
  - `article_content` ``

## `docs_articles_fts_config`

- Type: `table`
- Rows: `1`
- Columns:
  - `k` ``
  - `v` ``

## `docs_articles_fts_data`

- Type: `table`
- Rows: `80`
- Columns:
  - `id` `INTEGER`
  - `block` `BLOB`

## `docs_articles_fts_docsize`

- Type: `table`
- Rows: `370`
- Columns:
  - `id` `INTEGER`
  - `sz` `BLOB`

## `docs_articles_fts_idx`

- Type: `table`
- Rows: `77`
- Columns:
  - `segid` ``
  - `term` ``
  - `pgno` ``

## `docs_categories`

- Type: `table`
- Rows: `16`
- Columns:
  - `category_id` `TEXT`
  - `title` `TEXT`
  - `url` `TEXT`
  - `last_crawled_at` `TEXT`
  - `raw_json` `TEXT`

## `docs_sections`

- Type: `table`
- Rows: `52`
- Columns:
  - `category_id` `TEXT`
  - `section_id` `TEXT`
  - `title` `TEXT`
  - `url` `TEXT`

## `forum_comments`

- Type: `table`
- Rows: `77981`
- Columns:
  - `community_id` `TEXT`
  - `topic_id` `TEXT`
  - `comment_id` `TEXT`
  - `author` `TEXT`
  - `comment_time` `TEXT`
  - `vote_num` `INTEGER`
  - `comment_content` `TEXT`
  - `raw_json` `TEXT`

## `forum_comments_fts`

- Type: `table`
- Rows: `77981`
- Columns:
  - `community_id` ``
  - `topic_id` ``
  - `comment_id` ``
  - `author` ``
  - `comment_content` ``

## `forum_comments_fts_config`

- Type: `table`
- Rows: `1`
- Columns:
  - `k` ``
  - `v` ``

## `forum_comments_fts_data`

- Type: `table`
- Rows: `7534`
- Columns:
  - `id` `INTEGER`
  - `block` `BLOB`

## `forum_comments_fts_docsize`

- Type: `table`
- Rows: `77981`
- Columns:
  - `id` `INTEGER`
  - `sz` `BLOB`

## `forum_comments_fts_idx`

- Type: `table`
- Rows: `6406`
- Columns:
  - `segid` ``
  - `term` ``
  - `pgno` ``

## `forum_communities`

- Type: `table`
- Rows: `11`
- Columns:
  - `community_id` `TEXT`
  - `title` `TEXT`
  - `url` `TEXT`
  - `posts` `INTEGER`
  - `followers` `INTEGER`
  - `raw_json` `TEXT`

## `forum_topics`

- Type: `table`
- Rows: `6333`
- Columns:
  - `community_id` `TEXT`
  - `topic_id` `TEXT`
  - `title` `TEXT`
  - `url` `TEXT`
  - `comment_num` `INTEGER`
  - `post_content` `TEXT`
  - `last_crawled_at` `TEXT`
  - `raw_json` `TEXT`

## `forum_topics_fts`

- Type: `table`
- Rows: `6333`
- Columns:
  - `community_id` ``
  - `topic_id` ``
  - `title` ``
  - `post_content` ``

## `forum_topics_fts_config`

- Type: `table`
- Rows: `1`
- Columns:
  - `k` ``
  - `v` ``

## `forum_topics_fts_data`

- Type: `table`
- Rows: `3576`
- Columns:
  - `id` `INTEGER`
  - `block` `BLOB`

## `forum_topics_fts_docsize`

- Type: `table`
- Rows: `6333`
- Columns:
  - `id` `INTEGER`
  - `sz` `BLOB`

## `forum_topics_fts_idx`

- Type: `table`
- Rows: `2824`
- Columns:
  - `segid` ``
  - `term` ``
  - `pgno` ``

## `metadata`

- Type: `table`
- Rows: `2`
- Columns:
  - `key` `TEXT`
  - `value` `TEXT`
