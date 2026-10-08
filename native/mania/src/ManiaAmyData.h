// NoSwapMania: Amy Rose's package data (the JSON's "amy" section, tools/mania_only.py "moves"; the runtime is
// ManiaAmy.h). A package with an "amy" section plays with her moves; each number defaults to Origins' own (the exe's,
// 0x10000 = 1 px per frame), so the section may be empty. Included once, by ManiaMoreData.h (MoreData keeps an AmyData).
#ifndef MANIA_AMY_DATA_H
#define MANIA_AMY_DATA_H

#include "JsonLite.h"

// name, default (Origins')
#define AMY_FIELDS(X)                                                                                                           \
    X(chargeFrames, 20) /* jump held this long through the Hammer Jump: charged (Global/DropDash.wav) */                       \
    X(dashSpeed, 0x60000) /* the Hammer Dash's ground speed, flat */                                                            \
    X(dashFrames, 60)     /* its longest */                                                                                     \
    X(throwPose, 13)      /* the standing Hammer Throw's pose, frames */                                                        \
    X(jumpOffset, 2)      /* px (Sonic 5) */                                                                                    \
    X(sensorY, 17)        /* px from her centre to her feet (Sonic 20; her frames stand on 17) */

typedef struct {
    bool32 on; // the package has an "amy" section
#define X(name, def) int32 name;
    AMY_FIELDS(X)
#undef X
} AmyData;

static void ReadAmy(const JsonNode *mania, AmyData *out)
{
    const JsonNode *a = Json_Get(mania, "amy");
    out->on = a && a->type == JSON_OBJECT;
#define X(name, def) out->name = Json_Int(Json_Get(a, #name), def);
    AMY_FIELDS(X)
#undef X
    if (out->chargeFrames < 1)
        out->chargeFrames = 1;
    if (out->dashFrames < 1)
        out->dashFrames = 1;
}

#endif // MANIA_AMY_DATA_H
