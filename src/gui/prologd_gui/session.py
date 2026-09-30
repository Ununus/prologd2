"""Qt bridge to the interpreter process.

One `PrologSession` owns one `prologd --protocol json` child and translates its
event stream into signals.  Keeping the interpreter in a separate process is what
makes Ctrl+C, a crash in a user program and an interpreter restart cheap: the GUI
never shares memory or a call stack with it.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, Signal

from . import protocol
from .keywords import Keywords


class PrologSession(QObject):
    """A running interpreter session."""

    #: The interpreter is up; carries its version string.
    ready = Signal(str)
    #: Program output (`ВЫВОД`, query results), already decoded.
    output = Signal(str)
    #: A query finished; True when it found at least one solution.
    result = Signal(bool)
    #: The interpreter waits for input; carries "token", "line" or "codepoint".
    input_request = Signal(str)
    #: A diagnostic; a kind ("parse", "runtime", "protocol"), its severity
    #: ("error" or "warning"; protocol 4 — an older interpreter sends none, and
    #: then the default is an error), a text, and where it happened — a
    #: `protocol.Position`, or None when there is nothing to point at (a goal
    #: typed at the prompt, an error with no clause).
    failed = Signal(str, str, str, object)
    #: The trace of `ТРАССА`, one line at a time (protocol 3).
    trace = Signal(str)
    #: A stepped run stopped at a point: a `protocol.StepPoint`.
    stepped = Signal(object)
    #: The session ended; carries the process exit code.
    ended = Signal(int)

    #: The reserved names from the `ready` event.  Empty until a session is up,
    #: and stays empty with an interpreter older than protocol 2 — which is why
    #: every consumer must treat an empty table as "no keyword list available".
    keywords = Keywords()

    def __init__(self, executable: str, includes: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._executable = executable
        self._includes = list(includes or [])
        self._decoder = protocol.Decoder()
        self._awaiting_input = False
        self._paused = False
        # Requests issued before the interpreter announced itself are held back:
        # writing into a process that is still starting loses them.
        self._ready = False
        self._pending: list[bytes] = []

        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Starts a *fresh* interpreter.

        This is how a front-end gets a clean slate: the clause database, the
        `СЛУЧ` seed, `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` redirection and the preloaded `$`
        input lines all live in the process.  Loading a second program into a
        session that already ran one accumulates the clauses and duplicates every
        solution, so a run starts a new process.

        A live process is stopped first, so a caller can treat this as "give me a
        clean interpreter" without checking the state itself.
        """
        if self.is_running():
            self.stop()
        arguments = ["--protocol", "json"]
        for directory in self._includes:
            arguments += ["-I", directory]
        self._decoder = protocol.Decoder()
        self._awaiting_input = False
        self._paused = False
        self._ready = False
        self._pending.clear()
        self._process.setProgram(self._executable)
        self._process.setArguments(arguments)
        self._process.start()

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def stop(self, grace_ms: int = 200) -> None:
        """Ends the session and waits until the process is really gone.

        A runaway query cannot be interrupted politely, and `terminate()` alone
        does not reliably end a console child on Windows: it may keep running,
        and the next `start()` would then refuse to launch with "Process is
        already running".  So: a short grace period, then `kill()`, then wait for
        Qt to report the process finished.
        """
        if not self.is_running():
            return
        self._process.terminate()
        if not self._process.waitForFinished(grace_ms):
            self._process.kill()
            self._process.waitForFinished(2000)
        self._ready = False
        self._awaiting_input = False
        self._paused = False

    # -- requests ----------------------------------------------------------
    def load_text(self, text: str, name: str = "<buffer>", *, step: bool = False,
                  trace: bool = False) -> None:
        self._send(protocol.load_text(text, name, step=step, trace=trace))

    def load_file(self, path: str, *, step: bool = False, trace: bool = False) -> None:
        self._send(protocol.load_file(path, step=step, trace=trace))

    def run_query(self, text: str, *, step: bool = False, trace: bool = False) -> None:
        self._send(protocol.query(text, step=step, trace=trace))

    def answer_input(self, text: str) -> None:
        self._awaiting_input = False
        self._send(protocol.input_answer(text))

    def answer_step(self, action: str) -> None:
        """Continues, steps over or stops a paused step point.

        Only meaningful while the interpreter is waiting inside a step point; a
        `step` request with nothing waiting is a protocol error, and the window
        asks for one only when the panel says a step is paused.
        """
        self._paused = False
        self._send(protocol.step_answer(action))

    def paused(self) -> bool:
        """True while the interpreter waits at a step point."""
        return self._paused

    def interrupt(self) -> None:
        self._send(protocol.interrupt())

    def quit(self) -> None:
        self._send(protocol.quit_session())

    # -- internals ---------------------------------------------------------
    def _send(self, payload: bytes) -> None:
        if not self.is_running():
            self.failed.emit("session", "интерпретатор не запущен", None)
            return
        if not self._ready:
            self._pending.append(payload)
            return
        self._process.write(payload)

    def _flush_pending(self) -> None:
        queued = self._pending
        self._pending = []
        for payload in queued:
            self._process.write(payload)

    def _on_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput())
        for event in self._decoder.feed(chunk):
            self._dispatch(event)

    def _dispatch(self, event: dict) -> None:
        name = event.get("event")
        if name == "ready":
            self.keywords = Keywords.from_event(event)
            self._ready = True
            self._flush_pending()
            self.ready.emit(str(event.get("version", "")))
        elif name == "output":
            self.output.emit(str(event.get("text", "")))
        elif name == "result":
            self.result.emit(bool(event.get("found", False)))
        elif name == "input_request":
            self._awaiting_input = True
            self.input_request.emit(str(event.get("kind", "line")))
        elif name == "step":
            # The interpreter is inside this point and waits for `answer_step`.
            self._paused = True
            self.stepped.emit(
                protocol.StepPoint(
                    action=str(event.get("action", "call")),
                    goal=str(event.get("goal", "")),
                    depth=int(event.get("depth", 0)),
                    position=protocol.Position.from_event(event),
                )
            )
        elif name == "trace":
            self.trace.emit(str(event.get("text", "")))
        elif name == "error":
            self.failed.emit(
                str(event.get("kind", "")),
                str(event.get("severity", "error")),
                str(event.get("message", "")),
                protocol.Position.from_event(event),
            )
        elif name == "bye":
            pass  # the process exit reports the end of the session
        else:
            self.failed.emit("protocol", "error", f"неизвестное событие: {name}", None)

    def _on_finished(self, exit_code: int, _status) -> None:
        for event in self._decoder.feed(b"\n"):
            self._dispatch(event)
        self._ready = False
        self.ended.emit(exit_code)
