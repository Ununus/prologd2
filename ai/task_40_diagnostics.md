# task_40 — diagnostics a beginner can use

**Status:** done (2026-09-30)
**Depends on:** nothing; it overlaps task_39 (a new spelling should be mentioned
in the "did you mean" hints) and task_41 (the diagnostic for a `;` terminator)
**Milestone:** M14

## Goal

The interpreter is used to *teach*, and most of what a learner gets wrong today
is answered with silence.  Six measured examples (2026-09-30, the built CLI)
show where the messages stop helping:

| Program | Today | Wanted |
|---|---|---|
| `?члеен(а, [а]).` (typo, undefined name) | `НЕТ`, exit 0, nothing on stderr | warning + `не найдено: члеен/2; возможно, член/2` |
| `мама(Лена, Таня).` + `?мама(Лена, Таня).` | `Лена=_1`, `Таня=_1` — nonsense, no hint | warning: `Лена` — переменная, а не константа; константа — в одинарных кавычках |
| `дв(1, 2).` + `?дв(1).` | `НЕТ`, silent | warning: `дв` определён с арностью 2, а вызван с 1 |
| `?УМНОЖЕНИЕ(2, 3).` | `НЕТ`, silent — a *reserved* name with a wrong arity | error: `УМНОЖЕНИЕ` не имеет арности 2 (есть 3 и 4) |
| `факт(1)` (no final dot) | `pld:2:1: error: ошибка при разборе предложения` — a line past the end, message says nothing | `предложение заканчивается точкой` at the end of the last clause |
| `факт(1.` | `pld:3:1: error: непарные скобки` — points at the current token | `непарные скобки: '(' открыта в строке 1`, at the bracket |

The parser already recovers (`MessageSink` collects several diagnostics,
`Parser::recoverToStatementEnd`) and errors carry positions (`file:line:column`)
into both the CLI and the GUI, so this task is about *what* is reported, not
about building the plumbing.

## Deliverables

- [x] **Severity.**  `PrologError` gains `Severity { Error, Warning, Note }`;
      `DiagnosticSink` counts errors and warnings separately and `hasErrors`
      keeps meaning *errors* (a warning must never change an exit code, and
      `НЕ(нет_такого)` must keep working: an unknown predicate stays a
      *failure*, it just gets a warning).  CLI prints `warning:` next to
      `error:`, gains `--no-warnings`; the protocol's `error` event gains
      `severity`, and the GUI colours warnings amber (`panels.py` already
      colours by kind — the kind comes from the window, as its docstring
      insists) and counts them in the status bar.
- [x] **Parse-time checks**, each with the location a reader can act on:
  * unclosed bracket → keep a stack of opening brackets with their locations and
    report the *opening* one;
  * a statement that runs into end-of-file without a final dot → report at the
    end of the last clause, with the wording from the table above (and stop
    saying "ошибка при разборе предложения" where something specific is known);
  * a quoted atom or string left open → point at the opening quote (same
    mechanism).
- [x] **A variable that looks like a constant** (the porting trap the course
      itself teaches): warn about a variable in a *fact or rule head* that the
      clause never binds and never uses again — `мама(Лена, Таня).` is the
      canonical case.  The message names the variable and shows the fix (quoting
      it), because the alternative reading (a deliberate wildcard) is rare and
      `_` is right there.
- [x] **Singleton variables** per clause (excluding `_` and names starting with
      `_`, which is how the dialect already spells "deliberately unused"), as a
      warning: usually a typo, and the lessons use `_` consistently, so the
      course stays quiet.
- [x] **Call-site checks** (they need the name tables, which are in-process:
      `Database::predicates()` and `reservedKeywords()`):
  * an undefined predicate called in a body or a query → a warning with a
    suggestion when a name of the same arity is within a small edit distance
    (Cyrillic included — distance over code points, not bytes);
  * a *known* name called with an unknown arity → the arities it does have, both
    for user predicates and for reserved names (`УМНОЖЕНИЕ` 2 → «есть 3 и 4»);
  * the same checks for `ВЫП/1`'s argument when it is a literal goal (cheap and
    catches `ВЫП(члены(Х))`).
- [x] **Tests**: a new `src/tests/test_diagnostics.cpp` with one case per message
      (code, severity, position, and the exact text), a CLI case proving that
      warnings leave exit codes 0/2/3 alone and that `--no-warnings` silences
      them, and a GUI check that a warning arrives with its colour and position
      (`src/gui/tests/test_window.py`).
- [x] Documentation: `doc/help.typ` gains a short "диагностика" section (what is
      an error, what is a warning, exit codes 1/2/3 and the new flag),
      `doc/gui.typ` the amber colour, `ai/conventions.md` the rule that every new
      diagnostic carries a severity and a position.

## Acceptance criteria

1. Each row of the table above produces the wanted text at the wanted position.
2. A program that runs correctly today still runs *and still exits 0* when the
   same program produces warnings (`-q`, `--protocol json` and the GUI session
   included).
3. `ctest` and the headless GUI scripts are green; the lessons need no change
   (they are the corpus that must stay quiet — if a lesson starts warning, the
   lesson is wrong or the check is too eager).

## Risks and notes

* Teaching text is a user-visible surface: every message added here needs the
  same care as a built-in's help section, and the wording is Russian, lowercase,
  without a trailing period, matching the existing style (`ai/conventions.md`).
* "Unknown predicate" is a *warning*, not an error, on purpose: the dialect
  documents that an undefined goal fails, and negation as failure leans on it.
  An error would break `НЕ(нет_такого)` and the `?` queries of half the lessons.
* The "did you mean" suggestion must degrade gracefully: no candidate within the
  distance means a plain message, never a wrong suggestion.
* Optional, and better as its own decision: unused predicates and duplicated
  clauses as a `--lint` pass.  Useful for a course, noisy for a query file, so
  it is off unless asked for.

## Result

Everything in the table landed.  The shape it took, and the places where the
plan met the corpus:

* **Severity** is a field of `PrologError` (`Error`/`Warning`/`Note`), counted
  apart by `DiagnosticSink`; `format` prints `warning:` next to `error:`.  The
  CLI gained `--no-warnings` (a diagnostic hook that drops warnings and keeps the
  usual lines for everything else).  The wire format went to **4**: `error`
  events carry `severity`, the GUI colours warnings amber (`panels.WARNING`) and
  counts them beside the answer (`решение найдено · предупреждений: 2`).
* **A reserved name with an arity that exists nowhere** — not in the dispatch
  table, not in the program, not in the database — is an *error*, so
  `?УМНОЖЕНИЕ(2, 3).` now prints
  `УМНОЖЕНИЕ не имеет арности 2 (есть 3 и 4)` and the load exits 2 instead of
  answering `НЕТ` in silence.  Five tests that pinned the old silence were
  rewritten (control ×2, types, arith, database), and the check immediately
  found a real defect in the ported `examples/monkd.pld`: `ЗАКРАСКА` called with
  four arguments.
* **Call-site warnings** run after the whole unit and its imports are loaded, so
  forward and mutual references stay quiet (a test pins a mutual-recursion
  program).  The meta-predicates whose arguments are goals are opened up
  (`ВЫП`, `НЕ`, `ИЛИ`, `НАЙТИВСЁ`, `,`/2); `!` is skipped as a name.  The
  suggestion is the nearest name of the same arity within a small edit distance
  over *code points* (one Cyrillic letter = one edit), and the comparison is
  ordered by `std::map`, so a suggestion never depends on hash order.
* **Singleton variables**: in a fact the message names the quotes
  (`запишите её в одинарных кавычках: 'Лена'`), in a rule it also offers the
  wildcard (`если это пропуск, назовите её _Лена`), in a body it is the wildcard
  only.  Checking the corpus with it found eight unused variables in
  `drawing.pld`, lessons 6 and 7 and monk/monkd; all were fixed.  The debug
  appendix keeps one warning on purpose — it is the lesson's example.
* Not done, on purpose: the `--lint` pass (unused predicates, duplicated
  clauses) stays out, as the note above says.
* `Severity::Note` exists but nothing emits it yet: it is there for a remark that
  goes *with* another diagnostic, and inventing a user for it now would be worse
  than leaving the slot.
