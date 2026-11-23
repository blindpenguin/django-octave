"""Generate DRF permission classes and optionally wire them to viewsets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    ensure_import_lines,
    upsert_class,
)

PRESETS: frozenset[str] = frozenset(
    {"owner", "staff_or_read", "auth_or_read", "tenant_member"}
)


class PermissionExistsError(FileExistsError):
    """Raised when the permission class already exists without force."""


class PermissionPresetError(ValueError):
    """Raised for unknown or unavailable presets."""


class PermissionWireError(ValueError):
    """Raised when viewset wiring fails."""


@dataclass
class PermissionOptions:
    app_name: str
    class_name: str
    preset: str = "owner"
    owner_attr: str = "owner"
    viewset: str | None = None
    append: bool = False
    force: bool = False


def validate_preset(preset: str, *, use_multitenancy: bool) -> str:
    name = preset.strip().lower()
    if name not in PRESETS:
        allowed = ", ".join(sorted(PRESETS))
        raise PermissionPresetError(f"Unknown preset {preset!r}. Allowed: {allowed}")
    if name == "tenant_member" and not use_multitenancy:
        raise PermissionPresetError(
            "Preset tenant_member requires a multitenancy project "
            "(create with --multitenancy)."
        )
    return name


def _imports_for_preset(preset: str) -> list[str]:
    if preset in {"staff_or_read", "auth_or_read"}:
        return [
            "from rest_framework.permissions import SAFE_METHODS, BasePermission\n",
        ]
    return ["from rest_framework.permissions import BasePermission\n"]


def build_permission_class(
    class_name: str,
    *,
    preset: str,
    owner_attr: str = "owner",
) -> str:
    """Return class source for the given preset."""
    if preset == "owner":
        return f'''
class {class_name}(BasePermission):
    """Allow access only to the object's owner ({owner_attr})."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        owner = getattr(obj, "{owner_attr}", None)
        if owner is None:
            return False
        return owner == request.user
'''
    if preset == "staff_or_read":
        return f'''
class {class_name}(BasePermission):
    """Allow read to anyone; write requires staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
'''
    if preset == "auth_or_read":
        return f'''
class {class_name}(BasePermission):
    """Allow read to anyone; write requires authentication."""

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
'''
    if preset == "tenant_member":
        return f'''
class {class_name}(BasePermission):
    """Require an authenticated user with a tenant bound by TenantScopedMixin.

    The viewset must inherit ``TenantScopedMixin``; without it ``request.tenant``
    is never set and every request is denied.
    """

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return getattr(request, "tenant", None) is not None
'''
    raise PermissionPresetError(f"Unknown preset {preset!r}")


def _permissions_header(app_name: str, preset: str) -> str:
    imports = "".join(_imports_for_preset(preset))
    return f'''"""Permissions for {app_name}."""

from __future__ import annotations

{imports}'''


def write_permission(
    app_dir: Path,
    *,
    options: PermissionOptions,
) -> Path:
    """Upsert permission class into ``app_dir/permissions.py``."""
    path = app_dir / "permissions.py"
    class_src = build_permission_class(
        options.class_name,
        preset=options.preset,
        owner_attr=options.owner_attr,
    )
    header_imports = _imports_for_preset(options.preset)

    if not path.exists():
        path.write_text(
            _permissions_header(options.app_name, options.preset) + class_src,
            encoding="utf-8",
        )
        return path

    source = path.read_text(encoding="utf-8")
    exists = class_exists(source, options.class_name)
    if exists and not options.force:
        raise PermissionExistsError(
            f"{options.class_name} already exists in {path}. Use --force to replace it."
        )

    # Ensure SAFE_METHODS is available when needed (may already have BasePermission only)
    if options.preset in {"staff_or_read", "auth_or_read"} and "SAFE_METHODS" not in source:
        if "from rest_framework.permissions import BasePermission" in source:
            source = source.replace(
                "from rest_framework.permissions import BasePermission",
                "from rest_framework.permissions import SAFE_METHODS, BasePermission",
                1,
            )
            path.write_text(source, encoding="utf-8")
        else:
            path.write_text(
                ensure_import_lines(source, header_imports),
                encoding="utf-8",
            )

    upsert_class(
        path,
        options.class_name,
        class_src,
        force=exists and options.force,
        header_imports=header_imports,
    )
    return path


def viewset_has_tenant_mixin(views_path: Path, viewset_class: str) -> bool:
    """True if ``viewset_class`` lists ``TenantScopedMixin`` among its bases."""
    match = re.search(
        rf"class\s+{re.escape(viewset_class)}\s*\(([^)]*)\)",
        views_path.read_text(encoding="utf-8"),
    )
    return bool(match and "TenantScopedMixin" in match.group(1))


def resolve_viewset_class_name(raw: str) -> str:
    name = raw.strip()
    if name.endswith("ViewSet"):
        return name
    return f"{name}ViewSet"


def wire_permission_to_viewset(
    views_path: Path,
    *,
    app_name: str,
    viewset_class: str,
    permission_class: str,
    append: bool,
) -> None:
    """Set or append ``permission_classes`` on ``viewset_class``."""
    if not views_path.is_file():
        raise PermissionWireError(f"views.py not found: {views_path}")
    source = views_path.read_text(encoding="utf-8")
    if not class_exists(source, viewset_class):
        raise PermissionWireError(
            f"{viewset_class} not found in {views_path}. "
            f"Run: django-octave add-viewset {app_name} …"
        )

    source = add_to_import(
        source, f"apps.{app_name}.permissions", permission_class
    )
    views_path.write_text(source, encoding="utf-8")
    source = views_path.read_text(encoding="utf-8")

    class_idx = source.find(f"class {viewset_class}")
    if class_idx < 0:
        raise PermissionWireError(f"{viewset_class} not found")
    next_idx = source.find("\nclass ", class_idx + 1)
    chunk = source[class_idx:] if next_idx < 0 else source[class_idx:next_idx]
    match = re.search(r"permission_classes\s*=\s*\[([^\]]*)\]", chunk)
    if match:
        existing = [p.strip() for p in match.group(1).split(",") if p.strip()]
        if append:
            final = list(existing)
            if permission_class not in final:
                final.append(permission_class)
        else:
            final = [permission_class]
        new_assign = f"permission_classes = [{', '.join(final)}]"
        new_chunk = chunk[: match.start()] + new_assign + chunk[match.end() :]
    else:
        ser = re.search(r"serializer_class\s*=\s*[^\n]+", chunk)
        line = f"    permission_classes = [{permission_class}]\n"
        if ser:
            insert_at = ser.end()
            new_chunk = chunk[:insert_at] + "\n" + line + chunk[insert_at:]
        else:
            nl = chunk.find("\n")
            new_chunk = chunk[: nl + 1] + line + chunk[nl + 1 :]

    if next_idx < 0:
        source = source[:class_idx] + new_chunk
    else:
        source = source[:class_idx] + new_chunk + source[next_idx:]
    views_path.write_text(source, encoding="utf-8")
