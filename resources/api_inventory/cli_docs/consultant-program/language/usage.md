# CLI 用法: `/consultant-program/{language}`

- Methods: `GET`
- Sources: `platform_frontend`
- Description: Consultant program by language. / Discovered from platform frontend bundle.

## 查看定义

```powershell
python -m wqb_cli api show "/consultant-program/{language}"
```

## 调用方式

### `GET`

Command:

```powershell
python -m wqb_cli api call GET "/consultant-program/{language}" --var language=en
```

实际执行:

```powershell
python -m wqb_cli api call GET "/consultant-program/{language}" --var language=en
```

测试记录:

- Status: `tested`
- HTTP: `404 Not Found`
