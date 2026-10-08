// NiGHTS' free flight, Drill Dash and Paraloop in S3&K (abilities.py free_flight; tools/free_flight.py is the Sonic 1/2
// and CD port, native/mania/src/ManiaNights.h Mania's: the same rules and numbers). Included by NoSwapS3K.cpp after
// EccoSwim.h, whose free swim it takes into the air:
// - A jump press in mid-air (the air state, from a jump, a spring or a fall; not the frame he left the ground), or Y in
//   mid-air, starts the flight while the meter has anything left. The d-pad steers a heading (degrees, 0 right,
//   counterclockwise) toward its direction at flyTurn degrees a frame while the speed builds by flyAccel up to flySpeed;
//   nothing held, it drains by flyDrag. His velocity is the heading times the speed, set after the game's update (the
//   air state's gravity taken off in advance). Another jump press lets go (he falls, and may fly again); landing, a hit,
//   an object holding him or any state but the air one ends it.
// - The meter (flyMeter frames): drains flyDrain a frame in flight (not underwater), refills flyRefill a frame on the
//   ground, every ring adds flyRing. Empty, he floats down (falling flySink a frame at most) until he lands. Drawn in
//   the icon pass (NoSwapS3K.cpp shots::PlayerDraw) at the top middle while it isn't full or he flies.
// - Drawn from slot 42 (ANI_EXTRA(1), "Flight"): 0-7 the paraloop's 8 headings (0 right, counterclockwise), mirrored by
//   his facing (facing left, heading d is frame (4 - d) & 7 flipped); underwater flying level, 8.. the swim cycle.
// - Y in flight: the Drill Dash, drillFrames at drillSpeed along the heading (slot 41, ANI_EXTRA(0): 4 blur frames, 2
//   game frames each), an attack (shown to the game as the jump), untouchable; then drillCooldown frames; it costs
//   drillCost of the meter. Walls that break for Knuckles break for it (AsKnuckles).
// - The Paraloop: every loopEvery frames in flight his position is a sample (the last loopPoints kept); back within
//   loopClose px of one at least LOOP_AGE samples old, round a loop at least loopMin px wide and tall, everything whose
//   position is inside that polygon (even-odd) is touched for loopHit frames (Hook_Touch: LoopTouch, as the Screen
//   Nuke's), while he shows the game the jump: badniks break, monitors open, bosses take the hit.

namespace nights {
constexpr double PI = 3.14159265358979323846;
constexpr int MAX_POINTS = 32, LOOP_AGE = 4, DRILL_FRAMES = 4;
constexpr int METER_W = 64, METER_H = 4, METER_TOP = 10;
enum { NONE = 0, FLY = 1, FLOAT = 2, FALL = 3 };
struct State {
    int mode = NONE;
    double heading = 0;  // degrees
    int speed = 0;       // 16.16
    int meter = -1;      // frames of flight left (-1: full, set at the first update)
    int drill = 0;       // the drill and its rest, counting down
    int cycle = 0;       // the swim cycle's timer (256ths of a frame)
    int air = 0;         // frames in the air state
    int rings = -1;      // the ring count last frame
    int sampleT = 0, count = 0;
    int sx[MAX_POINTS], sy[MAX_POINTS];  // the samples, oldest first (px)
    int kill = 0;                        // the loop's hit: frames left
    int kn = 0;
    int kx[MAX_POINTS + 1], ky[MAX_POINTS + 1];  // the loop (px)
    int bx0 = 0, bx1 = 0, by0 = 0, by1 = 0;
};
static State g{};

static bool On() { return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.freeFlight; }
static void Reset() { g = State(); }
static bool Drilling() { return On() && g.mode == FLY && g.drill > Extra(g_character).abilities.drillCooldown; }

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

static void Leave(EntityPlayer* p, int mode, bool air) {  // out of the flight: his floating frames in the air
    g.mode = mode;
    g.drill = 0;
    if (air)
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_FALL, &p->animator, false, 0);
}

static bool Inside(int x, int y) {  // even-odd over the loop's edges
    bool in = false;
    for (int i = 0, j = g.kn - 1; i < g.kn; j = i++) {
        if ((g.ky[i] > y) != (g.ky[j] > y)) {
            long long xi = g.kx[i] + (long long)(y - g.ky[i]) * (g.kx[j] - g.kx[i]) / (g.ky[j] - g.ky[i]);
            if (x < xi)
                in = !in;
        }
    }
    return in;
}

// Hook_Touch (Player_CheckBadnikTouch): while the loop's hit lasts, anything inside it is touched
static bool LoopTouch(EntityPlayer* p, Entity* e) {
    if (!On() || g.kill <= 0 || g.mode != FLY || !p || !e || RSDK->GetEntitySlot(p) != 0)  // (in flight: his attack)
        return false;
    int x = e->position.x >> 16, y = e->position.y >> 16;
    if (x < g.bx0 || x > g.bx1 || y < g.by0 || y > g.by1 || !Inside(x, y))
        return false;
    static int logs = 0;
    if (shots::Budget(logs))
        Log("paraloop: touches %s (slot %d)", shots::ClassName(e->classID), RSDK->GetEntitySlot(e));
    return true;
}

// A sample (every loopEvery frames in flight), and the loop when the path closes on itself
static void Sample(EntityPlayer* p, const ExtraAbilities& c) {
    int n = std::clamp(c.loopPoints, 6, MAX_POINTS);
    if (++g.sampleT < std::max(1, c.loopEvery))
        return;
    g.sampleT = 0;
    for (int k = 0; k + 1 < n; k++) {
        g.sx[k] = g.sx[k + 1];
        g.sy[k] = g.sy[k + 1];
    }
    int x = p->position.x >> 16, y = p->position.y >> 16;
    g.sx[n - 1] = x;
    g.sy[n - 1] = y;
    g.count = std::min(g.count + 1, n);
    int m = -1;
    for (int k = n - g.count; k <= n - 1 - LOOP_AGE && m < 0; k++)
        if (std::abs(g.sx[k] - x) < c.loopClose && std::abs(g.sy[k] - y) < c.loopClose)
            m = k;
    if (m < 0)
        return;
    int x0 = x, x1 = x, y0 = y, y1 = y;
    for (int k = m; k < n; k++) {
        x0 = std::min(x0, g.sx[k]);
        x1 = std::max(x1, g.sx[k]);
        y0 = std::min(y0, g.sy[k]);
        y1 = std::max(y1, g.sy[k]);
    }
    if (x1 - x0 < c.loopMin || y1 - y0 < c.loopMin)
        return;
    g.kn = 0;
    for (int k = m; k < n; k++) {
        g.kx[g.kn] = g.sx[k];
        g.ky[g.kn++] = g.sy[k];
    }
    g.bx0 = x0;
    g.bx1 = x1;
    g.by0 = y0;
    g.by1 = y1;
    g.kill = std::max(1, c.loopHit);
    g.count = 0;
    Log("paraloop: a loop of %d samples, %dx%d px", g.kn, x1 - x0, y1 - y0);
}

// Each frame after the game's update (Abilities)
static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!On())
        return;
    int full = std::max(1, c.flyMeter);
    if (g.meter < 0)
        g.meter = full;
    if (g.kill > 0)
        g.kill--;
    if (g.drill > 0)
        g.drill--;
    int32 rings = *(int32*)((uint8*)p + shots::RINGS);
    if (g.rings >= 0 && rings > g.rings)  // every ring he gets tops the meter up
        g.meter = std::min(full, g.meter + (rings - g.rings) * c.flyRing);
    g.rings = rings;
    bool airState = g_playerStateAir && (void*)p->state.state == g_playerStateAir;
    bool free = airState && !Hurt(p) && !Held(p);
    bool water = InWater(p);  // (the underwater field, not the gravity)
    bool y = YPressed(p);
    int wasAir = g.air;
    g.air = airState ? std::min(g.air + 1, 100) : 0;

    if (!air) {  // on the ground: no flight, the meter fills up
        if (g.mode != NONE)
            Leave(p, NONE, false);
        g.meter = std::min(full, g.meter + c.flyRefill);
        g.count = 0;
        return;
    }
    if (g.mode == FLY) {
        if (!free)
            Leave(p, NONE, false);
        else if (p->jumpPress)  // jump again: he lets go
            Leave(p, FALL, true);
        else if (g.meter <= 0 && !water)  // empty: he floats down
            Leave(p, FLOAT, true);
    } else if (g.mode != FLOAT && free && wasAir > 0 && (p->jumpPress || y) && g.meter > 0) {
        g.mode = FLY;  // the flight: the heading from where he's going (or faces)
        if (p->velocity.x || p->velocity.y)
            g.heading = std::atan2(-(double)p->velocity.y, (double)p->velocity.x) * 180 / PI;
        else
            g.heading = (p->direction & 1) ? 180 : 0;
        g.speed = std::min((int)std::sqrt((double)p->velocity.x * p->velocity.x + (double)p->velocity.y * p->velocity.y),
                           c.flySpeed);
        g.count = 0;
        g.sampleT = 0;
        Log("flight: on (meter %d)", g.meter);
    }
    if (g.mode == FLOAT) {  // the meter's empty: a slow fall (the air state's gravity taken off in advance)
        if (!free) {
            g.mode = NONE;
        } else if (p->velocity.y > c.flySink - Gravity(p)) {
            p->velocity.y = c.flySink - Gravity(p);
        }
    }
    if (g.mode != FLY)
        return;
    if (!water)
        g.meter = std::max(0, g.meter - c.flyDrain);
    if (y && g.drill == 0 && g.meter > 0) {  // the Drill Dash
        g.drill = c.drillFrames + c.drillCooldown;
        g.meter = std::max(0, g.meter - c.drillCost);
        if (c.drillSound)
            PlaySound(c.drillSound);
    }
    int ix = p->right ? 1 : p->left ? -1 : 0, iy = p->down ? 1 : p->up ? -1 : 0;
    if (ix || iy) {  // turn toward the d-pad's direction, and speed up
        double target = std::atan2(-(double)iy, (double)ix) * 180 / PI;
        double diff = std::fmod(target - g.heading + 540.0, 360.0) - 180.0;
        double turn = c.flyTurn > 0 ? c.flyTurn : 360;
        g.heading += std::max(-turn, std::min(turn, diff));
        g.speed = std::min(g.speed + c.flyAccel, c.flySpeed);
    } else {
        g.speed = std::max(g.speed - c.flyDrag, 0);
    }
    g.heading = std::fmod(g.heading + 360.0, 360.0);
    bool drilling = g.drill > c.drillCooldown;
    int speed = drilling ? c.drillSpeed : g.speed;
    double r = g.heading * PI / 180;
    p->velocity.x = (int)(std::cos(r) * speed);
    p->velocity.y = (int)(-std::sin(r) * speed) - Gravity(p);  // (the air state's gravity taken off in advance)
    p->groundVel = p->velocity.x;
    NoJumpCap(p);
    double cx = std::cos(r);
    if (cx > 0.125)  // his facing: the way he's going across
        p->direction = 0;
    else if (cx < -0.125)
        p->direction = 1;
    int d = ((int)std::floor(g.heading / 45.0 + 0.5) % 8 + 8) % 8;
    if (p->direction & 1)
        d = (4 - d) & 7;
    if (drilling) {
        int t = c.drillFrames + c.drillCooldown - g.drill;
        Show(p, ANI_EXTRA(0), (t / 2) % DRILL_FRAMES, true);
    } else {
        int frame = d;
        if (water && d == 0) {  // underwater, level: the swim cycle, faster the faster he goes
            int cyc = std::max(1, c.flySwimFrames), ticks = std::max(1, c.flySwimTicks);
            g.cycle = (g.cycle + 64 + (int)((int64_t)192 * g.speed / std::max(1, c.flySpeed))) % (256 * ticks * cyc);
            frame = 8 + g.cycle / (256 * ticks);
        }
        Show(p, ANI_EXTRA(1), frame, false);
    }
    if ((drilling || g.kill > 0) && g_blinkOffset >= 0) {  // untouchable (without the blink's own flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    Sample(p, c);
    if (g.kill > 0)  // the loop's hit: he shows the game the jump (an attack) while it lasts
        p->animator.animationID = ANI_JUMP;
}

// The icon pass (shots::QueueIcon / PlayerDraw): the meter at the top middle while it isn't full or he flies
static bool Pass() {
    if (!On())
        return false;
    const ExtraAbilities& c = Extra(g_character).abilities;
    return g.mode == FLY || (g.meter >= 0 && g.meter < std::max(1, c.flyMeter));
}
static void Draw() {
    if (!Pass() || shots::Showing("TitleCard") || shots::Showing("ActClear"))
        return;
    auto* p = (EntityPlayer*)RSDK->GetEntity(0);
    if (!p || Held(p))
        return;
    shots::ScreenView v{};
    if (!shots::Screen(&v))
        return;
    const ExtraAbilities& c = Extra(g_character).abilities;
    int full = std::max(1, c.flyMeter);
    int x = v.w / 2 - METER_W / 2;
    RSDK->DrawRect(x - 2, METER_TOP, METER_W + 4, METER_H + 4, 0x000000, shots::ICON_ALPHA, shots::ICON_INK_ALPHA, true);
    int w = METER_W * std::max(0, g.meter) / full;
    if (w > 0)
        RSDK->DrawRect(x, METER_TOP + 2, w, METER_H, g.meter < full / 4 ? 0xE52E27 : 0xFFFF00, 0xFF, 0, true);
}
}  // namespace nights
