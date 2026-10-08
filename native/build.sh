#!/usr/bin/env bash
# Build the S3&K DLL with MinGW (mingw-w64-gcc) into the NoSwap mod folder.
set -euo pipefail
cd "$(dirname "$0")"
[ -d third_party/minhook ] || ./fetch_deps.sh
MH=third_party/minhook/src
python3 ../tools/gen_s3k_header.py
mkdir -p build ../mods/NoSwap
for f in buffer hook trampoline hde/hde64; do
    x86_64-w64-mingw32-gcc -O2 -c "$MH/$f.c" -Ithird_party/minhook/include -o "build/$(basename $f).o"
done
# (--no-insert-timestamp: the PE header's link time left at 0, so the same sources build the same DLL, byte for byte)
x86_64-w64-mingw32-g++ -std=c++17 -O2 -shared -static -s -Wl,--no-insert-timestamp \
    -Ithird_party/minhook/include -Ibuild \
    src/NoSwapS3K.cpp build/buffer.o build/hook.o build/trampoline.o build/hde64.o \
    -lpsapi \
    -o ../mods/NoSwap/NoSwapS3K.dll
echo "built mods/NoSwap/NoSwapS3K.dll"
