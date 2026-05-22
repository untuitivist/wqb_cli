# CLI 用法: `/competitions/{competition_id}/agreement`

- Methods: `GET, POST`
- Sources: `observed_platform`
- Description: Competition agreement.

## 查看定义

```powershell
python -m wqb_cli api show "/competitions/{competition_id}/agreement"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/competitions/{competition_id}/agreement" --var competition_id=challenge
```

实际执行:

```powershell
python -m wqb_cli api call GET "/competitions/{competition_id}/agreement" --var competition_id=challenge
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/competitions/{competition_id}/agreement" --var competition_id=challenge
```


```powershell
python -m wqb_cli api call POST "/competitions/{competition_id}/agreement" --var competition_id=challenge
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
