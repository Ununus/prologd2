# task_35 — the lesson course: rebuilt from scratch

**Status:** done — all twelve lessons and the appendix are written, and
`every lesson prints exactly what its comments promise` runs each file whole and compares
the output with its `%!` blocks.
**Depends on:** task_18 (the ported examples), task_10 (strings), task_12 (the database)
**Milestone:** M6 (documentation and teaching)

## Why the old course had to be rebuilt

The lessons in `examples/lessons/` were a port of the old course and had not been touched:

1. **The expected output is written down nowhere.**  A reader cannot check himself, and a
   change in semantics goes unnoticed: lesson 3 had silently drifted apart from `КОПИЯ`
   and would have drifted further but for a question about `сколько(идиотизм,"и",Q)`.
2. **The queries were commented out.**  Lesson 2 had no active query left, lessons 3 and 4
   had one each; running a file showed almost nothing.
3. **The tests sidestepped the queries.**  `test_lessons.cpp` stripped them with
   `withoutQueries()` and only checked "it parses and is silent".
4. **Mixed style.**  Single-letter variables of the old dialect (`С`, `Х`), `%и=Боря` next
   to `% н=1 н=2 н=3`, no consistent headings.
5. **Duplicate definitions inside a file.**  Lesson 5 defined `список/2`, `можно/2`,
   `нельзя/2` twice (the queens and the parliament), so the file could not be run whole —
   recorded in `ai/porting_notes.md`, but in the reader's way.
6. **Lesson 8 could not be run.**  Its active query was an endless animation
   (`?рамка,шаг(12,12,3,1).`): an infinite loop in the console and a timeout in a test.
7. **There was no lesson 7** and no explanation of the numbering (1–6, 8, 9).
8. **There was no index.**  Neither `README.md` nor `doc/help.typ` said in what order to
   read the lessons or what each of them covers.
9. **Not covered at all:** `ИМПОРТ` and modules, `НАЙТИВСЕ`, input/output and dialogue,
   the trace and stepping, `ТИХО`/`ВЕРСИЯ`.

## The principles of the new course

1. **One lesson, one topic**, opening with its goal and "what you need to know first".
2. **Every example is a working query with its expected output beside it**, right in the
   file:
   ```prolog
   ?СЛОЖЕНИЕ(5, 7, Х).
   %! Х=12
   ?СЛОЖЕНИЕ(5, 7, 13).
   %! НЕТ
   ```
   `%!` is a machine-readable expectation (a plain `%` stays prose).
3. **The lessons check themselves.**  `test_lessons.cpp` no longer strips the queries: it
   parses a file, runs it in one go (the order of queries is the order of the output) and
   compares the output with the `%!` blocks.  A lesson cannot "go stale" unnoticed — CI
   fails.  A lesson with input has a `<lesson>.input.txt` beside it, fed through
   `runProgram(source, input)`.  The check has no timeout: a lesson with an endless
   recursion would not fail it but **hang** the run, so every lesson is run by hand before
   it enters `checkedLessons()`.
4. **No duplicate names inside a file**: every lesson is a program of its own, and a
   repeated name gets a suffix or moves into the library.
5. **Comments explain "why"** rather than retelling the code: the traps of the dialect
   (`#expr#` evaluates on binding, the order of goals, cut and `НЕ`, no occurs check, the
   search direction of `КОПИЯ`, `ТИХО` as a per-query flag), and at the end of a lesson
   "what you know now" with links to the sections of `doc/help.typ`.
6. **Exercises at the end of a lesson** (2–4), each with a solution in a comment block
   (`% Решение: …`).
7. **One style:** `:-`, variables `Имя`/`_Имя`, `_` for the anonymous one, queries `?Цель.`,
   a 4-space indent only for continuations, lines no longer than 90 characters.

## The proposed order (12 lessons plus an appendix)

Part I is the language, part II the tasks, part III the tools.  Every lesson reuses the
material of the present lessons (the last column) — nothing is lost.

| № | Lesson | New | From |
|---|--------|-----|------|
| 1 | Facts, queries, variables | facts, `?`, `_`, atoms/strings/numbers, the order of answers, repeated variables | lesson 1 (start) |
| 2 | Rules, unification, enumeration | `:-`, variables in the head, the order of goals, alternatives, conjunction | lesson 1 (rules/alternatives) |
| 3 | Arithmetic | `#…#`, `СЛОЖЕНИЕ`, `УМНОЖЕНИЕ/3,4`, `БОЛЬШЕ`/`МЕНЬШЕ`, long integers, `ЦЕЛВЕЩ`, `int`/`float` | lessons 1–2 |
| 4 | Recursion, cut, negation | recursion and accumulators, `!`, `НЕ`, `ИЛИ`, `ЛОЖЬ`, `ВЫП`, "recursion optimisation" | lesson 1 (GCD, Fibonacci, `фи`) |
| 5 | Lists | `[H\|T]`, generation, `ДЛИНА`, `член`, `присоединить`, reverse, nth, deletion, `разные`, Hanoi, four sorts | lesson 4 |
| 6 | Strings and texts | `ДЛИНА`, `КОПИЯ` (5 modes), `СЦЕП`, `БУКВА`/`ЦИФРА`, `СТРЦЕЛ`/`СТРВЕЩ`/`СТРСПИС`; counting, replacing, deleting, reversing, brackets | lesson 3 |
| 7 | **Input, output, dialogue** (the missing topic) | `ВЫВОД`, `ПС`, `ВВОДЦЕЛ/ВЕЩ/СИМВ/СТР` with a prompt, `ВВКОД`, `ЧТЕНИЕ_ИЗ`/`ЗАПИСЬ_В`, `ТИХО`, `ЖДИ`; reading a file, "guess the number", a menu | **new**: today it is scattered (`угадай` in 2, the dialogue in 9) |
| 8 | Searching a state space | generate and test, cut in the enumeration, remembering what was visited | lesson 5 (the jugs, the queens, the parliament, the crossing) |
| 9 | Constraint tasks | "each was wrong once", `xor`, the table of solutions | lesson 6 (the criminal, who is who, the seats) |
| 10 | Meta-predicates and the database | `НАЙТИВСЕ/3`, `ВЫП`, `СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`, `ДОБ`, `УДАЛЕНИЕ`; a program that changes itself | lesson 9 + `НАЙТИВСЕ` (nowhere today) |
| 11 | Modules | `ИМПОРТ`, `-I`, the library `examples/lib/library.pld`, loading once, cycles | **new** |
| 12 | Graphics | `ТОЧКА`, `ЛИНИЯ`, `ОКРУЖНОСТЬ`, `ЗАКРАСКА`; a garden, a graph, a **terminating** animation | lesson 8 |
| A | Appendix: debugging | `ВЕРСИЯ`, `ТРАССА`/`НЕТ_ТРАССЫ`, stepping and the stack in the GUI, typical mistakes and their diagnoses | **new** |

Decided against: GUI elements as a separate lesson (there is `doc/gui.typ`), the innards of
the interpreter (there is `doc/technical.typ`), `ПОМОЩЬ` and the command-line directives
(there is `doc/help.typ` §15).

## Index and cross-references

* `examples/lessons/README.md` — the order, the topics, what comes before, the time, links
  to the sections of the manual; it is also the table of contents of the course.
* From `doc/help.typ`, every section gets a "example: lesson N" link (§4.4 → lesson 4,
  §7.4 → lesson 6, §11 → lesson 10, §14 → lesson 12).
* `README.md` — three lines about the course and a link to the index.

## The order of work (one lesson, one commit)

1. Tooling: extend `test_lessons.cpp` to read `%!` and `*.input.txt` (it fails first —
   that failure is the list of divergences).
2. Rewrite lessons 1→7 to the new plan, each one: the text, the examples with `%!`, the
   exercises, a `ctest` run.
3. Rewrite 8→12 and the appendix.
4. The index, the links from the manual and `README.md`, an entry in `porting_notes.md`
   (which lesson grew out of which) and in `ai/status.md`.
5. Keep the old files as `examples/lessons/_old/lesson_N.pld` (the original material must
   not be lost) and say so in the index.

## Acceptance

* `ctest` runs every lesson and **compares the output** with the `%!` blocks: 12 + 1 lessons
  green, not one "it parses and is silent".
* Every lesson can be run whole (including the ones with input — through `.input.txt`),
  with no endless queries.
* No lesson defines one name twice, and none needs editing before it runs.
* Every lesson has a goal, a "what you need to know", examples with output, the traps,
  exercises with solutions and a "what you know now" list with links to the manual.

## Open questions — decided (2026-09-30)

1. **Twelve lessons plus an appendix** (the full course, three parts plus debugging).
2. **There is no lesson 7 in the sources** — its place is taken by "Input, output,
   dialogue".
3. **Two-digit file names**: `lesson_01.pld … lesson_12.pld`, the appendix
   `appendix_debug.pld` (the index, not the names, sets the order of study).
4. **`doc/lessons.typ` is written** — the fifth Typst document: the same course with prose
   between the examples, built by the `docs` target with the others.

## Result

All twelve lessons and the appendix are written and checked by
`every lesson prints exactly what its comments promise`.  The expectations were taken by
running the interpreter, not invented — which is how mistakes were found and fixed both in
the original material (the non-terminating `нод/3`, the descending sorts, the trap of
`?длина(Х, 2)`, a failed number read leaving the rest of the line) and in my own drafts.

The index of the course is `examples/lessons/README.md`, the document `doc/lessons.typ`.
The old files are in `examples/lessons/_old/`, and `ai/porting_notes.md` maps them.
Departures from the plan: "Hanoi" moved to lesson 5 (where it is solved with a list of
moves), "four sorts" shrank to two, the task about the fathers' surnames and professions
stayed in the archive, and lesson 4 gained small examples checking `НЕ`/`ИЛИ`/`ВЫП`.
