add_executable(prlib_tests
  test_smoke.cpp
  test_big_int.cpp
  test_lexer.cpp
  test_keywords.cpp
  test_aliases.cpp
  test_parser.cpp
  test_unify.cpp
  test_engine.cpp
  test_builtins_control.cpp
  test_builtins_types.cpp
  test_builtins_arith.cpp
  test_builtins_string.cpp
  test_builtins_io.cpp
  test_builtins_database.cpp
  test_findall.cpp
  test_graphics.cpp
  test_module_loader.cpp
  test_io_context.cpp
  test_stepping.cpp
  test_typical_tasks.cpp
  test_lessons.cpp)

target_link_libraries(prlib_tests PRIVATE
  prlib
  Catch2::Catch2WithMain
  prologd_warnings
  prologd_utf8)

target_compile_definitions(prlib_tests PRIVATE
  PROLOGD_TEST_DATA_DIR="${CMAKE_SOURCE_DIR}/examples")

if(MSVC)
  target_compile_options(prlib_tests PRIVATE /utf-8)
endif()

# Keep test case names ASCII.  The discovery step below runs the test binary with
# `--list-tests` and decodes what it writes with the code page of the build's
# console (the OEM one when the build has none), so a Russian test name is stored
# double encoded in `prlib_tests-*_tests.cmake`; `ctest` then reports "No test
# cases matched" for it even though the binary runs the test fine.  The test
# *goals* are Russian throughout — only the names have to stay ASCII.
catch_discover_tests(prlib_tests)

# ---------------------------------------------------------------------------
# Command-line integration tests
# ---------------------------------------------------------------------------
if(TARGET prologd)
  set(PROLOGD_DEMO "${CMAKE_SOURCE_DIR}/examples/findall_demo.pld")

  add_test(NAME cli_source_short COMMAND prologd -s "${PROLOGD_DEMO}")
  add_test(NAME cli_source_long COMMAND prologd --source "${PROLOGD_DEMO}")
  add_test(NAME cli_source_equals COMMAND prologd "--source=${PROLOGD_DEMO}")
  add_test(NAME cli_positional COMMAND prologd "${PROLOGD_DEMO}")
  foreach(test IN ITEMS cli_source_short cli_source_long cli_source_equals cli_positional)
    set_tests_properties(${test} PROPERTIES
      PASS_REGULAR_EXPRESSION "А=\\[\\[вова,корчагин\\]")
  endforeach()

  add_test(NAME cli_version COMMAND prologd --version)
  set_tests_properties(cli_version PROPERTIES
    PASS_REGULAR_EXPRESSION "2\\.0\\.0")

  add_test(NAME cli_help COMMAND prologd --help)
  set_tests_properties(cli_help PROPERTIES
    PASS_REGULAR_EXPRESSION "--source")

  add_test(NAME cli_include
    COMMAND prologd -I "${CMAKE_SOURCE_DIR}/examples/lib"
            -s "${CMAKE_SOURCE_DIR}/examples/import_demo.pld")
  set_tests_properties(cli_include PROPERTIES
    PASS_REGULAR_EXPRESSION "Y=42")

  # task_32: an import that cannot be resolved must name the directories that
  # were searched, so a working-folder mistake is visible in the front-end.
  add_test(NAME cli_import_search_report
    COMMAND prologd -s "${CMAKE_CURRENT_SOURCE_DIR}/missing_import.pld")
  set_tests_properties(cli_import_search_report PROPERTIES
    PASS_REGULAR_EXPRESSION "Искался в:")

  # `--list-keywords` is a query: it prints `name/arity` lines and exits without
  # loading anything.  The Catch2 test covers the content; these two cover the
  # CLI shape — `/3` for a predicate, `/+` for the variadic ВЫВОД.
  add_test(NAME cli_list_keywords COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords PROPERTIES
    PASS_REGULAR_EXPRESSION "НАЙТИВСЁ/3")

  add_test(NAME cli_list_keywords_variadic COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords_variadic PROPERTIES
    PASS_REGULAR_EXPRESSION "ВЫВОД/\\+")

  # The JSON session needs byte-exact stdin, so it is driven by a CMake script
  # instead of the usual PASS_REGULAR_EXPRESSION form.
  add_test(NAME cli_json_protocol
    COMMAND ${CMAKE_COMMAND}
            "-DPROLOGD_EXE=$<TARGET_FILE:prologd>"
            "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/protocol_session.cmake")

  # Deep recursion and deep terms are released iteratively (task_38); a
  # regression kills the process, so these cases run the executable on its own
  # instead of inside the test binary.
  add_test(NAME cli_engine_limits
    COMMAND ${CMAKE_COMMAND}
            "-DPROLOGD_EXE=$<TARGET_FILE:prologd>"
            "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/engine_limits.cmake")
endif()
