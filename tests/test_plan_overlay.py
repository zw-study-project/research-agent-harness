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
SCRIPT = ROOT / "scripts" / "plan_overlay.py"


def load_module():
    spec = importlib.util.spec_from_file_location("research_overlay_plan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_overlay(root: Path) -> Path:
    overlay = root / "overlay"
    (overlay / "docs").mkdir(parents=True)
    (overlay / "docs" / "rules.md").write_text("rules\n", encoding="utf-8")
    (overlay / "memory").mkdir()
    (overlay / "memory" / "index.md").write_text("index\n", encoding="utf-8")
    return overlay


class OverlayPlanTests(unittest.TestCase):
    def test_missing_overlay_files_are_create(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            plan = module.build_plan(target, overlay)
        self.assertEqual({entry.action for entry in plan.entries if entry.path.startswith(("docs/", "memory/"))}, {"create"})

    def test_shared_root_files_are_merge_required(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            (target / "AGENTS.md").write_text("existing\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
        entry = next(item for item in plan.entries if item.path == "AGENTS.md")
        self.assertEqual(entry.action, "merge_required")

    def test_identical_existing_overlay_file_is_compatible(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            (target / "docs").mkdir(parents=True)
            (target / "docs" / "rules.md").write_text("rules\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
        entry = next(item for item in plan.entries if item.path == "docs/rules.md")
        self.assertEqual(entry.action, "compatible")

    def test_different_existing_overlay_file_is_merge_required(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            (target / "docs").mkdir(parents=True)
            (target / "docs" / "rules.md").write_text("custom\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
        entry = next(item for item in plan.entries if item.path == "docs/rules.md")
        self.assertEqual(entry.action, "merge_required")

    def test_file_directory_type_mismatch_is_conflict(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            (target / "docs").write_text("not a directory", encoding="utf-8")
            plan = module.build_plan(target, overlay)
        entry = next(item for item in plan.entries if item.path == "docs/rules.md")
        self.assertEqual(entry.action, "conflict")

    def test_apply_creates_only_create_entries(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            (target / "AGENTS.md").write_text("keep\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
            created = module.apply_plan(plan, overlay)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "keep\n")
            self.assertEqual(set(created), {"docs/rules.md", "memory/index.md"})

    def test_apply_never_overwrites_existing_file(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            (target / "docs").mkdir(parents=True)
            destination = target / "docs" / "rules.md"
            destination.write_text("custom\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
            module.apply_plan(plan, overlay)
            self.assertEqual(destination.read_text(encoding="utf-8"), "custom\n")

    def test_stale_plan_aborts_before_any_write(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            plan = module.build_plan(target, overlay)
            (target / "docs").mkdir()
            (target / "docs" / "rules.md").write_text("appeared\n", encoding="utf-8")
            with self.assertRaises(module.StalePlanError):
                module.apply_plan(plan, overlay)
            self.assertFalse((target / "memory" / "index.md").exists())

    def test_changed_overlay_source_aborts_before_any_write(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            plan = module.build_plan(target, overlay)
            (overlay / "docs" / "rules.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(module.StalePlanError):
                module.apply_plan(plan, overlay)
            self.assertFalse((target / "memory" / "index.md").exists())

    def test_symlinked_parent_outside_target_is_conflict(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            try:
                (target / "docs").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            plan = module.build_plan(target, overlay)
            entry = next(item for item in plan.entries if item.path == "docs/rules.md")
            self.assertEqual(entry.action, "conflict")
            with self.assertRaises(ValueError):
                module.apply_plan(plan, overlay)
            self.assertFalse((outside / "rules.md").exists())

    def test_shared_files_receive_specific_merge_guidance(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            for name in ("AGENTS.md", "progress.md", "session-handoff.md", "init.sh", "feature_list.json"):
                (target / name).write_text("existing\n", encoding="utf-8")
            plan = module.build_plan(target, overlay)
        reasons = {entry.path: entry.reason for entry in plan.entries if entry.action == "merge_required"}
        self.assertIn("research-contract", reasons["AGENTS.md"])
        self.assertIn("Current Research Claim", reasons["progress.md"])
        self.assertIn("next exact command", reasons["session-handoff.md"])
        self.assertIn("research validator", reasons["init.sh"])
        self.assertIn("projection", reasons["feature_list.json"])

    def test_non_ascii_target_path_can_be_applied(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "科研 项目"
            target.mkdir()
            module.apply_plan(module.build_plan(target, overlay), overlay)
            self.assertTrue((target / "docs" / "rules.md").is_file())

    def test_json_plan_stdout_is_parseable(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            target.mkdir()
            output = io.StringIO()
            with redirect_stdout(output):
                return_code = module.main(["--target", str(target), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertIn("entries", payload)

    def test_saved_plan_round_trips_without_losing_entries(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "科研 项目"
            target.mkdir()
            plan_file = root / "已审阅 plan.json"
            expected = module.build_plan(target, overlay)
            module.save_plan(expected, plan_file)
            actual = module.load_plan(plan_file)
        self.assertEqual(actual, expected)

    def test_load_plan_rejects_unknown_schema_version(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            plan_file = Path(temporary) / "plan.json"
            plan_file.write_text('{"schema_version": 99}', encoding="utf-8")
            with self.assertRaises(ValueError):
                module.load_plan(plan_file)

    def test_apply_saved_plan_rejects_target_change_before_writing(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            plan_file = root / "plan.json"
            module.save_plan(module.build_plan(target, overlay), plan_file)
            (target / "docs").mkdir()
            (target / "docs" / "rules.md").write_text("appeared\n", encoding="utf-8")
            with self.assertRaises(module.StalePlanError):
                module.apply_plan(module.load_plan(plan_file), overlay)
            self.assertFalse((target / "memory" / "index.md").exists())

    def test_apply_saved_plan_creates_only_reviewed_files(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = make_overlay(root)
            target = root / "target"
            target.mkdir()
            plan_file = root / "plan.json"
            module.save_plan(module.build_plan(target, overlay), plan_file)
            created = module.apply_plan(module.load_plan(plan_file), overlay)
            self.assertEqual(set(created), {"docs/rules.md", "memory/index.md"})

    def test_cli_save_then_apply_plan(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "目标 项目"
            target.mkdir()
            plan_file = root / "reviewed-plan.json"
            output = io.StringIO()
            with redirect_stdout(output):
                save_code = module.main(["--target", str(target), "--save-plan", str(plan_file), "--json"])
            with redirect_stdout(io.StringIO()):
                apply_code = module.main(["--apply-plan", str(plan_file), "--json"])
            self.assertEqual(save_code, 0)
            self.assertEqual(apply_code, 0)
            self.assertTrue((target / "docs" / "agent-research-rules.md").is_file())

    def test_cli_rejects_apply_with_apply_plan(self) -> None:
        module = load_module()
        with self.assertRaises(SystemExit):
            module.main(["--target", ".", "--apply", "--apply-plan", "plan.json"])


if __name__ == "__main__":
    unittest.main()
