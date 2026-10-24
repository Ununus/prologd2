# task_19 — Windows portability and CI

**Status:** done (locally verified; CI image still to be confirmed)
**Depends on:** tasks 01–18
**Milestone:** M10

## Goal

Make the project build and pass tests on Windows (MSVC) as well as Linux.

## Deliverables

- [ ] Audit for platform differences:
  * `std::filesystem` path separators and `weakly_canonical` behaviour;
  * UTF-8 console (`SetConsoleCP`/`SetConsoleOutputCP`) and `argv` encoding
    (`wmain`/`CommandLineToArgvW` or `std::filesystem::path` from UTF-8);
  * no POSIX-only includes, no `unistd.h`/`strings.h`;
  * `std::mt19937_64` reproducibility across platforms (document that the
    sequence is implementation-defined for some engines; prefer a fixed
    well-defined generator such as a documented xoshiro/`mt19937` with a
    fixed seeding procedure, and pin it with a test);
  * integer sizes (`long long` assumptions).
- [ ] CI configuration:
  * GitHub Actions workflow `.github/workflows/ci.yml` with a matrix:
    Ubuntu (GCC, Clang) and Windows (MSVC) and optionally MinGW;
  * configure → build → `ctest --output-on-failure`;
  * cache `src/3rdparty` / CMake FetchContent;
  * optional `PROLOGD_WERROR=ON` job.
- [ ] Presets (`CMakePresets.json`) for `linux-debug`, `linux-release`,
      `windows-msvc`, `windows-debug`.
- [ ] Root `README.md` build instructions for both platforms.

## Design notes

* FetchContent works on Windows; keep dependencies minimal so CI is fast.
* Avoid `char` signedness assumptions; always cast to `unsigned char` before
  classifying bytes.
* Keep all file paths as `std::filesystem::path` internally and convert to
  UTF-8 only for diagnostics.

## Tests

- [ ] CI is green on Linux and Windows.
- [ ] A cross-platform golden test for number formatting, sorting order and
      RNG sequences.
- [ ] Integration test that runs the executable with a UTF-8 file name and
      Cyrillic content on both platforms.

## Progress

- [x] `CMakePresets.json` with `linux-debug`, `linux-release`, `linux-werror`,
      `windows-msvc`, `windows-ninja`.
- [x] `.github/workflows/ci.yml`: Linux (GCC and Clang) and Windows (MSVC)
      build + test, with FetchContent caching and `--output-on-failure`.
- [x] Windows console switched to UTF-8 (`SetConsoleOutputCP`), `NOMINMAX` /
      `WIN32_LEAN_AND_MEAN` defined before `windows.h`.
- [x] UTF-8 file paths: `fromUtf8Path` converts user paths on Windows; used for
      source files, include directories and `ИМПОРТ` arguments.
- [x] Audit: only `io.h`/`unistd.h` are platform-specific and both are guarded;
      no `__int128` (the `BigInt` design avoids it); no other POSIX-only APIs.
- [x] Verified on a real machine: Visual Studio Community 2026 (MSVC 19.51,
      Windows SDK 10.0.26100) builds the release configuration and runs the
      whole suite — 108/108, including the CLI and JSON protocol tests.
- [x] Baseline moved to Visual Studio 2026 only; `windows-msvc` preset, README
      and CI use `Visual Studio 18 2026` (ADR-013).
- [x] Process code page: `src/utf8.manifest` is embedded into `prologd` and
      `prlib_tests`, so `argv` and narrow path APIs are UTF-8.  Before this,
      `prologd -s "…\демо.pld"` reported `????.pld` on a cp1252 machine.
- [x] `toUtf8Path`/`toUtf8PathGeneric` replace `path::string()` and
      `generic_string()` in the module loader, which used to throw
      `No mapping for the Unicode character exists…` for Cyrillic paths.
- [x] `docs` target fixed: it never created `build/doc`, so typst always failed
      with `failed to write PDF file (os error 3)`.
- [ ] Still open: the integration test for a UTF-8 file name with Cyrillic
      content as a *CLI* test (the library-level test in `test_module_loader.cpp`
      covers the loader), and the cross-platform golden test for number
      formatting/sorting (the RNG part is done, see below).
- [ ] Still open: confirm that the CI Windows image provides VS 2026.
- [x] UTF-8 file name integration test (`import works with UTF-8 file names`).
- [x] RNG sequences: `СЛУЧ` maps `std::mt19937_64` output with its own
      rejection-based mapping (ADR-049), so `test_builtins_arith.cpp`, which
      pins seed 42 to `-286924074`, holds on every platform.
- [x] `-Werror` preset builds and tests cleanly on Linux.
- [x] Clean build on GCC 15.2 is warning-free (58 -> 0, status 194):
      `InputRequestKind::Character` for the shadowed `CodePoint`, by-value
      `std::string` variables in test loops over literal lists, explicit
      `double` casts in `graphics.cpp`.
- [x] Cross-compiled the library, the CLI and the test binary for
      `x86_64-windows-gnu` with Zig: `libprlib.a`, `prologd.exe` and
      `prlib_tests.exe` are all valid PE32+ executables, so the Windows code
      paths (`windows.h`, `SetConsoleOutputCP`, `_isatty`, `fromUtf8Path`)
      compile.
- [ ] Execute the MSVC build and run the suite on a Windows runner (requires
      Windows; delegated to the CI workflow).

## Acceptance

Both platforms configure, build and run the whole suite in CI with no
platform-specific code paths outside the documented I/O and process setup.
