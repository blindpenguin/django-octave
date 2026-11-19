"""Jinja2 environment for project templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from django_octave.rendering.context import ProjectContext

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates" / "project"


def create_environment() -> Environment:
    if not TEMPLATES_ROOT.is_dir():
        msg = f"Template directory missing: {TEMPLATES_ROOT}"
        raise FileNotFoundError(msg)
    return Environment(
        loader=FileSystemLoader(TEMPLATES_ROOT),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def context_as_dict(ctx: ProjectContext) -> dict[str, object]:
    return {
        "project_name": ctx.project_name,
        "project_slug": ctx.project_slug,
        "database": ctx.database.value,
        "use_docker": ctx.use_docker,
        "use_multitenancy": ctx.use_multitenancy,
        "python_version": ctx.python_version,
        "packages": ctx.packages,
        "dev_packages": ctx.dev_packages,
        "db_engine": ctx.db_engine,
        "db_url_example": ctx.db_url_example,
        "include_db_service": ctx.include_db_service,
        "is_sqlite": ctx.database.value == "sqlite",
        "is_postgres": ctx.database.value == "postgres",
        "is_mariadb": ctx.database.value == "mariadb",
    }
