# task_10 — Built-ins: strings (`БУКВА`, `ЦИФРА`, `СЦЕП`, `КОПИЯ`, `ДЛИНА`)

**Status:** done
**Depends on:** task_09
**Milestone:** M5

## Goal

Implement the string predicates with all documented modes.

## Deliverables

- [ ] `src/builtins_string.cpp`
  * `БУКВА(S,P)` / `ЦИФРА(S,P)`: if `P` is bound, test `S[P]` (1-based,
    out-of-range → fail); if `P` is a variable, bind the 1-based position of the
    first letter/digit, or fail.
  * `СЦЕП(A,B,C)`: eight modes (see `reference_notes.md` / help):
      - `A,B` known → bind/compare `C`;
      - `A` known, `C` known, `B` variable → suffix removal (requires
        `|C| >= |A|`; note the original also required `|C| > |B|`, reproduce or
        document the fix);
      - `B` known, `C` known, `A` variable → prefix removal;
      - all known → exact comparison.
  * `КОПИЯ(S,Pos,Len,Sub)`: five modes including negative `Len` (search from
    the right) and the variable-position/length discovery modes.
  * `ДЛИНА/2` provided by the Prolog library clause
    `ДЛИНА(x,y)<-КОПИЯ(x,1,y,x);` (loaded in task_08); no native code.
- [ ] Position/length semantics are 1-based, `Len=0` yields `""`, `Pos=0` and
      out-of-range positions fail (original), documented explicitly.

## Design notes

* Operating on `std::string` with UTF-8 bytes vs code points is a real design
  question. Decide and document: the original treated strings as byte arrays
  (CP1251, so one byte per character). For UTF-8, positions in the new
  interpreter should be **code-point based** to keep `БУКВА`/`ЦИФРА`/`ДЛИНА`
  meaningful for text, but `ВВКОД`/`СТРСПИС` deal in code units. This decision
  must be consistent and recorded in `decisions.md` and `prologd-diff.typ`.
  Recommendation: code points for all string predicates, with `ВВКОД`/`СТРСПИС`
  explicitly defined in terms of code points as well.

## Tests

- [ ] `test_builtins_string.cpp`: all `КОПИЯ` cases from the original `COPY`
      test (`П=БВГ`, `Х=1`, `Х=6`, `Y=1`, failure cases), all `СЦЕП` modes,
      `БУКВА`/`ЦИФРА` including the `" абв "` examples, `ДЛИНА`.
- [ ] UTF-8 cases: `КОПИЯ("ПРОЛОГ",X,Y,"ЛОГ")` → `X=3,Y=3`;
      `КОПИЯ("ёжик",X,1,"ж")` → `X=2` (code-point semantics).
- [ ] Edge cases: empty string, `Len=0`, negative `Len`, position beyond the
      end, search not found.

## Acceptance

The original `COPY` test body passes after variable renaming, and UTF-8
behaviour matches the documented code-point policy.
