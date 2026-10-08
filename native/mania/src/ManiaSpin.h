// NoSwapMania: the Spin Dash-only gimmicks, for extras that can't Spin Dash (extras.py "no_roll": Gamma, Omega, Mega Man,
// Sparkster, Headdy, John Morris, Ecco; or whose crouch + jump is their Slide instead, abilities.py ground_slide: Ray
// Poward, Mega Man). Without this they soft-lock where the way on opens only for a Spin Dash. The objects (the
// decomp's SonicMania/Objects) read player 1's animation and state; while one of them updates, player 1 is shown to it
// as Spin Dashing (as ManiaWalls.h shows Knuckles' ID to the walls), then put back exactly, so the object's own code
// decides and acts as it does for Sonic:
//   - SDashWheel (Stardust Speedway 1's dash wheels, which open the MGZ-style doors, PlatformControl): its touch box
//     (33 px around its top half) toggles the door for a player whose animationID == ANI_SPINDASH (and launches one
//     Spin Dashing on its top). The extra Spin Dashes there by pushing into the wheel from the side for SPIN_PUSH_FRAMES
//     (on the ground, holding toward it, stalled against it), or at once with a dash move of its own running into it
//     (Mega Man's / Ray's Slide, Ecco's charge ram).
//   - DashLift (Lava Reef 1's Spin Dash lifts): moves for a player standing on it with animationID == ANI_SPINDASH, at
//     a speed from abilityTimer while the state is Player_State_Spindash (down facing left, up facing right). The extra
//     crouching on it is shown Spin Dashing (abilityTimer 0: the slowest Spin Dash, about 1 px per frame).
// Player 1 only, only for such extras; the vanilla characters and the extras that Spin Dash see nothing different.
// Included once, by NoSwapMania.c after ManiaCross.h / ManiaGuest.h (g_gs, CrossAsKnuckles, GuestOf).
#ifndef MANIA_SPIN_H
#define MANIA_SPIN_H

#define SPIN_PUSH_FRAMES (60)  // pushing into a dash wheel this long counts as a Spin Dash (about a second)
#define SPIN_WHEEL_NEAR  (46)  // px: the wheel's touch box (33) plus a player's half width (10), 3 to spare
#define SPIN_LIFT_NEAR   (40)  // px: a lift's width either side (the lift itself checks who stands on it)

static bool32 g_spinWrapped = false;
static Entity *g_spinWheel  = NULL; // the dash wheel player 1 is pushing into
static int32 g_spinPush     = 0;    // ... for this many frames

// Player 1, if it's an extra that can't Spin Dash
static EntityPlayer *SpinPlayer(void)
{
    if (!g_spinWrapped || !g_cur || !Player)
        return NULL;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p) || p->sidekick)
        return NULL;
    const GuestData *g = GuestOf(g_cur->folder);
    return g_cur->noRoll || (g && g->groundSlide) ? p : NULL;
}

// Its own dash move is running (Mega Man's / Ray's Slide, Ecco's charge ram)
static bool32 SpinDashMove(EntityPlayer *p) { return g_gs.slide > 0 || CrossAsKnuckles(p); }

// The dash wheel's update (Mod.RegisterObject); `p` shown Spin Dashing to it when it's ready
static void SpinWheelUpdate(void)
{
    Entity *self    = SceneInfo->entity;
    EntityPlayer *p = SpinPlayer();
    bool32 fake     = false;
    if (p) {
        int32 dx     = self->position.x - p->position.x; // (> 0: the wheel is to the right)
        int32 dy     = p->position.y - self->position.y;
        bool32 near  = Abs(dx) <= (SPIN_WHEEL_NEAR << 16) && dy >= -(56 << 16) && dy <= (24 << 16) && p->onGround;
        bool32 faces = dx > 0 ? !(p->direction & FLIP_X) : (p->direction & FLIP_X) != 0;
        bool32 holds = dx > 0 ? p->right : p->left;
        bool32 push  = near && holds && faces && Abs(p->groundVel) < 0x10000;
        if (push) {
            if (g_spinWheel == self)
                ++g_spinPush;
            else {
                g_spinWheel = self;
                g_spinPush  = 1;
            }
        }
        else if (g_spinWheel == self) {
            g_spinPush = 0;
        }
        fake = (push && g_spinPush >= SPIN_PUSH_FRAMES) || (near && faces && SpinDashMove(p));
    }
    Animator saved;
    if (fake) {
        saved                   = p->animator;
        p->animator.animationID = ANI_SPINDASH;
    }
    Mod.Super(self->classID, SUPER_UPDATE, NULL);
    if (fake && p->animator.animationID == ANI_SPINDASH)
        p->animator = saved; // (unless the wheel set one of its own: its top's bounce sets the jump)
    if (fake) {
        static int32 logs = 0;
        if (logs++ < 20 && g_spinPush == SPIN_PUSH_FRAMES)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "spin: pushing into a dash wheel counts as a Spin Dash");
    }
}

// The Spin Dash lift's update; player 1 crouching near it shown Spin Dashing
static void SpinLiftUpdate(void)
{
    Entity *self    = SceneInfo->entity;
    EntityPlayer *p = SpinPlayer();
    bool32 fake     = p && Player_State_Spindash_ && p->onGround && Abs(self->position.x - p->position.x) <= (SPIN_LIFT_NEAR << 16)
                  && (p->state == Player_State_Crouch_ || p->animator.animationID == ANI_CROUCH);
    Animator saved;
    void (*state)(void) = NULL;
    int32 timer         = 0;
    if (fake) {
        saved                   = p->animator;
        state                   = p->state;
        timer                   = p->abilityTimer;
        p->animator.animationID = ANI_SPINDASH;
        p->state                = Player_State_Spindash_;
        p->abilityTimer         = 0;
    }
    Mod.Super(self->classID, SUPER_UPDATE, NULL);
    if (fake) {
        if (p->animator.animationID == ANI_SPINDASH)
            p->animator = saved;
        if (p->state == Player_State_Spindash_)
            p->state = state;
        p->abilityTimer = timer;
    }
}

static void SpinStageLoad(void *data)
{
    (void)data;
    g_spinWheel = NULL;
    g_spinPush  = 0;
}

static void LinkSpin(void)
{
    bool32 any = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        const GuestData *g = GuestOf(g_extras[i].folder);
        any |= g_extras[i].noRoll || (g && g->groundSlide);
    }
    if (!any)
        return;
    if (!Player_State_Crouch_)
        Player_State_Crouch_ = Mod.GetPublicFunction(NULL, "Player_State_Crouch");
    if (!Player_State_Spindash_)
        Player_State_Spindash_ = Mod.GetPublicFunction(NULL, "Player_State_Spindash");
    Mod.RegisterObject(NULL, NULL, "SDashWheel", 0, 0, 0, SpinWheelUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.RegisterObject(NULL, NULL, "DashLift", 0, 0, 0, SpinLiftUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    Mod.AddModCallback(MODCB_ONSTAGELOAD, SpinStageLoad);
    g_spinWrapped = true;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "spin: dash wheels and Spin Dash lifts wrapped (extras without a Spin Dash)");
}

#endif // MANIA_SPIN_H
