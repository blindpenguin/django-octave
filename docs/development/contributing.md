# Contributing

## Setup

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```

End-to-end tests generate real projects and run `uv sync` (network). They are skipped by default:

```bash
OCTAVE_E2E=1 uv run pytest -m e2e              # multitenancy + production-settings suites (~1 min)
OCTAVE_E2E_DOCKER=1 uv run pytest tests/e2e/test_docker_image.py   # builds real images (~1 min, needs a Docker daemon)
```

The Docker suite builds the production image for SQLite, Postgres and MariaDB and removes every image and container it creates. It skips itself when Docker is not available.

## Continuous integration

Pull requests run `ruff check src tests`, `pytest` and `mkdocs build --strict` (workflow `CI`). Pushes to `master` also run both end-to-end suites. A release tag runs the same workflow first, and the release job only starts when it passes.

All third-party actions are pinned to a commit SHA with the version in a trailing comment; Dependabot proposes updates. `tests/test_workflows.py` enforces the pinning, least-privilege permissions and the release gate. `ruff format --check` is not part of CI yet.

A separate workflow, `Audit`, runs `uv audit --locked` against `uv.lock` once a week, when a pull request changes `uv.lock` or `pyproject.toml`, and on demand. It is deliberately not part of `CI` or the release gate, so a new advisory for an unrelated package cannot block a pull request or a hotfix release. Run it locally with `uv audit --locked`.

## Documentation

User docs live under `docs/` and are built with MkDocs Material:

```bash
uv run mkdocs serve
uv run mkdocs build --strict
```

The **published** site (GitHub Pages) updates only when a **public release** is published — not on every `master` push. Keep docs in the same PR/commit as the feature so the next tag ships matching docs. See [Releases](releases.md#docs-site).

!!! tip "Definition of Done"
    When you ship a new user-facing generator or flag, update the matching page under `docs/commands/` (and concepts if needed). Do not re-expand the README into a command catalog.

## Spec Workflow

Non-trivial features go through Spec Workflow (requirements → design → tasks → implement). Approvals:

```bash
./scripts/spec-dashboard.sh
# → http://localhost:5000
```

Artifacts live under `.spec-workflow/` (not end-user docs).

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) so release notes stay useful:

```text
feat(add): support --model for starter class name
fix(serializers): insert nested helpers before parent class
docs(layout): document shared api/ mount paths
chore(release): 0.2.3
```

| type | Use for |
|------|---------|
| `feat` | User-facing capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` / `test` / `chore` / `ci` / `perf` | As named |

Optional `(scope)`: `add`, `add-model`, `celery`, `docs`, …  
Breaking: `feat(api)!: …` or footer `BREAKING CHANGE: …`.

Claude Code follows this via `CLAUDE.md`. Preview notes: `python3 scripts/release-notes.py`.

## Layout

- Generator package: `src/django_octave/`
- Tests: `tests/` (mirrors package)
- Templates: `src/django_octave/templates/`
