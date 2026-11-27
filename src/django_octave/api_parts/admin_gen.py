"""Generate or refresh Django ModelAdmin classes from inspected models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.errors import OctaveError
from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    inspect_model_fields_path,
    searchable_names,
)
from django_octave.models_gen.cst_util import (
    add_to_import,
    class_exists,
    ensure_import_lines,
    upsert_class,
)

_LIST_DISPLAY_EXCLUDE = frozenset(
    {
        "TextField",
        "JSONField",
        "BinaryField",
        "FileField",
        "ImageField",
        "ManyToManyField",
    }
)
_PREFERRED_DISPLAY = ("name", "title", "slug", "email")
_LIST_DISPLAY_CAP = 8  # after id
_LIST_FILTER_CAP = 6


class AdminExistsError(OctaveError, FileExistsError):
    """Raised when the admin class already exists without force."""


class AdminFieldError(OctaveError, ValueError):
    """Raised when an override field name is unknown."""


@dataclass
class AdminOptions:
    app_name: str
    model_name: str
    list_display: list[str] | None = None
    search: list[str] | None = None
    list_filter: list[str] | None = None
    ordering: list[str] | None = None
    date_hierarchy: bool = True
    force: bool = False


def _valid_field_names(info: ModelFieldInfo) -> set[str]:
    names = set(info.available_names)
    names.update(info.fields.keys())
    names.update(info.relations.keys())
    names.add("id")
    if info.has_timestamps:
        names.update({"created_at", "updated_at"})
    return names


def _validate_names(
    names: list[str],
    available: set[str],
    *,
    label: str,
    allow_ordering_prefix: bool = False,
) -> list[str]:
    checked: list[str] = []
    unknown: list[str] = []
    for raw in names:
        name = raw[1:] if allow_ordering_prefix and raw.startswith("-") else raw
        if name not in available:
            unknown.append(raw)
        else:
            checked.append(raw)
    if unknown:
        valid = ", ".join(sorted(available))
        raise AdminFieldError(
            f"Unknown {label} field(s): {', '.join(unknown)}. Valid: {valid}"
        )
    return checked


def default_list_display(info: ModelFieldInfo) -> list[str]:
    """Build capped list_display starting with id."""
    chosen: list[str] = ["id"]
    remaining = _LIST_DISPLAY_CAP

    def add(name: str) -> None:
        nonlocal remaining
        if remaining <= 0 or name in chosen:
            return
        chosen.append(name)
        remaining -= 1

    for pref in _PREFERRED_DISPLAY:
        if pref in info.fields and info.fields[pref] not in _LIST_DISPLAY_EXCLUDE:
            add(pref)

    for name, ftype in info.fields.items():
        if ftype == "BooleanField":
            add(name)

    for name, rel in info.relations.items():
        if rel.kind in {"fk", "o2o"}:
            add(name)

    for name, ftype in info.fields.items():
        if ftype in _LIST_DISPLAY_EXCLUDE:
            continue
        if name in info.relations and info.relations[name].kind == "m2m":
            continue
        add(name)

    if info.has_timestamps:
        add("created_at")
        add("updated_at")

    return chosen


def default_list_filter(info: ModelFieldInfo) -> list[str]:
    names: list[str] = []
    for name, ftype in info.fields.items():
        if ftype == "BooleanField":
            names.append(name)
        elif name in info.relations and info.relations[name].kind in {"fk", "o2o"}:
            names.append(name)
    if info.has_timestamps:
        names.append("created_at")
    return names[:_LIST_FILTER_CAP]


def default_list_select_related(
    info: ModelFieldInfo, list_display: list[str]
) -> list[str]:
    return [
        name
        for name in list_display
        if name in info.relations and info.relations[name].kind in {"fk", "o2o"}
    ]


def resolve_admin_options(
    info: ModelFieldInfo,
    *,
    list_display: list[str] | None,
    search: list[str] | None,
    list_filter: list[str] | None,
    ordering: list[str] | None,
    use_date_hierarchy: bool,
) -> tuple[list[str], list[str], list[str], list[str], list[str] | None, str | None]:
    """Return display, search, filter, select_related, ordering, date_hierarchy."""
    available = _valid_field_names(info)

    if list_display is None:
        display = default_list_display(info)
    else:
        display = _validate_names(list_display, available, label="list_display")

    if search is None:
        search_fields = searchable_names(info)
    else:
        search_fields = _validate_names(search, available, label="search")

    if list_filter is None:
        filters = default_list_filter(info)
    else:
        filters = _validate_names(list_filter, available, label="filter")

    select_related = default_list_select_related(info, display)

    ordering_fields: list[str] | None = None
    if ordering is not None:
        ordering_fields = _validate_names(
            ordering, available, label="ordering", allow_ordering_prefix=True
        )

    hierarchy: str | None = None
    if use_date_hierarchy and info.has_timestamps:
        hierarchy = "created_at"

    return display, search_fields, filters, select_related, ordering_fields, hierarchy


def _tuple_repr(names: list[str]) -> str:
    if not names:
        return "()"
    if len(names) == 1:
        return f'("{names[0]}",)'
    return "(" + ", ".join(f'"{n}"' for n in names) + ")"


def build_admin_class(
    model_name: str,
    *,
    list_display: list[str],
    search_fields: list[str],
    list_filter: list[str],
    list_select_related: list[str],
    ordering: list[str] | None,
    date_hierarchy: str | None,
) -> str:
    lines = [
        f"@admin.register({model_name})",
        f"class {model_name}Admin(admin.ModelAdmin):",
        f"    list_display = {_tuple_repr(list_display)}",
        f"    list_filter = {_tuple_repr(list_filter)}",
        f"    search_fields = {_tuple_repr(search_fields)}",
    ]
    if list_select_related:
        lines.append(f"    list_select_related = {_tuple_repr(list_select_related)}")
    if date_hierarchy:
        lines.append(f'    date_hierarchy = "{date_hierarchy}"')
    if ordering:
        lines.append(f"    ordering = {_tuple_repr(ordering)}")
    lines.append("")
    return "\n".join(lines)


def _admin_header(app_name: str, model_name: str) -> str:
    return f'''"""Admin for {app_name}."""

from __future__ import annotations

from django.contrib import admin

from apps.{app_name}.models import {model_name}
'''


def write_admin(
    app_dir: Path,
    *,
    options: AdminOptions,
    info: ModelFieldInfo | None = None,
) -> Path:
    """Upsert ``{Model}Admin`` into ``app_dir/admin.py``."""
    models_path = app_dir / "models.py"
    if info is None:
        info = inspect_model_fields_path(models_path, options.model_name)

    display, search, filters, select_related, ordering, hierarchy = (
        resolve_admin_options(
            info,
            list_display=options.list_display,
            search=options.search,
            list_filter=options.list_filter,
            ordering=options.ordering,
            use_date_hierarchy=options.date_hierarchy,
        )
    )

    class_name = f"{options.model_name}Admin"
    class_src = "\n" + build_admin_class(
        options.model_name,
        list_display=display,
        search_fields=search,
        list_filter=filters,
        list_select_related=select_related,
        ordering=ordering,
        date_hierarchy=hierarchy,
    )

    path = app_dir / "admin.py"
    if not path.exists():
        path.write_text(
            _admin_header(options.app_name, options.model_name) + class_src,
            encoding="utf-8",
        )
        return path

    source = path.read_text(encoding="utf-8")
    exists = class_exists(source, class_name)
    if exists and not options.force:
        raise AdminExistsError(
            f"{class_name} already exists in {path}. Use --force to replace it."
        )

    source = add_to_import(
        source, f"apps.{options.app_name}.models", options.model_name
    )
    source = ensure_import_lines(source, ["from django.contrib import admin\n"])
    path.write_text(source, encoding="utf-8")
    upsert_class(
        path,
        class_name,
        class_src,
        force=exists and options.force,
        header_imports=["from django.contrib import admin\n"],
    )
    return path
