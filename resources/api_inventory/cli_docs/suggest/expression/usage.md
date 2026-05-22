# CLI 用法: `/suggest/expression`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Expression suggestion. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/suggest/expression"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/suggest/expression"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/suggest/expression"
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/suggest/expression"
```


```powershell
python -m wqb_cli api call POST "/suggest/expression"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
