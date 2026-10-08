from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
REQUIRED_REFERENCES = {
    "composition-contract.md",
    "research-agent-workflow.md",
    "evidence-and-claims.md",
    "experiment-lifecycle.md",
    "memory-and-handoff.md",
    "multi-agent-research.md",
}


class SkillContractTests(unittest.TestCase):
    def test_skill_has_required_frontmatter_and_references(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: research-agent-harness", text)
        self.assertIn("description: Use when", text)
        self.assertEqual(
            {path.name for path in (ROOT / "references").glob("*.md")},
            REQUIRED_REFERENCES,
        )

    def test_skill_links_every_reference(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in REQUIRED_REFERENCES:
            self.assertIn(f"references/{name}", text)

    def test_overlay_does_not_contain_shared_root_files(self) -> None:
        overlay = ROOT / "assets" / "overlay"
        forbidden = {
            "AGENTS.md",
            "CLAUDE.md",
            "progress.md",
            "session-handoff.md",
            "init.sh",
            "feature_list.json",
        }
        actual = {path.name for path in overlay.rglob("*") if path.is_file()}
        self.assertFalse(forbidden.intersection(actual))

    def test_every_local_markdown_link_resolves(self) -> None:
        import re

        for markdown in ROOT.rglob("*.md"):
            text = markdown.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken link in {markdown}: {target}")

    def test_overlay_verifier_uses_research_harness_validator_name(self) -> None:
        verifier = ROOT / "assets" / "overlay" / "scripts" / "verify-research-state.ps1"
        text = verifier.read_text(encoding="utf-8")
        self.assertIn('"validate-state.py"', text)
        self.assertNotIn('"validate-research-state.py"', text)


if __name__ == "__main__":
    unittest.main()
