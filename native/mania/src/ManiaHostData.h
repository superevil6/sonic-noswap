// NoSwapMania: the package data of the Tails- and Knuckles-hosted extras (Cream, Charmy, Flicky on Tails; Rouge on
// Knuckles; the runtime is ManiaHost.h). The JSON's "host" (tools/build_mania_art.py: extras.py "base"), and the S3&K DLL's
// field names and values for their own moves (gen_s3k_header.ability_fields, from abilities.py; the JSON's "abilities" lists
// only the ones not at their default, the same defaults here). Included once, by ManiaMoreData.h (MoreData keeps a HostData).
#ifndef MANIA_HOST_DATA_H
#define MANIA_HOST_DATA_H

#include "JsonLite.h"

#include <stdio.h>
#include <string.h>

// name, default (gen_s3k_header's)
#define HOST_FIELDS(X)                                                                                                          \
    X(aimDashY, 0) X(batGlide, 0) X(glideSpeed, 1000) X(glideSink, 0) X(glideGravity, 0) X(treasureSense, 0) X(sensePause, 0)  \
    X(senseShow, 0) X(senseCooldown, 0) X(jewelThief, 0)

typedef struct {
    int32 id;    // the character it plays on: ID_SONIC, ID_TAILS or ID_KNUCKLES
    int32 index; // ... 0 Sonic, 1 Tails, 2 Knuckles (their order in the game's per-character lists)
#define X(name, def) int32 name;
    HOST_FIELDS(X)
#undef X
    char senseSound[64]; // Treasure Sense's "no signal" sound ("": none)
} HostData;

static void ReadHost(const JsonNode *mania, const JsonNode *ab, HostData *out, const char *folder)
{
    memset(out, 0, sizeof(*out));
    const char *host = Json_String(Json_Get(mania, "host"), "sonic"); // (a package from before hosting: Sonic's)
    if (strcmp(host, "tails") == 0) {
        out->id    = ID_TAILS;
        out->index = 1;
    }
    else if (strcmp(host, "knuckles") == 0) {
        out->id    = ID_KNUCKLES;
        out->index = 2;
    }
    else {
        if (strcmp(host, "sonic") != 0)
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: host \"%s\" isn't sonic, tails or knuckles: plays on Sonic", folder, host);
        out->id    = ID_SONIC;
        out->index = 0;
    }
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    HOST_FIELDS(X)
#undef X
    snprintf(out->senseSound, sizeof(out->senseSound), "%s", Json_String(Json_Get(ab, "senseSound"), ""));
}

#endif // MANIA_HOST_DATA_H
