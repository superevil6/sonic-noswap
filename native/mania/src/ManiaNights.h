// NoSwapMania: NiGHTS' free flight, Drill Dash and Paraloop (abilities.py free_flight), the S3&K DLL's
// (native/src/NightsFlight.h: the same rules, numbers and art slots; tools/free_flight.py is the Sonic 1/2 and CD port),
// on Mania's Player, run for player 1 after every entity's update (OnUpdate): a velocity set here moves him next frame,
// after the air state's gravity (taken off in advance).
//   - A jump press in mid-air (the air state; not the frame he left the ground) or Y in mid-air starts the flight while
//     the meter has anything left; the d-pad steers the heading, another jump press lets go; landing, a hit or any state
//     but the air one ends it. Underwater it doesn't drain, and flying level he swims (slot 42's frames from 8).
//   - The meter drains in flight, refills on the ground, rings top it up; empty, he floats down. Drawn at the top middle
//     of the screen (MODCB_ONDRAW, the HUD's group) while it isn't full or he flies.
//   - Y in flight: the Drill Dash (slot 41: an attack, reported as the jump; untouchable).
//   - The Paraloop: his path sampled; when it closes on itself round a big enough loop, every hit class (the shots'
//     HIT_CLASSES, wrapped by HitUpdate) whose position is inside is hit for loopHit frames by player 1 standing in at it
//     (NightsStrike: the shots' StandInAt with a small box), the game's own hit code doing the rest.
// The package data (the JSON's "abilities": gen_s3k_header.ability_fields' names; only those not at their default) is
// kept by package folder (ReadNights from LoadPackage). Included once, by NoSwapMania.c after ManiaCross.h.
#ifndef MANIA_NIGHTS_H
#define MANIA_NIGHTS_H

#include <math.h>

#define NI_PI         (3.14159265358979323846)
#define NI_MAX_POINTS (32)
#define NI_LOOP_AGE   (4)
#define NI_DRILL      (4)
#define NI_METER_W    (64)
#define NI_METER_H    (4)
#define NI_METER_TOP  (10)
#define NI_BOX        (16) // px round a stand-in's point
#define NI_HUD_GROUP  (14) // Zone->hudDrawGroup (ManiaCross.h CR_HUD_GROUP)

// name, default (gen_s3k_header's: 0 for an extra without the move)
#define NIGHTS_FIELDS(X)                                                                                                        \
    X(freeFlight, 0) X(flySpeed, 0) X(flyAccel, 0) X(flyDrag, 0) X(flyTurn, 0) X(flyMeter, 0) X(flyDrain, 0) X(flyRefill, 0)   \
    X(flyRing, 0) X(flySink, 0) X(flySwimFrames, 0) X(flySwimTicks, 0) X(drillFrames, 0) X(drillSpeed, 0) X(drillCooldown, 0)  \
    X(drillCost, 0) X(loopPoints, 0) X(loopEvery, 0) X(loopClose, 0) X(loopMin, 0) X(loopHit, 0)

typedef struct {
    char folder[64];
#define X(name, def) int32 name;
    NIGHTS_FIELDS(X)
#undef X
    char drillSound[64];
} NightsData;

#define NIGHTS_MAX (64) // (EXTRA_MAX)
static NightsData g_nightsData[NIGHTS_MAX];
static int32 g_nightsDataCount = 0;

static void ReadNights(const JsonNode *ab, const char *folder)
{
    if (g_nightsDataCount >= NIGHTS_MAX)
        return;
    NightsData *out = &g_nightsData[g_nightsDataCount];
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    NIGHTS_FIELDS(X)
#undef X
    snprintf(out->drillSound, sizeof(out->drillSound), "%s", Json_String(Json_Get(ab, "drillSound"), ""));
    if (!out->freeFlight)
        return; // (not his move: nothing kept)
    snprintf(out->folder, sizeof(out->folder), "%s", folder);
    if (out->flyMeter < 1)
        out->flyMeter = 1;
    if (out->flySwimFrames < 1)
        out->flySwimFrames = 1;
    if (out->flySwimTicks < 1)
        out->flySwimTicks = 1;
    if (out->loopEvery < 1)
        out->loopEvery = 1;
    if (out->loopHit < 1)
        out->loopHit = 1;
    out->loopPoints = Clamp(out->loopPoints, 6, NI_MAX_POINTS);
    g_nightsDataCount++;
}

static const NightsData *NightsOf(const char *folder)
{
    for (int32 i = 0; i < g_nightsDataCount; ++i)
        if (strcmp(g_nightsData[i].folder, folder) == 0)
            return &g_nightsData[i];
    return NULL;
}

enum { NI_NONE, NI_FLY, NI_FLOAT, NI_FALL };
static const NightsData *g_ni = NULL; // the playing extra's (NULL: not his)
static int32 g_niAnim[2];             // slots 41 (the drill) and 42 (the flight), or -1
static uint16 g_niDrillSfx = 0xFFFF;
static bool32 g_niDrawOn   = false;
static EngineSpriteFrame g_niFrame;
static Animator g_niBox;
static struct {
    int32 mode;
    double heading; // degrees, 0 right, counterclockwise
    int32 speed, meter, drill, cycle, air, rings;
    int32 sampleT, count, sx[NI_MAX_POINTS], sy[NI_MAX_POINTS];
    int32 kill, kn, kx[NI_MAX_POINTS], ky[NI_MAX_POINTS], bx0, bx1, by0, by1;
} g_nf;

static void NiFrame(EntityPlayer *p, int32 anim, int32 frame, bool32 attacking)
{
    if (!Showing(p, anim))
        RSDK.SetSpriteAnimation(g_extraFrames, anim, &p->animator, true, 0);
    int32 count         = p->animator.frameCount > 0 ? p->animator.frameCount : 1;
    p->animator.frameID = Clamp(frame, 0, count - 1);
    p->animator.timer   = 0;
    p->animator.speed   = 0;
    if (attacking)
        p->animator.animationID = ANI_JUMP;
}

static void NiLeave(EntityPlayer *p, int32 mode, bool32 air)
{
    g_nf.mode  = mode;
    g_nf.drill = 0;
    if (air)
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_AIR_WALK, &p->animator, false, 0); // (his floating frames)
}

static bool32 NiInside(int32 x, int32 y)
{
    bool32 in = false;
    for (int32 i = 0, j = g_nf.kn - 1; i < g_nf.kn; j = i++) {
        if ((g_nf.ky[i] > y) != (g_nf.ky[j] > y)) {
            int64 xi = g_nf.kx[i] + (int64)(y - g_nf.ky[i]) * (g_nf.kx[j] - g_nf.kx[i]) / (g_nf.ky[j] - g_nf.ky[i]);
            if (x < xi)
                in = !in;
        }
    }
    return in;
}

// HitUpdate: while the loop's hit lasts, a hit class inside it is hit by player 1 standing in at it
static bool32 NightsStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    (void)kind;
    if (!g_active || !g_ni || g_nf.kill <= 0 || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_
        || p->state == Player_State_Drown_)
        return false;
    int32 x = self->position.x >> 16, y = self->position.y >> 16;
    if (x < g_nf.bx0 || x > g_nf.bx1 || y < g_nf.by0 || y > g_nf.by1 || !NiInside(x, y))
        return false;
    Animator own;
    const Animator *box = &g_niBox;
    if (!g_engineFrameOK) { // (the fallback: his own frame's box)
        own = p->animator;
        box = &own;
    }
    if (StandInAt(self, self->position, box, p->direction, p->collisionPlane, p)) {
        static int32 logs = 0;
        if (logs++ < 40)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "nights: the paraloop hit class %d (slot %d)", self->classID, RSDK.GetEntitySlot(self));
    }
    return true;
}
static bool32 NightsHits(void) { return g_cur && NightsOf(g_cur->folder) != NULL; }
static bool32 NightsHasFlight(const char *folder) { return NightsOf(folder) != NULL; }

static void NiSample(EntityPlayer *p)
{
    const NightsData *c = g_ni;
    int32 n = c->loopPoints;
    if (++g_nf.sampleT < c->loopEvery)
        return;
    g_nf.sampleT = 0;
    for (int32 k = 0; k + 1 < n; k++) {
        g_nf.sx[k] = g_nf.sx[k + 1];
        g_nf.sy[k] = g_nf.sy[k + 1];
    }
    int32 x = p->position.x >> 16, y = p->position.y >> 16;
    g_nf.sx[n - 1] = x;
    g_nf.sy[n - 1] = y;
    g_nf.count     = g_nf.count + 1 < n ? g_nf.count + 1 : n;
    int32 m        = -1;
    for (int32 k = n - g_nf.count; k <= n - 1 - NI_LOOP_AGE && m < 0; k++)
        if (Abs(g_nf.sx[k] - x) < c->loopClose && Abs(g_nf.sy[k] - y) < c->loopClose)
            m = k;
    if (m < 0)
        return;
    int32 x0 = x, x1 = x, y0 = y, y1 = y;
    for (int32 k = m; k < n; k++) {
        x0 = g_nf.sx[k] < x0 ? g_nf.sx[k] : x0;
        x1 = g_nf.sx[k] > x1 ? g_nf.sx[k] : x1;
        y0 = g_nf.sy[k] < y0 ? g_nf.sy[k] : y0;
        y1 = g_nf.sy[k] > y1 ? g_nf.sy[k] : y1;
    }
    if (x1 - x0 < c->loopMin || y1 - y0 < c->loopMin)
        return;
    g_nf.kn = 0;
    for (int32 k = m; k < n; k++) {
        g_nf.kx[g_nf.kn]   = g_nf.sx[k];
        g_nf.ky[g_nf.kn++] = g_nf.sy[k];
    }
    g_nf.bx0   = x0;
    g_nf.bx1   = x1;
    g_nf.by0   = y0;
    g_nf.by1   = y1;
    g_nf.kill  = c->loopHit;
    g_nf.count = 0;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "nights: a paraloop, %d samples, %dx%d px", g_nf.kn, x1 - x0, y1 - y0);
}

// Player 1's frame (OnUpdate, the game running)
static void NightsUpdate(EntityPlayer *p, bool32 transformed)
{
    const NightsData *c = g_ni;
    if (!g_active || !c || !IsExtra(p) || g_niAnim[1] < 0)
        return;
    if (g_nf.meter < 0)
        g_nf.meter = c->flyMeter;
    if (g_nf.kill > 0)
        g_nf.kill--;
    if (g_nf.drill > 0)
        g_nf.drill--;
    if (g_nf.rings >= 0 && p->rings > g_nf.rings) { // every ring he gets tops the meter up
        g_nf.meter += (p->rings - g_nf.rings) * c->flyRing;
        if (g_nf.meter > c->flyMeter)
            g_nf.meter = c->flyMeter;
    }
    g_nf.rings      = p->rings;
    bool32 air      = !p->onGround;
    bool32 airState = p->state == Player_State_Air_;
    bool32 free     = airState && !Hurt(p);
    bool32 water    = p->underwater != 0;
    bool32 y        = YPressedP1(p, transformed);
    int32 wasAir    = g_nf.air;
    g_nf.air        = airState ? (g_nf.air < 100 ? g_nf.air + 1 : 100) : 0;

    if (!air) { // on the ground: no flight, the meter fills up
        if (g_nf.mode != NI_NONE)
            NiLeave(p, NI_NONE, false);
        g_nf.meter = g_nf.meter + c->flyRefill < c->flyMeter ? g_nf.meter + c->flyRefill : c->flyMeter;
        g_nf.count = 0;
        return;
    }
    if (g_nf.mode == NI_FLY) {
        if (!free)
            NiLeave(p, NI_NONE, false);
        else if (p->jumpPress) // jump again: he lets go
            NiLeave(p, NI_FALL, true);
        else if (g_nf.meter <= 0 && !water) // empty: he floats down
            NiLeave(p, NI_FLOAT, true);
    }
    else if (g_nf.mode != NI_FLOAT && free && wasAir > 0 && (p->jumpPress || y) && g_nf.meter > 0) {
        g_nf.mode = NI_FLY; // the flight: the heading from where he's going (or faces)
        if (p->velocity.x || p->velocity.y)
            g_nf.heading = atan2(-(double)p->velocity.y, (double)p->velocity.x) * 180 / NI_PI;
        else
            g_nf.heading = (p->direction & FLIP_X) ? 180 : 0;
        double v     = sqrt((double)p->velocity.x * p->velocity.x + (double)p->velocity.y * p->velocity.y);
        g_nf.speed   = v < c->flySpeed ? (int32)v : c->flySpeed;
        g_nf.count   = 0;
        g_nf.sampleT = 0;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "nights: flight (meter %d)", g_nf.meter);
    }
    if (g_nf.mode == NI_FLOAT) { // the meter's empty: a slow fall (the air state's gravity taken off in advance)
        if (!free)
            g_nf.mode = NI_NONE;
        else if (p->velocity.y > c->flySink - p->gravityStrength)
            p->velocity.y = c->flySink - p->gravityStrength;
    }
    if (g_nf.mode != NI_FLY)
        return;
    if (!water)
        g_nf.meter = g_nf.meter - c->flyDrain > 0 ? g_nf.meter - c->flyDrain : 0;
    if (y && g_nf.drill == 0 && g_nf.meter > 0) { // the Drill Dash
        g_nf.drill = c->drillFrames + c->drillCooldown;
        g_nf.meter = g_nf.meter - c->drillCost > 0 ? g_nf.meter - c->drillCost : 0;
        if (g_niDrillSfx != 0xFFFF)
            RSDK.PlaySfx(g_niDrillSfx, false, 255);
    }
    int32 ix = p->right ? 1 : p->left ? -1 : 0, iy = p->down ? 1 : p->up ? -1 : 0;
    if (ix || iy) { // turn toward the d-pad's direction, and speed up
        double target = atan2(-(double)iy, (double)ix) * 180 / NI_PI;
        double diff   = fmod(target - g_nf.heading + 540.0, 360.0) - 180.0;
        double turn   = c->flyTurn > 0 ? c->flyTurn : 360;
        g_nf.heading += diff < -turn ? -turn : diff > turn ? turn : diff;
        g_nf.speed = g_nf.speed + c->flyAccel < c->flySpeed ? g_nf.speed + c->flyAccel : c->flySpeed;
    }
    else {
        g_nf.speed = g_nf.speed - c->flyDrag > 0 ? g_nf.speed - c->flyDrag : 0;
    }
    g_nf.heading    = fmod(g_nf.heading + 360.0, 360.0);
    bool32 drilling = g_nf.drill > c->drillCooldown && g_niAnim[0] >= 0;
    int32 speed     = drilling ? c->drillSpeed : g_nf.speed;
    double r        = g_nf.heading * NI_PI / 180;
    p->velocity.x   = (int32)(cos(r) * speed);
    p->velocity.y   = (int32)(-sin(r) * speed) - p->gravityStrength; // (the air state's gravity taken off in advance)
    p->groundVel    = p->velocity.x;
    p->applyJumpCap = false;
    if (cos(r) > 0.125) // his facing: the way he's going across
        p->direction = FLIP_NONE;
    else if (cos(r) < -0.125)
        p->direction = FLIP_X;
    int32 d = (((int32)floor(g_nf.heading / 45.0 + 0.5)) % 8 + 8) % 8;
    if (p->direction & FLIP_X)
        d = (4 - d) & 7;
    if (drilling) {
        int32 t = c->drillFrames + c->drillCooldown - g_nf.drill;
        NiFrame(p, g_niAnim[0], (t / 2) % NI_DRILL, true);
    }
    else {
        int32 frame = d;
        if (water && d == 0) { // underwater, level: the swim cycle, faster the faster he goes
            g_nf.cycle = (g_nf.cycle + 64 + (int32)((int64)192 * g_nf.speed / (c->flySpeed > 0 ? c->flySpeed : 1)))
                         % (256 * c->flySwimTicks * c->flySwimFrames);
            frame = 8 + g_nf.cycle / (256 * c->flySwimTicks);
        }
        NiFrame(p, g_niAnim[1], frame, false);
    }
    if ((drilling || g_nf.kill > 0) && p->blinkTimer < 3)
        p->blinkTimer = 3; // (untouchable: Player_Update counts it down to 2 before anything can hit him, no flicker)
    NiSample(p);
    if (g_nf.kill > 0)
        p->animator.animationID = ANI_JUMP; // (the loop's hit: an attack while it lasts)
}

// The meter (MODCB_ONDRAW, the HUD's group): a dark box at the top middle, the bar (yellow; red under a quarter)
static void NightsDraw(void *data)
{
    if ((int32)(size_t)data != NI_HUD_GROUP || !g_active || !g_ni || !ScreenInfo || !SceneInfo->entity)
        return;
    if (g_nf.mode != NI_FLY && (g_nf.meter < 0 || g_nf.meter >= g_ni->flyMeter))
        return;
    if (CrShowing("TitleCard") || CrShowing("ActClear") || CrShowing("PauseMenu"))
        return;
    if (!IsExtra((EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return;
    int32 x = ScreenInfo->center.x - NI_METER_W / 2;
    RSDK.DrawRect(x - 2, NI_METER_TOP, NI_METER_W + 4, NI_METER_H + 4, 0x000000, CR_ICON_ALPHA, INK_ALPHA, true);
    int32 w = NI_METER_W * (g_nf.meter > 0 ? g_nf.meter : 0) / g_ni->flyMeter;
    if (w > 0)
        RSDK.DrawRect(x, NI_METER_TOP + 2, w, NI_METER_H, g_nf.meter < g_ni->flyMeter / 4 ? 0xE52E27 : 0xFFFF00, 0xFF, INK_NONE, true);
}

// Stage load (at its start, everything off; once the extra is set up, his move)
static void NightsStageLoad(void)
{
    memset(&g_nf, 0, sizeof(g_nf));
    g_nf.meter = -1;
    g_nf.rings = -1;
    g_ni       = NULL;
    if (!g_cur || !g_active)
        return;
    const NightsData *c = NightsOf(g_cur->folder);
    if (!c)
        return;
    for (int32 k = 0; k < 2; ++k) g_niAnim[k] = HasAnim(g_cur->animBase + k);
    g_niDrillSfx    = SfxOf(c->drillSound);
    g_engineFrameOK = CheckEngineFrames();
    memset(&g_niFrame, 0, sizeof(g_niFrame));
    g_niFrame.hitboxCount = 1;
    for (int32 i = 0; i < 8; ++i) {
        g_niFrame.hitboxes[i].left = g_niFrame.hitboxes[i].top = -NI_BOX;
        g_niFrame.hitboxes[i].right = g_niFrame.hitboxes[i].bottom = NI_BOX;
    }
    memset(&g_niBox, 0, sizeof(g_niBox));
    g_niBox.frames      = (SpriteFrame *)&g_niFrame;
    g_niBox.frameCount  = 1;
    g_niBox.animationID = ANI_JUMP;
    g_ni                = Player_State_Air_ ? c : NULL;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: free flight %s; anims %d %d; hits %s; meter drawn %s", g_cur->name, g_ni ? "on" : "OFF",
                  g_niAnim[0], g_niAnim[1], g_hitsOn ? "on" : "OFF", g_niDrawOn ? "yes" : "NO");
}

// Link: the meter's draw (only when some package has the flight)
static void LinkNights(void)
{
    if (g_nightsDataCount > 0 && !g_niDrawOn) {
        Mod.AddModCallback(MODCB_ONDRAW, NightsDraw);
        g_niDrawOn = true;
    }
}

#endif // MANIA_NIGHTS_H
