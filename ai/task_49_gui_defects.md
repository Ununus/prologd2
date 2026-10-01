# task_49 — Three defects and the live output

**Status:** not started
**Depends on:** task_28 (stepping and the polite stop), task_29 (the session
restore and its storage), task_02 of the front-end (the output pane), task_46
(protocol 9, the run limits)
**Milestone:** M17

## Goal

Four things the user ran into while working with the window.  Three are defects
with a clear reproduction; the fourth is the reason a lesson's animation looks
like a jump instead of a countdown.

## The defects (found 2026-10-01)

### 1. `Шаг` → `Стоп` → `Запуск` answers «нет шага, который ждёт ответа»

The window's word for «the run is paused at a step point» survives a stop, so
`Запуск` goes down the «продолжить» path (`run_program` → `step_continue`) and
sends a `step` request into an interpreter that is not paused — the session prints
exactly that error and the program never runs.  The state is the *session's*
(`PrologSession._paused`), and the event that proves a pause is over is the one
that concludes the run: `result`, `loaded`, or the process ending.  Those are the
places the flag has to be cleared, and a test has to walk the whole sequence
(`Шаг`, `Стоп`, `Запуск`) rather than the parts.

### 2. Two unnamed tabs: the restored one is marked as changed

With one unnamed tab the window comes back clean, with two the surviving one comes
back `*изменённый`.  The stored session skips an *empty* unnamed tab (task_29's
rule) and remembers the rest by text; the restore marks every unnamed tab as
unsaved work.  Which of the two rules is wrong is what the reproduction decides:
what a user answered «не сохранять» about must not come back, but a tab that came
back *with its text* is unsaved work and must be asked about on the way out.  The
bug is in the *pairing* of names, texts and the current tab — the record's name,
the fresh name from `untitled_name()` and the `session_current` key are three
names for two tabs.

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

- [ ] `PrologSession`: the paused flag is cleared by the events that conclude a
      run, and `window.py`'s «продолжить» paths stop assuming it.
- [ ] `documents`/`window.py`: the restore pairs each record with *its* tab — name,
      text and which one was current — and the rule about empty unnamed tabs is
      written down where it is applied.
- [ ] `panels.OutputPane` + `window.py`: the output is appended in batches (one
      append per event-loop turn, however many events arrived), and the trim
      happens on that batch.
- [ ] `IoContext` + `protocol.cpp`: an output-line hook, and the session emitting
      an `output` event per completed line inside a run.
- [ ] Tests for all four, each with the reproduction the user gave.

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

## Tests

- [ ] `test_window.py`: `Шаг` → `Стоп` → `Запуск` runs the program (no «нет шага,
  который ждёт ответа» in the pane, and the answer of the program arrives).
- [ ] `test_window.py`/`test_settings.py`: two unnamed tabs — what comes back, what
  their names are, which one is current, and what the close questions ask about.
- [ ] `test_output.py`/`test_window.py`: 5 000 output lines arrive in one piece;
  a trace of a deep recursion leaves the window alive (a bounded time is enough —
  the point is that it finishes).
- [ ] `test_window.py`: a program that prints three lines with `ЖДИ` between them
      shows them as they are produced — the pane holds the first line while the
      run is still going.
- [ ] `protocol_session.cmake`: the session emits `output` per line while a load
      is still running.

## Acceptance

The three reproductions behave, the countdown counts, and a long trace no longer
takes the window with it.
