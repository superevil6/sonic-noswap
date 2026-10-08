// Marine's Anchor Throw in S3&K (tools/anchor_throw.py, the same states and numbers as Sonic 1/2 and CD; included by
// NoSwapS3K.cpp after HeadThrow.h, right before Abilities, so the helpers above are in scope). The user's design
// (2026-09-29):
// - Y (on the ground or in the air): the anchor flies forward (her facing; left / right held turn her first) in an arc:
//   anchorSpeed along, up at anchorRise, falling back under anchorGravity (up + Y: anchorHighSpeed / anchorHighRise, a
//   higher throw), anchorFrames frames at most. A chain is drawn from her hand to it (RSDK DrawLine, 2 px, dark), the
//   anchor slot 43's frame (ANI_EXTRA(2): 0 flukes forward, 1 up, 2 down; mirrored with the throw), in the Player's draw.
// - A badnik, monitor or boss the anchor reaches (Player_CheckBadnikTouch, the shots' hook: AnchorTouch) is touched: the
//   game takes it as her attack (reported as the jump), and one flying out comes back.
// - Solid terrain LEAD px ahead of it on a wall or ceiling side (the tile's ceiling-side solidity: never a jump-through
//   platform) latches it: she's reeled in (reelSpeed; the air state's gravity taken off in advance) until within
//   latchRange, stopped by the terrain, or reelFrames on, then a small hop toward it (grappleHop, grappleForward). A floor
//   under it (falling) or its range sends it back to her hand at anchorReturn px a frame; then anchorCooldown frames.
// - Meanwhile she holds her throwing pose (slot 41, an attack): still on the ground, falling as usual in the air. A hit,
//   an object taking over, a spring or a warp ends it.

static Entity* CurrentEntity(int* slotOut);  // (NoSwapS3K.cpp, below)

namespace anchor {
constexpr int LATCH = 100, BACK = 200, BACK_MAX = 90, HAND_X = 16, HAND_Y = 4, LEAD = 12, BOX = 12;
constexpr int F_FORWARD = 0, F_UP = 1, F_DOWN = 2;
constexpr uint32 CHAIN = 0x21201D;  // the anchor's outline (her #21201d)

struct State {
    int state = 0;        // tools/anchor_throw.py's numbers (0: ready; below 0: the cooldown)
    bool left = false;    // thrown to the left
    bool high = false;    // up + Y: the high throw
    bool ceiling = false; // latched on a ceiling (the frame: flukes up)
    int vy = 0;           // flying: its vertical speed this frame (the frame)
    Vector2 pos{};        // the anchor (16.16), or the point latched
    Vector2 last{};       // her position last frame (a warp ends it)
    void* groundState = nullptr;  // the plain ground state (seen while she stands, walks or runs)
};
static State g{};

static bool On() { return g_character > 0 && g_extraFrames && Extra(g_character).abilities.anchorThrow; }

// A solid tile at (x, y) px from her: floorSide, anything solid from above (a floor, a jump-through platform); otherwise
// only the ceiling side (walls and ceilings: the tile's LRB solidity)
static bool Solid(EntityPlayer* p, int x, int y, bool floorSide) {
    constexpr uint8 CMODE_FLOOR = 0, CMODE_ROOF = 2;
    return (floorSide && RSDK->ObjectTileCollision(p, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, x << 16, y << 16,
                                                   false))
           || RSDK->ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, x << 16, y << 16, false);
}

static void Pose(EntityPlayer* p) {  // slot 41's frame, reported as the jump (an attack)
    Animator probe{};
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA_ATTACK, &probe, true, 0);
    if (p->animator.frames != probe.frames)
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA_ATTACK, &p->animator, true, 0);
    p->animator.animationID = ANI_JUMP;
    p->animator.frameID = 0;
    p->animator.timer = 0;
}

static void Gone(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    g.state = -c.anchorCooldown;
    if (air)
        BackToJump(p);
    else
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

static void ToAir(EntityPlayer* p) {
    p->onGround = false;
    p->angle = 0;
    p->collisionMode = 0;  // floor
    p->state.state = (void(__fastcall*)())g_playerStateAir;
}

static Vector2 Hand(EntityPlayer* p) {
    return {p->position.x + (((p->direction & 1) ? -HAND_X : HAND_X) << 16), p->position.y + (HAND_Y << 16)};
}

static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1);
    if (!air && plain && p->state.state && g.state <= 0)
        g.groundState = (void*)p->state.state;
    bool airState = g_playerStateAir && (void*)p->state.state == g_playerStateAir;
    bool inState = air ? airState : g.groundState && (void*)p->state.state == g.groundState;
    Vector2 last = g.last;
    g.last = p->position;
    if (std::abs(p->position.x - last.x) > (64 << 16) || std::abs(p->position.y - last.y) > (64 << 16))
        g.state = 0;  // (a new stage, a respawn, a warp: whatever was going on is over)
    if (g.state > 0 && (Hurt(p) || Held(p) || !inState)) {  // a hit, an object taking over, a spring...
        g.state = 0;
        return;
    }
    if (g.state < 0)
        g.state++;
    if (g.state == 0 && !Hurt(p) && inState && (air || plain) && YPressed(p)) {
        if (p->left)
            p->direction = 1;
        if (p->right)
            p->direction = 0;
        g.left = p->direction & 1;
        g.high = p->up;
        g.ceiling = false;
        g.pos = Hand(p);
        g.state = 1;
        if (c.anchorSound)
            PlaySound(c.anchorSound);
        Log("marine: anchor throw (%s, %s)", g.high ? "high" : "level", air ? "air" : "ground");
    }
    if (g.state <= 0)
        return;
    g_ab.ready = false;  // (no jump ability meanwhile)
    int s = g.left ? -1 : 1;
    if (g.state < LATCH) {  // flying: the arc
        g.vy = -(g.high ? c.anchorHighRise : c.anchorRise) + c.anchorGravity * g.state;
        g.pos.x += (g.high ? c.anchorHighSpeed : c.anchorSpeed) * s;
        g.pos.y += g.vy;
        int ax = (g.pos.x - p->position.x) >> 16, ay = (g.pos.y - p->position.y) >> 16;
        int met = 0;
        if (g.vy >= 0 && Solid(p, ax, ay + LEAD, true)) {
            met = 1;  // a floor
        } else if (Solid(p, ax + s * LEAD, ay, false)) {
            met = 2;  // a wall: latched at that point
            g.pos.x += (s * LEAD) << 16;
        } else if (g.vy < 0 && Solid(p, ax, ay - LEAD, false)) {
            met = 3;  // a ceiling
            g.pos.y -= LEAD << 16;
            g.ceiling = true;
        }
        if (met == 0 && ++g.state >= c.anchorFrames)
            g.state = BACK + 1;
        if (met == 1)
            g.state = BACK + 1;
        if (met >= 2) {
            g.state = LATCH + 1;
            if (c.latchSound)
                PlaySound(c.latchSound);
            Log("marine: the anchor bites (%s)", met == 2 ? "wall" : "ceiling");
        }
    } else if (g.state < BACK) {  // latched: reeled in; there yet?
        int dx = (g.pos.x - p->position.x) >> 16, dy = (g.pos.y - p->position.y) >> 16;
        bool stopped = g.state > LATCH + 2 && (air ? std::abs(p->position.x - last.x) < 0x8000
                                                         && std::abs(p->position.y - last.y) < 0x8000
                                                   : p->groundVel == 0);
        if ((std::abs(dx) < c.latchRange && std::abs(dy) < c.latchRange) || g.state >= LATCH + c.reelFrames || stopped) {
            g.state = -c.anchorCooldown;  // there: a small hop toward it, and let go
            if (!air)
                ToAir(p);
            p->velocity.y = -c.grappleHop;
            p->velocity.x = dx < 0 ? -c.grappleForward : c.grappleForward;
            p->groundVel = p->velocity.x;
            NoJumpCap(p);
            BackToJump(p);
            return;
        }
        g.state++;
        double fx = g.pos.x - p->position.x, fy = g.pos.y - p->position.y, len = std::sqrt(fx * fx + fy * fy);
        if (!air) {  // on the ground: a point well above lifts her off; otherwise she's drawn along the ground
            if (dy < -12) {
                ToAir(p);
                p->velocity.x = 0;
                p->velocity.y = -0x10000;
                p->groundVel = 0;
            } else {
                p->groundVel = dx < 0 ? -c.reelSpeed : c.reelSpeed;
            }
        } else if (len > 0) {
            p->velocity.x = (int)(c.reelSpeed * fx / len);
            p->velocity.y = (int)(c.reelSpeed * fy / len) - Gravity(p);
        }
        p->direction = dx < 0 ? 1 : 0;
        Pose(p);
        return;
    } else {  // coming back to her hand
        Vector2 hand = Hand(p);
        double fx = hand.x - g.pos.x, fy = hand.y - g.pos.y, len = std::sqrt(fx * fx + fy * fy);
        if ((std::abs(fx) < c.anchorReturn + 0x40000 && std::abs(fy) < c.anchorReturn + 0x40000)
            || g.state >= BACK + BACK_MAX) {
            Gone(p, c, air);
            return;
        }
        g.state++;
        if (len > 0) {
            g.pos.x += (int)(c.anchorReturn * fx / len);
            g.pos.y += (int)(c.anchorReturn * fy / len);
        }
    }
    if (!air) {  // she stands still for it
        p->groundVel = 0;
        p->velocity.x = 0;
    }
    p->direction = g.left ? 1 : 0;
    Pose(p);
}

// Player_CheckBadnikTouch (the shots' hook): while the anchor flies or comes back, anything it reaches (BOX px round it,
// in the entity's hitbox) is touched (the game then takes it as her attack); one flying out comes back
static bool Touch(EntityPlayer* p, Entity* e, Hitbox* hitbox) {
    if (!On() || !p || !e || !hitbox || g.state <= 0 || (g.state > LATCH && g.state < BACK)
        || RSDK->GetEntitySlot(p) != 0)
        return false;
    int hx = (g.pos.x - e->position.x) >> 16, hy = (g.pos.y - e->position.y) >> 16;
    if (hx < hitbox->left - BOX || hx > hitbox->right + BOX || hy < hitbox->top - BOX || hy > hitbox->bottom + BOX)
        return false;
    if (g.state < LATCH)
        g.state = BACK + 1;
    return true;
}

// The Player's draw, wrapped: for Marine, her body, then the chain (two 1 px lines, 2 px thick) and the anchor
typedef void (*DrawFn)(void);
static DrawFn g_draw = nullptr;
static void Draw() {
    int slot = -1;
    Entity* self = CurrentEntity(&slot);
    g_draw();
    if (!self || slot != 0 || !On() || g.state <= 0)
        return;
    auto* p = (EntityPlayer*)self;
    const ExtraAbilities& c = Extra(g_character).abilities;
    Vector2 hand = Hand(p);
    int dx = (g.pos.x - hand.x) >> 16, dy = (g.pos.y - hand.y) >> 16;
    bool flat = std::abs(dx) >= std::abs(dy);
    for (int t = 0; t < 2; t++) {
        int sx = flat ? 0 : t << 16, sy = flat ? t << 16 : 0;
        RSDK->DrawLine(hand.x + sx, hand.y + sy, g.pos.x + sx, g.pos.y + sy, CHAIN, 0xFF, 0, false);
    }
    int frame = F_FORWARD;
    if (g.state < LATCH) {
        int along = g.high ? c.anchorHighSpeed : c.anchorSpeed;
        frame = g.vy < -along ? F_UP : g.vy > along ? F_DOWN : F_FORWARD;
    } else if (g.state < BACK && g.ceiling) {
        frame = F_UP;
    }
    Animator anchor{};
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA(2), &anchor, true, frame);
    int rotation = p->rotation;
    uint8 dir = p->direction;
    p->rotation = 0;
    p->direction = g.left ? 1 : 0;
    RSDK->DrawSprite(&anchor, &g.pos, false);
    p->rotation = rotation;
    p->direction = dir;
}

static DrawFn Wrap(DrawFn draw) {
    if (draw != (DrawFn)Draw)
        g_draw = draw;
    return Draw;
}
}  // namespace anchor

static bool AnchorTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox) { return anchor::Touch(p, e, hitbox); }
static void AnchorThrow(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!anchor::On())
        return;
    anchor::Update(p, c, air);
}
