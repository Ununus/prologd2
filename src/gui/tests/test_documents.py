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


def test_a_line_separator_becomes_a_plain_newline(directory: pathlib.Path) -> None:
    """`U+2028`/`U+2029` are folded on read (`tokens.LINE_SEPARATORS`, 2026-10-03).

    The editor draws `U+2028` as a new line while `blockCount()` does not count it,
    so the line numbers and the question markers of the margin stand on the wrong
    lines; `prologu` rejects the character instead of breaking the line.  A file that
    carries one is therefore read as if it had a plain newline — and written back
    with one, in the shape the editor showed.
    """
    path = directory / "разделитель.pld"
    path.write_bytes("?факт(1).\u2028?факт(2).\u2029".encode("utf-8"))
    text, used = documents.read_text(path)
    assert text == "?факт(1).\n?факт(2).\n", ascii(text)
    assert used == "utf-8"

    # The fold happens before the line ending is judged: a `U+2028` on the first
    # line of a CRLF file may not hide that the file is CRLF.
    path.write_bytes("?факт(1).\r\n\u2028?факт(2).\r\n".encode("utf-8"))
    document = documents.Document.from_file(path)
    assert document.eol == "\r\n"
    assert document.text == "?факт(1).\n\n?факт(2).\n", ascii(document.text)
    document.save()
    assert path.read_bytes() == "?факт(1).\r\n\r\n?факт(2).\r\n".encode("utf-8")
    print("ok: a line separator a file carries is folded into a newline")


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


def test_short_path_keeps_the_place_and_drops_the_prefix() -> None:
    """The status bar shows where a file is, not the whole of `C:\\Users\\…`."""
    import os

    plain = os.path.join("examples", "lesson_01.pld")
    assert documents.short_path(plain) == plain, "two parts are already short"
    assert documents.short_path("файл.pld") == "файл.pld"
    deep = os.path.join("C:\\", "Users", "vasla", "projects", "examples", "lessons", "lesson_04.pld")
    assert documents.short_path(deep) == os.path.join("…", "lessons", "lesson_04.pld")
    assert documents.short_path(deep, parts=1) == os.path.join("…", "lesson_04.pld")
    print("ok: a long path in the status bar keeps its last two parts")


def test_the_session_records_round_trip() -> None:
    """task_29: what a tab keeps between runs, and what it refuses to keep."""
    records = [
        documents.TabRecord(path="C:/пример.pld", name="пример.pld"),
        documents.TabRecord(name="Без имени 2", text="факт(1).\n?факт(1).\n", modified=True),
    ]
    lines = documents.encode_tabs(records)
    assert len(lines) == 2, "one entry per tab: the file has to stay readable"
    assert lines[0].startswith("{"), lines[0]
    assert documents.decode_tabs(lines) == records

    # A text with separators inside it survives — the tabs and the quotes of a
    # program included: the record is JSON, so nothing of the text is a field.
    text = "а\tб\nв\\г\nфакт(\"ц\").\n"
    one = [documents.TabRecord(name="Без имени", text=text, modified=True)]
    assert documents.decode_tabs(documents.encode_tabs(one))[0].text == text

    # A file is remembered by its path and no text at all: the next run reads the
    # file, so a change the user refused to save is not resurrected.  The
    # «unsaved» flag is kept for an *untitled* tab only (task_49): a file tab comes
    # back as the file on disk, so the flag would be a promise nothing can keep.
    kept, dropped = documents.session_records(
        [("C:/a.pld", "a.pld", "x" * 1000, True), ("", "Без имени", "я" * 10, True)]
    )
    assert dropped == 0
    assert kept[0] == documents.TabRecord(path="C:/a.pld", name="a.pld")
    assert kept[0].text == "" and kept[0].untitled is False
    assert kept[0].modified is False, "a file tab is clean: it is read from disk"
    assert kept[1].untitled is True and kept[1].text == "я" * 10
    assert kept[1].modified is True, "a tab the user changed is still unsaved work"
    untouched, _ = documents.session_records([("", "Без имени", "пример.\n", False)])
    assert untouched[0].modified is False, "a tab nobody edited comes back clean"
    print("ok: a session record round-trips, and a file is not stored as text")


def test_a_record_of_the_tab_separated_shape_still_reads() -> None:
    """task_29's three fields are read as they were written (task_49).

    That shape had no flag, and an untitled tab of those days was restored as
    unsaved work — which is what it meant then, so that is what it means here.  A
    file line is clean either way: its text comes from disk.
    """
    older = ["C:/a.pld\ta.pld\t", "\tБез имени 2\tфакт(1).\n\tс табом"]
    read = documents.decode_tabs(older)
    assert len(read) == 2, read
    assert read[0] == documents.TabRecord(path="C:/a.pld", name="a.pld")
    assert read[0].modified is False
    assert read[1].untitled is True
    assert read[1].text == "факт(1).\n\tс табом", ascii(read[1].text)
    assert read[1].modified is True, "that shape meant «unsaved work»"
    print("ok: a tab-separated record of task_29 is still read, tab in the text and all")


def test_the_session_budget_drops_whole_tabs_and_reports_them() -> None:
    """A buffer that does not fit goes entirely: half a text is worse than none.

    The budget is measured per buffer (task_108), not per session: it is the size
    above which closing the window has to ask about a tab, and one big scratch
    buffer must not cost the small one that stands next to it.
    """
    tabs = [
        ("C:/a.pld", "a.pld", "x" * 100, False),
        ("", "первый", "я" * 80, True),
        ("", "второй", "я" * 80, True),
        ("", "огромный", "я" * 120, True),
        ("", "пустой", "   \n", False),
    ]
    kept, dropped = documents.session_records(tabs, budget=100)
    assert [record.name for record in kept] == ["a.pld", "первый", "второй"], kept
    assert dropped == 1, "«огромный» did not fit and has to be counted"

    # A file's text is never stored, so its size is nobody's business.
    assert documents.session_records(tabs, budget=1000)[1] == 0
    empty, dropped = documents.session_records([("", "Без имени", "\n\n", False)], budget=10)
    assert empty == [] and dropped == 0
    print("ok: the budget drops whole buffers, counts them, and skips placeholders")


def test_a_session_that_cannot_be_read_costs_nothing() -> None:
    """A hand-edited file may hold rubbish; the start must survive it."""
    assert documents.decode_tabs([]) == []
    assert documents.decode_tabs(None) == []
    assert documents.decode_tabs(["", "без разделителей", "один\tразделитель"]) == []
    assert documents.decode_tabs(["{ не JSON", "{} мусор после объекта"]) == []
    good = "C:/a.pld\ta.pld\t"
    assert len(documents.decode_tabs(["мусор", good])) == 1
    assert documents.decode_tabs(['{"name": "Без имени"}']) == [
        documents.TabRecord(name="Без имени")
    ], "a JSON record with fields missing is still a tab"
    print("ok: a broken session line is dropped, and the rest still reads")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="prologd_documents_") as name:
        directory = pathlib.Path(name)
        test_line_endings_are_detected_from_the_first_break()
        test_line_endings_are_written_back()
        test_a_file_keeps_its_line_ending_and_its_encoding(directory)
        test_a_byte_order_mark_is_dropped(directory)
        test_a_line_separator_becomes_a_plain_newline(directory)
        test_text_that_is_not_utf8_is_reported_not_replaced(directory)
        test_saving_without_a_name_is_refused()
        test_save_as_moves_the_buffer_to_the_new_file(directory)
        test_untitled_names_reuse_a_freed_number()
        test_titles_carry_the_modified_marker()
        test_short_path_keeps_the_place_and_drops_the_prefix()
        test_the_recent_list_is_ordered_bounded_and_pruned(directory)
        test_the_session_records_round_trip()
        test_the_session_budget_drops_whole_tabs_and_reports_them()
        test_a_session_that_cannot_be_read_costs_nothing()
    print("all document checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
