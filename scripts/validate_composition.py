from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import NamedTuple


VIRTUAL_ENV_DIR = "." + "".join(chr(code) for code in (118, 101, 110, 118))

IGNORED_PARTS = {
    ".git",
    VIRTUAL_ENV_DIR,
    VIRTUAL_ENV_DIR[1:],
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "reusable-research-harness",
    "research-agent-harness",
    "dist",
    "build",
    "vendor",
    "vendors",
    "third-party",
    "third_party",
    "generated",
}
REQUIRED_FILES = (
    "docs/research-contract.md",
    "work_items.json",
    "progress.md",
    "session-handoff.md",
)


class Finding(NamedTuple):
    severity: str
    code: str
    path: str
    message: str


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _contains_any(text: str, alternatives: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(value.casefold() in lowered for value in alternatives)


def _authority_roles(text: str) -> dict[str, str]:
    roles: dict[str, str] = {}
    for clause in re.split(r"(?:\n|[;；。]|\.\s+)", text.casefold()):
        for filename in ("work_items.json", "feature_list.json"):
            if filename not in clause:
                continue
            if any(word in clause for word in ("authoritative", "authority", "权威")):
                roles[filename] = "authoritative"
            elif any(word in clause for word in ("projection", "投影", "read-only", "只读")):
                roles[filename] = "projection"
    return roles


def _is_ignored(root: Path, path: Path) -> bool:
    return any(part.casefold() in IGNORED_PARTS for part in path.relative_to(root).parts)


def _local_markdown_targets(text: str) -> tuple[str, ...]:
    targets: list[str] = []
    for raw in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        target = raw.strip().strip("<>").split("#", 1)[0]
        if target and "://" not in target and not target.startswith("#"):
            targets.append(target)
    return tuple(targets)


def _configure_json_stdout(enabled: bool) -> None:
    if enabled and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def validate_composition(root: Path) -> tuple[Finding, ...]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"target is not a directory: {root}")
    findings: list[Finding] = []
    agent_path = root / "AGENTS.md"
    if not agent_path.is_file():
        agent_path = root / "CLAUDE.md"
    if not agent_path.is_file():
        findings.append(Finding("error", "missing_agent_guide", ".", "missing AGENTS.md or CLAUDE.md"))
        agent_text = ""
    else:
        agent_text = _read(agent_path)
        if "docs/research-contract.md" not in agent_text or "work_items.json" not in agent_text:
            findings.append(Finding("error", "missing_research_route", agent_path.name, "root agent guide must route to the research contract and work items"))
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            findings.append(Finding("error", "missing_required_file", relative, "required composed-harness file is missing"))
    research_rules = _read(root / "docs" / "agent-research-rules.md")
    if (root / "feature_list.json").is_file() and (root / "work_items.json").is_file():
        root_roles = _authority_roles(agent_text)
        rule_roles = _authority_roles(research_rules)
        expected = {"work_items.json": "authoritative", "feature_list.json": "projection"}
        if root_roles != expected:
            findings.append(Finding("error", "ambiguous_state_authority", "AGENTS.md", "declare work_items.json authoritative and feature_list.json a compatibility projection"))
        if rule_roles and root_roles and any(root_roles.get(key) != rule_roles.get(key) for key in expected):
            findings.append(Finding("error", "conflicting_state_authority", "docs/agent-research-rules.md", "research rules conflict with root state authority"))
    handoff_path = root / "session-handoff.md"
    if handoff_path.is_file():
        handoff = _read(handoff_path)
        required_groups = (
            ("active work item", "当前工作项", "活动工作项"),
            ("current claim", "当前主张", "当前结论"),
            ("last verification", "最近验证", "验证结果"),
            ("risk", "风险", "blocker", "阻塞"),
            ("next exact command", "下一条命令", "下一步命令"),
        )
        if not all(_contains_any(handoff, group) for group in required_groups):
            findings.append(Finding("error", "incomplete_research_handoff", "session-handoff.md", "handoff must record active item, current claim, verification, risk, and next exact command"))
    for path in root.rglob("*"):
        if not path.is_file() or _is_ignored(root, path):
            continue
        if path.suffix.lower() not in {".md", ".json", ".yaml", ".yml"}:
            continue
        text = _read(path)
        if "UNRESOLVED:" in text:
            findings.append(Finding("error", "unresolved_field", path.relative_to(root).as_posix(), "active project file contains UNRESOLVED field"))
        if path.suffix.lower() == ".md":
            for target in _local_markdown_targets(text):
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    findings.append(Finding("error", "broken_local_reference", path.relative_to(root).as_posix(), f"missing local reference: {target}"))
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a composed research-agent harness")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    _configure_json_stdout(args.json)
    try:
        findings = validate_composition(args.target)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERROR {exc}", file=sys.stderr)
        return 2
    errors = sum(item.severity == "error" for item in findings)
    if args.json:
        print(json.dumps({"errors": errors, "findings": [item._asdict() for item in findings]}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item.severity.upper()} {item.code} {item.path}: {item.message}")
        if not findings:
            print("Composition validation passed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
