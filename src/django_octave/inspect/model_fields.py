"""Inspect concrete Django model fields from models.py via libcst (no Django runtime)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import libcst as cst

from django_octave.models_gen.writer import ModelWriteError

_TIMESTAMP_BASES = frozenset({"TimeStampedModel", "TenantAwareModel"})
_FILTERABLE_TYPES = frozenset(
    {
        "CharField",
        "BooleanField",
        "IntegerField",
        "PositiveIntegerField",
        "SmallIntegerField",
        "BigIntegerField",
        "SlugField",
        "UUIDField",
        "EmailField",
        "ForeignKey",
        "OneToOneField",
    }
)
_SEARCHABLE_TYPES = frozenset({"CharField", "SlugField", "EmailField", "TextField"})
_RELATION_KINDS: dict[str, Literal["fk", "o2o", "m2m"]] = {
    "ForeignKey": "fk",
    "OneToOneField": "o2o",
    "ManyToManyField": "m2m",
}


@dataclass(frozen=True)
class RelationInfo:
    """Metadata for a relation field discovered on a model."""

    kind: Literal["fk", "o2o", "m2m"]
    to: str | None
    """Target as ``Author`` or ``blog.Author`` when parseable from AST."""


@dataclass(frozen=True)
class ModelFieldInfo:
    """Result of inspecting one model class in models.py."""

    model_name: str
    fields: dict[str, str] = field(default_factory=dict)
    """Map of attribute name → Django field class name (e.g. ``CharField``)."""

    relations: dict[str, RelationInfo] = field(default_factory=dict)
    """Relation fields keyed by attribute name."""

    blank_fields: frozenset[str] = field(default_factory=frozenset)
    """Fields declared with ``blank=True`` (optional on forms)."""

    null_fields: frozenset[str] = field(default_factory=frozenset)
    """Fields declared with ``null=True``."""

    has_timestamps: bool = False
    """True when bases include TimeStampedModel or TenantAwareModel."""

    has_tenant_aware: bool = False
    """True when bases include TenantAwareModel."""

    @property
    def concrete_names(self) -> list[str]:
        return list(self.fields.keys())

    @property
    def available_names(self) -> list[str]:
        """Names valid for serializer Meta.fields (includes id and timestamps)."""
        names: list[str] = ["id"]
        names.extend(self.concrete_names)
        if self.has_timestamps:
            for ts in ("created_at", "updated_at"):
                if ts not in names:
                    names.append(ts)
        return names


def _attr_chain(node: cst.BaseExpression) -> list[str] | None:
    """Return dotted name parts for ``models.CharField``-style Attribute chains."""
    parts: list[str] = []
    cur: cst.BaseExpression = node
    while isinstance(cur, cst.Attribute):
        if not isinstance(cur.attr, cst.Name):
            return None
        parts.append(cur.attr.value)
        cur = cur.value
    if isinstance(cur, cst.Name):
        parts.append(cur.value)
        parts.reverse()
        return parts
    return None


def _field_type_from_call(value: cst.BaseExpression) -> str | None:
    """If ``value`` is a call to ``models.*Field`` / ``ForeignKey`` etc., return the type name."""
    if not isinstance(value, cst.Call):
        return None
    parts = _attr_chain(value.func)
    if not parts:
        return None
    type_name = parts[-1]
    if not type_name.endswith("Field") and type_name not in {
        "ForeignKey",
        "OneToOneField",
        "ManyToManyField",
    }:
        return None
    if len(parts) >= 2 and parts[-2] == "models":
        return type_name
    if len(parts) == 1:
        return type_name
    return None


def _literal_str(node: cst.BaseExpression) -> str | None:
    if isinstance(node, cst.SimpleString):
        raw = node.value
        if len(raw) >= 2 and raw[0] in {'"', "'"} and raw[-1] == raw[0]:
            return raw[1:-1]
    return None


def _relation_to_from_call(value: cst.Call) -> str | None:
    """Extract first positional or ``to=`` target from a relation field call."""
    for arg in value.args:
        if arg.keyword is None:
            lit = _literal_str(arg.value)
            if lit is not None:
                return lit
            if isinstance(arg.value, cst.Name):
                return arg.value.value
            parts = _attr_chain(arg.value)
            if parts:
                return ".".join(parts)
            break
    for arg in value.args:
        if arg.keyword is not None and arg.keyword.value == "to":
            lit = _literal_str(arg.value)
            if lit is not None:
                return lit
            if isinstance(arg.value, cst.Name):
                return arg.value.value
    return None


def _assign_targets(target: cst.BaseAssignTargetExpression) -> list[str]:
    if isinstance(target, cst.Name):
        return [target.value]
    if isinstance(target, cst.Tuple):
        names: list[str] = []
        for elt in target.elements:
            names.extend(_assign_targets(elt.value))
        return names
    return []


def _call_kw_is_true(call: cst.Call, keyword: str) -> bool:
    for arg in call.args:
        if arg.keyword is not None and arg.keyword.value == keyword:
            return isinstance(arg.value, cst.Name) and arg.value.value == "True"
    return False


def _record_field(
    fields: dict[str, str],
    relations: dict[str, RelationInfo],
    blank_fields: set[str],
    null_fields: set[str],
    name: str,
    field_type: str,
    call: cst.BaseExpression,
) -> None:
    if name == "objects":
        return
    fields[name] = field_type
    kind = _RELATION_KINDS.get(field_type)
    if kind is not None and isinstance(call, cst.Call):
        relations[name] = RelationInfo(kind=kind, to=_relation_to_from_call(call))
    if isinstance(call, cst.Call):
        if _call_kw_is_true(call, "blank"):
            blank_fields.add(name)
        if _call_kw_is_true(call, "null"):
            null_fields.add(name)


def _collect_from_class(node: cst.ClassDef) -> ModelFieldInfo:
    bases: list[str] = []
    for arg in node.bases:
        value = arg.value
        if isinstance(value, cst.Name):
            bases.append(value.value)
        else:
            parts = _attr_chain(value)
            if parts:
                bases.append(parts[-1])

    has_timestamps = any(b in _TIMESTAMP_BASES for b in bases)
    has_tenant_aware = "TenantAwareModel" in bases
    fields: dict[str, str] = {}
    relations: dict[str, RelationInfo] = {}
    blank_fields: set[str] = set()
    null_fields: set[str] = set()

    for stmt in node.body.body:
        if not isinstance(stmt, cst.SimpleStatementLine):
            continue
        for small in stmt.body:
            if isinstance(small, cst.Assign):
                field_type = _field_type_from_call(small.value)
                if field_type is None:
                    continue
                for name in _assign_targets(small.targets[0].target):
                    _record_field(
                        fields,
                        relations,
                        blank_fields,
                        null_fields,
                        name,
                        field_type,
                        small.value,
                    )
            elif isinstance(small, cst.AnnAssign) and small.value is not None:
                field_type = _field_type_from_call(small.value)
                if field_type is None:
                    continue
                if isinstance(small.target, cst.Name):
                    _record_field(
                        fields,
                        relations,
                        blank_fields,
                        null_fields,
                        small.target.value,
                        field_type,
                        small.value,
                    )

    return ModelFieldInfo(
        model_name=node.name.value,
        fields=fields,
        relations=relations,
        blank_fields=frozenset(blank_fields),
        null_fields=frozenset(null_fields),
        has_timestamps=has_timestamps,
        has_tenant_aware=has_tenant_aware,
    )


def inspect_model_fields(source: str, model_name: str) -> ModelFieldInfo:
    """Parse ``source`` and return field info for ``model_name``.

    Raises:
        ModelWriteError: if source cannot be parsed or the class is missing.
    """
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse models.py: {exc}") from exc

    for node in module.body:
        if isinstance(node, cst.ClassDef) and node.name.value == model_name:
            return _collect_from_class(node)

    raise ModelWriteError(f"Model class {model_name} not found in models.py")


def inspect_model_fields_path(models_path, model_name: str) -> ModelFieldInfo:
    """Read ``models_path`` and inspect ``model_name``."""
    from pathlib import Path

    path = Path(models_path)
    if not path.is_file():
        raise ModelWriteError(f"models.py not found: {path}")
    return inspect_model_fields(path.read_text(encoding="utf-8"), model_name)


def filterable_names(info: ModelFieldInfo) -> list[str]:
    """Field names suitable for default ``filterset_fields`` (AST type heuristic)."""
    return [name for name, ftype in info.fields.items() if ftype in _FILTERABLE_TYPES]


def searchable_names(info: ModelFieldInfo) -> list[str]:
    """Field names suitable for default ``search_fields``."""
    return [name for name, ftype in info.fields.items() if ftype in _SEARCHABLE_TYPES]


def default_ordering_names(info: ModelFieldInfo) -> list[str]:
    """Default ``ordering_fields``: name/title if present, else created_at, else empty."""
    names = set(info.available_names)
    for candidate in ("name", "title"):
        if candidate in names or candidate in info.fields:
            return [candidate]
    if info.has_timestamps or "created_at" in info.fields:
        return ["created_at"]
    return []


def resolve_related_app_and_model(
    to: str,
    *,
    default_app: str,
) -> tuple[str, str]:
    """Return ``(app_label, ModelName)`` from a ``to`` string."""
    if "." in to:
        app, model = to.split(".", 1)
        return app, model
    return default_app, to
