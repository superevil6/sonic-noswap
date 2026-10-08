// Dynamite Headdy's Head Throw in S3&K (tools/head_throw.py, the same states and numbers as Sonic 1/2 and CD; included
// by NoSwapS3K.cpp after StarGrab.h, right before Abilities, so the helpers above are in scope). The user's design
// (2026-09-29):
// - Y: the Head Throw, aimed 8 ways with the d-pad (nothing held: forward; on the ground, down doesn't aim). His head
//   flies out headStep px a frame for headFrames frames from his neck and comes straight back as fast, while his body
//   stands headless (slot 41: the throwing bodies per aim class, an attack). The head is drawn in the Player's draw
//   (HeadDraw: slot 43's frame, ANI_EXTRA(2), for the variant, the aim class and out / back, mirrored with his facing).
// - A badnik, monitor or boss the head reaches (Player_CheckBadnikTouch, the shots' hook: HeadTouch) is touched: the
//   game takes it as his attack (reported as the jump), and a head going out comes back. Solid terrain at the head
//   (TerrainAt) sends it back too. No grabbing. On the ground he stands still for it; in the air he falls as usual.
// - Head variants (power-up heads): g_variant, the index the shared monitor_swap module will set (0: his own head); its
//   numbers are headStep / headFrames[g_variant], its art slot 43's frames g_variant * HEAD_FRAMES and up.

static Entity* CurrentEntity(int* slotOut);  // (NoSwapS3K.cpp, below)

namespace head {
constexpr int BACK = 200, F_AIR = 5, HEAD_FRAMES = 10, F_BACK = 5, HEAD_Y = -6;
constexpr int UX[8] = {256, 181, 0, -181, -256, -181, 0, 181};
constexpr int UY[8] = {0, -181, -256, -181, 0, 181, 256, 181};
constexpr int DIR_OF[9] = {3, 2, 1, 4, 0, 0, 5, 6, 7};  // (x + 1) + 3 * (y + 1) -> direction
constexpr int CLASS[8] = {0, 1, 2, 1, 0, 3, 4, 3};      // direction -> aim class (slot 41's / 43's frames)

int g_variant = 0;  // the head variant (the monitor_swap module's; 0: his own head)

struct State {
    int state = 0;       // tools/head_throw.py's numbers (0: none)
    int dir = 0;         // the aim (0 right, counterclockwise)
    Vector2 last{};      // his position last frame (a warp ends it)
    void* groundState = nullptr;  // the plain ground state (seen while he stands, walks or runs)
};
static State g{};

static bool On() { return g_character > 0 && g_extraFrames && Extra(g_character).abilities.headThrow; }

static int Variant(const ExtraAbilities& c) {
    return g_variant >= 0 && g_variant < c.headVariants ? g_variant : 0;
}

// The head's place, px from his centre
static void Tip(const ExtraAbilities& c, int* x, int* y) {
    int len = (g.state > BACK ? g.state - BACK : g.state) * c.headStep[Variant(c)];
    *x = UX[g.dir] * len / 256;
    *y = UY[g.dir] * len / 256 + HEAD_Y;
}

static void Frame(EntityPlayer* p, int anim, int frame) {
    Animator probe{};
    RSDK->SetSpriteAnimation(g_extraFrames, anim, &probe, true, 0);
    if (p->animator.frames != probe.frames)
        RSDK->SetSpriteAnimation(g_extraFrames, anim, &p->animator, true, 0);
    p->animator.animationID = ANI_JUMP;  // (an attack)
    p->animator.frameID = frame;
    p->animator.timer = 0;
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
        g.state = 0;  // (a new stage, a respawn, a warp)
    if (g.state > 0 && (Hurt(p) || Held(p) || !inState)) {
        g.state = 0;
        return;
    }
    if (g.state <= 0 && !Hurt(p) && inState && (air || plain) && YPressed(p)) {
        int x = p->right ? 1 : p->left ? -1 : 0, y = p->up ? -1 : (p->down && air) ? 1 : 0;
        if (x == 0 && y == 0)
            x = (p->direction & 1) ? -1 : 1;
        if (x)
            p->direction = x < 0 ? 1 : 0;
        g.dir = DIR_OF[(x + 1) + 3 * (y + 1)];
        g.state = 1;
        if (c.headSound)
            PlaySound(c.headSound);
        Log("headdy: head throw (direction %d, %s, variant %d)", g.dir, air ? "air" : "ground", Variant(c));
    }
    if (g.state <= 0)
        return;
    if (g.state < BACK) {  // going out: solid terrain at the head sends it back
        int tx, ty;
        Tip(c, &tx, &ty);
        if (TerrainAt(p, tx, ty))
            g.state += BACK;
        else if (++g.state > c.headFrames[Variant(c)])
            g.state = BACK + c.headFrames[Variant(c)];
    } else if (--g.state <= BACK) {  // coming back: home
        g.state = 0;
        if (air)
            BackToJump(p);
        else
            RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
        return;
    }
    if (!air) {
        p->groundVel = 0;
        p->velocity.x = 0;
    }
    Frame(p, ANI_EXTRA_ATTACK, (air ? F_AIR : 0) + CLASS[g.dir]);
    if (UX[g.dir] > 0)
        p->direction = 0;
    if (UX[g.dir] < 0)
        p->direction = 1;
}

// Player_CheckBadnikTouch (the shots' hook): while his head is away, anything it reaches (10 px round it, in the
// entity's hitbox) is touched (the game then takes it as his attack); a head going out comes back
static bool Touch(EntityPlayer* p, Entity* e, Hitbox* hitbox) {
    if (!On() || !p || !e || !hitbox || g.state <= 0 || RSDK->GetEntitySlot(p) != 0)
        return false;
    int tx, ty;
    Tip(Extra(g_character).abilities, &tx, &ty);
    int hx = ((p->position.x - e->position.x) >> 16) + tx, hy = ((p->position.y - e->position.y) >> 16) + ty;
    if (hx < hitbox->left - 10 || hx > hitbox->right + 10 || hy < hitbox->top - 10 || hy > hitbox->bottom + 10)
        return false;
    if (g.state < BACK)
        g.state += BACK;
    return true;
}

// The Player's draw, wrapped: for Headdy, his body, then his thrown head
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
    int tx, ty;
    Tip(c, &tx, &ty);
    Animator head{};
    int frame = Variant(c) * HEAD_FRAMES + (g.state > BACK ? F_BACK : 0) + CLASS[g.dir];
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA(2), &head, true, frame);
    int rotation = p->rotation;
    p->rotation = 0;
    Vector2 pos = {p->position.x + (tx << 16), p->position.y + (ty << 16)};
    RSDK->DrawSprite(&head, &pos, false);
    p->rotation = rotation;
}

static DrawFn Wrap(DrawFn draw) {
    if (draw != (DrawFn)Draw)
        g_draw = draw;
    return Draw;
}
}  // namespace head

static bool HeadTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox) { return head::Touch(p, e, hitbox); }
static void HeadThrow(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    if (!head::On())
        return;
    head::Update(p, c, air);
}
