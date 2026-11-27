"""CLI tests for django-octave add-admin."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_post(tmp_path: Path) -> Path:
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
                "--field",
                "published:bool:default=false",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    return root


def test_add_admin_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-admin" in result.stdout
    result = runner.invoke(app, ["add-admin", "--help"])
    assert result.exit_code == 0
    assert "--list-display" in result.stdout
    assert "--filter" in result.stdout


def test_add_admin_refuse_force_and_overrides(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    # add-model already created PostAdmin — refuse without force
    refused = runner.invoke(
        app,
        ["add-admin", "blog", "Post", "--path", str(root)],
    )
    assert refused.exit_code == 1

    result = runner.invoke(
        app,
        [
            "add-admin",
            "blog",
            "Post",
            "--list-display",
            "id,title,published",
            "--search",
            "title",
            "--filter",
            "published",
            "--ordering",
            "-created_at",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    admin = (root / "apps" / "blog" / "admin.py").read_text(encoding="utf-8")
    assert "class PostAdmin" in admin
    assert 'list_display = ("id", "title", "published")' in admin
    assert 'search_fields = ("title",)' in admin
    assert 'list_filter = ("published",)' in admin
    assert 'ordering = ("-created_at",)' in admin
    assert 'date_hierarchy = "created_at"' in admin


def test_add_admin_heuristics_and_no_hierarchy(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-admin",
            "blog",
            "Post",
            "--no-date-hierarchy",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    admin = (root / "apps" / "blog" / "admin.py").read_text(encoding="utf-8")
    assert "title" in admin
    assert "published" in admin
    assert "date_hierarchy" not in admin


def test_add_admin_bad_field_and_missing_model(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    bad = runner.invoke(
        app,
        [
            "add-admin",
            "blog",
            "Post",
            "--list-display",
            "nope",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert bad.exit_code == 1

    missing = runner.invoke(
        app,
        ["add-admin", "blog", "Missing", "--force", "--path", str(root)],
    )
    assert missing.exit_code == 1
