# Composition Contract

## Ownership

| Artifact | Authority | Composition behavior |
|---|---|---|
| Root `AGENTS.md` or `CLAUDE.md` | Generic harness | Merge research routing manually |
| `feature_list.json` | Generic harness | Optional compatibility projection only |
| `progress.md` | Shared single file | Add research sections manually |
| `session-handoff.md` | Shared single file | Add research recovery fields manually |
| `init.sh` and main gates | Generic harness | Chain research validation manually |
| `work_items.json` | Research harness | Authoritative research work graph |
| Research contract and registries | Research harness | Preserve their schemas and identities |
| `memory/index.md` and research rules | Composition layer | Create only when absent |

Never maintain two writable authorities for the same state. If both feature and research work views exist, declare `work_items.json` authoritative for research and regenerate any projection from it.

## Actions

- `create`: absent overlay file; safe to create after reviewing the plan.
- `compatible`: existing file has identical content.
- `merge_required`: existing file or shared root artifact requires human-reviewed integration.
- `conflict`: file/directory type mismatch or unsafe target condition.
- `skip`: optional capability is not applicable.

Planning is read-only. Save the reviewed plan with `--save-plan`; later apply that exact document with `--apply-plan`. Applying rechecks target and overlay fingerprints before writing and uses exclusive file creation. Unknown plan schema versions, malformed entries, target mismatches, stale targets, and changed overlay sources are rejected.
