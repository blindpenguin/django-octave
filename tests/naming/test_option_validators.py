"""Allow-lists for free-text command options that are copied into generated code."""

from __future__ import annotations

import pytest

from django_octave.safe_names import (
    InvalidOptionError,
    is_safe_tag,
    validate_owner_attr,
    validate_tag,
    validate_url_name,
    validate_url_path,
)

INJECTION = [
    'x", __import__("os").system("id"), "y',
    "x'], y=['",
    'x"]; import os; y=["',
]
CONTROL = ["a\nb", "a\tb", "a\x00b", "a‮b", "a b"]


@pytest.mark.parametrize("value", ["blog", "Blog Posts", "a.b-c_d", "2fast", "x" * 64])
def test_tag_accepts_plain_labels(value: str) -> None:
    assert validate_tag(value) == value
    assert is_safe_tag(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        ".x",
        "-x",
        "_x",
        "x" * 65,
        "a/b",
        'a"b',
        "a'b",
        "a\\b",
        "a]b",
        "é",
        *INJECTION,
        *CONTROL,
    ],
)
def test_tag_rejects_everything_else(value: str) -> None:
    with pytest.raises(InvalidOptionError, match="Invalid --tag"):
        validate_tag(value)
    assert not is_safe_tag(value)


def test_tag_error_names_the_option_shows_the_value_and_states_the_rule() -> None:
    with pytest.raises(InvalidOptionError) as excinfo:
        validate_tag("a\nb")

    message = str(excinfo.value)
    assert "--tag" in message
    assert "'a\\nb'" in message  # control characters are escaped, never echoed raw
    assert "letters, digits" in message


def test_tag_strips_surrounding_whitespace() -> None:
    assert validate_tag("  blog  ") == "blog"


@pytest.mark.parametrize(
    "value", ["owner", "author", "created_by", "_private", "A1", "x" * 64]
)
def test_owner_attr_accepts_ascii_identifiers(value: str) -> None:
    assert validate_owner_attr(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1abc",
        "a-b",
        "a.b",
        "a b",
        "class",
        "def",
        "None",
        "é",
        "x" * 65,
        *INJECTION,
        *CONTROL,
    ],
)
def test_owner_attr_rejects_non_identifiers_and_keywords(value: str) -> None:
    with pytest.raises(InvalidOptionError, match="Invalid --owner-attr"):
        validate_owner_attr(value)


@pytest.mark.parametrize(
    "value", ["publish", "a-b", "a_b", "v1/publish", "a/b/c", "x" * 64]
)
def test_url_path_accepts_literal_segments(value: str) -> None:
    assert validate_url_path(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/a",
        "a/",
        "a//b",
        "a b",
        "a.b",
        "a?b",
        "a(b)",
        "a$",
        "(?P<x>.*)",
        "x" * 65,
        *INJECTION,
        *CONTROL,
    ],
)
def test_url_path_rejects_regexes_traversal_and_code(value: str) -> None:
    with pytest.raises(InvalidOptionError, match="Invalid --url-path"):
        validate_url_path(value)


@pytest.mark.parametrize("value", ["publish", "a-b", "a_b", "2x", "x" * 64])
def test_url_name_accepts_names(value: str) -> None:
    assert validate_url_name(value) == value


@pytest.mark.parametrize(
    "value", ["", "-a", "_a", "a/b", "a b", "a.b", "x" * 65, *INJECTION, *CONTROL]
)
def test_url_name_rejects_everything_else(value: str) -> None:
    with pytest.raises(InvalidOptionError, match="Invalid --url-name"):
        validate_url_name(value)
