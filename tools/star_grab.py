"""Ristar's moves (abilities.py "star_grab"): the Grab, the wall / ceiling hang and the Meteor Strike, for Sonic 1/2
(Retro Engine v4 player script; abilities.py calls in here) and the numbers the CD builder and the S3&K DLL read.

The user's design (2026-09-29):
- Y: Grab, aimed 8 ways with the d-pad (nothing held: forward; on the ground, down doesn't count). His arms stretch out
  grab_step px per frame for grab_frames frames (80 px) and come back in retract_frames. The arms are drawn at runtime,
  as the game draws them (vector lines): two 2 px black lines from his body to his hands (the sheet's loose hands, slot
  43 "Hands", at the ends). His body: slot 41 "Grab" (the reaching bodies; an attack).
  - The hands catch a badnik (the game's own Player_BadnikBreak while the arms are out): he's yanked in to it (the
    pulled-forward bodies, then the headbutt frame), headbutts it (his body attacks: the game breaks it) and bounces
    off. A monitor or a boss the hands touch is hit there (the arms' reach attacks, as Max's ear).
  - The hands catch solid terrain (the tip in a tile, floor or ceiling side: Max's Ear Grapple test): he's pulled in,
    and next to a wall or under a ceiling he HANGS there (gravity off; slot 42 "Hang": the Ladder frames on a wall, the
    Overhead ones under a ceiling). Up / down climb a wall (past its top: a hop onto the ledge), left / right move along
    a ceiling. A jump press and release lets go with a hop.
  - Nothing caught: the arms come back.
- Meteor Strike: hanging, hold jump; after windup_show frames he winds up (the swing-on-handle frames, drawn round his
  grip); held windup_full frames (1 s) or more, letting go launches him where the d-pad points (8 ways; nothing held:
  away from the wall, or the way he faces under a ceiling) as a flaming shooting star (slot 41's Meteor Strike frames)
  at meteor_speed for meteor_frames: nothing hurts him (the post-hit blink's rule, without the flicker) and he attacks
  everything he touches. Then he falls in his ball. Landing or a wall ends it early.
- Jump / roll: his own Spin/Roll frames (his art). No other mid-air move.

noswapAbility (S1/S2; the DLL's and CD's own state follow the same numbers):
  1..grab_frames        the arms going out (the step)
  101..                 caught terrain: pulled in (frames + 100)
  201..200+retract      the arms coming back (frames left + 200)
  301..                 caught a badnik: yanked in (frames + 300)
  1000 + h / 2000 + h   hanging on a wall / under a ceiling (h: frames jump has been held since a press, 0 none)
  3000 + left           the Meteor Strike (frames left)
NoSwap_grappleX / Y: the point caught (16.16). NoSwap_grappleDir: the aim (0 right, 1 up-right, 2 up, 3 up-left, 4 left,
5 down-left, 6 down, 7 down-right: the hands' frames too), or while hanging on a wall its side (FACING_RIGHT / LEFT).
"""
import re
import sys

# the aim's unit vector (x256), per direction
UX = [256, 181, 0, -181, -256, -181, 0, 181]
UY = [0, -181, -256, -181, 0, 181, 256, 181]
# the d-pad's (x + 1) + 3 * (y + 1) -> direction (4: nothing held, filled in by the facing)
DIR_OF = [3, 2, 1, 4, 0, 0, 5, 6, 7]
# the aim class of a direction (slot 41's frames per class: 0 forward, 1 forward-up, 2 up, 3 forward-down, 4 down)
CLASS = [0, 1, 2, 1, 0, 3, 4, 3]

REACH, PULL, RETRACT, YANK, WALL, CEILING, METEOR = 0, 100, 200, 300, 1000, 2000, 3000
# slot 41's frames: ground reach 0-4, air reach 5-9, pulled 10-14, headbutt 15, Meteor Strike 16 + 3 * class + k
F_AIR, F_PULL, F_HEADBUTT, F_METEOR = 5, 10, 15, 16
# slot 42's frames: wall 0-8, ceiling 9-17, the wind-up 18-25
F_CEILING, F_SWING = 9, 18
LADDER = 9
SWING = 8
WALL_X, CEILING_Y = 14, -24  # the tile tests beside him / above him (his box reaches 10 / 20 px)
GRIP_WALL, GRIP_CEILING = (12, -4), (0, -20)  # where he holds on (the wind-up's pivot)


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("star_grab")


def check(i):
    c = ab().ABILITIES[i]
    if c["windup_full"] >= 999 or c["meteor_frames"] >= 999 or c["grab_frames"] >= 99:
        sys.exit(f"star_grab: extra {i}: its numbers overflow its states")
    bad = [a for a in c["abilities"] if a not in ("star_grab", "physics")]
    if bad or c.get("shot") or c.get("melee_reach"):
        sys.exit(f"star_grab: extra {i}: star_grab uses noswapAbility, the grapple values and slots 41-43 alone ({bad})")
    return c


def table(name, values):
    return f"private table {name}\n\t" + ", ".join(map(str, values)) + "\nend table\n\n\n"


# ---------------------------------------------------------------- Sonic 1/2
def v4_functions(i):
    c = check(i)
    a = ab().ALIAS_OF[i]
    return (f"// [NoSwap] Ristar's moves ({a}; tools/star_grab.py): the aim's unit vectors (x256), the d-pad's direction, "
            "the aim classes\n"
            + table(f"NoSwap_StarUX{i}", UX) + table(f"NoSwap_StarUY{i}", UY)
            + table(f"NoSwap_StarDirOf{i}", DIR_OF) + table(f"NoSwap_StarClass{i}", CLASS)
            + v4_hang_function(i) + v4_draw_functions(i))


def tile(depth, x, y, out="temp3"):
    """A solid tile (floor or ceiling side) at (x, y) px from him, into `out`; his position is put back (the test moves
    him). Uses temp6 / temp7."""
    t = "\t" * depth
    return (f"{t}temp6 = player.xpos\n{t}temp7 = player.ypos\n"
            f"{t}ObjectTileCollision(CSIDE_FLOOR, {x}, {y}, player.collisionPlane)\n{t}{out} = checkResult\n"
            f"{t}player.xpos = temp6\n{t}player.ypos = temp7\n"
            f"{t}if {out} == false\n"
            f"{t}\tObjectTileCollision(CSIDE_ROOF, {x}, {y}, player.collisionPlane)\n{t}\t{out} = checkResult\n"
            f"{t}\tplayer.xpos = temp6\n{t}\tplayer.ypos = temp7\n{t}end if\n")


def v4_hang_function(i):
    """Pulled in to what the hands caught: next to a wall (the latch's side first) or under a ceiling he hangs there;
    otherwise (or on the ground) he lets go."""
    c = ab().ABILITIES[i]
    return f"""// Ristar: pulled in to what his hands caught (tools/star_grab.py): hang on a wall or a ceiling there, or let go
public function NoSwap_StarHang{i}
	player.xvel = 0
	player.yvel = 0
	player.speed = 0
	if player.gravity == GRAVITY_GROUND // on the ground: he just stands
		player.noswapAbility = 0
		player.animation = ANI_STOPPED
	else
		temp4 = FACING_RIGHT // the latch's side first
		temp5 = {WALL_X}
		if NoSwap_grappleX < player.xpos
			temp4 = FACING_LEFT
			temp5 = -{WALL_X}
		end if
{tile(2, "temp5", 0)}		if temp3 == false // the other side
			FlipSign(temp5)
			if temp4 == FACING_RIGHT
				temp4 = FACING_LEFT
			else
				temp4 = FACING_RIGHT
			end if
{tile(3, "temp5", 0)}		end if
		if temp3 == true
			player.noswapAbility = {WALL}
			NoSwap_grappleDir = temp4
			player.direction = temp4
		else
{tile(3, 0, CEILING_Y)}			if temp3 == true
				player.noswapAbility = {CEILING}
			else // nothing to hold on to: let go with a hop
				player.noswapAbility = 0
				player.yvel = -{c['hang_hop']:#x}
				player.timer = 0
				player.animation = ANI_JUMPING
			end if
		end if
	end if
end function


"""


def v4_air(i):
    """In the air state, before he moves (after its gravity): the velocities of the pull, the yank, the hang and the
    Meteor Strike, and no falling while the arms are out."""
    c = ab().ABILITIES[i]
    return f"""if player.noswapAbility > 0
	temp0 = player.noswapAbility
	if temp0 < {PULL} // the arms out: he stops falling
		if player.yvel > 0
			player.yvel = 0
		end if
	end if
	if temp0 > {RETRACT}
		if temp0 < {YANK} // coming back: likewise
			if player.yvel > 0
				player.yvel = 0
			end if
		end if
	end if
	temp1 = 0 // pulled along the line to the point caught, at this speed
	if temp0 > {PULL}
		if temp0 < {RETRACT}
			temp1 = {c['reel_speed'] >> 8:#x}
		end if
	end if
	if temp0 > {YANK}
		if temp0 < {WALL}
			temp1 = {c['yank_speed'] >> 8:#x}
		end if
	end if
	if temp1 > 0
		temp2 = NoSwap_grappleX
		temp2 -= player.xpos
		temp3 = NoSwap_grappleY
		temp3 -= player.ypos
		ATan2(temp4, temp2, temp3)
		Cos256(player.xvel, temp4)
		player.xvel *= temp1
		Sin256(player.yvel, temp4)
		player.yvel *= temp1
		player.speed = player.xvel
	end if
	if temp0 >= {WALL}
		if temp0 < {METEOR} // hanging: held still; up / down climb a wall, left / right move along a ceiling
			player.xvel = 0
			player.yvel = 0
			player.speed = 0
			temp1 = temp0
			temp1 %= 1000
			if temp1 == 0 // (not while jump is held: the wind-up)
				if temp0 < {CEILING}
					if player.up == true
						player.yvel = -{c['climb_speed']:#x}
					end if
					if player.down == true
						player.yvel = {c['climb_speed']:#x}
					end if
				else
					if player.left == true
						player.xvel = -{c['climb_speed']:#x}
					end if
					if player.right == true
						player.xvel = {c['climb_speed']:#x}
					end if
					player.speed = player.xvel
				end if
			end if
		else // the Meteor Strike: straight on at meteor_speed
			GetTableValue(player.xvel, NoSwap_grappleDir, NoSwap_StarUX{i})
			player.xvel *= {c['meteor_speed'] >> 8:#x}
			GetTableValue(player.yvel, NoSwap_grappleDir, NoSwap_StarUY{i})
			player.yvel *= {c['meteor_speed'] >> 8:#x}
			player.speed = player.xvel
		end if
	end if
end if
"""


def v4_start(i):
    """Y (in the ground or air states, not hurt): the Grab, aimed with the d-pad."""
    c = ab().ABILITIES[i]
    return f"""if keyPress[1].buttonY != false // Ristar's Grab (tools/star_grab.py)
	temp0 = false
	if player.noswapAbility <= 0
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
	end if
	if temp0 == true
		temp1 = 1 // x + 1
		if player.left == true
			temp1 = 0
		end if
		if player.right == true
			temp1 = 2
		end if
		temp2 = 1 // y + 1
		if player.up == true
			temp2 = 0
		end if
		if player.down == true
			if player.gravity != GRAVITY_GROUND // (on the ground, down doesn't aim)
				temp2 = 2
			end if
		end if
		if temp1 == 1
			if temp2 == 1 // nothing held: forward
				temp1 = 2
				if player.direction == FACING_LEFT
					temp1 = 0
				end if
			end if
		end if
		if temp1 == 0
			player.direction = FACING_LEFT
		end if
		if temp1 == 2
			player.direction = FACING_RIGHT
		end if
		temp2 *= 3
		temp1 += temp2
		GetTableValue(NoSwap_grappleDir, temp1, NoSwap_StarDirOf{i})
		player.noswapAbility = 1
		PlaySfx(SfxName[{c['grab_sfx']}], false)
	end if
end if
"""


def v4_after(i):
    """After the player has moved: the Grab's start, the arms (reach, terrain test, frames, hitbox), the pull, the yank
    and headbutt, the hang (climbing, letting go, the wind-up) and the Meteor Strike."""
    c = ab().ABILITIES[i]
    n = c["grab_frames"]
    step = c["grab_step"]
    return v4_start(i) + f"""if player.noswapAbility > 0
	temp0 = false // interrupted?
	CheckEqual(player.animation, ANI_HURT)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_DYING)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_DROWNING)
	temp0 |= checkResult
	temp1 = false
	CheckEqual(player.state, Player_State_Ground)
	temp1 |= checkResult
	CheckEqual(player.state, Player_State_Air)
	temp1 |= checkResult
	CheckEqual(player.state, Player_State_Air_NoDropDash)
	temp1 |= checkResult
	CheckEqual(player.state, Player_State_RollJump)
	temp1 |= checkResult
	if temp1 == false // a spring, a tube, an object taking over...
		temp0 = true
	end if
	if temp0 == true
		player.noswapAbility = 0
	end if
end if
player.hitboxTop = C_BOX
player.hitboxBottom = C_BOX
player.hitboxLeft = C_BOX
player.hitboxRight = C_BOX
temp0 = player.noswapAbility
if temp0 > 0
	if temp0 < {PULL} // the arms going out: does the tip reach solid terrain?
		temp4 = temp0
		temp4 *= {step}
		GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarUX{i})
		temp1 *= temp4
		temp1 /= 256
		GetTableValue(temp2, NoSwap_grappleDir, NoSwap_StarUY{i})
		temp2 *= temp4
		temp2 /= 256
		NoSwap_grappleX = temp1 // the hands' place (Sonic CD's badniks test it: tools/star_grab.py cd_touch)
		NoSwap_grappleX <<= 16
		NoSwap_grappleX += player.xpos
		NoSwap_grappleY = temp2
		NoSwap_grappleY <<= 16
		NoSwap_grappleY += player.ypos
		temp6 = player.xpos
		temp7 = player.ypos
		ObjectTileCollision(CSIDE_FLOOR, temp1, temp2, player.collisionPlane)
		temp3 = checkResult
		player.xpos = temp6
		player.ypos = temp7
		if temp3 == false
			ObjectTileCollision(CSIDE_ROOF, temp1, temp2, player.collisionPlane)
			temp3 = checkResult
			player.xpos = temp6
			player.ypos = temp7
		end if
		if temp3 == true // caught: pulled in
			player.noswapAbility = {PULL + 1}
			PlaySfx(SfxName[{c['latch_sfx']}], false)
		else
			player.noswapAbility++
			if player.noswapAbility > {n} // full reach, nothing there: back
				player.noswapAbility = {RETRACT + c['retract_frames']}
			end if
			// the hitbox (only enemies, monitors and bosses use it) out to the hands
			temp3 = temp1
			temp3 -= 8
			if temp3 > -10
				temp3 = -10
			end if
			player.hitboxLeft = temp3
			temp1 += 8
			if temp1 < 10
				temp1 = 10
			end if
			player.hitboxRight = temp1
			temp3 = temp2
			temp3 -= 8
			if temp3 > -20
				temp3 = -20
			end if
			player.hitboxTop = temp3
			temp2 += 8
			if temp2 < 20
				temp2 = 20
			end if
			player.hitboxBottom = temp2
		end if
		if player.gravity == GRAVITY_GROUND // he stands still for it
			player.speed = 0
			player.xvel = 0
		end if
	else
		if temp0 < {RETRACT} // pulled in: there yet?
			CallFunction(NoSwap_StarTo{i})
			temp1 = false
			if temp4 < {c['latch_range']}
				if temp5 < {c['latch_range']}
					temp1 = true
				end if
			end if
			if temp0 >= {PULL + c['reel_frames']}
				temp1 = true
			end if
			if temp0 > {PULL + 2}
				if player.gravity == GRAVITY_GROUND
					if player.speed == 0 // against a wall
						temp1 = true
					end if
				else
					if player.xvel == 0
						if player.yvel == 0 // stopped by the terrain
							temp1 = true
						end if
					end if
				end if
			end if
			if temp1 == true
				CallFunction(NoSwap_StarHang{i})
			else
				player.noswapAbility++
				temp1 = {c['reel_speed']:#x}
				CallFunction(NoSwap_StarPullGround{i})
			end if
		else
			if temp0 < {YANK} // the arms coming back
				player.noswapAbility--
				if player.noswapAbility == {RETRACT}
					player.noswapAbility = 0
					if player.gravity == GRAVITY_GROUND
						player.animation = ANI_STOPPED
					else
						player.animation = ANI_JUMPING
					end if
				end if
				if player.gravity == GRAVITY_GROUND
					player.speed = 0
					player.xvel = 0
				end if
			else
				if temp0 < {WALL} // yanked in to the badnik: close enough, a bounce off it
					CallFunction(NoSwap_StarTo{i})
					temp1 = false
					if temp4 < {c['yank_range']}
						if temp5 < {c['yank_range']}
							temp1 = true
						end if
					end if
					if temp0 >= {YANK + c['yank_frames']}
						temp1 = true
					end if
					if temp1 == true
						player.noswapAbility = 0
						player.state = Player_State_Air
						player.gravity = GRAVITY_AIR
						player.yvel = -{c['bounce_y']:#x}
						player.xvel = -{c['bounce_x']:#x}
						if player.direction == FACING_LEFT
							FlipSign(player.xvel)
						end if
						player.speed = player.xvel
						player.timer = 0
						player.animation = ANI_JUMPING
					else
						player.noswapAbility++
						temp1 = {c['yank_speed']:#x}
						CallFunction(NoSwap_StarPullGround{i})
					end if
				else
					if temp0 < {METEOR}
						CallFunction(NoSwap_StarHangUpdate{i})
					else
						CallFunction(NoSwap_StarMeteor{i})
					end if
				end if
			end if
		end if
	end if
end if
""" + v4_frame(i)


def v4_frame(i):
    """Slot 41 / 42's frame for the state (the code picks it), and his facing."""
    return f"""temp0 = player.noswapAbility
if temp0 > 0
	if temp0 < {WALL}
		player.animation = ANI_NOSWAP_ATTACK
		GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarClass{i})
		if temp0 > {YANK}
			temp1 += {F_PULL}
			if temp4 < 32
				if temp5 < 32
					temp1 = {F_HEADBUTT}
				end if
			end if
		else
			if temp0 > {PULL}
				if temp0 < {RETRACT}
					temp1 += {F_PULL}
				end if
			end if
			if temp0 < {PULL}
				if player.gravity != GRAVITY_GROUND
					temp1 += {F_AIR}
				end if
			end if
			if temp0 > {RETRACT}
				if player.gravity != GRAVITY_GROUND
					temp1 += {F_AIR}
				end if
			end if
		end if
		player.frame = temp1
		GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarUX{i}) // facing the aim
		if temp1 > 0
			player.direction = FACING_RIGHT
		end if
		if temp1 < 0
			player.direction = FACING_LEFT
		end if
		player.prevAnimation = player.animation // (the code picks the frame, not the animation speed)
		player.animationTimer = 0
	end if
end if
"""


def v4_hang_update(i):
    """Hanging: still attached (a wall beside him, a ceiling above), landed, climbing past a wall's top, jump (a press
    and release: let go; held windup_full frames: the Meteor Strike), and the frames."""
    c = ab().ABILITIES[i]
    return f"""// Ristar: hanging on a wall or under a ceiling (tools/star_grab.py)
public function NoSwap_StarHangUpdate{i}
	temp0 = player.noswapAbility
	temp1 = temp0
	temp1 %= 1000 // jump held (0: not pressed)
	temp0 -= temp1 // the kind: WALL or CEILING
	temp2 = {WALL_X}
	if NoSwap_grappleDir == FACING_LEFT
		temp2 = -{WALL_X}
	end if
	if player.gravity == GRAVITY_GROUND // down onto the floor
		player.noswapAbility = 0
		player.animation = ANI_STOPPED
	else
		if temp0 == {WALL}
{tile(3, "temp2", 0)}			player.direction = NoSwap_grappleDir
		else
{tile(3, 0, CEILING_Y)}		end if
		if temp3 == false // nothing to hold any more
			player.noswapAbility = 0
			player.animation = ANI_JUMPING
			if temp0 == {WALL}
				if player.up == true // climbed past the top: a hop onto the ledge
					player.yvel = -{c['hang_hop']:#x}
					player.xvel = {c['hang_push'] // 2:#x}
					if NoSwap_grappleDir == FACING_LEFT
						FlipSign(player.xvel)
					end if
					player.speed = player.xvel
					player.timer = 0
				end if
			end if
		else
			if player.jumpPress == true
				if temp1 == 0
					temp1 = 1
				end if
			end if
			if temp1 > 0
				if player.jumpHold == true
					if temp1 < 999
						temp1++
					end if
				else // let go of jump
					if temp1 >= {c['windup_full']} // the Meteor Strike
						CallFunction(NoSwap_StarLaunch{i})
						temp0 = {METEOR}
						temp1 = {c['meteor_frames']}
					else // a hop off (down held: he just drops)
						player.yvel = -{c['hang_hop']:#x}
						if player.up == false
							if player.down == true
								player.yvel = 0
							end if
						end if
						player.xvel = 0
						if temp0 == {WALL} // away from a wall
							player.xvel = {c['hang_push']:#x}
							if NoSwap_grappleDir == FACING_RIGHT
								FlipSign(player.xvel)
							end if
						end if
						player.speed = player.xvel
						temp0 = 0
						temp1 = 0
						player.animation = ANI_JUMPING
						player.timer = 0
					end if
				end if
			end if
			player.noswapAbility = temp0
			player.noswapAbility += temp1
			if temp0 >= {WALL}
				if temp0 < {METEOR} // the frames: climbing (by his height), moving along (by where he is), the wind-up
					player.animation = ANI_NOSWAP_HOVER
					player.prevAnimation = player.animation
					player.animationTimer = 0
					if temp1 >= {c['windup_show']}
						temp2 = temp1
						if temp1 < {c['windup_full']}
							temp2 >>= 2
						else
							temp2 >>= 1
						end if
						temp2 %= {SWING}
						temp2 += {F_SWING}
					else
						if temp0 == {WALL}
							temp2 = player.iypos
						else
							temp2 = player.ixpos
						end if
						temp2 >>= 3
						temp2 %= {LADDER}
						if temp2 < 0
							temp2 += {LADDER}
						end if
						if temp0 == {CEILING}
							temp2 += {F_CEILING}
						end if
					end if
					player.frame = temp2
				end if
			end if
		end if
	end if
end function


// Ristar: the Meteor Strike's launch, where the d-pad points (nothing held: away from a wall, or the way he faces)
public function NoSwap_StarLaunch{i}
	temp4 = 1 // x + 1
	if player.left == true
		temp4 = 0
	end if
	if player.right == true
		temp4 = 2
	end if
	temp5 = 1 // y + 1
	if player.up == true
		temp5 = 0
	end if
	if player.down == true
		temp5 = 2
	end if
	if temp4 == 1
		if temp5 == 1
			temp4 = 2
			if player.direction == FACING_LEFT
				temp4 = 0
			end if
			if temp0 == {WALL} // away from the wall
				temp4 = 0
				if NoSwap_grappleDir == FACING_LEFT
					temp4 = 2
				end if
			end if
		end if
	end if
	temp5 *= 3
	temp4 += temp5
	GetTableValue(NoSwap_grappleDir, temp4, NoSwap_StarDirOf{i})
	player.animation = ANI_NOSWAP_ATTACK
	player.timer = 0
	PlaySfx(SfxName[{c['meteor_sfx']}], false)
end function


// Ristar: the Meteor Strike (tools/star_grab.py): nothing hurts him, the frames; landing, a wall or time ends it
public function NoSwap_StarMeteor{i}
	temp0 = player.noswapAbility
	temp0 -= {METEOR} // frames left
	temp1 = false
	if player.gravity == GRAVITY_GROUND
		temp1 = true
	end if
	if temp0 < {c['meteor_frames'] - 1}
		if player.xvel == 0
			if player.yvel == 0 // stopped by a wall or a ceiling
				temp1 = true
			end if
		end if
	end if
	temp0--
	if temp0 <= 0
		temp1 = true
	end if
	if temp1 == true
		player.noswapAbility = 0
		if player.gravity == GRAVITY_GROUND
			player.animation = ANI_WALKING
		else
			player.animation = ANI_JUMPING
		end if
	else
		player.noswapAbility = {METEOR}
		player.noswapAbility += temp0
		if player.blinkTimer < 3 // nothing hurts him (the post-hit blink's rule; under 4, so he doesn't flicker)
			player.blinkTimer = 3
		end if
		player.animation = ANI_NOSWAP_ATTACK
		player.prevAnimation = player.animation
		player.animationTimer = 0
		GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarClass{i})
		temp1 *= 3
		temp1 += {F_METEOR}
		temp2 = temp0
		temp2 >>= 2
		temp2 %= 3
		temp1 += temp2
		player.frame = temp1
		GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarUX{i})
		if temp1 > 0
			player.direction = FACING_RIGHT
		end if
		if temp1 < 0
			player.direction = FACING_LEFT
		end if
	end if
end function


// Ristar: pulled or yanked while on the ground: a point well above lifts him off (the air state pulls him from next
// frame); otherwise he's drawn along the ground to it
public function NoSwap_StarPullGround{i}
	if player.gravity == GRAVITY_GROUND
		CallFunction(NoSwap_StarTo{i})
		if temp3 < -12
			player.state = Player_State_Air
			player.gravity = GRAVITY_AIR
			player.yvel = -0x10000
			player.xvel = 0
			player.speed = 0
		else
			player.speed = temp1
			if temp2 < 0
				FlipSign(player.speed)
			end if
			player.xvel = player.speed
		end if
	end if
end function


// Ristar: how far the point caught is (temp4, temp5: px across and down, both positive; temp2, temp3 signed)
public function NoSwap_StarTo{i}
	temp2 = NoSwap_grappleX
	temp2 -= player.xpos
	temp2 >>= 16
	temp3 = NoSwap_grappleY
	temp3 -= player.ypos
	temp3 >>= 16
	temp4 = temp2
	if temp4 < 0
		FlipSign(temp4)
	end if
	temp5 = temp3
	if temp5 < 0
		FlipSign(temp5)
	end if
end function


"""


def v4_draw_functions(i):
    """His draw (ObjectDraw calls NoSwap_StarDraw<i> instead of DrawObjectAnimation): the body (the wind-up's swing
    frame drawn at his grip), then the arms (DrawRect, 2 px squares along two lines 3 px either side of the aim) and
    the hands (slot 43's frame for the aim, open or gripping, drawn facing right: its frames are absolute)."""
    c = ab().ABILITIES[i]
    n, step, back = c["grab_frames"], c["grab_step"], c["retract_frames"]
    gx, gy = GRIP_WALL
    return v4_hang_update(i) + f"""// Ristar's arms: from his centre to (temp0, temp1) px, two 2 px black lines (the game's own are vector lines too).
// Leaves the lines' offset from the aim in temp3 / temp4 (px) for the hands
public function NoSwap_StarArms{i}
	temp2 = temp0 // the steps: the longer axis
	if temp2 < 0
		FlipSign(temp2)
	end if
	temp5 = temp1
	if temp5 < 0
		FlipSign(temp5)
	end if
	if temp5 > temp2
		temp2 = temp5
	end if
	if temp2 < 1
		temp2 = 1
	end if
	temp3 = temp1 // the offset: 3 px across the aim
	FlipSign(temp3)
	temp3 *= 3
	temp3 /= temp2
	temp4 = temp0
	temp4 *= 3
	temp4 /= temp2
	temp5 = 0
	while temp5 < temp2
		temp6 = temp0
		temp6 *= temp5
		temp6 /= temp2
		temp6 += player.ixpos
		temp6 -= screen.xoffset
		temp6 += temp3
		temp6--
		temp7 = temp1
		temp7 *= temp5
		temp7 /= temp2
		temp7 += player.iypos
		temp7 -= screen.yoffset
		temp7 += temp4
		temp7--
		DrawRect(temp6, temp7, 2, 2, 0, 0, 0, 255)
		temp6 -= temp3
		temp6 -= temp3
		temp7 -= temp4
		temp7 -= temp4
		DrawRect(temp6, temp7, 2, 2, 0, 0, 0, 255)
		temp5++
	loop
end function


// Ristar's hands at the arms' ends (temp0, temp1 px from his centre, temp3 / temp4 the lines' offset), frame temp2
public function NoSwap_StarHands{i}
	temp5 = player.animation
	temp6 = player.frame
	temp7 = player.direction
	player.animation = {ab().ANI_MELEE}
	player.frame = temp2
	player.direction = FACING_RIGHT
	temp0 += temp3
	temp0 *= 0x10000
	temp1 += temp4
	temp1 *= 0x10000
	player.xpos += temp0
	player.ypos += temp1
	DrawObjectAnimation()
	temp3 *= 0x20000
	temp4 *= 0x20000
	player.xpos -= temp3
	player.ypos -= temp4
	DrawObjectAnimation()
	player.xpos += temp3
	player.ypos += temp4
	player.xpos -= temp0
	player.ypos -= temp1
	player.animation = temp5
	player.frame = temp6
	player.direction = temp7
end function


// Ristar's draw (tools/star_grab.py): his body (in the wind-up, the swing frame round his grip), his arms and hands
public function NoSwap_StarDraw{i}
	temp0 = false // the wind-up: drawn round his grip
	if player.animation == ANI_NOSWAP_HOVER
		if player.frame >= {F_SWING}
			temp0 = true
		end if
	end if
	if temp0 == true
		temp1 = {gx}
		temp2 = {gy}
		temp3 = FACING_LEFT // the body swings out on the side away from the wall
		if player.noswapAbility >= {CEILING}
			temp1 = {GRIP_CEILING[0]}
			temp2 = {GRIP_CEILING[1]}
			temp3 = player.direction
		else
			if NoSwap_grappleDir == FACING_LEFT
				FlipSign(temp1)
				temp3 = FACING_RIGHT
			end if
		end if
		temp1 *= 0x10000
		temp2 *= 0x10000
		temp4 = player.direction
		player.xpos += temp1
		player.ypos += temp2
		player.direction = temp3
		DrawObjectAnimation()
		player.direction = temp4
		player.xpos -= temp1
		player.ypos -= temp2
	else
		DrawObjectAnimation()
	end if
	temp7 = player.noswapAbility
	if temp7 > 0
		if temp7 < {WALL}
			temp2 = -1 // the arms' length (px along the aim), or -1: out to the point caught
			if temp7 < {PULL}
				temp2 = temp7
				temp2 *= {step}
			end if
			if temp7 > {RETRACT}
				if temp7 < {YANK}
					temp2 = temp7
					temp2 -= {RETRACT}
					temp2 *= {n * step // back}
				end if
			end if
			if temp2 < 0
				temp0 = NoSwap_grappleX
				temp0 -= player.xpos
				temp0 >>= 16
				temp1 = NoSwap_grappleY
				temp1 -= player.ypos
				temp1 >>= 16
			else
				GetTableValue(temp0, NoSwap_grappleDir, NoSwap_StarUX{i})
				temp0 *= temp2
				temp0 /= 256
				GetTableValue(temp1, NoSwap_grappleDir, NoSwap_StarUY{i})
				temp1 *= temp2
				temp1 /= 256
			end if
			CallFunction(NoSwap_StarArms{i})
			temp2 = NoSwap_grappleDir // the hands: open, or gripping what they caught (+ 8)
			temp5 = player.noswapAbility
			if temp5 > {PULL}
				if temp5 < {RETRACT}
					temp2 += 8
				end if
				if temp5 > {YANK}
					temp2 += 8
				end if
			end if
			CallFunction(NoSwap_StarHands{i})
		end if
	end if
end function


"""


def v4_patch(t):
    """Player_BadnikBreak: while his arms are out, a badnik they (or he) touch is caught, not broken: he's yanked in to
    it (its place, NoSwap_grappleX / Y) to headbutt it. ObjectDraw: his draw is NoSwap_StarDraw<i>."""
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "public function Player_BadnikBreak\n"
        if t.count(head) != 1:
            sys.exit("star_grab: Player_BadnikBreak isn't there once")
        t = t.replace(head, head + f"""	if stage.playerListPos == {a} // [NoSwap] Ristar's Grab (tools/star_grab.py): his hands catch it
		if player[currentPlayer].noswapAbility > 0
			if player[currentPlayer].noswapAbility < {PULL}
				NoSwap_grappleX = object.xpos
				NoSwap_grappleY = object.ypos
				player[currentPlayer].noswapAbility = {YANK + 1}
				PlaySfx(SfxName[{ab().ABILITIES[i]['latch_sfx']}], false)
				return
			end if
		end if
	end if
""")
        start = t.index("event ObjectDraw\n")
        end = t.index("end event\n", start)
        draw = t[start:end]
        if draw.count("\tDrawObjectAnimation()\n") != 1:
            sys.exit("star_grab: expected 1 DrawObjectAnimation in ObjectDraw")
        draw = draw.replace("\tDrawObjectAnimation()\n",
                            f"\tif stage.playerListPos == {a} // [NoSwap] Ristar: his arms and hands (tools/star_grab.py)\n"
                            f"\t\tCallFunction(NoSwap_StarDraw{i})\n\telse\n\t\tDrawObjectAnimation()\n\tend if\n")
        t = t[:start] + draw + t[end:]
        # every one of his functions reserved up front: the v4 compiler only knows a function called before its
        # definition if it's reserved (NoSwap_StarLaunch<i>, called from his hang update, crashed the stage load:
        # "Operand not found", the user, 2026-09-29)
        names = re.findall(rf"^public function (NoSwap_Star\w*{i})$", t, flags=re.M)
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("star_grab: the script's reserve block isn't there once")
        t = t.replace(anchor, "".join(f"reserve function {n}\n" for n in names) + anchor)
    return t


# ---------------------------------------------------------------- Sonic CD
# The same code, turned into CD's v3 dialect (to_v3): CD has no tables (the aim's vectors come from Cos256 / Sin256 of the
# direction's angle, the other lookups are switches), no player hitbox to widen, and one player. His state is
# NoSwap.Star (Object[5].Value1, NoSwap.Pogo's value: he has no pogo, and NoSwap.Ability is reset on the ground every
# frame); the point caught and the aim are NoSwap.GrappleX / GrappleY / GrappleDir (Object[5].Value4-6). Y comes from
# the DLL (game.callbackParam3 == 1, build_soniccd.Y_REARM). His hands catch badniks, monitors and bosses through
# NoSwap_ShotTouch, which every one of them calls when the player isn't touching it (tools/shots_v3.py): while his arms
# are out, a hand (NoSwap.GrappleX / GrappleY, where the reach put it this frame) inside its box latches onto it.
CD_ALIAS = ("#alias Object[5].Value1 : NoSwap.Star // [NoSwap] Ristar's Grab / hang / Meteor Strike state (tools/star_grab.py; "
            "NoSwap.Pogo's value: never with the pogo)\n")
CD_HANDS = 46  # slot 43 in CD (cd_config.ABILITY_SLOTS)
V3_NAMES = [
    ("player.noswapAbility", "NoSwap.Star"), ("NoSwap_grappleX", "NoSwap.GrappleX"), ("NoSwap_grappleY", "NoSwap.GrappleY"),
    ("NoSwap_grappleDir", "NoSwap.GrappleDir"), ("player.xpos", "Player.XPos"), ("player.ypos", "Player.YPos"),
    ("player.ixpos", "Player.iXPos"), ("player.iypos", "Player.iYPos"), ("player.xvel", "Player.XVelocity"),
    ("player.yvel", "Player.YVelocity"), ("player.speed", "Player.Speed"), ("player.gravity", "Player.Gravity"),
    ("player.state", "Player.State"), ("player.prevAnimation", "Player.PrevAnimation"),
    ("player.animationTimer", "Player.AnimationTimer"), ("player.animation", "Player.Animation"),
    ("player.frame", "Player.Frame"), ("player.direction", "Player.Direction"), ("player.up", "Player.Up"),
    ("player.down", "Player.Down"), ("player.left", "Player.Left"), ("player.right", "Player.Right"),
    ("player.jumpPress", "Player.JumpPress"), ("player.jumpHold", "Player.JumpHold"), ("player.timer", "Player.Timer"),
    ("player.blinkTimer", "Player.InvincibleTimer"), ("player.collisionPlane", "Player.CollisionPlane"),
    ("screen.xoffset", "Screen.XOffset"), ("screen.yoffset", "Screen.YOffset"), ("checkResult", "CheckResult"),
    ("DrawObjectAnimation()", "DrawPlayerAnimation()"), ("public function ", "function "),
]


def to_v3(text, i):
    import re
    c = ab().ABILITIES[i]
    sfx = {c["grab_sfx"]: c["grab_sfx_cd"], c["latch_sfx"]: c["latch_sfx_cd"], c["meteor_sfx"]: c["meteor_sfx_cd"]}
    out = []

    def rename(line):
        for a, b in V3_NAMES:
            line = line.replace(a, b)
        line = re.sub(r"\btemp(\d)\b", r"TempValue\1", line)
        line = re.sub(r"SfxName\[([^\]]+)\]", lambda mm: sfx[mm.group(1)], line)
        return line.replace(f"Player.Animation = {ab().ANI_MELEE}", f"Player.Animation = {CD_HANDS}")
    lines = text.split("\n")
    k = 0
    while k < len(lines):
        line = lines[k]
        k += 1
        if line.startswith("private table "):  # (no tables in v3: the lookups below)
            while not lines[k].startswith("end table"):
                k += 1
            k += 1
            continue
        ind = line[:len(line) - len(line.lstrip("\t"))]
        code = line.strip()
        if "hitbox" in code:  # (CD: no player hitbox to widen; the hands test in NoSwap_ShotTouch)
            continue
        m = re.match(r"GetTableValue\(([\w.\[\]]+), ([\w.]+), NoSwap_Star(UX|UY|DirOf|Class)\d+\)", code)
        if m:
            dest, idx, name = m.groups()
            if name in ("UX", "UY"):
                dest, idx = rename(dest), rename(idx)
                out += [f"{ind}{dest} = {idx}", f"{ind}{dest} *= 32",
                        f"{ind}{'Cos256' if name == 'UX' else 'Sin256'}({dest}, {dest})"]
                if name == "UY":
                    out.append(f"{ind}FlipSign({dest})")
            else:
                dest, idx = rename(dest), rename(idx)
                values = DIR_OF if name == "DirOf" else CLASS
                out.append(f"{ind}switch {idx}")
                for v in sorted(set(values)):
                    out += [f"{ind}case {n}" for n, x in enumerate(values) if x == v]
                    out += [f"{ind}\t{dest} = {v}", f"{ind}\tbreak"]
                out.append(f"{ind}end switch")
            continue
        if code.startswith("ObjectTileCollision("):  # (CD: tested on a stand-in, Object, as the Ear Grapple does)
            out += [f"{ind}Object.XPos = Player.XPos", f"{ind}Object.YPos = Player.YPos", f"{ind}CheckResult = false"]
        line = {"temp6 = player.xpos": f"{ind}temp6 = Object.XPos", "temp7 = player.ypos": f"{ind}temp7 = Object.YPos",
                "player.xpos = temp6": f"{ind}Object.XPos = temp6", "player.ypos = temp7": f"{ind}Object.YPos = temp7"
                }.get(code.split(" //")[0], line)
        if code.startswith("if keyPress[1].buttonY != false"):
            line = f"{ind}if game.callbackParam3 == 1 // Y, from the DLL (Ristar's Grab)"
        out.append(rename(line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_grapple", "GetTableValue", "keyPress", "SfxName", "^="):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"star_grab: the CD code still has {bad!r}")
    return text


def cd_after(i):
    """NoSwap_AfterUpdate's Ristar block: the Grab's start (and Y re-armed for the DLL), the move, the frames."""
    import build_soniccd
    rearm = "".join(l + "\n" for l in build_soniccd.Y_REARM)
    return to_v3(v4_start(i), i) + rearm + to_v3(v4_after(i)[len(v4_start(i)):], i)


def cd_touch(i):
    """NoSwap_ShotTouch's Ristar part (Object: the badnik, monitor or boss; Object[10].Value0-3 its box, 16.16 from it):
    while his arms go out, a hand (8 px round NoSwap.GrappleX / GrappleY) inside its box catches it: he's yanked in (the
    box's owner's place), and his body's touch does the rest. Only TempValue0 (NoSwap_ShotTouch saved it)."""
    c = ab().ABILITIES[i]
    a = ab().ALIAS_OF[i]
    return f"""	if Stage.PlayerListPos == {a} // [NoSwap] Ristar's hands catch it (tools/star_grab.py cd_touch)
		if NoSwap.Star > 0
			if NoSwap.Star < {PULL}
				TempValue0 = NoSwap.GrappleX
				TempValue0 -= Object.XPos
				TempValue0 += 0x80000
				if TempValue0 > Object[10].Value0
					TempValue0 -= 0x100000
					if TempValue0 < Object[10].Value2
						TempValue0 = NoSwap.GrappleY
						TempValue0 -= Object.YPos
						TempValue0 += 0x80000
						if TempValue0 > Object[10].Value1
							TempValue0 -= 0x100000
							if TempValue0 < Object[10].Value3
								NoSwap.GrappleX = Object.XPos
								NoSwap.GrappleY = Object.YPos
								NoSwap.Star = {YANK + 1}
								PlaySfx({c['latch_sfx_cd']}, false)
							end if
						end if
					end if
				end if
			end if
		end if
	end if
"""


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object): his alias, functions, air and after blocks, the hands'
    test in NoSwap_ShotTouch and his draw."""
    import re
    for i in ids():
        a = ab().ALIAS_OF[i]
        check(i)
        head = "#alias 5\t:\tPLAYER_AMY_A\n"
        if t.count(head) != 1:
            sys.exit("star_grab: CD's Amy alias isn't there once")
        t = t.replace(head, head + CD_ALIAS)
        fns = to_v3(v4_functions(i), i)
        decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"star_grab: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        for fn, body in (("NoSwap_AirAbilities", to_v3(v4_air(i), i)), ("NoSwap_AfterUpdate", cd_after(i))):
            head = f"\nfunction {fn}\n"
            if t.count(head) != 1:
                sys.exit(f"star_grab: CD's {fn} isn't there once")
            block = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] Ristar (tools/star_grab.py)\n"
                     + "".join(f"\t\t{l}\n" if l.strip() else "\n" for l in body.rstrip("\n").split("\n")) + "\tend if\n")
            t = t.replace(head, head + block)
        head = "\nfunction NoSwap_ShotTouch\n\tObject[11].Value0 = TempValue0\n\tObject[11].Value1 = ArrayPos0\n\tCheckResult = false\n"
        if t.count(head) != 1:
            sys.exit("star_grab: CD's NoSwap_ShotTouch changed")
        t = t.replace(head, head + cd_touch(i))
        start = t.index("sub ObjectDraw\n")
        end = t.index("end sub\n", start)
        draw = t[start:end]
        if draw.count("\tDrawPlayerAnimation()\n") != 1:
            sys.exit("star_grab: expected 1 DrawPlayerAnimation in CD's ObjectDraw")
        draw = draw.replace("\tDrawPlayerAnimation()\n",
                            f"\tif Stage.PlayerListPos == {a} // [NoSwap] Ristar: his arms and hands (tools/star_grab.py)\n"
                            f"\t\tCallFunction(NoSwap_StarDraw{i})\n\telse\n\t\tDrawPlayerAnimation()\n\tend if\n")
        t = t[:start] + draw + t[end:]
    return t
