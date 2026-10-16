from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_registers_evidence_plugin_and_packages() -> None:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entry_points = payload["project"]["entry-points"]["wqb_cli.plugins"]
    assert entry_points["evidence"] == "wqb_cli.evidence.plugin:plugin"
    packages = payload["tool"]["setuptools"]["packages"]
    assert "wqb_cli.evidence" in packages
    assert "wqb_cli.evidence.providers.wind" in packages


def test_adaptive_workflow_has_wind_standing_without_execution_leakage() -> None:
    g = (ROOT / "workflows/workflow_simu/nodes/G_社区与文档经验/node.md").read_text(encoding="utf-8")
    h = (ROOT / "workflows/workflow_simu/nodes/H_经济学机制假设/node.md").read_text(encoding="utf-8")
    k = (ROOT / "workflows/workflow_simu/nodes/K_结果诊断/node.md").read_text(encoding="utf-8")

    assert "wqb evidence experiment freeze" in g
    assert "wqb evidence wind plan-check" in g
    assert "wqb evidence wind execute-plan" in g
    assert "wqb evidence wind call G" not in g
    assert "最多 **6 个机制**" in g
    assert "不得对 `candidate_datafields.json`" in g
    assert "mechanism_families.json" in g
    assert "reality_evidence_index.json" in g

    assert "wind_clarification_plan.json" in h
    assert "wqb evidence wind execute-plan" in h
    assert "wqb evidence wind call H clarification" not in h
    assert "reality_checks.json" in h
    assert "WIND_REALITY_OBSERVATION" in h
    assert "I 可以在不重新解释经济学含义、猜测数据类型或再次查询 Wind" in h

    assert "wqb evidence wind execute-plan" in k
    assert "最多 **3 次 Wind diagnosis 调用**" in k
    assert "不得作为失败 Alpha 的事后故事生成器" in k


def test_architecture_keeps_brain_authoritative() -> None:
    text = (ROOT / "docs/architecture/wind-evidence.md").read_text(encoding="utf-8")
    assert "not an alternate" in text
    assert "simulation" in text
    assert "submission" in text
    assert "F | forbidden" in text
    assert "J | forbidden" in text
    assert "M | forbidden" in text
    assert "research_freeze.json" in text
    assert "raw `wind call`" in text
    assert "fresh recorded Alice Market balance" in text
