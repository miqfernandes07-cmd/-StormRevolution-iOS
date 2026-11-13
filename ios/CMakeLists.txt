enable_language(OBJCXX)
if(NOT CMAKE_GENERATOR STREQUAL "Xcode")
  message(FATAL_ERROR "The iOS application currently requires the Xcode generator")
endif()
if(CMAKE_OSX_SYSROOT MATCHES "[Ss]imulator")
  set(STORM_METAL_SDK iphonesimulator)
else()
  set(STORM_METAL_SDK iphoneos)
endif()
set(STORM_METAL_AIR "${CMAKE_CURRENT_BINARY_DIR}/Diagnostic.air")
set(STORM_METAL_LIBRARY "${CMAKE_CURRENT_BINARY_DIR}/default.metallib")
add_custom_command(OUTPUT "${STORM_METAL_LIBRARY}"
  COMMAND xcrun --sdk ${STORM_METAL_SDK} metal -c
    "${CMAKE_CURRENT_SOURCE_DIR}/Metal/Diagnostic.metal" -o "${STORM_METAL_AIR}"
  COMMAND xcrun --sdk ${STORM_METAL_SDK} metallib
    "${STORM_METAL_AIR}" -o "${STORM_METAL_LIBRARY}"
  DEPENDS Metal/Diagnostic.metal VERBATIM)
set_source_files_properties("${STORM_METAL_LIBRARY}" PROPERTIES
  GENERATED TRUE MACOSX_PACKAGE_LOCATION Resources)
add_executable(StormRevolution MACOSX_BUNDLE
  App/main.mm App/StormViewController.mm Import/StormGameImporter.mm Import/StormImportSmoke.mm
  Assets.xcassets
  Metal/StormMetalView.mm Controls/StormControls.mm
  "${STORM_METAL_LIBRARY}")
target_compile_features(StormRevolution PRIVATE cxx_std_17)
target_compile_options(StormRevolution PRIVATE -fobjc-arc)
target_include_directories(StormRevolution PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(StormRevolution PRIVATE storm_runtime
  "-framework Foundation" "-framework UIKit" "-framework UniformTypeIdentifiers"
  "-framework GameController" "-framework Metal" "-framework MetalKit"
  "-framework QuartzCore" "-framework CoreGraphics")
set_target_properties(StormRevolution PROPERTIES
  OBJCXX_STANDARD 17
  OBJCXX_STANDARD_REQUIRED YES
  OBJCXX_EXTENSIONS NO
  XCODE_GENERATE_SCHEME TRUE
  MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/App/Info.plist"
  MACOSX_BUNDLE_GUI_IDENTIFIER "org.stormrevolution.port"
  XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "org.stormrevolution.port"
  XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2"
  XCODE_ATTRIBUTE_CLANG_ENABLE_OBJC_ARC YES
  XCODE_ATTRIBUTE_ENABLE_BITCODE NO
  XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO
  XCODE_ATTRIBUTE_CODE_SIGNING_REQUIRED NO
  XCODE_ATTRIBUTE_GENERATE_INFOPLIST_FILE NO)
set_source_files_properties(Assets.xcassets PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
set_target_properties(StormRevolution PROPERTIES
  XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_APPICON_NAME AppIcon)
