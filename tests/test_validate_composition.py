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
SCRIPT = ROOT / "scripts" / "validate_composition.py"


def load_module():
    spec = importlib.util.spec_from_file_location("research_composition_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def valid_project(root: Path, include_contract: bool = True) -> None:
    write(root, "AGENTS.md", "Read docs/research-contract.md and work_items.json. work_items.json is authoritative; feature_list.json is a compatibility projection.\n")
    if include_contract:
        write(root, "docs/research-contract.md", "# Research Contract\n")
    write(root, "docs/agent-research-rules.md", "# Research Agent Rules\n")
    write(root, "work_items.json", '{"schema_version": 1, "work_items": []}\n')
    write(root, "feature_list.json", '{"features": []}\n')
    write(root, "progress.md", "# Progress\n## Current Research Claim\nBounded claim.\n")
    write(root, "session-handoff.md", "# Handoff\n## Active work item\nRQ-001\n## Current claim\nBounded.\n## Last verification\n`python test.py` passed.\n## Risks\nNone known.\n## Next exact command\n`python next.py`\n")
    write(root, "memory/index.md", "# Research Memory Index\n")


class CompositionValidatorTests(unittest.TestCase):
    def test_complete_composition_passes(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            findings = module.validate_composition(root)
        self.assertFalse([item for item in findings if item.severity == "error"])

    def test_root_agent_guide_must_route_to_research_contract(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "AGENTS.md", "Generic instructions only.\n")
            findings = module.validate_composition(root)
        self.assertIn("missing_research_route", {item.code for item in findings})

    def test_work_items_is_declared_authoritative_when_feature_list_exists(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "AGENTS.md", "Read docs/research-contract.md and work_items.json.\n")
            findings = module.validate_composition(root)
        self.assertIn("ambiguous_state_authority", {item.code for item in findings})

    def test_reversed_state_authority_is_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "AGENTS.md", "Read docs/research-contract.md and work_items.json. feature_list.json is authoritative; work_items.json is a read-only projection.\n")
            findings = module.validate_composition(root)
        self.assertIn("ambiguous_state_authority", {item.code for item in findings})

    def test_overlay_rules_cannot_mask_conflicting_root_authority(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "AGENTS.md", "Read docs/research-contract.md and work_items.json. feature_list.json is authoritative; work_items.json is a projection.\n")
            write(root, "docs/agent-research-rules.md", "work_items.json is authoritative; feature_list.json is a projection.\n")
            findings = module.validate_composition(root)
        self.assertIn("conflicting_state_authority", {item.code for item in findings})

    def test_handoff_requires_current_claim_verification_risk_and_next_command(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "session-handoff.md", "# Handoff\n## Active work item\nRQ-001\n")
            findings = module.validate_composition(root)
        self.assertIn("incomplete_research_handoff", {item.code for item in findings})

    def test_missing_referenced_research_file_is_an_error(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root, include_contract=False)
            findings = module.validate_composition(root)
        self.assertIn("missing_required_file", {item.code for item in findings})

    def test_broken_local_markdown_reference_is_an_error(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "AGENTS.md", "Read docs/research-contract.md and work_items.json. work_items.json is authoritative; feature_list.json is a compatibility projection. See [protocol](docs/protocols/missing.md).\n")
            findings = module.validate_composition(root)
        self.assertIn("broken_local_reference", {item.code for item in findings})

    def test_vendored_skill_placeholders_are_ignored(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "reusable-research-harness/assets/template.md", "UNRESOLVED: fixture\n")
            findings = module.validate_composition(root)
        self.assertNotIn("unresolved_field", {item.code for item in findings})

    def test_virtual_environment_and_generated_paths_are_ignored(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            virtual_dir = "." + "".join(chr(code) for code in (118, 101, 110, 118))
            write(root, virtual_dir + "/generated.md", "UNRESOLVED: fixture\n")
            write(root, "build/generated.md", "UNRESOLVED: fixture\n")
            findings = module.validate_composition(root)
        self.assertNotIn("unresolved_field", {item.code for item in findings})

    def test_nested_vendor_templates_are_ignored(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            write(root, "docs/vendor/third-party-skill/assets/template.md", "UNRESOLVED: fixture\n")
            findings = module.validate_composition(root)
        self.assertNotIn("unresolved_field", {item.code for item in findings})

    def test_json_cli_stdout_is_parseable(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_project(root)
            output = io.StringIO()
            with redirect_stdout(output):
                return_code = module.main(["--target", str(root), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["errors"], 0)


if __name__ == "__main__":
    unittest.main()
