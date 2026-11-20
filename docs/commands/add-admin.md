# add-admin

Create or refine a `ModelAdmin` from inspected model fields.

## Examples

```bash
uv run django-octave add-admin blog Post --force
uv run django-octave add-admin blog Post \
  --list-display id,title,published \
  --search title \
  --filter published \
  --ordering -created_at \
  --force
```

## Important options

| Option | Notes |
|--------|--------|
| `--list-display` / `--search` / `--filter` / `--ordering` | Overrides (validated against model fields) |
| `--no-date-hierarchy` | Skip `date_hierarchy = "created_at"` heuristic |
| `--force` | Replace existing admin (including thin stub from `add-model`) |

## What it writes

Heuristics for `list_display` (skips Text/JSON/file/M2M by default), `search_fields`, `list_filter`, `list_select_related` for FKs in the display list, and date hierarchy when TimeStamped/TenantAware bases are present — into `apps/<app>/admin.py`.
