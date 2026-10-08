// NoSwapMania: Silver's Psychokinesis (abilities.py psycho_grab), the S3&K DLL's (native/src/PsychoGrab.h) on Mania's
// own ways. The user's design (2026-09-30): Y with a badnik in reach catches it instead of the Psychic Wave; it's
// destroyed as a hit would destroy it (the game's own badnik break: explosion, animal, score; his speed and pose kept),
// he holds its likeness for psychoHold frames (ability slot 45: his hand out, the orb forming), then CARRIES it beside his
// hand as he plays on; Y again: psychoThrow frames of the pose (played back down), then it's thrown as his shot ("input"
// "grab": straight ahead, piercing, the shots' stand-in hits), drawn as the badnik was (its animation copied, still
// playing). A hit while carrying loses it; so does a stage change. Nothing caught: the Psychic Wave (the melee) at once.
//   - Which badniks: ManiaPsychoTable.h (tools/gen_mania_psycho.py): single-object badniks only, with the offsets of the
//     Animators their Draw shows, from the decompilation's headers. Bosses, boss parts, projectiles, multi-part or
//     orbiting enemies and ones that grab the player aren't there.
//   - The catch (Y, from OnUpdate): the catchable objects on screen in reach (psychoReach px ahead, psychoBehind behind,
//     psychoHeight above or below), nearest first (at most PSY_TRIES): each one's own update runs once more with player 1
//     standing in on it (the shots' StandInAt: a 32x32 box, the attack, invincible), and its own code decides: a badnik
//     break (his score or score chain moved) is a catch; anything else (a projectile of that class, a badnik that can't
//     be hurt now) is refused, and the next one is tried. Its Animators are copied just before.
//   - The likeness: those Animators, drawn in the class's order at one spot, facing his way (the games' badniks face
//     left: flipped facing right); none valid: the shot's own art (the orb).
// Included once, by NoSwapMania.c (after ManiaMelee.h).
#ifndef MANIA_PSYCHO_H
#define MANIA_PSYCHO_H

#include "ManiaPsychoTable.h"

_Static_assert(sizeof(Animator) == PSYCHO_ANIMATOR_SIZE, "Animator differs from the decompilation's");

enum { PSY_IDLE, PSY_HOLD, PSY_CARRY, PSY_THROW };
#define PSY_CARRY_X (22) // the likeness beside his hand, bobbing 2 px up and down
#define PSY_CARRY_Y (-6)
#define PSY_BOB     (2)
#define PSY_TRIES   (4)  // the nearest few in reach (a projectile of a badnik's class is refused: the next is tried)
#define PSY_BOX     (16) // the stand-in's box, round the badnik

typedef struct {
    int32 count;
    Animator part[PSYCHO_PARTS_MAX];
    uint8 alphaMask; // parts drawn with INK_ALPHA (at alpha)
    int32 alpha;
} Likeness;

static bool32 g_psyOn = false;
static uint8 g_psyClass[CLASS_MAX]; // this stage's class IDs -> PSYCHO_CLASSES index + 1 (0: not catchable)
static int32 g_animPsy = -1;        // the Psychic Hold pose (ability slot 45)
static uint16 g_psySfx = 0xFFFF;
static struct {
    int32 phase, t;
    bool32 wave; // the Psychic Wave's turn (PsychoWave): nothing was caught
    Likeness look;
    Vector2 last;
} g_psy;
static struct {
    EntityNoSwapShot *shot; // the shot drawn as it (NULL: none)
    Likeness look;
    bool32 flyRight;
} g_psyThrown;
static EngineSpriteFrame g_psyFrame;
static Animator g_psyBox;

static bool32 PsyYPressed(EntityPlayer *p, bool32 transformed)
{
    InputState *key = ControllerInfo && p->controllerID >= 0 && p->controllerID <= PLAYER_COUNT ? &ControllerInfo[p->controllerID].keyY : NULL;
    return key && key->press && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled && !transformed;
}

// The melee's Y (MeleeFrame): with Psychokinesis, the Psychic Wave goes only when a catch came to nothing
static bool32 PsychoWave(bool32 press)
{
    if (!g_psyOn)
        return press;
    bool32 wave = g_psy.wave;
    g_psy.wave  = false;
    return wave;
}

// Its Animators, as its Draw shows them (a part that doesn't look like a playing animation is left out)
static void TakeLikeness(Entity *e, const PsychoClass *pc, Likeness *out)
{
    memset(out, 0, sizeof(*out));
    out->alpha = e->alpha;
    for (int32 i = 0; i < pc->count && i < PSYCHO_PARTS_MAX; ++i) {
        const Animator *a = (const Animator *)((const uint8 *)e + pc->offset[i]);
        if (!a->frames || a->frameCount < 1 || a->frameCount > 1024 || a->frameID < 0 || a->frameID >= a->frameCount)
            continue;
        if (pc->alpha >> i & 1)
            out->alphaMask |= (uint8)(1 << out->count);
        out->part[out->count++] = *a;
    }
}

static void AnimateLikeness(Likeness *look)
{
    for (int32 i = 0; i < look->count; ++i) RSDK.ProcessAnimation(&look->part[i]);
}

// Draws it as `self` (the entity drawing now) at pos (NULL: self's position), facing right or left
static void DrawLikeness(Entity *self, Likeness *look, Vector2 *pos, bool32 faceRight)
{
    uint8 dir = self->direction, fx = self->drawFX, ink = self->inkEffect;
    int32 alpha = self->alpha, rotation = self->rotation;
    self->direction = faceRight ? FLIP_X : FLIP_NONE;
    self->drawFX    = FX_FLIP;
    self->rotation  = 0;
    for (int32 i = 0; i < look->count; ++i) {
        self->inkEffect = (look->alphaMask >> i & 1) ? INK_ALPHA : INK_NONE;
        self->alpha     = look->alpha;
        RSDK.DrawSprite(&look->part[i], pos, false);
    }
    self->direction = dir;
    self->drawFX    = fx;
    self->inkEffect = ink;
    self->alpha     = alpha;
    self->rotation  = rotation;
}

// One catch attempt: its own update with player 1 standing in on it; true: broken as a badnik (caught)
static bool32 PsychoTry(EntityPlayer *p, Entity *e)
{
    uint16 cls             = e->classID;
    const PsychoClass *pc  = &PSYCHO_CLASSES[g_psyClass[cls] - 1];
    int32 slot             = RSDK.GetEntitySlot(e);
    Likeness look;
    TakeLikeness(e, pc, &look);
    int32 score = p->score, bonus = p->scoreBonus;
    Animator jump;
    const Animator *box = &g_psyBox;
    if (!g_engineFrameOK) { // (the fallback: his own jump frame's box)
        memset(&jump, 0, sizeof(jump));
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_JUMP, &jump, true, 0);
        box = &jump;
    }
    // (from OnUpdate, after the entity loop: the badnik is "self" for its update, as in the loop)
    Entity *prevEntity    = SceneInfo->entity;
    int32 prevSlot        = SceneInfo->entitySlot;
    SceneInfo->entity     = e;
    SceneInfo->entitySlot = (uint16)slot;
    bool32 hit = StandInAt(e, e->position, box, p->direction, p->collisionPlane, p);
    SceneInfo->entity     = prevEntity;
    SceneInfo->entitySlot = (uint16)prevSlot;
    bool32 caught = p->score != score || p->scoreBonus != bonus || (hit && e->classID != cls);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: %s (slot %d) %s; likeness %d part(s)", pc->name, slot,
                  caught ? "caught" : "can't be caught now", look.count);
    if (caught)
        g_psy.look = look;
    return caught;
}

// Y: the catchable ones in reach on screen, nearest first
static bool32 PsychoCatch(EntityPlayer *p)
{
    const Abilities *c = &g_cur->ab;
    int32 dir          = (p->direction & FLIP_X) ? -1 : 1;
    Entity *best[PSY_TRIES];
    int32 dist[PSY_TRIES], n = 0;
    for (int32 slot = RESERVE_ENTITY_COUNT; slot < ENTITY_COUNT; ++slot) {
        Entity *e = (Entity *)RSDK.GetEntity(slot);
        if (!e || e->classID == 0 || e->classID >= CLASS_MAX || !g_psyClass[e->classID] || !e->visible || e->active == ACTIVE_DISABLED)
            continue;
        int32 dx = ((e->position.x - p->position.x) >> 16) * dir, dy = (e->position.y - p->position.y) >> 16;
        if (dx < -c->psychoBehind || dx > c->psychoReach || Abs(dy) > c->psychoHeight)
            continue;
        Vector2 range = { 0, 0 };
        if (!RSDK.CheckOnScreen(e, &range))
            continue;
        int32 d = Abs(dx) + Abs(dy), k = n < PSY_TRIES ? n++ : PSY_TRIES;
        if (k == PSY_TRIES && d >= dist[PSY_TRIES - 1])
            continue;
        if (k == PSY_TRIES)
            k = PSY_TRIES - 1;
        for (; k > 0 && dist[k - 1] > d; --k) {
            best[k] = best[k - 1];
            dist[k] = dist[k - 1];
        }
        best[k] = e;
        dist[k] = d;
    }
    for (int32 i = 0; i < n; ++i)
        if (best[i]->classID && g_psyClass[best[i]->classID] && PsychoTry(p, best[i]))
            return true;
    return false;
}

static void PsychoThrow(EntityPlayer *p)
{
    g_psyThrown.shot = NULL;
    if (!Throw(p, false, 1, 0)) {
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: the throw failed");
        return;
    }
    EntityNoSwapShot *s = NULL;
    for (int32 k = 0; k < SHOT_OUT_MAX; ++k)
        if (g_out[k] && IsShot(g_out[k]) && g_out[k]->timer == 0)
            s = g_out[k]; // (the one just thrown: the others have flown a frame at least)
    if (s && g_psy.look.count > 0) {
        g_psyThrown.shot     = s;
        g_psyThrown.look     = g_psy.look;
        g_psyThrown.flyRight = s->velocity.x >= 0;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: thrown%s", g_psyThrown.shot ? "" : " (the orb)");
}

// Player 1's frame (MoreUpdate: before the shots and the melee)
static void PsychoUpdate(EntityPlayer *p, bool32 transformed)
{
    if (!g_psyOn)
        return;
    const Abilities *c = &g_cur->ab;
    bool32 air         = !p->onGround;
    if (g_psyThrown.shot) {
        if (IsShot(g_psyThrown.shot))
            AnimateLikeness(&g_psyThrown.look);
        else
            g_psyThrown.shot = NULL;
    }
    Vector2 last = g_psy.last;
    g_psy.last   = p->position;
    if (g_psy.phase != PSY_IDLE && (Abs(p->position.x - last.x) > (64 << 16) || Abs(p->position.y - last.y) > (64 << 16))) {
        g_psy.phase = PSY_IDLE; // (a respawn, a warp)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: a warp: the carried badnik is lost");
    }
    switch (g_psy.phase) {
        case PSY_IDLE:
            if (PsyYPressed(p, transformed) && !Hurt(p) && Free(p) && g_meleeLeft == 0 && g_meleeCooldown == 0
                && OutCount(0) < g_cur->shot.maxAlive) {
                if (PsychoCatch(p)) {
                    g_psy.phase = PSY_HOLD;
                    g_psy.t     = 0;
                    if (g_psySfx != 0xFFFF)
                        RSDK.PlaySfx(g_psySfx, false, 255);
                    break;
                }
                g_psy.wave = true; // (nothing caught: the Psychic Wave, this frame)
            }
            return;
        case PSY_CARRY: // playing on with it: Y throws
            if (Hurt(p)) {
                g_psy.phase = PSY_IDLE;
                RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: hit: the carried badnik is lost");
                return;
            }
            AnimateLikeness(&g_psy.look);
            g_psy.t++;
            if (PsyYPressed(p, transformed) && Free(p) && OutCount(0) < g_cur->shot.maxAlive) {
                g_psy.phase = PSY_THROW;
                g_psy.t     = 0;
                break;
            }
            return;
        default: break;
    }
    // the catch (HOLD) and the throw: the pose, held still
    if (Hurt(p) || !Free(p)) {
        g_psy.phase = g_psy.phase == PSY_THROW && !Hurt(p) ? PSY_CARRY : PSY_IDLE; // (an object took him: still carrying it)
        if (Showing(p, g_animPsy))
            RSDK.SetSpriteAnimation(g_extraFrames, air ? ANI_JUMP : ANI_IDLE, &p->animator, true, 0);
        return;
    }
    AnimateLikeness(&g_psy.look);
    int32 ticks     = c->psychoTicks > 1 ? c->psychoTicks : 1;
    bool32 throwing = g_psy.phase == PSY_THROW;
    Show(p, g_animPsy, air, g_psy.t == 0);
    int32 top = (p->animator.frameCount > 1 ? p->animator.frameCount : 1) - 1;
    int32 at  = g_psy.t / ticks < top ? g_psy.t / ticks : top;
    p->animator.frameID = throwing ? top - at : at; // (the throw: the orb goes back out)
    p->animator.timer   = 0;
    p->animator.speed   = 0;
    if (air) {
        p->velocity.x = 0;
        p->velocity.y = -p->gravityStrength; // (the air state's gravity taken off in advance: held still)
    }
    else {
        p->groundVel  = 0;
        p->velocity.x = 0;
    }
    if (++g_psy.t < (throwing ? c->psychoThrow : c->psychoHold))
        return;
    if (throwing) {
        PsychoThrow(p);
        g_psy.phase   = PSY_IDLE;
        g_meleeCooldown = c->shotCooldown; // (the melee's cooldown after it too)
    }
    else {
        g_psy.phase = PSY_CARRY;
        g_psy.t     = 0;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: carrying it");
    }
    if (air)
        BackToJump(p);
    else
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// After his own draw (MoreDraw, player 1): the badnik he holds or carries, beside his hand the way he faces, bobbing
// while carried; the orb when it had no likeness
static void PsychoDrawCarried(EntityPlayer *p)
{
    if (!g_psyOn || g_psy.phase == PSY_IDLE)
        return;
    bool32 left = (p->direction & FLIP_X) != 0;
    int32 bob   = g_psy.phase == PSY_CARRY ? ((g_psy.t >> 3) & 1 ? PSY_BOB : -PSY_BOB) : 0;
    Vector2 at  = { p->position.x + ((left ? -PSY_CARRY_X : PSY_CARRY_X) << 16), p->position.y + ((PSY_CARRY_Y + bob) << 16) };
    if (g_psy.look.count > 0) {
        DrawLikeness((Entity *)p, &g_psy.look, &at, !left);
        return;
    }
    if (g_shotFrames == 0xFFFF)
        return;
    Likeness orb;
    memset(&orb, 0, sizeof(orb));
    RSDK.SetSpriteAnimation(g_shotFrames, 0, &orb.part[0], true, 0);
    orb.count = 1;
    DrawLikeness((Entity *)p, &orb, &at, !left);
}

// The shot's draw (Shot_Draw): the one carrying a likeness draws it, facing the way it flies
static bool32 PsychoShotDraw(EntityNoSwapShot *shot)
{
    if (!g_psyOn || !g_psyThrown.shot || shot != g_psyThrown.shot)
        return false;
    DrawLikeness((Entity *)shot, &g_psyThrown.look, NULL, g_psyThrown.flyRight);
    return true;
}

// Stage load (MoreStageLoad, after the shots and the melee): on for an extra with psycho_grab, its grab shot, the hold
// pose and the hit classes wrapped
static void PsychoStageLoad(void)
{
    memset(&g_psy, 0, sizeof(g_psy));
    memset(&g_psyThrown, 0, sizeof(g_psyThrown));
    memset(g_psyClass, 0, sizeof(g_psyClass));
    g_psyOn = false;
    if (!g_cur || !g_cur->ab.psychoGrab)
        return;
    g_animPsy = HasAnim(g_cur->animBase + 3);
    g_psyOn   = g_shotOn && g_hitsOn && g_cur->shot.onGrab && g_animPsy >= 0 && Player_State_Ground_;
    int32 found = 0;
    for (size_t i = 0; i < PSYCHO_CLASS_COUNT; ++i) {
        uint16 id = RSDK.FindObject(PSYCHO_CLASSES[i].name);
        if (id && id < CLASS_MAX && g_hitKind[id] == HIT_BADNIK) { // (wrapped as a hit class: Mod.Super reaches its update)
            g_psyClass[id] = (uint8)(i + 1);
            found++;
        }
    }
    g_psySfx = g_cur->more.psychoSound[0] ? RSDK.GetSfx(g_cur->more.psychoSound) : 0xFFFF;
    memset(&g_psyFrame, 0, sizeof(g_psyFrame));
    g_psyFrame.hitboxCount = 1;
    for (int32 i = 0; i < 8; ++i) {
        g_psyFrame.hitboxes[i].left = g_psyFrame.hitboxes[i].top = -PSY_BOX;
        g_psyFrame.hitboxes[i].right = g_psyFrame.hitboxes[i].bottom = PSY_BOX;
    }
    memset(&g_psyBox, 0, sizeof(g_psyBox));
    g_psyBox.frames      = (SpriteFrame *)&g_psyFrame;
    g_psyBox.frameCount  = 1;
    g_psyBox.animationID = ANI_JUMP;
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "psychokinesis: %s (shot %d, hits %d, grab %d, pose %d), %d catchable classes here, sound %s (%d)",
                  g_psyOn ? "on" : "OFF", g_shotOn, g_hitsOn, g_cur->shot.onGrab, g_animPsy, found, g_cur->more.psychoSound, g_psySfx);
}

#endif // MANIA_PSYCHO_H
