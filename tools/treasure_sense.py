"""Rouge's Treasure Sense and Jewel Thief (abilities.py "treasure_sense", "jewel_thief"), in all four games: the Sonic 1/2
code (Retro Engine v4 player script; abilities.py and the S1/S2 builders call in here), Sonic CD's (build_soniccd.py calls
cd_patch / cd_broken_monitor) and the numbers the S3&K DLL reads (native/src/TreasureSense.h).

The user's approved lean first version (2026-09-30):
- Treasure Sense: Y on the GROUND (standing, walking or running in the plain ground state; not hurt, not held by an
  object or a cutscene). She stops for sense_pause frames in her own "Looking Up" pose (her ears up: listening), then
  for sense_show frames a marker points at the nearest treasure: at the SCREEN EDGE along the line from her to it, or
  on it when it's on screen, BLINKING faster the closer it is (metal-detector style: lit for half of a period that runs
  from BLINK_FAR frames at FAR px or more down to BLINK_NEAR at NEAR px or less; distance = px across + px down). It
  follows her and the treasure (looked up again every frame; one taken, the next nearest). Then sense_cooldown frames.
  Nothing found when the pause ends: no marker, a soft "no signal" sound (sense_sfx*), and the cooldown.
  Y in the air stays her Screw Kick.
- Treasure per game (the nearest by that distance):
    Sonic 1   the end-of-act giant ring (Special Ring, still floating) if the stage has one; otherwise the nearest unopened
              item monitor (type Monitor: a broken one becomes a Broken Monitor)
    Sonic 2   the nearest unopened item monitor
    Sonic CD  the big ring (Special Ring, still idle) if there is one; otherwise the nearest unopened monitor
    S3&K      the hidden giant rings (SpecialRing entities still in the stage and drawn: the game removes collected ones)
- The marker: the game's own ring, exact pixels (S1/S2/CD Global/Items.gif (1, 1, 16, 16), Ring.txt's frame 0; S3&K
  3K_Global/Ring.bin "Normal Ring" frame 0), drawn in screen space in the HUD's layer, in the pass John Morris' sub-weapon
  icon uses (tools/monitor_swap.py v4_hud_listing / v4_hud_pass, cd_hud_listing / cd_hud_pass; the DLL's icon pass
  shots::PlayerDraw). Never while a title card or the act results are up, without the HUD, in special stages (other
  player objects), or while she's held (S1/S2 / CD control mode NONE; S3&K Held()).
- Jewel Thief (passive): a 10-ring monitor gives her 20. S1/S2: Global/BrokenMonitor.txt's ring item calls the player
  script's NoSwap_RingMonitor right after its own +10 (so the game's cap at 999 and its extra life follow); every player
  script defines it (empty but for a jewel thief). CD: the same call in its BrokenMonitor. S3&K: the DLL wraps ItemBox's
  powerup (type 0, the ring box) and gives 10 more through the game's own Player_GiveRings. No other monitor changes.

State (S1/S2 NoSwap_treasure, packed; CD Object[CD_SLOT].Value0; the DLL's g_t), the same numbers everywhere:
  0 ready; 1..PAUSE the pause (frames so far); PAUSE+1..PAUSE+SHOW the marker; below 0 the cooldown (counting up).
"""
import sys

VALUE, ICON = "NoSwap_treasure", "NoSwap_senseIcon"  # Sonic 1/2 (packed: noswap_common.PACKED_VALUES)
CD_SLOT = 13  # Sonic CD: Object[13] (a reserved slot nothing touches: docs/soniccd_map.md section 4): Value0 the state,
# Value1 the HUD-layer listing
MARGIN = 12  # the marker's centre stays this far inside the screen's edges
NEAR, FAR = 64, 2048  # px (across + down)...
HALF_NEAR, HALF_FAR = 2, 16  # ...and the blink's half period there (a period of 4 frames very close, 32 far)
RING = (-8, -8, 16, 16, 1, 1)  # S1/S2/CD Global/Items.gif: the ring's first frame (Ring.txt's SpriteFrame 0)
V4_VALUES = f"""public value {VALUE} = 0 // treasure_sense: its state (tools/treasure_sense.py)
public value {ICON} = 0 // treasure_sense: the marker's HUD-layer listings this frame (tools/monitor_swap.py v4_hud_listing)
"""


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("treasure_sense")


def thieves():
    return ab().with_ability("jewel_thief")


def check(i):
    c = ab().ABILITIES[i]
    for k in ("sense_pause", "sense_show", "sense_cooldown", "sense_sfx", "sense_sfx_cd", "sense_sfx_s3k"):
        if k not in c:
            sys.exit(f"treasure_sense: extra {i} needs \"{k}\"")
    if not (0 < c["sense_pause"] and 0 < c["sense_show"] and c["sense_cooldown"] >= 0):
        sys.exit(f"treasure_sense: extra {i}: its frames must be positive")
    return c


def tab(text, n):
    return "".join("\t" * n + l + "\n" if l.strip() else "\n" for l in text.rstrip("\n").split("\n"))


# ---------------------------------------------------------------- Sonic 1/2
def v4_after(i):
    """In the extra's NoSwap_AfterUpdate (after she's moved): the Y press on the ground, the pause (her Looking Up pose,
    held still), the search when it ends, the marker's time and the cooldown; and the HUD-layer listing while it shows."""
    import monitor_swap
    c = check(i)
    p, s = c["sense_pause"], c["sense_show"]
    listing = monitor_swap.v4_hud_listing(ICON, "treasure_sense (tools/treasure_sense.py): the marker, drawn in the HUD's "
                                                "layer (ObjectDraw)")
    return f"""// Treasure Sense (tools/treasure_sense.py): Y on the ground
if {VALUE} < 0 // the cooldown
	{VALUE}++
end if
temp0 = false // on the ground, free: the plain ground state, not hurt, not held
if player.gravity == GRAVITY_GROUND
	CheckEqual(player.state, Player_State_Ground)
	temp0 = checkResult
end if
if player.animation == ANI_HURT
	temp0 = false
end if
if player.controlMode == CONTROLMODE_NONE
	temp0 = false
end if
if {VALUE} == 0
	if keyPress[1].buttonY != false
		if temp0 == true
			{VALUE} = 1
		end if
	end if
end if
if {VALUE} > 0
	if {VALUE} <= {p} // the pause: listening
		if temp0 == false // a jump, a hit, an object: over
			{VALUE} = 0
		else
			player.speed = 0
			player.xvel = 0
			player.animation = ANI_LOOKINGUP
			player.prevAnimation = ANI_LOOKINGUP
			player.frame = 0
			player.animationTimer = 0
			{VALUE}++
			if {VALUE} > {p}
				CallFunction(NoSwap_TreasureFind{i})
				if temp0 == false // no signal
					PlaySfx(SfxName[{c['sense_sfx']}], false)
					{VALUE} = -{c['sense_cooldown']}
				end if
			end if
		end if
	else
		{VALUE}++
		if {VALUE} > {p + s}
			{VALUE} = -{c['sense_cooldown']}
		end if
	end if
end if
{ICON} = 0
if {VALUE} > {p} // the marker: the HUD-layer pass (not while she's held)
	if player.controlMode != CONTROLMODE_NONE
{tab(listing, 2)}	end if
end if
"""


def near_v4(depth):
    """The nearest so far (temp0 any, temp1 / temp2 its place, temp3 how far) against object[arrayPos0]."""
    return tab("""temp4 = object[arrayPos0].xpos
temp4 -= player.xpos
temp4 >>= 16
if temp4 < 0
	FlipSign(temp4)
end if
temp5 = object[arrayPos0].ypos
temp5 -= player.ypos
temp5 >>= 16
if temp5 < 0
	FlipSign(temp5)
end if
temp4 += temp5
temp5 = true
if temp0 == true
	if temp4 >= temp3
		temp5 = false
	end if
end if
if temp5 == true
	temp0 = true
	temp3 = temp4
	temp1 = object[arrayPos0].ixpos
	temp2 = object[arrayPos0].iypos
end if""", depth)


def v4_find_function(i, game):
    ring = ""
    if game == "Sonic1u":  # (Sonic 2 has no giant ring object)
        ring = ("\tforeach (TypeName[Special Ring], arrayPos0, ALL_ENTITIES) // the end-of-act giant ring first\n"
                "\t\tif object[arrayPos0].state == 0 // (SPECIALRING_FLOATING: not entered)\n" + near_v4(3)
                + "\t\tend if\n\tnext\n")
    return (f"// [NoSwap] Rouge's Treasure Sense (tools/treasure_sense.py): the nearest treasure (px across + down): temp0\n"
            f"// true if any, temp1 / temp2 its place (px), temp3 how far. Uses temp0-temp5 and arrayPos0 (not temp7)\n"
            f"public function NoSwap_TreasureFind{i}\n\ttemp0 = false\n" + ring
            + ("\tif temp0 == false\n" if ring else "")
            + ("\t" if ring else "") + "\tforeach (TypeName[Monitor], arrayPos0, ALL_ENTITIES) // unopened item monitors\n"
            + near_v4(3 if ring else 2) + ("\t" if ring else "") + "\tnext\n" + ("\tend if\n" if ring else "")
            + "end function\n\n\n")


def v4_draw_function(i):
    """The marker (the HUD-layer pass, screen px): on the treasure when it's on screen, else at the screen's edge on the
    line from her to it; lit for half of its blink period. Frame 0: the ring (v4_patch's ObjectStartup). Not temp7."""
    m = MARGIN
    return f"""// [NoSwap] Rouge's Treasure Sense marker (tools/treasure_sense.py), in the HUD-layer pass: the game's ring at the
// nearest treasure, or at the screen's edge toward it, blinking faster the nearer it is. Leaves temp7 alone
public function NoSwap_TreasureDraw{i}
	CallFunction(NoSwap_TreasureFind{i})
	if temp0 == true
		temp4 = temp3 // the blink's half period: {HALF_NEAR} (within {NEAR} px) to {HALF_FAR} ({FAR} px and more)
		temp4 -= {NEAR}
		if temp4 < 0
			temp4 = 0
		end if
		temp4 *= {HALF_FAR - HALF_NEAR}
		temp4 /= {FAR - NEAR}
		temp4 += {HALF_NEAR}
		if temp4 > {HALF_FAR}
			temp4 = {HALF_FAR}
		end if
		temp5 = temp4
		temp5 <<= 1
		temp6 = {VALUE}
		temp6 %= temp5
		if temp6 < temp4 // lit
			temp1 -= screen.xoffset // its place on screen
			temp2 -= screen.yoffset
			temp0 = false // off screen (past the margin)?
			if temp1 < {m}
				temp0 = true
			end if
			if temp2 < {m}
				temp0 = true
			end if
			temp3 = screen.xsize
			temp3 -= {m}
			if temp1 > temp3
				temp0 = true
			end if
			temp3 = screen.ysize
			temp3 -= {m}
			if temp2 > temp3
				temp0 = true
			end if
			if temp0 == true // the screen's edge, on the line from her to it
				temp3 = player.xpos // her place on screen
				temp3 >>= 16
				temp3 -= screen.xoffset
				temp4 = player.ypos
				temp4 >>= 16
				temp4 -= screen.yoffset
				temp1 -= temp3
				temp2 -= temp4
				temp5 = 256 // how far along the line (in 256ths) the edge is
				if temp1 > 0
					temp6 = screen.xsize
					temp6 -= {m}
					temp6 -= temp3
					temp6 <<= 8
					temp6 /= temp1
					if temp6 < temp5
						temp5 = temp6
					end if
				end if
				if temp1 < 0
					temp6 = {m}
					temp6 -= temp3
					temp6 <<= 8
					temp6 /= temp1
					if temp6 < temp5
						temp5 = temp6
					end if
				end if
				if temp2 > 0
					temp6 = screen.ysize
					temp6 -= {m}
					temp6 -= temp4
					temp6 <<= 8
					temp6 /= temp2
					if temp6 < temp5
						temp5 = temp6
					end if
				end if
				if temp2 < 0
					temp6 = {m}
					temp6 -= temp4
					temp6 <<= 8
					temp6 /= temp2
					if temp6 < temp5
						temp5 = temp6
					end if
				end if
				if temp5 < 0
					temp5 = 0
				end if
				temp1 *= temp5
				temp1 /= 256
				temp1 += temp3
				temp2 *= temp5
				temp2 /= 256
				temp2 += temp4
				if temp1 < {m}
					temp1 = {m}
				end if
				if temp2 < {m}
					temp2 = {m}
				end if
				temp3 = screen.xsize
				temp3 -= {m}
				if temp1 > temp3
					temp1 = temp3
				end if
				temp3 = screen.ysize
				temp3 -= {m}
				if temp2 > temp3
					temp2 = temp3
				end if
			end if
			DrawSpriteScreenXY(0, temp1, temp2)
		end if
	end if
end function


"""


def v4_ring_function():
    """NoSwap_RingMonitor, in every player script (Global/BrokenMonitor.txt calls it: build_packages.py checks each
    variant defines it): a jewel thief's 10 more rings."""
    body = "".join(f"\tif stage.playerListPos == {ab().ALIAS_OF[i]} // jewel_thief: 10 more\n\t\tplayer[0].rings += 10\n"
                   "\tend if\n" for i in thieves())
    return ("// [NoSwap] Global/BrokenMonitor.txt's 10-ring item calls this right after its own +10 (its cap at 999 and its\n"
            "// extra life follow): a jewel_thief extra (Rouge) gets 10 more (tools/treasure_sense.py). No temps\n"
            "public function NoSwap_RingMonitor\n" + body + "end function\n\n\n")


def v4_patch(t, game):
    """The S1/S2 player script (after every other module's patches): NoSwap_RingMonitor (always); for each Treasure Sense
    extra its values, its functions (before NoSwap_AfterUpdate, which calls them), the marker's frame (ObjectStartup) and
    the HUD-layer pass (ObjectDraw)."""
    import monitor_swap
    anchor = "public function Player_HandleAmyHitbox\n"
    if t.count(anchor) != 1:
        sys.exit("treasure_sense: Player_HandleAmyHitbox isn't there once")
    t = t.replace(anchor, v4_ring_function() + anchor)
    if not ids():
        return t
    anchor = "public value Player_superState"
    if t.count(anchor) != 1:
        sys.exit("treasure_sense: Player_superState isn't there once")
    t = t.replace(anchor, V4_VALUES + "\n" + anchor)
    for i in ids():
        a = ab().ALIAS_OF[i]
        anchor = "// Runs at the end of every update, after the player has moved\npublic function NoSwap_AfterUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("treasure_sense: NoSwap_AfterUpdate isn't there once")
        t = t.replace(anchor, v4_find_function(i, game) + v4_draw_function(i) + anchor)
        if t.count("event ObjectStartup\n") != 1:
            sys.exit("treasure_sense: expected one ObjectStartup")
        x, y, w, h, sx, sy = RING
        t = t.replace("event ObjectStartup\n", "event ObjectStartup\n"
                      f"\tif stage.playerListPos == {a} // [NoSwap] treasure_sense (tools/treasure_sense.py): its marker, "
                      "the game's own ring (Ring.txt's frame 0)\n"
                      '\t\tLoadSpriteSheet("Global/Items.gif")\n'
                      f"\t\tSpriteFrame({x}, {y}, {w}, {h}, {sx}, {sy}) // 0: the ring\n\tend if\n", 1)
        t = monitor_swap.v4_hud_pass(t, a, ICON, f"CallFunction(NoSwap_TreasureDraw{i})",
                                     "treasure_sense (tools/treasure_sense.py): her HUD-layer listing draws the marker, "
                                     "not her", "treasure_sense")
    return t


def v4_broken_monitor(t):
    """Global/BrokenMonitor.txt (S1 player[0], S2 player[currentPlayer]): the ring item's +10, then NoSwap_RingMonitor."""
    out, n = [], 0
    lines = t.split("\n")
    for k, line in enumerate(lines):
        out.append(line)
        if line.strip() in ("player[0].rings += 10", "player[currentPlayer].rings += 10") \
                and "case MONITOR_RINGS" in lines[k - 1]:
            ind = line[:len(line) - len(line.lstrip("\t"))]
            out.append(f"{ind}CallFunction(NoSwap_RingMonitor) // [NoSwap] jewel_thief: 10 more for Rouge "
                       "(tools/treasure_sense.py; the cap and extra life below)")
            n += 1
    if n != 1:
        sys.exit(f"treasure_sense: BrokenMonitor.txt: {n} ring items found (expected 1)")
    return "\n".join(out)


# ---------------------------------------------------------------- Sonic CD
def cd_state():
    return f"Object[{CD_SLOT}].Value0"


def cd_icon():
    return f"Object[{CD_SLOT}].Value1"


def cd_after(i):
    """The CD NoSwap_AfterUpdate block (v4_after's): Y from the DLL (game.callbackParam3 == 1; the Screw Kick's block after
    this one re-arms it)."""
    import monitor_swap
    c = check(i)
    p, s, v = c["sense_pause"], c["sense_show"], cd_state()
    listing = "\n".join(monitor_swap.cd_hud_listing(cd_icon(), "treasure_sense (tools/treasure_sense.py): the marker, "
                                                               "drawn in the HUD's layer (ObjectDraw)"))
    return f"""// Treasure Sense (tools/treasure_sense.py): Y on the ground
if {v} < 0 // the cooldown
	{v}++
end if
TempValue0 = false // on the ground, free: the plain ground state, not hurt, not held
if Player.Gravity == GRAVITY_GROUND
	CheckEqual(Player.State, Player_State_Ground)
	TempValue0 = CheckResult
end if
if Player.Animation == ANI_HURT
	TempValue0 = false
end if
if Player.ControlMode == CONTROLMODE_NONE
	TempValue0 = false
end if
if {v} == 0
	if game.callbackParam3 == 1 // Y, from the DLL
		if TempValue0 == true
			{v} = 1
		end if
	end if
end if
if {v} > 0
	if {v} <= {p} // the pause: listening
		if TempValue0 == false // a jump, a hit, an object: over
			{v} = 0
		else
			Player.Speed = 0
			Player.XVelocity = 0
			Player.Animation = ANI_LOOKINGUP
			Player.PrevAnimation = ANI_LOOKINGUP
			Player.Frame = 0
			Player.AnimationTimer = 0
			{v}++
			if {v} > {p}
				CallFunction(NoSwap_TreasureFind{i})
				if TempValue0 == false // no signal
					PlaySfx({c['sense_sfx_cd']}, false)
					{v} = -{c['sense_cooldown']}
				end if
			end if
		end if
	else
		{v}++
		if {v} > {p + s}
			{v} = -{c['sense_cooldown']}
		end if
	end if
end if
{cd_icon()} = 0
if {v} > {p} // the marker: the HUD-layer pass (not while she's held)
	if Player.ControlMode != CONTROLMODE_NONE
{tab(listing, 2)}	end if
end if
"""


def to_v3(text):
    """v4 code of this module in CD's dialect (TempValue*, Object[ArrayPos0].*, Player.*, Screen.*; no loops here)."""
    import re
    rep = [("object[arrayPos0].xpos", "Object[ArrayPos0].XPos"), ("object[arrayPos0].ypos", "Object[ArrayPos0].YPos"),
           ("object[arrayPos0].ixpos", "Object[ArrayPos0].iXPos"), ("object[arrayPos0].iypos", "Object[ArrayPos0].iYPos"),
           ("player.xpos", "Player.XPos"), ("player.ypos", "Player.YPos"), ("screen.xoffset", "Screen.XOffset"), ("screen.yoffset", "Screen.YOffset"),
           ("screen.xsize", "Screen.XSize"), ("screen.ysize", "Screen.YSize"), (VALUE, cd_state()),
           ("public function", "function")]
    for a, b in rep:
        text = text.replace(a, b)
    text = re.sub(r"\btemp(\d)\b", r"TempValue\1", text)
    for bad in ("player.", "temp", "object[", "screen.", "foreach", "arrayPos0", "public "):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"treasure_sense: the CD code still has {bad!r}")
    return text


def cd_find_function(i):
    """v4_find_function in CD: the big ring (Special Ring, State 0: SPECIALRING_IDLE) first, then the monitors; the
    stage's entities are slots 32-1055 (as the game's own loops: AttractMode.txt)."""
    def loop(name, state_test):
        inner = to_v3(near_v4(0))
        if state_test:
            inner = "if Object[ArrayPos0].State == 0 // (SPECIALRING_IDLE: not entered)\n" + tab(inner, 1) + "end if\n"
        return ("ArrayPos0 = 32\nwhile ArrayPos0 < 1056\n"
                f"\tif Object[ArrayPos0].Type == TypeName[{name}]\n" + tab(inner, 2) + "\tend if\n\tArrayPos0++\nloop\n")
    body = ("TempValue0 = false\n" + "// the big ring first\n" + loop("Special Ring", True)
            + "if TempValue0 == false // then unopened item monitors\n" + tab(loop("Monitor", False), 1) + "end if\n")
    return (f"// [NoSwap] Rouge's Treasure Sense (tools/treasure_sense.py): the nearest treasure (px across + down):\n"
            f"// TempValue0 true if any, TempValue1 / 2 its place (px), TempValue3 how far. Uses TempValue0-5, ArrayPos0\n"
            f"function NoSwap_TreasureFind{i}\n" + tab(body, 1) + "end function\n\n\n")


def cd_functions(i):
    return cd_find_function(i) + to_v3(v4_draw_function(i))


def cd_ring_function():
    import build_soniccd
    body = "".join(f"\tif Stage.PlayerListPos == {ab().ALIAS_OF[i]} // jewel_thief: 10 more\n\t\tPlayer.Value0 += 10 // "
                   "(Player.Rings)\n\tend if\n" for i in thieves())
    return ("// [NoSwap] Global/BrokenMonitor.txt's 10-ring item calls this right after its own +10 (its cap at 999 and its\n"
            "// extra life follow): a jewel_thief extra (Rouge) gets 10 more (tools/treasure_sense.py)\n"
            "function NoSwap_RingMonitor\n" + (body or f"\t{build_soniccd.NO_OP}\n") + "end function\n\n\n")


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): NoSwap_RingMonitor (always); for each Treasure Sense
    extra its functions, its NoSwap_AfterUpdate block (first: it reads Y before the Screw Kick's block re-arms it), the
    marker's frame (ObjectStartup) and the HUD-layer pass (ObjectDraw)."""
    import monitor_swap
    fns = cd_ring_function() + "".join(cd_functions(i) for i in ids())
    import re
    decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
    for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                        ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
        if t.count(anchor) != 1:
            sys.exit(f"treasure_sense: CD anchor {anchor.strip()!r} isn't there once")
        t = t.replace(anchor, new)
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("treasure_sense: CD's NoSwap_AfterUpdate isn't there once")
        t = t.replace(head, head + f"\tif Stage.PlayerListPos == {a} // [NoSwap] Rouge's Treasure Sense (tools/treasure_sense.py)\n"
                      + tab(cd_after(i), 2) + "\tend if\n")
        if t.count("sub ObjectStartup\n") != 1:
            sys.exit("treasure_sense: expected one CD ObjectStartup")
        x, y, w, h, sx, sy = RING
        t = t.replace("sub ObjectStartup\n", "sub ObjectStartup\n"
                      f"\tif Stage.PlayerListPos == {a} // [NoSwap] treasure_sense (tools/treasure_sense.py): its marker, "
                      "the game's own ring (Ring.txt's frame 0)\n"
                      '\t\tLoadSpriteSheet("Global/Items.gif")\n'
                      f"\t\tSpriteFrame({x}, {y}, {w}, {h}, {sx}, {sy}) // 0: the ring\n\tend if\n", 1)
        t = monitor_swap.cd_hud_pass(t, a, cd_icon(), f"CallFunction(NoSwap_TreasureDraw{i})",
                                     "treasure_sense (tools/treasure_sense.py): her HUD-layer listing draws the marker, "
                                     "not her", "treasure_sense")
    return t


def cd_broken_monitor(t):
    """CD's Global/BrokenMonitor.txt: the ring item's +10, then NoSwap_RingMonitor."""
    out, n = [], 0
    lines = t.split("\n")
    for k, line in enumerate(lines):
        out.append(line)
        if line.strip() == "Player.Rings += 10" and "case MONITOR_RINGS" in lines[k - 1]:
            ind = line[:len(line) - len(line.lstrip("\t"))]
            out.append(f"{ind}CallFunction(NoSwap_RingMonitor) // [NoSwap] jewel_thief: 10 more for Rouge "
                       "(tools/treasure_sense.py; the cap and extra life below)")
            n += 1
    if n != 1:
        sys.exit(f"treasure_sense: CD BrokenMonitor.txt: {n} ring items found (expected 1)")
    return "\n".join(out)
