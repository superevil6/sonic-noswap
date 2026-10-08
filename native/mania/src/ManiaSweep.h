// NoSwapMania: the places where Mania picks a character's sprite by characterID that ManiaHud.h didn't cover (included
// by NoSwapMania.c after ManiaHud.h, whose helpers it uses; LinkSweep after LinkHud). Only while an extra plays; the
// game's own drawing, timing and states throughout, only the frames shown swapped (for that draw), as the HUD's are.
//   1. Press Garden's ice (Ice): a frozen player is drawn inside the block from Ice.bin's "<Character> Idle / Left /
//      Right / Shake" (Ice_FreezePlayer, by characterID: the host's, so Sonic). For an extra the block's contents are
//      its own Hurt frame (arms out, the frozen pose) from its Player.bin while the block draws; the block, its glints
//      and the struggle's shake offset stay the game's.
//   2. The 1-up monitor (ItemBox, and an Ice block holding one): ItemBox.bin "Powerups" frame 7/8/9 (Sonic / Tails /
//      Knuckles' head, by player 1's characterID) shows the extra's life icon (Hud.bin "Item Icon", centred like the
//      game's), in its save colours for that draw.
//   3. The UFO results (SpecialClear): the package's Results.bin (Special/Results.bin with the extra's name in its
//      host's messages: tools/build_mania_hud.py build_results) in place of the game's, so "<NAME> GOT A CHAOS
//      EMERALD" (and the all-emeralds / Super lines) read its name; the CONTINUE line's figure is its continue icon
//      (Hud.bin, its life icon if it has none), in its save colours, drawn first so the screen's fade covers it.
//   4. Studiopolis' TV van (TVVan, "exit TV"): the package's TVVan.bin, whose host ball is the extra's spin ball.
// Offsets: the decompilation's own structs (Plus build), compiled from SonicMania/Objects the way check_layout.sh does
// (EntityIce.stateDraw 104, .contentsAnimator 160, .altContentsAnimator 192, .playerPtr 256; ObjectItemBox.aniFrames
// 24, EntityItemBox.contentsAnimator 192; ObjectSpecialClear.aniFrames 4, EntitySpecialClear.continueIconVisible 120,
// .hasContinues 124, .continuePos 204, .continueAnimator 432; ObjectTVVan.aniFrames 4).
#ifndef MANIA_SWEEP_H
#define MANIA_SWEEP_H

#include <stddef.h>

#define SWEEP_ICE_STATEDRAW        (104)
#define SWEEP_ICE_CONTENTS         (160)
#define SWEEP_ICE_ALTCONTENTS      (192)
#define SWEEP_ICE_PLAYERPTR        (256)
#define SWEEP_ITEMBOX_ANIFRAMES    (24)
#define SWEEP_ITEMBOX_CONTENTS     (192)
#define SWEEP_ITEMBOX_POWERUPS     (2) // ItemBox.bin "Powerups"
#define SWEEP_ITEMBOX_1UP_SONIC    (7) // ITEMBOX_1UP_SONIC (Tails 8, Knuckles 9: ManiaHost.h's host index added)
#define SWEEP_SC_ANIFRAMES         (4)
#define SWEEP_SC_CONTINUE_VISIBLE  (120)
#define SWEEP_SC_HAS_CONTINUES     (124)
#define SWEEP_SC_CONTINUE_POS      (204)
#define SWEEP_SC_CONTINUE_ANIMATOR (432)
#define SWEEP_TVVAN_ANIFRAMES      (4)
_Static_assert(offsetof(Animator, frames) == 0 && offsetof(Animator, frameID) == 8 && sizeof(Animator) == 32, "Animator");

static void *g_iceObj         = NULL; // (the scene's objects, or NULL: Mod.RegisterObjectHook)
static void *g_itemBoxObj     = NULL;
static void *g_specialClearObj = NULL;
static void *g_tvVanObj       = NULL;
static void (*Ice_Draw_PlayerBlock_)(void) = NULL;
static void (*Ice_Draw_IceBlock_)(void)    = NULL;
static int32 g_itemIconAnim = -1;    // Hud.bin's "Item Icon" (-1: none this scene)
static bool32 g_resultsOK   = false; // SpecialClear has the package's Results.bin this scene
static SpriteFrame g_sweepBlank[32]; // (all 0 wide: DrawSprite draws nothing)

#define SWEEP_FIELD(type, entity, offset) ((type *)((uint8 *)(entity) + (offset)))

static void SweepSuperDraw(void *data)
{
    (void)data;
    Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

// The 1-up head of the extra's host on ItemBox.bin's Powerups (the monitor, or an ice block's)
static bool32 SweepIsOneUp(const Animator *a)
{
    if (g_itemIconAnim < 0 || !g_itemBoxObj || g_hudExtra < 0 || globals->gameMode == MODE_COMPETITION || globals->gameMode == MODE_ENCORE
        || globals->gameMode == MODE_TIMEATTACK)
        return false;
    uint16 items = *SWEEP_FIELD(uint16, g_itemBoxObj, SWEEP_ITEMBOX_ANIFRAMES);
    return a->frames && a->frames == RSDK.GetFrame(items, SWEEP_ITEMBOX_POWERUPS, 0)
           && a->frameID == SWEEP_ITEMBOX_1UP_SONIC + HostIndex(&g_extras[g_hudExtra]);
}

// Super's draw with `a` showing the extra's 1-up icon (the same frame number: Item Icon has as many), in its save colours
static void SweepDrawOneUp(Animator *a)
{
    SpriteFrame *frames = a->frames;
    a->frames           = RSDK.GetFrame(g_hudFrames, g_itemIconAnim, 0);
    WithSaveColours(&g_extras[g_hudExtra], SweepSuperDraw, NULL);
    a->frames = frames;
}

// ------------------------------------------------------------------------------------------------ 1. ice, 2. 1-ups
static void SweepIceDraw(void)
{
    Entity *self    = SceneInfo->entity;
    void *stateDraw = *SWEEP_FIELD(void *, self, SWEEP_ICE_STATEDRAW);
    if (stateDraw && stateDraw == (void *)Ice_Draw_PlayerBlock_) {
        EntityPlayer *p = *SWEEP_FIELD(EntityPlayer *, self, SWEEP_ICE_PLAYERPTR);
        SpriteFrame *hurt = p && IsExtra(p) && g_extraFrames < NS_SPRFILE_COUNT ? RSDK.GetFrame(g_extraFrames, ANI_HURT, 0) : NULL;
        if (hurt) {
            Animator *c         = SWEEP_FIELD(Animator, self, SWEEP_ICE_CONTENTS);
            SpriteFrame *frames = c->frames;
            int32 frameID       = c->frameID;
            c->frames           = hurt;
            c->frameID          = 0;
            Mod.Super(self->classID, SUPER_DRAW, NULL);
            c->frames  = frames;
            c->frameID = frameID;
            return;
        }
    }
    else if (stateDraw && stateDraw == (void *)Ice_Draw_IceBlock_) {
        Animator *alt = SWEEP_FIELD(Animator, self, SWEEP_ICE_ALTCONTENTS);
        if (SweepIsOneUp(alt)) {
            SweepDrawOneUp(alt);
            return;
        }
    }
    Mod.Super(self->classID, SUPER_DRAW, NULL);
}

static void SweepItemBoxDraw(void)
{
    Entity *self = SceneInfo->entity;
    Animator *c  = SWEEP_FIELD(Animator, self, SWEEP_ITEMBOX_CONTENTS);
    if (SweepIsOneUp(c))
        SweepDrawOneUp(c);
    else
        Mod.Super(self->classID, SUPER_DRAW, NULL);
}

// ------------------------------------------------------------------------------------------------ 3. the UFO results
static void SweepDrawContinueIcon(void *pos)
{
    int32 anim = RSDK.GetFrame(g_hudFrames, HUD_ANI_CONTINUE, 0) ? HUD_ANI_CONTINUE : HUD_ANI_LIFE;
    Animator icon;
    memset(&icon, 0, sizeof(icon));
    RSDK.SetSpriteAnimation(g_hudFrames, anim, &icon, true, 0);
    RSDK.DrawSprite(&icon, (Vector2 *)pos, true);
}

static void SweepSpecialClearDraw(void)
{
    Entity *self = SceneInfo->entity;
    if (!g_resultsOK || g_hudExtra < 0) {
        Mod.Super(self->classID, SUPER_DRAW, NULL);
        return;
    }
    // (where SpecialClear_Draw puts its continue figure, when it does)
    if (*SWEEP_FIELD(bool32, self, SWEEP_SC_HAS_CONTINUES) && *SWEEP_FIELD(bool32, self, SWEEP_SC_CONTINUE_VISIBLE) && ScreenInfo) {
        Vector2 pos = *SWEEP_FIELD(Vector2, self, SWEEP_SC_CONTINUE_POS);
        pos.x += (ScreenInfo->center.x << 16) - 0x560000 + 0xB00000;
        pos.y += 0xA0000;
        WithSaveColours(&g_extras[g_hudExtra], SweepDrawContinueIcon, &pos);
    }
    Animator *cont      = SWEEP_FIELD(Animator, self, SWEEP_SC_CONTINUE_ANIMATOR);
    SpriteFrame *frames = cont->frames;
    cont->frames        = g_sweepBlank; // (the game's figure: its frame number is 0-4)
    // (the name in its own colours: Results.bin's other frames drawn here use none of NAME_SLOTS, the game's continue
    // figure (it does) is blank; ManiaHud.h WithNameColours)
    WithNameColours(&g_extras[g_hudExtra], SweepSuperDraw, NULL);
    cont->frames = frames;
}

// ------------------------------------------------------------------------------------------------ stage load
static void SweepStageLoad(void *data)
{
    (void)data;
    g_itemIconAnim = -1;
    g_resultsOK    = false;
    if (g_mode == MODE_OFF || !g_hudOK || g_hudExtra < 0) // (ManiaHud.h's HudStageLoad ran first: the extra's Hud.bin)
        return;
    const Extra *e = &g_extras[g_hudExtra];
    uint16 at      = RSDK.FindSpriteAnimation(g_hudFrames, "Item Icon");
    if (at < 0x100 && RSDK.GetFrame(g_hudFrames, at, 0))
        g_itemIconAnim = at;
    if (g_specialClearObj && RSDK.FindObject("SpecialClear")) {
        uint16 frames = LoadPackageAni(e, "Results.bin", 0);
        if (frames != 0xFFFF) {
            *SWEEP_FIELD(uint16, g_specialClearObj, SWEEP_SC_ANIFRAMES) = frames; // (SpecialClear_Create, later, uses it)
            g_resultsOK = true;
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "special stage results: %s", e->name);
        }
    }
    if (g_tvVanObj && RSDK.FindObject("TVVan")) {
        uint16 frames = LoadPackageAni(e, "TVVan.bin", 0);
        if (frames != 0xFFFF)
            *SWEEP_FIELD(uint16, g_tvVanObj, SWEEP_TVVAN_ANIFRAMES) = frames; // (TVVan_StageLoad loaded the game's)
    }
}

static void LinkSweep(void)
{
    memset(g_sweepBlank, 0, sizeof(g_sweepBlank));
    Ice_Draw_PlayerBlock_ = Mod.GetPublicFunction(NULL, "Ice_Draw_PlayerBlock");
    Ice_Draw_IceBlock_    = Mod.GetPublicFunction(NULL, "Ice_Draw_IceBlock");
    Mod.RegisterObjectHook((void **)&g_iceObj, "Ice");
    Mod.RegisterObjectHook((void **)&g_itemBoxObj, "ItemBox");
    Mod.RegisterObjectHook((void **)&g_specialClearObj, "SpecialClear");
    Mod.RegisterObjectHook((void **)&g_tvVanObj, "TVVan");
    if (Ice_Draw_PlayerBlock_ || Ice_Draw_IceBlock_)
        Mod.RegisterObject(NULL, NULL, "Ice", 0, 0, 0, NULL, NULL, NULL, SweepIceDraw, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "ItemBox", 0, 0, 0, NULL, NULL, NULL, SweepItemBoxDraw, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "SpecialClear", 0, 0, 0, NULL, NULL, NULL, SweepSpecialClearDraw, NULL, NULL, NULL, NULL, NULL, NULL,
                       NULL);
    Mod.AddModCallback(MODCB_ONSTAGELOAD, SweepStageLoad); // (after HudStageLoad: registered later)
}

#endif // MANIA_SWEEP_H
