# add

Scaffold a domain app under `apps/` with DRF API stubs.

## Examples

```bash
uv run django-octave add blog
uv run django-octave add accounts --model Customer
uv run django-octave add blog --path /path/to/project
uv run django-octave add blog --force
```

## Important options

| Option | Notes |
|--------|--------|
| `APP` | `snake_case` module name; not reserved (`core`, `users`, …) |
| `--model` / `-m` | Starter model PascalCase name (default: derived from the app, e.g. `accounts` → `Account`) |
| `--path` | Project root (default: `.`) |
| `--force` | Replace an existing `apps/<name>/` (wiring stays idempotent) |

## What it writes

- `apps/<app>/` with starter model, serializer, viewset, urls, `services.py`
- Registers the app in `INSTALLED_APPS`
- Mounts under shared `api/` so the collection is `/api/<model_plural>/` (e.g. `/api/customers/`)

Use `--model` when the first domain type is not the singularized app name (e.g. `add accounts --model Customer` avoids an orphan `Account` starter).

## Next steps

- [add-model](add-model.md)
- [add-viewset](add-viewset.md)
