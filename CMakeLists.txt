cmake_minimum_required(VERSION 3.24)

project(prologd
  VERSION 2.0.0
  DESCRIPTION "PrologD logic programming language interpreter"
  LANGUAGES CXX)

# ---------------------------------------------------------------------------
# Global settings
# ---------------------------------------------------------------------------
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

string(TIMESTAMP PROLOGD_BUILD_DATE "%Y-%m-%d" UTC)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(PROLOGD_BUILD_TESTS "Build the test suite" ON)
option(PROLOGD_BUILD_CLI "Build the console front-end" ON)
option(PROLOGD_WERROR "Treat warnings as errors" OFF)
option(PROLOGD_FETCH_DEPS "Fetch third-party dependencies with FetchContent" ON)

set(PROLOGD_THIRDPARTY_DIR "${CMAKE_SOURCE_DIR}/src/3rdparty"
    CACHE PATH "Directory used as FetchContent base")

# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------
add_library(prologd_warnings INTERFACE)
if(MSVC)
  target_compile_options(prologd_warnings INTERFACE /W4 /permissive- /utf-8 /Zc:__cplusplus)
  if(PROLOGD_WERROR)
    target_compile_options(prologd_warnings INTERFACE /WX)
  endif()
else()
  target_compile_options(prologd_warnings INTERFACE
    -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Wsign-conversion
    -Wnon-virtual-dtor -Wold-style-cast -Wcast-align -Wunused
    -Woverloaded-virtual -Wnull-dereference -Wdouble-promotion)
  if(PROLOGD_WERROR)
    target_compile_options(prologd_warnings INTERFACE -Werror)
  endif()
endif()

# ---------------------------------------------------------------------------
# Third-party dependencies
# ---------------------------------------------------------------------------
if(PROLOGD_FETCH_DEPS)
  include(FetchContent)
  set(FETCHCONTENT_BASE_DIR "${PROLOGD_THIRDPARTY_DIR}")
  set(FETCHCONTENT_QUIET OFF)

  FetchContent_Declare(CLI11
    GIT_REPOSITORY https://github.com/CLIUtils/CLI11.git
    GIT_TAG v2.5.0
    GIT_SHALLOW TRUE)

  if(PROLOGD_BUILD_TESTS)
    FetchContent_Declare(Catch2
      GIT_REPOSITORY https://github.com/catchorg/Catch2.git
      GIT_TAG v3.7.1
      GIT_SHALLOW TRUE)
  endif()
endif()

if(PROLOGD_BUILD_TESTS)
  if(PROLOGD_FETCH_DEPS)
    FetchContent_MakeAvailable(Catch2)
  endif()
  enable_testing()
  list(APPEND CMAKE_MODULE_PATH "${catch2_SOURCE_DIR}/extras")
  include(Catch)
endif()

if(PROLOGD_BUILD_CLI AND PROLOGD_FETCH_DEPS)
  FetchContent_MakeAvailable(CLI11)
endif()

add_subdirectory(src)

if(PROLOGD_BUILD_TESTS)
  add_subdirectory(src/tests)
endif()

# ---------------------------------------------------------------------------
# Documentation (optional: requires the `typst` binary)
# ---------------------------------------------------------------------------
find_program(TYPST_EXECUTABLE typst)
add_custom_target(prologd_docs
  COMMENT "Building Typst documentation")
if(TYPST_EXECUTABLE)
  foreach(doc IN ITEMS help technical prologd-diff)
    add_custom_command(TARGET prologd_docs POST_BUILD
      COMMAND ${TYPST_EXECUTABLE} compile
              "${CMAKE_SOURCE_DIR}/doc/${doc}.typ"
              "${CMAKE_BINARY_DIR}/doc/${doc}.pdf"
      COMMENT "typst: ${doc}.typ -> ${doc}.pdf")
  endforeach()
  add_custom_target(docs DEPENDS prologd_docs)
else()
  add_custom_command(TARGET prologd_docs POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo
            "typst not found, skipping PDF generation")
  add_custom_command(TARGET prologd_docs POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo
            "install Typst to build the documentation PDFs")
  add_custom_target(docs DEPENDS prologd_docs)
endif()
