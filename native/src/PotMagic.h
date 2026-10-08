// Gilius Thunderhead's pot magic in S3&K (tools/pot_magic.py: the same rules and numbers as Sonic 1/2 and CD; included
// by NoSwapS3K.cpp after Voltteccer.h). The user's design (2026-10-02), Joe's monitor-charged meter (Ninjutsu.h) with a
// cap above one:
// - An item monitor that breaks while he plays (Hook_ItemBoxCheck: whatever broke it) adds a pot, up to potsMax; 0 at
//   each stage load but a seamless act transition's (Carry). The pots' pictures (his extra 6, a crop of his portrait)
//   in the dark box at the top middle of the screen, one each, in the HUD pass (shots::HudPass), as Joe's icon.
// - Up + Y casts the Earthquake (Press, before Abilities: the press is taken, g_ySuper, so no chop goes with it), from
//   his own free states; every pot is spent, the pots spent are its level (index level - 1 of the potsLevel* lists):
//   - its hit: the Screen Nuke's (g_nuke: the shots' Player_CheckBadnikTouch hook takes anything in the box round him as
//     touched, potsLevelX / Y px; 0 the whole screen), in potsLevelPulses waves of potsHit frames, potsGap apart, the
//     first potsFirst frames after the cast (a boss: a hit per wave);
//   - its flash: NukeFlashStart with potsFlash in the nuke's place (as Joe's Kariu); no shake (NoSwapS3K.cpp's Hammer
//     Drop note: the camera's shake isn't known safely in this build);
//   - its boulders (tools/pot_magic.py ROCK_*: the same numbers): potsLevelRocks per wave fall from above the screen,
//     land on the floor under them (the engine's ObjectTileCollision on a copy of his entity) and burst (extra 4 after a
//     big one, extra 5 after a small one), drawn after him in his own draw (shots::PlayerDraw), from his own frames
//     (extra 3: the boulders).
// - The cast pose (Update, after Abilities): extra 1 (slot 42) for potsCast frames, potsCastTicks each; still on the
//   ground, hanging still in the air, nothing hurts him (the blink at 3); a hit or an object ends the pose, not the quake.

namespace pots {
constexpr int LEVELS = 7;
constexpr int ROCK_TOP = 40, ROCK_VY0 = 0x30000, ROCK_G = 0x6000, ROCK_VMAX = 0xC0000, ROCK_STAGGER = 3, ROCK_ABOVE = 48,
              ROCK_BELOW = 160, ROCK_SCREEN = 184;
constexpr int ROCK_R[2] = {31, 16};  // half heights: big, small
constexpr int BURST_FRAMES = 5, BURST_TICKS = 4, ICON_GAP = 2, FEET = 20;  // (FEET: a burst frame's bottom under its y)
constexpr int ANI_ROCKS = 3, ANI_BURST_BIG = 4, ANI_BURST_SMALL = 5, ANI_POT = 6;  // (ANI_EXTRA(k): slots 45-48)

struct Rock {
    bool on;
    int x, y, vy;  // 16.16
    int age, delay, kind, phase, feet;  // phase 0 waiting, 1 falling, 2 bursting
    uint8 dir;
};
static Rock g_rocks[48];
static int g_count = 0;   // the pots
static int g_pose = 0;    // the cast pose's frames left
static int g_age = -1;    // the quake's age (-1: none)
static int g_level = 0;   // its level (pots spent)
static int g_feet = 0;    // his feet at the cast (16.16)

static bool On() { return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.potMagic; }

static void Reset() {  // (shots::Hook_StageLoad)
    g_count = g_pose = g_level = 0;
    g_age = -1;
    memset(g_rocks, 0, sizeof(g_rocks));
}

static void Carry() {  // (shots::Hook_StageLoad, a seamless act transition: the pots kept, a quake going on dropped)
    int pots = g_count;
    Reset();
    g_count = pots;
}

static void MonitorBroke() {  // (shots::Hook_ItemBoxCheck)
    if (!On())
        return;
    const ExtraAbilities& c = Extra(g_character).abilities;
    if (g_count >= c.potsMax)
        return;
    g_count++;
    if (c.potsSound)
        PlaySound(c.potsSound);
    Log("pot magic: a monitor broke: %d pot(s)", g_count);
}

static int EndAge(const ExtraAbilities& c) {  // (pot_magic.end_age)
    int p = 1;
    for (int k = 0; k < std::min(c.potsMax, LEVELS); k++)
        p = std::max(p, c.potsLevelPulses[k]);
    return std::max({c.potsFirst + (p - 1) * c.potsGap + c.potsHit, c.potsFlashCount, c.potsShake}) + 1;
}

// Wave w's boulder k of n, over -span .. span px from the middle (pot_magic.rock_offsets: the same arithmetic)
static void RockAt(int span, int n, int w, int k, int* dx, int* delay, int* kind) {
    double step = 2.0 * span / n;
    auto x = [&](int j) {
        long v = std::lround(-span + step * (j + 0.5) + (w % 2 ? step / 2 : 0));
        return (int)(v <= span ? v : v - 2L * span);
    };
    int me = x(k), order = 0;
    for (int j = 0; j < n; j++) {  // (sorted by distance from the middle, then by x)
        int o = x(j);
        if (std::abs(o) < std::abs(me) || (std::abs(o) == std::abs(me) && o < me))
            order++;
    }
    *dx = me;
    *delay = ROCK_STAGGER * order;
    *kind = k % 2;
}

static void Spawn(EntityPlayer* p, int lv, int w) {
    const ExtraAbilities& c = Extra(g_character).abilities;
    int n = c.potsLevelRocks[lv], whole = c.potsLevelX[lv] == 0;
    shots::ScreenView v{};
    if (n <= 0 || !shots::Screen(&v))
        return;
    int cx = whole ? (v.left + v.w / 2) : (p->position.x >> 16), span = whole ? ROCK_SCREEN : c.potsLevelX[lv];
    for (int k = 0; k < n; k++) {
        Rock* r = nullptr;
        for (Rock& s : g_rocks)
            if (!s.on) {
                r = &s;
                break;
            }
        if (!r)
            return;
        int dx = 0, delay = 0, kind = 0;
        RockAt(span, n, w, k, &dx, &delay, &kind);
        *r = Rock{true, (cx + dx) << 16, (v.top - ROCK_TOP) << 16, ROCK_VY0, 0, delay, kind, 0, g_feet, (uint8)(k % 2)};
    }
}

// Before Abilities: up + Y with pots casts the Earthquake. True: the press was the cast's (no other Y move sees it)
static bool Press(EntityPlayer* p) {
    if (!On() || g_count <= 0 || g_pose > 0 || !p->up || !YPressed(p) || Hurt(p))
        return false;
    StateKind kind = KindOf((const void*)p->state.state);
    if (kind != STATE_AIR && kind != STATE_GROUND && kind != STATE_OPEN)
        return false;
    const ExtraAbilities& c = Extra(g_character).abilities;
    if (c.potsCastSound)
        PlaySound(c.potsCastSound);
    g_level = std::clamp(g_count, 1, std::min(c.potsMax, LEVELS));
    g_count = 0;
    g_age = 0;
    g_feet = p->position.y + (FEET << 16);
    if (c.potsFlashCount > 0) {
        static ExtraAbilities flash;  // (NukeFlashStart reads the nuke's flash: the quake's in its place, as Joe's Kariu)
        flash = c;
        flash.nukeFlashCount = std::min(c.potsFlashCount, (int)(sizeof(flash.nukeFlash) / sizeof(flash.nukeFlash[0])));
        for (int k = 0; k < flash.nukeFlashCount; k++)
            flash.nukeFlash[k] = c.potsFlash[k];
        NukeFlashStart(flash);
    }
    if (c.potsQuakeSound)
        PlaySound(c.potsQuakeSound);
    Log("pot magic: the Earthquake, level %d", g_level);
    g_pose = std::max(c.potsCast, 1);
    return true;
}

static void Rocks(EntityPlayer* p) {
    for (Rock& r : g_rocks) {
        if (!r.on)
            continue;
        r.age++;
        if (r.age > 400) {  // (a safety net)
            r.on = false;
            continue;
        }
        if (r.phase == 0) {
            if (r.age >= r.delay)
                r.phase = 1;
            continue;
        }
        if (r.phase == 1) {
            r.y += r.vy;
            if (r.vy < ROCK_VMAX)
                r.vy += ROCK_G;
            if (r.y >= r.feet - (ROCK_ABOVE << 16)) {  // (low enough: the floor counts)
                Entity probe = *(Entity*)p;  // (a copy of his entity: the engine's collision, nothing of his moved)
                probe.position.x = r.x;
                probe.position.y = r.y;
                int rad = ROCK_R[r.kind];
                if (RSDK->ObjectTileCollision(&probe, p->collisionLayers, shots::CMODE_FLOOR, p->collisionPlane, 0, rad << 16, true)) {
                    r.y = probe.position.y + ((rad - FEET) << 16);  // (the burst's frames: their bottom FEET px under y)
                    r.phase = 2;
                    r.age = 0;
                }
            }
            if (r.phase == 1 && r.y > r.feet + (ROCK_BELOW << 16))
                r.on = false;
            continue;
        }
        if (r.age / BURST_TICKS >= BURST_FRAMES)
            r.on = false;
    }
}

// After Abilities: the quake's waves, the boulders, the pose
static void Update(EntityPlayer* p) {
    if (!On())
        return;
    const ExtraAbilities& c = Extra(g_character).abilities;
    if (g_age >= 0) {
        g_age++;
        int lv = g_level - 1, waves = std::clamp(c.potsLevelPulses[lv], 1, 4);
        bool pulse = false;
        for (int w = 0; w < waves; w++) {
            int s = c.potsFirst + w * c.potsGap;
            pulse |= g_age >= s && g_age < s + c.potsHit;
            if (g_age == 1 + w * c.potsGap)
                Spawn(p, lv, w);
        }
        if (pulse) {  // (counted down at each update's start, before this: the targets update after him)
            g_nuke = std::max(g_nuke, 1);
            g_nukeReachX = c.potsLevelX[lv];
            g_nukeReachY = c.potsLevelY[lv];
        }
        if (g_age > EndAge(c))
            g_age = -1;
    }
    Rocks(p);
    if (g_pose <= 0)
        return;
    if (Hurt(p) || Held(p)) {  // a hit, his death or an object: the pose is over (the quake goes on)
        g_pose = 0;
        return;
    }
    int total = std::max(c.potsCast, 1), ticks = std::max(c.potsCastTicks, 1);
    int frames = std::max(total / ticks, 1), elapsed = total - g_pose;
    PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, elapsed == 0);
    p->animator.frameID = std::min(elapsed / ticks, frames - 1);  // (the timer picks the frame)
    p->animator.timer = 0;
    if (g_blinkOffset >= 0) {  // nothing hurts him meanwhile (no flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    if (p->onGround) {
        p->groundVel = 0;
        p->velocity.x = 0;
    } else {  // hanging still (the melee's shotHang)
        p->velocity.x = 0;
        p->velocity.y = 0;
    }
    if (--g_pose == 0)
        RSDK->SetSpriteAnimation(g_extraFrames, p->onGround ? ANI_IDLE : ANI_JUMP, &p->animator, true, 0);
}

static bool Pass() { return On() && g_count > 0; }  // (the pots' pictures want the icon pass: shots::QueueIcon)

static void Note(int why, const char* what) {  // (each reason something isn't drawn, logged once)
    static unsigned noted = 0;
    if (!(noted & (1u << why))) {
        noted |= 1u << why;
        Log("pot magic: not drawn: %s", what);
    }
}

// Draw with the entity's own draw settings cleared (DrawSprite uses the current entity's), then put back
template <typename F>
static void Plain(uint8 dir, F draw) {
    Entity* self = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (!self || !Readable(self, sizeof(Entity)))
        return;
    uint8 fx = self->drawFX, ink = self->inkEffect, d = self->direction;
    self->drawFX = 0;
    self->inkEffect = 0;
    self->direction = dir;
    draw();
    self->drawFX = fx;
    self->inkEffect = ink;
    self->direction = d;
}

// In the icon pass (shots::PlayerDraw): the pots' pictures in the dark box at the top middle
static void Draw() {
    if (!Pass())
        return;
    if (shots::Showing("TitleCard") || shots::Showing("ActClear"))
        return Note(0, "title card / results up (normal)");
    int32 cx = 0;
    if (!shots::ScreenCentreX(&cx))
        return Note(1, "no screen info");
    SpriteFrame* f = RSDK->GetFrame(g_extraFrames, (uint16)ANI_EXTRA(ANI_POT), 0);
    if (!f || !f->frame.width || !f->frame.height)
        return Note(2, "the pot picture (extra 6) has no size");
    int w = f->frame.width, h = f->frame.height, n = g_count;
    int iw = n * (w + ICON_GAP) - ICON_GAP, bw = iw + 2 * shots::ICON_PAD_X, bh = h + 2 * shots::ICON_PAD_Y;
    Plain(0, [&] {
        RSDK->DrawRect(cx - bw / 2, shots::ICON_TOP, bw, bh, 0x000000, shots::ICON_ALPHA, shots::ICON_INK_ALPHA, true);
        Animator icon{};
        RSDK->SetSpriteAnimation(g_extraFrames, (uint16)ANI_EXTRA(ANI_POT), &icon, true, 0);
        int x = cx - iw / 2 + w / 2;  // (the picture's pivot is its middle)
        for (int k = 0; k < n; k++, x += w + ICON_GAP) {
            Vector2 pos = {x << 16, (shots::ICON_TOP + bh / 2) << 16};
            RSDK->DrawSprite(&icon, &pos, true);
        }
    });
}

// After his own draw (shots::PlayerDraw): the boulders and their bursts, in the world
static void DrawRocks() {
    if (!On())
        return;
    for (const Rock& r : g_rocks) {
        if (!r.on || r.phase == 0)
            continue;
        Animator a{};
        if (r.phase == 1)
            RSDK->SetSpriteAnimation(g_extraFrames, (uint16)ANI_EXTRA(ANI_ROCKS), &a, true, (uint8)r.kind);
        else
            RSDK->SetSpriteAnimation(g_extraFrames, (uint16)ANI_EXTRA(r.kind ? ANI_BURST_SMALL : ANI_BURST_BIG), &a, true,
                                     (uint8)std::min(r.age / BURST_TICKS, BURST_FRAMES - 1));
        if (!a.frames || a.frameCount == 0) {
            Note(3, "the Earthquake's frames (extra 3-5) are missing");
            continue;
        }
        Vector2 pos = {r.x, r.y};
        Plain(r.dir, [&] { RSDK->DrawSprite(&a, &pos, false); });
    }
}
}  // namespace pots
