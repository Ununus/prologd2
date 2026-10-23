#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

#include "prlib/diagnostics.hpp"
#include "prlib/lexer.hpp"

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

/// The language the built-in names are printed in (task_101).  It is a
/// *conversion*, not a mode of reading: the engine reads both spellings of every
/// built-in in every naming mode, so a file keeps working whichever language it is
/// printed in.
enum class Dialect : std::uint8_t {
  Russian = 0,  ///< `ВЫВОД`, `НАЙТИВСЕ`, `РАВНО`, `БОЛЬШЕ`, `НЕ`, `ИМПОРТ`…
  English = 1,  ///< `write`, `findall`, `=`, `is`, `>`, `\+`, `import`…
};

/// Everything the formatter is allowed to do, as the settings spell it.
struct FormatOptions {
  FormatMode mode = FormatMode::Soft;
  /// How a name is read (task_67).  A file's own `:- ИМЕНА(N).` first line wins
  /// over this; this is what a file without a marker gets, the way `--vars`
  /// gives the CLI a mode for a file that says nothing.
  VariableMode variables = VariableMode::Iso;
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
  /// The mode to *print* names in (task_99); empty prints them as the file reads
  /// them.  `Iso` writes an old-dialect program in the ISO spelling — numbered
  /// variables, `"…"` for the bare capitalised constants — and `Old` writes an ISO
  /// one back (`Сумма'`, while `X` and `X_` stay as they are, and a one-letter atom
  /// takes the quotes the old dialect needs: `а` → `'а'`).  The marker line of
  /// the answer always says which mode it is in, whether the source had one or not.
  /// A fragment (`selection_only`) keeps its names: the numbering needs the whole
  /// program.
  std::optional<VariableMode> names_out;
  /// The language to *print* the built-in names and the operator spellings in
  /// (task_101); empty prints them as they are written.  `English` spells out
  /// what ISO spells: `РАВНО(A, B)` → `A = B`, `РАВНО(A, #B#)` → `A is B`,
  /// `БОЛЬШЕ(A, B)` → `A > B`, `МЕНЬШЕ(A, B)` → `A < B`, `НЕ(A)` → `\+ A`, and
  /// every built-in that has an English name gets it.  `Russian` is the way back.
  /// It is a rewrite of words, not of layout, and it composes with the other two:
  /// the conversion runs first, then the names, then the layout.
  std::optional<Dialect> dialect_out;
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
