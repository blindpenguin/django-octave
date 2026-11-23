"""Tests for default= formatting: literals only, always valid Python."""

from __future__ import annotations

import ast

import pytest

from django_octave.fields.codegen import field_source, needs_uuid_import
from django_octave.fields.parser import FieldSpec, parse_field

UUID_TEXT = "123e4567-e89b-12d3-a456-426614174000"


def _default_node(source: str) -> ast.expr:
    """Return the AST of the ``default=`` argument of an emitted field line."""
    call = ast.parse(source).body[0].value  # type: ignore[attr-defined]
    return next(kw.value for kw in call.keywords if kw.arg == "default")


@pytest.mark.parametrize(
    "value",
    [
        "hello",
        "",
        "it's",
        'say "hi"',
        "back\\slash",
        "line1\nline2",
        "tab\there",
        "naïve – 日本語",
        "__import__('os').getcwd()",
        '"); import os; ("',
    ],
)
def test_text_default_is_a_string_literal_with_the_exact_value(value: str) -> None:
    spec = FieldSpec(name="title", type_key="char", default=value, max_length=50)

    node = _default_node(field_source(spec))

    assert isinstance(node, ast.Constant)
    assert node.value == value


def test_injection_payload_stays_inside_a_string_literal() -> None:
    payload = "x');import os;os.system('id');('"
    source = field_source(parse_field(f"title:char:default={payload}"))

    tree = ast.parse(source)

    assert len(tree.body) == 1  # one statement: nothing escaped the literal
    assert not any(isinstance(n, ast.Import) for n in ast.walk(tree))
    assert _default_node(source).value == payload  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("ok:bool:default=true", True),
        ("ok:bool:default=off", False),
        ("n:int:default=42", 42),
        ("n:int:default=-1", -1),
        ("price:decimal:default=9.99", "9.99"),
    ],
)
def test_scalar_defaults(declaration: str, expected: object) -> None:
    node = _default_node(field_source(parse_field(declaration)))

    assert ast.literal_eval(node) == expected


def test_uuid4_default_is_a_reference_not_a_call() -> None:
    node = _default_node(field_source(parse_field("ref:uuid:default=uuid4")))

    assert ast.unparse(node) == "uuid.uuid4"


def test_uuid_literal_default_is_canonical() -> None:
    node = _default_node(field_source(parse_field(f"ref:uuid:default={UUID_TEXT.upper()}")))

    assert ast.unparse(node) == f"uuid.UUID('{UUID_TEXT}')"


def test_no_default_emits_no_default_argument() -> None:
    assert "default" not in field_source(parse_field("title:char"))


@pytest.mark.parametrize(
    "spec",
    [
        FieldSpec(name="x", type_key="date", default="__import__('os').getcwd()"),
        FieldSpec(name="x", type_key="datetime", default="timezone.now"),
    ],
)
def test_hand_built_unsupported_default_is_rejected(spec: FieldSpec) -> None:
    with pytest.raises(ValueError, match="Unsupported default"):
        field_source(spec)


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ("ref:uuid:default=uuid4", True),
        (f"ref:uuid:default={UUID_TEXT}", True),
        ("ref:uuid", False),
        ("title:char:default=x", False),
    ],
)
def test_needs_uuid_import(declaration: str, expected: bool) -> None:
    assert needs_uuid_import([parse_field(declaration)]) is expected
