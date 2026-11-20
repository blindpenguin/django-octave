"""Unit tests for CRUD generation orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.crud_setup import (
    CrudSetupError,
    generate_crud,
    generate_crud_all,
)
from django_octave.frontend_gen.setup import render_frontend


def _mini_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    app = root / "apps" / "recipes"
    app.mkdir(parents=True)
    (app / "models.py").write_text(
        "class Category(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
        "\n"
        "class Recipe(models.Model):\n"
        "    title = models.CharField(max_length=200)\n"
        "    category = models.ForeignKey('Category', on_delete=models.CASCADE)\n",
        encoding="utf-8",
    )
    (app / "views.py").write_text(
        "class CategoryViewSet(viewsets.ModelViewSet):\n"
        "    queryset = Category.objects.all()\n"
        "class RecipeViewSet(viewsets.ModelViewSet):\n"
        "    queryset = Recipe.objects.all()\n",
        encoding="utf-8",
    )
    (app / "urls.py").write_text(
        'router.register("categories", CategoryViewSet, basename="category")\n'
        'router.register("recipes", RecipeViewSet, basename="recipe")\n',
        encoding="utf-8",
    )
    render_frontend(
        root / "frontend",
        project_name="Proj",
        project_slug="proj",
        include_register=False,
    )
    return root


def test_generate_crud_recipe(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    written, warnings = generate_crud(root, "recipes", "Recipe")
    assert warnings == [] or isinstance(warnings, list)
    page_dir = root / "frontend" / "src" / "pages" / "recipes"
    assert (page_dir / "ListView.vue").is_file()
    assert (page_dir / "CreateView.vue").is_file()
    router = (root / "frontend" / "src" / "router" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert "path: 'recipes'" in router
    assert "recipes/ListView.vue" in router
    layout = (root / "frontend" / "src" / "layouts" / "AppLayout.vue").read_text(
        encoding="utf-8"
    )
    assert "{ label: 'Recipe', to: '/recipes' }," in layout
    assert any(p.name == "ListView.vue" for p in written)

    with pytest.raises(FileExistsError):
        generate_crud(root, "recipes", "Recipe")

    generate_crud(root, "recipes", "Recipe", force=True)


def test_generate_crud_all(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    written, _warnings, skips = generate_crud_all(root)
    assert skips == []
    assert (root / "frontend" / "src" / "pages" / "recipes" / "ListView.vue").is_file()
    assert (
        root / "frontend" / "src" / "pages" / "categories" / "ListView.vue"
    ).is_file()
    router = (root / "frontend" / "src" / "router" / "index.ts").read_text(
        encoding="utf-8"
    )
    assert "path: 'recipes'" in router
    assert "path: 'categories'" in router
    assert written

    _w2, _warn2, skips2 = generate_crud_all(root)
    assert any("use --force" in s for s in skips2)


def test_generate_crud_requires_frontend(tmp_path: Path) -> None:
    root = tmp_path / "bare"
    root.mkdir()
    (root / "apps").mkdir()
    with pytest.raises(CrudSetupError, match="add-frontend"):
        generate_crud(root, "recipes", "Recipe")
