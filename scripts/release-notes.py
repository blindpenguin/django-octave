#!/usr/bin/env python3
"""Build Markdown release notes from Conventional Commits between git refs.

Usage:
  scripts/release-notes.py                 # since previous tag → HEAD
  scripts/release-notes.py v0.2.1..HEAD
  scripts/release-notes.py v0.2.1 v0.2.2
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict

_COMMIT_RE = re.compile(
    r"^(?P<type>feat|fix|docs|perf|refactor|test|chore|ci)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$"
)

_SECTION_ORDER = (
    ("feat", "### Features"),
    ("fix", "### Fixes"),
    ("perf", "### Performance"),
    ("docs", "### Documentation"),
)

_USER_FACING = frozenset(t for t, _ in _SECTION_ORDER)


def _run(args: list[str]) -> str:
    return subprocess.check_output(args, text=True).strip()


def _previous_tag(end_ref: str = "HEAD") -> str | None:
    try:
        return _run(
            [
                "git",
                "describe",
                "--tags",
                "--abbrev=0",
                "--match",
                "v[0-9]*",
                f"{end_ref}^",
            ]
        )
    except subprocess.CalledProcessError:
        return None


def _resolve_range(argv: list[str]) -> tuple[str, str]:
    if len(argv) == 0:
        end = "HEAD"
        start = _previous_tag(end)
        if start is None:
            # First release: all commits reachable from HEAD.
            return ("", end)
        return (start, end)
    if len(argv) == 1 and ".." in argv[0]:
        start, end = argv[0].split("..", 1)
        return (start, end or "HEAD")
    if len(argv) == 1:
        return (argv[0], "HEAD")
    if len(argv) == 2:
        return (argv[0], argv[1])
    raise SystemExit(f"Usage: {sys.argv[0]} [from[..to] | from to]")


def _subjects(start: str, end: str) -> list[str]:
    rev = f"{start}..{end}" if start else end
    out = _run(
        [
            "git",
            "log",
            rev,
            "--no-merges",
            "--pretty=format:%s",
        ]
    )
    if not out:
        return []
    return [line for line in out.splitlines() if line.strip()]


def _format(subjects: list[str]) -> str:
    buckets: dict[str, list[str]] = defaultdict(list)
    breaking: list[str] = []
    unmatched: list[str] = []

    for subject in subjects:
        # Skip pure version-bump commits.
        if re.match(r"^chore\(release\):\s*", subject):
            continue
        match = _COMMIT_RE.match(subject)
        if not match:
            unmatched.append(subject)
            continue
        kind = match.group("type")
        scope = match.group("scope")
        text = match.group("subject").strip()
        if match.group("breaking") or text.lower().startswith("breaking"):
            label = f"**{scope}:** {text}" if scope else text
            breaking.append(label)
        if kind not in _USER_FACING:
            continue
        label = f"**{scope}:** {text}" if scope else text
        buckets[kind].append(label)

    lines: list[str] = []
    if breaking:
        lines.append("### Breaking changes")
        lines.extend(f"- {item}" for item in breaking)
        lines.append("")

    for kind, heading in _SECTION_ORDER:
        items = buckets.get(kind) or []
        if not items:
            continue
        lines.append(heading)
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    if not any(buckets.get(k) for k, _ in _SECTION_ORDER) and not breaking:
        lines.append("### Changes")
        if unmatched:
            lines.extend(f"- {s}" for s in unmatched)
        else:
            lines.append("- (no conventional feat/fix/docs/perf commits in range)")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    start, end = _resolve_range(sys.argv[1:])
    print(_format(_subjects(start, end)), end="")


if __name__ == "__main__":
    main()
