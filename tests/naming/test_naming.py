"""Tests for app naming helpers."""

from __future__ import annotations

import pytest

from django_octave.naming import (
    InvalidAppNameError,
    humanize_field_label,
    model_name_from_app,
    singularize,
    validate_app_name,
)


def test_validate_app_name() -> None:
    assert validate_app_name("Blog") == "blog"
    assert validate_app_name("order-items") == "order_items"


@pytest.mark.parametrize("name", ["core", "users", "django", "123bad", ""])
def test_validate_rejects(name: str) -> None:
    with pytest.raises((InvalidAppNameError, ValueError)):
        validate_app_name(name)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Blog", "blog"),
        ("order-items", "order_items"),
        (" blog ", "blog"),
        ("blog 2", "blog_2"),
        ("_private", "private"),
        ("project_1x", "project_1x"),
        # A leading separator is dropped before the digit check, so a digit that
        # follows it is accepted and gets the ``project_`` prefix.
        ("-1x", "project_1x"),
    ],
)
def test_validate_app_name_accepts_and_normalizes(raw: str, expected: str) -> None:
    assert validate_app_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("1blog", "must start with a letter"),
        ("9", "must start with a letter"),
        (" 2x", "must start with a letter"),
        ("class", "Python keyword"),
        ("core", "reserved"),
        ("", "Cannot derive a valid project slug"),
        ("é", "Cannot derive a valid project slug"),
    ],
)
def test_validate_app_name_rejects_with_a_specific_message(
    raw: str, message: str
) -> None:
    with pytest.raises(InvalidAppNameError, match=message):
        validate_app_name(raw)


def test_singularize_and_model_name() -> None:
    assert singularize("orders") == "order"
    assert singularize("categories") == "category"
    assert model_name_from_app("orders") == "Order"
    assert model_name_from_app("blog") == "Blog"
    assert model_name_from_app("order_items") == "Item"


def test_humanize_field_label() -> None:
    assert humanize_field_label("name") == "Name"
    assert humanize_field_label("prep_minutes") == "Prep Minutes"
    assert humanize_field_label("is_published") == "Is Published"
    assert humanize_field_label("id") == "ID"
    assert humanize_field_label("api_url") == "API URL"
