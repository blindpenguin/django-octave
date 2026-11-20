"""Tests for __str__ label parsing and --fk-label overrides."""

from __future__ import annotations

import pytest

from django_octave.frontend_gen.str_label import (
    parse_fk_label_overrides,
    parse_simple_str_attr,
    str_method_is_complex,
)


def test_parse_simple_str_self_attr() -> None:
    src = """
class Category(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self) -> str:
        return self.name
"""
    assert parse_simple_str_attr(src, "Category") == "name"
    assert not str_method_is_complex(src, "Category")


def test_parse_simple_str_str_wrapped() -> None:
    src = """
class Recipe(models.Model):
    title = models.CharField(max_length=10)

    def __str__(self) -> str:
        return str(self.title)
"""
    assert parse_simple_str_attr(src, "Recipe") == "title"


def test_complex_str_detected() -> None:
    src = """
class Person(models.Model):
    first = models.CharField(max_length=10)
    last = models.CharField(max_length=10)

    def __str__(self) -> str:
        return f"{self.last}, {self.first}"
"""
    assert parse_simple_str_attr(src, "Person") is None
    assert str_method_is_complex(src, "Person")


def test_parse_fk_label_overrides() -> None:
    assert parse_fk_label_overrides(["author=email", "assignee=email"]) == {
        "author": "email",
        "assignee": "email",
    }
    with pytest.raises(ValueError, match="FIELD=ATTR"):
        parse_fk_label_overrides(["author"])
