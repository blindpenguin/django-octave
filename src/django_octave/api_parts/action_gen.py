"""Generate DRF ``@action`` methods on existing viewsets."""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from pathlib import Path

from django_octave.api_parts.permission_gen import resolve_viewset_class_name
from django_octave.api_parts.viewset_gen import resolve_permission
from django_octave.errors import OctaveError
from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    coalesce_from_imports,
    method_exists,
    upsert_method,
)
from django_octave.models_gen.writer import ModelWriteError
from django_octave.naming import pascal_to_snake, pluralize
from django_octave.safe_names import (
    is_safe_tag,
    validate_tag,
    validate_url_name,
    validate_url_path,
)

HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options"}
)

_ACTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_TAG_RE = re.compile(r'tags\s*=\s*\[\s*["\']([^"\']+)["\']')


class ActionExistsError(OctaveError, FileExistsError):
    """Raised when the action method already exists without force."""


class ActionNameError(OctaveError, ValueError):
    """Raised for invalid action method names."""


class ActionMethodError(OctaveError, ValueError):
    """Raised for invalid HTTP methods."""


class ActionTargetError(OctaveError, ValueError):
    """Raised when the viewset or serializer target is missing."""


@dataclass
class ActionOptions:
    app_name: str
    viewset: str
    action_name: str
    detail: bool = True
    methods: list[str] | None = None
    url_path: str | None = None
    url_name: str | None = None
    permission: str | None = None
    serializer: str | None = None
    tag: str | None = None
    force: bool = False


def validate_action_name(raw: str) -> str:
    name = raw.strip()
    if not _ACTION_NAME_RE.match(name) or keyword.iskeyword(name):
        raise ActionNameError(
            f"Invalid action name {raw!r}: must be a snake_case Python identifier "
            "starting with a letter"
        )
    return name


def parse_http_methods(raw: str | None, *, detail: bool) -> list[str]:
    """Parse comma-separated HTTP methods or return detail/list defaults."""
    if raw is None or not str(raw).strip():
        return ["post"] if detail else ["get"]
    methods = [m.strip().lower() for m in str(raw).split(",") if m.strip()]
    return normalize_methods(methods, detail=detail)


def normalize_methods(methods: list[str] | None, *, detail: bool) -> list[str]:
    if not methods:
        return ["post"] if detail else ["get"]
    cleaned = [m.strip().lower() for m in methods if m.strip()]
    if not cleaned:
        raise ActionMethodError("At least one HTTP method is required")
    unknown = [m for m in cleaned if m not in HTTP_METHODS]
    if unknown:
        allowed = ", ".join(sorted(HTTP_METHODS))
        raise ActionMethodError(
            f"Unknown HTTP method(s): {', '.join(unknown)}. Allowed: {allowed}"
        )
    return cleaned


def detect_viewset_tag(source: str, class_name: str) -> str | None:
    """Return Spectacular tag from the target viewset's own decorators.

    Only searches between the previous top-level ``class`` and this class
    line, using the **last** ``tags=[...]`` match (typically the viewset's
    ``@extend_schema_view``), so earlier viewsets in the file cannot win.
    """
    idx = source.find(f"class {class_name}")
    if idx < 0:
        return None
    prev = source.rfind("\nclass ", 0, idx)
    window = source[0 if prev < 0 else prev : idx]
    matches = list(_TAG_RE.finditer(window))
    return matches[-1].group(1) if matches else None


def default_tag_for_viewset(viewset_class: str) -> str:
    stem = viewset_class.removesuffix("ViewSet") or viewset_class
    return pascal_to_snake(stem)


def _action_decorator_kwargs(
    *,
    detail: bool,
    methods: list[str],
    url_path: str | None,
    url_name: str | None,
    permission: str | None,
    serializer: str | None,
) -> str:
    parts = [
        f"detail={detail!r}",
        "methods=[" + ", ".join(f'"{m}"' for m in methods) + "]",
    ]
    if url_path:
        parts.append(f'url_path="{url_path}"')
    if url_name:
        parts.append(f'url_name="{url_name}"')
    if permission:
        parts.append(f"permission_classes=[{permission}]")
    if serializer:
        parts.append(f"serializer_class={serializer}")
    return ", ".join(parts)


def build_action_method(
    action_name: str,
    *,
    detail: bool,
    methods: list[str],
    tag: str,
    url_path: str | None = None,
    url_name: str | None = None,
    permission: str | None = None,
    serializer: str | None = None,
) -> str:
    kwargs = _action_decorator_kwargs(
        detail=detail,
        methods=methods,
        url_path=url_path,
        url_name=url_name,
        permission=permission,
        serializer=serializer,
    )
    if detail:
        return f'''
@extend_schema(tags=["{tag}"])
@action({kwargs})
def {action_name}(self, request, pk=None):
    obj = self.get_object()
    # TODO: implement domain logic for {action_name}
    return Response({{"id": getattr(obj, "pk", None), "status": "ok"}})
'''
    return f'''
@extend_schema(tags=["{tag}"])
@action({kwargs})
def {action_name}(self, request):
    qs = self.filter_queryset(self.get_queryset())
    # TODO: implement domain logic for {action_name}
    page = self.paginate_queryset(qs)
    if page is not None:
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    serializer = self.get_serializer(qs, many=True)
    return Response(serializer.data)
'''


def _import_has_symbol(source: str, module: str, symbol: str) -> bool:
    prefix = f"from {module} import "
    for line in source.splitlines():
        if not line.startswith(prefix):
            continue
        names = [p.strip() for p in line[len(prefix) :].split(",")]
        if symbol in names:
            return True
    return False


def _prepare_action_imports(views_path: Path, source: str) -> list[str]:
    """Ensure spectacular extend_schema is importable; return remaining headers."""
    header_imports = [
        "from rest_framework.decorators import action\n",
        "from rest_framework.response import Response\n",
    ]
    if _import_has_symbol(source, "drf_spectacular.utils", "extend_schema"):
        return header_imports
    if _import_has_symbol(source, "drf_spectacular.utils", "extend_schema_view"):
        updated = source.replace(
            "from drf_spectacular.utils import extend_schema_view",
            "from drf_spectacular.utils import extend_schema, extend_schema_view",
            1,
        )
        views_path.write_text(updated, encoding="utf-8")
        return header_imports
    header_imports.append("from drf_spectacular.utils import extend_schema\n")
    return header_imports


def write_action(
    app_dir: Path,
    *,
    options: ActionOptions,
) -> Path:
    """Inject an ``@action`` method into ``app_dir/views.py``."""
    views_path = app_dir / "views.py"
    if not views_path.is_file():
        raise ActionTargetError(
            f"views.py not found in {app_dir}. "
            f"Run: django-octave add-viewset {options.app_name} …"
        )

    # Free text that ends up in generated code: validate before anything is written.
    if options.tag is not None:
        validate_tag(options.tag)
    if options.url_path is not None:
        validate_url_path(options.url_path)
    if options.url_name is not None:
        validate_url_name(options.url_name)

    viewset_class = resolve_viewset_class_name(options.viewset)
    action_name = validate_action_name(options.action_name)
    methods = normalize_methods(options.methods, detail=options.detail)

    source = views_path.read_text(encoding="utf-8")
    if not class_exists(source, viewset_class):
        raise ActionTargetError(
            f"{viewset_class} not found in {views_path}. "
            f"Run: django-octave add-viewset {options.app_name} …"
        )
    if method_exists(source, viewset_class, action_name) and not options.force:
        raise ActionExistsError(
            f"{action_name} already exists on {viewset_class}. Use --force to replace it."
        )

    permission_symbol: str | None = None
    permission_module: str | None = None
    if options.permission:
        permission_module, permission_symbol = resolve_permission(
            app_dir, options.app_name, options.permission
        )

    serializer_name: str | None = None
    if options.serializer:
        serializer_name = options.serializer.strip()
        ser_path = app_dir / "serializers.py"
        if not ser_path.is_file() or not class_exists(
            ser_path.read_text(encoding="utf-8"), serializer_name
        ):
            raise ActionTargetError(
                f"Serializer {serializer_name} not found in "
                f"apps.{options.app_name}.serializers. "
                f"Run: django-octave add-serializer {options.app_name} …"
            )

    # A tag read from the existing viewset is untrusted text too: use it only if it is safe.
    detected = detect_viewset_tag(source, viewset_class)
    tag = (
        options.tag
        or (detected if detected and is_safe_tag(detected) else None)
        or default_tag_for_viewset(viewset_class)
    )

    method_src = build_action_method(
        action_name,
        detail=options.detail,
        methods=methods,
        tag=tag,
        url_path=options.url_path,
        url_name=options.url_name,
        permission=permission_symbol,
        serializer=serializer_name,
    )

    header_imports = _prepare_action_imports(views_path, source)

    if permission_module and permission_symbol:
        source = views_path.read_text(encoding="utf-8")
        source = add_to_import(source, permission_module, permission_symbol)
        views_path.write_text(source, encoding="utf-8")
    if serializer_name:
        source = views_path.read_text(encoding="utf-8")
        source = add_to_import(
            source, f"apps.{options.app_name}.serializers", serializer_name
        )
        views_path.write_text(source, encoding="utf-8")

    try:
        upsert_method(
            views_path,
            viewset_class,
            action_name,
            method_src,
            force=options.force,
            header_imports=header_imports,
        )
    except ModelWriteError:
        raise

    cleaned = coalesce_from_imports(views_path.read_text(encoding="utf-8"))
    views_path.write_text(cleaned, encoding="utf-8")
    return views_path


def action_url_hint(
    *,
    app_name: str,
    viewset_class: str,
    action_name: str,
    detail: bool,
    url_path: str | None,
) -> str:
    """Human-readable route shape for success output."""
    stem = viewset_class.removesuffix("ViewSet") or viewset_class
    snake = pascal_to_snake(stem)
    plural = pluralize(snake)
    segment = url_path or action_name
    if detail:
        return f"/api/{plural}/{{pk}}/{segment}/"
    return f"/api/{plural}/{segment}/"
