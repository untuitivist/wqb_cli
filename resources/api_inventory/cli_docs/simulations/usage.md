# CLI 用法: `/simulations`

- Methods: `GET, OPTIONS, POST`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Simulation collection and simulation creation. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/simulations"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/simulations" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/simulations"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`

### `OPTIONS`

Dry-run:

```powershell
python -m wqb_cli api call OPTIONS "/simulations" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call OPTIONS "/simulations"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Dry-run:

```powershell
python -m wqb_cli api call POST "/simulations" --dry-run
```

实际执行需要显式 `--execute`，默认不会执行以避免远端副作用。

```powershell
python -m wqb_cli api call POST "/simulations" --execute
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
