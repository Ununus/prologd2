# task_34 — Every branch of every built-in

**Status:** done
**Depends on:** task_09, task_10, task_11, task_12, task_13, task_15
**Milestone:** M5 (verification)

## Goal

The user asked whether *all* branches of the built-in predicates work, and to put
every one of them — including the edge cases — into the tests:

> Давай проверим что все ветки предикатов работают корректно. Добавим в тесты все
> ветки. … также добавь краевые случаи, например — целое1 <= 0 — целое1 > длины
> строка1 — целое2 > длины строка1

So this is a verification round, not a feature round.  The method matters more
than the tests it produced:

1. list the branch structure from the source of each built-in group;
2. drive the *built* `prologd.exe` over each branch (bound, free, wrong type, out
   of range, empty list/string, end of input) and write down what comes back;
3. only then decide whether an answer is a defect or the port's documented
   behaviour (several surprises turned out to be faithful: the truncating integer
   arguments, `УДАЛЕНИЕ`'s clamp, `#1/2#` = 0, `СПИСОК([1|2])` being a list);
4. write the expectation from the measured answer, never from the intention;
5. fix what is a defect and document the behaviour change.

## What the sweep found

Six defects, each fixed and covered by a test:

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 1 | `SQRT(-4, X)` → `X=0`, `SQRT(-4.0, X)` → `X=nan`, `EXP(X, -1.0)`, `SIN(X, 2.0)`, `COS(X, 2.0)` → `nan` | `std::sqrt`/`ln`/`asin` of a value outside the domain returns `nan`, `BigInt::fromDouble(nan)` is 0, and unification put that in the variable | a value the function does not have is a **failure**; `std::isfinite` guards in `builtinSqrt` and `unaryFloat` |
| 2 | `РАВНО(16777217, 16777216.0)` true, `РАВНО(16777217, 16777217.0)` false | the integer was narrowed to `float` and compared with the double, so the two sides were compared in different precisions | compare exactly: the real must be whole and `BigInt::fromDouble(real)` must equal the integer |
| 3 | `?РАВНО(X, f(X)).` ended the process (0xC00000FD, stack overflow); `?РАВНО(X, [1|X]).` never ended | no occurs check, so the query builds a cyclic term, and the printer followed it (a cyclic list in a loop, without depth growth) | the printer remembers the nodes it is inside and writes `...`; the term copy behind `ДОБ`/`НАЙТИВСЕ` reports "Циклический терм нельзя скопировать"; the print depth default is 2000, not 100000 |
| 4 | `ВВОДЦЕЛ(X, "Число: ")` printed no prompt | the documented second argument was never read (nothing in the engine knew about a prompt) | `writePrompt` writes it before the read; a non-text prompt is a type error |
| 5 | `ТОЧКА(a, 1, 2)`, `ЛИНИЯ(1, 1, 2, 3, a)`, `ЗАКРАСКА([1], 1, 2)` … all *succeeded* | every call site dereferenced `std::optional` from `asInteger` without checking — undefined behaviour, which happened to read memory instead of raising | every non-free argument is validated by `coordinate(...)` |
| 6 | `ВВКОД(1114112)`, `ВВКОД(55296)` wrote four bytes that are not UTF-8 | `utf8Encode` encodes any value, only negative ones were rejected | a code point must be a Unicode scalar value (0…U+10FFFF, no surrogates) |

## Deliverables

- [x] Branch tests for the string group (`test_builtins_string.cpp`, rewritten):
      `СЦЕП`'s four modes and the empty string, `КОПИЯ`'s five modes with the
      negative-length meanings, the range edges (position 0, -1, past the end,
      zero length, empty source), `ДЛИНА`, `БУКВА`/`ЦИФРА` (first match, position,
      past the end), `СТРЦЕЛ`/`СТРВЕЩ`/`СТРСПИС`, and one type-error check per
      predicate.
- [x] Branch tests for arithmetic (`test_builtins_arith.cpp`): all comparison
      branches, `ABS`/`SQRT` including the negative root, the four float functions
      with their domain edges, `УМНОЖЕНИЕ/3` and `/4` in every mode (including the
      zero multiplier, which is legal, and the zero divisor, which is not),
      `СЛОЖЕНИЕ`, `int`/`float`/`ЦЕЛВЕЩ`, `СЛУЧ` with a seed and a truncated range.
- [x] Branch tests for the database (`test_builtins_database.cpp`): `СКОЛЬКО` over
      several arities and an unknown name, `ПРЕДЛ` numbering, head/body matching
      and renaming, `ТЕРМ` in both directions with lists as arguments, `ДОБ`
      positions (front, middle, end, past the end, 0, negative, fractional), the
      atom-as-fact case, `УДАЛЕНИЕ` including the clamp, and the snapshot a running
      enumeration keeps.
- [x] `test_builtins_control.cpp` (new, from `task_09`'s plan): `ЛОЖЬ`, the four
      branches of `НЕ` (including "bindings undone, database not"), `ИЛИ` with its
      commitment, `ТИХО` as a per-query flag, `ТРАССА`/`НЕТ_ТРАССЫ`, and the error
      for an argument that is not a goal.
- [x] `test_builtins_types.cpp` (new, from `task_09`'s plan): a truth table for
      `ПЕР`, `ЦЕЛ`, `ВЕЩ`, `СИМВ`, `СПИСОК` over variable, integer, real, atom,
      string, list cell, `[]`, compound and expression; the integer/real
      comparison at both precision edges; the cyclic term (printed, not followed;
      copied, refused).
- [x] Branch tests for I/O (`test_builtins_io.cpp`): `ВВКОД` writing and reading
      code points and refusing the invalid ones, the comparisons of the four
      reading predicates, the failures (unparseable token, end of input, trailing
      junk), whole lines versus tokens, the prompt, and `ЧТЕНИЕ_ИЗ`/`ЗАПИСЬ_В`.
- [x] Branch tests for graphics (`test_graphics.cpp`): the mode chosen by each
      combination of free arguments, the wrong-type error, and a real coordinate
      being truncated.
- [x] `test_findall.cpp`: the copy semantics (binding the list does not bind the
      template and the other way round), a bound list argument, a template that is
      not a variable, a nested `НАЙТИВСЕ` and an error from the goal.
- [x] `test_unify.cpp`: the integer/real comparison at the precision edges.
- [x] `doc/help.typ`: §4.4 (negation and the database), §4.6 (numbers, cyclic
      terms), §5.5–5.6 (domains — a behaviour change), §5.7, §6.3 (code points),
      §6.4–6.7 (prompts, failures, token/line interplay), §7.1–7.5 (string edges),
      §9 (the type tests), §11 (database clamps and numbering), §14 (graphics
      arguments).

## Acceptance

`prlib_tests.exe` is green (186 cases, 2733 assertions) and `ctest` is green
(197/197), as are the fifteen offscreen GUI scripts.  The test-case *names* are
ASCII, because the discovery step reads the test binary's output through the
console code page (see `src/tests/CMakeLists.txt`); the goals inside the tests are
Russian as everywhere else.
