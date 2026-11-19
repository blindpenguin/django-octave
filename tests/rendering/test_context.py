"""Tests for ProjectContext derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering import versions
from django_octave.rendering.context import ProjectContext, normalize_slug


def test_normalize_slug() -> None:
    assert normalize_slug("My API") == "my_api"
    assert normalize_slug("Hello-World") == "hello_world"
    with pytest.raises(ValueError):
        normalize_slug("***")


def test_context_sqlite_no_docker() -> None:
    options = NewProjectOptions(
        name="Demo",
        path=Path("/tmp"),
        database=DatabaseChoice.SQLITE,
        docker=False,
        multitenancy=False,
        force=False,
    )
    ctx = ProjectContext.from_options(options)
    assert ctx.project_slug == "demo"
    assert ctx.include_db_service is False
    assert versions.PSYCOPG not in ctx.packages
    assert "sqlite" in ctx.db_url_example


def test_context_postgres_docker() -> None:
    options = NewProjectOptions(
        name="Demo",
        path=Path("/tmp"),
        database=DatabaseChoice.POSTGRES,
        docker=True,
        multitenancy=True,
        force=False,
    )
    ctx = ProjectContext.from_options(options)
    assert ctx.include_db_service is True
    assert versions.PSYCOPG in ctx.packages
    assert ctx.use_multitenancy is True
