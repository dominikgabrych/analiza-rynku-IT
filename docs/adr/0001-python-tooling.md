# ADR 0001: Python tooling with uv, ruff and pytest

- Status: accepted
- Date: 2026-10-14

## Context

The code has to run the same way on a developer machine, in Docker images and in CI. Style and correctness checks should be fast enough to run on every change.

## Decision

- **Python 3.14.** Python 3.15 was released on 2026-10-09, and libraries with compiled extensions usually need a few weeks to publish wheels for a new version.
- **uv** installs the interpreter pinned in `.python-version`, manages dependencies and writes the lockfile (`uv.lock`, committed). The package is built with `uv_build`.
- **src layout.** The import package `radar` lives in `src/radar/` and tests live in `tests/`, so tests import the installed package rather than files from the working directory. The distribution name `analiza-rynku-it` differs from the import name, so `module-name` is set in `[tool.uv.build-backend]`.
- **ruff** lints and formats: pycodestyle errors (E4, E7, E9), Pyflakes (F), import sorting (I), bugbear (B) and pyupgrade (UP).
- **pytest** is configured in the native `[tool.pytest]` table, with the `importlib` import mode and strict mode recommended for new projects.

## Alternatives considered

- **pip and venv:** no single tool for the interpreter, the virtual environment and a lockfile.
- **Poetry:** comparable dependency management; uv was chosen for speed and for managing the interpreter in the same tool.
- **flake8, isort and Black:** three tools and three configurations for what ruff does alone.

## Consequences

- `uv sync` sets up the whole environment, and the lockfile gives the same versions everywhere.
- Docker images and CI use uv as well, so `uv.lock` is the single source of dependency versions.
- Moving to Python 3.15 means changing `.python-version` and `requires-python` once the dependencies support it.
