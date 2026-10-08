// NoSwapMania: NoSwap's extra characters for Sonic Mania Plus, as a code mod for the RSDKv5 decompilation's mod loader
// (built against RSDKv5-GameAPI; the Player layout in ManiaPlayer.h).
//
// Data-driven, like the Origins S3&K DLL: each extra is a package, a folder Data/Sprites/NoSwap/<folder>/ in this mod
// (tools/build_mania_art.py) with its noswap_character.json, its player sprites and its save select pictures. At startup
// the mod scans those folders in every active mod (a character can be its own download); the extras come in their
// "order" (tools/registry.py's numbers). Their moves are generic modules
// keyed by the S3&K DLL's ability fields (gen_s3k_header.ability_fields: the same names and numbers, from abilities.py):
//   - jet_dash (jetDash, dashFrames, dashSpeed): a jump press in mid-air dashes at a fixed speed (or his own if faster),
//     no fall, an attack; then hover (hover, hoverFrames, hoverSink): holding jump after the dash sinks slowly;
//   - double_jump (doubleJump, doubleJumpScale): a jump press in mid-air is a second jump at that part of the jump's
//     strength, spinning (an attack) until the fall starts (Bean's Leap, Trip's, Bomb's);
//   - umbrella (umbrella, umbrellaSink, floatFrames, umbrellaAttack): a jump press in mid-air opens a float, falling at
//     most umbrellaSink while jump is held, for floatFrames at most (0: no limit); with umbrellaAttack it's on the attack
//     animation and hurts (Espio's Whirlwind);
//   - no_breathing (noBreathing): never drowns (the drown timer held at 0);
//   - physics (topSpeed, acceleration, airAcceleration, jump: x1000 of Sonic's).
//   - shots (the package's "shot" / "shot2" and Shot.bin: abilities.py's projectiles, S3&K's numbers, as the S3&K DLL's
//     namespace shots): Y throws one (down + Y the second), with its throw pose; see "shots" below.
//   - melee without a shot (shot, shotFrames, shotTicks, shotAirFrames, shotCooldown, shotBlink, shotStop, shotHang,
//     shotSafe, shotCost, nuke*): Y's pose move, its reach the pose frames' own boxes, and its options (the nuke, safe,
//     cost...); see "melee" below.
//   - no_roll (the package's "no_roll", extras.py: Gamma): never curls into a ball; see Hook_NoRollInput.
//   - chaos_control (chaosFreeze / Warp / Speed / Pop: Shadow), aim_dash (dashFrames, dashSpeed, diagX / Y, upX / Y:
//     Blaze, Vector), screw_kick by jump (kickOnJump, kickX / Y: Mecha Sonic, Sally, Emerl), hammer_drop (Mania's own
//     Player_State_MightyHammerDrop: Bark; its landing throws a "slam" shot), water_swim (swimStroke, swimDelay: Big):
//     jump presses in mid-air, as the others; ability_cycle (cycleCount, cycleMoves: Emerl): Y's melee picks which
//     one; high_kick (Sally): Y, see HighKick; melee_boost (shotBoost: Mecha, Bark): the melee as a burst of speed.
//   - breaks_walls, shot_breaks_walls (Gamma), fire_immune (Blaze): objects' updates wrapped, see ManiaWalls.h.
// A move the package lists ("moves") that has no module here yet is skipped (logged once at startup). One mid-air move
// per jump (the jump press that would start Sonic's insta-shield, drop dash or shield move); Y still turns him Super.
//
// Hosting: an extra plays on its host's character ID (as NoSwap does in Origins): Sonic's, or Tails' / Knuckles' for the
// extras built on them (the package's "host"; ManiaHost.h). Who plays (modSettings.ini Character):
//   - "menu" (the default): Mania Mode's save select. On the No Save slot or a new save, up/down cycles Sonic & Tails,
//     Sonic, Tails, Knuckles, Mighty, Ray, then the extras, then back round; the slot shows the extra's own pictures. The
//     game itself sees Sonic (its save keeps characterID Sonic); the extra of each numbered save is kept in NoSwap's own
//     file, NoSwapManiaSlots.ini, next to the game's SaveData.bin (its working folder). Only Mania Mode;
//   - a package's folder name (e.g. "metal-sonic"): every Sonic everywhere is that extra (a test switch);
//   - "none": the game as it is.
// Per extra, at stage load: its sprites in place of Sonic.bin and SuperSonic.bin; its own colours in their palette slots
// (the JSON's "palette": Sonic's 64-69 and the global rows' unused 86-90, 111, 127), their other banks' versions (water,
// smog...: "host_tint" slots take the stage's Sonic colours there, the rest a tinted version); Super fades its
// "super_fade" slots to Sonic's golds, the others stay.
#include "ManiaPlayer.h"
#include "ManiaMenu.h"
#include "JsonLite.h"

#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#undef near // (old 16-bit keywords, defined empty by windows.h: the code uses them as variable names)
#undef far
#else
#include <dirent.h>
#endif

ObjectPlayer *Player         = NULL;
ObjectUISaveSlot *UISaveSlot = NULL;

#define LOG_TAG "[NoSwapMania] "

// ------------------------------------------------------------------------------------------------ loading sprites safely
// The engine holds 64 sprite sheets at once (RSDKv5 Drawing.hpp SURFACE_COUNT). A sheet it can't load (all in use, or a
// missing / unreadable GIF) still lets its animation file load, with those frames on sheet 0xFF, past the end of the
// engine's sheet table: drawing one crashes (the save select with 28 extras, 2026-10-01). So every animation file the mod
// loads is checked with this before anything draws from it.
#define NS_SURFACE_COUNT (0x40)
#define NS_SPRFILE_COUNT (0x400)

// `id` loaded, has animation `needAnim`, and every frame of every animation is on a loaded sheet
static bool32 AniFramesOK(uint16 id, int32 needAnim)
{
    if (id >= NS_SPRFILE_COUNT || !RSDK.GetFrame(id, needAnim, 0))
        return false;
    for (int32 a = 0; a < 0x1000 && RSDK.GetFrame(id, a, 0); ++a) {
        Animator ani;
        memset(&ani, 0, sizeof(ani));
        RSDK.SetSpriteAnimation(id, a, &ani, true, 0);
        // (each frame through GetFrame: the engine's own SpriteFrame is larger than the API's (it also holds the hitboxes),
        // so stepping ani.frames[f] read every frame past the first from the wrong place and failed good files)
        for (int32 f = 0; f < ani.frameCount; ++f) {
            SpriteFrame *frame = RSDK.GetFrame(id, a, f);
            if (!frame || frame->sheetID >= NS_SURFACE_COUNT)
                return false;
        }
    }
    return true;
}

// ------------------------------------------------------------------------------------------------ the packages
#define PACKAGE_DIR    "Data/Sprites/NoSwap" // (inside the mod's folder)
#define PACKAGE_JSON   "noswap_character.json"
#define EXTRA_MAX      (64)
#define OWN_MAX        (32) // (Sonic's 6, the global rows' 7 unused, and for a Mania-only package Mighty's and Ray's 6 each: tools/mania_v5_art.py)
#define SAVE_PAL_COUNT (27)  // the save select pictures' colours: in SAVE_SLOTS (tools/build_mania_art.py's list)
#define FLASH_MAX      (32)  // a nuke's flash frames (gen_s3k_header.FLASH_MAX)
static const uint8 SAVE_SLOTS[SAVE_PAL_COUNT] = { 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155,
                                                  156, 157, 158, 159, 160, 190, 191, 192, 193, 194, 195, 196, 197 };
#define NAME_PAL_COUNT (7) // the act clear / UFO results name's colours: SONIC's letters' global slots (ui_accent.MANIA_NAME_SLOTS)
static const uint8 NAME_SLOTS[NAME_PAL_COUNT] = { 2, 3, 4, 5, 6, 7, 11 };

// The ability fields the modules read: gen_s3k_header.ability_fields' names, and their defaults there (a package lists
// only the fields not at their default)
#define ABILITY_FIELDS(X)                                                                                                        \
    X(jetDash, 0) X(dashFrames, 0) X(dashSpeed, 0) X(hover, 0) X(hoverFrames, 0) X(hoverSink, 0) X(doubleJump, 0)               \
    X(doubleJumpScale, 1000) X(umbrella, 0) X(umbrellaSink, 0) X(floatFrames, 0) X(umbrellaAttack, 0) X(noBreathing, 0)       \
    X(topSpeed, 1000) X(acceleration, 1000) X(airAcceleration, 1000) X(jump, 1000) X(shotAirFrames, 0) X(shot, 0)            \
    X(shotFrames, 0) X(shotTicks, 1) X(shotCooldown, 0) X(shotBlink, 0) X(shotStop, 0) X(shotHang, 0) X(shotSafe, 0)         \
    X(shotCost, 0) X(nukeAt, -1) X(nukeHit, 0) X(nukeReachX, 0) X(nukeReachY, 0) X(chaosControl, 0) X(chaosFreeze, 0)         \
    X(chaosWarp, 0) X(chaosSpeed, 0) X(chaosPop, 0) X(aimDash, 0) X(diagX, 0) X(diagY, 0) X(upX, 0) X(upY, 0)                 \
    X(screwKick, 0) X(kickOnJump, 0) X(kickX, 0) X(kickY, 0) X(kickBounce, 0) X(shotBoost, 0) X(hammerDrop, 0)              \
    X(highKick, 0) X(highKickWindup, 0) X(highKickRise, 0) X(highKickTicks, 1) X(highKickRecover, 0)                         \
    X(highKickCooldown, 0) X(cycleCount, 0) X(waterSwim, 0) X(swimStroke, 0) X(swimDelay, 0) X(breaksWalls, 0)              \
    X(fireImmune, 0)                                                                                                          \
    X(anchorThrow, 0) X(anchorSpeed, 0) X(anchorRise, 0) X(anchorHighSpeed, 0) X(anchorHighRise, 0) X(anchorGravity, 0)       \
    X(anchorFrames, 0) X(anchorReturn, 0) X(anchorCooldown, 0) X(reelSpeed, 0) X(reelFrames, 0) X(latchRange, 0)             \
    X(grappleHop, 0) X(grappleForward, 0) X(waterWalk, 0) X(sink, 0) X(sinkTicks, 1) X(sinkSteps, 0) X(sinkUnderCount, 0)    \
    X(sinkUnderTicks, 1) X(sinkMax, 0) X(sinkCooldown, 0) X(floatLean, 0) X(floatLeanMax, 0) X(copyHeads, 0)                 \
    X(psychoGrab, 0) X(psychoReach, 0) X(psychoBehind, 0) X(psychoHeight, 0) X(psychoHold, 0) X(psychoThrow, 0)              \
    X(psychoTicks, 0) X(meleeRunSpeed, 0) X(meleeRunBoost, 0) X(meleeRunFrames, 0) X(meleeUp, 0) X(meleeUpRings, 0)       \
    X(meleeUpFrames, 0) X(noStomp, 0) X(tripleJump, 0) X(tripleWindow, 0) X(tripleSpeed, 0) X(triple2, 1000)                \
    X(triple3, 1000)

typedef struct {
#define X(name, def) int32 name;
    ABILITY_FIELDS(X)
#undef X
} Abilities;

// abilities.py move names that have a module here (the rest are skipped)
static const char *const MOVES_DONE[] = { "jet_dash", "hover", "no_breathing", "physics", "double_jump", "umbrella", "melee",
                                          "popgun", // (melee's old name: packages built before 2026-10 list it)
                                          "chaos_control", "aim_dash", "fire_immune", "screw_kick", "high_kick", "water_swim",
                                          "hammer_drop", "breaks_walls", "anchor_throw", "water_walk", "sink",
                                          "psycho_grab", "rocket_ride", "ear_grapple", "spirit_flight", "wall_cling",
                                          "extreme_gear", "puddle_slide", "charge", "spin_attack", "phase_warp", // (the last nine: ManiaBatch.h)
                                          "ground_slide", "rocket_burst", // (ManiaGuest.h)
                                          "star_grab", "head_throw", "monitor_swap", "free_swim", // (ManiaCross.h)
                                          "free_flight", // (ManiaNights.h)
                                          "voltteccer", // (ManiaVoltteccer.h)
                                          "ninjutsu", // (ManiaNinjutsu.h)
                                          "pot_magic", // (ManiaPotMagic.h)
                                          "no_stomp", // (ManiaNoStomp.h)
                                          "triple_jump" }; // (ManiaTriple.h)
#define CYCLE_MAX (4) // gen_s3k_header.CYCLE_MAX: ability_cycle's moves (1 double jump, 2 Screw Kick by jump, 3 Jet Dash, 4 umbrella)

#include "ManiaShot.h"
#include "ManiaMoreData.h"
#include "ManiaGhost.h"
#include "ManiaGuestData.h" // (the guest batch's numbers: ManiaGuest.h)
static void ReadNights(const JsonNode *ab, const char *folder); // (NiGHTS' numbers: ManiaNights.h)
static void ReadVolt(const JsonNode *ab, const char *folder); // (Pulseman's numbers: ManiaVoltteccer.h)

typedef struct {
    char folder[64];
    char name[64];
    int32 order;
    char playerFile[160];     // relative to Data/Sprites
    char saveSelectFile[160]; // relative to Data/Sprites
    int32 animBase;           // its first ability animation (abilities.py slot 41; 42 is animBase + 1)
    int32 ownCount;
    uint8 ownSlot[OWN_MAX];
    color ownColour[OWN_MAX];
    bool32 hostTint[OWN_MAX];
    bool32 superFade[OWN_MAX];
    int32 saveColourCount;
    color saveColours[SAVE_PAL_COUNT];
    int32 signColourCount;             // its signpost face's colours ("sign_colors": ManiaHud.h writes them in SAVE_SLOTS)
    color signColours[SAVE_PAL_COUNT];
    int32 nameColourCount;             // its results name's colours ("name_colors": ManiaHud.h writes them in NAME_SLOTS; 0: Sonic's blue)
    color nameColours[NAME_PAL_COUNT];
    Abilities ab;
    char shotFile[160]; // its Shot.bin, relative to Data/Sprites ("" : no shot)
    ShotData shot, shot2;
    bool32 noRoll;           // extras.py "no_roll"
    bool32 roll;             // extras.py "roll" (its own Rolling animation: ManiaNoStomp.h NoStompUpdate)
    char shotSound[64];      // the melee's sound ("": none)
    char nukeSound[64];      // its nuke's
    char meleeRunSound[64];  // melee_run / melee_up's own sounds ("": the melee's)
    char meleeUpSound[64];
    int32 nukeFlashCount;    // its nuke's flash: the screen's darkness per game frame (0-255)
    uint8 nukeFlash[FLASH_MAX];
    int32 cycleMoves[CYCLE_MAX]; // ability_cycle (cycleCount of them)
    char kickSound[64];          // the Screw Kick's sound ("": none)
    char highKickSound[64];      // the Spin-Kick High Jump's
    bool32 shotBreaksWalls;      // abilities.py "shot_breaks_walls" (Gamma): his shots break breakable walls ("walls" below)
    MoreData more;               // ManiaMore.h: the Shadow Sink's frames, the move sounds, copy heads, the charge flash
} Extra;

static Extra g_extras[EXTRA_MAX];
static int32 g_extraCount = 0;

static int32 ExtraIndex(const char *folder)
{
    for (int32 i = 0; i < g_extraCount; ++i)
        if (strcmp(g_extras[i].folder, folder) == 0)
            return i;
    return -1;
}

static bool32 IsIn(const JsonNode *array, int32 value)
{
    if (array && array->type == JSON_ARRAY)
        for (JsonNode *n = array->child; n; n = n->next)
            if (Json_Int(n, -1) == value)
                return true;
    return false;
}

static int32 Clamp255(int32 v) { return v < 0 ? 0 : v > 255 ? 255 : v; }

static void CopyText(char *out, size_t size, const char *text)
{
    snprintf(out, size, "%s", text ? text : "");
}

// One package's JSON into g_extras (false: not usable, logged)
static bool32 LoadPackage(const char *dir, const char *folder)
{
    if (g_extraCount >= EXTRA_MAX) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "more than %d packages: %s left out", EXTRA_MAX, folder);
        return false;
    }
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s/%s", dir, folder, PACKAGE_JSON);
    int32 line     = 0;
    JsonNode *root = Json_ParseFile(path, &line);
    if (!root) {
        if (line)
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s isn't valid JSON (line %d): left out", path, line);
        return false; // (no file: not a package)
    }
    JsonNode *mania = Json_Get(root, "mania");
    const char *player = Json_String(Json_Get(mania, "player"), NULL);
    const char *save   = Json_String(Json_Get(mania, "save_select"), NULL);
    if (!player || !save || strlen(folder) >= sizeof(g_extras[0].folder)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s has no Mania data (\"mania\" with \"player\" and \"save_select\"): left out", path);
        Json_Free(root);
        return false;
    }

    Extra *e = &g_extras[g_extraCount];
    memset(e, 0, sizeof(*e));
    CopyText(e->folder, sizeof(e->folder), folder);
    CopyText(e->name, sizeof(e->name), Json_String(Json_Get(root, "name"), folder));
    e->order = Json_Int(Json_Get(root, "order"), 1 << 20);
    CopyText(e->playerFile, sizeof(e->playerFile), player);
    CopyText(e->saveSelectFile, sizeof(e->saveSelectFile), save);
    e->animBase = Json_Int(Json_Get(mania, "anim_base"), ANI_SONIC_COUNT);

    JsonNode *palette = Json_Get(mania, "palette");
    JsonNode *host = Json_Get(mania, "host_tint"), *fade = Json_Get(mania, "super_fade");
    for (JsonNode *n = palette ? palette->child : NULL; n && palette->type == JSON_OBJECT; n = n->next) {
        int32 slot = n->key ? atoi(n->key) : 0, colour = Json_Colour(n);
        if (slot <= 0 || slot > 255 || colour < 0 || e->ownCount >= OWN_MAX) {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: palette entry \"%s\" skipped", folder, n->key ? n->key : "?");
            continue;
        }
        e->ownSlot[e->ownCount]   = (uint8)slot;
        e->ownColour[e->ownCount] = (color)colour;
        e->hostTint[e->ownCount]  = slot >= PLAYER_PALETTE_INDEX_SONIC && slot < PLAYER_PALETTE_INDEX_SONIC + PLAYER_PRIMARY_COLOR_COUNT && IsIn(host, slot);
        e->superFade[e->ownCount] = IsIn(fade, slot);
        e->ownCount++;
    }
    JsonNode *saveColours = Json_Get(mania, "save_colors");
    for (JsonNode *n = saveColours ? saveColours->child : NULL; n && e->saveColourCount < SAVE_PAL_COUNT; n = n->next) {
        int32 colour = Json_Colour(n);
        e->saveColours[e->saveColourCount++] = colour < 0 ? 0 : (color)colour;
    }
    JsonNode *signColours = Json_Get(mania, "sign_colors");
    for (JsonNode *n = signColours ? signColours->child : NULL; n && e->signColourCount < SAVE_PAL_COUNT; n = n->next) {
        int32 colour = Json_Colour(n);
        e->signColours[e->signColourCount++] = colour < 0 ? 0 : (color)colour;
    }
    JsonNode *nameColours = Json_Get(mania, "name_colors");
    for (JsonNode *n = nameColours ? nameColours->child : NULL; n && e->nameColourCount < NAME_PAL_COUNT; n = n->next) {
        int32 colour = Json_Colour(n);
        e->nameColours[e->nameColourCount++] = colour < 0 ? 0 : (color)colour;
    }
    if (e->nameColourCount != NAME_PAL_COUNT)
        e->nameColourCount = 0; // (all of them or none: a partial ramp would mix in Sonic's blue)

    JsonNode *ab = Json_Get(mania, "abilities");
#define X(field, def) e->ab.field = Json_Int(Json_Get(ab, #field), def);
    ABILITY_FIELDS(X)
#undef X

    if (e->ab.shotTicks < 1)
        e->ab.shotTicks = 1;
    e->noRoll = Json_Int(Json_Get(mania, "no_roll"), 0) != 0;
    e->roll   = Json_Int(Json_Get(mania, "roll"), 0) != 0;
    CopyText(e->shotSound, sizeof(e->shotSound), Json_String(Json_Get(ab, "shotSound"), ""));
    CopyText(e->nukeSound, sizeof(e->nukeSound), Json_String(Json_Get(ab, "nukeSound"), ""));
    CopyText(e->meleeRunSound, sizeof(e->meleeRunSound), Json_String(Json_Get(ab, "meleeRunSound"), ""));
    CopyText(e->meleeUpSound, sizeof(e->meleeUpSound), Json_String(Json_Get(ab, "meleeUpSound"), ""));
    CopyText(e->kickSound, sizeof(e->kickSound), Json_String(Json_Get(ab, "kickSound"), ""));
    CopyText(e->highKickSound, sizeof(e->highKickSound), Json_String(Json_Get(ab, "highKickSound"), ""));
    JsonNode *cycle = Json_Get(ab, "cycleMoves");
    int32 cycled = 0;
    for (JsonNode *n = cycle && cycle->type == JSON_ARRAY ? cycle->child : NULL; n && cycled < CYCLE_MAX; n = n->next)
        e->cycleMoves[cycled++] = Json_Int(n, 0);
    if (e->ab.cycleCount > cycled)
        e->ab.cycleCount = cycled;
    if (e->ab.highKickTicks < 1)
        e->ab.highKickTicks = 1;
    e->shotBreaksWalls = Json_Int(Json_Get(mania, "shot_breaks_walls"), 0) != 0;
    JsonNode *flash = Json_Get(ab, "nukeFlash");
    for (JsonNode *n = flash && flash->type == JSON_ARRAY ? flash->child : NULL; n && e->nukeFlashCount < FLASH_MAX; n = n->next)
        e->nukeFlash[e->nukeFlashCount++] = (uint8)Clamp255(Json_Int(n, 0));

    ReadMore(mania, ab, &e->more, folder);
    ReadGuest(ab, folder); // (ManiaGuestData.h)
    ReadNights(ab, folder); // (ManiaNights.h)
    ReadVolt(ab, folder); // (ManiaVoltteccer.h)
    ReadShot(Json_Get(mania, "shot"), &e->shot, folder, "shot");
    ReadShot(Json_Get(mania, "shot2"), &e->shot2, folder, "shot2");
    CopyText(e->shotFile, sizeof(e->shotFile), Json_String(Json_Get(mania, "shot_file"), ""));
    if (e->shot.motion != SHOT_NONE && !e->shotFile[0]) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: a shot but no \"shot_file\": no shot", folder);
        e->shot.motion = SHOT_NONE;
    }
    if (e->shot2.motion != SHOT_NONE && (e->shot.motion == SHOT_NONE || !(e->shot2.downOnly || e->shot2.onCharge) || e->shot.downOnly || e->shot2.aim)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: shot2 needs \"input\" \"down\" or \"charge\", no aim, and a shot on Y alone: no second shot", folder);
        e->shot2.motion = SHOT_NONE;
    }

    // (log once: the moves it has that aren't here yet)
    JsonNode *moves = Json_Get(mania, "moves");
    for (JsonNode *n = moves && moves->type == JSON_ARRAY ? moves->child : NULL; n; n = n->next) {
        const char *move = Json_String(n, "?");
        bool32 done      = false;
        for (size_t i = 0; i < sizeof(MOVES_DONE) / sizeof(MOVES_DONE[0]) && !done; ++i) done = strcmp(move, MOVES_DONE[i]) == 0;
        if (!done)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: \"%s\" isn't in the Mania mod yet: skipped", folder, move);
    }
    Json_Free(root);
    ++g_extraCount;
    return true;
}

static int ByOrder(const void *a, const void *b)
{
    const Extra *x = (const Extra *)a, *y = (const Extra *)b;
    return x->order != y->order ? (x->order < y->order ? -1 : 1) : strcmp(x->folder, y->folder);
}

// One package folder found in a mod: loaded unless a mod scanned before it has a package of the same folder (the engine
// serves Data/ files from the first active mod that has them, so that one's files are what the game would load)
static void LoadPackageOnce(const char *dir, const char *folder, const char *modID)
{
    if (ExtraIndex(folder) >= 0) {
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s/%s: a package \"%s\" was already found in another mod: left out", modID, folder, folder);
        return;
    }
    LoadPackage(dir, folder);
}

// Every Data/Sprites/NoSwap/<folder>/noswap_character.json in one mod's folder
static void ScanModPackages(const char *modID)
{
    String modPath;
    INIT_STRING(modPath);
    Mod.GetModPath(modID, &modPath);
    char root[256] = { 0 };
    if (modPath.chars && modPath.length && modPath.length < sizeof(root) - 1)
        RSDK.GetCString(root, &modPath);
    else
        snprintf(root, sizeof(root), "mods/%s", modID);
    char dir[400];
    snprintf(dir, sizeof(dir), "%s/%s", root, PACKAGE_DIR);

#ifdef _WIN32
    char pattern[420];
    snprintf(pattern, sizeof(pattern), "%s/*", dir);
    WIN32_FIND_DATAA found;
    HANDLE h = FindFirstFileA(pattern, &found);
    if (h != INVALID_HANDLE_VALUE) {
        do {
            if ((found.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && found.cFileName[0] != '.')
                LoadPackageOnce(dir, found.cFileName, modID);
        } while (FindNextFileA(h, &found));
        FindClose(h);
    }
#else
    DIR *d = opendir(dir);
    if (d) {
        struct dirent *ent;
        while ((ent = readdir(d)))
            if (ent->d_name[0] != '.')
                LoadPackageOnce(dir, ent->d_name, modID); // (a plain file has no JSON inside: skipped)
        closedir(d);
    }
#endif
}

// The packages of every active mod (so a character can be its own download: any mod with Data/Sprites/NoSwap/<folder>/
// noswap_character.json), in the loader's priority order; just this mod's if the loader can't list them
static void ScanPackages(const char *modID)
{
    g_extraCount = 0;
    int32 mods = Mod.GetModCount && Mod.GetModIDByIndex ? Mod.GetModCount(true) : 0;
    bool32 self = false;
    for (int32 m = 0; m < mods; ++m) {
        const char *id = Mod.GetModIDByIndex((uint32)m);
        if (!id)
            continue;
        self |= strcmp(id, modID) == 0;
        ScanModPackages(id);
    }
    if (!self)
        ScanModPackages(modID);
    qsort(g_extras, (size_t)g_extraCount, sizeof(Extra), ByOrder);
    for (int32 i = 0; i < g_extraCount; ++i)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "extra %d: %s (%s)", i + 1, g_extras[i].name, g_extras[i].folder);
    if (!g_extraCount)
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "no character packages in any active mod's %s", PACKAGE_DIR);
}

// ------------------------------------------------------------------------------------------------ settings
enum { MODE_OFF, MODE_MENU, MODE_ALWAYS };
static int32 g_mode = MODE_OFF;      // the setting (read at link time)
static char g_settingFolder[64];     // MODE_ALWAYS: the package it names
static int32 g_alwaysExtra  = -1;    // ... its index
static int32 g_playExtra    = -1;    // the extra the save select started the game with (-1: none)
static const int32 SONIC_TOP_SPEED = 0x60000; // sonicPhysicsTable[0] as the game ships it

// ------------------------------------------------------------------------------------------------ game functions
static void (*Player_State_Air_)(void);
static void (*Player_JumpAbility_Sonic_)(void);
static void (*Player_Input_P2_AI_)(void);

// ------------------------------------------------------------------------------------------------ per stage
static const Extra *g_cur   = NULL;  // the extra playing this stage (NULL: none)
static bool32 g_active      = false; // ... and it's set up
static uint16 g_extraFrames = 0;
static uint16 g_sonicFrames = 0; // the game's Sonic.bin / SuperSonic.bin IDs (swapped for the extra's when an object reloads them)
static uint16 g_superFrames = 0;
static int32 g_animAttack   = -1; // its attack animation (slot 41), or -1 (missing)
static int32 g_animHover    = -1; // its hover animation (slot 42), or -1
static color g_hostBank0[OWN_MAX]; // what the stage had in its own slots, as read back

// the moves this stage (the abilities, less those whose animation is missing)
static bool32 g_jetDash, g_hover, g_doubleJump, g_umbrella, g_chaos, g_aimDash, g_kick, g_hammer, g_swim, g_highKick;
static int32 g_animAttackUp   = -1; // the aimed dash's up / down poses (slots 44 / 45; missing: the attack's)
static int32 g_animAttackDown = -1;
static int32 g_animSwim       = -1; // water_swim's stroke (slot 46)
static int32 g_animHkPose     = -1; // the high kick's wind-up / recovery pose (slot 42) and kick (slot 43)
static int32 g_animHkKick     = -1;
static int32 g_copy           = 0;  // ability_cycle: the active move's place in the cycle (the melee's Y picks the next)

typedef struct {
    int32 dash;      // Jet Dash frames left
    int32 hover;     // 0 none; 1 allowed (the dash just ended); 2.. hovering (frames used + 1)
    int32 dbl;       // the double jump is rising
    int32 umbrella;  // 0 not yet this jump; 1 open; 2 closed
    int32 floated;   // frames the umbrella has been open
    int32 chaos;     // Chaos Control: frames left (the flash, then the warp); -1 the hop after it, while rising
    int32 aim;       // the aimed dash's frames left
    int32 aimDir;    // ... -1 up, 0 straight, 1 down
    bool32 aimLeft;  // ... the way it started (turning round mid-dash doesn't redirect it)
    int32 kick;      // the Screw Kick by jump (the dive): diving
    bool32 kickLeft; // ... its direction
    int32 hammer;    // the Hammer Drop: 1 dropping (the game's Player_State_MightyHammerDrop), 2 landed this frame
    int32 hammerVY;  // ... its fall speed as the frame ended (a badnik's bounce shows next frame)
    int32 swimDelay; // water swim: frames before the next stroke
} MoveState;
static MoveState g_moves[PLAYER_COUNT];
static int32 g_meleeLeft = 0; // player 1's melee: frames left (0: none; "melee" below)
static void (*Player_State_MightyHammerDrop_)(void);

// Sally's Spin-Kick High Jump (player 1's; HighKick, after every entity's update)
#define HIKICK_KICK    (1000) // (abilities.py HIGH_KICK_KICK / HIGH_KICK_RECOVER: the phases' first numbers)
#define HIKICK_RECOVER (2000)
static struct {
    int32 k;     // 0 none; 1.. the wind-up; HIKICK_KICK.. the kick; HIKICK_RECOVER.. the recovery
    bool32 used; // used this airborne period
    int32 cool;  // frames on the ground before the next
} g_hk;

static int32 g_hostID = ID_SONIC; // the character the playing extra is hosted on (ManiaHost.h: Sonic, Tails or Knuckles)

static bool32 IsExtra(EntityPlayer *player)
{
    return g_active && Player && player && player->classID == Player->classID && player->characterID == g_hostID;
}

static MoveState *StateOf(EntityPlayer *player)
{
    int32 slot = RSDK.GetEntitySlot(player);
    return slot >= 0 && slot < PLAYER_COUNT ? &g_moves[slot] : NULL;
}

// The animator shows `anim` of the extra's file (whatever ID it reports)
static bool32 Showing(EntityPlayer *player, int32 anim)
{
    return anim >= 0 && player->aniFrames == g_extraFrames && player->animator.frames == RSDK.GetFrame(g_extraFrames, anim, 0);
}

// One of its own animations. `attacking`: reported to the game as the jump (ANI_JUMP), which is how Player_CheckAttacking
// decides it hurts badniks and bosses, and how Player_State_Air keeps running its jump ability (as in the S3&K DLL).
static void Show(EntityPlayer *player, int32 anim, bool32 attacking, bool32 restart)
{
    if (restart || !Showing(player, anim))
        RSDK.SetSpriteAnimation(g_extraFrames, anim, &player->animator, true, 0);
    if (attacking)
        player->animator.animationID = ANI_JUMP;
}

static void BackToJump(EntityPlayer *player) { RSDK.SetSpriteAnimation(player->aniFrames, ANI_JUMP, &player->animator, true, 0); }

static int32 UmbrellaAnim(void) { return g_cur->ab.umbrellaAttack ? g_animAttack : g_animHover; }

// The aimed dash's pose for its direction (up / down: their own slots, or the straight one)
static int32 AimAnim(int32 dir)
{
    int32 anim = dir < 0 ? g_animAttackUp : dir > 0 ? g_animAttackDown : -1;
    return anim >= 0 ? anim : g_animAttack;
}

// ability_cycle (Emerl's Copycat): the active move's code (abilities.CYCLE_MOVES: 1 double jump, 2 the Screw Kick by jump,
// 3 Jet Dash, 4 umbrella); 0: no cycle. MoveOn: that move may start (no cycle: every move the extra has)
static int32 CycleMove(void) { return g_cur->ab.cycleCount > 0 ? g_cur->cycleMoves[g_copy % g_cur->ab.cycleCount] : 0; }
static bool32 MoveOn(int32 code) { int32 c = CycleMove(); return c == 0 || c == code; }

static void PlayNamed(const char *path)
{
    if (!path || !path[0])
        return;
    uint16 sfx = RSDK.GetSfx(path);
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}

// Landed or taken over by an object: the moves end (an attack pose still showing becomes the real jump ball, so the
// landing goes as any jump's). The swim's delay goes on.
static void EndMoves(EntityPlayer *player, MoveState *m)
{
    bool32 attackPose = m->dash > 0 || m->dbl || (m->umbrella == 1 && g_cur->ab.umbrellaAttack) || m->chaos || m->aim > 0 || m->kick
                        || m->hammer;
    if (attackPose && player->animator.animationID == ANI_JUMP
        && (Showing(player, g_animAttack) || Showing(player, g_animAttackUp) || Showing(player, g_animAttackDown)))
        BackToJump(player);
    int32 swimDelay = m->swimDelay;
    memset(m, 0, sizeof(*m));
    m->swimDelay = swimDelay;
}

// ------------------------------------------------------------------------------------------------ moves
// Mighty's Hammer Drop (abilities.py hammer_drop: Bark's Slam Ground), Mania Plus' own: Player_JumpAbility_Mighty's start,
// then the game's Player_State_MightyHammerDrop itself (his landing bounce, sounds, dust and screen shake), in the attack
// pose reported as the jump (Sonic's attack rules); Hook_HammerBefore / After give him Mighty's plowing through badniks
static bool32 BatchJump(EntityPlayer *self); // (ManiaBatch.h: the Sonic-hosted batch's jump moves)
static bool32 GuestJump(EntityPlayer *self); // (ManiaGuest.h: the Rocket Burst)
static bool32 AmyJump(EntityPlayer *self);   // (ManiaAmy.h: the Hammer Jump)
static void AmyAir(EntityPlayer *self);

static void HammerStart(EntityPlayer *self, MoveState *m)
{
    self->velocity.x >>= 1;
    self->velocity.y      = self->underwater ? 0x80000 : 0xC0000;
    m->hammer             = 1;
    m->hammerVY           = self->velocity.y;
    self->nextAirState    = NULL;
    self->nextGroundState = NULL;
    Show(self, g_animAttack, true, true);
    RSDK.PlaySfx(Player->sfxRelease, false, 0xFF);
    RSDK.PlaySfx(Player->sfxMightyDrill, false, 0xFE);
    self->state = Player_State_MightyHammerDrop_;
}

// Sonic's jump ability (Player_State_Air runs it, after gravity, while he's in the jump ball rising slower than the jump
// cap). For an extra: the jump press that would start the insta-shield, drop dash or a shield move starts its own move
// instead (or nothing). Everything else goes on to Sonic's own code, which then only checks Y for going Super
// (jumpAbilityState never gets past 1).
static bool32 Hook_JumpAbilitySonic(bool32 skipped)
{
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (skipped || !IsExtra(self))
        return false;
    if ((g_meleeLeft > 0 || g_hk.k > 0) && RSDK.GetEntitySlot(self) == SLOT_PLAYER1)
        return true; // (the melee's pose or the high kick: no jump ability, nor Sonic's, meanwhile)

    if (self->jumpAbilityState == 1 && self->jumpPress
        && (self->stateInput != Player_Input_P2_AI_ || (self->up && globals->gameMode != MODE_ENCORE))) {
        if (g_cur->more.amy.on)
            return AmyJump(self); // (Amy: the Hammer Jump, ManiaAmy.h)
        MoveState *m = StateOf(self);
        if (!m)
            return false;
        self->jumpAbilityState = 0;
        bool32 left            = (self->direction & FLIP_X) != 0;
        if (g_swim && self->underwater) {
            // (underwater the press is a swim stroke, Hook_StateAir: no other move this jump)
        }
        else if (g_jetDash && MoveOn(3)) {
            m->dash  = g_cur->ab.dashFrames;
            m->hover = 0;
            Show(self, g_animAttack, true, true); // (the dash's speed: Hook_StateAir, right after this frame's air state)
        }
        else if (g_doubleJump && MoveOn(1)) {
            // (S3&K's DoubleJump: its strength part of the jump's; this runs after the frame's gravity, so none is added)
            self->velocity.y = -(int32)((int64)self->jumpStrength * g_cur->ab.doubleJumpScale / 1000);
            m->dbl           = 1;
            Show(self, g_animAttack, true, true);
        }
        else if (g_kick && MoveOn(2)) {
            m->kick     = 1; // (its speed: Hook_StateAir)
            m->kickLeft = left;
            Show(self, g_animAttack, true, true);
            PlayNamed(g_cur->kickSound);
        }
        else if (g_umbrella && MoveOn(4) && m->umbrella == 0) {
            m->umbrella = 1; // (the float itself: Hook_StateAir)
            m->floated  = 0;
        }
        else if (g_chaos && CycleMove() == 0) {
            m->chaos = g_cur->ab.chaosFreeze + g_cur->ab.chaosWarp;
            if (RSDK.GetEntitySlot(self) == SLOT_PLAYER1)
                afterImage_Clear();
            Show(self, g_animAttack, true, true);
        }
        else if (g_aimDash && CycleMove() == 0) {
            m->aim     = g_cur->ab.dashFrames;
            m->aimDir  = self->up ? -1 : self->down ? 1 : 0;
            m->aimLeft = left;
            Show(self, AimAnim(m->aimDir), true, true);
        }
        else if (g_hammer && CycleMove() == 0) {
            HammerStart(self, m);
        }
        else if (GuestJump(self)) {
            // (ManiaGuest.h: the Rocket Burst)
        }
        else if (BatchJump(self)) {
            // (ManiaBatch.h: Rocket Ride, Ear Copter, Spirit Flight, Extreme Gear, Puddle Slide, Phase Warp)
        }
        return true;
    }
    return false;
}

// After the air state: the moves' frames
static void BatchAirGravity(EntityPlayer *p); // (ManiaBatch.h: Honey's floaty spin)

static bool32 Hook_StateAir(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!IsExtra(self))
        return false;
    BatchAirGravity(self); // (only the frames the air state really pulled her down)
    MoveState *m = StateOf(self);
    if (!m)
        return false;
    const Abilities *ab = &g_cur->ab;
    AmyAir(self); // (Amy's Hammer Jump: ManiaAmy.h)

    if (m->hammer && self->state == Player_State_MightyHammerDrop_)
        return false; // (the Hammer Drop just started: the game's drop state from next frame)
    m->hammer = 0;    // (an object sent him up out of the drop after its own frame: over)
    if (self->onGround || self->state != Player_State_Air_) { // landed (or an object took him) this frame
        EndMoves(self, m);
        return false;
    }
    bool32 attackShown = self->animator.animationID == ANI_JUMP && Showing(self, g_animAttack);

    // water_swim: underwater, a jump press in mid-air (in the jump ball or a stroke) is a stroke: up at swimStroke at
    // least (a faster rise is kept; letting go of jump doesn't cut it short), one per swimDelay frames at most
    if (g_swim) {
        if (m->swimDelay > 0)
            m->swimDelay--;
        bool32 inJump = self->animator.animationID == ANI_JUMP && self->aniFrames == g_extraFrames && !attackShown;
        if (self->underwater && self->jumpPress && (inJump || Showing(self, g_animSwim)) && m->swimDelay == 0) {
            m->swimDelay = ab->swimDelay;
            if (self->velocity.y > -ab->swimStroke)
                self->velocity.y = -ab->swimStroke;
            self->applyJumpCap = false;
            m->umbrella        = 2; // (no parasol this jump: underwater it's strokes)
            Show(self, g_animSwim, false, true);
        }
    }

    // jet_dash, then hover
    if (m->dash > 0) {
        if (!attackShown) {
            m->dash = m->hover = 0; // a spring, a hit, a bumper... set another animation: the dash is over
        }
        else {
            int32 speed = self->velocity.x < 0 ? -self->velocity.x : self->velocity.x;
            if (speed < ab->dashSpeed)
                speed = ab->dashSpeed;
            self->velocity.x = (self->direction & FLIP_X) ? -speed : speed;
            self->velocity.y = 0;
            if (--m->dash == 0) {
                BackToJump(self);
                m->hover = g_hover ? 1 : 0;
            }
        }
    }
    else if (m->hover > 0) {
        if (m->hover > 1 && !Showing(self, g_animHover)) {
            m->hover = 0; // something else took over the animation
        }
        else if (self->jumpHold && m->hover <= ab->hoverFrames) {
            self->velocity.y = ab->hoverSink;
            Show(self, g_animHover, false, false);
            m->hover++;
        }
        else {
            if (m->hover > 1)
                BackToJump(self);
            m->hover = 0;
        }
    }

    // double_jump: the attack pose until the fall starts
    if (m->dbl) {
        if (!attackShown) {
            m->dbl = 0; // (a spring, a hit...)
        }
        else if (self->velocity.y >= 0) {
            m->dbl = 0;
            BackToJump(self);
        }
    }

    // screw_kick by jump (Mecha Sonic's Spike Ball, Sally's Flying Kick Dive, Emerl's Dive): 45 degrees down and forward
    // at kickX / kickY, the direction locked, attacking, until he lands (no bounce: the game lands him from the jump
    // ball). A badnik or monitor bouncing him (rising now), a spring or a hit ends it. (Not on its first frame: a jump
    // press comes while the jump is still rising, so the kick's speed has to be set before that check can mean anything.)
    if (m->kick) {
        if (!attackShown) {
            m->kick = 0;
        }
        else if (m->kick > 1 && self->velocity.y <= 0x10000) {
            m->kick = 0;
            BackToJump(self);
        }
        else {
            self->direction  = m->kickLeft ? FLIP_X : FLIP_NONE;
            self->velocity.x = m->kickLeft ? -ab->kickX : ab->kickX;
            self->velocity.y = ab->kickY;
            m->kick          = 2; // (started: from now on, rising ends it)
        }
    }

    // chaos_control (Shadow): a flash held still (chaosFreeze frames), a quick warp forward (chaosWarp frames at
    // chaosSpeed), then a hop (chaosPop up), in the attack pose until the hop starts falling
    if (m->chaos > 0) {
        if (!attackShown) {
            m->chaos = 0;
        }
        else {
            int32 speed      = m->chaos > ab->chaosWarp ? 0 : ab->chaosSpeed;
            self->velocity.x = (self->direction & FLIP_X) ? -speed : speed;
            self->velocity.y = 0;
            if (--m->chaos == 0) {
                m->chaos         = -1;
                self->velocity.y = -ab->chaosPop;
            }
            if (speed > 0 && RSDK.GetEntitySlot(self) == SLOT_PLAYER1) // (the warp: a trail of afterimages behind him; ManiaGhost.h)
                afterImage_Record(self);
        }
    }
    else if (m->chaos < 0) {
        if (!attackShown || self->velocity.y >= 0) {
            m->chaos = 0;
            if (attackShown)
                BackToJump(self);
        }
    }

    // aim_dash (Blaze's Burst Dash, Vector's Shoulder Dash): straight at dashSpeed (or his own if faster), or with up
    // held as it starts upX / upY (45 degrees, Vector's straight up), with down diagX / diagY; dashFrames, an attack
    if (m->aim > 0) {
        int32 anim = AimAnim(m->aimDir);
        if (self->animator.animationID != ANI_JUMP || !Showing(self, anim)) {
            m->aim = 0;
        }
        else {
            int32 dir       = m->aimLeft ? -1 : 1;
            self->direction = m->aimLeft ? FLIP_X : FLIP_NONE;
            if (m->aimDir == 0) {
                int32 speed = self->velocity.x < 0 ? -self->velocity.x : self->velocity.x;
                if (speed < ab->dashSpeed)
                    speed = ab->dashSpeed;
                self->velocity.x = dir * speed;
                self->velocity.y = 0;
            }
            else if (m->aimDir < 0) {
                self->velocity.x = dir * ab->upX;
                self->velocity.y = -ab->upY;
            }
            else {
                self->velocity.x = dir * ab->diagX;
                self->velocity.y = ab->diagY;
            }
            if (--m->aim == 0)
                BackToJump(self);
        }
    }

    // umbrella: open while jump is held (and floatFrames not used up)
    if (m->umbrella == 1) {
        int32 anim = UmbrellaAnim();
        if (m->floated > 0 && !Showing(self, anim)) {
            m->umbrella = 2; // something else took over the animation
        }
        else if (self->jumpHold && (ab->floatFrames == 0 || m->floated < ab->floatFrames)) {
            m->floated++;
            if (self->velocity.y > ab->umbrellaSink)
                self->velocity.y = ab->umbrellaSink;
            Show(self, anim, ab->umbrellaAttack, false);
        }
        else {
            m->umbrella = 2;
            if (m->floated > 0)
                BackToJump(self);
        }
    }

    // ability_cycle: the attack moves share the attack animation; its frame is the active move's place in the cycle
    if (ab->cycleCount > 0 && (m->dash > 0 || m->dbl || m->kick) && Showing(self, g_animAttack)) {
        int32 count = self->animator.frameCount;
        self->animator.frameID = count > 0 ? (g_copy % ab->cycleCount) % count : 0;
        self->animator.timer   = 0;
    }
    return false;
}

static void SlamShots(EntityPlayer *p);

// The Hammer Drop's own state (Player_State_MightyHammerDrop), before it: landed (the game bounces him in the ball: the
// slam's shockwaves go out from where he landed); or a badnik (updating after him) bounced him with Sonic's rule,
// -(speed + 2 gravity): Mighty plows on through, 1 px per frame slower (Player_CheckBadnikBreak's Hammer Drop case)
static bool32 Hook_HammerBefore(bool32 skipped)
{
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    MoveState *m       = IsExtra(self) ? StateOf(self) : NULL;
    if (skipped || !m || m->hammer != 1)
        return false;
    if (self->onGround) {
        m->hammer = 2;
        if (RSDK.GetEntitySlot(self) == SLOT_PLAYER1)
            SlamShots(self);
    }
    else if (self->velocity.y < 0 && self->velocity.y == -(m->hammerVY + 2 * self->gravityStrength)) {
        self->velocity.y = m->hammerVY - 0x10000;
    }
    return false;
}

// ... after it: still dropping (the attack pose kept, its speed noted), or over (landed: Mighty's jumpAbilityState 3
// would be Sonic's drop dash charging, so none; a spring or a bounce: the ball)
static bool32 Hook_HammerAfter(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    MoveState *m       = IsExtra(self) ? StateOf(self) : NULL;
    if (!m || !m->hammer)
        return false;
    if (self->state == Player_State_MightyHammerDrop_ && m->hammer == 1) {
        m->hammerVY = self->velocity.y;
        Show(self, g_animAttack, true, false);
        return false;
    }
    if (m->hammer == 2)
        self->jumpAbilityState = 0;
    m->hammer = 0;
    if (Showing(self, g_animAttack))
        BackToJump(self);
    return false;
}

// ------------------------------------------------------------------------------------------------ shots
static int32 HasAnim(int32 anim);
// An extra's projectile (the package's "shot" / "shot2" and its Shot.bin), the S3&K DLL's namespace shots ported:
//   - NoSwapShot, an object of the mod's own (the mod's Data/Game/Game.xml puts it in every stage's object list): its
//     motion (ShotUpdate: straight / aimed, bounce, drop, dip, boomerang, homing), terrain and lifetime; drawn with the
//     package's Shot.bin (animation 0, the second shot's 1), mirrored when it flies left.
//   - Y (ShotFrame, after every entity's update): throws one (down + Y: the second shot). In the air Y goes to the game
//     first: if that made him Super this frame, no throw (Origins' rule). The throw pose (the shot animation's last
//     frame, ability slot 43; in the air slot 44 when it has one), cooldown, max_alive, as in S3&K.
//   - Hits (HitUpdate): every object that checks players with the game's attack rules (ManiaShot.h HIT_CLASSES:
//     badniks, item boxes, bosses, a few breakables) has its Update wrapped (Mod.RegisterObject by name; the game's own
//     Update runs through Mod.Super). When a shot is within reach of one, player 1 STANDS IN for the shot during that
//     object's update (StandIn): his entity is moved onto the shot, given its hitbox (the shot's animator: each frame's
//     box 0) and the attack (the jump animation and an invincibility timer, so nothing can hurt him), the object's own
//     update runs, and he is put back exactly as he was, keeping only what the game gave him (score, rings, lives,
//     shield...). So the game's own code decides everything: Player_CheckBadnikBreak (score chain, animal, explosion),
//     ItemBox_Break (the item goes to him), Player_CheckBossHit and each boss's own hit handling. A hit shows as the
//     stand-in bounced (every one of those sets the attacker's speed) or the object gone; the shot then ends ("pierce":
//     flies on, never hitting the same object twice).
#define SHOT_OUT_MAX  (8)
#define SHOT_MAGIC    (0x4E53484Fu)  // our shots (the entity's magic)
#define STANDIN_VY    (0x100)        // the stand-in's speed: falling a little (an item box takes a rising jump as a bump)
#define STANDIN_INV   (0x7FF0)       // ... its invincibility timer (an invincibility monitor setting another one is kept)
#define REACH_BADNIK  (64)           // px from an object's position to a shot's for a stand-in
#define REACH_BOSS    (128)
#define CLASS_MAX     (0x400)

typedef struct {
    RSDK_OBJECT
} ObjectNoSwapShot;

typedef struct {
    RSDK_ENTITY
    Animator animator;
    uint32 magic;
    int32 timer;      // its age in frames
    int32 phase;      // boomerang / homing: 0 out, 1 coming back
    int32 which;      // 1 the shot, 2 the second shot
    int32 hits;       // what it has hit
    int32 idle;       // homing: frames in a row without a target
    int32 lastHit[4]; // "pierce": the slots it has hit (+1; 0 none)
} EntityNoSwapShot;

static ObjectNoSwapShot *NoSwapShot = NULL;
static void (*Player_State_Hurt_)(void);
static void (*Player_State_Death_)(void);
static void (*Player_State_Drown_)(void);
static void (*Player_Input_P1_)(void);

static bool32 g_shotOn         = false;  // the extra playing has a shot and its art (this stage)
static uint16 g_shotFrames     = 0xFFFF; // its Shot.bin
static uint16 g_shotSfx[2]     = { 0xFFFF, 0xFFFF };
static uint16 g_puffSfx        = 0xFFFF;
static int32 g_animShot        = -1; // its throw pose (ability slot 43), in the air (44), or -1
static int32 g_animShotAir     = -1;
static EntityNoSwapShot *g_out[SHOT_OUT_MAX];
static int32 g_shotCooldown    = 0;
static int32 g_shotNext        = 0; // a cycle shot: the art frame the next throw takes
static int32 g_charge          = 0; // a charge shot ("input" "charge": Omega's Flame Blast): frames Y has been held
static bool32 SinkBlocksShot(EntityPlayer *p); // (ManiaMore.h)
static bool32 AnchorStrike(Entity *self, int32 kind, EntityPlayer *p);
static bool32 PsychoShotDraw(EntityNoSwapShot *shot); // (ManiaPsycho.h)
static bool32 PsychoWave(bool32 press);
static int32 g_aimK            = 0; // the last aimed throw's aim (0 level, 1 forward-up, 2 up, 3 forward-down, 4 down)
static bool32 g_high           = false; // the last throw was an up throw
static uint32 g_frame          = 0;
static bool32 g_hitWrapped     = false; // the hit classes' updates are wrapped (at link)
static bool32 g_hitsOn         = false; // ... and the extra playing hits with them this stage (a shot or the melee)
static bool32 g_meleeOn          = false; // the extra playing has the melee (Y's pose move, no shot on Y alone) this stage
static uint8 g_hitKind[CLASS_MAX];      // this stage's class IDs -> HIT_*
static struct {
    int32 left; // frames left
    bool32 air, high;
    int32 aim;
} g_pose;
// A homing shot's search (HitUpdate): every hit class on screen reports its position; the nearest to the shot is kept,
// and the shot reads and resets it in its own update
static struct {
    bool32 on;
    int32 fromX, fromY;
    int64 best; // -1: none
    int32 x, y;
} g_seek;

static bool32 IsShot(void *entity)
{
    Entity *e = (Entity *)entity;
    return NoSwapShot && e && NoSwapShot->classID && e->classID == NoSwapShot->classID && ((EntityNoSwapShot *)e)->magic == SHOT_MAGIC;
}

static const ShotData *CrossSwapOf(int32 which);              // (ManiaCross.h: John's sub-weapons, which >= 16)
static const ShotData *CrossSwapShot(const ShotData *shot);
static int32 CrossSwapAnim(void);
static int32 CrossSwapWhich(void);
static uint16 CrossSwapSfx(uint16 sfx);
static bool32 CrossBurnUpdate(EntityNoSwapShot *e, const ShotData *s);
static bool32 CrossWhipUp(EntityPlayer *p);
static const ShotData *ShotOf(const EntityNoSwapShot *s) { return s->which == 2 ? &g_cur->shot2 : s->which >= 16 ? CrossSwapOf(s->which) : &g_cur->shot; }

// Our shots out now (which: 0 all, 1 the first shot's, 2 the second's); the list drops any the engine has cleared
static int32 OutCount(int32 which)
{
    int32 n = 0;
    for (int32 k = 0; k < SHOT_OUT_MAX; ++k) {
        if (g_out[k] && !IsShot(g_out[k]))
            g_out[k] = NULL;
        n += g_out[k] && (which == 0 || g_out[k]->which == which);
    }
    return n;
}

static bool32 Hurt(EntityPlayer *p) { return p->state == Player_State_Hurt_ || p->state == Player_State_Death_ || p->state == Player_State_Drown_; }

static int32 Clamp(int32 v, int32 lo, int32 hi) { return v < lo ? lo : v > hi ? hi : v; }
static int32 Abs(int32 v) { return v < 0 ? -v : v; }

static void ShotGone(EntityNoSwapShot *s, const char *why)
{
    static int32 logs = 0;
    if (logs++ < 40)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: gone at %d,%d after %d frames (%s)", s->position.x >> 16, s->position.y >> 16, s->timer, why);
    if (g_cur && ShotOf(s)->motion == SHOT_HOMING) { // (a homing shot's cooldown starts when it's gone: Cheese back)
        g_seek.on     = false;
        g_shotCooldown = ShotOf(s)->cooldown;
    }
    for (int32 k = 0; k < SHOT_OUT_MAX; ++k)
        if (g_out[k] == s)
            g_out[k] = NULL;
    RSDK.ResetEntity(s, TYPE_DEFAULTOBJECT, NULL);
}

// A dropped shot's landing puff (motion "drop"): the game's badnik explosion (Explosion type 1, only drawn) and sound
static void Puff(EntityNoSwapShot *s)
{
    uint16 cls = RSDK.FindObject("Explosion");
    if (!cls)
        return;
    Entity *x = RSDK.CreateEntity(cls, INT_TO_VOID(1), s->position.x, s->position.y);
    if (x && x->classID == cls)
        x->drawGroup = s->drawGroup;
    if (g_puffSfx != 0xFFFF)
        RSDK.PlaySfx(g_puffSfx, false, 255);
}

// Back toward player 1's hand (s->y below his centre), plus his own velocity; caught within catchRadius
static bool32 ComeBack(EntityNoSwapShot *e, const ShotData *s, EntityPlayer *p, int32 div)
{
    int32 gapX = p->position.x - e->position.x, gapY = p->position.y + (s->y << 16) - e->position.y;
    e->velocity.x += Clamp(Clamp(gapX / div, -s->returnSpeed, s->returnSpeed) - e->velocity.x, -s->returnAccel, s->returnAccel);
    e->velocity.y += Clamp(Clamp(gapY / div, -s->returnSpeed, s->returnSpeed) - e->velocity.y, -s->returnAccel, s->returnAccel);
    e->position.x += e->velocity.x + p->velocity.x;
    e->position.y += e->velocity.y + p->velocity.y;
    int32 at = s->catchRadius << 16;
    return Abs(p->position.x - e->position.x) < at && Abs(p->position.y + (s->y << 16) - e->position.y) < at;
}

static void BoomerangUpdate(EntityNoSwapShot *e, const ShotData *s, EntityPlayer *p)
{
    int32 dir = (e->direction & FLIP_X) ? -1 : 1;
    if (e->phase == 0) { // out: his own forward speed along, its own slowing down
        int32 along = dir * p->velocity.x;
        e->position.x += e->velocity.x + dir * (along > 0 ? along : 0);
        e->velocity.x -= dir * s->decel;
        if (dir * e->velocity.x <= 0) {
            e->velocity.x = 0;
            e->phase      = 1;
        }
    }
    else if (ComeBack(e, s, p, 8)) {
        ShotGone(e, "caught");
        return;
    }
    Vector2 range = { 0x200000, 0x200000 };
    if (!RSDK.CheckOnScreen(e, &range)) {
        ShotGone(e, "offscreen");
        return;
    }
    RSDK.ProcessAnimation(&e->animator);
}

static void HomingUpdate(EntityNoSwapShot *e, const ShotData *s, EntityPlayer *p)
{
    if (e->phase == 0 && e->hits > 0)
        e->phase = 1; // (its first hit: back to him)
    if (e->phase == 0) {
        if (g_seek.best >= 0) { // a target: steer at it
            e->idle = 0;
            e->velocity.x += Clamp(Clamp((g_seek.x - e->position.x) / 4, -s->seekSpeed, s->seekSpeed) - e->velocity.x, -s->seekAccel, s->seekAccel);
            e->velocity.y += Clamp(Clamp((g_seek.y - e->position.y) / 4, -s->seekSpeed, s->seekSpeed) - e->velocity.y, -s->seekAccel, s->seekAccel);
            e->position.x += e->velocity.x;
            e->position.y += e->velocity.y;
        }
        else { // none: straight on, his forward speed along
            int32 along = (e->velocity.x > 0 && p->velocity.x > 0) || (e->velocity.x < 0 && p->velocity.x < 0) ? p->velocity.x : 0;
            e->position.x += e->velocity.x + along;
            e->position.y += e->velocity.y;
            if (++e->idle >= s->seekFrames)
                e->phase = 1;
        }
    }
    else if (ComeBack(e, s, p, 8)) {
        ShotGone(e, "caught");
        return;
    }
    g_seek.on    = e->phase == 0;
    g_seek.best  = -1;
    g_seek.fromX = e->position.x;
    g_seek.fromY = e->position.y;
    Vector2 range = { 0x200000, 0x200000 };
    if (!RSDK.CheckOnScreen(e, &range)) {
        ShotGone(e, "offscreen");
        return;
    }
    if (e->velocity.x > 0x4000)
        e->direction = FLIP_NONE;
    else if (e->velocity.x < -0x4000)
        e->direction = FLIP_X;
    RSDK.ProcessAnimation(&e->animator);
}

static bool32 ShotBreakWalls(EntityNoSwapShot *e, const ShotData *s);

static void ShotUpdate(EntityNoSwapShot *e)
{
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!g_active || !g_cur || !g_shotOn || ShotOf(e)->motion == SHOT_NONE || !p) {
        ShotGone(e, "no shot now");
        return;
    }
    const ShotData *s = ShotOf(e);
    if (++e->timer > s->lifetime) {
        ShotGone(e, "lifetime");
        return;
    }
    if (CrossBurnUpdate(e, s)) // (John's Holy Water: ManiaCross.h)
        return;
    if (s->motion == SHOT_BOOMERANG) {
        BoomerangUpdate(e, s, p);
        return;
    }
    if (s->motion == SHOT_HOMING) {
        HomingUpdate(e, s, p);
        return;
    }
    uint16 layers = e->collisionLayers;
    uint8 plane   = e->collisionPlane;
    int32 r       = s->radius << 16;
    // (shot_breaks_walls: a breakable wall where it's going breaks before its tiles can stop it; "ManiaWalls.h")
    if (s->terrain && ShotBreakWalls(e, s) && !s->pierce) {
        ShotGone(e, "broke a wall");
        return;
    }
    if (s->motion == SHOT_BOUNCE || s->motion == SHOT_DROP || s->motion == SHOT_DIP) { // (a dip's gravity pulls it up)
        e->velocity.y += s->gravity;
        if (e->velocity.y > s->maxFall)
            e->velocity.y = s->maxFall;
    }
    // ahead: a wall (solid from the side at its leading edge, above its middle, so a floor or a slope isn't one)
    e->position.x += e->velocity.x;
    int32 ahead = e->velocity.x < 0 ? -r - 0x10000 : r + 0x10000;
    if (s->terrain && e->velocity.x
        && (RSDK.ObjectTileCollision(e, layers, CMODE_LWALL, plane, ahead, -r / 2, false)
            || RSDK.ObjectTileCollision(e, layers, CMODE_RWALL, plane, ahead, -r / 2, false))) {
        ShotGone(e, "wall");
        return;
    }
    e->position.y += e->velocity.y;
    if (!s->terrain) {
    }
    else if (s->motion == SHOT_GROUND) { // along the floor, gripped to it (slopes too); none within 14 px: a ledge's end
        if (!RSDK.ObjectTileGrip(e, layers, CMODE_FLOOR, plane, 0, r, 14)) {
            ShotGone(e, "ledge");
            return;
        }
    }
    else if (s->motion == SHOT_BOUNCE) {
        if (e->velocity.y >= 0 && RSDK.ObjectTileCollision(e, layers, CMODE_FLOOR, plane, 0, r, true))
            e->velocity.y = s->bounce;
        else if (e->velocity.y < 0 && RSDK.ObjectTileCollision(e, layers, CMODE_ROOF, plane, 0, -r, true))
            e->velocity.y = 0;
    }
    else if (e->velocity.y > 0) { // (straight aimed down, a drop: a floor below its leading edge ends it)
        if (RSDK.ObjectTileCollision(e, layers, CMODE_FLOOR, plane, 0, r + 0x10000, false)) {
            if (s->motion == SHOT_DROP)
                Puff(e);
            ShotGone(e, "floor");
            return;
        }
    }
    else if (e->velocity.y < 0) {
        if (RSDK.ObjectTileCollision(e, layers, CMODE_ROOF, plane, 0, -r - 0x10000, false)) {
            ShotGone(e, "ceiling");
            return;
        }
    }
    Vector2 range = { 0x200000, 0x200000 };
    if (!RSDK.CheckOnScreen(e, &range)) {
        ShotGone(e, "offscreen");
        return;
    }
    if (!s->cycle && !s->aimFrames) // (a cycle or aim_frames shot keeps the frame its throw picked)
        RSDK.ProcessAnimation(&e->animator);
}

static void Shot_Update(void)
{
    EntityNoSwapShot *self = (EntityNoSwapShot *)SceneInfo->entity;
    if (!IsShot(self)) {
        RSDK.ResetEntity(self, TYPE_DEFAULTOBJECT, NULL); // (not one of ours: a stray)
        return;
    }
    ShotUpdate(self);
}

static void Shot_Draw(void)
{
    EntityNoSwapShot *self = (EntityNoSwapShot *)SceneInfo->entity;
    if (IsShot(self) && g_shotOn && !PsychoShotDraw(self)) // (Silver's thrown badnik draws as itself)
        RSDK.DrawSprite(&self->animator, NULL, false);
}

static void Shot_Create(void *data)
{
    (void)data;
    EntityNoSwapShot *self = (EntityNoSwapShot *)SceneInfo->entity;
    self->active           = ACTIVE_NORMAL;
    self->visible          = true;
    self->drawFX           = FX_FLIP;
}

// Throw one (false: can't now). An aimed shot goes where the d-pad points as Y is pressed: x from left / right, y from
// up (and down in the air); nothing held: forward; holding a side turns him to it first when `turn`. Diagonals: the
// same speed overall. which 2: the second shot. forceDir: a both-ways pair's own direction.
static bool32 Throw(EntityPlayer *p, bool32 turn, int32 which, int32 forceDir)
{
    const ShotData *s = which == 2 ? &g_cur->shot2 : CrossSwapShot(&g_cur->shot); // (John's sub-weapon: ManiaCross.h)
    if (!g_shotOn || s->motion == SHOT_NONE || OutCount(g_cur->shot2.motion != SHOT_NONE ? which : 0) >= s->maxAlive)
        return false;
    if (s->rings > 0 && p->rings < s->rings)
        return false;
    int32 slot = -1;
    for (int32 k = 0; k < SHOT_OUT_MAX && slot < 0; ++k)
        if (!g_out[k])
            slot = k;
    if (slot < 0)
        return false;
    g_high      = false;
    bool32 left = (p->direction & FLIP_X) != 0;
    int32 dir   = left ? -1 : 1;
    if (forceDir) {
        dir  = forceDir;
        left = dir < 0;
    }
    int32 ax = dir, ay = 0;
    if (s->aim) {
        ax = p->right ? 1 : p->left ? -1 : 0;
        ay = p->up ? -1 : (p->down && !p->onGround && s->aimDown) ? 1 : 0;
        if (!ax && !ay)
            ax = dir;
        if (ax && turn) {
            p->direction = ax < 0 ? FLIP_X : FLIP_NONE;
            left         = ax < 0;
            dir          = ax;
        }
    }
    g_aimK        = ay == 0 ? 0 : (ay < 0 ? 1 : 3) + (ax == 0 ? 1 : 0);
    bool32 ground = s->hasGround && p->onGround && !s->aim;
    int32 sx = ground ? s->groundX : s->x, sy = ground ? s->groundY : s->y;
    int32 x = s->aim ? p->position.x + ax * (s->x << 16) : p->position.x + dir * (sx << 16);
    int32 y = s->aim ? p->position.y + (s->y << 16) + ay * (s->x << 16) : p->position.y + (sy << 16);
    EntityNoSwapShot *e = (EntityNoSwapShot *)RSDK.CreateEntity(NoSwapShot->classID, NULL, x, y);
    if (!e || e->classID != NoSwapShot->classID)
        return false;
    RSDK.SetSpriteAnimation(g_shotFrames, which == 2 ? 1 : CrossSwapAnim(), &e->animator, true, 0);
    if (s->rings > 0)
        p->rings -= s->rings;
    if (s->aim) {
        int32 axis  = ax && ay ? (int32)((int64)s->speed * 46341 >> 16) : s->speed; // (a diagonal: speed / sqrt 2 per axis)
        int32 along = ax * p->velocity.x;
        e->velocity.x = ax * (axis + (along > 0 ? along : 0));
        e->velocity.y = ay * axis;
    }
    else if (s->motion == SHOT_BOOMERANG || s->motion == SHOT_HOMING) { // (its own speed: his is added live)
        e->velocity.x = dir * s->speed;
        e->velocity.y = 0;
        if (s->motion == SHOT_HOMING) {
            e->idle      = 0;
            g_seek.on    = true;
            g_seek.best  = -1;
            g_seek.fromX = e->position.x;
            g_seek.fromY = e->position.y;
        }
    }
    else {
        int32 along   = dir * p->velocity.x;
        int32 forward = forceDir || !s->carry ? 0 : (along > 0 ? along : 0);
        g_high        = s->hasUp && p->up; // (up held: the up throw's own numbers)
        e->velocity.x = dir * ((g_high ? s->upSpeed : ground ? s->groundSpeed : s->speed) + forward);
        e->velocity.y = g_high ? s->upStartVY : ground ? s->groundStartVY : s->startVY;
    }
    if (s->cycle) {
        int32 count = e->animator.frameCount > 0 ? e->animator.frameCount : 1;
        g_shotNext %= count;
        e->animator.frameID = g_shotNext++;
        e->animator.timer   = 0;
    }
    if (s->aim && s->aimFrames) { // its aim's frame, held
        e->animator.frameID = e->animator.frameCount > g_aimK ? g_aimK : 0;
        e->animator.timer   = 0;
        if (ax)
            left = ax < 0;
    }
    e->magic           = SHOT_MAGIC;
    e->which           = which == 2 ? 2 : CrossSwapWhich();
    e->timer           = 0;
    e->phase           = 0;
    e->hits            = 0;
    e->direction       = left ? FLIP_X : FLIP_NONE;
    e->drawFX          = FX_FLIP;
    e->active          = ACTIVE_NORMAL;
    e->visible         = true;
    e->drawGroup       = p->drawGroup;
    e->collisionLayers = p->collisionLayers;
    e->collisionPlane  = p->collisionPlane;
    e->updateRange.x   = 0x800000;
    e->updateRange.y   = 0x800000;
    memset(e->lastHit, 0, sizeof(e->lastHit));
    g_out[slot]    = e;
    g_shotCooldown = s->cooldown;
    uint16 sfx = which == 2 ? g_shotSfx[1] : CrossSwapSfx(g_shotSfx[0]);
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
    static int32 logs = 0;
    if (logs++ < 40)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: thrown (slot %d, %d out) at %d,%d, velocity %d,%d%s", RSDK.GetEntitySlot(e), OutCount(0),
                      e->position.x >> 16, e->position.y >> 16, e->velocity.x, e->velocity.y, g_high ? ", up throw" : "");
    return true;
}

// Y's throw: one, or with "both_ways" a pair, forward and back
static bool32 ThrowY(EntityPlayer *p, bool32 turn)
{
    if (!g_cur->shot.bothWays)
        return Throw(p, turn, 1, 0);
    int32 dir = (p->direction & FLIP_X) ? -1 : 1;
    if (!Throw(p, false, 1, dir))
        return false;
    Throw(p, false, 1, -dir);
    return true;
}

// Player 1's frame (after every entity's update): Y throws; the pose shows the shot animation's last frame (its up
// throw's, or its aim's with "aim_pose") for `pose` frames, standing still or in the air (in the air as an attack,
// reported to the game as the jump, as the other air moves; standing as itself)
static void ShotFrame(EntityPlayer *p, bool32 transformed)
{
    const ShotData *s = &g_cur->shot;
    bool32 air        = !p->onGround;
    if (g_shotCooldown > 0)
        g_shotCooldown--;
    bool32 standing    = !air && Abs(p->groundVel) < 0x10000;
    InputState *key    = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    bool32 control     = key && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled && !transformed && !Hurt(p);
    bool32 press       = control && !s->onSlam && !s->onGrab && (s->autofire ? key->down : key->press) && (!s->downOnly || p->down) && (!s->upOnly || p->up)
                         && !(s->upOnly && CrossWhipUp(p)); // (up and a side in the air: John's up-forward whip)
    if (SinkBlocksShot(p)) // (down + Y on the ground: Mephiles' Shadow Sink; nothing while he's sunk)
        press = false;
    if (g_cur->shot2.motion != SHOT_NONE && g_cur->shot2.onCharge) {
        // a charge shot (the S3&K DLL's): Y held charges ("charge_wait": not full while the cooldown runs); letting go of
        // a full charge throws it with the throw pose; a hit, or no control, loses the charge. Y's press still throws the
        // first shot as usual (Omega's small flame)
        const ShotData *s2 = &g_cur->shot2;
        bool32 fire        = false;
        if (!control || Hurt(p)) {
            g_charge = 0;
        }
        else if (key->down) {
            g_charge = g_charge < 0x7FFF ? g_charge + 1 : g_charge;
            if (s2->chargeWait && g_shotCooldown > 0 && g_charge >= s2->chargeFull)
                g_charge = s2->chargeFull - 1;
        }
        else {
            fire     = g_charge >= s2->chargeFull;
            g_charge = 0;
        }
        if (fire && Throw(p, air || standing, 2, 0) && s2->pose > 0 && (air || standing)) {
            g_pose.left = s2->pose;
            g_pose.air  = air;
            g_pose.high = false;
            g_pose.aim  = 0;
        }
    }
    else if (g_cur->shot2.motion != SHOT_NONE && p->down) { // down + Y: the second shot's (no pose), the cooldown shared
        if (g_shotCooldown == 0 && press)
            Throw(p, air || standing, 2, 0);
        press = false;
    }
    if (g_shotCooldown == 0 && press && ThrowY(p, air || standing) && s->pose > 0 && (air || standing)) {
        g_pose.left = s->pose;
        g_pose.air  = air;
        g_pose.high = g_high;
        g_pose.aim  = g_aimK;
    }
    if (g_pose.left <= 0)
        return;
    int32 anim  = air && g_animShotAir >= 0 ? g_animShotAir : g_animShot;
    bool32 keep = anim >= 0 && !Hurt(p) && (air ? g_pose.air && p->animator.animationID == ANI_JUMP : !g_pose.air && standing);
    if (keep) {
        Show(p, anim, air, g_pose.left == s->pose);
        int32 count = p->animator.frameCount;
        if (count > 0)
            p->animator.frameID = s->aimPose ? Clamp(g_pose.aim, 0, count - 1) : g_pose.high && s->upPose >= 0 && s->upPose < count ? s->upPose : count - 1;
        p->animator.timer = 0;
        p->animator.speed = 0;
    }
    if (!keep || --g_pose.left == 0) {
        // over, or cut short (landing, a hit...): if the pose still shows, the jump ball (it was reported as the jump, so
        // the game may have kept it: rolling on landing) or standing; anything else the game already put up stays
        bool32 showing = Showing(p, g_animShot) || Showing(p, g_animShotAir);
        g_pose.left    = 0;
        if (showing)
            RSDK.SetSpriteAnimation(p->aniFrames, air || p->animator.animationID == ANI_JUMP ? ANI_JUMP : ANI_IDLE, &p->animator, true, 0);
    }
}

// The Hammer Drop landed (Hook_HammerBefore): a slam shot ("input" "slam": Bark's shockwaves) goes out, one each way
static void SlamShots(EntityPlayer *p)
{
    if (!g_shotOn || !g_cur || !g_cur->shot.onSlam)
        return;
    bool32 a = Throw(p, false, 1, -1), b = Throw(p, false, 1, 1);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "slam: shockwaves %s / %s", a ? "left" : "-", b ? "right" : "-");
}

// A shot that can hit `target` now (within reach, not spent, not coming back, not already through it), or NULL
static EntityNoSwapShot *ShotInReach(Entity *target, int32 reach)
{
    int32 slot = RSDK.GetEntitySlot(target) + 1;
    for (int32 k = 0; k < SHOT_OUT_MAX; ++k) {
        EntityNoSwapShot *e = g_out[k];
        if (!e || !IsShot(e))
            continue;
        const ShotData *s = ShotOf(e);
        if ((e->hits > 0 && !s->pierce && s->motion != SHOT_HOMING) || (s->motion == SHOT_HOMING && (e->phase != 0 || e->hits > 0)))
            continue;
        if (e->lastHit[0] == slot || e->lastHit[1] == slot || e->lastHit[2] == slot || e->lastHit[3] == slot)
            continue;
        if (Abs(e->position.x - target->position.x) <= (reach << 16) && Abs(e->position.y - target->position.y) <= (reach << 16))
            return e;
    }
    return NULL;
}

// Player 1 stands in for a hit (a shot, the melee's reach, a nuke) during the target's own update (see the section's
// notes): at `pos`, with `anim`'s frame box as his hitbox; true: it hit
static bool32 StandInAt(Entity *target, Vector2 pos, const Animator *anim, uint8 direction, uint8 plane, EntityPlayer *p)
{
    uint16 cls = target->classID;
    EntityPlayer saved;
    memcpy(&saved, p, sizeof(saved));
    p->position             = pos;
    p->velocity.x           = 0;
    p->velocity.y           = STANDIN_VY;
    p->groundVel            = 0;
    p->onGround             = false;
    p->direction            = direction;
    p->animator             = *anim;
    p->animator.animationID = ANI_JUMP;
    p->invincibleTimer      = STANDIN_INV;
    p->outerbox             = NULL;
    p->innerbox             = NULL;
    p->isGhost              = false;
    p->collisionPlane       = plane;

    Mod.Super(cls, SUPER_UPDATE, NULL);

    bool32 hit = p->velocity.x != 0 || p->velocity.y != STANDIN_VY || target->classID != cls;
    // (what the game gave him while he stood in stays his; the rest is as he was)
    int32 rings = p->rings, ringExtraLife = p->ringExtraLife, shield = p->shield, lives = p->lives, score = p->score;
    int32 score1UP = p->score1UP, hyperRing = p->hyperRing, speedShoes = p->speedShoesTimer, scoreBonus = p->scoreBonus;
    int32 invincible = p->invincibleTimer, drown = p->drownTimer;
    memcpy(p, &saved, sizeof(saved));
    p->rings           = rings;
    p->ringExtraLife   = ringExtraLife;
    p->shield          = shield;
    p->lives           = lives;
    p->score           = score;
    p->score1UP        = score1UP;
    p->hyperRing       = hyperRing;
    p->speedShoesTimer = speedShoes;
    p->scoreBonus      = scoreBonus;
    if (invincible != STANDIN_INV)
        p->invincibleTimer = invincible;
    if (drown != saved.drownTimer)
        p->drownTimer = drown;
    return hit;
}

static bool32 StandIn(Entity *target, EntityNoSwapShot *shot, EntityPlayer *p)
{
    return StandInAt(target, shot->position, &shot->animator, shot->direction, shot->collisionPlane, p);
}

static bool32 StrikeUpdate(Entity *self, int32 kind, EntityPlayer *p);
static bool32 BatchStrike(Entity *self, int32 kind, EntityPlayer *p); // (ManiaBatch.h)
static bool32 BatchHits(void);
static bool32 CrossHits(void); // (ManiaCross.h: Ristar's catch, Headdy's head)
static bool32 AmyStrike(Entity *target, int32 kind, EntityPlayer *p); // (ManiaAmy.h: the hammer's reach)
static bool32 CrossStrike(Entity *self, int32 kind, EntityPlayer *p); // (ManiaCross.h: Ristar's hands, Headdy's head)
static bool32 NinjaStrike(Entity *self, int32 kind, EntityPlayer *p); // (ManiaNinjutsu.h: Joe's Kariu / Mijin blasts)
static bool32 PotsStrike(Entity *self, int32 kind, EntityPlayer *p); // (ManiaPotMagic.h: Gilius' Earthquake)
static bool32 NightsStrike(Entity *self, int32 kind, EntityPlayer *p); // (ManiaNights.h: NiGHTS' Paraloop)
static bool32 NightsHits(void);
static bool32 NightsHasFlight(const char *folder);

static bool32 NoStompBefore(Entity *self, int32 kind, EntityPlayer *p, uint16 *saved); // (ManiaNoStomp.h)
static void NoStompAfter(EntityPlayer *p, bool32 changed, uint16 saved, uint16 shown);
static void HitUpdateInner(void);

// The hit classes' Update (HIT_CLASSES, wrapped at link): no_stomp's view of player 1 around it (ManiaNoStomp.h)
static void HitUpdate(void)
{
    Entity *self    = SceneInfo->entity;
    uint16 cls      = self->classID;
    int32 kind      = g_hitsOn && cls < CLASS_MAX ? g_hitKind[cls] : HIT_NONE;
    EntityPlayer *p = Player ? (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1) : NULL;
    uint16 saved    = 0;
    bool32 changed  = p && NoStompBefore(self, kind, p, &saved);
    uint16 shown    = changed ? p->animator.animationID : 0;
    HitUpdateInner();
    NoStompAfter(p, changed, saved, shown);
}

// ... the game's own, with player 1 standing in for a shot in reach
static void HitUpdateInner(void)
{
    Entity *self = SceneInfo->entity;
    uint16 cls   = self->classID;
    int32 kind   = g_hitsOn && cls < CLASS_MAX ? g_hitKind[cls] : HIT_NONE;
    if (kind != HIT_NONE && CrossStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Headdy's head stood in: ManiaCross.h)
    if (kind != HIT_NONE && NinjaStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Joe's Ninjutsu blast stood in: ManiaNinjutsu.h)
    if (kind != HIT_NONE && PotsStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Gilius' Earthquake stood in: ManiaPotMagic.h)
    if (kind != HIT_NONE && NightsStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (inside NiGHTS' Paraloop: ManiaNights.h)
    if (kind != HIT_NONE && AmyStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Amy's hammer: ManiaAmy.h)
    if (kind != HIT_NONE && BatchStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Max's ear, Honey's spin, Heavy's charge: ManiaBatch.h)
    if (kind != HIT_NONE && AnchorStrike(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (Marine's anchor stood in: the object's update has run)
    if (kind != HIT_NONE && StrikeUpdate(self, kind, (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return; // (the melee or its nuke stood in: the object's update has run)
    if (kind == HIT_NONE || !g_shotOn || !OutCount(0)) {
        Mod.Super(cls, SUPER_UPDATE, NULL);
        return;
    }
    if (g_seek.on) { // (a homing shot seeking: this one is a target if it's on screen)
        Vector2 range = { 0, 0 };
        if (RSDK.CheckOnScreen(self, &range)) {
            int64 dx = (int64)self->position.x - g_seek.fromX, dy = (int64)self->position.y - g_seek.fromY;
            int64 d = (dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy);
            if (g_seek.best < 0 || d < g_seek.best) {
                g_seek.best = d;
                g_seek.x    = self->position.x;
                g_seek.y    = self->position.y;
            }
        }
    }
    int32 reach           = kind == HIT_BOSS ? REACH_BOSS : REACH_BADNIK;
    EntityNoSwapShot *shot = ShotInReach(self, reach);
    EntityPlayer *p       = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!shot || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_ || p->state == Player_State_Drown_) {
        Mod.Super(cls, SUPER_UPDATE, NULL);
        return;
    }
    // Player 1 near it himself: his own turn every other frame (the object checks him then; a shot hits on the others)
    int32 near = (reach + 24) << 16;
    if (Abs(p->position.x - self->position.x) <= near && Abs(p->position.y - self->position.y) <= near && (g_frame & 1)) {
        Mod.Super(cls, SUPER_UPDATE, NULL);
        return;
    }
    int32 slot = RSDK.GetEntitySlot(self);
    if (!StandIn(self, shot, p))
        return;
    static int32 logs = 0;
    if (logs++ < 60)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: hit class %d (slot %d, %s)", cls, slot,
                      kind == HIT_BOSS ? "boss" : kind == HIT_ITEMBOX ? "item box" : "badnik");
    shot->hits++;
    const ShotData *s = ShotOf(shot);
    if (s->motion == SHOT_HOMING)
        shot->phase = 1;
    else if (s->pierce)
        shot->lastHit[(shot->hits - 1) & 3] = slot + 1;
    else
        ShotGone(shot, "hit");
}

static void MeleeStageLoad(void);

// Stage load: the playing extra's shot art and sounds, this stage's hit classes (for its shot or its melee)
static void ShotsStageLoad(void)
{
    g_shotOn = false;
    g_hitsOn = false;
    memset(g_out, 0, sizeof(g_out));
    memset(&g_pose, 0, sizeof(g_pose));
    memset(&g_seek, 0, sizeof(g_seek));
    g_shotCooldown = 0;
    g_charge       = 0;
    memset(g_hitKind, 0, sizeof(g_hitKind));
    MeleeStageLoad(); // (g_meleeOn)
    if (!g_cur || (g_cur->shot.motion == SHOT_NONE && !g_meleeOn && !g_cur->ab.anchorThrow && !BatchHits() && !CrossHits()
                   && !NightsHits() && !g_cur->ab.noStomp)) // (NiGHTS' Paraloop: ManiaNights.h; no_stomp: ManiaNoStomp.h)
        return;
    int32 found = 0;
    for (size_t i = 0; i < HIT_CLASS_COUNT; ++i) {
        uint16 id = RSDK.FindObject(HIT_CLASSES[i].name);
        if (id && id < CLASS_MAX) {
            g_hitKind[id] = HIT_CLASSES[i].kind;
            found++;
        }
    }
    g_animShot    = HasAnim(g_cur->animBase + 2);
    g_animShotAir = g_cur->ab.shotAirFrames > 0 ? HasAnim(g_cur->animBase + 8) : -1;
    g_hitsOn      = g_hitWrapped;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "hits: %d hittable classes here%s", found, g_hitWrapped ? "" : " (NOT wrapped: no hits)");
    if (g_cur->shot.motion == SHOT_NONE)
        return;
    if (!NoSwapShot || !NoSwapShot->classID || !RSDK.FindObject("NoSwapShot")) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "shot: the NoSwapShot object isn't in this stage (Data/Game/Game.xml missing?): no shots");
        return;
    }
    g_shotFrames = RSDK.LoadSpriteAnimation(g_cur->shotFile, SCOPE_STAGE);
    if (!AniFramesOK(g_shotFrames, 0)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "shot: %s is missing or its sheet didn't load: no shots", g_cur->shotFile);
        g_shotFrames = 0xFFFF;
        return;
    }
    g_shotSfx[0] = g_cur->shot.sound[0] ? RSDK.GetSfx(g_cur->shot.sound) : 0xFFFF;
    g_shotSfx[1] = g_cur->shot2.sound[0] ? RSDK.GetSfx(g_cur->shot2.sound) : 0xFFFF;
    g_puffSfx    = RSDK.GetSfx("Global/Destroy.wav");
    g_shotOn     = g_hitWrapped;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: %s, art %s (id %d), pose %d / air %d, sound %s (%d)", g_cur->name, g_cur->shotFile,
                  g_shotFrames, g_animShot, g_animShotAir, g_cur->shot.sound, g_shotSfx[0]);
}

static bool32 LinkMelee(void);

// Link: the shot object and the hit classes' wrapped updates (only when some package has a shot or a melee)
static void LinkShots(void)
{
    bool32 any = false;
    for (int32 i = 0; i < g_extraCount; ++i)
        any |= g_extras[i].shot.motion != SHOT_NONE || g_extras[i].ab.shot || g_extras[i].ab.anchorThrow || g_extras[i].more.batch.earGrapple
               || g_extras[i].more.batch.spinAttack || g_extras[i].more.batch.charge // (the last three: ManiaBatch.h's hits)
               || g_extras[i].more.cross.starGrab || g_extras[i].more.cross.headThrow // (ManiaCross.h's)
               || NightsHasFlight(g_extras[i].folder) // (ManiaNights.h's Paraloop)
               || g_extras[i].ab.noStomp; // (ManiaNoStomp.h)
    if (!any)
        return;
    if (!Player_State_Hurt_ || !Player_State_Death_ || !Player_State_Drown_ || !Player_Input_P1_ || !LinkMelee()) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "shot: the game's Player functions weren't found: no shots, no melee");
        return;
    }
    Mod.RegisterObject((void **)&NoSwapShot, NULL, "NoSwapShot", sizeof(EntityNoSwapShot), sizeof(ObjectNoSwapShot), 0, Shot_Update, NULL,
                       NULL, Shot_Draw, Shot_Create, NULL, NULL, NULL, NULL, NULL, NULL);
    for (size_t i = 0; i < HIT_CLASS_COUNT; ++i)
        Mod.RegisterObject(NULL, NULL, HIT_CLASSES[i].name, 0, 0, 0, HitUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    g_hitWrapped = true;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: NoSwapShot registered, %d hit classes' updates wrapped", (int32)HIT_CLASS_COUNT);
}

#include "ManiaMelee.h"
#include "ManiaPsycho.h"
#include "ManiaWalls.h"
#include "ManiaMore.h"
#include "ManiaBatch.h"
#include "ManiaHost.h" // (hosting on Tails / Knuckles, and their extras' moves)
#include "ManiaAmy.h"  // (Amy Rose's hammer moves and Super palette)
#include "ManiaGuest.h" // (the guest batch's moves: the Slide, the Rocket Burst)
#include "ManiaNoStomp.h" // (no_stomp: the jump isn't an attack, the roll / Slide is)
#include "ManiaCross.h" // (Ristar, Headdy, John Morris, Ecco)
#include "ManiaNinjutsu.h" // (Joe Musashi's Ninjutsu)
#include "ManiaNights.h" // (NiGHTS' free flight, Drill Dash and Paraloop)
#include "ManiaVoltteccer.h" // (Pulseman's Voltteccer)
#include "ManiaPotMagic.h" // (Gilius' pot magic)
#include "ManiaTriple.h" // (Mario's Triple Jump)

// Sally's Spin-Kick High Jump (abilities.py high_kick), the S3&K DLL's HighKick: Y on the ground (the plain ground state,
// standing, walking or running) or in the air state starts it, once per airborne period, or after highKickCooldown
// frames on the ground. A wind-up held still (the hover slot, frame 0: not an attack), then straight up at highKickRise
// in the kick's frames (the shot slot, an attack: reported as the jump), then at the top highKickRecover frames of the
// recovery pose (hover slot frame 1: not an attack), then she falls in the jump ball with her jump ability ready. A hit,
// a roll, an object taking over or landing ends it; started during the dive, it ends the dive. Player 1's, after every
// entity's update (as the melee).
static void HighKick(EntityPlayer *p, bool32 transformed, int32 animPose, int32 animKick)
{
    const Abilities *ab = &g_cur->ab;
    bool32 air          = !p->onGround;
    int32 a             = p->animator.animationID;
    bool32 plain        = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_WALK || (a >= ANI_JOG && a <= ANI_DASH);
    bool32 inState      = air ? p->state == Player_State_Air_ : p->state == Player_State_Ground_;
    if (!air && g_hk.k == 0) {
        g_hk.used = false;
        if (g_hk.cool > 0)
            g_hk.cool--;
    }
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    bool32 press    = key && key->press && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled && !transformed;
    if (g_hk.k == 0 && !Hurt(p) && press && (air ? inState && !g_hk.used : plain && inState && g_hk.cool == 0)) {
        g_hk.k    = 1;
        g_hk.used = true;
        MoveState *m = StateOf(p);
        if (m && m->kick) {
            m->kick = 0; // (out of the dive)
            BackToJump(p);
        }
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "high kick (%s)", air ? "air" : "ground");
    }
    if (g_hk.k == 0)
        return;
    if (Hurt(p) || !inState || (g_hk.k >= HIKICK_KICK && !air)) { // over
        g_hk.k    = 0;
        g_hk.cool = ab->highKickCooldown;
        if (!Hurt(p) && (Showing(p, animPose) || Showing(p, animKick))) {
            if (air)
                BackToJump(p);
            else
                RSDK.SetSpriteAnimation(p->aniFrames, ANI_WALK, &p->animator, true, 0);
        }
        return;
    }
    if (g_hk.k < HIKICK_KICK) { // the wind-up: held still
        p->velocity.x = 0;
        p->groundVel  = 0;
        if (air)
            p->velocity.y = 0;
        Show(p, animPose, false, false);
        p->animator.frameID = 0;
        if (++g_hk.k > ab->highKickWindup) { // launch, straight up
            if (!air) {
                p->onGround      = false;
                p->angle         = 0;
                p->collisionMode = CMODE_FLOOR;
                p->state         = Player_State_Air_;
            }
            p->velocity.y       = -ab->highKickRise;
            p->jumpAbilityState = 0;
            p->applyJumpCap     = false; // (letting go of jump doesn't cut it short)
            PlayNamed(g_cur->highKickSound);
            g_hk.k = HIKICK_KICK;
        }
    }
    else {
        if (g_hk.k < HIKICK_RECOVER) { // the kick, rising
            p->velocity.x = 0;
            p->groundVel  = 0;
            Show(p, animKick, true, g_hk.k == HIKICK_KICK);
            int32 count = p->animator.frameCount;
            if (count > 0)
                p->animator.frameID = (g_hk.k - HIKICK_KICK) / ab->highKickTicks % count;
            g_hk.k++;
            if (p->velocity.y >= 0) // the top: the recovery
                g_hk.k = HIKICK_RECOVER;
        }
        if (g_hk.k >= HIKICK_RECOVER) { // the recovery (normal air control)
            Show(p, animPose, false, false);
            p->animator.frameID = p->animator.frameCount > 1 ? 1 : 0;
            if (++g_hk.k > HIKICK_RECOVER + ab->highKickRecover) { // then she falls as from a jump, her jump ability ready
                g_hk.k    = 0;
                g_hk.cool = ab->highKickCooldown;
                BackToJump(p);
                p->jumpAbilityState = 1;
            }
        }
    }
    p->animator.timer = 0;
}

// ------------------------------------------------------------------------------------------------ palette
static bool32 IsUnset(color c) { return c == 0 || ((c >> 16) >= 0xF0 && ((c >> 8) & 0xFF) < 0x10 && (c & 0xFF) >= 0xF0); }

// The other banks the stage uses for the player (HCZ / AIZ water: bank 1, CPZ's Mega Mack: 2; OOZ's smog and FarPlane
// copy bank 0's player colours as they are into 1-2 / 3). Per bank, a mode:
//   BANK_TINT: the stage has its own version of Sonic there (water): the extra's colours through the bank's tint
//   BANK_COPY: the stage has none (or bank 0's as is): the extra's own colours
// The tint is fitted to the bank's version of every colour both banks have (slots 1-255, Sonic's own included): an
// affine map (out = M * rgb + t, least squares) plus half the local error of the 6 nearest pairs, so an extra's colour
// takes the bank's overall tint and lean near similar colours. (Water palettes are hand-painted, not a formula:
// HCZ turns reds purple and oranges grey; a per-colour ratio off the nearest single colour blew up on dark channels:
// Big's brown (7A5405) came out cyan and his purple (320A78) pink.)
#define BANK_FIRST (1)
#define BANK_LAST  (5) // (6-7: the Super fade's scratch banks)
enum { BANK_OFF, BANK_TINT, BANK_COPY };
static uint8 g_bankMode[8];
static color g_bankWrote[8][OWN_MAX]; // what NoSwap last put in each bank's own slots (kept across stages: stale rows)
static color g_bankTint[8][OWN_MAX];  // the bank's version of each own colour (TINT: the fit; COPY: the colour)
static color g_bankHost[8][PLAYER_PRIMARY_COLOR_COUNT]; // TINT: the stage's own Sonic colours there
static color g_host0[PLAYER_PRIMARY_COLOR_COUNT];      // bank 0's Sonic colours, as the stage loaded them

static bool32 IsOwnSlot(int32 slot)
{
    for (int32 i = 0; i < g_cur->ownCount; ++i)
        if (g_cur->ownSlot[i] == slot)
            return true;
    return false;
}

static bool32 IsSonicSlot(int32 slot) { return slot >= PLAYER_PALETTE_INDEX_SONIC && slot < PLAYER_PALETTE_INDEX_SONIC + PLAYER_PRIMARY_COLOR_COUNT; }

#define FIT_MAX (256 + PLAYER_PRIMARY_COLOR_COUNT)
typedef struct {
    int32 count;
    float src[FIT_MAX][3], dst[FIT_MAX][3], w[FIT_MAX];
    float m[4][3]; // out[ch] = sum(rgb1[k] * m[k][ch])
} BankFit;

static void FitAdd(BankFit *f, color a, color b, float w)
{
    if (f->count >= FIT_MAX || IsUnset(a) || IsUnset(b))
        return;
    for (int32 ch = 0; ch < 3; ++ch) {
        f->src[f->count][ch] = (float)((a >> (16 - 8 * ch)) & 0xFF);
        f->dst[f->count][ch] = (float)((b >> (16 - 8 * ch)) & 0xFF);
    }
    f->w[f->count++] = w;
}

static void FitApply(const BankFit *f, const float *c, float *out)
{
    for (int32 ch = 0; ch < 3; ++ch) out[ch] = c[0] * f->m[0][ch] + c[1] * f->m[1][ch] + c[2] * f->m[2][ch] + f->m[3][ch];
}

// Solve the weighted least squares (a small ridge keeps a bank with few distinct colours sane); false: no data
static bool32 FitSolve(BankFit *f)
{
    if (f->count < 8)
        return false;
    double a[4][7] = { { 0 } }; // [X'WX + ridge | X'WY]
    double wsum = 0;
    for (int32 n = 0; n < f->count; ++n) {
        double x[4] = { f->src[n][0], f->src[n][1], f->src[n][2], 1.0 };
        for (int32 r = 0; r < 4; ++r) {
            for (int32 c = 0; c < 4; ++c) a[r][c] += f->w[n] * x[r] * x[c];
            for (int32 ch = 0; ch < 3; ++ch) a[r][4 + ch] += f->w[n] * x[r] * f->dst[n][ch];
        }
        wsum += f->w[n];
    }
    for (int32 r = 0; r < 3; ++r) a[r][r] += 1e-3 * wsum;
    for (int32 col = 0; col < 4; ++col) {
        int32 piv = col;
        for (int32 r = col + 1; r < 4; ++r)
            if ((a[r][col] < 0 ? -a[r][col] : a[r][col]) > (a[piv][col] < 0 ? -a[piv][col] : a[piv][col]))
                piv = r;
        if ((a[piv][col] < 0 ? -a[piv][col] : a[piv][col]) < 1e-9)
            return false;
        for (int32 c = 0; c < 7; ++c) {
            double t   = a[col][c];
            a[col][c]  = a[piv][c];
            a[piv][c]  = t;
        }
        for (int32 r = 0; r < 4; ++r) {
            if (r == col)
                continue;
            double k = a[r][col] / a[col][col];
            for (int32 c = col; c < 7; ++c) a[r][c] -= k * a[col][c];
        }
    }
    for (int32 r = 0; r < 4; ++r)
        for (int32 ch = 0; ch < 3; ++ch) f->m[r][ch] = (float)(a[r][4 + ch] / a[r][r]);
    return true;
}

static color FitColour(const BankFit *f, color c)
{
    float in[3] = { (float)(c >> 16), (float)((c >> 8) & 0xFF), (float)(c & 0xFF) }, out[3];
    FitApply(f, in, out);
    // (the 6 nearest pairs' own errors, weighted by nearness: half of it)
    int32 near[6];
    float nd[6];
    int32 nc = 0;
    for (int32 n = 0; n < f->count; ++n) {
        float d = 0;
        for (int32 ch = 0; ch < 3; ++ch) d += (in[ch] - f->src[n][ch]) * (in[ch] - f->src[n][ch]);
        int32 at = nc < 6 ? nc++ : 6;
        if (at == 6) {
            if (d >= nd[5])
                continue;
            at = 5;
        }
        while (at > 0 && nd[at - 1] > d) {
            nd[at]   = nd[at - 1];
            near[at] = near[at - 1];
            --at;
        }
        nd[at]   = d;
        near[at] = n;
    }
    float res[3] = { 0, 0, 0 }, wsum = 0;
    for (int32 j = 0; j < nc; ++j) {
        float fit[3], w = 1.0f / (nd[j] + 256.0f);
        FitApply(f, f->src[near[j]], fit);
        for (int32 ch = 0; ch < 3; ++ch) res[ch] += w * (f->dst[near[j]][ch] - fit[ch]);
        wsum += w;
    }
    color o = 0;
    for (int32 ch = 0; ch < 3; ++ch) {
        float v = out[ch] + (wsum > 0 ? 0.5f * res[ch] / wsum : 0);
        int32 iv = (int32)(v + 0.5f);
        o |= (color)(iv < 0 ? 0 : iv > 0xFF ? 0xFF : iv) << (16 - 8 * ch);
    }
    return o;
}

static bool32 SameSonics(uint8 bank, const color *cols)
{
    for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c)
        if (RSDK.GetPaletteEntry(bank, PLAYER_PALETTE_INDEX_SONIC + c) != cols[c])
            return false;
    return true;
}

// Work out (fresh: from what the bank holds now) or redo (the stage's Sonic colours kept from before) a bank's mode
// and colours, and write them
static void SetupBank(uint8 bank, bool32 fresh)
{
    const Extra *e = g_cur;
    color now[PLAYER_PRIMARY_COLOR_COUNT], bank0[PLAYER_PRIMARY_COLOR_COUNT], own[PLAYER_PRIMARY_COLOR_COUNT], wrote[PLAYER_PRIMARY_COLOR_COUNT];
    bool32 unset = false, ownAll = true, wroteAll = true;
    for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c) {
        now[c]   = RSDK.GetPaletteEntry(bank, PLAYER_PALETTE_INDEX_SONIC + c);
        bank0[c] = RSDK.GetPaletteEntry(0, PLAYER_PALETTE_INDEX_SONIC + c);
        own[c] = wrote[c] = now[c];
        unset |= IsUnset(now[c]);
    }
    for (int32 i = 0; i < e->ownCount; ++i) {
        if (!IsSonicSlot(e->ownSlot[i]))
            continue;
        own[e->ownSlot[i] - PLAYER_PALETTE_INDEX_SONIC]   = e->ownColour[i];
        wrote[e->ownSlot[i] - PLAYER_PALETTE_INDEX_SONIC] = g_bankWrote[bank][i];
    }
    for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c) {
        ownAll &= now[c] == own[c];
        wroteAll &= now[c] == wrote[c];
    }

    if (fresh) {
        // no Sonic of its own there: unset, bank 0's (as loaded, or now), the extra's, or what NoSwap wrote before
        // (rows a stage doesn't load keep the last stage's)
        bool32 copy = unset || SameSonics(bank, g_host0) || SameSonics(bank, bank0) || ownAll || wroteAll;
        g_bankMode[bank] = copy ? BANK_COPY : BANK_TINT;
        if (!copy)
            memcpy(g_bankHost[bank], now, sizeof(now));
    }

    BankFit *fit = NULL;
    static BankFit fitStore;
    if (g_bankMode[bank] == BANK_TINT) {
        fit        = &fitStore;
        fit->count = 0;
        for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c) FitAdd(fit, g_host0[c], g_bankHost[bank][c], 2.0f); // (the closest role)
        for (int32 s = 1; s < 256; ++s)
            if (!IsSonicSlot(s) && !IsOwnSlot(s))
                FitAdd(fit, RSDK.GetPaletteEntry(0, s), RSDK.GetPaletteEntry(bank, s), 1.0f);
        if (!FitSolve(fit))
            fit = NULL;
    }

    for (int32 i = 0; i < e->ownCount; ++i) {
        uint8 slot = e->ownSlot[i];
        color c    = e->ownColour[i];
        if (g_bankMode[bank] == BANK_TINT) {
            if (e->hostTint[i])
                c = g_bankHost[bank][slot - PLAYER_PALETTE_INDEX_SONIC];
            else if (fit)
                c = FitColour(fit, c);
        }
        g_bankTint[bank][i] = c;
        // (COPY: Sonic's slots are the game's to copy from bank 0, the Super fade included)
        if (!(g_bankMode[bank] == BANK_COPY && IsSonicSlot(slot) && !fresh))
            RSDK.SetPaletteEntry(bank, slot, c);
        g_bankWrote[bank][i] = RSDK.GetPaletteEntry(bank, slot); // (as stored: 16-bit)
    }
}

static void WriteBank0(void)
{
    for (int32 i = 0; i < g_cur->ownCount; ++i) RSDK.SetPaletteEntry(0, g_cur->ownSlot[i], g_cur->ownColour[i]);
}

// The game's own Super palettes (Player's static values), kept to put back: an extra's colours must not stay there for
// the next stage's Sonic
static color g_superSaved[3][18];
static bool32 g_superKept = false;

static color *SuperRows(int32 which)
{
    return which == 0 ? Player->superPalette_Sonic : which == 1 ? Player->superPalette_Sonic_HCZ : Player->superPalette_Sonic_CPZ;
}

static void RestoreSuper(void)
{
    if (!g_superKept) {
        for (int32 w = 0; w < 3; ++w) memcpy(g_superSaved[w], SuperRows(w), sizeof(g_superSaved[w]));
        g_superKept = true;
    }
    for (int32 w = 0; w < 3; ++w) memcpy(SuperRows(w), g_superSaved[w], sizeof(g_superSaved[w]));
}

// Super (Sonic's slots only): row 0 is what the game puts back when he turns back (and fades from), rows 1-2 the
// colours it fades between. A "super_fade" slot fades to Sonic's golds; the others stay his own colour. HCZ's water
// rows (bank 1) and CPZ's (bank 2) likewise, in that bank's version (Player_HandleSuperColors).
static void SetupSuper(void)
{
    const Extra *e = g_cur;
    RestoreSuper();
    for (int32 i = 0; i < e->ownCount; ++i) {
        if (!IsSonicSlot(e->ownSlot[i]))
            continue;
        int32 c = e->ownSlot[i] - PLAYER_PALETTE_INDEX_SONIC;
        color *rows[3] = { Player->superPalette_Sonic, Player->superPalette_Sonic_HCZ, Player->superPalette_Sonic_CPZ };
        color vals[3]  = { e->ownColour[i], g_bankMode[1] ? g_bankTint[1][i] : e->ownColour[i], g_bankMode[2] ? g_bankTint[2][i] : e->ownColour[i] };
        for (int32 w = 0; w < 3; ++w) {
            rows[w][c] = vals[w];
            if (!e->superFade[i])
                rows[w][6 + c] = rows[w][12 + c] = vals[w];
        }
    }
}

static void SetupPalette(void)
{
    const Extra *e = g_cur;
    for (int32 i = 0; i < e->ownCount; ++i) g_hostBank0[i] = RSDK.GetPaletteEntry(0, e->ownSlot[i]);
    for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c) g_host0[c] = RSDK.GetPaletteEntry(0, PLAYER_PALETTE_INDEX_SONIC + c);
    memset(g_bankMode, BANK_OFF, sizeof(g_bankMode));
    for (uint8 bank = BANK_FIRST; bank <= BANK_LAST; ++bank) SetupBank(bank, true);
    SetupSuper();
    WriteBank0();
}

// Each frame: a bank whose own slots something else rewrote (a palette load: a Palette entity, a boss...) is done
// again; a TINT bank the game now copies bank 0's player colours into (OOZ, FarPlane) becomes COPY; a TINT bank whose
// Sonic slots something else changed (not the Super fade) gets the extra's again.
static void KeepBanks(bool32 super)
{
    const Extra *e = g_cur;
    color bank0[PLAYER_PRIMARY_COLOR_COUNT];
    for (int32 c = 0; c < PLAYER_PRIMARY_COLOR_COUNT; ++c) bank0[c] = RSDK.GetPaletteEntry(0, PLAYER_PALETTE_INDEX_SONIC + c);
    bool32 superRows = false;
    for (uint8 bank = BANK_FIRST; bank <= BANK_LAST; ++bank) {
        bool32 redo = false, fresh = false;
        for (int32 i = 0; i < e->ownCount && !redo; ++i)
            redo = !IsSonicSlot(e->ownSlot[i]) && RSDK.GetPaletteEntry(bank, e->ownSlot[i]) != g_bankWrote[bank][i];
        if (redo) {
            // (Sonic's slots still NoSwap's: the same mode, the fit again; else all afresh)
            fresh = false;
            for (int32 i = 0; i < e->ownCount && !fresh; ++i)
                fresh = IsSonicSlot(e->ownSlot[i]) && RSDK.GetPaletteEntry(bank, e->ownSlot[i]) != g_bankWrote[bank][i];
        }
        else if (g_bankMode[bank] == BANK_TINT && SameSonics(bank, bank0)) {
            g_bankMode[bank] = BANK_COPY;
            redo             = true;
        }
        else if (g_bankMode[bank] == BANK_TINT && !super) {
            for (int32 i = 0; i < e->ownCount && !redo; ++i)
                redo = IsSonicSlot(e->ownSlot[i]) && RSDK.GetPaletteEntry(bank, e->ownSlot[i]) != g_bankWrote[bank][i];
        }
        if (!redo)
            continue;
        SetupBank(bank, fresh);
        superRows |= bank == 1 || bank == 2;
    }
    if (superRows && !super)
        SetupSuper();
}

// ------------------------------------------------------------------------------------------------ physics
// Sonic's table as the game ships it (kept the first time: the object's static values may outlive a stage), put back
// at every stage load, then scaled by the extra's multipliers
static int32 g_physSaved[64];
static bool32 g_physKept = false;

static void RestorePhysics(void)
{
    int32 *table = Player->sonicPhysicsTable;
    if (!g_physKept) {
        if (table[0] != SONIC_TOP_SPEED) {
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "Sonic's physics table isn't the game's (top speed 0x%X): left as it is", table[0]);
            return;
        }
        memcpy(g_physSaved, table, sizeof(g_physSaved));
        g_physKept = true;
    }
    memcpy(table, g_physSaved, sizeof(g_physSaved));
}

static void SetupPhysics(void)
{
    const Abilities *ab = &g_cur->ab;
    RestorePhysics();
    if (!g_physKept)
        return;
    int32 *table = Player->sonicPhysicsTable;
    for (int32 row = 0; row < 8; ++row) {
        int32 *t = &table[row * 8];
        t[0]     = (int32)((int64)t[0] * ab->topSpeed / 1000);
        t[1]     = (int32)((int64)t[1] * ab->acceleration / 1000); // (acceleration; the game's deceleration is this one too)
        t[2]     = (int32)((int64)t[2] * ab->airAcceleration / 1000);
        t[6]     = (int32)((int64)t[6] * ab->jump / 1000); // (jumpStrength)
    }
}

// ------------------------------------------------------------------------------------------------ callbacks
static int32 StageExtra(void);

// The stage has the playing extra's host (Sonic, or Tails / Knuckles: ManiaHost.h)
static bool32 StageHasSonic(void)
{
    if (globals->gameMode == MODE_COMPETITION || globals->gameMode == MODE_ENCORE)
        return true; // (anyone can be Sonic there, and Encore swaps characters mid-stage)
    int32 host = HostOf(StageExtra());
    return (globals->playerID & 0xFF) == host || ((globals->playerID >> 8) & 0xFF) == host;
}

static void SaveSelectStageLoad(void);

// The extra playing this stage in Sonic's place (-1: none)
static int32 StageExtra(void)
{
    if (g_mode == MODE_ALWAYS)
        return g_alwaysExtra;
    if (g_mode == MODE_MENU && globals->gameMode == MODE_MANIA && (globals->playerID & 0xFF) == HostOf(g_playExtra))
        return g_playExtra;
    return -1;
}

// An animation of the extra's file, or -1 if it has none there
static int32 HasAnim(int32 anim) { return anim >= 0 && anim < 0x100 && RSDK.GetFrame(g_extraFrames, anim, 0) ? anim : -1; }

// modSettings.ini AllEmeralds = y (a test switch, off by default): every stage starts with all seven Chaos Emeralds
// in the save in use (SaveGame_GetSaveRAM, the game's public function; collectedEmeralds is SaveRAM +0x70 in the
// decompilation's SaveGame.h: 0x58 bytes of padding, then saveState, characterID, zoneID, lives, score, score1UP),
// so Super can be tried without collecting them. Works with or without the extras (Character = none).
static bool32 g_allEmeralds = false;
static void *(*SaveGame_GetSaveRAM_)(void) = NULL;
static void AllEmeraldsStageLoad(void)
{
    if (!g_allEmeralds)
        return;
    if (!SaveGame_GetSaveRAM_)
        SaveGame_GetSaveRAM_ = Mod.GetPublicFunction(NULL, "SaveGame_GetSaveRAM");
    uint8 *ram = SaveGame_GetSaveRAM_ ? (uint8 *)SaveGame_GetSaveRAM_() : NULL;
    if (ram)
        *(int32 *)(ram + 0x70) = 0x7F;
}

static void OnStageLoadEmeraldsOnly(void *data)
{
    (void)data;
    AllEmeraldsStageLoad();
}

static void OnStageLoad(void *data)
{
    (void)data;
    AllEmeraldsStageLoad();
    g_active = false;
    g_cur    = NULL;
    memset(g_moves, 0, sizeof(g_moves));
    afterImage_Clear(); // (a ghost's animator is the last stage's sprites: gone)
    g_wallsOn = g_fireOn = false;
    ShotsStageLoad(); // (nobody's shots from the last stage)
    MoreStageLoad();
    SaveSelectStageLoad();
    AmyStageLoad(); // (off until set up below)
    CrossStageLoad(); // (likewise: ManiaCross.h)
    NinjaStageLoad(); // (likewise: ManiaNinjutsu.h)
    PotsStageLoad(); // (likewise: ManiaPotMagic.h)
    NightsStageLoad(); // (likewise: ManiaNights.h)
    VoltStageLoad(); // (likewise: ManiaVoltteccer.h)
    if (g_mode == MODE_OFF || !Player)
        return;
    // (whatever an extra changed in Player's static values last stage: the game's own again)
    if (g_physKept)
        RestorePhysics();
    if (g_superKept)
        RestoreSuper();
    int32 extra = StageExtra();
    if (!StageHasSonic() || extra < 0 || extra >= g_extraCount)
        return;
    g_cur = &g_extras[extra];

    g_extraFrames = RSDK.LoadSpriteAnimation(g_cur->playerFile, SCOPE_STAGE);
    if (!AniFramesOK(g_extraFrames, ANI_JUMP)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s is missing or its sheet didn't load: %s is off", g_cur->playerFile, g_cur->name);
        g_cur = NULL;
        return;
    }
    const Abilities *ab = &g_cur->ab;
    g_animAttack = HasAnim(g_cur->animBase + 0);
    g_animHover  = HasAnim(g_cur->animBase + 1);
    g_jetDash    = ab->jetDash && g_animAttack >= 0;
    g_hover      = ab->hover && g_jetDash && g_animHover >= 0;
    g_doubleJump = ab->doubleJump && g_animAttack >= 0;
    g_umbrella   = ab->umbrella && (ab->umbrellaAttack ? g_animAttack : g_animHover) >= 0;
    g_animAttackUp   = HasAnim(g_cur->animBase + 3);
    g_animAttackDown = HasAnim(g_cur->animBase + 4);
    g_animSwim       = HasAnim(g_cur->animBase + 5);
    g_animHkPose     = HasAnim(g_cur->animBase + 1);
    g_animHkKick     = HasAnim(g_cur->animBase + 2);
    g_chaos          = ab->chaosControl && g_animAttack >= 0;
    g_aimDash        = ab->aimDash && g_animAttack >= 0;
    g_kick           = ab->screwKick && ab->kickOnJump && g_animAttack >= 0;
    g_hammer         = ab->hammerDrop && g_animAttack >= 0 && Player_State_MightyHammerDrop_;
    g_swim           = ab->waterSwim && g_animSwim >= 0;
    g_highKick       = ab->highKick && g_animHkPose >= 0 && g_animHkKick >= 0 && Player_State_Ground_ && Player_Input_P1_;
    g_copy           = 0;
    memset(&g_hk, 0, sizeof(g_hk));
    if (ab->jetDash != g_jetDash || ab->hover != g_hover || ab->doubleJump != g_doubleJump || ab->umbrella != g_umbrella
        || ab->chaosControl != g_chaos || ab->aimDash != g_aimDash || (ab->screwKick && ab->kickOnJump) != g_kick
        || ab->hammerDrop != g_hammer || ab->waterSwim != g_swim || ab->highKick != g_highKick)
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s lacks an ability animation (attack %d, hover %d, shot %d, swim %d): some moves are off",
                      g_cur->playerFile, g_animAttack, g_animHover, g_animHkKick, g_animSwim);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s plays: sprites %s (id %d); jet dash %d, hover %d, double jump %d, umbrella %d, chaos %d, "
                  "aim dash %d, kick %d, hammer %d, swim %d, high kick %d, cycle %d, walls %d/%d, fire %d",
                  g_cur->name, g_cur->playerFile, (int32)g_extraFrames, g_jetDash, g_hover, g_doubleJump, g_umbrella, g_chaos, g_aimDash,
                  g_kick, g_hammer, g_swim, g_highKick, ab->cycleCount, ab->breaksWalls, g_cur->shotBreaksWalls, ab->fireImmune);

    // (the host's own IDs: Player_LoadSprites has loaded them; an object reloading them later, e.g. Player_ChangeCharacter
    // in Encore, gets these same IDs back, which OnLateUpdate swaps. Player_Create, after this, gives the host its
    // frames from Player's: the extra's. ManiaHost.h)
    HostStageLoad();
    SetupPhysics();
    SetupPalette();
    g_active = true;
    ShotsStageLoad();
    WallsStageLoad();
    MoreStageLoad();
    BatchStageLoad(); // (ManiaBatch.h)
    GuestStageLoad(); // (ManiaGuest.h)
    NoStompStageLoad(); // (ManiaNoStomp.h: after the shots' hit classes and the guest batch)
    CrossStageLoad(); // (ManiaCross.h)
    NinjaStageLoad(); // (ManiaNinjutsu.h)
    PotsStageLoad(); // (ManiaPotMagic.h)
    NightsStageLoad(); // (ManiaNights.h)
    VoltStageLoad(); // (ManiaVoltteccer.h)
    AmyStageLoad();   // (ManiaAmy.h)
    TripleStageLoad(); // (ManiaTriple.h)
}

static void EachPlayer(void (*fn)(EntityPlayer *))
{
    if (!Player)
        return;
    for (int32 slot = 0; slot < PLAYER_COUNT; ++slot) {
        EntityPlayer *player = (EntityPlayer *)RSDK.GetEntity(slot);
        if (IsExtra(player))
            fn(player);
    }
}

static void NoBreathing(EntityPlayer *player) { player->drownTimer = 0; }

// An object (Player_ChangeCharacter, SizeLaser...) gave him Sonic's frames back: his own again
static void KeepSprites(EntityPlayer *player)
{
    if (player->aniFrames != g_sonicFrames && player->aniFrames != g_superFrames)
        return;
    player->aniFrames = g_extraFrames;
    int32 frame       = player->animator.frameID;
    RSDK.SetSpriteAnimation(g_extraFrames, player->animator.animationID, &player->animator, true, 0);
    if (frame < player->animator.frameCount)
        player->animator.frameID = frame;
}

static void ForgetMoves(EntityPlayer *player)
{
    MoveState *m = StateOf(player);
    if (!m || (m->hammer && player->state == Player_State_MightyHammerDrop_))
        return;
    if ((m->dash || m->hover || m->dbl || m->umbrella || m->chaos || m->aim || m->kick || m->hammer)
        && (player->onGround || player->state != Player_State_Air_))
        EndMoves(player, m);
}

static bool32 anySuper;
static void CheckSuper(EntityPlayer *player) { anySuper |= player->superState != SUPERSTATE_NONE; }

static void OnUpdate(void *data)
{
    if (!g_active)
        return;
    if (g_cur->ab.noBreathing)
        EachPlayer(NoBreathing); // (after every entity's update: the Water object's count never gets past 1)
    EachPlayer(ForgetMoves);
    // (Y's throw or melee and their poses: only while the game runs, not paused or frozen)
    EntityPlayer *p1 = Player ? (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1) : NULL;
    if ((size_t)data != ENGINESTATE_REGULAR || !p1)
        return;
    g_frame++;
    afterImage_Fade(); // (any move's afterimages fade out: ManiaGhost.h)
    if (g_tripleOn)
        EachPlayer(TripleUpdate); // (Mario's Triple Jump: ManiaTriple.h)
    bool32 transformed = IsExtra(p1) && g_meleePrevSuper == SUPERSTATE_NONE && p1->superState != SUPERSTATE_NONE; // (Y made him Super)
    if (IsExtra(p1))
        g_meleePrevSuper = p1->superState;
    NinjaPress(p1, transformed); // (first: Joe's up + Y cast takes the press, no shuriken with it; ManiaNinjutsu.h)
    PotsPress(p1, transformed); // (first too: Gilius' up + Y Earthquake takes the press, no chop with it; ManiaPotMagic.h)
    MoreUpdate(p1, transformed); // (the Shadow Sink, the anchor)
    BatchUpdate(p1, transformed); // (the Sonic-hosted batch's moves: ManiaBatch.h)
    GuestUpdate(p1, transformed); // (the guest batch's: ManiaGuest.h)
    NoStompUpdate(p1); // (no_stomp's roll shown as his slide: ManiaNoStomp.h)
    CrossUpdate(p1, transformed); // (Ristar, Headdy, Ecco: ManiaCross.h)
    NightsUpdate(p1, transformed); // (NiGHTS: ManiaNights.h)
    VoltUpdate(p1); // (Pulseman: ManiaVoltteccer.h)
    if (g_shotOn && IsExtra(p1) && !g_cur->more.amy.on) // (Amy's Y: ManiaAmy.h, gated)
        ShotFrame(p1, transformed);
    AmyUpdate(p1, transformed); // (Amy's throw, her body numbers: ManiaAmy.h)
    if (g_meleeOn)
        MeleeUpdate(p1, transformed);
    if (g_highKick && IsExtra(p1))
        HighKick(p1, transformed, g_animHkPose, g_animHkKick);
    HostUpdate(p1, transformed); // (the Tails / Knuckles-hosted extras' moves: ManiaHost.h)
    NinjaAfter(p1); // (Joe's cast pose, Mijin's cost, Fushin's jump: after every move; ManiaNinjutsu.h)
    PotsAfter(p1); // (Gilius' Earthquake: its waves, boulders and pose, after every move; ManiaPotMagic.h)
    MoreAfter(p1); // (the water walk: after every move has moved her)
}

static void OnLateUpdate(void *data)
{
    (void)data;
    if (!g_active)
        return;
    if (g_cur->ab.noBreathing)
        EachPlayer(NoBreathing);
    HostSetFrames(); // (the host's frames: the extra's)
    EachPlayer(KeepSprites);
    EachPlayer(HostKeep); // (no twin tails on Tails' extras)

    // Something put the stage's colours back in the extra's slots (a palette reload): its own again. Sonic's slots
    // together (a tinted version, a zone's own lighting effect, is left alone, and so is the Super form's fade); the
    // others one by one.
    anySuper = false;
    EachPlayer(CheckSuper);
    KeepBanks(anySuper);
    bool32 sonics = !anySuper, any = false;
    for (int32 i = 0; i < g_cur->ownCount; ++i) {
        uint8 slot = g_cur->ownSlot[i];
        bool32 host = RSDK.GetPaletteEntry(0, slot) == g_hostBank0[i] && g_hostBank0[i] != g_cur->ownColour[i];
        if (slot >= PLAYER_PALETTE_INDEX_SONIC && slot < PLAYER_PALETTE_INDEX_SONIC + PLAYER_PRIMARY_COLOR_COUNT) {
            any = true;
            sonics &= RSDK.GetPaletteEntry(0, slot) == g_hostBank0[i];
        }
        else if (host) {
            RSDK.SetPaletteEntry(0, slot, g_cur->ownColour[i]);
        }
    }
    if (any && sonics)
        for (int32 i = 0; i < g_cur->ownCount; ++i)
            if (g_cur->ownSlot[i] >= PLAYER_PALETTE_INDEX_SONIC && g_cur->ownSlot[i] < PLAYER_PALETTE_INDEX_SONIC + PLAYER_PRIMARY_COLOR_COUNT)
                RSDK.SetPaletteEntry(0, g_cur->ownSlot[i], g_cur->ownColour[i]);
}

// ------------------------------------------------------------------------------------------------ save select
// UISaveSlot keeps its character as frameID (0 Sonic & Tails, 1 Sonic, 2 Tails, 3 Knuckles, 4 Mighty, 5 Ray). An extra
// is its host's frameID (1 Sonic, 2 Tails, 3 Knuckles: what the game starts, saves and loads; ManiaHost.h HostFrame) plus
// NoSwap's own record for that slot, g_slotExtra.
#define SLOT_FILE         "NoSwapManiaSlots.ini" // (the game's working folder, where SaveData.bin is)
#define SLOT_COUNT        (8)                    // Mania Mode's numbered saves (slotID 0-7)
#define SLOT_NOSAVE       (SLOT_COUNT)           // g_slotExtra's entry for the No Save slot
#define FRAME_SONIC_TAILS (0)
#define FRAME_SONIC       (1)

static void (*UISaveSlot_StateInput_NewSave_)(void);
static void (*UISubHeading_SaveButton_ActionCB_)(void);

static int32 g_slotExtra[SLOT_COUNT + 1]; // the extra each slot shows (-1: none)
// The extras' pictures: the save select atlas (tools/build_mania_art.py build_save_atlas: every extra we build, on ONE
// sheet, so the menu's sheet count doesn't grow with the roster), or, for a package outside it (a third party's), its own
// SaveSelect.bin / Save.gif, loaded only when first shown and at most SAVE_OWN_MAX of them per menu scene (each is a sheet
// of the engine's 64; the menu's own take ~37). Past the cap, or if anything fails to load, that slot shows Sonic.
#define SAVE_ATLAS_FILE "NoSwap/SaveSelectAtlas.bin"
#define SAVE_OWN_MAX    (4)
static const int32 SAVE_ATLAS_PARTS[4] = { 1, 2, 3, 21 }; // Players, Player Shadows, Life Icons, Continue Icons (frame 0: Sonic's)
static uint16 g_saveAtlas = 0xFFFF;      // SaveSelectAtlas.bin (0xFFFF: not here)
static int32 g_atlasAnim[EXTRA_MAX];     // the extra's "extra:<folder>" animation there (-1: not in it)
static uint16 g_saveFrames[EXTRA_MAX];   // a package's own SaveSelect copy (outside the atlas)
static int8 g_saveState[EXTRA_MAX];      // its state: 0 not loaded yet, 1 loaded, -1 failed / over the cap
static int32 g_saveOwnLoaded = 0;        // own copies tried this menu scene
static EntityUISaveSlot *g_cycleSlot = NULL; // the slot whose character input is running, and its frameID before it
static int32 g_cycleFrom             = 0;

// g_slotExtra's entry for a save slot, or -1 (Encore's slots are left alone)
static int32 SlotKey(EntityUISaveSlot *slot)
{
    if (!UISaveSlot || !slot || slot->classID != UISaveSlot->classID || slot->encoreMode)
        return -1;
    if (slot->type == UISAVESLOT_NOSAVE)
        return SLOT_NOSAVE;
    return slot->slotID >= 0 && slot->slotID < SLOT_COUNT ? slot->slotID : -1;
}

// NoSwapManiaSlots.ini: "slot<N>=<package folder>" for each numbered save (1-8) that is an extra
static void LoadSlotFile(void)
{
    for (int32 i = 0; i <= SLOT_COUNT; ++i) g_slotExtra[i] = -1;
    FILE *f = fopen(SLOT_FILE, "r");
    if (!f)
        return;
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        int32 n = 0;
        char key[64];
        if (sscanf(line, " slot%d = %63[^ \t\r\n;]", &n, key) == 2 && n >= 1 && n <= SLOT_COUNT)
            g_slotExtra[n - 1] = ExtraIndex(key); // (a package that's gone: -1, the save plays as Sonic)
    }
    fclose(f);
}

static void SaveSlotFile(const int32 *records)
{
    FILE *f = fopen(SLOT_FILE, "w");
    if (!f) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "couldn't write %s", SLOT_FILE);
        return;
    }
    fprintf(f, "; NoSwapMania: the extra character of each Mania Mode save (the game's own save has Sonic there)\n");
    for (int32 i = 0; i < SLOT_COUNT; ++i)
        if (records[i] >= 0)
            fprintf(f, "slot%d=%s\n", i + 1, g_extras[records[i]].folder);
    fclose(f);
}
static int32 g_fileExtra[SLOT_COUNT]; // what the file says (the numbered saves as saved; g_slotExtra is what's shown)

// The extra this slot shows now (-1: none). A slot that isn't on Sonic any more (moved on, a blank save reset to
// Sonic & Tails, a deleted save) forgets its extra.
static int32 ShownExtra(EntityUISaveSlot *slot)
{
    int32 key = SlotKey(slot);
    if (key < 0)
        return -1;
    if (g_slotExtra[key] >= 0 && slot->frameID != HostFrame(g_slotExtra[key])) // (an extra shows on its host's frame)
        g_slotExtra[key] = -1;
    return g_slotExtra[key];
}

// The menu scene: the extras' SaveSelect copies; and nobody is chosen yet
static void SaveSelectStageLoad(void)
{
    memset(g_saveState, 0, sizeof(g_saveState));
    for (int32 i = 0; i < EXTRA_MAX; ++i) g_atlasAnim[i] = -1;
    g_saveAtlas     = 0xFFFF;
    g_saveOwnLoaded = 0;
    g_cycleSlot     = NULL;
    if (g_mode == MODE_OFF || !UISaveSlot || !RSDK.FindObject("UISaveSlot"))
        return;
    g_playExtra = -1;
    if (!g_extraCount)
        return;
    g_saveAtlas = RSDK.LoadSpriteAnimation(SAVE_ATLAS_FILE, SCOPE_STAGE);
    if (!AniFramesOK(g_saveAtlas, 21)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s is missing or its sheet didn't load: each extra's own pictures instead", SAVE_ATLAS_FILE);
        g_saveAtlas = 0xFFFF;
    }
    int32 inAtlas = 0;
    for (int32 i = 0; g_saveAtlas != 0xFFFF && i < g_extraCount; ++i) {
        char name[80];
        snprintf(name, sizeof(name), "extra:%.63s", g_extras[i].folder);
        uint16 anim = RSDK.FindSpriteAnimation(g_saveAtlas, name);
        if (anim < 0x1000 && RSDK.GetFrame(g_saveAtlas, anim, 0)) {
            g_atlasAnim[i] = anim;
            ++inAtlas;
        }
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "save select: %d of %d extras in the atlas (the rest load their own pictures when shown)",
                  inAtlas, g_extraCount);
}

// The SaveSelect copy to draw an extra's slot with, set up for it (0xFFFF: none, the slot shows Sonic)
static uint16 SaveFramesFor(int32 extra)
{
    if (g_atlasAnim[extra] >= 0) { // its four pictures into its host's frames of the atlas copy (only we draw with it)
        for (int32 k = 0; k < 4; ++k) {
            SpriteFrame *to = RSDK.GetFrame(g_saveAtlas, SAVE_ATLAS_PARTS[k], HostIndex(&g_extras[extra])); // (0 Sonic, 1 Tails, 2 Knux)
            SpriteFrame *from = RSDK.GetFrame(g_saveAtlas, g_atlasAnim[extra], k);
            if (!to || !from)
                return 0xFFFF;
            *to = *from;
        }
        return g_saveAtlas;
    }
    if (g_saveState[extra] == 0) { // a package outside the atlas: its own copy, the first time it shows
        const Extra *e = &g_extras[extra];
        if (g_saveOwnLoaded >= SAVE_OWN_MAX) {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "save select: %s isn't in the atlas and %d packages' own pictures are loaded "
                          "already (the engine's sheets are limited): it shows Sonic", e->folder, SAVE_OWN_MAX);
            g_saveState[extra] = -1;
            return 0xFFFF;
        }
        ++g_saveOwnLoaded;
        g_saveFrames[extra] = RSDK.LoadSpriteAnimation(e->saveSelectFile, SCOPE_STAGE);
        g_saveState[extra]  = AniFramesOK(g_saveFrames[extra], 21) ? 1 : -1;
        if (g_saveState[extra] < 0)
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s is missing or its sheet didn't load: the save select shows Sonic for %s",
                          e->saveSelectFile, e->folder);
    }
    return g_saveState[extra] > 0 ? g_saveFrames[extra] : 0xFFFF;
}

// UISaveSlot's Draw, for a slot showing an extra: the game's own drawing with the extra's SaveSelect copy (the same
// animations; Sonic's frames are the extra's) and the extra's colours in the menu palette's free slots, both put back
// right after. (The zone preview's animator is pointed at the copy too: the game resizes that frame as it scrolls.)
static void SaveSlot_Draw(void)
{
    EntityUISaveSlot *self = (EntityUISaveSlot *)SceneInfo->entity;
    int32 extra            = ShownExtra(self);
    uint16 frames          = extra >= 0 && extra < g_extraCount ? SaveFramesFor(extra) : 0xFFFF;
    if (frames == 0xFFFF) {
        Mod.Super(UISaveSlot->classID, SUPER_DRAW, NULL);
        return;
    }
    const Extra *e = &g_extras[extra];

    uint16 saved[8][SAVE_PAL_COUNT];
    for (int32 bank = 0; bank < 8; ++bank) {
        uint16 *pal = Mod.GetPaletteBank ? Mod.GetPaletteBank(bank) : NULL;
        if (pal)
            for (int32 c = 0; c < SAVE_PAL_COUNT; ++c) saved[bank][c] = pal[SAVE_SLOTS[c]];
        for (int32 c = 0; c < e->saveColourCount; ++c) RSDK.SetPaletteEntry(bank, SAVE_SLOTS[c], e->saveColours[c]);
    }
    uint16 aniFrames        = UISaveSlot->aniFrames;
    SpriteFrame *zoneFrames = self->zoneIconAnimator.frames;
    UISaveSlot->aniFrames   = frames;
    if (zoneFrames)
        self->zoneIconAnimator.frames = RSDK.GetFrame(frames, 5, 0);

    Mod.Super(UISaveSlot->classID, SUPER_DRAW, NULL);

    UISaveSlot->aniFrames         = aniFrames;
    self->zoneIconAnimator.frames = zoneFrames;
    for (int32 bank = 0; bank < 8; ++bank) {
        uint16 *pal = Mod.GetPaletteBank ? Mod.GetPaletteBank(bank) : NULL;
        if (pal)
            for (int32 c = 0; c < SAVE_PAL_COUNT; ++c) pal[SAVE_SLOTS[c]] = saved[bank][c];
    }
}

// Up/down on a No Save slot or a new save (UISaveSlot_StateInput_NewSave, which calls UISaveSlot_NextCharacter /
// PrevCharacter): before it, remember the character; after it, fit the extras in. They come after the last character
// (Ray; Knuckles without Plus) going up, before Sonic & Tails going down. The game's own step (its sound and bounce) has
// run already; this only changes where it lands.
static bool32 Hook_NewSaveInput_Before(bool32 skipped)
{
    (void)skipped;
    EntityUISaveSlot *self = (EntityUISaveSlot *)SceneInfo->entity;
    g_cycleSlot            = SlotKey(self) >= 0 ? self : NULL;
    if (g_cycleSlot)
        g_cycleFrom = self->frameID;
    return false;
}

static bool32 Hook_NewSaveInput_After(bool32 skipped)
{
    EntityUISaveSlot *self = (EntityUISaveSlot *)SceneInfo->entity;
    if (skipped || self != g_cycleSlot || !g_extraCount)
        return false;
    g_cycleSlot = NULL;
    int32 key = SlotKey(self), from = g_cycleFrom, to = self->frameID;
    if (key < 0 || from == to)
        return false;
    int32 last  = (API.CheckDLC(DLC_PLUS) ? 6 : 4) - 1;
    int32 extra = g_slotExtra[key] >= 0 && from == HostFrame(g_slotExtra[key]) ? g_slotExtra[key] : -1;

    // (an extra shows on its host's frame: Sonic's, Tails' or Knuckles', ManiaHost.h HostFrame)
    if (extra >= 0) { // was an extra (so the game has just stepped off its host)
        bool32 up = to == (from + 1) % (last + 1);
        if (up && extra + 1 < g_extraCount) {
            g_slotExtra[key] = extra + 1;
            self->frameID    = HostFrame(extra + 1);
        }
        else if (!up && extra > 0) {
            g_slotExtra[key] = extra - 1;
            self->frameID    = HostFrame(extra - 1);
        }
        else {
            g_slotExtra[key] = -1;
            self->frameID    = up ? FRAME_SONIC_TAILS : last;
        }
    }
    else if (from == last && to == FRAME_SONIC_TAILS) { // up past the last character: the first extra
        g_slotExtra[key] = 0;
        self->frameID    = HostFrame(0);
    }
    else if (from == FRAME_SONIC_TAILS && to == last) { // down past Sonic & Tails: the last extra
        g_slotExtra[key] = g_extraCount - 1;
        self->frameID    = HostFrame(g_extraCount - 1);
    }
    return false;
}

// A save slot starts the game (UISubHeading_SaveButton_ActionCB, before it): who plays, and a new save's extra kept
static bool32 Hook_SaveAction(bool32 skipped)
{
    (void)skipped;
    EntityUISaveSlot *self = (EntityUISaveSlot *)SceneInfo->entity;
    int32 key              = SlotKey(self);
    g_playExtra            = key >= 0 ? ShownExtra(self) : -1;
    if (key >= 0 && key < SLOT_COUNT && self->isNewSave && g_fileExtra[key] != g_playExtra) {
        g_fileExtra[key] = g_playExtra;
        SaveSlotFile(g_fileExtra);
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "save slot %d starts: %s", self->slotID,
                  g_playExtra >= 0 ? g_extras[g_playExtra].name : "(the game's own character)");
    return false;
}

static void LinkSaveSelect(void)
{
    UISaveSlot_StateInput_NewSave_    = Mod.GetPublicFunction(NULL, "UISaveSlot_StateInput_NewSave");
    UISubHeading_SaveButton_ActionCB_ = Mod.GetPublicFunction(NULL, "UISubHeading_SaveButton_ActionCB");
    if (!UISaveSlot_StateInput_NewSave_ || !UISubHeading_SaveButton_ActionCB_) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "the game's save select functions weren't found: no extras there");
        return;
    }
    LoadSlotFile();
    for (int32 i = 0; i < SLOT_COUNT; ++i) g_fileExtra[i] = g_slotExtra[i];

    MOD_REGISTER_OBJECT_HOOK(UISaveSlot);
    // (UISaveSlot overridden: only its Draw is ours, the rest is the game's)
    Mod.RegisterObject(NULL, NULL, "UISaveSlot", sizeof(EntityUISaveSlot), 0, 0, NULL, NULL, NULL, SaveSlot_Draw, NULL, NULL, NULL,
                       NULL, NULL, NULL, NULL);
    Mod.RegisterStateHook(UISaveSlot_StateInput_NewSave_, Hook_NewSaveInput_Before, true);
    Mod.RegisterStateHook(UISaveSlot_StateInput_NewSave_, Hook_NewSaveInput_After, false);
    Mod.RegisterStateHook(UISubHeading_SaveButton_ActionCB_, Hook_SaveAction, true);
}

// ------------------------------------------------------------------------------------------------ no_roll
// extras.py "no_roll" (Gamma never curls into a ball), as the S3&K DLL's NoRollInput: right after player 1's input
// (Player_Input_P1), on the ground, down is let go of while moving (Player_State_Ground's roll needs it) and, crouching, when
// jump is pressed (Player_State_Crouch then stands him up and jumps: a plain jump, no Spin Dash). Crouching still works;
// objects that force a roll (tubes) still do. His jump is the game's (its animation his own jump pose), so it attacks.
static bool32 Hook_NoRollInput(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!IsExtra(self) || !g_cur->noRoll || !self->onGround)
        return false;
    if (self->state == Player_State_Crouch_ || self->animator.animationID == ANI_CROUCH) {
        if (self->jumpPress)
            self->down = false;
    }
    else if (self->groundVel != 0) {
        self->down = false;
    }
    return false;
}

#include "ManiaHud.h" // (the HUD and screens: life icon, act clear name, Super glow, continue, Blue Spheres)
#include "ManiaUfo.h" // (the UFO special stages: the extra's spin ball in place of the 3D model)
#include "ManiaSweep.h" // (the frozen player, 1-up monitors, UFO results, the TV van: by characterID elsewhere)
#include "ManiaSpin.h"  // (Spin Dash-only gimmicks for extras without one: dash wheels, Spin Dash lifts)

// ------------------------------------------------------------------------------------------------ link
static int32 ReadSetting(const char *id)
{
    String value;
    INIT_STRING(value);
    Mod.GetSettingsString(id, "Character", &value, "menu");
    char text[64];
    memset(text, 0, sizeof(text));
    if (value.chars && value.length < sizeof(text))
        RSDK.GetCString(text, &value);
    if (strcmp(text, "none") == 0)
        return MODE_OFF;
    if (!text[0] || strcmp(text, "menu") == 0)
        return MODE_MENU;
    CopyText(g_settingFolder, sizeof(g_settingFolder), text);
    return MODE_ALWAYS;
}

#if RETRO_USE_MOD_LOADER
DLLExport bool32 LinkModLogic(EngineInfo *info, const char *id)
{
#if RETRO_REV02
    LinkGameLogicDLL(info);
#else
    LinkGameLogicDLL(*info);
#endif
    globals = Mod.GetGlobals();
    modID   = id;

    g_allEmeralds = Mod.GetSettingsBool(id, "AllEmeralds", false);
    if (g_allEmeralds)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "AllEmeralds: on (a test switch: every stage starts with all seven)");
    g_mode = ReadSetting(id);
    if (g_mode == MODE_OFF) {
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "Character: none (the game as it is)");
        if (g_allEmeralds)
            Mod.AddModCallback(MODCB_ONSTAGELOAD, OnStageLoadEmeraldsOnly);
        return true;
    }
    ScanPackages(id);
    if (g_mode == MODE_ALWAYS) {
        g_alwaysExtra = ExtraIndex(g_settingFolder);
        if (g_alwaysExtra < 0) {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "Character = %s: no such package; chosen in the save select instead", g_settingFolder);
            g_mode = MODE_MENU;
        }
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "Character: %s%s", g_mode == MODE_ALWAYS ? g_extras[g_alwaysExtra].name : "chosen in Mania Mode's save select",
                  g_mode == MODE_ALWAYS ? " (in place of every Sonic)" : "");
    if (!g_extraCount) {
        g_mode = MODE_OFF;
        return true;
    }

    Player_State_Air_         = Mod.GetPublicFunction(NULL, "Player_State_Air");
    Player_JumpAbility_Sonic_ = Mod.GetPublicFunction(NULL, "Player_JumpAbility_Sonic");
    Player_Input_P2_AI_       = Mod.GetPublicFunction(NULL, "Player_Input_P2_AI");
    Player_Input_P1_          = Mod.GetPublicFunction(NULL, "Player_Input_P1");
    if (!Player_State_Air_ || !Player_JumpAbility_Sonic_ || !Player_Input_P2_AI_ || !Player_Input_P1_) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "the game's Player functions weren't found: off");
        g_mode = MODE_OFF;
        return true;
    }

    MOD_REGISTER_OBJECT_HOOK(Player);
    Mod.AddModCallback(MODCB_ONSTAGELOAD, OnStageLoad);
    Mod.AddModCallback(MODCB_ONUPDATE, OnUpdate);
    Mod.AddModCallback(MODCB_ONLATEUPDATE, OnLateUpdate);
    Mod.RegisterStateHook(Player_JumpAbility_Sonic_, Hook_JumpAbilitySonic, true);
    Mod.RegisterStateHook(Player_State_Air_, Hook_StateAir, false);
    Player_State_MightyHammerDrop_ = Mod.GetPublicFunction(NULL, "Player_State_MightyHammerDrop");
    if (Player_State_MightyHammerDrop_) {
        Mod.RegisterStateHook(Player_State_MightyHammerDrop_, Hook_HammerBefore, true);
        Mod.RegisterStateHook(Player_State_MightyHammerDrop_, Hook_HammerAfter, false);
    }
    if (!Player_State_Ground_) // (the high kick's ground state; LinkShots finds it when an extra has a shot or melee)
        Player_State_Ground_ = Mod.GetPublicFunction(NULL, "Player_State_Ground");
    Player_State_Hurt_  = Mod.GetPublicFunction(NULL, "Player_State_Hurt");
    Player_State_Death_ = Mod.GetPublicFunction(NULL, "Player_State_Death");
    Player_State_Drown_ = Mod.GetPublicFunction(NULL, "Player_State_Drown");
    LinkShots();
    LinkWalls();
    LinkMore();
    LinkBatch(); // (after LinkMore: ManiaBatch.h)
    LinkGuest(); // (before no_roll's input hook: ManiaGuest.h)
    bool32 noRoll = false;
    for (int32 i = 0; i < g_extraCount; ++i) noRoll |= g_extras[i].noRoll;
    if (noRoll) {
        if (!Player_State_Crouch_)
            Player_State_Crouch_ = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
        Mod.RegisterStateHook(Player_Input_P1_, Hook_NoRollInput, false);
    }
    LinkSaveSelect();
    LinkHud();
    LinkHost(); // (after LinkHud: ManiaHost.h)
    LinkAmy();  // (last: its late update after the HUD's)
    LinkUfo();  // (ManiaUfo.h)
    LinkSweep(); // (ManiaSweep.h; after LinkHud)
    LinkCross(); // (ManiaCross.h)
    LinkNinja(); // (ManiaNinjutsu.h)
    LinkPots(); // (ManiaPotMagic.h)
    LinkNights(); // (ManiaNights.h)
    LinkSpin();  // (ManiaSpin.h)
    return true;
}
#endif
