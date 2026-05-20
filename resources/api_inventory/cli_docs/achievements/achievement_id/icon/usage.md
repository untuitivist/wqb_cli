# CLI 用法: `/achievements/{achievement_id}/icon`

- Methods: `GET`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/achievements/{achievement_id}/icon"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/achievements/{achievement_id}/icon" --var achievement_id=ALPHA_PERF_EXCELLENT --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/achievements/{achievement_id}/icon" --var achievement_id=ALPHA_PERF_EXCELLENT
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
