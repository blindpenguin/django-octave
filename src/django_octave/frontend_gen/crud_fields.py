"""Map ModelFieldInfo → CrudField descriptors for generated forms/tables."""

from __future__ import annotations

from pathlib import Path

from django_octave.frontend_gen.crud_discover import discover_app_resources
from django_octave.frontend_gen.crud_types import CrudField, CrudFieldKind, ResourceSpec
from django_octave.frontend_gen.str_label import (
    parse_simple_str_attr,
    str_method_is_complex,
)
from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    inspect_model_fields_path,
    resolve_related_app_and_model,
)
from django_octave.models_gen.writer import ModelWriteError

_LABEL_CANDIDATES = ("name", "title", "email", "slug")
_STRINGISH = frozenset({"CharField", "SlugField", "EmailField"})

_TYPE_MAP: dict[str, CrudFieldKind] = {
    "CharField": "string",
    "TextField": "text",
    "IntegerField": "number",
    "PositiveIntegerField": "number",
    "SmallIntegerField": "number",
    "BigIntegerField": "number",
    "BooleanField": "boolean",
    "DecimalField": "decimal",
    "FloatField": "decimal",
    "DateField": "date",
    "DateTimeField": "datetime",
    "EmailField": "email",
    "SlugField": "slug",
    "URLField": "string",
    "UUIDField": "string",
}


def label_field_for_info(info: ModelFieldInfo) -> str:
    """Pick a display label field for list titles and FK option labels."""
    names = set(info.fields) | set(info.available_names)
    for candidate in _LABEL_CANDIDATES:
        if candidate in info.fields:
            return candidate
    for name, ftype in info.fields.items():
        if ftype in _STRINGISH:
            return name
    if "id" in names:
        return "id"
    return next(iter(info.fields), "id")


def _related_plural(
    project_root: Path,
    *,
    related_app: str,
    related_model: str,
) -> str | None:
    """Return router plural path when a ModelViewSet is registered; else None."""
    # Frontend auth_api provides GET /api/users/ for FK selects (not a ModelViewSet).
    if related_app == "users" and related_model == "User":
        from django_octave.frontend_gen.django_patch import users_list_endpoint_present

        if users_list_endpoint_present(project_root):
            return "users"

    for spec in discover_app_resources(project_root, related_app):
        if spec.model_name == related_model and spec.skip_reason is None:
            return spec.model_plural
    # Cross-app — scan all
    from django_octave.frontend_gen.crud_discover import discover_resources

    for spec in discover_resources(project_root):
        if (
            spec.app_name == related_app
            and spec.model_name == related_model
            and spec.skip_reason is None
        ):
            return spec.model_plural
    return None


def _model_source(project_root: Path, app_name: str) -> str | None:
    models_path = project_root / "apps" / app_name / "models.py"
    if not models_path.is_file():
        return None
    try:
        return models_path.read_text(encoding="utf-8")
    except OSError:
        return None


def resolve_label_field(
    project_root: Path,
    *,
    app_name: str,
    model_name: str,
    info: ModelFieldInfo | None = None,
) -> tuple[str, list[str]]:
    """Prefer simple ``__str__`` attribute, else heuristic. May suggest API ``label``."""
    warnings: list[str] = []
    source = _model_source(project_root, app_name)
    if source:
        attr = parse_simple_str_attr(source, model_name)
        if attr:
            return attr, warnings
        if str_method_is_complex(source, model_name):
            warnings.append(
                f"{app_name}.{model_name}: complex __str__; "
                "SPA prefers API field 'label' (str(instance)) when present, "
                "else heuristic / --fk-label"
            )
            # Prefer runtime `label` from serializers that expose str(obj)
            return "label", warnings

    if info is None:
        models_path = project_root / "apps" / app_name / "models.py"
        try:
            info = inspect_model_fields_path(models_path, model_name)
        except ModelWriteError, OSError:
            return "id", warnings
    return label_field_for_info(info), warnings


def _related_label(
    project_root: Path,
    *,
    related_app: str,
    related_model: str,
) -> tuple[str, list[str]]:
    if related_app == "users" and related_model == "User":
        # UserListSerializer exposes label=str(user) and email
        source = _model_source(project_root, "users")
        if source:
            attr = parse_simple_str_attr(source, "User")
            if attr:
                return attr, []
        return "label", []
    return resolve_label_field(
        project_root, app_name=related_app, model_name=related_model
    )


def build_crud_fields(
    project_root: Path,
    info: ModelFieldInfo,
    *,
    default_app: str,
    fk_label_overrides: dict[str, str] | None = None,
    owner_field: str | None = None,
) -> tuple[tuple[CrudField, ...], list[str]]:
    """Build CrudField tuple and warning messages (e.g. M2M omit, FK fallback)."""
    warnings: list[str] = []
    fields: list[CrudField] = []
    overrides = fk_label_overrides or {}

    # readonly id + timestamps for detail
    fields.append(CrudField(name="id", kind="readonly", required=False))
    if info.has_timestamps:
        fields.append(CrudField(name="created_at", kind="readonly", required=False))
        fields.append(CrudField(name="updated_at", kind="readonly", required=False))

    for name, ftype in info.fields.items():
        if name == owner_field:
            # The server owns it (OwnerScopedMixin): shown in the detail view, never edited.
            fields.append(CrudField(name=name, kind="readonly", required=False))
            continue
        if ftype == "ManyToManyField":
            warnings.append(f"omitting M2M field {name!r} in v1 CRUD forms")
            continue
        if ftype in {"ForeignKey", "OneToOneField"}:
            rel = info.relations.get(name)
            to = rel.to if rel else None
            required = name not in info.blank_fields and name not in info.null_fields
            if not to:
                fields.append(CrudField(name=name, kind="number", required=required))
                warnings.append(
                    f"FK {name!r}: could not parse target; using number input"
                )
                continue
            related_app, related_model = resolve_related_app_and_model(
                to, default_app=default_app
            )
            # Normalize users.User → users / User
            if related_app == "auth":
                related_app = "users"
            plural = _related_plural(
                project_root,
                related_app=related_app,
                related_model=related_model,
            )
            if plural is None:
                fields.append(CrudField(name=name, kind="number", required=required))
                warnings.append(
                    f"FK {name!r}: no list route for {related_app}.{related_model}; "
                    "using number (PK) input"
                )
                continue
            if name in overrides:
                label = overrides[name]
            else:
                label, label_warnings = _related_label(
                    project_root,
                    related_app=related_app,
                    related_model=related_model,
                )
                warnings.extend(label_warnings)
            fields.append(
                CrudField(
                    name=name,
                    kind="fk",
                    required=required,
                    related_plural=plural,
                    related_label_field=label,
                    related_app=related_app,
                    related_model=related_model,
                )
            )
            continue

        kind = _TYPE_MAP.get(ftype, "string")
        required = name not in info.blank_fields and name not in info.null_fields
        # BooleanField default False is still a required checkbox (always sent)
        if ftype == "BooleanField":
            required = False
        fields.append(CrudField(name=name, kind=kind, required=required))

    return tuple(fields), warnings


def enrich_resource(
    project_root: Path,
    spec: ResourceSpec,
    *,
    fk_label_overrides: dict[str, str] | None = None,
) -> tuple[ResourceSpec, list[str]]:
    """Attach fields + label_field to a discovered ResourceSpec."""
    models_path = project_root / "apps" / spec.app_name / "models.py"
    try:
        info = inspect_model_fields_path(models_path, spec.model_name)
    except ModelWriteError as exc:
        return (
            ResourceSpec(
                app_name=spec.app_name,
                model_name=spec.model_name,
                model_snake=spec.model_snake,
                model_plural=spec.model_plural,
                api_collection=spec.api_collection,
                viewset_name=spec.viewset_name,
                skip_reason=spec.skip_reason or str(exc),
                owner_field=spec.owner_field,
            ),
            [str(exc)],
        )

    crud_fields, warnings = build_crud_fields(
        project_root,
        info,
        default_app=spec.app_name,
        fk_label_overrides=fk_label_overrides,
        owner_field=spec.owner_field,
    )
    label, label_warnings = resolve_label_field(
        project_root,
        app_name=spec.app_name,
        model_name=spec.model_name,
        info=info,
    )
    warnings.extend(label_warnings)
    enriched = ResourceSpec(
        app_name=spec.app_name,
        model_name=spec.model_name,
        model_snake=spec.model_snake,
        model_plural=spec.model_plural,
        api_collection=spec.api_collection,
        viewset_name=spec.viewset_name,
        label_field=label,
        fields=crud_fields,
        skip_reason=spec.skip_reason,
        owner_field=spec.owner_field,
    )
    return enriched, warnings
