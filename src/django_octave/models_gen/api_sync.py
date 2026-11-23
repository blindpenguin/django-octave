"""Keep serializer/admin/views/urls in sync with a new model."""

from __future__ import annotations

from pathlib import Path

from django_octave.fields.codegen import filterable_field_names
from django_octave.fields.parser import FieldSpec
from django_octave.models_gen.cst_util import (
    add_to_import,
    ensure_router_registration,
    upsert_class,
)
from django_octave.naming import pascal_to_snake, pluralize
from django_octave.tenancy import (
    TENANCY_IMPORT,
    ensure_tenancy_module,
    viewset_bases,
)


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


def _viewset_class(model_name: str, fields: list[FieldSpec], *, scoped: bool) -> str:
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
class {model_name}ViewSet({viewset_bases(scoped=scoped)}):
    queryset = {model_name}.objects.all()
    serializer_class = {model_name}Serializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {filter_repr}
    search_fields = {search_repr}
"""


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


def _write_views_file(
    path: Path, app_name: str, model_name: str, fields: list[FieldSpec], *, scoped: bool
) -> None:
    path.write_text(
        f'''"""API views for {app_name}."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

{TENANCY_IMPORT if scoped else ""}from apps.{app_name}.models import {model_name}
from apps.{app_name}.serializers import {model_name}Serializer
{_viewset_class(model_name, fields, scoped=scoped)}
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


def sync_api_stubs(
    app_dir: Path,
    *,
    app_name: str,
    model_name: str,
    fields: list[FieldSpec],
    force: bool,
    use_multitenancy: bool = False,
) -> None:
    """Create or update DRF stubs for ``model_name`` in ``app_dir``.

    With ``use_multitenancy`` the model is tenant-aware, so its viewset gets
    ``TenantScopedMixin``.
    """
    scoped = use_multitenancy
    if scoped:
        ensure_tenancy_module(app_dir.parent)
    serializers = app_dir / "serializers.py"
    admin = app_dir / "admin.py"
    views = app_dir / "views.py"
    urls = app_dir / "urls.py"

    if not serializers.exists():
        _write_serializers_file(serializers, app_name, model_name, fields)
    else:
        text = add_to_import(
            serializers.read_text(encoding="utf-8"),
            f"apps.{app_name}.models",
            model_name,
        )
        serializers.write_text(text, encoding="utf-8")
        upsert_class(
            serializers,
            f"{model_name}Serializer",
            _serializer_class(model_name, fields),
            force=force,
            header_imports=["from rest_framework import serializers\n"],
        )

    if not admin.exists():
        _write_admin_file(admin, app_name, model_name, fields)
    else:
        text = add_to_import(
            admin.read_text(encoding="utf-8"),
            f"apps.{app_name}.models",
            model_name,
        )
        admin.write_text(text, encoding="utf-8")
        upsert_class(
            admin,
            f"{model_name}Admin",
            _admin_class(model_name, fields),
            force=force,
            header_imports=["from django.contrib import admin\n"],
        )

    if not views.exists():
        _write_views_file(views, app_name, model_name, fields, scoped=scoped)
    else:
        text = views.read_text(encoding="utf-8")
        text = add_to_import(text, f"apps.{app_name}.models", model_name)
        text = add_to_import(text, f"apps.{app_name}.serializers", f"{model_name}Serializer")
        views.write_text(text, encoding="utf-8")
        upsert_class(
            views,
            f"{model_name}ViewSet",
            _viewset_class(model_name, fields, scoped=scoped),
            force=force,
            header_imports=[
                "from drf_spectacular.utils import extend_schema, extend_schema_view\n",
                "from rest_framework import viewsets\n",
                "from rest_framework.permissions import IsAuthenticated\n",
                *([TENANCY_IMPORT] if scoped else []),
            ],
        )

    if not urls.exists():
        _write_urls_file(urls, app_name, model_name)
    else:
        ensure_router_registration(urls, app_name, model_name)
