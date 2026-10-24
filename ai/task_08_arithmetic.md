# task_08 — Arithmetic expressions and numeric predicates

**Status:** done
**Depends on:** task_03, task_06
**Milestone:** M4

## Goal

Implement `#expr#` evaluation and the numeric built-ins with PrologD semantics.

## Deliverables

- [ ] `include/prlib/arith.hpp`, `src/arith.cpp`
  * `struct ArithValue { std::variant<BigInt, double> value; }`.
  * `ArithEvaluator` resolving variables through `Bindings`; variables bound to
    numbers are operands; anything else is `ErrorCode::ErrorInArithmeticExpression`
    (32).
  * Operators `+ - * / mod div` and unary `-`, with precedence and parentheses
    (AST produced by task_05).
  * Promotion: if any operand is float, compute in double; otherwise BigInt.
  * `/` and `div` on integers truncate toward zero; `mod` uses C++ remainder
    semantics; `mod`/`div` on floats → errors 34/35.
  * Division by zero → error 41.
  * `negate`, `abs`, `sqrt`, `sin`, `cos`, `tan`, `exp` helpers.
- [ ] `src/builtins_arith.cpp`
  * `БОЛЬШЕ/2` including int/float/atom-string comparisons
    (`reference_notes.md` §5); wrong types → `UnknownError` (24) with the
    original message convention.
  * `СЛОЖЕНИЕ/3`, `УМНОЖЕНИЕ/3`, `УМНОЖЕНИЕ/4` with all documented reversible
    cases (see the original user help).
  * `ABS/2`, `SQRT/2`, `SIN/2`, `COS/2`, `TAN/2`, `EXP/2` (compute or compare).
  * `int/1`, `float/1`.
  * `СЛУЧ/1`, `СЛУЧ/3` with a seeded `std::mt19937_64`.
- [ ] Prolog library clauses loaded at startup, exactly as the original:
  ```
  РАВНО(x,x).
  МЕНЬШЕ(x,y) <- БОЛЬШЕ(y,x);
  СЛОЖЕНИЕ(x,y,z) <- УМНОЖЕНИЕ(1,x,y,z);
  ПС <- ВВКОД(10);
  ДЛИНА(x,y) <- КОПИЯ(x,1,y,x);
  НЕ(x) <- ВЫП(x),!,ЛОЖЬ;   НЕ(_);
  ИЛИ(x,_) <- ВЫП(x),!;     ИЛИ(_,x) <- ВЫП(x);
  ```
  Note: `СЛОЖЕНИЕ` is also native; the native version wins at call time but the
  library clause remains visible to `СКОЛЬКО`/`ПРЕДЛ` (preserve this quirk).

## Design notes

* Conversion between `BigInt` and `double` must match the original's
  `convert_to<FloatType>()`.
* `SQRT` on integers: original computes `sqrt(double)` and compares; `zap1`
  cases use `l1*l1` (inverse is exact squaring). Reproduce exactly.
* `СЛУЧ/1` with a bound integer seeds `std::mt19937_64`; with a variable binds a
  number from -2147483648 to 2147483647.  Both `СЛУЧ/1` and `СЛУЧ/3` map the
  engine output to their range themselves (ADR-049), not through
  `std::uniform_int_distribution`, so a seeded run is the same on every platform.

## Tests

- [ ] `test_arith.cpp`: each operator, precedence, parentheses, mixed
      int/float, unary minus, division/mod/div semantics and errors.
- [ ] `test_builtins_arith.cpp`: all cases of `УМНОЖЕНИЕ/4` from the help,
      reversible `СЛОЖЕНИЕ`/`УМНОЖЕНИЕ`, `БОЛЬШЕ` for numbers and strings,
      `ABS`/`SQRT`/trig, `int`/`float`.
- [ ] `test_arith_big.cpp`: big-integer expressions such as
      `#123456789123456789123456789*123456789123456789123456789#` and the
      original `LONG ARITH` expectations.
- [ ] division-by-zero and type errors produce the documented codes.

## Acceptance

The arithmetic sections of the original `prologd_test/test.txt` (`Add`, `Mult`,
`Calculations`, `LONG ARITH*`) reproduce their expected output after variable
renaming.
