#include <catch2/catch_test_macros.hpp>

#include <memory>

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
  REQUIRE(backend->calls()[0].kind == GraphicsCall::Kind::SetPixel);
  REQUIRE(backend->calls()[0].x1 == 10);
  REQUIRE(backend->calls()[0].y1 == 20);
  REQUIRE(backend->calls()[0].color == 3);
  REQUIRE(backend->calls()[1].kind == GraphicsCall::Kind::Line);
  REQUIRE(backend->calls()[1].x2 == 100);
  REQUIRE(backend->calls()[2].kind == GraphicsCall::Kind::Ellipse);
  REQUIRE(backend->calls()[3].kind == GraphicsCall::Kind::FloodFill);
}

TEST_CASE("ТОЧКА with a variable reads a pixel colour") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram("?ТОЧКА(1, 2, C).\n", "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.output == "C=0\n");
  REQUIRE(backend->calls().size() == 1);
  REQUIRE(backend->calls()[0].kind == GraphicsCall::Kind::GetPixel);
}

TEST_CASE("graphics predicates reject free coordinates where they are required") {
  auto backend = std::make_shared<RecordingGraphicsBackend>();
  const auto result = runProgram("?ЗАКРАСКА(X, 1, 2).\n", "", backend);
  REQUIRE(result.loaded);
  REQUIRE(result.error.find("ЗАКРАСКА") != std::string::npos);
}
