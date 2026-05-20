# CLI 用法: `/alphas/{alpha_id}`

- Methods: `GET, PATCH`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha details or property patch. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/{alpha_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}" --var alpha_id=vR5p8vqb --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}" --var alpha_id=vR5p8vqb
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `PATCH`

Dry-run:

```powershell
python -m wqb_cli api call PATCH "/alphas/{alpha_id}" --var alpha_id=vR5p8vqb --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call PATCH "/alphas/{alpha_id}" --var alpha_id=vR5p8vqb --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: PATCH may mutate remote state; not executed by inventory test.
