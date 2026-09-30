"""Layout-independent insertions: `Ctrl` plus a **physical** key (task_31).

With the Russian layout active the characters a program needs (`:-`, `()`, `[]`,
`#`, `?`, `>`, `<`, `+`, `*`) sit on other keys than in the English one, and
switching layout to type punctuation is what this table removes: `Ctrl` plus the
key the symbol lives on gives the insert in either layout.

Matching is by **scan code**, never by the character the layout produces —
that is the whole point.  `Ctrl` is the only modifier (plus the `Shift` a chord
needs): `Alt` alone reaches the menu bar on Windows, and `Ctrl+Alt` is `AltGr`
on many layouts, so neither is accepted.  `AltGr` itself is `Ctrl+Alt` on
Windows, which is why a chord never demands `Alt`.

The table is data: it lives in the settings file (`shortcuts/table`, JSON), so a
symbol on another physical key — or a keyboard without that key — is remapped
without a code change.  This module is Qt-free and therefore testable headlessly;
the editor matches `QKeyEvent.nativeScanCode()` against it.

`|` in `insert` marks where the caret ends up, `{}` in `wrap` is the selection a
bracket-like entry wraps (`(` + selection + `)`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator

#: Where the caret ends up inside `Entry.insert`.
CARET = "|"

#: What `Entry.wrap` puts the selected text between.
SELECTION = "{}"


@dataclass(frozen=True)
class Chord:
    """One physical key that triggers an entry."""

    #: Windows scan code of the key (positional, the same in every layout).
    scan: int
    #: `True`/`False` demand that state of `Shift`; `None` accepts either, which
    #: is right for a key that carries a single insert.
    shift: bool | None = None
    #: The key's name in the US layout — for the cheat sheet and for the
    #: collision check against the window's other shortcuts.
    key: str = ""
    #: Which layout justifies this chord: `us` for the rows of the table, `ru`
    #: for the second chord of `:` and `?` (a Russian key, since the symbol is
    #: there in that layout).
    layout: str = "us"

    @property
    def label(self) -> str:
        """`Ctrl+;`, `Ctrl+Shift+.` — how the chord is shown to a user."""
        parts = ["Ctrl"]
        if self.shift:
            parts.append("Shift")
        parts.append(self.key)
        return "+".join(parts)


@dataclass(frozen=True)
class Entry:
    """One insert, with every key that produces it."""

    #: The text to insert, with `CARET` where the caret should stand.
    insert: str
    chords: tuple[Chord, ...]
    #: For the bracket-like entries: what a selection is wrapped with.
    wrap: str | None = None
    #: The character the entry is about, checked against the real layouts.
    char: str = ""

    @property
    def text(self) -> str:
        return self.insert.replace(CARET, "")

    @property
    def caret(self) -> int:
        return self.insert.index(CARET) if CARET in self.insert else len(self.text)


@dataclass(frozen=True)
class Insert:
    """What the editor should replace the selection with, and where to stand."""

    text: str
    #: The caret (or the selection) covers `[start, end)` of `text`.
    start: int
    end: int


#: The table.  Every row is addressed by the physical key, so the same chord
#: works in a Russian and in an English layout.
DEFAULT_ENTRIES: tuple[Entry, ...] = (
    Entry(":-" + CARET + ".", (Chord(0x27, None, ";"), Chord(0x07, None, "6", "ru")),
          char=":"),
    Entry("(" + CARET + ")", (Chord(0x0A, None, "9"),), wrap="(" + SELECTION + ")",
          char="("),
    Entry("[" + CARET + "]", (Chord(0x1A, None, "["),), wrap="[" + SELECTION + "]",
          char="["),
    Entry("#" + CARET, (Chord(0x04, None, "3"),), wrap="#" + SELECTION + "#", char="#"),
    Entry("?" + CARET, (Chord(0x35, True, "/"), Chord(0x08, None, "7", "ru")),
          wrap="?" + SELECTION, char="?"),
    Entry("РАВНО(" + CARET + ",)", (Chord(0x0D, False, "="),), char="="),
    Entry("БОЛЬШЕ(" + CARET + ",)", (Chord(0x34, True, "."),), char=">"),
    Entry("МЕНЬШЕ(" + CARET + ",)", (Chord(0x33, True, ","),), char="<"),
    Entry("СЛОЖЕНИЕ(" + CARET + ",,)", (Chord(0x0D, True, "="),), char="+"),
    Entry("УМНОЖЕНИЕ(" + CARET + ",,)", (Chord(0x09, None, "8"),), char="*"),
    # The simple symbols, so a program can be written without leaving the layout
    # for them either.  Two of them share a key with `=` and `Shift+4`-style
    # neighbours, so their `Shift` state is exact.
    Entry("/", (Chord(0x35, False, "/"),), char="/"),
    Entry("-", (Chord(0x0C, False, "-"),), char="-"),
    Entry("_", (Chord(0x0C, True, "-"),), char="_"),
    Entry("!", (Chord(0x02, None, "1"),), char="!"),
    # The two quote pairs put the caret *inside*: a string or an atom is what is
    # being written next, so the closing quote is only in the way.
    Entry("'" + CARET + "'", (Chord(0x28, False, "'"),), char="'"),
    Entry('"' + CARET + '"', (Chord(0x28, True, "'"),), char='"'),
)

_HEADER = (
    "Ctrl и физическая клавиша — работает в любой раскладке.",
    "`|` показывает, где окажется курсор; `{}` — куда идёт выделенный текст.",
)


class Shortcuts:
    """The table, indexable by `(scan code, shift)`."""

    def __init__(self, entries: tuple[Entry, ...] | list[Entry] = DEFAULT_ENTRIES) -> None:
        self.entries: tuple[Entry, ...] = tuple(entries)
        self._exact: dict[tuple[int, bool], Entry] = {}
        self._any: dict[int, Entry] = {}
        for entry in self.entries:
            for chord in entry.chords:
                if chord.shift is None:
                    self._any[chord.scan] = entry
                else:
                    self._exact[(chord.scan, bool(chord.shift))] = entry

    # -- building ----------------------------------------------------------
    @classmethod
    def default(cls) -> "Shortcuts":
        return cls(DEFAULT_ENTRIES)

    @classmethod
    def from_json(cls, text: str | None) -> "Shortcuts":
        """The table as stored in the settings file; junk means the default.

        A hand-edited file is data like any other: a table that cannot be read
        must not take the window down, and the built-in table is always there to
        fall back to.
        """
        if not text:
            return cls.default()
        try:
            raw = json.loads(text)
        except (TypeError, ValueError):
            return cls.default()
        if not isinstance(raw, list):
            return cls.default()
        entries: list[Entry] = []
        for item in raw:
            if not isinstance(item, dict) or not isinstance(item.get("insert"), str):
                continue
            chords: list[Chord] = []
            for chord in item.get("chords") or []:
                if not isinstance(chord, dict) or not isinstance(chord.get("scan"), int):
                    continue
                shift = chord.get("shift", None)
                chords.append(
                    Chord(
                        scan=int(chord["scan"]),
                        shift=None if shift is None else bool(shift),
                        key=str(chord.get("key", "")),
                        layout=str(chord.get("layout", "us")),
                    )
                )
            if not chords:
                continue
            entries.append(
                Entry(
                    insert=item["insert"],
                    chords=tuple(chords),
                    wrap=item.get("wrap") if isinstance(item.get("wrap"), str) else None,
                    char=str(item.get("char", "")),
                )
            )
        return cls(entries) if entries else cls.default()

    def to_json(self) -> str:
        """The table as it is written into the settings file, one line per entry."""
        raw = []
        for entry in self.entries:
            item: dict[str, Any] = {
                "insert": entry.insert,
                "chords": [
                    {
                        "scan": chord.scan,
                        "shift": chord.shift,
                        "key": chord.key,
                        "layout": chord.layout,
                    }
                    for chord in entry.chords
                ],
            }
            if entry.wrap is not None:
                item["wrap"] = entry.wrap
            if entry.char:
                item["char"] = entry.char
            raw.append(item)
        return json.dumps(raw, ensure_ascii=False, indent=1)

    # -- lookups -----------------------------------------------------------
    def find(self, scan: int, shift: bool) -> Entry | None:
        """The entry for a physical key, or None when nothing is bound to it."""
        entry = self._exact.get((int(scan), bool(shift)))
        if entry is not None:
            return entry
        return self._any.get(int(scan))

    def insert_for(self, scan: int, shift: bool, selection: str = "") -> Insert | None:
        """What the editor should do for a key press, selection included.

        A bracket-like entry *wraps* a selection and keeps it over the wrapped
        text; every other entry replaces it, exactly as typing the character
        would.
        """
        entry = self.find(scan, shift)
        if entry is None:
            return None
        if selection and entry.wrap is not None:
            head, _, tail = entry.wrap.partition(SELECTION)
            text = head + selection + tail
            return Insert(text, len(head), len(head) + len(selection))
        return Insert(entry.text, entry.caret, entry.caret)

    def keys(self) -> list[str]:
        """Every chord as a shortcut string (`Ctrl+Shift+.`) — what must not collide."""
        return [chord.label for entry in self.entries for chord in entry.chords]

    def cheatsheet(self) -> list[str]:
        """The lines the «Шпаргалка» shows: the table, as a user reads it."""
        lines = list(_HEADER)
        lines.append("")
        for entry in self.entries:
            chords = " или ".join(chord.label for chord in entry.chords)
            hint = f"   (выделение → {entry.wrap.replace(SELECTION, '…')})" if entry.wrap else ""
            lines.append(f"{chords}  →  {entry.insert}{hint}")
        return lines

    # -- containers --------------------------------------------------------
    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[Entry]:
        return iter(self.entries)
