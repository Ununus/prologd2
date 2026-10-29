# `section -> page` of the manual, for the `F1` card of the window.
#
# Typst knows the page of a heading only inside `context`, so `help.typ` emits the
# map as a hidden `<help-sections>` element and this writes out what the query
# prints.  `typst eval` is the current spelling of the same query; `typst query` is
# the older one and is tried when `eval` is not known to the binary.
#
# -DTYPST=<binary> -DSOURCE=<doc/help.typ> -DOUTPUT=<doc/help_sections.json>
#
# A failure is a warning, not an error: a checkout without the map shows the card
# without a page link, which is what it did before the map existed.

foreach(variable TYPST SOURCE OUTPUT)
  if(NOT DEFINED ${variable})
    message(FATAL_ERROR "write_sections.cmake: -D${variable} is required")
  endif()
endforeach()

execute_process(
  COMMAND "${TYPST}" eval "query(<help-sections>).first().value"
          --in "${SOURCE}" --format json
  OUTPUT_VARIABLE json
  RESULT_VARIABLE status
  ERROR_VARIABLE error)
if(NOT status EQUAL 0)
  execute_process(
    COMMAND "${TYPST}" query "${SOURCE}" "<help-sections>" --one --field value
            --format json
    OUTPUT_VARIABLE json
    RESULT_VARIABLE status
    ERROR_VARIABLE error)
endif()

if(status EQUAL 0 AND json MATCHES "^\\[")
  file(WRITE "${OUTPUT}" "${json}")
  message(STATUS "typst: ${OUTPUT}")
else()
  message(WARNING "typst: no section map for the F1 card (${error})")
endif()
