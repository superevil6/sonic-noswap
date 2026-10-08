#!/usr/bin/env python3
"""Build the Sonic 2 part of the NoSwap mod.

Same approach as build_sonic1.py: reads the community-decompiled Origins scripts installed next to
SonicOrigins.exe, applies anchored edits and writes the changed scripts into
mods/NoSwap/Sonic2u/Data/Scripts/. docs/sonic2_map.md lists every character-dependent site and why
each one is (or isn't) patched.

Extra characters behave like Sonic wherever they have no art or behaviour of their own yet
(placeholders), including Sonic's whole ending.
"""
import json
import os
import sys
from pathlib import Path

from noswap_common import *  # noqa: F401,F403 - shared patch helpers, save routines, art helpers
import abilities
__import__("own_sounds").mark_classic(abilities.ABILITIES, __import__("extras").EXTRAS)  # (own sounds: their Sonic 1/2/CD fields marked, tools/own_sounds.py)
import extras
import shots_v4
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
GAME_EXEC = Path(os.environ.get(
    "ORIGINS_EXEC",
    str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec",
))
BASE = GAME_EXEC / "Sonic2u" / "Scripts"
OUT = REPO / "mods" / "NoSwap" / "Sonic2u" / "Data" / "Scripts"

COMPLETE_VALUE = 22  # what Sonic 2's final boss writes into a save's progress entry


def extend_sonic_cases(t, pick, total, expr="stage.playerListPos", name="", only=None):
    """Add every extra's case label (or those passing `only`) right after Sonic's case label in chosen switches.

    Considers every `switch <expr>` whose first case is PLAYER_SONIC_A, numbered in file order.
    `total` is how many such switches the file must have; `pick` lists the ones to extend (None = all).
    """
    lines = t.split("\n")
    found = []
    for i, line in enumerate(lines):
        if line.strip().split("//")[0].strip() != f"switch {expr}":
            continue
        j = i + 1
        while lines[j].strip() == "" or lines[j].strip().startswith("//"):
            j += 1
        if lines[j].strip().split("//")[0].strip() == "case PLAYER_SONIC_A":
            found.append(j)
    if len(found) != total:
        sys.exit(f"extend '{name}': found {len(found)} Sonic-first switches on {expr} (expected {total})")
    chosen = range(total) if pick is None else pick
    for k in sorted(chosen, reverse=True):
        j = found[k]
        indent = lines[j][: len(lines[j]) - len(lines[j].lstrip("\t"))]
        lines[j + 1:j + 1] = [l for l in case_labels(indent, only=only).split("\n") if l]
    return "\n".join(lines)


def insert_after_lines(t, line_text, new_lines, expected, name):
    """Insert `new_lines` (same indentation) after every line whose stripped text is `line_text`."""
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == line_text]
    if len(hits) != expected:
        sys.exit(f"insert '{name}': found {len(hits)} (expected {expected})")
    for i in reversed(hits):
        indent = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i + 1:i + 1] = [indent + n for n in new_lines]
    return "\n".join(lines)


# ---------------------------------------------------------------- player

def build_player_object(t):
    t = patch(t, "public alias 6 : PLAYER_AMY_TAILS_A\n", EXTRA_ALIAS, "alias")

    # Drop Dash: Sonic's case re-checked the character, which would reject the extra character
    t = patch(t,
        "\t\t\t\t\tswitch player.character\n\t\t\t\t\tcase PLAYER_SONIC_A\n"
        "\t\t\t\t\t\tCheckEqual(player.character, PLAYER_SONIC_A) // A bit redundant here, but whatever\n"
        "\t\t\t\t\t\ttemp0 = checkResult\n",
        "\t\t\t\t\tswitch player.character\n\t\t\t\t\tcase PLAYER_SONIC_A\n"
        + case_labels("\t\t\t\t\t", "[NoSwap] Sonic's Drop Dash rules", only=lambda e: e["drop_dash"]) +
        "\t\t\t\t\t\ttemp0 = true // [NoSwap] was a redundant CheckEqual(player.character, PLAYER_SONIC_A)\n",
        "drop dash")

    # stage.playerListPos switches: physics, Super palette (extended); startup (own case below). Sonic's Super palette
    # only for extras with extras.py "super" (Metal Sonic): the others' own colours glow (abilities.py NoSwap_SuperGlow)
    t = extend_sonic_cases(t, [0], 3, name="player physics")
    t = extend_sonic_cases(t, [1], 3, name="player super palette", only=lambda e: e["super"])
    # player.character switches: drop dash (already done), balancing/idle, two Drop Dash releases
    t = extend_sonic_cases(t, [1], 4, expr="player.character", name="player idle")
    t = extend_sonic_cases(t, [2, 3], 4, expr="player.character", name="player drop dash release",
                           only=lambda e: e["drop_dash"])

    # Startup: the extra character's own setup, after Amy's (the rest, the same for every extra, is one block after
    # the switch: abilities.py extra_startup)
    t = patch(t,
        "= Player_Action_DblJumpAmy\n\t\t\tANI_PEELOUT \t\t\t\t\t\t= ANI_RUNNING\n\t\t\tbreak\n",
        "= Player_Action_DblJumpAmy\n\t\t\tANI_PEELOUT \t\t\t\t\t\t= ANI_RUNNING\n\t\t\tbreak\n\n"
        + "".join(
            f"\t\t{extras.startup_case(e)}\n"
            f"\t\t\tLoadAnimation(\"{extras.PLAYER_ANI}\")\n"
            "\t\t\tplayer[SLOT_PLAYER1].jumpAbility \t= Player_Action_DblJumpSonic\n"
            "\t\t\tbreak\n\n" for e in EXTRAS).rstrip("\n") + "\n",
        "startup")
    return t


# ---------------------------------------------------------------- global objects

HUD_ICON, HUD_NAME = 42, 43  # the extra's life icon and name tag frames (after the game's 0-41)


def build_hud(t):
    # The character ID picks the life icon (ID + 15) and name tag (icon + 6): for an extra, the icon's number becomes
    # 42 and the name tag's 43.
    t = insert_after_lines(t, "temp0 = stage.playerListPos", [
        f"if temp0 >= PLAYER_EXTRA1_A // [NoSwap] the extra's life icon is frame {HUD_ICON}, its name tag {HUD_NAME}",
        f"\ttemp0 = {HUD_ICON - 15}",
        "end if",
    ], 3, "hud")
    tag = f"if temp0 >= {HUD_ICON} // [NoSwap] the extra's icon: its name tag is the next frame\n"
    t = patch_n(t, "\t\t\ttemp0 += 6\n\t\t\tDrawSpriteScreenXY(temp0, 33, 213)\n",
                f"\t\t\t{tag}\t\t\t\ttemp0 -= {HUD_ICON + 6 - HUD_NAME}\n\t\t\tend if\n"
                "\t\t\ttemp0 += 6\n\t\t\tDrawSpriteScreenXY(temp0, 33, 213)\n", "hud name tag", 1)
    t = patch(t, "\t\t\ttemp1 = temp0\n\t\t\ttemp1 += 6\n",
              f"\t\t\ttemp1 = temp0\n\t\t\ttemp1 += 6\n\t\t\t{tag}\t\t\t\ttemp1 -= {HUD_ICON + 6 - HUD_NAME}\n\t\t\tend if\n",
              "hud name tag (2P layout)")
    t = patch(t, "\tSpriteFrame(0, 0, 31, 7, 217, 34)\t// #41 - Amy name tag\n",
        "\tSpriteFrame(0, 0, 31, 7, 217, 34)\t// #41 - Amy name tag\n"
        "\t// [NoSwap] the extra's HUD art (on the Display_NoSwap copy its package ships)\n"
        f"\t{ui().frame('life_icon', f'#{HUD_ICON} - the extra life icon')}\n"
        f"\t{ui().frame('life_name', f'#{HUD_NAME} - the extra name tag')}\n",
        "hud frames")
    return use_sheet_copy(t, "Global/Display.gif")


def monitor_1up_icon(t, number):
    old = f"SpriteFrame(-8, -9, 16, 14, 18, 96)"
    lines = t.split("\n")
    editor = next(i for i, l in enumerate(lines) if l.startswith("event RSDKLoad"))
    hits = [i for i, l in enumerate(lines[:editor]) if l.strip().startswith(old)]  # not the editor's copy
    if len(hits) != 1:
        sys.exit(f"1-UP icon: found {len(hits)} (expected 1)")
    i = hits[0]
    ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
    lines[i:i + 1] = extra_block(ind, [ui().frame("monitor_1up", f"{number} - the extra's own 1-UP icon")],
                                 [lines[i].strip("\t")])
    return use_sheet_copy("\n".join(lines), "Global/Items.gif")


def build_broken_monitor(t):
    return __import__("treasure_sense").v4_broken_monitor(monitor_1up_icon(t, 5))  # (jewel_thief: Rouge's 20 rings)


def build_monitor(t):
    t = abilities.apply_monitor(monitor_1up_icon(t, 7))
    # Debug mode: the 1-UP icon offset is the character ID, which runs past the monitor list for extras
    return patch_n(t,
        "\t\tif stage.playerListPos != PLAYER_AMY\n\t\t\ttemp0 += stage.playerListPos\n",
        "\t\tif stage.playerListPos != PLAYER_AMY\n"
        "\t\t\tif stage.playerListPos < PLAYER_EXTRA1_A // [NoSwap] extras use Sonic's 1-UP for now\n"
        "\t\t\t\ttemp0 += stage.playerListPos\n"
        "\t\t\tend if\n",
        "monitor debug icon", 2)


def build_sign_post(t):
    t = before_sonic_switch(t, 0, 1, [
        "SpriteFrame(-24, -16, 48, 32, 34, 100)",
        "SpriteFrame(-16, -16, 32, 32, 149, 99)",
        "SpriteFrame(-4, -16, 8, 32, 247, 2)",
        "SpriteFrame(-16, -16, 32, 32, 116, 99)",
        ui().frame("sign_face", "#5 - the extra's face (Origins only rewrites it for the base characters)"),
        "SpriteFrame(-16, -16, 32, 32, 149, 99)",
        "SpriteFrame(-4, -16, 8, 32, 247, 2)",
        "SpriteFrame(-16, -16, 32, 32, 116, 99)",
    ], name="signpost frames", comment="Sonic's spin frames with the extra's own face")
    return use_sheet_copy(t, "Global/Items2.gif")


def build_act_finish(t):
    # "[NAME] GOT" and the continue icons: the extra's own art, before switches 2 and 3 of the Sonic-first ones
    t = before_sonic_switch(t, 3, 4, [
        ui().frame("mini_1", "24 - continue frame 1"),
        ui().frame("mini_2", "25 - continue frame 2"),
    ], name="act finish continue icons")
    t = before_sonic_switch(t, 2, 4, [
        ui().frame("act_name", "0 - the extra name, ending where \"SONIC\" ends"),
        "SpriteFrame(16, 0, 48, 16, 1, 205) // 1 - \"GOT\" large text",
    ], name="act finish name")
    # perfect bonus ring count: an extra takes Sonic's case (the first Sonic-first switch); skip the save-mode-only
    # one (the second) and the frame switches above
    t = extras_as_sonic(t, [0], 4, name="act finish")
    return use_sheet_copy(t, "Global/Display.gif")


# ---------------------------------------------------------------- special stage

SS_FRAME_OFFSET = 80  # first free frame: Sonic, Tails, Knuckles, tails, tags and Amy's frames are 0-79
# The extra's ball frames (docs/plan-b-modular-characters.md step 3b item 4): NoSwap's Special/PlayerObject.txt has
# no extra's case (an extra there is Sonic); each package ships its own copy, loading its balls from this fixed name.
# NoSwap ships a blank placeholder under it (the DLL only redirects files NoSwap has).
BALL_SHEET = "Special/NoSwap_Extra.gif"


def pow2(n):
    """The next power of two >= n."""
    return 1 << max(0, n - 1).bit_length()


def special_ball(e):
    """The special stage shows the player from behind, and the extras' sheets have no back views. They
    roll through it instead, as their own spin ball (their Sonic 2 "Jumping" frames, or their own "Rolling"
    curl if their jump isn't a ball; unchanged), cut onto a small sheet of their own (BALL_SHEET, in their package).
    Returns (the sheet, [(x, y, w, h), ...] for 8 frames, palette slots used)."""
    from PIL import Image
    ani = extras.player_ani(e, "Sonic2u")
    jump = next(a for a in ani["anims"] if a["name"] == ball_animation(e))
    sheets = [Image.open(extras.player_sheet_path(e, "Sonic2u", s)) for s in ani["sheets"]]
    crops, rects, x = {}, [], 1
    for f in jump["frames"]:
        key = (f["sheet"], f["x"], f["y"], f["w"], f["h"])
        if key not in crops:
            crops[key] = (sheets[f["sheet"]].crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])), x)
            x += f["w"] + 1
        rects.append((crops[key][1], 1, f["w"], f["h"]))
    # the engine keeps sheets at power-of-two sizes (its row stride is a shift): any other width
    # scrambles the picture (seen in the special stage, 2026-09-26)
    out = Image.new("P", (pow2(x), pow2(max(c.height for c, _ in crops.values()) + 2)), 0)
    out.putpalette(sheets[0].getpalette())
    used = set()
    for img, px in crops.values():
        out.paste(img, (px, 1))
        used |= {i for i, n in enumerate(img.histogram()) if n}
    return out, [rects[i % len(rects)] for i in range(8)], sorted(used - {0})


def special_ball_case(e, rects, used):
    """The extra's halfpipe bounds (Sonic's), its ball frames and the palette slots they use."""
    glob = gameconfig_palette(REPO / "extracted/Sonic2/Data/Game/GameConfig.bin")
    colours = {i: (glob[i][0] << 16) | (glob[i][1] << 8) | glob[i][2] for i in used if i < len(glob)}
    colours.update({i: c for i, c in e["palette"].items() if i in used})
    lines = ["player[2].xBoundsR = 88", f"player[2].frameOffset = {SS_FRAME_OFFSET}",
             f'LoadSpriteSheet("{BALL_SHEET}")']
    # rolling: the ball sits on the pipe like Sonic's feet (running frames reach 28 px below centre)
    lines += [f"SpriteFrame({-(w // 2)}, {28 - h}, {w}, {h}, {x}, {y})" for x, y, w, h in rects]
    # jumping: centred, like Sonic's jump frames
    lines += [f"SpriteFrame({-(w // 2)}, {-(h // 2)}, {w}, {h}, {x}, {y})" for x, y, w, h in rects]
    return lines + palette_lines(e, 0, "", colours).rstrip("\n").split("\n")


def build_special_player(t, extra=None, ball=None):
    """Halfpipe bounds and sprite offset per character: without a case the player is pinned in place.
    extra None: NoSwap's own copy, where any extra takes Sonic's case. Else that extra's package copy: before the
    switch (which has no case for it), what its case did: its bounds, and its ball frames after all of the stage's own
    frames (0-79). `ball`: special_ball(extra)."""
    if t[:t.index("\tplayer[2].type = TypeName[Player Object]")].count("SpriteFrame(") != SS_FRAME_OFFSET + 2:
        sys.exit("special player: frame count changed")  # +2: the Mirror Mode tag pair is either/or
    if extra is None:
        return extras_as_sonic(t, None, 1, name="special player: extras are Sonic without their package")
    _, rects, used = ball
    return before_sonic_switch(t, 0, 1, special_ball_case(extra, rects, used), "special player",
                               comment="this package's extra: its own ball frames and colours")


def package_special(extra, game_dir):
    """A character package's special stage (tools/build_packages.py): its Special/PlayerObject.txt and BALL_SHEET."""
    ball = special_ball(extra)
    build_scripts({"Special/PlayerObject.txt": lambda t: build_special_player(t, extra, ball)}, BASE,
                  game_dir / "Data" / "Scripts")
    out = game_dir / "Data" / "Sprites" / BALL_SHEET
    out.parent.mkdir(parents=True, exist_ok=True)
    save_sheet(ball[0], out)


def special_placeholder():
    """NoSwap's own BALL_SHEET (never loaded by its own scripts), and no per-extra ball sheets any more."""
    from PIL import Image
    for e in EXTRAS:
        (SPRITES_OUT / f"Special/NoSwap_{e['file']}.gif").unlink(missing_ok=True)
    blank = Image.new("P", (16, 16), 0)
    blank.putpalette([0] * 768)
    (SPRITES_OUT / BALL_SHEET).parent.mkdir(parents=True, exist_ok=True)
    save_sheet(blank, SPRITES_OUT / BALL_SHEET)


def build_special_hud(t):
    return patch(t,
        "\t\tobject.frame = object.character\n\t\tobject.frame += 12\n",
        "\t\tobject.frame = object.character\n\t\tobject.frame += 12\n"
        "\t\tif object.character >= PLAYER_EXTRA1_A // [NoSwap] placeholder: Sonic's ring label\n"
        "\t\t\tobject.frame = 12\n"
        "\t\tend if\n",
        "special hud")


def build_special_checkpoint(t):
    return patch(t,
        "\t\t\t\t\t\t\tobject.emblemFrame += stage.playerListPos\n\t\t\t\t\t\tend if\n",
        "\t\t\t\t\t\t\tobject.emblemFrame += stage.playerListPos\n\t\t\t\t\t\tend if\n"
        "\t\t\t\t\t\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] placeholder: Sonic's emblem, not Amy's\n"
        "\t\t\t\t\t\t\tobject.emblemFrame = 4\n"
        "\t\t\t\t\t\tend if\n",
        "special checkpoint")


def build_special_finish(t):
    # 7th emerald reward (softlock without it), the results' icon and text-frame blocks: an extra takes Sonic's case,
    # but in the two text blocks that name the player (nameless_results, which also does the ring count's label)
    t = nameless_results(guard_special_retry(t, "value15"))
    lines = t.split("\n")
    found = sonic_first_switches(t)
    pick = [k for k, i in enumerate(found) if lines[i - 1].strip() != "else"]  # not the two nameless_results wrapped
    if len(pick) != 5:
        sys.exit(f"special finish: {len(pick)} switches to remap (expected 5)")
    return extras_as_sonic(t, pick, 7, name="special finish")


BLANK = "SpriteFrame(0, 0, 1, 1, 500, 500)"  # a transparent pixel of Special/Objects.gif


def nameless_results(t):
    """The results lines name the player ("SONIC GOT A / CHAOS EMERALD", "SONIC HAS ALL THE / CHAOS
    EMERALDS", "SONIC RINGS"). The results font is slanted, so extras' names can't be spelled from its
    letters: for any extra the name is left out ("GOT A / CHAOS EMERALD"), centred. Every extra alike, Metal Sonic
    too (the user's call, 2026-09-26: no "SONIC" for him either)."""
    for name_line, text_line, text in (
            ("\t\tSpriteFrame(-72, 32, 72, 16, 189, 277) \t// Sonic Text - #24\n",
             "\t\tSpriteFrame(8, 32, 72, 16, 412, 277) \t// \"GOT A\" Text - #25\n",
             "SpriteFrame(-36, 32, 72, 16, 412, 277) // #25 - \"GOT A\", centred"),
            ("\t\tSpriteFrame(-120, 32, 72, 16, 189, 277)\t// Sonic Text - #37\n",
             "\t\tSpriteFrame(-40, 32, 159, 16, 162, 311) // \"HAS ALL THE\" Text - #28\n",
             "SpriteFrame(-80, 32, 159, 16, 162, 311) // #28 - \"HAS ALL THE\", centred")):
        at = t.index(name_line + text_line)
        start = t.rindex("\tswitch stage.playerListPos\n", 0, at)
        if not t[start:at].startswith("\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n"):
            sys.exit("special results: the named switch no longer starts with Sonic's case")
        t = extras_skip_switch(t, start, [f"{BLANK} // (no name)", text], "no name", "special results name")
    # the ring count's label: "RINGS" for extras
    ring = "\tSpriteFrame(-96, 0, 92, 15, 176, 345) \t// Sonic Rings Text - #20"
    if t.count(ring) != 1:
        sys.exit("special results: Sonic Rings frame not found")
    i = t.index(ring)
    end = t.index("\n", i)
    t = (t[:i] + f"\tif stage.playerListPos >= {EXTRA_MIN_ID} // [NoSwap] any extra: just \"RINGS\"\n"
         "\t\tSpriteFrame(-96, 0, 44, 15, 46, 345) \t// #20 - \"RINGS\"\n\telse\n\t" + t[i:end] + "\n\tend if" + t[end:])
    return t


# ---------------------------------------------------------------- continue, ending, zones

def build_continue(t):
    t = before_sonic_switch(t, 0, 1, [
        ui().frame("cont_mini_1", "#12 - foot tapping 1"),
        ui().frame("cont_mini_2", "#13 - foot tapping 2"),
    ], name="continue icons")
    return use_sheet_copy(t, "Continue/Objects.gif")


def build_continue_setup(t):
    return extras_as_sonic(t, None, 2, name="continue positions")


def build_end_setup(t):
    # An extra plays Sonic's ending (the pictures, then the fall onto the Tornado), but never his Super ending: that
    # loads SuperSonic.ani over the extra (Super Sonic's sprites) and flies him alongside the Tornado (nobody on the
    # plane), with Super Sonic's own pictures to finish. With all the emeralds an extra is caught like Amy is.
    anchor = "#endplatform\n\n\t\t\tif temp0 == false\n\t\t\t\t// Make the player go Super\n"
    t = patch(t, anchor, "#endplatform\n"
              f"\t\t\tif stage.playerListPos >= {EXTRA_MIN_ID} // [NoSwap] no Super ending for extras (it's Super "
              "Sonic's art): the Tornado catches them\n"
              "\t\t\t\ttemp0 = true\n"
              "\t\t\tend if\n\n\t\t\tif temp0 == false\n\t\t\t\t// Make the player go Super\n", "no super ending")
    return extras_as_sonic(t, None, 2, name="ending setup")


# The Tornado's frames the extra's ending draws: the extra's three poses (its own art, jumping toward the screen) after
# the game's 0-67
ENDING_POSES = [(68, "end_pose_1"), (69, "end_pose_2"), (70, "end_pose_3")]
# Tornado.txt's Sonic-first switches (in file order): 0 Super Sonic meets the Tornado, 1 the rider hides for the
# zoom-out, 2 and 4 Super Sonic flies off, 3 the zoom-out frames, 5-7 the three poses (drawn)
TORNADO_POSES = {5: ("0x220000", "0x2F0000"), 6: ("0x2A0000", "0x2F0000"), 7: ("0x6E0000", "0x670000")}


def build_tornado_ending(t):
    """The Tornado's ending for an extra: it lands on the plane as Sonic does (its own sprite), then the zoom-out uses
    the plane with Tails alone (the game's frames with Sonic in the back seat are Sonic's art, and no extra has
    zoomed-out art: Super Sonic's frames 12-16, where he flies apart) and the three poses toward the screen are the
    extra's own, in the fixed boxes of its package's Ending/Objects_NoSwap.gif (end_pose_1-3, as Sonic 1's ending).
    The Super Sonic switches (0, 2, 4) get no case for extras: an extra is never Super in the ending (build_end_setup)."""
    frames = [ui().frame(key, f"{n} - the extra's pose {k + 1}") for k, (n, key) in enumerate(ENDING_POSES)]
    t = patch(t, "\tSpriteFrame(6, -3, 65, 102, 325, 256)\n#endplatform\n",
              "\tSpriteFrame(6, -3, 65, 102, 325, 256)\n#endplatform\n\n"
              "\t// [NoSwap] 68-70 - the extra's posing frames (its package's Ending/Objects_NoSwap.gif, loaded while an "
              "extra plays)\n" + "".join(f"\t{f}\n" for f in frames), "ending pose frames")
    for k in sorted(TORNADO_POSES, reverse=True):  # (from the last: offsets before them don't move)
        dx, dy = TORNADO_POSES[k]
        n = ENDING_POSES[k - 5][0]
        t = extras_skip_switch(t, switch_offset(t, k, 8), [f"temp0 -= {dx}", f"temp1 -= {dy}",
                                                           f"DrawSpriteXY({n}, temp0, temp1)"],
                               f"its own pose {k - 4} (Sonic's place)", "ending pose")
    t = extras_skip_switch(t, switch_offset(t, 3, 8),
                           ["GetTableValue(object.tornadoFrame, object.zoomoutSprIndex, Tornado_ZoomoutSprites_SS)"],
                           "the plane with Tails alone (frames 12-16: no one else's art)", "ending zoom-out")
    t = extras_as_sonic(t, [1], 8, name="ending tornado")  # the rider hides as Sonic does
    return use_sheet_copy(t, "Ending/Objects.gif")


def switch_offset(t, k, total):
    """The text offset of the k-th Sonic-first `switch stage.playerListPos` (of `total`)."""
    found = sonic_first_switches(t)
    if len(found) != total:
        sys.exit(f"ending tornado: found {len(found)} Sonic-first switches (expected {total})")
    lines = t.split("\n")
    return sum(len(l) + 1 for l in lines[:found[k]])


# The whole-bank palette loads after which the extra's own colours are written again (noswap_common.WATER_FUNCTION)
WATER_LOADS = [("CPZ_WaterPal.act", 1), ("ARZ_WaterPal.act", 1), ("HPZ_WaterPal.act", 1), ("ElectricFlash.act", 2)]


def water_palettes(expected):
    # Underwater palettes and flashes are whole-bank loads that would blank extras' own colour slots
    return lambda t: water_colours_after_loads(t, WATER_LOADS, expected, "water palettes")


def water_function(t):
    return water_colours_function(t, WATER_LOADS, gameconfig_palette(REPO / "extracted/Sonic2/Data/Game/GameConfig.bin"),
                                  REPO / "extracted/Sonic2/Data/Palettes")


def build_attract_setup(t):
    # Demo and credits replays are recorded per character; extras replay Sonic's inputs
    return extras_as_sonic(t, None, 1, name="attract replays")


# Y on a card in Origins' character select opens the level select as that character (the DLL confirms the
# card and flips the flag, a magic number while the select is open: see CD_SHOT_MAGIC in the DLL)
Y_FLAG = "NoSwap_yLevelSelect"


def build_title_start(t):
    t = patch(t, "private alias  2 : START_LEVELSELECT\n",
              "private alias  2 : START_LEVELSELECT\n"
              f"private value {Y_FLAG} = 0 // [NoSwap] 1: Y picked the character, open the level select\n", "y flag")
    t = patch(t, "\t\tCallNativeFunction2(NotifyCallback, NOTIFY_CHARACTER_SELECT, 0)\n\t\tobject.state = START_1PWAITFORCHARSELECT\n",
              f"\t\t{Y_FLAG} = 0x4E53 // [NoSwap] the magic number 0x4E53593F: Y in the character select sets it to 1\n"
              f"\t\t{Y_FLAG} <<= 16\n\t\t{Y_FLAG} += 0x593F\n"
              "\t\tCallNativeFunction2(NotifyCallback, NOTIFY_CHARACTER_SELECT, 0)\n\t\tobject.state = START_1PWAITFORCHARSELECT\n",
              "y flag set")
    t = patch(t, "\t\t\tStopMusic()\n\t\telse\n\t\t\tif game.callbackResult == 0\n\t\t\t\tobject.state = START_AWAITACTION\n",
              "\t\t\tStopMusic()\n"
              f"\t\t\tif {Y_FLAG} == 1 // [NoSwap] Y on the card: this character's level select, without saving\n"
              "\t\t\t\toptions.gameMode = 0\n"
              "\t\t\t\tobject.timer = 0\n"
              "\t\t\t\tobject.state = START_LEVELSELECT\n"
              "\t\t\tend if\n"
              f"\t\t\t{Y_FLAG} = 0\n"
              "\t\telse\n\t\t\tif game.callbackResult == 0\n"
              f"\t\t\t\t{Y_FLAG} = 0\n"
              "\t\t\t\tobject.state = START_AWAITACTION\n", "y level select")
    return t


def build_level_select(t):
    # Origins crashes if told a character ID it doesn't know: tell it Sonic, then keep playing the extra
    # (an extra picked in Origins' character select keeps playing in the level select)
    # Testing aid (as Sonic 1's): hold Y while starting Death Egg (entry 19) to go straight to the ending
    # (presentation stage 1); with all the emeralds it's the good ending
    t = patch(t,
        "\t\t\tstage.listPos = temp2\n\t\t\tLoadStage()\n\t\t\tSetScreenFade(0x00, 0x00, 0x00, 0xFF)\n",
        "\t\t\tstage.listPos = temp2\n"
        "\t\t\tif object.currentSelection == 19 // [NoSwap] testing: Y held on Death Egg goes to the ending\n"
        "\t\t\t\tif keyDown[1].buttonY == true\n"
        "\t\t\t\t\tstage.activeList = PRESENTATION_STAGE\n"
        "\t\t\t\t\tstage.listPos = 1\n"
        "\t\t\t\tend if\n"
        "\t\t\tend if\n"
        "\t\t\tLoadStage()\n\t\t\tSetScreenFade(0x00, 0x00, 0x00, 0xFF)\n",
        "ending shortcut")
    return patch(t,
        "\t\t\tCallNativeFunction4(NotifyCallback, NOTIFY_PLAYER_SET, stage.playerListPos, stage.player2Enabled, 0)\n",
        "\t\t\ttemp3 = stage.playerListPos // [NoSwap] never send Origins an extra's ID\n"
        "\t\t\tif stage.playerListPos > PLAYER_AMY_TAILS\n"
        "\t\t\t\tstage.playerListPos = PLAYER_SONIC\n"
        "\t\t\tend if\n"
        "\t\t\tCallNativeFunction4(NotifyCallback, NOTIFY_PLAYER_SET, stage.playerListPos, stage.player2Enabled, 0)\n"
        "\t\t\tstage.playerListPos = temp3\n",
        "level select guard")

# ---------------------------------------------------------------- sprites

SPRITES_IN = REPO / "extracted" / "Sonic2" / "Data" / "Sprites"
SPRITES_OUT = REPO / "mods" / "NoSwap" / "Sonic2u" / "Data" / "Sprites"


# ---------------------------------------------------------------- the extra's UI art

# Results names built from the title-card alphabet on Global/Display.gif (TitleCard.txt frames
# #0-#25): letter -> (x, y, width), all 16 high
S2_ALPHABET = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [
    (37, 79, 15), (53, 79, 16), (70, 79, 16), (87, 79, 16), (104, 79, 15), (120, 79, 15), (136, 79, 16),
    (153, 79, 16), (170, 79, 8), (179, 79, 16), (196, 79, 16), (213, 79, 16), (43, 96, 23), (67, 96, 16),
    (84, 96, 16), (101, 96, 16), (118, 96, 16), (135, 96, 16), (152, 96, 16), (169, 96, 16), (186, 96, 16),
    (203, 96, 16), (220, 96, 22), (43, 113, 15), (59, 113, 16), (76, 113, 16)]))

# The extra's UI art: fixed boxes on the "<name>_NoSwap.gif" sheet copies (noswap_common.UiSheets). NoSwap ships the
# copies with empty boxes; each character package ships its own with its art in them (tools/build_packages.py). The
# scripts load a copy only while an extra plays, since an object type can only draw from one sheet.
UI_SHEETS = {
    "Global/Display.gif": ["life_icon", "life_name", "act_name", "mini_1", "mini_2"],
    "Global/Items.gif": ["monitor_1up"],
    "Global/Items2.gif": ["sign_face"],
    "Continue/Objects.gif": ["cont_mini_1", "cont_mini_2"],
    # the ending's three poses toward the screen: the same art as Sonic 1's (the extra's "ending" manifest)
    "Ending/Objects.gif": ["end_pose_1", "end_pose_2", "end_pose_3"],
}

# Ending/Objects.gif is 512x512 with no room for the boxes, and only Ending/Tornado.txt loads the copy (an object type
# draws every frame from the last sheet its ObjectStartup loads), so the copy holds only the game frames the Tornado
# draws for an extra (by Tornado.txt's frame numbers, noswap_common.startup_frames): 0-3 the propeller, 4 the Tornado,
# 5-9 Tails piloting, 12-16 the zoom-out with Tails alone, 17-18 its propeller, 50 the big Tornado with Tails, 52-59 the
# "Sonic the Hedgehog 2" logo and its shines (51 is an empty frame). Not Sonic's pilot frames (10-11: only for Tails),
# the zoom-outs with a passenger, anyone's poses or Super Sonic's (43-48). The boxes are packed around them.
KEEP_FRAMES = {"Ending/Objects.gif": ("Ending/Tornado.txt", list(range(0, 10)) + list(range(12, 19)) + [50]
                                      + list(range(52, 60)))}


def keep_rects():
    out = {}
    for sheet, (script, numbers) in KEEP_FRAMES.items():
        rects = startup_frames((BASE / script).read_text(errors="ignore"), script)
        out[sheet] = [rects[n] for n in numbers]
    return out


def s2_element(key, extra):
    """An extra's art for Sonic 2. The UI sheet was cut for Sonic 1, where some art sits in slots 128+;
    Sonic 2 uses the plain player slots everywhere except the continue screen. The ending poses are Sonic 1's ending
    art (its slots 129-143 are Sonic's colours there): in Sonic 2's ending the plain slots 1-15 hold the player's
    colours (the ending stage's 142-143 aren't Sonic's), so they move back down too."""
    from PIL import Image
    if key == "act_name":
        return alphabet_name(Image.open(SPRITES_IN / "Global" / "Display.gif"), S2_ALPHABET, extra["name"])
    manifest = ui_manifest(extra, "ending" if key.startswith("end_") else "ui")
    sheet = Image.open(manifest["sheet"])
    src = key[len("cont_"):] if key.startswith("cont_") else key
    x, y, w, h = manifest["frames"][src]
    img = sheet.crop((x, y, x + w, y + h)).point(lambda i: i - 128 if i >= 128 else i)
    if key.startswith("cont_"):
        cont = Image.open(SPRITES_IN / "Continue" / "Objects.gif")
        img = title_remap(img, sheet.getpalette(), cont, skip=())
    return img


def element_pivot(key, img):
    """Where each element's art sits relative to its object (the offsets its frames have always had)."""
    w, h = img.size
    if key == "act_name":
        return 8 - w, 0  # ending where "SONIC" ends
    if key in ("mini_1", "mini_2", "cont_mini_1", "cont_mini_2"):
        return -9, -12
    if key == "monitor_1up":
        return -8, -9
    if key == "sign_face":
        return -24, -16
    # the ending poses, drawn where Sonic's are: the two small ones with their feet where his are and centred on him
    # (frame 24: 31x38 at 0,0; frame 25: 29x42 at 2,5), the big one centred on his (frame 26: 77x96 at 3,3)
    if key == "end_pose_1":
        return 15 - w // 2, 38 - h
    if key == "end_pose_2":
        return 16 - w // 2, 47 - h
    if key == "end_pose_3":
        return 41 - w // 2, 51 - h // 2
    return 0, 0  # life icon, name tag


_UI = None


def ui():
    global _UI
    if _UI is None:
        _UI = UiSheets(SPRITES_IN, UI_SHEETS, s2_element, element_pivot, keep_rects())
    return _UI


def package_sprites(extra, sprites_out):
    """A character package's own sheet copies, with its art in the boxes (tools/build_packages.py)."""
    ui().write(sprites_out, extra)


def add_own_case(t, pick, total, block, expr="stage.playerListPos", name=""):
    """Insert each extra's own case (body: `block(extra)` lines) before Sonic's case in a chosen Sonic-first switch."""
    lines = t.split("\n")
    found = []
    for i, line in enumerate(lines):
        if line.strip().split("//")[0].strip() != f"switch {expr}":
            continue
        j = i + 1
        while lines[j].strip() == "" or lines[j].strip().startswith("//"):
            j += 1
        if lines[j].strip().split("//")[0].strip() == "case PLAYER_SONIC_A":
            found.append(j)
    if len(found) != total:
        sys.exit(f"own case '{name}': found {len(found)} Sonic-first switches (expected {total})")
    j = found[pick]
    indent = lines[j][: len(lines[j]) - len(lines[j].lstrip("\t"))]
    lines[j:j] = own_cases(indent, block)
    return "\n".join(lines)


BUILDERS = {
    "Players/PlayerObject.txt": lambda t: water_function(abilities.apply_player(build_player_object(t), "Sonic2u")),
    "ARZ/Water.txt": lambda t: knux_like(abilities.apply_water(t)),
    "CPZ/Water.txt": lambda t: knux_like(abilities.apply_water(t)),
    "HPZ/Water.txt": lambda t: knux_like(abilities.apply_water(t)),
    "HPZ/BreakWall.txt": lambda t: knux_like(t, walls=True),  # (and extras that break walls: breaks_walls)
    "MBZ/MBZSetup.txt": abilities.apply_fire_tiles,  # Egg Gauntlet's lava tiles spare fire_immune extras (Blaze)
    "Mission/Water.txt": lambda t: knux_like(abilities.apply_water(t)),
    "Global/HUD.txt": build_hud,
    "Global/Monitor.txt": build_monitor,
    "Global/Ring.txt": abilities.apply_ring,  # magnetic extras pull rings in
    "Global/BrokenMonitor.txt": build_broken_monitor,
    "Global/SignPost.txt": build_sign_post,
    "Global/ActFinish.txt": build_act_finish,
    "Special/PlayerObject.txt": build_special_player,
    "Special/HUD.txt": build_special_hud,
    "Special/Checkpoint.txt": build_special_checkpoint,
    "Special/SpecialFinish.txt": build_special_finish,
    "Continue/Continue.txt": build_continue,
    "Continue/ContinueSetup.txt": build_continue_setup,
    "Ending/EndSetup.txt": build_end_setup,
    "Ending/Tornado.txt": build_tornado_ending,
    "EHZ/EHZSetup.txt": build_attract_setup,
    "CPZ/CPZSetup.txt": lambda t: build_attract_setup(water_palettes(2)(t)),
    "ARZ/ARZSetup.txt": lambda t: build_attract_setup(water_palettes(2)(t)),
    "HPZ/HPZSetup.txt": water_palettes(2),
    "CNZ/CNZSetup.txt": build_attract_setup,
    "LevelSelect/MenuControl.txt": build_level_select,
    "Title/Start.txt": build_title_start,
}
# Extras' shots (tools/shots_v4.py): every script with a player loop hitting badniks, monitors or bosses gets a copy
# of it for the shots' group, and TailsObject.txt is the shot object while an extra plays
shots_v4.add_builders(BUILDERS, BASE)
# Heavy's full charge: enemies and bosses can't hurt him (noswap_common.juggernaut; after the shots' copies)
add_juggernaut_builders(BUILDERS, BASE, "Sonic2u")
__import__("psycho_grab").add_builders(BUILDERS, BASE, "Sonic2u")  # (Silver's Psychokinesis: the grabbable badniks)


# Scripts earlier builds wrote that the game's own versions now replace (extras save like the vanilla
# characters since they're real kinds in Origins' character select; the title picker is gone)
RETIRED = ["Global/DeathEvent.txt", "SCZ/SCZSetup.txt", "WFZ/Tornado.txt",
           "WFZ/EggmanLaser.txt", "MCZ/HPZTrigger.txt", "DEZ/DeathEggRobot.txt",
           "Special/SpecialSetup.txt"]  # (its extras' aliases went with literal_extra_ids: the game's own is the same)


def retire():
    for rel in RETIRED:
        (OUT / rel).unlink(missing_ok=True)
    (SPRITES_OUT / "Title" / "Title_NoSwap.gif").unlink(missing_ok=True)


if __name__ == "__main__":
    if os.environ.get("NOSWAP_SCRIPTS_OUT"):  # just the player script, into a package (tools/build_packages.py)
        build_scripts({"Players/PlayerObject.txt": BUILDERS["Players/PlayerObject.txt"]}, BASE,
                      Path(os.environ["NOSWAP_SCRIPTS_OUT"]))
        sys.exit()
    extras.stash_all_player_art()  # (sheet2ani's player .ani and sheets: packages ship them, NoSwap doesn't)
    retire()
    special_placeholder()
    ui().write(SPRITES_OUT)  # NoSwap's own copies: the boxes empty (the packages' have the art)
    build_scripts(BUILDERS, BASE, OUT)
