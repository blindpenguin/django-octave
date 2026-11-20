"""Generate or refresh ModelViewSet classes and router registration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.api_parts.serializer_gen import SerializerOptions, write_serializer
from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    default_ordering_names,
    filterable_names,
    inspect_model_fields_path,
    searchable_names,
)
from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    ensure_import_lines,
    ensure_router_registration,
    upsert_class,
)
from django_octave.naming import pascal_to_snake

PERMISSIONS: dict[str, str] = {
    "IsAuthenticated": "rest_framework.permissions.IsAuthenticated",
    "AllowAny": "rest_framework.permissions.AllowAny",
    "IsAdminUser": "rest_framework.permissions.IsAdminUser",
}


class ViewSetExistsError(FileExistsError):
    """Raised when the viewset class already exists without force."""


class ViewSetPermissionError(ValueError):
    """Raised when permission is outside the allowlist."""


class ViewSetFieldError(ValueError):
    """Raised when a filter/search/ordering field is unknown."""


@dataclass
class ViewSetOptions:
    app_name: str
    model_name: str
    permission: str = "IsAuthenticated"
    filters: list[str] | None = None
    search: list[str] | None = None
    ordering: list[str] | None = None
    tag: str | None = None
    force: bool = False


def validate_permission(name: str) -> str:
    """Validate a stock DRF permission name (allowlist only)."""
    if name not in PERMISSIONS:
        allowed = ", ".join(sorted(PERMISSIONS))
        raise ViewSetPermissionError(
            f"Unknown permission {name!r}. Allowed: {allowed}"
        )
    return name


def resolve_permission(
    app_dir: Path,
    app_name: str,
    name: str,
) -> tuple[str, str]:
    """Resolve permission to ``(import_module, symbol)``.

    Stock allowlist first; otherwise a class defined in
    ``apps.<app>/permissions.py``.
    """
    if name in PERMISSIONS:
        return ("rest_framework.permissions", name)
    perms = app_dir / "permissions.py"
    if perms.is_file() and class_exists(perms.read_text(encoding="utf-8"), name):
        return (f"apps.{app_name}.permissions", name)
    allowed = ", ".join(sorted(PERMISSIONS))
    raise ViewSetPermissionError(
        f"Unknown permission {name!r}. Allowed stock: {allowed}. "
        f"Or define {name} in apps.{app_name}.permissions "
        f"(django-octave add-permission {app_name} {name})."
    )


def _validate_names(
    names: list[str],
    available: set[str],
    *,
    label: str,
) -> list[str]:
    unknown = [n for n in names if n not in available]
    if unknown:
        valid = ", ".join(sorted(available))
        raise ViewSetFieldError(
            f"Unknown {label} field(s): {', '.join(unknown)}. Valid: {valid}"
        )
    return names


def resolve_viewset_lists(
    info: ModelFieldInfo,
    *,
    filters: list[str] | None,
    search: list[str] | None,
    ordering: list[str] | None,
) -> tuple[list[str], list[str], list[str]]:
    available = set(info.available_names)
    available.update(info.fields.keys())

    if filters is None:
        filter_fields = filterable_names(info)
    else:
        filter_fields = _validate_names(filters, available, label="filter")

    if search is None:
        search_fields = searchable_names(info)
    else:
        search_fields = _validate_names(search, available, label="search")

    if ordering is None:
        ordering_fields = default_ordering_names(info)
    else:
        ordering_fields = _validate_names(ordering, available, label="ordering")

    return filter_fields, search_fields, ordering_fields


def build_viewset_class(
    model_name: str,
    *,
    permission: str,
    filters: list[str],
    search: list[str],
    ordering: list[str],
    tag: str,
) -> str:
    filter_repr = "[" + ", ".join(f'"{n}"' for n in filters) + "]"
    search_repr = "[" + ", ".join(f'"{n}"' for n in search) + "]"
    ordering_repr = "[" + ", ".join(f'"{n}"' for n in ordering) + "]"
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
    permission_classes = [{permission}]
    filterset_fields = {filter_repr}
    search_fields = {search_repr}
    ordering_fields = {ordering_repr}
"""


def _views_header(
    app_name: str,
    model_name: str,
    *,
    permission: str,
    permission_module: str,
) -> str:
    if permission_module == "rest_framework.permissions":
        perm_import = f"from rest_framework.permissions import {permission}"
    else:
        perm_import = f"from {permission_module} import {permission}"
    return f'''"""API views for {app_name}."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
{perm_import}

from apps.{app_name}.models import {model_name}
from apps.{app_name}.serializers import {model_name}Serializer
'''


def _urls_header(app_name: str, model_name: str) -> str:
    from django_octave.naming import pluralize

    snake = pascal_to_snake(model_name)
    plural = pluralize(snake)
    return f'''"""URL routes for {app_name}."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.{app_name}.views import {model_name}ViewSet

router = DefaultRouter()
router.register("{plural}", {model_name}ViewSet, basename="{snake}")

urlpatterns = [
    path("", include(router.urls)),
]
'''


def _ensure_serializer(
    app_dir: Path,
    *,
    app_name: str,
    model_name: str,
    info: ModelFieldInfo,
) -> None:
    serializers = app_dir / "serializers.py"
    class_name = f"{model_name}Serializer"
    if serializers.exists() and class_exists(
        serializers.read_text(encoding="utf-8"), class_name
    ):
        return
    write_serializer(
        app_dir,
        options=SerializerOptions(
            app_name=app_name,
            model_name=model_name,
            force=False,
        ),
        info=info,
    )


def write_viewset(
    app_dir: Path,
    *,
    options: ViewSetOptions,
    info: ModelFieldInfo | None = None,
) -> tuple[Path, Path]:
    """Upsert viewset and ensure router registration.

    Returns ``(views.py path, urls.py path)``.
    """
    perm_module, permission = resolve_permission(
        app_dir, options.app_name, options.permission
    )
    models_path = app_dir / "models.py"
    if info is None:
        info = inspect_model_fields_path(models_path, options.model_name)

    filter_fields, search_fields, ordering_fields = resolve_viewset_lists(
        info,
        filters=options.filters,
        search=options.search,
        ordering=options.ordering,
    )
    tag = options.tag or pascal_to_snake(options.model_name)

    _ensure_serializer(
        app_dir,
        app_name=options.app_name,
        model_name=options.model_name,
        info=info,
    )

    class_name = f"{options.model_name}ViewSet"
    class_src = build_viewset_class(
        options.model_name,
        permission=permission,
        filters=filter_fields,
        search=search_fields,
        ordering=ordering_fields,
        tag=tag,
    )

    perm_import_line = f"from {perm_module} import {permission}\n"
    views_path = app_dir / "views.py"
    if not views_path.exists():
        views_path.write_text(
            _views_header(
                options.app_name,
                options.model_name,
                permission=permission,
                permission_module=perm_module,
            )
            + class_src,
            encoding="utf-8",
        )
    else:
        source = views_path.read_text(encoding="utf-8")
        exists = class_exists(source, class_name)
        if exists and not options.force:
            raise ViewSetExistsError(
                f"{class_name} already exists in {views_path}. Use --force to replace it."
            )

        source = add_to_import(source, f"apps.{options.app_name}.models", options.model_name)
        source = add_to_import(
            source,
            f"apps.{options.app_name}.serializers",
            f"{options.model_name}Serializer",
        )
        source = ensure_import_lines(
            source,
            [
                "from drf_spectacular.utils import extend_schema, extend_schema_view\n",
                "from rest_framework import viewsets\n",
                perm_import_line,
            ],
        )
        views_path.write_text(source, encoding="utf-8")
        upsert_class(
            views_path,
            class_name,
            class_src,
            force=exists and options.force,
            header_imports=[
                "from drf_spectacular.utils import extend_schema, extend_schema_view\n",
                "from rest_framework import viewsets\n",
                perm_import_line,
            ],
        )

    urls_path = app_dir / "urls.py"
    if not urls_path.exists():
        urls_path.write_text(
            _urls_header(options.app_name, options.model_name),
            encoding="utf-8",
        )
    else:
        ensure_router_registration(urls_path, options.app_name, options.model_name)

    return views_path, urls_path
