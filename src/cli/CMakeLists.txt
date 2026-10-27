# The branch became the ISO-compatible engine «Пролог-У», so the *target* is
# `prologu` and the file it produces is `prologu.exe`.  Only the executable is
# renamed: the CMake project (`project(prologd …)`), the options `PROLOGD_*`, the
# support targets below and the `prologd` C++ namespace are the name of the
# repository, not of a file (task_75).
add_executable(prologu main.cpp protocol.cpp)

target_link_libraries(prologu PRIVATE
  prlib
  CLI11::CLI11
  prologd_json
  prologd_warnings
  prologd_utf8)

if(MSVC)
  target_compile_options(prologu PRIVATE /utf-8)
endif()

install(TARGETS prologu RUNTIME DESTINATION bin)
