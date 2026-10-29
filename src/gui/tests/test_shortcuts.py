"""Headless checks of the layout-independent insertions (task_31).

    python src/gui/tests/test_shortcuts.py

The table, the mapping and the cheat sheet are Qt-free, and most of this file is
too.  Two groups need more than that:

* **the layouts** — where a symbol sits on a real keyboard is asked of the
  keyboard (`VkKeyScanExW` + `MapVirtualKeyW`, Windows-only), because that is the
  one thing that cannot be reasoned about: `?` and `:` are on other physical keys
  in ЙЦУКЕН than in the US layout, and a symbol that was *believed* to coincide
  but does not would be discovered by the user rather than here.  This is the
  automatic part of the manual checklist the task asks for.
* **the editor** — that the caret ends up between `-` and `.` is a property of
  the widget, not of the table, so the last group posts real key events to a real
  `CodeEditor` offscreen (skipped when PySide6 is missing).
"""

from __future__ import annotations

import ctypes
import os
import pathlib
import sys

# Set before PySide6 is imported (inside the editor group below), so the widget
# never tries to open a window the test machine does not have.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import actions  # noqa: E402
from prologd_gui.shortcuts import (  # noqa: E402
    MACOS_SCAN_CODES,
    Shortcuts,
    X11_KEYCODE_OFFSET,
    to_windows_scan_code,
)

#: Characters whose position in a layout is deliberately *not* a chord of its row,
#: with the reason.  Every other symbol must be reachable in every layout that
#: has it — that is the whole point of the feature.
UNREACHABLE_IN_LAYOUT: dict[str, dict[str, str]] = {
    "/": {
        "ru": "в русской раскладке `/` стоит на Shift+\\, а Ctrl+Shift+\\ — "
        "«Объединить редакторы» (решение пользователя: объединение остаётся)"
    },
    '"': {
        "ru": "в русской раскладке `\"` стоит на Shift+2; строку можно добавить "
        "в таблицу — она данные (`Ctrl+Shift+'` и есть строка)"
    },
}


# -- the table -------------------------------------------------------------
def test_every_chord_inserts_its_text() -> None:
    table = Shortcuts.default()
    for entry in table:
        for chord in entry.chords:
            for shift in (False, True):
                if chord.shift is not None and shift != chord.shift:
                    # A key that carries two inserts: the other `Shift` state
                    # belongs to the other entry and is checked there.
                    continue
                insert = table.insert_for(chord.scan, shift)
                assert insert is not None, f"{chord.label} did not match"
                assert insert.text == entry.text, (chord.label, insert.text)
                assert insert.start == insert.end == entry.caret, (chord.label, insert)

    # A key nobody bound must fall through to the editor untouched (`Ctrl+C`,
    # `Ctrl+Z`, `Ctrl+W`: every one of them types nothing here).
    for scan in (0x2E, 0x2C, 0x11, 0x1E, 0x39):
        assert table.insert_for(scan, False) is None, hex(scan)
        assert table.insert_for(scan, True) is None, hex(scan)
    print(f"ok: {len(table)} rows and {len(table.keys())} chords insert what the table says")


def test_shift_decides_where_a_key_carries_two_inserts() -> None:
    table = Shortcuts.default()
    for scan, plain, shifted in (
        (0x0D, "РАВНО(,)", "СЛОЖЕНИЕ(,,)"),
        (0x0C, "-", "_"),
        (0x28, "''", '""'),
    ):
        assert table.find(scan, False).text == plain, hex(scan)
        assert table.find(scan, True).text == shifted, hex(scan)

    # `;` and `6` are one insert: the English `:` is `Ctrl+;` and the Russian one
    # `Ctrl+Shift+6`, and both must do the same thing.
    for scan in (0x27, 0x07):
        assert table.find(scan, False).text == ":-."
        assert table.find(scan, True).text == ":-."
    for scan in (0x0A, 0x1A, 0x04, 0x08, 0x09, 0x02):
        assert table.find(scan, False) is table.find(scan, True), hex(scan)
    print("ok: Shift decides the insert where a key carries two, and is ignored where it does not")


def test_a_key_is_read_in_the_windows_numbering_whatever_the_platform() -> None:
    """The table is written in Windows scan codes, so every platform converts.

    This is the bug of part 224, and the numbers are the bug: X11 numbers `x` as
    53 and Windows numbers 53 as `/`, so the editor matched `Ctrl+X` against `/`
    and inserted a slash instead of cutting.  `e` is 26 on X11 and 26 is `[` on
    Windows, which is why `Ctrl+E` inserted `[]`.  The conversion is what the
    fix is; the two pairs below are the report, kept as a check.
    """
    table = Shortcuts.default()

    # X11: the keycode is the scan code plus 8.
    assert X11_KEYCODE_OFFSET == 8
    assert to_windows_scan_code(53, "xcb") == 0x2D, "x is not 45"
    assert to_windows_scan_code(26, "xcb") == 0x12, "e is not 18"
    assert to_windows_scan_code(61, "xcb") == 0x35, "/ is not 53"
    for code, shift in ((53, False), (26, False)):
        assert table.insert_for(to_windows_scan_code(code, "xcb"), shift) is None, (
            f"key {code} still inserts something"
        )
    slash = table.insert_for(to_windows_scan_code(61, "xcb"), False)
    assert slash is not None and slash.text == "/", slash

    # Windows hands the scan code over as it is.
    for chord_scan in (0x27, 0x0A, 0x35, 0x28):
        assert to_windows_scan_code(chord_scan, "windows") == chord_scan

    # The Mac numbers its own way, and every chord of the table must have an
    # answer there: a chord missing from the map would silently do nothing on a
    # Mac, which is a failure nobody would report as a bug in the map.
    assert to_windows_scan_code(7, "cocoa") is None, "x is not a chord on the Mac"
    assert to_windows_scan_code(44, "cocoa") == 0x35, "/ is 44 on the Mac"
    chords = {chord.scan for entry in table for chord in entry.chords}
    assert chords <= set(MACOS_SCAN_CODES.values()), (
        "no Mac key for: " + ", ".join(hex(s) for s in sorted(chords - set(MACOS_SCAN_CODES.values())))
    )

    # An unknown platform fails closed: no insert at all rather than a wrong one.
    assert to_windows_scan_code(0x27, "somefutureplatform") is None
    # The offscreen platform is the tests' own, and speaks Windows scan codes.
    assert to_windows_scan_code(0x27, "offscreen") == 0x27
    print("ok: a physical key is read in the Windows numbering on every platform")


def test_no_two_entries_share_a_key() -> None:
    table = Shortcuts.default()
    exact: set[tuple[int, bool]] = set()
    any_shift: set[int] = set()
    for entry in table:
        for chord in entry.chords:
            if chord.shift is None:
                assert chord.scan not in any_shift, f"0x{chord.scan:02X} twice"
                any_shift.add(chord.scan)
            else:
                pair = (chord.scan, bool(chord.shift))
                assert pair not in exact, f"0x{chord.scan:02X}/{chord.shift} twice"
                exact.add(pair)

    # `find` prefers an exact `(scan, shift)` over an any-shift chord, so a key
    # that appears in both would answer differently depending on `Shift` — the
    # kind of table that is impossible to explain in the cheat sheet.
    shared = any_shift & {scan for scan, _ in exact}
    assert not shared, [hex(scan) for scan in shared]

    labels = table.keys()
    assert len(labels) == len(set(labels)), sorted(labels)
    print("ok: no physical key is bound twice")


def test_the_table_does_not_steal_a_window_command() -> None:
    """The table takes `Ctrl`+punctuation, so the window must not want the same.

    The zoom moved to the keypad (`Ctrl+Num++`, `Ctrl+Num+-`, `Ctrl+0`) for
    exactly this reason: `Ctrl+=`/`Ctrl+-` are inserts now, and a shortcut is
    resolved by Qt *before* the editor sees the key.
    """
    bound = {
        sequence
        for action in actions.ACTIONS
        for sequence in (action.shortcuts or ())
    }
    taken = sorted(set(Shortcuts.default().keys()) & bound)
    assert not taken, f"the window already uses {taken}"
    print(f"ok: none of the {len(bound)} window shortcuts is an insert chord")


def test_a_selection_is_wrapped_where_the_table_says_so() -> None:
    table = Shortcuts.default()
    for scan, shift, text, start, end in (
        (0x0A, False, "(Х)", 1, 2),
        (0x1A, False, "[Х]", 1, 2),
        (0x04, False, "#Х#", 1, 2),
        (0x35, True, "?Х", 1, 2),
    ):
        insert = table.insert_for(scan, shift, "Х")
        assert (insert.text, insert.start, insert.end) == (text, start, end), (text, insert)

    # Everything else replaces the selection, as typing the character would.
    for scan, shift in ((0x27, False), (0x0D, False), (0x34, True), (0x0C, True)):
        insert = table.insert_for(scan, shift, "Х")
        plain = table.find(scan, shift)
        assert insert.text == plain.text, (scan, insert.text)
        assert insert.start == insert.end == plain.caret, (scan, insert)

    # A bracket entry with nothing selected is just its two characters.
    insert = table.insert_for(0x0A, False)
    assert (insert.text, insert.start) == ("()", 1)
    print("ok: a selection is wrapped by the bracket-like entries and replaced by the rest")


def test_the_stored_table_round_trips_and_survives_junk() -> None:
    table = Shortcuts.default()
    again = Shortcuts.from_json(table.to_json())
    assert list(again) == list(table)
    assert again.to_json() == table.to_json()
    assert again.keys() == table.keys()

    for junk in ("", None, "не json", "{}", "[]", "[1, 2]", '[{"insert": 5}]',
                 '[{"insert": "|-", "chords": []}]'):
        assert list(Shortcuts.from_json(junk)) == list(table), repr(junk)

    # A hand-written table is honoured — that is why it is data at all.
    edited = '[{"insert": "|€", "chords": [{"scan": 26, "shift": null, "key": "["}]}]'
    edited_table = Shortcuts.from_json(edited)
    assert len(edited_table) == 1
    assert edited_table.insert_for(0x1A, False).text == "€"
    assert edited_table.insert_for(0x1A, False).start == 0
    print("ok: the table round-trips through JSON, junk means the built-in table")


def test_the_cheat_sheet_lists_the_active_table() -> None:
    table = Shortcuts.default()
    lines = table.cheatsheet()
    text = "\n".join(lines)
    for chord in table.keys():
        assert chord in text, chord
    for entry in table:
        assert entry.insert in text, entry.insert
    assert "выделение" in text, "the wrapping hint is missing"
    assert len(lines) == len(table) + 3, len(lines)
    print("ok: the cheat sheet lists every chord of the table it was built from")


# -- the real layouts ------------------------------------------------------
def load_layout(name: str) -> int:
    """A keyboard layout handle by its Windows id (`00000419` — Russian)."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.LoadKeyboardLayoutW.restype = ctypes.c_void_p
    handle = user32.LoadKeyboardLayoutW(name, 1)
    assert handle, f"layout {name} is not installed"
    return handle


def key_scan(char: str, layout: int) -> tuple[int, bool] | None:
    """Where `char` sits in a layout: `(scan code, whether Shift is needed)`.

    `VkKeyScanExW` answers what a real key press would produce, high byte and
    all; `MapVirtualKeyW` turns its virtual key into the scan code the editor
    matches on.
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.VkKeyScanExW.restype = ctypes.c_short
    user32.MapVirtualKeyW.restype = ctypes.c_uint
    packed = user32.VkKeyScanExW(ctypes.c_wchar(char), ctypes.c_void_p(layout))
    if packed == -1:
        return None
    virtual_key = packed & 0xFF
    state = (packed >> 8) & 0xFF
    assert not state & 0b110, f"{char!r} needs Ctrl or Alt in this layout"
    return user32.MapVirtualKeyW(virtual_key, 0), bool(state & 1)


def test_every_symbol_sits_where_the_table_says_in_both_layouts() -> None:
    if sys.platform != "win32":
        print("skipped: the layout check asks Windows for the real layouts")
        return
    table = Shortcuts.default()
    layouts = (("us", load_layout("00000409")), ("ru", load_layout("00000419")))
    checked = 0
    for entry in table:
        for name, layout in layouts:
            where = key_scan(entry.char, layout)
            if where is None:
                # The layout simply has no such character (`[`, `#`, `'` — in
                # ЙЦУКЕН those keys carry letters).  The chord still works: it is
                # the *physical* key that is matched.
                continue
            if name in UNREACHABLE_IN_LAYOUT.get(entry.char, {}):
                continue
            scan, shift = where
            assert table.find(scan, shift) is entry, (
                f"{entry.char!r} is on 0x{scan:02X} in the {name} layout, "
                f"which the table does not bind"
            )
            checked += 1
        for chord in entry.chords:
            if chord.layout != "ru":
                continue
            where = key_scan(entry.char, layouts[1][1])
            assert where is not None, f"{entry.char!r} is not in the Russian layout at all"
            assert where[0] == chord.scan, f"{chord.label}: 0x{where[0]:02X} expected"
            assert chord.shift is None or chord.shift == where[1], chord.label
    assert checked >= 2 * len(table) - 12, checked
    print(f"ok: {checked} symbol positions agree with the US and the Russian layout")
    for char, reasons in UNREACHABLE_IN_LAYOUT.items():
        for name, reason in reasons.items():
            print(f"   (известное исключение: {char!r} в {name} — {reason})")


# -- the editor ------------------------------------------------------------
def make_editor(text: str = ""):
    from prologd_gui.editor import CodeEditor

    editor = CodeEditor()
    editor.set_shortcuts(Shortcuts.default())
    editor.setPlainText(text)
    return editor


def press(editor, scan: int, shift: bool = False, *, alt: bool = False, control: bool = True) -> bool:
    """Posts a key press the way the keyboard would; returns whether it was taken.

    `QKeyEvent` has two constructors and only the second one carries a native scan
    code — the offscreen platform has no keyboard, so a scan code has to be handed
    in explicitly.  The virtual key and the native modifiers are left at zero:
    nothing in the window reads them, and a test that filled them would be
    pretending to know what Windows would have sent.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    modifiers = Qt.KeyboardModifier.NoModifier
    if control:
        modifiers |= Qt.KeyboardModifier.ControlModifier
    if shift:
        modifiers |= Qt.KeyboardModifier.ShiftModifier
    if alt:
        modifiers |= Qt.KeyboardModifier.AltModifier
    # The key value is deliberately meaningless: the handler matches the *scan
    # code*, which is what the layout does not change.
    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_unknown, modifiers, scan, 0, 0
    )
    QApplication.sendEvent(editor, event)
    return event.isAccepted()


def test_the_editor_inserts_where_the_caret_should_be() -> None:
    editor = make_editor()
    assert press(editor, 0x27), "Ctrl+; was not taken"
    assert editor.toPlainText() == ":-."
    assert editor.textCursor().position() == 2, "the caret is not between `-` and `.`"

    editor.undo()
    assert editor.toPlainText() == "", "one Ctrl+Z did not undo the insert"

    for scan, shift, text, caret in (
        (0x0A, False, "()", 1),
        (0x1A, False, "[]", 1),
        (0x04, False, "#", 1),
        (0x35, True, "?", 1),
        (0x0D, False, "РАВНО(,)", 6),
        (0x34, True, "БОЛЬШЕ(,)", 7),
        (0x33, True, "МЕНЬШЕ(,)", 7),
        (0x0D, True, "СЛОЖЕНИЕ(,,)", 9),
        (0x09, False, "УМНОЖЕНИЕ(,,)", 10),
        (0x35, False, "/", 1),
        (0x0C, False, "-", 1),
        (0x0C, True, "_", 1),
        (0x02, False, "!", 1),
        (0x28, False, "''", 1),
        (0x28, True, '""', 1),
    ):
        editor.setPlainText("")
        assert press(editor, scan, shift), hex(scan)
        assert editor.toPlainText() == text, (hex(scan), editor.toPlainText())
        assert editor.textCursor().position() == caret, (hex(scan), text)
        editor.undo()
        assert editor.toPlainText() == "", hex(scan)

    # The same chord with the Russian key: `Ctrl+Shift+6` is `Ctrl+6` here, and
    # both are the `:` the English layout has on `Ctrl+;`.
    for scan, shift in ((0x07, False), (0x07, True), (0x08, False), (0x08, True)):
        editor.setPlainText("")
        assert press(editor, scan, shift), hex(scan)
        assert editor.toPlainText() in (":-.", "?"), (hex(scan), editor.toPlainText())
    print("ok: the editor inserts every chord with the caret where the table says")


def test_a_selection_is_wrapped_and_one_ctrl_z_undoes_it() -> None:
    from PySide6.QtGui import QTextCursor

    editor = make_editor("Х")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    editor.setTextCursor(cursor)

    assert press(editor, 0x0A)
    assert editor.toPlainText() == "(Х)"
    assert editor.textCursor().selectedText() == "Х", "the wrapped text is not kept selected"

    # The wrapped text stays selected, so a second wrapping goes around it: the
    # brackets it already has are outside the selection and stay where they are.
    press(editor, 0x04)
    assert editor.toPlainText() == "(#Х#)"

    editor.undo()
    assert editor.toPlainText() == "(Х)", "one Ctrl+Z did not undo the whole insert"
    editor.undo()
    assert editor.toPlainText() == "Х", "the first insert was not one undo step either"
    print("ok: a selection is wrapped, kept selected, and wrapped again in one undo step")


def test_the_editor_reads_x11_keycodes_on_a_linux_desktop() -> None:
    """The same bug, seen through the editor: `Ctrl+X` must not insert `/`.

    The suite runs on `offscreen`, which speaks Windows scan codes; a Linux
    desktop answers `xcb` and numbers the keys 8 higher.  The platform name is
    what `_insert_shortcut` asks Qt for, so it is the one thing replaced here —
    the events carry the *X11 keycodes* a real keyboard would send.
    """
    import types

    from prologd_gui import editor as editor_module

    saved = editor_module.QGuiApplication
    editor_module.QGuiApplication = types.SimpleNamespace(platformName=lambda: "xcb")
    try:
        editor = make_editor()
        # 53 is `x` on X11 and `/` in the Windows numbering: it must do nothing,
        # so the window's own «Вырезать» handles the key.
        assert not press(editor, 53), "Ctrl+X was swallowed again"
        assert editor.toPlainText() == "", "Ctrl+X inserted something"
        # 26 is `e` on X11 and `[` in the Windows numbering.
        assert not press(editor, 26), "Ctrl+E was swallowed again"
        assert editor.toPlainText() == "", "Ctrl+E inserted something"
        # 61 is where `/` really stands, and 61 - 8 is the `0x35` of the table.
        assert press(editor, 61), "the `/` key stopped working"
        assert editor.toPlainText() == "/", editor.toPlainText()
        # A key the table does not know is left alone as well.
        assert not press(editor, 24), "Ctrl+Q inserted something"  # `q` on X11
    finally:
        editor_module.QGuiApplication = saved
    print("ok: on X11 the editor converts keycodes and leaves Ctrl+X and Ctrl+E alone")


def test_the_modifiers_the_feature_must_not_swallow() -> None:
    editor = make_editor("х")
    for shift in (False, True):
        assert not press(editor, 0x27, shift, alt=True, control=False), "Alt+; was swallowed"
        assert not press(editor, 0x27, shift, alt=True), "Ctrl+Alt+; was swallowed"
        assert not press(editor, 0x27, shift, control=False), "; was swallowed"
    assert editor.toPlainText() == "х", "something was inserted after all"
    print("ok: Alt, AltGr (Ctrl+Alt) and a bare key are left to the window")


def main(argv: list[str]) -> int:
    test_every_chord_inserts_its_text()
    test_shift_decides_where_a_key_carries_two_inserts()
    test_a_key_is_read_in_the_windows_numbering_whatever_the_platform()
    test_no_two_entries_share_a_key()
    test_the_table_does_not_steal_a_window_command()
    test_a_selection_is_wrapped_where_the_table_says_so()
    test_the_stored_table_round_trips_and_survives_junk()
    test_the_cheat_sheet_lists_the_active_table()
    test_every_symbol_sits_where_the_table_says_in_both_layouts()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed, the editor group was not run")
        return 0
    application = QApplication(sys.argv[:1])
    test_the_editor_inserts_where_the_caret_should_be()
    test_a_selection_is_wrapped_and_one_ctrl_z_undoes_it()
    test_the_editor_reads_x11_keycodes_on_a_linux_desktop()
    test_the_modifiers_the_feature_must_not_swallow()
    del application
    print("all shortcut checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
