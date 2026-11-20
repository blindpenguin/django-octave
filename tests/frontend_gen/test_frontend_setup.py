"""Integration-style tests for setup_frontend orchestrator."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.frontend_gen.setup import FrontendExistsError, setup_frontend

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


def test_setup_frontend_no_docker(tmp_path: Path) -> None:
    root = _new_project(tmp_path, docker=False)
    written = setup_frontend(root, include_register=False)
    assert (root / "frontend" / "package.json").is_file()
    assert (root / "apps" / "users" / "auth_api.py").is_file()
    env = (root / ".env.example").read_text(encoding="utf-8")
    assert "5173" in env
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "EmailTokenObtainPairView" in urls
    assert "api/auth/register" not in urls
    assert any(p.name == "frontend" for p in written)

    try:
        setup_frontend(root)
        raise AssertionError("expected FrontendExistsError")
    except FrontendExistsError:
        pass


def test_setup_frontend_register_and_docker(tmp_path: Path) -> None:
    root = _new_project(tmp_path, docker=True)
    setup_frontend(root, include_register=True)
    assert (root / "frontend" / "src" / "pages" / "RegisterView.vue").is_file()
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "api/auth/register" in urls
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "frontend:" in compose
    assert "5173:5173" in compose
    prod = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "8080:80" in prod
