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
| `NAME` | Project name (prompted if omitted): 1-64 letters, digits, spaces, `.`, `-`, `_`, starting with a letter or digit. The directory is its ASCII slug (`My Shop` → `my_shop`); a name without any ASCII letter or digit cannot produce one. See [Security](../concepts/security.md#project-names) |
| `--database` / `-d` | `sqlite`, `postgres`, or `mariadb` |
| `--docker` / `--no-docker` | Include Docker artifacts |
| `--multitenancy` / `--no-multitenancy` | Row-level tenancy (create-time only) |
| `--frontend` / `--no-frontend` | Vue + Nuxt UI SPA under `frontend/` |
| `--register` / `--no-register` | With frontend: signup page + API (prompted if omitted) |
| `--crud` / `--no-crud` | With frontend: Vue CRUD for all ModelViewSets (prompted if omitted) |
| `--celery` / `--no-celery` | Run Celery setup after create (default: **off**) |
| `--path` | Parent directory (default: `.`) |
| `--force` | Generate into a non-empty directory: generated files are **overwritten**, everything else is **kept** (see below) |

## Existing directories and `--force`

- Target missing or empty: the project is created there.
- Target not empty: refused, unless `--force` is given.
- With `--force`, each generated file is written over the file at the same path. Files that are not part of the generated tree (your own apps, notes, `.git/`) are never touched or deleted. The command prints how many files it overwrote.
- Nothing is written if any path it would write is a symbolic link (or goes through one), or if a directory sits where a file belongs. The error names the path.

Unrelated edits to generated files (for example your own `config/settings/base.py`) **are** overwritten, so commit first.

## What it writes

A full project tree: `config/`, `apps/core`, `apps/users`, settings, pytest/Ruff/`uv` tooling, empty `staticfiles/` for WhiteNoise, optional Docker Compose files. Local settings enable WhiteNoise finders so `runserver` / pytest work without an immediate `collectstatic`.

## Next steps

- [First project](../getting-started/first-project.md)
- [add](add.md) — domain app
- [add-frontend](add-frontend.md) — Vue + Nuxt UI SPA (also via `--frontend`)
- [add-frontend-crud](add-frontend-crud.md) — per-model CRUD (also via `--crud`)
