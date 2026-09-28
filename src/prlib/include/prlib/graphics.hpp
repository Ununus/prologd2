#pragma once

#include <cstdint>
#include <memory>
#include <vector>

namespace prologd {

/// Default virtual screen size used by the original PrologD graphics.
inline constexpr int kMaxGrX = 1024;
inline constexpr int kMaxGrY = 768;

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
  virtual void rectangle(long long x1, long long y1, long long x2, long long y2,
                         unsigned color) = 0;
  virtual void ellipse(long long x1, long long y1, long long x2, long long y2,
                       unsigned color) = 0;
  virtual void floodFill(long long x, long long y, unsigned color) = 0;
  virtual void clearView(unsigned color) = 0;
  virtual void vertical(long long x1, long long y, long long x2, unsigned color) = 0;
  virtual void horizontal(long long x, long long y1, long long y2, unsigned color) = 0;

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

/// One recorded call; used by tests.
struct GraphicsCall {
  enum class Kind { SetPixel, GetPixel, Line, Rectangle, Ellipse, FloodFill, Clear, Vertical, Horizontal };
  Kind kind = Kind::SetPixel;
  long long x1 = 0;
  long long y1 = 0;
  long long x2 = 0;
  long long y2 = 0;
  unsigned color = 0;
};

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
  void vertical(long long x1, long long y, long long x2, unsigned color) override;
  void horizontal(long long x, long long y1, long long y2, unsigned color) override;

  [[nodiscard]] const std::vector<GraphicsCall>& calls() const noexcept { return calls_; }
  void clear() { calls_.clear(); }

 private:
  std::vector<GraphicsCall> calls_;
};

}  // namespace prologd
