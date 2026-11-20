"""Detect whether an octave project already has Celery wired."""

from __future__ import annotations

from pathlib import Path


def celery_configured(root: Path) -> bool:
    """Return True if ``config/celery.py`` exists or settings mention CELERY_BROKER_URL."""
    if (root / "config" / "celery.py").is_file():
        return True
    settings = root / "config" / "settings" / "base.py"
    if settings.is_file() and "CELERY_BROKER_URL" in settings.read_text(
        encoding="utf-8"
    ):
        return True
    return False


def project_slug(root: Path) -> str:
    """Best-effort project slug for Celery app name."""
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("name"):
                # name = "slug"
                if "=" in line:
                    raw = line.split("=", 1)[1].strip().strip("\"'")
                    if raw:
                        return raw
    return root.name
