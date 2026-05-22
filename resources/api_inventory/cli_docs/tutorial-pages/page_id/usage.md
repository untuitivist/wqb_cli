# CLI 用法: `/tutorial-pages/{page_id}`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Tutorial page details.

## 查看定义

```powershell
python -m wqb_cli api show "/tutorial-pages/{page_id}"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/tutorial-pages/{page_id}" --var page_id=exclusive-events-and-support-for-consultants
```

实际执行:

```powershell
python -m wqb_cli api call GET "/tutorial-pages/{page_id}" --var page_id=exclusive-events-and-support-for-consultants
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
