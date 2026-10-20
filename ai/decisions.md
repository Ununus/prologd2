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
