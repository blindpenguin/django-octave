"""CLI tests for django-octave add-viewset."""

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
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    return root


def test_add_viewset_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-viewset" in result.stdout
    result = runner.invoke(app, ["add-viewset", "--help"])
    assert result.exit_code == 0
    assert "--permission" in result.stdout


def test_add_viewset_force_and_permission(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    refused = runner.invoke(
        app,
        ["add-viewset", "blog", "Post", "--path", str(root)],
    )
    assert refused.exit_code == 1

    result = runner.invoke(
        app,
        [
            "add-viewset",
            "blog",
            "Post",
            "--permission",
            "AllowAny",
            "--filter",
            "title",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "class PostViewSet" in views
    assert "AllowAny" in views
    assert 'filterset_fields = ["title"]' in views
    urls = (root / "apps" / "blog" / "urls.py").read_text(encoding="utf-8")
    assert "PostViewSet" in urls
    assert urls.count("PostViewSet") >= 1


def test_add_viewset_bad_permission(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
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
    assert result.exit_code == 1
    assert "Unknown permission" in result.output


def test_add_viewset_auto_serializer(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    ser = root / "apps" / "blog" / "serializers.py"
    ser.write_text(
        '"""Serializers for blog."""\n\nfrom rest_framework import serializers\n',
        encoding="utf-8",
    )
    views = root / "apps" / "blog" / "views.py"
    views.write_text(
        '"""API views for blog."""\n\nfrom rest_framework import viewsets\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "add-viewset",
            "blog",
            "Post",
            "--permission",
            "IsAuthenticated",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "class PostSerializer" in ser.read_text(encoding="utf-8")
    assert "class PostViewSet" in views.read_text(encoding="utf-8")
    assert "PostViewSet" in (root / "apps" / "blog" / "urls.py").read_text(
        encoding="utf-8"
    )
