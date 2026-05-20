# CLI 用法: `/data-sets`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Data set search. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/data-sets"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/data-sets" --param instrumentType=EQUITY --param region=USA --param delay=1 --param universe=TOP3000 --param limit=1 --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/data-sets" --param instrumentType=EQUITY --param region=USA --param delay=1 --param universe=TOP3000 --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
