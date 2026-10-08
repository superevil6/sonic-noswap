"""Joe Musashi's Ninjutsu (abilities.py "ninjutsu"), in all four Origins games and Mania: the Sonic 1/2 code (Retro
Engine v4 player script; abilities.py and its shot update call in here), Sonic CD's (build_soniccd.py calls cd_patch /
cd_update_dispatch), the numbers the S3&K DLL and the Mania mod read (s3k_fields: native/src/Ninjutsu.h,
native/mania/src/ManiaNinjutsu.h).

The user's design (2026-10-01, "the user's twist"):
- A charge is stored ONLY by breaking an item monitor (by anything: his body, a shuriken, a blast), and only while none
  is held: at most one, held until used (or until the stage restarts: a death or the next act, as every NoSwap move's
  state). Which magic it is, is RANDOM per monitor, among the "ninjutsu" list (Ikazuchi, Kariu, Fushin, Mijin).
- The held one shows at the top middle of the screen in a dark box, John Morris' sub-weapon icon's place and look
  (tools/monitor_swap.py ICON_*: the same pass, v4_hud_listing's / the DLL's icon pass / Mania's ONDRAW). The icon is
  the GAME's own monitor art for it (no art drawn; his sheet has no Ninjutsu effect art): Ikazuchi the lightning shield
  monitor, Kariu the fire shield's, Fushin the power sneakers', Mijin Eggman's (it hurts you). Sonic CD has none of the
  elemental ones: there Ikazuchi is the blue shield's, Kariu the invincibility stars', Fushin the sneakers', Mijin the
  broken monitor (S1/S2/CD Global/Items.gif, S3&K 3K_Global/ItemBox.bin, Mania Global/ItemBox.bin "Powerups").
- Up + Y casts it (Y alone stays the shuriken; up + Y with nothing held throws a shuriken too), on the ground or in the
  air, from his own free states (not hurt, not held by an object; in mid-air Y transforms first when Super is
  possible: projectile-system.md's Y/Super rule). The press is the cast's: no shuriken with it.
  - Ikazuchi: a lightning shield, the game's own (S1/S2 player.shield SHIELD_LIGHTNING + Player_ApplyShield, as the
    lightning monitor; S3&K the exe's Player_ApplyShield; Mania Player_ApplyShield). Sonic CD has only the blue shield:
    that one, as its monitor gives it.
  - Kariu: a screen-wide fire hit: Tails Doll's Screen Nuke mechanics (abilities.py melee_nuke), from its own object
    (S1/S2 the Tails Object in the shots' group, CD a shot slot with Value7 1, S3&K the DLL's g_nuke, Mania the stand-in),
    with its black flash ("ninja_kariu": hit, reach_x / reach_y, reach_cd, flash, sounds; S3&K and Mania: the screen).
  - Fushin: a higher jump for ninja_fushin frames (his jump strength x ninja_fushin_jump, the game's own physics value
    rescaled each frame, water and Super included; back to it after).
  - Mijin: self-destruct: Bomb's half-screen nuke ("ninja_mijin_blast", no flash) at once, his Mijin frames (his own
    sheet's: he darkens and bursts into fragments), nothing hurts him meanwhile, then the COST: a normal hit through the
    game's own hurt (abilities.py melee_cost: rings scattered, a shield lost instead, at 0 rings he dies).
- The cast pose: ability slot 42 (CD 47, S3&K / Mania extra 1) for ninja_cast frames, ninja_cast_ticks each; Mijin's
  in slot 48 (CD 49, S3&K / Mania extra 6) for ninja_mijin frames. He stands still on the ground and hangs still in the
  air, and nothing hurts him meanwhile (melee_safe's rule); a hit, a death or an object taking him ends it.

Shared design note (the "monitor-charged meter", for Gilius' magic later): the charge is a counter that monitor breaks
add to (here capped at 1, holding a kind), read and spent by a cast. A Golden Axe meter would be the same detection and
icon pass with a cap above 1 and the icon drawn N times; nothing of it is built until he is.

State, per engine (the same numbers everywhere):
  kind     0 none, 1-4 held (KINDS), 9-12 being cast (8 + kind)
  pose     the cast pose's frames left
  fushin   Fushin's frames left
  Sonic 1/2  NoSwap_ninja (packed: noswap_common.PACKED_VALUES): kind in its low 4 bits, the HUD listing above (as
             monitor_swap's ICON_VALUE: 2 / 1 listed this frame, 3 ours next); NoSwap_ninjaTime: pose in its low 6 bits,
             fushin above. A monitor counted: its Broken Monitor's value30 (monitor_swap.MARK; no extra has both moves).
  Sonic CD   Object[CD_SLOT] (docs/soniccd_map.md section 4: never touched): Value0 kind, Value1 pose, Value2 fushin,
             Value3 the HUD listing, Value4 the monitor breaks seen (Global/Monitor.txt counts them in
             Object[monitor_swap.CD_SLOT].Value0 in every build), Value5 / Value6 the jump strength written / its base.
  S3&K, Mania  the DLL's ninja::g_*, the Mania mod's g_nj* (0 at each stage load).
"""
import sys

KINDS = {"ikazuchi": 1, "kariu": 2, "fushin": 3, "mijin": 4}
CASTING = 8  # kind + CASTING: that one being cast
VALUE, TIME = "NoSwap_ninja", "NoSwap_ninjaTime"  # Sonic 1/2 (packed: noswap_common.PACKED_VALUES)
POSE_BITS = 6  # NoSwap_ninjaTime: the pose's frames in its low 6 bits (so a pose lasts at most 63 frames)
LISTING_SHIFT = 4  # NoSwap_ninja: the HUD listing above the kind's 4 bits
CD_SLOT = 14  # Sonic CD: Object[14] (reserved, never touched)
MARK = 0x4E4A  # S1/S2: the Tails Object's value33 (no shot sets it): MARK + 1 a Kariu blast, MARK + 2 a Mijin blast
# The icons: the game's own monitor art for each kind (S1/S2/CD Global/Items.gif: BrokenMonitor.txt's frames; the S3&K
# and Mania ItemBox.bin "Powerups" frame numbers are in the DLL / mod: ItemBox types 4 lightning, 3 fire, 6 sneakers,
# 10 Eggman)
ICONS = {"Sonic1u": {1: (51, 76), 2: (68, 76), 3: (68, 31), 4: (68, 91)},
         "Sonic2u": {1: (18, 126), 2: (35, 126), 3: (35, 81), 4: (35, 141)}}
ICON_W, ICON_H = 16, 14
CD_ICONS = {1: (-8, -8, 16, 16, 26, 40), 2: (-8, -8, 16, 16, 26, 73), 3: (-8, -8, 16, 16, 26, 106),
            4: (-16, -8, 32, 16, 51, 166)}  # (CD: blue shield, invincibility, sneakers, the broken monitor)
ANI_CAST, ANI_MIJIN = "ANI_NOSWAP_HOVER", "ANI_NOSWAP_GLIDE_DOWN"  # slots 42 / 48 (CD 47 / 49)
NUKE_KEYS = ("hit", "reach_x", "reach_y", "reach_cd")
FLASH_MAX = 32  # (gen_s3k_header.FLASH_MAX)


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("ninjutsu")


def check(i):
    """The extra's ninjutsu numbers, checked (the build stops on a mistake)."""
    c = ab().ABILITIES[i]
    kinds = c.get("ninjutsu")
    if not isinstance(kinds, list) or not kinds or len(set(kinds)) != len(kinds) or any(k not in KINDS for k in kinds):
        sys.exit(f"ninjutsu: extra {i}: \"ninjutsu\" is a list of different magics among {', '.join(KINDS)}")
    for k in ("ninja_cast", "ninja_cast_ticks", "ninja_mijin", "ninja_mijin_ticks", "ninja_fushin", "ninja_fushin_jump",
              "ninja_kariu", "ninja_mijin_blast", "ninja_sfx", "ninja_sfx_cd", "ninja_cast_sfx", "ninja_cast_sfx_cd"):
        if k not in c:
            sys.exit(f"ninjutsu: extra {i} needs \"{k}\"")
    for k in ("ninja_cast", "ninja_mijin"):
        if not 0 < c[k] < (1 << POSE_BITS):
            sys.exit(f"ninjutsu: extra {i}: \"{k}\" is 1 to {(1 << POSE_BITS) - 1} frames")
    for k in ("ninja_cast_ticks", "ninja_mijin_ticks"):
        if c[k] < 1:
            sys.exit(f"ninjutsu: extra {i}: \"{k}\" is at least 1")
    if c["ninja_fushin"] < 1 or not 1.0 <= c["ninja_fushin_jump"] <= 3.0:
        sys.exit(f"ninjutsu: extra {i}: \"ninja_fushin\" is at least 1 frame, \"ninja_fushin_jump\" 1.0 to 3.0")
    for k in ("ninja_kariu", "ninja_mijin_blast"):
        n = c[k]
        if not isinstance(n, dict) or any(not isinstance(n.get(x), int) or n[x] < 1 for x in NUKE_KEYS):
            sys.exit(f"ninjutsu: extra {i}: \"{k}\" needs {', '.join(NUKE_KEYS)} (whole numbers, at least 1)")
        flash = n.get("flash", [])
        if len(flash) > FLASH_MAX or any(not 0 <= a <= 255 for a in flash) or (flash and n["hit"] > len(flash)):
            sys.exit(f"ninjutsu: extra {i}: \"{k}\" flash: at most {FLASH_MAX} darkness values 0-255, as long as its "
                     "hit at least")
    if c["ninja_mijin_blast"].get("flash"):
        sys.exit(f"ninjutsu: extra {i}: Mijin's blast has no flash (Bomb's)")
    if "monitor_swap" in c.get("abilities", []):
        sys.exit(f"ninjutsu: extra {i}: not with monitor_swap (both count monitors with the same mark)")
    if not ab().has(i, "melee"):
        sys.exit(f"ninjutsu: extra {i}: needs the melee (Y alone; up + Y is the cast)")
    return c


def kinds(i):
    return [KINDS[k] for k in check(i)["ninjutsu"]]


def jump_q8(i):
    return round(256 * check(i)["ninja_fushin_jump"])


def tab(text, n):
    return "".join("\t" * n + l + "\n" if l.strip() else "\n" for l in text.rstrip("\n").split("\n"))


# ---------------------------------------------------------------- Sonic 1/2
V4_VALUES = f"""public value {VALUE} = 0 // ninjutsu: the magic held / being cast, and the icon's HUD listing (tools/ninjutsu.py)
public value {TIME} = 0 // ninjutsu: the cast pose's frames left, and Fushin's (tools/ninjutsu.py)
"""

FREE_V4 = """temp0 = false // his own free states (the melee's): not hurt, not held by an object
CheckEqual(player.state, Player_State_Ground)
temp0 |= checkResult
CheckEqual(player.state, Player_State_Air)
temp0 |= checkResult
CheckEqual(player.state, Player_State_Air_NoDropDash)
temp0 |= checkResult
CheckEqual(player.state, Player_State_RollJump)
temp0 |= checkResult
if player.animation == ANI_HURT
	temp0 = false
end if
"""

# melee_cost (abilities.MELEE_COST): a normal hit through the game's own hurt, in his free states, not through an
# invincibility star
COST_V4 = """temp1 = false // Mijin's cost (abilities.py melee_cost: Bomb's Self-Destruct): a normal hit, the game's own hurt
CheckEqual(player.state, Player_State_Ground)
temp1 |= checkResult
CheckEqual(player.state, Player_State_Air)
temp1 |= checkResult
CheckEqual(player.state, Player_State_Air_NoDropDash)
temp1 |= checkResult
CheckEqual(player.state, Player_State_RollJump)
temp1 |= checkResult
CheckEqual(player.state, Player_State_Roll)
temp1 |= checkResult
CheckEqual(player.state, Player_State_LookUp)
temp1 |= checkResult
CheckEqual(player.state, Player_State_Crouch)
temp1 |= checkResult
if player.invincibleTimer != 0 // (an invincibility star: no hit, as Player_Hit)
	temp1 = false
end if
if temp1 == true
	player.blinkTimer = 0 // (the pose's guard isn't one against it)
	player.state = Player_State_GotHit // rings, a shield, or at 0 rings his death
	if player.direction == FACING_RIGHT // knocked back
		player.speed = -0x20000
	else
		player.speed = 0x20000
	end if
end if
"""


def v4_spawn(i, which):
    """A blast's object (melee_nuke's: abilities.nuke_spawn), marked in value33 (MARK + 1 Kariu, MARK + 2 Mijin)."""
    import shots_v4
    n = check(i)["ninja_kariu" if which == 1 else "ninja_mijin_blast"]
    return f"""CreateTempObject(TypeName[Tails Object], 0, player.xpos, player.ypos) // its blast (abilities.py melee_nuke's object)
arrayPos0 = object[tempObjectPos].entityPos
if object[arrayPos0].type == TypeName[Tails Object] // (made)
	object[arrayPos0].state = {shots_v4.LIVE}
	object[arrayPos0].priority = PRIORITY_ACTIVE
	object[arrayPos0].interaction = true
	object[arrayPos0].drawOrder = 6 // (the top layer: the flash goes over everything)
	object[arrayPos0].value0 = 0
	object[arrayPos0].value36 = -1 // (nothing drawn until its update gives the flash)
	object[arrayPos0].value33 = {MARK + which} // ({'Kariu' if which == 1 else 'Mijin'}: tools/ninjutsu.py v4_update_dispatch)
end if
""" + (f"PlaySfx(SfxName[{n['sfx']}], false)\n" if n.get("sfx") else "")


def v4_after(i):
    """In the extra's NoSwap_AfterUpdate, first (before the shuriken reads Y): monitors charge it, up + Y casts it (the
    pose, Fushin's jump and the icon: v4_after_pose, last)."""
    c = check(i)
    ks = kinds(i)
    cast, mijin = c["ninja_cast"], c["ninja_mijin"]
    ikazuchi = f"""PlaySfx(SfxName[Lightning Shield], false) // Ikazuchi: the lightning shield, as its monitor gives it
player.shield = SHIELD_LIGHTNING
currentPlayer = player.entityPos
arrayPos0 = player.entityPos
arrayPos0 += playerCount
if Player_superState != SUPERSTATE_SUPER
	if object[arrayPos0].type != invincibilityType
		CallFunction(Player_ApplyShield)
	end if
end if
"""
    fushin = f"""temp0 = {TIME} // Fushin: the high jump, for {c['ninja_fushin']} frames
temp0 &= {(1 << POSE_BITS) - 1}
temp0 += {c['ninja_fushin'] << POSE_BITS}
{TIME} = temp0
"""
    casts = {1: ikazuchi, 2: v4_spawn(i, 1), 3: fushin, 4: v4_spawn(i, 2)}
    names = {1: "Ikazuchi", 2: "Kariu", 3: "Fushin", 4: "Mijin"}
    cast_lines = "".join(f"if {VALUE} == {k} // {names[k]}\n" + tab(casts[k], 1) + "end if\n" for k in ks)
    block_shot = (f"\t\t\t\t\t\t{ab().shot_cooldown_name(i)} = 2 // (and its cooldown: no shuriken this frame, whatever the "
                  "engine does with the press above)\n" if ab().shot(i, "v4") else "")
    return f"""// [NoSwap] Ninjutsu (tools/ninjutsu.py): a broken monitor stores one magic, up + Y casts it
{VALUE} &= 15 // (the kind; the icon's HUD listing above it is made afresh below)
foreach (TypeName[Broken Monitor], arrayPos0, ACTIVE_ENTITIES) // each monitor broken (by anything): a charge, if none
	if object[arrayPos0].value30 == 0 // (counted once: tools/monitor_swap.py MARK)
		object[arrayPos0].value30 = 1
		if {VALUE} == 0
			Rand(temp0, {len(ks)})
			GetTableValue({VALUE}, temp0, NoSwap_NinjaKinds{i}) // one at random
			PlaySfx(SfxName[{c['ninja_sfx']}], false)
		end if
	end if
next
temp6 = {TIME}
temp6 &= {(1 << POSE_BITS) - 1}
if temp6 == 0
	if {VALUE} > 0
		if {VALUE} < {CASTING} // a magic held
			if keyPress[1].buttonY != false
				if keyDown[1].up != false // up + Y: cast it
{tab(FREE_V4, 5)}					if temp0 == true
						keyPress[1].buttonY = false // (the cast's press: no shuriken with it)
{block_shot}						PlaySfx(SfxName[{c['ninja_cast_sfx']}], false)
{tab(cast_lines, 6)}						temp6 = {cast} // the pose
						if {VALUE} == {KINDS['mijin']}
							temp6 = {mijin}
						end if
						temp0 = {TIME}
						temp0 >>= {POSE_BITS}
						temp0 <<= {POSE_BITS}
						temp0 += temp6
						{TIME} = temp0
						{VALUE} += {CASTING} // being cast
					end if
				end if
			end if
		end if
	end if
end if
"""


def v4_after_pose(i):
    """In the extra's NoSwap_AfterUpdate, last (after his moves, so the pose is what shows): the pose (a throw pose the
    cast's press started is cut), Mijin's cost, Fushin's jump, and the icon's HUD-layer listing."""
    import monitor_swap
    c = check(i)
    q = jump_q8(i)
    cast, cticks, mijin, mticks = c["ninja_cast"], c["ninja_cast_ticks"], c["ninja_mijin"], c["ninja_mijin_ticks"]
    listing = monitor_swap.v4_hud_listing("temp0", "").split("\n", 1)[1]  # (its first line set the value to 0)
    listing = listing.replace("temp0 = 1", "temp0 = 1 // (ours only: he's hidden)").replace("temp0 = 2", "temp0 = 2 "
                                                                                           "// (StageSetup's too, first)")
    return f"""// [NoSwap] Ninjutsu (tools/ninjutsu.py): the cast pose, Fushin, the held magic's icon
temp6 = {TIME}
temp6 &= {(1 << POSE_BITS) - 1}
if temp6 > 0 // the pose
	if NoSwap_melee > 0 // (a throw pose the cast's press started, if the engine kept the press: cut, the cast's shows)
		NoSwap_melee = 0
	end if
	temp0 = false
	CheckEqual(player.animation, ANI_HURT)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_DYING)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_DROWNING)
	temp0 |= checkResult
	CheckEqual(player.controlMode, CONTROLMODE_NONE)
	temp0 |= checkResult
	if temp0 == true // a hit, his death or an object: over (no cost)
		{TIME} -= temp6
		{VALUE} = 0
	else
		{TIME}--
		temp6--
		if player.blinkTimer < 3 // nothing hurts him meanwhile (melee_safe's rule; under 4: no flicker)
			player.blinkTimer = 3
		end if
		if player.gravity == GRAVITY_GROUND
			player.speed = 0
			player.xvel = 0
		else
			player.xvel = 0 // hanging still in the air (melee_hang's; the state's gravity next frame cancelled)
			player.yvel = player.gravityStrength
			FlipSign(player.yvel)
		end if
		if {VALUE} == {CASTING + KINDS['mijin']} // Mijin's frames (slot 48)
			player.animation = {ANI_MIJIN}
			temp0 = {mijin}
			temp0 -= temp6
			temp0 /= {mticks}
			if temp0 >= {mijin // mticks}
				temp0 = {mijin // mticks - 1}
			end if
		else
			player.animation = {ANI_CAST} // the cast pose (slot 42)
			temp0 = {cast}
			temp0 -= temp6
			temp0 /= {cticks}
			if temp0 >= {cast // cticks}
				temp0 = {cast // cticks - 1}
			end if
		end if
		player.prevAnimation = player.animation // (the timer picks the frame)
		player.frame = temp0
		player.animationTimer = 0
		if temp6 == 0 // its end
			if player.gravity == GRAVITY_GROUND
				player.animation = ANI_STOPPED
			else
				player.animation = ANI_JUMPING
			end if
			if {VALUE} == {CASTING + KINDS['mijin']}
{tab(COST_V4, 4)}			end if
			{VALUE} = 0
		end if
	end if
end if
temp1 = {TIME}
temp1 >>= {POSE_BITS}
if temp1 > 0 // Fushin: the game's own jump strength (water, Super, shoes: its physics table), {c['ninja_fushin_jump']}x
	{TIME} -= {1 << POSE_BITS}
	currentPlayer = player.entityPos
	CallFunction(Player_UpdatePhysicsState) // (on the last frame: back to his own)
	temp1 = {TIME}
	temp1 >>= {POSE_BITS}
	if temp1 > 0
		player.jumpStrength *= {q}
		player.jumpStrength >>= 8
	end if
end if
temp0 = 0 // the held magic's icon: the HUD-layer pass (tools/monitor_swap.py v4_hud_listing)
if {VALUE} > 0
	if {VALUE} < {CASTING}
{tab(listing, 2)}	end if
end if
temp0 <<= {LISTING_SHIFT}
{VALUE} += temp0
"""


def v4_tables(i):
    c = check(i)
    flash = c["ninja_kariu"].get("flash", [])
    return (f"// [NoSwap] Ninjutsu (tools/ninjutsu.py): the magics a monitor can store (1 Ikazuchi, 2 Kariu, 3 Fushin, 4 "
            f"Mijin)\nprivate table NoSwap_NinjaKinds{i}\n\t" + ", ".join(str(k) for k in kinds(i)) + "\nend table\n\n"
            + (f"// [NoSwap] Ninjutsu: Kariu's flash, its darkness per frame (0-255, SetScreenFade's alpha)\n"
               f"private table NoSwap_NinjaFlash{i}\n\t" + ", ".join(str(a) for a in flash) + "\nend table\n\n"
               if flash else ""))


def v4_blast_body(i, which):
    """A blast's own update (object: it; abilities.nuke_update_body's, with its looks: abilities.nuke_looks): on player
    1 all its life, the flash's darkness per frame in value36 (TailsObject.txt draws it; -1 nothing), and for its first
    `hit` frames in the shots' group, a jumping player to the enemies' shot loops with a box reach_x x reach_y round him."""
    import shots_v4
    n = check(i)["ninja_kariu" if which == 1 else "ninja_mijin_blast"]
    flash = n.get("flash", [])
    life = max(len(flash), n["hit"])
    flash_lines = f"""	temp0 = object.value0
	temp0--
	GetTableValue(object.value36, temp0, NoSwap_NinjaFlash{i})
	if object.value36 == 0
		object.value36 = -1 // (nothing to draw)
	end if
""" if flash else ""
    return f"""object.value0++ // its age ({'Kariu' if which == 1 else 'Mijin'}: tools/ninjutsu.py v4_blast_body)
object.xpos = object[0].xpos
object.ypos = object[0].ypos
if object.value0 > {life}
	object.type = TypeName[Blank Object]
else
{flash_lines}	if object.value0 <= {n['hit']}
		object.groupID = {shots_v4.GROUP} // the shots' group: the enemies' shot loops
		object.state = {shots_v4.LIVE}
		object.animation = ANI_JUMPING // (its looks: a jumping player 1, its box round him)
		object.gravity = GRAVITY_GROUND
		object.value16 = false // isSidekick
		object.value19 = object[0].value19 // badnikBonus
		object.value38 = -{n['reach_y']} // hitbox top, bottom, left, right
		object.value39 = {n['reach_y']}
		object.value40 = -{n['reach_x']}
		object.value41 = {n['reach_x']}
	else
		object.groupID = TypeName[Tails Object] // (out of it: its hit is over)
	end if
end if
"""


def v4_update_dispatch(i, body):
    """NoSwap_ShotUpdate's body for a ninjutsu extra (abilities.shot_update_function): his blasts' own update, else his
    shot's (`body`)."""
    if i not in ids():
        return body
    return (f"if object.value33 == {MARK + 1} // [NoSwap] Kariu's blast (tools/ninjutsu.py)\n" + tab(v4_blast_body(i, 1), 1)
            + "else\n" + f"\tif object.value33 == {MARK + 2} // Mijin's\n" + tab(v4_blast_body(i, 2), 2) + "\telse\n"
            + tab(body, 2) + "\tend if\nend if\n")


def v4_patch(t, game):
    """The S1/S2 player script (after every other module's patches): for each ninjutsu extra its values and tables, the
    icons' frames (ObjectStartup: Global/Items.gif, the game's own monitor art) and the HUD-layer pass (ObjectDraw)."""
    import monitor_swap
    if not ids():
        return t
    anchor = "public value Player_superState"
    if t.count(anchor) != 1:
        sys.exit("ninjutsu: Player_superState isn't there once")
    t = t.replace(anchor, V4_VALUES + "\n" + anchor)
    anchor = "// [NoSwap] Ability modules for extra characters (generated by tools/abilities.py)\n"
    if t.count(anchor) != 1:
        sys.exit("ninjutsu: the ability modules' first line isn't there once")
    t = t.replace(anchor, anchor + "".join(v4_tables(i) for i in ids()))
    if t.count("event ObjectStartup\n") != 1 or t.count("event ObjectDraw\n") != 1:
        sys.exit("ninjutsu: expected one ObjectStartup and one ObjectDraw")
    for i in ids():
        a = ab().ALIAS_OF[i]
        frames = "".join(f"\t\tSpriteFrame({-ICON_W // 2}, {-ICON_H // 2}, {ICON_W}, {ICON_H}, {x}, {y}) // {k - 1}: "
                         f"{next(n for n, v in KINDS.items() if v == k)}'s icon\n"
                         for k, (x, y) in sorted(ICONS[game].items()))
        t = t.replace("event ObjectStartup\n", "event ObjectStartup\n"
                      f"\tif stage.playerListPos == {a} // [NoSwap] ninjutsu (tools/ninjutsu.py): the held magic's icon, the "
                      "game's own monitor art\n" '\t\tLoadSpriteSheet("Global/Items.gif")\n' + frames + "\tend if\n", 1)
        bw, bh = ICON_W + 2 * monitor_swap.ICON_PAD_X, ICON_H + 2 * monitor_swap.ICON_PAD_Y
        cy = monitor_swap.ICON_TOP + bh // 2
        draw = f"""temp0 = screen.xcenter // the held magic's icon (John Morris' sub-weapon box: tools/monitor_swap.py)
temp0 -= {bw // 2}
DrawRect(temp0, {monitor_swap.ICON_TOP}, {bw}, {bh}, 0, 0, 0, {monitor_swap.ICON_ALPHA})
temp0 = {VALUE}
temp0--
DrawSpriteScreenXY(temp0, screen.xcenter, {cy})"""
        t = v4_hud_pass(t, a, draw)
    return t


def v4_hud_pass(t, alias, draw):
    """monitor_swap.v4_hud_pass with the listing in NoSwap_ninja's bits above the kind (LISTING_SHIFT)."""
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    body = t[start + len("event ObjectDraw\n"):end]
    s = 1 << LISTING_SHIFT
    head = f"""	temp7 = false // [NoSwap] ninjutsu (tools/ninjutsu.py): his HUD-layer listing draws the held magic's icon, not him
	if stage.playerListPos == {alias}
		temp6 = {VALUE}
		temp6 >>= {LISTING_SHIFT}
		if temp6 == 2 // StageSetup's listing (first): him; ours (the HUD's layer) next
			{VALUE} += {s}
		else
			if temp6 > 0 // ours (3), or ours only (1: he's hidden)
				{VALUE} &= {s - 1}
				temp7 = true
""" + tab(draw, 4) + """			end if
		end if
	end if
	if temp7 == false
"""
    body = "".join("\t" + l if l.strip() else l for l in body.splitlines(True))
    return t[:start] + "event ObjectDraw\n" + head + body + "\tend if\n" + t[end:]


# ---------------------------------------------------------------- Sonic CD
def cd_v(k):
    return f"Object[{CD_SLOT}].Value{k}"


def cd_spawn(i, which):
    """A blast in the first shot slot (build_soniccd.nuke_spawn_cd's: a Tails Object, Value7 1 a nuke: NoSwap_ShotTouch
    leaves it, TailsObject.txt draws its fade), Value5 which (1 Kariu, 2 Mijin: cd_update_dispatch)."""
    import shots_v3
    n = check(i)["ninja_kariu" if which == 1 else "ninja_mijin_blast"]
    slot = shots_v3.SLOTS[0]
    return [f"ResetObjectEntity({slot}, TypeName[Tails Object], 0, Player.XPos, Player.YPos) // its blast (melee_nuke's object)",
            f"Object[{slot}].State = {shots_v3.LIVE}", f"Object[{slot}].Priority = PRIORITY_ACTIVE",
            f"Object[{slot}].DrawOrder = 6 // (the top layer: the fade goes over everything)", f"Object[{slot}].Value2 = 0",
            f"Object[{slot}].Value3 = {n['reach_cd'] << 16:#x}", f"Object[{slot}].Value4 = Player.CollisionPlane",
            f"Object[{slot}].Value5 = {which} // ({'Kariu' if which == 1 else 'Mijin'}: tools/ninjutsu.py cd_update_dispatch)",
            f"Object[{slot}].Value6 = -1 // (nothing drawn until its update gives the fade)",
            f"Object[{slot}].Value7 = 1 // a nuke: NoSwap_ShotTouch leaves it"] \
        + ([f"PlaySfx({n['sfx_cd']}, false)"] if n.get("sfx_cd") else [])


def cd_blast_body(i, which):
    """build_soniccd.nuke_update_cd's, with its numbers."""
    import shots_v3
    n = check(i)["ninja_kariu" if which == 1 else "ninja_mijin_blast"]
    flash = n.get("flash", [])
    cases = [f"\tcase {k + 1}\n\t\tObject.Value6 = {a if a else -1}\n\t\tbreak" for k, a in enumerate(flash)]
    return (["Object.Value2++ // its age (tools/ninjutsu.py cd_blast_body)", "Object.XPos = Player.XPos",
             "Object.YPos = Player.YPos", f"if Object.Value2 > {max(len(flash), n['hit'])}",
             "\tObject.Type = TypeName[Blank Object]", "else"]
            + (["\tswitch Object.Value2 // the flash's darkness"] + "\n".join(cases).split("\n") + ["\tend switch"]
               if flash else [])
            + [f"\tif Object.Value2 <= {n['hit']}", f"\t\tObject.State = {shots_v3.LIVE} // its hit", "\telse",
               "\t\tObject.State = 0 // (over: the targets' tests pass it by)", "\tend if", "end if"])


def cd_update_dispatch(i, lines):
    """NoSwap_ShotUpdate's lines for a ninjutsu extra (build_soniccd): his blasts' update (a nuke, Value7 1), else his
    shot's."""
    if i not in ids():
        return lines
    t = lambda ls, n: ["\t" * n + l for l in ls]
    return (["if Object.Value7 == 1 // [NoSwap] a Ninjutsu blast (tools/ninjutsu.py)", "\tif Object.Value5 == 1 // Kariu's"]
            + t(cd_blast_body(i, 1), 2) + ["\telse // Mijin's"] + t(cd_blast_body(i, 2), 2) + ["\tend if", "else"]
            + t(lines, 1) + ["end if"])


def cd_after(i):
    """The CD NoSwap_AfterUpdate block (v4_after's), first: Y from the DLL (game.callbackParam3 1), up held."""
    import monitor_swap
    c = check(i)
    ks = kinds(i)
    v = cd_v
    cast, cticks, mijin, mticks = c["ninja_cast"], c["ninja_cast_ticks"], c["ninja_mijin"], c["ninja_mijin_ticks"]
    pick = "\n".join(f"if TempValue0 == {n}\n\t{v(0)} = {k}\nend if" for n, k in enumerate(ks))
    ikazuchi = """PlaySfx(SFX_G_SHIELD, false) // Ikazuchi: CD's only shield, the blue one, as its monitor gives it
Object[2].PropertyValue = 1 // (ACTIVE_SHIELD)
if Object[2].Type != TypeName[Invincibility]
	Object[2].Type = TypeName[Blue Shield]
	Object[2].Priority = PRIORITY_ACTIVE
	Object[2].DrawOrder = 4
	Object[2].InkEffect = INK_ALPHA
	Object[2].Alpha = 160
	Object[2].XPos = Player.XPos
	Object[2].YPos = Player.YPos
end if"""
    fushin = (f"if {v(2)} == 0 // Fushin: the high jump (a second one goes on from the first's base)\n"
              f"\t{v(5)} = 0 // (its base next frame)\nend if\n{v(2)} = {c['ninja_fushin']}")
    casts = {1: ikazuchi, 2: "\n".join(cd_spawn(i, 1)), 3: fushin, 4: "\n".join(cd_spawn(i, 2))}
    names = {1: "Ikazuchi", 2: "Kariu", 3: "Fushin", 4: "Mijin"}
    cast_lines = "".join(f"if {v(0)} == {k} // {names[k]}\n" + tab(casts[k], 1) + "end if\n" for k in ks)
    listing = "\n".join(monitor_swap.cd_hud_listing(v(3), "ninjutsu (tools/ninjutsu.py): the held magic's icon, drawn "
                                                          "in the HUD's layer (ObjectDraw)"))
    states = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
              "Player_State_Roll", "Player_State_LookUp", "Player_State_Crouch"]
    cost = ("TempValue0 = false // Mijin's cost (build_soniccd.melee_cost_cd: Bomb's): a normal hit, the game's own hurt\n"
            + "".join(f"CheckEqual(Player.State, {s})\nTempValue0 |= CheckResult\n" for s in states)
            + """ArrayPos0 = Player.EntityNo
ArrayPos0 += 2
if Object[ArrayPos0].Type == TypeName[Invincibility] // (a star: no hit, as Player_Hit)
	TempValue0 = false
end if
if TempValue0 == true
	Player.InvincibleTimer = 0 // (the pose's guard isn't one against it)
	Player.State = Player_State_GotHit // rings, the shield, or his death
	if Player.Direction == FACING_RIGHT // knocked back
		Player.Speed = -0x20000
	else
		Player.Speed = 0x20000
	end if
end if
""")
    q = jump_q8(i)
    return f"""// Ninjutsu (tools/ninjutsu.py): a broken monitor stores one magic, up + Y casts it
if Object[12].Value0 != {v(4)} // a monitor broke (Global/Monitor.txt counts them: tools/monitor_swap.py cd_monitor)
	{v(4)} = Object[12].Value0
	if {v(0)} == 0 // none held: one at random
		Rand(TempValue0, {len(ks)})
{tab(pick, 2)}		PlaySfx({c['ninja_sfx_cd']}, false)
	end if
end if
if {v(1)} == 0
	if {v(0)} > 0
		if {v(0)} < {CASTING} // a magic held
			if game.callbackParam3 == 1 // Y, from the DLL
				if Player.Up == true // up + Y: cast it
					TempValue0 = false // his own free states: not hurt, not held
					CheckEqual(Player.State, Player_State_Ground)
					TempValue0 |= CheckResult
					CheckEqual(Player.State, Player_State_Air)
					TempValue0 |= CheckResult
					CheckEqual(Player.State, Player_State_Air_NoDropDash)
					TempValue0 |= CheckResult
					if Player.Animation == ANI_HURT
						TempValue0 = false
					end if
					if TempValue0 == true
						game.callbackParam3 = 0 // (taken: the cast's press, not a shuriken's)
						PlaySfx({c['ninja_cast_sfx_cd']}, false)
{tab(cast_lines, 6)}						{v(1)} = {cast} // the pose
						if {v(0)} == {KINDS['mijin']}
							{v(1)} = {mijin}
						end if
						{v(0)} += {CASTING} // being cast
					end if
				end if
			end if
		end if
	end if
end if
if {v(1)} > 0 // the pose
	TempValue0 = false
	CheckEqual(Player.Animation, ANI_HURT)
	TempValue0 |= CheckResult
	CheckEqual(Player.Animation, ANI_DYING)
	TempValue0 |= CheckResult
	CheckEqual(Player.Animation, ANI_DROWNING)
	TempValue0 |= CheckResult
	CheckEqual(Player.ControlMode, CONTROLMODE_NONE)
	TempValue0 |= CheckResult
	if TempValue0 == true // a hit, his death or an object: over (no cost)
		{v(1)} = 0
		{v(0)} = 0
	else
		{v(1)}--
		if Player.InvincibleTimer < 3 // nothing hurts him meanwhile (the post-hit timer; no BlinkTimer: no flicker)
			Player.InvincibleTimer = 3
		end if
		if Player.Gravity == GRAVITY_GROUND
			Player.Speed = 0
			Player.XVelocity = 0
		else
			Player.XVelocity = 0 // hanging still in the air (melee_hang's; the state's gravity next frame cancelled)
			Player.Speed = 0
			Player.YVelocity = 0
			Player.YVelocity -= Player.GravityStrength
		end if
		if {v(0)} == {CASTING + KINDS['mijin']} // Mijin's frames (CD 49)
			Player.Animation = {ANI_MIJIN}
			TempValue0 = {mijin}
			TempValue0 -= {v(1)}
			TempValue0 /= {mticks}
			if TempValue0 >= {mijin // mticks}
				TempValue0 = {mijin // mticks - 1}
			end if
		else
			Player.Animation = {ANI_CAST} // the cast pose (CD 47)
			TempValue0 = {cast}
			TempValue0 -= {v(1)}
			TempValue0 /= {cticks}
			if TempValue0 >= {cast // cticks}
				TempValue0 = {cast // cticks - 1}
			end if
		end if
		Player.Frame = TempValue0 // (the timer picks the frame)
		Player.AnimationTimer = 0
		if {v(1)} == 0 // its end
			if Player.Gravity == GRAVITY_GROUND
				Player.Animation = ANI_STOPPED
			else
				Player.Animation = ANI_JUMPING
			end if
			if {v(0)} == {CASTING + KINDS['mijin']}
{tab(cost, 4)}			end if
			{v(0)} = 0
		end if
	end if
end if
if {v(2)} > 0 // Fushin: his jump strength (the game's, whatever set it last: the water too), {c['ninja_fushin_jump']}x
	{v(2)}--
	if Player.JumpStrength != {v(5)} // (the first frame, or the game set a new one)
		{v(6)} = Player.JumpStrength
		{v(5)} = Player.JumpStrength
		{v(5)} *= {q}
		{v(5)} >>= 8
		Player.JumpStrength = {v(5)}
	end if
	if {v(2)} == 0 // over: his own back
		if Player.JumpStrength == {v(5)}
			Player.JumpStrength = {v(6)}
		end if
		{v(5)} = 0
	end if
end if
{v(3)} = 0 // the held magic's icon
if {v(0)} > 0
	if {v(0)} < {CASTING}
{tab(listing, 2)}	end if
end if
"""


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): for each ninjutsu extra its NoSwap_AfterUpdate block
    (first: it takes up + Y before the shuriken's block reads it), the icons' frames (ObjectStartup: Global/Items.gif) and
    the HUD-layer pass (ObjectDraw)."""
    import monitor_swap
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("ninjutsu: CD's NoSwap_AfterUpdate isn't there once")
        t = t.replace(head, head + f"\tif Stage.PlayerListPos == {a} // [NoSwap] Joe Musashi's Ninjutsu (tools/ninjutsu.py)\n"
                      + tab(cd_after(i), 2) + "\tend if\n")
        if t.count("sub ObjectStartup\n") != 1:
            sys.exit("ninjutsu: expected one CD ObjectStartup")
        frames = "".join(f"\t\tSpriteFrame({px}, {py}, {w}, {h}, {x}, {y}) // {k - 1}: "
                         f"{next(n for n, v in KINDS.items() if v == k)}'s icon\n"
                         for k, (px, py, w, h, x, y) in sorted(CD_ICONS.items()))
        t = t.replace("sub ObjectStartup\n", "sub ObjectStartup\n"
                      f"\tif Stage.PlayerListPos == {a} // [NoSwap] ninjutsu (tools/ninjutsu.py): the held magic's icon, the "
                      "game's own monitor art\n" '\t\tLoadSpriteSheet("Global/Items.gif")\n' + frames + "\tend if\n", 1)
        w = max(f[2] for f in CD_ICONS.values())
        h = max(f[3] for f in CD_ICONS.values())
        bw, bh = w + 2 * monitor_swap.ICON_PAD_X, h + 2 * monitor_swap.ICON_PAD_Y
        cy = monitor_swap.ICON_TOP + bh // 2
        draw = f"""TempValue0 = Screen.CenterX
TempValue0 -= {bw // 2}
DrawRect(TempValue0, {monitor_swap.ICON_TOP}, {bw}, {bh}, 0, 0, 0, {monitor_swap.ICON_ALPHA})
TempValue0 = {cd_v(0)}
TempValue0--
DrawSpriteScreenXY(TempValue0, Screen.CenterX, {cy})"""
        t = monitor_swap.cd_hud_pass(t, a, cd_v(3), draw, "ninjutsu (tools/ninjutsu.py): his HUD-layer listing draws the "
                                     "held magic's icon, not him", "ninjutsu")
    return t


# ---------------------------------------------------------------- S3&K and Mania (their JSON)
def s3k_fields(c):
    """The fields the DLL (native/src/Ninjutsu.h) and the Mania mod (ManiaNinjutsu.h) read: gen_s3k_header.ability_fields
    appends them (OPTIONAL_FIELDS: only a ninjutsu extra's package has them)."""
    on = "ninjutsu" in c.get("abilities", [])
    get = c.get
    kariu = get("ninja_kariu") or {}
    mijin = get("ninja_mijin_blast") or {}
    flash = list(kariu.get("flash", []))
    if len(flash) > FLASH_MAX:
        raise SystemExit(f"ninjutsu: more than {FLASH_MAX} Kariu flash frames")
    mask = sum(1 << KINDS[k] for k in get("ninjutsu", []) if k in KINDS) if on else 0
    B, I, S = "bool", "int", "str"
    return [
        # Joe Musashi's Ninjutsu (tools/ninjutsu.py): the magics a monitor can store (bit k: kind k), the cast pose's
        # frames and ticks (extra 1), Mijin's (extra 6), Fushin's frames and jump (1/1000), Kariu's hit, flash and sound,
        # Mijin's blast (a box ninjaMijinX / Y px round him), and the charge's and cast's sounds
        (B, "ninjutsu", 1, on), (I, "ninjaKinds", 1, mask),
        (I, "ninjaCast", 1, get("ninja_cast", 0) if on else 0), (I, "ninjaCastTicks", 1, get("ninja_cast_ticks", 1) if on else 1),
        (I, "ninjaMijin", 1, get("ninja_mijin", 0) if on else 0),
        (I, "ninjaMijinTicks", 1, get("ninja_mijin_ticks", 1) if on else 1),
        (I, "ninjaFushin", 1, get("ninja_fushin", 0) if on else 0),
        (I, "ninjaFushinJump", 1, round(1000 * get("ninja_fushin_jump", 1.0)) if on else 1000),
        (I, "ninjaKariuHit", 1, kariu.get("hit", 0) if on else 0),
        (I, "ninjaKariuFlashCount", 1, len(flash) if on else 0),
        (I, "ninjaKariuFlash", FLASH_MAX, (flash + [0] * (FLASH_MAX - len(flash))) if on else [0] * FLASH_MAX),
        (S, "ninjaKariuSound", 1, kariu.get("sfx_s3k") if on else None),
        (I, "ninjaMijinHit", 1, mijin.get("hit", 0) if on else 0),
        (I, "ninjaMijinX", 1, mijin.get("reach_x", 0) if on else 0),
        (I, "ninjaMijinY", 1, mijin.get("reach_y", 0) if on else 0),
        (S, "ninjaMijinSound", 1, mijin.get("sfx_s3k") if on else None),
        (S, "ninjaSound", 1, get("ninja_sfx_s3k") if on else None),
        (S, "ninjaCastSound", 1, get("ninja_cast_sfx_s3k") if on else None),
    ]


S3K_FIELD_NAMES = {name for _, name, _, _ in s3k_fields({"abilities": []})}
