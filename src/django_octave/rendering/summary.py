"""Post-generation next-step output."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown

from django_octave.rendering.context import ProjectContext

console = Console()


def print_next_steps(ctx: ProjectContext) -> None:
    target = ctx.target_dir
    lines = [
        f"# Created `{ctx.project_slug}`",
        "",
        f"Location: `{target}`",
        "",
        "## Next steps",
        "",
        f"```bash\ncd {target}\nuv sync\n```",
        "",
        "Copy env and migrate:",
        "",
        "```bash\ncp .env.example .env\nuv run python manage.py migrate\nuv run python manage.py createsuperuser\n```",
        "",
    ]
    if ctx.use_docker:
        lines.extend(
            [
                "### Docker (dev)",
                "",
                "```bash\ndocker compose up --build\n```",
                "",
                "### Docker (prod-oriented)",
                "",
                "```bash\nuv lock   # commit uv.lock for reproducible image builds\n"
                "docker compose -f docker-compose.prod.yml up --build\n```",
                "",
                "Set `DJANGO_ALLOWED_HOSTS` and a real `DJANGO_SECRET_KEY` in `.env` first: "
                "prod settings refuse to start without them.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Run the API:",
                "",
                "```bash\nuv run python manage.py runserver\n```",
                "",
            ]
        )
    lines.extend(
        [
            "OpenAPI UI (after server is up): `/api/schema/swagger-ui/`",
            "",
        ]
    )
    console.print(Markdown("\n".join(lines)))
