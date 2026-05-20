# POST /simulations

## 参数命令行 + 打印结果

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call POST /simulations --execute --json {\"type\":\"REGULAR\",\"settings\":{\"instrumentType\":\"EQUITY\",\"region\":\"USA\",\"universe\":\"TOP3000\",\"delay\":1,\"decay\":15,\"neutralization\":\"SUBINDUSTRY\",\"truncation\":0.08,\"pasteurization\":\"ON\",\"unitHandling\":\"VERIFY\",\"nanHandling\":\"OFF\",\"language\":\"FASTEXPR\",\"visualization\":false},\"regular\":\"close\"}
```

打印结果文件：`print_result.json`

## 文件 IO 命令行 + 输入输出文件

```powershell
D:\_soft\Anaconda\envs\WQBRAIN\python.exe -m wqb_cli api call POST /simulations --input api_inventory\endpoints\simulations\examples\POST\input.json --execute --output api_inventory\endpoints\simulations\examples\POST\file_output.json
```

输入文件：`input.json`
输出文件：`file_output.json`

说明：示例是真实 CLI 调用，不使用 dry-run 模式。变更类接口带 `--execute`，请求结果以平台实际返回为准；账号密码从 `.env` 读取且不会写入命令文本。
