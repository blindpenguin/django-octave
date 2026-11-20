"""CLI tests for django-octave add."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _new_project(tmp_path: Path, *, multitenancy: bool = False) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--no-docker",
        "--path",
        str(tmp_path),
    ]
    args.append("--multitenancy" if multitenancy else "--no-multitenancy")
    args.append("--no-frontend")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return tmp_path / "proj"


def test_add_help() -> None:
    result = runner.invoke(app, ["add", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout
    assert "--model" in result.stdout


def test_add_happy_path(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    result = runner.invoke(app, ["add", "blog", "--path", str(root)])
    assert result.exit_code == 0, result.output
    app_dir = root / "apps" / "blog"
    assert (app_dir / "models.py").is_file()
    assert (app_dir / "serializers.py").is_file()
    assert (app_dir / "views.py").is_file()
    assert (app_dir / "urls.py").is_file()
    assert (app_dir / "services.py").is_file()
    settings = (root / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert '"apps.blog"' in settings
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert 'path("api/", include("apps.blog.urls"))' in urls
    models = (app_dir / "models.py").read_text(encoding="utf-8")
    assert "TimeStampedModel" in models
    assert "class Blog" in models
    assert 'router.register("blogs"' in (app_dir / "urls.py").read_text(encoding="utf-8")


def test_add_with_explicit_model(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    result = runner.invoke(
        app, ["add", "accounts", "--model", "Customer", "--path", str(root)]
    )
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "accounts" / "models.py").read_text(encoding="utf-8")
    assert "class Customer" in models
    assert "class Account" not in models
    urls = (root / "apps" / "accounts" / "urls.py").read_text(encoding="utf-8")
    assert 'router.register("customers"' in urls
    assert 'basename="customer"' in urls
    assert "CustomerViewSet" in urls


def test_add_rejects_reserved(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    result = runner.invoke(app, ["add", "core", "--path", str(root)])
    assert result.exit_code == 1


def test_add_refuses_existing(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    result = runner.invoke(app, ["add", "blog", "--path", str(root)])
    assert result.exit_code == 1


def test_add_force_idempotent_wiring(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    assert runner.invoke(app, ["add", "blog", "--path", str(root)]).exit_code == 0
    result = runner.invoke(app, ["add", "blog", "--path", str(root), "--force"])
    assert result.exit_code == 0, result.output
    settings = (root / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert settings.count('"apps.blog"') == 1
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert urls.count("apps.blog.urls") == 1


def test_add_multitenancy_model(tmp_path: Path) -> None:
    root = _new_project(tmp_path, multitenancy=True)
    result = runner.invoke(app, ["add", "orders", "--path", str(root)])
    assert result.exit_code == 0, result.output
    models = (root / "apps" / "orders" / "models.py").read_text(encoding="utf-8")
    assert "TenantAwareModel" in models
    assert "class Order" in models
