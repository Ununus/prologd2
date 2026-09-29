# task_27 — GUI: output pane, input pane and window layout

**Status:** in progress — the window layout (the movable output panel) and the
output pane itself are done; the input console is **deliberately postponed** (the
user wants to think it over), and saving the pane to a file is still open
**Depends on:** task_21
**Milestone:** M11

## Goal

The two panes the user asked for: a program output pane that can sit under the
editor or to its right, and a real input pane for `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД`
instead of only a modal dialog.

## Deliverables

- [x] `prologd_gui/panels.py` — `OutputPane(QPlainTextEdit)`:
  * read-only, monospace, `NoWrap`, selectable and copyable;
  * colours by kind: program output plain, query echo `#0A22D6`, diagnostics
    crimson, trace grey — the reference GUI did the same with `appendHtml`;
  * arbitrary text arrives in chunks (`output` events), so colouring is applied
    by *line*, not by HTML, and a partial line is not lost;
  * **Очистить вывод**, save the pane to a text file, copy selection;
  * a line/byte limit (setting, default e.g. 50 000 lines) that drops the oldest
    lines with a visible "вывод усечён" marker — a runaway `ВЫВОД` must not eat
    the machine;
  * "следить за выводом" auto-scroll that stops when the user scrolls up.
- [ ] `InputPane` — the console the reference GUI had: a label showing what is
      asked, a one-line editor for `token`/`codepoint` and a multi-line area for
      `line`, plus an "Отправить" button; it answers the pending
      `input_request` with `{"cmd":"input","text":…}`.
- [ ] Input mode setting: **панель ввода** (default) or **диалоги** (the modal
      dialogs the skeleton has today).  Whichever is active, the *kind* of the
      request decides the widget, and an unanswered request must be visible in
      the status bar.
- [x] Layout: a `QSplitter` with the editor(s) and an *output container*; the
      container is vertical (output over input) and can be moved to the right
      side of the window:
  * **Панель вывода** `F4` shows/hides it;
  * **Сменить ориентацию сплита** `Ctrl+F4` moves it between bottom and right —
    the same pair of commands the reference GUI had
    (`changeSplitOrientation`), but implemented as one splitter whose
    *orientation* changes (editor first either way): side by side on the right,
    stacked at the bottom;
  * the chosen side and the sizes of both splitters are persisted
    (`view/output_position`, `view/output_visible`, `view/panel_sizes`,
    `view/output_sizes`) and restored on start — the settings store of task_22
    was already there, so this needed no task_29;
  * `childrenCollapsible` is off and both halves have a minimum size, so a pane
    cannot be collapsed to nothing (a panel squeezed to zero pixels looks like a
    lost window).
- [x] Status bar: interpreter state (запущен/остановлен/выполняется), line and
      column of the caret, current file's encoding/eol, last exit code.
- [x] Tests: the pane logic that is text-based (colour classification of an
      output chunk, truncation) lives in a Qt-free helper and is covered by
      `src/gui/tests/test_output.py`; the layout goes into the manual checklist.

## Progress

Done in this round (2026-09-29):

* the layout half of the task, as ticked above.  The output and the input queue
  travel together as one `_sidebar` splitter inside `_panel_splitter`; `F4`
  (checkable, `_toggle_output`) and `Ctrl+F4` (`flip_output_position`) are wired,
  the four settings keys above carry the state, and `_save_panel_state` runs on
  close (next to `_save_split_state`).
* `test_window.py`: `test_the_output_panel_moves_and_hides` — the position turns,
  the input queue goes with the panel, `F4` hides rather than loses it, a pane
  cannot be dragged to zero, and a *new* window built on the same settings file
  comes back with the panel at the bottom.

Still open: saving the pane to a text file, the input *console* mode as an
alternative to the modal dialogs (the user asked to postpone that one), the rest of
the pane furniture the reference GUI had, and a paragraph in `doc/gui.typ`, §6,
about what the run state means (the README has it).

Done in the third round (2026-09-29): the run state was split in two — the process
being *up* and a computation being *in flight* — and the window no longer starts an
interpreter just by opening: it comes up with the first run or with a query typed
into the query line.  `Запустить` is enabled while nothing is computing (the answer
frees it, and the next press restarts the whole file), `Остановить` while the
process is alive, and the stop says which of the two it interrupted:
`--- остановлено ---` for a computation, `--- база знаний выгружена ---` for an idle
interpreter.  The load note became `--- загрузка базы знаний ---`, the status bar
says `выполняется` / `база знаний загружена` / `интерпретатор остановлен`, and
`test_window.py` checks the whole walk: nothing running → run → answer → stop (idle)
→ run → stop (in flight).

Done in the second round (2026-09-29):

* `panels.py` — `LineBuffer` (Qt-free: chunks split into lines, the unfinished
  tail held, and a change of kind closing the held line) and `OutputPane` (colours
  by kind from `KIND_COLORS`, a plain-text cursor so the user's own selection is
  left alone, a 50 000-line limit dropped in one edit with `TRUNCATED_MARK` kept
  as the first line, and auto-scroll that follows the end until the user scrolls
  up — and again as soon as they come back down).
* The window feeds the pane by kind: the program's output plain, its own notes
  grey, the echo of an answer in the query blue, and diagnostics crimson;
  `clear_output` resets the pane (tail included), and the end of a run flushes the
  half-line a program left behind.
* The status bar carries the interpreter's state, the caret's line and column (the
  pane forwards `cursorPositionChanged`), the file's line ending and encoding, and
  the last exit code.
* `run` and `stop` follow the session (`_sync_run_actions`), and «Переносить
  длинные строки» is the *editor's* switch — the output never wraps.
* Tests: `test_output.py` (five checks, among them the truncation marker and the
  follow behaviour) and three more in `test_window.py` (run state, wrap switch,
  undo per tab).
## Design notes

* The output pane already exists (read-only `ZoomablePlainTextEdit`), the query
  line is under the editor and the **input queue** is under the output — see
  `doc/gui.typ`, section 6.1, and `window._on_input_request`.  What is missing is
  docking, tabs and a per-pane toolbar, plus choosing where the output goes: it is
  arranged by plain `QSplitter`s (editor | output-over-input) with no way to move
  it.  The font size is shared with the editor on purpose (task_29 splits it).
* Everything about the panes is presentation, so nothing here may require an
  interpreter change: `output`, `error` and `input_request` events already carry
  all the information (task_21).
* Splitting an output chunk into lines with a kept remainder is the classic bug
  in this code: keep the tail of the buffer explicitly, or the last partial
  `ВЫВОД` line disappears from the window.
* Truncation must be cheap: drop whole lines from the front in one
  `QTextCursor` edit, never re-set the whole document text per chunk.

## Acceptance

`ВЫВОД` output appears as it arrives, diagnostics are red, the query echo is
blue, the pane can be moved between the bottom and the right side with `Ctrl+F4`
and hidden with `F4`, `ВВОДСТР` is answered from the input pane, and a program
printing a million lines leaves the window responsive with a truncated pane.
