#!/usr/bin/env bash
# Fetch third-party code for the S3&K DLL into third_party/ (vendored in this repository with their licences: this
# re-fetches them if deleted).
#  - HiteModLoader headers (MIT, hedge-dev): the mod loader's API
#  - MinHook (BSD-2, TsudaKageyu): function hooking that builds with MinGW
#  - thesupersonic16's DllMods (MIT): reference for S3&K structs and signatures (Ultrafix3kFixes)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p third_party
HML=https://raw.githubusercontent.com/hedge-dev/HiteModLoader/HEAD/HiteModLoader
mkdir -p third_party/HiteModLoader
for f in include/HiteModLoader.h include/Helpers.h include/CommonLoader.h SigScan.h ../LICENSE.md; do
    curl -fsSL "$HML/$f" -o "third_party/HiteModLoader/$(basename "$f")"
done
[ -d third_party/minhook ] || git clone --depth 1 https://github.com/TsudaKageyu/minhook.git third_party/minhook
DM=https://raw.githubusercontent.com/thesupersonic16/DllMods/main
mkdir -p third_party/reference
for f in Source/Ultrafix3kFixes/Ultrafix3kFixes/Game.h Source/Ultrafix3kFixes/Ultrafix3kFixes/SigScan.cpp \
         Source/Ultrafix3kFixes/Ultrafix3kFixes/Mod.cpp Source/OriginsPlayerPatcher/OriginsPlayerPatcher/SigScan.cpp LICENSE; do
    curl -fsSL "$DM/$f" -o "third_party/reference/$(echo "$f" | tr / _ | sed 's/^Source_//')"
done
echo "fetched into $(pwd)/third_party"
