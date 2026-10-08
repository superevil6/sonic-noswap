// Joe Musashi's Ninjutsu in S3&K (tools/ninjutsu.py: the same rules and numbers as Sonic 1/2 and CD; included by
// NoSwapS3K.cpp after TreasureSense.h). The user's design (2026-10-01):
// - An item monitor that breaks while he plays (Hook_ItemBoxCheck: whatever broke it, his body, a shuriken, a blast)
//   stores one magic if none is held: at random among his ninjaKinds (bit k: kind k). At most one, held until cast;
//   0 at each stage load (the Origins S1/S2/CD scripts start each stage afresh too), except a seamless act
//   transition's (Carry: held through it; a death still loses it).
// - The held one's icon at the top middle of the screen in the dark box (monitor_swap's look: shots::ICON_*), drawn in
//   the HUD pass (shots::HudPass): the game's own monitor art, 3K_Global/ItemBox.bin's
//   "Powerups" frame of the ItemBox type it stands for (4 the lightning shield, 3 the fire shield, 6 the sneakers, 10
//   Eggman).
// - Up + Y casts it (Press, before Abilities: the press is taken, g_ySuper, so no shuriken goes with it), from his own
//   free states (the air or ground states; not hurt, not held). Y that made him Super isn't a press (YPressed).
//   - Ikazuchi: the lightning shield as its monitor gives it: ItemBox_GivePowerup's type 4 case (0x1401d2c69, read
//     with objdump) sets the shield byte (+0xE8) to 4 and calls Player_ApplyShield (0x1401e3040: no shield entity while
//     Super or invincible, as for the monitor), then Global/LightningShield.wav. Off if its bytes differ.
//   - Kariu: Tails Doll's Screen Nuke (g_nuke: anything on screen is touched, the shots' hooks) with its flash
//     (NukeFlashStart, his ninjaKariuFlash in the nuke's place).
//   - Fushin: ninjaFushin frames of his jump strength x ninjaFushinJump / 1000 (NinjaJump, in ApplyPhysics: the game's
//     own value, water and Super included, scaled; back to it after).
//   - Mijin: Bomb's half-screen nuke (a box ninjaMijinX / Y px round him) at once, then, as his Mijin frames end, a
//     normal hit on him (ShotCost: the melee's cost, the exe's own Player_Hit).
// - The pose (Update, after Abilities): extra 1 (S1/S2's slot 42) for ninjaCast frames, ninjaCastTicks each; Mijin's
//   extra 6 (slot 48). Still on the ground, hanging still in the air (the melee's shotHang), nothing hurts him (the
//   blink at 3); a hit or an object taking him ends it (no cost).

namespace ninja {
constexpr int KIND_IKAZUCHI = 1, KIND_KARIU = 2, KIND_FUSHIN = 3, KIND_MIJIN = 4;
constexpr int ICON_FRAME[5] = {0, 4, 3, 6, 10};  // ItemBox.bin "Powerups": lightning, fire, sneakers, Eggman
constexpr int ITEMBOX_POWERUPS = 2;              // (3K_Global/ItemBox.bin: Normal, Broken, Powerups...)
constexpr uintptr_t APPLY_SHIELD = 0x1401e3040;  // Player_ApplyShield(player)
constexpr int SHIELD_BYTE = 0xE8, SHIELD_LIGHTNING_ = 4;

static int g_kind = 0;      // the magic held (0 none)
static int g_pose = 0;      // the cast pose's frames left
static int g_poseKind = 0;  // the magic being cast
static int g_fushin = 0;    // Fushin's frames left
static uint32 g_seed = 0x4E4A3D57;

static bool On() { return g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.ninjutsu; }

// Each stage load (shots::Hook_StageLoad): nothing held, nothing going on
static void Reset() {
    g_kind = g_pose = g_poseKind = g_fushin = 0;
}

// A seamless act transition's stage load (shots::Hook_StageLoad): the held magic kept, anything going on dropped
static void Carry() {
    g_pose = g_poseKind = g_fushin = 0;
}

static const char* Name(int k) {
    static const char* const names[] = {"none", "Ikazuchi", "Kariu", "Fushin", "Mijin"};
    return k >= 0 && k <= 4 ? names[k] : "?";
}

// A monitor broke (shots::Hook_ItemBoxCheck): a magic, at random, if none is held or being cast
static void MonitorBroke() {
    if (!On() || g_kind || g_pose)
        return;
    const ExtraAbilities& c = Extra(g_character).abilities;
    int kinds[4], n = 0;
    for (int k = KIND_IKAZUCHI; k <= KIND_MIJIN; k++)
        if (c.ninjaKinds >> k & 1)
            kinds[n++] = k;
    if (!n)
        return;
    g_seed ^= GetTickCount();  // (xorshift, stirred by the time)
    g_seed ^= g_seed << 13;
    g_seed ^= g_seed >> 17;
    g_seed ^= g_seed << 5;
    g_kind = kinds[g_seed % n];
    if (c.ninjaSound)
        PlaySound(c.ninjaSound);
    Log("ninjutsu: a monitor broke: %s stored", Name(g_kind));
}

// Fushin's higher jump: the jump multiplier ApplyPhysics uses (1000 = his own)
static int JumpScale(int m) {
    if (g_fushin <= 0 || !On())
        return m;
    return (int)((long long)m * Extra(g_character).abilities.ninjaFushinJump / 1000);
}

static void Ikazuchi(EntityPlayer* p) {
    static const uint8 PROLOGUE[] = {0x40, 0x57, 0x48, 0x83, 0xec, 0x50, 0x83, 0xb9, 0x0c, 0x02, 0x00, 0x00, 0x01,
                                     0x48, 0x8b, 0xf9};
    static int ok = -1;
    if (ok < 0) {
        ok = Readable((void*)APPLY_SHIELD, sizeof(PROLOGUE)) && !memcmp((void*)APPLY_SHIELD, PROLOGUE, sizeof(PROLOGUE));
        Log("ninjutsu: Player_ApplyShield at %p %s", (void*)APPLY_SHIELD, ok ? "checks out" : "is DIFFERENT: no shield");
    }
    if (!ok)
        return;
    *((uint8*)p + SHIELD_BYTE) = SHIELD_LIGHTNING_;
    ((void (*)(EntityPlayer*))APPLY_SHIELD)(p);
    PlaySound("Global/LightningShield.wav");
}

// Before Abilities: up + Y with a magic held casts it. True: the press was the cast's (no other Y move sees it)
static bool Press(EntityPlayer* p) {
    if (!On() || g_kind == 0 || g_pose > 0 || !p->up || !YPressed(p) || Hurt(p))
        return false;
    StateKind kind = KindOf((const void*)p->state.state);
    if (kind != STATE_AIR && kind != STATE_GROUND && kind != STATE_OPEN)
        return false;
    const ExtraAbilities& c = Extra(g_character).abilities;
    if (c.ninjaCastSound)
        PlaySound(c.ninjaCastSound);
    switch (g_kind) {
        case KIND_IKAZUCHI:
            Ikazuchi(p);
            break;
        case KIND_KARIU: {  // the Screen Nuke, the whole screen, with its flash
            g_nuke = c.ninjaKariuHit;
            g_nukeReachX = g_nukeReachY = 0;
            if (c.ninjaKariuFlashCount > 0) {
                static ExtraAbilities flash;  // (NukeFlashStart reads the nuke's flash: his Kariu's in its place)
                flash = c;
                flash.nukeFlashCount = c.ninjaKariuFlashCount;
                memcpy(flash.nukeFlash, c.ninjaKariuFlash, sizeof(flash.nukeFlash));
                NukeFlashStart(flash);
            }
            if (c.ninjaKariuSound)
                PlaySound(c.ninjaKariuSound);
            break;
        }
        case KIND_FUSHIN:
            g_fushin = c.ninjaFushin;
            break;
        case KIND_MIJIN:  // Bomb's half-screen nuke
            g_nuke = c.ninjaMijinHit;
            g_nukeReachX = c.ninjaMijinX;
            g_nukeReachY = c.ninjaMijinY;
            if (c.ninjaMijinSound)
                PlaySound(c.ninjaMijinSound);
            break;
    }
    Log("ninjutsu: %s cast", Name(g_kind));
    g_poseKind = g_kind;
    g_kind = 0;
    g_pose = std::max(g_poseKind == KIND_MIJIN ? c.ninjaMijin : c.ninjaCast, 1);
    return true;
}

// After Abilities: the pose (and Mijin's cost at its end), Fushin's count
static void Update(EntityPlayer* p) {
    if (!On())
        return;
    if (g_fushin > 0 && --g_fushin == 0)
        Log("ninjutsu: Fushin over");
    if (g_pose <= 0)
        return;
    if (Hurt(p) || Held(p)) {  // a hit, his death or an object: over (no cost)
        g_pose = 0;
        g_poseKind = 0;
        return;
    }
    const ExtraAbilities& c = Extra(g_character).abilities;
    bool mijin = g_poseKind == KIND_MIJIN;
    int total = std::max(mijin ? c.ninjaMijin : c.ninjaCast, 1), ticks = std::max(mijin ? c.ninjaMijinTicks : c.ninjaCastTicks, 1);
    int frames = std::max(total / ticks, 1), elapsed = total - g_pose;
    PlayExtraAnimation(p, mijin ? ANI_EXTRA_GLIDE_DOWN : ANI_EXTRA_HOVER, false, elapsed == 0);
    p->animator.frameID = std::min(elapsed / ticks, frames - 1);  // (the timer picks the frame)
    p->animator.timer = 0;
    if (g_blinkOffset >= 0) {  // nothing hurts him meanwhile (no flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    if (p->onGround) {
        p->groundVel = 0;
        p->velocity.x = 0;
    } else {  // hanging still (the melee's shotHang)
        p->velocity.x = 0;
        p->velocity.y = 0;
    }
    if (--g_pose == 0) {
        RSDK->SetSpriteAnimation(g_extraFrames, p->onGround ? ANI_IDLE : ANI_JUMP, &p->animator, true, 0);
        if (mijin)  // Mijin's cost: a normal hit (Bomb's Self-Destruct)
            ShotCost(p, p->direction & 1);
        g_poseKind = 0;
    }
}

// The icon wants the icon pass this frame (shots::QueueIcon): a magic held, not being cast
static bool Pass() { return On() && g_kind > 0 && g_pose == 0; }

static void Note(int why, const char* what) {  // (each reason the icon isn't drawn, logged once)
    static unsigned noted = 0;
    if (!(noted & (1u << why))) {
        noted |= 1u << why;
        Log("ninjutsu: icon not drawn: %s", what);
    }
}

// In the icon pass (shots::PlayerDraw): the held magic's monitor icon in the dark box at the top middle
static void Draw() {
    if (!Pass())
        return;
    if (shots::Showing("TitleCard") || shots::Showing("ActClear"))
        return Note(0, "title card / results up (normal)");
    int32 cx = 0;
    if (!shots::ScreenCentreX(&cx))
        return Note(1, "no screen info");
    uint16 frames = RSDK->LoadSpriteAnimation("3K_Global/ItemBox.bin", SCOPE_STAGE);
    if (frames == 0xFFFF)
        return Note(2, "3K_Global/ItemBox.bin not loaded");
    SpriteFrame* f = RSDK->GetFrame(frames, ITEMBOX_POWERUPS, ICON_FRAME[g_kind]);
    if (!f || !f->frame.width || !f->frame.height)
        return Note(3, "its frame has no size");
    Entity* self = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (!self || !Readable(self, sizeof(Entity)))
        return;
    static bool first = true;
    if (first) {
        first = false;
        Log("ninjutsu: drawing the icon at x %d (%dx%d)", cx, (int)f->frame.width, (int)f->frame.height);
    }
    int bw = f->frame.width + 2 * shots::ICON_PAD_X, bh = f->frame.height + 2 * shots::ICON_PAD_Y;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;  // (DrawSprite draws with the entity's own)
    self->drawFX = 0;
    self->inkEffect = 0;
    self->direction = 0;
    RSDK->DrawRect(cx - bw / 2, shots::ICON_TOP, bw, bh, 0x000000, shots::ICON_ALPHA, shots::ICON_INK_ALPHA, true);
    Animator icon{};
    RSDK->SetSpriteAnimation(frames, ITEMBOX_POWERUPS, &icon, true, (uint8)ICON_FRAME[g_kind]);
    Vector2 pos = {cx << 16, (shots::ICON_TOP + bh / 2) << 16};
    RSDK->DrawSprite(&icon, &pos, true);
    self->drawFX = fx;
    self->inkEffect = ink;
    self->direction = dir;
}
}  // namespace ninja

static int NinjaJump(int m) { return ninja::JumpScale(m); }
