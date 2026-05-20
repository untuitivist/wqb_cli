# CLI 用法: `/consultant/boards/leader`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Consultant leaderboard.

## 查看定义

```powershell
python -m wqb_cli api show "/consultant/boards/leader"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/consultant/boards/leader" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/consultant/boards/leader"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
