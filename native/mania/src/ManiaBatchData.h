// NoSwapMania: the package data of the moves ported with the Sonic-hosted batch (Robotnik, Max, Tikal, Trip, Jet, Chaos,
// Tails Doll, Heavy, Honey; the runtime is ManiaBatch.h). The S3&K DLL's field names and values (gen_s3k_header.
// ability_fields, from abilities.py: the JSON's "abilities" lists only the ones not at their default, the same defaults
// here), plus the Shine Spark's glow (the JSON's "spark_glow": per level, Mania slot -> colour; build_mania_art.py).
// The moves' numbers the mod already reads (hover*, reel*, latchRange, grapple Hop / Forward) stay in NoSwapMania.c's
// ABILITY_FIELDS. Included once, by ManiaMoreData.h (MoreData keeps a BatchData).
#ifndef MANIA_BATCH_DATA_H
#define MANIA_BATCH_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

#define BATCH_TIP_MAX    (8)  // gen_s3k_header.GRAPPLE_MAX
#define BATCH_PUDDLE_MAX (40) // gen_s3k_header.PUDDLE_MAX
#define BATCH_GLOW_MAX   (8)

// name, default (gen_s3k_header's)
#define BATCH_FIELDS(X)                                                                                                         \
    X(bombJump, 0) X(bombFrames, 0) X(blastFrames, 0) X(blastTicks, 1) X(bombLaunch, 0) X(rideSpeed, 0) X(rideRise, 0)         \
    X(earGrapple, 0) X(grappleY, 0) X(grappleFrames, 0) X(snapFrames, 1) X(grappleRefill, 0) X(grappleCooldown, 0)             \
    X(spiritFlight, 0) X(spiritTransform, 0) X(spiritTicks, 1) X(spiritFrames, 0) X(spiritSpeed, 0) X(spiritDiag, 0)           \
    X(spiritAccel, 0)                                                                                                           \
    X(wallCling, 0) X(clingFrames, 0) X(clingHold, 0) X(clingSlide, 0) X(climbSpeed, 0) X(wallJumpX, 0) X(wallJumpY, 0)        \
    X(clingLock, 0) X(ledgeHop, 0) X(ledgeForward, 0) X(wallX, 12) X(wallY, -2)                                                 \
    X(extremeGear, 0) X(gearSpeed, 0) X(gearTop, 0) X(gearAccel, 0) X(gearRecover, 0) X(gearBrake, 0) X(gearTurn, 0)           \
    X(gearSink, 0) X(gearLift, 0) X(gearRise, 0) X(gearLiftFrames, 0) X(gearFrames, 0)                                         \
    X(puddleSlide, 0) X(puddleDrop, 0) X(puddleSpeed, 0) X(puddleTicks, 1) X(puddleMove, 0) X(puddleSteps, 0)                  \
    X(charge, 0) X(chargeAccel, 0) X(chargeGain, 0) X(chargeTop, 0) X(chargeFriction, 0) X(chargeBrake, 0) X(chargeStride, 1) \
    X(chargeShove, 0) X(sparkStore, 0) X(sparkSpeed, 0) X(sparkDiag, 0) X(sparkSkid, 0) X(sparkSkidFrames, 0)                  \
    X(spinAttack, 0) X(spinFrames, 0) X(spinCooldown, 0) X(spinTicks, 1) X(spinGravity, 256) X(spinBounce, 0)                  \
    X(spinBounceX, 0)                                                                                                           \
    X(phaseWarp, 0) X(warpRange, 0) X(warpVanish, 0) X(warpGone, 0) X(warpAppear, 0)

#define BATCH_SOUNDS(X) X(rideSound) X(blastSound) X(gearSound) X(puddleSound) X(sparkStoreSound) X(sparkSound) X(spinSound) X(warpSound)

typedef struct {
#define X(name, def) int32 name;
    BATCH_FIELDS(X)
#undef X
#define X(name) char name[64];
    BATCH_SOUNDS(X)
#undef X
    int32 tipX[BATCH_TIP_MAX], tipY[BATCH_TIP_MAX]; // the ear's tip per frame, px from his centre facing right
    int32 puddleFrames[BATCH_PUDDLE_MAX];           // the puddle's frame per step
    int32 glowCount[3];                             // the Shine Spark's glow, per level: Mania slot -> colour
    uint8 glowSlot[3][BATCH_GLOW_MAX];
    color glowColour[3][BATCH_GLOW_MAX];
} BatchData;

static void BatchList(const JsonNode *array, int32 *out, int32 max)
{
    int32 k = 0;
    for (const JsonNode *n = array && array->type == JSON_ARRAY ? array->child : NULL; n && k < max; n = n->next) out[k++] = Json_Int(n, 0);
}

static void ReadBatch(const JsonNode *mania, const JsonNode *ab, BatchData *out, const char *folder)
{
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    BATCH_FIELDS(X)
#undef X
#define X(name) snprintf(out->name, sizeof(out->name), "%s", Json_String(Json_Get(ab, #name), ""));
    BATCH_SOUNDS(X)
#undef X
    BatchList(Json_Get(ab, "tipX"), out->tipX, BATCH_TIP_MAX);
    BatchList(Json_Get(ab, "tipY"), out->tipY, BATCH_TIP_MAX);
    BatchList(Json_Get(ab, "puddleFrames"), out->puddleFrames, BATCH_PUDDLE_MAX);
    if (out->grappleFrames > BATCH_TIP_MAX)
        out->grappleFrames = BATCH_TIP_MAX;
    if (out->puddleSteps > BATCH_PUDDLE_MAX)
        out->puddleSteps = BATCH_PUDDLE_MAX;
    if (out->blastTicks < 1)
        out->blastTicks = 1;
    if (out->snapFrames < 1)
        out->snapFrames = 1;
    if (out->spiritTicks < 1)
        out->spiritTicks = 1;
    if (out->puddleTicks < 1)
        out->puddleTicks = 1;
    if (out->chargeStride < 1)
        out->chargeStride = 1;
    if (out->spinTicks < 1)
        out->spinTicks = 1;
    if (out->earGrapple && out->grappleFrames < 1) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: an Ear Grapple with no tips: no grapple", folder);
        out->earGrapple = 0;
    }
    const JsonNode *glow = Json_Get(mania, "spark_glow");
    int32 level = 0;
    for (const JsonNode *g = glow && glow->type == JSON_ARRAY ? glow->child : NULL; g && level < 3; g = g->next, ++level) {
        for (const JsonNode *n = g->type == JSON_OBJECT ? g->child : NULL; n && out->glowCount[level] < BATCH_GLOW_MAX; n = n->next) {
            int32 slot = n->key ? atoi(n->key) : 0, colour = Json_Colour(n);
            if (slot <= 0 || slot > 255 || colour < 0)
                continue;
            out->glowSlot[level][out->glowCount[level]]     = (uint8)slot;
            out->glowColour[level][out->glowCount[level]++] = (color)colour;
        }
    }
}

#endif // MANIA_BATCH_DATA_H
