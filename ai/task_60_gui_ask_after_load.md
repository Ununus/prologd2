# task_60 — the window: a question is asked only when there is someone to ask

**Status:** done (2026-10-04) — both fixes are in: a marker asks after a successful load
(the `_pending_query` state, the send from `_on_loaded`, a failed load discarding the
question with a line in "Система"), and the query line loads the current text **only** when
there is no base at all.  Five new cases in `test_window.py`; the protocol is untouched
(version 11).
**Depends on:** task_36 (question markers and the separate `query` request named `<query>`),
task_50 (the query line and its docstrings), task_46 (`questions`), task_58 (the "knowledge
base loaded" line in `_on_loaded`)
**Milestone:** post-M10

## Goal

Two fixes of one family — about **when** the window sends a question:

1. **A marker click asks after a successful load**, not together with it (§1).  Today the
   question goes out right after the load, so with a file that did not parse the window asks
   it against an empty base: the answer is "НЕТ", the warning "`<query>:1:2: не найдено:
   факт/1`" and a **second** parse error about the same line (`<query>:1:8` on top of
   `Без имени:1:8`) — even though that line lives in the file which did not parse anyway.
2. **The query line loads the program only when it has nothing to ask** (§2).  Today it
   never re-reads the file (which is right: there is one base, and reloading it is extra
   work), but it also does not notice that there is **no base at all**: a goal typed before
   the first `F5` answers "НЕТ" and "не найдено: факт/1" instead of honestly starting the
   program.

## Facts this rests on (checked on the built `prologd.exe`)

* `questions=false` at load means "do not **run** the program's own `?` lines"
  (`protocol.cpp`: `loader_.setQueryRunner(nullptr)`), but the file is still **parsed in
  full** — which is why a `?0 < 5 < 4.` in a file is reported by the load, and reported with
  the file's name.
* A separate query is parsed by its own parse and is called `<query>`; that is how the
  protocol tells "an error in the file, line N" from "an error in the line that was sent"
  (task_36).  Both errors are honest — two parses of one text — but in the window they mean
  one thing, "this question cannot be run", and one message is enough.
* A file that did not parse **loads no base at all**: `loader_.loadSource` parses the whole
  text before adding anything, so any question after such a load answers against an empty
  base.  That was the real defect; the doubled parse message was only its visible part.
* The query line does no loading: `_run_query` starts the interpreter if it is not running
  (`_start_session`) and sends `query` at once.  With an empty base the answer is "НЕТ" and
  a "не найдено" warning.
* Only `run_program` (`F5` and a marker click) clears the panels; the query line does not,
  so an error from a long-ago run stays in "Вывод" beside the new one.  That is right (a log
  must not vanish) and does not change here — and with the deferred question this case
  disappears by itself, because the request goes out only after a successful load.

## §1. The marker: the question goes out after the load has answered

**Where.**  `window.py`: `_on_query_requested`, `_on_loaded`, `_on_failed`, `_stop_now`,
`_on_ended`, `run_program`, and the new `_pending_query`.

**What to do.**

* A new state `self._pending_query: str | None = None` — a question waiting for its load,
  beside `_awaiting_query` and `_answer_text` (one family: "what is in flight right now").
* `_on_query_requested`: instead of `self._session.run_query(statement)`, remember the
  statement and set `self._awaiting_query = True`; the rest of the order stays (stop the
  running program, `run_program(questions=False)`, put the line into the query field so that
  one can see what is being asked).
* `_on_loaded`: in the branch that already prints `--- база знаний загружена (N мс) ---`
  (the quiet load made for a question), send the deferred question — there and only there is
  it known that the file parsed.
* `_on_failed` (the error branch): if a question was waiting, drop it and say so in one line
  in "Система": `--- вопрос не выполнен: база знаний не загрузилась ---`.  The file's error
  is already shown with its line marked, and that is enough: silence is worse (the click
  "did nothing") and a second question to the interpreter is worse than both.
* The deferred question is also forgotten in `_stop_now` ("Остановить"), in `_on_ended` (the
  process died: there will be no answer) and in `run_program` (a new run cancels the old
  question).  In `_on_ended` that is safe: the event of the old process arrives **inside**
  `session.start()` of the new one (see the comment in `run_program`), that is, before the
  new question is deferred.

**Decisions.**

* **Defer rather than "do not ask after an error".**  A load error can only be learned from
  an event *before* the question is sent: both the load and the request go into one channel
  and the answers come back asynchronously.  A deferred question is exactly "ask when there
  is someone to ask", and it removes the doubled error by construction: the request goes out
  only after the file parsed, and then a line from the file parses by itself.
* **A question that came from a comment** (`% ?цель.`) is a separate case: parsing the file
  does not cover it (a `% ?…` is prose to the parser), so a bad "parked" question still
  reports itself — once, as `<query>`.  That is how it should be: it is not a doubled error
  but a different text, and the case is pinned by a test.
* The order "the loading line, then the answer" does not change: the line is printed where
  it was, and the question goes out right after it.

## §2. The query line: it loads only when there is nobody to ask

**Where.**  `window.py::_run_query` and the same `_pending_query`.

**What to do.**  Before sending the request, look at `self._loaded` — the sign that "the
running interpreter has a loaded program":

* **there is a base** — everything as it is: `query` goes out at once, no reloading (a user
  decision: there is one base, and re-reading the file for every goal is extra work; a goal
  asks the program that the last `F5` or marker click loaded);
* **there is no base** (`_loaded` false: the interpreter has only just started, or the base
  was unloaded by a stop) — quietly load the current text
  (`run_program(questions=False)`) and send the question by the §1 route, that is, after
  `loaded`.  Then `?факт(1).` without a preceding `F5` answers "ДА" instead of "НЕТ".

**Decisions.**

* **The sign is `_loaded`, not "the session is not running".**  A session can be alive
  without a base: "Остановить" on a free interpreter unloads the base (`_stop_now`), while a
  polite stop of a query does not (`_finish_polite_stop` keeps the base).  Only `_loaded`
  tells these states apart, and it is reset in `_on_ended`.
* **Quietly** (`questions=False`), like a marker: the goal is one question, and the
  program's own `?` lines have nothing to do with it.

## §3. Documents and records

* `doc/gui.typ` §4.2 (questions in the margin): a click asks **after** the load, and a file
  that did not parse gets no question — "Система" gets a line about it while the file's error
  stays in place with its line marked.  §6 (running and the query line): the goal asks the
  **loaded** base; if there is none, the window first loads the current text quietly.
* `src/gui/README.md` — the same two places in prose (the marker section and the query-line
  section).
* `ai/status.md` — the task row and the round's entry.
* `ai/task_60_gui_ask_after_load.md` — this file, with its status and "what the round found".

## Checks

`src/gui/tests/test_window.py`:

* **`test_a_clicked_question_is_asked_once_the_load_has_answered`** — a file with
  `?0 < 5 < 4.`: a marker click gives **one** parse error (the file's name) and `<query>`
  does not occur in "Проблемы" at all;
* **`test_a_question_is_not_asked_when_the_file_does_not_parse`** — a good question
  "parked" in a comment, in a file with a syntax error: no answer (no "НЕТ" in "Вывод"), no
  "не найдено" warning, "Система" has the "вопрос не выполнен" line, and the file's line is
  marked; and after that an `F5` on the same file still shows its own error;
* **`test_a_parked_question_still_reports_its_own_parse_error`** — the same trick in a file
  that parses: exactly one error, and it is `<query>:1:8` (the file is not to blame here);
* **`test_the_goal_line_loads_when_there_is_no_base`** — a fresh window, `факт(1).` in the
  editor, a goal in the query line: "ДА", and no "не найдено" in "Проблемы";
* **`test_the_goal_line_does_not_reload_a_loaded_base`** — after `F5` the program text is
  edited to `факт(2).` and the same goal is asked: the answer is "ДА" (from the loaded base)
  and "Система" holds exactly one `--- загрузка базы знаний ---` line, that is, there was no
  reloading.

Then the usual round: every `src/gui/tests/test_*.py` suite, `protocol_smoke.py`, `ctest`,
the docs build, and a look at the pages of §4.2 and §6.

## What the round found

1. **Only `run_program` clears the panels.**  `F5` and a marker click start from a clean
   slate, the query line does not (and rightly so: a log must not vanish).  That is why the
   user saw two errors "at once": the file's error from an earlier `F5` or click stayed in
   "Вывод" and the new one from `query` was added to it.
2. **A file that did not parse loads no base at all**, so a question after a failed load
   answered "НЕТ" and "не найдено: факт/1" about an empty interpreter.  That was the real
   defect; the doubled parse message was only its visible part.
3. **`_awaiting_query` stayed set after a polite stop.**  In `_on_result` the "we were
   stopped" branch returns before the flag is cleared, so the next `loaded` (from any later
   run) hit the early `return` and printed the "база знаний загружена" line for no reason.
   The flag is now cleared in `_finish_polite_stop`, together with the deferred question.
4. **The sign of "there is someone to ask" is `_loaded`, not "the session is running".**  A
   session lives long: stopping a free interpreter unloads the base (`_stop_now`), a polite
   stop of a query does not (`_finish_polite_stop`).  Only `_loaded` tells these apart, and
   it is reset in `_on_ended`.
5. **A question from a comment is checked separately.**  Parsing the file does not see it, so
   a bad "parked" question still reports itself, once, as `<query>` — pinned by a test.

## Notes

* Nothing changes in the interpreter or the protocol: both fixes are about *when* the window
  sends what it can already send.  The protocol version stays 11.
* The existing cases that must stay green and incidentally exercise the deferred route:
  `test_a_marker_answers_one_question_alone`,
  `test_a_question_parked_in_a_comment_runs_from_the_margin`,
  `test_a_marker_while_a_step_is_paused_starts_a_fresh_quiet_run`,
  `test_a_marker_builds_the_answer_table` and the other table cases (task_59).
