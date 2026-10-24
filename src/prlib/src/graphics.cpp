#include "prlib/graphics.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

namespace prologd {
namespace {

/// `floor(value + 0.5)`.
///
/// An explicit rule, because the ellipse is rasterised from its parametric
/// equation on **both** sides of the pipe: the canvas in
/// `src/gui/prologd_gui/graphics.py` rounds with `math.floor(value + 0.5)`, and
/// `std::round` would differ from it on a half (it rounds away from zero, so a
/// negative half would land one pixel off).  The two pictures are compared pixel
/// by pixel in `protocol_smoke.py`.
[[nodiscard]] long long halfUp(double value) {
  return static_cast<long long>(std::floor(value + 0.5));
}

[[nodiscard]] long long clamped(long long value) {
  return std::clamp(value, -kCoordinateLimit, kCoordinateLimit);
}

[[nodiscard]] long long absolute(long long value) { return value < 0 ? -value : value; }

}  // namespace

// ---------------------------------------------------------------------------
// RecordingGraphicsBackend
// ---------------------------------------------------------------------------

void RecordingGraphicsBackend::setPixel(long long x, long long y, unsigned color) {
  calls_.push_back({GraphicsOp::SetPixel, x, y, 0, 0, color});
}

unsigned RecordingGraphicsBackend::getPixel(long long x, long long y) {
  calls_.push_back({GraphicsOp::GetPixel, x, y, 0, 0, 0});
  return 0;
}

void RecordingGraphicsBackend::line(long long x1, long long y1, long long x2, long long y2,
                                    unsigned color) {
  calls_.push_back({GraphicsOp::Line, x1, y1, x2, y2, color});
}

void RecordingGraphicsBackend::rectangle(long long x1, long long y1, long long x2,
                                         long long y2, unsigned color) {
  calls_.push_back({GraphicsOp::Rectangle, x1, y1, x2, y2, color});
}

void RecordingGraphicsBackend::ellipse(long long x, long long y, long long rx, long long ry,
                                       unsigned color) {
  calls_.push_back({GraphicsOp::Ellipse, x, y, rx, ry, color});
}

void RecordingGraphicsBackend::floodFill(long long x, long long y, unsigned color) {
  calls_.push_back({GraphicsOp::FloodFill, x, y, 0, 0, color});
}

void RecordingGraphicsBackend::clearView(unsigned color) {
  calls_.push_back({GraphicsOp::ClearView, 0, 0, 0, 0, color});
}

void RecordingGraphicsBackend::vertical(long long x, long long y1, long long y2,
                                        unsigned color) {
  calls_.push_back({GraphicsOp::Vertical, x, y1, x, y2, color});
}

void RecordingGraphicsBackend::horizontal(long long x1, long long x2, long long y,
                                          unsigned color) {
  calls_.push_back({GraphicsOp::Horizontal, x1, y, x2, y, color});
}

// ---------------------------------------------------------------------------
// BitmapGraphicsBackend
// ---------------------------------------------------------------------------

BitmapGraphicsBackend::BitmapGraphicsBackend() : BitmapGraphicsBackend(kMaxGrX, kMaxGrY) {}

BitmapGraphicsBackend::BitmapGraphicsBackend(int width, int height) {
  reset(width, height);
}

void BitmapGraphicsBackend::reset(int width, int height) {
  width_ = width > 0 ? width : kMaxGrX;
  height_ = height > 0 ? height : kMaxGrY;
  pixels_.assign(static_cast<std::size_t>(width_) * static_cast<std::size_t>(height_), 0);
}

void BitmapGraphicsBackend::setSink(Sink sink) { sink_ = std::move(sink); }

bool BitmapGraphicsBackend::inside(long long x, long long y) const {
  return x >= 0 && y >= 0 && x < width_ && y < height_;
}

std::size_t BitmapGraphicsBackend::index(long long x, long long y) const {
  return static_cast<std::size_t>(y) * static_cast<std::size_t>(width_) +
         static_cast<std::size_t>(x);
}

void BitmapGraphicsBackend::put(long long x, long long y, unsigned color) {
  if (inside(x, y)) {
    pixels_[index(x, y)] = color;
  }
}

unsigned BitmapGraphicsBackend::at(long long x, long long y) const {
  return inside(x, y) ? pixels_[index(x, y)] : 0u;
}

unsigned BitmapGraphicsBackend::getPixel(long long x, long long y) { return at(x, y); }

void BitmapGraphicsBackend::report(GraphicsOp op, long long x1, long long y1, long long x2,
                                   long long y2, unsigned color) {
  if (sink_) {
    sink_(GraphicsEvent{op, x1, y1, x2, y2, color});
  }
}

void BitmapGraphicsBackend::setPixel(long long x, long long y, unsigned color) {
  report(GraphicsOp::SetPixel, x, y, 0, 0, color);
  put(clamped(x), clamped(y), color);
}

void BitmapGraphicsBackend::drawLine(long long x1, long long y1, long long x2, long long y2,
                                     unsigned color) {
  // Bresenham over all eight octants, both ends included, and `x` stepped first
  // when a step is equally cheap in both directions — the same algorithm as
  // `Canvas.line` on the front-end side.
  const long long left = clamped(x1);
  const long long top = clamped(y1);
  const long long right = clamped(x2);
  const long long bottom = clamped(y2);
  const long long dx = absolute(right - left);
  const long long dy = -absolute(bottom - top);
  const long long step_x = left < right ? 1 : -1;
  const long long step_y = top < bottom ? 1 : -1;
  long long error = dx + dy;
  long long x = left;
  long long y = top;
  for (;;) {
    put(x, y, color);
    if (x == right && y == bottom) {
      break;
    }
    const long long doubled = 2 * error;
    if (doubled >= dy) {
      error += dy;
      x += step_x;
    }
    if (doubled <= dx) {
      error += dx;
      y += step_y;
    }
  }
}

void BitmapGraphicsBackend::line(long long x1, long long y1, long long x2, long long y2,
                                 unsigned color) {
  report(GraphicsOp::Line, x1, y1, x2, y2, color);
  drawLine(x1, y1, x2, y2, color);
}

void BitmapGraphicsBackend::rectangle(long long x1, long long y1, long long x2, long long y2,
                                      unsigned color) {
  report(GraphicsOp::Rectangle, x1, y1, x2, y2, color);
  // The *outline* of the box, in any corner order: a program that wants it
  // filled draws a line with two free ends or follows the frame with `ЗАКРАСКА`
  // (`examples/drawing.pld` does exactly that).
  const long long left = clamped(std::min(x1, x2));
  const long long right = clamped(std::max(x1, x2));
  const long long top = clamped(std::min(y1, y2));
  const long long bottom = clamped(std::max(y1, y2));
  drawLine(left, top, right, top, color);
  drawLine(left, bottom, right, bottom, color);
  drawLine(left, top, left, bottom, color);
  drawLine(right, top, right, bottom, color);
}

void BitmapGraphicsBackend::ellipse(long long x, long long y, long long rx, long long ry,
                                    unsigned color) {
  report(GraphicsOp::Ellipse, x, y, rx, ry, color);
  // Centre and radii, from the parametric equation `x = cx + rx·cos`,
  // `y = cy + ry·sin`.  Two scans (by `x` and by `y`) rather than one, because a
  // single scan leaves gaps where the curve is steep, and the frame has to stop
  // `ЗАКРАСКА` everywhere it looks closed.
  const long long centre_x = clamped(x);
  const long long centre_y = clamped(y);
  const double radius_x = static_cast<double>(absolute(clamped(rx)));
  const double radius_y = static_cast<double>(absolute(clamped(ry)));
  if (radius_x < 1.0 && radius_y < 1.0) {
    put(centre_x, centre_y, color);
    return;
  }
  if (radius_x < 1.0) {
    drawLine(centre_x, centre_y - static_cast<long long>(radius_y), centre_x,
             centre_y + static_cast<long long>(radius_y), color);
    return;
  }
  if (radius_y < 1.0) {
    drawLine(centre_x - static_cast<long long>(radius_x), centre_y,
             centre_x + static_cast<long long>(radius_x), centre_y, color);
    return;
  }
  for (long long column = halfUp(static_cast<double>(centre_x) - radius_x);
       column <= halfUp(static_cast<double>(centre_x) + radius_x); ++column) {
    const double t = (static_cast<double>(column) - static_cast<double>(centre_x)) / radius_x;
    const double offset = radius_y * std::sqrt(std::max(0.0, 1.0 - t * t));
    put(column, halfUp(static_cast<double>(centre_y) - offset), color);
    put(column, halfUp(static_cast<double>(centre_y) + offset), color);
  }
  for (long long row = halfUp(static_cast<double>(centre_y) - radius_y);
       row <= halfUp(static_cast<double>(centre_y) + radius_y); ++row) {
    const double t = (static_cast<double>(row) - static_cast<double>(centre_y)) / radius_y;
    const double offset = radius_x * std::sqrt(std::max(0.0, 1.0 - t * t));
    put(halfUp(static_cast<double>(centre_x) - offset), row, color);
    put(halfUp(static_cast<double>(centre_x) + offset), row, color);
  }
}

void BitmapGraphicsBackend::floodFill(long long x, long long y, unsigned color) {
  report(GraphicsOp::FloodFill, x, y, 0, 0, color);
  if (!inside(x, y)) {
    return;  // starting outside the screen: there is no area to fill
  }
  const unsigned target = pixels_[index(x, y)];
  if (target == color) {
    return;  // already that colour: nothing to tell apart, so nothing to do
  }
  std::vector<std::pair<long long, long long>> pending{{x, y}};
  while (!pending.empty()) {
    const std::pair<long long, long long> cell = pending.back();
    pending.pop_back();
    if (!inside(cell.first, cell.second) ||
        pixels_[index(cell.first, cell.second)] != target) {
      continue;
    }
    pixels_[index(cell.first, cell.second)] = color;
    // Four neighbours, not eight: a diagonal gap of one pixel does not leak, so
    // an outline drawn by `ЛИНИЯ` holds the fill — that is how a picture is made.
    pending.emplace_back(cell.first + 1, cell.second);
    pending.emplace_back(cell.first - 1, cell.second);
    pending.emplace_back(cell.first, cell.second + 1);
    pending.emplace_back(cell.first, cell.second - 1);
  }
}

void BitmapGraphicsBackend::clearView(unsigned color) {
  report(GraphicsOp::ClearView, 0, 0, 0, 0, color);
  std::fill(pixels_.begin(), pixels_.end(), color);
}

void BitmapGraphicsBackend::vertical(long long x, long long y1, long long y2,
                                     unsigned color) {
  report(GraphicsOp::Vertical, x, y1, x, y2, color);
  drawLine(x, y1, x, y2, color);
}

void BitmapGraphicsBackend::horizontal(long long x1, long long x2, long long y,
                                       unsigned color) {
  report(GraphicsOp::Horizontal, x1, y, x2, y, color);
  drawLine(x1, y, x2, y, color);
}

}  // namespace prologd
