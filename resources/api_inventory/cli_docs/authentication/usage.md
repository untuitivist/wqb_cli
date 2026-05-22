# CLI 用法: `/authentication`

- Methods: `DELETE, GET, HEAD, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Authentication session endpoint. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/authentication"
```

## 调用方式

### `DELETE`

Command:

```powershell
python -m wqb_cli api call DELETE "/authentication"
```


```powershell
python -m wqb_cli api call DELETE "/authentication"
```

测试记录:

- Status: `skipped_mutating`
- Reason: DELETE may mutate remote state; not executed by inventory test.

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/authentication"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/authentication"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `HEAD`

Command:

```powershell
python -m wqb_cli api call HEAD "/authentication"
```

实际执行:

```powershell
python -m wqb_cli api call HEAD "/authentication"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/authentication"
```


```powershell
python -m wqb_cli api call POST "/authentication"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
