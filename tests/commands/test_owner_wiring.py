"""Both wiring paths make a viewset owner-scoped; nothing else changes."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _flat(text: str) -> str:
    return " ".join(text.replace("│", " ").split())


def _invoke(*args: str) -> object:
    return runner.invoke(app, list(args))


def _project(tmp_path: Path, *, multitenancy: bool = False) -> Path:
    for args in (
        ["new", "demo", "-d", "sqlite", "--no-docker",
         "--multitenancy" if multitenancy else "--no-multitenancy",
         "--no-frontend", "--path", str(tmp_path)],
        ["add", "blog", "--path", str(tmp_path / "demo")],
        ["add-model", "blog", "Note", "--fields", "title:char,owner:fk:to=users.User",
         "--force", "--path", str(tmp_path / "demo")],
    ):  # fmt: skip
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return tmp_path / "demo"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return _project(tmp_path)


def _views(root: Path) -> str:
    text = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    ast.parse(text)
    return text


def _serializers(root: Path) -> str:
    text = (root / "apps" / "blog" / "serializers.py").read_text(encoding="utf-8")
    ast.parse(text)
    return text


def _read_only(root: Path) -> tuple[str, ...]:
    """`NoteSerializer.Meta.read_only_fields` as a tuple of names."""
    tree = ast.parse(_serializers(root))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "NoteSerializer":
            for item in ast.walk(node):
                if isinstance(item, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "read_only_fields" for t in item.targets
                ):
                    return tuple(ast.literal_eval(item.value))
    return ()


def _scoping_lines(root: Path) -> list[str]:
    return [
        line
        for line in _views(root).splitlines()
        if "OwnerScopedMixin" in line or "owner_field" in line
    ]


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".venv" not in p.parts
    }


def _owner_permission(root: Path, *extra: str) -> object:
    return _invoke(
        "add-permission", "blog", "IsOwner", "--preset", "owner", "--owner-attr", "owner",
        *extra, "--path", str(root),
    )  # fmt: skip


def test_add_permission_with_viewset_scopes_the_viewset_and_the_serializer(project: Path) -> None:
    result = _owner_permission(project, "--viewset", "Note")

    assert result.exit_code == 0, result.output
    views = _views(project)
    assert "class NoteViewSet(OwnerScopedMixin, viewsets.ModelViewSet):" in views
    assert 'owner_field = "owner"' in views
    assert "permission_classes = [IsOwner]" in views
    assert "from apps.core.ownership import OwnerScopedMixin" in views
    assert "owner" in _read_only(project)
    output = _flat(result.output)
    assert "scoped to the requesting user" in output
    assert "now read-only" in output


def test_add_permission_without_viewset_says_how_to_finish_and_changes_no_views(
    project: Path,
) -> None:
    views_before = _views(project)

    result = _owner_permission(project)

    assert result.exit_code == 0, result.output
    assert _views(project) == views_before
    output = _flat(result.output)
    assert "only checks single objects" in output
    assert "add-viewset blog YourModel --permission IsOwner --force" in output


def test_other_presets_do_not_add_the_mixin(project: Path) -> None:
    result = _invoke(
        "add-permission", "blog", "IsStaff", "--preset", "staff_or_read",
        "--viewset", "Note", "--path", str(project),
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    assert "OwnerScopedMixin" not in _views(project)
    assert "only checks single objects" not in _flat(result.output)


def test_add_viewset_with_a_generated_owner_permission_scopes_the_new_viewset(
    project: Path,
) -> None:
    assert _owner_permission(project).exit_code == 0

    result = _invoke(
        "add-viewset", "blog", "Note", "--permission", "IsOwner", "--force", "--path", str(project)
    )

    assert result.exit_code == 0, result.output
    views = _views(project)
    assert "class NoteViewSet(OwnerScopedMixin, viewsets.ModelViewSet):" in views
    assert 'owner_field = "owner"' in views
    assert "permission_classes = [IsOwner]" in views
    assert "owner" in _read_only(project)
    assert "scoped to the requesting user" in _flat(result.output)


def test_both_paths_produce_the_same_files(tmp_path: Path) -> None:
    first = _project(tmp_path / "a")
    assert _owner_permission(first, "--viewset", "Note").exit_code == 0
    second = _project(tmp_path / "b")
    assert _owner_permission(second).exit_code == 0
    assert _invoke(
        "add-viewset", "blog", "Note", "--permission", "IsOwner", "--force", "--path", str(second)
    ).exit_code == 0

    # (the two viewsets differ in unrelated stub details; the scoping must be identical)
    assert _scoping_lines(first) == _scoping_lines(second)
    assert _scoping_lines(first)
    assert _read_only(first) == _read_only(second)
    assert "owner" in _read_only(first)


def test_wiring_twice_changes_nothing_the_second_time(project: Path) -> None:
    assert _owner_permission(project, "--viewset", "Note").exit_code == 0
    first = _tree(project)

    result = _owner_permission(project, "--viewset", "Note", "--force")

    assert result.exit_code == 0, result.output
    later = _tree(project)
    unchanged = {k for k in first if k != "apps/blog/permissions.py"}  # see below
    assert {k: later[k] for k in unchanged} == {k: first[k] for k in unchanged}
    # (--force re-inserts the permission class, which adds one blank line: unrelated cosmetics)
    assert later["apps/blog/permissions.py"].replace(b"\n\n\n", b"\n\n") == first[
        "apps/blog/permissions.py"
    ].replace(b"\n\n\n", b"\n\n")
    assert _views(project).count("OwnerScopedMixin") == 2  # import + base, never duplicated
    assert _read_only(project).count("owner") == 1
    assert "already scoped" in _flat(result.output)


def test_a_permission_without_owner_attr_is_never_guessed(project: Path) -> None:
    permissions = project / "apps" / "blog" / "permissions.py"
    permissions.write_text(
        "from rest_framework.permissions import BasePermission\n\n\n"
        "class IsHandmade(BasePermission):\n    def has_permission(self, request, view):\n"
        "        return True\n",
        encoding="utf-8",
    )

    result = _invoke(
        "add-viewset", "blog", "Note", "--permission", "IsHandmade", "--force", "--path", str(project)
    )

    assert result.exit_code == 0, result.output
    assert "OwnerScopedMixin" not in _views(project)
    assert "owner" not in _read_only(project)


def test_stock_permissions_generate_exactly_what_they_did_before(project: Path) -> None:
    result = _invoke(
        "add-viewset", "blog", "Note", "--permission", "IsAdminUser", "--force", "--path", str(project)
    )

    assert result.exit_code == 0, result.output
    assert "class NoteViewSet(viewsets.ModelViewSet):" in _views(project)
    assert "owner_field" not in _views(project)


@pytest.mark.parametrize("command", ["permission", "viewset"])
def test_a_project_without_ownership_module_is_refused_and_left_untouched(
    project: Path, command: str
) -> None:
    assert _owner_permission(project).exit_code == 0
    (project / "apps" / "core" / "ownership.py").unlink()
    before = _tree(project)
    args = (
        ["add-permission", "blog", "IsOwner", "--preset", "owner", "--viewset", "Note", "--force"]
        if command == "permission"
        else ["add-viewset", "blog", "Note", "--permission", "IsOwner", "--force"]
    )

    result = _invoke(*args, "--path", str(project))

    assert result.exit_code == 1
    assert "apps/core/ownership.py" in _flat(result.output)
    assert "Traceback" not in result.output
    assert _tree(project) == before


def test_a_tenant_project_puts_the_owner_mixin_before_the_tenant_mixin(tmp_path: Path) -> None:
    root = _project(tmp_path, multitenancy=True)
    assert _invoke(
        "add-viewset", "blog", "Note", "--force", "--path", str(root)
    ).exit_code == 0
    assert "class NoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):" in _views(root)

    result = _owner_permission(root, "--viewset", "Note")

    assert result.exit_code == 0, result.output
    assert (
        "class NoteViewSet(OwnerScopedMixin, TenantScopedMixin, viewsets.ModelViewSet):"
        in _views(root)
    )


def test_a_tenant_project_scopes_a_freshly_created_viewset_in_the_right_order(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, multitenancy=True)
    assert _owner_permission(root).exit_code == 0

    result = _invoke(
        "add-viewset", "blog", "Note", "--permission", "IsOwner", "--force", "--path", str(root)
    )

    assert result.exit_code == 0, result.output
    assert (
        "class NoteViewSet(OwnerScopedMixin, TenantScopedMixin, viewsets.ModelViewSet):"
        in _views(root)
    )


def test_the_owner_attribute_not_among_the_serializer_fields_is_reported(project: Path) -> None:
    result = _invoke(
        "add-permission", "blog", "IsOwner", "--preset", "owner", "--owner-attr", "created_by",
        "--viewset", "Note", "--path", str(project),
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    assert 'owner_field = "created_by"' in _views(project)
    assert "is not one of its fields" in _flat(result.output)
