"""Tests for app naming helpers."""

from __future__ import annotations

import pytest

from django_octave.naming import (
    InvalidAppNameError,
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


def test_singularize_and_model_name() -> None:
    assert singularize("orders") == "order"
    assert singularize("categories") == "category"
    assert model_name_from_app("orders") == "Order"
    assert model_name_from_app("blog") == "Blog"
    assert model_name_from_app("order_items") == "Item"
