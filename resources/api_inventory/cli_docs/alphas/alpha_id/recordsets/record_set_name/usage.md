# CLI 用法: `/alphas/{alpha_id}/recordsets/{record_set_name}`

- Methods: `GET`
- Sources: `official_doc_snippet`
- Description: 获取指定 record set。

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/{alpha_id}/recordsets/{record_set_name}"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/recordsets/{record_set_name}" --var alpha_id=vR5p8vqb --var record_set_name=pnl --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/recordsets/{record_set_name}" --var alpha_id=vR5p8vqb --var record_set_name=pnl
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
