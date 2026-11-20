# Contributing

## Setup

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```

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

Cursor enforces this via `.cursor/rules/commits.mdc`. Preview notes: `python3 scripts/release-notes.py`.

## Layout

- Generator package: `src/django_octave/`
- Tests: `tests/` (mirrors package)
- Templates: `src/django_octave/templates/`
