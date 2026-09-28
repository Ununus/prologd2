# task_01 — Project bootstrap, build system, tooling

**Status:** done
**Depends on:** task_00
**Milestone:** M0

## Goal

Create the CMake project for the new C++23 interpreter, wire FetchContent
dependencies, .gitignore entries and a first green test binary.

## Deliverables

- [ ] `src/CMakeLists.txt` — project `prologd`, C++23, warnings-as-errors
      option, `CMAKE_EXPORT_COMPILE_COMMANDS`.
- [ ] `src/prlib/CMakeLists.txt` — static library target `prlib`.
- [ ] `src/cli/CMakeLists.txt` — executable target `prologd` (stub `main`).
- [ ] `src/tests/CMakeLists.txt` — Catch2 v3 test target `prlib_tests`.
- [ ] FetchContent for Catch2 (`v3.7.1` or newer) and CLI11 (`v2.4.2` or
      newer) into `src/3rdparty` via `FETCHCONTENT_BASE_DIR`.
- [ ] Option `PROLOGD_FETCH_DEPS` (default ON) so an offline build can use a
      pre-populated `3rdparty`.
- [ ] `.gitignore`: add `src/3rdparty/`, `build/`, `out/`, `compile_commands.json`.
- [ ] `README.md` at repository root: how to configure, build, test on Linux
      and Windows.
- [ ] `ai/status.md` created.

## Design notes

* Use `add_library(prlib STATIC)` now; `BUILD_SHARED_LIBS` respected later.
* Compiler warnings: `-Wall -Wextra -Wpedantic -Wconversion -Wshadow` for GCC/
  Clang; `/W4 /permissive-` for MSVC. Start without `-Werror` in CI to avoid
  blocking on third-party headers, but keep a `PROLOGD_WERROR` option.
* Third-party targets get `SYSTEM` includes.
* Test target links `prlib` and `Catch2::Catch2WithMain`; register with
  `catch_discover_tests`.

## Tests

- [ ] `test_smoke.cpp`: `REQUIRE(1 + 1 == 2)` compiles and runs, proving the
      toolchain and Catch2 integration.
- [ ] `ctest --test-dir build` reports 1 passing test.

## Acceptance

A clean checkout configures and builds on Linux with:

```sh
cmake -S src -B build -G Ninja
cmake --build build
ctest --test-dir build
```

and produces `build/cli/prologd` (or equivalent) that prints version/help.
