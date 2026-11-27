"""Tests for the ``.octave.toml`` marker: format, validation, versions and updates."""

from __future__ import annotations

import itertools
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

from django_octave.project import marker as marker_module
from django_octave.project.marker import (
    FILENAME,
    SCHEMA,
    Marker,
    MarkerError,
    check_compatible,
    current_version,
    new_marker,
    read_marker,
    render_marker,
    update_features,
    write_marker,
)

DATABASES = ["sqlite", "postgres", "mariadb"]


def _marker(**overrides: object) -> Marker:
    values: dict[str, object] = {
        "schema": SCHEMA,
        "generator_version": "0.3.0",
        "database": "postgres",
        "docker": True,
        "multitenancy": False,
        "frontend": False,
        "register": False,
        "crud": False,
        "celery": False,
    }
    values.update(overrides)
    return Marker(**values)  # type: ignore[arg-type]


VALID_TEXT = """\
schema = 1
generator_version = "0.3.0"

[project]
database = "sqlite"
docker = false
multitenancy = false

[features]
frontend = false
register = false
crud = false
celery = false
"""


def _write_text(root: Path, text: str) -> None:
    (root / FILENAME).write_text(text, encoding="utf-8")


# --- format and round trip ----------------------------------------------------------------


@pytest.mark.parametrize("database", DATABASES)
@pytest.mark.parametrize(
    "flags",
    list(itertools.product([False, True], repeat=2)),
    ids=lambda f: f"docker={f[0]}-mt={f[1]}",
)
def test_render_then_read_returns_the_same_project_options(
    tmp_path: Path, database: str, flags: tuple[bool, bool]
) -> None:
    docker, multitenancy = flags
    marker = _marker(database=database, docker=docker, multitenancy=multitenancy)
    write_marker(tmp_path, marker)

    assert read_marker(tmp_path) == marker


@pytest.mark.parametrize(
    "features",
    list(itertools.product([False, True], repeat=4)),
    ids=lambda f: "".join("1" if x else "0" for x in f),
)
def test_render_then_read_returns_the_same_features(
    tmp_path: Path, features: tuple[bool, bool, bool, bool]
) -> None:
    frontend, register, crud, celery = features
    marker = _marker(frontend=frontend, register=register, crud=crud, celery=celery)
    write_marker(tmp_path, marker)

    assert read_marker(tmp_path) == marker


def test_rendered_file_starts_with_a_comment_and_is_plain_toml() -> None:
    text = render_marker(_marker(database="mariadb", docker=True, frontend=True))

    assert text.startswith("# Written by django-octave. Commit this file")
    data = tomllib.loads(text)
    assert data == {
        "schema": 1,
        "generator_version": "0.3.0",
        "project": {"database": "mariadb", "docker": True, "multitenancy": False},
        "features": {
            "frontend": True,
            "register": False,
            "crud": False,
            "celery": False,
        },
    }


def test_write_marker_returns_the_path_and_overwrites(tmp_path: Path) -> None:
    first = write_marker(tmp_path, _marker(database="sqlite"))
    second = write_marker(tmp_path, _marker(database="postgres"))

    assert first == second == tmp_path / FILENAME
    assert read_marker(tmp_path).database == "postgres"  # type: ignore[union-attr]


def test_read_marker_without_a_file_returns_none(tmp_path: Path) -> None:
    assert read_marker(tmp_path) is None


def test_read_marker_ignores_unknown_extra_keys(tmp_path: Path) -> None:
    text = VALID_TEXT.replace("schema = 1\n", 'schema = 1\nnote = "x"\n')
    text = text.replace("celery = false", "celery = false\nnew_feature = true")
    _write_text(tmp_path, text + '\n[extra]\nfuture = "value"\n')

    marker = read_marker(tmp_path)

    assert marker is not None
    assert marker.database == "sqlite"
    assert marker.celery is False


# --- invalid files ---------------------------------------------------------------------------


INVALID = [
    pytest.param("this is = not = toml", "not valid TOML", id="bad-toml"),
    pytest.param(VALID_TEXT.replace("schema = 1\n", ""), "schema", id="missing-schema"),
    pytest.param(
        VALID_TEXT.replace("schema = 1", 'schema = "1"'), "schema", id="schema-string"
    ),
    pytest.param(
        VALID_TEXT.replace("schema = 1", "schema = true"), "schema", id="schema-bool"
    ),
    pytest.param(
        VALID_TEXT.replace("schema = 1", "schema = 0"), "schema", id="schema-zero"
    ),
    pytest.param(
        VALID_TEXT.replace('generator_version = "0.3.0"\n', ""),
        "generator_version",
        id="missing-version",
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', "3"),
        "generator_version",
        id="version-not-a-string",
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', '""'), "generator_version", id="version-empty"
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', '"v1.0"'),
        "generator_version",
        id="version-v-prefix",
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', '"1.0 beta"'),
        "generator_version",
        id="version-space",
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', '"1.0\\nx"'),
        "generator_version",
        id="version-newline",
    ),
    pytest.param(
        VALID_TEXT.replace('"0.3.0"', '"1.' + "x" * 64 + '"'),
        "generator_version",
        id="version-long",
    ),
    pytest.param(
        VALID_TEXT.replace("[project]\n", "[projekt]\n"),
        "[project]",
        id="missing-project",
    ),
    pytest.param(
        VALID_TEXT.replace('"sqlite"', '"oracle"'), "database", id="unknown-database"
    ),
    pytest.param(
        VALID_TEXT.replace('"sqlite"', "1"), "database", id="database-not-a-string"
    ),
    pytest.param(
        VALID_TEXT.replace("docker = false", 'docker = "yes"'),
        "docker",
        id="docker-string",
    ),
    pytest.param(
        VALID_TEXT.replace("multitenancy = false\n", ""),
        "multitenancy",
        id="missing-multitenancy",
    ),
    pytest.param(
        VALID_TEXT.replace("[features]\n", "[feature]\n"),
        "[features]",
        id="missing-features",
    ),
    pytest.param(
        VALID_TEXT.replace("celery = false", "celery = 1"), "celery", id="celery-int"
    ),
    pytest.param(VALID_TEXT.replace("crud = false\n", ""), "crud", id="missing-crud"),
]


@pytest.mark.parametrize(("text", "mentions"), INVALID)
def test_read_marker_invalid_file_names_the_file_and_the_problem(
    tmp_path: Path, text: str, mentions: str
) -> None:
    _write_text(tmp_path, text)

    with pytest.raises(MarkerError) as raised:
        read_marker(tmp_path)

    message = str(raised.value)
    assert FILENAME in message
    assert mentions in message
    assert "fix or delete" in message


def test_render_marker_refuses_values_that_are_not_on_the_allow_list() -> None:
    with pytest.raises(MarkerError, match="database"):
        render_marker(_marker(database="oracle"))
    with pytest.raises(MarkerError, match="generator_version"):
        render_marker(_marker(generator_version='0.3.0"\nsneaky = "x'))
    with pytest.raises(MarkerError, match="schema"):
        render_marker(_marker(schema=0))


def test_render_marker_accepts_unknown_as_the_version() -> None:
    assert (
        tomllib.loads(render_marker(_marker(generator_version="unknown")))[
            "generator_version"
        ]
        == "unknown"
    )


# --- the running version -------------------------------------------------------------------


def test_current_version_is_the_installed_package_version() -> None:
    assert current_version() == metadata.version("django-octave")


def test_current_version_is_unknown_without_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(marker_module.metadata, "version", missing)

    assert current_version() == "unknown"


@pytest.mark.parametrize("junk", ["not a version!", "", "v2", '1.0"\nx="y'])
def test_current_version_never_returns_text_outside_the_pattern(
    monkeypatch: pytest.MonkeyPatch, junk: str
) -> None:
    monkeypatch.setattr(marker_module.metadata, "version", lambda _name: junk)

    assert current_version() == "unknown"


def test_new_marker_records_the_options_and_no_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(marker_module, "current_version", lambda: "0.3.0")

    marker = new_marker(database="mariadb", docker=True, multitenancy=True)

    assert marker == _marker(
        database="mariadb", docker=True, multitenancy=True, generator_version="0.3.0"
    )


# --- compatibility ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("generated", "running"),
    [
        ("0.3.1", "0.3.0"),
        ("0.4.0", "0.3.9"),
        ("1.0.0", "0.9.9"),
        ("0.10.0", "0.9.0"),  # numeric, not lexicographic
        ("0.4.0.dev1", "0.3.0"),
        ("0.3.0.1", "0.3.0"),
        ("0.3.1", "0.3"),
    ],
)
def test_check_compatible_refuses_a_newer_generator_naming_both_versions(
    generated: str, running: str
) -> None:
    with pytest.raises(MarkerError) as raised:
        check_compatible(_marker(generator_version=generated), running=running)

    message = str(raised.value)
    assert generated in message
    assert running in message
    assert "pgrade django-octave" in message


@pytest.mark.parametrize(
    ("generated", "running"),
    [
        ("0.3.0", "0.3.0"),
        ("0.2.9", "0.3.0"),
        ("0.3.0", "0.10.0"),
        ("0.3", "0.3.0"),
        ("0.3.0", "0.3"),
        ("0.4.0.dev1", "0.4.0"),  # same release, a dev build counts as that release
        ("0.4.0", "0.4.0rc1"),
        ("unknown", "0.3.0"),
        ("0.3.0", "unknown"),
        ("unknown", "unknown"),
    ],
)
def test_check_compatible_allows_equal_older_and_unknown_versions(
    generated: str, running: str
) -> None:
    check_compatible(_marker(generator_version=generated), running=running)


def test_check_compatible_uses_the_running_version_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(marker_module, "current_version", lambda: "0.3.0")

    check_compatible(_marker(generator_version="0.3.0"))
    with pytest.raises(MarkerError):
        check_compatible(_marker(generator_version="0.3.1"))


def test_check_compatible_refuses_a_newer_marker_schema() -> None:
    with pytest.raises(MarkerError) as raised:
        check_compatible(_marker(schema=SCHEMA + 1), running="0.3.0")

    message = str(raised.value)
    assert "newer django-octave" in message
    assert f"schema {SCHEMA + 1}" in message
    assert "pgrade django-octave" in message


# --- updating features -----------------------------------------------------------------------


def test_update_features_without_a_marker_creates_nothing(tmp_path: Path) -> None:
    assert update_features(tmp_path, celery=True) is False

    assert list(tmp_path.iterdir()) == []


def test_update_features_changes_only_the_named_keys(tmp_path: Path) -> None:
    original = _marker(
        generator_version="0.0.1", database="mariadb", docker=True, multitenancy=True
    )
    write_marker(tmp_path, original)

    assert update_features(tmp_path, celery=True) is True

    updated = read_marker(tmp_path)
    assert updated is not None
    assert updated.celery is True
    assert updated.generator_version == "0.0.1"
    assert (updated.database, updated.docker, updated.multitenancy) == (
        "mariadb",
        True,
        True,
    )
    assert (updated.frontend, updated.register, updated.crud) == (False, False, False)


def test_update_features_can_set_several_keys_at_once(tmp_path: Path) -> None:
    write_marker(tmp_path, _marker())

    update_features(tmp_path, frontend=True, register=True)
    update_features(tmp_path, register=False, crud=True)

    updated = read_marker(tmp_path)
    assert updated is not None
    assert (updated.frontend, updated.register, updated.crud) == (True, False, True)


@pytest.mark.parametrize(
    "changes",
    [{"database": True}, {"generator_version": True}, {"nope": True}],
)
def test_update_features_rejects_keys_that_are_not_features(
    tmp_path: Path, changes: dict[str, bool]
) -> None:
    write_marker(tmp_path, _marker())

    with pytest.raises(TypeError, match="feature"):
        update_features(tmp_path, **changes)


def test_update_features_rejects_values_that_are_not_booleans(tmp_path: Path) -> None:
    write_marker(tmp_path, _marker())

    with pytest.raises(TypeError, match="bool"):
        update_features(tmp_path, celery="yes")  # type: ignore[arg-type]


def test_update_features_with_an_invalid_marker_raises_and_leaves_the_file(
    tmp_path: Path,
) -> None:
    _write_text(tmp_path, "schema = [")
    before = (tmp_path / FILENAME).read_bytes()

    with pytest.raises(MarkerError):
        update_features(tmp_path, celery=True)

    assert (tmp_path / FILENAME).read_bytes() == before
