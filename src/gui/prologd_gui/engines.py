"""The engines the window can run, and what each of them can do (task_79).

Two programs answer this front-end's line-delimited JSON: our own `prologu.exe`
(«Пролог-У», the engine of this repository) and the original `prologd.exe`
(«Пролог-Д»), which task_78 builds beside it.  They are **not** interchangeable,
and the protocol number does not say so: the original answers `"protocol": 13`
and its own `src/protocol.cpp` calls that a *subset* of ours.  So the differences
are written down here, once, as a table — the alternative is `if`s scattered over
the window, and a command that quietly does nothing.

A **capability** is what a front-end command needs from the engine behind it: the
format request, a step, a trace, the graphics screen, the `limits` object of a
`load`, the naming modes.  `Engine.has` answers for one engine, and the window
asks before it offers a command (`Action.needs`), before it promises a limit
(`window._limits_note`) and before it shows a row of the settings dialog
(`settings.GATED_ROWS`).

Nothing here imports Qt or the rest of the package, so the table can be read —
and checked — without a display: `tests/test_engines.py`.

*Where* the file of an engine is looked for is not here either: that is
`paths.engine_executable`, which asks this module for `file_name` and nothing
else.
"""

from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass

#: Formatting: the `format` request of the protocol, and the «Форматировать»
#: command with the mode control beside it (task_30, task_47).
FORMAT = "format"
#: `Шаг` and `Шаг с обходом`: the `step` request and the `stepped` events.
STEP = "step"
#: «Запустить с трассировкой»: `trace` in a `load`, and the `trace` events.
TRACE = "trace"
#: The graphics screen: `screen` in a `load`, the `drawn`/`bitmap` events, and
#: the two «экран» rows of the settings dialog (task_73).
GRAPHICS = "graphics"
#: The `limits` object of a `load` — `maxSteps`, `maxDepth`, `maxFindall`.
LIMITS = "limits"
#: «Имена переменных»: `variables` in a `load`, and the reading of a file that
#: does not declare its dialect in the first line (task_67).
NAMING = "naming"

#: Everything our own engine answers.
ALL_FEATURES = frozenset({FORMAT, STEP, TRACE, GRAPHICS, LIMITS, NAMING})


def _executable(stem: str) -> str:
    """`stem` with the suffix this platform runs."""
    return f"{stem}.exe" if os.name == "nt" else stem


@dataclass(frozen=True)
class Engine:
    """One engine: how the window names it, which file it is, what it can do."""

    #: The value stored under `view/engine`, and the way the tests and the
    #: window pass an engine around.
    key: str
    #: The name for the user: the button's tooltip, the status bar, the
    #: «пределы» note.
    title: str
    #: The file, looked for beside the window and in the build trees (`paths`).
    file_name: str
    #: The picture of the engine switch *while this engine is the one that runs*
    #: (`assets`): `u.png` for ours, `d.png` for the original.
    icon: str
    #: What a front-end command may ask of it.
    features: frozenset[str]

    def has(self, feature: str) -> bool:
        """Whether this engine answers `feature`; `""` is «nothing is needed»."""
        return not feature or feature in self.features


#: Our own engine: this repository's `src/prlib`, the one the CLI drives.
OURS = Engine(
    key="u",
    title="Пролог-У",
    file_name=_executable("prologu"),
    icon="u",
    features=ALL_FEATURES,
)

#: The original Пролог-Д (`Ununus/prologd`, pinned in the top-level
#: `CMakeLists.txt`): the old dialect, the same engine the web service runs.
#: Its feature set is empty on purpose — not «unknown», but «answers none of
#: them»: its protocol has no `format`, no `step`, no `trace`, no graphics and no
#: `limits`, and it reads variable names the old way because that *is* the old
#: dialect.  What it does answer — `load`, `query`, `input`, `interrupt`, `quit`,
#: `НАЙТИВСЕ`, `ИМПОРТ` — is what the window offers on both engines.
ORIGINAL = Engine(
    key="d",
    title="Пролог-Д",
    file_name=_executable("prologd"),
    icon="d",
    features=frozenset(),
)

ENGINES: tuple[Engine, ...] = (OURS, ORIGINAL)

BY_KEY: dict[str, Engine] = {engine.key: engine for engine in ENGINES}

#: Without a choice — or with one the file no longer knows — our own engine runs.
DEFAULT = OURS


def by_key(key: object) -> Engine:
    """The engine a stored value names; anything else is `DEFAULT`.

    Tolerant like every other reader of the ini: a key this build does not know
    is not a reason to refuse to start.
    """
    return BY_KEY.get(str(key).strip().lower(), DEFAULT)


def other(engine: Engine) -> Engine:
    """The engine the switch button moves to — two of them, one button."""
    return ORIGINAL if engine is OURS else OURS


def of_path(path: str) -> Engine | None:
    """The engine a file name names, or `None` when it names neither.

    The two places a *particular binary* is given by hand — `--exe` and task_46's
    removed «Интерпретатор» row — may name it: `…\\prologd.exe` means «Пролог-Д»
    whatever the settings say, because a developer who built the other engine and
    named that file does not want our own started from its folder.
    """
    name = str(path).strip().replace("\\", "/").rsplit("/", 1)[-1].lower()
    for engine in ENGINES:
        if name and name == engine.file_name.lower():
            return engine
    return None


def launch(pin: str, chosen: str) -> tuple[Engine, str]:
    """What a window starts with: the engine, and the folder to look for it in.

    Three answers, and the order is the whole rule:

    1. `pin` — the `--exe` of this launch, or the value task_46's removed
       «Интерпретатор» row still holds in the file.  A name that is one of the
       two engine files *is* the engine (`of_path`), and the folder it lies in is
       where the other one is looked for as well: the pair was built together;
    2. `chosen` — `view/engine`, written by the button on the toolbar;
    3. our own engine.

    The second half of the pair is the folder, `""` when nothing was pinned —
    then `paths.interpreter` searches the usual places.  `main.py`, which refuses
    to start without the file, and the window, which starts with it, both call
    this: one rule, so they cannot disagree about which binary was asked for.
    """
    text = str(pin or "").strip()
    parent = str(pathlib.PurePath(text).parent) if text else ""
    folder = "" if parent in ("", ".") else parent
    return of_path(text) or by_key(chosen), folder
