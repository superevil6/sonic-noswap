// Silver's Psychokinesis in S3&K (abilities.py psycho_grab; included by NoSwapS3K.cpp after the shots, before
// Abilities). The user's design (2026-09-30): Y with a badnik in reach catches it instead of the Psychic Wave; it's
// destroyed as a hit would destroy it (points, animal, explosion: the game's own break), he holds its likeness for a
// moment (slot 45: his hand out, the orb forming) and throws it forward as his shot ("input" "grab"), drawn as the
// badnik was (its animation copied, still playing). Only a badnik's own code can let it be caught:
// - Y (the melee's conditions): SEEK. The badniks that check player 1 this frame (Player_CheckBadnikTouch, the shots'
//   hook) are looked at: on screen, visible, not a hazard's class (jugg::Enemy) nor a class seen hitting as a boss, in
//   reach (psychoReach px ahead, psychoBehind behind, psychoHeight up or down); the nearest is the target.
// - Next frame: CATCH. The target's touch check says "touched" (once); its own code then breaks it
//   (Player_CheckBadnikBreak: broken as his attack, his speed and pose kept) or, being something else, hits him as a
//   boss or hurts him: refused (no hit, no hurt), and the grab is off.
// - Next frame: caught, HOLD for psychoHold frames (standing still, or held still in the air), then CARRY: he plays on
//   with the likeness floating beside his hand (DrawCarried, after his own draw) until Y again: THROW, psychoThrow
//   frames of the pose (held still), then the shot. A hit or a stage change loses it (the user, 2026-09-30: "hold onto
//   it until the Y button is clicked again"). Not caught (refused, gone, or no target): the Psychic Wave instead
//   (WaveY), a frame or two after Y.
// The likeness: the badnik's Animator, found in its entity by its shape (a sprite frame pointer whose frame has a sane
// size, a frame number within the count); none found: the shot's own art (the orb). The shot keeps its own hitbox.

namespace psycho {
enum { IDLE = 0, SEEK, CATCH, HOLD, CARRY, THROW };
constexpr int CARRY_X = 22, CARRY_Y = -6, CARRY_BOB = 2;  // (the likeness beside his hand, bobbing 2 px up and down)
constexpr int HOLD_FRAMES = 5;  // (slot 45's frames: 60-64)

struct State {
    int phase = IDLE;
    int t = 0;
    Entity* target = nullptr;
    uint16 cls = 0;
    int64_t best = -1;
    bool touched = false, caught = false, refused = false;
    bool wave = false;       // the Psychic Wave's turn (WaveY): nothing was caught
    Animator anim{};         // the caught badnik's likeness
    bool haveAnim = false;
    Vector2 last{};
};
static State g{};
static struct {
    Entity* shot = nullptr;  // the shot carrying it
    Animator anim{};
    bool flyRight = true;
} g_thrown;

static bool On() {
    return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.psychoGrab && shots::Active()
           && shots::Data().onGrab;
}

static void Reset() {
    g = State();
    g_thrown.shot = nullptr;
}

// The badnik's Animator: the first 8-aligned spot after the entity header shaped like one
static bool LooksLikeAnimator(const uint8* at) {
    if (!Readable(at, sizeof(Animator)))
        return false;
    const Animator* a = (const Animator*)at;
    if (!a->frames || a->frameCount < 1 || a->frameCount > 256 || a->frameID < 0 || a->frameID >= a->frameCount
        || a->loopIndex >= a->frameCount || a->animationID < 0 || a->animationID > 1024)
        return false;
    const SpriteFrame* f = (const SpriteFrame*)a->frames;
    if (!Readable(f, sizeof(SpriteFrame) * a->frameCount))
        return false;
    const GameSpriteFrame& fr = f[a->frameID].frame;
    return fr.width >= 4 && fr.width <= 256 && fr.height >= 4 && fr.height <= 256 && fr.pivotX <= 0 && fr.pivotY <= 0
           && fr.pivotX >= -256 && fr.pivotY >= -256;
}
static bool FindAnimator(Entity* e, Animator* out) {
    const uint8* base = (const uint8*)e;
    for (size_t off = (sizeof(Entity) + 7) & ~(size_t)7; off <= 0x200; off += 8) {
        if (LooksLikeAnimator(base + off)) {
            *out = *(const Animator*)(base + off);
            static int logs = 0;
            if (logs++ < 20)
                Log("psychokinesis: %s's likeness at +0x%x (animation %d, frame %d of %d)", shots::ClassName(e->classID),
                    (unsigned)off, out->animationID, out->frameID, out->frameCount);
            return true;
        }
    }
    Log("psychokinesis: %s: no likeness found (the orb goes instead)", shots::ClassName(e->classID));
    return false;
}

// Player_CheckBadnikTouch (the shots' hook), player 1 only: SEEK looks, CATCH touches the target (true)
static bool Touch(EntityPlayer* p, Entity* e) {
    if (!p || !e || (g.phase != SEEK && g.phase != CATCH) || !On() || RSDK->GetEntitySlot(p) != 0)
        return false;
    if (g.phase == CATCH) {
        if (e != g.target || e->classID != g.cls || g.touched)
            return false;
        g.touched = true;
        g.haveAnim = FindAnimator(e, &g.anim);
        return true;
    }
    if (shots::Ours(e) || !e->visible || !jugg::Enemy(e) || (jugg::g_class[e->classID] & jugg::JUGG_BOSS))
        return false;
    Vector2 range = {0, 0};
    if (!RSDK->CheckOnScreen(e, &range))
        return false;
    const ExtraAbilities& c = Extra(g_character).abilities;
    int dir = (p->direction & 1) ? -1 : 1;
    int dx = ((e->position.x - p->position.x) >> 16) * dir, dy = (e->position.y - p->position.y) >> 16;
    if (dx < -c.psychoBehind || dx > c.psychoReach || std::abs(dy) > c.psychoHeight)
        return false;
    int64_t d = std::abs(dx) + std::abs(dy);
    if (g.best < 0 || d < g.best) {
        g.best = d;
        g.target = e;
        g.cls = e->classID;
    }
    return false;
}

static bool Catching(EntityPlayer* p, Entity* e) {
    return g.phase == CATCH && g.touched && e && e == g.target && p && RSDK->GetEntitySlot(p) == 0;
}

// Player_CheckBadnikBreak on the target: broken as his attack (the jump's animation for the call), his speed and pose
// kept (no bounce off it)
static bool Breaks(EntityPlayer* p, Entity* e, bool32 destroy, bool32* result) {
    if (!Catching(p, e) || !shots::g_break)
        return false;
    int16 anim = p->animator.animationID;
    Vector2 vel = p->velocity;
    int32 ground = p->groundVel;
    p->animator.animationID = ANI_JUMP;
    *result = shots::g_break(p, e, destroy);
    p->animator.animationID = anim;
    p->velocity = vel;
    p->groundVel = ground;
    g.caught = *result;
    Log("psychokinesis: caught %s (slot %d): %s", shots::ClassName(g.cls), RSDK->GetEntitySlot(e),
        *result ? "broken" : "not broken");
    return true;
}

// The target hits him as a boss, or hurts him: it isn't a badnik to catch (refused: no hit, no hurt)
static bool Refuses(EntityPlayer* p, Entity* e) {
    if (!Catching(p, e))
        return false;
    if (!g.refused)
        Log("psychokinesis: %s can't be caught (not a badnik)", shots::ClassName(g.cls));
    g.refused = true;
    return true;
}

// The melee's Y (Abilities): while Psychokinesis is on, the Psychic Wave goes only when a catch came to nothing
static bool WaveY(EntityPlayer* p) {
    if (!On())
        return YPressed(p);
    if (!g.wave)
        return false;
    g.wave = false;
    return true;
}

static void Throw(EntityPlayer* p) {
    shots::g_lastThrown = nullptr;
    if (!shots::Throw(p, false) || !shots::g_lastThrown) {
        Log("psychokinesis: the throw failed");
        return;
    }
    g_thrown.shot = g.haveAnim ? shots::g_lastThrown : nullptr;
    g_thrown.anim = g.anim;
    g_thrown.flyRight = shots::g_lastThrown->velocity.x >= 0;
    Log("psychokinesis: thrown%s", g.haveAnim ? "" : " (the orb)");
}

// Each frame (Abilities, before the melee)
static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!On()) {
        if (g.phase != IDLE)
            g = State();
        return;
    }
    Vector2 last = g.last;
    g.last = p->position;
    if (std::abs(p->position.x - last.x) > (64 << 16) || std::abs(p->position.y - last.y) > (64 << 16))
        g.phase = IDLE;  // (a new stage, a respawn, a warp)
    switch (g.phase) {
        case IDLE:
            if (YPressed(p) && !Hurt(p) && !Held(p) && g_ab.shot == 0 && g_ab.cooldown == 0
                && shots::OutCount() < shots::Data().maxAlive) {
                g = State();
                g.last = p->position;
                g.phase = SEEK;
            }
            return;
        case SEEK:  // (the badniks looked this frame, after his update)
            if (g.target) {
                g.phase = CATCH;
            } else {
                g.phase = IDLE;
                g.wave = true;
            }
            return;
        case CATCH:
            if (g.caught && !Hurt(p)) {
                g.phase = HOLD;
                g.t = 0;
                if (c.psychoSound)
                    PlaySound(c.psychoSound);
                break;
            }
            if (!g.touched)
                Log("psychokinesis: the target was gone");
            g.phase = IDLE;
            g.wave = !g.caught;  // (caught but hurt meanwhile: nothing)
            return;
        case CARRY:  // playing on with it: Y throws
            if (Hurt(p)) {
                g.phase = IDLE;
                Log("psychokinesis: hit: the carried badnik is lost");
                return;
            }
            if (g.haveAnim)
                RSDK->ProcessAnimation(&g.anim);
            g.t++;
            if (YPressed(p) && !Held(p) && shots::OutCount() < shots::Data().maxAlive) {
                g.phase = THROW;
                g.t = 0;
                break;
            }
            return;
        default:
            break;
    }
    // HOLD (the catch) and THROW: the pose, held still
    if (Hurt(p) || Held(p)) {
        if (g.phase == THROW && !Hurt(p))  // (an object took him: still carrying it)
            g.phase = CARRY;
        else
            g.phase = IDLE;
        return;
    }
    if (g.haveAnim)
        RSDK->ProcessAnimation(&g.anim);
    int ticks = std::max(1, c.psychoTicks);
    bool throwing = g.phase == THROW;
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK_UP, air, g.t == 0);
    int top = std::max(1, (int)p->animator.frameCount) - 1;
    p->animator.frameID = throwing ? top - std::min(g.t / ticks, top) : std::min(g.t / ticks, top);  // (the throw: the
    p->animator.timer = 0;                                                                              // orb goes back out)
    if (air) {
        p->velocity.x = 0;
        p->velocity.y = -Gravity(p);  // (the air state's gravity taken off in advance: held still)
    } else {
        p->groundVel = 0;
        p->velocity.x = 0;
    }
    if (++g.t < (throwing ? c.psychoThrow : c.psychoHold))
        return;
    if (throwing) {
        Throw(p);
        g.phase = IDLE;
        g_ab.cooldown = c.shotCooldown;  // (the melee's cooldown after it too)
    } else {
        g.phase = CARRY;
        g.t = 0;
        Log("psychokinesis: carrying it");
    }
    if (air)
        BackToJump(p);
    else
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// After his own draw (shots::PlayerDraw, player 1): the badnik he carries (or holds while catching / throwing), beside
// his hand the way he faces, bobbing; the orb when it had no likeness
static void DrawCarried() {
    if ((g.phase != CARRY && g.phase != HOLD && g.phase != THROW) || !On())
        return;
    Entity* self = SCENE_INFO->entity;
    if (!self || !Readable(self, sizeof(Entity)))
        return;
    auto* p = (EntityPlayer*)self;
    bool left = p->direction & 1;
    int bob = g.phase == CARRY ? ((g.t >> 3) & 1 ? CARRY_BOB : -CARRY_BOB) : 0;
    Vector2 at = {p->position.x + ((left ? -CARRY_X : CARRY_X) << 16), p->position.y + ((CARRY_Y + bob) << 16)};
    Animator orb{};
    const Animator* a = &g.anim;
    if (!g.haveAnim) {
        RSDK->SetSpriteAnimation(shots::g_frames, 0, &orb, true, 0);
        a = &orb;
    }
    uint8 dir = self->direction, fx = self->drawFX, ink = self->inkEffect;
    int32 rotation = self->rotation;
    self->direction = left ? 0 : 1;  // (the games' badniks face left: flipped facing right)
    self->drawFX = 1;                // FX_FLIP
    self->inkEffect = 0;
    self->rotation = 0;
    RSDK->DrawSprite((Animator*)a, &at, false);
    self->direction = dir;
    self->drawFX = fx;
    self->inkEffect = ink;
    self->rotation = rotation;
}

// SuperHammer's draw (the shots' hook): the shot carrying a likeness draws it, facing the way it flies (the games'
// badniks are drawn facing left: flipped flying right)
static bool Draw(Entity* shot) {
    if (!g_thrown.shot || shot != g_thrown.shot || !On())
        return false;
    uint8 dir = shot->direction, fx = shot->drawFX;
    shot->direction = g_thrown.flyRight ? 1 : 0;
    shot->drawFX = 1;  // FX_FLIP
    RSDK->DrawSprite(&g_thrown.anim, nullptr, false);
    shot->direction = dir;
    shot->drawFX = fx;
    return true;
}

static void Animate(Entity* shot) {
    if (g_thrown.shot && shot == g_thrown.shot)
        RSDK->ProcessAnimation(&g_thrown.anim);
}
}  // namespace psycho
