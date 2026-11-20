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
