cmake_minimum_required(VERSION 3.24)

# Drives the console front-end in `--protocol json` mode and checks the event
# stream.  Run by CTest as `cli_json_protocol`; parameters are the executable
# and a scratch directory.
#
# The requests are written to a file and fed through `INPUT_FILE`, which is the
# only way to hand bytes to a child process unchanged: a shell pipeline would
# re-encode the Cyrillic text into the console code page.

if(NOT PROLOGD_EXE OR NOT WORK_DIR)
  message(FATAL_ERROR "PROLOGD_EXE and WORK_DIR are required")
endif()

set(session "${WORK_DIR}/protocol_session.jsonl")

# --- a full session: load, query, interactive input, quit ---------------------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"факт(1).\\nфакт(2).\\n?факт(X).\\n\"}\n"
  "{\"cmd\":\"query\",\"text\":\"?факт(2).\"}\n"
  "{\"cmd\":\"load\",\"text\":\"?ВВОДСТР(X), ВЫВОД(X).\\n\"}\n"
  "{\"cmd\":\"input\",\"text\":\"ответ\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  ERROR_VARIABLE cli_errors
  RESULT_VARIABLE exit_code)

set(expected_events
  "{\"event\":\"ready\",\"protocol\":1"
  "{\"event\":\"result\",\"found\":true}"
  "{\"event\":\"output\",\"text\":\"X=1\\nX=2\\n\"}"
  "{\"event\":\"input_request\",\"kind\":\"line\"}"
  "{\"event\":\"output\",\"text\":\"ответX=ответ\\n\"}"
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

# --- a program that does not parse must be reported and set exit code 2 -------
file(WRITE "${session}"
  "{\"cmd\":\"load\",\"text\":\"это не программа\"}\n"
  "{\"cmd\":\"quit\"}\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json
  INPUT_FILE "${session}"
  OUTPUT_VARIABLE events
  RESULT_VARIABLE exit_code)

string(FIND "${events}" "\"kind\":\"parse\"" position)
if(position EQUAL -1)
  message(FATAL_ERROR "Expected a parse error event\n--- got ---\n${events}")
endif()
if(NOT exit_code EQUAL 2)
  message(FATAL_ERROR "Expected exit code 2 for a parse failure, got ${exit_code}")
endif()

# --- the protocol owns stdin/stdout, so -i/-o/-e are refused ------------------
execute_process(
  COMMAND "${PROLOGD_EXE}" --protocol json -o "${WORK_DIR}/protocol_out.txt"
  INPUT_FILE "${session}"
  RESULT_VARIABLE exit_code)
if(NOT exit_code EQUAL 1)
  message(FATAL_ERROR "Expected exit code 1 for -o with --protocol json, got ${exit_code}")
endif()
