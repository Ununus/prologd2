#include <catch2/catch_test_macros.hpp>

#include <sstream>
#include <string>
#include <vector>

#include "prlib/engine.hpp"
#include "prlib/module_loader.hpp"

// task_40: what the interpreter says when something is wrong, with the position
// a reader can act on.  The subject here is the diagnostic itself — its code,
// its severity, its position and its exact text — so the engine's diagnostic
// hook is used instead of the console text, and the queries are not run: parsing
// and loading are enough for every case below.
//
// The expected messages are copied word for word on purpose: this text is a
// user-visible surface (a beginner reads it), and a test that only looked for
// "some message appeared" would not notice it becoming unhelpful.

namespace {

using prologd::Engine;
using prologd::ErrorCode;
using prologd::ModuleLoader;
using prologd::PrologError;
using prologd::Severity;
using prologd::SourceLocation;

/// Load a program and collect the diagnostics the engine reported.
std::vector<PrologError> diagnosticsOf(const std::string& source) {
  std::istringstream input;
  std::ostringstream output;
  std::ostringstream error;
  Engine engine;
  engine.setStreams(input, output, error);
  engine.initialize();
  std::vector<PrologError> collected;
  engine.setDiagnosticHook([&collected](const PrologError& diagnostic) {
    collected.push_back(diagnostic);
  });
  ModuleLoader loader(engine);
  std::string message;
  (void)loader.loadSource(source, "<test>", &message);
  return collected;
}

std::vector<const PrologError*> withSeverity(const std::vector<PrologError>& diagnostics,
                                             Severity severity) {
  std::vector<const PrologError*> result;
  for (const PrologError& diagnostic : diagnostics) {
    if (diagnostic.severity == severity) {
      result.push_back(&diagnostic);
    }
  }
  return result;
}

std::vector<const PrologError*> withCode(const std::vector<PrologError>& diagnostics,
                                         ErrorCode code) {
  std::vector<const PrologError*> result;
  for (const PrologError& diagnostic : diagnostics) {
    if (diagnostic.code == code) {
      result.push_back(&diagnostic);
    }
  }
  return result;
}

}  // namespace

TEST_CASE("an unclosed bracket is reported at the opening bracket") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("факт(1.\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::UnpairedBracket);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.isParseError);
  REQUIRE(error.location.file == "<test>");
  REQUIRE(error.location.line == 1);
  // Byte columns, like everywhere else in the dialect: `факт` is four letters
  // of two bytes each, so the bracket sits in the ninth column.
  REQUIRE(error.location.column == 9);
  REQUIRE(error.message == "непарные скобки: '(' открыта в строке 1");
}

TEST_CASE("a value where a functor belongs is not called an unpaired bracket") {
  // `атом(Переменная("текст")).` is bracketed correctly, and the fault is the
  // variable used as a name.  The argument list used to report the outer `(` as
  // unpaired, which sent the reader looking for a missing bracket that is there.
  const std::vector<PrologError> diagnostics = diagnosticsOf("атом(Переменная(\"текст\")).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::InvalidFunction);
  REQUIRE(error.message.find("Переменная не может быть именем функции") != std::string::npos);
  REQUIRE(error.message.find("непарные") == std::string::npos);
  // The complaint sits on the bracket the value put in front of: byte 29 ends the
  // name, so its `(` is column 30.
  REQUIRE(error.location.column == 30);
}

TEST_CASE("a string where a functor belongs says so, and the head rule keeps its own") {
  // A string is a value, and a value cannot be a functor: the same message,
  // worded for a string.
  const std::vector<PrologError> diagnostics = diagnosticsOf(
      "атом(\"текст\"(1)).\n");
  REQUIRE(diagnostics.size() == 1);
  REQUIRE(diagnostics.front().message.find("Строка не может быть именем функции") !=
          std::string::npos);
  // At the head of a clause the old message is the right one, and it stays: there
  // the fault is the variable in head position, not a call of it.
  const std::vector<PrologError> head = diagnosticsOf("Переменная(\"текст\").\n");
  REQUIRE(head.size() == 1);
  REQUIRE(head.front().message == "Голова предложения не может быть списком или переменной");
}

TEST_CASE("a missing final dot is reported at the end of the clause") {  const std::vector<PrologError> diagnostics = diagnosticsOf("факт(1)\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::InvalidSentence);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 11);  // the `)` the dot belongs after
  REQUIRE(error.message == "предложение должно заканчиваться точкой");
}

TEST_CASE("a missing dot before the next clause is reported at the end of the first") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("студент(вова, корчагин)\nстудент(данил, ахмеров).\n");
  REQUIRE_FALSE(diagnostics.empty());
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::InvalidSentence);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.message == "предложение должно заканчиваться точкой");
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 42);  // the `)` of the first line, in bytes
}

TEST_CASE("an unclosed string points at its opening quote") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ВЫВОД(\"привет).\n");
  const std::vector<const PrologError*> errors = withSeverity(diagnostics, Severity::Error);
  REQUIRE_FALSE(errors.empty());
  const PrologError& error = *errors.front();
  REQUIRE(error.code == ErrorCode::InvalidStringLiteral);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 13);  // the opening `"`
}

TEST_CASE("two variables that differ only in alphabet are reported") {
  // `C` is Latin, the second name is a Cyrillic es: one shape, two variables.
  // The warning stands at the second spelling and names both alphabets.
  const std::vector<PrologError> diagnostics = diagnosticsOf("a(C, С).\n");
  const std::vector<const PrologError*> confusable =
      withCode(diagnostics, ErrorCode::ConfusableVariable);
  REQUIRE(confusable.size() == 1);
  REQUIRE(confusable.front()->severity == Severity::Warning);
  REQUIRE(confusable.front()->location.line == 1);
  REQUIRE(confusable.front()->location.column == 6);  // the second name, in bytes
  REQUIRE(confusable.front()->message ==
          "переменные «C» (латиница) и «С» (кириллица) выглядят одинаково, "
          "но это разные переменные");

  // A question is a statement too, and there the slip is likelier still.
  const std::vector<PrologError> question = diagnosticsOf("?a(C, С).\n");
  const std::vector<const PrologError*> asked =
      withCode(question, ErrorCode::ConfusableVariable);
  REQUIRE(asked.size() == 1);
  REQUIRE(asked.front()->location.line == 1);
  REQUIRE(asked.front()->location.column == 7);  // past the `?`, in bytes
}

TEST_CASE("a look-alike is silent without the pair in one clause") {
  // One Cyrillic letter on its own is a name like any other, `_C` and `_С`
  // are wildcards, and two clauses never share a variable: no pair, no warning.
  const std::vector<PrologError> lone = diagnosticsOf("r(С).\n");
  REQUIRE(withCode(lone, ErrorCode::ConfusableVariable).empty());

  const std::vector<PrologError> wildcards = diagnosticsOf("q(_C, _С).\n");
  REQUIRE(wildcards.empty());

  const std::vector<PrologError> clauses =
      diagnosticsOf("a(С, С).\nb(C, C).\n");
  REQUIRE(clauses.empty());
}

TEST_CASE("a reserved name with an arity it does not have is an error") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?УМНОЖЕНИЕ(2, 3).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::WrongArity);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 2);  // the goal, not the `?`
  REQUIRE(error.message == "УМНОЖЕНИЕ не имеет арности 2 (есть 3 и 4)");
}

TEST_CASE("a singleton in a fact is told to use quotes") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("мама(Лена, Таня).\n");
  REQUIRE(diagnostics.size() == 2);
  const PrologError& first = diagnostics[0];
  REQUIRE(first.code == ErrorCode::SingletonVariable);
  REQUIRE(first.severity == Severity::Warning);
  REQUIRE(first.location.line == 1);
  REQUIRE(first.message ==
          "Лена — переменная, а не константа; если имелась в виду константа, "
          "запишите её в одинарных кавычках: 'Лена'");
  REQUIRE(diagnostics[1].message.find("'Таня'") != std::string::npos);
}

TEST_CASE("a singleton in a rule offers the wildcard as well") {
  // In a rule the name can be a forgotten wildcard, so both readings are named.
  const std::vector<PrologError> head = diagnosticsOf("дв(Н, М) :- БОЛЬШЕ(Н, 1).\n");
  REQUIRE(head.size() == 1);
  REQUIRE(head.front().message ==
          "М — переменная, а не константа; если это пропуск, назовите её _М, "
          "а если константа — запишите её в одинарных кавычках: 'М'");

  // A name used once in the body gets the plain advice.
  const std::vector<PrologError> body = diagnosticsOf("дв(Н) :- МЕНЬШЕ(Н, К).\n");
  REQUIRE(body.size() == 1);
  REQUIRE(body.front().message ==
          "переменная К встречается один раз; если это намеренно, назовите её _К");
}

TEST_CASE("deliberately unused names are not reported") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("p(_X, _).\nq(A) :- r(A).\nr(1).\n");
  REQUIRE(diagnostics.empty());
}

TEST_CASE("an undefined predicate is a warning with a suggestion") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("член(а, [а]).\n?члеен(а, [а]).\n");
  const std::vector<const PrologError*> warnings =
      withSeverity(diagnostics, Severity::Warning);
  REQUIRE(warnings.size() == 1);
  const PrologError& warning = *warnings.front();
  REQUIRE(warning.code == ErrorCode::UnknownPredicate);
  REQUIRE(warning.location.line == 2);
  REQUIRE(warning.location.column == 2);
  // The suggestion is measured in code points, so one Cyrillic letter is one
  // edit — `члеен` is `член` with a letter too many.
  REQUIRE(warning.message == "не найдено: члеен/2; возможно, член/2");
}

TEST_CASE("an ISO `is` is told what the dialect writes instead") {
  // `is/2` is not a predicate of the dialect: it is a *sign* (task_92), so the
  // call stays an ordinary unknown name — a program may define its own `is/2` —
  // but the warning names the spelling that does the same thing, because a
  // reader of ISO Prolog reaches for `is` first.
  const std::vector<PrologError> diagnostics = diagnosticsOf("?is(X, #2+3#).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& warning = diagnostics.front();
  REQUIRE(warning.code == ErrorCode::UnknownPredicate);
  REQUIRE(warning.severity == Severity::Warning);
  REQUIRE(warning.location.line == 1);
  REQUIRE(warning.location.column == 2);
  REQUIRE(warning.message ==
          "не найдено: is/2; «is» — знак, а не предикат: пишут «X is 2 + 3»");
}

TEST_CASE("an ISO exception is told there are none") {
  // Stage 4 of task_82: `catch`/`throw` are refused, and the refusal is carried
  // by the same table as `is/2` — two warnings that name the reason instead of
  // a bare «не найдено».
  const std::vector<PrologError> caught =
      diagnosticsOf("?catch(Истина, _Ошибка, _Запас).\n");
  REQUIRE(caught.size() == 1);
  REQUIRE(caught.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(caught.front().message ==
          "не найдено: catch/3; исключений в Пролог-Д нет: ошибка останавливает "
          "программу");

  const std::vector<PrologError> thrown = diagnosticsOf("?throw(беда).\n");
  REQUIRE(thrown.size() == 1);
  REQUIRE(thrown.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(thrown.front().message ==
          "не найдено: throw/1; исключений в Пролог-Д нет: «не получилось» — это "
          "ЛОЖЬ, а объяснение печатает ВЫВОД");
}

TEST_CASE("bagof and setof are predicates of their own, not advice") {
  // Task_91: the two used to be unknown names with a hint pointing at
  // `НАЙТИВСЕ/3`; they are built-ins now, so a program that calls them — in
  // either spelling — gets no warning at all.
  REQUIRE(diagnosticsOf("?bagof(_Х, ЛОЖЬ, _С).\n").empty());
  REQUIRE(diagnosticsOf("?ВСЕРЕШ(_Х, ЛОЖЬ, _С).\n").empty());
  REQUIRE(diagnosticsOf("?setof(_Х, ЛОЖЬ, _С).\n").empty());
  REQUIRE(diagnosticsOf("?МНОРЕШ(_Х, ЛОЖЬ, _С).\n").empty());
}

TEST_CASE("a bare caret is told where a quantifier belongs") {
  // `^` is the quantifier of the goal of `ВСЕРЕШ`/`МНОРЕШ` and nothing else
  // (task_91): away from them there is no `^/2` predicate, and the warning says
  // where the sign does belong rather than «не найдено» alone.
  const std::vector<PrologError> caret = diagnosticsOf("р(1).\n?Х^р(Х).\n");
  REQUIRE(caret.size() == 1);
  REQUIRE(caret.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(caret.front().message ==
          "не найдено: ^/2; «^» — не предикат, а квантор: он стоит перед всей целью "
          "«ВСЕРЕШ/3» или «МНОРЕШ/3» — ВСЕРЕШ(Х, У^(р(Х), ц(У)), С)");
}

TEST_CASE("a module and a rational are told they do not exist") {
  // The other two refusals of stage 4 (task_82).  `:- module(…)` is refused by
  // the parser, where the export list would otherwise fail; a *call* to
  // `module/1` or `rational/1` is an ordinary unknown name with a hint.
  const std::vector<PrologError> module = diagnosticsOf("?module(м).\n");
  REQUIRE(module.size() == 1);
  REQUIRE(module.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(module.front().message ==
          "не найдено: module/1; модулей в Пролог-Д нет: файл подключают "
          "директивой «ИМПОРТ(\"файл.pld\")»");

  const std::vector<PrologError> rational = diagnosticsOf("?rational(1).\n");
  REQUIRE(rational.size() == 1);
  REQUIRE(rational.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(rational.front().message ==
          "не найдено: rational/1; рациональных чисел в Пролог-Д нет: числа — "
          "целые и вещественные");
}

TEST_CASE("the retired findall spelling suggests the current one") {
  // The name with ё left the language (task_44): it is one letter away from
  // `НАЙТИВСЕ`, so the ordinary unknown-name path already says exactly what to
  // fix — the checker needs no special case for it.
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("?НАЙТИВСЁ(_, ЛОЖЬ, _).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& warning = diagnostics.front();
  REQUIRE(warning.code == ErrorCode::UnknownPredicate);
  REQUIRE(warning.severity == Severity::Warning);
  REQUIRE(warning.location.line == 1);
  REQUIRE(warning.location.column == 2);
  REQUIRE(warning.message == "не найдено: НАЙТИВСЁ/3; возможно, НАЙТИВСЕ/3");
}

TEST_CASE("a retired name says what to write instead") {
  // `or` was the English spelling of `ИЛИ` and left the language with it
  // (task_44); the English vocabulary for the behaviour is `first`, the alias of
  // `ПЕРВОЕ`.  Unlike a name that was never in the language, this one is an
  // error with a message: the reader has nowhere else to learn what `or` meant.
  const std::vector<PrologError> diagnostics = diagnosticsOf("?or(ЛОЖЬ, ЛОЖЬ).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.code == ErrorCode::UnknownPredicate);
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.isParseError);
  REQUIRE(error.location.line == 1);
  REQUIRE(error.location.column == 2);  // the goal, not the `?`
  REQUIRE(error.message ==
          "«or» переименовано: теперь это «first(Ц1, Ц2)», а дизъюнкция — «A ; B»");

  // The English spelling `КОПИЯ` used to answer to went in task_84, and its
  // message has to name both what it was and what the ISO predicate of the same
  // family is — the two differ in the count of arguments and in where positions
  // start, so «переименовано» would be the wrong word.
  const std::vector<PrologError> gone =
      diagnosticsOf("?substring(\"аб\", 1, 1, _).\n");
  REQUIRE(gone.size() == 1);
  REQUIRE(gone.front().code == ErrorCode::UnknownPredicate);
  REQUIRE(gone.front().severity == Severity::Error);
  REQUIRE(gone.front().isParseError);
  REQUIRE(gone.front().message.find("«substring» снято") == 0);
  REQUIRE(gone.front().message.find("sub_string") != std::string::npos);

  // The names marker is retired with the modes it declared: both spellings say
  // there is nothing to declare any more, because that is the whole of what the
  // word meant.
  for (const char* spelling : {"ИМЕНА", "variables"}) {
    INFO("marker: " << spelling);
    const std::vector<PrologError> marker =
        diagnosticsOf(std::string("?-") + spelling + "(0).\n");
    REQUIRE(marker.size() == 1);
    REQUIRE(marker.front().code == ErrorCode::UnknownPredicate);
    REQUIRE(marker.front().severity == Severity::Error);
    REQUIRE(marker.front().message.find("режимов имён больше нет") == 0);
  }
}

TEST_CASE("the original dialect's or-word loads, and its two arguments are goals") {
  // task_83: the Russian word is callable again, so nothing is said about the
  // call itself...
  REQUIRE(diagnosticsOf("?ИЛИ(ЛОЖЬ, ЛОЖЬ).\n").empty());
  // ...and both arguments are reached as goals, the way `ПЕРВОЕ`'s are: a name
  // inside one of them is checked, not taken for an opaque term.
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ИЛИ(члены(Х), ЛОЖЬ).\n");
  REQUIRE(diagnostics.size() == 1);
  REQUIRE(diagnostics.front().message.find("не найдено: члены/1") == 0);
}

TEST_CASE("an `->` with nothing after it says so") {
  // task_85: the sign is an operator now, and a goal that was deleted leaves the
  // arrow behind.  The message names the arrow instead of blaming the whole goal
  // («Цель должна быть предикатом»), which points at the wrong end of the line.
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ЛОЖЬ -> .\n");
  REQUIRE(diagnostics.size() == 1);
  REQUIRE(diagnostics.front().code == ErrorCode::InvalidSentence);
  REQUIRE(diagnostics.front().isParseError);
  REQUIRE(diagnostics.front().message == "после «->» нужна цель");
}

TEST_CASE("an arity a user predicate does not have lists the ones it has") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("дв(1, 2).\n?дв(1).\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& warning = diagnostics.front();
  REQUIRE(warning.severity == Severity::Warning);
  REQUIRE(warning.code == ErrorCode::WrongArity);
  REQUIRE(warning.location.line == 2);
  REQUIRE(warning.message == "дв определён с арностью 2, а вызван с 1");
}

TEST_CASE("the argument of call is checked when it is a literal goal") {
  const std::vector<PrologError> diagnostics = diagnosticsOf("?ВЫП(члены(Х)).\n");
  REQUIRE(diagnostics.size() == 1);
  REQUIRE(diagnostics.front().message.find("не найдено: члены/1") == 0);
}

TEST_CASE("a program that defines what it calls is silent") {
  // Forward and mutual references are normal Prolog: the warning must wait for
  // the whole unit, or half of every course file would be flagged.
  const std::vector<PrologError> diagnostics = diagnosticsOf(
      "чёт(0).\n"
      "чёт(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), нечёт(Н1).\n"
      "нечёт(Н) :- БОЛЬШЕ(Н, 0), СЛОЖЕНИЕ(Н1, 1, Н), чёт(Н1).\n"
      "?ТИХО, чёт(2).\n");
  REQUIRE(diagnostics.empty());
}

TEST_CASE("both branches of a disjunction are checked") {
  const std::vector<PrologError> diagnostics =
      diagnosticsOf("член(а, [а]).\n?(член(а, [а]) ; члеен(а, [а])).\n");
  const std::vector<const PrologError*> warnings =
      withSeverity(diagnostics, Severity::Warning);
  REQUIRE(warnings.size() == 1);
  REQUIRE(warnings.front()->message == "не найдено: члеен/2; возможно, член/2");
  REQUIRE(warnings.front()->location.line == 2);
}

TEST_CASE("a `;` where a sentence ends says what changed") {
  // The terminator of the original dialect, retired by task_41: the position is
  // the `;` itself, and the message names the new meaning.
  const std::vector<PrologError> diagnostics = diagnosticsOf("прим(1);\n");
  REQUIRE(diagnostics.size() == 1);
  const PrologError& error = diagnostics.front();
  REQUIRE(error.severity == Severity::Error);
  REQUIRE(error.code == ErrorCode::InvalidSentence);
  REQUIRE(error.location.line == 1);
  // Byte columns: `прим` is four letters of two bytes each, so the `;` sits in
  // the twelfth column.
  REQUIRE(error.location.column == 12);
  REQUIRE(error.message == "«;» — дизъюнкция; предложение должно заканчиваться точкой");
}
