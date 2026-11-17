set(STORM_REX_IOS_SDK "" CACHE PATH "Extracted, verified iPhone runtime package")
set(STORM_NATIVE_GENERATED "" CACHE PATH "Private ReXGlue generated/default directory")
if(NOT CMAKE_OSX_ARCHITECTURES STREQUAL "arm64" OR CMAKE_OSX_SYSROOT MATCHES "[Ss]imulator")
  message(FATAL_ERROR "The native runtime package requires an ARM64 iPhone device target")
endif()
foreach(required "${STORM_REX_IOS_SDK}/manifest.json"
                 "${STORM_REX_IOS_SDK}/include/rex/version.h"
                 "${STORM_NATIVE_GENERATED}/StormProbe_init.h")
  if(NOT EXISTS "${required}")
    message(FATAL_ERROR "Missing native input: ${required}")
  endif()
endforeach()
file(READ "${STORM_REX_IOS_SDK}/manifest.json" sdk_manifest)
string(JSON sdk_commit GET "${sdk_manifest}" sdk_commit)
string(JSON physical_offset GET "${sdk_manifest}" physical_offset_in_code)
if(NOT sdk_commit STREQUAL "a3e1d82678ca20d68d4837a8e9ee4652ff073745" OR NOT physical_offset EQUAL 1)
  message(FATAL_ERROR "Native code and SDK require the pinned iPhone physical mapping ABI")
endif()
file(GLOB generated_sources CONFIGURE_DEPENDS "${STORM_NATIVE_GENERATED}/*.cpp")
if(NOT generated_sources)
  message(FATAL_ERROR "No private recompiled title sources found")
endif()
add_library(storm_native_title OBJECT ${generated_sources})
add_executable(StormNative MACOSX_BUNDLE
  StormNativeMain.mm StormNativeSession.mm
  ../Import/StormGameImporter.mm ../Controls/StormControls.mm
  ../../runtime/filesystem/zip_archive.cpp
  $<TARGET_OBJECTS:storm_native_title>)
foreach(target storm_native_title StormNative)
  target_compile_features(${target} PRIVATE cxx_std_23)
  set_target_properties(${target} PROPERTIES CXX_STANDARD 23 OBJCXX_STANDARD 23
    CXX_STANDARD_REQUIRED YES OBJCXX_STANDARD_REQUIRED YES)
  target_include_directories(${target} PRIVATE "${STORM_REX_IOS_SDK}/include"
    "${STORM_NATIVE_GENERATED}" "${PROJECT_SOURCE_DIR}/runtime" "${PROJECT_SOURCE_DIR}/ios")
  target_compile_definitions(${target} PRIVATE REX_PHYSICAL_OFFSET_IN_CODE=1
    IMGUI_USER_CONFIG="rex/ui/imgui_config.h")
  target_compile_options(${target} PRIVATE -fexperimental-library -fno-char8_t
    -fno-strict-aliasing -ffp-model=strict)
endforeach()
target_precompile_headers(storm_native_title PRIVATE "${STORM_NATIVE_GENERATED}/StormProbe_pch.h")
target_compile_options(StormNative PRIVATE "$<$<COMPILE_LANGUAGE:OBJCXX>:-fobjc-arc>")
file(GLOB sdk_frameworks "${STORM_REX_IOS_SDK}/Frameworks/*.framework")
foreach(framework IN LISTS sdk_frameworks)
  get_filename_component(framework_name "${framework}" NAME_WE)
  add_library("storm_sdk_${framework_name}" SHARED IMPORTED)
  set_target_properties("storm_sdk_${framework_name}" PROPERTIES FRAMEWORK TRUE
    IMPORTED_LOCATION "${framework}/${framework_name}")
  target_link_libraries(StormNative PRIVATE "storm_sdk_${framework_name}")
endforeach()
target_link_libraries(StormNative PRIVATE ZLIB::ZLIB "${STORM_REX_IOS_SDK}/lib/librexxenos.a"
  "-framework Foundation" "-framework UIKit" "-framework UniformTypeIdentifiers"
  "-framework GameController" "-framework QuartzCore" "-framework CoreGraphics")
set_target_properties(StormNative PROPERTIES
  XCODE_GENERATE_SCHEME TRUE
  MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist"
  XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "org.stormrevolution.native"
  XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1"
  XCODE_ATTRIBUTE_CLANG_ENABLE_OBJC_ARC YES
  XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO XCODE_ATTRIBUTE_CODE_SIGNING_REQUIRED NO
  XCODE_ATTRIBUTE_ENABLE_BITCODE NO
  XCODE_ATTRIBUTE_LD_RUNPATH_SEARCH_PATHS "@executable_path/Frameworks")
add_custom_command(TARGET StormNative POST_BUILD
  COMMAND "${CMAKE_COMMAND}" -E copy_directory "${STORM_REX_IOS_SDK}/Frameworks"
    "$<TARGET_BUNDLE_DIR:StormNative>/Frameworks" VERBATIM)
