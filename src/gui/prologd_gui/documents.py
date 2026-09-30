"""Open programs: their file state, their line endings, the recent list.

Qt-free on purpose — file I/O included.  What a buffer does with a *file* (which
line ending to write back, which encoding the text arrived in, whether the text
still matches what is on disk) is the part worth testing without a display, and
it is also the part that loses work when it is wrong.  The window keeps only the
widgets and the prompts.
"""

from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass
from typing import Iterable

UNTITLED = "Без имени"

EOL_LF = "\n"
EOL_CRLF = "\r\n"

#: What a file is assumed to be.  Nothing else is guessed: text that is not
#: UTF-8 is reported, and the window asks which encoding to use rather than
#: silently replacing bytes with something that only looks like text.
DEFAULT_ENCODING = "utf-8"

#: Offered in that dialog, in the order a Russian-language tool should: the
#: code pages an old Windows editor wrote, then UTF-8 for the rest.
SUGGESTED_ENCODINGS = ("cp1251", "cp866", "latin-1", "utf-8")


class DecodeFailure(Exception):
    """The bytes are not text in the encoding that was tried."""

    def __init__(self, path: str, encoding: str, error: UnicodeDecodeError) -> None:
        super().__init__(
            f"{path}: не читается как {encoding} — {error.reason} "
            f"(позиция {error.start})"
        )
        self.path = path
        self.encoding = encoding
        self.error = error


def detect_eol(text: str) -> str:
    """The line ending of `text`, judged by its first line break.

    A file is not required to be consistent, and the first break is the one that
    identifies it in every editor the user may have written it in.
    """
    index = text.find("\n")
    if index > 0 and text[index - 1] == "\r":
        return EOL_CRLF
    return EOL_LF


def with_eol(text: str, eol: str) -> str:
    """`text` — always LF in the editor — written back in `eol`."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", eol)


def read_text(path: str | os.PathLike[str], encoding: str | None = None) -> tuple[str, str]:
    """Reads a program: its text and the encoding it was read in.

    A byte-order mark is dropped, whatever the encoding: the lexer ignores one
    too, but keeping it would put an invisible character at the start of the
    first line of the editor.
    """
    data = pathlib.Path(path).read_bytes()
    used = encoding or DEFAULT_ENCODING
    try:
        text = data.decode(used)
    except UnicodeDecodeError as error:
        raise DecodeFailure(str(path), used, error) from error
    if text.startswith("\ufeff"):
        text = text[1:]
    return text, used


def write_text(
    path: str | os.PathLike[str], text: str, *, encoding: str = DEFAULT_ENCODING, eol: str = EOL_LF
) -> None:
    """Writes a program, in the encoding and line ending it came with."""
    pathlib.Path(path).write_bytes(with_eol(text, eol).encode(encoding, errors="strict"))


def untitled_name(used: Iterable[str]) -> str:
    """`Без имени`, `Без имени 2`, … — a freed number is used again.

    Numbers are not a counter that only grows: closing the second new buffer and
    making another one gives `Без имени 2`, which is what a user expects and what
    keeps the tab titles short.
    """
    taken = set(used)
    if UNTITLED not in taken:
        return UNTITLED
    number = 2
    while f"{UNTITLED} {number}" in taken:
        number += 1
    return f"{UNTITLED} {number}"


def short_path(path: str | os.PathLike[str], parts: int = 2) -> str:
    """A path as a *place* one can read: the last `parts` components, `…` before.

    The status bar is one line the user scans while working, and a full
    `C:\\Users\\…\\examples\\lessons\\lesson_04.pld` in it pushes everything else
    out of sight.  The window title keeps the whole path — two files of one name
    have to be told apart — the status line only has to say *where*.
    """
    text = str(path)
    pieces = pathlib.Path(text).parts
    if len(pieces) <= parts:
        return text
    return "…" + os.sep + os.sep.join(pieces[-parts:])


@dataclass
class Document:
    """One open buffer, and what is known about the file behind it.

    `modified` mirrors the editor's own flag — Qt clears it when an undo brings
    the text back to what was saved, which a flag of our own could not do — so
    the window pushes the state in rather than this class guessing it.
    """

    name: str = UNTITLED
    path: str | None = None
    eol: str = EOL_LF
    encoding: str = DEFAULT_ENCODING
    modified: bool = False
    text: str = ""

    # -- construction ------------------------------------------------------
    @classmethod
    def from_file(cls, path: str | os.PathLike[str], encoding: str | None = None) -> "Document":
        """Reads a file, remembering its line ending and its encoding.

        `text` is held in LF like the editor holds it; `eol` remembers what the
        file used, and that is what a save writes back.
        """
        raw, used = read_text(path, encoding)
        return cls(
            name=pathlib.Path(path).name,
            path=str(path),
            eol=detect_eol(raw),
            encoding=used,
            modified=False,
            text=with_eol(raw, EOL_LF),
        )

    @classmethod
    def untitled(cls, name: str) -> "Document":
        """An empty buffer.  It is written with LF until it is saved: a new
        program has no file to tell us otherwise."""
        return cls(name=name, path=None, eol=EOL_LF, encoding=DEFAULT_ENCODING, text="")

    # -- names -------------------------------------------------------------
    def title(self) -> str:
        """The tab title: the name, with `*` while there are unsaved changes."""
        return ("*" if self.modified else "") + self.name

    def window_title(self) -> str:
        """What the title bar says: the file's *full* path, plus `*` while there
        are unsaved changes.

        The tab keeps the short name — a tab bar full of paths is unreadable — and
        the window carries where those tabs are, so two files with one name are
        told apart without opening anything.
        """
        return f"{'*' if self.modified else ''}{self.path or self.name} — PrologD"

    def directory(self) -> str:
        """Where its file lives, for the open/save dialogs; the cwd otherwise."""
        if self.path:
            return str(pathlib.Path(self.path).parent)
        return ""
    def rename(self, path: str | os.PathLike[str]) -> None:
        self.path = str(path)
        self.name = pathlib.Path(path).name

    # -- text --------------------------------------------------------------
    def set_text(self, text: str) -> None:
        """Takes the editor's text; the editor works in LF, so `eol` stays."""
        self.text = text

    def save(self, path: str | os.PathLike[str] | None = None) -> str:
        """Writes the buffer and records where it went.

        `UnicodeEncodeError` is left to the caller: a file read as cp1251 cannot
        hold every character either, and the answer is to offer UTF-8 rather than
        to write replacement characters.
        """
        target = path if path is not None else self.path
        if not target:
            raise ValueError("у буфера нет имени файла")
        write_text(target, self.text, encoding=self.encoding, eol=self.eol)
        self.rename(target)
        self.modified = False
        return self.path or str(target)


#: How much *untitled* text a remembered session may hold (task_29).  The store
#: is a text file a human may open, so the budget is small enough to keep it
#: readable; what does not fit is dropped, and the window says how much.
SESSION_TEXT_BUDGET = 256 * 1024


@dataclass(frozen=True)
class TabRecord:
    """One tab as it is remembered between runs (task_29).

    A file is remembered by its **path**: the next run reads the file, so the tab
    shows the file on disk rather than what the editor held when the window
    closed — a user who answered «не сохранять» meant it.  An untitled buffer has
    no file to read, so its text travels with the record, up to the budget.
    """

    path: str = ""
    name: str = ""
    text: str = ""

    @property
    def untitled(self) -> bool:
        return not self.path


def encode_tabs(records: Iterable[TabRecord]) -> list[str]:
    """The records as the settings file holds them: `path<TAB>name<TAB>text`.

    One entry per tab, in the order the tab bar shows them, and the tab character
    as the separator simply because no path or buffer name may contain one.
    """
    return [f"{record.path}\t{record.name}\t{record.text}" for record in records]


def decode_tabs(lines: Iterable[str]) -> list[TabRecord]:
    """The other way.  A line that makes no sense is dropped, never fatal.

    The file may be hand-edited, or written by another version: a session that
    cannot be read may cost the *session*, never the start.
    """
    records: list[TabRecord] = []
    for line in lines or []:
        if not isinstance(line, str) or line.count("\t") < 2:
            continue
        path, name, text = line.split("\t", 2)
        records.append(TabRecord(path=path, name=name, text=text))
    return records


def session_records(
    tabs: Iterable[tuple[str, str, str]], budget: int = SESSION_TEXT_BUDGET
) -> tuple[list[TabRecord], int]:
    """What of the open tabs is worth remembering, and how many were dropped.

    `tabs` are `(path, name, text)` triples in tab-bar order.  Only an *untitled*
    buffer spends the budget, and one that does not fit is dropped whole: a tab
    that comes back with half of its text is worse than one that does not come
    back, and the window says how many were left out.  An empty untitled tab is
    skipped altogether — it is the placeholder a first file would replace anyway.
    """
    records: list[TabRecord] = []
    dropped = 0
    spent = 0
    for path, name, text in tabs:
        if path:
            records.append(TabRecord(path=str(path), name=str(name)))
            continue
        if not str(text).strip():
            continue
        if spent + len(text) > budget:
            dropped += 1
            continue
        spent += len(text)
        records.append(TabRecord(name=str(name), text=str(text)))
    return records, dropped


class RecentFiles:
    """The files opened last, newest first, at most `max` of them."""

    MAX = 10

    def __init__(self, paths: Iterable[str] = (), max_size: int | None = None) -> None:
        """`max_size` is the limit from the settings (task_29's «Помнить
        недавних файлов»); `MAX` stays the default for a caller that has none."""
        self._max = self.MAX if max_size is None else max(0, int(max_size))
        self._paths = _unique(paths)[: self._max]

    def paths(self) -> list[str]:
        return list(self._paths)

    def limit(self) -> int:
        return self._max

    def add(self, path: str | os.PathLike[str]) -> list[str]:
        """Records a use, moving an already known file to the front."""
        self._paths = _unique([str(path), *self._paths])[: self._max]
        return self.paths()

    def remove(self, path: str | os.PathLike[str]) -> list[str]:
        key = _key(path)
        self._paths = [item for item in self._paths if _key(item) != key]
        return self.paths()

    def prune(self) -> list[str]:
        """Drops what is no longer on disk — what the menu is built from."""
        self._paths = [item for item in self._paths if pathlib.Path(item).is_file()]
        return self.paths()

    def clear(self) -> list[str]:
        self._paths = []
        return []


def _key(path: str | os.PathLike[str]) -> str:
    # Windows does not care about case in a path, so neither does the list:
    # `C:\\A.pld` and `c:\\a.pld` are one file, not two entries.
    return os.path.normcase(str(path))


def _unique(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if not path:
            continue
        key = _key(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(str(path))
    return result
