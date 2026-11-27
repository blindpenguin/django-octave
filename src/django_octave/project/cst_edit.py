"""Structure-aware edits of Python config files (``urls.py``, settings) with libcst.

The patchers that wire an app into a project used to search these files with regular
expressions, which broke as soon as a formatter wrapped a line or a person used another
quote style. These helpers read the syntax tree instead, so formatting, quoting and
wrapping stop mattering, and everything an edit does not need to change stays as it is.

The helpers take and return libcst nodes or source strings and never touch the disk. They
raise :class:`ConfigEditError` for files they cannot understand; the patchers turn that
into their own error type with the manual step to take.

How libcst stores a list matters here. The whitespace *between* items lives on each item's
comma, including a trailing comment and comment lines above the next item. The whitespace
after the *last* item (its trailing comment, the newline before the closing bracket) lives
on the closing bracket. Appending, inserting and removing therefore move those pieces
instead of copying text, so comments and indentation survive.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import libcst as cst
from libcst import helpers

from django_octave.errors import OctaveError


class ConfigEditError(OctaveError, ValueError):
    """Raised when a config file cannot be read or edited safely."""


# --- parsing --------------------------------------------------------------------------------


def parse_source(source: str, path: Path) -> cst.Module:
    """Parse ``source``; the error names ``path`` and the syntax problem."""
    try:
        return cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        msg = f"{path}: syntax error ({exc.message}, line {exc.raw_line}); fix the file first"
        raise ConfigEditError(msg) from exc


def check_result(source: str, path: Path) -> str:
    """Return ``source`` if it parses; otherwise refuse, so nothing broken is written."""
    try:
        ast.parse(source)
    except SyntaxError as exc:
        msg = f"{path}: the patched file does not parse ({exc.msg}, line {exc.lineno})"
        raise ConfigEditError(msg) from exc
    return source


# --- strings ----------------------------------------------------------------------------------


def string_value(node: cst.CSTNode) -> str | None:
    """The value of a plain string literal; ``None`` for f-strings, bytes, joins, names."""
    if isinstance(node, cst.SimpleString):
        value = node.evaluated_value
        return value if isinstance(value, str) else None
    return None


class _FirstString(cst.CSTVisitor):
    def __init__(self) -> None:
        self.quote: str | None = None

    def visit_SimpleString(self, node: cst.SimpleString) -> bool:
        if self.quote is None:
            self.quote = node.quote[0]
        return False


def dominant_quote(node: cst.CSTNode) -> str:
    """The quote character of the first string inside ``node``; ``"`` when there is none."""
    finder = _FirstString()
    node.visit(finder)
    return finder.quote or '"'


def make_string(value: str, quote: str) -> cst.SimpleString:
    """A string literal for ``value``; refuses text that could not sit safely in quotes."""
    if quote not in {'"', "'"} or any(c in value for c in ('"', "'", "\\", "\n", "\r")):
        msg = f"cannot write {value!r} as a string literal"
        raise ConfigEditError(msg)
    return cst.SimpleString(f"{quote}{value}{quote}")


class _SequenceStrings(cst.CSTVisitor):
    def __init__(self) -> None:
        self.found: set[str] = set()

    def _elements(self, elements: Sequence[cst.Element]) -> None:
        for element in elements:
            value = string_value(element.value)
            if value is not None:
                self.found.add(value)

    def visit_List(self, node: cst.List) -> bool:
        self._elements(node.elements)
        return True

    def visit_Tuple(self, node: cst.Tuple) -> bool:
        self._elements(node.elements)
        return True


def sequence_strings(module: cst.Module) -> set[str]:
    """Every string that is an element of a list or tuple anywhere in ``module``."""
    visitor = _SequenceStrings()
    module.visit(visitor)
    return visitor.found


# --- top-level sequences ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SequenceRef:
    """Where a top-level ``NAME = [...]`` (or tuple) sits in a module."""

    statement: int
    small: int
    kind: Literal["assign", "annotated", "augmented"]


def _small_sequence(small: cst.BaseSmallStatement, name: str) -> str | None:
    """The kind of assignment of a literal list/tuple to ``name``, if ``small`` is one."""
    if isinstance(small, cst.Assign):
        if (
            len(small.targets) == 1
            and isinstance(small.targets[0].target, cst.Name)
            and small.targets[0].target.value == name
            and isinstance(small.value, (cst.List, cst.Tuple))
        ):
            return "assign"
    elif isinstance(small, cst.AnnAssign):
        if (
            isinstance(small.target, cst.Name)
            and small.target.value == name
            and isinstance(small.value, (cst.List, cst.Tuple))
        ):
            return "annotated"
    elif isinstance(small, cst.AugAssign):
        if (
            isinstance(small.target, cst.Name)
            and small.target.value == name
            and isinstance(small.operator, cst.AddAssign)
            and isinstance(small.value, (cst.List, cst.Tuple))
        ):
            return "augmented"
    return None


def find_sequence(module: cst.Module, name: str) -> SequenceRef | None:
    """The top-level literal list or tuple assigned to ``name``.

    A plain or annotated assignment wins over an augmented one (``name += [...]``).
    """
    augmented: SequenceRef | None = None
    for index, statement in enumerate(module.body):
        if not isinstance(statement, cst.SimpleStatementLine):
            continue
        for small_index, small in enumerate(statement.body):
            kind = _small_sequence(small, name)
            if kind == "augmented" and augmented is None:
                augmented = SequenceRef(index, small_index, "augmented")
            elif kind in {"assign", "annotated"}:
                return SequenceRef(index, small_index, kind)  # type: ignore[arg-type]
    return augmented


def _small(
    module: cst.Module, ref: SequenceRef
) -> cst.Assign | cst.AnnAssign | cst.AugAssign:
    statement = module.body[ref.statement]
    assert isinstance(statement, cst.SimpleStatementLine)
    small = statement.body[ref.small]
    assert isinstance(small, (cst.Assign, cst.AnnAssign, cst.AugAssign))
    return small


def sequence_of(module: cst.Module, ref: SequenceRef) -> cst.List | cst.Tuple:
    """The list or tuple node ``ref`` points at."""
    value = _small(module, ref).value
    assert isinstance(value, (cst.List, cst.Tuple))
    return value


def with_sequence(
    module: cst.Module, ref: SequenceRef, sequence: cst.List | cst.Tuple
) -> cst.Module:
    """``module`` with the sequence ``ref`` points at replaced by ``sequence``."""
    statement = module.body[ref.statement]
    assert isinstance(statement, cst.SimpleStatementLine)
    body = list(statement.body)
    body[ref.small] = _small(module, ref).with_changes(value=sequence)
    new_body = list(module.body)
    new_body[ref.statement] = statement.with_changes(body=body)
    return module.with_changes(body=new_body)


# --- editing a comma separated sequence ---------------------------------------------------------

_Ws = cst.BaseParenthesizableWhitespace
_Item = cst.Element | cst.ImportAlias


@dataclass(frozen=True, slots=True)
class _Seq:
    """A comma separated sequence: its items and the whitespace inside its brackets."""

    items: list[_Item]
    open_ws: _Ws | None
    close_ws: _Ws | None


def _plain_line() -> cst.TrailingWhitespace:
    return cst.TrailingWhitespace(
        whitespace=cst.SimpleWhitespace(""), comment=None, newline=cst.Newline()
    )


def _is_paren(ws: object) -> bool:
    return isinstance(ws, cst.ParenthesizedWhitespace)


def _plain(gap: _Ws) -> _Ws:
    """``gap`` without a trailing comment and without comment lines."""
    if isinstance(gap, cst.ParenthesizedWhitespace):
        return cst.ParenthesizedWhitespace(
            first_line=_plain_line(),
            empty_lines=[],
            indent=gap.indent,
            last_line=gap.last_line,
        )
    return gap


def _unpack(node: cst.List | cst.Tuple | cst.ImportFrom) -> _Seq:
    if isinstance(node, cst.List):
        seq = _Seq(
            list(node.elements),
            node.lbracket.whitespace_after,
            node.rbracket.whitespace_before,
        )
    elif isinstance(node, cst.Tuple):
        if not node.lpar:
            msg = "a tuple without parentheses cannot be edited"
            raise ConfigEditError(msg)
        seq = _Seq(
            list(node.elements),
            node.lpar[-1].whitespace_after,
            node.rpar[0].whitespace_before,
        )
    else:
        if isinstance(node.names, cst.ImportStar):
            msg = "cannot add names to 'from ... import *'"
            raise ConfigEditError(msg)
        if node.lpar is not None and node.rpar is not None:
            seq = _Seq(
                list(node.names),
                node.lpar.whitespace_after,
                node.rpar.whitespace_before,
            )
        else:
            seq = _Seq(list(node.names), None, None)
    return _normalize(seq)


def _normalize(seq: _Seq) -> _Seq:
    """Keep the whitespace before the closing bracket in one place.

    A parenthesized import stores the newline before ``)`` on the last name's comma, a list
    stores it on the bracket. Both print the same, so move it to the bracket.
    """
    if not seq.items or seq.close_ws is None:
        return seq
    last = seq.items[-1]
    if (
        isinstance(last.comma, cst.Comma)
        and isinstance(last.comma.whitespace_after, cst.ParenthesizedWhitespace)
        and isinstance(seq.close_ws, cst.SimpleWhitespace)
        and not seq.close_ws.value
    ):
        items = list(seq.items)
        items[-1] = last.with_changes(
            comma=last.comma.with_changes(whitespace_after=cst.SimpleWhitespace(""))
        )
        return _Seq(items, seq.open_ws, last.comma.whitespace_after)
    return seq


def _pack(node: cst.List | cst.Tuple | cst.ImportFrom, seq: _Seq) -> cst.CSTNode:
    if isinstance(node, cst.List):
        return node.with_changes(
            elements=seq.items,
            lbracket=node.lbracket.with_changes(whitespace_after=seq.open_ws),
            rbracket=node.rbracket.with_changes(whitespace_before=seq.close_ws),
        )
    if isinstance(node, cst.Tuple):
        lpar = [
            *node.lpar[:-1],
            node.lpar[-1].with_changes(whitespace_after=seq.open_ws),
        ]
        rpar = [
            node.rpar[0].with_changes(whitespace_before=seq.close_ws),
            *node.rpar[1:],
        ]
        return node.with_changes(elements=seq.items, lpar=lpar, rpar=rpar)
    if node.lpar is not None and node.rpar is not None:
        return node.with_changes(
            names=seq.items,
            lpar=node.lpar.with_changes(whitespace_after=seq.open_ws),
            rpar=node.rpar.with_changes(whitespace_before=seq.close_ws),
        )
    return node.with_changes(names=seq.items)


def _separator(seq: _Seq) -> _Ws:
    """The whitespace that normally separates two items of this sequence."""
    first = seq.items[0].comma if seq.items else None
    if len(seq.items) >= 2 and isinstance(first, cst.Comma):
        return _plain(first.whitespace_after)
    if isinstance(seq.open_ws, cst.ParenthesizedWhitespace):
        return _plain(seq.open_ws)
    return cst.SimpleWhitespace(" ")


def _append_to_empty(seq: _Seq, item: _Item) -> _Seq:
    if isinstance(seq.open_ws, cst.ParenthesizedWhitespace):
        # ``[\n]``: the item goes on its own line, indented one level inside the brackets.
        close_indent = seq.open_ws.last_line.value
        open_ws = cst.ParenthesizedWhitespace(
            first_line=_plain_line(),
            empty_lines=[],
            indent=seq.open_ws.indent,
            last_line=cst.SimpleWhitespace(close_indent + "    "),
        )
        close_ws = cst.ParenthesizedWhitespace(
            first_line=_plain_line(),
            empty_lines=[],
            indent=seq.open_ws.indent,
            last_line=cst.SimpleWhitespace(close_indent),
        )
        return _Seq([item.with_changes(comma=cst.Comma())], open_ws, close_ws)
    return _Seq(
        [item.with_changes(comma=cst.MaybeSentinel.DEFAULT)], seq.open_ws, seq.close_ws
    )


def _append(seq: _Seq, item: _Item) -> _Seq:
    if not seq.items:
        return _append_to_empty(seq, item)
    items = list(seq.items)
    last = items[-1]
    had_trailing = isinstance(last.comma, cst.Comma)
    last_comma_before = (
        last.comma.whitespace_before
        if isinstance(last.comma, cst.Comma)
        else cst.SimpleWhitespace("")
    )
    sep = _separator(seq)
    close = seq.close_ws
    if isinstance(close, cst.ParenthesizedWhitespace):
        # The last item's trailing comment moves onto its own comma; the closing bracket
        # keeps any comment lines, so they stay after the new item.
        if isinstance(sep, cst.ParenthesizedWhitespace):
            indent, last_line = sep.indent, sep.last_line
        else:
            indent, last_line = (
                close.indent,
                cst.SimpleWhitespace(close.last_line.value + "    "),
            )
        prev_gap: _Ws = cst.ParenthesizedWhitespace(
            first_line=close.first_line,
            empty_lines=[],
            indent=indent,
            last_line=last_line,
        )
        new_close: _Ws | None = cst.ParenthesizedWhitespace(
            first_line=_plain_line(),
            empty_lines=close.empty_lines,
            indent=close.indent,
            last_line=close.last_line,
        )
    else:
        prev_gap = sep
        new_close = close
    items[-1] = last.with_changes(
        comma=cst.Comma(whitespace_before=last_comma_before, whitespace_after=prev_gap)
    )
    new_comma = cst.Comma() if had_trailing else cst.MaybeSentinel.DEFAULT
    items.append(item.with_changes(comma=new_comma))
    return _Seq(items, seq.open_ws, new_close)


def _insert_after(seq: _Seq, index: int, item: _Item) -> _Seq:
    if index >= len(seq.items) - 1:
        return _append(seq, item)
    items = list(seq.items)
    anchor = items[index]
    assert isinstance(anchor.comma, cst.Comma)
    gap = anchor.comma.whitespace_after
    if isinstance(gap, cst.ParenthesizedWhitespace):
        # The anchor keeps its trailing comment; comment lines above the next item stay
        # above it, which is now the new item's successor.
        keep = gap.with_changes(empty_lines=[])
        pass_on: _Ws = gap.with_changes(first_line=_plain_line())
    else:
        keep = pass_on = gap
    items[index] = anchor.with_changes(
        comma=anchor.comma.with_changes(whitespace_after=keep)
    )
    items.insert(
        index + 1, item.with_changes(comma=cst.Comma(whitespace_after=pass_on))
    )
    return _Seq(items, seq.open_ws, seq.close_ws)


def _remove(seq: _Seq, index: int) -> _Seq:
    items = list(seq.items)
    removed = items[index]
    if len(items) == 1:
        return _Seq(
            [],
            cst.SimpleWhitespace("") if seq.open_ws else None,
            seq.close_ws and cst.SimpleWhitespace(""),
        )
    if index == len(items) - 1:
        prev = items[index - 1]
        assert isinstance(prev.comma, cst.Comma)
        prev_gap = prev.comma.whitespace_after
        new_close = seq.close_ws
        if isinstance(prev_gap, cst.ParenthesizedWhitespace) and isinstance(
            seq.close_ws, cst.ParenthesizedWhitespace
        ):
            new_close = cst.ParenthesizedWhitespace(
                first_line=prev_gap.first_line,
                empty_lines=seq.close_ws.empty_lines,
                indent=seq.close_ws.indent,
                last_line=seq.close_ws.last_line,
            )
        comma = (
            cst.Comma(
                whitespace_before=removed.comma.whitespace_before,
                whitespace_after=cst.SimpleWhitespace(""),
            )
            if isinstance(removed.comma, cst.Comma)
            else cst.MaybeSentinel.DEFAULT
        )
        items[index - 1] = prev.with_changes(comma=comma)
        del items[index]
        return _Seq(items, seq.open_ws, new_close)
    assert isinstance(removed.comma, cst.Comma)
    gap = removed.comma.whitespace_after
    if index == 0:
        open_ws = seq.open_ws
        if isinstance(open_ws, cst.ParenthesizedWhitespace) and isinstance(
            gap, cst.ParenthesizedWhitespace
        ):
            open_ws = cst.ParenthesizedWhitespace(
                first_line=open_ws.first_line,
                empty_lines=gap.empty_lines,
                indent=gap.indent,
                last_line=gap.last_line,
            )
        del items[0]
        return _Seq(items, open_ws, seq.close_ws)
    prev = items[index - 1]
    assert isinstance(prev.comma, cst.Comma)
    prev_gap = prev.comma.whitespace_after
    if isinstance(gap, cst.ParenthesizedWhitespace):
        if isinstance(prev_gap, cst.ParenthesizedWhitespace):
            merged: _Ws = cst.ParenthesizedWhitespace(
                first_line=prev_gap.first_line,
                empty_lines=gap.empty_lines,
                indent=gap.indent,
                last_line=gap.last_line,
            )
        else:
            merged = gap
    else:
        merged = prev_gap
    items[index - 1] = prev.with_changes(
        comma=prev.comma.with_changes(whitespace_after=merged)
    )
    del items[index]
    return _Seq(items, seq.open_ws, seq.close_ws)


def append_item(
    sequence: cst.List | cst.Tuple, value: cst.BaseExpression
) -> cst.List | cst.Tuple:
    """Add ``value`` as the last item, in the style of the list (comments are kept)."""
    seq = _append(_unpack(sequence), cst.Element(value=value))
    return _pack(sequence, seq)  # type: ignore[return-value]


def insert_item_after(
    sequence: cst.List | cst.Tuple, index: int, value: cst.BaseExpression
) -> cst.List | cst.Tuple:
    """Add ``value`` right after the item at ``index``."""
    seq = _insert_after(_unpack(sequence), index, cst.Element(value=value))
    return _pack(sequence, seq)  # type: ignore[return-value]


def remove_items(
    sequence: cst.List | cst.Tuple, predicate: Callable[[cst.BaseExpression], bool]
) -> cst.List | cst.Tuple:
    """Remove every item whose value satisfies ``predicate``."""
    seq = _unpack(sequence)
    for index in reversed(range(len(seq.items))):
        item = seq.items[index]
        assert isinstance(item, cst.Element)
        if predicate(item.value):
            seq = _remove(seq, index)
    return _pack(sequence, seq)  # type: ignore[return-value]


# --- routes -------------------------------------------------------------------------------------


def _path_args(node: cst.CSTNode) -> Sequence[cst.Arg] | None:
    if (
        isinstance(node, cst.Call)
        and isinstance(node.func, cst.Name)
        and node.func.value == "path"
    ):
        return node.args
    return None


def route_of(node: cst.CSTNode) -> str | None:
    """The route string of a ``path("route", ...)`` call, or ``None`` for anything else."""
    args = _path_args(node)
    if not args or args[0].keyword is not None:
        return None
    return string_value(args[0].value)


def view_of(call: cst.CSTNode) -> cst.BaseExpression | None:
    """The view argument (second positional argument) of a ``path()`` call."""
    args = _path_args(call)
    if args is None or len(args) < 2 or args[1].keyword is not None:
        return None
    return args[1].value


def with_view(call: cst.Call, view: cst.BaseExpression) -> cst.Call:
    """``call`` with its view argument replaced; the rest of the call stays as written."""
    args = list(call.args)
    if len(args) < 2 or args[1].keyword is not None:
        msg = "the path() call has no view argument to replace"
        raise ConfigEditError(msg)
    args[1] = args[1].with_changes(value=view)
    return call.with_changes(args=args)


# --- imports ----------------------------------------------------------------------------------


def _import_from(
    statement: cst.CSTNode, from_module: str
) -> tuple[cst.SimpleStatementLine, int] | None:
    if not isinstance(statement, cst.SimpleStatementLine):
        return None
    for index, small in enumerate(statement.body):
        if (
            isinstance(small, cst.ImportFrom)
            and not small.relative
            and small.module is not None
            and helpers.get_full_name_for_node(small.module) == from_module
        ):
            return statement, index
    return None


def find_import_from(module: cst.Module, from_module: str) -> int | None:
    """Index in ``module.body`` of the first top-level ``from <from_module> import ...``."""
    for index, statement in enumerate(module.body):
        if _import_from(statement, from_module) is not None:
            return index
    return None


def imported_names(module: cst.Module, from_module: str) -> set[str]:
    """Names imported by top-level absolute ``from <from_module> import ...`` statements."""
    names: set[str] = set()
    for statement in module.body:
        found = _import_from(statement, from_module)
        if found is None:
            continue
        line, _ = found
        for small in line.body:
            if (
                isinstance(small, cst.ImportFrom)
                and not small.relative
                and small.module is not None
                and helpers.get_full_name_for_node(small.module) == from_module
                and not isinstance(small.names, cst.ImportStar)
            ):
                names.update(
                    alias.name.value
                    for alias in small.names
                    if isinstance(alias.name, cst.Name)
                )
    return names


def _last_import_index(module: cst.Module) -> int | None:
    last: int | None = None
    for index, statement in enumerate(module.body):
        if isinstance(statement, cst.SimpleStatementLine) and any(
            isinstance(small, (cst.Import, cst.ImportFrom)) for small in statement.body
        ):
            last = index
    return last


def _after_docstring(module: cst.Module) -> int:
    if module.body:
        first = module.body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and len(first.body) == 1
            and isinstance(first.body[0], cst.Expr)
            and isinstance(
                first.body[0].value, (cst.SimpleString, cst.ConcatenatedString)
            )
        ):
            return 1
    return 0


def ensure_import_names(
    module: cst.Module,
    from_module: str,
    names: Sequence[str],
    *,
    fallback_statement: str,
) -> cst.Module:
    """Make sure ``names`` are imported from ``from_module``.

    Missing names are appended to the existing top-level import (one line or in
    parentheses). Without one, ``fallback_statement`` is added after the last import (or
    after the docstring).
    """
    index = find_import_from(module, from_module)
    if index is None:
        statement = cst.parse_statement(fallback_statement + "\n")
        last = _last_import_index(module)
        position = last + 1 if last is not None else _after_docstring(module)
        body = list(module.body)
        body.insert(position, statement)  # type: ignore[arg-type]
        return module.with_changes(body=body)
    found = _import_from(module.body[index], from_module)
    assert found is not None
    line, small_index = found
    node = line.body[small_index]
    assert isinstance(node, cst.ImportFrom)
    seq = _unpack(node)
    present = {item.name.value for item in seq.items if isinstance(item.name, cst.Name)}  # type: ignore[union-attr]
    for name in names:
        if name not in present:
            seq = _append(seq, cst.ImportAlias(name=cst.Name(name)))
    body = list(line.body)
    body[small_index] = _pack(node, seq)  # type: ignore[assignment]
    new_body = list(module.body)
    new_body[index] = line.with_changes(body=body)
    return module.with_changes(body=new_body)


def remove_import_name(module: cst.Module, from_module: str, name: str) -> cst.Module:
    """Remove ``name`` from ``from <from_module> import ...``; drop the line if it was alone."""
    new_body: list[cst.BaseStatement] = []
    for statement in module.body:
        found = _import_from(statement, from_module)
        if found is None:
            new_body.append(statement)
            continue
        line, small_index = found
        node = line.body[small_index]
        assert isinstance(node, cst.ImportFrom)
        if isinstance(node.names, cst.ImportStar):
            new_body.append(statement)
            continue
        seq = _unpack(node)
        indexes = [
            i
            for i, item in enumerate(seq.items)
            if isinstance(item.name, cst.Name) and item.name.value == name  # type: ignore[union-attr]
        ]
        if not indexes:
            new_body.append(statement)
            continue
        for i in reversed(indexes):
            seq = _remove(seq, i)
        if not seq.items:
            smalls = [s for j, s in enumerate(line.body) if j != small_index]
            if smalls:
                new_body.append(line.with_changes(body=smalls))
            continue
        smalls = list(line.body)
        smalls[small_index] = _pack(node, seq)  # type: ignore[assignment]
        new_body.append(line.with_changes(body=smalls))
    if not new_body and not module.header and not module.footer:
        return module.with_changes(body=new_body, has_trailing_newline=False)
    return module.with_changes(body=new_body)


class _NameUses(cst.CSTVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.used = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        return False

    def visit_Import(self, node: cst.Import) -> bool:
        return False

    def visit_Attribute(self, node: cst.Attribute) -> bool:
        node.value.visit(self)  # ``x.NAME`` is not a use of the name NAME
        return False

    def visit_Arg(self, node: cst.Arg) -> bool:
        node.value.visit(self)  # ``f(NAME=1)`` is a keyword, not a use
        return False

    def visit_Name(self, node: cst.Name) -> bool:
        if node.value == self.name:
            self.used = True
        return False


def name_is_used(module: cst.Module, name: str) -> bool:
    """Whether ``name`` is used outside of import statements (strings and comments do not count)."""
    visitor = _NameUses(name)
    module.visit(visitor)
    return visitor.used


# --- the block of imports that django-octave manages ------------------------------------------


def _marker_line(marker: str) -> cst.EmptyLine:
    return cst.EmptyLine(
        indent=True,
        whitespace=cst.SimpleWhitespace(""),
        comment=cst.Comment(marker),
        newline=cst.Newline(),
    )


def _marker_position(lines: Sequence[cst.EmptyLine], marker: str) -> int | None:
    for position, line in enumerate(lines):
        if line.comment is not None and line.comment.value == marker:
            return position
    return None


def remove_marked_block(module: cst.Module, begin: str, end: str) -> cst.Module:
    """Remove the statements between the ``begin`` and ``end`` marker comments, and both markers.

    Comments and blank lines around the block stay. Nothing changes when neither marker is
    there; a marker without its partner raises :class:`ConfigEditError`.
    """
    begin_at: tuple[int, int] | None = None
    end_at: tuple[int, int] | None = None
    for index, statement in enumerate(module.body):
        lines = statement.leading_lines
        if begin_at is None:
            position = _marker_position(lines, begin)
            if position is not None:
                begin_at = (index, position)
        if begin_at is not None and end_at is None:
            start = begin_at[1] + 1 if begin_at[0] == index else 0
            position = _marker_position(lines[start:], end)
            if position is not None:
                end_at = (index, start + position)
    if begin_at is None and end_at is None:
        # An end marker alone is just as unbalanced as a begin marker alone.
        if any(_marker_position(s.leading_lines, end) is not None for s in module.body):
            msg = f"the marker comment {end!r} has no matching {begin!r}"
            raise ConfigEditError(msg)
        return module
    if begin_at is None or end_at is None:
        missing, other = (end, begin) if end_at is None else (begin, end)
        msg = f"the marker comment {other!r} has no matching {missing!r}"
        raise ConfigEditError(msg)

    body = list(module.body)
    first, last = begin_at[0], end_at[0]
    before_marker = list(body[first].leading_lines[: begin_at[1]])
    if first == last:
        lines = list(body[last].leading_lines)
        kept = (
            lines[: begin_at[1]]
            + lines[begin_at[1] + 1 : end_at[1]]
            + lines[end_at[1] + 1 :]
        )
        body[last] = body[last].with_changes(leading_lines=kept)
        return module.with_changes(body=body)
    end_lines = list(body[last].leading_lines)
    del end_lines[end_at[1]]
    body[last] = body[last].with_changes(leading_lines=[*before_marker, *end_lines])
    del body[first:last]
    return module.with_changes(body=body)


def insert_marked_block(
    module: cst.Module,
    *,
    after_index: int | None,
    begin: str,
    end: str,
    statements: Sequence[str],
) -> cst.Module:
    """Insert ``statements`` between the ``begin`` and ``end`` marker comments, after a statement."""
    if after_index is None or not statements:
        msg = "cannot place the block: there is no statement to put it after"
        raise ConfigEditError(msg)
    block = [cst.parse_statement(code + "\n") for code in statements]
    block[0] = block[0].with_changes(
        leading_lines=[_marker_line(begin), *block[0].leading_lines]
    )
    body = list(module.body)
    position = after_index + 1
    body[position:position] = block  # type: ignore[assignment]
    following = position + len(block)
    if following < len(body):
        body[following] = body[following].with_changes(
            leading_lines=[_marker_line(end), *body[following].leading_lines]
        )
        return module.with_changes(body=body)
    return module.with_changes(body=body, footer=[_marker_line(end), *module.footer])


__all__ = [
    "ConfigEditError",
    "SequenceRef",
    "append_item",
    "check_result",
    "dominant_quote",
    "ensure_import_names",
    "find_import_from",
    "find_sequence",
    "imported_names",
    "insert_item_after",
    "insert_marked_block",
    "make_string",
    "name_is_used",
    "parse_source",
    "remove_import_name",
    "remove_items",
    "remove_marked_block",
    "route_of",
    "sequence_of",
    "sequence_strings",
    "string_value",
    "view_of",
    "with_sequence",
    "with_view",
]
