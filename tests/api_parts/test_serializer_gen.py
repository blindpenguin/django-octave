"""Unit tests for serializer generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.serializer_gen import (
    SerializerExistsError,
    SerializerFieldError,
    SerializerOptions,
    build_serializer_class,
    resolve_field_lists,
    write_serializer,
)
from django_octave.inspect.model_fields import inspect_model_fields

SAMPLE = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    body = models.TextField()
'''


def test_resolve_defaults() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    fields, ro = resolve_field_lists(info, fields=None, read_only=None, include_id=True)
    assert fields == ["id", "title", "body", "created_at", "updated_at"]
    assert ro == ["id", "created_at", "updated_at"]


def test_resolve_no_id_and_explicit_fields() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    fields, ro = resolve_field_lists(
        info, fields=["title"], read_only=None, include_id=False
    )
    assert fields == ["title"]
    assert ro == []


def test_resolve_unknown_field() -> None:
    info = inspect_model_fields(SAMPLE, "Post")
    with pytest.raises(SerializerFieldError, match="Unknown field"):
        resolve_field_lists(info, fields=["nope"], read_only=None, include_id=True)


def test_build_serializer_class() -> None:
    src = build_serializer_class(
        "Post", fields=["id", "title"], read_only=["id"]
    )
    assert "class PostSerializer" in src
    assert '"id", "title",' in src
    assert 'read_only_fields = ("id",)' in src


def test_write_serializer_create_and_refuse(tmp_path: Path) -> None:
    models = tmp_path / "models.py"
    models.write_text(SAMPLE, encoding="utf-8")
    opts = SerializerOptions(app_name="blog", model_name="Post")
    path = write_serializer(tmp_path, options=opts)
    text = path.read_text(encoding="utf-8")
    assert "class PostSerializer" in text
    assert "from apps.blog.models import Post" in text

    with pytest.raises(SerializerExistsError):
        write_serializer(tmp_path, options=opts)

    opts_force = SerializerOptions(
        app_name="blog",
        model_name="Post",
        fields=["title"],
        include_id=True,
        force=True,
    )
    write_serializer(tmp_path, options=opts_force)
    text = path.read_text(encoding="utf-8")
    assert '"id", "title",' in text
    assert text.count("class PostSerializer") == 1
