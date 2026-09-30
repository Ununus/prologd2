# task_18 — Port examples and build the acceptance test suite

**Status:** done
**Depends on:** tasks 07–14, 16
**Milestone:** M9

## Goal

Convert the original example programs and test corpus to the new standard
syntax, and add typical-task regression tests.

## Migration rules (old → new)

1. Every single-letter variable becomes an upper-case name (`х` → `X`, `ф` →
   `Ф`, `a` → `A`, …). Since a single Russian letter like `ф` may collide, use
   a deterministic table and keep it in `ai/porting_notes.md`.
2. Trailing-apostrophe variables (`история'`, `x'`) become normal upper-case
   names (`История`, `X`).
3. Upper-case atoms (`Россия`, `Миша`, `Капица`, `Денис`, `Иванов`, …) become
   quoted atoms (`'Россия'`).
4. Predicate names that start with an upper-case letter (`Фиб`, `ЧёЁ`, `XOR`)
   must be lower-cased (`фиб`, `чёё`, `xor`) — documented breaking change.
5. `;` terminators may stay or be changed to `.`.
6. Built-in names are unchanged.

## Deliverables

- [ ] `ai/porting_notes.md` — the variable-rename table plus per-file notes.
- [ ] `examples/` (new tree at repository root or under `src/`):
  * `lessons/lesson_1.pld` … `lesson_9.pld` converted (lesson 7 is absent in
    the original);
  * `examples/monk.pld`, `monkd.pld`, `ranez.pld`, `drawing.pld`,
    `factorial.pld`, `file_io.pld`;
  * `examples/findall_demo.pld` implementing the requirement.
- [ ] A Catch2 golden-test runner for the `TEST`/`INPUT`/`EXPECTED`/`END`
  format, reading the ported programs from `examples/`.
- [ ] At minimum these tests, each as a real Prolog program with expected
  output:
  * factorial, Fibonacci (iterative and recursive), GCD;
  * list predicates: `member`, `append`, `reverse`, `delete`, `select`;
  * sorting: bubble/insertion/quick/merge (from `lesson 4`);
  * N-queens (`lesson 5`), water jugs (`lesson 5`);
  * monkey and bananas (`lesson 5` перевоз);
  * parliament problem (`lesson 5` парламент);
  * **knapsack** (`рюкзак`) — add a new idiomatic PrologD program with a known
    answer, plus a test;
  * `НАЙТИВСЕ` examples from the requirement;
  * long arithmetic (`111!`, `1333!`).
- [ ] `ctest` runs the full suite; every previously passing original test that
      is still meaningful has an equivalent after porting.

## Design notes

* The old corpus mixes expectations that changed on purpose (variable printing,
  UTF-8 string codes). Where output changed by design, record the new expected
  output and the reason in the test file as a comment and in
  `prologd-diff.typ`.
* Keep tests fast: cap N-queens to 8×8 and sorting lists to reasonable sizes;
  long arithmetic is fine.
* Graphics examples (`lesson 8`) are tested with the recording backend, not by
  drawing.

## Acceptance

`ctest` is green, including the ported corpus and all typical-task programs, and
`НАЙТИВСЕ` reproduces the required examples exactly.
