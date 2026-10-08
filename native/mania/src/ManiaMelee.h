// NoSwapMania's melee: Y's pose move for an extra without a shot on Y (abilities.py "melee"), the S3&K DLL's ported
// (native/src/NoSwapS3K.cpp, the melee in its jump ability code), with its options:
//   - the pose: the melee animation (ability slot 43; in the air slot 44 with shotAirFrames), one frame per shotTicks game
//     frames (shotFrames / shotAirFrames in all), from player 1's frame (after every entity's update, as ShotFrame); on the
//     ground as itself, in the air reported as the jump (an attack, as the other air moves); shotCooldown frames from one
//     to the next; shotStop: he stands still for it on the ground; shotHang: he hangs still in the air;
//   - its reach: the pose frames' own boxes (build_s3k_art: melee_reach per frame, round him with melee_radial: Silver's
//     wave), which hit through the shots' stand-in (StrikeUpdate: player 1 stands in at his own place with the pose frame
//     as his hitbox during a hit class's update, every other frame, his own turn on the others);
//   - melee_nuke (nukeAt, nukeHit, nukeReachX / Y, nukeFlash, nukeSound): at the move's game frame nukeAt, for nukeHit
//     game frames everything whose position is within nukeReachX px either side of him and nukeReachY above and below
//     (0: anything on screen, Tails Doll's) is hit, by a stand-in with that whole box as his hitbox; each object once per
//     nuke (so a boss takes one hit); the flash: the screen darkened to black by nukeFlash[i] (0-255) per game frame
//     (FillScreen, drawn under the HUD: a runtime effect, the sprites untouched);
//   - shotSafe: nothing hurts him during it (the post-hit blink's rule, held at 3 frames: no flicker);
//   - shotCost: as it ends, a normal hit through the game's own Player_Hit (a shield lost, or the rings scattered, and at
//     0 rings he dies), knocked back from the way he faces; not while hurt, held by an object, invincible (a star) or
//     Super. Bomb's Self-Destruct;
//   - shotBlink: after it, the post-hit blink for that many frames (Espio's Leaf Swirl);
//   - melee_run / melee_up (meleeRunSpeed / Boost / Frames, meleeUp / UpRings / UpFrames: Axel's Grand Upper and Dragon
//     Wing): as Y is pressed on the ground, up held with meleeUpRings rings (taken; fewer: the plain melee) shows ability
//     slot 46's frames, else running (at least meleeRunSpeed either way) slot 45's, held at least meleeRunBoost the way he
//     faces (not standing still for it); their reach is their frames' own boxes (build_s3k_art.py), as the plain pose's.
// A hit, or an object taking him (a state that isn't his own movement), ends it early: no cost, no nuke still to come.
// Included once, by NoSwapMania.c (after "shots").
#ifndef MANIA_MELEE_H
#define MANIA_MELEE_H

#include <stddef.h>

#define STRUCK_MAX  (0x1000) // entity slots (ENTITY_COUNT is 0x940)
#define FLASH_GROUP (13)     // the flash's draw group: over the stage, under the HUD (Zone->hudDrawGroup, 14)

static void (*Player_Hit_)(EntityPlayer *player);
static void (*Player_State_Ground_)(void);
static void (*Player_State_Crouch_)(void);
static void (*Player_State_LookUp_)(void);
static void (*Player_State_Roll_)(void);
static void (*Player_State_Spindash_)(void);
static void (*Player_State_Peelout_)(void);

static struct {
    int32 total;     // the move's game frames
    bool32 air;      // showing the air pose
    bool32 poseOK;   // pose: the pose frame shown this frame, reported as the jump (the reach's stand-in hitbox)
    Animator pose;
} g_pop;
static int32 g_meleeCooldown = 0;
static int32 g_meleePose = 0; // melee_run / melee_up: 0 the plain pose, 4 running, 5 up + Y (as the S3&K DLL's whipAim)
static int32 g_meleePrevSuper = SUPERSTATE_NONE;
static uint16 g_meleeSfx = 0xFFFF, g_nukeSfx = 0xFFFF;
static uint16 g_meleeRunSfx = 0xFFFF, g_meleeUpSfx = 0xFFFF; // melee_run / melee_up's own (else g_meleeSfx)
static uint8 g_struck[STRUCK_MAX / 8]; // the objects this melee (or its nuke) has hit
static int32 CrossWhipAnim(EntityPlayer *p, bool32 air, bool32 start, int32 anim); // (ManiaCross.h: John's whip poses)
static bool32 CrossUpThrow(EntityPlayer *p);                                       // (... and his up + Y sub-weapon)
static bool32 CrossWhipShowing(EntityPlayer *p);

static struct {
    int32 left;  // game frames of hits left
    int32 flash; // the flash frame showing (-1: none)
} g_nuke;

// The engine's own sprite frame (RSDK Animation.hpp: the game's SpriteFrame, then its hitboxes), for the nuke's box: a
// frame of our own whose hitbox 0 is the whole reach. Checked against a real frame at stage load (g_engineFrameOK).
typedef struct {
    SpriteFrame frame;
    uint8 hitboxCount;
    Hitbox hitboxes[8];
} EngineSpriteFrame;
static EngineSpriteFrame g_nukeFrame;
static Animator g_nukeAnim;
static bool32 g_engineFrameOK = false;

static bool32 Struck(int32 slot) { return slot >= 0 && slot < STRUCK_MAX && (g_struck[slot >> 3] >> (slot & 7) & 1); }
static void Strike(int32 slot)
{
    if (slot >= 0 && slot < STRUCK_MAX)
        g_struck[slot >> 3] |= (uint8)(1 << (slot & 7));
}

// His own movement's states (the melee starts and goes on only in these; anything else is an object holding him)
static bool32 Free(EntityPlayer *p)
{
    void *s = (void *)p->state;
    return s == (void *)Player_State_Ground_ || s == (void *)Player_State_Air_ || s == (void *)Player_State_Crouch_
           || s == (void *)Player_State_LookUp_ || s == (void *)Player_State_Roll_ || s == (void *)Player_State_Spindash_
           || s == (void *)Player_State_Peelout_;
}

static bool32 CheckEngineFrames(void)
{
    Animator a;
    memset(&a, 0, sizeof(a));
    RSDK.SetSpriteAnimation(g_extraFrames, ANI_JUMP, &a, true, 0);
    if (!a.frames || a.frameCount < 2)
        return false;
    char *base = (char *)a.frames;
    char *h0   = (char *)RSDK.GetHitbox(&a, 0);
    char *h01  = (char *)RSDK.GetHitbox(&a, 1);
    a.frameID  = 1;
    char *h1   = (char *)RSDK.GetHitbox(&a, 0);
    return h0 - base == (ptrdiff_t)offsetof(EngineSpriteFrame, hitboxes) && h01 - h0 == (ptrdiff_t)sizeof(Hitbox)
           && h1 - h0 == (ptrdiff_t)sizeof(EngineSpriteFrame);
}

// Stage load (from ShotsStageLoad, which then fills this stage's hit classes when g_meleeOn)
static void MeleeStageLoad(void)
{
    g_meleeOn = false;
    g_meleeLeft = 0;
    memset(&g_pop, 0, sizeof(g_pop));
    memset(&g_nuke, 0, sizeof(g_nuke));
    g_nuke.flash   = -1;
    g_meleeCooldown  = 0;
    g_meleePose      = 0;
    g_meleePrevSuper = SUPERSTATE_NONE;
    if (!g_cur || !g_cur->ab.shot || !Player_Hit_ || (g_cur->shot.motion != SHOT_NONE && !g_cur->shot.downOnly && !g_cur->shot.onSlam && !g_cur->shot.onGrab && !g_cur->shot.upOnly))
        return; // (a shot on Y alone: Y is the shot's; a grab shot leaves Y to Psychokinesis and this; up + Y: John's)
    const Abilities *ab = &g_cur->ab;
    if (HasAnim(g_cur->animBase + 2) < 0 || ab->shotFrames <= 0) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s: no melee animation (ability slot 43) or frames: no melee", g_cur->name);
        return;
    }
    g_meleeSfx        = g_cur->shotSound[0] ? RSDK.GetSfx(g_cur->shotSound) : 0xFFFF;
    g_meleeRunSfx     = g_cur->meleeRunSound[0] ? RSDK.GetSfx(g_cur->meleeRunSound) : g_meleeSfx;
    g_meleeUpSfx      = g_cur->meleeUpSound[0] ? RSDK.GetSfx(g_cur->meleeUpSound) : g_meleeSfx;
    g_nukeSfx       = g_cur->nukeSound[0] ? RSDK.GetSfx(g_cur->nukeSound) : 0xFFFF;
    g_engineFrameOK = CheckEngineFrames();
    g_meleeOn         = true;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee: %s, %d frames (air %d) of %d, cooldown %d%s%s%s%s; nuke at %d for %d, reach %d x %d, flash %d; "
                  "sounds %s (%d) / %s (%d); engine frame layout %s",
                  g_cur->name, ab->shotFrames, ab->shotAirFrames, ab->shotTicks, ab->shotCooldown, ab->shotStop ? ", stop" : "",
                  ab->shotHang ? ", hang" : "", ab->shotSafe ? ", safe" : "", ab->shotCost ? ", cost" : "", ab->nukeAt, ab->nukeHit,
                  ab->nukeReachX, ab->nukeReachY, g_cur->nukeFlashCount, g_cur->shotSound, g_meleeSfx, g_cur->nukeSound, g_nukeSfx,
                  g_engineFrameOK ? "checks out" : "DIFFERENT (the nuke hits at each object with his own frame's box)");
}

static void NukeStart(void)
{
    const Abilities *ab = &g_cur->ab;
    g_nuke.left  = ab->nukeHit;
    g_nuke.flash = g_cur->nukeFlashCount > 0 ? 0 : -1;
    // the box: round him (nukeReachX / Y), or (0) the screen's own size round its middle, 16 px past its edges
    int32 rx = ab->nukeReachX > 0 ? ab->nukeReachX : (ScreenInfo ? ScreenInfo->center.x : 212) + 16;
    int32 ry = ab->nukeReachX > 0 ? ab->nukeReachY : (ScreenInfo ? ScreenInfo->center.y : 120) + 16;
    memset(&g_nukeFrame, 0, sizeof(g_nukeFrame));
    g_nukeFrame.hitboxCount = 1;
    for (int32 i = 0; i < 8; ++i) {
        g_nukeFrame.hitboxes[i].left   = (int16)-rx;
        g_nukeFrame.hitboxes[i].top    = (int16)-ry;
        g_nukeFrame.hitboxes[i].right  = (int16)rx;
        g_nukeFrame.hitboxes[i].bottom = (int16)ry;
    }
    memset(&g_nukeAnim, 0, sizeof(g_nukeAnim));
    g_nukeAnim.frames      = (SpriteFrame *)&g_nukeFrame;
    g_nukeAnim.frameCount  = 1;
    g_nukeAnim.animationID = ANI_JUMP;
    if (g_nukeSfx != 0xFFFF)
        RSDK.PlaySfx(g_nukeSfx, false, 255);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee: the nuke, %d frames, box %d x %d", g_nuke.left, rx, ry);
}

// The melee's cost (melee_cost): a normal hit, the game's own (Player_HurtFlip's knock-back, then Player_Hit)
static void MeleeCost(EntityPlayer *p)
{
    const char *why = Hurt(p) ? "hurt already" : !Free(p) ? "held by an object" : p->invincibleTimer ? "invincible"
                      : p->superState == SUPERSTATE_SUPER ? "Super" : NULL;
    if (why) {
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee cost: none (%s)", why);
        return;
    }
    p->velocity.x = p->direction != FLIP_NONE ? 0x20000 : -0x20000;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee cost: Player_Hit (rings %d)", p->rings);
    // (this runs from MODCB_ONUPDATE, after the entity loop, so SceneInfo->entity is the list's last slot, not him; Ring_LoseRings
    // gives the scattered rings self->drawGroup (RSDK_THIS), which was that blank slot's group 0, under the stage: invisible rings.
    // So he is "self" for the call, as he would be for a hit in his own update.)
    Entity *prevEntity = SceneInfo->entity;
    int32 prevSlot     = SceneInfo->entitySlot;
    SceneInfo->entity     = (Entity *)p;
    SceneInfo->entitySlot = RSDK.GetEntitySlot(p);
    Player_Hit_(p);
    SceneInfo->entity     = prevEntity;
    SceneInfo->entitySlot = prevSlot;
}

// Over: finished (its blink and cost), or cut short (neither)
static void MeleeEnd(EntityPlayer *p, bool32 finished)
{
    const Abilities *ab = &g_cur->ab;
    g_meleeLeft    = 0;
    g_pop.poseOK = false;
    if (Showing(p, g_animShot) || Showing(p, g_animShotAir) || CrossWhipShowing(p)
        || (g_meleePose && (Showing(p, HasAnim(g_cur->animBase + 3)) || Showing(p, HasAnim(g_cur->animBase + 4)))))
        RSDK.SetSpriteAnimation(p->aniFrames, p->onGround ? ANI_IDLE : ANI_JUMP, &p->animator, true, 0);
    if (!finished)
        return;
    if (ab->shotBlink > 0)
        p->blinkTimer = ab->shotBlink;
    if (ab->shotCost)
        MeleeCost(p);
}

// Player 1's frame (after every entity's update). transformed: Y made him Super this frame (no melee: Origins' rule)
static void MeleeFrame(EntityPlayer *p, bool32 transformed)
{
    const Abilities *ab = &g_cur->ab;
    bool32 air          = !p->onGround;
    if (g_meleeCooldown > 0)
        g_meleeCooldown--;
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    bool32 press    = key && key->press && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled && !transformed && !Hurt(p) && Free(p)
                   && !(g_cur->shot.motion != SHOT_NONE && g_cur->shot.downOnly && p->down) // (down + Y: the shot's)
                   && !CrossUpThrow(p); // (up + Y: John's sub-weapon, ManiaCross.h)
    press = PsychoWave(press); // (Silver: the wave only when Y caught nothing; ManiaPsycho.h)
    if (g_meleeLeft == 0 && g_meleeCooldown == 0 && press) {
        g_pop.total   = ab->shotFrames > ab->shotAirFrames ? ab->shotFrames : ab->shotAirFrames;
        if (ab->meleeRunFrames > g_pop.total)
            g_pop.total = ab->meleeRunFrames;
        if (ab->meleeUpFrames > g_pop.total)
            g_pop.total = ab->meleeUpFrames;
        g_meleePose = 0; // melee_run / melee_up: the pose by how he is as Y is pressed
        if (!air && ab->meleeUp && p->up && p->rings >= ab->meleeUpRings && HasAnim(g_cur->animBase + 4) >= 0) {
            p->rings -= ab->meleeUpRings;
            g_meleePose = 5;
        }
        else if (!air && ab->meleeRunSpeed > 0 && Abs(p->groundVel) >= ab->meleeRunSpeed && HasAnim(g_cur->animBase + 3) >= 0) {
            g_meleePose = 4;
        }
        g_meleeLeft     = g_pop.total;
        g_meleeCooldown = ab->shotCooldown;
        memset(g_struck, 0, sizeof(g_struck));
        uint16 sfx = g_meleePose == 5 ? g_meleeUpSfx : g_meleePose == 4 ? g_meleeRunSfx : g_meleeSfx;
        if (sfx != 0xFFFF)
            RSDK.PlaySfx(sfx, false, 255);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee (%s)", air ? "air" : "ground");
        if (ab->cycleCount > 0) { // ability_cycle: the melee's pose is the switch; the next move is active
            g_copy = (g_copy + 1) % ab->cycleCount;
            MoveState *m = StateOf(p);
            if (air && m) { // the move going on or used this jump ends; an unused jump keeps its press for the new one
                m->dash = 0;
                m->dbl  = 0;
                m->kick = 0;
                if (m->umbrella == 1)
                    m->umbrella = 2;
            }
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "copycat: move %d of %d", g_copy + 1, ab->cycleCount);
        }
    }
    if (g_meleeLeft <= 0)
        return;
    if (Hurt(p) || !Free(p)) {
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee: cut short (%s)", Hurt(p) ? "hurt" : "an object took him");
        MeleeEnd(p, false);
        return;
    }
    int32 elapsed  = g_pop.total - g_meleeLeft;
    bool32 airShot = air && ab->shotAirFrames > 0 && g_animShotAir >= 0;
    int32 frames   = (airShot ? ab->shotAirFrames : ab->shotFrames) / ab->shotTicks;
    if (frames < 1)
        frames = 1;
    int32 anim = CrossWhipAnim(p, air, elapsed == 0, airShot ? g_animShotAir : g_animShot); // (John's whip poses: ManiaCross.h)
    bool32 runPose = g_meleePose == 4 && ab->meleeRunFrames > 0, upPose = g_meleePose == 5 && ab->meleeUpFrames > 0;
    if (runPose || upPose) { // (melee_run / melee_up: their own frames, on the ground and in the air alike)
        airShot = false;
        anim    = HasAnim(g_cur->animBase + (runPose ? 3 : 4));
        frames  = (runPose ? ab->meleeRunFrames : ab->meleeUpFrames) / ab->shotTicks;
        if (frames < 1)
            frames = 1;
    }
    Show(p, anim, air, elapsed == 0 || airShot != g_pop.air);
    g_pop.air  = airShot;
    int32 at   = elapsed / ab->shotTicks;
    if (at > frames - 1)
        at = frames - 1;
    if (at > p->animator.frameCount - 1)
        at = p->animator.frameCount - 1;
    p->animator.frameID = at < 0 ? 0 : at;
    p->animator.timer   = 0;
    p->animator.speed   = 0;
    g_pop.pose          = p->animator;
    g_pop.pose.animationID = ANI_JUMP;
    g_pop.poseOK        = true;
    if (ab->shotStop && !air && !runPose) {
        p->groundVel  = 0;
        p->velocity.x = 0;
    }
    if (runPose && ab->meleeRunBoost > 0) { // melee_run's boost: at least meleeRunBoost the way he faces
        int32 dir = (p->direction & FLIP_X) ? -1 : 1;
        if (air)
            p->velocity.x = dir * (dir * p->velocity.x > ab->meleeRunBoost ? dir * p->velocity.x : ab->meleeRunBoost);
        else
            p->groundVel = dir * (dir * p->groundVel > ab->meleeRunBoost ? dir * p->groundVel : ab->meleeRunBoost);
    }
    if (ab->shotHang && air) {
        p->velocity.x = 0;
        p->velocity.y = 0;
    }
    if (ab->shotBoost > 0) { // a burst of speed (melee_boost: Mecha's Jet Boost, Bark's Bear Rush): at least shotBoost the
        int32 dir = (p->direction & FLIP_X) ? -1 : 1; // way he faces, on the ground or level in the air
        if (air) {
            p->velocity.x = dir * (dir * p->velocity.x > ab->shotBoost ? dir * p->velocity.x : ab->shotBoost);
            p->velocity.y = 0;
        }
        else {
            p->groundVel = dir * (dir * p->groundVel > ab->shotBoost ? dir * p->groundVel : ab->shotBoost);
        }
    }
    if (ab->nukeAt >= 0 && elapsed == ab->nukeAt)
        NukeStart();
    if (ab->shotSafe && p->blinkTimer < 3)
        p->blinkTimer = 3; // (Player_Update counts it down to 2 before anything can hit him: visible, and Player_Hurt says no)
    if (--g_meleeLeft == 0 || (elapsed + 1) / ab->shotTicks >= frames)
        MeleeEnd(p, true);
}

// A hit class's update (HitUpdate): the nuke, or the melee's reach, stands in for it when it's in reach and not hit
// yet; true: its update has run (with the stand-in)
static bool32 StrikeUpdate(Entity *self, int32 kind, EntityPlayer *p)
{
    (void)kind;
    if (!g_meleeOn || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_ || p->state == Player_State_Drown_)
        return false;
    int32 slot = RSDK.GetEntitySlot(self);
    if (slot < 0 || slot >= STRUCK_MAX || Struck(slot))
        return false;
    const Abilities *ab = &g_cur->ab;
    const Animator *anim = NULL;
    Vector2 pos = p->position;
    int32 dx = Abs(self->position.x - p->position.x), dy = Abs(self->position.y - p->position.y);
    if (g_nuke.left > 0) {
        bool32 in;
        if (ab->nukeReachX > 0) {
            in = dx <= (ab->nukeReachX << 16) && dy <= (ab->nukeReachY << 16);
        }
        else {
            Vector2 range = { 16 << 16, 16 << 16 };
            in = RSDK.CheckOnScreen(self, &range);
            if (ScreenInfo) { // (the box round the screen's middle)
                pos.x = (ScreenInfo->position.x + ScreenInfo->center.x) << 16;
                pos.y = (ScreenInfo->position.y + ScreenInfo->center.y) << 16;
            }
        }
        if (!in)
            return false;
        if (g_engineFrameOK) {
            anim = &g_nukeAnim;
        }
        else if (g_pop.poseOK || Showing(p, g_animShot)) { // (the fallback: his own frame's box, at the object)
            anim = &g_pop.pose;
            pos  = self->position;
        }
    }
    else if (g_meleeLeft > 0 && g_pop.poseOK && ab->nukeAt < 0) {
        // the reach: the pose frame's box at him (loosely near: the game's own touch test decides); his own turn every
        // other frame unless nothing can hurt him meanwhile
        int32 near = (REACH_BOSS + 64) << 16;
        if (dx > near || dy > near || ((g_frame & 1) && !ab->shotSafe))
            return false;
        anim = &g_pop.pose;
    }
    if (!anim)
        return false;
    if (StandInAt(self, pos, anim, p->direction, p->collisionPlane, p)) {
        Strike(slot);
        static int32 logs = 0;
        if (logs++ < 60)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "melee: %s hit class %d (slot %d, %s)", g_nuke.left > 0 ? "the nuke" : "the reach", self->classID,
                          slot, kind == HIT_BOSS ? "boss" : kind == HIT_ITEMBOX ? "item box" : "badnik");
    }
    return true;
}

// The frame's end (OnUpdate, the game running): the nuke's hits and flash count down; then player 1's melee
static void MeleeUpdate(EntityPlayer *p1, bool32 transformed)
{
    if (g_nuke.left > 0)
        g_nuke.left--;
    if (g_nuke.flash >= 0 && ++g_nuke.flash >= g_cur->nukeFlashCount)
        g_nuke.flash = -1;
    if (IsExtra(p1))
        MeleeFrame(p1, transformed);
}

// The nuke's flash (MODCB_ONDRAW, once per draw group)
static void MeleeDraw(void *data)
{
    if (!g_active || !g_meleeOn || !g_cur || g_nuke.flash < 0 || g_nuke.flash >= g_cur->nukeFlashCount || (int32)(size_t)data != FLASH_GROUP)
        return;
    int32 dark = g_cur->nukeFlash[g_nuke.flash];
    if (dark > 0)
        RSDK.FillScreen(0x000000, dark, dark, dark);
}

// Link: the game functions it calls (false: missing)
static bool32 LinkMelee(void)
{
    Player_Hit_            = Mod.GetPublicFunction(NULL, "Player_Hit");
    Player_State_Ground_   = Mod.GetPublicFunction(NULL, "Player_State_Ground");
    Player_State_Crouch_   = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
    Player_State_LookUp_   = Mod.GetPublicFunction(NULL, "Player_State_LookUp");
    Player_State_Roll_     = Mod.GetPublicFunction(NULL, "Player_State_Roll");
    Player_State_Spindash_ = Mod.GetPublicFunction(NULL, "Player_State_Spindash");
    Player_State_Peelout_  = Mod.GetPublicFunction(NULL, "Player_State_Peelout");
    if (!Player_Hit_ || !Player_State_Ground_ || !Player_State_Crouch_ || !Player_State_LookUp_ || !Player_State_Roll_
        || !Player_State_Spindash_ || !Player_State_Peelout_) {
        Player_Hit_ = NULL;
        return false;
    }
    bool32 flash = false;
    for (int32 i = 0; i < g_extraCount; ++i) flash |= g_extras[i].nukeFlashCount > 0;
    if (flash)
        Mod.AddModCallback(MODCB_ONDRAW, MeleeDraw);
    return true;
}

#endif
