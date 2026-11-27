"""Allow-lists for names that are copied into generated files.

A project name ends up in Python, TOML, JSON, HTML, Vue templates and Markdown, so
the rule is an allow-list: anything outside it is refused, instead of trying to
escape for every format. Imports only ``django_octave.errors`` (which has no imports
of its own), so every layer (CLI, rendering, frontend detection) can use it without
import cycles.
"""

from __future__ import annotations

import keyword
import re

from django_octave.errors import OctaveError

PROJECT_NAME_RE = re.compile(r"^[^\W_][\w .\-]{0,63}$")
"""1-64 chars: Unicode letters/digits, space, ``.``, ``-``, ``_``; starts with a letter/digit."""

PROJECT_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
"""Package-name style identifier (used in ``package.json`` and similar)."""

RULE = (
    "use 1-64 letters, digits, spaces, '.', '-' or '_', starting with a letter or digit"
)


class InvalidProjectNameError(OctaveError, ValueError):
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


class InvalidOptionError(OctaveError, ValueError):
    """Raised when a command option value is not on its allow-list."""


TAG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}")
OWNER_ATTR_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
URL_PATH_RE = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*")
URL_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")

_TAG_RULE = (
    "use 1-64 letters, digits, spaces, '.', '-' or '_', starting with a letter or digit"
)
_OWNER_ATTR_RULE = "use a Python identifier of up to 64 ASCII letters, digits or '_' that is not a keyword"
_URL_PATH_RULE = (
    "use up to 64 letters, digits, '-' or '_', optionally separated by single '/'"
)
_URL_NAME_RULE = "use 1-64 letters, digits, '-' or '_', starting with a letter or digit"


def _check(
    option: str, raw: str, pattern: re.Pattern[str], rule: str, *, max_len: int = 64
) -> str:
    value = raw.strip()
    if len(value) > max_len or pattern.fullmatch(value) is None:
        msg = f"Invalid {option} {raw!r}: {rule}."
        raise InvalidOptionError(msg)
    return value


def validate_tag(raw: str, *, option: str = "--tag") -> str:
    """Spectacular tag copied into ``extend_schema(tags=[...])``."""
    return _check(option, raw, TAG_RE, _TAG_RULE)


def is_safe_tag(raw: str) -> bool:
    return len(raw) <= 64 and TAG_RE.fullmatch(raw) is not None


def validate_owner_attr(raw: str) -> str:
    """Attribute name copied into ``getattr(obj, "<attr>", None)``."""
    value = _check("--owner-attr", raw, OWNER_ATTR_RE, _OWNER_ATTR_RULE)
    if keyword.iskeyword(value):
        msg = f"Invalid --owner-attr {raw!r}: {_OWNER_ATTR_RULE}."
        raise InvalidOptionError(msg)
    return value


def validate_url_path(raw: str) -> str:
    """``@action(url_path=...)``: a literal router path segment."""
    return _check("--url-path", raw, URL_PATH_RE, _URL_PATH_RULE)


def validate_url_name(raw: str) -> str:
    """``@action(url_name=...)``: a URL name fragment."""
    return _check("--url-name", raw, URL_NAME_RE, _URL_NAME_RULE)
