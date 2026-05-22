# GET /achievements/{achievement_id}/icon

## 参数命令行 + 打印结果

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call GET /achievements/{achievement_id}/icon --var achievement_id=ALPHA_PERF_EXCELLENT
```

打印结果文件：`print_result.json`

## 文件 IO 命令行 + 输入输出文件

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call GET /achievements/{achievement_id}/icon --input api_inventory\endpoints\achievements\achievement_id\icon\examples\GET\input.json --output api_inventory\endpoints\achievements\achievement_id\icon\examples\GET\file_output.json
```

输入文件：`input.json`
输出文件：`file_output.json`

说明：示例是真实 CLI 调用。请求结果以平台实际返回为准；账号密码从 `.env` 读取且不会写入命令文本。
