// Rouge's Treasure Sense and Jewel Thief in S3&K (tools/treasure_sense.py: the same rules and numbers as Sonic 1/2 and CD;
// included by NoSwapS3K.cpp after WaterWalk.h). The user's lean first version (2026-09-30):
// - Treasure Sense: Y on the ground (standing, walking or running; not hurt, not held). She stops to listen in her
//   "Looking Up" pose for sensePause frames, then for senseShow frames the game's ring (3K_Global/Ring.bin "Normal
//   Ring" frame 0, exact pixels) blinks at the screen's edge on the line from her to the nearest hidden giant ring
//   (SpecialRing entities still in the stage and drawn: the game removes collected ones), or on it when it's on
//   screen; lit for half of a period that runs from 32 frames (SENSE_FAR px and more, across + down) to 4 (SENSE_NEAR px or
//   less). Drawn in the Player's icon pass (shots::PlayerDraw: John Morris' sub-weapon icon pass, generalised), never
//   while a title card or the results are up or while she's held. Nothing found: MenuBleep ("no signal") and no
//   marker. Then senseCooldown frames. Y in the air stays her Screw Kick.
// - Jewel Thief: ItemBox's powerup (0x1401d26c0, "ItemBox_GivePowerup(box)": its type at +0x70, the player it rewards at
//   +0x88; type 0 the 10-ring box: Player_GiveRings(player, 10, true) at 0x1401d2b74) is wrapped: after it, a ring box
//   rewarding player 1 while a jewelThief extra plays gives 10 more through the game's own Player_GiveRings
//   (0x1401e2e20; its cap and extra life), silently. Both functions' first bytes are checked at startup; on a mismatch
//   the hook stays off (10 rings, as before).

namespace treasure {
constexpr int MARGIN = 12, SENSE_NEAR = 64, SENSE_FAR = 2048, BLINK_NEAR = 2, BLINK_FAR = 16;  // (tools/treasure_sense.py)
constexpr int ANI_LOOK_UP = 3;  // (3K_Players' animation list: Idle, Bored 1, Bored 2, Look Up, Crouch...)
constexpr uintptr_t GIVE_POWERUP = 0x1401d26c0, GIVE_RINGS = 0x1401e2e20;
constexpr int BOX_TYPE = 0x70, BOX_PLAYER = 0x88, TYPE_RINGS = 0, EXTRA_RINGS = 10;

static int g_t = 0;         // 0 ready; 1..pause the pause; then the marker; below 0 the cooldown
static Vector2 g_last{};    // her position last frame (a stage change or a warp ends it)

static bool On() { return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.treasureSense; }

// The nearest hidden giant ring to her (px across + down)
static bool Find(EntityPlayer* p, Vector2* at, int* dist) {
    int32 cls = RSDK->FindObject("SpecialRing");
    if (cls <= 0)
        return false;
    bool found = false;
    Entity* e = nullptr;
    while (RSDK->GetAllEntities((uint16)cls, (void**)&e)) {
        if (!e || !e->visible)
            continue;
        int d = std::abs((e->position.x - p->position.x) >> 16) + std::abs((e->position.y - p->position.y) >> 16);
        if (!found || d < *dist) {
            found = true;
            *dist = d;
            *at = e->position;
        }
    }
    return found;
}

// Each frame after player 1's update (Hook_PlayerUpdate, after the moves)
static void Update(EntityPlayer* p) {
    if (!On()) {
        g_t = 0;
        return;
    }
    const ExtraAbilities& c = Extra(g_character).abilities;
    Vector2 last = g_last;
    g_last = p->position;
    if (std::abs(p->position.x - last.x) > (64 << 16) || std::abs(p->position.y - last.y) > (64 << 16))
        g_t = g_t < 0 ? g_t : 0;  // (a new stage, a respawn, a warp: whatever was going on is over)
    if (g_t < 0)
        g_t++;
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_LOOK_UP
                 || (a >= ANI_WALK && a <= ANI_DASH + 1);
    bool free = p->onGround && plain && !Hurt(p) && !Held(p);
    if (g_t == 0 && free && YPressed(p)) {
        g_t = 1;
        Log("treasure sense: listening");
    }
    if (g_t > 0 && g_t <= c.sensePause) {  // the pause: held still, listening
        if (!free) {
            g_t = 0;
            Log("treasure sense: interrupted");
            return;
        }
        p->groundVel = 0;
        p->velocity.x = 0;
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_LOOK_UP, &p->animator, false, 0);
        if (++g_t > c.sensePause) {
            Vector2 at{};
            int d = 0;
            if (!Find(p, &at, &d)) {
                if (c.senseSound)
                    PlaySound(c.senseSound);
                g_t = -c.senseCooldown;
                Log("treasure sense: no signal (no giant ring left here)");
            } else {
                Log("treasure sense: the nearest giant ring is %d px away (%d, %d)", d, at.x >> 16, at.y >> 16);
            }
        }
    } else if (g_t > c.sensePause) {
        if (++g_t > c.sensePause + c.senseShow)
            g_t = -c.senseCooldown;
    }
}

// The marker wants the icon pass this frame (shots::QueueIcon)
static bool Pass() { return On() && g_t > Extra(g_character).abilities.sensePause; }

static void Note(int why, const char* what) {  // (each reason the marker isn't drawn, logged once)
    static unsigned noted = 0;
    if (!(noted & (1u << why))) {
        noted |= 1u << why;
        Log("treasure sense: marker not drawn: %s", what);
    }
}

// In the icon pass (shots::PlayerDraw): the ring at the treasure, or at the screen's edge toward it, lit or not
static void Draw() {
    if (!Pass())
        return;
    auto* p = (EntityPlayer*)RSDK->GetEntity(0);
    if (!p || !Readable(p, sizeof(EntityPlayer)))
        return;
    if (Held(p))
        return Note(0, "she's held (normal)");
    if (shots::Showing("TitleCard") || shots::Showing("ActClear"))
        return Note(1, "title card / results up (normal)");
    shots::ScreenView v{};
    if (!shots::Screen(&v))
        return Note(2, "no screen info");
    Vector2 at{};
    int d = 0;
    if (!Find(p, &at, &d))
        return;
    int half = std::clamp(BLINK_NEAR + std::max(d - SENSE_NEAR, 0) * (BLINK_FAR - BLINK_NEAR) / (SENSE_FAR - SENSE_NEAR), BLINK_NEAR, BLINK_FAR);
    if (g_t % (2 * half) >= half)
        return;  // (the blink's dark half)
    int w = v.w, h = v.h, left = v.left, top = v.top;
    int tx = (at.x >> 16) - left, ty = (at.y >> 16) - top;
    if (tx < MARGIN || ty < MARGIN || tx > w - MARGIN || ty > h - MARGIN) {  // off screen: the edge, on the line from her
        int px = (p->position.x >> 16) - left, py = (p->position.y >> 16) - top;
        int dx = tx - px, dy = ty - py;
        long long s = 256;  // how far along the line (in 256ths) the edge is
        if (dx > 0)
            s = std::min(s, (long long)(w - MARGIN - px) * 256 / dx);
        if (dx < 0)
            s = std::min(s, (long long)(MARGIN - px) * 256 / dx);
        if (dy > 0)
            s = std::min(s, (long long)(h - MARGIN - py) * 256 / dy);
        if (dy < 0)
            s = std::min(s, (long long)(MARGIN - py) * 256 / dy);
        s = std::max(s, 0LL);
        tx = std::clamp((int)(px + dx * s / 256), MARGIN, w - MARGIN);
        ty = std::clamp((int)(py + dy * s / 256), MARGIN, h - MARGIN);
    }
    uint16 frames = RSDK->LoadSpriteAnimation("3K_Global/Ring.bin", SCOPE_STAGE);
    if (frames == 0xFFFF)
        return Note(4, "3K_Global/Ring.bin not loaded");
    Entity* self = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (!self || !Readable(self, sizeof(Entity)))
        return;
    static bool first = true;
    if (first) {
        first = false;
        Log("treasure sense: drawing the marker (screen %dx%d)", w, h);
    }
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;  // (DrawSprite draws with the entity's own)
    self->drawFX = 0;
    self->inkEffect = 0;
    self->direction = 0;
    Animator ring{};
    RSDK->SetSpriteAnimation(frames, 0, &ring, true, 0);
    Vector2 pos = {tx << 16, ty << 16};
    RSDK->DrawSprite(&ring, &pos, true);
    self->drawFX = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

// Jewel Thief: ItemBox's powerup, wrapped
typedef void (*GivePowerupFn)(Entity* box);
typedef void (*GiveRingsFn)(EntityPlayer* player, int32 amount, bool32 playSfx);
static GivePowerupFn g_givePowerup = nullptr;
static void Hook_GivePowerup(Entity* box) {
    g_givePowerup(box);
    if (!box || g_character <= 0 || !RSDK || !Extra(g_character).abilities.jewelThief)
        return;
    int32 type = *(int32*)((uint8*)box + BOX_TYPE);
    auto* who = *(EntityPlayer**)((uint8*)box + BOX_PLAYER);
    if (type != TYPE_RINGS || !who || who != (EntityPlayer*)RSDK->GetEntity(0))
        return;
    ((GiveRingsFn)GIVE_RINGS)(who, EXTRA_RINGS, false);
    Log("jewel thief: a ring monitor: %d more rings", EXTRA_RINGS);
}

static void SetUp() {
    static const uint8 POWERUP[] = {0x4c, 0x8b, 0xdc, 0x53, 0x55, 0x48, 0x83, 0xec, 0x68, 0x66, 0x0f, 0x6f, 0x05, 0x6f,
                                    0x0f, 0x9c, 0x00, 0x48, 0x8b, 0xe9, 0x8b, 0x41, 0x70, 0x48, 0x8b, 0x99, 0x88, 0x00,
                                    0x00, 0x00};  // (type: [rcx+0x70]; the player: [rcx+0x88])
    // its type 0 case: Player_GiveRings(player, 10, true) (mov r8d, r14d; mov edx, 10; mov rcx, rbx; call GIVE_RINGS)
    static const uint8 RINGS_CASE[] = {0x45, 0x8b, 0xc6, 0xba, 0x0a, 0x00, 0x00, 0x00, 0x48, 0x8b, 0xcb, 0xe8, 0x9c, 0x02,
                                       0x01, 0x00};
    constexpr uintptr_t RINGS_CASE_AT = 0x1401d2b74;
    static const uint8 GIVE[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x74, 0x24, 0x10, 0x57, 0x48, 0x83, 0xec, 0x20};
    bool ok = Readable((void*)GIVE_POWERUP, sizeof(POWERUP)) && !memcmp((void*)GIVE_POWERUP, POWERUP, sizeof(POWERUP))
              && Readable((void*)RINGS_CASE_AT, sizeof(RINGS_CASE))
              && !memcmp((void*)RINGS_CASE_AT, RINGS_CASE, sizeof(RINGS_CASE))
              && Readable((void*)GIVE_RINGS, sizeof(GIVE)) && !memcmp((void*)GIVE_RINGS, GIVE, sizeof(GIVE));
    if (!ok) {
        Log("jewel thief: ItemBox's powerup / Player_GiveRings are DIFFERENT (another game build?): off (10 rings)");
        return;
    }
    if (MH_CreateHook((void*)GIVE_POWERUP, (void*)Hook_GivePowerup, (void**)&g_givePowerup) != MH_OK
        || MH_EnableHook((void*)GIVE_POWERUP) != MH_OK) {
        MH_RemoveHook((void*)GIVE_POWERUP);
        Log("jewel thief: hooking ItemBox's powerup failed: off");
        return;
    }
    Log("jewel thief: on (ItemBox's powerup wrapped; acts only for an extra with jewelThief)");
}
}  // namespace treasure
