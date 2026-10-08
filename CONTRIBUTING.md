# Contributing

Thanks for helping make research agents safer and more reproducible.

## Before you start

- Search existing issues before opening a new one.
- Keep changes focused on composition safety, research workflow reliability, or compatibility.
- Open an issue before proposing a large change to file ownership, plan semantics, or validation rules.

## Development setup

The runtime and tests use only the Python standard library. Python 3.10 or newer is recommended.

```bash
git clone https://github.com/zw-study-project/research-agent-harness.git
cd research-agent-harness
python -m unittest discover -s tests -v
```

## Pull requests

1. Add or update tests for behavior changes.
2. Preserve the non-overwrite guarantee.
3. Keep saved-plan validation fail-closed: malformed or stale plans must not write files.
4. Update `README.md`, `SKILL.md`, or the relevant reference when behavior changes.
5. Run the complete test suite and include the result in the pull-request description.

Small, reviewable pull requests are preferred. Explain the failure mode your change addresses and the evidence that the new behavior is safe.

## Reporting bugs

Include the operating system, Python version, command, expected result, actual result, and a minimal project layout when possible. Remove credentials and private research data before attaching logs or fixtures.

