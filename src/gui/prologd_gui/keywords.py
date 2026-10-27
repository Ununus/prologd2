"""The reserved names the interpreter reports in its ``ready`` event.

The list is deliberately *not* kept in the GUI: the interpreter owns it
(``src/prlib/include/prlib/keywords.hpp``, fed by the lexer's reserved set and
the dispatch table), so highlighting, completion and the shortcut cheat-sheet
cannot drift from what the interpreter actually accepts.

This module is Qt-free and therefore testable headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

#: Kinds, spelled as the interpreter spells them.
PREDICATE = "predicate"
OPERATOR = "operator"
DIRECTIVE = "directive"


def _arities(raw: Any) -> tuple[int, ...]:
    """Keeps the integers of an `arities` field, whatever arrived."""
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(
        int(value)
        for value in raw
        if isinstance(value, int) and not isinstance(value, bool)
    )


@dataclass(frozen=True)
class Keyword:
    """One reserved name."""

    name: str
    kind: str = PREDICATE
    arities: tuple[int, ...] = ()
    variadic: bool = False

    @property
    def callable(self) -> bool:
        """True when the name is a predicate a program can call."""
        return self.kind == PREDICATE


class Keywords:
    """The reserved names, indexed by name."""

    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self._by_name: dict[str, Keyword] = {}
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            keyword = Keyword(
                name=str(entry.get("name", "")),
                kind=str(entry.get("kind", PREDICATE)),
                arities=_arities(entry.get("arities")),
                variadic=bool(entry.get("variadic", False)),
            )
            if keyword.name:
                self._by_name[keyword.name] = keyword
        # Byte order, which is what the interpreter sorts by; for UTF-8 it
        # agrees with code-point order, so `sorted` is the same thing.
        self._names = sorted(self._by_name)

    @classmethod
    def from_event(cls, event: dict[str, Any]) -> "Keywords":
        """Builds the table from a ``ready`` event; missing field means empty."""
        return cls(event.get("keywords"))

    @classmethod
    def from_list_lines(cls, text: str) -> "Keywords":
        """Builds the table from `prologd --list-keywords` output.

        The window fetches the names this way when it is opened, so completion
        and colouring work before the first run without keeping an interpreter
        alive; the first real session replaces the table with the `ready`
        event's copy of the same data.  A line is `name/arity`, `name/+` for a
        variadic name, or a bare `name` for an operator or a directive — the
        text form carries no `kind`, so those look like predicates here.  Every
        consumer that needs the kind waits for `ready`; completion uses names
        and arities only.
        """
        entries: dict[str, dict[str, Any]] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            name, slash, tail = line.partition("/")
            entry = entries.setdefault(name, {"name": name, "arities": []})
            if not slash:
                continue
            if tail == "+":
                entry["variadic"] = True
                continue
            try:
                entry["arities"].append(int(tail))
            except ValueError:
                continue
        return cls(list(entries.values()))

    # -- lookups -----------------------------------------------------------
    def names(self) -> list[str]:
        """Every reserved name, sorted."""
        return list(self._names)

    def predicates(self) -> list[Keyword]:
        """Only the callable names, in the same order."""
        return [self._by_name[name] for name in self._names if self._by_name[name].callable]

    def is_reserved(self, name: str) -> bool:
        return name in self._by_name

    def get(self, name: str) -> Keyword | None:
        return self._by_name.get(name)

    def arity(self, name: str) -> tuple[int, ...]:
        """Known arities of `name`; empty for operators, directives and `ВЫВОД`."""
        keyword = self._by_name.get(name)
        return keyword.arities if keyword is not None else ()

    def labels(self, name: str) -> tuple[str, ...]:
        """How the name is shown to a user: ``('ВЫВОД/+',)``, ``('СЛУЧ/1', 'СЛУЧ/3')``."""
        keyword = self._by_name.get(name)
        if keyword is None:
            return ()
        if keyword.variadic:
            return (f"{keyword.name}/+",)
        if not keyword.arities:
            return (keyword.name,)
        return tuple(f"{keyword.name}/{arity}" for arity in keyword.arities)

    def all_labels(self) -> list[str]:
        """Every label in sorted order — the same lines ``prologd --list-keywords`` prints."""
        return [label for name in self._names for label in self.labels(name)]

    # -- containers --------------------------------------------------------
    def __len__(self) -> int:
        return len(self._names)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name

    def __iter__(self) -> Iterator[Keyword]:
        return iter(self._by_name[name] for name in self._names)
