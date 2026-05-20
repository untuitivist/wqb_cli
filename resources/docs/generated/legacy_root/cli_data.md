# WQB Data CLI

`wqb data` 是数据域命令层，封装 data categories、datasets、fields �?operators 等接口�?
## `wqb data categories`

列出 BRAIN 数据分类�?
Raw API:

```text
GET /data-categories
```

命令:

```powershell
wqb data categories
```

验证记录:

## `wqb data datasets`

搜索数据集�?
Raw API:

```text
GET /data-sets
```

命令:

```powershell
wqb data datasets --instrument-type EQUITY --region USA --delay 1 --universe TOP3000 --limit 20
```

常用过滤:

```powershell
wqb data datasets --search analyst --limit 10
wqb data datasets --category analyst --limit 10
```

验证记录:

## `wqb data dataset`

获取单个数据集详情�?
Raw API:

```text
GET /data-sets/{dataset_id}
```

命令:

```powershell
wqb data dataset analyst10
```

验证记录:

## `wqb data fields`

搜索数据字段�?
Raw API:

```text
GET /data-fields
```

命令:

```powershell
wqb data fields --dataset analyst10 --limit 20
```

常用过滤:

```powershell
wqb data fields --search sentiment --limit 10
wqb data fields --region USA --delay 1 --universe TOP3000 --limit 10
```

验证记录:

## `wqb data field`

获取单个 data field 详情�?
Raw API:

```text
GET /data-fields/{field_id}
```

命令:

```powershell
wqb data field actual_update_flag_ebi
```

验证记录:

## `wqb data operators`

获取 FastExpr/Python operator 列表�?
Raw API:

```text
GET /operators
```

命令:

```powershell
wqb data operators
```

可选过�?

```powershell
wqb data operators --instrument-type EQUITY --region USA --delay 1
```

验证记录:
