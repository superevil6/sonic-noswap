// NoSwapMania: the package data of Joe Musashi's Ninjutsu (tools/ninjutsu.py; the runtime is ManiaNinjutsu.h). The S3&K
// DLL's field names and values (gen_s3k_header.ability_fields, from ninjutsu.s3k_fields: the JSON's "abilities" lists
// only the ones not at their default, the same defaults here). Included once, by ManiaMoreData.h (MoreData keeps a
// NinjaData).
#ifndef MANIA_NINJUTSU_DATA_H
#define MANIA_NINJUTSU_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

#define NINJA_FLASH_MAX (32) // (gen_s3k_header.FLASH_MAX)

// name, default (ninjutsu.s3k_fields')
#define NINJA_FIELDS(X)                                                                                                         \
    X(ninjutsu, 0) X(ninjaKinds, 0) X(ninjaCast, 0) X(ninjaCastTicks, 1) X(ninjaMijin, 0) X(ninjaMijinTicks, 1)                \
    X(ninjaFushin, 0) X(ninjaFushinJump, 1000) X(ninjaKariuHit, 0) X(ninjaKariuFlashCount, 0) X(ninjaMijinHit, 0)              \
    X(ninjaMijinX, 0) X(ninjaMijinY, 0)

#define NINJA_SOUNDS(X) X(ninjaKariuSound) X(ninjaMijinSound) X(ninjaSound) X(ninjaCastSound)

typedef struct {
#define X(name, def) int32 name;
    NINJA_FIELDS(X)
#undef X
#define X(name) char name[64];
    NINJA_SOUNDS(X)
#undef X
    int32 ninjaKariuFlash[NINJA_FLASH_MAX];
} NinjaData;

static void ReadNinja(const JsonNode *ab, NinjaData *out)
{
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    NINJA_FIELDS(X)
#undef X
#define X(name) snprintf(out->name, sizeof(out->name), "%s", Json_String(Json_Get(ab, #name), ""));
    NINJA_SOUNDS(X)
#undef X
    const JsonNode *flash = Json_Get(ab, "ninjaKariuFlash");
    int32 k = 0;
    for (const JsonNode *n = flash && flash->type == JSON_ARRAY ? flash->child : NULL; n && k < NINJA_FLASH_MAX; n = n->next)
        out->ninjaKariuFlash[k++] = Json_Int(n, 0);
    if (out->ninjaKariuFlashCount > k)
        out->ninjaKariuFlashCount = k;
    if (out->ninjaCastTicks < 1)
        out->ninjaCastTicks = 1;
    if (out->ninjaMijinTicks < 1)
        out->ninjaMijinTicks = 1;
}

#endif // MANIA_NINJUTSU_DATA_H
