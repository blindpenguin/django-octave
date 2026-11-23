"""Project names are allow-listed before they are copied into generated files."""

from __future__ import annotations

import pytest

from django_octave.safe_names import (
    InvalidProjectNameError,
    is_safe_project_name,
    is_safe_slug,
    validate_project_name,
)


@pytest.mark.parametrize(
    "name",
    [
        "Sample",
        "My App",
        "my-app_2.0",
        "Café Münster",
        "日本語プロジェクト",
        "2fast",
        "a",
        "a" * 64,
    ],
)
def test_project_name_accepts_letters_digits_spaces_dots_hyphens_underscores(name: str) -> None:
    assert is_safe_project_name(name)
    assert validate_project_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        ".hidden",
        "-dash",
        "_under",
        "a" * 65,
        'My" + __import__("os").getcwd() + "App',
        "it's",
        "back\\slash",
        "<script>",
        "a&b",
        "{{ 1 + 1 }}",
        "${HOME}",
        "`id`",
        "a;b",
        "a(b)",
        "a/b",
        "a:b",
        "a=b",
        "a\nb",
        "a\tb",
        "a\x00b",
        "a‮b",  # right-to-left override
        "a＂b",  # fullwidth quotation mark
        "a b",  # line separator
    ],
)
def test_project_name_rejects_everything_outside_the_allow_list(name: str) -> None:
    assert not is_safe_project_name(name)
    with pytest.raises(InvalidProjectNameError, match="Invalid project name"):
        validate_project_name(name)


def test_validate_project_name_strips_surrounding_whitespace() -> None:
    assert validate_project_name("  My App \n") == "My App"


def test_validate_project_name_error_escapes_control_characters() -> None:
    with pytest.raises(InvalidProjectNameError) as excinfo:
        validate_project_name("bad\nname")

    assert "\n" not in str(excinfo.value)  # shown with !r, never echoed raw
    assert "1-64 letters, digits" in str(excinfo.value)


@pytest.mark.parametrize("slug", ["demo", "demo_app", "my-app.1", "A1", "a" * 64])
def test_slug_accepts_package_style_names(slug: str) -> None:
    assert is_safe_slug(slug)


@pytest.mark.parametrize("slug", ["", "_x", ".x", "-x", "a b", 'a"b', "a\nb", "a" * 65, "é"])
def test_slug_rejects_everything_else(slug: str) -> None:
    assert not is_safe_slug(slug)
