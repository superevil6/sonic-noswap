// NoSwapMania: Amy Rose's moves (a package with an "amy" section: tools/mania_only.py; its numbers ManiaAmyData.h), as
// Origins Plus plays them in Sonic 3 & Knuckles (read from the exe: Action_DblJumpAmy 0x1401db9d0, the Hammer Jump's
// state 0x1401ea5e0, the Hammer Dash's 0x1401ea4a0, SuperHammer; scratchpad amy/STATUS.md):
//   - Hammer Jump: a second jump press in mid-air, in the jump (where Sonic's insta-shield / drop dash would start):
//     her Hammer Jump animation (keeping the jump's frame and speed), Global/HammerJump.wav, no change of speed; letting
//     go of jump no longer cuts the jump short. Once per jump; underwater and Super too. With a shield, up held and not
//     Super: the shield's own move instead (Sonic's code). Y in the jump still turns her Super (Sonic's code).
//   - Hammer Dash: jump held through the Hammer Jump for chargeFrames (20): Global/DropDash.wav; letting go after that
//     loses the charge (the sound stopped). Landing charged: Global/HammerDash.wav and her own state
//     (Amy_State_HammerDash): dashSpeed (6 px) flat, no friction or slope, left / right turn her at once, off ledges too
//     (falling), until jump is let go, dashFrames (60) pass, a wall stops her or the floor turns into a wall / ceiling.
//   - The hammer's reach: in both, her hits use the frame's AttackBox (the third box; Hammer Jump +-25 px, the dash's
//     forward boxes). Mania's attack check reads box 0 only, so for every hittable object (ManiaShot.h HIT_CLASSES) near
//     her during them, its update runs with her animator on the "<name> Reach" copy (box 0 = the AttackBox, the same
//     frame; tools/mania_v5_art.py), reported as the jump, and her real body box as outerbox (what hurts her, solid
//     objects); the game's own code does the rest (the badnik's bounce, the boss' rebound, monitors).
//     Global/HammerHit.wav on a badnik or boss hit.
//   - Hammer Throw (SuperHammer): Y, Origins' HYPER Amy only; here AMY_THROW_GATE (Mania has no Hyper: Super). Standing
//     (idle, bored, look up, crouch, balance): her Hammer Throw pose, the hammer leaving on its frame 1; moving or in the
//     air (walk... dash, the jump and the Hammer Jump, spin dash, push, breathe): thrown at once. The hammer is the
//     package's shot (NoSwapShot: an arc through everything, gone offscreen or after a hit), cooldown 6, no limit.
//   - Physics: Sonic's (the package changes none); jumpOffset 2 px and sensorY 17 px (her frames stand on 17); no drop
//     dash, insta-shield or Peel Out (her jump press is the Hammer Jump; statePeelout cleared).
//   - Super Amy: her own palette cycle (Origins' rows, her five pinks) instead of the generic Super glow.
//   - Outta Here: never (her sheet has no such animation: the game would wait on its frame 14 forever).
// Included once, by NoSwapMania.c (after ManiaHost.h).
#ifndef MANIA_AMY_H
#define MANIA_AMY_H

// The Hammer Throw's gate (Origins: Hyper Amy only). AMY_THROW_SUPER: while Super; AMY_THROW_ALWAYS: always
#define AMY_THROW_ALWAYS (0)
#define AMY_THROW_SUPER  (1)
#define AMY_THROW_GATE   AMY_THROW_SUPER

// Her sounds: Origins' own (tools/origins_sfx.py into the mod's Data/SoundFX; loaded by Data/Game/Game.xml), the charge
// Mania's drop dash (as Origins). The throw's is the package's shot "sound".
#define AMY_SFX_JUMP   "Global/HammerJump.wav"
#define AMY_SFX_CHARGE "Global/DropDash.wav"
#define AMY_SFX_DASH   "Global/HammerDash.wav"
#define AMY_SFX_HIT    "Global/HammerHit.wav"

enum { AMY_SHIELD_NONE, AMY_SHIELD_BLUE, AMY_SHIELD_BUBBLE, AMY_SHIELD_FIRE, AMY_SHIELD_LIGHTNING };

typedef struct {
    bool32 jump;     // in the Hammer Jump
    int32 charge;    // frames jump has been held through it
    bool32 charging; // ... may still charge (until it has once)
    bool32 dashing;  // in the Hammer Dash
    int32 dash;      // ... its frames
} AmyMove;
static AmyMove g_amy[PLAYER_COUNT];

static bool32 g_amyOn = false; // the extra playing is Amy, set up this stage
static int32 g_amyJumpAnim = -1, g_amyDashAnim = -1, g_amyThrowAnim = -1, g_amyJumpReach = -1, g_amyDashReach = -1;
static uint16 g_amySfxJump = 0xFFFF, g_amySfxCharge = 0xFFFF, g_amySfxDash = 0xFFFF, g_amySfxHit = 0xFFFF;
static void (*Player_HandleAirMovement_)(void);
static void (*Player_HandleGroundRotation_)(void);
static void (*Player_Gravity_False_)(void);
static struct {
    int32 left;     // the standing throw's pose: frames left
    bool32 pending; // ... the hammer not thrown yet
    Animator anim;  // ... its animation (the ground state sets hers every frame: this one is copied over it)
} g_amyPose;

static AmyMove *AmyOf(EntityPlayer *p)
{
    int32 slot = RSDK.GetEntitySlot(p);
    return slot >= 0 && slot < PLAYER_COUNT ? &g_amy[slot] : NULL;
}

static void AmySfx(uint16 sfx)
{
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}

static void Amy_State_HammerDash(void);
static void EachPlayer(void (*fn)(EntityPlayer *)); // (NoSwapMania.c)

// ------------------------------------------------------------------------------------------------ Hammer Jump
// Hook_JumpAbilitySonic, for Amy, on the jump press that starts a jump ability: true: done (Sonic's code skipped)
static bool32 AmyJump(EntityPlayer *self)
{
    AmyMove *a = AmyOf(self);
    if (!g_amyOn || !a)
        return false; // (not set up: Sonic's own)
    if (self->shield != AMY_SHIELD_NONE && self->up && self->superState != SUPERSTATE_SUPER) {
        if (self->shield >= AMY_SHIELD_BUBBLE && !self->invincibleTimer)
            return false; // (the shield's own move: Sonic's code)
        self->jumpAbilityState = 0;
        return true; // (the blue shield's would be the drop dash: nothing)
    }
    self->jumpAbilityState = 0;
    a->jump     = true;
    a->charge   = 0;
    a->charging = true;
    int32 frame = self->animator.frameID;
    int16 speed = self->animator.speed;
    Show(self, g_amyJumpAnim, true, true);
    if (self->animator.frameCount > 0)
        self->animator.frameID = frame % self->animator.frameCount;
    self->animator.speed = speed;
    self->applyJumpCap   = false;
    AmySfx(g_amySfxJump);
    return true;
}

// The Hammer Dash starts (landed charged)
static void AmyDashStart(EntityPlayer *self, AmyMove *a)
{
    const AmyData *d = &g_cur->more.amy;
    a->dashing            = true;
    a->dash               = 0;
    self->groundVel       = (self->direction & FLIP_X) ? -d->dashSpeed : d->dashSpeed;
    self->applyJumpCap    = false;
    self->nextAirState    = NULL;
    self->nextGroundState = NULL;
    self->state           = Amy_State_HammerDash;
    Show(self, g_amyDashAnim, true, true);
    AmySfx(g_amySfxDash);
}

// Hook_StateAir (after Player_State_Air), for Amy: the Hammer Jump's frame, its charge and landing
static void AmyAir(EntityPlayer *self)
{
    AmyMove *a = AmyOf(self);
    if (!g_amyOn || !a || !a->jump)
        return;
    const AmyData *d = &g_cur->more.amy;
    bool32 shown     = self->animator.animationID == ANI_JUMP && Showing(self, g_amyJumpAnim);
    // landed (the air state just made it the ground's). Not gated on `shown`: Mania's own landing code has already swapped
    // her animation to walk / idle on this frame, so the charged dash never started (the user, 2026-10-01)
    if (self->onGround && self->state == Player_State_Ground_) {
        a->jump = false;
        if (a->charge >= d->chargeFrames && g_amyDashAnim >= 0)
            AmyDashStart(self, a);
        else if (shown)
            BackToJump(self); // (lands as the jump ball does)
        return;
    }
    if (self->state != Player_State_Air_ || !shown) { // a spring, a hit, an object taking her...
        a->jump = false;
        if (a->charge >= d->chargeFrames && g_amySfxCharge != 0xFFFF)
            RSDK.StopSfx(g_amySfxCharge);
        if (shown)
            BackToJump(self);
        return;
    }
    self->applyJumpCap = false;
    if (self->jumpHold) {
        if (a->charging && ++a->charge >= d->chargeFrames) {
            a->charging = false;
            AmySfx(g_amySfxCharge);
        }
    }
    else if (a->charge >= d->chargeFrames) { // let go charged: lost
        a->charge = 0;
        if (g_amySfxCharge != 0xFFFF)
            RSDK.StopSfx(g_amySfxCharge);
    }
}

// Before Player_State_Ground (a state hook, run first: true skips the game's ground state this frame): her landing out of
// the Hammer Jump. Mania lands a player outside the air state (Player_Update, after the movement: onGround with a
// nextGroundState switches straight to the ground state), so AmyAir (after the air state) never saw it and the charged
// dash never started (the user, 2026-10-01). Landed charged: the dash, the ground state skipped (its friction would eat
// the speed); otherwise the jump's over and the ground state runs as usual.
static bool32 AmyGroundBefore(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!g_amyOn || !self || !IsExtra(self))
        return false;
    AmyMove *a = AmyOf(self);
    if (!a || !a->jump || !self->onGround)
        return false;
    const AmyData *d = &g_cur->more.amy;
    a->jump = false;
    if (a->charge >= d->chargeFrames && g_amyDashAnim >= 0 && !Hurt(self)) {
        AmyDashStart(self, a);
        return true;
    }
    return false;
}

// ------------------------------------------------------------------------------------------------ Hammer Dash
static void AmyDashEnd(EntityPlayer *self, AmyMove *a)
{
    a->dashing = false;
    a->dash    = 0;
    bool32 ours = Showing(self, g_amyDashAnim);
    if (self->onGround) {
        self->state = Player_State_Ground_;
        if (ours)
            RSDK.SetSpriteAnimation(g_extraFrames, Abs(self->groundVel) >= self->topSpeed ? ANI_RUN : ANI_WALK, &self->animator, true, 0);
    }
    else {
        self->state = Player_State_Air_;
        if (ours)
            RSDK.SetSpriteAnimation(g_extraFrames, ANI_AIR_WALK, &self->animator, true, 0);
    }
}

// Her own state (Origins' 0x1401ea4a0): the ground's rotation or the air's gravity, then the dash's speed
static void Amy_State_HammerDash(void)
{
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    AmyMove *a         = AmyOf(self);
    if (!a || !g_amyOn || !IsExtra(self)) {
        self->state = self->onGround ? Player_State_Ground_ : Player_State_Air_;
        return;
    }
    const AmyData *d = &g_cur->more.amy;
    if (self->onGround) {
        Player_HandleGroundRotation_();
        Player_Gravity_False_();
    }
    else {
        Player_HandleAirMovement_();
    }
    if (!self->jumpHold || ++a->dash >= d->dashFrames || self->groundVel == 0) { // (0: a wall stopped her)
        AmyDashEnd(self, a);
        return;
    }
    if (self->left)
        self->direction = FLIP_X;
    else if (self->right)
        self->direction = FLIP_NONE;
    self->groundVel = (self->direction & FLIP_X) ? -d->dashSpeed : d->dashSpeed;
    if (self->angle >= 0x41 && self->angle <= 0xC0) { // the floor turned into a wall or a ceiling
        AmyDashEnd(self, a);
        return;
    }
    Show(self, g_amyDashAnim, true, false);
}

// ------------------------------------------------------------------------------------------------ the hammer's reach
// HitUpdate, before the shots: a hittable object near her during the Hammer Jump or Dash updates with her animator on
// the Reach copy (box 0 = the AttackBox) and her body box as outerbox; true: its update has run
static bool32 AmyStrike(Entity *target, int32 kind, EntityPlayer *p)
{
    if (!g_amyOn || !p || !IsExtra(p) || !p->interaction || Hurt(p))
        return false;
    AmyMove *a = AmyOf(p);
    if (!a)
        return false;
    int32 reach = -1;
    if (a->jump && p->state == Player_State_Air_ && Showing(p, g_amyJumpAnim))
        reach = g_amyJumpReach;
    else if (a->dashing && p->state == Amy_State_HammerDash && Showing(p, g_amyDashAnim))
        reach = g_amyDashReach;
    if (reach < 0)
        return false;
    int32 range = (kind == HIT_BOSS ? REACH_BOSS : REACH_BADNIK) << 16;
    if (Abs(target->position.x - p->position.x) > range || Abs(target->position.y - p->position.y) > range)
        return false;

    Animator real = p->animator, hammer;
    memset(&hammer, 0, sizeof(hammer));
    RSDK.SetSpriteAnimation(g_extraFrames, reach, &hammer, true, 0);
    if (hammer.frameCount <= 0)
        return false;
    hammer.frameID     = real.frameID < hammer.frameCount ? real.frameID : 0;
    hammer.animationID = ANI_JUMP;
    Hitbox *outer = p->outerbox, *inner = p->innerbox;
    p->outerbox   = RSDK.GetHitbox(&real, 0);
    p->innerbox   = RSDK.GetHitbox(&real, 1);
    p->animator   = hammer;
    uint16 cls    = target->classID;
    int32 vy      = p->velocity.y, gravity = p->gravityStrength;

    Mod.Super(cls, SUPER_UPDATE, NULL);

    if (p->animator.frames == hammer.frames) // (the game set no animation of its own meanwhile)
        p->animator = real;
    p->outerbox = outer;
    p->innerbox = inner;
    bool32 hit = kind == HIT_BADNIK ? target->classID != cls || p->velocity.y != vy // (gone, or her badnik bounce)
                                    : kind == HIT_BOSS && p->velocity.y == -(vy + 2 * gravity) && vy != -gravity; // (Player_CheckBossHit's rebound)
    if (hit) {
        AmySfx(g_amySfxHit);
        static int32 logs = 0;
        if (logs++ < 40)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "amy: hammer hit class %d (%s)", cls, kind == HIT_BOSS ? "boss" : "badnik");
    }
    return true;
}

// ------------------------------------------------------------------------------------------------ Hammer Throw
static bool32 AmyStanding(int32 a)
{
    return a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_LOOK_UP || a == ANI_CROUCH || a == ANI_BALANCE_1
           || a == ANI_BALANCE_2;
}

static bool32 AmyMoving(int32 a)
{
    return a == ANI_WALK || a == ANI_AIR_WALK || a == ANI_JOG || a == ANI_RUN || a == ANI_DASH || a == ANI_JUMP || a == ANI_SPINDASH
           || a == ANI_PUSH || a == ANI_BREATHE;
}

// Player 1's frame (after every entity's update): the pose, then Y
static void AmyThrowFrame(EntityPlayer *p, bool32 transformed)
{
    const AmyData *d = &g_cur->more.amy;
    if (g_shotCooldown > 0)
        g_shotCooldown--;
    if (g_amyPose.left > 0) {
        bool32 still = p->onGround && !Hurt(p) && Abs(p->groundVel) < 0x10000
                       && (p->state == Player_State_Ground_ || p->state == Player_State_LookUp_ || p->state == Player_State_Crouch_);
        if (still) {
            RSDK.ProcessAnimation(&g_amyPose.anim);
            p->animator = g_amyPose.anim;
        }
        if (g_amyPose.pending && (!still || g_amyPose.anim.frameID >= 1)) { // (the hammer leaves on the pose's frame 1)
            g_amyPose.pending = false;
            Throw(p, false, 1, 0);
        }
        if (!still || --g_amyPose.left == 0) {
            g_amyPose.left = 0;
            if (Showing(p, g_amyThrowAnim))
                RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
        }
        return;
    }
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    bool32 gate     = AMY_THROW_GATE == AMY_THROW_ALWAYS || p->superState == SUPERSTATE_SUPER;
    if (!gate || !key || !key->press || g_shotCooldown > 0 || p->stateInput != Player_Input_P1_ || !SceneInfo->timeEnabled || transformed
        || Hurt(p) || !g_shotOn)
        return;
    int32 a = p->animator.animationID;
    if (p->state == Amy_State_HammerDash || p->aniFrames != g_extraFrames)
        return; // (no throw in the dash)
    if (p->onGround && AmyStanding(a) && g_amyThrowAnim >= 0) {
        g_amyPose.left    = d->throwPose;
        g_amyPose.pending = true;
        memset(&g_amyPose.anim, 0, sizeof(g_amyPose.anim));
        RSDK.SetSpriteAnimation(g_extraFrames, g_amyThrowAnim, &g_amyPose.anim, true, 0);
        p->animator    = g_amyPose.anim;
        g_shotCooldown = g_cur->shot.cooldown;
    }
    else if (AmyMoving(a)) {
        Throw(p, false, 1, 0);
    }
}

// ------------------------------------------------------------------------------------------------ every frame
// Each Amy (after every entity's update): her body numbers, no Peel Out or Outta Here, a dash something else ended
static void AmyKeep(EntityPlayer *p)
{
    const AmyData *d = &g_cur->more.amy;
    p->outtaHereTimer = 0;
    p->statePeelout   = NULL;
    if (!p->isChibi) {
        p->jumpOffset = d->jumpOffset << 16;
        p->sensorY    = d->sensorY << 16;
    }
    AmyMove *a = AmyOf(p);
    if (a && a->dashing && p->state != Amy_State_HammerDash) { // (a spring, a hit, an object took her)
        a->dashing = false;
        a->dash    = 0;
        if (Showing(p, g_amyDashAnim))
            RSDK.SetSpriteAnimation(g_extraFrames, p->onGround ? ANI_WALK : ANI_AIR_WALK, &p->animator, true, 0);
    }
}

static void AmyUpdate(EntityPlayer *p1, bool32 transformed)
{
    if (!g_amyOn)
        return;
    EachPlayer(AmyKeep);
    if (IsExtra(p1))
        AmyThrowFrame(p1, transformed);
}

// ------------------------------------------------------------------------------------------------ Super Amy
// Origins' Super Amy palette (the exe's rows; her five pinks): row 0 is her own, then 5..30 every 5; the cycle steps 5
// every 7 frames up to 50 and wraps to 5 (35..50 are rows 25..10 again); turning back fades down 10 every 8 frames.
// Written into her slots in bank 0 after everything else this frame (the game's Super blend leaves her colours as they
// are: ManiaHud.h GlowsWhenSuper is false for her).
#define AMY_PINKS (5)
static const uint8 AMY_PINK_SLOTS[AMY_PINKS] = { 65, 64, 90, 88, 66 }; // (Origins' 75-79 in her Mania slots)
static const color AMY_SUPER_ROWS[7][AMY_PINKS] = {
    { 0xB44890, 0xFC6CFC, 0xFCB4FC, 0x6C0048, 0x90246C }, // 0: her own
    { 0xD468B0, 0xFC8CFC, 0xFCD4FC, 0x8C2068, 0xB0448C }, // 5
    { 0xF488D0, 0xFCACFC, 0xFCE4FC, 0xAC4088, 0xD064AC }, // 10
    { 0xF4A8F0, 0xFCCCFC, 0xFCE4FC, 0xCC60A8, 0xF084CC }, // 15
    { 0xF4C8F0, 0xFCECFC, 0xFCE4FC, 0xEC80C8, 0xF0A4EC }, // 20
    { 0xF4E8F0, 0xFCECFC, 0xFCE4FC, 0xECA0E8, 0xF0C4EC }, // 25
    { 0xF4E8F0, 0xFCECFC, 0xFCE4FC, 0xECC0E8, 0xF0E4EC }, // 30
};
static struct {
    int32 step;   // the cycle's place: 0 (her own), 5..50
    int32 timer;  // frames to its next step
    int32 wrote;  // the row last written (-1: none since the stage loaded)
} g_amySuper;

static int32 AmySuperRow(int32 step) { return step <= 30 ? step / 5 : (60 - step) / 5; }

static void AmyLateUpdate(void *data)
{
    (void)data;
    if (!g_amyOn || !g_active)
        return;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p))
        return;
    bool32 super = p->superState == SUPERSTATE_SUPER || p->superState == SUPERSTATE_FADEIN;
    if (super) {
        if (--g_amySuper.timer <= 0) {
            g_amySuper.timer = 7;
            g_amySuper.step += 5;
            if (g_amySuper.step > 50)
                g_amySuper.step = 5;
        }
    }
    else if (g_amySuper.step > 0) { // fading back: 10 down every 8 frames, on the row it shows
        if (g_amySuper.step > 30)
            g_amySuper.step = 60 - g_amySuper.step;
        if (--g_amySuper.timer <= 0) {
            g_amySuper.timer = 8;
            g_amySuper.step  = g_amySuper.step > 10 ? g_amySuper.step - 10 : 0;
        }
    }
    else if (g_amySuper.wrote <= 0) {
        g_amySuper.timer = 0;
        return; // (her own colours: the mod's usual handling)
    }
    int32 row = AmySuperRow(g_amySuper.step);
    for (int32 c = 0; c < AMY_PINKS; ++c) RSDK.SetPaletteEntry(0, AMY_PINK_SLOTS[c], AMY_SUPER_ROWS[row][c]);
    g_amySuper.wrote = row;
}

// ------------------------------------------------------------------------------------------------ stage load, link
static void AmyStageLoad(void)
{
    memset(g_amy, 0, sizeof(g_amy));
    memset(&g_amyPose, 0, sizeof(g_amyPose));
    memset(&g_amySuper, 0, sizeof(g_amySuper));
    g_amySuper.wrote = -1;
    g_amyOn          = false;
    if (!g_active || !g_cur || !g_cur->more.amy.on)
        return;
    if (!Player_HandleAirMovement_ || !Player_HandleGroundRotation_ || !Player_Gravity_False_ || !Player_State_Ground_ || !Player_State_LookUp_
        || !Player_State_Crouch_) {
        RSDK.PrintLog(PRINT_ERROR, LOG_TAG "amy: the game's Player functions weren't found: no hammer");
        return;
    }
    g_amyJumpAnim  = HasAnim(g_cur->animBase + 0);
    g_amyDashAnim  = HasAnim(g_cur->animBase + 1);
    g_amyThrowAnim = HasAnim(g_cur->animBase + 2);
    uint16 jr = RSDK.FindSpriteAnimation(g_extraFrames, "Hammer Jump Reach");
    uint16 dr = RSDK.FindSpriteAnimation(g_extraFrames, "Hammer Dash Reach");
    g_amyJumpReach = jr < 0x100 ? HasAnim(jr) : -1;
    g_amyDashReach = dr < 0x100 ? HasAnim(dr) : -1;
    g_amySfxJump   = RSDK.GetSfx(AMY_SFX_JUMP);
    g_amySfxCharge = RSDK.GetSfx(AMY_SFX_CHARGE);
    g_amySfxDash   = RSDK.GetSfx(AMY_SFX_DASH);
    g_amySfxHit    = RSDK.GetSfx(AMY_SFX_HIT);
    g_amyOn        = g_amyJumpAnim >= 0;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "amy: hammer jump %d, dash %d, throw %d (shot %d, gate %s), reach %d / %d, sounds %d %d %d %d",
                  g_amyJumpAnim, g_amyDashAnim, g_amyThrowAnim, g_shotOn, AMY_THROW_GATE == AMY_THROW_SUPER ? "Super" : "always",
                  g_amyJumpReach, g_amyDashReach, g_amySfxJump, g_amySfxCharge, g_amySfxDash, g_amySfxHit);
}

static void LinkAmy(void)
{
    bool32 any = false;
    for (int32 i = 0; i < g_extraCount; ++i) any |= g_extras[i].more.amy.on;
    if (!any)
        return;
    Player_HandleAirMovement_    = Mod.GetPublicFunction(NULL, "Player_HandleAirMovement");
    Player_HandleGroundRotation_ = Mod.GetPublicFunction(NULL, "Player_HandleGroundRotation");
    Player_Gravity_False_        = Mod.GetPublicFunction(NULL, "Player_Gravity_False");
    if (!Player_State_Ground_)
        Player_State_Ground_ = Mod.GetPublicFunction(NULL, "Player_State_Ground");
    if (!Player_State_LookUp_)
        Player_State_LookUp_ = Mod.GetPublicFunction(NULL, "Player_State_LookUp");
    if (!Player_State_Crouch_)
        Player_State_Crouch_ = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
    Mod.AddModCallback(MODCB_ONLATEUPDATE, AmyLateUpdate); // (after OnLateUpdate and the HUD's: registered last)
    if (Player_State_Ground_)
        Mod.RegisterStateHook(Player_State_Ground_, AmyGroundBefore, true); // (her charged landing: the Hammer Dash)
}

#endif // MANIA_AMY_H
