#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("facts answer ground and variable queries") {
  const auto result = runProgram(
      "человек(аня).\n"
      "человек(боря).\n"
      "?человек(аня).\n"
      "?человек(витя).\n"
      "?человек(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nНЕТ\nX=аня\nX=боря\n");
}

TEST_CASE("rules and conjunction work") {
  const auto result = runProgram(
      "родитель(аня, боря).\n"
      "родитель(боря, витя).\n"
      "дед(X, Y) :- родитель(X, Z), родитель(Z, Y).\n"
      "?дед(аня, Y).\n"
      "?дед(аня, боря).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Y=витя\nНЕТ\n");
}

TEST_CASE("backtracking enumerates all solutions in order") {
  const auto result = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?член(X, [1,2,3]).\n"
      "?член(2, [1,2,3]).\n"
      "?член(9, [1,2,3]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\nX=2\nX=3\nДА\nНЕТ\n");
}

TEST_CASE("cut commits to the first clause") {
  const auto result = runProgram(
      "фактор(0, 1) :- !.\n"
      "фактор(N, F) :- фактор(#N-1#, X), УМНОЖЕНИЕ(X, N, F).\n"
      "?фактор(7, F).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "F=5040\n");
}

TEST_CASE("meta-call runs the goal") {
  const auto result = runProgram(
      "цель(5).\n"
      "проверка(X) :- ВЫП(цель(X)).\n"
      "?проверка(Y).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "Y=5\n");
}

TEST_CASE("a meta-call with extra arguments is call/N") {
  // `ВЫП(Цель, Доп...)` дописывает аргументы к цели — правило `call/N`:
  // цель всегда идёт первой, а каждый доп. аргумент — один аргумент.
  const auto compound = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?ВЫП(член(X), [1, 2]).\n");
  REQUIRE(compound.loaded);
  REQUIRE(compound.output == "X=1\nX=2\n");

  // Атом от дополнительных аргументов становится составным термом.
  const auto atom = runProgram("?ВЫП(БОЛЬШЕ, 3, 1).\n?ВЫП(РАВНО, 1, 2).\n");
  REQUIRE(atom.loaded);
  REQUIRE(atom.output == "ДА\nНЕТ\n");

  // Цель может прийти переменной: она разыменовывается до подстановки.
  // (Ответ печатает и связывание запроса: `Ц=член` — по разу на решение.)
  const auto bound = runProgram(
      "член(X, [X|_]).\n"
      "член(X, [_|T]) :- член(X, T).\n"
      "?РАВНО(Ц, член), ВЫП(Ц, X, [1, 2]).\n");
  REQUIRE(bound.loaded);
  REQUIRE(bound.output == "Ц=член\nX=1\nЦ=член\nX=2\n");
}

TEST_CASE("a meta-call with extra arguments refuses a non-callable goal") {
  for (const std::string& goal : {"ВЫП(5, 1)", "ВЫП(X, 1)"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Цель должна быть предикатом") != std::string::npos);
  }
}

TEST_CASE("a cut after a meta-call prunes the caller's choices") {
  // Отсечение после мета-вызова действует на вызывающий предикат как обычная
  // цель: второе решение `а` и второе предложение `б` уже не рассматриваются.
  // (Написать `!` *внутри* аргумента нельзя — парсер отказывает, см.
  // test_parser.cpp.)
  const auto result = runProgram(
      "а(1).\n"
      "а(2).\n"
      "б(X) :- а(X), ВЫП(РАВНО(1, 1)), !.\n"
      "б(99).\n"
      "?б(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\n");
}

TEST_CASE("negation as failure") {
  const auto result = runProgram(
      "цель(5).\n"
      "нет_цели(X) :- НЕ(цель(X)).\n"
      "?нет_цели(5).\n"
      "?нет_цели(6).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nДА\n");
}

TEST_CASE("disjunction") {
  const auto result = runProgram(
      "a(1).\n"
      "b(2).\n"
      "c(X) :- ПЕРВОЕ(a(X), b(X)).\n"
      "?c(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=1\n");
}

TEST_CASE("undefined predicates fail") {
  const auto result = runProgram("?нет_такого(1).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\n");
}

TEST_CASE("deep recursion does not overflow the C++ stack") {
  // The shape matters.  With a base clause that does *not* cut, a choice point
  // survives at the deepest level, and letting it go used to release the whole
  // frame chain inside the shared_ptr destructors — one C++ frame per level,
  // which is a real stack overflow (the command-line front-end printed the right
  // answer and then died with 0xC00000FD).  The chain release is iterative now,
  // and the depth limit is raised so that this exercises the release rather than
  // the guard.
  const auto result = runProgram(
      "л(0).\n"
      "л(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), л(Н1).\n"
      "?л(50000).\n",
      {}, nullptr, [](prologd::Engine& engine) { engine.options().maxDepth = 0; });
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\n");
  REQUIRE(result.error.empty());
}

TEST_CASE("the depth limit reports runaway recursion") {
  const auto result = runProgram(
      "л(Н) :- СЛОЖЕНИЕ(Н1, 1, Н), л(Н1).\n"
      "?л(1).\n",
      {}, nullptr, [](prologd::Engine& engine) { engine.options().maxDepth = 200; });
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find("Превышена глубина рекурсии") != std::string::npos);
  // A limit that fires names itself and its value.  It names nothing else on
  // purpose: raising it is the caller's vocabulary — a flag, a protocol field, a
  // row of a settings dialog — and the engine knows about none of them (ADR-020).
  REQUIRE(result.error.find("200") != std::string::npos);
  REQUIRE(result.error.find("--max-depth") == std::string::npos);
  REQUIRE(result.error.find("настройках") == std::string::npos);
}

TEST_CASE("every limit names itself and its value") {
  SECTION("steps") {
    const auto result = runProgram(
        "цикл :- цикл.\n"
        "?цикл.\n",
        {}, nullptr, [](prologd::Engine& engine) {
          prologd::Limits limits;
          limits.maxSteps = 1000;
          limits.applyTo(engine.options());
        });
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Превышен предел шагов") != std::string::npos);
    REQUIRE(result.error.find("1000") != std::string::npos);
    REQUIRE(result.error.find("--max-steps") == std::string::npos);
  }

  SECTION("НАЙТИВСЕ") {
    // The cap is a *diagnostic*, never a silent truncation: the answer list must
    // not come back short and look complete.  The template comes first and the
    // goal second (`НАЙТИВСЕ(Шаблон, Цель, Список)`).
    const auto result = runProgram(
        "число(0).\n"
        "число(Н) :- число(Н1), СЛОЖЕНИЕ(Н1, 1, Н).\n"
        "?НАЙТИВСЕ(Х, число(Х), С).\n",
        {}, nullptr, [](prologd::Engine& engine) {
          prologd::Limits limits;
          limits.maxFindAllSolutions = 50;
          limits.applyTo(engine.options());
        });
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("Превышен предел решений НАЙТИВСЕ") != std::string::npos);
    REQUIRE(result.error.find("50") != std::string::npos);
    REQUIRE(result.error.find("--max-findall") == std::string::npos);
  }

  SECTION("a zero means «no limit» for every one of them") {
    const auto result = runProgram(
        "число(1).\n"
        "число(2).\n"
        "число(3).\n"
        "?НАЙТИВСЕ(Х, число(Х), С), ВЫВОД(С), ПС.\n",
        {}, nullptr, [](prologd::Engine& engine) {
          prologd::Limits limits;
          limits.maxFindAllSolutions = 0;
          limits.maxDepth = 0;
          limits.maxSteps = 0;
          limits.applyTo(engine.options());
        });
    REQUIRE_FALSE(result.runtimeError);
    REQUIRE(result.output.find("[1,2,3]") != std::string::npos);
  }

  SECTION("defaults") {
    // A fresh engine has **no** limits: a limit is something the caller asks
    // for, and one record carries that request, so the CLI and the protocol
    // cannot disagree about what «nothing asked for» means (task_46).
    prologd::EngineOptions options;
    prologd::Limits().applyTo(options);
    REQUIRE(options.maxSteps == 0);
    REQUIRE(options.maxDepth == 0);
    REQUIRE(options.maxFindAllSolutions == 0);
    // The nesting guard is the exception, and it is not a limit the user sets:
    // it keeps a meta-call from growing the C++ stack of nested solvers.
    REQUIRE(options.maxNestedDepth == prologd::kDefaultMaxNestedDepth);
  }
}

TEST_CASE("quiet suppresses solution output for its query only") {
  const auto result = runProgram(
      "?ТИХО, ВЫВОД(фыв).\n"
      "?ВЫВОД(куц).\n"
      "foo(5).\n"
      "?ТИХО, foo(X).\n"
      "?foo(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "фывкуц\nДА\nX=5\n");
}
