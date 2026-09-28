#include "prlib/graphics.hpp"

namespace prologd {

void RecordingGraphicsBackend::setPixel(long long x, long long y, unsigned color) {
  calls_.push_back({GraphicsCall::Kind::SetPixel, x, y, 0, 0, color});
}

unsigned RecordingGraphicsBackend::getPixel(long long x, long long y) {
  calls_.push_back({GraphicsCall::Kind::GetPixel, x, y, 0, 0, 0});
  return 0;
}

void RecordingGraphicsBackend::line(long long x1, long long y1, long long x2, long long y2,
                                    unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Line, x1, y1, x2, y2, color});
}

void RecordingGraphicsBackend::rectangle(long long x1, long long y1, long long x2,
                                         long long y2, unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Rectangle, x1, y1, x2, y2, color});
}

void RecordingGraphicsBackend::ellipse(long long x1, long long y1, long long x2, long long y2,
                                       unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Ellipse, x1, y1, x2, y2, color});
}

void RecordingGraphicsBackend::floodFill(long long x, long long y, unsigned color) {
  calls_.push_back({GraphicsCall::Kind::FloodFill, x, y, 0, 0, color});
}

void RecordingGraphicsBackend::clearView(unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Clear, 0, 0, 0, 0, color});
}

void RecordingGraphicsBackend::vertical(long long x1, long long y, long long x2,
                                        unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Vertical, x1, y, x2, 0, color});
}

void RecordingGraphicsBackend::horizontal(long long x, long long y1, long long y2,
                                          unsigned color) {
  calls_.push_back({GraphicsCall::Kind::Horizontal, x, y1, y2, 0, color});
}

}  // namespace prologd
