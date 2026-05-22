# CLI 用法: `/alphas/{alpha_id}/correlations/power-pool`

- Methods: `GET`
- Sources: `observed_platform`
- Description: Power Pool correlation.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/{alpha_id}/correlations/power-pool"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/correlations/power-pool" --var alpha_id=vR5p8vqb
```

实际执行:

```powershell
python -m wqb_cli api call GET "/alphas/{alpha_id}/correlations/power-pool" --var alpha_id=vR5p8vqb
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
