"""Target Django project inspection and patching."""

from django_octave.project.detect import OctaveProject, detect_project
from django_octave.project.patch import patch_installed_apps, patch_urls

__all__ = [
    "OctaveProject",
    "detect_project",
    "patch_installed_apps",
    "patch_urls",
]
