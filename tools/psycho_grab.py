"""Silver's Psychokinesis (abilities.py "psycho_grab") in Sonic 1 and 2 (RSDKv4). S3&K's is the DLL's
(native/src/PsychoGrab.h); the rules and numbers are the same.

The user's design (2026-09-30): Y with a badnik in reach catches it instead of the Psychic Wave; he stops a moment (slot
45: his hand out, the orb forming), then carries it beside his hand as he plays on; Y again: a short throw pose, and it
flies straight ahead through everything it meets until a wall, the screen's edge or its lifetime, where it breaks as a
hit breaks it (explosion, animal, points). A hit on him while he has it breaks it where it is. Nothing in reach: the
Psychic Wave as before (a frame after Y).

v4 can only draw an object with its own type's sprites, so the badnik itself is what he carries and throws:
- Each grabbable badnik's script (GRABBABLE: single-object badniks; no shots, no multi-part or orbiting enemies, none
  that grab the player; no bosses) gets a block at the top of its ObjectUpdate (enemy_patch). While it's caught its own
  update is skipped (it can't move, attack or hurt anyone) and its own draw shows it as it was, frozen.
- Player 1's value12 (player.tailFrame: a Tails value no other character uses, and no script reads of another
  character's player) is the move's state: its phase in the low 4 bits (PHASES), the caught badnik's slot above them.
  value13 (player.tailAnim, likewise) is the nearest distance while it looks, then the poses' timer. Both are 0 at each
  stage load (abilities.extra_startup). The badniks read and write them; shared scripts check stage.playerListPos >= 7
  first (vanilla Tails uses the pair).
- LOOK (a frame after Y: the badniks update after him): each badnik on screen in reach (reach px ahead, behind px behind,
  height px up or down) writes its slot and distance if it's the nearest yet. Next frame he takes it (HOLD) or, none
  found, the Psychic Wave goes (WAVE: NoSwap_MeleeMove, melee_gate).
- HOLD / CARRY / THROW: the badnik keeps beside his hand (CARRY_X ahead, CARRY_Y below his centre), facing his way (the
  games' badniks face left unflipped).
- THROWN: an invisible Tails Object (a shot of the shots' group, tools/shots_v4.py, marked MARK in value34, drawing nothing:
  value36 -1) flies straight ahead and hits as a jumping player; the badnik keeps to it. When it's gone the badnik breaks
  (BREAK): Player_BadnikBreak with player 1 shown as jumping for the call (his speed and pose kept).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

PHASES = {"idle": 0, "look": 1, "hold": 2, "carry": 3, "throw": 4, "thrown": 5, "break": 6, "wave": 7}
MARK = 0x51C0  # the thrower's value34
CARRY_X, CARRY_Y = 22, -6
GRABBABLE = {
    "Sonic1u": ["BallHog", "Batbrain", "Bomb", "Burrobot", "BuzzBomber", "Chopper", "Crabmeat", "Jaws", "Motobug",
                "NewtronFly", "NewtronShoot", "Roller", "Splats", "Yadrin"],
    "Sonic2u": ["Aquis", "Balkiry", "Batbot", "Bee", "Buzzer", "ChopChop", "Coconuts", "Crawl", "Flasher", "Grounder",
                "Grounder2", "Masher", "Nebula", "Octus", "Redz", "Slicer", "Snail", "Spiker", "SpinyFloor", "SpinyWall",
                "Stegway", "Whisp"],
}


def ab():
    import abilities
    return abilities


def extras():
    return ab().with_ability("psycho_grab")


def numbers():
    """The move's numbers (the first extra with it: the badniks' shared scripts have one set)."""
    ids = extras()
    return ab().ABILITIES[ids[0]] if ids else None


def thrown_shot(i):
    """The thrower as a shot for abilities.one_shot_update_body: straight, through everything (pierce), invisible."""
    s = ab().shot(i, "s3k") or {}
    return {"motion": "straight", "speed": s.get("speed", 0x80000), "lifetime": s.get("lifetime", 90),
            "radius": s.get("radius", 12), "pierce": True, "art": {"ticks": 2}}


def looks(i):
    """What the enemies' shot loops see of the thrower: a jumping player 1 with a box the size of the S3&K shot's."""
    s = ab().shot(i, "s3k") or {}
    x0, y0, x1, y1 = s.get("art", {}).get("hitbox", [-14, -14, 14, 14])
    return f"""object.animation = ANI_JUMPING
object.gravity = GRAVITY_GROUND
object.value16 = false // isSidekick
object.value19 = object[0].value19 // badnikBonus
object.value38 = {y0} // hitbox top, bottom, left, right
object.value39 = {y1}
object.value40 = {x0}
object.value41 = {x1}
"""


def v4_after(i):
    """Player 1's side, in NoSwap_AfterUpdate before the melee (object: him)."""
    import shots_v4
    c = ab().ABILITIES[i]
    s = thrown_shot(i)
    sfx, sfx_throw = c.get("psycho_sfx", "Charge"), c.get("psycho_throw_sfx", "Release")
    ticks, hold, throw = max(1, c["psycho_ticks"]), c["psycho_hold"], c["psycho_throw"]
    top = 4  # (slot 45's last frame: 60-64)
    P = PHASES
    return f"""// Psychokinesis (tools/psycho_grab.py): player.tailFrame its phase (low 4 bits) and the caught badnik's slot,
// player.tailAnim the nearest distance while it looks, then the poses' timer
temp0 = player.tailFrame
temp1 = temp0
temp1 &= 15 // its phase
temp0 >>= 4 // the caught badnik's slot
if temp1 == {P['wave']} // (the Psychic Wave had its turn last frame)
	player.tailFrame = 0
	temp1 = 0
end if
if temp1 == {P['look']} // looked last frame (the badniks update after him)
	if temp0 > 0
		temp1 = {P['hold']}
		player.tailAnim = 0
		temp2 = temp0
		temp2 <<= 4
		temp2 |= {P['hold']}
		player.tailFrame = temp2
		PlaySfx(SfxName[{sfx}], false)
	else
		player.tailFrame = {P['wave']} // nothing in reach: the Psychic Wave (NoSwap_MeleeMove, below)
		temp1 = {P['wave']}
	end if
end if
if temp1 == 0
	if keyPress[1].buttonY != false
		temp2 = false
		CheckEqual(player.state, Player_State_Ground)
		temp2 |= checkResult
		CheckEqual(player.state, Player_State_Air)
		temp2 |= checkResult
		CheckEqual(player.state, Player_State_Air_NoDropDash)
		temp2 |= checkResult
		CheckEqual(player.state, Player_State_RollJump)
		temp2 |= checkResult
		if player.animation == ANI_HURT
			temp2 = false
		end if
		if NoSwap_melee != 0 // (the Psychic Wave going on)
			temp2 = false
		end if
		if temp2 == true
			player.tailFrame = {P['look']}
			player.tailAnim = 0x7FFF
		end if
	end if
end if
if temp1 >= {P['hold']}
	if temp1 <= {P['break']}
		arrayPos1 = temp0
		if object[arrayPos1].type == TypeName[Blank Object] // (its slot emptied: the stage took it)
			player.tailFrame = 0
			temp1 = 0
		end if
	end if
end if
if temp1 >= {P['hold']}
	if temp1 <= {P['throw']}
		temp2 = false
		CheckEqual(player.animation, ANI_HURT)
		temp2 |= checkResult
		CheckEqual(player.animation, ANI_DYING)
		temp2 |= checkResult
		CheckEqual(player.animation, ANI_DROWNING)
		temp2 |= checkResult
		if temp2 == true // a hit: it breaks where it is
			temp1 = {P['break']}
			temp2 = temp0
			temp2 <<= 4
			temp2 |= {P['break']}
			player.tailFrame = temp2
		end if
	end if
end if
if temp1 == {P['carry']} // carrying it: Y throws
	if keyPress[1].buttonY != false
		temp1 = {P['throw']}
		player.tailAnim = 0
		temp2 = temp0
		temp2 <<= 4
		temp2 |= {P['throw']}
		player.tailFrame = temp2
	end if
end if
temp2 = false // the pose (catching or throwing), held still
CheckEqual(temp1, {P['hold']})
temp2 |= checkResult
CheckEqual(temp1, {P['throw']})
temp2 |= checkResult
if temp2 == true
	player.animation = ANI_NOSWAP_ATTACK_UP
	temp3 = player.tailAnim
	temp3 /= {ticks}
	if temp3 > {top}
		temp3 = {top}
	end if
	if temp1 == {P['throw']} // (throwing: the orb goes back out)
		FlipSign(temp3)
		temp3 += {top}
	end if
	player.frame = temp3
	player.speed = 0
	player.xvel = 0
	if player.gravity == GRAVITY_AIR
		player.yvel = 0
	end if
	player.tailAnim++
	temp3 = {hold}
	if temp1 == {P['throw']}
		temp3 = {throw}
	end if
	if player.tailAnim >= temp3
		if temp1 == {P['hold']}
			temp2 = temp0 // caught: he carries it
			temp2 <<= 4
			temp2 |= {P['carry']}
			player.tailFrame = temp2
		else
			temp2 = {CARRY_X << 16} // thrown: an invisible shot flies, the badnik with it
			if player.direction == FACING_LEFT
				FlipSign(temp2)
			end if
			temp2 += player.xpos
			temp3 = player.ypos
			temp3 += {CARRY_Y << 16}
			CreateTempObject(TypeName[Tails Object], player.collisionPlane, temp2, temp3)
			arrayPos0 = object[tempObjectPos].entityPos
			temp2 = temp0
			temp2 <<= 4
			if object[arrayPos0].type == TypeName[Tails Object] // (made)
				object[arrayPos0].groupID = {shots_v4.GROUP} // the shots' group: the enemies' shot loops (tools/shots_v4.py)
				object[arrayPos0].state = {shots_v4.LIVE}
				object[arrayPos0].priority = PRIORITY_ACTIVE
				object[arrayPos0].interaction = true
				object[arrayPos0].drawOrder = player.sortedDrawOrder
				object[arrayPos0].direction = player.direction
				object[arrayPos0].xvel = {s['speed']}
				if player.direction == FACING_LEFT
					FlipSign(object[arrayPos0].xvel)
				end if
				object[arrayPos0].yvel = 0
				object[arrayPos0].value0 = 0
				object[arrayPos0].frame = 0
				object[arrayPos0].animationTimer = 0
				object[arrayPos0].value34 = {MARK} // Psychokinesis' thrower: the badnik keeps to it
				object[arrayPos0].value36 = -1 // (nothing drawn: the badnik is what shows)
				temp2 |= {P['thrown']}
				PlaySfx(SfxName[{sfx_throw}], false)
			else
				temp2 |= {P['break']}
			end if
			player.tailFrame = temp2
		end if
		if player.gravity == GRAVITY_AIR
			player.animation = ANI_JUMPING
		else
			player.animation = ANI_STOPPED
		end if
	end if
end if
"""


def melee_gate():
    """NoSwap_MeleeMove's Y, shared by every extra with a melee (abilities.melee_function): with Psychokinesis (its
    state in player.tailFrame, 0 for everyone else) Y is its own, and the Psychic Wave goes only on its WAVE phase."""
    return f"""		temp6 = keyPress[1].buttonY
		if object.value12 != 0 // [NoSwap] Psychokinesis (tools/psycho_grab.py): Y is its; the wave only when nothing was caught
			temp6 = false
			if object.value12 == {PHASES['wave']}
				temp6 = true
			end if
		end if
		if temp6 != false
"""


def enemy_block(nl="\n"):
    """The top of a grabbable badnik's ObjectUpdate (enemy_patch): LOOK, then while caught its own update skipped."""
    c = numbers()
    P = PHASES
    body = f"""	// [NoSwap] Psychokinesis (tools/psycho_grab.py: Silver): player 1's value12 its state (the low 4 bits the phase,
	// the rest the caught badnik's slot), value13 the nearest distance while it looks
	temp7 = false // caught?
	if stage.playerListPos >= 7
		temp0 = object[0].value12
		temp1 = temp0
		temp1 &= 15
		temp0 >>= 4
		if temp1 == {P['look']} // looking: in reach and on screen, the nearest yet?
			temp2 = object.xpos
			temp2 -= object[0].xpos
			temp2 >>= 16
			if object[0].direction == FACING_LEFT
				FlipSign(temp2)
			end if
			temp3 = object.ypos
			temp3 -= object[0].ypos
			temp3 >>= 16
			if temp3 < 0
				FlipSign(temp3)
			end if
			if temp2 >= -{c['psycho_behind']}
				if temp2 <= {c['psycho_reach']}
					if temp3 <= {c['psycho_height']}
						if object.outOfBounds == false
							temp4 = temp2
							if temp4 < 0
								FlipSign(temp4)
							end if
							temp4 += temp3
							if temp4 < object[0].value13
								object[0].value13 = temp4
								temp4 = object.entityPos
								temp4 <<= 4
								temp4 |= {P['look']}
								object[0].value12 = temp4
							end if
						end if
					end if
				end if
			end if
		end if
		if temp1 >= {P['hold']}
			if temp1 <= {P['break']}
				if temp0 == object.entityPos
					temp7 = true
				end if
			end if
		end if
	end if
	if temp7 == true // caught: his (its own update skipped: it can't move, attack or hurt)
		object.priority = PRIORITY_ACTIVE
		if temp1 < {P['thrown']} // beside his hand, facing his way
			temp2 = {CARRY_X << 16}
			object.direction = FLIP_X
			if object[0].direction == FACING_LEFT
				FlipSign(temp2)
				object.direction = FLIP_NONE
			end if
			object.xpos = object[0].xpos
			object.xpos += temp2
			object.ypos = object[0].ypos
			object.ypos += {CARRY_Y << 16}
		end if
		if temp1 == {P['thrown']} // with its flight (the thrower: a Tails Object marked {MARK:#x})
			temp2 = false
			foreach (TypeName[Tails Object], arrayPos0, ALL_ENTITIES)
				if object[arrayPos0].value34 == {MARK}
					object.xpos = object[arrayPos0].xpos
					object.ypos = object[arrayPos0].ypos
					temp2 = true
				end if
			next
			if temp2 == false // its flight is over
				temp1 = {P['break']}
			end if
		end if
		if temp1 == {P['break']} // the game's own break, player 1's attack (his speed and pose kept)
			object[0].value13 = object[0].animation
			object[0].value12 = object[0].yvel
			object[0].animation = ANI_JUMPING
			currentPlayer = 0
			CallFunction(Player_BadnikBreak)
			object[0].animation = object[0].value13
			object[0].yvel = object[0].value12
			object[0].value12 = 0
			object[0].value13 = 0
		end if
	else
"""
    return body.replace("\n", nl)


def enemy_patch(t, rel):
    """One grabbable badnik's script: its ObjectUpdate's body under the caught test (enemy_block)."""
    nl = "\r\n" if "\r\n" in t else "\n"
    head = f"event ObjectUpdate{nl}"
    if t.count(head) != 1:
        sys.exit(f"psycho_grab: {rel}: no single ObjectUpdate")
    start = t.index(head) + len(head)
    end = t.index(f"end event{nl}", start)
    body = t[start:end]
    body = "".join("\t" + l + nl if l.strip() else nl for l in body.split(nl)[:-1])
    return t[:start] + enemy_block(nl) + body + f"\tend if{nl}" + t[end:]


def add_builders(builders, base, game):
    """enemy_patch into a game builder's BUILDERS (after the others: the shots' and the juggernaut's), only in a build
    with an extra that has the move."""
    if not extras():
        return builders
    for name in GRABBABLE[game]:
        rel = f"Enemies/{name}.txt"
        if not (base / rel).exists():
            sys.exit(f"psycho_grab: {game} has no {rel}")
        first = builders.get(rel)
        builders[rel] = (lambda t, rel=rel, first=first: enemy_patch(first(t) if first else t, rel))
    return builders


# ---------------------------------------------------------------- Sonic CD
# The same move in CD's v3 dialect (build_soniccd.py calls cd_gate, cd_startup, cd_shot_update and cd_add_builders):
# - Its state is reserved slot CD_STATE's values (docs/soniccd_map.md section 4: a slot nothing touches, cleared at each
#   stage load, and by the player's startup): Value0 the phase (PHASES), Value1 the nearest distance while it looks, then
#   the poses' timer, then the thrower's slot; Value2 the caught badnik's slot; Value3 the badniks' scratch (caught?);
#   Value4 the caught badnik's type (anything else in its slot: the stage took it); Value5-7 a looking badnik's saved
#   TempValue0-2. Full ints (no byte fields).
# - Y is the DLL's (game.callbackParam3 1, before the melee's Y_REARM); cd_gate puts his lines before the melee's Y
#   test, which then fires the Psychic Wave only as S1/S2's melee_gate does.
# - The badniks (CD_GRABBABLE): their ObjectMain and ObjectPlayerInteraction run only when not caught. The LOOK is in their
#   ObjectPlayerInteraction, just before each player test that breaks them (the object's own code decides: a state it
#   can't be broken in, buried / submerged / armoured, never gets there).
# - THROWN: the thrower is one of Sonic CD's shots (tools/shots_v3.py: a Tails Object in its reserved slots, LIVE,
#   piercing; Value7 CD_MARK, which also draws nothing); the badniks' shot test makes its touch an attack. The caught
#   badnik keeps to it and, when it's gone, breaks with Player_BadnikBreak as a shot's hit (SHOT_HIT: no bounce).
CD_STATE = 14
CD_POSE = 48  # Psychic Hold in CD (S1/S2's 45 has no CD slot: testmods/silver/make_configs.py appends it as 47, CD's 48)
CD_MARK = -0x51C0  # the thrower's Value7 (not 0: TailsObject.txt draws nothing; not above 0 for Value6's fade)
# Single-object badniks (their projectiles are their own objects, linked to nothing). Left out: R3/KamaKama (its
# blades wait on it by its slot), R5/Kemusi (a segmented body), R8/Hotaru (its laser beam's parts), R8/PohBee (spike balls
# orbiting it), R8/Scarab (Object[+n] parts), the bosses, their parts, the projectiles and the Missions' copies.
CD_GRABBABLE = ["R1/Anton", "R1/Kamemusi", "R1/Mosqui", "R1/PataBata", "R1/TagaTaga", "R3/Ladybug", "R3/Moth",
                "R4/Dragonfly", "R4/TagaTaga", "R4/WaterSkimmer", "R4/Yago", "R5/KumoKumo", "R5/NoroNoro", "R5/Sasuri",
                "R6/BataPyon", "R6/Minomusi", "R6/PohBee", "R6/Semi", "R7/Dango", "R7/Kabasira", "R7/Kanabun",
                "R8/Dango", "R8/MechaBu"]


def cd_v(n):
    return f"Object[{CD_STATE}].Value{n}"


def cd_after(i):
    """Silver's side in NoSwap_AfterUpdate (CD), before the melee's Y test (cd_gate)."""
    import shots_v3
    c = ab().ABILITIES[i]
    s = thrown_shot(i)
    ticks, hold, throw = max(1, c["psycho_ticks"]), c["psycho_hold"], c["psycho_throw"]
    top = 4  # (Psychic Hold's last frame: 60-64)
    P, ph, t, slot, typ = PHASES, cd_v(0), cd_v(1), cd_v(2), cd_v(4)
    first, end = shots_v3.SLOTS[0], shots_v3.SLOTS[-1] + 1
    states = "".join(f"\t\tCheckEqual(Player.State, {st})\n\t\tTempValue0 |= CheckResult\n"
                     for st in ("Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash",
                                "Player_State_RollJump"))
    return f"""// Psychokinesis (tools/psycho_grab.py): {ph} its phase, {t} the nearest distance while it looks (then the
// poses' timer, then the thrower's slot), {slot} the caught badnik's slot, {typ} its type
if {ph} == {P['wave']} // (the Psychic Wave had its turn last frame)
	{ph} = 0
end if
if {ph} == {P['look']} // looked last frame (the badniks update after him)
	if {slot} > 0
		{ph} = {P['hold']}
		{t} = 0
		ArrayPos0 = {slot}
		{typ} = Object[ArrayPos0].Type
		PlaySfx(SFX_G_CHARGE, false)
	else
		{ph} = {P['wave']} // nothing in reach: the Psychic Wave (the melee, below)
	end if
end if
if {ph} == 0
	if game.callbackParam3 == 1 // Y, from the DLL
		TempValue0 = false
{states}		if Player.Animation == ANI_HURT
			TempValue0 = false
		end if
		if NoSwap.Shot != 0 // (the Psychic Wave going on)
			TempValue0 = false
		end if
		if TempValue0 == true
			{ph} = {P['look']}
			{t} = 0x7FFF
			{slot} = 0
		end if
	end if
end if
if {ph} >= {P['hold']}
	if {ph} <= {P['break']}
		ArrayPos0 = {slot}
		if Object[ArrayPos0].Type != {typ} // (its slot is something else now: the stage took it)
			{ph} = 0
			{slot} = 0
		end if
	end if
end if
if {ph} >= {P['hold']}
	if {ph} <= {P['throw']}
		CheckEqual(Player.Animation, ANI_HURT)
		TempValue0 = CheckResult
		CheckEqual(Player.Animation, ANI_DYING)
		TempValue0 |= CheckResult
		CheckEqual(Player.Animation, ANI_DROWNING)
		TempValue0 |= CheckResult
		if TempValue0 == true // a hit: it breaks where it is
			{ph} = {P['break']}
		end if
	end if
end if
if {ph} == {P['carry']} // carrying it: Y throws
	if game.callbackParam3 == 1
		{ph} = {P['throw']}
		{t} = 0
	end if
end if
CheckEqual({ph}, {P['hold']}) // the pose (catching or throwing), held still
TempValue2 = CheckResult
CheckEqual({ph}, {P['throw']})
TempValue2 |= CheckResult
if TempValue2 == true
	Player.Animation = {CD_POSE} // Psychic Hold
	TempValue3 = {t}
	TempValue3 /= {ticks}
	if TempValue3 > {top}
		TempValue3 = {top}
	end if
	if {ph} == {P['throw']} // (throwing: the orb goes back out)
		FlipSign(TempValue3)
		TempValue3 += {top}
	end if
	Player.Frame = TempValue3
	Player.AnimationTimer = 0
	Player.Speed = 0
	Player.XVelocity = 0
	if Player.Gravity == GRAVITY_AIR
		Player.YVelocity = 0
	end if
	{t}++
	TempValue3 = {hold}
	if {ph} == {P['throw']}
		TempValue3 = {throw}
	end if
	if {t} >= TempValue3
		if {ph} == {P['hold']}
			{ph} = {P['carry']} // caught: he carries it
		else
			{ph} = {P['break']} // thrown: an invisible shot flies (no free slot: it breaks here)
			TempValue2 = 0 // a free shot slot (tools/shots_v3.py)
			ArrayPos0 = {first}
			while ArrayPos0 < {end}
				if Object[ArrayPos0].Type != TypeName[Tails Object]
					if TempValue2 == 0
						TempValue2 = ArrayPos0
					end if
				end if
				ArrayPos0++
			loop
			if TempValue2 > 0
				TempValue3 = {CARRY_X << 16}
				if Player.Direction == FACING_LEFT
					FlipSign(TempValue3)
				end if
				TempValue3 += Player.XPos
				TempValue4 = Player.YPos
				TempValue4 {'-' if CARRY_Y < 0 else '+'}= {abs(CARRY_Y) << 16}
				ResetObjectEntity(TempValue2, TypeName[Tails Object], 0, TempValue3, TempValue4)
				ArrayPos0 = TempValue2
				Object[ArrayPos0].State = {shots_v3.LIVE}
				Object[ArrayPos0].Priority = PRIORITY_ACTIVE
				Object[ArrayPos0].DrawOrder = Player.DrawOrder
				Object[ArrayPos0].Direction = Player.Direction
				TempValue4 = {s['speed']:#x}
				if Player.Direction == FACING_LEFT
					FlipSign(TempValue4)
				end if
				Object[ArrayPos0].Value0 = TempValue4
				Object[ArrayPos0].Value1 = 0
				Object[ArrayPos0].Value2 = 0
				Object[ArrayPos0].Value3 = {s['radius'] << 16}
				Object[ArrayPos0].Value4 = Player.CollisionPlane
				Object[ArrayPos0].Value5 = {shots_v3.PIERCE} // it flies on through what it hits
				Object[ArrayPos0].Value6 = 0
				Object[ArrayPos0].Value7 = {CD_MARK} // Psychokinesis' thrower: the badnik keeps to it (nothing drawn)
				Object[ArrayPos0].Animation = {shots_v3.ANI_SHOT}
				Object[ArrayPos0].Frame = 0
				Object[ArrayPos0].AnimationTimer = 0
				{ph} = {P['thrown']}
				{t} = TempValue2
				PlaySfx(SFX_G_RELEASE, false)
			end if
		end if
		if Player.Gravity == GRAVITY_AIR
			Player.Animation = ANI_JUMPING
		else
			Player.Animation = ANI_STOPPED
		end if
	end if
end if
""".rstrip("\n").split("\n")


Y_TEST = "if game.callbackParam3 == 1 // Y, from the DLL"


def cd_gate(i, body):
    """build_soniccd's NoSwap_AfterUpdate lines for extra i: cd_after before the melee's Y test, which then takes Y only
    while the move is idle and fires on its WAVE phase (S1/S2's melee_gate)."""
    if body.count(Y_TEST) != 1:
        sys.exit(f"psycho_grab: extra {i}: the CD melee's Y test isn't there once")
    k = body.index(Y_TEST)
    ph = cd_v(0)
    gate = ["TempValue1 = false // [NoSwap] Psychokinesis (tools/psycho_grab.py): Y is its; the wave only when nothing was caught",
            "if game.callbackParam3 == 1 // Y, from the DLL", "\tTempValue1 = true", "end if",
            f"if {ph} != 0", "\tTempValue1 = false", f"\tif {ph} == {PHASES['wave']}", "\t\tTempValue1 = true", "\tend if",
            "end if", "if TempValue1 == true"]
    return body[:k] + cd_after(i) + gate + body[k + 1:]


def cd_startup():
    """A clean state at each stage load (the player's startup; the engine clears the slot too)."""
    return "".join(f"\t\t{cd_v(n)} = 0 // Psychokinesis (tools/psycho_grab.py)\n" for n in range(5))


def cd_shot_update(i):
    """The thrower's own update (NoSwap_ShotUpdate's block: Object, the thrower): a straight, piercing shot."""
    import shots_v3
    return shots_v3.update_body_of(thrown_shot(i), shots_v3.ANI_SHOT)


def cd_caught(ind):
    """Lines setting the scratch Value3 to 1 when this badnik is the caught one (no temps: its own code runs after)."""
    return [f"{ind}{cd_v(3)} = 0 // [NoSwap] Psychokinesis (tools/psycho_grab.py: Silver): is it the caught one?",
            f"{ind}if Object.EntityNo == {cd_v(2)}", f"{ind}\tif {cd_v(0)} >= {PHASES['hold']}",
            f"{ind}\t\t{cd_v(3)} = 1", f"{ind}\tend if", f"{ind}end if"]


def cd_look(ind):
    """A badnik's LOOK (just before its player test that breaks it): in reach, on screen, the nearest yet? Its temps are
    kept (Value5-7)."""
    c = numbers()
    P = PHASES
    body = f"""if {cd_v(0)} == {P['look']} // [NoSwap] Psychokinesis (tools/psycho_grab.py: Silver) looks: in reach, on screen, nearest?
	{cd_v(5)} = TempValue0
	{cd_v(6)} = TempValue1
	{cd_v(7)} = TempValue2
	TempValue0 = Object.XPos // ahead of him
	TempValue0 -= Player.XPos
	TempValue0 >>= 16
	if Player.Direction == 1 // (facing left)
		FlipSign(TempValue0)
	end if
	TempValue1 = Object.YPos // above or below him
	TempValue1 -= Player.YPos
	TempValue1 >>= 16
	if TempValue1 < 0
		FlipSign(TempValue1)
	end if
	if TempValue0 >= -{c['psycho_behind']}
		if TempValue0 <= {c['psycho_reach']}
			if TempValue1 <= {c['psycho_height']}
				TempValue2 = Object.iXPos
				TempValue2 -= Screen.XOffset
				if TempValue2 >= 0
					if TempValue2 < Screen.XSize
						TempValue2 = Object.iYPos
						TempValue2 -= Screen.YOffset
						if TempValue2 >= 0
							if TempValue2 < Screen.YSize
								if TempValue0 < 0
									FlipSign(TempValue0)
								end if
								TempValue0 += TempValue1
								if TempValue0 < {cd_v(1)}
									{cd_v(1)} = TempValue0
									{cd_v(2)} = Object.EntityNo
								end if
							end if
						end if
					end if
				end if
			end if
		end if
	end if
	TempValue0 = {cd_v(5)}
	TempValue1 = {cd_v(6)}
	TempValue2 = {cd_v(7)}
end if"""
    return [ind + l for l in body.split("\n")]


def cd_held():
    """The top of a caught badnik's ObjectMain (its own code skipped): beside his hand, with the thrower, or broken."""
    P = PHASES
    ph = cd_v(0)
    return f"""	Object.Priority = 1 // (active offscreen too)
	if {ph} < {P['thrown']} // beside his hand, facing his way (the badniks face left unflipped)
		Object.XPos = Player.XPos
		Object.Direction = 1
		if Player.Direction == 0
			Object.XPos += {CARRY_X << 16}
		else
			Object.XPos -= {CARRY_X << 16}
			Object.Direction = 0
		end if
		Object.YPos = Player.YPos
		Object.YPos {'-' if CARRY_Y < 0 else '+'}= {abs(CARRY_Y) << 16}
	end if
	if {ph} == {P['thrown']} // with its flight (the thrower: a Tails Object in its slot, Value7 {CD_MARK})
		ArrayPos0 = {cd_v(1)}
		{cd_v(3)} = 0
		if Object[ArrayPos0].Type == TypeName[Tails Object]
			if Object[ArrayPos0].Value7 == {CD_MARK}
				Object.XPos = Object[ArrayPos0].XPos
				Object.YPos = Object[ArrayPos0].YPos
				{cd_v(3)} = 1
			end if
		end if
		if {cd_v(3)} == 0 // its flight is over
			{ph} = {P['break']}
		end if
	end if
	if {ph} == {P['break']} // the game's own break, as a shot's hit (no bounce for him: tools/shots_v3.py SHOT_HIT)
		{ph} = 0
		{cd_v(1)} = 0
		{cd_v(2)} = 0
		{__import__('shots_v3').SHOT_HIT} = true
		CallFunction(Player_BadnikBreak)
	end if""".split("\n")


def cd_wrap_sub(t, sub, rel, top, held=None):
    """`sub`'s body runs only when this badnik isn't the caught one (`top`: lines before the test; held: lines for the
    caught one)."""
    head = f"sub {sub}\n"
    if t.count(head) != 1:
        sys.exit(f"psycho_grab: {rel}: no single {sub}")
    start = t.index(head) + len(head)
    end = t.index("\nend sub\n", start)
    body = t[start:end].split("\n")
    body = [("\t" + l if l.strip() and not l.lstrip().startswith("#") else l) for l in body]
    new = top + cd_caught("\t") + ([f"\tif {cd_v(3)} == 1 // caught: his (its own code skipped: it can't move, attack or hurt)"]
                                   + ["\t" + l for l in held] + ["\telse"] if held else [f"\tif {cd_v(3)} == 0"]) + body + ["\tend if"]
    return t[:start] + "\n".join(new) + t[end:]


def cd_enemy_patch(t, rel):
    import shots_v3
    lines = t.split("\n")
    sites = []
    for first, last, ind, box in shots_v3.collision_sites(lines):
        nxt = shots_v3.next_code(lines, last, 2)
        if nxt and (nxt[0] == "if CheckResult == false" or nxt == ["if CheckResult == true", "CallFunction(Player_BadnikBreak)"]):
            sites.append((first, ind))
    if not sites:
        sys.exit(f"psycho_grab: {rel}: no badnik test for the LOOK")
    for first, ind in sorted(sites, reverse=True):
        lines[first:first] = cd_look(ind)
    t = "\n".join(lines)
    t = cd_wrap_sub(t, "ObjectPlayerInteraction", rel, [])
    return cd_wrap_sub(t, "ObjectMain", rel, [], cd_held())


def cd_add_builders(builders, base):
    """cd_enemy_patch into build_soniccd's BUILDERS, after the others (the shots' tests included), in a build with the move."""
    if not extras():
        return builders
    for name in CD_GRABBABLE:
        rel = f"{name}.txt"
        if not (base / rel).exists():
            sys.exit(f"psycho_grab: Sonic CD has no {rel}")
        first = builders.get(rel)
        builders[rel] = (lambda t, rel=rel, first=first: cd_enemy_patch(first(t) if first else t, rel))
    return builders
