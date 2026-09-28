add_executable(prlib_tests
  test_smoke.cpp
  test_big_int.cpp
  test_lexer.cpp
  test_parser.cpp
  test_unify.cpp
  test_engine.cpp
  test_builtins_arith.cpp
  test_builtins_string.cpp
  test_builtins_io.cpp
  test_builtins_database.cpp
  test_findall.cpp
  test_graphics.cpp
  test_module_loader.cpp
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
endif()
