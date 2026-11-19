"""CLI tests for django-octave add-model."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _project_with_app(tmp_path: Path, *, multitenancy: bool = False) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--no-docker",
        "--path",
        str(tmp_path),
        "--multitenancy" if multitenancy else "--no-multitenancy",
    ]
    assert runner.invoke(app, args).exit_code == 0
    root = tmp_path / "proj"
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    return root


def test_add_model_help() -> None:
    result = runner.invoke(app, ["add-model", "--help"])
    assert result.exit_code == 0
    assert "--field" in result.stdout


def test_add_model_happy_path(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    result = runner.invoke(
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
    )
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "class Post(TimeStampedModel)" in models
    assert "title = models.CharField" in models
    ser = (root / "apps" / "blog" / "serializers.py").read_text(encoding="utf-8")
    assert "PostSerializer" in ser
    assert '"title"' in ser
    views = (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8")
    assert "PostViewSet" in views
    urls = (root / "apps" / "blog" / "urls.py").read_text(encoding="utf-8")
    assert "PostViewSet" in urls


def test_add_model_default_field(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    result = runner.invoke(app, ["add-model", "blog", "Tag", "--path", str(root)])
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "class Tag(" in models
    assert "name = models.CharField" in models


def test_add_model_bad_field(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    result = runner.invoke(
        app,
        ["add-model", "blog", "Post", "--field", "x:nope", "--path", str(root)],
    )
    assert result.exit_code == 1


def test_add_model_duplicate_and_force(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    args = ["add-model", "blog", "Post", "--field", "title:char", "--path", str(root)]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code == 1
    forced = runner.invoke(app, [*args, "--force", "--field", "body:text"])
    # note: duplicate --field from args - need clean invoke
    forced = runner.invoke(
        app,
        [
            "add-model",
            "blog",
            "Post",
            "--field",
            "title:char",
            "--field",
            "body:text",
            "--path",
            str(root),
            "--force",
        ],
    )
    assert forced.exit_code == 0, forced.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "body = models.TextField" in models


def test_add_model_multitenancy(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path, multitenancy=True)
    result = runner.invoke(
        app,
        ["add-model", "blog", "Post", "--field", "title:char", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "TenantAwareModel" in models
