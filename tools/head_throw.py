"""Dynamite Headdy's Head Throw (abilities.py "head_throw"), for Sonic 1/2 (Retro Engine v4 player script; abilities.py
calls in here), Sonic CD (build_soniccd.py calls cd_patch) and the numbers the S3&K DLL reads (native/src/HeadThrow.h).

The user's design (2026-09-29):
- Y: Head Throw, aimed 8 ways with the d-pad (nothing held: forward; on the ground, down doesn't aim). His head flies
  out step px a frame for frames frames (80 px) from his neck (HEAD_Y px above his centre) and comes straight back at
  the same speed, while his body stands headless (slot 41 "Throw": the throwing bodies per aim class, ground 0-4, air
  5-9; an attack). The head is drawn at runtime (slot 43 "Heads", the sheet's flying head per aim class: out 0-4, back
  5-9, mirrored with his facing). It hits enemies, monitors and bosses it touches (S1/S2: his hitbox reaches out to it,
  as Ristar's hands; CD: NoSwap_ShotTouch; S3&K: Player_CheckBadnikTouch); a badnik hit (S1/S2, CD, S3&K) or solid
  terrain at the head sends it back at once. No grabbing. On the ground he stands still for it; in the air he falls
  as usual.
- Head variants (power-up heads, for the shared monitor_swap module to pick later): ABILITIES' "head_variants", a list
  of {"name", "step", "frames"}; index 0 is his normal head, the only one built now. Variant v's art is slot 43's frames
  v * HEAD_FRAMES and up. The index each engine reads is variant_expr(engine) (now the constant 0; the module replaces
  it with its per-player item index), and the DLL's head::g_variant.

noswapAbility (S1/S2; CD's NoSwap.Star, the DLL's own state, the same numbers):
  1..frames          the head going out (length state * step)
  BACK + k           the head coming back (length k * step), down to BACK: done
NoSwap_grappleDir: the aim (0 right, 1 up-right, 2 up, 3 up-left, 4 left, 5 down-left, 6 down, 7 down-right).
NoSwap_grappleX / Y: the head's place this frame (16.16; CD's badniks test it).
"""
import re
import sys

UX = [256, 181, 0, -181, -256, -181, 0, 181]
UY = [0, -181, -256, -181, 0, 181, 256, 181]
DIR_OF = [3, 2, 1, 4, 0, 0, 5, 6, 7]  # the d-pad's (x + 1) + 3 * (y + 1) -> direction
CLASS = [0, 1, 2, 1, 0, 3, 4, 3]  # direction -> aim class (0 forward, 1 forward-up, 2 up, 3 forward-down, 4 down)
BACK = 200
F_AIR = 5  # slot 41: air bodies
HEAD_FRAMES = 10  # slot 43 frames per variant (out 0-4, back 5-9)
F_HEAD_BACK = 5
HEAD_Y = -6  # the neck (the head's centre when on his body), px from his centre
VARIANT_MAX = 8  # (the DLL's arrays)


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("head_throw")


def variants(i):
    return ab().ABILITIES[i]["head_variants"]


def check(i):
    c = ab().ABILITIES[i]
    vs = c.get("head_variants") or []
    if not vs or len(vs) > VARIANT_MAX:
        sys.exit(f"head_throw: extra {i}: 1 to {VARIANT_MAX} head_variants")
    for v in vs:
        if set(v) != {"name", "step", "frames"} or not 0 < v["frames"] < BACK - 1:
            sys.exit(f"head_throw: extra {i}: a head variant is {{name, step, frames}} (frames under {BACK - 1}): {v}")
    bad = [a for a in c["abilities"] if a not in ("head_throw", "physics")]
    if bad or c.get("shot") or c.get("melee_reach"):
        sys.exit(f"head_throw: extra {i}: head_throw uses noswapAbility, the grapple values and slots 41-43 alone ({bad})")
    return c


def variant_expr(engine):
    """The head variant index an engine's code reads (0: his normal head). The monitor_swap module replaces this with
    its per-player item index (S1/S2 "v4", CD "cd")."""
    return "0"


def pick(dest, key, i, ind, engine="v4"):
    """dest = the current variant's `key` (a chain of ifs; one variant: the constant)."""
    vs = variants(i)
    out = f"{ind}{dest} = {vs[0][key]}\n"
    var = variant_expr(engine)
    for n, v in enumerate(vs[1:], 1):
        out += f"{ind}if {var} == {n}\n{ind}\t{dest} = {v[key]}\n{ind}end if\n"
    return out


def table(name, values):
    return f"private table {name}\n\t" + ", ".join(map(str, values)) + "\nend table\n\n\n"


# ---------------------------------------------------------------- Sonic 1/2
def v4_functions(i):
    check(i)
    a = ab().ALIAS_OF[i]
    return (f"// [NoSwap] Headdy's Head Throw ({a}; tools/head_throw.py): the aim's unit vectors (x256), the d-pad's "
            "direction, the aim classes\n"
            + table(f"NoSwap_HeadUX{i}", UX) + table(f"NoSwap_HeadUY{i}", UY)
            + table(f"NoSwap_HeadDirOf{i}", DIR_OF) + table(f"NoSwap_HeadClass{i}", CLASS)
            + v4_draw_function(i))


def v4_start(i):
    """Y (in the ground or air states, not hurt): the Head Throw, aimed with the d-pad."""
    c = ab().ABILITIES[i]
    return f"""if keyPress[1].buttonY != false // Headdy's Head Throw (tools/head_throw.py)
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
		GetTableValue(NoSwap_grappleDir, temp1, NoSwap_HeadDirOf{i})
		player.noswapAbility = 1
		PlaySfx(SfxName[{c['head_sfx']}], false)
	end if
end if
"""


def v4_tip(i, ind):
    """temp1 / temp2: the head's place (px from his centre) for noswapAbility temp0. Uses temp4, temp5."""
    return (f"{ind}temp5 = temp0\n{ind}if temp5 > {BACK}\n{ind}\ttemp5 -= {BACK}\n{ind}end if\n"
            + pick("temp4", "step", i, ind)
            + f"{ind}temp5 *= temp4\n"
            f"{ind}GetTableValue(temp1, NoSwap_grappleDir, NoSwap_HeadUX{i})\n{ind}temp1 *= temp5\n{ind}temp1 /= 256\n"
            f"{ind}GetTableValue(temp2, NoSwap_grappleDir, NoSwap_HeadUY{i})\n{ind}temp2 *= temp5\n{ind}temp2 /= 256\n"
            f"{ind}temp2 += {HEAD_Y}\n")


def v4_after(i):
    """After the player has moved: the throw's start, the head (out, terrain, back), his hitbox out to it, the frame."""
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
{v4_tip(i, chr(9))}	NoSwap_grappleX = temp1 // the head's place (Sonic CD's badniks test it: tools/head_throw.py cd_touch)
	NoSwap_grappleX <<= 16
	NoSwap_grappleX += player.xpos
	NoSwap_grappleY = temp2
	NoSwap_grappleY <<= 16
	NoSwap_grappleY += player.ypos
	if temp0 < {BACK} // going out: solid terrain at the head sends it back
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
		if temp3 == true
			player.noswapAbility += {BACK}
		else
			player.noswapAbility++
{pick("temp3", "frames", i, chr(9) * 3)}			if player.noswapAbility > temp3 // full reach: back
				player.noswapAbility = temp3
				player.noswapAbility += {BACK}
			end if
		end if
	else // coming back
		player.noswapAbility--
		if player.noswapAbility <= {BACK}
			player.noswapAbility = 0
			if player.gravity == GRAVITY_GROUND
				player.animation = ANI_STOPPED
			else
				player.animation = ANI_JUMPING
			end if
		end if
	end if
	if player.noswapAbility > 0 // the hitbox (only enemies, monitors and bosses use it) out to the head
		temp3 = temp1
		temp3 -= 10
		if temp3 > -10
			temp3 = -10
		end if
		player.hitboxLeft = temp3
		temp1 += 10
		if temp1 < 10
			temp1 = 10
		end if
		player.hitboxRight = temp1
		temp3 = temp2
		temp3 -= 10
		if temp3 > -20
			temp3 = -20
		end if
		player.hitboxTop = temp3
		temp2 += 10
		if temp2 < 20
			temp2 = 20
		end if
		player.hitboxBottom = temp2
	end if
	if player.gravity == GRAVITY_GROUND // he stands still for it
		player.speed = 0
		player.xvel = 0
	end if
end if
temp0 = player.noswapAbility
if temp0 > 0 // slot 41's frame (his headless body for the aim; the code picks it) and his facing
	player.animation = ANI_NOSWAP_ATTACK
	GetTableValue(temp1, NoSwap_grappleDir, NoSwap_HeadClass{i})
	if player.gravity != GRAVITY_GROUND
		temp1 += {F_AIR}
	end if
	player.frame = temp1
	GetTableValue(temp1, NoSwap_grappleDir, NoSwap_HeadUX{i}) // facing the aim
	if temp1 > 0
		player.direction = FACING_RIGHT
	end if
	if temp1 < 0
		player.direction = FACING_LEFT
	end if
	player.prevAnimation = player.animation // (the code picks the frame, not the animation speed)
	player.animationTimer = 0
end if
"""


def v4_draw_function(i):
    """His draw (ObjectDraw calls NoSwap_HeadDraw<i> instead of DrawObjectAnimation): his body, then while it's away
    his head (slot 43's frame for the variant, the aim class, out or back; mirrored with his facing)."""
    return f"""// Headdy's draw (tools/head_throw.py): his body, and his head while it's thrown
public function NoSwap_HeadDraw{i}
	DrawObjectAnimation()
	temp0 = player.noswapAbility
	if temp0 > 0
{v4_tip(i, chr(9) * 2)}		temp3 = 0 // the frame: out, or back (+ {F_HEAD_BACK})
		if temp0 > {BACK}
			temp3 = {F_HEAD_BACK}
		end if
		GetTableValue(temp0, NoSwap_grappleDir, NoSwap_HeadClass{i})
		temp3 += temp0
		temp0 = {variant_expr("v4")}
		temp0 *= {HEAD_FRAMES}
		temp3 += temp0
		temp5 = player.animation
		temp6 = player.frame
		player.animation = {ab().ANI_MELEE}
		player.frame = temp3
		temp1 *= 0x10000
		temp2 *= 0x10000
		player.xpos += temp1
		player.ypos += temp2
		DrawObjectAnimation()
		player.xpos -= temp1
		player.ypos -= temp2
		player.animation = temp5
		player.frame = temp6
	end if
end function


"""


def v4_patch(t):
    """Player_BadnikBreak: a badnik broken while his head is going out sends the head back. ObjectDraw: his draw is
    NoSwap_HeadDraw<i>."""
    for i in ids():
        a = ab().ALIAS_OF[i]
        head = "public function Player_BadnikBreak\n"
        if t.count(head) != 1:
            sys.exit("head_throw: Player_BadnikBreak isn't there once")
        t = t.replace(head, head + f"""	if stage.playerListPos == {a} // [NoSwap] Headdy's Head Throw (tools/head_throw.py): a hit sends the head back
		if player[currentPlayer].noswapAbility > 0
			if player[currentPlayer].noswapAbility < {BACK}
				player[currentPlayer].noswapAbility += {BACK}
			end if
		end if
	end if
""")
        start = t.index("event ObjectDraw\n")
        end = t.index("end event\n", start)
        draw = t[start:end]
        if draw.count("\tDrawObjectAnimation()\n") != 1:
            sys.exit("head_throw: expected 1 DrawObjectAnimation in ObjectDraw")
        draw = draw.replace("\tDrawObjectAnimation()\n",
                            f"\tif stage.playerListPos == {a} // [NoSwap] Headdy: his thrown head (tools/head_throw.py)\n"
                            f"\t\tCallFunction(NoSwap_HeadDraw{i})\n\telse\n\t\tDrawObjectAnimation()\n\tend if\n", 1)
        t = t[:start] + draw + t[end:]
        names = re.findall(rf"^public function (NoSwap_Head\w*{i})$", t, flags=re.M)
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("head_throw: the script's reserve block isn't there once")
        t = t.replace(anchor, "".join(f"reserve function {n}\n" for n in names) + anchor)
    return t


# ---------------------------------------------------------------- Sonic CD
# The same code in CD's v3 dialect (as tools/star_grab.py's Ristar): no tables (the aim's vectors from Cos256 / Sin256,
# the other lookups switches), no player hitbox to widen, one player. His state is NoSwap.Star (Object[5].Value1: star_grab's
# alias, added here if Ristar isn't in the build); the head's place and the aim NoSwap.GrappleX / GrappleY / GrappleDir.
# Y comes from the DLL (game.callbackParam3 == 1). The head hits badniks, monitors and bosses through NoSwap_ShotTouch.
CD_HEADS = 46  # slot 43 in CD (cd_config.ABILITY_SLOTS)


def to_v3(text, i):
    import star_grab
    c = ab().ABILITIES[i]
    sfx = {c["head_sfx"]: c["head_sfx_cd"]}
    out = []

    def rename(line):
        for a, b in star_grab.V3_NAMES:
            line = line.replace(a, b)
        line = re.sub(r"\btemp(\d)\b", r"TempValue\1", line)
        line = re.sub(r"SfxName\[([^\]]+)\]", lambda mm: sfx[mm.group(1)], line)
        return line.replace(f"Player.Animation = {ab().ANI_MELEE}", f"Player.Animation = {CD_HEADS}")
    lines = text.split("\n")
    k = 0
    while k < len(lines):
        line = lines[k]
        k += 1
        if line.startswith("private table "):
            while not lines[k].startswith("end table"):
                k += 1
            k += 1
            continue
        ind = line[:len(line) - len(line.lstrip("\t"))]
        code = line.strip()
        if "hitbox" in code:
            continue
        m = re.match(r"GetTableValue\(([\w.\[\]]+), ([\w.]+), NoSwap_Head(UX|UY|DirOf|Class)\d+\)", code)
        if m:
            dest, idx, name = m.groups()
            dest, idx = rename(dest), rename(idx)
            if name in ("UX", "UY"):
                out += [f"{ind}{dest} = {idx}", f"{ind}{dest} *= 32",
                        f"{ind}{'Cos256' if name == 'UX' else 'Sin256'}({dest}, {dest})"]
                if name == "UY":
                    out.append(f"{ind}FlipSign({dest})")
            else:
                values = DIR_OF if name == "DirOf" else CLASS
                out.append(f"{ind}switch {idx}")
                for v in sorted(set(values)):
                    out += [f"{ind}case {n}" for n, x in enumerate(values) if x == v]
                    out += [f"{ind}\t{dest} = {v}", f"{ind}\tbreak"]
                out.append(f"{ind}end switch")
            continue
        if code.startswith("ObjectTileCollision("):
            out += [f"{ind}Object.XPos = Player.XPos", f"{ind}Object.YPos = Player.YPos", f"{ind}CheckResult = false"]
        line = {"temp6 = player.xpos": f"{ind}temp6 = Object.XPos", "temp7 = player.ypos": f"{ind}temp7 = Object.YPos",
                "player.xpos = temp6": f"{ind}Object.XPos = temp6", "player.ypos = temp7": f"{ind}Object.YPos = temp7"
                }.get(code.split(" //")[0], line)
        if code.startswith("if keyPress[1].buttonY != false"):
            line = f"{ind}if game.callbackParam3 == 1 // Y, from the DLL (Headdy's Head Throw)"
        out.append(rename(line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_grapple", "GetTableValue", "keyPress", "SfxName", "^="):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"head_throw: the CD code still has {bad!r}")
    return text


def cd_after(i):
    import build_soniccd
    rearm = "".join(l + "\n" for l in build_soniccd.Y_REARM)
    return to_v3(v4_start(i), i) + rearm + to_v3(v4_after(i)[len(v4_start(i)):], i)


def cd_touch(i):
    """NoSwap_ShotTouch's Headdy part (Object: the badnik, monitor or boss; Object[10].Value0-3 its box, 16.16 from it):
    his head (10 px round NoSwap.GrappleX / GrappleY) inside the box hits it as a shot does (CheckResult, SHOT_HIT: the
    target's own code takes it as an attack), and a head going out comes back. Only TempValue0 (saved)."""
    import shots_v3
    a = ab().ALIAS_OF[i]
    return f"""	if Stage.PlayerListPos == {a} // [NoSwap] Headdy's thrown head hits it (tools/head_throw.py cd_touch)
		if NoSwap.Star > 0
			TempValue0 = NoSwap.GrappleX
			TempValue0 -= Object.XPos
			TempValue0 += 0xA0000
			if TempValue0 > Object[10].Value0
				TempValue0 -= 0x140000
				if TempValue0 < Object[10].Value2
					TempValue0 = NoSwap.GrappleY
					TempValue0 -= Object.YPos
					TempValue0 += 0xA0000
					if TempValue0 > Object[10].Value1
						TempValue0 -= 0x140000
						if TempValue0 < Object[10].Value3
							CheckResult = true
							{shots_v3.SHOT_HIT} = true
							if NoSwap.Star < {BACK}
								NoSwap.Star += {BACK}
							end if
						end if
					end if
				end if
			end if
		end if
	end if
"""


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object): his functions, after block, the head's test in
    NoSwap_ShotTouch and his draw."""
    import star_grab
    for i in ids():
        a = ab().ALIAS_OF[i]
        check(i)
        if star_grab.CD_ALIAS not in t:
            head = "#alias 5\t:\tPLAYER_AMY_A\n"
            if t.count(head) != 1:
                sys.exit("head_throw: CD's Amy alias isn't there once")
            t = t.replace(head, head + star_grab.CD_ALIAS)
        fns = to_v3(v4_functions(i), i)
        decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", fns, re.M))
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"head_throw: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        head = "\nfunction NoSwap_AfterUpdate\n"
        if t.count(head) != 1:
            sys.exit("head_throw: CD's NoSwap_AfterUpdate isn't there once")
        body = cd_after(i)
        block = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] Headdy (tools/head_throw.py)\n"
                 + "".join(f"\t\t{l}\n" if l.strip() else "\n" for l in body.rstrip("\n").split("\n")) + "\tend if\n")
        t = t.replace(head, head + block)
        head = "\nfunction NoSwap_ShotTouch\n\tObject[11].Value0 = TempValue0\n\tObject[11].Value1 = ArrayPos0\n\tCheckResult = false\n"
        if t.count(head) != 1:
            sys.exit("head_throw: CD's NoSwap_ShotTouch changed")
        t = t.replace(head, head + cd_touch(i))
        start = t.index("sub ObjectDraw\n")
        end = t.index("end sub\n", start)
        draw = t[start:end]
        old = "\tDrawPlayerAnimation()\n"
        if draw.count(old) != 1:
            sys.exit("head_throw: expected 1 bare DrawPlayerAnimation in CD's ObjectDraw")
        draw = draw.replace(old, f"\tif Stage.PlayerListPos == {a} // [NoSwap] Headdy: his thrown head (tools/head_throw.py)\n"
                                 f"\t\tCallFunction(NoSwap_HeadDraw{i})\n\telse\n\t\tDrawPlayerAnimation()\n\tend if\n")
        t = t[:start] + draw + t[end:]
    return t
