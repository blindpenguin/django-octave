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
- `--celery` / `--no-celery` — wire Celery + Redis after create (default: off)
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

Field form: `name:type[:option=value…]`.  
Scalar types: `char`, `text`, `int`, `bool`, `decimal`, `date`, `datetime`, `email`, `url`, `slug`, `uuid`.  
Relations: `fk`, `o2o`, `m2m` with required `to=Model` or `to=app_label.Model` (optional `on_delete=cascade|protect|set_null|…` for fk/o2o).

```bash
uv run django-octave add-model blog Post \
  --field title:char \
  --field author:fk:to=Author \
  --field tags:m2m:to=Tag
```

If no `--field` is given, defaults to `name:char:max=255`. Updates serializer, admin, viewset, and router for the new model.

### Add a serializer

```bash
uv run django-octave add-serializer blog Post \
  --fields title,id \
  --read-only id \
  --path /path/to/project
```

Inspects `apps/<app>/models.py` for field names (plus `id` / timestamps when the model uses TimeStamped/TenantAware bases). Relation fields default to primary-key style. Omit `--fields` to include all inspected fields. Use `--no-id` to drop `id`. `--force` replaces an existing `<Model>Serializer`.

Optional read-only nesting (one level; creates a slim `{Related}NestedSerializer` when needed):

```bash
uv run django-octave add-serializer blog Post --nested author --force
```

### Add a viewset

```bash
uv run django-octave add-viewset blog Post \
  --permission AllowAny \
  --filter title,published \
  --search title \
  --ordering title \
  --tag posts \
  --path /path/to/project
```

Creates or refreshes `<Model>ViewSet` with Spectacular tags, filter/search/ordering, and router registration. If the serializer is missing, a default one is created automatically. Permissions: `IsAuthenticated` (default), `AllowAny`, `IsAdminUser`, or a custom class from `apps/<app>/permissions.py` (see add-permission). `--force` replaces an existing viewset.

### Add a permission

```bash
uv run django-octave add-permission blog IsOwner --preset owner --owner-attr owner
uv run django-octave add-permission blog IsStaffOrRead --preset staff_or_read
uv run django-octave add-permission blog IsAuthOrRead --preset auth_or_read
# Multitenancy projects only:
uv run django-octave add-permission blog IsTenantMember --preset tenant_member
```

Writes `apps/<app>/permissions.py`. Presets: `owner` (object owner check; fail closed if attribute missing), `staff_or_read`, `auth_or_read`, `tenant_member` (requires `--multitenancy` project). Wire onto an existing viewset:

```bash
uv run django-octave add-permission blog IsOwner --viewset Post
uv run django-octave add-permission blog IsOwner --viewset PostViewSet --append
```

Or regenerate the viewset with the custom class:

```bash
uv run django-octave add-viewset blog Post --permission IsOwner --force
```

`--force` replaces an existing permission class.

### Add a custom viewset action

```bash
uv run django-octave add-action blog Post publish
uv run django-octave add-action blog Post recent --list --methods get
uv run django-octave add-action blog Post publish \
  --permission IsOwner \
  --url-path publish-now \
  --force
```

Injects an `@action` stub onto an existing `<Model>ViewSet` in `views.py`. Default is a **detail** action (`POST …/{pk}/publish/`) that calls `self.get_object()`. Use `--list` for a collection route. Optional `--methods`, `--url-path`, `--url-name`, `--permission`, `--serializer` (must already exist), and `--tag`. The router picks up new actions automatically — no `urls.py` edit. `--force` replaces an existing method of the same name.

### Add / refine ModelAdmin

```bash
uv run django-octave add-admin blog Post --force
uv run django-octave add-admin blog Post \
  --list-display id,title,published \
  --search title \
  --filter published \
  --ordering -created_at \
  --force
```

Creates or refreshes `<Model>Admin` in `apps/<app>/admin.py` from inspected model fields: capped `list_display` (skips Text/JSON/file/M2M by default), `search_fields`, `list_filter`, `list_select_related` for FKs in the display list, and `date_hierarchy = "created_at"` when the model uses TimeStamped/TenantAware bases. Use `--no-date-hierarchy` to omit that. Overrides replace heuristics after validating field names. `--force` replaces an existing admin class (including the thin stub from `add-model`).

### Add tests (factory + pytest)

```bash
uv run django-octave add-test blog Post
uv run django-octave add-test blog Post --force
```

Writes `tests/factories/<app>_<model>.py` (factory-boy), ensures `tests/factories/user.py` and `api_client` / `auth_client` fixtures in `tests/conftest.py`. If a `<Model>ViewSet` exists, also writes `tests/test_<app>_<model>_api.py` (auth deny, list, retrieve via `reverse("<snake>-list|detail")`). Without a viewset, writes a model smoke test instead. Tenant-aware models on multitenancy projects get `@pytest.mark.skip` on API stubs until tenant setup is wired. `--force` replaces the model’s factory/test files.

```bash
cd /path/to/project && uv run pytest
```

### Add Celery (background tasks)

Opt-in — not required when creating a project:

```bash
uv run django-octave add-celery --path /path/to/project
# or at create time:
uv run django-octave new myapi -d sqlite --no-docker --no-multitenancy --celery
```

Writes `config/celery.py` (autodiscover + empty `beat_schedule`), loads the app from `config/__init__.py`, adds `CELERY_*` settings and Redis URL lines to `.env.example`, and appends `celery[redis]` to `pyproject.toml`. If `docker-compose.yml` exists, injects `redis` / `worker` / `beat` services (marker-refreshable with `--force`).

Run workers (separate processes — do not use `worker --beat` in production):

```bash
uv sync
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

Under Compose, set broker URLs to `redis://redis:6379/0` (the injected services set this via `environment`).

### Add a Celery task

```bash
uv run django-octave add-task blog send_digest --every 3600
uv run django-octave add-task blog send_digest --crontab "0 8 * * *" --force
uv run django-octave add-task blog send_digest --bind
```

Requires `add-celery` first. Creates `apps/<app>/tasks.py` with a `@shared_task` stub. `--every SECONDS` or `--crontab` (5 fields) merges into `config/celery.py` `beat_schedule`. `--force` replaces an existing task or schedule key.

## Requirements

- Python 3.14+ (generator)
- [uv](https://docs.astral.sh/uv/)

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

Spec Workflow approval dashboard (approvals for specs):

```bash
./scripts/spec-dashboard.sh
# → http://localhost:5000
```

### Cutting a GitHub Release

1. Bump `version` in `pyproject.toml` (e.g. with `uv version 0.1.1`).
2. Commit the version bump.
3. Tag and push (tag must match the package version, with a `v` prefix):

```bash
git tag -a v0.1.1 -m "v0.1.1"
git push origin v0.1.1
```

That runs [`.github/workflows/release.yml`](.github/workflows/release.yml): build with `uv`, smoke-test the wheel and sdist, then create a [GitHub Release](https://github.com/blindpenguin/django-octave/releases) with the artifacts attached. Watch the run under Actions.

PyPI publish is not part of this pipeline yet; install from a release asset or from a git checkout for now.

Local smoke check (optional):

```bash
uv build
uv run --isolated --no-project --with dist/*.whl scripts/smoke_dist.py
uv run --isolated --no-project --with dist/*.tar.gz scripts/smoke_dist.py
```

## License

[GPL-3.0](LICENSE)
