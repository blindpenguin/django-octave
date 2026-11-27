"""Unit tests for viewset generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.viewset_gen import (
    ViewSetExistsError,
    ViewSetFieldError,
    ViewSetOptions,
    ViewSetPermissionError,
    build_viewset_class,
    resolve_permission,
    resolve_viewset_lists,
    validate_permission,
    write_viewset,
)
from django_octave.inspect.model_fields import inspect_model_fields

SAMPLE = """
from django.db import models
from apps.core.models import TimeStampedModel

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    published = models.BooleanField(default=False)
    body = models.TextField()
"""


def test_validate_permission() -> None:
    assert validate_permission("AllowAny") == "AllowAny"
    with pytest.raises(ViewSetPermissionError):
        validate_permission("IsOwner")


def test_resolve_permission_stock_and_local(tmp_path: Path) -> None:
    mod, name = resolve_permission(tmp_path, "blog", "IsAuthenticated")
    assert mod == "rest_framework.permissions"
    assert name == "IsAuthenticated"

    with pytest.raises(ViewSetPermissionError, match="Unknown permission"):
        resolve_permission(tmp_path, "blog", "IsOwner")

    (tmp_path / "permissions.py").write_text(
        "class IsOwner:\n    pass\n",
        encoding="utf-8",
    )
    mod, name = resolve_permission(tmp_path, "blog", "IsOwner")
    assert mod == "apps.blog.permissions"
    assert name == "IsOwner"


def test_resolve_defaults() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    filters, search, ordering = resolve_viewset_lists(
        info, filters=None, search=None, ordering=None
    )
    assert filters == ["title", "published"]
    assert search == ["title", "body"]
    assert ordering == ["title"]


def test_resolve_bad_filter() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    with pytest.raises(ViewSetFieldError, match="filter"):
        resolve_viewset_lists(info, filters=["nope"], search=None, ordering=None)


def test_build_viewset_class() -> None:
    src = build_viewset_class(
        "Post",
        permission="AllowAny",
        filters=["title"],
        search=["title"],
        ordering=["title"],
        tag="post",
    )
    assert "class PostViewSet" in src
    assert "permission_classes = [AllowAny]" in src
    assert 'tags=["post"]' in src


def test_write_viewset_auto_serializer(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(SAMPLE, encoding="utf-8")
    opts = ViewSetOptions(
        app_name="blog",
        model_name="Post",
        permission="AllowAny",
        filters=["title"],
    )
    views, urls = write_viewset(tmp_path, options=opts)
    assert "class PostViewSet" in views.read_text(encoding="utf-8")
    assert "class PostSerializer" in (tmp_path / "serializers.py").read_text(
        encoding="utf-8"
    )
    assert "router.register" in urls.read_text(encoding="utf-8")
    assert "PostViewSet" in urls.read_text(encoding="utf-8")

    with pytest.raises(ViewSetExistsError):
        write_viewset(tmp_path, options=opts)

    opts.force = True
    opts.permission = "IsAdminUser"
    write_viewset(tmp_path, options=opts)
    text = views.read_text(encoding="utf-8")
    assert text.count("class PostViewSet") == 1
    assert "IsAdminUser" in text
