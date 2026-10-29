"""The built-in reference — the records of `doc/builtins.json`.

    from prologd_gui.reference import Reference
    reference = Reference.load()      # a missing file is an empty reference
    reference.summary("КОПИЯ")        # 'Подстрока и поиск: ...'
    reference.variants("КОПИЯ")   # the five argument modes of §7.4

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
`doc/` was not copied — and, in a package (task_61), the file travels beside the
window with the documents (`paths.builtins`).
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator

from . import paths

#: Where the records live: `doc/builtins.json` of the checkout or of the package.
DEFAULT_PATH = paths.builtins()


def record_title(record: dict) -> str:
    """The first line of a record: `ИМЯ (алиас) — сводка`.

    The English spelling is no longer a line of its own (2026-10-02): it sits
    next to the Russian name in parentheses, so the help reads
    `ВВКОД (put_code) — …` instead of a separate «английское имя».  A name with
    several spellings lists them all: `ИМЯ (alias1, alias2) — …`.
    """
    name = record.get("name")
    head = str(name) if isinstance(name, str) else ""
    aliases = [alias for alias in (record.get("aliases") or []) if isinstance(alias, str)]
    if aliases:
        head = f"{head} ({', '.join(aliases)})"
    summary = record.get("summary")
    if isinstance(summary, str) and summary:
        return f"{head} — {summary}" if head else summary
    return head


#: The `kind` of a record in the words a reader of the window understands.
KIND_LABELS = {
    "predicate": "предикат",
    "function": "функция",
    "operator": "знак",
    "directive": "директива",
}

#: The `group` of a record — the same words the manual's contents use.
GROUP_LABELS = {
    "arith": "арифметика",
    "io": "ввод и вывод",
    "types": "типы",
    "control": "управление выводом",
    "database": "база знаний",
    "strings": "строки",
    "graphics": "графика",
    "debug": "отладка",
    "lists": "списки",
    "modules": "модули",
}


def card_html(record: dict, palette, mono: str = "") -> str:
    """The record as the `F1` dock shows it: a card, not a list of lines.

    Inline styles and the `<table>` of the rich-text subset `QTextDocument`
    supports (no classes, no flex): the colours come from the theme palette, so the
    card follows the light and the dark theme, and the names are set in the editor's
    own monospace face (part 235).
    """
    name = _text(record.get("name"))
    aliases = [alias for alias in (record.get("aliases") or []) if isinstance(alias, str)]
    kind = KIND_LABELS.get(_text(record.get("kind")), "")
    group = GROUP_LABELS.get(_text(record.get("group")), "")
    arities = [str(arity) for arity in (record.get("arities") or []) if isinstance(arity, int)]
    summary = _text(record.get("summary"))
    variants = [variant for variant in (record.get("variants") or []) if isinstance(variant, str)]
    section = _text(record.get("section"))

    def code(text: str) -> str:
        family = f"font-family:'{mono}';" if mono else ""
        return f'<span style="{family}">{_escape(text)}</span>'

    meta = " · ".join(
        part for part in (kind, f"арности {', '.join(arities)}" if arities else "", group) if part
    )
    title = _escape(name)
    if aliases:
        title += f' <span style="font-weight:normal">{_escape(", ".join(aliases))}</span>'

    parts = [
        f'<p style="margin:0;font-size:large;font-weight:bold;'
        f'color:{palette.syntax.keyword}">{title}</p>'
    ]
    if meta:
        parts.append(
            f'<p style="margin:0 0 6px 0;color:{palette.placeholder}">{_escape(meta)}</p>'
        )
    if summary:
        parts.append(f'<p style="margin:0 0 8px 0;font-style:italic">{_escape(summary)}</p>')
    if variants:
        rule = f"border-bottom:1px solid {palette.alternate_base}"
        rows = []
        for variant in variants:
            call, dash, what = variant.partition(" — ")
            if dash:
                rows.append(
                    f'<tr><td width="45%" style="padding:4px 12px 4px 0;{rule}">'
                    f"{code(call)}</td>"
                    f'<td style="padding:4px 0;{rule}">{_escape(what)}</td></tr>'
                )
            else:
                rows.append(f'<tr><td colspan="2" style="padding:4px 0">{code(variant)}</td></tr>')
        parts.append(
            '<table width="100%" cellspacing="0" cellpadding="3" '
            'style="border-collapse:collapse">' + "".join(rows) + "</table>"
        )
    if section:
        parts.append(
            f'<p style="margin:8px 0 0 0"><a href="section:{_escape(section)}">'
            f"руководство, §{_escape(section)}</a></p>"
        )
    return "".join(parts)


def load_section_pages(path=None) -> dict[str, int]:
    """`section -> page` of the manual; an empty map when the docs were not built.

    The file is the array `help.typ` emits through a hidden `<help-sections>`
    element, one `{"number": "7.4", "page": 22}` per heading (part 235).
    """
    try:
        data = json.loads(pathlib.Path(path or pages_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        data = data[0]  # a query of one element answers a list of lists
    pages: dict[str, int] = {}
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            number, page = row.get("number"), row.get("page")
            if isinstance(number, str) and isinstance(page, int) and number not in pages:
                pages[number] = page
    return pages


def pages_path() -> pathlib.Path:
    """Where the map lives: `doc/help_sections.json`, beside the manuals."""
    return paths.sections()


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


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

    def title(self, name: str) -> str:
        """The first line of a record, by name: `ИМЯ (алиас) — сводка`."""
        record = self.record(name)
        return record_title(record) if record else ""

    def detail_lines(self, name: str) -> list[str]:
        """The popup's preview: the title, then one line per call form.

        What the completion popup shows under the list (2026-10-02): the name
        with its alias and summary, then the argument modes — the same facts the
        `F1` dock shows, compacted to what a glance needs.
        """
        record = self.record(name)
        if record is None:
            return []
        title = record_title(record)
        if not title:
            return []
        lines = [title]
        variants = self.variants(name)
        if variants:
            lines.append("")
            lines.extend(variants)
        return lines
