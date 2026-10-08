// NoSwapMania: the extra in the game's HUD and screens (included by NoSwapMania.c after everything it uses; LinkHud at
// the end of the link). Each package's files from tools/build_mania_hud.py, next to its Player.bin:
//   - Hud.bin: 0 its life icon, 1 its act clear name, 2 its continue icon. The icons are its save select pictures
//     (Save.gif, in the menu palette's free slots): drawn with its "save_colors" written in those slots (every bank)
//     only for that draw, then the scene's own put back (as the save select does: SaveSlot_Draw), so they show in their
//     exact colours anywhere. The name is in the global palette's blues (Mania's own letters).
//     3 its signpost face: Mania's own board with its Origins sign face in the panel, in SAVE_SLOTS while drawn (its
//     "sign_colors", as the icons' save colours).
//   - Continue.bin: Players/Continue.bin with Sonic's idle, react and icon the extra's.
//   - SpecialBS.bin: the Blue Spheres runner as the extra's spin ball (its jump frames).
// What it does, only while an extra plays (Mania Mode's save select, or the Character test switch):
//   1. HUD (its Draw wrapped): the life icon. The game's own is drawn from a blank frame (HUD_Draw picks Sonic's frame
//      0 by characterID), then ours where it would be (the entity's lifePos), with the save colours.
//   2. ActClear (its Create wrapped): "<NAME> GOT THROUGH": the name animator on Hud.bin's name, which ends where
//      SONIC's does, so "GOT THROUGH" and the black stripes stay the game's. Its Draw wrapped: the name in the extra's
//      "name_colors" (WithNameColours; SpecialClear's too, ManiaSweep.h).
//   3. Super: the extra's own colours glow toward a pale gold, as in the S3&K DLL (SuperGlow: 96 to 176 of 256). Its
//      colours in Sonic's slots (64-69) go through the game's own Super fade: Player->superPalette_Sonic's rows 1 and 2
//      (and HCZ's / CPZ's water rows) are its colours glowed by 96 and 176, so Player_BlendSuperSonicColors fades in and
//      pulses them as it does Sonic's golds. Its other slots (86-90, 111, 127) follow the same blend each frame (bank 0).
//      Extras with "super_fade" slots (Metal Sonic: Sonic's golds) keep that look.
//   4. The continue scene (Ending, ContinueSetup / ContinuePlayer: no Player object there, so the main code does
//      nothing): Continue.bin in place of the game's, the extra's Player.bin for the run off, its colours in banks 0 and
//      1 (ContinueSetup draws the whole screen with bank 1), and the save colours while ContinueSetup draws its icons.
//   5. Blue Spheres (SpecialBS, no Player object either): BSS_Player's Sonic frames are SpecialBS.bin, its colours in
//      bank 0 (the stage writes only 128-162 and 208-211 there).
//   6. SignPost (its Draw wrapped): the face plate on Sonic's face (SIGNPOSTANI_SONIC: the extra is hosted on Sonic) is
//      drawn from Hud.bin's Sign Face frames instead (the animator's own frame number and timing kept), its colours
//      written only for that draw.
//   7. Chemical Plant 1's intro (CPZ1Intro): CPZ1Intro->playerFrames is the package's CutsceneCPZ.bin, the game's with
//      the Sonic / Tails / Knuckles animations showing the extra's own Look Up (Mania's own fallback, pre-Plus Tails'),
//      every frame count and timing kept, so the cutscene's steps (Player_State_Static, its end on the animation's last
//      frame) run exactly as the game's; ReadyStage then sets its own Idle from player 1's sprites (the extra's).
// Not done: the UFO special stages (a 3D Sonic model), SpecialClear's name and icon (its own results font).
#ifndef MANIA_HUD_H
#define MANIA_HUD_H

// Offsets in the decompilation's own structs (Plus build; tools: native/mania/check_layout.sh's way, compiled against
// SonicMania/Objects: EntityHUD.lifePos 128, .lifeIconAnimator 472; EntityActClear.playerNameAnimator 272)
#define HUD_LIFE_POS        (128)
#define HUD_LIFE_ANIMATOR   (472)
#define ACTCLEAR_NAME_ANIMATOR (272)
#define SIGNPOST_FACE_ANIMATOR (224) // EntitySignPost.facePlateAnimator
#define SIGNPOSTANI_SONIC_ID   (0)

typedef struct {
    RSDK_OBJECT
    uint16 aniFrames;       // Players/Continue.bin
    uint16 playerAniFrames; // the player's own sprites (the run off)
    uint16 tailAniFrames;
} ObjectContinuePlayerHud;
_Static_assert(offsetof(ObjectContinuePlayerHud, aniFrames) == 4, "ContinuePlayer.aniFrames");
_Static_assert(offsetof(ObjectContinuePlayerHud, playerAniFrames) == 6, "ContinuePlayer.playerAniFrames");

typedef struct {
    RSDK_OBJECT
    uint16 jumpPressState;
    uint16 unused1;
    uint16 sonicFrames; // SpecialBS/Sonic.bin
    uint16 tailsFrames; // SpecialBS/Tails.bin (an extra hosted on Tails: ManiaHost.h)
    uint16 knuxFrames;  // SpecialBS/Knuckles.bin
} ObjectBSS_PlayerHud;
_Static_assert(offsetof(ObjectBSS_PlayerHud, sonicFrames) == 8, "BSS_Player.sonicFrames");
_Static_assert(offsetof(ObjectBSS_PlayerHud, tailsFrames) == 10, "BSS_Player.tailsFrames");
_Static_assert(offsetof(ObjectBSS_PlayerHud, knuxFrames) == 12, "BSS_Player.knuxFrames");

typedef struct {
    RSDK_OBJECT
    uint16 aniFrames; // Global/SignPost.bin
} ObjectSignPostHud;
_Static_assert(offsetof(ObjectSignPostHud, aniFrames) == 4, "SignPost.aniFrames");

typedef struct {
    RSDK_OBJECT
    uint16 playerFrames; // Players/CutsceneCPZ.bin
} ObjectCPZ1IntroHud;
_Static_assert(offsetof(ObjectCPZ1IntroHud, playerFrames) == 4, "CPZ1Intro.playerFrames");

enum { HUD_ANI_LIFE, HUD_ANI_NAME, HUD_ANI_CONTINUE, HUD_ANI_SIGN };
#define SUPER_GLOW_TO (0xFFF0A0) // a pale gold (the S3&K DLL's and abilities.py's)

static ObjectContinuePlayerHud *g_contPlayer = NULL; // (the scene's, or NULL: Mod.RegisterObjectHook)
static ObjectBSS_PlayerHud *g_bssPlayer      = NULL;
static ObjectSignPostHud *g_signPost         = NULL;
static ObjectCPZ1IntroHud *g_cpz1Intro       = NULL;
static int32 g_hudExtra    = -1;    // the extra in this scene's HUD and screens (-1: none)
static uint16 g_hudFrames  = 0;     // its Hud.bin
static bool32 g_hudOK      = false; // ... loaded
static bool32 g_signOK     = false; // ... with its signpost face (Hud.bin's Sign Face, as many frames as Sonic's)
static int32 g_signAni     = SIGNPOSTANI_SONIC_ID; // SignPost.bin's face animation of its host (0 Sonic, 1 Tails, 2 Knuckles)
static bool32 g_contScene  = false; // this is the continue scene, set up for the extra
static int32 g_glowWrote   = 0;     // the Super glow last written to its other slots (0: its own colours)
static SpriteFrame g_blankFrames[8]; // (all 0 wide: DrawSprite draws nothing)

static color Glow(color c, int32 amount)
{
    if (amount <= 0)
        return c;
    color out = 0;
    for (int32 shift = 16; shift >= 0; shift -= 8) {
        int32 v = (c >> shift) & 0xFF, to = (SUPER_GLOW_TO >> shift) & 0xFF;
        v += (to - v) * amount / 256;
        out |= (color)v << shift;
    }
    return out;
}

// A package file next to its Player.bin ("NoSwap/<folder>/Player.bin" -> "NoSwap/<folder>/<name>")
static void PackageFile(const Extra *e, const char *name, char *out, size_t size)
{
    const char *slash = strrchr(e->playerFile, '/');
    int32 dir         = slash ? (int32)(slash - e->playerFile + 1) : 0;
    snprintf(out, size, "%.*s%s", dir, e->playerFile, name);
}

static uint16 LoadPackageAni(const Extra *e, const char *name, int32 anim)
{
    char path[160];
    PackageFile(e, name, path, sizeof(path));
    uint16 id = RSDK.LoadSpriteAnimation(path, SCOPE_STAGE);
    if (!AniFramesOK(id, anim)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s is missing or its sheet didn't load: that screen shows Sonic for %s", path, e->name);
        return 0xFFFF;
    }
    return id;
}

// `count` colours in `slots` (at most `slotCount`) in every bank while `draw` runs, then the scene's own back
static void WithSlotColours(const uint8 *slots, int32 slotCount, const color *colours, int32 count, void (*draw)(void *), void *arg)
{
    if (!Mod.GetPaletteBank) {
        draw(arg);
        return;
    }
    uint16 saved[8][SAVE_PAL_COUNT];
    if (slotCount > SAVE_PAL_COUNT)
        slotCount = SAVE_PAL_COUNT;
    for (int32 bank = 0; bank < 8; ++bank) {
        uint16 *pal = Mod.GetPaletteBank(bank);
        if (pal)
            for (int32 c = 0; c < slotCount; ++c) saved[bank][c] = pal[slots[c]];
        for (int32 c = 0; c < count && c < slotCount; ++c) RSDK.SetPaletteEntry(bank, slots[c], colours[c]);
    }
    draw(arg);
    for (int32 bank = 0; bank < 8; ++bank) {
        uint16 *pal = Mod.GetPaletteBank(bank);
        if (pal)
            for (int32 c = 0; c < slotCount; ++c) pal[slots[c]] = saved[bank][c];
    }
}

// `count` colours in SAVE_SLOTS (the icons' slots) in every bank while `draw` runs, then the scene's own back
static void WithColours(const color *colours, int32 count, void (*draw)(void *), void *arg)
{
    WithSlotColours(SAVE_SLOTS, SAVE_PAL_COUNT, colours, count, draw, arg);
}

// The extra's results name colours ("name_colors") in SONIC's letters' slots (NAME_SLOTS) while `draw` runs: its name
// on Hud.gif / Results.bin is in those slots, as Tails' and Knuckles' names are drawn in their own (19-23 / 80-85);
// none: Sonic's blue, as before
static void WithNameColours(const Extra *e, void (*draw)(void *), void *arg)
{
    if (e->nameColourCount)
        WithSlotColours(NAME_SLOTS, NAME_PAL_COUNT, e->nameColours, e->nameColourCount, draw, arg);
    else
        draw(arg);
}

static void WithSaveColours(const Extra *e, void (*draw)(void *), void *arg)
{
    WithColours(e->saveColours, e->saveColourCount, draw, arg);
}

static void WriteOwnColours(uint8 bank, const Extra *e)
{
    for (int32 i = 0; i < e->ownCount; ++i) RSDK.SetPaletteEntry(bank, e->ownSlot[i], e->ownColour[i]);
}

// ------------------------------------------------------------------------------------------------ 1. the life icon
// (after a death, Player_HandleDeath sets the player's classID to TYPE_BLANK for the whole fade out (HUD_Draw still
// reads its characterID and lives): a blank slot with the host's ID is still the extra's, or Sonic's face showed till
// the fade ended; the user, 2026-10-03)
static bool32 HudMine(EntityPlayer *p)
{
    bool32 mine = IsExtra(p) || (g_active && p && p->classID == TYPE_BLANK && p->characterID == g_hostID);
    return g_hudOK && mine && globals->gameMode != MODE_COMPETITION && globals->gameMode != MODE_ENCORE;
}

static void DrawLifeIcon(void *pos)
{
    Animator anim;
    memset(&anim, 0, sizeof(anim));
    RSDK.SetSpriteAnimation(g_hudFrames, HUD_ANI_LIFE, &anim, true, 0);
    RSDK.DrawSprite(&anim, (Vector2 *)pos, true);
}

static void HudDraw(void)
{
    Entity *self    = SceneInfo->entity;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SceneInfo->currentScreenID);
    if (!HudMine(p)) {
        Mod.Super(self->classID, SUPER_DRAW, NULL);
        return;
    }
    Animator *life      = (Animator *)((uint8 *)self + HUD_LIFE_ANIMATOR);
    SpriteFrame *frames = life->frames;
    life->frames        = g_blankFrames;
    Mod.Super(self->classID, SUPER_DRAW, NULL);
    life->frames = frames;
    Vector2 pos = *(Vector2 *)((uint8 *)self + HUD_LIFE_POS); // (where HUD_Draw draws it, screen-relative)
    WithSaveColours(&g_extras[g_hudExtra], DrawLifeIcon, &pos);
}

// ------------------------------------------------------------------------------------------------ 2. the act clear name
static void ActClearCreate(void *data)
{
    // (the class by name: during a create the engine hasn't set the entity's classID yet (RSDK::CreateEntity sets it
    // after create returns), so SceneInfo->entity->classID was 0 and Super ran the blank object's create: ActClear never
    // set itself up (no text, no tally, controls never taken; the user, 2026-10-01))
    Mod.Super(RSDK.FindObject("ActClear"), SUPER_CREATE, data);
    if (SceneInfo->inEditor || !HudMine((EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        return;
    RSDK.SetSpriteAnimation(g_hudFrames, HUD_ANI_NAME, (Animator *)((uint8 *)SceneInfo->entity + ACTCLEAR_NAME_ANIMATOR), true, 0);
}

static void ActClearSuperDraw(void *data)
{
    (void)data;
    Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

// The name in the extra's own colours: ActClear_Draw's other sprites (HUD.bin's GOT THROUGH, act number, bonus words,
// numbers) use none of NAME_SLOTS (their slots: 34-41, 59), so this is only while its name draws
static void ActClearDraw(void)
{
    if (!SceneInfo->inEditor && HudMine((EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)))
        WithNameColours(&g_extras[g_hudExtra], ActClearSuperDraw, NULL);
    else
        Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

// ------------------------------------------------------------------------------------------------ 3. Super
// Each frame: Sonic's Super rows for the extra's colours in his slots (rows 1-2 its own glowed; SetupSuper wrote its
// own in all three), and its other slots at the blend the game is at (rows 0-1 while fading in or out: 0 to 96; rows
// 1-2 once it pulses: 96 to 176)
static bool32 GlowsWhenSuper(const Extra *e)
{
    if (e->more.amy.on)
        return false; // (Amy: her own Super palette cycle, ManiaAmy.h)
    for (int32 i = 0; i < e->ownCount; ++i)
        if (e->superFade[i])
            return false; // (Sonic's golds instead: Metal)
    return true;
}

static void SuperGlowFrame(void)
{
    const Extra *e = g_cur;
    if (!g_active || !e || !Player || !GlowsWhenSuper(e))
        return;
    color *rows[3] = { Player->superPalette_Sonic, Player->superPalette_Sonic_HCZ, Player->superPalette_Sonic_CPZ };
    for (int32 i = 0; i < e->ownCount; ++i) {
        if (!IsSonicSlot(e->ownSlot[i]))
            continue;
        int32 c = e->ownSlot[i] - PLAYER_PALETTE_INDEX_SONIC;
        for (int32 w = 0; w < 3; ++w) {
            rows[w][6 + c]  = Glow(rows[w][c], 96);
            rows[w][12 + c] = Glow(rows[w][c], 176);
        }
    }
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    int32 glow      = 0;
    if (IsExtra(p) && p->superState != SUPERSTATE_NONE) {
        int32 amount = p->superBlendAmount < 0 ? 0 : p->superBlendAmount > 256 ? 256 : p->superBlendAmount;
        glow         = p->superBlendState >= 2 ? 96 + 80 * amount / 256 : 96 * amount / 256;
    }
    if (glow == g_glowWrote)
        return;
    if ((glow > 0) != (g_glowWrote > 0))
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "super glow %s", glow > 0 ? "on" : "off");
    g_glowWrote = glow;
    for (int32 i = 0; i < e->ownCount; ++i)
        if (!IsSonicSlot(e->ownSlot[i]))
            RSDK.SetPaletteEntry(0, e->ownSlot[i], Glow(e->ownColour[i], glow));
}

// ------------------------------------------------------------------------------------------------ 4. continue
static void ContinueSuperDraw(void *data)
{
    (void)data;
    Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

static void ContinueSetupDraw(void)
{
    if (g_contScene && g_hudExtra >= 0)
        WithSaveColours(&g_extras[g_hudExtra], ContinueSuperDraw, NULL); // (its countdown icons: Continue.bin's Icon)
    else
        Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

// ------------------------------------------------------------------------------------------------ 6. the signpost
static void SignSuperDraw(void *data)
{
    (void)data;
    Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
}

static void SignPostDraw(void)
{
    Entity *self   = SceneInfo->entity;
    Animator *face = (Animator *)((uint8 *)self + SIGNPOST_FACE_ANIMATOR);
    // (Sonic's face only: the face of whoever passed it, and the extra is player 1 hosted on Sonic; Tails' and the
    // others' stay the game's)
    if (!g_signOK || !g_signPost || !HudMine((EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1)) || face->animationID != g_signAni
        || face->frames != RSDK.GetFrame(g_signPost->aniFrames, g_signAni, 0)) {
        Mod.Super(self->classID, SUPER_DRAW, NULL);
        return;
    }
    SpriteFrame *frames = face->frames;
    face->frames        = RSDK.GetFrame(g_hudFrames, HUD_ANI_SIGN, 0);
    const Extra *e      = &g_extras[g_hudExtra];
    WithColours(e->signColours, e->signColourCount, SignSuperDraw, NULL);
    face->frames = frames;
}

// ------------------------------------------------------------------------------------------------ stage load
static void HudStageLoad(void *data)
{
    (void)data;
    g_hudExtra  = -1;
    g_hudOK     = false;
    g_signOK    = false;
    g_contScene = false;
    g_glowWrote = 0;
    if (g_mode == MODE_OFF)
        return;
    int32 extra = StageExtra();
    if (extra < 0 || extra >= g_extraCount || !StageHasSonic())
        return;
    const Extra *e = &g_extras[extra];
    g_hudExtra     = extra;
    g_hudFrames    = LoadPackageAni(e, "Hud.bin", HUD_ANI_NAME);
    g_hudOK        = g_hudFrames != 0xFFFF;
    // (an extra hosted on Knuckles: ActClear_Draw sets KNUCKLES' name further right, with its own "GOT THROUGH" after it;
    // the name ends where KNUCKLES' does then, as it ends where SONIC's does for the others; ManiaHost.h)
    if (g_hudOK && HostIndex(e) == 2 && RSDK.FindObject("ActClear")) {
        uint16 hud = RSDK.LoadSpriteAnimation("Global/HUD.bin", SCOPE_STAGE);
        uint16 at  = hud < 0x400 ? RSDK.FindSpriteAnimation(hud, "Player Name") : 0xFFFF;
        SpriteFrame *knux = at < 0x1000 ? RSDK.GetFrame(hud, at, 2) : NULL, *ours = RSDK.GetFrame(g_hudFrames, HUD_ANI_NAME, 0);
        if (knux && ours)
            ours->pivotX = (int16)(knux->pivotX + knux->width - ours->width);
    }
    // (its sign face: as many frames as SignPost.bin's Sonic animation, since the face animator keeps its frame number)
    if (g_hudOK && g_signPost && e->signColourCount && RSDK.FindObject("SignPost")) {
        Animator sonic, ours;
        memset(&sonic, 0, sizeof(sonic));
        memset(&ours, 0, sizeof(ours));
        g_signAni = HostIndex(e); // (the host's face: Sonic's, Tails' or Knuckles'; ManiaHost.h)
        RSDK.SetSpriteAnimation(g_signPost->aniFrames, g_signAni, &sonic, true, 0);
        if (AniFramesOK(g_hudFrames, HUD_ANI_SIGN))
            RSDK.SetSpriteAnimation(g_hudFrames, HUD_ANI_SIGN, &ours, true, 0);
        g_signOK = sonic.frameCount > 0 && ours.frameCount >= sonic.frameCount;
        if (g_signOK)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "signpost: %s's face", e->name);
        else
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s's Hud.bin has no sign face: the signpost shows Sonic", e->name);
    }

    // (player 1 is the extra: StageExtra; the players aren't created yet at stage load)
    if (g_cpz1Intro && RSDK.FindObject("CPZ1Intro")) {
        uint16 frames = LoadPackageAni(e, "CutsceneCPZ.bin", 0);
        if (frames != 0xFFFF) {
            g_cpz1Intro->playerFrames = frames; // (CPZ1Intro_StageLoad loaded the game's: the cutscene starts later)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "Chemical Plant intro: %s looks up", e->name);
        }
    }
    if (g_bssPlayer && RSDK.FindObject("BSS_Player")) {
        uint16 frames = LoadPackageAni(e, "SpecialBS.bin", 0);
        if (frames != 0xFFFF) {
            g_bssPlayer->sonicFrames = frames; // (BSS_Player_Create, after this, gives Sonic these)
            if (HostIndex(e) == 1)             // (... or its host: ManiaHost.h; Tails' tail animation (4) isn't in
                g_bssPlayer->tailsFrames = frames; // SpecialBS.bin, so no tail is drawn)
            else if (HostIndex(e) == 2)
                g_bssPlayer->knuxFrames = frames;
            WriteOwnColours(0, e);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "Blue Spheres: %s rolls as its spin ball", e->name);
        }
    }
    if (g_contPlayer && RSDK.FindObject("ContinuePlayer") && RSDK.FindObject("ContinueSetup")) {
        uint16 cont   = LoadPackageAni(e, "Continue.bin", 0);
        uint16 player = RSDK.LoadSpriteAnimation(e->playerFile, SCOPE_STAGE);
        if (cont != 0xFFFF && AniFramesOK(player, ANI_WALK)) {
            g_contPlayer->aniFrames       = cont; // (ContinuePlayer_Create and ContinueSetup_Create, after this)
            g_contPlayer->playerAniFrames = player;
            WriteOwnColours(0, e);
            WriteOwnColours(1, e); // (ContinueSetup draws the screen with bank 1)
            g_contScene = true;
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "continue: %s", e->name);
        }
    }
}

static void HudLateUpdate(void *data)
{
    (void)data;
    SuperGlowFrame();
}

static void LinkHud(void)
{
    memset(g_blankFrames, 0, sizeof(g_blankFrames));
    Mod.RegisterObjectHook((void **)&g_bssPlayer, "BSS_Player");
    Mod.RegisterObjectHook((void **)&g_contPlayer, "ContinuePlayer");
    Mod.RegisterObjectHook((void **)&g_signPost, "SignPost");
    Mod.RegisterObjectHook((void **)&g_cpz1Intro, "CPZ1Intro");
    // (only these events are ours; the rest stays the game's)
    Mod.RegisterObject(NULL, NULL, "HUD", 0, 0, 0, NULL, NULL, NULL, HudDraw, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "ActClear", 0, 0, 0, NULL, NULL, NULL, ActClearDraw, ActClearCreate, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "SignPost", 0, 0, 0, NULL, NULL, NULL, SignPostDraw, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "ContinueSetup", 0, 0, 0, NULL, NULL, NULL, ContinueSetupDraw, NULL, NULL, NULL, NULL, NULL, NULL,
                       NULL);
    Mod.AddModCallback(MODCB_ONSTAGELOAD, HudStageLoad);  // (after OnStageLoad: registered later)
    Mod.AddModCallback(MODCB_ONLATEUPDATE, HudLateUpdate); // (after OnLateUpdate)
}

#endif // MANIA_HUD_H
