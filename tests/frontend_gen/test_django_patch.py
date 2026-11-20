"""Unit tests for Django CORS / auth patches used by frontend setup."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.frontend_gen.django_patch import (
    patch_django_for_frontend,
    patch_env_cors,
    register_endpoint_present,
)

runner = CliRunner()


def _new_project(tmp_path: Path) -> Path:
    args = [
        "new",
        "proj",
        "-d",
        "sqlite",
        "--no-docker",
        "--no-multitenancy",
        "--no-frontend",
        "--path",
        str(tmp_path),
    ]
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path / "proj"


def test_patch_env_cors_merges_vite_origins(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text(
        "CORS_ALLOWED_ORIGINS=http://localhost:3000\n",
        encoding="utf-8",
    )
    patch_env_cors(env)
    text = env.read_text(encoding="utf-8")
    assert "http://localhost:5173" in text
    assert "http://127.0.0.1:5173" in text
    assert "http://localhost:8080" in text
    assert "http://localhost:3000" in text


def test_patch_django_without_register(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    patch_django_for_frontend(root, include_register=False)
    auth = (root / "apps" / "users" / "auth_api.py").read_text(encoding="utf-8")
    assert "EmailTokenObtainPairView" in auth
    assert "class UserListView" in auth
    assert "class RegisterView" in auth
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "EmailTokenObtainPairView" in urls
    assert "UserListView" in urls
    assert 'path("api/users/"' in urls
    assert "api/auth/register" not in urls
    assert "TokenRefreshView" in urls
    env = (root / ".env.example").read_text(encoding="utf-8")
    assert "5173" in env
    assert not register_endpoint_present(root)


def test_patch_django_with_register(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    patch_django_for_frontend(root, include_register=True)
    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert 'path("api/auth/register/"' in urls
    assert "RegisterView" in urls
    assert 'path("api/users/"' in urls
    assert register_endpoint_present(root)
