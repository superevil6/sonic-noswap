"""Water walk (abilities.py "water_walk": Marine's sea legs), for Sonic 1/2 (Retro Engine v4 player script; abilities.py
calls in here), Sonic CD (build_soniccd.py calls cd_patch; R4/Water.txt marks the water: cd_water_mark) and the S3&K DLL
(native/src/WaterWalk.h, the same rule).

The user's design (2026-09-29): above water, the water's SURFACE is solid ground for her: she stands, walks, runs, rolls
and jumps on it. Holding DOWN lets her sink through it (a dive); underwater she swims as usual (and never drowns: the
no_breathing module). She only lands on it from above: coming up from below, she jumps out and lands on it as she falls
back (the sanest rule: no sudden pops out of the water, and a dive is never undone by the surface catching her again).

The rule (after the player has moved, every frame; v4 / CD like a bridge object, which also runs after the player):
- only in the free states (on the ground, rolling, in the air or a jump: never held by an object, hurt or dying), not
  moving up (a spring or a jump always leaves it), down not held, and the engine found no real floor this frame;
- her feet (her centre plus the current frame's collision bottom) at or below the surface, and last frame's feet
  (minus her vertical speed) no more than TOL_AIR px below it, or TOL_GROUND px either side while she was on the water
  already (the surface bobs and LZ's water rises and falls: she rides it);
- room over her head there (a solid ceiling tile at her head once lifted: she's left to sink, so rising water never
  pushes her into a ceiling);
then her feet are put on the surface, the vertical speed is 0 and she's on the ground (angle 0, floor mode, the floor
sensors set so she doesn't teeter), keeping her speed along; landing in the jump ball she lands walking (the engine's
own landing: the jump offset). The surface: S1/S2 stage.waterLevel (px; the Water objects set it, a huge value without
water), CD Stage.WaterLevel (px) only while R4/Water.txt's object has marked it this frame (R3 sets a WaterLevel for a
background effect with no water), S3&K the Water object's waterLevel (16.16; its statics at +4).
"""
import sys

TOL_AIR = 4  # px: landing from above (the fall per frame is added)
TOL_GROUND = 16  # px: already on the water, it may bob or rise under her
HEAD = 24  # px: her head's room test, above her new centre
V4_MAX_LEVEL = 0x8000  # S1/S2: a waterLevel at or past this (px) is no water


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("water_walk")


def v4_after(i, t, level="stage.waterLevel", marked=None, one_camera=False):
    """The rule, after the player has moved (S1/S2; CD through to_v3). `level`: the surface in px. `marked`: a condition
    line that must hold too (CD's mark), or None."""
    reeling = ""
    if ab().has(i, "anchor_throw"):
        import anchor_throw
        reeling = (f"\tif player.noswapAbility > {anchor_throw.LATCH}\n\t\tif player.noswapAbility < {anchor_throw.BACK} "
                   "// (reeled in by her anchor: not now)\n\t\t\ttemp0 = false\n\t\tend if\n\tend if\n")
    import re
    sensors = "".join(f"\t\t\tplayer.floorSensor{s} = true\n" for s in ("L", "C", "R", "LC", "RC")
                      if s in ("L", "C", "R") or re.search(rf":\s*player\.floorSensor{s}\b", t))
    mark = f"if {marked}\n" if marked else ""
    camera = ("\t\t\t\tcamera[0].adjustY = 0\n" if one_camera else  # (CD: one player, its camera)
              "\t\t\t\tif player.entityPos == camera[0].target\n\t\t\t\t\tcamera[0].adjustY = 0\n\t\t\t\tend if\n")
    return mark + f"""if {level} < {V4_MAX_LEVEL:#x} // [NoSwap] water walk (tools/water_walk.py): the surface is ground for her
	temp0 = false
	if player.down == false
		if player.yvel >= 0
			if player.gravity == GRAVITY_AIR // (no real floor under her this frame)
				CheckEqual(player.state, Player_State_Ground)
				temp0 |= checkResult
				CheckEqual(player.state, Player_State_Roll)
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
		end if
	end if
{reeling}	if temp0 == true
		temp1 = player.collisionBottom // her feet below her centre, px
		temp4 = false // landing in the jump ball: she lands walking (the engine's landing, its jump offset)
		if player.animation == ANI_JUMPING
			if player.state != Player_State_Roll
				temp4 = true
				temp1 -= player.jumpOffset
			end if
		end if
		temp2 = {level} // the surface
		temp2 <<= 16
		temp3 = temp1 // her feet
		temp3 <<= 16
		temp3 += player.ypos
		temp5 = {TOL_AIR << 16:#x} // how far below the surface her feet may have been last frame
		temp6 = temp3
		temp6 -= player.yvel
		CheckEqual(player.state, Player_State_Ground)
		temp7 = checkResult
		CheckEqual(player.state, Player_State_Roll)
		temp7 |= checkResult
		if temp7 == true // already on it: it may bob or rise under her, or sink a little
			temp5 = {TOL_GROUND << 16:#x}
			temp6 = temp2 // (her feet above it by no more than that too)
			temp6 -= temp3
			if temp6 > temp5
				temp0 = false
			end if
			temp6 = temp3
		else
			if temp3 < temp2 // still above it
				temp0 = false
			end if
		end if
		temp5 += temp2
		if temp6 > temp5 // she was below it: coming up from under the water (she lands on it from above only)
			temp0 = false
		end if
		if temp0 == true // room over her head?
			temp5 = temp2
			temp5 -= temp3
			temp5 >>= 16
			temp5 -= {HEAD}
			temp6 = player.xpos
			temp7 = player.ypos
			ObjectTileCollision(CSIDE_ROOF, 0, temp5, player.collisionPlane)
			player.xpos = temp6
			player.ypos = temp7
			if checkResult == true
				temp0 = false
			end if
		end if
		if temp0 == true // on the water
			temp1 <<= 16
			player.ypos = temp2
			player.ypos -= temp1
			player.yvel = 0
			player.gravity = GRAVITY_GROUND
			player.angle = 0
			player.rotation = 0
			player.collisionMode = CMODE_FLOOR
{sensors}			CheckEqual(player.state, Player_State_Ground)
			temp7 = checkResult
			CheckEqual(player.state, Player_State_Roll)
			temp7 |= checkResult
			if temp7 == false // landing: her speed along kept
				player.speed = player.xvel
				player.badnikBonus = 0
			end if
			if temp4 == true
				player.animation = ANI_WALKING
{camera}			end if
		end if
	end if
end if
""" + ("end if\n" if marked else "")


# ---------------------------------------------------------------- Sonic CD
# R4/Water.txt's object marks the water every frame (reserved slot 5's XPos: 1; nothing else uses it) after it sets
# Stage.WaterLevel; her code reads the mark and clears it, so without a Water object this frame there's no water.
CD_MARK = "Object[5].XPos"


def cd_water_mark(t):
    """R4/Water.txt's ObjectMain: the mark, at its end (after Stage.WaterLevel >>= 16)."""
    old = "\tStage.WaterLevel >>= 16\nend sub\n"
    if t.count(old) != 1:
        sys.exit("water_walk: R4/Water.txt's ObjectMain end changed")
    return t.replace(old, "\tStage.WaterLevel >>= 16\n"
                          f"\t{CD_MARK} = 1 // [NoSwap] the water is here this frame (tools/water_walk.py: water walk)\nend sub\n")


def to_v3(text):
    import re
    import star_grab
    names = star_grab.V3_NAMES + [("player.rotation", "Player.Rotation"), ("player.angle", "Player.Angle"),
                                  ("player.collisionMode", "Player.CollisionMode"),
                                  ("player.collisionBottom", "Player.CollisionBottom"),
                                  ("player.jumpOffset", "Player.JumpOffset"), ("player.floorSensor", "Player.FloorSensor")]
    out = []
    for line in text.split("\n"):
        ind = line[:len(line) - len(line.lstrip("\t"))]
        code = line.strip()
        if code.startswith("ObjectTileCollision("):
            out += [f"{ind}Object.XPos = Player.XPos", f"{ind}Object.YPos = Player.YPos", f"{ind}CheckResult = false"]
        line = {"temp6 = player.xpos": f"{ind}temp6 = Object.XPos", "temp7 = player.ypos": f"{ind}temp7 = Object.YPos",
                "player.xpos = temp6": f"{ind}Object.XPos = temp6", "player.ypos = temp7": f"{ind}Object.YPos = temp7"
                }.get(code.split(" //")[0], line)
        if code.startswith("player.badnikBonus"):  # (CD keeps no such count on the player)
            continue
        line = line.replace("camera[0].adjustY", "Screen.AdjustCameraY")
        for a, b in names:
            line = line.replace(a, b)
        line = re.sub(r"\btemp(\d)\b", r"TempValue\1", line)
        out.append(line)
    text = "\n".join(out)
    for bad in ("player.", "temp", "camera[", "stage."):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"water_walk: the CD code still has {bad!r}")
    return text


def cd_after(i, t):
    body = v4_after(i, "", level="Stage.WaterLevel", marked=f"{CD_MARK} == 1", one_camera=True)
    body = body.replace("CheckEqual(player.state, Player_State_RollJump)\n\t\t\t\ttemp0 |= checkResult\n", "") \
        if "Player_State_RollJump" not in t else body
    return to_v3(body) + f"\n{CD_MARK} = 0 // (the Water object marks it again next frame)\n"


def cd_patch(t):
    """The CD player script: her water walk at the end of NoSwap_AfterUpdate (after her other moves)."""
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "\nfunction NoSwap_AfterUpdate\n"
        start = t.find(head)
        if start < 0 or t.count(head) != 1:
            sys.exit("water_walk: CD's NoSwap_AfterUpdate isn't there once")
        end = t.index("\nend function\n", start)
        body = cd_after(i, t)
        block = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] water walk (tools/water_walk.py)\n"
                 + "".join(f"\t\t{l}\n" if l.strip() else "\n" for l in body.rstrip("\n").split("\n")) + "\tend if\n")
        t = t[:end + 1] + block + t[end + 1:]
    return t
