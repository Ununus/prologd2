# task_107 — the names marker has no English spelling

**Status:** done (2026-10-24) — ADR-045, part 174
**Depends on:** task_67 (the marker), task_106 (the statement templates)
**Milestone:** 2.6.0

## Goal

The owner asked to remove `variables` — the English spelling of `ИМЕНА` — from the
alias table and from the engine.

## Why it had to go

The marker is not a normal builtin.  The mode of a file is read by
`readVariableMarker` *before* the file is lexed, and that reader matches the word
`ИМЕНА` and nothing else.  `variables` was registered by the same `add` that
registers every alias, so it was callable, offered by completion, listed by
`--list-keywords` and documented — and a file that started with
`:- variables(0).` set nothing: the line fell through to the directive, and the
builtin answered «режим имён задаётся первой строкой файла» (checked on the engine:
exit 3, while the Russian line loads).  A name that can only fail is worse than no
name.

## What was changed

- `builtins.cpp`: `{"ИМЕНА", "variables"}` left `kEnglishNames`.
- `lexer.cpp`: `"variables"` left `kReservedBuiltins` and joined
  `kRetiredBuiltinNames` — retired names stay reserved for the *checks* so a call is
  an error with an explanation, but they are not keywords and so never reach
  completion or `--list-keywords`.
- `checks.cpp`: the retired message — ««variables» снято: маркер имён пишется
  по-русски — «:- ИМЕНА(0|1|2).»».
- `doc/builtins.json`: `aliases: []` for `ИМЕНА`; `doc/help.typ` names the marker
  among the names without an English spelling, both in the appendix and in the
  `--dialect` paragraph.
- Tests: `test_aliases.cpp` gained `ИМЕНА` in `hasNoEnglishSpelling` and a case of
  its own; `test_diagnostics.cpp` pins the message.

## Checks

- `ctest` — **423** tests (one new), all pass.
- `test_reference.py` — 71 records over 128 reserved names (was 129), arities,
  variadic flags and kinds agree with the engine.
- The manuals build; pages 43–45 were looked at (the appendix row is gone, the
  paragraph after the table now names three exceptions).

## What was deliberately not done

- no redirect from `variables` to `ИМЕНА`: the word was never a working marker, and
  a silent redirect would hide a program that also lost its mode.
