"""Parse CLI field declarations ``name:type[:options]``."""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_TYPES: frozenset[str] = frozenset(
    {
        "char",
        "text",
        "int",
        "bool",
        "decimal",
        "date",
        "datetime",
        "email",
        "url",
        "slug",
        "uuid",
        "fk",
        "o2o",
        "m2m",
    }
)

RELATION_TYPES: frozenset[str] = frozenset({"fk", "o2o", "m2m"})

ON_DELETE_CHOICES: frozenset[str] = frozenset(
    {"cascade", "protect", "set_null", "set_default", "do_nothing"}
)

RESERVED_FIELD_NAMES: frozenset[str] = frozenset(
    {"id", "pk", "objects", "all_objects", "DoesNotExist", "MultipleObjectsReturned"}
)

_FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_RELATED_TO_RE = re.compile(r"^([A-Z][A-Za-z0-9_]*)(\.[A-Z][A-Za-z0-9_]*)?$")
# app_label.Model — app_label is snake_case
_RELATED_TO_APP_RE = re.compile(
    r"^([a-z][a-z0-9_]*)\.([A-Z][A-Za-z0-9_]*)$"
)
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


class FieldParseError(ValueError):
    """Raised when a field declaration cannot be parsed."""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    type_key: str
    null: bool = False
    blank: bool = False
    unique: bool = False
    default: str | None = None
    max_length: int | None = None
    max_digits: int | None = None
    decimal_places: int | None = None
    related_to: str | None = None
    """Target model: ``Author`` or ``blog.Author``."""

    on_delete: str | None = None
    """Normalized on_delete token for fk/o2o (e.g. ``cascade``)."""


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    msg = f"Invalid boolean value {raw!r}"
    raise FieldParseError(msg)


def _validate_related_to(raw: str) -> str:
    value = raw.strip()
    if _RELATED_TO_APP_RE.match(value) or _RELATED_TO_RE.match(value):
        return value
    msg = (
        f"Invalid to={value!r}; use Model or app_label.Model "
        "(e.g. Author or blog.Author)"
    )
    raise FieldParseError(msg)


def parse_field(raw: str) -> FieldSpec:
    """Parse a single ``name:type[:k=v...]`` declaration."""
    parts = [p.strip() for p in raw.split(":")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        msg = f"Malformed field {raw!r}; expected name:type[:options]"
        raise FieldParseError(msg)

    name, type_key, *option_parts = parts
    if not _FIELD_NAME_RE.match(name):
        msg = f"Invalid field name {name!r}; use snake_case starting with a letter"
        raise FieldParseError(msg)
    if name in RESERVED_FIELD_NAMES:
        msg = f"Field name {name!r} is reserved"
        raise FieldParseError(msg)
    type_key = type_key.lower()
    if type_key not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        msg = f"Unknown field type {type_key!r}; allowed: {allowed}"
        raise FieldParseError(msg)

    null = blank = unique = False
    blank_explicit = False
    default: str | None = None
    max_length: int | None = 255 if type_key == "char" else None
    max_digits: int | None = 10 if type_key == "decimal" else None
    decimal_places: int | None = 2 if type_key == "decimal" else None
    related_to: str | None = None
    on_delete: str | None = "cascade" if type_key in {"fk", "o2o"} else None

    for opt in option_parts:
        if not opt:
            continue
        if "=" in opt:
            key, value = opt.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
        else:
            key = opt.strip().lower()
            value = "true"

        if key in {"null", "blank", "unique"}:
            flag = _parse_bool(value)
            if key == "null":
                null = flag
            elif key == "blank":
                blank = flag
                blank_explicit = True
            else:
                unique = flag
        elif key == "default":
            default = value
        elif key == "max":
            max_length = int(value)
        elif key == "max_digits":
            max_digits = int(value)
        elif key == "decimal_places":
            decimal_places = int(value)
        elif key == "to":
            if type_key not in RELATION_TYPES:
                msg = f"Option to= is only valid for fk/o2o/m2m (got {type_key})"
                raise FieldParseError(msg)
            related_to = _validate_related_to(value)
        elif key == "on_delete":
            if type_key not in {"fk", "o2o"}:
                msg = f"Option on_delete= is only valid for fk/o2o (got {type_key})"
                raise FieldParseError(msg)
            token = value.lower()
            if token not in ON_DELETE_CHOICES:
                allowed = ", ".join(sorted(ON_DELETE_CHOICES))
                msg = f"Unknown on_delete {value!r}; allowed: {allowed}"
                raise FieldParseError(msg)
            on_delete = token
        else:
            msg = f"Unknown field option {key!r} in {raw!r}"
            raise FieldParseError(msg)

    if type_key == "decimal" and (max_digits is None or decimal_places is None):
        msg = "decimal fields require max_digits and decimal_places"
        raise FieldParseError(msg)

    if type_key in RELATION_TYPES and not related_to:
        msg = f"{type_key} fields require to=Model or to=app.Model"
        raise FieldParseError(msg)

    if type_key == "m2m":
        on_delete = None
        if not blank_explicit:
            blank = True

    if on_delete == "set_null":
        null = True
        blank = True

    return FieldSpec(
        name=name,
        type_key=type_key,
        null=null,
        blank=blank,
        unique=unique,
        default=default,
        max_length=max_length,
        max_digits=max_digits,
        decimal_places=decimal_places,
        related_to=related_to,
        on_delete=on_delete,
    )


_COMPACT_FIELD_SPLIT_RE = re.compile(r",(?=[a-z][a-z0-9_]*:)")


def split_compact_fields(raw: str) -> list[str]:
    """Split a compact ``--fields`` string into individual field declarations.

    Splits on commas that precede the next ``name:type`` token so values like
    ``to=blog.Author`` stay intact. Commas inside option values that look like
    another field start are not supported — use repeatable ``--field`` instead.
    """
    text = raw.strip()
    if not text:
        return []
    return [part.strip() for part in _COMPACT_FIELD_SPLIT_RE.split(text) if part.strip()]


def parse_fields(raw_fields: list[str] | None) -> list[FieldSpec]:
    """Parse fields; default to ``name:char:max=255`` when empty."""
    if not raw_fields:
        return [parse_field("name:char:max=255")]
    return [parse_field(item) for item in raw_fields]
