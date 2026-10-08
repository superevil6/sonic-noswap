#pragma once
#include "../third_party/reference/Ultrafix3kFixes_Ultrafix3kFixes_Game.h"  // (types for the editor; the .cpp already has them)

// native/src/Ghost.h: fading afterimages behind player 1, for any move (S3&K). Written by the user (their first C++
// module, 2026-10-01). Included by NoSwapS3K.cpp after the other move headers (it borrows RSDK, CurrentEntity, Log...).
// How a move uses it:
//   afterImage::Clear()      when the move starts (and at every stage load: a ghost's animator is that stage's sprites)
//   afterImage::Record(p)    each frame the trail should grow (one ghost of p as it is now)
//   afterImage::Fade()       every frame (NoSwapS3K.cpp's player update): each ghost fades out
//   afterImage::Draw         wraps the Player's draw: the ghosts, oldest first and see-through, then the player on top
// First user: Shadow's Chaos Control (its warp frames).
namespace afterImage {

struct Ghost { Vector2 pos; Animator anim; uint8 direction; int32 rotation; int alpha; };

constexpr int COUNT = 8;
static Ghost g_buf[COUNT];
static int g_next = 0;

static void Clear() {
    for (int k = 0; k < COUNT; k++)
        g_buf[k].alpha = 0;   // alpha 0 = an empty slot: Draw skips it
    g_next = 0;
}

static void Fade(int step = 0x18) {
    for (int k = 0; k < COUNT; k++)
        g_buf[k].alpha = std::max(g_buf[k].alpha - step, 0);
}

static void Record(EntityPlayer* p, int startAlpha = 0xC0) {
    Ghost& slot = g_buf[g_next];  // the oldest slot, overwritten (a ring buffer)
    slot.pos = p->position;
    slot.anim = p->animator;      // a copy: the player's own animator changes every frame
    slot.direction = p->direction;
    slot.rotation = p->rotation;
    slot.alpha = startAlpha;
    g_next = (g_next + 1) % COUNT;
}

typedef void (*DrawFn)(void);
static DrawFn g_draw = nullptr;
static void Draw() {
    int slot = -1;
    Entity* self = CurrentEntity(&slot);
    if (!self || slot != 0) {          // not player 1: just the game's draw
        g_draw();
        return;
    }
    auto* p = (EntityPlayer*)self;

    // 1. Save what we're about to borrow (like stashing values before a temporary change)
    uint8 ink = p->inkEffect;
    int32 alpha = p->alpha;
    uint8 dir = p->direction;
    int32 rot = p->rotation;

    // 2. Every ghost, oldest first: g_next is the slot about to be overwritten, i.e. the oldest
    for (int k = 0; k < COUNT; k++) {
        Ghost& gh = g_buf[(g_next + k) % COUNT];   // a reference: no copy
        if (gh.alpha <= 0)
            continue;                              // empty or faded out
        p->inkEffect = 2;                          // INK_ALPHA: see-through by p->alpha, so each ghost fades (1 is INK_BLEND, a flat 50%)
        p->alpha = gh.alpha;
        p->direction = gh.direction;               // the way he faced back then
        p->rotation = gh.rotation;
        RSDK->DrawSprite(&gh.anim, &gh.pos, false); // & = "the address of": DrawSprite takes pointers
    }

    // 3. Put everything back exactly as it was
    p->inkEffect = ink;
    p->alpha = alpha;
    p->direction = dir;
    p->rotation = rot;

    // 4. Shadow himself, drawn last so he's on top of his trail
    g_draw();
}

static DrawFn Wrap(DrawFn draw) {
    if (draw != (DrawFn)Draw)
        g_draw = draw;
    return Draw;
}
}  // namespace afterImage