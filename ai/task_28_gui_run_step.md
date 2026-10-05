# task_28 — GUI: run, step, stop, error line, input

**Status:** done — running, stepping (`F10`/`Shift+F10`/`F5`), the trace, the error
line with its position, and input were already partly in from task_27 and are now
complete; the engine seam, the protocol additions and the tests are in.  The one
item left open on 2026-09-29 — «Остановить» ask-first — landed on 2026-10-01
(`interrupt`, `STOP_GRACE_MS`, the run-vs-unload split); see the note at the end.
**Depends on:** task_22, task_25, task_27
**Milestone:** M11

## Goal

Execution from the window: run the whole program, run it step by step, stop a
program that has run away, show where an error happened, and answer the
interpreter's questions.

## Deliverables

Run

- [x] **Запуск** `F5`: push the current buffer into the session and run its
      queries and directives; output goes to the output pane with the query echo
      (task_27).  *How* the buffer is loaded decides what `ИМПОРТ` sees, and that
      is not obvious, so it is spelled out here:

      | What is in the tab | Request | `ИМПОРТ("lib/x.pld")` resolves against |
      |---|---|---|
      | a saved file, unmodified | `{"cmd":"load","path":…}` | the file's own directory |
      | a saved file, modified | `{"cmd":"load","text":…,"name":"<the file path>"}` | the file's own directory — `name` is what the loader treats as the importing path |
      | «Без имени N» | `{"cmd":"load","text":…,"name":"Без имени N"}` | the process working directory, then every `-I` directory |

      The second row is the interesting one: the text comes from the editor but
      the identity comes from the path, so `F5` on a dirty buffer behaves exactly
      like `prologd -s file.pld` and the diagnostics point at the real file.

      The *working folder* (task_29) is passed as `-I` for every session, so it
      is searched whether or not the buffer has been saved: a saved file simply
      gains its own directory as the first candidate, and nothing is lost by
      saving an untitled buffer.  When an import is not found at all, the
      interpreter names the directories it tried (task_32) and the GUI shows that
      text verbatim.
- [x] "Сохранять перед запуском" stays available as an option (the reference GUI
      had it), but it is no longer needed for imports to resolve.
- [x] **Запуск с трассировкой**: the same with the trace enabled, so the
      reference-style trace text appears in the pane (grey).
- [x] Restart policy: **every run starts a fresh interpreter process** and clears
      the output pane.  The clause database, the RNG seed and file redirection all live in
      the process, so a reused session
      accumulates clauses and prints every solution twice — found by hand in the
      skeleton, where a second **Запустить** doubled the output.  A tab switch, a
      run after a stop and a crashed child also start fresh; one session is kept
      for the queries that belong together.  Setting (task_29): «не сбрасывать
      перед запуском» for a REPL-like workflow, off by default.  The status bar
      always shows which state the session is in.

Stop

- [x] **Остановить** `Shift+F5`: send `interrupt` first (it works while the
      interpreter waits for input and between commands), and if the query is
      still running after a short grace period, terminate the child and start a
      new session — exactly the note in `src/gui/README.md`, which is why the
      button cannot be a polite signal alone.
- [x] The editor must stay responsive while a query runs: all interpreter I/O
      happens on the `QProcess` signals, never in a blocking call from the UI
      thread.

Error line

- [x] Protocol v2: `error` events carry structured position fields
      (`file`, `line`, `column`) next to the human `message`, so the GUI does
      not parse `file:line:column:` out of the text.  Parse diagnostics already
      have the location; **verify that runtime errors carry one too** — a
      runtime error is raised through `raiseAt(code, location, …)` and clauses
      keep their `SourceLocation`, so if any runtime path loses the position,
      fix it there and cover it with a test.
- [x] The editor marks the reported line: red background plus a marker in the
      line-number area, the caret moves there, and the mark is cleared on the
      next run or on edit.  A parse error marks the line too (the offset *is*
      the column).
- [x] Diagnostics from `ИМПОРТ`ed files carry that file's name; the GUI opens
      the file in a tab if it is not open yet (or says where it is, if the path
      is outside the project).

Step by step

- [x] `prlib`: `EngineOptions::stepHook`, the same shape as `externalStop`:
      a `std::function` called by the solver at the four points it already
      traces (call, exit, redo, fail) with a `StepInfo {action, goal text,
      depth, location}` and returning `continue / pause / stop`.  Null by
      default, so the cost when not stepping is one branch.  It must be safe to
      call from the solver's own loop and must not be a signal handler.
- [x] Protocol v2: `{"event":"step","action":"call","goal":"…","depth":2,"file":…,"line":…,"column":…}`
      emitted when the hook pauses, answered by
      `{"cmd":"step","action":"into|over|continue|stop"}`.  Reuse the
      re-entrant request loop that `answerInputRequest` already uses — the
      session reads requests while the engine is inside a query, so no new
      threading model is needed.
- [x] GUI: **Шаг** `F10` (into), `Shift+F10` (over), `F5`/**Продолжить**
      (continue), a step panel showing the current goal, depth and the call
      stack, and the traced line highlighted in the editor like an error line
      but in a neutral colour.  While stepping, output is flushed line by line
      so the picture in the editor matches the step just reported.
- [x] Stepping must not be implemented by parsing the textual trace: the text
      format is for humans and changes with `ВЕРСИЯ`.  If the structured hook is
      not worth its cost later, the fallback is to grep the trace text — record
      that as a deliberate fallback in `decisions.md`, not as the design.

Input

- [x] `input_request` is answered from the input pane (task_27) or a dialog,
      depending on the setting; the three kinds map to the three widgets, and
      an unanswered request is visible in the status bar and can be cancelled
      (which answers with an empty string, as `std::nullopt` means end of
      input).
- [x] **Стоп** while the interpreter waits for input aborts the query; the
      pending request is dismissed.

## Tests

- [x] Catch2: a step hook that records the sequence of actions for a small
      program and stops at the N-th step; a hook that returns `stop` makes the
      query end with the same error code as `interrupt`.
- [x] CTest: a protocol session that runs a query with stepping on, checks the
      `step` events and that `{"cmd":"step","action":"stop"}` ends the query.
- [x] CTest: a parse *and* a runtime error both produce `error` events with
      `line` and `column` fields.
- [x] Python: Qt-free step-client test (`src/gui/tests/test_stepping.py`) against
      the built interpreter, like `protocol_smoke.py`.
- [x] Manual checklist: error line highlighted, Stop on `ПС <- ПС` (or an
      infinite loop), step-by-step on a small recursive program.

## Acceptance

A runaway program stops on **Остановить** and the window stays usable; a syntax
error and a runtime error both mark the offending line in red; a small program
can be walked goal by goal and the editor follows the current line; `ВВОДСТР`
is answered from the input pane.

## What was built (2026-09-29)

* `prlib`: `EngineOptions::stepHook` — `std::function<StepDecision(const StepInfo&)>`
  called at the four points the textual trace already had (call, exit, redo, fail),
  with `StepInfo{action, goal, depth, location}`.  The environment frames carry the
  depth and the clause's `SourceLocation`, so a step point and a runtime error both
  know where they are; the frames of a conjunction and of `ВЫП` are not goals and
  are not announced, which is what makes the `call`/`exit` pairs balance.
* `prlib`: `Engine::raise` fills in the location of the clause being solved, so
  **runtime errors carry a position** — the gap the task asked to check for.  A
  nested query (`НАЙТИВСЕ`, `НЕ`, `ИЛИ`) saves and restores it.
* `prlib`: `IoContext::setTraceSink` — the trace text goes to the front-end when one
  asks for it, and to the output stream as before when none does.  That is how the
  GUI colours the trace apart from the program's own output.
* Protocol 3: `step` events, the `step` request (`into`/`over`/`continue`/`stop`),
  `trace` events, `file`/`line`/`column` on `error`, and the `step`/`trace` flags of
  `load` and `query`.
* GUI: the step strip (`panels.StepPane`) with the action, goal, depth, position and
  the call stack the window rebuilds from `call`/`exit`; the trace line marked in the
  editor in a neutral colour; `F10`, `Shift+F10`, `F5` as «продолжить», and the three
  commands enabled (a *paused* step is a usable state — a disabled `QAction` fires no
  shortcut); the error line from the structured position, with the caret on it and
  the file opened in a tab when the diagnostic comes from an `ИМПОРТ`ed file.
* Tests: `src/tests/test_stepping.cpp` (6 cases), `src/gui/tests/test_stepping.py`
  (7 checks, Qt-free, against the built interpreter), five more checks in
  `test_window.py`, and the protocol session in `src/tests/protocol_session.cmake`.

Two decisions worth keeping (both in `ai/decisions.md`):

1. **There is no `Pause` outcome.**  The hook *blocks* — reading the next request,
   the same re-entrant loop `input_request` uses — and then answers `Continue` or
   `Stop`.  The solver has no continuation to suspend, and the request loop a
   front-end already has is exactly the pause; a third value would have been a
   promise the engine cannot keep.
2. **Stepping is not implemented by reading the trace text.**  The text format is
   for humans and changes with the version; the structured hook is what the panel,
   the stack and the highlighted line are built on.

One thing the task asked for and the 2026-09-29 round did **not** do — the polite
stop — was finished on 2026-10-01:

* `interrupt` reaches the solver at every step of its loop, so a query that is
  solving (a runaway included) ends on the request — the old comment «a runaway
  query has to be stopped by ending the process» was simply stale.  A *paused step
  point* answers `interrupt` by ending the pause (the step loop maps it to
  `StepDecision::Stop`; pinned by a ctest case now), and a read waiting for input
  answers it by ending the wait.
* «Остановить» asks first: `interrupt`, then `STOP_GRACE_MS` (500 ms), and only
  then terminate + kill.  A polite stop leaves the session **idle with its
  knowledge base** — that is what makes the two outcomes differ cleanly at last:
  stopping a *run* keeps the interpreter, stopping an *idle* interpreter unloads
  the base, and both say so in the pane and in the status bar.  Closing the window
  skips the request and takes the process down at once.
* The error event of the interrupted query is the stop's own: the window answers
  it with the `--- остановлено ---` note and marks no line.
* Tests: `test_stopping_a_query_asks_first_and_keeps_the_base` (run a read that
  waits for input, stop, the base stays and the pending request is dismissed; the
  next press unloads), the in-flight stop of `test_the_run_state_drives_the_buttons`
  now waits for the note instead of assuming it, and the protocol session gained
  the `interrupt`-at-a-pause case.
* One naming point from the Run table was finished in the same pass: a text load is
  named after its tab — a saved file by its path, an unnamed buffer by its title
  («Без имени 2») — instead of the protocol's `<buffer>`, so a diagnostic in an
  unnamed buffer reads «Без имени 2:1:1».  `<buffer>` stays the protocol's default
  for a load that names nothing, and the window still reads it as the showing tab.
