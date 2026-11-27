"""Idempotent patches for settings and URLs.

Both patches edit the syntax tree (see ``cst_edit``), so a file that a formatter or a person
has changed is still understood. A file whose shape cannot be understood is refused with
the exact step to take by hand, and nothing is written.
"""

from __future__ import annotations

from pathlib import Path

import libcst as cst

from django_octave.errors import OctaveError
from django_octave.project.cst_edit import (
    ConfigEditError,
    append_item,
    check_result,
    dominant_quote,
    ensure_import_names,
    find_sequence,
    make_string,
    parse_source,
    sequence_of,
    sequence_strings,
    string_value,
    with_sequence,
)


class PatchError(OctaveError, ValueError):
    """Raised when a project file cannot be patched safely."""


class _IncludesModule(cst.CSTVisitor):
    """Finds ``include("<module>")`` anywhere in a file, in either quote style."""

    def __init__(self, module: str) -> None:
        self.module = module
        self.found = False

    def visit_Call(self, node: cst.Call) -> bool:
        if (
            isinstance(node.func, cst.Name)
            and node.func.value == "include"
            and node.args
            and node.args[0].keyword is None
            and string_value(node.args[0].value) == self.module
        ):
            self.found = True
        return True


def patch_installed_apps(settings_path: Path, dotted_app: str) -> bool:
    """Ensure ``dotted_app`` is listed in INSTALLED_APPS.

    The app counts as listed when it is a string element of any list or tuple in the file
    (a mention in a comment does not count). Otherwise it is added to the list or tuple
    assigned to ``INSTALLED_APPS``; if there is none that can be edited (for example
    ``DJANGO_APPS + LOCAL_APPS``), :class:`PatchError` says what to add by hand.

    Returns True if the file was modified.
    """
    source = settings_path.read_text(encoding="utf-8")
    try:
        module = parse_source(source, settings_path)
        if dotted_app in sequence_strings(module):
            return False
        ref = find_sequence(module, "INSTALLED_APPS")
        if ref is None:
            msg = (
                f"INSTALLED_APPS in {settings_path} is not a plain list or tuple that "
                f'django-octave can edit. Add "{dotted_app}" to it yourself.'
            )
            raise PatchError(msg)
        sequence = sequence_of(module, ref)
        entry = make_string(dotted_app, dominant_quote(sequence))
        updated = with_sequence(module, ref, append_item(sequence, entry))
        new_source = check_result(updated.code, settings_path)
    except ConfigEditError as exc:
        raise PatchError(str(exc)) from exc
    settings_path.write_text(new_source, encoding="utf-8")
    return True


def patch_urls(urls_path: Path, app_name: str) -> bool:
    """Ensure ``apps.<app>.urls`` is included under the shared ``api/`` prefix.

    New includes use ``path("api/", include("apps.<app>.urls"))`` so router
    plurals yield ``/api/<plural>/`` (not ``/api/<app>/<plural>/``).

    Legacy mounts ``path("api/<app>/", …)`` still count as already wired
    (idempotent; not auto-rewritten): any ``include("apps.<app>.urls")`` does.

    Returns True if the file was modified.
    """
    include_module = f"apps.{app_name}.urls"
    source = urls_path.read_text(encoding="utf-8")
    try:
        module = parse_source(source, urls_path)
        finder = _IncludesModule(include_module)
        module.visit(finder)
        if finder.found:
            return False
        if find_sequence(module, "urlpatterns") is None:
            msg = (
                f"urlpatterns in {urls_path} is not a plain list that django-octave can "
                "edit. Import include and path from django.urls, then add this line to "
                f'urlpatterns yourself: path("api/", include("{include_module}")),'
            )
            raise PatchError(msg)
        # The import may add a statement above urlpatterns, so look the list up afterwards.
        module = ensure_import_names(
            module,
            "django.urls",
            ["include"],
            fallback_statement="from django.urls import include, path",
        )
        ref = find_sequence(module, "urlpatterns")
        assert ref is not None
        sequence = sequence_of(module, ref)
        quote = dominant_quote(sequence)
        route = cst.Call(
            func=cst.Name("path"),
            args=[
                cst.Arg(make_string("api/", quote)),
                cst.Arg(
                    cst.Call(
                        func=cst.Name("include"),
                        args=[cst.Arg(make_string(include_module, quote))],
                    )
                ),
            ],
        )
        updated = with_sequence(module, ref, append_item(sequence, route))
        new_source = check_result(updated.code, urls_path)
    except ConfigEditError as exc:
        raise PatchError(str(exc)) from exc
    urls_path.write_text(new_source, encoding="utf-8")
    return True
