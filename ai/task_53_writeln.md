# task_53 — `ВЫВОДПС` / `writeln`

**Status:** done (2026-10-03) — `ВЫВОДПС`/`writeln` is in, tested (290/290),
documented and green in the GUI.  Сдвиг номеров в разделе 6 затронул не только
руководство: `doc/builtins.json`, `doc/prologd-diff.typ` и урок 7 тоже пришлось
поправить
**Depends on:** task_51 (`ПЕРВОЕ` variadic — it turns the hardcoded variadic name
into a table of variadic names, which is exactly what a second one needs), task_11
(the I/O built-ins), task_37/task_39 (`doc/builtins.json` and the alias table)
**Milestone:** post-M10

## Goal

`ВЫВОДПС(Аргумент, ...)` writes every argument exactly as `ВЫВОД` does and then
ends the line; the English spelling is `writeln`:

```prolog
?ВЫВОДПС("Сумма: ", X).          % то же, что ?ВЫВОД("Сумма: ", X), ПС
?ВЫВОДПС("Угадали!").
?writeln("ok").
```

`ВЫВОД` and `ПС` stay as they are — the new predicate is only their combination,
the way `writeln` is `write` + `nl` in DEC-10/SWI.

## Why it is small

| Thing | Where | Note |
|---|---|---|
| the body | `builtins_io.cpp:39` `builtinWrite` | writes every argument with `engine.format(...)` and always succeeds |
| the newline | `builtinNewline` (`builtins.cpp`, the body of `ПС`) | `engine.io().newline()` |
| the name | the variadic table of task_51 | one row: `ВЫВОДПС`/`writeln` → `builtinWriteLine` |
| the alias | `kEnglishNames` in `builtins.cpp` | one row `{"ВЫВОДПС", "writeln"}`, and `test_aliases.cpp` checks it |
| the lexer | `kReservedBuiltins` in `lexer.cpp:9-40` | the reserved set is still written by hand (see `ai/conventions.md`): `"ВЫВОДПС"` beside `"ВЫВОД"`, `"writeln"` beside `"write"` |
| the data | `doc/builtins.json` | one record with `arities: []` and `variadic: true` |

**Do task_51 first.**  Without its table the word «variadic» is hardcoded in three
places (`isVariadicBuiltin`, `findBuiltin`'s `arity >= 1`, the two literal names in
`builtinNames`), and this task would have to copy that instead of adding a row.

## Decision — arity

Variadic **from arity 1**, like `ВЫВОД`/`write` and `ВЫП`/`call`: `variadic` in
this chain already means «one argument at least» (`checks.cpp`, `hasArity`), and
the zero-argument «just a newline» case is `ПС`/`nl`, which exists.  If the zero
form is ever wanted it is a second registration (`add("ВЫВОДПС", 0, builtinNewline)`),
but that would be a second spelling of `ПС`; not proposed.

## Deliverables

- [x] `builtins_io.cpp`, next to `builtinWrite`: `builtinWriteLine` — write the
      arguments, then one `newline()`, and return `BuiltinResult::Continue`
      (`builtinWrite` never fails, so the line break cannot be skipped by mistake).
      Declare it where `builtinWrite` is declared.
- [x] `builtins.cpp`: the row in the variadic table (task_51) and the alias row in
      `kEnglishNames`; refresh the comments that enumerate the variadic names.
- [x] `lexer.cpp`: both spellings into `kReservedBuiltins` (the I/O group), or the
      name lexes as a *variable* and the call is never reached —
      `test_keywords.cpp` walks `builtinNames()` and fails if a name is not
      reserved, so this is caught, but it is still part of the change.
- [x] `doc/builtins.json`: the record — `name` `ВЫВОДПС`, `aliases` `["writeln"]`,
      `kind` `predicate`, `arities` `[]`, `variadic` `true`, `group` `io`,
      `section` `6.2` (see below), a summary and variants such as
      `ВЫВОДПС(Аргумент, ...) — вывод аргументов и перевод строки` and
      `ВЫВОДПС(А, Б) — то же, что ВЫВОД(А, Б), ПС`.
- [x] `doc/help.typ`: a new **§6.2 «`ВЫВОДПС(Аргумент, ...)`»** right after §6.1
      `ВЫВОД` — one paragraph («то же самое одной целью: аргументы, как у `ВЫВОД`,
      затем `ПС`») and an example.  Then **renumber section 6** (§6.2 → §6.3 …
      §6.9 → §6.10) and update every `section` in `doc/builtins.json` that moved
      (`ПС`, `ВВКОД`, `ВВОДЦЕЛ`, `ВВОДВЕЩ`, `ВВОДСИМВ`, `ВВОДСТР`, `ЧТЕНИЕ_ИЗ`,
      `ЗАПИСЬ_В`, `ЖДИ`), because `src/gui/tests/test_reference.py` asserts that
      every `section` is a heading of the manual.  The alternative — mention
      `ВЫВОДПС` inside §6.1 and point both records at `6.1` — avoids the
      renumbering but breaks the manual's «одна запись на предикат» habit; the plan
      prefers the real subsection, and the renumbering is mechanical.
- [x] `doc/prologd-diff.typ`: one line in the I/O part — the short form did not
      exist in the original dialect.
- [x] Tests:
      * `test_builtins_io.cpp` — the arguments and exactly one line break
      (`?ВЫВОДПС("а", 1), ВЫВОД("б"), ПС.` prints `а1\nб\n`); a list, a free
      variable and a quoted atom print as they do under `ВЫВОД`; five arguments;
      `writeln` reaches the same function.
      * `test_aliases.cpp` — `ВЫВОДПС` joins the variadic skip that task_51
        generalises.
      * `test_keywords.cpp` — `ВЫВОДПС` and `writeln` are `variadic` with an empty
        arity list, and both are reserved.
      * `src/tests/CMakeLists.txt` — optionally a `ВЫВОДПС/+` expectation in the
        `--list-keywords` test, beside `ВЫВОД/+`.
      * GUI: `test_reference.py` (json ↔ interpreter ↔ manual), and
        `test_completion.py` if it should show `ВЫВОДПС/+` beside `ВЫВОД/+`.
- [x] Lessons and examples are **not** rewritten (`ВЫВОД(X), ПС` stays correct);
      optionally one `%?` line shows the short form.  **Взято:** урок 7 показывает
      `?ВЫВОДПС("Сумма: ", 5).` рядом с первой формой, а его вопросы в
      `test_queries.py` пересчитаны (19 → 20).

## What must not change

- `ВЫВОД`/`write` and `ПС`/`nl`: both keep their behaviour, arities and names.
- No protocol change: the name reaches the window through the existing `keywords`
  data (`--list-keywords` and the `ready` event) once the tables know it.
- Nothing in the solver or the checker: the predicate is a plain dispatch-table
  built-in with a variadic registration.

## Verification

1. `cmake --build build/windows-msvc --config Release` and
   `ctest --test-dir build/windows-msvc -C Release`.
2. By hand with `build\windows-msvc\src\cli\Release\prologd.exe`:
   `?ВЫВОДПС("а", 1).` prints `а1` and a line break; `?ВЫВОДПС(5).`;
   `?writeln("ок").`; `?ВЫВОДПС("без", " пробелов").`
3. `prologd --list-keywords` → `ВЫВОДПС/+` and `writeln/+`.
4. GUI suites (`PYTHONUTF8=1`, `QT_QPA_PLATFORM=offscreen`), then
   `cmake --build build/windows-msvc --config Release --target docs` and a look at
   the §6 pages (the renumbering must not leave a dangling cross-reference — check
   the §6.3…§6.10 mentions in `help.typ` and `doc/gui.typ`).

## Решения

1. **Тело — один проход, а не вызов `ПС`.**  `builtinWriteLine` повторяет цикл
   `builtinWrite` и сам вызывает `engine.io().newline()`.  Через второй вызов
   цели это стоило бы своего узла выбора и второго разрешения имени, а поведение
   `ПС` тривиально (всегда истинен).  Зато перевод строки пишется ровно один раз
   и всегда: `ВЫВОД` не может отказать, значит и пропустить его нечем.
2. **Вариадичность от единицы.**  `ВЫВОДПС` без аргументов — это `ПС`, второй
   записи для него не нужно.  Таблица task_51 говорит именно «хотя бы один»:
   `findBuiltin(имя, 0) == nullptr`, и тест это проверяет.
3. **Настоящая §6.2, а не абзац внутри §6.1.**  В руководстве одна запись на
   предикат, и `test_reference.py` требует, чтобы `section` каждой записи
   `doc/builtins.json` был заголовком руководства.  Поэтому раздел 6 поехал
   (6.2 → 6.3 … 6.9 → 6.10), а не появилась ссылка на чужой номер.
4. **Ничего не менялось ни в решателе, ни в проверках, ни в протоколе.**  Имя,
   английская пара и арность берутся из таблиц; окно получает новое имя тем же
   каналом (`--list-keywords` и `keywords` в `ready`), что и остальные.
5. **Место в руководстве выбрал пользователь: §6.3, после `ПС`, а не §6.2.**
   `ПС` — часть того же вывода, и он остался на своём номере; новая секция встала
   за ним, а дальше всё сдвинулось на один: `ВВКОД` 6.3 → 6.4 … `ЖДИ` 6.9 →
   6.10.  Итоговые номера: 6.1 `ВЫВОД`, 6.2 `ПС`, 6.3 `ВЫВОДПС`, 6.4–6.10 —
   прежние 6.3–6.9.

## Что нашёл раунд

* Таблица вариадических имён (task_51) оказалась ровно тем, ради чего её
  заводили: третий вариадический предикат — это две строки данных
  (`kVariadicNames` и `kEnglishNames`) плюс одно слово в `kReservedBuiltins`.
* Номера 6.3–6.9 жили не только в руководстве: ссылка в `doc/prologd-diff.typ`
  («таблица кодов, раздел 6.3» → 6.4), в комментариях урока 7 и в плане
  `task_54_input_stream.md`.  Все три поправлены в этом же раунде — иначе
  документы разошлись бы с руководством молча.
* `--list-keywords` вырос со 108 имён до 110.  Это единственная дорога нового
  имени в окно, и GUI-правок не потребовалось: подсветка, автодополнение и
  справка читают список оттуда.
* Тесты-удочки сработали: `test_aliases.cpp` («у каждого русского имени есть
  английское») и `test_keywords.cpp` («каждый зарегистрированный встроенный
  зарезервирован») не дают забыть ни строку в таблице пар, ни слово в лексере.

## Notes

- The name fits the family: `ВВОДСТР` is `ВВОД` + `СТР`, so `ВЫВОДПС` is `ВЫВОД` +
  `ПС` — no underscore, in the same style.
- `writeln` is the spelling a reader of ordinary Prolog expects (SWI has
  `writeln/1`), which is the point of the alias pair.
- The `ВЫВОДПС` record is the second variadic predicate in `doc/builtins.json`
  after `ВЫВОД`; it is also the second *user* of task_51's table, so it doubles as
  the check that the table really is data.
