"""``django-octave add-task`` — create a Celery ``@shared_task`` stub."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown

from django_octave.celery_gen import TaskExistsError, TaskGenError, write_task
from django_octave.celery_gen.task_gen import (
    CrontabError,
    TaskOptions,
    validate_task_name,
)
from django_octave.cli import app
from django_octave.naming import InvalidAppNameError, validate_app_name
from django_octave.project.detect import NotOctaveProjectError, detect_project

err_console = Console(stderr=True)
console = Console()


@app.command("add-task")
def add_task_cmd(
    app_name: Annotated[
        str | None,
        typer.Argument(help="Existing app under apps/."),
    ] = None,
    task_name: Annotated[
        str | None,
        typer.Argument(help="Task function name (snake_case)."),
    ] = None,
    bind: Annotated[
        bool,
        typer.Option("--bind", help="Use @shared_task(bind=True)."),
    ] = False,
    every: Annotated[
        float | None,
        typer.Option("--every", help="Beat interval in seconds."),
    ] = None,
    crontab: Annotated[
        str | None,
        typer.Option("--crontab", help='5-field cron expression, e.g. "0 8 * * *".'),
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root (default: current directory)."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing task / schedule entry."),
    ] = False,
) -> None:
    """Create or refresh a Celery shared_task in apps/<app>/tasks.py."""
    from django_octave.prompts.add_task import resolve_add_task_options

    options = resolve_add_task_options(
        app=app_name,
        task_name=task_name,
        bind=bind,
        every=every,
        crontab=crontab,
        path=path,
        force=force,
    )
    try:
        project = detect_project(options.path)
        app = validate_app_name(options.app)
        name = validate_task_name(options.task_name)
        tasks_path = write_task(
            project.root,
            options=TaskOptions(
                app_name=app,
                task_name=name,
                bind=options.bind,
                every=options.every,
                crontab=options.crontab,
                force=options.force,
            ),
        )
    except (
        NotOctaveProjectError,
        InvalidAppNameError,
        TaskExistsError,
        TaskGenError,
        CrontabError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        err_console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    lines = [
        f"# Task `{name}`",
        "",
        f"- Updated `{tasks_path.relative_to(project.root)}`",
    ]
    if options.every is not None or options.crontab is not None:
        lines.append(f"- Beat schedule key `{app}.{name}` in `config/celery.py`")
    lines.extend(
        [
            "",
            "## Next steps",
            "",
            "```bash",
            "uv run celery -A config worker -l INFO",
            "uv run celery -A config beat -l INFO",
            "```",
            "",
        ]
    )
    console.print(Markdown("\n".join(lines)))
