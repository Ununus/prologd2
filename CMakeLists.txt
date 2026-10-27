cmake_minimum_required(VERSION 3.24)

project(prologd
  VERSION 2.6.1
  DESCRIPTION "PrologD logic programming language interpreter"
  LANGUAGES CXX)

# ---------------------------------------------------------------------------
# Global settings
# ---------------------------------------------------------------------------
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# The date `--version` prints beside the number.  It is the *release* date, not the
# build date: a banner that changes on every compile cannot be checked against, and a
# package built from a tag should name the day the tag was cut.  Bump it with
# `VERSION` above.
set(PROLOGD_RELEASE_DATE "2026-10-25")

# What `--version` calls the program: the executable's own name in Latin letters.
# It reaches the generated `src/prlib/src/version.cpp` through `configure_file`, not
# through a `-D` macro, so that an encoding slip cannot reach the compiler's command
# line.
set(PROLOGD_PRODUCT_NAME "prologd")

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
# UTF-8 process encoding (Windows)
# ---------------------------------------------------------------------------
# The interpreter is UTF-8 end to end, so the process itself must not fall back
# to the ANSI code page.  See src/utf8.manifest for the reasoning.
add_library(prologd_utf8 INTERFACE)
if(MSVC)
  target_link_options(prologd_utf8 INTERFACE
    "/MANIFEST:EMBED"
    "/MANIFESTINPUT:${CMAKE_SOURCE_DIR}/src/utf8.manifest")
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

# ---------------------------------------------------------------------------
# JSON for the front-end protocol (CLI only)
# ---------------------------------------------------------------------------
# Only the console front-end needs JSON: it carries the protocol the Python GUI
# speaks (src/cli/protocol.cpp, src/gui).  prlib stays dependency-free.
#
# The library is taken as its single-header release rather than cloned: one
# 900 KB file instead of a full repository checkout.  The download is pinned by
# hash, and a stale or truncated file is therefore impossible to keep.
add_library(prologd_json INTERFACE)
if(PROLOGD_BUILD_CLI)
  if(PROLOGD_FETCH_DEPS)
    set(PROLOGD_JSON_VERSION 3.11.3)
    set(PROLOGD_JSON_DIR "${PROLOGD_THIRDPARTY_DIR}/json-${PROLOGD_JSON_VERSION}")
    set(PROLOGD_JSON_HEADER "${PROLOGD_JSON_DIR}/include/nlohmann/json.hpp")
    if(NOT EXISTS "${PROLOGD_JSON_HEADER}")
      file(MAKE_DIRECTORY "${PROLOGD_JSON_DIR}/include/nlohmann")
      file(DOWNLOAD
        "https://github.com/nlohmann/json/releases/download/v${PROLOGD_JSON_VERSION}/json.hpp"
        "${PROLOGD_JSON_HEADER}"
        EXPECTED_HASH SHA256=9bea4c8066ef4a1c206b2be5a36302f8926f7fdc6087af5d20b417d0cf103ea6
        TLS_VERIFY ON
        STATUS prologd_json_status)
      list(GET prologd_json_status 0 prologd_json_code)
      if(NOT prologd_json_code EQUAL 0)
        list(GET prologd_json_status 1 prologd_json_message)
        file(REMOVE "${PROLOGD_JSON_HEADER}")
        message(FATAL_ERROR
          "Cannot download nlohmann/json ${PROLOGD_JSON_VERSION}: ${prologd_json_message}")
      endif()
      message(STATUS "Downloaded nlohmann/json ${PROLOGD_JSON_VERSION} header")
    endif()
    target_include_directories(prologd_json INTERFACE "${PROLOGD_JSON_DIR}/include")
  else()
    find_package(nlohmann_json REQUIRED)
    target_link_libraries(prologd_json INTERFACE nlohmann_json::nlohmann_json)
  endif()
endif()

add_subdirectory(src)

if(PROLOGD_BUILD_TESTS)
  add_subdirectory(src/tests)
endif()

# ---------------------------------------------------------------------------
# Documentation (optional: requires the `typst` binary)
# ---------------------------------------------------------------------------
# The PDFs are written next to their sources, in the source tree: they are what
# the reader is handed, and a build directory is not somewhere anyone looks for
# them.  The PDFs are ignored by git (.gitignore) — the `.typ` files are the
# sources of truth, the PDFs are an artefact.
find_program(TYPST_EXECUTABLE typst)
add_custom_target(prologd_docs
  COMMENT "Building Typst documentation")
if(TYPST_EXECUTABLE)
  # Only the documents are listed here: doc/style.typ is a shared style file that
  # each of them imports, not a document of its own.
  foreach(doc IN ITEMS help technical gui lessons library)
    add_custom_command(TARGET prologd_docs POST_BUILD
      COMMAND ${TYPST_EXECUTABLE} compile
              "${CMAKE_SOURCE_DIR}/doc/${doc}.typ"
              "${CMAKE_SOURCE_DIR}/doc/${doc}.pdf"
      COMMENT "typst: doc/${doc}.typ -> doc/${doc}.pdf")
  endforeach()
  add_custom_target(docs DEPENDS prologd_docs)
else()
  add_custom_command(TARGET prologd_docs POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo
            "typst not found, skipping PDF generation")
  add_custom_command(TARGET prologd_docs POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo
            "install Typst to build the documentation PDFs into doc/")
  add_custom_target(docs DEPENDS prologd_docs)
endif()
