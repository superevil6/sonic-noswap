// NoSwapMania: the package data of the moves ported with the guest batch (Sticks, Mega Man, Ray Poward, Sparkster;
// the runtime is ManiaGuest.h): the S3&K DLL's field names and values (gen_s3k_header.ability_fields, from abilities.py;
// the JSON's "abilities" lists only those not at their default, the same defaults here). The Slide's numbers are the
// Puddle Slide's (puddle*: ManiaBatchData.h reads them into MoreData.batch). Kept by package folder (ReadGuest from
// LoadPackage), since the extras are sorted after loading. Included once, by NoSwapMania.c (after ManiaMoreData.h).
#ifndef MANIA_GUEST_DATA_H
#define MANIA_GUEST_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

// name, default (gen_s3k_header's)
#define GUEST_FIELDS(X)                                                                                                         \
    X(groundSlide, 0) X(slideRunning, 0)                                                                                        \
    X(rocketBurst, 0) X(rocketCharge, 0) X(rocketFrames, 0) X(rocketSpeed, 0) X(rocketDiag, 0) X(rocketSink, 0)               \
    X(rocketSpinFrames, 0) X(rocketSpinTicks, 1)

#define GUEST_SOUNDS(X) X(rocketChargeSound) X(rocketSound)

typedef struct {
    char folder[64];
#define X(name, def) int32 name;
    GUEST_FIELDS(X)
#undef X
#define X(name) char name[64];
    GUEST_SOUNDS(X)
#undef X
} GuestData;

#define GUEST_MAX (64) // (EXTRA_MAX)
static GuestData g_guestData[GUEST_MAX];
static int32 g_guestDataCount = 0;

static void ReadGuest(const JsonNode *ab, const char *folder)
{
    if (g_guestDataCount >= GUEST_MAX)
        return;
    GuestData *out = &g_guestData[g_guestDataCount];
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    GUEST_FIELDS(X)
#undef X
#define X(name) snprintf(out->name, sizeof(out->name), "%s", Json_String(Json_Get(ab, #name), ""));
    GUEST_SOUNDS(X)
#undef X
    if (!out->groundSlide && !out->rocketBurst)
        return; // (none of these moves: nothing kept)
    snprintf(out->folder, sizeof(out->folder), "%s", folder);
    if (out->rocketSpinTicks < 1)
        out->rocketSpinTicks = 1;
    g_guestDataCount++;
}

// The package's crossover data (NULL: none of these moves)
static const GuestData *GuestOf(const char *folder)
{
    for (int32 i = 0; i < g_guestDataCount; ++i)
        if (strcmp(g_guestData[i].folder, folder) == 0)
            return &g_guestData[i];
    return NULL;
}

#endif // MANIA_GUEST_DATA_H
