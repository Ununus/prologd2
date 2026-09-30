# PrologD 2.0 — master plan

## 1. Mission

Build a modern, memory-safe, UTF-8-native re-implementation of the **PrologD**
logic programming language and its interpreter, as a C++23 console application
that runs on Linux and Windows.

The original PrologD (<https://github.com/Ununus/prologd>) is a Qt GUI plus
`src/prlib`, an interpreter written around 2000 in the pre-standard C++ of that
era. It:

* works in CP1251 and performs hand-written CP1251↔UTF-8 conversion at the I/O
  boundary;
* is memory-frugal by design (a byte heap, manual records, pointer arithmetic);
* recognises a variable as *any single letter*, which contradicts standard
  Prolog;
* defines all built-in predicates with Russian names written in upper case.

The new interpreter must preserve the *surface language* people know (Russian
built-ins, `<-` rules, `?` queries, `#expr#` arithmetic, `[H|T]` lists) while
adopting the **standard Prolog lexical convention** for variables and atoms, and
modern C++ engineering.

`НАЙТИВСЕ/3` (a `findall/3` analogue) was an explicit requirement of this
rewrite, and the one predicate that did not exist in the original: it must work
exactly as specified. The requirement examples are quoted in
`task_13_findall.md`.

## 2. Definition of done

1. `prologd` console executable, UTF-8 in/out, buildable on Linux and Windows.
2. Parser for the whole surface language with precise diagnostics and dedicated
   negative tests.
3. Unification, backtracking search, cut (`!`), meta-call (`ВЫП`), negation
   (`НЕ`), disjunction (`ИЛИ`).
4. Arbitrary-precision integers ("длинная арифметика") with all documented
   arithmetic predicates and `#expr#` expressions.
5. Every built-in predicate documented in the original user help implemented,
   including the program database predicates (`ДОБ`, `УДАЛЕНИЕ`, `ПРЕДЛ`,
   `ТЕРМ`, `СКОЛЬКО`), string predicates and the graphics predicates as no-op
   backend stubs.
6. `НАЙТИВСЕ/3` implemented natively, matching the required examples.
7. A clean, modular `ИМПОРТ` (module import) subsystem replacing the student
   preprocessor.
8. Test suite (Catch2) covering: parser errors, unification, backtracking/cut,
   each built-in, typical tasks (factorial, Fibonacci, sorting, N-queens,
   water jugs, knapsack, monkey & bananas), and the stated requirements.
9. Russian documentation in `doc/technical.typ`, `doc/help.typ`,
   `doc/prologd-diff.typ`, compiled with Typst when available.
10. The graphics/UI boundary is isolated behind an interface with a documented
    null implementation.  The GUI itself is a separate front-end
    (`src/gui`, PySide6 over the JSON session, milestone M11) that never links
    against `prlib`.

## 3. Chosen architecture (summary)

Full rationale in `decisions.md`.

```
src/
  CMakeLists.txt          top-level project, options, FetchContent
  prlib/                  interpreter library (target: prlib)
    include/prlib/*.hpp
    src/*.cpp
  cli/                    console front-end (target: prologd)
  tests/                  Catch2 test executables
  3rdparty/               FetchContent cache (gitignored)
```

Core design:

* **Terms are values, not heap offsets.** `Term` is a small tagged value with
  `shared_ptr<const Compound>` for compound subterms. Copying a term is cheap
  and safe; there is no manual heap.
* **Bindings and trail are separate from terms.** `Bindings` maps a variable id
  to a term; every mutation is trailed and undone on backtracking.
* **The engine is an explicit resolution machine**: an environment stack, a
  choice-point stack and a trail. `!` truncates the choice-point stack down to
  the current predicate invocation's barrier. This keeps cut semantics exactly
  standard and makes recursion depth independent of the C++ stack for the
  search loop.
* **Nested solves** (for `НЕ`, `ВЫП` inside negation, `НАЙТИВСЕ`, `СКОЛЬКО`)
  run a fresh engine that shares bindings and the trail, so results are copied
  out and all temporary bindings are undone.
* **Numbers**: a hand-written `BigInt` (base 10^9, sign-magnitude) plus IEEE
  `double`, with the documented PrologD promotion rules.
* **Lexer/parser**: hand-written UTF-8 aware lexer and recursive-descent parser.
  This gives byte-accurate diagnostics and avoids generator/tooling complexity;
  RE-flex was considered and rejected (see `decisions.md`).
* **Modules**: a `ModuleLoader` resolves `ИМПОРТ("file")` directives relative to
  the importing file, de-duplicates by canonical path, detects cycles and
  forbids escaping the configured root.

## 4. Syntax decisions (detail in `doc/prologd-diff.typ`)

Adopted from standard Prolog:

* Variables: `Name`, `_Name` (multi-letter, start with an upper-case letter);
  `_` is anonymous. **Any single letter is no longer a variable.**
* Atoms: lower-case-starting names, or quoted `'...'`.
* Clause terminator `.`; `;` is still accepted for backward compatibility (it is
  *not* disjunction).
* Rules `Head :- Body` and `Head <- Body`.
* Queries `?- Body` and `?Body`.

Retained from PrologD:

* Russian built-in names in upper case are **reserved atoms** (so they are not
  parsed as variables), e.g. `БОЛЬШЕ`, `НАЙТИВСЕ`.
* `# expression #` arithmetic expressions with infix `+ - * / mod div`.
* `<-` implication.
* String literals with double quotes, single-quoted atoms.

Removed from PrologD:

* Trailing-apostrophe variable names (`Имя'`); use standard upper-case names.
* Variable-as-any-single-letter.

## 5. Milestones

| # | Milestone | Tasks |
|---|-----------|-------|
| M0 | Repository, build, tooling | 01 |
| M1 | Core data model | 02, 03 |
| M2 | Front end (lexer, parser, diagnostics) | 04, 05 |
| M3 | Unification and search engine | 06, 07 |
| M4 | Arithmetic | 08 |
| M5 | Built-in predicates | 09–14 |
| M6 | Modules / ИМПОРТ | 15 |
| M7 | Graphics stubs and CLI | 16, 17 |
| M8 | Documentation | 18 |
| M9 | Examples port and typical-task tests | 19 |
| M10 | Windows portability and CI | 20 |
| M11 | GUI front-end (PySide6) | 21–33 |
| M12 | Built-in coverage and the lesson course | 34, 35 |
| M13 | Editor aids: run one query, look one up | 36, 37 |
| M14 | Engine limits, diagnostics and the standard surface | 38–43 |

## 6. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| `;` is a terminator, not disjunction; hides standard expectations | Document loudly in `prologd-diff.typ`; keep `ИЛИ/2` and separate clauses. |
| Upper-case Russian built-ins collide with the variable rule | The lexer resolves reserved built-in names to atoms before the variable rule; documented as an extension. |
| `BigInt` bugs | Dedicated property/fuzz test task (03) comparing against string arithmetic and `__int128` ranges. |
| Cut with nested meta-calls | Explicit `call` transparency: `ВЫП/1` pushes the goal into the *current* environment so cut scope is unchanged. |
| Old tests and lessons use single-letter variables | Porting task (19) provides a checklist and converts examples; the old `test.txt` semantics guide expected output. |
| Non-determinism of float printing | Reproduce the original `toString` trimming rules exactly; test on both platforms. |

## 7. Upstream compatibility target

When a feature is ambiguous, the tie-breaker order is:

1. the original user help, `prologd-help.txt` (documentation),
2. observed behaviour of the original `prlib/*.cpp` (implementation),
3. the original `prologd_test/test.txt` (regression corpus),
4. SWI-Prolog for *standard* syntax questions only.

All of the original material is published at <https://github.com/Ununus/prologd>.
