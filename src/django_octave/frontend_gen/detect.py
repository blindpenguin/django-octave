"""Detect whether an octave project already has a frontend scaffold."""

from __future__ import annotations

from pathlib import Path

from django_octave.rendering.context import normalize_slug
from django_octave.safe_names import is_safe_project_name, is_safe_slug


def frontend_configured(root: Path) -> bool:
    """Return True if ``frontend/package.json`` or a non-empty ``frontend/`` exists."""
    frontend = root / "frontend"
    if (frontend / "package.json").is_file():
        return True
    if frontend.is_dir() and any(frontend.iterdir()):
        return True
    return False


def project_slug(root: Path) -> str:
    """Project slug from ``pyproject.toml`` ``name``, else from the directory name.

    The value is copied into generated files (for example ``package.json``), so a
    ``pyproject.toml`` name that is not a plain package-style identifier is ignored.
    """
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("name") and "=" in line:
                raw = line.split("=", 1)[1].strip().strip("\"'")
                if is_safe_slug(raw):
                    return raw
                break
    try:
        return normalize_slug(root.name)
    except ValueError:
        return "project"


def project_display_name(root: Path) -> str:
    """Human-readable project title for SPA chrome (falls back to the slug).

    The README title is used only when it is safe to copy into generated source;
    otherwise (quotes, braces, ...) the slug is used instead.
    """
    readme = root / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                if title and is_safe_project_name(title):
                    return title
                break
    return project_slug(root)
