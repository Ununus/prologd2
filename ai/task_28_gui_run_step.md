# task_28 — GUI: run, step, stop, error line, input

**Status:** not started
**Depends on:** task_22, task_25, task_27
**Milestone:** M11

## Goal

Execution from the window: run the whole program, run it step by step, stop a
program that has run away, show where an error happened, and answer the
interpreter's questions.

## Deliverables

Run

- [ ] **Запуск** `F5`: push the current buffer into the session and run its
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
- [ ] "Сохранять перед запуском" stays available as an option (the reference GUI
      had it), but it is no longer needed for imports to resolve.
- [ ] **Запуск с трассировкой**: the same with the trace enabled, so the
      reference-style trace text appears in the pane (grey).
- [ ] Restart policy: a session is reused while it is alive; a tab switch,
      a run after a stop, or a crashed child starts a fresh process.  The status
      bar always shows which state the session is in.

Stop

- [ ] **Остановить** `Shift+F5`: send `interrupt` first (it works while the
      interpreter waits for input and between commands), and if the query is
      still running after a short grace period, terminate the child and start a
      new session — exactly the note in `src/gui/README.md`, which is why the
      button cannot be a polite signal alone.
- [ ] The editor must stay responsive while a query runs: all interpreter I/O
      happens on the `QProcess` signals, never in a blocking call from the UI
      thread.

Error line

- [ ] Protocol v2: `error` events carry structured position fields
      (`file`, `line`, `column`) next to the human `message`, so the GUI does
      not parse `file:line:column:` out of the text.  Parse diagnostics already
      have the location; **verify that runtime errors carry one too** — a
      runtime error is raised through `raiseAt(code, location, …)` and clauses
      keep their `SourceLocation`, so if any runtime path loses the position,
      fix it there and cover it with a test.
- [ ] The editor marks the reported line: red background plus a marker in the
      line-number area, the caret moves there, and the mark is cleared on the
      next run or on edit.  A parse error marks the line too (the offset *is*
      the column).
- [ ] Diagnostics from `ИМПОРТ`ed files carry that file's name; the GUI opens
      the file in a tab if it is not open yet (or says where it is, if the path
      is outside the project).

Step by step

- [ ] `prlib`: `EngineOptions::stepHook`, the same shape as `externalStop`:
      a `std::function` called by the solver at the four points it already
      traces (call, exit, redo, fail) with a `StepInfo {action, goal text,
      depth, location}` and returning `continue / pause / stop`.  Null by
      default, so the cost when not stepping is one branch.  It must be safe to
      call from the solver's own loop and must not be a signal handler.
- [ ] Protocol v2: `{"event":"step","action":"call","goal":"…","depth":2,"file":…,"line":…,"column":…}`
      emitted when the hook pauses, answered by
      `{"cmd":"step","action":"into|over|continue|stop"}`.  Reuse the
      re-entrant request loop that `answerInputRequest` already uses — the
      session reads requests while the engine is inside a query, so no new
      threading model is needed.
- [ ] GUI: **Шаг** `F10` (into), `Shift+F10` (over), `F5`/**Продолжить**
      (continue), a step panel showing the current goal, depth and the call
      stack, and the traced line highlighted in the editor like an error line
      but in a neutral colour.  While stepping, output is flushed line by line
      so the picture in the editor matches the step just reported.
- [ ] Stepping must not be implemented by parsing the textual trace: the text
      format is for humans and changes with `ВЕРСИЯ`.  If the structured hook is
      not worth its cost later, the fallback is to grep the trace text — record
      that as a deliberate fallback in `decisions.md`, not as the design.

Input

- [ ] `input_request` is answered from the input pane (task_27) or a dialog,
      depending on the setting; the three kinds map to the three widgets, and
      an unanswered request is visible in the status bar and can be cancelled
      (which answers with an empty string, as `std::nullopt` means end of
      input).
- [ ] **Стоп** while the interpreter waits for input aborts the query; the
      pending request is dismissed.

## Tests

- [ ] Catch2: a step hook that records the sequence of actions for a small
      program and stops at the N-th step; a hook that returns `stop` makes the
      query end with the same error code as `interrupt`.
- [ ] CTest: a protocol session that runs a query with stepping on, checks the
      `step` events and that `{"cmd":"step","action":"stop"}` ends the query.
- [ ] CTest: a parse *and* a runtime error both produce `error` events with
      `line` and `column` fields.
- [ ] Python: Qt-free step-client test (`src/gui/tests/test_stepping.py`) against
      the built interpreter, like `protocol_smoke.py`.
- [ ] Manual checklist: error line highlighted, Stop on `ПС <- ПС` (or an
      infinite loop), step-by-step on a small recursive program.

## Acceptance

A runaway program stops on **Остановить** and the window stays usable; a syntax
error and a runtime error both mark the offending line in red; a small program
can be walked goal by goal and the editor follows the current line; `ВВОДСТР`
is answered from the input pane.
