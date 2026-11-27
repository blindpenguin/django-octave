"""Unit tests for Django CORS / auth patches used by frontend setup."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from typer.testing import CliRunner

from django_octave.cli import app
from django_octave.frontend_gen.django_patch import (
    ensure_user_list_api,
    patch_django_for_frontend,
    patch_env_cors,
    patch_env_proxies,
    register_endpoint_present,
    render_auth_api,
    write_auth_api,
)
from django_octave.tenancy import TenancyModuleMissingError

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


def test_patch_urls_replaces_throttled_obtain_view_and_keeps_refresh_throttle(
    tmp_path: Path,
) -> None:
    root = _new_project(tmp_path)

    patch_django_for_frontend(root, include_register=False)

    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert "throttled(TokenObtainPairView)" not in urls
    assert 'path("api/auth/token/", EmailTokenObtainPairView.as_view()' in urls
    assert "throttled(TokenRefreshView)" in urls


def test_patch_urls_puts_frontend_imports_after_the_throttle_import(
    tmp_path: Path,
) -> None:
    root = _new_project(tmp_path)

    patch_django_for_frontend(root, include_register=False)

    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert urls.index("from apps.core.throttling import throttled") < urls.index(
        "from apps.users.auth_api import"
    )


def test_patch_urls_is_idempotent_with_throttled_urls(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    patch_django_for_frontend(root, include_register=True)
    once = (root / "config" / "urls.py").read_text(encoding="utf-8")

    patch_django_for_frontend(root, include_register=True)

    assert (root / "config" / "urls.py").read_text(encoding="utf-8") == once


def test_patch_urls_still_patches_a_project_generated_before_throttling(
    tmp_path: Path,
) -> None:
    root = _new_project(tmp_path)
    urls_path = root / "config" / "urls.py"
    stock = urls_path.read_text(encoding="utf-8")
    stock = stock.replace("from apps.core.throttling import throttled\n\n", "")
    stock = stock.replace(
        "throttled(TokenObtainPairView)", "TokenObtainPairView.as_view()"
    )
    stock = stock.replace("throttled(TokenRefreshView)", "TokenRefreshView.as_view()")
    urls_path.write_text(stock, encoding="utf-8")

    patch_django_for_frontend(root, include_register=True)

    patched = urls_path.read_text(encoding="utf-8")
    assert 'path("api/auth/token/", EmailTokenObtainPairView.as_view()' in patched
    assert "TokenRefreshView.as_view()" in patched
    assert 'path("api/auth/register/"' in patched
    assert patched.index("from rest_framework_simplejwt.views") < patched.index(
        "from apps.users.auth_api import"
    )


def _new_mt_project(tmp_path: Path) -> Path:
    args = [
        "new", "mtproj", "-d", "sqlite", "--no-docker", "--multitenancy",
        "--no-frontend", "--path", str(tmp_path),
    ]  # fmt: skip
    assert runner.invoke(app, args).exit_code == 0
    return tmp_path / "mtproj"


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_auth_api_parses_and_throttles_credential_views(
    multitenancy: bool,
) -> None:
    source = render_auth_api(use_multitenancy=multitenancy)

    ast.parse(source)
    assert (
        source.count("throttle_classes = [AuthRateThrottle]") == 2
    )  # obtain + register
    assert "from apps.core.throttling import AuthRateThrottle" in source
    assert 'fields = ("id", "email", "label")' in source  # exposed fields unchanged


def test_render_auth_api_plain_user_list_is_unchanged() -> None:
    source = render_auth_api(use_multitenancy=False)

    assert 'queryset = User.objects.all().order_by("email")' in source
    assert "TenantScopedMixin" not in source
    assert "memberships" not in source


def test_render_auth_api_multitenancy_user_list_is_scoped_to_the_tenant() -> None:
    source = render_auth_api(use_multitenancy=True)

    assert "class UserListView(TenantScopedMixin, ListAPIView)" in source
    assert "from apps.core.tenancy import TenantScopedMixin" in source
    assert "User.objects.filter(memberships__tenant=self.request.tenant)" in source
    assert "User.objects.all().order_by" not in source


def test_write_auth_api_uses_the_multitenancy_variant_for_mt_projects(
    tmp_path: Path,
) -> None:
    root = _new_mt_project(tmp_path)

    path = write_auth_api(root)

    assert "TenantScopedMixin" in path.read_text(encoding="utf-8")


def test_write_auth_api_refuses_a_multitenancy_project_without_tenancy_module(
    tmp_path: Path,
) -> None:
    root = _new_mt_project(tmp_path)
    (root / "apps" / "core" / "tenancy.py").unlink()  # generated before the DRF fix

    with pytest.raises(TenancyModuleMissingError, match="tenancy.py"):
        write_auth_api(root)

    assert not (root / "apps" / "users" / "auth_api.py").exists()


def test_write_auth_api_keeps_an_existing_module_unless_forced(tmp_path: Path) -> None:
    root = _new_project(tmp_path)
    path = write_auth_api(root)
    path.write_text(
        path.read_text(encoding="utf-8") + "\n# my edit\n", encoding="utf-8"
    )

    write_auth_api(root)
    assert "# my edit" in path.read_text(encoding="utf-8")

    write_auth_api(root, force=True)
    assert "# my edit" not in path.read_text(encoding="utf-8")


def test_patch_env_proxies_appends_the_proxy_count(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text("DJANGO_DEBUG=True", encoding="utf-8")  # no trailing newline

    patch_env_proxies(env)

    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "DJANGO_DEBUG=True"
    assert "DJANGO_NUM_PROXIES=1" in lines


def test_patch_env_proxies_creates_a_missing_file(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"

    patch_env_proxies(env)

    assert "DJANGO_NUM_PROXIES=1" in env.read_text(encoding="utf-8")


@pytest.mark.parametrize("existing", ["DJANGO_NUM_PROXIES=0", "DJANGO_NUM_PROXIES=2"])
def test_patch_env_proxies_never_overrides_an_existing_value(
    tmp_path: Path, existing: str
) -> None:
    env = tmp_path / ".env.example"
    env.write_text(f"{existing}\n", encoding="utf-8")

    patch_env_proxies(env)

    assert env.read_text(encoding="utf-8") == f"{existing}\n"


def test_patch_env_proxies_is_idempotent(tmp_path: Path) -> None:
    env = tmp_path / ".env.example"
    env.write_text("A=1\n", encoding="utf-8")
    patch_env_proxies(env)
    once = env.read_text(encoding="utf-8")

    patch_env_proxies(env)

    assert env.read_text(encoding="utf-8") == once
    assert once.count("DJANGO_NUM_PROXIES=") == 1


def test_patch_django_for_frontend_adds_proxy_count_to_env_example(
    tmp_path: Path,
) -> None:
    root = _new_project(tmp_path)

    patch_django_for_frontend(root, include_register=False)

    env = (root / ".env.example").read_text(encoding="utf-8")
    assert env.count("DJANGO_NUM_PROXIES=1") == 1
    assert "CORS_ALLOWED_ORIGINS=" in env


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_auth_api_registration_validates_the_password_against_the_user(
    multitenancy: bool,
) -> None:
    source = render_auth_api(use_multitenancy=multitenancy)

    ast.parse(source)
    assert (
        'validate_password(attrs["password"], user=User(email=attrs["email"]))'
        in source
    )
    assert "except DjangoValidationError as exc:" in source
    assert '{"password": list(exc.messages)}' in source
    # the helper user is only a data holder for the validators; it is never saved
    assert "User(email=attrs" in source
    assert 'User(email=attrs["email"]).save' not in source


def test_render_auth_api_keeps_the_other_registration_error_shapes() -> None:
    source = render_auth_api(use_multitenancy=False)

    assert '{"password_confirm": "Passwords do not match."}' in source
    assert '"A user with this email already exists."' in source


def test_ensure_user_list_api_wires_the_user_list_without_register(
    tmp_path: Path,
) -> None:
    root = _new_project(tmp_path)

    written = ensure_user_list_api(root)

    urls = (root / "config" / "urls.py").read_text(encoding="utf-8")
    assert 'path("api/users/"' in urls
    assert "api/auth/register" not in urls
    assert (root / "apps" / "users" / "auth_api.py") in written
    assert (root / "config" / "urls.py") in written
