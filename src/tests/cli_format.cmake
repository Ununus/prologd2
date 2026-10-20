# task_30: `--format` lays a program out without changing what it means.
#
# Three things are checked, on the real executable: the formatted text parses
# (the next format of it succeeds), formatting is idempotent, and running the
# formatted file prints exactly what the original printed.  Both modes, and a
# plain example next to a lesson that is full of comments and `;`.

set(example "${SOURCE_DIR}/examples/findall.pld")
set(lesson "${SOURCE_DIR}/examples/lessons/lesson_04.pld")

function(format_the_file source mode out)
  execute_process(
    COMMAND "${PROLOGD_EXE}" "--format=${mode}" -s "${source}"
    OUTPUT_FILE "${out}"
    ERROR_VARIABLE errors
    RESULT_VARIABLE result)
  if(NOT result EQUAL 0)
    message(FATAL_ERROR "--format=${mode} -s ${source} exited with ${result}: ${errors}")
  endif()
endfunction()

function(run_the_file source out)
  execute_process(
    COMMAND "${PROLOGD_EXE}" -s "${source}"
    OUTPUT_FILE "${out}"
    ERROR_VARIABLE errors
    RESULT_VARIABLE result)
  if(NOT result EQUAL 0)
    message(FATAL_ERROR "-s ${source} exited with ${result}: ${errors}")
  endif()
endfunction()

foreach(mode IN ITEMS soft hard)
  foreach(source IN ITEMS "${example}" "${lesson}")
    get_filename_component(name "${source}" NAME_WE)
    set(first "${WORK_DIR}/format_${name}_${mode}.pld")
    set(second "${WORK_DIR}/format_${name}_${mode}_again.pld")
    format_the_file("${source}" "${mode}" "${first}")
    format_the_file("${first}" "${mode}" "${second}")
    file(READ "${first}" once)
    file(READ "${second}" twice)
    if(NOT once STREQUAL twice)
      message(FATAL_ERROR "formatting ${source} (${mode}) twice differs")
    endif()
    run_the_file("${source}" "${WORK_DIR}/run_original.txt")
    run_the_file("${first}" "${WORK_DIR}/run_formatted.txt")
    file(READ "${WORK_DIR}/run_original.txt" original_output)
    file(READ "${WORK_DIR}/run_formatted.txt" formatted_output)
    if(NOT original_output STREQUAL formatted_output)
      message(FATAL_ERROR "the ${mode} format of ${source} prints something else")
    endif()
  endforeach()
endforeach()

# A source that does not parse must come back with an error, not with a mangled
# rewrite: exit code 2 and the usual `file:line:column:` line.
file(WRITE "${WORK_DIR}/format_broken.pld" "цель(Х:-часть(Х).\n")
execute_process(
  COMMAND "${PROLOGD_EXE}" --format=hard -s "${WORK_DIR}/format_broken.pld"
  OUTPUT_FILE "${WORK_DIR}/format_broken.out"
  ERROR_VARIABLE broken_errors
  RESULT_VARIABLE broken_result)
if(NOT broken_result EQUAL 2)
  message(FATAL_ERROR "a broken source exited with ${broken_result}, expected 2")
endif()
if(NOT broken_errors MATCHES "format_broken.pld:[0-9]+:[0-9]+: error")
  message(FATAL_ERROR "the diagnostic does not name the position: ${broken_errors}")
endif()
file(READ "${WORK_DIR}/format_broken.out" broken_output)
if(NOT broken_output STREQUAL "")
  message(FATAL_ERROR "a broken source wrote something to stdout: ${broken_output}")
endif()
