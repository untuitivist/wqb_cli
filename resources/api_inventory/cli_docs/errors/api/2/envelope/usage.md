# CLI 用法: `/errors/api/2/envelope`

- Methods: `POST`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/errors/api/2/envelope"
```

## 调用方式

### `POST`

Dry-run:

```powershell
python -m wqb_cli api call POST "/errors/api/2/envelope" --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call POST "/errors/api/2/envelope" --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
