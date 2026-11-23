"""Generated viewsets inherit TenantScopedMixin in multitenancy projects only."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.api_parts.viewset_gen import (
    ViewSetOptions,
    build_viewset_class,
    write_viewset,
)
from django_octave.cli import app
from django_octave.frontend_gen.crud_discover import discover_app_resources
from django_octave.inspect.model_fields import inspect_model_fields
from django_octave.tenancy import TenancyModuleMissingError, viewset_bases

runner = CliRunner()

MIXIN_CLASS = "class NoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):"
MIXIN_IMPORT = "from apps.core.tenancy import TenantScopedMixin"

TENANT_MODEL = '''
from django.db import models
from apps.core.models import TenantAwareModel


class Note(TenantAwareModel):
    name = models.CharField(max_length=255)
'''


def _project(tmp_path: Path, *, multitenancy: bool) -> Path:
    result = runner.invoke(
        app,
        [
            "new", "proj", "-d", "sqlite", "--no-docker", "--no-frontend",
            "--multitenancy" if multitenancy else "--no-multitenancy",
            "--path", str(tmp_path),
        ],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    return tmp_path / "proj"


def _views(root: Path, app_name: str = "notes") -> str:
    return (root / "apps" / app_name / "views.py").read_text(encoding="utf-8")


def test_viewset_bases_plain_and_scoped() -> None:
    assert viewset_bases(scoped=False) == "viewsets.ModelViewSet"
    assert viewset_bases(scoped=True) == "TenantScopedMixin, viewsets.ModelViewSet"


def test_add_multitenancy_app_viewset_is_scoped(tmp_path: Path) -> None:
    root = _project(tmp_path, multitenancy=True)
    result = runner.invoke(app, ["add", "notes", "--path", str(root)])
    assert result.exit_code == 0, result.output
    views = _views(root)
    ast.parse(views)
    assert MIXIN_CLASS in views
    assert MIXIN_IMPORT in views
    assert "queryset = Note.objects.all()" in views


def test_add_plain_app_viewset_is_unchanged(tmp_path: Path) -> None:
    root = _project(tmp_path, multitenancy=False)
    result = runner.invoke(app, ["add", "notes", "--path", str(root)])
    assert result.exit_code == 0, result.output
    views = _views(root)
    assert "class NoteViewSet(viewsets.ModelViewSet):" in views
    assert "tenancy" not in views
    assert "TenantScopedMixin" not in views


def test_add_model_in_multitenancy_project_scopes_new_viewset(tmp_path: Path) -> None:
    root = _project(tmp_path, multitenancy=True)
    assert runner.invoke(app, ["add", "notes", "--path", str(root)]).exit_code == 0
    result = runner.invoke(app, ["add-model", "notes", "Tag", "--path", str(root)])
    assert result.exit_code == 0, result.output
    views = _views(root)
    ast.parse(views)
    assert "class TagViewSet(TenantScopedMixin, viewsets.ModelViewSet):" in views
    assert views.count(MIXIN_IMPORT) == 1


def test_add_in_old_multitenancy_project_fails_with_actionable_error(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, multitenancy=True)
    (root / "apps" / "core" / "tenancy.py").unlink()  # project from before the fix
    result = runner.invoke(app, ["add", "notes", "--path", str(root)])
    assert result.exit_code == 1
    assert "tenancy.py" in result.output
    assert not (root / "apps" / "notes").exists()


def test_write_viewset_scoped_for_tenant_aware_model(tmp_path: Path) -> None:
    apps = tmp_path / "apps"
    app_dir = apps / "notes"
    app_dir.mkdir(parents=True)
    (apps / "core").mkdir()
    (apps / "core" / "tenancy.py").write_text("", encoding="utf-8")
    (app_dir / "models.py").write_text(TENANT_MODEL, encoding="utf-8")
    info = inspect_model_fields(TENANT_MODEL, "Note")

    views_path, _ = write_viewset(
        app_dir,
        options=ViewSetOptions(app_name="notes", model_name="Note", use_multitenancy=True),
        info=info,
    )

    views = views_path.read_text(encoding="utf-8")
    ast.parse(views)
    assert MIXIN_CLASS in views
    assert MIXIN_IMPORT in views


def test_write_viewset_requires_tenancy_module(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "notes"
    app_dir.mkdir(parents=True)
    (app_dir / "models.py").write_text(TENANT_MODEL, encoding="utf-8")
    info = inspect_model_fields(TENANT_MODEL, "Note")

    with pytest.raises(TenancyModuleMissingError, match="tenancy.py"):
        write_viewset(
            app_dir,
            options=ViewSetOptions(
                app_name="notes", model_name="Note", use_multitenancy=True
            ),
            info=info,
        )


def test_build_viewset_class_scoped_keeps_queryset_line() -> None:
    src = build_viewset_class(
        "Note", permission="IsAuthenticated", filters=[], search=[], ordering=[],
        tag="note", scoped=True,
    )  # fmt: skip
    assert MIXIN_CLASS in src
    assert "queryset = Note.objects.all()" in src


def test_crud_discovery_still_finds_scoped_viewset(tmp_path: Path) -> None:
    root = _project(tmp_path, multitenancy=True)
    assert runner.invoke(app, ["add", "notes", "--path", str(root)]).exit_code == 0
    resources = discover_app_resources(root, "notes")
    assert [r.model_name for r in resources] == ["Note"]
