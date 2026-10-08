// NoSwapMania: the moves ported with Omega, Marine and Mephiles, and Emerl's copy heads (their data: ManiaMoreData.h).
// Each is the S3&K DLL's (native/src/NoSwapS3K.cpp, AnchorThrow.h, WaterWalk.h), on Mania's Player and the mod's own ways:
//   - anchor_throw (Marine; AnchorThrow.h): Y on the ground or in the air throws the anchor in an arc (up + Y higher), a
//     chain drawn from her hand (RSDK DrawLine), the anchor (ability slot 43: 0 flukes forward, 1 up, 2 down). It hits
//     through the shots' stand-in (AnchorStrike, from HitUpdate: player 1 stands in at the anchor with a 24x24 box); a
//     hit flying out sends it back. A wall or ceiling ahead of it latches: she's reeled in, then a small hop; a floor or
//     its range sends it back to her hand; then its cooldown. She holds her throwing pose (slot 41, an attack).
//   - water_walk (Marine; WaterWalk.h): above the stage's water level (the Water object's waterLevel: ObjectWaterLite), the
//     surface is ground for her; down held dives. (Not the pools: CPZ / HCZ's Water entities of type "pool".)
//   - sink (Mephiles' Shadow Sink): down + Y on the ground sinks him (slot 47's frames), under for sinkMax frames at most,
//     then he rises; letting go of down or Y rises at once. He doesn't move (Hook_SinkInput clears his input) and
//     nothing hurts him (the post-hit blink held at 3: no flicker); then sinkCooldown frames. Y alone still throws.
//   - float_lean (Mephiles): his walk / jog / run / dash (full rotation in Mania's Sonic.bin already) drawn turned by his
//     speed alone, not the slope: only while drawing (MoreDraw), the game never sees it.
//   - copy heads (Emerl): the active Copycat move's copy of his idle / bored / walk / air walk / jog / run / dash / peel out
//     / copy flash shown in place of the game's: the animator's frame list swapped only while drawing (MoreDraw).
//   - the charge flash (Omega's Flame Blast; the charge itself is in ShotFrame): from chargeStart frames held, his own
//     colours show the charge palettes, only while his sprite draws (MoreDraw: the palette set, his draw, put back), as
//     Player_Draw itself does for a second Sonic.
// MoreDraw is the Player's Draw, wrapped (Mod.RegisterObject "Player", only its Draw; the rest stays the game's), and only
// when a package needs it. Included once, by NoSwapMania.c (after ManiaWalls.h).
#ifndef MANIA_MORE_H
#define MANIA_MORE_H

#include <math.h>

typedef struct {
    RSDK_OBJECT
    int32 waterLevel; // (Mania's ObjectWater: its first field)
} ObjectWaterLite;
static ObjectWaterLite *g_waterLite = NULL;

static bool32 g_anchorOn = false, g_waterWalkOn = false, g_sinkOn = false, g_drawWrapped = false;
static int32 g_animSink = -1, g_animAnchor = -1;
static uint16 g_anchorSfx = 0xFFFF, g_latchSfx = 0xFFFF, g_sinkSfx = 0xFFFF;

// ------------------------------------------------------------------------------------------------ anchor
#define ANCHOR_LATCH  (100) // (tools/anchor_throw.py's states)
#define ANCHOR_BACK   (200)
#define ANCHOR_BACK_MAX (90)
#define ANCHOR_HAND_X (16)
#define ANCHOR_HAND_Y (4)
#define ANCHOR_LEAD   (12)
#define ANCHOR_BOX    (12)
#define ANCHOR_CHAIN  (0x21201D) // the anchor's outline (her #21201d)
#define ANCHOR_STRUCK_MAX (16)

static struct {
    int32 state;    // 0 ready; 1.. flying; ANCHOR_LATCH.. reeling; ANCHOR_BACK.. coming back; < 0 the cooldown
    bool32 left;    // thrown to the left
    bool32 high;    // up + Y
    bool32 ceiling; // latched on a ceiling
    int32 vy;       // flying: its vertical speed this frame
    Vector2 pos;    // the anchor, or the point latched
    Vector2 last;   // her position last frame (a warp ends it)
    int32 struck[ANCHOR_STRUCK_MAX]; // what this throw has hit (slot + 1)
    int32 struckCount;
} g_anchor;
static EngineSpriteFrame g_anchorFrame; // its stand-in box (hitbox 0: ANCHOR_BOX round it)
static Animator g_anchorBox;

static bool32 YPressedP1(EntityPlayer *p, bool32 transformed)
{
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    return key && key->press && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled && !transformed;
}

static bool32 YHeldP1(EntityPlayer *p)
{
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    return key && key->down;
}

// Solid terrain at (x, y) px from her: floorSide, anything solid from above too; otherwise walls and ceilings only
static bool32 AnchorSolid(EntityPlayer *p, int32 x, int32 y, bool32 floorSide)
{
    return (floorSide && RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, x << 16, y << 16, false))
           || RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, x << 16, y << 16, false);
}

static void AnchorPose(EntityPlayer *p)
{
    Show(p, g_animAttack, true, false); // (slot 41, reported as the jump: an attack)
    p->animator.frameID = 0;
    p->animator.timer   = 0;
}

static void AnchorGone(EntityPlayer *p, bool32 air)
{
    g_anchor.state = -g_cur->ab.anchorCooldown;
    if (air)
        BackToJump(p);
    else
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

static void ToAirState(EntityPlayer *p)
{
    p->onGround      = false;
    p->angle         = 0;
    p->collisionMode = CMODE_FLOOR;
    p->state         = Player_State_Air_;
}

static Vector2 AnchorHand(EntityPlayer *p)
{
    Vector2 v = { p->position.x + (((p->direction & FLIP_X) ? -ANCHOR_HAND_X : ANCHOR_HAND_X) << 16), p->position.y + (ANCHOR_HAND_Y << 16) };
    return v;
}

static void AnchorUpdate(EntityPlayer *p, bool32 transformed)
{
    const Abilities *c = &g_cur->ab;
    bool32 air         = !p->onGround;
    int32 a            = p->animator.animationID;
    bool32 plain       = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_WALK || (a >= ANI_JOG && a <= ANI_DASH);
    bool32 inState     = air ? p->state == Player_State_Air_ : p->state == Player_State_Ground_;
    Vector2 last       = g_anchor.last;
    g_anchor.last      = p->position;
    if (Abs(p->position.x - last.x) > (64 << 16) || Abs(p->position.y - last.y) > (64 << 16))
        g_anchor.state = 0; // (a respawn, a warp: whatever was going on is over)
    if (g_anchor.state > 0 && (Hurt(p) || !inState)) { // a hit, an object taking over, a spring...
        g_anchor.state = 0;
        return;
    }
    if (g_anchor.state < 0)
        g_anchor.state++;
    if (g_anchor.state == 0 && !Hurt(p) && inState && (air || plain) && YPressedP1(p, transformed)) {
        if (p->left)
            p->direction = FLIP_X;
        if (p->right)
            p->direction = FLIP_NONE;
        g_anchor.left        = (p->direction & FLIP_X) != 0;
        g_anchor.high        = p->up;
        g_anchor.ceiling     = false;
        g_anchor.pos         = AnchorHand(p);
        g_anchor.state       = 1;
        g_anchor.struckCount = 0;
        if (g_anchorSfx != 0xFFFF)
            RSDK.PlaySfx(g_anchorSfx, false, 255);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "anchor throw (%s, %s)", g_anchor.high ? "high" : "level", air ? "air" : "ground");
    }
    if (g_anchor.state <= 0)
        return;
    int32 s = g_anchor.left ? -1 : 1;
    if (g_anchor.state < ANCHOR_LATCH) { // flying: the arc
        g_anchor.vy = -(g_anchor.high ? c->anchorHighRise : c->anchorRise) + c->anchorGravity * g_anchor.state;
        g_anchor.pos.x += (g_anchor.high ? c->anchorHighSpeed : c->anchorSpeed) * s;
        g_anchor.pos.y += g_anchor.vy;
        int32 ax = (g_anchor.pos.x - p->position.x) >> 16, ay = (g_anchor.pos.y - p->position.y) >> 16;
        int32 met = 0;
        if (g_anchor.vy >= 0 && AnchorSolid(p, ax, ay + ANCHOR_LEAD, true)) {
            met = 1; // a floor
        }
        else if (AnchorSolid(p, ax + s * ANCHOR_LEAD, ay, false)) {
            met = 2; // a wall: latched at that point
            g_anchor.pos.x += (s * ANCHOR_LEAD) << 16;
        }
        else if (g_anchor.vy < 0 && AnchorSolid(p, ax, ay - ANCHOR_LEAD, false)) {
            met = 3; // a ceiling
            g_anchor.pos.y -= ANCHOR_LEAD << 16;
            g_anchor.ceiling = true;
        }
        if (met == 0 && ++g_anchor.state >= c->anchorFrames)
            g_anchor.state = ANCHOR_BACK + 1;
        if (met == 1)
            g_anchor.state = ANCHOR_BACK + 1;
        if (met >= 2) {
            g_anchor.state = ANCHOR_LATCH + 1;
            if (g_latchSfx != 0xFFFF)
                RSDK.PlaySfx(g_latchSfx, false, 255);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "anchor bites (%s)", met == 2 ? "wall" : "ceiling");
        }
    }
    else if (g_anchor.state < ANCHOR_BACK) { // latched: reeled in; there yet?
        int32 dx = (g_anchor.pos.x - p->position.x) >> 16, dy = (g_anchor.pos.y - p->position.y) >> 16;
        bool32 stopped = g_anchor.state > ANCHOR_LATCH + 2
                         && (air ? Abs(p->position.x - last.x) < 0x8000 && Abs(p->position.y - last.y) < 0x8000 : p->groundVel == 0);
        if ((Abs(dx) < c->latchRange && Abs(dy) < c->latchRange) || g_anchor.state >= ANCHOR_LATCH + c->reelFrames || stopped) {
            g_anchor.state = -c->anchorCooldown; // there: a small hop toward it, and let go
            if (!air)
                ToAirState(p);
            p->velocity.y   = -c->grappleHop;
            p->velocity.x   = dx < 0 ? -c->grappleForward : c->grappleForward;
            p->groundVel    = p->velocity.x;
            p->applyJumpCap = false;
            BackToJump(p);
            return;
        }
        g_anchor.state++;
        double fx = (double)(g_anchor.pos.x - p->position.x), fy = (double)(g_anchor.pos.y - p->position.y), len = sqrt(fx * fx + fy * fy);
        if (!air) { // on the ground: a point well above lifts her off; otherwise she's drawn along the ground
            if (dy < -12) {
                ToAirState(p);
                p->velocity.x = 0;
                p->velocity.y = -0x10000;
                p->groundVel  = 0;
            }
            else {
                p->groundVel = dx < 0 ? -c->reelSpeed : c->reelSpeed;
            }
        }
        else if (len > 0) {
            p->velocity.x = (int32)(c->reelSpeed * fx / len);
            p->velocity.y = (int32)(c->reelSpeed * fy / len) - p->gravityStrength; // (the air state's gravity, in advance)
        }
        p->applyJumpCap = false;
        p->direction    = dx < 0 ? FLIP_X : FLIP_NONE;
        AnchorPose(p);
        return;
    }
    else { // coming back to her hand
        Vector2 hand = AnchorHand(p);
        double fx = (double)(hand.x - g_anchor.pos.x), fy = (double)(hand.y - g_anchor.pos.y), len = sqrt(fx * fx + fy * fy);
        if ((fabs(fx) < c->anchorReturn + 0x40000 && fabs(fy) < c->anchorReturn + 0x40000) || g_anchor.state >= ANCHOR_BACK + ANCHOR_BACK_MAX) {
            AnchorGone(p, air);
            return;
        }
        g_anchor.state++;
        if (len > 0) {
            g_anchor.pos.x += (int32)(c->anchorReturn * fx / len);
            g_anchor.pos.y += (int32)(c->anchorReturn * fy / len);
        }
    }
    if (!air) { // she stands still for it
        p->groundVel  = 0;
        p->velocity.x = 0;
    }
    p->direction = g_anchor.left ? FLIP_X : FLIP_NONE;
    AnchorPose(p);
}

// A hit class's update (HitUpdate, before the melee's): while the anchor flies or comes back, anything in reach gets a
// stand-in update with player 1 on the anchor (a 24x24 box); each object once per throw; one flying out comes back. Her
// own turn every other frame when she's near it herself. true: its update has run
static bool32 AnchorStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    if (!g_anchorOn || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_ || p->state == Player_State_Drown_ || g_anchor.state <= 0
        || (g_anchor.state > ANCHOR_LATCH && g_anchor.state < ANCHOR_BACK))
        return false;
    int32 reach = kind == HIT_BOSS ? REACH_BOSS : REACH_BADNIK;
    if (Abs(g_anchor.pos.x - self->position.x) > (reach << 16) || Abs(g_anchor.pos.y - self->position.y) > (reach << 16))
        return false;
    int32 slot = RSDK.GetEntitySlot(self);
    for (int32 i = 0; i < g_anchor.struckCount; ++i)
        if (g_anchor.struck[i] == slot + 1)
            return false;
    int32 near = (reach + 24) << 16;
    if (Abs(p->position.x - self->position.x) <= near && Abs(p->position.y - self->position.y) <= near && (g_frame & 1))
        return false;
    Animator anchorAnim;
    const Animator *box = &g_anchorBox;
    if (!g_engineFrameOK) { // (the fallback: the anchor's own frame's box)
        memset(&anchorAnim, 0, sizeof(anchorAnim));
        RSDK.SetSpriteAnimation(g_extraFrames, g_animAnchor, &anchorAnim, true, 0);
        box = &anchorAnim;
    }
    if (!StandInAt(self, g_anchor.pos, box, g_anchor.left ? FLIP_X : FLIP_NONE, p->collisionPlane, p))
        return true;
    if (g_anchor.struckCount < ANCHOR_STRUCK_MAX)
        g_anchor.struck[g_anchor.struckCount++] = slot + 1;
    if (g_anchor.state < ANCHOR_LATCH)
        g_anchor.state = ANCHOR_BACK + 1;
    static int32 logs = 0;
    if (logs++ < 60)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "anchor: hit class %d (slot %d)", self->classID, slot);
    return true;
}

// The chain and the anchor, after her sprite (MoreDraw)
static void AnchorDraw(EntityPlayer *p)
{
    const Abilities *c = &g_cur->ab;
    Vector2 hand       = AnchorHand(p);
    int32 dx = (g_anchor.pos.x - hand.x) >> 16, dy = (g_anchor.pos.y - hand.y) >> 16;
    bool32 flat = Abs(dx) >= Abs(dy);
    for (int32 t = 0; t < 2; ++t) {
        int32 sx = flat ? 0 : t << 16, sy = flat ? t << 16 : 0;
        RSDK.DrawLine(hand.x + sx, hand.y + sy, g_anchor.pos.x + sx, g_anchor.pos.y + sy, ANCHOR_CHAIN, 0xFF, INK_NONE, false);
    }
    int32 frame = 0;
    if (g_anchor.state < ANCHOR_LATCH) {
        int32 along = g_anchor.high ? c->anchorHighSpeed : c->anchorSpeed;
        frame       = g_anchor.vy < -along ? 1 : g_anchor.vy > along ? 2 : 0;
    }
    else if (g_anchor.state < ANCHOR_BACK && g_anchor.ceiling) {
        frame = 1;
    }
    if (g_animAnchor < 0)
        return;
    Animator anchor;
    memset(&anchor, 0, sizeof(anchor));
    RSDK.SetSpriteAnimation(g_extraFrames, g_animAnchor, &anchor, true, frame);
    int32 rotation = p->rotation;
    uint8 dir      = p->direction;
    int32 fx       = p->drawFX;
    p->rotation    = 0;
    p->direction   = g_anchor.left ? FLIP_X : FLIP_NONE;
    p->drawFX      = FX_FLIP;
    RSDK.DrawSprite(&anchor, &g_anchor.pos, false);
    p->rotation  = rotation;
    p->direction = dir;
    p->drawFX    = fx;
}

// ------------------------------------------------------------------------------------------------ water walk
#define WALK_TOL_AIR    (4)
#define WALK_TOL_GROUND (16)
#define WALK_HEAD       (24)

static bool32 OnGroundState(EntityPlayer *p)
{
    void *s = (void *)p->state;
    return s == (void *)Player_State_Ground_ || s == (void *)Player_State_Crouch_ || s == (void *)Player_State_LookUp_
           || s == (void *)Player_State_Roll_ || s == (void *)Player_State_Spindash_ || s == (void *)Player_State_Peelout_;
}

static void WaterWalk(EntityPlayer *p)
{
    if (!g_waterLite)
        return;
    int32 level = g_waterLite->waterLevel;
    if (level <= 0 || level >= 0x7FFF0000)
        return; // (no water in this stage)
    if (p->down || p->velocity.y < 0 || Hurt(p) || p->onGround)
        return; // (diving, rising, hurt; or the game found a real floor)
    bool32 onWater = OnGroundState(p); // (she was on it last frame: a ground state)
    if (!onWater && p->state != Player_State_Air_)
        return; // (an object has her)
    if (g_anchor.state > ANCHOR_LATCH && g_anchor.state < ANCHOR_BACK)
        return; // (reeled in by her anchor)
    Hitbox *box  = RSDK.GetHitbox(&p->animator, 0);
    int32 bottom = box ? box->bottom : 20;
    int32 feet   = p->position.y + (bottom << 16);
    if (onWater) {
        if (level - feet > (WALK_TOL_GROUND << 16) || feet - level > (WALK_TOL_GROUND << 16))
            return;
    }
    else if (feet < level || feet - p->velocity.y > level + (WALK_TOL_AIR << 16)) {
        return; // (still above it; or she was under it: coming up from below)
    }
    int32 head = ((level - feet) >> 16) - WALK_HEAD;
    if (RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, 0, head << 16, false))
        return; // (no room: rising water doesn't push her into a ceiling; she's left to sink)
    p->position.y    = level - (bottom << 16);
    p->velocity.y    = 0;
    p->onGround      = true;
    p->angle         = 0;
    p->rotation      = 0;
    p->collisionMode = CMODE_FLOOR;
    if (!onWater)
        p->groundVel = p->velocity.x; // landing: her speed along kept
    int32 a = p->animator.animationID;
    if (a == ANI_BALANCE_1 || a == ANI_BALANCE_2) // (no teetering: the whole surface is under her)
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// ------------------------------------------------------------------------------------------------ the Shadow Sink
#define SINK_RISE (1000) // (abilities.py SINK_RISE)
static struct {
    int32 k;       // 0 ready; 1.. sinking / under; SINK_RISE.. rising; < 0 the cooldown
    bool32 down;   // down held (as the input had it, before Hook_SinkInput cleared it)
} g_sink;

// Down + Y on the ground is the sink's, even while it cools down; and no throw while he's sunk (ShotFrame)
static bool32 SinkBlocksShot(EntityPlayer *p) { return g_sinkOn && (g_sink.k > 0 || (p->onGround && g_sink.down)); }

// After player 1's input (Player_Input_P1): while he's sunk, no input (he doesn't move or jump); down kept aside for the sink
static bool32 Hook_SinkInput(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!g_sinkOn || !IsExtra(self))
        return false;
    g_sink.down = self->down;
    if (g_sink.k > 0) {
        self->left = self->right = self->up = self->down = false;
        self->jumpPress = self->jumpHold = false;
    }
    return false;
}

static void SinkUpdate(EntityPlayer *p, bool32 transformed)
{
    const Abilities *c = &g_cur->ab;
    const MoreData *d  = &g_cur->more;
    int32 steps = Clamp(c->sinkSteps, 1, SINK_FRAMES_MAX), under = Clamp(c->sinkUnderCount, 1, SINK_UNDER_MAX);
    int32 ticks = c->sinkTicks > 1 ? c->sinkTicks : 1, uticks = c->sinkUnderTicks > 1 ? c->sinkUnderTicks : 1, total = steps * ticks;
    bool32 air  = !p->onGround;
    if (g_sink.k < 0)
        g_sink.k++;
    int32 a      = p->animator.animationID;
    bool32 plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_CROUCH || (a >= ANI_WALK && a <= ANI_DASH)
                   || Showing(p, g_animShot);
    bool32 free  = p->state == Player_State_Ground_ || p->state == Player_State_Crouch_;
    if (g_sink.k == 0 && !air && plain && free && !Hurt(p) && g_sink.down && YPressedP1(p, transformed)) {
        g_sink.k = 1;
        if (g_sinkSfx != 0xFFFF)
            RSDK.PlaySfx(g_sinkSfx, false, 255);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shadow sink");
    }
    if (g_sink.k <= 0)
        return;
    if (air || Hurt(p) || !free) { // the ground gave way, a hit that got through, an object: over
        g_sink.k = -c->sinkCooldown;
        if (Showing(p, g_animSink))
            RSDK.SetSpriteAnimation(g_extraFrames, air ? ANI_AIR_WALK : ANI_IDLE, &p->animator, true, 0);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shadow sink: ended");
        return;
    }
    p->groundVel  = 0;
    p->velocity.x = 0;
    p->velocity.y = 0;
    if (p->blinkTimer < 3)
        p->blinkTimer = 3; // nothing hurts him (Player_Update counts it down to 2 before anything can: no flicker)
    if (g_sink.k < SINK_RISE && !(g_sink.down && YHeldP1(p))) // let go: he rises, from where he is
        g_sink.k = SINK_RISE + (g_sink.k < total ? g_sink.k : total);
    int32 frame;
    if (g_sink.k <= total) { // sinking
        int32 i = (g_sink.k - 1) / ticks;
        frame   = d->sinkFrames[i < steps - 1 ? i : steps - 1];
        g_sink.k++;
    }
    else if (g_sink.k < SINK_RISE) { // under
        frame = d->sinkUnder[((g_sink.k - total - 1) / uticks) % under];
        if (++g_sink.k > total + c->sinkMax) // time's up: he rises
            g_sink.k = SINK_RISE + total;
    }
    else { // rising: the sink's frames backward
        frame = d->sinkFrames[Clamp((g_sink.k - SINK_RISE - 1) / ticks, 0, steps - 1)];
        g_sink.k--;
    }
    Show(p, g_animSink, false, false);
    p->animator.frameID = frame < p->animator.frameCount ? frame : p->animator.frameCount - 1;
    p->animator.timer   = 0;
    p->animator.speed   = 0;
    if (g_sink.k == SINK_RISE) { // risen
        g_sink.k = -c->sinkCooldown;
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
    }
}

// ------------------------------------------------------------------------------------------------ the draw
// The Player's Draw (wrapped when a package needs it): for the extra, his copy head, lean and charge flash only while his
// sprite draws; then Marine's chain and anchor
static void BatchDrawBefore(EntityPlayer *self); // (ManiaBatch.h)
static void BatchDrawAfter(EntityPlayer *self);
static void CrossDrawBefore(EntityPlayer *self); // (ManiaCross.h: Ristar's wind-up swing; his arms, Headdy's head)
static void CrossDrawAfter(EntityPlayer *self);
static int32 VoltGlowPhase(void); // (ManiaVoltteccer.h: Pulseman's charged flash)
static void MoreDraw(void)
{
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!g_active || !g_cur || !IsExtra(self) || self->aniFrames != g_extraFrames) {
        Mod.Super(Player->classID, SUPER_DRAW, NULL);
        return;
    }
    const Abilities *c = &g_cur->ab;
    const MoreData *d  = &g_cur->more;
    bool32 p1          = RSDK.GetEntitySlot(self) == SLOT_PLAYER1;
    Animator *a        = &self->animator;
    SpriteFrame *frames = a->frames;
    int32 rotation     = self->rotation;

    // copy heads: the active move's copy of this animation (the same frames, timing and boxes, another head)
    if (d->copySets > 0 && p1 && frames) {
        int32 id = a->animationID, k = -1;
        static const int8 COPY_OF[] = { 0, 1, -1, -1, -1, 2, 3, 4, 5, 6 }; // Idle, Bored 1, Walk, Air Walk, Jog, Run, Dash
        if (id >= 0 && id < (int32)sizeof(COPY_OF))
            k = COPY_OF[id];
        else if (id == ANI_ABILITY_1)
            k = 7; // the Peel Out ("Fly")
        else if (id == g_animShot)
            k = 8; // the copy flash
        if (k >= 0 && k < d->copyCount && frames == RSDK.GetFrame(g_extraFrames, id, 0)) {
            Animator copy;
            memset(&copy, 0, sizeof(copy));
            RSDK.SetSpriteAnimation(g_extraFrames, d->copyOffset + d->copyCount * (g_copy % d->copySets) + k, &copy, true, 0);
            if (copy.frames && copy.frameCount == a->frameCount)
                a->frames = copy.frames;
        }
    }
    // float_lean: his walk / run turned by his speed alone
    if (c->floatLean && a->animationID >= ANI_WALK && a->animationID <= ANI_DASH) {
        int32 v    = self->onGround ? self->groundVel : self->velocity.x;
        int32 lean = Clamp((int32)((int64)v * c->floatLean / 0x10000), -c->floatLeanMax, c->floatLeanMax);
        self->rotation = lean & 0x1FF;
    }
    // the charge flash: charge1 every other 4 frames until full, then charge2a, charge2b and his own, 2 frames each
    int32 phase = -1;
    const ShotData *s2 = &g_cur->shot2;
    if (p1 && s2->onCharge && g_charge >= s2->chargeStart)
        phase = g_charge < s2->chargeFull ? ((g_charge >> 2) & 1 ? 0 : -1) : ((g_charge >> 1) % 3 < 2 ? (g_charge >> 1) % 3 + 1 : -1);
    if (p1 && phase < 0)
        phase = VoltGlowPhase(); // (Pulseman charged: charge1 every other 4 frames, ManiaVoltteccer.h)
    color saved[CHARGE_PAL_MAX];
    int32 n = phase >= 0 ? d->chargeCount[phase] : 0;
    for (int32 i = 0; i < n; ++i) {
        saved[i] = RSDK.GetPaletteEntry(0, d->chargeSlot[phase][i]);
        RSDK.SetPaletteEntry(0, d->chargeSlot[phase][i], d->chargeColour[phase][i]);
    }

    if (p1)
        afterImage_Draw(self); // (his afterimages, under him: ManiaGhost.h)
    BatchDrawBefore(self); // (Honey's spin lean, Heavy's spark glow: ManiaBatch.h)
    CrossDrawBefore(self);
    Mod.Super(Player->classID, SUPER_DRAW, NULL);
    BatchDrawAfter(self);
    CrossDrawAfter(self); // (puts back what CrossDrawBefore moved, then draws the arms / head)

    for (int32 i = 0; i < n; ++i) RSDK.SetPaletteEntry(0, d->chargeSlot[phase][i], saved[i]);
    a->frames      = frames;
    self->rotation = rotation;
    if (g_anchorOn && p1 && g_anchor.state > 0)
        AnchorDraw(self);
    if (p1)
        PsychoDrawCarried(self); // (Silver's caught badnik: ManiaPsycho.h)
}

// ------------------------------------------------------------------------------------------------ stage, frame, link
static uint16 SfxOf(const char *path) { return path && path[0] ? RSDK.GetSfx(path) : 0xFFFF; }

// Stage load (OnStageLoad, once the extra is set up)
static void MoreStageLoad(void)
{
    memset(&g_anchor, 0, sizeof(g_anchor));
    memset(&g_sink, 0, sizeof(g_sink));
    g_charge     = 0;
    g_anchorOn   = false;
    g_waterWalkOn = false;
    g_sinkOn     = false;
    PsychoStageLoad(); // (Silver's Psychokinesis: off without an extra that has it)
    if (!g_cur)
        return;
    const Abilities *c = &g_cur->ab;
    g_animAnchor = HasAnim(g_cur->animBase + 2);
    g_animSink   = HasAnim(g_cur->animBase + 5);
    g_anchorOn   = c->anchorThrow && g_animAttack >= 0 && Player_State_Ground_; // (its hits: when the hit classes are wrapped)
    g_sinkOn     = c->sink && g_animSink >= 0 && g_cur->more.sinkFrames[0] >= 0 && Player_State_Ground_;
    g_waterWalkOn = c->waterWalk && Player_State_Ground_ && RSDK.FindObject("Water");
    g_anchorSfx  = SfxOf(g_cur->more.anchorSound);
    g_latchSfx   = SfxOf(g_cur->more.latchSound);
    g_sinkSfx    = SfxOf(g_cur->more.sinkSound);
    if (g_anchorOn) {
        g_engineFrameOK = CheckEngineFrames();
        memset(&g_anchorFrame, 0, sizeof(g_anchorFrame));
        g_anchorFrame.hitboxCount = 1;
        for (int32 i = 0; i < 8; ++i) {
            g_anchorFrame.hitboxes[i].left = g_anchorFrame.hitboxes[i].top = -ANCHOR_BOX;
            g_anchorFrame.hitboxes[i].right = g_anchorFrame.hitboxes[i].bottom = ANCHOR_BOX;
        }
        memset(&g_anchorBox, 0, sizeof(g_anchorBox));
        g_anchorBox.frames      = (SpriteFrame *)&g_anchorFrame;
        g_anchorBox.frameCount  = 1;
        g_anchorBox.animationID = ANI_JUMP;
    }
    if (c->anchorThrow || c->sink || c->waterWalk || c->floatLean || g_cur->more.copySets || g_cur->shot2.onCharge)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: anchor %d (pose %d, anchor %d), water walk %d, sink %d (anim %d), lean %d, copy heads %d, "
                      "charge %d (flash %d/%d/%d), draw %s",
                      g_cur->name, g_anchorOn, g_animAttack, g_animAnchor, g_waterWalkOn, g_sinkOn, g_animSink, c->floatLean,
                      g_cur->more.copySets, g_cur->shot2.onCharge, g_cur->more.chargeCount[0], g_cur->more.chargeCount[1],
                      g_cur->more.chargeCount[2], g_drawWrapped ? "wrapped" : "NOT wrapped");
}

// Player 1's frame (OnUpdate, the game running), before the shots and the melee: the sink, the anchor; then (after
// them all) the water walk: MoreAfter
static void MoreUpdate(EntityPlayer *p1, bool32 transformed)
{
    if (!IsExtra(p1))
        return;
    if (g_sinkOn)
        SinkUpdate(p1, transformed);
    if (g_anchorOn)
        AnchorUpdate(p1, transformed);
    PsychoUpdate(p1, transformed); // (Silver: before the melee, which waves only when Y caught nothing)
}

static void MoreAfter(EntityPlayer *p1)
{
    if (g_waterWalkOn && IsExtra(p1))
        WaterWalk(p1);
}

// Link: the Player's draw wrapped and the hooks, only when a package needs them
static void LinkMore(void)
{
    bool32 draw = false, sink = false, water = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        const Extra *e = &g_extras[i];
        draw |= e->ab.anchorThrow || e->ab.floatLean || e->more.copySets > 0 || e->shot2.onCharge || e->ab.psychoGrab
                || e->ab.chaosControl; // (Chaos Control's afterimages: ManiaGhost.h)
        sink |= e->ab.sink != 0;
        water |= e->ab.waterWalk != 0;
    }
    if (draw) {
        Mod.RegisterObject(NULL, NULL, "Player", sizeof(EntityPlayer), 0, 0, NULL, NULL, NULL, MoreDraw, NULL, NULL, NULL, NULL, NULL, NULL,
                           NULL);
        g_drawWrapped = true;
    }
    if (sink && Player_Input_P1_)
        Mod.RegisterStateHook(Player_Input_P1_, Hook_SinkInput, false);
    if (water)
        Mod.RegisterObjectHook((void **)&g_waterLite, "Water");
    if (!Player_State_Ground_) // (LinkShots finds it when an extra has a shot, a melee or the anchor)
        Player_State_Ground_ = Mod.GetPublicFunction(NULL, "Player_State_Ground");
    if (!Player_State_Crouch_)
        Player_State_Crouch_ = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
    if (!Player_State_LookUp_)
        Player_State_LookUp_ = Mod.GetPublicFunction(NULL, "Player_State_LookUp");
    if (!Player_State_Roll_)
        Player_State_Roll_ = Mod.GetPublicFunction(NULL, "Player_State_Roll");
    if (!Player_State_Spindash_)
        Player_State_Spindash_ = Mod.GetPublicFunction(NULL, "Player_State_Spindash");
    if (!Player_State_Peelout_)
        Player_State_Peelout_ = Mod.GetPublicFunction(NULL, "Player_State_Peelout");
}

#endif // MANIA_MORE_H
