"""Tests for ``resolve_related_names``: distinct reverse names for clashing relations."""

from __future__ import annotations

import re

import pytest

from django_octave.fields.parser import FieldSpec, parse_field
from django_octave.fields.related import ResolvedFields, resolve_related_names

USER = "users.User"


def _specs(*declarations: str) -> list[FieldSpec]:
    return [parse_field(d) for d in declarations]


def _names(resolved: ResolvedFields) -> dict[str, str | None]:
    return {f.name: f.related_name for f in resolved.fields}


def _resolve(
    *declarations: str, app: str = "notes", model: str = "Note"
) -> ResolvedFields:
    return resolve_related_names(_specs(*declarations), app=app, model=model)


@pytest.mark.parametrize(
    ("declarations", "expected"),
    [
        pytest.param(
            (f"owner:fk:to={USER}", f"assignee:fk:to={USER}"),
            {"owner": "note_owner", "assignee": "note_assignee"},
            id="two-fk",
        ),
        pytest.param(
            (f"owner:fk:to={USER}", f"watchers:m2m:to={USER}"),
            {"owner": "note_owner", "watchers": "note_watchers"},
            id="fk-and-m2m",
        ),
        pytest.param(
            (f"owner:fk:to={USER}", f"profile:o2o:to={USER}"),
            {"owner": "note_owner", "profile": "note_profile"},
            id="fk-and-o2o-share-the-query-name",
        ),
        pytest.param(
            (f"editors:m2m:to={USER}", f"viewers:m2m:to={USER}"),
            {"editors": "note_editors", "viewers": "note_viewers"},
            id="two-m2m",
        ),
        pytest.param(
            (f"primary:o2o:to={USER}", f"backup:o2o:to={USER}"),
            {"primary": "note_primary", "backup": "note_backup"},
            id="two-o2o",
        ),
        pytest.param(
            (f"a:fk:to={USER}", f"b:fk:to={USER}", f"c:m2m:to={USER}"),
            {"a": "note_a", "b": "note_b", "c": "note_c"},
            id="three-unnamed",
        ),
    ],
)
def test_resolve_gives_each_clashing_relation_its_own_name(
    declarations: tuple[str, ...], expected: dict[str, str]
) -> None:
    resolved = _resolve(*declarations)

    assert _names(resolved) == expected
    assert resolved.generated == expected


@pytest.mark.parametrize(
    "target_pair",
    [
        ("Author", "Author"),
        ("Author", "notes.Author"),
        ("notes.Author", "Author"),
        ("notes.Author", "notes.Author"),
    ],
)
def test_resolve_bare_and_app_qualified_own_app_target_are_the_same_target(
    target_pair: tuple[str, str],
) -> None:
    first, second = target_pair

    resolved = _resolve(f"writer:fk:to={first}", f"editor:fk:to={second}")

    assert resolved.generated == {"writer": "note_writer", "editor": "note_editor"}


def test_resolve_bare_target_and_another_apps_model_are_different_targets() -> None:
    resolved = _resolve("writer:fk:to=Author", "editor:fk:to=blog.Author")

    assert resolved.generated == {}
    assert _names(resolved) == {"writer": None, "editor": None}


@pytest.mark.parametrize("target", ["Note", "notes.Note"])
def test_resolve_self_relation_declared_twice_is_a_clash(target: str) -> None:
    resolved = _resolve(f"parent:fk:to={target}", f"original:fk:to={target}")

    assert resolved.generated == {"parent": "note_parent", "original": "note_original"}


def test_resolve_single_relation_is_untouched() -> None:
    specs = _specs("title:char", f"owner:fk:to={USER}")

    resolved = resolve_related_names(specs, app="notes", model="Note")

    assert resolved.fields == specs
    assert resolved.generated == {}


def test_resolve_relations_to_different_targets_are_untouched() -> None:
    resolved = _resolve(
        f"owner:fk:to={USER}", "category:fk:to=Category", "tags:m2m:to=Tag"
    )

    assert resolved.generated == {}
    assert set(_names(resolved).values()) == {None}


def test_resolve_explicit_name_is_kept_and_does_not_count_as_a_clash() -> None:
    resolved = _resolve(
        f"owner:fk:to={USER}:related_name=owned_notes", f"assignee:fk:to={USER}"
    )

    assert _names(resolved) == {"owner": "owned_notes", "assignee": None}
    assert resolved.generated == {}


def test_resolve_hidden_reverse_relation_does_not_count_as_a_clash() -> None:
    resolved = _resolve(f"owner:fk:to={USER}:related_name=+", f"assignee:fk:to={USER}")

    assert _names(resolved) == {"owner": "+", "assignee": None}
    assert resolved.generated == {}


def test_resolve_names_only_the_unnamed_fields_of_a_clash() -> None:
    resolved = _resolve(
        f"a:fk:to={USER}:related_name=mine", f"b:fk:to={USER}", f"c:fk:to={USER}"
    )

    assert _names(resolved) == {"a": "mine", "b": "note_b", "c": "note_c"}
    assert resolved.generated == {"b": "note_b", "c": "note_c"}


def test_resolve_each_target_group_is_named_on_its_own() -> None:
    resolved = _resolve(
        f"owner:fk:to={USER}",
        f"assignee:fk:to={USER}",
        "tags:m2m:to=Tag",
        "labels:m2m:to=Tag",
        "category:fk:to=Category",
    )

    assert resolved.generated == {
        "owner": "note_owner",
        "assignee": "note_assignee",
        "tags": "note_tags",
        "labels": "note_labels",
    }
    assert _names(resolved)["category"] is None


@pytest.mark.parametrize(
    ("taken", "expected_owner"),
    [
        (("note_owner",), "note_owner_2"),
        (("note_owner", "note_owner_2"), "note_owner_3"),
    ],
)
def test_resolve_generated_name_that_collides_with_an_explicit_one_gets_a_suffix(
    taken: tuple[str, ...], expected_owner: str
) -> None:
    explicit = [
        f"x{i}:fk:to=Other{i}:related_name={name}" for i, name in enumerate(taken)
    ]

    resolved = _resolve(*explicit, f"owner:fk:to={USER}", f"assignee:fk:to={USER}")

    assert resolved.generated == {"owner": expected_owner, "assignee": "note_assignee"}


@pytest.mark.parametrize(
    ("model", "prefix"),
    [
        ("Note", "note"),
        ("BlogPost", "blog_post"),
        ("HTTPLog", "http_log"),
        ("Item2", "item2"),
    ],
)
def test_resolve_names_start_with_the_snake_case_model_name(
    model: str, prefix: str
) -> None:
    resolved = _resolve(f"a:fk:to={USER}", f"b:fk:to={USER}", model=model)

    assert resolved.generated == {"a": f"{prefix}_a", "b": f"{prefix}_b"}


def test_resolve_cleans_underscores_so_django_accepts_the_reverse_query_name() -> None:
    resolved = _resolve(f"owner_:fk:to={USER}", f"a__b:fk:to={USER}")

    assert resolved.generated == {"owner_": "note_owner", "a__b": "note_a_b"}


def test_resolve_cleaning_that_makes_two_names_equal_adds_a_suffix() -> None:
    resolved = _resolve(f"a__b:fk:to={USER}", f"a_b:fk:to={USER}")

    assert resolved.generated == {"a__b": "note_a_b", "a_b": "note_a_b_2"}


@pytest.mark.parametrize("model", ["Note", "BlogPost", "HTTPLog"])
def test_resolve_generated_names_are_valid_reverse_query_names(model: str) -> None:
    resolved = _resolve(
        f"owner_:fk:to={USER}", f"a__b:fk:to={USER}", f"c:m2m:to={USER}", model=model
    )

    for name in resolved.generated.values():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name)
        assert not name.endswith("_")
        assert "__" not in name


def test_resolve_is_deterministic_and_keeps_the_order() -> None:
    declarations = (
        "title:char",
        f"owner:fk:to={USER}",
        "n:int",
        f"assignee:fk:to={USER}",
    )

    first = _resolve(*declarations)
    second = _resolve(*declarations)

    assert first == second
    assert [f.name for f in first.fields] == ["title", "owner", "n", "assignee"]
    assert list(first.generated) == ["owner", "assignee"]


def test_resolve_leaves_every_other_attribute_of_a_spec_alone() -> None:
    resolved = _resolve(
        f"owner:fk:to={USER}:on_delete=set_null", f"assignee:fk:to={USER}:unique"
    )

    owner, assignee = resolved.fields
    assert (owner.on_delete, owner.null, owner.blank) == ("set_null", True, True)
    assert (assignee.unique, assignee.on_delete) == (True, "cascade")
    assert (owner.related_to, assignee.related_to) == (USER, USER)


def test_resolve_does_not_change_the_input() -> None:
    specs = _specs(f"owner:fk:to={USER}", f"assignee:fk:to={USER}")
    before = list(specs)

    resolve_related_names(specs, app="notes", model="Note")

    assert specs == before
    assert all(s.related_name is None for s in specs)


def test_resolve_empty_and_scalar_only_fields() -> None:
    assert _resolve().fields == []
    assert _resolve("title:char", "n:int").generated == {}
