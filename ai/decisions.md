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
barrier (transparent `call/1`). `НЕ(G)`, `НАЙТИВСЕ` and `СКОЛЬКО` run nested
engine instances over the same bindings/trail.

**Consequences.** Backtracking is O(1) per choice point; the 50 000-step
recursion test runs in milliseconds. Cut semantics are exactly standard and
directly testable. Memory per choice point is one `EnvRef` plus a few words.

**Status.** Accepted (supersedes the vector-of-environments variant).

---

## ADR-005: Reserved Russian built-in names are atoms

**Context.** Standard Prolog says an identifier starting with an upper-case
letter is a variable. PrologD built-ins are Russian names in upper case
(`БОЛЬШЕ`, `СЛОЖЕНИЕ`, `НАЙТИВСЕ`, …). Strict application of the standard would
turn every built-in into a variable.

**Decision.** The lexer keeps a compile-time set of reserved built-in names.
An identifier that exactly matches a reserved name becomes an atom regardless
of its first letter. All other upper-case-starting identifiers are variables.

**Consequences.** Built-ins keep their familiar spelling; users cannot use those
exact names as variables (acceptable). Documented as an extension in
`prologd-diff.typ` and `help.typ`.

**Status.** Accepted.

---

## ADR-006: `;` is the disjunction; the terminator is `.`

**Context.** Standard Prolog uses `;` for disjunction and `.` as the clause
terminator.  PrologD used both `;` and `.` as terminators and had no disjunction
operator; disjunction was expressed with separate clauses or with `ИЛИ/2` — a
predicate that in fact takes the first solution of its first goal and so was not
a disjunction at all.  This ADR first decided to keep the old behaviour.

**Decision.** `;` between goals *is* the backtrackable disjunction (`,` binds
tighter), the sentence terminator is `.` alone, and the committed «take the
first» form is the built-in `ПЕРВОЕ/2` (renamed from `ИЛИ/2`).  A `;` written
where a sentence used to end is an error that says what changed.

**Consequences.** Standard-Prolog programs read naturally; a ported program that
used the old `;` terminator must replace it with `.` (one file in this
repository did), and a program calling `ИЛИ` must rename the call — the
interpreter answers both with a message.  Documented in `prologd-diff.typ`
§6 and §16–§18.

**Status.** Accepted; revised by task_41 (the `;` terminator) and task_44 (the
rename) — the original "keep `;` as a terminator" decision misled on both counts.

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

---

## ADR-015: Stepping blocks inside the engine, and positions come from the clause

**Context.** task_28 asked for step-by-step execution in the window.  The naive
shapes both fail: parsing the textual trace is fragile (the text is for humans and
changes with the version), and a hook that "pauses" has nowhere to pause — the
solver is a plain C++ loop over a persistent environment chain, with no coroutine
or continuation to suspend and resume.

**Decision.** Three things, all of them small:

1. `EngineOptions::stepHook` — a `std::function<StepDecision(const StepInfo&)>`
   called at the four points the textual trace already has (call, exit, redo,
   fail), with `StepInfo{action, goal, depth, location}`.  It has exactly **two**
   outcomes, `Continue` and `Stop`; there is no `Pause`, because a hook that wants
   the user to look at the point it was given simply *waits* — reading the next
   request from the front-end — and then answers.  That wait is the same re-entrant
   request loop `input_request` already uses, so the protocol needs no new
   threading model, and the solver needs no suspension.  Null by default, so a run
   that is not stepped through pays one branch per point.
2. The positions a front-end needs are carried by the *environment*: an `EnvNode`
   knows its depth and the `SourceLocation` of the clause it is solving, which is
   what a step point reports, and `Engine::raise` fills the same location in, so a
   **runtime** error — not only a parse error — names its line.  A nested query
   saves and restores the engine's current location.
3. `error` events carry `file`/`line`/`column` as fields, and a front-end is
   expected to *not* parse them out of the message.  A diagnostic sink that
   replaces the error-stream text is how the interpreter hands them over.

The trace of `ТРАССА` is untouched on the console path but goes through
`IoContext::setTraceSink` when a front-end asks, so the GUI can colour it apart
from the program's own output.

**Consequences.** Stepping costs one indirect call per traced point even when the
hook is installed and running on; a front-end that never installs it pays a null
check.  The hook runs on the solver's own thread and may block — it must not
throw, and it is not a signal handler.  The alternative the task named as a
deliberate fallback (grepping the trace text) is *not* used: the structured hook is
what the panel, the call stack and the highlighted line are built on.

**Status.** Accepted.

## ADR-016: What a built-in does when it cannot answer

**Context.** `task_34` walked every branch of every built-in and found six defects,
five of them where the code had to decide something the documentation never
settled: what a float function returns for a value it does not have, how an
integer and a real are compared, what happens to a term that contains itself, what
the optional second argument of a reading predicate means, and what a code point
beyond Unicode is.  Each one had a branch, and the branch was wrong — the class of
bug a test suite that only tries the happy path never sees.

**Decision.** The rules, written down now so the next predicate does not invent
its own:

1. **A value the function does not have is a failure, never a silent non-number.**
   `SQRT` of a negative, `ln` of a non-positive, `asin`/`acos` outside `[-1, 1]`
   and a forward value that is not finite all fail.  `nan` is a C++ accident:
   `BigInt::fromDouble(nan)` is 0, so before this rule `SQRT(-4, X)` answered
   `X=0` in integer mode and `X=nan` in float mode.  This is a behaviour change
   (documented in `help.typ` §5.5–5.6).
2. **An integer and a real are compared as numbers, exactly.**  Equal means the
   real is whole and its value equals the integer: `6` matches `6.0`, and
   `16777217` matches neither `16777216.0` (what narrowing the integer to `float`
   used to produce) nor `16777217.0`.  In other words the comparison happens in
   one precision, and rounding cannot make two different numbers equal — comparing
   the integer's *nearest double* was rejected for the same reason
   (`10^20 + 1` would match `10^20.0`).
3. **A cyclic term is a fact of the language, and the walkers defend themselves.**
   There is no occurs check (ADR/notes), so `РАВНО(X, f(X))` is legal and makes a
   term that contains itself.  Printing stops at the repeat and writes `...`
   (`f(...)`, `[1|...]`), the print depth is a stack-safety number (2000, not
   100000), and a *copy* — what `ДОБ` and `НАЙТИВСЕ` need — is refused with
   «Циклический терм нельзя скопировать» instead of recursing until the process
   dies.  The alternative (enabling the occurs check) was rejected: it changes
   unification for every program to protect one line at the prompt.
4. **A documented argument is read, or it is an error.**  The second argument of
   `ВВОДЦЕЛ`/`ВВОДВЕЩ`/`ВВОДСИМВ`/`ВВОДСТР` is the prompt the original typed at
   the console; it is written before the read, and a prompt that is not text is a
   type error.  Silently ignoring an argument was the defect.
5. **An argument that is not a number is a type error, in the graphics predicates
   too.**  Dereferencing an empty `std::optional` is not "lenient", it is
   undefined behaviour; every non-free coordinate and colour goes through one
   checking helper.  A real is truncated, as in every other integer argument.
6. **Text written out has to be valid UTF-8.**  `ВВКОД` accepts a Unicode scalar
   value only: negative, past `U+10FFFF` or a surrogate is an error, because the
   JSON protocol cannot carry the bytes that used to be produced.

**Consequences.** Five behaviour changes a program can notice (the float domains,
the number comparison, the cyclic-term diagnostic, the prompt, the code point
range), all of them recorded in `doc/help.typ` and pinned by tests; the truncation
of real arguments, the clamp in `УДАЛЕНИЕ` and `#1/2#` = 0 were *kept* because they
are the documented port, not defects.  The sweep also produced a harness rule: test
case *names* must be ASCII, because Catch2 discovery reads the test binary's
`--list-tests` output through the console code page and a Russian name reaches
`ctest` double encoded.

**Status.** Accepted.

## ADR-017: No clause indexing yet

**Context.** `Database::clausesFor` hands the solver one clause list per
predicate and the solver tries the clauses in order (`selectClause`).  A
first-argument index (SWI-style, built just in time) would skip the clauses whose
first argument cannot match a goal that arrives with a bound first argument.
task_42 measured what the absent index costs, with `tools/bench_engine.py` on the
Release build (this machine, 2026-09-30):

* 100 000 integer facts — query on the first clause 0.31 s, on the last 0.33 s: a
  full scan of ~100 000 failed head attempts costs ≈ 20 ms (repeated runs put it
  between 10 and 30 ms), i.e. ≈ 0.1–0.3 µs per attempt (each attempt creates an
  environment and unifies the head);
* 50 000 facts with a compound head (`ф(к(N))`), where each failed attempt also
  compares a structure: first 0.25 s, last 0.25 s — the scan hides inside the
  spread;
* the queens search (8 queens; 14 clauses, heavy bodies, head matching by
  structure): 0.29 s, and an index cannot prune it at all — every clause head
  matches shallowly and the work is inside the bodies.

**Decision.** Do not build the index yet.  Its saving is at most one scan per
*call*, and the predicates this interpreter runs — lessons, puzzles, typical
tasks — have a handful of clauses; the index would have to live inside the
copy-on-write snapshot (`ClauseList`), because a choice point keeps the list it
saw and a running enumeration must keep a consistent view, which is real
complexity for a microsecond.

**Consequences.** The clause list stays a plain `std::vector<Clause>` inside the
snapshot; the benchmark knows the workload that would justify an index.

**Status.** Accepted — measured and deferred, to be revisited when a real program
calls a predicate with thousands of clauses *repeatedly* with a bound first
argument, or when clause heads become expensive to unify (then the per-attempt
cost and the scan length both matter).

## ADR-018: The built-ins are the definitions; the engine loads no library

**Context.** `Engine::initialize()` used to parse and load a seven-clause library
(`НЕ`, `ИЛИ`, `РАВНО`, `МЕНЬШЕ`, `СЛОЖЕНИЕ`, `ПС`, `ДЛИНА`).  Every one of those
names is also in the dispatch table, and `Solver::resolveGoal` consults
`findBuiltin` first, so the clauses could never be selected — they were visible
only where the database is read directly: `?СКОЛЬКО(НЕ, А)` answered `А=2` (the
`НЕ(X) :- ВЫП(X), !, ЛОЖЬ.` and `НЕ(_).` pair) and `?СКОЛЬКО(ДЛИНА, В)` answered
`В=1`, while a call to `НЕ` never reached those clauses.  A reader asking «сколько
предложений у НЕ» got a number that described nothing callable.

**Decision.** Delete the library (task_43; the two `ИЛИ` clauses had already left
with the rename, task_44).  `Engine::initialize()` keeps its place and does
nothing but say why.

**Consequences.** `СКОЛЬКО`/`ПРЕДЛ`/`УДАЛЕНИЕ` report only what the program
defines; nothing observable changes for a call (the dispatch table answered those
names before and does now).  A future build without a dispatch table would want
the bootstrap back — it belongs in a file that says exactly that and must not be
loaded by default.

**Status.** Accepted.
