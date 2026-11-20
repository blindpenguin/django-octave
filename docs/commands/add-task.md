# add-task

Create a Celery `@shared_task` stub and optionally merge a Beat schedule entry.

!!! note
    Requires [`add-celery`](add-celery.md) first (`config/celery.py` must exist).

## Examples

```bash
uv run django-octave add-task blog send_digest --every 3600
uv run django-octave add-task blog send_digest --crontab "0 8 * * *" --force
uv run django-octave add-task blog send_digest --bind
```

## Important options

| Option | Notes |
|--------|--------|
| `APP` / `TASK_NAME` | Existing app; snake_case task name |
| `--bind` | `@shared_task(bind=True)` |
| `--every` | Interval seconds → `beat_schedule` |
| `--crontab` | 5-field cron (mutually exclusive with `--every`) |
| `--force` | Replace existing task / schedule key |

## What it writes

- `apps/<app>/tasks.py` — `@shared_task` stub
- Optional merge into `config/celery.py` `beat_schedule` (key `app.task_name` → path `apps.app.tasks.task_name`)
