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

Command:

```powershell
python -m wqb_cli api call GET "/simulations/super-selection"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/simulations/super-selection"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/simulations/super-selection"
```


```powershell
python -m wqb_cli api call POST "/simulations/super-selection"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
