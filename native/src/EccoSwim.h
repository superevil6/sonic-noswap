// Ecco's free swim in S3&K (abilities.py free_swim; included by NoSwapS3K.cpp before Abilities). The user's design
// (2026-09-30, "painful but beatable" on land, a god in water):
// - Underwater (the player's underwater field, InWater) he swims anywhere: a heading (degrees, 0 right,
//   counterclockwise) turns toward the d-pad's direction at swimTurn degrees a frame while the speed builds by swimAccel up
//   to swimSpeed; nothing held, it drains by swimDrag. His velocity is the heading times the speed, set after the game's
//   update (the air state's gravity taken off in advance). Resting on the floor, anything held lifts him off again.
// - Drawn with slot 41 ("Swim", ANI_EXTRA(0)): swimDirs directions x swimCycle frames, direction-major (direction 0 facing
//   right, counterclockwise in equal steps), never flipped (p->direction 0 while he swims); the cycle runs faster the
//   faster he goes.
// - Y: the charge ram, ramFrames at ramSpeed along the heading (slot 42, "Charge": swimDirs x ramCycle), an
//   attack (shown to the game as the jump, so badniks break and bosses take the hit); then ramCooldown frames.
// - Swimming up out of the surface: a leap. The game's own air physics carry him; the arc shows slot 43 ("Leap", ANI_EXTRA(2):
//   leapFrames frames over leapTicks each) until he lands or is back in the water.
// - A hit, an object holding him, or any state but the plain air / ground ones: no swim (the game's own).

namespace swim {
constexpr double PI = 3.14159265358979323846;
struct State {
    bool swimming = false;  // last frame in the swim
    bool leaping = false;
    double heading = 0;     // degrees
    int speed = 0;          // 16.16
    int charge = 0;         // frames of the charge left
    int cooldown = 0;
    int cycle = 0;          // the swim cycle's timer (256ths of a frame)
    int leapT = 0;
    void* groundState = nullptr;  // the plain ground state (seen while he flops about)
};
static State g{};

static bool On() { return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.freeSwim; }
static bool Underwater(EntityPlayer* p) { return InWater(p); }  // (the underwater field, not the gravity)

static void ToAir(EntityPlayer* p) {
    p->onGround = false;
    p->angle = 0;
    p->collisionMode = 0;
    p->state.state = (void(__fastcall*)())g_playerStateAir;
}

static int DirIndex(double heading, int dirs) {
    double step = 360.0 / dirs;
    int k = (int)std::floor(heading / step + 0.5);
    return ((k % dirs) + dirs) % dirs;
}

static void Show(EntityPlayer* p, int anim, int frame, bool attacking) {
    Animator probe{};
    RSDK->SetSpriteAnimation(g_extraFrames, anim, &probe, true, 0);
    if (p->animator.frames != probe.frames)
        RSDK->SetSpriteAnimation(g_extraFrames, anim, &p->animator, true, 0);
    int count = std::max(1, (int)p->animator.frameCount);
    p->animator.frameID = std::min(std::max(frame, 0), count - 1);
    p->animator.timer = 0;
    p->animator.speed = 0;
    if (attacking)
        p->animator.animationID = ANI_JUMP;
}

static void Reset() { g = State(); }
// The charge ram going on (or just ended: a wall it hit stops him, and a wall's update may run after his): walls that
// break for Knuckles break for it (NoSwapS3K.cpp AsKnuckles; the user hit Launch Base 2's walls, 2026-09-30)
static int g_ramGrace = 0;
static bool Ramming() { return On() && (g.charge > 0 || g_ramGrace > 0); }

// Each frame after the game's update (Abilities)
static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!On())
        return;
    if (g.cooldown > 0)
        g.cooldown--;
    bool airState = g_playerStateAir && (void*)p->state.state == g_playerStateAir;
    int a = p->animator.animationID;
    if (!air && (a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1)))
        g.groundState = (void*)p->state.state;
    bool groundState = !air && g.groundState && (void*)p->state.state == g.groundState;
    bool free = !Hurt(p) && !Held(p) && (airState || groundState);
    bool water = Underwater(p);

    // out of the water, going up: the leap (the game's air physics), its frames until he lands or splashes back
    if (!water) {
        if (g.swimming && air && airState && p->velocity.y < 0) {
            g.leaping = true;
            g.leapT = 0;
            p->direction = std::cos(g.heading * PI / 180) < 0 ? 1 : 0;
        }
        g.swimming = false;
        g.charge = 0;
        if (g.leaping) {
            if (!air || !airState || Hurt(p)) {
                g.leaping = false;
            } else {
                int frames = std::max(1, c.leapFrames);
                Show(p, ANI_EXTRA(2), std::min(g.leapT++ / std::max(1, c.leapTicks), frames - 1), false);
            }
        }
        return;
    }
    g.leaping = false;
    if (!free) {
        g.swimming = false;
        g.charge = 0;
        return;
    }
    int ix = p->right ? 1 : p->left ? -1 : 0, iy = p->down ? 1 : p->up ? -1 : 0;
    if (!g.swimming) {  // into the swim: the heading from where he's going (or faces)
        if (p->velocity.x || p->velocity.y)
            g.heading = std::atan2(-(double)p->velocity.y, (double)p->velocity.x) * 180 / PI;
        else
            g.heading = (p->direction & 1) ? 180 : 0;
        g.speed = std::min((int)std::sqrt((double)p->velocity.x * p->velocity.x + (double)p->velocity.y * p->velocity.y),
                           c.swimSpeed);
    }
    if (!air) {  // resting on the floor: anything held (or the charge) lifts him off
        if (!ix && !iy && !YPressed(p) && g.charge == 0) {
            g.swimming = false;
            return;
        }
        ToAir(p);
        p->position.y -= 2 << 16;
    }
    g.swimming = true;
    if (YPressed(p) && g.charge == 0 && g.cooldown == 0) {
        g.charge = c.ramFrames;
        g.cooldown = c.ramFrames + c.ramCooldown;
        if (c.ramSound)
            PlaySound(c.ramSound);
    }
    if (ix || iy) {  // turn toward the d-pad's direction, and speed up
        double target = std::atan2(-(double)iy, (double)ix) * 180 / PI;
        double diff = std::fmod(target - g.heading + 540.0, 360.0) - 180.0;
        double turn = c.swimTurn > 0 ? c.swimTurn : 360;
        g.heading += std::max(-turn, std::min(turn, diff));
        g.speed = std::min(g.speed + c.swimAccel, c.swimSpeed);
    } else {
        g.speed = std::max(g.speed - c.swimDrag, 0);
    }
    g.heading = std::fmod(g.heading + 360.0, 360.0);
    int speed = g.speed;
    if (g_ramGrace > 0)
        g_ramGrace--;
    if (g.charge > 0) {
        g.charge--;
        g_ramGrace = 4;
        speed = c.ramSpeed;
    }
    double r = g.heading * PI / 180;
    p->velocity.x = (int)(std::cos(r) * speed);
    p->velocity.y = (int)(-std::sin(r) * speed) - Gravity(p);  // (the air state's gravity taken off in advance)
    p->groundVel = p->velocity.x;
    p->direction = 0;  // (the frames are drawn every way round: never flipped)
    int dirs = std::max(1, c.swimDirs), k = DirIndex(g.heading, dirs);
    if (c.ramCycle > 0 && g.charge > 0) {
        int t = c.ramFrames - g.charge;
        Show(p, ANI_EXTRA(1), k * c.ramCycle + (t / 2) % c.ramCycle, true);
        if (g_blinkOffset >= 0) {  // (untouchable while ramming, without the flicker)
            int& blink = *(int*)((char*)p + g_blinkOffset);
            if (blink < 3)
                blink = 3;
        }
    } else {
        int cyc = std::max(1, c.swimCycle);
        g.cycle += 64 + (int)((int64_t)192 * g.speed / std::max(1, c.swimSpeed));  // (faster strokes, faster swim)
        Show(p, ANI_EXTRA(0), k * cyc + (g.cycle / (256 * std::max(1, c.swimTicks))) % cyc, false);
    }
}
}  // namespace swim
