#!/usr/bin/env python3
"""Sonic CD (RSDKv3) projectiles: an extra's "shot" (abilities.py), a real object that flies on its own and breaks
badniks, opens monitors and hits bosses. The Sonic 1/2 version is tools/shots_v4.py, the S3&K one the DLL's; this is
the CD port of the same design (scratchpad research, approved by the user 2026-09-27).

v3 has no groups, no foreach and one player (`Player.`), so the shot can't pose as a second player the way it does in
S1/S2. Instead:
- The shot's object type is the game's "Tails Object" (global object 6, Players/TailsObject.txt), unused while an extra
  plays (its ObjectStartup only does anything for Tails; extras keep slot 1 blank). NoSwap ships a TailsObject.txt whose
  subs, for an extra (Stage.PlayerListPos >= 7), load the player's own animation file (extras.PLAYER_ANI: already
  loaded, so no new sheet), run the player script's NoSwap_ShotUpdate and DrawObjectAnimation() (R7/MetalSonic.txt does
  the same for Metal Sonic). The shot's frames are an animation (ANI_SHOT, a fixed slot) in each package's own player
  .ani, on a free spot of its own player sheet (place_art): no new sprite sheet, no sprite memory.
- Shots live in the reserved entity slots SLOTS (nothing in the game or NoSwap touches them), so the targets find them
  by number. A shot's Object.State is LIVE; its Value0/1 are its velocity, Value2 its age, Value3 its radius (16.16),
  Value4 its collision plane.
- Badniks: after each badnik's own collision test (C_ENEMY, then Player_BadnikBreak), if the player didn't touch it,
  NoSwap_ShotTouch tests the same box against the live shots. On a hit the shot is gone at once (no double kills), the
  flag SHOT_HIT is set and CheckResult is true, so the badnik runs its own Player_BadnikBreak: the flag makes that an
  attack (flower, smoke, score, sound, Origins' kill callback) without the player's bounce, and never a hurt.
- Bosses: the same test after their collision, and after their attack test (the Amy hammer block's place)
  NoSwap_ShotAttack makes a shot's hit an attack. The boss's own code then runs: its hit, flash, sound and invulnerable
  time. It also flings the player as if he'd hit it; NoSwap_ShotAttack keeps his speeds and the player script puts
  them back at the start of his next update, before he moves.
- Monitors: after the monitor's own player test, if it's still a monitor, the shot test with the monitor's box; a hit
  runs the monitor's own break lines without the player's bounce. The Broken Monitor gives the item to the player.
- Without an extra with a shot no shot exists: the tests find nothing in SLOTS.
"""
import os
import re
import sys

LIVE = 0xA7  # a shot's Object.State while it flies (v3 keeps an entity's state in one byte: 0x7E57 read back as 0x57)
SLOTS = (6, 7, 8)  # reserved entity slots the shots use (docs/soniccd_map.md section 4: never touched)
ARGS = 10  # Object[ARGS].Value0-3: the box NoSwap_ShotTouch tests (16.16, from the target), Value4: SHOT_HIT
SAVE = 11  # Object[SAVE].Value0-1: NoSwap_ShotTouch's saved TempValue0 / ArrayPos0; Value2: the player's YVelocity
# before a badnik's break; Value3-5: his XVelocity, YVelocity, Speed before a boss's hit; Value7: those to put back
SHOT_HIT = f"Object[{ARGS}].Value4"
# A homing shot (motion "homing": Cream's Cheese; homing_body). A build with one has no other shots (abilities.check_homing).
# Seeking it's LIVE; after a hit, or with no target for a while, it comes back as RETURNING (the targets' test skips it).
# Its target search: NoSwap_ShotTouch (every badnik and boss calls it each frame the player isn't touching it; not the
# monitor) keeps the nearest one on screen to a seeking shot in SEEK_BEST (its distance + 1, 16.16 across + down;
# SEEK_NONE: none yet) and SEEK_X / SEEK_Y (where it is), which the shot reads and resets in its own update.
RETURNING = 0xA8
SEEK_BEST, SEEK_X, SEEK_Y = f"Object[{ARGS}].Value5", f"Object[{ARGS}].Value6", f"Object[{ARGS}].Value7"
SEEK_NONE = 0x7FFFFFF
SEEK_SCRATCH = f"Object[{SAVE}].Value6"
ANI_SHOT = 54  # the shot's animation in the extra's own player .ani (after CD's 45-53 ability slots: cd_config.py)
ANI_SHOT2 = 55  # a second shot's ("shot2", abilities.py: Robotnik's Bomb Drop): its animation also tells its shots apart
HOST = "Players/TailsObject.txt"
MONITOR = "Global/Monitor.txt"
# Bosses: their player collision gets the shot test, and after their Amy hammer block (one each) NoSwap_ShotAttack.
# (Mission/Boss_Face2.txt has no Amy block: BOSS_ANCHORS. R3/BossBody (hit by any touch), R5's (by touch, then its
# bombs) and R7's race are left out.)
BOSSES = ["R1/Boss_Face.txt", "R4/Eggman1.txt", "R4/Eggman2.txt", "R6/EggmanMobile.txt", "R8/EggMobile.txt"]
BOSS_ANCHORS = {"Mission/Boss_Face2.txt": ("\t\t\t\t\tCheckEqual(Player.Animation, ANI_HAMMER_DASH)\n"
                                           "\t\t\t\t\tTempValue2 |= CheckResult\n", "TempValue2")}
WRAP_HEAD = "if Object[5].Value3 == 0 // [NoSwap] an extra's shot reaches further"  # build_soniccd.enemy_reach
COLLISION = re.compile(r"^(\t*)PlayerObjectCollision\(C_ENEMY, ?(-?\d+), ?(-?\d+), ?(-?\d+), ?(-?\d+)\)\s*$")


def code(line):
    return line.split("//")[0].strip()


# ---------------------------------------------------------------- the targets
def shot_test(ind, box, why):
    l, t, r, b = box
    return [f"{ind}if CheckResult == false // [NoSwap] not the player: an extra's shot? ({why}; tools/shots_v3.py)",
            f"{ind}\tObject[{ARGS}].Value0 = {l << 16}",
            f"{ind}\tObject[{ARGS}].Value1 = {t << 16}",
            f"{ind}\tObject[{ARGS}].Value2 = {r << 16}",
            f"{ind}\tObject[{ARGS}].Value3 = {b << 16}",
            f"{ind}\tCallFunction(NoSwap_ShotTouch)",
            f"{ind}end if"]


def collision_sites(lines):
    """[(first, last, indent, box)] of each player C_ENEMY test NoSwap's builder left: build_soniccd.enemy_reach's
    wrapped form (first line WRAP_HEAD, the original test on the next line) or a bare one."""
    from build_soniccd import origins_lines
    active = origins_lines(lines)
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if active[i] and l.strip() == WRAP_HEAD:
            ind = l[: len(l) - len(l.lstrip("\t"))]
            m = COLLISION.match(lines[i + 1])
            end = next(k for k in range(i + 1, len(lines)) if lines[k] == f"{ind}end if")
            if not m:
                sys.exit(f"shots_v3: no C_ENEMY test after {WRAP_HEAD!r}")
            out.append((i, end, ind, tuple(map(int, m.group(2, 3, 4, 5)))))
            i = end + 1
            continue
        m = COLLISION.match(l)
        if m and active[i]:
            out.append((i, i, m.group(1), tuple(map(int, m.group(2, 3, 4, 5)))))
        i += 1
    return out


def next_code(lines, k, n):
    """The n code lines Origins compiles after line k (no blanks, comments, #platform lines or other platforms' code)."""
    from build_soniccd import origins_lines
    active = origins_lines(lines)
    out = []
    for j in range(k + 1, len(lines)):
        c = code(lines[j])
        if c and not c.startswith("#") and active[j]:
            out.append(c)
            if len(out) == n:
                break
    return out


def badnik_sites(t):
    """Each badnik test: the player's C_ENEMY test, then `if CheckResult == true` / CallFunction(Player_BadnikBreak).
    (Tests followed by anything else, like Kemusi's spiky body (Player_Hit) or a rolling Dango's armour, are left: a shot
    passes through them.)"""
    lines = t.split("\n")
    return lines, [s for s in collision_sites(lines)
                   if next_code(lines, s[1], 2) == ["if CheckResult == true", "CallFunction(Player_BadnikBreak)"]]


def add_tests(lines, sites, why):
    for first, last, ind, box in sorted(sites, reverse=True):
        lines[last + 1:last + 1] = shot_test(ind, box, why)
    return "\n".join(lines)


def badnik(t, name):
    lines, sites = badnik_sites(t)
    if not sites:
        sys.exit(f"shots_v3: {name}: no badnik test")
    return add_tests(lines, sites, "its Player_BadnikBreak takes it as an attack")


def boss(t, name):
    """The shot test after the boss's collision tests (in ObjectPlayerInteraction) and NoSwap_ShotAttack after its
    attack test's Amy block (or BOSS_ANCHORS)."""
    lines = t.split("\n")
    start = lines.index("sub ObjectPlayerInteraction")
    end = next(k for k in range(start, len(lines)) if lines[k] == "end sub")
    sites = [s for s in collision_sites(lines) if start < s[0] < end]
    if not sites:
        sys.exit(f"shots_v3: {name}: no C_ENEMY test in ObjectPlayerInteraction")
    t = add_tests(lines, sites, "the boss takes a hit")
    if name in BOSS_ANCHORS:
        anchor, var = BOSS_ANCHORS[name]
        ind = anchor.split("\n")[-2][: len(anchor.split("\n")[-2]) - len(anchor.split("\n")[-2].lstrip("\t"))]
        return patch_once(t, anchor, anchor + attack_lines(ind, var), name)
    lines = t.split("\n")
    amy = [k for k, l in enumerate(lines) if code(l) == "if Stage.PlayerListPos == PLAYER_AMY"]
    if len(amy) != 1:
        sys.exit(f"shots_v3: {name}: {len(amy)} Amy blocks (expected 1)")
    k = amy[0]
    ind = lines[k][: len(lines[k]) - len(lines[k].lstrip("\t"))]
    e = next(j for j in range(k + 1, len(lines)) if lines[j] == f"{ind}end if")
    body = "\n".join(code(l) for l in lines[k + 1:e])
    if "ANI_HAMMER" not in body:
        sys.exit(f"shots_v3: {name}: the Amy block isn't the hammer's")
    if "CheckResult = true" in body:
        var = None
    elif "TempValue0 = true" in body or "TempValue0 |= CheckResult" in body:
        var = "TempValue0"
    else:
        sys.exit(f"shots_v3: {name}: the Amy block sets neither CheckResult nor TempValue0")
    lines[e + 1:e + 1] = attack_lines(ind, var).rstrip("\n").split("\n")
    return "\n".join(lines)


def attack_lines(ind, var):
    """NoSwap_ShotAttack: CheckResult true when a shot hit (var: the test's own variable, when it isn't CheckResult)."""
    if var is None:
        return f"{ind}CallFunction(NoSwap_ShotAttack) // [NoSwap] an extra's shot hit it: an attack (tools/shots_v3.py)\n"
    return (f"{ind}CheckResult = false // [NoSwap] an extra's shot hit it: an attack (tools/shots_v3.py)\n"
            f"{ind}CallFunction(NoSwap_ShotAttack)\n{ind}{var} |= CheckResult\n")


def patch_once(t, anchor, new, name):
    if t.count(anchor) != 1:
        sys.exit(f"shots_v3: {name}: anchor found {t.count(anchor)} times (expected 1)")
    return t.replace(anchor, new)


# The monitor's own break (its ObjectPlayerInteraction), without the player's bounce
MONITOR_BREAK = ["Object.State = MONITOR_IDLE",
                 "CreateTempObject(TypeName[Smoke Puff], 0, Object.XPos, Object.YPos)",
                 "Object[TempObjectPos].DrawOrder = 4",
                 "Object.Type = TypeName[Broken Monitor]",
                 "BrokenMonitor.Priority\t= PRIORITY_ACTIVE",
                 "BrokenMonitor.Alpha\t\t= 255",
                 "BrokenMonitor.YVelocity = Object.YPos",
                 "BrokenMonitor.Timer\t\t= -0x30000",
                 "PlaySfx(SFX_G_DESTROY, false)"]
MONITOR_BOX = (-16, -14, 16, 16)  # its player test: PlayerObjectCollision(C_TOUCH, -16, -14, 16, 16)


def monitor(t):
    """After the monitor's own player test, still a monitor: an extra's shot opens it the same way."""
    start = t.index("sub ObjectPlayerInteraction\n")
    end = t.index("\nend sub\n", start)
    own = t[start:end]
    if "PlayerObjectCollision(C_TOUCH, %d, %d, %d, %d)" % MONITOR_BOX not in own:
        sys.exit("shots_v3: Monitor.txt: its player test's box changed")
    at = 0
    for l in MONITOR_BREAK:  # (its own lines, in its order)
        k = own.find("\t" + l + "\n", at)
        if k < 0:
            sys.exit(f"shots_v3: Monitor.txt: its break has no line {l!r}")
        at = k
    new = (["\tif Object.Type == TypeName[Monitor] // [NoSwap] not broken by the player: an extra's shot? "
            "(tools/shots_v3.py)", "\t\tCheckResult = false"]
           + shot_test("\t", MONITOR_BOX, "it opens the monitor")[1:-1]
           + ["\t\tif CheckResult == true", f"\t\t\t{SHOT_HIT} = false"]
           + ["\t\t\t" + l for l in MONITOR_BREAK] + ["\t\tend if", "\tend if"])
    return t[:end] + "\n" + "\n".join(new) + t[end:]


# ---------------------------------------------------------------- the shot's object (TailsObject.txt)
def wrap_sub(t, sub, extra):
    """`sub` runs `extra` for an extra (Stage.PlayerListPos >= 7) and its own code for anyone else."""
    head = f"sub {sub}\n"
    if t.count(head) != 1:
        sys.exit(f"shots_v3: TailsObject.txt: expected one {sub}")
    start = t.index(head)
    end = t.index("\nend sub\n", start)
    body = t[start + len(head):end]
    new = ("\tif Stage.PlayerListPos >= 7 // [NoSwap] an extra: this type is its shots (tools/shots_v3.py)\n"
           + "".join(f"\t\t{l}\n" for l in extra) + "\telse\n" + body + "\n\tend if")
    return t[:start] + head + new + t[end:]


def tails_object(t):
    import extras
    t = wrap_sub(t, "ObjectMain", ["CallFunction(NoSwap_ShotUpdate)"])
    # (Value7, which no shot sets: 1 marks a Screen Nuke's object, abilities.py melee_nuke, which draws the screen's fade
    # to black by its Value6 instead; -1: nothing)
    t = wrap_sub(t, "ObjectDraw", ["if Object.Value7 == 0",
                                   "\tDrawObjectAnimation() // its frames: ANI_SHOT of the player's own animation",
                                   "else",
                                   "\tif Object.Value6 > 0 // a Screen Nuke's flash (abilities.py melee_nuke)",
                                   "\t\tSetScreenFade(0, 0, 0, Object.Value6)",
                                   "\tend if",
                                   "end if"])
    return wrap_sub(t, "ObjectStartup", [f'LoadAnimation("{extras.PLAYER_ANI}") // the player\'s own (already loaded: '
                                         "no new sheet); the shot is its animation "
                                         f"{ANI_SHOT}"])


def add_builders(builders):
    """The shot's scripts into build_soniccd's BUILDERS, each after its own builder (enemy_reach's wrap included)."""
    from build_soniccd import BASE
    from shots_v4 import compose
    for p in sorted(BASE.rglob("*.txt")):
        rel = p.relative_to(BASE).as_posix()
        if rel in BOSSES or rel in BOSS_ANCHORS:
            builders[rel] = compose(builders.get(rel), lambda t, rel=rel: boss(t, rel))
            continue
        text = p.read_bytes().decode("utf-8", errors="ignore").replace("\r\n", "\n")
        if "CallFunction(Player_BadnikBreak)" in text and not rel.startswith("Players/"):
            inner = builders.get(rel)
            if badnik_sites(inner(text) if inner else text)[1]:
                builders[rel] = compose(inner, lambda t, rel=rel: badnik(t, rel))
    builders[MONITOR] = compose(builders.get(MONITOR), monitor)
    builders[HOST] = compose(builders.get(HOST), tails_object)
    return builders


# ---------------------------------------------------------------- the player script (every variant)
def seek_lines():
    """NoSwap_ShotTouch's target search for a seeking homing shot (Object[ArrayPos0], LIVE): this target (Object: not
    the monitor), on screen, nearer than any other this frame: kept (see SEEK_BEST). TempValue0 is NoSwap_ShotTouch's
    (saved and put back)."""
    return f"""				if Object.Type != TypeName[Monitor] // [NoSwap] a homing shot's target search (tools/shots_v3.py)
					TempValue0 = Object.iXPos
					TempValue0 -= Screen.XOffset
					if TempValue0 >= 0
						if TempValue0 < Screen.XSize
							TempValue0 = Object.iYPos
							TempValue0 -= Screen.YOffset
							if TempValue0 >= 0
								if TempValue0 < Screen.YSize
									TempValue0 = Object.XPos // how near: across + down, + 1
									TempValue0 -= Object[ArrayPos0].XPos
									if TempValue0 < 0
										FlipSign(TempValue0)
									end if
									{SEEK_SCRATCH} = TempValue0
									TempValue0 = Object.YPos
									TempValue0 -= Object[ArrayPos0].YPos
									if TempValue0 < 0
										FlipSign(TempValue0)
									end if
									TempValue0 += {SEEK_SCRATCH}
									TempValue0++
									if TempValue0 < {SEEK_BEST}
										{SEEK_BEST} = TempValue0
										{SEEK_X} = Object.XPos
										{SEEK_Y} = Object.YPos
									end if
								end if
							end if
						end if
					end if
				end if
"""


PIERCE = 7  # a piercing shot's Value5 (shot "pierce": Mega Man's Charge Shot; only a straight shot's, whose Value5 is free)
PIERCE6 = 0x7E57  # a piercing boomerang's Value6 (its Value5 is its phase; John's cross): no cycle frame or homing count


def player_functions(update_blocks, touch=(), keep_nukes=False, homing=False, pierce=False, pierce6=False):
    """The functions the targets and TailsObject.txt call (every player script has them). update_blocks: the extras'
    NoSwap_ShotUpdate bodies (build_soniccd's per-extra blocks; none: a stub removing any shot). touch: lines setting
    CheckResult while an extra's own touch attacks (build_soniccd.touch_attack_lines: Heavy's Charge), so a boss it
    touches takes a hit too. keep_nukes: a build with a Screen Nuke (abilities.py melee_nuke: its object's Value7 1),
    which a hit doesn't remove (only such a build's script has the test). homing: a build with a homing shot (its only
    shot: abilities.check_homing), which a hit sends back (RETURNING) instead of removing, and whose target search
    (seek_lines) runs here."""
    slots_end = SLOTS[-1] + 1
    gone = (f"""								Object[ArrayPos0].Type = TypeName[Blank Object] // gone at its first hit
								Object[ArrayPos0].State = 0
""" if not keep_nukes else f"""								if Object[ArrayPos0].Value7 == 0 // gone at its first hit (not a Screen Nuke)
									Object[ArrayPos0].Type = TypeName[Blank Object]
									Object[ArrayPos0].State = 0
								end if
""")
    if homing:  # (a homing shot: back to her after its first hit, hitting nothing more; homing_body)
        gone = gone.replace("Object[ArrayPos0].Type = TypeName[Blank Object] // gone at its first hit",
                            f"Object[ArrayPos0].Value5 = 1 // a homing shot: back to her (its update), no more hits")
        gone = gone.replace("Object[ArrayPos0].State = 0", f"Object[ArrayPos0].State = {RETURNING}")
        gone = gone.replace("Object[ArrayPos0].Type = TypeName[Blank Object]",
                            f"Object[ArrayPos0].Value5 = 1 // a homing shot: back to her (its update), no more hits")
    if pierce:  # (a build with a piercing shot: it isn't gone at a hit, it flies on)
        gone = (f"\t\t\t\t\t\t\t\tif Object[ArrayPos0].Value5 != {PIERCE} // (a piercing shot flies on)\n"
                + "".join("\t" + l + "\n" for l in gone.rstrip("\n").split("\n")) + "\t\t\t\t\t\t\t\tend if\n")
    if pierce6:  # (a build with a piercing boomerang: Value6 marks it, its Value5 being its phase)
        gone = (f"\t\t\t\t\t\t\t\tif Object[ArrayPos0].Value6 != {PIERCE6} // (a piercing boomerang flies on)\n"
                + "".join("\t" + l + "\n" for l in gone.rstrip("\n").split("\n")) + "\t\t\t\t\t\t\t\tend if\n")
    return f"""// [NoSwap] Shot: a target's test (tools/shots_v3.py). In: Object[{ARGS}].Value0-3, the target's box (16.16, from it).
// Out: CheckResult true when a live shot overlaps it: that shot is gone and {SHOT_HIT} is set (the target's own code
// then takes it as an attack: Player_BadnikBreak, NoSwap_ShotAttack). Keeps TempValue0 and ArrayPos0.
function NoSwap_ShotTouch
	Object[{SAVE}].Value0 = TempValue0
	Object[{SAVE}].Value1 = ArrayPos0
	CheckResult = false
	ArrayPos0 = {SLOTS[0]}
	while ArrayPos0 < {slots_end}
		if Object[ArrayPos0].Type == TypeName[Tails Object]
			if Object[ArrayPos0].State == {LIVE}
{seek_lines() if homing else ""}				TempValue0 = Object[ArrayPos0].XPos // its right edge, from the target
				TempValue0 -= Object.XPos
				TempValue0 += Object[ArrayPos0].Value3
				if TempValue0 > Object[{ARGS}].Value0
					TempValue0 -= Object[ArrayPos0].Value3 // its left edge
					TempValue0 -= Object[ArrayPos0].Value3
					if TempValue0 < Object[{ARGS}].Value2
						TempValue0 = Object[ArrayPos0].YPos // its bottom edge
						TempValue0 -= Object.YPos
						TempValue0 += Object[ArrayPos0].Value3
						if TempValue0 > Object[{ARGS}].Value1
							TempValue0 -= Object[ArrayPos0].Value3 // its top edge
							TempValue0 -= Object[ArrayPos0].Value3
							if TempValue0 < Object[{ARGS}].Value3
								CheckResult = true
								{SHOT_HIT} = true
{gone}								ArrayPos0 = {slots_end}
							end if
						end if
					end if
				end if
			end if
		end if
		ArrayPos0++
	loop
	TempValue0 = Object[{SAVE}].Value0
	ArrayPos0 = Object[{SAVE}].Value1
end function


// [NoSwap] Shot: a boss's attack test asks (tools/shots_v3.py). CheckResult true when a shot hit it (else unchanged);
// the player's speeds are kept, to be put back before he moves again (the boss flings him as if he'd hit it)
function NoSwap_ShotAttack
	if {SHOT_HIT} == true
		{SHOT_HIT} = false
		CheckResult = true
		Object[{SAVE}].Value3 = Player.XVelocity
		Object[{SAVE}].Value4 = Player.YVelocity
		Object[{SAVE}].Value5 = Player.Speed
		Object[{SAVE}].Value7 = true
	end if
""" + "".join(f"\t{l}\n" for l in touch) + f"""end function


// [NoSwap] Shot: the shot's own update (Object: the shot), from TailsObject.txt (tools/shots_v3.py). An extra without a
// shot never makes one: this removes any
function NoSwap_ShotUpdate
""" + ("".join(update_blocks) if update_blocks else "\tObject.Type = TypeName[Blank Object]\n") + "end function\n\n\n"


def player_script(t):
    """Player_BadnikBreak takes a shot's hit (SHOT_HIT) as an attack, without the player's bounce and never as a hurt;
    and at the start of his update, the speeds a boss's shot hit changed are put back."""
    anchor = ("\tCheckEqual(Player.Animation, ANI_GLIDING_STOP)\n\tTempValue0 |= CheckResult\n#endplatform\n\n"
              "\tArrayPos0   = Player.EntityNo\n")
    t = patch_once(t, anchor, anchor.replace("\n\n", f"\n\tObject[{SAVE}].Value2 = Player.YVelocity // [NoSwap] an extra's "
                                            "shot hit it: an attack, without his bounce (tools/shots_v3.py)\n"
                                            f"\tTempValue0 |= {SHOT_HIT}\n\n", 1), "badnik break: shot")
    anchor = "\telse\n\t\tif Player.InvincibleTimer == 0\n\t\t\tPlayer.State = Player_State_GotHit\n"
    t = patch_once(t, anchor, "\telse\n\t\tTempValue0 = Player.InvincibleTimer\n"
                   f"\t\tTempValue0 |= {SHOT_HIT} // [NoSwap] (a shot's touch never hurts him: a mission's no-kill rule)\n"
                   "\t\tif TempValue0 == 0\n\t\t\tPlayer.State = Player_State_GotHit\n", "badnik break: no hurt")
    anchor = "\tend if\nend function\n\n// Do you really need an explanation?\nfunction Player_Hit\n"
    t = patch_once(t, anchor, f"\tend if\n\tif {SHOT_HIT} == true // [NoSwap] a shot's hit: no bounce\n"
                   f"\t\tPlayer.YVelocity = Object[{SAVE}].Value2\n\t\t{SHOT_HIT} = false\n\tend if\n"
                   "end function\n\n// Do you really need an explanation?\nfunction Player_Hit\n", "badnik break: end")
    anchor = "sub ObjectMain\n"
    return patch_once(t, anchor, anchor + f"""	if Object[{SAVE}].Value7 == true // [NoSwap] an extra's shot hit a boss last frame: his speeds back (tools/shots_v3.py)
		Object[{SAVE}].Value7 = false
		Player.XVelocity = Object[{SAVE}].Value3
		Player.YVelocity = Object[{SAVE}].Value4
		Player.Speed = Object[{SAVE}].Value5
	end if
	{SHOT_HIT} = false

""", "shot restore")


def shot_states():
    return ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
            "Player_State_Roll"]


def update_body(s, s2=None):
    """The shot's own update (Object: the shot): too old, at a wall or offscreen, gone; otherwise it moves, bounces off
    floors (motion "bounce") and animates (a hit removes it in NoSwap_ShotTouch). s2: a second shot ("shot2"), whose
    shots are the ones in animation ANI_SHOT2."""
    if s2:
        return ([f"if Object.Animation == {ANI_SHOT2} // the second shot (\"shot2\")"]
                + ["\t" + l for l in update_body_of(s2, ANI_SHOT2)] + ["else"]
                + ["\t" + l for l in update_body_of(s, ANI_SHOT)] + ["end if"])
    return update_body_of(s, ANI_SHOT)


ANI_SWAP = 56  # swap shots' animations ("swap_shots", abilities.py: John's sub-weapons): entry k's flight ANI_SWAP + 2k, a
# burning one's flames ANI_SWAP + 2k + 1 (its animation also tells its shots apart)


def swap_anims(k):
    return ANI_SWAP + 2 * k, ANI_SWAP + 2 * k + 1


def swap_update_body(shots):
    """The update of an extra's swap shots (one per monitor_swap entry), each told by its animation (swap_anims)."""
    out = ["TempValue7 = Object.Animation // (the swap shots' tests read it once: an update may change it)"]
    for k, s in enumerate(shots):
        fly, burn = swap_anims(k)
        if "burn" in s:
            out += [f"TempValue1 = false // swap shot {k}: its flight or its flames (tools/monitor_swap.py)",
                    f"if TempValue7 == {fly}", "\tTempValue1 = true", "end if",
                    f"if TempValue7 == {burn}", "\tTempValue1 = true", "end if", "if TempValue1 == true"]
        else:
            out += [f"if TempValue7 == {fly} // swap shot {k} (tools/monitor_swap.py)"]
        out += ["\t" + l for l in update_body_of(s, fly, burn if "burn" in s else None)] + ["end if"]
    return out


def update_body_of(s, anim, burn_anim=None):
    """update_body for one shot, drawn with animation `anim`. burn_anim: a swap shot's "burn" (John's Holy Water): landing
    it burns there in that animation for its burn lifetime; "terrain" false: walls, floors and ceilings don't end it."""
    import build_s3k_shot
    art = s.get("art", {})
    r, ticks, count = s["radius"], art.get("ticks", 2), build_s3k_shot.frame_count(art)
    if s["motion"] == "boomerang":
        return boomerang_body(s, ticks, count, anim)
    if s["motion"] == "homing":
        return homing_body(s, ticks, count, anim)
    bounce = s["motion"] == "bounce"
    pull = f"+= {s.get('gravity', 0):#x}" if s.get("gravity", 0) >= 0 else f"-= {-s['gravity']:#x}"  # (a dip's pulls up)
    fall = [f"\tObject.Value1 {pull}", f"\tif Object.Value1 > {s['max_fall']:#x}",
            f"\t\tObject.Value1 = {s['max_fall']:#x}", "\tend if"] if s["motion"] in ("bounce", "drop", "dip") else []
    frame = (["\t\t\tObject.Frame = Object.Value6 // (cycle: its own frame, picked when thrown)"] if s.get("cycle") else
             ["\t\t\tObject.Frame = Object.Value6 // (aim_frames: its aim's frame, picked when thrown)"]
             if s.get("aim_frames") else
             ["\t\t\tObject.AnimationTimer++", f"\t\t\tif Object.AnimationTimer >= {ticks * count}",
              "\t\t\t\tObject.AnimationTimer = 0", "\t\t\tend if",
              f"\t\t\tObject.Animation = {anim}", "\t\t\tObject.Frame = Object.AnimationTimer",
              f"\t\t\tObject.Frame /= {ticks}"])
    if "hitboxes" in art:  # a reach per frame (build_s3k_shot.py "hitboxes"): its radius, the box's right edge
        frame += [x for k, (_, _, right, _) in enumerate(art["hitboxes"])
                  for x in (f"\t\t\tif Object.Frame == {k} // (its reach shrinks with its art)",
                            f"\t\t\t\tObject.Value3 = {right << 16:#x}", "\t\t\tend if")]
    floor = ["\t\tif Object.Value1 >= 0 // bouncing along the floor",
             f"\t\t\tObjectTileCollision(CSIDE_FLOOR, 0, {r}, Object.Value4)",
             "\t\t\tif CheckResult == true", f"\t\t\t\tObject.Value1 = {s['bounce']:#x}", "\t\t\tend if",
             "\t\telse",
             f"\t\t\tObjectTileCollision(CSIDE_ROOF, 0, {-r}, Object.Value4)",
             "\t\t\tif CheckResult == true", "\t\t\t\tObject.Value1 = 0", "\t\t\tend if",
             "\t\tend if"] if bounce else []
    terrain = s.get("terrain", True) is not False  # (swap shot "terrain" false: nothing solid ends it, John's axe)
    walls = ["\tif Object.Value0 > 0", f"\t\tObjectTileCollision(CSIDE_LWALL, {r + 1}, {-(r // 2)}, Object.Value4)",
             "\tend if",
             "\tif Object.Value0 < 0", f"\t\tObjectTileCollision(CSIDE_RWALL, {-(r + 1)}, {-(r // 2)}, Object.Value4)",
             "\tend if"] if terrain else []
    shown = ["\t\tif Object.OutOfBounds == true", "\t\t\tObject.Type = TypeName[Blank Object]", "\t\telse"] + frame + [
        "\t\tend if"]
    rest = (["Object.Value2++ // its age", f"if Object.Value2 > {s['lifetime']}", "\tObject.Type = TypeName[Blank Object]",
             "else"] + fall
            + ["\tObject.XPos += Object.Value0",
               "\tCheckResult = false // a wall ahead (its leading edge, above its middle: not a floor or a slope)"]
            + walls + [
               "\tif CheckResult == true", "\t\tObject.Type = TypeName[Blank Object]",
               "\telse", "\t\tObject.YPos += Object.Value1"] + floor
            + (vertical(s, shown, burn_anim) if terrain else shown)
            + ["\tend if", "end if"])
    body = ([f"if Object.State != {LIVE} // (a hit already removed it)", "\tObject.Type = TypeName[Blank Object]", "else"]
            + ["\t" + l for l in rest] + ["end if"])
    if burn_anim is not None:  # (burning where it landed: its flames' own update first)
        b = s["burn"]["art"]
        bt, bn = b.get("ticks", 2), build_s3k_shot.frame_count(b)
        body = ([f"if Object.Animation == {burn_anim} // burning (swap shot \"burn\": John's Holy Water's flames)",
                 "\tObject.Value2++ // its age", f"\tif Object.Value2 > {s['lifetime']}",
                 "\t\tObject.Type = TypeName[Blank Object]", "\telse", "\t\tObject.AnimationTimer++",
                 f"\t\tif Object.AnimationTimer >= {bt * bn}", "\t\t\tObject.AnimationTimer = 0", "\t\tend if",
                 "\t\tObject.Frame = Object.AnimationTimer", f"\t\tObject.Frame /= {bt}", "\tend if", "else"]
                + ["\t" + l for l in body] + ["end if"])
    return probe_sounds(body) if os.environ.get("NOSWAP_SHOT_PROBE") else body


def boomerang_body(s, ticks, count, anim=ANI_SHOT):
    """A boomerang's own update (Object: the shot; update_body's for motion "boomerang"; abilities.boomerang_update_body
    is the S1/S2 one, the DLL's BoomerangUpdate the S3&K one): too old, gone. Out (Value5 0): ahead at its own speed
    (Value0) plus the player's forward speed, slowing by decel per frame; stopped, it comes back (Value5 1), homing on
    his hand (y px below his centre) wherever he is now: per axis a target speed of 1/8 of the gap, at most
    return_speed, reached at return_accel per frame, plus his own velocity. Within catch px: caught, gone. No terrain;
    offscreen: gone. (A hit removes it in NoSwap_ShotTouch.)"""
    rmax, racc, catch, y = s["return_speed"], s["return_accel"], s["catch"] << 16, s["y"] << 16

    def offset(var):  # (his hand: y px below his centre; a negative one as a subtraction)
        return [] if not y else [f"\t\t{var} {'+=' if y > 0 else '-='} {abs(y):#x}"]

    def home(pos, vel, player_pos, player_vel):
        return ([f"\t\tTempValue0 = {player_pos} // the gap to him, /8, at most return_speed"]
                + (offset("TempValue0") if pos == "YPos" else [])
                + [f"\t\tTempValue0 -= Object.{pos}", "\t\tTempValue0 /= 8",
                   f"\t\tif TempValue0 > {rmax:#x}", f"\t\t\tTempValue0 = {rmax:#x}", "\t\tend if",
                   f"\t\tif TempValue0 < -{rmax:#x}", f"\t\t\tTempValue0 = -{rmax:#x}", "\t\tend if",
                   f"\t\tTempValue0 -= Object.{vel} // toward it at most return_accel this frame",
                   f"\t\tif TempValue0 > {racc:#x}", f"\t\t\tTempValue0 = {racc:#x}", "\t\tend if",
                   f"\t\tif TempValue0 < -{racc:#x}", f"\t\t\tTempValue0 = -{racc:#x}", "\t\tend if",
                   f"\t\tObject.{vel} += TempValue0", f"\t\tObject.{pos} += Object.{vel}",
                   f"\t\tObject.{pos} += {player_vel} // (plus his own velocity: running doesn't outpace it)"])

    rest = (["Object.Value2++ // its age", f"if Object.Value2 > {s['lifetime']}", "\tObject.Type = TypeName[Blank Object]",
             "else",
             "\tif Object.Value5 == 0 // a boomerang flying out (tools/shots_v3.py boomerang_body)",
             "\t\tTempValue0 = Player.XVelocity // his own forward speed along (so he doesn't run into it)",
             "\t\tif Object.Direction == FACING_LEFT", "\t\t\tFlipSign(TempValue0)", "\t\tend if",
             "\t\tif TempValue0 < 0", "\t\t\tTempValue0 = 0", "\t\tend if",
             "\t\tif Object.Direction == FACING_LEFT", "\t\t\tFlipSign(TempValue0)", "\t\tend if",
             "\t\tTempValue0 += Object.Value0", "\t\tObject.XPos += TempValue0",
             "\t\tTempValue1 = false // slowing down; stopped: it comes back",
             "\t\tif Object.Direction == FACING_LEFT", f"\t\t\tObject.Value0 += {s['decel']:#x}",
             "\t\t\tif Object.Value0 > -1", "\t\t\t\tTempValue1 = true", "\t\t\tend if",
             "\t\telse", f"\t\t\tObject.Value0 -= {s['decel']:#x}",
             "\t\t\tif Object.Value0 < 1", "\t\t\t\tTempValue1 = true", "\t\t\tend if", "\t\tend if",
             "\t\tif TempValue1 == true", "\t\t\tObject.Value0 = 0", "\t\t\tObject.Value1 = 0",
             "\t\t\tObject.Value5 = 1", "\t\tend if",
             "\telse // coming back, homing on his hand"]
            + home("XPos", "Value0", "Player.XPos", "Player.XVelocity")
            + home("YPos", "Value1", "Player.YPos", "Player.YVelocity")
            + ["\t\tTempValue0 = Player.XPos // within catch px of his hand: caught", "\t\tTempValue0 -= Object.XPos",
               "\t\tif TempValue0 < 0", "\t\t\tFlipSign(TempValue0)", "\t\tend if",
               "\t\tTempValue1 = Player.YPos"] + offset("TempValue1") + [
               "\t\tTempValue1 -= Object.YPos",
               "\t\tif TempValue1 < 0", "\t\t\tFlipSign(TempValue1)", "\t\tend if",
               f"\t\tif TempValue0 < {catch:#x}", f"\t\t\tif TempValue1 < {catch:#x}", "\t\t\t\tObject.Value5 = 2",
               "\t\t\tend if", "\t\tend if",
               "\tend if",
               "\tif Object.Value5 == 2", "\t\tObject.Type = TypeName[Blank Object]",
               "\telse",
               "\t\tif Object.OutOfBounds == true", "\t\t\tObject.Type = TypeName[Blank Object]",
               "\t\telse", "\t\t\tObject.AnimationTimer++", f"\t\t\tif Object.AnimationTimer >= {ticks * count}",
               "\t\t\t\tObject.AnimationTimer = 0", "\t\t\tend if",
               f"\t\t\tObject.Animation = {anim}", "\t\t\tObject.Frame = Object.AnimationTimer",
               f"\t\t\tObject.Frame /= {ticks}", "\t\tend if",
               "\tend if",
               "end if"])
    body = ([f"if Object.State != {LIVE} // (a hit already removed it)", "\tObject.Type = TypeName[Blank Object]", "else"]
            + ["\t" + l for l in rest] + ["end if"])
    # (probe: state lost, hurt (5); lifetime, select (27); caught, release (7); offscreen, lose rings (4))
    return probe_sounds(body, [5, 27, 7, 4]) if os.environ.get("NOSWAP_SHOT_PROBE") else body


def homing_body(s, ticks, count, anim=ANI_SHOT):
    """A homing shot's own update (Object: the shot; update_body's for motion "homing": Cream's Cheese). Seeking (State
    LIVE, Value5 0): the nearest target NoSwap_ShotTouch kept since its last update (SEEK_BEST / SEEK_X / SEEK_Y) is
    steered at: per axis a target speed of 1/4 of the gap, at most seek_speed, reached at seek_accel per frame; none:
    straight on (plus his forward speed along), and seek_frames of those in a row (Value6 counts) turn it back. Its first
    hit turns it back too (NoSwap_ShotTouch: RETURNING, Value5 1); coming back it flies as a boomerang does
    (boomerang_body's return) and is caught within catch px. Gone (caught, too old, offscreen): the cooldown starts
    then. No terrain. Drawn facing the way it flies. (abilities.homing_update_body is the S1/S2 one, the DLL's
    HomingUpdate the S3&K one.)"""
    smax, sacc, rmax, racc = s["seek_speed"], s["seek_accel"], s["return_speed"], s["return_accel"]
    catch, y = s["catch"] << 16, s["y"] << 16

    def clamp(var, lim, ind):
        return [f"{ind}if {var} > {lim:#x}", f"{ind}\t{var} = {lim:#x}", f"{ind}end if",
                f"{ind}if {var} < -{lim:#x}", f"{ind}\t{var} = -{lim:#x}", f"{ind}end if"]

    def steer(pos, vel, target, div, top, acc, ind, dy=0):
        return ([f"{ind}TempValue0 = {target} // the gap, /{div}, at most {top:#x}, reached at {acc:#x} a frame"]
                + ([f"{ind}TempValue0 {'+=' if dy > 0 else '-='} {abs(dy):#x}"] if dy else [])
                + [f"{ind}TempValue0 -= Object.{pos}", f"{ind}TempValue0 /= {div}"] + clamp("TempValue0", top, ind)
                + [f"{ind}TempValue0 -= Object.{vel}"] + clamp("TempValue0", acc, ind)
                + [f"{ind}Object.{vel} += TempValue0", f"{ind}Object.{pos} += Object.{vel}"])

    back = lambda ind: [f"{ind}Object.State = {RETURNING} // coming back: no more hits (its speed kept: it swings round)",
                        f"{ind}Object.Value5 = 1"]
    body = (["Object.Value2++ // its age (tools/shots_v3.py homing_body)",
             f"if Object.Value2 > {s['lifetime']}", "\tObject.Value5 = 2", "end if",
             f"if Object.State == {LIVE} // seeking",
             "\tif Object.Value5 == 0",
             f"\t\tif {SEEK_BEST} < {SEEK_NONE:#x} // a target (the nearest NoSwap_ShotTouch kept): steer at it",
             "\t\t\tObject.Value6 = 0"]
            + steer("XPos", "Value0", SEEK_X, 4, smax, sacc, "\t\t\t")
            + steer("YPos", "Value1", SEEK_Y, 4, smax, sacc, "\t\t\t")
            + ["\t\telse // none: straight on (his forward speed along), then back",
               "\t\t\tObject.Value6++", "\t\t\tTempValue0 = Player.XVelocity",
               "\t\t\tif Object.Value0 > 0", "\t\t\t\tif TempValue0 < 0", "\t\t\t\t\tTempValue0 = 0", "\t\t\t\tend if",
               "\t\t\telse", "\t\t\t\tif TempValue0 > 0", "\t\t\t\t\tTempValue0 = 0", "\t\t\t\tend if", "\t\t\tend if",
               "\t\t\tTempValue0 += Object.Value0", "\t\t\tObject.XPos += TempValue0", "\t\t\tObject.YPos += Object.Value1",
               f"\t\t\tif Object.Value6 >= {s['seek_frames']}"] + back("\t\t\t\t") + ["\t\t\tend if",
               "\t\tend if",
               f"\t\t{SEEK_BEST} = {SEEK_NONE:#x} // (the next search)",
               "\tend if",
               "else",
               f"\tif Object.State != {RETURNING} // (neither: gone)", "\t\tObject.Value5 = 2", "\tend if",
               "end if",
               "if Object.Value5 == 1 // coming back, homing on his hand"]
            + steer("XPos", "Value0", "Player.XPos", 8, rmax, racc, "\t")
            + ["\tObject.XPos += Player.XVelocity // (plus his own velocity: running doesn't outpace it)"]
            + steer("YPos", "Value1", "Player.YPos", 8, rmax, racc, "\t", y)
            + ["\tObject.YPos += Player.YVelocity",
               "\tTempValue0 = Player.XPos // within catch px of his hand: caught", "\tTempValue0 -= Object.XPos",
               "\tif TempValue0 < 0", "\t\tFlipSign(TempValue0)", "\tend if",
               "\tTempValue1 = Player.YPos"] + ([f"\tTempValue1 {'+=' if y > 0 else '-='} {abs(y):#x}"] if y else []) + [
               "\tTempValue1 -= Object.YPos", "\tif TempValue1 < 0", "\t\tFlipSign(TempValue1)", "\tend if",
               f"\tif TempValue0 < {catch:#x}", f"\t\tif TempValue1 < {catch:#x}", "\t\t\tObject.Value5 = 2",
               "\t\tend if", "\tend if",
               "end if",
               "if Object.OutOfBounds == true", "\tObject.Value5 = 2", "end if",
               "if Object.Value5 == 2 // gone (caught, too old or offscreen): the next throw after the cooldown",
               f"\tNoSwap.ShotCooldown = {s['cooldown']}", "\tObject.Type = TypeName[Blank Object]", "\tObject.State = 0",
               "else",
               "\tif Object.Value0 > 0x4000 // drawn facing the way it flies", "\t\tObject.Direction = FACING_RIGHT",
               "\tend if", "\tif Object.Value0 < -0x4000", "\t\tObject.Direction = FACING_LEFT", "\tend if",
               "\tObject.AnimationTimer++", f"\tif Object.AnimationTimer >= {ticks * count}",
               "\t\tObject.AnimationTimer = 0", "\tend if",
               f"\tObject.Animation = {anim}", "\tObject.Frame = Object.AnimationTimer", f"\tObject.Frame /= {ticks}",
               "end if"])
    return probe_sounds(body, [7]) if os.environ.get("NOSWAP_SHOT_PROBE") else body


def vertical(s, rest, burn_anim=None):
    """Motion "straight" / "drop" / "dip": gone at a floor below / a ceiling above, moving that way (aimed up or down), before
    `rest` (the offscreen test and the animation). burn_anim: a swap shot's "burn" (John's Holy Water): landing, it stays
    there burning in that animation (its age set to leave the burn's lifetime)."""
    if burn_anim is not None:
        r = s["radius"]
        return (["\t\tCheckResult = false // a floor or a ceiling ahead (its leading edge)",
                 "\t\tif Object.Value1 > 0", f"\t\t\tObjectTileCollision(CSIDE_FLOOR, 0, {r + 1}, Object.Value4)", "\t\tend if",
                 "\t\tif Object.Value1 < 0", f"\t\t\tObjectTileCollision(CSIDE_ROOF, 0, {-(r + 1)}, Object.Value4)",
                 "\t\tend if",
                 "\t\tif CheckResult == true",
                 "\t\t\tif Object.Value1 > 0 // landed: it bursts into its flames there (swap shot \"burn\")",
                 "\t\t\t\tObject.Value0 = 0", "\t\t\t\tObject.Value1 = 0",
                 f"\t\t\t\tObject.Value2 = {s['lifetime'] - s['burn']['lifetime']} // (its flames' frames: the burn's lifetime)",
                 f"\t\t\t\tObject.Animation = {burn_anim}", "\t\t\t\tObject.Frame = 0", "\t\t\t\tObject.AnimationTimer = 0",
                 f"\t\t\t\tObject.Value3 = {s['burn']['art'].get('hitbox', [0, 0, r, r])[2] << 16:#x} // (its flames' reach)",
                 "\t\t\telse", "\t\t\t\tObject.Type = TypeName[Blank Object]", "\t\t\tend if",
                 "\t\telse"] + ["\t" + l for l in rest] + ["\t\tend if"])
    if s["motion"] == "bounce":
        return rest
    r = s["radius"]
    if s["motion"] == "ground":  # along the floor, gripped to it (as a walking badnik); no floor to grip: a ledge's end
        return ([f"\t\tObjectTileGrip(CSIDE_FLOOR, 0, {r}, Object.Value4)",
                 "\t\tif CheckResult == false // off a ledge's end", "\t\t\tObject.Type = TypeName[Blank Object]",
                 "\t\telse"] + ["\t" + l for l in rest] + ["\t\tend if"])
    return (["\t\tCheckResult = false // a floor or a ceiling ahead (its leading edge)",
             "\t\tif Object.Value1 > 0", f"\t\t\tObjectTileCollision(CSIDE_FLOOR, 0, {r + 1}, Object.Value4)", "\t\tend if",
             "\t\tif Object.Value1 < 0", f"\t\t\tObjectTileCollision(CSIDE_ROOF, 0, {-(r + 1)}, Object.Value4)",
             "\t\tend if",
             "\t\tif CheckResult == true"]
            + (["\t\t\tif Object.Value1 > 0 // a drop landed: the game's own explosion puff there, as its bombs make",
                "\t\t\t\tCreateTempObject(TypeName[Explosion], 0, Object.XPos, Object.YPos)",
                "\t\t\t\tObject[TempObjectPos].DrawOrder = Object.DrawOrder", "\t\t\tend if"] if s["motion"] == "drop" else [])
            + ["\t\t\tObject.Type = TypeName[Blank Object]", "\t\telse"]
            + ["\t" + l for l in rest] + ["\t\tend if"])


def probe_sounds(body, ends=None):
    """NOSWAP_SHOT_PROBE=1 (a diagnostic build): each way the shot ends plays its own sound, and its first update the
    jump sound. State lost: hurt (5); lifetime: select (27); wall: skid (3); offscreen: lose rings (4). (`ends`: a
    boomerang's own list.)"""
    if ends is None:
        ends = [5, 27, 3, 4]  # (the Blank Object lines, in order: state, lifetime, wall, offscreen)
        if sum(l.strip() == "Object.Type = TypeName[Blank Object]" for l in body) == 5:  # (straight: floor / ceiling: skid)
            ends.insert(3, 3)
    sounds = iter(ends)
    out = []
    for line in body:
        out.append(line)
        if line.strip() == "Object.Type = TypeName[Blank Object]":
            out.append(line.replace("Object.Type = TypeName[Blank Object]", f"PlaySfx({next(sounds)}, false) // [probe]"))
        elif line.strip() == "Object.Value2++ // its age":
            ind = line[:len(line) - len(line.lstrip())]
            out += [f"{ind}if Object.Value2 == 1 // [probe] its first update", f"{ind}\tPlaySfx(0, false)", f"{ind}end if"]
    return out


def aim_start(s):
    """An aimed shot (shot "aim"): the d-pad as Y is pressed picks its direction (TempValue5: x, -1 left / 1 right;
    TempValue6: y, -1 up / 1 down; down only in the air: on the ground it's crouching), nothing held: the way he faces.
    Holding left or right turns him that way first when he's standing or in the air. TempValue3 / TempValue4: where it
    starts, x px out along the aim from y px below his centre. (abilities.aim_start, for Sonic CD.)"""
    step = s["x"] << 16
    return (["\t\t\tTempValue5 = 0 // the aim (tools/shots_v3.py aim_start): x -1 left / 1 right, y -1 up / 1 down",
            "\t\t\tTempValue6 = 0",
            "\t\t\tif Player.Left == true", "\t\t\t\tTempValue5 = -1", "\t\t\tend if",
            "\t\t\tif Player.Right == true", "\t\t\t\tTempValue5 = 1", "\t\t\tend if",
            "\t\t\tif Player.Up == true", "\t\t\t\tTempValue6 = -1"]
             + (["\t\t\telse", "\t\t\t\tif Player.Down == true",
                 "\t\t\t\t\tif Player.Gravity == GRAVITY_AIR // (on the ground, down is crouching)",
                 "\t\t\t\t\t\tTempValue6 = 1", "\t\t\t\t\tend if", "\t\t\t\tend if"]
                if s.get("aim_down", True) else [])  # ("aim_down" false: down never aims, 5 directions in the air too)
             + ["\t\t\tend if",
            "\t\t\tif TempValue5 == 0", "\t\t\t\tif TempValue6 == 0 // nothing held: the way he faces",
            "\t\t\t\t\tTempValue5 = 1", "\t\t\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\t\t\tTempValue5 = -1",
            "\t\t\t\t\tend if", "\t\t\t\tend if", "\t\t\tend if",
            "\t\t\tif TempValue5 != 0 // holding a side: he turns to it first, standing or in the air",
            "\t\t\t\tTempValue4 = Player.Speed", "\t\t\t\tif TempValue4 < 0", "\t\t\t\t\tFlipSign(TempValue4)",
            "\t\t\t\tend if", "\t\t\t\tif Player.Gravity == GRAVITY_AIR", "\t\t\t\t\tTempValue4 = 0", "\t\t\t\tend if",
            "\t\t\t\tif TempValue4 < 0x10000", "\t\t\t\t\tif TempValue5 < 0",
            "\t\t\t\t\t\tPlayer.Direction = FACING_LEFT", "\t\t\t\t\telse", "\t\t\t\t\t\tPlayer.Direction = FACING_RIGHT",
            "\t\t\t\t\tend if", "\t\t\t\tend if", "\t\t\tend if",
            "\t\t\tTempValue3 = TempValue5", f"\t\t\tTempValue3 *= {step:#x}", "\t\t\tTempValue3 += Player.XPos",
            "\t\t\tTempValue4 = TempValue6", f"\t\t\tTempValue4 *= {step:#x}", "\t\t\tTempValue4 += Player.YPos",
            f"\t\t\tTempValue4 += {s['y'] << 16}"])


def aim_velocity(s):
    """An aimed shot's velocity (aim_start's TempValue5 / 6): speed along an axis, abilities.shot_diag per axis on a
    diagonal; his own speed that way is added to x, so he doesn't run into it."""
    import abilities
    return ["\t\t\tTempValue4 = " + f"{s['speed']:#x} // its speed per axis (tools/shots_v3.py aim_velocity)",
            "\t\t\tif TempValue5 != 0", "\t\t\t\tif TempValue6 != 0 // a diagonal: the same speed overall",
            f"\t\t\t\t\tTempValue4 = {abilities.shot_diag(s):#x}", "\t\t\t\tend if", "\t\t\tend if",
            "\t\t\tTempValue7 = Player.XVelocity // his own speed along its x (so he doesn't run into it)",
            "\t\t\tTempValue7 *= TempValue5", "\t\t\tif TempValue7 < 0", "\t\t\t\tTempValue7 = 0", "\t\t\tend if",
            "\t\t\tTempValue7 += TempValue4", "\t\t\tTempValue7 *= TempValue5",
            "\t\t\tObject[ArrayPos0].Value0 = TempValue7",
            "\t\t\tTempValue7 = TempValue4", "\t\t\tTempValue7 *= TempValue6",
            "\t\t\tObject[ArrayPos0].Value1 = TempValue7"]


def after_lines(s, pose_frame, y_rearm, cooldown="NoSwap.ShotCooldown", which=1, two=False, down2=True, anims=None):
    """In NoSwap_AfterUpdate: Y (the DLL's, game.callbackParam3) throws a shot from the states a throw can start in
    (CD has no Super), at most max_alive out and cooldown frames apart; then, standing, the throw's last frame for `pose`
    frames. y_rearm: build_soniccd.Y_REARM. A shot with "input" "down" (Mecha's spike ball) needs down held (crouching
    too), and its caller's melee takes Y alone: then y_rearm is the melee's (empty here) and `cooldown` a value of its
    own (NoSwap.ShotCooldown is the melee's NoSwap.Shot). two: the extra has a second shot ("shot2": down + Y); which
    2: this is it (its lines go before the first's, which rearm Y; the cooldown is shared and counted down by the
    first's). With two, each counts only its own shots (by their animation: ANI_SHOT / ANI_SHOT2). anims: a swap shot's
    (swap_anims: John's sub-weapons; which 2, two), its flight's and flames' animations: it counts those. "input" "up": up
    + Y (the melee takes Y alone); "rings": each throw costs that many rings (fewer: no throw)."""
    anim = anims[0] if anims else ANI_SHOT2 if which == 2 else ANI_SHOT
    aim = bool(s.get("aim"))
    up = s.get("up", {})  # the throw with up held (abilities.py shot_up_*): its own speed / start_vy / pose frame
    g = s.get("ground", {})  # thrown standing on the ground: its own start / speed / start_vy (abilities.py shot_ground_*)
    states = []
    down = s.get("input") == "down"  # (down + Y throws; Y alone is the melee: Mecha's spike ball)
    for st in (shot_states() + (["Player_State_LookUp"] if aim or up else [])  # (aimed / up: standing)
               + (["Player_State_Crouch"] if down else [])  # (down + Y: crouching)
               + (["Player_State_Fly"] if s.get("from_flight") else [])):  # (Tails' flight: Flicky's drop)
        states += [f"\tCheckEqual(Player.State, {st})", "\tTempValue0 |= CheckResult"]
    if down:
        states += ["\tif Player.Down == false // (shot \"input\" \"down\": Y alone is the melee)", "\t\tTempValue0 = false",
                   "\tend if"]
    elif two and down2 and not anims:  # (down2 False: the second shot isn't down + Y's: a charge shot)
        states += ["\tif Player.Down == true // (down + Y throws the second shot, \"shot2\")", "\t\tTempValue0 = false",
                   "\tend if"]
    if s.get("input") == "up":  # (up + Y; Y alone is the melee: John's sub-weapons)
        states += ["\tif Player.Up == false // (shot \"input\" \"up\": Y alone is the melee)", "\t\tTempValue0 = false",
                   "\tend if"]
    if s.get("rings"):  # (a throw costs rings: "rings are hearts")
        states += [f"\tif Player.Rings < {s['rings']} // (a throw costs {s['rings']} ring(s))", "\t\tTempValue0 = false",
                   "\tend if"]
    count = (["\t\t\t\tTempValue1++"] if not two else
             [f"\t\t\t\tif Object[ArrayPos0].Animation == {anim} // (only this shot's)", "\t\t\t\t\tTempValue1++",
              "\t\t\t\tend if"])
    if anims:  # (a swap shot: its flight's and flames' animations)
        count = [f"\t\t\t\tif Object[ArrayPos0].Animation >= {anims[0]} // (only this swap shot's)",
                 f"\t\t\t\t\tif Object[ArrayPos0].Animation <= {anims[-1]}", "\t\t\t\t\t\tTempValue1++",
                 "\t\t\t\t\tend if", "\t\t\t\tend if"]
    out = ([f"if {cooldown} > 0 // Shot (tools/shots_v3.py)", f"\t{cooldown}--", "end if"] if which == 1 else []) + [
           "if game.callbackParam3 == 1 // Y, from the DLL", "\tTempValue0 = false"] + states + [
        "\tif Player.Animation == ANI_HURT", "\t\tTempValue0 = false", "\tend if",
        f"\tif {cooldown} > 0", "\t\tTempValue0 = false", "\tend if",
        "\tif TempValue0 == true",
        "\t\tTempValue1 = 0 // shots out", "\t\tTempValue2 = 0 // a free slot",
        f"\t\tArrayPos0 = {SLOTS[0]}", f"\t\twhile ArrayPos0 < {SLOTS[-1] + 1}",
        "\t\t\tif Object[ArrayPos0].Type == TypeName[Tails Object]"] + count + [
        "\t\t\telse", "\t\t\t\tif TempValue2 == 0", "\t\t\t\t\tTempValue2 = ArrayPos0", "\t\t\t\tend if", "\t\t\tend if",
        "\t\t\tArrayPos0++", "\t\tloop",
        f"\t\tif TempValue1 >= {s['max_alive']}", "\t\t\tTempValue2 = 0", "\t\tend if",
        "\t\tif TempValue2 > 0"] + (aim_start(s) if aim else [
        f"\t\t\tTempValue3 = {s['x'] << 16}", "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue3)",
        "\t\t\tend if", "\t\t\tTempValue3 += Player.XPos",
        "\t\t\tTempValue4 = Player.YPos", f"\t\t\tTempValue4 += {s['y'] << 16}"]
        + (["\t\t\tif Player.Gravity == GRAVITY_GROUND // (on the ground: shot \"ground\"'s start)",
            f"\t\t\t\tTempValue3 = {g.get('x', s['x']) << 16}", "\t\t\t\tif Player.Direction == FACING_LEFT",
            "\t\t\t\t\tFlipSign(TempValue3)", "\t\t\t\tend if", "\t\t\t\tTempValue3 += Player.XPos",
            "\t\t\t\tTempValue4 = Player.YPos", f"\t\t\t\tTempValue4 += {g.get('y', s['y']) << 16}", "\t\t\tend if"]
           if "x" in g or "y" in g else [])) + [
        "\t\t\tResetObjectEntity(TempValue2, TypeName[Tails Object], 0, TempValue3, TempValue4)",
        "\t\t\tArrayPos0 = TempValue2",
        f"\t\t\tObject[ArrayPos0].State = {LIVE}",
        "\t\t\tObject[ArrayPos0].Priority = PRIORITY_ACTIVE",
        "\t\t\tObject[ArrayPos0].DrawOrder = Player.DrawOrder",
        "\t\t\tObject[ArrayPos0].Direction = Player.Direction"] + (aim_velocity(s) if aim else [
        "\t\t\tTempValue4 = Player.XVelocity // its speed, plus his own forward (so he doesn't run into it)",
        "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue4)", "\t\t\tend if",
        "\t\t\tif TempValue4 < 0", "\t\t\t\tTempValue4 = 0", "\t\t\tend if",
        *([f"\t\t\tTempValue4 += {s['speed']:#x}"] if "speed" not in up and "speed" not in g else [
            f"\t\t\tTempValue5 = {s['speed']:#x}", "\t\t\tif Player.Up == true // up held: the up throw's own speed",
            f"\t\t\t\tTempValue5 = {up['speed']:#x}", "\t\t\tend if", "\t\t\tTempValue4 += TempValue5"] if "speed" in up else [
            f"\t\t\tTempValue5 = {s['speed']:#x}", "\t\t\tif Player.Gravity == GRAVITY_GROUND // (on the ground: shot "
            "\"ground\"'s speed)", f"\t\t\t\tTempValue5 = {g['speed']:#x}", "\t\t\tend if", "\t\t\tTempValue4 += TempValue5"]),
        "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue4)", "\t\t\tend if",
        "\t\t\tObject[ArrayPos0].Value0 = TempValue4",
        f"\t\t\tObject[ArrayPos0].Value1 = {s['start_vy'] if s['motion'] in ('bounce', 'drop', 'dip') else 0:#x}"]
        + (["\t\t\tif Player.Up == true // up held: thrown higher", f"\t\t\t\tObject[ArrayPos0].Value1 = {up['start_vy']:#x}",
            "\t\t\tend if"] if "start_vy" in up and s["motion"] == "bounce" else [])
        + (["\t\t\tif Player.Gravity == GRAVITY_GROUND // (on the ground: shot \"ground\"'s toss)",
            f"\t\t\t\tObject[ArrayPos0].Value1 = {g['start_vy']:#x}", "\t\t\tend if"] if "start_vy" in g else [])
        if s["motion"] not in ("boomerang", "homing") else [  # (a boomerang: its own speed; its update adds his, live)
        f"\t\t\tTempValue4 = {s['speed']:#x} // a boomerang: its own speed", "\t\t\tif Player.Direction == FACING_LEFT",
        "\t\t\t\tFlipSign(TempValue4)", "\t\t\tend if", "\t\t\tObject[ArrayPos0].Value0 = TempValue4",
        "\t\t\tObject[ArrayPos0].Value1 = 0", "\t\t\tObject[ArrayPos0].Value5 = 0 // flying out"]
        + ([] if s["motion"] != "homing" else [
            "\t\t\tObject[ArrayPos0].Value6 = 0 // a homing shot: no target yet, its search on (homing_body)",
            f"\t\t\t{SEEK_BEST} = {SEEK_NONE:#x}"])) + [
        "\t\t\tObject[ArrayPos0].Value2 = 0",
        *([f"\t\t\tObject[ArrayPos0].Value5 = {PIERCE} // shot \"pierce\": it flies on through what it hits"]
          if s.get("pierce") and s["motion"] != "boomerang" else []),
        *([f"\t\t\tObject[ArrayPos0].Value6 = {PIERCE6:#x} // shot \"pierce\": a boomerang flies on through what it hits"]
          if s.get("pierce") and s["motion"] == "boomerang" else []),
        f"\t\t\tObject[ArrayPos0].Value3 = {s['radius'] << 16}",
        "\t\t\tObject[ArrayPos0].Value4 = Player.CollisionPlane",
        f"\t\t\tObject[ArrayPos0].Animation = {anim}",
        "\t\t\tObject[ArrayPos0].Frame = 0", "\t\t\tObject[ArrayPos0].AnimationTimer = 0"] + (
        ["\t\t\tObject[ArrayPos0].Value6 = NoSwap.ShotNext // (cycle: this throw's frame, held)",
         "\t\t\tObject[ArrayPos0].Frame = NoSwap.ShotNext", "\t\t\tNoSwap.ShotNext++",
         f"\t\t\tif NoSwap.ShotNext >= {__import__('build_s3k_shot').frame_count(s.get('art', {}))}",
         "\t\t\t\tNoSwap.ShotNext = 0", "\t\t\tend if"] if s.get("cycle") else []) + (
        # aim_frames: its aim's frame (aim_start's TempValue5 / 6: 0 level, 1 forward-up, 2 up, 3 forward-down, 4 down),
        # held, drawn facing the way it flies (Fang's cork; abilities.shot_cycle's for Sonic 1/2)
        ["\t\t\tTempValue4 = 0 // (aim_frames: its aim's frame)", "\t\t\tif TempValue6 != 0",
         "\t\t\t\tTempValue4 = 3", "\t\t\t\tif TempValue6 < 0", "\t\t\t\t\tTempValue4 = 1", "\t\t\t\tend if",
         "\t\t\t\tif TempValue5 == 0", "\t\t\t\t\tTempValue4++", "\t\t\t\tend if", "\t\t\tend if",
         "\t\t\tObject[ArrayPos0].Value6 = TempValue4", "\t\t\tObject[ArrayPos0].Frame = TempValue4",
         "\t\t\tif TempValue5 < 0 // (drawn the way it flies)", "\t\t\t\tObject[ArrayPos0].Direction = FACING_LEFT",
         "\t\t\tend if", "\t\t\tif TempValue5 > 0", "\t\t\t\tObject[ArrayPos0].Direction = FACING_RIGHT",
         "\t\t\tend if"] if s.get("aim") and s.get("aim_frames") else []) + [
        f"\t\t\t{cooldown} = {s['cooldown']}",
        f"\t\t\tPlaySfx({s['sound']}, false)"] + (
        [f"\t\t\tPlayer.Rings -= {s['rings']} // (its cost in rings)"] if s.get("rings") else [])
    if s.get("carry") is False:  # (shot "carry" false: its own speed alone, his forward speed not added: Jet's Tornado Trap)
        carry = ["\t\t\tTempValue4 = Player.XVelocity // its speed, plus his own forward (so he doesn't run into it)",
                 "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue4)", "\t\t\tend if",
                 "\t\t\tif TempValue4 < 0", "\t\t\t\tTempValue4 = 0", "\t\t\tend if"]
        at = [k for k in range(len(out)) if out[k:k + len(carry)] == carry]
        if aim or s["motion"] in ("boomerang", "homing") or len(at) != 1:
            sys.exit("shot: \"carry\" false is for an unaimed bounce / straight / drop / dip shot")
        out[at[0]:at[0] + len(carry)] = ["\t\t\tTempValue4 = 0 // (shot \"carry\" false: its own speed alone)"]
    if s.get("both_ways"):  # (shot "both_ways": its mirror image thrown with it, the other way; abilities.check_both_ways)
        start = out.index(f"\t\t\tTempValue3 = {s['x'] << 16}")
        end = out.index(f"\t\t\t{cooldown} = {s['cooldown']}")
        block = out[start:end]
        facing = "\t\t\tObject[ArrayPos0].Direction = Player.Direction"
        if aim or two or block.count(facing) != 1 or sum("Player.Direction == FACING_LEFT" in l for l in block) != 2:
            sys.exit("shot: \"both_ways\": the throw's code isn't the one it mirrors")
        mirror = []
        for l in block:
            if l == facing:
                mirror += ["\t\t\tObject[ArrayPos0].Direction = FACING_LEFT // (the other way)",
                           "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tObject[ArrayPos0].Direction = FACING_RIGHT",
                           "\t\t\tend if"]
            else:
                mirror.append(l.replace("Player.Direction == FACING_LEFT", "Player.Direction == FACING_RIGHT"))
        out[end:end] = [
            "\t\t\tTempValue2 = 0 // shot \"both_ways\": the second, his other side, the other way (another free slot)",
            f"\t\t\tArrayPos0 = {SLOTS[0]}", f"\t\t\twhile ArrayPos0 < {SLOTS[-1] + 1}",
            "\t\t\t\tif Object[ArrayPos0].Type != TypeName[Tails Object]",
            "\t\t\t\t\tif TempValue2 == 0", "\t\t\t\t\t\tTempValue2 = ArrayPos0", "\t\t\t\t\tend if", "\t\t\t\tend if",
            "\t\t\t\tArrayPos0++", "\t\t\tloop", "\t\t\tif TempValue2 > 0"] + ["\t" + l for l in mirror] + ["\t\t\tend if"]
    pose = s.get("pose", 0) if pose_frame >= 0 else 0
    import abilities
    up_pose = up.get("pose_frame", pose_frame) if up and pose else None
    if up_pose is not None and not 0 <= up_pose <= pose_frame:
        sys.exit(f"shot: up pose_frame {up_pose} isn't a frame of the CD throw slot (0-{pose_frame})")
    always = bool(pose and s.get("pose_always"))  # (Big's cast: the pose at any speed and in the air: pose_always_*)
    if always:
        out += pose_always_set(pose)
    elif pose:
        out += ["\t\t\tif Player.Gravity == GRAVITY_GROUND", "\t\t\t\tTempValue4 = Player.Speed",
                "\t\t\t\tif TempValue4 < 0", "\t\t\t\t\tFlipSign(TempValue4)", "\t\t\t\tend if",
                "\t\t\t\tif TempValue4 < 0x10000 // standing: the throw pose", f"\t\t\t\t\tNoSwap.ShotPose = {pose}"] + (
                ["\t\t\t\t\tif Player.Up == true // (the up throw's pose)",
                 f"\t\t\t\t\t\tNoSwap.ShotPose = {pose + abilities.UP_POSE}", "\t\t\t\t\tend if"]
                if up_pose is not None else []) + [
                "\t\t\t\tend if", "\t\t\tend if"]
    out += ["\t\tend if", "\tend if", "end if"] + y_rearm
    if always:
        return out + pose_always_show(pose_frame)
    if pose:
        out += ["if NoSwap.ShotPose > 0 // the throw pose, standing: the throw's last frame",
                "\tTempValue0 = Player.Speed", "\tif TempValue0 < 0", "\t\tFlipSign(TempValue0)", "\tend if",
                "\tTempValue1 = false", "\tif Player.Gravity == GRAVITY_GROUND", "\t\tif TempValue0 < 0x10000",
                "\t\t\tif Player.Animation != ANI_HURT", "\t\t\t\tTempValue1 = true", "\t\t\tend if", "\t\tend if",
                "\tend if",
                "\tif TempValue1 == true", "\t\tPlayer.Animation = ANI_NOSWAP_SHOT", f"\t\tPlayer.Frame = {pose_frame}"] + (
                [f"\t\tif NoSwap.ShotPose > {abilities.UP_POSE} // after an up throw: its own pose frame",
                 f"\t\t\tPlayer.Frame = {up_pose}", "\t\tend if"] if up_pose is not None else []) + [
                "\t\tPlayer.AnimationTimer = 0", "\t\tNoSwap.ShotPose--"] + (
                [f"\t\tif NoSwap.ShotPose == {abilities.UP_POSE}", "\t\t\tNoSwap.ShotPose = 0", "\t\tend if"]
                if up_pose is not None else []) + ["\t\tif NoSwap.ShotPose == 0",
                "\t\t\tPlayer.Animation = ANI_STOPPED", "\t\tend if",
                "\telse", "\t\tNoSwap.ShotPose = 0", "\tend if", "end if"]
    if pose and s.get("aim_pose"):
        out = aim_pose_lines(out, pose, pose_frame)
    if s.get("autofire"):  # (Y held, from the DLL: 2 each frame while the script keeps build_soniccd.Y_REARM_HOLD's number)
        press = "if game.callbackParam3 == 1 // Y, from the DLL"
        if out.count(press) != 1 or which != 1:
            sys.exit("shot: \"autofire\": the throw's Y test isn't there once")
        k = out.index(press)
        out[k:k] = ["if game.callbackParam3 == 2 // (shot \"autofire\": Y held, from the DLL: a throw every cooldown frames)",
                    "\tgame.callbackParam3 = 1", "end if"]
    return out


def aim_pose_lines(out, pose, pose_frame):
    """Shot "aim_pose" (Ray Poward's run-and-gun; abilities.shot_aim_pose): the standing pose shows its aim's frame of
    the throw slot (0 level, 1 forward-up, 2 up; aim_start's TempValue5 / 6), not the last: NoSwap.ShotPose = frames left
    + abilities.UP_POSE * that frame."""
    import abilities
    k = abilities.UP_POSE
    pose_set = f"\t\t\t\t\tNoSwap.ShotPose = {pose}"
    frame = f"\t\tPlayer.Frame = {pose_frame}"
    end = ["\t\tNoSwap.ShotPose--", "\t\tif NoSwap.ShotPose == 0"]
    at = [n for n in range(len(out) - 1) if out[n:n + 2] == end]
    if out.count(pose_set) != 1 or out.count(frame) != 1 or len(at) != 1:
        sys.exit("shot: \"aim_pose\": the pose's code isn't the one it changes")
    n = out.index(frame)
    out[n:n + 1] = ["\t\tTempValue2 = NoSwap.ShotPose // (shot \"aim_pose\": its aim's frame)", f"\t\tTempValue2 /= {k}",
                    "\t\tPlayer.Frame = TempValue2"]
    n = [m for m in range(len(out) - 1) if out[m:m + 2] == end][0] + 1
    out[n:n] = ["\t\tTempValue2 = NoSwap.ShotPose // (its frames left: the offset aside)", f"\t\tTempValue2 %= {k}",
                "\t\tif TempValue2 == 0", "\t\t\tNoSwap.ShotPose = 0", "\t\tend if"]
    n = out.index(pose_set)
    out[n:n + 1] = ["\t\t\t\t\tTempValue7 = 0 // (shot \"aim_pose\": its aim's frame, 0 level, 1 forward-up, 2 up)",
                    "\t\t\t\t\tif TempValue6 != 0", "\t\t\t\t\t\tTempValue7 = 3", "\t\t\t\t\t\tif TempValue6 < 0",
                    "\t\t\t\t\t\t\tTempValue7 = 1", "\t\t\t\t\t\tend if", "\t\t\t\t\t\tif TempValue5 == 0",
                    "\t\t\t\t\t\t\tTempValue7++", "\t\t\t\t\t\tend if", "\t\t\t\t\tend if",
                    f"\t\t\t\t\tTempValue7 *= {k}", f"\t\t\t\t\tTempValue7 += {pose}", "\t\t\t\t\tNoSwap.ShotPose = TempValue7"]
    return out


def pose_always_set(pose):
    """Shot "pose_always" (Big's cast; abilities.shot_pose_always_set): the throw pose on the ground at any speed (not
    rolling: the roll goes on), and in the air over whatever shows (the jump ball too), which comes back after it
    (NoSwap.ShotPose = -(frames left + abilities.POSE_PREV * that animation)). CD has one throw slot (46), for both."""
    import abilities
    k = abilities.POSE_PREV
    return ["\t\t\tif Player.Gravity == GRAVITY_GROUND",
            "\t\t\t\tif Player.State != Player_State_Roll // (rolling: no pose, the roll goes on)",
            f"\t\t\t\t\tNoSwap.ShotPose = {pose}", "\t\t\t\tend if",
            "\t\t\telse", "\t\t\t\tTempValue4 = 0", "\t\t\t\tif NoSwap.ShotPose < 0 // (a pose still showing: what it replaced)",
            "\t\t\t\t\tTempValue4 = NoSwap.ShotPose", "\t\t\t\t\tFlipSign(TempValue4)", f"\t\t\t\t\tTempValue4 /= {k}",
            "\t\t\t\tend if", "\t\t\t\tif Player.Animation != ANI_NOSWAP_SHOT", "\t\t\t\t\tTempValue4 = Player.Animation",
            "\t\t\t\tend if", f"\t\t\t\tTempValue4 *= {k}", f"\t\t\t\tTempValue4 += {pose}", "\t\t\t\tFlipSign(TempValue4)",
            "\t\t\t\tNoSwap.ShotPose = TempValue4", "\t\t\tend if"]


def pose_always_show(pose_frame):
    """Shot "pose_always": the pose's frames (see pose_always_set). On the ground the game picks his animation each
    frame and this puts the pose over it; off a ledge it ends in the fall pose. In the air it goes over anything until
    its frames run out, a hit or landing; the last animation anything else gave him comes back after it."""
    import abilities
    k = abilities.POSE_PREV
    return ["if NoSwap.ShotPose > 0 // the throw pose on the ground (shot \"pose_always\": at any speed; not rolling)",
            "\tTempValue1 = false", "\tif Player.Gravity == GRAVITY_GROUND", "\t\tif Player.Animation != ANI_HURT",
            "\t\t\tTempValue1 = true", "\t\tend if", "\t\tif Player.State == Player_State_Roll", "\t\t\tTempValue1 = false",
            "\t\tend if", "\tend if",
            "\tif TempValue1 == true", "\t\tPlayer.Animation = ANI_NOSWAP_SHOT", "\t\tPlayer.PrevAnimation = ANI_NOSWAP_SHOT",
            f"\t\tPlayer.Frame = {pose_frame}", "\t\tPlayer.AnimationTimer = 0", "\t\tNoSwap.ShotPose--",
            "\t\tif NoSwap.ShotPose == 0", "\t\t\tPlayer.Animation = ANI_STOPPED", "\t\t\tif Player.Speed != 0",
            "\t\t\t\tPlayer.Animation = ANI_WALKING", "\t\t\tend if", "\t\tend if",
            "\telse", "\t\tNoSwap.ShotPose = 0", "\t\tif Player.Animation == ANI_NOSWAP_SHOT // (off a ledge: the fall pose)",
            "\t\t\tPlayer.Animation = ANI_WALKING", "\t\tend if", "\tend if", "end if",
            "if NoSwap.ShotPose < 0 // the throw pose in the air (shot \"pose_always\": over whatever shows)",
            "\tTempValue1 = false", "\tif Player.Gravity == GRAVITY_AIR", "\t\tif Player.Animation != ANI_HURT",
            "\t\t\tTempValue1 = true", "\t\tend if", "\tend if",
            "\tif TempValue1 == true", "\t\tTempValue0 = NoSwap.ShotPose", "\t\tFlipSign(TempValue0)",
            "\t\tTempValue1 = TempValue0", f"\t\tTempValue1 %= {k} // frames left", f"\t\tTempValue0 /= {k} // what it replaced",
            "\t\tif Player.Animation != ANI_NOSWAP_SHOT // (something else gave him an animation: that comes back after)",
            "\t\t\tTempValue0 = Player.Animation", "\t\tend if", "\t\tTempValue1--",
            "\t\tif TempValue1 == 0 // the pose is over: what it replaced (the jump ball, a fall, a spring...)",
            "\t\t\tPlayer.Animation = TempValue0", "\t\t\tNoSwap.ShotPose = 0",
            "\t\telse", "\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT", "\t\t\tPlayer.PrevAnimation = ANI_NOSWAP_SHOT",
            f"\t\t\tPlayer.Frame = {pose_frame}", "\t\t\tPlayer.AnimationTimer = 0", f"\t\t\tTempValue0 *= {k}",
            "\t\t\tTempValue0 += TempValue1", "\t\t\tFlipSign(TempValue0)", "\t\t\tNoSwap.ShotPose = TempValue0",
            "\t\tend if", "\telse", "\t\tNoSwap.ShotPose = 0", "\tend if", "end if"]


# ---------------------------------------------------------------- the art (in the package's own player .ani and sheet)
def shot_frames(e, s, palette=None):
    """The shot's frames, [(P-mode image in the extra's palette slots, pivot x, pivot y)]: the one art source (the S3&K
    recipe's, as in S1/S2: build_s3k_shot.frames; palette: the slots a spark may use)."""
    import build_s3k_shot
    return build_s3k_shot.frames(s.get("art", {}), e, palette)


def free_spot(sheet, taken, w, h):
    """(x, y) of a w x h spot with no pixel and no frame's box in it, inside the .ani's reach (x, y are bytes)."""
    import numpy as np
    a = np.array(sheet)
    busy = a != 0
    for (x, y, fw, fh) in taken:
        busy[y:y + fh, x:x + fw] = True
    H, W = busy.shape
    for y in range(0, min(H, 256) - h + 1):
        for x in range(0, min(W, 256) - w + 1):
            if not busy[y:y + h, x:x + w].any():
                return x, y
    return None


def place_art(e, s, data, s2=None):
    """The shot's frames into the package's own CD player art (data: its SonicCDu/Data): pasted pixel for pixel on a
    free spot of one of its player sheets (1 px apart, off every frame's box) and animation ANI_SHOT of its .ani
    naming them. No new sheet: the TailsObject.txt shot loads the player's own animation file. s2: a second shot
    ("shot2"), likewise, as animation ANI_SHOT2."""
    where = place_one(e, s, data, ANI_SHOT)
    return where + (f"; its second shot: {place_one(e, s2, data, ANI_SHOT2)}" if s2 else "")


def place_swap_art(e, shots, data):
    """Swap shots' frames (one per monitor_swap entry: John's sub-weapons) into the package's CD player art, as place_art
    does a plain shot's: entry k's flight as animation swap_anims(k)[0], a burning one's flames as [1]."""
    where = []
    for k, s in enumerate(shots):
        fly, burn = swap_anims(k)
        where.append(place_one(e, s, data, fly, f"NoSwap Swap Shot {k}"))
        if "burn" in s:
            where.append(place_one(e, dict(s, art=s["burn"]["art"]), data, burn, f"NoSwap Swap Shot {k} Flames"))
    return "; ".join(where)


def place_one(e, s, data, anim, anim_name=None):
    """place_art for one shot, as animation `anim` (its name: `name`, or NoSwap Shot / NoSwap Shot 2)."""
    import extras
    import sheet2ani
    from PIL import Image
    from gifio import save_sheet
    frames = shot_frames(e, s)
    ani_path = data / "Animations" / extras.PLAYER_ANI
    ani = sheet2ani.read_ani(ani_path)
    if len(ani["anims"]) > anim:
        sys.exit(f"{e['name']}: its CD .ani has {len(ani['anims'])} animations: slot {anim} (shots_v3.ANI_SHOT / 2) is taken")
    w = sum(im.width + 1 for im, _, _ in frames) + 1
    h = max(im.height for im, _, _ in frames) + 2
    for k, name in enumerate(ani["sheets"]):
        path = data / "Sprites" / name
        sheet = Image.open(path)
        if sheet.mode != "P":
            sys.exit(f"{path}: not a paletted sheet")
        taken = [(f["x"], f["y"], f["w"], f["h"]) for a in ani["anims"] for f in a["frames"] if f["sheet"] == k]
        spot = free_spot(sheet, taken, w, h)
        if spot:
            break
    else:
        sys.exit(f"{e['name']}: no free {w}x{h} spot for its shot on its CD player sheets (shots_v3.place_art)")
    used = set(sheet.getdata())
    if "spark" in s.get("art", {}):  # (its colours: the ones this sheet uses; the sizes don't change)
        import build_s3k_shot
        frames = shot_frames(e, s, build_s3k_shot.sheet_slots(sheet))
    if "sheet" in s.get("art", {}):  # (a drawing of the extra's own: the colours any of its CD player sheets use, all
        # in the one player palette; the sizes don't change)
        import build_s3k_shot
        slots = {}
        for other in ani["sheets"]:
            slots.update(build_s3k_shot.sheet_slots(Image.open(data / "Sprites" / other)))
        if s["art"].get("own_slots"):  # (the recipe's "own_slots": all its own colours, which its palette file loads)
            slots.update(build_s3k_shot.own_palette(e))
        frames = shot_frames(e, s, slots)
        used |= set(slots)
    out, x = [], spot[0] + 1
    for im, px, py in frames:
        if not set(im.getdata()) - {0} <= used:
            sys.exit(f"{e['name']}: its shot's colours aren't all on its CD player sheet {name}")
        sheet.paste(im, (x, spot[1] + 1))
        out.append(dict(sheet=k, hitbox=0, x=x, y=spot[1] + 1, w=im.width, h=im.height, px=px, py=py))
        x += im.width + 1
    save_sheet(sheet, path)
    while len(ani["anims"]) < anim:
        ani["anims"].append(dict(name="(unused)", speed=0, loop=0, rot=0, frames=[]))
    ani["anims"].append(dict(name=anim_name or ("NoSwap Shot" if anim == ANI_SHOT else "NoSwap Shot 2"), speed=0, loop=0,
                             rot=0, frames=out))
    sheet2ani.write_ani(ani_path, ani)
    return f"{name} at {spot}"
