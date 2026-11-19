"""Keep serializer/admin/views/urls in sync with a new model."""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from django_octave.fields.codegen import filterable_field_names
from django_octave.fields.parser import FieldSpec
from django_octave.models_gen.writer import ModelWriteError, _RemoveClass
from django_octave.naming import pascal_to_snake, pluralize


def _serializer_class(model_name: str, fields: list[FieldSpec]) -> str:
    field_names = ["id", *[f.name for f in fields], "created_at", "updated_at"]
    fields_tuple = ", ".join(f'"{n}"' for n in field_names)
    return f"""
class {model_name}Serializer(serializers.ModelSerializer):
    class Meta:
        model = {model_name}
        fields = ({fields_tuple},)
        read_only_fields = ("id", "created_at", "updated_at",)
"""


def _admin_class(model_name: str, fields: list[FieldSpec]) -> str:
    display_names = ["id", *[f.name for f in fields], "created_at", "updated_at"]
    display = ", ".join(f'"{n}"' for n in display_names)
    search_fields = [f.name for f in fields if f.type_key in {"char", "slug", "email", "text"}]
    search = "(" + ", ".join(f'"{n}"' for n in search_fields) + ("," if search_fields else "") + ")"
    return f"""
@admin.register({model_name})
class {model_name}Admin(admin.ModelAdmin):
    list_display = ({display},)
    search_fields = {search}
"""


def _viewset_class(model_name: str, fields: list[FieldSpec]) -> str:
    tag = pascal_to_snake(model_name)
    filter_fields = filterable_field_names(fields)
    filter_repr = "[" + ", ".join(f'"{n}"' for n in filter_fields) + "]"
    search = [f.name for f in fields if f.type_key in {"char", "slug", "email", "text"}]
    search_repr = "[" + ", ".join(f'"{n}"' for n in search) + "]"
    return f"""
@extend_schema_view(
    list=extend_schema(tags=["{tag}"]),
    retrieve=extend_schema(tags=["{tag}"]),
    create=extend_schema(tags=["{tag}"]),
    update=extend_schema(tags=["{tag}"]),
    partial_update=extend_schema(tags=["{tag}"]),
    destroy=extend_schema(tags=["{tag}"]),
)
class {model_name}ViewSet(viewsets.ModelViewSet):
    queryset = {model_name}.objects.all()
    serializer_class = {model_name}Serializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {filter_repr}
    search_fields = {search_repr}
"""


def _ensure_import_lines(source: str, lines: list[str]) -> str:
    for line in lines:
        bare = line if line.endswith("\n") else line + "\n"
        if bare.strip() and bare.strip() not in {row.strip() for row in source.splitlines()}:
            parts = source.splitlines(keepends=True)
            idx = 0
            for i, row in enumerate(parts):
                if row.startswith("from __future__") or row.startswith(("import ", "from ")):
                    idx = i + 1
            parts.insert(idx, bare)
            source = "".join(parts)
    return source


def _add_to_import(source: str, module: str, symbol: str) -> str:
    prefix = f"from {module} import "
    if symbol in source and prefix in source:
        # crude: if symbol already imported from module
        for line in source.splitlines():
            if line.startswith(prefix) and symbol in line:
                return source
    if prefix in source:
        lines = source.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(prefix) and symbol not in line:
                lines[i] = line.rstrip("\n").rstrip() + f", {symbol}\n"
                return "".join(lines)
    return _ensure_import_lines(source, [f"{prefix}{symbol}\n"])


def _class_exists(source: str, class_name: str) -> bool:
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return f"class {class_name}" in source
    return any(isinstance(n, cst.ClassDef) and n.name.value == class_name for n in module.body)


def _upsert_class(
    path: Path,
    class_name: str,
    class_src: str,
    *,
    force: bool,
    header_imports: list[str],
) -> None:
    source = path.read_text(encoding="utf-8")
    source = _ensure_import_lines(source, header_imports)
    path.write_text(source, encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    exists = _class_exists(source, class_name)
    if exists and not force:
        return
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    if exists and force:
        module = module.visit(_RemoveClass(class_name))
    addition = cst.parse_module(class_src.lstrip("\n"))
    updated = module.with_changes(body=[*module.body, *addition.body])
    path.write_text(updated.code, encoding="utf-8")


def _write_serializers_file(path: Path, app_name: str, model_name: str, fields: list[FieldSpec]) -> None:
    path.write_text(
        f'''"""Serializers for {app_name}."""

from __future__ import annotations

from rest_framework import serializers

from apps.{app_name}.models import {model_name}
{_serializer_class(model_name, fields)}
''',
        encoding="utf-8",
    )


def _write_admin_file(path: Path, app_name: str, model_name: str, fields: list[FieldSpec]) -> None:
    path.write_text(
        f'''from django.contrib import admin

from apps.{app_name}.models import {model_name}
{_admin_class(model_name, fields)}
''',
        encoding="utf-8",
    )


def _write_views_file(path: Path, app_name: str, model_name: str, fields: list[FieldSpec]) -> None:
    path.write_text(
        f'''"""API views for {app_name}."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.{app_name}.models import {model_name}
from apps.{app_name}.serializers import {model_name}Serializer
{_viewset_class(model_name, fields)}
''',
        encoding="utf-8",
    )


def _write_urls_file(path: Path, app_name: str, model_name: str) -> None:
    snake = pascal_to_snake(model_name)
    plural = pluralize(snake)
    path.write_text(
        f'''"""URL routes for {app_name}."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.{app_name}.views import {model_name}ViewSet

router = DefaultRouter()
router.register("{plural}", {model_name}ViewSet, basename="{snake}")

urlpatterns = [
    path("", include(router.urls)),
]
''',
        encoding="utf-8",
    )


def _ensure_router_registration(path: Path, app_name: str, model_name: str) -> None:
    source = path.read_text(encoding="utf-8")
    snake = pascal_to_snake(model_name)
    plural = pluralize(snake)
    register = f'router.register("{plural}", {model_name}ViewSet, basename="{snake}")'
    source = _add_to_import(source, f"apps.{app_name}.views", f"{model_name}ViewSet")
    if register not in source and f"{model_name}ViewSet" not in [
        line for line in source.splitlines() if "router.register" in line
    ]:
        # still add if no register line for this viewset
        if not any(
            "router.register" in line and f"{model_name}ViewSet" in line
            for line in source.splitlines()
        ):
            ridx = source.rfind("router.register(")
            if ridx != -1:
                end = source.find("\n", ridx)
                source = source[: end + 1] + register + "\n" + source[end + 1 :]
            else:
                idx = source.find("urlpatterns")
                if idx == -1:
                    source = source.rstrip() + "\n" + register + "\n"
                else:
                    source = source[:idx] + register + "\n\n" + source[idx:]
    path.write_text(source, encoding="utf-8")


def sync_api_stubs(
    app_dir: Path,
    *,
    app_name: str,
    model_name: str,
    fields: list[FieldSpec],
    force: bool,
) -> None:
    """Create or update DRF stubs for ``model_name`` in ``app_dir``."""
    serializers = app_dir / "serializers.py"
    admin = app_dir / "admin.py"
    views = app_dir / "views.py"
    urls = app_dir / "urls.py"

    if not serializers.exists():
        _write_serializers_file(serializers, app_name, model_name, fields)
    else:
        text = _add_to_import(
            serializers.read_text(encoding="utf-8"),
            f"apps.{app_name}.models",
            model_name,
        )
        serializers.write_text(text, encoding="utf-8")
        _upsert_class(
            serializers,
            f"{model_name}Serializer",
            _serializer_class(model_name, fields),
            force=force,
            header_imports=["from rest_framework import serializers\n"],
        )

    if not admin.exists():
        _write_admin_file(admin, app_name, model_name, fields)
    else:
        text = _add_to_import(
            admin.read_text(encoding="utf-8"),
            f"apps.{app_name}.models",
            model_name,
        )
        admin.write_text(text, encoding="utf-8")
        _upsert_class(
            admin,
            f"{model_name}Admin",
            _admin_class(model_name, fields),
            force=force,
            header_imports=["from django.contrib import admin\n"],
        )

    if not views.exists():
        _write_views_file(views, app_name, model_name, fields)
    else:
        text = views.read_text(encoding="utf-8")
        text = _add_to_import(text, f"apps.{app_name}.models", model_name)
        text = _add_to_import(text, f"apps.{app_name}.serializers", f"{model_name}Serializer")
        views.write_text(text, encoding="utf-8")
        _upsert_class(
            views,
            f"{model_name}ViewSet",
            _viewset_class(model_name, fields),
            force=force,
            header_imports=[
                "from drf_spectacular.utils import extend_schema, extend_schema_view\n",
                "from rest_framework import viewsets\n",
                "from rest_framework.permissions import IsAuthenticated\n",
            ],
        )

    if not urls.exists():
        _write_urls_file(urls, app_name, model_name)
    else:
        _ensure_router_registration(urls, app_name, model_name)
