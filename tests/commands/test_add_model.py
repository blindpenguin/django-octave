"""CLI tests for django-octave add-model."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
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
        "--no-frontend",
    ]
    assert runner.invoke(app, args).exit_code == 0
    root = tmp_path / "proj"
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    return root


def test_add_model_help() -> None:
    result = runner.invoke(app, ["add-model", "--help"])
    assert result.exit_code == 0
    assert "--field" in result.stdout
    assert "--fields" in result.stdout


def test_add_model_compact_fields(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-model",
            "blog",
            "Post",
            "--fields",
            "title:char:max=200,published:bool:default=false",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "title = models.CharField" in models
    assert "published = models.BooleanField" in models


def test_add_model_field_and_fields_combine(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    result = runner.invoke(
        app,
        [
            "add-model",
            "blog",
            "Post",
            "--field",
            "title:char",
            "--fields",
            "published:bool,slug:slug",
            "--path",
            str(root),
        ],
    )
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert "title = models.CharField" in models
    assert "published = models.BooleanField" in models
    assert "slug = models.SlugField" in models


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


UUID_TEXT = "123e4567-e89b-12d3-a456-426614174000"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted((root / "apps" / "blog").rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def _add_model(root: Path, *fields: str) -> object:
    return runner.invoke(
        app,
        ["add-model", "blog", "Post", "--fields", ",".join(fields), "--path", str(root)],
    )


def _post_default(models_source: str) -> ast.expr:
    """The ``default=`` argument of the first field in ``class Post``."""
    post = next(
        n
        for n in ast.parse(models_source).body
        if isinstance(n, ast.ClassDef) and n.name == "Post"
    )
    for node in ast.walk(post):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "default":
                    return kw.value
    raise AssertionError("no default= found")


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("title:char:default=hello", "hello"),
        ("title:char:default=it's \"q\"", "it's \"q\""),
        ("count:int:default=3", 3),
        ("ok:bool:default=true", True),
        ("price:decimal:default=9.99", "9.99"),
    ],
)
def test_add_model_literal_defaults_generate_valid_models(
    tmp_path: Path, field: str, expected: object
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_model(root, field)

    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert ast.literal_eval(_post_default(models)) == expected


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("ref:uuid:default=uuid4", "uuid.uuid4"),
        (f"ref:uuid:default={UUID_TEXT}", f"uuid.UUID('{UUID_TEXT}')"),
    ],
)
def test_add_model_uuid_defaults_import_uuid(
    tmp_path: Path, field: str, expected: str
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_model(root, field)

    assert result.exit_code == 0, result.output
    models = (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")
    assert ast.unparse(_post_default(models)) == expected
    assert "import uuid" in models


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("x:date:default=__import__('os').getcwd()", "Defaults are not supported"),
        ("n:int:default=abc", "Invalid default"),
        ("ok:bool:default=maybe", "Invalid default"),
        ("class:char", "Python keyword"),
        ("save:char", "shadow a Django model method"),
    ],
)
def test_add_model_rejected_input_exits_1_and_writes_nothing(
    tmp_path: Path, field: str, message: str
) -> None:
    root = _project_with_app(tmp_path)
    before = _snapshot(root)

    result = _add_model(root, field)

    assert result.exit_code == 1
    assert message in " ".join(result.output.split())
    assert _snapshot(root) == before
