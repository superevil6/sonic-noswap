// Ristar's moves in S3&K (tools/star_grab.py, the same states and numbers as Sonic 1/2 and CD; included by NoSwapS3K.cpp
// right before Abilities, so the helpers above are in scope). The user's design (2026-09-29):
// - Y: the Grab, aimed 8 ways with the d-pad (nothing held: forward; on the ground, down doesn't aim). His arms stretch
//   out grabStep px a frame for grabFrames frames and come back in retractFrames. The arms are drawn at runtime, as the
//   game draws them (vector lines): two 2 px black lines (RSDK DrawLine) from his body to his hands, the hands being slot
//   43's frames ("Hands", ANI_EXTRA(2): 8 directions open, then gripping), drawn in the Player's draw (StarDraw).
//   - A badnik his hands reach (Player_CheckBadnikTouch, the shots' hook: StarTouch) is caught, not touched: he's
//     yanked in to it (an attack: reported as the jump) and his body's touch breaks it (the game's own break and bounce);
//     then he bounces off it.
//   - Solid terrain at a hand (TerrainAt, the Ear Grapple's test) is caught: he's pulled in, and next to a wall or under
//     a ceiling he hangs there (pinned in place; slot 42: the Ladder / Overhead frames). Up / down climb a wall (past its
//     top: a hop onto the ledge), left / right move along a ceiling; a jump press and release lets go with a hop.
//   - Nothing caught: the arms come back.
// - Meteor Strike: hanging, hold jump (the wind-up from windupShow frames: the swing frames, drawn round his grip); let
//   go after windupFull frames or more and he flies where the d-pad points (nothing held: away from the wall, or the way
//   he faces) at meteorSpeed for meteorFrames, attacking and untouchable (the blink timer at 3); landing or a wall ends it.
// Runs after the game's update, so the velocities set here move him next frame, after the air state's gravity (taken
// off in advance).

static Entity* CurrentEntity(int* slotOut);  // (NoSwapS3K.cpp, below)

namespace star {
constexpr int PULL = 100, RETRACT = 200, YANK = 300, WALL = 1000, CEILING = 2000, METEOR = 3000;
constexpr int F_AIR = 5, F_PULL = 10, F_HEADBUTT = 15, F_METEOR = 16, F_CEILING = 9, F_SWING = 18, LADDER = 9, SWING = 8;
constexpr int WALL_X = 14, CEILING_Y = -24;
constexpr int UX[8] = {256, 181, 0, -181, -256, -181, 0, 181};
constexpr int UY[8] = {0, -181, -256, -181, 0, 181, 256, 181};
constexpr int DIR_OF[9] = {3, 2, 1, 4, 0, 0, 5, 6, 7};  // (x + 1) + 3 * (y + 1) -> direction
constexpr int CLASS[8] = {0, 1, 2, 1, 0, 3, 4, 3};      // direction -> aim class (slot 41's frames)

struct State {
    int state = 0;       // tools/star_grab.py's numbers (0: none)
    int dir = 0;         // the aim (0 right, counterclockwise), or while on a wall its side (0 right, 1 left)
    Vector2 latch{};     // the point caught
    Vector2 hand{};      // where the hands are this frame (StarTouch)
    Vector2 pin{};       // hanging: where he's held
    Vector2 last{};      // his position last frame (a pull stopped by the terrain)
    void* groundState = nullptr;  // the plain ground state (seen while he stands, walks or runs)
};
static State g{};

static bool On() { return g_character > 0 && g_extraFrames && Extra(g_character).abilities.starGrab; }

static int DirFrom(int x, int y) { return DIR_OF[(x + 1) + 3 * (y + 1)]; }

static void End(EntityPlayer* p, bool air) {
    g.state = 0;
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

static void Frame(EntityPlayer* p, int anim, int frame, bool attacking) {
    // (PlayExtraAnimation alone can't tell: an attack shows as ANI_JUMP, and in the air he's already in the jump, so
    // the reaching body never replaced his jump frames and his gloves showed twice (the user, 2026-09-29). So the
    // animator's frames are compared with this animation's own.)
    Animator probe{};
    RSDK->SetSpriteAnimation(g_extraFrames, anim, &probe, true, 0);
    if (p->animator.frames != probe.frames)
        RSDK->SetSpriteAnimation(g_extraFrames, anim, &p->animator, true, 0);
    if (attacking)
        p->animator.animationID = ANI_JUMP;
    p->animator.frameID = frame;
    p->animator.timer = 0;
}

static void Face(EntityPlayer* p, int dir) {
    if (UX[dir] > 0)
        p->direction = 0;
    if (UX[dir] < 0)
        p->direction = 1;
}

// Along the line to the point caught at `speed` (the air state's gravity taken off in advance); on the ground a point well
// above lifts him off, otherwise he's drawn along the ground to it
static void PullTo(EntityPlayer* p, int speed, bool air) {
    double dx = g.latch.x - p->position.x, dy = g.latch.y - p->position.y, len = std::sqrt(dx * dx + dy * dy);
    if (!air) {
        if (dy < -(12 << 16)) {
            ToAir(p);
            p->velocity.x = 0;
            p->velocity.y = -0x10000;
            p->groundVel = 0;
        } else {
            p->groundVel = dx < 0 ? -speed : speed;
        }
        return;
    }
    if (len > 0) {
        p->velocity.x = (int)(speed * dx / len);
        p->velocity.y = (int)(speed * dy / len) - Gravity(p);
    }
}

// Pulled in to what the hands caught: hang on a wall (the latch's side first) or under a ceiling, or let go
static void Hang(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    p->velocity.x = 0;
    p->velocity.y = air ? -Gravity(p) : 0;
    p->groundVel = 0;
    if (!air) {
        End(p, false);
        return;
    }
    int side = g.latch.x < p->position.x ? 1 : 0;
    for (int k = 0; k < 2; k++, side ^= 1) {
        if (TerrainAt(p, side ? -WALL_X : WALL_X, 0)) {
            g.state = WALL;
            g.dir = side;
            g.pin = p->position;
            p->direction = side;
            Log("ristar: hangs on a wall (%s)", side ? "left" : "right");
            return;
        }
    }
    if (TerrainAt(p, 0, CEILING_Y)) {
        g.state = CEILING;
        g.pin = p->position;
        Log("ristar: hangs under a ceiling");
        return;
    }
    g.state = 0;  // nothing to hold on to: let go with a hop
    p->velocity.y = -c.hangHop;
    NoJumpCap(p);
    BackToJump(p);
}

static void Launch(EntityPlayer* p, const ExtraAbilities& c, bool wall) {
    int x = p->right ? 1 : p->left ? -1 : 0, y = p->down ? 1 : p->up ? -1 : 0;
    if (x == 0 && y == 0)
        x = wall ? (g.dir ? 1 : -1) : ((p->direction & 1) ? -1 : 1);  // away from a wall, or the way he faces
    g.dir = DirFrom(x, y);
    g.state = METEOR + c.meteorFrames;
    NoJumpCap(p);
    if (c.meteorSound)
        PlaySound(c.meteorSound);
    Log("ristar: meteor strike (direction %d)", g.dir);
}

// Hanging: still attached, climbing, jump (a press and release: let go; held windupFull frames: the Meteor Strike)
static void HangUpdate(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!air) {  // down onto the floor
        End(p, false);
        return;
    }
    int kind = g.state >= CEILING ? CEILING : WALL;
    int held = g.state - kind;
    if (p->jumpPress && held == 0)
        held = 1;
    if (held > 0) {
        if (p->jumpHold) {
            held = std::min(held + 1, 999);
        } else if (held >= c.windupFull) {  // let go of a full wind-up
            Launch(p, c, kind == WALL);
            return;
        } else {  // a hop off (down held: he just drops)
            g.state = 0;
            p->velocity.y = (p->down && !p->up) ? 0 : -c.hangHop;
            p->velocity.x = kind == WALL ? (g.dir ? c.hangPush : -c.hangPush) : 0;
            NoJumpCap(p);
            BackToJump(p);
            return;
        }
    }
    if (held == 0) {  // climbing along
        if (kind == WALL)
            g.pin.y += p->up ? -c.climbSpeed : p->down ? c.climbSpeed : 0;
        else
            g.pin.x += p->left ? -c.climbSpeed : p->right ? c.climbSpeed : 0;
    }
    p->position = g.pin;
    p->velocity.x = 0;
    p->velocity.y = -Gravity(p);
    p->groundVel = 0;
    bool attached = kind == WALL ? TerrainAt(p, g.dir ? -WALL_X : WALL_X, 0) : TerrainAt(p, 0, CEILING_Y);
    if (!attached) {  // nothing to hold any more
        g.state = 0;
        if (kind == WALL && p->up) {  // climbed past the top: a hop onto the ledge
            p->velocity.y = -c.hangHop;
            p->velocity.x = g.dir ? -c.hangPush / 2 : c.hangPush / 2;
            NoJumpCap(p);
        }
        BackToJump(p);
        return;
    }
    g.state = kind + held;
    if (kind == WALL)
        p->direction = g.dir;
    int frame;
    if (held >= c.windupShow) {
        frame = F_SWING + (held >> (held < c.windupFull ? 2 : 1)) % SWING;
    } else {
        int along = (kind == WALL ? p->position.y : p->position.x) >> 16;
        frame = ((along >> 3) % LADDER + LADDER) % LADDER + (kind == CEILING ? F_CEILING : 0);
    }
    Frame(p, ANI_EXTRA_HOVER, frame, false);
}

static void Update(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1);
    if (!air && plain && p->state.state && g.state == 0)
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
    if (g.state <= 0 && !Hurt(p) && inState && (air || plain) && YPressed(p)) {
        int x = p->right ? 1 : p->left ? -1 : 0, y = p->up ? -1 : (p->down && air) ? 1 : 0;
        if (x == 0 && y == 0)
            x = (p->direction & 1) ? -1 : 1;
        if (x)
            p->direction = x < 0 ? 1 : 0;
        g.dir = DirFrom(x, y);
        g.state = 1;
        if (c.grabSound)
            PlaySound(c.grabSound);
        Log("ristar: grab (direction %d, %s)", g.dir, air ? "air" : "ground");
    }
    if (g.state <= 0)
        return;
    g_ab.ready = false;  // (no jump ability meanwhile)
    const int cls = CLASS[g.state >= WALL ? 0 : g.dir];
    if (g.state < PULL) {  // the arms going out: does a hand reach solid terrain?
        int len = g.state * c.grabStep, tx = UX[g.dir] * len / 256, ty = UY[g.dir] * len / 256;
        g.hand = {p->position.x + (tx << 16), p->position.y + (ty << 16)};
        if (TerrainAt(p, tx, ty)) {
            g.latch = g.hand;
            g.state = PULL + 1;
            if (c.latchSound)
                PlaySound(c.latchSound);
            Log("ristar: caught terrain");
        } else if (++g.state > c.grabFrames) {
            g.state = RETRACT + c.retractFrames;
        }
    } else if (g.state < RETRACT) {  // pulled in: there yet?
        int dx = std::abs((g.latch.x - p->position.x) >> 16), dy = std::abs((g.latch.y - p->position.y) >> 16);
        bool stopped = g.state > PULL + 2 && (air ? std::abs(p->position.x - last.x) < 0x8000
                                                        && std::abs(p->position.y - last.y) < 0x8000
                                                  : p->groundVel == 0);
        if ((dx < c.latchRange && dy < c.latchRange) || g.state >= PULL + c.reelFrames || stopped) {
            Hang(p, c, air);
            if (g.state == 0 || g.state >= WALL)
                return;
        } else {
            g.state++;
            PullTo(p, c.reelSpeed, air);
        }
    } else if (g.state < YANK) {  // the arms coming back
        if (--g.state == RETRACT) {
            End(p, air);
            return;
        }
    } else if (g.state < WALL) {  // yanked in to the badnik: close enough, a bounce off it
        int dx = std::abs((g.latch.x - p->position.x) >> 16), dy = std::abs((g.latch.y - p->position.y) >> 16);
        if ((dx < c.yankRange && dy < c.yankRange) || g.state >= YANK + c.yankFrames) {
            g.state = 0;
            if (!air)
                ToAir(p);
            p->velocity.y = -c.bounceY;
            p->velocity.x = (p->direction & 1) ? c.bounceX : -c.bounceX;
            NoJumpCap(p);
            BackToJump(p);
            return;
        }
        g.state++;
        PullTo(p, c.yankSpeed, air);
        Frame(p, ANI_EXTRA_ATTACK, dx < 32 && dy < 32 ? F_HEADBUTT : F_PULL + cls, true);
        Face(p, g.dir);
        return;
    } else if (g.state < METEOR) {
        HangUpdate(p, c, air);
        return;
    } else {  // the Meteor Strike
        int left = g.state - METEOR - 1;
        bool stopped = left < c.meteorFrames - 1 && std::abs(p->position.x - last.x) < 0x10000
                       && std::abs(p->position.y - last.y) < 0x10000;
        if (!air || left <= 0 || stopped) {
            End(p, air);
            return;
        }
        g.state--;
        p->velocity.x = UX[g.dir] * (c.meteorSpeed >> 8);
        p->velocity.y = UY[g.dir] * (c.meteorSpeed >> 8) - Gravity(p);
        if (g_blinkOffset >= 0) {  // nothing hurts him (without the flicker)
            int& blink = *(int*)((char*)p + g_blinkOffset);
            if (blink < 3)
                blink = 3;
        }
        Frame(p, ANI_EXTRA_ATTACK, F_METEOR + 3 * CLASS[g.dir] + (left >> 2) % 3, true);
        Face(p, g.dir);
        return;
    }
    // the arms out or coming back, or pulled in: held still (no falling), the frame
    if (g.state < PULL || (g.state > RETRACT && g.state < YANK)) {
        if (air) {
            if (p->velocity.y > -Gravity(p))
                p->velocity.y = -Gravity(p);
        } else {
            p->groundVel = 0;
            p->velocity.x = 0;
        }
    }
    bool pulled = g.state > PULL && g.state < RETRACT;
    Frame(p, ANI_EXTRA_ATTACK, pulled ? F_PULL + cls : (air ? F_AIR : 0) + cls, air);
    Face(p, g.dir);
}

// Player_CheckBadnikTouch (the shots' hook): while his arms go out, a badnik a hand reaches (8 px round it, in its
// hitbox) is caught: yanked in, not touched this frame (his body's touch breaks it)
static bool Touch(EntityPlayer* p, Entity* e, Hitbox* hitbox) {
    if (!On() || !p || !e || !hitbox || g.state <= 0 || g.state >= PULL || RSDK->GetEntitySlot(p) != 0)
        return false;
    int hx = (g.hand.x - e->position.x) >> 16, hy = (g.hand.y - e->position.y) >> 16;
    if (hx < hitbox->left - 8 || hx > hitbox->right + 8 || hy < hitbox->top - 8 || hy > hitbox->bottom + 8)
        return false;
    g.latch = e->position;
    g.state = YANK + 1;
    if (Extra(g_character).abilities.latchSound)
        PlaySound(Extra(g_character).abilities.latchSound);
    Log("ristar: caught a badnik (slot %d)", RSDK->GetEntitySlot(e));
    return true;
}

// The Player's draw, wrapped: for Ristar, his body (in the wind-up, the swing frame round his grip), then his arms (two 2
// px black lines each side of the aim) and his hands (slot 43's frame for the aim, drawn facing right: absolute frames)
typedef void (*DrawFn)(void);
static DrawFn g_draw = nullptr;
static void Draw() {
    int slot = -1;
    Entity* self = CurrentEntity(&slot);
    if (!self || slot != 0 || !On()) {
        g_draw();
        return;
    }
    auto* p = (EntityPlayer*)self;
    const ExtraAbilities& c = Extra(g_character).abilities;
    Vector2 at = p->position;
    uint8 dir = p->direction;
    bool winding = g.state >= WALL && g.state < METEOR && g.state % 1000 >= c.windupShow;
    if (winding) {  // round his grip, the body swinging out away from a wall
        if (g.state >= CEILING) {
            p->position.y -= 20 << 16;
        } else {
            p->position.x += (g.dir ? -12 : 12) << 16;
            p->position.y -= 4 << 16;
            p->direction = g.dir ? 0 : 1;
        }
    }
    g_draw();
    p->position = at;
    p->direction = dir;
    if (g.state <= 0 || g.state >= WALL)
        return;
    int dx, dy;
    bool grip = (g.state > PULL && g.state < RETRACT) || g.state > YANK;
    if (grip) {
        dx = (g.latch.x - p->position.x) >> 16;
        dy = (g.latch.y - p->position.y) >> 16;
    } else {
        int len = g.state < PULL ? g.state * c.grabStep
                                 : (g.state - RETRACT) * (c.grabFrames * c.grabStep / std::max(1, c.retractFrames));
        dx = UX[g.dir] * len / 256;
        dy = UY[g.dir] * len / 256;
    }
    int n = std::max({std::abs(dx), std::abs(dy), 1});
    int ox = -dy * 3 / n, oy = dx * 3 / n;  // the arms: 3 px either side of the aim
    bool flat = std::abs(dx) >= std::abs(dy);
    for (int side = -1; side <= 1; side += 2) {
        int x1 = p->position.x + ((side * ox) << 16), y1 = p->position.y + ((side * oy) << 16);
        int x2 = x1 + (dx << 16), y2 = y1 + (dy << 16);
        for (int t = 0; t < 2; t++) {  // 2 px thick
            int sx = flat ? 0 : t << 16, sy = flat ? t << 16 : 0;
            RSDK->DrawLine(x1 + sx, y1 + sy, x2 + sx, y2 + sy, 0x000000, 0xFF, 0, false);
        }
    }
    Animator hand{};
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA(2), &hand, true, g.dir + (grip ? 8 : 0));
    int rotation = p->rotation;
    p->direction = 0;
    p->rotation = 0;
    for (int side = -1; side <= 1; side += 2) {
        Vector2 pos = {p->position.x + ((dx + side * ox) << 16), p->position.y + ((dy + side * oy) << 16)};
        RSDK->DrawSprite(&hand, &pos, false);
    }
    p->direction = dir;
    p->rotation = rotation;
}

static DrawFn Wrap(DrawFn draw) {
    if (draw != (DrawFn)Draw)
        g_draw = draw;
    return Draw;
}
}  // namespace star

static bool StarTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox) { return star::Touch(p, e, hitbox); }
static void StarGrab(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!star::On())
        return;
    star::Update(p, c, air);
}
