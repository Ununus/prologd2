"""Wire format of the `prologd --protocol json` session.

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
PROTOCOL_VERSION = 3

#: Event names the interpreter emits.
EVENTS = ("ready", "output", "result", "input_request", "step", "trace", "error", "bye")

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
              trace: bool = False) -> bytes:
    """Loads program text (the editor buffer).

    `step` makes the run stop at its first step point and wait for a `step`
    request; `trace` turns `ТРАССА` on, so the trace arrives as `trace` events.
    The flags are left off the wire when they are false, which keeps a plain run
    looking exactly as it did before protocol 3.
    """
    return encode_request(cmd="load", text=text, name=name, **_flags(step=step, trace=trace))


def load_file(path: str, *, step: bool = False, trace: bool = False) -> bytes:
    """Loads a program from disk; imports resolve against `-I` directories."""
    return encode_request(cmd="load", path=path, **_flags(step=step, trace=trace))


def query(text: str, *, step: bool = False, trace: bool = False) -> bytes:
    """Runs one statement, usually `?Goal.`."""
    return encode_request(cmd="query", text=text, **_flags(step=step, trace=trace))


def step_answer(action: str) -> bytes:
    """Answers a paused step point: `into`, `over`, `continue` or `stop`."""
    if action not in STEP_ANSWERS:
        raise ValueError(f"unknown step action: {action!r}")
    return encode_request(cmd="step", action=action)


def _flags(*, step: bool = False, trace: bool = False) -> dict:
    """Only the flags that are on: a false one would be noise on the wire."""
    flags: dict[str, bool] = {}
    if step:
        flags["step"] = True
    if trace:
        flags["trace"] = True
    return flags


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
