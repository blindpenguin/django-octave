"""Render the Vue + Nuxt UI frontend template tree."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from django_octave.frontend_gen.compose import inject_project_compose
from django_octave.frontend_gen.detect import (
    frontend_configured,
    project_display_name,
    project_slug,
)
from django_octave.frontend_gen.django_patch import patch_django_for_frontend
from django_octave.safe_names import RULE, is_safe_project_name, is_safe_slug

FRONTEND_TEMPLATES_ROOT = (
    Path(__file__).resolve().parent.parent / "templates" / "frontend"
)


class FrontendExistsError(FileExistsError):
    """Raised when a frontend already exists without force."""


class FrontendSetupError(ValueError):
    """Raised when frontend scaffolding cannot complete safely."""


def _destination_name(template_rel: Path) -> str:
    name = template_rel.as_posix()
    if name.endswith(".j2"):
        return name[: -len(".j2")]
    return name


def _should_skip(template_rel: Path, *, include_register: bool) -> bool:
    """Skip register-only templates when registration is off."""
    if include_register:
        return False
    posix = template_rel.as_posix()
    if posix in {
        "src/pages/RegisterView.vue.j2",
        "src/pages/RegisterView.vue",
    }:
        return True
    return False


def create_frontend_environment() -> Environment:
    if not FRONTEND_TEMPLATES_ROOT.is_dir():
        msg = f"Frontend template directory missing: {FRONTEND_TEMPLATES_ROOT}"
        raise FileNotFoundError(msg)
    return Environment(
        loader=FileSystemLoader(FRONTEND_TEMPLATES_ROOT),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_frontend(
    target_dir: Path,
    *,
    project_name: str,
    project_slug: str,
    include_register: bool = False,
) -> Path:
    """Render frontend templates into ``target_dir`` (typically ``<project>/frontend``).

    Always writes a fresh tree into ``target_dir`` (caller handles refuse/force).
    """
    if not project_name.strip():
        raise FrontendSetupError("project_name must not be empty")
    if not project_slug.strip():
        raise FrontendSetupError("project_slug must not be empty")
    if not is_safe_project_name(project_name):
        raise FrontendSetupError(f"Unsafe project_name {project_name!r}: {RULE}")
    if not is_safe_slug(project_slug):
        raise FrontendSetupError(f"Unsafe project_slug {project_slug!r}")

    env = create_frontend_environment()
    mapping: dict[str, object] = {
        "project_name": project_name,
        "project_slug": project_slug,
        "include_register": include_register,
    }

    with tempfile.TemporaryDirectory(prefix="django-octave-frontend-") as tmp:
        tmp_root = Path(tmp) / "frontend"
        tmp_root.mkdir()
        for path in sorted(FRONTEND_TEMPLATES_ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(FRONTEND_TEMPLATES_ROOT)
            if _should_skip(rel, include_register=include_register):
                continue
            dest = tmp_root / _destination_name(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if path.name.endswith(".j2"):
                template = env.get_template(rel.as_posix())
                dest.write_text(template.render(mapping), encoding="utf-8")
            else:
                shutil.copy2(path, dest)

        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_root), str(target_dir))

    return target_dir


def scaffold_frontend(
    root: Path,
    *,
    include_register: bool = False,
    force: bool = False,
    project_name: str | None = None,
    project_slug_name: str | None = None,
) -> Path:
    """Render ``frontend/`` only (no Django/Compose patches). Prefer ``setup_frontend``."""
    root = root.resolve()
    if frontend_configured(root) and not force:
        raise FrontendExistsError(
            "Frontend already looks configured "
            "(frontend/package.json or non-empty frontend/). Use --force to refresh."
        )

    name = project_name or project_display_name(root)
    slug = project_slug_name or project_slug(root)
    target = root / "frontend"
    return render_frontend(
        target,
        project_name=name,
        project_slug=slug,
        include_register=include_register,
    )


def setup_frontend(
    root: Path,
    *,
    include_register: bool = False,
    force: bool = False,
    project_name: str | None = None,
    project_slug_name: str | None = None,
) -> list[Path]:
    """Full frontend setup: SPA tree, Django CORS/auth, optional Compose.

    Returns paths written or updated.
    """
    root = root.resolve()
    written: list[Path] = []

    frontend_dir = scaffold_frontend(
        root,
        include_register=include_register,
        force=force,
        project_name=project_name,
        project_slug_name=project_slug_name,
    )
    written.append(frontend_dir)

    patched = patch_django_for_frontend(
        root,
        include_register=include_register,
        force=force,
    )
    written.extend(patched)

    written.extend(inject_project_compose(root, force=force))
    return written
