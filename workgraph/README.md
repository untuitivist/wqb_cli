# Workgraph

这里存放新的 agent 工作图。

- `regular/`：当前可用的 REGULAR alpha 工作图。
- `super/`：未来 SUPER alpha 工作图占位，当前不要用于正式研究运行。

旧 `workflow/` 不属于这里的 runner。
不要调用或改接 `workflow/nodes/*/run.bat`。

## 运行原则

每次研究运行只写入：

```text
research_runs/run_YYYYMMDD_HHMMSS/
```

每个节点只写自己的节点目录。
节点输出必须包含过程、证据、校验报告、handoff 和机器可读结果。
后续节点只读取显式上游 artifact，不依赖聊天历史。

## 角色

workagent 只调度和监督，不做节点业务。
nodesubagent 一次只执行一个节点，不更新 `graph_state.json`。

## 当前入口

核心说明见：

```text
regular/WORKGRAPH.md
regular/workagent_contract.md
regular/nodesubagent_contract.md
regular/node_output_contract.md
regular/node_io_constraints.md
```

常用脚本：

```powershell
python workgraph\regular\scripts\init_run.py
python workgraph\regular\scripts\create_node_task.py ...
python workgraph\regular\scripts\validate_node_bundle.py ...
python workgraph\regular\scripts\validate_run_scope.py ...
python workgraph\regular\scripts\update_graph_state.py ...
python workgraph\regular\scripts\audit_run.py ...
```

