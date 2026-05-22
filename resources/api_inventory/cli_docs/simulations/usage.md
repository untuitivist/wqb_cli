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

Command:

```powershell
python -m wqb_cli api call GET "/simulations"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/simulations"
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`

### `OPTIONS`

Command:

```powershell
python -m wqb_cli api call OPTIONS "/simulations"
```

实际执行:

```powershell
python -m wqb_cli api call OPTIONS "/simulations"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/simulations"
```


```powershell
python -m wqb_cli api call POST "/simulations"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
