"""Unit tests for CRUD field mapping."""

from __future__ import annotations

from pathlib import Path

from django_octave.frontend_gen.crud_discover import discover_app_resources
from django_octave.frontend_gen.crud_fields import (
    build_crud_fields,
    enrich_resource,
    label_field_for_info,
)
from django_octave.inspect.model_fields import inspect_model_fields


def test_label_heuristic_prefers_name() -> None:
    info = inspect_model_fields(
        "class Cat(models.Model):\n"
        "    name = models.CharField(max_length=10)\n"
        "    title = models.CharField(max_length=10)\n",
        "Cat",
    )
    assert label_field_for_info(info) == "name"


def test_build_fields_fk_and_omit_m2m(tmp_path: Path) -> None:
    app = tmp_path / "apps" / "recipes"
    app.mkdir(parents=True)
    (app / "models.py").write_text(
        """
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)

class Recipe(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    tags = models.ManyToManyField(Category)
""",
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

    info = inspect_model_fields(
        (app / "models.py").read_text(encoding="utf-8"),
        "Recipe",
    )
    fields, warnings = build_crud_fields(tmp_path, info, default_app="recipes")
    by_name = {f.name: f for f in fields}
    assert by_name["title"].kind == "string"
    assert by_name["category"].kind == "fk"
    assert by_name["category"].related_plural == "categories"
    assert by_name["category"].related_label_field == "name"
    assert "tags" not in by_name
    assert any("M2M" in w for w in warnings)


def test_fk_without_list_route_falls_back_to_number(tmp_path: Path) -> None:
    app = tmp_path / "apps" / "tickets"
    app.mkdir(parents=True)
    users = tmp_path / "apps" / "users"
    users.mkdir(parents=True)
    (users / "models.py").write_text(
        "class User(models.Model):\n    email = models.EmailField()\n",
        encoding="utf-8",
    )
    (app / "models.py").write_text(
        "class Ticket(models.Model):\n"
        "    subject = models.CharField(max_length=100)\n"
        "    assignee = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)\n",
        encoding="utf-8",
    )
    (app / "views.py").write_text(
        "class TicketViewSet(viewsets.ModelViewSet):\n"
        "    queryset = Ticket.objects.all()\n",
        encoding="utf-8",
    )
    (app / "urls.py").write_text(
        'router.register("tickets", TicketViewSet, basename="ticket")\n',
        encoding="utf-8",
    )
    info = inspect_model_fields(
        (app / "models.py").read_text(encoding="utf-8"),
        "Ticket",
    )
    fields, warnings = build_crud_fields(tmp_path, info, default_app="tickets")
    by_name = {f.name: f for f in fields}
    assert by_name["assignee"].kind == "number"
    assert by_name["assignee"].related_plural is None
    assert any("PK" in w and "assignee" in w for w in warnings)


def test_user_fk_uses_users_list_when_wired(tmp_path: Path) -> None:
    app = tmp_path / "apps" / "kb"
    app.mkdir(parents=True)
    users = tmp_path / "apps" / "users"
    users.mkdir(parents=True)
    (users / "models.py").write_text(
        "class User(models.Model):\n    email = models.EmailField()\n",
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "urls.py").write_text(
        'path("api/users/", UserListView.as_view(), name="user_list"),\n',
        encoding="utf-8",
    )
    (app / "models.py").write_text(
        "class Article(models.Model):\n"
        "    title = models.CharField(max_length=100)\n"
        "    author = models.ForeignKey('users.User', on_delete=models.CASCADE)\n",
        encoding="utf-8",
    )
    info = inspect_model_fields(
        (app / "models.py").read_text(encoding="utf-8"),
        "Article",
    )
    fields, warnings = build_crud_fields(tmp_path, info, default_app="kb")
    by_name = {f.name: f for f in fields}
    assert by_name["author"].kind == "fk"
    assert by_name["author"].related_plural == "users"
    # Prefer API `label` (str(user)) when User models aren't on disk with simple __str__
    assert by_name["author"].related_label_field in {"label", "email"}
    assert not any("author" in w and "PK" in w for w in warnings)


def test_enrich_resource(tmp_path: Path) -> None:
    app = tmp_path / "apps" / "blog"
    app.mkdir(parents=True)
    (app / "models.py").write_text(
        "class Post(models.Model):\n    title = models.CharField(max_length=10)\n",
        encoding="utf-8",
    )
    (app / "views.py").write_text(
        "class PostViewSet(viewsets.ModelViewSet):\n"
        "    queryset = Post.objects.all()\n",
        encoding="utf-8",
    )
    (app / "urls.py").write_text(
        'router.register("posts", PostViewSet, basename="post")\n',
        encoding="utf-8",
    )
    spec = discover_app_resources(tmp_path, "blog")[0]
    enriched, _ = enrich_resource(tmp_path, spec)
    assert enriched.label_field == "title"
    assert any(f.name == "title" for f in enriched.fields)
