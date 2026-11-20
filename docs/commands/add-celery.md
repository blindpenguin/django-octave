# add-celery

Opt-in Celery + Redis wiring for an existing octave project.

## Examples

```bash
uv run django-octave add-celery
uv run django-octave add-celery --path /path/to/project
uv run django-octave add-celery --force
```

At create time:

```bash
uv run django-octave new myapi -d sqlite --no-docker --no-multitenancy --celery
```

## What it writes

- `config/celery.py` — app + empty `beat_schedule`
- Loads the app from `config/__init__.py`
- `CELERY_*` settings + Redis URL lines in `.env.example`
- `celery[redis]` in `pyproject.toml`
- If `docker-compose.yml` exists: `redis` / `worker` / `beat` services (marker-refreshable with `--force`)

## Runners

```bash
uv sync
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

!!! warning
    Do not use `worker --beat` in production — run Beat separately.

See [Celery concepts](../concepts/celery.md).

## Next

- [add-task](add-task.md)
