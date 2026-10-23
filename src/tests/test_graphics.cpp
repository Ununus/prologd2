#include <catch2/catch_test_macros.hpp>

#include <memory>
#include <string>
#include <vector>

#include "prlib/graphics.hpp"
#include "test_helpers.hpp"

using namespace prologd;
using prologd::test::runProgram;

TEST_CASE("graphics predicates call the backend") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram(
      "?ТОЧКА(10, 20, 3).\n"
      "?ЛИНИЯ(0, 0, 100, 100, 4).\n"
      "?ОКРУЖНОСТЬ(50, 50, 10, 7).\n"
      "?ЗАКРАСКА(50, 50, 15).\n",
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nДА\nДА\n");
  REQUIRE(backend->calls().size() == 4);
  REQUIRE(backend->calls()[0].op == GraphicsOp::SetPixel);
  REQUIRE(backend->calls()[0].x1 == 10);
  REQUIRE(backend->calls()[0].y1 == 20);
  REQUIRE(backend->calls()[0].color == 3);
  REQUIRE(backend->calls()[1].op == GraphicsOp::Line);
  REQUIRE(backend->calls()[1].x2 == 100);
  REQUIRE(backend->calls()[2].op == GraphicsOp::Ellipse);
  REQUIRE(backend->calls()[3].op == GraphicsOp::FloodFill);
}

TEST_CASE("point with a variable reads a pixel colour") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram("?ТОЧКА(1, 2, C).\n", "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "C=0\n");
  REQUIRE(backend->calls().size() == 1);
  REQUIRE(backend->calls()[0].op == GraphicsOp::GetPixel);
}

TEST_CASE("graphics predicates reject free coordinates where they are required") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram("?ЗАКРАСКА(X, 1, 2).\n", "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.error.find("ЗАКРАСКА") != std::string::npos);
}

TEST_CASE("free arguments choose the mode of the point predicate") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram(
      "?ТОЧКА(X, Y, 3).\n"   // two free coordinates clear the view
      "?ТОЧКА(1, Y, 3).\n"   // a free Y draws a vertical line
      "?ТОЧКА(X, 2, 3).\n",  // and a free X a horizontal one
      "", backend);
  REQUIRE(result.loaded);
  // A query with a free variable reports the bindings, not `ДА`.
  REQUIRE(result.output == "X=_1\nY=_1\nY=_1\nX=_1\n");
  REQUIRE(backend->calls().size() == 3);
  REQUIRE(backend->calls()[0].op == GraphicsOp::ClearView);
  REQUIRE(backend->calls()[1].op == GraphicsOp::Vertical);
  // A vertical line at `X` covers the whole height; a horizontal one covers the
  // whole width *at the row given*.  The horizontal line used to pass its row as
  // the second endpoint, i.e. it landed at row `width` — outside the screen, so
  // `ТОЧКА(X, 2, Ц)` drew nothing at all (part 158).
  REQUIRE(backend->calls()[1].x1 == 1);
  REQUIRE(backend->calls()[1].y1 == 0);
  REQUIRE(backend->calls()[1].y2 == 600);
  REQUIRE(backend->calls()[2].x1 == 0);
  REQUIRE(backend->calls()[2].x2 == 600);
  REQUIRE(backend->calls()[2].y1 == 2);
  REQUIRE(backend->calls()[2].op == GraphicsOp::Horizontal);

  // Three free arguments are not a mode at all.
  const auto allFree = runProgram("?ТОЧКА(X, Y, Z).\n", "", backend);
  REQUIRE(allFree.loaded);
  REQUIRE(allFree.runtimeError);
  REQUIRE(allFree.error.find("ТОЧКА: Недопустимый тип аргументов") != std::string::npos);
}

TEST_CASE("the rectangle form of the fill draws one line per row") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram(
      "?ЗАКРАСКА(10, 20, 30, 24, 7).\n"    // five rows, borders included
      "?ЗАКРАСКА(30, 24, 10, 20, 7).\n"    // the corners may come in any order
      "?ЗАКРАСКА(-5, -5, 700, 2, 7).\n",   // rows off the screen are dropped
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE(backend->calls().size() == 5 + 5 + 3);
  REQUIRE(backend->calls()[0].op == GraphicsOp::Horizontal);
  REQUIRE(backend->calls()[0].x1 == 10);
  REQUIRE(backend->calls()[0].x2 == 30);
  REQUIRE(backend->calls()[0].y1 == 20);
  REQUIRE(backend->calls()[4].y1 == 24);
  // Swapped corners give the same picture, row for row.
  REQUIRE(backend->calls()[5].x1 == 10);
  REQUIRE(backend->calls()[5].y1 == 20);
  REQUIRE(backend->calls()[9].y1 == 24);
  // The third call reaches the screen at rows 0, 1 and 2 only.
  REQUIRE(backend->calls()[10].y1 == 0);
  REQUIRE(backend->calls()[10].x1 == -5);
  REQUIRE(backend->calls()[10].x2 == 700);
  REQUIRE(backend->calls()[12].y1 == 2);
}

TEST_CASE("the rectangle form of the fill refuses a free argument") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram("?ЗАКРАСКА(X, 1, 2, 3, 4).\n", "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("ЗАКРАСКА: Недопустимый тип аргументов") != std::string::npos);
  REQUIRE(backend->calls().empty());
}

TEST_CASE("free arguments choose the mode of the line and circle predicates") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram(
      "?ЛИНИЯ(1, Y, 2, 3, 4).\n"       // a vertical line from y=2 to y=3
      "?ЛИНИЯ(1, 2, X, 3, 4).\n"       // a horizontal one from x=1 to x=3
      "?ЛИНИЯ(1, Y, 2, X, 4).\n"       // a filled rectangle
      "?ЛИНИЯ(X, 1, Y, 1, 4).\n"       // free ends: the whole screen
      "?ОКРУЖНОСТЬ(1, 2, 3, 4).\n"     // a circle
      "?ОКРУЖНОСТЬ(1, Y, 3, 4).\n"     // a filled band across the screen
      "?ОКРУЖНОСТЬ(X, 2, 3, 4).\n"
      "?ОКРУЖНОСТЬ(X, Y, 3, 4).\n",    // and the whole screen again
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Y=_1\nX=_1\nY=_1\nX=_1\nX=_1\nY=_1\nДА\nY=_1\nX=_1\nX=_1\nY=_1\n");
  REQUIRE(backend->calls().size() == 8);
  REQUIRE(backend->calls()[0].op == GraphicsOp::Vertical);
  REQUIRE(backend->calls()[1].op == GraphicsOp::Horizontal);
  REQUIRE(backend->calls()[2].op == GraphicsOp::Rectangle);
  REQUIRE(backend->calls()[3].op == GraphicsOp::Rectangle);
  REQUIRE(backend->calls()[4].op == GraphicsOp::Ellipse);
  REQUIRE(backend->calls()[5].op == GraphicsOp::Rectangle);
  REQUIRE(backend->calls()[6].op == GraphicsOp::Rectangle);
  REQUIRE(backend->calls()[7].op == GraphicsOp::ClearView);
}

TEST_CASE("a coordinate that is not a number is an error") {
  // Every non-free argument has to be an integer (an expression is evaluated).
  // The call sites used to dereference an empty `optional`, which is undefined
  // behaviour: these calls were accepted and drew with whatever was in memory.
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const std::vector<std::string> cases = {
      "ТОЧКА(a, 1, 2)",        "ТОЧКА(\"1\", 1, 2)",   "ТОЧКА([1], 1, 2)",
      "ТОЧКА(1, a, 2)",        "ТОЧКА(1, 2, a)",        "ТОЧКА(1, 2, [a])",
      "ЛИНИЯ(a, 1, 2, 3, 4)",  "ЛИНИЯ(1, 1, 2, 3, a)",  "ЛИНИЯ(1, 1, 2, a, 4)",
      "ОКРУЖНОСТЬ(a, 1, 2, 3)", "ОКРУЖНОСТЬ(1, 1, 2, a)",
      "ЗАКРАСКА(a, 1, 2)",     "ЗАКРАСКА(1, 1, a)",
  };
  for (const std::string& goal : cases) {
    const auto result = runProgram("? " + goal + ".\n", "", backend);
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Недопустимый тип аргументов") != std::string::npos);
  }
  REQUIRE(backend->calls().empty());
}

TEST_CASE("a real coordinate is truncated, an expression is evaluated") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram(
      "?ТОЧКА(1.5, 2.5, 3).\n"
      "?ТОЧКА(#1+1#, #2*2#, #3#).\n",
      "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\n");
  REQUIRE(backend->calls().size() == 2);
  // A real is truncated towards zero, as in every other integer argument.
  REQUIRE(backend->calls()[0].x1 == 1);
  REQUIRE(backend->calls()[0].y1 == 2);
  REQUIRE(backend->calls()[1].x1 == 2);
  REQUIRE(backend->calls()[1].y1 == 4);
  REQUIRE(backend->calls()[1].color == 3);
}
