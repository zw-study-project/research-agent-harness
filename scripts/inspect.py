from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import NamedTuple


GENERIC_CAPABILITIES = {
    "instructions": ("AGENTS.md", "CLAUDE.md"),
    "state": ("progress.md",),
    "verification": ("init.sh", "init.ps1", "scripts/verify-fast.ps1", "scripts/verify-full.ps1"),
    "lifecycle": ("session-handoff.md",),
}
RESEARCH_PATHS = (
    "docs/research-contract.md",
    "work_items.json",
    "resources/registry.json",
    "literature/registry.json",
    "explorations/registry.json",
    "experiments/registry.json",
)


class LayerStatus(NamedTuple):
    present: tuple[str, ...]
    missing: tuple[str, ...]


class InspectionResult(NamedTuple):
    target: str
    generic: LayerStatus
    research: LayerStatus
    state: str
    findings: tuple[str, ...]


def _layer_status(target: Path, expected: tuple[str, ...]) -> LayerStatus:
    present = tuple(path for path in expected if (target / path).is_file())
    missing = tuple(path for path in expected if path not in present)
    return LayerStatus(present=present, missing=missing)


def _generic_status(target: Path) -> LayerStatus:
    present: list[str] = []
    missing: list[str] = []
    for capability, alternatives in GENERIC_CAPABILITIES.items():
        match = next((path for path in alternatives if (target / path).is_file()), None)
        if match:
            present.append(f"{capability}:{match}")
        else:
            missing.append(capability)
    if (target / "feature_list.json").is_file():
        present.append("compatibility_projection:feature_list.json")
    return LayerStatus(tuple(present), tuple(missing))


def inspect_target(target: Path) -> InspectionResult:
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"target is not a directory: {target}")
    generic = _generic_status(target)
    research = _layer_status(target, RESEARCH_PATHS)
    generic_complete = not generic.missing
    research_complete = not research.missing
    any_present = bool(generic.present or research.present)
    if generic_complete and research_complete:
        state = "composed"
    elif generic_complete:
        state = "generic_only"
    elif research_complete:
        state = "research_only"
    elif any_present:
        state = "partial"
    else:
        state = "empty"
    findings = tuple(
        message
        for missing, message in (
            (generic.missing, "generic harness is incomplete"),
            (research.missing, "research harness is incomplete"),
        )
        if missing
    )
    return InspectionResult(
        target=str(target), generic=generic, research=research, state=state, findings=findings
    )


def result_to_dict(result: InspectionResult) -> dict[str, object]:
    return {
        "target": result.target,
        "generic": {"present": result.generic.present, "missing": result.generic.missing},
        "research": {"present": result.research.present, "missing": result.research.missing},
        "state": result.state,
        "findings": result.findings,
    }


def _configure_json_stdout(enabled: bool) -> None:
    if enabled and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect generic and research harness layers")
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    _configure_json_stdout(args.json)
    try:
        result = inspect_target(args.target)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(f"State: {result.state}")
        for finding in result.findings:
            print(f"- {finding}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
