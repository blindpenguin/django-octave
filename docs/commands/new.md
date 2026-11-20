# new

Create a production-ready Django REST API project.

## Examples

```bash
uv run django-octave new
```

```bash
uv run django-octave new myapi \
  --database sqlite \
  --no-docker \
  --no-multitenancy
```

```bash
uv run django-octave new myapi \
  -d postgres \
  --docker \
  --no-multitenancy \
  --frontend \
  --no-register \
  --no-crud \
  --celery \
  --path ~/Projects
```

## Important options

| Option | Default / notes |
|--------|-----------------|
| `NAME` | Project directory name (prompted if omitted) |
| `--database` / `-d` | `sqlite`, `postgres`, or `mariadb` |
| `--docker` / `--no-docker` | Include Docker artifacts |
| `--multitenancy` / `--no-multitenancy` | Row-level tenancy (create-time only) |
| `--frontend` / `--no-frontend` | Vue + Nuxt UI SPA under `frontend/` |
| `--register` / `--no-register` | With frontend: signup page + API (prompted if omitted) |
| `--crud` / `--no-crud` | With frontend: Vue CRUD for all ModelViewSets (prompted if omitted) |
| `--celery` / `--no-celery` | Run Celery setup after create (default: **off**) |
| `--path` | Parent directory (default: `.`) |
| `--force` | Allow non-empty target directory |

## What it writes

A full project tree: `config/`, `apps/core`, `apps/users`, settings, pytest/Ruff/`uv` tooling, empty `staticfiles/` for WhiteNoise, optional Docker Compose files. Local settings enable WhiteNoise finders so `runserver` / pytest work without an immediate `collectstatic`.

## Next steps

- [First project](../getting-started/first-project.md)
- [add](add.md) — domain app
- [add-frontend](add-frontend.md) — Vue + Nuxt UI SPA (also via `--frontend`)
- [add-frontend-crud](add-frontend-crud.md) — per-model CRUD (also via `--crud`)
