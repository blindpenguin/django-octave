# add-frontend-crud

Generate **list / detail / create / edit** Vue pages (plus delete-with-confirm on detail) for a DRF `ModelViewSet`, wired into the SPA router and nav.

Requires an existing `frontend/` from [add-frontend](add-frontend.md) and a discoverable viewset (see [add-viewset](add-viewset.md)).

## Examples

```bash
uv run django-octave add-frontend-crud recipes Recipe
uv run django-octave add-frontend-crud recipes Recipe --force
uv run django-octave add-frontend-crud recipes Recipe --path /path/to/project
```

Bulk (all ModelViewSets) via the shell:

```bash
uv run django-octave add-frontend --no-register --crud
uv run django-octave new myapi -d sqlite --no-docker --no-multitenancy \
  --frontend --no-register --crud
```

## Prerequisites

- `frontend/` present (`django-octave add-frontend`)
- `ModelViewSet` for `APP.MODEL` with `router.register` in `apps/<app>/urls.py`
- Model fields inspectable via libcst (no Django runtime at generate time)

## Flags

| Option | Notes |
|--------|--------|
| `APP` / `MODEL` | Required (prompted interactively) |
| `--force` | Overwrite existing `frontend/src/pages/<plural>/` |
| `--fk-label FIELD=ATTR` | Optional; repeatable. Override which related field labels a FK select (e.g. `--fk-label author=email`) |
| `--path` | Project root (default: `.`) |

## What it writes

- `frontend/src/pages/<plural>/` — `ListView`, `DetailView`, `CreateView`, `EditView`
- `frontend/src/composables/useCrudResource.ts` — shared list/detail/mutate helpers (once)
- Nested router **child** routes under `AppLayout` + sidebar `crudNavItems` entries (JS marker regions)

### Foreign keys

FK fields render as a **select** loaded from the related model’s list API (`/api/<related-plural>/`) when that resource has a registered ModelViewSet.

**Dropdown labels** (in order):

1. API field `label` when the list serializer exposes it (recommended: `SerializerMethodField` → `str(instance)` so Django `__str__` wins at runtime)
2. Else a generate-time pick: simple `__str__` like `return self.name` / `return str(self.email)`, else heuristic (`name` → `title` → `email` → `slug` → first string field)
3. Else `--fk-label FIELD=ATTR` override
4. Else `id`

`users.User` FKs use **`GET /api/users/`** (`id`, `email`, `label=str(user)`). Other FKs without a list route fall back to a **numeric PK** input. Many-to-many editors are **not** generated in v1.

## Auth & API

Pages are behind the SPA auth guard. Mutations use the existing JWT `apiFetch` / `apiJson` client against `/api/<plural>/` (list, create, retrieve, PATCH, DELETE).

## Related

- [add-frontend](add-frontend.md)
- [add-viewset](add-viewset.md)
- [new](new.md)
