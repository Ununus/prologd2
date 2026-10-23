# task_99 — converting a source between the name modes (PLD ↔ ISO)

**Status:** planned (2026-10-23) — deliberately not started
**Depends on:** task_67 (two name modes), task_77 (`2` merged into `1`), the
formatter (`--format`)
**Milestone:** post-2.5.0

## Goal

A program written in the old naming should be printable in the ISO naming and
back.  The engine already *reads* both (`--vars`, the file's own `:- ИМЕНА(N).`)
but prints the names it was given; the window already formats through the
protocol, and that is the same kind of request.  The owner asked for two menu
entries — `Скрипты → Сконвертировать исходник → «PLD to ISO» / «ISO to PLD»` —
with the answer in a new unnamed tab.

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

The reverse direction is not symmetric, and that is where the losses are:

- an ISO variable keeps its name if it is one letter or a letter plus `_` (`X`,
  `X_`) and otherwise gets an apostrophe: `Сумма'`, `Var1'`, `X_1'` — the old
  lexer accepts any name followed by `'`;
- an ISO **atom of one letter** (`x`, `Б`) has no old spelling at all — only
  `"x"`, which is a string;
- a quoted atom (`'a b'`, `'X_3'`) has none either — only `"a b"`;
- a string that happens to be a bare capitalised name loses its quotes:
  `"Str"` → `Str`.

## Numbering (proposed, to be confirmed)

Base = the name with its first letter capitalised and the apostrophe dropped.  If
one variable has that base it is printed bare (`Var1`, `Var2`).  If several share
it (`X`, `x`, `X'`, `x'`), all of them are numbered `X_1`…`X_n` in order of first
appearance — the owner's example.  A base that is a reserved name gets a suffix
(`И'` → `И_1`), because in ISO `И` is a predicate and not a variable.

## To settle before starting

- an atom with no old spelling: replace it by a string and report a warning in
  «Проблемы», or refuse and open no tab?  (Proposed: replace and warn.)
- `--names 0|1` on the command line beside `--format` — at once, or the protocol
  first and the CLI later?
- the protocol's `format` request gains a target mode, so the version goes up by
  one in the four places it is written down.

## Deliverables (none begun)

- [ ] prlib: a token pass that renames variables and strings and rewrites the
      marker; whitespace and comments stay put, so it composes with `--format`.
- [ ] CLI: `--names 0|1` — «print the source with the names of this mode».
- [ ] protocol: `names_out` on the `format` request; version bump.
- [ ] window: the submenu under «Скрипты», two actions, the answer in a new
      unnamed tab; the buffer's own mode (`buffers.variable_mode`, taken from the
      marker) says which direction makes sense.
- [ ] tests: the round trip PLD → ISO → PLD returns the same names but for the
      numbering; `X_`; `_Имя`; a variable whose base is a reserved name; a
      one-letter atom in the reverse direction; the marker line.
- [ ] docs: `help.typ` (the naming section), `doc/gui.typ` §9, ADR-038.

## Measurements of the field (2026-10-23)

- `maze.pld` is the newest file in the ISO naming and reads as one; `#...#` in
  `maze.graphics.pld` is mode-independent (the lexer emits `Hash` in both modes),
  so it is a good test case for «nothing but names changes».
- The old naming is exercised by `examples/prologd/` (untouched upstream) and by
  the lessons `ai/tools/port_lessons.py` once converted.
