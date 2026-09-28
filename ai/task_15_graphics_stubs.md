# task_15 — Graphics predicates and backend stubs

**Status:** done
**Depends on:** task_09
**Milestone:** M7

## Goal

Restore the graphics built-ins behind an interface so the console build is
complete and a future Qt GUI can plug in.

## Deliverables

- [ ] `include/prlib/graphics.hpp`
  * `GraphicsBackend` interface:
    ```cpp
    struct GraphicsBackend {
      virtual ~GraphicsBackend() = default;
      virtual void setPixel(long long x, long long y, unsigned color) = 0;
      virtual unsigned getPixel(long long x, long long y) = 0;
      virtual void line(long long x1, long long y1, long long x2, long long y2, unsigned color) = 0;
      virtual void rectangle(long long x1, long long y1, long long x2, long long y2, unsigned color) = 0;
      virtual void ellipse(long long x1, long long y1, long long x2, long long y2, unsigned color) = 0;
      virtual void floodFill(long long x, long long y, unsigned color) = 0;
      virtual void clearView(unsigned color) = 0;
      virtual void vertical(long long x1, long long y, long long x2, unsigned color) = 0;
      virtual void horizontal(long long x, long long y1, long long y2, unsigned color) = 0;
      virtual int width() const;   // default kMaxGrX
      virtual int height() const;  // default kMaxGrY
    };
    ```
  * `NullGraphicsBackend` (no-ops, `getPixel` returns 0) and
    `RecordingGraphicsBackend` (for tests).
  * `kMaxGrX = 1024`, `kMaxGrY = 768`.
- [ ] `src/builtins_graphics.cpp`
  * `ТОЧКА/3`, `ЛИНИЯ/5`, `ОКРУЖНОСТЬ/4`, `ЗАКРАСКА/3` reproducing the
    documented argument-type dispatch (integer vs unbound variable selects
    different drawing operations), delegating to the backend.
  * Non-conforming argument types produce the original error messages.
- [ ] The engine exposes `setGraphicsBackend(std::shared_ptr<GraphicsBackend>)`;
  CLI installs the null backend by default, with `--graphics-log` installing the
  recording backend for debugging.

## Design notes

* Reproduce the original coordinate conventions exactly (`maxgrx=1024`,
  `maxgry=768`; `ТОЧКА` with an unbound `Y` draws a vertical line with
  `color=0` — note the original bug and decide whether to keep it; document the
  choice).
* Keep the backend call in a `try`/`catch` so a GUI backend can report errors
  as `ErrorCode::ExecutionInterrupted` or similar.

## Tests

- [ ] `test_builtins_graphics.cpp` with `RecordingGraphicsBackend`:
      each documented mode of `ТОЧКА`, `ЛИНИЯ`, `ОКРУЖНОСТЬ`, `ЗАКРАСКА`
      produces the expected backend calls (count and coordinates);
      wrong argument types produce errors.

## Acceptance

All four graphics predicates are callable in the console build, always succeed
for valid arguments, and are covered by backend-recording tests.
