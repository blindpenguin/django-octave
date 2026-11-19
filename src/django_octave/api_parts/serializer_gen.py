"""Generate or refresh ModelSerializer classes for an existing model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.inspect.model_fields import ModelFieldInfo, inspect_model_fields_path
from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    ensure_import_lines,
    upsert_class,
)


class SerializerExistsError(FileExistsError):
    """Raised when the serializer class already exists without force."""


class SerializerFieldError(ValueError):
    """Raised when a requested field name is not known on the model."""


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


_DEFAULT_READ_ONLY = ("id", "created_at", "updated_at")


def resolve_field_lists(
    info: ModelFieldInfo,
    *,
    fields: list[str] | None,
    read_only: list[str] | None,
    include_id: bool,
) -> tuple[list[str], list[str]]:
    """Return ``(meta_fields, read_only_fields)`` validated against ``info``."""
    available = set(info.available_names)
    available.update({"id", "created_at", "updated_at"})

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

    return meta, ro


def build_serializer_class(
    model_name: str,
    *,
    fields: list[str],
    read_only: list[str],
) -> str:
    fields_tuple = ", ".join(f'"{n}"' for n in fields)
    if fields_tuple:
        fields_tuple += ","
    ro_tuple = ", ".join(f'"{n}"' for n in read_only)
    if ro_tuple:
        ro_tuple += ","
    return f"""
class {model_name}Serializer(serializers.ModelSerializer):
    class Meta:
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
    )
    class_name = f"{options.model_name}Serializer"
    class_src = build_serializer_class(
        options.model_name,
        fields=meta_fields,
        read_only=read_only,
    )
    path = app_dir / "serializers.py"

    if not path.exists():
        path.write_text(
            _serializers_header(options.app_name, options.model_name) + class_src,
            encoding="utf-8",
        )
        return path

    source = path.read_text(encoding="utf-8")
    exists = class_exists(source, class_name)
    if exists and not options.force:
        raise SerializerExistsError(
            f"{class_name} already exists in {path}. Use --force to replace it."
        )

    source = add_to_import(source, f"apps.{options.app_name}.models", options.model_name)
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
