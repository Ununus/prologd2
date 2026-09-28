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
.venv\Scripts\python.exe src/gui/main.py --include examples/lib
```

`--exe` overrides the interpreter path (by default the newest build under
`build/` is used), `--include` adds an `ИМПОРТ` search directory and may be
repeated.

Activating the environment is optional: calling `.venv\Scripts\python.exe`
directly needs no `Set-ExecutionPolicy` and makes it obvious which interpreter is
meant.

`--theme light|system` chooses the appearance.  **`light` is the default and is
forced** through the Fusion style with an explicit palette, because Qt 6 follows
the Windows dark theme and the syntax colours are chosen for a *white*
background — on a dark one they are unreadable.  `system` keeps the platform
choice: what a light desktop wants, and the hook for a real dark theme, which
needs its own syntax palette rather than just this switch (task_29).

`--settings FILE` chooses the settings file; by default it is
`%LOCALAPPDATA%\PrologD\gui\gui.ini`, holding the font family and size, line
numbers, the indent character and width, completion and its threshold, and the
theme.  A value that cannot be
read falls back to the default instead of refusing to start, and keys this
version does not know are left alone (task_29 adds the dialog).

## Editor keys

| Key | Command |
| --- | --- |
| `F5`, `Ctrl+R` | **Запустить** — a run in a fresh interpreter |
| `Shift+F5`, `Ctrl+.` | **Остановить** |
| `Ctrl+O` | **Открыть…** — fills the editor and does not run |
| `Ctrl+L` | clear the output pane |
| `Ctrl+K` / `Ctrl+U` | comment / uncomment the selection or the current line |
| `Ctrl+Space` | completion popup — it also opens by itself after two letters |
| `Enter` / `Tab` / `Esc` | take the highlighted completion / close the popup |
| `Ctrl`+wheel, `Ctrl+0` | font size (6…72 pt) and its reset |
| `Tab` / `Shift+Tab` | indent / outdent the selected lines |
| `Enter` | continues the indent after `,`, `:-` or `<-` |

Neither list is final: the menu bar and the toolbar icons are task_26, the rest
of the combinations task_31.  Zoom deliberately has no key pair of its own —
`Ctrl+=`, `Ctrl++` and `Ctrl+-` will insert a `РАВНО(…)`, `СЛОЖЕНИЕ(…)` or
`ВЫЧИТАНИЕ(…)` skeleton there.

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
* **`result` carries no text.**  The answer is printed by the interpreter itself
  (`ДА`, `НЕТ`, or `X=1` lines) and arrives as `output`; `result` only says the
  query is over, with `found` telling whether anything matched.  A front-end that
  appends its own `НЕТ` for `found == false` prints the answer twice — which
  looks like a bug in the user's program.  The window keeps it for the status
  bar only.
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

* A graphics pane fed by a `GraphicsBackend` that emits protocol events
  (`ТОЧКА`, `ЛИНИЯ`, … currently reach a null backend).
* Step-by-step execution over the `ТРАССА` stream.
* Settings persistence: the file and the editor's values exist; the dialog and
  the rest of the list (interpreter path, include directories, window layout)
  are task_29.
