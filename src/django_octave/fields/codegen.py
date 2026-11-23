"""Map FieldSpec to Django model field source snippets."""

from __future__ import annotations

import json
import uuid

from django_octave.fields.parser import RELATION_TYPES, FieldSpec

_TYPE_MAP: dict[str, str] = {
    "char": "models.CharField",
    "text": "models.TextField",
    "int": "models.IntegerField",
    "bool": "models.BooleanField",
    "decimal": "models.DecimalField",
    "date": "models.DateField",
    "datetime": "models.DateTimeField",
    "email": "models.EmailField",
    "url": "models.URLField",
    "slug": "models.SlugField",
    "uuid": "models.UUIDField",
}

_ON_DELETE_MAP: dict[str, str] = {
    "cascade": "models.CASCADE",
    "protect": "models.PROTECT",
    "set_null": "models.SET_NULL",
    "set_default": "models.SET_DEFAULT",
    "do_nothing": "models.DO_NOTHING",
}

_RELATION_CTOR: dict[str, str] = {
    "fk": "models.ForeignKey",
    "o2o": "models.OneToOneField",
    "m2m": "models.ManyToManyField",
}


_TEXT_DEFAULT_TYPES = frozenset({"char", "text", "email", "url", "slug"})


def _default_expr(spec: FieldSpec) -> str | None:
    """Source for ``default=``; literals only (the parser has validated the value)."""
    if spec.default is None:
        return None
    raw = spec.default
    if spec.type_key == "bool":
        return "True" if raw == "true" else "False"
    if spec.type_key == "int":
        return str(int(raw))
    if spec.type_key in _TEXT_DEFAULT_TYPES or spec.type_key == "decimal":
        return json.dumps(raw, ensure_ascii=False)
    if spec.type_key == "uuid":
        if raw == "uuid4":
            return "uuid.uuid4"
        return f"uuid.UUID({json.dumps(str(uuid.UUID(raw)))})"
    msg = f"Unsupported default for {spec.type_key} field {spec.name!r}"
    raise ValueError(msg)


def _related_to_literal(related_to: str) -> str:
    return f'"{related_to}"'


def field_source(spec: FieldSpec) -> str:
    """Return ``name = models.X(...)`` source line (no trailing newline)."""
    if spec.type_key in RELATION_TYPES:
        assert spec.related_to is not None
        args: list[str] = [_related_to_literal(spec.related_to)]
        if spec.type_key in {"fk", "o2o"}:
            assert spec.on_delete is not None
            args.append(f"on_delete={_ON_DELETE_MAP[spec.on_delete]}")
        if spec.null:
            args.append("null=True")
        if spec.blank:
            args.append("blank=True")
        if spec.unique:
            args.append("unique=True")
        joined = ", ".join(args)
        ctor = _RELATION_CTOR[spec.type_key]
        return f"{spec.name} = {ctor}({joined})"

    args = []
    if spec.type_key == "char" and spec.max_length is not None:
        args.append(f"max_length={spec.max_length}")
    if spec.type_key == "slug" and spec.max_length is not None:
        args.append(f"max_length={spec.max_length}")
    if spec.type_key == "email" and spec.max_length is not None:
        args.append(f"max_length={spec.max_length}")
    if spec.type_key == "decimal":
        args.append(f"max_digits={spec.max_digits}")
        args.append(f"decimal_places={spec.decimal_places}")
    if spec.null:
        args.append("null=True")
    if spec.blank:
        args.append("blank=True")
    if spec.unique:
        args.append("unique=True")
    default = _default_expr(spec)
    if default is not None:
        args.append(f"default={default}")
    joined = ", ".join(args)
    ctor = _TYPE_MAP[spec.type_key]
    return f"{spec.name} = {ctor}({joined})"


def needs_uuid_import(fields: list[FieldSpec]) -> bool:
    """True when any field's default is written as ``uuid.uuid4`` / ``uuid.UUID(...)``."""
    return any(f.type_key == "uuid" and f.default is not None for f in fields)


def str_field_name(fields: list[FieldSpec]) -> str | None:
    """Pick a default ordering / ``__str__`` field.

    Prefer human label names, then other char-like fields. Do not prefer
    ``text`` when any char/slug/email field exists (e.g. ``note`` over ``body``).
    """
    names = {f.name for f in fields}
    for candidate in ("name", "title", "subject", "slug"):
        if candidate in names:
            return candidate
    for field in fields:
        if field.type_key in {"char", "slug", "email"}:
            return field.name
    for field in fields:
        if field.type_key == "text":
            return field.name
    return None


def filterable_field_names(fields: list[FieldSpec]) -> list[str]:
    allowed = {"char", "bool", "int", "slug", "uuid", "email", "fk", "o2o"}
    return [f.name for f in fields if f.type_key in allowed]
