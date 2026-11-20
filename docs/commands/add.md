# add

Scaffold a domain app under `apps/` with DRF API stubs.

## Examples

```bash
uv run django-octave add blog
uv run django-octave add blog --path /path/to/project
uv run django-octave add blog --force
```

## Important options

| Option | Notes |
|--------|--------|
| `APP` | `snake_case` module name; not reserved (`core`, `users`, …) |
| `--path` | Project root (default: `.`) |
| `--force` | Replace an existing `apps/<name>/` (wiring stays idempotent) |

## What it writes

- `apps/<app>/` with starter model, serializer, viewset, urls, `services.py`
- Registers the app in `INSTALLED_APPS`
- Mounts `api/<app>/`

## Next steps

- [add-model](add-model.md)
- [add-viewset](add-viewset.md)
