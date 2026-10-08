// NoSwapMania: Mario's Triple Jump (abilities.py triple_jump; tripleJump, tripleWindow, tripleSpeed, triple2, triple3), as
// the S3&K DLL's TripleJump (native/src/NoSwapS3K.cpp) and Sonic 1/2/CD play it: a jump within tripleWindow frames of
// landing from the last one, running (ground speed at least tripleSpeed, the frame before the jump), is the next of a
// chain of three. The 2nd and 3rd go higher (triple2 / triple3: the jump strength's multipliers, x1000) and the 3rd
// somersaults (the attack animation, slot 41, reported to the game as the jump) until he starts falling; then the chain
// starts over. Rolling (any ground state but Player_State_Ground / the landing frame), a hit, a spring or a ledge (in the air without the
// jump) break it.
// Runs from OnUpdate, after every entity's update (Mania lands a player in Player_Update, outside the air state, so the
// frame's result is read here rather than in a state hook). The game's jump has already moved him once by its velocity
// by then, so the extra strength goes on from the next frame, along the ground's angle as Player_Action_Jump adds its
// own (the angle and ground speed from the frame before the jump), as in the S3&K DLL.
// Included once, by NoSwapMania.c.
#ifndef MANIA_TRIPLE_H
#define MANIA_TRIPLE_H

typedef struct {
    int32 chain;       // the last jump's number in the chain (1-3; 4 once the third's somersault is over)
    int32 window;      // frames left on the ground to jump again
    int32 lastVel;     // last frame's ground speed and angle (on the ground)
    int32 lastAngle;
    bool32 wasGrounded; // last frame: on the ground
} TripleMove;
static TripleMove g_triple[PLAYER_COUNT];
static bool32 g_tripleOn = false; // the extra playing has the Triple Jump (set up this stage)

static void TripleStageLoad(void)
{
    memset(g_triple, 0, sizeof(g_triple));
    g_tripleOn = g_cur && g_cur->ab.tripleJump;
}

static void TripleUpdate(EntityPlayer *p)
{
    int32 slot = RSDK.GetEntitySlot(p);
    if (slot < 0 || slot >= PLAYER_COUNT)
        return;
    TripleMove *t   = &g_triple[slot];
    const Abilities *ab = &g_cur->ab;
    bool32 air      = !p->onGround && p->state == Player_State_Air_;
    bool32 flip     = g_animAttack >= 0 && Showing(p, g_animAttack);
    bool32 jumpAnim = p->animator.animationID == ANI_JUMP;
    bool32 jumped   = t->wasGrounded && air && jumpAnim && p->velocity.y < 0; // (the game's jump this frame; not a spring)

    // (landing: the air state lands him next frame, so on the frame he touches down he's onGround still in the air state)
    bool32 groundOther = p->onGround && p->state != Player_State_Ground_ && p->state != Player_State_Air_;
    if (Hurt(p) || groundOther || (!p->onGround && !air) || (air && !jumpAnim))
        t->chain = t->window = 0; // a hit, rolling (or crouching...), an object taking him, a spring or a ledge

    if (jumped) {
        if (Abs(t->lastVel) < ab->tripleSpeed || t->chain >= 3)
            t->chain = 0; // too slow, or after the third: a first jump
        t->chain++;
        int32 m = t->chain == 2 ? ab->triple2 : t->chain == 3 ? ab->triple3 : 1000;
        if (m != 1000) {
            int64 more = (int64)p->jumpStrength * (m - 1000) / 1000;
            uint8 a    = (uint8)(t->lastAngle & 0xFF);
            p->velocity.x += (int32)((more * RSDK.Sin256(a)) >> 8);
            p->velocity.y -= (int32)((more * RSDK.Cos256(a)) >> 8);
        }
        if (t->chain == 3)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "triple: jump 3, flip anim %d", g_animAttack);
        else
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "triple: jump %d (ground speed 0x%X)", t->chain, Abs(t->lastVel));
    }

    // the chain stays open while he's in the air from a jump (the jump pose, the somersault or the Fireball's air pose,
    // all reported as the jump), and for tripleWindow frames after
    if (air && jumpAnim)
        t->window = ab->tripleWindow;
    else if (t->window > 0)
        t->window--;
    else
        t->chain = 0;

    if (t->chain == 3) { // the third jump: the somersault until he starts falling (a spring, a hit or the Fireball end it)
        if (air && p->velocity.y < 0 && jumpAnim && (flip || jumped) && g_animAttack >= 0) {
            Show(p, g_animAttack, true, jumped);
        }
        else {
            t->chain = 4;
            if (air && jumpAnim && flip)
                BackToJump(p);
        }
    }

    t->wasGrounded = p->onGround;
    if (p->onGround) {
        t->lastVel   = p->groundVel;
        t->lastAngle = p->angle;
    }
}

#endif
