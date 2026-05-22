# CLI 用法: `/users/self/alphas`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Current user's alphas.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self/alphas"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/users/self/alphas" --param limit=1
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self/alphas" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
