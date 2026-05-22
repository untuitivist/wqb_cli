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

Command:

```powershell
python -m wqb_cli api call POST "/errors/api/2/envelope"
```


```powershell
python -m wqb_cli api call POST "/errors/api/2/envelope"
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
