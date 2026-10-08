// NoSwapMania: hosting on Tails and Knuckles, and the moves of the extras hosted there (their data: ManiaHostData.h).
//
// Hosting: an extra plays on its package's "host" character (tools/build_mania_art.py: extras.py "base"): Sonic (most),
// Tails (Cream, Charmy, Flicky: his flight, Player_JumpAbility_Tails / Player_State_TailsFlight, with their own Fly...
// frames) or Knuckles (Rouge: his glide and climb, with hers). Its Player.bin follows the host's Mania file (Tails.bin /
// Knux.bin: 55 animations, their own from 48 on), so the host's own code runs on the extra's animations, as in the
// Origins S3&K builds. What changes with the host:
//   - who: IsExtra is "player on the host's character ID" (g_hostID); the save select's extra shows on the host's frame
//     (UISaveSlot frameID 1 Sonic, 2 Tails, 3 Knuckles), so the game starts, saves and loads that character;
//   - sprites: Player->sonicFrames / superFrames, tailsFrames or knuxFrames are the extra's (HostSetFrames), and
//     Tails' twin tails are off: Player->tailsTailsFrames and each player's tailFrames are -1, so Player_Update never
//     animates them and Player_Draw never draws them (Charmy, Cream and Flicky have no twin tails; the S3&K DLL's
//     NoTail.bin);
//   - colours: the extra's own stay in Sonic's slots 64-69 and the free global ones (the palette code is the same for
//     every host; the host's own slots, 70-75 / 80-85, are left to the game). Super: the game fades the host's slots, so
//     for Tails / Knuckles HostSuperFrame blends the extra's Sonic slots itself, from Player->superPalette_Sonic's row 0
//     (its own colours) to row 1 (its glow: ManiaHud.h) by the host's own blend amount;
//   - screens (ManiaHud.h): the host's Continue.bin animations, signpost face animation, BSS_Player frames, and for
//     Knuckles the act clear name moved to where KNUCKLES ends.
// Moves (player 1, after every entity's update, as the S3&K DLL's after the player's update):
//   - aimDashY (Charmy's Stinger): Y in mid-air, in the air state or Tails' flight (out of it for good), once per airborne
//     period: the aimed dash (Hook_StateAir's aim_dash: straight, up or down by the d-pad, dashFrames), his flight held off
//     meanwhile (jumpAbilityState 0, given back after a dash from the air state);
//   - screwKick on Y (Rouge's Screw Kick): Y in mid-air or out of Knuckles' glide, once per airborne period: 45 degrees
//     down and forward (kickX / kickY, the direction locked) until she lands, attacking; landing bounces her (kickBounce,
//     along the ground's angle); a spring or anything sending her up ends it;
//   - batGlide (Rouge): Knuckles' glide state, wrapped (after it, before the game moves her): its x speed glideSpeed / 1000
//     of his at every moment, and a gentler sink (glideSink, glideGravity), as the S3&K DLL's BatGlide;
//   - treasureSense (Rouge's Treasure Sense, TreasureSense.h): Y on the ground, a listening pause (her Look Up pose), then
//     the game's ring (Global/Ring.bin) blinks at the screen's edge toward the nearest hidden giant ring (SpecialRing still
//     enabled: not collected), faster the closer it is; nothing there: senseSound. Drawn in MODCB_ONDRAW (group 13);
//   - jewelThief (Rouge's Jewel Thief): a 10-ring monitor gives her 20: ItemBox_State_Break wrapped; the frame it gives
//     the powerup (its state then IconFinish), a ring box for player 1 adds 10 more through Player_GiveRings, silently.
// Included once, by NoSwapMania.c (after ManiaBatch.h; LinkHost after LinkHud).
#ifndef MANIA_HOST_H
#define MANIA_HOST_H

static void (*Player_State_TailsFlight_)(void);
static void (*Player_State_KnuxGlideLeft_)(void);
static void (*Player_State_KnuxGlideRight_)(void);
static void (*Player_GiveRings_)(EntityPlayer *player, int32 amount, bool32 playSfx);
static void (*ItemBox_State_Break_)(void);
static void (*ItemBox_State_IconFinish_)(void);

static const char *const HOST_FILE[3] = { "Players/Sonic.bin", "Players/Tails.bin", "Players/Knux.bin" };
static const int32 HOST_ID[3]         = { ID_SONIC, ID_TAILS, ID_KNUCKLES };

// Offsets in the decompilation's structs (compiled against SonicMania/Objects, as check_layout.sh does)
#define ITEMBOX_STATE        (96)  // EntityItemBox.state
#define ITEMBOX_TYPE         (104) // .type (ITEMBOX_RING 0)
#define ITEMBOX_STORED       (128) // .storedEntity (the player it rewards)
#define SPECIALRING_ENABLED  (160) // EntitySpecialRing.enabled (not collected yet)
#define SENSE_MARGIN     (12) // (tools/treasure_sense.py)
#define SENSE_NEAR       (64)
#define SENSE_FAR        (2048)
#define SENSE_BLINK_NEAR (2)
#define SENSE_BLINK_FAR  (16)
#define SENSE_GROUP      (13) // the marker's draw group: over the stage, under the HUD (14)
#define SENSE_HOLD_FRAME (5)  // Look Up's held frame (Player_State_LookUp; build_mania_art.py RETURN_TO_IDLE)

static struct {
    bool32 stingUsed, stinging; // the Stinger: used this airborne period; going (Hook_StateAir's aim dash runs it)
    int32 stingJump;            // ... jumpAbilityState to give back after it
    bool32 kick, kickUsed, kickLeft; // the Screw Kick on Y
    int32 kickJump;
    bool32 glided;   // the bat glide: gliding last frame
    int32 glideVY;   // ... its fall speed then
    int32 sense;     // Treasure Sense: 0 ready; 1..pause the pause; then the marker; below 0 the cooldown
    Vector2 last;    // her position last frame (a warp or respawn ends it)
    bool32 superWrote; // the Super blend is in her Sonic slots
} g_hm;
static uint16 g_ringFrames = 0xFFFF; // Global/Ring.bin (the Treasure Sense marker)

static int32 HostIndex(const Extra *e) { return e ? e->more.host.index : 0; }
static int32 HostOf(int32 extra) { return extra >= 0 && extra < g_extraCount ? g_extras[extra].more.host.id : ID_SONIC; }
// UISaveSlot's frameID for the extra (1 Sonic, 2 Tails, 3 Knuckles)
static int32 HostFrame(int32 extra) { return 1 + (extra >= 0 && extra < g_extraCount ? g_extras[extra].more.host.index : 0); }

// ------------------------------------------------------------------------------------------------ sprites
// The extra's frames in its host's place (Player_Create, after the stage load, gives the host its frames from here; an
// object reloading the host's file later gets the same ID back, which KeepSprites swaps)
static void HostSetFrames(void)
{
    switch (HostIndex(g_cur)) {
        default:
            Player->sonicFrames = g_extraFrames;
            Player->superFrames = g_extraFrames;
            break;
        case 1:
            Player->tailsFrames      = g_extraFrames;
            Player->tailsTailsFrames = 0xFFFF; // (no twin tails)
            break;
        case 2: Player->knuxFrames = g_extraFrames; break;
    }
}

// Stage load (OnStageLoad, the extra's sprites loaded): its host, the host's own files' IDs, its frames in their place
static void HostStageLoad(void)
{
    int32 h       = HostIndex(g_cur);
    g_hostID      = HOST_ID[h];
    g_sonicFrames = RSDK.LoadSpriteAnimation(HOST_FILE[h], SCOPE_STAGE);
    g_superFrames = h == 0 ? RSDK.LoadSpriteAnimation("Players/SuperSonic.bin", SCOPE_STAGE) : g_sonicFrames;
    HostSetFrames();
    memset(&g_hm, 0, sizeof(g_hm));
    g_ringFrames = g_cur->more.host.treasureSense ? RSDK.LoadSpriteAnimation("Global/Ring.bin", SCOPE_STAGE) : 0xFFFF;
    if (h)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s plays on %s", g_cur->name, h == 1 ? "Tails" : "Knuckles");
}

// Each player, late: no twin tails on an extra hosted on Tails
static void HostKeep(EntityPlayer *p)
{
    if (HostIndex(g_cur) == 1)
        p->tailFrames = 0xFFFF;
}

// ------------------------------------------------------------------------------------------------ Super
static color HostLerp(color a, color b, int32 amount)
{
    color out = 0;
    for (int32 shift = 16; shift >= 0; shift -= 8) {
        int32 x = (a >> shift) & 0xFF, y = (b >> shift) & 0xFF;
        out |= (color)(x + (y - x) * amount / 256) << shift;
    }
    return out;
}

// Each frame, late (after ManiaHud.h's SuperGlowFrame): Tails' / Knuckles' Super fades their own slots, so the extra's
// Sonic slots follow the host's blend amount here (bank 0)
static void HostSuperFrame(void)
{
    if (!g_active || !g_cur || HostIndex(g_cur) == 0 || !Player)
        return;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p))
        return;
    int32 amount = p->superBlendAmount < 0 ? 0 : p->superBlendAmount > 256 ? 256 : p->superBlendAmount;
    bool32 on    = p->superState != SUPERSTATE_NONE || amount > 0;
    if (!on && !g_hm.superWrote)
        return;
    g_hm.superWrote = on;
    for (int32 i = 0; i < g_cur->ownCount; ++i) {
        int32 slot = g_cur->ownSlot[i];
        int32 c    = slot - PLAYER_PALETTE_INDEX_SONIC;
        if (c < 0 || c >= PLAYER_PRIMARY_COLOR_COUNT)
            continue;
        RSDK.SetPaletteEntry(0, (uint8)slot, on ? HostLerp(Player->superPalette_Sonic[c], Player->superPalette_Sonic[6 + c], amount)
                                                : Player->superPalette_Sonic[c]);
    }
}

// ------------------------------------------------------------------------------------------------ the Stinger
static void Stinger(EntityPlayer *p, bool32 transformed)
{
    MoveState *m = StateOf(p);
    if (!m)
        return;
    bool32 air = !p->onGround;
    if (!air)
        g_hm.stingUsed = false;
    if (g_hm.stinging && m->aim == 0) { // over (Hook_StateAir: its frames up, or a spring, a hit, landing)
        g_hm.stinging = false;
        if (air && p->state == Player_State_Air_)
            p->jumpAbilityState = g_hm.stingJump;
    }
    bool32 flying   = Player_State_TailsFlight_ && p->state == Player_State_TailsFlight_;
    bool32 airState = p->state == Player_State_Air_;
    if (!g_aimDash || !air || g_hm.stingUsed || m->aim > 0 || !(airState || flying) || Hurt(p) || !YPressedP1(p, transformed))
        return;
    g_hm.stingUsed      = true;
    g_hm.stinging       = true;
    g_hm.stingJump      = flying ? 0 : p->jumpAbilityState; // (out of the flight for good, as the flight itself leaves it)
    p->jumpAbilityState = 0;                                // (no flight during the dash)
    if (flying)
        p->state = Player_State_Air_;
    m->aim     = g_cur->ab.dashFrames;
    m->aimDir  = p->up ? -1 : p->down ? 1 : 0;
    m->aimLeft = (p->direction & FLIP_X) != 0;
    Show(p, AimAnim(m->aimDir), true, true);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "stinger%s", flying ? " (out of flight)" : "");
}

// ------------------------------------------------------------------------------------------------ the Screw Kick on Y
static bool32 Gliding(EntityPlayer *p)
{
    return (Player_State_KnuxGlideLeft_ && p->state == Player_State_KnuxGlideLeft_)
           || (Player_State_KnuxGlideRight_ && p->state == Player_State_KnuxGlideRight_);
}

static void ScrewKickY(EntityPlayer *p, bool32 transformed)
{
    const Abilities *ab = &g_cur->ab;
    bool32 air          = !p->onGround;
    bool32 gliding      = Gliding(p);
    bool32 airState     = p->state == Player_State_Air_;
    if (!air && !g_hm.kick)
        g_hm.kickUsed = false;
    if (g_animAttack >= 0 && air && !g_hm.kick && !g_hm.kickUsed && (airState || gliding) && !Hurt(p) && YPressedP1(p, transformed)) {
        g_hm.kick = g_hm.kickUsed = true;
        g_hm.kickLeft = (p->direction & FLIP_X) != 0;
        g_hm.kickJump = gliding ? 0 : p->jumpAbilityState; // (out of the glide for good, as the glide leaves it)
        if (gliding)
            p->state = Player_State_Air_;
        Show(p, g_animAttack, true, true);
        PlayNamed(g_cur->kickSound);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "screw kick%s", gliding ? " (out of the glide)" : "");
    }
    else if (g_hm.kick) {
        if (!air) {
            if (p->state == Player_State_Air_ && ab->kickBounce) { // landed (the game hasn't seen it yet): a small bounce
                int32 a8      = p->angle & 0xFF;
                p->velocity.x = (int32)(((int64)p->groundVel * RSDK.Cos256(a8) + (int64)ab->kickBounce * RSDK.Sin256(a8)) >> 8);
                p->velocity.y = (int32)(((int64)p->groundVel * RSDK.Sin256(a8) - (int64)ab->kickBounce * RSDK.Cos256(a8)) >> 8);
                ToAirState(p);
                BackToJump(p);
            }
            else if (p->state == Player_State_Air_) {
                BackToJump(p); // (the game lands her from the jump ball)
            }
            g_hm.kick     = false;
            g_hm.kickUsed = true; // (no second kick in the bounce)
        }
        else if (p->state != Player_State_Air_ || Hurt(p)) { // an object took over, or a hit
            g_hm.kick = false;
        }
        else if (p->velocity.y <= 0x10000) { // a spring or anything else sending her up
            g_hm.kick           = false;
            p->jumpAbilityState = g_hm.kickJump;
            BackToJump(p);
        }
        else {
            Show(p, g_animAttack, true, false);
        }
    }
    if (g_hm.kick) {
        p->jumpAbilityState = 0; // (no glide out of the kick)
        p->direction        = g_hm.kickLeft ? FLIP_X : FLIP_NONE;
        p->velocity.x       = g_hm.kickLeft ? -ab->kickX : ab->kickX;
        p->velocity.y       = ab->kickY;
    }
}

// ------------------------------------------------------------------------------------------------ the bat glide
// After Knuckles' glide state (Player_State_KnuxGlideLeft / Right), before the game moves her by its velocity
static bool32 Hook_BatGlide(bool32 skipped)
{
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (skipped || !IsExtra(self) || !g_cur->more.host.batGlide || RSDK.GetEntitySlot(self) != SLOT_PLAYER1)
        return false;
    const HostData *h = &g_cur->more.host;
    bool32 gliding    = !self->onGround && Gliding(self);
    if (gliding && g_hm.glided) {
        self->velocity.x = (int32)((int64)self->velocity.x * h->glideSpeed / 1000);
        if (self->velocity.y >= 0) {
            int32 y = g_hm.glideVY > h->glideSink ? g_hm.glideVY - 0x2000 : g_hm.glideVY + h->glideGravity;
            self->velocity.y = Clamp(y, 0, self->velocity.y); // (never sinking faster than his)
        }
    }
    g_hm.glided  = gliding;
    g_hm.glideVY = self->velocity.y;
    return false;
}

// ------------------------------------------------------------------------------------------------ Treasure Sense
// The nearest hidden giant ring still to collect (px across + down)
static bool32 TreasureFind(EntityPlayer *p, Vector2 *at, int32 *dist)
{
    uint16 cls = RSDK.FindObject("SpecialRing");
    if (!cls)
        return false;
    bool32 found = false;
    Entity *e    = NULL;
    while (RSDK.GetAllEntities(cls, (void **)&e)) {
        if (!e || !*(bool32 *)((uint8 *)e + SPECIALRING_ENABLED))
            continue;
        int32 d = Abs((e->position.x - p->position.x) >> 16) + Abs((e->position.y - p->position.y) >> 16);
        if (!found || d < *dist) {
            found = true;
            *dist = d;
            *at   = e->position;
        }
    }
    return found;
}

static void TreasureSense(EntityPlayer *p, bool32 transformed)
{
    const HostData *h = &g_cur->more.host;
    Vector2 last      = g_hm.last;
    g_hm.last         = p->position;
    if (Abs(p->position.x - last.x) > (64 << 16) || Abs(p->position.y - last.y) > (64 << 16))
        g_hm.sense = g_hm.sense < 0 ? g_hm.sense : 0; // (a respawn, a warp: whatever was going on is over)
    if (g_hm.sense < 0)
        g_hm.sense++;
    int32 a      = p->animator.animationID;
    bool32 plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_LOOK_UP || a == ANI_WALK || (a >= ANI_JOG && a <= ANI_DASH);
    bool32 free  = p->onGround && plain && !Hurt(p) && (p->state == Player_State_Ground_ || (Player_State_LookUp_ && p->state == Player_State_LookUp_));
    if (g_hm.sense == 0 && free && YPressedP1(p, transformed)) {
        g_hm.sense = 1;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "treasure sense: listening");
    }
    if (g_hm.sense > 0 && g_hm.sense <= h->sensePause) { // the pause: held still, listening
        if (!free) {
            g_hm.sense = 0;
            return;
        }
        p->groundVel  = 0;
        p->velocity.x = 0;
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_LOOK_UP, &p->animator, false, 0);
        if (p->animator.frameCount > 0)
            p->animator.frameID = p->animator.frameCount > SENSE_HOLD_FRAME ? SENSE_HOLD_FRAME : p->animator.frameCount - 1;
        p->animator.timer = 0;
        if (++g_hm.sense > h->sensePause) {
            Vector2 at;
            int32 d = 0;
            if (!TreasureFind(p, &at, &d)) {
                PlayNamed(h->senseSound);
                g_hm.sense = -h->senseCooldown;
                RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "treasure sense: no signal (no giant ring left here)");
            }
            else {
                RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "treasure sense: the nearest giant ring is %d px away (%d, %d)", d, at.x >> 16, at.y >> 16);
            }
        }
    }
    else if (g_hm.sense > h->sensePause) {
        if (++g_hm.sense > h->sensePause + h->senseShow)
            g_hm.sense = -h->senseCooldown;
    }
}

static bool32 SceneShows(const char *name)
{
    uint16 cls = RSDK.FindObject(name);
    return cls && RSDK.GetEntityCount(cls, true) > 0;
}

// The marker (MODCB_ONDRAW, once per draw group): the ring at the treasure, or at the screen's edge toward it, lit or not
static void HostDraw(void *data)
{
    if ((int32)(size_t)data != SENSE_GROUP || !g_active || !g_cur || !g_cur->more.host.treasureSense || g_ringFrames == 0xFFFF || !ScreenInfo
        || g_hm.sense <= g_cur->more.host.sensePause)
        return;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p) || SceneShows("TitleCard") || SceneShows("ActClear"))
        return;
    Vector2 at;
    int32 d = 0;
    if (!TreasureFind(p, &at, &d))
        return;
    int32 half = Clamp(SENSE_BLINK_NEAR + (d > SENSE_NEAR ? d - SENSE_NEAR : 0) * (SENSE_BLINK_FAR - SENSE_BLINK_NEAR) / (SENSE_FAR - SENSE_NEAR),
                       SENSE_BLINK_NEAR, SENSE_BLINK_FAR);
    if (g_hm.sense % (2 * half) >= half)
        return; // (the blink's dark half)
    int32 sc = SceneInfo->currentScreenID;
    int32 w = ScreenInfo[sc].size.x, hgt = ScreenInfo[sc].size.y, left = ScreenInfo[sc].position.x, top = ScreenInfo[sc].position.y;
    int32 tx = (at.x >> 16) - left, ty = (at.y >> 16) - top;
    if (tx < SENSE_MARGIN || ty < SENSE_MARGIN || tx > w - SENSE_MARGIN || ty > hgt - SENSE_MARGIN) { // off screen: the edge
        int32 px = (p->position.x >> 16) - left, py = (p->position.y >> 16) - top;
        int32 dx = tx - px, dy = ty - py;
        int64 s = 256; // how far along the line (in 256ths) the edge is
        if (dx > 0 && (int64)(w - SENSE_MARGIN - px) * 256 / dx < s)
            s = (int64)(w - SENSE_MARGIN - px) * 256 / dx;
        if (dx < 0 && (int64)(SENSE_MARGIN - px) * 256 / dx < s)
            s = (int64)(SENSE_MARGIN - px) * 256 / dx;
        if (dy > 0 && (int64)(hgt - SENSE_MARGIN - py) * 256 / dy < s)
            s = (int64)(hgt - SENSE_MARGIN - py) * 256 / dy;
        if (dy < 0 && (int64)(SENSE_MARGIN - py) * 256 / dy < s)
            s = (int64)(SENSE_MARGIN - py) * 256 / dy;
        if (s < 0)
            s = 0;
        tx = Clamp((int32)(px + dx * s / 256), SENSE_MARGIN, w - SENSE_MARGIN);
        ty = Clamp((int32)(py + dy * s / 256), SENSE_MARGIN, hgt - SENSE_MARGIN);
    }
    Entity *self = SceneInfo->entity;
    if (!self)
        return;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction; // (DrawSprite draws with the entity's own)
    self->drawFX    = FX_NONE;
    self->inkEffect = INK_NONE;
    self->direction = FLIP_NONE;
    Animator ring;
    memset(&ring, 0, sizeof(ring));
    RSDK.SetSpriteAnimation(g_ringFrames, 0, &ring, true, 0);
    Vector2 pos = { tx << 16, ty << 16 };
    RSDK.DrawSprite(&ring, &pos, true);
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

// ------------------------------------------------------------------------------------------------ Jewel Thief
// After ItemBox_State_Break: the frame its contents reach the top it gives the powerup (ItemBox_GivePowerup) and moves on
// to IconFinish; a ring box (10 rings) rewarding player 1, a jewelThief extra: 10 more
static bool32 Hook_ItemBoxBreak(bool32 skipped)
{
    Entity *box = SceneInfo->entity;
    if (skipped || !g_active || !g_cur || !g_cur->more.host.jewelThief || !Player_GiveRings_ || !box)
        return false;
    void *state = *(void **)((uint8 *)box + ITEMBOX_STATE);
    if (state != (void *)ItemBox_State_IconFinish_ || *(int32 *)((uint8 *)box + ITEMBOX_TYPE) != 0)
        return false;
    EntityPlayer *p1 = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (*(EntityPlayer **)((uint8 *)box + ITEMBOX_STORED) != p1 || !IsExtra(p1))
        return false;
    Player_GiveRings_(p1, 10, false);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "jewel thief: a ring monitor: 10 more rings");
    return false;
}

// ------------------------------------------------------------------------------------------------ frame, link
// Player 1's frame (OnUpdate, the game running)
static void HostUpdate(EntityPlayer *p1, bool32 transformed)
{
    if (!g_active || !g_cur || !IsExtra(p1))
        return;
    const HostData *h = &g_cur->more.host;
    if (!Gliding(p1))
        g_hm.glided = false;
    if (h->aimDashY)
        Stinger(p1, transformed);
    if (g_cur->ab.screwKick && !g_cur->ab.kickOnJump)
        ScrewKickY(p1, transformed);
    if (h->treasureSense)
        TreasureSense(p1, transformed);
}

static void HostLateUpdate(void *data)
{
    (void)data;
    HostSuperFrame();
}

static void LinkHost(void)
{
    bool32 glide = false, jewel = false, sense = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        glide |= g_extras[i].more.host.batGlide != 0;
        jewel |= g_extras[i].more.host.jewelThief != 0;
        sense |= g_extras[i].more.host.treasureSense != 0;
    }
    Player_State_TailsFlight_   = Mod.GetPublicFunction(NULL, "Player_State_TailsFlight");
    Player_State_KnuxGlideLeft_  = Mod.GetPublicFunction(NULL, "Player_State_KnuxGlideLeft");
    Player_State_KnuxGlideRight_ = Mod.GetPublicFunction(NULL, "Player_State_KnuxGlideRight");
    if (!Player_State_LookUp_)
        Player_State_LookUp_ = Mod.GetPublicFunction(NULL, "Player_State_LookUp");
    if (!Player_State_Ground_)
        Player_State_Ground_ = Mod.GetPublicFunction(NULL, "Player_State_Ground");
    if (glide && Player_State_KnuxGlideLeft_ && Player_State_KnuxGlideRight_) {
        Mod.RegisterStateHook(Player_State_KnuxGlideLeft_, Hook_BatGlide, false);
        Mod.RegisterStateHook(Player_State_KnuxGlideRight_, Hook_BatGlide, false);
    }
    if (jewel) {
        Player_GiveRings_         = Mod.GetPublicFunction(NULL, "Player_GiveRings");
        ItemBox_State_Break_      = Mod.GetPublicFunction(NULL, "ItemBox_State_Break");
        ItemBox_State_IconFinish_ = Mod.GetPublicFunction(NULL, "ItemBox_State_IconFinish");
        if (Player_GiveRings_ && ItemBox_State_Break_ && ItemBox_State_IconFinish_)
            Mod.RegisterStateHook(ItemBox_State_Break_, Hook_ItemBoxBreak, false);
        else
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "jewel thief: the game's ItemBox / Player_GiveRings functions weren't found: off");
    }
    if (sense)
        Mod.AddModCallback(MODCB_ONDRAW, HostDraw);
    Mod.AddModCallback(MODCB_ONLATEUPDATE, HostLateUpdate); // (after ManiaHud.h's: LinkHud is earlier)
}

#endif // MANIA_HOST_H
