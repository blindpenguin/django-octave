"""Patch Django project files for Vue frontend (CORS, JWT email obtain, register)."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from django_octave.project.detect import detect_project
from django_octave.tenancy import ensure_tenancy_module

AUTH_API_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "frontend_django"

_ENV_MARKER_BEGIN = "# --- django-octave frontend begin ---"
_ENV_MARKER_END = "# --- django-octave frontend end ---"
_URLS_IMPORT_BEGIN = "# --- django-octave frontend imports begin ---"
_URLS_IMPORT_END = "# --- django-octave frontend imports end ---"

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080"
)


class DjangoPatchError(ValueError):
    """Raised when Django patches cannot complete safely."""


def build_frontend_env_block() -> str:
    return f"""
{_ENV_MARKER_BEGIN}
# Vite (5173) and prod SPA nginx (8080) origins for the Vue frontend
CORS_ALLOWED_ORIGINS={_DEFAULT_CORS_ORIGINS}
{_ENV_MARKER_END}
"""


def register_endpoint_present(root: Path) -> bool:
    """True if a register URL is already wired in ``config/urls.py``."""
    urls = root / "config" / "urls.py"
    if not urls.is_file():
        return False
    text = urls.read_text(encoding="utf-8")
    return "api/auth/register" in text


def users_list_endpoint_present(root: Path) -> bool:
    """True if ``api/users/`` is wired for FK selects."""
    urls = root / "config" / "urls.py"
    if not urls.is_file():
        return False
    return "api/users/" in urls.read_text(encoding="utf-8")


def _merge_cors_line(existing: str) -> str:
    wanted = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    parts = [p.strip() for p in existing.split(",") if p.strip()]
    for origin in wanted:
        if origin not in parts:
            parts.append(origin)
    return ",".join(parts)


def patch_env_cors(env_path: Path, *, force: bool = False) -> None:
    """Ensure ``.env.example`` lists Vite/SPA CORS origins."""
    block = build_frontend_env_block().strip("\n") + "\n"
    if not env_path.exists():
        env_path.write_text(block.lstrip("\n"), encoding="utf-8")
        return

    text = env_path.read_text(encoding="utf-8")
    if _ENV_MARKER_BEGIN in text:
        if not force:
            return
        start = text.index(_ENV_MARKER_BEGIN)
        end = text.index(_ENV_MARKER_END) + len(_ENV_MARKER_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        env_path.write_text(text[:start] + block + text[end:], encoding="utf-8")
        return

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("CORS_ALLOWED_ORIGINS="):
            raw = line.split("=", 1)[1].strip()
            merged = _merge_cors_line(raw)
            out.append(f"CORS_ALLOWED_ORIGINS={merged}\n")
            replaced = True
        else:
            out.append(line if line.endswith("\n") else f"{line}\n")
    if not replaced:
        out.append(block)
    env_path.write_text("".join(out), encoding="utf-8")


_NUM_PROXIES_BLOCK = """
# The SPA's nginx is one reverse proxy in front of Django. This lets rate limits
# tell clients apart by their real address (0 = Django is exposed directly).
DJANGO_NUM_PROXIES=1
"""


def patch_env_proxies(env_path: Path) -> None:
    """Append ``DJANGO_NUM_PROXIES=1`` unless the file already sets it."""
    if not env_path.exists():
        env_path.write_text(_NUM_PROXIES_BLOCK.lstrip("\n"), encoding="utf-8")
        return
    text = env_path.read_text(encoding="utf-8")
    if any(line.startswith("DJANGO_NUM_PROXIES=") for line in text.splitlines()):
        return
    if text and not text.endswith("\n"):
        text += "\n"
    env_path.write_text(text + _NUM_PROXIES_BLOCK, encoding="utf-8")


def render_auth_api(*, use_multitenancy: bool) -> str:
    """Render ``apps/users/auth_api.py`` (tenant-scoped user list when multitenant)."""
    env = Environment(
        loader=FileSystemLoader(AUTH_API_TEMPLATES),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("auth_api.py.j2").render(use_multitenancy=use_multitenancy)


def write_auth_api(root: Path, *, force: bool = False) -> Path:
    """Write ``apps/users/auth_api.py`` with email JWT, user list, RegisterView."""
    users = root / "apps" / "users"
    if not users.is_dir():
        raise DjangoPatchError(f"apps/users not found under {root}")
    path = users / "auth_api.py"
    if path.is_file() and not force:
        existing = path.read_text(encoding="utf-8")
        if "class UserListView" in existing and "def get_label" in existing:
            return path
        # Older auth_api — upgrade in place (UserListView / label)
    use_multitenancy = detect_project(root).use_multitenancy
    if use_multitenancy:
        ensure_tenancy_module(root / "apps")
    path.write_text(render_auth_api(use_multitenancy=use_multitenancy), encoding="utf-8")
    return path


def _import_block(*, include_register: bool) -> str:
    lines = [
        _URLS_IMPORT_BEGIN,
        "from apps.users.auth_api import EmailTokenObtainPairView, UserListView",
    ]
    if include_register:
        lines.append("from apps.users.auth_api import RegisterView")
    lines.append(_URLS_IMPORT_END)
    return "\n".join(lines) + "\n"


def patch_urls(root: Path, *, include_register: bool, force: bool = False) -> Path:
    """Wire email JWT obtain, user list, and optional register into ``config/urls.py``."""
    urls_path = root / "config" / "urls.py"
    if not urls_path.is_file():
        raise DjangoPatchError(f"Missing {urls_path}")

    text = urls_path.read_text(encoding="utf-8")
    skip_register = include_register and register_endpoint_present(root) and (
        _URLS_IMPORT_BEGIN not in text
    )
    wire_register = include_register and not skip_register

    # Strip previous frontend import marker block
    if _URLS_IMPORT_BEGIN in text:
        start = text.index(_URLS_IMPORT_BEGIN)
        end = text.index(_URLS_IMPORT_END) + len(_URLS_IMPORT_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]

    # Normalize simplejwt import: keep TokenRefreshView only
    text = re.sub(
        r"from rest_framework_simplejwt\.views import [^\n]+\n",
        "from rest_framework_simplejwt.views import TokenRefreshView\n",
        text,
        count=1,
    )

    # Insert frontend imports after the throttle import (first-party, sorts before
    # apps.users) when present, else after the simplejwt import.
    refresh_import = "from rest_framework_simplejwt.views import TokenRefreshView\n"
    throttle_import = "from apps.core.throttling import throttled\n"
    if refresh_import not in text:
        raise DjangoPatchError("Could not find simplejwt TokenRefreshView import")
    anchor = throttle_import if throttle_import in text else refresh_import
    insert_at = text.index(anchor) + len(anchor)
    text = (
        text[:insert_at]
        + _import_block(include_register=wire_register)
        + text[insert_at:]
    )

    # Replace the obtain view (stock, throttled or already patched) with the email one.
    text, replaced = re.subn(
        r'path\(\s*"api/auth/token/"\s*,\s*[^,]+,\s*name\s*=\s*"token_obtain_pair"\s*\)',
        'path("api/auth/token/", EmailTokenObtainPairView.as_view(), '
        'name="token_obtain_pair")',
        text,
    )
    if not replaced:
        raise DjangoPatchError("Could not find api/auth/token/ path")

    # Remove managed register / users list paths, then re-add
    text = re.sub(
        r'\n?\s*path\(\s*"api/auth/register/"\s*,\s*RegisterView\.as_view\(\)\s*,'
        r'\s*name\s*=\s*"auth_register"\s*\),?',
        "",
        text,
    )
    text = re.sub(
        r'\n?\s*path\(\s*"api/users/"\s*,\s*UserListView\.as_view\(\)\s*,'
        r'\s*name\s*=\s*"user_list"\s*\),?',
        "",
        text,
    )

    match = re.search(
        r'path\(\s*"api/auth/token/refresh/"\s*,[^\n]+\n',
        text,
    )
    if not match:
        raise DjangoPatchError("Could not find token refresh path")
    insert_parts: list[str] = []
    if wire_register:
        insert_parts.append(
            '    path("api/auth/register/", RegisterView.as_view(), '
            'name="auth_register"),\n'
        )
    insert_parts.append(
        '    path("api/users/", UserListView.as_view(), name="user_list"),\n'
    )
    end = match.end()
    text = text[:end] + "".join(insert_parts) + text[end:]

    if not force and skip_register and include_register:
        pass

    urls_path.write_text(text, encoding="utf-8")
    return urls_path


def ensure_user_list_api(root: Path) -> list[Path]:
    """Ensure ``UserListView`` + ``/api/users/`` exist (for CRUD User FK selects)."""
    root = root.resolve()
    include_register = register_endpoint_present(root)
    written: list[Path] = []
    written.append(write_auth_api(root, force=False))
    written.append(patch_urls(root, include_register=include_register, force=False))
    return written


def patch_django_for_frontend(
    root: Path,
    *,
    include_register: bool,
    force: bool = False,
) -> list[Path]:
    """Apply CORS env, auth_api module, and urls wiring. Returns touched paths."""
    root = root.resolve()
    written: list[Path] = []

    env_example = root / ".env.example"
    patch_env_cors(env_example, force=force)
    patch_env_proxies(env_example)
    written.append(env_example)

    auth_api = write_auth_api(root, force=force)
    written.append(auth_api)

    urls = patch_urls(root, include_register=include_register, force=force)
    written.append(urls)

    return written
