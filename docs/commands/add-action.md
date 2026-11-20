# add-action

Inject a DRF `@action` stub onto an existing `<Model>ViewSet`.

## Examples

```bash
uv run django-octave add-action blog Post publish
uv run django-octave add-action blog Post recent --list --methods get
uv run django-octave add-action blog Post publish \
  --permission IsOwner \
  --url-path publish-now \
  --force
```

## Important options

| Option | Notes |
|--------|--------|
| Default | **Detail** action (`POST …/{pk}/…/`) calling `self.get_object()` |
| `--list` | Collection route instead of detail |
| `--methods` | Comma-separated HTTP methods |
| `--url-path` / `--url-name` | Optional routing overrides |
| `--permission` / `--serializer` / `--tag` | Optional; serializer must already exist |
| `--force` | Replace an existing method of the same name |

## What it changes

Method on the viewset in `apps/<app>/views.py`. The router picks up new actions automatically — no `urls.py` edit.

Spectacular tags default to the **target** viewset’s tag (or `--tag`). Printed route shapes look like `/api/<plural>/{pk}/<action>/` under the shared `api/` mount.
