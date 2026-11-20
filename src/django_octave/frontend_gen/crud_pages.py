"""Render CRUD Vue pages for a ResourceSpec into frontend/."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from django_octave.frontend_gen.crud_types import CrudField, ResourceSpec
from django_octave.naming import humanize_field_label

CRUD_TEMPLATES_ROOT = (
    Path(__file__).resolve().parent.parent / "templates" / "frontend_crud"
)

_PAGE_TEMPLATES = (
    ("ListView.vue", "pages/ListView.vue.j2"),
    ("DetailView.vue", "pages/DetailView.vue.j2"),
    ("CreateView.vue", "pages/CreateView.vue.j2"),
    ("EditView.vue", "pages/EditView.vue.j2"),
)


def _field_context(f: CrudField) -> dict[str, object]:
    return {
        "name": f.name,
        "label": humanize_field_label(f.name),
        "kind": f.kind,
        "required": f.required,
        "related_plural": f.related_plural,
        "related_label_field": f.related_label_field,
    }


def _template_context(spec: ResourceSpec) -> dict[str, object]:
    writable = [f for f in spec.fields if f.kind != "readonly"]
    list_fields = writable[:6] or list(spec.fields)[:6]
    return {
        "model_name": spec.model_name,
        "model_snake": spec.model_snake,
        "model_plural": spec.model_plural,
        "api_collection": spec.api_collection,
        "label_field": spec.label_field,
        "fields": [_field_context(f) for f in spec.fields],
        "writable_fields": [_field_context(f) for f in writable],
        "list_fields": [_field_context(f) for f in list_fields],
        "has_fk": any(f.kind == "fk" for f in writable),
    }


def create_crud_environment() -> Environment:
    if not CRUD_TEMPLATES_ROOT.is_dir():
        raise FileNotFoundError(f"CRUD templates missing: {CRUD_TEMPLATES_ROOT}")
    return Environment(
        loader=FileSystemLoader(CRUD_TEMPLATES_ROOT),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def ensure_crud_composable(frontend_dir: Path, *, force: bool = False) -> Path:
    """Write shared useCrudResource composable once."""
    dest = frontend_dir / "src" / "composables" / "useCrudResource.ts"
    if dest.is_file() and not force:
        return dest
    env = create_crud_environment()
    text = env.get_template("composables/useCrudResource.ts.j2").render()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def render_crud_pages(
    frontend_dir: Path,
    spec: ResourceSpec,
    *,
    force: bool = False,
) -> list[Path]:
    """Render List/Detail/Create/Edit under ``src/pages/<plural>/``."""
    if not spec.fields:
        raise ValueError(
            f"{spec.app_name}.{spec.model_name}: no fields — enrich ResourceSpec first"
        )

    page_dir = frontend_dir / "src" / "pages" / spec.model_plural
    list_path = page_dir / "ListView.vue"
    if list_path.is_file() and not force:
        raise FileExistsError(
            f"CRUD pages already exist at {page_dir}. Use --force to refresh."
        )

    env = create_crud_environment()
    ctx = _template_context(spec)
    written: list[Path] = []

    written.append(ensure_crud_composable(frontend_dir, force=False))

    page_dir.mkdir(parents=True, exist_ok=True)
    for dest_name, template_name in _PAGE_TEMPLATES:
        dest = page_dir / dest_name
        dest.write_text(env.get_template(template_name).render(ctx), encoding="utf-8")
        written.append(dest)
    return written
