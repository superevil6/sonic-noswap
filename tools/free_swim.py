"""Ecco's free swim (abilities.py "free_swim"), for Sonic 1/2 (Retro Engine v4 player script; abilities.py calls in here)
and Sonic CD (build_soniccd.py calls cd_patch). The S3&K DLL's is native/src/EccoSwim.h, the reference: this is a port
of it, the same rules and numbers (Ecco's abilities.py entry).

The user's design (2026-09-30, "painful but beatable" on land, a god in water):
- Underwater (S1/S2 / CD: player.gravityStrength 0x1000, which the Water objects set below the water line) he swims
  anywhere: a heading (HEADING units a turn, 0 right, counterclockwise) turns toward the d-pad's direction by swim_turn
  degrees a frame while the speed builds by swim_accel up to swim_speed; nothing held, it drains by swim_drag. He's kept
  in the game's air state; his velocity is the heading times the speed, set right after the air state's own gravity and
  air control (S1/S2: NoSwap_AirAbilities; CD: the end of Player_HandleAirMovement), so neither touches it. Resting on
  the floor, anything held (or Y) lifts him off.
- Never flipped while swimming (the frames are drawn every way round): slot "Swim", 8 directions x swim_cycle frames,
  direction-major (frame swim_cycle * d + k; d 0 right, counterclockwise in 45-degree steps), the cycle faster the
  faster he goes (swim_ticks game frames a frame at full speed).
- Y: the charge ram, ram_frames frames at ram_speed along the heading, an attack (badniks break, monitors break, bosses
  take the hit; untouchable meanwhile: the post-hit timer kept up without its flicker), then ram_cooldown frames' rest;
  slot "Charge", 8 directions x ram_cycle frames (the blur last), frame ram_cycle * d + (t / 2) % ram_cycle.
- Swimming up out of the surface: the leap, the game's own air physics, slot "Leap" (leap_frames frames, leap_ticks
  game frames each) until he lands or is back in the water.
- A hit, an object holding him, or any state but the plain ground / air ones: no swim.

Attack or not (the slots' numbers are other moves' attack slots):
  S1/S2: Swim 41, Charge 42, Leap 43; 41 (ANI_NOSWAP_ATTACK) and 43 (ANI_NOSWAP_MELEE) are attacks to the game
    (Player_BadnikBreak, Player_CheckHit: bosses, Global/Monitor.txt), 42 (ANI_NOSWAP_HOVER) isn't.
  CD: Swim 45, Leap 46, Charge 47; 45 / 46 are Amy's hammer slots (Player_BadnikBreak takes them as attacks for anyone),
    47 isn't.
So the game sees another animation than the one drawn, as extras.py "roll" does (abilities.apply_roll): the game's
animation is the non-attack slot (S1/S2 42, CD 47) while he swims or leaps and the attack slot (S1/S2 41, CD 45) while
he rams; right before ProcessAnimation / the draw it's swapped for the drawn slot and its frame (NoSwap_swimFrame), and
right after swapped back (frame 0: the game reads the frame's hitbox; all of these frames use the standing box). S1/S2
hook into abilities.py's NoSwap_RollIn / NoSwap_RollOut; CD gets its own NoSwap_SwimIn / NoSwap_SwimOut around its
ProcessAnimation / DrawPlayerAnimation. CD's monitors and bosses only take Amy's hammer slots as attacks for Amy: there
the ram answers NoSwap_SurgeMonitor (monitors) and NoSwap_ShotAttack (bosses, called on the player's touch).

State (S1/S2 / CD):
  player.noswapAbility / Object[5].Value1   the mode: 0 none, 1 swimming, 2 leaping (CD: NoSwap.Pogo's value; he has
                                            no pogo, and a non-zero one only stops the ground reset of Value0)
  NoSwap_swimHeading / Object[5].Value4     the heading (0..HEADING-1)
  NoSwap_swimSpeed / Object[5].Value5       the speed (16.16)
  NoSwap_swimCool / Object[5].Value6        the ram and its rest: ram_frames + ram_cooldown at the press, counting down;
                                            ramming while above ram_cooldown
  NoSwap_swimTime / Object[5].Value2        the swim cycle's timer (256ths of a game frame), or the leap's frames
  NoSwap_swimFrame / Object[5].Value0       the drawn slot's frame (read while the mode isn't 0)
(S1/S2's NoSwap_swim* values are packed into Player_unusedValue1/2/4/5/6: noswap_common.PACKED_VALUES.)
"""
import re
import sys

HEADING = 8192  # heading units a full turn (Sin / Cos take HEADING >> 4 = 512)
SWIM, LEAP = 1, 2
WATER_GRAVITY = 0x1000  # the player's gravityStrength underwater (S1/S2 and CD)
V4 = {"swim": 41, "ram": 42, "leap": 43, "game_swim": 42, "game_ram": 41, "blink": 3,
      "y": "if keyPress[1].buttonY != false"}
CD = {"swim": 45, "ram": 47, "leap": 46, "game_swim": 47, "game_ram": 45, "blink": 2,
      "y": "if game.callbackParam3 == 1 // Y, from the DLL"}
CD_NAMES = [("player.noswapAbility", "Object[5].Value1"), ("NoSwap_swimHeading", "Object[5].Value4"),
            ("NoSwap_swimSpeed", "Object[5].Value5"), ("NoSwap_swimCool", "Object[5].Value6"),
            ("NoSwap_swimTime", "Object[5].Value2"), ("NoSwap_swimFrame", "Object[5].Value0")]
V4_VALUES = ["NoSwap_swimHeading", "NoSwap_swimSpeed", "NoSwap_swimCool", "NoSwap_swimTime", "NoSwap_swimFrame"]


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("free_swim")


def check(i):
    c = ab().ABILITIES[i]
    if c.get("swim_dirs", 8) != 8:
        sys.exit(f"free_swim: extra {i}: S1/S2 / CD draw 8 directions (swim_dirs 8)")
    taken = [a for a in c["abilities"] if a not in ("free_swim", "no_breathing", "physics")]
    if taken or c.get("shot") or c.get("melee_reach"):
        sys.exit(f"free_swim: extra {i}: free_swim uses noswapAbility, NoSwap_swim* and slots 41-43 alone ({taken})")
    return c


def sound(i, eng):
    c = ab().ABILITIES[i]
    return (f"PlaySfx(SfxName[{c.get('ram_sfx_v4', 'Release')}], false)" if eng is V4
            else f"PlaySfx({c.get('ram_sfx_cd', 'SFX_G_RELEASE')}, false)")


def reset_anim(depth, eng):
    """His animation back to the game's (walking: the ground state picks its own next frame) if it's still a swim one."""
    t = "\t" * depth
    return (f"{t}if player.animation == {eng['game_swim']}\n{t}\tplayer.animation = ANI_WALKING\n{t}end if\n"
            f"{t}if player.animation == {eng['game_ram']}\n{t}\tplayer.animation = ANI_WALKING\n{t}end if\n")


def update_function(i, eng):
    """NoSwap_FreeSwim<i>: every frame after the player has moved (NoSwap_AfterUpdate): the mode, the heading and speed,
    the ram's start, the lift off the floor, the leap, and the game's / the drawn animation."""
    c = check(i)
    ram_cool = c["ram_cooldown"]
    turn = round(c["swim_turn"] * HEADING / 360) if c["swim_turn"] > 0 else HEADING // 2
    cyc, ticks, rcyc = max(1, c["swim_cycle"]), max(1, c["swim_ticks"]), max(1, c["ram_cycle"])
    rearm = "".join(f"\t{l}\n" for l in __import__("build_soniccd").Y_REARM) if eng is CD else ""
    return f"""// [NoSwap] Ecco's free swim (tools/free_swim.py; the S3&K DLL's native/src/EccoSwim.h)
public function NoSwap_FreeSwim{i}
	if NoSwap_swimCool > 0
		NoSwap_swimCool--
	end if
	temp2 = false // Y pressed
	{eng['y']}
		temp2 = true
	end if
{rearm}	temp0 = false // the plain ground states (on the ground)
	if player.gravity == GRAVITY_GROUND
		CheckEqual(player.state, Player_State_Ground)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_LookUp)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Crouch)
		temp0 |= checkResult
	end if
	temp1 = false // the plain air states
	CheckEqual(player.state, Player_State_Air)
	temp1 |= checkResult
	CheckEqual(player.state, Player_State_Air_NoDropDash)
	temp1 |= checkResult
	if player.animation == ANI_HURT
		temp0 = false
		temp1 = false
	end if
	if player.gravityStrength != {WATER_GRAVITY:#x} // out of the water
		if NoSwap_swimCool > {ram_cool} // (no ram out there)
			NoSwap_swimCool = {ram_cool}
		end if
		if player.noswapAbility == {SWIM}
			player.noswapAbility = 0
			temp3 = false
			if temp1 == true
				if player.gravity == GRAVITY_AIR
					if player.yvel < 0 // going up out of the surface: the leap
						temp3 = true
					end if
				end if
			end if
			if temp3 == true
				player.noswapAbility = {LEAP}
				NoSwap_swimTime = 0
				temp4 = NoSwap_swimHeading
				temp4 >>= 4
				Cos(temp5, temp4)
				player.direction = FACING_RIGHT
				if temp5 < 0
					player.direction = FACING_LEFT
				end if
			else
{reset_anim(4, eng)}			end if
		end if
		if player.noswapAbility == {LEAP}
			temp3 = temp1
			if player.gravity == GRAVITY_GROUND
				temp3 = false
			end if
			if temp3 == false // landed, hurt, a spring or an object...: over
				player.noswapAbility = 0
{reset_anim(4, eng)}			else // the leap's frames (the game's air physics carry him)
				temp4 = NoSwap_swimTime
				temp4 /= {max(1, c['leap_ticks'])}
				if temp4 > {max(1, c['leap_frames']) - 1}
					temp4 = {max(1, c['leap_frames']) - 1}
				end if
				NoSwap_swimTime++
				NoSwap_swimFrame = temp4
				player.animation = {eng['game_swim']}
				player.prevAnimation = player.animation
				player.frame = 0
				player.animationTimer = 0
			end if
		end if
	else // underwater
		if player.noswapAbility == {LEAP} // back in: the leap's over
			player.noswapAbility = 0
		end if
		temp3 = temp0
		temp3 |= temp1
		if temp3 == false // hurt, held, a special state: no swim
			if NoSwap_swimCool > {ram_cool}
				NoSwap_swimCool = {ram_cool}
			end if
			if player.noswapAbility == {SWIM}
				player.noswapAbility = 0
{reset_anim(4, eng)}			end if
		else
			if player.noswapAbility != {SWIM} // into the swim: the heading from where he's going (or faces)
				temp4 = player.xvel
				temp5 = player.yvel
				temp3 = temp4
				temp3 |= temp5
				if temp3 == 0
					NoSwap_swimHeading = 0
					if player.direction == FACING_LEFT
						NoSwap_swimHeading = {HEADING // 2}
					end if
				else
					ATan2(temp3, temp4, temp5) // (256 a turn, clockwise on screen)
					temp6 = 256
					temp6 -= temp3
					temp3 = temp6
					temp3 &= 255
					temp3 <<= 5
					NoSwap_swimHeading = temp3
				end if
				if temp4 < 0 // his speed: about the length of his velocity (the larger part + 3/8 of the smaller)
					FlipSign(temp4)
				end if
				if temp5 < 0
					FlipSign(temp5)
				end if
				if temp4 < temp5
					temp3 = temp4
					temp4 = temp5
					temp5 = temp3
				end if
				temp5 *= 3
				temp5 >>= 3
				temp4 += temp5
				if temp4 > {c['swim_speed']:#x}
					temp4 = {c['swim_speed']:#x}
				end if
				NoSwap_swimSpeed = temp4
			end if
			temp3 = -1 // the d-pad's direction (0 right, counterclockwise in eighths of a turn), -1 none
			if player.right == true
				temp3 = 0
				if player.up == true
					temp3 = 1
				end if
				if player.down == true
					temp3 = 7
				end if
			else
				if player.left == true
					temp3 = 4
					if player.up == true
						temp3 = 3
					end if
					if player.down == true
						temp3 = 5
					end if
				else
					if player.up == true
						temp3 = 2
					end if
					if player.down == true
						temp3 = 6
					end if
				end if
			end if
			temp6 = true // swimming on
			if player.gravity == GRAVITY_GROUND // resting on the floor: anything held (or the ram) lifts him off
				temp7 = temp2
				if temp3 >= 0
					temp7 = true
				end if
				if NoSwap_swimCool > {ram_cool}
					temp7 = true
				end if
				if temp7 == false
					temp6 = false
					if player.noswapAbility == {SWIM}
						player.noswapAbility = 0
{reset_anim(6, eng)}					end if
				else
					player.state = Player_State_Air
					player.gravity = GRAVITY_AIR
					player.angle = 0
					player.collisionMode = CMODE_FLOOR
					player.ypos -= 0x20000
				end if
			end if
			if temp6 == true
				player.noswapAbility = {SWIM}
				if temp2 == true // Y: the ram
					if NoSwap_swimCool == 0
						NoSwap_swimCool = {c['ram_frames'] + ram_cool}
						{sound(i, eng)}
					end if
				end if
				if temp3 >= 0 // turn toward the d-pad's direction, and speed up
					temp3 *= {HEADING // 8}
					temp3 -= NoSwap_swimHeading
					temp3 += {HEADING + HEADING // 2}
					temp3 %= {HEADING}
					temp3 -= {HEADING // 2}
					if temp3 > {turn}
						temp3 = {turn}
					end if
					if temp3 < -{turn}
						temp3 = -{turn}
					end if
					NoSwap_swimHeading += temp3
					NoSwap_swimHeading += {HEADING}
					NoSwap_swimHeading %= {HEADING}
					NoSwap_swimSpeed += {c['swim_accel']:#x}
					if NoSwap_swimSpeed > {c['swim_speed']:#x}
						NoSwap_swimSpeed = {c['swim_speed']:#x}
					end if
				else // nothing held: gliding to a stop
					NoSwap_swimSpeed -= {c['swim_drag']:#x}
					if NoSwap_swimSpeed < 0
						NoSwap_swimSpeed = 0
					end if
				end if
				temp4 = NoSwap_swimHeading // the direction drawn
				temp4 += {HEADING // 16}
				temp4 >>= {(HEADING // 8).bit_length() - 1}
				temp4 &= 7
				if NoSwap_swimCool > {ram_cool} // ramming: the charge's frames, untouchable (no flicker)
					temp5 = {c['ram_frames'] + ram_cool}
					temp5 -= NoSwap_swimCool
					temp5 >>= 1
					temp5 %= {rcyc}
					temp4 *= {rcyc}
					temp4 += temp5
					player.animation = {eng['game_ram']}
					if player.blinkTimer < {eng['blink']}
						player.blinkTimer = {eng['blink']}
					end if
				else // the stroke's cycle, faster the faster he goes
					temp5 = NoSwap_swimSpeed
					temp5 *= 192
					temp5 /= {max(1, c['swim_speed']):#x}
					temp5 += 64
					NoSwap_swimTime += temp5
					NoSwap_swimTime %= {256 * ticks * cyc}
					temp5 = NoSwap_swimTime
					temp5 /= {256 * ticks}
					temp4 *= {cyc}
					temp4 += temp5
					player.animation = {eng['game_swim']}
				end if
				NoSwap_swimFrame = temp4
				player.prevAnimation = player.animation
				player.frame = 0
				player.animationTimer = 0
				player.direction = FACING_RIGHT // (drawn every way round: never flipped)
			end if
		end if
	end if
end function


"""


def velocity_function(i):
    """NoSwap_FreeSwimVel<i>: in the air state, after its gravity and air control, before he moves: the swim's velocity
    (the heading times the speed; ram_speed while ramming)."""
    c = ab().ABILITIES[i]
    return f"""// [NoSwap] Ecco's free swim: his velocity, after the air state's gravity and air control (tools/free_swim.py)
public function NoSwap_FreeSwimVel{i}
	if player.noswapAbility == {SWIM}
		temp0 = false
		CheckEqual(player.state, Player_State_Air)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Air_NoDropDash)
		temp0 |= checkResult
		if temp0 == true
			temp1 = NoSwap_swimSpeed
			if NoSwap_swimCool > {c['ram_cooldown']} // the ram
				temp1 = {c['ram_speed']:#x}
			end if
			temp2 = NoSwap_swimHeading
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
end function


"""


def swap_in(i, eng, depth=1, a=None):
    """The game's animation -> the drawn one and its frame (before ProcessAnimation / the draw)."""
    a = a or ab().ALIAS_OF[i]
    t = "\t" * depth
    return f"""{t}if stage.playerListPos == {a} // [NoSwap] Ecco's free swim: the drawn slot and frame (tools/free_swim.py)
{t}	if player.noswapAbility > 0
{t}		if player.animation == {eng['game_ram']}
{t}			player.animation = {eng['ram']}
{t}			player.prevAnimation = player.animation
{t}			player.frame = NoSwap_swimFrame
{t}			player.animationTimer = 0
{t}		else
{t}			if player.animation == {eng['game_swim']}
{t}				player.animation = {eng['swim']}
{t}				if player.noswapAbility == {LEAP}
{t}					player.animation = {eng['leap']}
{t}				end if
{t}				player.prevAnimation = player.animation
{t}				player.frame = NoSwap_swimFrame
{t}				player.animationTimer = 0
{t}			end if
{t}		end if
{t}	end if
{t}end if
"""


def swap_out(i, eng, depth=1, a=None):
    """The drawn animation -> the game's one (after ProcessAnimation / the draw), frame 0 (the game reads its hitbox)."""
    a = a or ab().ALIAS_OF[i]
    t = "\t" * depth
    out = f"{t}if stage.playerListPos == {a} // [NoSwap] Ecco's free swim: back to the game's animation\n" \
          f"{t}\tif player.noswapAbility > 0\n"
    pairs = [(eng["ram"], eng["game_ram"]), (eng["swim"], eng["game_swim"]), (eng["leap"], eng["game_swim"])]
    for k, (drawn, game) in enumerate(pairs):
        d = t + "\t" * (2 + k)
        out += (f"{d}if player.animation == {drawn}\n{d}\tplayer.animation = {game}\n"
                f"{d}\tplayer.prevAnimation = player.animation\n{d}\tplayer.frame = 0\n")
        if k < len(pairs) - 1:
            out += f"{d}else\n"
    for k in reversed(range(len(pairs))):
        out += f"{t}{chr(9) * (2 + k)}end if\n"
    return out + f"{t}\tend if\n{t}end if\n"


# ---------------------------------------------------------------- Sonic 1/2
def v4_functions(i):
    return update_function(i, V4) + velocity_function(i)


def v4_air(i):
    """NoSwap_AirAbilities (in the air state, after its gravity and air control): the swim's velocity."""
    return f"CallFunction(NoSwap_FreeSwimVel{i}) // Ecco's free swim (tools/free_swim.py)\n"


def v4_after(i):
    return f"CallFunction(NoSwap_FreeSwim{i}) // Ecco's free swim (tools/free_swim.py)\n"


def v4_patch(t, game=None):
    """The S1/S2 player script (after every other module's patches): his values (packed: noswap_common.PACKED_VALUES),
    the animation swap in NoSwap_RollIn / NoSwap_RollOut (around ProcessAnimation and the draw), reserve lines."""
    for i in ids():
        anchor = "public value Player_superState"
        if t.count(anchor) != 1:
            sys.exit("free_swim: Player_superState isn't there once")
        t = t.replace(anchor, "// [NoSwap] Ecco's free swim (tools/free_swim.py; packed: noswap_common.PACKED_VALUES)\n"
                      + "".join(f"private value {v} = 0\n" for v in V4_VALUES) + "\n" + anchor, 1)
        head = "public function NoSwap_RollIn\n"
        if t.count(head) != 1:
            sys.exit("free_swim: NoSwap_RollIn isn't there once (abilities.apply_roll)")
        t = t.replace(head, head + swap_in(i, V4))
        head = "public function NoSwap_RollOut\n"
        if t.count(head) != 1:
            sys.exit("free_swim: NoSwap_RollOut isn't there once (abilities.apply_roll)")
        start = t.index(head)
        end = t.index("end function\n", start)
        t = t[:end] + swap_out(i, V4) + t[end:]
        for call in ("CallFunction(NoSwap_RollIn)", "CallFunction(NoSwap_RollOut)"):
            if t.count(call) != 3:
                sys.exit(f"free_swim: expected {call} around both ProcessAnimation calls and the draw")
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("free_swim: the script's reserve block isn't there once")
        t = t.replace(anchor, f"reserve function NoSwap_FreeSwim{i}\nreserve function NoSwap_FreeSwimVel{i}\n" + anchor)
    return t


# ---------------------------------------------------------------- Sonic CD
def to_v3(text):
    import star_grab
    names = CD_NAMES + star_grab.V3_NAMES + [
        ("player.gravityStrength", "Player.GravityStrength"), ("player.angle", "Player.Angle"),
        ("player.collisionMode", "Player.CollisionMode"), ("stage.playerListPos", "Stage.PlayerListPos")]
    out = []
    for line in text.split("\n"):
        for a, b in names:
            line = line.replace(a, b)
        out.append(re.sub(r"\btemp(\d)\b", r"TempValue\1", line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_swim", "keyPress", "SfxName", "stage.", "^="):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"free_swim: the CD code still has {bad!r}")
    return text


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): his functions, the call in NoSwap_AfterUpdate,
    the velocity at the end of Player_HandleAirMovement, the animation swap around ProcessAnimation / the draw, and the
    ram's touch for monitors (NoSwap_SurgeMonitor) and bosses (NoSwap_ShotAttack)."""
    for i in ids():
        c = check(i)
        a = ab().ALIAS_OF[i]
        ram = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] Ecco's ram (tools/free_swim.py)\n"
               f"\t\tif Object[5].Value1 == {SWIM}\n\t\t\tif Object[5].Value6 > {c['ram_cooldown']}\n"
               "\t\t\t\tCheckResult = true\n\t\t\tend if\n\t\tend if\n\tend if\n")
        fns = to_v3(update_function(i, CD) + velocity_function(i)
                    + "// [NoSwap] Ecco's free swim: the game's animation -> the drawn one (tools/free_swim.py)\n"
                    + "public function NoSwap_SwimIn\n" + swap_in(i, CD) + "end function\n\n\n"
                    + "// [NoSwap] Ecco's free swim: the drawn animation -> the game's one (tools/free_swim.py)\n"
                    + "public function NoSwap_SwimOut\n" + swap_out(i, CD) + "end function\n\n\n")
        decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"free_swim: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        # NoSwap_AfterUpdate: his update, at its end
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("free_swim: CD's NoSwap_AfterUpdate isn't there once")
        end = t.index("\nend function\n", t.index(head))
        t = (t[:end + 1] + f"\tif Stage.PlayerListPos == {a} // [NoSwap] Ecco's free swim (tools/free_swim.py)\n"
             f"\t\tCallFunction(NoSwap_FreeSwim{i})\n\tend if\n" + t[end + 1:])
        # the velocity: after the air state's gravity and air control
        head = "\nfunction Player_HandleAirMovement\n"
        if t.count(head) != 1:
            sys.exit("free_swim: CD's Player_HandleAirMovement isn't there once")
        end = t.index("\nend function\n", t.index(head))
        t = (t[:end + 1] + f"\tif Stage.PlayerListPos == {a} // [NoSwap] Ecco's free swim: his velocity "
             f"(tools/free_swim.py)\n\t\tCallFunction(NoSwap_FreeSwimVel{i})\n\tend if\n" + t[end + 1:])
        # the ram breaks monitors and hits bosses (CD takes Amy's hammer slots as attacks for Amy only there)
        head = "\nfunction NoSwap_SurgeMonitor\n"
        if t.count(head) != 1:
            sys.exit("free_swim: CD's NoSwap_SurgeMonitor isn't there once")
        t = t.replace(head, head + ram)
        head = "\nfunction NoSwap_ShotAttack\n"
        if t.count(head) != 1:
            sys.exit("free_swim: CD's NoSwap_ShotAttack isn't there once")
        t = t.replace(head, head + "\tif Object[10].Value4 == false // (the player's own touch, not a shot's)\n"
                      + "".join("\t" + l + "\n" for l in ram.rstrip("\n").split("\n")) + "\tend if\n")
        # the animation swap around ProcessAnimation (ObjectMain) and the draw (ObjectDraw)
        for sub, call in (("sub ObjectMain\n", "ProcessAnimation()"), ("sub ObjectDraw\n", "DrawPlayerAnimation()")):
            start = t.index(sub)
            end = t.index("end sub\n", start)
            body = re.sub(rf"\n(\t+){re.escape(call)}\n",
                          lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_SwimIn) // [NoSwap] Ecco's free swim\n"
                                     f"{m.group(1)}{call}\n{m.group(1)}CallFunction(NoSwap_SwimOut)\n"), t[start:end])
            n = body.count("CallFunction(NoSwap_SwimIn)")  # (ObjectMain: the normal and the debug-mode copy; the
            if n != 2 if call == "ProcessAnimation()" else n < 1:  # draw: every DrawPlayerAnimation there)
                sys.exit(f"free_swim: {n} {call} in CD's {sub.strip()}")
            t = t[:start] + body + t[end:]
    return t
