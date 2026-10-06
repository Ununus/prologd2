"""Persisted preferences, and the description the dialog is built from.

`Settings` is the store: typed properties for what the window reads, one key at
 a time, in an ini file (`%LOCALAPPDATA%\\PrologD\\gui\\ini`, or `--settings
FILE`).  `SETTINGS` is the *list* of what the user may change: label, section,
kind, default and bounds — the dialog builds a row from each record and
«Сбросить» writes those defaults back, so a value cannot be editable without
being stored, or stored without being documented.

Three promises hold for a hand-edited or foreign file:

* a value that cannot be read (a string where a number used to be) falls back to
  the default instead of taking the window down with it;
* a number outside its bounds is clamped, never rejected;
* a key this version does not know is **preserved** — an ini written by a newer
  build must survive a round through this one, which is why values are written
  one key at a time rather than by replacing the file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

from . import theme

ORGANIZATION = "PrologD"
APPLICATION = "gui"

FONT_FAMILY = "editor/font_family"
FONT_SIZE = "editor/font_size"
LINE_NUMBERS = "editor/line_numbers"
WRAP = "editor/wrap"
INDENT_CHARACTER = "editor/indent_character"
INDENT_WIDTH = "editor/indent_width"
COMPLETION = "editor/completion"
AUTO_COMPLETE_AFTER = "editor/auto_complete_after"
THEME = "view/theme"
RECENT_FILES = "files/recent"
LAST_DIRECTORY = "files/last_directory"
SPLIT_EDITOR = "view/split"
SPLIT_SIZES = "view/split_sizes"
RESTORE_SPLIT = "view/restore_split"
#: The graphics window (task_45): whether it was open, and where it stood.  Both
#: are records the *window* keeps rather than choices in the dialog — the same
#: kind of thing as the split sizes, and the reason they are listed in
#: `MACHINE_KEYS`.
GRAPHICS_VISIBLE = "view/graphics_visible"
GRAPHICS_GEOMETRY = "view/graphics_geometry"
#: Where the *main* window stood (task_49).  The graphics window remembered its
#: own since task_45 and the main window — the one the user moves first — did not,
#: which is what the user ran into.  A machine key for the same reason: it is a
#: record the window keeps, not a choice in the dialog.
WINDOW_GEOMETRY = "view/window_geometry"
TOOLBAR = "view/toolbar"
OUTPUT_POSITION = "view/output_position"
OUTPUT_VISIBLE = "view/output_visible"
#: The goal field under the editor — and the console that appears under *it*
#: (part 92).  One key for the two: an answer box under nothing would be a puzzle.
QUERY_VISIBLE = "view/query_visible"
PANEL_SIZES = "view/panel_sizes"
SAVE_BEFORE_RUN = "execution/save_before_run"
FORMAT_MODE = "format/mode"
FORMAT_WIDTH = "format/width"
FORMAT_INDENT = "format/indent"
FORMAT_UNIT = "format/unit"
FORMAT_SELECTION = "format/selection"
#: The `Ctrl`+key insertions (task_31), as the JSON the window parses.  Kept as
#: a string rather than a parsed table: a file a human edited may hold nonsense,
#: and turning nonsense into the built-in table is `Shortcuts.from_json`'s job.
SHORTCUTS_TABLE = "shortcuts/table"
#: The syntax colours the user changed (task_50): a JSON object `field: "#rrggbb"`
#: per theme, holding only the fields that differ from the shipped palette.  Two
#: keys, one per *actual* palette — the `system` theme resolves to one of them,
#: so its override follows whichever page the desktop chose.
SYNTAX_LIGHT = "syntax/light"
SYNTAX_DARK = "syntax/dark"
#: The output panel has a size of its own since task_29: a log is read at a
#: different distance from the program, and the two used to share one number.
OUTPUT_FONT_SIZE = "output/font_size"
OUTPUT_LINE_LIMIT = "output/line_limit"
#: Whether «най» offers `НАЙТИВСЕ` (off) or only `найти` (on) — task_24's model
#: has both, the switch is new (task_29).
COMPLETION_MATCH_CASE = "editor/completion_match_case"
#: The pale band behind the line the caret is on.
CURRENT_LINE = "editor/current_line"
#: A new line continues the indentation of the one above it (task_29's switch
#: over what used to be the editor's only behaviour).
AUTO_INDENT = "editor/auto_indent"
#: Minutes between two automatic saves of *named* buffers; 0 is off.
AUTOSAVE_MINUTES = "files/autosave_minutes"
RECENT_LIMIT = "files/recent_limit"
#: Reopen the tabs of the previous run (task_29): the switch the user sets…
RESTORE_TABS = "files/restore_tabs"
#: …and the session itself, which the window writes on the way out: the tabs in
#: bar order (`documents.encode_tabs`) and which one was showing.
SESSION_TABS = "session/tabs"
SESSION_CURRENT = "session/current"
#: Whether the output pane scrolls to the end as lines arrive.  It stops
#: following by itself when the user scrolls up; this switch is the other way —
#: «не уводите взгляд с того, что я читаю».
FOLLOW_OUTPUT = "view/follow_output"
#: Where the program's own input questions are answered (task_27 has both ways):
#: in the console field under the output, or in a modal box per question.
INPUT_MODE = "view/input_mode"
#: The folders `ИМПОРТ` searches, in the order the engine tries them (task_29;
#: task_46 folded the single «Рабочая папка» row into this list in 2026-10-02 —
#: one list instead of a folder plus a list).
IMPORT_PATHS = "execution/import_paths"
#: Whether a run also answers the program's own `?`-statements — the `questions`
#: flag of `load` (protocol 5).  Off, a lesson is loaded as rules only, which is
#: what a lecture wants; the margin's own marker click always answers its one
#: question, whatever this says.
RUN_QUESTIONS = "execution/run_questions"
#: Whether a run question echoes itself (`?цель.`) before its answer — the
#: `printQuestions` flag of `load` (protocol 11, task_46: the old `questions` was
#: split into *run* and *print*).
PRINT_QUESTIONS = "execution/print_questions"
#: Whether the answer of a *single* goal is shown as a table in the «Таблица» tab
#: as well (task_59): columns are the goal's variables, rows are the solutions.
#: The text in «Выводе» does not change — the table is an addition, and it is
#: built for a margin marker or a goal typed into the query line, never for a
#: whole run: the answers of several questions cannot be told apart in the text
#: (`answers.py`).
ANSWER_TABLE = "execution/answer_table"
#: The guards of a run (task_46), sent with every `load` (protocol 9).  `0` means
#: «без предела» for all of them.  The engine has no limits of its own and its
#: message names a limit and its value only, so the answer to «where do I raise
#: it» is the window's: `window._limits_note` prints the rows of a run before it
#: starts, in the words of the dialog.
MAX_STEPS = "execution/max_steps"
MAX_DEPTH = "execution/max_depth"
MAX_FINDALL = "execution/max_findall"
#: The wall-clock timeout in milliseconds; `0` is off.  Checked by the *window*,
#: not by the engine: it is a property of the run, and the front-end already owns
#: the polite-stop machinery (`interrupt`), which also keeps a clock out of the
#: solver's hot loop.
TIMEOUT_MILLISECONDS = "execution/timeout_milliseconds"
#: How many output events (a line of the program's text, a drawing primitive, a
#: trace line) one run may produce; `0` is off.  Like the timeout it is the
#: window's own guard, not the engine's — the solver has no idea how much it has
#: printed — and the answer to a flood is the same escalation: the request, then
#: the process.
MAX_OUTPUT_EVENTS = "execution/max_output_events"
#: Which `prologd` the window runs (task_46).  Empty means «the one the window
#: was started with» — `--exe`, itself auto-detected when left out.  A row that
#: names another build takes effect at the next session start, and the status
#: bar says which one is in use.
INTERPRETER = "execution/interpreter"
#: Where the *process* starts (task_46): `ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ` and the other
#: relative paths open from this folder.  Three answers: the running file's
#: folder, the window's own folder, or a fixed one (`PROCESS_DIRECTORY_PATH`).
#: Not the `-I` search folders of «Дополнительные каталоги ИМПОРТ» — those are
#: *search* directories for the import; this one is the working directory of the
#: child process.
PROCESS_DIRECTORY = "execution/process_directory"
PROCESS_DIRECTORY_PATH = "execution/process_directory_path"

DEFAULT_FONT_FAMILY = "Cascadia Mono"
DEFAULT_FONT_SIZE = 11.0
DEFAULT_THEME = "light"

#: Where the output panel sits: to the right of the editor or under it.  `Ctrl+F4`
#: moves it, `F4` hides it.  The bottom is the default (task_50): a log is read
#: across the full width, and the editor keeps its tall column for the program.
DEFAULT_OUTPUT_POSITION = "bottom"
OUTPUT_POSITIONS = ("right", "bottom")

#: How the program's input questions are answered: in the console under the
#: output pane (the field is then the first thing looked at, and the modal box is
#: the answer only when that panel is hidden) or in a box per question.
DEFAULT_INPUT_MODE = "panel"
INPUT_MODES = ("panel", "dialog")

#: How a file's names are read *when the file does not say* (task_67).  The old
#: Пролог-Д wrote a variable as one letter and left a string constant unquoted,
#: which mode 0 reads as a variable, so an old program means something else there.
#: A file whose first line declares `:- ИМЕНА(N).` is read that way whatever this
#: row says — the dialect belongs to the file — and an imported file is read in its
#: own mode, too.  So this is a fallback, and the fallback is the modern reading.
VARIABLE_MODE = "execution/variable_mode"
VARIABLE_MODES = ("0", "1", "2")

#: The screen the graphics predicates draw on (task_73).  The engine's own default
#: is the same 600 × 600 (`kMaxGrX`/`kMaxGrY`): the whole buffer travels to the
#: window in a snapshot and ЗАКРАСКА walks it cell by cell, so the picture is as
#: big as it needs to be and no bigger.  A lesson that wants the old screen asks
#: for 1024 × 768 in these two rows.
SCREEN_WIDTH = "execution/screen_width"
SCREEN_HEIGHT = "execution/screen_height"
DEFAULT_SCREEN_SIZE = 600
MINIMUM_SCREEN_SIZE = 16
MAXIMUM_SCREEN_SIZE = 2048

MINIMUM_FONT_SIZE = 6.0
MAXIMUM_FONT_SIZE = 72.0

#: How many characters are typed before the popup appears by itself.
DEFAULT_AUTO_COMPLETE_AFTER = 2
MINIMUM_AUTO_COMPLETE_AFTER = 1
MAXIMUM_AUTO_COMPLETE_AFTER = 10

#: The formatter (task_30): the three shapes the mode control offers — «в одну
#: строку», «мягкое» (цели собираются до ширины) и «жёсткое» (голова одна, по цели
#: на строку).  «Не менять» ушёл: ненажатая команда и есть «не менять», а из
#: жёсткого обратно в мягкое теперь можно — мягкое строит строки заново.  Меню
#: этого значения стояло в «Правке» с task_30 и вернулось на панель инструментов
#: в task_47, кнопкой сразу после «Форматировать».
DEFAULT_FORMAT_MODE = "soft"
FORMAT_MODES = ("line", "soft", "hard")
DEFAULT_FORMAT_WIDTH = 80
MINIMUM_FORMAT_WIDTH = 20
MAXIMUM_FORMAT_WIDTH = 1000
DEFAULT_FORMAT_INDENT = 1
MINIMUM_FORMAT_INDENT = 1
MAXIMUM_FORMAT_INDENT = 8
DEFAULT_FORMAT_UNIT = "tab"
FORMAT_UNITS = ("tab", "spaces")

#: task_29.  The output starts at the editor's size, so an old file (and a fresh
#: one) behaves as it did; the two only differ once the user splits them.
DEFAULT_OUTPUT_FONT_SIZE = DEFAULT_FONT_SIZE
DEFAULT_OUTPUT_LINE_LIMIT = 50_000
MINIMUM_OUTPUT_LINE_LIMIT = 100
MAXIMUM_OUTPUT_LINE_LIMIT = 500_000

#: 0 is off.  An interval rather than «перед запуском»: that switch is
#: `save_before_run`, and it is a different promise (this one saves work the user
#: has not run at all).
DEFAULT_AUTOSAVE_MINUTES = 0
MAXIMUM_AUTOSAVE_MINUTES = 120

DEFAULT_RECENT_LIMIT = 10
MAXIMUM_RECENT_LIMIT = 50

#: task_46's limits.  The engine's own defaults are «без предела», and the window
#: ships numbers a lesson program cannot notice but a runaway cannot outlive: no
#: step cap, a million frames of recursion, a million solutions per НАЙТИВСЕ and
#: no clock.  Depth is the one that matters by default — without a cap a runaway
#: recursion is stopped by nothing at all, while a million frames is deep enough
#: that no honest program reaches it.
DEFAULT_MAX_STEPS = 0
MAXIMUM_MAX_STEPS = 1_000_000_000
DEFAULT_MAX_DEPTH = 1_000_000
MAXIMUM_MAX_DEPTH = 10_000_000
DEFAULT_MAX_FINDALL = 1_000_000
MAXIMUM_MAX_FINDALL = 100_000_000
DEFAULT_TIMEOUT_MILLISECONDS = 0
MAXIMUM_TIMEOUT_MILLISECONDS = 3_600_000
#: The output cap ships *on*: fifty thousand events is more than any lesson prints
#: or draws, and much less than a runaway produces — the window handles about
#: twenty thousand a second, so the cap fires on a runaway in a couple of seconds.
#: A program that needs more raises the row in the dialog; `0` still means
#: «без предела».
DEFAULT_MAX_OUTPUT_EVENTS = 50_000
DEFAULT_VARIABLE_MODE = "0"
MAXIMUM_MAX_OUTPUT_EVENTS = 10_000_000

#: task_46's process directory: where a program's relative file paths point.
#: `file` is the folder of the running file (a new, unsaved buffer falls back to
#: `window`), `window` is the folder the window itself was started in — the old
#: behaviour — and `custom` is `PROCESS_DIRECTORY_PATH`.
DEFAULT_PROCESS_DIRECTORY = "file"
PROCESS_DIRECTORY_MODES = ("file", "window", "custom")

_TRUE = ("1", "true", "yes", "y", "да")


@dataclass(frozen=True)
class Setting:
    """One preference, described once.

    The same record is what the dialog builds its row from, what validation
    clamps against, and what «Сбросить» writes back — so a value can neither be
    editable without being stored nor stored without being documented.  `kind` is
    one of `bool`, `int`, `float`, `choice`, `text`, `file`, `directory`, `dirs`.
    """

    key: str
    label: str
    section: str
    kind: str = "text"
    default: object = ""
    low: float | None = None
    high: float | None = None
    #: `(value, what the user reads)` for `kind == "choice"`.
    choices: tuple[tuple[str, str], ...] = ()
    suffix: str = ""
    hint: str = ""

    def label_of(self, value: object) -> str:
        """How this value is written on screen (the label of a choice, else str)."""
        for choice, text in self.choices:
            if choice == value:
                return text
        return str(value)


#: The sections of the dialog, in the order they are shown.
SECTIONS = ("Редактор", "Вид", "Формат", "Выполнение", "Файлы")

#: Everything the dialog edits.  The keys the *window* writes for itself
#: (geometry, recent files, the insert table) are not here — see `MACHINE_KEYS`.
SETTINGS: tuple[Setting, ...] = (
    # -- editor
    Setting(FONT_FAMILY, "Шрифт", "Редактор", "text", DEFAULT_FONT_FAMILY,
            hint="Моноширинный шрифт с кириллицей; остальные панели берут его же"),
    Setting(FONT_SIZE, "Размер шрифта", "Редактор", "float", DEFAULT_FONT_SIZE,
            MINIMUM_FONT_SIZE, MAXIMUM_FONT_SIZE, suffix=" pt"),
    Setting(LINE_NUMBERS, "Номера строк", "Редактор", "bool", True),
    Setting(CURRENT_LINE, "Подсвечивать текущую строку", "Редактор", "bool", True,
            hint="Бледная полоса под курсором"),
    Setting(WRAP, "Переносить длинные строки", "Редактор", "bool", False,
            hint="Только в редакторе: строку вывода переносить нельзя"),
    Setting(INDENT_CHARACTER, "Отступ", "Редактор", "choice", "\t",
            choices=(("\t", "табуляция"), (" ", "пробелы"))),
    Setting(INDENT_WIDTH, "Ширина отступа", "Редактор", "int", 1, 1, 16,
            suffix=" знаков"),
    Setting(AUTO_INDENT, "Автоотступ", "Редактор", "bool", True,
            hint="Новая строка продолжает отступ предыдущей; `Enter` на пустой строке ничего не добавляет"),
    Setting(COMPLETION, "Автодополнение", "Редактор", "bool", True),
    Setting(AUTO_COMPLETE_AFTER, "Показывать после", "Редактор", "int",
            DEFAULT_AUTO_COMPLETE_AFTER, MINIMUM_AUTO_COMPLETE_AFTER,
            MAXIMUM_AUTO_COMPLETE_AFTER, suffix=" букв"),
    Setting(COMPLETION_MATCH_CASE, "Учитывать регистр в подсказках", "Редактор",
            "bool", True,
            hint="С выключенным: «най» предлагает и «НАЙТИВСЕ», и «найти»"),
    # -- view
    Setting(THEME, "Оформление", "Вид", "choice", DEFAULT_THEME,
            choices=(("light", "светлое"), ("dark", "тёмное"),
                     ("system", "системное")),
            hint="Тёмное — своя палитра подсветки и своя страница; «системное» — цвета рабочего стола, и виджетов, и подсветки"),
    Setting(TOOLBAR, "Панель инструментов", "Вид", "bool", True),
    Setting(OUTPUT_VISIBLE, "Панель вывода", "Вид", "bool", True),
    Setting(QUERY_VISIBLE, "Панель ввода цели", "Вид", "bool", True),
    Setting(OUTPUT_POSITION, "Панель вывода", "Вид", "choice",
            DEFAULT_OUTPUT_POSITION,
            choices=(("right", "справа"), ("bottom", "снизу"))),
    Setting(OUTPUT_FONT_SIZE, "Размер шрифта вывода", "Вид", "float",
            DEFAULT_OUTPUT_FONT_SIZE, MINIMUM_FONT_SIZE, MAXIMUM_FONT_SIZE,
            suffix=" pt", hint="Отдельно от редактора: колесо над панелью меняет его"),
    Setting(OUTPUT_LINE_LIMIT, "Помнить строк вывода", "Вид", "int",
            DEFAULT_OUTPUT_LINE_LIMIT, MINIMUM_OUTPUT_LINE_LIMIT,
            MAXIMUM_OUTPUT_LINE_LIMIT, suffix=" строк",
            hint="Старые строки удаляются, чтобы долгий прогон не съел память"),
    Setting(FOLLOW_OUTPUT, "Следить за выводом", "Вид", "bool", True,
            hint="Панель прокручивается к концу; выключено — остаётся там, где читают"),
    Setting(INPUT_MODE, "Спрашивать ввод", "Вид", "choice", DEFAULT_INPUT_MODE,
            choices=(("panel", "в панели вывода"), ("dialog", "в диалоге")),
            hint="В панели — консоль под строкой цели; в диалоге — окно на каждый запрос"),
    # -- format
    Setting(FORMAT_MODE, "Режим", "Формат", "choice", DEFAULT_FORMAT_MODE,
            choices=(("line", "в одну строку"), ("soft", "мягкое"),
                     ("hard", "жёсткое"))),
    Setting(FORMAT_WIDTH, "Ширина строки", "Формат", "int", DEFAULT_FORMAT_WIDTH,
            MINIMUM_FORMAT_WIDTH, MAXIMUM_FORMAT_WIDTH, suffix=" знаков"),
    Setting(FORMAT_INDENT, "Отступ продолжения", "Формат", "int",
            DEFAULT_FORMAT_INDENT, MINIMUM_FORMAT_INDENT, MAXIMUM_FORMAT_INDENT),
    Setting(FORMAT_UNIT, "Единица отступа", "Формат", "choice", DEFAULT_FORMAT_UNIT,
            choices=(("tab", "табуляция"), ("spaces", "четыре пробела"))),
    Setting(FORMAT_SELECTION, "Форматировать только выделенное", "Формат", "bool",
            False),
    # -- execution
    Setting(SAVE_BEFORE_RUN, "Сохранять перед запуском", "Выполнение", "bool", False,
            hint="Сохраняет текущий файл, если в нём есть несохранённые правки"),
    Setting(ANSWER_TABLE, "Формировать таблицу", "Выполнение", "bool", True,
            hint="Ответ отдельного запроса показывается ещё и таблицей: переменные — столбцы, решения — строки.  Текст в «Выводе» не меняется; выключено — таблица не строится вовсе"),
    Setting(RUN_QUESTIONS, "Выполнять вопросы при запуске", "Выполнение", "bool", True,
            hint="Строки «?цель.» программы выполняются сами; выключено — только правила"),
    Setting(PRINT_QUESTIONS, "Печатать вопросы при запуске", "Выполнение", "bool", False,
            hint="Каждый выполненный вопрос печатается сам (строка «?цель.») перед своим ответом"),
    Setting(MAX_STEPS, "Предел шагов", "Выполнение", "int", DEFAULT_MAX_STEPS, 0,
            MAXIMUM_MAX_STEPS,
            hint="Сколько шагов решателя на один запуск; 0 — без предела.  Останавливает бесконечный поиск"),
    Setting(MAX_DEPTH, "Предел глубины", "Выполнение", "int", DEFAULT_MAX_DEPTH, 0,
            MAXIMUM_MAX_DEPTH,
            hint="Глубина рекурсии; 0 — без предела.  Без предела убежавшую рекурсию останавливает только память"),
    Setting(MAX_FINDALL, "Предел решений НАЙТИВСЕ", "Выполнение", "int",
            DEFAULT_MAX_FINDALL, 0, MAXIMUM_MAX_FINDALL,
            hint="Столько решений соберёт НАЙТИВСЕ; 0 — без предела.  Предел — ошибка, а не обрезанный список"),
    Setting(TIMEOUT_MILLISECONDS, "Предел времени, мс", "Выполнение", "int",
            DEFAULT_TIMEOUT_MILLISECONDS, 0, MAXIMUM_TIMEOUT_MILLISECONDS,
            hint="Остановить программу по времени; 0 — без предела.  Ждущий ввода не прерывается"),
    Setting(MAX_OUTPUT_EVENTS, "Предел вывода", "Выполнение", "int",
            DEFAULT_MAX_OUTPUT_EVENTS, 0, MAXIMUM_MAX_OUTPUT_EVENTS, suffix=" событий",
            hint="Сколько событий вывода (строк и примитивов рисунка) разрешено за один запуск; 0 — без предела.  При превышении прогон останавливается — от потока вывода окно не зависает"),
    Setting(SCREEN_WIDTH, "Ширина графического экрана", "Выполнение", "int",
            DEFAULT_SCREEN_SIZE, MINIMUM_SCREEN_SIZE, MAXIMUM_SCREEN_SIZE,
            suffix=" точек",
            hint="Размер буфера, в котором рисуют графические предикаты.  Он же уезжает в окно снимком, а закраска обходит его по клеткам: чем больше экран, тем дороже каждый кадр.  600 — умолчание, 1024 × 768 — как было в первой версии"),
    Setting(SCREEN_HEIGHT, "Высота графического экрана", "Выполнение", "int",
            DEFAULT_SCREEN_SIZE, MINIMUM_SCREEN_SIZE, MAXIMUM_SCREEN_SIZE,
            suffix=" точек",
            hint="Высота того же буфера; вместе с шириной задаёт экран (раздел 6.5).  Новый размер применяется со следующего запуска"),
    Setting(VARIABLE_MODE, "Имена переменных", "Выполнение", "choice",
            DEFAULT_VARIABLE_MODE,
            choices=(("0", "как в ISO: переменная с большой буквы"),
                     ("1", "по-старому: одна буква — переменная"),
                     ("2", "то же плюс имена с апострофом")),
            hint="Как читать имена в файле, который об этом молчит: 0 — имя с большой буквы — переменная; 1 и 2 — старый диалект, где переменная — одна буква, а имя с большой буквы без кавычек — строковая константа.  Строка «:- ИМЕНА(N).» первой строкой файла важнее этой настройки, и импортируемый файл читается в своём режиме.  Режим меняет подсветку и форматирование, а запуск всё равно читает маркер из файла"),
    Setting(IMPORT_PATHS, "Дополнительные каталоги ИМПОРТ", "Выполнение", "dirs", (),
            hint="Каталоги, в которых ИМПОРТ ищет файлы; передаются интерпретатору как -I, в этом порядке"),
    Setting(INTERPRETER, "Интерпретатор", "Выполнение", "file", "",
            hint="Путь к prologd; пусто — тот, с которым окно запущено.  Смена действует со следующего запуска"),
    Setting(PROCESS_DIRECTORY, "Рабочий каталог процесса", "Выполнение", "choice",
            DEFAULT_PROCESS_DIRECTORY,
            choices=(("file", "каталог файла программы"),
                     ("window", "рабочая папка окна"),
                     ("custom", "свой каталог")),
            hint="Отсюда считаются ЗАПИСЬ_В, ЧТЕНИЕ_ИЗ и другие относительные пути"),
    Setting(PROCESS_DIRECTORY_PATH, "Свой каталог процесса", "Выполнение", "directory", "",
            hint="Используется, когда выше выбран «свой каталог»"),
    # -- files
    Setting(RESTORE_TABS, "Восстанавливать вкладки при старте", "Файлы", "bool", True,
            hint="Файлы читаются заново с диска"),
    Setting(AUTOSAVE_MINUTES, "Автосохранение, мин", "Файлы", "int",
            DEFAULT_AUTOSAVE_MINUTES, 0, MAXIMUM_AUTOSAVE_MINUTES,
            hint="0 — выключено.  Сохраняются только файлы с именем"),
    Setting(RECENT_LIMIT, "Помнить недавних файлов", "Файлы", "int",
            DEFAULT_RECENT_LIMIT, 0, MAXIMUM_RECENT_LIMIT),
)

#: The key of a record, for the callers that have one and not the other.
BY_KEY: dict[str, Setting] = {setting.key: setting for setting in SETTINGS}

#: A record looked up by key, for a property that wants the bounds of that record
#: rather than a number written out a second time (`input_mode`).
_INPUT_MODE_SETTING = BY_KEY[INPUT_MODE]
_VARIABLE_MODE_SETTING = BY_KEY[VARIABLE_MODE]
#: The same for the process directory (task_46): its `file|window|custom` answer
#: is written through the description, so a wrong value in a hand-edited file
#: falls back the way every other choice does.
_PROCESS_DIRECTORY_SETTING = BY_KEY[PROCESS_DIRECTORY]

#: Stored, but written by the window rather than by the user: window geometry,
#: the recent list, the insert table.  Kept here so a test can prove that every
#: key of this module is either editable in the dialog or on this list.
MACHINE_KEYS = (
    RECENT_FILES,
    LAST_DIRECTORY,
    SPLIT_EDITOR,
    SPLIT_SIZES,
    RESTORE_SPLIT,
    GRAPHICS_VISIBLE,
    GRAPHICS_GEOMETRY,
    WINDOW_GEOMETRY,
    PANEL_SIZES,
    SHORTCUTS_TABLE,
    SYNTAX_LIGHT,
    SYNTAX_DARK,
    SESSION_TABS,
    SESSION_CURRENT,
)


def default_path() -> Path:
    """`%LOCALAPPDATA%\\PrologD\\gui\\gui.ini` on Windows, the XDG equivalent elsewhere.

    `AppConfigLocation` is `AppLocalDataLocation` on Windows (the *local*, not the
    roaming directory) and is derived from the organisation and application name,
    so `main.py` sets both on `QCoreApplication` before the first call here.
    """
    directory = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(directory or ".") / "gui.ini"


class Settings:
    """Typed access to the ini file, with the bounds applied on read."""

    #: Also the names `main.py` sets on `QCoreApplication`, because `default_path`
    #: is derived from them.
    organization = ORGANIZATION
    application = APPLICATION

    def __init__(self, filename: str | Path | None = None) -> None:
        self.path = Path(filename) if filename is not None else default_path()
        self._store = QSettings(str(self.path), QSettings.Format.IniFormat)

    # -- reading helpers ----------------------------------------------------
    def _text(self, key: str, default: str) -> str:
        value = self._store.value(key, default)
        return default if value is None else str(value)

    def _flag(self, key: str, default: bool) -> bool:
        value = self._store.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in _TRUE
        return bool(value)

    def _number(self, key: str, default: float, low: float, high: float) -> float:
        try:
            value = float(self._store.value(key, default))
        except (TypeError, ValueError):
            return default
        if value != value:  # NaN, which compares false against everything
            return default
        return min(high, max(low, value))

    def _write(self, key: str, value: object) -> None:
        self._store.setValue(key, value)
        # Written straight away rather than on destruction: a crashed or killed
        # window would otherwise lose the settings the user just changed, and
        # there are few enough of them for the write to cost nothing.
        self._store.sync()

    def raw_value(self, key: str, default: object = None) -> object:
        """A value this class has no property for (task_29's dialog reads these)."""
        return self._store.value(key, default)

    def all_keys(self) -> list[str]:
        """Every key in the file, known to this class or not."""
        return list(self._store.allKeys())

    def has(self, key: str) -> bool:
        """Whether the file holds this key at all.

        Asked by the one preference that *follows* another until it is given a
        value of its own: the output's font size reads as the editor's while
        nobody has ever set it (task_29).
        """
        return self._store.contains(key)

    # -- the described settings (task_29) -----------------------------------
    def value_of(self, setting: Setting) -> object:
        """One described setting, read with its own default and bounds.

        The single reader for the dialog and for «Сбросить»: a kind that is not
        known here is a programming mistake, and saying so beats a widget that
        silently shows the default for ever.
        """
        if setting.kind == "bool":
            return self._flag(setting.key, bool(setting.default))
        if setting.kind == "int":
            return int(self._number(setting.key, float(setting.default),
                                    float(setting.low), float(setting.high)))
        if setting.kind == "float":
            return float(self._number(setting.key, float(setting.default),
                                      float(setting.low), float(setting.high)))
        if setting.kind == "choice":
            return self._choice(setting)
        if setting.kind == "dirs":
            return self._paths(setting.key)
        if setting.kind in ("text", "directory", "file"):
            return self._text(setting.key, str(setting.default))
        raise ValueError(f"unknown kind {setting.kind!r} for {setting.key}")

    def set_value(self, setting: Setting, value: object) -> None:
        """Writes one described setting, validated by its own description."""
        if setting.kind == "bool":
            self._write(setting.key, bool(value))
        elif setting.kind == "int":
            self._write(setting.key, int(self._clamp(setting, value)))
        elif setting.kind == "float":
            self._write(setting.key, float(self._clamp(setting, value)))
        elif setting.kind == "choice":
            values = [choice for choice, _ in setting.choices]
            self._write(setting.key, value if value in values else setting.default)
        elif setting.kind == "dirs":
            self._write(setting.key, [str(item) for item in value or [] if str(item)])
        elif setting.kind in ("text", "directory", "file"):
            self._write(setting.key, str(value))
        else:
            raise ValueError(f"unknown kind {setting.kind!r} for {setting.key}")

    def reset(self, settings: tuple[Setting, ...] | None = None) -> int:
        """«Сбросить»: every described setting back to its default.

        Only the described ones.  The recent list, the window geometry and the
        insert table are not preferences the user set in this dialog, and
        clearing them on «Сбросить» would throw away work rather than undo a
        choice.  Returns how many keys were written.
        """
        chosen = SETTINGS if settings is None else settings
        for setting in chosen:
            self.set_value(setting, setting.default)
        return len(chosen)

    def export_to(self, path: str | Path) -> int:
        """Writes the whole configuration to `path`, unknown keys included.

        An empty store is filled with the defaults first: the file a teacher
        hands out has to be a complete configuration, not an empty ini.
        """
        self._store.sync()
        target = QSettings(str(path), QSettings.Format.IniFormat)
        for key in self._store.allKeys():
            target.setValue(key, self._store.value(key))
        for setting in SETTINGS:
            if not target.contains(setting.key):
                target.setValue(setting.key, self.value_of(setting))
        target.sync()
        return len(target.allKeys())

    def read_keys(self, path: str | Path) -> dict[str, object]:
        """Every key of another ini, read but not written (task_29's «Импорт…»).

        Reading and writing are apart so the dialog can *show* an imported file
        before it keeps it: «Отмена» after «Импорт…» must leave the settings as
        they were, and staging is what makes that true.
        """
        source = QSettings(str(path), QSettings.Format.IniFormat)
        keys = source.allKeys()
        if not keys:
            raise ValueError(f"{path}: это не файл настроек")
        return {key: source.value(key) for key in keys}

    def write_keys(self, values: dict[str, object]) -> int:
        """Writes a set of keys as they are — unknown names included."""
        for key, value in values.items():
            self._store.setValue(key, value)
        self._store.sync()
        return len(values)

    def import_from(self, path: str | Path) -> int:
        """Reads a configuration written by `export_to`; returns how many keys came.

        Everything in the file is copied, not just the keys this version knows:
        a class file from a newer build keeps its own settings for when the
        student's machine is updated.
        """
        return self.write_keys(self.read_keys(path))

    def _choice(self, setting: Setting) -> str:
        """A stored choice: exact match first, then ignoring case and space.

        `indent_character` is a space or a tab, so the fallback has to compare
        without stripping; `theme` and the format modes are words, and a file
        that says `System` means the same as `system`.
        """
        value = self._text(setting.key, str(setting.default))
        for choice, _ in setting.choices:
            if value == choice:
                return choice
        folded = value.strip().lower()
        for choice, _ in setting.choices:
            if choice.strip().lower() == folded and choice.strip():
                return choice
        return str(setting.default)

    def _paths(self, key: str) -> list[str]:
        """A stored list of directories, tolerating a hand-edited file (a single
        path comes back as a string, and a blank one as nothing at all)."""
        value = self._store.value(key, [])
        if isinstance(value, str):
            value = [value] if value else []
        return [str(item) for item in value or [] if str(item)]

    @staticmethod
    def _clamp(setting: Setting, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return float(setting.default)
        if number != number:  # NaN
            return float(setting.default)
        low = float(setting.low) if setting.low is not None else number
        high = float(setting.high) if setting.high is not None else number
        return min(high, max(low, number))

    # -- editor -------------------------------------------------------------
    @property
    def font_family(self) -> str:
        return self._text(FONT_FAMILY, DEFAULT_FONT_FAMILY)

    @font_family.setter
    def font_family(self, value: str) -> None:
        self._write(FONT_FAMILY, str(value))

    @property
    def font_size(self) -> float:
        return self._number(FONT_SIZE, DEFAULT_FONT_SIZE, MINIMUM_FONT_SIZE, MAXIMUM_FONT_SIZE)

    @font_size.setter
    def font_size(self, value: float) -> None:
        self._write(FONT_SIZE, min(MAXIMUM_FONT_SIZE, max(MINIMUM_FONT_SIZE, float(value))))

    @property
    def line_numbers(self) -> bool:
        return self._flag(LINE_NUMBERS, True)

    @line_numbers.setter
    def line_numbers(self, value: bool) -> None:
        self._write(LINE_NUMBERS, bool(value))

    @property
    def wrap(self) -> bool:
        """Wrap long lines in the editor.  Off by default: a program line is read
        as a whole, and a wrapped one hides where the line really ends."""
        return self._flag(WRAP, False)

    @wrap.setter
    def wrap(self, value: bool) -> None:
        self._write(WRAP, bool(value))

    @property
    def indent_character(self) -> str:
        character = self._text(INDENT_CHARACTER, "\t")
        return character if character in ("\t", " ") else "\t"

    @indent_character.setter
    def indent_character(self, value: str) -> None:
        self._write(INDENT_CHARACTER, "\t" if value == "\t" else " ")

    @property
    def indent_width(self) -> int:
        return int(self._number(INDENT_WIDTH, 1, 1, 16))

    @indent_width.setter
    def indent_width(self, value: int) -> None:
        self._write(INDENT_WIDTH, int(min(16, max(1, value))))

    @property
    def auto_indent(self) -> bool:
        """Whether `Enter` starts the new line at the old line's indentation."""
        return self._flag(AUTO_INDENT, True)

    @auto_indent.setter
    def auto_indent(self, value: bool) -> None:
        self._write(AUTO_INDENT, bool(value))

    @property
    def completion(self) -> bool:
        return self._flag(COMPLETION, True)

    @completion.setter
    def completion(self, value: bool) -> None:
        self._write(COMPLETION, bool(value))

    @property
    def auto_complete_after(self) -> int:
        return int(
            self._number(
                AUTO_COMPLETE_AFTER,
                DEFAULT_AUTO_COMPLETE_AFTER,
                MINIMUM_AUTO_COMPLETE_AFTER,
                MAXIMUM_AUTO_COMPLETE_AFTER,
            )
        )

    @auto_complete_after.setter
    def auto_complete_after(self, value: int) -> None:
        self._write(
            AUTO_COMPLETE_AFTER,
            int(min(MAXIMUM_AUTO_COMPLETE_AFTER, max(MINIMUM_AUTO_COMPLETE_AFTER, value))),
        )

    @property
    def completion_match_case(self) -> bool:
        """Whether the popup honours the case of what is typed (task_29)."""
        return self._flag(COMPLETION_MATCH_CASE, True)

    @completion_match_case.setter
    def completion_match_case(self, value: bool) -> None:
        self._write(COMPLETION_MATCH_CASE, bool(value))

    @property
    def current_line(self) -> bool:
        """Whether the line the caret is on is tinted."""
        return self._flag(CURRENT_LINE, True)

    @current_line.setter
    def current_line(self, value: bool) -> None:
        self._write(CURRENT_LINE, bool(value))

    # -- view ---------------------------------------------------------------
    @property
    def theme(self) -> str:
        return self._text(THEME, DEFAULT_THEME)

    @theme.setter
    def theme(self, value: str) -> None:
        self._write(THEME, str(value))

    @property
    def palette(self) -> theme.Palette:
        """The colours of everything: the theme name, resolved (task_29).

        `system` means the desktop's own colours — the widget palette *and* the page
        the syntax colours are measured against — so the answer comes from
        `appearance`, the one module that knows Qt's colour scheme.  The import is
        local: the store itself has nothing to do with widgets.

        The syntax colours the user changed (task_50) are layered over the
        resolved palette: the override is read for the palette that was actually
        chosen, so a `system` desktop gets the dark override when the desktop is
        dark.
        """
        from . import appearance

        resolved = appearance.theme_palette(self.theme)
        overrides = self.syntax_overrides(resolved.name)
        if not overrides:
            return resolved
        return theme.apply_syntax_overrides(resolved, overrides)

    # -- syntax colours (task_50) -------------------------------------------
    def syntax_overrides(self, name: str) -> dict[str, str]:
        """The changed syntax colours of one palette, `field -> #rrggbb`.

        `name` is `light` or `dark` — the *actual* palette, not the `system`
        choice.  A file that holds nonsense falls back to nothing; only known
        field names with valid hex survive (`theme.clean_hex`).
        """
        key = SYNTAX_LIGHT if name == theme.LIGHT.name else SYNTAX_DARK
        text = self._text(key, "").strip()
        if not text:
            return {}
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        known = set(theme.Theme.__dataclass_fields__)
        cleaned: dict[str, str] = {}
        for field, value in raw.items():
            hex_value = theme.clean_hex(str(value))
            if field in known and hex_value is not None:
                cleaned[field] = hex_value
        return cleaned

    def set_syntax_overrides(self, name: str, overrides: dict[str, str]) -> None:
        """Writes the changed syntax colours of one palette as JSON (task_50)."""
        key = SYNTAX_LIGHT if name == theme.LIGHT.name else SYNTAX_DARK
        self._write(key, json.dumps(overrides, ensure_ascii=False))

    # -- files -------------------------------------------------------------
    @property
    def recent_files(self) -> list[str]:
        """Newest first.  A single value comes back as a string, not a list."""
        value = self._store.value(RECENT_FILES, [])
        if isinstance(value, str):
            value = [value] if value else []
        return [str(item) for item in value or [] if str(item)]

    @recent_files.setter
    def recent_files(self, paths) -> None:
        self._write(RECENT_FILES, [str(path) for path in paths])

    @property
    def last_directory(self) -> str:
        """Where the open/save dialogs start; empty means "the current one"."""
        return self._text(LAST_DIRECTORY, "")

    @last_directory.setter
    def last_directory(self, value: str) -> None:
        self._write(LAST_DIRECTORY, str(value))

    @property
    def recent_limit(self) -> int:
        """How many files the «Последние» menu remembers."""
        return int(self._number(RECENT_LIMIT, DEFAULT_RECENT_LIMIT, 0, MAXIMUM_RECENT_LIMIT))

    @recent_limit.setter
    def recent_limit(self, value: int) -> None:
        self._write(RECENT_LIMIT, min(MAXIMUM_RECENT_LIMIT, max(0, int(value))))

    @property
    def autosave_minutes(self) -> int:
        """Minutes between two automatic saves; 0 is off."""
        return int(
            self._number(AUTOSAVE_MINUTES, DEFAULT_AUTOSAVE_MINUTES, 0,
                         MAXIMUM_AUTOSAVE_MINUTES)
        )

    @autosave_minutes.setter
    def autosave_minutes(self, value: int) -> None:
        self._write(AUTOSAVE_MINUTES, min(MAXIMUM_AUTOSAVE_MINUTES, max(0, int(value))))

    @property
    def restore_tabs(self) -> bool:
        """Whether the tabs of the previous run reopen on the next start."""
        return self._flag(RESTORE_TABS, True)

    @restore_tabs.setter
    def restore_tabs(self, value: bool) -> None:
        self._write(RESTORE_TABS, bool(value))

    @property
    def session_tabs(self) -> list[str]:
        """The remembered tabs, in bar order; "" when there is no session."""
        return self._paths(SESSION_TABS)

    @session_tabs.setter
    def session_tabs(self, lines) -> None:
        self._write(SESSION_TABS, [str(line) for line in lines])

    @property
    def session_current(self) -> str:
        """Which tab was showing: its path, or the name of an untitled one."""
        return self._text(SESSION_CURRENT, "")

    @session_current.setter
    def session_current(self, value: str) -> None:
        self._write(SESSION_CURRENT, str(value))

    @property
    def graphics_visible(self) -> bool:
        """Whether the graphics window was open when the window was last closed."""
        return self._flag(GRAPHICS_VISIBLE, False)

    @graphics_visible.setter
    def graphics_visible(self, value: bool) -> None:
        self._write(GRAPHICS_VISIBLE, bool(value))

    @property
    def graphics_geometry(self) -> str:
        """The graphics window's geometry as text; "" until it was ever moved.

        Stored as text and not as a rectangle: Qt's `saveGeometry`/`restoreGeometry`
        know about screens, a maximised state and a window that was moved to a
        display that is no longer there, and a hand-made x/y/width/height would
        have to re-learn all of that.
        """
        return self._text(GRAPHICS_GEOMETRY, "")

    @graphics_geometry.setter
    def graphics_geometry(self, value: str) -> None:
        self._write(GRAPHICS_GEOMETRY, str(value))

    @property
    def window_geometry(self) -> str:
        """The main window's geometry as text; "" until it was ever moved.

        The same `saveGeometry()` blob the graphics window keeps (see
        `prologd_gui.geometry`): the size, the place *and* whether the window was
        maximised, in a form Qt can put back on a screen that still exists.
        """
        return self._text(WINDOW_GEOMETRY, "")

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._write(WINDOW_GEOMETRY, str(value))

    # -- the split editor ---------------------------------------------------
    @property
    def split_editor(self) -> bool:
        """Whether the second editor pane was open."""
        return self._flag(SPLIT_EDITOR, False)

    @split_editor.setter
    def split_editor(self, value: bool) -> None:
        self._write(SPLIT_EDITOR, bool(value))

    @property
    def split_sizes(self) -> list[int]:
        """The widths of the two editor panes, as last seen."""
        value = self._store.value(SPLIT_SIZES, [])
        if isinstance(value, (int, str)):  # a single value is not a list
            value = [value] if value != "" else []
        sizes: list[int] = []
        for item in value or []:
            try:
                sizes.append(int(item))
            except (TypeError, ValueError):
                continue
        return sizes

    @split_sizes.setter
    def split_sizes(self, sizes) -> None:
        self._write(SPLIT_SIZES, [int(size) for size in sizes])

    @property
    def restore_split(self) -> bool:
        """Reopen the split editor on the next start.

        Named apart from the «восстанавливать вкладки» switch of task_29: this one
        only decides the panes, because the documents themselves are not reopened
        yet.
        """
        return self._flag(RESTORE_SPLIT, True)

    @restore_split.setter
    def restore_split(self, value: bool) -> None:
        self._write(RESTORE_SPLIT, bool(value))

    @property
    def toolbar_visible(self) -> bool:
        return self._flag(TOOLBAR, True)

    @toolbar_visible.setter
    def toolbar_visible(self, value: bool) -> None:
        self._write(TOOLBAR, bool(value))

    # -- the output panel ---------------------------------------------------
    @property
    def output_position(self) -> str:
        """`right` or `bottom`; anything else in the file reads as the default."""
        value = self._text(OUTPUT_POSITION, DEFAULT_OUTPUT_POSITION).strip().lower()
        return value if value in OUTPUT_POSITIONS else DEFAULT_OUTPUT_POSITION

    @output_position.setter
    def output_position(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(OUTPUT_POSITION, text if text in OUTPUT_POSITIONS else DEFAULT_OUTPUT_POSITION)

    @property
    def output_visible(self) -> bool:
        """Whether the output panel is shown at all (`F4` switches this)."""
        return self._flag(OUTPUT_VISIBLE, True)

    @output_visible.setter
    def output_visible(self, value: bool) -> None:
        self._write(OUTPUT_VISIBLE, bool(value))

    @property
    def query_visible(self) -> bool:
        """Whether the goal field is shown at all (part 92)."""
        return self._flag(QUERY_VISIBLE, True)

    @query_visible.setter
    def query_visible(self, value: bool) -> None:
        self._write(QUERY_VISIBLE, bool(value))

    @property
    def output_font_size(self) -> float:
        """The output panel's own size since task_29.

        It starts *shared* with the editor (`DEFAULT_OUTPUT_FONT_SIZE` is the
        same number), and only a change in the dialog or a wheel over the panel
        pulls them apart; a file written by an older build therefore reads as one
        size, exactly as it looked before.
        """
        return self._number(OUTPUT_FONT_SIZE, self.font_size, MINIMUM_FONT_SIZE,
                            MAXIMUM_FONT_SIZE)

    @output_font_size.setter
    def output_font_size(self, value: float) -> None:
        self._write(
            OUTPUT_FONT_SIZE,
            min(MAXIMUM_FONT_SIZE, max(MINIMUM_FONT_SIZE, float(value))),
        )

    @property
    def output_line_limit(self) -> int:
        """How many lines of output are kept before the oldest are dropped."""
        return int(
            self._number(OUTPUT_LINE_LIMIT, DEFAULT_OUTPUT_LINE_LIMIT,
                         MINIMUM_OUTPUT_LINE_LIMIT, MAXIMUM_OUTPUT_LINE_LIMIT)
        )

    @output_line_limit.setter
    def output_line_limit(self, value: int) -> None:
        self._write(
            OUTPUT_LINE_LIMIT,
            min(MAXIMUM_OUTPUT_LINE_LIMIT, max(MINIMUM_OUTPUT_LINE_LIMIT, int(value))),
        )

    @property
    def follow_output(self) -> bool:
        """Whether the output pane keeps the end of the text in sight."""
        return self._flag(FOLLOW_OUTPUT, True)

    @follow_output.setter
    def follow_output(self, value: bool) -> None:
        self._write(FOLLOW_OUTPUT, bool(value))

    @property
    def input_mode(self) -> str:
        """`panel` (the console under the output) or `dialog` (a box per question)."""
        return self._choice(_INPUT_MODE_SETTING)

    @input_mode.setter
    def input_mode(self, value: str) -> None:
        self.set_value(_INPUT_MODE_SETTING, value)

    @property
    def panel_sizes(self) -> list[int]:
        """The editor and the output panel as last seen — widths or heights,
        depending on which side the panel is on."""
        return self._sizes(PANEL_SIZES)

    @property
    def variable_mode(self) -> str:
        """How a file *without* a marker of its own is read: `0`, `1` or `2`.

        The file's own `:- ИМЕНА(N).` first line beats this (task_67), so what is
        left is the window's half of `--vars`: the mode of a file that says
        nothing — `0`, unless the reader asks for the old dialect by name.
        """
        return self._choice(_VARIABLE_MODE_SETTING)

    @variable_mode.setter
    def variable_mode(self, value: str) -> None:
        self.set_value(_VARIABLE_MODE_SETTING, value)

    @property
    def variable_mode_number(self) -> int:
        """The same choice as the number a run takes."""
        return int(self.variable_mode)

    @panel_sizes.setter
    def panel_sizes(self, sizes) -> None:
        self._write(PANEL_SIZES, [int(size) for size in sizes])

    def _sizes(self, key: str) -> list[int]:
        """A stored list of sizes, tolerating a hand-edited file.

        A single value comes back as a string rather than a list, and a value that
        is not a number is dropped instead of stopping the window from starting.
        """
        value = self._store.value(key, [])
        if isinstance(value, (int, str)):
            value = [value] if value != "" else []
        sizes: list[int] = []
        for item in value or []:
            try:
                sizes.append(int(item))
            except (TypeError, ValueError):
                continue
        return sizes

    # -- execution ----------------------------------------------------------
    @property
    def save_before_run(self) -> bool:
        """Write the current file before running it (the «Выполнение» switch)."""
        return self._flag(SAVE_BEFORE_RUN, False)

    @save_before_run.setter
    def save_before_run(self, value: bool) -> None:
        self._write(SAVE_BEFORE_RUN, bool(value))

    @property
    def run_questions(self) -> bool:
        """Whether a run answers the program's own `?`-statements.

        The `questions` flag of `load` (protocol 5).  Off, a lesson is loaded as
        rules only — which is what a lecture wants: the questions come one at a
        time, from the editor's margin.  The margin's own click is not affected:
        it always answers its one question.
        """
        return self._flag(RUN_QUESTIONS, True)

    @run_questions.setter
    def run_questions(self, value: bool) -> None:
        self._write(RUN_QUESTIONS, bool(value))

    @property
    def print_questions(self) -> bool:
        """Whether a run question echoes itself before its answer (protocol 11)."""
        return self._flag(PRINT_QUESTIONS, False)

    @print_questions.setter
    def print_questions(self, value: bool) -> None:
        self._write(PRINT_QUESTIONS, bool(value))

    @property
    def answer_table(self) -> bool:
        """Whether a single goal's answer is also shown as a table (task_59).

        On by default since 2026-10-03: the table is what makes the answer of one
        goal readable at a glance, and the panel moves to its tab only when there
        is an answer to show.  The text of the answer is written either way.  A
        single goal is the goal line or a margin marker; a whole run is never
        tabulated.
        """
        return self._flag(ANSWER_TABLE, True)

    @answer_table.setter
    def answer_table(self, value: bool) -> None:
        self._write(ANSWER_TABLE, bool(value))

    @property
    def max_steps(self) -> int:
        """The step cap of a run; 0 is «без предела»."""
        return int(self._number(MAX_STEPS, DEFAULT_MAX_STEPS, 0, MAXIMUM_MAX_STEPS))

    @max_steps.setter
    def max_steps(self, value: int) -> None:
        self._write(MAX_STEPS, int(min(MAXIMUM_MAX_STEPS, max(0, value))))

    @property
    def max_depth(self) -> int:
        """The recursion-depth cap of a run; 0 is «без предела»."""
        return int(self._number(MAX_DEPTH, DEFAULT_MAX_DEPTH, 0, MAXIMUM_MAX_DEPTH))

    @max_depth.setter
    def max_depth(self, value: int) -> None:
        self._write(MAX_DEPTH, int(min(MAXIMUM_MAX_DEPTH, max(0, value))))

    @property
    def max_findall(self) -> int:
        """How many solutions one НАЙТИВСЕ may collect; 0 is «без предела»."""
        return int(self._number(MAX_FINDALL, DEFAULT_MAX_FINDALL, 0, MAXIMUM_MAX_FINDALL))

    @max_findall.setter
    def max_findall(self, value: int) -> None:
        self._write(MAX_FINDALL, int(min(MAXIMUM_MAX_FINDALL, max(0, value))))

    @property
    def timeout_milliseconds(self) -> int:
        """The wall-clock cap of a run in milliseconds; 0 is off."""
        return int(
            self._number(TIMEOUT_MILLISECONDS, DEFAULT_TIMEOUT_MILLISECONDS, 0,
                         MAXIMUM_TIMEOUT_MILLISECONDS)
        )

    @timeout_milliseconds.setter
    def timeout_milliseconds(self, value: int) -> None:
        self._write(TIMEOUT_MILLISECONDS, int(min(MAXIMUM_TIMEOUT_MILLISECONDS, max(0, value))))

    @property
    def max_output_events(self) -> int:
        """How many output events one run may produce; 0 is off."""
        return int(
            self._number(MAX_OUTPUT_EVENTS, DEFAULT_MAX_OUTPUT_EVENTS, 0,
                         MAXIMUM_MAX_OUTPUT_EVENTS)
        )

    @max_output_events.setter
    def max_output_events(self, value: int) -> None:
        self._write(MAX_OUTPUT_EVENTS, int(min(MAXIMUM_MAX_OUTPUT_EVENTS, max(0, value))))

    @property
    def screen_size(self) -> tuple[int, int]:
        """The screen the graphics predicates draw on: `(width, height)` (task_73).

        Sent with every run, so the buffer is the size the window shows; a request
        that names no size keeps the engine's own default, which is the same
        600 × 600.  Two rows rather than one so a hand-edited file cannot hold a
        size the dialog would have to parse.
        """
        width = self._number(SCREEN_WIDTH, DEFAULT_SCREEN_SIZE, MINIMUM_SCREEN_SIZE,
                             MAXIMUM_SCREEN_SIZE)
        height = self._number(SCREEN_HEIGHT, DEFAULT_SCREEN_SIZE, MINIMUM_SCREEN_SIZE,
                              MAXIMUM_SCREEN_SIZE)
        return (int(width), int(height))

    @screen_size.setter
    def screen_size(self, size) -> None:
        for key, value in zip((SCREEN_WIDTH, SCREEN_HEIGHT), size, strict=True):
            self._write(key, int(min(MAXIMUM_SCREEN_SIZE, max(MINIMUM_SCREEN_SIZE, value))))

    def limits(self) -> dict:
        """The three caps, as the `limits` object of a `load` (protocol 9).

        `0` is «без предела» and is therefore *left out*: the engine's own default
        is «без предела» as well, so a zero on the wire would be a second way of
        saying «nothing was asked for».  The timeout is not here — the window
        keeps that clock.
        """
        asked = {
            "maxSteps": self.max_steps,
            "maxDepth": self.max_depth,
            "maxFindall": self.max_findall,
        }
        return {name: value for name, value in asked.items() if value > 0}

    @property
    def import_paths(self) -> list[str]:
        """The folders `ИМПОРТ` searches, in the order the engine tries them."""
        return self._paths(IMPORT_PATHS)

    @import_paths.setter
    def import_paths(self, paths) -> None:
        self._write(IMPORT_PATHS, [str(path) for path in paths if str(path)])

    # -- the interpreter and its process directory (task_46) ------------------
    @property
    def interpreter(self) -> str:
        """The `prologd` path the rows name; `""` means «the window's own»."""
        return self._text(INTERPRETER, "")

    @interpreter.setter
    def interpreter(self, value: str) -> None:
        self._write(INTERPRETER, str(value))

    @property
    def process_directory(self) -> str:
        """`file`, `window` or `custom`; anything else reads as `file`."""
        return self._choice(_PROCESS_DIRECTORY_SETTING)

    @process_directory.setter
    def process_directory(self, value: str) -> None:
        self.set_value(_PROCESS_DIRECTORY_SETTING, value)

    @property
    def process_directory_path(self) -> str:
        """The folder of the `custom` answer; `""` when none was set."""
        return self._text(PROCESS_DIRECTORY_PATH, "")

    @process_directory_path.setter
    def process_directory_path(self, value: str) -> None:
        self._write(PROCESS_DIRECTORY_PATH, str(value))

    # -- the formatter (task_30) ---------------------------------------------
    @property
    def format_mode(self) -> str:
        """`line`, `soft` or `hard`; anything else in the file reads as `soft`.

        An ini written by an earlier build may say `none` (the retired «не
        менять»); the fallback turns that into the soft mode.
        """
        value = self._text(FORMAT_MODE, DEFAULT_FORMAT_MODE).strip().lower()
        return value if value in FORMAT_MODES else DEFAULT_FORMAT_MODE

    @format_mode.setter
    def format_mode(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(FORMAT_MODE, text if text in FORMAT_MODES else DEFAULT_FORMAT_MODE)

    @property
    def format_width(self) -> int:
        """What has to fit on one line in the soft mode, in code points."""
        return int(
            self._number(FORMAT_WIDTH, DEFAULT_FORMAT_WIDTH, MINIMUM_FORMAT_WIDTH,
                         MAXIMUM_FORMAT_WIDTH)
        )

    @format_width.setter
    def format_width(self, value: int) -> None:
        self._write(FORMAT_WIDTH, int(value))

    @property
    def format_indent(self) -> int:
        """How many indent units a continuation line starts with."""
        return int(
            self._number(FORMAT_INDENT, DEFAULT_FORMAT_INDENT, MINIMUM_FORMAT_INDENT,
                         MAXIMUM_FORMAT_INDENT)
        )

    @format_indent.setter
    def format_indent(self, value: int) -> None:
        self._write(FORMAT_INDENT, int(value))

    @property
    def format_unit(self) -> str:
        """`tab` or `spaces` — one tab is one unit, four spaces are one unit."""
        value = self._text(FORMAT_UNIT, DEFAULT_FORMAT_UNIT).strip().lower()
        return value if value in FORMAT_UNITS else DEFAULT_FORMAT_UNIT

    @format_unit.setter
    def format_unit(self, value: str) -> None:
        text = str(value).strip().lower()
        self._write(FORMAT_UNIT, text if text in FORMAT_UNITS else DEFAULT_FORMAT_UNIT)

    @property
    def format_selection(self) -> bool:
        """«Форматировать только выделенное»: with a selection, only it is sent."""
        return self._flag(FORMAT_SELECTION, False)

    @format_selection.setter
    def format_selection(self, value: bool) -> None:
        self._write(FORMAT_SELECTION, bool(value))

    # -- editor keys --------------------------------------------------------
    @property
    def shortcuts_table(self) -> str:
        """The insert table as JSON; "" when the file has none yet.

        The window writes the built-in table here the first time it runs, which
        is what makes the table readable — and remappable — from the file at
        all.
        """
        return self._text(SHORTCUTS_TABLE, "").strip()

    @shortcuts_table.setter
    def shortcuts_table(self, value: str) -> None:
        self._write(SHORTCUTS_TABLE, str(value))
