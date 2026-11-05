cmake_minimum_required(VERSION 3.20)
project(StormRevolutionIOS VERSION 0.1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
option(STORM_SANITIZERS "Enable undefined behavior sanitizer for host tests" OFF)
add_library(storm_runtime STATIC
  runtime/storm_runtime.cpp
  runtime/cpu/context.cpp
  runtime/audio/pcm_ring.cpp
  runtime/memory/guest_memory.cpp
  runtime/kernel/imports.cpp
  runtime/filesystem/content_root.cpp)
target_include_directories(storm_runtime PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/runtime" "${CMAKE_CURRENT_SOURCE_DIR}")
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(storm_runtime PRIVATE -Wall -Wextra -Wpedantic -Werror)
  if(STORM_SANITIZERS)
    target_compile_options(storm_runtime PUBLIC -fsanitize=undefined -fno-sanitize-recover=all)
    target_link_options(storm_runtime PUBLIC -fsanitize=undefined)
  endif()
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  add_subdirectory(ios)
else()
  include(CTest)
  if(BUILD_TESTING)
    find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
    find_package(Threads REQUIRED)
    add_executable(storm_runtime_tests tests/test_runtime.cpp)
    target_link_libraries(storm_runtime_tests PRIVATE storm_runtime Threads::Threads)
    add_test(NAME runtime COMMAND storm_runtime_tests)
    add_executable(storm_audio_tests tests/test_audio.cpp)
    target_link_libraries(storm_audio_tests PRIVATE storm_runtime Threads::Threads)
    add_test(NAME audio_pcm COMMAND storm_audio_tests)
    add_test(NAME python_tools COMMAND "${Python3_EXECUTABLE}" -m unittest discover -s tests -p "test_*.py" -v)
    set_tests_properties(python_tools PROPERTIES WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
      ENVIRONMENT "CXX=${CMAKE_CXX_COMPILER}")
  endif()
endif()
