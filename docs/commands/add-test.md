# add-test

Generate factory-boy factories and pytest stubs for a model.

## Examples

```bash
uv run django-octave add-test blog Post
uv run django-octave add-test blog Post --force
```

```bash
cd /path/to/project && uv run pytest
```

## Behavior

- Writes `tests/factories/<app>_<model>.py` (including cross-app FK `SubFactory` paths)
- Ensures `tests/factories/user.py` (`factory.django.Password`, no post-generation deprecation) and `api_client` / `auth_client` / `user` fixtures in `tests/conftest.py`
- If a `<Model>ViewSet` exists: `tests/test_<app>_<model>_api.py` using `reverse("<model_snake>-list|detail")`
  - Auth-required viewsets: anonymous list expects 401/403
  - `AllowAny` viewsets: anonymous list expects 200
  - Owner-style User FKs (`author` / `assignee` / …): authenticated smoke tests pass `field=user`
- Without a viewset: model smoke test instead
- Tenant-aware models on multitenancy projects: API stubs may be `@pytest.mark.skip` until tenant setup is wired

## Important options

| Option | Notes |
|--------|--------|
| `--force` | Replace the model’s factory/test files |
| `--path` | Project root |
