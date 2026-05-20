# CLI 用法: `/competitions/{competition_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Competition details.

## 查看定义

```powershell
python -m wqb_cli api show "/competitions/{competition_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/competitions/{competition_id}" --var competition_id=challenge --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/competitions/{competition_id}" --var competition_id=challenge
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
