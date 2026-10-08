// NoSwapMania's breakable walls and fire immunity: objects whose update decides by player 1's character ID, speed or
// shield are wrapped (Mod.RegisterObject by name, the game's own update through Mod.Super), as the S3&K DLL does with its
// BreakableWall / fire hooks. Included once, by NoSwapMania.c (after "shots" and the melee).
//
// Walls: Mania's BreakableWall (walls, floors, burrow floors, ceilings), LRZRockPile's walls and AIZRockPile (the decomp's
// SonicMania/Objects: they break for Knuckles, for a fast rolling player from the side, for the jump ball from above...).
//   - breaks_walls (abilities.py: Vector, Heavy, Omega): while one of those updates, player 1 shows Knuckles' character ID,
//     so walking into them breaks them as they do for Knuckles; the real ID straight after (not in a pose whose ID means
//     Knuckles' glide there: Sonic's Peel Out shares its number);
//   - shot_breaks_walls (Gamma's Arm Cannon): a shot of his flying into one breaks it. Each frame, before a shot moves (so
//     before the wall's own tiles stop it), every such object in reach gets a stand-in update (as the shots' hits,
//     "shots": player 1 put on the shot's leading edge with the shot's hitbox, posed as the object needs, then put back
//     exactly, keeping only score): a wall from the side as a fast roll on the ground (0x60000, the jump ball: what Sonic
//     breaks it with), a floor from above as the falling jump ball, a ceiling from below as a rising one; with
//     breaks_walls too, as Knuckles. So only what Sonic (or, for breaks_walls, Knuckles) can break breaks: Knuckles-only
//     walls stay for a shot of an extra without breaks_walls. The object's own code breaks it (tiles, debris, sound,
//     score); the shot ends there (a piercing one flies on).
// Fire (abilities.py fire_immune: Blaze): the fire shield's immunity, all the time and nothing else of it. Mania asks
// Player_ElementHurt(player, entity, SHIELD_FIRE) or reads the shield itself; the objects that only hurt that way (flames,
// fireballs, lava falls and geysers, burning logs, the spike log, the LRZ lava tiles in LRZ1Setup / LRZ2Setup's static
// update...) run with player 1's shield reading the fire shield, put back straight after. Not the badniks and bosses
// with fire among other attacks (Redz, Sol, HeavyRider, Gachapandora, WeatherMobile, the Phantom Ruby gunners,
// Drillerdroid): there a real hit meanwhile would take the pretend shield instead of rings. Not the generic Projectile
// either (any shield but the blue deflects them). Nor OOZSetup (a fire shield sets the oil alight).
#ifndef MANIA_WALLS_H
#define MANIA_WALLS_H

#define FIRE_SHIELD   (3)       // Mania's ShieldTypes: SHIELD_FIRE
#define ROLL_SPEED    (0x60000) // the side stand-in's ground speed (BreakableWall wants 0x48000)
#define WALL_REACH    (160)     // px: walls whose position is further from a shot aren't tried (the biggest are 8 x 8 tiles)
#define WALL_TRY_MAX  (32)

enum { WALL_NONE, WALL_BREAKABLE, WALL_LRZ, WALL_AIZ };
enum { POSE_SIDE, POSE_DOWN, POSE_UP };

// (EntityBreakableWall: ManiaPlayer.h, checked by check_layout.sh)
// LRZRockPile's state (its first field, as every object with a state machine)
typedef struct {
    RSDK_ENTITY
    void (*state)(void);
} EntityWithState;

static const struct {
    const char *name;
    uint8 kind;
} WALL_CLASSES[] = { { "BreakableWall", WALL_BREAKABLE }, { "LRZRockPile", WALL_LRZ }, { "AIZRockPile", WALL_AIZ } };
#define WALL_CLASS_COUNT (sizeof(WALL_CLASSES) / sizeof(WALL_CLASSES[0]))

// the fire hazards (update) and the LRZ lava tiles (static update)
static const char *const FIRE_CLASSES[] = { "FlameSpring", "BurningLog", "Fireball",   "Flamethrower", "LavaFall",  "LavaGeyser",
                                            "LRZFireball", "PhantomMissile", "CrashTest", "GasPlatform", "SpikeLog" };
#define FIRE_CLASS_COUNT (sizeof(FIRE_CLASSES) / sizeof(FIRE_CLASSES[0]))

static bool32 g_wallsWrapped = false, g_fireWrapped = false;
static bool32 g_wallsOn = false; // this stage: the extra breaks walls (walking or with shots)
static bool32 g_fireOn  = false; // ... is fire immune
static uint16 g_wallClass[WALL_CLASS_COUNT]; // this stage's IDs (0: not here)
static uint16 g_lrz1Setup = 0, g_lrz2Setup = 0;
static void (*BreakableWall_State_Wall_)(void), (*BreakableWall_State_Floor_)(void), (*BreakableWall_State_BurrowFloor_)(void);
static void (*BreakableWall_State_BurrowFloorUp_)(void), (*BreakableWall_State_Ceiling_)(void), (*LRZRockPile_State_Wall_)(void);

static uint8 WallKind(uint16 cls)
{
    for (size_t i = 0; i < WALL_CLASS_COUNT; ++i)
        if (cls && g_wallClass[i] == cls)
            return WALL_CLASSES[i].kind;
    return WALL_NONE;
}

// ------------------------------------------------------------------------------------------------ breaks_walls
static bool32 CrossAsKnuckles(EntityPlayer *p); // (ManiaCross.h: Ecco's charge ram)
static bool32 NoStompAsKnuckles(EntityPlayer *p); // (ManiaNoStomp.h: the Slide and the roll)
static void WallUpdate(void)
{
    Entity *self    = SceneInfo->entity;
    EntityPlayer *p = Player ? (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1) : NULL;
    int32 anim      = p ? p->animator.animationID : 0;
    bool32 knux     = g_wallsOn && g_cur && (g_cur->ab.breaksWalls || CrossAsKnuckles(p) || NoStompAsKnuckles(p)) && IsExtra(p) && anim != ANI_ABILITY_1
                  && anim != ANI_ABILITY_4;
    if (knux)
        p->characterID = ID_KNUCKLES;
    Mod.Super(self->classID, SUPER_UPDATE, NULL);
    if (knux && p->characterID == ID_KNUCKLES)
        p->characterID = g_hostID; // (its host back: ManiaHost.h)
}

// ------------------------------------------------------------------------------------------------ shot_breaks_walls
// Player 1 stands in for the shot at `at`, posed for `pose`, during the wall's own update (called from the shot's update:
// the scene's entity is the wall meanwhile). True: it broke (gone, moved: a burrow floor losing a row, or its state or
// visibility changed: LRZRockPile's broken state)
static bool32 WallStandIn(Entity *w, Vector2 at, const EntityNoSwapShot *shot, int32 pose, EntityPlayer *p)
{
    uint16 cls     = w->classID;
    Vector2 wpos   = w->position;
    bool32 visible = w->visible;
    void *state    = WallKind(cls) == WALL_AIZ ? NULL : (void *)((EntityWithState *)w)->state;
    int32 dir      = shot->velocity.x < 0 ? -1 : shot->velocity.x > 0 ? 1 : ((shot->direction & FLIP_X) ? -1 : 1);

    EntityPlayer saved;
    memcpy(&saved, p, sizeof(saved));
    p->position             = at;
    p->direction            = dir < 0 ? FLIP_X : FLIP_NONE;
    p->animator             = shot->animator;
    p->animator.animationID = ANI_JUMP;
    p->invincibleTimer      = STANDIN_INV;
    p->outerbox             = NULL;
    p->innerbox             = NULL;
    p->isGhost              = false;
    p->sidekick             = false;
    p->collisionPlane       = shot->collisionPlane;
    p->collisionMode        = CMODE_FLOOR;
    p->angle                = 0;
    if (g_cur->ab.breaksWalls)
        p->characterID = ID_KNUCKLES;
    if (pose == POSE_SIDE) { // a fast roll on the ground
        p->onGround      = true;
        p->groundedStore = true;
        p->groundVel     = dir * ROLL_SPEED;
        p->velocity.x    = p->groundVel;
        p->velocity.y    = 0;
    }
    else { // the jump ball falling onto it, or rising into it
        p->onGround      = false;
        p->groundedStore = false;
        p->groundVel     = 0;
        p->velocity.x    = 0;
        p->velocity.y    = pose == POSE_DOWN ? 0x40000 : -0x40000;
    }

    Entity *prevEntity    = SceneInfo->entity;
    int32 prevSlot        = SceneInfo->entitySlot;
    SceneInfo->entity     = w;
    SceneInfo->entitySlot = RSDK.GetEntitySlot(w);
    Mod.Super(cls, SUPER_UPDATE, NULL);
    SceneInfo->entity     = prevEntity;
    SceneInfo->entitySlot = prevSlot;

    bool32 broke = w->classID != cls || w->position.x != wpos.x || w->position.y != wpos.y || w->visible != visible
                   || (state && (void *)((EntityWithState *)w)->state != state);
    int32 score = p->score, score1UP = p->score1UP, lives = p->lives, scoreBonus = p->scoreBonus;
    memcpy(p, &saved, sizeof(saved));
    p->score      = score;
    p->score1UP   = score1UP;
    p->lives      = lives;
    p->scoreBonus = scoreBonus;
    return broke;
}

// The pose a wall needs from this shot (-1: none: a floor from below, a ceiling from above, a broken piece)
static int32 WallPose(Entity *w, uint8 kind, int32 vx, int32 vy)
{
    int32 ax = Abs(vx), ay = Abs(vy);
    if (kind == WALL_AIZ)
        return ax >= ay ? POSE_SIDE : vy > 0 ? POSE_DOWN : -1;
    void *state = (void *)((EntityWithState *)w)->state;
    if (kind == WALL_LRZ)
        return state == (void *)LRZRockPile_State_Wall_ ? POSE_SIDE : -1;
    if (state == (void *)BreakableWall_State_Wall_)
        return POSE_SIDE;
    if (state == (void *)BreakableWall_State_Floor_ || state == (void *)BreakableWall_State_BurrowFloor_)
        return vy > 0 ? POSE_DOWN : -1;
    if (state == (void *)BreakableWall_State_Ceiling_ || state == (void *)BreakableWall_State_BurrowFloorUp_)
        return vy < 0 ? POSE_UP : -1;
    return -1; // (its falling tiles)
}

// A shot about to move (ShotUpdate): the breakable walls where its leading edge will be; true: one broke
static bool32 ShotBreakWalls(EntityNoSwapShot *e, const ShotData *s)
{
    if (!g_wallsOn || !g_cur || !g_cur->shotBreaksWalls)
        return false;
    EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1);
    if (!IsExtra(p) || p->state == Player_State_Death_ || p->state == Player_State_Drown_)
        return false;
    int32 vx = e->velocity.x, vy = e->velocity.y, lead = (s->radius + 4) << 16;
    Vector2 at = e->position;
    at.x += vx + (vx > 0 ? lead : vx < 0 ? -lead : 0);
    at.y += vy + (vy > 0 ? lead : vy < 0 ? -lead : 0);
    Hitbox *box = RSDK.GetHitbox(&e->animator, 0);

    // (collected first, the whole list walked: the engine's entity loop mustn't be left half way)
    Entity *tries[WALL_TRY_MAX];
    int32 count = 0;
    for (size_t i = 0; i < WALL_CLASS_COUNT; ++i) {
        if (!g_wallClass[i])
            continue;
        Entity *w = NULL;
        while (RSDK.GetAllEntities(g_wallClass[i], (void **)&w)) {
            if (count >= WALL_TRY_MAX || Abs(w->position.x - at.x) > (WALL_REACH << 16) || Abs(w->position.y - at.y) > (WALL_REACH << 16))
                continue;
            if (WALL_CLASSES[i].kind == WALL_BREAKABLE && box) { // (its own box against the shot's, 2 px to spare)
                const EntityBreakableWall *b = (const EntityBreakableWall *)w;
                int32 wx = w->position.x >> 16, wy = w->position.y >> 16, sx = at.x >> 16, sy = at.y >> 16;
                if (sx + box->right + 2 < wx + b->hitbox.left || sx + box->left - 2 > wx + b->hitbox.right
                    || sy + box->bottom + 2 < wy + b->hitbox.top || sy + box->top - 2 > wy + b->hitbox.bottom)
                    continue;
            }
            tries[count++] = w;
        }
    }
    bool32 broke = false;
    for (int32 k = 0; k < count; ++k) {
        Entity *w  = tries[k];
        uint8 kind = WallKind(w->classID);
        int32 pose = kind ? WallPose(w, kind, vx, vy) : -1;
        if (pose < 0 || !WallStandIn(w, at, e, pose, p))
            continue;
        broke = true;
        static int32 logs = 0;
        if (logs++ < 40)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shot: broke a wall (class %d, %s)", w->classID,
                          pose == POSE_SIDE ? "side" : pose == POSE_DOWN ? "from above" : "from below");
    }
    return broke;
}

// ------------------------------------------------------------------------------------------------ fire_immune
static int32 g_fireSaved[PLAYER_COUNT];

static void FireShieldOn(void)
{
    for (int32 slot = 0; slot < PLAYER_COUNT; ++slot) {
        EntityPlayer *p   = (EntityPlayer *)RSDK.GetEntity(slot);
        g_fireSaved[slot] = -1;
        if (IsExtra(p) && p->shield != FIRE_SHIELD) {
            g_fireSaved[slot] = p->shield;
            p->shield         = FIRE_SHIELD;
        }
    }
}

static void FireShieldOff(void)
{
    for (int32 slot = 0; slot < PLAYER_COUNT; ++slot) {
        EntityPlayer *p = (EntityPlayer *)RSDK.GetEntity(slot);
        if (g_fireSaved[slot] >= 0 && p->shield == FIRE_SHIELD)
            p->shield = g_fireSaved[slot];
    }
}

static void FireUpdate(void)
{
    bool32 on = g_fireOn && Player;
    if (on)
        FireShieldOn();
    Mod.Super(SceneInfo->entity->classID, SUPER_UPDATE, NULL);
    if (on)
        FireShieldOff();
}

static void FireStatic(uint16 cls)
{
    bool32 on = g_fireOn && Player && cls;
    if (on)
        FireShieldOn();
    if (cls)
        Mod.Super(cls, SUPER_STATICUPDATE, NULL);
    if (on)
        FireShieldOff();
}
static void Lrz1StaticUpdate(void) { FireStatic(g_lrz1Setup); }
static void Lrz2StaticUpdate(void) { FireStatic(g_lrz2Setup); }

// ------------------------------------------------------------------------------------------------ stage load, link
static void WallsStageLoad(void)
{
    g_wallsOn = g_wallsWrapped && g_active && g_cur
                && (g_cur->ab.breaksWalls || g_cur->shotBreaksWalls || g_cur->more.cross.freeSwim || g_cur->ab.noStomp);
    g_fireOn  = g_fireWrapped && g_active && g_cur && g_cur->ab.fireImmune;
    for (size_t i = 0; i < WALL_CLASS_COUNT; ++i) g_wallClass[i] = g_wallsOn ? (uint16)RSDK.FindObject(WALL_CLASSES[i].name) : 0;
    g_lrz1Setup = g_fireOn ? (uint16)RSDK.FindObject("LRZ1Setup") : 0;
    g_lrz2Setup = g_fireOn ? (uint16)RSDK.FindObject("LRZ2Setup") : 0;
    if (g_wallsOn || g_fireOn)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "walls: %s%s (classes here: %d %d %d); fire immune: %s", g_cur->ab.breaksWalls ? "as Knuckles" : "",
                      g_cur->shotBreaksWalls ? " + shots" : "", g_wallClass[0], g_wallClass[1], g_wallClass[2], g_fireOn ? "yes" : "no");
}

static void LinkWalls(void)
{
    bool32 walls = false, fire = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        walls |= g_extras[i].ab.breaksWalls || g_extras[i].shotBreaksWalls || g_extras[i].more.cross.freeSwim // (Ecco's ram: ManiaCross.h)
                 || g_extras[i].ab.noStomp; // (no_stomp's Slide and roll: ManiaNoStomp.h)
        fire |= g_extras[i].ab.fireImmune != 0;
    }
    if (walls) {
        BreakableWall_State_Wall_          = Mod.GetPublicFunction(NULL, "BreakableWall_State_Wall");
        BreakableWall_State_Floor_         = Mod.GetPublicFunction(NULL, "BreakableWall_State_Floor");
        BreakableWall_State_BurrowFloor_   = Mod.GetPublicFunction(NULL, "BreakableWall_State_BurrowFloor");
        BreakableWall_State_BurrowFloorUp_ = Mod.GetPublicFunction(NULL, "BreakableWall_State_BurrowFloorUp");
        BreakableWall_State_Ceiling_       = Mod.GetPublicFunction(NULL, "BreakableWall_State_Ceiling");
        LRZRockPile_State_Wall_            = Mod.GetPublicFunction(NULL, "LRZRockPile_State_Wall");
        if (!BreakableWall_State_Wall_ || !BreakableWall_State_Floor_ || !BreakableWall_State_BurrowFloor_ || !BreakableWall_State_BurrowFloorUp_
            || !BreakableWall_State_Ceiling_ || !LRZRockPile_State_Wall_) {
            RSDK.PrintLog(PRINT_ERROR, LOG_TAG "walls: the game's BreakableWall / LRZRockPile states weren't found: no wall breaking");
        }
        else {
            for (size_t i = 0; i < WALL_CLASS_COUNT; ++i)
                Mod.RegisterObject(NULL, NULL, WALL_CLASSES[i].name, 0, 0, 0, WallUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                                   NULL);
            g_wallsWrapped = true;
        }
    }
    if (fire) {
        for (size_t i = 0; i < FIRE_CLASS_COUNT; ++i)
            Mod.RegisterObject(NULL, NULL, FIRE_CLASSES[i], 0, 0, 0, FireUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
        Mod.RegisterObject(NULL, NULL, "LRZ1Setup", 0, 0, 0, NULL, NULL, Lrz1StaticUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
        Mod.RegisterObject(NULL, NULL, "LRZ2Setup", 0, 0, 0, NULL, NULL, Lrz2StaticUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
        g_fireWrapped = true;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "walls %s, fire %s", g_wallsWrapped ? "wrapped" : "off", g_fireWrapped ? "wrapped" : "off");
}

#endif // MANIA_WALLS_H
