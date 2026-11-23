"""Tests for project rendering matrices."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import TargetExistsError, render_project


def _options(
    tmp_path: Path,
    *,
    database: DatabaseChoice = DatabaseChoice.SQLITE,
    docker: bool = False,
    multitenancy: bool = False,
    force: bool = False,
    name: str = "Sample",
) -> NewProjectOptions:
    return NewProjectOptions(
        name=name,
        path=tmp_path,
        database=database,
        docker=docker,
        multitenancy=multitenancy,
        frontend=False,
        register=False,
        crud=False,
        force=force,
    )


def test_render_sqlite_baseline(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path))
    target = render_project(ctx)
    assert (target / "manage.py").is_file()
    assert (target / "apps" / "users" / "models.py").is_file()
    assert (target / "apps" / "users" / "migrations" / "0001_initial.py").is_file()
    assert not (target / "Dockerfile").exists()
    assert not (target / "apps" / "core" / "middleware.py").exists()
    assert not (target / "apps" / "core" / "tenancy.py").exists()
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg" not in pyproject
    assert "AUTH_USER_MODEL" in (target / "config" / "settings" / "base.py").read_text(
        encoding="utf-8"
    )
    # WhiteNoise STATIC_ROOT present for a quiet first run.
    assert (target / "staticfiles" / ".gitkeep").is_file()
    gitignore = (target / ".gitignore").read_text(encoding="utf-8")
    assert "staticfiles/*" in gitignore
    assert "!staticfiles/.gitkeep" in gitignore
    local = (target / "config" / "settings" / "local.py").read_text(encoding="utf-8")
    assert "WHITENOISE_USE_FINDERS" in local
    assert "StaticFilesStorage" in local


def test_render_docker_and_multitenancy(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(
        _options(tmp_path, database=DatabaseChoice.POSTGRES, docker=True, multitenancy=True)
    )
    target = render_project(ctx)
    assert (target / "Dockerfile").is_file()
    assert (target / "docker-compose.yml").is_file()
    assert (target / "apps" / "core" / "tenancy.py").is_file()
    assert not (target / "apps" / "core" / "middleware.py").exists()
    assert (target / "apps" / "core" / "migrations" / "0001_initial.py").is_file()
    models = (target / "apps" / "core" / "models.py").read_text(encoding="utf-8")
    assert "class Tenant" in models
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "psycopg" in pyproject


def test_refuse_non_empty_without_force(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, name="Clash"))
    render_project(ctx)
    with pytest.raises(TargetExistsError):
        render_project(ctx)


def test_render_docker_hardening(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(
        _options(tmp_path, database=DatabaseChoice.POSTGRES, docker=True)
    )

    target = render_project(ctx)

    dockerfile = (target / "Dockerfile").read_text(encoding="utf-8")
    assert "USER app" in dockerfile
    assert "uv:latest" not in dockerfile
    assert ".env" in (target / ".dockerignore").read_text(encoding="utf-8").splitlines()
    prod = (target / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in prod
    dev = (target / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:5432:5432"' in dev


def test_render_without_docker_skips_dockerignore(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, docker=False))

    target = render_project(ctx)

    assert not (target / ".dockerignore").exists()


def test_render_prod_settings_reject_placeholder_secret(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path))

    target = render_project(ctx)

    prod = (target / "config" / "settings" / "prod.py").read_text(encoding="utf-8")
    assert "ImproperlyConfigured" in prod
    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    assert "DEFAULT_THROTTLE_RATES" in base


def test_render_multitenancy_binds_tenant_in_drf_not_middleware(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, multitenancy=True))
    target = render_project(ctx)
    settings = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    tenancy = (target / "apps" / "core" / "tenancy.py").read_text(encoding="utf-8")
    assert "Tenant" not in settings.split("MIDDLEWARE", 1)[1].split("]", 1)[0]
    assert "class TenantScopedMixin" in tenancy
    assert "class TenantRequired" in tenancy
    models = (target / "apps" / "core" / "models.py").read_text(encoding="utf-8")
    assert "PermissionDenied" in models  # foreign-tenant save guard


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_all_python_files_parse(tmp_path: Path, multitenancy: bool) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, multitenancy=multitenancy))
    target = render_project(ctx)
    for path in target.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _prod_settings(tmp_path: Path) -> str:
    target = render_project(ProjectContext.from_options(_options(tmp_path)))
    return (target / "config" / "settings" / "prod.py").read_text(encoding="utf-8")


def test_render_prod_settings_require_explicit_allowed_hosts(tmp_path: Path) -> None:
    prod = _prod_settings(tmp_path)

    assert 'os.environ.get("DJANGO_ALLOWED_HOSTS"' in prod
    assert "DJANGO_ALLOWED_HOSTS is not set" in prod
    assert "must not contain '*'" in prod


def test_render_prod_settings_make_api_docs_admin_only(tmp_path: Path) -> None:
    prod = _prod_settings(tmp_path)

    assert '"SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"]' in prod
    assert "rest_framework.authentication.SessionAuthentication" in prod


def test_render_local_settings_leave_api_docs_open(tmp_path: Path) -> None:
    target = render_project(ProjectContext.from_options(_options(tmp_path)))

    local = (target / "config" / "settings" / "local.py").read_text(encoding="utf-8")
    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")

    assert "SERVE_PERMISSIONS" not in local
    assert "SERVE_PERMISSIONS" not in base  # drf-spectacular default (AllowAny) applies


def test_render_env_example_warns_about_production_hosts(tmp_path: Path) -> None:
    target = render_project(ProjectContext.from_options(_options(tmp_path)))

    env = (target / ".env.example").read_text(encoding="utf-8")

    assert "Production: replace with your real host names" in env
    assert "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1" in env


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_auth_throttle_module_is_always_generated(
    tmp_path: Path, multitenancy: bool
) -> None:
    target = render_project(
        ProjectContext.from_options(_options(tmp_path, multitenancy=multitenancy))
    )

    throttling = (target / "apps" / "core" / "throttling.py").read_text(encoding="utf-8")

    assert "class AuthRateThrottle(AnonRateThrottle)" in throttling
    assert 'scope = "auth"' in throttling
    assert "throttle_classes=[AuthRateThrottle]" in throttling


def test_render_token_urls_use_the_auth_throttle(tmp_path: Path) -> None:
    target = render_project(ProjectContext.from_options(_options(tmp_path)))

    urls = (target / "config" / "urls.py").read_text(encoding="utf-8")

    assert "from apps.core.throttling import throttled" in urls
    assert "throttled(TokenObtainPairView)" in urls
    assert "throttled(TokenRefreshView)" in urls
    assert "TokenObtainPairView.as_view()" not in urls
    assert "TokenRefreshView.as_view()" not in urls


def test_render_settings_define_auth_rate_and_proxy_count(tmp_path: Path) -> None:
    target = render_project(ProjectContext.from_options(_options(tmp_path)))

    base = (target / "config" / "settings" / "base.py").read_text(encoding="utf-8")

    assert '"auth": "10/min"' in base
    assert '"anon": "60/min"' in base  # other endpoints unchanged
    assert 'env.int("DJANGO_NUM_PROXIES", default=0)' in base


def test_render_tenant_related_name_includes_the_app_label(tmp_path: Path) -> None:
    target = render_project(ProjectContext.from_options(_options(tmp_path, multitenancy=True)))

    models = (target / "apps" / "core" / "models.py").read_text(encoding="utf-8")

    assert 'related_name="%(app_label)s_%(class)s_set"' in models
    assert 'related_name="%(class)ss"' not in models


def _dockerfile(tmp_path: Path, database: DatabaseChoice) -> str:
    ctx = ProjectContext.from_options(_options(tmp_path, database=database, docker=True))
    return (render_project(ctx) / "Dockerfile").read_text(encoding="utf-8")


def _stage(dockerfile: str, name: str) -> str:
    """Text of the Dockerfile stage called ``name``."""
    parts = re.split(r"(?m)^(?=FROM )", dockerfile)
    return next(p for p in parts if re.match(rf"FROM .* AS {name}\b", p))


@pytest.mark.parametrize("database", list(DatabaseChoice))
def test_render_dockerfile_stage_order_puts_runtime_last(
    tmp_path: Path, database: DatabaseChoice
) -> None:
    dockerfile = _dockerfile(tmp_path, database)

    stages = re.findall(r"(?m)^FROM .* AS (\w+)", dockerfile)

    assert stages == ["dev", "builder", "runtime"]


def test_render_dockerfile_runtime_stage_is_minimal_and_non_root(tmp_path: Path) -> None:
    runtime = _stage(_dockerfile(tmp_path, DatabaseChoice.SQLITE), "runtime")

    assert "curl" not in runtime
    assert "build-essential" not in runtime
    assert "ghcr.io/astral-sh/uv" not in runtime  # no uv binary
    assert "uv run" not in runtime  # nothing re-resolves at boot
    assert 'CMD ["gunicorn", "config.wsgi:application"' in runtime
    assert runtime.index("USER app") < runtime.index("collectstatic")


def test_render_dockerfile_builder_installs_without_dev_and_honours_the_lock(
    tmp_path: Path,
) -> None:
    builder = _stage(_dockerfile(tmp_path, DatabaseChoice.SQLITE), "builder")

    assert "COPY pyproject.toml uv.lock* ./" in builder
    assert "uv sync --locked --no-dev --no-install-project" in builder
    assert "uv sync --no-dev --no-install-project" in builder
    assert "[ -f uv.lock ]" in builder


def test_render_dockerfile_collectstatic_uses_build_only_variables(tmp_path: Path) -> None:
    dockerfile = _dockerfile(tmp_path, DatabaseChoice.SQLITE)
    runtime = _stage(dockerfile, "runtime")

    run = next(line for line in runtime.split("\n\n") if "collectstatic" in line)

    assert "DJANGO_SETTINGS_MODULE=config.settings.prod" in run
    assert "DJANGO_ALLOWED_HOSTS=build.invalid" in run
    assert "DATABASE_URL=sqlite:" in run
    # Set only on that RUN line: never as ENV, so it is not part of the image environment.
    env_blocks = re.findall(r"(?ms)^ENV .*?(?=^\S)", runtime)
    assert not any("DJANGO_SECRET_KEY" in block for block in env_blocks)
    secret = re.search(r"DJANGO_SECRET_KEY=(\S+)", run)
    assert secret is not None
    assert len(secret.group(1)) >= 50  # satisfies the prod settings length check
    assert not secret.group(1).startswith("change-me")


def test_render_dockerfile_dev_stage_keeps_uv_run_for_compose(tmp_path: Path) -> None:
    dev = _stage(_dockerfile(tmp_path, DatabaseChoice.SQLITE), "dev")

    assert "COPY --from=ghcr.io/astral-sh/uv:0.13" in dev
    assert 'CMD ["uv", "run", "gunicorn"' in dev
    assert "USER app" in dev


def test_render_dockerfile_mariadb_dev_libs_only_in_build_stages(tmp_path: Path) -> None:
    dockerfile = _dockerfile(tmp_path, DatabaseChoice.MARIADB)

    assert "default-libmysqlclient-dev" in _stage(dockerfile, "builder")
    assert "default-libmysqlclient-dev" in _stage(dockerfile, "dev")
    runtime = _stage(dockerfile, "runtime")
    assert "libmariadb3" in runtime
    assert "default-libmysqlclient-dev" not in runtime


@pytest.mark.parametrize("database", [DatabaseChoice.SQLITE, DatabaseChoice.POSTGRES])
def test_render_dockerfile_installs_no_mariadb_library_for_other_databases(
    tmp_path: Path, database: DatabaseChoice
) -> None:
    dockerfile = _dockerfile(tmp_path, database)

    assert "libmariadb" not in dockerfile
    assert "libmysqlclient" not in dockerfile


def test_render_dev_compose_builds_the_dev_target(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, docker=True))

    dev = (render_project(ctx) / "docker-compose.yml").read_text(encoding="utf-8")

    assert "build:\n      context: .\n      target: dev\n" in dev
    assert "command: uv run python manage.py runserver" in dev  # bind mount + uv


def test_render_prod_compose_uses_the_image_command_and_default_stage(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, docker=True))

    prod = (render_project(ctx) / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "build: ." in prod
    assert "target:" not in prod  # default (runtime) stage
    assert "command:" not in prod  # CMD of the image starts gunicorn from the venv
    assert "uv run" not in prod


def test_render_readme_documents_lock_hosts_and_api_docs_access(tmp_path: Path) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, docker=True))

    readme = (render_project(ctx) / "README.md").read_text(encoding="utf-8")

    assert "uv lock" in readme
    assert "DJANGO_ALLOWED_HOSTS" in readme
    assert "logged-in admin" in readme
    assert "DJANGO_NUM_PROXIES" in readme
    assert "rate limited" in readme


def test_next_steps_for_docker_mention_the_lock_file_and_hosts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from django_octave.rendering.summary import print_next_steps

    print_next_steps(ProjectContext.from_options(_options(tmp_path, docker=True)))

    out = " ".join(capsys.readouterr().out.split())
    assert "uv lock" in out
    assert "DJANGO_ALLOWED_HOSTS" in out


@pytest.mark.parametrize("multitenancy", [False, True])
def test_render_readme_states_the_default_access_model(tmp_path: Path, multitenancy: bool) -> None:
    ctx = ProjectContext.from_options(_options(tmp_path, multitenancy=multitenancy))

    readme = (render_project(ctx) / "README.md").read_text(encoding="utf-8")

    assert "## Access" in readme
    assert "every authenticated user can read and change **every record**" in readme
    assert "--preset owner --viewset" in readme
    assert "sets the owner on the server" in readme
    assert "uv audit" in readme
    assert ("(within their tenant)" in readme) is multitenancy
