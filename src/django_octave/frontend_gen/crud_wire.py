"""Inject CRUD routes and nav links into the Vue SPA via markers."""

from __future__ import annotations

from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.frontend_gen.crud_types import ResourceSpec

ROUTES_BEGIN = "// --- django-octave crud routes begin ---"
ROUTES_END = "// --- django-octave crud routes end ---"
NAV_BEGIN = "// --- django-octave crud nav begin ---"
NAV_END = "// --- django-octave crud nav end ---"


class CrudWireError(OctaveError, ValueError):
    """Raised when router/layout wiring cannot complete."""


def _replace_marker(text: str, begin: str, end: str, body: str) -> str:
    inner = body.rstrip()
    block = f"{begin}\n{inner}\n{end}\n" if inner else f"{begin}\n{end}\n"
    if begin in text and end in text:
        start = text.index(begin)
        stop = text.index(end) + len(end)
        if stop < len(text) and text[stop] == "\n":
            stop += 1
        return text[:start] + block + text[stop:]
    raise CrudWireError(f"Missing markers {begin!r} … {end!r}")


def _ensure_routes_markers(text: str) -> str:
    if ROUTES_BEGIN in text:
        return text
    # Nested AppLayout children: insert after home child route
    needle = "          name: 'home',"
    idx = text.find(needle)
    if idx != -1:
        close = text.find("},", idx)
        if close == -1:
            raise CrudWireError(
                "Could not locate home child route end in router/index.ts"
            )
        insert_at = close + 2
        return (
            text[:insert_at]
            + f"\n        {ROUTES_BEGIN}\n        {ROUTES_END}"
            + text[insert_at:]
        )
    # Legacy flat home route
    legacy = "    {\n      path: '/',\n      name: 'home',"
    idx = text.find(legacy)
    if idx != -1:
        close = text.find("},", idx)
        if close == -1:
            raise CrudWireError("Could not locate home route end in router/index.ts")
        insert_at = close + 2
        return (
            text[:insert_at]
            + f"\n    {ROUTES_BEGIN}\n    {ROUTES_END}"
            + text[insert_at:]
        )
    idx = text.find("\n  ],\n})")
    if idx == -1:
        raise CrudWireError("Could not locate routes array in router/index.ts")
    return text[:idx] + f"\n    {ROUTES_BEGIN}\n    {ROUTES_END}\n" + text[idx:]


def _ensure_nav_markers(text: str) -> str:
    if NAV_BEGIN in text:
        return text
    needle = "const crudNavItems = ["
    idx = text.find(needle)
    if idx != -1:
        insert_at = idx + len(needle)
        return text[:insert_at] + f"\n  {NAV_BEGIN}\n  {NAV_END}" + text[insert_at:]
    raise CrudWireError(
        "Could not locate crudNavItems array in AppLayout.vue "
        "(expected `const crudNavItems = [`)"
    )


def build_routes_body(specs: list[ResourceSpec]) -> str:
    chunks: list[str] = []
    for spec in specs:
        p = spec.model_plural
        chunks.append(
            f"""        {{
          path: '{p}',
          name: '{p}-list',
          component: () => import('../pages/{p}/ListView.vue'),
        }},
        {{
          path: '{p}/new',
          name: '{p}-create',
          component: () => import('../pages/{p}/CreateView.vue'),
        }},
        {{
          path: '{p}/:id',
          name: '{p}-detail',
          component: () => import('../pages/{p}/DetailView.vue'),
        }},
        {{
          path: '{p}/:id/edit',
          name: '{p}-edit',
          component: () => import('../pages/{p}/EditView.vue'),
        }},"""
        )
    return "\n".join(chunks)


def build_nav_body(specs: list[ResourceSpec]) -> str:
    if not specs:
        return ""
    return "\n".join(
        f"  {{ label: '{spec.model_name}', to: '/{spec.model_plural}' }},"
        for spec in specs
    )


def list_crud_plurals_on_disk(frontend_dir: Path) -> list[str]:
    pages = frontend_dir / "src" / "pages"
    if not pages.is_dir():
        return []
    return [
        child.name
        for child in sorted(pages.iterdir())
        if child.is_dir() and (child / "ListView.vue").is_file()
    ]


def wire_crud(frontend_dir: Path, specs: list[ResourceSpec]) -> list[Path]:
    """Rewrite CRUD route/nav markers for the given specs."""
    router_path = frontend_dir / "src" / "router" / "index.ts"
    layout_path = frontend_dir / "src" / "layouts" / "AppLayout.vue"
    if not router_path.is_file():
        raise CrudWireError(f"Missing {router_path}")
    if not layout_path.is_file():
        raise CrudWireError(f"Missing {layout_path}")

    router_text = _ensure_routes_markers(router_path.read_text(encoding="utf-8"))
    router_text = _replace_marker(
        router_text, ROUTES_BEGIN, ROUTES_END, build_routes_body(specs)
    )
    router_path.write_text(router_text, encoding="utf-8")

    layout_text = _ensure_nav_markers(layout_path.read_text(encoding="utf-8"))
    layout_text = _replace_marker(
        layout_text, NAV_BEGIN, NAV_END, build_nav_body(specs)
    )
    layout_path.write_text(layout_text, encoding="utf-8")
    return [router_path, layout_path]
