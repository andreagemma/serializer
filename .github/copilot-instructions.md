# Copilot Instructions for serializer

## Project Description

serializer is a typed Python package for robust object serialization with optional compression codecs and format metadata.

## Scope

These instructions apply to the entire repository.

## Project Context

- This is a Python package with sources under `src/serializer`.
- Keep backward compatibility with existing public APIs unless explicitly requested.

## Development Rules

- Prefer small, targeted changes.
- Keep code typed and add type annotations on public functions, classes, and variables.
- Preserve existing behavior for public APIs unless explicitly requested otherwise.
- Add or update tests under `tests/` for behavior changes.
- Keep style consistent with the existing codebase.
- Avoid heavy new dependencies unless clearly justified.

## Quality Checks

Before finalizing changes, run:

- `pytest -q`

If relevant to modified files, also run project quality scripts.

## Verification and Alignment

- Keep `CHANGELOG.md` updated when behavior, interfaces, or CI/release workflows change.
- Keep `README.md` and docs content aligned with code changes.
- Verify dependencies are correctly declared in `pyproject.toml`.
- Keep `MANIFEST.in` updated where applicable.

## Third-Party Licensing Workflow

Based on dependencies declared in `pyproject.toml`:

- Archive third-party licenses under `licenses/third_party/packages/<package>/`.
- Save at least one `LICENSE` file for each package.
- Save `COPYING` too when upstream provides it.
- Keep `licenses/third_party/summary.tsv` updated with columns:
  `package`, `version`, `license_file`, `source_url`.
- Keep `THIRD_PARTY_NOTICES.md` updated.
- Ensure `MANIFEST.in` includes these artifacts when present.

## Quality And Fix Workflow

- Always run commands in the current active environment.
- If the user asks for a quality verification, run in this order:
  - `ruff check .`
  - `ruff format --check .`
  - `mypy`
- If the user asks for a fix, apply corrective edits and then run quality checks.
- If the user asks only for formatting, run only:
  - `ruff format .`
- Otherwise, prefer fixing issues reported by `ruff check` and `mypy` without changing runtime functionality.
- After changes, verify with tests (`pytest -q`, or focused pytest selection when appropriate).

## Safety

- Do not run destructive git history operations.
- Ask for clarification before broad refactors when requirements are ambiguous.
