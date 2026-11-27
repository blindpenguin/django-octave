"""Probe every free-text option of every command for code injection.

The options are *discovered* from the Typer definition, so a new option is covered
automatically. For each option and each payload the command must either fail
(exit != 0, project tree unchanged) or leave only files in which the payload is
not executable. It must never print a traceback or write unparsable Python.
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from django_octave.cli import app

runner = CliRunner()
MARKER = "octave-probe"

PAYLOADS = [
    'x", __import__("os").system("octave-probe"), "y',  # inside call arguments
    'x"], __import__("os").system("octave-probe"), ["y',  # inside a list
    "x', __import__('os').system('octave-probe'), 'y",  # single quotes
    'x"]; __import__("os").system("octave-probe"); y=["',  # statement break
    'x\nimport os\nos.system("octave-probe")\n',  # newline
]

# Positional arguments the fixture project can satisfy. A command with any other
# positional argument fails the test, so new commands cannot be skipped silently.
ARGUMENTS = {
    "name": "probeapp",  # `add NAME` creates an app (undone after every probe)
    "app_name": "blog",
    "model_name": "Post",
    "viewset": "Post",
    "action_name": "probe_action",
    "task_name": "probe_task",
    "class_name": "IsProbe",
}
# Commands exempt from probing, each with a reason (their free text is covered elsewhere).
EXEMPT = {
    "new": "its only free text is the project name (tests/naming/test_project_name.py)",
}


def _discover() -> list[tuple[str, str, list[str], bool]]:
    """Return ``(command, option, positional_arg_names, has_force)`` for every str option."""
    found = []
    for name, command in sorted(typer.main.get_command(app).commands.items()):
        arguments = [p.name for p in command.params if p.param_type_name == "argument"]
        has_force = any(p.name == "force" for p in command.params)
        for param in command.params:
            if param.param_type_name != "option" or param.name == "path":
                continue
            annotation = param.type_descriptor.annotation
            if annotation is str or annotation == list[str]:
                found.append((name, param.opts[0], arguments, has_force))
    return found


DISCOVERED = _discover()


def test_discovery_finds_the_known_free_text_options() -> None:
    options = {(command, option) for command, option, _, _ in DISCOVERED}

    # If Typer's introspection API changes, fail loudly instead of probing nothing.
    assert {
        ("add-viewset", "--tag"),
        ("add-action", "--url-path"),
        ("add-action", "--url-name"),
        ("add-action", "--tag"),
        ("add-permission", "--owner-attr"),
        ("add-model", "--field"),
    } <= options
    assert len(options) >= 25


def test_every_command_with_free_text_options_is_probeable_or_exempt() -> None:
    for command, option, arguments, _ in DISCOVERED:
        if command in EXEMPT:
            continue
        unknown = [a for a in arguments if a not in ARGUMENTS]
        assert not unknown, (
            f"{command} {option}: positional argument(s) {unknown} are not in ARGUMENTS; "
            "extend the table (or add the command to EXEMPT with a reason)."
        )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and ".venv" not in p.parts
    }


def _restore(root: Path, baseline: dict[str, bytes]) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        relative = str(path.relative_to(root))
        if path.is_file() and relative not in baseline:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    for relative, data in baseline.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)


def _executable_marker_calls(root: Path) -> list[str]:
    """Calls that run the payload, and Python files that no longer parse."""
    problems = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            problems.append(f"{path.relative_to(root)}: does not parse")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and any(
                isinstance(a, ast.Constant) and a.value == MARKER for a in node.args
            ):
                problems.append(
                    f"{path.relative_to(root)}: executes {ast.unparse(node)[:60]}"
                )
    return problems


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent = tmp_path_factory.mktemp("probe")

    def run(*args: str) -> None:
        result = runner.invoke(app, list(args))
        assert result.exit_code == 0, result.output

    run("new", "demo", "-d", "sqlite", "--no-docker", "--no-multitenancy", "--no-frontend",
        "--path", str(parent))  # fmt: skip
    root = parent / "demo"
    run("add", "blog", "--path", str(root))
    run(
        "add-model",
        "blog",
        "Post",
        "--fields",
        "title:char,body:text",
        "--path",
        str(root),
    )
    run("add-celery", "--path", str(root))
    return root


@pytest.mark.parametrize(
    ("command", "option", "arguments", "has_force"),
    [pytest.param(*d, id=f"{d[0]} {d[1]}") for d in DISCOVERED if d[0] not in EXEMPT],
)
def test_free_text_option_cannot_inject_code(
    project: Path, command: str, option: str, arguments: list[str], has_force: bool
) -> None:
    baseline = _snapshot(project)
    positional = [ARGUMENTS[a] for a in arguments if a in ARGUMENTS]
    failures: list[str] = []

    for payload in PAYLOADS:
        args = [command, *positional, option, payload, "--path", str(project)]
        if has_force:
            args.append("--force")
        result = runner.invoke(app, args)
        label = f"payload {payload!r}"

        if "Traceback" in result.output:
            failures.append(f"{label}: traceback in output")
        if result.exit_code != 0:
            if _snapshot(project) != baseline:
                failures.append(
                    f"{label}: exit {result.exit_code} but the project tree changed"
                )
        else:
            failures += [f"{label}: {p}" for p in _executable_marker_calls(project)]
        _restore(project, baseline)

    assert not failures, f"{command} {option}:\n  " + "\n  ".join(failures)
    assert _snapshot(project) == baseline
    shutil.rmtree(project / ".pytest_cache", ignore_errors=True)


@pytest.mark.parametrize("option", ["--field", "--fields"])
def test_related_name_value_cannot_inject_code(project: Path, option: str) -> None:
    """The payload sits in the ``related_name=`` position, where it would be quoted."""
    baseline = _snapshot(project)
    failures: list[str] = []

    for payload in PAYLOADS:
        spec = f"owner:fk:to=users.User:related_name={payload}"
        args = [
            "add-model",
            "blog",
            "Post",
            option,
            spec,
            "--path",
            str(project),
            "--force",
        ]
        result = runner.invoke(app, args)
        label = f"payload {payload!r}"

        if "Traceback" in result.output:
            failures.append(f"{label}: traceback in output")
        if result.exit_code == 0:
            failures.append(f"{label}: accepted as a related_name")
        if _snapshot(project) != baseline:
            failures.append(f"{label}: the project tree changed")
        _restore(project, baseline)

    assert not failures, f"add-model {option}:\n  " + "\n  ".join(failures)
    shutil.rmtree(project / ".pytest_cache", ignore_errors=True)
