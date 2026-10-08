#!/usr/bin/env bash
# Deploy NoSwapMania to the Sonic Mania decomp play folder (default ~/Code/mania/run, ours: not the Steam install).
# The mod folder is symlinked, so later builds (native/mania/build.sh, tools/build_mania_art.py's packages) are live at the next
# game start. The decomp's mod loader only runs mods marked active in mods/modconfig.ini ([Mods] <folder>=y): this
# adds / sets that line and leaves the other mods' lines alone.
set -euo pipefail
cd "$(dirname "$0")/.."
RUN="${1:-$HOME/Code/mania/run}"
MOD=NoSwapMania
[ -f "mods/$MOD/$MOD.so" ] || { echo "mods/$MOD/$MOD.so missing: run native/mania/build.sh first" >&2; exit 1; }
ls mods/$MOD/Data/Sprites/NoSwap/*/noswap_character.json >/dev/null 2>&1 || { echo "no character packages: run tools/build_mania_art.py first" >&2; exit 1; }
mkdir -p "$RUN/mods"
if [ -e "$RUN/mods/$MOD" ] && [ ! -L "$RUN/mods/$MOD" ]; then
    echo "$RUN/mods/$MOD exists and isn't our symlink: not touching it" >&2
    exit 1
fi
ln -sfn "$PWD/mods/$MOD" "$RUN/mods/$MOD"

CFG="$RUN/mods/modconfig.ini"
if [ ! -f "$CFG" ]; then
    printf '[Mods]\n%s=y\n' "$MOD" > "$CFG"
elif grep -q "^$MOD=" "$CFG"; then
    sed -i "s/^$MOD=.*/$MOD=y/" "$CFG"
elif grep -q '^\[Mods\]' "$CFG"; then
    sed -i "/^\[Mods\]/a $MOD=y" "$CFG"
else
    printf '[Mods]\n%s=y\n' "$MOD" >> "$CFG"
fi
echo "deployed: $RUN/mods/$MOD -> mods/$MOD, enabled in $CFG"
