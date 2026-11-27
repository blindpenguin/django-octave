"""Detect django-octave-generated project roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.project.marker import Marker, check_compatible, read_marker


class NotOctaveProjectError(OctaveError, ValueError):
    """Raised when the path is not a compatible project."""


@dataclass(frozen=True, slots=True)
class OctaveProject:
    root: Path
    settings_base: Path
    urls: Path
    apps_dir: Path
    use_multitenancy: bool
    marker: Marker | None = None
    """Contents of ``.octave.toml``; ``None`` for a project generated without one."""


def _has_tenant_aware_model(models_path: Path) -> bool:
    if not models_path.is_file():
        return False
    text = models_path.read_text(encoding="utf-8")
    return "class TenantAwareModel" in text


def _has_tenant_middleware(middleware_path: Path) -> bool:
    """Legacy layout (before ``tenancy.py``): tenant bound in Django middleware."""
    if not middleware_path.is_file():
        return False
    text = middleware_path.read_text(encoding="utf-8")
    return "TenantMiddleware" in text


def detect_project(path: Path) -> OctaveProject:
    """Resolve and validate an octave-style project at ``path``."""
    root = path.expanduser().resolve()
    if not root.is_dir():
        msg = f"Project path does not exist: {root}"
        raise NotOctaveProjectError(msg)

    apps_dir = root / "apps"
    settings_base = root / "config" / "settings" / "base.py"
    urls = root / "config" / "urls.py"
    missing: list[str] = []
    if not (apps_dir.is_dir() and (apps_dir / "__init__.py").is_file()):
        missing.append("apps/ package")
    if not settings_base.is_file():
        missing.append("config/settings/base.py")
    else:
        settings_text = settings_base.read_text(encoding="utf-8")
        if "INSTALLED_APPS" not in settings_text:
            missing.append("INSTALLED_APPS in config/settings/base.py")
    if not urls.is_file():
        missing.append("config/urls.py")

    if missing:
        joined = ", ".join(missing)
        msg = f"{root} does not look like a django-octave project (missing: {joined})"
        raise NotOctaveProjectError(msg)

    core_models = apps_dir / "core" / "models.py"
    core_middleware = apps_dir / "core" / "middleware.py"
    use_mt = (
        _has_tenant_aware_model(core_models)
        or (apps_dir / "core" / "tenancy.py").is_file()
        or _has_tenant_middleware(core_middleware)
    )

    # Refuses (before any command writes a file) a project from a newer django-octave
    # or an unreadable marker. Projects without a marker are accepted as before, and
    # what is present (multitenancy above) is still read from the files, not the marker.
    marker = read_marker(root)
    if marker is not None:
        check_compatible(marker)

    return OctaveProject(
        root=root,
        settings_base=settings_base,
        urls=urls,
        apps_dir=apps_dir,
        use_multitenancy=use_mt,
        marker=marker,
    )
