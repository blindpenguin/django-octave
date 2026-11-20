"""CLI tests for django-octave add-frontend-crud and --crud bulk."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_recipe(tmp_path: Path) -> Path:
    assert (
        runner.invoke(
            app,
            [
                "new",
                "proj",
                "-d",
                "sqlite",
                "--no-docker",
                "--no-multitenancy",
                "--no-frontend",
                "--path",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    root = tmp_path / "proj"
    assert (
        runner.invoke(
            app,
            ["add", "recipes", "--path", str(root), "--model", "Recipe"],
        ).exit_code
        == 0
    )
    (root / "apps" / "recipes" / "models.py").write_text(
        '"""Domain models for recipes."""\n\n'
        "from __future__ import annotations\n\n"
        "from django.db import models\n\n"
        "from apps.core.models import TimeStampedModel\n\n\n"
        "class Category(TimeStampedModel):\n"
        "    name = models.CharField(max_length=100)\n\n"
        "    class Meta:\n"
        '        ordering = ("name",)\n\n'
        "    def __str__(self) -> str:\n"
        "        return self.name\n\n\n"
        "class Recipe(TimeStampedModel):\n"
        "    title = models.CharField(max_length=200)\n"
        "    category = models.ForeignKey(\n"
        "        Category, on_delete=models.CASCADE, related_name='recipes'\n"
        "    )\n\n"
        "    class Meta:\n"
        '        ordering = ("title",)\n\n'
        "    def __str__(self) -> str:\n"
        "        return self.title\n",
        encoding="utf-8",
    )
    for model in ("Category", "Recipe"):
        result = runner.invoke(
            app,
            [
                "add-viewset",
                "recipes",
                model,
                "--force",
                "--path",
                str(root),
            ],
        )
        assert result.exit_code == 0, result.output
    fe = runner.invoke(
        app,
        [
            "add-frontend",
            "--no-register",
            "--no-crud",
            "--path",
            str(root),
        ],
    )
    assert fe.exit_code == 0, fe.output
    return root


def test_help_lists_add_frontend_crud() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "add-frontend-crud" in result.stdout


def test_add_frontend_crud_help() -> None:
    result = runner.invoke(app, ["add-frontend-crud", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout
    assert "--fk-label" in result.stdout


def test_add_frontend_crud_generate_refuse_force(tmp_path: Path) -> None:
    root = _project_with_recipe(tmp_path)
    result = runner.invoke(
        app,
        ["add-frontend-crud", "recipes", "Recipe", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    page_dir = root / "frontend" / "src" / "pages" / "recipes"
    assert (page_dir / "ListView.vue").is_file()
    create = (page_dir / "CreateView.vue").read_text(encoding="utf-8")
    assert "/api/categories/" in create
    assert "USelect" in create or "select" in create.lower()

    refused = runner.invoke(
        app,
        ["add-frontend-crud", "recipes", "Recipe", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        [
            "add-frontend-crud",
            "recipes",
            "Recipe",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert forced.exit_code == 0, forced.output


def test_add_frontend_crud_missing_frontend(tmp_path: Path) -> None:
    assert (
        runner.invoke(
            app,
            [
                "new",
                "bare",
                "-d",
                "sqlite",
                "--no-docker",
                "--no-multitenancy",
                "--no-frontend",
                "--path",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    root = tmp_path / "bare"
    result = runner.invoke(
        app,
        ["add-frontend-crud", "recipes", "Recipe", "--path", str(root)],
    )
    assert result.exit_code == 1
    assert "frontend" in result.output.lower()


def test_add_frontend_crud_missing_viewset(tmp_path: Path) -> None:
    assert (
        runner.invoke(
            app,
            [
                "new",
                "proj",
                "-d",
                "sqlite",
                "--no-docker",
                "--no-multitenancy",
                "--no-frontend",
                "--path",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    root = tmp_path / "proj"
    assert (
        runner.invoke(
            app,
            [
                "add-frontend",
                "--no-register",
                "--no-crud",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    result = runner.invoke(
        app,
        ["add-frontend-crud", "recipes", "Recipe", "--path", str(root)],
    )
    assert result.exit_code == 1


def test_add_frontend_bulk_crud(tmp_path: Path) -> None:
    root = _project_with_recipe(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-frontend",
            "--no-register",
            "--crud",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (root / "frontend" / "src" / "pages" / "recipes" / "ListView.vue").is_file()
    assert (
        root / "frontend" / "src" / "pages" / "categories" / "ListView.vue"
    ).is_file()
    router = (root / "frontend" / "src" / "router" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert "recipes-list" in router
    assert "categories-list" in router
