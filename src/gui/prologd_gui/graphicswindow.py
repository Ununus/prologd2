"""The window the graphics predicates draw into (task_45).

The picture itself lives in `prologd_gui.graphics` (a `Canvas`: values, not Qt),
and this module is the Qt half: a widget that shows the buffer, a small toolbar,
and the rules of the window — how a pixel becomes a screen pixel at a given zoom,
what the mouse says about a cell, and how the picture is saved.

Why a window of its own, and not a panel next to the editor: that is what the
menu entry has said since task_15, it can go to a second screen, and it must not
compete for space with the code the student is writing.
"""

from __future__ import annotations

import pathlib

from PySide6.QtCore import QByteArray, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import graphics

#: The text of the coordinate label while the pointer is off the picture.
NO_CELL = "вне экрана"


class CanvasView(QWidget):
    """Paints a `graphics.Canvas` as pixels, scaled to fit by default.

    The buffer the canvas holds is handed to a `QImage` without copying, so a
    primitive costs a few writes and one repaint — that is what makes an
    animation (`examples/lessons/lesson_12`) follow the program rather than lag
    behind it.
    """

    #: The cell under the pointer, or None: `(x, y, value)`.
    hovered = Signal(object)

    def __init__(self, canvas: graphics.Canvas, parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._fit = True
        self.setMouseTracking(True)
        self.setMinimumSize(96, 72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # -- what and how ------------------------------------------------------
    def canvas(self) -> graphics.Canvas:
        return self._canvas

    def fit(self) -> bool:
        """True while the picture is scaled to the window."""
        return self._fit

    def set_fit(self, fit: bool) -> None:
        self._fit = bool(fit)
        self.updateGeometry()
        self.update()

    def image(self) -> QImage:
        """The picture as an image, over the canvas' own buffer.

        `Format_RGBA8888` matches the byte order `graphics._rgba` writes, on any
        machine: the bytes are red, green, blue, alpha in that order, which is
        also what `QImage.save(..., "PNG")` wants.
        """
        canvas = self._canvas
        return QImage(canvas.rgba, canvas.width, canvas.height, QImage.Format.Format_RGBA8888)

    def scale(self) -> float:
        """How many widget pixels one cell takes."""
        canvas = self._canvas
        if not self._fit:
            return 1.0
        return min(
            self.width() / max(1, canvas.width),
            self.height() / max(1, canvas.height),
        )

    def picture_rect(self) -> QRect:
        """Where the picture stands inside the widget, centred."""
        canvas = self._canvas
        scale = self.scale()
        width = round(canvas.width * scale)
        height = round(canvas.height * scale)
        return QRect(
            (self.width() - width) // 2, (self.height() - height) // 2, width, height
        )

    def cell_at(self, point: QPoint) -> tuple[int, int] | None:
        """The cell a widget point stands on, or None when it is outside."""
        scale = self.scale()
        if scale <= 0:
            return None
        rect = self.picture_rect()
        x = int((point.x() - rect.x()) / scale)
        y = int((point.y() - rect.y()) / scale)
        if 0 <= x < self._canvas.width and 0 <= y < self._canvas.height:
            return x, y
        return None

    def sizeHint(self) -> QSize:
        if self._fit:
            return super().sizeHint()
        return QSize(self._canvas.width, self._canvas.height)

    def minimumSizeHint(self) -> QSize:
        if self._fit:
            return QSize(96, 72)
        return QSize(self._canvas.width, self._canvas.height)

    # -- drawing -----------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        rect = self.picture_rect()
        if rect.isEmpty():
            return
        # Nearest neighbour: the picture is pixel art, and a smoothed line at a
        # fractional zoom is a line that no longer stands where the program put
        # it (the engine's `getPixel` would disagree).
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(rect, self.image())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        cell = self.cell_at(event.position().toPoint())
        if cell is None:
            self.hovered.emit(None)
            return
        x, y = cell
        self.hovered.emit((x, y, self._canvas.pixel(x, y)))

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        self.hovered.emit(None)


class GraphicsWindow(QWidget):
    """The picture of the current session, in a window of its own."""

    #: The user closed the window: the main window hides it and remembers that.
    closed = Signal()

    def __init__(self, canvas: graphics.Canvas, parent=None) -> None:
        super().__init__(parent)
        # A window of its own that the main window owns: without the flag a
        # QWidget with a parent is a *child* widget, and the picture would be
        # embedded in the editor instead of standing beside it (task_45 asks for
        # a window, so it can go to a second screen).
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowTitle("Графическое окно")
        self._canvas = canvas
        self._view = CanvasView(canvas, self)
        self._view.hovered.connect(self._show_cell)

        self._toolbar = QToolBar("Рисунок", self)
        self._fit_action = self._toolbar.addAction("Вписать в окно")
        self._fit_action.setCheckable(True)
        self._fit_action.setChecked(True)
        self._fit_action.setToolTip("Показывать весь экран 1024×768 целиком")
        self._fit_action.toggled.connect(self._set_fit)
        self._scale_action = self._toolbar.addAction("1 : 1")
        self._scale_action.setToolTip("Одна точка программы — один пиксель на экране")
        self._scale_action.triggered.connect(lambda: self._set_fit(False))
        self._toolbar.addSeparator()
        clear = self._toolbar.addAction("Очистить")
        clear.setToolTip(
            "Стереть рисунок в окне; экран интерпретатора чистит сама программа"
        )
        clear.triggered.connect(self.clear_picture)
        save = self._toolbar.addAction("Сохранить как PNG…")
        save.setToolTip("Сохранить рисунок в файл")
        save.triggered.connect(self.save_png_dialog)
        self._cell = QLabel(NO_CELL, self)
        self._toolbar.addWidget(self._cell)

        self._scroll = QScrollArea(self)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._view)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._scroll, 1)
        self.resize(720, 560)

    # -- the picture -------------------------------------------------------
    def canvas(self) -> graphics.Canvas:
        return self._canvas

    def view(self) -> CanvasView:
        """The widget that paints the picture (tests look at it directly)."""
        return self._view

    def refresh(self) -> None:
        """Repaints the picture after the canvas changed.

        The view's size is checked as well: a snapshot may arrive at a size of
        its own, and in the actual-size mode the widget has to match it or the
        scroll area would be laid out for the old picture.
        """
        if not self._fit_action.isChecked():
            self._view.setMinimumSize(self._canvas.width, self._canvas.height)
            self._view.setMaximumSize(self._canvas.width, self._canvas.height)
        self._view.update()

    def clear_picture(self) -> None:
        """Clears what is *shown*.

        The interpreter's own screen is not touched: there is no request for
        that, and there should not be one — the screen belongs to the program,
        and a program that wants a clean one starts with `ТОЧКА(X, Y, Цвет)`.
        The next run starts a fresh interpreter, and the window clears with it.
        """
        self._canvas.clear()
        self.refresh()

    def _show_cell(self, cell) -> None:
        if cell is None:
            self._cell.setText(NO_CELL)
            return
        x, y, value = cell
        self._cell.setText(f"x={x} y={y} цвет={value}")

    def _set_fit(self, fit: bool) -> None:
        """One cell per pixel, or the whole screen in the window."""
        self._fit_action.setChecked(bool(fit))
        self._scroll.setWidgetResizable(bool(fit))
        self._view.set_fit(bool(fit))
        if fit:
            self._view.setMinimumSize(96, 72)
            self._view.setMaximumSize(16777215, 16777215)
        else:
            # Actual size: the picture is 1024×768, and the scroll area is what
            # moves over it.
            self._view.setMinimumSize(self._canvas.width, self._canvas.height)
            self._view.setMaximumSize(self._canvas.width, self._canvas.height)
        self.refresh()

    # -- saving ------------------------------------------------------------
    def save_png(self, path: str) -> bool:
        """Writes the picture to `path` as PNG; False when Qt refused."""
        return bool(self._view.image().save(str(path), "PNG"))

    def save_png_dialog(self) -> None:
        """«Сохранить как PNG…»: asks for a file and writes it."""
        suggested = str(pathlib.Path.home() / "рисунок.png")
        path, _filter = QFileDialog.getSaveFileName(
            self, "Сохранить рисунок", suggested, "PNG (*.png)"
        )
        if path:
            self.save_png(path)

    # -- the window itself -------------------------------------------------
    def geometry_text(self) -> str:
        """The geometry as text, for the settings file (machine key)."""
        return bytes(self.saveGeometry().toBase64()).decode("ascii")

    def restore_geometry(self, text: str) -> None:
        """Puts the window back where it was; junk in the file is ignored."""
        if not text:
            return
        try:
            self.restoreGeometry(QByteArray.fromBase64(text.encode("ascii")))
        except (ValueError, TypeError):
            pass

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """Closing hides: the picture is kept, and the action turns itself off."""
        event.ignore()
        self.hide()
        self.closed.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt spelling
        """`Esc` closes the picture — the first thing in the window's order (task_48).

        The window has a focus of its own (it can stand on a second screen), so the
        main window's `Esc` handler never sees this key: the picture is what the
        reader is looking at, and closing it is what `Esc` means there.  Going
        through `close()` and not `hide()` keeps the two ways out the same one:
        the main window is told, and its entry turns itself off.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)
