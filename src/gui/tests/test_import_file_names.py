"""Typing a file name inside «ИМПОРТ(…)"»: the prefix, the folders, the entries.

Qt-free: the questions are about a text, a caret and a folder on disk.

    python src/gui/tests/test_import_file_names.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import imports  # noqa: E402

FOLDERS = [pathlib.Path("C:/проект"), pathlib.Path("C:/библиотеки")]


def test_the_caret_inside_the_directive_names_what_is_typed() -> None:
    text = ':- ИМПОРТ("lib/is"), ВЫВОД(1).\n'
    caret = text.index("is") + 2
    assert imports.import_argument_at(text, caret) == ("lib/", "is"), (
        imports.import_argument_at(text, caret)
    )
    # The name alone: no folder part yet, and the English spelling counts too.
    alone = ':- import("is'
    assert imports.import_argument_at(alone, len(alone)) == ("", "is")
    # A quoted atom is the same argument to the parser, so it completes too.
    quoted = ":- ИМПОРТ('is"
    assert imports.import_argument_at(quoted, len(quoted)) == ("", "is")
    # Right after a slash the folder is the whole answer, the name is empty.
    fresh = ':- ИМПОРТ("lib/'
    assert imports.import_argument_at(fresh, len(fresh)) == ("lib/", "")
    print("ok: the caret inside the directive's string knows what is typed")


def test_the_caret_anywhere_else_asks_nothing() -> None:
    ordinary = ':- ВЫВОД("is'
    assert imports.import_argument_at(ordinary, len(ordinary)) is None
    # A directive in a comment is not a directive.
    commented = '% :- ИМПОРТ("is'
    assert imports.import_argument_at(commented, len(commented)) is None
    # Before the opening quote and past the closing one there is nothing to offer.
    text = ':- ИМПОРТ("iso.pld").'
    assert imports.import_argument_at(text, text.index("(")) is None
    assert imports.import_argument_at(text, len(text)) is None
    # Another line entirely.
    two_lines = ':- ИМПОРТ("iso.pld").\nцель :- ВЫВОД(1).'
    assert imports.import_argument_at(two_lines, len(two_lines)) is None
    print("ok: an ordinary string, a comment and the code around get nothing")


def test_the_entries_are_folders_first_then_files() -> None:
    text = ':- ИМПОРТ("'
    typed = imports.import_argument_at(text, len(text))
    assert typed == ("", ""), typed

    def lister(directory: pathlib.Path):
        assert directory in FOLDERS, directory
        return [("library.pld", False), ("iso.pld", False), ("lib", True), ("README.md", False)]

    names = imports.complete_names(FOLDERS, "i", lister=lister)
    # One folder matches nothing here, so the list is the one folder's entries:
    # `i` matches `iso.pld` only.
    assert names == ["iso.pld"], names
    # Empty prefix: folders first (with a slash), then the `.pld` files — the
    # markdown is not a program and is not offered.
    assert imports.complete_names(FOLDERS[:1], "", lister=lister) == [
        "lib/",
        "iso.pld",
        "library.pld",
    ], imports.complete_names(FOLDERS[:1], "", lister=lister)
    # The case of the typed prefix does not matter: Windows would find the file.
    assert imports.complete_names(FOLDERS[:1], "ISO", lister=lister) == ["iso.pld"]
    print("ok: folders first, then the `.pld` files, matched without case")


def test_a_subfolder_is_listed_from_the_typed_folder() -> None:
    seen: list[pathlib.Path] = []

    def lister(directory: pathlib.Path):
        seen.append(directory)
        return [("внутри.pld", False)]

    names = imports.complete_names(FOLDERS[:1], "lib/вн", lister=lister)
    assert names == ["внутри.pld"], names
    assert seen == [pathlib.Path("C:/проект/lib")], seen
    # A folder that is not there lists nothing — no error, no complaint.
    assert imports.complete_names(FOLDERS, "нет/такой", lister=lambda path: []) == []
    print("ok: a typed folder narrows the listing, a missing one says nothing")


def test_the_folders_are_the_ones_the_engine_would_try() -> None:
    with tempfile.TemporaryDirectory(prefix="prologd_folders_") as folder:
        root = pathlib.Path(folder)
        (root / "проект").mkdir()
        (root / "библиотеки").mkdir()
        (root / "stdlib").mkdir()
        found = imports.search_folders(
            root / "проект", [str(root / "библиотеки"), str(root / "нет")], str(root / "prologd.exe")
        )
        assert found == [root / "проект", root / "библиотеки", root / "stdlib"], found
        # The same folder twice is one entry, and the order is the engine's.
        twice = imports.search_folders(root / "проект", [str(root / "проект")], None)
        assert twice == [root / "проект"], twice
    print("ok: the search folders are the file's own, the -I rows and stdlib")


def main(argv: list[str]) -> int:
    test_the_caret_inside_the_directive_names_what_is_typed()
    test_the_caret_anywhere_else_asks_nothing()
    test_the_entries_are_folders_first_then_files()
    test_a_subfolder_is_listed_from_the_typed_folder()
    test_the_folders_are_the_ones_the_engine_would_try()
    print("all import file-name checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
