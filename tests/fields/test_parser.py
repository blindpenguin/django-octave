"""Tests for field DSL parsing and codegen."""

from __future__ import annotations

import pytest

from django_octave.fields.codegen import (
    field_source,
    filterable_field_names,
    str_field_name,
)
from django_octave.fields.parser import (
    FieldParseError,
    parse_field,
    parse_fields,
    split_compact_fields,
)


def test_parse_char_defaults() -> None:
    spec = parse_field("title:char")
    assert spec.name == "title"
    assert spec.max_length == 255
    assert "CharField" in field_source(spec)
    assert "max_length=255" in field_source(spec)


def test_parse_bool_default() -> None:
    spec = parse_field("published:bool:default=false")
    assert "default=False" in field_source(spec)


def test_parse_fields_default() -> None:
    fields = parse_fields([])
    assert len(fields) == 1
    assert fields[0].name == "name"


def test_split_compact_fields() -> None:
    parts = split_compact_fields(
        "title:char:max=200,published:bool:default=false,author:fk:to=blog.Author"
    )
    assert parts == [
        "title:char:max=200",
        "published:bool:default=false",
        "author:fk:to=blog.Author",
    ]
    assert split_compact_fields("") == []
    assert [f.name for f in parse_fields(parts)] == ["title", "published", "author"]


def test_bad_type() -> None:
    with pytest.raises(FieldParseError):
        parse_field("x:nope")


def test_filterable() -> None:
    fields = [parse_field("title:char"), parse_field("body:text"), parse_field("n:int")]
    assert filterable_field_names(fields) == ["title", "n"]


def test_parse_fk() -> None:
    spec = parse_field("author:fk:to=Author")
    assert spec.type_key == "fk"
    assert spec.related_to == "Author"
    assert spec.on_delete == "cascade"
    src = field_source(spec)
    assert "ForeignKey" in src
    assert '"Author"' in src
    assert "on_delete=models.CASCADE" in src


def test_parse_fk_cross_app_set_null() -> None:
    spec = parse_field("author:fk:to=blog.Author:on_delete=set_null")
    assert spec.related_to == "blog.Author"
    assert spec.on_delete == "set_null"
    assert spec.null is True
    assert "SET_NULL" in field_source(spec)


def test_parse_m2m_blank_default() -> None:
    spec = parse_field("tags:m2m:to=Tag")
    assert spec.blank is True
    assert "ManyToManyField" in field_source(spec)
    assert "blank=True" in field_source(spec)


def test_parse_fk_requires_to() -> None:
    with pytest.raises(FieldParseError, match="to="):
        parse_field("author:fk")


def test_parse_bad_to() -> None:
    with pytest.raises(FieldParseError, match="Invalid to="):
        parse_field("author:fk:to=not-valid")


def test_str_field_name_prefers_labels_over_text() -> None:
    assert (
        str_field_name(
            parse_fields(["body:text", "note:char:max=120:blank"])
        )
        == "note"
    )
    assert (
        str_field_name(parse_fields(["body:text", "subject:char:max=200"]))
        == "subject"
    )
    assert str_field_name(parse_fields(["title:char", "body:text"])) == "title"
    assert str_field_name(parse_fields(["body:text"])) == "body"
    assert str_field_name(parse_fields(["n:int"])) is None


UUID_TEXT = "123e4567-e89b-12d3-a456-426614174000"


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("title:char:default=hello", "hello"),
        ("title:char:default=", ""),
        ("title:char:default=it's \"quoted\"", "it's \"quoted\""),
        ("n:int:default=7", "7"),
        ("n:int:default=-3", "-3"),
        ("ok:bool:default=yes", "true"),
        ("ok:bool:default=0", "false"),
        ("price:decimal:default=9.99", "9.99"),
        ("ref:uuid:default=uuid", "uuid4"),
        ("ref:uuid:default=UUID4", "uuid4"),
        (f"ref:uuid:default={UUID_TEXT.upper()}", UUID_TEXT),
    ],
)
def test_parse_default_normalised(declaration: str, expected: str) -> None:
    assert parse_field(declaration).default == expected


@pytest.mark.parametrize(
    "declaration",
    [
        "n:int:default=abc",
        "n:int:default=1.5",
        "ok:bool:default=maybe",
        "price:decimal:default=abc",
        "price:decimal:default=NaN",
        "price:decimal:default=Infinity",
        "ref:uuid:default=not-a-uuid",
    ],
)
def test_parse_default_invalid_value_rejected(declaration: str) -> None:
    with pytest.raises(FieldParseError, match="Invalid default"):
        parse_field(declaration)


@pytest.mark.parametrize(
    "declaration",
    [
        "x:date:default=__import__('os').getcwd()",
        "x:datetime:default=timezone.now",
        "x:fk:to=Author:default=1",
        "x:o2o:to=Author:default=1",
        "x:m2m:to=Tag:default=1",
    ],
)
def test_parse_default_unsupported_type_rejected(declaration: str) -> None:
    with pytest.raises(FieldParseError, match="Defaults are not supported"):
        parse_field(declaration)


@pytest.mark.parametrize("name", ["class", "import", "lambda", "None", "def", "from"])
def test_parse_field_name_python_keyword_rejected(name: str) -> None:
    # "None" fails the snake_case regex first; either way it must be rejected.
    with pytest.raises(FieldParseError):
        parse_field(f"{name}:char")


@pytest.mark.parametrize("name", ["class", "import", "lambda", "def", "from"])
def test_parse_field_name_keyword_message(name: str) -> None:
    with pytest.raises(FieldParseError, match="Python keyword"):
        parse_field(f"{name}:char")


@pytest.mark.parametrize(
    "name",
    ["save", "delete", "clean", "full_clean", "validate_unique", "refresh_from_db", "from_db", "check", "serializable_value"],
)
def test_parse_field_name_model_api_rejected(name: str) -> None:
    with pytest.raises(FieldParseError, match="shadow a Django model method"):
        parse_field(f"{name}:char")


@pytest.mark.parametrize("name", ["title", "name", "match", "type", "saved", "checked"])
def test_parse_field_name_valid_unchanged(name: str) -> None:
    assert parse_field(f"{name}:char").name == name


def test_parse_field_reserved_message_unchanged() -> None:
    with pytest.raises(FieldParseError, match="is reserved"):
        parse_field("id:int")


def test_parse_default_with_colon_gets_hint() -> None:
    with pytest.raises(FieldParseError, match="values containing ':' are not supported"):
        parse_field("opens:char:default=12:30")


def test_parse_unknown_option_without_default_has_no_colon_hint() -> None:
    with pytest.raises(FieldParseError) as excinfo:
        parse_field("title:char:bogus=1")
    assert "':'" not in str(excinfo.value)


@pytest.mark.parametrize("option", ["max=abc", "max=1.5"])
def test_parse_non_integer_option_is_a_parse_error(option: str) -> None:
    with pytest.raises(FieldParseError, match="expected an integer"):
        parse_field(f"title:char:{option}")
