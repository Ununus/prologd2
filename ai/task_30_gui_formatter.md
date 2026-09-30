# task_30 — GUI: the program formatter

**Status:** done (protocol 6, CLI `--format`, GUI `Ctrl+I`)
**Depends on:** task_21 (protocol), task_25 (documents), task_29 (settings)
**Milestone:** M11

## Goal

A **Форматировать** action with two modes, chosen in the settings, plus
formatting of the selection only:

* **soft** — the lines are built again: goals are packed up to the width and
  moved to a continuation line, indented, when they do not fit (2026-10-01, on
  request: this is what lets a hard layout come back to soft — a break the
  formatter wrote cannot be told apart from one the author made);
* **hard** — one goal of a clause body per line, continuation lines indented;
* **line** — the goals of a body share one line, whatever the width
  (2026-10-01: replaced «не менять»; the command not being pressed is «не
  менять»).

Indent is configurable (default: 1 tab stop, tabs or spaces) and trailing
whitespace is always removed.

```
Правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),
функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).
```
soft (`ширина 80`, `отступ 1 таб`) →
```
Правило(а,б,с):-функция1(а,б,с), функция2(а,б,с), функция3(а,б,с),
	функция4(а,б,с), функция5(а,б,с), функция6(а,б,с).
```
hard →
```
Правило(а,б,с):-функция1(а,б,с),
	функция2(а,б,с),
	функция3(а,б,с),
	функция4(а,б,с),
	функция5(а,б,с),
	функция6(а,б,с).
```

## Where it lives

The formatter goes into `prlib` and is reached through the CLI and the protocol;
the GUI is a client.  Laying out a clause requires knowing where the body starts
and which comma separates two *goals* rather than two arguments — that is the
grammar, and the grammar already exists once, in the parser.  A second
implementation in Python would drift.

- [x] `prlib`: `formatSource(text, FormatOptions) -> FormatResult {text,
      changed, diagnostics}`, `FormatOptions {mode: none|soft|hard, width
      (default 80 columns), indent_steps (default 1), indent_unit: tab|spaces,
      selection_only}`.  Also `source_name`, so a diagnostic names the buffer
      the text came from (the CLI the path, the window `<buffer>`).
- [x] Algorithm: lex → parse into statements with their `SourceLocation` →
      rebuild the text by inserting and removing **whitespace only**.  The bytes
      of every token are copied verbatim, so quoting, `#expr#` bodies, comments
      and Cyrillic text cannot be damaged, and nothing is re-printed from the
      AST.  (The statement structure comes from the token stream — statement
      ends at a `depth 0` dot, body separators at `depth 0` commas inside the
      body, `#…#` tracked as a toggle — and the parse is what decides whether
      the text may be touched at all.)
- [x] **Trailing whitespace never survives**: the reference examples above were
      written with a space after the final comma and the formatted text has
      none.
- [x] **Idempotence**: `format(format(x)) == format(x)`, enforced by a property
      test over `examples/*.pld` (every `.pld` under `examples/`, both modes).
- [x] **Semantics preserved**: the formatted program must produce the same
      output as the original for every example (golden test — `cli_format.cmake`
      runs both and compares; the Catch2 suite keeps the byte-exact shapes).
- [x] Comments: a trailing `% …` stays on its goal's line, a comment on its own
      line stays on its own line (indented with the continuation indent inside a
      body), and a comment is never moved across a goal boundary.
- [x] Empty lines: at most one blank line *between* clauses; blank lines inside
      a clause are kept (the reference implementation deleted them — see below).
- [x] Input that does not parse: return the text unchanged with the diagnostics,
      so the GUI can report "не удалось разобрать" and mark the line instead of
      mangling the buffer (the window does exactly that; the CLI exits 2).
- [x] Selection mode: the selected fragment is parsed as a statement sequence;
      a partial clause (the caret is in the middle of a body) is formatted up to
      its last complete goal and the remainder is left alone (the cut is the
      last top-level separator whose prefix parses with a dot).
- [x] CLI: `prologd --format[=soft|hard] [--format-width N] [--format-indent N]
      [--format-unit tab|spaces] [-s FILE]` → formatted text on stdout, exit 0;
      exit 2 with the usual diagnostic when the source does not parse.  No `-o`
      needed, so it composes with the shell; no files means stdin.
- [x] Protocol **6**: `{"cmd":"format",…}` → `{"event":"formatted","text":…}`
      or `error` events of kind `format`; the request is answerable between
      queries (it does not need the engine) and leaves the exit code alone — the
      request failed, the session did not.
- [x] GUI: `prologd_gui/formatter.py` (Qt-free client — the position mapping),
      the action **Форматировать** `Ctrl+I` with a mode menu on the toolbar
      («не менять»/«мягкое»/«жёсткое» and «только выделенное»; the same settings
      keys task_29's dialog will edit), a context-menu entry; the replacement is
      one undo step, the caret and the selection survive it, and the cursor does
      not jump to the top of the document.

## Why the reference implementation is a reference, not a source

`ai/_ref/prolog/src/gui/Editor.cpp:508 formatDocument()` (see also
`canBeFunction` at the top of the same file) is a hand-rolled character state
machine over the plain text:

* `canBeFunction` decides "a call starts here" by scanning for the first
  `:`, `.`, `,` or `;` at parenthesis depth 0 — a guess, not a parse;
* it mutates the string it is scanning (`str.insert`) and compensates with
  hand-written index arithmetic (`st += 2`), which is where the corner cases
  live;
* it deletes blank lines inside a clause (`str_list.erase(...)`), so formatting
  destroys the author's grouping and is **not idempotent**;
* it always breaks after a comma, so there is no мягкое mode at all;
* it reformats the whole document — no selection mode;
* it recognises `:-`/`<-` but nothing else about the statement structure.

Keep it as a reference for the *intent* (the two target shapes above) and for
the colour conventions elsewhere; do not port it.

## Tests

- [x] Catch2 golden tests for both examples above, byte-exact (this is the
      acceptance criterion the user actually wrote down — with the head spelled
      `правило`: a capital initial is a *variable* in this dialect, so the task's
      `Правило` would not parse; the columns are the same).
- [x] Catch2: trailing comment kept, comment-only line kept, `#1+2#` untouched,
      quoted atoms untouched, a one-goal clause unchanged, `;` terminator,
      `<-` rule, unparsable input returned unchanged, idempotence.
- [x] CTest: `prologd --format=hard -s examples/*.pld` output re-parses, and
      running the formatted file yields the same output as the original
      (`src/tests/cli_format.cmake`: both modes × a plain example and a lesson,
      plus a broken source that must exit 2 and write nothing to stdout).
- [x] Python: `src/gui/tests/test_formatter.py` (Qt-free) against the built
      interpreter — request/response shape, the settings on the wire, the
      selection cut, an error case and the caret mapping.

## Decisions (from the user, 2026-09-29)

* Trailing whitespace is removed — no space after the last comma on a line.
* Continuation indent defaults to **one tab** (was two in the examples above);
  the unit and the count stay configurable.
* The soft width is **80 columns**.  With 80 the built-in example splits exactly
  as drawn: goals 1–3 end at column 66 and goal 4 would reach 83, so the break
  falls before goal 4.
* Tab size for the *display* of a tab is the editor's tab-width setting
  (task_29) — the formatter emits one tab, the editor decides how wide it looks.

## Acceptance

**Форматировать** turns either example into the shape above, the same action on
an already formatted document changes nothing, formatting a selection behaves
like formatting that fragment alone, a broken program is reported instead of
rewritten, and the formatted `examples/` still pass their golden tests.

## What was built (notes for the next session)

* The formatter is `prlib/formatter.{hpp,cpp}`; the wire is protocol 6 and the
  CLI gained `--format`, `--format-width`, `--format-indent`, `--format-unit`
  (a query of its own: it prints and exits, like `--list-keywords`).
* The statement structure is taken from the *token stream* (the lexer's output):
  the parse is the permission, the tokens are the map.  Offsets come from the
  token `SourceLocation`s (line/column, columns count bytes) and a line table.
* Canonical spacing the formatter writes: clause `голова:-тело` (glued), a
  directive `:- цель.` (one space), a query `?цель.` (glued), goal separator
  `, ` and ` ; `, and no space before the final dot.
* 2026-10-01, follow-up round: the mode control moved from the toolbar into
  «Правка → Формат», «не менять» became «в одну строку», and the soft mode turned
  canonical so that hard → soft works; the wire went to protocol **7** (`format`
  takes `line` instead of `none`).
* `FormatOptions::indent_unit == Spaces` means **four** spaces per step.
* Selection formatting drops the fragment's own parse errors when it found a
  parsable cut: they are about the part that is deliberately left alone, and a
  front-end must not report «не удалось разобрать» for a cut it just handled.
* The window's mapping (old offsets → new) is `prologd_gui/formatter.py`, and the
  mode control sits on the toolbar until task_29's dialog owns the settings keys.
* `FormatMode::None` is accepted on the wire (the settings may say «не менять»),
  and the window says so in the status bar instead of sending anything.
