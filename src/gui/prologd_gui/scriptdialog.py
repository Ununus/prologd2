"""The settings of «Сконвертировать картинку…» — the boxes that become arguments.

One dialog, one job: collect what `tools/image_to_pld.py` takes on its command line
and hand it back as a list of strings.  Nothing here runs the tool or knows about
tabs — the window does that (`MainWindow.convert_image`), which is also what keeps
this file testable without a modal box: `arguments()` is a pure read of the fields.

The name is the atom the facts are written with (`картинка(имя, …)`), so it is
checked as one: letters, digits and the underscore.  The grid is not a field of its
own any more: it follows from the picture's size and the two cell sizes, and the dialog
shows what they come to before anything runs.
"""

from __future__ import annotations

import pathlib
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import scripts

#: What a picture name may hold: it is an atom of the generated program.
ATOM = re.compile(r"^[\wА-Яа-яЁё]+$")

#: The file kinds a reader is likely to have; the tool reads whatever Qt reads.
FILTER = "Картинки (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*)"

#: One line of explanation per field, shown both on the label and on the field:
#: the words a reader would otherwise look for in the tool's `--help`.
HINTS = {
    "image": (
        "Файл картинки: PNG, JPEG, BMP или GIF.  Имя для фактов возьмётся из имени "
        "файла, если поле «Имя» ещё пустое."
    ),
    "name": (
        "Имя атома в фактах `картинка(Имя, ...)`; оно же попадёт в вопрос "
        "`?нарисовать_картинку(Имя).`  Допустимы буквы, цифры и подчёркивание."
    ),
    "size": (
        "Сколько пикселей картинки в одной клетке.  Сетка не задаётся числом клеток: "
        "она следует из размера картинки, так что пропорции сохраняются.  Мельче "
        "клетка — точнее рисунок, но больше прямоугольников и фактов."
    ),
    "canvas_cell": (
        "Сколько точек холста занимает одна клетка.  `авто` подбирает так, чтобы "
        "длинная сторона картинки заняла около 600 точек, а короткая не стала меньше "
        "16 — предела ХОЛСТ."
    ),
    "colors": (
        "Сколько цветов остаётся после сжатия палитры (медианное сечение).  "
        "Больше цветов — точнее оттенки, но больше прямоугольников и фактов."
    ),
    "tolerance": (
        "Насколько пиксель должен отличаться от фона, чтобы считаться «чернилами» "
        "(по каждому каналу).  Больше порог — больше выпадает вместе с фоном."
    ),
    "coverage": (
        "Доля клетки, которая должна быть «чернилами», чтобы клетку рисовать.  "
        "Меньше доля — рисунок жирнее, больше — тонкие линии пропадают."
    ),
    "background": (
        "auto — фон определяется по самой картинке; иначе цвет через запятую: "
        "255,255,255.  Пиксели этого цвета (в пределах порога) не рисуются."
    ),
    "drop_background": (
        "Фон не попадает в рисунок: клетки цвета фона остаются пустыми, и картинка "
        "ложится на то, что нарисовано раньше."
    ),
}


#: The same rule as the tool's own `plan()` and `auto_canvas_cell()`: the dialog has to
#: say what the numbers will come to *before* anything runs.  `test_scripts.py` keeps
#: the two in step by running the tool and reading the `:- ХОЛСТ` it prints.
CANVAS_COMFORT = 600
MIN_CANVAS_CELL, MAX_CANVAS_CELL = 1, 32
MIN_CANVAS, MAX_CANVAS = 16, 2048


def picture_size(path: str) -> tuple[int, int] | None:
    """The picture's width and height, or None when the file cannot be read."""
    image = QImage(path)
    return None if image.isNull() else (image.width(), image.height())


def auto_canvas_cell(cols: int, rows: int) -> int:
    """How many dots a cell should take so the picture fills the canvas it is shown on."""
    long_side, short_side = max(cols, rows), min(cols, rows)
    roomy = CANVAS_COMFORT // long_side
    enough = -(-MIN_CANVAS // short_side)  # ceil: the short side has to reach 16 dots
    return max(MIN_CANVAS_CELL, min(MAX_CANVAS_CELL, max(roomy, enough)))


class ImageToPldDialog(QDialog):
    """The fields of the converter: a picture, its name, two cells and four knobs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сконвертировать картинку")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Картинка переводится в факты `картинка(Имя, X1, Y1, X2, Y2, Цвет).`: "
                "что программа потом рисует.",
                self,
            )
        )
        form = QFormLayout()
        # The picture: a line to paste into and a button for the usual way.
        self._image = QLineEdit(self)
        self._image.setPlaceholderText("путь к файлу картинки")
        browse = QPushButton("Обзор…", self)
        browse.clicked.connect(self._choose_file)
        browse.setToolTip("Выбрать файл картинки на диске")
        row = QHBoxLayout()
        row.addWidget(self._image, 1)
        row.addWidget(browse)
        holder = QWidget(self)
        holder.setLayout(row)
        self._add_row(form, "Картинка:", holder, HINTS["image"])
        self._image.setToolTip(HINTS["image"])
        # The name: the atom of the generated facts, filled from the file name.
        self._name = QLineEdit(self)
        self._name.setPlaceholderText("имя")
        self._add_row(form, "Имя:", self._name, HINTS["name"])
        self._cell = QSpinBox(self)
        self._cell.setRange(1, 64)
        self._cell.setValue(16)
        self._cell.setSuffix(" px")
        self._add_row(form, "Клетка картинки:", self._cell, HINTS["size"])
        self._canvas_cell = QSpinBox(self)
        self._canvas_cell.setRange(0, MAX_CANVAS_CELL)
        self._canvas_cell.setValue(0)  # the minimum is drawn as «авто»
        self._canvas_cell.setSpecialValueText("авто")
        self._canvas_cell.setSuffix(" точек")
        self._add_row(form, "Клетка холста:", self._canvas_cell, HINTS["canvas_cell"])
        self._colors = QSpinBox(self)
        self._colors.setRange(2, 32)
        self._colors.setValue(6)
        self._add_row(form, "Цветов:", self._colors, HINTS["colors"])
        self._tolerance = QSpinBox(self)
        self._tolerance.setRange(0, 255)
        self._tolerance.setValue(24)
        self._add_row(form, "Порог фона:", self._tolerance, HINTS["tolerance"])
        self._coverage = QDoubleSpinBox(self)
        self._coverage.setRange(0.0, 1.0)
        self._coverage.setSingleStep(0.05)
        self._coverage.setDecimals(2)
        self._coverage.setValue(0.30)
        self._add_row(form, "Доля «чернил»:", self._coverage, HINTS["coverage"])
        self._background = QLineEdit("auto", self)
        self._add_row(form, "Фон:", self._background, HINTS["background"])
        # The switch the field answers to: no switch, no page to leave out.
        self._drop_background = QCheckBox("Отбрасывать фон", self)
        self._drop_background.setChecked(False)
        self._drop_background.setToolTip(HINTS["drop_background"])
        form.addRow(self._drop_background)
        layout.addLayout(form)
        # What the chosen numbers come to: the grid and the canvas, which nobody can
        # work out in their head from a picture size and two cells.
        self._plan = QLabel("", self)
        self._plan.setWordWrap(True)
        layout.addWidget(self._plan)
        self._hint = QLabel("", self)
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        # The roles give the layout; the words are ours (the translator Qt ships
        # with is not loaded, and «OK» is not what the rest of the window says).
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("ОК")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._image.textChanged.connect(self._refresh)
        self._name.textChanged.connect(self._refresh)
        self._cell.valueChanged.connect(self._refresh)
        self._canvas_cell.valueChanged.connect(self._refresh)
        self._drop_background.toggled.connect(self._refresh)
        self._refresh()

    # -- what the window reads ---------------------------------------------
    def image(self) -> str:
        return self._image.text().strip()

    def name(self) -> str:
        return self._name.text().strip()

    def arguments(self) -> list[str]:
        """The converter's command line, without the script itself."""
        return scripts.image_arguments(
            self.image(),
            self.name(),
            cell=self._cell.value(),
            canvas_cell=self._canvas_cell.value() or "auto",
            drop_background=self._drop_background.isChecked(),
            colors=self._colors.value(),
            tolerance=self._tolerance.value(),
            coverage=self._coverage.value(),
            background=self._background.text().strip() or "auto",
        )

    # -- the fields --------------------------------------------------------
    def _add_row(
        self, form: QFormLayout, caption: str, field: QWidget, hint: str
    ) -> None:
        """A form row that explains itself: the hint is on the label and the field.

        Hovering a field is how a reader asks «а это что?», and the answer has to be
        at hand there; the label carries the same words, because that is what the
        eye lands on first.
        """
        label = QLabel(caption, self)
        label.setToolTip(hint)
        field.setToolTip(hint)
        form.addRow(label, field)

    def set_image(self, path: str) -> None:
        self._image.setText(str(path))
        if not self.name():
            self._name.setText(self._name_from(path))

    def _choose_file(self) -> None:
        chosen, _filter = QFileDialog.getOpenFileName(self, "Картинка", "", FILTER)
        if chosen:
            self.set_image(chosen)

    @staticmethod
    def _name_from(path: str) -> str:
        """The file's stem, cut down to what an atom may hold."""
        stem = pathlib.Path(path).stem
        cleaned = re.sub(r"\W+", "_", stem, flags=re.UNICODE).strip("_")
        return cleaned or "картинка"

    def _refresh(self) -> None:
        """OK is allowed only when the picture, its name and the grid all hold.

        The summary under the form says what the numbers come to — the grid the picture
        makes and the canvas it will be drawn on — and when they cannot work out, that
        line stays empty and `_hint` says why instead.
        """
        path = self.image()
        problems = []
        size = None
        if not path:
            problems.append("не выбрана картинка")
        elif not pathlib.Path(path).is_file():
            problems.append(f"нет файла: {path}")
        else:
            size = picture_size(path)
            if size is None:
                problems.append(f"картинка не читается: {path}")
        if not self.name():
            problems.append("не указано имя")
        elif not ATOM.match(self.name()):
            problems.append("в имени допустимы только буквы, цифры и подчёркивание")
        summary = ""
        if size is not None:
            summary, wrong = self._grid(*size)
            if wrong:
                problems.append(wrong)
        # Everything about the page goes grey with it: a threshold, an ink share and a
        # colour are all answers to «what is the background», and there is none.
        self._tolerance.setEnabled(self._drop_background.isChecked())
        self._coverage.setEnabled(self._drop_background.isChecked())
        self._background.setEnabled(self._drop_background.isChecked())
        self._plan.setText(summary)
        usable = not problems
        button = self.findChild(QDialogButtonBox)
        if button is not None:
            button.button(QDialogButtonBox.StandardButton.Ok).setEnabled(usable)
        self._hint.setText("; ".join(problems))

    def _grid(self, width: int, height: int) -> tuple[str, str]:
        """What the settings come to, and what is wrong with it — empty when fine.

        The summary is built even when the numbers cannot work: «холст 8×8» next to
        «сторона 8 вне пределов 16..2048» says what to change, while an empty line
        only says that something is wrong.
        """
        cell = self._cell.value()
        cols, rows = width // cell, height // cell
        if cols < 1 or rows < 1:
            return "", f"картинка {width}×{height} меньше клетки {cell} px"
        canvas_cell = self._canvas_cell.value() or auto_canvas_cell(cols, rows)
        width_dots, height_dots = cols * canvas_cell, rows * canvas_cell
        summary = f"Сетка {cols}×{rows} клеток, холст {width_dots}×{height_dots} точек"
        lost = (width - cols * cell, height - rows * cell)
        if lost != (0, 0):
            summary += f"; по краям отброшено {lost[0]}×{lost[1]} px"
        for side in (width_dots, height_dots):
            if not MIN_CANVAS <= side <= MAX_CANVAS:
                return summary, (f"сторона холста {side} вне пределов "
                                 f"{MIN_CANVAS}..{MAX_CANVAS}")
        return summary, ""
