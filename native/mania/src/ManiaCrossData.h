// NoSwapMania: the package data of the crossover moves (Ristar, Dynamite Headdy, John Morris, Ecco; the runtime is
// ManiaCross.h). The S3&K DLL's field names and values (gen_s3k_header.ability_fields, from abilities.py: the JSON's
// "abilities" lists only the ones not at their default, the same defaults here), plus John's sub-weapons (the JSON's
// "swap_shots": monitor_swap's shots, each with its flames' animation and lifetime; build_mania_art.py build_shot).
// The numbers the mod already reads elsewhere (reelSpeed / reelFrames / latchRange: NoSwapMania.c ABILITY_FIELDS; the
// melee's; latchSound: ManiaMoreData.h) stay there. Included once, by ManiaMoreData.h (MoreData keeps a CrossData),
// which NoSwapMania.c includes after ManiaShot.h (ReadShot).
// (Not the Sticks / Mega Man / Ray Poward / Sparkster batch: that one is ManiaGuest.h / ManiaGuestData.h.)
#ifndef MANIA_CROSS_DATA_H
#define MANIA_CROSS_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

#define CROSS_HEAD_MAX (8) // gen_s3k_header.HEAD_VARIANT_MAX
#define CROSS_SWAP_MAX (8) // monitor_swap entries

// name, default (gen_s3k_header's)
#define CROSS_FIELDS(X)                                                                                                         \
    /* Ristar's Grab, hang and Meteor Strike (tools/star_grab.py) */                                                            \
    X(starGrab, 0) X(grabStep, 0) X(grabFrames, 0) X(retractFrames, 1) X(yankSpeed, 0) X(yankFrames, 0) X(yankRange, 0)       \
    X(bounceY, 0) X(bounceX, 0) X(climbSpeed, 0) X(hangHop, 0) X(hangPush, 0) X(windupShow, 0) X(windupFull, 0)               \
    X(meteorSpeed, 0) X(meteorFrames, 0)                                                                                        \
    /* Headdy's Head Throw (tools/head_throw.py) */                                                                             \
    X(headThrow, 0) X(headVariants, 0)                                                                                          \
    /* John's whip poses (melee_whip) and monitor_swap */                                                                      \
    X(shotWhip, 0) X(swapCount, 0) X(swapIcon, 0)                                                                               \
    /* Ecco's free swim (native/src/EccoSwim.h) */                                                                              \
    X(freeSwim, 0) X(swimSpeed, 0) X(swimAccel, 0) X(swimDrag, 0) X(swimTurn, 0) X(swimDirs, 1) X(swimCycle, 1)               \
    X(swimTicks, 1) X(ramFrames, 0) X(ramSpeed, 0) X(ramCooldown, 0) X(ramCycle, 0) X(leapFrames, 0) X(leapTicks, 1)

#define CROSS_SOUNDS(X) X(grabSound) X(meteorSound) X(headSound) X(swapSound) X(ramSound)

typedef struct {
#define X(name, def) int32 name;
    CROSS_FIELDS(X)
#undef X
#define X(name) char name[64];
    CROSS_SOUNDS(X)
#undef X
    int32 headStep[CROSS_HEAD_MAX], headFrames[CROSS_HEAD_MAX]; // per head variant (0: his own head)
    int32 swapShotCount;                                        // John's sub-weapons (monitor_swap's swap_shots)
    ShotData swapShot[CROSS_SWAP_MAX];
    int32 burnAnim[CROSS_SWAP_MAX]; // a burning one's flames: its Shot.bin animation (-1: none) and their lifetime
    int32 burnLifetime[CROSS_SWAP_MAX];
} CrossData;

static void CrossList(const JsonNode *array, int32 *out, int32 max)
{
    int32 k = 0;
    for (const JsonNode *n = array && array->type == JSON_ARRAY ? array->child : NULL; n && k < max; n = n->next) out[k++] = Json_Int(n, 0);
}

static void ReadCrossMoves(const JsonNode *mania, const JsonNode *ab, CrossData *out, const char *folder)
{
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    CROSS_FIELDS(X)
#undef X
#define X(name) snprintf(out->name, sizeof(out->name), "%s", Json_String(Json_Get(ab, #name), ""));
    CROSS_SOUNDS(X)
#undef X
    CrossList(Json_Get(ab, "headStep"), out->headStep, CROSS_HEAD_MAX);
    CrossList(Json_Get(ab, "headFrames"), out->headFrames, CROSS_HEAD_MAX);
    if (out->headVariants > CROSS_HEAD_MAX)
        out->headVariants = CROSS_HEAD_MAX;
    if (out->headThrow && (out->headVariants < 1 || out->headStep[0] <= 0 || out->headFrames[0] <= 0)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: a Head Throw without its head's numbers: no throw", folder);
        out->headThrow = 0;
    }
    if (out->retractFrames < 1)
        out->retractFrames = 1;
    if (out->swimDirs < 1)
        out->swimDirs = 1;
    if (out->swimCycle < 1)
        out->swimCycle = 1;
    if (out->swimTicks < 1)
        out->swimTicks = 1;
    if (out->leapTicks < 1)
        out->leapTicks = 1;
    const JsonNode *swaps = Json_Get(mania, "swap_shots");
    for (const JsonNode *n = swaps && swaps->type == JSON_ARRAY ? swaps->child : NULL; n && out->swapShotCount < CROSS_SWAP_MAX; n = n->next) {
        int32 k = out->swapShotCount++;
        ReadShot(n, &out->swapShot[k], folder, "swap_shots");
        out->burnAnim[k]     = Json_Int(Json_Get(n, "burn_anim"), -1);
        out->burnLifetime[k] = Json_Int(Json_Get(n, "burn_lifetime"), 0);
    }
    if (out->swapShotCount > 0 && out->swapShot[0].motion == SHOT_NONE)
        out->swapShotCount = 0; // (its first can't be thrown here: none)
}

#endif // MANIA_CROSS_DATA_H
