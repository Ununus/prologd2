# task_46 — Interpreter options, profiles and limits

**Status:** in progress — the limits are done (protocol 9), the interpreter path,
the process directory and profiles remain (2026-10-01)
**Depends on:** task_29 (the dialog and the description table), task_21/task_27
(the session and its run states), task_38 (the engine's own limits)
**Milestone:** M16

## Goal

Everything about *which* interpreter runs and *how long* it may run becomes a
setting a teacher can hand out, instead of a command-line flag only the person
who wrote it remembers: the path to `prologd`, the working directory of the
process, named profiles, and the limits a student program needs — a step cap, a
depth cap, a `НАЙТИВСЕ` cap and a wall-clock timeout.

This is the last item of task_29's settings list that is not a dialog row, so the
work is split where the work really is: the front-end already exists, the session
does not carry the values, and the engine has some of them.

## What already exists (checked 2026-10-01)

| Thing | Where | State |
|---|---|---|
| `maxSteps` (0 = unlimited), `maxDepth`, `maxNestedDepth`, `maxFindAllSolutions` | `prlib/engine.hpp`, `EngineOptions` | in the engine |
| `--max-steps`, `--max-depth` | `src/cli/main.cpp` | CLI only |
| `--exe PATH` | `src/gui/main.py` | command line only |
| the shared folder and the `-I` list | `settings` `execution/working_directory`, `execution/import_paths`, the dialog | done (task_29) |
| a wall-clock timeout | `window.py` (`_arm_timeout`) | done in the front-end (2026-10-01) |
| the working directory of the *process* (`ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ` are relative to it) | — | does not exist |
| interpreter profiles | — | do not exist |

The JSON session exposed **none** of the limits until protocol 9: `load` carried
`step`, `trace` and `questions` and nothing else, so a dialog could not reach
`maxSteps`.  Version 9 adds the `limits` object (see below).

## Deliverables

- [x] **One place that builds the limits.**  `prlib/engine.hpp` has a `Limits`
      struct with `applyTo(EngineOptions&)`, and `--max-steps`/`--max-depth`/
      `--max-findall` all go through it, so a flag and a setting cannot drift apart.
      Its defaults are **no limit** at all (ADR-020): a limit is an option of the
      run, not a property of the core, and the core's messages name a limit and its
      value and nothing else — no flag, no dialog row.  The struct deliberately
      **has no timeout**: see the note below.
- [x] **CLI parity, half of it**: `--max-findall N` sits next to
      `--max-steps`/`--max-depth` and is documented in `help.typ`.
- [ ] **CLI parity, the rest**: `--timeout-ms N` — a *text-mode* deadline.  Not
      needed by the window (which has its own clock, below); it would have to be
      polled from inside `Engine::shouldStop()`, and a clock read at every
      solution is exactly the cost the front-end clock avoids.  Decide whether a
      text-mode deadline is worth that before adding it.
- [x] **Protocol 9**: the `limits` object on `load` (`maxSteps`, `maxDepth`,
      `maxFindall`; `0` = без предела; applied *before* the load, because the
      program's own `?`-statements run during it).  A limit that fires ends the
      run with a diagnostic that **names the limit and its value** — «Превышен
      предел шагов выполнения: 5000» (ADR-020; the callers' vocabulary stays with
      the callers: `--help` names the flag, the window names its own rows).  A
      request with a field of the wrong type (`"maxSteps":-1`) is an `error` event
      of kind `protocol` and the session reads the next line; before version 9 such
      a request took the process down.  `timeoutMs` is **not** on the wire (see
      the design notes).
- [ ] **The GUI rows** (`Выполнение`): `execution/interpreter` (a file path — the
      dialog's folder rows already have the «Обзор…» button), and
      `execution/process_directory` as a *choice* — `каталог файла` (default for a
      saved file), `рабочая папка` (default for «Без имени») or a fixed directory.
      Both are pushed into `PrologSession` (`setProgram`, and the child's working
      directory via `QProcess.setWorkingDirectory`), and «Применить» **restarts a
      live session** after either changes, saying so in the status bar.
- [x] **The GUI rows** for the limits: `execution/max_steps` → «Предел шагов»,
      `execution/max_depth` → «Предел глубины», `execution/max_findall` → «Предел
      решений НАЙТИВСЕ», `execution/timeout_seconds` → «Предел времени, с»; all
      four `0 = без предела`, and the three solver limits are sent with every
      `load`.  The window's own defaults are **0 / 1 000 000 / 1 000 000 / 0**: the
      decision about what is safe for a lesson is the window's, since the core
      refuses to make it.  The run names the rows it differs from in the output
      pane («пределы: «Предел шагов» 5000 — строки в «Выполнении» настроек»), which
      is the window's half of «where do I raise it».
- [ ] **Profiles**: `execution/profiles` — a table of named sets of (the `-I`
      list, the limits, the interpreter path), stored as JSON in the settings file
      the way `shortcuts/table` is; `execution/profile` — the active name; a page
      «Профили» in the dialog to add, rename, copy and delete one, and «Сделать
      текущей».  A profile is applied at every session start, and switching one on
      restarts a live session.
- [ ] The status bar names the interpreter when it is not the default one, so a
      window that runs a different build says so (`проlogd: …\Debug\prologd.exe`).

## Design notes

* **The core knows no front-end (ADR-020, 2026-10-01).**  A limit is an option of
  the *run*: the engine's own defaults are «без предела», its messages name a limit
  and its value and stop there, and the vocabulary of raising one — a flag, a
  dialog row — lives with whoever owns it.  So the window carries the numbers that
  make a lesson safe (0 / 1 000 000 / 1 000 000 / 0) and says, before a run, which
  of its rows differ from them.
* **The wall-clock timeout lives in the front-end, by decision (2026-10-01).**
  The engine counts steps and never looks at a clock: a `steady_clock::now()` in
  the solver's hot path is a cost paid for every solution, and it is the front-end
  that knows what «too slow for a lesson» means anyway.  So the window arms a
  `QTimer` for the run and, when it fires, prints «--- предел времени: N с,
  остановлено ---» and sends the ordinary `interrupt` request.  Consequences, both
  pinned by tests: a *computing* program stops on the deadline (the engine polls
  the stop flag at every step, as it already did for «Остановить»), while a
  program **waiting for input** (`ВВОД` with nobody answering) is blocked outside
  the solver and the deadline does not reach it — that is what «Остановить» is for.
  A text-mode `--timeout-ms` would need the engine clock back; it stays unwritten
  until someone wants a deadline outside the window.* The **step cap is the cheap guard** for a runaway *search* (it counts work), the
  **timeout** for a slow computation (it counts wall clock), and the `НАЙТИВСЕ`
  cap is a **diagnostic, not a silent truncation**: reaching it is an error that
  says which setting raised it, because a truncated result set that looks complete
  is the one outcome worse than a failure.
* The **profile table is data**, not a dialog state: it lives in the settings file
  with the same promises as the rest (unknown keys survive, broken values fall
  back), and `test_settings.py` gets one row per profile field.
* Nothing on the command line is lost: the flags stay and mean the same values,
  they are simply no longer the only way in.

## Tests

- [x] Catch2: the step cap, the depth cap (value, flag and row name in the
      message) and the `НАЙТИВСЕ` cap each name themselves
      (`every limit names itself, its value and where to raise it`), a fresh
      `Limits` equals the engine's defaults, and a limit of `0` really means
      unlimited for every one of them.  No `timeoutMs` case: there is no engine
      clock to test.
- [x] `protocol_session.cmake`: the limits travel on `load`, a negative one is
      refused with a `protocol` error, and the session serves the next request.
- [x] `test_settings.py` (defaults, `limits()` shape, a negative value falls back
      to `0`, the timeout is clamped) and `test_settingsdialog.py` (a row each).
- [x] `test_window.py`: the limits reach the wire (a run with a step cap of 5000
      stops and says why), the run names its limits, the deadline is armed and
      dropped with the run, and an expired deadline interrupts.
- [ ] `test_window.py` for the rest: a profile changes the `-I` list of the next
      session; changing the interpreter path with «Применить» stops the live
      session and the next run uses the new path (a copy of the built exe as the
      «other» interpreter).
- [ ] By hand: a lesson program with an endless loop stops with a message; a
      teacher's profile switches the search path in one click.

## Acceptance

A student program that would hang the window stops with a message that names the
limit and the setting that raises it; a teacher can hand out one settings file
with a profile in it and switch profiles without a restart; the interpreter that
runs is visible in the window, not only in the command line that started it.
