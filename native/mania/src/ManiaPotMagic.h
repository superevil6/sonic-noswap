// NoSwapMania: Gilius Thunderhead's pot magic (tools/pot_magic.py; its data: ManiaPotMagicData.h), the S3&K DLL's
// (native/src/PotMagic.h: the same rules and numbers), on Mania's Player, for player 1:
//   - an item monitor broken (ItemBox_State_Break's first run, hooked as Joe's Ninjutsu is: by anyone or anything) adds
//     a pot, up to potsMax; 0 at each stage load;
//   - the pots' pictures (his extra 6: a crop of his portrait) in the dark box at the top middle of the screen, one
//     each, MODCB_ONDRAW after the HUD's group (Joe's icon's place);
//   - up + Y casts the Earthquake (PotsPress, first in OnUpdate: the press is taken off the controller for the rest of
//     the frame, so no chop goes with it), from his own free states (ManiaMelee.h Free; not hurt; not the press that
//     made him Super). Every pot is spent; the pots spent are its level (index level - 1 of the potsLevel* lists):
//       its hit    the melee nuke's stand-in (StandInAt) on everything in the box round him (potsLevelX / Y px; 0: the
//                  screen), in potsLevelPulses waves of potsHit frames, potsGap apart, the first potsFirst frames after
//                  the cast; each target once per wave (a boss: a hit per wave);
//       its shake  the game's own Camera_ShakeScreen, every 8 frames for potsShake frames;
//       its flash  FillScreen by potsFlash per frame (the melee flash's group: Joe's Kariu's);
//       boulders   potsLevelRocks per wave (tools/pot_magic.py ROCK_*: the same numbers) fall from above the screen,
//                  land on the floor under them (the engine's ObjectTileCollision on a copy of his entity) and burst
//                  (extra 4 after a big one, extra 5 after a small one), drawn after his draw group from his own frames
//                  (extra 3: the boulders);
//   - the pose (PotsAfter, after every move): extra slot 1 (slot 42) for potsCast frames, potsCastTicks each; still on the
//     ground, hanging still in the air, nothing hurts him (the blink at 3); a hit or an object ends the pose, not the
//     quake.
// Included once, by NoSwapMania.c (after ManiaVoltteccer.h).
#ifndef MANIA_POT_MAGIC_H
#define MANIA_POT_MAGIC_H

#define PM_ROCK_TOP      (40)
#define PM_ROCK_VY0      (0x30000)
#define PM_ROCK_G        (0x6000)
#define PM_ROCK_VMAX     (0xC0000)
#define PM_ROCK_STAGGER  (3)
#define PM_ROCK_ABOVE    (48)
#define PM_ROCK_BELOW    (160)
#define PM_ROCK_SCREEN   (184)
#define PM_BURST_FRAMES  (5)
#define PM_BURST_TICKS   (4)
#define PM_FEET          (20) // a burst frame's bottom FEET px under its y (feet-anchored frames)
#define PM_ICON_GAP      (2)
#define PM_ROCKS_MAX     (48)
#define PM_ANI_ROCKS     (3) // the extra's animations (animBase + k: slots 45-48)
#define PM_ANI_BURST_BIG (4)
#define PM_ANI_BURST_SMALL (5)
#define PM_ANI_POT       (6)

static const int32 PM_ROCK_R[2] = { 31, 16 }; // half heights: big, small

typedef struct {
    bool32 on;
    int32 x, y, vy; // 16.16
    int32 age, delay, kind, phase, feet; // phase 0 waiting, 1 falling, 2 bursting
    uint8 dir;
} PmRock;

static struct {
    int32 count; // the pots
    int32 pose;  // the cast pose's frames left
    int32 age;   // the quake's age (-1: none)
    int32 level; // its level (pots spent)
    int32 feet;  // his feet at the cast (16.16)
    int32 wave;  // the wave whose pulse is running (its targets struck once: g_pmStruck)
    int32 flash; // the flash's frame showing (-1: none)
} g_pm;

static PmRock g_pmRocks[PM_ROCKS_MAX];
static bool32 g_pmOn = false, g_pmHooked = false, g_pmFrameOK = false;
static int32 g_pmAnimCast = -1;
static uint16 g_pmSfx = 0xFFFF, g_pmCastSfx = 0xFFFF, g_pmQuakeSfx = 0xFFFF;
static uint8 g_pmStruck[STRUCK_MAX / 8]; // what this wave has hit
static EngineSpriteFrame g_pmFrame;      // the quake's stand-in box
static Animator g_pmBox;
static int32 g_pmPulse = 0;              // frames of the current pulse left (its hits)
static void (*Camera_ShakeScreen_)(int32 screen, int32 shakeX, int32 shakeY);
static void *ItemBox_State_Break_Pm_ = NULL;

static const PotsData *PmData(void) { return &g_cur->more.pots; }
static void PmSfx(uint16 sfx)
{
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}

// Stage load (NoSwapMania.c's, after the others): no pots, nothing going on
static void PotsStageLoad(void)
{
    memset(&g_pm, 0, sizeof(g_pm));
    memset(g_pmRocks, 0, sizeof(g_pmRocks));
    g_pm.age   = -1;
    g_pm.flash = -1;
    g_pmPulse  = 0;
    g_pmOn     = false;
    if (!g_cur || !g_active || !g_cur->more.pots.potMagic)
        return;
    const PotsData *c = PmData();
    g_pmAnimCast      = HasAnim(g_cur->animBase + 1);
    g_pmFrameOK       = CheckEngineFrames();
    g_pmSfx           = SfxOf(c->potsSound);
    g_pmCastSfx       = SfxOf(c->potsCastSound);
    g_pmQuakeSfx      = SfxOf(c->potsQuakeSound);
    g_pmOn = g_pmAnimCast >= 0 && c->potsMax > 0 && Player_State_Ground_;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "pot magic: %s, max %d, anims %d %d %d %d, monitor hook %d, stand-in %s, shake %s",
                  g_pmOn ? "on" : "OFF", c->potsMax, g_pmAnimCast, HasAnim(g_cur->animBase + PM_ANI_ROCKS),
                  HasAnim(g_cur->animBase + PM_ANI_BURST_BIG), HasAnim(g_cur->animBase + PM_ANI_POT), g_pmHooked,
                  g_pmFrameOK ? "checks out" : "DIFFERENT (no quake hits)", Camera_ShakeScreen_ ? "found" : "NOT found");
}

// ItemBox_State_Break, before it: its first run (contentsSpeed still as ItemBox_Break left it) is a monitor just broken
static bool32 Hook_PotsItemBox(bool32 skipped)
{
    (void)skipped;
    Entity *box = SceneInfo->entity;
    if (!g_pmOn || !box || g_pm.count >= PmData()->potsMax)
        return false;
    if (*(int32 *)((uint8 *)box + CR_ITEMBOX_CONTENTS_SPEED) != -0x30000)
        return false;
    g_pm.count++;
    PmSfx(g_pmSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "pot magic: the monitor at slot %d broke: %d pot(s)", RSDK.GetEntitySlot(box), g_pm.count);
    return false;
}

// The level's box round him (x / y px; 0: the screen's) as the stand-in's frame
static void PotsBox(int32 x, int32 y)
{
    int32 rx = x > 0 ? x : (ScreenInfo ? ScreenInfo->center.x : 212) + 16;
    int32 ry = x > 0 ? y : (ScreenInfo ? ScreenInfo->center.y : 120) + 16;
    memset(&g_pmFrame, 0, sizeof(g_pmFrame));
    g_pmFrame.hitboxCount = 1;
    for (int32 i = 0; i < 8; ++i) {
        g_pmFrame.hitboxes[i].left   = (int16)-rx;
        g_pmFrame.hitboxes[i].top    = (int16)-ry;
        g_pmFrame.hitboxes[i].right  = (int16)rx;
        g_pmFrame.hitboxes[i].bottom = (int16)ry;
    }
    memset(&g_pmBox, 0, sizeof(g_pmBox));
    g_pmBox.frames      = (SpriteFrame *)&g_pmFrame;
    g_pmBox.frameCount  = 1;
    g_pmBox.animationID = ANI_JUMP;
}

// Wave w's boulder k of n, over -span .. span px from the middle (pot_magic.rock_offsets: the same arithmetic)
static int32 PmRockX(int32 span, int32 n, int32 w, int32 j)
{
    double step = 2.0 * span / n;
    double v    = -span + step * (j + 0.5) + (w % 2 ? step / 2 : 0);
    int32 x     = (int32)(v < 0 ? -(int32)(-v + 0.5) : (int32)(v + 0.5)); // (half away from zero, as C's lround and pot_magic.rock_offsets)
    return x <= span ? x : x - 2 * span;
}

static void PotsSpawn(EntityPlayer *p, int32 lv, int32 w)
{
    const PotsData *c = PmData();
    int32 n = c->potsLevelRocks[lv];
    if (n <= 0 || !ScreenInfo)
        return;
    bool32 whole = c->potsLevelX[lv] == 0;
    int32 cx     = whole ? ScreenInfo->position.x + ScreenInfo->center.x : (p->position.x >> 16);
    int32 span   = whole ? PM_ROCK_SCREEN : c->potsLevelX[lv];
    for (int32 k = 0; k < n; ++k) {
        PmRock *r = NULL;
        for (int32 s = 0; s < PM_ROCKS_MAX; ++s)
            if (!g_pmRocks[s].on) {
                r = &g_pmRocks[s];
                break;
            }
        if (!r)
            return;
        int32 me = PmRockX(span, n, w, k), order = 0;
        for (int32 j = 0; j < n; ++j) { // (the nearest to the middle first, then by x)
            int32 o = PmRockX(span, n, w, j);
            if (Abs(o) < Abs(me) || (Abs(o) == Abs(me) && o < me))
                order++;
        }
        memset(r, 0, sizeof(*r));
        r->on    = true;
        r->x     = (cx + me) << 16;
        r->y     = (ScreenInfo->position.y - PM_ROCK_TOP) << 16;
        r->vy    = PM_ROCK_VY0;
        r->delay = PM_ROCK_STAGGER * order;
        r->kind  = k % 2;
        r->feet  = g_pm.feet;
        r->dir   = (uint8)(k % 2);
    }
}

// First in OnUpdate: up + Y with pots casts the Earthquake (the press then taken: nothing else sees it this frame)
static void PotsPress(EntityPlayer *p, bool32 transformed)
{
    if (!g_pmOn || !IsExtra(p) || g_pm.count <= 0 || g_pm.pose || !p->up || !YPressedP1(p, transformed) || Hurt(p) || !Free(p))
        return;
    ControllerInfo[p->controllerID].keyY.press = false; // (the cast's press: no chop with it)
    const PotsData *c = PmData();
    PmSfx(g_pmCastSfx);
    g_pm.level = g_pm.count < c->potsMax ? g_pm.count : c->potsMax;
    g_pm.count = 0;
    g_pm.age   = 0;
    g_pm.wave  = -1;
    g_pm.feet  = p->position.y + (PM_FEET << 16);
    g_pm.flash = c->potsFlashCount > 0 ? 0 : -1;
    g_pm.pose  = c->potsCast > 0 ? c->potsCast : 1;
    PmSfx(g_pmQuakeSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "pot magic: the Earthquake, level %d", g_pm.level);
}

// A hit class's update (HitUpdate): the quake stands in for it when it's in reach and not hit in this wave; true: its
// update has run
static bool32 PotsStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    (void)kind;
    if (!g_pmOn || g_pmPulse <= 0 || !g_pmFrameOK || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_
        || p->state == Player_State_Drown_ || g_pm.level < 1)
        return false;
    int32 slot = RSDK.GetEntitySlot(self);
    if (slot < 0 || slot >= STRUCK_MAX || (g_pmStruck[slot >> 3] >> (slot & 7) & 1))
        return false;
    const PotsData *c = PmData();
    int32 x = c->potsLevelX[g_pm.level - 1], y = c->potsLevelY[g_pm.level - 1];
    Vector2 pos = p->position;
    bool32 in;
    if (x > 0) {
        in = Abs(self->position.x - p->position.x) <= (x << 16) && Abs(self->position.y - p->position.y) <= (y << 16);
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
    PotsBox(x, y);
    if (StandInAt(self, pos, &g_pmBox, p->direction, p->collisionPlane, p)) {
        g_pmStruck[slot >> 3] |= (uint8)(1 << (slot & 7));
        static int32 logs = 0;
        if (logs++ < 60)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "pot magic: the quake hit class %d (slot %d)", self->classID, slot);
    }
    return true;
}

static int32 PotsEndAge(const PotsData *c)
{
    int32 p = 1;
    for (int32 k = 0; k < c->potsMax && k < POTS_LEVELS; ++k)
        if (c->potsLevelPulses[k] > p)
            p = c->potsLevelPulses[k];
    int32 end = c->potsFirst + (p - 1) * c->potsGap + c->potsHit;
    if (c->potsFlashCount > end)
        end = c->potsFlashCount;
    if (c->potsShake > end)
        end = c->potsShake;
    return end + 1;
}

static void PotsRocks(EntityPlayer *p)
{
    for (int32 s = 0; s < PM_ROCKS_MAX; ++s) {
        PmRock *r = &g_pmRocks[s];
        if (!r->on)
            continue;
        if (++r->age > 400) { // (a safety net)
            r->on = false;
            continue;
        }
        if (r->phase == 0) {
            if (r->age >= r->delay)
                r->phase = 1;
            continue;
        }
        if (r->phase == 1) {
            r->y += r->vy;
            if (r->vy < PM_ROCK_VMAX)
                r->vy += PM_ROCK_G;
            if (r->y >= r->feet - (PM_ROCK_ABOVE << 16)) { // (low enough: the floor counts)
                Entity probe;
                memcpy(&probe, p, sizeof(probe)); // (a copy of his entity: the engine's collision, nothing of his moved)
                probe.position.x = r->x;
                probe.position.y = r->y;
                int32 rad        = PM_ROCK_R[r->kind];
                if (RSDK.ObjectTileCollision(&probe, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, 0, rad << 16, true)) {
                    r->y     = probe.position.y + ((rad - PM_FEET) << 16);
                    r->phase = 2;
                    r->age   = 0;
                }
            }
            if (r->phase == 1 && r->y > r->feet + (PM_ROCK_BELOW << 16))
                r->on = false;
            continue;
        }
        if (r->age / PM_BURST_TICKS >= PM_BURST_FRAMES)
            r->on = false;
    }
}

// Last in OnUpdate (after every move): the quake's waves, shake and flash, the boulders, the pose
static void PotsAfter(EntityPlayer *p)
{
    if (!g_pmOn)
        return;
    const PotsData *c = PmData();
    if (g_pmPulse > 0)
        g_pmPulse--;
    if (g_pm.flash >= 0 && ++g_pm.flash >= c->potsFlashCount)
        g_pm.flash = -1;
    if (g_pm.age >= 0) {
        g_pm.age++;
        int32 lv = g_pm.level - 1, waves = c->potsLevelPulses[lv];
        if (waves < 1)
            waves = 1;
        for (int32 w = 0; w < waves && w < 4; ++w) {
            int32 s = c->potsFirst + w * c->potsGap;
            if (g_pm.age == s) { // a wave's pulse: its hits (each target once)
                g_pm.wave = w;
                g_pmPulse = c->potsHit;
                memset(g_pmStruck, 0, sizeof(g_pmStruck));
            }
            if (g_pm.age == 1 + w * c->potsGap)
                PotsSpawn(p, lv, w);
        }
        if (g_pm.age <= c->potsShake && (g_pm.age & 7) == 1 && Camera_ShakeScreen_)
            Camera_ShakeScreen_(0, 0, 4);
        if (g_pm.age > PotsEndAge(c))
            g_pm.age = -1;
    }
    PotsRocks(p);
    if (!IsExtra(p) || g_pm.pose <= 0)
        return;
    if (Hurt(p) || !Free(p)) { // a hit, his death or an object: the pose is over (the quake goes on)
        g_pm.pose = 0;
        return;
    }
    int32 total = c->potsCast > 0 ? c->potsCast : 1, ticks = c->potsCastTicks;
    int32 frames = total / ticks > 0 ? total / ticks : 1, elapsed = total - g_pm.pose;
    Show(p, g_pmAnimCast, false, elapsed == 0);
    int32 frame         = elapsed / ticks;
    p->animator.frameID = frame < frames ? frame : frames - 1; // (the timer picks the frame)
    if (p->animator.frameID >= p->animator.frameCount && p->animator.frameCount > 0)
        p->animator.frameID = p->animator.frameCount - 1;
    p->animator.timer = 0;
    if (p->blinkTimer < 3) // nothing hurts him meanwhile (no flicker)
        p->blinkTimer = 3;
    if (p->onGround) {
        p->groundVel  = 0;
        p->velocity.x = 0;
    }
    else { // hanging still (the melee's hang)
        p->velocity.x = 0;
        p->velocity.y = 0;
    }
    if (--g_pm.pose == 0)
        RSDK.SetSpriteAnimation(p->aniFrames, p->onGround ? ANI_IDLE : ANI_JUMP, &p->animator, true, 0);
}

// Draw with the current entity's draw settings cleared (DrawSprite uses them), then put back
static void PmDrawPlain(Animator *a, Vector2 *pos, uint8 dir, bool32 screen)
{
    Entity *self = SceneInfo->entity;
    if (!self) {
        RSDK.DrawSprite(a, pos, screen);
        return;
    }
    uint8 fx = self->drawFX, ink = self->inkEffect, d = self->direction;
    self->drawFX    = FX_FLIP;
    self->inkEffect = INK_NONE;
    self->direction = dir;
    RSDK.DrawSprite(a, pos, screen);
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->direction = d;
}

// MODCB_ONDRAW, per draw group: the boulders (after his group), the flash (the melee flash's group), the pots' pictures
// (after the HUD's group)
static void PotsDraw(void *data)
{
    int32 group = (int32)(size_t)data;
    if (!g_active || !g_cur || !g_pmOn || !SceneInfo->entity)
        return;
    EntityPlayer *p1 = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p1))
        return;
    if (group == p1->drawGroup) {
        for (int32 s = 0; s < PM_ROCKS_MAX; ++s) {
            PmRock *r = &g_pmRocks[s];
            if (!r->on || r->phase == 0)
                continue;
            Animator a;
            memset(&a, 0, sizeof(a));
            if (r->phase == 1)
                RSDK.SetSpriteAnimation(g_extraFrames, g_cur->animBase + PM_ANI_ROCKS, &a, true, r->kind);
            else
                RSDK.SetSpriteAnimation(g_extraFrames, g_cur->animBase + (r->kind ? PM_ANI_BURST_SMALL : PM_ANI_BURST_BIG), &a, true,
                                        r->age / PM_BURST_TICKS < PM_BURST_FRAMES ? r->age / PM_BURST_TICKS : PM_BURST_FRAMES - 1);
            if (!a.frames || !a.frameCount)
                continue;
            Vector2 pos = { r->x, r->y };
            PmDrawPlain(&a, &pos, r->dir, false);
        }
    }
    if (group == FLASH_GROUP && g_pm.flash >= 0 && g_pm.flash < PmData()->potsFlashCount) {
        int32 dark = PmData()->potsFlash[g_pm.flash];
        if (dark > 0)
            RSDK.FillScreen(0x000000, dark, dark, dark);
    }
    if (group != CR_HUD_GROUP || g_pm.count <= 0 || !ScreenInfo)
        return;
    if (CrShowing("TitleCard") || CrShowing("ActClear") || CrShowing("PauseMenu"))
        return;
    SpriteFrame *f = RSDK.GetFrame(g_extraFrames, g_cur->animBase + PM_ANI_POT, 0);
    if (!f || !f->width || !f->height)
        return;
    int32 w = f->width, n = g_pm.count;
    int32 iw = n * (w + PM_ICON_GAP) - PM_ICON_GAP, bw = iw + 2 * CR_ICON_PAD_X, bh = f->height + 2 * CR_ICON_PAD_Y;
    int32 cx = ScreenInfo->center.x;
    Entity *self = SceneInfo->entity;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;
    self->drawFX    = FX_NONE;
    self->inkEffect = INK_NONE;
    self->direction = FLIP_NONE;
    RSDK.DrawRect(cx - bw / 2, CR_ICON_TOP, bw, bh, 0x000000, CR_ICON_ALPHA, INK_ALPHA, true);
    Animator icon;
    memset(&icon, 0, sizeof(icon));
    RSDK.SetSpriteAnimation(g_extraFrames, g_cur->animBase + PM_ANI_POT, &icon, true, 0);
    for (int32 k = 0, x = cx - iw / 2 + w / 2; k < n; ++k, x += w + PM_ICON_GAP) {
        Vector2 pos = { x << 16, (CR_ICON_TOP + bh / 2) << 16 };
        RSDK.DrawSprite(&icon, &pos, true);
    }
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

// Link (after LinkNinja): the shake, the monitor hook and the draw, when an installed extra has the move
static void LinkPots(void)
{
    bool32 any = false;
    for (int32 i = 0; i < g_extraCount; ++i) any |= g_extras[i].more.pots.potMagic != 0;
    if (!any)
        return;
    Camera_ShakeScreen_     = Mod.GetPublicFunction(NULL, "Camera_ShakeScreen");
    ItemBox_State_Break_Pm_ = Mod.GetPublicFunction(NULL, "ItemBox_State_Break");
    if (ItemBox_State_Break_Pm_) {
        Mod.RegisterStateHook(ItemBox_State_Break_Pm_, Hook_PotsItemBox, true);
        g_pmHooked = true;
    }
    else {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "pot magic: ItemBox_State_Break wasn't found: no pots");
    }
    Mod.AddModCallback(MODCB_ONDRAW, PotsDraw);
}

#endif // MANIA_POT_MAGIC_H
