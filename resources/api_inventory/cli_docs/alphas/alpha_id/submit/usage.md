# CLI 用法: `/alphas/{alpha_id}/submit`

- Methods: `POST`
- Sources: `rocky-d/wqb`
- Description: Submit alpha.

## 查看定义

```powershell
python -m wqb_cli api show "/alphas/{alpha_id}/submit"
```

## 调用方式

### `POST`

Command:

```powershell
python -m wqb_cli api call POST "/alphas/{alpha_id}/submit" --var alpha_id=vR5p8vqb
```


```powershell
python -m wqb_cli api call POST "/alphas/{alpha_id}/submit" --var alpha_id=vR5p8vqb
```

测试记录:

- Status: `skipped_mutating`
- Reason: POST may mutate remote state; not executed by inventory test.
