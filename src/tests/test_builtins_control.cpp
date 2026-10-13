#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("the first line of a file says how its names are read") {
  // task_67: the marker is read by the loader *before* the file is lexed, so it is
  // the one way a file can ask for the old dialect's names — and it does not run
  // as a goal afterwards.
  // `Молоко` without quotes is a string constant in mode 1, not a variable.
  const auto result = runProgram(
      ":- ИМЕНА(1).\n"
      "?РАВНО(д, 1).\n"
      "?СЦЕП(Молоко, \" и\", Х).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "д=1\nХ=Молоко и\n");
}

TEST_CASE("the old dialect reads apostrophe names, and `2` says the same") {
  // task_77: `2` was a mode of its own until the merge, and both numbers name the
  // old dialect now — the apostrophe name is what says which reading a file got.
  const auto one = runProgram(":- ИМЕНА(1).\n?РАВНО(Сумма', 5).\n");
  REQUIRE(one.loaded);
  REQUIRE(one.output == "Сумма'=5\n");

  const auto two = runProgram(":- ИМЕНА(2).\n?РАВНО(Сумма', 5).\n");
  REQUIRE(two.loaded);
  REQUIRE(two.output == "Сумма'=5\n");
}

TEST_CASE("a marker off the first line says where it belongs") {
  // A comment above the marker makes it a plain directive — and a directive cannot
  // set a mode the text above it was already read in.  The load itself succeeds, so
  // the complaint arrives as a runtime error, not as a load failure.
  const auto result = runProgram("% комментарий\n:- ИМЕНА(1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("первой строкой") != std::string::npos);
}

TEST_CASE("the always-false goal fails and negation turns it round") {
  const auto result = runProgram("?ЛОЖЬ.\n?ЛОЖЬ, НЕ(ЛОЖЬ).\n?НЕ(ЛОЖЬ).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nНЕТ\nДА\n");
}

TEST_CASE("negation undoes the bindings of the goal it checks") {
  const auto result = runProgram(
      "?НЕ(ЛОЖЬ).\n"
      "?НЕ(НЕ(ЛОЖЬ)).\n"                      // double negation is negation
      "?НЕ(ПЕР(X)).\n"                        // ПЕР holds for a free X, so this fails
      "?НЕ(ЦЕЛ(X)).\n"                        // ЦЕЛ does not, and X stays free
      "?НЕ(ПЕР(1)).\n"
      "?НЕ((РАВНО(A, 1), ЛОЖЬ)), ПЕР(A).\n"   // the binding of A is gone
      "?НЕ((РАВНО(B, 1), ЛОЖЬ)), РАВНО(B, 2).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nНЕТ\nX=_1\nДА\nA=_1\nB=2\n");
}

TEST_CASE("`\\+` is the ISO spelling of the same negation") {
  const auto result = runProgram(
      "?\\+ ЛОЖЬ.\n"
      "?\\+ РАВНО(1, 2).\n"
      "?\\+ РАВНО(1, 1).\n"
      "?\\+ \\+ ЛОЖЬ.\n"                        // double negation is negation
      "?\\+ (ЛОЖЬ ; ЛОЖЬ).\n"
      "?\\+ (ЛОЖЬ ; РАВНО(A, 1)), ПЕР(A).\n"    // the whole disjunction is negated
      "?\\+ (ЛОЖЬ, РАВНО(B, 1)), ПЕР(B).\n");   // the binding of B is gone
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\nНЕТ\nДА\nНЕТ\nB=_1\n");
}

TEST_CASE("negation keeps what a goal did to the database") {
  // Bindings are undone, side effects are not: the database is not backtrackable
  // in PrologD, so the clause asserted inside `НЕ` survives the negation.
  const auto result = runProgram("?НЕ(ДОБ(ф(1), [], 1)).\n?ф(1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nДА\n");
}

TEST_CASE("negation answers a goal that is not a predicate with an error") {
  for (const std::string& goal : {"НЕ(5)", "НЕ(X)"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Цель должна быть предикатом") != std::string::npos);
  }

  // An atom is a goal of arity 0: an unknown one simply fails, so НЕ succeeds.
  const auto atom = runProgram("?НЕ(a).\n");
  REQUIRE(atom.loaded);
  REQUIRE_FALSE(atom.runtimeError);
  REQUIRE(atom.output == "ДА\n");

  // A wrong arity, on the other hand, is not this predicate at all: it cannot
  // ever work, and the load says so (task_40).
  const auto arity = runProgram("?НЕ(ЛОЖЬ, ЛОЖЬ).\n");
  REQUIRE_FALSE(arity.loaded);
  REQUIRE(arity.error.find("НЕ не имеет арности 2 (есть 1)") != std::string::npos);
}

TEST_CASE("the choice form succeeds when either goal does") {
  const auto result = runProgram(
      "?ПЕРВОЕ(ЛОЖЬ, НЕ(ЛОЖЬ)).\n"
      "?ПЕРВОЕ(НЕ(ЛОЖЬ), ЛОЖЬ).\n"
      "?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ).\n"
      "?ПЕРВОЕ(РАВНО(X, 1), РАВНО(X, 2)).\n"
      "?ПЕРВОЕ(ЛОЖЬ, РАВНО(Y, 2)).\n"
      "?ПЕРВОЕ(РАВНО(A, 1), РАВНО(B, 2)), РАВНО(A, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\nX=1\nY=2\nA=1\nB=_1\n");
}

TEST_CASE("the choice form commits to the first solution of its first goal") {
  // Once the first goal has succeeded the second is out of reach, and a
  // generator in the first position yields a single solution.
  const auto both = runProgram("?ПЕРВОЕ(РАВНО(X, 1), РАВНО(X, 2)), РАВНО(X, 2).\n");
  REQUIRE(both.loaded);
  REQUIRE(both.output == "НЕТ\n");

  const auto generator = runProgram("п(1).\nп(2).\n?ПЕРВОЕ(п(X), ЛОЖЬ).\n");
  REQUIRE(generator.loaded);
  REQUIRE(generator.output == "X=1\n");
}

TEST_CASE("the choice form takes any number of goals") {
  // task_51: `ПЕРВОЕ` is variadic like `ВЫВОД` — goals are tried in order, and
  // the first one that succeeds is committed to.  One goal is `ВЫП(Ц)`.
  const auto skipping = runProgram(
      "?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, РАВНО(X, 1), РАВНО(X, 2)).\n"
      "?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, ЛОЖЬ).\n"
      "?ПЕРВОЕ(РАВНО(A, 1)).\n");
  REQUIRE(skipping.loaded);
  REQUIRE_FALSE(skipping.runtimeError);
  REQUIRE(skipping.output == "X=1\nНЕТ\nA=1\n");

  // Commitment is still to the first goal that succeeds: the goals after it are
  // not reached, so the alternatives of a generator are dropped.
  const auto committed = runProgram("п(1).\nп(2).\n?ПЕРВОЕ(ЛОЖЬ, п(X), ЛОЖЬ).\n");
  REQUIRE(committed.loaded);
  REQUIRE(committed.output == "X=1\n");

  // The first goal that succeeds wins even when a later one would succeed too.
  const auto earlier = runProgram("?ПЕРВОЕ(РАВНО(X, 9), РАВНО(X, 1)).\n");
  REQUIRE(earlier.loaded);
  REQUIRE(earlier.output == "X=9\n");

  // A goal that is not a predicate is still an error, wherever it stands.
  const auto bad = runProgram("?ПЕРВОЕ(ЛОЖЬ, 5, РАВНО(X, 1)).\n");
  REQUIRE(bad.loaded);
  REQUIRE(bad.runtimeError);
  REQUIRE(bad.error.find("Цель должна быть предикатом") != std::string::npos);
}

TEST_CASE("`=` is the unification predicate") {
  // task_52: the sign is sugar — the solver sees `РАВНО/2`, so it binds,
  // reverses and fails exactly like the long form, and `;` stays the
  // disjunction around it.
  const auto result = runProgram(
      "?X = 1, Y = X.\n"
      "?1 = 2.\n"
      "?f(A) = f(2).\n"
      "?X = #1 + 1#.\n"
      "?НЕ(X = 1).\n"
      "?X = 1 ; X = 2.\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "X=1\nY=1\nНЕТ\nA=2\nX=2\nНЕТ\nX=1\nX=2\n");
}

TEST_CASE("a disjunction tries both branches and yields all their solutions") {
  // `;` is the backtrackable disjunction (task_41), unlike `ПЕРВОЕ`, which
  // commits to the first solution of the first goal that succeeds.
  const auto result = runProgram(
      "a(1).\n"
      "a(2).\n"
      "b(3).\n"
      "?a(X) ; b(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\nX=2\nX=3\n");

  // The right branch is entered only after the whole left one.
  const auto two = runProgram("?РАВНО(X, 1) ; РАВНО(X, 2).\n");
  REQUIRE(two.loaded);
  REQUIRE(two.output == "X=1\nX=2\n");

  // Both branches failing is a plain failure.
  const auto none = runProgram("?ЛОЖЬ ; ЛОЖЬ.\n");
  REQUIRE(none.loaded);
  REQUIRE(none.output == "НЕТ\n");
}

TEST_CASE("a disjunction is a goal in a rule, under negation, call and findall") {
  const auto rule = runProgram(
      "a(1).\n"
      "a(2).\n"
      "b(3).\n"
      "p(X) :- a(X) ; b(X).\n"
      "?p(X).\n");
  REQUIRE(rule.loaded);
  REQUIRE(rule.output == "X=1\nX=2\nX=3\n");

  const auto negation =
      runProgram("?НЕ((ЛОЖЬ ; ЛОЖЬ)).\n?НЕ((ЛОЖЬ ; РАВНО(X, 1))).\n");
  REQUIRE(negation.loaded);
  REQUIRE(negation.output == "ДА\nНЕТ\n");

  const auto meta = runProgram("?ВЫП((РАВНО(X, 1) ; РАВНО(X, 2))).\n");
  REQUIRE(meta.loaded);
  REQUIRE(meta.output == "X=1\nX=2\n");

  const auto findall = runProgram("?НАЙТИВСЕ(X, (РАВНО(X, 1) ; РАВНО(X, 2)), L).\n");
  REQUIRE(findall.loaded);
  REQUIRE(findall.output == "X=_1\nL=[1,2]\n");
}

TEST_CASE("the comma binds tighter than the disjunction") {
  const auto left = runProgram("?РАВНО(X, 1), ЛОЖЬ ; РАВНО(X, 2).\n");
  REQUIRE(left.loaded);
  REQUIRE(left.output == "X=2\n");

  const auto both = runProgram(
      "?РАВНО(X, 1), РАВНО(Y, 1) ; РАВНО(X, 2), РАВНО(Y, 2).\n");
  REQUIRE(both.loaded);
  REQUIRE(both.output == "X=1\nY=1\nX=2\nY=2\n");
}

TEST_CASE("a cut inside a branch is local to that branch") {
  // The branch runs in a frame of its own whose cut barrier sits above the
  // alternative, so `!` prunes what the branch created and leaves the other one
  // alone — the ISO rule, and the reason `ПЕРВОЕ` is kept for the committed
  // form.
  const auto after = runProgram("?РАВНО(X, 1), ! ; РАВНО(X, 2).\n");
  REQUIRE(after.loaded);
  REQUIRE(after.output == "X=1\nX=2\n");

  const auto first = runProgram("?!, ЛОЖЬ ; РАВНО(X, 1).\n");
  REQUIRE(first.loaded);
  REQUIRE(first.output == "X=1\n");
}

TEST_CASE("the choice form answers a goal that is not a predicate with an error") {
  for (const std::string& goal : {"ПЕРВОЕ(5, НЕ(ЛОЖЬ))", "ПЕРВОЕ(ЛОЖЬ, 5)", "ПЕРВОЕ(X, НЕ(ЛОЖЬ))"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Цель должна быть предикатом") != std::string::npos);
  }

  const auto atom = runProgram("?ПЕРВОЕ(a, НЕ(ЛОЖЬ)).\n");
  REQUIRE(atom.loaded);
  REQUIRE_FALSE(atom.runtimeError);
  REQUIRE(atom.output == "ДА\n");

  // Any positive arity is legal now (task_51): three goals answer like two.
  const auto three = runProgram("?ПЕРВОЕ(ЛОЖЬ, ЛОЖЬ, ЛОЖЬ).\n");
  REQUIRE(three.loaded);
  REQUIRE_FALSE(three.runtimeError);
  REQUIRE(three.output == "НЕТ\n");

  // Arity 0 is not: a variadic name still wants one goal at least.
  const auto none = runProgram("?ПЕРВОЕ.\n");
  REQUIRE_FALSE(none.loaded);
  REQUIRE(none.error.find("ПЕРВОЕ не имеет арности 0") != std::string::npos);
}

TEST_CASE("quiet silences the query it appears in") {
  // Quiet is a per-query flag: the next query reports as usual.  Note that the
  // answer of the silenced query carries neither `ДА` nor the bindings.
  const auto alone = runProgram("?ТИХО.\n?РАВНО(1, 1).\n");
  REQUIRE(alone.loaded);
  REQUIRE(alone.output == "ДА\n");

  const auto withBindings = runProgram("?ТИХО, РАВНО(X, 1).\n?РАВНО(1, 1).\n");
  REQUIRE(withBindings.loaded);
  REQUIRE(withBindings.output == "ДА\n");
}

TEST_CASE("the trace flags turn tracing on and off") {
  // What the trace produces is the business of the trace sink (see
  // `test_stepping.cpp`); here the two goals only have to succeed and leave the
  // query that follows alone.
  const auto result = runProgram("?ТРАССА.\n?НЕТ_ТРАССЫ.\n?РАВНО(X, 1).\n");
  REQUIRE(result.loaded);
  REQUIRE_FALSE(result.runtimeError);
  REQUIRE(result.output == "ДА\nДА\nX=1\n");
}

TEST_CASE("forall holds when no solution of the first goal fails the second") {
  const auto result = runProgram(
      "человек(аня).\n"
      "человек(боря).\n"
      "совершеннолетний(аня).\n"
      "?ДЛЯВСЕХ(человек(_Х), совершеннолетний(_Х)).\n"   // боря — контрпример
      "?ДЛЯВСЕХ(совершеннолетний(_Х), человек(_Х)).\n"
      "?ДЛЯВСЕХ(человек(_Х), человек(_Х)).\n"
      "?ДЛЯВСЕХ(ЛОЖЬ, совершеннолетний(_Х)).\n"          // решений нет — «для всех» пусто
      "?ДЛЯВСЕХ(человек(_Х), НЕ(человек(_Х))).\n"
      "?forall(человек(_Х), человек(_Х)).\n");            // английское имя
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nДА\nДА\nДА\nНЕТ\nДА\n");
}

TEST_CASE("forall leaves the bindings of the caller alone") {
  const auto result = runProgram(
      "человек(аня).\n"
      "?РАВНО(Х, 5), ДЛЯВСЕХ(человек(_Ч), человек(_Ч)), ВЫВОД(Х), ПС.\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "5\nХ=5\n");
}

TEST_CASE("forall takes goals, and the goals inside it are checked") {
  // A number is not a goal: the nested solver says so, like it does for `НЕ`.
  const auto notAGoal = runProgram("?ДЛЯВСЕХ(1, 2).\n");
  REQUIRE(notAGoal.loaded);
  REQUIRE(notAGoal.runtimeError);
  REQUIRE(notAGoal.error.find("Цель должна быть предикатом") != std::string::npos);

  // Both arguments are goals, so the call-site check opens them (`checks.cpp`): a
  // misspelled name inside is a warning, not silence.
  const auto checked =
      runProgram("человек(аня).\n?ДЛЯВСЕХ(человек(_Х), нет_такого(_Х)).\n");
  REQUIRE(checked.loaded);
  REQUIRE(checked.output == "НЕТ\n");
  REQUIRE(checked.error.find("не найдено: нет_такого/1") != std::string::npos);
}
