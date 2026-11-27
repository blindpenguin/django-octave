"""`new --force` overwrites generated files and never deletes anything else."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.options import DatabaseChoice
from django_octave.prompts.new_project import NewProjectOptions
from django_octave.rendering import writer
from django_octave.rendering.context import ProjectContext
from django_octave.rendering.writer import (
    TargetExistsError,
    TargetSymlinkError,
    TargetWriteError,
    render_project,
    render_project_report,
)


def _ctx(tmp_path: Path, *, force: bool) -> ProjectContext:
    return ProjectContext.from_options(
        NewProjectOptions(
            name="Sample",
            path=tmp_path,
            database=DatabaseChoice.SQLITE,
            docker=False,
            multitenancy=False,
            frontend=False,
            register=False,
            crud=False,
            force=force,
        )
    )


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_force_keeps_foreign_files_and_overwrites_generated_ones(
    tmp_path: Path,
) -> None:
    target = render_project(_ctx(tmp_path, force=False))
    (target / "notes.txt").write_text("mine", encoding="utf-8")
    (target / "apps" / "mine").mkdir()
    (target / "apps" / "mine" / "models.py").write_text("# mine", encoding="utf-8")
    (target / "manage.py").write_text("# edited", encoding="utf-8")

    report = render_project_report(_ctx(tmp_path, force=True))

    assert (target / "notes.txt").read_text(encoding="utf-8") == "mine"
    assert (target / "apps" / "mine" / "models.py").read_text(
        encoding="utf-8"
    ) == "# mine"
    assert "# edited" not in (target / "manage.py").read_text(encoding="utf-8")
    assert report.target == target


def test_force_reports_the_number_of_overwritten_files(tmp_path: Path) -> None:
    first = render_project_report(_ctx(tmp_path, force=False))
    generated = len(_tree(first.target))

    second = render_project_report(_ctx(tmp_path, force=True))

    assert first.overwritten == 0
    assert second.overwritten == generated


def test_without_force_a_non_empty_target_is_refused_and_untouched(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(TargetExistsError, match="--force"):
        render_project(_ctx(tmp_path, force=False))

    assert _tree(target) == {"keep.txt": b"keep"}


def test_existing_empty_target_receives_the_project_directly(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()

    render_project(_ctx(tmp_path, force=False))

    assert (target / "manage.py").is_file()
    assert not (target / "sample").exists()  # regression: no nested project


def test_target_that_is_a_file_is_a_clear_error(tmp_path: Path) -> None:
    (tmp_path / "sample").write_text("i am a file", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="not a directory"):
        render_project(_ctx(tmp_path, force=True))

    assert (tmp_path / "sample").read_text(encoding="utf-8") == "i am a file"


def test_symlinked_directory_on_a_write_path_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / "apps").symlink_to(outside, target_is_directory=True)
    before = _tree(target)

    with pytest.raises(TargetSymlinkError, match="apps"):
        render_project(_ctx(tmp_path, force=True))

    assert list(outside.iterdir()) == []  # nothing written through the link
    assert _tree(target) == before  # and nothing else written either
    assert not (target / "manage.py").exists()


@pytest.mark.parametrize("dangling", [False, True], ids=["file-link", "dangling-link"])
def test_symlinked_file_on_a_write_path_is_refused(
    tmp_path: Path, dangling: bool
) -> None:
    target = tmp_path / "sample"
    target.mkdir()
    victim = tmp_path / "victim.txt"
    if not dangling:
        victim.write_text("secret", encoding="utf-8")
    (target / "manage.py").symlink_to(victim)

    with pytest.raises(TargetSymlinkError, match="manage.py"):
        render_project(_ctx(tmp_path, force=True))

    assert (victim.read_text(encoding="utf-8") if victim.exists() else None) == (
        None if dangling else "secret"
    )


def test_unwritable_destination_names_the_file(tmp_path: Path) -> None:
    target = tmp_path / "sample"
    (target / "manage.py").mkdir(parents=True)  # a directory where a file belongs

    with pytest.raises(TargetWriteError, match="manage.py"):
        render_project(_ctx(tmp_path, force=True))

    assert sorted(p.name for p in target.iterdir()) == [
        "manage.py"
    ]  # nothing else written


def test_template_failure_leaves_the_target_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "sample"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")

    def boom() -> None:
        raise RuntimeError("template exploded")

    monkeypatch.setattr(writer, "create_environment", boom)

    with pytest.raises(RuntimeError, match="exploded"):
        render_project(_ctx(tmp_path, force=True))

    assert _tree(target) == {"keep.txt": b"keep"}


def test_fresh_target_is_created_with_parents(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    ctx = ProjectContext.from_options(
        NewProjectOptions(
            name="Sample",
            path=nested,
            database=DatabaseChoice.SQLITE,
            docker=False,
            multitenancy=False,
            frontend=False,
            register=False,
            crud=False,
            force=False,
        )
    )

    assert (render_project(ctx) / "manage.py").is_file()
