#!/usr/bin/env bash
# Build everything in the right order. The game builders write NoSwap's scripts with every extra's moves; the package
# step then rebuilds NoSwap's own player scripts without them and each character's package (docs/plan-b-modular-
# characters.md). Running a game builder alone leaves the everyone-included player script in NoSwap's folder.
# Origins' menu archives (raw/ui, raw/text) come from the game's own files (ORIGINS_GAME) and the packages' cards.
# Art is separate (tools/build_art.py [extra]): run it first when a character's art or configs change.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/refresh_characters.py  # (character.json characters edited since their configs: configs + art first)
python3 tools/build_sonic1.py >/dev/null
python3 tools/build_sonic2.py >/dev/null
python3 tools/build_soniccd.py >/dev/null
python3 tools/build_s3k_hud.py >/dev/null  # (each extra's S3&K HUD, signpost and results names: rebuilt every time, so a changed base or name can't go stale)
python3 tools/build_packages.py | grep -v '^built '
python3 tools/build_origins_menu.py  # (Origins' select archives with card slots; reads the packages' card pictures)
bash native/build.sh
# Mania Lock-On (mods/ManiaLockOn: the SONIC MANIA button, its own mod): its menu patches (from the game's archives;
# skipped when up to date) and its DLL
python3 tools/build_lockon_menu.py
bash native/lockon/build.sh
echo "all built"
