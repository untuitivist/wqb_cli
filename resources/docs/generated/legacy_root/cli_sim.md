# WQB Simulation CLI

`wqb sim` �?simulation 相关命令层�?
## `wqb sim options`

获取 `/simulations` �?POST schema�?
Raw API:

```text
OPTIONS /simulations
```

命令:

```powershell
wqb sim options
```

验证记录:

## `wqb sim get`

获取 simulation 状态或完成结果�?
Raw API:

```text
GET /simulations/{simulation_id}
```

命令:

```powershell
wqb sim get 2UnwIe7g5jEcCgDvI4GpqO
```

验证记录:

## `wqb sim create`

Raw API:

```text
POST /simulations
```

示例输入:

```powershell
api_inventory/examples/simulation_regular_close.json
```

显式执行:

```powershell
wqb sim create --input api_inventory/examples/simulation_regular_close.json --execute
```

验证记录:
