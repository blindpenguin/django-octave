"""Unit tests for factory / AllowAny polish in test_gen."""

from __future__ import annotations

from django_octave.api_parts.test_gen import (
    build_api_test_source,
    build_model_factory_source,
    detect_viewset_allows_anonymous,
)
from django_octave.inspect.model_fields import ModelFieldInfo, RelationInfo


def test_cross_app_subfactory() -> None:
    info = ModelFieldInfo(
        model_name="RecipeIngredient",
        fields={
            "recipe": "ForeignKey",
            "ingredient": "ForeignKey",
            "quantity": "DecimalField",
        },
        relations={
            "recipe": RelationInfo(kind="fk", to="Recipe"),
            "ingredient": RelationInfo(kind="fk", to="ingredients.Ingredient"),
        },
    )
    src = build_model_factory_source(
        app_name="recipes",
        model_name="RecipeIngredient",
        info=info,
    )
    assert (
        "ingredient = factory.SubFactory("
        '"tests.factories.ingredients_ingredient.IngredientFactory")'
    ) in src
    assert "TODO: wire SubFactory" not in src


def test_detect_allow_any() -> None:
    views = """
class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Category.objects.all()

class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Recipe.objects.all()
"""
    assert detect_viewset_allows_anonymous(views, "CategoryViewSet") is True
    assert detect_viewset_allows_anonymous(views, "RecipeViewSet") is False


def test_api_test_anonymous_modes() -> None:
    deny = build_api_test_source(
        app_name="blog",
        model_name="Post",
        anonymous_list_ok=False,
    )
    assert "test_list_requires_auth" in deny
    assert "401" in deny or "UNAUTHORIZED" in deny

    open_ = build_api_test_source(
        app_name="blog",
        model_name="Post",
        anonymous_list_ok=True,
    )
    assert "test_list_anonymous_ok" in open_
    assert "test_list_requires_auth" not in open_
