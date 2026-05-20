# CLI 用法: `/data-sets/{dataset_id}`

- Methods: `GET`
- Sources: `rocky-d/wqb`
- Description: Dataset details.

## 查看定义

```powershell
python -m wqb_cli api show "/data-sets/{dataset_id}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/data-sets/{dataset_id}" --var dataset_id=analyst10 --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/data-sets/{dataset_id}" --var dataset_id=analyst10
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
