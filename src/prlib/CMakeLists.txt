add_library(prlib STATIC
  src/big_int.cpp
  src/utf8.cpp
  src/term.cpp
  src/term_print.cpp
  src/diagnostics.cpp
  src/checks.cpp
  src/lexer.cpp
  src/keywords.cpp
  src/parser.cpp
  src/formatter.cpp
  src/program.cpp
  src/bindings.cpp
  src/engine.cpp
  src/builtins.cpp
  src/builtins_arith.cpp
  src/builtins_io.cpp
  src/builtins_string.cpp
  src/builtins_database.cpp
  src/builtins_graphics.cpp
  src/io.cpp
  src/graphics.cpp
  src/module_loader.cpp)

target_include_directories(prlib
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)

target_link_libraries(prlib PRIVATE prologd_warnings)

target_compile_definitions(prlib PUBLIC
  PROLOGD_VERSION="${PROJECT_VERSION}")

configure_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/src/version.cpp.in"
  "${CMAKE_CURRENT_BINARY_DIR}/generated/version.cpp"
  @ONLY)

target_sources(prlib PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated/version.cpp")

# UTF-8 source encoding for MSVC.
if(MSVC)
  target_compile_options(prlib PUBLIC /utf-8)
endif()
