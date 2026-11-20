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
| `--celery` / `--no-celery` | Run Celery setup after create (default: **off**) |
| `--path` | Parent directory (default: `.`) |
| `--force` | Allow non-empty target directory |

## What it writes

A full project tree: `config/`, `apps/core`, `apps/users`, settings, pytest/Ruff/`uv` tooling, optional Docker Compose files.

## Next steps

- [First project](../getting-started/first-project.md)
- [add](add.md) — domain app
