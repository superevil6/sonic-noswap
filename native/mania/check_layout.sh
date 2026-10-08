#!/usr/bin/env bash
# Check src/ManiaPlayer.h's Player / globals layout against the decompilation's own headers (compile only: nothing is
# run). Both sides compile the same list of sizes and offsets into a constant table; the tables must be identical.
# DECOMP_DIR: the Sonic-Mania-Decompilation checkout the game was built from (default ~/Code/mania/...).
set -euo pipefail
cd "$(dirname "$0")"
DECOMP_DIR="${DECOMP_DIR:-$HOME/Code/mania/Sonic-Mania-Decompilation}"
GAMEAPI_DIR="${GAMEAPI_DIR:-$HOME/Code/mania/RSDKv5-GameAPI}"
DEFS="-DRETRO_REVISION=3 -DRETRO_USE_MOD_LOADER=1 -DRETRO_MOD_LOADER_VER=2 -DGAME_VERSION=6 -DGAME_INCLUDE_EDITOR=1"
T=build/layout
mkdir -p $T
cat > $T/fields.inc <<'FIELDS'
sizeof(ObjectPlayer), sizeof(EntityPlayer), sizeof(Animator), sizeof(GlobalVariables),
F(ObjectPlayer, sonicPhysicsTable) F(ObjectPlayer, superPalette_Sonic) F(ObjectPlayer, superPalette_Sonic_HCZ)
F(ObjectPlayer, superPalette_Sonic_CPZ) F(ObjectPlayer, sonicFrames) F(ObjectPlayer, superFrames) F(ObjectPlayer, superDashCooldown)
F(EntityPlayer, state) F(EntityPlayer, animator) F(EntityPlayer, aniFrames) F(EntityPlayer, characterID)
F(EntityPlayer, drownTimer) F(EntityPlayer, underwater) F(EntityPlayer, superState) F(EntityPlayer, sidekick)
F(EntityPlayer, topSpeed) F(EntityPlayer, jumpStrength) F(EntityPlayer, jumpCap) F(EntityPlayer, stateInput) F(EntityPlayer, controllerID)
F(EntityPlayer, up) F(EntityPlayer, jumpPress) F(EntityPlayer, jumpHold) F(EntityPlayer, jumpAbilityState)
F(EntityPlayer, stateAbility) F(EntityPlayer, abilityValues) F(EntityPlayer, uncurlTimer)
F(EntityPlayer, outerbox) F(EntityPlayer, rings) F(EntityPlayer, score1UP) F(EntityPlayer, invincibleTimer) F(EntityPlayer, speedShoesTimer)
F(EntityPlayer, scoreBonus) F(EntityPlayer, gravityStrength) F(EntityPlayer, isGhost) F(EntityPlayer, controllerID)
F(EntityPlayer, blinkTimer) F(EntityPlayer, interaction) F(EntityPlayer, down) F(EntityPlayer, groundVel) F(EntityPlayer, direction)
F(GlobalVariables, gameMode) F(GlobalVariables, playerID) F(GlobalVariables, medalMods)
sizeof(EntityUISaveSlot), F(ObjectUISaveSlot, aniFrames) F(EntityUISaveSlot, parent) F(EntityUISaveSlot, isNewSave)
F(EntityUISaveSlot, stateInput) F(EntityUISaveSlot, frameID) F(EntityUISaveSlot, type) F(EntityUISaveSlot, slotID)
F(EntityUISaveSlot, encoreMode) F(EntityUISaveSlot, buttonBounceOffset) F(EntityUISaveSlot, uiAnimator)
F(EntityUISaveSlot, zoneIconAnimator) F(EntityUISaveSlot, textFrames)
F(EntityPlayer, nextAirState) F(EntityPlayer, nextGroundState) F(EntityPlayer, shield) F(EntityPlayer, groundedStore)
F(EntityPlayer, applyJumpCap) F(EntityPlayer, collisionMode) F(EntityPlayer, angle) F(EntityPlayer, onGround)
F(ObjectPlayer, sfxRelease) F(ObjectPlayer, sfxMightyDrill)
sizeof(EntityBreakableWall), F(EntityBreakableWall, state) F(EntityBreakableWall, size) F(EntityBreakableWall, hitbox)
FIELDS
printf '#include "Game.h"\n#include <stddef.h>\n#define F(t, f) offsetof(t, f),\nconst unsigned int layout[] = {\n#include "fields.inc"\n};\n' > $T/decomp.c
printf '#include "ManiaPlayer.h"\n#include "ManiaMenu.h"\n#define F(t, f) offsetof(t, f),\nconst unsigned int layout[] = {\n#include "fields.inc"\n};\n' > $T/ours.c
# Both builds: Linux (gcc, LP64) and Windows (mingw, LLP64: `long` is 32-bit there), so each one's offsets are checked
check() {  # check <name> <cc> <objcopy> <const data section>
    local cc=$2 objcopy=$3 sect=$4 d=$T/$1
    mkdir -p $d
    $cc -c -w $DEFS -DMANIA_PREPLUS=0 -DMANIA_FIRST_RELEASE=0 -I"$DECOMP_DIR/SonicMania" \
        -I"$DECOMP_DIR/SonicMania/Objects" -I$T $T/decomp.c -o $d/decomp.o
    $cc -c -w $DEFS -Isrc -I"$GAMEAPI_DIR/C" -I"$GAMEAPI_DIR/C/GameAPI" -I$T $T/ours.c -o $d/ours.o
    for side in decomp ours; do $objcopy -O binary -j $sect $d/$side.o $d/$side.bin; done
    if [ ! -s $d/ours.bin ]; then
        echo "$1: no layout table in $sect"; exit 1
    elif cmp -s $d/decomp.bin $d/ours.bin; then
        echo "$1 layout OK: $(od -An -tu4 -w1000 $d/ours.bin | tr -s ' ')"
    else
        echo "$1 LAYOUT MISMATCH"; od -An -tu4 -w1000 $d/decomp.bin; od -An -tu4 -w1000 $d/ours.bin; exit 1
    fi
}
check linux gcc objcopy .rodata
if command -v x86_64-w64-mingw32-gcc >/dev/null; then
    check windows x86_64-w64-mingw32-gcc x86_64-w64-mingw32-objcopy .rdata
else
    echo "windows layout: not checked (no x86_64-w64-mingw32-gcc)"
fi
