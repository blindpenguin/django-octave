"""Unit tests for celery_gen setup writers."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.celery_gen.detect import celery_configured
from django_octave.celery_gen.setup import (
    CeleryExistsError,
    build_celery_module,
    build_env_block,
    build_settings_block,
    setup_celery,
)
from django_octave.cli import app

runner = CliRunner()


def _new_project(tmp_path: Path, *, docker: bool = False) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--docker" if docker else "--no-docker",
        "--no-multitenancy",
        "--no-frontend",
        "--path",
        str(tmp_path),
    ]
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path / "proj"


def test_build_snippets() -> None:
    mod = build_celery_module("myproj")
    assert 'Celery("myproj")' in mod
    assert "beat_schedule" in mod
    assert "CELERY_BROKER_URL" in build_settings_block()
    assert "REDIS_URL=" in build_env_block()


def test_setup_celery_writes_and_refuses(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    assert not celery_configured(root)
    written = setup_celery(root)
    assert (root / "config" / "celery.py").is_file()
    assert "celery_app" in (root / "config" / "__init__.py").read_text(encoding="utf-8")
    settings = (root / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert "CELERY_BROKER_URL" in settings
    env = (root / ".env.example").read_text(encoding="utf-8")
    assert "CELERY_BROKER_URL=" in env
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "celery[redis]" in pyproject
    assert any(p.name == "celery.py" for p in written)
    assert celery_configured(root)

    with pytest.raises(CeleryExistsError):
        setup_celery(root)

    setup_celery(root, force=True)
    assert "CELERY_TASK_TRACK_STARTED" in (
        root / "config" / "settings" / "base.py"
    ).read_text(encoding="utf-8")


def test_setup_celery_with_compose(tmp_path: Path) -> None:
    root = _new_project(tmp_path, docker=True)
    setup_celery(root)
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "django-octave celery begin" in compose
    assert "  redis:" in compose
    assert "  worker:" in compose
    assert "  beat:" in compose
