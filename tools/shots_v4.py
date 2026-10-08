#!/usr/bin/env python3
"""Sonic 1 / Sonic 2 (RSDKv4) projectiles: an extra's "shot" (abilities.py), a real object that flies on its own and
hits badniks, monitors and bosses exactly as a jumping player does. The S3&K version is the DLL's (NoSwapS3K.cpp
namespace shots); this one is all script.

How it works (the design from the 2026-09-27 research, approved by the user):
- The shot's object type is the game's "Tails Object" (global object 2, Players/TailsObject.txt). The game only makes
  one when player 1 *is* Tails, and its ObjectStartup loads nothing for anyone else, so while an extra plays the type
  is free. NoSwap ships a TailsObject.txt (tails_object) whose events, for an extra (stage.playerListPos >= 7), load the
  shot's sheet, run the player script's NoSwap_ShotUpdate and draw the frame it picks. Tails' own code is untouched.
- No new sheet (a separate Players/NoSwapShot.gif drew nothing in Sonic 1, 2026-09-27: its sprite surfaces/memory are
  full): the shot's frames are in a reserved strip of the extra's own first player sheet (SHEET, extras.player_sheet(1),
  which its NoSwapExtra.ani names, so it's always loaded), rows RESERVED_Y and down, in fixed boxes (SHEET_BOXES). An
  .ani frame's x/y are bytes, so no player frame can ever reach there. The engine keeps one surface per sheet name
  (AddGraphicsFile returns the one already loaded; vanilla TailsObject.txt / Player2Object.txt load Tails.ani's own
  Players/Tails1.gif the same way), so this costs only the strip's rows. place_art adds the strip to packages with a
  shot; the others' sheets (and NoSwap's placeholder) stay as they are: they never make a shot, so nothing draws it.
- The badniks, monitors and bosses test the players in `foreach (GROUP_PLAYERS, currentPlayer, ACTIVE_ENTITIES)`
  loops and call the player script's Player_BadnikBreak / Player_CheckHit, which decide from
  player[currentPlayer].animation. A shot is in its own group (GROUP, which the engine already accepts: S1's special
  stage uses 0x101 for its blocks; no normal stage does), and loop_copies gives every such loop a copy for that group
  right after it. The shot looks like a jumping player to them (animation ANI_JUMPING, its hitbox in value38-41,
  isSidekick false, gravity GRAVITY_GROUND for the monitors), so the game's own code gives the game's own outcome:
  explosion, animal and score; the monitor's item to player 1; the boss's hit, flash and sound.
- The copies can't hurt the shot or double anything: any other Player_ call in a copy (Player_Hit, Player_Kill...)
  only marks the shot spent; C_BOX (a hitbox from an animation file, which the shot has none of) becomes the shot's
  own box; a target already gone (blank, or a monitor already broken) is skipped; after a hit the shot is marked
  spent (object.state no longer LIVE) and vanishes in its own update, before it's drawn. Loops that keep a player's
  slot (Grabber and Jellygnite grab players) get only their hit test (the minimal copy), so nothing holds a shot.
- Without an extra with a shot nothing ever joins the group: the copies loop over nothing.
"""
import os
import re
import sys

from PIL import Image

GROUP = "0x101"  # the shots' group (object.groupID)
LIVE = 0x7E57  # a shot's object.state while it flies; anything else (0 from a copy, a Player_State_ from a game script):
# spent. (A player state is a function number; no stage has anywhere near this many functions.)
SHEET = "Players/NoSwapExtra_1.gif"  # (relative to Data/Sprites: extras.player_sheet(1)) the shot's frames, in fixed boxes
RESERVED_Y = 256  # the strip's first row: past any .ani frame's reach (its x/y are bytes)
BOX_W, BOX_H, FRAMES = 64, 32, 4  # SHEET_BOXES: FRAMES boxes of BOX_W x BOX_H, side by side, the pivot at each one's centre
SHEET_BOXES = [(k * BOX_W, RESERVED_Y, BOX_W, BOX_H) for k in range(FRAMES)]
# The big boxes, for art taller than BOX_H (Mecha Sonic's 48 px spike ball): the same columns, BIG_H rows, as TailsObject
# frames FRAMES and up. A package uses one set or the other (big), so the others' sheets keep their 32-row strip.
BIG_H = 64
BIG_BOXES = [(k * BOX_W, RESERVED_Y, BOX_W, BIG_H) for k in range(FRAMES)]
# A second shot ("shot2", abilities.py: Robotnik's Bomb Drop): its frames in a second row of boxes under the first's big
# ones, as TailsObject frames ROW2_FRAME and up (small), ROW2_FRAME + FRAMES and up (big); a shot's frame tells which one
# it is (abilities.shot_update_body). Only a package with a second shot has that row; the frames are there for all.
ROW2_Y = RESERVED_Y + BIG_H
ROW2_FRAME = 2 * FRAMES
SHEET_BOXES2 = [(x, ROW2_Y, w, h) for x, _, w, h in SHEET_BOXES]
BIG_BOXES2 = [(x, ROW2_Y, w, h) for x, _, w, h in BIG_BOXES]
# Swap shots ("swap_shots", abilities.py: John Morris' sub-weapons, one per monitor_swap entry, each with its own frames,
# and a burning one's flames too): TailsObject frames SWAP_FRAME and up, small boxes (BOX_W x BOX_H) SWAP_COLUMNS to a row
# from RESERVED_Y down (a package with them has no plain shot: the rows are its own), each entry's frames in turn
# (abilities.swap_layout); a shot's frame tells its entry. Only a package with them has the rows.
SWAP_FRAME = 4 * FRAMES
SWAP_COLUMNS, SWAP_ROWS = 4, 4
SWAP_BOXES = [(k % SWAP_COLUMNS * BOX_W, RESERVED_Y + k // SWAP_COLUMNS * BOX_H, BOX_W, BOX_H)
              for k in range(SWAP_COLUMNS * SWAP_ROWS)]
TARGET_CALLS = ("Player_BadnikBreak", "Player_CheckHit")
MONITOR = "Global/Monitor.txt"
SPENT = "object[currentPlayer].state = 0 // [NoSwap] a shot: spent (it vanishes in its own update)"
# A homing shot's target search (motion "homing": Cream's Cheese; abilities.homing_update_body): every copy's first line
# (not the monitor's) calls SEEK, a public function of TailsObject.txt (seek_function), with the enemy as `object` and
# the shot as object[currentPlayer]. While the shot seeks (its value43 1) it keeps the nearest on-screen enemy it's shown
# (value44 its distance to the shot, px across + down, SEEK_NONE none; value45 / 46 its xpos / ypos; value31 / 32
# scratch), which its own update reads and resets. No other shot sets value43, so for them it does nothing. (Those
# values are player aliases no game script reads of another player: acceleration-style ones only a player's own
# code uses.)
SEEK = "NoSwap_ShotSeek"
SEEK_NONE = 0x7FFF
HITBOX = ("object[currentPlayer].value40, object[currentPlayer].value38, object[currentPlayer].value41, "
          "object[currentPlayer].value39")  # the shot's box: left, top, right, bottom (the players' hitbox values)


def code(line):
    return line.split("//")[0].strip()


def indent(line):
    return line[: len(line) - len(line.lstrip("\t"))]


def player_loops(lines):
    """(first, last) line numbers of each `foreach (GROUP_PLAYERS, currentPlayer, ...)` ... `next` (any nesting)."""
    stack, out = [], []
    for i, l in enumerate(lines):
        c = code(l)
        if c.startswith("foreach"):
            stack.append(i)
        elif c == "next":
            if not stack:
                sys.exit(f"shots: unbalanced next at line {i + 1}")
            start = stack.pop()
            if re.match(r"foreach \(GROUP_PLAYERS, currentPlayer, ACTIVE_ENTITIES\)$", code(lines[start])):
                out.append((start, i))
    return out


def qualifies(body, name):
    text = "\n".join(code(l) for l in body)
    if any(f"CallFunction({f})" in text for f in TARGET_CALLS):
        return True
    return name == MONITOR and "TypeName[Broken Monitor]" in text


# Lines a copy rewrites instead of keeping: S2's monitor remembers who broke it and gives that player the item
REWRITES = {"object.rewardPlayer = currentPlayer": "object.rewardPlayer = 0 // [NoSwap] a shot's monitor: the item to player 1"}


def keeps_player(body):
    """The loop stores a player's slot (Grabber / Jellygnite grab players): its copy gets only its hit tests."""
    return any(re.search(r"(?<![=!<>])=\s*currentPlayer\b", code(l)) and not code(l).startswith(("if ", "foreach"))
               and code(l) not in REWRITES for l in body)


def seek_line(ind, name):
    """The copy's first line: a homing shot's target search (SEEK), for any target but the monitor."""
    return [] if name == MONITOR else [f"{ind}CallFunction({SEEK}) // a homing shot: this one's a target (tools/shots_v4.py)"]


def full_copy(body, ind, guard, name=None):
    """The loop's own body for the shots' group (see the module's notes)."""
    out = [f"{ind}foreach ({GROUP}, currentPlayer, ACTIVE_ENTITIES) // [NoSwap] an extra's shots, as the players above "
           "(tools/shots_v4.py)",
           f"{ind}\tif {guard}"] + seek_line(ind + "\t\t", name)
    for l in body[1:-1]:
        c = code(l)
        if l.lstrip().startswith("#"):
            out.append(l)  # (#platform lines stay at the start of the line)
            continue
        l2 = "\t" + l
        l2 = l2.replace("currentPlayer, C_BOX, C_BOX, C_BOX, C_BOX)", f"currentPlayer, {HITBOX})")
        if "C_BOX" in code(l2):
            sys.exit(f"shots: a C_BOX the copy can't give the shot's box: {l.strip()}")
        m = re.fullmatch(r"CallFunction\((Player_\w+)\)", c)
        if m and m.group(1) == "Player_BadnikBreak":
            out += [l2, f"{indent(l2)}{SPENT}"]
        elif m and m.group(1) == "Player_CheckHit":
            out += [l2, f"{indent(l2)}if checkResult == true", f"{indent(l2)}\t{SPENT}", f"{indent(l2)}end if"]
        elif m:  # (Player_Hit, Player_Kill, Player_FireHit...: nothing hurts a shot; it fizzles)
            out.append(f"{indent(l2)}{SPENT.replace('spent', 'fizzles (instead of ' + m.group(1) + ')')}")
        elif c in REWRITES:
            out.append(indent(l2) + REWRITES[c])
        elif c == "object.type = TypeName[Broken Monitor]":
            out += [l2, f"{indent(l2)}{SPENT}"]
        else:
            out.append(l2)
    return out + [f"{ind}\tend if", f"{ind}next"]


def minimal_copy(body, ind, name):
    """Only the loop's badnik hit tests: each Player_BadnikBreak with the box test just before it."""
    tests = []
    for k, l in enumerate(body):
        if code(l) == "CallFunction(Player_BadnikBreak)":
            box = next((code(body[j]) for j in range(k - 1, 0, -1) if code(body[j]).startswith("BoxCollisionTest(")), None)
            if not box or "player[currentPlayer].hitboxLeft" not in box:
                sys.exit(f"shots: {name}: no player hitbox test before a Player_BadnikBreak")
            if box not in tests:
                tests.append(box)
    if not tests or any(f"CallFunction({f})" in code(l) for l in body for f in TARGET_CALLS[1:]):
        sys.exit(f"shots: {name}: a loop keeping a player's slot with no badnik test (or a boss's): look at it")
    out = [f"{ind}foreach ({GROUP}, currentPlayer, ACTIVE_ENTITIES) // [NoSwap] an extra's shots: only the hit test "
           "(this one grabs players; tools/shots_v4.py)",
           f"{ind}\tif object.type != TypeName[Blank Object]"] + seek_line(ind + "\t\t", name)
    for box in tests:
        out += [f"{ind}\t\t{box}", f"{ind}\t\tif checkResult == true", f"{ind}\t\t\tCallFunction(Player_BadnikBreak)",
                f"{ind}\t\t\t{SPENT}", f"{ind}\t\tend if"]
    return out + [f"{ind}\tend if", f"{ind}next"]


def check_after(lines, end, name):
    """Nothing right after the loop reads checkResult before setting it (the copy would change it)."""
    for l in lines[end + 1:]:
        c = code(l)
        if re.match(r"end (event|function)", c):
            return
        if c.startswith(("checkResult =", "BoxCollisionTest(", "ObjectTileCollision(", "ObjectTileGrip(", "Check",
                         "CallFunction(", "Rand(checkResult")):
            return  # set before anything reads it
        if "checkResult" in c:
            sys.exit(f"shots: {name}: checkResult is read after a player loop: {c}")


def loop_copies(t, name):
    """A copy of every player loop that hits badniks, monitors or bosses, for the shots' group (the module's notes)."""
    lines = t.split("\n")
    loops = [(s, e) for s, e in player_loops(lines) if qualifies(lines[s:e + 1], name)]
    if not loops:
        sys.exit(f"shots: {name}: no player loop to copy")
    guard = "object.type == TypeName[Monitor]" if name == MONITOR else "object.type != TypeName[Blank Object]"
    for s, e in sorted(loops, reverse=True):
        body = lines[s:e + 1]
        check_after(lines, e, name)
        copy = minimal_copy(body, indent(lines[s]), name) if keeps_player(body) else full_copy(body, indent(lines[s]),
                                                                                                    guard, name)
        lines[e + 1:e + 1] = copy
    return "\n".join(lines)


def target_scripts(base):
    """The game's scripts with a loop loop_copies copies (not the players' own scripts)."""
    out = []
    for p in sorted(base.rglob("*.txt")):
        rel = p.relative_to(base).as_posix()
        if rel.startswith(("Players/", "Special/")):
            continue
        lines = p.read_bytes().decode("utf-8", errors="ignore").replace("\r\n", "\n").split("\n")
        if any(qualifies(lines[s:e + 1], rel) for s, e in player_loops(lines)):
            out.append(rel)
    return out


def compose(first, then):
    return (lambda t: then(first(t))) if first else then


def add_builders(builders, base):
    """The shot's scripts into a game builder's BUILDERS: every target script (after its own builder, if it has one)
    and TailsObject.txt."""
    for rel in target_scripts(base):
        builders[rel] = compose(builders.get(rel), lambda t, rel=rel: loop_copies(t, rel))
    builders["Players/TailsObject.txt"] = compose(builders.get("Players/TailsObject.txt"), tails_object)
    return builders


def wrap_event(t, event, extra, name):
    """`event` runs `extra` for an extra (stage.playerListPos >= 7) and its own code for anyone else."""
    start = t.index(f"event {event}\n")
    end = t.index("\nend event\n", start)
    body = t[start + len(f"event {event}\n"):end]
    new = ("\tif stage.playerListPos >= 7 // [NoSwap] an extra: this type is its shots (tools/shots_v4.py)\n"
           + "".join(f"\t\t{l}\n" for l in extra) + "\telse\n" + body + "\n\tend if")
    return t[:start] + f"event {event}\n" + new + t[end:]


def seek_function():
    """SEEK (see its notes above SEEK): object is the enemy, object[currentPlayer] the shot. Only values of the shot are
    written (no temps: the enemy's own code goes on after the copy)."""
    s = "object[currentPlayer]"
    return f"""// [NoSwap] A homing shot's target search (tools/shots_v4.py SEEK): each enemy's shot loop copy calls this first
// (object: the enemy; {s}: a shot). A seeking homing shot (value43 1) keeps the nearest enemy on screen it's shown
// (value44 its distance, px; value45 / 46 its position), which its own update reads and resets
public function {SEEK}
	if {s}.value43 == 1
		{s}.value31 = object.ixpos
		{s}.value31 -= screen.xoffset
		if {s}.value31 >= 0
			if {s}.value31 < screen.xsize
				{s}.value31 = object.iypos
				{s}.value31 -= screen.yoffset
				if {s}.value31 >= 0
					if {s}.value31 < screen.ysize
						{s}.value31 = object.ixpos
						{s}.value31 -= {s}.ixpos
						if {s}.value31 < 0
							FlipSign({s}.value31)
						end if
						{s}.value32 = object.iypos
						{s}.value32 -= {s}.iypos
						if {s}.value32 < 0
							FlipSign({s}.value32)
						end if
						{s}.value31 += {s}.value32
						if {s}.value31 < {s}.value44
							{s}.value44 = {s}.value31
							{s}.value45 = object.xpos
							{s}.value46 = object.ypos
						end if
					end if
				end if
			end if
		end if
	end if
end function


"""


def tails_object(t):
    """Players/TailsObject.txt: Tails' as it is, and for an extra its shots (the module's notes). NoSwap_ShotUpdate is
    the player script's (a stub where the extra has no shot, which blanks one: none ever exists)."""
    for event in ("ObjectUpdate", "ObjectDraw", "ObjectStartup"):
        if t.count(f"event {event}\n") != 1:
            sys.exit(f"shots: TailsObject.txt: expected one {event}")
    frames = [f"SpriteFrame({-w // 2}, {-h // 2}, {w}, {h}, {x}, {y}) // box {k}" for k, (x, y, w, h) in
              enumerate(SHEET_BOXES)]
    frames += [f"SpriteFrame({-w // 2}, {-h // 2}, {w}, {h}, {x}, {y}) // big box {k} (a package with big art: big)" for k,
               (x, y, w, h) in enumerate(BIG_BOXES)]
    frames += [f"SpriteFrame({-w // 2}, {-h // 2}, {w}, {h}, {x}, {y}) // second-row {kind}box {k} (a second shot's: shot2)"
               for kind, boxes in (("", SHEET_BOXES2), ("big ", BIG_BOXES2)) for k, (x, y, w, h) in enumerate(boxes)]
    frames += [f"SpriteFrame({-w // 2}, {-h // 2}, {w}, {h}, {x}, {y}) // swap box {k} (swap shots' frames: John's sub-weapons)"
               for k, (x, y, w, h) in enumerate(SWAP_BOXES)]
    first = t.index("event ObjectUpdate\n")  # (the shots' target search, public: the enemies' scripts call it)
    t = t[:first] + seek_function() + t[first:]
    t = wrap_event(t, "ObjectUpdate", ["CallFunction(NoSwap_ShotUpdate)"], "update")
    probe = (["if object.value30 == 0 // [probe] its first draw: the Jump sound", "\tobject.value30 = 1",
              "\tPlaySfx(SfxName[Jump], false)", "end if"] if os.environ.get("NOSWAP_SHOT_PROBE") else [])
    # (value36, flyCarryTimer, which no shot sets: a Screen Nuke's object, abilities.py melee_nuke, draws the screen's fade
    # to black by that much instead; -1: nothing)
    t = wrap_event(t, "ObjectDraw", probe + ["if object.value36 == 0",
                                             "\tDrawSpriteFX(object.frame, FX_FLIP, object.xpos, object.ypos)",
                                             "else",
                                             "\tif object.value36 > 0 // a Screen Nuke's flash (abilities.py melee_nuke)",
                                             "\t\tSetScreenFade(0, 0, 0, object.value36)",
                                             "\tend if",
                                             "end if"], "draw")
    return wrap_event(t, "ObjectStartup", [f'LoadSpriteSheet("{SHEET}") // the extra\'s own player sheet (its .ani\'s, '
                                           "already loaded): the shot's frames are in its reserved strip"]
                      + frames, "startup")


# ---------------------------------------------------------------- the sheet
def fits(frames, boxes):
    """Every frame (P-mode image, pivot x, pivot y) fits its box with its pivot at the box's centre."""
    for (im, px, py), (x, y, w, h) in zip(frames, boxes):
        at = (x + w // 2 + px, y + h // 2 + py)
        if at[0] < x or at[1] < y or at[0] + im.width > x + w or at[1] + im.height > y + h:
            return False
    return True


def big(frames):
    """The frames need the big boxes (BIG_BOXES: TailsObject frames FRAMES and up)."""
    return not fits(frames, SHEET_BOXES)


def place_swap_art(frames, sheet_path):
    """Swap shots' frames (abilities.swap_layout's order: every entry's flight frames, then a burning one's flames), each
    pasted pixel for pixel in its SWAP_BOXES box of the package's player sheet sheet_path (its pivot at the box's
    centre), as place_art does the plain shot's."""
    from gifio import save_sheet
    if len(frames) > len(SWAP_BOXES):
        sys.exit(f"shots: {len(frames)} swap shot frames, the strip has {len(SWAP_BOXES)} boxes")
    sheet = Image.open(sheet_path)
    sheet.load()
    if sheet.mode != "P" or sheet.height > RESERVED_Y or sheet.width < SWAP_COLUMNS * BOX_W:
        sys.exit(f"shots: {sheet_path} is {sheet.mode} {sheet.width}x{sheet.height}: expected a paletted sheet at least "
                 f"{SWAP_COLUMNS * BOX_W} wide and at most {RESERVED_Y} high")
    boxes = SWAP_BOXES[:len(frames)]
    out = Image.new("P", (sheet.width, max(y + h for _, y, _, h in boxes)), 0)
    out.putpalette(sheet.getpalette())
    out.paste(sheet, (0, 0))
    for (im, px, py), (x, y, w, h) in zip(frames, boxes):
        at = (x + w // 2 + px, y + h // 2 + py)
        if at[0] < x or at[1] < y or at[0] + im.width > x + w or at[1] + im.height > y + h:
            sys.exit(f"shots: a {im.width}x{im.height} swap shot frame (pivot {px},{py}) doesn't fit its {w}x{h} box")
        out.paste(im, at)
    save_sheet(out, sheet_path)


def place_art(frames, sheet_path, frames2=None, held=False):
    """frames: [(P-mode image, pivot x, pivot y)] (build_s3k_shot.flame_frames, in the extra's own palette slots, which
    its player script sets): each pasted pixel for pixel in its box of the reserved strip of the package's player sheet
    sheet_path (SHEET), its pivot at the box's centre. The sheet grows by the strip's rows (it's written afresh by
    build_packages.build_player_art each build); its palette and every other pixel stay as they are. frames2: a second
    shot's ("shot2"), in the second row (ROW2_Y), which the strip then reaches down to. held: the shot's frame is
    picked, not animated (shot "aim_frames": abilities.shot_cycle maps it), so "two_rows" art may be small in its first
    row too (its frames past FRAMES are then TailsObject frames ROW2_FRAME and up, not straight after the first row's)."""
    from PIL import Image
    from gifio import save_sheet
    more = frames[FRAMES:]  # (art "two_rows": frames past the first row's go on in the second row's small boxes)
    frames = frames[:FRAMES]
    if more and (frames2 or len(more) > FRAMES or not (big(frames) or held) or not fits(more, SHEET_BOXES2)):
        sys.exit(f"shots: {len(frames) + len(more)} frames: past {FRAMES} only with big art in the first row, no second "
                 f"shot, and at most {FRAMES} more that fit the second row's small boxes (art \"two_rows\")")
    if len(frames2 or []) > FRAMES:
        sys.exit(f"shots: {len(frames2)} second-shot frames, the strip has {FRAMES} boxes a row")
    sheet = Image.open(sheet_path)
    sheet.load()
    if sheet.mode != "P" or sheet.height > RESERVED_Y or sheet.width < FRAMES * BOX_W:
        sys.exit(f"shots: {sheet_path} is {sheet.mode} {sheet.width}x{sheet.height}: expected a paletted sheet at least "
                 f"{FRAMES * BOX_W} wide and at most {RESERVED_Y} high (the shot's strip starts at row {RESERVED_Y})")
    boxes = BIG_BOXES if big(frames) else SHEET_BOXES  # (big art: its own box set, and the strip that much taller)
    placed = list(zip(frames, boxes))
    height = RESERVED_Y + boxes[0][3]
    if more:  # (TailsObject frames 2 * FRAMES and up: right after the big boxes' FRAMES..2 * FRAMES - 1)
        placed += list(zip(more, SHEET_BOXES2))
        height = ROW2_Y + SHEET_BOXES2[0][3]
    if frames2:
        boxes2 = BIG_BOXES2 if big(frames2) else SHEET_BOXES2
        placed += list(zip(frames2, boxes2))
        height = ROW2_Y + boxes2[0][3]
    out = Image.new("P", (sheet.width, height), 0)
    out.putpalette(sheet.getpalette())
    out.paste(sheet, (0, 0))
    for (im, px, py), (x, y, w, h) in placed:
        at = (x + w // 2 + px, y + h // 2 + py)
        if at[0] < x or at[1] < y or at[0] + im.width > x + w or at[1] + im.height > y + h:
            sys.exit(f"shots: a {im.width}x{im.height} frame (pivot {px},{py}) doesn't fit its {w}x{h} box")
        out.paste(im, at)
    save_sheet(out, sheet_path)
