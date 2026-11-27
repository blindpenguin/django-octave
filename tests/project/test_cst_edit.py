"""Unit tests for the libcst helpers that edit config files without disturbing them.

Every edit is compared byte for byte with the expected source, and every result must still
parse. The shapes are the ones a formatter or a person produces: multi-line with and
without a trailing comma, one line, empty, tuples, comments, other indentation.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import libcst as cst
import pytest

from django_octave.project.cst_edit import (
    ConfigEditError,
    append_item,
    check_result,
    dominant_quote,
    ensure_import_names,
    find_import_from,
    find_sequence,
    imported_names,
    insert_item_after,
    insert_marked_block,
    make_string,
    name_is_used,
    parse_source,
    remove_import_name,
    remove_items,
    remove_marked_block,
    route_of,
    sequence_of,
    sequence_strings,
    string_value,
    view_of,
    with_sequence,
    with_view,
)

PATH = Path("config/urls.py")
BEGIN = "# --- begin ---"
END = "# --- end ---"


def _edit(
    source: str, name: str, change: Callable[[cst.BaseExpression], cst.BaseExpression]
) -> str:
    module = parse_source(source, PATH)
    ref = find_sequence(module, name)
    assert ref is not None, f"no sequence {name} in {source!r}"
    updated = with_sequence(module, ref, change(sequence_of(module, ref)))  # type: ignore[arg-type]
    ast.parse(updated.code)
    return updated.code


def _new(value: str = '"new"') -> cst.BaseExpression:
    return cst.parse_expression(value)


def _append(source: str, value: str = '"new"') -> str:
    return _edit(source, "x", lambda seq: append_item(seq, _new(value)))  # type: ignore[arg-type]


# --- append_item ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            'x = [\n    "a",\n    "b",\n]\n',
            'x = [\n    "a",\n    "b",\n    "new",\n]\n',
            id="multi-line-trailing-comma",
        ),
        pytest.param(
            'x = [\n    "a",\n    "b"\n]\n',
            'x = [\n    "a",\n    "b",\n    "new"\n]\n',
            id="multi-line-no-trailing-comma",
        ),
        pytest.param('x = ["a", "b"]\n', 'x = ["a", "b", "new"]\n', id="one-line"),
        pytest.param('x = ["a"]\n', 'x = ["a", "new"]\n', id="one-line-one-item"),
        pytest.param("x = []\n", 'x = ["new"]\n', id="empty-one-line"),
        pytest.param("x = [\n]\n", 'x = [\n    "new",\n]\n', id="empty-multi-line"),
        pytest.param(
            'x = [\n    "a",\n    "b",  # last\n]\n',
            'x = [\n    "a",\n    "b",  # last\n    "new",\n]\n',
            id="comment-on-the-last-item",
        ),
        pytest.param(
            'x = [\n    "a",\n    # more later\n]\n',
            'x = [\n    "a",\n    "new",\n    # more later\n]\n',
            id="comment-line-before-the-bracket",
        ),
        pytest.param(
            'x = [\n    # first\n    "a",\n    # second\n    "b",\n]\n',
            'x = [\n    # first\n    "a",\n    # second\n    "b",\n    "new",\n]\n',
            id="comment-lines-between-items",
        ),
        pytest.param(
            'x = [\n        "a",\n        "b",\n    ]\n',
            'x = [\n        "a",\n        "b",\n        "new",\n    ]\n',
            id="deeper-indentation",
        ),
        pytest.param(
            'x = [\n    "a",\n\n    "b",\n]\n',
            'x = [\n    "a",\n\n    "b",\n    "new",\n]\n',
            id="blank-line-between-items",
        ),
        pytest.param(
            'x = [\n    "]",\n    "a,b",  # "quoted" [bracket]\n]\n',
            'x = [\n    "]",\n    "a,b",  # "quoted" [bracket]\n    "new",\n]\n',
            id="brackets-and-quotes-inside-strings-and-comments",
        ),
        pytest.param(
            'x = [\n    f(\n        "a",\n        1,\n    ),\n]\n',
            'x = [\n    f(\n        "a",\n        1,\n    ),\n    "new",\n]\n',
            id="multi-line-call-as-last-item",
        ),
    ],
)
def test_append_item_keeps_the_shape_of_a_list(source: str, expected: str) -> None:
    assert _append(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            'x = (\n    "a",\n    "b",\n)\n',
            'x = (\n    "a",\n    "b",\n    "new",\n)\n',
            id="multi-line",
        ),
        pytest.param('x = ("a", "b")\n', 'x = ("a", "b", "new")\n', id="one-line"),
        pytest.param(
            'x = ("a",)\n', 'x = ("a", "new",)\n', id="one-item-trailing-comma"
        ),
    ],
)
def test_append_item_keeps_the_shape_of_a_tuple(source: str, expected: str) -> None:
    assert _append(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            'x: list[str] = [\n    "a",\n]\n',
            'x: list[str] = [\n    "a",\n    "new",\n]\n',
            id="annotated",
        ),
        pytest.param(
            'x: list = ["a"]\n', 'x: list = ["a", "new"]\n', id="annotated-one-line"
        ),
        pytest.param(
            'x += [\n    "a",\n]\n', 'x += [\n    "a",\n    "new",\n]\n', id="augmented"
        ),
    ],
)
def test_append_item_works_on_annotated_and_augmented_assignments(
    source: str, expected: str
) -> None:
    assert _append(source) == expected


def test_append_item_leaves_every_other_statement_untouched() -> None:
    source = (
        '"""Doc."""\n\nimport os\n\n# about x\nx = [\n    "a",  # keep\n]\n\ny = ["z"]\n\n'
        "def f():\n    return [1, 2]\n"
    )

    updated = _append(source)

    assert updated == source.replace(
        '    "a",  # keep\n]', '    "a",  # keep\n    "new",\n]'
    )


def test_append_item_uses_the_newlines_of_the_file() -> None:
    source = 'x = [\r\n    "a",\r\n]\r\n'

    updated = _append(source)

    assert updated == 'x = [\r\n    "a",\r\n    "new",\r\n]\r\n'


# --- insert_item_after --------------------------------------------------------------------------


def _insert_after(source: str, index: int) -> str:
    return _edit(source, "x", lambda seq: insert_item_after(seq, index, _new()))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("source", "index", "expected"),
    [
        pytest.param(
            'x = [\n    "a",\n    "b",\n]\n',
            0,
            'x = [\n    "a",\n    "new",\n    "b",\n]\n',
            id="after-the-first",
        ),
        pytest.param(
            'x = [\n    "a",  # first\n    "b",\n]\n',
            0,
            'x = [\n    "a",  # first\n    "new",\n    "b",\n]\n',
            id="comment-stays-with-its-item",
        ),
        pytest.param(
            'x = [\n    "a",\n    # about b\n    "b",\n]\n',
            0,
            'x = [\n    "a",\n    "new",\n    # about b\n    "b",\n]\n',
            id="comment-above-the-next-item-stays-above-it",
        ),
        pytest.param('x = ["a", "b"]\n', 0, 'x = ["a", "new", "b"]\n', id="one-line"),
        pytest.param(
            'x = [\n    "a",\n    "b",\n]\n',
            1,
            'x = [\n    "a",\n    "b",\n    "new",\n]\n',
            id="after-the-last-is-an-append",
        ),
    ],
)
def test_insert_item_after_puts_the_item_right_after_the_index(
    source: str, index: int, expected: str
) -> None:
    assert _insert_after(source, index) == expected


# --- remove_items --------------------------------------------------------------------------------


def _remove(source: str, *values: str) -> str:
    return _edit(
        source,
        "x",
        lambda seq: remove_items(seq, lambda el: string_value(el) in values),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("source", "values", "expected"),
    [
        pytest.param(
            'x = [\n    "a",\n    "b",\n    "c",\n]\n',
            ("b",),
            'x = [\n    "a",\n    "c",\n]\n',
            id="middle",
        ),
        pytest.param(
            'x = [\n    "a",\n    "b",\n    "c",\n]\n',
            ("a",),
            'x = [\n    "b",\n    "c",\n]\n',
            id="first",
        ),
        pytest.param(
            'x = [\n    "a",\n    # about b\n    "b",\n]\n',
            ("a",),
            'x = [\n    # about b\n    "b",\n]\n',
            id="first-keeps-the-comment-above-the-next-item",
        ),
        pytest.param(
            'x = [\n    "a",\n    "b",\n    "c",\n]\n',
            ("c",),
            'x = [\n    "a",\n    "b",\n]\n',
            id="last-keeps-the-trailing-comma",
        ),
        pytest.param(
            'x = [\n    "a",\n    "b",\n    "c"\n]\n',
            ("c",),
            'x = [\n    "a",\n    "b"\n]\n',
            id="last-without-trailing-comma",
        ),
        pytest.param(
            'x = [\n    "a",  # keep me\n    "b",  # drop me\n]\n',
            ("b",),
            'x = [\n    "a",  # keep me\n]\n',
            id="last-with-comments",
        ),
        pytest.param(
            'x = [\n    "a",\n    # about c\n    "b",\n    # about d\n    "c",\n]\n',
            ("b",),
            'x = [\n    "a",\n    # about d\n    "c",\n]\n',
            id="the-comment-of-the-next-item-is-kept",
        ),
        pytest.param(
            'x = ["a", "b", "c"]\n', ("b",), 'x = ["a", "c"]\n', id="one-line-middle"
        ),
        pytest.param(
            'x = ["a", "b", "c"]\n', ("c",), 'x = ["a", "b"]\n', id="one-line-last"
        ),
        pytest.param('x = ["a", "b"]\n', ("a", "b"), "x = []\n", id="everything"),
        pytest.param(
            'x = [\n    "a",\n    "b",\n]\n',
            ("zzz",),
            'x = [\n    "a",\n    "b",\n]\n',
            id="nothing",
        ),
        pytest.param(
            'x = [\n    "a",\n    "b",\n    "a",\n]\n',
            ("a",),
            'x = [\n    "b",\n]\n',
            id="every-match",
        ),
    ],
)
def test_remove_items_keeps_the_shape_of_a_list(
    source: str, values: tuple[str, ...], expected: str
) -> None:
    assert _remove(source, *values) == expected


# --- finding sequences and strings ----------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        'x = ["a"]\n',
        'x: list[str] = ["a"]\n',
        'x = ("a",)\n',
        'x += ["a"]\n',
        '"""Doc."""\nimport os\nx = ["a"]\n',
    ],
)
def test_find_sequence_finds_top_level_list_and_tuple_assignments(source: str) -> None:
    assert find_sequence(parse_source(source, PATH), "x") is not None


@pytest.mark.parametrize(
    "source",
    [
        "y = ['a']\n",
        "x = base + ['a']\n",
        "x = list(base)\n",
        "x = {'a'}\n",
        "x = 'a'\n",
        "def f():\n    x = ['a']\n",
        "if flag:\n    x = ['a']\n",
        "x, y = ['a'], ['b']\n",
    ],
)
def test_find_sequence_ignores_everything_that_is_not_a_literal_sequence(
    source: str,
) -> None:
    assert find_sequence(parse_source(source, PATH), "x") is None


def test_find_sequence_prefers_the_plain_assignment_over_an_augmented_one() -> None:
    module = parse_source('x += ["extra"]\nx = ["a"]\n', PATH)

    ref = find_sequence(module, "x")

    assert ref is not None
    assert string_value(sequence_of(module, ref).elements[0].value) == "a"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('"a.b"', "a.b"),
        ("'a.b'", "a.b"),
        ('"""a"""', "a"),
        ('r"a\\b"', "a\\b"),
        ('f"a{b}"', None),
        ('"a" "b"', None),
        ('b"a"', None),
        ("name", None),
        ("1", None),
    ],
)
def test_string_value_reads_only_plain_string_literals(
    expression: str, expected: str | None
) -> None:
    assert string_value(cst.parse_expression(expression)) == expected


def test_sequence_strings_collects_list_and_tuple_elements_but_not_comments_or_other_strings() -> (
    None
):
    module = parse_source(
        '# TODO "apps.todo"\nNAME = "apps.name"\nAPPS = ["apps.a", \'apps.b\']\n'
        'OTHER = ("apps.c",)\nD = {"k": "apps.d"}\ncall("apps.e")\n'
        'class C:\n    LIST = ["apps.f"]\n',
        PATH,
    )

    assert sequence_strings(module) == {"apps.a", "apps.b", "apps.c", "apps.f"}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('x = ["a", "b"]\n', '"'),
        ("x = ['a', 'b']\n", "'"),
        ('x = [1, "a"]\n', '"'),
        ("x = []\n", '"'),
        ("x = [1, 2]\n", '"'),
        ("x = [f('a'), \"b\"]\n", "'"),
    ],
)
def test_dominant_quote_follows_the_first_string_in_the_sequence(
    source: str, expected: str
) -> None:
    module = parse_source(source, PATH)
    ref = find_sequence(module, "x")
    assert ref is not None

    assert dominant_quote(sequence_of(module, ref)) == expected


def test_make_string_uses_the_quote_and_refuses_text_that_would_break_it() -> None:
    assert make_string("apps.blog", '"').value == '"apps.blog"'
    assert make_string("apps.blog", "'").value == "'apps.blog'"
    for bad in ['a"b', "a'b", "a\\b", "a\nb"]:
        with pytest.raises(ConfigEditError):
            make_string(bad, '"')


# --- routes ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('path("api/", include("x"))', "api/"),
        ("path('api/', view, name='n')", "api/"),
        (
            'path(\n    "api/auth/token/",\n    view,\n    name="n",\n)',
            "api/auth/token/",
        ),
        ('re_path(r"^x$", view)', None),
        ("path(route, view)", None),
        ('other("api/", view)', None),
        ('"api/"', None),
    ],
)
def test_route_of_reads_the_first_string_of_a_path_call(
    expression: str, expected: str | None
) -> None:
    assert route_of(cst.parse_expression(expression)) == expected


def test_with_view_replaces_only_the_view_argument_and_keeps_the_formatting() -> None:
    call = cst.parse_expression(
        'path(\n    "api/auth/token/",\n    throttled(TokenObtainPairView),\n    name="n",\n)'
    )

    changed = with_view(
        call, cst.parse_expression("EmailTokenObtainPairView.as_view()")
    )

    assert cst.Module([]).code_for_node(changed) == (
        'path(\n    "api/auth/token/",\n    EmailTokenObtainPairView.as_view(),\n    name="n",\n)'
    )
    assert (
        cst.Module([]).code_for_node(view_of(call)) == "throttled(TokenObtainPairView)"
    )  # type: ignore[arg-type]


def test_view_of_returns_none_for_a_call_without_a_view() -> None:
    assert view_of(cst.parse_expression('path("api/")')) is None  # type: ignore[arg-type]


# --- imports -----------------------------------------------------------------------------------


def _ensure(
    source: str, *names: str, fallback: str = "from django.urls import include, path"
) -> str:
    module = parse_source(source, PATH)
    updated = ensure_import_names(
        module, "django.urls", list(names), fallback_statement=fallback
    )
    ast.parse(updated.code)
    return updated.code


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            "from django.urls import path\n",
            "from django.urls import path, include\n",
            id="one-line",
        ),
        pytest.param(
            "from django.urls import (\n    path,\n)\n",
            "from django.urls import (\n    path,\n    include,\n)\n",
            id="parenthesized-trailing-comma",
        ),
        pytest.param(
            "from django.urls import (\n    path\n)\n",
            "from django.urls import (\n    path,\n    include\n)\n",
            id="parenthesized-no-trailing-comma",
        ),
        pytest.param(
            "from django.urls import path as p\n",
            "from django.urls import path as p, include\n",
            id="aliased",
        ),
        pytest.param(
            "from django.urls import include, path\n",
            "from django.urls import include, path\n",
            id="already-imported",
        ),
        pytest.param(
            "from django.urls import include as inc\n",
            "from django.urls import include as inc\n",
            id="already-imported-under-an-alias",
        ),
    ],
)
def test_ensure_import_names_adds_a_missing_name_to_the_existing_import(
    source: str, expected: str
) -> None:
    assert _ensure(source, "include") == expected


def test_ensure_import_names_adds_the_fallback_after_the_last_import_when_there_is_none() -> (
    None
):
    source = '"""Doc."""\n\nfrom __future__ import annotations\n\nimport os\nfrom a import b\n\nx = 1\n'

    assert _ensure(source, "include") == source.replace(
        "from a import b\n", "from a import b\nfrom django.urls import include, path\n"
    )


def test_ensure_import_names_puts_the_fallback_after_the_docstring_when_there_are_no_imports() -> (
    None
):
    source = '"""Doc."""\n\nx = 1\n'

    updated = _ensure(source, "include")

    assert updated == '"""Doc."""\nfrom django.urls import include, path\n\nx = 1\n'


def test_ensure_import_names_only_looks_at_top_level_absolute_imports() -> None:
    source = (
        "from .urls import include\n"
        "def f():\n    from django.urls import include\n"
        "x = 1\n"
    )

    updated = _ensure(source, "include")

    assert "from django.urls import include, path\n" in updated


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("from m import A, B\n", "from m import A\n", id="one-line-last"),
        pytest.param("from m import B, A\n", "from m import A\n", id="one-line-first"),
        pytest.param(
            "from m import (\n    A,\n    B,\n)\n",
            "from m import (\n    A,\n)\n",
            id="parenthesized",
        ),
        pytest.param("from m import B\n", "", id="the-only-name-removes-the-statement"),
        pytest.param("from m import A\n", "from m import A\n", id="not-imported"),
    ],
)
def test_remove_import_name_removes_one_name(source: str, expected: str) -> None:
    module = parse_source(source, PATH)

    updated = remove_import_name(module, "m", "B")

    ast.parse(updated.code)
    assert updated.code == expected


def test_name_is_used_ignores_imports_but_sees_every_other_use() -> None:
    module = parse_source(
        "from m import A, B\n\nx = [A]\n\ndef f():\n    return B\n", PATH
    )

    assert name_is_used(module, "A") is True
    assert name_is_used(module, "B") is True
    assert name_is_used(parse_source("from m import A\n", PATH), "A") is False
    assert name_is_used(parse_source("# A\nx = 'A'\n", PATH), "A") is False


# --- the managed block with marker comments ---------------------------------------------------


BLOCK = (
    '"""Doc."""\n\nimport os\n'
    f"{BEGIN}\nfrom a import b\nfrom a import c\n{END}\n\nx = 1\n"
)


def test_remove_marked_block_removes_the_statements_and_both_marker_lines() -> None:
    module = parse_source(BLOCK, PATH)

    updated = remove_marked_block(module, BEGIN, END)

    assert updated.code == '"""Doc."""\n\nimport os\n\nx = 1\n'


def test_remove_marked_block_keeps_comments_and_blank_lines_around_the_block() -> None:
    source = (
        "import os\n\n# keep above\n"
        f"{BEGIN}\nfrom a import b\n{END}\n# keep below\nx = 1\n"
    )

    updated = remove_marked_block(parse_source(source, PATH), BEGIN, END)

    assert updated.code == "import os\n\n# keep above\n# keep below\nx = 1\n"


def test_remove_marked_block_without_markers_changes_nothing() -> None:
    module = parse_source("import os\n\nx = 1\n", PATH)

    assert remove_marked_block(module, BEGIN, END).code == module.code


@pytest.mark.parametrize(
    "source",
    [
        f"import os\n{BEGIN}\nfrom a import b\nx = 1\n",
        f"import os\nfrom a import b\n{END}\nx = 1\n",
        f"import os\n{END}\nfrom a import b\n{BEGIN}\nx = 1\n",
    ],
    ids=["begin-only", "end-only", "end-before-begin"],
)
def test_remove_marked_block_refuses_unbalanced_markers(source: str) -> None:
    with pytest.raises(ConfigEditError, match="--- (begin|end) ---"):
        remove_marked_block(parse_source(source, PATH), BEGIN, END)


def test_insert_marked_block_adds_statements_between_the_markers_after_a_statement() -> (
    None
):
    module = parse_source("import os\nfrom k import t\n\nx = 1\n", PATH)

    updated = insert_marked_block(
        module,
        after_index=find_import_from(module, "k"),
        begin=BEGIN,
        end=END,
        statements=["from a import b", "from a import c"],
    )

    assert updated.code == (
        f"import os\nfrom k import t\n{BEGIN}\nfrom a import b\nfrom a import c\n{END}\n\nx = 1\n"
    )


def test_insert_then_remove_marked_block_round_trips() -> None:
    source = "import os\nfrom k import t\n\nx = 1\n"
    module = parse_source(source, PATH)
    inserted = insert_marked_block(
        module,
        after_index=find_import_from(module, "k"),
        begin=BEGIN,
        end=END,
        statements=["from a import b"],
    )

    assert remove_marked_block(inserted, BEGIN, END).code == source


# --- parsing and checking --------------------------------------------------------------------


def test_parse_source_names_the_file_and_the_syntax_problem() -> None:
    with pytest.raises(ConfigEditError) as raised:
        parse_source("x = [\ndef broken(:\n", PATH)

    message = str(raised.value)
    assert "config/urls.py" in message.replace("\\", "/")
    assert "syntax" in message.lower()


def test_check_result_returns_valid_source_and_refuses_the_rest() -> None:
    assert check_result("x = 1\n", PATH) == "x = 1\n"
    with pytest.raises(ConfigEditError, match="does not parse"):
        check_result("x = [\n", PATH)


def test_find_import_from_returns_the_index_of_the_first_top_level_absolute_import() -> (
    None
):
    module = parse_source(
        "import os\nfrom .m import a\nfrom m import b\nfrom m import c\n"
        "def f():\n    from m import d\n",
        PATH,
    )

    assert find_import_from(module, "m") == 2


def test_find_import_from_returns_none_when_the_module_is_not_imported() -> None:
    assert (
        find_import_from(parse_source("import m\nfrom n import a\n", PATH), "m") is None
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("from m import a, b\n", {"a", "b"}, id="one-line"),
        pytest.param(
            "from m import (\n    a,\n    b,\n)\n", {"a", "b"}, id="parenthesized"
        ),
        pytest.param(
            "from m import a as x, b\n", {"a", "b"}, id="aliased-counts-the-name"
        ),
        pytest.param(
            "from m import a\nfrom m import b\n", {"a", "b"}, id="several-statements"
        ),
        pytest.param("from n import a\nimport m\n", set(), id="other-modules"),
        pytest.param("from .m import a\n", set(), id="relative-import"),
        pytest.param("def f():\n    from m import a\n", set(), id="not-top-level"),
        pytest.param("from m import *\n", set(), id="star-import"),
    ],
)
def test_imported_names_lists_the_names_imported_from_a_module(
    source: str, expected: set[str]
) -> None:
    assert imported_names(parse_source(source, PATH), "m") == expected
