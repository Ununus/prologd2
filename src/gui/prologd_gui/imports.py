"""The files a program brings in with `ИМПОРТ` (task_102).

Completion offers the names written in the buffer, and in Prolog the name of the
next goal is very often the name of a *library* predicate — one that lives in
another file and is named only by a directive.  Two questions are answered here:
which files the directives of a text name, and what is written in them.

The resolution is `paths.resolve_import`, the one `F12` uses (task_69), so the
file read here is the file the run would load.  The walk is recursive — an
imported file may import its own — and remembers what it has seen, because the
engine tolerates a cycle and so must this.  A name that is nowhere to be found is
not an error: the interpreter reports it when the program runs, and a popup is no
place for that.

Qt-free and lazy: nothing is read until `ImportedFiles.texts` is asked for it, and
a file is read again only when its size or modification time changed.

    QT_QPA_PLATFORM=offscreen PYTHONUTF8=1 python src/gui/tests/test_imports.py
"""

from __future__ import annotations

import os
import pathlib

from . import paths, tokens

#: The two spellings of the directive — the Russian name and its English alias.
DIRECTIVE_NAMES = ("ИМПОРТ", "import")


def directive_names(
    text: str, keywords=None, mode: int = tokens.MODE_ISO
) -> list[str]:
    """The file names the `ИМПОРТ` directives of `text` name, in the order written.

    The line is read with the editor's own tokenizer, so a directive inside a
    comment or a string names nothing, and both spellings count.  The argument is
    a string or, since the parser takes an atom too, a bare name;
    `tokens.literal_text` unwraps the quotes the tokenizer keeps.
    """
    names: list[str] = []
    for line in text.splitlines():
        # The whole text is scanned on every keystroke that changes the directive
        # list, so the lines that cannot carry one are dropped by a substring test
        # before the tokenizer sees them.
        if "ИМПОРТ" not in line and "import" not in line:
            continue
        inside = False
        for token in tokens.tokenize(line, keywords, mode):
            # The name of the directive is a reserved word, so it arrives as a
            # `KEYWORD` when the table is known; without a table (a window that has
            # not run the interpreter yet) a capitalised `ИМПОРТ` is a *variable*
            # and the English `import` an atom, so all three kinds count.
            if token.text in DIRECTIVE_NAMES and token.kind in (
                tokens.KEYWORD,
                tokens.ATOM,
                tokens.VARIABLE,
            ):
                inside = True
            elif inside and token.kind in (tokens.STRING, tokens.QUOTED_ATOM):
                # The parser takes a string or an atom, and the tokenizer hands a
                # literal over as it was written — `tokens.literal_text` unwraps it.
                names.append(tokens.literal_text(token.text))
                break
            elif inside and token.kind == tokens.ATOM:
                names.append(token.text)
                break
            elif inside and token.kind in (tokens.COMMENT, tokens.PUNCTUATION):
                if token.text != "(":
                    break
    return names


class ImportedFiles:
    """The texts a buffer's imports bring in, each read once per version of the file.

    The result is `{path: text}` in the order the directives are written, with the
    files an imported file imports of its own added after it — the order the engine
    loads them in.  `resolve` and `read` are seams: the check of this module needs
    neither a built tree nor a display.
    """

    def __init__(self, read=None) -> None:
        #: path -> (modification time, size, text): what was read last time.
        self._read: dict[str, tuple[int, int, str]] = {}
        #: How a path becomes its text; `None` means «read the file».  The check of
        #: this module hands in a dictionary instead, so the walk is tested without a
        #: disk and the cache is not in the way of what it checks.
        self._read_from = read

    def texts(
        self,
        names,
        *,
        source_dir: pathlib.Path | None = None,
        directories=(),
        interpreter_path: str | None = None,
        resolve=None,
    ) -> dict[str, str]:
        """Every file the given directives name, read, and their own imports too."""
        finder = resolve if resolve is not None else paths.resolve_import
        found: dict[str, str] = {}
        self._walk(
            list(names),
            source_dir=source_dir,
            directories=tuple(directories),
            interpreter_path=interpreter_path,
            finder=finder,
            found=found,
            seen=set(),
        )
        return found

    def forget(self) -> None:
        """Drops what was read; the next ask reads every file again."""
        self._read.clear()

    # -- internals ---------------------------------------------------------
    def _walk(
        self,
        names,
        *,
        source_dir,
        directories,
        interpreter_path,
        finder,
        found: dict[str, str],
        seen: set[str],
    ) -> None:
        for name in names:
            path = finder(
                name,
                source_dir=source_dir,
                directories=directories,
                interpreter_path=interpreter_path,
            )
            if not path or path in seen:
                continue
            seen.add(path)
            content = self._read_file(path)
            if content is None:
                continue
            found[path] = content
            # An imported file may import its own; the search starts in *its*
            # folder, exactly as the engine resolves the directive it was reached
            # through.
            self._walk(
                directive_names(content),
                source_dir=pathlib.Path(path).parent,
                directories=directories,
                interpreter_path=interpreter_path,
                finder=finder,
                found=found,
                seen=seen,
            )

    def _read_file(self, path: str) -> str | None:
        if self._read_from is not None:
            return self._read_from(path)
        try:
            status = os.stat(path)
        except OSError:
            return None
        stamp = (status.st_mtime_ns, status.st_size)
        cached = self._read.get(path)
        if cached is not None and cached[0] == stamp[0] and cached[1] == stamp[1]:
            return cached[2]
        try:
            # `utf-8-sig` drops a byte-order mark: the tokenizer would otherwise
            # see one unknown character before the first name of the file.
            content = pathlib.Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None
        self._read[path] = (stamp[0], stamp[1], content)
        return content
