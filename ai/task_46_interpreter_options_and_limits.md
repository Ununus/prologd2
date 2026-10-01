# task_46 — Interpreter options, profiles and limits

**Status:** not started
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
| a wall-clock timeout | — | does not exist |
| the working directory of the *process* (`ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ` are relative to it) | — | does not exist |
| interpreter profiles | — | do not exist |

The JSON session exposes **none** of the limits: `load` carries `step`, `trace`
and `questions` and nothing else, so a dialog cannot reach `maxSteps`.

## Deliverables

- [ ] **One place that builds the limits.**  `EngineOptions` gains a
      `timeoutMs` (0 = none) next to the existing caps, and a single helper fills
      an `EngineOptions` from a `Limits` struct — the CLI and the protocol both use
      it, so a flag and a setting cannot drift apart.
- [ ] **CLI parity**: `--max-findall N` and `--timeout-ms N` next to the existing
      `--max-steps`/`--max-depth`, documented in `help.typ` and the README.
- [ ] **Protocol 9/10**: a `limits` object on `load` (or a `set_limits` request
      answered by `limits_set`) with `maxSteps`, `maxDepth`, `maxFindall`,
      `timeoutMs`; a limit that fires ends the run with a diagnostic that **names
      the limit and the setting that raises it** — «остановлено: превышен предел
      шагов (execution/max_steps)» — because a limit nobody can name is a mystery.
- [ ] **The GUI rows** (`Выполнение`): `execution/interpreter` (a file path — the
      dialog's folder rows already have the «Обзор…» button), and
      `execution/process_directory` as a *choice* — `каталог файла` (default for a
      saved file), `рабочая папка` (default for «Без имени») or a fixed directory.
      Both are pushed into `PrologSession` (`setProgram`, and the child's working
      directory via `QProcess.setWorkingDirectory`), and «Применить» **restarts a
      live session** after either changes, saying so in the status bar.
- [ ] **The GUI rows** for the limits: `execution/max_steps`, `execution/max_depth`,
      `execution/max_findall`, `execution/timeout_ms`, all `0 = без предела`, sent
      with every `load`.
- [ ] **Profiles**: `execution/profiles` — a table of named sets of (the `-I`
      list, the limits, the interpreter path), stored as JSON in the settings file
      the way `shortcuts/table` is; `execution/profile` — the active name; a page
      «Профили» in the dialog to add, rename, copy and delete one, and «Сделать
      текущей».  A profile is applied at every session start, and switching one on
      restarts a live session.
- [ ] The status bar names the interpreter when it is not the default one, so a
      window that runs a different build says so (`проlogd: …\Debug\prologd.exe`).

## Design notes

* **A wall-clock timeout cannot preempt everything.**  The solver polls
  `shouldStop()` at every step, next to `externalStop`, so a *computing* program
  ends on time; a program **waiting for input** (`ВВОД` with nobody answering) is
  blocked outside the solver and the deadline does not reach it — that is what
  «Остановить» is for, and the task file says so instead of promising otherwise.
  Pin both halves with tests: a runaway computation stops on the deadline, a
  waiting read does not (the GUI's stop request is what ends it).
* The **step cap is the cheap guard** for a runaway *search* (it counts work), the
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

- [ ] Catch2: `timeoutMs` ends a slow query with the documented diagnostic; the
      step cap and the `НАЙТИВСЕ` cap keep their messages (task_38's tests grow a
      case each); a limit of `0` really means unlimited.
- [ ] `protocol_session.cmake`: the limits travel on `load`, they are refused when
      they make no sense (`-1`), and the diagnostic names the limit.
- [ ] `test_settings.py` / `test_settingsdialog.py`: the new rows round-trip and
      the profile table survives a foreign file; «Профили» adds, copies and
      deletes.
- [ ] `test_window.py`: the limits reach the wire (a run with a step cap of 1
      stops and says why); a profile changes the `-I` list of the next session;
      changing the interpreter path with «Применить» stops the live session and
      the next run uses the new path (a copy of the built exe as the «other»
      interpreter).
- [ ] By hand: a lesson program with an endless loop stops with a message; a
      teacher's profile switches the search path in one click.

## Acceptance

A student program that would hang the window stops with a message that names the
limit and the setting that raises it; a teacher can hand out one settings file
with a profile in it and switch profiles without a restart; the interpreter that
runs is visible in the window, not only in the command line that started it.
