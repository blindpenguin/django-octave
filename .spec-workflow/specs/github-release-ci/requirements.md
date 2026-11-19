# Requirements Document

## Introduction

**github-release-ci** adds a GitHub Actions release pipeline so tagged versions of `django-octave` are built with `uv`, smoke-tested as installable distributions, and published as a **GitHub Release** with wheel + sdist artifacts attached.

**Out of scope for this spec:** publishing to PyPI/TestPyPI (Trusted Publishing can be a follow-up); changelog automation beyond a short release body; signing beyond what GitHub provides by default; multi-platform wheels (pure Python package).

## Alignment with Product Vision

Supports distributing django-octave as an installable GPL-3.0 Python package for solo developers, with a repeatable release path that matches the uv-based tooling already used in the repo.

## Requirements

### Requirement 1 — Tag-triggered release workflow

**User Story:** As a maintainer, I want pushing a version tag to build and attach package artifacts to a GitHub Release, so that users can download installable distributions from the repo.

#### Acceptance Criteria

1. WHEN a version tag matching `vX.Y.Z` (and optional pre-release forms such as `vX.Y.ZrcN` / `vX.Y.ZaN` / `vX.Y.ZbN`) is pushed THEN GitHub Actions SHALL run a release workflow under `.github/workflows/`.
2. WHEN the workflow runs THEN it SHALL build sdist and wheel with `uv build`.
3. WHEN the build succeeds THEN the workflow SHALL create or update a GitHub Release for that tag and attach the `dist/*` artifacts (wheel + sdist).
4. The workflow SHALL use least-privilege permissions (contents write only where needed for creating the release; no long-lived PyPI tokens).

### Requirement 2 — Distribution smoke checks

**User Story:** As a maintainer, I want the built wheel and sdist smoke-tested before the release is published, so that missing package data (especially templates) is caught early.

#### Acceptance Criteria

1. WHEN artifacts are built THEN the workflow SHALL install/run a smoke check against the wheel and against the sdist (e.g. `uv run --isolated --no-project --with dist/*.whl …`).
2. The smoke check SHALL verify that the `django-octave` console script is importable/runnable (`--help` succeeds) and that packaged templates are present on the import path.
3. IF the smoke check fails THEN the workflow SHALL fail and SHALL NOT publish a GitHub Release with those artifacts.

### Requirement 3 — Version consistency

**User Story:** As a maintainer, I want the Git tag to match the package version, so that releases stay coherent.

#### Acceptance Criteria

1. WHEN the release workflow runs on tag `vX.Y.Z…` THEN it SHALL verify that `pyproject.toml` `project.version` equals the tag without the leading `v` (or document and implement an equivalent single source of truth).
2. IF the tag and package version disagree THEN the workflow SHALL fail before publishing.

### Requirement 4 — Docs for cutting a release

**User Story:** As a maintainer, I want short README (or CONTRIBUTING) instructions for releasing, so that tagging is not tribal knowledge.

#### Acceptance Criteria

1. Docs SHALL describe: bump version in `pyproject.toml`, tag `vX.Y.Z`, push tags, and where to find the GitHub Release / Actions run.
2. Docs SHALL note that PyPI publish is out of scope of this pipeline (or link as future work) so expectations are clear.

## Non-Functional Requirements

### Code Architecture and Modularity
- Workflow YAML kept focused; smoke test as a small script under `tests/` or `scripts/`.
- Prefer official `astral-sh/setup-uv` and pinned/sha-locked Actions where practical.

### Security
- No PyPI API tokens in repo secrets for this spec.
- Prefer `softprops/action-gh-release` or `gh release` with `GITHUB_TOKEN` only.
- Separate build vs publish jobs if it reduces privilege sharing without adding complexity that fights GitHub Release attachment.

### Reliability
- Fail closed on version mismatch or smoke failure.
- Pure-Python wheel (`py3-none-any`) is sufficient.

### Usability
- Release body may be minimal (tag name + artifact list); no requirement for full changelog generation.
