"""Idempotent patches for settings and URLs."""

from __future__ import annotations

import re
from pathlib import Path


class PatchError(ValueError):
    """Raised when a project file cannot be patched safely."""


_INSTALLED_APPS_RE = re.compile(
    r"(INSTALLED_APPS\s*=\s*\[)(.*?)(\n\])",
    re.DOTALL,
)


def patch_installed_apps(settings_path: Path, dotted_app: str) -> bool:
    """Ensure ``dotted_app`` is listed in INSTALLED_APPS.

    Returns True if the file was modified.
    """
    text = settings_path.read_text(encoding="utf-8")
    entry = f'"{dotted_app}"'
    if entry in text or f"'{dotted_app}'" in text:
        return False

    match = _INSTALLED_APPS_RE.search(text)
    if not match:
        msg = f"Could not locate INSTALLED_APPS list in {settings_path}"
        raise PatchError(msg)

    body = match.group(2)
    # Keep trailing comma style on last entry.
    insertion = f'\n    "{dotted_app}",'
    if body.rstrip().endswith(","):
        new_body = body.rstrip() + insertion + "\n"
    else:
        new_body = body.rstrip() + "," + insertion + "\n"

    new_text = text[: match.start(2)] + new_body + text[match.end(2) :]
    settings_path.write_text(new_text, encoding="utf-8")
    return True


def patch_urls(urls_path: Path, app_name: str) -> bool:
    """Ensure ``api/<app_name>/`` include exists in urlpatterns.

    Returns True if the file was modified.
    """
    text = urls_path.read_text(encoding="utf-8")
    include_mod = f"apps.{app_name}.urls"
    mount = f'"api/{app_name}/"'
    if include_mod in text and mount in text:
        return False

    # Ensure include is imported from django.urls.
    if "from django.urls import" in text:
        if re.search(r"from django\.urls import ([^\n]+)", text):

            def _ensure_include(match: re.Match[str]) -> str:
                names = match.group(1)
                parts = [p.strip() for p in names.split(",")]
                if "include" not in parts:
                    parts.append("include")
                return f"from django.urls import {', '.join(parts)}"

            text = re.sub(
                r"from django\.urls import ([^\n]+)",
                _ensure_include,
                text,
                count=1,
            )
    else:
        # Insert after future import / top imports.
        lines = text.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from __future__"):
                insert_at = i + 1
            elif line.startswith(("import ", "from ")):
                insert_at = i + 1
        lines.insert(insert_at, "from django.urls import include, path\n")
        text = "".join(lines)

    snippet = (
        f'    path("api/{app_name}/", include("apps.{app_name}.urls")),\n'
    )
    marker = "urlpatterns = ["
    idx = text.find(marker)
    if idx == -1:
        msg = f"Could not locate urlpatterns in {urls_path}"
        raise PatchError(msg)

    # Insert before the closing bracket of urlpatterns list.
    # Find matching closing ] after urlpatterns = [
    start = idx + len(marker)
    depth = 1
    pos = start
    while pos < len(text) and depth:
        if text[pos] == "[":
            depth += 1
        elif text[pos] == "]":
            depth -= 1
        pos += 1
    if depth != 0:
        msg = f"Unbalanced urlpatterns list in {urls_path}"
        raise PatchError(msg)
    close_idx = pos - 1
    new_text = text[:close_idx] + snippet + text[close_idx:]
    urls_path.write_text(new_text, encoding="utf-8")
    return True
