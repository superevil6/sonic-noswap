"""NiGHTS' free flight (abilities.py "free_flight"), for Sonic 1/2 (Retro Engine v4 player script; abilities.py calls in
here) and Sonic CD (build_soniccd.py calls cd_patch). The S3&K DLL's is native/src/NightsFlight.h, Mania's
native/mania/src/ManiaNights.h: the same rules and numbers. Modelled on Ecco's free swim (tools/free_swim.py,
native/src/EccoSwim.h), moved out of the water and into the air.

The design (approved 2026-10-01):
- A jump press in mid-air (any plain air state, from a jump, a spring or a fall; not the frame he left the ground), or
  Y in mid-air, starts the flight while the flight meter has anything left. In flight the d-pad steers: a heading
  (HEADING units a turn, 0 right, counterclockwise) turns toward the d-pad's direction by fly_turn degrees a frame while
  the speed builds by fly_accel up to fly_speed; nothing held, it drains by fly_drag (he hangs in the air). His velocity
  is the heading times the speed, set after the air state's own gravity and air control (S1/S2: NoSwap_AirAbilities;
  CD: the end of Player_HandleAirMovement), so neither touches it. Another jump press stops the flight (he falls as
  usual and may fly again with what's left); landing, a hit, an object holding him or any state but the plain air ones
  ends it.
- The flight meter (fly_meter frames of flight): drains fly_drain a frame while he flies (not underwater), refills
  fly_refill a frame on the ground, and every ring he gets adds fly_ring. Empty, the flight ends and he floats down
  (his fall held to fly_sink at most) until he lands. It's drawn at the top middle of the screen (the HUD's layer:
  tools/monitor_swap.py's HUD-layer pass, as John's sub-weapon icon) while it isn't full or he flies: a dark box with a
  yellow bar (red when under a quarter).
- Drawn from slot 42 ("Flight", not an attack): its frames 0-7 are the paraloop's 8 headings (0 right, then
  counterclockwise in 45-degree steps), his facing mirroring them: facing left he shows heading d's mirror, frame
  (4 - d) & 7 (so he's never upside down flying along); he faces the way he's going across. Underwater, flying level
  (heading 0 / 4), its frames 8.. are the swim cycle (fly_swim_frames of them, faster the faster he goes).
- Y in flight: the Drill Dash, drill_frames frames at drill_speed along the heading, an attack (slot 41, "Drill":
  its 4 blur frames, 2 game frames each), untouchable meanwhile (the post-hit timer kept up without its flicker), then
  drill_cooldown frames' rest; it costs drill_cost of the meter.
- The Paraloop: while he flies, every loop_every frames his position is a sample (the last loop_points kept). When he
  comes back within loop_close px of a sample at least LOOP_AGE samples old (his path closes on itself: a crossing or a
  near miss), and the samples since make a loop at least loop_min px wide and tall, everything inside that polygon (an
  even-odd test over its edges) is hit, through the game's own hit code:
    Sonic 1/2  an invisible Tails Object in the shots' group (tools/shots_v4.py: the enemies' shot loops) at each
               entity inside, looking like a jumping player with a small box (hit_update_body / hit_looks: in the
               shots' NoSwap_ShotUpdate / NoSwap_ShotLooks);
    Sonic CD   the slot numbers of the entities inside go in a list that NoSwap_ShotTouch (every badnik, boss and
               monitor asks it: tools/shots_v3.py) answers with a shot's hit for loop_hit frames.
  The samples restart after a loop. A Ring Sparkle (the game's own) is left at each sample as he flies (the trail) and
  at each corner of a closed loop.

State (S1/S2 / CD):
  player.noswapAbility / Object[5].Value1   the mode: 0 none, 1 flying, 2 floating down (empty), 3 stopped (falling)
  NoSwap_flyHeading / Object[5].Value4      the heading (0..HEADING-1)
  NoSwap_flySpeed / Object[5].Value5        the speed (16.16)
  NoSwap_flyMeter / Object[5].Value7        the meter (frames)
  NoSwap_flyDrill / Object[5].Value6        the drill and its rest (drill_frames + drill_cooldown at the press, counting
                                            down; drilling while above drill_cooldown)
  (table) / Object[5].Value2                the swim cycle's timer (256ths of a game frame)
  NoSwap_flyFrame / Object[5].Value0        the drawn frame (slot 41 or 42), read while the mode is 1
  NoSwap_flyIcon / Object[28].Value4        the HUD-layer listing (tools/monitor_swap.py v4_hud_listing)
  the rest (air frames, the rings seen, the loop's sample timer and count, its match and box, the samples, CD's kill
  list) in a table (S1/S2: NoSwap_FlyData<i>) or reserved entity slots (CD: CD_SLOTS; docs/soniccd_map.md section 4).
(S1/S2's NoSwap_fly* values are packed into Player_unusedValue1-7: noswap_common.PACKED_VALUES.)
"""
import re
import sys

HEADING = 8192  # heading units a full turn (Sin / Cos take HEADING >> 4 = 512)
FLY, FLOAT, FALL = 1, 2, 3
WATER_GRAVITY = 0x1000  # the player's gravityStrength underwater (S1/S2 and CD)
LOOP_AGE = 4  # a sample the path closes on is at least this many samples old
DRILL_FRAMES = 4  # the drill's frames in slot 41 (2 game frames each)
METER_W, METER_H, METER_TOP, METER_ALPHA = 64, 4, 10, 160  # the meter's bar (px), the box 2 px round it
V4 = {"drill": 41, "fly": 42, "blink": 3, "y": "if keyPress[1].buttonY != false"}
CD = {"drill": 45, "fly": 47, "blink": 2, "y": "if game.callbackParam3 == 1 // Y, from the DLL"}
V4_VALUES = ["NoSwap_flyHeading", "NoSwap_flySpeed", "NoSwap_flyMeter", "NoSwap_flyDrill", "NoSwap_flyFrame",
             "NoSwap_flyIcon"]  # (the swim cycle's timer is in the table: "time")
CD_NAMES = [("player.noswapAbility", "Object[5].Value1"), ("NoSwap_flyHeading", "Object[5].Value4"),
            ("NoSwap_flySpeed", "Object[5].Value5"), ("NoSwap_flyMeter", "Object[5].Value7"),
            ("NoSwap_flyDrill", "Object[5].Value6"),
            ("NoSwap_flyFrame", "Object[5].Value0"), ("NoSwap_flyIcon", "Object[28].Value4"),
            ("player.rings", "Player.Rings"), ("player.gravityStrength", "Player.GravityStrength"),
            ("player.angle", "Player.Angle"), ("player.collisionMode", "Player.CollisionMode"),
            ("stage.playerListPos", "Stage.PlayerListPos"), ("player.visible", "Player.Visible"),
            ("screen.xcenter", "Screen.CenterX"), ("arrayPos0", "ArrayPos0"), ("arrayPos1", "ArrayPos1")]
# Sonic CD's storage (reserved entity slots nothing else touches: docs/soniccd_map.md section 4; 14 left for others)
CD_SLOTS = (16, 17, 18, 22, 27, 28)
CD_KILL = 27  # Object[27].Value0-6 the kill list (entity slots, -1 none), Value7 its frames left
KILL_MAX = 7
SPAWN_MAX = 24  # Sonic 1/2: hit objects at most per loop
TEMP_START = 1056  # the first temporary entity slot (v3 / v4): scene entities are 32..TEMP_START-1


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("free_flight")


def cfg(i):
    """The extra's numbers, with their defaults (the S3&K DLL's: gen_s3k_header.py)."""
    c = ab().ABILITIES[i]
    d = dict(fly_speed=0x50000, fly_accel=0x3000, fly_drag=0x1800, fly_turn=8, fly_meter=360, fly_drain=1,
             fly_refill=6, fly_ring=60, fly_sink=0x10000, fly_swim_frames=10, fly_swim_ticks=4, drill_frames=20,
             drill_speed=0xA0000, drill_cooldown=20, drill_cost=30, loop_points=12, loop_every=5, loop_close=24,
             loop_min=40, loop_hit=3, drill_sfx="Release", drill_sfx_cd="SFX_G_RELEASE")
    out = {k: c.get(k, v) for k, v in d.items()}
    taken = [a for a in c["abilities"] if a not in ("free_flight", "no_breathing", "physics")]
    if taken or c.get("shot") or c.get("melee_reach"):
        sys.exit(f"free_flight: extra {i}: the flight uses noswapAbility, NoSwap_fly* and slots 41-42 alone ({taken})")
    if not 6 <= out["loop_points"] <= 12:
        sys.exit(f"free_flight: extra {i}: loop_points is 6 to 12 (Sonic CD's storage)")
    return out


# ---------------------------------------------------------------- storage (LOAD / STORE pseudo-lines)
def keys(c):
    n = c["loop_points"]
    return ["time", "air", "rings", "ltimer", "lcount", "m", "mx", "my", "bx0", "bx1", "by0", "by1", "spawned"] \
        + [f"X{k}" for k in range(n)] + [f"Y{k}" for k in range(n)]


def cd_place(c):
    """key -> "Object[s].Valuek" for Sonic CD."""
    n = c["loop_points"]
    free = [(s, v) for s in (16, 17, 18, 22) for v in range(8)]
    out = {}
    for k in range(n):
        out[f"X{k}"] = free.pop(0)
    for k in range(n):
        out[f"Y{k}"] = free.pop(0)
    for name in ("bx0", "bx1", "by0", "by1", "spawned"):
        out[name] = free.pop(0)
    for v, name in enumerate(("air", "rings", "ltimer", "lcount")):
        out[name] = (28, v)
    out["time"] = (5, 2)
    for v, name in zip((5, 6, 7), ("m", "mx", "my")):
        out[name] = (28, v)
    return {k: f"Object[{s}].Value{v}" for k, (s, v) in out.items()}


def resolve(text, i, eng):
    """@LOAD var key / @STORE key var -> the engine's lines."""
    c = cfg(i)
    if eng is CD:
        place = cd_place(c)
    else:
        index = {k: n for n, k in enumerate(keys(c))}

    def one(m):
        ind, op, a, b, rest = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if op == "LOAD":
            line = f"{a} = {place[b]}" if eng is CD else f"GetTableValue({a}, {index[b]}, NoSwap_FlyData{i})"
        else:
            line = f"{place[a]} = {b}" if eng is CD else f"SetTableValue({b}, {index[a]}, NoSwap_FlyData{i})"
        return ind + line + rest
    text = re.sub(r"^(\t*)@(LOAD|STORE) (\S+) (\S+)((?: //.*)?)$", one, text, flags=re.M)
    if "@LOAD" in text or "@STORE" in text:
        sys.exit("free_flight: a storage line wasn't resolved")
    return text


def ind(text, depth):
    t = "\t" * depth
    return "".join(t + l + "\n" if l.strip() else "\n" for l in text.rstrip("\n").split("\n"))


def sfx_line(i, eng):
    c = cfg(i)
    return (f"PlaySfx(SfxName[{c['drill_sfx']}], false)" if eng is V4 else f"PlaySfx({c['drill_sfx_cd']}, false)")


def reset_anim():
    """Out of the flight: his animation back to the game's own (his floating frames, the walk) if it's still ours."""
    return ("if player.animation == ANI_NOSWAP_ATTACK\n\tplayer.animation = ANI_WALKING\nend if\n"
            "if player.animation == ANI_NOSWAP_HOVER\n\tplayer.animation = ANI_WALKING\nend if\n")


def sparkle(x, y):
    """A Ring Sparkle (the game's own, a global object in all three) at (x, y) px."""
    return (f"temp6 = {x}\ntemp6 <<= 16\ntemp7 = {y}\ntemp7 <<= 16\n"
            "CreateTempObject(TypeName[Ring Sparkle], 0, temp6, temp7)\n")


# ---------------------------------------------------------------- the update (after the player has moved)
def loop_code(i, eng):
    """In flight, every loop_every frames: a sample (the oldest dropped), a sparkle, and the closing test (the loop)."""
    c = cfg(i)
    n = c["loop_points"]
    out = ["@LOAD temp0 ltimer", "temp0++", f"if temp0 >= {c['loop_every']}", "\ttemp0 = 0", "end if",
           "@STORE ltimer temp0", "if temp0 == 0 // a sample (tools/free_flight.py: the Paraloop)"]
    body = []
    for k in range(n - 1):  # (the oldest dropped, the others one along)
        body += [f"@LOAD temp1 X{k + 1}", f"@STORE X{k} temp1", f"@LOAD temp1 Y{k + 1}", f"@STORE Y{k} temp1"]
    body += ["temp0 = player.ixpos", "temp1 = player.iypos", f"@STORE X{n - 1} temp0", f"@STORE Y{n - 1} temp1",
             "@LOAD temp7 lcount", f"if temp7 < {n}", "\ttemp7++", "end if", "@STORE lcount temp7"]
    body += sparkle("temp0", "temp1").rstrip("\n").split("\n")
    body += ["temp6 = player.ixpos", "temp7 = player.iypos", "@LOAD temp5 lcount",
             "arrayPos1 = -1 // the oldest sample he's come back to"]
    for k in range(n - LOOP_AGE):
        body += [f"if arrayPos1 < 0", f"\tif temp5 >= {n - k} // (sample {k} taken)",
                 f"\t\t@LOAD temp2 X{k}", "\t\ttemp2 -= temp6", "\t\tif temp2 < 0", "\t\t\tFlipSign(temp2)", "\t\tend if",
                 f"\t\tif temp2 < {c['loop_close']}", f"\t\t\t@LOAD temp3 Y{k}", "\t\t\ttemp3 -= temp7",
                 "\t\t\tif temp3 < 0", "\t\t\t\tFlipSign(temp3)", "\t\t\tend if", f"\t\t\tif temp3 < {c['loop_close']}",
                 f"\t\t\t\tarrayPos1 = {k}", f"\t\t\t\t@LOAD temp2 X{k}", "\t\t\t\t@STORE mx temp2",
                 f"\t\t\t\t@LOAD temp2 Y{k}", "\t\t\t\t@STORE my temp2", "\t\t\tend if", "\t\tend if", "\tend if",
                 "end if"]
    # its box (the samples from the match on)
    box = [f"@LOAD temp0 X{n - 1}", "temp1 = temp0", f"@LOAD temp2 Y{n - 1}", "temp3 = temp2"]
    for k in range(n - 1):
        box += [f"if arrayPos1 <= {k}", f"\t@LOAD temp4 X{k}", "\tif temp4 < temp0", "\t\ttemp0 = temp4", "\tend if",
                "\tif temp4 > temp1", "\t\ttemp1 = temp4", "\tend if", f"\t@LOAD temp4 Y{k}", "\tif temp4 < temp2",
                "\t\ttemp2 = temp4", "\tend if", "\tif temp4 > temp3", "\t\ttemp3 = temp4", "\tend if", "end if"]
    box += ["@STORE bx0 temp0", "@STORE bx1 temp1", "@STORE by0 temp2", "@STORE by1 temp3", "temp1 -= temp0",
            "temp3 -= temp2", "temp4 = false", f"if temp1 >= {c['loop_min']}", f"\tif temp3 >= {c['loop_min']}",
            "\t\ttemp4 = true", "\tend if", "end if"]
    hit = ["temp0 = 0 // the loop (tools/free_flight.py): the samples start over", "@STORE lcount temp0"]
    for k in range(n):  # a sparkle at each of its corners
        hit += [f"if arrayPos1 <= {k}", f"\t@LOAD temp0 X{k}", f"\t@LOAD temp1 Y{k}"] \
            + ["\t" + l for l in sparkle("temp0", "temp1").rstrip("\n").split("\n")] + ["end if"]
    hit += kill_code(i, eng).rstrip("\n").split("\n")
    body += ["if arrayPos1 >= 0"] + ["\t" + l for l in box] + ["\tif temp4 == true"] + ["\t\t" + l for l in hit] \
        + ["\tend if", "end if"]
    out += ["\t" + l for l in body] + ["end if"]
    return "\n".join(out) + "\n"


def inside_code(c):
    """temp2 = 1 when (temp0, temp1) px is inside the loop: the even-odd test over its edges (the samples from arrayPos1
    on, and back to the matched one: mx, my). Uses temp2-temp7."""
    n = c["loop_points"]
    out = ["temp2 = 0"]

    def edge(a_lines, b_lines):
        return (b_lines + a_lines + [
            "temp7 = 0", "if temp6 > temp1", "\ttemp7++", "end if", "if temp4 > temp1", "\ttemp7++", "end if",
            "if temp7 == 1 // the edge crosses his row: where", "\ttemp7 = temp1", "\ttemp7 -= temp6",
            "\ttemp3 -= temp5", "\ttemp7 *= temp3", "\ttemp4 -= temp6", "\ttemp7 /= temp4", "\ttemp7 += temp5",
            "\tif temp0 < temp7", "\t\ttemp3 = 1", "\t\ttemp3 -= temp2", "\t\ttemp2 = temp3", "\tend if", "end if"])
    for b in range(1, n):
        out += [f"if arrayPos1 <= {b - 1}"] + ["\t" + l for l in edge(
            [f"@LOAD temp3 X{b - 1}", f"@LOAD temp4 Y{b - 1}"], [f"@LOAD temp5 X{b}", f"@LOAD temp6 Y{b}"])] + ["end if"]
    out += edge(["@LOAD temp3 mx", "@LOAD temp4 my"], [f"@LOAD temp5 X{n - 1}", f"@LOAD temp6 Y{n - 1}"])
    return out


def kill_code(i, eng):
    """Everything inside the loop is hit: each scene entity (32..TEMP_START-1) in its box and inside it."""
    c = cfg(i)
    if eng is V4:
        found = [f"@LOAD temp3 spawned", f"if temp3 < {SPAWN_MAX}", "\ttemp3++", "\t@STORE spawned temp3",
                 "\ttemp4 = object[arrayPos0].xpos", "\ttemp5 = object[arrayPos0].ypos",
                 "\tCreateTempObject(TypeName[Tails Object], 0, temp4, temp5)",
                 "\tarrayPos2 = object[tempObjectPos].entityPos",
                 "\tif object[arrayPos2].type == TypeName[Tails Object] // (made: an invisible hit, tools/free_flight.py)"]
        found += ["\t\t" + l for l in spawn_lines("object[arrayPos2]")] + ["\tend if", "end if"]
        pre = ["temp0 = 0", "@STORE spawned temp0"]
    else:
        found = [f"@LOAD temp3 spawned", f"if temp3 < {KILL_MAX}"]
        for k in range(KILL_MAX):
            found += [f"\tif temp3 == {k}", f"\t\tObject[{CD_KILL}].Value{k} = arrayPos0", "\tend if"]
        found += ["\ttemp3++", "\t@STORE spawned temp3", "end if"]
        pre = ["temp0 = 0", "@STORE spawned temp0"] + [f"Object[{CD_KILL}].Value{k} = -1" for k in range(KILL_MAX)] \
            + [f"Object[{CD_KILL}].Value7 = {c['loop_hit']} // the list's frames (NoSwap_ShotTouch)"]
    test = inside_code(c)
    loop = pre + ["arrayPos0 = 32", f"while arrayPos0 < {TEMP_START}",
                  "\tif object[arrayPos0].type != TypeName[Blank Object]",
                  "\t\ttemp0 = object[arrayPos0].ixpos", "\t\ttemp1 = object[arrayPos0].iypos",
                  "\t\t@LOAD temp2 bx0", "\t\tif temp0 >= temp2", "\t\t\t@LOAD temp2 bx1", "\t\t\tif temp0 <= temp2",
                  "\t\t\t\t@LOAD temp2 by0", "\t\t\t\tif temp1 >= temp2", "\t\t\t\t\t@LOAD temp2 by1",
                  "\t\t\t\t\tif temp1 <= temp2"] \
        + ["\t\t\t\t\t\t" + l for l in test] + ["\t\t\t\t\t\tif temp2 == 1"] \
        + ["\t\t\t\t\t\t\t" + l for l in found] \
        + ["\t\t\t\t\t\tend if", "\t\t\t\t\tend if", "\t\t\t\tend if", "\t\t\tend if", "\t\tend if", "\tend if",
           "\tarrayPos0++", "loop"]
    return "\n".join(loop) + "\n"


def spawn_lines(o):
    """A Sonic 1/2 paraloop hit (an invisible Tails Object in the shots' group), as the enemies' shot loops see it: a
    jumping player 1 with a 16 px box round it (tools/shots_v4.py)."""
    import shots_v4
    return [f"{o}.state = {shots_v4.LIVE}", f"{o}.priority = PRIORITY_ACTIVE", f"{o}.groupID = {shots_v4.GROUP}",
            f"{o}.value0 = 0", f"{o}.value36 = -1 // (nothing drawn)"] + [f"{o}.{l}" for l in hit_looks_fields()]


def hit_looks_fields():
    return ["animation = ANI_JUMPING", "gravity = GRAVITY_GROUND", "value16 = false // isSidekick",
            "value19 = object[0].value19 // badnikBonus", "value38 = -16 // hitbox top, bottom, left, right",
            "value39 = 16", "value40 = -16", "value41 = 16"]


def hit_looks(i):
    """NoSwap_ShotLooks for the paraloop's hits (Sonic 1/2; abilities.shot_update_function)."""
    return "".join(f"object.{l}\n" for l in hit_looks_fields())


def hit_update_body(i):
    """NoSwap_ShotUpdate for the paraloop's hits (Sonic 1/2): a few frames in the shots' group, then gone; a hit (spent:
    not LIVE) ends it at once."""
    import shots_v4
    c = cfg(i)
    return f"""object.value0++ // a paraloop hit's age (tools/free_flight.py)
if object.state != {shots_v4.LIVE}
	object.type = TypeName[Blank Object] // (spent: it hit)
else
	if object.value0 > {c['loop_hit'] + 2}
		object.type = TypeName[Blank Object]
	else
		object.groupID = {shots_v4.GROUP}
		object.value36 = -1
		CallFunction(NoSwap_ShotLooks)
	end if
end if
"""


def update_function(i, eng):
    """NoSwap_FreeFlight<i>: every frame after the player has moved (NoSwap_AfterUpdate)."""
    c = cfg(i)
    turn = round(c["fly_turn"] * HEADING / 360) if c["fly_turn"] > 0 else HEADING // 2
    cool = c["drill_cooldown"]
    swim = max(1, c["fly_swim_frames"])
    ticks = max(1, c["fly_swim_ticks"])
    rearm = "".join(f"{l}\n" for l in __import__("build_soniccd").Y_REARM) if eng is CD else ""
    full = c["fly_meter"]
    body = f"""if NoSwap_flyDrill > 0
	NoSwap_flyDrill--
end if
temp2 = false // Y pressed
{eng['y']}
	temp2 = true
end if
{rearm}@LOAD temp0 rings // every ring he gets tops the meter up
if player.rings > temp0
	temp1 = player.rings
	temp1 -= temp0
	temp1 *= {c['fly_ring']}
	NoSwap_flyMeter += temp1
	if NoSwap_flyMeter > {full}
		NoSwap_flyMeter = {full}
	end if
end if
temp0 = player.rings
@STORE rings temp0
temp1 = false // the plain air states
CheckEqual(player.state, Player_State_Air)
temp1 |= checkResult
CheckEqual(player.state, Player_State_Air_NoDropDash)
temp1 |= checkResult
CheckEqual(player.state, Player_State_RollJump)
temp1 |= checkResult
if player.animation == ANI_HURT
	temp1 = false
end if
temp3 = false // underwater
if player.gravityStrength == {WATER_GRAVITY:#x}
	temp3 = true
end if
if player.gravity == GRAVITY_GROUND // on the ground: no flight, the meter fills up
	if player.noswapAbility > 0
		player.noswapAbility = 0
{ind(reset_anim(), 2)}	end if
	NoSwap_flyMeter += {c['fly_refill']}
	if NoSwap_flyMeter > {full}
		NoSwap_flyMeter = {full}
	end if
	temp0 = 0
	@STORE air temp0
	@STORE lcount temp0
else
	temp4 = false // started this frame
	if player.noswapAbility == {FLY}
		if temp1 == false // hurt, held, a special state: over
			player.noswapAbility = 0
{ind(reset_anim(), 3)}		else
			if player.jumpPress == true // jump again: he lets go (and falls)
				player.noswapAbility = {FALL}
{ind(reset_anim(), 4)}			else
				if NoSwap_flyMeter <= 0
					if temp3 == false // empty: he floats down
						player.noswapAbility = {FLOAT}
{ind(reset_anim(), 6)}					end if
				end if
			end if
		end if
	else
		if player.noswapAbility != {FLOAT}
			if temp1 == true
				@LOAD temp0 air
				if temp0 > 0 // (not the frame he left the ground: the press that jumped)
					temp5 = player.jumpPress
					temp5 |= temp2
					if NoSwap_flyMeter <= 0
						temp5 = false
					end if
					if temp5 == true // the flight
						temp4 = true
						player.noswapAbility = {FLY}
						player.state = Player_State_Air
						player.timer = 0
						temp5 = player.xvel // the heading from where he's going (or faces)
						temp6 = player.yvel
						temp0 = temp5
						temp0 |= temp6
						if temp0 == 0
							NoSwap_flyHeading = 0
							if player.direction == FACING_LEFT
								NoSwap_flyHeading = {HEADING // 2}
							end if
						else
							ATan2(temp0, temp5, temp6) // (256 a turn, clockwise on screen)
							temp7 = 256
							temp7 -= temp0
							temp0 = temp7
							temp0 &= 255
							temp0 <<= 5
							NoSwap_flyHeading = temp0
						end if
						if temp5 < 0 // his speed: about the length of his velocity (the larger part + 3/8 of the smaller)
							FlipSign(temp5)
						end if
						if temp6 < 0
							FlipSign(temp6)
						end if
						if temp5 < temp6
							temp0 = temp5
							temp5 = temp6
							temp6 = temp0
						end if
						temp6 *= 3
						temp6 >>= 3
						temp5 += temp6
						if temp5 > {c['fly_speed']:#x}
							temp5 = {c['fly_speed']:#x}
						end if
						NoSwap_flySpeed = temp5
						temp0 = 0
						@STORE lcount temp0
						@STORE ltimer temp0
					end if
				end if
			end if
		end if
	end if
	@LOAD temp0 air
	if temp0 < 100
		temp0++
		@STORE air temp0
	end if
	if player.noswapAbility == {FLY}
		if temp3 == false // the meter drains (not underwater)
			NoSwap_flyMeter -= {c['fly_drain']}
			if NoSwap_flyMeter < 0
				NoSwap_flyMeter = 0
			end if
		end if
		if temp2 == true // Y: the Drill Dash
			if NoSwap_flyDrill == 0
				if NoSwap_flyMeter > 0
					NoSwap_flyDrill = {c['drill_frames'] + cool}
					NoSwap_flyMeter -= {c['drill_cost']}
					if NoSwap_flyMeter < 0
						NoSwap_flyMeter = 0
					end if
					{sfx_line(i, eng)}
				end if
			end if
		end if
		temp0 = -1 // the d-pad's direction (0 right, counterclockwise in eighths of a turn), -1 none
		if player.right == true
			temp0 = 0
			if player.up == true
				temp0 = 1
			end if
			if player.down == true
				temp0 = 7
			end if
		else
			if player.left == true
				temp0 = 4
				if player.up == true
					temp0 = 3
				end if
				if player.down == true
					temp0 = 5
				end if
			else
				if player.up == true
					temp0 = 2
				end if
				if player.down == true
					temp0 = 6
				end if
			end if
		end if
		if temp0 >= 0 // turn toward the d-pad's direction, and speed up
			temp0 *= {HEADING // 8}
			temp0 -= NoSwap_flyHeading
			temp0 += {HEADING + HEADING // 2}
			temp0 %= {HEADING}
			temp0 -= {HEADING // 2}
			if temp0 > {turn}
				temp0 = {turn}
			end if
			if temp0 < -{turn}
				temp0 = -{turn}
			end if
			NoSwap_flyHeading += temp0
			NoSwap_flyHeading += {HEADING}
			NoSwap_flyHeading %= {HEADING}
			NoSwap_flySpeed += {c['fly_accel']:#x}
			if NoSwap_flySpeed > {c['fly_speed']:#x}
				NoSwap_flySpeed = {c['fly_speed']:#x}
			end if
		else // nothing held: he slows to a hover
			NoSwap_flySpeed -= {c['fly_drag']:#x}
			if NoSwap_flySpeed < 0
				NoSwap_flySpeed = 0
			end if
		end if
		temp0 = NoSwap_flyHeading // his facing: the way he's going across
		temp0 >>= 4
		Cos(temp1, temp0)
		if temp1 > 64
			player.direction = FACING_RIGHT
		end if
		if temp1 < -64
			player.direction = FACING_LEFT
		end if
		temp4 = NoSwap_flyHeading // the heading drawn (0 right, counterclockwise in eighths)
		temp4 += {HEADING // 16}
		temp4 >>= {(HEADING // 8).bit_length() - 1}
		temp4 &= 7
		if player.direction == FACING_LEFT // (mirrored: heading d's mirror is frame 4 - d)
			temp5 = 4
			temp5 -= temp4
			temp5 &= 7
			temp4 = temp5
		end if
		if NoSwap_flyDrill > {cool} // drilling: the blur, an attack, untouchable (no flicker)
			temp5 = {c['drill_frames'] + cool}
			temp5 -= NoSwap_flyDrill
			temp5 >>= 1
			temp5 %= {DRILL_FRAMES}
			NoSwap_flyFrame = temp5
			player.animation = ANI_NOSWAP_ATTACK
			if player.blinkTimer < {eng['blink']}
				player.blinkTimer = {eng['blink']}
			end if
		else
			if temp3 == true // underwater, level: the swim cycle, faster the faster he goes
				if temp4 == 0
					temp5 = NoSwap_flySpeed
					temp5 *= 192
					temp5 /= {max(1, c['fly_speed']):#x}
					temp5 += 64
					@LOAD temp4 time
					temp4 += temp5
					temp4 %= {256 * ticks * swim}
					@STORE time temp4
					temp4 /= {256 * ticks}
					temp4 += 8
				end if
			end if
			NoSwap_flyFrame = temp4
			player.animation = ANI_NOSWAP_HOVER
		end if
		player.prevAnimation = player.animation
		player.frame = 0
		player.animationTimer = 0
{ind(loop_code(i, eng), 2)}	end if
end if
"""
    listing = __import__("monitor_swap").v4_hud_listing("NoSwap_flyIcon", "free_flight (tools/free_flight.py): the "
                                                        "flight meter, drawn in the HUD's layer (ObjectDraw)")
    if eng is CD:
        listing = "\n".join(__import__("monitor_swap").cd_hud_listing(
            "NoSwap_flyIcon", "free_flight (tools/free_flight.py): the flight meter, drawn in the HUD's layer")) + "\n"
    show = f"""NoSwap_flyIcon = 0 // the meter shows while it isn't full or he flies
temp0 = false
if NoSwap_flyMeter < {full}
	temp0 = true
end if
if player.noswapAbility == {FLY}
	temp0 = true
end if
if temp0 == true
{ind(listing, 1)}end if
"""
    if eng is CD:
        body = body.replace("CheckEqual(player.state, Player_State_RollJump)\ntemp1 |= checkResult\n",
                            "CheckEqual(player.state, Player_State_RollJump)\ntemp1 |= checkResult\n")
    text = f"""// [NoSwap] NiGHTS' free flight, Drill Dash and Paraloop (tools/free_flight.py; the S3&K DLL's native/src/NightsFlight.h)
public function NoSwap_FreeFlight{i}
{ind(body, 1)}{ind(show, 1)}end function


"""
    return resolve(text, i, eng)


def velocity_function(i):
    """NoSwap_FreeFlightVel<i>: in the air state, after its gravity and air control, before he moves: the flight's
    velocity (the heading times the speed; drill_speed while drilling), or the float's capped fall."""
    c = cfg(i)
    return f"""// [NoSwap] NiGHTS' free flight: his velocity, after the air state's gravity and air control (tools/free_flight.py)
public function NoSwap_FreeFlightVel{i}
	if player.noswapAbility == {FLY}
		temp0 = false
		CheckEqual(player.state, Player_State_Air)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Air_NoDropDash)
		temp0 |= checkResult
		if temp0 == true
			temp1 = NoSwap_flySpeed
			if NoSwap_flyDrill > {c['drill_cooldown']} // the Drill Dash
				temp1 = {c['drill_speed']:#x}
			end if
			temp2 = NoSwap_flyHeading
			temp2 >>= 4
			Cos(temp0, temp2)
			temp0 *= temp1
			temp0 >>= 9
			player.xvel = temp0
			player.speed = temp0
			Sin(temp0, temp2)
			temp0 *= temp1
			temp0 >>= 9
			FlipSign(temp0)
			player.yvel = temp0
			player.timer = 0 // (no jump cap)
		end if
	end if
	if player.noswapAbility == {FLOAT} // the meter's empty: he floats down
		if player.yvel > {c['fly_sink']:#x}
			player.yvel = {c['fly_sink']:#x}
		end if
	end if
end function


"""


def swap_in(i, depth=1, a=None):
    """The drawn frame (before ProcessAnimation / the draw): the game's animation is the drawn slot already."""
    a = a or ab().ALIAS_OF[i]
    t = "\t" * depth
    return f"""{t}if stage.playerListPos == {a} // [NoSwap] NiGHTS' flight: the drawn frame (tools/free_flight.py)
{t}	if player.noswapAbility == {FLY}
{t}		temp7 = false
{t}		if player.animation == ANI_NOSWAP_ATTACK
{t}			temp7 = true
{t}		end if
{t}		if player.animation == ANI_NOSWAP_HOVER
{t}			temp7 = true
{t}		end if
{t}		if temp7 == true
{t}			player.prevAnimation = player.animation
{t}			player.frame = NoSwap_flyFrame
{t}			player.animationTimer = 0
{t}		end if
{t}	end if
{t}end if
"""


def swap_out(i, depth=1, a=None):
    """Frame 0 again after ProcessAnimation / the draw (the game reads its hitbox: all his flight frames use the same)."""
    a = a or ab().ALIAS_OF[i]
    t = "\t" * depth
    return f"""{t}if stage.playerListPos == {a} // [NoSwap] NiGHTS' flight: frame 0 for the game again
{t}	if player.noswapAbility == {FLY}
{t}		if player.animation == ANI_NOSWAP_ATTACK
{t}			player.frame = 0
{t}		end if
{t}		if player.animation == ANI_NOSWAP_HOVER
{t}			player.frame = 0
{t}		end if
{t}	end if
{t}end if
"""


def meter_draw(i, eng):
    """The meter, in the HUD's layer (screen space): a dark box, the bar (yellow; red under a quarter)."""
    c = cfg(i)
    full = max(1, c["fly_meter"])
    return f"""temp0 = screen.xcenter // the flight meter (tools/free_flight.py)
temp0 -= {METER_W // 2 + 2}
DrawRect(temp0, {METER_TOP}, {METER_W + 4}, {METER_H + 4}, 0, 0, 0, {METER_ALPHA})
temp0 += 2
temp1 = NoSwap_flyMeter
temp1 *= {METER_W}
temp1 /= {full}
if temp1 > 0
	if NoSwap_flyMeter < {full // 4}
		DrawRect(temp0, {METER_TOP + 2}, temp1, {METER_H}, 229, 46, 39, 255)
	else
		DrawRect(temp0, {METER_TOP + 2}, temp1, {METER_H}, 255, 255, 0, 255)
	end if
end if"""


# ---------------------------------------------------------------- Sonic 1/2
def v4_table(i):
    n = len(keys(cfg(i)))
    return (f"// NiGHTS' flight state (tools/free_flight.py: keys())\nprivate table NoSwap_FlyData{i}\n\t"
            + ", ".join("0" for _ in range(n)) + "\nend table\n\n\n")


def v4_functions(i):
    return (v4_table(i) + update_function(i, V4) + velocity_function(i)
            + f"// [NoSwap] NiGHTS' jump ability: nothing (his flight starts in NoSwap_FreeFlight{i}; not Sonic's moves)\n"
            f"public function NoSwap_FlyJump{i}\n\tif player.jumpPress == true\n\t\tplayer.jumpAbilityState = 2\n"
            "\tend if\nend function\n\n\n")


def v4_air(i):
    return f"CallFunction(NoSwap_FreeFlightVel{i}) // NiGHTS' free flight (tools/free_flight.py)\n"


def v4_after(i):
    return f"CallFunction(NoSwap_FreeFlight{i}) // NiGHTS' free flight (tools/free_flight.py)\n"


def v4_patch(t, game=None):
    """The S1/S2 player script (after every other module's patches): his values (packed: noswap_common.PACKED_VALUES),
    his jump ability (none of Sonic's), the drawn frame in NoSwap_RollIn / NoSwap_RollOut, the meter's HUD-layer draw,
    reserve lines."""
    import monitor_swap
    from extras import EXTRAS, startup_case
    for i in ids():
        anchor = "public value Player_superState"
        if t.count(anchor) != 1:
            sys.exit("free_flight: Player_superState isn't there once")
        t = t.replace(anchor, "// [NoSwap] NiGHTS' free flight (tools/free_flight.py; packed: noswap_common.PACKED_VALUES)\n"
                      + "".join(f"private value {v} = 0\n" for v in V4_VALUES) + "\n" + anchor, 1)
        extra = next(e for e in EXTRAS if e["id"] == i)
        case = t.index(startup_case(extra))
        line = t.index("= Player_Action_DblJumpSonic", case)
        if line > t.index("break", case):
            sys.exit("free_flight: his startup case has no jump ability line")
        t = t[:line] + f"= NoSwap_FlyJump{i} // [NoSwap] free_flight" + t[line + len("= Player_Action_DblJumpSonic"):]
        head = "public function NoSwap_RollIn\n"
        if t.count(head) != 1:
            sys.exit("free_flight: NoSwap_RollIn isn't there once (abilities.apply_roll)")
        t = t.replace(head, head + swap_in(i))
        head = "public function NoSwap_RollOut\n"
        if t.count(head) != 1:
            sys.exit("free_flight: NoSwap_RollOut isn't there once (abilities.apply_roll)")
        start = t.index(head)
        end = t.index("end function\n", start)
        t = t[:end] + swap_out(i) + t[end:]
        for call in ("CallFunction(NoSwap_RollIn)", "CallFunction(NoSwap_RollOut)"):
            if t.count(call) != 3:
                sys.exit(f"free_flight: expected {call} around both ProcessAnimation calls and the draw")
        t = monitor_swap.v4_hud_pass(t, ab().ALIAS_OF[i], "NoSwap_flyIcon", meter_draw(i, V4),
                                     "free_flight (tools/free_flight.py): his HUD-layer listing draws the flight meter, "
                                     "not him", "free_flight")
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("free_flight: the script's reserve block isn't there once")
        t = t.replace(anchor, f"reserve function NoSwap_FreeFlight{i}\nreserve function NoSwap_FreeFlightVel{i}\n"
                      f"reserve function NoSwap_FlyJump{i}\n" + anchor)
    return t


# ---------------------------------------------------------------- Sonic CD
def to_v3(text):
    import star_grab
    names = [("object[arrayPos0].ixpos", "Object[ArrayPos0].iXPos"), ("object[arrayPos0].iypos", "Object[ArrayPos0].iYPos"),
             ("object[arrayPos0].type", "Object[ArrayPos0].Type")] + CD_NAMES \
        + [(a, b) for a, b in star_grab.V3_NAMES if a != "player.noswapAbility"] + [
        ("ANI_NOSWAP_ATTACK", str(CD["drill"])), ("ANI_NOSWAP_HOVER", str(CD["fly"]))]
    out = []
    for line in text.split("\n"):
        for a, b in names:
            line = line.replace(a, b)
        out.append(re.sub(r"\btemp(\d)\b", r"TempValue\1", line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_fly", "keyPress", "SfxName", "stage.", "^=", "object[", "screen."):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"free_flight: the CD code still has {bad!r}")
    return text


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): his functions, the call in NoSwap_AfterUpdate,
    the velocity at the end of Player_HandleAirMovement, the drawn frame around ProcessAnimation / the draw, the meter's
    HUD-layer draw, the drill's touch for monitors (NoSwap_SurgeMonitor) and bosses (NoSwap_ShotAttack), and the
    paraloop's kill list in NoSwap_ShotTouch."""
    import monitor_swap
    import shots_v3
    for i in ids():
        c = cfg(i)
        a = ab().ALIAS_OF[i]
        drill = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] NiGHTS' Drill Dash (tools/free_flight.py)\n"
                 f"\t\tif Object[5].Value1 == {FLY}\n\t\t\tif Object[5].Value6 > {c['drill_cooldown']}\n"
                 "\t\t\t\tCheckResult = true\n\t\t\tend if\n\t\tend if\n\tend if\n")
        fns = to_v3(update_function(i, CD) + velocity_function(i)
                    + "// [NoSwap] NiGHTS' flight: the drawn frame (tools/free_flight.py)\n"
                    + "public function NoSwap_FlyIn\n" + swap_in(i) + "end function\n\n\n"
                    + "// [NoSwap] NiGHTS' flight: frame 0 for the game again (tools/free_flight.py)\n"
                    + "public function NoSwap_FlyOut\n" + swap_out(i) + "end function\n\n\n")
        decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"free_flight: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("free_flight: CD's NoSwap_AfterUpdate isn't there once")
        end = t.index("\nend function\n", t.index(head))
        t = (t[:end + 1] + f"\tif Stage.PlayerListPos == {a} // [NoSwap] NiGHTS' free flight (tools/free_flight.py)\n"
             f"\t\tCallFunction(NoSwap_FreeFlight{i})\n"
             f"\t\tif Object[{CD_KILL}].Value7 > 0 // (the paraloop's kill list: its frames)\n"
             f"\t\t\tObject[{CD_KILL}].Value7--\n\t\tend if\n\tend if\n" + t[end + 1:])
        head = "\nfunction Player_HandleAirMovement\n"
        if t.count(head) != 1:
            sys.exit("free_flight: CD's Player_HandleAirMovement isn't there once")
        end = t.index("\nend function\n", t.index(head))
        t = (t[:end + 1] + f"\tif Stage.PlayerListPos == {a} // [NoSwap] NiGHTS' free flight: his velocity "
             f"(tools/free_flight.py)\n\t\tCallFunction(NoSwap_FreeFlightVel{i})\n\tend if\n" + t[end + 1:])
        head = "\nfunction NoSwap_SurgeMonitor\n"
        if t.count(head) != 1:
            sys.exit("free_flight: CD's NoSwap_SurgeMonitor isn't there once")
        t = t.replace(head, head + drill)
        head = "\nfunction NoSwap_ShotAttack\n"
        if t.count(head) != 1:
            sys.exit("free_flight: CD's NoSwap_ShotAttack isn't there once")
        t = t.replace(head, head + "\tif Object[10].Value4 == false // (the player's own touch, not a shot's)\n"
                      + "".join("\t" + l + "\n" for l in drill.rstrip("\n").split("\n")) + "\tend if\n")
        head = "\nfunction NoSwap_ShotTouch\n\tObject[11].Value0 = TempValue0\n\tObject[11].Value1 = ArrayPos0\n\tCheckResult = false\n"
        if t.count(head) != 1:
            sys.exit("free_flight: CD's NoSwap_ShotTouch changed")
        kill = "".join(f"\t\t\tif TempValue0 == Object[{CD_KILL}].Value{k}\n\t\t\t\tCheckResult = true\n"
                       f"\t\t\t\t{shots_v3.SHOT_HIT} = true\n\t\t\tend if\n" for k in range(KILL_MAX))
        t = t.replace(head, head + f"\tif Stage.PlayerListPos == {a} // [NoSwap] NiGHTS' Paraloop: what's inside his loop "
                      f"is hit (tools/free_flight.py)\n\t\tif Object[{CD_KILL}].Value7 > 0\n"
                      "\t\t\tTempValue0 = Object.EntityNo\n" + kill + "\t\tend if\n\tend if\n")
        for sub, call in (("sub ObjectMain\n", "ProcessAnimation()"), ("sub ObjectDraw\n", "DrawPlayerAnimation()")):
            start = t.index(sub)
            end = t.index("end sub\n", start)
            body = re.sub(rf"\n(\t+){re.escape(call)}\n",
                          lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_FlyIn) // [NoSwap] NiGHTS' flight\n"
                                     f"{m.group(1)}{call}\n{m.group(1)}CallFunction(NoSwap_FlyOut)\n"), t[start:end])
            n = body.count("CallFunction(NoSwap_FlyIn)")
            if n != 2 if call == "ProcessAnimation()" else n < 1:
                sys.exit(f"free_flight: {n} {call} in CD's {sub.strip()}")
            t = t[:start] + body + t[end:]
        draw = to_v3(meter_draw(i, CD))
        t = monitor_swap.cd_hud_pass(t, a, "Object[28].Value4", draw, "free_flight (tools/free_flight.py): his HUD-layer "
                                     "listing draws the flight meter, not him", "free_flight")
    return t
