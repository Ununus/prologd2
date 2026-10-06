# task_67 — режимы имён переменных (0 / 1 / 2)

**Status:** in progress (2026-10-06)
**Depends on:** task_04 (the lexer), task_14 (the loader), ADR-005 (the reserved set),
task_46 (a run option travels with the run)
**Asked for by:** the teacher's review — «расширить встроенный предикат `ПЕР` на
включение вариантов `ПЕР(0)`, `ПЕР(1)`, `ПЕР(2)`», which is the variable-naming
question he had raised before, numbered 0/1/2.

## What the three numbers mean

| Mode | A variable is | A bare capitalised name (`Молоко`) is |
|---|---|---|
| 0 (current) | `Имя`, `_`, `_Имя` | a variable (ISO: only a lowercase name is an atom) |
| 1 | **one letter**, upper or lower, with at most one `_` after it (`д`, `Б`, `В_`, `A_`) | a **string constant**, written without quotes |
| 2 | mode 1 **plus** any name ending with `'` | the same as in mode 1 |

Mode 0 is what the port ships and what the whole corpus — lessons, examples, tests,
`%!` promises — is written in, so it stays the default everywhere.

**Why this is a lexer mode and not a run-time switch.** The apostrophe: today `'` is
the *quote* of an atom (`'Молоко'`, `''` escapes), while in the old dialect it was the
*suffix* of a variable name (`Сумма'`). A name is classified while the text is read,
so `ПЕР(1)` as a goal inside a program cannot change how the text *above* it was
read. The switch therefore belongs to the file and to the run.

**1 is a subset of 2** in what it accepts; they differ in exactly one place: in
mode 1 an apostrophe name is an *error*, in mode 2 it is a variable. Keeping all
three is cheap — one flag in the name rule — and worth it: a student's `X'` in mode 1
gets a message instead of a silently different program.

## How the mode is switched

* **`:- ИМЕНА(0|1|2).` as the first line of the file** — the loader reads that line
  *before* the lexer runs, the way a shebang is read. Anywhere else it is an error
  saying where the marker belongs. The marker is deliberately **not** `ПЕР`:
  `ПЕР/1` is the ISO `var/1` type test and keeps its arity and its meaning.
* The command line: `--vars 0|1|2`, one run, like `--max-steps`.
* The window: a row in «Выполнение» («Имена переменных»), and the same value for the
  highlighter, completion and the formatter — otherwise a mode-1 file would be
  coloured and reflowed as if it were mode 0.

## Steps

- [x] 1. `LexerOptions{VariableMode}` + the rule in `Lexer::lexIdentifier` +
      `--vars 0|1|2` + lexer tests. No marker yet, no window.  Measured on the old
      corpus: `_old/lesson_6.pld` with its `%?места(д,к,м,н).` line uncommented
      answers `НЕТ` in mode 0 (the four letters are *atoms* there) and
      `д=1, к=3, м=4, н=2` in mode 1 — the answer its author wrote it for.
- [x] 2. The marker `:- ИМЕНА(N).` on the first line: the loader peeks at it, and a
      marker elsewhere is diagnosed with its own message.  Done: `readVariableMarker`
      in `engine.cpp` reads the first line with the ISO rules, `parseSource` starts the
      real lexing at that line's newline (so line numbers survive), and `ИМЕНА/1` —
      reserved in both spellings — answers a marker that is not in the first line.
- [x] 3. The window: the row «Имена переменных» in «Выполнение» (`auto` plus the
      three modes), the highlighter (`tokens.mode_from_first_line`, `set_mode`), the
      buffer watching its own first line (`refresh_variable_mode`), and `vars` on the
      wire for `load`, `query` and `format` — protocol 12.  `query` needs it most: a
      question clicked on a margin marker arrives *without* the file's first line, so
      without `vars` it was read in mode 0 and `?студент(Вова).` matched the first
      student instead of the one the file means.  Completion needed nothing: a mode
      changes how a name is *read*, not which names exist.
- [x] 4. `examples/lessons/_old/` became *checked* mode-1 examples — see the table below.
      Six of the eight files are now run by `checkedOldLessons()` in `test_lessons.cpp`,
      with their old `?` questions uncommented and their answers recorded as `%!` lines.
      This is the acceptance test for the mode: an old lesson answers what its author
      wrote it for only in mode 1.
- [x] 5. `doc/prologd-diff.typ` gained the section, `doc/help.typ` the marker (the
      flag was written there in step 1), `doc/gui.typ` the settings row and its
      effect on the highlighting, and `ai/conventions.md` the rule «a mode is per
      file, never per build», together with the note that only C++ owns the rule.

## The old corpus as the acceptance test

Every question of `examples/lessons/_old/` was measured on its own (a prefix of the file
per question; the difference is that question's answer) and either uncommented with its
`%!` lines or left a comment with the reason written above it.  The text of the old
lessons is **not** repaired: what does not run keeps its old shape and says why.

| File | Checked | What stayed a comment, and why |
|---|---|---|
| `_old/lesson_1.pld` | yes | `нод(30,125,н)` — never finishes |
| `_old/lesson_2.pld` | no | the file does not load: `РАВНО` called with one argument |
| `_old/lesson_3.pld` | yes | — |
| `_old/lesson_4.pld` | yes | `бинсорт(...)` — the answer is a list of thousands of elements, it prints megabytes and never finishes |
| `_old/lesson_5.pld` | yes | `ферзи(8,A)` — 92 solutions, too many rows; `парламент(7,4,c)` — never finishes |
| `_old/lesson_6.pld` | yes | `whoiswho(М,м,В,П,п)` — the old question has five arguments, the definition has three |
| `_old/lesson_8.pld` | yes | `рамка,шаг(12,12,3,1)` — draws the whole frame and never finishes (this line used to be live) |
| `_old/lesson_9.pld` | no | `оценка([...])` reads input (asks about every writer), and the questions after it are its answers; `Фиб(10,ф)` cannot parse — in mode 1 a name with a capital letter is a string constant, not a predicate |

Each of the six checked files starts with the same preamble: the marker and three comment
lines saying what mode 1 means, so a reader who opens one of them learns the rule from the
file itself.

## Design notes

* In modes 1 and 2 a bare capitalised name lexes as **`String`**, not as an atom:
  the original kept strings and symbolic constants in one storage, and old programs
  call string predicates (`СЦЕП`, `ДЛИНА`, `КОПИЯ`) on such names. Printing is
  unchanged — this dialect prints strings without quotes — so the mode is invisible
  exactly where it should be invisible.
* `'` keeps its positional meaning: at the *start* of a token it opens a quoted
  atom in every mode; in mode 2 a `'` directly after a name makes that name a
  variable.
* The reserved built-in set wins over both modes (ADR-005): `ИМПОРТ` stays a
  predicate name whatever its case is.
* The formatter and the window's tokenizer must be given the same mode, or a
  `--format` round trip in mode 1 would disagree with the text it was given.
