# add-permission

Create a DRF `BasePermission` subclass from a preset; optionally wire it onto a viewset.

## Examples

```bash
uv run django-octave add-permission blog IsOwner --preset owner --owner-attr owner
uv run django-octave add-permission blog IsStaffOrRead --preset staff_or_read
uv run django-octave add-permission blog IsAuthOrRead --preset auth_or_read
uv run django-octave add-permission blog IsTenantMember --preset tenant_member
```

Wire onto an existing viewset:

```bash
uv run django-octave add-permission blog IsOwner --viewset Post
uv run django-octave add-permission blog IsOwner --viewset PostViewSet --append
```

Or regenerate the viewset:

```bash
uv run django-octave add-viewset blog Post --permission IsOwner --force
```

## Presets

| Preset | Notes |
|--------|--------|
| `owner` | Object owner check; fail closed if attribute missing |
| `staff_or_read` | Staff write / read for others |
| `auth_or_read` | Authenticated write / read for others |
| `tenant_member` | Multitenancy projects only |

## Important options

| Option | Notes |
|--------|--------|
| `--preset` | Default: `owner` |
| `--owner-attr` | Attribute for owner preset |
| `--viewset` | Model or `ModelViewSet` name to wire |
| `--append` | Append instead of replacing `permission_classes` |
| `--force` | Replace an existing permission class |

## What it writes

`apps/<app>/permissions.py` (+ optional `views.py` wiring).
