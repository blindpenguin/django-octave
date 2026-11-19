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
    }
)

RESERVED_FIELD_NAMES: frozenset[str] = frozenset(
    {"id", "pk", "objects", "all_objects", "DoesNotExist", "MultipleObjectsReturned"}
)

_FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
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


def _parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    msg = f"Invalid boolean value {raw!r}"
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
    default: str | None = None
    max_length: int | None = 255 if type_key == "char" else None
    max_digits: int | None = 10 if type_key == "decimal" else None
    decimal_places: int | None = 2 if type_key == "decimal" else None

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
        else:
            msg = f"Unknown field option {key!r} in {raw!r}"
            raise FieldParseError(msg)

    if type_key == "decimal" and (max_digits is None or decimal_places is None):
        msg = "decimal fields require max_digits and decimal_places"
        raise FieldParseError(msg)

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
    )


def parse_fields(raw_fields: list[str] | None) -> list[FieldSpec]:
    """Parse fields; default to ``name:char:max=255`` when empty."""
    if not raw_fields:
        return [parse_field("name:char:max=255")]
    return [parse_field(item) for item in raw_fields]
