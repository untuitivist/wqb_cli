# POST /errors/api/2/envelope

## 参数命令行 + 打印结果

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call POST /errors/api/2/envelope --param sentry_client=sample --param sentry_key=sample --param sentry_version=sample --json "{\"event_id\":\"example\",\"timestamp\":\"2026-05-19T19:19:07.909062+00:00\",\"exception\":{\"values\":[{\"type\":\"ExampleError\",\"value\":\"example request\"}]}}"
```

打印结果文件：`print_result.json`

## 文件 IO 命令行 + 输入输出文件

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call POST /errors/api/2/envelope --input api_inventory\endpoints\errors\api\2\envelope\examples\POST\input.json --output api_inventory\endpoints\errors\api\2\envelope\examples\POST\file_output.json
```

输入文件：`input.json`
输出文件：`file_output.json`

说明：示例是真实 CLI 调用。请求结果以平台实际返回为准；账号密码从 `.env` 读取且不会写入命令文本。
