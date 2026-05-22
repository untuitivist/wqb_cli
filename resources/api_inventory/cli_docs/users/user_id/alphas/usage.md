# CLI 用法: `/users/{user_id}/alphas`

- Methods: `OPTIONS`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/users/{user_id}/alphas"
```

## 调用方式

### `OPTIONS`

Command:

```powershell
python -m wqb_cli api call OPTIONS "/users/{user_id}/alphas" --var user_id=JL40454
```

实际执行:

```powershell
python -m wqb_cli api call OPTIONS "/users/{user_id}/alphas" --var user_id=JL40454
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
