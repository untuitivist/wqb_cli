# CLI 用法: `/users/{user_id}`

- Methods: `GET`
- Sources: `platform_dynamic_capture, rocky-d/wqb`
- Description: User profile by id.

## 查看定义

```powershell
python -m wqb_cli api show "/users/{user_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users/{user_id}" --var user_id=JL40454 --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/{user_id}" --var user_id=JL40454
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
