// NoSwapMania: the moves ported with the guest batch (Sticks, Mega Man, Ray Poward, Sparkster; their data:
// ManiaGuestData.h). Sticks' and Ray's Wall Cling is ManiaBatch.h's (Trip's), the shots (boomerang, Buster + Charge Shot,
// aimed autofire, sword wave) NoSwapMania.c's. Each move here is the S3&K DLL's (native/src/NoSwapS3K.cpp: the same
// names, phases and numbers), on Mania's Player, run for player 1 after every entity's update (OnUpdate, after
// ManiaBatch.h's): the velocity set here moves him next frame, after the air state's gravity (taken off in advance).
//   - ground_slide (Ray Poward, Mega Man): down + jump on the ground from a crouch (Hook_GuestInput takes the press: no
//     Spin Dash, no jump), or with slideRunning (Mega Man) out of a run too, slides him forward at puddleSpeed for
//     puddleMove steps, then slowing to a stop, in the Slide frames (ability slot 42: puddleFrames, one per step of
//     puddleTicks game frames). Nothing hurts him meanwhile (the post-hit blink held at 3, no flicker); a jump, a spring,
//     a ledge or a hit ends it; no roll out of it; he can fire during it (the shots' pose shows only standing).
//   - rocket_burst (Sparkster): a jump press in mid-air starts charging while jump is held (drifting to a stop, falling at
//     rocketSink at most; the attack animation's frame 0, flashing with frame 1 once charged: rocketCharge frames).
//     Letting go fires it where the d-pad points (8 ways) at rocketSpeed (rocketDiag per axis diagonally), gravity off,
//     for rocketFrames, a wall or a ceiling stopping it bouncing it off (a ricochet), in the Rocket Dash frame for its
//     angle (2-6); nothing held: the Rocket Spin in place for rocketSpinFrames (frames 7-10 in turn). Let go too soon, it
//     fizzles. An attack throughout (reported to the game as the jump). Landing, a hit, a spring or an object ends it;
//     after the burst he falls with half its speed. Once per jump (the jump ability's press).
// Included once, by NoSwapMania.c (after ManiaBatch.h, whose helpers it uses: BtFrame, BtSfx, BtAir, BtMin / BtMax).
#ifndef MANIA_GUEST_H
#define MANIA_GUEST_H

#define GUEST_ROCKET_CHARGING (1000) // (abilities.py ROCKET_CHARGING)

static struct {
    bool32 trigger;    // GuestJump: this frame's jump press in mid-air is the Rocket Burst's
    bool32 slideStart; // Hook_GuestInput took a slide's jump press this frame
    int32 slide;       // the Slide: frames left
    int32 rocket;      // the Rocket Burst: GUEST_ROCKET_CHARGING.. charging (+ frames held); 1.. flying (frames left)
    Vector2 rocketVel;
    bool32 reset;
} g_gs;

static const GuestData *g_guestCur = NULL; // the extra playing has one of these moves (this stage)
static bool32 g_gsSlide = false, g_gsRocket = false;
static int32 g_gsAnimAttack = -1, g_gsAnimSlide = -1;
static uint16 g_gsSlideSfx = 0xFFFF, g_gsChargeSfx = 0xFFFF, g_gsRocketSfx = 0xFFFF;
static bool32 g_gsInputHooked = false;

// A jump press in mid-air (Hook_JumpAbilitySonic): the Rocket Burst's
static bool32 GuestJump(EntityPlayer *self)
{
    if (!g_gsRocket || RSDK.GetEntitySlot(self) != SLOT_PLAYER1 || g_gs.rocket > 0)
        return false;
    g_gs.trigger = true;
    return true;
}

// Right after player 1's input (Player_Input_P1; registered before no_roll's, so it sees down as pressed): down + jump
// from a crouch (or a run, slideRunning) is the Slide, not a Spin Dash or a jump; no roll out of the slide
static bool32 Hook_GuestInput(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!g_gsSlide || !IsExtra(self) || RSDK.GetEntitySlot(self) != SLOT_PLAYER1 || !self->onGround || Hurt(self))
        return false;
    bool32 crouch  = self->animator.animationID == ANI_CROUCH || self->state == Player_State_Crouch_;
    bool32 running = g_guestCur->slideRunning && self->down && self->groundVel != 0 && g_gs.slide == 0 && self->state == Player_State_Ground_;
    if ((crouch || running) && self->jumpPress) {
        self->down      = false; // (the crouch stands him up; no roll, and no jump)
        self->jumpPress = false;
        g_gs.slideStart = true;
        return false;
    }
    if (g_gs.slide > 0)
        self->down = false; // no roll (or crouch) out of the slide
    return false;
}

// ------------------------------------------------------------------------------------------------ the Slide
static void GuestSlide(EntityPlayer *p, const BatchData *c, bool32 air)
{
    const int32 steps = Clamp(c->puddleSteps, 1, BATCH_PUDDLE_MAX), ticks = c->puddleTicks, total = steps * ticks;
    bool32 start      = g_gs.slideStart;
    g_gs.slideStart   = false;
    bool32 started    = false;
    if (start && !air && !Hurt(p)) {
        g_gs.slide = total;
        started    = true;
        if (p->state == Player_State_Crouch_)
            p->state = Player_State_Ground_; // (the crouch's way back up would hold him there: standing straight into it)
        BtSfx(g_gsSlideSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "slide");
    }
    if (g_gs.slide <= 0)
        return;
    int32 a = p->animator.animationID;
    if (air || Hurt(p) || (!started && (p->state != Player_State_Ground_ || a == ANI_JUMP || a == ANI_CROUCH))) {
        g_gs.slide = 0; // a jump, a roll, a ledge, a spring, a hit
        if (Showing(p, g_gsAnimSlide))
            RSDK.SetSpriteAnimation(p->aniFrames, air ? ANI_AIR_WALK : ANI_IDLE, &p->animator, true, 0);
        return;
    }
    g_gs.slide--;
    int32 step = BtMin((total - g_gs.slide - 1) / ticks, steps - 1);
    Show(p, g_gsAnimSlide, false, false);
    BtFrame(p, c->puddleFrames[step]);
    p->animator.speed = 0;
    int32 dir         = (p->direction & FLIP_X) ? -1 : 1;
    if (step < c->puddleMove) // sliding
        p->groundVel = BtMax(p->groundVel * dir, c->puddleSpeed) * dir;
    else // getting up: slowing to a stop
        p->groundVel -= p->groundVel >> 2;
    if (p->blinkTimer < 3)
        p->blinkTimer = 3; // nothing hurts him (no flicker)
    if (g_gs.slide == 0)   // up again
        RSDK.SetSpriteAnimation(p->aniFrames, ANI_IDLE, &p->animator, true, 0);
}

// ------------------------------------------------------------------------------------------------ the Rocket Burst
static void GuestRocket(EntityPlayer *p, const GuestData *c, bool32 trigger, bool32 air)
{
    Vector2 *v = &g_gs.rocketVel;
    if (trigger) {
        g_gs.rocket = GUEST_ROCKET_CHARGING;
        v->x = v->y = 0;
        Show(p, g_gsAnimAttack, true, true);
        BtSfx(g_gsChargeSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "rocket burst: charging");
    }
    else if (g_gs.rocket > 0) {
        if (!air || !BtAir(p) || p->animator.animationID != ANI_JUMP) { // landed (the game picks his pose), a spring...
            g_gs.rocket = 0;
            return;
        }
        if (g_gs.rocket < GUEST_ROCKET_CHARGING) {
            if (v->x != 0 && p->velocity.x == 0) // a wall stopped it (the game's collision): ricochet
                v->x = -v->x;
            if (v->y < 0 && p->velocity.y == 0) // a ceiling
                v->y = -v->y;
            if (--g_gs.rocket == 0) { // over: he falls from here, with half its speed
                BackToJump(p);
                p->velocity.x = v->x / 2;
                p->velocity.y = v->y / 2;
                return;
            }
        }
        else {
            if (g_gs.rocket < GUEST_ROCKET_CHARGING + 0x4000)
                g_gs.rocket++;
            if (!p->jumpHold) { // let go: fire
                if (g_gs.rocket < GUEST_ROCKET_CHARGING + c->rocketCharge) { // too soon: it fizzles
                    g_gs.rocket = 0;
                    BackToJump(p);
                    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "rocket burst: fizzled");
                    return;
                }
                int32 dx = p->left ? -1 : p->right ? 1 : 0, dy = p->up ? -1 : p->down ? 1 : 0;
                int32 speed = dx && dy ? c->rocketDiag : c->rocketSpeed; // (diagonals: the same speed overall)
                v->x        = dx * speed;
                v->y        = dy * speed;
                g_gs.rocket = BtMax(1, dx || dy ? c->rocketFrames : c->rocketSpinFrames);
                BtSfx(g_gsRocketSfx);
                RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "rocket burst: %d, %d", dx, dy);
            }
        }
    }
    if (g_gs.rocket <= 0)
        return;
    int32 frame = 0;
    if (g_gs.rocket >= GUEST_ROCKET_CHARGING) { // charging: drifting to a stop, falling slowly
        p->velocity.x -= p->velocity.x / 16;
        if (p->velocity.y > c->rocketSink - p->gravityStrength)
            p->velocity.y = c->rocketSink - p->gravityStrength;
        if (g_gs.rocket >= GUEST_ROCKET_CHARGING + c->rocketCharge) // charged: it flashes
            frame = (g_gs.rocket >> 2) & 1;
    }
    else {
        p->velocity.x   = v->x;
        p->velocity.y   = v->y - p->gravityStrength;
        p->applyJumpCap = false;
        if (v->x != 0)
            p->direction = v->x < 0 ? FLIP_X : FLIP_NONE;
        if (v->x == 0 && v->y == 0) // the Rocket Spin: its frames in turn
            frame = 7 + ((c->rocketSpinFrames - g_gs.rocket) / c->rocketSpinTicks) % 4;
        else // the Rocket Dash for its angle: down, down-forward, forward, up-forward, up
            frame = v->y > 0 ? (v->x ? 3 : 2) : v->y < 0 ? (v->x ? 5 : 6) : 4;
    }
    Show(p, g_gsAnimAttack, true, false);
    BtFrame(p, frame);
    p->animator.speed = 0;
}

// ------------------------------------------------------------------------------------------------ per frame, stage, link
// Player 1's frame (OnUpdate, the game running), after the batch's moves and before the shots and the melee
static void GuestUpdate(EntityPlayer *p, bool32 transformed)
{
    (void)transformed;
    bool32 trigger = g_gs.trigger;
    g_gs.trigger   = false;
    if (!g_guestCur || !IsExtra(p))
        return;
    bool32 air = !p->onGround;
    if (Hurt(p) || !Free(p)) { // a hit, or an object holding him: whatever was going on is over
        g_gs.slide = g_gs.rocket = 0;
        g_gs.slideStart = false;
        return;
    }
    if (g_gsSlide)
        GuestSlide(p, &g_cur->more.batch, air);
    if (g_gsRocket)
        GuestRocket(p, g_guestCur, trigger, air);
}

static void GuestStageLoad(void)
{
    memset(&g_gs, 0, sizeof(g_gs));
    g_guestCur = NULL;
    g_gsSlide = g_gsRocket = false;
    if (!g_cur || !g_active)
        return;
    const GuestData *c = GuestOf(g_cur->folder);
    if (!c)
        return;
    g_gsAnimAttack = HasAnim(g_cur->animBase + 0);
    g_gsAnimSlide  = HasAnim(g_cur->animBase + 1);
    g_gsSlide      = c->groundSlide && g_gsAnimSlide >= 0 && Player_State_Ground_ && Player_State_Crouch_ && g_gsInputHooked;
    g_gsRocket     = c->rocketBurst && g_gsAnimAttack >= 0;
    g_gsSlideSfx   = SfxOf(g_cur->more.batch.puddleSound);
    g_gsChargeSfx  = SfxOf(c->rocketChargeSound);
    g_gsRocketSfx  = SfxOf(c->rocketSound);
    if (g_gsSlide || g_gsRocket)
        g_guestCur = c;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: slide %d (running %d), rocket burst %d; anims %d %d", g_cur->name, g_gsSlide, c->slideRunning,
                  g_gsRocket, g_gsAnimAttack, g_gsAnimSlide);
}

// Link (after LinkBatch, before no_roll's input hook: the Slide's input must see down before no_roll lets go of it)
static void LinkGuest(void)
{
    bool32 slide = false;
    for (int32 i = 0; i < g_guestDataCount; ++i) slide |= g_guestData[i].groundSlide != 0;
    if (slide && Player_Input_P1_) {
        if (!Player_State_Ground_)
            Player_State_Ground_ = Mod.GetPublicFunction(NULL, "Player_State_Ground");
        if (!Player_State_Crouch_)
            Player_State_Crouch_ = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
        Mod.RegisterStateHook(Player_Input_P1_, Hook_GuestInput, false);
        g_gsInputHooked = true;
    }
}

#endif // MANIA_GUEST_H
