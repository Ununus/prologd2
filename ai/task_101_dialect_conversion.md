# task_101 — converting a source between the two dialects (Russian ↔ English)

**Status:** done (2026-10-23) — ADR-039, part 168
**Depends on:** task_39 (the English alias table), task_52/92 (`=`/`is`/`<`/`>`/
`=:=` are sugar over the Russian built-ins), task_55 (`\+` is the second spelling
of `НЕ/1`), task_99 (the same request already carries a conversion)
**Milestone:** 2.6.0

## Goal

The dialect answers to two sets of names — Russian built-ins and their English
aliases — and prints whichever the author wrote.  The owner asked for two menu
entries under «Сконвертировать исходник»: «Диалект: Русский в Английский» and
«Диалект: Английский в Русский», so that a Russian program can be printed as an
ISO-looking one and back.  The existing naming entries became «Имена: PLD в ISO»
and «Имена: ISO в PLD» at the same request.

## Rules (Russian → English; the other direction is their mirror)

| written | printed | why it is exact |
|---|---|---|
| `ВЫВОД(a)`, `НАЙТИВСЕ(…)`, `ИМПОРТ(…)`, `ВЫП(…)` … | `write(a)`, `findall(…)`, `import(…)`, `call(…)` | the alias table (`builtinAliases()`) plus the two names answered outside it |
| `РАВНО(A, B)` | `A = B` | `=` *is* `РАВНО/2` in the parser's table |
| `РАВНО(A, #B#)` | `A is B` | `is` builds `РАВНО(A, ЭКСПР(B))` — the same term as `#…#` makes |
| `БОЛЬШЕ(A, B)` | `A > B` | `>` *is* `БОЛЬШЕ/2` |
| `МЕНЬШЕ(A, B)` | `A < B` | `<` *is* `МЕНЬШЕ/2` |
| `НЕ(A)` | `\+ A` | `\+` builds `НЕ(A)` |
| `X is Y` | `РАВНО(X, #Y#)` | the same equivalence, read backwards |

What is *not* converted, and why:

- `ИЛИ/2` — the original dialect's word, and the one built-in without an English
  spelling (task_83).  Its arguments are converted, the name is not.
- `РАВНО(РАВНО(X, Y), Z)` — no sign spelling exists: `X = Y = Z` is a chain, and
  the language refuses chains.  The call keeps a name: `equal(X = Y, Z)`.
- a call with a comment inside it — rewriting it would lose the comment, so it
  keeps its name (`equal(X, % почему` … `Y)`), and the comment stays.
- a call of the wrong arity (`БОЛЬШЕ(X)`) — a name rename only.
- the marker line `:- ИМЕНА(N).` — `variables(0)` is not a marker, and the file is
  read by that line.

## Where it lives

`FormatOptions::dialect_out` (`std::optional<Dialect>`) and a pass inside
`formatSource` that runs **before** the names and the layout — one request can ask
for all three (`--format --names 0 --dialect en`).  The rewrite works on the token
list (`DialectConverter` in `formatter.cpp`) and copies every byte outside a
rewritten span as it was written; the answer is lexed and parsed again before it is
handed back, so a conversion can never turn a working file into a broken one.

The `is` rule is an equivalence, not a guess: `parseComparison` builds
`РАВНО(left, parseArithmeticOperand())`, and `parseArithmeticOperand` is
`ЭКСПР(parseAdditive())` — exactly what `#…#` makes elsewhere.  Checked by hand
before the code was written (`X is 1 + 1` and `РАВНО(X, #1 + 1#)` run alike), and
the fixtures run in both spellings with the same answers.

## Deliverables

- [x] prlib: the `dialect` pass, `Dialect`, `--dialect`-ready `FormatOptions`.
- [x] CLI: `--dialect ru|en`, composable with `--format` and `--names`.
- [x] protocol: `format` takes `dialect` (`en`/`ru`); version **16**.
- [x] window: the submenu lists four entries in two groups; the two new ones send
      `dialect` and open the answer in a tab of its own.
- [x] tests: six C++ cases (`test_formatter.cpp`) — every rule, the refusals, the
      way back, the marker and a fragment, and the three passes composing; the wire
      case `test_the_dialect_converts_over_the_same_request`; the menu case in
      `test_scripts.py`; the window case extended with one dialect conversion.
      `ctest` **422/422** (was 416).
- [x] docs: `help.typ` §15 (the flag and «Смена диалекта»), `gui.typ` §9 (four
      entries, the menu table, the changelog), ADR-039.

## What the owner asked to check

- `РАВНО/equal(X, Y)` → `X = Y`: **right**, `=` is literally `РАВНО/2`.
- `РАВНО/equal(X, #Y#)` → `X is Y`: **right**, and the reason is written above.
- What was missing: `НЕ/not(A)` → `\+ A` (ISO negation), `ИМПОРТ`/`ВЫП` (not in
  the alias table), and the cases where a sign cannot be written at all (a nested
  call, a comment, a wrong arity) — they keep a name instead of being dropped.
