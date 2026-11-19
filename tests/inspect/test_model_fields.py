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
