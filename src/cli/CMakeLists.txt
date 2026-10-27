# The console front-end: the `prologd` executable, the same name as the CMake
# project, the `PROLOGD_*` options and the `prologd` C++ namespace.
add_executable(prologd main.cpp protocol.cpp)

target_link_libraries(prologd PRIVATE
  prlib
  CLI11::CLI11
  prologd_json
  prologd_warnings
  prologd_utf8)

if(MSVC)
  target_compile_options(prologd PRIVATE /utf-8)
endif()

install(TARGETS prologd RUNTIME DESTINATION bin)
