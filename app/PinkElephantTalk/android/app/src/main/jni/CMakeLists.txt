cmake_minimum_required(VERSION 3.13)

project(appmodules)

# This file includes all the necessary to let you build your application with the New Architecture.
include(${REACT_ANDROID_DIR}/cmake-utils/ReactNative-application.cmake)

# Bundled espeak-ng Cantonese TTS. Only builds on arm64-v8a (matching the
# app's abiFilters). libappmodules.so (built above via ReactNative-application.cmake)
# registers core TurboModules such as PlatformConstants.
if (ANDROID_ABI STREQUAL "arm64-v8a")
    add_library(cantonese_tts SHARED cantonese_tts.c)

    target_include_directories(cantonese_tts PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/espeak/include)
    target_link_libraries(cantonese_tts
        ${CMAKE_CURRENT_SOURCE_DIR}/libespeak-ng.a
        ${CMAKE_CURRENT_SOURCE_DIR}/libspeechPlayer.a
        ${CMAKE_CURRENT_SOURCE_DIR}/libucd.a
        log m c++)

    set_target_properties(cantonese_tts PROPERTIES C_STANDARD 11)
else()
    message(WARNING "cantonese_tts only supports arm64-v8a (current: ${ANDROID_ABI}); skipping cantonese_tts build")
endif()
