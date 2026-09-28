"""Qt bridge to the interpreter process.

One `PrologSession` owns one `prologd --protocol json` child and translates its
event stream into signals.  Keeping the interpreter in a separate process is what
makes Ctrl+C, a crash in a user program and an interpreter restart cheap: the GUI
never shares memory or a call stack with it.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, Signal

from . import protocol


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
    #: A diagnostic; carries a kind ("parse", "runtime", "protocol") and a text.
    failed = Signal(str, str)
    #: The session ended; carries the process exit code.
    ended = Signal(int)

    def __init__(self, executable: str, includes: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._executable = executable
        self._includes = list(includes or [])
        self._decoder = protocol.Decoder()
        self._awaiting_input = False

        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        arguments = ["--protocol", "json"]
        for directory in self._includes:
            arguments += ["-I", directory]
        self._decoder = protocol.Decoder()
        self._awaiting_input = False
        self._process.setProgram(self._executable)
        self._process.setArguments(arguments)
        self._process.start()

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def stop(self) -> None:
        """Ends the session.  A runaway query cannot be interrupted politely, so
        the process is terminated and started again when needed."""
        if self.is_running():
            self._process.terminate()
            if not self._process.waitForFinished(2000):
                self._process.kill()

    # -- requests ----------------------------------------------------------
    def load_text(self, text: str, name: str = "<buffer>") -> None:
        self._send(protocol.load_text(text, name))

    def load_file(self, path: str) -> None:
        self._send(protocol.load_file(path))

    def run_query(self, text: str) -> None:
        self._send(protocol.query(text))

    def answer_input(self, text: str) -> None:
        self._awaiting_input = False
        self._send(protocol.input_answer(text))

    def interrupt(self) -> None:
        self._send(protocol.interrupt())

    def quit(self) -> None:
        self._send(protocol.quit_session())

    # -- internals ---------------------------------------------------------
    def _send(self, payload: bytes) -> None:
        if not self.is_running():
            self.failed.emit("session", "интерпретатор не запущен")
            return
        self._process.write(payload)

    def _on_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput())
        for event in self._decoder.feed(chunk):
            self._dispatch(event)

    def _dispatch(self, event: dict) -> None:
        name = event.get("event")
        if name == "ready":
            self.ready.emit(str(event.get("version", "")))
        elif name == "output":
            self.output.emit(str(event.get("text", "")))
        elif name == "result":
            self.result.emit(bool(event.get("found", False)))
        elif name == "input_request":
            self._awaiting_input = True
            self.input_request.emit(str(event.get("kind", "line")))
        elif name == "error":
            self.failed.emit(str(event.get("kind", "")), str(event.get("message", "")))
        elif name == "bye":
            pass  # the process exit reports the end of the session
        else:
            self.failed.emit("protocol", f"неизвестное событие: {name}")

    def _on_finished(self, exit_code: int, _status) -> None:
        for event in self._decoder.feed(b"\n"):
            self._dispatch(event)
        self.ended.emit(exit_code)
