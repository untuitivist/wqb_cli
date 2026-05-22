# PATCH /users/self/consultant/tutorial/summary

## 参数命令行 + 打印结果

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call PATCH /users/self/consultant/tutorial/summary --json {\"completedSteps\":[]}
```

打印结果文件：`print_result.json`

## 文件 IO 命令行 + 输入输出文件

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call PATCH /users/self/consultant/tutorial/summary --input api_inventory\endpoints\users\self\consultant\tutorial\summary\examples\PATCH\input.json --output api_inventory\endpoints\users\self\consultant\tutorial\summary\examples\PATCH\file_output.json
```

输入文件：`input.json`
输出文件：`file_output.json`

说明：示例是真实 CLI 调用。请求结果以平台实际返回为准；账号密码从 `.env` 读取且不会写入命令文本。
