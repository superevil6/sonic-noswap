// Pulseman's Voltteccer in S3&K (abilities.py voltteccer; tools/voltteccer.py is the Sonic 1/2 port, native/mania/src/
// ManiaVoltteccer.h Mania's: the same rules and numbers). Included by NoSwapS3K.cpp after NightsFlight.h; Update runs
// each frame after the game's update (Abilities), so a velocity set here moves him next frame (the air state's gravity
// taken off in advance).
// - The charge: running on the ground (a walk / jog / run / dash pose, ground speed at least voltRun) for voltCharge
//   frames in a row charges him; slower first, it starts over. Charged: a sound, and his reds flash his own electric
//   blues (the package's charge_palettes charge1, every other 4 frames: a runtime palette effect, the art untouched).
//   Slower than voltKeep on the ground, or a hit, loses it.
// - The launch: a jump press while charged (on the ground the game's jump has just happened; or in mid-air, from the
//   air state) turns him into the ball (ANI_EXTRA(0): frames 0-3 its loop, voltTicks each; 4-5 the small ball as it
//   starts and in its last frames), up-forward at voltSpeed (voltDiag per axis), gravity off, for voltFrames.
// - Rebounds: a wall reverses its speed across; a ceiling, the stage's top edge or a floor its speed up / down (the
//   speed kept); anything that bounces him (a badnik he breaks, a boss, a bumper) reverses that axis too.
// - An attack throughout (shown to the game as the jump) and nothing hurts him (the blink held at 3, no flicker). At
//   the end he pops back out into his jump ball with half its speed; a spring, an object, a hit, death end it at once.

namespace volt {
constexpr int SMALL = 4, LOOP = 4, START_SMALL = 6, END_SMALL = 24, TOP = 16, CLOCK = 64;
struct State {
    int charge = 0;  // 0..voltCharge-1 running; charged: its clock
    bool charged = false;
    int ball = 0;    // frames left (0: none)
    Vector2 v{};     // the ball's velocity
    bool shown = false;  // the charged flash wrote his colours
};
static State g{};

static void Reset() {  // (each stage's start: Hook_StageLoad; his colours are the stage's own by then)
    g = State();
}

static void Show(EntityPlayer* p, const ExtraAbilities& c, bool restart) {
    int t = c.voltFrames - g.ball;
    int frame = (t < START_SMALL || g.ball <= END_SMALL) ? SMALL + ((t >> 2) & 1) : (t / std::max(1, c.voltTicks)) % LOOP;
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, restart);
    if (p->animator.frameCount > frame) {  // the code picks the frame
        p->animator.frameID = frame;
        p->animator.timer = 0;
    }
    p->animator.speed = 0;
}

static void Velocity(EntityPlayer* p) {
    int vx = g.v.x, vy = g.v.y - Gravity(p);  // (the air state adds it back)
    if (vy > -0x40000 && vy < 0)  // (and takes 1/32 of the speed along off while rising that slowly: added in advance)
        vx = (int)((long long)vx * 32 / 31);
    p->velocity.x = vx;
    p->velocity.y = vy;
    p->groundVel = g.v.x;
    NoJumpCap(p);
}

// The charged flash (a runtime palette effect): charge1 every other 4 frames of the charge's clock; his own colours back
// once it's over
static void Glow(bool on) {
    const ExtraData& x = Extra(g_character);
    on = on && (int)x.chargePalettes[0].size() > 0 && ((g.charge >> 2) & 1);
    if (!on) {
        if (g.shown)
            ApplyExtraPalette();
        g.shown = false;
        return;
    }
    if (!ExtraPaletteScene())
        return;
    for (const PaletteColour& pc : x.chargePalettes[0])
        RSDK->SetPaletteEntry(0, pc.index, pc.rgb);
    g.shown = true;
}

// Each frame after the game's update (Abilities)
static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (g.ball > 0) {  // the ball
        bool airState = !g_playerStateAir || (void*)p->state.state == g_playerStateAir;
        bool ours = p->animator.animationID == ANI_JUMP;
        if (Hurt(p) || Held(p) || (air && (!ours || !airState))) {
            g.ball = 0;  // a spring, an object, a hit, death: over (their speed and pose stay)
            Log("voltteccer: taken over");
        } else {
            if (!air) {  // a floor: it rebounds up (the speed kept)
                if (g.v.y > 0)
                    g.v.y = -g.v.y;
                p->onGround = false;
                p->angle = 0;
                p->collisionMode = 0;  // (the floor's)
                if (g_playerStateAir)
                    p->state.state = (void(__fastcall*)())g_playerStateAir;
            } else {
                int vy = p->velocity.y;
                if (g.v.x != 0 && p->velocity.x == 0)  // a wall
                    g.v.x = -g.v.x;
                else if ((g.v.x > 0 && p->velocity.x < 0) || (g.v.x < 0 && p->velocity.x > 0))  // bounced back
                    g.v.x = -g.v.x;
                if (g.v.y < 0 && (vy == 0 || p->position.y < (TOP << 16)))  // a ceiling, the stage's top
                    g.v.y = -g.v.y;
                else if ((g.v.y > 0 && vy < 0) || (g.v.y < 0 && vy > 0))  // bounced (a badnik, a boss, a bumper)
                    g.v.y = -g.v.y;
            }
            if (--g.ball == 0) {  // over: back to his jump ball, with half its speed
                BackToJump(p);
                p->velocity.x = g.v.x / 2;
                p->velocity.y = g.v.y / 2;
                p->groundVel = p->velocity.x;
                Log("voltteccer: over");
            } else {
                p->direction = g.v.x < 0 ? 1 : 0;
                Velocity(p);
                Show(p, c, !air);
                if (g_blinkOffset >= 0) {  // untouchable (without the blink's own flicker)
                    int& blink = *(int*)((char*)p + g_blinkOffset);
                    if (blink < 3)
                        blink = 3;
                }
            }
        }
    }
    // the charge
    int a = p->animator.animationID;
    bool run = !air && !Held(p) && a >= ANI_WALK && a <= ANI_DASH + 1 && std::abs(p->groundVel) >= c.voltRun;
    if (Hurt(p) || g.ball > 0) {
        g.charge = 0;
        g.charged = false;
    } else if (!g.charged) {
        if (run && ++g.charge >= std::max(1, c.voltCharge)) {
            g.charged = true;
            g.charge = 0;
            if (c.voltReadySound)
                PlaySound(c.voltReadySound);
            Log("voltteccer: charged");
        } else if (!run) {
            g.charge = 0;
        }
    } else {
        g.charge = (g.charge + 1) % CLOCK;  // (the flash's clock)
        if (!air && std::abs(p->groundVel) < c.voltKeep)
            g.charged = false;  // slowing down loses it
    }
    bool airState = !g_playerStateAir || (void*)p->state.state == g_playerStateAir;
    if (g.charged && p->jumpPress && air && airState && !Held(p) && !Hurt(p)) {  // the launch: up-forward
        int dir = p->velocity.x > 0 ? 1 : p->velocity.x < 0 ? -1 : (p->direction & 1) ? -1 : 1;
        g.charged = false;
        g.charge = 0;
        g.ball = std::max(START_SMALL + END_SMALL + 1, c.voltFrames);
        g.v = {dir * c.voltDiag, -c.voltDiag};
        p->direction = dir < 0 ? 1 : 0;
        p->jumpAbilityState = 0;
        Velocity(p);
        Show(p, c, true);
        if (c.voltSound)
            PlaySound(c.voltSound);
        Log("voltteccer: launched (%d)", dir);
    }
    Glow(g.charged && g.ball == 0);
}
}  // namespace volt
