# task_23 — GUI: one source of truth for the built-in names

**Status:** not started
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

- [ ] `prlib`: one function that returns the reserved names with their arity,
      built from the same table the lexer and the dispatcher use, so a new
      built-in cannot be forgotten in one place.
- [ ] `prlib`: it must be the *lexer* list that wins (a name is reserved because
      the lexer says so, even if the dispatcher has it under a different arity).
- [ ] CLI: `prologd --list-keywords` prints one `name/arity` per line, sorted,
      byte-exact UTF-8, exit code 0.  Machine-readable, so tests and scripts do
      not parse help text.
- [ ] Protocol v2: the `ready` event carries the names, e.g.
      `{"event":"ready","protocol":2,"version":"2.0.0","keywords":[{"name":"ВЫП","arity":1},…]}`.
      The GUI then needs no extra round trip and no version drift.  Bump
      `PROTOCOL_VERSION` in `src/gui/prologd_gui/protocol.py`, keep the C++
      constant in step (task_21 requirement), and document the change in
      `src/gui/README.md`.
- [ ] `prologd_gui/keywords.py` — Qt-free holder: parse the `keywords` field,
      expose `names()`, `arity(name)`, `is_reserved(name)`.
- [ ] Tests:
  * Catch2: every name the dispatcher registers is in the lexer's reserved set,
    and every reserved name is registered (no orphans in either direction);
  * CTest: `prologd --list-keywords` output parses, is sorted and contains
    `НАЙТИВСЁ/3`, `ВЫП/1`, `ПС/0`;
  * Python: `protocol.Decoder` accepts a `ready` event with and without the
    `keywords` field (an older interpreter must still work).

## Design notes

* The list is small (about 50 names) and static, so shipping it inside `ready`
  costs nothing and removes a whole class of "the GUI does not know about the
  new predicate" bugs.
* Arity is what makes completion useful (`ВЫВОД/1` vs `ВЫВОД/2`); report it as
  a number and *do not* fold it into the name.
* `doc/help.typ` already documents every predicate; a test could later compare
  the two lists, but the help text is prose — leave it as a manual check.

## Acceptance

`prologd --list-keywords` and the `keywords` field of the `ready` event carry
the same names in the same order, both derived from one table in `prlib`, and
the GUI has no hard-coded built-in list of its own.
