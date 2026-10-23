"""Checks of `imports.py`: what a directive names, and what the files hold (task_102).

Qt-free and filesystem-light: the recursion, the cycle and the caching are checked
with a dictionary of texts in place of a disk, and the one real read uses a
temporary folder.

    python src/gui/tests/test_imports.py
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import imports  # noqa: E402


def test_a_directive_names_its_file_in_both_spellings() -> None:
    text = (
        ":- ИМПОРТ(\"библиотека.pld\").\n"
        ":- import('lib/ещё.pld').\n"
        ":- ИМПОРТ(голое_имя).\n"
    )
    assert imports.directive_names(text) == [
        "библиотека.pld",
        "lib/ещё.pld",
        "голое_имя",
    ], imports.directive_names(text)
    print("ok: both spellings and both argument kinds name a file")


def test_a_directive_in_a_comment_or_a_string_names_nothing() -> None:
    text = (
        "% :- ИМПОРТ(\"нет.pld\").\n"
        "факт('ИМПОРТ(\"тоже_нет.pld\")').\n"
        ":- ВЫВОД(\"и это не импорт\").\n"
        ":- ИМПОРТ(\"да.pld\").   % а это импорт\n"
    )
    assert imports.directive_names(text) == ["да.pld"], imports.directive_names(text)
    print("ok: a commented or a quoted directive names nothing")


def test_the_walk_is_recursive_and_survives_a_cycle() -> None:
    disk = {
        "a.pld": ":- ИМПОРТ(\"b.pld\").\nа(1).\n",
        "b.pld": ":- ИМПОРТ(\"c.pld\").\nб(1).\n",
        # Back to `a` — the engine tolerates a cycle, and so must the walk.
        "c.pld": ":- ИМПОРТ(\"a.pld\").\nв(1).\n:- ИМПОРТ(\"пропавший.pld\").\n",
    }
    files = imports.ImportedFiles(read=disk.get)

    def resolve(name, *, source_dir, directories, interpreter_path):
        return name if name in disk else None

    found = files.texts(
        ["a.pld"], resolve=resolve, directories=(), interpreter_path=None
    )
    assert list(found) == ["a.pld", "b.pld", "c.pld"], list(found)
    assert found["c.pld"].startswith(":- ИМПОРТ(\"a.pld\")"), found["c.pld"]
    print("ok: the walk is recursive, sees a file once, and ignores a missing one")


def test_the_files_are_found_through_the_engine_s_order() -> None:
    """The folder of the importing file first, then the `-I` directories."""
    with tempfile.TemporaryDirectory(prefix="prologd_imports_") as folder:
        root = pathlib.Path(folder)
        (root / "проект").mkdir()
        (root / "библиотеки").mkdir()
        (root / "проект" / "своё.pld").write_text("своё(1).\n", encoding="utf-8")
        (root / "библиотеки" / "общее.pld").write_text(
            ':- ИМПОРТ("рядом.pld").\nобщее(1).\n', encoding="utf-8"
        )
        # Imported by `общее.pld`, so it is looked for beside it — not beside the
        # buffer the walk started from.
        (root / "библиотеки" / "рядом.pld").write_text("рядом(1).\n", encoding="utf-8")
        files = imports.ImportedFiles()
        found = files.texts(
            ["своё.pld", "общее.pld"],
            source_dir=root / "проект",
            directories=[str(root / "библиотеки")],
        )
        assert [pathlib.Path(path).name for path in found] == [
            "своё.pld",
            "общее.pld",
            "рядом.pld",
        ], list(found)
        assert found[str(root / "библиотеки" / "рядом.pld")] == "рядом(1).\n"
    print("ok: the search starts in each importing file's own folder")


def test_a_file_is_read_again_only_when_it_changed() -> None:
    """The popup asks on every keystroke that changes a directive, so the read is cached."""
    with tempfile.TemporaryDirectory(prefix="prologd_imports_") as folder:
        path = pathlib.Path(folder) / "библиотека.pld"
        path.write_text("первое(1).\n", encoding="utf-8")
        files = imports.ImportedFiles()
        first = files.texts([str(path)])
        again = files.texts([str(path)])
        assert again == first
        # A second read of an unchanged file is the cached text, not a new one.
        assert again[str(path)] is first[str(path)]
        # A longer file changes its size, and that is enough to read it again.
        path.write_text("первое(1).\nвторое(2).\n", encoding="utf-8")
        changed = files.texts([str(path)])
        assert "второе(2)." in changed[str(path)], changed[str(path)]
    print("ok: an unchanged file is served from the cache, a changed one is read again")


def main(argv: list[str]) -> int:
    test_a_directive_names_its_file_in_both_spellings()
    test_a_directive_in_a_comment_or_a_string_names_nothing()
    test_the_walk_is_recursive_and_survives_a_cycle()
    test_the_files_are_found_through_the_engine_s_order()
    test_a_file_is_read_again_only_when_it_changed()
    print("all imports checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
