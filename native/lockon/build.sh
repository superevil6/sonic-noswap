#!/usr/bin/env bash
# Build Mania Lock-On's DLL with MinGW (mingw-w64-gcc) into mods/ManiaLockOn, with NoSwap's MinHook checkout
# (native/third_party/minhook, native/fetch_deps.sh). Its menu patches come from tools/build_lockon_menu.py.
set -euo pipefail
cd "$(dirname "$0")"
NATIVE=..
[ -d $NATIVE/third_party/minhook ] || (cd $NATIVE && ./fetch_deps.sh)
MH=$NATIVE/third_party/minhook/src
OBJ=$NATIVE/build/lockon
mkdir -p "$OBJ" ../../mods/ManiaLockOn
for f in buffer hook trampoline hde/hde64; do
    x86_64-w64-mingw32-gcc -O2 -c "$MH/$f.c" -I$NATIVE/third_party/minhook/include -o "$OBJ/$(basename $f).o"
done
# (--no-insert-timestamp: the same sources build the same DLL, byte for byte)
x86_64-w64-mingw32-g++ -std=c++17 -O2 -Wall -Wno-unused-function -shared -static -s -Wl,--no-insert-timestamp \
    -I$NATIVE/third_party/minhook/include \
    src/ManiaLockOn.cpp "$OBJ/buffer.o" "$OBJ/hook.o" "$OBJ/trampoline.o" "$OBJ/hde64.o" \
    -o ../../mods/ManiaLockOn/ManiaLockOn.dll
echo "built mods/ManiaLockOn/ManiaLockOn.dll"
