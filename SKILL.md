---
name: research-agent-harness
description: Use when building or auditing a computational research agent environment that must combine a generic agent harness with research contracts, evidence discipline, experiment lineage, bounded memory, and non-overwriting project adoption.
---

# Research Agent Harness

Compose, do not duplicate. Use `harness-creator` for the generic reliability base and `reusable-research-harness` for the research control plane. This skill inspects their project artifacts, plans a safe overlay, and validates the combined contract.

## Workflow

1. Inspect the target and current changes. Run `python scripts/inspect.py --target <project> --json`.
2. If the generic layer is missing, use `harness-creator` first. If the research layer is missing, use `reusable-research-harness` without overwriting existing files.
3. Read [composition contract](references/composition-contract.md) and save a reviewable plan: `python scripts/plan_overlay.py --target <project> --save-plan <plan.json> --json`.
4. Review every `merge_required` and `conflict`. Never replace shared root files automatically.
5. Apply the exact reviewed plan with `python scripts/plan_overlay.py --apply-plan <plan.json> --json`. The command must reject target or overlay changes since planning.
6. Merge the reported research-routing fragments into the existing agent guide, progress, handoff, and verification entry points.
7. Run the source harness validators, then `python scripts/validate_composition.py --target <project> --json`, then the project's fast and full gates.
8. Record evidence, risks, the current bounded claim, and one exact next command.

Do not edit or copy the source skill packages. Project artifacts are the integration boundary. Default to inspection and saved dry-run plans; apply commands only create absent overlay files.

## Load References as Needed

- File ownership and composition modes: [Composition Contract](references/composition-contract.md)
- Startup, work, and end-of-session behavior: [Research Agent Workflow](references/research-agent-workflow.md)
- Evidence levels and claim ceilings: [Evidence and Claims](references/evidence-and-claims.md)
- Smoke, pilot, formal comparison, and diagnostics: [Experiment Lifecycle](references/experiment-lifecycle.md)
- Bounded durable context: [Memory and Handoff](references/memory-and-handoff.md)
- Parallel research ownership: [Multi-Agent Research](references/multi-agent-research.md)

## Completion Gate

A composed research harness is ready only when shared-file merges were reviewed, both source layers validate, composition validation passes, project gates run, and neither source skill changed.
