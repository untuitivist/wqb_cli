# CLI 用法: `/data-sets/search`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Dataset search helper. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/data-sets/search"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/data-sets/search"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/data-sets/search"
```

测试记录:

- Status: `tested`
- HTTP: `400 Bad Request`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/data-sets/search"
```


```powershell
python -m wqb_cli api call POST "/data-sets/search"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
