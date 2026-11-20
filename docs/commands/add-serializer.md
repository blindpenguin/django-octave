# add-serializer

Create or refresh a `ModelSerializer` with field control.

## Examples

```bash
uv run django-octave add-serializer blog Post \
  --fields title,id \
  --read-only id
```

```bash
uv run django-octave add-serializer blog Post --nested author --force
```

## Important options

| Option | Notes |
|--------|--------|
| `--fields` | Comma-separated `Meta.fields` (default: inspected) |
| `--read-only` | Comma-separated `read_only_fields` |
| `--no-id` | Omit `id` from fields |
| `--nested` | Read-only nesting (one level); may create `{Related}NestedSerializer` |
| `--force` | Replace an existing `<Model>Serializer` |

## What it writes

`apps/<app>/serializers.py` — inspects the model for field names (plus `id` / timestamps when using TimeStamped/TenantAware bases). Relations default to primary-key style unless `--nested`.
