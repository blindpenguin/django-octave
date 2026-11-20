"""Detect whether an octave project already has a frontend scaffold."""

from __future__ import annotations

from pathlib import Path


def frontend_configured(root: Path) -> bool:
    """Return True if ``frontend/package.json`` or a non-empty ``frontend/`` exists."""
    frontend = root / "frontend"
    if (frontend / "package.json").is_file():
        return True
    if frontend.is_dir() and any(frontend.iterdir()):
        return True
    return False


def project_slug(root: Path) -> str:
    """Best-effort project slug from ``pyproject.toml`` name or directory name."""
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("name"):
                if "=" in line:
                    raw = line.split("=", 1)[1].strip().strip("\"'")
                    if raw:
                        return raw
    return root.name


def project_display_name(root: Path) -> str:
    """Human-readable project title for SPA chrome (falls back to slug)."""
    readme = root / "README.md"
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                if title:
                    return title
    return project_slug(root)
