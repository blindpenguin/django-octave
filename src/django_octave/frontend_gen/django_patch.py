"""Patch Django project files for Vue frontend (CORS, JWT email obtain, register)."""

from __future__ import annotations

from pathlib import Path

import libcst as cst
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from django_octave.errors import OctaveError
from django_octave.project.cst_edit import (
    ConfigEditError,
    check_result,
    dominant_quote,
    find_import_from,
    find_sequence,
    imported_names,
    insert_item_after,
    insert_marked_block,
    name_is_used,
    parse_source,
    remove_import_name,
    remove_items,
    remove_marked_block,
    route_of,
    sequence_of,
    view_of,
    with_sequence,
    with_view,
)
from django_octave.project.detect import detect_project
from django_octave.tenancy import ensure_tenancy_module

AUTH_API_TEMPLATES = (
    Path(__file__).resolve().parent.parent / "templates" / "frontend_django"
)

_ENV_MARKER_BEGIN = "# --- django-octave frontend begin ---"
_ENV_MARKER_END = "# --- django-octave frontend end ---"
_URLS_IMPORT_BEGIN = "# --- django-octave frontend imports begin ---"
_URLS_IMPORT_END = "# --- django-octave frontend imports end ---"

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080"
)


class DjangoPatchError(OctaveError, ValueError):
    """Raised when Django patches cannot complete safely."""


def build_frontend_env_block() -> str:
    return f"""
{_ENV_MARKER_BEGIN}
# Vite (5173) and prod SPA nginx (8080) origins for the Vue frontend
CORS_ALLOWED_ORIGINS={_DEFAULT_CORS_ORIGINS}
{_ENV_MARKER_END}
"""


class _Routes(cst.CSTVisitor):
    """Every ``path("route", view, ...)`` call in a file: ``(route, view source)``."""

    def __init__(self) -> None:
        self.found: list[tuple[str, str | None]] = []

    def visit_Call(self, node: cst.Call) -> bool:
        route = route_of(node)
        if route is not None:
            view = view_of(node)
            self.found.append((route, _code(view) if view is not None else None))
        return True


def _code(node: cst.CSTNode) -> str:
    return cst.Module([]).code_for_node(node).strip()


def _routes_of(module: cst.Module) -> list[tuple[str, str | None]]:
    visitor = _Routes()
    module.visit(visitor)
    return visitor.found


def _routes_in(root: Path) -> list[tuple[str, str | None]]:
    """The routes wired in ``config/urls.py``; nothing if it is missing or does not parse."""
    urls = root / "config" / "urls.py"
    if not urls.is_file():
        return []
    try:
        return _routes_of(parse_source(urls.read_text(encoding="utf-8"), urls))
    except ConfigEditError:
        return []


def register_endpoint_present(root: Path) -> bool:
    """True if a register URL is already wired in ``config/urls.py``."""
    return any(
        route.startswith("api/auth/register") for route, _view in _routes_in(root)
    )


def users_list_endpoint_present(root: Path) -> bool:
    """True if ``api/users/`` is wired for FK selects."""
    return any(route.startswith("api/users/") for route, _view in _routes_in(root))


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
    path.write_text(
        render_auth_api(use_multitenancy=use_multitenancy), encoding="utf-8"
    )
    return path


_AUTH_API = "apps.users.auth_api"
_SIMPLEJWT_VIEWS = "rest_framework_simplejwt.views"
_REGISTER_VIEW = "RegisterView.as_view()"
_USERS_VIEW = "UserListView.as_view()"
_TOKEN_VIEW = "EmailTokenObtainPairView.as_view()"


def _is_managed_register(route: str, view: str | None) -> bool:
    return route == "api/auth/register/" and view == _REGISTER_VIEW


def _route_call(quote: str, route: str, view: str, name: str) -> cst.BaseExpression:
    # Fixed text only: the route, view and name are constants of this module.
    return cst.parse_expression(
        f"path({quote}{route}{quote}, {view}, name={quote}{name}{quote})"
    )


def _indexes(sequence: cst.List | cst.Tuple, matches) -> list[int]:
    return [i for i, el in enumerate(sequence.elements) if matches(el.value)]


def _patched_urls(source: str, path: Path, *, include_register: bool) -> str:
    module = parse_source(source, path)
    routes = _routes_of(module)

    # A register route the user wired by hand (anything but the managed shape) is theirs:
    # it is never duplicated and never removed. Decided from the routes themselves, so the
    # answer does not change after the first run adds the managed import block.
    hand_register = any(
        route.startswith("api/auth/register") and not _is_managed_register(route, view)
        for route, view in routes
    )
    wire_register = include_register and not hand_register

    module = remove_marked_block(module, _URLS_IMPORT_BEGIN, _URLS_IMPORT_END)

    ref = find_sequence(module, "urlpatterns")
    if ref is None:
        msg = (
            f"urlpatterns in {path} is not a plain list that django-octave can edit, so "
            f"add-frontend cannot wire the email token view ({_TOKEN_VIEW} on "
            '"api/auth/token/") and the "api/users/" route. Wire them yourself.'
        )
        raise ConfigEditError(msg)
    sequence = sequence_of(module, ref)
    quote = dominant_quote(sequence)

    # The obtain route gets the email view; its name and formatting stay as they are.
    token = _indexes(sequence, lambda v: route_of(v) == "api/auth/token/")
    if not token:
        msg = (
            f'Could not find the "api/auth/token/" route in urlpatterns of {path}; '
            f"add-frontend replaces its view with {_TOKEN_VIEW}."
        )
        raise ConfigEditError(msg)
    elements = list(sequence.elements)
    for i in token:
        call = elements[i].value
        assert isinstance(call, cst.Call)
        elements[i] = elements[i].with_changes(
            value=with_view(call, cst.parse_expression(_TOKEN_VIEW))
        )
    sequence = sequence.with_changes(elements=elements)

    if not include_register:
        sequence = remove_items(
            sequence,
            lambda v: _is_managed_register(
                route_of(v) or "", _code(view_of(v)) if view_of(v) is not None else None
            ),
        )

    refresh = _indexes(sequence, lambda v: route_of(v) == "api/auth/token/refresh/")
    if not refresh:
        msg = (
            f'Could not find the "api/auth/token/refresh/" route in urlpatterns of {path}; '
            'add-frontend adds the "api/users/" route'
            + (' and the "api/auth/register/" route' if wire_register else "")
            + " right after it."
        )
        raise ConfigEditError(msg)

    # Existing routes stay where they are; missing ones go right after the refresh route.
    present = {r for r, _v in _routes_of(module)}
    after = refresh[0]
    if wire_register and not any(r.startswith("api/auth/register") for r in present):
        route = _route_call(
            quote, "api/auth/register/", _REGISTER_VIEW, "auth_register"
        )
        sequence = insert_item_after(sequence, after, route)
        after += 1
    if not any(r.startswith("api/users/") for r in present):
        route = _route_call(quote, "api/users/", _USERS_VIEW, "user_list")
        sequence = insert_item_after(sequence, after, route)
    module = with_sequence(module, ref, sequence)

    # simplejwt: the stock obtain view is no longer used by the file.
    if not name_is_used(module, "TokenObtainPairView"):
        module = remove_import_name(module, _SIMPLEJWT_VIEWS, "TokenObtainPairView")

    # The managed import block: only the names that are not imported yet.
    have = imported_names(module, _AUTH_API)
    lines = []
    group = [n for n in ("EmailTokenObtainPairView", "UserListView") if n not in have]
    if group:
        lines.append(f"from {_AUTH_API} import {', '.join(group)}")
    if wire_register and "RegisterView" not in have:
        lines.append(f"from {_AUTH_API} import RegisterView")
    if lines:
        anchor = find_import_from(module, "apps.core.throttling")
        if anchor is None:
            anchor = find_import_from(module, _SIMPLEJWT_VIEWS)
        if anchor is None:
            msg = (
                f"Could not find the simplejwt TokenRefreshView import in {path}; add "
                "these lines to the imports yourself: " + "; ".join(lines)
            )
            raise ConfigEditError(msg)
        module = insert_marked_block(
            module,
            after_index=anchor,
            begin=_URLS_IMPORT_BEGIN,
            end=_URLS_IMPORT_END,
            statements=lines,
        )
    return check_result(module.code, path)


def patch_urls(root: Path, *, include_register: bool) -> Path:
    """Wire email JWT obtain, user list, and optional register into ``config/urls.py``.

    Edits the syntax tree, so wrapped lines, either quote style and parenthesized imports
    are fine. A file that cannot be understood raises :class:`DjangoPatchError` saying what
    to do by hand, and is left untouched.
    """
    urls_path = root / "config" / "urls.py"
    if not urls_path.is_file():
        raise DjangoPatchError(f"Missing {urls_path}")
    source = urls_path.read_text(encoding="utf-8")
    try:
        patched = _patched_urls(source, urls_path, include_register=include_register)
    except ConfigEditError as exc:
        raise DjangoPatchError(str(exc)) from exc
    if patched != source:
        urls_path.write_text(patched, encoding="utf-8")
    return urls_path


def ensure_user_list_api(root: Path) -> list[Path]:
    """Ensure ``UserListView`` + ``/api/users/`` exist (for CRUD User FK selects)."""
    root = root.resolve()
    include_register = register_endpoint_present(root)
    written: list[Path] = []
    written.append(write_auth_api(root, force=False))
    written.append(patch_urls(root, include_register=include_register))
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

    urls = patch_urls(root, include_register=include_register)
    written.append(urls)

    return written
