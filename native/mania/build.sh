#!/usr/bin/env bash
# Build the Sonic Mania decomp code mod into mods/NoSwapMania/: NoSwapMania.so (Linux, gcc) and NoSwapMania.dll
# (Windows, MinGW: the Windows decomp that Origins' SONIC MANIA button starts). mod.ini's LogicFile=NoSwapMania has no
# extension: the decomp adds its platform's (.so / .dll).
# Its sprites come from tools/build_mania_art.py (run it first when an extra's art changes).
# GAMEAPI_DIR: an RSDKv5-GameAPI checkout (default ~/Code/mania/RSDKv5-GameAPI).
# NOSWAP_MANIA_WINDOWS=0 skips the Windows build (it's skipped anyway without x86_64-w64-mingw32-gcc).
set -euo pipefail
cd "$(dirname "$0")"
GAMEAPI_DIR="${GAMEAPI_DIR:-$HOME/Code/mania/RSDKv5-GameAPI}"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGAMEAPI_DIR="$GAMEAPI_DIR" >/dev/null
cmake --build build -j
mkdir -p ../../mods/NoSwapMania
cp build/NoSwapMania.so ../../mods/NoSwapMania/NoSwapMania.so
echo "built mods/NoSwapMania/NoSwapMania.so"

if [ "${NOSWAP_MANIA_WINDOWS:-1}" != 0 ] && command -v x86_64-w64-mingw32-gcc >/dev/null; then
    # (static libgcc: the DLL needs nothing but Windows' own DLLs)
    cmake -S . -B build/win -DCMAKE_BUILD_TYPE=Release -DGAMEAPI_DIR="$GAMEAPI_DIR" -DCMAKE_SYSTEM_NAME=Windows \
        -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc -DCMAKE_RC_COMPILER=x86_64-w64-mingw32-windres \
        -DCMAKE_SHARED_LINKER_FLAGS="-static-libgcc -s" >/dev/null
    cmake --build build/win -j
    cp build/win/NoSwapMania.dll ../../mods/NoSwapMania/NoSwapMania.dll
    echo "built mods/NoSwapMania/NoSwapMania.dll"
else
    echo "skipped the Windows NoSwapMania.dll (no x86_64-w64-mingw32-gcc, or NOSWAP_MANIA_WINDOWS=0)"
fi
