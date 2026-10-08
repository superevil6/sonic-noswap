// NoSwapMania: the crossover moves (Ristar, Dynamite Headdy, John Morris, Ecco; their data: ManiaCrossData.h), each the S3&K DLL's (the same states, numbers
// and art slots), on Mania's Player, run for player 1 after every entity's update (OnUpdate, as the S3&K DLL runs its
// moves after the game's): a velocity set here moves him next frame, after the air state's gravity (taken off in
// advance, as S3&K does).
//   - star_grab (Ristar; native/src/StarGrab.h): Y stretches his arms 8 ways (drawn at runtime: two 2 px black lines and
//     his hands, slot 43, after his sprite). A badnik, monitor or boss a hand reaches is caught (CrossStrike: the hand
//     within CR_CATCH px of it): he's yanked in to it as an attack (reported as the jump: the game's own break and
//     bounce), then bounces off it. Solid terrain at a hand: pulled in, and next to a wall or under a ceiling he hangs
//     (slot 42), climbs, hops off, or winds up the Meteor Strike on held jump (untouchable, an attack, 8 ways).
//   - head_throw (Dynamite Headdy; native/src/HeadThrow.h): Y throws his head 8 ways, out and straight back, his body
//     headless (slot 41, an attack); anything the head reaches is hit by player 1 standing in at the head (CrossStrike:
//     the shots' StandInAt, a CR_HEAD_BOX box) and a head going out comes back. Head variants: the index the
//     monitor_swap module would pick (his own head only so far: abilities.py has one variant).
//   - melee_whip + monitor_swap (John Morris; NoSwapS3K.cpp shots): the whip is the melee (ManiaMelee.h), its pose by
//     the d-pad as Y is pressed (CrossWhipAnim: crouching, up-forward or down in the air); up + Y throws the current
//     sub-weapon (the shots' Throw, the JSON's "swap_shots" entry at g_crSwap: CrossSwapShot), Holy Water bursting into
//     flames where it lands (CrossBurnUpdate); every item monitor broken moves the sub-weapon on (ItemBox_State_Break
//     hooked: its first run); the current one is drawn at the top middle of the screen in a dark box (CrossIconDraw,
//     over the HUD).
//   - free_swim (Ecco; native/src/EccoSwim.h): underwater (Mania's Water object: the main water and the pools, the
//     player's underwater field) he swims anywhere with the d-pad (slot 41, 8 directions); Y is the charge ram (slot 42:
//     an attack, untouchable, breaking walls as Knuckles: CrossAsKnuckles, ManiaWalls.h); out of the surface going up,
//     the leap (slot 43). On land: his flop (the package's walk), physics and no_roll.
// Included once, by NoSwapMania.c (after ManiaAmy.h).
#ifndef MANIA_CROSS_H
#define MANIA_CROSS_H

#include <math.h>

#define CR_PULL    (100) // (tools/star_grab.py's states)
#define CR_RETRACT (200)
#define CR_YANK    (300)
#define CR_WALL    (1000)
#define CR_CEILING (2000)
#define CR_METEOR  (3000)
#define CR_F_AIR      (5)
#define CR_F_PULL     (10)
#define CR_F_HEADBUTT (15)
#define CR_F_METEOR   (16)
#define CR_F_CEILING  (9)
#define CR_F_SWING    (18)
#define CR_LADDER     (9)
#define CR_SWING      (8)
#define CR_WALL_X     (14)
#define CR_CEILING_Y  (-24)
#define CR_CATCH      (20) // px from a hand to a badnik / monitor's position that catches it (S3&K: its hitbox + 8)
#define CR_CATCH_BOSS (40)
#define CR_HEAD_BACK   (200) // (tools/head_throw.py's)
#define CR_HEAD_FRAMES (10)
#define CR_HEAD_F_BACK (5)
#define CR_HEAD_Y      (-6)
#define CR_HEAD_BOX    (10)  // px round the head it hits (S3&K: the hitbox + 10 round its point)
#define CR_ICON_TOP    (8)   // the sub-weapon icon (monitor_swap.py ICON_*)
#define CR_ICON_PAD_X  (4)
#define CR_ICON_PAD_Y  (3)
#define CR_ICON_ALPHA  (160)
#define CR_HUD_GROUP   (14) // Zone->hudDrawGroup
#define CR_BURNING     (2)  // a swap shot's phase while its flames burn where it landed
#define CR_SWAP_WHICH  (16) // a swap shot's "which": CR_SWAP_WHICH + its entry
#define CR_PI          (3.14159265358979323846)
// (EntityItemBox's fields, the decomp's struct: compiled offsets, as ManiaHost.h's ITEMBOX_*)
#define CR_ITEMBOX_CONTENTS_SPEED (124) // .contentsSpeed: -0x30000 as ItemBox_Break leaves it, until its state's first run

static const int32 CR_UX[8]     = { 256, 181, 0, -181, -256, -181, 0, 181 };
static const int32 CR_UY[8]     = { 0, -181, -256, -181, 0, 181, 256, 181 };
static const int32 CR_DIR_OF[9] = { 3, 2, 1, 4, 0, 0, 5, 6, 7 }; // (x + 1) + 3 * (y + 1) -> direction
static const int32 CR_CLASS[8]  = { 0, 1, 2, 1, 0, 3, 4, 3 };    // direction -> aim class

static bool32 g_crStar = false, g_crHead = false, g_crWhip = false, g_crSwapOn = false, g_crSwim = false;
static int32 g_crAnim[3]; // ability slots 41-43 (animBase + 0..2), or -1
static uint16 g_crGrabSfx = 0xFFFF, g_crLatchSfx = 0xFFFF, g_crMeteorSfx = 0xFFFF, g_crHeadSfx = 0xFFFF, g_crSwapSfx = 0xFFFF,
              g_crRamSfx = 0xFFFF;
static uint16 g_crThrowSfx[CROSS_SWAP_MAX];
static int32 g_crSwap    = 0; // John's sub-weapon: the monitor_swap index (0 at each stage's start)
static int32 g_crWhipAim = 0; // the whip's pose, picked as Y was pressed: 0 plain, 1 crouching, 2 up-forward, 3 down
static bool32 g_crItemHooked = false, g_crIconOn = false;
static EngineSpriteFrame g_crHeadFrame; // the head's stand-in box
static Animator g_crHeadBox;
static void (*ItemBox_State_Break_Cross_)(void);

static struct { // Ristar
    int32 state;  // tools/star_grab.py's numbers (0: none)
    int32 dir;    // the aim (0 right, counterclockwise), or on a wall its side (0 right, 1 left)
    Vector2 latch, hand, pin, last;
} g_st;
static struct { // Headdy
    int32 state;
    int32 dir;
    Vector2 last;
} g_hd;
static struct { // Ecco
    bool32 swimming, leaping;
    double heading; // degrees, 0 right, counterclockwise
    int32 speed;    // 16.16
    int32 charge, cooldown, cycle, leapT, ramGrace;
} g_ec;

static const CrossData *CrData(void) { return &g_cur->more.cross; }
static bool32 CrPlain(EntityPlayer *p)
{
    int32 a = p->animator.animationID;
    return a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_WALK || (a >= ANI_JOG && a <= ANI_DASH);
}
static bool32 CrInState(EntityPlayer *p, bool32 air) { return air ? p->state == Player_State_Air_ : p->state == Player_State_Ground_; }
static void CrSfx(uint16 sfx)
{
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}
// solid terrain at (x, y) px from him (the S3&K DLL's TerrainAt: a floor or a ceiling side there)
static bool32 CrTerrainAt(EntityPlayer *p, int32 x, int32 y)
{
    return RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, x << 16, y << 16, false)
           || RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, x << 16, y << 16, false);
}
// One of his ability animations at a frame, held there (attacking: reported to the game as the jump)
static void CrFrame(EntityPlayer *p, int32 anim, int32 frame, bool32 attacking)
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
static void CrFace(EntityPlayer *p, int32 dir)
{
    if (CR_UX[dir] > 0)
        p->direction = FLIP_NONE;
    if (CR_UX[dir] < 0)
        p->direction = FLIP_X;
}
static void CrUntouchable(EntityPlayer *p)
{
    if (p->blinkTimer < 3)
        p->blinkTimer = 3; // (Player_Update counts it down to 2 before anything can hit him: no flicker)
}
static int32 CrAimDir(EntityPlayer *p, bool32 air)
{
    int32 x = p->right ? 1 : p->left ? -1 : 0, y = p->up ? -1 : (p->down && air) ? 1 : 0;
    if (x == 0 && y == 0)
        x = (p->direction & FLIP_X) ? -1 : 1;
    if (x)
        p->direction = x < 0 ? FLIP_X : FLIP_NONE;
    return CR_DIR_OF[(x + 1) + 3 * (y + 1)];
}
static bool32 CrWarped(Vector2 *last, EntityPlayer *p)
{
    Vector2 was = *last;
    *last       = p->position;
    return Abs(p->position.x - was.x) > (64 << 16) || Abs(p->position.y - was.y) > (64 << 16);
}

// ------------------------------------------------------------------------------------------------ Ristar
static void StarEnd(EntityPlayer *p, bool32 air)
{
    g_st.state = 0;
    if (air)
        BackToJump(p);
    else
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// Along the line to the point caught at `speed` (gravity taken off in advance); on the ground a point well above lifts
// him off, otherwise he's drawn along the ground to it
static void StarPullTo(EntityPlayer *p, int32 speed, bool32 air)
{
    double dx = (double)(g_st.latch.x - p->position.x), dy = (double)(g_st.latch.y - p->position.y), len = sqrt(dx * dx + dy * dy);
    if (!air) {
        if (dy < -(double)(12 << 16)) {
            ToAirState(p);
            p->velocity.x = 0;
            p->velocity.y = -0x10000;
            p->groundVel  = 0;
        }
        else {
            p->groundVel = dx < 0 ? -speed : speed;
        }
        return;
    }
    if (len > 0) {
        p->velocity.x = (int32)(speed * dx / len);
        p->velocity.y = (int32)(speed * dy / len) - p->gravityStrength;
    }
}

static void StarHang(EntityPlayer *p, const CrossData *c, bool32 air)
{
    p->velocity.x = 0;
    p->velocity.y = air ? -p->gravityStrength : 0;
    p->groundVel  = 0;
    if (!air) {
        StarEnd(p, false);
        return;
    }
    int32 side = g_st.latch.x < p->position.x ? 1 : 0;
    for (int32 k = 0; k < 2; k++, side ^= 1) {
        if (CrTerrainAt(p, side ? -CR_WALL_X : CR_WALL_X, 0)) {
            g_st.state   = CR_WALL;
            g_st.dir     = side;
            g_st.pin     = p->position;
            p->direction = side ? FLIP_X : FLIP_NONE;
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: hangs on a wall (%s)", side ? "left" : "right");
            return;
        }
    }
    if (CrTerrainAt(p, 0, CR_CEILING_Y)) {
        g_st.state = CR_CEILING;
        g_st.pin   = p->position;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: hangs under a ceiling");
        return;
    }
    g_st.state      = 0; // nothing to hold on to: let go with a hop
    p->velocity.y   = -c->hangHop;
    p->applyJumpCap = false;
    BackToJump(p);
}

static void StarLaunch(EntityPlayer *p, const CrossData *c, bool32 wall)
{
    int32 x = p->right ? 1 : p->left ? -1 : 0, y = p->down ? 1 : p->up ? -1 : 0;
    if (x == 0 && y == 0)
        x = wall ? (g_st.dir ? 1 : -1) : ((p->direction & FLIP_X) ? -1 : 1); // away from a wall, or the way he faces
    g_st.dir        = CR_DIR_OF[(x + 1) + 3 * (y + 1)];
    g_st.state      = CR_METEOR + c->meteorFrames;
    p->applyJumpCap = false;
    CrSfx(g_crMeteorSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: meteor strike (direction %d)", g_st.dir);
}

static void StarHangUpdate(EntityPlayer *p, const CrossData *c, bool32 air)
{
    if (!air) {
        StarEnd(p, false);
        return;
    }
    int32 kind = g_st.state >= CR_CEILING ? CR_CEILING : CR_WALL;
    int32 held = g_st.state - kind;
    if (p->jumpPress && held == 0)
        held = 1;
    if (held > 0) {
        if (p->jumpHold) {
            held = held + 1 < 999 ? held + 1 : 999;
        }
        else if (held >= c->windupFull) { // let go of a full wind-up
            StarLaunch(p, c, kind == CR_WALL);
            return;
        }
        else { // a hop off (down held: he just drops)
            g_st.state      = 0;
            p->velocity.y   = (p->down && !p->up) ? 0 : -c->hangHop;
            p->velocity.x   = kind == CR_WALL ? (g_st.dir ? c->hangPush : -c->hangPush) : 0;
            p->applyJumpCap = false;
            BackToJump(p);
            return;
        }
    }
    if (held == 0) { // climbing along
        if (kind == CR_WALL)
            g_st.pin.y += p->up ? -c->climbSpeed : p->down ? c->climbSpeed : 0;
        else
            g_st.pin.x += p->left ? -c->climbSpeed : p->right ? c->climbSpeed : 0;
    }
    p->position   = g_st.pin;
    p->velocity.x = 0;
    p->velocity.y = -p->gravityStrength;
    p->groundVel  = 0;
    bool32 attached = kind == CR_WALL ? CrTerrainAt(p, g_st.dir ? -CR_WALL_X : CR_WALL_X, 0) : CrTerrainAt(p, 0, CR_CEILING_Y);
    if (!attached) { // nothing to hold any more
        g_st.state = 0;
        if (kind == CR_WALL && p->up) { // climbed past the top: a hop onto the ledge
            p->velocity.y   = -c->hangHop;
            p->velocity.x   = g_st.dir ? -c->hangPush / 2 : c->hangPush / 2;
            p->applyJumpCap = false;
        }
        BackToJump(p);
        return;
    }
    g_st.state = kind + held;
    if (kind == CR_WALL)
        p->direction = g_st.dir ? FLIP_X : FLIP_NONE;
    int32 frame;
    if (held >= c->windupShow) {
        frame = CR_F_SWING + (held >> (held < c->windupFull ? 2 : 1)) % CR_SWING;
    }
    else {
        int32 along = (kind == CR_WALL ? p->position.y : p->position.x) >> 16;
        frame       = ((along >> 3) % CR_LADDER + CR_LADDER) % CR_LADDER + (kind == CR_CEILING ? CR_F_CEILING : 0);
    }
    CrFrame(p, g_crAnim[1], frame, false);
}

static void StarUpdate(EntityPlayer *p, bool32 transformed)
{
    const CrossData *c = CrData();
    const Abilities *ab = &g_cur->ab;
    bool32 air         = !p->onGround;
    bool32 inState     = CrInState(p, air);
    Vector2 last       = g_st.last;
    if (CrWarped(&g_st.last, p))
        g_st.state = 0; // (a respawn, a warp: whatever was going on is over)
    if (g_st.state > 0 && (Hurt(p) || !inState)) { // a hit, an object taking over, a spring...
        g_st.state = 0;
        return;
    }
    if (g_st.state <= 0 && !Hurt(p) && inState && (air || CrPlain(p)) && YPressedP1(p, transformed)) {
        g_st.dir   = CrAimDir(p, air);
        g_st.state = 1;
        CrSfx(g_crGrabSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: grab (direction %d, %s)", g_st.dir, air ? "air" : "ground");
    }
    if (g_st.state <= 0)
        return;
    int32 cls = CR_CLASS[g_st.state >= CR_WALL ? 0 : g_st.dir];
    if (g_st.state < CR_PULL) { // the arms going out: does a hand reach solid terrain?
        int32 len = g_st.state * c->grabStep, tx = CR_UX[g_st.dir] * len / 256, ty = CR_UY[g_st.dir] * len / 256;
        g_st.hand.x = p->position.x + (tx << 16);
        g_st.hand.y = p->position.y + (ty << 16);
        if (CrTerrainAt(p, tx, ty)) {
            g_st.latch = g_st.hand;
            g_st.state = CR_PULL + 1;
            CrSfx(g_crLatchSfx);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: caught terrain");
        }
        else if (++g_st.state > c->grabFrames) {
            g_st.state = CR_RETRACT + c->retractFrames;
        }
    }
    else if (g_st.state < CR_RETRACT) { // pulled in: there yet?
        int32 dx = Abs((g_st.latch.x - p->position.x) >> 16), dy = Abs((g_st.latch.y - p->position.y) >> 16);
        bool32 stopped = g_st.state > CR_PULL + 2
                         && (air ? Abs(p->position.x - last.x) < 0x8000 && Abs(p->position.y - last.y) < 0x8000 : p->groundVel == 0);
        if ((dx < ab->latchRange && dy < ab->latchRange) || g_st.state >= CR_PULL + ab->reelFrames || stopped) {
            StarHang(p, c, air);
            if (g_st.state == 0 || g_st.state >= CR_WALL)
                return;
        }
        else {
            g_st.state++;
            StarPullTo(p, ab->reelSpeed, air);
        }
    }
    else if (g_st.state < CR_YANK) { // the arms coming back
        if (--g_st.state == CR_RETRACT) {
            StarEnd(p, air);
            return;
        }
    }
    else if (g_st.state < CR_WALL) { // yanked in to the badnik: close enough, a bounce off it
        int32 dx = Abs((g_st.latch.x - p->position.x) >> 16), dy = Abs((g_st.latch.y - p->position.y) >> 16);
        if ((dx < c->yankRange && dy < c->yankRange) || g_st.state >= CR_YANK + c->yankFrames) {
            g_st.state = 0;
            if (!air)
                ToAirState(p);
            p->velocity.y   = -c->bounceY;
            p->velocity.x   = (p->direction & FLIP_X) ? c->bounceX : -c->bounceX;
            p->applyJumpCap = false;
            BackToJump(p);
            return;
        }
        g_st.state++;
        StarPullTo(p, c->yankSpeed, air);
        CrFrame(p, g_crAnim[0], dx < 32 && dy < 32 ? CR_F_HEADBUTT : CR_F_PULL + cls, true);
        CrFace(p, g_st.dir);
        return;
    }
    else if (g_st.state < CR_METEOR) {
        StarHangUpdate(p, c, air);
        return;
    }
    else { // the Meteor Strike
        int32 left     = g_st.state - CR_METEOR - 1;
        bool32 stopped = left < c->meteorFrames - 1 && Abs(p->position.x - last.x) < 0x10000 && Abs(p->position.y - last.y) < 0x10000;
        if (!air || left <= 0 || stopped) {
            StarEnd(p, air);
            return;
        }
        g_st.state--;
        p->velocity.x = CR_UX[g_st.dir] * (c->meteorSpeed >> 8);
        p->velocity.y = CR_UY[g_st.dir] * (c->meteorSpeed >> 8) - p->gravityStrength;
        CrUntouchable(p);
        CrFrame(p, g_crAnim[0], CR_F_METEOR + 3 * CR_CLASS[g_st.dir] + (left >> 2) % 3, true);
        CrFace(p, g_st.dir);
        return;
    }
    // the arms out or coming back, or pulled in: held still (no falling), the frame
    if (g_st.state < CR_PULL || (g_st.state > CR_RETRACT && g_st.state < CR_YANK)) {
        if (air) {
            if (p->velocity.y > -p->gravityStrength)
                p->velocity.y = -p->gravityStrength;
        }
        else {
            p->groundVel  = 0;
            p->velocity.x = 0;
        }
    }
    bool32 pulled = g_st.state > CR_PULL && g_st.state < CR_RETRACT;
    CrFrame(p, g_crAnim[0], pulled ? CR_F_PULL + cls : (air ? CR_F_AIR : 0) + cls, air);
    CrFace(p, g_st.dir);
}

// The draw (MoreDraw), before his sprite: in the wind-up, the body swings round his grip; after it: his arms and hands
static Vector2 g_crDrawPos;
static uint8 g_crDrawDir;
static void StarDrawBefore(EntityPlayer *p)
{
    const CrossData *c = CrData();
    g_crDrawPos        = p->position;
    g_crDrawDir        = p->direction;
    bool32 winding     = g_st.state >= CR_WALL && g_st.state < CR_METEOR && g_st.state % 1000 >= c->windupShow;
    if (!winding)
        return;
    if (g_st.state >= CR_CEILING) {
        p->position.y -= 20 << 16;
    }
    else {
        p->position.x += (g_st.dir ? -12 : 12) << 16;
        p->position.y -= 4 << 16;
        p->direction = g_st.dir ? FLIP_NONE : FLIP_X;
    }
}

static void StarDrawAfter(EntityPlayer *p)
{
    const CrossData *c = CrData();
    p->position        = g_crDrawPos;
    p->direction       = g_crDrawDir;
    if (g_st.state <= 0 || g_st.state >= CR_WALL)
        return;
    int32 dx, dy;
    bool32 grip = (g_st.state > CR_PULL && g_st.state < CR_RETRACT) || g_st.state > CR_YANK;
    if (grip) {
        dx = (g_st.latch.x - p->position.x) >> 16;
        dy = (g_st.latch.y - p->position.y) >> 16;
    }
    else {
        int32 back = c->grabFrames * c->grabStep / (c->retractFrames > 0 ? c->retractFrames : 1);
        int32 len  = g_st.state < CR_PULL ? g_st.state * c->grabStep : (g_st.state - CR_RETRACT) * back;
        dx         = CR_UX[g_st.dir] * len / 256;
        dy         = CR_UY[g_st.dir] * len / 256;
    }
    int32 n = Abs(dx) > Abs(dy) ? Abs(dx) : Abs(dy);
    if (n < 1)
        n = 1;
    int32 ox = -dy * 3 / n, oy = dx * 3 / n; // the arms: 3 px either side of the aim
    bool32 flat = Abs(dx) >= Abs(dy);
    for (int32 side = -1; side <= 1; side += 2) {
        int32 x1 = p->position.x + ((side * ox) << 16), y1 = p->position.y + ((side * oy) << 16);
        int32 x2 = x1 + (dx << 16), y2 = y1 + (dy << 16);
        for (int32 t = 0; t < 2; t++) { // 2 px thick
            int32 sx = flat ? 0 : t << 16, sy = flat ? t << 16 : 0;
            RSDK.DrawLine(x1 + sx, y1 + sy, x2 + sx, y2 + sy, 0x000000, 0xFF, INK_NONE, false);
        }
    }
    if (g_crAnim[2] < 0)
        return;
    Animator hand;
    memset(&hand, 0, sizeof(hand));
    RSDK.SetSpriteAnimation(g_extraFrames, g_crAnim[2], &hand, true, g_st.dir + (grip ? 8 : 0));
    int32 rotation = p->rotation;
    uint8 dir      = p->direction;
    p->direction   = FLIP_NONE; // (the hands are drawn every way round: absolute frames)
    p->rotation    = 0;
    for (int32 side = -1; side <= 1; side += 2) {
        Vector2 pos = { p->position.x + ((dx + side * ox) << 16), p->position.y + ((dy + side * oy) << 16) };
        RSDK.DrawSprite(&hand, &pos, false);
    }
    p->direction = dir;
    p->rotation  = rotation;
}

// ------------------------------------------------------------------------------------------------ Headdy
static int32 HeadVariant(void) { return 0; } // (the monitor_swap index for heads: his own head only, abilities.py)

static void HeadTip(const CrossData *c, int32 *x, int32 *y)
{
    int32 len = (g_hd.state > CR_HEAD_BACK ? g_hd.state - CR_HEAD_BACK : g_hd.state) * c->headStep[HeadVariant()];
    *x        = CR_UX[g_hd.dir] * len / 256;
    *y        = CR_UY[g_hd.dir] * len / 256 + CR_HEAD_Y;
}

static void HeadUpdate(EntityPlayer *p, bool32 transformed)
{
    const CrossData *c = CrData();
    bool32 air         = !p->onGround;
    bool32 inState     = CrInState(p, air);
    if (CrWarped(&g_hd.last, p))
        g_hd.state = 0;
    if (g_hd.state > 0 && (Hurt(p) || !inState)) {
        g_hd.state = 0;
        return;
    }
    if (g_hd.state <= 0 && !Hurt(p) && inState && (air || CrPlain(p)) && YPressedP1(p, transformed)) {
        g_hd.dir   = CrAimDir(p, air);
        g_hd.state = 1;
        CrSfx(g_crHeadSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "headdy: head throw (direction %d, %s)", g_hd.dir, air ? "air" : "ground");
    }
    if (g_hd.state <= 0)
        return;
    int32 frames = c->headFrames[HeadVariant()];
    if (g_hd.state < CR_HEAD_BACK) { // going out: solid terrain at the head sends it back
        int32 tx, ty;
        HeadTip(c, &tx, &ty);
        if (CrTerrainAt(p, tx, ty))
            g_hd.state += CR_HEAD_BACK;
        else if (++g_hd.state > frames)
            g_hd.state = CR_HEAD_BACK + frames;
    }
    else if (--g_hd.state <= CR_HEAD_BACK) { // coming back: home
        g_hd.state = 0;
        if (air)
            BackToJump(p);
        else
            RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
        return;
    }
    if (!air) {
        p->groundVel  = 0;
        p->velocity.x = 0;
    }
    CrFrame(p, g_crAnim[0], (air ? CR_F_AIR : 0) + CR_CLASS[g_hd.dir], true);
    CrFace(p, g_hd.dir);
}

static void HeadDrawAfter(EntityPlayer *p)
{
    if (g_hd.state <= 0 || g_crAnim[2] < 0)
        return;
    int32 tx, ty;
    HeadTip(CrData(), &tx, &ty);
    Animator head;
    memset(&head, 0, sizeof(head));
    int32 frame = HeadVariant() * CR_HEAD_FRAMES + (g_hd.state > CR_HEAD_BACK ? CR_HEAD_F_BACK : 0) + CR_CLASS[g_hd.dir];
    RSDK.SetSpriteAnimation(g_extraFrames, g_crAnim[2], &head, true, frame);
    int32 rotation = p->rotation;
    p->rotation    = 0;
    Vector2 pos    = { p->position.x + (tx << 16), p->position.y + (ty << 16) };
    RSDK.DrawSprite(&head, &pos, false); // (mirrored with his facing, as S3&K)
    p->rotation = rotation;
}

// ------------------------------------------------------------------------------------------------ Ecco
static int32 SwimDirIndex(double heading, int32 dirs)
{
    double step = 360.0 / dirs;
    int32 k     = (int32)floor(heading / step + 0.5);
    return ((k % dirs) + dirs) % dirs;
}

static void SwimUpdate(EntityPlayer *p, bool32 transformed)
{
    const CrossData *c = CrData();
    bool32 air         = !p->onGround;
    if (g_ec.cooldown > 0)
        g_ec.cooldown--;
    bool32 airState = p->state == Player_State_Air_, groundState = !air && p->state == Player_State_Ground_;
    bool32 free     = !Hurt(p) && (airState || groundState);
    bool32 water    = p->underwater != 0;
    bool32 y        = YPressedP1(p, transformed);

    // out of the water, going up: the leap (the game's air physics), its frames until he lands or splashes back
    if (!water) {
        if (g_ec.swimming && air && airState && p->velocity.y < 0) {
            g_ec.leaping = true;
            g_ec.leapT   = 0;
            p->direction = cos(g_ec.heading * CR_PI / 180) < 0 ? FLIP_X : FLIP_NONE;
        }
        g_ec.swimming = false;
        g_ec.charge   = 0;
        if (g_ec.ramGrace > 0)
            g_ec.ramGrace--;
        if (g_ec.leaping) {
            if (!air || !airState || Hurt(p)) {
                g_ec.leaping = false;
            }
            else if (g_crAnim[2] >= 0) {
                int32 frames = c->leapFrames > 0 ? c->leapFrames : 1;
                CrFrame(p, g_crAnim[2], Clamp(g_ec.leapT++ / c->leapTicks, 0, frames - 1), false);
            }
        }
        return;
    }
    g_ec.leaping = false;
    if (!free) {
        g_ec.swimming = false;
        g_ec.charge   = 0;
        return;
    }
    int32 ix = p->right ? 1 : p->left ? -1 : 0, iy = p->down ? 1 : p->up ? -1 : 0;
    if (!g_ec.swimming) { // into the swim: the heading from where he's going (or faces)
        if (p->velocity.x || p->velocity.y)
            g_ec.heading = atan2(-(double)p->velocity.y, (double)p->velocity.x) * 180 / CR_PI;
        else
            g_ec.heading = (p->direction & FLIP_X) ? 180 : 0;
        double v   = sqrt((double)p->velocity.x * p->velocity.x + (double)p->velocity.y * p->velocity.y);
        g_ec.speed = v < c->swimSpeed ? (int32)v : c->swimSpeed;
    }
    if (!air) { // resting on the floor: anything held (or the charge) lifts him off
        if (!ix && !iy && !y && g_ec.charge == 0) {
            g_ec.swimming = false;
            return;
        }
        ToAirState(p);
        p->position.y -= 2 << 16;
    }
    g_ec.swimming = true;
    if (y && g_ec.charge == 0 && g_ec.cooldown == 0) {
        g_ec.charge   = c->ramFrames;
        g_ec.cooldown = c->ramFrames + c->ramCooldown;
        CrSfx(g_crRamSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ecco: charge ram");
    }
    if (ix || iy) { // turn toward the d-pad's direction, and speed up
        double target = atan2(-(double)iy, (double)ix) * 180 / CR_PI;
        double diff   = fmod(target - g_ec.heading + 540.0, 360.0) - 180.0;
        double turn   = c->swimTurn > 0 ? c->swimTurn : 360;
        g_ec.heading += diff < -turn ? -turn : diff > turn ? turn : diff;
        g_ec.speed = g_ec.speed + c->swimAccel < c->swimSpeed ? g_ec.speed + c->swimAccel : c->swimSpeed;
    }
    else {
        g_ec.speed = g_ec.speed - c->swimDrag > 0 ? g_ec.speed - c->swimDrag : 0;
    }
    g_ec.heading = fmod(g_ec.heading + 360.0, 360.0);
    int32 speed  = g_ec.speed;
    if (g_ec.ramGrace > 0)
        g_ec.ramGrace--;
    if (g_ec.charge > 0) {
        g_ec.charge--;
        g_ec.ramGrace = 4;
        speed         = c->ramSpeed;
    }
    double r      = g_ec.heading * CR_PI / 180;
    p->velocity.x = (int32)(cos(r) * speed);
    p->velocity.y = (int32)(-sin(r) * speed) - p->gravityStrength; // (the air state's gravity taken off in advance)
    p->groundVel    = p->velocity.x;
    p->applyJumpCap = false;     // (Mania's air state caps a rise when jump isn't held: not a swim's)
    p->direction    = FLIP_NONE; // (the frames are drawn every way round: never flipped)
    int32 k       = SwimDirIndex(g_ec.heading, c->swimDirs);
    if (c->ramCycle > 0 && g_ec.charge > 0 && g_crAnim[1] >= 0) {
        int32 t = c->ramFrames - g_ec.charge;
        CrFrame(p, g_crAnim[1], k * c->ramCycle + (t / 2) % c->ramCycle, true);
        CrUntouchable(p);
    }
    else if (g_crAnim[0] >= 0) {
        g_ec.cycle += 64 + (int32)((int64)192 * g_ec.speed / (c->swimSpeed > 0 ? c->swimSpeed : 1)); // (faster strokes, faster swim)
        CrFrame(p, g_crAnim[0], k * c->swimCycle + (g_ec.cycle / (256 * c->swimTicks)) % c->swimCycle, false);
    }
}

// ManiaWalls.h WallUpdate: walls that break for Knuckles break for the ram (going on, or just ended: a wall it hit
// stopped him, and the wall's update may run after his)
static bool32 CrossAsKnuckles(EntityPlayer *p)
{
    return g_crSwim && IsExtra(p) && (g_ec.charge > 0 || g_ec.ramGrace > 0);
}

// ------------------------------------------------------------------------------------------------ John Morris
// melee_whip (ManiaMelee.h MeleeFrame): the pose by the d-pad as Y was pressed (start: just pressed)
static int32 CrossWhipAnim(EntityPlayer *p, bool32 air, bool32 start, int32 anim)
{
    if (!g_crWhip)
        return anim;
    if (start)
        g_crWhipAim = !air ? (p->down ? 1 : 0) : p->down ? 3 : p->up ? 2 : 0;
    int32 want = -1;
    if (!air && g_crWhipAim == 1)
        want = HasAnim(g_cur->animBase + 0);
    else if (air && g_crWhipAim == 2)
        want = HasAnim(g_cur->animBase + 3);
    else if (air && g_crWhipAim == 3)
        want = HasAnim(g_cur->animBase + 4);
    return want >= 0 ? want : anim;
}

// A whip pose of its own still showing (MeleeEnd: back to standing or the jump)
static bool32 CrossWhipShowing(EntityPlayer *p)
{
    return g_crWhip && (Showing(p, HasAnim(g_cur->animBase + 0)) || Showing(p, HasAnim(g_cur->animBase + 3)) || Showing(p, HasAnim(g_cur->animBase + 4)));
}

// In the air, up with a side held is the up-forward whip, not the up + Y sub-weapon (the S3&K DLL's UpThrow)
static bool32 CrossWhipUp(EntityPlayer *p) { return g_crWhip && !p->onGround && p->up && (p->left || p->right); }
// Y is the up + Y shot's now (so not the melee's)
static bool32 CrossUpThrow(EntityPlayer *p)
{
    return g_cur && g_cur->shot.motion != SHOT_NONE && g_cur->shot.upOnly && p->up && !CrossWhipUp(p);
}

// The shots (NoSwapMania.c Throw / ShotOf): John's current sub-weapon in place of the package's "shot"
static const ShotData *CrossSwapShot(const ShotData *shot)
{
    return g_crSwapOn ? &CrData()->swapShot[g_crSwap % CrData()->swapShotCount] : shot;
}
static int32 CrossSwapAnim(void) { return g_crSwapOn ? g_crSwap % CrData()->swapShotCount : 0; }
static int32 CrossSwapWhich(void) { return g_crSwapOn ? CR_SWAP_WHICH + g_crSwap % CrData()->swapShotCount : 1; }
static uint16 CrossSwapSfx(uint16 sfx) { return g_crSwapOn ? g_crThrowSfx[g_crSwap % CrData()->swapShotCount] : sfx; }
static const ShotData *CrossSwapOf(int32 which)
{
    int32 k = which - CR_SWAP_WHICH;
    return g_cur && k >= 0 && k < g_cur->more.cross.swapShotCount ? &g_cur->more.cross.swapShot[k] : (g_cur ? &g_cur->shot : NULL);
}

// A burning sub-weapon (Holy Water: "burn"): its flight as a drop, and on the floor its flames, held there for its burn
// lifetime (still hitting: "pierce"). true: its update is done here
static bool32 CrossBurnUpdate(EntityNoSwapShot *e, const ShotData *s)
{
    int32 k = e->which - CR_SWAP_WHICH;
    if (!g_crSwapOn || k < 0 || k >= CrData()->swapShotCount || CrData()->burnAnim[k] < 0 || s->motion != SHOT_DROP)
        return false;
    Vector2 range = { 0x200000, 0x200000 };
    if (e->phase == CR_BURNING) {
        if (!RSDK.CheckOnScreen(e, &range)) {
            ShotGone(e, "offscreen (burning)");
            return true;
        }
        RSDK.ProcessAnimation(&e->animator);
        return true;
    }
    uint16 layers = e->collisionLayers;
    uint8 plane   = e->collisionPlane;
    int32 r       = s->radius << 16;
    e->velocity.y += s->gravity;
    if (e->velocity.y > s->maxFall)
        e->velocity.y = s->maxFall;
    e->position.x += e->velocity.x;
    int32 ahead = e->velocity.x < 0 ? -r - 0x10000 : r + 0x10000;
    if (s->terrain && e->velocity.x
        && (RSDK.ObjectTileCollision(e, layers, CMODE_LWALL, plane, ahead, -r / 2, false)
            || RSDK.ObjectTileCollision(e, layers, CMODE_RWALL, plane, ahead, -r / 2, false))) {
        ShotGone(e, "wall");
        return true;
    }
    e->position.y += e->velocity.y;
    if (e->velocity.y > 0 && RSDK.ObjectTileCollision(e, layers, CMODE_FLOOR, plane, 0, r + 0x10000, false)) {
        // landed: it bursts into its flames there
        e->velocity.x = 0;
        e->velocity.y = 0;
        e->phase      = CR_BURNING;
        e->timer      = s->lifetime - CrData()->burnLifetime[k] > 0 ? s->lifetime - CrData()->burnLifetime[k] : 0;
        RSDK.SetSpriteAnimation(g_shotFrames, CrData()->burnAnim[k], &e->animator, true, 0);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "holy water: flames at %d,%d", e->position.x >> 16, e->position.y >> 16);
        return true;
    }
    if (e->velocity.y < 0 && RSDK.ObjectTileCollision(e, layers, CMODE_ROOF, plane, 0, -r - 0x10000, false)) {
        ShotGone(e, "ceiling");
        return true;
    }
    if (!RSDK.CheckOnScreen(e, &range)) {
        ShotGone(e, "offscreen");
        return true;
    }
    RSDK.ProcessAnimation(&e->animator);
    return true;
}

// ItemBox_State_Break, before it: its first run (contentsSpeed still as ItemBox_Break left it) is a monitor just broken,
// by anyone or anything: the next sub-weapon (the S3&K DLL's Hook_ItemBoxCheck)
static bool32 Hook_CrossItemBox(bool32 skipped)
{
    (void)skipped;
    Entity *box = SceneInfo->entity;
    if (!g_active || !g_cur || !box || g_cur->more.cross.swapCount <= 0)
        return false;
    if (*(int32 *)((uint8 *)box + CR_ITEMBOX_CONTENTS_SPEED) != -0x30000)
        return false;
    g_crSwap = (g_crSwap + 1) % g_cur->more.cross.swapCount;
    CrSfx(g_crSwapSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "monitor swap: the monitor at slot %d broke: entry %d of %d", RSDK.GetEntitySlot(box), g_crSwap + 1,
                  g_cur->more.cross.swapCount);
    return false;
}

// The sub-weapon icon (MODCB_ONDRAW, after the HUD's group): a translucent black box at the top middle of the screen,
// the current entry's flight frame 0 in it; not while the title card or the act results are up
static bool32 CrShowing(const char *object)
{
    uint16 id = RSDK.FindObject(object);
    return id && RSDK.GetEntityCount(id, true) > 0;
}

static void CrossIconDraw(void *data)
{
    if ((int32)(size_t)data != CR_HUD_GROUP || !g_active || !g_cur || !g_crSwapOn || !g_crIconOn || !g_shotOn || g_shotFrames == 0xFFFF
        || !ScreenInfo || !SceneInfo->entity)
        return;
    if (CrShowing("TitleCard") || CrShowing("ActClear") || CrShowing("PauseMenu"))
        return;
    EntityPlayer *p1 = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p1))
        return;
    int32 n = CrData()->swapShotCount, w = 0, h = 0;
    for (int32 k = 0; k < n; k++) {
        SpriteFrame *f = RSDK.GetFrame(g_shotFrames, k, 0);
        if (f) {
            w = f->width > w ? f->width : w;
            h = f->height > h ? f->height : h;
        }
    }
    if (!w || !h)
        return;
    int32 cx = ScreenInfo->center.x, bw = w + 2 * CR_ICON_PAD_X, bh = h + 2 * CR_ICON_PAD_Y;
    Entity *self = SceneInfo->entity;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;
    self->drawFX    = FX_NONE;
    self->inkEffect = INK_NONE;
    self->direction = FLIP_NONE;
    RSDK.DrawRect(cx - bw / 2, CR_ICON_TOP, bw, bh, 0x000000, CR_ICON_ALPHA, INK_ALPHA, true);
    Animator icon;
    memset(&icon, 0, sizeof(icon));
    RSDK.SetSpriteAnimation(g_shotFrames, (uint16)(g_crSwap % n), &icon, true, 0);
    Vector2 pos = { cx << 16, (CR_ICON_TOP + bh / 2) << 16 };
    RSDK.DrawSprite(&icon, &pos, true);
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

// ------------------------------------------------------------------------------------------------ hits, draw, frame
// A hit class's update (HitUpdate, first): Ristar's hands catching it (noted; its own update runs as usual: false), or
// Headdy's head hitting it (player 1 stands in at the head: true, its update has run)
static bool32 CrossStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    if (!g_active || !g_cur || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_ || p->state == Player_State_Drown_)
        return false;
    if (g_crStar && g_st.state > 0 && g_st.state < CR_PULL) {
        int32 reach = kind == HIT_BOSS ? CR_CATCH_BOSS : CR_CATCH;
        if (Abs(g_st.hand.x - self->position.x) <= (reach << 16) && Abs(g_st.hand.y - self->position.y) <= (reach << 16)) {
            g_st.latch = self->position;
            g_st.state = CR_YANK + 1;
            CrSfx(g_crLatchSfx);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ristar: caught class %d (slot %d)", self->classID, RSDK.GetEntitySlot(self));
        }
        return false;
    }
    if (g_crHead && g_hd.state > 0) {
        int32 tx, ty;
        HeadTip(CrData(), &tx, &ty);
        Vector2 at  = { p->position.x + (tx << 16), p->position.y + (ty << 16) };
        int32 reach = kind == HIT_BOSS ? REACH_BOSS : REACH_BADNIK;
        if (Abs(at.x - self->position.x) > (reach << 16) || Abs(at.y - self->position.y) > (reach << 16))
            return false;
        int32 near = (reach + 24) << 16; // (his own turn every other frame when he's near it himself)
        if (Abs(p->position.x - self->position.x) <= near && Abs(p->position.y - self->position.y) <= near && (g_frame & 1))
            return false;
        Animator own;
        const Animator *box = &g_crHeadBox;
        if (!g_engineFrameOK) { // (the fallback: his own frame's box, at the head)
            own = p->animator;
            box = &own;
        }
        if (StandInAt(self, at, box, p->direction, p->collisionPlane, p)) {
            if (g_hd.state < CR_HEAD_BACK)
                g_hd.state += CR_HEAD_BACK;
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "headdy: the head hit class %d (slot %d)", self->classID, RSDK.GetEntitySlot(self));
        }
        return true;
    }
    return false;
}

// The Player's draw (MoreDraw), around his sprite
static void CrossDrawBefore(EntityPlayer *self)
{
    if (g_crStar && RSDK.GetEntitySlot(self) == SLOT_PLAYER1)
        StarDrawBefore(self);
}
static void CrossDrawAfter(EntityPlayer *self)
{
    if (RSDK.GetEntitySlot(self) != SLOT_PLAYER1)
        return;
    if (g_crStar)
        StarDrawAfter(self);
    if (g_crHead)
        HeadDrawAfter(self);
}

// Player 1's frame (OnUpdate, the game running)
static void CrossUpdate(EntityPlayer *p, bool32 transformed)
{
    if (!g_active || !g_cur || !IsExtra(p))
        return;
    if (g_crStar)
        StarUpdate(p, transformed);
    if (g_crHead)
        HeadUpdate(p, transformed);
    if (g_crSwim)
        SwimUpdate(p, transformed);
}

static bool32 CrossHits(void)
{
    const CrossData *c = g_cur ? &g_cur->more.cross : NULL;
    return c && (c->starGrab || c->headThrow);
}

// Stage load (OnStageLoad: at its start, everything off; once the extra is set up, its moves)
static void CrossStageLoad(void)
{
    memset(&g_st, 0, sizeof(g_st));
    memset(&g_hd, 0, sizeof(g_hd));
    memset(&g_ec, 0, sizeof(g_ec));
    g_crSwap    = 0; // (monitor_swap: the first entry at each stage's start)
    g_crWhipAim = 0;
    g_crStar = g_crHead = g_crWhip = g_crSwapOn = g_crSwim = false;
    if (!g_cur || !g_active)
        return;
    const CrossData *c = CrData();
    for (int32 k = 0; k < 3; ++k) g_crAnim[k] = HasAnim(g_cur->animBase + k);
    g_crStar   = c->starGrab && g_crAnim[0] >= 0 && g_crAnim[1] >= 0 && Player_State_Ground_;
    g_crHead   = c->headThrow && g_crAnim[0] >= 0 && Player_State_Ground_;
    g_crWhip   = c->shotWhip && g_meleeOn;
    g_crSwapOn = c->swapShotCount > 0 && g_shotOn;
    g_crSwim   = c->freeSwim && g_crAnim[0] >= 0 && Player_State_Ground_;
    if (!(c->starGrab || c->headThrow || c->shotWhip || c->swapShotCount || c->freeSwim))
        return;
    g_crGrabSfx   = SfxOf(c->grabSound);
    g_crLatchSfx  = SfxOf(g_cur->more.latchSound);
    g_crMeteorSfx = SfxOf(c->meteorSound);
    g_crHeadSfx   = SfxOf(c->headSound);
    g_crSwapSfx   = SfxOf(c->swapSound);
    g_crRamSfx    = SfxOf(c->ramSound);
    for (int32 k = 0; k < c->swapShotCount; ++k) g_crThrowSfx[k] = SfxOf(c->swapShot[k].sound);
    if (g_crHead) {
        g_engineFrameOK = CheckEngineFrames();
        memset(&g_crHeadFrame, 0, sizeof(g_crHeadFrame));
        g_crHeadFrame.hitboxCount = 1;
        for (int32 i = 0; i < 8; ++i) {
            g_crHeadFrame.hitboxes[i].left = g_crHeadFrame.hitboxes[i].top = -CR_HEAD_BOX;
            g_crHeadFrame.hitboxes[i].right = g_crHeadFrame.hitboxes[i].bottom = CR_HEAD_BOX;
        }
        memset(&g_crHeadBox, 0, sizeof(g_crHeadBox));
        g_crHeadBox.frames      = (SpriteFrame *)&g_crHeadFrame;
        g_crHeadBox.frameCount  = 1;
        g_crHeadBox.animationID = ANI_JUMP;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: star grab %d, head throw %d, whip %d, sub-weapons %d (%d, item hook %d, icon %d), free swim %d; "
                  "anims %d %d %d; hits %s; draw %s",
                  g_cur->name, g_crStar, g_crHead, g_crWhip, g_crSwapOn, c->swapShotCount, g_crItemHooked, g_crIconOn, g_crSwim, g_crAnim[0],
                  g_crAnim[1], g_crAnim[2], g_hitsOn ? "on" : "OFF", g_drawWrapped ? "wrapped" : "NOT wrapped");
}

// Link (last): the Player's draw wrapped if nothing else did (Ristar's arms, Headdy's head), the monitor hook and the icon
static void LinkCross(void)
{
    bool32 draw = false, swap = false, icon = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        const CrossData *c = &g_extras[i].more.cross;
        draw |= c->starGrab || c->headThrow;
        swap |= c->swapCount > 0;
        icon |= c->swapIcon && c->swapShotCount > 0;
    }
    if (draw && !g_drawWrapped) {
        Mod.RegisterObject(NULL, NULL, "Player", sizeof(EntityPlayer), 0, 0, NULL, NULL, NULL, MoreDraw, NULL, NULL, NULL, NULL, NULL, NULL,
                           NULL);
        g_drawWrapped = true;
    }
    if (swap) {
        ItemBox_State_Break_Cross_ = Mod.GetPublicFunction(NULL, "ItemBox_State_Break");
        if (ItemBox_State_Break_Cross_) {
            Mod.RegisterStateHook(ItemBox_State_Break_Cross_, Hook_CrossItemBox, true);
            g_crItemHooked = true;
        }
        else {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "monitor swap: ItemBox_State_Break wasn't found: no swaps");
        }
    }
    if (icon) {
        Mod.AddModCallback(MODCB_ONDRAW, CrossIconDraw);
        g_crIconOn = true;
    }
}

#endif // MANIA_CROSS_H
