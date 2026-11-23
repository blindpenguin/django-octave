"""Typed generation context and derivation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering import versions
from django_octave.safe_names import validate_project_name

_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def normalize_slug(name: str) -> str:
    """Normalize a project name to a filesystem/python-safe slug."""
    slug = name.strip().lower().replace("-", "_").replace(" ", "_")
    slug = _SLUG_RE.sub("_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        msg = f"Cannot derive a valid project slug from {name!r}"
        raise ValueError(msg)
    if slug[0].isdigit():
        slug = f"project_{slug}"
    return slug


def database_dependencies(database: DatabaseChoice) -> list[str]:
    """Extra runtime packages for the chosen database."""
    if database is DatabaseChoice.POSTGRES:
        return [versions.PSYCOPG]
    if database is DatabaseChoice.MARIADB:
        return [versions.MYSQLCLIENT]
    return []


def django_db_engine(database: DatabaseChoice) -> str:
    if database is DatabaseChoice.SQLITE:
        return "django.db.backends.sqlite3"
    if database is DatabaseChoice.POSTGRES:
        return "django.db.backends.postgresql"
    return "django.db.backends.mysql"


def example_database_url(database: DatabaseChoice, slug: str) -> str:
    if database is DatabaseChoice.SQLITE:
        return "sqlite:///db.sqlite3"
    if database is DatabaseChoice.POSTGRES:
        return f"postgres://postgres:postgres@localhost:5432/{slug}"
    return f"mysql://root:root@localhost:3306/{slug}"


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Inputs and derived values for Jinja project templates."""

    project_name: str
    project_slug: str
    target_dir: Path
    database: DatabaseChoice
    use_docker: bool
    use_multitenancy: bool
    force: bool
    python_version: str = versions.GENERATED_PYTHON_VERSION
    packages: list[str] = field(default_factory=list)
    dev_packages: list[str] = field(default_factory=list)
    db_engine: str = ""
    db_url_example: str = ""
    include_db_service: bool = False

    @classmethod
    def from_options(cls, options: NewProjectOptions) -> ProjectContext:
        name = validate_project_name(options.name)  # templates copy it into source files
        slug = normalize_slug(name)
        target = (options.path.expanduser().resolve() / slug)
        packages = list(versions.ALWAYS_ON_DEPENDENCIES) + database_dependencies(
            options.database
        )
        return cls(
            project_name=name,
            project_slug=slug,
            target_dir=target,
            database=options.database,
            use_docker=options.docker,
            use_multitenancy=options.multitenancy,
            force=options.force,
            packages=packages,
            dev_packages=list(versions.DEV_DEPENDENCIES),
            db_engine=django_db_engine(options.database),
            db_url_example=example_database_url(options.database, slug),
            include_db_service=options.docker
            and options.database is not DatabaseChoice.SQLITE,
        )
