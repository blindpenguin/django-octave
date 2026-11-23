"""Unit tests for frontend template rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.frontend_gen.setup import FrontendSetupError, render_frontend


def test_render_frontend_without_register(tmp_path: Path) -> None:
    target = tmp_path / "frontend"
    render_frontend(
        target,
        project_name="Demo App",
        project_slug="demo_app",
        include_register=False,
    )

    assert (target / "package.json").is_file()
    assert (target / "vite.config.ts").is_file()
    assert (target / "src" / "main.ts").is_file()
    assert (target / "src" / "pages" / "LoginView.vue").is_file()
    assert (target / "src" / "pages" / "HomeView.vue").is_file()
    assert not (target / "src" / "pages" / "RegisterView.vue").exists()

    pkg = (target / "package.json").read_text(encoding="utf-8")
    assert '"name": "demo_app-frontend"' in pkg
    assert "@nuxt/ui" in pkg

    vite = (target / "vite.config.ts").read_text(encoding="utf-8")
    assert "@nuxt/ui/vite" in vite
    assert "port: 5173" in vite

    main = (target / "src" / "main.ts").read_text(encoding="utf-8")
    assert "@nuxt/ui/vue-plugin" in main

    router = (target / "src" / "router" / "index.ts").read_text(encoding="utf-8")
    assert "RegisterView" not in router
    assert "name: 'login'" in router
    assert "AuthLayout" in router
    assert "AppLayout" in router
    assert "django-octave crud routes begin" in router

    assert (target / "src" / "layouts" / "AuthLayout.vue").is_file()
    layout = (target / "src" / "layouts" / "AppLayout.vue").read_text(encoding="utf-8")
    assert "UDashboardGroup" in layout
    assert "crudNavItems" in layout
    assert "// --- django-octave crud nav begin ---" in layout
    assert "getUserEmail" in layout
    assert "exact: true" in layout
    assert "pathActive" in layout
    assert "active: to ? pathActive(to)" in layout

    home = (target / "src" / "pages" / "HomeView.vue").read_text(encoding="utf-8")
    assert "AppLayout" not in home

    auth = (target / "src" / "auth" / "useAuth.ts").read_text(encoding="utf-8")
    assert "export async function login" in auth
    assert "export async function register" not in auth
    assert "setUserEmail(email)" in auth
    assert "getUserEmail" in auth

    tokens = (target / "src" / "auth" / "tokens.ts").read_text(encoding="utf-8")
    assert "octave_email" in tokens
    assert "export function getUserEmail" in tokens
    assert "export function setUserEmail" in tokens
    assert "localStorage.removeItem(EMAIL_KEY)" in tokens

    index = (target / "index.html").read_text(encoding="utf-8")
    assert 'class="isolate"' in index
    assert "Demo App" in index


def test_render_frontend_with_register(tmp_path: Path) -> None:
    target = tmp_path / "frontend"
    render_frontend(
        target,
        project_name="Demo App",
        project_slug="demo_app",
        include_register=True,
    )

    assert (target / "src" / "pages" / "RegisterView.vue").is_file()
    router = (target / "src" / "router" / "index.ts").read_text(encoding="utf-8")
    assert "RegisterView" in router
    assert "name: 'register'" in router
    auth = (target / "src" / "auth" / "useAuth.ts").read_text(encoding="utf-8")
    assert "export async function register" in auth
    login = (target / "src" / "pages" / "LoginView.vue").read_text(encoding="utf-8")
    assert 'to="/register"' in login


def test_render_frontend_rejects_empty_names(tmp_path: Path) -> None:
    with pytest.raises(FrontendSetupError):
        render_frontend(tmp_path / "frontend", project_name="", project_slug="x")
    with pytest.raises(FrontendSetupError):
        render_frontend(tmp_path / "frontend", project_name="X", project_slug="")


def _nginx_conf(tmp_path: Path) -> str:
    frontend = tmp_path / "frontend"
    render_frontend(
        frontend, project_name="Demo", project_slug="demo", include_register=False
    )
    return (frontend / "nginx.conf").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "header",
    [
        'add_header X-Content-Type-Options "nosniff" always;',
        'add_header X-Frame-Options "DENY" always;',
        'add_header Referrer-Policy "same-origin" always;',
    ],
)
def test_render_nginx_sends_security_headers_on_every_response(
    tmp_path: Path, header: str
) -> None:
    assert header in _nginx_conf(tmp_path)


def test_render_nginx_defines_headers_at_server_level_only(tmp_path: Path) -> None:
    conf = _nginx_conf(tmp_path)
    locations = conf.split("location ", 1)[1]  # everything from the first location on

    # nginx drops inherited add_header in a location that defines its own.
    assert "add_header" not in locations


def test_render_nginx_keeps_proxy_and_spa_fallback(tmp_path: Path) -> None:
    conf = _nginx_conf(tmp_path)

    assert "proxy_pass http://web:8000;" in conf
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in conf
    assert "try_files $uri $uri/ /index.html;" in conf
