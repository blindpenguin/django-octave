"""Generate Celery shared_task stubs and optional Beat schedule entries."""

from __future__ import annotations

import ast
import keyword
import re
from dataclasses import dataclass
from pathlib import Path

from django_octave.celery_gen.detect import celery_configured
from django_octave.errors import OctaveError

_TASK_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_BEAT_ASSIGN_RE = re.compile(
    r"app\.conf\.beat_schedule\s*=\s*\{",
)


class TaskGenError(OctaveError, ValueError):
    """Raised when task generation cannot complete."""


class TaskExistsError(OctaveError, FileExistsError):
    """Raised when a task already exists without force."""


class CrontabError(TaskGenError):
    """Raised when a crontab expression is invalid."""


@dataclass(frozen=True, slots=True)
class TaskOptions:
    app_name: str
    task_name: str
    bind: bool = False
    every: float | None = None
    crontab: str | None = None
    force: bool = False


def validate_task_name(raw: str) -> str:
    name = raw.strip()
    if not _TASK_NAME_RE.match(name) or keyword.iskeyword(name):
        raise TaskGenError(
            f"Invalid task name {raw!r}: must be a snake_case Python identifier "
            "starting with a letter"
        )
    return name


def parse_crontab(expr: str) -> dict[str, str]:
    """Parse a 5-field cron expression into celery.schedules.crontab kwargs."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise CrontabError(
            f"Invalid crontab {expr!r}: expected 5 fields "
            "(minute hour day_of_month month_of_year day_of_week)"
        )
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return {
        "minute": minute,
        "hour": hour,
        "day_of_month": day_of_month,
        "month_of_year": month_of_year,
        "day_of_week": day_of_week,
    }


def build_task_stub(*, task_name: str, bind: bool) -> str:
    if bind:
        return f"""@shared_task(bind=True)
def {task_name}(self) -> str:
    # TODO: implement
    return "ok"
"""
    return f"""@shared_task
def {task_name}() -> str:
    # TODO: implement
    return "ok"
"""


def _ensure_tasks_module(path: Path, *, app_name: str) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return f'''"""Celery tasks for {app_name}."""

from __future__ import annotations

from celery import shared_task
'''


def _has_function(tree: ast.AST, name: str) -> bool:
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            return True
    return False


def _upsert_task_in_module(
    text: str, *, task_name: str, bind: bool, force: bool
) -> str:
    stub = build_task_stub(task_name=task_name, bind=bind).rstrip() + "\n"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise TaskGenError(f"Could not parse tasks.py: {exc}") from exc

    if _has_function(tree, task_name):
        if not force:
            raise TaskExistsError(
                f"Task {task_name!r} already exists. Use --force to replace."
            )
        # Replace function including decorator lines immediately above
        lines = text.splitlines(keepends=True)
        # Find function by walking AST for lineno
        target: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == task_name
            ):
                target = node
                break
        assert target is not None
        start = target.lineno - 1
        # include decorators
        if target.decorator_list:
            start = min(d.lineno for d in target.decorator_list) - 1
        end = target.end_lineno or target.lineno
        # end_lineno is 1-based inclusive
        new_lines = lines[:start] + [stub if stub.endswith("\n") else stub + "\n"]
        # preserve trailing newline style: stub already has newline
        if end < len(lines) and lines[end - 1].endswith("\n") is False:
            pass
        rest = lines[end:]
        # drop blank line immediately after old def if present to avoid triple blanks
        text = "".join(new_lines + rest)
        if "from celery import shared_task" not in text:
            text = _ensure_shared_task_import(text)
        return text

    # Append
    if "from celery import shared_task" not in text and "shared_task" not in text:
        text = _ensure_shared_task_import(text)
    text = text.rstrip() + "\n\n" + stub
    if not text.endswith("\n"):
        text += "\n"
    return text


def _ensure_shared_task_import(text: str) -> str:
    line = "from celery import shared_task\n"
    if "from celery import shared_task" in text:
        return text
    marker = "from __future__ import annotations\n"
    if marker in text:
        return text.replace(marker, marker + "\n" + line, 1)
    return line + "\n" + text


def _crontab_call(fields: dict[str, str]) -> str:
    parts = ", ".join(f'{k}="{v}"' for k, v in fields.items())
    return f"crontab({parts})"


def _schedule_entry(
    *,
    schedule_key: str,
    task_path: str,
    every: float | None,
    crontab_expr: str | None,
) -> str:
    if every is not None and crontab_expr is not None:
        raise TaskGenError("Use only one of --every or --crontab, not both")
    if every is not None:
        return (
            f'    "{schedule_key}": {{\n'
            f'        "task": "{task_path}",\n'
            f'        "schedule": {float(every)},\n'
            f"    }},\n"
        )
    assert crontab_expr is not None
    fields = parse_crontab(crontab_expr)
    return (
        f'    "{schedule_key}": {{\n'
        f'        "task": "{task_path}",\n'
        f'        "schedule": {_crontab_call(fields)},\n'
        f"    }},\n"
    )


def _ensure_crontab_import(text: str) -> str:
    if "from celery.schedules import crontab" in text:
        return text
    line = "from celery.schedules import crontab\n"
    # after celery import if present
    if "from celery import Celery" in text:
        return text.replace(
            "from celery import Celery\n",
            "from celery import Celery\n" + line,
            1,
        )
    return line + text


def _merge_beat_schedule(
    celery_path: Path,
    *,
    schedule_key: str,
    task_path: str,
    every: float | None,
    crontab_expr: str | None,
    force: bool,
) -> None:
    text = celery_path.read_text(encoding="utf-8")
    if crontab_expr is not None:
        text = _ensure_crontab_import(text)

    entry = _schedule_entry(
        schedule_key=schedule_key,
        task_path=task_path,
        every=every,
        crontab_expr=crontab_expr,
    )

    # Detect existing key
    key_pat = re.compile(rf'["\']{re.escape(schedule_key)}["\']\s*:')
    if key_pat.search(text):
        if not force:
            raise TaskExistsError(
                f"Beat schedule key {schedule_key!r} already exists. Use --force."
            )
        # Replace the dict entry for this key (naive brace match from key)
        m = key_pat.search(text)
        assert m is not None
        start = m.start()
        # walk back to include leading whitespace / optional comma context
        # find opening of this entry — start at key
        brace = text.find("{", m.end())
        if brace < 0:
            raise TaskGenError(
                f"Could not parse beat_schedule entry for {schedule_key!r}"
            )
        depth = 0
        i = brace
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        # include trailing comma/newline
        end = i
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == ",":
            end += 1
        if end < len(text) and text[end] == "\n":
            end += 1
        # find line start for indentation replacement
        line_start = text.rfind("\n", 0, start) + 1
        text = text[:line_start] + entry + text[end:]
        celery_path.write_text(text, encoding="utf-8")
        return

    match = _BEAT_ASSIGN_RE.search(text)
    if not match:
        raise TaskGenError(
            f"{celery_path}: could not find app.conf.beat_schedule = {{...}}"
        )
    # Find matching closing brace of the assignment dict
    open_brace = text.find("{", match.start())
    depth = 0
    close = open_brace
    while close < len(text):
        if text[close] == "{":
            depth += 1
        elif text[close] == "}":
            depth -= 1
            if depth == 0:
                break
        close += 1
    if depth != 0:
        raise TaskGenError(f"{celery_path}: unclosed beat_schedule dict")

    inner = text[open_brace + 1 : close]
    if inner.strip():
        new_inner = inner.rstrip() + "\n" + entry
    else:
        new_inner = "\n" + entry
    text = text[: open_brace + 1] + new_inner + text[close:]
    celery_path.write_text(text, encoding="utf-8")


def write_task(root: Path, *, options: TaskOptions) -> Path:
    """Write/upsert a shared_task and optionally merge beat_schedule.

    Returns path to ``apps/<app>/tasks.py``.
    """
    root = root.resolve()
    if not celery_configured(root) or not (root / "config" / "celery.py").is_file():
        raise TaskGenError("Celery is not configured. Run: django-octave add-celery")
    if options.every is not None and options.crontab is not None:
        raise TaskGenError("Use only one of --every or --crontab, not both")
    if options.every is not None and options.every <= 0:
        raise TaskGenError("--every must be a positive number of seconds")

    app_dir = root / "apps" / options.app_name
    if not app_dir.is_dir():
        raise TaskGenError(
            f"App apps.{options.app_name} not found. Run: django-octave add {options.app_name}"
        )

    tasks_path = app_dir / "tasks.py"
    text = _ensure_tasks_module(tasks_path, app_name=options.app_name)
    text = _upsert_task_in_module(
        text,
        task_name=options.task_name,
        bind=options.bind,
        force=options.force,
    )
    tasks_path.write_text(text, encoding="utf-8")

    if options.every is not None or options.crontab is not None:
        schedule_key = f"{options.app_name}.{options.task_name}"
        task_path = f"apps.{options.app_name}.tasks.{options.task_name}"
        _merge_beat_schedule(
            root / "config" / "celery.py",
            schedule_key=schedule_key,
            task_path=task_path,
            every=options.every,
            crontab_expr=options.crontab,
            force=options.force,
        )

    return tasks_path
