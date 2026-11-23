"""Allow-lists for names that are copied into generated files.

A project name ends up in Python, TOML, JSON, HTML, Vue templates and Markdown, so
the rule is an allow-list: anything outside it is refused, instead of trying to
escape for every format. Kept free of other ``django_octave`` imports so every
layer (CLI, rendering, frontend detection) can use it without import cycles.
"""

from __future__ import annotations

import re

PROJECT_NAME_RE = re.compile(r"^[^\W_][\w .\-]{0,63}$")
"""1-64 chars: Unicode letters/digits, space, ``.``, ``-``, ``_``; starts with a letter/digit."""

PROJECT_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
"""Package-name style identifier (used in ``package.json`` and similar)."""

RULE = "use 1-64 letters, digits, spaces, '.', '-' or '_', starting with a letter or digit"


class InvalidProjectNameError(ValueError):
    """Raised when a project name or slug is not on the allow-list."""


def is_safe_project_name(raw: str) -> bool:
    return PROJECT_NAME_RE.fullmatch(raw) is not None


def is_safe_slug(raw: str) -> bool:
    return PROJECT_SLUG_RE.fullmatch(raw) is not None


def validate_project_name(raw: str) -> str:
    """Return the stripped project name, or raise :class:`InvalidProjectNameError`."""
    name = raw.strip()
    if not is_safe_project_name(name):
        msg = f"Invalid project name {raw!r}: {RULE}."
        raise InvalidProjectNameError(msg)
    return name
