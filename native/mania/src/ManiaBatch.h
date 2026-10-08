// NoSwapMania: the moves ported with the Sonic-hosted batch (their data: ManiaBatchData.h). Each is the S3&K DLL's
// (native/src/NoSwapS3K.cpp: the same names, phases and numbers), on Mania's Player, run for player 1 after every
// entity's update (OnUpdate, as the S3&K DLL runs its moves after the game's): the velocity set here moves him next
// frame, after the air state's gravity (taken off in advance where S3&K does). A jump press in mid-air that would start
// the extra's jump move (Hook_JumpAbilitySonic) only notes it (BatchJump); the move starts here, the same frame.
//   - rocket_ride (Robotnik): bombFrames on a rocket, at least rideSpeed along and rising at rideRise, an attack; a wall
//     blows it up early; the blast launches him (bombLaunch, half his speed along) and hits all round (the blast frames'
//     own 64 px boxes: the game's own collision); then the parachute (hover: jump held once he's falling).
//   - ear_grapple (Max): with grappleY, Y in mid-air shoots the ear 45 degrees up and forward a frame at a time (tipX /
//     tipY); a tip in solid terrain latches and reels him in, then a hop; a badnik, monitor or boss the tip reaches is hit
//     (BatchStrike: player 1 stands in at the tip, 8 px round it) and the ear snaps back; grappleRefill gives the grab back
//     after a latch or a hit (grappleCooldown). The jump press opens the Ear Copter (hover) at once.
//   - spirit_flight (Tikal): the orb, held still for its transform, then flying where the d-pad points for spiritFrames.
//   - wall_cling (Trip): holding toward a wall beside her in the air clings; up / down climb; jump kicks off (her double
//     jump ready again); past the top a hop onto the ledge.
//   - extreme_gear (Jet): the board, a fast shallow glide while jump is held (forward speeds up, back brakes and carves
//     round, up lifts for a while); landing runs on at its speed; a throw, a wall or letting go ends it.
//   - puddle_slide (Chaos): the drop, then melting into a puddle and sliding, untouchable (the blink at 3), no punch.
//   - charge (Heavy): Y held on the ground pushes him far past his top speed (the shove first); let go, he coasts; back
//     brakes. Past his top speed he's a Juggernaut: badniks and bosses touching him (their updates: BatchStrike) see him
//     invincible, so they break or take his hit and can't hurt him; badniks' shots of their own class and the generic
//     Projectile likewise. Hazards still hurt. Its Shine Spark: at full charge down stores it (Hook_BatchInput takes the
//     down: no roll; a skid and the glow, BatchDrawBefore), jump launches it up / up-forward / forward until the terrain
//     stops him (no control meanwhile, an attack, a Juggernaut).
//   - spin_attack (Honey): Y held, on the ground or in the air, spins her (an attack: BatchStrike reports her as the jump
//     to what she touches); floaty in the air; whatever she hits bounces her hard; drawn leaning with her speed.
//   - phase_warp (Tails Doll): flickers out, warps up to warpRange px the d-pad's way (never into terrain), flickers back.
// Included once, by NoSwapMania.c (after ManiaMore.h).
#ifndef MANIA_BATCH_H
#define MANIA_BATCH_H

#define BT_SPARK_ACTIVE (1000)  // (abilities.py SPARK_ACTIVE)
// A Shine Spark's limits (the user, 2026-10-01: up-forward over open sky in Green Hill flew forever: Mania doesn't stop a
// player at the stage's top and the sky has no wall): up / up-forward stop BT_SPARK_TOP px below the stage's top (y 0,
// Origins' S1/S2/CD rule), and any spark stops after BT_SPARK_MAX_FRAMES (3 s)
#define BT_SPARK_TOP        (16)
#define BT_SPARK_MAX_FRAMES (180)
#define BT_EAR_LATCH    (100)   // g_bt.ear: 1.. going out; 101.. latched; 201.. snapping back
#define BT_EAR_SNAP     (200)
#define BT_EAR_BOX      (8)     // px round the ear's tip it hits
#define BT_JUGG_INV     (0x7FF1) // the Juggernaut's invincibility timer, only during an enemy's update (the stand-in's is 0x7FF0)

// ability animations: extra slot k at animBase + k (build_s3k_art.ABILITY_SLOTS: 41, 42, 43, 45, 46, 47, 48)
enum { BA_ATTACK, BA_HOVER, BA_SHOT, BA_UP, BA_DOWN, BA_CLING, BA_COUNT };

static struct {
    bool32 trigger;  // BatchJump: this frame's jump press in mid-air is the extra's move
    bool32 reset;    // (held / hurt: already reset)
    int32 bomb;      // Rocket Ride: frames left (riding, then the blast)
    int32 hover;     // parachute / Ear Copter: 0 none; 1 allowed; 2.. open
    int32 ear;       // Ear Grapple (BT_EAR_*)
    bool32 earLeft, earUsed;
    int32 earWait;
    Vector2 latch, earLast, earTip;
    int32 spirit;    // Spirit Flight: frames left
    Vector2 spiritVel;
    int32 cling;     // Wall Cling: frames on the wall (0: not)
    bool32 clingLeft;
    int32 clingLock;
    bool32 gear;     // Extreme Gear
    int32 gearVel, gearLift, gearLeft;
    bool32 puddleDrop; // Puddle Slide: diving
    int32 puddle;      // ... frames of the puddle left
    int32 charge;      // Charge: his locked speed (signed; 0 none)
    int32 chargeAnim;
    bool32 chargeWait; // braked to a stop: Y let go before the next
    int32 spark;       // Shine Spark: 1..sparkStore stored; BT_SPARK_ACTIVE + kind (+100 left) flying
    bool32 sparkDown;  // Hook_BatchInput took a down at full charge
    int32 sparkFlown;  // ... frames it has flown (BT_SPARK_MAX_FRAMES: never forever)
    int32 spin;        // Spin Attack: frames spun (below 0: the cooldown)
    int32 spinAnim;
    bool32 spinHit;    // BatchStrike: she hit something this frame
    int32 warp, warpDX, warpDY, warpVX; // Phase Warp
    bool32 hidden;     // ... his visibility is ours
} g_bt;

static bool32 g_btOn = false; // the extra playing has one of these moves (this stage)
static bool32 g_btRide, g_btEar, g_btSpirit, g_btCling, g_btGear, g_btPuddle, g_btCharge, g_btSpark, g_btSpin, g_btWarp;
static int32 g_btAnim[BA_COUNT];
static uint16 g_btRideSfx, g_btBlastSfx, g_btGearSfx, g_btPuddleSfx, g_btStoreSfx, g_btSparkSfx, g_btSpinSfx, g_btWarpSfx;
static bool32 g_btInputHooked = false, g_btProjWrapped = false;
static void *g_btBoxBreak = NULL; // ItemBox_State_Break: a monitor just broken (the spin's hit; its later states aren't)
static EngineSpriteFrame g_earFrame; // the ear tip's stand-in box
static Animator g_earBox;

static const BatchData *BtData(void) { return &g_cur->more.batch; }
static int32 BtMax(int32 a, int32 b) { return a > b ? a : b; }
static int32 BtMin(int32 a, int32 b) { return a < b ? a : b; }
static int32 BtApproach(int32 v, int32 target, int32 step) { return v < target ? BtMin(v + step, target) : BtMax(v - step, target); }
static void BtSfx(uint16 sfx)
{
    if (sfx != 0xFFFF)
        RSDK.PlaySfx(sfx, false, 255);
}
static bool32 BtAir(EntityPlayer *p) { return p->state == Player_State_Air_; }
static bool32 BtPoseBusy(void) { return g_pose.left > 0 || g_meleeLeft > 0; } // (a throw or the melee: S3&K's g_ab.shot)
static void BtToAir(EntityPlayer *p)
{
    p->onGround      = false;
    p->angle         = 0;
    p->collisionMode = CMODE_FLOOR;
    p->state         = Player_State_Air_;
}
static void BtFrame(EntityPlayer *p, int32 frame)
{
    int32 count         = p->animator.frameCount;
    p->animator.frameID = count > 0 ? Clamp(frame, 0, count - 1) : 0;
    p->animator.timer   = 0;
}
static bool32 BtYHeld(EntityPlayer *p) { return YHeldP1(p) && p->stateInput == Player_Input_P1_ && SceneInfo->timeEnabled; }
// solid terrain (a floor or a ceiling side) at (x, y) px from him
static bool32 BtTerrainAt(EntityPlayer *p, int32 x, int32 y)
{
    return RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, x << 16, y << 16, false)
           || RSDK.ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, x << 16, y << 16, false);
}

static void BtReset(EntityPlayer *p)
{
    int32 spin       = g_bt.spin < 0 ? g_bt.spin : 0;
    bool32 wait      = g_bt.chargeWait;
    if (g_bt.hidden)
        p->visible = true;
    memset(&g_bt, 0, sizeof(g_bt));
    g_bt.spin       = spin;
    g_bt.chargeWait = wait;
    g_bt.chargeAnim = g_bt.spinAnim = -1;
}

// ------------------------------------------------------------------------------------------------ Rocket Ride
// After a Rocket Ride or an Ear Grapple, with hover: jump held once he's falling (in the jump ball) opens the parachute
// / Ear Copter; let go, no more this jump
static void FallingHover(EntityPlayer *p, const Abilities *ab)
{
    bool32 open = g_bt.hover > 1;
    if (open && !Showing(p, g_btAnim[BA_HOVER])) { // (a spring, a hit...: something else took the animation)
        g_bt.hover = 0;
        return;
    }
    bool32 falling = p->velocity.y >= 0 && p->animator.animationID == ANI_JUMP;
    if (p->jumpHold && g_bt.hover <= ab->hoverFrames && (open || falling)) {
        p->velocity.y = ab->hoverSink;
        Show(p, g_btAnim[BA_HOVER], false, false);
        g_bt.hover++;
    }
    else if (open) {
        BackToJump(p);
        g_bt.hover = 0;
    }
}

static void RocketRide(EntityPlayer *p, const Abilities *ab, const BatchData *c, bool32 trigger, bool32 air, bool32 left)
{
    if (trigger) {
        g_bt.bomb  = c->bombFrames + c->blastFrames + 1;
        g_bt.hover = 0;
        int32 dir  = left ? -1 : 1;
        if (c->rideSpeed > 0)
            p->velocity.x = dir * BtMax(dir * p->velocity.x, c->rideSpeed);
        else
            p->velocity.x /= 2;
        BtSfx(g_btRideSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "rocket ride");
    }
    if (g_bt.bomb > 0 && p->animator.animationID != ANI_JUMP) {
        g_bt.bomb = 0; // a spring or an object took over (no parachute this jump)
    }
    else if (g_bt.bomb > 0) {
        if (c->rideSpeed > 0 && !trigger && g_bt.bomb > c->blastFrames + 1 && Abs(p->velocity.x) < c->rideSpeed / 2)
            g_bt.bomb = c->blastFrames + 1; // a wall stopped the rocket: it blows up now
        if (--g_bt.bomb == 0) {             // the blast is over
            BackToJump(p);
            g_bt.hover = ab->hover ? 1 : 0;
        }
        else {
            bool32 blast = g_bt.bomb <= c->blastFrames;
            if (g_bt.bomb == c->blastFrames) {
                p->velocity.y = -c->bombLaunch;
                if (c->rideSpeed > 0)
                    p->velocity.x /= 2;
                p->applyJumpCap = false; // (as after a spring)
                BtSfx(g_btBlastSfx);
                RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "rocket ride: blast");
            }
            else if (!blast && c->rideSpeed > 0) { // riding: full speed along
                int32 dir     = p->velocity.x < 0 ? -1 : 1;
                p->velocity.x = dir * BtMax(dir * p->velocity.x, c->rideSpeed);
                p->velocity.y = -c->rideRise;
            }
            else if (!blast) {
                p->velocity.y = 0;
            }
            Show(p, g_btAnim[BA_ATTACK], true, trigger);
            BtFrame(p, blast ? 1 + (c->blastFrames - g_bt.bomb) / c->blastTicks : 0);
        }
    }
    else if (air && g_bt.hover > 0) {
        FallingHover(p, ab);
    }
}

// ------------------------------------------------------------------------------------------------ Ear Grapple
static void EarGrapple(EntityPlayer *p, const Abilities *ab, const BatchData *c, bool32 trigger, bool32 air, bool32 transformed)
{
    if (c->grappleY) { // the jump press opens the Ear Copter; Y in mid-air grapples, once per airborne period
        if (trigger && g_bt.ear <= 0 && ab->hover && g_btAnim[BA_HOVER] >= 0) {
            g_bt.hover    = 2;
            p->velocity.y = ab->hoverSink;
            Show(p, g_btAnim[BA_HOVER], false, true);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ear copter");
        }
        trigger = false;
        if (!air) {
            g_bt.earUsed = false;
            g_bt.earWait = 0;
        }
        else if (g_bt.earWait > 0 && g_bt.ear <= 0) {
            --g_bt.earWait;
        }
        if (air && !g_bt.earUsed && g_bt.earWait <= 0 && g_bt.ear <= 0 && BtAir(p) && !Hurt(p) && YPressedP1(p, transformed)) {
            g_bt.earUsed = true;
            trigger      = true;
        }
    }
    Vector2 last = g_bt.earLast;
    g_bt.earLast = p->position;
    if (trigger) {
        g_bt.ear     = 1;
        g_bt.earLeft = (p->direction & FLIP_X) != 0;
        g_bt.hover   = 0;
        Show(p, g_btAnim[BA_ATTACK], true, true);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ear grapple");
    }
    else if (g_bt.ear > 0 && (!air || p->animator.animationID != ANI_JUMP || BtPoseBusy())) {
        if (c->grappleRefill && g_bt.ear > BT_EAR_LATCH && g_bt.ear < BT_EAR_SNAP)
            g_bt.earUsed = false; // (latched: the grab's back)
        g_bt.ear = 0;             // landed, a spring, hurt...
    }
    if (g_bt.ear <= 0) {
        if (air && g_bt.hover > 0)
            FallingHover(p, ab);
        return;
    }
    const int32 n    = c->grappleFrames;
    const int32 side = g_bt.earLeft ? -1 : 1;
    p->direction     = g_bt.earLeft ? FLIP_X : FLIP_NONE;
    int32 frame      = 0;
    if (g_bt.ear > BT_EAR_SNAP) { // snapping back, shorter each frame
        frame = (g_bt.ear - BT_EAR_SNAP - 1) * (n / c->snapFrames);
        if (--g_bt.ear == BT_EAR_SNAP) {
            g_bt.ear   = 0;
            g_bt.hover = ab->hover ? 1 : 0;
            BackToJump(p);
            return;
        }
    }
    else if (g_bt.ear > BT_EAR_LATCH) { // latched and reeling in
        int32 dx = (g_bt.latch.x - p->position.x) >> 16, dy = (g_bt.latch.y - p->position.y) >> 16;
        bool32 stopped = g_bt.ear > BT_EAR_LATCH + 2 && Abs(p->position.x - last.x) < 0x8000 && Abs(p->position.y - last.y) < 0x8000;
        if (g_bt.ear >= BT_EAR_LATCH + ab->reelFrames || (Abs(dx) < ab->latchRange && Abs(dy) < ab->latchRange) || stopped) {
            p->velocity.x = side * ab->grappleForward; // there: a small hop, still moving forward
            p->velocity.y = -ab->grappleHop;
            if (c->grappleRefill) {
                g_bt.earUsed = false;
                g_bt.earWait = c->grappleCooldown;
            }
            g_bt.ear   = 0;
            g_bt.hover = ab->hover ? 1 : 0;
            BackToJump(p);
            return;
        }
        g_bt.ear++;
        for (int32 k = 1; k < n; k++) // the longest ear that doesn't reach past the latch point
            if (c->tipX[k] <= dx * side && c->tipY[k] >= dy)
                frame = k;
    }
    else { // the ear going out: does its tip reach solid ground?
        frame    = g_bt.ear - 1;
        int32 tx = side * c->tipX[frame], ty = c->tipY[frame];
        g_bt.earTip.x = p->position.x + (tx << 16);
        g_bt.earTip.y = p->position.y + (ty << 16);
        if (BtTerrainAt(p, tx, ty)) {
            g_bt.latch = g_bt.earTip;
            g_bt.ear   = BT_EAR_LATCH + 1;
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ear grapple latched");
        }
        else {
            if (p->velocity.y > -p->gravityStrength) // he stops falling
                p->velocity.y = -p->gravityStrength;
            if (++g_bt.ear > n) // full reach, nothing there
                g_bt.ear = BT_EAR_SNAP + c->snapFrames;
        }
    }
    if (g_bt.ear > BT_EAR_LATCH && g_bt.ear < BT_EAR_SNAP) { // reeled in along the line to the latch point
        double dx = (double)(g_bt.latch.x - p->position.x), dy = (double)(g_bt.latch.y - p->position.y), len = sqrt(dx * dx + dy * dy);
        if (len > 0) {
            p->velocity.x = (int32)(ab->reelSpeed * dx / len);
            p->velocity.y = (int32)(ab->reelSpeed * dy / len) - p->gravityStrength;
        }
        p->applyJumpCap = false;
    }
    Show(p, g_btAnim[BA_ATTACK], true, false);
    BtFrame(p, frame);
}

// ------------------------------------------------------------------------------------------------ Spirit Flight
static void SpiritFlight(EntityPlayer *p, const BatchData *c, bool32 trigger, bool32 air)
{
    const int32 total = c->spiritTransform * c->spiritTicks + c->spiritFrames;
    Vector2 *v        = &g_bt.spiritVel;
    if (trigger) {
        g_bt.spirit = total;
        v->x = v->y = 0;
        Show(p, g_btAnim[BA_ATTACK], true, true);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "spirit flight");
    }
    else if (g_bt.spirit > 0) {
        if (!air || p->animator.animationID != ANI_JUMP) { // landed, a spring...
            g_bt.spirit = 0;
            return;
        }
        if (BtPoseBusy()) { // a throw (her Spirit Orb): she re-forms
            g_bt.spirit = 0;
            return;
        }
        if (p->velocity.x == 0) // a wall stopped her: the orb too
            v->x = 0;
        if (p->velocity.y == 0 && v->y < 0) // a ceiling
            v->y = 0;
        if (--g_bt.spirit == 0 || (g_bt.spirit <= c->spiritFrames && p->jumpPress)) { // she re-forms
            g_bt.spirit   = 0;
            BackToJump(p);
            p->velocity.x = v->x;
            p->velocity.y = BtMax(v->y, 0);
            return;
        }
    }
    if (g_bt.spirit <= 0)
        return;
    if (g_bt.spirit <= c->spiritFrames) { // flying where the d-pad points
        int32 speed = (p->left || p->right) && (p->up || p->down) ? c->spiritDiag : c->spiritSpeed;
        v->x        = BtApproach(v->x, p->left ? -speed : p->right ? speed : 0, c->spiritAccel);
        v->y        = BtApproach(v->y, p->up ? -speed : p->down ? speed : 0, c->spiritAccel);
    }
    else {
        v->x = v->y = 0;
    }
    p->velocity.x   = v->x;
    p->velocity.y   = v->y - p->gravityStrength;
    p->applyJumpCap = false;
    Show(p, g_btAnim[BA_ATTACK], true, false);
    if (g_bt.spirit >= c->spiritFrames) // the transform, then the orb's first frame; its loop runs from there
        BtFrame(p, BtMin((total - g_bt.spirit) / c->spiritTicks, c->spiritTransform));
}

// ------------------------------------------------------------------------------------------------ Wall Cling
static bool32 WallBeside(EntityPlayer *p, const BatchData *c, bool32 left)
{
    return RSDK.ObjectTileCollision(p, p->collisionLayers, left ? CMODE_RWALL : CMODE_LWALL, p->collisionPlane,
                                    (left ? -c->wallX : c->wallX) << 16, c->wallY << 16, false);
}

static void LetGoOfWall(EntityPlayer *p, const BatchData *c)
{
    g_bt.cling          = 0;
    g_bt.clingLock      = c->clingLock;
    p->jumpAbilityState = 1; // (her double jump ready again)
    BackToJump(p);
}

static void WallCling(EntityPlayer *p, const BatchData *c, bool32 air)
{
    bool32 airState = BtAir(p);
    if (!air)
        g_bt.clingLock = 0;
    else if (g_bt.clingLock > 0 && g_bt.cling == 0 && !WallBeside(p, c, g_bt.clingLeft))
        g_bt.clingLock--; // (only while she's away from it)

    if (g_bt.cling > 0) {
        if (!air || !airState || !Showing(p, g_btAnim[BA_CLING])) {
            g_bt.cling = 0;
            return;
        }
        const bool32 left = g_bt.clingLeft;
        g_bt.cling++;
        if (p->jumpPress) { // a wall jump: kick off away from it
            LetGoOfWall(p, c);
            p->velocity.x   = left ? c->wallJumpX : -c->wallJumpX;
            p->velocity.y   = -c->wallJumpY - p->gravityStrength;
            p->direction    = left ? FLIP_NONE : FLIP_X;
            p->applyJumpCap = true; // (letting go of jump cuts it short, as a jump)
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "wall jump");
            return;
        }
        bool32 wall = WallBeside(p, c, left);
        if (!wall || !(left ? p->left : p->right) || g_bt.cling > c->clingFrames) { // the wall ends, let go, out of time
            LetGoOfWall(p, c);
            if (!wall && p->up) { // climbed to its top: a hop up onto the ledge
                p->velocity.x   = left ? -c->ledgeForward : c->ledgeForward;
                p->velocity.y   = -c->ledgeHop - p->gravityStrength;
                p->applyJumpCap = false;
            }
            return;
        }
        int32 vy = g_bt.cling > c->clingHold ? c->clingSlide : 0;
        if (p->up)
            vy = -c->climbSpeed;
        else if (p->down)
            vy = c->climbSpeed;
        p->velocity.x = 0;
        p->velocity.y = vy - p->gravityStrength;
        p->direction  = left ? FLIP_X : FLIP_NONE;
        Show(p, g_btAnim[BA_CLING], false, false);
        return;
    }
    int32 a     = p->animator.animationID;
    bool32 pose = a == ANI_JUMP || (a >= ANI_WALK && a <= ANI_DASH); // jumping (the double jump too) or falling
    if (!air || !airState || !pose || p->left == p->right || BtPoseBusy())
        return;
    bool32 left = p->left;
    if (g_bt.clingLock > 0 && left == g_bt.clingLeft)
        return;
    if (!WallBeside(p, c, left))
        return;
    g_bt.cling     = 1;
    g_bt.clingLeft = left;
    MoveState *m   = StateOf(p);
    if (m)
        m->dbl = 0;
    p->velocity.x = 0;
    p->velocity.y = -p->gravityStrength;
    p->direction  = left ? FLIP_X : FLIP_NONE;
    Show(p, g_btAnim[BA_CLING], false, true);
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "wall cling");
}

// ------------------------------------------------------------------------------------------------ Extreme Gear
static void ExtremeGear(EntityPlayer *p, const BatchData *c, bool32 trigger, bool32 air)
{
    if (trigger) {
        bool32 left   = (p->direction & FLIP_X) != 0;
        int32 forward = BtMax(left ? -p->velocity.x : p->velocity.x, c->gearSpeed);
        g_bt.gear     = true;
        g_bt.gearVel  = left ? -forward : forward;
        g_bt.gearLift = c->gearLiftFrames;
        g_bt.gearLeft = c->gearFrames;
        p->velocity.x = g_bt.gearVel;
        p->velocity.y = (p->velocity.y > 0 ? 0 : p->velocity.y / 2) - p->gravityStrength; // onto the board: no fall
        Show(p, g_btAnim[BA_ATTACK], true, true);
        BtSfx(g_btGearSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "extreme gear");
        return;
    }
    if (!g_bt.gear)
        return;
    if (!air) { // landed: running on at the board's speed
        p->groundVel = g_bt.gearVel;
        g_bt.gear    = false;
        return;
    }
    if (p->animator.animationID != ANI_JUMP || BtPoseBusy() || !BtAir(p)) {
        g_bt.gear = false; // a spring, the throw, an object
        return;
    }
    if (!p->jumpHold || p->velocity.x == 0 || (c->gearFrames > 0 && g_bt.gearLeft <= 0)) {
        g_bt.gear = false; // let go, a wall, or the ride's time up: off the board, in the jump ball
        BackToJump(p);
        return;
    }
    g_bt.gearLeft--;
    bool32 left = g_bt.gearVel < 0;
    int32 s     = Abs(g_bt.gearVel);
    bool32 forward = left ? p->left : p->right, back = left ? p->right : p->left;
    if (back) { // braking; slow enough, he carves round
        s -= c->gearBrake;
        if (s <= c->gearTurn) {
            s    = c->gearTurn;
            left = !left;
        }
    }
    else if (s < c->gearSpeed) {
        s = BtMin(s + c->gearRecover, c->gearSpeed);
    }
    else if (forward && s < c->gearTop) {
        s = BtMin(s + c->gearAccel, c->gearTop);
    }
    g_bt.gearVel  = left ? -s : s;
    p->direction  = left ? FLIP_X : FLIP_NONE;
    p->velocity.x = g_bt.gearVel;
    int32 vy      = p->velocity.y;
    if (p->up && g_bt.gearLift > 0) { // the nose tilts up: a little lift
        g_bt.gearLift--;
        vy = vy > -c->gearRise ? BtMax(vy - c->gearLift, -c->gearRise) : vy + p->gravityStrength;
    }
    else {
        vy = BtMin(vy + p->gravityStrength, c->gearSink);
    }
    p->velocity.y   = vy - p->gravityStrength;
    p->applyJumpCap = false;
    Show(p, g_btAnim[BA_ATTACK], true, false);
}

// ------------------------------------------------------------------------------------------------ Puddle Slide
static void PuddleSlide(EntityPlayer *p, const BatchData *c, bool32 trigger, bool32 air)
{
    const int32 steps = Clamp(c->puddleSteps, 1, BATCH_PUDDLE_MAX), ticks = c->puddleTicks, total = steps * ticks;
    bool32 landed     = false;
    if (trigger) {
        if (p->velocity.y < c->puddleDrop)
            p->velocity.y = c->puddleDrop;
        g_bt.puddleDrop = true;
        g_bt.puddle     = 0;
        Show(p, g_btAnim[BA_ATTACK], true, true);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "puddle drop");
    }
    else if (g_bt.puddleDrop) {
        if (!air) { // landed from the drop: melt
            g_bt.puddleDrop = false;
            if (!Hurt(p) && (p->state == Player_State_Ground_ || BtAir(p))) { // (the air state lands him next frame)
                g_bt.puddle = total;
                landed      = true;
                BtSfx(g_btPuddleSfx);
            }
        }
        else if (p->animator.animationID != ANI_JUMP || p->velocity.y <= 0x10000) {
            g_bt.puddleDrop = false; // a spring, a badnik bounce, a hit...
            if (p->animator.animationID == ANI_JUMP)
                BackToJump(p);
        }
        else {
            Show(p, g_btAnim[BA_ATTACK], true, false);
        }
    }
    if (g_bt.puddle <= 0)
        return;
    int32 a = p->animator.animationID;
    if (air || Hurt(p) || (!landed && (p->state != Player_State_Ground_ || a == ANI_JUMP || a == ANI_CROUCH))) {
        g_bt.puddle = 0; // a jump, a roll, a crouch, a ledge, a spring, a hit
        return;
    }
    g_bt.puddle--;
    int32 step = BtMin((total - g_bt.puddle - 1) / ticks, steps - 1);
    Show(p, g_btAnim[BA_HOVER], false, false);
    BtFrame(p, c->puddleFrames[step]);
    p->animator.speed = 0;
    if (step < c->puddleMove) { // melting and sliding
        int32 dir    = (p->direction & FLIP_X) ? -1 : 1;
        p->groundVel = BtMax(p->groundVel * dir, c->puddleSpeed) * dir;
    }
    else { // rising: slowing to a stop
        p->groundVel -= p->groundVel >> 2;
    }
    if (p->blinkTimer < 3)
        p->blinkTimer = 3; // nothing hurts him (no flicker)
    if (g_meleeCooldown < 2)
        g_meleeCooldown = 2; // and Y doesn't punch
    if (g_bt.puddle == 0)  // risen
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// ------------------------------------------------------------------------------------------------ Charge, Shine Spark
static bool32 Juggernaut(EntityPlayer *p)
{
    if (!g_btCharge || !IsExtra(p) || RSDK.GetEntitySlot(p) != SLOT_PLAYER1 || Hurt(p))
        return false;
    if (g_bt.spark > BT_SPARK_ACTIVE)
        return true; // (the Shine Spark, flying)
    return g_bt.charge != 0 && p->onGround && p->state == Player_State_Ground_ && Abs(g_bt.charge) > p->topSpeed;
}

static void ChargeEnd(EntityPlayer *p, bool32 air)
{
    if (g_bt.charge && !air && p->animator.animationID == ANI_JUMP) // (ours still showing: the game's run back)
        RSDK.SetSpriteAnimation(g_extraFrames, Abs(p->groundVel) >= p->topSpeed ? ANI_RUN : ANI_WALK, &p->animator, true, 0);
    g_bt.charge     = 0;
    g_bt.chargeAnim = -1;
}

static void Charge(EntityPlayer *p, const BatchData *c, bool32 air)
{
    bool32 held = BtYHeld(p);
    if (g_bt.chargeWait) {
        if (held && g_bt.charge == 0)
            return;
        g_bt.chargeWait = false;
    }
    int32 top = p->topSpeed;
    if (g_bt.charge == 0) {
        if (air || !held || Hurt(p) || p->down || p->animator.animationID == ANI_JUMP || p->state != Player_State_Ground_ || g_bt.spark != 0)
            return;
        int32 dir       = (p->direction & FLIP_X) ? -1 : 1;
        g_bt.charge     = dir * BtMax(BtMax(1, dir * p->groundVel), c->chargeShove);
        g_bt.chargeAnim = -1;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "charge");
    }
    if (air || Hurt(p) || p->state != Player_State_Ground_) {
        ChargeEnd(p, air);
        return;
    }
    int32 dir = g_bt.charge < 0 ? -1 : 1;
    int32 v   = Abs(g_bt.charge);
    if (v >= 0x20000 && 2 * dir * p->groundVel < v) { // a wall stopped him
        ChargeEnd(p, air);
        return;
    }
    bool32 brake = dir > 0 ? p->left : p->right;
    if (brake) {
        held = false; // (the slide's pose)
        v -= c->chargeBrake;
        if (v <= 0) { // a full stop: over, standing
            g_bt.charge     = 0;
            g_bt.chargeAnim = -1;
            g_bt.chargeWait = true;
            p->groundVel    = 0;
            p->velocity.x   = 0;
            RSDK.SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "charge: braked to a stop");
            return;
        }
    }
    else if (held) {
        v = BtMin(c->chargeTop, v + c->chargeAccel + (int32)((int64)v * c->chargeGain >> 10));
    }
    else {
        v -= c->chargeFriction;
        if (v <= top) {
            ChargeEnd(p, air);
            return;
        }
    }
    g_bt.charge  = dir * v;
    p->groundVel = dir * v;
    p->direction = dir < 0 ? FLIP_X : FLIP_NONE;
    int32 slot   = !held ? BA_HOVER : v > top ? BA_SHOT : BA_ATTACK;
    Show(p, g_btAnim[slot], true, slot != g_bt.chargeAnim);
    g_bt.chargeAnim = slot;
    int32 count     = p->animator.frameCount;
    if (count > 0) {
        int32 f = ((p->position.x >> 16) / c->chargeStride) % count;
        if (f < 0)
            f += count;
        BtFrame(p, dir < 0 ? count - 1 - f : f);
    }
    p->animator.speed = 0;
}

static void SparkVelocity(EntityPlayer *p, const BatchData *c, int32 kind, int32 dir, bool32 air)
{
    int32 vx = kind == 1 ? 0 : dir * (kind == 2 ? c->sparkDiag : c->sparkSpeed);
    int32 vy = kind == 1 ? -c->sparkSpeed : kind == 2 ? -c->sparkDiag : 0;
    if (!air) {
        p->groundVel = vx; // (forward along the ground)
        return;
    }
    vy -= p->gravityStrength;     // (the air state adds it back)
    if (vy > -0x40000 && vy < 0)  // (and its drag while rising that slowly: added in advance)
        vx = (int32)((int64)vx * 32 / 31);
    p->velocity.x = vx;
    p->velocity.y = vy;
}

static void Spark(EntityPlayer *p, const BatchData *c, bool32 air)
{
    bool32 down    = g_bt.sparkDown;
    g_bt.sparkDown = false;
    if (g_bt.spark > BT_SPARK_ACTIVE) { // flying
        int32 k = g_bt.spark - BT_SPARK_ACTIVE, kind = k % 100, dir = k >= 100 ? -1 : 1;
        int32 a     = p->animator.animationID;
        bool32 ours = a == ANI_JUMP || (a >= ANI_WALK && a <= ANI_DASH); // (along the ground the game puts its run in)
        bool32 go   = ours && (BtAir(p) || (!air && p->state == Player_State_Ground_)); // (landing: the air state still)
        bool32 stop = false;
        if (go) {
            int32 along = dir * (air ? p->velocity.x : p->groundVel);
            if (!air)
                stop = kind != 3 || along < c->sparkSpeed / 2; // landed (or a ceiling); forward, a wall
            else if (kind == 1)
                stop = p->velocity.y > -c->sparkSpeed / 2; // a ceiling
            else if (kind == 2)
                stop = p->velocity.y > -c->sparkDiag / 2 || along < c->sparkDiag / 2;
            else
                stop = along < c->sparkSpeed / 2; // a wall
            if (kind != 3 && (p->position.y >> 16) < BT_SPARK_TOP)
                stop = true; // the stage's top: his ceiling
            if (++g_bt.sparkFlown > BT_SPARK_MAX_FRAMES)
                stop = true; // (open sky both ways: never forever)
        }
        if (!go || stop) {
            g_bt.spark = 0;
            if (stop) { // the terrain stopped him: he drops from there
                if (air) {
                    p->velocity.x = 0;
                    if (p->velocity.y < 0)
                        p->velocity.y = 0;
                }
                p->groundVel = 0;
                RSDK.SetSpriteAnimation(g_extraFrames, air ? ANI_AIR_WALK : ANI_WALK, &p->animator, true, 0);
            }
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shine spark: %s", stop ? "stopped by the terrain" : "taken over");
            return;
        }
        p->direction = dir < 0 ? FLIP_X : FLIP_NONE;
        SparkVelocity(p, c, kind, dir, air);
        int32 slot = kind == 3 ? BA_SHOT : BA_UP;
        Show(p, g_btAnim[slot], true, false);
        int32 count = p->animator.frameCount;
        if (kind == 3 && count > 0) {
            int32 f = ((p->position.x >> 16) / c->chargeStride) % count;
            if (f < 0)
                f += count;
            BtFrame(p, dir < 0 ? count - 1 - f : f);
        }
        p->animator.timer = 0;
        p->animator.speed = 0;
        return;
    }
    if (g_bt.spark > 0) { // stored
        g_bt.spark--;
        if (g_bt.spark > c->sparkStore - c->sparkSkidFrames && !air && p->groundVel != 0) { // just stored: the skid
            int32 v      = BtMax(0, Abs(p->groundVel) - c->sparkSkid);
            p->groundVel = p->groundVel < 0 ? -v : v;
            if (v > 0 && p->animator.animationID != ANI_SKID)
                RSDK.SetSpriteAnimation(g_extraFrames, ANI_SKID, &p->animator, false, 0);
        }
        bool32 free = air ? BtAir(p) : (p->state == Player_State_Ground_ || p->state == Player_State_Crouch_ || p->state == Player_State_LookUp_);
        if (g_bt.spark > 0 && p->jumpPress && free && !Hurt(p)) { // launch
            int32 kind = 1, dir = (p->direction & FLIP_X) ? -1 : 1;
            if (p->left || p->right) {
                kind = p->up ? 2 : 3;
                dir  = p->left ? -1 : 1;
            }
            g_bt.spark          = BT_SPARK_ACTIVE + kind + (dir < 0 ? 100 : 0);
            g_bt.sparkFlown     = 0;
            g_bt.charge         = 0;
            p->direction        = dir < 0 ? FLIP_X : FLIP_NONE;
            BtToAir(p);
            p->jumpAbilityState = 0;
            p->applyJumpCap     = false;
            SparkVelocity(p, c, kind, dir, true);
            Show(p, g_btAnim[kind == 3 ? BA_SHOT : BA_UP], true, true);
            BtSfx(g_btSparkSfx);
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shine spark: launched (%s)", kind == 1 ? "up" : kind == 2 ? "up-forward" : "forward");
        }
        return;
    }
    if (down && !air && g_bt.charge != 0 && Abs(g_bt.charge) > p->topSpeed && !Hurt(p)) { // storing
        g_bt.charge     = 0;
        g_bt.chargeAnim = -1;
        g_bt.spark      = c->sparkStore;
        RSDK.SetSpriteAnimation(g_extraFrames, ANI_SKID, &p->animator, true, 0);
        BtSfx(g_btStoreSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "shine spark: stored");
    }
}

// After player 1's input (Player_Input_P1): the Shine Spark flying takes the pad (no control, no jump out of a run along
// the ground); at full charge (or one stored) down on the ground is the spark's (no roll), and a crouch's jump with one
// stored is a plain jump (then the launch), not a Spin Dash
static bool32 Hook_BatchInput(bool32 skipped)
{
    (void)skipped;
    EntityPlayer *self = (EntityPlayer *)SceneInfo->entity;
    if (!g_btSpark || !IsExtra(self) || RSDK.GetEntitySlot(self) != SLOT_PLAYER1)
        return false;
    if (g_bt.spark > BT_SPARK_ACTIVE) {
        self->up = self->down = self->left = self->right = false;
        self->jumpPress = false;
        return false;
    }
    bool32 full = g_bt.charge != 0 && Abs(g_bt.charge) > self->topSpeed;
    if (self->onGround && self->down && (full || g_bt.spark > 0)) {
        if (self->groundVel != 0) {
            g_bt.sparkDown = full;
            self->down     = false;
        }
        else if (self->jumpPress && g_bt.spark > 0) {
            self->down = false;
        }
    }
    return false;
}

// ------------------------------------------------------------------------------------------------ Spin Attack
static void SpinAttack(EntityPlayer *p, const BatchData *c, bool32 air, bool32 transformed)
{
    int32 a      = p->animator.animationID;
    bool32 plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH);
    bool32 inState = air ? BtAir(p) : p->state == Player_State_Ground_;
    if (g_bt.spin < 0)
        g_bt.spin++;
    if (g_bt.spin == 0 && YPressedP1(p, transformed) && !Hurt(p) && inState && (air || plain) && !BtPoseBusy()) {
        g_bt.spin     = 1;
        g_bt.spinAnim = -1;
        g_bt.spinHit  = false;
        if (air && a != ANI_JUMP)
            p->applyJumpCap = false; // (not her own jump: a spring's or a fall's rise isn't cut short, see below)
        BtSfx(g_btSpinSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "spin attack");
    }
    if (g_bt.spin <= 0)
        return;
    if (!BtYHeld(p) || g_bt.spin > c->spinFrames || Hurt(p) || !inState) { // let go, too long or out of it: over
        g_bt.spin    = -c->spinCooldown;
        g_bt.spinHit = false;
        if (!Hurt(p) && (Showing(p, g_btAnim[BA_ATTACK]) || Showing(p, g_btAnim[BA_SHOT]))) {
            if (air)
                BackToJump(p);
            else
                RSDK.SetSpriteAnimation(g_extraFrames, ANI_WALK, &p->animator, true, 0);
        }
        return;
    }
    if (g_bt.spinHit) { // a hard bounce off what she hit
        g_bt.spinHit    = false;
        p->velocity.y   = -c->spinBounce;
        p->applyJumpCap = false;
        if (!air) { // on the ground: up and away, a pinball
            int32 away    = (p->direction & FLIP_X) ? c->spinBounceX : -c->spinBounceX;
            p->velocity.x = away;
            p->groundVel  = away;
            BtToAir(p);
            air = true;
        }
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "spin attack: bounce");
    }
    // (floaty: BatchAirGravity, right after the game's own air state, only on the frames it pulled her down)
    int32 slot = air ? BA_ATTACK : BA_SHOT;
    if (air && g_bt.spinAnim >= 0 && !Showing(p, g_btAnim[slot]) && !Showing(p, g_btAnim[g_bt.spinAnim]))
        p->applyJumpCap = false; // an object (a spring...) took her pose and launched her: the spin shows her as the jump
                                 // ball (ANI_JUMP), and the game's jump cap (Player_HandleAirMovement) would cut that rise
                                 // to 4 px per frame unless jump is held, the user's slow rise at a spring, 2026-10-02
    Show(p, g_btAnim[slot], true, slot != g_bt.spinAnim);
    g_bt.spinAnim = slot;
    int32 count   = p->animator.frameCount;
    BtFrame(p, count > 0 ? (g_bt.spin / c->spinTicks) % count : 0);
    p->animator.speed = 0;
    g_bt.spin++;
}

// After the game's air state (Hook_StateAir), player 1 spinning: part of the gravity it has just added taken back. Only
// when it really added it (still the air state, in the air: Player_HandleAirMovement ran; a landing frame or an object's
// launch adds none), and before her move and the objects, so a spring's or a hit's speed is never touched
static void BatchAirGravity(EntityPlayer *p)
{
    if (!g_btOn || !g_btSpin || g_bt.spin <= 0 || RSDK.GetEntitySlot(p) != SLOT_PLAYER1 || p->state != Player_State_Air_
        || p->onGround || Hurt(p) || !BtYHeld(p))
        return;
    p->velocity.y -= (int32)((int64)p->gravityStrength * (256 - g_cur->more.batch.spinGravity) >> 8);
}

// ------------------------------------------------------------------------------------------------ Phase Warp
static void PhaseWarp(EntityPlayer *p, const BatchData *c, bool32 trigger, bool32 air)
{
    const int32 appear = c->warpAppear, gone = c->warpGone, total = c->warpVanish + gone + appear;
    if (trigger) {
        int32 dx = p->right ? 1 : p->left ? -1 : 0, dy = p->up ? -1 : p->down ? 1 : 0;
        if (!dx && !dy)
            dx = (p->direction & FLIP_X) ? -1 : 1;
        g_bt.warp   = total;
        g_bt.warpDX = dx;
        g_bt.warpDY = dy;
        g_bt.warpVX = p->velocity.x;
        Show(p, g_btAnim[BA_ATTACK], true, true);
        BtSfx(g_btWarpSfx);
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "phase warp (%d, %d)", dx, dy);
    }
    else if (g_bt.warp > 0 && (!air || Hurt(p) || p->animator.animationID != ANI_JUMP || BtPoseBusy())) {
        g_bt.warp = 0; // landed, a hit, a spring, the melee...
    }
    if (g_bt.warp <= 0) {
        if (g_bt.hidden)
            p->visible = true;
        g_bt.hidden = false;
        return;
    }
    p->velocity.x = 0; // held still
    p->velocity.y = -p->gravityStrength;
    if (g_bt.warp == gone + appear) { // gone: to the destination, the last clear step along the way
        static const int32 POINTS[][2] = { { 0, 0 }, { 0, -13 }, { 0, 13 }, { -8, 0 }, { 8, 0 } }; // (abilities.WARP_POINTS)
        const bool32 diag = g_bt.warpDX && g_bt.warpDY;
        const int32 step = 8 << 16, axis = diag ? (int32)((int64)step * 46341 >> 16) : step, steps = c->warpRange / 8;
        int32 ox = 0, oy = 0, k = 0;
        for (; k < steps; k++) {
            int32 nx = ox + g_bt.warpDX * axis, ny = oy + g_bt.warpDY * axis;
            bool32 blocked = false;
            for (int32 i = 0; i < 5 && !blocked; ++i) blocked = BtTerrainAt(p, (nx >> 16) + POINTS[i][0], (ny >> 16) + POINTS[i][1]);
            if (blocked)
                break;
            ox = nx;
            oy = ny;
        }
        p->position.x += ox;
        p->position.y += oy;
        RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "phase warp: %d of %d steps (%d, %d px)", k, steps, ox >> 16, oy >> 16);
    }
    Show(p, g_btAnim[BA_ATTACK], true, false);
    bool32 out  = g_bt.warp <= gone + appear && g_bt.warp > appear;
    p->visible  = !out && (g_bt.warp & 1); // gone, or a flicker every other frame
    g_bt.hidden = true;
    if (p->blinkTimer < 3)
        p->blinkTimer = 3; // untouchable (without the blink's own flicker)
    if (--g_bt.warp == 0) { // back: his speed along, falling from here
        p->velocity.x = g_bt.warpVX;
        p->velocity.y = 0;
        p->visible    = true;
        g_bt.hidden   = false;
        BackToJump(p);
    }
}

// ------------------------------------------------------------------------------------------------ hits
// A hit class's update (HitUpdate, before the anchor, the melee and the shots): Max's ear tip stands in for him while
// it goes out (as Marine's anchor: a 16x16 box round the tip, his own turn every other frame when he's near it); and while
// Honey spins, Heavy charges or sparks, the object's own update sees player 1 as the jump (an attack), Heavy past his top
// speed invincible too (the Juggernaut). true: its update has run
static bool32 BatchStrike(Entity *self, int32 kind, EntityPlayer *p)
{
    if (!g_btOn || !IsExtra(p) || !p->interaction || p->state == Player_State_Death_ || p->state == Player_State_Drown_)
        return false;
    uint16 cls = self->classID;
    if (g_btEar && g_bt.ear > 0 && g_bt.ear <= g_cur->more.batch.grappleFrames) {
        int32 reach = kind == HIT_BOSS ? REACH_BOSS : REACH_BADNIK;
        if (Abs(g_bt.earTip.x - self->position.x) > (reach << 16) || Abs(g_bt.earTip.y - self->position.y) > (reach << 16))
            return false;
        int32 near = (reach + 24) << 16;
        if (Abs(p->position.x - self->position.x) <= near && Abs(p->position.y - self->position.y) <= near && (g_frame & 1))
            return false;
        const Animator *box = &g_earBox;
        Animator own;
        if (!g_engineFrameOK) { // (the fallback: his own frame's box, at the tip)
            own = p->animator;
            box = &own;
        }
        if (StandInAt(self, g_bt.earTip, box, p->direction, p->collisionPlane, p)) {
            const BatchData *c = &g_cur->more.batch;
            g_bt.ear = BT_EAR_SNAP + c->snapFrames;
            if (c->grappleRefill) {
                g_bt.earUsed = false;
                g_bt.earWait = c->grappleCooldown;
            }
            RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "ear grapple: the ear hit class %d (slot %d)", cls, RSDK.GetEntitySlot(self));
        }
        return true;
    }
    bool32 spinning = g_btSpin && g_bt.spin > 0;
    bool32 jugg     = Juggernaut(p);
    bool32 attack   = spinning || jugg || (g_btCharge && g_bt.charge != 0);
    if (!attack)
        return false;
    int32 far = (REACH_BOSS + 128) << 16;
    if (Abs(p->position.x - self->position.x) > far || Abs(p->position.y - self->position.y) > far)
        return false;
    int32 anim = p->animator.animationID, inv = p->invincibleTimer;
    Vector2 vel = p->velocity, pos = p->position;
    int32 score = p->score, bonus = p->scoreBonus;
    void *state = ((EntityWithState *)self)->state;
    p->animator.animationID = ANI_JUMP;
    if (jugg && !p->invincibleTimer)
        p->invincibleTimer = BT_JUGG_INV;
    // (a monitor breaks only under a falling or grounded jump ball, ItemBox_CheckHit; otherwise it's solid. The floaty
    // spin hangs near the top of its arc rising slowly, so coming down onto one she sat on its lid until she fell: from
    // above she's shown to it as not rising, and breaks it at the first touch like a rolling Sonic)
    bool32 lid = spinning && kind == HIT_ITEMBOX && vel.y < 0 && p->position.y < self->position.y;
    if (lid)
        p->velocity.y = 0;
    Mod.Super(cls, SUPER_UPDATE, NULL);
    bool32 gone  = self->classID != cls;
    bool32 moved = p->velocity.x != vel.x || p->velocity.y != vel.y;
    bool32 newState = !gone && ((EntityWithState *)self)->state != state;
    // A hit is only a real one (the user's random double jumps, 2026-10-02): the object destroyed; a badnik broken
    // (Player_CheckBadnikBreak's score, also the ones it doesn't destroy itself); a monitor breaking (ItemBox_State_Break:
    // its later states, half a second on, aren't); a breakable or a boss changing state as it sends her off; a boss's
    // hit (Player_CheckBossHit: her speed turned round where she is; a solid boss body pushing her moves her too). Not a
    // monitor's or anything's solid sides and lid stopping her (no bounce off a monitor touched from below or the side)
    bool32 broke = kind == HIT_ITEMBOX && g_btBoxBreak && state != g_btBoxBreak && newState
                   && ((EntityWithState *)self)->state == g_btBoxBreak;
    bool32 scored = p->score != score || p->scoreBonus != bonus;
    bool32 struck = kind != HIT_ITEMBOX && moved && (newState || (kind == HIT_BOSS && p->position.x == pos.x && p->position.y == pos.y));
    if (spinning && !Hurt(p) && (gone || broke || scored || struck)) {
        g_bt.spinHit = true;
        p->velocity  = vel; // (the bounce is the spin's own: SpinAttack)
    }
    else if (lid && p->velocity.y == 0) {
        p->velocity.y = vel.y; // (no touch: still rising)
    }
    if (p->animator.animationID == ANI_JUMP && anim != ANI_JUMP && !Hurt(p))
        p->animator.animationID = anim;
    if (p->invincibleTimer == BT_JUGG_INV)
        p->invincibleTimer = inv;
    return true;
}

// The generic Projectile's update (wrapped when a package has the Charge): the Juggernaut is invincible to it
static void BatchProjectileUpdate(void)
{
    Entity *self    = SceneInfo->entity;
    EntityPlayer *p = Player ? (EntityPlayer *)RSDK.GetEntity(SLOT_PLAYER1) : NULL;
    bool32 jugg     = g_active && g_btOn && p && Juggernaut(p) && !p->invincibleTimer;
    if (jugg)
        p->invincibleTimer = BT_JUGG_INV;
    Mod.Super(self->classID, SUPER_UPDATE, NULL);
    if (jugg && p->invincibleTimer == BT_JUGG_INV)
        p->invincibleTimer = 0;
}

// ------------------------------------------------------------------------------------------------ the draw
// The Player's draw (MoreDraw), around his own: Honey's spin drawn leaning toward her travel (spin_lean: 5 / 512 of a turn
// per px per frame, 32 at most, eased in and out over 8 frames: S3&K's SPIN_LEAN) and the Shine Spark's glow (his greys
// toward white-hot: stored, levels 0 1 2 1 pulsing, 4 frames each, 2 in its last second; flying, 2), only while his
// sprite draws (MoreDraw puts his rotation back after)
static int32 g_btGlowLevel = -1;
static color g_btGlowSaved[BATCH_GLOW_MAX];

static void BatchDrawBefore(EntityPlayer *self)
{
    g_btGlowLevel = -1;
    if (!g_btOn || RSDK.GetEntitySlot(self) != SLOT_PLAYER1)
        return;
    const BatchData *c = &g_cur->more.batch;
    if (g_btSpin && g_bt.spin > 0 && (Showing(self, g_btAnim[BA_ATTACK]) || Showing(self, g_btAnim[BA_SHOT]))) {
        bool32 air = !self->onGround;
        int32 v    = air ? self->velocity.x : self->groundVel;
        int32 lean = Clamp((int32)((int64)v * 5 / 0x10000), -32, 32);
        int32 ease = BtMin(g_bt.spin - 1, 8);
        if (g_bt.spin > c->spinFrames - 7)
            ease = c->spinFrames + 1 - g_bt.spin;
        lean           = lean * BtMax(ease, 0) / 8;
        self->rotation = ((air ? 0 : self->angle << 1) + lean) & 0x1FF;
    }
    if (g_btSpark && g_bt.spark > 0) {
        int32 k = 2;
        if (g_bt.spark < BT_SPARK_ACTIVE) {
            k = (g_bt.spark > 60 ? g_bt.spark >> 2 : g_bt.spark >> 1) & 3;
            if (k == 3)
                k = 1;
        }
        if (c->glowCount[k] > 0) {
            g_btGlowLevel = k;
            for (int32 i = 0; i < c->glowCount[k]; ++i) {
                g_btGlowSaved[i] = RSDK.GetPaletteEntry(0, c->glowSlot[k][i]);
                RSDK.SetPaletteEntry(0, c->glowSlot[k][i], c->glowColour[k][i]);
            }
        }
    }
}

static void BatchDrawAfter(EntityPlayer *self)
{
    (void)self;
    if (g_btGlowLevel < 0)
        return;
    const BatchData *c = &g_cur->more.batch;
    for (int32 i = 0; i < c->glowCount[g_btGlowLevel]; ++i) RSDK.SetPaletteEntry(0, c->glowSlot[g_btGlowLevel][i], g_btGlowSaved[i]);
    g_btGlowLevel = -1;
}

// ------------------------------------------------------------------------------------------------ jump, frame, stage, link
// Hook_JumpAbilitySonic's press (jumpAbilityState 1, jump pressed, in the air state): the extra's move, noted for BatchUpdate
static bool32 BatchJump(EntityPlayer *self)
{
    if (!g_btOn || RSDK.GetEntitySlot(self) != SLOT_PLAYER1)
        return false;
    const BatchData *c = &g_cur->more.batch;
    if (!(g_btRide || (g_btEar && c->grappleY) || g_btSpirit || g_btGear || g_btPuddle || g_btWarp))
        return false;
    g_bt.trigger = true;
    return true;
}

// The extra's hits need the hit classes (ShotsStageLoad fills them for it): the ear, the spin, the charge
static bool32 BatchHits(void)
{
    const BatchData *c = g_cur ? &g_cur->more.batch : NULL;
    return c && (c->earGrapple || c->spinAttack || c->charge);
}
static bool32 BatchNeedsHits(const Extra *e) { return e->more.batch.earGrapple || e->more.batch.spinAttack || e->more.batch.charge; }

// Player 1's frame (OnUpdate, the game running), after the sink / anchor and before the shots and the melee
static void BatchUpdate(EntityPlayer *p, bool32 transformed)
{
    bool32 trigger = g_bt.trigger;
    g_bt.trigger   = false;
    if (!g_btOn || !IsExtra(p))
        return;
    const Abilities *ab = &g_cur->ab;
    const BatchData *c  = &g_cur->more.batch;
    bool32 air          = !p->onGround;
    bool32 left         = (p->direction & FLIP_X) != 0;
    if (Hurt(p) || !Free(p)) { // a hit, or an object holding him: whatever was going on is over
        if (!g_bt.reset)
            BtReset(p);
        g_bt.reset = true;
        return;
    }
    g_bt.reset = false;
    if (!air) {
        g_bt.bomb   = 0;
        g_bt.hover  = 0;
        g_bt.spirit = 0;
        if (g_bt.ear > 0 && g_bt.ear < BT_EAR_SNAP)
            g_bt.ear = 0;
    }
    if (g_btRide)
        RocketRide(p, ab, c, trigger && g_bt.ear <= 0, air, left);
    if (g_btEar)
        EarGrapple(p, ab, c, trigger, air, transformed);
    if (g_btSpirit)
        SpiritFlight(p, c, trigger, air);
    if (g_btPuddle)
        PuddleSlide(p, c, trigger, air);
    if (g_btCling)
        WallCling(p, c, air);
    if (g_btGear)
        ExtremeGear(p, c, trigger, air);
    if (g_btCharge)
        Charge(p, c, air);
    if (g_btSpark)
        Spark(p, c, air);
    if (g_btSpin)
        SpinAttack(p, c, air, transformed);
    if (g_btWarp)
        PhaseWarp(p, c, trigger, air);
}

static void BatchStageLoad(void)
{
    memset(&g_bt, 0, sizeof(g_bt));
    g_bt.chargeAnim = g_bt.spinAnim = -1;
    g_btOn = g_btRide = g_btEar = g_btSpirit = g_btCling = g_btGear = g_btPuddle = g_btCharge = g_btSpark = g_btSpin = g_btWarp = false;
    if (!g_cur || !g_active)
        return;
    const BatchData *c  = &g_cur->more.batch;
    const Abilities *ab = &g_cur->ab;
    for (int32 k = 0; k < BA_COUNT; ++k) g_btAnim[k] = HasAnim(g_cur->animBase + k);
    bool32 ground = Player_State_Ground_ && Player_State_Crouch_ && Player_State_LookUp_;
    g_btRide   = c->bombJump && g_btAnim[BA_ATTACK] >= 0 && (!ab->hover || g_btAnim[BA_HOVER] >= 0);
    g_btEar    = c->earGrapple && g_btAnim[BA_ATTACK] >= 0 && (!ab->hover || g_btAnim[BA_HOVER] >= 0);
    g_btSpirit = c->spiritFlight && g_btAnim[BA_ATTACK] >= 0;
    g_btCling  = c->wallCling && g_btAnim[BA_CLING] >= 0;
    g_btGear   = c->extremeGear && g_btAnim[BA_ATTACK] >= 0;
    g_btPuddle = c->puddleSlide && g_btAnim[BA_ATTACK] >= 0 && g_btAnim[BA_HOVER] >= 0 && ground;
    g_btCharge = c->charge && g_btAnim[BA_ATTACK] >= 0 && g_btAnim[BA_HOVER] >= 0 && g_btAnim[BA_SHOT] >= 0 && ground;
    g_btSpark  = g_btCharge && c->sparkSpeed > 0 && c->sparkStore > 0 && g_btAnim[BA_UP] >= 0 && g_btInputHooked;
    g_btSpin   = c->spinAttack && g_btAnim[BA_ATTACK] >= 0 && g_btAnim[BA_SHOT] >= 0 && ground;
    g_btWarp   = c->phaseWarp && g_btAnim[BA_ATTACK] >= 0;
    g_btOn     = g_btRide || g_btEar || g_btSpirit || g_btCling || g_btGear || g_btPuddle || g_btCharge || g_btSpin || g_btWarp;
    if (!g_btOn && !(c->bombJump || c->earGrapple || c->spiritFlight || c->wallCling || c->extremeGear || c->puddleSlide || c->charge
                     || c->spinAttack || c->phaseWarp))
        return;
    g_btRideSfx   = SfxOf(c->rideSound);
    g_btBlastSfx  = SfxOf(c->blastSound);
    g_btGearSfx   = SfxOf(c->gearSound);
    g_btPuddleSfx = SfxOf(c->puddleSound);
    g_btStoreSfx  = SfxOf(c->sparkStoreSound);
    g_btSparkSfx  = SfxOf(c->sparkSound);
    g_btSpinSfx   = SfxOf(c->spinSound);
    g_btBoxBreak  = g_btSpin ? Mod.GetPublicFunction(NULL, "ItemBox_State_Break") : NULL;
    g_btWarpSfx   = SfxOf(c->warpSound);
    if (g_btEar) {
        g_engineFrameOK = CheckEngineFrames();
        memset(&g_earFrame, 0, sizeof(g_earFrame));
        g_earFrame.hitboxCount = 1;
        for (int32 i = 0; i < 8; ++i) {
            g_earFrame.hitboxes[i].left = g_earFrame.hitboxes[i].top = -BT_EAR_BOX;
            g_earFrame.hitboxes[i].right = g_earFrame.hitboxes[i].bottom = BT_EAR_BOX;
        }
        memset(&g_earBox, 0, sizeof(g_earBox));
        g_earBox.frames      = (SpriteFrame *)&g_earFrame;
        g_earBox.frameCount  = 1;
        g_earBox.animationID = ANI_JUMP;
    }
    RSDK.PrintLog(PRINT_NORMAL, LOG_TAG "%s: rocket ride %d, ear grapple %d, spirit %d, wall cling %d, gear %d, puddle %d, charge %d (spark %d, "
                  "glow %d), spin %d, warp %d; anims %d %d %d %d %d %d; hits %s",
                  g_cur->name, g_btRide, g_btEar, g_btSpirit, g_btCling, g_btGear, g_btPuddle, g_btCharge, g_btSpark, c->glowCount[0],
                  g_btSpin, g_btWarp, g_btAnim[0], g_btAnim[1], g_btAnim[2], g_btAnim[3], g_btAnim[4], g_btAnim[5],
                  g_hitsOn ? "on" : "OFF (no ear hits, spin bounces or Juggernaut)");
}

// Link (after LinkMore): the Player's draw wrapped if LinkMore didn't (the spin lean, the spark glow), the input hook (the
// Shine Spark), the generic Projectile's update (the Juggernaut)
static void LinkBatch(void)
{
    bool32 draw = false, spark = false, charge = false;
    for (int32 i = 0; i < g_extraCount; ++i) {
        const BatchData *c = &g_extras[i].more.batch;
        draw |= c->spinAttack || (c->charge && c->sparkSpeed > 0);
        spark |= c->charge && c->sparkSpeed > 0;
        charge |= c->charge != 0;
    }
    if (draw && !g_drawWrapped) {
        Mod.RegisterObject(NULL, NULL, "Player", sizeof(EntityPlayer), 0, 0, NULL, NULL, NULL, MoreDraw, NULL, NULL, NULL, NULL, NULL, NULL,
                           NULL);
        g_drawWrapped = true;
    }
    if (spark && Player_Input_P1_) {
        Mod.RegisterStateHook(Player_Input_P1_, Hook_BatchInput, false);
        g_btInputHooked = true;
    }
    if (charge) {
        Mod.RegisterObject(NULL, NULL, "Projectile", 0, 0, 0, BatchProjectileUpdate, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                           NULL);
        g_btProjWrapped = true;
    }
}

#endif // MANIA_BATCH_H
