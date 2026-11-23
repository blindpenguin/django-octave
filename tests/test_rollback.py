"""`rollback_on_error` makes a command all-or-nothing and keeps Python parseable."""

from __future__ import annotations

from pathlib import Path

import pytest

from django_octave.rollback import GeneratedCodeError, rollback_on_error


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "apps" / "blog").mkdir(parents=True)
    (tmp_path / "apps" / "blog" / "views.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "apps" / "blog" / "models.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "config.txt").write_text("keep", encoding="utf-8")
    return tmp_path


def test_success_keeps_the_changes(root: Path) -> None:
    with rollback_on_error(root):
        (root / "apps" / "blog" / "views.py").write_text("x = 2\n", encoding="utf-8")
        (root / "apps" / "blog" / "new.py").write_text("z = 3\n", encoding="utf-8")

    assert (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8") == "x = 2\n"
    assert (root / "apps" / "blog" / "new.py").is_file()


def test_exception_restores_modified_created_and_deleted_files(root: Path) -> None:
    before = _tree(root)

    with pytest.raises(RuntimeError, match="boom"), rollback_on_error(root):
        (root / "apps" / "blog" / "views.py").write_text("changed = True\n", encoding="utf-8")
        (root / "apps" / "blog" / "created.py").write_text("n = 1\n", encoding="utf-8")
        (root / "apps" / "blog" / "models.py").unlink()
        (root / "apps" / "newapp").mkdir()
        (root / "apps" / "newapp" / "x.py").write_text("q = 1\n", encoding="utf-8")
        raise RuntimeError("boom")

    assert _tree(root) == before
    assert not (root / "apps" / "newapp").exists()  # created directory is removed too


def test_an_unparsable_python_file_is_rolled_back_and_reported(root: Path) -> None:
    before = _tree(root)

    with pytest.raises(GeneratedCodeError, match=r"apps/blog/views\.py does not parse"), rollback_on_error(root):
        (root / "apps" / "blog" / "views.py").write_text("def broken(:\n", encoding="utf-8")

    assert _tree(root) == before


def test_a_new_unparsable_file_is_removed(root: Path) -> None:
    with pytest.raises(GeneratedCodeError, match="permissions.py"), rollback_on_error(root):
        (root / "apps" / "blog" / "permissions.py").write_text('x = "a" "\n', encoding="utf-8")

    assert not (root / "apps" / "blog" / "permissions.py").exists()


def test_files_that_were_already_unparsable_and_untouched_do_not_fail_the_command(
    root: Path,
) -> None:
    (root / "apps" / "blog" / "legacy.py").write_text("this is not python\n", encoding="utf-8")

    with rollback_on_error(root):
        (root / "apps" / "blog" / "views.py").write_text("x = 5\n", encoding="utf-8")

    assert (root / "apps" / "blog" / "views.py").read_text(encoding="utf-8") == "x = 5\n"


def test_non_python_files_are_not_parsed(root: Path) -> None:
    with rollback_on_error(root):
        (root / "notes.txt").write_text("def broken(:", encoding="utf-8")

    assert (root / "notes.txt").is_file()


@pytest.mark.parametrize("ignored", [".venv", "node_modules", "__pycache__", ".git"])
def test_ignored_directories_are_neither_snapshotted_nor_touched(root: Path, ignored: str) -> None:
    (root / ignored).mkdir()
    (root / ignored / "big.bin").write_bytes(b"1")

    with pytest.raises(RuntimeError), rollback_on_error(root):
        (root / ignored / "big.bin").write_bytes(b"2")
        (root / ignored / "new.bin").write_bytes(b"3")
        raise RuntimeError

    assert (root / ignored / "big.bin").read_bytes() == b"2"  # left alone
    assert (root / ignored / "new.bin").is_file()


def test_keyboard_interrupt_also_restores(root: Path) -> None:
    before = _tree(root)

    with pytest.raises(KeyboardInterrupt), rollback_on_error(root):
        (root / "apps" / "blog" / "views.py").write_text("half = ", encoding="utf-8")
        raise KeyboardInterrupt

    assert _tree(root) == before
