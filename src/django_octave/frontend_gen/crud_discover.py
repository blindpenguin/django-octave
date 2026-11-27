"""Discover ModelViewSet resources from apps/*/views.py and urls.py."""

from __future__ import annotations

import re
from pathlib import Path

from django_octave.frontend_gen.crud_types import ResourceSpec
from django_octave.naming import pascal_to_snake, pluralize

_REGISTER_RE = re.compile(
    r"""router\.register\(\s*"""
    r"""(?:\"(?P<path_dq>[^\"]*)\"|'(?P<path_sq>[^']*)')\s*,\s*"""
    r"""(?P<viewset>\w+ViewSet)"""
)

_VIEWSET_CLASS_RE = re.compile(
    r"class\s+(?P<vs>\w+ViewSet)\s*\((?P<bases>[^)]*)\)\s*:",
)

_OWNER_FIELD_RE = re.compile(r"""^\s*owner_field\s*=\s*["'](?P<field>\w+)["']""", re.M)

_QUERYSET_RE = re.compile(
    r"queryset\s*=\s*(?P<model>\w+)\.objects",
)


def _apps_root(project_root: Path) -> Path:
    return project_root / "apps"


def _model_from_viewset_body(class_body: str, viewset_name: str) -> str | None:
    """Infer model name from queryset or ViewSet name suffix."""
    m = _QUERYSET_RE.search(class_body)
    if m:
        return m.group("model")
    if viewset_name.endswith("ViewSet") and len(viewset_name) > len("ViewSet"):
        return viewset_name[: -len("ViewSet")]
    return None


def _owner_field(bases: str, class_body: str) -> str | None:
    """Owner attribute of a viewset that uses ``OwnerScopedMixin``, else None."""
    if "OwnerScopedMixin" not in bases:
        return None
    match = _OWNER_FIELD_RE.search(class_body)
    return match.group("field") if match else "owner"


def _split_viewset_classes(source: str) -> list[tuple[str, str, str]]:
    """Return list of (viewset_name, bases, body_until_next_class)."""
    matches = list(_VIEWSET_CLASS_RE.finditer(source))
    results: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        results.append((m.group("vs"), m.group("bases"), source[start:end]))
    return results


def _router_paths(urls_source: str) -> dict[str, str]:
    """Map ViewSet class name → router path segment."""
    out: dict[str, str] = {}
    for m in _REGISTER_RE.finditer(urls_source):
        path = (
            m.group("path_dq") if m.group("path_dq") is not None else m.group("path_sq")
        )
        if path is None:
            continue
        out[m.group("viewset")] = path
    return out


def _is_model_viewset(bases: str) -> bool:
    return "ModelViewSet" in bases


def discover_app_resources(project_root: Path, app_name: str) -> list[ResourceSpec]:
    """Discover ModelViewSet resources in one app."""
    app_dir = _apps_root(project_root) / app_name
    views_path = app_dir / "views.py"
    urls_path = app_dir / "urls.py"
    models_path = app_dir / "models.py"
    if not views_path.is_file():
        return []

    views_src = views_path.read_text(encoding="utf-8")
    urls_src = urls_path.read_text(encoding="utf-8") if urls_path.is_file() else ""
    routes = _router_paths(urls_src)
    model_names: set[str] = set()
    if models_path.is_file():
        model_names = set(
            re.findall(
                r"^class\s+(\w+)\s*\(", models_path.read_text(encoding="utf-8"), re.M
            )
        )

    specs: list[ResourceSpec] = []
    for vs_name, bases, body in _split_viewset_classes(views_src):
        if not _is_model_viewset(bases):
            continue
        model_name = _model_from_viewset_body(body, vs_name)
        if not model_name:
            specs.append(
                ResourceSpec(
                    app_name=app_name,
                    model_name=vs_name,
                    model_snake=pascal_to_snake(vs_name),
                    model_plural=pluralize(pascal_to_snake(vs_name)),
                    api_collection="/api/",
                    viewset_name=vs_name,
                    skip_reason="could not infer model from viewset",
                )
            )
            continue

        snake = pascal_to_snake(model_name)
        plural = routes.get(vs_name) or pluralize(snake)
        skip: str | None = None
        if model_names and model_name not in model_names:
            skip = f"model class {model_name} not found in models.py"

        specs.append(
            ResourceSpec(
                app_name=app_name,
                model_name=model_name,
                model_snake=snake,
                model_plural=plural,
                api_collection=f"/api/{plural}/",
                viewset_name=vs_name,
                skip_reason=skip,
                owner_field=_owner_field(bases, body),
            )
        )
    return specs


def discover_resources(project_root: Path) -> list[ResourceSpec]:
    """Discover all ModelViewSet resources under ``apps/``."""
    apps = _apps_root(project_root)
    if not apps.is_dir():
        return []
    found: list[ResourceSpec] = []
    for child in sorted(apps.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if child.name in {"core"}:
            # core usually has no public ModelViewSets; still scan if present
            pass
        found.extend(discover_app_resources(project_root, child.name))
    return found


def lookup_resource(
    project_root: Path,
    app_name: str,
    model_name: str,
) -> ResourceSpec | None:
    """Find a single resource by app + model name (case-sensitive PascalCase model)."""
    for spec in discover_app_resources(project_root, app_name):
        if spec.model_name == model_name and spec.skip_reason is None:
            return spec
        if spec.model_name == model_name:
            return spec
    # Fallback: invent from naming if viewset missing — caller may reject
    return None


def require_resource(
    project_root: Path,
    app_name: str,
    model_name: str,
) -> ResourceSpec:
    """Lookup or raise ValueError with add-viewset hint."""
    specs = discover_app_resources(project_root, app_name)
    for spec in specs:
        if spec.model_name == model_name:
            if spec.skip_reason:
                raise ValueError(
                    f"{app_name}.{model_name}: {spec.skip_reason}. "
                    f"Fix the model/viewset or run: django-octave add-viewset {app_name} {model_name}"
                )
            return spec
    raise ValueError(
        f"No ModelViewSet found for {app_name}.{model_name}. "
        f"Run: django-octave add-viewset {app_name} {model_name}"
    )
