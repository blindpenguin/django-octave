"""Tests for project rendering matrices."""

from __future__ import annotations

import ast
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
        frontend=False,
        register=False,
        crud=False,
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
    assert not (target / "apps" / "core" / "tenancy.py").exists()
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg" not in pyproject
    assert "AUTH_USER_MODEL" in (target / "config" / "settings" / "base.py").read_text(
        encoding="utf-8"
    )
    # WhiteNoise STATIC_ROOT present for a quiet first run.
    assert (target / "staticfiles" / ".gitkeep").is_file()
    gitignore = (target / ".gitignore").read_text(encoding="utf-8")
    assert "staticfiles/*" in gitignore
    assert "!staticfiles/.gitkeep" in gitignore
    local = (target / "config" / "settings" / "local.py").read_text(encoding="utf-8")
    assert "WHITENOISE_USE_FINDERS" in local
    assert "StaticFilesStorage" in local


def test_render_docker_and_multitenancy(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(
        _options(tmp_path, database=DatabaseChoice.POSTGRES, docker=True, multitenancy=True)
    )
    target = render_project(ctx)
    assert (target / "Dockerfile").is_file()
    assert (target / "docker-compose.yml").is_file()
    assert (target / "apps" / "core" / "tenancy.py").is_file()
    assert not (target / "apps" / "core" / "middleware.py").exists()
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


def test_render_docker_hardening(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(
        _options(tmp_path, database=DatabaseChoice.POSTGRES, docker=True)
    )

    target = render_project(ctx)

    dockerfile = (target / "Dockerfile").read_text(encoding="utf-8")
    assert "USER app" in dockerfile
    assert "uv:latest" not in dockerfile
    assert ".env" in (target / ".dockerignore").read_text(encoding="utf-8").splitlines()
    prod = (target / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in prod
    dev = (target / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:5432:5432"' in dev


def test_render_without_docker_skips_dockerignore(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, docker=False))

    target = render_project(ctx)

    assert not (target / ".dockerignore").exists()


def test_render_prod_settings_reject_placeholder_secret(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path))

    target = render_project(ctx)

    prod = (target / "config" / "settings" / "prod.py").read_text(encoding="utf-8")
    assert "ImproperlyConfigured" in prod
    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert "DEFAULT_THROTTLE_RATES" in base


def test_render_multitenancy_binds_tenant_in_drf_not_middleware(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, multitenancy=True))
    target = render_project(ctx)
    settings = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    tenancy = (target / "apps" / "core" / "tenancy.py").read_text(encoding="utf-8")
    assert "Tenant" not in settings.split("MIDDLEWARE", 1)[1].split("]", 1)[0]
    assert "class TenantScopedMixin" in tenancy
    assert "class TenantRequired" in tenancy
    models = (target / "apps" / "core" / "models.py").read_text(encoding="utf-8")
    assert "PermissionDenied" in models  # foreign-tenant save guard


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_all_python_files_parse(tmp_path: Path, multitenancy: bool) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, multitenancy=multitenancy))
    target = render_project(ctx)
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
