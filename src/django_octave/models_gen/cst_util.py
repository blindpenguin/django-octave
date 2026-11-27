"""Shared libcst helpers for class upsert, imports, and router wiring."""

from __future__ import annotations

import re
from pathlib import Path

import libcst as cst

from django_octave.models_gen.writer import ModelWriteError, _RemoveClass
from django_octave.naming import pascal_to_snake, pluralize

_REGISTER_RE = re.compile(
    r"""router\.register\(\s*"""
    r"""(?:\"(?P<path_dq>[^\"]*)\"|'(?P<path_sq>[^']*)')\s*,\s*"""
    r"""(?P<viewset>\w+ViewSet)\s*,\s*"""
    r"""basename\s*=\s*(?:\"(?P<base_dq>[^\"]*)\"|'(?P<base_sq>[^']*)')\s*\)"""
)


_FROM_IMPORT_RE = re.compile(r"^from\s+(\S+)\s+import\s+(.+)$")


def coalesce_from_imports(source: str) -> str:
    """Merge single-line ``from M import …`` lines that share a module.

    Best-effort: leaves parenthesized multi-line imports and plain ``import``
    statements unchanged. Stable symbol order is first-seen.
    """
    lines = source.splitlines(keepends=True)
    # Collect indices of simple from-imports by module.
    by_module: dict[str, list[int]] = {}
    parsed: dict[int, tuple[str, list[str], str]] = {}
    for i, row in enumerate(lines):
        raw = row.rstrip("\n")
        if "(" in raw or raw.strip().startswith("#"):
            continue
        match = _FROM_IMPORT_RE.match(raw.strip())
        if not match:
            continue
        module, names_raw = match.group(1), match.group(2)
        if "(" in names_raw:
            continue
        symbols = [p.strip() for p in names_raw.split(",") if p.strip()]
        if not symbols:
            continue
        by_module.setdefault(module, []).append(i)
        # Preserve whether original line ended with newline style via lines[i]
        ending = "\n" if row.endswith("\n") else ""
        parsed[i] = (module, symbols, ending)

    drop: set[int] = set()
    replacements: dict[int, str] = {}
    for module, idxs in by_module.items():
        if len(idxs) < 2:
            continue
        seen: list[str] = []
        for i in idxs:
            for sym in parsed[i][1]:
                if sym not in seen:
                    seen.append(sym)
        first = idxs[0]
        ending = parsed[first][2] or "\n"
        replacements[first] = f"from {module} import {', '.join(seen)}{ending}"
        drop.update(idxs[1:])

    if not replacements and not drop:
        return source

    out: list[str] = []
    for i, row in enumerate(lines):
        if i in drop:
            continue
        if i in replacements:
            out.append(replacements[i])
        else:
            out.append(row)
    return "".join(out)


def _insert_import_line(source: str, bare: str) -> str:
    """Insert a full import line after the existing import block."""
    if bare.strip() in {row.strip() for row in source.splitlines()}:
        return source
    parts = source.splitlines(keepends=True)
    idx = 0
    for i, row in enumerate(parts):
        if row.startswith("from __future__") or row.startswith(("import ", "from ")):
            idx = i + 1
    parts.insert(idx, bare if bare.endswith("\n") else bare + "\n")
    return "".join(parts)


def ensure_import_lines(source: str, lines: list[str]) -> str:
    """Insert missing import lines after existing import block.

    When the new line is ``from M import S`` and a ``from M import …`` already
    exists, merge via ``add_to_import`` instead of inserting a duplicate line.
    """
    for line in lines:
        bare = line if line.endswith("\n") else line + "\n"
        stripped = bare.strip()
        if not stripped:
            continue
        match = _FROM_IMPORT_RE.match(stripped)
        if match and "(" not in stripped:
            module, names_raw = match.group(1), match.group(2)
            prefix = f"from {module} import "
            if "(" not in names_raw and prefix in source:
                for sym in (p.strip() for p in names_raw.split(",") if p.strip()):
                    source = add_to_import(source, module, sym)
                continue
        source = _insert_import_line(source, bare)
    return coalesce_from_imports(source)


def add_to_import(source: str, module: str, symbol: str) -> str:
    """Ensure ``from module import ... symbol`` is present."""
    prefix = f"from {module} import "
    if symbol in source and prefix in source:
        for line in source.splitlines():
            if line.startswith(prefix) and symbol in line:
                return source
    if prefix in source:
        lines = source.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(prefix) and symbol not in line:
                lines[i] = line.rstrip("\n").rstrip() + f", {symbol}\n"
                return "".join(lines)
    return coalesce_from_imports(_insert_import_line(source, f"{prefix}{symbol}\n"))


def class_exists(source: str, class_name: str) -> bool:
    """Return True if a top-level class named ``class_name`` exists."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return f"class {class_name}" in source
    return any(
        isinstance(n, cst.ClassDef) and n.name.value == class_name for n in module.body
    )


def method_exists(source: str, class_name: str, method_name: str) -> bool:
    """Return True if ``class_name`` has a method named ``method_name``."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return f"def {method_name}" in source
    for node in module.body:
        if not isinstance(node, cst.ClassDef) or node.name.value != class_name:
            continue
        for item in node.body.body:
            if isinstance(item, cst.FunctionDef) and item.name.value == method_name:
                return True
    return False


class _RemoveMethodInClass(cst.CSTTransformer):
    """Remove a FunctionDef from a named top-level class."""

    def __init__(self, class_name: str, method_name: str) -> None:
        self.class_name = class_name
        self.method_name = method_name

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.class_name:
            return updated_node
        new_body = [
            item
            for item in updated_node.body.body
            if not (
                isinstance(item, cst.FunctionDef)
                and item.name.value == self.method_name
            )
        ]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


class _AppendMethodToClass(cst.CSTTransformer):
    """Append parsed statements (decorators + FunctionDef) to a class body."""

    def __init__(self, class_name: str, addition: list[cst.BaseStatement]) -> None:
        self.class_name = class_name
        self.addition = addition

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.class_name:
            return updated_node
        spacer: list[cst.BaseStatement | cst.EmptyLine] = []
        if updated_node.body.body:
            spacer = [cst.EmptyLine()]
        new_body = [*updated_node.body.body, *spacer, *self.addition]
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )


def upsert_method(
    path: Path,
    class_name: str,
    method_name: str,
    method_src: str,
    *,
    force: bool,
    header_imports: list[str],
) -> None:
    """Create or replace a method on ``class_name`` in ``path``.

    When the method already exists and ``force`` is False, leave it unchanged
    (after ensuring header imports).
    """
    source = path.read_text(encoding="utf-8")
    source = ensure_import_lines(source, header_imports)
    path.write_text(source, encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    if not class_exists(source, class_name):
        raise ModelWriteError(f"{class_name} not found in {path}")
    exists = method_exists(source, class_name, method_name)
    if exists and not force:
        return
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    if exists and force:
        module = module.visit(_RemoveMethodInClass(class_name, method_name))
    try:
        addition_mod = cst.parse_module(method_src.lstrip("\n"))
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(
            f"Could not generate method {method_name} for {path}: {exc}"
        ) from exc
    addition = list(addition_mod.body)
    if not addition:
        raise ModelWriteError("method_src produced no statements")
    updated = module.visit(_AppendMethodToClass(class_name, addition))
    path.write_text(updated.code, encoding="utf-8")


def _top_level_class_index(module: cst.Module, class_name: str) -> int | None:
    for i, node in enumerate(module.body):
        if isinstance(node, cst.ClassDef) and node.name.value == class_name:
            return i
    return None


def _with_blank_leading(addition: list[cst.CSTNode]) -> list[cst.CSTNode]:
    if not addition:
        return addition
    first = addition[0]
    if isinstance(first, cst.ClassDef):
        addition = list(addition)
        addition[0] = first.with_changes(
            leading_lines=[
                *first.leading_lines,
                cst.EmptyLine(),
                cst.EmptyLine(),
            ]
        )
    return addition


def ensure_class_before(path: Path, class_name: str, before_class: str) -> bool:
    """Move ``class_name`` immediately before ``before_class`` if it is after.

    Returns True if the file was modified.
    """
    source = path.read_text(encoding="utf-8")
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    src_idx = _top_level_class_index(module, class_name)
    before_idx = _top_level_class_index(module, before_class)
    if src_idx is None or before_idx is None or src_idx < before_idx:
        return False
    body = list(module.body)
    node = body.pop(src_idx)
    # After pop, before_idx shifts if src was before it — but src was after.
    before_idx = _top_level_class_index(module.with_changes(body=body), before_class)
    if before_idx is None:
        body.append(node)
    else:
        if isinstance(node, cst.ClassDef):
            node = node.with_changes(
                leading_lines=[
                    *node.leading_lines,
                    cst.EmptyLine(),
                    cst.EmptyLine(),
                ]
            )
        body.insert(before_idx, node)
    path.write_text(module.with_changes(body=body).code, encoding="utf-8")
    return True


def upsert_class(
    path: Path,
    class_name: str,
    class_src: str,
    *,
    force: bool,
    header_imports: list[str],
    before: str | None = None,
) -> None:
    """Create or replace a top-level class in ``path``.

    When the class already exists and ``force`` is False, leave it unchanged
    (after ensuring header imports), except when ``before`` is set and the
    class currently appears after that anchor — then move it before the anchor.

    When ``before`` names an existing top-level class, the new/replaced class
    is inserted immediately before that anchor; otherwise it is appended.
    """
    source = path.read_text(encoding="utf-8")
    source = ensure_import_lines(source, header_imports)
    path.write_text(source, encoding="utf-8")
    source = path.read_text(encoding="utf-8")
    exists = class_exists(source, class_name)
    if exists and not force:
        if before:
            ensure_class_before(path, class_name, before)
        return
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc
    if exists and force:
        module = module.visit(_RemoveClass(class_name))
    try:
        addition_mod = cst.parse_module(class_src.lstrip("\n"))
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(
            f"Could not generate {class_name} for {path}: {exc}"
        ) from exc
    addition = _with_blank_leading(list(addition_mod.body))
    body = list(module.body)
    insert_at: int | None = None
    if before:
        insert_at = _top_level_class_index(module, before)
    if insert_at is None:
        updated = module.with_changes(body=[*body, *addition])
    else:
        updated = module.with_changes(
            body=[*body[:insert_at], *addition, *body[insert_at:]]
        )
    path.write_text(updated.code, encoding="utf-8")


def ensure_router_registration(path: Path, app_name: str, model_name: str) -> None:
    """Ensure ``urls.py`` imports the viewset and registers it on the router.

    Rewrites an existing registration for the same ViewSet when basename/path
    is stale (e.g. legacy ``basename="<app>"``). Always uses the pluralized
    model snake as the route path (empty ``""`` is not used — it steals
    sibling routes as detail pks).
    """
    source = path.read_text(encoding="utf-8")
    snake = pascal_to_snake(model_name)
    plural = pluralize(snake)
    viewset = f"{model_name}ViewSet"
    source = add_to_import(source, f"apps.{app_name}.views", viewset)

    match = None
    for m in _REGISTER_RE.finditer(source):
        if m.group("viewset") == viewset:
            match = m
            break

    if match is not None:
        # Always use plural path — empty "" steals sibling routes as detail pks.
        canonical = f'router.register("{plural}", {viewset}, basename="{snake}")'
        if match.group(0) != canonical:
            source = source[: match.start()] + canonical + source[match.end() :]
        path.write_text(source, encoding="utf-8")
        return

    register = f'router.register("{plural}", {viewset}, basename="{snake}")'
    ridx = source.rfind("router.register(")
    if ridx != -1:
        end = source.find("\n", ridx)
        source = source[: end + 1] + register + "\n" + source[end + 1 :]
    else:
        idx = source.find("urlpatterns")
        if idx == -1:
            source = source.rstrip() + "\n" + register + "\n"
        else:
            source = source[:idx] + register + "\n\n" + source[idx:]
    path.write_text(source, encoding="utf-8")


# --- class-level edits used by owner scoping ----------------------------------------


def _parse_for_edit(path: Path) -> cst.Module:
    try:
        return cst.parse_module(path.read_text(encoding="utf-8"))
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(f"Could not parse {path}: {exc}") from exc


def ensure_class_base(
    path: Path, class_name: str, base: str, *, first: bool = True
) -> bool:
    """Make ``base`` (a plain name) one of ``class_name``'s bases. Returns True if changed."""
    module = _parse_for_edit(path)
    changed = False

    class _Edit(cst.CSTTransformer):
        def leave_ClassDef(
            self, original_node: cst.ClassDef, updated_node: cst.ClassDef
        ) -> cst.ClassDef:
            nonlocal changed
            if original_node.name.value != class_name:
                return updated_node
            if any(
                isinstance(arg.value, cst.Name) and arg.value.value == base
                for arg in updated_node.bases
            ):
                return updated_node
            new = cst.Arg(value=cst.Name(base))
            bases = [new, *updated_node.bases] if first else [*updated_node.bases, new]
            changed = True
            return updated_node.with_changes(bases=bases)

    updated = module.visit(_Edit())
    if changed:
        path.write_text(updated.code, encoding="utf-8")
    return changed


def _assigned_name(statement: cst.BaseStatement) -> str | None:
    """Name assigned by a single ``name = value`` statement, else None."""
    if not isinstance(statement, cst.SimpleStatementLine) or len(statement.body) != 1:
        return None
    small = statement.body[0]
    if isinstance(small, cst.Assign) and len(small.targets) == 1:
        target = small.targets[0].target
        if isinstance(target, cst.Name):
            return target.value
    return None


def set_class_attribute(
    path: Path, class_name: str, attr: str, value_source: str
) -> bool:
    """Set ``attr = value_source`` in ``class_name``'s body. Returns True if changed.

    Replaces an existing simple assignment; otherwise inserts the statement before
    ``queryset = ...`` (or at the top, after a docstring).
    """
    module = _parse_for_edit(path)
    try:
        value = cst.parse_expression(value_source)
    except cst.ParserSyntaxError as exc:
        raise ModelWriteError(
            f"Invalid value {value_source!r} for {attr}: {exc}"
        ) from exc
    changed = False

    class _Edit(cst.CSTTransformer):
        def leave_ClassDef(
            self, original_node: cst.ClassDef, updated_node: cst.ClassDef
        ) -> cst.ClassDef:
            nonlocal changed
            if original_node.name.value != class_name:
                return updated_node
            body = list(updated_node.body.body)
            for i, statement in enumerate(body):
                if _assigned_name(statement) == attr:
                    assign = statement.body[0]  # type: ignore[union-attr]
                    if cst.Module([]).code_for_node(assign.value) == cst.Module(
                        []
                    ).code_for_node(value):
                        return updated_node
                    body[i] = statement.with_changes(  # type: ignore[union-attr]
                        body=[assign.with_changes(value=value)]
                    )
                    changed = True
                    return updated_node.with_changes(
                        body=updated_node.body.with_changes(body=body)
                    )
            new_statement = cst.parse_statement(f"{attr} = {value_source}")
            at = next(
                (i for i, s in enumerate(body) if _assigned_name(s) == "queryset"), None
            )
            if at is None:
                at = 0
                if body and isinstance(body[0], cst.SimpleStatementLine):
                    first = body[0].body[0] if body[0].body else None
                    if isinstance(first, cst.Expr) and isinstance(
                        first.value, cst.SimpleString | cst.ConcatenatedString
                    ):
                        at = 1
            body.insert(at, new_statement)
            changed = True
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=body)
            )

    updated = module.visit(_Edit())
    if changed:
        path.write_text(updated.code, encoding="utf-8")
    return changed


def _string_items(node: cst.BaseExpression) -> list[str] | None:
    """Evaluated strings of a tuple/list of string literals, else None."""
    if not isinstance(node, cst.Tuple | cst.List):
        return None
    out = []
    for element in node.elements:
        value = element.value
        if not isinstance(value, cst.SimpleString):
            return None
        out.append(str(value.evaluated_value))
    return out


def ensure_read_only_field(path: Path, class_name: str, field: str) -> str:
    """Put ``field`` into ``<class_name>.Meta.read_only_fields``.

    Returns ``"added"``, ``"present"`` (already read-only) or ``"not-a-field"`` (the
    serializer's explicit ``fields`` does not include it, so nothing is changed).
    """
    module = _parse_for_edit(path)
    result = "not-a-field"
    found_class = False

    class _Edit(cst.CSTTransformer):
        def leave_ClassDef(
            self, original_node: cst.ClassDef, updated_node: cst.ClassDef
        ) -> cst.ClassDef:
            nonlocal result, found_class
            if original_node.name.value != class_name:
                return updated_node
            found_class = True
            body = list(updated_node.body.body)
            meta_index = next(
                (
                    i
                    for i, s in enumerate(body)
                    if isinstance(s, cst.ClassDef) and s.name.value == "Meta"
                ),
                None,
            )
            if meta_index is None:
                result = "not-a-field"
                return updated_node
            meta = body[meta_index]
            assert isinstance(meta, cst.ClassDef)
            meta_body = list(meta.body.body)

            fields_node = next(
                (
                    s.body[0].value  # type: ignore[union-attr]
                    for s in meta_body
                    if _assigned_name(s) == "fields"
                ),
                None,
            )
            if fields_node is not None:
                explicit = _string_items(fields_node)
                if explicit is not None and field not in explicit:
                    result = "not-a-field"
                    return updated_node

            for i, statement in enumerate(meta_body):
                if _assigned_name(statement) != "read_only_fields":
                    continue
                assign = statement.body[0]  # type: ignore[union-attr]
                current = _string_items(assign.value)
                if current is None:
                    raise ModelWriteError(
                        f"{class_name}.Meta.read_only_fields in {path} is not a plain "
                        f"tuple/list of strings; add {field!r} to it by hand"
                    )
                if field in current:
                    result = "present"
                    return updated_node
                container = assign.value
                assert isinstance(container, cst.Tuple | cst.List)
                elements = [
                    *container.elements,
                    cst.Element(value=cst.SimpleString(f'"{field}"')),
                ]
                meta_body[i] = statement.with_changes(
                    body=[
                        assign.with_changes(
                            value=container.with_changes(elements=elements)
                        )
                    ]
                )
                break
            else:
                statement = cst.parse_statement(f'read_only_fields = ("{field}",)')
                at = next(
                    (
                        i + 1
                        for i, s in enumerate(meta_body)
                        if _assigned_name(s) == "fields"
                    ),
                    len(meta_body),
                )
                meta_body.insert(at, statement)

            result = "added"
            body[meta_index] = meta.with_changes(
                body=meta.body.with_changes(body=meta_body)
            )
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=body)
            )

    updated = module.visit(_Edit())
    if not found_class:
        raise ModelWriteError(f"{class_name} not found in {path}")
    if result == "added":
        path.write_text(updated.code, encoding="utf-8")
    return result
