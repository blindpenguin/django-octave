# django-octave

Opinionated CLI that kickstarts production-ready **Django REST API** projects for solo developers.

It scaffolds Django, DRF, OpenAPI (drf-spectacular), JWT auth, env-based settings, a `core` app, pytest/Ruff/`uv` tooling, and optional Docker, row-level multitenancy, or Celery — so you start on domain logic instead of boilerplate.

## What you get

- **`django-octave new`** — interactive prompts and/or flags to create a full project
- **Opinionated stack** — Django, DRF, drf-spectacular, SimpleJWT, django-filter, CORS, django-environ, WhiteNoise, Gunicorn
- **Database choice** — SQLite, PostgreSQL, or MariaDB
- **Optional Docker** — dev and production Compose/Dockerfile with `uv`
- **Optional multitenancy** — first-party row-level tenancy, create-time only
- **Optional Celery** — Redis broker, worker + Beat (Compose when Docker is present)
- **Generators** — apps, models, serializers, viewsets, permissions, actions, admin, tests, tasks

## Start here

1. [Install](getting-started/install.md)
2. [Create your first project](getting-started/first-project.md)
3. Browse [commands](commands/new.md) as you need them

## Local docs preview

From a clone of this repository:

```bash
uv sync
uv run mkdocs serve
```

Then open the URL MkDocs prints (usually `http://127.0.0.1:8000`).
