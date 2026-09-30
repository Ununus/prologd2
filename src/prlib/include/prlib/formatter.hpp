#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/diagnostics.hpp"

namespace prologd {

/// How the formatter lays a program out.
enum class FormatMode {
  None,  ///< «не форматировать»: `formatSource` returns the text as it is.
  Line,  ///< «в одну строку»: the goals of a body share one line, whatever the width
  Soft,  ///< the lines are built again: goals are packed up to the width
  Hard,  ///< one goal of a body per line
};

/// The unit a continuation line is indented with.
enum class IndentUnit {
  Tab,     ///< one tab per step, the editor decides how wide it looks
  Spaces,  ///< four spaces per step
};

/// Everything the formatter is allowed to do, as the settings spell it.
struct FormatOptions {
  FormatMode mode = FormatMode::Soft;
  /// What the diagnostics of a source that does not parse name as their file.
  /// A front-end passes the buffer's own name; the CLI the path it read.
  std::string source_name = "<format>";
  /// The soft width: what has to fit on one line, counted in code points, with
  /// one column per character.  A tab counts as one column of its own.
  std::size_t width = 80;
  /// How many indent units a continuation line starts with.
  std::size_t indent_steps = 1;
  IndentUnit indent_unit = IndentUnit::Tab;
  /// «Форматировать только выделенное»: the text is a fragment, and a fragment
  /// may end in the middle of a body — it is then formatted up to its last
  /// complete goal and the rest is copied as it stands.
  bool selection_only = false;
};

/// What `formatSource` made of the input.
struct FormatResult {
  /// The formatted text; the input unchanged when the source does not parse.
  std::string text;
  /// True when `text` differs from the input.
  bool changed = false;
  /// The parse diagnostics of a source that does not parse; a successful
  /// format may still carry warnings.
  std::vector<PrologError> diagnostics;

  [[nodiscard]] bool ok() const {
    for (const PrologError& diagnostic : diagnostics) {
      if (diagnostic.severity == Severity::Error) {
        return false;
      }
    }
    return true;
  }
};

/// Lays out a program without touching a single byte of it except whitespace.
///
/// The text is lexed and parsed with the same grammar the interpreter runs, and
/// the output is rebuilt from the token stream: every token is copied verbatim
/// — quoting, `#expr#` bodies and Cyrillic names cannot be damaged — and only
/// the whitespace *between* the goals of a body (and around `:-`, at line ends
/// and between statements) is rewritten.  A source that does not parse comes
/// back byte for byte with its diagnostics, so a front-end can report «не
/// удалось разобрать» instead of mangling the buffer.
FormatResult formatSource(std::string_view text, const FormatOptions& options = {});

}  // namespace prologd
