# WQB Alpha CLI

`wqb alpha` 是业务域命令层，封装 raw API registry 中的 `/alphas/*` endpoint�?
## `wqb alpha get`

获取一�?alpha 的完整详情�?
Raw API:

```text
GET /alphas/{alpha_id}
```

命令:

```powershell
wqb alpha get vR5p8vqb
```

输出:

- JSON object�?- `ok=true` 表示 HTTP status �?2xx/3xx�?- `response.body` �?API 返回�?alpha 详情�?
验证记录:

## `wqb alpha list`

列出当前用户�?alpha�?
Raw API:

```text
GET /users/self/alphas
```

命令:

```powershell
wqb alpha list --limit 20 --offset 0
```

常用过滤:

```powershell
wqb alpha list --limit 10 --type REGULAR
wqb alpha list --limit 10 --color PURPLE
wqb alpha list --limit 10 --tag '!OWN'
```

验证记录:

## `wqb alpha check`

获取 alpha 的提交检查结果�?
Raw API:

```text
GET /alphas/{alpha_id}/check
```

命令:

```powershell
wqb alpha check vR5p8vqb
```

验证记录:

## `wqb alpha recordsets`

列出 alpha 可用 record sets�?
Raw API:

```text
GET /alphas/{alpha_id}/recordsets
```

命令:

```powershell
wqb alpha recordsets vR5p8vqb
```

验证记录:

## `wqb alpha recordset`

获取某个具体 record set，例�?`pnl`、`sharpe`、`turnover`、`yearly-stats`�?
Raw API:

```text
GET /alphas/{alpha_id}/recordsets/{record_set_name}
```

命令:

```powershell
wqb alpha recordset vR5p8vqb pnl
```

验证记录:

## `wqb alpha correlation self`

获取 alpha �?self correlation record set�?
Raw API:

```text
GET /alphas/{alpha_id}/correlations/self
```

命令:

```powershell
wqb alpha correlation self vR5p8vqb
```

验证记录:

## `wqb alpha correlation prod`

获取 alpha �?production correlation record set�?
Raw API:

```text
GET /alphas/{alpha_id}/correlations/prod
```

命令:

```powershell
wqb alpha correlation prod vR5p8vqb
```

验证记录:

## `wqb alpha correlation power-pool`

获取 alpha �?Power Pool correlation record set�?
Raw API:

```text
GET /alphas/{alpha_id}/correlations/power-pool
```

命令:

```powershell
wqb alpha correlation power-pool vR5p8vqb
```

验证记录:

## `wqb alpha performance-comparison`

获取 alpha �?performance comparison�?
Raw API:

```text
GET /alphas/{alpha_id}/performance-comparison
```

命令:

```powershell
wqb alpha performance-comparison vR5p8vqb
```

验证记录:
