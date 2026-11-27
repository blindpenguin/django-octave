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
        [
            "add-model",
            "blog",
            "Post",
            "--fields",
            ",".join(fields),
            "--path",
            str(root),
        ],
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
        ('title:char:default=it\'s "q"', 'it\'s "q"'),
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


# --- related_name: explicit option and generated names --------------------------------

CLASHING = "title:char,owner:fk:to=users.User,assignee:fk:to=users.User"


def _add_related(root: Path, fields: str, *extra: str):
    return runner.invoke(
        app,
        ["add-model", "blog", "Post", "--fields", fields, "--path", str(root), *extra],
    )


def _model_source(root: Path) -> str:
    return (root / "apps" / "blog" / "models.py").read_text(encoding="utf-8")


def test_add_model_clashing_relations_get_distinct_related_names(
    tmp_path: Path,
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_related(root, CLASHING)

    assert result.exit_code == 0, result.output
    models = _model_source(root)
    assert 'related_name="post_owner"' in models
    assert 'related_name="post_assignee"' in models
    ast.parse(models)


def test_add_model_says_which_related_names_it_chose(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)

    result = _add_related(root, CLASHING)

    assert "own reverse name" in result.output
    assert "post_owner" in result.output
    assert "post_assignee" in result.output
    assert "related_name=" in result.output


def test_add_model_force_rerun_writes_identical_bytes(tmp_path: Path) -> None:
    root = _project_with_app(tmp_path)
    assert _add_related(root, CLASHING).exit_code == 0
    first = {p.name: p.read_bytes() for p in (root / "apps" / "blog").glob("*.py")}

    assert _add_related(root, CLASHING, "--force").exit_code == 0

    second = {p.name: p.read_bytes() for p in (root / "apps" / "blog").glob("*.py")}
    assert second == first


def test_add_model_explicit_related_names_are_written_as_given_without_a_note(
    tmp_path: Path,
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_related(
        root,
        "title:char,owner:fk:to=users.User:related_name=owned_notes,"
        "assignee:fk:to=users.User:related_name=+",
    )

    assert result.exit_code == 0, result.output
    models = _model_source(root)
    assert 'related_name="owned_notes"' in models
    assert 'related_name="+"' in models
    assert "post_owner" not in models
    assert "own reverse name" not in result.output


def test_add_model_one_explicit_name_leaves_the_other_relation_alone(
    tmp_path: Path,
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_related(
        root,
        "owner:fk:to=users.User:related_name=owned_notes,assignee:fk:to=users.User",
    )

    assert result.exit_code == 0, result.output
    models = _model_source(root)
    assert models.count("related_name") == 1
    assert "own reverse name" not in result.output


def test_add_model_without_a_clash_adds_no_related_name_and_no_note(
    tmp_path: Path,
) -> None:
    root = _project_with_app(tmp_path)

    result = _add_related(root, "title:char,owner:fk:to=users.User,tags:m2m:to=Tag")

    assert result.exit_code == 0, result.output
    assert "related_name" not in _model_source(root)
    assert "own reverse name" not in result.output


@pytest.mark.parametrize(
    "fields",
    [
        "owner:fk:to=users.User:related_name=class",
        "owner:fk:to=users.User:related_name=a-b",
        "owner:fk:to=users.User:related_name=x_",
        "owner:fk:to=users.User:related_name",
        "title:char:related_name=x",
        "a:fk:to=users.User:related_name=n,b:fk:to=users.User:related_name=n",
    ],
)
def test_add_model_invalid_related_name_exits_1_and_changes_nothing(
    tmp_path: Path, fields: str
) -> None:
    root = _project_with_app(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*.py") if ".venv" not in p.parts}

    result = _add_related(root, fields)

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    after = {p: p.read_bytes() for p in root.rglob("*.py") if ".venv" not in p.parts}
    assert after == before


def test_add_model_stubs_do_not_depend_on_related_name(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    explicit = tmp_path / "explicit"
    generated.mkdir()
    explicit.mkdir()
    root_a = _project_with_app(generated)
    root_b = _project_with_app(explicit)

    assert _add_related(root_a, CLASHING).exit_code == 0
    assert (
        _add_related(
            root_b,
            "title:char,owner:fk:to=users.User:related_name=+,"
            "assignee:fk:to=users.User:related_name=+",
        ).exit_code
        == 0
    )

    for name in ("serializers.py", "admin.py", "views.py", "urls.py"):
        a = (root_a / "apps" / "blog" / name).read_text(encoding="utf-8")
        b = (root_b / "apps" / "blog" / name).read_text(encoding="utf-8")
        assert a == b, name
