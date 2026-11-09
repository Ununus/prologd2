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
first» form is the built-in `ПЕРВОЕ/2` (renamed from `ИЛИ/2`; variadic from one
goal since task_51).  A `;` written
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

* 100 000 integer facts — query on the first clause 0.31 s, on the last 0.33 s.
  *Corrected 2026-10-03:* those two runs both scan the whole list, so their
  difference is not the scan — a ground query under `ТИХО` keeps asking for
  solutions after its first one (`Engine::runQuery`: `quiet_` returns
  `!has_variables`), and only a cut or a variable in the query stops it.  Isolated
  with a cut right after the call (and re-measured on the same machine and preset):
  loading the same 100 000 facts costs 0.25 s, and the scan costs ≈ 50 ms — 0.3 ms
  for 1 000 clauses, 3.7 ms for 10 000, 54 ms for 100 000, i.e. ≈ 0.5 µs per failed
  head attempt (each attempt creates an environment and unifies the head);
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

## ADR-019: A predicate fed by two unrelated files is a warning

**Context.** `ИМПОРТ` merges everything into one global database.  Two files that
each define `член/2` produce one predicate with the clauses of both, in load
order — silently.  That is what made the old lessons 8 and 9 unrunnable when a
teacher loaded both.  Two neighbouring cases must *not* be reported: the diamond
(`examples/diamond/`: one module reached by several import paths, loaded once)
and the extension pattern (a file adding clauses to a predicate of a module it
imports).

**Decision.** After the outermost file and its imports are loaded, every
predicate whose clauses come from more than one file is examined.  If two of
those files have no import path between them — direct or transitive, in either
direction — one warning names the predicate, both files and their clause counts
(once per predicate).  Files related by imports are skipped, which is exactly
what keeps the extension pattern silent.  A clause made at run time (`ДОБ`) and a
virtual source (`<test>`, `<stdin>`) is not a file for this purpose.  The check
runs only when the outermost load was a file; a session at the prompt is not
asked about itself.

**Consequences.** The clash and the extension are told apart by the import graph
the loader already keeps (it detects cycles with it), so no extra bookkeeping.
A program that intends one name across two unrelated files gets a warning it can
ignore — warnings never change exit codes and `--no-warnings` drops it.

**Status.** Accepted.

---

## ADR-020: A limit is a run option, and the core names no front-end

**Context.** task_46 added the run limits (steps, recursion depth, `НАЙТИВСЕ`
solutions; the wall-clock deadline is the front-end's, see below).  The first cut
had the engine's messages quote both the flag and the dialog row that raise the
limit — «Превышена глубина рекурсии: 10000 (--max-depth; «Предел глубины» в
настройках окна)» — and the engine's own defaults were 10 000 (depth) and
1 000 000 (solutions).  prlib is used by the command line, by the protocol
session, by the tests and by the lessons runner; a message that names a settings
row of the PySide6 window is a dependency pointing the wrong way, and it goes
stale the moment a front-end renames a row or disappears.

**Decision.** The core knows no front-end.

* `0` means «no limit» for all three, and a fresh engine has **no limits**: a
  limit is something the *caller* asks for — `--max-steps`/`--max-depth`/
  `--max-findall` on the command line, the `limits` object of a protocol `load`,
  a row of a settings dialog.  `Limits` is the one record that carries that
  request into `EngineOptions`, so the three callers cannot disagree about what a
  zero means.
* A limit that fires prints the limit and its value and stops there:
  «Превышен предел шагов выполнения: 5000», «Превышена глубина рекурсии: 200»,
  «Превышен предел решений НАЙТИВСЕ: 50».  No flag, no row, no advice.
  *Поправка 2026-10-22 (task_91).*  «Its own name» is the *predicate's* name as
  well: `collectAll` takes it from the caller, so a `ВСЕРЕШ` that hits the same
  setting is told «Превышен предел решений ВСЕРЕШ: 50» and is not sent looking
  for a `НАЙТИВСЕ` it never called.  The number still comes from one place
  (`maxFindAllSolutions`), which is about the setting, not about the name.
* «Where do I raise it» is answered by whoever put the number there, in their own
  vocabulary: the CLI's `--help`, and in the window a line the run prints before
  it starts, in the words of the dialog's rows («пределы: «Предел шагов» 5000 —
  строки в «Выполнении» настроек»).
* The **wall-clock deadline is not in the engine at all**: `steady_clock::now()`
  in the solver's hot loop is a cost per solution, and the front-end owns the
  clock anyway (a QTimer plus the existing `interrupt` request, the command
  line's Ctrl+C).  Consequence, documented rather than papered over: a
  *computing* run stops on the deadline, a run waiting **outside** the solver
  (`ВВОД` nobody answers) is ended by «Остановить» and not by the deadline.
* The one default that stands is `kDefaultMaxNestedDepth` — the guard on
  `НАЙТИВСЕ`/`ВЫП` nesting inside themselves.  It is not a limit a user sets and
  has no flag or row, because it guards the C++ stack of nested solvers
  (task_38), not a promise about the program.

**Consequences.** Running `prologd` with no flags runs a program to the end: a
runaway recursion is stopped by nothing and grows until memory runs out (the
frame chain is released iteratively, so it is memory and not the C++ stack).  The
safety therefore lives where the audience does — the window ships 0 / 1 000 000 /
1 000 000 / 0, numbers no lesson program can notice and a runaway cannot outlive
— while a script that wants a guard asks for one.  The tests pin the wording in
both directions: a message contains the limit and its value, and does *not*
contain a flag or the word «настройках».

**Status.** Accepted.

---

## ADR-021: The window stays Russian

**Context.** task_29's settings list carried «язык интерфейса RU/EN» (the
reference front-end was Russian only), which would mean a translation layer and a
second set of every string in the window: menu, dialog, hints, diagnostics
wrappers, the reference dock.

**Decision.** Not planned — dropped 2026-10-01.  The window is Russian only; no
`QTranslator`, no string tables, no language setting.  This is about the
*interface*: the language keeps its English spellings of the built-in predicates
(task_39) and `doc/help.typ` keeps everything a reader of ordinary Prolog
expects, because that is the *language*, not the shell.

**Consequences.** Every label, hint and message written in the window stays a
plain Russian string, which is why `settings.py` can hold the labels of the dialog
verbatim.  A future translation would start from scratch; nothing is prepared for
it, and nothing pretends to be.

**Status.** Accepted (task cancelled by the user's decision).

---

## ADR-022: The pixels live in the interpreter, the primitives travel

**Context.** The graphics predicates draw through `GraphicsBackend`, which lives
*inside* the interpreter process, while the window is on the other side of a pipe
(`--protocol json`).  Two facts decide the design: a drawing call is one-way, and
`ТОЧКА(X, Y, Цвет)` with a free colour and `ЗАКРАСКА` are **reads** the engine
performs from inside a built-in.  A synchronous question to the front-end in the
middle of a built-in is something the protocol does nowhere, and `ЗАКРАСКА` reads
cells the same query has just written.

**Decision.**

* The screen is a `BitmapGraphicsBackend` inside the session: a `1024 × 768` buffer
  that answers `getPixel` locally and performs `floodFill` and `clearView` itself.
  The console build keeps `NullGraphicsBackend`; nothing there changed.
* Every primitive is **reported** as it is drawn (`GraphicsEvent` → a `graphics`
  event on the wire): a few bytes per `ТОЧКА` instead of the megabytes a bitmap
  would cost, and the window redraws it in O(cells of that primitive).
* A cell holds **the colour value the program wrote**, not an ARGB word.  A read
  has to give back exactly what a write put there, and turning a value into a
  visible colour is the front-end's business: `0`…`15` are the EGA palette the
  original lessons draw with, anything above is read as `0xRRGGBB` (`color_for`,
  one function, in `graphics.py`).
* A window that was **not open** while the program drew asks for the whole screen:
  `{"cmd":"graphics","snapshot":true}` → a `bitmap` event, base64 of four-byte
  little-endian values (the program's numbers, so a replayed picture and a
  snapshot are comparable cell by cell).  The snapshot is not the normal path.
* The **rasterising rules** — Bresenham lines, an outlined rectangle, an ellipse
  from its parametric equation with `floor(v + 0.5)`, a four-connected fill, and
  clipping at the edges (with coordinates clamped at ±1 000 000 first, because
  `10**18` overflows C++ and does not overflow Python) — are written twice: in
  `prlib/graphics.cpp` and in `prologd_gui/graphics.py`.  `test_graphics.py` pins
  them to each other: it draws a program, takes the engine's bitmap and replays the
  same events into a canvas, then compares the two pictures cell by cell.
* An `ellipse` is a **centre and two radii**, not a bounding box:
  `ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes its four numbers straight through, and the
  interface's parameter names (`x1, y1, x2, y2`, task_15) said otherwise until the
  first look at a real drawing.  The wire spells the fields `x`, `y`, `rx`, `ry`.

**Consequences.** A front-end can be written in anything, and the protocol stays
line-delimited JSON with no back-channel.  The engine owns the truth, so a
`getPixel` after a fill is the same answer whoever asks.  The price is a second
implementation of the drawing rules, which is why the cross-check exists and why
it compares pictures rather than calls.

**Status.** Accepted.

## ADR-023: An answer is a piece of the input stream

**Context.** Every source of input is supposed to behave the same — a file (`-i`,
`ЧТЕНИЕ_ИЗ`), stdin, and the answer a front-end gives
through `setInputRequestHandler`.  They did not.  The answer was put into the
interactive buffer whole, so an answer holding a `\n` was *one* line however many
separators it had: `ВВОДСТР` returned the separators as text, a `ВВОДСИМВ` followed
by `ВВОДСТР` left a remainder starting with `\n`, and `ВВКОД` read code 10 between
the lines.  The window's answer was the one source where a program written against
a file behaved differently, which is what made the multi-line console a trap.

**Decision.**

* An answer is a **piece of the input stream**.  `IoContext` keeps what is left of
  it and hands out one line at a time: up to the first `\n` (a `\r` before it is
  dropped, as in a file), or all that is left when there is no separator, since the
  end of a piece ends its last line.  A new piece is asked for only when the one in
  hand is used up — so `a\n` is one line and not one plus an empty one.
* An empty answer stays one empty line, which is what a one-line front-end and a
  file holding an empty line already agreed on.
* The **front-end's queue keeps its split**: the `>` echo and the «осталось строк»
  counter need one line per answer.  That split is bookkeeping, not reading — each
  queued line is a one-line piece anyway.
* A **byte order mark is a marker at the start of a stream**, not data: the first
  line of the base stream, the first line of each file opened by `ЧТЕНИЕ_ИЗ`, and
  the start of each answer are stripped with the same helper the lexer uses on a
  source (`Notepad` writes the mark into a new data file by default).  Anywhere
  else it is text.  (The `$` lines that also needed nothing were removed in part 81.)
* The protocol does not change: `input.text` was always free to contain `\n`, and
  the interpreter is now what splits it.

**Consequences.** A program written against a file behaves the same in the window,
so a lesson can be checked by running it (`-i file`) before running it by hand.
The multi-line console keeps its reason to exist and gains a precise meaning —
several lines of *input* — and `Ctrl+Enter` stays the key that sends it, with the
placeholder saying «Строки».  The price is that a front-end which used to send one
line per answer and lean on `ВВОДСТР` returning everything must now send the
separators itself — that is the only behaviour that was ever portable.

**Status.** Accepted.

## ADR-024: The shipped Windows build is a folder frozen by PyInstaller

**Context.** The window is a PySide6 application and the interpreter is a C++
executable; a teacher who wants to hand both to a student should not have to install
Python, Qt or a runtime.  The alternatives were measured before choosing
(`ai/task_61_portable_windows_build.md` §3): Nuitka compiles and starts faster but
needs a compiler and a much longer build; cx_Freeze has fewer Qt hooks;
`pyside6-deploy` is Nuitka underneath.  All four produce a folder, so the decision is
reversible.

**Decision.**

* **PyInstaller, `--onedir`** — a folder, not `--onefile`: `--onefile` unpacks ~95 MiB
  into `%TEMP%` on every start, `--onedir` starts directly and stays inspectable.
  The freeze is `--windowed` (no console flash), with `prologd-gui.exe` named apart
  from `prologd.exe`.
* **One folder is the program.**  `prologd-gui.exe`, its `_internal`, `prologd.exe`,
  the Visual C++ DLLs, `doc` (five PDFs, their `.typ`, `builtins.json`), `examples`
  (lessons, tasks, `lib`) and a memo.  The window finds the interpreter *beside
  itself*, keeps `gui.ini` there and opens the documents from its own `doc` — that is
  `prologd_gui.paths`, and it is what makes copying the folder enough.
* **The runtime rides along**: `vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll`
  in the root, taken from Visual Studio's redistributable folder, because the C++
  executable looks next to itself and a machine without Visual Studio has no local
  copy (the UCRT itself is part of Windows 10).
* **Qt modules the window never loads are left out** — QML/Quick, `Qt6Pdf`,
  `Qt6VirtualKeyboard`, `Qt6Network` and their plugins, 19.2 MiB of 116.3.  The cut is
  checked by `tools/check_dependencies.py` (a still-needed file shows up as a SUSPECT)
  and by starting the frozen window in the `offscreen` platform.
* **Nothing is supplied behind the reader's back.**  An earlier decision to seed
  `examples/lib` into the `ИМПОРТ` search list was reversed on 2026-10-03: lesson 11
  asks the student to add the folder by hand, so the settings row is the whole truth
  and no path recorded at first start can go stale when the folder moves.
* **Windows 10 (1903) or newer, 64-bit** is the floor (ADR-013 for the UTF-8 manifest
  element, Qt 6 and Python 3.14 for the rest); verified by the user on Windows 10 22H2
  (19045.6456) and on a clean Windows 11 in Windows Sandbox (24H2 26100.9457).
* **`tools/build_portable.ps1`** is the one way to build it: Release → `ctest` →
  `docs` → freeze → lay out → checks → zip, with `-SkipTests`/`-SkipFreeze`/`-NoTrim`
  for a shorter round.

**Consequences.** A release is one folder (`dist\prologd-2.0.0-win64`, 282 files,
95.5 MiB, zip 37.7 MiB) with no installer, which is what the lessons and the memo
describe.  An installer, if it ever comes, is a *second* front end to the same folder
and has to answer what it does with `gui.ini` beside the exe.  The cost of the choice
is the size and a build that needs a Windows machine with the toolchain: no
cross-compilation, and the zip is built by hand — by the script — not by CI.

**Status.** Accepted.

## ADR-025: Three built-ins instead of `bagof` and `setof`

**Context.** The user asked whether `bagof/3` and `setof/3` could be added, and what
else was worth adding.  The collecting half of `findall` already existed
(`Engine::collectAll`: a nested solver, a copied template per solution, the bindings
undone afterwards), so the question was which ISO conveniences fit this dialect.

`bagof`/`setof` were refused, and the reasons are structural rather than stylistic:

* `BuiltinResult` is `Continue`/`Fail`/`Handled` — a built-in gives one verdict and
  the machine moves on, so it cannot leave a choice point of its own.  `bagof` with
  its witness grouping *must* yield one list per group on backtracking: it would
  need a new kind of frame in the machine, not a new entry in a table.
* `setof` sorts by the *standard order of terms*, and this dialect deliberately has
  no such order: `БОЛЬШЕ`/`МЕНЬШЕ` compare two numbers or two text constants and
  raise a type error for anything else, while the ISO `@<`-family is rejected with a
  hint (task_52).  A term order over variables, numbers, atoms, compounds *and* this
  dialect's separate string type is a language design question, not a predicate.
* The grouping needs `^` (`bagof(X, Y^p(X, Y), L)`) — one more ISO operator this
  dialect says no to.

**Decision.** Three predicates, covering the deterministic part of what people reach
for `setof`/`forall`/`ground` to do:

* `СОРТИРОВКА(Список, Результат)` (`sort`) — ascending, repeats dropped, the second
  argument unified with the result.  The order is the dialect's own, shared with
  `БОЛЬШЕ`/`МЕНЬШЕ` through `detail::compareOrder`: numbers by value, text by code
  point, anything else a type error.  The whole list is checked *before* the sort, so
  a mixed list is refused once instead of depending on which pairs the algorithm
  happens to compare.  `1` and `1.0` count as one value, because the dialect's own
  comparison calls them equal (`РАВНО(1, 1.0)` holds).
* `ДЛЯВСЕХ(Условие, Следствие)` (`forall`) — ISO `forall/2` exactly: true when no
  solution of the condition fails the action, implemented as
  `Engine::hasCounterexample`, a nested solve that stops at the first counterexample.
  It is sugar over `НЕ((Усл, НЕ(След)))`, and it is worth having because the
  affirmative form is what a check reads like.
* `ПОЛНЫЙ(Терм)` (`ground`) — no free variable anywhere in the term.  Unlike the
  other two it cannot be written reliably in the language itself: the walk needs the
  cycle guard the printer already uses, or `РАВНО(X, f(X))` sends the Prolog version
  past the depth limit (measured); and such a term has no free variable, so the
  honest answer is «полный».

**Consequences.** The names are honest — `sort/2`, `forall/2` and `ground/1` do what
ISO says — so the alias table (help.typ §17) stays a table of synonyms rather than a
list of near-misses.  `bagof`/`setof` stay absent and `help.typ` says so in its
comparison table: a reader coming from SWI looks for them, finds nothing, and gets
`СОРТИРОВКА` instead.  No lesson broke: the course sorts with `вставсорт/2` and
`быстрсорт/2`, which are not reserved names, so the hand-written exercises stay
exercises (checked before the names were added).  Each new predicate costs the usual
five places — the dispatch table with its English alias, the reserved-name set,
`doc/builtins.json`, a section of `help.typ` and a line in `prologd-diff.typ` — plus
tests and the lesson material.

**Status.** Accepted.

**Поправка 2026-10-20 (задача 90, задача 91).**  Вторая причина из списка выше
больше не действует: стандартный порядок термов в диалекте есть — `@<`, `@=<`,
`@>`, `@>=` и `compare/3`, и `СОРТИРОВКА` сортирует им любые термы, включая
составные.  Первая причина уточнена: встроенный предикат по-прежнему не может
оставить точку выбора, но `bagof` раскладывается на детерминированный сбор групп
в движке и библиотечную рекурсию по списку групп — тогда новое звено машины не
нужно (оно остаётся отдельной возможностью, нужной `sub_string/5` для перебора
вхождений).  Третья причина (`^`) остаётся и требует своей работы.  Поэтому
решение «`bagof`/`setof` не заводить» переоткрыто задачей 91; из отказа этого ADR
в силе остаются только `catch`/`throw`, модули, словари и рациональные.

**Поправка 2026-10-21 (часть 130).**  Пока `bagof/3` и `setof/3` не написаны,
вызов любого из них — это не молчание: у них есть подсказка в той же таблице, что
у `is/2` и `catch/3` («все решения собирает `НАЙТИВСЕ/3`…»), а `help.typ` §12
объясняет, чем их заменить сегодня.


## ADR-026: The standard library is a folder beside the interpreter, searched last

**Context.** After part 84 the shipped library lived in `stdlib/`, and every program
that used it had to name the folder: `prologd -I stdlib -s …` on the command line, the
same row in the window's settings dialog.  ADR-018 says the engine loads no library of
its own — that stays true — but a *search directory* is not a library.  The first
PrologD shipped a file `lists` among the examples, and a reader had to copy it or point
at it; a program that arrives with the interpreter should not.

**Decision.** `prologd.exe` searches a `stdlib` folder beside itself, last: after the
importing file's own folder (ADR-010) and after every `-I` directory.  The folder is
located by asking the loader about the running module (`GetModuleFileNameW` on Windows,
the `/proc/self/exe` link on Linux); the rule itself —
`standardLibraryDirectory(directory)` — is a pure function of the directory, so a test
covers it in a temporary folder instead of copying an interpreter anywhere.
`-I stdlib` remains the way to reach the library from a build tree, where nothing sits
beside the executable.

**Consequences.** A program shipped with the interpreter needs no flag and no settings
row for the library — `:- ИМПОРТ("lists.pld").` is the whole ceremony — and the portable
package proves it: `build_portable.ps1` runs `stdlib_demo.pld` **without** `-I`.  The
window's «Дополнительные каталоги ИМПОРТ» list keeps meaning what it meant, what the
*reader* added (part 74): the folder the interpreter searches by itself is not a row in
it, and an import that fails still reports every directory it tried, `stdlib` included.
A user file that shares a name with a library file wins, because the folder is searched
last.  The reference is a sixth document, `doc/library.typ`, and `test_stdlib.cpp`
fails when a predicate defined in `stdlib/*.pld` has no line in it.

**Status.** Accepted.

## ADR-027: The ISO arithmetic signs are accepted, and `#…#` stays

**Context.** `help.typ` §3.3 said, as a decision and not an accident, that `is`, `=:=`
and `=\=` were absent because `#…#` already evaluates everywhere a number is needed and
`РАВНО` is reversible (`РАВНО(5, #2+3#)` holds).  The cost of that decision showed up
when programs from books were read: `X is N - 1` got a hint instead of an answer, and a
factorial had to be rewritten before it would run.  Stage 3 of task_82 (task_92) had to
either keep the refusal or take the signs, and the second is what the owner asked for
(«ISO до конца»).

**Decision.** The three arithmetic signs are sugar of the same kind as `>`/`=<`: the
parser recognises them before it parses the goal and builds `РАВНО(X, #E#)` (`is`),
`РАВНО(#E1#, #E2#)` (`=:=`) and the same under `НЕ` (`=\=`, `\=`).  Their operands are
ordinary arithmetic expressions with **no** `#…#`, which is the one place the dialect
takes bare arithmetic in goal position.  The word `is` is *not* reserved: outside that
arithmetic position it is a name like any other, so `is(X, Y)` and `ф(is)` keep working
— that is why the decision is made by looking ahead (`arithmeticComparisonAhead`) rather
than by lexing `is` as a sign.  `#…#` stays, exactly as before: it evaluates inside any
term (`ВЫВОД(#2 + 3#)`) and remains the only way to write an expression as an argument.

**Consequences.** Book programs now run as written, and the hints «`is` — не оператор»
and «`\=` — не оператор» are gone; the remaining advice table is `==`, `\==` and `<=`,
which this dialect still lacks (`\=` is not `\==`: the first asks about unification, the
second about identity).  A free variable in an operand is the same runtime error as in
`#…#`, so the two spellings cannot disagree.  `/* … */` came with the same stage: it is
the standard's comment, non-nesting, an unclosed one is a lexical error — and the
formatter returns any text containing `/*` untouched, because the layout rules were
written for `%` and a multi-line comment inside a goal would be moved into another
clause.  Losing a comment is worse than leaving the spacing alone.

**Status.** Accepted.

## ADR-028: Exceptions are refused, and the refusal is spoken aloud

**Context.** Stage 4 of task_82 asked for the refusals to be settled — `catch`/`throw`,
`:- module`, dicts, rationals — and part of it was already in the language as behaviour
without a stated reason.  A program from a book that writes
`catch(Цель, Ошибка, Восстановление)` used to get a bare «не найдено: catch/3»: true, but
it reads as a typo, and a reader concludes the name is misspelled rather than missing.
The dialect has no exceptions of any kind: a runtime error (division by zero, a wrong
argument type, a free variable where a number is needed) is a `PrologRuntimeError` that
the engine throws and the CLI prints before stopping the run.

**Decision.** No exceptions.  `throw/1` and `catch/3` are not added, and the refusal is
carried by the same mechanism that already answers foreign spellings (`is`, task_55):
the names stay **unreserved** — a program may define its own `catch/3` and `throw/1`, and
then the ordinary call rules apply — while a call to one produces the usual unknown-name
warning *plus* a sentence saying there is nothing to reach for:

```
не найдено: catch/3; исключений в Пролог-Д нет: ошибка останавливает программу
не найдено: throw/1; исключений в Пролог-Д нет: «не получилось» — это ЛОЖЬ,
              а объяснение печатает ВЫВОД
```

The hint table (`kForeignSpellings`, `checks.cpp`) is the whole implementation: no
machine change, no reserved name, no new dispatch entry.  `is/2`'s hint was rewritten at
the same time — since task_92 it says «`is` — знак, а не предикат: пишут `X is 2 + 3`».

**Consequences.** A reader who tries ISO exception handling is told what to do instead:
failure as a signal (`(Условие -> Тогда ; Иначе)`, `НЕ`), checks *before* the risky
operation (`ПОЛНЫЙ`, `ЦЕЛ`, `ЧИСЛО`), `ВЫВОД` for the explanation, `ДЛЯВСЕХ` for «for all
X, if p(X) then q(X)».  A program that catches errors has to be rewritten; one that does
not is unaffected.  The refusal is documented where a reader looks for it — `help.typ`
§4.9 and the «Исключений нет» section of `prologd-diff.typ`, whose summary table gained an
«Исключения» row.

**Поправка 2026-10-21 (часть 131).**  Этап 4 закрыт: к подсказкам `catch`/`throw`
добавлены `:- module(…)` (ошибка разбора до чтения списка экспорта — там
`предикат/арность` требует `/` как знака терма, и человек получал «непарные
скобки»), `_{…}` (лексер), `1 rdiv 3` (вместо «предложение должно заканчиваться
точкой») и вызовы `module/1`, `rational/1` (таблица чужих имён).  Записи — в
`help.typ` §8 и в разделе «Импорт модулей» файла `prologd-diff.typ`.

**Status.** Accepted.

## ADR-029: The state control names an engine *line*, not a release

**Superseded by ADR-054** (part 213): the naming modes are gone, and the state
control with them.

**Context.**  Task_79 ended the toolbar with two state controls: `n.png` («имена») with a
menu of the two dialects, and `u.png`/`d.png` switching the engine.  Both had to be
deciphered, and the first reader of a package took `Д` for «Пролог-Д 2.0» — the name of
the whole product — rather than for the original engine.  Exact release numbers made it
worse rather than better: `2.0` is the *shell's* version in the About box while the
interpreter is at 2.4.x, and the pinned original repository declares
`project("prologd" VERSION 1.27)` — a value that once meant January 2026 (year.month) and
is read now as «version 1, number 27».

**Decision.**  One control, three states, named by the **line** of the engine and never by
a release: `2.x ISO`, `2.x PLD`, `1.x` (`actions.STATES`, marker `actions.STATE`).  `x` is
deliberate: it is the notation the manual's own comparison table already uses («Пролог-Д
(1.x)», «(2.x)», «(2.x ISO)», `doc/help.typ`), and nothing has to be edited when the
interpreter's minor number moves.  The exact version lives in exactly one place — «О
программе», filled from the live `ready`; the pinned original cannot report its own at
all (it has no `--version`).

**Consequences.**  The three pictures are the words themselves (`engine-iso`,
`engine-pld`, `engine-1.x`), so the state is read off the toolbar without a click, and a
missing file falls back to the text (`test_icons` keeps the file from going missing in the
first place).  The control is one switch over two questions, so its rows differ in price
and the code says so: `2.x ISO` ↔ `2.x PLD` writes `execution/variable_mode` and leaves a
live session alone, while `1.x` — and either `2.x` row while the original runs — goes
through `choose_engine`, which stops the session first.  `1.x` does not rewrite the stored
dialect, so a visit and a return keep the choice the user made.  A build whose only engine
has no `NAMING` keeps the control hidden (parts 143, 148); a row that would start an engine
this copy does not carry is greyed out with the reason, not hidden.

**Status.** Accepted 2026-10-22 (task_93).

## ADR-030: The order sign on `СОРТИРОВКА/3`, and why `@=<` keeps repeats

**Context.**  `СОРТИРОВКА/2` is ISO's `sort/2`: ascending, repeats dropped, and nothing
else — descending had no spelling at all, and «keep the repeats» was `msort/2` from the
standard library, ascending only.  SWI's `sort/4` covers every combination with
`(Key, Order, List, Sorted)`, but its `Key` — the number of an argument of a compound —
is a concept this dialect does not otherwise use: there are no dicts here, and compounds
are taught late.

**Decision.**  A middle arity: `СОРТИРОВКА(Порядок, Список, Результат)` with the four
signs of the standard order.  `@<` and `@>` drop the repeats; `@=<` and `@>=` keep them —
the rule of SWI's `sort/4`, kept word for word so that a reader who moves to SWI finds
the same table.  It reads backwards until it is said out loud: a repeat *is* equal to its
twin, and the sign that admits equality is the one that leaves the equal element in
place.  The sort is stable, so with a «keep» sign the repeats stand in their original
order, and with a «drop» sign the first of a run survives.

`СОРТИРОВКА/2` is exactly `СОРТИРОВКА(@<, …)`, and both arities go through one function
(`sortTerms`), so the two cannot drift apart.  A later `СОРТИРОВКА/4` with a key is
additive: the keyed form *is* `sort(0, Порядок, …)` when the key is `0`.

The order is an atom from a set of four; `<` and `>` are refused, because they compare
numbers rather than terms (`БОЛЬШЕ`/`МЕНЬШЕ` with an infix spelling), and a bare word is
refused as a typo.

**Consequences.**  `sort/3` exists as the English spelling — every Russian name carries
its English twin at every arity (`test_aliases.cpp` enforces it) — and that is an arity
SWI does not have, so the manual and `prologd-diff.typ` say plainly that the form with
the order is ours while SWI's has the key first.  `msort/2` in the standard library is
now describable as `СОРТИРОВКА(@=<, …)`, which is how the manual explains it.

**Status.** Accepted 2026-10-22 (task_95).

## ADR-031: `ВСЕРЕШ`/`МНОРЕШ` — a built-in that answers more than once

**Context.**  ADR-025 refused `bagof`/`setof` for three reasons, and the first of them
was the real one: `BuiltinResult` was `Continue`/`Fail`/`Handled`, so a built-in gave
one verdict and the machine moved on.  Task_91 wrote down two ways to get past it — **А**
a deterministic `группы_по/3` built-in plus a library recursion over the list of groups,
**Б** a new kind of choice point — and the owner chose **Б** (2026-10-22).  The same
frame is what `sub_string/5` needs to enumerate occurrences (task_84), so it is bought
once and used twice; the library version must hold *every* group in memory before the
first answer, and a cut inside a group cannot save that work.

**Decision.**  A built-in may now report `BuiltinResult::Yield` and leave its answers
in the engine (`Engine::setBuiltinChoice` / `takeBuiltinChoice`); `Solver::solveGoal`
turns them into a `ChoicePoint::Kind::Builtin` frame and hands out the first, and
`Solver::backtrack` takes the next one.  The frame is an ordinary `ChoicePoint` with one
more field — `std::unique_ptr<BuiltinChoice> payload`, null for the other kinds, so an
ordinary choice point pays one pointer for a feature it never uses — and its
`trail_mark` is taken *before* the call, because the bindings to undo are the previous
answer's, not only the last solution's.

Grouping happens once, up front, exactly as `НАЙТИВСЕ` collects:
`Engine::collectGroupedSolutions` rewrites the goal into
`$group($key(Свободные…), Шаблон)`, collects with `collectAll`, sorts by the key with
`stable_sort` and merges adjacent equal keys.  Free variables are the goal's minus the
template's minus the quantified ones, sorted by `VarId` so the key reads the same on
every solution.  `^` becomes a token and a parser level (`xfy 200`: tighter than `,`
and `;`, right-nested), and it is not a predicate: the checker opens it in front of a
`ВСЕРЕШ`/`МНОРЕШ` goal, and anywhere else `^/2` gets the usual unknown-name warning
plus the sentence that says where a quantifier belongs.

**Consequences.**  `ВСЕРЕШ/3` (`bagof`) answers once per group of free variables, `^`
keeps a variable out of the key, `МНОРЕШ/3` (`setof`) is the same plus `sortedTerms` —
the very function `СОРТИРОВКА` uses, so the two cannot disagree about «sorted».  An
empty collection **fails** (ISO, and the opposite of `НАЙТИВСЕ`'s `[]`), which is said
in three places: the manual, the technical reference and the example.  `!` after the
call cuts the remaining groups, as it cuts the clauses of a predicate.  A quantifier in
the middle of a conjunction stays what it looks like — an unknown `^/2` — and the hint
says the quantifier goes in front of the whole goal.  The old hint table rows for
`bagof`/`setof` are gone: they are built-ins now, and `test_diagnostics.cpp` asserts the
refusal is *no longer* there.

**Status.** Accepted 2026-10-22 (task_91).

## ADR-032: `ИСТИНА`/`true` exists, because an empty branch has to be a goal

**Context.**  The maze example walks a row and draws a wall where the character is
`#` — the ordinary Prolog idiom `( КОПИЯ(Строка, X, 1, "#") -> нарисовать_стенку(…)
; ИСТИНА )`.  The dialect had no `true/0`: the load failed with «не найдено: true/0»,
so there was no way to write «otherwise do nothing».  The alternatives were worse than
a built-in: a hand-written `ничего.` fact in every program (a name each author invents,
and the reader has to find it), or `; ВЫП(…)` games, or duplicating the recursion into
two clauses.  ISO has `true/0`, so the idiom is not ours to invent.

**Decision.**  `ИСТИНА/0` is a built-in that always succeeds and binds nothing;
`true` is its English name through the one table in `builtins.cpp`, exactly as
`ЛОЖЬ`/`fail`.  It is added to the lexer's reserved set (so a clause named `истина`
cannot shadow it), to `doc/builtins.json` (section 4.2, next to `ЛОЖЬ`) and to
`help.typ` §4.2, which now shows the empty-branch idiom as the reason the predicate
exists.

**Consequences.**  `(A -> B ; ИСТИНА)` and `ВЫП`-based alternatives both work, and a
program that never needs it pays nothing — one table row and one reserved word.  The
manual's appendix 17 gains the pair `ИСТИНА`/`true` by itself, because the table there
is generated from `builtins.json`.  `test_builtins_control.cpp` pins the behaviour
(`?ИСТИНА.`, `?true.`, the empty branch, `?НЕ(ИСТИНА)`, a conjunction).

**Status.** Accepted 2026-10-23 (task_97).

## ADR-033: A raster picture may be converted, but a 16-pixel mouse is drawn

**Context.**  The owner gave pictures for the maze (`ai/_ref/images`) and asked for a
converter that turns a picture into drawing predicates with configurable size, colour
count and pixel-merge factor.  `tools/image_to_pld.py` does that: background = the most
frequent colour, a cell's colour = the mean of its *ink* pixels only, palette by median
cut, rectangles merged greedily right-then-down.  Measured on 16×16 cells: the wall
comes out as 76 rectangles in 4 colours and is recognisably brick; the cheese is 45
rectangles and is recognisable; the mouse needs 45–70 and is **not**: its outline is
thinner than one cell, so averaging either smears it into a grey blob or drops it.
Raising the cell size fixes the mouse and makes the maze a picture instead of a grid.

**Decision.**  The example uses both routes, each where it wins.  The wall and the
cheese come from `maze.images.pld`, generated by the converter and shipped as facts
(regeneration is one command, stated in the file header).  The mouse is drawn with
primitives — two circles for the body and head, two for the ears, a `ТОЧКА` for the eye,
a `ЛИНИЯ` for the tail — so it stays readable at 16 pixels and the animation does not
depend on a raster.

**Consequences.**  `examples/problems/maze/` reads as two ideas instead of one: a
picture can be *data* (facts, drawn in a loop that fails after the last one) or *code*
(primitives).  The converter stays a tool, not part of the build: its output is
committed, so the example runs from a clean checkout without PySide6.  `ЗАКРАСКА/5` is
what both routes draw with, and it emits one `horizontal` per scan line, so a full
112×112 maze is about 3400 operations — cheap enough for the snapshot in
`tools/render_graphics.py`.

**Status.** Accepted 2026-10-23 (task_97).

## ADR-034: the directive imports definitions, the question imports a program

**Context.**  The loader ran the `?`-lines of every file it processed, imported
ones included.  That is a leftover of the previous version, where `?ИМПОРТ("f").`
was a preprocessor splice: `preprocessor.cpp` matched the line with a regexp and
substituted the file's text in its place, so the questions came along.  Nothing
shipped depends on it (75 files of `examples/` and `stdlib/`, not one import of a
file with questions), no test pinned it, and the manual never said it out loud.
The cost showed up on `examples/problems/maze/maze.pld`: importing it ran its
animation, ate the input file and could abort the importer's load.  A question
also runs against a half-built database — the importer's clauses after the
directive are not in yet — and the protocol's `questions: false` (task_36) can
only silence a whole load, not one import.

**Decision.**  The two spellings mean two things, and the parser records which one
was written (`ImportDirective::run_questions`, set from the `?`/`:-` marker).
`:- ИМПОРТ("f").` is the directive: the file contributes definitions, its
`?`-lines are parsed and statically checked but not run.  `?ИМПОРТ("f").` keeps
the splice of 2.0 and runs them, in the order they stand.  `loadFile`/`process`
carry the flag; `loadSource` (the window's `load`, and `-s`) still runs the
questions of the file it was given, and `questions: false` silences everything as
before.

**Consequences.**  A library is quiet: no output, no input consumed, no failed
question aborting the import — `maze.pld` can be imported while it still ends with
its own `?`-question, which is exactly what the example needs.  A program written
for 2.0 keeps its behaviour as long as it writes `?ИМПОРТ`, the spelling it
already used.  The rule is one line in the manual (§8) and one sentence in the
diff; «never run imported questions» was rejected because it would silently change
what an old program prints.  Two cases in `test_module_loader.cpp` pin both
halves, including the answer the spliced question prints for itself.

**Status.** Accepted 2026-10-23 (task_97).

## ADR-035: the program may name its canvas, and it wins over the front-end

**Context.**  The size of the screen was the front-end's to name: the protocol's
`load.screen` (task_73), the window's settings, and the engine's own 600 × 600
(the original dialect drew on 1024 × 768).  A program that draws a picture of a
known size — the maze is 14 cells of 16 pixels — had no way to say so and had to
be started with an extra setting that a reader of the source would not see.  The
window's choice is a *preference*; the program's need is a *fact*, and a fact
should travel with the file.

**Decision.**  `:- ХОЛСТ(Высота, Ширина).` (English `canvas`) is a directive the
loader applies while it loads the file: it therefore arrives after the front-end's
`screen` request and overrides it, exactly as `ИМЕНА` overrides the naming row of
the settings.  Both arguments are integer literals — the size must be known before
the first pixel, and an expression is evaluated only when a goal runs — and each
side must be 16…2048, the pair the protocol already enforced: `kMinScreen` and
`kMaxScreen` now live in `graphics.hpp` and both places use them.  The buffer is
cleared whenever the size is set, and the last directive of a program wins.
`GraphicsBackend` gains a virtual `reset(width, height)` — a no-op for the console
backend — so the loader resizes a canvas without knowing which backend it holds.

**Consequences.**  A program carries its canvas: `:- ХОЛСТ(224, 224).` above a
14 × 14 maze is enough, no flag and no settings row.  A library's directive counts
too, because the database is one for the whole program, and the last one wins —
said in the manual.  A front-end has to accept a bitmap of a size it did not ask
for; the snapshot carries `width` and `height`, so the window needed no change.
The name is `ХОЛСТ` rather than `ЭКРАН`, which would read as the *window*: the
canvas is what a program draws on, and `canvas` is the English word for it.

**Status.** Accepted 2026-10-23 (task_98).

## ADR-036: the converter is a menu entry, and its answer is a tab

**Context.**  `tools/image_to_pld.py` turns a picture into `картинка/6` facts, and
the maze example was written with it (ADR-033): background detection, ink-only
averaging, a median-cut palette, rectangle merging — ten flags that a student will
not type.  The window already knows the picture story (the graphics canvas), and a
converted picture is the one thing a reader wants *beside* a program rather than in
a terminal.

**Decision.**  A menu of its own, «Скрипты», before «Справка»: one entry,
«Сконвертировать картинку…», opens a dialog of the tool's own settings (picture,
name, grid, colours, background threshold, ink share, background), the window runs
the tool in *its own* interpreter (the tool imports PySide6 for the image), and the
facts it prints land in a new unnamed tab.  The tool gained a mode without `--out`
that prints the program and sends its summary to stderr, so the window needs no
temporary file and the answer is the text itself.  Cancel and a tool error are two
different answers: a cancellation is silent, a failure is a box with the tool's own
words.  Nothing is loaded into the interpreter — a conversion is text, not a run, so
it cannot disturb a session or a live database.

**Consequences.**  The dialog's fields are exactly the tool's keys (`scripts.py`
builds the command line, `scriptdialog.py` collects it), so one place decides what a
setting means; `test_scripts.py` checks the seam without a window — the menu is where
it belongs, the arguments are right, a generated picture becomes a program, and a
missing picture or a missing tool is an error with words.  That program is now the
whole answer and not just facts — `:- ХОЛСТ` the size of the picture, the facts, a
`нарисовать_картинку/1` that turns a cell into a rectangle and a closing question —
because the point of a tab is that it can be run; the file form keeps to facts
alone, since a file is imported and a directive would act on the importer
(ADR-034).  The text is broken the way `prologu --format soft` breaks it, and the
same suite pins that, so «Форматировать» on a fresh tab is a no-op.  A packaged
build has no `tools/` beside it, and the entry says so instead of running nothing (a
shipped copy of the converter is a separate question, not a task yet).

**Status.** Accepted 2026-10-23 (task_99).

## ADR-037: the grid follows the picture, and a cell has two sizes

**Context.**  The converter squeezed every picture into a square `--size` grid, so a
600x800 portrait came out as 512x512 and its shape was lost.  The one number was also
doing two jobs: `--size 16` meant «16 cells across» and «16 dots per cell» at once,
and the cells it cut were 18 or 19 source pixels wide depending on where the column
fell (600/32 is not an integer) — three different sizes pretending to be one.

**Decision.**  Two numbers, each with one meaning.  `--cell` is the size of a cell
**in pixels of the picture** (1..64, 16 by default) and the grid follows from it:
`cols = width / cell`, `rows = height / cell`, the remainder trimmed evenly from both
sides — 600 px at a cell of 16 is 37 cells and 4 px off each edge.  `--canvas-cell` is
the same cell **on the canvas**, in dots (1..32, `auto` by default); `auto` takes the
largest cell that keeps the longer side near the engine's default canvas (600 dots)
and the shorter side at least 16, the `ХОЛСТ` minimum.  So 600x800 is 37x50 cells,
148x200 dots at a cell of 4, and its proportions are the picture's.  The facts stay in
cell coordinates and do not depend on `--canvas-cell` — only the printed drawing
predicate and `:- ХОЛСТ` do, and the directive takes the height first.  `--size` is
gone: a sprite that must fill exactly one cell of a program says so with its own
`--cell` (the maze's 228-pixel cheese is `--cell 14`, which is 16 cells), and `--cell`
takes a comma list, one value per `--image`, because pictures differ in size.

**Consequences.**  `maze.images.pld` was regenerated with `--cell 14,4 --colors 4`;
the maze's own drawing did not change (`Слева + X1`), and the two renders differ in
224 pixels of 200704 — the cheese's edges, nothing else.  A canvas outside the
engine's 16..2048 is refused with both the numbers and what to change, as is a
picture smaller than its cell; nothing is clamped silently.  The dialog lost
«Сетка» and gained «Клетка картинки», «Клетка холста» and a live line «Сетка 37×50
клеток, холст 148×200 точек», so the `auto` rule now lives in two places — the tool
must work without a window — and `test_scripts.py` keeps them honest by running the
tool and comparing the dialog's promise with the `:- ХОЛСТ` it prints.  The tool
prints LF rather than the platform's CRLF, because the answer lands in a tab.

**Status.** Accepted 2026-10-23 (task_97).

## ADR-038: the naming conversion is the formatter's token pass, and it names its mode

**Superseded by ADR-053** (part 212): the conversion is gone from the engine.

**Context.**  The dialect reads names two ways (`--vars 0|1`, the file's own
`:- ИМЕНА(N).`) but prints them as written, so a program written for the original
engine stays unreadable to the ISO reader and back.  A Python port
(`ai/tools/port_lessons.py`) knows neither `:- ИМЕНА`, nor `'атом'`, nor `#…#`, nor
`A_`, nor `\"` inside a string, and renames keywords as a side effect — a second
lexer would be a second source of truth, drifting on the first unusual file.  The
formatter already walks the tokens of a source and rewrites only what it is told to.

**Decision.**  The conversion is a *print mode of the formatter*, not a separate
pass: `FormatOptions::names_out` says which mode to print, and the printer reads
each name from a map instead of from the source.  The map comes from
`variableNames(tokens, from, to)`, which reverses the lexer's own rules — the lexer
says what a name *is*, the map says how to spell it in the other mode.  The window
sends the formatter request it already sends with `names` added (protocol 15), so
there is no new command, no new response and no second text pipeline.

- Into ISO: the base is the name with its first letter up and its apostrophe off
  (`X'` → `X`, `var1'` → `Var1`); `_` and `_имя` are ISO variables as written.  A
  base one variable has is printed bare; a base several share (`Х`, `х`, `Х'`, `х'`)
  is numbered `Х_1…Х_n` in the order the variables are first written, and a base
  that is a reserved name is numbered too (a reserved word is a predicate in
  every mode and cannot be a variable).  Numbering is
  global per file, because one old name has to become one ISO name everywhere it
  appears.  An old-mode string (a bare capitalised name) gets quotes: `Str` →
  `"Str"`.
- Into the old dialect: `_`, `_имя`, a single code point and a letter with a
  trailing `_` are variables in both modes and stay; everything else gets the
  apostrophe that makes it one (`Сумма'`, `X_1'`).  A string stays a string —
  `"Str"` is a string in both modes, so unquoting it would buy nothing.  An *atom*
  of one letter or of a letter plus `_` takes single quotes, because the old
  dialect reads exactly that shape as a variable: `?одно(а, а).` asks about a
  constant in ISO and would answer `а=_1` in the old spelling, so it becomes
  `?одно('а', 'а').`; a one-letter functor becomes `'а'(1)` the same way.  Both
  spellings are checked against the pinned original, which answers ДА.
- The answer's first line is always the marker (`:- ИМЕНА(0).` or
  `:- ИМЕНА(1).`), replacing one that was there and being added when there was
  none: a converted file has to be read in the mode it is written in, and a reader
  that trusts the settings would otherwise read it in the wrong one.
- A fragment (`selection_only`) is never renamed: the numbering needs the whole
  program, and a fragment renamed on its own would number differently from the file
  it comes from.  `--format` and `--names` may be asked for together — one pass
  lays the text out *and* renames it.
- In the window the answer opens in a new unnamed tab («Скрипты →
  Сконвертировать исходник → PLD в ISO / ISO в PLD»), the source keeps what its
  author wrote, and the mode is forced to `soft`: a converted program is read
  afterwards, and a one-line answer is not.  The entry needs `engines.FORMAT`, so
  the original engine has it disabled.

**Consequences.**  Round trips settle: `Х,х,Х'` → `Х_1,Х_2,Х_3` → `Х_1',Х_2',Х_3'`
→ `Х_1,Х_2,Х_3`, and the second ISO pass is word for word the first.  One spelling
has no old-dialect form at all — an atom containing `'` — and it is left as it is
rather than refused: the conversion quotes what it can and never turns an atom into
a string.  The mode the source is *read* in still comes from its own marker, so a
file converted to ISO and saved can be opened and run without touching the row.
Protocol 15 is written down in four places (`protocol.cpp`, `protocol.py`,
`protocol_session.cmake`, `test_formatter.py`); a front end that does not send
`names` behaves exactly as before.

**Status.** Accepted 2026-10-23 (task_99); the rule about one-letter atoms and the
renaming of the two menu entries are part of it (part 167).

## ADR-039: the dialect conversion trades a call for the sign it already is

**Superseded by ADR-053** (part 212): the conversion is gone from the engine.

**Context.**  The dialect answers to two sets of names — the Russian built-ins and
their English aliases (task_39) — and to two spellings of four of them: `=`, `is`,
`<`, `>` and `\+` are sugar the parser melts into `РАВНО`, `МЕНЬШЕ`, `БОЛЬШЕ` and
`НЕ` (tasks 52, 55, 92).  A program written in Russian therefore has an
ISO-looking twin, and the owner asked for a conversion in both directions, beside
the naming one (task_99) that already rides the formatter's request.

**Decision.**  One more *print* option of the same request:
`FormatOptions::dialect_out` and a pass that runs **before** the naming pass and
the layout, so a single request can ask for all three.  The pass rewrites the
token list and copies every byte outside a rewritten span as it was written; the
answer is lexed and parsed again before it is returned, so a conversion cannot
turn a working file into a broken one.

- The names come from `builtinAliases()` (one place lists a pair, so no name can
  be invented) plus `ВЫП`/`call` and `ИМПОРТ`/`import`, which are answered outside
  that table.
- A call becomes a sign because the two are *the same term*, not because they
  look alike: `=` is `РАВНО/2`, `>` is `БОЛЬШЕ/2`, `\+` is `НЕ/1`, and `is` builds
  `РАВНО(X, ЭКСПР(Y))` — which is exactly `РАВНО(X, #Y#)`, since `#…#` is the
  expression wrapper.  That is why `РАВНО(X, #Y#)` → `X is Y` and not `X = Y`.
- A call keeps its name where a sign cannot stand: a nested operator call
  (`РАВНО(РАВНО(X, Y), Z)` has no spelling — `X = Y = Z` is a chain the language
  refuses), a comment inside the arguments (a rewrite would lose it), a wrong
  arity.  The rename still happens (`equal`, `greater`), so nothing is lost —
  only spelled out.  `ИЛИ` has no English name at all (task_83) and stays.
- The marker line `:- ИМЕНА(N).` is copied as it is: `variables(0)` would not be
  read as a marker, and the file is read by that line.
- A fragment (`selection_only`) is not converted: its structure is cut in the
  middle, and the rewrite needs whole terms.

**Consequences.**  A Russian program can be printed as an ISO one and back, and
the round trip settles: `en → ru → en` is word for word the first text.  The two
axes are independent and composable (`--dialect en --names 0 --format=hard`), and
the window lists both in one submenu — «Имена: …» and «Диалект: …» — so the user
sees which of the two rewrites is meant before clicking.  Protocol 16 carries the
new field; a front end that does not send `dialect` behaves as before.  What the
conversion cannot say, it leaves in the other language — `equal(X, Y)` is still
this dialect's name, not ISO's (ISO writes `=(X, Y)`, which our parser does not
read), and that is the one place where "as ISO as possible" stops.

**Status.** Accepted 2026-10-23 (task_101).

## ADR-040: the popup reads an imported file once, and only its predicates

**Context.**  Completion offered the names written in the buffer, and a name that
a program *imports* lives in another file — in Prolog that is very often the name
of the next goal (lesson 11 is «import the library, then call `член`»).  The two
halves of the answer already existed: `paths.resolve_import` repeats the engine's
search order for `F12` (task_69), and `collect_names` is a pure function of a text.

**Decision.**  A third source of candidates, `IMPORTED`, filled from the files the
`ИМПОРТ` directives of a buffer name.  The window is the half that knows the search
directories and the interpreter, so it hands the editor a *lookup* — directive names
in, `{path: text}` out — and the editor asks it only when the list of directive
names changed.  Files are read once per version (size and modification time), and
the walk is recursive with a `seen` set and the search restarted in each importing
file's own folder, because a file may import its own and the engine tolerates a
cycle.

Only **predicates** are taken from an imported file.  Its atoms (a colour, a kind
of friction) are not what the next goal is typed with, and a library of a thousand
facts would bury the names of the document itself.  A name the document already has
stays the document's, and a reserved name stays reserved; the ranking puts a
reserved name first, the document's own next and an imported one last, so the
import can add names but never push the buffer's own out of the way.

**Consequences.**  The popup is a function of three things now — reserved names,
the buffer's text and the imported texts — and `set_imported` invalidates the
candidate list only when the set of texts actually differs.  The label under the
popup says «импорт: библиотека.pld» for a name that has no record of its own: a
library predicate has no description, but it does have a file.  A file edited in
another tab is picked up when it is saved, not before: the cache is keyed by the
file's version on disk, and keying it by the buffer's text instead would mean
wiring every buffer into the popup.  A name that cannot be found is not reported —
the interpreter says so when the program runs.

**Status.** Accepted 2026-10-23 (task_102).

## ADR-041: the popup reads the comment the author wrote, and F12 reads the clause

**Context.**  A library documents its predicates the way a Prolog file always has —
with `%` lines right above the clause (`stdlib/iso.pld` does it for every name) —
and both the popup and the keyboard were blind to that text: the label under the
popup knew only `doc/builtins.json`, and `F12` knew only the `ИМПОРТ` directive
(task_69).  The user has to open the file to see either.

**Decision.**  Two small readers, both line-based like the completion scan, because
the text may be mid-edit and not parse at all.

- **The comment**: `collect_names` returns it with the name — the `%` block written
  *directly above* the first clause head, joined into one paragraph.  The block
  ends at a blank line, which is what keeps a file's header off its first
  predicate.  `Candidate.summary` carries it and the label under the popup shows,
  in order: the imported file, the comment, the built-in record.
- **The definition**: `definitions.py` finds the first clause head of a name by the
  shape every program has — the name is the line's first token, the next one opens
  its arguments, ends the sentence or starts the body.  `F12` asks it for the name
  under the caret, first in the buffer and then in the files its imports bring in
  (the popup's own list), and moves the caret or opens the tab.

**Consequences.**  The popup now says something about a user's own predicate, and
the answer comes from the file rather than from a documentation table that would
have to be kept in step — a library can document itself.  `F12` gained a second
duty on the same key and lost its narrow title («Перейти к определению» covers
both, and the entry is offered wherever there is a name, with the search done on
the key press).  The scan is deliberately line-based: a name mentioned in a comment
is not a definition, a goal is not a head, and an operator-style head is not
recognised — the price of working in a buffer that does not parse.

**Status.** Accepted 2026-10-23 (task_103).

## ADR-042: one string in the language is a path, and only that one completes

**Context.**  The popup says nothing inside a string, and that rule is deliberate:
a string is not code, and `ВЫВОД("при|")` has nothing to offer.  But one string in
the language *is* a path — the argument of `:- ИМПОРТ("…").` — and a mistyped file
name is found only when the program runs (the message then lists every path tried,
which is honest but late).

**Decision.**  A narrow exception, expressed as a question about the text and the
caret rather than as a mode of the editor: `imports.import_argument_at` recognises
the directive and the caret *inside its literal*, and answers what is typed — the
folder part and the name part.  Inside that one string the popup offers files and
folders from the folders the run would search (`search_folders`: the file's own,
the `-I` rows, `stdlib`), one letter is enough, `/` opens a folder, and accepting
replaces only the name part so a hand-typed `lib/` stays.  Every other string keeps
the old silence, and the entry inserts a bare name — no brackets, no arity.

**Consequences.**  The completion now has a second *kind* of candidate (a file name)
with the same plumbing: `Candidate` with no arity inserts the name and nothing else,
`_insert_completion` takes the prefix from the mode instead of `word_before` (a
path may contain `-`).  The folders are listed on demand and never cached beyond the
call: a folder listing is cheap, and a stale cache in a popup is worse than none.
A missing folder is silent — a half-typed path is the normal state while typing.
What was *not* built is any index of the disk: the popup lists the folders the
engine would try, one level at a time, and nothing else.

**Status.** Accepted 2026-10-24 (task_104).

## ADR-043: a directive is completed as the statement it has to be

**Context.**  `ИМПОРТ` arrives in the keyword table as a *directive* — a name with
no arities — and the popup offered it like an operator: the bare word.  Accepting
it wrote `ИМПОРТ` where the language wants `:- ИМПОРТ("файл.pld").`, so the answer
was a sentence that does not parse.  The owner asked for the whole statement on
`ИМ|`.

**Decision.**  A directive candidate carries its own skeleton: a small table names
the text and where the caret goes (`:- ИМПОРТ("").`, after the opening quote), and
`Candidate` learned three things — `display` (the whole statement is what the popup
shows), `skeleton` (what accepting inserts) and `directive` (that it is one).
Matching stays by name, so `ИМ` finds it and the ranking is untouched.  The editor
offers it only where a statement can start — nothing but whitespace before the
typed word on its line — because a directive in a body is a syntax error, and a
popup that offers one is offering the error.

**Consequences.**  The chain `ИМ` → `:- ИМПОРТ("")` → `iso` → `iso.pld` is one
flow: the skeleton leaves the caret where the string completion of task_104 works,
so the two features meet without either knowing about the other.  A future
directive with a shape of its own (`ХОЛСТ`) is one line in the table.  What is not
built: a template inserts no newline and no trailing text — the line belongs to the
user.

**Status.** Accepted 2026-10-24 (task_105).

## ADR-044: the template carries its caret, and the marker carries its line

**Partly superseded by ADR-054** (part 213): the marker's first-line rule went
with the modes; the caret template stays.

**Context.**  task_105 gave `ИМПОРТ` a skeleton and left the rest of the family
alone: `ХОЛСТ` still arrived as a bare name (accepting it wrote `ХОЛСТ` where the
language wants `:- ХОЛСТ(Высота, Ширина).`), and `ИМЕНА` — the names marker —
arrived as the call `ИМЕНА/1`, which is exactly the form that *fails*: the builtin
raises «режим имён задаётся первой строкой файла».  The owner asked for both,
written as the statements they are.

**Decision.**  The table is `STATEMENT_TEMPLATES`, keyed by name, and it is
consulted *before* the arities — a name in it has no call form to offer at all.
An entry is a `Statement(template, first_line)` whose template carries a `|` where
the caret goes (`':- ХОЛСТ(|, ).'`): the mark says both things at once, needs no
arithmetic, and survives a quote or a comma standing before it.  `ИМЕНА` is marked
`first_line`, and the editor drops it unless the caret is on the file's first line
(`completion.at_file_start`) — the rule the loader itself follows, since
`readVariableMarker` reads line one and only line one.

**Consequences.**  On the first line `ИМ` offers the marker *and* the import, with
`:- ИМЕНА().` first because the alphabet says so — which is also what a first line
is for; below it only `:- ИМПОРТ("").` is offered, so the task_105 flow is
unchanged.  `ХОЛ` meets the comma, so the height is typed where it belongs.  The
English spellings `import`/`canvas` have templates of their own, but `variables`
deliberately has none: the marker reader knows the Russian spelling only, and
`:- variables(0).` was checked on the engine — it answers with the very error above
(exit 3) while `:- ИМЕНА(0).` loads.  The alias is therefore still offered as a
call, which is a wart of the alias table rather than of this table (removed in
ADR-045, task_107).

**Status.** Accepted 2026-10-24 (task_106).

## ADR-045: the names marker has one spelling, because the loader knows one

**Superseded by ADR-054** (part 213): there is no marker at all any more.

**Context.**  `variables` was registered as the English spelling of `ИМЕНА` by the
same `add` that registers every alias, but the marker is not a normal builtin: the
mode of a file is read by `readVariableMarker` *before* lexing, and that reader
matches the word `ИМЕНА` only.  So `:- variables(0).` on a first line did not set
anything — it fell through to the directive and the builtin raised «режим имён
задаётся первой строкой файла» (checked on the engine: exit 3, while the Russian
line loads).  A name that can only fail is worse than no name: it is offered by
completion and by `--list-keywords`, and the reference panel documents it.

**Decision.**  Remove the alias (`kEnglishNames` in `builtins.cpp`) and the word's
reservation as a keyword (`kReservedBuiltins` in `lexer.cpp`), and keep it as a
*retired* spelling (`kRetiredBuiltinNames`, message in `checks.cpp`): a call to it
is then an error that says what to write, exactly as `substring` does since
task_84.  Retired is not reserved: `--list-keywords`, the popup and the reference
panel no longer know the word, so the mistake cannot be made by choosing it from a
list.

**Consequences.**  `ИМЕНА/1` is the only spelling of the marker, and the reference
record, the English-names appendix and the `--dialect` paragraph all name it that
way (the appendix skips records with no alias, and says why).  `test_aliases.cpp`
counts `ИМЕНА` among the names with no English spelling, and
`test_diagnostics.cpp` pins the message.  `ctest` is 423 tests, the reference check
covers 128 reserved names.

**Status.** Accepted 2026-10-24 (task_107).

## ADR-046: the closing question belongs to what has nowhere else to go

**Context.**  Closing the window asked about every modified buffer, and «Сохранить»
on an unnamed one opened a file dialog for a program that had no name yet — while
the session was already keeping that program's *text* and bringing it back on the
next start (task_29/task_49).  A **file** tab is remembered by its path only, so its
unsaved edits really are lost unless they are written; the question there is the
whole point.  The owner asked whether unnamed tabs should be asked about at all,
and whether the Notepad++ habit (save everything on exit, restore everything) is
better.

**Decision.**  The window asks only where the session cannot keep the work: a buffer
with a file, an unnamed buffer while «Восстанавливать вкладки при старте» is off, and
an unnamed buffer whose text is over `SESSION_TEXT_BUDGET`.  The last of those is why
the budget became **per buffer** instead of per session: it is now exactly the size
that decides whether a question is needed, so one big scratch tab cannot cost the
small one beside it.  The rule lives in `_closing_needs_a_question` and applies to
the *window's* close only (`self._closing`): closing a tab, «Закрыть все вкладки»
and the tab menu have no session behind them and still ask about everything.

The Notepad++ route was turned down: it writes the user's files without a question
at exit, it would need the text of *file* buffers in the session (today only
untitled text is stored there), and it makes «Не сохранять» untrue.

**Consequences.**  The promise is spoken: closing silently keeps an unnamed tab by
writing it into the settings file, so a store that cannot be written would make the
silence a lie — `Settings.write_failed` (from `QSettings.status`) makes the window
warn before it goes, and the close still happens, because a warning must not become
a veto.  «Не сохранять» for an unnamed tab now belongs to the tab's own close, where
it still means «не показывать больше»; the session drops such a buffer as before
(`_discarded`).  A program generated by a script («Сконвертировать картинку»,
«Сконвертировать исходник») is an unnamed tab like any other, so it comes back with
its text instead of a save question — a generated program is scratch work until the
user gives it a name.

**Status.** Accepted 2026-10-24 (task_108).

## ADR-047: what the window reads twice must read the same thing twice

**Context.**  Two defects of one shape, both found by the owner after the first
`F5`.  (1) The reserved names reach the window from two places: `--list-keywords`
before the first run (no kinds — `ИМПОРТ` is a `KEYWORD`) and the `ready` event
from then on (`"kind": "directive"`).  `imports.directive_names`,
`imports.import_argument_at` and `theme._BOLD_KINDS` each knew one half: after the
first run the directive named no file (the popup lost every imported name, `F12` on
one said «не найдено», the file name inside the brackets stopped completing) and
stopped being bold.  (2) The «Дополнительные каталоги ИМПОРТ» list was handed over
as typed, and its two readers resolve a relative folder differently — the window
against its own working directory, the interpreter against the running program's
folder — so a row of `stdlib` meant one folder to the popup and another to the run.

**Decision.**  One predicate for «this token is the directive's name»
(`imports.is_directive_name`), accepting every kind that name can arrive as —
`DIRECTIVE`, `KEYWORD`, `ATOM`, `VARIABLE` — and used by both functions that look
for it; `DIRECTIVE` counts as bold, because the two tables describe one word.  The
`-I` list is handed over as absolute paths (`os.path.abspath`: a spelling rewrite,
no disk, and it is asked on every keystroke).

**Consequences.**  The popup, `F12` and the colours no longer depend on whether a
run has happened yet.  A relative row is resolved once, by the window, and both
readers see the same folder.  What is *not* fixed, and is not a defect: in a build
tree the engine's own `stdlib` search looks beside `prologu.exe`, which is deep in
`build/…`, so `ИМПОРТ("iso.pld")` needs `-I <repo>/stdlib` there; in the portable
package `stdlib` sits beside the executable and no `-I` is needed.

**Status.** Accepted 2026-10-24 (task_111).

## ADR-048: the welcome follows the engines the build carries

**Context.**  The first tab used to hold a bare example program written in the
intersection of the dialects (task_79).  The owner turned it into a map of the
window — commands, a completion hint, a program whose questions show the answer
table — and wanted a build with the original engine alone to show less: `ИМПОРТ`
and `length` are not its words, and the first thing a welcome must do is run.

**Decision.**  Two texts: `WELCOME_COMMON` (the window's own hints and the program
both engines read) and `WELCOME_OURS` (four lines our engine adds above it).
`welcome_text(ours_present)` chooses, and the answer comes from
`paths.engine_present(engines.OURS, folder=self._engine_folder)` — the same fact the
window uses for `--exe` and for the «only engine this build has» message.  No flag
in `tools/build_portable.ps1`: the packaging script describes what it ships, and the
window sees it.

**Consequences.**  `both` and `u` show the whole map, `d` the commons.  The text
lives in two spellings of one program, so the promise «answers on either engine» is
checked twice: the common text on both engines, the whole text on ours (with the
repository's `stdlib` on the import path — a build tree has none beside the
executable, the package does).  The manual does not quote the program any more: it
describes the features the text demonstrates, and a copy in two places would drift.

**Status.** Accepted 2026-10-24 (task_112).

## ADR-049: `СЛУЧ` maps the engine output itself, not through a distribution

**Context.**  `std::mt19937_64` is specified bit for bit: the same seed produces
the same raw stream in every standard library.  `std::uniform_int_distribution`
is not specified: MSVC takes the low half of a draw, libstdc++ 15 takes the high
half (Lemire's method), so a seeded program printed `-286924074` on Windows and
`1095884669` on Linux.  The arithmetic test pinned the Windows number, and the
portability audit (task_19) asked for a sequence that does not depend on the
platform.

**Decision.**  `builtins_arith.cpp` turns engine output into a range with its own
rejection-based mapping (`randomOffset` / `randomInRange`): drop draws below
`2^64 mod bound`, then take `value % bound`.  Both forms of `СЛУЧ` use it.

**Consequences.**  A seeded `СЛУЧ` now draws the same numbers on every platform
and every standard library.  For `СЛУЧ(X)` the mapping happens to reproduce the
value the MSVC distribution produced, so the pinned test expectation did not
change; a future change to the mapping is a behaviour change and must update that
test.

**Status.** Accepted 2026-10-24.

## ADR-050: the Debian package is one frozen folder under `/opt`

**Context.**  The portable Windows package works because the window, both engines
and their data sit in one folder: the window looks for the engines beside itself
and the engine searches `stdlib` beside itself.  A Debian package must not keep
the settings there — `/opt` is root-owned — and Debian policy dislikes `/opt`
altogether.  The task asked where the Linux install lives, whether to freeze the
window or use the distribution's PySide6, and how `/usr/bin` should point at it.

**Decision.**  `/opt/prologd` is that one folder: the frozen window, `prologu`,
`prologd`, the PDFs and `builtins.json`, `examples` and `stdlib`.
`/usr/bin/prologd-gui` is a two-line wrapper that `exec`s the frozen window; the
desktop entry, the MIME type, the hicolor icons and the package's copyright live
in `/usr`.  `paths.install_roots()` treats `/opt`, `/usr` and `/usr/local` as
install locations on non-Windows, so the settings go to XDG by rule rather than
by a failed writability probe.  The window is frozen with PyInstaller on Linux
too: the distro's PySide6 is older than the version the sources use, and the
Windows package already takes this route.  The desktop/MIME entries declare the
type but never set a default handler.  The deliberate departures from policy —
`/opt`, bundled Qt/Python, the unhardened PyInstaller bootloader, no man page —
are recorded in `installer/linux/lintian-overrides`.

**Consequences.**  `dpkg` owns every installed file, so `apt remove` leaves
`/opt` and `/usr` clean.  Copying the installed folder elsewhere still behaves as
a portable copy, because it is no longer under an install root.  `lintian` is
clean only with the overrides; the package is not archive-ready, which is the
price of keeping one folder.  The wrapper leaves room for a `--settings`
argument later; the settings rule itself does not depend on it.

**Status.** Accepted 2026-10-25 (task_118).

## ADR-051: a macOS `.app` is installed, and its settings live in Application Support

**Context.**  The window finds its settings by asking `paths.settings_path()`; a
portable folder keeps `gui.ini` beside the executable, an installed copy lets Qt
choose the per-user directory.  On macOS PyInstaller puts the executable in
`PrologD.app/Contents/MacOS`, which is writable for the user — the old rule would
therefore write `gui.ini` into the bundle and change a signed app on the first
close.  Qt's `AppConfigLocation` on macOS is `~/Library/Preferences`, the place for
property lists, while the task's layout calls for `~/Library/Application Support`.

**Decision.**  `paths.inside_app_bundle()` recognises `Contents/MacOS` under a
`.app`; `settings_path()` answers `None` for it, so the window uses
`settings.default_path()`.  That function uses `AppDataLocation`
(`~/Library/Application Support/PrologD/gui`) on macOS and keeps
`AppConfigLocation` (`AppData/Local` on Windows, `~/.config` on Linux) elsewhere.
A copy of the same folder outside a `.app` remains portable.  The `macos-release`
CMake preset sets the deployment target to 14.4, the floor of the PySide6 6.12/Qt
6.12 wheels the Linux and macOS builds install.

**Consequences.**  The bundle can be signed: nothing writes into `Contents/MacOS`
on a normal close.  Settings survive an app upgrade and a reinstall, and a user who
copies the folder to a USB stick still gets the portable behaviour.  A macOS
release built with PySide6 6.8 instead would have to lower the preset and
`LSMinimumSystemVersion` together; claiming 12.0 while shipping Qt 6.12 would be a
lie.  The shortcut table is a separate gap: its Windows scan codes do not match
the macOS key codes, and that is recorded in task_119.

**Status.** Accepted 2026-10-25 (task_119).

## ADR-052: one engine — the second one is gone

**Context.**  task_78 built the original Пролог-Д beside ours as an `ExternalProject`
pinned to a commit; the window was a *host of two programs* (task_79), with a switch on
the toolbar, a `view/engine` key, a capability table (`Action.needs`,
`settings.GATED_ROWS`) and a packaging flag `-Engine both|u|d`.  That second engine was
a different dialect in a different encoding with its own command line, and all of it
existed to run programs of the previous dialect — a need `--vars 1` already answers,
because the naming modes are ours.

**Decision.**  The repository builds **one** engine.  Removed: the CMake option and the
pinned commit, `src/gui/prologd_gui/engines.py` with the capability table, the
`view/engine` key, `-Engine` in both Windows scripts, `engine-1.x.png`, the `1.x` row of
the state control, `doc/prologd-diff.typ`, and the `.deb`/`.dmg`/zip payload of the
second binary.  The `/usr/bin` and App Paths entries for `prologd.exe` went with it.

**What survives on purpose.**  The *naming modes* (`--vars 0|1`, `:- ИМЕНА(N).`) and
the formatter's reverse direction: they read and write the previous dialect's names, and
`examples/prologd/` — byte-for-byte upstream — is still the corpus those modes are
checked against.  The state control stays, now with two rows, `ISO` and `PLD`.

**Consequences.**  One `prologu` to search for, one feature set, no gating anywhere; a
package is smaller and its layout is the same on every platform.  The prose that
compared three «Пролог-Д» columns (`doc/help.typ`) now compares two modes of one engine
against SWI and GNU Prolog.  Nothing in the repository can run `examples/prologd/`
verbatim any more — that corpus is a reference, not a test.

## ADR-053: the engine reads both naming modes but does not rewrite a program for you

**Context.**  task_99 and task_101 taught `--format` to answer with a *different* program:
`--names 0|1` respelled the variables between the two naming modes, `--dialect ru|en`
swapped the built-in names and their sign spellings, and the window offered both under
«Скрипты → Сконвертировать исходник».  The two passes worked, but they made the formatter
answer for things it does not own: the `format` request carried two more fields, the
protocol went to 16 for a front-end feature, and every rule of the *reader* had to be
written a second time, backwards, in the writer — numbered variables (`Х_1`), quotes
around a one-letter atom, an apostrophe after a long name, and a list of which built-ins
have a sign.  Both commits were the last two of the release, so removing them was also
how the owner wanted the record to read: the naming modes stay, the automatic translation
goes.

**Decision.**  `formatSource` only lays text out.  Removed with the passes: `Dialect`,
`FormatOptions::names_out`, `FormatOptions::dialect_out`, `variableNames`,
`planNames`, the `replacements_` map the printer consulted, `DialectConverter` and the
whole sign-and-alias machinery behind it, `withModeMarker`, `src/prlib/utf8.*` (added for
the renaming) and the `variables` spelling in `lexer.cpp`.  The `format` request is the
one it was at protocol 14; `--names` and `--dialect` are gone from the command line; the
submenu is gone from the window.  This supersedes ADR-038, ADR-039, and the sentence in
ADR-052 that expected «the formatter's reverse direction» to stay.

**Why remove rather than hide.**  The conversion produced a *new program* that then had to
be read, debugged and run: a wrong apostrophe is a silent change of meaning (`а` the atom
became a variable), which is exactly the class of bug a convenience pass must not have.
Two of the rules were already known to be approximate — numbering had to be global to the
file, and a call with a comment inside could not be turned into a sign — and the owner
would rather rewrite the few programs that need it by hand than trust a partly-correct
rewriter.

**What still answers the need.**  `--vars 0|1` and a file's own `:- ИМЕНА(N).` line read
either naming mode directly, so an old program runs as it is; the state control switches
the mode for a file that declares none.  The ISO *reading* is unaffected: English built-in
names, `=`, `is`, `>`, `\+` are still understood and still parsed as sugar over the
Russian built-ins (ADR-039's premise holds), only the printing of them is gone.

## ADR-054: one reading of a name, and it is ISO's

**Context.**  task_67 taught the reader two naming modes — `0` (ISO: an upper-case
initial is a variable) and `1` (the previous dialect: any single letter is a variable,
a bare capitalised name is a string constant, a long variable name ends with an
apostrophe) — and let a file declare its own with `:- ИМЕНА(N).` on the first line.
The mode travelled everywhere: `--vars` on the command line, the `vars` field of the
`load`/`query`/`format` requests, `execution/variable_mode` in the window, a
`QToolButton` with two pictures on the toolbar, a rule of the highlighter, the
completer and `F12`.  The corpus it served is almost gone: `examples/prologd/` and the
`_old` lessons were the only programs written for it, and after the conversion passes
went (ADR-053) the owner asked for the modes themselves to go too.

**Decision.**  There is **one** way to read a name, and it is ISO's: a lower-case
initial is a name, an upper-case one a variable, `_` starts a variable, `'` quotes an
atom, and an apostrophe never ends a name.  Removed: `VariableMode`,
`variableModeFromNumber`, `readVariableMarker`, `LexerOptions`, `--vars`, the `vars`
protocol field (the protocol is now 15), `ИМЕНА/1` as a built-in, the settings row,
the toolbar control, the highlighter's `set_mode`, `mode_from_first_line` and the
`first_line` rule of the completion popup.  `examples/prologd/`, `examples/names.pld`,
`examples/lib/old_lib*.pld` and `examples/lessons/_old/` are deleted: they could not
be read any more, and keeping unreadable programs in a repository that ships them as
examples would be worse than losing the archive (git keeps it).

**The marker is still reserved, and it is an error.**  `ИМЕНА` and `variables` stay in
`kRetiredBuiltinNames`, so a file whose first line is `:- ИМЕНА(1).` parses as a call
and the checks refuse it with «режимов имён больше нет: имена читаются как в ISO…».
That is deliberately a *hard* error rather than a warning: the file was written for a
reading this engine no longer has, and its meaning would change silently — `Сумма'`
would be a name and a stray quote, `Вдова` a variable instead of a constant.  A
warning would let it load and answer something else.

**Consequences.**  The lexer keeps one branch instead of three, the formatter loses
the «unquoted string constant» span rule it needed for the old mode, and the window
loses a control, a settings row and a mode-dependent path through three modules.  What
stays is the *reading* of ISO spellings — English built-in names, `=`, `is`, `>`,
`\+` — which never depended on the mode: it is the parser's sugar over the Russian
built-ins (ADR-039).  A reader with a program in the previous dialect has to rewrite
its names by hand; the two rules that do most of the work are «one letter is a name,
not a variable» and «a long variable ends with an apostrophe».

## ADR-055: the program is `prologd`, and the language is 27.1

**Context.**  The engine had been renamed «Пролог-У» when the branch became
ISO-compatible (task_75/task_76): the target was `prologu`, the manuals said
«Пролог-У» and «Пролог-Д 2.0», the banner carried the build timestamp, and `ВЕРСИЯ`
printed that banner.  With the second engine gone (ADR-052) and the naming modes gone
(ADR-054) there is one interpreter in the repository, and two names for it — ours and
the previous one — read as two programs that are no longer there.

**Decision.**  One name: `prologd` — the target, the executable, and the word in every
manual, script and example.  No «Пролог-У», no «2.x», no «2.0»: the product is
«Пролог-Д», the language it reads is Пролог-Д, and the only number is the release.

**Two versions, on purpose.**  `prologd --version` prints `prologd 2.6.1
(2026-10-25)` — the *program*, with the day its release was cut (`PROLOGD_RELEASE_DATE`
in the top `CMakeLists.txt`, bumped with `VERSION`; a build timestamp would make the
same tag print differently on two machines).  `?ВЕРСИЯ` prints `27.1` — the
*language*, a constant (`kDialectVersion`) that never follows a release, because the
course's programs and lessons print it and a lesson that prints a version has to keep
printing it.  The two are not the same question: «which build am I running» is asked of
the console, «which dialect is this» of the program.

**Consequences.**  A lesson may now promise the `ВЕРСИЯ` line: the appendix prints
`27.1` and `ДА` and is checked like any other question.  A package keeps one binary
named `prologd`, so `/opt/prologd/prologd` is no longer a name that could be confused
with the original engine's `prologd.exe` — the original is not built any more
(ADR-052).

## ADR-056: `/` is the real quotient, `//` and `div` the whole one

**Context.**  The dialect's `/` truncated when both operands were integers: `1/2`
was `0`, and a real average needed a real operand somewhere.  That is C's rule, not
ISO's, and it was the last arithmetic operation whose *type* depended on the operands
rather than on the operator.  `mod` and `div` already existed; `rem` did not, and the
functions of ISO existed only as two-argument predicates (`sqrt(X, Y)`), so an
expression could not say `sqrt(2)`.

**Decision.**  Arithmetic follows ISO where the two differ:

* `/` is always the *real* quotient — `1 / 2` is `0.5`, `6 / 3` is `2.0`;
* `//` (a sign of its own) and `div` are the whole quotient, truncating toward zero:
  `-7 // 2` is `-3`, `-5 div 3` is `-1`;
* `rem` and `mod` answer the remainder *with the sign of the dividend*: `-5 rem 3`
  is `-2`.  ISO's `mod` takes the divisor's sign and would answer `1`; the owner
  asked to keep ours for now, so `mod` and `rem` are the same operation and the
  difference is written down in the manual and in the tests instead of being
  silently «fixed» in one of them;  **that part is superseded by ADR-065**
  (part 240): `div` and `mod` now round down, as ISO has them;
* the four integer operators refuse real operands with a type error naming the
  operator — a truncation nobody asked for is worse than a diagnostic.

The expressions also gained ISO's *functions*: `abs(X)`, `sign(X)`, `sqrt(X)`,
`sin(X)`, `cos(X)`, `tan(X)`, `exp(X)`, `log(X)`, the four rounding ones
`floor(X)`, `ceiling(X)`, `round(X)`, `truncate(X)` and the constant `pi`.  `abs`
and `sign` keep the type of the argument, the root and the five transcendental ones
always answer a real, the four rounding ones answer a whole number (an integer
argument comes back untouched — through `double` it would lose digits past 2^53).  A
function call
is recognised in the expression grammar by name, so `abs(2 - 5)` is parsed with the
arithmetic rules — the term grammar has no `-` and cannot take that argument.  A
value the function does not have (the root of a negative number, the logarithm of
zero, an overflow) is a *runtime error*, because an expression must produce a
number; the two-argument predicates of the same names keep answering `НЕТ` instead.
`log` has no two-argument twin at all: it is a function only.

`**` is ISO's power, with ISO's shape: tighter than the unary sign (`-2 ** 2` is
`-4`, `2 * 3 ** 2` is `18`) and non-associative, so `2 ** 3 ** 4` asks for the
brackets instead of guessing one of two readings that differ by a factor of
`2 ** 74`.  A whole base with a whole exponent that is not negative stays whole and
exact — `2 ** 100` keeps all thirty-one digits — and every other combination goes
through `pow` and answers a real (`2 ** -1` is `0.5`).  Two liberties are taken and
written down: a sign is read after `**` (`2 ** -1`, which ISO spells `2 ** (-1)`),
and a power whose answer would have more than twenty thousand digits is refused
with a message — ISO sets no such limit, but `2 ** 1000000000` would occupy every
byte the machine has, and a diagnostic is better than a hunt for the power button.

**Consequences.**  A program that used `/` on integers for whole division has to say
`//` or `div`; the repository's own programs were four lines (lesson 3, `iso/arith`,
`drawing.pld`, one test fixture) and all four were rewritten.  `sign`, `pi`, `log`
and the four rounding names are reserved names of a new kind (`function`): they are
not callable goals, and a goal named after them says so.  `**` is a sign of its own
in the lexer, so `2**3` is a power and never two multiplications; `^` stays the
quantifier of `ВСЕРЕШ`, which is why ISO's other spelling of the power is not
available here.  A student coming from ISO finds the arithmetic they know; a reader
of the previous dialect finds that `mod` still keeps the dividend's sign — the one
place where the two readings still differ, and it is documented rather than hidden.

## ADR-057: пять escape-последовательностей и отказ на остальное

**Context.**  Строки понимали только `\"` и `\\`, а перевод строки печатался как
две буквы `\n`.  Вывести текст в две строки можно было лишь двумя целями с `ПС`
между ними, а записать такой текст в файл через `ЗАПИСЬ_В` — склеивая куски.
Строка при этом не переходит через перевод строки: разбор обрывается на нём, и
незакрытый литерал — ошибка.  Значит, `\n` был единственным способом сказать
«здесь кончается строка текста».

**Decision.**  Внутри строк работают пять последовательностей: `\n`, `\t`, `\r`,
`\\` и `\"`.  Любая другая после обратного слэша — ошибка с перечнем того, что
есть, одна на литерал: `\q` — это опечатка, и молча оставить её буквами значило
бы отдать программе не тот текст, который написан.  Обратный слэш перед концом
строки — не escape-последовательность, а незаконченная запись.  В именах в
одинарных кавычках последовательностей нет: там кавычку удваивают (`'Иван''ы'`),
и это правило старого Пролог-Д оставлено как есть.  Печать строки не меняется —
строка печатается своим текстом, поэтому `\n` в ответе и в `ВЫВОД` — настоящий
перевод строки.

**Consequences.**  Программа, где обратный слэш был просто буквой (путь
`"C:\temp"`), теперь получает табуляцию: `\t` — известная последовательность, и
ошибки тут не будет.  Это записано в справке и в `technical.typ`, а не спрятано.
Студент получает привычное `\n` и `\t`; ответ интерпретатора с такой строкой
занимает несколько строк, что последовательно с правилом «строка — это текст», а
не с записью терма в кавычках.  Урок 6 показывает обе стороны: `ДЛИНА("a\tb")`
равна 3, а `ВЫВОД("1\n2\n\n3")` печатает четыре строки.

**Part 217 — the Windows paths.**  The rule above has a price, and the first to pay it
were three I/O tests: they pasted `temp_directory_path().string()` into the source of a
test program, and on the Windows runner that path is
`C:\Users\runneradmin\AppData\Local\Temp\…` — `\U` is then an unknown escape (an error)
and `\r` of `\runneradmin` a carriage return.  The fix is in the tests, not in the
language: `prologStringLiteral` (`src/tests/test_helpers.hpp`) doubles the backslash and
the quote, and every path that goes into program *text* goes through it.  Not processing
escapes inside `ИМПОРТ(...)` was considered and rejected: the lexer decodes the literal
before the parser knows the goal, `ИМПОРТ(Имя)` may take a variable, and `ЗАПИСЬ_В` and
`ЧТЕНИЕ_ИЗ` would need the same exception — a literal has to mean one thing everywhere.
The idiom for a person writing a Windows path by hand is the quoted atom,
`'C:\Users\имя\файл.txt'`: it has no escapes at all, and that is what `help.typ` says.

## ADR-058: a built-in can walk, and the walk belongs to `ПОДСТРОКА/5`

**Context.**  `sub_string/5` was written as a deterministic built-in and answered the
first solution of ISO's order, because `BuiltinResult` had been one outcome and a
built-in could not hand a choice point to the solver — `ВСЕРЕШ` (task_91) changed that,
but only for answers collected up front.  Meanwhile the predicate was English-only,
which left `sub_string` the one ISO name in the string group with no Russian spelling.

**Decision.**  The built-in yields answers one at a time: `BuiltinChoice` grew a
`produce` callback, asked only when the stored answers are used up, and `nullopt` from
it means «no more» and drops the callback.  `sub_string/5` uses it for the whole
enumeration in ISO's order — «До» from zero up, «Длина» from zero up inside it — so a
string of n characters costs n(n+1)/2 answers computed one at a time instead of
n(n+1)(n+2)/6 bytes of pieces held at once.  Bound counts narrow the walk
(`lengthsAt` intersects the three conditions) rather than filtering a list.  The
Russian name is `ПОДСТРОКА/5`, registered with `sub_string` as its English spelling;
the error messages keep naming the ISO form, which is the one the manual quotes, and
`builtins.json` carries the Russian name so the pair table in §17 prints it in the
Russian column.

**Consequences.**  `?sub_string("абаба", До, Длина, После, "ба")` now has two answers
and `?sub_string("ПРОЛОГ", До, Длина, После, Подстрока)` twenty-eight; a query that
wants the first says `!`, and `НАЙТИВСЕ` collects them all.  The tests that pinned one
answer gained the cut, the example program shows both, and the manual's «перебора
вхождений нет» paragraph became an explanation of the order.  `ПОДСТРОКА` is a new
reserved name — i.e. a program may not define its own `ПОДСТРОКА/5`, the same rule as
for every other built-in.

## ADR-059: case tells a predicate from a function

**Context.**  The six arithmetic predicates of English spelling (`abs/2`, `sqrt/2`,
`sin/2`, `cos/2`, `tan/2`, `exp/2`) were written in lowercase, and so are the functions
of the same names inside `#…#`.  One spelling therefore meant two things — a goal and
a name in an expression — and the only way to tell them apart was the number of
arguments.  Every other name of the dialect is a capital word (`БОЛЬШЕ`, `КОПИЯ`), so
the lowercase names were also the only ones that looked foreign.

**Decision.**  The predicates are `ABS/2`, `SQRT/2`, `SIN/2`, `COS/2`, `TAN/2` and
`EXP/2`; the functions keep the lowercase spelling of ISO.  Case is now the whole
difference: `ABS(X, Y)` is a goal that answers, `abs(X)` is a name inside `#…#` that
only computes.  Both spellings are reserved, the lowercase six are of the keyword kind
`function` (they have no arity), and the uppercase six are `predicate` arity two.

**Consequences.**  A program that called `abs/2` gets an error that names the new
spelling instead of «не найдено» — the retired-name table is where that message lives,
and only arity two is retired, because `abs/1` was never a predicate.  `stdlib/math.pld`
and the N-queens fixture were the only programs of the repository to be rewritten.
`builtins.json` carries a record for each spelling — the predicate points at §5.5 or
§5.6, the function at §3.3 — and the reference panel therefore shows `ABS/2` as a
predicate and `abs` as a function, which is exactly the distinction a reader of the
manual needs.  English names of the other built-ins stay lowercase (`is_whole`,
`findall`): only the arithmetic ones had a lowercase twin inside expressions, and only
they needed the case to tell them apart.

## ADR-060: a look-alike variable is a pair, and only of one letter

**Context.**  A program of this dialect is written in two alphabets at once — the
keywords and many predicates are Russian, the ISO names and most variables are Latin —
and a keyboard switches alphabets with one keystroke.  `С` (Cyrillic es) and `C` (Latin
cee) are the same shape on the screen and different variables to the engine, so
`БОЛЬШЕ(С, 0)` after `СЛОЖЕНИЕ(C, 1, С)` is a program that *looks* right and answers
wrong.  Nothing in the engine noticed: the singleton warning fires only for a variable
used once, and both spellings here are used.

**Decision.**  A new warning, `ErrorCode::ConfusableVariable`, for two names of one
clause that differ only in alphabet.  Its scope is deliberately narrow:

* **one code point only** — `Сумма` and `Cумма` are different names too, but a longer
  name has a meaning of its own, and guessing which spelling the author meant is not
  the engine's business;
* **one statement only** — each statement has its own scope, so `С` in one fact and
  `C` in another never share a variable and are not a typo.  A *question* is a
  statement too and is checked the same way: it is typed by hand, where the slip is
  likelier than anywhere else.  The singleton warning, by contrast, stays clause-only,
  because a variable used once in a question is how one asks;
* **a closed table of twelve** — `А В Е К М Н О Р С Т Х У` → `A B E K M H O P C T X Y`,
  the Cyrillic capitals drawn exactly like a Latin one.  This is not UTS #39
  confusables: a generated skeleton (`l`, `1` and `I` fold together) would flag names
  that are honest, and the twelve are the ones a Russian keyboard actually produces;
* **the warning stands at the second spelling** and names both, with the alphabet of
  each in words — «переменные «C» (латиница) и «С» (кириллица) выглядят одинаково, но
  это разные переменные» — because the second is where the reader has to look, and
  because the two letters themselves are indistinguishable in the message.

`_C` and `_С` are silent: a name with a leading underscore says "I meant to leave this
out", and the underscore already tells them apart at a glance.

**Consequences.**  It is a warning, so no program changes meaning and no exit code
changes; `--no-warnings` silences it as it does the others.  The check runs after
`warnSingletonVariables` on the same `usages_` table, so a body singleton gets both
messages — «встречается один раз» and «выглядят одинаково» — which is the truth: one
of the two spellings is a typo *and* the mistyped name is used once.  The test corpus
(`examples/`, `stdlib/`) had no such pair, so no lesson text changed.

## ADR-061: the GUI is sliced by what a rule needs, not by what the window owns

**Context.**  `window.py` reached 4596 lines and 256 methods on one class: the
controller that stitches `panels`, `editor`, `session`, `settings`, `search` and the
rest together.  It grows with every feature (98 commits touched it), and its own
section headings had stopped matching their contents — 678 lines under «the graphics
window» also held the formatter, `F12`, the tab menus and the questions of the margin.

The obvious move — split `MainWindow` into `RunController`, `FindController`,
`FileController` — is the wrong one here.  The 29 GUI scripts reach into the window
some 400 times (`_actions` alone 183, `_settings` 78, `_table` and `_input_console` 43
each), because those are the *surface* of the window, not its internals.  A split into
objects with their own state would either break that surface or duplicate it.

**Decision.**  Slice by rule, not by owner.  A piece moves out when its logic can be
stated without the window: the helper takes the few callables and widgets it needs as
arguments and knows nothing about `MainWindow`.

* `marks.py` — which tab a position names, and that one line is marked at a time.  It
  receives `_buffer_for_path` and `open_path` as callables, so the rules are exercised
  without a window.
* `outputfeed.py` — `OutputFeed`: the queue of what a run printed, the zero-timer, the
  join by kind, the three panes and the `refresh` callback.

The window keeps thin methods with the same names (`_append_output`,
`_mark_error_line`, …) because they are the surface: `_append_output` still is where
the answer table collects its text, and `_mark_error_line` still writes the status
line.  Nothing that a script touches changes its name.

**Consequences.**  The file did not shrink much (4596 → 4504), and that is the point:
the win is that two pieces of logic now have a contract and a home of their own, not
that a number went down.  The next slices, in the order they are worth doing: the find
bar (~300 lines), the answer table's run (~160), and the picture bridge (~250, the most
entangled).  Cutting the controller into mixins is ruled out — the coupling would stay
and only its address would change.

## ADR-062: a comment is a trap, and the story lives in the journal

**Context.**  The GUI carried 5432 lines of comments and docstrings — 32% of
`src/gui/prologd_gui` — and the owner asked whether they should be trimmed.  The
density was not an accident of one file: `window.py` 34.7%, `session.py` 36.6%,
`actions.py` 36.3%.  What it mostly held was good: the traps (`isHidden` vs
`isVisible`, `blockSignals` in `_set_checked`, `abspath` vs `resolve`, the X11
scan-code offset).  What it also held was *history* — 154 `task_NN` and 20 `part NNN`
pointers wrapped in paragraphs retelling what broke and when — which `ai/status.md`
already records in full.

**Decision.**  A comment or docstring states what the code does and **why not the
obvious alternative**, in as few lines as that takes.  The rule of thumb applied
across the GUI:

* **kept** — a trap a future editor would otherwise walk into; an ordering that must
  not be rearranged; a platform quirk; a pointer (`task_58`, `part 226`) where the
  reasoning is longer than the code;
* **cut** — the retelling of the defect that produced the line, the "we used to…, and
  then task_NN…" narrative, a paragraph that repeats what the docstring above it says,
  and a comment that restates the statement it stands over;
* **moved** — nothing: the story is already in the journal, and a code reader who
  wants it follows the pointer.

Long docstrings on a *public* entry point keep their contract (parameters, flags,
what is returned); the essays inside them go.

**Consequences.**  363 lines of notes left 19 files (notes 5432 → 5069, 32% → 30.6%),
and the biggest essays lost two thirds of their length: `run_program` 24 → 12,
`_import_directories` 20 → 8, `session.py`'s flood comment 16 → 5.  Only comments and
docstrings changed — an AST comparison with docstrings stripped is byte-identical for
every file — and all 29 GUI scripts with both CTest suites stayed green.  The
module *introductions* of the remaining small modules (12–24 lines, one to a file)
were left alone: they say what the module is for, which is the one thing a reader
cannot get from its code.

## ADR-063: the `F1` card is rich text from the records, not a page from Typst

**Context.**  The owner asked whether the predicate reference could look the way the
manuals do — «примерно как Typst» — and whether that meant one `.typ` per predicate,
compiled to PDF and shown in Qt.  The dock held three plain-text lines while
`doc/builtins.json` already carried the kind, arities, group, section, summary and
argument modes of 84 records.

**Decision.**  The card is **rich text built from the record**:
`reference.card_html(record, palette, mono)` — a pure function — rendered in a
`QTextBrowser` that zooms with the rest of the window.

The Typst routes were weighed and set aside:

* **one `.typ` per predicate, compiled to PDF** — 84 documents beside a JSON that
  already describes the same predicates, so the truth would live twice; `typst`
  would become a dependency of the *package* build, `QtPdf` would enter the freeze,
  and the PDF would fix its colours: a dark theme needs a second build of 84 pages.
  A dock is a card next to the code, not a page of a book;
* **one SVG per predicate from a Typst template** — visually the closest, but the
  text stops being selectable or searchable, and the colours would be baked twice
  as well.  Worth revisiting only if the card ever needs real typography (drop caps,
  two-dimensional layouts) that `QTextDocument` cannot express;
* **searching the PDF at runtime for the section** — fragile, and it would have made
  page numbers a runtime guess instead of a build result.

The one thing Typst still supplies is the **page**: `help.typ` ends with a hidden
`#context` block that queries the headings and emits `{number, page}` for each as a
`<help-sections>` metadata element, and `--target docs` writes that to
`doc/help_sections.json` (`doc/write_sections.cmake`, `typst eval` with `typst query`
as the fallback).  The card's section line is a link, and the window opens the PDF
with `#page=N` — a fragment most viewers honour and the rest ignore, so a missing map
costs the page and never the document.

**Consequences.**  The colours come from the theme palette (`syntax.keyword` for the
name, `placeholder` for the kind line, `alternate_base` for the row rules), so the
card is dark on a dark desktop — but a `QTextDocument` settles its text colour when it
is built, so the window re-renders the remembered record after a theme change.  The
prose is set in the interface face and only the calls in the editor's monospace one:
the dock stops looking like a log file.  `reference_text()` now answers the card's
plain text, so the existing `F1` check reads facts from it and the link from
`toHtml()`.  The map is a build artefact: gitignored, shipped by all three package
scripts, and absent in a fresh checkout, where the link opens the manual at its start.

---

## ADR-064: one exact comparison for every number, and printing that reads back

**Context.**  Three places compared numbers, and the two that handled a mixed pair
narrowed the integer to a `double`: the standard order (`order.cpp`), the
`ArithValue` comparison behind `БОЛЬШЕ`/`МЕНЬШЕ` (`builtins_arith.cpp`), and — by
an exact rule of its own — unification (`engine.cpp`).  On a pair near 2^53 the
three disagreed: `БОЛЬШЕ(2 ** 53 + 1, 2 ** 53 + 0.0)` was false, `compare` answered
`=`, `РАВНО` answered no.  The comparison was not even transitive, so
`std::stable_sort` inside `СОРТИРОВКА` ran on an invalid order and dropped the
wrong element: `[2 ** 53 + 1, 2 ** 53 + 0.0, 2 ** 53]` sorted to two different
lists depending on the input order.  Separately, `formatFloat` went through
`std::to_string`, which keeps six decimals: `#1/3#` was written `0.333333`, a text
that does not read back as the number it stands for.

**Decision.**  Numbers are compared by value **exactly, from one function**.
`compareNumbers(const Term&, const Term&)` in `term.hpp`/`term.cpp` is the rule:
two integers compare as integers, a mixed pair compares the integer with the real
without narrowing either side, NaN stands before every number.  The standard order
calls it; unification is `compareNumbers(...) == 0`; and the numbers an expression
has just produced go through the overload `compareNumbers(const ArithValue&, ...)`
in `engine.hpp`/`engine.cpp`, which converts to terms and calls the same rule, so
`БОЛЬШЕ`, `СРАВНЕНИЕ` and `РАВНО` cannot disagree by construction.  The relations
that check a computed value against a given one — `СЛОЖЕНИЕ` and `УМНОЖЕНИЕ` with
all three places bound, `ABS`, `SQRT`, the trigonometry — take the same answer
through a local `sameNumber`, which is that rule with NaN never equal to anything
(IEEE's answer, not the total order's).

`BigInt::fromDouble` had to become exact for this to hold: it divided the
magnitude by the base in `double`, and above 2^53 that dropped low digits (1846 of
3999 random large doubles came back wrong).  It now writes the whole part with
`std::to_chars(std::trunc(value), chars_format::fixed, 0)` — exact by definition —
and parses the digits, so the conversion is the number the double holds.

`formatFloat` prints the **shortest text that reads back as the same double**
(`std::to_chars` shortest), and appends `.0` when that text has neither a point nor
an exponent, so a real never prints as a whole number.  The lexer already read the
exponent form, so `1e+20` is a literal the parser takes.

The deliberate deviation from ISO stays: `1 = 1.0` holds (the original PrologD
compares values, and `help.typ` §4.7 says so).  ISO keeps the two types apart
because it has `==` to observe the difference; this dialect has no `==` at all
(`lexer.cpp` answers «не оператор»), so comparing values everywhere — `=`, `=:=`,
`<`, standard order — is *more* consistent than ISO's split, not less.  `ЦЕЛ/1` and
`ВЕЩ/1` still tell the kinds apart, and the arithmetic keeps them: `/` is the real
quotient, `//` the whole one.

**Consequences.**  `СОРТИРОВКА`, `СРАВНЕНИЕ`, `БОЛЬШЕ`, `МЕНЬШЕ` and `РАВНО` give
one answer about one pair, and `std::stable_sort` gets a real order again (the
mixed pair near 2^53 now sorts out deterministically).  Answers are longer than
before: `pi` prints all seventeen digits, and `2 ** 0.5 * 2 ** 0.5` prints
`2.0000000000000004` rather than a `2.0` that neither unified with it nor read back
as it.  A lesson and §3.3 say so, and the two lines that still described the
integer `/` of an older version (`#1/2#` is `0`, `ВЕЩ(#1/2#)` is false) are
corrected.  The paper trail for a real is now `to_chars`, which needs a C++17
library that has floating-point `to_chars` — GCC 11+, MSVC 2019 16.4+, libc++ 14+,
all below the C++23 the project already asks for.

**Status.** Accepted.

---

## ADR-065: `div` rounds down and `mod` keeps the divisor's sign

**Context.**  ADR-056 made `//` and `div` one operation (truncating) and `rem` and
`mod` another (the remainder of that truncation, with the dividend's sign), and
recorded the difference from ISO as an owner's choice.  The owner has now asked for
ISO: `div` and `mod` are the floored pair.

**Decision.**  The four whole operators are two pairs, and the pair decides how the
quotient rounds when the signs of the operands differ:

* `//` and `rem` truncate toward zero — `-7 // 2` is `-3`, `-7 rem 2` is `-1`;
* `div` and `mod` round down — `-7 div 2` is `-4`, `-7 mod 2` is `1`, and `5 mod -3`
  is `-1`.

`BigInt` already answers the truncated pair (`/` and `%`, both toward zero), so the
floored one is that answer one step lower whenever the division left a remainder
whose sign differs from the divisor's; the remainder is then measured from the
quotient below it, which is why `mod` carries the divisor's sign.  Each pair closes
its own identity — `A = (A // B) * B + A rem B` and `A = (A div B) * B + A mod B` —
which the test checks on both lines.

**Consequences.**  `div` and `mod` are no longer synonyms of `//` and `rem`, so the
manual's §3.3 lists four operators with two rules instead of two with a spelling
each, and `builtins.json` says so in the three records.  Nothing in `examples/` or
`stdlib/` changes answer: the corpus divides non-negative numbers only (`graphics.pld`
splits a colour code, `math.pld` takes a gcd and a half), where the two rules agree.
Each record of the reference now shows the negative case (`-5 mod 3` is `1`), which
is what a reader coming from ISO looks for.  The permutation is exact for every sign
combination: 574 pairs of `(a, b)` for `a` in -20…20 and `b` in -7…7 were run through
the interpreter and checked against Python's `//` and `%`, with no mismatch.

**Status.** Accepted.

---

## ADR-066: `halt/0` and nothing else, named `ЗАВЕРШЕНИЕ`

**Context.**  The owner asked whether the dialect wants `halt/0,1`.  The console and
the JSON session already have exit codes of their own — 0 clean, 2 a load or parse
failure, 3 a runtime failure — and a program could not influence any of them: a run
whose questions all failed still exited 0.  ISO's `halt` is the one built-in that
gives a program a say in how the session ends.

**Decision.**  The dialect takes `halt/0`: `ЗАВЕРШЕНИЕ` ends the session where it
stands and the front-end answers with 0.  `halt/1` is not here — a program-chosen
exit status would have to share the code space with the front-end's own 2 and 3,
and the owner chose the half that buys ISO compatibility without reopening that
question.

The signal is an exception of its own, `HaltRequest` in `engine.hpp`, and
deliberately not a `PrologRuntimeError`: the query did not fail, the session ended,
and the goals that answer every failure with «нет» (`НЕ`, `ПЕРВОЕ`, `НАЙТИВСЕ`,
`ДЛЯВСЕХ`) must let it through.  The console catches it around the whole run
(statements after the halt never execute, the exception goes up through the loader,
not back into it); the JSON session catches it in its request loop and breaks, so
the tail of the loop still flushes and emits `bye`; the test harness catches it and
marks the program as halted, because it stands in for a front-end and would
otherwise take the test binary down.

The Russian name is `ЗАВЕРШЕНИЕ` and not `ВЫХОД`: one letter away from `ВЫВОД`, and
the two mean opposite things — a student who types `ВЫХОД` where `ВЫВОД` was meant
would end the session in the middle of a lesson.  The pair is `ЗАВЕРШЕНИЕ`/`halt`,
like `ВЫВОД`/`write`.

**Consequences.**  A program can stop early — a branch that has decided everything
does not have to walk to the last line — and a console script sees the same 0 it
sees for a program that ran to the end.  In the window a halt is the end of the
session: the child process goes, `_on_ended` puts the buttons back, and the next
«Запустить» starts a new interpreter with an empty base (the clauses of the halted
run are gone, as they are after any new run).  `ЗАВЕРШЕНИЕ` is a reserved name, so
the call-site check knows its arity and `ЗАВЕРШЕНИЕ(0)` is a load-time error rather
than a silent «нет такого».  The manual's §4.10 says all of this, `builtins.json`
carries the record (the pair table in §17 and the `F1` card pick it up on their
own), and the README of the window says `bye` can now come from the program.

**Status.** Accepted.

## ADR-067: `АТОМ` and `СТРОКА` split `СИМВ`, and `atom("…")` is false

**Context.**  The port made text one kind in two spellings: a string was a term of
its own but every check that asked «is this text» answered for both, so
`atom("молоко")` was true.  The ISO predicate of that name asks something else —
`atom/1` is true for an atom and false for a string — and the library said so in a
comment instead of behaving so.  The owner had already decided not to make an atom
and a string the same thing; this is the other half of that decision: the *checks*
have to tell them apart.

**Decision.**  `АТОМ`/`atom` and `СТРОКА`/`string` are built in, one term kind each
(`TermKind::Atom`, `TermKind::String`), and `СИМВ`/`is_text` stays as the union the
dialect needs for «текст» — the kind every text-taking built-in accepts.  `[]` is an
atom, as it is in ISO: it is a constant like any other.

Conversions follow the same reading: `АТОМСТР`/`atom_string` translates one text
into the other kind and back, and refuses with a type error when an argument is
bound to the wrong kind — ISO calls that a type error, not a failure, and so does
this dialect.  Both arguments free is an error too (there is nothing to translate).

The library keeps its own predicates but stops redefining what is built in:
`stdlib/iso.pld` loses `atom/1`, `atomic/1` widens to `СИМВ` (a string is atomic,
as in ISO), and `callable/1` narrows to what the engine accepts as a goal —
`callable("молоко")` is now false, because `ВЫП("молоко")` is «Цель должна быть
предикатом».

**Consequences.**  The recorded difference from ISO in `doc/library.typ` and in the
journal is gone: a string is now excluded from `atom/1` here for the same reason as
in ISO, even though the string itself is a different thing (text in quotes here, a
code list there).  A program that asked `atom("…")` gets «нет» — that is the point,
and no shipped example did.  The two names are reserved, so the arity check, the
highlighter, completion and `--list-keywords` know them with no further work.
`examples/types.pld` is the one place that shows the whole set; §9 and §10 of the
manual carry the reading, and `doc/builtins.json` the records.

**Status.** Accepted.

## ADR-068: a position is `_at`, a value check is `ЗНАЧ`

**Context.**  Two naming questions came out of `examples/types.pld` (part 247).  First,
`is_letter/2` and `is_digit/2` take a *position* as their second argument, and a name
without `_at` promises a test of one term — a reader of ordinary Prolog would expect
`is_letter(X)`.  Second, `is_whole` and `is_number` had no Russian names at all, and
the obvious words were taken: `ПОЛНЫЙ` is `ground`, `ЦЕЛ` is `integer`, and `number/1`
in `stdlib/iso.pld` is the *strict* test, so a soft «ЧИСЛО» next to it would put two
different `number`s side by side.

**Decision.**  The English names say what the second argument is: `БУКВА/2` and
`ЦИФРА/2` answer to `is_letter_at` and `is_digit_at`.  The old spellings are retired
the way `substring` was — reserved, so a call reaches the checks and is told what to
write instead of being answered «не найдено».

The soft value checks get Russian names built from the check word and the tail `ЗНАЧ`:
`ЦЕЛЗНАЧ` is «значение целое», `ЧИСЛЗНАЧ` is «значение — число».  The tail does the
work the `is_` prefix does in English: it marks a predicate of ours, which looks at the
*value*, and keeps it apart from the type test of the same stem.  `is_whole` and
`is_number` stay as the English spellings through the ordinary alias table.

**Consequences.**  `#`-style naming rules are written where a new built-in is read
(`ai/conventions.md`): bare where the standard means the same, `is_` for a check of
ours, a trailing `_at` when the last argument is a position, `ЗНАЧ` for the soft value
checks, `X_to_Y` for a conversion.  The pair table in §17 gained `ЦЕЛЗНАЧ`/`is_whole`
and `ЧИСЛЗНАЧ`/`is_number` on its own, and §5.7 stopped saying «русского имени нет».
Nothing in the corpus called `is_letter` or `is_digit`, so no program needed changing;
both new spellings are reserved, keyworded and completed with no further work.

**Status.** Accepted.

## ADR-069: the packages carry four manuals, `technical.pdf` stays at home

**Context.**  Both packages — the Debian one (`tools/build_deb.sh`) and the portable
Windows folder that the Inno installer copies (`tools/build_portable.ps1`) — took all
five PDFs the `docs` target builds: `help`, `technical`, `gui`, `lessons`, `library`.
`technical.pdf` is the design document: the model of terms, unification, the machine,
the algorithm and its complexity, the test scheme.  Whoever opens it is working on the
engine, and both packages are made for the reader who *writes programs*: the same round
had already taken the `.typ` sources out of the package (task_116) for that reason.

**Decision.**  `DOCUMENTS` and `$documentNames` name four documents.  `technical.typ`
and its PDF stay in the repository, and the `docs` target keeps building it — the
conventions require looking at the changed pages of whatever manual was edited, and
`technical.typ` is edited with the engine.

**Consequences.**  The package carries `help`, `gui`, `lessons` and `library`.  Nothing
in the window or the interpreter opens `technical.pdf`, so no code had to move; both
scripts print the count from their list, so the messages followed on their own.  The
existence check now covers the four shipped PDFs, which is what it was for — catching a
`typst` that failed on a document the package needs — and `doc/README.md` keeps its
`typst compile` line for `technical.typ`, because building it by hand is how a change to
the engine's description is read.  The `.deb` loses about 350 KB.  That is not the
reason: the design document is for the person changing the engine, and beside
`help.pdf` it is noise.

**Status.** Accepted.

## ADR-070: the comparison signs stay the shout of `БОЛЬШЕ` and `МЕНЬШЕ`

**Context.**  The manual writes `A > B`, `A < B`, `A >= B`, `A =< B` as the sign
spellings of `БОЛЬШЕ`/`МЕНЬШЕ` (the last two through `НЕ`), and says so: the parser
substitutes the same goal.  In ISO the same four signs are arithmetic — both operands
are evaluated and must be numbers, so `"а" < "б"` there is a type error, while here it
is true, because `МЕНЬШЕ` compares values: numbers, texts, lists.  The owner asked
whether the signs should be made ISO-strict.

**Decision.**  They stay as they are: a sign is the shorthand of the word, and the word
compares values.  The divergence is written down in the manual — a `#warn` box in §5.1
and the reason given in §3.7, where `СОРТИРОВКА` refuses `<` because it sorts by the
standard order of terms, not by value.

**Consequences.**  A program that ISO answers correctly never changes meaning: correct
ISO code does not compare non-numbers with these signs.  What differs is only the
answer-to-error boundary, and it moves in the permissive direction — an ISO program with
this particular bug gets an answer here instead of a report.  The alternative — signs
strict, words wide — would have cost the invariant «знак -- это только запись» and
needed a second goal behind the same token, a hidden numeric check in the parser.
`=:=` and `=\=` stay arithmetic-only, as in ISO, and `@<` stays the standard order, so
each of the three notations keeps one meaning.

**Status.** Accepted.

## ADR-071: a malformed command line is exit code 1, whatever CLI11 thinks

**Context.**  The manual has promised «`1` -- ошибка в параметрах командной строки»
since the CLI was written, and the README repeated it.  It was not true: `main()`
returned `app.exit(parseError)`, so CLI11's own numbers reached the shell — 104 for a
number that is not a number, 105 for a value outside a set, 109 for an unknown option,
114 for a missing argument.  Code 1 was returned only by the checks made *after* the
parse (`--format` together with `--protocol json`, an `-i`/`-o`/`-e` file that does not
open), which is the rarer mistake of the two.

**Decision.**  The catch keeps `app.exit(parseError)` — it prints the message — and
returns 1 unless that code is 0.  Zero is the half that must survive: `--help` and
`--version` are `ParseError`s too, with code 0, and a script that builds and then asks
for help depends on that.

**Consequences.**  The documented contract is now the real one, for every kind of bad
command line, and no script has to learn four numbers that describe the mistake to the
parser rather than to the person who typed it.  Nothing else changed: the load and
parse failures keep 2, runtime errors keep 3, `--format` on unparsable input keeps 2,
and a program whose questions all failed still exits 0.  `cli_diagnostics.cmake` checks
both halves — an unknown option gives 1, `--help` gives 0 — and the check failed against
the old binary, so it guards the behaviour rather than describing it.

**Status.** Accepted.

## ADR-072: `sort/2` is the set and `msort/2` is the sort, so an English name belongs to an arity

**Context.**  `СОРТИРОВКА/2` was ISO's `sort/2` — sorted, repeats dropped — and
`msort/2` lived in `stdlib/iso.pld` as a Prolog merge sort because the engine had no
second sort.  The owner wanted the set to have a Russian name of its own
(`МНОЖЕСТВО`) and `СОРТИРОВКА/2` to be the `msort/2` of SWI: sorted, repeats kept,
with `СОРТИРОВКА/3` unchanged.

That splits one English spelling across two predicates: `sort/2` is the set, `sort/3`
is the sort with the order written down, and `msort/2` is the two-argument sort.  The
alias table gave one English spelling to every arity of a Russian name, which cannot
express it, and the reference test's model — spelling to record, arities equal — could
not express it either.

**Decision.**  `kEnglishNames` keeps the name-wide pairs; a second table,
`kEnglishNamesByArity`, names an arity and is consulted first.  `builtinAliases()` now
returns rows of `{russian, english, arity}` (arity empty for a variadic name) instead
of pairs, so the tests check one spelling at one arity.  `builtins.json` gains
`aliasArities` for a spelling that covers part of a record, and its records may now
share a spelling as long as their arities do not overlap.

Two sorts, one order: `МНОЖЕСТВО/2` is `sortedTerms(…, keepDuplicates: false)` —
`СОРТИРОВКА(@<, …)` — and `СОРТИРОВКА/2` is the same call with the flag set —
`СОРТИРОВКА(@=<, …)`, so `[1, 1.0]` stays whole even though the dialect calls those
one number.  The Prolog merge sort and its two helpers left `stdlib/iso.pld`: the
library keeps what ISO names, and `msort` is now a spelling of a built-in.

**Consequences.**  An ISO program that calls `sort/2` gets the same answer as before.
A program that relied on `sort/3` keeps it.  `msort/3` does not exist, and the parser
says so by name (`msort не имеет арности 3`).  `--list-keywords` prints `sort/2`,
`sort/3` and `msort/2`; the pair table of appendix 17 gained `МНОЖЕСТВО`/`sort` and
gained the sentence about `СОРТИРОВКА` having two English names.  `sets.pld` builds
its sets with `МНОЖЕСТВО` now, and the examples (`sort.pld`, `stdlib.pld`,
`lesson_05.pld`, `order.pld`, `problems/sorting.pld`) show the pair rather than one
predicate.

**Status.** Accepted.

## ADR-073: a type error names the kind of the term and the spelling that was typed

**Context.**  The owner compared our refusal with SWI's and asked for
`sort("abacb", X): Недопустимый тип аргументов: аргумент 1: ожидался список, найден
"abacb" (строка)`.  The comparison found a real defect: answers print strings without
quotes on purpose (§6.1, ADR-067), so the same rule in a diagnostic made a string
indistinguishable from an atom of the same letters — `МНОЖЕСТВО("abacb", X)` blamed an
argument that read exactly like `abacb`.  The second defect came with part 259: the
message named the Russian original, so `?msort("ab", X).` was refused in the name of
`СОРТИРОВКА`, a word the person never typed.

**Decision.**  The message keeps its shape — one line, compiler style, no full stop —
and gains two things.  Every argument is named by kind (`число`, `атом`, `строка`,
`список`, `составной терм`) before its value, and a string is written in the quotes it
was typed with, escapes included.  Quoting lives in the diagnostic helper only: the
printer of *answers* stays as it was, because «строка печатается без кавычек» is a
documented property of the dialect, not an oversight.

The predicate is named the way the program spelled it.  `Solver` sets the spelling on
the engine for the duration of the call (`Engine::setCallingName`) and restores it
afterwards, including when the built-in throws; a built-in called directly — by a
test, or by another built-in's helper — finds the field empty and falls back to the
Russian name it passes itself.

**Consequences.**  `аргумент 1 — строка "abacb", нужно список` and `msort:
Недопустимый тип аргументов` are what a reader sees now.  The echo of the whole call
was rejected: it repeats «аргумент 1», drags an unrelated variable into the line and
grows without bound.  The «ожидался … найден …» order was rejected because Russian
agreement would need a gender table where the impersonal «нужно» needs none.

**Status.** Accepted.

## ADR-074: `1` and `1.0` are one number in the term order, and the manual says so

**Context.**  Part 262 checked the standard-order section (§5.9) the same way part 261
checked the «Отличие от ISO» boxes — by running it in `gprolog` and `swipl`.  The
heading promised the ISO order and the table kept it, except for one row: «число — по
значению; `1` и `1.0` — одно число».  Both implementations disagree: they order
*floats before integers*, so `1.0 @< 1` is true, `1 @< 1.0` is false,
`compare(>, 1, 1.0)` succeeds, `sort([1,1.0], S)` gives `S = [1.0,1]` and
`msort([1,1.0], S)` the same.  GNU Prolog's manual lists the order as «floating point
numbers, in numeric order; integers, in numeric order; atoms …» and calls the order
system-dependent only for variables, so the difference is real on both sides, not an
SWI quirk.

**Decision.**  The behaviour stays.  Numbers are compared by value here, the two
spellings of one value are equal in the term order, and `МНОЖЕСТВО([1,1.0], С)` gives
`С=[1]` — which is what the owner asked for when the sorts were separated (part 259)
and what §3.7 and `examples/sort.pld` already show.  A second `#warn` box in §5.9
states the difference, because a reader arriving from SWI would otherwise read the
`С=[1]` example as a bug: `1.0 @< 1` is false here, `СРАВНЕНИЕ(Порядок, 1, 1.0)` is
`=`, and `СОРТИРОВКА` keeps the pair in the order it was given.

**Consequences.**  `МНОЖЕСТВО` really is a set of *values*: `1` and `1.0` collapse.
§5.9 now carries two boxes side by side — the merged numbers and the separate string
kind — so the section's promise of the ISO order holds for the kinds and their order
and names its two exceptions instead of implying there are none.

**Status.** Accepted.

## ADR-075: `atan` and `atan2` are functions of the expression, and `atan2` brings a two-argument call

**Context.**  Part 262 wrote down that the function names inside an expression are
ISO's, with `tan` as the single exception: ISO has `atan`, `tan` is what the
implementations added.  The owner read that line and asked «Сделаем atan у нас?» —
the dialect had no arc tangent in expression form at all, and `atan2`, ISO's
two-argument arc tangent, was absent in every form.  A quarter of a circle could be
named only by the predicate `TAN(X, Y)` with `Y` bound, which answers `atan` and
nothing else.

**Decision.**  Both go in as *functions*: `atan(X)` and `atan2(Y, X)`, the arguments
in ISO's order — the ordinate first, so `atan2(1, -1)` is 3π/4 and not -π/4.
Neither gets a predicate.  The owner chose that: the inverse of `atan` is already
`TAN(X, Y)` with `Y` known, and `LOG/2` is the precedent for a function that has no
predicate at all (§5.6 says so in as many words).  An `ATAN/2` would be a third
spelling of the same two counts, and `ATAN2/3` would be an API of our own invention.

`atan2` is the only two-argument function of ISO, and the expression grammar knew
none: a name followed by `(` was a one-argument call, and everything with two
arguments was an operator.  The parser therefore grew one branch
(`isTwoArgumentFunctionName` + the comma inside the call), and `evaluateBinary` — the
place two arguments already reach — grew the case.  The comma of `atan2(1, 2)` is
read inside the call and never escapes: `?X is atan(1), Y is 2.` is still two goals.

**Consequences.**  All twelve names of ISO's arithmetic are here now, `tan` still
being the one the standard lacks.  `atan2(1)` is a parse error that says it wants
two arguments, and bare `atan` used as a goal gets the existing warning
«пишется в арифметическом выражении, а не в цели».  `--list-keywords` prints 184
lines, and `doc/builtins.json` holds two more records of kind `function`, so the
reference panel of the window and `test_reference.py` see them.

**Status.** Accepted.

## ADR-076: `ВРЕМЯ/1` reads a monotonic clock, in seconds, from the start of the run

**Context.**  A reader of the project asked for a Prolog `clock`-like predicate: the
window shows a run's time in its «Система» tab, but a program itself had no way to
time anything, and the request named the use — comparing algorithms.  The owner
proposed `std::chrono::system_clock::now().time_since_epoch().count()`, and asked
which name is better, `ВРЕМЯ` or `ЧАСЫ`.

Two facts sank the proposal.  `time_point::duration` is implementation-defined: it
is nanoseconds with libstdc++ (this machine prints `1794147891067677269`) and
**microseconds** with libc++, which is what macOS builds link against — the same
instant would print a thousand times smaller there, and the project ships a macOS
build.  And `system_clock` is not monotonic: an NTP correction or a hand-set clock
can move it, after which a difference of two readings is wrong or negative — the one
thing a measurement must never be.

**Decision.**  `ВРЕМЯ(Секунды)` (`elapsed`) binds a real number: seconds since the
engine was created, taken from `std::chrono::steady_clock` and converted with
`duration_cast` to a fixed unit before it is divided.  `steady_clock` is the clock
the standard names for intervals, and the zero being the run's own start is what
makes the value readable — nothing in the dialect can format an epoch second into a
date, so the epoch would buy nothing and print as noise.

The name is `ВРЕМЯ`: the dialect's getters name the *quantity*, not the device
(`ВЕРСИЯ`, `ДЛИНА`, `СКОЛЬКО`, `СЛУЧ`), and `ЧАСЫ` would have made the predicate a
clock rather than a reading.  The English name is `elapsed`, not `get_time`: the
latter is SWI's and means seconds since 1970, which this is not.  `clock` was the
other candidate and was rejected because C's `clock()` is *processor* time.

**Consequences.**  A benchmark reads `?ВРЕМЯ(Т1), алгоритм, ВРЕМЯ(Т2), Д is Т2 - Т1.`
with `Д` around `0.087` for `фиб(20)` here.  The value is new at every call, like
`СЛУЧ`'s, so §13 says that a program must not expect the same reading twice — which
is also why the test asserts only what holds on any machine (the kind of the value,
that a later reading is never smaller, that a 50 ms pause is visible) and never a
number.  `Engine` carries the start reading as whole nanoseconds, so its header
stays free of `<chrono>`.

**Status.** Accepted.

## ADR-077: a package keeps `stdlib` beside the engine, not beside the window

**Context.**  A reader on macOS 26.3.1 ran the released 2.7.0 `.dmg`: the window came
up, and the welcome program failed with «Не найден импортируемый файл 'iso.pld'
(…:1:1). Искался в: /iso.pld».  The search had exactly one candidate — the working
directory — so the engine's own library was not on the list at all.  The bundle put
`stdlib` in `Contents/MacOS/`, beside the window, while the engine had moved to
`Contents/MacOS/bin/` in part 221 (the `PrologD`/`prologd` name clash); the engine looks
for `stdlib` beside *itself* and found nothing.  The `.deb` (`/opt/prologd`) and the
Windows folder have the library beside the engine and were never affected.

**Decision.**  The layout follows the engine: `Contents/MacOS/bin/stdlib`.  `doc/` and
`examples/` stay beside the window, because the *window* reads them through
`data_root()`.  The engine is not taught to look one level up: that would be a second,
undocumented rule — `stdlib` beside or above, depending on how deep the engine sits —
and every future layout would have to guess which one it means.  The rule that exists
is one sentence and both other platforms already obey it.

**Consequences.**  `paths.py` needed nothing: it mirrors the engine — `Path(interpreter)
.parent / "stdlib"` — so `F12` on `ИМПОРТ` began working with the same change.
`macos.yml` now copies the library into `bin` and runs an importing program from `/`
against the bundle on every push; `release.yml` does the same before signing, and the
program is exactly the shape of the welcome buffer (an untitled file, a working
directory of `/` on a Finder launch).  Both checks were dry-run against a simulated
bundle on Linux, where the rule is proven by the existing unit test of
`standardLibraryDirectory`.

**Status.** Accepted.

## ADR-078: `ФОРМАТ` and `ВЫВОДФ` fill `{}` from the term printer, and `std::format` is not used

**Context.**  The owner proposed `ФОРМАТ/2+(X, "Строка с {} в ней", аргументы)` and
`ВЫВОДФ/1+("Так же с {}\n", аргументы)` and asked whether it is hard, whether it is
worth it, and whether `std::format` would help.  The gap it fills is real: nothing in
the dialect turned a *value* into text.  `СЦЕП/3` refuses a number outright
(«аргумент 2 — число 5, нужно строка или атом»), and the conversions that exist
(`str_to_int`, `str_to_float`, `atom_string`) all go the other way, so «Ответ: 5» was
not expressible at all.

**Decision.**  Both predicates exist, variadic like `ВЫВОД`.  `ФОРМАТ(Результат,
Образец, Значение, ...)` binds a *string*, as `СЦЕП` does; `ВЫВОДФ(Образец,
Значение, ...)` writes the same text straight to the output.  A value is formatted by
`Engine::format` — the printer of `ВЫВОД` — so a string is spliced without quotes and a
list as `[a,b]`: one printer for answers and for the text a program builds.  `{{` and
`}}` are literal braces; a lone brace is an error, and so is a mismatch between places
and values (one message naming both numbers).

`std::format` was considered and rejected for three reasons.  Its arguments would be
Prolog *terms* we print ourselves, so every `{}` would already be a string and the
library would replace only the twenty-line scan for braces.  It would import a format
specification we do not support (`{:>10}`, `{:d}`, `{0}`) and throw `std::format_error`
where our diagnostics name the argument and the count.  And its availability divides
the three builds: libc++ gained `<format>` only in its 18 branch (there is no such
header in `release/17.x`), and on this machine `clang++ -std=c++23` cannot find it at
all while `g++` 15 can.

**Consequences.**  The manual has one subsection for the pair (§6.11, at the end of
«Ввод и вывод», so no renumbering) with pointers from `ВЫВОД` (§6.1) and `СЦЕП`
(§7.3).  The result being a string makes the goal work as a check too, which the tests
pin.  `format_string` and `format` are the English names; `format` prints, as it does
in SWI, though the place syntax differs — `{}` here, `~w` there.

**Status.** Accepted.

## ADR-079: a free number in `ПРЕДЛ/4` walks the clauses; the number stays a number

**Context.**  A reader working with graphs asked why the number in
`ПРЕДЛ(Имя, Номер, Голова, Цели)` has to be a bound integer — «нельзя, чтобы Номер
был переменной, из которой я узнавал бы, под каким номером оно лежит?» — and whether
that is architecturally hard.  It was not hard, and the refusal was an accident of the
implementation rather than a decision: the built-in read the number with
`integerValue`, so an unbound variable fell into `badArgument` and was reported as a
type error — «аргумент 2 — несвязанная переменная, нужно целое число».

**Decision.**  A free number enumerates.  `?ПРЕДЛ(ребро, Н, ребро(б, в), Ц).`
answers `Н=2`; `?ПРЕДЛ(ребро, Н, Г, Ц).` answers three times, once per clause, in text
order; `?НАЙТИВСЕ(Н, ПРЕДЛ(ребро, Н, _, _), Все)` collects `[1,2,3]`.  A bound number
behaves exactly as before, down to the type error for a number of the wrong kind and
«НЕТ» for a number outside the list.

The mechanism is the one the collector work put in (ADR-031): the built-in returns
`BuiltinResult::Yield` and walks the answers through a producer, which is what
`УДАЛЕНИЕ/1` already does for «первое подходящее, на возврате — следующее».  No new
machinery, and `ПРЕДЛ` is the third built-in to use it.

Two properties had to be chosen, and both follow the base the manual already
describes.  The walk is over a **snapshot** taken when the goal was called — the same
logical update view `УДАЛЕНИЕ/1` promises — because a walk over live positions would
renumber itself the moment an earlier answer was retracted.  And each answer
instantiates its clause afresh, so the head and the body of one answer share their
variables with each other and with nothing else.

**Consequences.**  Nothing existing changed meaning: a program that passes a number
gets what it got before.  The numbering is the one `СКОЛЬКО`, `УДАЛЕНИЕ/2` and the
bound form already use — by name, across arities — so the three cannot disagree about
what «номер 2» means.  `ПРЕДЛ` is not ISO's `clause/2`; SWI's `nth_clause/3` is the
closest relative, and it enumerates too.

**Status.** Accepted.

## ADR-080: `replace_clause` and `copy_predicate` live in the library, not in the engine

**Context.**  A reader asked for `замена(Старое, Новое)` — remove the clauses whose head
matches and insert the replacement — and the owner asked where it belongs: a library
(a knowledge-base one, or a graph one) or the engine.  The whole predicate is five
goals of the language, and only since part 270: `ПРЕДЛ` enumerating the clauses is what
makes «find the number of the clause I recognise» expressible at all.

**Decision.**  `stdlib/database.pld`: `replace_clause/2` (replace by a fact),
`replace_clause/3` (by a rule, the body as a list, as `ДОБ`/`ДОБНАЧ` take it),
`copy_predicate/2` (all clauses of a name under another name — a snapshot) and
`copy_clauses/2`, the helper the library documents as «служебный», the way `replace/5`
and `unique/3` are documented.

Three reasons the engine was not used.  The built-ins of the base are either ISO's
(`asserta`, `assertz`, `retract`, `retractall`) or readers the language cannot express
(`СКОЛЬКО`, `ПРЕДЛ`, `ТЕРМ`); `replace_clause` is neither, it composes what already
exists.  No implementation has the name — `replace_clause`, `replace`, `replace_all`
and `update_clause` are all absent from SWI 9.2.9 and GNU Prolog 1.5.0 — so a built-in
would freeze a name of our invention beside `УДАЛЕНИЕ` and look as if it had the same
standing.  And it carries a *policy* — all matching clauses or one, the old position or
the front, a fact or a rule — which a library can spell out and a built-in must fix.

**Consequences.**  No graph library.  Its useful part (`вершины/2`, `смежные/3`) is
homework in lesson 8 and in `examples/problems/maze`, and a ready-made search would
cancel the exercise.  What a graph program actually needed was one operation on the
base, and that is this file.  The library is Latin-named like the rest (`head`, `gcd`,
`replace/4` for strings — hence `replace_clause` and not `replace/2`), it is imported
with one directive, and it travels in every package unchanged.  `doc/library.typ` §8
and `stdlib/README.md` describe it; `test_stdlib.cpp` now runs it, not only checks that
it is documented.

**Status.** Accepted.

## ADR-081: the load-time name check knows what the program builds at run time

**Context.**  A reader's program copied a graph — `?copy_predicate(ребро, линия),
линия(А, Б).` — and behaved differently on the two ways of running it: `F5` was
silent, a click on the query's margin marker reported «не найдено: линия/2».  The
marker runs the buffer *quietly* (`questions=false`), and the load-time check of
`checkCallSites` then sees a goal naming a predicate that does not exist *yet*: the
query that would create it is the very statement the quiet load skipped.  A full run
hides it, because the query executes during the load, before the check.  The same
false positive was already there for `examples/database.pld`
(«не найдено: двойной/2», «не найдено: след/1») — `copy_predicate` only made it
visible in someone's own program.

**Decision.**  The check asks what the text itself hands to the base, and stays
silent about those names.  Two sources, both literal and both in the unit's own
text: a head given to `ДОБ`/`assert`, `ДОБНАЧ`/`asserta`, `ДОБКОН`/`assertz` (name
and arity), and an atom given to a predicate the unit does not define — a library
predicate may create the name it is handed, so `copy_predicate(ребро, линия)` covers
`линия/2`, at any arity, because only the library knows which arity it builds.

Everywhere else the warning stands: a mistyped name beside a created one is still
reported with its suggestion (`не найдено: следа/1; возможно, след/1`).

**Consequences.**  The two runs now agree, and the check no longer cries wolf about a
predicate the program builds itself — the whole point of the base being mutable.
The price is the arity of a handed name: `?copy_predicate(ребро, линия), линия(X)` in
a program where the copy is `линия/2` goes unreported about the arity.  Rejected
alternatives: skipping the check on a quiet load (silent about clause bodies too, the
one thing the check is good at), and running it at call time (a warning after the
answer, and dead code never checked).

**Status.** Accepted.
