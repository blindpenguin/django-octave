"""Generate or refresh ModelSerializer classes for an existing model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    inspect_model_fields_path,
    resolve_related_app_and_model,
)
from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    ensure_class_before,
    ensure_import_lines,
    upsert_class,
)
from django_octave.models_gen.writer import ModelWriteError, model_exists


class SerializerExistsError(OctaveError, FileExistsError):
    """Raised when the serializer class already exists without force."""


class SerializerFieldError(OctaveError, ValueError):
    """Raised when a requested field name is not known on the model."""


@dataclass
class NestedRef:
    field_name: str
    serializer_class: str | None = None
    """Explicit nested class name; None → ``{RelatedModel}NestedSerializer``."""


@dataclass
class SerializerOptions:
    app_name: str
    model_name: str
    fields: list[str] | None = None
    """Explicit Meta.fields; None means use inspected defaults."""

    read_only: list[str] | None = None
    """Explicit read-only names; merged with defaults for id/timestamps."""

    include_id: bool = True
    force: bool = False
    nested: list[NestedRef] = field(default_factory=list)


_DEFAULT_READ_ONLY = ("id", "created_at", "updated_at")
_NEST_DISPLAY_CANDIDATES = ("name", "title", "slug", "email")


def parse_nested_option(raw: str) -> NestedRef:
    """Parse ``author`` or ``author=AuthorSerializer``."""
    text = raw.strip()
    if not text:
        raise SerializerFieldError("Empty --nested value")
    if "=" in text:
        name, cls = text.split("=", 1)
        name, cls = name.strip(), cls.strip()
        if not name or not cls:
            raise SerializerFieldError(f"Malformed --nested {raw!r}")
        return NestedRef(field_name=name, serializer_class=cls)
    return NestedRef(field_name=text)


def resolve_field_lists(
    info: ModelFieldInfo,
    *,
    fields: list[str] | None,
    read_only: list[str] | None,
    include_id: bool,
    nested: list[NestedRef] | None = None,
) -> tuple[list[str], list[str]]:
    """Return ``(meta_fields, read_only_fields)`` validated against ``info``."""
    available = set(info.available_names)
    available.update({"id", "created_at", "updated_at"})
    for name, rel in info.relations.items():
        if rel.kind in {"fk", "o2o"}:
            available.add(f"{name}_id")

    if fields is None:
        meta = list(info.available_names)
        if not include_id:
            meta = [n for n in meta if n != "id"]
    else:
        meta = list(fields)
        if include_id and "id" not in meta:
            meta = ["id", *meta]
        if not include_id:
            meta = [n for n in meta if n != "id"]

    nested = nested or []
    for ref in nested:
        if ref.field_name not in info.relations:
            raise SerializerFieldError(
                f"Cannot nest {ref.field_name!r}: not a relation field. "
                f"Relations: {', '.join(sorted(info.relations)) or '(none)'}"
            )
        if ref.field_name not in meta:
            meta.append(ref.field_name)
        rel = info.relations[ref.field_name]
        if rel.kind in {"fk", "o2o"}:
            attname = f"{ref.field_name}_id"
            if attname not in meta:
                meta.append(attname)

    unknown = [n for n in meta if n not in available]
    if unknown:
        valid = ", ".join(sorted(available))
        raise SerializerFieldError(
            f"Unknown field(s): {', '.join(unknown)}. Valid: {valid}"
        )

    if read_only is None:
        ro = [n for n in _DEFAULT_READ_ONLY if n in meta]
    else:
        unknown_ro = [n for n in read_only if n not in available]
        if unknown_ro:
            valid = ", ".join(sorted(available))
            raise SerializerFieldError(
                f"Unknown read-only field(s): {', '.join(unknown_ro)}. Valid: {valid}"
            )
        merged = list(
            dict.fromkeys([*read_only, *[n for n in _DEFAULT_READ_ONLY if n in meta]])
        )
        ro = [n for n in merged if n in meta]

    for ref in nested:
        if ref.field_name not in ro:
            ro.append(ref.field_name)

    return meta, ro


def _slim_nested_fields(related: ModelFieldInfo) -> list[str]:
    names = ["id"]
    for candidate in _NEST_DISPLAY_CANDIDATES:
        if candidate in related.fields:
            names.append(candidate)
            break
    return names


def build_nested_serializer_class(model_name: str, *, fields: list[str]) -> str:
    fields_tuple = ", ".join(f'"{n}"' for n in fields)
    if fields_tuple:
        fields_tuple += ","
    return f"""
class {model_name}NestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = {model_name}
        fields = ({fields_tuple})
        read_only_fields = ({fields_tuple})
"""


def build_serializer_class(
    model_name: str,
    *,
    fields: list[str],
    read_only: list[str],
    nested_decls: list[tuple[str, str]] | None = None,
) -> str:
    """Build parent serializer; ``nested_decls`` is ``(field_name, SerializerClass)``."""
    nested_decls = nested_decls or []
    decl_lines = [
        f"    {fname} = {scls}(read_only=True)" for fname, scls in nested_decls
    ]
    body = ("\n".join(decl_lines) + "\n") if decl_lines else ""
    fields_tuple = ", ".join(f'"{n}"' for n in fields)
    if fields_tuple:
        fields_tuple += ","
    ro_tuple = ", ".join(f'"{n}"' for n in read_only)
    if ro_tuple:
        ro_tuple += ","
    return f"""
class {model_name}Serializer(serializers.ModelSerializer):
{body}    class Meta:
        model = {model_name}
        fields = ({fields_tuple})
        read_only_fields = ({ro_tuple})
"""


def _serializers_header(app_name: str, model_name: str) -> str:
    return f'''"""Serializers for {app_name}."""

from __future__ import annotations

from rest_framework import serializers

from apps.{app_name}.models import {model_name}
'''


def _ensure_nested_helpers(
    app_dir: Path,
    *,
    parent_app: str,
    parent_serializer: str,
    nested: list[NestedRef],
    info: ModelFieldInfo,
    force: bool,
) -> list[tuple[str, str]]:
    """Create slim nested serializers; return ``(field, class_name)`` decls.

    Helpers are inserted **before** ``parent_serializer`` when that class
    already exists, so nested class names are defined before use.
    """
    decls: list[tuple[str, str]] = []
    ser_path = app_dir / "serializers.py"
    parent_exists = class_exists(
        ser_path.read_text(encoding="utf-8"), parent_serializer
    )
    before = parent_serializer if parent_exists else None

    for ref in nested:
        rel = info.relations[ref.field_name]
        if rel.to is None:
            raise SerializerFieldError(
                f"Cannot nest {ref.field_name!r}: relation target not found in models.py AST"
            )
        rel_app, rel_model = resolve_related_app_and_model(
            rel.to, default_app=parent_app
        )
        class_name = ref.serializer_class or f"{rel_model}NestedSerializer"
        decls.append((ref.field_name, class_name))

        if ref.serializer_class is not None:
            continue

        related_models = (
            app_dir / "models.py"
            if rel_app == parent_app
            else app_dir.parent / rel_app / "models.py"
        )
        if not related_models.is_file():
            raise ModelWriteError(
                f"Related model app models.py not found for {rel.to!r}: {related_models}"
            )
        related_source = related_models.read_text(encoding="utf-8")
        if not model_exists(related_source, rel_model):
            raise ModelWriteError(
                f"Related model {rel_model} not found for nesting {ref.field_name}. "
                f"Run: django-octave add-model {rel_app} {rel_model}"
            )
        related_info = inspect_model_fields_path(related_models, rel_model)
        slim_fields = _slim_nested_fields(related_info)
        nested_src = build_nested_serializer_class(rel_model, fields=slim_fields)

        source = ser_path.read_text(encoding="utf-8")
        source = add_to_import(source, f"apps.{rel_app}.models", rel_model)
        source = ensure_import_lines(
            source, ["from rest_framework import serializers\n"]
        )
        ser_path.write_text(source, encoding="utf-8")

        exists = class_exists(ser_path.read_text(encoding="utf-8"), class_name)
        if exists and not force:
            if before:
                ensure_class_before(ser_path, class_name, before)
            continue
        upsert_class(
            ser_path,
            class_name,
            nested_src,
            force=exists and force,
            header_imports=["from rest_framework import serializers\n"],
            before=before,
        )

    return decls


def write_serializer(
    app_dir: Path,
    *,
    options: SerializerOptions,
    info: ModelFieldInfo | None = None,
) -> Path:
    """Upsert ``<Model>Serializer`` under ``app_dir/serializers.py``.

    Returns the serializers.py path.
    """
    models_path = app_dir / "models.py"
    if info is None:
        info = inspect_model_fields_path(models_path, options.model_name)

    meta_fields, read_only = resolve_field_lists(
        info,
        fields=options.fields,
        read_only=options.read_only,
        include_id=options.include_id,
        nested=options.nested,
    )

    path = app_dir / "serializers.py"
    if not path.exists():
        path.write_text(
            _serializers_header(options.app_name, options.model_name),
            encoding="utf-8",
        )

    source = path.read_text(encoding="utf-8")
    class_name = f"{options.model_name}Serializer"
    exists = class_exists(source, class_name)
    if exists and not options.force:
        raise SerializerExistsError(
            f"{class_name} already exists in {path}. Use --force to replace it."
        )

    nested_decls = _ensure_nested_helpers(
        app_dir,
        parent_app=options.app_name,
        parent_serializer=class_name,
        nested=options.nested,
        info=info,
        force=options.force,
    )

    class_src = build_serializer_class(
        options.model_name,
        fields=meta_fields,
        read_only=read_only,
        nested_decls=nested_decls,
    )

    source = path.read_text(encoding="utf-8")
    source = add_to_import(
        source, f"apps.{options.app_name}.models", options.model_name
    )
    source = ensure_import_lines(source, ["from rest_framework import serializers\n"])
    path.write_text(source, encoding="utf-8")

    upsert_class(
        path,
        class_name,
        class_src,
        force=exists and options.force,
        header_imports=["from rest_framework import serializers\n"],
    )
    return path
