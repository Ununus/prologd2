#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <vector>

namespace prologd {

/// Default virtual screen size — what a program draws on when nobody asks for
/// another size.  The original PrologD used `1024 × 768`; the default is smaller
/// now because the whole buffer travels to a front-end as a snapshot, and
/// `ЗАКРАСКА` walks it cell by cell: a lesson's picture is drawn in a fraction of
/// a second, while the old screen takes a visible moment (task_73).  A front-end
/// that wants the old screen asks for it — see `BitmapGraphicsBackend::reset`.
inline constexpr int kMaxGrX = 600;
inline constexpr int kMaxGrY = 600;

/// How far outside the screen a coordinate may be before it is pulled back.
///
/// A program may ask for `ЛИНИЯ(0, 0, 10**18, 10**18, 1)`, and arithmetic on
/// such numbers overflows a `long long` — undefined behaviour in C++, and a
/// difference between the engine and the canvas, whose integers do not wrap.
/// Clamping to a bound far beyond the screen cannot change a pixel that is *on*
/// the screen, and the front-end clamps to the same number, so the two pictures
/// stay identical (task_45).
inline constexpr long long kCoordinateLimit = 1'000'000;

/// Drawing backend used by the graphics built-ins.
///
/// The console build installs `NullGraphicsBackend`; a future Qt front-end
/// installs a `QPainter` implementation.  The interpreter never depends on a
/// concrete backend.
class GraphicsBackend {
 public:
  virtual ~GraphicsBackend() = default;

  virtual void setPixel(long long x, long long y, unsigned color) = 0;
  [[nodiscard]] virtual unsigned getPixel(long long x, long long y) = 0;
  virtual void line(long long x1, long long y1, long long x2, long long y2,
                    unsigned color) = 0;
  /// The outline of the box between the two opposite corners, in any order.
  virtual void rectangle(long long x1, long long y1, long long x2, long long y2,
                         unsigned color) = 0;
  /// The outline of the ellipse centred at `(x, y)` with the radii `rx`/`ry`.
  ///
  /// **Not** a bounding box: `ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes its four numbers
  /// straight through, so the first two are the centre and the last two the
  /// radii.  The parameter names said `x1, y1, x2, y2` until task_45, and both
  /// rasterisers read them as a box until a drawing of `examples/drawing.pld`
  /// came out as a flat line.
  virtual void ellipse(long long x, long long y, long long rx, long long ry,
                       unsigned color) = 0;
  virtual void floodFill(long long x, long long y, unsigned color) = 0;
  virtual void clearView(unsigned color) = 0;
  /// The run in column `x` from row `y1` to row `y2` — both ends drawn.
  virtual void vertical(long long x, long long y1, long long y2, unsigned color) = 0;
  /// The run in row `y` from column `x1` to column `x2` — both ends drawn.
  virtual void horizontal(long long x1, long long x2, long long y, unsigned color) = 0;

  [[nodiscard]] virtual int width() const { return kMaxGrX; }
  [[nodiscard]] virtual int height() const { return kMaxGrY; }
};

/// Does nothing; the default for the console build.
class NullGraphicsBackend final : public GraphicsBackend {
 public:
  void setPixel(long long, long long, unsigned) override {}
  [[nodiscard]] unsigned getPixel(long long, long long) override { return 0; }
  void line(long long, long long, long long, long long, unsigned) override {}
  void rectangle(long long, long long, long long, long long, unsigned) override {}
  void ellipse(long long, long long, long long, long long, unsigned) override {}
  void floodFill(long long, long long, unsigned) override {}
  void clearView(unsigned) override {}
  void vertical(long long, long long, long long, unsigned) override {}
  void horizontal(long long, long long, long long, unsigned) override {}
};

/// What a cell holds: the colour **value** the program wrote, which is not an
/// ARGB word.  `ТОЧКА(X, Y, Ц)` reads a pixel back, and it has to read exactly
/// what `ТОЧКА(X, Y, Ц)` wrote; turning a value into a visible colour is the
/// front-end's business, where the pixels are shown (task_45).
using GraphicsColor = unsigned;

/// The primitives of the backend, in one vocabulary (task_45).
///
/// The names are the backend's own method names, because one list serves the
/// recording backend, the protocol's `graphics` events and the front-end's
/// canvas: three spellings of `floodFill` would be three chances to disagree.
enum class GraphicsOp {
  SetPixel,
  GetPixel,  ///< a read: it never travels as an event
  Line,
  Rectangle,
  Ellipse,
  FloodFill,
  ClearView,
  Vertical,
  Horizontal,
};

/// One drawing call (task_45).
///
/// Every primitive is a **cell**, a **segment** or a **box**, and the slots say
/// which:
///
/// | `op` | slots |
/// |------|-------|
/// | `SetPixel`, `FloodFill` | `x1`, `y1` — the cell |
/// | `Line`, `Vertical`, `Horizontal` | `x1`, `y1`, `x2`, `y2` — the two ends; a run repeats the coordinate it does not move along |
/// | `Rectangle` | `x1`, `y1`, `x2`, `y2` — opposite corners of the box, in any order |
/// | `Ellipse` | `x1`, `y1` — the centre, `x2`, `y2` — the two radii |
/// | `ClearView` | `color` alone |
///
/// A segment and a box include their ends, so `vertical(x, 0, height)` covers the
/// whole empty column and `rectangle` outlines a frame that `ЗАКРАСКА` can
/// respect.
struct GraphicsEvent {
  GraphicsOp op = GraphicsOp::SetPixel;
  long long x1 = 0;
  long long y1 = 0;
  long long x2 = 0;
  long long y2 = 0;
  unsigned color = 0;
};

/// One recorded call; used by tests.  The same shape as an event, reads included.
using GraphicsCall = GraphicsEvent;

/// Records calls instead of drawing.
class RecordingGraphicsBackend final : public GraphicsBackend {
 public:
  void setPixel(long long x, long long y, unsigned color) override;
  [[nodiscard]] unsigned getPixel(long long x, long long y) override;
  void line(long long x1, long long y1, long long x2, long long y2, unsigned color) override;
  void rectangle(long long x1, long long y1, long long x2, long long y2,
                 unsigned color) override;
  void ellipse(long long x1, long long y1, long long x2, long long y2,
               unsigned color) override;
  void floodFill(long long x, long long y, unsigned color) override;
  void clearView(unsigned color) override;
  void vertical(long long x, long long y1, long long y2, unsigned color) override;
  void horizontal(long long x1, long long x2, long long y, unsigned color) override;

  [[nodiscard]] const std::vector<GraphicsCall>& calls() const noexcept { return calls_; }
  void clear() { calls_.clear(); }

 private:
  std::vector<GraphicsCall> calls_;
};

/// Draws into a `width × height` buffer of colour values and reports every
/// primitive to a sink (task_45).
///
/// The buffer is the source of truth *inside* the engine: `getPixel` answers
/// locally, and `ЗАКРАСКА` reads pixels this backend has itself written — which
/// is why the pixels cannot live on the other side of a pipe.  A cell holds the
/// colour value the program wrote (see `GraphicsColor`).
///
/// The drawing rules — where a line puts its pixels, that a rectangle outlines
/// its box, where `floodFill` stops, how a coordinate outside the screen is
/// clipped — are written twice on purpose: here, and in
/// `src/gui/prologd_gui/graphics.py`, where the front-end redraws the same
/// primitives as they arrive.  `protocol_smoke.py` compares the two pictures
/// pixel by pixel, so the two implementations cannot drift apart quietly.
class BitmapGraphicsBackend final : public GraphicsBackend {
 public:
  /// Called for every primitive, in the order the program drew them.  The
  /// coordinates are the ones the program asked for, not the clipped ones: the
  /// front-end clips the same way, and a picture that a program drew off the
  /// screen should be visible in the event stream as what it was.
  using Sink = std::function<void(const GraphicsEvent&)>;

  BitmapGraphicsBackend();
  BitmapGraphicsBackend(int width, int height);

  /// Makes the screen another size, and clears it.
  ///
  /// A front-end names the screen it shows before a run (task_73), so the buffer
  /// is made the size the window draws — a bigger picture costs memory here and
  /// bytes on the wire.  The pixels are *thrown away*: a picture belongs to the
  /// run that drew it, and a snapshot of the previous one would be a lie.  A
  /// size of zero or less keeps the default, the way the constructor treats it.
  void reset(int width, int height);

  void setSink(Sink sink);

  void setPixel(long long x, long long y, unsigned color) override;
  [[nodiscard]] unsigned getPixel(long long x, long long y) override;
  void line(long long x1, long long y1, long long x2, long long y2, unsigned color) override;
  void rectangle(long long x1, long long y1, long long x2, long long y2,
                 unsigned color) override;
  void ellipse(long long x1, long long y1, long long x2, long long y2,
               unsigned color) override;
  void floodFill(long long x, long long y, unsigned color) override;
  void clearView(unsigned color) override;
  void vertical(long long x, long long y1, long long y2, unsigned color) override;
  void horizontal(long long x1, long long x2, long long y, unsigned color) override;

  [[nodiscard]] int width() const override { return width_; }
  [[nodiscard]] int height() const override { return height_; }

  /// The value of a cell; `0` outside the screen, exactly like `getPixel`.
  [[nodiscard]] unsigned at(long long x, long long y) const;
  /// Every cell, row by row — what a snapshot sends to a front-end.
  [[nodiscard]] const std::vector<GraphicsColor>& pixels() const noexcept {
    return pixels_;
  }

 private:
  [[nodiscard]] bool inside(long long x, long long y) const;
  [[nodiscard]] std::size_t index(long long x, long long y) const;
  void put(long long x, long long y, unsigned color);
  /// A line that is *not* reported: the edges of a rectangle and of an ellipse
  /// are parts of one primitive, and the front-end draws that primitive itself.
  void drawLine(long long x1, long long y1, long long x2, long long y2, unsigned color);
  void report(GraphicsOp op, long long x1, long long y1, long long x2, long long y2,
              unsigned color);

  int width_ = kMaxGrX;
  int height_ = kMaxGrY;
  std::vector<GraphicsColor> pixels_;
  Sink sink_;
};

}  // namespace prologd
