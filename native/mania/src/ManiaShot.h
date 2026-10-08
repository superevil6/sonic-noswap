// NoSwapMania's shot data: an extra's projectile as its package describes it ("shot" / "shot2" in the "mania" section of
// noswap_character.json, written by tools/build_mania_art.py from abilities.py's S3&K numbers). The same fields, ranges
// and defaults as the S3&K DLL's ShotData / ReadShot (native/src/ExtraData.h), less what the Mania mod doesn't do yet
// (swap shots, burning drops, "pose_always"). The runtime: NoSwapMania.c "shots".
// Included once, by NoSwapMania.c (after its LOG_TAG).
#ifndef MANIA_SHOT_H
#define MANIA_SHOT_H

#include "JsonLite.h"

#include <string.h>

enum { SHOT_NONE, SHOT_BOUNCE, SHOT_STRAIGHT, SHOT_BOOMERANG, SHOT_HOMING, SHOT_DROP, SHOT_DIP, SHOT_GROUND };

typedef struct {
    int32 motion;
    int32 speed;        // forward speed (the player's own forward speed is added, unless "carry" is false)
    int32 startVY;      // vertical speed when thrown (down: positive)
    int32 gravity;      // added to the vertical speed each frame (bounce, drop; negative: a dip)
    int32 bounce;       // vertical speed after touching a floor (bounce)
    int32 maxFall;      // fall speed cap
    int32 lifetime;     // frames before it vanishes
    int32 maxAlive;     // at most this many out at once
    int32 cooldown;     // frames between throws
    int32 pose;         // frames the throw pose shows
    int32 x, y;         // where it starts, px from the player's centre (x: forward)
    int32 radius;       // its size for terrain
    int32 decel, returnSpeed, returnAccel, catchRadius; // boomerang (and a homing shot's way back)
    int32 seekSpeed, seekAccel, seekFrames;              // homing
    int32 rings;        // each throw costs this many rings (fewer: no throw)
    bool32 hasUp;       // "up": {speed, start_vy, pose_frame}: thrown with up held (Bean's high throw)
    int32 upSpeed, upStartVY, upPose;
    bool32 hasGround;   // "ground": {x, y, speed, start_vy}: thrown standing on the ground
    int32 groundX, groundY, groundSpeed, groundStartVY;
    bool32 aim;         // aimed with the d-pad (ground: 5 directions; air: 8)
    bool32 aimDown;     // "aim_down" false: never aimed down
    bool32 aimFrames;   // its art frame is its aim's (0 level, 1 forward-up, 2 up, 3 forward-down, 4 down), held
    bool32 aimPose;     // the throw pose shows its aim's frame
    bool32 autofire;    // thrown every cooldown while Y is held
    bool32 cycle;       // each throw shows the next art frame, held
    bool32 carry;       // the player's forward speed added (unaimed)
    bool32 bothWays;    // a pair each throw, one each way
    bool32 downOnly;    // "input" "down": down + Y
    bool32 upOnly;      // "input" "up": up + Y
    bool32 onSlam;      // "input" "slam": thrown by the Hammer Drop's landing, one each way, not with Y (Bark's shockwaves:
                        // motion "ground", along the floor gripped to it)
    bool32 onCharge;    // "input" "charge" (a second shot): Y held charges it; letting go of a full charge throws it (Omega's
    int32 chargeStart;  // Flame Blast, Mega Man's Charge Shot): the flash from chargeStart frames held, full at chargeFull;
    int32 chargeFull;   // "charge_wait": not full while the shared cooldown runs
    bool32 chargeWait;
    bool32 onGrab;      // "input" "grab": thrown only by Silver's Psychokinesis (ManiaPsycho.h), never by Y itself
    bool32 pierce;     // a hit doesn't end it
    bool32 terrain;     // walls, floors and ceilings end it (false: nothing does)
    char sound[64];     // Data/SoundFX path ("": silent)
} ShotData;

static void ShotDefaults(ShotData *s)
{
    memset(s, 0, sizeof(*s));
    s->speed       = 0x40000;
    s->maxFall     = 0x80000;
    s->lifetime    = 180;
    s->maxAlive    = 1;
    s->radius      = 8;
    s->decel       = 0x4000;
    s->returnSpeed = 0xA0000;
    s->returnAccel = 0x4000;
    s->catchRadius = 16;
    s->seekSpeed   = 0x58000;
    s->seekAccel   = 0x8000;
    s->seekFrames  = 20;
    s->upPose      = -1;
    s->aimDown     = true;
    s->carry       = true;
    s->terrain     = true;
    s->chargeStart = 30;
    s->chargeFull  = 72;
}

// A number field within [lo, hi] (else the default kept, logged)
static void ShotInt(const JsonNode *v, const char *name, int32 *at, int32 lo, int32 hi, const char *folder, const char *what)
{
    const JsonNode *n = Json_Get(v, name);
    if (!n || n->type == JSON_NULL)
        return;
    if (n->type == JSON_NUMBER && n->number >= lo && n->number <= hi)
        *at = (int32)n->number;
    else
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: %s.%s wrong type or out of range, default kept", folder, what, name);
}

static void ShotBool(const JsonNode *v, const char *name, bool32 *at)
{
    const JsonNode *n = Json_Get(v, name);
    if (n && n->type == JSON_BOOL)
        *at = n->number != 0;
}

static void ReadShot(const JsonNode *v, ShotData *out, const char *folder, const char *what)
{
    ShotDefaults(out);
    if (!v || v->type != JSON_OBJECT)
        return;
    static const char *const NAMES[] = { "none", "bounce", "straight", "boomerang", "homing", "drop", "dip", "ground" };
    const char *m = Json_String(Json_Get(v, "motion"), "");
    int32 motion  = -1;
    for (int32 i = 1; i < 8; ++i)
        if (strcmp(m, NAMES[i]) == 0)
            motion = i;
    const char *input = Json_String(Json_Get(v, "input"), "y");
    bool32 slam = strcmp(input, "slam") == 0;
    if (motion < 0 || (motion == SHOT_GROUND) != slam) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: %s: motion \"%s\" / input \"%s\" isn't in the Mania mod yet: no %s", folder, what, m, input,
                      what);
        return;
    }
    out->motion = motion;
    ShotInt(v, "speed", &out->speed, 0, 0x200000, folder, what);
    ShotInt(v, "start_vy", &out->startVY, -0x200000, 0x200000, folder, what);
    ShotInt(v, "gravity", &out->gravity, -0x20000, 0x20000, folder, what);
    ShotInt(v, "bounce", &out->bounce, -0x200000, 0, folder, what);
    ShotInt(v, "max_fall", &out->maxFall, 0, 0x200000, folder, what);
    ShotInt(v, "lifetime", &out->lifetime, 1, 3600, folder, what);
    ShotInt(v, "max_alive", &out->maxAlive, 1, 8, folder, what);
    ShotInt(v, "cooldown", &out->cooldown, 0, 600, folder, what);
    ShotInt(v, "pose", &out->pose, 0, 120, folder, what);
    ShotInt(v, "x", &out->x, -64, 64, folder, what);
    ShotInt(v, "y", &out->y, -64, 64, folder, what);
    ShotInt(v, "radius", &out->radius, 1, 32, folder, what);
    ShotInt(v, "decel", &out->decel, 1, 0x100000, folder, what);
    ShotInt(v, "return_speed", &out->returnSpeed, 0x1000, 0x200000, folder, what);
    ShotInt(v, "return_accel", &out->returnAccel, 1, 0x100000, folder, what);
    ShotInt(v, "catch", &out->catchRadius, 1, 64, folder, what);
    ShotInt(v, "seek_speed", &out->seekSpeed, 0x1000, 0x200000, folder, what);
    ShotInt(v, "seek_accel", &out->seekAccel, 1, 0x100000, folder, what);
    ShotInt(v, "seek_frames", &out->seekFrames, 1, 600, folder, what);
    ShotInt(v, "rings", &out->rings, 0, 99, folder, what);
    ShotInt(v, "charge_start", &out->chargeStart, 1, 3600, folder, what);
    ShotInt(v, "charge_full", &out->chargeFull, 1, 3600, folder, what);
    ShotBool(v, "charge_wait", &out->chargeWait);
    const JsonNode *up = Json_Get(v, "up");
    if (up && up->type == JSON_OBJECT) {
        out->hasUp     = true;
        out->upSpeed   = out->speed;
        out->upStartVY = out->startVY;
        ShotInt(up, "speed", &out->upSpeed, 0, 0x200000, folder, what);
        ShotInt(up, "start_vy", &out->upStartVY, -0x200000, 0x200000, folder, what);
        ShotInt(up, "pose_frame", &out->upPose, 0, 255, folder, what);
    }
    const JsonNode *gr = Json_Get(v, "ground");
    if (gr && gr->type == JSON_OBJECT) {
        out->hasGround     = true;
        out->groundX       = out->x;
        out->groundY       = out->y;
        out->groundSpeed   = out->speed;
        out->groundStartVY = out->startVY;
        ShotInt(gr, "x", &out->groundX, -64, 64, folder, what);
        ShotInt(gr, "y", &out->groundY, -64, 64, folder, what);
        ShotInt(gr, "speed", &out->groundSpeed, 0, 0x200000, folder, what);
        ShotInt(gr, "start_vy", &out->groundStartVY, -0x200000, 0x200000, folder, what);
    }
    ShotBool(v, "aim", &out->aim);
    ShotBool(v, "aim_down", &out->aimDown);
    ShotBool(v, "aim_frames", &out->aimFrames);
    ShotBool(v, "aim_pose", &out->aimPose);
    ShotBool(v, "autofire", &out->autofire);
    ShotBool(v, "cycle", &out->cycle);
    ShotBool(v, "carry", &out->carry);
    ShotBool(v, "both_ways", &out->bothWays);
    ShotBool(v, "pierce", &out->pierce);
    ShotBool(v, "terrain", &out->terrain);
    out->downOnly = strcmp(input, "down") == 0;
    out->upOnly   = strcmp(input, "up") == 0;
    out->onSlam   = slam;
    out->onCharge = strcmp(input, "charge") == 0;
    out->onGrab   = strcmp(input, "grab") == 0;
    const char *sound = Json_String(Json_Get(v, "sound"), "");
    snprintf(out->sound, sizeof(out->sound), "%s", sound);
}

// The objects a shot can hit: every class whose update checks players with the game's attack rules, so a stand-in
// player there (NoSwapMania.c "shots": StandIn) meets the game's own code. Taken from the decompilation's sources
// (SonicMania/Objects): every object calling Player_CheckBadnikBreak (the badniks, HIT_BADNIK) or Player_CheckBossHit (the
// bosses, HIT_BOSS: a wider reach), ItemBox (HIT_ITEMBOX), and a few breakables / boss parts that check
// Player_CheckBadnikTouch or Player_CheckAttacking themselves (a shot sets off a mine or a switch as Amy's hammer does).
// Not here on purpose: bumpers, springs, rings, checkpoints, signposts, special rings, ice (anything a stand-in player
// would set off for the real one).
enum { HIT_NONE, HIT_BADNIK, HIT_BOSS, HIT_ITEMBOX };
typedef struct {
    const char *name;
    uint8 kind;
} HitClass;
static const HitClass HIT_CLASSES[] = {
    { "ItemBox", HIT_ITEMBOX },
    // badniks (Player_CheckBadnikBreak)
    { "Aquis", HIT_BADNIK }, { "Armadiloid", HIT_BADNIK }, { "BallHog", HIT_BADNIK }, { "Batbot", HIT_BADNIK },
    { "Batbrain", HIT_BADNIK }, { "Blaster", HIT_BADNIK }, { "Blastoid", HIT_BADNIK }, { "Bloominator", HIT_BADNIK },
    { "Bubbler", HIT_BADNIK }, { "Buggernaut", HIT_BADNIK }, { "Bumpalo", HIT_BADNIK }, { "BuzzBomber", HIT_BADNIK },
    { "Cactula", HIT_BADNIK }, { "Canista", HIT_BADNIK }, { "Caterkiller", HIT_BADNIK }, { "CaterkillerJr", HIT_BADNIK },
    { "Chopper", HIT_BADNIK }, { "Clucker", HIT_BADNIK }, { "Crabmeat", HIT_BADNIK }, { "Dango", HIT_BADNIK },
    { "Dragonfly", HIT_BADNIK }, { "FBZTrash", HIT_BADNIK }, { "Fireworm", HIT_BADNIK }, { "FlasherMKII", HIT_BADNIK },
    { "Grabber", HIT_BADNIK }, { "Hatterkiller", HIT_BADNIK }, { "Hotaru", HIT_BADNIK }, { "HotaruMKII", HIT_BADNIK },
    { "IceBomba", HIT_BADNIK }, { "Jawz", HIT_BADNIK }, { "Jellygnite", HIT_BADNIK }, { "JuggleSaw", HIT_BADNIK },
    { "Kabasira", HIT_BADNIK }, { "Kanabun", HIT_BADNIK }, { "MechaBu", HIT_BADNIK }, { "MegaChopper", HIT_BADNIK },
    { "MicDrop", HIT_BADNIK }, { "MonkeyDude", HIT_BADNIK }, { "Motobug", HIT_BADNIK }, { "Newtron", HIT_BADNIK },
    { "Octus", HIT_BADNIK }, { "Orbinaut", HIT_BADNIK }, { "PohBee", HIT_BADNIK }, { "Pointdexter", HIT_BADNIK },
    { "Rattlekiller", HIT_BADNIK }, { "Redz", HIT_BADNIK }, { "Rexon", HIT_BADNIK }, { "Rhinobot", HIT_BADNIK },
    { "RollerMKII", HIT_BADNIK }, { "Scarab", HIT_BADNIK }, { "SentryBug", HIT_BADNIK }, { "Shutterbug", HIT_BADNIK },
    { "Sol", HIT_BADNIK }, { "Spiny", HIT_BADNIK }, { "Splats", HIT_BADNIK }, { "Stegway", HIT_BADNIK },
    { "Sweep", HIT_BADNIK }, { "Technosqueek", HIT_BADNIK }, { "Toxomister", HIT_BADNIK }, { "Tubinaut", HIT_BADNIK },
    { "TurboSpiker", HIT_BADNIK }, { "TurboTurtle", HIT_BADNIK }, { "Vultron", HIT_BADNIK }, { "WallCrawl", HIT_BADNIK },
    { "Wisp", HIT_BADNIK }, { "Woodrow", HIT_BADNIK },
    // breakables that take the attack rules (Player_CheckBadnikTouch / Player_CheckAttacking)
    { "Mine", HIT_BADNIK }, { "Pinata", HIT_BADNIK }, { "FlowerPod", HIT_BADNIK }, { "TurretSwitch", HIT_BADNIK },
    { "DoorTrigger", HIT_BADNIK },
    // bosses and minibosses (Player_CheckBossHit), and boss parts with their own hit checks
    { "AmoebaDroid", HIT_BOSS }, { "BigSqueeze", HIT_BOSS }, { "CrimsonEye", HIT_BOSS }, { "DBTower", HIT_BOSS },
    { "DDWrecker", HIT_BOSS }, { "DERobot", HIT_BOSS }, { "Drillerdroid", HIT_BOSS }, { "DrillerdroidO", HIT_BOSS },
    { "ERZKing", HIT_BOSS }, { "ERZMystic", HIT_BOSS }, { "ERZShinobi", HIT_BOSS }, { "Gachapandora", HIT_BOSS },
    { "GigaMetal", HIT_BOSS }, { "HeavyKing", HIT_BOSS }, { "HeavyMystic", HIT_BOSS }, { "HeavyRider", HIT_BOSS },
    { "HeavyShinobi", HIT_BOSS }, { "HotaruHiWatt", HIT_BOSS }, { "KleptoMobile", HIT_BOSS }, { "LaundroMobile", HIT_BOSS },
    { "MegaOctus", HIT_BOSS }, { "MetalSonic", HIT_BOSS }, { "MeterDroid", HIT_BOSS }, { "PhantomEgg", HIT_BOSS },
    { "PhantomKing", HIT_BOSS }, { "PhantomMystic", HIT_BOSS }, { "PhantomShinobi", HIT_BOSS }, { "RockDrill", HIT_BOSS },
    { "Shiversaw", HIT_BOSS }, { "Tuesday", HIT_BOSS }, { "UberCaterkiller", HIT_BOSS }, { "WeatherMobile", HIT_BOSS },
    { "SilverSonic", HIT_BOSS }, { "ERZGunner", HIT_BOSS }, { "PhantomGunner", HIT_BOSS }, { "SpiderMobile", HIT_BOSS },
    { "EggPistonsMKII", HIT_BOSS }, { "HeavyGunner", HIT_BOSS }, { "MSHologram", HIT_BOSS },
};
#define HIT_CLASS_COUNT (sizeof(HIT_CLASSES) / sizeof(HIT_CLASSES[0]))

#endif // MANIA_SHOT_H
