"""``django-octave add-viewset`` — create or refresh a ModelViewSet + router."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.api_parts.viewset_gen import ViewSetOptions, write_viewset
from django_octave.cli import app
from django_octave.commands._common import console, handle_errors, resolve_target
from django_octave.prompts.add_serializer import csv_to_list
from django_octave.rollback import rollback_on_error
from django_octave.safe_names import validate_tag


@app.command("add-viewset")
def add_viewset_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    model_name: Annotated[
        str | None,
        typer.Argument(help="Model class name (PascalCase)."),
    ] = None,
    permission: Annotated[
        str,
        typer.Option(
            "--permission",
            help=(
                "Permission class: IsAuthenticated, AllowAny, IsAdminUser, "
                "or a class in apps.<app>.permissions."
            ),
        ),
    ] = "IsAuthenticated",
    filter_fields: Annotated[
        str | None,
        typer.Option("--filter", help="Comma-separated filterset_fields."),
    ] = None,
    search: Annotated[
        str | None,
        typer.Option("--search", help="Comma-separated search_fields."),
    ] = None,
    ordering: Annotated[
        str | None,
        typer.Option("--ordering", help="Comma-separated ordering_fields."),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Spectacular tag (default: snake_case model)."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing viewset class."),
    ] = False,
) -> None:
    """Create or refresh a DRF ModelViewSet and ensure router registration."""
    from django_octave.prompts.add_viewset import resolve_add_viewset_options

    options = resolve_add_viewset_options(
        app=app_name,
        model=model_name,
        permission=permission,
        filters=filter_fields,
        search=search,
        ordering=ordering,
        tag=tag,
        path=path,
        force=force,
    )
    scoping_notes: list[str] = []
    with handle_errors():
        if options.tag is not None:
            validate_tag(options.tag)
        target = resolve_target(options.path, options.app, options.model)
        with rollback_on_error(target.project.root):
            views_path, urls_path = write_viewset(
                target.app_dir,
                options=ViewSetOptions(
                    app_name=target.app,
                    model_name=target.model,
                    permission=options.permission,
                    filters=csv_to_list(options.filters),
                    search=csv_to_list(options.search),
                    ordering=csv_to_list(options.ordering),
                    tag=options.tag,
                    force=options.force,
                    use_multitenancy=target.project.use_multitenancy,
                ),
                notes=scoping_notes,
            )
    project, model = target.project, target.model

    console.print(
        Markdown(
            "\n".join(
                [
                    f"# ViewSet `{model}ViewSet`",
                    "",
                    f"- Updated `{views_path.relative_to(project.root)}`",
                    f"- Router: `{urls_path.relative_to(project.root)}`",
                    f"- Permission: `{options.permission}`",
                    *[f"- {note}" for note in scoping_notes],
                    "",
                    "## Next steps",
                    "",
                    "```bash",
                    f"cd {project.root}",
                    "uv run python manage.py runserver",
                    "```",
                    "",
                ]
            )
        )
    )
