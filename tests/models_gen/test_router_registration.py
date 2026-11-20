"""Tests for router basename registration rewrite."""

from __future__ import annotations

from pathlib import Path

from django_octave.models_gen.cst_util import ensure_router_registration

STALE = '''"""URL routes for recipes."""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.recipes.views import RecipeViewSet

router = DefaultRouter()
router.register("", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("", include(router.urls)),
]
'''


def test_rewrites_stale_app_basename(tmp_path: Path) -> None:
    path = tmp_path / "urls.py"
    path.write_text(STALE, encoding="utf-8")
    ensure_router_registration(path, "recipes", "Recipe")
    text = path.read_text(encoding="utf-8")
    assert 'basename="recipe"' in text
    assert 'router.register("recipes", RecipeViewSet, basename="recipe")' in text
    assert 'basename="recipes"' not in text
    assert 'router.register("",' not in text


def test_inserts_plural_registration(tmp_path: Path) -> None:
    path = tmp_path / "urls.py"
    path.write_text(STALE, encoding="utf-8")
    ensure_router_registration(path, "recipes", "Recipe")
    ensure_router_registration(path, "recipes", "Category")
    text = path.read_text(encoding="utf-8")
    assert 'router.register("recipes", RecipeViewSet, basename="recipe")' in text
    assert 'router.register("categories", CategoryViewSet, basename="category")' in text
    assert "CategoryViewSet" in text
