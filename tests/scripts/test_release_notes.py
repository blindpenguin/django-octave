"""Tests for Conventional Commit release-note formatting."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release-notes.py"


def _load():
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_format_groups_user_facing_types() -> None:
    mod = _load()
    md = mod._format(
        [
            "feat(add): support --model for starter class name",
            "fix(serializers): insert nested helpers before parent",
            "docs(layout): document shared api/ mounts",
            "chore: tweak ruff config",
            "chore(release): 0.2.3",
            "wip stuff",
        ]
    )
    assert "### Features" in md
    assert "**add:** support --model for starter class name" in md
    assert "### Fixes" in md
    assert "**serializers:** insert nested helpers before parent" in md
    assert "### Documentation" in md
    assert "chore: tweak" not in md
    assert "0.2.3" not in md
    assert "wip stuff" not in md


def test_breaking_marker() -> None:
    mod = _load()
    md = mod._format(["feat(api)!: rename collection paths"])
    assert "### Breaking changes" in md
    assert "**api:** rename collection paths" in md


# --- BREAKING CHANGE footers ---------------------------------------------------------------


def test_breaking_change_footer_is_listed_first_with_its_own_text() -> None:
    mod = _load()
    body = (
        "Longer explanation of the change.\n\n"
        "BREAKING CHANGE: prod settings now require DJANGO_ALLOWED_HOSTS,\n"
        "and docker build now builds the production image.\n\n"
        "Co-Authored-By: Someone <someone@example.com>\n"
    )

    md = mod._format([("fix(project): harden generated projects", body)])

    assert md.startswith("### Breaking changes\n")
    assert (
        "- **project:** prod settings now require DJANGO_ALLOWED_HOSTS, "
        "and docker build now builds the production image." in md
    )
    assert "Co-Authored-By" not in md
    assert "Someone" not in md
    assert "### Fixes\n- **project:** harden generated projects" in md  # still a fix too


def test_footer_stops_at_a_trailer_without_a_blank_line() -> None:
    mod = _load()
    body = "BREAKING CHANGE: the flag is gone\nCo-Authored-By: A <a@example.com>\n"

    assert mod._breaking_footers(body) == ["the flag is gone"]


def test_hyphenated_spelling_and_several_footers_are_supported() -> None:
    mod = _load()
    body = "BREAKING-CHANGE: first thing\n\nBREAKING CHANGE: second thing\n"

    assert mod._breaking_footers(body) == ["first thing", "second thing"]


def test_a_footer_on_a_non_user_facing_commit_is_still_announced() -> None:
    mod = _load()

    md = mod._format([("chore(deps): bump django", "BREAKING CHANGE: Django 6 is required\n")])

    assert "### Breaking changes\n- **deps:** Django 6 is required" in md
    assert "### Fixes" not in md
    assert "bump django" not in md  # not a user-facing section entry


def test_bang_and_footer_on_one_commit_are_reported_once() -> None:
    mod = _load()

    md = mod._format(
        [("feat(api)!: rename collection paths", "BREAKING CHANGE: collection paths are renamed\n")]
    )

    assert md.count("### Breaking changes") == 1
    assert md.count("collection paths") == 2  # once as the breaking entry, once as the feature
    assert "- **api:** collection paths are renamed" in md
    assert md.count("rename collection paths") == 1  # the subject only appears under Features


def test_plain_subjects_and_empty_bodies_behave_as_before() -> None:
    mod = _load()

    assert mod._format(["fix(a): b"]) == mod._format([("fix(a): b", "")])
    assert "Breaking" not in mod._format([("fix(a): b", "just some prose\nBREAKING mentioned inline\n")])


def test_the_version_bump_commit_is_still_skipped() -> None:
    mod = _load()

    md = mod._format([("chore(release): 0.3.0", "BREAKING CHANGE: ignored\n"), "fix(a): b"])

    assert "ignored" not in md
    assert "0.3.0" not in md


def test_commits_are_read_with_their_bodies_from_a_real_git_repository(
    tmp_path: Path, monkeypatch
) -> None:
    import subprocess

    mod = _load()
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
        "PATH": __import__("os").environ["PATH"], "HOME": str(tmp_path),
    }  # fmt: skip

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, env=env, check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "a").write_text("1", encoding="utf-8")
    git("add", "a")
    git("commit", "-q", "-m", "fix(core): first", "-m", "BREAKING CHANGE: it is different\nnow.")
    (tmp_path / "a").write_text("2", encoding="utf-8")
    git("commit", "-q", "-am", "feat(core): second")
    monkeypatch.chdir(tmp_path)

    commits = mod._commits("", "HEAD")

    assert [subject for subject, _ in commits] == ["feat(core): second", "fix(core): first"]
    assert "BREAKING CHANGE: it is different" in commits[1][1]
    md = mod._format(commits)
    assert "- **core:** it is different now." in md
