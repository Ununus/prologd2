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
  "\"protocol\":5"
  "\"keywords\":"
  "{\"event\":\"result\",\"found\":true}"
  "{\"event\":\"output\",\"text\":\"X=1\\nX=2\\n\"}"
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
