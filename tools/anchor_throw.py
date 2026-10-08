"""Marine's Anchor Throw (abilities.py "anchor_throw"), for Sonic 1/2 (Retro Engine v4 player script; abilities.py calls in
here), Sonic CD (build_soniccd.py calls cd_patch) and the numbers the S3&K DLL reads (native/src/AnchorThrow.h).

The user's design (2026-09-29):
- Y (on the ground or in the air): she throws an anchor forward (the way she faces; left / right held turn her first) in
  an ARC: up at anchor_rise and forward at anchor_speed, falling back under anchor_gravity. Up + Y throws it higher
  (anchor_high_rise, anchor_high_speed). It flies anchor_frames frames at most. A chain is drawn at runtime from her hand
  to it (a 2 px dark line, as Ristar's arms are drawn: DrawRect dots in S1/S2 / CD, RSDK DrawLine in S3&K), and the anchor
  itself is the user's own drawing (slot 43 "Anchor": flukes forward, up, down; mirrored with her facing).
- It hits enemies, monitors and bosses (S1/S2: her hitbox reaches out to it, as Headdy's head; CD: NoSwap_ShotTouch;
  S3&K: Player_CheckBadnikTouch); a badnik hit sends it back.
- Solid terrain ahead of it (LEAD px past its centre) on a WALL or a CEILING side (the tile's LRB solidity: the Ear
  Grapple's test's ceiling side, so a jump-through platform never catches it) latches it: she's reeled in along the chain
  (Max's reel: reel_speed, until within latch_range, stopped by the terrain, or reel_frames), then let go with a small hop
  (grapple_hop up, grapple_forward toward it).
- Landing on a floor (moving down, the tile's floor side under it) or reaching its range: it's pulled back to her hand at
  anchor_return px a frame (the chain retracting) and gone. One out at a time; anchor_cooldown frames after it's gone.
- Meanwhile she holds her throwing pose (slot 41 "Anchor Throw", an attack, as Headdy's headless body): on the ground she
  stands still, in the air she falls as usual. A hurt, an object taking over or a new jump ends it (the anchor's gone).

noswapAbility (S1/S2; CD's NoSwap.Star, the DLL's own state, the same numbers):
  -k               the cooldown (k frames left)
  1..FLY-1         flying out (the frame number: its vertical speed is -rise + gravity * frame)
  LATCH + k        latched, reeling her in (k frames so far)
  BACK + k         coming back (k frames so far)
NoSwap_grappleX / Y: the anchor's place (16.16), or the point latched. NoSwap_grappleDir: her facing (FACING_LEFT 1) + 2 if
thrown high + 4 if latched on a ceiling.
"""
import re
import sys

FLY, LATCH, BACK = 0, 100, 200
BACK_MAX = 90  # coming back: gone after this many frames whatever happens
HAND_X, HAND_Y = 16, 4  # her open hand in the throwing pose (POINT), px from her centre facing right
LEAD = 12  # the terrain tests: this far past the anchor's centre (its drawing reaches 13-15 px)
BOX = 12  # its hit box: this far round its centre
F_FORWARD, F_UP, F_DOWN = 0, 1, 2  # slot 43's frames
CHAIN = (0x21, 0x20, 0x1D)  # the chain's colour: the anchor's outline (her #21201d)
HIGH, CEILING = 2, 4  # NoSwap_grappleDir's bits


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("anchor_throw")


def check(i):
    c = ab().ABILITIES[i]
    bad = [a for a in c["abilities"] if a not in ("anchor_throw", "water_walk", "no_breathing", "physics")]
    if bad or c.get("shot") or c.get("melee_reach"):
        sys.exit(f"anchor_throw: extra {i}: the Anchor Throw uses noswapAbility, the grapple values and slots 41 / 43 "
                 f"alone ({bad})")
    if not 0 < c["anchor_frames"] < LATCH or c["reel_frames"] >= BACK - LATCH:
        sys.exit(f"anchor_throw: extra {i}: its frames overflow its states")
    return c


# ---------------------------------------------------------------- Sonic 1/2
def v4_functions(i):
    check(i)
    return v4_pull_function(i) + v4_draw_function(i)


def tile(depth, x, y, sides, out="temp3"):
    """A solid tile at (x, y) px from her into `out`: `sides` "floor" (floor or ceiling side: anything solid from above)
    or "wall" (the ceiling side only: the tile's LRB solidity, never a jump-through platform). Her position is put back
    (the test moves her). Uses temp6 / temp7."""
    t = "\t" * depth
    out_ = (f"{t}temp6 = player.xpos\n{t}temp7 = player.ypos\n")
    if sides == "floor":
        out_ += (f"{t}ObjectTileCollision(CSIDE_FLOOR, {x}, {y}, player.collisionPlane)\n{t}{out} = checkResult\n"
                 f"{t}player.xpos = temp6\n{t}player.ypos = temp7\n{t}if {out} == false\n")
        t2 = t + "\t"
    else:
        t2 = t
    out_ += (f"{t2}ObjectTileCollision(CSIDE_ROOF, {x}, {y}, player.collisionPlane)\n{t2}{out} = checkResult\n"
             f"{t2}player.xpos = temp6\n{t2}player.ypos = temp7\n")
    if sides == "floor":
        out_ += f"{t}end if\n"
    return out_


def v4_start(i):
    """Y (in the ground or air states, not hurt, nothing out, no cooldown): the throw."""
    c = ab().ABILITIES[i]
    return f"""if keyPress[1].buttonY != false // Marine's Anchor Throw (tools/anchor_throw.py)
	temp0 = false
	if player.noswapAbility == 0
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
		if player.left == true
			player.direction = FACING_LEFT
		end if
		if player.right == true
			player.direction = FACING_RIGHT
		end if
		NoSwap_grappleDir = player.direction
		if player.up == true // up + Y: thrown higher
			NoSwap_grappleDir += {HIGH}
		end if
		NoSwap_grappleX = {HAND_X}
		if player.direction == FACING_LEFT
			FlipSign(NoSwap_grappleX)
		end if
		NoSwap_grappleX <<= 16
		NoSwap_grappleX += player.xpos
		NoSwap_grappleY = {HAND_Y}
		NoSwap_grappleY <<= 16
		NoSwap_grappleY += player.ypos
		player.noswapAbility = 1
		PlaySfx(SfxName[{c['anchor_sfx']}], false)
	end if
end if
"""


def v4_after(i):
    """After the player has moved: the throw's start, the flight (arc, terrain, range), the reel, the way back, her
    hitbox out to the anchor, the pose."""
    c = check(i)
    ceil_bit, high_bit = CEILING, HIGH
    return v4_start(i) + f"""if player.noswapAbility > 0
	temp0 = false // interrupted? (the anchor's gone)
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
if player.noswapAbility < 0 // the cooldown
	player.noswapAbility++
end if
player.hitboxTop = C_BOX
player.hitboxBottom = C_BOX
player.hitboxLeft = C_BOX
player.hitboxRight = C_BOX
temp0 = player.noswapAbility
if temp0 > 0
	if temp0 < {LATCH} // flying: the arc (its speeds from the frame number)
		temp1 = {c['anchor_speed']:#x}
		temp2 = -{c['anchor_rise']:#x}
		temp3 = NoSwap_grappleDir
		temp3 &= {high_bit}
		if temp3 != 0 // thrown high
			temp1 = {c['anchor_high_speed']:#x}
			temp2 = -{c['anchor_high_rise']:#x}
		end if
		temp3 = NoSwap_grappleDir
		temp3 &= 1
		if temp3 == FACING_LEFT
			FlipSign(temp1)
		end if
		temp3 = temp0
		temp3 *= {c['anchor_gravity']:#x}
		temp2 += temp3
		NoSwap_grappleX += temp1
		NoSwap_grappleY += temp2
		temp4 = NoSwap_grappleX // its place, px from her
		temp4 -= player.xpos
		temp4 >>= 16
		temp5 = NoSwap_grappleY
		temp5 -= player.ypos
		temp5 >>= 16
		temp0 = 0 // what it met: 1 a floor, 2 a wall, 3 a ceiling
		if temp2 >= 0 // falling: a floor under it
			temp1 = temp5
			temp1 += {LEAD}
{tile(3, "temp4", "temp1", "floor")}			if temp3 == true
				temp0 = 1
			end if
		end if
		if temp0 == 0 // a wall ahead of it
			temp1 = {LEAD}
			temp3 = NoSwap_grappleDir
			temp3 &= 1
			if temp3 == FACING_LEFT
				temp1 = -{LEAD}
			end if
			temp1 += temp4
{tile(3, "temp1", "temp5", "wall")}			if temp3 == true
				temp0 = 2
				temp1 -= temp4
				temp1 <<= 16
				NoSwap_grappleX += temp1 // latched at that point
			end if
		end if
		if temp0 == 0
			if temp2 < 0 // rising: a ceiling over it
				temp1 = temp5
				temp1 -= {LEAD}
{tile(4, "temp4", "temp1", "wall")}				if temp3 == true
					temp0 = 3
					NoSwap_grappleY -= {LEAD << 16:#x}
					NoSwap_grappleDir |= {ceil_bit}
				end if
			end if
		end if
		if temp0 == 0
			player.noswapAbility++
			if player.noswapAbility >= {c['anchor_frames']} // its range: back
				player.noswapAbility = {BACK + 1}
			end if
		end if
		if temp0 == 1 // a floor: back
			player.noswapAbility = {BACK + 1}
		end if
		if temp0 >= 2 // a wall or a ceiling: it bites, and reels her in
			player.noswapAbility = {LATCH + 1}
			PlaySfx(SfxName[{c['latch_sfx']}], false)
		end if
	else
		if temp0 < {BACK} // latched: reeled in; there yet?
			CallFunction(NoSwap_AnchorTo{i})
			temp1 = false
			if temp4 < {c['latch_range']}
				if temp5 < {c['latch_range']}
					temp1 = true
				end if
			end if
			if temp0 >= {LATCH + c['reel_frames']}
				temp1 = true
			end if
			if temp0 > {LATCH + 2}
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
			if temp1 == true // there: a small hop toward it, and let go
				player.noswapAbility = -{c['anchor_cooldown']}
				if player.gravity == GRAVITY_GROUND
					player.state = Player_State_Air
					player.gravity = GRAVITY_AIR
				end if
				player.yvel = -{c['grapple_hop']:#x}
				player.xvel = {c['grapple_forward']:#x}
				if temp2 < 0
					FlipSign(player.xvel)
				end if
				player.speed = player.xvel
				player.timer = 0
				player.animation = ANI_JUMPING
			else
				player.noswapAbility++
				CallFunction(NoSwap_AnchorPullGround{i})
			end if
		else // coming back to her hand
			temp1 = {HAND_X}
			if player.direction == FACING_LEFT
				temp1 = -{HAND_X}
			end if
			temp1 <<= 16
			temp1 += player.xpos
			temp1 -= NoSwap_grappleX
			temp2 = {HAND_Y << 16:#x}
			temp2 += player.ypos
			temp2 -= NoSwap_grappleY
			temp3 = temp1
			if temp3 < 0
				FlipSign(temp3)
			end if
			temp4 = temp2
			if temp4 < 0
				FlipSign(temp4)
			end if
			temp5 = false
			if temp3 < {c['anchor_return'] + 0x40000:#x}
				if temp4 < {c['anchor_return'] + 0x40000:#x}
					temp5 = true // home
				end if
			end if
			if temp0 >= {BACK + BACK_MAX}
				temp5 = true
			end if
			if temp5 == true
				player.noswapAbility = -{c['anchor_cooldown']}
				if player.gravity == GRAVITY_GROUND
					player.animation = ANI_STOPPED
				else
					player.animation = ANI_JUMPING
				end if
			else
				player.noswapAbility++
				ATan2(temp5, temp1, temp2)
				Cos256(temp3, temp5)
				temp3 *= {c['anchor_return'] >> 8:#x}
				NoSwap_grappleX += temp3
				Sin256(temp3, temp5)
				temp3 *= {c['anchor_return'] >> 8:#x}
				NoSwap_grappleY += temp3
			end if
		end if
	end if
	temp0 = player.noswapAbility
	if temp0 > 0
		temp1 = true // flying or coming back: the hitbox (only enemies, monitors and bosses use it) out to the anchor
		if temp0 > {LATCH}
			if temp0 < {BACK}
				temp1 = false
			end if
		end if
		if temp1 == true
			temp1 = NoSwap_grappleX
			temp1 -= player.xpos
			temp1 >>= 16
			temp2 = NoSwap_grappleY
			temp2 -= player.ypos
			temp2 >>= 16
			temp3 = temp1
			temp3 -= {BOX}
			if temp3 > -10
				temp3 = -10
			end if
			player.hitboxLeft = temp3
			temp1 += {BOX}
			if temp1 < 10
				temp1 = 10
			end if
			player.hitboxRight = temp1
			temp3 = temp2
			temp3 -= {BOX}
			if temp3 > -20
				temp3 = -20
			end if
			player.hitboxTop = temp3
			temp2 += {BOX}
			if temp2 < 20
				temp2 = 20
			end if
			player.hitboxBottom = temp2
			if player.gravity == GRAVITY_GROUND // she stands still for it
				player.speed = 0
				player.xvel = 0
			end if
		end if
	end if
end if
temp0 = player.noswapAbility
if temp0 > 0 // slot 41 (her throwing pose, an attack) and her facing: the throw's, or toward the point latched
	player.animation = ANI_NOSWAP_ATTACK
	player.frame = 0
	temp1 = NoSwap_grappleDir
	temp1 &= 1
	player.direction = temp1
	if temp0 > {LATCH}
		if temp0 < {BACK}
			if NoSwap_grappleX > player.xpos
				player.direction = FACING_RIGHT
			end if
			if NoSwap_grappleX < player.xpos
				player.direction = FACING_LEFT
			end if
		end if
	end if
	player.prevAnimation = player.animation // (the code picks the frame, not the animation speed)
	player.animationTimer = 0
end if
"""


def v4_air(i):
    """In the air state, before she moves (after its gravity): latched, reeled in along the chain (Max's reel)."""
    c = ab().ABILITIES[i]
    return f"""if player.noswapAbility > {LATCH}
	if player.noswapAbility < {BACK} // latched: reeled in along the chain to the point (Max's reel)
		temp0 = NoSwap_grappleX
		temp0 -= player.xpos
		temp1 = NoSwap_grappleY
		temp1 -= player.ypos
		ATan2(temp2, temp0, temp1)
		Cos256(player.xvel, temp2)
		player.xvel *= {c['reel_speed'] >> 8:#x}
		Sin256(player.yvel, temp2)
		player.yvel *= {c['reel_speed'] >> 8:#x}
		player.speed = player.xvel
	end if
end if
"""


def v4_pull_function(i):
    """Latched while on the ground: a point well above lifts her off (the air state reels her from next frame);
    otherwise she's drawn along the ground to it (Ristar's pull). And the distance helper."""
    c = ab().ABILITIES[i]
    return f"""// Marine: how far the point latched is (temp4, temp5: px across and down, both positive; temp2, temp3 signed)
public function NoSwap_AnchorTo{i}
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


// Marine: reeled in while on the ground (tools/anchor_throw.py): a point well above lifts her off; otherwise she's drawn
// along the ground to it
public function NoSwap_AnchorPullGround{i}
	if player.gravity == GRAVITY_GROUND
		CallFunction(NoSwap_AnchorTo{i})
		if temp3 < -12
			player.state = Player_State_Air
			player.gravity = GRAVITY_AIR
			player.yvel = -0x10000
			player.xvel = 0
			player.speed = 0
		else
			player.speed = {c['reel_speed']:#x}
			if temp2 < 0
				FlipSign(player.speed)
			end if
			player.xvel = player.speed
		end if
	end if
end function


"""


def v4_draw_function(i):
    """Her draw (ObjectDraw calls NoSwap_AnchorDraw<i> instead of DrawObjectAnimation): her body, then while the anchor is
    out the chain (DrawRect, 2 px dots from her hand to it) and the anchor (slot 43's frame, mirrored with the throw)."""
    c = ab().ABILITIES[i]
    r, g, b = CHAIN
    return f"""// Marine's draw (tools/anchor_throw.py): her body, and while it's out the anchor's chain and the anchor
public function NoSwap_AnchorDraw{i}
	DrawObjectAnimation()
	if player.noswapAbility > 0
		temp1 = {HAND_X} // the chain: from her hand (screen px)...
		if player.direction == FACING_LEFT
			temp1 = -{HAND_X}
		end if
		temp1 += player.ixpos
		temp1 -= screen.xoffset
		temp2 = {HAND_Y}
		temp2 += player.iypos
		temp2 -= screen.yoffset
		temp3 = NoSwap_grappleX // ...to the anchor
		temp3 >>= 16
		temp3 -= screen.xoffset
		temp3 -= temp1
		temp4 = NoSwap_grappleY
		temp4 >>= 16
		temp4 -= screen.yoffset
		temp4 -= temp2
		temp5 = temp3 // the steps: the longer axis
		if temp5 < 0
			FlipSign(temp5)
		end if
		temp0 = temp4
		if temp0 < 0
			FlipSign(temp0)
		end if
		if temp0 > temp5
			temp5 = temp0
		end if
		if temp5 < 1
			temp5 = 1
		end if
		temp6 = 0
		while temp6 < temp5
			temp7 = temp3
			temp7 *= temp6
			temp7 /= temp5
			temp7 += temp1
			temp7--
			temp0 = temp4
			temp0 *= temp6
			temp0 /= temp5
			temp0 += temp2
			temp0--
			DrawRect(temp7, temp0, 2, 2, {r}, {g}, {b}, 255)
			temp6++
		loop
		temp0 = player.noswapAbility // the anchor's frame: flukes forward, up or down
		temp1 = {F_FORWARD}
		if temp0 < {LATCH} // flying: along its path (its vertical speed against its speed along)
			temp2 = -{c['anchor_rise']:#x}
			temp3 = {c['anchor_speed']:#x}
			temp4 = NoSwap_grappleDir
			temp4 &= {HIGH}
			if temp4 != 0
				temp2 = -{c['anchor_high_rise']:#x}
				temp3 = {c['anchor_high_speed']:#x}
			end if
			temp4 = temp0
			temp4 *= {c['anchor_gravity']:#x}
			temp2 += temp4
			temp4 = temp3
			FlipSign(temp4)
			if temp2 < temp4
				temp1 = {F_UP}
			end if
			if temp2 > temp3
				temp1 = {F_DOWN}
			end if
		else
			if temp0 < {BACK} // latched: biting into a wall (forward) or a ceiling (up)
				temp4 = NoSwap_grappleDir
				temp4 &= {CEILING}
				if temp4 != 0
					temp1 = {F_UP}
				end if
			end if
		end if
		temp5 = player.animation
		temp6 = player.frame
		temp7 = player.direction
		temp2 = player.xpos
		temp3 = player.ypos
		temp4 = player.rotation
		player.animation = {ab().ANI_MELEE}
		player.frame = temp1
		temp1 = NoSwap_grappleDir
		temp1 &= 1
		player.direction = temp1
		player.xpos = NoSwap_grappleX
		player.ypos = NoSwap_grappleY
		player.rotation = 0
		DrawObjectAnimation()
		player.xpos = temp2
		player.ypos = temp3
		player.rotation = temp4
		player.animation = temp5
		player.frame = temp6
		player.direction = temp7
	end if
end function


"""


def v4_patch(t):
    """Player_BadnikBreak: a badnik broken while the anchor flies out sends it back. ObjectDraw: her draw is
    NoSwap_AnchorDraw<i>. Her functions reserved up front."""
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "public function Player_BadnikBreak\n"
        if t.count(head) != 1:
            sys.exit("anchor_throw: Player_BadnikBreak isn't there once")
        t = t.replace(head, head + f"""	if stage.playerListPos == {a} // [NoSwap] Marine's Anchor Throw (tools/anchor_throw.py): a hit sends it back
		if player[currentPlayer].noswapAbility > 0
			if player[currentPlayer].noswapAbility < {LATCH}
				player[currentPlayer].noswapAbility = {BACK + 1}
			end if
		end if
	end if
""")
        start = t.index("event ObjectDraw\n")
        end = t.index("end event\n", start)
        draw = t[start:end]
        if draw.count("\tDrawObjectAnimation()\n") != 1:
            sys.exit("anchor_throw: expected 1 DrawObjectAnimation in ObjectDraw")
        draw = draw.replace("\tDrawObjectAnimation()\n",
                            f"\tif stage.playerListPos == {a} // [NoSwap] Marine: her anchor and its chain (tools/anchor_throw.py)\n"
                            f"\t\tCallFunction(NoSwap_AnchorDraw{i})\n\telse\n\t\tDrawObjectAnimation()\n\tend if\n", 1)
        t = t[:start] + draw + t[end:]
        names = re.findall(rf"^public function (NoSwap_Anchor\w*{i})$", t, flags=re.M)
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("anchor_throw: the script's reserve block isn't there once")
        t = t.replace(anchor, "".join(f"reserve function {n}\n" for n in names) + anchor)
    return t


# ---------------------------------------------------------------- Sonic CD
# The same code in CD's v3 dialect (as tools/star_grab.py's Ristar and tools/head_throw.py's Headdy): her state is
# NoSwap.Star (Object[5].Value1, star_grab's alias, added here if Ristar and Headdy aren't in the build); the anchor's place
# and bits NoSwap.GrappleX / GrappleY / GrappleDir. Y comes from the DLL (game.callbackParam3 == 1). The anchor hits
# badniks, monitors and bosses through NoSwap_ShotTouch. No player hitbox to widen.
CD_ANCHOR = 46  # slot 43 in CD (cd_config.ABILITY_SLOTS)


def to_v3(text, i):
    import star_grab
    c = ab().ABILITIES[i]
    sfx = {c["anchor_sfx"]: c["anchor_sfx_cd"], c["latch_sfx"]: c["latch_sfx_cd"]}
    out = []

    def rename(line):
        for a, b in star_grab.V3_NAMES + [("player.rotation", "Player.Rotation")]:
            line = line.replace(a, b)
        line = re.sub(r"\btemp(\d)\b", r"TempValue\1", line)
        line = re.sub(r"SfxName\[([^\]]+)\]", lambda mm: sfx[mm.group(1)], line)
        return line.replace(f"Player.Animation = {ab().ANI_MELEE}", f"Player.Animation = {CD_ANCHOR}")
    for line in text.split("\n"):
        ind = line[:len(line) - len(line.lstrip("\t"))]
        code = line.strip()
        if "hitbox" in code:
            continue
        if code.startswith("ObjectTileCollision("):
            out += [f"{ind}Object.XPos = Player.XPos", f"{ind}Object.YPos = Player.YPos", f"{ind}CheckResult = false"]
        line = {"temp6 = player.xpos": f"{ind}temp6 = Object.XPos", "temp7 = player.ypos": f"{ind}temp7 = Object.YPos",
                "player.xpos = temp6": f"{ind}Object.XPos = temp6", "player.ypos = temp7": f"{ind}Object.YPos = temp7"
                }.get(code.split(" //")[0], line)
        if code.startswith("if keyPress[1].buttonY != false"):
            line = f"{ind}if game.callbackParam3 == 1 // Y, from the DLL (Marine's Anchor Throw)"
        out.append(rename(line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_grapple", "keyPress", "SfxName", "^="):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"anchor_throw: the CD code still has {bad!r}")
    return text


def cd_after(i):
    import build_soniccd
    rearm = "".join(l + "\n" for l in build_soniccd.Y_REARM)
    return to_v3(v4_start(i), i) + rearm + to_v3(v4_after(i)[len(v4_start(i)):], i)


def cd_touch(i):
    """NoSwap_ShotTouch's Marine part (Object: the badnik, monitor or boss; Object[10].Value0-3 its box, 16.16 from it): the
    anchor (BOX px round NoSwap.GrappleX / GrappleY), flying or coming back, inside the box hits it as a shot does
    (CheckResult, SHOT_HIT: the target's own code takes it as an attack), and one flying out comes back. Only TempValue0."""
    import shots_v3
    a = ab().ALIAS_OF[i]
    return f"""	if Stage.PlayerListPos == {a} // [NoSwap] Marine's anchor hits it (tools/anchor_throw.py cd_touch)
		TempValue0 = false
		if NoSwap.Star > 0
			TempValue0 = true
			if NoSwap.Star > {LATCH}
				if NoSwap.Star < {BACK}
					TempValue0 = false
				end if
			end if
		end if
		if TempValue0 == true
			TempValue0 = NoSwap.GrappleX
			TempValue0 -= Object.XPos
			TempValue0 += {BOX << 16:#x}
			if TempValue0 > Object[10].Value0
				TempValue0 -= {2 * BOX << 16:#x}
				if TempValue0 < Object[10].Value2
					TempValue0 = NoSwap.GrappleY
					TempValue0 -= Object.YPos
					TempValue0 += {BOX << 16:#x}
					if TempValue0 > Object[10].Value1
						TempValue0 -= {2 * BOX << 16:#x}
						if TempValue0 < Object[10].Value3
							CheckResult = true
							{shots_v3.SHOT_HIT} = true
							if NoSwap.Star < {LATCH}
								NoSwap.Star = {BACK + 1}
							end if
						end if
					end if
				end if
			end if
		end if
	end if
"""


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object): her functions, air and after blocks, the anchor's test in
    NoSwap_ShotTouch and her draw."""
    import star_grab
    for i in ids():
        a = ab().ALIAS_OF[i]
        check(i)
        if star_grab.CD_ALIAS not in t:
            head = "#alias 5\t:\tPLAYER_AMY_A\n"
            if t.count(head) != 1:
                sys.exit("anchor_throw: CD's Amy alias isn't there once")
            t = t.replace(head, head + star_grab.CD_ALIAS)
        fns = to_v3(v4_functions(i), i)
        decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"anchor_throw: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        for fn, body in (("NoSwap_AirAbilities", to_v3(v4_air(i), i)), ("NoSwap_AfterUpdate", cd_after(i))):
            head = f"\nfunction {fn}\n"
            if t.count(head) != 1:
                sys.exit(f"anchor_throw: CD's {fn} isn't there once")
            block = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] Marine's Anchor Throw (tools/anchor_throw.py)\n"
                     + "".join(f"\t\t{l}\n" if l.strip() else "\n" for l in body.rstrip("\n").split("\n")) + "\tend if\n")
            t = t.replace(head, head + block)
        head = "\nfunction NoSwap_ShotTouch\n\tObject[11].Value0 = TempValue0\n\tObject[11].Value1 = ArrayPos0\n\tCheckResult = false\n"
        if t.count(head) != 1:
            sys.exit("anchor_throw: CD's NoSwap_ShotTouch changed")
        t = t.replace(head, head + cd_touch(i))
        start = t.index("sub ObjectDraw\n")
        end = t.index("end sub\n", start)
        draw = t[start:end]
        old = "\tDrawPlayerAnimation()\n"
        if draw.count(old) != 1:
            sys.exit("anchor_throw: expected 1 bare DrawPlayerAnimation in CD's ObjectDraw")
        draw = draw.replace(old, f"\tif Stage.PlayerListPos == {a} // [NoSwap] Marine: her anchor and its chain (tools/anchor_throw.py)\n"
                                 f"\t\tCallFunction(NoSwap_AnchorDraw{i})\n\telse\n\t\tDrawPlayerAnimation()\n\tend if\n")
        t = t[:start] + draw + t[end:]
    return t
