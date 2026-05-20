# CLI 用法: `/simulations/super-selection`

- Methods: `GET, POST`
- Sources: `observed_platform, platform_frontend`
- Description: Super selection simulation. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/simulations/super-selection"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/simulations/super-selection" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/simulations/super-selection"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Dry-run:

```powershell
python -m wqb_cli api call POST "/simulations/super-selection" --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call POST "/simulations/super-selection" --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
