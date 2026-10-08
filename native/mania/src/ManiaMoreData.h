// NoSwapMania: the package data of the moves ported with Omega, Marine, Mephiles and Emerl's copy heads (the runtime is
// ManiaMore.h). Their number fields are in NoSwapMania.c's ABILITY_FIELDS (the S3&K DLL's names, from
// gen_s3k_header.ability_fields); here the lists and texts:
//   - sinkFrames / sinkUnder (abilities.py sink: Mephiles' Shadow Sink, slot 47's frames sinking / while under);
//   - anchorSound / latchSound (anchor_throw: Marine), sinkSound;
//   - copy heads (the JSON's "copy_heads": build_mania_art.py COPY_HEADS_MANIA's offset, count and sets: Emerl);
//   - the charge flash (the JSON's "charge_palettes": Omega's Flame Blast; per phase charge1 / charge2a / charge2b, the
//     Mania palette slots of his own colours and what they show then).
// Included once, by NoSwapMania.c (after ManiaShot.h).
#ifndef MANIA_MORE_DATA_H
#define MANIA_MORE_DATA_H

#include "JsonLite.h"
#include "ManiaBatchData.h" // (the Sonic-hosted batch's moves: ManiaBatch.h)
#include "ManiaHostData.h"  // (the host, and the Tails / Knuckles-hosted extras' moves: ManiaHost.h)
#include "ManiaAmyData.h"   // (Amy's moves: ManiaAmy.h)
#include "ManiaCrossData.h" // (Ristar, Headdy, John Morris, Ecco: ManiaCross.h)
#include "ManiaNinjutsuData.h" // (Joe Musashi's Ninjutsu: ManiaNinjutsu.h)
#include "ManiaPotMagicData.h" // (Gilius' pot magic: ManiaPotMagic.h)

#include <stdio.h>
#include <string.h>

#define SINK_FRAMES_MAX (16) // (gen_s3k_header.SINK_MAX / SINK_UNDER_MAX)
#define SINK_UNDER_MAX  (8)
#define CHARGE_PAL_MAX  (16)

typedef struct {
    int32 sinkFrames[SINK_FRAMES_MAX];
    int32 sinkUnder[SINK_UNDER_MAX];
    char anchorSound[64];
    char latchSound[64];
    char sinkSound[64];
    char psychoSound[64]; // psycho_grab (Silver's Psychokinesis: ManiaPsycho.h): the catch's
    int32 copyOffset, copyCount, copySets; // copy heads: set m's copy of the list's k-th is offset + count * m + k (sets 0: none)
    int32 chargeCount[3];
    uint8 chargeSlot[3][CHARGE_PAL_MAX];
    color chargeColour[3][CHARGE_PAL_MAX];
    BatchData batch; // the Sonic-hosted batch's moves (ManiaBatchData.h)
    HostData host;   // who it plays on, and the Tails / Knuckles-hosted moves (ManiaHostData.h)
    AmyData amy;     // Amy's moves (ManiaAmyData.h; on: the package's "amy" section)
    CrossData cross; // Ristar's, Headdy's, John Morris' and Ecco's moves (ManiaCrossData.h)
    NinjaData ninja; // Joe Musashi's Ninjutsu (ManiaNinjutsuData.h)
    PotsData pots;   // Gilius' pot magic (ManiaPotMagicData.h)
} MoreData;

static void MoreList(const JsonNode *array, int32 *out, int32 max)
{
    int32 k = 0;
    for (const JsonNode *n = array && array->type == JSON_ARRAY ? array->child : NULL; n && k < max; n = n->next) out[k++] = Json_Int(n, 0);
}

static void ReadMore(const JsonNode *mania, const JsonNode *ab, MoreData *out, const char *folder)
{
    memset(out, 0, sizeof(*out));
    ReadBatch(mania, ab, &out->batch, folder);
    ReadHost(mania, ab, &out->host, folder);
    ReadAmy(mania, &out->amy);
    ReadCrossMoves(mania, ab, &out->cross, folder);
    ReadNinja(ab, &out->ninja);
    ReadPots(ab, &out->pots);
    MoreList(Json_Get(ab, "sinkFrames"), out->sinkFrames, SINK_FRAMES_MAX);
    MoreList(Json_Get(ab, "sinkUnder"), out->sinkUnder, SINK_UNDER_MAX);
    snprintf(out->anchorSound, sizeof(out->anchorSound), "%s", Json_String(Json_Get(ab, "anchorSound"), ""));
    snprintf(out->latchSound, sizeof(out->latchSound), "%s", Json_String(Json_Get(ab, "latchSound"), ""));
    snprintf(out->sinkSound, sizeof(out->sinkSound), "%s", Json_String(Json_Get(ab, "sinkSound"), ""));
    snprintf(out->psychoSound, sizeof(out->psychoSound), "%s", Json_String(Json_Get(ab, "psychoSound"), ""));
    const JsonNode *heads = Json_Get(mania, "copy_heads");
    if (heads && heads->type == JSON_OBJECT) {
        out->copyOffset = Json_Int(Json_Get(heads, "offset"), 0);
        out->copyCount  = Json_Int(Json_Get(heads, "count"), 0);
        out->copySets   = Json_Int(Json_Get(heads, "sets"), 0);
        if (out->copyOffset <= 0 || out->copyCount <= 0 || out->copySets <= 0 || out->copyOffset + out->copyCount * out->copySets > 0x100) {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: \"copy_heads\" doesn't add up: no copy heads", folder);
            out->copySets = 0;
        }
    }
    const JsonNode *pals = Json_Get(mania, "charge_palettes");
    int32 phase = 0;
    for (const JsonNode *p = pals && pals->type == JSON_ARRAY ? pals->child : NULL; p && phase < 3; p = p->next, ++phase) {
        for (const JsonNode *n = p->type == JSON_OBJECT ? p->child : NULL; n && out->chargeCount[phase] < CHARGE_PAL_MAX; n = n->next) {
            int32 slot = n->key ? atoi(n->key) : 0, colour = Json_Colour(n);
            if (slot <= 0 || slot > 255 || colour < 0)
                continue;
            out->chargeSlot[phase][out->chargeCount[phase]]     = (uint8)slot;
            out->chargeColour[phase][out->chargeCount[phase]++] = (color)colour;
        }
    }
}

#endif // MANIA_MORE_DATA_H
