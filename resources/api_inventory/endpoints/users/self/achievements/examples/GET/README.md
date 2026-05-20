# GET /users/self/achievements

## 参数命令行 + 打印结果

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call GET /users/self/achievements
```

打印结果文件：`print_result.json`

## 文件 IO 命令行 + 输入输出文件

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call GET /users/self/achievements --input api_inventory\endpoints\users\self\achievements\examples\GET\input.json --output api_inventory\endpoints\users\self\achievements\examples\GET\file_output.json
```

输入文件：`input.json`
输出文件：`file_output.json`

说明：示例是真实 CLI 调用，不使用 dry-run 模式。变更类接口带 `--execute`，请求结果以平台实际返回为准；账号密码从 `.env` 读取且不会写入命令文本。
