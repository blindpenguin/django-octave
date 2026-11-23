"""Atomic project tree writer."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django_octave.rendering.context import ProjectContext
from django_octave.rendering.engine import (
    TEMPLATES_ROOT,
    context_as_dict,
    create_environment,
)


class TargetExistsError(FileExistsError):
    """Raised when the target directory exists and is non-empty without force."""


def _destination_name(template_rel: Path) -> str:
    name = template_rel.as_posix()
    if name.endswith(".j2"):
        return name[: -len(".j2")]
    return name


def _should_skip(template_rel: Path, ctx: ProjectContext) -> bool:
    parts = template_rel.parts
    # Docker artifacts only when enabled.
    docker_files = {
        "Dockerfile.j2",
        "docker-compose.yml.j2",
        "docker-compose.prod.yml.j2",
        ".dockerignore.j2",
    }
    if template_rel.name in docker_files and not ctx.use_docker:
        return True
    # Multitenancy-only files live under optional path markers.
    if "multitenancy" in parts and not ctx.use_multitenancy:
        return True
    if template_rel.as_posix() == "apps/core/tenancy.py.j2" and not ctx.use_multitenancy:
        return True
    # Concrete core migrations only apply when multitenancy models exist.
    if (
        not ctx.use_multitenancy
        and template_rel.parts[:3] == ("apps", "core", "migrations")
        and template_rel.name.startswith("0")
    ):
        return True
    return False


def render_project(ctx: ProjectContext) -> Path:
    """Render the project template tree into ``ctx.target_dir``.

    Writes into a temporary directory first, then moves into place.
    """
    target = ctx.target_dir
    if target.exists():
        if any(target.iterdir()) and not ctx.force:
            msg = (
                f"Target directory {target} exists and is not empty. "
                "Use --force to overwrite."
            )
            raise TargetExistsError(msg)
    elif target.exists() and not target.is_dir():
        msg = f"Target path exists and is not a directory: {target}"
        raise NotADirectoryError(msg)

    env = create_environment()
    mapping = context_as_dict(ctx)

    with tempfile.TemporaryDirectory(prefix="django-octave-") as tmp:
        tmp_root = Path(tmp) / ctx.project_slug
        tmp_root.mkdir()

        for path in sorted(TEMPLATES_ROOT.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(TEMPLATES_ROOT)
            if _should_skip(rel, ctx):
                continue
            dest_rel = _destination_name(rel)
            dest = tmp_root / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".j2" or path.name.endswith(".j2"):
                template = env.get_template(rel.as_posix())
                dest.write_text(template.render(mapping), encoding="utf-8")
            else:
                shutil.copy2(path, dest)

        # Ensure WhiteNoise's STATIC_ROOT exists even if the template was skipped.
        staticfiles = tmp_root / "staticfiles"
        staticfiles.mkdir(exist_ok=True)
        gitkeep = staticfiles / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

        if target.exists() and ctx.force:
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_root), str(target))

    return target
