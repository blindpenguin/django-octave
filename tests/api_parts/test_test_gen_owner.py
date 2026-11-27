"""Generated API tests for owner-scoped viewsets."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.api_parts.test_gen import build_api_test_source
from django_octave.cli import app

runner = CliRunner()

OWNER_TESTS = [
    "test_list_only_returns_own_rows",
    "test_other_users_row_is_not_found",
    "test_create_sets_the_owner_to_the_requester_and_ignores_the_payload",
    "test_update_cannot_change_the_owner",
]


def _source(**kwargs: object) -> str:
    source = build_api_test_source(app_name="notes", model_name="Note", **kwargs)  # type: ignore[arg-type]
    ast.parse(source)
    return source


def test_plain_owner_scoped_source_has_the_four_isolation_tests() -> None:
    source = _source(owner_field="owner")

    for name in OWNER_TESTS:
        assert f"def {name}(" in source
    assert "NoteFactory(owner=user)" in source
    assert "NoteFactory(owner=UserFactory())" in source
    assert "Note.objects.get(" in source
    assert "tenant_client" not in source
    assert "tenant=tenant" not in source
    assert "status.HTTP_404_NOT_FOUND" in source


def test_tenant_owner_scoped_source_uses_the_tenant_fixtures() -> None:
    source = _source(tenant_aware=True, owner_field="owner")

    for name in OWNER_TESTS:
        assert f"def {name}(" in source
    assert "tenant_client, tenant, user" in source
    assert "NoteFactory(tenant=tenant, owner=user)" in source
    assert "NoteFactory(tenant=tenant, owner=UserFactory())" in source
    assert "Note.all_objects.get(" in source
    assert "pytest.mark.skip" not in source


def test_the_declared_owner_field_is_used_everywhere() -> None:
    source = _source(owner_field="created_by", owner_kw="assignee=user")

    assert "NoteFactory(created_by=user)" in source  # not the heuristic's assignee
    assert "assignee=user" not in source
    assert '"created_by"' in source
    assert "created.created_by == user" in source


def test_the_create_test_skips_instead_of_guessing_when_related_objects_are_needed() -> (
    None
):
    source = _source(owner_field="owner")

    assert "pytest.skip(" in source
    assert "isinstance(value, Model)" in source


@pytest.mark.parametrize("tenant_aware", [False, True])
def test_without_owner_field_the_output_has_no_owner_tests(tenant_aware: bool) -> None:
    source = _source(tenant_aware=tenant_aware, owner_kw="owner=user")

    for name in OWNER_TESTS:
        assert name not in source
    assert "UserFactory" not in source
    assert "import factory" not in source


def test_imports_are_present_and_ordered() -> None:
    source = _source(owner_field="owner")
    header = source.split("\n\n\n")[0]

    for needed in (
        "import factory",
        "from django.db.models import Model",
        "from apps.notes.models import Note",
        "from tests.factories.notes_note import NoteFactory",
        "from tests.factories.user import UserFactory",
    ):
        assert needed in header
    assert header.index("notes_note import") < header.index("factories.user import")


def _project(tmp_path: Path, *, wire_owner: bool) -> Path:
    root = tmp_path / "demo"
    steps = [
        ["new", "demo", "-d", "sqlite", "--no-docker", "--no-multitenancy", "--no-frontend",
         "--path", str(tmp_path)],
        ["add", "notes", "--model", "Note", "--path", str(root)],
        ["add-model", "notes", "Note", "--fields", "title:char,owner:fk:to=users.User",
         "--force", "--path", str(root)],
    ]  # fmt: skip
    if wire_owner:
        steps.append(
            [
                "add-permission",
                "notes",
                "IsOwner",
                "--preset",
                "owner",
                "--owner-attr",
                "owner",
                "--viewset",
                "Note",
                "--path",
                str(root),
            ]
        )
    for args in steps:
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return root


def test_add_test_writes_owner_tests_only_for_owner_scoped_viewsets(
    tmp_path: Path,
) -> None:
    scoped = _project(tmp_path / "s", wire_owner=True)
    plain = _project(tmp_path / "p", wire_owner=False)

    for root in (scoped, plain):
        result = runner.invoke(
            app, ["add-test", "notes", "Note", "--force", "--path", str(root)]
        )
        assert result.exit_code == 0, result.output

    scoped_tests = (scoped / "tests" / "test_notes_note_api.py").read_text(
        encoding="utf-8"
    )
    plain_tests = (plain / "tests" / "test_notes_note_api.py").read_text(
        encoding="utf-8"
    )
    ast.parse(scoped_tests)
    ast.parse(plain_tests)
    for name in OWNER_TESTS:
        assert f"def {name}(" in scoped_tests
        assert name not in plain_tests
    assert (
        "NoteFactory(owner=user)" in scoped_tests
    )  # smoke tests also create owned rows
