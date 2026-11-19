"""Tests for project rendering matrices."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import TargetExistsError, render_project


def _options(
    tmp_path: Path,
    *,
    database: DatabaseChoice = DatabaseChoice.SQLITE,
    docker: bool = False,
    multitenancy: bool = False,
    force: bool = False,
    name: str = "Sample",
) -> NewProjectOptions:
    return NewProjectOptions(
        name=name,
        path=tmp_path,
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        force=force,
    )


def test_render_sqlite_baseline(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path))
    target = render_project(ctx)
    assert (target / "manage.py").is_file()
    assert (target / "apps" / "users" / "models.py").is_file()
    assert (target / "apps" / "users" / "migrations" / "0001_initial.py").is_file()
    assert not (target / "Dockerfile").exists()
    assert not (target / "apps" / "core" / "middleware.py").exists()
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg" not in pyproject
    assert "AUTH_USER_MODEL" in (target / "config" / "settings" / "base.py").read_text(
        encoding="utf-8"
    )


def test_render_docker_and_multitenancy(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(
        _options(tmp_path, database=DatabaseChoice.POSTGRES, docker=True, multitenancy=True)
    )
    target = render_project(ctx)
    assert (target / "Dockerfile").is_file()
    assert (target / "docker-compose.yml").is_file()
    assert (target / "apps" / "core" / "middleware.py").is_file()
    assert (target / "apps" / "core" / "migrations" / "0001_initial.py").is_file()
    models = (target / "apps" / "core" / "models.py").read_text(encoding="utf-8")
    assert "class Tenant" in models
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg" in pyproject


def test_refuse_non_empty_without_force(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, name="Clash"))
    render_project(ctx)
    with pytest.raises(TargetExistsError):
        render_project(ctx)
