# Simulation 输入 JSON 示例

这些 JSON 都可以直接保存为 `--input` 文件后交给 `wqb sim create`。

## REGULAR FASTEXPR multi-simulation

multi-simulation 的输入是 JSON array。
数组内每个元素是一条 `REGULAR` + `FASTEXPR` simulation。
同一个 multi 请求中必须保持一致的 settings 是 `delay`、`region`、`instrumentType`、`language`。

```json
[
  {
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "TOP3000",
      "delay": 1,
      "decay": 4,
      "neutralization": "SUBINDUSTRY",
      "truncation": 0.08,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "OFF",
      "language": "FASTEXPR",
      "visualization": false
    },
    "regular": "rank(ts_delta(close, 1))"
  },
  {
    "type": "REGULAR",
    "settings": {
      "instrumentType": "EQUITY",
      "region": "USA",
      "universe": "TOP3000",
      "delay": 1,
      "decay": 4,
      "neutralization": "SUBINDUSTRY",
      "truncation": 0.08,
      "pasteurization": "ON",
      "unitHandling": "VERIFY",
      "nanHandling": "OFF",
      "language": "FASTEXPR",
      "visualization": false
    },
    "regular": "-rank(ts_delta(close, 1))"
  }
]
```

对应 fixture：

```text
resources/docs/commands/simulations/create/fixtures/regular_fastexpr_multi.json
```

## REGULAR FASTEXPR single-simulation

single-simulation 的输入是 JSON object。

```json
{
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 4,
    "neutralization": "SUBINDUSTRY",
    "truncation": 0.08,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "language": "FASTEXPR",
    "visualization": false
  },
  "regular": "rank(ts_delta(close, 1))"
}
```

对应 fixture：

```text
resources/docs/commands/simulations/create/fixtures/regular_fastexpr_single.json
```

## REGULAR PYTHON single-simulation

`PYTHON` 不能合成 multi-simulation。
多个 Python alpha 需要由外部调度器按并发限制逐条提交。

```json
{
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "CHN",
    "universe": "TOP2000U",
    "delay": 1,
    "decay": 15,
    "neutralization": "REVERSION_AND_MOMENTUM",
    "truncation": 0.04,
    "lookback": 2,
    "pasteurization": "ON",
    "maxTrade": "ON",
    "maxPosition": "OFF",
    "language": "PYTHON",
    "visualization": false,
    "startDate": "2014-01-01",
    "endDate": "2023-12-31"
  },
  "regular": "from brain.alphas import alpha\nimport numpy as np\nimport numpy.typing as npt\n\n\ndef _pasteurize(a, universe):\n    a = a.copy()\n    a[~universe.astype(bool)] = np.nan\n    return a\n\n\n@alpha(data=[\"close\", \"high\", \"low\"], store=[])\ndef cli_regular_python_example(data, store) -> npt.NDArray[np.float32]:\n    if data.close.shape[0] < 2:\n        return np.full(data.close.shape[1], np.nan, dtype=np.float32)\n    spread = data.high - data.low\n    spread = np.where(spread == 0, np.nan, spread)\n    signal = ((data.close - data.low) - (data.high - data.close)) / spread\n    a = -(signal[-1] - signal[-2])\n    a = _pasteurize(a, data.close[-1])\n    return a.astype(np.float32)"
}
```

对应 fixture：

```text
resources/docs/commands/simulations/create/fixtures/regular_python_single.json
```

## SUPER single-simulation

`SUPER` 请求体使用 `selection` 和 `combo`，不用 `regular`。

```json
{
  "type": "SUPER",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 4,
    "neutralization": "SUBINDUSTRY",
    "truncation": 0.08,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "OFF",
    "selectionHandling": "POSITIVE",
    "selectionLimit": 10,
    "language": "FASTEXPR",
    "visualization": false
  },
  "selection": "own == 1",
  "combo": "1"
}
```

对应 fixture：

```text
resources/docs/commands/simulations/create/fixtures/super_single.json
```
