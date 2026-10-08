// The Spin Dash-only gimmicks, for extras that can't Spin Dash (extras.py "no_roll": Gamma, Omega, Mega Man, Sparkster,
// Headdy, John Morris, Ecco; or whose crouch + jump is their Slide instead, abilities.py ground_slide: Ray Poward, Mega
// Man). Without this they soft-lock where the way on opens only for a Spin Dash (Marble Garden's dash wheels). While
// such an object updates, player 1 is shown to it as Spin Dashing (the AsKnuckles way: only for that update, put back
// straight after), so the object's own code decides and acts as it does for Sonic. Included by NoSwapS3K.cpp after
// AsKnuckles; Hook_RegisterObject wraps the updates (spin::Wrap).
//
// From this build's exe (objdump on .didata, never run); the player's animator.animationID is +0x144 (3K_Players:
// 4 Crouch, 20 Spindash, 21 Push, 70 Dropdash), its state +0xF0, abilityTimer +0x1B4, superState +0x1F4:
//   DashWheel (Marble Garden 1/2's dash triggers, sprites 3K_MGZ/DashTrigger.bin): its update 0x140168640 (the thunk to
//     0x140169300, its state machine at +0xF8) runs State_Main 0x140168d70: for each player touching its box (its own
//     side, on the ground) with animationID == 20 (cmp word [rsi+0x144], 0x14 at 0x140168e79) it toggles (+0x70) and
//     spins for 60 frames (+0xE8); a player rolling into it (State_Roll 0x1401eba50) is stood up (State_Ground) and
//     pushed off. On its top, animationID 20 or 70 (or the spin running) bounces the player away at 7 px per frame.
//     The extra Spin Dashes there by pushing into it from the side for PUSH_FRAMES (on the ground, holding toward it,
//     stalled against it), or at once with a dash move running into it (the Slide: g_ab.puddle; Ecco's charge ram).
//   DashLift (Lava Reef 1's Spin Dash lifts, Mania's object): its update 0x140153af0 (Platform's, which runs its state
//     machine) runs State_Main 0x140154110: a player standing on it (+0xC4) with animationID == 20 (0x1401541cd) moves
//     it, at a speed from abilityTimer while its state is State_Spindash (0x1401ebb40, lea r14 at 0x140154182; else
//     from groundVel), facing left down, right up. The extra crouching on it is shown Spin Dashing, abilityTimer 0 (the
//     slowest Spin Dash, about 1 px per frame).
// Each is wrapped only when its update is that function and the checked bytes are there.
namespace spin {
constexpr int ANI_SPINDASH = 20;
constexpr int ABILITY_TIMER = 0x1B4;
constexpr int PUSH_FRAMES = 60;   // pushing into a dash wheel this long counts as a Spin Dash (about a second)
constexpr int WHEEL_NEAR = 46;    // px: the wheel's touch box (33) plus a player's half width (10), 3 to spare
constexpr int LIFT_NEAR = 40;     // px: a lift's width either side (the lift itself checks who stands on it)
constexpr uintptr_t WHEEL_UPDATE = 0x140168640, WHEEL_CHECK = 0x140168e79;
constexpr uintptr_t LIFT_UPDATE = 0x140153af0, LIFT_CHECK = 0x1401541cd, LIFT_SPINDASH_LEA = 0x140154182;
constexpr uintptr_t STATE_SPINDASH = 0x1401ebb40;
static const uint8 WHEEL_CHECK_BYTES[] = {0x66, 0x83, 0xbe, 0x44, 0x01, 0x00, 0x00, 0x14};  // cmp word [rsi+0x144], 20
static const uint8 LIFT_UPDATE_BYTES[] = {0x48, 0x8b, 0x05, 0x91, 0xc6, 0xd1, 0x02, 0x48, 0x8b, 0x08};
static const uint8 LIFT_CHECK_BYTES[] = {0x0f, 0xb7, 0x8f, 0x44, 0x01, 0x00, 0x00, 0x66, 0x83, 0xf9, 0x14};
static const uint8 LIFT_SPINDASH_BYTES[] = {0x4c, 0x8d, 0x35, 0xb7, 0x79, 0x09, 0x00};  // lea r14, [State_Spindash]

static UpdateFn g_wheelUpdate = nullptr, g_liftUpdate = nullptr;
static void* g_wheel = nullptr;  // the dash wheel player 1 is pushing into
static int g_push = 0;           // ... for this many frames

// Player 1, if it's an extra that can't Spin Dash
static EntityPlayer* Player1() {
    if (g_character <= 0 || !RSDK)
        return nullptr;
    const ExtraData& e = Extra(g_character);
    if (!e.noRoll && !e.abilities.groundSlide)
        return nullptr;
    return (EntityPlayer*)RSDK->GetEntity(0);
}

static void WheelUpdate(void* arg) {
    int slot = -1;
    Entity* self = CurrentEntity(&slot);
    EntityPlayer* p = self ? Player1() : nullptr;
    bool fake = false;
    if (p) {
        int dx = self->position.x - p->position.x;  // (> 0: the wheel is to the right)
        int dy = p->position.y - self->position.y;
        bool beside = std::abs(dx) <= (WHEEL_NEAR << 16) && dy >= -(56 << 16) && dy <= (24 << 16) && p->onGround;
        bool faces = dx > 0 ? !(p->direction & 1) : (p->direction & 1) != 0;
        bool holds = dx > 0 ? p->right : p->left;
        bool push = beside && holds && faces && std::abs(p->groundVel) < 0x10000;
        if (push) {
            if (g_wheel == self) {
                ++g_push;
            } else {
                g_wheel = self;
                g_push = 1;
            }
        } else if (g_wheel == self) {
            g_push = 0;
        }
        bool dash = (Extra(g_character).abilities.groundSlide && g_ab.puddle > 0) || swim::Ramming();
        fake = (push && g_push >= PUSH_FRAMES) || (beside && faces && dash);
        if (push && g_push == PUSH_FRAMES)
            Log("spin: pushing into a dash wheel counts as a Spin Dash");
    }
    Animator saved;
    if (fake) {
        saved = p->animator;
        p->animator.animationID = ANI_SPINDASH;
    }
    g_wheelUpdate(arg);
    if (fake && p->animator.animationID == ANI_SPINDASH)
        p->animator = saved;
}

static void LiftUpdate(void* arg) {
    int slot = -1;
    Entity* self = CurrentEntity(&slot);
    EntityPlayer* p = self ? Player1() : nullptr;
    bool fake = p && p->onGround && p->animator.animationID == ANI_CROUCH
                && std::abs(self->position.x - p->position.x) <= (LIFT_NEAR << 16);
    Animator saved;
    void(__fastcall * state)() = nullptr;
    int* timer = p ? (int*)((char*)p + ABILITY_TIMER) : nullptr;
    int timerWas = 0;
    if (fake) {
        saved = p->animator;
        state = p->state.state;
        timerWas = *timer;
        p->animator.animationID = ANI_SPINDASH;
        p->state.state = (void(__fastcall*)())STATE_SPINDASH;
        *timer = 0;
    }
    g_liftUpdate(arg);
    if (fake) {
        if (p->animator.animationID == ANI_SPINDASH)
            p->animator = saved;
        if ((uintptr_t)p->state.state == STATE_SPINDASH)
            p->state.state = state;
        *timer = timerWas;
    }
}

// Hook_RegisterObject: the dash wheel's and the lift's updates (by name), when they're this build's
static void Wrap(const char* name, void (*&update)(void)) {
    if (!name || !update)
        return;
    bool wheel = strcmp(name, "DashWheel") == 0, lift = strcmp(name, "DashLift") == 0;
    if (!wheel && !lift)
        return;
    bool ok;
    if (wheel) {
        static const uint8 THUNK[] = {0x48, 0x8b, 0x0d};  // mov rcx, [rip+...] (then mov rcx, [rcx]; jmp)
        ok = (uintptr_t)update == WHEEL_UPDATE && Readable((void*)WHEEL_UPDATE, 11)
             && memcmp((void*)WHEEL_UPDATE, THUNK, sizeof(THUNK)) == 0 && ((uint8*)WHEEL_UPDATE)[10] == 0xe9
             && Readable((void*)WHEEL_CHECK, sizeof(WHEEL_CHECK_BYTES))
             && memcmp((void*)WHEEL_CHECK, WHEEL_CHECK_BYTES, sizeof(WHEEL_CHECK_BYTES)) == 0;
    } else {
        ok = (uintptr_t)update == LIFT_UPDATE && Readable((void*)LIFT_UPDATE, sizeof(LIFT_UPDATE_BYTES))
             && memcmp((void*)LIFT_UPDATE, LIFT_UPDATE_BYTES, sizeof(LIFT_UPDATE_BYTES)) == 0
             && Readable((void*)LIFT_CHECK, sizeof(LIFT_CHECK_BYTES))
             && memcmp((void*)LIFT_CHECK, LIFT_CHECK_BYTES, sizeof(LIFT_CHECK_BYTES)) == 0
             && Readable((void*)LIFT_SPINDASH_LEA, sizeof(LIFT_SPINDASH_BYTES))
             && memcmp((void*)LIFT_SPINDASH_LEA, LIFT_SPINDASH_BYTES, sizeof(LIFT_SPINDASH_BYTES)) == 0;
    }
    if (!ok) {
        Log("%s update at %p is DIFFERENT (another game build?): not wrapped (extras without a Spin Dash can't use it)",
            name, (void*)update);
        return;
    }
    if (wheel) {
        g_wheelUpdate = (UpdateFn)update;
        update = (void (*)(void))WheelUpdate;
    } else {
        g_liftUpdate = (UpdateFn)update;
        update = (void (*)(void))LiftUpdate;
    }
    Log("wrapped %s update (extras without a Spin Dash: pushing / crouching counts as one there)", name);
}
}  // namespace spin
