// NoSwapMania: the extra in the UFO special stages (included by NoSwapMania.c after ManiaHud.h; LinkUfo in the link).
// Mania draws the UFO runner as a 3D model (UFO_Player_Draw: Special/<Char>Jog / Dash / Jump / Ball / Tumble.bin through
// UFO_Camera's matrices). An extra has no model, so while one plays (Mania Mode's save select, or the Character test
// switch; the scene has no Player object, so this is set up from StageExtra like the HUD's screens) UFO_Player's Draw is
// ours: its 2D spin ball (the frames of its own Player.bin Jump animation, exact pixels) drawn where the model would be.
//   - Where: the model's own origin, the runner's feet (position.x, height, position.y), through UFO_Camera->matWorld and
//     the engine's 3D projection (Scene3D: screen = centre + (x << 8) / z, as UFO_Ring does for its sprites); the ball
//     stands on that point (its frame's bottom there), so it rises with the jump as the model does.
//   - Size: 1x at the camera's normal distance (it follows 160 px behind, so the depth is that almost always); a gentle
//     depth scale only when the camera pulls away (the springboard's arc), clamped to 0.75-1.25 and snapped to exactly 1x
//     near the normal distance, so in normal play the sprite is pixel-exact (a runtime draw effect; the art untouched).
//   - Rolling: its jump frames in turn, faster with ground speed (the jog model's own speed rule), faster still at dash
//     speed (the dash model: past 12 px a frame, and each mach level), one frame every game frame while tumbling (a
//     sphere hit's Tumble model); in the air it keeps the speed it left the ground with.
//   - Colours: the extra's own colours written into its palette slots of bank 0 only while the ball draws, then the
//     stage's put back (UFO_Setup and UFO_HUD use 96-127 for the mach bar, and 64-69 are Sonic's). The playfield's
//     scanline banks are set back to 0 before the player's draw group (UFO_Setup_DrawHook_PrepareDrawingFX on group 3).
// Vanilla characters keep their models (the game's own Draw).
#ifndef MANIA_UFO_H
#define MANIA_UFO_H

#include <stddef.h>

// The decompilation's UFO structs, as far as used (offsets checked against SonicMania/Objects/UFO by compiling them:
// EntityUFO_Player.state 96, angleX 128, height 132, angleZ 140, animator 472; ObjectUFO_Player.jogModel 28;
// ObjectUFO_Camera.matWorld 4; ObjectUFO_Setup.machLevel 24)
typedef struct {
    RSDK_ENTITY
    StateMachine(state);
    int32 machQuota1, machQuota2, machQuota3;
    int32 startingRings;
    int32 timer;
    int32 courseOutTimer;
    int32 angleX;
    int32 height;
    int32 gravityStrength;
    int32 angleZ;
    int32 velDivisor;
    int32 bumperTimer;
    int32 angleVel;
    int32 skidTimer;
    void *camera;
    void *circuitPtr;
    Matrix matRotate, matTransform, matWorld, matNormal;
    StateMachine(stateInput);
    int32 controllerID;
    bool32 up, down, left, right, jumpPress, jumpHold;
    Animator animator;
} EntityUFO_PlayerNS;
_Static_assert(offsetof(EntityUFO_PlayerNS, state) == 96, "UFO_Player.state");
_Static_assert(offsetof(EntityUFO_PlayerNS, angleX) == 128, "UFO_Player.angleX");
_Static_assert(offsetof(EntityUFO_PlayerNS, height) == 132, "UFO_Player.height");
_Static_assert(offsetof(EntityUFO_PlayerNS, angleZ) == 140, "UFO_Player.angleZ");
_Static_assert(offsetof(EntityUFO_PlayerNS, animator) == 472, "UFO_Player.animator");
_Static_assert(sizeof(EntityUFO_PlayerNS) == 504, "EntityUFO_Player");

typedef struct {
    RSDK_OBJECT
    int32 maxSpeed;
    uint16 aniFrames;
    uint16 sfx[9];
    uint16 jogModel, dashModel, jumpModel, ballModel, tumbleModel;
    uint16 sceneIndex;
} ObjectUFO_PlayerNS;
_Static_assert(offsetof(ObjectUFO_PlayerNS, jogModel) == 28, "UFO_Player.jogModel");
_Static_assert(offsetof(ObjectUFO_PlayerNS, tumbleModel) == 36, "UFO_Player.tumbleModel");

typedef struct {
    RSDK_OBJECT
    Matrix matWorld;
    Matrix matView;
    Matrix matTemp;
    bool32 isSS7;
} ObjectUFO_CameraNS;
_Static_assert(offsetof(ObjectUFO_CameraNS, matWorld) == 4, "UFO_Camera.matWorld");

typedef struct {
    RSDK_OBJECT
    uint8 pad[24 - 4];
    int32 machLevel;
} ObjectUFO_SetupNS;
_Static_assert(offsetof(ObjectUFO_SetupNS, machLevel) == 24, "UFO_Setup.machLevel");

#define UFO_NORMAL_DEPTH (160 << 8) // the camera's distance behind the runner (UFO_Camera radius 0x2800 x Sin1024): 1x there
#define UFO_SCALE_MIN    (0x180)
#define UFO_SCALE_MAX    (0x280)
#define UFO_SCALE_SNAP   (0x18)     // within this of 1x (0x200): exactly 1x
#define UFO_DASH_SPEED   (0xC0000)  // UFO_Player_State_Run's dash model threshold

static ObjectUFO_PlayerNS *g_ufoPlayer = NULL; // (the scene's, or NULL: Mod.RegisterObjectHook)
static ObjectUFO_CameraNS *g_ufoCamera = NULL;
static ObjectUFO_SetupNS *g_ufoSetup   = NULL;
static int32 g_ufoExtra   = -1; // the extra running this UFO stage (-1: none, the game's model)
static uint16 g_ufoFrames = 0;  // its Player.bin
static int32 g_ufoCount   = 0;  // its jump animation's frames
static int32 g_ufoPhase   = 0;  // the roll: 256 per frame
static int32 g_ufoRate    = 96; // ... per game frame (kept through a jump)

static bool32 UfoMine(void) { return g_ufoExtra >= 0 && g_ufoPlayer && g_ufoCamera; }

// After the game's update: the roll's speed for what the model would show now
static void UfoUpdate(void)
{
    Mod.Super(SceneInfo->entity->classID, SUPER_UPDATE, NULL);
    if (!UfoMine())
        return;
    EntityUFO_PlayerNS *self = (EntityUFO_PlayerNS *)SceneInfo->entity;
    int32 model              = self->animator.animationID;
    int32 mach               = g_ufoSetup ? g_ufoSetup->machLevel : 0;
    if (model == g_ufoPlayer->tumbleModel)
        g_ufoRate = 256; // (tumbling: a frame every game frame)
    else if (model == g_ufoPlayer->dashModel)
        g_ufoRate = Clamp(192 + 16 * mach, 192, 240);
    else if (model == g_ufoPlayer->jogModel)
        g_ufoRate = Clamp(64 + (Abs(self->groundVel) >> 13), 64, 176); // (the jog model's own: 48 + groundVel >> 12)
    // (the jump and ball models: it keeps rolling as it left the ground)
    g_ufoPhase += g_ufoRate;
}

typedef struct {
    Animator *anim;
    Vector2 pos;
} UfoBall;

static void UfoDrawBall(void *arg)
{
    UfoBall *b = (UfoBall *)arg;
    RSDK.DrawSprite(b->anim, &b->pos, true);
}

// The extra's own colours in bank 0 only while `draw` runs, then the scene's back
static void WithOwnColours(const Extra *e, void (*draw)(void *), void *arg)
{
    uint16 *pal = Mod.GetPaletteBank ? Mod.GetPaletteBank(0) : NULL;
    if (!pal) {
        draw(arg);
        return;
    }
    uint16 saved[OWN_MAX];
    for (int32 i = 0; i < e->ownCount; ++i) saved[i] = pal[e->ownSlot[i]];
    for (int32 i = 0; i < e->ownCount; ++i) RSDK.SetPaletteEntry(0, e->ownSlot[i], e->ownColour[i]);
    draw(arg);
    for (int32 i = 0; i < e->ownCount; ++i) pal[e->ownSlot[i]] = saved[i];
}

static void UfoDraw(void)
{
    if (!UfoMine()) {
        Mod.Super(SceneInfo->entity->classID, SUPER_DRAW, NULL);
        return;
    }
    EntityUFO_PlayerNS *self = (EntityUFO_PlayerNS *)SceneInfo->entity;
    // (the model's origin, its feet: UFO_Player_Draw's translation for the jog / dash / tumble models; projected as
    // UFO_Ring_LateUpdate / _Draw project their sprites)
    const Matrix *m = &g_ufoCamera->matWorld;
    int32 x = self->position.x >> 8, y = self->height >> 8, z = self->position.y >> 8;
    int32 wx = m->values[0][3] + (y * m->values[0][1] >> 8) + (z * m->values[0][2] >> 8) + (x * m->values[0][0] >> 8);
    int32 wy = m->values[1][3] + (y * m->values[1][1] >> 8) + (z * m->values[1][2] >> 8) + (x * m->values[1][0] >> 8);
    int32 wz = m->values[2][3] + (y * m->values[2][1] >> 8) + (z * m->values[2][2] >> 8) + (x * m->values[2][0] >> 8);
    if (wz < 0x100)
        return; // (behind the camera: the engine skips such vertices too)
    RSDKScreenInfo *screen = &ScreenInfo[SceneInfo->currentScreenID];
    int32 sx = screen->center.x + (int32)(((int64)wx << 8) / wz);
    int32 sy = screen->center.y - (int32)(((int64)wy << 8) / wz);

    int32 scale = (int32)((int64)0x200 * UFO_NORMAL_DEPTH / wz);
    scale       = Clamp(scale, UFO_SCALE_MIN, UFO_SCALE_MAX);
    if (Abs(scale - 0x200) <= UFO_SCALE_SNAP)
        scale = 0x200;

    Animator anim;
    memset(&anim, 0, sizeof(anim));
    RSDK.SetSpriteAnimation(g_ufoFrames, ANI_JUMP, &anim, true, 0);
    anim.frameID     = g_ufoCount > 0 ? (g_ufoPhase >> 8) % g_ufoCount : 0;
    anim.speed       = 0;
    SpriteFrame *f   = RSDK.GetFrame(g_ufoFrames, ANI_JUMP, anim.frameID);
    int32 bottom     = f ? f->pivotY + f->height : 16; // (its frame's bottom, px below its pivot)
    UfoBall ball     = { &anim, { sx << 16, (sy << 16) - (int32)((int64)bottom * scale << 7) } };

    uint8 fx    = self->drawFX;
    Vector2 was = self->scale;
    uint8 dir   = self->direction;
    self->drawFX    = scale == 0x200 ? FX_NONE : FX_SCALE;
    self->scale.x   = scale;
    self->scale.y   = scale;
    self->direction = FLIP_NONE;
    WithOwnColours(&g_extras[g_ufoExtra], UfoDrawBall, &ball);
    self->drawFX    = fx;
    self->scale     = was;
    self->direction = dir;
}

static void UfoStageLoad(void *data)
{
    (void)data;
    g_ufoExtra = -1;
    g_ufoPhase = 0;
    g_ufoRate  = 96;
    if (g_mode == MODE_OFF || !g_ufoPlayer || !g_ufoCamera || !RSDK.FindObject("UFO_Player") || !RSDK.FindObject("UFO_Camera"))
        return;
    int32 extra = StageExtra();
    if (extra < 0 || extra >= g_extraCount || !StageHasSonic())
        return;
    const Extra *e = &g_extras[extra];
    g_ufoFrames    = RSDK.LoadSpriteAnimation(e->playerFile, SCOPE_STAGE);
    if (!AniFramesOK(g_ufoFrames, ANI_JUMP)) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "%s is missing or its sheet didn't load: the UFO stage shows the model", e->playerFile);
        return;
    }
    Animator anim;
    memset(&anim, 0, sizeof(anim));
    RSDK.SetSpriteAnimation(g_ufoFrames, ANI_JUMP, &anim, true, 0);
    // (its distinct ball frames: the Jump animation repeats them over Mania's 16-frame template; one turn of them)
    g_ufoCount       = anim.frameCount;
    SpriteFrame *one = RSDK.GetFrame(g_ufoFrames, ANI_JUMP, 0);
    for (int32 k = 1; one && k < anim.frameCount; ++k) {
        SpriteFrame *f = RSDK.GetFrame(g_ufoFrames, ANI_JUMP, k);
        if (f && f->sprX == one->sprX && f->sprY == one->sprY && f->sheetID == one->sheetID) {
            g_ufoCount = k;
            break;
        }
    }
    g_ufoExtra = extra;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "UFO stage: %s rolls as its spin ball (%d frames)", e->name, g_ufoCount);
}

static void LinkUfo(void)
{
    Mod.RegisterObjectHook((void **)&g_ufoPlayer, "UFO_Player");
    Mod.RegisterObjectHook((void **)&g_ufoCamera, "UFO_Camera");
    Mod.RegisterObjectHook((void **)&g_ufoSetup, "UFO_Setup");
    // (only the update and draw are ours; the rest stays the game's)
    Mod.RegisterObject(NULL, NULL, "UFO_Player", 0, 0, 0, UfoUpdate, NULL, NULL, UfoDraw, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.AddModCallback(MODCB_ONSTAGELOAD, UfoStageLoad);
}

#endif // MANIA_UFO_H
