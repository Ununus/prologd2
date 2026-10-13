# task_75 — Исполняемый файл движка: `prologd.exe` → `prologu.exe`

**Status:** done (2026-10-13)
**Depends on:** task_74 (версия 2.2.0)

## Зачем

Ветка становится ISO-совместимым движком «Пролог-У», а старый диалект будет
приезжать из оригинального `Ununus/prologd` (task_78).  Два движка рядом не могут
называться одинаково: наш — `prologu.exe`.

## Что **не** переименовываем (важно)

Инвентаризация дала 254 файла и 1281 упоминание, но там три разные вещи:

* **файл движка** — `prologd.exe` → `prologu.exe` (это и есть задача);
* **пакет окна** `prologd_gui` (импорты в двух десятках файлов) — **остаётся**:
  оболочка сохраняет имя «Пролог-Д 2.0» и свои значки `prologd2.png`/`.ico`;
* **идентичность проекта CMake** — `project(prologd VERSION …)`, опции
  `PROLOGD_BUILD_*`, переменные `PROLOGD_TEST_DATA_DIR`/`PROLOGD_STDLIB_DIR`/
  `PROLOGD_BUILD_DATE`, таргет документов `prologd_docs` — **остаются**: это имя
  репозитория, а не имя файла.  Меняем только `add_executable(prologd …)`
  (и, если нужно, `OUTPUT_NAME`).

## Шаги

1. Грепом по всем упоминаниям (не по памяти!) собрать список: `src/cli/CMakeLists.txt`,
   `src/tests/*.cmake` и `src/tests/CMakeLists.txt`, `.vscode/tasks.json`,
   `tools/build_portable.ps1`, `tools/check_dependencies.py`,
   `src/gui/prologd_gui/paths.py` (поиск движка рядом с окном),
   `src/gui/tests/test_session.py::find_executable`, `README.md`, документы.
2. Переименовать таргет и всё, что называет *файл*: `prologd.exe`.
3. Окно: искать `prologu.exe`, а `prologd.exe` — во втором режиме (task_79).
4. Пакет: в портативной раскладке рядом окажутся оба движка; имя основного —
   `prologu.exe`.
5. Документы: примеры командной строки (`prologd -s …` в `help.typ` §15, README,
   `technical.typ`).

## Проверки

`ctest` 330/330 (там `cli_version`, `cli_help` и прочие тесты, которые зовут файл по
имени); оконные проверки; `typst` — шесть документов; портативная сборка доходит до
«Ready».

## Чего остерегаться

* Слепой замены `prologd` → `prologu` по всему дереву: она переименует и пакет
  окна, и переменные CMake.  Замена — только там, где речь о *файле*.
* `ai/status.md`, `ai/decisions.md` и старые `ai/task_*.md` — это записи о прошлом:
  там имя не меняем.

## Что вышло (2026-10-13, часть 106)

Переименован **файл**, и только он: `add_executable(prologu …)` и
`install(TARGETS prologu …)`.  Пройдены все места, где зовётся *файл*:

* сборка — `src/cli/CMakeLists.txt`; `src/tests/CMakeLists.txt` (17 API-тестов,
  `if(TARGET …)`, четыре `$<TARGET_FILE:…>`);
* инструменты — `tools/build_portable.ps1` (имя в пакете и три проверки по нему),
  `tools/bench_engine.py`;
* окно — `paths.EXECUTABLE_NAME` и `paths.interpreter()`, сообщение `main.py`
  (теперь оно берёт имя из `paths`, а не повторяет строку);
* проверки окна — шесть копий списка каталогов сборки заменены вызовом
  `paths.interpreter()`: `test_session`, `test_formatter`, `test_graphics`,
  `test_keywords`, `test_variable_modes`, `protocol_smoke` (при пустом списке
  сообщение «build prologu first…» осталось, а `argv[1]` по-прежнему главнее);
* документы — `help.typ` (§15), `lessons.typ`, `library.typ`, `prologd-diff.typ`,
  `gui.typ`, четыре README и портативная памятка; примеры командной строки;
* программы — шапки «Запуск:»/«Подключение:» в двадцати `.pld` (`examples/**`,
  `stdlib/**`).

**Что нашлось по дороге.**  CMake не удаляет файл прежней цели, поэтому рядом с
`prologu.exe` в `build\windows-msvc\src\cli\Release\` остался `prologd.exe` от
08.10.  Он удалён вручную (`.exe` и `.pdb`), а `paths.interpreter()` нарочно не
берёт второе имя как запасное: старый движок лежит в любом дереве, собранном до
переименования, и окно молча запустило бы не тот файл.  Выбор движка станет явным
в задаче 79.

**Про кавычки.**  В `examples/lib/old_lib_2.pld` было `студент('Вася').` —
написано без кавычек: `студент(Вася).`, и в прозе файла сказано, почему.  Ответы
`use_old_names.pld` не изменились.

**Проверки.**  `ctest` 331/331 (= 314 случаев Catch2 + 17 CLI-тестов; в частях
103–105 стояло 330 — на один меньше, чем дают источники); `prologu.exe --version`
→ `2.2.0`; `examples\use_old_names.pld` печатает все четыре ответа из своего
файла; шесть документов собираются; `test_window` и двенадцать других оконных
проверок зелёные.  Портативный пакет **не** пересобирался: его имя и
`prologd-gui.exe` пока прежние, а соберётся он в задаче 76 — вместе со сменой
надписи версии (собран там же: `dist\prologd-2.3.0-win64`, часть 107).
