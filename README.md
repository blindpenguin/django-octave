# django-octave

Opinionated CLI that kickstarts production-ready **Django REST API** projects for solo developers.

It scaffolds Django, DRF, OpenAPI (drf-spectacular), JWT auth, env-based settings, a `core` app, pytest/Ruff/`uv` tooling, and optional Docker, multitenancy, Celery, or a Vue + Nuxt UI frontend — so you start on domain logic instead of boilerplate.

## Features

- **`django-octave new`** — interactive prompts and/or flags to create a full project
- **Opinionated stack** — Django, DRF, drf-spectacular, SimpleJWT, django-filter, CORS, django-environ, WhiteNoise, Gunicorn
- **Database choice** — SQLite, PostgreSQL, or MariaDB
- **Optional Docker, multitenancy, Celery, Vue frontend** — opt-in at create time or via later generators
- **Generators** — apps, models, serializers, viewsets, permissions, actions, admin, tests, tasks, frontend
- **Layout** — `config/` project package, domain apps under `apps/`, always-on `apps.core`

## Install

```bash
uv sync
uv run django-octave --help
```

## Quick start

```bash
uv run django-octave new myapi \
  --database sqlite \
  --no-docker \
  --no-multitenancy \
  --no-frontend
```

```bash
cd myapi
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

## Documentation

Full guides and command reference:

- **Online:** [https://blindpenguin.github.io/django-octave/](https://blindpenguin.github.io/django-octave/)
- **In this repo:** [`docs/`](docs/index.md) — preview with `uv run mkdocs serve`

## Requirements

- Python 3.14+ (generator)
- [uv](https://docs.astral.sh/uv/)

## License

[GPL-3.0](LICENSE)
