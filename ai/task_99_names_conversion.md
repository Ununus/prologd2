# task_99 — converting a source between the name modes (PLD ↔ ISO)

**Status:** superseded (part 212) — the conversion was removed from the engine,
the protocol is back to 14 and the menu entry is gone; kept as the record of the
work.  Was: done (2026-10-23) — ADR-038, part 166
**Depends on:** task_67 (two name modes), task_77 (`2` merged into `1`), the
formatter (`--format`)
**Milestone:** 2.6.0

## Goal

A program written in the old naming should be printable in the ISO naming and
back.  The engine already *reads* both (`--vars`, the file's own `:- ИМЕНА(N).`)
but prints the names it was given; the window already formats through the
protocol, and that is the same kind of request.  The owner asked for two menu
entries — `Скрипты → Сконвертировать исходник → «PLD to ISO» / «ISO to PLD»` —
with the answer in a new unnamed tab.  (The titles became `PLD в ISO` and
`ISO в PLD` at the owner's request, part 167.)

## Decisions

- [x] **The marker is printed always**: `:- ИМЕНА(0).` for the ISO naming and
      `:- ИМЕНА(1).` for the old one, in both directions — even though a file
      without a marker is read as ISO.  A converted file says what it is.
      (Owner's decision, 2026-10-23.)
- [x] **The conversion lives in the engine**, not in a script under `tools/`, and
      rides the request the formatter already takes.  The lexer classifies names by
      mode (`lexIdentifier`, `isOldVariableName`, the reserved table, the
      apostrophe suffix); `ai/tools/port_lessons.py` — the only Python attempt —
      knows neither `:- ИМЕНА`, nor `'атом'`, nor `#...#`, nor `A_`, nor `\"` in a
      string, and renames keywords (`ИЛИ` → `ПЕРВОЕ`) as a side effect.  A second
      lexer in Python would be a second source of truth, drifting on the first
      unusual file.

## Rules (old naming → ISO), as `lexer.cpp` reads them

| written in the old mode | what it is | printed as ISO |
|---|---|---|
| `x`, `X`, `д` | Variable (one letter) | `X_1`, `X_2`, … |
| `X_` | Variable (letter + `_`) | `X_` |
| `X'`, `var1'`, `Сумма'` | Variable (apostrophe suffix) | `X_3`, `Var1`, `Сумма` |
| `Str`, `X_3` | **String** (bare capitalised name) | `"Str"`, `"X_3"` |
| `atom`, `функ` | Identifier (atom) | unchanged |
| `"Str"` | String | unchanged |
| `_`, `_Имя` | Variable | unchanged |
| `ЛОЖЬ`, `И`, `ПЕРВОЕ` | Identifier — a reserved name wins in both modes | unchanged |

The reverse direction is not symmetric, and that is where the losses are — though
task_100 removes most of them: once the pinned original reads `'атом'` and `_имя`
(task_100), an ISO atom gets a spelling in the old naming (`x` → `'x'`, a quoted
`'a b'` → `'a b'`) instead of being turned into a string.

- an ISO variable keeps its name if it is one letter or a letter plus `_` (`X`,
  `X_`) and otherwise gets an apostrophe: `Сумма'`, `Var1'`, `X_1'` — the old
  lexer accepts any name followed by `'`;
- an ISO atom that is not a plain lower-case name is quoted: `'x'`, `'a b'`,
  `'X_3'` — readable by the original since task_100 (before that pin the only
  spelling was `"x"`, a string, and the meaning changed);
- a string that happens to be a bare capitalised name loses its quotes:
  `"Str"` → `Str`;  *(not done as written: `"Str"` is a string in both modes, so
  the quotes stay — see «What was decided» below)*
- what stays lost: an atom containing a `'` — the old dialect reads `'…'` up to the
  first closing quote and has no doubled-quote escape.

## Numbering (implemented as proposed)

Base = the name with its first letter capitalised and the apostrophe dropped.  If
one variable has that base it is printed bare (`Var1`, `Var2`).  If several share
it (`X`, `x`, `X'`, `x'`), all of them are numbered `X_1`…`X_n` in order of first
appearance — the owner's example.  A base that is a reserved name gets a suffix
(`И'` → `И_1`), because in ISO `И` is a predicate and not a variable.

## Settled before starting

- ~~an atom with no old spelling~~ — settled by task_100: the new pin reads
  `'атом'` and `_имя`, so the conversion quotes instead of turning the atom into a
  string.  Only an atom containing `'` has no spelling at all; it is left as it is
  rather than refused, because a refusal would block a whole file over one atom.
- ~~`--names 0|1` on the command line beside `--format` — at once, or the protocol
  first and the CLI later?~~ — at once: one pass, one place, and the window needed
  the wire on the same day.
- ~~the protocol's `format` request gains a target mode, so the version goes up by
  one in the four places it is written down~~ — done: 15.

## Deliverables (all done, 2026-10-23)

- [x] prlib: a token pass that renames variables and strings and rewrites the
      marker; whitespace and comments stay put, so it composes with `--format`.
      `FormatOptions::names_out` (`std::optional<VariableMode>`) plus
      `variableNames(tokens, from, to)` in `formatter.cpp`; the `Formatter` keeps a
      `replacements_` map and prints a name through it.  `utf8::upperCaseFirst` is
      the new helper (`prlib/utf8.hpp`).  A trailing apostrophe after an old-mode
      variable is folded into the token's span, so a rename cannot leave a stray
      `'` behind; an old-mode string whose source byte is not `"` is printed quoted.
- [x] CLI: `--names 0|1` — «print the source with the names of this mode».  It goes
      through the formatter branch (`--format` and `--names` may be asked for
      together), refuses `--protocol json` like `--format`, and exits 2 on a source
      that does not parse.
- [x] protocol: `names_out` on the `format` request (key `names`); version 15,
      written down in four places (`protocol.cpp`, `protocol.py`,
      `protocol_session.cmake`, `test_formatter.py`).
- [x] window: the submenu under «Скрипты», two actions (`names_iso`, `names_pld`,
      `needs=engines.FORMAT`), the answer in a new unnamed tab; `convert_names()`
      sends the formatter request with `names` and `_show_converted()` opens the
      tab.  The buffer is never rewritten, the status says «имена переведены в
      режим ISO/PLD: N строк в новом табе», and the direction is the user's (both
      entries are always live: a marker-less file is read as ISO, but the owner
      may know better).
- [x] tests: 5 cases in `src/tests/test_formatter.cpp` (old → ISO with numbers and
      quotes; shared bases `пара(Х,х,Х',х')` → `пара(Х_1,Х_2,Х_3,Х_4)`; ISO → old;
      the marker replaced and added; the way back keeping what it can), the wire
      case `test_the_names_convert_over_the_same_request` in
      `src/gui/tests/test_formatter.py`, the menu case in `test_scripts.py` and
      `test_the_conversion_opens_in_a_tab_of_its_own` in `test_window.py`.
- [x] docs: `doc/help.typ` (the `--names` flag, «Смена режима имён» with both rule
      lists, a pointer from §2), `doc/gui.typ` §9 (the submenu, the new paragraph,
      the menu table and the changelog bullet), ADR-038.

## What was decided while doing it

- **`--names` on the command line and on the wire at once.**  The two are the same
  pass and the same code; doing the CLI first and the protocol later would have
  meant writing the worker twice.
- **Numbering is global per file**, in order of first appearance, with a `taken`
  set and a bump loop (a variable may be *named* `Х_1`, and then `Х` takes `Х_2`).
  This differs from the owner's illustrative example, which numbered per clause;
  one old name must become one ISO name everywhere, or the program stops meaning
  the same thing.
- **An atom the old dialect would read as a variable takes quotes** (part 167,
  the owner's example): `?одно(а, а).` in ISO asks about a constant, and the old
  dialect reads one letter as a variable — it answered `а=_1`.  `а` → `'а'`, `а_`
  → `'а_'`, and the same for a one-letter functor (`а(1).` → `'а'(1).`); long names
  (`атом`, `а1`) and an already quoted `'а'` stay as they are.
- **A string stays a string in both directions.**  `Str` → `"Str"` (a bare
  capitalised name is a string in the old mode, a variable in ISO), and `"Str"`
  comes back unchanged — unquoting it would be a change of nothing.
- **A fragment is never renamed** (`selection_only`): the numbering needs the whole
  program, and a fragment numbered on its own would disagree with its own file.
- **The marker is printed always** (owner's decision, kept) — `withModeMarker`
  replaces the first line when it is a marker and prepends one otherwise.
- **The window forces `soft`** whatever the «Форматировать» control says: the
  answer is a program to read, not a line.
- **An atom containing `'` is left as it is**, not refused: the old dialect reads
  `'…'` up to the first closing quote and has no escape, so that one spelling is
  lost — and the conversion never turns an atom into a string to save it.

## Measurements (2026-10-23)

`build\probe-convert-old.pld` — `:- ИМЕНА(1).` / `пример(Х,х):-функ(Str),второй(Х').`:

```
prologu --names 0        :- ИМЕНА(0).
                         пример(Х_1,Х_2):-функ("Str"), второй(Х_3).
prologu --format=hard --names 0
                         :- ИМЕНА(0).
                         пример(Х_1,Х_2):-
                                 функ("Str"),
                                 второй(Х_3).
```

Round trip: ISO → `--names 1` → `пример(Х_1',Х_2'):-функ("Str"), второй(Х_3').`,
and `--names 0` on that file gives the first ISO text word for word.  Both files
load (`exit 0`).

`ctest` **415/415** (was 410), the 26 GUI scripts, `protocol_smoke.py` and the six
PDFs are green; the changed pages looked at: `help` 38–40 (the flag and the rules),
`gui` 30–32 (the paragraph and the menu table).

## Measurements of the field (2026-10-23)

- `maze.pld` is the newest file in the ISO naming and reads as one; `#...#` in
  `maze.graphics.pld` is mode-independent (the lexer emits `Hash` in both modes),
  so it is a good test case for «nothing but names changes».
- The old naming is exercised by `examples/prologd/` (untouched upstream) and by
  the lessons `ai/tools/port_lessons.py` once converted.
