cmake_minimum_required(VERSION 3.24)

# Drives the console front-end in `--protocol json` mode and checks the event
# stream.  Run by CTest as `cli_json_protocol`; parameters are the executable
# and a scratch directory.
#
# The requests are written to a file and fed through `INPUT_FILE`, which is the
# only way to hand bytes to a child process unchanged: a shell pipeline would
# re-encode the Cyrillic text into the console code page.
#
# The *expectations* here are ASCII only, and that is deliberate: `execute_process`
# decodes the child's stdout with the console code page, so a Cyrillic needle
# matches in a UTF-8 console (code page 65001) and nowhere else.  The Cyrillic
# side — the trace text, the goal of a step, the message of a diagnostic — is
# covered by the Catch2 tests, which compare inside one process.

if(NOT PROLOGD_EXE OR NOT WORK_DIR)
  message(FATAL_ERROR "PROLOGD_EXE and WORK_DIR are required")
endif()

set(session "${WORK_DIR}/protocol_session.jsonl")

# --- a full session: load, query, interactive input, quit ---------------------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\nфакт(2).\\n?факт(X).\\n\"}\n"
  "{\"cmd\":\"query\",\"text\":\"?факт(2).\"}\n"
  "{\"cmd\":\"load\",\"text\":\"?ВВОДСТР(X), ВЫВОД(X).\\n\"}\n"
  "{\"cmd\":\"input\",\"text\":\"ok\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  ERROR_VARIABLE cli_errors
  RESULT_VARIABLE exit_code)

set(expected_events
  "{\"event\":\"ready\","
  "\"protocol\":11"
  "\"keywords\":"
  "{\"event\":\"result\",\"found\":true}"
  "{\"event\":\"loaded\"}"
  # One event per written line since task_49, so the two answers of `?факт(X).`
  # arrive separately — and *before* the `result` that ends the query.
  "{\"event\":\"output\",\"text\":\"X=1\\n\"}"
  "{\"event\":\"output\",\"text\":\"X=2\\n\"}"
  "{\"event\":\"input_request\",\"kind\":\"line\"}"
  "{\"event\":\"output\",\"text\":\"okX=ok\\n\"}"
  "{\"event\":\"bye\"}")

foreach(event IN LISTS expected_events)
  string(FIND "${events}" "${event}" position)
  if(position EQUAL -1)
    message(FATAL_ERROR "Missing event ${event}\n--- got ---\n${events}")
  endif()
endforeach()

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "Session exit code ${exit_code}, stderr: ${cli_errors}")
endif()

# --- a quiet load: the program's own `?`-statements do not run ----------------
# This is how the editor's margin answers one clicked query alone (task_36): the
# program is loaded for its clauses, and only the query that was asked for runs.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(X).\\n\",\"questions\":false}\n"
  "{\"cmd\":\"query\",\"text\":\"?факт(X).\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

# Exactly one answer and one result may appear: the quiet load's own `?факт(X).`
# would have added an `X=1` of its own.
string(REGEX MATCHALL "\\{\"event\":\"output\",\"text\":\"X=1" answers "${events}")
list(LENGTH answers answer_count)
if(NOT answer_count EQUAL 1)
  message(FATAL_ERROR "Expected exactly one answer from a quiet load, got ${answer_count}\n--- got ---\n${events}")
endif()
string(REGEX MATCHALL "\\{\"event\":\"result\",\"found\":true\\}" results "${events}")
list(LENGTH results result_count)
if(NOT result_count EQUAL 1)
  message(FATAL_ERROR "Expected exactly one result event from a quiet load, got ${result_count}\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "Quiet-load session exit code ${exit_code}")
endif()

# --- printQuestions: a run question echoes itself before its answer -----------
# task_46's split: `questions` runs the program's own `?`-statements, and
# `printQuestions` (protocol 11) makes each one print itself the way `-q` does.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(X).\\n\",\"printQuestions\":true}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "{\"event\":\"output\",\"text\":\"?факт(X).\\n\"}" echoed)
string(FIND "${events}" "{\"event\":\"output\",\"text\":\"X=1\\n\"}" answer)
if(echoed EQUAL -1)
  message(FATAL_ERROR "The question did not echo itself\n--- got ---\n${events}")
endif()
if(NOT echoed LESS answer)
  message(FATAL_ERROR "The question echoed after its answer\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "printQuestions session exit code ${exit_code}")
endif()

# --- format: layout only, and a broken source is reported, not rewritten ------
# The formatter answers between queries and needs no engine (task_30).  Cyrillic
# needles cannot survive `execute_process`'s code page, so the check is about the
# shape of the events: a `formatted` event that says the text changed, a tab as
# the break's indent, and an `error` of kind `format` for a source that does not
# parse.  Neither request touches the exit code: the session itself did not fail.
file(WRITE "${session}"
  "{\"cmd\":\"format\",\"text\":\"факт(1).\\nцель(Х):-часть(Х), ещё(Х).\\n\",\"mode\":\"hard\"}\n"
  "{\"cmd\":\"format\",\"text\":\"цель(Х:-часть(Х).\\n\",\"mode\":\"hard\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"event\":\"formatted\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "Expected a formatted event\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"changed\":true" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The formatted event did not say the text changed\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\\t" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The hard format did not indent the break with a tab\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"kind\":\"format\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A broken source must answer with an error event of kind format\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "The format session exited with ${exit_code}")
endif()

# --- a program that does not parse must be reported and set exit code 2 -------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"это не программа\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

# --- a parse error carries its position in fields of their own ----------------
string(FIND "${events}" "\"kind\":\"parse\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "Expected a parse error event\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"file\":\"<buffer>\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The parse error did not name the file it came from\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 2)
  message(FATAL_ERROR "Expected exit code 2 for a parse failure, got ${exit_code}")
endif()

# --- stepping: the run stops at a point and waits for a `step` request --------
# The pause *is* the wait: the session reads requests while the engine is inside
# the query, exactly as it does for `input_request`, so no new threading model
# was needed.  The program's `?`-statements run during the load, so the hook has
# to be armed around the load itself.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(X).\\n\",\"name\":\"step.pld\",\"step\":true}\n"
  "{\"cmd\":\"step\",\"action\":\"into\"}\n"
  "{\"cmd\":\"step\",\"action\":\"continue\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  ERROR_VARIABLE cli_errors
  RESULT_VARIABLE exit_code)

set(expected_steps
  "\"event\":\"step\""
  "\"action\":\"call\""
  "\"goal\":\""
  "\"depth\":0"
  "\"file\":\"step.pld\""
  "\"line\":2"
  "{\"event\":\"result\",\"found\":true}")

foreach(event IN LISTS expected_steps)
  string(FIND "${events}" "${event}" position)
  if(position EQUAL -1)
    message(FATAL_ERROR "Missing step event ${event}\n--- got ---\n${events}")
  endif()
endforeach()

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "Stepping exit code ${exit_code}, stderr: ${cli_errors}")
endif()

# --- `step` with `stop` ends the query, and the session says so ---------------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(X).\\n\",\"name\":\"stop.pld\",\"step\":true}\n"
  "{\"cmd\":\"step\",\"action\":\"stop\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"runtime\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A stopped step did not report a runtime error\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "Expected exit code 3 after a stopped step, got ${exit_code}")
endif()

# --- `interrupt` at a paused step point ends the pause -------------------------
# The window's «Остановить» relies on it: the pause is the one state the solver's
# own stop flag cannot reach, because nothing is solving there.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(X).\\n\",\"name\":\"pause.pld\",\"step\":true}\n"
  "{\"cmd\":\"interrupt\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"runtime\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "An interrupted pause did not report a runtime error\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "Expected exit code 3 after an interrupted pause, got ${exit_code}")
endif()

# --- a runtime error names the clause it happened in --------------------------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"дели(Х):-БОЛЬШЕ(1,#1/0#).\\n?дели(1).\\n\",\"name\":\"boom.pld\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"runtime\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The division by zero was not reported\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"file\":\"boom.pld\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The runtime error did not name its clause\n--- got ---\n${events}")
endif()

# --- the limits of a run travel with the load (protocol 9, task_46) ----------
# The message a limit prints is Cyrillic and cannot survive this file's code page,
# so the check is about the *shape*: a runaway with a step cap ends the run as a
# runtime error (exit code 3) instead of running for ever, and a limit of the
# wrong type is an error event that leaves the session alive.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"loop :- loop.\\n?loop.\\n\",\"limits\":{\"maxSteps\":1000}}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"runtime\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A runaway with a step cap was not stopped\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "Expected exit code 3 for a limit that fired, got ${exit_code}")
endif()

file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"fact(1).\\n\",\"limits\":{\"maxSteps\":-1}}\n"
  "{\"cmd\":\"load\",\"text\":\"?less(2,3).\\n\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"protocol\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A negative limit must be refused with an error event\n--- got ---\n${events}")
endif()
# The refused load defined nothing (`fact/1` never arrived), so the next request
# is a program of its own: what is being checked is that the session reads it.
string(FIND "${events}" "{\"event\":\"loaded\"}" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The session did not serve the request after a bad one\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A refused request must not change the exit code, got ${exit_code}")
endif()

# --- the program's output arrives as it is written, not at the end of the run --
# task_49: `ВЫВОД` went into one buffer per *request*, so a countdown that prints a
# line and then sleeps arrived as a single block when the program was over — a
# lesson's animation looked like a jump.  The check is about the *order and the
# count*: one `output` event per written line, and every one of them before the
# `loaded` that ends the load.  The program prints ASCII words, because the needles
# here have to survive `execute_process`'s code page.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"?ВЫВОД(\\\"one\\\"),ПС,ЖДИ(50),ВЫВОД(\\\"two\\\"),ПС,ЖДИ(50),ВЫВОД(\\\"three\\\"),ПС.\\n\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(REGEX MATCHALL "\\{\"event\":\"output\"" outputs "${events}")
list(LENGTH outputs output_count)
# Four: the three lines the program wrote, and the `ДА` the query answers with
# (also a line, so also an event of its own).
if(NOT output_count EQUAL 4)
  message(FATAL_ERROR "Expected one output event per written line (4 with the answer), got ${output_count}\n--- got ---\n${events}")
endif()

string(FIND "${events}" "{\"event\":\"output\",\"text\":\"one\\n\"}" one_position)
string(FIND "${events}" "{\"event\":\"output\",\"text\":\"two\\n\"}" two_position)
string(FIND "${events}" "{\"event\":\"output\",\"text\":\"three\\n\"}" three_position)
string(FIND "${events}" "{\"event\":\"loaded\"}" loaded_position)
if(one_position EQUAL -1 OR two_position EQUAL -1 OR three_position EQUAL -1 OR loaded_position EQUAL -1)
  message(FATAL_ERROR "The three lines did not arrive as three events\n--- got ---\n${events}")
endif()
if(NOT one_position LESS two_position)
  message(FATAL_ERROR "The second line did not follow the first\n--- got ---\n${events}")
endif()
if(NOT two_position LESS three_position)
  message(FATAL_ERROR "The third line did not follow the second\n--- got ---\n${events}")
endif()
if(NOT three_position LESS loaded_position)
  message(FATAL_ERROR "The lines must arrive as they are written, before the load ends\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "The live-output session exited with ${exit_code}")
endif()

# --- the trace goes out as events of its own ---------------------------------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n?факт(1).\\n\",\"trace\":true}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"event\":\"trace\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The trace did not arrive as trace events\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"text\":\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The trace events carry no text\n--- got ---\n${events}")
endif()

# --- the protocol owns stdin/stdout, so -i/-o/-e are refused ------------------
execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json -o "${WORK_DIR}/protocol_out.txt"
  INPUT_FILE "${session}"
  RESULT_VARIABLE exit_code)
if(NOT exit_code EQUAL 1)
  message(FATAL_ERROR "Expected exit code 1 for -o with --protocol json, got ${exit_code}")
endif()

# --- a query error names the query, not the buffer ----------------------------
# A front-end marks a line when a diagnostic names one; `<query>` says the error
# is in the statement it sent (the query line, a margin marker) and not in the
# program, whose line 1 was marked and shown for every failed query before.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\n\"}\n"
  "{\"cmd\":\"query\",\"text\":\"?is_whole(\\\"4\\\").\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"runtime\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A failed query was not reported as a runtime error\n--- got ---\n${events}")
endif()

string(FIND "${events}" "\"file\":\"<query>\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A query error must name the query\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"file\":\"<buffer>\"" position)
if(NOT position EQUAL -1)
  message(FATAL_ERROR "A query error must not name the buffer\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "Expected exit code 3 after a runtime error, got ${exit_code}")
endif()

# --- the drawing reaches the wire as events, and the snapshot as a bitmap ----
# task_45.  The primitives go out one by one, in the order the program drew
# them, and a window that opens later asks for the picture instead of starting
# blank.  The bitmap itself is checked by its *bytes*: the first cell of
# `?ТОЧКА(0, 0, 3)` is 3, so the four little-endian bytes `03 00 00 00` start
# the payload, whose base64 begins `AwAAAA`.
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"?ТОЧКА(0, 0, 3).\\n?ЛИНИЯ(1, 1, 8, 4, 5).\\n\"}\n"
  "{\"cmd\":\"graphics\",\"snapshot\":true}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A drawing session must end cleanly, got ${exit_code}: ${events}")
endif()

string(FIND "${events}" "\"op\":\"setPixel\"" point_position)
if(point_position EQUAL -1)
  message(FATAL_ERROR "A ТОЧКА did not reach the wire\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"op\":\"line\"" line_position)
if(line_position EQUAL -1)
  message(FATAL_ERROR "A ЛИНИЯ did not reach the wire\n--- got ---\n${events}")
endif()
if(NOT point_position LESS line_position)
  message(FATAL_ERROR "The primitives arrived out of order\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"color\":5" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The primitive did not carry its colour\n--- got ---\n${events}")
endif()

string(FIND "${events}" "\"event\":\"bitmap\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The snapshot did not come back\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"width\":1024" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The snapshot must be the engine's screen\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"height\":768" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The snapshot must be the engine's screen\n--- got ---\n${events}")
endif()
string(FIND "${events}" "\"data\":\"AwAAAA" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The bitmap does not carry the pixel that was drawn\n--- got ---\n${events}")
endif()

# Asking for anything else is the front-end's mistake, and it is answered: a
# blank window that looks correct is the one outcome worse than an error.
file(WRITE "${session}"
  "{\"cmd\":\"graphics\"}\n"
  "{\"cmd\":\"load\",\"text\":\"?less(2, 3).\\n\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"protocol\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "A graphics request without snapshot must be refused\n--- got ---\n${events}")
endif()
string(FIND "${events}" "{\"event\":\"loaded\"}" position)
if(position EQUAL -1)
  message(FATAL_ERROR "The session did not go on after the refusal\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A refused graphics request must not change the exit code, got ${exit_code}")
endif()
