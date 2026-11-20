"""Unit tests for CRUD page rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.crud_fields import enrich_resource
from django_octave.frontend_gen.crud_pages import render_crud_pages
from django_octave.frontend_gen.crud_types import ResourceSpec
from django_octave.frontend_gen.setup import render_frontend


def _mini_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    app = root / "apps" / "recipes"
    app.mkdir(parents=True)
    (app / "models.py").write_text(
        "class Recipe(models.Model):\n"
        "    title = models.CharField(max_length=200)\n"
        "    category = models.ForeignKey('Category', on_delete=models.CASCADE)\n"
        "\n"
        "class Category(models.Model):\n"
        "    name = models.CharField(max_length=100)\n",
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
    frontend = root / "frontend"
    render_frontend(
        frontend,
        project_name="Proj",
        project_slug="proj",
        include_register=False,
    )
    return root


def test_render_crud_pages(tmp_path: Path) -> None:
    root = _mini_project(tmp_path)
    spec = ResourceSpec(
        app_name="recipes",
        model_name="Recipe",
        model_snake="recipe",
        model_plural="recipes",
        api_collection="/api/recipes/",
        viewset_name="RecipeViewSet",
    )
    enriched, _ = enrich_resource(root, spec)
    written = render_crud_pages(root / "frontend", enriched)
    page_dir = root / "frontend" / "src" / "pages" / "recipes"
    assert (page_dir / "ListView.vue").is_file()
    assert (page_dir / "DetailView.vue").is_file()
    assert (page_dir / "CreateView.vue").is_file()
    assert (page_dir / "EditView.vue").is_file()
    assert (root / "frontend" / "src" / "composables" / "useCrudResource.ts").is_file()
    create = (page_dir / "CreateView.vue").read_text(encoding="utf-8")
    assert "/api/categories/" in create
    assert "from '../../api/client'" in create
    assert "unwrapList" in create
    assert ":label=\"'Title'\"" in create or "label=\"'Title'\"" in create or "'Title'" in create
    list_view = (page_dir / "ListView.vue").read_text(encoding="utf-8")
    assert "header: 'Title'" in list_view or "header: \"Title\"" in list_view
    assert "AppLayout" not in list_view
    assert "AppLayout" not in create
    assert any(p.name == "CreateView.vue" for p in written)

    cat = ResourceSpec(
        app_name="recipes",
        model_name="Category",
        model_snake="category",
        model_plural="categories",
        api_collection="/api/categories/",
        viewset_name="CategoryViewSet",
    )
    cat_enriched, _ = enrich_resource(root, cat)
    render_crud_pages(root / "frontend", cat_enriched, force=True)
    cat_create = (
        root / "frontend" / "src" / "pages" / "categories" / "CreateView.vue"
    ).read_text(encoding="utf-8")
    assert "apiJson" not in cat_create
    assert "unwrapList" not in cat_create
    assert "onMounted" not in cat_create

    with pytest.raises(FileExistsError):
        render_crud_pages(root / "frontend", enriched)

    render_crud_pages(root / "frontend", enriched, force=True)
