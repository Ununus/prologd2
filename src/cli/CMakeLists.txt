add_executable(prologd main.cpp)

target_link_libraries(prologd PRIVATE prlib CLI11::CLI11 prologd_warnings)

if(MSVC)
  target_compile_options(prologd PRIVATE /utf-8)
endif()

install(TARGETS prologd RUNTIME DESTINATION bin)
