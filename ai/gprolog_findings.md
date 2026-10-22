# GNU Prolog as a third engine: what was measured, and why it waits

**Status:** dropped on 2026-10-22 by the owner («Лучше сосредоточиться на нашем
2.x»).  Nothing was added to the tree; this file is the record so that the idea
does not start from a blank page if it comes back.

**Scope of the idea.** A fourth row beside `2.x ISO`, `2.x PLD` and `1.x` (ADR-029),
served by a bridge program of its own (`gnu_bridge/`), speaking our JSON protocol
(protocol 13) to the window and driving GNU Prolog behind it.  `prlib` untouched, the
bridge under its own CMake option, the file text handed to GNU Prolog as it is, its
errors passed through in English, and `--list-keywords` limited to the ISO subset we
also have.

## What is on this machine

* GNU Prolog **1.5.0**, 64-bit, installed at `F:\programs\GNU-Prolog`; its banner says
  `Compiled Jul  8 2021, 12:33:56 with cl` — the official Windows build is **MSVC**.
* The install carries the FFI: `include/gprolog.h` and `lib/libengine_pl.lib`,
  `lib/libbips_pl.lib`, `lib/liblinedit.lib`, `lib/top_level*.obj`.
* Sources of the current tree: `C:\Users\vasla\source\projects\prologd\gprolog-master`.

## Building it from source (if it is ever needed)

`src/WINDOWS` is the recipe, and it names our toolchain: *"GNU Prolog has been tested
with Microsoft Visual Studio 2026 Community (v18.2.1)"*.  The driver is **MSYS2 bash**
with the MSVC environment loaded, not CMake:

```bash
./configure --with-msvc --disable-gui-console
make
make install
```

Needs `yasm.exe` copied into `PATH` as `yasm-win64.exe` (the installed package already
has one in its `bin/`), and care with msys' `/bin/link.exe`, which shadows the MSVC
linker.  `--disable-gui-console` is the switch that removes the engine's own window.

## Measurements

1. **The process route works today** — no build, no linking:

   ```
   set LINEDIT=gui=no
   gprolog.exe --consult-file prog.pl --query-goal "Goal, write(...), nl, fail ; halt"
   ```

   `fail ; halt` enumerates every solution and exits with code 0; stdout is captured
   with `Start-Process -RedirectStandardOutput`.  Without `halt` the engine stays at
   the `| ?- ` prompt (this is what looked like a hang).  The banner (four lines) and
   the `compiling …/compiled …` lines have to be dropped, and the goal is echoed after
   `| ?- `, so the answers are what follows that line.
2. **Error positions do exist**: `file:line:column: syntax error: …` — passing errors
   through "without a position" is not necessary.
3. **`LINEDIT=gui=no`** turns the GUI console off, but that mode **hung** at the prompt
   even with stdin from `NUL`; with the GUI console and a redirected stdout the process
   finished by itself.  The window is therefore a separate question, best answered by a
   build with `--disable-gui-console`.
4. **The FFI links but does not run.**  Probe `build/gplffi/` (git-ignored) linked with
   MSVC after three fixes — `/MT` (the shipped libs use the static CRT), `ws2_32` and
   `liblinedit` — and `Pl_Start_Prolog` with `Pl_Create_Atom` works, but **the first call
   of a goal crashes**: `Pl_Query_Call(true, 0, nullptr)` → `Segmentation Violation`.
   The engine probably expects the start-up that `gplc`-generated code performs (hence
   `top_level_main.obj`/`top_level.obj` in `lib/`).  Useful entry points found in
   `gprolog.h`: `Pl_Query_Begin/Start/Next_Solution/End`, `Pl_Mk_*`, `Pl_Rd_*`,
   `Pl_Un_*`, `Pl_Writeq_To_String`, `Pl_Read_From_String`, `Pl_Err_*`.
5. **"The file text as it is" does not work for our programs.**  `examples/iso/arith.pld`
   gave **23 syntax errors**: Russian names are not atoms for an ISO lexer,
   `:- import("...")` is an unknown directive, and `?goal.` is not ISO (`?- goal.` is).
   A `GNU` row would run only programs written in Latin, never our examples or lessons.

## If the idea comes back

1. Build the engine from source (`--with-msvc --disable-gui-console`): that removes the
   window question and puts the sources of the engine next to the bridge.
2. Find out how `gplc`'s generated `main` starts the engine and make `Pl_Query_*` live
   (the probe is already there); only then is an in-process bridge worth writing.
3. If the FFI does not work within half a day, fall back to the process route above:
   markers to separate `output` from `result`, `halt` in the wrapper, the child's stdin
   separate from the protocol's, and an interrupt is a killed child.

Cheaper alternative with most of the value: no engine at all — a script that runs
`examples/iso/*.pld` through `gprolog --consult-file … --query-goal …` and compares the
`%!` lines with ours.  That is the "reference implementation" use, and it costs an
afternoon.
