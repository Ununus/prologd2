cmake_minimum_required(VERSION 3.24)

# Drives the console front-end on programs that are deep enough to have killed
# it before task_38: the solver itself loops, but two chains are *released*
# through shared_ptr destructors (the environment chain and the chain of list
# cells), and letting a deep one go in a single step is a stack overflow — the
# process printed the right answer and then died with 0xC00000FD.
#
# These cases run in a *separate process* on purpose: a regression here kills the
# interpreter, and a Catch2 case in the same process would take the whole suite
# with it instead of failing one test.
#
# The expectations are ASCII only: `execute_process` decodes the child's output
# with the console code page, so a Cyrillic needle matches in a UTF-8 console and
# nowhere else.  The programs therefore print `ok` from a quiet query (`ТИХО`),
# and the Cyrillic side lives in the Catch2 tests.

if(NOT PROLOGD_EXE OR NOT WORK_DIR)
  message(FATAL_ERROR "PROLOGD_EXE and WORK_DIR are required")
endif()

# A recursion whose base clause does not cut: a choice point survives at the
# deepest level, which is the shape that used to release the whole chain at once.
set(deep_program "л(0).\nл(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), л(Н1).\n?ТИХО, л(100000), ВЫВОД(ok), ПС.\n")
file(WRITE "${WORK_DIR}/engine_deep_recursion.pld" "${deep_program}")

execute_process(
  COMMAND "${PROLOGD_EXE}" --max-depth 0 -s "${WORK_DIR}/engine_deep_recursion.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A 100000-deep recursion exited with ${exit_code}: ${errors}")
endif()
if(NOT output STREQUAL "ok\n")
  message(FATAL_ERROR "Expected \"ok\", got: ${output}")
endif()
if(NOT errors STREQUAL "")
  message(FATAL_ERROR "Expected no diagnostics, got: ${errors}")
endif()

# The same depth in a *term*: a list of 60 000 cells is released cell by cell,
# and each cell used to destroy its tail inside its own destructor.
set(fact_lines "")
foreach(index RANGE 1 60000)
  string(APPEND fact_lines "ф(${index}).\n")
endforeach()
file(WRITE "${WORK_DIR}/engine_deep_term.pld"
  "${fact_lines}?ТИХО, НАЙТИВСЕ(И, ф(И), _), ВЫВОД(ok), ПС.\n")

execute_process(
  COMMAND "${PROLOGD_EXE}" --max-depth 0 -s "${WORK_DIR}/engine_deep_term.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 0)
  message(FATAL_ERROR "A 60000-cell list exited with ${exit_code}: ${errors}")
endif()
if(NOT output STREQUAL "ok\n")
  message(FATAL_ERROR "Expected \"ok\", got: ${output}")
endif()

# The guard, when a caller asks for it: the same runaway recursion under
# `--max-depth` ends with one diagnostic and exit code 3, not with a crash and not
# with silence.  The flag is spelled out because the interpreter has *no* default
# depth limit (ADR-020): a runaway program stops when its caller says where.
set(runaway_program "л(Н) :- СЛОЖЕНИЕ(Н1, 1, Н), л(Н1).\n?л(1).\n")
file(WRITE "${WORK_DIR}/engine_depth_limit.pld" "${runaway_program}")

execute_process(
  COMMAND "${PROLOGD_EXE}" --max-depth 10000 -s "${WORK_DIR}/engine_depth_limit.pld"
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors
  RESULT_VARIABLE exit_code)

if(NOT exit_code EQUAL 3)
  message(FATAL_ERROR "A runaway recursion should exit 3, got ${exit_code}: ${errors}")
endif()
if(errors STREQUAL "")
  message(FATAL_ERROR "A runaway recursion should say why it stopped")
endif()
