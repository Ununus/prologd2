"""The built-in reference — the records of `doc/builtins.json`.

    from prologd_gui.reference import Reference
    reference = Reference.load()      # a missing file is an empty reference
    reference.summary("КОПИЯ")        # 'Подстрока и поиск: ...'
    reference.variants("substring")   # the five argument modes of §7.4

Qt-free on purpose, like `keywords.py` and `protocol.py`: the window, the
completion popup and the tests all read the same object, and nothing here needs a
display.

The file is data, not a document: it is the one place a predicate's summary, its
argument modes and its English spelling are written down, and `doc/help.typ`
builds its appendix table from it.  `test_reference.py` keeps it in step with the
interpreter (`--list-keywords` and the `ready` event) and with the section
numbers of the manual.

A missing or broken file must never break the window: `load` answers an *empty*
reference then, the popup shows names and arities without descriptions, and the
help command says there is no record.  The GUI has to work in a checkout where
`doc/` was not copied.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator

#: Where the records live in a checkout: `src/gui/prologd_gui/` -> the root.
DEFAULT_PATH = pathlib.Path(__file__).resolve().parents[3] / "doc" / "builtins.json"


class Reference:
    """The records by name; an alias resolves to the record of its predicate."""

    def __init__(self, records: list[dict] | None = None) -> None:
        self._records: list[dict] = list(records or [])
        self._by_name: dict[str, dict] = {}
        for record in self._records:
            for name in self._names_of(record):
                self._by_name.setdefault(name, record)

    @staticmethod
    def _names_of(record: dict) -> Iterator[str]:
        """Every spelling the record answers to: its name and its aliases."""
        name = record.get("name")
        if isinstance(name, str) and name:
            yield name
        aliases = record.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias:
                    yield alias

    @classmethod
    def load(cls, path: str | pathlib.Path | None = None) -> "Reference":
        """Reads the file; anything unreadable or malformed answers an empty one."""
        try:
            text = pathlib.Path(path or DEFAULT_PATH).read_text(encoding="utf-8")
            data = json.loads(text)
            records = data.get("records", []) if isinstance(data, dict) else []
        except (OSError, ValueError):
            return cls()
        if not isinstance(records, list):
            return cls()
        return cls([record for record in records if isinstance(record, dict)])

    def __len__(self) -> int:
        return len(self._records)

    def record(self, name: str) -> dict | None:
        """The record of a predicate, by any of its spellings."""
        return self._by_name.get(name)

    def summary(self, name: str) -> str:
        """The one-line description, or "" when the name has no record."""
        record = self.record(name)
        text = record.get("summary") if record else None
        return text if isinstance(text, str) else ""

    def variants(self, name: str) -> list[str]:
        """The argument modes, one complete call form per line."""
        record = self.record(name)
        lines = record.get("variants") if record else None
        if not isinstance(lines, list):
            return []
        return [line for line in lines if isinstance(line, str)]

    def section(self, name: str) -> str:
        """The `doc/help.typ` heading the record comes from (e.g. `7.4`)."""
        record = self.record(name)
        text = record.get("section") if record else None
        return text if isinstance(text, str) else ""
