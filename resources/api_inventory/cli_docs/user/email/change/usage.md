# CLI 用法: `/user/email/change`

- Methods: `GET, POST`
- Sources: `platform_frontend`
- Description: Change email. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/user/email/change"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/user/email/change" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/user/email/change"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`

### `POST`

Dry-run:

```powershell
python -m wqb_cli api call POST "/user/email/change" --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call POST "/user/email/change" --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
