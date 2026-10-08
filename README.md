# Research Agent Harness

> A safety-first composition layer for research agents that need reproducible experiments, evidence-aware claims, durable handoffs, and zero-surprise adoption.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen)](#validation)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-7C3AED)](SKILL.md)

Research agents fail in ways ordinary coding-agent harnesses do not catch. A test can pass while the scientific claim is still too broad. An experiment can run while silently changing a frozen variable. A new “memory” file can create a second source of truth. A helpful installer can overwrite the project rules it was supposed to preserve.

Research Agent Harness addresses those failures by composing a generic coding-agent harness with a research control plane—without duplicating ownership or overwriting existing project files.

## Why this exists

Most agent harnesses focus on code completion: instructions, task state, tests, and session recovery. Computational research also needs:

- **Evidence discipline** — distinguish code facts, engineering checks, measurements, external claims, hypotheses, and interpretations.
- **Claim ceilings** — never let a result support a stronger conclusion than the evidence allows.
- **Experiment lineage** — keep scientific variables, protocols, artifacts, and comparisons traceable.
- **Bounded memory** — persist only the context needed to resume work without turning chat history into an undocumented database.
- **Explicit state authority** — prevent `feature_list.json`, `work_items.json`, progress notes, and handoffs from becoming competing sources of truth.
- **Safe adoption** — inspect first, produce a reviewable plan, and refuse stale or conflicting writes.

## What makes it different

| Typical installer | Research Agent Harness |
|---|---|
| Copies templates immediately | Inspects the target before planning changes |
| Overwrites or silently merges files | Never overwrites shared root files |
| Applies the latest inferred state | Applies only the exact reviewed plan |
| Treats passing tests as proof | Separates engineering verification from research evidence |
| Stores broad conversational memory | Uses bounded, indexed, task-relevant memory |
| Adds another task tracker | Declares one authoritative research work graph |

The core safety mechanism is a two-phase workflow:

```text
inspect target
      │
      ▼
build + save plan ──► human review of merge_required / conflict
      │
      ▼
re-check target and source fingerprints
      │
      ├── changed?  abort safely
      │
      └── unchanged? create absent overlay files only
```

## Features

- Detects generic, research, partial, empty, and already-composed harness states.
- Plans overlay changes as `create`, `compatible`, `merge_required`, `conflict`, or `skip`.
- Saves portable JSON plans for review before any write occurs.
- Fingerprints both the target and overlay source to reject stale plans.
- Uses exclusive file creation so existing files cannot be replaced accidentally.
- Validates research routing, state authority, handoff completeness, required files, unresolved fields, and local Markdown links.
- Handles Unicode paths and Windows projects.
- Includes research protocols for evidence, experiment lifecycle, memory, handoff, and multi-agent ownership.
- Ships with a PowerShell composition-verification hook and ready-to-use project overlay files.

## Quick start

### 1. Install the skill

Clone this repository into your agent's skills directory, or copy the folder there:

```bash
git clone https://github.com/zw-study-project/research-agent-harness.git
```

For Codex, a typical local installation is:

```text
~/.codex/skills/research-agent-harness/
```

The repository is also usable directly from a checkout; the Python scripts have no third-party runtime dependencies.

### 2. Inspect a target project

```bash
python scripts/inspect.py --target /path/to/research-project --json
```

The result reports whether the generic reliability layer and research layer are present, incomplete, or already composed.

### 3. Generate a reviewable overlay plan

```bash
python scripts/plan_overlay.py \
  --target /path/to/research-project \
  --save-plan /path/to/reviewed-plan.json \
  --json
```

Review every entry marked `merge_required` or `conflict`. Shared project files such as `AGENTS.md`, `progress.md`, `session-handoff.md`, and verification entry points are deliberately never merged automatically.

### 4. Apply the exact reviewed plan

```bash
python scripts/plan_overlay.py \
  --apply-plan /path/to/reviewed-plan.json \
  --json
```

If either the target project or overlay changed after planning, application stops before writing anything. Generate and review a new plan instead.

### 5. Merge shared-file guidance and validate

After manually integrating the reported routing fragments into the project's existing shared files:

```bash
python scripts/validate_composition.py \
  --target /path/to/research-project \
  --json
```

Then run the source harness validators and the target project's own fast and full gates.

## Composition model

Research Agent Harness is intentionally a composition layer, not a monolithic framework.

```text
Generic agent harness
  ├─ startup instructions
  ├─ feature / task state
  ├─ verification gates
  └─ session lifecycle
           +
Research control plane
  ├─ research contract
  ├─ authoritative work graph
  ├─ evidence and claim rules
  ├─ experiment registries
  └─ bounded memory
           │
           ▼
Research Agent Harness
  ├─ inspection
  ├─ non-overwriting overlay plan
  ├─ stale-plan protection
  └─ composition validation
```

The expected source layers are:

- [`harness-creator`](https://github.com/openai/skills) or an equivalent generic reliability harness.
- A research harness that provides the project research contract, `work_items.json`, and research registries.

The composition contract is tool-agnostic: alternative source harnesses work if they provide the same project-level responsibilities and explicit ownership boundaries.

## Project structure

```text
research-agent-harness/
├── SKILL.md                         # Agent-facing workflow and completion gate
├── agents/openai.yaml               # Skill discovery metadata
├── scripts/
│   ├── inspect.py                   # Detect target harness state
│   ├── plan_overlay.py              # Plan and safely apply the overlay
│   └── validate_composition.py      # Validate the combined contract
├── assets/overlay/                  # Files created only when absent
├── references/                      # Research workflow and safety contracts
└── tests/                           # Unit and contract tests
```

## Key design guarantees

### No hidden overwrite

Overlay application opens destination files in exclusive-create mode. Existing shared files are reported for manual integration rather than replaced.

### Review means review

The saved plan contains target and source fingerprints. Application recomputes both fingerprints and rejects the operation if anything relevant changed.

### One authority per state

When both generic and research work views exist, `work_items.json` is authoritative for research. Any `feature_list.json` view must be a compatibility projection, not a second writable state store.

### Evidence before claims

The workflow requires the agent to record verification evidence, risks, a bounded current claim, frozen variables, the next evidence needed, and one copy-pasteable next command.

## Validation

Run the complete test suite with the Python standard library:

```bash
python -m unittest discover -s tests -v
```

Current suite: **43 tests**, covering inspection, plan serialization, stale-plan rejection, non-overwrite behavior, Unicode paths, path escape protection, contract validation, and Markdown reference integrity.

## Use cases

- Reproducible ML and data-science experiments run by coding agents.
- Long-running literature-to-experiment research workflows.
- Agent teams that need explicit write scopes and merge authority.
- Existing repositories that cannot tolerate template installers overwriting local conventions.
- Research projects that need auditable handoffs across sessions or models.

## Roadmap

- Cross-platform shell verification entry points.
- Example composed projects for common research stacks.
- Machine-readable composition reports for CI annotations.
- More adapters for existing agent harness ecosystems.
- End-to-end benchmarks on representative research tasks.

Have a use case or integration idea? [Open an issue](https://github.com/zw-study-project/research-agent-harness/issues) or start a discussion.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, test, and pull-request guidance. For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

Released under the [MIT License](LICENSE).

