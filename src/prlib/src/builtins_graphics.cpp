#include <optional>

#include "builtins_internal.hpp"

namespace prologd {

using detail::asInteger;
using detail::badArguments;
using detail::isUnbound;
using detail::unifyInteger;

namespace {

std::optional<long long> intArg(Engine& engine, const Term& term) {
  const auto value = asInteger(engine, term);
  if (!value) {
    return std::nullopt;
  }
  return value->toInt64();
}

bool isFree(Engine& engine, const Term& term) { return isUnbound(engine, term); }

/// A coordinate or a colour that is not free.
///
/// It has to be an integer (an arithmetic expression counts: it is evaluated).
/// The call sites used to dereference the result of `asInteger` unconditionally,
/// so a real, an atom, a string or a list — anything that is not a number — was
/// undefined behaviour rather than a diagnostic.
long long coordinate(Engine& engine, const Term& term, std::string_view predicate) {
  const auto value = intArg(engine, term);
  if (!value) {
    badArguments(predicate);
  }
  return *value;
}

}  // namespace

BuiltinResult builtinPoint(Engine& engine, std::span<const Term> args) {
  const bool free_x = isFree(engine, args[0]);
  const bool free_y = isFree(engine, args[1]);
  const bool free_color = isFree(engine, args[2]);
  GraphicsBackend& graphics = engine.graphics();
  if (!free_x && !free_y && !free_color) {
    graphics.setPixel(coordinate(engine, args[0], "ТОЧКА"),
                      coordinate(engine, args[1], "ТОЧКА"),
                      static_cast<unsigned>(coordinate(engine, args[2], "ТОЧКА")));
    return BuiltinResult::Continue;
  }
  if (!free_x && !free_y && free_color) {
    const unsigned color =
        graphics.getPixel(coordinate(engine, args[0], "ТОЧКА"),
                          coordinate(engine, args[1], "ТОЧКА"));
    return unifyInteger(engine, args[2], BigInt(static_cast<std::int64_t>(color)))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }
  if (!free_x && free_y && !free_color) {
    graphics.vertical(coordinate(engine, args[0], "ТОЧКА"), 0, graphics.height(),
                      static_cast<unsigned>(coordinate(engine, args[2], "ТОЧКА")));
    return BuiltinResult::Continue;
  }
  if (free_x && !free_y && !free_color) {
    graphics.horizontal(0, coordinate(engine, args[1], "ТОЧКА"), graphics.width(),
                        static_cast<unsigned>(coordinate(engine, args[2], "ТОЧКА")));
    return BuiltinResult::Continue;
  }
  if (free_x && free_y && !free_color) {
    graphics.clearView(static_cast<unsigned>(coordinate(engine, args[2], "ТОЧКА")));
    return BuiltinResult::Continue;
  }
  badArguments("ТОЧКА");
}

BuiltinResult builtinLine(Engine& engine, std::span<const Term> args) {
  GraphicsBackend& graphics = engine.graphics();
  const bool free_a1 = isFree(engine, args[0]);
  const bool free_a2 = isFree(engine, args[1]);
  const bool free_a3 = isFree(engine, args[2]);
  const bool free_a4 = isFree(engine, args[3]);
  if (!free_a1 && !free_a2 && !free_a3 && !free_a4) {
    graphics.line(coordinate(engine, args[0], "ЛИНИЯ"), coordinate(engine, args[1], "ЛИНИЯ"),
                  coordinate(engine, args[2], "ЛИНИЯ"), coordinate(engine, args[3], "ЛИНИЯ"),
                  static_cast<unsigned>(coordinate(engine, args[4], "ЛИНИЯ")));
    return BuiltinResult::Continue;
  }
  const unsigned color = static_cast<unsigned>(coordinate(engine, args[4], "ЛИНИЯ"));
  if (!free_a1 && free_a2 && !free_a3 && !free_a4) {
    graphics.vertical(coordinate(engine, args[0], "ЛИНИЯ"), coordinate(engine, args[2], "ЛИНИЯ"),
                      coordinate(engine, args[3], "ЛИНИЯ"), color);
    return BuiltinResult::Continue;
  }
  if (!free_a1 && !free_a2 && free_a3 && !free_a4) {
    graphics.horizontal(coordinate(engine, args[0], "ЛИНИЯ"), coordinate(engine, args[1], "ЛИНИЯ"),
                        coordinate(engine, args[3], "ЛИНИЯ"), color);
    return BuiltinResult::Continue;
  }
  if (!free_a1 && free_a2 && !free_a3 && free_a4) {
    graphics.rectangle(coordinate(engine, args[0], "ЛИНИЯ"), 0,
                       coordinate(engine, args[2], "ЛИНИЯ"), graphics.height(), color);
    return BuiltinResult::Continue;
  }
  if (free_a1 && !free_a2 && !free_a3 && free_a4) {
    graphics.rectangle(0, coordinate(engine, args[1], "ЛИНИЯ"), graphics.width(),
                       coordinate(engine, args[2], "ЛИНИЯ"), color);
    return BuiltinResult::Continue;
  }
  // Two or more free coordinates fill the screen (historical behaviour).
  graphics.rectangle(0, 0, graphics.width(), graphics.height(), color);
  return BuiltinResult::Continue;
}

BuiltinResult builtinCircle(Engine& engine, std::span<const Term> args) {
  GraphicsBackend& graphics = engine.graphics();
  const bool free_a1 = isFree(engine, args[0]);
  const bool free_a2 = isFree(engine, args[1]);
  const bool free_a3 = isFree(engine, args[2]);
  if (!free_a1 && !free_a2 && !free_a3) {
    const long long radius = coordinate(engine, args[2], "ОКРУЖНОСТЬ");
    graphics.ellipse(coordinate(engine, args[0], "ОКРУЖНОСТЬ"),
                     coordinate(engine, args[1], "ОКРУЖНОСТЬ"), radius, radius,
                     static_cast<unsigned>(coordinate(engine, args[3], "ОКРУЖНОСТЬ")));
    return BuiltinResult::Continue;
  }
  const unsigned color = static_cast<unsigned>(coordinate(engine, args[3], "ОКРУЖНОСТЬ"));
  if (!free_a1 && free_a2 && !free_a3) {
    const long long radius = coordinate(engine, args[2], "ОКРУЖНОСТЬ");
    const long long x = coordinate(engine, args[0], "ОКРУЖНОСТЬ");
    graphics.rectangle(x - radius, 0, x + radius, graphics.height(), color);
    return BuiltinResult::Continue;
  }
  if (free_a1 && !free_a2 && !free_a3) {
    const long long radius = coordinate(engine, args[2], "ОКРУЖНОСТЬ");
    const long long y = coordinate(engine, args[1], "ОКРУЖНОСТЬ");
    graphics.rectangle(0, y - radius, graphics.width(), y + radius, color);
    return BuiltinResult::Continue;
  }
  graphics.clearView(color);
  return BuiltinResult::Continue;
}

BuiltinResult builtinFill(Engine& engine, std::span<const Term> args) {
  for (const Term& argument : args) {
    if (isFree(engine, argument)) {
      badArguments("ЗАКРАСКА");
    }
  }
  engine.graphics().floodFill(coordinate(engine, args[0], "ЗАКРАСКА"),
                              coordinate(engine, args[1], "ЗАКРАСКА"),
                              static_cast<unsigned>(coordinate(engine, args[2], "ЗАКРАСКА")));
  return BuiltinResult::Continue;
}

}  // namespace prologd
