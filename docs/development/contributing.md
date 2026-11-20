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

!!! tip "Definition of Done"
    When you ship a new user-facing generator or flag, update the matching page under `docs/commands/` (and concepts if needed). Do not re-expand the README into a command catalog.

## Spec Workflow

Non-trivial features go through Spec Workflow (requirements → design → tasks → implement). Approvals:

```bash
./scripts/spec-dashboard.sh
# → http://localhost:5000
```

Artifacts live under `.spec-workflow/` (not end-user docs).

## Layout

- Generator package: `src/django_octave/`
- Tests: `tests/` (mirrors package)
- Templates: `src/django_octave/templates/`
