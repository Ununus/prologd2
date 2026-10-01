#include <catch2/catch_test_macros.hpp>

#include <memory>
#include <vector>

#include "prlib/graphics.hpp"
#include "test_helpers.hpp"

using namespace prologd;
using prologd::test::runProgram;

namespace {

/// A small screen, so a test can look at every cell of it: `kMaxGrX × kMaxGrY`
/// is the engine's real size, and the drawing rules are the same at any size.
constexpr int kWidth = 12;
constexpr int kHeight = 8;

int setCells(const BitmapGraphicsBackend& backend) {
  int count = 0;
  for (unsigned value : backend.pixels()) {
    if (value != 0) {
      ++count;
    }
  }
  return count;
}

}  // namespace

TEST_CASE("a point lands in the one cell it names") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  REQUIRE(backend.width() == kWidth);
  REQUIRE(backend.height() == kHeight);
  REQUIRE(backend.pixels().size() == static_cast<std::size_t>(kWidth) * kHeight);
  REQUIRE(backend.at(0, 0) == 0);

  backend.setPixel(1, 2, 7);
  REQUIRE(backend.at(1, 2) == 7);
  REQUIRE(backend.getPixel(1, 2) == 7);
  REQUIRE(backend.at(2, 1) == 0);
  REQUIRE(setCells(backend) == 1);

  // Outside the screen: written nowhere, read as black (the null backend's
  // answer, so a program cannot tell an empty screen from a missing one).
  backend.setPixel(-1, 2, 7);
  backend.setPixel(kWidth, 2, 7);
  backend.setPixel(1, -1, 7);
  backend.setPixel(1, kHeight, 7);
  REQUIRE(setCells(backend) == 1);
  REQUIRE(backend.at(-1, 2) == 0);
  REQUIRE(backend.getPixel(kWidth, kHeight) == 0);
}

TEST_CASE("a line includes both of its ends") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.line(0, 0, 6, 3, 5);
  REQUIRE(backend.at(0, 0) == 5);
  REQUIRE(backend.at(6, 3) == 5);
  REQUIRE(setCells(backend) == 7);  // one pixel per column of the run

  // A diagonal of a square is one pixel per row, corners included.
  BitmapGraphicsBackend square(kWidth, kHeight);
  square.line(0, 0, 7, 7, 5);
  REQUIRE(square.at(0, 0) == 5);
  REQUIRE(square.at(7, 7) == 5);
  REQUIRE(square.at(4, 4) == 5);
  REQUIRE(setCells(square) == 8);

  // A single point is a line whose ends coincide.
  BitmapGraphicsBackend point(kWidth, kHeight);
  point.line(3, 3, 3, 3, 5);
  REQUIRE(setCells(point) == 1);
  REQUIRE(point.at(3, 3) == 5);
}

TEST_CASE("a rectangle is the outline of its box") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.rectangle(2, 1, 6, 4, 3);
  REQUIRE(backend.at(2, 1) == 3);   // a corner
  REQUIRE(backend.at(6, 4) == 3);   // the other one
  REQUIRE(backend.at(4, 1) == 3);   // the top edge
  REQUIRE(backend.at(4, 4) == 3);   // the bottom one
  REQUIRE(backend.at(2, 3) == 3);   // the left one
  REQUIRE(backend.at(6, 3) == 3);   // the right one
  REQUIRE(backend.at(4, 3) == 0);   // and the inside is untouched
  REQUIRE(setCells(backend) == 2 * 5 + 2 * 2);  // two columns of 4, two rows of 3

  // The corners may come in any order: a program that computes them has no
  // reason to sort them.
  BitmapGraphicsBackend reversed(kWidth, kHeight);
  reversed.rectangle(6, 4, 2, 1, 3);
  REQUIRE(reversed.pixels() == backend.pixels());
}

TEST_CASE("an ellipse is a centre and two radii") {
  // Not a bounding box: `ОКРУЖНОСТЬ(X, Y, R, Цвет)` passes its four numbers
  // straight through, and reading them as a box drew every circle of
  // `examples/drawing.pld` as a flat line.
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.ellipse(5, 3, 5, 3, 4);
  REQUIRE(backend.at(0, 3) == 4);   // the left extreme
  REQUIRE(backend.at(10, 3) == 4);  // the right one
  REQUIRE(backend.at(5, 0) == 4);   // the top one
  REQUIRE(backend.at(5, 6) == 4);   // the bottom one
  REQUIRE(backend.at(5, 3) == 0);   // an outline, not a disc
  REQUIRE(backend.at(0, 0) == 0);   // and a corner of the box is outside it

  // Every drawn cell is inside the box, and every row of it has at least one:
  // the outline is closed where `ЗАКРАСКА` will look for a wall.
  for (int y = 0; y < kHeight; ++y) {
    bool row = false;
    for (int x = 0; x < kWidth; ++x) {
      if (backend.at(x, y) == 4) {
        REQUIRE(x <= 10);
        row = true;
      }
    }
    if (y <= 6) {
      REQUIRE(row);
    }
  }

  // A radius that is not there draws the segment (or the point) it shrank to,
  // and a radius is a length: a negative one is the same shape.
  BitmapGraphicsBackend flat(kWidth, kHeight);
  flat.ellipse(5, 4, 3, 0, 4);
  REQUIRE(flat.at(2, 4) == 4);
  REQUIRE(flat.at(8, 4) == 4);
  REQUIRE(setCells(flat) == 7);

  BitmapGraphicsBackend point(kWidth, kHeight);
  point.ellipse(2, 2, 0, 0, 4);
  REQUIRE(setCells(point) == 1);
  REQUIRE(point.at(2, 2) == 4);

  BitmapGraphicsBackend negative(kWidth, kHeight);
  negative.ellipse(5, 3, -5, -3, 4);
  REQUIRE(negative.pixels() == backend.pixels());
}

TEST_CASE("a fill stops at a wall of another colour") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.rectangle(2, 1, 9, 6, 5);  // a frame
  backend.floodFill(5, 3, 7);        // fill its inside

  REQUIRE(backend.at(5, 3) == 7);  // the inside is filled
  REQUIRE(backend.at(3, 2) == 7);
  REQUIRE(backend.at(8, 5) == 7);
  REQUIRE(backend.at(2, 1) == 5);  // the frame is not touched
  REQUIRE(backend.at(9, 3) == 5);

  // Outside the frame is a region of its own: filling there goes round it.
  backend.floodFill(0, 0, 9);
  REQUIRE(backend.at(0, 0) == 9);
  REQUIRE(backend.at(1, 0) == 9);
  REQUIRE(backend.at(0, 7) == 9);
  REQUIRE(backend.at(2, 1) == 5);  // still the frame
  REQUIRE(backend.at(5, 3) == 7);  // and still the inside

  int inside = 0;
  for (int y = 2; y <= 5; ++y) {
    for (int x = 3; x <= 8; ++x) {
      inside += backend.at(x, y) == 7 ? 1 : 0;
    }
  }
  REQUIRE(inside == 6 * 4);
}

TEST_CASE("a fill that would change nothing does nothing") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.clearView(6);
  backend.floodFill(4, 4, 6);  // the colour is already there
  REQUIRE(setCells(backend) == kWidth * kHeight);

  // Starting outside the screen there is no area to fill at all.
  BitmapGraphicsBackend empty(kWidth, kHeight);
  empty.floodFill(-1, 0, 3);
  empty.floodFill(0, kHeight, 3);
  REQUIRE(setCells(empty) == 0);
}

TEST_CASE("a run covers its ends and the whole screen can be filled") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.vertical(2, 1, 4, 8);
  REQUIRE(backend.at(2, 1) == 8);
  REQUIRE(backend.at(2, 4) == 8);
  REQUIRE(backend.at(2, 0) == 0);
  REQUIRE(backend.at(3, 1) == 0);  // one column, not a band
  backend.horizontal(0, kWidth, 6, 9);
  REQUIRE(backend.at(0, 6) == 9);
  REQUIRE(backend.at(kWidth - 1, 6) == 9);
  REQUIRE(setCells(backend) == 4 + kWidth);
}

TEST_CASE("the whole screen can be cleared and the buffer is the size it says") {
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.clearView(11);
  REQUIRE(setCells(backend) == kWidth * kHeight);
  REQUIRE(backend.at(0, 0) == 11);
  REQUIRE(backend.at(kWidth - 1, kHeight - 1) == 11);

  // `ТОЧКА(X, Y, Цвет)` with two free coordinates is this fill, and it is what
  // the original did with it.
  BitmapGraphicsBackend fresh(kWidth, kHeight);
  fresh.setPixel(1, 1, 4);
  fresh.clearView(0);
  REQUIRE(setCells(fresh) == 0);
}

TEST_CASE("the interpreter draws into the bitmap and reads it back") {
  auto backend = std::make_shared<BitmapGraphicsBackend>(kWidth, kHeight);
  const auto result = runProgram(
      "?ТОЧКА(1, 2, 9), ТОЧКА(1, 2, Ц).\n"
      "?ТОЧКА(3, 1, 5), ЛИНИЯ(0, 7, 7, 7, 2).\n"
      "?ТОЧКА(X, Y, 6), ТОЧКА(4, 4, Ю).\n",
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  // The read gives back exactly what the write put there — the reason a cell
  // holds the program's colour value and not an RGB word.
  REQUIRE(result.output.find("Ц=9") != std::string::npos);
  REQUIRE(result.output.find("Ю=6") != std::string::npos);
  REQUIRE(backend->at(0, 0) == 6);
  REQUIRE(backend->at(1, 2) == 6);  // the last query filled the whole screen
}

TEST_CASE("a fill reads the pixels the program itself drew") {
  // This is why the pixels live inside the engine: the fill has to read cells
  // the same query just wrote, and a front-end on the other side of a pipe is
  // asked nothing in the middle of a built-in.
  auto backend = std::make_shared<BitmapGraphicsBackend>(kWidth, kHeight);
  const auto result = runProgram(
      "?ЛИНИЯ(2, 1, 8, 1, 5), ЛИНИЯ(2, 5, 8, 5, 5),\n"
      "  ЛИНИЯ(2, 1, 2, 5, 5), ЛИНИЯ(8, 1, 8, 5, 5),\n"
      "  ЗАКРАСКА(5, 3, 7), ТОЧКА(5, 3, В).\n",
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output.find("В=7") != std::string::npos);
  REQUIRE(backend->at(2, 1) == 5);  // the wall
  REQUIRE(backend->at(5, 3) == 7);  // and what the fill put inside it
}

TEST_CASE("every primitive is reported, and a read is not") {
  std::vector<GraphicsEvent> events;
  auto backend = std::make_shared<BitmapGraphicsBackend>(kWidth, kHeight);
  backend->setSink([&events](const GraphicsEvent& event) { events.push_back(event); });

  const auto result = runProgram(
      "?ТОЧКА(1, 2, 3).\n"
      "?ТОЧКА(1, 2, Ц).\n"        // a read: no event
      "?ЛИНИЯ(0, 0, 6, 3, 5).\n"
      "?ЛИНИЯ(2, Y, 1, 4, 5).\n"  // a vertical run
      "?ОКРУЖНОСТЬ(6, 3, 2, 4).\n"
      "?ЗАКРАСКА(1, 1, 9).\n"
      "?ТОЧКА(X, Y, 6).\n",       // the whole screen
      "", backend);

  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(events.size() == 6);
  REQUIRE(events[0].op == GraphicsOp::SetPixel);
  REQUIRE(events[0].x1 == 1);
  REQUIRE(events[0].y1 == 2);
  REQUIRE(events[0].color == 3);
  REQUIRE(events[1].op == GraphicsOp::Line);
  REQUIRE(events[1].x2 == 6);
  REQUIRE(events[2].op == GraphicsOp::Vertical);
  REQUIRE(events[2].x1 == 2);  // the column
  REQUIRE(events[2].y1 == 1);  // from row 1
  REQUIRE(events[2].x2 == 2);  // the same column
  REQUIRE(events[2].y2 == 4);  // to row 4
  REQUIRE(events[3].op == GraphicsOp::Ellipse);
  REQUIRE(events[3].color == 4);
  REQUIRE(events[4].op == GraphicsOp::FloodFill);
  REQUIRE(events[4].x1 == 1);
  REQUIRE(events[5].op == GraphicsOp::ClearView);
  REQUIRE(events[5].color == 6);
}

TEST_CASE("a coordinate far outside the screen is clipped, not wrapped") {
  // `10**18` overflows the arithmetic a rasteriser needs, and the front-end's
  // integers do not wrap: the two pictures would part ways.  Both clamp to
  // `kCoordinateLimit`, and a line through the screen still crosses it.
  BitmapGraphicsBackend backend(kWidth, kHeight);
  backend.line(0, 0, 1'000'000'000'000'000'000LL, 0, 4);
  REQUIRE(backend.at(0, 0) == 4);
  REQUIRE(backend.at(kWidth - 1, 0) == 4);
  REQUIRE(setCells(backend) == kWidth);

  BitmapGraphicsBackend below(kWidth, kHeight);
  below.line(0, 1'000'000'000'000'000'000LL, kWidth - 1, 1'000'000'000'000'000'000LL, 4);
  REQUIRE(setCells(below) == 0);  // the whole line lives below the screen
}
