"""Unit tests for CRUD resource discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.crud_discover import (
    discover_app_resources,
    discover_resources,
    require_resource,
)


def _write_app(
    root: Path,
    app: str,
    *,
    models: str,
    views: str,
    urls: str,
) -> None:
    app_dir = root / "apps" / app
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(models, encoding="utf-8")
    (app_dir / "views.py").write_text(views, encoding="utf-8")
    (app_dir / "urls.py").write_text(urls, encoding="utf-8")


def test_discover_recipe_style(tmp_path: Path) -> None:
    _write_app(
        tmp_path,
        "recipes",
        models="""
class Category(models.Model):
    name = models.CharField(max_length=100)

class Recipe(models.Model):
    title = models.CharField(max_length=200)
""",
        views="""
from rest_framework import viewsets

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
""",
        urls="""
router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("recipes", RecipeViewSet, basename="recipe")
""",
    )
    specs = discover_app_resources(tmp_path, "recipes")
    by_model = {s.model_name: s for s in specs}
    assert set(by_model) == {"Category", "Recipe"}
    assert by_model["Recipe"].model_plural == "recipes"
    assert by_model["Recipe"].api_collection == "/api/recipes/"
    assert by_model["Category"].api_collection == "/api/categories/"
    assert by_model["Recipe"].skip_reason is None


def test_discover_fallback_plural_when_no_urls(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "blog"
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(
        "class Post(models.Model):\n    title = models.CharField(max_length=10)\n",
        encoding="utf-8",
    )
    (app_dir / "views.py").write_text(
        "class PostViewSet(viewsets.ModelViewSet):\n"
        "    queryset = Post.objects.all()\n",
        encoding="utf-8",
    )
    specs = discover_app_resources(tmp_path, "blog")
    assert len(specs) == 1
    assert specs[0].model_plural == "posts"
    assert specs[0].api_collection == "/api/posts/"


def test_require_resource_missing(tmp_path: Path) -> None:
    (tmp_path / "apps" / "blog").mkdir(parents=True)
    (tmp_path / "apps" / "blog" / "views.py").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="add-viewset"):
        require_resource(tmp_path, "blog", "Post")


def test_discover_resources_scans_apps(tmp_path: Path) -> None:
    _write_app(
        tmp_path,
        "kb",
        models="class Article(models.Model):\n    title = models.CharField(max_length=10)\n",
        views=(
            "class ArticleViewSet(viewsets.ModelViewSet):\n"
            "    queryset = Article.objects.all()\n"
        ),
        urls='router.register("articles", ArticleViewSet, basename="article")\n',
    )
    all_specs = discover_resources(tmp_path)
    assert any(s.model_name == "Article" for s in all_specs)
