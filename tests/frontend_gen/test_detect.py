"""Unit tests for frontend detect + force/refuse scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.detect import frontend_configured, project_slug
from django_octave.frontend_gen.setup import FrontendExistsError, scaffold_frontend


def test_frontend_configured_false_on_empty(tmp_path: Path) -> None:
    assert not frontend_configured(tmp_path)
    (tmp_path / "frontend").mkdir()
    assert not frontend_configured(tmp_path)


def test_frontend_configured_package_json(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text("{}", encoding="utf-8")
    assert frontend_configured(tmp_path)


def test_frontend_configured_nonempty_dir(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "README").write_text("x", encoding="utf-8")
    assert frontend_configured(tmp_path)


def test_project_slug_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my_slug"\n',
        encoding="utf-8",
    )
    assert project_slug(tmp_path) == "my_slug"


def test_scaffold_refuses_without_force(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n',
        encoding="utf-8",
    )
    scaffold_frontend(tmp_path, include_register=False)
    assert (tmp_path / "frontend" / "package.json").is_file()
    with pytest.raises(FrontendExistsError):
        scaffold_frontend(tmp_path, include_register=False)


def test_scaffold_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n',
        encoding="utf-8",
    )
    scaffold_frontend(tmp_path, include_register=False)
    marker = tmp_path / "frontend" / "custom.txt"
    marker.write_text("keep-me-not", encoding="utf-8")
    scaffold_frontend(tmp_path, include_register=True, force=True)
    assert not marker.exists()
    assert (tmp_path / "frontend" / "src" / "pages" / "RegisterView.vue").is_file()
    assert "demo-frontend" in (
        tmp_path / "frontend" / "package.json"
    ).read_text(encoding="utf-8")
