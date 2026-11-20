"""CLI tests for django-octave add-serializer."""

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


def test_add_serializer_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "add-serializer" in result.stdout
    result = runner.invoke(app, ["add-serializer", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.stdout


def test_add_serializer_refuse_then_force(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    refused = runner.invoke(
        app,
        ["add-serializer", "blog", "Post", "--path", str(root)],
    )
    assert refused.exit_code == 1
    assert "already exists" in refused.output

    result = runner.invoke(
        app,
        [
            "add-serializer",
            "blog",
            "Post",
            "--fields",
            "title,id",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    ser = (root / "apps" / "blog" / "serializers.py").read_text(encoding="utf-8")
    assert ser.count("class PostSerializer") == 1
    post_block = ser.split("class PostSerializer")[1]
    assert '"title"' in post_block and '"id"' in post_block
    fields_line = post_block.split("fields =")[1].split(")")[0]
    assert "created_at" not in fields_line
    assert "name" not in fields_line


def test_add_serializer_bad_field(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-serializer",
            "blog",
            "Post",
            "--fields",
            "nope",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 1
    assert "Unknown field" in result.output


def test_add_serializer_missing_model(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    result = runner.invoke(
        app,
        ["add-serializer", "blog", "Missing", "--path", str(root)],
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_add_model_fk_and_nested_serializer(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    assert (
        runner.invoke(
            app,
            [
                "add-model",
                "blog",
                "Author",
                "--field",
                "name:char",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    # Replace Post with author FK (force)
    assert (
        runner.invoke(
            app,
            [
                "add-model",
                "blog",
                "Post",
                "--field",
                "title:char",
                "--field",
                "author:fk:to=Author",
                "--force",
                "--path",
                str(root),
            ],
        ).exit_code
        == 0
    )
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert 'ForeignKey("Author"' in models or "ForeignKey(\"Author\"" in models

    result = runner.invoke(
        app,
        [
            "add-serializer",
            "blog",
            "Post",
            "--nested",
            "author",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    ser = (root / "apps" / "blog" / "serializers.py").read_text(encoding="utf-8")
    assert "AuthorNestedSerializer" in ser
    assert "author = AuthorNestedSerializer(read_only=True)" in ser


def test_add_serializer_bad_nested(tmp_path: Path) -> None:
    root = _project_with_post(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-serializer",
            "blog",
            "Post",
            "--nested",
            "nope",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 1
    assert "not a relation" in result.output.lower() or "Cannot nest" in result.output
