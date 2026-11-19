"""Context for rendering a domain app via ``django-octave add``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django_octave.naming import model_name_from_app, validate_app_name
from django_octave.project.detect import OctaveProject


@dataclass(frozen=True, slots=True)
class AppContext:
    project_root: Path
    app_name: str
    model_name: str
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
    ) -> AppContext:
        app_name = validate_app_name(raw_name)
        model_name = model_name_from_app(app_name)
        return cls(
            project_root=project.root,
            app_name=app_name,
            model_name=model_name,
            use_multitenancy=project.use_multitenancy,
            force=force,
            installed_app=f"apps.{app_name}",
            api_mount=f"api/{app_name}/",
            app_dir=project.apps_dir / app_name,
            settings_base=project.settings_base,
            urls_path=project.urls,
        )

    def as_template_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "model_name": self.model_name,
            "use_multitenancy": self.use_multitenancy,
            "installed_app": self.installed_app,
            "api_mount": self.api_mount,
        }
