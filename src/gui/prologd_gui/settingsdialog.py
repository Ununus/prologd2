"""«Настройки…»: every preference of `settings.SETTINGS` in one dialog.

The dialog is **built from the description table** in `settings.py`: each record
carries its label, section, kind, default and bounds, and this module turns a
record into a row.  That is the whole reason the table exists — a new preference
is a new `Setting`, and the dialog, its validation and «Сбросить» grow by
themselves.  The reverse is checked too (`src/gui/tests/test_settingsdialog.py`):
every row of the table has a widget, and every widget writes its key.

What the buttons mean:

* **ОК** and **Применить** write the values through `Settings` — which validates
  by the same description — and then the window re-reads them, so a change shows
  at once (font, line numbers, the side of the output panel) rather than at the
  next start;
* **Отмена** closes without writing: an import that was not applied yet is
  dropped with it;
* **Сбросить** puts the defaults into the *widgets* — they still have to be
  applied, so the reset can be looked at before it is kept;
* **Импорт…** stages a file (`Settings.read_keys`) and shows it; **Экспорт…**
  applies first and then writes the whole configuration, because what is
  exported has to be what the user is looking at.

Nothing here calls a modal box of its own (the file and folder choosers are
small replaceable methods): a modal dialog hangs a headless test rather than
failing it, and that trap has cost this project time twice.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import actions, assets
from . import settings as settings_module
from . import shortcuts
#: The page that is not built from the table: the insert table of task_31 is
#: *data* in the settings file, and what the user needs here is to see it and to
#: find the file — not a JSON editor.
INSERTS_PAGE = "Вставки"


class PathListEditor(QWidget):
    """A list of directories with «Добавить…» and «Убрать».

    One folder per click: `QFileDialog` returns one at a time, and the list is
    there to show what was collected, so a multi-selection dialog would buy
    nothing.  A folder already in the list is not added twice — the same
    directory twice would only make the engine search it twice.
    """

    def __init__(self, ask, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ask = ask
        self._list = QListWidget(self)
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setMinimumHeight(72)
        add = QToolButton(self)
        add.setToolTip("Добавить…")
        add_picture = assets.icon(actions.ADD_ICON)
        if add_picture is not None:
            add.setIcon(add_picture)
        add.clicked.connect(self._add)
        remove = QToolButton(self)
        remove.setToolTip("Убрать")
        remove_picture = assets.icon(actions.REMOVE_ICON)
        if remove_picture is not None:
            remove.setIcon(remove_picture)
        remove.clicked.connect(self.remove_selected)
        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._list, 1)
        row.addLayout(buttons)
        self._add_button = add
        self._remove_button = remove

    # -- what the dialog reads and writes ----------------------------------
    def paths(self) -> list[str]:
        return [self._list.item(row).text() for row in range(self._list.count())]

    def set_paths(self, paths) -> None:
        self._list.clear()
        for path in paths or []:
            self._list.addItem(QListWidgetItem(str(path)))

    def add_path(self, path: str) -> bool:
        """Adds one folder unless it is already there; returns whether it landed."""
        text = str(path).strip()
        if not text or text in self.paths():
            return False
        self._list.addItem(QListWidgetItem(text))
        return True

    def remove_selected(self) -> int:
        rows = sorted((index.row() for index in self._list.selectedIndexes()), reverse=True)
        for row in rows:
            self._list.takeItem(row)
        return len(rows)

    def list_widget(self) -> QListWidget:
        """The list itself — what a test clicks in."""
        return self._list

    def buttons(self) -> tuple[QToolButton, QToolButton]:
        return self._add_button, self._remove_button

    def _add(self) -> None:
        chosen = self._ask()
        if chosen:
            self.add_path(chosen)


def _same(value: object, other: object) -> bool:
    """Whether a widget's value is already what the store holds.

    A `dirs` row keeps a list, and the store answers with a list too, but the
    description's default is a tuple — comparing them needs the same shape.
    """
    if isinstance(value, list) or isinstance(other, (list, tuple)):
        return list(value) == list(other)  # type: ignore[arg-type]
    return value == other


class SettingsDialog(QDialog):
    """The described settings, one page per section, built from the table."""

    #: Emitted after the values were written — «Применить» and «ОК».
    #: The window behind a modal dialog is blocked for input but still painted,
    #: so this is what makes an applied change visible *there and then* (font,
    #: line numbers, the side of the output panel) instead of after the dialog
    #: closes.  The dialog itself knows nothing about editors: it says «written»
    #: and whoever is interested re-reads the store.
    changesApplied = Signal()


    def __init__(self, settings: settings_module.Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(680, 460)
        self._settings = settings
        self._applied = False
        #: An imported file that has not been applied yet.  «Отмена» drops it.
        self._staged: dict[str, object] = {}
        self._widgets: dict[str, QWidget] = {}
        #: The row wrapper of a `directory`/`file` setting — the field *with* its
        #: «…» button — keyed the same way as `_widgets`, so a row that follows
        #: another can be enabled and disabled as one piece (task_46).
        self._row_holders: dict[str, QWidget] = {}
        self._sections: dict[str, int] = {}
        self._build()
        self.reload()

    # -- construction ------------------------------------------------------
    def _build(self) -> None:
        self._nav = QListWidget(self)
        self._nav.setMaximumWidth(160)
        # Long section names elide instead of bringing in a scrollbar: a scrollbar
        # in a six-row list of sections is noise.
        self._nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pages = QStackedWidget(self)
        #: The pages' form layouts and the labels in them, for the one column
        #: width they all get at the end of this method.
        self._forms: list[QFormLayout] = []
        self._labels: list[QLabel] = []
        for section in settings_module.SECTIONS:
            page = QWidget(self)
            form = QFormLayout(page)
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            for setting in self._rows(section):
                widget = self._make_widget(setting)
                self._widgets[setting.key] = widget
                label = QLabel(f"{setting.label}:")
                self._labels.append(label)
                field: QWidget = widget
                if setting.kind in ("directory", "file"):
                    field = self._with_browse(setting, widget)
                    self._row_holders[setting.key] = field
                # Every value fills its column, so the right edge of the fields is
                # one line on the page; a checkbox stays its own size and sits at
                # the left edge of that column, which is where it is ticked.
                if not isinstance(widget, QCheckBox):
                    field.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                    )
                for view in (label, field):
                    if setting.hint:
                        view.setToolTip(setting.hint)
                form.addRow(label, field)
            form.addRow(QWidget())  # a stretch row: the rows stay at the top
            self._forms.append(form)
            self._sections[section] = self._pages.addWidget(page)
            self._nav.addItem(section)
        self._build_inserts_page()
        self._align_columns()
        # «Свой каталог процесса» follows the choice above it: inactive until
        # «свой каталог» is selected, and `reload` (which fills the combo) then
        # fires the change signal and settles the state again (task_46).
        self._sync_process_directory_path()
        process_combo = self._widgets[settings_module.PROCESS_DIRECTORY]
        process_combo.currentIndexChanged.connect(
            lambda _index: self._sync_process_directory_path()
        )
        self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)
        self._nav.setCurrentRow(0)

        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)

        left = QVBoxLayout()
        left.addWidget(self._nav, 1)
        body = QVBoxLayout(self)
        body.setContentsMargins(8, 8, 8, 8)
        row = QHBoxLayout()
        row.addLayout(left)
        row.addWidget(self._pages, 1)
        body.addLayout(row, 1)
        body.addWidget(self._message_label)
        body.addWidget(self._build_buttons())

    def _align_columns(self) -> None:
        """One label width for every page.

        A `QFormLayout` sizes its first column to the longest label *on that
        page*, so the fields started at a different x on every section and the
        page shifted sideways when the user walked through them.  A fixed width —
        the widest label of the whole dialog — puts every page on the same grid;
        the labels are right-aligned, so what the eye compares (the colon column
        and the left edge of the fields) is in the same place everywhere.

        `QFormLayout` has no column width to set in PySide6 (`setColumnMinimumWidth`
        belongs to the grid and box layouts), and a fixed label is what actually
        makes the column the same width wherever it is used.
        """
        self._label_column = max(
            (label.sizeHint().width() for label in self._labels), default=0
        )
        for label in self._labels:
            label.setFixedWidth(self._label_column)

    def label_column_width(self) -> int:
        """The width every page's label column has (what `_align_columns` set)."""
        return self._label_column

    def _rows(self, section: str) -> list[settings_module.Setting]:
        return [entry for entry in settings_module.SETTINGS if entry.section == section]

    def _sync_process_directory_path(self) -> None:
        """`«Свой каталог процесса»` is editable only for the `custom` answer.

        The path row follows the choice above it: `каталог файла` and `рабочая
        папка окна` leave no path to type, so the field — and its «…» button —
        is inactive until «свой каталог» is chosen (task_46).
        """
        combo = self._widgets.get(settings_module.PROCESS_DIRECTORY)
        holder = self._row_holders.get(settings_module.PROCESS_DIRECTORY_PATH)
        if combo is None or holder is None:
            return
        holder.setEnabled(combo.currentData() == "custom")

    def _make_widget(self, setting: settings_module.Setting) -> QWidget:
        """The widget a record asks for, by its `kind`."""
        if setting.kind == "bool":
            return QCheckBox(self)
        if setting.kind == "int":
            box = QSpinBox(self)
            box.setRange(int(setting.low), int(setting.high))
            box.setSuffix(setting.suffix)
            return box
        if setting.kind == "float":
            box = QDoubleSpinBox(self)
            box.setDecimals(0)
            box.setSingleStep(1)
            box.setRange(float(setting.low), float(setting.high))
            box.setSuffix(setting.suffix)
            return box
        if setting.kind == "choice":
            combo = QComboBox(self)
            for value, text in setting.choices:
                combo.addItem(text, value)
            return combo
        if setting.kind == "dirs":
            # A closure, not the bound method: the chooser is replaceable on the
            # dialog (`_ask_directory`), and a bound method captured here would
            # keep pointing at the real `QFileDialog` — which is modal, and a
            # modal box in a headless run hangs the test instead of failing it.
            return PathListEditor(lambda: self._ask_directory(), self)
        return QLineEdit(self)

    def _with_browse(self, setting: settings_module.Setting, field: QWidget) -> QWidget:
        """A path field with a «…» button, since nobody types a path by hand.

        A `directory` row asks for a folder, a `file` row for one file (task_46's
        interpreter); the button's tooltip says which.
        """
        button = QToolButton(self)
        button.setText("…")
        button.setToolTip(
            "Выбрать файл" if setting.kind == "file" else "Выбрать каталог"
        )
        button.clicked.connect(lambda: self._browse(setting.key))
        holder = QWidget(self)
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        row.addWidget(button)
        return holder

    def _build_inserts_page(self) -> None:
        """The «Вставки» page: what `Ctrl`+key does, and where the table lives.

        The table is data (task_31) — this page shows the active chords and opens
        the file they are written in.  «Вернуть встроенную» is here because a
        hand-edited table is the one setting a user can break without noticing:
        the built-in one is always there to fall back to.
        """
        page = QWidget(self)
        layout = QVBoxLayout(page)
        note = QLabel(
            "Таблица вставок живёт в файле настроек (ключ <b>shortcuts/table</b>): "
            "знак, который на вашей клавиатуре лежит иначе, переносится на другое "
            "сочетание там же, без правки кода."
        )
        note.setWordWrap(True)
        self._inserts = QListWidget(page)
        self._inserts.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        path_label = QLabel(f"Файл настроек: {self._settings.path}")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setWordWrap(True)
        open_button = QPushButton("Открыть файл настроек", page)
        open_button.clicked.connect(lambda: self._open_settings_file())
        revert_button = QPushButton("Вернуть встроенную таблицу", page)
        revert_button.clicked.connect(self.restore_shortcuts)
        layout.addWidget(note)
        layout.addWidget(self._inserts, 1)
        layout.addWidget(path_label)
        layout.addWidget(open_button)
        layout.addWidget(revert_button)
        self._sections[INSERTS_PAGE] = self._pages.addWidget(page)
        self._nav.addItem(INSERTS_PAGE)

    def _build_buttons(self) -> QWidget:
        """The buttons, in the order the user asked for.

        A `QDialogButtonBox` lays its buttons out by *role* and by the current
        style, so the order cannot be chosen with it — and the order matters
        here: «Сбросить», «Импорт…» and «Экспорт…» act on the whole file and
        belong on the left, while «ОК», «Отмена» and «Применить» close or end
        the dialog and belong on the right, where every other window has them.
        """
        def make(title: str, tooltip: str = "") -> QPushButton:
            button = QPushButton(title, self)
            if tooltip:
                button.setToolTip(tooltip)
            return button

        ok = make("ОК")
        cancel = make("Отмена")
        apply_button = make("Применить")
        reset = make("Сбросить", "Вернуть значения по умолчанию")
        import_button = make("Импорт…", "Прочитать настройки из файла")
        export_button = make(
            "Экспорт…", "Выгрузить настройки в файл (текущие значения применяются)"
        )
        ok.clicked.connect(self._accept)
        apply_button.clicked.connect(self.apply)
        cancel.clicked.connect(self.reject)
        reset.clicked.connect(self.reset)
        import_button.clicked.connect(lambda: self.import_from())
        export_button.clicked.connect(lambda: self.export_to())
        # `ОК` answers Enter and the dialog's `default` button is what the focus
        # lands on when the dialog opens.
        ok.setDefault(True)
        ok.setAutoDefault(True)

        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        for button in (reset, import_button, export_button):
            layout.addWidget(button)
        layout.addStretch(1)
        for button in (ok, cancel, apply_button):
            layout.addWidget(button)
        self._buttons_row = row
        self._buttons = {
            "ok": ok,
            "apply": apply_button,
            "cancel": cancel,
            "reset": reset,
            "import": import_button,
            "export": export_button,
        }
        return row

    def button_order(self) -> list[str]:
        """The buttons left to right, by name (what a test compares).

        Read from the *layout*, not from `x()`: a widget that has not been shown
        yet has no geometry, and a test must not depend on the window manager
        having laid the dialog out already.
        """
        layout = self._buttons_row.layout()
        return [
            name
            for name, _ in sorted(self._buttons.items(), key=lambda item: layout.indexOf(item[1]))
        ]

    # -- what the widgets hold ---------------------------------------------
    def widgets(self) -> dict[str, QWidget]:
        """The widget of every described setting, by key (what tests drive)."""
        return dict(self._widgets)

    def button(self, name: str):
        """One of the dialog's buttons by name (what tests click)."""
        return self._buttons[name]

    def values(self) -> dict[str, object]:
        """What is on screen right now, as the store would hold it."""
        return {
            setting.key: self._read_widget(setting)
            for setting in settings_module.SETTINGS
        }

    def reload(self) -> None:
        """Fills every widget from the settings — the constructor and «Импорт…»."""
        for setting in settings_module.SETTINGS:
            self._set_widget(setting, self._settings.value_of(setting))
        self._fill_inserts()

    def _fill_inserts(self) -> None:
        table = shortcuts.Shortcuts.from_json(self._settings.shortcuts_table)
        self._inserts.clear()
        for line in table.cheatsheet():
            self._inserts.addItem(QListWidgetItem(line))

    def _set_widget(self, setting: settings_module.Setting, value: object) -> None:
        widget = self._widgets[setting.key]
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            widget.setCurrentIndex(index if index >= 0 else 0)
        elif isinstance(widget, PathListEditor):
            widget.set_paths(value)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))

    def _read_widget(self, setting: settings_module.Setting) -> object:
        widget = self._widgets[setting.key]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, PathListEditor):
            return widget.paths()
        if isinstance(widget, QLineEdit):
            return widget.text()
        raise TypeError(f"no reader for {setting.key}")

    # -- the buttons -------------------------------------------------------
    def applied(self) -> bool:
        """Whether anything was written through this dialog."""
        return self._applied

    def apply(self) -> None:
        """Writes what changed; `Settings` validates against the description.

        Only the rows that differ from the store: writing all of them would put
        twenty-seven keys into a fresh file the user never touched, and it would
        *freeze* the one preference that follows another (the output's font size
        reads as the editor's until it is set).

        `changesApplied` goes out even when nothing changed: the caller's answer
        to it is a re-read of the store, which is cheap and always right.
        """
        changed = 0
        for setting in settings_module.SETTINGS:
            value = self._read_widget(setting)
            if _same(value, self._settings.value_of(setting)):
                continue
            self._settings.set_value(setting, value)
            changed += 1
        if self._staged:
            self._settings.write_keys(self._staged)
            self._staged = {}
        self._applied = True
        self._message(f"настройки записаны: {changed}" if changed else "ничего не изменилось")
        self.changesApplied.emit()

    def _accept(self) -> None:
        self.apply()
        self.accept()

    def reset(self) -> None:
        """Puts the defaults into the widgets — «Применить» still has to follow."""
        for setting in settings_module.SETTINGS:
            self._set_widget(setting, setting.default)
        if self._sections:
            self._nav.setCurrentRow(0)
        self._message("значения по умолчанию — нажмите «Применить», чтобы сохранить")

    def restore_shortcuts(self) -> None:
        """Writes the built-in insert table, for a table that was broken by hand."""
        self._settings.shortcuts_table = shortcuts.Shortcuts.default().to_json()
        self._fill_inserts()
        self._applied = True
        self._message("таблица вставок возвращена к встроенной")
        self.changesApplied.emit()

    def export_to(self, path: str | None = None) -> bool:
        """Writes the whole configuration to a file (the current values included)."""
        target = path or self._ask_export_path()
        if not target:
            return False
        self.apply()
        count = self._settings.export_to(target)
        self._message(f"выгружено ключей: {count} — {pathlib.Path(target).name}")
        return True

    def import_from(self, path: str | None = None) -> bool:
        """Reads a file *into the dialog*; «Применить» or «ОК» keeps it.

        Staged rather than written: «Отмена» after «Импорт…» has to leave the
        settings, unknown keys included, exactly as they were.
        """
        target = path or self._ask_import_path()
        if not target:
            return False
        try:
            values = self._settings.read_keys(target)
        except (OSError, ValueError) as error:
            self._message(f"не удалось прочитать: {error}")
            return False
        self._staged = values
        # The widgets read from the *store*, which does not have the file yet, so
        # the imported values are put on screen one by one.
        for setting in settings_module.SETTINGS:
            if setting.key in values:
                self._set_widget(setting, values[setting.key])
        self._fill_inserts()
        self._message(
            f"прочитано ключей: {len(values)} — нажмите «Применить», чтобы сохранить"
        )
        return True

    def message(self) -> str:
        """The line under the pages (what a test reads instead of a modal box)."""
        return self._message_label.text()

    def section_names(self) -> list[str]:
        return [self._nav.item(row).text() for row in range(self._nav.count())]

    def show_section(self, name: str) -> bool:
        """Opens one page by its title; False when there is no such page."""
        found = self._nav.findItems(name, Qt.MatchFlag.MatchExactly)
        if not found:
            return False
        self._nav.setCurrentRow(self._nav.row(found[0]))
        return True

    def _message(self, text: str) -> None:
        self._message_label.setText(text)

    # -- the replaceable modals --------------------------------------------
    def _ask_export_path(self) -> str | None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Выгрузить настройки", str(self._start_directory() / "prologd.ini"),
            "Настройки (*.ini);;Все файлы (*)",
        )
        return path or None

    def _ask_import_path(self) -> str | None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Прочитать настройки", str(self._start_directory()),
            "Настройки (*.ini);;Все файлы (*)",
        )
        return path or None

    def _ask_directory(self) -> str | None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Каталог для ИМПОРТ", str(self._start_directory())
        )
        return chosen or None

    def _ask_file(self) -> str | None:
        """The chooser of the interpreter row (task_46): one executable."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Интерпретатор", str(self._start_directory()),
            "Исполняемый файл (*.exe);;Все файлы (*)",
        )
        return path or None

    def _start_directory(self) -> pathlib.Path:
        remembered = self._settings.last_directory
        if remembered and pathlib.Path(remembered).is_dir():
            return pathlib.Path(remembered)
        return pathlib.Path.home()

    def _browse(self, key: str) -> None:
        setting = settings_module.BY_KEY[key]
        chosen = self._ask_file() if setting.kind == "file" else self._ask_directory()
        widget = self._widgets.get(key)
        if chosen and isinstance(widget, QLineEdit):
            widget.setText(chosen)

    def _open_settings_file(self) -> None:
        """Hands the ini to the desktop: it is a text file, and it is the last
        word on everything this dialog shows."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._settings.path)))
        self._message(f"файл настроек: {self._settings.path}")
