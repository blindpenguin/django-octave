"""Tests for the admin stub that ``add-model`` writes (``_admin_class``)."""

from __future__ import annotations

import ast

import pytest

from django_octave.fields.parser import FieldSpec, parse_field
from django_octave.models_gen.api_sync import _admin_class


def _fields(*declarations: str) -> list[FieldSpec]:
    return [parse_field(d) for d in declarations]


def _class_attribute(source: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", None) == name
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError(f"{name} not found in\n{source}")


@pytest.mark.parametrize(
    ("declarations", "expected"),
    [
        pytest.param(
            ("title:char", "tags:m2m:to=Tag", "owner:fk:to=users.User"),
            ("id", "title", "owner", "created_at", "updated_at"),
            id="m2m-in-the-middle",
        ),
        pytest.param(
            ("editors:m2m:to=users.User", "viewers:m2m:to=users.User", "title:char"),
            ("id", "title", "created_at", "updated_at"),
            id="several-m2m",
        ),
        pytest.param(
            ("tags:m2m:to=Tag",),
            ("id", "created_at", "updated_at"),
            id="m2m-only",
        ),
    ],
)
def test_admin_list_display_leaves_out_many_to_many_fields(
    declarations: tuple[str, ...], expected: tuple[str, ...]
) -> None:
    source = _admin_class("Note", _fields(*declarations))

    assert _class_attribute(source, "list_display") == expected


def test_admin_list_display_keeps_every_other_field_in_declaration_order() -> None:
    declarations = (
        "title:char",
        "body:text",
        "n:int",
        "published:bool",
        "owner:fk:to=users.User",
        "profile:o2o:to=users.User",
        "ref:uuid",
    )

    source = _admin_class("Note", _fields(*declarations))

    assert _class_attribute(source, "list_display") == (
        "id",
        "title",
        "body",
        "n",
        "published",
        "owner",
        "profile",
        "ref",
        "created_at",
        "updated_at",
    )


def test_admin_without_many_to_many_fields_is_byte_identical_to_before() -> None:
    source = _admin_class(
        "Note", _fields("title:char", "body:text", "owner:fk:to=users.User")
    )

    assert source == (
        "\n"
        "@admin.register(Note)\n"
        "class NoteAdmin(admin.ModelAdmin):\n"
        '    list_display = ("id", "title", "body", "owner", "created_at", "updated_at",)\n'
        '    search_fields = ("title", "body",)\n'
    )


def test_admin_search_fields_do_not_depend_on_many_to_many_fields() -> None:
    with_m2m = _admin_class("Note", _fields("title:char", "tags:m2m:to=Tag"))
    without = _admin_class("Note", _fields("title:char"))

    assert _class_attribute(with_m2m, "search_fields") == ("title",)
    assert _class_attribute(without, "search_fields") == ("title",)


def test_admin_stub_is_valid_python_for_an_m2m_only_model() -> None:
    source = _admin_class("Note", _fields("tags:m2m:to=Tag"))

    ast.parse(source)
    assert _class_attribute(source, "search_fields") == ()
