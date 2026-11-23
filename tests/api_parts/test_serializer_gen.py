"""Unit tests for serializer generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.api_parts.serializer_gen import (
    NestedRef,
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


SAMPLE_REL = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Author(TimeStampedModel):
    name = models.CharField(max_length=100)

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
'''


def test_write_serializer_nested(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(SAMPLE_REL, encoding="utf-8")
    opts = SerializerOptions(
        app_name="blog",
        model_name="Post",
        nested=[NestedRef("author")],
        force=False,
    )
    path = write_serializer(tmp_path, options=opts)
    text = path.read_text(encoding="utf-8")
    assert "class AuthorNestedSerializer" in text
    assert "author = AuthorNestedSerializer(read_only=True)" in text
    assert '"author_id"' in text
    assert "author" in text.split("read_only_fields")[1]
    assert text.index("class AuthorNestedSerializer") < text.index(
        "class PostSerializer"
    )


def test_nested_user_helper_before_existing_parent(tmp_path: Path) -> None:
    """Reproduce support-desk order: parent exists, then nest users.User."""
    apps = tmp_path / "apps"
    tickets = apps / "tickets"
    users = apps / "users"
    tickets.mkdir(parents=True)
    users.mkdir(parents=True)
    (tickets / "models.py").write_text(
        '''
from django.db import models
from apps.core.models import TimeStampedModel

class Ticket(TimeStampedModel):
    subject = models.CharField(max_length=200)
    assignee = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)
''',
        encoding="utf-8",
    )
    (users / "models.py").write_text(
        '''
from django.db import models

class User(models.Model):
    email = models.EmailField()
''',
        encoding="utf-8",
    )
    ser = tickets / "serializers.py"
    ser.write_text(
        '''"""Serializers for tickets."""

from __future__ import annotations

from rest_framework import serializers

from apps.tickets.models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "subject", "assignee")
''',
        encoding="utf-8",
    )
    write_serializer(
        tickets,
        options=SerializerOptions(
            app_name="tickets",
            model_name="Ticket",
            nested=[NestedRef("assignee")],
            force=True,
        ),
    )
    text = ser.read_text(encoding="utf-8")
    assert "class UserNestedSerializer" in text
    assert "assignee = UserNestedSerializer(read_only=True)" in text
    assert text.index("class UserNestedSerializer") < text.index(
        "class TicketSerializer"
    )


def test_ensure_class_before_moves_helper(tmp_path: Path) -> None:
    from django_octave.models_gen.cst_util import ensure_class_before

    path = tmp_path / "serializers.py"
    path.write_text(
        """
from rest_framework import serializers

class TicketSerializer(serializers.ModelSerializer):
    assignee = UserNestedSerializer(read_only=True)
    class Meta:
        model = object
        fields = ()

class UserNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = object
        fields = ()
""",
        encoding="utf-8",
    )
    assert ensure_class_before(path, "UserNestedSerializer", "TicketSerializer")
    text = path.read_text(encoding="utf-8")
    assert text.index("class UserNestedSerializer") < text.index(
        "class TicketSerializer"
    )


TENANT_SAMPLE = '''
from django.db import models
from apps.core.models import TenantAwareModel


class Note(TenantAwareModel):
    name = models.CharField(max_length=255)
'''


def test_resolve_tenant_aware_model_never_exposes_tenant() -> None:
    info = inspect_model_fields(TENANT_SAMPLE, "Note")
    fields, _ = resolve_field_lists(info, fields=None, read_only=None, include_id=True)
    assert "tenant" not in fields
    assert "tenant_id" not in fields
    with pytest.raises(SerializerFieldError, match="Unknown field"):
        resolve_field_lists(info, fields=["tenant"], read_only=None, include_id=True)
