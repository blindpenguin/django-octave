---
paths:
  - "**/tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---

# Testing (pytest)

- Place tests under `tests/` mirroring the package; run with `uv run pytest`
- One behavior per test; name `test_<unit>_<condition>_<expected>`
- Structure: Arrange → Act → Assert (visually separate)
- Prefer `@pytest.mark.parametrize` over copy-pasted cases
- Fixtures: default **function** scope; session/module only for expensive read-only setup + per-test cleanup
- One resource per fixture; tear down after `yield`
- Prefer factory fixtures (`make_x(**overrides)`) over many near-duplicate fixtures
- Avoid `autouse=True` except for global safety (e.g. block network)
- Shared fixtures in nearest `conftest.py`
- Assert exceptions with `pytest.raises`; don’t swallow unexpected errors
- For Django: use `pytest-django`; prefer service/selector unit tests over full stack when logic lives outside views
