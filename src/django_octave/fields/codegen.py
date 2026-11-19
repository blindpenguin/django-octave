"""Map FieldSpec to Django model field source snippets."""

from __future__ import annotations

from django_octave.fields.parser import FieldSpec

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


def _default_expr(spec: FieldSpec) -> str | None:
    if spec.default is None:
        return None
    raw = spec.default
    if spec.type_key == "bool":
        return "True" if raw.lower() in {"1", "true", "yes", "on"} else "False"
    if spec.type_key == "int":
        return str(int(raw))
    if spec.type_key == "uuid" and raw.lower() in {"uuid", "uuid4"}:
        return "uuid.uuid4"
    if spec.type_key in {"char", "text", "email", "url", "slug"}:
        escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if spec.type_key == "decimal":
        return f'"{raw}"'
    return raw


def field_source(spec: FieldSpec) -> str:
    """Return ``name = models.X(...)`` source line (no trailing newline)."""
    args: list[str] = []
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
    return any(
        f.type_key == "uuid" and f.default is not None and f.default.lower() in {"uuid", "uuid4"}
        for f in fields
    )


def str_field_name(fields: list[FieldSpec]) -> str | None:
    names = {f.name for f in fields}
    for candidate in ("name", "title"):
        if candidate in names:
            return candidate
    for field in fields:
        if field.type_key in {"char", "slug", "email", "text"}:
            return field.name
    return None


def filterable_field_names(fields: list[FieldSpec]) -> list[str]:
    allowed = {"char", "bool", "int", "slug", "uuid", "email"}
    return [f.name for f in fields if f.type_key in allowed]
