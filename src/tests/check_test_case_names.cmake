# Every `TEST_CASE` name must be ASCII (task_95, part 223).
#
# `catch_discover_tests` registers each case as a CTest test and passes the name
# back as `--test-case "<name>"`.  A name with Cyrillic in it survives on Linux —
# the bytes are UTF-8 on both sides — and turns into mojibake on Windows, where
# the argument reaches the process through the console code page: the filter then
# matches nothing, CTest reports "No test cases matched", and the case fails
# without its body ever running.  That is what happened twice in part 223, and
# this check is what keeps it from happening a third time.
#
#     cmake -DSOURCES_DIR=<src/tests> -P check_test_case_names.cmake
#
# The test *bodies* are Russian throughout; only the names have to be Latin.
#
# The file is read whole and searched with a regex, **not** line by line: CMake's
# `file(STRINGS)` cuts a line at the first byte above ASCII — silently, with no
# error — so a line-by-line version of this check passes on exactly the names it
# was written to catch.  Comparing the whole file also keeps the match position,
# which is what turns into a line number for the message.

if(NOT DEFINED SOURCES_DIR)
  message(FATAL_ERROR "SOURCES_DIR is not set")
endif()

file(GLOB sources "${SOURCES_DIR}/test_*.cpp")
list(SORT sources)
if(NOT sources)
  message(FATAL_ERROR "no test sources under ${SOURCES_DIR}")
endif()

set(offenders "")
list(LENGTH sources count)
foreach(source IN LISTS sources)
  file(READ "${source}" content)
  # `TEST_CASE("…")` up to the closing quote, and never across a line break.
  string(REGEX MATCHALL "TEST_CASE\\(\"[^\"\n]*\"" declarations "${content}")
  foreach(declaration IN LISTS declarations)
    if(declaration MATCHES "[^ -~]")
      # Where it stands, as a line number: one more than the breaks before it.
      string(FIND "${content}" "${declaration}" position)
      string(SUBSTRING "${content}" 0 ${position} prefix)
      string(REGEX MATCHALL "\n" breaks "${prefix}")
      list(LENGTH breaks lines_before)
      math(EXPR line "${lines_before} + 1")
      get_filename_component(short "${source}" NAME)
      string(APPEND offenders "\n  ${short}:${line}: ${declaration}")
    endif()
  endforeach()
endforeach()

if(offenders)
  message(FATAL_ERROR
    "test case names must be ASCII: CTest passes each name back as --test-case, "
    "and a console code page that is not UTF-8 turns a Russian name into mojibake, "
    "so the case fails with «No test cases matched».  The body may be Russian.${offenders}")
endif()

message(STATUS "checked ${count} test sources: every TEST_CASE name is ASCII")
