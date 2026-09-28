# task_09 — Built-ins: control, type tests, conversions

**Status:** done
**Depends on:** task_07, task_08
**Milestone:** M5

## Goal

Implement the control-flow built-ins, `ТРАССА`/`ТИХО`/`ВЕРСИЯ`, the type tests
(`ПЕР`, `ЦЕЛ`, `ВЕЩ`, `СИМВ`, `СПИСОК`) and the conversion predicates
(`ЦЕЛВЕЩ`, `СТРЦЕЛ`, `СТРВЕЩ`, `СТРСПИС`).

## Deliverables

- [ ] `src/builtins_control.cpp`
  * `!`, `ЛОЖЬ`, `ВЫП/1`, `ТРАССА`, `НЕТ_ТРАССЫ`, `ТИХО`, `ВЕРСИЯ`.
  * `ВЕРСИЯ` prints the configured version string (CMake `PROLOGD_VERSION`
    plus build date).
- [ ] `src/builtins_types.cpp`
  * `ПЕР/1`: true iff the argument dereferences to an unbound variable.
  * `ЦЕЛ/1`: integer, arithmetic expression evaluating to integer, or a variable
    bound to one.
  * `ВЕЩ/1`: float or numeric expression evaluating to float.
  * `СИМВ/1`: atom or string (bound or directly).
  * `СПИСОК/1`: list cell or `[]`.
- [ ] `src/builtins_convert.cpp`
  * `ЦЕЛВЕЩ/2`: int→float, float→int (truncation toward zero), or compare.
  * `СТРЦЕЛ/2`: string/atom→BigInt (accepts optional leading `+`/`-`),
    BigInt→string (decimal), or compare.
  * `СТРВЕЩ/2`: string/atom→double, double→string using the trimmed format, or
    compare.
  * `СТРСПИС/2`: string/atom ↔ list of UTF-8 code point values; on the
    list→string path values are taken modulo 255 (original behaviour);
    decode code points greater than 127 as UTF-8 when they form valid
    sequences, otherwise as Latin-1 (document precisely).
  * Conversion failures return failure (`No`), not an error, exactly as the
    original `try/catch` behaviour.

## Design notes

* These predicates must accept both `"string"` and bare atoms wherever the
  original `occ_line` accepted a `recordstring`; the original parser stored
  both atoms and strings so that string predicates accepted both.
* `СТРСПИС` is the bridge between byte-level strings and `ВВКОД`-style code
  predicates; tests must pin the chosen encoding policy for non-ASCII input.

## Tests

- [ ] `test_builtins_types.cpp`: a truth table for each type test over
      var/int/float/atom/string/list/compound/expression.
- [ ] `test_builtins_convert.cpp`:
      * `ЦЕЛВЕЩ(3,X)` → `X=3.0`, `ЦЕЛВЕЩ(X,3.7)` → `X=3`, compare cases;
      * `СТРЦЕЛ("42",K)`, `СТРЦЕЛ(gamma,K)` fails, `СТРЦЕЛ(N,"-17")`;
      * `СТРВЕЩ("3.14",K)`;
      * `СТРСПИС("АБИ",X)` → `X=[-64,-63,-56]`-equivalent **or** the documented
        Unicode policy — the test must match the implemented, documented
        policy and the help text must be updated accordingly;
      * `СТРСПИС(G,[-64,-63,-56])` round-trip.
- [ ] `test_builtins_control.cpp`: `ВЫП`, `ЛОЖЬ`, `ТИХО`, `ТРАССА` toggling.

## Acceptance

Type/conversion/control predicates have dedicated passing tests and are
documented in `doc/help.typ`.
