# PrologD GUI (PySide6)

The graphical front-end is a **Python/PySide6** application that drives the
`prologd` executable through a line-delimited JSON protocol.  It never links
against `prlib`:

```
  ┌──────────────────┐   requests (JSON lines, stdin)   ┌───────────────┐
  │  PySide6 GUI     │ ───────────────────────────────▶ │  prologd      │
  │  prologd_gui/    │ ◀─────────────────────────────── │  --protocol   │
  └──────────────────┘   events (JSON lines, stdout)    │  json         │
                                                        └───────────────┘
```

Keeping the interpreter in a separate process means a buggy user program, a
Ctrl+C, or a restart of the session cannot take the GUI down with it.

## Running

```powershell
# build the interpreter first
cmake --preset windows-msvc
cmake --build build/windows-msvc --config Release

python -m venv .venv
.venv\Scripts\python -m pip install -r src/gui/requirements.txt
.venv\Scripts\python src/gui/main.py --include examples/lib
```

`--exe` overrides the interpreter path (by default the newest build under
`build/` is used), `--include` adds an `ИМПОРТ` search directory and may be
repeated.

Headless check of the protocol, without PySide6 installed:

```powershell
python src/gui/tests/protocol_smoke.py
```

## Protocol contract (version 2)

One JSON object per line in both directions; the interpreter writes nothing else
to stdout.  The C++ side lives in `src/cli/protocol.cpp`, the Python side in
`prologd_gui/protocol.py`.  Version 2 added the reserved names to `ready`;
version 1 sessions are still understood by the Python client (the table is then
empty and completion falls back to the document's own predicates).

### Requests

| Request | Meaning |
|---------|---------|
| `{"cmd":"load","path":"prog.pld"}` | load a file; `ИМПОРТ` resolves against the `-I` directories |
| `{"cmd":"load","text":"…","name":"buffer"}` | load program text (the editor buffer) |
| `{"cmd":"query","text":"?цель(X)."}` | run one statement |
| `{"cmd":"input","text":"…"}` | answer the pending `input_request` |
| `{"cmd":"interrupt"}` | ask for a stop (see the note below) |
| `{"cmd":"quit"}` | end the session |

### Events

| Event | Meaning |
|-------|---------|
| `{"event":"ready","protocol":2,"version":"2.0.0","keywords":[…]}` | the session is up |
| `{"event":"output","text":"…"}` | program output (`ВЫВОД`, query results, traces) |
| `{"event":"result","found":true}` | one query finished; `found` is false when nothing matched |
| `{"event":"input_request","kind":"line"}` | `ВВОДСТР`/`ВВОДСИМВ`/`ВВКОД` waits for an answer; `kind` is `token`, `line` or `codepoint` |
| `{"event":"error","kind":"parse","message":"…"}` | diagnostic; `kind` is `parse`, `runtime` or `protocol` |
| `{"event":"bye"}` | the session is over |

Exit codes: `0` clean, `1` usage error, `2` load/parse failure, `3` runtime
failure (for example an interrupted query).

### Notes for front-ends

* **A run is a new session.**  The clause database, the `СЛУЧ` seed, the
  `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` redirection and the preloaded `$` input lines all live
  in the interpreter process, so loading a second program into a session that
  already ran one *accumulates* clauses and prints every solution twice.  Start a
  fresh process for a run — that is what **Запустить** does — and keep one session
  only for the queries that belong together.  A request written before the
  interpreter announced itself is queued by `session.py` rather than lost.
* `ready` carries `keywords`: every reserved name the lexer knows, with its kind
  (`predicate`, `operator`, `directive`) and its arities — `[]` for operators,
  directives and the variadic `ВЫВОД`, which is marked with `"variadic":true`.
  The same table is printed by `prologd --list-keywords`, one `name/arity` per
  line (`ВЫВОД/+` for the variadic one), so a front-end never keeps its own copy
  of the built-in list.  Highlighting, completion and the shortcut cheat-sheet
  all read it.

* Read the interpreter's stdout line by line and never merge it with stderr; in
  protocol mode all diagnostics travel as `error` events.
* The answer to an `input_request` is one string; embedded newlines stay inside
  that string.
* `interrupt` is handled between commands and while the interpreter waits for
  input.  A query that neither waits for input nor finishes **cannot** be
  interrupted politely — terminate the process and start a new session, which is
  what the **Остановить** button does.
* `-i`, `-o` and `-e` are refused together with `--protocol json`: the protocol
  owns stdin and stdout.

## Roadmap

* Syntax highlighting for the editor, driven by the lexer's keyword set and the
  `doc/help.typ` keyword table.
* A graphics pane fed by a `GraphicsBackend` that emits protocol events
  (`ТОЧКА`, `ЛИНИЯ`, … currently reach a null backend).
* Step-by-step execution over the `ТРАССА` stream.
* Settings persistence (interpreter path, include directories, window layout).
