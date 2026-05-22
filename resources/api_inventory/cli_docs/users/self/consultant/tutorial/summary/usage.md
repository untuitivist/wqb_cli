# CLI 用法: `/users/self/consultant/tutorial/summary`

- Methods: `GET, PATCH`
- Sources: `platform_dynamic_capture`
- Description: Observed by passive platform network capture.

## 查看定义

```powershell
python -m wqb_cli api show "/users/self/consultant/tutorial/summary"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/users/self/consultant/tutorial/summary"
```

实际执行:

```powershell
python -m wqb_cli api call GET "/users/self/consultant/tutorial/summary"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`

### `PATCH`

Command:

```powershell
python -m wqb_cli api call PATCH "/users/self/consultant/tutorial/summary"
```


```powershell
python -m wqb_cli api call PATCH "/users/self/consultant/tutorial/summary"
```

测试记录:

- Status: `skipped_mutating`
- Reason: PATCH may mutate remote state; not executed by inventory test.
