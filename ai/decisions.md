# Architecture decision records

Format: `ADR-NNN: title` — context, decision, consequences, status.

---

## ADR-001: Value terms instead of a pointer heap

**Context.** The original interpreter stores terms as records in a single byte
`std::vector<unsigned char>` and refers to them by `size_t` offsets. Terms are
mutable and variable bindings are stored in a parallel variable stack, giving
structure sharing. This is memory-efficient but unsafe and hard to maintain.

**Decision.** Represent a term as a value type:

```cpp
struct Term {
  enum class Kind { Var, Atom, Int, Float, String, Compound };
  Kind kind;
  // Var:   VarId
  // Atom:  interned symbol id
  // Int:   BigInt
  // Float: double
  // Str:   std::string
  // Cmp:   std::shared_ptr<const Compound>   // name + std::vector<Term>
};
```

Lists are represented as compounds with the reserved functor `./2` and the atom
`[]` (or as a dedicated `Nil` atom); the choice is finalised in task 02.

**Consequences.** Copying a term is cheap (shared subterms); unification is a
plain recursive function over the trail; no manual memory management; the
memory-saving goal of the original is explicitly abandoned (memory is not a
constraint today). Cyclic terms are not supported (the original did not create
them either).

**Status.** Accepted.

---

## ADR-002: Hand-written UTF-8 lexer and recursive-descent parser (no RE-flex)

**Context.** The user suggested RE-flex for parser generation. The language has
a tiny grammar (terms, `,`, `:-`/`<-`, `?`, `#expr#`, lists). Error messages
must be precise because the test suite checks individual syntax errors, and the
input is UTF-8 (multi-byte Cyrillic) while flex-family tools are byte oriented.

**Decision.** Write a hand-written lexer that decodes UTF-8 code points and
classifies them (upper/lower letter, digit, etc.), and a recursive-descent
parser with a token buffer. Keep the parser grammar documented in
`technical.typ`.

**Consequences.** No lexer-generator dependency; better diagnostics and full
control over the reserved Russian built-in names; slightly more code than a
generated scanner. RE-flex remains an option for future operator-table grammar
but is not used.

**Status.** Accepted.

---

## ADR-003: Hand-written `BigInt` instead of Boost.Multiprecision

**Context.** The original uses `boost::multiprecision::cpp_int`. Boost is not
installed. Fetching Boost.Multiprecision standalone was tested and **fails**:
it hard-requires the Boost.Config package (`#error "Boost.Config is considered
a requirement…"`). Fetching the full Boost superproject is hundreds of
megabytes.

**Decision.** Implement a small, well-tested `BigInt` in
`src/prlib/include/prlib/big_int.hpp`: sign + magnitude, base 10^9 limbs,
operations `+ - * / %`, comparisons, `to_string`/`from_string`,
`to_double`/`from_double`, `abs`, `pow`-free.

**Consequences.** No external heavy dependency; decimal conversion is fast
because limbs are base 10^9. Must be covered by dedicated tests (task 03),
including division and rounding/truncation semantics (`/` truncates toward
zero, `mod` follows PrologD's C++ `%` behaviour).

**Status.** Accepted.

---

## ADR-004: Explicit resolution machine with a persistent environment chain

**Context.** Cut, meta-call and negation need well-defined backtracking control
that is easy to reason about. A naive recursive solver plus exceptions makes
cut scope subtle. A first implementation used a `std::vector<Env>` stack and
restored it by index on backtracking; that was both incorrect (environments
above a choice point may already have been popped after a solution, losing
their goal lists) and O(depth) per choice point, which made deep recursion
quadratic.

**Decision.** Implement the engine as a loop over:

* a **persistent environment chain**: `EnvNode { parent, goals, index,
  cp_barrier }` held through `shared_ptr<const EnvNode>`. Pushing an
  environment or advancing its goal index allocates one small node that shares
  the parent chain, so a choice point captures the whole continuation in O(1)
  and restores it in O(1);
* a **choice-point stack** (`ChoicePoint`: captured `EnvRef`, next clause
  index, trail mark, cut barrier);
* a **trail** of variable bindings to undo.

`!` truncates the choice-point stack to the current environment's barrier.
`ВЫП(G)` pushes `G` into a child environment that *inherits* the caller's cut
barrier (transparent `call/1`). `НЕ(G)`, `НАЙТИВСЁ` and `СКОЛЬКО` run nested
engine instances over the same bindings/trail.

**Consequences.** Backtracking is O(1) per choice point; the 50 000-step
recursion test runs in milliseconds. Cut semantics are exactly standard and
directly testable. Memory per choice point is one `EnvRef` plus a few words.

**Status.** Accepted (supersedes the vector-of-environments variant).

---

## ADR-005: Reserved Russian built-in names are atoms

**Context.** Standard Prolog says an identifier starting with an upper-case
letter is a variable. PrologD built-ins are Russian names in upper case
(`БОЛЬШЕ`, `СЛОЖЕНИЕ`, `НАЙТИВСЁ`, …). Strict application of the standard would
turn every built-in into a variable.

**Decision.** The lexer keeps a compile-time set of reserved built-in names.
An identifier that exactly matches a reserved name becomes an atom regardless
of its first letter. All other upper-case-starting identifiers are variables.

**Consequences.** Built-ins keep their familiar spelling; users cannot use those
exact names as variables (acceptable). Documented as an extension in
`prologd-diff.typ` and `help.typ`.

**Status.** Accepted.

---

## ADR-006: `;` remains a clause terminator, not disjunction

**Context.** Standard Prolog uses `;` for disjunction and `.` as the clause
terminator. PrologD uses both `;` and `.` as terminators and has no disjunction
operator (disjunction is expressed with separate clauses or `ИЛИ/2`).

**Decision.** Keep `;` and `.` as terminators. Do not implement `;` disjunction.
Document the deviation.

**Consequences.** Existing PrologD programs keep working. Programs written for
standard Prolog that rely on `;` disjunction must be rewritten with `ИЛИ/2` or
multiple clauses. A future option could add a disjunction operator inside
`#`-free goal lists, but that is out of scope.

**Status.** Accepted.

---

## ADR-007: `#expr#` retained; no `is/2`

**Context.** PrologD evaluates arithmetic through `#…​#` terms and through the
relational predicates `СЛОЖЕНИЕ`, `УМНОЖЕНИЕ`, `БОЛЬШЕ`. Standard Prolog uses
`is/2` and infix comparison operators.

**Decision.** Keep `#expr#` (it is pervasive in lessons and tests) and keep the
relational predicates. Do not add `is/2` in the first iteration; it can be
added later as a convenience without breaking anything.

**Consequences.** Arithmetic surface stays PrologD-compatible. Documented in
`prologd-diff.typ` as a retained non-standard construct.

**Status.** Accepted.

---

## ADR-008: Graphics behind an interface, console build uses a null backend

**Context.** The original draws through Qt. The GUI is explicitly out of scope
for now, but the graphics built-ins must remain usable and testable.

**Decision.** Define `GraphicsBackend` (a small abstract interface:
`setPixel`, `getPixel`, `line`, `rectangle`, `ellipse`, `floodFill`,
`clearView`, plus the vertical/horizontal helpers). The CLI installs
`NullGraphicsBackend`, which records nothing and returns 0 from `getPixel`.
A future Qt front-end installs a real backend.

**Consequences.** Graphics predicates always succeed as documented; they can be
unit-tested with a recording mock. No Qt dependency in the core library.

**Status.** Accepted.

---

## ADR-009: Catch2 and CLI11 via CMake FetchContent into `src/3rdparty`

**Context.** The user requested `FetchContent` with a `3rdparty` folder added to
`.gitignore`.

**Decision.** `FetchContent` downloads Catch2 v3 and CLI11 into
`src/3rdparty` (`FETCHCONTENT_BASE_DIR`). The folder is gitignored. The build
must work offline once the folder is populated (`FETCHCONTENT_FULLY_DISCONNECTED`
option documented).

**Status.** Accepted.

---

## ADR-010: Module loader replaces the student preprocessor

**Context.** `src/preprocessor.{h,cpp}` in the old project textually splices
imported files with a regex, uses a global `std::stringstream`, writes a
temporary file, and has no cycle detection or path containment beyond a manual
`"../"` check.

**Decision.** Replace it with a `ModuleLoader` component:

* recognises an `ИМПОРТ("file")` directive during parsing;
* resolves paths relative to the importing file and the configured include
  directories;
* canonicalises and de-duplicates (import-once semantics);
* detects cycles and reports the chain;
* forbids paths escaping the configured root;
* reports errors with `file:line:column`.

**Status.** Accepted.

---

## ADR-011: Drop the historical numeric error codes

**Context.** The original interpreter numbered every error from 1 to 44 and
printed `<code> <text> (<code>)`. The user asked not to preserve the historical
codes. Keeping them would freeze an implementation detail into the public
interface and make new diagnostics awkward.

**Decision.** `ErrorCode` becomes a *semantic category* (lexical, syntax,
runtime) with no stable numbers. `DiagnosticSink::format` prints the usual
compiler shape `<file>:<line>:<column>: error: <message>`. Categories remain
available programmatically (for example to tell parse errors from runtime
errors), but they are not part of the user-facing contract. The mapping from
old names is documented in `ai/reference_notes.md`.

**Consequences.** Diagnostics are clearer and free to evolve; tests assert on
categories and message text rather than numbers. The original `err.h` is kept
only as historical reference (see <https://github.com/Ununus/prologd>).

**Status.** Accepted.

---

## ADR-012: Conventional command-line interface

**Context.** The old CLI used `-s=FILE` and a `-d/--directory` alias, and the
first port kept a pre-pass that rewrote `-x=value` and an `--encoding` option
that only accepted UTF-8. The user asked for a conventional CLI instead.

**Decision.** Use plain CLI11 conventions: `-s/--source FILE`, `-I/--include
DIR`, `-i/--input`, `-o/--output`, `-e/--error`, `-q/--questions`, `-t/--trace`,
`-h/--help`, `--version`, and source files as positional arguments. Remove the
`-s=FILE` rewriting, the `-d/--directory` alias and the `--encoding` option.
UTF-8 is the only encoding and is not configurable.

**Consequences.** `prologd file.pld`, `prologd -s file.pld` and
`prologd --source=file.pld` all work. The CTest suite includes CLI integration
tests for each form, for `-I`, `--help` and `--version`.

**Status.** Accepted.

---

## ADR-013: Visual Studio 2026 only, and the process runs with the UTF-8 code page

**Context.** The user's machine has Visual Studio 2026 (MSVC 19.51) and nothing
else, while `CMakePresets.json`, the README and CI named `Visual Studio 17 2022`
— configuration stopped at compiler detection.  Verifying the Windows build also
exposed two real defects on a machine whose ANSI code page is 1252 and whose OEM
code page is 437: `prologd -s "…\демо.pld"` could not open the file (arguments
reach `main` already converted through the ANSI code page, so Cyrillic becomes
`?`), and `ModuleLoader` threw `No mapping for the Unicode character exists in
the target multi-byte code page` because `path::string()`/`generic_string()`
produce the native narrow encoding.  Both were invisible in CI, whose Windows
runners have UTF-8 as the process code page.

**Decision.**

1. Visual Studio 2026 is the only Windows toolchain: the `windows-msvc` preset,
   the README and the CI `Configure` step all use `Visual Studio 18 2026`;
   support for VS 2022 is dropped rather than kept next to it.
2. `prologd` and `prlib_tests` embed `src/utf8.manifest`
   (`<activeCodePage>UTF-8</activeCodePage>`, Windows 10 1903+) through the
   `prologd_utf8` interface target, so every narrow API — `argv`, `path::string`,
   `fopen` — speaks UTF-8 in these processes.
3. `utf8_path.hpp` gains `toUtf8Path`/`toUtf8PathGeneric`, the mirrors of the
   existing `fromUtf8Path`; `prlib` must never use `path::string()` or
   `generic_string()` for text again.

**Consequences.** Behaviour on Windows now matches CI and Linux: Cyrillic paths
and command lines work, and the module loader can key on a path without throwing.
The manifest is ignored by older Windows versions, where the explicit conversions
in `utf8_path.hpp` still carry the load, so the helpers stay mandatory in code.
CI needs a runner image that actually provides VS 2026.

**Status.** Accepted.

---

## ADR-014: PySide6 GUI driven by a line-delimited JSON session

**Context.** task_20 planned a Qt 6 C++ front-end reusing the original
`MainWindow`, `Editor` and `Highlighter`.  The user chose **PySide6** instead:
Python is quicker to iterate on for UI work and needs no C++ binding layer.  The
constraint that the core must not grow GUI code also had to survive.

**Decision.** The front-end lives in `src/gui` as a plain Python package
(`prologd_gui`) and drives the built `prologd` executable with
`--protocol json`: requests are JSON objects on stdin, events are JSON objects on
stdout, one per line, versioned as protocol 1 and documented in
`src/gui/README.md`.  `prlib` gains only two seams, both front-end agnostic:

* `IoContext::setInputRequestHandler` — an interactive read asks the front-end
  instead of reading a stream, so a GUI can pop up a dialog and the protocol can
  emit `input_request`;
* `EngineOptions::externalStop` — the solver polls a front-end predicate next to
  its own flag, which is the async-signal-safe way to turn Ctrl+C (or a Stop
  button) into `ErrorCode::Interrupted`.

The CLI gains `--protocol`, SIGINT/SIGTERM handling (a `volatile sig_atomic_t`
consumed by `externalStop`) and `nlohmann/json` — taken as the single-header
release, pinned by SHA-256, and linked into the CLI target only, so `prlib` stays
dependency-free.

**Consequences.** A crashing or interrupted user program cannot take the GUI down
and a session restart is just a process restart.  A query that neither waits for
input nor terminates cannot be interrupted politely: the front-end terminates the
process (documented, and what the Stop button does).  `-i`/`-o`/`-e` are refused
together with `--protocol json`.  Python is now part of the repository: PEP 8,
type hints, no dependency besides PySide6, and `protocol.py` stays Qt-free so it
can be tested headlessly.

**Status.** Accepted.
