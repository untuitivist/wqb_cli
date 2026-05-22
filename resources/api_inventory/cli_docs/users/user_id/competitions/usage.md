# CLI 用法: `/users/{user_id}/competitions`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: User competitions by id.

## 查看定义

```powershell
python -m wqb_cli api show "/users/{user_id}/competitions"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/users/{user_id}/competitions" --var user_id=JL40454
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/{user_id}/competitions" --var user_id=JL40454
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
