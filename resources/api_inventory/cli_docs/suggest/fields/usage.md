# CLI 用法: `/suggest/fields`

- Methods: `GET, POST`
- Sources: `platform_dynamic_capture, platform_frontend`
- Description: Field suggestion. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/suggest/fields"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/suggest/fields" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/suggest/fields"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Dry-run:

```powershell
python -m wqb_cli api call POST "/suggest/fields" --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call POST "/suggest/fields" --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
