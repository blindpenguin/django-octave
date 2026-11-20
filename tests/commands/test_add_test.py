"""CLI tests for django-octave add-test."""

from __future__ import annotations

import ast
from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_post(tmp_path: Path, *, with_viewset: bool = True) -> Path:
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
    if with_viewset:
        assert (
            runner.invoke(
                app,
                ["add-viewset", "blog", "Post", "--force", "--path", str(root)],
            ).exit_code
            == 0
        )
    else:
        # strip viewset class if add-model created stubs
        views = root / "apps" / "blog" / "views.py"
        if views.exists():
            text = views.read_text(encoding="utf-8")
            if "PostViewSet" in text:
                views.write_text(
                    '"""API views for blog."""\n\nfrom rest_framework import viewsets\n',
                    encoding="utf-8",
                )
    return root


def test_add_test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert "add-test" in result.stdout
    result = runner.invoke(app, ["add-test", "--help"])
    assert result.exit_code == 0


def test_add_test_with_viewset_refuse_force(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path, with_viewset=True)
    result = runner.invoke(
        app,
        ["add-test", "blog", "Post", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    factory = root / "tests" / "factories" / "blog_post.py"
    api = root / "tests" / "test_blog_post_api.py"
    assert factory.is_file()
    assert api.is_file()
    ast.parse(factory.read_text(encoding="utf-8"))
    ast.parse(api.read_text(encoding="utf-8"))
    assert "PostFactory" in factory.read_text(encoding="utf-8")
    assert 'reverse("post-list")' in api.read_text(encoding="utf-8")
    assert (root / "tests" / "factories" / "user.py").is_file()
    assert "auth_client" in (root / "tests" / "conftest.py").read_text(encoding="utf-8")

    refused = runner.invoke(
        app,
        ["add-test", "blog", "Post", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        ["add-test", "blog", "Post", "--force", "--path", str(root)],
    )
    assert forced.exit_code == 0, forced.output


def test_add_test_without_viewset(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path, with_viewset=False)
    result = runner.invoke(
        app,
        ["add-test", "blog", "Post", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    model_test = root / "tests" / "test_blog_post_model.py"
    assert model_test.is_file()
    ast.parse(model_test.read_text(encoding="utf-8"))
    assert not (root / "tests" / "test_blog_post_api.py").exists()


def test_add_test_missing_model(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path, with_viewset=False)
    result = runner.invoke(
        app,
        ["add-test", "blog", "Missing", "--path", str(root)],
    )
    assert result.exit_code == 1
