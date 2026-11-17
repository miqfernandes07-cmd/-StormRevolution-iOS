# Target locations for the iPhone framework packager, evaluated after SDK configuration.
function(storm_rexglue_ios_artifacts)
  set(entries "")
  foreach(name rexbase rexppc rexfilesystem rexkernel rexxam rexxbdm rexui rexapu
               rexhid rexgpu rexapp rexui-sdl3 rexapu-sdl3 rexhid-sdl3 rexgpu-xenos-vulkan)
    string(APPEND entries "{\"name\":\"${name}\",\"path\":\"$<TARGET_FILE:${name}>\"},")
  endforeach()
  string(APPEND entries "{\"name\":\"SDL3\",\"path\":\"$<TARGET_FILE:SDL3::SDL3>\"}")
  file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/storm-ios-artifacts-$<CONFIG>.json"
    CONTENT "{\"frameworks\":[${entries}],\"xenos_archive\":\"$<TARGET_FILE:rexxenos>\"}\n")
endfunction()
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL storm_rexglue_ios_artifacts)
