"""Wire format of the `prologu --protocol json` session.

Requests are JSON objects, one per line, and events come back the same way.  The
C++ side of the contract lives in `src/cli/protocol.cpp`; keep the two in step.

This module is deliberately free of Qt so it can be tested headlessly (see
`tests/protocol_smoke.py`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator

#: Bumped by the interpreter whenever a request or an event changes shape.
#: 2: the `ready` event carries `keywords` (the reserved names and their arities).
#: 3: `step` events and the `step` request, `trace` events, positions on `error`,
#:    and the `step`/`trace` flags of `load` and `query`.
#: 5: `load` takes `questions` — `false` loads a program without running its own
#:    `?`-statements (the editor's margin runs one query alone, task_36).
#: 6: `format` for the formatter; the answer is a `formatted` event (task_30).
#: 7: the modes of `format` are `line`, `soft` and `hard`.
#: 8: `loaded` — a load and the program's own `?`-statements are over.
#: 9: `load` takes `limits` — the step, depth and НАЙТИВСЕ caps of the run
#:    (`maxSteps`, `maxDepth`, `maxFindall`; `0` is «без предела»), so a window can
#:    stop a runaway program the way the command line does (task_46).  A field of
#:    the wrong *type* is answered with an `error` event instead of ending the
#:    session.
#: 10: `graphics` events — every drawing primitive as the program calls it, a cell,
#:    a segment or a box — and the `graphics` request with `snapshot`, answered
#:    with the whole `bitmap` (task_45), for a window that was not open while the
#:    picture was made.
#: 11: `load` takes `printQuestions` — a run question echoes itself (`?цель.`)
#:    before its answer, the way `-q` does on the command line (task_46).
#: 12: `load`, `query` and `format` carry the naming mode (`vars`, task_67).
#: 13: `load` and `query` take the `screen` the picture is drawn on (`width` and
#:    `height`), and `ready` carries the engine's own screen (task_73).
#: 14: `screen` is also an *event*: the canvas a program names with
#:    `:- ХОЛСТ(Высота, Ширина).`, sent as soon as the directive is applied, so a
#:    window can take the size before the first primitive (ADR-035).
#: 15: `format` takes `names`: the mode to *print* the names in, so the same
#:    request converts a program between the two dialects (task_99).
PROTOCOL_VERSION = 15

#: Event names the interpreter emits.
EVENTS = ("ready", "output", "result", "input_request", "step", "trace", "graphics",
          "bitmap", "screen", "error", "bye")

#: What the solver was doing at a step point, as the `step` event spells it.
STEP_ACTIONS = ("call", "exit", "redo", "fail")

#: The answers a paused step accepts.
STEP_ANSWERS = ("into", "over", "continue", "stop")


@dataclass(frozen=True)
class Position:
    """Where something stands in the source, as the protocol reports it.

    Sent as fields of their own so a front-end never parses `file:line:column:`
    out of a message — and omitted when there is nothing to point at (a goal
    typed at the prompt, an error with no clause).
    """

    file: str = ""
    line: int = 0
    column: int = 0

    @classmethod
    def from_event(cls, event: dict) -> "Position | None":
        """The position of a `step` or `error` event; `None` when it has none."""
        name = event.get("file")
        if not name:
            return None
        return cls(str(name), int(event.get("line", 0)), int(event.get("column", 0)))

    def where(self) -> str:
        """`path:line:column`, or an empty string when there is no position."""
        if not self.file:
            return ""
        return f"{self.file}:{self.line}:{self.column}"


@dataclass(frozen=True)
class StepPoint:
    """One point of a stepped run.

    `goal` is empty for `exit`: the goal that succeeded is the one the matching
    `call` reported, and a front-end keeps its own stack — that stack is exactly
    what an `exit` pops.
    """

    action: str
    goal: str
    depth: int
    position: Position | None = None


def encode_request(**fields: Any) -> bytes:
    """Encodes one request, ready to be written to the session's stdin."""
    return (json.dumps(fields, ensure_ascii=False) + "\n").encode("utf-8")


def load_text(text: str, name: str = "<buffer>", *, step: bool = False,
              trace: bool = False, questions: bool = True,
              print_questions: bool = False,
              limits: dict | None = None,
              variable_mode: int = 0,
              screen: tuple[int, int] | None = None) -> bytes:
    """Loads program text (the editor buffer).

    `step` makes the run stop at its first step point and wait for a `step`
    request; `trace` turns `ТРАССА` on, so the trace arrives as `trace` events.
    `questions=False` loads the program *without* running its own
    `?`-statements: what the editor's margin needs to answer one clicked query
    alone (task_36).  `print_questions` echoes each run question (`?цель.`) as an
    `output` event before its answer (protocol 11) — the two flags are apart
    because running the lesson and seeing the questions on the pane are two
    choices.  The flags are left off the wire when they are false, which keeps a
    plain run looking exactly as it did before protocol 3.

    `limits` are the guards of the run (protocol 9): `maxSteps`, `maxDepth`,
    `maxFindall`, each `0` for «без предела».  The *wall-clock* timeout is not
    here — it is the front-end's own clock (task_46).

    `variable_mode` is how this run reads names that no marker in the file has
    settled (protocol 12, task_67): 0 is the ISO reading, 1 and 2 the old
    dialect's, and a file's own `:- ИМЕНА(N).` line wins over all of them.

    `screen` is the size of the picture the run draws on (protocol 13, task_73).
    """
    return encode_request(
        cmd="load", text=text, name=name,
        **_flags(step=step, trace=trace, questions=questions,
                 print_questions=print_questions),
        **_limits(limits),
        **_variable_mode(variable_mode),
        **_screen(screen),
    )


def load_file(path: str, *, step: bool = False, trace: bool = False,
              questions: bool = True, print_questions: bool = False,
              limits: dict | None = None, variable_mode: int = 0,
              screen: tuple[int, int] | None = None) -> bytes:
    """Loads a program from disk; imports resolve against `-I` directories."""
    return encode_request(
        cmd="load", path=path,
        **_flags(step=step, trace=trace, questions=questions,
                 print_questions=print_questions),
        **_limits(limits),
        **_variable_mode(variable_mode),
        **_screen(screen),
    )


def query(text: str, *, step: bool = False, trace: bool = False,
          variable_mode: int = 0, screen: tuple[int, int] | None = None) -> bytes:
    """Runs one statement, usually `?Goal.`.

    `variable_mode` is how *this statement* reads names (task_67): a question typed
    into the goal line or clicked on a margin marker arrives on its own, without a
    file's first line, so it has to be told what the program it asks reads —
    otherwise `?студент(Вова, Корчагин).` of a mode-1 program would read the two
    names as variables instead of the constants the file meant.

    `screen` is the size of the picture this statement draws on (protocol 13): the
    graphics window is live while a question is answered, so a question carries the
    screen the question before it used.
    """
    return encode_request(cmd="query", text=text, **_flags(step=step, trace=trace),
                          **_variable_mode(variable_mode), **_screen(screen))


def graphics_snapshot() -> bytes:
    """Asks for the picture drawn so far (protocol 10, task_45).

    The primitives arrive as they are drawn, so a window that is open follows the
    program; a window that opens in the middle of one asks for this instead of
    starting blank.  The answer is a `bitmap` event with the whole screen.
    """
    return encode_request(cmd="graphics", snapshot=True)


def step_answer(action: str) -> bytes:
    """Answers a paused step point: `into`, `over`, `continue` or `stop`."""
    if action not in STEP_ANSWERS:
        raise ValueError(f"unknown step action: {action!r}")
    return encode_request(cmd="step", action=action)


def format_text(
    text: str,
    *,
    mode: str = "soft",
    width: int = 80,
    indent: int = 1,
    unit: str = "tab",
    selection: bool = False,
    name: str = "<format>",
    variable_mode: int = 0,
    names: int | None = None,
) -> bytes:
    """Asks the interpreter to lay `text` out; the answer is `formatted`.

    The formatter lives in prlib (the grammar is there once already), so the
    window sends the buffer and receives the laid-out text back.  `selection`
    tells it the text is a fragment: one that breaks off in the middle of a body
    comes back formatted up to its last complete goal, the rest untouched
    (task_30).  `names` is the mode to *print* the names in — the same request
    then converts a program between the two dialects (protocol 15, task_99);
    `variable_mode` stays «how the text is read».  Flags that are the defaults are
    left off the wire.
    """
    if mode not in ("line", "soft", "hard"):
        raise ValueError(f"unknown format mode: {mode!r}")
    fields: dict[str, Any] = {"cmd": "format", "text": text, "mode": mode}
    if width != 80:
        fields["width"] = width
    if indent != 1:
        fields["indent"] = indent
    if unit != "tab":
        fields["unit"] = unit
    if selection:
        fields["selection"] = True
    if name != "<format>":
        fields["name"] = name
    if names is not None:
        fields["names"] = int(names)
    fields.update(_variable_mode(variable_mode))
    return encode_request(**fields)


def _flags(*, step: bool = False, trace: bool = False, questions: bool = True,
           print_questions: bool = False) -> dict:
    """Only the flags that are on: a false one would be noise on the wire."""
    flags: dict[str, bool] = {}
    if step:
        flags["step"] = True
    if trace:
        flags["trace"] = True
    if not questions:
        flags["questions"] = False
    if print_questions:
        flags["printQuestions"] = True
    return flags


def _limits(limits: dict | None) -> dict:
    """The `limits` object of a `load`, or nothing when they are the defaults.

    Only the ones that were asked for travel: a window that sets no limit sends
    no `limits` at all, which is what keeps an old front-end's traffic identical
    to what it was before protocol 9.
    """
    if not limits:
        return {}
    asked = {name: int(value) for name, value in limits.items() if int(value) > 0}
    return {"limits": asked} if asked else {}


def _variable_mode(mode: int) -> dict:
    """The naming mode of a run or of a formatting request (protocol 12, task_67).

    Mode 0 is left off the wire: it is the interpreter's own default, so a zero
    would be a second way of saying «nothing was asked for».  A file's own
    `:- ИМЕНА(N).` line still wins over whatever travels here.
    """
    return {"vars": int(mode)} if int(mode) else {}


def _screen(size: tuple[int, int] | None) -> dict:
    """The screen the picture is drawn on (protocol 13, task_73).

    The engine's own screen is 600 × 600; a front-end that shows another size names
    it here, and the buffer becomes that size — cleared, because the picture belongs
    to the run that drew it.  `None` leaves the engine's default alone, the way a
    zero naming mode is left off the wire.
    """
    if size is None:
        return {}
    width, height = size
    return {"screen": {"width": int(width), "height": int(height)}}


def input_answer(text: str) -> bytes:
    """Answers the pending `input_request`."""
    return encode_request(cmd="input", text=text)


def interrupt() -> bytes:
    """Asks for a stop; effective while the interpreter waits for input."""
    return encode_request(cmd="interrupt")


def quit_session() -> bytes:
    """Ends the session; the interpreter answers with `bye`."""
    return encode_request(cmd="quit")


class Decoder:
    """Turns the byte stream of events into whole JSON objects."""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: bytes) -> Iterator[dict]:
        self._buffer += chunk.decode("utf-8", errors="replace")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                yield {
                    "event": "error",
                    "kind": "protocol",
                    "message": f"нераспознанный ответ: {line}",
                }
                continue
            if isinstance(event, dict):
                yield event
