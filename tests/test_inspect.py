from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "inspect.py"


def load_module():
    spec = importlib.util.spec_from_file_location("research_harness_inspect", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_files(root: Path, paths: list[str]) -> None:
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}" if path.suffix == ".json" else "fixture\n", encoding="utf-8")


class InspectTests(unittest.TestCase):
    def test_empty_project_reports_both_layers_missing(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            result = module.inspect_target(Path(temporary))
        self.assertEqual(result.state, "empty")
        self.assertTrue(result.generic.missing)
        self.assertTrue(result.research.missing)

    def test_generic_harness_is_detected_without_research_layer(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(root, ["AGENTS.md", "feature_list.json", "progress.md", "init.sh", "session-handoff.md"])
            result = module.inspect_target(root)
        self.assertEqual(result.state, "generic_only")
        self.assertFalse(result.generic.missing)
        self.assertTrue(result.research.missing)

    def test_research_harness_is_detected_without_generic_layer(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(root, [
                "docs/research-contract.md", "work_items.json", "resources/registry.json",
                "literature/registry.json", "explorations/registry.json", "experiments/registry.json",
            ])
            result = module.inspect_target(root)
        self.assertEqual(result.state, "research_only")
        self.assertFalse(result.research.missing)

    def test_claude_guide_and_documented_verifier_form_valid_generic_layer(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_files(root, ["CLAUDE.md", "progress.md", "session-handoff.md", "scripts/verify-fast.ps1"])
            result = module.inspect_target(root)
        self.assertEqual(result.state, "generic_only")
        self.assertFalse(result.generic.missing)

    def test_non_ascii_target_path_is_supported(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "科研 项目"
            root.mkdir()
            self.assertEqual(module.inspect_target(root).state, "empty")

    def test_json_cli_stdout_is_parseable(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            with redirect_stdout(output):
                return_code = module.main(["--target", temporary, "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["state"], "empty")

    def test_missing_target_returns_exit_two(self) -> None:
        module = load_module()
        missing = Path(tempfile.gettempdir()) / "research-agent-harness-missing-target"
        output = io.StringIO()
        with redirect_stdout(output):
            return_code = module.main(["--target", str(missing), "--json"])
        self.assertEqual(return_code, 2)


if __name__ == "__main__":
    unittest.main()
