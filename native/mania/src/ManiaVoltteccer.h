// NoSwapMania: Pulseman's Voltteccer (abilities.py voltteccer), the S3&K DLL's (native/src/Voltteccer.h: the same rules,
// numbers and art slot; tools/voltteccer.py is the Sonic 1/2 port), on Mania's Player, run for player 1 after every
// entity's update (OnUpdate): a velocity set here moves him next frame, after the air state's gravity (taken off in
// advance).
//   - The charge: running on the ground (the plain ground state, a walk / jog / run / dash pose, ground speed at least
//     voltRun) for voltCharge frames in a row charges him; slower first, it starts over. Charged: a sound, and his reds
//     flash his own electric blues (the package's charge_palettes charge1, every other 4 frames, only while his sprite
//     draws: ManiaMore.h MoreDraw asks VoltGlowPhase). Slower than voltKeep on the ground, or a hit, loses it.
//   - The launch: a jump press while charged (on the ground the game's jump has just happened; or in mid-air) turns him
//     into the ball (ability slot 41: frames 0-3 its loop, voltTicks each; 4-5 the small ball as it starts and in its
//     last frames), up-forward at voltSpeed (voltDiag per axis), gravity off, for voltFrames.
//   - Rebounds: a wall reverses its speed across; a ceiling, the stage's top edge or a floor its speed up / down (the
//     speed kept); anything that bounces him (a badnik he breaks, a boss, a bumper) reverses that axis too.
//   - An attack throughout (reported to the game as the jump), and nothing hurts him (the blink held at 3, no flicker).
//     At the end he pops back out into his jump ball with half its speed; a spring, an object, a hit, death end it.
// The package data (the JSON's "abilities": gen_s3k_header.ability_fields' names; only those not at their default) is
// kept by package folder (ReadVolt from LoadPackage). Included once, by NoSwapMania.c after ManiaNights.h.
#ifndef MANIA_VOLTTECCER_H
#define MANIA_VOLTTECCER_H

#define VT_SMALL       (4)  // slot 41: the loop 0-3, the small ball 4-5 (tools/voltteccer.py)
#define VT_LOOP        (4)
#define VT_START_SMALL (6)
#define VT_END_SMALL   (24)
#define VT_TOP         (16) // px below the stage's top: its ceiling (Mania doesn't stop a player there)
#define VT_CLOCK       (64)

// name, default (gen_s3k_header's: 0 for an extra without the move)
#define VOLT_FIELDS(X)                                                                                                         \
    X(voltteccer, 0) X(voltRun, 0) X(voltCharge, 0) X(voltKeep, 0) X(voltSpeed, 0) X(voltDiag, 0) X(voltFrames, 0)           \
    X(voltTicks, 0)

typedef struct {
    char folder[64];
#define X(name, def) int32 name;
    VOLT_FIELDS(X)
#undef X
    char voltSound[64];
    char voltReadySound[64];
} VoltData;

#define VOLT_MAX (64) // (EXTRA_MAX)
static VoltData g_voltData[VOLT_MAX];
static int32 g_voltDataCount = 0;

static void ReadVolt(const JsonNode *ab, const char *folder)
{
    if (g_voltDataCount >= VOLT_MAX)
        return;
    VoltData *out = &g_voltData[g_voltDataCount];
    memset(out, 0, sizeof(*out));
#define X(name, def) out->name = Json_Int(Json_Get(ab, #name), def);
    VOLT_FIELDS(X)
#undef X
    snprintf(out->voltSound, sizeof(out->voltSound), "%s", Json_String(Json_Get(ab, "voltSound"), ""));
    snprintf(out->voltReadySound, sizeof(out->voltReadySound), "%s", Json_String(Json_Get(ab, "voltReadySound"), ""));
    if (!out->voltteccer)
        return; // (not his move: nothing kept)
    snprintf(out->folder, sizeof(out->folder), "%s", folder);
    if (out->voltCharge < 1)
        out->voltCharge = 1;
    if (out->voltTicks < 1)
        out->voltTicks = 1;
    if (out->voltFrames <= VT_START_SMALL + VT_END_SMALL)
        out->voltFrames = VT_START_SMALL + VT_END_SMALL + 1;
    g_voltDataCount++;
}

static const VoltData *VoltOf(const char *folder)
{
    for (int32 i = 0; i < g_voltDataCount; ++i)
        if (strcmp(g_voltData[i].folder, folder) == 0)
            return &g_voltData[i];
    return NULL;
}

static const VoltData *g_vt = NULL; // the playing extra's (NULL: not his)
static int32 g_vtAnim       = -1;   // slot 41, or -1
static uint16 g_vtSfx = 0xFFFF, g_vtReadySfx = 0xFFFF;
static struct {
    int32 charge;   // 0..voltCharge-1 running; charged: voltCharge + its clock
    bool32 charged;
    int32 ball;     // frames left (0: none)
    Vector2 v;      // the ball's velocity
} g_vs;

// MoreDraw (ManiaMore.h): the charged flash's phase while his sprite draws (0: charge1; -1: his own colours)
static int32 VoltGlowPhase(void)
{
    if (!g_active || !g_vt || !g_vs.charged || g_vs.ball > 0)
        return -1;
    return (g_vs.charge >> 2) & 1 ? 0 : -1;
}

static void VtShow(EntityPlayer *p)
{
    int32 t     = g_vt->voltFrames - g_vs.ball;
    int32 frame = (t < VT_START_SMALL || g_vs.ball <= VT_END_SMALL) ? VT_SMALL + ((t >> 2) & 1) : (t / g_vt->voltTicks) % VT_LOOP;
    Show(p, g_vtAnim, true, false);
    BtFrame(p, frame);
    p->animator.speed = 0;
}

static void VtVelocity(EntityPlayer *p)
{
    p->velocity.x   = g_vs.v.x;
    p->velocity.y   = g_vs.v.y - p->gravityStrength; // (the air state adds it back)
    p->groundVel    = g_vs.v.x;
    p->applyJumpCap = false;
}

// Player 1's frame (OnUpdate, the game running)
static void VoltUpdate(EntityPlayer *p)
{
    const VoltData *c = g_vt;
    if (!g_active || !c || !IsExtra(p) || g_vtAnim < 0)
        return;
    bool32 air = !p->onGround;
    if (g_vs.ball > 0) { // the ball
        bool32 ours   = Showing(p, g_vtAnim) && p->animator.animationID == ANI_JUMP;
        bool32 landed = p->state == Player_State_Ground_ || (Player_State_Roll_ && p->state == Player_State_Roll_);
        if (Hurt(p) || (air && (!ours || !BtAir(p))) || (!air && !landed)) {
            g_vs.ball = 0; // a spring, an object, a hit, death: over (their speed and pose stay)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "voltteccer: taken over");
        }
        else {
            if (!air) { // a floor: it rebounds up (the speed kept)
                if (g_vs.v.y > 0)
                    g_vs.v.y = -g_vs.v.y;
                BtToAir(p);
            }
            else {
                int32 vy = p->velocity.y;
                if (g_vs.v.x != 0 && p->velocity.x == 0) // a wall
                    g_vs.v.x = -g_vs.v.x;
                else if ((g_vs.v.x > 0 && p->velocity.x < 0) || (g_vs.v.x < 0 && p->velocity.x > 0)) // bounced back
                    g_vs.v.x = -g_vs.v.x;
                if (g_vs.v.y < 0 && (vy == 0 || p->position.y < (VT_TOP << 16))) // a ceiling, the stage's top
                    g_vs.v.y = -g_vs.v.y;
                else if ((g_vs.v.y > 0 && vy < 0) || (g_vs.v.y < 0 && vy > 0)) // bounced (a badnik, a boss, a bumper)
                    g_vs.v.y = -g_vs.v.y;
            }
            if (--g_vs.ball == 0) { // over: back to his jump ball, with half its speed
                BackToJump(p);
                p->velocity.x = g_vs.v.x / 2;
                p->velocity.y = g_vs.v.y / 2;
                p->groundVel  = p->velocity.x;
            }
            else {
                p->direction = g_vs.v.x < 0 ? FLIP_X : FLIP_NONE;
                VtVelocity(p);
                VtShow(p);
                if (p->blinkTimer < 3)
                    p->blinkTimer = 3; // (untouchable: Player_Update counts it down to 2 before anything can hit him, no flicker)
            }
        }
    }
    // the charge
    int32 a      = p->animator.animationID;
    bool32 run   = !air && p->state == Player_State_Ground_ && a >= ANI_WALK && a <= ANI_DASH && Abs(p->groundVel) >= c->voltRun;
    bool32 lost  = Hurt(p) || g_vs.ball > 0;
    if (lost) {
        g_vs.charge  = 0;
        g_vs.charged = false;
    }
    else if (!g_vs.charged) {
        if (run && ++g_vs.charge >= c->voltCharge) {
            g_vs.charged = true;
            g_vs.charge  = 0;
            BtSfx(g_vtReadySfx);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "voltteccer: charged");
        }
        else if (!run)
            g_vs.charge = 0;
    }
    else {
        g_vs.charge = (g_vs.charge + 1) % VT_CLOCK; // (the flash's clock)
        if (!air && Abs(p->groundVel) < c->voltKeep)
            g_vs.charged = false; // slowing down loses it
    }
    if (!g_vs.charged || !p->jumpPress || !air || !BtAir(p) || Hurt(p))
        return;
    // the launch: up-forward, the way he's going (or faces)
    int32 dir    = p->velocity.x > 0 ? 1 : p->velocity.x < 0 ? -1 : (p->direction & FLIP_X) ? -1 : 1;
    g_vs.charged = false;
    g_vs.charge  = 0;
    g_vs.ball    = c->voltFrames;
    g_vs.v.x     = dir * c->voltDiag;
    g_vs.v.y     = -c->voltDiag;
    p->direction = dir < 0 ? FLIP_X : FLIP_NONE;
    BtToAir(p);
    VtVelocity(p);
    Show(p, g_vtAnim, true, true);
    VtShow(p);
    BtSfx(g_vtSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "voltteccer: launched (%d)", dir);
}

// Stage load (at its start, everything off; once the extra is set up, his move)
static void VoltStageLoad(void)
{
    memset(&g_vs, 0, sizeof(g_vs));
    g_vt = NULL;
    if (!g_cur || !g_active)
        return;
    const VoltData *c = VoltOf(g_cur->folder);
    if (!c)
        return;
    g_vtAnim     = HasAnim(g_cur->animBase + 0);
    g_vtSfx      = SfxOf(c->voltSound);
    g_vtReadySfx = SfxOf(c->voltReadySound);
    g_vt         = Player_State_Air_ && Player_State_Ground_ && g_vtAnim >= 0 ? c : NULL;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: voltteccer %s; anim %d; flash colours %d", g_cur->name, g_vt ? "on" : "OFF", g_vtAnim,
                  g_cur->more.chargeCount[0]);
}

#endif // MANIA_VOLTTECCER_H
