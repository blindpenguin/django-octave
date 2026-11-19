# django-octave

Opinionated CLI that kickstarts production-ready **Django REST API** projects for solo developers.

It scaffolds Django, DRF, OpenAPI (drf-spectacular), JWT auth, env-based settings, a `core` app, pytest/Ruff/`uv` tooling, and optional Docker or row-level multitenancy — so you start on domain logic instead of boilerplate.

## Features

- **`django-octave new`** — interactive prompts and/or flags to create a full project
- **Opinionated stack** — Django, DRF, drf-spectacular, SimpleJWT, django-filter, CORS, django-environ, WhiteNoise, Gunicorn
- **Database choice** — SQLite, PostgreSQL, or MariaDB
- **Optional Docker** — dev and production Compose/Dockerfile with `uv`
- **Optional row-level multitenancy** — first-party, create-time only
- **Layout** — `config/` project package, domain apps under `apps/`, always-on `apps.core` (e.g. timestamped models)
- **`django-octave add`** — scaffold domain apps with DRF API stubs after create

## Install

```bash
uv sync
```

## Usage

Interactive:

```bash
uv run django-octave new
```

Flags (scriptable / CI):

```bash
uv run django-octave new myapi \
  --database sqlite \
  --no-docker \
  --no-multitenancy
```

Other options:

- `--database sqlite|postgres|mariadb` (default when prompted: sqlite)
- `--docker` / `--no-docker`
- `--multitenancy` / `--no-multitenancy`
- `--path DIR` — parent directory for the project
- `--force` — allow generating into a non-empty directory

### Add an app

From inside a generated project (or pass `--path`):

```bash
uv run django-octave add blog
# or
uv run django-octave add blog --path /path/to/project
```

Creates `apps/blog/` with a starter model, serializer, viewset, urls, and `services.py`; registers the app in `INSTALLED_APPS` and mounts `api/blog/`.

- App names: `snake_case`, not reserved (`core`, `users`, …)
- `--force` — replace an existing `apps/<name>/` (wiring stays idempotent)

### Add a model

```bash
uv run django-octave add-model blog Post \
  --field title:char:max=200 \
  --field published:bool:default=false \
  --path /path/to/project
```

Field form: `name:type[:option=value…]`. Types: `char`, `text`, `int`, `bool`, `decimal`, `date`, `datetime`, `email`, `url`, `slug`, `uuid`.  
If no `--field` is given, defaults to `name:char:max=255`. Updates serializer, admin, viewset, and router for the new model.

## Requirements

- Python 3.14+ (generator)
- [uv](https://docs.astral.sh/uv/)

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

## License

[GPL-3.0](LICENSE)
