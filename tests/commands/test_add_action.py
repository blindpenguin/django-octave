"""CLI tests for django-octave add-action."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_viewset(tmp_path: Path) -> Path:
    assert (
        runner.invoke(
            app,
            [
                "new",
                "proj",
                "-d",
                "sqlite",
                "--no-docker",
                "--no-multitenancy",
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
    assert (
        runner.invoke(
            app,
            ["add-viewset", "blog", "Post", "--force", "--path", str(root)],
        ).exit_code
        == 0
    )
    return root


def test_add_action_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-action" in result.stdout
    result = runner.invoke(app, ["add-action", "--help"])
    assert result.exit_code == 0
    assert "--detail" in result.stdout or "--list" in result.stdout
    assert "--methods" in result.stdout


def test_add_action_detail_refuse_force(tmp_path: Path) -> None:
    root = _project_with_viewset(tmp_path)
    result = runner.invoke(
        app,
        ["add-action", "blog", "Post", "publish", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "def publish" in views
    assert "self.get_object()" in views
    assert '@extend_schema(tags=["post"])' in views or "tags=[" in views

    refused = runner.invoke(
        app,
        ["add-action", "blog", "Post", "publish", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        [
            "add-action",
            "blog",
            "Post",
            "publish",
            "--methods",
            "put",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert forced.exit_code == 0, forced.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert views.count("def publish") == 1
    assert '"put"' in views


def test_add_action_list_and_permission(tmp_path: Path) -> None:
    root = _project_with_viewset(tmp_path)
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
            "add-action",
            "blog",
            "Post",
            "recent",
            "--list",
            "--permission",
            "IsOwner",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "def recent" in views
    assert "detail=False" in views
    assert "permission_classes=[IsOwner]" in views
    assert "from apps.blog.permissions import IsOwner" in views


def test_add_action_bad_name_and_missing_viewset(tmp_path: Path) -> None:
    root = _project_with_viewset(tmp_path)
    bad = runner.invoke(
        app,
        ["add-action", "blog", "Post", "BadName", "--path", str(root)],
    )
    assert bad.exit_code == 1

    missing = runner.invoke(
        app,
        ["add-action", "blog", "Missing", "publish", "--path", str(root)],
    )
    assert missing.exit_code == 1
    assert "MissingViewSet" in missing.output or "not found" in missing.output.lower()
