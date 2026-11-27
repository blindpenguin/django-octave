"""Unit tests for static model field inspection."""

from __future__ import annotations

import pytest

from django_octave.inspect.model_fields import (
    default_ordering_names,
    filterable_names,
    inspect_model_fields,
    searchable_names,
)
from django_octave.models_gen.writer import ModelWriteError

SAMPLE_TIMESTAMPED = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    published = models.BooleanField(default=False)
    body = models.TextField()
    views = models.IntegerField(default=0)
'''

SAMPLE_PLAIN = '''
from django.db import models

class Tag(models.Model):
    name = models.SlugField(max_length=50)
    email = models.EmailField()
'''

SAMPLE_TENANT = '''
from django.db import models
from apps.core.models import TenantAwareModel

class Item(TenantAwareModel):
    code = models.UUIDField()
'''


def test_inspect_timestamped_fields() -> None:
    info = inspect_model_fields(SAMPLE_TIMESTAMPED, "Post")
    assert info.has_timestamps is True
    assert info.fields["title"] == "CharField"
    assert info.fields["published"] == "BooleanField"
    assert info.fields["body"] == "TextField"
    assert info.fields["views"] == "IntegerField"
    assert info.available_names == [
        "id",
        "title",
        "published",
        "body",
        "views",
        "created_at",
        "updated_at",
    ]


def test_inspect_plain_model_no_timestamps() -> None:
    info = inspect_model_fields(SAMPLE_PLAIN, "Tag")
    assert info.has_timestamps is False
    assert "created_at" not in info.available_names
    assert info.available_names == ["id", "name", "email"]


def test_tenant_aware_has_timestamps() -> None:
    info = inspect_model_fields(SAMPLE_TENANT, "Item")
    assert info.has_timestamps is True
    assert "created_at" in info.available_names
    assert info.fields["code"] == "UUIDField"


def test_filterable_and_searchable_heuristics() -> None:
    info = inspect_model_fields(SAMPLE_TIMESTAMPED, "Post")
    assert filterable_names(info) == ["title", "published", "views"]
    assert searchable_names(info) == ["title", "body"]
    assert default_ordering_names(info) == ["title"]


def test_default_ordering_falls_back_to_created_at() -> None:
    source = """
from django.db import models
from apps.core.models import TimeStampedModel

class Note(TimeStampedModel):
    body = models.TextField()
"""
    info = inspect_model_fields(source, "Note")
    assert default_ordering_names(info) == ["created_at"]


def test_missing_model_raises() -> None:
    with pytest.raises(ModelWriteError, match="not found"):
        inspect_model_fields(SAMPLE_PLAIN, "Missing")


SAMPLE_RELATIONS = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Author(TimeStampedModel):
    name = models.CharField(max_length=100)

class Post(TimeStampedModel):
    title = models.CharField(max_length=100)
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    tags = models.ManyToManyField("Tag", blank=True)
'''


def test_inspect_relations() -> None:
    info = inspect_model_fields(SAMPLE_RELATIONS, "Post")
    assert "author" in info.relations
    assert info.relations["author"].kind == "fk"
    assert info.relations["author"].to == "Author"
    assert info.relations["tags"].kind == "m2m"
    assert "author" in filterable_names(info)
    assert "tags" not in filterable_names(info)


SAMPLE_RELATED_NAMES = '''
from django.db import models
from apps.core.models import TimeStampedModel

class Note(TimeStampedModel):
    title = models.CharField(max_length=100)
    owner = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="note_owner")
    assignee = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, related_name="+", null=True, blank=True
    )
    watchers = models.ManyToManyField("users.User", related_name="watched_notes", blank=True)
'''


def test_inspect_ignores_related_name_and_keeps_relations_and_flags() -> None:
    info = inspect_model_fields(SAMPLE_RELATED_NAMES, "Note")

    assert info.fields["owner"] == "ForeignKey"
    assert info.relations["owner"].kind == "fk"
    assert info.relations["owner"].to == "users.User"
    assert info.relations["assignee"].kind == "fk"
    assert "assignee" in info.null_fields
    assert "assignee" in info.blank_fields
    assert info.relations["watchers"].kind == "m2m"
    assert "watchers" in info.blank_fields
    assert filterable_names(info) == ["title", "owner", "assignee"]
