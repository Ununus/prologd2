#include <catch2/catch_test_macros.hpp>

#include "prlib/engine.hpp"

using namespace prologd;

namespace {

Term var(Engine& engine, const std::string& name) {
  return makeVar(engine.allocateVar(name), name);
}

}  // namespace

TEST_CASE("unify variables and atoms") {
  Engine engine;
  Term x = var(engine, "X");
  REQUIRE(engine.unify(x, makeAtom("a")));
  REQUIRE(engine.deref(x).text == "a");
}

TEST_CASE("unify chains and repeated variables") {
  Engine engine;
  Term x = var(engine, "X");
  Term y = var(engine, "Y");
  REQUIRE(engine.unify(x, y));
  REQUIRE(engine.unify(y, makeInt(42)));
  REQUIRE(engine.deref(x).integer == BigInt(42));
  REQUIRE_FALSE(engine.unify(x, makeInt(43)));
}

TEST_CASE("atoms and strings are interchangeable") {
  Engine engine;
  REQUIRE(engine.unify(makeAtom("да"), makeString("да")));
  REQUIRE_FALSE(engine.unify(makeAtom("да"), makeString("нет")));
}

TEST_CASE("integers and floats unify by value") {
  Engine engine;
  REQUIRE(engine.unify(makeInt(6), makeFloat(6.0)));
  REQUIRE_FALSE(engine.unify(makeInt(6), makeFloat(6.5)));
  REQUIRE(engine.unify(makeInt(-5), makeFloat(-5.0)));
  REQUIRE_FALSE(engine.unify(makeInt(2), makeFloat(-2.0)));
  // The comparison is exact, in both directions and at any size: narrowing the
  // integer to `float` first made `16777217` equal `16777216.0`, and comparing
  // the integer's nearest double made `10^20 + 1` equal `10^20.0`.
  REQUIRE(engine.unify(makeInt(16777217), makeFloat(16777217.0)));
  REQUIRE_FALSE(engine.unify(makeInt(16777217), makeFloat(16777216.0)));
  REQUIRE(engine.unify(makeInt(BigInt("100000000000000000000")), makeFloat(1e20)));
  REQUIRE_FALSE(engine.unify(makeInt(BigInt("100000000000000000001")), makeFloat(1e20)));
  REQUIRE(engine.unify(makeFloat(1e20), makeInt(BigInt("100000000000000000000"))));
}

TEST_CASE("compound unification") {
  Engine engine;
  const Term a = makeCompound("f", {makeInt(1), makeAtom("a")});
  const Term b = makeCompound("f", {makeInt(1), makeAtom("a")});
  const Term c = makeCompound("f", {makeInt(2), makeAtom("a")});
  REQUIRE(engine.unify(a, b));
  REQUIRE_FALSE(engine.unify(a, c));
}

TEST_CASE("list unification binds head and tail") {
  Engine engine;
  Term head = var(engine, "H");
  Term tail = var(engine, "T");
  const Term pattern = makeList(head, tail);
  const Term list = makeListFromVector({makeInt(1), makeInt(2), makeInt(3)});
  REQUIRE(engine.unify(pattern, list));
  REQUIRE(engine.deref(head).integer == BigInt(1));
  std::vector<Term> elements;
  REQUIRE(listToVector(engine.deref(tail), elements));
  REQUIRE(elements.size() == 2);
}

TEST_CASE("arithmetic expressions evaluate during unification") {
  Engine engine;
  const Term expression =
      makeCompound("$expr", {makeCompound("+", {makeInt(1), makeInt(2)})});
  REQUIRE(engine.unify(expression, makeInt(3)));
  REQUIRE_FALSE(engine.unify(expression, makeInt(4)));
}

TEST_CASE("unwind restores bindings") {
  Engine engine;
  Term x = var(engine, "X");
  const std::size_t mark = engine.bindings().trailMark();
  REQUIRE(engine.unify(x, makeAtom("a")));
  engine.bindings().unwind(mark);
  REQUIRE(engine.deref(x).kind == TermKind::Var);
}
