# Celery

Background jobs are **opt-in**. Celery is not required for a new project.

Wire it with [`add-celery`](../commands/add-celery.md) (or `new --celery`), then add stubs with [`add-task`](../commands/add-task.md).

## Runners

Use **separate** worker and Beat processes:

```bash
uv sync
uv run celery -A config worker -l INFO
uv run celery -A config beat -l INFO
```

!!! warning
    Do **not** use `celery worker --beat` in production. Run Beat as its own process (Compose `beat` service or a second local terminal).

## Schedules

v1 uses **code** `app.conf.beat_schedule` in `config/celery.py` (no django-celery-beat). Prefer `--every` or `--crontab` on `add-task` to merge entries.

## Compose

See [Docker](docker.md) for Redis/worker/beat injection and `redis://redis:6379/0` broker URLs.
