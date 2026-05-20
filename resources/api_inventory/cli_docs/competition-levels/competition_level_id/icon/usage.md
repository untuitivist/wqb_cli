# CLI 用法: `/competition-levels/{competition_level_id}/icon`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/competition-levels/{competition_level_id}/icon"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/competition-levels/{competition_level_id}/icon" --var competition_level_id=none --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/competition-levels/{competition_level_id}/icon" --var competition_level_id=none
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
