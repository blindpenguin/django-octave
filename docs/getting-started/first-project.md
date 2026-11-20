# First project

## Create

Interactive:

```bash
uv run django-octave new
```

Flags (scriptable / CI):

```bash
uv run django-octave new myapi \
  --database sqlite \
  --no-docker \
  --no-multitenancy \
  --no-frontend
```

Useful options:

| Flag | Meaning |
|------|---------|
| `--database sqlite\|postgres\|mariadb` | Database backend |
| `--docker` / `--no-docker` | Dockerfile + Compose |
| `--multitenancy` / `--no-multitenancy` | Row-level tenancy (create-time only) |
| `--frontend` / `--no-frontend` | Vue + Nuxt UI SPA under `frontend/` |
| `--register` / `--no-register` | With frontend: signup page + API |
| `--celery` / `--no-celery` | Wire Celery after create (default: off) |
| `--path DIR` | Parent directory for the project |
| `--force` | Allow a non-empty target directory |

Full detail: [`new`](../commands/new.md).

## Run locally

```bash
cd myapi
uv sync
cp .env.example .env   # if present — fill secrets for non-SQLite
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

OpenAPI UI is available via drf-spectacular (typically `/api/schema/swagger-ui/` — check the generated project README).

## Add domain code

```bash
uv run django-octave add blog
uv run django-octave add-model blog Post --fields title:char:max=200,published:bool
uv run django-octave add-viewset blog Post
uv run django-octave add-test blog Post
```

See [project layout](../concepts/layout.md) and the [commands](../commands/add.md) section.

## Optional stacks

- [Docker](../concepts/docker.md)
- [Multitenancy](../concepts/multitenancy.md)
- [Celery](../concepts/celery.md)
- [add-frontend](../commands/add-frontend.md) — Vue + Nuxt UI SPA
