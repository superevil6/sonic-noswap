// NoSwapMania: the package data of Gilius' pot magic (tools/pot_magic.py; the runtime is ManiaPotMagic.h). The S3&K
// DLL's field names and values (gen_s3k_header.ability_fields, from pot_magic.s3k_fields: the JSON's "abilities" lists
// only the ones not at their default, the same defaults here). Included once, by ManiaMoreData.h (MoreData keeps a
// PotsData).
#ifndef MANIA_POT_MAGIC_DATA_H
#define MANIA_POT_MAGIC_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

#define POTS_FLASH_MAX (32) // (pot_magic.FLASH_MAX)
#define POTS_LEVELS    (7)  // (pot_magic.LEVELS_MAX)

// name, default (pot_magic.s3k_fields')
#define POTS_FIELDS(X)                                                                                                          \
    X(potMagic, 0) X(potsMax, 0) X(potsCast, 0) X(potsCastTicks, 1) X(potsHit, 0) X(potsGap, 0) X(potsFirst, 0)                \
    X(potsShake, 0) X(potsFlashCount, 0)

#define POTS_LISTS(X) X(potsFlash, POTS_FLASH_MAX) X(potsLevelX, POTS_LEVELS) X(potsLevelY, POTS_LEVELS)                       \
    X(potsLevelPulses, POTS_LEVELS) X(potsLevelRocks, POTS_LEVELS)

#define POTS_SOUNDS(X) X(potsSound) X(potsCastSound) X(potsQuakeSound)

typedef struct {
#define X(name, def) int32 name;
    POTS_FIELDS(X)
#undef X
#define X(name, n) int32 name[n];
    POTS_LISTS(X)
#undef X
#define X(name) char name[64];
    POTS_SOUNDS(X)
#undef X
} PotsData;

static void ReadPots(const JsonNode *ab, PotsData *out)
{
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    POTS_FIELDS(X)
#undef X
#define X(name, n)                                                                                                              \
    {                                                                                                                           \
        int32 k = 0;                                                                                                            \
        const JsonNode *list = Json_Get(ab, #name);                                                                             \
        for (const JsonNode *e = list && list->type == JSON_ARRAY ? list->child : NULL; e && k < n; e = e->next)               \
            out->name[k++] = Json_Int(e, 0);                                                                                    \
    }
    POTS_LISTS(X)
#undef X
#define X(name) snprintf(out->name, sizeof(out->name), "%s", Json_String(Json_Get(ab, #name), ""));
    POTS_SOUNDS(X)
#undef X
    if (out->potsFlashCount > POTS_FLASH_MAX)
        out->potsFlashCount = POTS_FLASH_MAX;
    if (out->potsMax > POTS_LEVELS)
        out->potsMax = POTS_LEVELS;
    if (out->potsCastTicks < 1)
        out->potsCastTicks = 1;
}

#endif // MANIA_POT_MAGIC_DATA_H
