#!/usr/bin/env bash
# Copy dev mods from this repo into the game's HMM mods folder.
set -euo pipefail
GAME_MODS="${GAME_MODS:-$HOME/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec/mods}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
for mod in "$REPO"/mods/*/; do
    name="$(basename "$mod")"
    [ "$name" = "NoSwapMania" ] && continue  # (the Sonic Mania mod: tools/deploy_mania.sh, never into Origins)
    # Keep files the game writes (logs, the DLL's cache/ folder) and the player's own settings (NoSwapS3K.ini: installed
    # only if missing)
    # (Mania Lock-On: also its HedgeModManager settings, ManiaLockOn.ini, and the menu archives its DLL makes in raw/)
    extra=()
    [ "$name" = "ManiaLockOn" ] && extra=(--exclude 'ManiaLockOn.ini' --exclude '/raw/')
    rsync -a --delete --exclude '*.log' --exclude 'NoSwapS3K.ini' --exclude 'cache/' "${extra[@]}" "$mod" "$GAME_MODS/$name/"
    [ -f "$mod/NoSwapS3K.ini" ] && [ ! -f "$GAME_MODS/$name/NoSwapS3K.ini" ] && cp "$mod/NoSwapS3K.ini" "$GAME_MODS/$name/"
    echo "deployed $name"
done
