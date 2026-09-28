# task_02 — Core data model: terms, atoms, lists

**Status:** done
**Depends on:** task_01
**Milestone:** M1

## Goal

Define the immutable term representation, symbol interning, the clause/program
model and term copying/printing helpers.

## Deliverables

- [ ] `include/prlib/term.hpp`, `src/term.cpp`
  * `using VarId = std::uint32_t;`
  * `Term` value type per ADR-001 with kinds `Var, Atom, Int, Float, String,
    List, Compound`.
  * Constructors/helpers: `makeVar`, `makeAtom`, `makeInt`, `makeFloat`,
    `makeString`, `makeCompound(name, args)`, `makeList(head, tail)`,
    `makeNil()`.
  * Predicates: `isVar`, `isAtom`, `isNumber`, `isCompound`, `isList`.
  * List helpers: `listToVector`, `vectorToList`, `listLength`.
- [ ] `include/prlib/symbol_table.hpp` — interned atoms (`std::string_view`
      keyed `unordered_map`, stable ids) and reserved built-in names.
- [ ] `include/prlib/program.hpp`, `src/program.cpp`
  * `Clause { Term head; std::vector<Term> body; SourceLocation loc; }`
  * `Database` — functor/arity keyed clause lists with a stable clause id;
    assert/retract by position; lookup by name for `СКОЛЬКО`/`ПРЕДЛ`.
- [ ] `include/prlib/term_print.hpp`, `src/term_print.cpp`
  * `formatTerm(const Term&, const Bindings&)` implementing PrologD output:
    lists `[a,b|T]`, strings unquoted, atoms as-is, unbound vars `_N`,
    integers, floats with trailing-zero trimming.
  * `writeTerm` with a variable-write counter so each unbound variable gets a
    distinct `_N` within one printed term.
- [ ] `include/prlib/source_location.hpp` — file, line, column.
- [ ] `Bindings` interface (declared here, implemented in task_06):
      `deref`, `bind`, `trailMark`, `unwind`.

## Design notes

* Choose one list encoding and document it. Recommended: dedicated
  `Kind::List` with `std::shared_ptr<const ListCell>` (`head`, `tail`), plus a
  canonical `Kind::Atom` for `[]`. This keeps `[H|T]` and `[]` distinct from
  compound terms and makes printing/serialisation trivial.
* Terms are immutable; `std::shared_ptr<const …>` subterms make copies cheap.
* Variable identity is a global monotonic `VarId`; the *name* of a variable is
  stored in the `Database`/`VariableTable` for printing, not inside `Term`.
* Printing must be deterministic across platforms (no `std::to_chars` float
  dependence for the trimmed format).

## Tests

- [ ] `test_term.cpp`: construction, equality of ground terms, list
      conversions, deep copy, `formatTerm` for every kind.
- [ ] `test_symbol_table.cpp`: interning returns identical ids, reserved names
      recognised.
- [ ] `test_program.cpp`: add/lookup/retract clauses, clause numbering.

## Acceptance

`formatTerm` matches the original output for the samples in
`reference_notes.md` §3, verified by unit tests.
