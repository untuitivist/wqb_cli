from __future__ import annotations

import string
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "workflows"
SIMU = WORKFLOWS / "workflow_simu"
BATCH = WORKFLOWS / "workflow_batchsimu"


def _node_letters(workflow: Path) -> list[str]:
    return sorted(
        path.name.split("_", 1)[0]
        for path in (workflow / "nodes").iterdir()
        if path.is_dir()
    )


def _markdown_text(workflow: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(workflow.rglob("*.md"))
    )


class WorkflowLayoutTests(unittest.TestCase):
    def test_workflows_are_complete_and_old_layout_is_gone(self) -> None:
        self.assertTrue((SIMU / "workflow_graph.md").is_file())
        self.assertTrue((BATCH / "workflow_graph.md").is_file())
        self.assertFalse((ROOT / "workflow").exists())

        self.assertEqual(_node_letters(SIMU), list(string.ascii_uppercase[:13]))
        self.assertEqual(_node_letters(BATCH), list(string.ascii_uppercase[:12]))

        for workflow in (SIMU, BATCH):
            for node in (workflow / "nodes").iterdir():
                if node.is_dir():
                    self.assertTrue((node / "node.md").is_file(), node)

    def test_workflow_documents_do_not_cross_reference(self) -> None:
        self.assertNotIn("workflow_batchsimu", _markdown_text(SIMU))
        self.assertNotIn("workflow_simu", _markdown_text(BATCH))

    def test_workflow_run_contracts_are_physically_separate(self) -> None:
        simu_graph = (SIMU / "workflow_graph.md").read_text(encoding="utf-8")
        batch_graph = (BATCH / "workflow_graph.md").read_text(encoding="utf-8")

        self.assertIn("research_runs/\n  workflow_simu/", simu_graph)
        self.assertIn("research_runs/\n  workflow_batchsimu/", batch_graph)
        self.assertIn("A-M", simu_graph)
        self.assertIn("A-L", batch_graph)
        self.assertIn("alpha_submission_allowed = false", batch_graph)

    def test_workflow_markdown_is_utf8_without_bom(self) -> None:
        for path in WORKFLOWS.rglob("*.md"):
            content = path.read_bytes()
            self.assertFalse(content.startswith(b"\xef\xbb\xbf"), path)
            content.decode("utf-8")

    def test_workflows_are_in_sdist_and_wheel_configuration(self) -> None:
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("recursive-include workflows *.md", manifest)
        self.assertIn('"workflows/*.md"', pyproject)
        self.assertIn('"workflows/**/*.md"', pyproject)


if __name__ == "__main__":
    unittest.main()
