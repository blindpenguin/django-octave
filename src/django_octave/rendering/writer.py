"""Atomic project tree writer."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django_octave.rendering.context import ProjectContext
from django_octave.rendering.engine import (
    TEMPLATES_ROOT,
    context_as_dict,
    create_environment,
)


class TargetExistsError(FileExistsError):
    """Raised when the target directory exists and is non-empty without force."""


class TargetSymlinkError(ValueError):
    """Raised when a path the generator would write passes through a symlink."""


class TargetWriteError(ValueError):
    """Raised when a generated file cannot be written into an existing target."""


@dataclass(frozen=True, slots=True)
class RenderReport:
    """Outcome of :func:`render_project_report`."""

    target: Path
    overwritten: int
    """Existing files replaced by generated ones (only with ``--force``)."""


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


def _check_target(ctx: ProjectContext) -> None:
    target = ctx.target_dir
    if not target.exists():
        return
    if not target.is_dir():
        msg = f"Target path exists and is not a directory: {target}"
        raise NotADirectoryError(msg)
    if any(target.iterdir()) and not ctx.force:
        msg = (
            f"Target directory {target} exists and is not empty. "
            "Use --force to overwrite generated files."
        )
        raise TargetExistsError(msg)


def _generated_files(src_root: Path) -> list[Path]:
    return [p for p in sorted(src_root.rglob("*")) if p.is_file()]


def _preflight(src_root: Path, target: Path) -> None:
    """Fail before the first write: no symlinks on write paths, no dir-for-file clashes."""
    for file in _generated_files(src_root):
        current = target
        for part in file.relative_to(src_root).parts:
            current = current / part
            if current.is_symlink():
                msg = (
                    f"Refusing to write through symlink {current}; "
                    "remove it or choose another directory."
                )
                raise TargetSymlinkError(msg)
            if not current.exists():
                break
        else:
            if current.is_dir():
                msg = f"Could not write {current}: a directory exists where a file is expected"
                raise TargetWriteError(msg)


def _place(src_root: Path, target: Path) -> int:
    """Put the rendered tree at ``target``; return how many files were overwritten.

    A missing target receives the tree as is. An existing target is merged
    file by file: generated files overwrite, nothing else is touched or deleted.
    """
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_root), str(target))
        return 0

    _preflight(src_root, target)
    overwritten = 0
    for file in _generated_files(src_root):
        dest = target / file.relative_to(src_root)
        if dest.is_dir():
            # shutil.copy2 would silently copy *into* the directory.
            msg = f"Could not write {dest}: a directory exists where a file is expected"
            raise TargetWriteError(msg)
        existed = dest.exists()
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
        except OSError as exc:
            msg = f"Could not write {dest}: {exc}"
            raise TargetWriteError(msg) from exc
        overwritten += existed
    return overwritten


def render_project_report(ctx: ProjectContext) -> RenderReport:
    """Render the project template tree into ``ctx.target_dir``.

    Renders into a temporary directory first, so a template failure never
    touches the target. An existing target is merged into, never deleted.
    """
    _check_target(ctx)
    target = ctx.target_dir

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

        overwritten = _place(tmp_root, target)

    return RenderReport(target=target, overwritten=overwritten)


def render_project(ctx: ProjectContext) -> Path:
    """Render the project into ``ctx.target_dir`` and return that path."""
    return render_project_report(ctx).target
