# Python Library Repository Standard

## Purpose

Use this document to create a modern, publishable Python library repository with the
same structure and engineering conventions as `ga-serializer`.

Replace these placeholders before implementation:

- `<distribution-name>`: PyPI name, usually kebab-case, for example `ga-serializer`.
- `<package-name>`: importable Python package, always a valid identifier, for example
  `serializer`.
- `<github-owner>` and `<repository-name>`: GitHub coordinates.
- `<description>`: one concise sentence describing the library.
- `<initial-version>`: normally `0.1.0`.

The distribution name and import package may differ. Installation can therefore be
`pip install <distribution-name>` while usage is `import <package-name>`.

## Non-negotiable conventions

- Support Python 3.10 and later.
- Use a `src/` layout and PEP 621 metadata in `pyproject.toml`.
- Use `setuptools` as the PEP 517 build backend; do not add `setup.py`.
- Keep the version in Python code as the single source of truth.
- Ship typing information with `py.typed`.
- Use `pytest`, branch coverage, Ruff, and strict mypy.
- Build both wheel and source distribution and validate them with Twine.
- Use GitHub Actions based on Node.js 24 runtimes.
- Publish to PyPI with Trusted Publishing; never store a PyPI token in the repository.
- Keep the README in concise, technical English with executable examples.
- Use Conventional Commit messages and keep `main` releasable.

## Repository layout

Create this structure, omitting feature-specific files only when they are genuinely
unnecessary:

```text
<repository-name>/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── create-release.yml
│       └── release.yml
├── benchmarks/                 # optional, never imported by the package
│   └── benchmark_<feature>.py
├── src/
│   └── <package-name>/
│       ├── __init__.py         # curated public API only
│       ├── _api.py             # primary implementation
│       ├── _version.py         # single version source
│       ├── exceptions.py       # public exceptions and warnings
│       └── py.typed
├── tests/
│   ├── test_api.py
│   └── test_version.py
├── .gitattributes
├── .gitignore
├── AGENT.md
├── LICENSE
├── README.md
└── pyproject.toml
```

Initialize Git on `main` and make one intentional root commit only after the complete
baseline passes verification:

```bash
git init -b main
git add .
git commit -m "feat: create modern <distribution-name> package"
```

Do not commit virtual environments, caches, build outputs, coverage files, IDE state,
or generated package metadata.

## Packaging

### Version source

Store the version only in `src/<package-name>/_version.py`:

```python
"""Package version: the single source of truth for builds and releases."""

__version__ = "<initial-version>"
```

Re-export it from `src/<package-name>/__init__.py`:

```python
from ._version import __version__

__all__ = ["__version__"]
```

Public names added later must be imported explicitly and listed in `__all__`. Keep
internal modules private with a leading underscore.

### `pyproject.toml`

Start from this configuration and add only justified runtime dependencies and extras:

```toml
[build-system]
requires = ["setuptools>=77", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "<distribution-name>"
dynamic = ["version"]
description = "<description>"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Intended Audience :: Developers",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Typing :: Typed",
]
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8.0", "pytest-cov>=5.0"]
dev = [
  "build>=1.2",
  "mypy>=1.10",
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "ruff>=0.5",
  "twine>=5.1",
]

[project.urls]
Documentation = "https://github.com/<github-owner>/<repository-name>#readme"
Issues = "https://github.com/<github-owner>/<repository-name>/issues"
Source = "https://github.com/<github-owner>/<repository-name>"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
<package-name> = ["py.typed"]

[tool.setuptools.dynamic]
version = {attr = "<package-name>._version.__version__"}

[tool.pytest.ini_options]
addopts = "-ra --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["<package-name>"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.10"
strict = true
files = ["src"]
```

Use extras for optional integrations. Optional dependencies must be imported lazily
inside the code path that needs them. Missing optional dependencies must produce a
specific warning or exception and must never silently generate incorrect data.

## Code conventions

- Add `from __future__ import annotations` to Python modules that use annotations.
- Type every public function, method, class attribute, and return value.
- Prefer explicit exceptions over assertions for user input validation.
- Define a package-specific base exception and warning hierarchy in `exceptions.py`.
- Keep functional APIs familiar when a standard-library convention exists.
- Use immutable configuration objects for fluent APIs; configuration methods return a
  new object rather than mutating shared state.
- Use method chaining only where it improves composition or reuse.
- Do not import heavy or optional modules at package import time.
- Never hide a broken installed dependency by catching an unrelated transitive import
  failure.
- Document security boundaries prominently when loading external or executable data.
- Preserve backward compatibility deliberately; test any supported legacy format.

## Tests

Tests belong in `tests/` and must use the public API unless a test explicitly validates
an internal contract.

Required coverage:

- Normal round trips and representative input types.
- Empty, `None`, boundary, malformed, and corrupted inputs where applicable.
- Paths and open streams when the API supports I/O.
- Every built-in backend or codec.
- Missing optional dependency behavior, tested with mocks.
- Strict-mode or no-fallback behavior.
- Public fluent configuration and immutability.
- Version re-export from `_version.py`.
- Build artifact smoke test for at least one wheel.

Minimum version test:

```python
import re

import <package-name>
from <package-name>._version import __version__


def test_public_version_uses_code_source() -> None:
    assert <package-name>.__version__ == __version__
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)?", __version__)
```

Run locally:

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src
pytest --cov=<package-name> --cov-report=term-missing
ruff check .
mypy
python -m pip check
```

Do not weaken lint or type-checking rules merely to make CI green. Fix the underlying
code or add a narrowly scoped, documented suppression when a third-party API is truly
untyped.

## Build verification

Builds must be reproducible from a clean checkout:

```bash
python -m build
python -m twine check dist/*
```

Verify all of the following before release:

- Both `.whl` and `.tar.gz` exist.
- Wheel metadata uses `<distribution-name>` and the version from `_version.py`.
- The wheel contains `<package-name>/_version.py` and `py.typed`.
- Importing from the built wheel exposes the expected `__version__` and public API.
- `python -m pip check` reports no dependency conflicts.

`build/`, `dist/`, `*.egg-info/`, and generated archives must remain ignored by Git.

## README style

Write `README.md` in technical, concise English. It must stand on its own on both
GitHub and PyPI. Use this order:

1. Project name and CI/PyPI/Python badges.
2. One-paragraph purpose and backend behavior.
3. Installation, including extras.
4. Minimal runnable quick start.
5. Paths, streams, fluent APIs, or other major usage patterns.
6. Supported integrations or codecs and their dependencies.
7. Error and fallback semantics.
8. Legacy compatibility, if supported.
9. Security warning.
10. Benchmarks, if present.
11. Development commands.
12. Release instructions and license.

README rules:

- State clearly when the distribution and import names differ.
- Keep examples executable and aligned with the current public API.
- Explain defaults instead of forcing readers to infer them.
- Use tables only for genuine comparisons or exact mappings.
- Avoid development history, marketing filler, and undocumented placeholders.
- Explain that integrity checks do not imply cryptographic authenticity.
- If generated benchmark results are embedded, delimit them with stable comments so a
  script can replace only that section:

```markdown
<!-- <distribution-name>-benchmark:start -->

_Generated Markdown results._

<!-- <distribution-name>-benchmark:end -->
```

## GitHub Actions

Grant the smallest possible permission set. Use current Node.js 24 action versions:

- `actions/checkout@v5`
- `actions/setup-python@v6`
- `actions/upload-artifact@v7`
- `actions/download-artifact@v8`

### CI workflow

`.github/workflows/ci.yml` must run on pushes to `main`, pull requests, and manual
dispatch. It contains two jobs:

1. `test`: Python 3.10 through 3.14 on Ubuntu, plus Python 3.10 and 3.14 boundary
   coverage on Windows and macOS. Run install, compileall, pytest with coverage, and
   `pip check`.
2. `quality`: Python 3.10 on Ubuntu. Run Ruff and strict mypy.

Use `fail-fast: false` for the version matrix and `permissions: contents: read` for the
workflow.

### Build and publish workflow

`.github/workflows/release.yml` must:

1. Check out the exact triggering ref.
2. Use Python 3.12.
3. Install `build` and `twine`.
4. Run `python -m build` and `python -m twine check dist/*`.
5. Upload the distributions as one Actions artifact.
6. Download that exact artifact in the publish job.
7. Publish with `pypa/gh-action-pypi-publish@release/v1`.

The publish job must use a protected GitHub environment named `pypi` and only that job
receives `permissions: id-token: write`. Never pass a username, password, or API token
when Trusted Publishing is enabled.

Configure the matching publisher in PyPI with exact values:

- PyPI project: `<distribution-name>`
- GitHub owner: `<github-owner>`
- Repository: `<repository-name>`
- Workflow filename: `release.yml` (not the full path)
- Environment: `pypi`

For a package that does not yet exist on PyPI, create a Pending Trusted Publisher
before the first release. An `invalid-publisher` OIDC error means these values do not
match the workflow claims; it is not fixed by adding a secret.

### Create-release workflow

`.github/workflows/create-release.yml` is manually dispatched and accepts an optional
complete `tag` override. Its default behavior is:

1. Import `__version__` from `<package-name>._version`.
2. Resolve the tag to `v<version>` when no override is supplied.
3. Validate the tag with `git check-ref-format`.
4. Create a GitHub Release with generated notes.
5. Explicitly dispatch `release.yml` at the new tag with publication enabled.

Use `permissions: contents: write` to create the tag/release and `actions: write` to
dispatch the publishing workflow. Do not duplicate build commands in
`create-release.yml`; `release.yml` owns build artifacts and publishing.

The explicit dispatch is required because events created with the repository
`GITHUB_TOKEN` do not normally trigger another workflow. A release workflow must not
depend on accidental recursive events.

## Release process

Follow this sequence for every release:

1. Confirm the worktree is clean and `main` is synchronized.
2. Run tests, Ruff, mypy, dependency checks, build, and Twine validation.
3. Update `src/<package-name>/_version.py`; never duplicate the version elsewhere.
4. Update README or changelog content relevant to the release.
5. Commit with an intentional message, for example `chore: release 0.2.0`.
6. Push `main` and wait for CI to pass.
7. Confirm the exact PyPI Trusted Publisher configuration.
8. Run the **Create release** workflow without a tag override for the normal
   `v<version>` tag.
9. Verify the build artifact, PyPI publication, and GitHub Release.
10. Test installation in a clean environment:

```bash
python -m venv release-smoke-test
python -m pip install <distribution-name>==<version>
python -c "import <package-name>; print(<package-name>.__version__)"
```

PyPI versions are immutable. Never rebuild different content under an already
published version. Increment `_version.py` and create a new release instead.

## Agent working rules

- Inspect the repository and Git status before editing.
- Preserve user-owned or unrelated worktree changes.
- Use patch-based edits and keep changes inside the repository.
- Do not perform destructive Git or filesystem operations without explicit approval.
- Do not push, publish, create releases, or mutate external services unless explicitly
  authorized.
- Keep implementation, tests, documentation, packaging, and workflows synchronized.
- Validate changes proportionally to risk; packaging and release changes require an
  actual wheel/sdist build and metadata smoke test.
- Commit only files in scope and use a focused Conventional Commit message.

## Definition of done

A new repository is complete only when:

- The `src/` package imports successfully on Python 3.10+.
- Public APIs are typed, documented, and tested.
- Ruff, strict mypy, pytest, coverage, compileall, and `pip check` pass.
- Wheel and sdist build successfully and pass `twine check`.
- Version metadata comes only from `_version.py`.
- CI covers supported Python versions and operating-system boundaries.
- GitHub Release creation defaults to the code version and supports a tag override.
- PyPI Trusted Publishing claims match the configured publisher exactly.
- The README accurately explains installation, usage, security, development, and
  release operations.
- Generated artifacts are ignored and the committed worktree is clean.
