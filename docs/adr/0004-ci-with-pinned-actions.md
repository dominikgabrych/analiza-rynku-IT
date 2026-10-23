# ADR 0004: CI on GitHub Actions with actions pinned to commit SHAs

- Status: accepted
- Date: 2026-10-14 (recorded 2026-10-19)

## Context

Every change should pass lint and tests before it reaches `main`. Third-party actions run with access to the code, and a tag such as `v7` can be moved to different code after it was reviewed.

## Decision

- **One workflow** runs lint, formatting checks and tests on pull requests and on `main`, with a read-only token.
- **Actions are pinned to full commit SHAs**, as GitHub's [secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) recommends, and Dependabot proposes updates monthly.

## Alternatives considered

- **Version tags (`@v7`):** easier to read, but a compromised maintainer account can point a tag at malicious code.
- **[Workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles):** stronger than SHA pinning, but in public preview as of 2026-10-19; to revisit once generally available.

## Consequences

- CI installs exactly the versions in `uv.lock`.
- Each action update arrives as a pull request with a new SHA to review.
