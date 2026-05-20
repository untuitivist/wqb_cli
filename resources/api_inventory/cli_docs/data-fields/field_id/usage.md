# CLI 用法: `/data-fields/{field_id}`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Data field details.

## 查看定义

```powershell
python -m wqb_cli api show "/data-fields/{field_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/data-fields/{field_id}" --var field_id=abnormal_news_sentiment_1d --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/data-fields/{field_id}" --var field_id=abnormal_news_sentiment_1d
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
