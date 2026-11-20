"""CLI tests for django-octave add-frontend and new --frontend."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()


def _new_project(tmp_path: Path, *, docker: bool = False) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--docker" if docker else "--no-docker",
        "--no-multitenancy",
        "--no-frontend",
        "--path",
        str(tmp_path),
    ]
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path / "proj"


def test_help_lists_add_frontend() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "add-frontend" in result.stdout


def test_add_frontend_help() -> None:
    result = runner.invoke(app, ["add-frontend", "--help"])
    assert result.exit_code == 0
    assert "--register" in result.stdout
    assert "--crud" in result.stdout
    assert "--force" in result.stdout


def test_add_frontend_requires_register_noninteractive(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    result = runner.invoke(app, ["add-frontend", "--path", str(root)])
    assert result.exit_code == 2


def test_add_frontend_no_register(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    result = runner.invoke(
        app,
        ["add-frontend", "--no-register", "--no-crud", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    assert (root / "frontend" / "package.json").is_file()
    assert not (root / "frontend" / "src" / "pages" / "RegisterView.vue").exists()
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "EmailTokenObtainPairView" in urls
    assert "api/auth/register" not in urls

    refused = runner.invoke(
        app,
        ["add-frontend", "--no-register", "--no-crud", "--path", str(root)],
    )
    assert refused.exit_code == 1

    forced = runner.invoke(
        app,
        [
            "add-frontend",
            "--register",
            "--no-crud",
            "--force",
            "--path",
            str(root),
        ],
    )
    assert forced.exit_code == 0, forced.output
    assert (root / "frontend" / "src" / "pages" / "RegisterView.vue").is_file()
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "api/auth/register" in urls


def test_add_frontend_docker_compose(tmp_path: Path) -> None:
    root = _new_project(tmp_path, docker=True)
    result = runner.invoke(
        app,
        ["add-frontend", "--no-register", "--no-crud", "--path", str(root)],
    )
    assert result.exit_code == 0, result.output
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "frontend:" in compose
    assert "5173:5173" in compose


def test_add_frontend_not_octave(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["add-frontend", "--no-register", "--no-crud", "--path", str(tmp_path)],
    )
    assert result.exit_code == 1


def test_new_with_frontend(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            "with_fe",
            "-d",
            "sqlite",
            "--no-docker",
            "--no-multitenancy",
            "--frontend",
            "--no-register",
            "--no-crud",
            "--path",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    root = tmp_path / "with_fe"
    assert (root / "frontend" / "package.json").is_file()
    assert (root / "apps" / "users" / "auth_api.py").is_file()
