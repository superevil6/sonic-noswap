// NoSwapMania: Joe Musashi's Ninjutsu (tools/ninjutsu.py; its data: ManiaNinjutsuData.h), the S3&K DLL's
// (native/src/Ninjutsu.h: the same rules and numbers), on Mania's Player, for player 1:
//   - an item monitor broken (ItemBox_State_Break's first run, hooked as John's sub-weapon swap is: by anyone or
//     anything) stores one magic, at random among ninjaKinds (bit k: kind k), if none is held or being cast; 0 at each
//     stage load;
//   - the held one's icon at the top middle of the screen in the dark box (John's sub-weapon box, ManiaCross.h's look),
//     MODCB_ONDRAW after the HUD's group: the game's own monitor art, Global/ItemBox.bin "Powerups" (4 the lightning
//     shield, 3 the fire shield, 6 the sneakers, 10 Eggman);
//   - up + Y casts it (NinjaPress, first in OnUpdate: the press is taken off the controller for the rest of the frame,
//     so no shuriken goes with it), from his own free states (ManiaMelee.h Free; not hurt; not the press that made him
//     Super):
//       Ikazuchi  the lightning shield (Player_ApplyShield, as its monitor; Global/LightningShield.wav);
//       Kariu     a screen-wide hit (the melee's nuke stand-in: the screen's box, ninjaKariuHit frames) and its flash
//                 (FillScreen by ninjaKariuFlash per frame, in the melee flash's group);
//       Fushin    his jump strength x ninjaFushinJump / 1000 for ninjaFushin frames (the game's own value, whatever set it
//                 last: the water, Super), then back;
//       Mijin     Bomb's half-screen hit (a box ninjaMijinX / Y px round him) at once, then, as his Mijin frames end, a
//                 normal hit on him (ManiaMelee.h MeleeCost: the game's own Player_Hit);
//   - the pose (NinjaAfter, after every move): extra slot 1 (slot 42) for ninjaCast frames, Mijin's extra slot 6 (slot
//     48); still on the ground, hanging still in the air, nothing hurts him (the blink at 3); a hit or an object taking
//     him ends it (no cost).
// Included once, by NoSwapMania.c (after ManiaCross.h).
#ifndef MANIA_NINJUTSU_H
#define MANIA_NINJUTSU_H

#define NJ_IKAZUCHI (1)
#define NJ_KARIU    (2)
#define NJ_FUSHIN   (3)
#define NJ_MIJIN    (4)
#define NJ_POWERUPS (2) // Global/ItemBox.bin: Normal, Broken, Powerups...

static const int32 NJ_ICON_FRAME[5] = { 0, 4, 3, 6, 10 }; // the ItemBox types: lightning, fire, sneakers, Eggman

static struct {
    int32 kind;      // the magic held (0 none)
    int32 pose;      // the cast pose's frames left
    int32 poseKind;  // the magic being cast
    int32 fushin;    // Fushin's frames left
    int32 jumpWritten, jumpBase; // Fushin: the jump strength we wrote, and the game's under it
    int32 nuke;      // a blast's frames of hits left
    int32 nukeX, nukeY; // its box round him (0: the screen)
    int32 flash;     // Kariu's flash frame showing (-1: none)
} g_nj;

static bool32 g_njOn = false, g_njHooked = false, g_njFrameOK = false;
static int32 g_njAnimCast = -1, g_njAnimMijin = -1;
static uint16 g_njSfx = 0xFFFF, g_njCastSfx = 0xFFFF, g_njKariuSfx = 0xFFFF, g_njMijinSfx = 0xFFFF, g_njShieldSfx = 0xFFFF;
static uint8 g_njStruck[STRUCK_MAX / 8]; // what this blast has hit
static EngineSpriteFrame g_njFrame;     // the blast's stand-in box
static Animator g_njBox;
static void (*Player_ApplyShield_)(EntityPlayer *player);
static void *ItemBox_State_Break_Nj_ = NULL;

static const NinjaData *NjData(void) { return &g_cur->more.ninja; }
static void NjSfx(uint16 sfx)
{
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}
static const char *NjName(int32 k)
{
    static const char *const names[] = { "none", "Ikazuchi", "Kariu", "Fushin", "Mijin" };
    return k >= 0 && k <= 4 ? names[k] : "?";
}

// Stage load (NoSwapMania.c's, after the others): nothing held, nothing going on
static void NinjaStageLoad(void)
{
    memset(&g_nj, 0, sizeof(g_nj));
    g_nj.flash = -1;
    g_njOn     = false;
    if (!g_cur || !g_active || !g_cur->more.ninja.ninjutsu)
        return;
    const NinjaData *c = NjData();
    g_njAnimCast       = HasAnim(g_cur->animBase + 1);
    g_njAnimMijin      = HasAnim(g_cur->animBase + 6);
    g_njFrameOK        = CheckEngineFrames();
    g_njSfx            = SfxOf(c->ninjaSound);
    g_njCastSfx        = SfxOf(c->ninjaCastSound);
    g_njKariuSfx       = SfxOf(c->ninjaKariuSound);
    g_njMijinSfx       = SfxOf(c->ninjaMijinSound);
    g_njShieldSfx      = RSDK.GetSfx("Global/LightningShield.wav");
    g_njOn = g_njAnimCast >= 0 && g_njAnimMijin >= 0 && c->ninjaKinds != 0 && Player_State_Ground_ && Player_Hit_;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ninjutsu: %s, kinds %#x, anims %d %d, monitor hook %d, stand-in %s, shield %s",
                  g_njOn ? "on" : "OFF", c->ninjaKinds, g_njAnimCast, g_njAnimMijin, g_njHooked,
                  g_njFrameOK ? "checks out" : "DIFFERENT (no blast hits)", Player_ApplyShield_ ? "found" : "NOT found");
}

// ItemBox_State_Break, before it: its first run (contentsSpeed still as ItemBox_Break left it) is a monitor just broken
static bool32 Hook_NinjaItemBox(bool32 skipped)
{
    (void)skipped;
    Entity *box = SceneInfo->entity;
    if (!g_njOn || !box || g_nj.kind || g_nj.pose)
        return false;
    if (*(int32 *)((uint8 *)box + CR_ITEMBOX_CONTENTS_SPEED) != -0x30000)
        return false;
    int32 kinds[4], n = 0;
    for (int32 k = NJ_IKAZUCHI; k <= NJ_MIJIN; ++k)
        if (NjData()->ninjaKinds >> k & 1)
            kinds[n++] = k;
    if (!n)
        return false;
    int32 r = RSDK.Rand(0, n);
    g_nj.kind = kinds[r >= 0 && r < n ? r : 0];
    NjSfx(g_njSfx);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ninjutsu: the monitor at slot %d broke: %s stored", RSDK.GetEntitySlot(box), NjName(g_nj.kind));
    return false;
}

static void NinjaBlast(int32 hit, int32 x, int32 y)
{
    g_nj.nuke  = hit;
    g_nj.nukeX = x;
    g_nj.nukeY = y;
    memset(g_njStruck, 0, sizeof(g_njStruck));
    int32 rx = x > 0 ? x : (ScreenInfo ? ScreenInfo->center.x : 212) + 16;
    int32 ry = x > 0 ? y : (ScreenInfo ? ScreenInfo->center.y : 120) + 16;
    memset(&g_njFrame, 0, sizeof(g_njFrame));
    g_njFrame.hitboxCount = 1;
    for (int32 i = 0; i < 8; ++i) {
        g_njFrame.hitboxes[i].left   = (int16)-rx;
        g_njFrame.hitboxes[i].top    = (int16)-ry;
        g_njFrame.hitboxes[i].right  = (int16)rx;
        g_njFrame.hitboxes[i].bottom = (int16)ry;
    }
    memset(&g_njBox, 0, sizeof(g_njBox));
    g_njBox.frames      = (SpriteFrame *)&g_njFrame;
    g_njBox.frameCount  = 1;
    g_njBox.animationID = ANI_JUMP;
}

// First in OnUpdate: up + Y with a magic held casts it (the press then taken: nothing else sees it this frame)
static void NinjaPress(EntityPlayer *p, bool32 transformed)
{
    if (!g_njOn || !IsExtra(p) || !g_nj.kind || g_nj.pose || !p->up || !YPressedP1(p, transformed) || Hurt(p) || !Free(p))
        return;
    ControllerInfo[p->controllerID].keyY.press = false; // (the cast's press: no shuriken with it)
    const NinjaData *c = NjData();
    NjSfx(g_njCastSfx);
    switch (g_nj.kind) {
        case NJ_IKAZUCHI:
            if (Player_ApplyShield_) {
                p->shield = AMY_SHIELD_LIGHTNING; // (4: Mania's ShieldTypes, ManiaAmy.h)
                Entity *prevEntity    = SceneInfo->entity; // (as in his own update: MeleeCost's note)
                int32 prevSlot        = SceneInfo->entitySlot;
                SceneInfo->entity     = (Entity *)p;
                SceneInfo->entitySlot = RSDK.GetEntitySlot(p);
                Player_ApplyShield_(p);
                SceneInfo->entity     = prevEntity;
                SceneInfo->entitySlot = prevSlot;
                NjSfx(g_njShieldSfx);
            }
            break;
        case NJ_KARIU:
            NinjaBlast(c->ninjaKariuHit, 0, 0);
            g_nj.flash = c->ninjaKariuFlashCount > 0 ? 0 : -1;
            NjSfx(g_njKariuSfx);
            break;
        case NJ_FUSHIN:
            g_nj.fushin = c->ninjaFushin;
            break;
        case NJ_MIJIN:
            NinjaBlast(c->ninjaMijinHit, c->ninjaMijinX, c->ninjaMijinY);
            NjSfx(g_njMijinSfx);
            break;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ninjutsu: %s cast", NjName(g_nj.kind));
    g_nj.poseKind = g_nj.kind;
    g_nj.kind     = 0;
    g_nj.pose     = g_nj.poseKind == NJ_MIJIN ? c->ninjaMijin : c->ninjaCast;
    if (g_nj.pose < 1)
        g_nj.pose = 1;
}

// A hit class's update (HitUpdate): a blast stands in for it when it's in reach and not hit yet; true: its update has run
static bool32 NinjaStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    (void)kind;
    if (!g_njOn || g_nj.nuke <= 0 || !g_njFrameOK || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_
        || p->state == Player_State_Drown_)
        return false;
    int32 slot = RSDK.GetEntitySlot(self);
    if (slot < 0 || slot >= STRUCK_MAX || (g_njStruck[slot >> 3] >> (slot & 7) & 1))
        return false;
    Vector2 pos = p->position;
    bool32 in;
    if (g_nj.nukeX > 0) {
        in = Abs(self->position.x - p->position.x) <= (g_nj.nukeX << 16) && Abs(self->position.y - p->position.y) <= (g_nj.nukeY << 16);
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
    if (StandInAt(self, pos, &g_njBox, p->direction, p->collisionPlane, p)) {
        g_njStruck[slot >> 3] |= (uint8)(1 << (slot & 7));
        static int32 logs = 0;
        if (logs++ < 60)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ninjutsu: the blast hit class %d (slot %d)", self->classID, slot);
    }
    return true;
}

// Last in OnUpdate (after every move): the blast's and flash's count, the pose, Fushin's jump
static void NinjaAfter(EntityPlayer *p)
{
    if (!g_njOn)
        return;
    const NinjaData *c = NjData();
    if (g_nj.nuke > 0)
        g_nj.nuke--;
    if (g_nj.flash >= 0 && ++g_nj.flash >= c->ninjaKariuFlashCount)
        g_nj.flash = -1;
    if (!IsExtra(p))
        return;
    if (g_nj.fushin > 0) {
        if (p->jumpStrength != g_nj.jumpWritten) { // (the first frame, or the game set a new one)
            g_nj.jumpBase    = p->jumpStrength;
            g_nj.jumpWritten = (int32)((int64)p->jumpStrength * c->ninjaFushinJump / 1000);
            p->jumpStrength  = g_nj.jumpWritten;
        }
        if (--g_nj.fushin == 0) { // over: his own back
            if (p->jumpStrength == g_nj.jumpWritten)
                p->jumpStrength = g_nj.jumpBase;
            g_nj.jumpWritten = 0;
        }
    }
    if (g_nj.pose <= 0)
        return;
    if (Hurt(p) || !Free(p)) { // a hit, his death or an object: over (no cost)
        g_nj.pose     = 0;
        g_nj.poseKind = 0;
        return;
    }
    bool32 mijin  = g_nj.poseKind == NJ_MIJIN;
    int32 total   = mijin ? c->ninjaMijin : c->ninjaCast, ticks = mijin ? c->ninjaMijinTicks : c->ninjaCastTicks;
    if (total < 1)
        total = 1;
    int32 frames  = total / ticks > 0 ? total / ticks : 1, elapsed = total - g_nj.pose;
    Show(p, mijin ? g_njAnimMijin : g_njAnimCast, false, elapsed == 0);
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
    if (--g_nj.pose == 0) {
        RSDK.SetSpriteAnimation(p->aniFrames, p->onGround ? ANI_IDLE : ANI_JUMP, &p->animator, true, 0);
        if (mijin) // Mijin's cost: a normal hit (Bomb's Self-Destruct)
            MeleeCost(p);
        g_nj.poseKind = 0;
    }
}

// MODCB_ONDRAW, per draw group: Kariu's flash (the melee flash's group), the held magic's icon (after the HUD's group)
static void NinjaDraw(void *data)
{
    int32 group = (int32)(size_t)data;
    if (!g_active || !g_cur || !g_njOn)
        return;
    if (group == FLASH_GROUP && g_nj.flash >= 0 && g_nj.flash < NjData()->ninjaKariuFlashCount) {
        int32 dark = NjData()->ninjaKariuFlash[g_nj.flash];
        if (dark > 0)
            RSDK.FillScreen(0x000000, dark, dark, dark);
        return;
    }
    if (group != CR_HUD_GROUP || !g_nj.kind || g_nj.pose || !ScreenInfo || !SceneInfo->entity)
        return;
    if (CrShowing("TitleCard") || CrShowing("ActClear") || CrShowing("PauseMenu"))
        return;
    EntityPlayer *p1 = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p1))
        return;
    uint16 frames = RSDK.LoadSpriteAnimation("Global/ItemBox.bin", SCOPE_STAGE);
    SpriteFrame *f = frames != 0xFFFF ? RSDK.GetFrame(frames, NJ_POWERUPS, NJ_ICON_FRAME[g_nj.kind]) : NULL;
    if (!f || !f->width || !f->height)
        return;
    int32 cx = ScreenInfo->center.x, bw = f->width + 2 * CR_ICON_PAD_X, bh = f->height + 2 * CR_ICON_PAD_Y;
    Entity *self = SceneInfo->entity;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;
    self->drawFX    = FX_NONE;
    self->inkEffect = INK_NONE;
    self->direction = FLIP_NONE;
    RSDK.DrawRect(cx - bw / 2, CR_ICON_TOP, bw, bh, 0x000000, CR_ICON_ALPHA, INK_ALPHA, true);
    Animator icon;
    memset(&icon, 0, sizeof(icon));
    RSDK.SetSpriteAnimation(frames, NJ_POWERUPS, &icon, true, (uint8)NJ_ICON_FRAME[g_nj.kind]);
    Vector2 pos = { cx << 16, (CR_ICON_TOP + bh / 2) << 16 };
    RSDK.DrawSprite(&icon, &pos, true);
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

// Link (after LinkCross): the shield function, the monitor hook and the draw, when an installed extra has the move
static void LinkNinja(void)
{
    bool32 any = false;
    for (int32 i = 0; i < g_extraCount; ++i) any |= g_extras[i].more.ninja.ninjutsu != 0;
    if (!any)
        return;
    Player_ApplyShield_ = Mod.GetPublicFunction(NULL, "Player_ApplyShield");
    ItemBox_State_Break_Nj_ = Mod.GetPublicFunction(NULL, "ItemBox_State_Break");
    if (ItemBox_State_Break_Nj_) {
        Mod.RegisterStateHook(ItemBox_State_Break_Nj_, Hook_NinjaItemBox, true);
        g_njHooked = true;
    }
    else {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "ninjutsu: ItemBox_State_Break wasn't found: no charges");
    }
    Mod.AddModCallback(MODCB_ONDRAW, NinjaDraw);
}

#endif // MANIA_NINJUTSU_H
