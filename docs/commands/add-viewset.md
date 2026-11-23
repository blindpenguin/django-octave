# add-viewset

Create or refresh a `ModelViewSet` with Spectacular tags, filtering, and router registration.

## Examples

```bash
uv run django-octave add-viewset blog Post \
  --permission AllowAny \
  --filter title,published \
  --search title \
  --ordering title \
  --tag posts
```

## Important options

| Option | Notes |
|--------|--------|
| `--permission` | `IsAuthenticated` (default), `AllowAny`, `IsAdminUser`, or a local permission class |
| `--filter` / `--search` / `--ordering` | Comma-separated field lists |
| `--tag` | Spectacular tag (default: snake_case model) |
| `--force` | Replace an existing viewset |

## What it writes

Viewset in `views.py` + router wiring. Missing serializers are created automatically.

## Related

- [add-permission](add-permission.md)
- [add-action](add-action.md)

Generated viewsets use `IsAuthenticated` and no ownership scoping: any authenticated user can read and change every row. See [Who can access what](../concepts/security.md#who-can-access-what).
