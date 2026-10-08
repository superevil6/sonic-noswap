// native/mania/src/ManiaGhost.h: fading afterimages behind player 1, for any move (Mania). The user's native/src/Ghost.h
// (namespace afterImage, their first C++ module, 2026-10-01) in the Mania mod's C: the same Clear / Record / Fade / Draw,
// named afterImage_* since C has no namespaces. Included once, by NoSwapMania.c (after ManiaMoreData.h: the moves above
// MoreDraw use it).
// How a move uses it:
//   afterImage_Clear()       when the move starts (and at every stage load: a ghost's animator is that stage's sprites)
//   afterImage_Record(p)     each frame the trail should grow (one ghost of p as it is now)
//   afterImage_Fade()        every frame (NoSwapMania.c's OnUpdate, the game running): each ghost fades out
//   afterImage_Draw(p)       in the Player's draw (MoreDraw), before his own: the ghosts, oldest first and see-through;
//                            the player is drawn after it, on top
// First user: Shadow's Chaos Control (its warp frames).
#ifndef MANIA_GHOST_H
#define MANIA_GHOST_H

typedef struct { Vector2 pos; Animator anim; uint8 direction; int32 rotation; int32 alpha; } Ghost;

#define GHOST_COUNT (8)
static Ghost g_ghostBuf[GHOST_COUNT];
static int32 g_ghostNext = 0;

static void afterImage_Clear(void)
{
    for (int32 k = 0; k < GHOST_COUNT; k++)
        g_ghostBuf[k].alpha = 0; // alpha 0 = an empty slot: Draw skips it
    g_ghostNext = 0;
}

static void afterImage_Fade(void)
{
    for (int32 k = 0; k < GHOST_COUNT; k++)
        g_ghostBuf[k].alpha = g_ghostBuf[k].alpha > 0x18 ? g_ghostBuf[k].alpha - 0x18 : 0;
}

static void afterImage_Record(EntityPlayer *p)
{
    Ghost *slot     = &g_ghostBuf[g_ghostNext]; // the oldest slot, overwritten (a ring buffer)
    slot->pos       = p->position;
    slot->anim      = p->animator;              // a copy: the player's own animator changes every frame
    slot->direction = p->direction;
    slot->rotation  = p->rotation;
    slot->alpha     = 0xC0;
    g_ghostNext     = (g_ghostNext + 1) % GHOST_COUNT;
}

static void afterImage_Draw(EntityPlayer *p)
{
    // 1. Save what we're about to borrow (like stashing values before a temporary change)
    int32 ink   = p->inkEffect;
    int32 alpha = p->alpha;
    uint8 dir   = p->direction;
    int32 rot   = p->rotation;

    // 2. Every ghost, oldest first: g_ghostNext is the slot about to be overwritten, i.e. the oldest
    for (int32 k = 0; k < GHOST_COUNT; k++) {
        Ghost *gh = &g_ghostBuf[(g_ghostNext + k) % GHOST_COUNT];
        if (gh->alpha <= 0)
            continue;                  // empty or faded out
        p->inkEffect = INK_ALPHA;      // see-through, by p->alpha
        p->alpha     = gh->alpha;
        p->direction = gh->direction;  // the way he faced back then
        p->rotation  = gh->rotation;
        RSDK.DrawSprite(&gh->anim, &gh->pos, false);
    }

    // 3. Put everything back exactly as it was (the player himself is drawn next, on top of his trail)
    p->inkEffect = ink;
    p->alpha     = alpha;
    p->direction = dir;
    p->rotation  = rot;
}

#endif // MANIA_GHOST_H
