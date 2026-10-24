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


# ---------------------------------------------------------------------------
# Typing a file name inside the directive (task_104)
# ---------------------------------------------------------------------------

#: The separator the directive's argument is completed with — the one the
#: examples and the library use.  `\` is accepted as typed, never offered.
SEPARATOR = "/"


def import_argument_at(
    text: str, position: int, keywords=None, mode: int = tokens.MODE_ISO
) -> tuple[str, str] | None:
    """What is typed inside the file name of an `ИМПОРТ` directive, at `position`.

    Answers `(folder, name)`: the folder part as typed (`lib/`, or empty when the
    name stands alone) and the name part — the text after the last separator up to
    the caret.  `None` when the caret is anywhere else: in a comment, in the code
    around the directive, or in a string of another predicate, where a file name
    would be an odd thing to suggest.

    The line is read with the editor's tokenizer, so the directive and its string
    are recognised the same way `directive_names` recognises them.
    """
    line_start = text.rfind("\n", 0, position) + 1
    line_end = text.find("\n", position)
    line = text[line_start:] if line_end < 0 else text[line_start:line_end]
    column = position - line_start
    directive = False
    for token in tokens.tokenize(line, keywords, mode):
        if token.text in DIRECTIVE_NAMES and token.kind in (
            tokens.KEYWORD,
            tokens.ATOM,
            tokens.VARIABLE,
        ):
            directive = True
            continue
        if not directive:
            if token.start > column:
                break
            continue
        if token.kind not in (tokens.STRING, tokens.QUOTED_ATOM):
            continue
        if not token.start < column <= token.end:
            # The caret is past this literal (or before it): not our business.
            return None
        raw = line[token.start : token.end]
        closed = len(raw) >= 2 and raw[-1] == raw[0]
        if closed and column > token.end - 1:
            return None  # at the closing quote or after it
        typed = line[token.start + 1 : column]
        cut = max(typed.rfind("/"), typed.rfind("\\"))
        return (typed[: cut + 1], typed[cut + 1 :]) if cut >= 0 else ("", typed)
    return None


def directory_entries(directory: pathlib.Path) -> list[tuple[str, bool]]:
    """The entries of a folder as `(name, is_a_folder)`, sorted, or empty if absent.

    A folder that is not there is not an error: a half-typed path is the normal
    case while the user types, and a popup has no place for a complaint.
    """
    try:
        with os.scandir(directory) as scanned:
            entries = [
                (entry.name, entry.is_dir())
                for entry in scanned
                if not entry.name.startswith(".")
            ]
    except OSError:
        return []
    entries.sort(key=lambda item: (not item[1], item[0].lower()))
    return entries


def search_folders(
    source_dir: pathlib.Path | None, directories=(), interpreter_path: str | None = None
) -> list[pathlib.Path]:
    """Where an `ИМПОРТ` name is looked for, in the engine's order (`resolve_import`).

    The folder of the importing file first, then the `-I` directories, then
    `stdlib` beside the interpreter — and only the folders that exist, because a
    popup lists what it can.
    """
    candidates: list[pathlib.Path] = []
    if source_dir is not None:
        candidates.append(pathlib.Path(source_dir))
    candidates += [pathlib.Path(directory) for directory in directories]
    if interpreter_path:
        candidates.append(pathlib.Path(interpreter_path).parent / "stdlib")
    unique: list[pathlib.Path] = []
    for candidate in candidates:
        if candidate not in unique and candidate.is_dir():
            unique.append(candidate)
    return unique


def complete_names(
    folders, typed: str, *, pattern: str = ".pld", lister=None
) -> list[str]:
    """What the half-typed `typed` can become: the entries of its folder, filtered.

    `typed` is the whole argument as far as the caret (`lib/is`): its folder part
    chooses the folder to list (inside every one of `folders`), its name part
    filters the entries.  Folders come first with a trailing `/`, then the files of
    `pattern`; both are compared without case, because Windows is.
    """
    lister = lister if lister is not None else directory_entries
    cut = max(typed.rfind("/"), typed.rfind("\\"))
    folder = typed[: cut + 1]
    prefix = typed[cut + 1 :].lower()
    names: list[str] = []
    for root in folders:
        directory = pathlib.Path(root) / folder if folder else pathlib.Path(root)
        for name, is_folder in lister(directory):
            if not name.lower().startswith(prefix):
                continue
            if is_folder:
                names.append(name + SEPARATOR)
            elif name.lower().endswith(pattern):
                names.append(name)
    unique: list[str] = []
    for name in names:
        if name not in unique:
            unique.append(name)
    unique.sort(key=lambda item: (not item.endswith(SEPARATOR), item.lower()))
    return unique
