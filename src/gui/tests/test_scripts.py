"""«Скрипты → Сконвертировать картинку…»: the fields, the arguments, the answer.

The window's part (opening the dialog and a tab) needs a whole `MainWindow`, so what
is checked here is the seam that can be checked without one: the dialog turns its
fields into the tool's command line, the tool turns a picture into facts, and the
menu entry that starts it all is where it should be — in a menu of its own, just
before «Справка» (ADR-036).

    QT_QPA_PLATFORM=offscreen PYTHONUTF8=1 python src/gui/tests/test_scripts.py
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from prologd_gui import actions, engines, scriptdialog, scripts  # noqa: E402


def draw_picture(path: pathlib.Path) -> None:
    """A picture the converter can chew: a red square in the middle of a white field."""
    size = 32
    image = QImage(size, size, QImage.Format.Format_RGBA8888)
    image.fill(QColor(255, 255, 255))
    for y in range(8, 24):
        for x in range(8, 24):
            image.setPixelColor(x, y, QColor(200, 30, 30))
    assert image.save(str(path)), path


def draw_tall_picture(path: pathlib.Path) -> None:
    """32x48 with one cell of red in the top left: what a grid of 2x3 makes of it.

    A picture that is not square is the whole point of the grid change — it proves the
    columns and rows are counted separately, that the canvas takes its sides in the
    order `ХОЛСТ(Высота, Ширина)` wants, and that empty cells make no facts.
    """
    image = QImage(32, 48, QImage.Format.Format_RGBA8888)
    image.fill(QColor(255, 255, 255))
    for y in range(0, 16):
        for x in range(0, 16):
            image.setPixelColor(x, y, QColor(200, 30, 30))
    assert image.save(str(path)), path


def test_the_menu_holds_the_converter_before_the_help() -> None:
    titles = [title for title, _entries in actions.MENUS]
    assert "Скрипты" in titles, titles
    assert titles.index("Скрипты") + 1 == titles.index("Справка"), titles
    entries = dict(actions.MENUS)["Скрипты"]
    # The picture converter, and then the submenu of the conversions (task_99).
    assert entries == ("script_image", actions.SEPARATOR, actions.NAMES_SUBMENU), entries
    action = actions.BY_KEY["script_image"]
    assert action.title == "Сконвертировать картинку…", action.title
    conversions = [actions.BY_KEY[key] for key in actions.NAMES_CONVERSIONS]
    assert [entry.title for entry in conversions] == ["Имена: PLD в ISO", "Имена: ISO в PLD"], (
        conversions
    )
    assert all(entry.needs == engines.FORMAT for entry in conversions), conversions
    # The other axis: the language of the built-in names, with the signs each of
    # them has a spelling for (task_101).
    dialect = [actions.BY_KEY[key] for key in actions.DIALECT_CONVERSIONS]
    assert [entry.title for entry in dialect] == [
        "Диалект: Русский в Английский",
        "Диалект: Английский в Русский",
    ], dialect
    assert all(entry.needs == engines.FORMAT for entry in dialect), dialect
    assert actions.CONVERSIONS == actions.NAMES_CONVERSIONS + (
        actions.SEPARATOR,
    ) + actions.DIALECT_CONVERSIONS
    print("ok: «Скрипты» стоит перед «Справкой» и держит конвертер и перевод имён")


def test_the_dialog_turns_its_fields_into_the_tool_s_arguments(directory: pathlib.Path) -> None:
    picture = directory / "мышь.png"
    draw_picture(picture)
    dialog = scriptdialog.ImageToPldDialog()
    try:
        # Nothing chosen yet: no picture, no name — and OK says so.
        assert dialog.arguments()  # the command line is built all the same
        box = dialog.findChild(scriptdialog.QDialogButtonBox)
        assert box is not None, "no buttons"
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is False

        dialog.set_image(str(picture))
        # The name comes from the file, ready to be an atom of the facts.
        assert dialog.name() == "мышь", dialog.name()
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is True
        arguments = dialog.arguments()
        assert arguments[:2] == ["--image", f"мышь={picture}"], arguments
        assert "--cell" in arguments and "--canvas-cell" in arguments, arguments
        assert arguments[arguments.index("--canvas-cell") + 1] == "auto", arguments
        # The box starts unticked, so the page is painted and no colour is named.
        assert "--keep-background" in arguments, arguments
        assert "--background" not in arguments, arguments
        # The grid is not a field any more: it follows from the picture and the cell,
        # and the dialog says what it comes to.
        assert dialog._plan.text() == "Сетка 2×2 клеток, холст 64×64 точек", dialog._plan.text()
        dialog._cell.setValue(8)
        assert "Сетка 4×4" in dialog._plan.text(), dialog._plan.text()
        assert dialog.arguments()[dialog.arguments().index("--cell") + 1] == "8"
        dialog._cell.setValue(16)

        # «Клетка холста» is a number or «авто», and the minimum is what draws «авто».
        assert dialog._canvas_cell.specialValueText() == "авто"
        assert dialog._canvas_cell.value() == 0
        dialog._canvas_cell.setValue(4)
        assert dialog.arguments()[dialog.arguments().index("--canvas-cell") + 1] == "4"
        assert dialog._plan.text() == "Сетка 2×2 клеток, холст 8×8 точек", dialog._plan.text()
        # … and a canvas below the engine's 16 dots is refused before anything runs.
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is False
        assert "вне пределов" in dialog._hint.text(), dialog._hint.text()
        dialog._canvas_cell.setValue(0)
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is True

        # The switch: the page is painted by default, and the three fields that answer
        # «what is the background» grey out when there is no background to leave out.
        drop = dialog._drop_background
        assert drop.isChecked() is False
        assert dialog._background.isEnabled() is False
        assert dialog._tolerance.isEnabled() is False
        assert dialog._coverage.isEnabled() is False
        assert "--keep-background" in dialog.arguments(), dialog.arguments()
        assert "--background" not in dialog.arguments(), dialog.arguments()
        drop.setChecked(True)
        assert dialog._background.isEnabled() is True
        assert dialog._tolerance.isEnabled() is True
        assert dialog._coverage.isEnabled() is True
        assert dialog.arguments()[dialog.arguments().index("--background") + 1] == "auto"
        assert "--keep-background" not in dialog.arguments(), dialog.arguments()

        # A name that is not an atom is refused, and said why.
        dialog._name.setText("мышь 1")
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is False
        assert "имени допустимы" in dialog._hint.text(), dialog._hint.text()

        # A picture that is not there is refused too.
        dialog._name.setText("мышь")
        dialog._image.setText(str(directory / "нет.png"))
        assert box.button(scriptdialog.QDialogButtonBox.StandardButton.Ok).isEnabled() is False
        assert "нет файла" in dialog._hint.text(), dialog._hint.text()
    finally:
        dialog.deleteLater()
    print("ok: поля диалога дают командную строку конвертера, а плохие — отказ")


def test_every_field_explains_itself() -> None:
    """Hovering a field says what it does — the reader should not need the manual."""
    dialog = scriptdialog.ImageToPldDialog()
    try:
        fields = {
            "Картинка:": dialog._image,
            "Имя:": dialog._name,
            "Клетка картинки:": dialog._cell,
            "Клетка холста:": dialog._canvas_cell,
            "Цветов:": dialog._colors,
            "Порог фона:": dialog._tolerance,
            "Доля «чернил»:": dialog._coverage,
            "Фон:": dialog._background,
        }
        labels = {label.text(): label for label in dialog.findChildren(scriptdialog.QLabel)}
        for caption, field in fields.items():
            tip = field.toolTip()
            assert len(tip) > 20, (caption, tip)
            # The label explains itself too: it is what the eye lands on first.
            assert caption in labels, (caption, sorted(labels))
            assert labels[caption].toolTip() == tip, caption
        # And the words are about this field, not «введите значение».
        assert "пикселей картинки" in fields["Клетка картинки:"].toolTip()
        assert "авто" in fields["Клетка холста:"].toolTip()
        assert "auto" in fields["Фон:"].toolTip(), fields["Фон:"].toolTip()
        assert "подчёркивание" in fields["Имя:"].toolTip(), fields["Имя:"].toolTip()
        # The checkbox has no caption beside it, so its words are on itself.
        tip = dialog._drop_background.toolTip()
        assert "ложится на то, что нарисовано раньше" in tip, tip
    finally:
        dialog.deleteLater()
    print("ok: каждое поле конвертера объясняет себя подсказкой")


def test_the_converter_answers_with_a_program(directory: pathlib.Path) -> None:
    picture = directory / "столбик.png"
    draw_tall_picture(picture)
    arguments = scripts.image_arguments(str(picture), "столбик", cell=16, colors=4,
                                        tolerance=32, coverage=0.5, background="auto")
    text = scripts.run(arguments)
    lines = [line for line in text.splitlines() if line.strip()]
    assert lines, text
    assert lines[0].startswith("%"), lines[0]
    # 32x48 at a cell of 16 is 2x3 cells, and only one of them has ink: the grid
    # follows the picture, so the shape of the answer is the shape of the picture.
    assert "% столбик: 2x3 клеток по 16 px" in text, text[:400]
    facts = [line for line in lines if line.startswith("картинка(")]
    assert len(facts) == 1, facts
    assert facts[0].startswith("картинка(столбик, 0, 0, 0, 0, "), facts[0]
    assert facts[0].endswith(")."), facts[0]
    # A red square stays red: the colour is the last number of the fact.
    value = int(facts[0].rstrip(".)").rsplit(",", 1)[1].strip())
    assert (value >> 16) > 120 and ((value >> 8) & 0xFF) < 90, value
    # The answer is a program that draws itself, not a pile of facts: a canvas the
    # size of the picture, a predicate that turns cells into rectangles, and a
    # question that calls it — «Запустить» straight after the conversion works.
    # `ХОЛСТ` takes the height first: 3 cells of 32 dots, then 2.
    assert ":- ХОЛСТ(96, 64)." in lines, lines[:8]
    assert lines.index(":- ХОЛСТ(96, 64).") < lines.index(facts[0]), lines[:8]
    assert "% Холст: 2x3 клеток по 32 точек." in lines, lines[:8]
    assert any(line.startswith("нарисовать_картинку(Имя):-") for line in lines), lines[-6:]
    assert lines[-1] == "?нарисовать_картинку(столбик).", lines[-3:]
    # The file form stays facts only: `maze.images.pld` is imported, and a directive
    # or a question would act on the program that imports it (ADR-034).
    target = directory / "только-факты.pld"
    written = scripts.run([*arguments, "--out", str(target)])
    assert "facts" in written, written
    saved = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert saved[:1] and not saved[0].startswith((":-", "?")), saved[:2]
    assert not any(line.startswith((":-", "?")) for line in saved), saved[-3:]
    saved_facts = [line for line in saved if line.startswith("картинка(")]
    assert saved_facts == facts, saved_facts[:2]
    print(f"ok: конвертер вернул готовую программу ({len(facts)} фактов, ХОЛСТ и вопрос)")


def test_the_dialog_predicts_the_canvas_the_tool_draws(directory: pathlib.Path) -> None:
    """The summary under the form has to be the tool's own arithmetic, not a guess.

    The rule lives twice — the tool works without the window, the dialog must answer
    before anything runs — so the two are compared on the very line the tool prints.
    """
    picture = directory / "прогноз.png"
    draw_tall_picture(picture)
    dialog = scriptdialog.ImageToPldDialog()
    try:
        dialog.set_image(str(picture))
        assert dialog._plan.text() == "Сетка 2×3 клеток, холст 64×96 точек", dialog._plan.text()
        text = scripts.run(dialog.arguments())
    finally:
        dialog.deleteLater()
    canvas = [line for line in text.splitlines() if line.startswith(":- ХОЛСТ(")]
    assert canvas == [":- ХОЛСТ(96, 64)."], canvas
    print("ok: обещание диалога совпало с ХОЛСТ, который напечатал конвертер")


def test_the_program_is_already_soft_formatted(directory: pathlib.Path) -> None:
    """The tab must not look like a reformat away from the house style.

    The drawing clause is broken by hand the way `prologu --format soft` breaks it,
    so formatting the freshly converted tab changes nothing.  A packing change in
    the formatter shows up here instead of in someone's eyes.
    """
    executable = os.environ.get("PROLOGD_TEST_EXE")
    if not executable or not pathlib.Path(executable).is_file():
        print("skipped: PROLOGD_TEST_EXE не задан, формат не проверен")
        return
    picture = directory / "формат.png"
    draw_tall_picture(picture)
    # Two shapes of the drawing clause: the arithmetic one and the plain one a cell
    # of a single dot takes.
    cases = [
        ("клетка 16, клетка холста авто", {"cell": 16}),
        ("клетка 2, клетка холста 1", {"cell": 2, "canvas_cell": 1}),
    ]
    for what, options in cases:
        text = scripts.run(scripts.image_arguments(str(picture), "формат", **options))
        source = directory / "формат.pld"
        source.write_text(text, encoding="utf-8", newline="\n")
        formatted = subprocess.run(
            [executable, "--format", "soft", str(source)], capture_output=True, check=False
        )
        assert formatted.returncode == 0, formatted.stderr.decode("utf-8", "replace")
        answer = formatted.stdout.decode("utf-8").replace("\r\n", "\n")
        assert answer == text, f"{what}: не то, что печатает --format soft"
    print("ok: программа конвертера уже в мягком формате (оба вида рисующего предиката)")


def test_the_converter_survives_the_extremes(directory: pathlib.Path) -> None:
    """The zero division the window showed, and the switch that keeps the page.

    `--coverage 0` asks for «every cell that has any ink», and the first version
    divided by zero on a cell that had none — the window got a traceback in a box.
    `--keep-background` is the checkbox: the page becomes part of the drawing, so an
    opaque picture covers its whole grid instead of only its ink.
    """
    picture = directory / "страница.png"
    draw_tall_picture(picture)
    dropped = scripts.run(scripts.image_arguments(str(picture), "страница", cell=16,
                                                  coverage=0))
    facts = [line for line in dropped.splitlines() if line.startswith("картинка(")]
    # One cell of red and five of white: the white ones are the page, so they go.
    assert len(facts) == 1, facts
    kept = scripts.run(scripts.image_arguments(str(picture), "страница", cell=16,
                                               drop_background=False))
    kept_facts = [line for line in kept.splitlines() if line.startswith("картинка(")]
    assert "фон не отбрасывается" in kept, kept[:300]
    assert len(kept_facts) > len(facts), (len(kept_facts), len(facts))
    # A colour to drop and «keep everything» at once is a contradiction, and the tool
    # says so instead of picking one.
    try:
        scripts.run(["--image", f"страница={picture}",
                     "--keep-background", "--background", "255,255,255"])
    except scripts.ScriptError as error:
        assert "вместе" in str(error), str(error)
    else:
        raise AssertionError("both keys were accepted")
    print("ok: клетка без чернил не делит на ноль, а галочка «Отбрасывать фон» работает")


def test_a_crash_is_one_line_not_a_traceback() -> None:
    """The window has one small box for a failure; a traceback does not fit and says little."""
    noisy = (
        "Traceback (most recent call last):\n"
        '  File "C:\\tools\\image_to_pld.py", line 172, in sample\n'
        "    cells.append((total[0] // ink, total[1] // ink, total[2] // ink))\n"
        "ZeroDivisionError: division by zero\n"
    )
    assert scripts.words(noisy) == "конвертер упал: ZeroDivisionError: division by zero"
    assert scripts.words("--cell 100: 1..64 only") == "--cell 100: 1..64 only"
    assert scripts.words("   ") == ""
    print("ok: падение конвертера приходит одной строкой, отказ — как есть")


def test_the_child_speaks_utf8_even_with_no_python_variables(
    directory: pathlib.Path,
) -> None:
    """The window runs with a bare environment, and the facts are Cyrillic.

    A process without a console prints its pipe with the system ANSI code page
    (cp1252 on this machine), so the first `картинка(` used to end in a
    `UnicodeEncodeError`.  The window sets `PYTHONIOENCODING` for the child and the
    tool names UTF-8 for itself; the check runs with neither `PYTHONUTF8` nor
    `PYTHONIOENCODING` in the base environment, which is exactly what a window
    started from Explorer has.
    """
    picture = directory / "кубик.png"
    draw_tall_picture(picture)
    bare = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    arguments = scripts.image_arguments(str(picture), "кубик")
    text = scripts.run(arguments, base_env=bare)
    assert "картинка(кубик," in text, text[:200]
    # The tool stands on its own as well: run it directly, with the bare environment
    # and no help from `scripts.run` — its own `reconfigure("utf-8")` is what saves
    # a caller that forgets to set the variable.
    direct = subprocess.run(
        [sys.executable, str(scripts.tool_path()), *arguments],
        capture_output=True,
        env=bare,
        check=False,
    )
    assert direct.returncode == 0, direct.stderr.decode("utf-8", "replace")
    assert "картинка(кубик,".encode("utf-8") in direct.stdout, direct.stdout[:200]
    print("ok: кириллица в фактах переживает cp1252 дочернего процесса")


def test_a_broken_call_is_an_error_with_words() -> None:
    missing = pathlib.Path(tempfile.gettempdir()) / "нет-такой-картинки.png"
    arguments = scripts.image_arguments(str(missing), "нет")
    try:
        scripts.run(arguments)
    except scripts.ScriptError as error:
        assert "картинк" in str(error) or "нет" in str(error), str(error)
    else:
        raise AssertionError("a missing picture was accepted")
    # A tool that is not shipped at all is refused before any process starts.
    try:
        scripts.run([], tool=pathlib.Path(tempfile.gettempdir()) / "нет-скрипта.py")
    except scripts.ScriptError as error:
        assert "нет конвертера" in str(error), str(error)
    else:
        raise AssertionError("a missing tool was accepted")
    print("ok: неудачи конвертера приходят словами, а не молчанием")


def main(argv: list[str]) -> int:
    if QApplication is None:  # pragma: no cover
        print("skipped: PySide6 is not installed")
        return 0
    application = QApplication.instance() or QApplication([])
    assert application is not None
    test_the_menu_holds_the_converter_before_the_help()
    with tempfile.TemporaryDirectory(prefix="prologd_scripts_") as folder:
        directory = pathlib.Path(folder)
        test_the_dialog_turns_its_fields_into_the_tool_s_arguments(directory)
        test_every_field_explains_itself()
        test_the_converter_answers_with_a_program(directory)
        test_the_dialog_predicts_the_canvas_the_tool_draws(directory)
        test_the_program_is_already_soft_formatted(directory)
        test_the_converter_survives_the_extremes(directory)
        test_the_child_speaks_utf8_even_with_no_python_variables(directory)
    test_a_crash_is_one_line_not_a_traceback()
    test_a_broken_call_is_an_error_with_words()
    print("all script checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
