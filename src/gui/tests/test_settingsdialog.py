"""Checks of the settings dialog (offscreen, no interpreter, no window).

    python src/gui/tests/test_settingsdialog.py

The dialog is built from `settings.SETTINGS`, so most of what can go wrong is a
row that does not exist, a widget whose value is not read back, or a button that
writes more than it should.  Every check drives the dialog the way the user does
— through its widgets and its buttons — and reads the *store* afterwards, never
the dialog's own idea of what it did.

The three file choosers are replaced (the same rule as everywhere else in this
front-end): a modal `QFileDialog` hangs a headless run instead of failing it.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from prologd_gui import settings as settings_module  # noqa: E402
from prologd_gui.settings import Settings  # noqa: E402


def dialog_for(directory: pathlib.Path, name: str = "gui.ini"):
    """A dialog over a throw-away settings file."""
    from prologd_gui.settingsdialog import SettingsDialog

    return SettingsDialog(Settings(directory / name))


def test_a_page_per_section_and_a_widget_per_row(directory: pathlib.Path) -> None:
    """The dialog *is* the description table — nothing added, nothing forgotten."""
    dialog = dialog_for(directory)
    names = dialog.section_names()
    # The described sections in order, with the two data pages slotted in:
    # «Подсветка» right after «Вид» (it is about the theme), «Вставки» at the end.
    described = list(settings_module.SECTIONS)
    described.insert(described.index("Вид") + 1, settings_module.__dict__.get(
        "SYNTAX_PAGE", "Подсветка"))
    assert names == [*described, settings_module.__dict__.get("INSERTS_PAGE", "Вставки")], names

    widgets = dialog.widgets()
    described = {setting.key for setting in settings_module.SETTINGS}
    assert set(widgets) == described, sorted(described ^ set(widgets))

    # Each row sits on the page its record names.
    from PySide6.QtWidgets import QLabel

    for section in settings_module.SECTIONS:
        assert dialog.show_section(section) is True
        page = dialog._pages.currentWidget()
        labels = {label.text().rstrip(":") for label in page.findChildren(QLabel)}
        for setting in settings_module.SETTINGS:
            if setting.section == section:
                assert setting.label in labels, (section, setting.label)
    print(f"ok: {len(widgets)} rows over {len(dialog.section_names())} pages, from the table alone")


def test_the_syntax_page_lists_every_colour_in_both_themes(directory: pathlib.Path) -> None:
    """«Подсветка» (task_50): each role with its light and dark hex side by side."""
    from prologd_gui import theme

    dialog = dialog_for(directory)
    assert dialog.show_section("Подсветка") is True
    rows = dialog.syntax_rows()
    assert len(rows) == len(theme.SYNTAX_LABELS) == len(theme.Theme.__dataclass_fields__), len(rows)
    # The first row is the comment, in the light palette's and the dark one's hex.
    assert rows[0] == ("Комментарий", theme.LIGHT_SYNTAX.comment, theme.DARK_SYNTAX.comment), rows[0]
    for label, light, dark in rows:
        assert len(light) == 7 and light.startswith("#"), light
        assert len(dark) == 7 and dark.startswith("#"), dark
    labels = [label for label, _, _ in rows]
    assert labels == list(theme.SYNTAX_LABELS.values()), labels
    print(f"ok: {len(rows)} syntax roles, light and dark hex for each")


def test_a_colour_can_be_changed_and_applied(directory: pathlib.Path) -> None:
    """«Подсветка»: clicking a swatch and applying writes the override (task_50)."""
    from prologd_gui import theme

    dialog = dialog_for(directory, "edit.ini")
    dialog.show_section("Подсветка")
    button = dialog._syntax_light_buttons["comment"]
    assert button.color() == theme.LIGHT_SYNTAX.comment

    # The swatch asks through the replaceable chooser — a modal QColorDialog
    # would hang the headless run — and the answer is what gets painted.
    dialog._ask_color = lambda start: "#00ff00"
    button.click()
    assert button.color() == "#00ff00"

    # Not stored until «Применить», and the store is what the window re-reads.
    assert dialog._settings.syntax_overrides("light") == {}
    dialog.button("apply").click()
    assert dialog._settings.syntax_overrides("light") == {"comment": "#00ff00"}

    # «Вернуть встроенные цвета» clears it back on screen and in the file.
    dialog.restore_syntax_colors()
    assert dialog._settings.syntax_overrides("light") == {}
    assert button.color() == theme.LIGHT_SYNTAX.comment
    print("ok: a syntax colour is edited through the swatch, applied, and can be reverted")


def test_the_widgets_show_the_stored_values(directory: pathlib.Path) -> None:
    settings = Settings(directory / "show.ini")
    settings.font_size = 17.0
    settings.line_numbers = False
    settings.output_position = "bottom"
    settings.import_paths = ["C:/общие"]
    from prologd_gui.settingsdialog import SettingsDialog

    dialog = SettingsDialog(settings)
    code = settings_module.BY_KEY
    assert dialog._widgets[code["editor/font_size"].key].value() == 17
    assert dialog._widgets[code["editor/line_numbers"].key].isChecked() is False
    assert dialog._widgets[code["view/output_position"].key].currentData() == "bottom"
    assert dialog._widgets[code["execution/import_paths"].key].paths() == ["C:/общие"]
    assert dialog.message() == "", "nothing to report before a button is pressed"
    print("ok: the widgets show what the file holds, default and changed alike")


def test_apply_writes_and_cancel_does_not(directory: pathlib.Path) -> None:
    path = directory / "apply.ini"
    dialog = dialog_for(directory, "apply.ini")
    keys = {setting.key: setting for setting in settings_module.SETTINGS}

    dialog._widgets[keys["editor/line_numbers"].key].setChecked(False)
    dialog._widgets[keys["view/output_position"].key].setCurrentIndex(
        dialog._widgets[keys["view/output_position"].key].findData("right")
    )
    dialog.button("cancel").click()
    assert Settings(path).line_numbers is True, "«Отмена» wrote the file"
    assert Settings(path).output_position == "bottom", "«Отмена» wrote the file"

    dialog = dialog_for(directory, "apply.ini")
    dialog._widgets[keys["editor/line_numbers"].key].setChecked(False)
    dialog._widgets[keys["view/output_position"].key].setCurrentIndex(
        dialog._widgets[keys["view/output_position"].key].findData("bottom")
    )
    dialog.button("apply").click()
    read = Settings(path)
    assert read.line_numbers is False
    assert read.output_position == "bottom"
    assert dialog.applied() is True
    print("ok: «Применить» writes, «Отмена» leaves the file alone")


def test_reset_puts_the_defaults_in_the_widgets_and_needs_applying(
    directory: pathlib.Path,
) -> None:
    path = directory / "reset.ini"
    settings = Settings(path)
    settings.font_size = 30.0
    settings.wrap = True

    dialog = dialog_for(directory, "reset.ini")
    dialog.button("reset").click()
    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    assert dialog._widgets[keys["editor/font_size"].key].value() == int(
        settings_module.DEFAULT_FONT_SIZE
    ), "«Сбросить» did not touch the widget"
    assert Settings(path).font_size == 30.0, "«Сбросить» wrote without being applied"
    assert "Применить" in dialog.message(), dialog.message()

    dialog.button("apply").click()
    read = Settings(path)
    assert read.font_size == settings_module.DEFAULT_FONT_SIZE
    assert read.wrap is False
    print("ok: «Сбросить» fills the widgets, and the defaults are kept only on apply")


def test_import_stages_a_file_and_carries_unknown_keys(directory: pathlib.Path) -> None:
    path = directory / "import.ini"
    source = directory / "класс.ini"
    source.write_text("[editor]\nfont_size=9\n[будущее]\nthing=42\n", encoding="utf-8")

    dialog = dialog_for(directory, "import.ini")
    assert not dialog._settings.raw_value("будущее/thing"), "the store knew the key already"
    assert dialog.import_from(str(source)) is True

    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    assert dialog._widgets[keys["editor/font_size"].key].value() == 9, "the value is not on screen"
    assert Settings(path).font_size == settings_module.DEFAULT_FONT_SIZE, "import wrote at once"

    # «Отмена» after «Импорт…»: nothing at all, not even the unknown key.
    dialog.button("cancel").click()
    assert Settings(path).raw_value("будущее/thing") is None, "«Отмена» kept the import"

    dialog = dialog_for(directory, "import.ini")
    assert dialog.import_from(str(source)) is True
    dialog.button("ok").click()
    read = Settings(path)
    assert read.font_size == 9.0
    assert read.raw_value("будущее/thing") == "42", "the unknown key of the file was dropped"

    # A file that is not a configuration is reported, not swallowed.
    junk = directory / "не-настройки.txt"
    junk.write_text("это просто текст\n", encoding="utf-8")
    assert dialog.import_from(str(junk)) is False
    assert "не удалось" in dialog.message(), dialog.message()
    print("ok: «Импорт…» shows a file, «ОК» keeps it, unknown keys and all")


def test_export_writes_a_file_another_store_can_read(directory: pathlib.Path) -> None:
    target = directory / "для_класса.ini"
    dialog = dialog_for(directory, "export.ini")
    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    dialog._widgets[keys["editor/font_size"].key].setValue(14)
    assert dialog.export_to(str(target)) is True

    read = Settings(target)
    assert read.font_size == 14.0, "the exported file does not carry the value on screen"
    assert read.format_width == settings_module.DEFAULT_FORMAT_WIDTH
    assert "выгружено" in dialog.message(), dialog.message()
    print("ok: «Экспорт…» writes the whole configuration, the current values included")


def test_the_folder_rows_and_the_insert_page(directory: pathlib.Path) -> None:
    """The two rows that are not a single widget, and the page built by hand."""
    from prologd_gui import shortcuts

    dialog = dialog_for(directory, "folders.ini")
    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    editor = dialog._widgets[keys["execution/import_paths"].key]
    dialog._ask_directory = lambda: "C:/курс"

    add, remove = editor.buttons()
    assert add.icon().isNull() is False, "«Добавить…» lost its picture"
    assert remove.icon().isNull() is False, "«Убрать» lost its picture"
    add.click()
    add.click()  # the same folder twice: the list keeps one
    dialog._ask_directory = lambda: None
    add.click()
    assert editor.paths() == ["C:/курс"], editor.paths()

    editor.list_widget().item(0).setSelected(True)
    remove.click()
    assert editor.paths() == [], "«Убрать» did not remove the selected row"

    # The process folder is a plain field with a «…» button beside it.
    field = dialog._widgets[keys["execution/process_directory_path"].key]
    dialog._ask_directory = lambda: "C:/общие"
    dialog._browse(keys["execution/process_directory_path"].key)
    assert field.text() == "C:/общие"

    # The insert page shows the live table and can put the built-in one back.
    dialog.show_section("Вставки")
    shown = [dialog._inserts.item(row).text() for row in range(dialog._inserts.count())]
    assert any("Ctrl+;" in line for line in shown), shown[:3]
    dialog._settings.shortcuts_table = "не json"
    dialog._fill_inserts()
    settings_after = dialog._settings.shortcuts_table
    dialog.restore_shortcuts()
    assert settings_after == "не json"
    assert dialog._settings.shortcuts_table == shortcuts.Shortcuts.default().to_json()
    print("ok: the folder rows work, and the insert page lists and restores the table")


def test_the_interpreter_and_process_directory_rows(directory: pathlib.Path) -> None:
    """The two rows of task_46: a file chooser and a three-way choice."""
    dialog = dialog_for(directory, "interp.ini")
    keys = {setting.key: setting for setting in settings_module.SETTINGS}

    # The interpreter is a *file* row: its «…» asks for one file, not a folder.
    field = dialog._widgets[keys["execution/interpreter"].key]
    dialog._ask_file = lambda: "C:/проlogd/prologd.exe"
    dialog._browse(keys["execution/interpreter"].key)
    assert field.text() == "C:/проlogd/prologd.exe"

    # The process directory is a choice of three, and the default is `file`.
    combo = dialog._widgets[keys["execution/process_directory"].key]
    assert combo.count() == 3
    assert combo.currentData() == "file"
    values = [combo.itemData(row) for row in range(combo.count())]
    assert values == ["file", "window", "custom"], values
    print("ok: the interpreter row asks for a file, the directory row is a three-way choice")


def test_the_process_directory_path_follows_its_choice(directory: pathlib.Path) -> None:
    """«Свой каталог процесса» is inactive until «свой каталог» is chosen."""
    dialog = dialog_for(directory, "dir_switch.ini")
    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    combo = dialog._widgets[keys["execution/process_directory"].key]
    holder = dialog._row_holders[keys["execution/process_directory_path"].key]

    assert combo.currentData() == "file"
    assert holder.isEnabled() is False, "the path row is active without «свой каталог»"
    combo.setCurrentIndex(combo.findData("custom"))
    assert holder.isEnabled() is True, "«свой каталог» did not enable the path row"
    combo.setCurrentIndex(combo.findData("window"))
    assert holder.isEnabled() is False
    print("ok: the process-directory path is inactive until «свой каталог» is chosen")


def test_applying_announces_itself(directory: pathlib.Path) -> None:
    """`changesApplied` is what makes «Применить» visible behind the dialog.

    Not every button writes: «Отмена» writes nothing, «Сбросить» only fills the
    widgets, while «Применить», «ОК» and «Вернуть встроенную таблицу» write and
    therefore have to say so.
    """
    keys = {setting.key: setting for setting in settings_module.SETTINGS}
    seen: list[int] = []

    dialog = dialog_for(directory, "signal.ini")
    dialog.changesApplied.connect(lambda: seen.append(1))
    dialog._widgets[keys["editor/line_numbers"].key].setChecked(False)
    dialog.button("cancel").click()
    assert seen == [], "«Отмена» announced a change"

    dialog = dialog_for(directory, "signal.ini")
    dialog.changesApplied.connect(lambda: seen.append(1))
    dialog._widgets[keys["editor/line_numbers"].key].setChecked(False)
    dialog.button("reset").click()
    assert seen == [], "«Сбросить» wrote without being applied"
    dialog.button("apply").click()
    assert len(seen) == 1, seen
    dialog.button("ok").click()
    assert len(seen) == 2, seen

    dialog.restore_shortcuts()
    assert len(seen) == 3, seen
    print("ok: «Применить», «ОК» and the built-in table announce themselves, «Отмена» does not")


def test_the_button_row_and_the_shared_label_column(directory: pathlib.Path) -> None:
    """Where the buttons sit, and that the fields line up on every page.

    Both were asked for after the first hands-on run: the file's own buttons
    («Сбросить», «Импорт…», «Экспорт…») on the left and the ones that end the
    dialog («ОК», «Отмена», «Применить») on the right, and one label-column width
    for the whole dialog — a `QFormLayout` sizes that column to the longest label
    *on its own page*, so the fields used to jump sideways when the section
    changed.
    """
    dialog = dialog_for(directory, "layout.ini")
    assert dialog.button_order() == ["reset", "import", "export", "ok", "cancel", "apply"]

    width = dialog.label_column_width()
    assert width > 0, "the column width was never computed"
    widest = max(label.sizeHint().width() for label in dialog._labels)
    assert width >= widest, (width, widest)
    for label in dialog._labels:
        assert label.minimumWidth() == width and label.maximumWidth() == width, (
            label.text(),
            label.minimumWidth(),
        )

    labels = [label.text() for label in dialog._labels]
    assert "Шрифт:" in labels and "Дополнительные каталоги ИМПОРТ:" in labels, labels[:4]
    print(f"ok: the buttons are ordered as asked, and every page's labels take {width} px")


def main(argv: list[str]) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("skipped: PySide6 is not installed, so the dialog is not checked")
        return 0
    application = QApplication(sys.argv[:1])
    with tempfile.TemporaryDirectory(prefix="prologd_gui_dialog_") as name:
        directory = pathlib.Path(name)
        test_a_page_per_section_and_a_widget_per_row(directory)
        test_the_syntax_page_lists_every_colour_in_both_themes(directory)
        test_a_colour_can_be_changed_and_applied(directory)
        test_the_widgets_show_the_stored_values(directory)
        test_apply_writes_and_cancel_does_not(directory)
        test_reset_puts_the_defaults_in_the_widgets_and_needs_applying(directory)
        test_import_stages_a_file_and_carries_unknown_keys(directory)
        test_export_writes_a_file_another_store_can_read(directory)
        test_the_folder_rows_and_the_insert_page(directory)
        test_the_interpreter_and_process_directory_rows(directory)
        test_the_process_directory_path_follows_its_choice(directory)
        test_the_button_row_and_the_shared_label_column(directory)
        test_applying_announces_itself(directory)
    del application
    print("all settings-dialog checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
