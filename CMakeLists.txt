cmake_minimum_required(VERSION 3.24)

project(prologd
  VERSION 2.4.2
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

# The product the *engine* calls itself (task_76).  It reaches the generated
# `src/prlib/src/version.cpp` through `configure_file`, not through a `-D` macro: a
# non-ASCII value on the compiler's command line travels through a response file in the
# machine's ANSI code page, while the generated source is written as UTF-8 bytes and
# compiled with `/utf-8` like every other file of `prlib`.
set(PROLOGD_PRODUCT_NAME "Пролог-У")

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
# The original engine (optional)
# ---------------------------------------------------------------------------
# The old dialect is not a mode of *this* engine: it is an engine of its own, kept in
# `Ununus/prologd`, which serves a live web service and is not ours to change
# (task_78).  It is built as a *nested* CMake project rather than pulled into this
# graph, and that is deliberate: its targets are named `prlib` and `prologd_json` —
# both names this tree already uses — it is C++17 where this tree is C++23, and its
# sources are CP1251 where this tree is UTF-8.  In one graph, `target_link_libraries`
# could quietly pick the wrong `prlib`; in two, nothing of ours can.
#
# Its console interpreter is told to write to *this* tree's runtime directory, so the
# two engines land side by side — `src/cli/<config>/prologu.exe` and `prologd.exe` —
# which is where the window looks for an engine and where the portable layout copies
# them from.
#
# Off by default, and worth saying why: it needs the network once (a clone of the
# pinned commit) and half a minute of building, and a build that only has our engine
# downloads nothing.  A machine with no network points `PROLOGD_ENGINE_SOURCE` at a
# clone it already has, and then nothing is fetched at all.
option(BUILD_WITH_PROLOGD
  "Build the original prologd — the old dialect, a second engine — beside prologu" OFF)

if(BUILD_WITH_PROLOGD)
  if(NOT PROLOGD_BUILD_CLI)
    message(FATAL_ERROR
      "BUILD_WITH_PROLOGD=ON builds a console engine: set PROLOGD_BUILD_CLI=ON too")
  endif()
  set(PROLOGD_ENGINE_REPOSITORY "https://github.com/Ununus/prologd.git"
      CACHE STRING "Where the original engine is taken from")
  # A commit, never a branch: `master` moves, and the engine a front-end is checked
  # against must not change under our feet.  The pinned one answers protocol 13 —
  # a *documented subset* of ours (its own `src/protocol.cpp` says so): the requests
  # and events both engines share exist, stepping, tracing, formatting and graphics
  # do not.  Bumped in part 133 to the commit that made its paths UTF-8
  # (`ce23afb`): a Cyrillic file name on the command line, in `-I` and in
  # `?ИМПОРТ("…")` is taken as it was typed.  Bumped in part 139 to `cf4001e` —
  # «БОЛЬШЕ: сравнение списков» (`112e241`) together with the commit that put
  # `prlib/extfunc.cpp` back into CP1251: that file had been re-saved as UTF-8 and
  # every message from it came out as garbage, which is why the pin waited (part
  # 138).  Bumped in part 140 to c36f101 — «Предикат СОРТИРОВКА»: its СОРТИРОВКА/2
  # orders by the comparison of БОЛЬШЕ and refuses lists of mixed kinds, which
  # ours does not (ours follows the standard order, task_90).  Bumped in part 143 to
  # 823a9d1, which moved the built-in reference into the engine (`doc/builtins.json`)
  # and generated its manual in Typst (`doc/help.typ`, `doc/style.typ`): a package
  # that ships only this engine takes both from here instead of ours (part 143).
  #
  # Not a cache variable on purpose: a cache entry is written once, by the first
  # configure, and every later bump of the pin would then be invisible in a tree
  # that has already been built.  To build against another commit, point
  # `PROLOGD_ENGINE_SOURCE` at a clone of it — that is the override this file
  # documents.
  set(PROLOGD_ENGINE_COMMIT "823a9d18212a26c64672b7812be56268d4e91206")
  set(PROLOGD_ENGINE_SOURCE ""
      CACHE PATH "An existing clone of the original engine; skips the download")

  include(ExternalProject)
  if(PROLOGD_ENGINE_SOURCE)
    set(prologd_engine_origin
      SOURCE_DIR "${PROLOGD_ENGINE_SOURCE}"
      DOWNLOAD_COMMAND ""
      UPDATE_COMMAND "")
  else()
    set(prologd_engine_origin
      GIT_REPOSITORY "${PROLOGD_ENGINE_REPOSITORY}"
      GIT_TAG "${PROLOGD_ENGINE_COMMIT}"
      GIT_SHALLOW FALSE      # a commit needs the history, not the tip
      UPDATE_COMMAND "")     # and it is never fetched again: the pin is the point
  endif()

  # `Release` whatever this build is, and not `$<CONFIG>`: this engine is built to be
  # the artifact the package ships and the front-end is checked against, and one
  # answer to «which binary is the reference» is worth more than a matching Debug.
  ExternalProject_Add(prologd_engine
    ${prologd_engine_origin}
    PREFIX "${CMAKE_BINARY_DIR}/prologd-engine"
    BINARY_DIR "${CMAKE_BINARY_DIR}/prologd-engine/build"
    CMAKE_ARGS
      "-DCMAKE_BUILD_TYPE=Release"
      "-DPROLOGD_BUILD_FOR_GUI=ON"   # the JSON session a front-end speaks
      "-DPROLOGD_BUILD_TESTS=OFF"    # its suite is not ours to run
      # Our JSON header, not theirs.  The original downloads `json.hpp` at configure
      # time; this tree already keeps `json-3.11.3` in exactly the layout it looks
      # for, so the download is skipped and there is no second copy of a 900 KB file.
      "-DPROLOGD_THIRDPARTY_DIR=${CMAKE_SOURCE_DIR}/src/3rdparty"
      "-DCMAKE_RUNTIME_OUTPUT_DIRECTORY=${CMAKE_BINARY_DIR}/src/cli"
    BUILD_COMMAND
      ${CMAKE_COMMAND} --build <BINARY_DIR> --config Release --target prologd
    INSTALL_COMMAND ""
    COMMENT "Building the original prologd (the old dialect)")
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
  foreach(doc IN ITEMS help technical prologd-diff gui lessons library)
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
