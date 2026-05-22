# CLI 用法: `/user/password/change`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change password. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/user/password/change"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/user/password/change"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/user/password/change"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/user/password/change"
```


```powershell
python -m wqb_cli api call POST "/user/password/change"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
