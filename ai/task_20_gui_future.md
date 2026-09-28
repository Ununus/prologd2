# task_20 — GUI boundary (superseded)

**Status:** superseded by ADR-014; the work continues in `task_21_gui_pyside.md`
**Depends on:** task_15, task_16
**Milestone:** post-M10

## Goal

Keep a clean seam so the original Qt GUI (previous implementation,
<https://github.com/Ununus/prologd>) can be rebuilt on top of the new core
without touching the interpreter.

## Already provided by earlier tasks

- `GraphicsBackend` interface (task_15) with `NullGraphicsBackend` and
  `RecordingGraphicsBackend`.
- `IIOStreams` / `IoContext` (task_11) so a GUI can supply dialogs for
  `ВВОДСИМД`/`ВВОДСТР`/`ВВОДЦЕЛ` (the original `InputStringFromDialog`) and
  capture `ВЫВОД`.
- Trace output goes through the output stream (task_07), so a GUI can show it
  in a pane.
- Engine run control (`shouldStop`) so a GUI can offer an Abort button
  (the original `EnableRunning`).

## Future deliverables (not in scope now)

- Qt 6 front-end reusing `MainWindow`, `Editor`, `Highlighter`, `Actions`.
- `QGraphicsBackend : GraphicsBackend` using `QPainter`.
- `DialogIo : IIOStreams` for interactive input.
- Settings persistence, syntax highlighting rules generated from the lexer's
  keyword set (`doc/help.typ` keyword table).
- Packaging for Windows and Linux.

## Constraint

Nothing in this task may require changes to `prlib` beyond adding an interface
implementation. If a core change is needed, record it in `decisions.md` first.
