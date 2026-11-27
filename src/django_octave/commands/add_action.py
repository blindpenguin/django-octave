"""``django-octave add-action`` — inject a DRF ``@action`` onto a viewset."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown

from django_octave.api_parts.action_gen import (
    ActionOptions,
    action_url_hint,
    parse_http_methods,
    write_action,
)
from django_octave.api_parts.permission_gen import resolve_viewset_class_name
from django_octave.cli import app
from django_octave.commands._common import console, handle_errors
from django_octave.naming import validate_app_name
from django_octave.project.detect import detect_project
from django_octave.rollback import rollback_on_error
from django_octave.safe_names import validate_tag, validate_url_name, validate_url_path


@app.command("add-action")
def add_action_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    viewset: Annotated[
        str | None,
        typer.Argument(help="Model or ModelViewSet class name."),
    ] = None,
    action_name: Annotated[
        str | None,
        typer.Argument(help="Action method name (snake_case)."),
    ] = None,
    detail: Annotated[
        bool,
        typer.Option("--detail/--list", help="Detail (pk) vs collection action."),
    ] = True,
    methods: Annotated[
        str | None,
        typer.Option(
            "--methods",
            help="Comma-separated HTTP methods (default: post detail / get list).",
        ),
    ] = None,
    url_path: Annotated[
        str | None,
        typer.Option("--url-path", help="Optional @action url_path."),
    ] = None,
    url_name: Annotated[
        str | None,
        typer.Option("--url-name", help="Optional @action url_name."),
    ] = None,
    permission: Annotated[
        str | None,
        typer.Option(
            "--permission",
            help="Optional per-action permission (stock or apps.<app>.permissions).",
        ),
    ] = None,
    serializer: Annotated[
        str | None,
        typer.Option(
            "--serializer",
            help="Optional serializer_class (must exist in serializers.py).",
        ),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Spectacular tag (default: detect or snake)."),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing action method."),
    ] = False,
) -> None:
    """Add a DRF @action stub to an existing ModelViewSet."""
    from django_octave.prompts.add_action import resolve_add_action_options

    options = resolve_add_action_options(
        app=app_name,
        viewset=viewset,
        action_name=action_name,
        detail=detail,
        list_action=not detail,
        methods=methods,
        url_path=url_path,
        url_name=url_name,
        permission=permission,
        serializer=serializer,
        tag=tag,
        path=path,
        force=force,
    )
    with handle_errors():
        if options.tag is not None:
            validate_tag(options.tag)
        if options.url_path is not None:
            validate_url_path(options.url_path)
        if options.url_name is not None:
            validate_url_name(options.url_name)
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        app_dir = project.apps_dir / app
        if not app_dir.is_dir():
            raise FileNotFoundError(
                f"App apps.{app} not found. Run: django-octave add {app}"
            )
        method_list = parse_http_methods(options.methods, detail=options.detail)
        vs_class = resolve_viewset_class_name(options.viewset)
        with rollback_on_error(project.root):
            views_path = write_action(
                app_dir,
                options=ActionOptions(
                    app_name=app,
                    viewset=options.viewset,
                    action_name=options.action_name,
                    detail=options.detail,
                    methods=method_list,
                    url_path=options.url_path,
                    url_name=options.url_name,
                    permission=options.permission,
                    serializer=options.serializer,
                    tag=options.tag,
                    force=options.force,
                ),
            )

    hint = action_url_hint(
        app_name=app,
        viewset_class=vs_class,
        action_name=options.action_name,
        detail=options.detail,
        url_path=options.url_path,
    )
    kind = "detail" if options.detail else "list"
    console.print(
        Markdown(
            "\n".join(
                [
                    f"# Action `{options.action_name}` on `{vs_class}`",
                    "",
                    f"- Updated `{views_path.relative_to(project.root)}`",
                    f"- Kind: `{kind}` · methods: `{', '.join(method_list)}`",
                    f"- Route shape: `{hint}`",
                    "",
                    "Router registration is unchanged; `@action` is auto-discovered.",
                    "",
                ]
            )
        )
    )
