#include <catch2/catch_test_macros.hpp>

#include "test_helpers.hpp"

using prologd::test::runProgram;

TEST_CASE("factorial") {
  const auto result = runProgram(
      "факториал(0, 1).\n"
      "факториал(N, F) :- БОЛЬШЕ(N, 0), факториал(#N-1#, X), УМНОЖЕНИЕ(X, N, F).\n"
      "?факториал(10, F).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "F=3628800\n");
}

TEST_CASE("Fibonacci") {
  const auto result = runProgram(
      "фиб(0, 0).\n"
      "фиб(1, 1).\n"
      "фиб(N, F) :- БОЛЬШЕ(N, 1), фиб(#N-1#, A), фиб(#N-2#, B), СЛОЖЕНИЕ(A, B, F).\n"
      "?фиб(15, F).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "F=610\n");
}

TEST_CASE("greatest common divisor") {
  const auto result = runProgram(
      "нод(A, 0, A).\n"
      "нод(A, B, G) :- БОЛЬШЕ(B, 0), нод(B, #A mod B#, G).\n"
      "?нод(1071, 462, G).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "G=21\n");
}

TEST_CASE("insertion sort") {
  const auto result = runProgram(
      "вставка(X, [], [X]).\n"
      "вставка(X, [H|T], [X,H|T]) :- НЕ(БОЛЬШЕ(X, H)), !.\n"
      "вставка(X, [H|T], [H|R]) :- вставка(X, T, R).\n"
      "сорт([], []).\n"
      "сорт([H|T], R) :- сорт(T, S), вставка(H, S, R).\n"
      "?сорт([5,3,8,1,9,2], R).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "R=[1,2,3,5,8,9]\n");
}

TEST_CASE("N-queens counted with findall") {
  const auto result = runProgram(
      "ферзь(0, N, [], A) :- список(N, A), !.\n"
      "ферзь(N, M, [[N,X]|A], C) :- ферзь(#N-1#, #M+1#, A, B), выбрать(X, B, C),\n"
      "                            можно([N,X], A).\n"
      "список(0, []).\n"
      "список(N, [N|A]) :- список(#N-1#, A).\n"
      "выбрать(X, [X|A], A).\n"
      "выбрать(X, [Y|A], [Y|B]) :- выбрать(X, A, B).\n"
      "можно(_, []) :- !.\n"
      "можно(A, [B|C]) :- НЕ(нельзя(A, B)), можно(A, C).\n"
      "нельзя([A,_], [A,_]) :- !.\n"
      "нельзя([_,A], [_,A]) :- !.\n"
      "нельзя([A,B], [C,D]) :- ABS(#A-C#, E), ABS(#B-D#, F), РАВНО(E, F).\n"
      "ферзи(N, A) :- ферзь(N, 0, A, []).\n"
      "?НАЙТИВСЕ(1, ферзи(4, A), L).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output == "A=_1\nL=[1,1]\n");
}

TEST_CASE("knapsack") {
  const auto result = runProgram(
      "вещь(а, 2, 3).\n"
      "вещь(б, 3, 4).\n"
      "вещь(в, 4, 5).\n"
      "вещь(г, 5, 6).\n"
      "рюкзак([], 0, 0, []).\n"
      "рюкзак([И|Х], В, Ц, [И|Взято]) :-\n"
      "    вещь(И, В1, Ц1), рюкзак(Х, В2, Ц2, Взято),\n"
      "    СЛОЖЕНИЕ(В1, В2, В), СЛОЖЕНИЕ(Ц1, Ц2, Ц).\n"
      "рюкзак([_|Х], В, Ц, Взято) :- рюкзак(Х, В, Ц, Взято).\n"
      "подходит(Взято) :- рюкзак([а,б,в,г], В, _, Взято), РАВНО(В, 7).\n"
      "?НАЙТИВСЕ(Взято, подходит(Взято), L).\n"
      "?рюкзак([а,в], В, Ц, Взято).\n");
  REQUIRE(result.loaded);
  REQUIRE(result.output ==
          "Взято=_1\n"
          "L=[[а,г],[б,в]]\n"
          "В=6\n"
          "Ц=8\n"
          "Взято=[а,в]\n"
          "В=2\n"
          "Ц=3\n"
          "Взято=[а]\n"
          "В=4\n"
          "Ц=5\n"
          "Взято=[в]\n"
          "В=0\n"
          "Ц=0\n"
          "Взято=[]\n");
}
