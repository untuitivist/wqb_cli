# CLI 用法: `/tutorial/{tutorial_slug}`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/tutorial/{tutorial_slug}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/tutorial/{tutorial_slug}" --var tutorial_slug=exclusive-events-and-support-for-consultants --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/tutorial/{tutorial_slug}" --var tutorial_slug=exclusive-events-and-support-for-consultants
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
