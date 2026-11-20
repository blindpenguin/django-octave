"""Unit tests for CRUD router/nav wiring."""

from __future__ import annotations

from pathlib import Path

from django_octave.frontend_gen.crud_types import ResourceSpec
from django_octave.frontend_gen.crud_wire import (
    ROUTES_BEGIN,
    wire_crud,
)
from django_octave.frontend_gen.setup import render_frontend


def test_wire_crud_injects_routes_and_nav(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    render_frontend(
        frontend,
        project_name="Demo",
        project_slug="demo",
        include_register=False,
    )
    spec = ResourceSpec(
        app_name="recipes",
        model_name="Recipe",
        model_snake="recipe",
        model_plural="recipes",
        api_collection="/api/recipes/",
        viewset_name="RecipeViewSet",
    )
    wire_crud(frontend, [spec])
    router = (frontend / "src" / "router" / "index.ts").read_text(encoding="utf-8")
    assert ROUTES_BEGIN in router
    assert "recipes-list" in router
    assert "pages/recipes/ListView.vue" in router
    assert "path: 'recipes'" in router
    assert "path: '/recipes'" not in router
    assert "component: AppLayout" in router
    layout = (frontend / "src" / "layouts" / "AppLayout.vue").read_text(encoding="utf-8")
    assert "crudNavItems" in layout
    assert "// --- django-octave crud nav begin ---" in layout
    assert "{ label: 'Recipe', to: '/recipes' }," in layout

    # Re-wire with second resource replaces block
    cat = ResourceSpec(
        app_name="recipes",
        model_name="Category",
        model_snake="category",
        model_plural="categories",
        api_collection="/api/categories/",
        viewset_name="CategoryViewSet",
    )
    wire_crud(frontend, [spec, cat])
    router = (frontend / "src" / "router" / "index.ts").read_text(encoding="utf-8")
    assert "categories-list" in router
    assert router.count("recipes-list") == 1
    layout = (frontend / "src" / "layouts" / "AppLayout.vue").read_text(encoding="utf-8")
    assert "{ label: 'Category', to: '/categories' }," in layout
    assert layout.count("label: 'Recipe'") == 1
