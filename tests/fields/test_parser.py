"""Tests for field DSL parsing and codegen."""

from __future__ import annotations

import pytest

from django_octave.fields.codegen import field_source, filterable_field_names
from django_octave.fields.parser import FieldParseError, parse_field, parse_fields


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


def test_bad_type() -> None:
    with pytest.raises(FieldParseError):
        parse_field("x:nope")


def test_filterable() -> None:
    fields = [parse_field("title:char"), parse_field("body:text"), parse_field("n:int")]
    assert filterable_field_names(fields) == ["title", "n"]
