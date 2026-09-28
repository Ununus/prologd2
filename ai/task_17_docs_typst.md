# task_17 — Typst documentation (`doc/*.typ`)

**Status:** done
**Depends on:** tasks 02–16 (write incrementally)
**Milestone:** M8

## Goal

Produce the three Russian Typst documents required by the request.

## Deliverables

- [ ] `doc/help.typ` — user help, a modern analogue of
  the original `prologd-help.txt`:
  * syntax overview (program, clauses, queries, comments, directives);
  * data types (integers, floats, arithmetic expressions, atoms, strings,
    compounds, lists);
  * every built-in predicate with syntax, argument types, semantics and
    examples, grouped as in the original;
  * the `НАЙТИВСЁ/3` section with the required examples;
  * a short migration section pointing to `prologd-diff.typ`;
  * update it in the same commit/change as each predicate implementation
    (per `conventions.md`).
- [ ] `doc/technical.typ` — internal design, scientific style:
  * problem statement and language model;
  * term representation, symbol interning, variable identity;
  * substitution, trail, unification algorithm and complexity;
  * resolution machine: environments, choice points, cut, nested solves;
  * arithmetic: `BigInt`, promotion rules, error taxonomy;
  * module loader;
  * I/O abstraction and graphics boundary;
  * testing strategy and measurements (e.g. factorial 1333 timing);
  * limitations and future work.
- [ ] `doc/prologd-diff.typ` — every syntax/behaviour change from PrologD:
  * variables (single letter → standard upper-case multi-letter);
  * trailing-apostrophe variables removed;
  * atoms/constants starting with an upper-case letter must now be quoted
    (`'Россия'`);
  * reserved Russian built-in names as an extension;
  * `;` is a terminator, not disjunction;
  * `#expr#` retained (not `is/2`);
  * UTF-8 instead of CP1251, `ВВКОД`/`СТРСПИС` code-point policy;
  * string indexing by code points rather than bytes;
  * import directive and module semantics;
  * output/diagnostics format changes;
  * unchanged behaviour table.
  * Each item: original behaviour, new behaviour, migration recipe, example.
- [ ] `doc/README.md` (or a section) describing how to build the PDFs with
  `typst compile` and noting that Typst is optional for the C++ build.
- [ ] Add a `docs` CMake target (custom target) that runs `typst compile` when
  the `typst` binary is found; skip with a warning otherwise.

## Design notes

* No `typst` binary is assumed to be installed; CI must not fail if it is
  missing.
* Use Typst `@preview` packages sparingly; a plain document with headings,
  tables and code blocks is enough.
* Russian typography: use «ёлочки» for quotes in prose, keep code as-is.

## Tests / verification

- [ ] If `typst` is available: `typst compile doc/help.typ`, `technical.typ`,
      `prologd-diff.typ` succeed without errors.
- [ ] Link check: every implemented predicate appears in `help.typ`.
- [ ] Diff check: every entry of `ai/decisions.md` that changes the language
      appears in `prologd-diff.typ`.

## Acceptance

All three documents exist, compile (when Typst is present), are in Russian, and
cover the requested topics.
