"""CLI tests for django-octave add-permission."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_post(tmp_path: Path, *, multitenancy: bool = False) -> Path:
    mt = ["--multitenancy"] if multitenancy else ["--no-multitenancy"]
    assert (
        runner.invoke(
            app,
            [
                "new",
                "proj",
                "-d",
                "sqlite",
                "--no-docker",
                *mt,
                "--no-frontend",
                "--path",
                str(tmp_path),
            ],
        ).exit_code
        == 0
    )
    root = tmp_path / "proj"
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "add-model",
                "blog",
                "Post",
                "--field",
                "title:char:max=200",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    return root


def test_add_permission_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-permission" in result.stdout
    result = runner.invoke(app, ["add-permission", "--help"])
    assert result.exit_code == 0
    assert "--preset" in result.stdout
    assert "--viewset" in result.stdout


def test_add_permission_create_refuse_force(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    result = runner.invoke(
        app,
        ["add-permission", "blog", "IsOwner", "--preset", "owner", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    perms = root / "apps" / "blog" / "permissions.py"
    assert perms.is_file()
    text = perms.read_text(encoding="utf-8")
    assert "class IsOwner(BasePermission)" in text
    assert 'getattr(obj, "owner"' in text

    refused = runner.invoke(
        app,
        ["add-permission", "blog", "IsOwner", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        [
            "add-permission",
            "blog",
            "IsOwner",
            "--preset",
            "auth_or_read",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert forced.exit_code == 0, forced.output
    text = perms.read_text(encoding="utf-8")
    assert "SAFE_METHODS" in text
    assert "is_authenticated" in text


def test_add_permission_tenant_gate(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path, multitenancy=False)
    bad = runner.invoke(
        app,
        [
            "add-permission",
            "blog",
            "IsTenantMember",
            "--preset",
            "tenant_member",
            "--path",
            str(root),
        ],
    )
    assert bad.exit_code == 1
    assert "multitenancy" in bad.output.lower()

    mt_root = _project_with_post(tmp_path / "mt", multitenancy=True)
    ok = runner.invoke(
        app,
        [
            "add-permission",
            "blog",
            "IsTenantMember",
            "--preset",
            "tenant_member",
            "--path",
            str(mt_root),
        ],
    )
    assert ok.exit_code == 0, ok.output
    text = (mt_root / "apps" / "blog" / "permissions.py").read_text(encoding="utf-8")
    assert 'getattr(request, "tenant"' in text


def test_add_permission_wire_viewset(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    assert (
        runner.invoke(
            app,
            ["add-viewset", "blog", "Post", "--force", "--path", str(root)],
        ).exit_code
        == 0
    )
    result = runner.invoke(
        app,
        [
            "add-permission",
            "blog",
            "IsOwner",
            "--preset",
            "owner",
            "--viewset",
            "Post",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "from apps.blog.permissions import IsOwner" in views
    assert "permission_classes = [IsOwner]" in views


def test_add_viewset_custom_permission(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    assert (
        runner.invoke(
            app,
            ["add-permission", "blog", "IsOwner", "--path", str(root)],
        ).exit_code
        == 0
    )
    result = runner.invoke(
        app,
        [
            "add-viewset",
            "blog",
            "Post",
            "--permission",
            "IsOwner",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "from apps.blog.permissions import IsOwner" in views
    assert "permission_classes = [IsOwner]" in views
