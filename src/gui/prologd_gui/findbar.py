"""The find bar: the widgets, and nothing about where the matches are.

A strip above the editor and not a dialog.  A modal box cannot be driven from a
headless test — the same trap that made `Buffers._ask_save` an injectable method —
and the editor has to stay readable while a search is running, which a dialog
covers up.

The bar knows three things: what was typed, which switches are on, and one line of
text to show («3 из 17 — поиск с начала»).  Where the matches are, which one the
caret is on and how a replacement is written belong to `search.py` (the arithmetic)
and to the window (the editor).  So this module has no opinions to test beyond its
signals, and `search.py` is the part `test_search.py` hammers.

`Enter` in the question field steps forward and `Shift+Enter` backwards, the way
`F3` and `Shift+F3` do from the menu — the field keeps the keys of a `QLineEdit`
otherwise, so a selection can still be edited with the arrows.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import actions, assets, search


class _Field(QLineEdit):
    """A field where `Enter` finds and `Esc` closes the bar."""

    #: `Enter` (False) or `Shift+Enter` (True).
    stepped = Signal(bool)
    escaped = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.stepped.emit(bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class FindBar(QWidget):
    """What `Ctrl+F` puts above the editor."""

    #: The question or a switch changed: search again from the caret of the pane.
    changed = Signal()
    #: Walk the matches: `Enter`/`F3` move forward, `Shift+Enter`/`Shift+F3` back.
    stepRequested = Signal(bool)
    replaceRequested = Signal()
    replaceAllRequested = Signal()
    #: `Esc`, the `✕`, or a step that found nothing to go on with.
    closeRequested = Signal()
    #: «Только в выделении» was switched on or off; the span is the window's.
    spanToggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        #: True while the fields are filled from the outside, so the fill is not
        #: mistaken for typing and does not start a search of its own.
        self._quiet = False
        #: The three rows.  Rows and not loose layouts, because the geometry of a
        #: widget says which row it ended up on — which is what a test checks.
        self._field_row = QWidget()
        self._switch_row = QWidget()
        self._replace_row = QWidget()

        self._find = _Field()
        self._find.setPlaceholderText("найти")
        self._find.setClearButtonEnabled(True)
        self._find.setMinimumWidth(180)
        self._find.textChanged.connect(self._on_find_text)
        self._find.stepped.connect(self.stepRequested)
        self._find.escaped.connect(self.closeRequested)

        self._replace = _Field()
        self._replace.setPlaceholderText("заменить на")
        self._replace.setMinimumWidth(180)
        self._replace.stepped.connect(lambda _backwards: self.replaceRequested.emit())
        self._replace.escaped.connect(self.closeRequested)

        self._previous = self._picture_button("find_prev", "Назад (Shift+F3)")
        self._previous.clicked.connect(lambda: self.stepRequested.emit(True))
        self._next = self._picture_button("find_next", "Далее (F3)")
        self._next.clicked.connect(lambda: self.stepRequested.emit(False))

        self._status = QLabel("")
        self._status.setMinimumWidth(130)
        self._status.setToolTip("Сколько нашлось и с какого места поиск пошёл на второй круг")

        self._match_case = QCheckBox("С учётом регистра")
        self._match_case.setToolTip("«факт» и «Факт» — разные предикаты, но искать их "
                                    "вместе иногда удобнее")
        self._match_case.toggled.connect(self._on_switch)
        self._whole_word = QCheckBox("Слово целиком")
        self._whole_word.setToolTip("Не находить «факт» внутри «фактик»")
        self._whole_word.toggled.connect(self._on_switch)
        self._in_selection = QCheckBox("Только в выделении")
        self._in_selection.setToolTip("Искать внутри фрагмента, выделенного в редакторе")
        self._in_selection.toggled.connect(self._on_span_toggled)

        self._replace_button = QPushButton("Заменить")
        self._replace_button.clicked.connect(self.replaceRequested)
        self._replace_all_button = QPushButton("Заменить всё")
        self._replace_all_button.clicked.connect(self.replaceAllRequested)

        self._disclosure = QToolButton()
        self._disclosure.setText("Замена")
        self._disclosure.setCheckable(True)
        self._disclosure.setToolTip("Показать поле «Заменить на» и кнопки замены")
        self._disclosure.toggled.connect(self.show_replace)
        picture = assets.icon(actions.BY_KEY["find"].icon or "")
        if picture is not None:
            self._disclosure.setIcon(picture)

        self._close = QToolButton()
        self._close.setText("\u2715")
        self._close.setToolTip("Закрыть поиск (Esc)")
        self._close.clicked.connect(self.closeRequested)

        first_row = QHBoxLayout(self._field_row)
        first_row.setContentsMargins(0, 0, 0, 0)
        first_row.addWidget(self._lens())
        first_row.addWidget(self._find, 1)
        first_row.addWidget(self._previous)
        first_row.addWidget(self._next)
        first_row.addWidget(self._status)
        first_row.addWidget(self._disclosure)
        first_row.addWidget(self._close)

        # The switches get a row of their own: beside the field they were the first
        # thing squeezed out when the window was narrow — and a switch that cannot be
        # read is a switch the user cannot use.
        self._switch_row = QWidget()
        switch_row = QHBoxLayout(self._switch_row)
        switch_row.setContentsMargins(0, 0, 0, 0)
        switch_row.addSpacing(24)
        switch_row.addWidget(self._match_case)
        switch_row.addWidget(self._whole_word)
        switch_row.addWidget(self._in_selection)
        switch_row.addStretch(1)

        self._replace_row = QWidget()
        second_row = QHBoxLayout(self._replace_row)
        second_row.setContentsMargins(0, 0, 0, 0)
        second_row.addSpacing(24)
        second_row.addWidget(self._replace, 1)
        second_row.addWidget(self._replace_button)
        second_row.addWidget(self._replace_all_button)

        rows = QVBoxLayout(self)
        rows.setContentsMargins(4, 3, 4, 3)
        rows.setSpacing(2)
        rows.addWidget(self._field_row)
        rows.addWidget(self._switch_row)
        rows.addWidget(self._replace_row)
        # Hidden rather than removed from the layout: a widget that is not visible
        # takes no room, and the editor must not keep a gap where a row used to be.
        self._replace_row.setVisible(False)
        # «Maximum»: the size hint is the ceiling.  With the default policy the
        # layout shared the window's spare height with the editor, so the strip was
        # as tall as the program pane and the search ate half of the window.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setVisible(False)

    def _lens(self) -> QLabel:
        """The picture at the left, so the strip reads as «поиск» at a glance."""
        label = QLabel()
        picture = assets.icon(actions.FIND_ICON)
        if picture is not None:
            label.setPixmap(picture.pixmap(16, 16))
        return label

    def _picture_button(self, key: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setToolTip(tooltip)
        icon = assets.icon(actions.BY_KEY[key].icon or "")
        if icon is not None:
            button.setIcon(icon)
        else:  # a picture that is not drawn yet must not leave an empty button
            button.setText(tooltip.split(" (")[0])
        return button

    # -- what the window asks ----------------------------------------------
    def needle(self) -> str:
        return self._find.text()

    def replacement(self) -> str:
        return self._replace.text()

    def find_field(self) -> QLineEdit:
        """The question field — what a test types into, and what `Enter` runs in."""
        return self._find

    def replace_field(self) -> QLineEdit:
        return self._replace

    def field_row(self) -> QWidget:
        """The row of the field and its buttons; the other rows sit under it."""
        return self._field_row

    def switch_row(self) -> QWidget:
        """The row of the three switches, under the field."""
        return self._switch_row

    def replace_row(self) -> QWidget:
        """The row of «Заменить на», shown by the «Замена» button."""
        return self._replace_row

    def switch_boxes(self) -> tuple[QCheckBox, ...]:
        """The switches themselves, so a test can see which row holds them."""
        return (self._match_case, self._whole_word, self._in_selection)

    def match_case(self) -> bool:
        return self._match_case.isChecked()

    def whole_word(self) -> bool:
        return self._whole_word.isChecked()

    def only_in_selection(self) -> bool:
        return self._in_selection.isChecked()

    def options(self) -> search.Options:
        """The switches as the search engine wants them (the span is the window's)."""
        return search.Options(match_case=self.match_case(), whole_word=self.whole_word())

    def set_needle(self, text: str) -> None:
        """Fills the question field without starting a search of its own."""
        self._quiet = True
        try:
            self._find.setText(text)
            # Selected, so typing the next question replaces this one — and so the
            # word `Ctrl+F3` found is visibly the one being searched for.
            self._find.selectAll()
        finally:
            self._quiet = False

    def set_only_in_selection(self, enabled: bool) -> None:
        """Sets the switch the way a click does: the window hears about it."""
        self._in_selection.setChecked(enabled)

    def uncheck_only_in_selection(self) -> None:
        """Puts the switch back without telling the window.

        The window switches it *off* itself when there is nothing selected, and a
        signal there would only be that refusal coming back to it.
        """
        self._quiet = True
        try:
            self._in_selection.setChecked(False)
        finally:
            self._quiet = False

    def set_match_case(self, enabled: bool) -> None:
        self._match_case.setChecked(enabled)

    def set_whole_word(self, enabled: bool) -> None:
        self._whole_word.setChecked(enabled)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def status_text(self) -> str:
        return self._status.text()

    def show_replace(self, visible: bool) -> None:
        self._replace_row.setVisible(visible)
        if visible:
            self._replace.setFocus()
        else:
            self._find.setFocus()

    def replace_visible(self) -> bool:
        return not self._replace_row.isHidden()

    def focus_find(self) -> None:
        self._find.setFocus()
        self._find.selectAll()

    # -- internals ---------------------------------------------------------
    def _on_find_text(self, _text: str) -> None:
        if not self._quiet:
            self.changed.emit()

    def _on_switch(self, _checked: bool) -> None:
        if not self._quiet:
            self.changed.emit()

    def _on_span_toggled(self, checked: bool) -> None:
        if not self._quiet:
            self.spanToggled.emit(checked)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """`Esc` closes the bar from the switches and the buttons as well."""
        if event.key() == Qt.Key.Key_Escape:
            self.closeRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
