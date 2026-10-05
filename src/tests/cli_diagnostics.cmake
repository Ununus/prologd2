cmake_minimum_required(VERSION 3.24)

# Drives the console front-end over the diagnostics of task_40.  The four
# promises that need a real process are here, because they are about exit codes
# and about the error stream:
#
#   * a warning is advice: the program still loads, runs and exits 0;
#   * `--no-warnings` silences it and changes nothing else;
#   * an error still stops the load with exit code 2;
#   * a runtime error names its clause and exits 3 (part 89).
#
# A CMake script is used because `PASS_REGULAR_EXPRESSION` cannot look at the
# error stream.  The expectations are ASCII only: `execute_process` decodes the
# child's output with the code page of the build's console, so a Cyrillic needle
# matches in a UTF-8 console and nowhere else.  The Russian text of every message
# is pinned by the Catch2 tests instead.

if(NOT PROLOGD_EXE OR NOT WORK_DIR)
  message(FATAL_ERROR "PROLOGD_EXE and WORK_DIR are required")
endif()

# An undefined predicate: a warning naming it, and exit code 0 — negation as
# failure and half the lessons lean on an unknown goal being a plain failure.
file(WRITE "${WORK_DIR}/cli_warning.pld" "член(а, [а]).\n?члеен(а, [а]).\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" -s "${WORK_DIR}/cli_warning.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A program with a warning exited with ${exit_code}: ${errors}")
endif()
if(NOT errors MATCHES "warning:")
  message(FATAL_ERROR "Expected a warning, got: ${errors}")
endif()
if(errors MATCHES "error:")
  message(FATAL_ERROR "A warning must not be spelled as an error: ${errors}")
endif()

# The same program with the switch: silence, same exit code, same answer.
execute_process(
  COMMAND "${PROLOGD_EXE}" --no-warnings -s "${WORK_DIR}/cli_warning.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "--no-warnings changed the exit code: ${exit_code}")
endif()
if(NOT errors STREQUAL "")
  message(FATAL_ERROR "--no-warnings left: ${errors}")
endif()

# An error, on the other hand, is still an error: a statement without its dot
# stops the load, and the exit code says so.
file(WRITE "${WORK_DIR}/cli_error.pld" "факт(1)\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --no-warnings -s "${WORK_DIR}/cli_error.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 2)
  message(FATAL_ERROR "A missing dot should exit 2, got ${exit_code}: ${errors}")
endif()
if(NOT errors MATCHES "error:")
  message(FATAL_ERROR "--no-warnings silenced an error: ${errors}")
endif()

# A runtime error names the clause it happened in, and the exit code separates it
# from a load that failed (3 against 2).  The message is Russian and cannot be
# matched here, so the needle is the ASCII part of the line — the file, the line
# and the column, which is the same shape the protocol sends to the window.
file(WRITE "${WORK_DIR}/cli_runtime.pld" "дели(Х) :- БОЛЬШЕ(1, #1/0#).\n?дели(1).\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" -s "${WORK_DIR}/cli_runtime.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "A runtime error should exit 3, got ${exit_code}: ${errors}")
endif()
if(NOT errors MATCHES "cli_runtime\\.pld:1:[0-9]+: error:")
  message(FATAL_ERROR "A runtime error did not name its place: ${errors}")
endif()

# A reserved name with an arity it does not have can never work, so it is an
# error too (and exit code 2).
file(WRITE "${WORK_DIR}/cli_arity.pld" "?УМНОЖЕНИЕ(2, 3).\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" -s "${WORK_DIR}/cli_arity.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 2)
  message(FATAL_ERROR "A wrong arity should exit 2, got ${exit_code}: ${errors}")
endif()
if(NOT errors MATCHES "error:")
  message(FATAL_ERROR "Expected an error for the wrong arity, got: ${errors}")
endif()
