# CLI 用法: `/video-courses`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Video courses. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/video-courses"
```

## 调用方式

### `GET`

Dry-run:

```powershell
python -m wqb_cli api call GET "/video-courses" --dry-run
```

实际执行:

```powershell
python -m wqb_cli api call GET "/video-courses"
```

测试记录:

- Status: `tested`
- HTTP: `200 OK`
