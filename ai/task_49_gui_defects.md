# task_49 — Four defects and the live output

**Status:** done (2026-10-01)
**Depends on:** task_28 (stepping and the polite stop), task_29 (the session
restore and its storage), task_02 of the front-end (the output pane), task_46
(protocol 9, the run limits)
**Milestone:** M17

## Goal

Five things the user ran into while working with the window.  Four are defects
with a clear reproduction (the fifth came in with «продолжим task_49»); the last
item is the reason a lesson's animation looks like a jump instead of a countdown.

## The defects (found 2026-10-01)

### 1. `Шаг` → `Стоп` → `Запуск` answers «нет шага, который ждёт ответа»

The window's word for «the run is paused at a step point» survives a stop, so
`Запуск` goes down the «продолжить» path (`run_program` → `step_continue`) and
sends a `step` request into an interpreter that is not paused — the session prints
exactly that error and the program never runs.  The state is the *session's*
(`PrologSession._paused`), and the event that proves a pause is over is the one
that concludes the run: `result`, `loaded`, an error, or the process ending.
Those are the places the flag has to be cleared, and a test has to walk the whole
sequence (`Шаг`, `Стоп`, `Запуск`) rather than the parts.  **What the reproduction
added**: with «Стоп» the process stays (the polite interrupt ends the *query*), so
the clearing event is the interrupted query's *error* — the reproduction failed
without that case, and the check says so by asserting the session is still
running.

### 2. Two unnamed tabs: the restored one is marked as changed

With one unnamed tab the window comes back clean, with two the surviving one comes
back `*изменённый`.  The stored session skips an *empty* unnamed tab (task_29's
rule) and remembers the rest by text; the restore marks every unnamed tab as
unsaved work.  **What the reproduction decided**: it is the restore that was
wrong — the tab the user never touched is the one that came back starred (the
welcome program of the first tab, with a second, empty tab beside it; the one-tab
case looked right only because an empty tab is not stored at all).  A session is
written *after* the closing questions have resolved every change, so a tab that
survives as text is one the user left alone: the record now says whether it was
unsaved work, and the flag is what the next start honours.

### 3. `Запустить с трассировкой` on a deep recursion freezes the window

A long trace is thousands of events, and the window appends each one to the output
pane as it arrives.  Windows offers to close the program: the GUI is not merely
slow, it is starved.  Two suspects, and the measurement will say which: the
per-event append (a document write and a repaint per line, with the pane's line
limit trimming on the way) or the pane's trimming rule itself.  The fix is to
append in *batches* — the session's decoder already hands over everything a read
produced, so the window can coalesce into one append per event-loop turn — and to
make the trimming cheap.

### 4. Output arrives only when the program is over

`ВЫВОД`, `ВЫВОД` + `ПС`, then `ЖДИ(1000)` — the countdown appears as one block at
the end instead of 3, 2, 1.  The session collects the engine's output in a buffer
and emits it once per *request* (`flush()` after `dispatch`), and a whole program
is one request: its own `?`-statements run inside the load.  The engine knows when
a line is complete (`ПС`, or the `\n` a `ВЫВОД` may carry), so the seam belongs
there: the I/O context gets a hook that says «a line ended», and the session turns
that into an `output` event.  The console build keeps the hook empty — its stream
is the terminal's business.

## Deliverables

- [x] `PrologSession`: the paused flag is cleared by the events that conclude a
      run (`result`, `loaded`, an `error` that is not a warning, the process
      ending — the last two are what a `Стоп` arrives as while a step waits, and
      the reproduction needed them: the polite stop ends the *query*, not the
      process).  `window.py`'s «продолжить» paths follow the flag, which is now
      true only while a step point is really waiting.
- [x] `documents`/`window.py`: the restore pairs each record with *its* tab — and
      what the reproduction decided is that the record carries the **unsaved**
      flag: with two unnamed tabs the untouched welcome program came back starred
      (`*Без имени`) and was asked about on the way out, while the one-tab case
      looked right only because an empty tab is not stored at all.  The record is
      JSON now (`path`, `name`, `text`, `modified`), because a fourth
      tab-separated field cannot be told apart from a task_29 line whose text
      contains a tab — and program text does contain tabs.
- [x] `panels.OutputPane` + `window.py`: the output is handed over in *batches*
      (one `feed` per run of one kind, on the next turn of the event loop) and the
      history is trimmed in *bulks* (a tenth of the limit).
- [x] `IoContext` + `protocol.cpp`: an output-line hook (`setOutputLineSink`,
      fired by `ПС` or by the `\n` a `ВЫВОД` carries), and the session answering it
      with `flush()` — so the program's output goes out as it is written.  The
      hook says *when*, never *what*: the owner takes the text from its own stream,
      which is why the console needs no change at all and why a program that
      redirected its output to a file reports nothing.
- [x] Tests for the first three and for the geometry, each with the reproduction
      the user gave.
- [x] `protocol_smoke.py` / `protocol_session.cmake`: one `output` event per
      written line, every line before the `loaded` that ends the load (and the
      two older expectations of the single-block shape updated — the text is the
      same, the granularity is finer).

### 5. The main window forgets its size and place (found 2026-10-01)

The user, in one sentence with "let us continue task_49": "the graphics window keeps
its size and position, while the main window does not".  The graphics
window has kept a `saveGeometry()` blob since task_45 and the main window — the one
the user moves first — kept nothing.  Both go through `prologd_gui.geometry` now,
and the key is `view/window_geometry` (a machine key: a record, not a row in the
dialog).

## Design notes

* The trace is *not* the only case: the same starvation waits in a program that
  prints in a loop, and in a `НАЙТИВСЕ` that prints every solution.  So the fix is
  in the way the window appends, not in a special case for trace lines.
* A batch is not a throttle: nothing is dropped or delayed by a timer — the
  window appends everything that arrived in the turn, and one repaint follows.
  A timer that samples the output would lose lines, and a lost line in a log is
  worse than a slow one.
* The line hook is about *lines*, not about flushing a stream: the engine's `ПС`
  and the `\n` of a `ВЫВОД` both end a line, and the front-end is the one that
  decides what to do with it (the console does nothing).

## What the measurement said (2026-10-01)

Defect 3 was two costs, and the second was the freeze:

| work | before | after |
|------|--------|-------|
| pane, 20 000 lines | 0.68 s (34 µs/line) | 0.26 s (13 µs/line) |
| pane, 200 000 lines with a 50 000-line limit | **21.9 s** (110 µs/line) | **3.0 s** (15 µs/line) |
| traced deep recursion, 16 002 trace lines (end to end) | 2.2 s | 0.6 s |

The `.26 s` of the first row is one `feed` per line — the window's batching (task_49)
removes the rest of it, because the *window* was paying a Python call per line and
the pane was paying one insertion per line.  The second row is the quadratic trim:
removing from the front of a `QTextDocument` costs about the same whatever is
removed, so one line per appended line is O(n²) — and that is what Windows
noticed (the window was busy, not slow).

A useful negative result: batching alone was *not* the answer (one append of
20 000 lines still cost 27 µs/line), and neither was the scrollbar (32 µs/line
with the follow switched off).  The cursor is not the cost either (a fresh
`QTextCursor` per insert costs 7 µs against 5 µs for a persistent one).  The
task file had guessed «the per-event append or the trimming»; the numbers said
«both, and the trimming is the one that explodes».

## Tests

- [x] `test_window.py`: `Шаг` → `Стоп` → `Запуск` runs the program (and the
      process is still alive after the stop, so the pause cannot have been cleared
      by the session ending).
- [x] `test_window.py`: two unnamed tabs — the untouched one comes back clean, and
      the stored record says so; `test_documents.py` covers the record's shape,
      the flag, and a task_29 line read the old way.
- [x] `test_output.py`/`test_window.py`: the history is bounded in bulks and comes
      to its limit on request; 20 000 lines queued through the window arrive in
      one batch and none of them is lost, and a traced recursion of 1 200 steps
      arrives in bounded time.
- [x] `test_window.py`: the window comes back with the size and the place it was
      closed at, and starts at the default when nothing is remembered.
- [x] `test_window.py`: a program that prints three lines with `ЖДИ` between them
      shows them as they are produced — the pane holds the first line while the
      run is still going, and not the third.
- [x] `test_io_context.cpp`: the hook fires at a line end (`ПС`, or a `\n` inside a
      `ВЫВОД`) and not for a line that is still open, and a context without a sink
      is silent.
- [x] `protocol_smoke.py`/`protocol_session.cmake`: see the deliverable above.

## What the live output measured (2026-10-01)

A program that prints three lines with `ЖДИ(60)` between them:

| | events |
|---|---|
| before | `loaded@0.15`, then **one** `output@0.15` with all three lines |
| after | `output@0.01`, `output@0.08`, `output@0.14`, `loaded@0.14` |

The console prints byte for byte what it always did (`one\ntwo\nthree\nДА\n`): the
hook is unset there, and the text does not depend on who is reading it.

## Acceptance

The four reproductions behave (the step runs again, the untouched tab comes back
clean, a long trace no longer takes the window, the window returns where it was),
the countdown counts, and a long trace no longer takes the window with it.
