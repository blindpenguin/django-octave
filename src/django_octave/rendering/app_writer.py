"""Render domain app templates into apps/<name>."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from django_octave.errors import OctaveError
from django_octave.rendering.app_context import AppContext
from django_octave.tenancy import ensure_tenancy_module

APP_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates" / "app"


class AppExistsError(OctaveError, FileExistsError):
    """Raised when the app directory already exists without force."""


def _destination_name(template_rel: Path) -> str:
    name = template_rel.as_posix()
    if name.endswith(".j2"):
        return name[: -len(".j2")]
    return name


def render_app(ctx: AppContext) -> Path:
    """Render app templates into ``ctx.app_dir``."""
    target = ctx.app_dir
    if target.exists() and any(target.iterdir()) and not ctx.force:
        msg = f"App directory {target} already exists. Use --force to replace it."
        raise AppExistsError(msg)

    if ctx.use_multitenancy:
        ensure_tenancy_module(ctx.app_dir.parent)

    if not APP_TEMPLATES_ROOT.is_dir():
        msg = f"App template directory missing: {APP_TEMPLATES_ROOT}"
        raise FileNotFoundError(msg)

    env = Environment(
        loader=FileSystemLoader(APP_TEMPLATES_ROOT),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    mapping = ctx.as_template_dict()

    with tempfile.TemporaryDirectory(prefix="django-octave-app-") as tmp:
        tmp_root = Path(tmp) / ctx.app_name
        tmp_root.mkdir()
        for path in sorted(APP_TEMPLATES_ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(APP_TEMPLATES_ROOT)
            dest = tmp_root / _destination_name(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if path.name.endswith(".j2"):
                template = env.get_template(rel.as_posix())
                dest.write_text(template.render(mapping), encoding="utf-8")
            else:
                shutil.copy2(path, dest)

        if target.exists() and ctx.force:
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_root), str(target))

    return target
