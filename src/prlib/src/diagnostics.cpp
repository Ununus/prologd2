#include "prlib/diagnostics.hpp"

#include <exception>
#include <utility>

namespace prologd {

std::string_view errorCodeText(ErrorCode code) {
  switch (code) {
    case ErrorCode::NoErrors:
      return "нет ошибок";

    // Lexical.
    case ErrorCode::InvalidCharacter:
      return "недопустимый символ";
    case ErrorCode::InvalidNumberLiteral:
      return "неверный формат числа";
    case ErrorCode::InvalidStringLiteral:
      return "незакрытая или неверно записанная строка";

    // Syntax.
    case ErrorCode::InvalidDefinition:
      return "неверная запись правила";
    case ErrorCode::InvalidSentence:
      return "ошибка при разборе предложения";
    case ErrorCode::InvalidGoal:
      return "неверная цель";
    case ErrorCode::InvalidFunction:
      return "ошибка при разборе функции";
    case ErrorCode::UnpairedBracket:
      return "непарные скобки";
    case ErrorCode::WrongList:
      return "неправильный список";
    case ErrorCode::MissingFunctor:
      return "отсутствует имя функции перед скобкой";
    case ErrorCode::MisplacedSign:
      return "знак операции вне арифметического выражения";
    case ErrorCode::InvalidArithmeticExpression:
      return "ошибка в арифметическом выражении";
    case ErrorCode::MisplacedQuestion:
      return "неверное использование \"?\"";
    case ErrorCode::MisplacedUnderscore:
      return "неверное использование \"_\"";
    case ErrorCode::MisplacedCut:
      return "неверное использование \"!\"";
    case ErrorCode::SingletonVariable:
      return "переменная встречается один раз";

    // Runtime.
    case ErrorCode::TypeMismatch:
      return "недопустимый тип аргументов";
    case ErrorCode::WrongArity:
      return "неверное число аргументов встроенного предиката";
    case ErrorCode::UnknownPredicate:
      return "неизвестный предикат";
    case ErrorCode::DivisionByZero:
      return "деление на ноль";
    case ErrorCode::ArithmeticType:
      return "операция неприменима к вещественному операнду";
    case ErrorCode::ArithmeticError:
      return "ошибка при вычислении";
    case ErrorCode::TypeConversion:
      return "ошибка преобразования типа";
    case ErrorCode::StackOverflow:
      return "переполнение стека";
    case ErrorCode::Interrupted:
      return "выполнение прервано";
    case ErrorCode::TooManySolutions:
      return "слишком много решений";
    case ErrorCode::NotEnoughMemory:
      return "недостаточно памяти";
    case ErrorCode::IoError:
      return "ошибка ввода-вывода";
    case ErrorCode::NotImplemented:
      return "предикат не реализован";
    case ErrorCode::ImportError:
      return "ошибка импорта модуля";
    case ErrorCode::RuntimeError:
      return "ошибка времени выполнения";
    case ErrorCode::Unknown:
      return "неизвестная ошибка";
  }
  return "неизвестная ошибка";
}

PrologRuntimeError::PrologRuntimeError(PrologError error)
    : error_(std::move(error)),
      what_(error_.message.empty() ? std::string(errorCodeText(error_.code))
                                   : error_.message) {}

std::string_view severityText(Severity severity) noexcept {
  switch (severity) {
    case Severity::Error:
      return "error";
    case Severity::Warning:
      return "warning";
    case Severity::Note:
      return "note";
  }
  return "error";
}

void DiagnosticSink::report(PrologError error) {
  if (error.code != ErrorCode::NoErrors || error.severity != Severity::Error) {
    if (error.message.empty()) {
      error.message = std::string(errorCodeText(error.code));
    }
  }
  if (error.severity == Severity::Warning) {
    ++warnings_;
  } else if (error.code != ErrorCode::NoErrors) {
    ++errors_;
  }
  diagnostics_.push_back(std::move(error));
}

void DiagnosticSink::clear() {
  diagnostics_.clear();
  errors_ = 0;
  warnings_ = 0;
}

std::string DiagnosticSink::format(const PrologError& error) {
  std::string result;
  if (!error.location.file.empty()) {
    result += error.location.file;
    result += ':';
    result += std::to_string(error.location.line);
    result += ':';
    result += std::to_string(error.location.column);
    result += ": ";
  }
  result += severityText(error.severity);
  result += ": ";
  result += error.message.empty() ? std::string(errorCodeText(error.code)) : error.message;
  return result;
}

}  // namespace prologd
