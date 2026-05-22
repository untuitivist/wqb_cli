# CLI 用法: `/operators`

- Methods: `GET`
- Sources: `platform_dynamic_capture, platform_frontend, rocky-d/wqb`
- Description: Operator list/search. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/operators"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/operators"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/operators"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
