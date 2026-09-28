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

}  // namespace

BuiltinResult builtinPoint(Engine& engine, std::span<const Term> args) {
  const bool free_x = isFree(engine, args[0]);
  const bool free_y = isFree(engine, args[1]);
  const bool free_color = isFree(engine, args[2]);
  GraphicsBackend& graphics = engine.graphics();
  if (!free_x && !free_y && !free_color) {
    graphics.setPixel(*intArg(engine, args[0]), *intArg(engine, args[1]),
                      static_cast<unsigned>(*intArg(engine, args[2])));
    return BuiltinResult::Continue;
  }
  if (!free_x && !free_y && free_color) {
    const unsigned color = graphics.getPixel(*intArg(engine, args[0]), *intArg(engine, args[1]));
    return unifyInteger(engine, args[2], BigInt(static_cast<std::int64_t>(color)))
               ? BuiltinResult::Continue
               : BuiltinResult::Fail;
  }
  if (!free_x && free_y && !free_color) {
    graphics.vertical(*intArg(engine, args[0]), 0, graphics.height(),
                      static_cast<unsigned>(*intArg(engine, args[2])));
    return BuiltinResult::Continue;
  }
  if (free_x && !free_y && !free_color) {
    graphics.horizontal(0, *intArg(engine, args[1]), graphics.width(),
                        static_cast<unsigned>(*intArg(engine, args[2])));
    return BuiltinResult::Continue;
  }
  if (free_x && free_y && !free_color) {
    graphics.clearView(static_cast<unsigned>(*intArg(engine, args[2])));
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
    graphics.line(*intArg(engine, args[0]), *intArg(engine, args[1]),
                  *intArg(engine, args[2]), *intArg(engine, args[3]),
                  static_cast<unsigned>(*intArg(engine, args[4])));
    return BuiltinResult::Continue;
  }
  const unsigned color = static_cast<unsigned>(*intArg(engine, args[4]));
  if (!free_a1 && free_a2 && !free_a3 && !free_a4) {
    graphics.vertical(*intArg(engine, args[0]), *intArg(engine, args[2]),
                      *intArg(engine, args[3]), color);
    return BuiltinResult::Continue;
  }
  if (!free_a1 && !free_a2 && free_a3 && !free_a4) {
    graphics.horizontal(*intArg(engine, args[0]), *intArg(engine, args[1]),
                        *intArg(engine, args[3]), color);
    return BuiltinResult::Continue;
  }
  if (!free_a1 && free_a2 && !free_a3 && free_a4) {
    graphics.rectangle(*intArg(engine, args[0]), 0, *intArg(engine, args[2]),
                       graphics.height(), color);
    return BuiltinResult::Continue;
  }
  if (free_a1 && !free_a2 && !free_a3 && free_a4) {
    graphics.rectangle(0, *intArg(engine, args[1]), graphics.width(),
                       *intArg(engine, args[2]), color);
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
    const long long radius = *intArg(engine, args[2]);
    graphics.ellipse(*intArg(engine, args[0]), *intArg(engine, args[1]), radius, radius,
                     static_cast<unsigned>(*intArg(engine, args[3])));
    return BuiltinResult::Continue;
  }
  const unsigned color = static_cast<unsigned>(*intArg(engine, args[3]));
  if (!free_a1 && free_a2 && !free_a3) {
    const long long radius = *intArg(engine, args[2]);
    graphics.rectangle(*intArg(engine, args[0]) - radius, 0,
                       *intArg(engine, args[0]) + radius, graphics.height(), color);
    return BuiltinResult::Continue;
  }
  if (free_a1 && !free_a2 && !free_a3) {
    const long long radius = *intArg(engine, args[2]);
    graphics.rectangle(0, *intArg(engine, args[1]) - radius, graphics.width(),
                       *intArg(engine, args[1]) + radius, color);
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
  engine.graphics().floodFill(*intArg(engine, args[0]), *intArg(engine, args[1]),
                              static_cast<unsigned>(*intArg(engine, args[2])));
  return BuiltinResult::Continue;
}

}  // namespace prologd
