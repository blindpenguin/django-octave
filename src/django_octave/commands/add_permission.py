"""``django-octave add-permission`` — create a DRF permission class."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.api_parts.permission_gen import (
    PRESETS,
    PermissionExistsError,
    PermissionOptions,
    PermissionPresetError,
    PermissionWireError,
    resolve_viewset_class_name,
    validate_preset,
    wire_permission_to_viewset,
    write_permission,
)
from django_octave.cli import app
from django_octave.naming import (
    InvalidAppNameError,
    InvalidModelNameError,
    validate_app_name,
    validate_model_name,
)
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


@app.command("add-permission")
def add_permission_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    class_name: Annotated[
        str | None,
        typer.Argument(help="Permission class name (PascalCase, e.g. IsOwner)."),
    ] = None,
    preset: Annotated[
        str,
        typer.Option(
            "--preset",
            help=f"Preset: {', '.join(sorted(PRESETS))} (default: owner).",
        ),
    ] = "owner",
    owner_attr: Annotated[
        str,
        typer.Option(
            "--owner-attr",
            help="Object attribute for owner preset (default: owner).",
        ),
    ] = "owner",
    viewset: Annotated[
        str | None,
        typer.Option(
            "--viewset",
            help="Wire onto Model or ModelViewSet (sets permission_classes).",
        ),
    ] = None,
    append: Annotated[
        bool,
        typer.Option(
            "--append",
            help="With --viewset: append instead of replacing permission_classes.",
        ),
    ] = False,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing permission class."),
    ] = False,
) -> None:
    """Create or refresh a DRF BasePermission subclass in permissions.py."""
    from django_octave.prompts.add_permission import resolve_add_permission_options

    options = resolve_add_permission_options(
        app=app_name,
        class_name=class_name,
        preset=preset,
        owner_attr=owner_attr,
        viewset=viewset,
        append=append,
        path=path,
        force=force,
    )
    try:
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        # Reuse PascalCase validator (IsOwner, IsStaffOrRead, …)
        name = validate_model_name(options.class_name)
        preset_name = validate_preset(
            options.preset, use_multitenancy=project.use_multitenancy
        )
        app_dir = project.apps_dir / app
        if not app_dir.is_dir():
            raise FileNotFoundError(
                f"App apps.{app} not found. Run: django-octave add {app}"
            )
        perm_path = write_permission(
            app_dir,
            options=PermissionOptions(
                app_name=app,
                class_name=name,
                preset=preset_name,
                owner_attr=options.owner_attr,
                viewset=options.viewset,
                append=options.append,
                force=options.force,
            ),
        )
        wired: str | None = None
        if options.viewset:
            vs = resolve_viewset_class_name(options.viewset)
            wire_permission_to_viewset(
                app_dir / "views.py",
                app_name=app,
                viewset_class=vs,
                permission_class=name,
                append=options.append,
            )
            wired = vs
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        InvalidModelNameError,
        PermissionExistsError,
        PermissionPresetError,
        PermissionWireError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    lines = [
        f"# Permission `{name}`",
        "",
        f"- Preset: `{preset_name}`",
        f"- Updated `{perm_path.relative_to(project.root)}`",
    ]
    if wired:
        lines.append(f"- Wired to `{wired}` (`append={options.append}`)")
    lines.extend(
        [
            "",
            "## Next steps",
            "",
            "```bash",
            f"django-octave add-viewset {app} YourModel --permission {name} --force",
            "```",
            "",
        ]
    )
    console.print(Markdown("\n".join(lines)))
