# task_37 — GUI: a built-in reference without leaving the editor

**Status:** not started
**Depends on:** task_23 (the reserved names from `ready`, one source for the
list), task_24 (the completion popup), task_26 (the action table, where the new
command is declared)
**Milestone:** M13
**Note:** the English-alias idea in `ai/maybe/english_aliases.md` is *not* a
dependency, but if it is ever scheduled, the aliases belong in the same data file
this task introduces (one record per predicate, an `aliases` list), otherwise the
reference would grow a second copy of every entry.

## Goal

Answer «what does `КОПИЯ` do?» in the window where the question is asked.  The
user's own words: «на память бывает трудно вспомнить что делает та или иная
функция (пр. `КОПИЯ`), а специально открывать отдельный файл для быстрой справки
— трудозатратно».  Today the GUI can open a built PDF (`window.py`'s
`_open_document`), which is the "open a separate file" the user is complaining
about: the reader loses the caret, the page and the window.

`doc/help.typ` already holds the answer in the shape the GUI needs — one
subsection per predicate with its argument modes listed one per line:

```
== 7.4. `КОПИЯ(S, Позиция, Длина, Подстрока)`

- `КОПИЯ(с, ц1, ц2, П)` --- `П` --- подстрока длины `|ц2|` с позиции `ц1`;
- `КОПИЯ(с, ц1, П, с4)` --- `П` --- длина вхождения, начинающегося в позиции `ц1`;
…
```

So the work is not writing documentation: it is giving that documentation a
**machine-readable form** and showing it where it is needed.

## Deliverables

- [ ] **One source of data: `doc/builtins.json`.**  One record per reserved name
      — the full list is every name `prologd --list-keywords` prints (60
      registrations in `src/prlib/src/builtins.cpp:248-321`, ~57 names, plus
      `mod`, `div`, `ИМПОРТ`, `ВЫП`).  Fields:
      `name`, `kind` (`predicate`/`operator`/`directive`, the same spelling the
      protocol uses), `arities`, `variadic`, `group` (`control`, `arith`,
      `strings`, `io`, `database`, `graphics`, `modules`), `summary` (one
      Russian line), `variants` (the argument modes, one per line, each a
      complete call form), `section` (the `doc/help.typ` heading it comes from,
      e.g. `7.4`).
      Shape:

      ```json
      {
        "name": "КОПИЯ",
        "kind": "predicate",
        "arities": [4],
        "group": "strings",
        "section": "7.4",
        "summary": "Подстрока и поиск: берёт часть строки, проверяет её или находит вхождение",
        "variants": [
          "КОПИЯ(с, ц1, ц2, П) — П = подстрока длины |ц2| с позиции ц1",
          "КОПИЯ(с, п, р, с4) — П = позиция вхождения, Р = его длина"
        ]
      }
      ```

- [ ] **`doc/help.typ` builds its compact list from the same file** (`json()` is
      part of Typst): the per-predicate prose stays hand-written, but the summary
      table and the «варианты» lines come from the JSON, so a predicate cannot be
      described in two places with two different meanings.  If that turns out
      awkward in Typst, the fallback is to keep `help.typ` as it is and let the
      checker below be the only guarantee that the two agree.
- [ ] **A checker that keeps the two in step** — `src/gui/tests/test_reference.py`,
      Qt-free, and the reason this task is worth doing at all:
  * every name from `prologd --list-keywords` has a record and no record is
    unknown (the exe is found the way the other CLI checks find it);
  * every `section` exists as a heading in `doc/help.typ`;
  * every `variant` starts with the predicate's own name;
  * `summary` is non-empty and does not end in a period (matching the style of
    the diagnostics);
  * the arities in the JSON equal the arities the interpreter reports.
- [ ] `src/gui/prologd_gui/reference.py`, Qt-free: loads the JSON from
      `doc/builtins.json` (found the way `window.py` already finds `doc/*.pdf`,
      `parents[3] / "doc"`), indexes it by name, and answers
      `record(name)`, `summary(name)`, `variants(name)`.  A missing or broken
      file must degrade to "no descriptions", never to a failed start-up — the
      GUI has to work in a checkout where `doc/` was not copied.
- [ ] **In the popup:** a detail label under the completion list, updated from
      `QCompleter.highlighted`, showing `НАЙТИВСЁ/3 — собирает все решения цели в
      список` and, if there is room, the first variant line.  Qt's completer has
      no second row, so this is a frameless `QLabel` positioned under
      `completer.popup()` and hidden when the popup closes; it must not take
      focus and must not move the caret (the popup's own trap from task_24).
- [ ] **On demand:** a new action «Справка по предикату» in `actions.py`
      (`Shift+F1`; `F1` is free today but is the conventional help key, so both
      may open it — decide with the user) that shows the record of the word under
      the caret: summary, every variant, and the `help.typ` section number.
      A small non-modal panel is preferable to a modal box — a modal window
      cannot be driven from a headless test (the lesson repeated in
      `buffers.py` about `_ask_save`).
- [ ] Tests: `test_reference.py` as above, plus additions to
      `test_completion.py` (the label follows the highlighted row, disappears when
      the popup closes, and says nothing for a word with no record),
      `test_window.py` (`Shift+F1` on `КОПИЯ` shows the five `variants` lines of
      §7.4 and the section number; on an unknown word it shows nothing or says so)
      and, if the label is a new widget, `test_appearance.py` for its colours.
- [ ] Docs: `doc/gui.typ` (section: «справка по предикату» — the popup label and
      `Shift+F1`), `doc/README.md` (that `builtins.json` is data for the GUI and
      for `help.typ`, not a document, so the `docs` target does not build it),
      `src/gui/README.md` (the module and where the file is expected).
- [ ] `ai/conventions.md` gains one line: a new built-in is added to
      `builtins.cpp`, to the lexer's reserved set, **and** to `doc/builtins.json`
      — the checker will fail otherwise, which is the point.

## Acceptance criteria

1. Typing `копи` in the editor shows `КОПИЯ/4` in the popup and its summary under
   it, without opening anything else.
2. `Shift+F1` with the caret on `КОПИЯ` lists all five argument modes of §7.4 and
   names the section, so the PDF is one click away but not required.
3. With `doc/builtins.json` deleted, the window starts and works: the popup shows
   names and arities exactly as today, and no description appears.  No exception,
   no empty popup.
4. `test_reference.py` fails if a predicate is added to the interpreter without a
   record, and if a record names a section that `help.typ` does not have.
5. The whole suite stays green (`ctest`, and the headless GUI scripts).

## Risks and notes

* **Drift is the whole risk.**  The JSON is a second copy of knowledge that lives
  in `help.typ`; the checker (name set, section existence, arity equality) is
  what makes the copy safe.  Skipping the checker turns this task into a future
  defect.
* Writing the 57 summaries and their variants is the bulk of the work (2–4 hours
  of careful rewriting from `help.typ`), and it is worth doing in the same pass as
  the JSON — a half-filled file is worse than none, because the checker then has
  to be weakened.
* The popup label must not make the completion list jump (a label that appears
  under the popup moves nothing, but a label *inside* a custom view would change
  the popup's size on every keystroke).
* Out of scope: an embedded copy of the whole user manual, F1 opening `help.pdf`
  at the right page (PDF has no anchors in the general case), and translating the
  summaries into English (the GUI is Russian, like `doc/*.typ`).
