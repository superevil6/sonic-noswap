// Water walk in S3&K (tools/water_walk.py, the same rule as Sonic 1/2 and CD: Marine's sea legs; included by NoSwapS3K.cpp
// after AnchorThrow.h). Above water, the water's surface is ground for her: after the game's update (where it found no
// floor under her), in a free state, not moving up, down not held, her feet (her centre plus the current frame's outer
// box bottom) at or below the surface and last frame's no more than TOL_AIR px under it (TOL_GROUND either side while
// she's on it already, riding a bobbing or rising surface), and room over her head: her feet go on the surface, she's
// on the ground (angle 0, floor mode; landing in the air state, the state itself turns to the ground one next frame, as
// with any landing), her speed along kept. Down held dives through it; she only lands on it from above.
//
// The surface: the Water object's waterLevel (16.16), the int at +4 of its statics (Mania's ObjectWater layout). Its
// statics pointer is what RegisterObject got for "Water" (g_waterStatics); this build's Water update reads the level there
// and compares the player's position.y with it (0x1401ba816: mov rax,[Water]; mov ecx,[rax+4]; cmp [rdi+0xc],ecx), and
// those bytes are checked once before any of it is trusted (WaterCheck). A stage without the Water object has no statics
// (null), one without water a huge level.

static void** g_waterStatics = nullptr;  // (Hook_RegisterObject: the "Water" object's statics)

namespace waterwalk {
constexpr int TOL_AIR = 4, TOL_GROUND = 16, HEAD = 24;
constexpr int ANI_BALANCE_1 = 25, ANI_BALANCE_2 = 26;  // (3K_Players/Sonic.bin: teetering on a ledge)
constexpr uintptr_t WATER_CMP = 0x1401ba816;

static bool Checked() {
    static int ok = -1;
    if (ok < 0) {
        static const uint8 CODE[] = {0x48, 0x8b, 0x05, 0x3b, 0xaa, 0xbf, 0x03, 0x8b, 0x48, 0x04, 0x39, 0x4f, 0x0c};
        bool code = Readable((void*)WATER_CMP, sizeof(CODE)) && memcmp((void*)WATER_CMP, CODE, sizeof(CODE)) == 0;
        void** statics = code ? (void**)(WATER_CMP + 7 + *(const int32*)(WATER_CMP + 3)) : nullptr;
        ok = code && g_waterStatics && statics == g_waterStatics;
        Log("water walk: the Water object's level %s (statics %p, registered %p)",
            ok ? "checks out (+4)" : "is DIFFERENT (another game build?): no water walk", (void*)statics,
            (void*)g_waterStatics);
    }
    return ok == 1;
}

static void Update(EntityPlayer* p) {
    if (!g_waterStatics || !Checked())
        return;
    uint8* water = (uint8*)*g_waterStatics;
    if (!water || !Readable(water, 8))
        return;
    int level = *(int32*)(water + 4);
    if (level <= 0 || level >= 0x7FFF0000)
        return;  // (no water in this stage)
    if (p->down || p->velocity.y < 0 || Hurt(p) || Held(p) || p->onGround)
        return;  // (diving, rising, hurt, held; or the game found a real floor)
    StateKind kind = KindOf((const void*)p->state.state);
    bool onWater = kind == STATE_GROUND;  // (she was on it last frame: the ground states)
    if (kind != STATE_GROUND && kind != STATE_AIR)
        return;
    if (anchor::g.state > anchor::LATCH && anchor::g.state < anchor::BACK)
        return;  // (reeled in by her anchor)
    Hitbox* box = RSDK->GetHitbox(&p->animator, 0);
    int bottom = box ? box->bottom : 20;
    int feet = p->position.y + (bottom << 16);
    if (onWater) {
        if (level - feet > (TOL_GROUND << 16) || feet - level > (TOL_GROUND << 16))
            return;
    } else {
        if (feet < level || feet - p->velocity.y > level + (TOL_AIR << 16))
            return;  // (still above it; or she was under it: coming up from below)
    }
    int head = ((level - feet) >> 16) - HEAD;
    constexpr uint8 CMODE_ROOF = 2;
    if (RSDK->ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, 0, head << 16, false))
        return;  // (no room: rising water doesn't push her into a ceiling; she's left to sink)
    p->position.y = level - (bottom << 16);
    p->velocity.y = 0;
    p->onGround = true;
    p->angle = 0;
    p->rotation = 0;
    p->collisionMode = 0;  // floor
    if (!onWater)
        p->groundVel = p->velocity.x;  // landing: her speed along kept
    int a = p->animator.animationID;
    if (a == ANI_BALANCE_1 || a == ANI_BALANCE_2)  // (no teetering: the whole surface is under her)
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}
}  // namespace waterwalk

static void WaterWalk(EntityPlayer* p) { waterwalk::Update(p); }
