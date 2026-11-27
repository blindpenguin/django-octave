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

## The files it edits

`add` edits `config/settings/base.py` and `config/urls.py` by reading their structure, not by searching the text, so files that a formatter or you have changed still work:

- **`INSTALLED_APPS`**: a list or tuple, on one line or several, with or without a trailing comma, with comments, with either quote style, with a type annotation. (When there is no plain assignment, an `INSTALLED_APPS += [...]` list is edited instead.) The new entry follows the style of the existing ones. An app that is already a string entry of a list or tuple anywhere in the file counts as registered; a mention in a comment does not.
- **`urlpatterns`**: a list in the same shapes. `include` is added to your `from django.urls import ...` line (one line or in parentheses), or a new import line is added when there is none. Any existing `include("apps.<app>.urls")` counts as already wired.

Everything else in those files stays exactly as it is.

If a file has a shape `add` cannot edit (for example `INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS`, or `urlpatterns = base_patterns + [...]`), or does not parse, `add` stops and says what to add by hand, for example:

```text
urlpatterns in config/urls.py is not a plain list that django-octave can edit. Import include and
path from django.urls, then add this line to urlpatterns yourself: path("api/", include("apps.blog.urls")),
```

`add` is all-or-nothing: a refused patch leaves no `apps/<app>/` directory and no changed file.

Use `--model` when the first domain type is not the singularized app name (e.g. `add accounts --model Customer` avoids an orphan `Account` starter).

## Next steps

- [add-model](add-model.md)
- [add-viewset](add-viewset.md)
