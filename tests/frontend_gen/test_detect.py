"""Unit tests for frontend detect + force/refuse scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from django_octave.frontend_gen.detect import (
    frontend_configured,
    project_display_name,
    project_slug,
)
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


def _write_readme(root: Path, title_line: str) -> None:
    (root / "README.md").write_text(f"{title_line}\n\nText.\n", encoding="utf-8")


def test_display_name_uses_a_safe_readme_title(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    _write_readme(tmp_path, "# My Shop 2.0")

    assert project_display_name(tmp_path) == "My Shop 2.0"


@pytest.mark.parametrize(
    "title",
    ['My "Shop"', "Bob's Shop", "{{ 1 + 1 }}", "<b>Shop</b>", 'a" + __import__("os") + "b', "x" * 65],
)
def test_display_name_falls_back_to_the_slug_for_an_unsafe_readme_title(
    tmp_path: Path, title: str
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    _write_readme(tmp_path, f"# {title}")

    assert project_display_name(tmp_path) == "demo"


def test_display_name_without_readme_is_the_slug(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")

    assert project_display_name(tmp_path) == "demo"


def test_slug_ignores_an_unsafe_pyproject_name_and_uses_the_directory(tmp_path: Path) -> None:
    root = tmp_path / "My Project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "a\\"b"\n', encoding="utf-8"
    )  # name = "a\"b"

    assert project_slug(root) == "my_project"


def test_slug_falls_back_when_the_directory_has_no_usable_characters(tmp_path: Path) -> None:
    root = tmp_path / "日本語"
    root.mkdir()

    assert project_slug(root) == "project"


def test_scaffold_with_a_hostile_readme_title_produces_valid_json(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    _write_readme(tmp_path, '# Bad", "x": "y')

    scaffold_frontend(tmp_path, include_register=False)

    package = json.loads((tmp_path / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "demo-frontend"
    index = (tmp_path / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "<title>demo</title>" in index


def test_scaffold_with_a_hostile_pyproject_name_produces_valid_json(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "x\\", \\"evil\\": \\"1"\n', encoding="utf-8")

    scaffold_frontend(root, include_register=False)

    package = json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "proj-frontend"
    assert "evil" not in package
