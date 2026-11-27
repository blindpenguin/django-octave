"""Wire Celery into an octave project."""

from __future__ import annotations

from pathlib import Path

from django_octave.celery_gen.compose import inject_compose_services
from django_octave.celery_gen.detect import celery_configured, project_slug
from django_octave.errors import OctaveError
from django_octave.project.marker import update_features
from django_octave.rendering.versions import CELERY

_SETTINGS_MARKER_BEGIN = "# --- django-octave celery begin ---"
_SETTINGS_MARKER_END = "# --- django-octave celery end ---"
_ENV_MARKER_BEGIN = "# --- django-octave celery begin ---"
_ENV_MARKER_END = "# --- django-octave celery end ---"


class CeleryExistsError(OctaveError, FileExistsError):
    """Raised when Celery is already configured without force."""


class CelerySetupError(OctaveError, ValueError):
    """Raised when Celery setup cannot complete safely."""


def build_celery_module(slug: str) -> str:
    return f'''"""Celery application for {slug}."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("{slug}")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks (extended by django-octave add-task).
app.conf.beat_schedule = {{}}
'''


def build_settings_block() -> str:
    return f"""
{_SETTINGS_MARKER_BEGIN}
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=env("REDIS_URL", default="redis://127.0.0.1:6379/0"),
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default=CELERY_BROKER_URL,
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
{_SETTINGS_MARKER_END}
"""


def build_env_block() -> str:
    return f"""
{_ENV_MARKER_BEGIN}
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
# Under Docker Compose, use redis://redis:6379/0 instead of 127.0.0.1
{_ENV_MARKER_END}
"""


def _ensure_config_init(init_path: Path) -> None:
    load = 'from .celery import app as celery_app\n\n__all__ = ("celery_app",)\n'
    if not init_path.exists() or not init_path.read_text(encoding="utf-8").strip():
        init_path.write_text(load, encoding="utf-8")
        return
    text = init_path.read_text(encoding="utf-8")
    if "celery_app" in text or "from .celery import" in text:
        return
    init_path.write_text(text.rstrip() + "\n\n" + load, encoding="utf-8")


def _patch_settings(settings_path: Path, *, force: bool) -> None:
    text = settings_path.read_text(encoding="utf-8")
    block = build_settings_block().strip("\n") + "\n"
    if _SETTINGS_MARKER_BEGIN in text:
        if not force:
            return
        start = text.index(_SETTINGS_MARKER_BEGIN)
        end = text.index(_SETTINGS_MARKER_END) + len(_SETTINGS_MARKER_END)
        # include trailing newline after end marker if present
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + block + text[end:]
    elif "CELERY_BROKER_URL" in text and not force:
        return
    else:
        text = text.rstrip() + "\n\n" + block
    settings_path.write_text(text, encoding="utf-8")


def _patch_env_example(env_path: Path, *, force: bool) -> None:
    if not env_path.exists():
        env_path.write_text(build_env_block().lstrip("\n"), encoding="utf-8")
        return
    text = env_path.read_text(encoding="utf-8")
    block = build_env_block().strip("\n") + "\n"
    if _ENV_MARKER_BEGIN in text:
        if not force:
            return
        start = text.index(_ENV_MARKER_BEGIN)
        end = text.index(_ENV_MARKER_END) + len(_ENV_MARKER_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + block + text[end:]
    elif "CELERY_BROKER_URL" in text and not force:
        return
    else:
        text = text.rstrip() + "\n" + block
    env_path.write_text(text, encoding="utf-8")


def _patch_pyproject(pyproject: Path) -> None:
    if not pyproject.is_file():
        raise CelerySetupError(f"pyproject.toml not found: {pyproject}")
    text = pyproject.read_text(encoding="utf-8")
    marker = "dependencies = ["
    if marker not in text:
        raise CelerySetupError("Could not find dependencies = [ in pyproject.toml")
    idx = text.index(marker) + len(marker)
    end = text.find("\n]", idx)
    if end < 0:
        raise CelerySetupError("Could not parse dependencies list in pyproject.toml")
    chunk = text[idx:end]
    if "celery" in chunk:
        return
    insert = f'\n    "{CELERY}",'
    text = text[:end] + insert + text[end:]
    pyproject.write_text(text, encoding="utf-8")


def setup_celery(root: Path, *, force: bool = False) -> list[Path]:
    """Configure Celery for ``root``. Returns paths written/updated."""
    root = root.resolve()
    if celery_configured(root) and not force:
        raise CeleryExistsError(
            "Celery already looks configured "
            "(config/celery.py or CELERY_BROKER_URL). Use --force to refresh."
        )

    config_dir = root / "config"
    if not config_dir.is_dir():
        raise CelerySetupError(f"config/ not found under {root}")

    written: list[Path] = []
    slug = project_slug(root)
    celery_path = config_dir / "celery.py"
    celery_path.write_text(build_celery_module(slug), encoding="utf-8")
    written.append(celery_path)

    init_path = config_dir / "__init__.py"
    _ensure_config_init(init_path)
    written.append(init_path)

    settings = config_dir / "settings" / "base.py"
    if not settings.is_file():
        raise CelerySetupError(f"Missing {settings}")
    _patch_settings(settings, force=force)
    written.append(settings)

    env_example = root / ".env.example"
    _patch_env_example(env_example, force=force)
    written.append(env_example)

    pyproject = root / "pyproject.toml"
    _patch_pyproject(pyproject)
    written.append(pyproject)

    compose = root / "docker-compose.yml"
    if compose.is_file():
        inject_compose_services(compose, force=force)
        written.append(compose)

    update_features(root, celery=True)
    return written
