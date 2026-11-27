"""Integration coverage for generator-polish fixes."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _new(tmp_path: Path) -> Path:
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
    return tmp_path / "proj"


def test_add_basename_and_add_test_reverse(tmp_path: Path) -> None:
    root = _new(tmp_path)
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    urls = (root / "apps" / "blog" / "urls.py").read_text(encoding="utf-8")
    assert 'basename="blog"' in urls  # model Blog → snake blog
    result = runner.invoke(app, ["add-test", "blog", "Blog", "--path", str(root)])
    assert result.exit_code == 0, result.output
    test_src = (root / "tests" / "test_blog_blog_api.py").read_text(encoding="utf-8")
    assert 'reverse("blog-list")' in test_src


def test_cross_app_factory_and_allow_any(tmp_path: Path) -> None:
    root = _new(tmp_path)
    assert (
        runner.invoke(app, ["add", "ingredients", "--path", str(root)]).exit_code == 0
    )
    assert runner.invoke(app, ["add", "recipes", "--path", str(root)]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "add-model",
                "ingredients",
                "Ingredient",
                "--fields",
                "name:char:max=80",
                "--force",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "add-model",
                "recipes",
                "Recipe",
                "--fields",
                "title:char:max=100,ingredient:fk:to=ingredients.Ingredient",
                "--force",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "add-viewset",
                "recipes",
                "Recipe",
                "--permission",
                "AllowAny",
                "--force",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    # Sync may rewrite basename on urls
    urls = (root / "apps" / "recipes" / "urls.py").read_text(encoding="utf-8")
    assert 'basename="recipe"' in urls

    assert (
        runner.invoke(
            app,
            ["add-test", "recipes", "Recipe", "--force", "--path", str(root)],
        ).exit_code
        == 0
    )
    factory = (root / "tests" / "factories" / "recipes_recipe.py").read_text(
        encoding="utf-8"
    )
    assert "ingredients_ingredient.IngredientFactory" in factory
    api = (root / "tests" / "test_recipes_recipe_api.py").read_text(encoding="utf-8")
    assert "test_list_anonymous_ok" in api
