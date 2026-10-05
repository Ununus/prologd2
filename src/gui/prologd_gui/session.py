"""Qt bridge to the interpreter process.

One `PrologSession` owns one `prologd --protocol json` child and translates its
event stream into signals.  Keeping the interpreter in a separate process is what
makes Ctrl+C, a crash in a user program and an interpreter restart cheap: the GUI
never shares memory or a call stack with it.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, Signal

from . import graphics, protocol
from .keywords import Keywords


def read_keywords(executable: str, timeout_ms: int = 4000) -> Keywords:
    """The reserved names without a session: one `prologd --list-keywords` run.

    The window needs the table for completion, colouring and the shortcut sheet
    *before* anything is run, and a window that has only been *opened* must not
    keep an interpreter alive — so the names are fetched once with the same
    query the CLI answers, and the first real session replaces the table with
    the `ready` event's copy (one source of truth either way).  An interpreter
    too old to know the option leaves the table empty, which is the state every
    consumer already handles.
    """
    process = QProcess()
    process.start(executable, ["--list-keywords"])
    finished = process.waitForFinished(timeout_ms)
    if (
        not finished
        or process.exitStatus() != QProcess.ExitStatus.NormalExit
        or process.exitCode() != 0
    ):
        process.kill()
        process.waitForFinished(1000)
        return Keywords()
    stdout = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
    return Keywords.from_list_lines(stdout)


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
    #: The laid-out text of a `format` request, and whether it differs from what
    #: was sent (protocol 6, task_30).
    formatted = Signal(str, bool)
    #: A stepped run stopped at a point: a `protocol.StepPoint`.
    stepped = Signal(object)
    #: A load and the program's own `?`-statements are over (protocol 8).  It is
    #: what tells a front-end that a run *without* questions finished.
    loaded = Signal()
    #: One drawing primitive, as the program called it (protocol 10): a cell, a
    #: segment or a box, in the order the program drew them (task_45).
    drawn = Signal(dict)
    #: The whole picture, for a window that was not open while it was drawn:
    #: width, height and the raw little-endian colour values.
    bitmap = Signal(int, int, bytes)
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
        #: The child's working directory (task_46); `""` means «inherit the
        #: window's own folder», which is what a process always did before.
        self._working_directory = ""
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

    def set_includes(self, includes: list[str] | None) -> None:
        """Replaces the `-I` directories (task_29's dialog).

        A session already running keeps the ones it was started with: the list is
        put on the command line, and a process cannot be re-argued.  «Запустить»
        starts a fresh session anyway, which is when the new path takes effect.
        """
        self._includes = [str(directory) for directory in includes or [] if str(directory)]

    def set_executable(self, executable: str) -> None:
        """Replaces the program the next `start()` launches (task_46).

        Like `-I`, the path is fixed once a process is up: a running session keeps
        the interpreter it was started with, and the next `start()` — a run always
        starts one — picks the new one up.
        """
        self._executable = str(executable)

    def executable(self) -> str:
        """The program `start()` launches (what a test reads back)."""
        return self._executable

    def set_working_directory(self, directory: str) -> None:
        """Replaces the child's working directory; `""` is «inherit» (task_46)."""
        self._working_directory = str(directory or "")

    def working_directory(self) -> str:
        """The working directory the next `start()` gives the child; `""` = inherit."""
        return self._working_directory

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Starts a *fresh* interpreter.

        This is how a front-end gets a clean slate: the clause database, the
        `СЛУЧ` seed and the `ЗАПИСЬ_В`/`ЧТЕНИЕ_ИЗ` redirection all live in the
        process.  Loading a second program into a
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
        # The relative paths of a program (`ЗАПИСЬ_В`, `ЧТЕНИЕ_ИЗ`) start here;
        # `""` leaves the setting unset and the child inherits the window's own
        # folder, as it always did (task_46).
        self._process.setWorkingDirectory(self._working_directory)
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
                  trace: bool = False, questions: bool = True,
                  print_questions: bool = False,
                  limits: dict | None = None) -> None:
        self._send(protocol.load_text(text, name, step=step, trace=trace,
                                      questions=questions,
                                      print_questions=print_questions,
                                      limits=limits))

    def load_file(self, path: str, *, step: bool = False, trace: bool = False,
                  questions: bool = True, print_questions: bool = False,
                  limits: dict | None = None) -> None:
        self._send(protocol.load_file(path, step=step, trace=trace, questions=questions,
                                      print_questions=print_questions,
                                      limits=limits))

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

    def request_graphics_snapshot(self) -> None:
        """Asks for the picture drawn so far (protocol 10, task_45).

        A window that opens in the middle of a run has missed every primitive
        already drawn; this is how it catches up, and the answer is a `bitmap`
        signal.
        """
        self._send(protocol.graphics_snapshot())

    def quit(self) -> None:
        self._send(protocol.quit_session())

    def format_text(
        self,
        text: str,
        *,
        mode: str = "soft",
        width: int = 80,
        indent: int = 1,
        unit: str = "tab",
        selection: bool = False,
        name: str = "<format>",
    ) -> None:
        """Asks the interpreter to lay the text out; `formatted` answers it.

        The formatter lives in prlib, next to the grammar it has to understand,
        so the request travels over the protocol like everything else (protocol
        6).  It needs no engine and is answered between queries; the reply is
        either a `formatted` event or `error` events of kind `format`.
        """
        self._send(
            protocol.format_text(
                text, mode=mode, width=width, indent=indent, unit=unit,
                selection=selection, name=name,
            )
        )

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
            # The query this step belonged to has answered, so nothing is waiting
            # for a `step` answer any more (task_49).  A step point is *inside* a
            # query: `result` cannot arrive while one is pending, and the events
            # below are the end of the run wherever it was paused — the same three
            # places that end a run.
            self._paused = False
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
        elif name == "formatted":
            self.formatted.emit(str(event.get("text", "")), bool(event.get("changed", False)))
        elif name == "loaded":
            self._paused = False  # a load that ends ends the pause with it
            self.loaded.emit()
        elif name == "graphics":
            # The operation has to be one this version knows: a picture with a
            # primitive quietly missing looks correct and is not, so an unknown
            # one is reported the way an unknown event is.
            op = str(event.get("op", ""))
            if op not in graphics.GRAPHICS_OPS:
                self.failed.emit(
                    "protocol", "error", f"неизвестная графическая операция: {op}", None
                )
                return
            self.drawn.emit(dict(event))
        elif name == "bitmap":
            try:
                width, height, data = graphics.decode_bitmap(event)
            except ValueError as broken:
                self.failed.emit("protocol", "error", str(broken), None)
                return
            self.bitmap.emit(width, height, data)
        elif name == "error":
            # An error ends the query it belongs to, so a step point cannot still
            # be pending — and this is the event a user's «Стоп» arrives as while
            # a step was waiting (the interrupted query).  A *warning* is not an
            # end of anything, which is why it is left out.
            if str(event.get("severity", "error")) != "warning":
                self._paused = False
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
        # The process is gone, so no step point can be pending: a pause that
        # outlived its interpreter would turn the next «Запуск» into a `step`
        # request (task_49).
        self._paused = False
        self.ended.emit(exit_code)
