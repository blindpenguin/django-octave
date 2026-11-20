"""Context for rendering a domain app via ``django-octave add``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.naming import (
    model_name_from_app,
    pascal_to_snake,
    pluralize,
    validate_app_name,
    validate_model_name,
)
from django_octave.project.detect import OctaveProject


@dataclass(frozen=True, slots=True)
class AppContext:
    project_root: Path
    app_name: str
    model_name: str
    model_snake: str
    model_plural: str
    use_multitenancy: bool
    force: bool
    installed_app: str
    api_mount: str
    app_dir: Path
    settings_base: Path
    urls_path: Path

    @classmethod
    def build(
        cls,
        *,
        project: OctaveProject,
        raw_name: str,
        force: bool,
        model_name: str | None = None,
    ) -> AppContext:
        app_name = validate_app_name(raw_name)
        if model_name is None:
            model_name = model_name_from_app(app_name)
        else:
            model_name = validate_model_name(model_name)
        model_snake = pascal_to_snake(model_name)
        model_plural = pluralize(model_snake)
        return cls(
            project_root=project.root,
            app_name=app_name,
            model_name=model_name,
            model_snake=model_snake,
            model_plural=model_plural,
            use_multitenancy=project.use_multitenancy,
            force=force,
            installed_app=f"apps.{app_name}",
            # Collection URL under shared api/ mount + plural router path.
            api_mount=f"api/{model_plural}/",
            app_dir=project.apps_dir / app_name,
            settings_base=project.settings_base,
            urls_path=project.urls,
        )

    def as_template_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "model_name": self.model_name,
            "model_snake": self.model_snake,
            "model_plural": self.model_plural,
            "use_multitenancy": self.use_multitenancy,
            "installed_app": self.installed_app,
            "api_mount": self.api_mount,
        }
