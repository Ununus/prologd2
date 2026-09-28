"""Checks of the document model: files, line endings, encodings, recent list.

    python src/gui/tests/test_documents.py

Qt-free, so it runs anywhere Python does, and it is where the losing-work bugs
would be: a CRLF file rewritten with LF, a cp1251 file read as mojibake, a save
that forgets where it went.  Messages are ASCII on purpose — a piped run encodes
stdout with the ANSI code page, where Cyrillic cannot be encoded at all (see
`ai/conventions.md`).
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import documents  # noqa: E402

RUSSIAN = "член(X, [X|_]).\n"


def test_line_endings_are_detected_from_the_first_break() -> None:
    assert documents.detect_eol("а\nб\n") == "\n"
    assert documents.detect_eol("а\r\nб\r\n") == "\r\n"
    assert documents.detect_eol("а\r\nб\n") == "\r\n", "the first break decides"
    assert documents.detect_eol("без переводов") == "\n", "the default is LF"
    assert documents.detect_eol("") == "\n"
    print("ok: line endings are read from the text")


def test_line_endings_are_written_back() -> None:
    assert documents.with_eol("а\nб\n", "\r\n") == "а\r\nб\r\n"
    assert documents.with_eol("а\r\nб\n", "\n") == "а\nб\n"
    assert documents.with_eol("а\rб", "\n") == "а\nб", "a lone CR counts as a break"
    print("ok: the text is converted both ways, never mixed")


def test_a_file_keeps_its_line_ending_and_its_encoding(directory: pathlib.Path) -> None:
    path = directory / "программа.pld"
    path.write_bytes(RUSSIAN.replace("\n", "\r\n").encode("cp1251"))

    document = documents.Document.from_file(path, encoding="cp1251")
    assert document.eol == "\r\n", "CRLF was not noticed"
    assert document.encoding == "cp1251"
    assert document.text == RUSSIAN, "the editor works in LF"
    assert document.modified is False
    assert document.name == "программа.pld"

    document.set_text("факт(1).\n")
    document.modified = True
    assert document.title() == "*программа.pld"
    document.save()

    written = path.read_bytes()
    assert written == "факт(1).\r\n".encode("cp1251"), written
    assert document.modified is False, "saving must clear the modified flag"
    print("ok: a CRLF cp1251 file is written back byte-for-byte in its own shape")


def test_a_byte_order_mark_is_dropped(directory: pathlib.Path) -> None:
    path = directory / "bom.pld"
    path.write_bytes(b"\xef\xbb\xbf" + RUSSIAN.encode("utf-8"))
    document = documents.Document.from_file(path)
    assert document.text == RUSSIAN, "the mark would sit at the start of line 1"
    document.set_text(document.text)
    document.save()
    assert path.read_bytes() == RUSSIAN.encode("utf-8"), "no mark is written back"
    print("ok: a byte-order mark is dropped on read and never written")


def test_text_that_is_not_utf8_is_reported_not_replaced(directory: pathlib.Path) -> None:
    path = directory / "old.pld"
    path.write_bytes("факт(1).\n".encode("cp1251"))
    try:
        documents.read_text(path)
    except documents.DecodeFailure as failure:
        assert failure.path == str(path)
        assert failure.encoding == "utf-8"
        assert failure.error.start >= 0
        assert "utf-8" in str(failure), "the message names what was tried"
    else:
        raise AssertionError("cp1251 bytes must not pass as UTF-8")

    # Naming the encoding opens it, and the file keeps that encoding.
    text, used = documents.read_text(path, encoding="cp1251")
    assert text == "факт(1).\n" and used == "cp1251"
    print("ok: undecodable text raises instead of being replaced with U+FFFD")


def test_saving_without_a_name_is_refused() -> None:
    document = documents.Document.untitled("Без имени")
    try:
        document.save()
    except ValueError as error:
        assert "имени" in str(error)
    else:
        raise AssertionError("an untitled buffer has no file to write")
    print("ok: an untitled buffer cannot be saved without a path")


def test_save_as_moves_the_buffer_to_the_new_file(directory: pathlib.Path) -> None:
    document = documents.Document.untitled("Без имени 2")
    document.set_text("факт(1).\n")
    target = directory / "новое.pld"
    returned = document.save(target)
    assert returned == str(target)
    assert document.name == "новое.pld" and document.path == str(target)
    assert target.read_bytes() == "факт(1).\n".encode("utf-8")
    print("ok: save as renames the buffer and writes UTF-8")


def test_untitled_names_reuse_a_freed_number() -> None:
    assert documents.untitled_name([]) == "Без имени"
    assert documents.untitled_name(["Без имени"]) == "Без имени 2"
    assert documents.untitled_name(["Без имени", "Без имени 2"]) == "Без имени 3"
    assert documents.untitled_name(["Без имени", "Без имени 3"]) == "Без имени 2"
    assert documents.untitled_name(["программа.pld"]) == "Без имени"
    print("ok: untitled buffers are numbered, and a freed number comes back")


def test_titles_carry_the_modified_marker() -> None:
    document = documents.Document.untitled("Без имени")
    assert document.title() == "Без имени"
    assert document.window_title() == "Без имени — PrologD"
    document.modified = True
    assert document.title() == "*Без имени"
    assert document.window_title() == "*Без имени — PrologD"
    print("ok: the marker is in the tab title and in the window title")


def test_the_recent_list_is_ordered_bounded_and_pruned(directory: pathlib.Path) -> None:
    recent = documents.RecentFiles()
    for number in range(12):
        recent.add(directory / f"файл{number}.pld")
    paths = recent.paths()
    assert len(paths) == documents.RecentFiles.MAX == 10, paths
    assert paths[0].endswith("файл11.pld"), "the newest comes first"

    # Adding a known file moves it to the front instead of duplicating it.
    recent.add(paths[-1])
    assert recent.paths()[0] == paths[-1]
    assert len(recent.paths()) == 10

    # Case does not make a second entry on Windows.
    upper = paths[0].upper()
    recent.add(upper)
    assert len(recent.paths()) == 10, recent.paths()

    # Pruning removes what is gone: the menu is built from this list.
    keep = directory / "есть.pld"
    keep.write_text("факт(1).\n", encoding="utf-8")
    pruned = documents.RecentFiles([str(keep), *recent.paths()]).prune()
    assert pruned == [str(keep)], pruned

    # Removing one entry, and clearing the whole list.
    assert documents.RecentFiles(paths).remove(paths[0]) == paths[1:]
    assert documents.RecentFiles(paths).clear() == []
    print("ok: recent files: newest first, at most ten, pruned and deduplicated")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="prologd_documents_") as name:
        directory = pathlib.Path(name)
        test_line_endings_are_detected_from_the_first_break()
        test_line_endings_are_written_back()
        test_a_file_keeps_its_line_ending_and_its_encoding(directory)
        test_a_byte_order_mark_is_dropped(directory)
        test_text_that_is_not_utf8_is_reported_not_replaced(directory)
        test_saving_without_a_name_is_refused()
        test_save_as_moves_the_buffer_to_the_new_file(directory)
        test_untitled_names_reuse_a_freed_number()
        test_titles_carry_the_modified_marker()
        test_the_recent_list_is_ordered_bounded_and_pruned(directory)
    print("all document checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
