"""Field declarations whose reverse accessors must not clash (shared case table).

Each case becomes a model in its own app of one generated project. Model names are
unique per case because two apps with a same-named model pointing at one target clash
on their default accessor (``User.note_set``) whatever the fields are. Templates use
``{model}`` and ``{app}``; ``users.User`` is the project's user model.
"""

from __future__ import annotations

CLASH_CASES: tuple[tuple[str, str], ...] = (
    (
        "roadmap_owner_assignee",
        "title:char,owner:fk:to=users.User,assignee:fk:to=users.User",
    ),
    (
        "fk_fk",
        "owner:fk:to=users.User,reviewer:fk:to=users.User:on_delete=set_null",
    ),
    ("m2m_m2m", "title:char,editors:m2m:to=users.User,viewers:m2m:to=users.User"),
    ("o2o_o2o", "title:char,primary:o2o:to=users.User,backup:o2o:to=users.User"),
    ("fk_o2o", "title:char,owner:fk:to=users.User,profile:o2o:to=users.User"),
    ("fk_m2m", "title:char,owner:fk:to=users.User,watchers:m2m:to=users.User"),
    (
        "self_relation_twice",
        "title:char,parent:fk:to={model},original:fk:to={model}:on_delete=set_null",
    ),
    (
        "app_qualified_and_bare_target",
        "title:char,parent:fk:to={model},original:fk:to={app}.{model}",
    ),
)
"""Cases that fail Django's system check today (``fields.E304``/``E305``)."""

CONTROL_CASES: tuple[tuple[str, str], ...] = (
    ("single_fk", "title:char,owner:fk:to=users.User"),
    ("single_m2m", "title:char,tags:m2m:to=users.User"),
    ("single_o2o", "title:char,profile:o2o:to=users.User"),
    ("different_targets", "title:char,owner:fk:to=users.User,parent:fk:to={model}"),
)
"""Cases without a clash: they must pass before and after, with unchanged output."""

EXPLICIT_CASES: tuple[tuple[str, str], ...] = (
    (
        "explicit_plus_unnamed",
        "title:char,owner:fk:to=users.User:related_name={app}_owned,"
        "assignee:fk:to=users.User",
    ),
    (
        "explicit_hidden_plus_unnamed",
        "title:char,owner:fk:to=users.User:related_name=+,assignee:fk:to=users.User",
    ),
    (
        "explicit_both",
        "title:char,owner:fk:to=users.User:related_name={app}_owned,"
        "assignee:fk:to=users.User:related_name={app}_assigned",
    ),
)
"""Cases that use the new ``related_name=`` option (an unknown option before it existed).

Explicit names are unique per case (``{app}_owned``): the cases share one project, and
two apps that give the same reverse name to relations to ``users.User`` clash with each
other, which is the caller's choice to avoid.
"""

ALL_CASES: tuple[tuple[str, str], ...] = CLASH_CASES + CONTROL_CASES + EXPLICIT_CASES


def case_app(case_id: str) -> str:
    return f"case_{case_id}"


def case_model(case_id: str) -> str:
    """A PascalCase model name unique to the case (``fk_o2o`` -> ``FkO2o``)."""
    return "".join(part.capitalize() for part in case_id.split("_"))


def case_fields(case_id: str, template: str) -> str:
    return template.format(app=case_app(case_id), model=case_model(case_id))
