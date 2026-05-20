# CLI 用法: `/users/self/activities/pyramid-alphas`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Current user's pyramid alpha counts.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self/activities/pyramid-alphas"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users/self/activities/pyramid-alphas" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self/activities/pyramid-alphas"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
