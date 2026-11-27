"""libcst helpers that add a base class, a class attribute and a read-only serializer field."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from django_octave.models_gen.cst_util import (
    ensure_class_base,
    ensure_read_only_field,
    set_class_attribute,
)
from django_octave.models_gen.writer import ModelWriteError


def _write(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "mod.py"
    path.write_text(source, encoding="utf-8")
    return path


def _text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    ast.parse(text)  # every edit must leave valid Python
    return text


# --- ensure_class_base -----------------------------------------------------------------


def test_base_is_inserted_first(tmp_path: Path) -> None:
    path = _write(tmp_path, "class V(viewsets.ModelViewSet):\n    pass\n")

    assert ensure_class_base(path, "V", "OwnerScopedMixin") is True

    assert "class V(OwnerScopedMixin, viewsets.ModelViewSet):" in _text(path)


def test_base_goes_before_an_existing_mixin_and_is_idempotent(tmp_path: Path) -> None:
    path = _write(
        tmp_path, "class V(TenantScopedMixin, viewsets.ModelViewSet):\n    pass\n"
    )

    assert ensure_class_base(path, "V", "OwnerScopedMixin") is True
    assert ensure_class_base(path, "V", "OwnerScopedMixin") is False

    text = _text(path)
    assert (
        "class V(OwnerScopedMixin, TenantScopedMixin, viewsets.ModelViewSet):" in text
    )
    assert text.count("OwnerScopedMixin") == 1


def test_base_can_be_appended_and_other_classes_are_untouched(tmp_path: Path) -> None:
    path = _write(tmp_path, "class A(X):\n    pass\n\n\nclass B(X):\n    pass\n")

    ensure_class_base(path, "B", "Mixin", first=False)

    text = _text(path)
    assert "class A(X):" in text
    assert "class B(X, Mixin):" in text


def test_base_edit_keeps_comments_and_decorators(tmp_path: Path) -> None:
    source = (
        "# header comment\n"
        "@decorator(tags=['x'])\n"
        "class V(\n    viewsets.ModelViewSet,  # the base\n):\n"
        "    queryset = Item.objects.all()  # keep me\n"
    )
    path = _write(tmp_path, source)

    ensure_class_base(path, "V", "OwnerScopedMixin")

    text = _text(path)
    assert "# header comment" in text
    assert "@decorator(tags=['x'])" in text
    assert "# the base" in text
    assert "# keep me" in text
    assert "OwnerScopedMixin" in text


def test_base_edit_on_an_unparsable_file_names_the_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "class V(:\n")

    with pytest.raises(ModelWriteError, match=r"mod\.py"):
        ensure_class_base(path, "V", "OwnerScopedMixin")


# --- set_class_attribute ---------------------------------------------------------------


def test_attribute_is_inserted_before_queryset(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'class V:\n    """Doc."""\n\n    queryset = Item.objects.all()\n    serializer_class = S\n',
    )

    assert set_class_attribute(path, "V", "owner_field", '"owner"') is True

    text = _text(path)
    assert text.index('owner_field = "owner"') < text.index("queryset")
    assert '"""Doc."""' in text


def test_attribute_without_queryset_goes_after_the_docstring(tmp_path: Path) -> None:
    path = _write(
        tmp_path, 'class V:\n    """Doc."""\n\n    def go(self):\n        pass\n'
    )

    set_class_attribute(path, "V", "owner_field", '"owner"')

    text = _text(path)
    assert text.index('"""Doc."""') < text.index("owner_field") < text.index("def go")


def test_attribute_is_replaced_not_duplicated(tmp_path: Path) -> None:
    path = _write(tmp_path, 'class V:\n    owner_field = "owner"\n    queryset = Q\n')

    assert set_class_attribute(path, "V", "owner_field", '"created_by"') is True
    assert set_class_attribute(path, "V", "owner_field", '"created_by"') is False

    text = _text(path)
    assert text.count("owner_field") == 1
    assert 'owner_field = "created_by"' in text


def test_attribute_on_another_class_is_untouched(tmp_path: Path) -> None:
    path = _write(tmp_path, "class A:\n    x = 1\n\n\nclass B:\n    x = 2\n")

    set_class_attribute(path, "B", "owner_field", '"owner"')

    text = _text(path)
    assert text.count("owner_field") == 1
    assert text.index("class B") < text.index("owner_field")


# --- ensure_read_only_field --------------------------------------------------------------

SERIALIZER = """\
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ("id", "title", "owner", "created_at")
        read_only_fields = ("id", "created_at",)
"""


def test_field_is_added_to_a_tuple_with_trailing_comma(tmp_path: Path) -> None:
    path = _write(tmp_path, SERIALIZER)

    assert ensure_read_only_field(path, "NoteSerializer", "owner") == "added"

    text = _text(path)
    assert ast.literal_eval(text.split("read_only_fields = ")[1].splitlines()[0]) == (
        "id",
        "created_at",
        "owner",
    )


def test_field_is_added_to_a_list_and_to_a_tuple_without_trailing_comma(
    tmp_path: Path,
) -> None:
    for existing, expected in (
        ('["id"]', ["id", "owner"]),
        ('("id")', None),  # a parenthesised string is not a tuple: refuse to guess
    ):
        path = _write(
            tmp_path,
            SERIALIZER.replace('("id", "created_at",)', existing),
        )
        if expected is None:
            with pytest.raises(ModelWriteError, match="by hand"):
                ensure_read_only_field(path, "NoteSerializer", "owner")
        else:
            assert ensure_read_only_field(path, "NoteSerializer", "owner") == "added"
            line = _text(path).split("read_only_fields = ")[1].splitlines()[0]
            assert ast.literal_eval(line) == expected


def test_field_already_read_only_is_left_alone(tmp_path: Path) -> None:
    path = _write(
        tmp_path, SERIALIZER.replace('"created_at",)', '"created_at", "owner")')
    )
    before = path.read_text(encoding="utf-8")

    assert ensure_read_only_field(path, "NoteSerializer", "owner") == "present"

    assert path.read_text(encoding="utf-8") == before


def test_read_only_fields_is_created_when_absent(tmp_path: Path) -> None:
    source = SERIALIZER.replace(
        '        read_only_fields = ("id", "created_at",)\n', ""
    )
    path = _write(tmp_path, source)

    assert ensure_read_only_field(path, "NoteSerializer", "owner") == "added"

    text = _text(path)
    assert 'read_only_fields = ("owner",)' in text
    assert text.index("fields =") < text.index("read_only_fields")


def test_field_missing_from_explicit_fields_changes_nothing(tmp_path: Path) -> None:
    path = _write(tmp_path, SERIALIZER.replace('"owner", ', ""))
    before = path.read_text(encoding="utf-8")

    assert ensure_read_only_field(path, "NoteSerializer", "owner") == "not-a-field"

    assert path.read_text(encoding="utf-8") == before


def test_all_fields_serializer_gets_the_read_only_entry(tmp_path: Path) -> None:
    source = (
        "class NoteSerializer(serializers.ModelSerializer):\n"
        "    class Meta:\n"
        "        model = Note\n"
        '        fields = "__all__"\n'
    )
    path = _write(tmp_path, source)

    assert ensure_read_only_field(path, "NoteSerializer", "owner") == "added"

    assert 'read_only_fields = ("owner",)' in _text(path)


def test_read_only_edit_errors_name_the_problem(tmp_path: Path) -> None:
    unparsable = _write(tmp_path, "class NoteSerializer(:\n")
    with pytest.raises(ModelWriteError, match=r"mod\.py"):
        ensure_read_only_field(unparsable, "NoteSerializer", "owner")

    missing = _write(tmp_path, "class Other:\n    pass\n")
    with pytest.raises(ModelWriteError, match="NoteSerializer not found"):
        ensure_read_only_field(missing, "NoteSerializer", "owner")

    computed = _write(
        tmp_path, SERIALIZER.replace('("id", "created_at",)', "BASE + ('x',)")
    )
    with pytest.raises(ModelWriteError, match="plain tuple/list"):
        ensure_read_only_field(computed, "NoteSerializer", "owner")
