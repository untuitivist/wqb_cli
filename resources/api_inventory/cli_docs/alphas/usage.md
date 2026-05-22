# CLI 用法: `/alphas`

- Methods: `GET`
- Sources: `platform_frontend, rocky-d/wqb`
- Description: Alpha collection. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/alphas" --param limit=1
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas" --param limit=1
```

测试记录:

- Status: `tested`
- HTTP: `405 Method Not Allowed`
