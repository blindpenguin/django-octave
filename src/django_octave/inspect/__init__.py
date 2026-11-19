"""Static inspection of generated Django project sources."""

from django_octave.inspect.model_fields import (
    ModelFieldInfo,
    filterable_names,
    inspect_model_fields,
    searchable_names,
)

__all__ = [
    "ModelFieldInfo",
    "filterable_names",
    "inspect_model_fields",
    "searchable_names",
]
