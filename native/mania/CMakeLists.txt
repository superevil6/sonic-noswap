# NoSwapMania: the Sonic Mania (RSDKv5 decompilation) code mod, a Linux shared library for the decomp's mod loader.
# Built against RSDKv5-GameAPI's C API (https://github.com/RSDKModding/RSDKv5-GameAPI), not vendored here: point
# GAMEAPI_DIR at a checkout (default ~/Code/mania/RSDKv5-GameAPI). Use build.sh.
cmake_minimum_required(VERSION 3.10)
project(NoSwapMania C)

set(GAMEAPI_DIR "$ENV{HOME}/Code/mania/RSDKv5-GameAPI" CACHE PATH "RSDKv5-GameAPI checkout (its C/GameAPI is used)")
if(NOT EXISTS "${GAMEAPI_DIR}/C/GameAPI/Game.c")
    message(FATAL_ERROR "RSDKv5-GameAPI not found at ${GAMEAPI_DIR} (set -DGAMEAPI_DIR=...)")
endif()

add_library(NoSwapMania SHARED
    src/NoSwapMania.c
    ${GAMEAPI_DIR}/C/GameAPI/Game.c
)
target_include_directories(NoSwapMania PRIVATE src ${GAMEAPI_DIR}/C ${GAMEAPI_DIR}/C/GameAPI)
# The decomp as built in ~/Code/mania (its CMakeCache): Plus (GAME_VERSION 6 = 1.06), v5U engine (RETRO_REVISION 3),
# mod loader v2. The engine refuses a logic file whose modInfo.engineVer differs.
target_compile_definitions(NoSwapMania PRIVATE
    RETRO_REVISION=3
    RETRO_USE_MOD_LOADER=1
    RETRO_MOD_LOADER_VER=2
    GAME_VERSION=6
    GAME_INCLUDE_EDITOR=1
)
set_target_properties(NoSwapMania PROPERTIES PREFIX "" OUTPUT_NAME NoSwapMania C_STANDARD 11)
target_compile_options(NoSwapMania PRIVATE -Wall -Wno-unused-function -Wno-missing-braces)
