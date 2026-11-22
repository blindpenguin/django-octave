---
paths:
  - "**/*.py"
---

# Python

Leave formatting/import sorting to Ruff. Focus on behavior and types.

## Types

- Annotate public functions: parameters and return types
- Prefer precise types over `Any`; use `object` when any value is truly accepted
- Inputs: abstract (`Iterable`, `Sequence`, `Mapping`); outputs: concrete (`list`, `dict`)
- Use `X | None`, `list[str]`, `dict[str, T]` (not `Optional`/`List`/`Dict` from `typing`)
- Prefer `TypedDict` / `dataclasses` / pydantic models over `dict[str, Any]` for structured data
- Avoid bare `# type: ignore`; if needed, use `# type: ignore[code]` sparingly

## Style

```python
# ❌ BAD
def load(items: list) -> dict:
    try:
        return do_work(items)
    except Exception:
        pass

# ✅ GOOD
def load(items: Sequence[str]) -> dict[str, int]:
    try:
        return do_work(items)
    except ValueError as exc:
        raise LoadError("failed to load items") from exc
```

- Prefer `pathlib.Path` over `os.path` for new code
- Raise specific exceptions; chain with `from` when wrapping
- No mutable default args (`def f(x=[])`); use `None` + assign inside
- Keep modules cohesive; extract helpers when a file’s responsibility blurs
