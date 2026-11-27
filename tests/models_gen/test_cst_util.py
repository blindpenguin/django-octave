"""Unit tests for cst_util method upsert helpers."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from django_octave.models_gen.cst_util import (
    method_exists,
    upsert_class,
    upsert_method,
)
from django_octave.models_gen.writer import ModelWriteError

SAMPLE = '''"""API views."""

from rest_framework import viewsets

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def list(self, request):
        return super().list(request)
'''

METHOD = """
@action(detail=True, methods=["post"])
def publish(self, request, pk=None):
    obj = self.get_object()
    return Response({"id": obj.pk})
"""


def test_method_exists() -> None:
    assert method_exists(SAMPLE, "PostViewSet", "list")
    assert not method_exists(SAMPLE, "PostViewSet", "publish")
    assert not method_exists(SAMPLE, "OtherViewSet", "list")


def test_upsert_method_append_and_force(tmp_path: Path) -> None:
    path = tmp_path / "views.py"
    path.write_text(SAMPLE, encoding="utf-8")
    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD,
        force=False,
        header_imports=[
            "from rest_framework.decorators import action\n",
            "from rest_framework.response import Response\n",
        ],
    )
    text = path.read_text(encoding="utf-8")
    assert "def publish" in text
    assert "from rest_framework.decorators import action" in text
    assert method_exists(text, "PostViewSet", "publish")

    # Without force: leave existing method body
    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD.replace("obj.pk", '"skip"'),
        force=False,
        header_imports=[],
    )
    assert '"skip"' not in path.read_text(encoding="utf-8")

    upsert_method(
        path,
        "PostViewSet",
        "publish",
        METHOD.replace("obj.pk", '"forced"'),
        force=True,
        header_imports=[],
    )
    text = path.read_text(encoding="utf-8")
    assert text.count("def publish") == 1
    assert '"forced"' in text


def test_upsert_method_missing_class(tmp_path: Path) -> None:
    path = tmp_path / "views.py"
    path.write_text("from rest_framework import viewsets\n", encoding="utf-8")
    with pytest.raises(ModelWriteError, match="PostViewSet"):
        upsert_method(
            path,
            "PostViewSet",
            "publish",
            METHOD,
            force=False,
            header_imports=[],
        )


def test_upsert_class_with_unparsable_generated_source_names_the_file(
    tmp_path: Path,
) -> None:
    from django_octave.models_gen.cst_util import upsert_class

    target = tmp_path / "views.py"
    target.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(
        ModelWriteError, match=r"Could not generate Broken for .*views\.py"
    ):
        upsert_class(
            target,
            "Broken",
            "class Broken(:\n    pass\n",
            force=False,
            header_imports=[],
        )

    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_upsert_method_with_unparsable_generated_source_names_the_file(
    tmp_path: Path,
) -> None:
    from django_octave.models_gen.cst_util import upsert_method

    target = tmp_path / "views.py"
    target.write_text("class A:\n    pass\n", encoding="utf-8")

    with pytest.raises(
        ModelWriteError, match=r"Could not generate method go for .*views\.py"
    ):
        upsert_method(
            target,
            "A",
            "go",
            "def go(self:\n    pass\n",
            force=False,
            header_imports=[],
        )


# --- replacing a class with --force keeps it where it is ---------------------------------


def _klass(name: str, marker: str = "old") -> str:
    return f'class {name}:\n    marker = "{marker}"\n'


def _join_blocks(*blocks: str) -> str:
    """A module whose top-level blocks are separated by exactly two blank lines."""
    return "from x import y\n" + "".join(f"\n\n{block}" for block in blocks)


def _class_order(text: str) -> list[str]:
    return [n.name for n in ast.parse(text).body if isinstance(n, ast.ClassDef)]


def _upsert_text(
    tmp_path: Path,
    source: str,
    name: str,
    *,
    force: bool,
    before: str | None = None,
    class_src: str | None = None,
) -> str:
    target = tmp_path / "views.py"
    target.write_text(source, encoding="utf-8")
    upsert_class(
        target,
        name,
        class_src if class_src is not None else _klass(name, "new"),
        force=force,
        header_imports=[],
        before=before,
    )
    return target.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["A", "B", "C"])
def test_upsert_class_force_replaces_in_place_and_leaves_the_rest_byte_identical(
    tmp_path: Path, name: str
) -> None:
    blocks = {n: _klass(n) for n in "ABC"}
    source = _join_blocks(*blocks.values())
    expected = _join_blocks(*({**blocks, name: _klass(name, "new")}).values())

    text = _upsert_text(tmp_path, source, name, force=True)

    assert text == expected
    assert _class_order(text) == ["A", "B", "C"]


def test_upsert_class_force_keeps_the_comment_above_the_replaced_class(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("A"), "# keep me\n" + _klass("B"), _klass("C"))
    expected = _join_blocks(
        _klass("A"), "# keep me\n" + _klass("B", "new"), _klass("C")
    )

    assert _upsert_text(tmp_path, source, "B", force=True) == expected


def test_upsert_class_force_does_not_change_the_blank_lines_above_the_class(
    tmp_path: Path,
) -> None:
    # A hand-formatted file with a single blank line is left as it is.
    source = (
        "from x import y\n\n" + _klass("A") + "\n" + _klass("B") + "\n\n" + _klass("C")
    )
    expected = (
        "from x import y\n\n"
        + _klass("A")
        + "\n"
        + _klass("B", "new")
        + "\n\n"
        + _klass("C")
    )

    assert _upsert_text(tmp_path, source, "B", force=True) == expected


def test_upsert_class_force_replaces_every_statement_of_the_addition_in_place(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("A"), _klass("B"), _klass("C"))
    class_src = _klass("B", "new") + "\nHELPER = 1\n"

    text = _upsert_text(tmp_path, source, "B", force=True, class_src=class_src)

    assert _class_order(text) == ["A", "B", "C"]
    assert text.index("HELPER = 1") < text.index("class C")
    assert text.index("class B") < text.index("HELPER = 1")


def test_upsert_class_force_with_anchor_keeps_a_class_that_is_already_before_it(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("Helper"), _klass("Other"), _klass("Parent"))
    expected = _join_blocks(_klass("Helper", "new"), _klass("Other"), _klass("Parent"))

    text = _upsert_text(tmp_path, source, "Helper", force=True, before="Parent")

    assert text == expected


def test_upsert_class_force_with_anchor_moves_a_class_that_is_after_it(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("Parent"), _klass("Other"), _klass("Helper"))

    text = _upsert_text(tmp_path, source, "Helper", force=True, before="Parent")

    assert _class_order(text) == ["Helper", "Parent", "Other"]
    assert 'marker = "new"' in text


def test_upsert_class_inserts_a_missing_class_before_the_anchor_with_two_blank_lines(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("Parent"))

    text = _upsert_text(tmp_path, source, "Helper", force=False, before="Parent")

    assert text == _join_blocks(_klass("Helper", "new"), _klass("Parent"))


def test_upsert_class_appends_a_missing_class_with_two_blank_lines(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("A"), _klass("B"))

    text = _upsert_text(tmp_path, source, "C", force=False)

    assert text == _join_blocks(_klass("A"), _klass("B"), _klass("C", "new"))


def test_upsert_class_without_force_leaves_an_existing_class_alone(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("A"), _klass("B"))

    assert _upsert_text(tmp_path, source, "A", force=False) == source


def test_upsert_class_without_force_still_moves_a_class_before_its_anchor(
    tmp_path: Path,
) -> None:
    source = _join_blocks(_klass("Parent"), _klass("Helper"))

    text = _upsert_text(tmp_path, source, "Helper", force=False, before="Parent")

    assert _class_order(text) == ["Helper", "Parent"]
    assert 'marker = "old"' in text
