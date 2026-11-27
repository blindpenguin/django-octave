"""The config patchers cope with files that were reformatted or edited by hand.

Each case takes a project django-octave generated, edits ``config/urls.py`` or
``config/settings/base.py`` the way a user or a formatter plausibly would, runs the patch
and checks the *structure* of the result (parsed with ``ast``). Exact whitespace of the
inserted lines is pinned by the golden files in ``test_patch_golden.py``.

Files whose shape cannot be understood must be refused with the manual step and left
byte-identical.
"""

from __future__ import annotations

import ast
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from django_octave.frontend_gen.django_patch import (
    DjangoPatchError,
    patch_django_for_frontend,
)
from django_octave.options import DatabaseChoice
from django_octave.project.patch import PatchError, patch_installed_apps, patch_urls
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import render_project

TOKEN_ROUTE = '    path("api/auth/token/", throttled(TokenObtainPairView), name="token_obtain_pair"),\n'
REFRESH_ROUTE = '    path("api/auth/token/refresh/", throttled(TokenRefreshView), name="token_refresh"),\n'


@pytest.fixture(scope="module")
def template_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    options = NewProjectOptions(
        name="Shapes",
        path=tmp_path_factory.mktemp("shapes"),
        database=DatabaseChoice.SQLITE,
        docker=False,
        multitenancy=False,
        frontend=False,
        register=False,
        crud=False,
        force=False,
    )
    return render_project(ProjectContext.from_options(options))


@pytest.fixture
def project(template_project: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "proj"
    shutil.copytree(template_project, copy)
    return copy


def _urls(root: Path) -> Path:
    return root / "config" / "urls.py"


def _settings(root: Path) -> Path:
    return root / "config" / "settings" / "base.py"


def _replace(text: str, old: str, new: str) -> str:
    """``str.replace`` that fails loudly when the edit did not apply."""
    assert old in text, f"edit did not apply: {old!r}"
    return text.replace(old, new)


# --- edits to config/urls.py -----------------------------------------------------------------


def _wrapped(text: str) -> str:
    text = _replace(
        text,
        TOKEN_ROUTE,
        '    path(\n        "api/auth/token/",\n        throttled(TokenObtainPairView),\n'
        '        name="token_obtain_pair",\n    ),\n',
    )
    return _replace(
        text,
        REFRESH_ROUTE,
        '    path(\n        "api/auth/token/refresh/",\n        throttled(TokenRefreshView),\n'
        '        name="token_refresh",\n    ),\n',
    )


def _paren_imports(text: str) -> str:
    text = _replace(
        text,
        "from django.urls import path\n",
        "from django.urls import (\n    path,\n)\n",
    )
    return _replace(
        text,
        "from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView\n",
        "from rest_framework_simplejwt.views import (\n    TokenObtainPairView,\n"
        "    TokenRefreshView,\n)\n",
    )


def _single_quotes(text: str) -> str:
    return _replace(text, '"', "'")


def _annotated(text: str) -> str:
    return _replace(text, "urlpatterns = [", "urlpatterns: list = [")


def _bracket_in_string(text: str) -> str:
    return _replace(
        text,
        '    path("admin/", admin.site.urls),\n',
        '    path("admin/", admin.site.urls),\n    re_path(r"^legacy[0-9]]/$", legacy),\n',
    )


def _plus_equals(text: str) -> str:
    return text.rstrip("\n") + '\n\nurlpatterns += [\n    path("health/", health),\n]\n'


def _comments(text: str) -> str:
    text = _replace(
        text,
        '    path("admin/", admin.site.urls),\n',
        '    # --- admin ---\n    path("admin/", admin.site.urls),  # the admin\n\n',
    )
    return _replace(text, "    ),\n]\n", "    ),  # redoc\n]\n")


def _no_trailing_comma(text: str) -> str:
    return _replace(text, "    ),\n]\n", "    )\n]\n")


def _one_line_urlpatterns(text: str) -> str:
    start = text.index("urlpatterns = [")
    return text[:start] + 'urlpatterns = [path("admin/", admin.site.urls)]\n'


URL_EDITS: dict[str, Callable[[str], str]] = {
    "wrapped-calls": _wrapped,
    "parenthesized-imports": _paren_imports,
    "single-quotes": _single_quotes,
    "annotated-urlpatterns": _annotated,
    "bracket-in-string": _bracket_in_string,
    "plus-equals-block": _plus_equals,
    "comments": _comments,
    "no-trailing-comma": _no_trailing_comma,
}
ADD_ONLY_URL_EDITS: dict[str, Callable[[str], str]] = {
    "one-line-urlpatterns": _one_line_urlpatterns,
}


def _apply(path: Path, edit: Callable[[str], str]) -> str:
    original = path.read_text(encoding="utf-8")
    path.write_text(edit(original), encoding="utf-8")
    return path.read_text(encoding="utf-8")


# --- reading the result ---------------------------------------------------------------------


def _routes(text: str) -> list[tuple[str, str]]:
    """``(route, view source)`` for every ``path()``/``re_path()`` call in the file."""
    routes = []
    for node in ast.walk(ast.parse(text)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"path", "re_path"}
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
        ):
            routes.append((str(node.args[0].value), ast.unparse(node.args[1])))
    return routes


def _includes(text: str, module: str) -> int:
    return sum(
        1
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "include"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == module
    )


def _imported(text: str, module: str) -> set[str]:
    return {
        alias.name
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
    }


# Lines that have to change when an item is added after them: the last item needs a comma
# now, and a one-line list gains the item on the same line.
MUST_CHANGE: dict[str, tuple[str, ...]] = {
    "no-trailing-comma": ("    )",),
    "one-line-urlpatterns": ('urlpatterns = [path("admin/", admin.site.urls)]',),
}


def _kept_lines(
    original: str,
    patched: str,
    *,
    changed: tuple[str, ...],
    exact: tuple[str, ...] = (),
) -> list[str]:
    """Original lines that vanished although the patch had no reason to touch them."""
    now = {line.rstrip() for line in patched.splitlines()}
    return [
        line.rstrip()
        for line in original.splitlines()
        if line.strip()
        and line.rstrip() not in now
        and line.rstrip() not in exact
        and not any(token in line for token in changed)
    ]


# --- add: config/urls.py ----------------------------------------------------------------------


@pytest.mark.parametrize("edit", sorted({**URL_EDITS, **ADD_ONLY_URL_EDITS}))
def test_add_includes_the_app_urls_whatever_the_shape_of_urls_py(
    project: Path, edit: str
) -> None:
    original = _apply(_urls(project), {**URL_EDITS, **ADD_ONLY_URL_EDITS}[edit])

    changed = patch_urls(_urls(project), "blog")

    patched = _urls(project).read_text(encoding="utf-8")
    assert changed is True
    ast.parse(patched)
    assert _includes(patched, "apps.blog.urls") == 1
    assert "include" in _imported(patched, "django.urls")
    assert (
        _kept_lines(
            original,
            patched,
            changed=("from django.urls import",),
            exact=MUST_CHANGE.get(edit, ()),
        )
        == []
    )


@pytest.mark.parametrize("edit", sorted({**URL_EDITS, **ADD_ONLY_URL_EDITS}))
def test_add_is_idempotent_whatever_the_shape_of_urls_py(
    project: Path, edit: str
) -> None:
    _apply(_urls(project), {**URL_EDITS, **ADD_ONLY_URL_EDITS}[edit])
    patch_urls(_urls(project), "blog")
    once = _urls(project).read_text(encoding="utf-8")

    changed = patch_urls(_urls(project), "blog")

    assert changed is False
    assert _urls(project).read_text(encoding="utf-8") == once


def test_add_urls_refuses_a_urlpatterns_it_cannot_edit_and_gives_the_manual_step(
    project: Path,
) -> None:
    _apply(
        _urls(project),
        lambda t: _replace(t, "urlpatterns = [", "urlpatterns = base_patterns + ["),
    )
    before = _urls(project).read_bytes()

    with pytest.raises(PatchError) as raised:
        patch_urls(_urls(project), "blog")

    message = str(raised.value)
    assert "config/urls.py" in message.replace("\\", "/")
    assert 'path("api/", include("apps.blog.urls")),' in message
    assert _urls(project).read_bytes() == before


def test_add_urls_refuses_a_file_without_urlpatterns(project: Path) -> None:
    _urls(project).write_text('"""Empty."""\n', encoding="utf-8")

    with pytest.raises(
        PatchError, match=r'path\("api/", include\("apps\.blog\.urls"\)\),'
    ):
        patch_urls(_urls(project), "blog")


def test_add_urls_refuses_a_file_that_does_not_parse_and_leaves_it_alone(
    project: Path,
) -> None:
    _urls(project).write_text("urlpatterns = [\n\ndef broken(:\n", encoding="utf-8")
    before = _urls(project).read_bytes()

    with pytest.raises(PatchError) as raised:
        patch_urls(_urls(project), "blog")

    assert "urls.py" in str(raised.value)
    assert _urls(project).read_bytes() == before


# --- add: config/settings/base.py ------------------------------------------------------------


def _apps_block(text: str) -> tuple[int, int]:
    start = text.index("INSTALLED_APPS")
    return start, text.index("\n]", start) + 2


def _one_line_apps(text: str) -> str:
    start, end = _apps_block(text)
    entries = [
        line.strip().rstrip(",")
        for line in text[start:end].splitlines()[1:-1]
        if line.strip() and not line.strip().startswith("#")
    ]
    return text[:start] + "INSTALLED_APPS = [" + ", ".join(entries) + "]\n" + text[end:]


def _tuple_apps(text: str) -> str:
    start, end = _apps_block(text)
    block = text[start:end].replace("INSTALLED_APPS = [", "INSTALLED_APPS = (", 1)
    return text[:start] + block[:-2] + "\n)\n" + text[end:]


def _apps_no_trailing_comma(text: str) -> str:
    return _replace(text, '    "apps.users",\n]\n', '    "apps.users"\n]\n')


def _apps_single_quotes(text: str) -> str:
    start, end = _apps_block(text)
    return text[:start] + text[start:end].replace('"', "'") + text[end:]


def _apps_annotated(text: str) -> str:
    return _replace(text, "INSTALLED_APPS = [", "INSTALLED_APPS: list[str] = [")


def _apps_comments(text: str) -> str:
    text = _replace(
        text, '    "apps.core",\n', '    # project apps\n    "apps.core",\n'
    )
    return _replace(
        text, '    "apps.users",\n]\n', '    "apps.users",  # custom user model\n]\n'
    )


APPS_EDITS: dict[str, Callable[[str], str]] = {
    "one-line": _one_line_apps,
    "tuple": _tuple_apps,
    "no-trailing-comma": _apps_no_trailing_comma,
    "single-quotes": _apps_single_quotes,
    "annotated": _apps_annotated,
    "comments": _apps_comments,
}


def _installed_apps(text: str) -> list[str]:
    for node in ast.parse(text).body:
        targets = (
            [node.target]
            if isinstance(node, ast.AnnAssign)
            else getattr(node, "targets", [])
        )
        if any(isinstance(t, ast.Name) and t.id == "INSTALLED_APPS" for t in targets):
            return [str(e.value) for e in node.value.elts]  # type: ignore[attr-defined]
    raise AssertionError("INSTALLED_APPS not found")


def _other_statements(text: str) -> list[str]:
    """Everything except the INSTALLED_APPS statement, as a normalized dump."""
    out = []
    for node in ast.parse(text).body:
        targets = (
            [node.target]
            if isinstance(node, ast.AnnAssign)
            else getattr(node, "targets", [])
        )
        if any(isinstance(t, ast.Name) and t.id == "INSTALLED_APPS" for t in targets):
            continue
        out.append(ast.dump(node))
    return out


@pytest.mark.parametrize("edit", sorted(APPS_EDITS))
def test_installed_apps_gets_the_app_in_that_list_and_nothing_else_changes(
    project: Path, edit: str
) -> None:
    original = _apply(_settings(project), APPS_EDITS[edit])
    apps_before = _installed_apps(original)

    changed = patch_installed_apps(_settings(project), "apps.blog")

    patched = _settings(project).read_text(encoding="utf-8")
    assert changed is True
    assert _installed_apps(patched) == [*apps_before, "apps.blog"]
    assert _other_statements(patched) == _other_statements(original)


@pytest.mark.parametrize("edit", sorted(APPS_EDITS))
def test_installed_apps_patch_is_idempotent(project: Path, edit: str) -> None:
    _apply(_settings(project), APPS_EDITS[edit])
    patch_installed_apps(_settings(project), "apps.blog")
    once = _settings(project).read_text(encoding="utf-8")

    changed = patch_installed_apps(_settings(project), "apps.blog")

    assert changed is False
    assert _settings(project).read_text(encoding="utf-8") == once


def test_an_app_mentioned_only_in_a_comment_is_still_added(project: Path) -> None:
    _apply(_settings(project), lambda t: '# TODO register "apps.blog" soon\n' + t)

    changed = patch_installed_apps(_settings(project), "apps.blog")

    assert changed is True
    assert "apps.blog" in _installed_apps(
        _settings(project).read_text(encoding="utf-8")
    )


SPLIT_APPS = (
    "DJANGO_APPS = ['django.contrib.admin']\n"
    "LOCAL_APPS = ['apps.core', 'apps.users']\n"
    "INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS\n"
)


def test_installed_apps_built_from_other_lists_is_refused_with_the_manual_step(
    project: Path,
) -> None:
    _settings(project).write_text(SPLIT_APPS, encoding="utf-8")
    before = _settings(project).read_bytes()

    with pytest.raises(PatchError) as raised:
        patch_installed_apps(_settings(project), "apps.blog")

    message = str(raised.value)
    assert "INSTALLED_APPS" in message
    assert '"apps.blog"' in message
    assert "base.py" in message
    assert _settings(project).read_bytes() == before


def test_installed_apps_built_from_other_lists_is_fine_when_the_app_is_already_listed(
    project: Path,
) -> None:
    _settings(project).write_text(
        SPLIT_APPS.replace("'apps.users']", "'apps.users', 'apps.blog']"),
        encoding="utf-8",
    )
    before = _settings(project).read_bytes()

    assert patch_installed_apps(_settings(project), "apps.blog") is False

    assert _settings(project).read_bytes() == before


def test_installed_apps_patch_never_touches_the_other_lists(project: Path) -> None:
    # Regression: with INSTALLED_APPS on one line, the old pattern ran on into MIDDLEWARE.
    original = _apply(_settings(project), _one_line_apps)

    patch_installed_apps(_settings(project), "apps.blog")

    patched = _settings(project).read_text(encoding="utf-8")
    assert "apps.blog" not in _middleware(patched)
    assert _middleware(patched) == _middleware(original)


def _middleware(text: str) -> list[str]:
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "MIDDLEWARE" for t in node.targets
        ):
            return [str(e.value) for e in node.value.elts]  # type: ignore[attr-defined]
    raise AssertionError("MIDDLEWARE not found")


# --- add-frontend: config/urls.py -----------------------------------------------------------


@pytest.mark.parametrize("edit", sorted(URL_EDITS))
@pytest.mark.parametrize("register", [True, False])
def test_add_frontend_wires_the_routes_whatever_the_shape_of_urls_py(
    project: Path, edit: str, register: bool
) -> None:
    original = _apply(_urls(project), URL_EDITS[edit])

    patch_django_for_frontend(project, include_register=register)

    patched = _urls(project).read_text(encoding="utf-8")
    ast.parse(patched)
    routes = dict(_routes(patched))
    assert routes["api/auth/token/"] == "EmailTokenObtainPairView.as_view()"
    assert "api/auth/token/refresh/" in routes
    assert [r for r, _v in _routes(patched)].count("api/users/") == 1
    assert [r for r, _v in _routes(patched)].count("api/auth/register/") == (
        1 if register else 0
    )
    assert {"EmailTokenObtainPairView", "UserListView"} <= _imported(
        patched, "apps.users.auth_api"
    )
    assert "TokenRefreshView" in _imported(patched, "rest_framework_simplejwt.views")
    assert "TokenObtainPairView" not in _imported(
        patched, "rest_framework_simplejwt.views"
    )
    assert (
        _kept_lines(
            original,
            patched,
            changed=(
                "TokenObtainPairView",
                "from rest_framework_simplejwt.views import",
            ),
        )
        == []
    )


@pytest.mark.parametrize("edit", sorted(URL_EDITS))
def test_add_frontend_is_idempotent_whatever_the_shape_of_urls_py(
    project: Path, edit: str
) -> None:
    _apply(_urls(project), URL_EDITS[edit])
    patch_django_for_frontend(project, include_register=True)
    once = _urls(project).read_text(encoding="utf-8")

    patch_django_for_frontend(project, include_register=True)

    assert _urls(project).read_text(encoding="utf-8") == once


def test_add_frontend_refuses_a_missing_token_route_and_says_what_it_wanted(
    project: Path,
) -> None:
    _apply(_urls(project), lambda t: _replace(t, TOKEN_ROUTE, ""))
    before = _urls(project).read_bytes()

    with pytest.raises(DjangoPatchError) as raised:
        patch_django_for_frontend(project, include_register=False)

    message = str(raised.value)
    assert "api/auth/token/" in message
    assert "EmailTokenObtainPairView" in message
    assert _urls(project).read_bytes() == before


def test_add_frontend_refuses_a_missing_refresh_route_and_says_what_it_wanted(
    project: Path,
) -> None:
    _apply(_urls(project), lambda t: _replace(t, REFRESH_ROUTE, ""))
    before = _urls(project).read_bytes()

    with pytest.raises(DjangoPatchError) as raised:
        patch_django_for_frontend(project, include_register=False)

    message = str(raised.value)
    assert "api/auth/token/refresh/" in message
    assert "api/users/" in message
    assert _urls(project).read_bytes() == before


def test_add_frontend_refuses_a_file_that_does_not_parse_and_leaves_it_alone(
    project: Path,
) -> None:
    _apply(_urls(project), lambda t: t + "\ndef broken(:\n")
    before = _urls(project).read_bytes()

    with pytest.raises(DjangoPatchError) as raised:
        patch_django_for_frontend(project, include_register=False)

    assert "urls.py" in str(raised.value)
    assert _urls(project).read_bytes() == before


def test_add_frontend_refuses_unbalanced_managed_block_markers(project: Path) -> None:
    patch_django_for_frontend(project, include_register=False)
    _apply(
        _urls(project),
        lambda t: _replace(t, "# --- django-octave frontend imports end ---\n", ""),
    )
    before = _urls(project).read_bytes()

    with pytest.raises(DjangoPatchError) as raised:
        patch_django_for_frontend(project, include_register=False)

    assert "frontend imports" in str(raised.value)
    assert _urls(project).read_bytes() == before


# --- quote style of what is added --------------------------------------------------------------


def test_add_writes_the_new_route_in_the_quote_style_of_the_file(project: Path) -> None:
    _apply(_urls(project), _single_quotes)

    patch_urls(_urls(project), "blog")

    patched = _urls(project).read_text(encoding="utf-8")
    assert "path('api/', include('apps.blog.urls'))," in patched
    assert 'include("apps.blog.urls")' not in patched


def test_add_writes_the_new_route_with_double_quotes_when_the_file_has_no_precedent(
    project: Path,
) -> None:
    _apply(_urls(project), _one_line_urlpatterns)

    patch_urls(_urls(project), "blog")

    # The one remaining route is written with double quotes, so that is the style.
    assert 'path("api/", include("apps.blog.urls"))' in _urls(project).read_text(
        encoding="utf-8"
    )


def test_installed_apps_gets_the_new_entry_in_the_quote_style_of_the_list(
    project: Path,
) -> None:
    _apply(_settings(project), _apps_single_quotes)

    patch_installed_apps(_settings(project), "apps.blog")

    assert "'apps.blog'" in _settings(project).read_text(encoding="utf-8")
    assert '"apps.blog"' not in _settings(project).read_text(encoding="utf-8")


# --- nothing broken is ever written -----------------------------------------------------------


class _BrokenModule:
    """Stands in for the edited module and prints source that does not parse."""

    code = "urlpatterns = [\n"


def _broken_result(*_args: object, **_kwargs: object) -> _BrokenModule:
    return _BrokenModule()


def test_installed_apps_patch_refuses_to_write_a_result_that_does_not_parse(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("django_octave.project.patch.with_sequence", _broken_result)
    before = _settings(project).read_bytes()

    with pytest.raises(PatchError, match="does not parse"):
        patch_installed_apps(_settings(project), "apps.blog")

    assert _settings(project).read_bytes() == before


def test_urls_patch_refuses_to_write_a_result_that_does_not_parse(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("django_octave.project.patch.with_sequence", _broken_result)
    before = _urls(project).read_bytes()

    with pytest.raises(PatchError, match="does not parse"):
        patch_urls(_urls(project), "blog")

    assert _urls(project).read_bytes() == before


# --- add-frontend leaves what the user owns alone ------------------------------------------------


def test_add_frontend_keeps_the_stock_obtain_import_while_the_file_still_uses_it(
    project: Path,
) -> None:
    _apply(
        _urls(project),
        lambda t: _replace(
            t,
            '    path("admin/", admin.site.urls),\n',
            '    path("admin/", admin.site.urls),\n'
            '    path("legacy/token/", TokenObtainPairView.as_view()),\n',
        ),
    )

    patch_django_for_frontend(project, include_register=False)

    patched = _urls(project).read_text(encoding="utf-8")
    assert "TokenObtainPairView" in _imported(patched, "rest_framework_simplejwt.views")
    assert dict(_routes(patched))["legacy/token/"] == "TokenObtainPairView.as_view()"
    assert (
        dict(_routes(patched))["api/auth/token/"]
        == "EmailTokenObtainPairView.as_view()"
    )


def test_add_frontend_does_not_move_a_users_route_the_user_already_has(
    project: Path,
) -> None:
    hand = '    path("api/users/", my_users, name="users"),\n'
    _apply(
        _urls(project), lambda t: _replace(t, "    ),\n]\n", "    ),\n" + hand + "]\n")
    )

    patch_django_for_frontend(project, include_register=False)

    routes = _routes(_urls(project).read_text(encoding="utf-8"))
    assert [(r, v) for r, v in routes if r == "api/users/"] == [
        ("api/users/", "my_users")
    ]
    assert routes[-1] == ("api/users/", "my_users")  # still where the user put it


def _import_count(text: str, module: str, name: str) -> int:
    return sum(
        1
        for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names
        if alias.name == name
    )


def test_add_frontend_does_not_import_names_the_user_already_imports(
    project: Path,
) -> None:
    _apply(
        _urls(project),
        lambda t: _replace(
            t,
            "from apps.core.throttling import throttled\n",
            "from apps.core.throttling import throttled\n"
            "from apps.users.auth_api import UserListView\n",
        ),
    )

    patch_django_for_frontend(project, include_register=False)

    patched = _urls(project).read_text(encoding="utf-8")
    assert _import_count(patched, "apps.users.auth_api", "UserListView") == 1
    assert (
        _import_count(patched, "apps.users.auth_api", "EmailTokenObtainPairView") == 1
    )


def test_add_frontend_does_not_remove_a_hand_wired_register_route_when_register_is_off(
    project: Path,
) -> None:
    hand = '    path("api/auth/register/", my_register, name="my_register"),\n'
    _apply(_urls(project), lambda t: _replace(t, REFRESH_ROUTE, REFRESH_ROUTE + hand))

    patch_django_for_frontend(project, include_register=False)

    assert ("api/auth/register/", "my_register") in _routes(
        _urls(project).read_text(encoding="utf-8")
    )


def test_add_frontend_does_not_duplicate_a_hand_wired_register_route(
    project: Path,
) -> None:
    hand = '    path("api/auth/register/", my_register, name="my_register"),\n'
    _apply(_urls(project), lambda t: _replace(t, REFRESH_ROUTE, REFRESH_ROUTE + hand))

    patch_django_for_frontend(project, include_register=True)
    patch_django_for_frontend(project, include_register=True)

    patched = _urls(project).read_text(encoding="utf-8")
    assert [r for r, _v in _routes(patched)].count("api/auth/register/") == 1
    assert "RegisterView" not in _imported(patched, "apps.users.auth_api")


def test_add_frontend_writes_the_new_routes_in_the_quote_style_of_the_file(
    project: Path,
) -> None:
    _apply(_urls(project), _single_quotes)

    patch_django_for_frontend(project, include_register=True)

    patched = _urls(project).read_text(encoding="utf-8")
    assert "path('api/users/', UserListView.as_view(), name='user_list')," in patched
    assert (
        "path('api/auth/register/', RegisterView.as_view(), name='auth_register'),"
        in patched
    )
    assert 'path("api/' not in patched
