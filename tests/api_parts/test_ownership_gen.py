"""Making a viewset owner-scoped: the contract readers and `apply_owner_scoping`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from django_octave.api_parts.ownership_gen import (
    OwnershipModuleMissingError,
    OwnershipWireError,
    apply_owner_scoping,
    ensure_ownership_module,
    model_of_viewset,
    owner_attr_of_permission,
    viewset_owner_field,
)
from django_octave.api_parts.permission_gen import build_permission_class
from django_octave.models_gen.cst_util import class_exists
from django_octave.safe_names import InvalidOptionError
from django_octave.tenancy import viewset_bases

VIEWS = '''\
"""API views for notes."""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.notes.models import Note
from apps.notes.serializers import NoteSerializer


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]


class OtherViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
'''

SERIALIZERS = """\
from rest_framework import serializers

from apps.notes.models import Note


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ("id", "title", "owner", "assignee")
        read_only_fields = ("id",)
"""


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    apps = tmp_path / "apps"
    (apps / "core").mkdir(parents=True)
    (apps / "core" / "ownership.py").write_text(
        "class OwnerScopedMixin: ...\n", encoding="utf-8"
    )
    app = apps / "notes"
    app.mkdir()
    (app / "views.py").write_text(VIEWS, encoding="utf-8")
    (app / "serializers.py").write_text(SERIALIZERS, encoding="utf-8")
    return app


def _views(app: Path) -> str:
    text = (app / "views.py").read_text(encoding="utf-8")
    ast.parse(text)
    return text


def _serializers(app: Path) -> str:
    text = (app / "serializers.py").read_text(encoding="utf-8")
    ast.parse(text)
    return text


def test_viewset_bases_put_the_owner_mixin_before_the_tenant_mixin() -> None:
    assert viewset_bases(scoped=False) == "viewsets.ModelViewSet"
    assert viewset_bases(scoped=True) == "TenantScopedMixin, viewsets.ModelViewSet"
    assert (
        viewset_bases(scoped=False, owned=True)
        == "OwnerScopedMixin, viewsets.ModelViewSet"
    )
    assert (
        viewset_bases(scoped=True, owned=True)
        == "OwnerScopedMixin, TenantScopedMixin, viewsets.ModelViewSet"
    )


def test_the_generated_owner_permission_declares_its_attribute(tmp_path: Path) -> None:
    source = (
        "from rest_framework.permissions import BasePermission\n"
        + build_permission_class("IsOwner", preset="owner", owner_attr="created_by")
    )
    path = tmp_path / "permissions.py"
    path.write_text(source, encoding="utf-8")

    assert owner_attr_of_permission(path, "IsOwner") == "created_by"


def test_other_presets_and_hand_written_classes_have_no_owner_attr(
    tmp_path: Path,
) -> None:
    source = "from rest_framework.permissions import BasePermission, SAFE_METHODS\n"
    source += build_permission_class(
        "IsStaff", preset="staff_or_read", owner_attr="owner"
    )
    source += "\n\nclass Handmade(BasePermission):\n    pass\n"
    path = tmp_path / "permissions.py"
    path.write_text(source, encoding="utf-8")

    assert owner_attr_of_permission(path, "IsStaff") is None
    assert owner_attr_of_permission(path, "Handmade") is None
    assert owner_attr_of_permission(path, "Missing") is None
    assert owner_attr_of_permission(tmp_path / "nope.py", "IsOwner") is None


def test_owner_attr_is_read_per_class_not_from_a_neighbour(tmp_path: Path) -> None:
    source = 'class Plain:\n    pass\n\n\nclass IsOwner:\n    owner_attr = "owner"\n'
    path = tmp_path / "permissions.py"
    path.write_text(source, encoding="utf-8")

    assert owner_attr_of_permission(path, "Plain") is None
    assert owner_attr_of_permission(path, "IsOwner") == "owner"


def test_viewset_owner_field_and_model_readers() -> None:
    scoped = VIEWS.replace(
        "class NoteViewSet(viewsets.ModelViewSet):\n",
        'class NoteViewSet(OwnerScopedMixin, viewsets.ModelViewSet):\n    owner_field = "created_by"\n',
    )

    assert viewset_owner_field(scoped, "NoteViewSet") == "created_by"
    assert viewset_owner_field(scoped, "OtherViewSet") is None
    assert viewset_owner_field(VIEWS, "NoteViewSet") is None
    assert model_of_viewset(VIEWS, "NoteViewSet") == "Note"
    assert model_of_viewset("class FooViewSet(X):\n    pass\n", "FooViewSet") == "Foo"


def test_ensure_ownership_module_names_the_missing_file(tmp_path: Path) -> None:
    (tmp_path / "core").mkdir()

    with pytest.raises(OwnershipModuleMissingError, match=r"apps/core/ownership\.py"):
        ensure_ownership_module(tmp_path)


def test_apply_owner_scoping_wires_viewset_and_serializer(app_dir: Path) -> None:
    notes = apply_owner_scoping(
        app_dir, viewset_class="NoteViewSet", owner_attr="owner"
    )

    views = _views(app_dir)
    assert "from apps.core.ownership import OwnerScopedMixin" in views
    assert "class NoteViewSet(OwnerScopedMixin, viewsets.ModelViewSet):" in views
    assert 'owner_field = "owner"' in views
    assert viewset_owner_field(views, "NoteViewSet") == "owner"
    assert viewset_owner_field(views, "OtherViewSet") is None  # only the named viewset
    serializers = _serializers(app_dir)
    assert '"owner"' in serializers.split("read_only_fields")[1]
    assert any("scoped to the requesting user" in n for n in notes)
    assert any("now read-only" in n for n in notes)


def test_apply_owner_scoping_is_idempotent(app_dir: Path) -> None:
    apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr="owner")
    views_once = _views(app_dir)
    serializers_once = _serializers(app_dir)

    notes = apply_owner_scoping(
        app_dir, viewset_class="NoteViewSet", owner_attr="owner"
    )

    assert _views(app_dir) == views_once
    assert _serializers(app_dir) == serializers_once
    assert any("already scoped" in n for n in notes)
    assert any("already read-only" in n for n in notes)


def test_apply_owner_scoping_keeps_the_tenant_mixin_behind_the_owner_mixin(
    app_dir: Path,
) -> None:
    path = app_dir / "views.py"
    path.write_text(
        VIEWS.replace(
            "class NoteViewSet(viewsets.ModelViewSet):",
            "class NoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):",
        ),
        encoding="utf-8",
    )

    apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr="owner")

    assert (
        "class NoteViewSet(OwnerScopedMixin, TenantScopedMixin, viewsets.ModelViewSet):"
        in _views(app_dir)
    )


def test_apply_owner_scoping_can_change_the_owner_attribute(app_dir: Path) -> None:
    apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr="owner")

    apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr="assignee")

    assert viewset_owner_field(_views(app_dir), "NoteViewSet") == "assignee"
    assert _views(app_dir).count("owner_field") == 1


def test_a_missing_serializer_is_reported_but_the_viewset_is_still_scoped(
    app_dir: Path,
) -> None:
    (app_dir / "serializers.py").unlink()

    notes = apply_owner_scoping(
        app_dir, viewset_class="NoteViewSet", owner_attr="owner"
    )

    assert viewset_owner_field(_views(app_dir), "NoteViewSet") == "owner"
    assert any("not found: make 'owner' read-only" in n for n in notes)


def test_an_owner_attribute_that_is_not_a_serializer_field_is_left_alone(
    app_dir: Path,
) -> None:
    before = _serializers(app_dir)

    notes = apply_owner_scoping(
        app_dir, viewset_class="NoteViewSet", owner_attr="created_by"
    )

    assert _serializers(app_dir) == before
    assert any("is not one of its fields" in n for n in notes)


def test_apply_owner_scoping_refuses_a_project_without_the_mixin_module(
    app_dir: Path,
) -> None:
    (app_dir.parent / "core" / "ownership.py").unlink()
    before = _views(app_dir)

    with pytest.raises(OwnershipModuleMissingError):
        apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr="owner")

    assert _views(app_dir) == before


@pytest.mark.parametrize("attr", ["", "class", 'x", y=("', "a-b"])
def test_apply_owner_scoping_validates_the_attribute_first(
    app_dir: Path, attr: str
) -> None:
    before = _views(app_dir)

    with pytest.raises(InvalidOptionError):
        apply_owner_scoping(app_dir, viewset_class="NoteViewSet", owner_attr=attr)

    assert _views(app_dir) == before


def test_apply_owner_scoping_reports_an_unknown_viewset(app_dir: Path) -> None:
    with pytest.raises(OwnershipWireError, match="NopeViewSet not found"):
        apply_owner_scoping(app_dir, viewset_class="NopeViewSet", owner_attr="owner")

    assert not class_exists(_views(app_dir), "NopeViewSet")
