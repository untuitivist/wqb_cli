# CLI 用法: `/users/{user_id}/activities/diversity`

- Methods: `GET`
- Sources: `official_doc_snippet`
- Description: 按 Region、Delay、Data Category 返回 alpha 提交分布。

## 查看定义

```powershell
python -m wqb_cli api show "/users/{user_id}/activities/diversity"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/users/{user_id}/activities/diversity" --var user_id=JL40454 --param grouping=region,delay,dataCategory --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/{user_id}/activities/diversity" --var user_id=JL40454 --param grouping=region,delay,dataCategory
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
