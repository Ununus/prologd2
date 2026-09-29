#include <catch2/catch_test_macros.hpp>

#include <string>

#include "test_helpers.hpp"

using prologd::test::runProgram;

namespace {

/// A type error is a runtime error, not a failure: the message names the
/// predicate (see `badArguments`).
void checkBadArguments(const std::string& goal, const std::string& predicate) {
  const auto result = runProgram("? " + goal + ".\n");
  REQUIRE(result.loaded);
  REQUIRE(result.runtimeError);
  REQUIRE(result.error.find(predicate + ": Недопустимый тип аргументов") != std::string::npos);
}

}  // namespace

TEST_CASE("counts clauses by name") {
  const auto result = runProgram(
      "пример(1) :- пример(3).\n"
      "пример(2).\n"
      "?СКОЛЬКО(пример, N).\n"
      "?СКОЛЬКО(пример, 2).\n"
      "?СКОЛЬКО(пример, 3).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "N=2\nДА\nНЕТ\n");
}

TEST_CASE("the clause counter counts every arity of a name") {
  // Ни одного предложения с таким именем — это ноль, а не ошибка.
  const auto empty = runProgram("?СКОЛЬКО(нет, N).\n?СКОЛЬКО(нет, 0).\n?СКОЛЬКО(нет, 1).\n");
  REQUIRE(empty.loaded);
  REQUIRE(empty.output == "N=0\nДА\nНЕТ\n");

  // Имя считается целиком: предложения разной арности складываются.
  const auto mixed = runProgram(
      "прим(1).\n"
      "прим(1, 2).\n"
      "?СКОЛЬКО(прим, N).\n"
      "?СКОЛЬКО(прим, 2).\n"
      "?СКОЛЬКО(прим, 1).\n");
  REQUIRE(mixed.loaded);
  REQUIRE(mixed.output == "N=2\nДА\nНЕТ\n");

  // Дробное число усекается, как и во всех целочисленных аргументах, а имя
  // можно передать строкой: для имени строка и атом — одно и то же.
  const auto lenient = runProgram(
      "прим(1).\n"
      "?СКОЛЬКО(прим, 1.0).\n"
      "?СКОЛЬКО(прим, 1.5).\n"
      "?СКОЛЬКО(\"прим\", N).\n");
  REQUIRE(lenient.loaded);
  REQUIRE(lenient.output == "ДА\nДА\nN=1\n");
}

TEST_CASE("the clause counter: a bad name or count is an error") {
  for (const std::string& goal : {"СКОЛЬКО(5, N)", "СКОЛЬКО(X, N)", "СКОЛЬКО(прим, \"1\")"}) {
    checkBadArguments(goal, "СКОЛЬКО");
  }
  // Арность, для которой ничего не зарегистрировано, — это неизвестный
  // предикат: цель просто терпит неудачу.
  const auto wrongArity = runProgram("прим(1).\n?СКОЛЬКО(прим).\n?СКОЛЬКО(прим, N, 1).\n");
  REQUIRE(wrongArity.loaded);
  REQUIRE_FALSE(wrongArity.runtimeError);
  REQUIRE(wrongArity.output == "НЕТ\nНЕТ\n");
}

TEST_CASE("inspects clauses") {
  const auto result = runProgram(
      "пример(1) :- пример(3).\n"
      "пример(2).\n"
      "?ПРЕДЛ(пример, 1, X, Y).\n"
      "?ПРЕДЛ(пример, 2, X, Y).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=пример(1)\nY=[пример(3)]\nX=пример(2)\nY=[]\n");
}

TEST_CASE("the clause reader numbers clauses from one") {
  const auto result = runProgram(
      "прим(1) :- прим(3).\n"
      "прим(2).\n"
      "?ПРЕДЛ(прим, 0, H, B).\n"
      "?ПРЕДЛ(прим, -1, H, B).\n"
      "?ПРЕДЛ(прим, 3, H, B).\n"
      "?ПРЕДЛ(прим, 99, H, B).\n"
      "?ПРЕДЛ(нет, 1, H, B).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("the clause reader checks the head and the body it is given") {
  const auto result = runProgram(
      "прим(1) :- прим(3).\n"
      "прим(2).\n"
      "?ПРЕДЛ(прим, 1, прим(1), B).\n"    // the head matches → body bound
      "?ПРЕДЛ(прим, 1, прим(9), B).\n"    // a wrong head is a failure
      "?ПРЕДЛ(прим, 1, H, [прим(3)]).\n"  // the body matches
      "?ПРЕДЛ(прим, 1, H, []).\n"         // a rule has a non-empty body
      "?ПРЕДЛ(прим, 2, H, []).\n");       // a fact has an empty body
  REQUIRE(result.loaded);
  REQUIRE(result.output == "B=[прим(3)]\nНЕТ\nH=прим(1)\nНЕТ\nH=прим(2)\n");
}

TEST_CASE("the clause reader renames the variables of the clause") {
  // Голова и тело получают одни и те же свежие переменные: иначе копия
  // предложения означала бы не то же самое, что исходное.
  const auto result = runProgram(
      "прим(X, Y) :- БОЛЬШЕ(X, Y).\n"
      "?ПРЕДЛ(прим, 1, H, B).\n"
      "?ПРЕДЛ(прим, 1, H2, B2).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "H=прим(_1,_2)\nB=[БОЛЬШЕ(_1,_2)]\nH2=прим(_1,_2)\nB2=[БОЛЬШЕ(_1,_2)]\n");
}

TEST_CASE("the clause reader rejects a bad name or number") {
  for (const std::string& goal : {"ПРЕДЛ(5, 1, H, B)", "ПРЕДЛ(прим, X, H, B)",
                                  "ПРЕДЛ(прим, \"1\", H, B)"}) {
    checkBadArguments(goal, "ПРЕДЛ");
  }
  // Дробный номер усекается: 1.0 — это номер 1, а 0.5 — уже ноль, то есть мимо.
  const auto fractional =
      runProgram("прим(1).\n?ПРЕДЛ(прим, 1.0, H, B).\n?ПРЕДЛ(прим, 0.5, H, B).\n");
  REQUIRE(fractional.loaded);
  REQUIRE(fractional.output == "H=прим(1)\nB=[]\nНЕТ\n");
}

TEST_CASE("converts between terms and lists") {
  const auto result = runProgram(
      "?ТЕРМ(T, [пример, 1]).\n"
      "?ТЕРМ(пример(1), L).\n"
      "?ТЕРМ(T, [пример]).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "T=пример(1)\nL=[пример,1]\nT=пример\n");
}

TEST_CASE("the term converter builds a term from a list of any length") {
  const auto result = runProgram(
      "?ТЕРМ(T, [прим]).\n"           // one element → an atom
      "?ТЕРМ(T, [прим, 1]).\n"
      "?ТЕРМ(T, [прим, 1, 2]).\n"
      "?ТЕРМ(T, [прим, [1, 2]]).\n"   // a list is an argument like any other
      "?ТЕРМ(прим, L).\n"
      "?ТЕРМ(прим(1), L).\n"
      "?ТЕРМ(прим([1]), L).\n"
      "?ТЕРМ(прим([]), L).\n");       // ...including an empty one
  REQUIRE(result.loaded);
  REQUIRE(result.output == "T=прим\nT=прим(1)\nT=прим(1,2)\nT=прим([1,2])\n"
                            "L=[прим]\nL=[прим,1]\nL=[прим,[1]]\nL=[прим,[]]\n");
}

TEST_CASE("the term converter: an empty or open list is an error, a bad shape is a failure") {
  // Пустой список не описывает ни один терм, и список с «хвостом» — тоже не
  // список: это ошибка, а не неудача.
  for (const std::string& goal : {"ТЕРМ(T, [])", "ТЕРМ(T, [прим | 1])"}) {
    const auto result = runProgram("? " + goal + ".\n");
    REQUIRE(result.loaded);
    REQUIRE(result.runtimeError);
    REQUIRE(result.error.find("неправильный список") != std::string::npos);
  }

  // Здесь строить нечего или построенное не совпадает — обычная неудача.
  const auto failures = runProgram(
      "?ТЕРМ(T, [1, 2]).\n"           // the head of the list is not a name
      "?ТЕРМ(T, [X, 1]).\n"           // an unbound head cannot name a functor
      "?ТЕРМ(T, [[1], 2]).\n"
      "?ТЕРМ(1, L).\n"                // a number is not a term to convert
      "?ТЕРМ(\"abc\", L).\n"          // nor is a string
      "?ТЕРМ(X, Y).\n"                // nothing to build from and nowhere to put it
      "?ТЕРМ(прим(1), [прим]).\n"     // [прим] is the atom прим, not прим(1)
      "?ТЕРМ(прим, [прим, 1]).\n"
      "?ТЕРМ([прим, 1], [прим, 2]).\n");
  REQUIRE(failures.loaded);
  REQUIRE(failures.output == "НЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\nНЕТ\n");
}

TEST_CASE("asserts and retracts clauses") {
  const auto result = runProgram(
      "пример(1).\n"
      "?ДОБ(пример(3), [], 1).\n"
      "?пример(X).\n"
      "?УДАЛЕНИЕ(пример, 1).\n"
      "?пример(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nX=3\nX=1\nДА\nX=1\n");
}

TEST_CASE("the assert built-in puts the clause where the position says") {
  const auto front = runProgram("прим(1).\nприм(2).\n?ДОБ(прим(9), [], 1).\n?прим(X).\n");
  REQUIRE(front.loaded);
  REQUIRE(front.output == "ДА\nX=9\nX=1\nX=2\n");

  const auto middle =
      runProgram("прим(1).\nприм(2).\nприм(3).\n?ДОБ(прим(9), [], 2).\n?прим(X).\n");
  REQUIRE(middle.loaded);
  REQUIRE(middle.output == "ДА\nX=1\nX=9\nX=2\nX=3\n");

  // Позиция за концом — это конец.
  const auto tail = runProgram("прим(1).\nприм(2).\n?ДОБ(прим(9), [], 3).\n"
                               "?ДОБ(прим(8), [], 100).\n?прим(X).\n");
  REQUIRE(tail.loaded);
  REQUIRE(tail.output == "ДА\nДА\nX=1\nX=2\nX=9\nX=8\n");

  // Позиция меньше двух — начало, и 0 с -5 упираются туда же, куда и 1.
  const auto clamped =
      runProgram("прим(1).\n?ДОБ(прим(9), [], 0).\n?ДОБ(прим(8), [], -5).\n?прим(X).\n");
  REQUIRE(clamped.loaded);
  REQUIRE(clamped.output == "ДА\nДА\nX=8\nX=9\nX=1\n");

  // Дробная позиция усекается, как и всё остальное целочисленное.
  const auto fractional = runProgram("прим(1).\n?ДОБ(прим(9), [], 1.5).\n?прим(X).\n");
  REQUIRE(fractional.loaded);
  REQUIRE(fractional.output == "ДА\nX=9\nX=1\n");
}

TEST_CASE("the assert built-in counts positions by name and keeps arities apart") {
  // Позиция нумеруется по имени целиком, а не внутри одной арности: позиция 2
  // среди прим(1) и прим(2, 3) — это место перед прим(2, 3), то есть в группе
  // арности 1 новая цель встаёт в конец.
  const auto across = runProgram("прим(1).\nприм(2, 3).\n?ДОБ(прим(9), [], 2).\n?прим(X).\n");
  REQUIRE(across.loaded);
  REQUIRE(across.output == "ДА\nX=1\nX=9\n");

  // Новая арность заводит свою группу предложений.
  const auto newArity = runProgram("прим(1).\n?ДОБ(прим(9, 8), [], 1).\n"
                                   "?прим(X).\n?прим(X, Y).\n?СКОЛЬКО(прим, N).\n");
  REQUIRE(newArity.loaded);
  REQUIRE(newArity.output == "ДА\nX=1\nX=9\nY=8\nN=2\n");

  // Одно и то же предложение можно добавить дважды.
  const auto twice = runProgram("прим(1).\n?ДОБ(прим(9), [], 1).\n?ДОБ(прим(9), [], 1).\n"
                                "?прим(X).\n?СКОЛЬКО(прим, N).\n");
  REQUIRE(twice.loaded);
  REQUIRE(twice.output == "ДА\nДА\nX=9\nX=9\nX=1\nN=3\n");
}

TEST_CASE("the assert built-in works on an empty database and takes an atom as a fact") {
  // Голова без аргументов — это атом, и он же становится фактом нулевой
  // арности: ни `факт(X)`, ни `факт(X, Y)` его не видят.
  const auto result = runProgram("?ДОБ(факт, [], 1).\n?факт.\n?факт(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nДА\nНЕТ\n");
}

TEST_CASE("the assert built-in renumbers the variables of the clause") {
  // Переменные предложения копируются: вызывающая сторона остаётся свободной,
  // а голова и тело делят одни и те же новые переменные.
  const auto result = runProgram(
      "два(2).\n"
      "?ДОБ(четыре(X), [два(Y), УМНОЖЕНИЕ(Y, 2, X)], 1).\n"
      "?четыре(Z).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nY=_1\nZ=4\n");
}

TEST_CASE("the assert built-in rejects a head or a goal that cannot be called") {
  for (const std::string& goal : {"ДОБ(5, [], 1)", "ДОБ(X, [], 1)", "ДОБ(факт, 5, 1)",
                                  "ДОБ(факт, [], \"1\")", "ДОБ(факт, [], X)",
                                  "ДОБ(факт, [1], 1)", "ДОБ(факт, [X], 1)"}) {
    checkBadArguments(goal, "ДОБ");
  }
  // Список целей с «хвостом» — не список целей.
  const auto open = runProgram("?ДОБ(факт, [a | 1], 1).\n");
  REQUIRE(open.loaded);
  REQUIRE(open.runtimeError);
  REQUIRE(open.error.find("неправильный список") != std::string::npos);
}

TEST_CASE("asserts a rule with a body") {
  const auto result = runProgram(
      "база(1).\n"
      "?ДОБ(удвоить(X, Y), [УМНОЖЕНИЕ(X, 2, Y)], 1).\n"
      "?удвоить(5, Z).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "X=_1\nY=_1\nZ=10\n");
}

TEST_CASE("the retract built-in removes the numbered clause") {
  const auto first =
      runProgram("прим(1).\nприм(2).\nприм(3).\n?УДАЛЕНИЕ(прим, 1).\n?прим(X).\n");
  REQUIRE(first.loaded);
  REQUIRE(first.output == "ДА\nX=2\nX=3\n");

  const auto middle = runProgram("прим(1).\nприм(2).\nприм(3).\n?УДАЛЕНИЕ(прим, 2).\n"
                                 "?прим(X).\n?СКОЛЬКО(прим, N).\n");
  REQUIRE(middle.loaded);
  REQUIRE(middle.output == "ДА\nX=1\nX=3\nN=2\n");

  const auto last =
      runProgram("прим(1).\nприм(2).\nприм(3).\n?УДАЛЕНИЕ(прим, 3).\n?прим(X).\n");
  REQUIRE(last.loaded);
  REQUIRE(last.output == "ДА\nX=1\nX=2\n");

  // Номер, который был первым, снова становится первым.
  const auto twice = runProgram("прим(1).\nприм(2).\nприм(3).\n?УДАЛЕНИЕ(прим, 1).\n"
                                "?УДАЛЕНИЕ(прим, 1).\n?прим(X).\n");
  REQUIRE(twice.loaded);
  REQUIRE(twice.output == "ДА\nДА\nX=3\n");

  // Когда предложений не осталось, удалять больше нечего.
  const auto drained = runProgram("прим(1).\n?УДАЛЕНИЕ(прим, 1).\n?УДАЛЕНИЕ(прим, 1).\n"
                                  "?СКОЛЬКО(прим, N).\n");
  REQUIRE(drained.loaded);
  REQUIRE(drained.output == "ДА\nНЕТ\nN=0\n");
}

TEST_CASE("the retract built-in numbers clauses by name, across arities") {
  const auto first = runProgram("прим(1).\nприм(2, 3).\n?УДАЛЕНИЕ(прим, 1).\n"
                                "?прим(X).\n?прим(X, Y).\n");
  REQUIRE(first.loaded);
  REQUIRE(first.output == "ДА\nНЕТ\nX=2\nY=3\n");

  const auto second = runProgram("прим(1).\nприм(2, 3).\n?УДАЛЕНИЕ(прим, 2).\n"
                                 "?прим(X).\n?прим(X, Y).\n?СКОЛЬКО(прим, N).\n");
  REQUIRE(second.loaded);
  REQUIRE(second.output == "ДА\nX=1\nНЕТ\nN=1\n");
}

TEST_CASE("the retract built-in clamps a number that is out of range") {
  // Так ведёт себя исходный PrologD (см. task_12): номер меньше единицы — это
  // первое предложение, номер за концом — последнее.
  const auto result = runProgram(
      "прим(1).\n"
      "прим(2).\n"
      "прим(3).\n"
      "?УДАЛЕНИЕ(прим, 0).\n"
      "?прим(X).\n"
      "?УДАЛЕНИЕ(прим, -2).\n"
      "?прим(X).\n"
      "?УДАЛЕНИЕ(прим, 99).\n"
      "?прим(X).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "ДА\nX=2\nX=3\nДА\nX=3\nДА\nНЕТ\n");
}

TEST_CASE("the retract built-in: a name without clauses fails, a bad argument is an error") {
  const auto missing = runProgram("?УДАЛЕНИЕ(нет, 1).\n");
  REQUIRE(missing.loaded);
  REQUIRE_FALSE(missing.runtimeError);
  REQUIRE(missing.output == "НЕТ\n");

  for (const std::string& goal : {"УДАЛЕНИЕ(5, 1)", "УДАЛЕНИЕ(прим, X)",
                                  "УДАЛЕНИЕ(прим, \"1\")"}) {
    checkBadArguments(goal, "УДАЛЕНИЕ");
  }
}

TEST_CASE("changing the database during a goal does not disturb that goal") {
  // Перебор держит снимок: удаление внутри цели не укорачивает уже идущий
  // перебор, хотя сама база меняется сразу.  В первой цели удаление
  // выполняется на каждом решении, поэтому база в итоге пуста.
  const auto retract = runProgram("прим(1).\nприм(2).\nприм(3).\n"
                                  "?прим(X), УДАЛЕНИЕ(прим, 1).\n?прим(Y).\n");
  REQUIRE(retract.loaded);
  REQUIRE(retract.output == "X=1\nX=2\nX=3\nНЕТ\n");

  // Добавление видно только следующей цели, и выполняется оно столько раз,
  // сколько решений дала первая цель: отсюда два `прим(9)`.
  const auto asserted = runProgram("прим(1).\nприм(2).\n"
                                   "?прим(X), ДОБ(прим(9), [], 1).\n?прим(Y).\n");
  REQUIRE(asserted.loaded);
  REQUIRE(asserted.output == "X=1\nX=2\nY=9\nY=9\nY=1\nY=2\n");
}
