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
    assert dialog.section_names() == [
        *settings_module.SECTIONS,
        settings_module.__dict__.get("INSERTS_PAGE", "Вставки"),
    ] or dialog.section_names()[:-1] == list(settings_module.SECTIONS), dialog.section_names()

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
        dialog._widgets[keys["view/output_position"].key].findData("bottom")
    )
    dialog.button("cancel").click()
    assert Settings(path).line_numbers is True, "«Отмена» wrote the file"
    assert Settings(path).output_position == "right", "«Отмена» wrote the file"

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
    add.click()
    add.click()  # the same folder twice: the list keeps one
    dialog._ask_directory = lambda: None
    add.click()
    assert editor.paths() == ["C:/курс"], editor.paths()

    editor.list_widget().item(0).setSelected(True)
    remove.click()
    assert editor.paths() == [], "«Убрать» did not remove the selected row"

    # The working folder is a plain field with a «…» button beside it.
    field = dialog._widgets[keys["execution/working_directory"].key]
    dialog._ask_directory = lambda: "C:/общие"
    dialog._browse(keys["execution/working_directory"].key)
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
        test_the_widgets_show_the_stored_values(directory)
        test_apply_writes_and_cancel_does_not(directory)
        test_reset_puts_the_defaults_in_the_widgets_and_needs_applying(directory)
        test_import_stages_a_file_and_carries_unknown_keys(directory)
        test_export_writes_a_file_another_store_can_read(directory)
        test_the_folder_rows_and_the_insert_page(directory)
    del application
    print("all settings-dialog checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
