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

- Writes `tests/factories/<app>_<model>.py`
- Ensures `tests/factories/user.py` and `api_client` / `auth_client` fixtures in `tests/conftest.py`
- If a `<Model>ViewSet` exists: `tests/test_<app>_<model>_api.py` (auth deny, list, retrieve)
- Without a viewset: model smoke test instead
- Tenant-aware models on multitenancy projects: API stubs may be `@pytest.mark.skip` until tenant setup is wired

## Important options

| Option | Notes |
|--------|--------|
| `--force` | Replace the model’s factory/test files |
| `--path` | Project root |
