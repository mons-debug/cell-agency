# Code Review — March 30, 2026

## Scope

I reviewed the repository using:

- Static compile check: `python -m compileall -q .`
- Linting: `ruff check .`
- Manual inspection of core runtime paths (`run_crew.py`, `core/workflow_engine.py`, `tools/file_tools.py`, MCP server tools).

## High-Priority Issues

### 1) Hard-coded runtime root (`~/agency`) breaks portability

Multiple core modules derive paths from `Path.home() / "agency"` instead of project-relative or configurable paths.

Examples:

- `run_crew.py` defines `AGENCY_DIR = Path.home() / "agency"` and builds `CREWS_DIR` from it.
- `tools/file_tools.py` allows only roots under `~/agency/{clients,skills,memory}`.

Why this matters:

- Running this code outside a machine with exactly that folder layout can cause false "file not found" or permission errors.
- CI, containers, and other developers' environments are likely to break.

Recommendation:

- Centralize root path resolution (env var like `AGENCY_DIR`, fallback to repo root).
- Reuse that resolver everywhere instead of repeating `Path.home() / "agency"`.

### 2) Exception swallowing in workflow tool dispatch hides root causes

In `core/workflow_engine.py`, `_call_tool` catches broad exceptions and silently ignores them before falling back to MCP execution.

Why this matters:

- Real errors from tool registry calls are suppressed.
- Debugging becomes significantly harder because the original traceback is lost.
- Fallback may mask behavior differences and produce misleading outputs.

Recommendation:

- Log exception details (at least tool name + error message + traceback snippet).
- Only fallback for known expected exceptions.

### 3) Dynamic package install tool can be abused

`mcp-servers/agency_server.py` exposes `agency_install_package(package_name)` which runs package installs directly from tool input.

Why this matters:

- It increases supply-chain and operational risk.
- If exposed in unintended contexts, this becomes arbitrary dependency mutation at runtime.

Recommendation:

- Add an allowlist for installable packages.
- Require explicit approval flow for install operations.
- Log every install attempt with actor/context.

## Medium-Priority Issues

### 4) Lint debt is high and obscures meaningful problems

`ruff check .` reports **65 issues** across the repo, including:

- Unused imports/variables (`F401`, `F841`)
- Import ordering and module-top violations (`E402`)
- Ambiguous variable names (`E741`)
- Multiple imports on one line (`E401`)
- Redundant f-strings (`F541`)

Why this matters:

- Signal-to-noise ratio is low in code reviews.
- Important warnings can be missed.
- CI quality gates are harder to enforce.

Recommendation:

- Apply auto-fixes for safe rules first (`ruff check --fix .`).
- Then clean remaining violations module-by-module.
- Add linting to CI to prevent regression.

## Low-Priority Notes

- `python -m compileall -q .` passes, so files are syntactically valid.
- Main issues are maintainability, portability, and runtime observability rather than syntax errors.

## Suggested Action Plan

1. Introduce a shared settings module for runtime paths and migrate high-traffic modules first.
2. Replace silent exception handling in workflow dispatch with structured logging.
3. Lock down `agency_install_package` behind allowlist + approval.
4. Run staged lint cleanup and enforce in CI.

