"""Structural checks for the GitHub workflows (pinned actions, least privilege, release gate)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
PIN_COMMENT = re.compile(r"@[0-9a-f]{40}\s+#\s*v\d")


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers(data: dict[str, Any]) -> dict[str, Any]:
    # PyYAML (YAML 1.1) reads the key `on` as the boolean True.
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict)
    return triggers


def _uses(data: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for job in data["jobs"].values():
        if "uses" in job:
            found.append(job["uses"])
        found.extend(step["uses"] for step in job.get("steps", []) if "uses" in step)
    return found


def test_workflows_exist() -> None:
    names = {p.name for p in WORKFLOWS}

    assert {"ci.yml", "release.yml", "docs.yml"} <= names


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_external_action_is_pinned_to_a_commit_sha(path: Path) -> None:
    for ref in _uses(_load(path)):
        if ref.startswith("./"):
            continue
        assert PINNED.match(ref), f"{path.name}: {ref} is not pinned to a 40-character SHA"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_pin_names_its_version_in_a_comment(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if "uses:" in line and "uses: ./" not in line:
            assert PIN_COMMENT.search(line), f"{path.name}: missing '# vX' comment: {line.strip()}"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflows_start_with_no_permissions(path: Path) -> None:
    assert _load(path).get("permissions") == {}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflows_never_use_pull_request_target(path: Path) -> None:
    assert "pull_request_target" not in _triggers(_load(path))


def test_ci_runs_lint_tests_and_docs_on_pull_requests() -> None:
    data = _load(ROOT / ".github" / "workflows" / "ci.yml")
    triggers = _triggers(data)
    steps = " ".join(s.get("run", "") for s in data["jobs"]["test"]["steps"])

    assert "pull_request" in triggers
    assert "workflow_call" in triggers
    assert "ruff check" in steps
    assert "pytest" in steps
    assert "mkdocs build --strict" in steps


def test_ci_end_to_end_job_skips_pull_requests_and_runs_both_suites() -> None:
    e2e = _load(ROOT / ".github" / "workflows" / "ci.yml")["jobs"]["e2e"]

    assert e2e["if"] == "github.event_name != 'pull_request'"
    assert e2e["env"] == {"OCTAVE_E2E": "1", "OCTAVE_E2E_DOCKER": "1"}


def test_ci_uses_read_only_permissions_and_no_secrets() -> None:
    path = ROOT / ".github" / "workflows" / "ci.yml"

    for name, job in _load(path)["jobs"].items():
        assert job["permissions"] == {"contents": "read"}, name
    assert "secrets." not in path.read_text(encoding="utf-8")


def test_release_is_gated_on_the_ci_workflow() -> None:
    jobs = _load(ROOT / ".github" / "workflows" / "release.yml")["jobs"]

    assert jobs["verify"]["uses"] == "./.github/workflows/ci.yml"
    assert jobs["verify"]["permissions"] == {"contents": "read"}
    needs = jobs["release"]["needs"]
    assert "verify" in ([needs] if isinstance(needs, str) else needs)


def test_dependabot_keeps_github_actions_current() -> None:
    data = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))

    ecosystems = {u["package-ecosystem"]: u for u in data["updates"]}
    assert ecosystems["github-actions"]["directory"] == "/"
