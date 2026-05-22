# CLI 用法: `/suggest/examples`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Suggestion examples. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/suggest/examples"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/suggest/examples"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/suggest/examples"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/suggest/examples"
```


```powershell
python -m wqb_cli api call POST "/suggest/examples"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
