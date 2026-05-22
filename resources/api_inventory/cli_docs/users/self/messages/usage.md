# CLI 用法: `/users/self/messages`

- Methods: `GET`
- Sources: `observed_platform, platform_dynamic_capture`
- Description: Current user's messages.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self/messages"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/users/self/messages"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self/messages"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
