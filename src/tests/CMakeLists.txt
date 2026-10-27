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
  test_builtins_lists.cpp
  test_standard_order.cpp
  test_builtins_io.cpp
  test_builtins_database.cpp
  test_findall.cpp
  test_bagof_setof.cpp
  test_graphics.cpp
  test_graphics_backend.cpp
  test_module_loader.cpp
  test_io_context.cpp
  test_stepping.cpp
  test_typical_tasks.cpp
  test_diagnostics.cpp
  test_formatter.cpp
  test_lessons.cpp
  test_stdlib.cpp)

target_link_libraries(prlib_tests PRIVATE
  prlib
  Catch2::Catch2WithMain
  prologd_warnings
  prologd_utf8)

target_compile_definitions(prlib_tests PRIVATE
  PROLOGD_TEST_DATA_DIR="${CMAKE_SOURCE_DIR}/examples"
  PROLOGD_STDLIB_DIR="${CMAKE_SOURCE_DIR}/stdlib"
  PROLOGD_DOC_DIR="${CMAKE_SOURCE_DIR}/doc")

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
  set(PROLOGD_DEMO "${CMAKE_SOURCE_DIR}/examples/findall.pld")

  add_test(NAME cli_source_short COMMAND prologd -s "${PROLOGD_DEMO}")
  add_test(NAME cli_source_long COMMAND prologd --source "${PROLOGD_DEMO}")
  add_test(NAME cli_source_equals COMMAND prologd "--source=${PROLOGD_DEMO}")
  add_test(NAME cli_positional COMMAND prologd "${PROLOGD_DEMO}")
  foreach(test IN ITEMS cli_source_short cli_source_long cli_source_equals cli_positional)
    set_tests_properties(${test} PROPERTIES
      PASS_REGULAR_EXPRESSION "А=\\[\\[вова,корчагин\\]")
  endforeach()

  add_test(NAME cli_version COMMAND prologd --version)
  # The banner is `<name> <version> (<release date>)`, and it has **one** source:
  # `project(prologd VERSION x.y.z)` and `PROLOGD_RELEASE_DATE` in the top
  # `CMakeLists.txt`.  The test asks the binary instead of repeating the literals.
  string(REPLACE "." "\\." PROLOGD_VERSION_PATTERN "${PROJECT_VERSION}")
  set_tests_properties(cli_version PROPERTIES
    PASS_REGULAR_EXPRESSION "^prologd ${PROLOGD_VERSION_PATTERN} \\([0-9]+-[0-9]+-[0-9]+\\)")

  add_test(NAME cli_help COMMAND prologd --help)
  set_tests_properties(cli_help PROPERTIES
    PASS_REGULAR_EXPRESSION "--source")

  add_test(NAME cli_include
    COMMAND prologd -I "${CMAKE_SOURCE_DIR}/examples/lib"
            -s "${CMAKE_SOURCE_DIR}/examples/import.pld")
  set_tests_properties(cli_include PROPERTIES
    PASS_REGULAR_EXPRESSION "Дважды=42")

  # Part 133: a name of a file is UTF-8 — on the command line, in `-I` and in
  # `?ИМПОРТ("…")` — so a Cyrillic path is taken as it was typed.  The directory and
  # the programs are written here, at configure time; the needles are ASCII on
  # purpose, because CMake decodes a child's output with the code page of the build's
  # console (`cli_diagnostics.cmake` says the same in its own comment).
  set(prologd_cyrillic "${CMAKE_CURRENT_BINARY_DIR}/кириллица")
  file(MAKE_DIRECTORY "${prologd_cyrillic}" "${prologd_cyrillic}/библиотеки")
  file(WRITE "${prologd_cyrillic}/программа.pld" "?СЛОЖЕНИЕ(2, 3, С).\n")
  file(WRITE "${prologd_cyrillic}/вход.txt" "hello\n")
  file(WRITE "${prologd_cyrillic}/чтение.pld" "?ВВОДСТР(X).\n")
  file(WRITE "${prologd_cyrillic}/библиотеки/библиотека.pld"
       "удвоить(Ч, Д):-УМНОЖЕНИЕ(Ч, 2, Д).\n")
  file(WRITE "${prologd_cyrillic}/импорт.pld"
       "?ИМПОРТ(\"библиотека.pld\").\n?удвоить(21, Д).\n")

  add_test(NAME cli_cyrillic_path
    COMMAND prologd -s "${prologd_cyrillic}/программа.pld")
  set_tests_properties(cli_cyrillic_path PROPERTIES
    PASS_REGULAR_EXPRESSION "=5")

  # `-i` names a file too, and the same conversion opens it.
  add_test(NAME cli_cyrillic_input_file
    COMMAND prologd -s "${prologd_cyrillic}/чтение.pld"
            -i "${prologd_cyrillic}/вход.txt")
  set_tests_properties(cli_cyrillic_input_file PROPERTIES
    PASS_REGULAR_EXPRESSION "X=hello")

  # The library lies in another Cyrillic directory, so only `-I` can find it.
  add_test(NAME cli_cyrillic_include
    COMMAND prologd -I "${prologd_cyrillic}/библиотеки"
            -s "${prologd_cyrillic}/импорт.pld")
  set_tests_properties(cli_cyrillic_include PROPERTIES
    PASS_REGULAR_EXPRESSION "Д=42")

  # task_32: an import that cannot be resolved must name the directories that
  # were searched, so a working-folder mistake is visible in the front-end.
  add_test(NAME cli_import_search_report
    COMMAND prologd -s "${CMAKE_CURRENT_SOURCE_DIR}/missing_import.pld")
  set_tests_properties(cli_import_search_report PROPERTIES
    PASS_REGULAR_EXPRESSION "Искался в:")

  # `--list-keywords` is a query: it prints `name/arity` lines and exits without
  # loading anything.  The Catch2 test covers the content; these cover the CLI
  # shape — `/3` for a predicate, `/+` for a variadic name (ВЫВОД, ВЫВОДПС,
  # ПЕРВОЕ).
  add_test(NAME cli_list_keywords COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords PROPERTIES
    PASS_REGULAR_EXPRESSION "НАЙТИВСЕ/3")

  add_test(NAME cli_list_keywords_variadic COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords_variadic PROPERTIES
    PASS_REGULAR_EXPRESSION "ВЫВОД/\\+")

  add_test(NAME cli_list_keywords_variadic_first COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords_variadic_first PROPERTIES
    PASS_REGULAR_EXPRESSION "ПЕРВОЕ/\\+")

  add_test(NAME cli_list_keywords_variadic_writeln COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords_variadic_writeln PROPERTIES
    PASS_REGULAR_EXPRESSION "ВЫВОДПС/\\+")

  add_test(NAME cli_list_keywords_variadic_writeln_english COMMAND prologd --list-keywords)
  set_tests_properties(cli_list_keywords_variadic_writeln_english PROPERTIES
    PASS_REGULAR_EXPRESSION "writeln/\\+")

  # The names marker is retired with the modes it declared: a file that still
  # starts with one is refused, and the message says why rather than «не найдено».
  add_test(NAME cli_names_marker_is_refused
    COMMAND prologd -s "${CMAKE_CURRENT_SOURCE_DIR}/names_marker.pld")
  set_tests_properties(cli_names_marker_is_refused PROPERTIES
    PASS_REGULAR_EXPRESSION "режимов имён больше нет")

  # task_30: `--format` is checked by the bytes it writes — the formatted file
  # must still print what the original printed, and formatting it again must not
  # change it.  Both need the real executable, so a CMake script drives it.
  add_test(NAME cli_format
    COMMAND ${CMAKE_COMMAND}
            "-DPROLOGD_EXE=$<TARGET_FILE:prologd>"
            "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            "-DSOURCE_DIR=${CMAKE_SOURCE_DIR}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/cli_format.cmake")

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

  # task_40: a warning must leave the exit code alone, `--no-warnings` must
  # silence it, and an error must still exit 2.  The error stream is the point,
  # which `PASS_REGULAR_EXPRESSION` cannot see, so a CMake script drives it.
  add_test(NAME cli_diagnostics
    COMMAND ${CMAKE_COMMAND}
            "-DPROLOGD_EXE=$<TARGET_FILE:prologd>"
            "-DWORK_DIR=${CMAKE_CURRENT_BINARY_DIR}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/cli_diagnostics.cmake")
endif()
