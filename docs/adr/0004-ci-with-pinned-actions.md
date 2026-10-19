# ADR 0004: CI on GitHub Actions with actions pinned to commit SHAs

- Status: accepted
- Date: 2026-10-14 (recorded 2026-10-19)

## Context

Every change should pass the same lint and test checks before it reaches `main`. Actions from other repositories run with access to the code and the workflow token, and a tag such as `v7` can be moved to different code after it was reviewed.

## Decision

- **One workflow** (`.github/workflows/ci.yml`) runs on pushes to `main` and on pull requests: `uv sync --locked`, `ruff check`, `ruff format --check` and `pytest`.
- **Least privilege:** the workflow token has `contents: read`, and checkout does not persist credentials.
- **Actions are pinned to full commit SHAs** with the version in a comment, as GitHub's [secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) recommends. uv is pinned to `0.13.1`.
- **[Dependabot](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/auto-update-actions)** opens monthly pull requests that update the pinned actions.

## Alternatives considered

- **Version tags (`@v7`):** easier to read, but a compromised maintainer account can point a tag at malicious code.
- **[Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles):** GitHub's newer mechanism records the commit of every action, including transitive dependencies, and verifies the source repository at run time. GitHub describes it as stronger than SHA pinning. As of 2026-10-19 it is in public preview and needs the `gh actions-lock` extension, so we keep SHA pinning and revisit once it is generally available.

## Consequences

- `uv sync --locked` fails when `uv.lock` is out of date, so CI uses exactly the locked versions.
- Action updates arrive as Dependabot pull requests, and each new SHA needs a review.
- Tests that need a database will require a PostgreSQL service in the workflow.
