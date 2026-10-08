"""Gilius Thunderhead's pot magic (abilities.py "pot_magic"), in all four Origins games and Mania: the Sonic 1/2 code
(Retro Engine v4 player script; abilities.py calls v4_after / v4_after_pose / v4_tables / v4_patch / v4_update), Sonic
CD's (build_soniccd.py calls cd_patch / cd_update), the numbers the S3&K DLL and the Mania mod read (s3k_fields:
native/src/PotMagic.h, native/mania/src/ManiaPotMagic.h), and the Earthquake's art in the S1/S2 packages (build_v4_art,
from build_packages.py).

The user's design (2026-10-02): Joe Musashi's monitor-charged meter (tools/ninjutsu.py's "shared design note") with a cap
above 1, the Golden Axe way:
- Every item monitor that breaks while he plays (by anything: his body, his axe, the quake itself) adds a magic pot, up
  to pots_max (3). They're kept until cast (or until the stage restarts: a death or the next act, as every NoSwap move's
  state).
- The pots show at the top middle of the screen in the dark box (John Morris' sub-weapon box, Joe's Ninjutsu icon's
  place and look: tools/monitor_swap.py ICON_*), one picture per pot. The picture is a 16x16 crop of his own portrait on
  Ragey's sheet (no art drawn; the sheet has no pot): ability slot 48 (S1/S2: the reserved strip, STRIP_ICON).
- Up + Y casts the Earthquake (Y alone stays the axe chop; up + Y with no pots is the chop too), on the ground or in
  the air, from his own free states (not hurt, not held by an object; in mid-air Y transforms first when Super is
  possible: projectile-system.md's Y/Super rule). It spends every pot; the pots spent are its level (1 to pots_max):
  - its hit: Tails Doll's Screen Nuke mechanics (abilities.py melee_nuke), from its own object, in `pulses` waves of
    pots_hit frames, pots_gap frames apart, the first pots_first frames after the cast: everything in a box reach_x x
    reach_y px round him (reach_x 0: the whole screen) is hit as by his attack (badniks, monitors, bosses: a boss takes
    one hit per wave: 1 / 1 / 2 by default). Sonic CD: a square reach_cd round him.
  - the screen shakes for pots_shake frames (S1/S2 screen.shakeY, CD Screen.ShakeY, Mania Camera_ShakeScreen; S3&K has
    none: the DLL's camera layout isn't known, NoSwapS3K.cpp's Hammer Drop note), and a dark flash (pots_flash: Kariu's).
  - its art (Bad Moon's Golden Axe II Earthquake: Gilius_Magic_GA2.png, pasted onto his working sheet): `rocks` boulders
    per wave fall from the top of the screen, spread over the box (ROCK_*: where, when, how fast), and where each lands
    (the floor under it, at most ROCK_BELOW px under his feet; nothing above ROCK_ABOVE px over them counts) it bursts:
    the gold spikes, the white spikes, the dust cloud big to small (slot 46 after a big boulder, 47 after a small one,
    BURST_TICKS each). S1/S2: Tails Objects (the shots' type, tools/shots_v4.py) drawing the reserved strip's frames
    (STRIP); S3&K and Mania: drawn by the DLL / mod from his own animations (slots 45-47). Sonic CD has no spare object
    slots for them: the shake and the flash only there.
- The cast pose: ability slot 42 (CD 47, S3&K / Mania extra 1) for pots_cast frames, pots_cast_ticks each. He stands still
  on the ground and hangs still in the air, and nothing hurts him meanwhile (melee_safe's rule); a hit, a death or an
  object taking him ends the pose (the quake goes on).

State, per engine:
  count    the pots (0 .. pots_max)
  pose     the cast pose's frames left
  Sonic 1/2  NoSwap_pots (packed: noswap_common.PACKED_VALUES, Joe's NoSwap_ninja's slot): the count in its low 3 bits,
             the HUD listing above bit LISTING_SHIFT (as monitor_swap's ICON_VALUE); NoSwap_potsTime: the pose in its low
             6 bits. A monitor counted: its Broken Monitor's value30 (monitor_swap.MARK: not with monitor_swap or
             ninjutsu). The quake: a Tails Object marked MARK + 1 in value33 (value0 its age, value1 its level, value2
             his feet's y at the cast); a boulder MARK + 2 (value0 age, value1 its delay, value2 big 0 / small 1, value3
             its fall speed, value4 0 waiting / 1 falling / 2 bursting, value5 his feet's y).
  Sonic CD   Object[CD_SLOT] (Joe's: never touched by the game; one extra plays at a time): Value0 the count, Value1 the
             pose, Value3 the HUD listing, Value4 the monitor breaks seen (Global/Monitor.txt counts them in
             Object[monitor_swap.CD_SLOT].Value0). The quake: the first shot slot (a nuke: Value7 1), Value5 its level.
  S3&K, Mania  the DLL's pots::g_*, the Mania mod's g_pm* (0 at each stage load).
"""
import sys

VALUE, TIME = "NoSwap_pots", "NoSwap_potsTime"  # Sonic 1/2 (packed: noswap_common.PACKED_VALUES)
POSE_BITS = 6  # NoSwap_potsTime: the pose's frames in its low 6 bits
COUNT_MASK = 7  # NoSwap_pots: the count in its low 3 bits (pots_max at most 7)
LISTING_SHIFT = 4  # NoSwap_pots: the HUD listing above it
CD_SLOT = 14  # Sonic CD: Object[14] (ninjutsu.CD_SLOT: reserved, never touched; not with ninjutsu)
MARK = 0x4751  # S1/S2: the Tails Object's value33: MARK + 1 the quake, MARK + 2 a boulder (ninjutsu.MARK's 0x4E4A + 1/2)
ANI_CAST = "ANI_NOSWAP_HOVER"  # slot 42 (CD 47)
SLOT_CAST, SLOT_ROCKS, SLOT_BURST_BIG, SLOT_BURST_SMALL, SLOT_POT = "42", "45", "46", "47", "48"
FLASH_MAX = 32  # (gen_s3k_header.FLASH_MAX)
LEVELS_MAX = 7
# The boulders (the same numbers in every engine: PotMagic.h / ManiaPotMagic.h copy them): they appear ROCK_TOP px above
# the screen's top, fall from ROCK_VY0 px a frame gaining ROCK_G a frame up to ROCK_VMAX (16.16), one more every
# ROCK_STAGGER frames (the nearest to the middle first); a boulder lands on the floor under it once it's below
# ROCK_ABOVE px over his feet (at the cast), and is gone ROCK_BELOW px under them. Wave w (one per pulse) starts at the
# quake's frame 1 + w * pots_gap. Its boulders: n spread evenly over the box's width (rock_offsets), big and small in
# turn; the whole screen: over ROCK_SCREEN px either side of the screen's middle.
ROCK_TOP, ROCK_VY0, ROCK_G, ROCK_VMAX, ROCK_STAGGER, ROCK_ABOVE, ROCK_BELOW, ROCK_SCREEN = 40, 0x30000, 0x6000, 0xC0000, 3, 48, 160, 184
ROCK_R = (31, 16)  # the boulders' half heights (big, small): Gilius_Magic_GA2.png's 62x64 and 31x32
BURST_FRAMES, BURST_TICKS = 5, 4  # the burst: slot 46 / 47's frames (gold spikes, white spikes, dust big, mid, small)
# Sonic 1/2: the art in the reserved strip of his first player sheet (tools/shots_v4.py: TailsObject.txt's frames there).
# A boulder in a big box (64x64, its middle at the box's), each burst frame in a small one (64x32, its bottom on the box's
# bottom: drawn 16 px over the floor), the pot picture in a small one (its middle at the box's). {TailsObject frame: box}
STRIP_ROCKS = (4, 5)  # big boxes 0, 1 (shots_v4.BIG_BOXES)
STRIP_BURST = ((18, 19, 22, 23, 24), (25, 26, 27, 28, 29))  # swap boxes 2, 3, 6, 7, 8 / 9-13 (shots_v4.SWAP_BOXES)
STRIP_ICON = 30  # swap box 14
ICON_GAP = 2  # px between two pot pictures


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("pot_magic")


def nin():
    import ninjutsu
    return ninjutsu


def check(i):
    """The extra's pot_magic numbers, checked (the build stops on a mistake)."""
    c = ab().ABILITIES[i]
    m = c.get("pots_max", 3)
    if not isinstance(m, int) or not 1 <= m <= LEVELS_MAX:
        sys.exit(f"pot_magic: extra {i}: \"pots_max\" is 1 to {LEVELS_MAX}")
    for k in ("pots_levels", "pots_cast", "pots_cast_ticks", "pots_hit", "pots_gap", "pots_sfx", "pots_sfx_cd",
              "pots_cast_sfx", "pots_cast_sfx_cd", "pots_quake_sfx", "pots_quake_sfx_cd"):
        if k not in c:
            sys.exit(f"pot_magic: extra {i} needs \"{k}\"")
    levels = c["pots_levels"]
    if not isinstance(levels, list) or len(levels) != m:
        sys.exit(f"pot_magic: extra {i}: \"pots_levels\" has one entry per pot count (pots_max {m})")
    for n, lv in enumerate(levels, 1):
        if not isinstance(lv, dict) or any(not isinstance(lv.get(x), int) for x in ("reach_x", "reach_y", "reach_cd",
                                                                                      "pulses", "rocks")):
            sys.exit(f"pot_magic: extra {i}: level {n} needs reach_x, reach_y, reach_cd, pulses, rocks (whole numbers)")
        if (lv["reach_x"] == 0) != (lv["reach_y"] == 0) or lv["reach_x"] < 0 or lv["reach_y"] < 0 or lv["reach_cd"] < 1 \
                or not 1 <= lv["pulses"] <= 4 or not 0 <= lv["rocks"] <= 8:
            sys.exit(f"pot_magic: extra {i}: level {n}: reach_x / reach_y both 0 (the whole screen) or both above 0, "
                     "reach_cd at least 1, pulses 1 to 4, rocks 0 to 8")
    if not 0 < c["pots_cast"] < (1 << POSE_BITS) or c["pots_cast_ticks"] < 1:
        sys.exit(f"pot_magic: extra {i}: \"pots_cast\" is 1 to {(1 << POSE_BITS) - 1} frames, \"pots_cast_ticks\" at least 1")
    if c["pots_hit"] < 1 or c["pots_gap"] < c["pots_hit"] or c.get("pots_first", 0) < 0 or c.get("pots_shake", 0) < 0:
        sys.exit(f"pot_magic: extra {i}: \"pots_hit\" at least 1, \"pots_gap\" at least pots_hit, pots_first / "
                 "pots_shake 0 or more")
    flash = c.get("pots_flash", [])
    if len(flash) > FLASH_MAX or any(not 0 <= a <= 255 for a in flash):
        sys.exit(f"pot_magic: extra {i}: \"pots_flash\": at most {FLASH_MAX} darkness values 0-255")
    if any(a in c.get("abilities", []) for a in ("monitor_swap", "ninjutsu")):
        sys.exit(f"pot_magic: extra {i}: not with monitor_swap or ninjutsu (they count monitors with the same mark)")
    if not ab().has(i, "melee"):
        sys.exit(f"pot_magic: extra {i}: needs the melee (Y alone; up + Y is the cast)")
    return c


def levels(i):
    return check(i)["pots_levels"]


def end_age(i):
    """The quake's last frame: its last pulse's end, its flash's, its shake's."""
    c = check(i)
    p = max(lv["pulses"] for lv in levels(i))
    return max(c.get("pots_first", 0) + (p - 1) * c["pots_gap"] + c["pots_hit"], len(c.get("pots_flash", [])),
               c.get("pots_shake", 0)) + 1


def rock_offsets(span, n, wave):
    """Wave `wave`'s n boulders: [(x px from the middle, delay frames, big 0 / small 1)], spread evenly over -span ..
    span (a later wave half a step over), big and small in turn, the nearest to the middle first. The DLL and the Mania
    mod compute the same (PotMagic.h / ManiaPotMagic.h RockAt)."""
    if n <= 0:
        return []
    step = 2 * span / n
    rnd = lambda v: int(abs(v) + 0.5) * (1 if v >= 0 else -1)  # (half away from zero: C's lround)
    xs = [rnd(-span + step * (k + 0.5) + (step / 2 if wave % 2 else 0)) for k in range(n)]
    xs = [x if x <= span else x - 2 * span for x in xs]
    order = sorted(range(n), key=lambda k: (abs(xs[k]), xs[k]))
    return [(xs[k], ROCK_STAGGER * order.index(k), k % 2) for k in range(n)]


def tab(text, n):
    return nin().tab(text, n)


def sfx_line(name):
    return f"PlaySfx(SfxName[{name}], false)\n" if name else ""


# ---------------------------------------------------------------- Sonic 1/2
V4_VALUES = f"""public value {VALUE} = 0 // pot_magic: the pots, and the pots' HUD listing (tools/pot_magic.py)
public value {TIME} = 0 // pot_magic: the cast pose's frames left (tools/pot_magic.py)
"""


def v4_after(i):
    """In the extra's NoSwap_AfterUpdate, first (before his moves read Y): monitors fill the pots, up + Y casts."""
    c = check(i)
    mx = c.get("pots_max", 3)
    return f"""// [NoSwap] Pot magic (tools/pot_magic.py): broken monitors fill his pots, up + Y casts the Earthquake
{VALUE} &= {COUNT_MASK} // (the pots; the HUD listing above them is made afresh below)
foreach (TypeName[Broken Monitor], arrayPos0, ACTIVE_ENTITIES) // each monitor broken (by anything): a pot
	if object[arrayPos0].value30 == 0 // (counted once: tools/monitor_swap.py MARK)
		object[arrayPos0].value30 = 1
		if {VALUE} < {mx}
			{VALUE}++
			{sfx_line(c['pots_sfx']).rstrip()}
		end if
	end if
next
temp6 = {TIME}
temp6 &= {(1 << POSE_BITS) - 1}
if temp6 == 0
	if {VALUE} > 0 // pots to spend
		if keyPress[1].buttonY != false
			if keyDown[1].up != false // up + Y: the Earthquake
{tab(nin().FREE_V4, 4)}				if temp0 == true
					keyPress[1].buttonY = false // (the cast's press: no chop with it)
					{sfx_line(c['pots_cast_sfx']).rstrip()}
					CreateTempObject(TypeName[Tails Object], 0, player.xpos, player.ypos) // the quake (tools/pot_magic.py v4_quake_body)
					arrayPos0 = object[tempObjectPos].entityPos
					if object[arrayPos0].type == TypeName[Tails Object] // (made)
						object[arrayPos0].state = 0 // (no hit until its first wave)
						object[arrayPos0].priority = PRIORITY_ACTIVE
						object[arrayPos0].interaction = true
						object[arrayPos0].drawOrder = 6 // (the top layer: the flash goes over everything)
						object[arrayPos0].value0 = 0
						object[arrayPos0].value1 = {VALUE} // its level: the pots spent
						object[arrayPos0].value2 = player.ypos // his feet at the cast (the boulders land round there)
						object[arrayPos0].value2 += 0x140000
						object[arrayPos0].value36 = -1 // (nothing drawn until its update gives the flash)
						object[arrayPos0].value33 = {MARK + 1}
					end if
					{sfx_line(c['pots_quake_sfx']).rstrip()}
					{VALUE} = 0 // every pot spent
					{TIME} += {c['pots_cast']} // the pose
				end if
			end if
		end if
	end if
end if
"""


def v4_after_pose(i):
    """In the extra's NoSwap_AfterUpdate, last (after his moves, so the pose is what shows): the cast pose (a chop the
    cast's press started is cut) and the pots' HUD-layer listing."""
    import monitor_swap
    c = check(i)
    cast, cticks = c["pots_cast"], c["pots_cast_ticks"]
    frames = max(cast // cticks, 1)
    listing = monitor_swap.v4_hud_listing("temp0", "").split("\n", 1)[1]
    listing = listing.replace("temp0 = 1", "temp0 = 1 // (ours only: he's hidden)").replace("temp0 = 2", "temp0 = 2 "
                                                                                           "// (StageSetup's too, first)")
    return f"""// [NoSwap] Pot magic (tools/pot_magic.py): the cast pose, the pots' pictures
temp6 = {TIME}
temp6 &= {(1 << POSE_BITS) - 1}
if temp6 > 0 // the pose
	if NoSwap_melee > 0 // (a chop the cast's press started, if the engine kept the press: cut, the cast's shows)
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
	if temp0 == true // a hit, his death or an object: the pose is over (the quake goes on)
		{TIME} -= temp6
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
		player.animation = {ANI_CAST} // the cast pose (slot 42)
		temp0 = {cast}
		temp0 -= temp6
		temp0 /= {cticks}
		if temp0 >= {frames}
			temp0 = {frames - 1}
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
		end if
	end if
end if
temp0 = 0 // the pots' pictures: the HUD-layer pass (tools/monitor_swap.py v4_hud_listing)
if {VALUE} > 0
{tab(listing, 1)}end if
temp0 <<= {LISTING_SHIFT}
{VALUE} += temp0
"""


def v4_tables(i):
    c = check(i)
    flash = c.get("pots_flash", [])
    return ("// [NoSwap] Pot magic (tools/pot_magic.py): the Earthquake's burst frames (TailsObject frames: a big boulder's "
            f"burst, then a small one's)\nprivate table NoSwap_PotsBurst{i}\n\t"
            + ", ".join(str(f) for f in STRIP_BURST[0] + STRIP_BURST[1]) + "\nend table\n\n"
            + (f"// [NoSwap] Pot magic: the Earthquake's flash, its darkness per frame (0-255, SetScreenFade's alpha)\n"
               f"private table NoSwap_PotsFlash{i}\n\t" + ", ".join(str(a) for a in flash) + "\nend table\n\n"
               if flash else ""))


def v4_rock_spawn(span_expr, dx, delay, kind, k):
    """One boulder (a Tails Object, MARK + 2) from the quake's update (object: the quake): x the box's middle (temp1) +
    dx, y ROCK_TOP px over the screen's top."""
    return f"""temp0 = {dx} // boulder {k}: {dx:+d} px, after {delay} frames, {'big' if kind == 0 else 'small'}
temp0 <<= 16
temp0 += temp1
temp2 = screen.yoffset
temp2 -= {ROCK_TOP}
temp2 <<= 16
CreateTempObject(TypeName[Tails Object], 0, temp0, temp2)
arrayPos0 = object[tempObjectPos].entityPos
if object[arrayPos0].type == TypeName[Tails Object] // (made)
	object[arrayPos0].state = 0
	object[arrayPos0].priority = PRIORITY_ACTIVE
	object[arrayPos0].drawOrder = 4
	object[arrayPos0].value33 = {MARK + 2}
	object[arrayPos0].value0 = 0
	object[arrayPos0].value1 = {delay}
	object[arrayPos0].value2 = {kind}
	object[arrayPos0].value3 = {ROCK_VY0:#x}
	object[arrayPos0].value4 = 0
	object[arrayPos0].value5 = object.value2
	object[arrayPos0].value36 = -1 // (not drawn while it waits)
	object[arrayPos0].frame = {STRIP_ROCKS[kind]}
	object[arrayPos0].direction = {k % 2}
end if
"""


def v4_quake_body(i):
    """The quake's own update (object: it; abilities.nuke_update_body's, with waves): its flash (value36: TailsObject.txt
    draws it), the shake, each wave's boulders, and during each wave's pulse in the shots' group, a jumping player to the
    enemies' shot loops with its level's box round him (the whole screen: round the screen's middle)."""
    import shots_v4
    c = check(i)
    first, gap, hit = c.get("pots_first", 0), c["pots_gap"], c["pots_hit"]
    flash = c.get("pots_flash", [])
    shake = c.get("pots_shake", 0)
    out = [f"object.value0++ // its age (pot_magic: tools/pot_magic.py v4_quake_body)",
           f"if object.value0 > {end_age(i)}",
           "\tobject.type = TypeName[Blank Object]",
           "else"]
    if flash:
        out += [f"\tif object.value0 <= {len(flash)} // the flash",
                "\t\ttemp0 = object.value0", "\t\ttemp0--",
                f"\t\tGetTableValue(object.value36, temp0, NoSwap_PotsFlash{i})",
                "\t\tif object.value36 == 0", "\t\t\tobject.value36 = -1", "\t\tend if",
                "\telse", "\t\tobject.value36 = -1", "\tend if"]
    if shake:
        out += [f"\tif object.value0 <= {shake} // the shake (the game's own: screen.shakeY, kept going)",
                "\t\ttemp0 = object.value0", "\t\ttemp0 &= 7", "\t\tif temp0 == 1", "\t\t\tscreen.shakeY = 4",
                "\t\tend if", "\tend if"]
    out += ["\ttemp4 = false // in a wave's pulse"]
    for n, lv in enumerate(levels(i), 1):
        whole = lv["reach_x"] == 0
        body = []
        if whole:
            body += ["temp1 = screen.xoffset // the whole screen: round its middle",
                     "temp1 += screen.xcenter", "temp1 <<= 16",
                     "temp2 = screen.ysize", "temp2 >>= 1", "temp3 = temp2", "temp2 += screen.yoffset", "temp2 <<= 16"]
            span = ROCK_SCREEN
        else:
            body += ["temp1 = object[0].xpos // round him", "temp2 = object[0].ypos"]
            span = lv["reach_x"]
        body += ["object.xpos = temp1", "object.ypos = temp2"]
        for w in range(lv["pulses"]):
            s = first + w * gap
            body += [f"if object.value0 >= {s} // wave {w + 1}'s pulse", f"\tif object.value0 < {s + hit}",
                     "\t\ttemp4 = true", "\tend if", "end if"]
            rocks = rock_offsets(span, lv["rocks"], w)
            if rocks:
                body += [f"if object.value0 == {1 + w * gap} // wave {w + 1}'s boulders"]
                body += ["\t" + l for r, (dx, d, kind) in enumerate(rocks)
                         for l in v4_rock_spawn(span, dx, d, kind, r).rstrip("\n").split("\n")]
                body += ["end if"]
        body += ["if temp4 == true // its hit: the shots' group, a jumping player 1 with the box",
                 f"\tobject.groupID = {shots_v4.GROUP}", f"\tobject.state = {shots_v4.LIVE}",
                 "\tobject.animation = ANI_JUMPING", "\tobject.gravity = GRAVITY_GROUND",
                 "\tobject.value16 = false // isSidekick", "\tobject.value19 = object[0].value19 // badnikBonus"]
        if whole:
            body += ["\tobject.value39 = temp3 // hitbox top, bottom, left, right: the screen and 16 px",
                     "\tobject.value39 += 16", "\tobject.value38 = object.value39", "\tFlipSign(object.value38)",
                     "\tobject.value41 = screen.xcenter", "\tobject.value41 += 16", "\tobject.value40 = object.value41",
                     "\tFlipSign(object.value40)"]
        else:
            body += [f"\tobject.value38 = -{lv['reach_y']} // hitbox top, bottom, left, right",
                     f"\tobject.value39 = {lv['reach_y']}", f"\tobject.value40 = -{lv['reach_x']}",
                     f"\tobject.value41 = {lv['reach_x']}"]
        body += ["else", "\tobject.groupID = TypeName[Tails Object] // (out of it: no hit now)", "\tobject.state = 0",
                 "end if"]
        out += [f"\tif object.value1 == {n} // level {n}: {n} pot{'s' if n > 1 else ''}"] + ["\t\t" + l for l in body] \
            + ["\tend if"]
    out += ["end if"]
    return "\n".join(out) + "\n"


def v4_rock_body(i):
    """A boulder's own update (object: it): waits its delay (hidden), falls, lands on the floor under it (only below
    ROCK_ABOVE px over his feet; gone ROCK_BELOW px under them), then plays its burst (16 px over the floor) and goes."""
    rb, rs = ROCK_R
    return f"""object.value0++ // its age (pot_magic: tools/pot_magic.py v4_rock_body)
if object.value4 == 0 // waiting
	if object.value0 >= object.value1
		object.value4 = 1
		object.value36 = 0 // (drawn: its frame)
	end if
else
	if object.value4 == 1 // falling
		object.ypos += object.value3
		if object.value3 < {ROCK_VMAX:#x}
			object.value3 += {ROCK_G:#x}
		end if
		temp0 = object.value5
		temp0 -= {ROCK_ABOVE << 16:#x}
		if object.ypos >= temp0 // (low enough: the floor counts)
			temp1 = {rb}
			if object.value2 == 1
				temp1 = {rs}
			end if
			ObjectTileCollision(CSIDE_FLOOR, 0, temp1, object[0].collisionPlane)
			if checkResult == true // landed: its burst, 16 px over the floor
				temp1 -= 16
				temp1 <<= 16
				object.ypos += temp1
				object.value4 = 2
				object.value0 = 0
			end if
		end if
		temp0 = object.value5
		temp0 += {ROCK_BELOW << 16:#x}
		if object.ypos > temp0 // (fell past: gone)
			object.type = TypeName[Blank Object]
		end if
	end if
	if object.value4 == 2 // bursting
		temp0 = object.value0
		temp0 /= {BURST_TICKS}
		if temp0 >= {BURST_FRAMES}
			object.type = TypeName[Blank Object]
		else
			temp1 = object.value2
			temp1 *= {BURST_FRAMES}
			temp0 += temp1
			GetTableValue(object.frame, temp0, NoSwap_PotsBurst{i})
		end if
	end if
end if
if object.value0 > 400 // (a safety net)
	object.type = TypeName[Blank Object]
end if
"""


def v4_looks(i):
    """NoSwap_ShotLooks for him (abilities.shot_update_function): the quake sets its own looks each pulse (v4_quake_body);
    this is the same jumping player 1, his own box."""
    return """object.animation = ANI_JUMPING
object.gravity = GRAVITY_GROUND
object.value16 = false // isSidekick
object.value19 = object[0].value19 // badnikBonus
"""


def v4_update(i):
    """NoSwap_ShotUpdate's body for him (abilities.shot_update_function: he has no shot): the quake's and the boulders'
    updates by their mark; anything else of his type is removed."""
    return (f"if object.value33 == {MARK + 1} // [NoSwap] the Earthquake (tools/pot_magic.py)\n" + tab(v4_quake_body(i), 1)
            + "else\n" + f"\tif object.value33 == {MARK + 2} // one of its boulders\n" + tab(v4_rock_body(i), 2)
            + "\telse\n\t\tobject.type = TypeName[Blank Object] // (nothing else of his)\n\tend if\nend if\n")


def v4_hud_pass(t, alias, draw):
    """ninjutsu.v4_hud_pass with this module's value."""
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    body = t[start + len("event ObjectDraw\n"):end]
    s = 1 << LISTING_SHIFT
    head = f"""	temp7 = false // [NoSwap] pot_magic (tools/pot_magic.py): his HUD-layer listing draws the pots, not him
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


def v4_patch(t, game):
    """The S1/S2 player script (after every other module's patches): his values and tables, the pot picture's frame
    (ObjectStartup: his first player sheet's reserved strip, STRIP_ICON's box) and the HUD-layer pass (ObjectDraw)."""
    import monitor_swap
    import shots_v4
    if not ids():
        return t
    anchor = "public value Player_superState"
    if t.count(anchor) != 1:
        sys.exit("pot_magic: Player_superState isn't there once")
    t = t.replace(anchor, V4_VALUES + "\n" + anchor)
    anchor = "// [NoSwap] Ability modules for extra characters (generated by tools/abilities.py)\n"
    if t.count(anchor) != 1:
        sys.exit("pot_magic: the ability modules' first line isn't there once")
    t = t.replace(anchor, anchor + "".join(v4_tables(i) for i in ids()))
    if t.count("event ObjectStartup\n") != 1 or t.count("event ObjectDraw\n") != 1:
        sys.exit("pot_magic: expected one ObjectStartup and one ObjectDraw")
    x, y, bw, bh = shots_v4.SWAP_BOXES[STRIP_ICON - shots_v4.SWAP_FRAME]
    for i in ids():
        a = ab().ALIAS_OF[i]
        t = t.replace("event ObjectStartup\n", "event ObjectStartup\n"
                      f"\tif stage.playerListPos == {a} // [NoSwap] pot_magic (tools/pot_magic.py): the pot picture, a "
                      "crop of his portrait in his first player sheet's reserved strip\n"
                      f'\t\tLoadSpriteSheet("{shots_v4.SHEET}")\n'
                      f"\t\tSpriteFrame(-8, -8, 16, 16, {x + bw // 2 - 8}, {y + bh // 2 - 8}) // 0: a pot\n\tend if\n", 1)
        pad_x, pad_y = monitor_swap.ICON_PAD_X, monitor_swap.ICON_PAD_Y
        bh2 = 16 + 2 * pad_y
        cy = monitor_swap.ICON_TOP + bh2 // 2
        draw = f"""temp1 = {VALUE} // the pots: one picture each, in the dark box (John Morris' sub-weapon box's look)
temp1 &= {COUNT_MASK}
temp2 = temp1 // the pictures' width
temp2 *= {16 + ICON_GAP}
temp2 -= {ICON_GAP}
temp0 = temp2
temp0 += {2 * pad_x}
temp3 = screen.xcenter
temp4 = temp0
temp4 >>= 1
temp3 -= temp4
DrawRect(temp3, {monitor_swap.ICON_TOP}, temp0, {bh2}, 0, 0, 0, {monitor_swap.ICON_ALPHA})
temp3 += {pad_x + 8} // the first picture's middle
while temp1 > 0
	DrawSpriteScreenXY(0, temp3, {cy})
	temp3 += {16 + ICON_GAP}
	temp1--
loop"""
        t = v4_hud_pass(t, a, draw)
    return t


def build_v4_art(e, sheet_path):
    """The Earthquake's frames and the pot picture in the reserved strip of his first player sheet (shots_v4.SHEET),
    pixel for pixel from his working sheet's frames (slots 45-48), in his own palette slots (build_packages.py, after
    build_player_art: he has no shot, so the strip is his)."""
    from PIL import Image
    import shots_v4
    from gifio import save_sheet
    import character_json
    c = character_json.load(e["art"])
    anims = c.get("ability_animations") or {}
    if not all(s in anims for s in (SLOT_ROCKS, SLOT_BURST_BIG, SLOT_BURST_SMALL, SLOT_POT)):
        sys.exit(f"pot_magic: {e['art'].name}: no character.json ability_animations (slots 45-48)")
    src = Image.open(c["folder"] / c["sheet"]["file"]).convert("RGB")
    bg = {tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)) for h in c["sheet"].get("background", [])}
    slots = {}
    for s, rgb in e["palette"].items():
        slots[((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)] = int(s)
    for h, s in (c["palette"].get("shared") or {}).items():
        slots[tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))] = int(s)

    def cut(name):
        x, y, w, h = c["frames"][name]
        im = Image.new("P", (w, h), 0)
        px, out = src.load(), im.load()
        for i in range(w):
            for j in range(h):
                rgb = px[x + i, y + j]
                if rgb in bg:
                    continue
                out[i, j] = slots[rgb] if rgb in slots else min(
                    slots.items(), key=lambda kv: sum((a - b) ** 2 for a, b in zip(kv[0], rgb)))[1]
        return im

    def names(slot):
        return [f if isinstance(f, str) else f["frame"] for f in anims[slot]["frames"]]
    sheet = Image.open(sheet_path)
    sheet.load()
    if sheet.mode != "P" or sheet.height > shots_v4.RESERVED_Y or sheet.width < 4 * shots_v4.BOX_W:
        sys.exit(f"pot_magic: {sheet_path} is {sheet.mode} {sheet.width}x{sheet.height}: expected a paletted sheet at least "
                 f"{4 * shots_v4.BOX_W} wide and at most {shots_v4.RESERVED_Y} high")
    out = Image.new("P", (sheet.width, shots_v4.RESERVED_Y + 4 * shots_v4.BOX_H), 0)
    out.putpalette(sheet.getpalette())
    out.paste(sheet, (0, 0))
    placed = []
    for frame, name in zip(STRIP_ROCKS, names(SLOT_ROCKS)):  # (a boulder: its middle at the big box's)
        x, y, w, h = shots_v4.BIG_BOXES[frame - shots_v4.FRAMES]
        im = cut(name)
        placed.append((im, (x + w // 2 - im.width // 2, y + h // 2 - im.height // 2), (x, y, w, h)))
    for frames, slot in zip(STRIP_BURST, (SLOT_BURST_BIG, SLOT_BURST_SMALL)):  # (a burst frame: its bottom on the box's)
        for frame, name in zip(frames, names(slot)):
            x, y, w, h = shots_v4.SWAP_BOXES[frame - shots_v4.SWAP_FRAME]
            im = cut(name)
            placed.append((im, (x + w // 2 - im.width // 2, y + h - im.height), (x, y, w, h)))
    x, y, w, h = shots_v4.SWAP_BOXES[STRIP_ICON - shots_v4.SWAP_FRAME]
    im = cut(names(SLOT_POT)[0])
    if im.size != (16, 16):
        sys.exit(f"pot_magic: {e['art'].name}: the pot picture (slot 48) must be 16x16, not {im.width}x{im.height}")
    placed.append((im, (x + w // 2 - 8, y + h // 2 - 8), (x, y, w, h)))
    for im, at, (x, y, w, h) in placed:
        if at[0] < x or at[1] < y or at[0] + im.width > x + w or at[1] + im.height > y + h:
            sys.exit(f"pot_magic: a {im.width}x{im.height} frame doesn't fit its {w}x{h} box")
        mask = im.point(lambda v: 255 if v else 0, "L")
        out.paste(im, at, mask)
    save_sheet(out, sheet_path)


def build_art(extras, packages):
    """build_packages.py: each pot_magic package's Sonic 1/2 strip (build_v4_art)."""
    import shots_v4
    made = []
    for e in extras:
        if not ab().has(e["id"], "pot_magic"):
            continue
        for game in ("Sonic1u", "Sonic2u"):
            build_v4_art(e, packages / e["art"].name / game / "Data" / "Sprites" / shots_v4.SHEET)
        made.append(e["art"].name)
    print(f"Sonic1u/Sonic2u: the Earthquake's frames in the reserved strip of {shots_v4.SHEET}: {', '.join(made) or 'no package'}")


# ---------------------------------------------------------------- Sonic CD
def cd_v(k):
    return f"Object[{CD_SLOT}].Value{k}"


def cd_after(i):
    """The CD NoSwap_AfterUpdate block (v4_after's and v4_after_pose's), first: Y from the DLL (game.callbackParam3 1),
    up held."""
    import monitor_swap
    import shots_v3
    c = check(i)
    v = cd_v
    mx = c.get("pots_max", 3)
    cast, cticks = c["pots_cast"], c["pots_cast_ticks"]
    frames = max(cast // cticks, 1)
    slot = shots_v3.SLOTS[0]
    listing = "\n".join(monitor_swap.cd_hud_listing(v(3), "pot_magic (tools/pot_magic.py): the pots' pictures, drawn in "
                                                           "the HUD's layer (ObjectDraw)"))
    return f"""// Pot magic (tools/pot_magic.py): broken monitors fill his pots, up + Y casts the Earthquake
if Object[12].Value0 != {v(4)} // monitors broke (Global/Monitor.txt counts them: tools/monitor_swap.py cd_monitor)
	TempValue0 = Object[12].Value0
	TempValue0 -= {v(4)}
	{v(4)} = Object[12].Value0
	if TempValue0 > 0
		if {v(0)} < {mx}
			PlaySfx({c['pots_sfx_cd']}, false)
		end if
		{v(0)} += TempValue0
		if {v(0)} > {mx}
			{v(0)} = {mx}
		end if
	end if
end if
if {v(1)} == 0
	if {v(0)} > 0 // pots to spend
		if game.callbackParam3 == 1 // Y, from the DLL
			if Player.Up == true // up + Y: the Earthquake
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
					game.callbackParam3 = 0 // (taken: the cast's press, not a chop's)
					PlaySfx({c['pots_cast_sfx_cd']}, false)
					ResetObjectEntity({slot}, TypeName[Tails Object], 0, Player.XPos, Player.YPos) // the quake (cd_update)
					Object[{slot}].State = 0
					Object[{slot}].Priority = PRIORITY_ACTIVE
					Object[{slot}].DrawOrder = 6 // (the top layer: the fade goes over everything)
					Object[{slot}].Value2 = 0
					Object[{slot}].Value4 = Player.CollisionPlane
					Object[{slot}].Value5 = {v(0)} // its level: the pots spent
					Object[{slot}].Value6 = -1 // (nothing drawn until its update gives the fade)
					Object[{slot}].Value7 = 1 // a nuke: NoSwap_ShotTouch leaves it, TailsObject.txt draws its fade
					PlaySfx({c['pots_quake_sfx_cd']}, false)
					{v(0)} = 0 // every pot spent
					{v(1)} = {cast} // the pose
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
	if TempValue0 == true // a hit, his death or an object: the pose is over (the quake goes on)
		{v(1)} = 0
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
		Player.Animation = {ANI_CAST} // the cast pose (CD 47)
		TempValue0 = {cast}
		TempValue0 -= {v(1)}
		TempValue0 /= {cticks}
		if TempValue0 >= {frames}
			TempValue0 = {frames - 1}
		end if
		Player.Frame = TempValue0 // (the timer picks the frame)
		Player.AnimationTimer = 0
		if {v(1)} == 0 // its end
			if Player.Gravity == GRAVITY_GROUND
				Player.Animation = ANI_STOPPED
			else
				Player.Animation = ANI_JUMPING
			end if
		end if
	end if
end if
{v(3)} = 0 // the pots' pictures
if {v(0)} > 0
{tab(listing, 1)}end if
"""


def cd_update(i):
    """NoSwap_ShotUpdate's lines for him (build_soniccd: he has no shot): the quake (a nuke in the first shot slot,
    build_soniccd.nuke_update_cd's, with waves): on him all its life, the flash's darkness per frame in Value6, the
    shake, and LIVE during each wave's pulse with its level's square reach (Value3)."""
    import shots_v3
    c = check(i)
    first, gap, hit = c.get("pots_first", 0), c["pots_gap"], c["pots_hit"]
    flash = c.get("pots_flash", [])
    shake = c.get("pots_shake", 0)
    out = ["Object.Value2++ // its age (pot_magic: tools/pot_magic.py cd_update)", "Object.XPos = Player.XPos",
           "Object.YPos = Player.YPos", f"if Object.Value2 > {end_age(i)}", "\tObject.Type = TypeName[Blank Object]",
           "else"]
    if flash:
        out += ["\tObject.Value6 = -1", "\tswitch Object.Value2 // the flash's darkness"]
        out += [l for k, a in enumerate(flash) for l in (f"\tcase {k + 1}", f"\t\tObject.Value6 = {a if a else -1}",
                                                         "\t\tbreak")]
        out += ["\tend switch"]
    if shake:
        out += [f"\tif Object.Value2 <= {shake} // the shake (the game's own: Screen.ShakeY, kept going)",
                "\t\tTempValue0 = Object.Value2", "\t\tTempValue0 &= 7", "\t\tif TempValue0 == 1",
                "\t\t\tScreen.ShakeY = 4", "\t\tend if", "\tend if"]
    out += ["\tTempValue1 = false // in a wave's pulse"]
    for n, lv in enumerate(levels(i), 1):
        body = [f"Object.Value3 = {lv['reach_cd'] << 16:#x} // its reach"]
        for w in range(lv["pulses"]):
            s = first + w * gap
            body += [f"if Object.Value2 >= {s} // wave {w + 1}'s pulse", f"\tif Object.Value2 < {s + hit}",
                     "\t\tTempValue1 = true", "\tend if", "end if"]
        out += [f"\tif Object.Value5 == {n} // level {n}"] + ["\t\t" + l for l in body] + ["\tend if"]
    out += ["\tif TempValue1 == true", f"\t\tObject.State = {shots_v3.LIVE} // its hit", "\telse",
            "\t\tObject.State = 0 // (no hit now: the targets' tests pass it by)", "\tend if", "end if"]
    return out


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): his NoSwap_AfterUpdate block (first: it takes
    up + Y before the chop reads it) and the HUD-layer pass (ObjectDraw): one pot picture each (slot 48, CD 49: his own
    animation, drawn as him at each place, monitor_swap.cd_patch's way)."""
    import monitor_swap
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("pot_magic: CD's NoSwap_AfterUpdate isn't there once")
        t = t.replace(head, head + f"\tif Stage.PlayerListPos == {a} // [NoSwap] Gilius' pot magic (tools/pot_magic.py)\n"
                      + tab(cd_after(i), 2) + "\tend if\n")
        pad_x, pad_y = monitor_swap.ICON_PAD_X, monitor_swap.ICON_PAD_Y
        bh = 16 + 2 * pad_y
        cy = monitor_swap.ICON_TOP + bh // 2
        import cd_config
        ani = cd_config.ABILITY_SLOTS[SLOT_POT]
        draw = f"""TempValue1 = {cd_v(0)} // the pots: one picture each, in the dark box
TempValue2 = TempValue1
TempValue2 *= {16 + ICON_GAP}
TempValue2 -= {ICON_GAP}
TempValue2 += {2 * pad_x}
TempValue3 = Screen.CenterX
TempValue0 = TempValue2
TempValue0 >>= 1
TempValue3 -= TempValue0
DrawRect(TempValue3, {monitor_swap.ICON_TOP}, TempValue2, {bh}, 0, 0, 0, {monitor_swap.ICON_ALPHA})
TempValue3 += {pad_x + 8}
TempValue0 = Player.Animation
TempValue2 = Player.Frame
TempValue4 = Player.XPos
TempValue5 = Player.YPos
TempValue6 = Player.Direction
Object[{CD_SLOT}].Value5 = Player.Rotation
Object[{CD_SLOT}].Value6 = Player.Visible
Player.Animation = {ani} // the pot (slot 48)
Player.Frame = 0
Player.Direction = 0
Player.Rotation = 0
Player.Visible = true
Player.YPos = Screen.YOffset
Player.YPos += {cy}
Player.YPos *= 65536
while TempValue1 > 0
	Player.XPos = Screen.XOffset
	Player.XPos += TempValue3
	Player.XPos *= 65536
	DrawPlayerAnimation()
	TempValue3 += {16 + ICON_GAP}
	TempValue1--
loop
Player.Animation = TempValue0
Player.Frame = TempValue2
Player.XPos = TempValue4
Player.YPos = TempValue5
Player.Direction = TempValue6
Player.Rotation = Object[{CD_SLOT}].Value5
Player.Visible = Object[{CD_SLOT}].Value6"""
        t = monitor_swap.cd_hud_pass(t, a, cd_v(3), draw, "pot_magic (tools/pot_magic.py): his HUD-layer listing draws the "
                                     "pots, not him", "pot_magic")
    return t


# ---------------------------------------------------------------- S3&K and Mania (their JSON)
def s3k_fields(c):
    """The fields the DLL (native/src/PotMagic.h) and the Mania mod (ManiaPotMagic.h) read: gen_s3k_header.ability_fields
    appends them (OPTIONAL_FIELDS: only a pot_magic extra's package has them)."""
    on = "pot_magic" in c.get("abilities", [])
    get = c.get
    lv = list(get("pots_levels") or []) if on else []
    flash = list(get("pots_flash", [])) if on else []
    if len(flash) > FLASH_MAX or len(lv) > LEVELS_MAX:
        raise SystemExit(f"pot_magic: more than {FLASH_MAX} flash frames or {LEVELS_MAX} levels")
    pad = lambda xs: xs + [0] * (LEVELS_MAX - len(xs))
    B, I, S = "bool", "int", "str"
    return [
        # Gilius' pot magic (tools/pot_magic.py): the most pots, the cast pose's frames and ticks (extra 1), each wave's
        # hit frames, the frames between waves and before the first, the shake's frames, the flash, per level (index:
        # pots spent - 1) the box (px round him; 0: the whole screen), waves and boulders, and the sounds
        (B, "potMagic", 1, on), (I, "potsMax", 1, get("pots_max", 3) if on else 0),
        (I, "potsCast", 1, get("pots_cast", 0) if on else 0), (I, "potsCastTicks", 1, get("pots_cast_ticks", 1) if on else 1),
        (I, "potsHit", 1, get("pots_hit", 0) if on else 0), (I, "potsGap", 1, get("pots_gap", 0) if on else 0),
        (I, "potsFirst", 1, get("pots_first", 0) if on else 0), (I, "potsShake", 1, get("pots_shake", 0) if on else 0),
        (I, "potsFlashCount", 1, len(flash)), (I, "potsFlash", FLASH_MAX, flash + [0] * (FLASH_MAX - len(flash))),
        (I, "potsLevelX", LEVELS_MAX, pad([v["reach_x"] for v in lv])),
        (I, "potsLevelY", LEVELS_MAX, pad([v["reach_y"] for v in lv])),
        (I, "potsLevelPulses", LEVELS_MAX, pad([v["pulses"] for v in lv])),
        (I, "potsLevelRocks", LEVELS_MAX, pad([v["rocks"] for v in lv])),
        (S, "potsSound", 1, get("pots_sfx_s3k") if on else None),
        (S, "potsCastSound", 1, get("pots_cast_sfx_s3k") if on else None),
        (S, "potsQuakeSound", 1, get("pots_quake_sfx_s3k") if on else None),
    ]


S3K_FIELD_NAMES = {name for _, name, _, _ in s3k_fields({"abilities": []})}
