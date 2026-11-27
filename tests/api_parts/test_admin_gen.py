"""Unit tests for admin generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.admin_gen import (
    AdminExistsError,
    AdminFieldError,
    AdminOptions,
    build_admin_class,
    default_list_display,
    resolve_admin_options,
    write_admin,
)
from django_octave.inspect.model_fields import inspect_model_fields

SAMPLE = """
from django.db import models
from apps.core.models import TimeStampedModel

class Author(TimeStampedModel):
    name = models.CharField(max_length=100)

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    body = models.TextField()
    published = models.BooleanField(default=False)
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
"""


def test_default_list_display_excludes_text() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    display = default_list_display(info)
    assert display[0] == "id"
    assert "title" in display
    assert "published" in display
    assert "author" in display
    assert "body" not in display
    assert "created_at" in display


def test_resolve_overrides_and_select_related() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    display, search, filters, select_related, ordering, hierarchy = (
        resolve_admin_options(
            info,
            list_display=None,
            search=None,
            list_filter=None,
            ordering=["-created_at"],
            use_date_hierarchy=True,
        )
    )
    assert "author" in select_related
    assert hierarchy == "created_at"
    assert ordering == ["-created_at"]
    assert "title" in search
    assert "published" in filters

    with pytest.raises(AdminFieldError):
        resolve_admin_options(
            info,
            list_display=["nope"],
            search=None,
            list_filter=None,
            ordering=None,
            use_date_hierarchy=False,
        )


def test_build_admin_class() -> None:
    src = build_admin_class(
        "Post",
        list_display=["id", "title"],
        search_fields=["title"],
        list_filter=["published"],
        list_select_related=["author"],
        ordering=["title"],
        date_hierarchy="created_at",
    )
    assert "@admin.register(Post)" in src
    assert "class PostAdmin(admin.ModelAdmin):" in src
    assert 'list_select_related = ("author",)' in src
    assert 'date_hierarchy = "created_at"' in src


def test_write_admin_create_force(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(SAMPLE, encoding="utf-8")
    opts = AdminOptions(app_name="blog", model_name="Post")
    path = write_admin(tmp_path, options=opts)
    text = path.read_text(encoding="utf-8")
    assert "class PostAdmin" in text
    assert "list_select_related" in text
    assert 'date_hierarchy = "created_at"' in text

    with pytest.raises(AdminExistsError):
        write_admin(tmp_path, options=opts)

    forced = AdminOptions(
        app_name="blog",
        model_name="Post",
        list_display=["id", "title"],
        date_hierarchy=False,
        force=True,
    )
    write_admin(tmp_path, options=forced)
    text = path.read_text(encoding="utf-8")
    assert text.count("class PostAdmin") == 1
    assert 'list_display = ("id", "title")' in text
    assert "date_hierarchy" not in text
