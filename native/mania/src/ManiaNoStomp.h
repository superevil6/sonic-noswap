// NoSwapMania: abilities.py "no_stomp" (Joe Musashi, Ray Poward, Mega Man, Axel, Gilius; the user's design, 2026-10-02):
// the jump isn't an attack, and the roll / Spin Dash / Slide is (the S3&K DLL's NoStomp*, native/src/NoSwapS3K.cpp):
//   - the jump: while a badnik's update runs (HitUpdate, HIT_CLASSES' HIT_BADNIK ones that are real badniks: not the
//     breakables after "Mine"), player 1 in the air in his own jump pose (the Jump animation's frames, not a move shown as
//     the jump) is shown to it as falling (ANI_AIR_WALK), so Player_CheckAttacking says no and the badnik hurts him as
//     walking into it does (Player_Hurt: shields, invincibility and the post-hit blink protect as ever). Not while
//     invincible (the game's invincibleTimer counts anyway) or Super. Monitors (ItemBox) and bosses still take the jump.
//   - the roll is his Slide: on the ground in the Jump animation (a roll, a Spin Dash's release) his "Rolling" animation
//     shows (build_s3k_art ROLL_OFFSET 7, extras.py "roll"), reported to the game as the jump, so it attacks and breaks
//     walls as a roll does (the S3&K DLL's RollCurl). In the air the jump pose comes back.
//   - ground_slide (Mega Man, Ray): while the Slide lasts (g_gs.slide) a hit class's update sees him as the jump (ANI_JUMP),
//     so badniks break, bosses take a hit and monitors break (the slide is an attack).
//   - walls: the Slide and the roll break walls as Knuckles does (ManiaWalls.h WallUpdate: NoStompAsKnuckles).
//   - extras.py "roll" without no_stomp (Mario, Pulseman, NiGHTS: a jump that isn't a ball): the same
//     roll display (NoStompUpdate), nothing else; the roll stays the game's attack (reported as the jump).
// Included once, by NoSwapMania.c (after ManiaGuest.h: g_gs).
#ifndef MANIA_NOSTOMP_H
#define MANIA_NOSTOMP_H

#define NOSTOMP_ROLL_OFFSET (7) // build_s3k_art.ROLL_OFFSET: the "Rolling" animation after the ability base

static bool32 g_nsOn        = false; // this stage: the extra playing has no_stomp
static bool32 g_rcOn        = false; // this stage: its roll shows its Rolling animation (no_stomp, or extras.py "roll")
static int32 g_nsAnimRoll   = -1;    // its Rolling animation (-1: none)
static uint8 g_nsBadnik[CLASS_MAX];  // this stage's class IDs that are real badniks (the jump doesn't break them)
static void *g_nsCurl       = NULL;  // the roll's frames while shown (RollCurl)
static bool32 g_nsWasGround = false;

// Breakables in HIT_CLASSES that take the attack rules but aren't badniks: the jump still breaks them (switches, mines)
static const char *const NOSTOMP_NOT_BADNIKS[] = { "Mine", "Pinata", "FlowerPod", "TurretSwitch", "DoorTrigger" };

static bool32 NoStompPlayer(EntityPlayer *p) { return g_nsOn && p && IsExtra(p) && !p->sidekick; }

// The Slide (ground_slide) is running
static bool32 NoStompSliding(EntityPlayer *p) { return NoStompPlayer(p) && g_gs.slide > 0 && p->onGround; }

// Rolling on the ground (a roll or a Spin Dash's release: the Jump animation, on the ground)
static bool32 NoStompRolling(EntityPlayer *p)
{
    return NoStompPlayer(p) && p->onGround && p->animator.animationID == ANI_JUMP;
}

// ManiaWalls.h WallUpdate: walls break for the Slide and the roll as for Knuckles
static bool32 NoStompAsKnuckles(EntityPlayer *p) { return NoStompSliding(p) || NoStompRolling(p); }

// HitUpdate, around the hit class's own update: what player 1 shows it (returns true when it changed his animation ID;
// `saved` the ID to put back)
static bool32 NoStompBefore(Entity *self, int32 kind, EntityPlayer *p, uint16 *saved)
{
    if (kind == HIT_NONE || !NoStompPlayer(p) || !p->interaction)
        return false;
    uint16 cls = self->classID;
    if (NoStompSliding(p) && p->animator.animationID != ANI_JUMP) { // the Slide: an attack
        *saved                  = p->animator.animationID;
        p->animator.animationID = ANI_JUMP;
        return true;
    }
    if (kind == HIT_BADNIK && cls < CLASS_MAX && g_nsBadnik[cls] && !p->onGround && p->superState == SUPERSTATE_NONE
        && Showing(p, ANI_JUMP)) { // his own jump pose: not an attack
        *saved                  = p->animator.animationID;
        p->animator.animationID = ANI_AIR_WALK;
        return true;
    }
    return false;
}

static void NoStompAfter(EntityPlayer *p, bool32 changed, uint16 saved, uint16 shown)
{
    if (changed && p->animator.animationID == shown) // (unless the update set one of its own: a hurt)
        p->animator.animationID = saved;
}

// Player 1's frame (OnUpdate): the roll shows his Rolling animation (the S3&K DLL's RollCurl; no_stomp or "roll")
static void NoStompUpdate(EntityPlayer *p)
{
    if (!g_rcOn || !p || !IsExtra(p) || p->sidekick || g_nsAnimRoll < 0)
        return;
    if (g_nsCurl && p->animator.frames != g_nsCurl)
        g_nsCurl = NULL; // something else took over (a spring, a hit, another animation)
    bool32 grounded = p->onGround && p->state != Player_State_Air_;
    bool32 rolling  = grounded && g_nsWasGround && p->animator.animationID == ANI_JUMP && Showing(p, ANI_JUMP);
    g_nsWasGround   = grounded;
    if (rolling && !g_nsCurl) {
        Show(p, g_nsAnimRoll, true, true);
        g_nsCurl = (void *)p->animator.frames;
    }
    else if (g_nsCurl && !p->onGround && p->animator.animationID == ANI_JUMP) {
        BackToJump(p); // a jump out of the roll, or rolling off a ledge: the jump pose
        g_nsCurl = NULL;
    }
}

static void NoStompStageLoad(void)
{
    g_nsOn        = false;
    g_rcOn        = false;
    g_nsAnimRoll  = -1;
    g_nsCurl      = NULL;
    g_nsWasGround = false;
    memset(g_nsBadnik, 0, sizeof(g_nsBadnik));
    if (!g_cur || !g_active || !(g_cur->ab.noStomp || g_cur->roll))
        return;
    g_rcOn       = true;
    g_nsAnimRoll = HasAnim(g_cur->animBase + NOSTOMP_ROLL_OFFSET);
    if (!g_cur->ab.noStomp) { // ("roll" only: just the display)
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: roll shown as anim %d", g_cur->name, g_nsAnimRoll);
        return;
    }
    g_nsOn = true;
    for (size_t i = 0; i < HIT_CLASS_COUNT; ++i) {
        if (HIT_CLASSES[i].kind != HIT_BADNIK)
            continue;
        bool32 other = false;
        for (size_t k = 0; k < sizeof(NOSTOMP_NOT_BADNIKS) / sizeof(NOSTOMP_NOT_BADNIKS[0]); ++k)
            other |= strcmp(HIT_CLASSES[i].name, NOSTOMP_NOT_BADNIKS[k]) == 0;
        uint16 id = other ? 0 : RSDK.FindObject(HIT_CLASSES[i].name);
        if (id && id < CLASS_MAX)
            g_nsBadnik[id] = true;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: no stomp (the jump isn't an attack); roll shown as anim %d%s", g_cur->name, g_nsAnimRoll,
                  g_hitsOn ? "" : " (hit classes NOT wrapped: badniks treat the jump as usual)");
}

#endif // MANIA_NOSTOMP_H
