# task_23 — GUI: one source of truth for the built-in names

**Status:** done
**Depends on:** task_21
**Milestone:** M11

## Goal

The front-end needs the list of reserved names (built-ins) for highlighting,
autocompletion and the shorthand key combinations.  That list must come from the
interpreter, not from a copy in the GUI: today the names live in
`src/prlib/src/lexer.cpp` (reserved atoms), `src/prlib/src/builtins.cpp`
(registration with arity) and are duplicated a third time in
`ai/_ref/.../Highlighter.cpp` + `MainWindow.cpp` in the old GUI.

## Deliverables

- [x] `prlib`: one function that returns the reserved names with their arity,
      built from the same table the lexer and the dispatcher use, so a new
      built-in cannot be forgotten in one place.
- [x] `prlib`: it must be the *lexer* list that wins (a name is reserved because
      the lexer says so, even if the dispatcher has it under a different arity).
- [x] CLI: `prologd --list-keywords` prints one `name/arity` per line, sorted,
      byte-exact UTF-8, exit code 0.  Machine-readable, so tests and scripts do
      not parse help text.
- [x] Protocol v2: the `ready` event carries the names, e.g.
      `{"event":"ready","protocol":2,"version":"2.0.0","keywords":[…]}`, where an entry is
      `{"name":"ВЫП","kind":"predicate","arities":[1]}`.
      The GUI then needs no extra round trip and no version drift.  Bump
      `PROTOCOL_VERSION` in `src/gui/prologd_gui/protocol.py`, keep the C++
      constant in step (task_21 requirement), and document the change in
      `src/gui/README.md`.
- [x] `prologd_gui/keywords.py` — Qt-free holder: parse the `keywords` field,
      expose `names()`, `arity(name)`, `is_reserved(name)`.
- [x] Tests:
  * Catch2: every name the dispatcher registers is in the lexer's reserved set,
    and every reserved name is registered (no orphans in either direction);
  * CTest: `prologd --list-keywords` output parses, is sorted and contains
    `НАЙТИВСЁ/3`, `ВЫП/1`, `ПС/0`;
  * Python: `protocol.Decoder` accepts a `ready` event with and without the
    `keywords` field (an older interpreter must still work).

## Design notes

* **A name has a kind, not just an arity.**  Implementation showed four cases
  the first draft missed:
  * `mod`, `div` are reserved but are infix operators — they have no dispatch
    entry at all;
  * `ИМПОРТ` is a statement form the loader handles, not a callable predicate;
  * `ВЫВОД` accepts *any* positive arity, so no arity list can describe it;
  * `ВЫП/1` is answered by the engine before it consults the dispatch table
    (`Solver::unifyGoal`), so `findBuiltin` never sees it — the same is true of
    the conjunction `,`/2, which is punctuation and not a reserved name.

  Hence `KeywordKind { Predicate, Operator, Directive }` plus a `variadic` flag,
  and the rule that `Predicate` means "has arities or is variadic".  Without the
  flag `ВЫВОД` would silently vanish from the list.
* **A predicate may have several arities.**  `ВЫВОД/1`, `УМНОЖЕНИЕ/3` and
  `УМНОЖЕНИЕ/4` are different call shapes of one name, so arities are reported as
  a sorted list and completion offers one entry per arity.
* The list is small (about 65 names) and static, so shipping it inside `ready`
  costs nothing and removes a whole class of "the GUI does not know about the
  new predicate" bugs.
* Rendering: `--list-keywords` prints one `name/arity` per line, a bare name for
  an operator or a directive, and `name/+` for the variadic one, so the output
  is one line per call shape:

  ```
  ABS/2
  ...
  ИМПОРТ
  НАЙТИВСЁ/3
  УМНОЖЕНИЕ/3
  УМНОЖЕНИЕ/4
  ВЫВОД/+
  mod
  ```

* The reverse drift check needs a list of what the *dispatcher* knows, so
  `builtinNames()` lives next to `findBuiltin` — the Catch2 test asserts every
  registered name is reserved (a built-in the lexer does not reserve would be
  parsed as a variable and never called).  Names the engine answers itself are
  not part of that list: they are guarded by the assertion that `ВЫП` is a
  reserved predicate of arity 1.
* `doc/help.typ` already documents every predicate; a test could later compare
  the two lists, but the help text is prose — leave it as a manual check.

## Acceptance

`prologd --list-keywords` and the `keywords` field of the `ready` event carry
the same names in the same order, both derived from one table in `prlib`, and
the GUI has no hard-coded built-in list of its own.

**Result.** 59 reserved names; `src/gui/tests/test_keywords.py` compares the two
lists element by element (the CLI lines against the decoded `ready` event).  The
Catch2 test lives in `src/tests/test_keywords.cpp` (6 cases) and two CTest
entries cover the CLI shape.
