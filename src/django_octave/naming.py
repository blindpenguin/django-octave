"""App naming validation and model-name derivation."""

from __future__ import annotations

import keyword
import re

from django_octave.rendering.context import normalize_slug

RESERVED_APP_NAMES: frozenset[str] = frozenset(
    {
        "core",
        "users",
        "config",
        "django",
        "test",
        "tests",
        "admin",
        "auth",
        "contenttypes",
        "sessions",
        "static",
        "media",
    }
)

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class InvalidAppNameError(ValueError):
    """Raised when an app name is invalid or reserved."""


def validate_app_name(raw: str) -> str:
    """Normalize and validate an app module name.

    Returns the normalized ``snake_case`` name.
    """
    # Normalize like project slugs, but do not auto-prefix digit-leading names.
    stripped = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if stripped[:1].isdigit():
        msg = f"Invalid app name {raw!r}: must start with a letter"
        raise InvalidAppNameError(msg)
    try:
        name = normalize_slug(raw)
    except ValueError as exc:
        raise InvalidAppNameError(str(exc)) from exc
    if name.startswith("project_") and stripped[:1].isdigit():
        msg = f"Invalid app name {raw!r}: must start with a letter"
        raise InvalidAppNameError(msg)
    if not _IDENTIFIER_RE.match(name):
        msg = (
            f"Invalid app name {raw!r}: must be a snake_case Python identifier "
            "starting with a letter"
        )
        raise InvalidAppNameError(msg)
    if keyword.iskeyword(name):
        msg = f"App name {name!r} is a Python keyword"
        raise InvalidAppNameError(msg)
    if name in RESERVED_APP_NAMES:
        msg = f"App name {name!r} is reserved"
        raise InvalidAppNameError(msg)
    return name


def singularize(word: str) -> str:
    """Best-effort English singularization for model names."""
    if len(word) <= 3:
        return word
    lower = word.lower()
    if lower.endswith(("ss", "us", "is")):
        return word
    if lower.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if lower.endswith("ses"):
        return word[:-2]
    if lower.endswith("s"):
        return word[:-1]
    return word


def model_name_from_app(app_name: str) -> str:
    """Derive a PascalCase model name from an app module name."""
    base = app_name.split("_")[-1]
    singular = singularize(base)
    return "".join(part.capitalize() for part in singular.split("_") if part) or "Item"
