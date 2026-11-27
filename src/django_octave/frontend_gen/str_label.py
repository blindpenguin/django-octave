"""Parse model ``__str__`` for FK / list label fields (static, no Django runtime)."""

from __future__ import annotations

import re

_CLASS_RE = re.compile(r"class\s+(?P<name>\w+)\s*\([^)]*\):")
_SIMPLE_RETURN_RE = re.compile(
    r"def\s+__str__\s*\(\s*self\s*\)\s*(?:->\s*[^:\n]+)?\s*:\s*"
    r'(?:(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')\s*)?'
    r"return\s+(?:str\(\s*self\.(?P<a>\w+)\s*\)|self\.(?P<b>\w+))\s*"
    r"(?:#.*)?$",
    re.MULTILINE,
)
_ANY_STR_RE = re.compile(r"def\s+__str__\s*\(\s*self\s*\)")


def _class_body(source: str, model_name: str) -> str | None:
    matches = list(_CLASS_RE.finditer(source))
    for i, m in enumerate(matches):
        if m.group("name") != model_name:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        return source[start:end]
    return None


def parse_simple_str_attr(source: str, model_name: str) -> str | None:
    """If ``__str__`` is ``return self.X`` / ``return str(self.X)``, return ``X``."""
    body = _class_body(source, model_name)
    if body is None:
        return None
    m = _SIMPLE_RETURN_RE.search(body)
    if not m:
        return None
    return m.group("a") or m.group("b")


def str_method_is_complex(source: str, model_name: str) -> bool:
    """True when a ``__str__`` exists but is not a simple single-attribute return."""
    body = _class_body(source, model_name)
    if body is None:
        return False
    if not _ANY_STR_RE.search(body):
        return False
    return parse_simple_str_attr(source, model_name) is None


def parse_fk_label_overrides(raw: list[str] | None) -> dict[str, str]:
    """Parse ``field=attr`` pairs from CLI ``--fk-label`` values."""
    if not raw:
        return {}
    out: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise ValueError(
                f"Invalid --fk-label {item!r}; expected FIELD=ATTR (e.g. author=email)"
            )
        field, _, attr = item.partition("=")
        field, attr = field.strip(), attr.strip()
        if not field or not attr:
            raise ValueError(
                f"Invalid --fk-label {item!r}; expected FIELD=ATTR (e.g. author=email)"
            )
        out[field] = attr
    return out
