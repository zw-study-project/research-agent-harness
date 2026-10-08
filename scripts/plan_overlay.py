from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import NamedTuple


SHARED_PATHS = {
    "AGENTS.md",
    "CLAUDE.md",
    "progress.md",
    "session-handoff.md",
    "init.sh",
    "feature_list.json",
}
PLAN_SCHEMA_VERSION = 1
PLAN_ACTIONS = {"create", "compatible", "merge_required", "conflict", "skip"}
MERGE_GUIDANCE = {
    "AGENTS.md": "add routing to docs/research-contract.md, work_items.json, and agent research rules",
    "CLAUDE.md": "add routing to docs/research-contract.md, work_items.json, and agent research rules",
    "progress.md": "add Current Research Claim, decisions, risks, and verification evidence sections",
    "session-handoff.md": "add active work item, current claim, frozen variables, risks, next evidence, and one next exact command",
    "init.sh": "chain the project-local research validator before the existing full gate",
    "feature_list.json": "declare this a compatibility projection of authoritative work_items.json; do not edit both",
}


class PlanEntry(NamedTuple):
    path: str
    action: str
    source_sha256: str | None
    target_sha256: str | None
    reason: str


class OverlayPlan(NamedTuple):
    target: str
    target_fingerprint: str
    source_fingerprint: str
    entries: tuple[PlanEntry, ...]


class StalePlanError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _blocked_by_parent(target: Path, relative: Path) -> bool:
    current = target
    for part in relative.parts[:-1]:
        current = current / part
        if current.exists() and not current.is_dir():
            return True
    return False


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath((str(root.resolve()), str(candidate.resolve()))) == str(root.resolve())
    except (OSError, ValueError):
        return False


def _state(path: Path) -> dict[str, str | None]:
    if path.is_file():
        return {"type": "file", "sha256": _sha256(path)}
    if path.is_dir():
        return {"type": "directory", "sha256": None}
    return {"type": "missing", "sha256": None}


def _relevant_paths(overlay_root: Path) -> tuple[Path, ...]:
    paths: set[Path] = {Path(item) for item in SHARED_PATHS}
    for source in overlay_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(overlay_root)
        paths.add(relative)
        parent = relative.parent
        while parent != Path("."):
            paths.add(parent)
            parent = parent.parent
    return tuple(sorted(paths, key=lambda value: value.as_posix()))


def _fingerprint(target: Path, overlay_root: Path) -> str:
    snapshot = {
        relative.as_posix(): _state(target / relative)
        for relative in _relevant_paths(overlay_root)
    }
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_fingerprint(overlay_root: Path) -> str:
    snapshot = {
        source.relative_to(overlay_root).as_posix(): _sha256(source)
        for source in overlay_root.rglob("*")
        if source.is_file()
    }
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_plan(target: Path, overlay_root: Path) -> OverlayPlan:
    target = target.resolve()
    overlay_root = overlay_root.resolve()
    if not target.is_dir():
        raise ValueError(f"target is not a directory: {target}")
    if not overlay_root.is_dir():
        raise ValueError(f"overlay root is not a directory: {overlay_root}")
    entries: list[PlanEntry] = []
    for shared in sorted(SHARED_PATHS):
        destination = target / shared
        if destination.is_file():
            entries.append(PlanEntry(shared, "merge_required", None, _sha256(destination), MERGE_GUIDANCE[shared]))
        elif destination.exists():
            entries.append(PlanEntry(shared, "conflict", None, None, "shared path is not a file"))
        else:
            entries.append(PlanEntry(shared, "skip", None, None, "shared file is not supplied by the overlay"))
    for source in sorted((path for path in overlay_root.rglob("*") if path.is_file()), key=lambda value: value.as_posix()):
        relative = source.relative_to(overlay_root)
        relative_text = relative.as_posix()
        destination = target / relative
        source_hash = _sha256(source)
        if not _is_within(target, destination.parent) or _blocked_by_parent(target, relative) or (destination.exists() and not destination.is_file()):
            entries.append(PlanEntry(relative_text, "conflict", source_hash, None, "file/directory type mismatch"))
        elif destination.is_file():
            target_hash = _sha256(destination)
            action = "compatible" if target_hash == source_hash else "merge_required"
            reason = "existing content is identical" if action == "compatible" else "existing project file requires manual merge"
            entries.append(PlanEntry(relative_text, action, source_hash, target_hash, reason))
        else:
            entries.append(PlanEntry(relative_text, "create", source_hash, None, "overlay file is absent"))
    return OverlayPlan(str(target), _fingerprint(target, overlay_root), _source_fingerprint(overlay_root), tuple(entries))


def apply_plan(plan: OverlayPlan, overlay_root: Path) -> tuple[str, ...]:
    target = Path(plan.target)
    current = build_plan(target, overlay_root)
    if current.target_fingerprint != plan.target_fingerprint or current.source_fingerprint != plan.source_fingerprint:
        raise StalePlanError("target or overlay source changed after planning; generate a new plan")
    if any(entry.action == "conflict" for entry in plan.entries):
        raise ValueError("overlay plan contains conflicts")
    payloads: list[tuple[PlanEntry, bytes]] = []
    for entry in plan.entries:
        if entry.action != "create":
            continue
        source = overlay_root / entry.path
        destination = target / entry.path
        if not _is_within(target, destination.parent):
            raise StalePlanError(f"destination escapes target: {entry.path}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry.source_sha256:
            raise StalePlanError(f"overlay source changed: {entry.path}")
        payloads.append((entry, data))
    created: list[str] = []
    for entry, data in payloads:
        destination = target / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(data)
        created.append(entry.path)
    return tuple(created)


def _plan_dict(plan: OverlayPlan, created: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "target": plan.target,
        "target_fingerprint": plan.target_fingerprint,
        "source_fingerprint": plan.source_fingerprint,
        "entries": [entry._asdict() for entry in plan.entries],
        "created": list(created),
    }


def save_plan(plan: OverlayPlan, path: Path) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    document = _plan_dict(plan)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_plan(path: Path) -> OverlayPlan:
    path = path.resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read plan {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported or missing plan schema_version")
    required_strings = ("target", "target_fingerprint", "source_fingerprint")
    if any(not isinstance(document.get(key), str) or not document[key] for key in required_strings):
        raise ValueError("plan is missing target or fingerprint fields")
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("plan entries must be a list")
    entries: list[PlanEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ValueError("each plan entry must be an object")
        if set(raw) != {"path", "action", "source_sha256", "target_sha256", "reason"}:
            raise ValueError("plan entry fields are invalid")
        if not isinstance(raw["path"], str) or not raw["path"] or raw["action"] not in PLAN_ACTIONS:
            raise ValueError("plan entry path or action is invalid")
        if not isinstance(raw["reason"], str):
            raise ValueError("plan entry reason must be text")
        for hash_key in ("source_sha256", "target_sha256"):
            if raw[hash_key] is not None and not isinstance(raw[hash_key], str):
                raise ValueError(f"plan entry {hash_key} must be text or null")
        entries.append(PlanEntry(**raw))
    return OverlayPlan(
        target=document["target"],
        target_fingerprint=document["target_fingerprint"],
        source_fingerprint=document["source_fingerprint"],
        entries=tuple(entries),
    )


def _configure_json_stdout(enabled: bool) -> None:
    if enabled and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a non-overwriting research harness overlay")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--json", action="store_true")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--apply-plan", type=Path)
    parser.add_argument("--save-plan", type=Path)
    args = parser.parse_args(argv)
    _configure_json_stdout(args.json)
    overlay_root = Path(__file__).resolve().parents[1] / "assets" / "overlay"
    try:
        if args.apply_plan:
            if args.save_plan:
                parser.error("--save-plan cannot be combined with --apply-plan")
            plan = load_plan(args.apply_plan)
            if args.target and args.target.resolve() != Path(plan.target).resolve():
                raise ValueError("--target does not match the saved plan target")
            created = apply_plan(plan, overlay_root)
        else:
            if args.target is None:
                parser.error("--target is required unless --apply-plan is used")
            if args.apply and args.save_plan:
                parser.error("--save-plan cannot be combined with --apply")
            plan = build_plan(args.target, overlay_root)
            if args.save_plan:
                save_plan(plan, args.save_plan)
            created = apply_plan(plan, overlay_root) if args.apply else ()
    except (ValueError, StalePlanError, FileExistsError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_plan_dict(plan, created), ensure_ascii=False, indent=2))
    else:
        for entry in plan.entries:
            print(f"{entry.action.upper()} {entry.path}: {entry.reason}")
        for path in created:
            print(f"CREATED {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
