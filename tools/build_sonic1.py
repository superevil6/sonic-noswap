#!/usr/bin/env python3
"""Build the Sonic 1 part of the NoSwap mod.

Reads the community-decompiled Origins scripts that HedgeModManager installs
next to SonicOrigins.exe, applies our edits, and writes the changed scripts
into mods/NoSwap/Sonic1u/Data/Scripts/.

Every edit is anchored on exact text from the original script. If an anchor
is missing or appears more than once, the build stops instead of guessing,
so an update to the base scripts can never silently produce a broken mod.
All inserted lines are tagged with [NoSwap] so they are easy to find.
"""
import json
import os
import shutil
import sys
from pathlib import Path

from noswap_common import *  # noqa: F401,F403 - shared patch helpers, save routines, art helpers
import abilities
__import__("own_sounds").mark_classic(abilities.ABILITIES, __import__("extras").EXTRAS)  # (own sounds: their Sonic 1/2/CD fields marked, tools/own_sounds.py)
import extras
import shots_v4
from extras import s1_special_ani, stash_special_ani
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
GAME_EXEC = Path(os.environ.get(
    "ORIGINS_EXEC",
    str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec",
))
BASE = GAME_EXEC / "Sonic1u" / "Scripts"
OUT = REPO / "mods" / "NoSwap" / "Sonic1u" / "Data" / "Scripts"


SPRITES_IN = REPO / "extracted" / "Sonic1" / "Data" / "Sprites"
SPRITES_OUT = REPO / "mods" / "NoSwap" / "Sonic1u" / "Data" / "Sprites"

# Act-finish names for extras, built from the title-card alphabet on Global/Display.gif
# (TitleCard.txt frames #0-#25): letter -> (x, y, width), all 16 high
ALPHABET = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [
    (37, 73, 15), (53, 73, 15), (69, 73, 15), (85, 73, 15), (101, 73, 14), (116, 73, 14), (131, 73, 16),
    (148, 73, 15), (164, 73, 6), (171, 73, 14), (186, 73, 16), (203, 73, 15), (219, 73, 16), (236, 73, 15),
    (37, 90, 16), (54, 90, 15), (70, 90, 16), (87, 90, 15), (103, 90, 14), (118, 90, 14), (133, 90, 15),
    (149, 90, 15), (165, 90, 22), (188, 90, 16), (205, 90, 16), (222, 90, 15)]))

# The extra's UI art: fixed boxes on the "<name>_NoSwap.gif" sheet copies (noswap_common.UiSheets). NoSwap ships the
# copies with empty boxes; each character package ships its own with its art in them (tools/build_packages.py). Game
# sheets must never ship modified under their own names: a changed Special/Objects.gif broke the special stage (maze
# and results drawn as garbage, for every character) and a changed Ending/Objects.gif made the ending's final leap
# vanish (2026-09-25). The special stage results keep the game's own Special/Objects.gif (Sonic's icons for extras);
# only the continue screen loads Special/Objects_NoSwap.gif. No copy may pass 512 rows (the engine draws no more;
# 2026-09-26 the ending poses at rows 513+ vanished): see KEEP_FRAMES.
UI_SHEETS = {
    "Global/Display.gif": ["life_icon", "life_name", "act_name"],
    "Global/Items.gif": ["monitor_1up"],
    "Global/Items2.gif": ["sign_face"],
    "Special/Objects.gif": ["mini_1", "mini_2"],
    "Ending/Objects.gif": ["end_idle", "end_pose_1", "end_pose_2", "end_pose_3"] + [f"good_{n}" for n in range(1, 7)],
}
ENDING_KEYS = UI_SHEETS["Ending/Objects.gif"]

# Those two game sheets have no room for the boxes in their first 512 rows (the engine draws no more: SHEET_ROWS), and
# one script loads each copy (an object type draws every frame from the last sheet it loads), so their copies hold only
# the game's frames that script draws for an extra (by the game script's frame numbers: startup_frames), where they
# were, with the boxes packed around them. The frame numbers, from reading the scripts' extra path:
# - Continue/Continue.txt: 0 "CONTINUE", 1 the stars, 2-11 the digits (its 12-13 are the extra's minis, in the boxes).
# - Ending/EndingPose.txt: the extra's 0-9 are its poses (in the boxes); the rest it can draw: 10 "Sonic the Hedgehog"
#   (its logo: extras are neither below PLAYER_SONIC_TAILS nor Amy), and, should a Tails ever follow the extra (the
#   same object type draws player 2), 41-42 the "... and Tails/Miles" logos and 20-23, 43-44 player 2's frames.
#   Its tail frames 36-40 are Tails's alone (object.tailFrame is set only for PLAYER_TAILS_A).
KEEP_FRAMES = {
    "Special/Objects.gif": ("Continue/Continue.txt", range(0, 12)),
    "Ending/Objects.gif": ("Ending/EndingPose.txt", [10, 20, 21, 22, 23, 41, 42, 43, 44]),
}


def keep_rects():
    out = {}
    for sheet, (script, numbers) in KEEP_FRAMES.items():
        rects = startup_frames((BASE / script).read_text(errors="ignore"), script)
        out[sheet] = [rects[n] for n in numbers]
    return out


def element_image(key, extra):
    from PIL import Image
    if key == "act_name":
        return alphabet_name(Image.open(SPRITES_IN / "Global" / "Display.gif"), ALPHABET, extra["name"])
    manifest = ui_manifest(extra, "ui")
    if key not in manifest["frames"]:
        manifest = ui_manifest(extra, "ending")
    x, y, w, h = manifest["frames"][key]
    return Image.open(manifest["sheet"]).crop((x, y, x + w, y + h))


def element_pivot(key, img):
    """Where each element's art sits relative to its object (the offsets its frames have always had)."""
    w, h = img.size
    if key == "act_name":
        return -w, 0  # right-aligned, like the game's names
    if key == "monitor_1up":
        return -8, -9
    if key == "sign_face":
        return -24, -16
    if key in ("mini_1", "mini_2"):
        return -(w // 2), -(h // 2)
    if key == "end_pose_2":  # ending poses: the feet where Sonic's are (y=+19; +44 for the medium pose)
        return -(w // 2), 44 - h
    if key == "end_pose_3":  # the big pose centred on Sonic's
        return 31 - w // 2, -1 - h // 2
    if key in ENDING_KEYS:
        return -(w // 2), 19 - h
    return 0, 0  # life icon, name tag


_UI = None


def ui():
    global _UI
    if _UI is None:
        _UI = UiSheets(SPRITES_IN, UI_SHEETS, element_image, element_pivot, keep_rects())
    return _UI


def package_sprites(extra, sprites_out):
    """A character package's own sheet copies, with its art in the boxes (tools/build_packages.py)."""
    ui().write(sprites_out, extra)


def build_player_object(t):
    t = patch(t,
        "public alias 6 : PLAYER_AMY_TAILS_A\n",
        EXTRA_ALIAS,
        "alias")

    # Physics table
    t = add_case(t,
        "public function Player_UpdatePhysicsState\n\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n\tcase PLAYER_SONIC_TAILS_A",
        "physics")

    # Super form palette: Sonic's, for extras with extras.py "super" (Metal Sonic); the others' own colours glow
    # (abilities.py NoSwap_SuperGlow)
    t = add_case(t,
        "\t\tswitch stage.playerListPos\n\t\tcase PLAYER_SONIC_A\n\t\tcase PLAYER_SONIC_TAILS_A // This case check should never pass since playing as S&T will set your character to Sonic alone",
        "super palette", only=lambda e: e["super"])

    # Drop Dash: Sonic's case re-checked the character, which would reject the extra character.
    t = patch(t,
        "\t\t\t\t\tswitch player.character\n\t\t\t\t\tcase PLAYER_SONIC_A\n"
        "\t\t\t\t\t\tCheckEqual(player.character, PLAYER_SONIC_A) // A bit redundant here, but whatever\n"
        "\t\t\t\t\t\ttemp0 = checkResult\n",
        "\t\t\t\t\tswitch player.character\n\t\t\t\t\tcase PLAYER_SONIC_A\n"
        + case_labels("\t\t\t\t\t", "[NoSwap] Sonic's Drop Dash rules", only=lambda e: e["drop_dash"]) +
        "\t\t\t\t\t\ttemp0 = true // [NoSwap] was a redundant CheckEqual(player.character, PLAYER_SONIC_A)\n",
        "drop dash")

    # Drop Dash release (two states share the same code)
    anchor = "\t\t\tswitch player.character\n\t\t\tcase PLAYER_SONIC_A\n\t\t\t\tCallFunction(Player_Action_Spindash) // Good ol' Sonic Team programming"
    if t.count(anchor) != 2:
        sys.exit(f"patch 'drop dash release': anchor found {t.count(anchor)} times (expected 2)")
    t = t.replace(anchor,
        "\t\t\tswitch player.character\n\t\t\tcase PLAYER_SONIC_A\n"
        + case_labels("\t\t\t", only=lambda e: e["drop_dash"]) +
        "\t\t\t\tCallFunction(Player_Action_Spindash) // Good ol' Sonic Team programming")

    # Balancing animation
    t = add_case(t,
        "\t\t\t\t// Update balancing animation\n\t\t\t\tswitch player.character\n\t\t\t\tcase PLAYER_SONIC_A",
        "balancing")

    # Startup: the extra character's own setup
    t = patch(t,
        "= Player_Action_DblJumpAmy\n\t\t\tANI_PEELOUT \t\t\t= ANI_RUNNING\n\t\t\tbreak\n",
        "= Player_Action_DblJumpAmy\n\t\t\tANI_PEELOUT \t\t\t= ANI_RUNNING\n\t\t\tbreak\n\n"
        + "".join(player_startup(e) for e in EXTRAS),
        "startup")
    return t


def player_startup(extra):
    """The extra's startup case: Sonic's moveset (abilities.py swaps in its own moves) with its own animation file.
    What every extra's case would repeat (the Super palette, its own colours, the character ID, jump offset and
    Peelout) is one block after the switch (abilities.py extra_startup): the player script was too big for the engine."""
    return (
        f"\t\t{extras.startup_case(extra)}\n"
        f"\t\t\tLoadAnimation(\"{extras.PLAYER_ANI}\")\n"
        "\t\t\tplayer[SLOT_PLAYER1].jumpAbility \t= Player_Action_DblJumpSonic\n"
        "\t\t\tbreak\n\n")


HUD_ICON, HUD_NAME = 46, 47  # the extra's life icon and name tag frames (after the game's 0-45)


def build_hud(t):
    # The character ID picks the life icon (ID + 15) and the name tag (icon + 9): for an extra, the icon's number
    # becomes 46 and the name tag's 47.
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == "temp0 = stage.playerListPos"]
    if len(hits) != 2:
        sys.exit(f"patch 'hud': anchor found {len(hits)} times (expected 2)")
    for i in reversed(hits):
        indent = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i + 1:i + 1] = [
            f"{indent}if temp0 >= PLAYER_EXTRA1_A // [NoSwap] the extra's life icon is frame {HUD_ICON}, its name tag "
            f"{HUD_NAME} (see ObjectStartup)",
            f"{indent}\ttemp0 = {HUD_ICON - 15}",
            f"{indent}end if",
        ]
    anchor = "#platform: USE_ORIGINS\n\t\ttemp0 += 9\n#endplatform\n"
    t = "\n".join(lines)
    for a in (anchor, anchor.replace("\t\t", "\t")):
        if t.count(a) != 1:
            sys.exit("patch 'hud': name tag offset anchor")
        ind = "\t\t" if a == anchor else "\t"
        t = t.replace(a, a + f"{ind}if stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] the extra's name tag\n"
                             f"{ind}\ttemp0 -= {HUD_ICON + 9 - HUD_NAME}\n{ind}end if\n", 1)
    t = patch(t,
        "\tforeach (TypeName[HUD], arrayPos0, ALL_ENTITIES)\n",
        "#platform: USE_ORIGINS\n"
        "\t// [NoSwap] the extra's HUD art (on the Display_NoSwap copy its package ships)\n"
        f"\t{ui().frame('life_icon', f'{HUD_ICON} - the extra life icon')}\n"
        f"\t{ui().frame('life_name', f'{HUD_NAME} - the extra name tag')}\n"
        "#endplatform\n\n"
        "\tforeach (TypeName[HUD], arrayPos0, ALL_ENTITIES)\n",
        "hud frames")
    return use_sheet_copy(t, "Global/Display.gif")


def build_act_finish(t):
    t = patch(t,
        "\tSpriteFrame(-43, 0, 47, 16, 182, 166)\t\t// #23 - \"Amy\"\n#endplatform\n",
        "\tSpriteFrame(-43, 0, 47, 16, 182, 166)\t\t// #23 - \"Amy\"\n\n"
        f"\t{ui().frame('act_name', '#24 - [NoSwap] the extra name, right-aligned like the others')}\n"
        "#endplatform\n",
        "act finish name frame")
    t = use_sheet_copy(t, "Global/Display.gif")
    return patch(t,
        "\tif stage.playerListPos != PLAYER_AMY_A\n\t\tDrawSpriteScreenXY(stage.playerListPos, temp0, 60)\n",
        "\tif stage.playerListPos != PLAYER_AMY_A\n"
        "\t\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] the extra's name is frame 24\n"
        "\t\t\tDrawSpriteScreenXY(24, temp0, 60)\n"
        "\t\telse\n"
        "\t\t\tDrawSpriteScreenXY(stage.playerListPos, temp0, 60)\n"
        "\t\tend if\n",
        "act finish name")


MONITOR_1UP_SONIC = "\t\t\tSpriteFrame(-8, -9, 16, 14, 51, 46) // 5 - MONITOR_1UP_SONIC, actually Sonic this time\n"


def monitor_1up_icon(t):
    t = patch(t, MONITOR_1UP_SONIC,
        "\n".join(extra_block("\t\t\t", [ui().frame("monitor_1up", "5 - the extra's own 1-UP icon")],
                               [MONITOR_1UP_SONIC.strip("\t\n")])) + "\n",
        "1-UP icon")
    return use_sheet_copy(t, "Global/Items.gif")


def build_broken_monitor(t):
    return __import__("treasure_sense").v4_broken_monitor(monitor_1up_icon(t))  # (jewel_thief: Rouge's 20 rings)


def build_monitor(t):
    t = abilities.apply_monitor(monitor_1up_icon(t))
    # Debug mode: the 1-UP icon offset is the character ID, which runs past the monitor list for extras
    t = patch_n(t,
        "\t\tif stage.playerListPos != PLAYER_AMY_A\n\t\t\ttemp0 += stage.playerListPos\n\t\tend if\n",
        "\t\tif stage.playerListPos != PLAYER_AMY_A\n"
        "\t\t\tif stage.playerListPos < PLAYER_EXTRA1_A // [NoSwap] extras use Sonic's 1-UP for now\n"
        "\t\t\t\ttemp0 += stage.playerListPos\n"
        "\t\t\tend if\n"
        "\t\tend if\n",
        "monitor debug icon", 2)
    # Debug mode list: offer Sonic's 1-UP to extras, like Amy
    return patch(t,
        "\t\t\t\t\t\tif stage.playerListPos == PLAYER_AMY\n\t\t\t\t\t\t\ttemp2 = true\n\t\t\t\t\t\tend if\n",
        "\t\t\t\t\t\tif stage.playerListPos == PLAYER_AMY\n\t\t\t\t\t\t\ttemp2 = true\n\t\t\t\t\t\tend if\n"
        "\t\t\t\t\t\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] extras use Sonic's 1-UP for now\n"
        "\t\t\t\t\t\t\ttemp2 = true\n"
        "\t\t\t\t\t\tend if\n",
        "monitor debug list")


def build_sign_post(t, items2_loads=2):
    # Sonic's spin frames, with the extra character's face as frame 5
    frames = ["SpriteFrame(-24, -16, 48, 32, 34, 182)", "SpriteFrame(-16, -16, 32, 32, 1, 150)",
              "SpriteFrame(-4, -16, 8, 32, 189, 131)", "SpriteFrame(-16, -16, 32, 32, 1, 183)",
              ui().frame("sign_face", "the extra's face"), "SpriteFrame(-16, -16, 32, 32, 1, 150)",
              "SpriteFrame(-4, -16, 8, 32, 189, 131)", "SpriteFrame(-16, -16, 32, 32, 1, 183)"]
    t = patch(t, "\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n",
        "\n".join(extra_block("\t", frames, comment="Sonic's spin frames with the extra's own face")) + "\n"
        "\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n",
        "signpost face")
    # SignPost loads Items2 once per platform block; the mission signpost only once
    return use_sheet_copy(t, "Global/Items2.gif", expected=items2_loads)


def build_mission_sign_post(t):
    return build_sign_post(t, items2_loads=1)


def build_goggles(t):
    return extras_take_case_at(t,
        "\t\tswitch stage.playerListPos\n\t\tcase PLAYER_SONIC_A\n\t\tcase PLAYER_SONIC_TAILS_A",
        "goggles")


# The special stage (docs/plan-b-modular-characters.md step 3b item 4): NoSwap's Special/PlayerObject.txt has no
# extra's case (an extra there is Sonic); each package ships its own copy, which loads its animation under a fixed
# name. NoSwap ships placeholders under those names (the DLL only redirects files NoSwap has): Sonic's SonicSS.ani and
# blank sheets.
SS_ANI = "NoSwapExtraSS.ani"
SS_SHEETS = 2  # Players/NoSwapExtraSS_1.gif, _2.gif: the sheets a package's SS_ANI names (the most any extra's needs)
SS_SWITCH = '\t\tswitch stage.playerListPos\n\t\tcase PLAYER_SONIC_A\n\t\t\tLoadAnimation("SonicSS.ani")\n'


def ss_sheet(k):
    return f"Players/NoSwapExtraSS_{k}.gif"


def build_special_player(t, extra=None):
    """extra None: NoSwap's own copy, where any extra takes Sonic's case. Else that extra's package copy: its own
    animation and colours before the switch (which has no case for it), as its case had them."""
    if extra is None:
        return extras_take_case_at(t, SS_SWITCH, "special startup: extras are Sonic without their package")
    body = [f'LoadAnimation("{SS_ANI}")'] + [l for l in palette_lines(extra, 0, "").split("\n") if l]
    body.append("player[0].animationSpeed = 48")
    return patch(t, SS_SWITCH,
        "\n".join(extra_block("\t\t", body, comment="this package's extra: its own special stage animation and "
                                                     "colours")) + "\n" + SS_SWITCH,
        "special startup")


def special_placeholders():
    """NoSwap's own files under the fixed names (never loaded by its own scripts: see SS_ANI)."""
    from PIL import Image
    anis = REPO / "mods" / "NoSwap" / "Sonic1u" / "Data" / "Animations"
    for e in EXTRAS:  # the per-extra .ani sheet2ani wrote here goes to the art's build folder, for the packages
        stash_special_ani(e)
    shutil.copyfile(REPO / "extracted" / "Sonic1" / "Data" / "Animations" / "SonicSS.ani", anis / SS_ANI)
    blank = Image.new("P", (16, 16), 0)
    blank.putpalette([0] * 768)
    for k in range(1, SS_SHEETS + 1):
        (SPRITES_OUT / ss_sheet(k)).parent.mkdir(parents=True, exist_ok=True)
        save_sheet(blank, SPRITES_OUT / ss_sheet(k))


def package_special(extra, game_dir):
    """A character package's special stage (tools/build_packages.py): its Special/PlayerObject.txt, and its special
    stage .ani (s1_special_ani) as SS_ANI naming the fixed sheet names, which are byte copies of the sheets it used."""
    import sheet2ani
    build_scripts({"Special/PlayerObject.txt": lambda t: build_special_player(t, extra)}, BASE,
                  game_dir / "Data" / "Scripts")
    ani = sheet2ani.read_ani(s1_special_ani(extra))
    if len(ani["sheets"]) > SS_SHEETS:
        sys.exit(f"{extra['file']}SS.ani names {len(ani['sheets'])} sheets: NoSwap ships {SS_SHEETS} (SS_SHEETS)")
    sprites = game_dir / "Data" / "Sprites"
    (sprites / "Players").mkdir(parents=True, exist_ok=True)
    for k in range(1, SS_SHEETS + 1):
        (sprites / ss_sheet(k)).unlink(missing_ok=True)
    for k, sheet in enumerate(ani["sheets"], 1):  # (sheet2ani's numbered sheets, kept with the art: extras.player_build)
        shutil.copyfile(extras.player_build(extra, "Sonic1u") / "Sprites" / sheet, sprites / ss_sheet(k))
    ani["sheets"] = [ss_sheet(k) for k in range(1, len(ani["sheets"]) + 1)]
    sheet2ani.write_ani(game_dir / "Data" / "Animations" / SS_ANI, ani)


SONIC_SWITCH = "\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n\tcase PLAYER_SONIC_TAILS_A\n"


MINI_ICON_SWITCH = SONIC_SWITCH + "\t\tSpriteFrame(-8, -11, 16, 23, 399, 376)\n"


def mini_icons(t):
    """Foot-tapping mini icons (continue screen): the extra's own."""
    return patch(t, MINI_ICON_SWITCH,
        "\n".join(extra_block("\t", [ui().frame("mini_1"), ui().frame("mini_2")])) + "\n" + MINI_ICON_SWITCH,
        "mini icons")


def build_special_finish(t):
    # The results screen defines its sprite frames per character; a missing case would shift every later frame
    # Extras use Sonic's results icons and super text and a nameless "GOT THEM ALL" (3 switches, none naming an
    # extra's ID): the special stage keeps the game's own Special/Objects.gif
    t = guard_special_retry(t, "value12")
    # "SONIC GOT THEM ALL" for extras: just "GOT THEM ALL" (the same line, cropped past "SONIC "), so no one
    # else's name shows. Every extra alike, Metal Sonic too (the user's call, 2026-09-26: no "SONIC" for him either)
    line = '\t\tSpriteFrame(-127, 0, 254, 16, 156, 435) // 3 - "SONIC GOT THEM ALL"\n'
    if t.count(line) != 1:
        sys.exit("special results: SONIC GOT THEM ALL frame not found")
    t = extras_skip_switch(t, t.rindex(SONIC_SWITCH, 0, t.index(line)),
                           ['SpriteFrame(-87, 0, 175, 16, 235, 435) // 3 - "GOT THEM ALL"'],
                           'no name, just "GOT THEM ALL"', "special results name")
    # the other two (the results icons, "NOW SONIC CAN BE SUPER SONIC"): any extra takes Sonic's
    return extras_take_case_at(t, SONIC_SWITCH, "special results icons and super text", expected=2)


def build_special_1up(t):
    return extras_take_case_at(t, SONIC_SWITCH, "special 1-UP")


ATTRACT_SWITCH = "\t\tswitch stage.playerListPos\n\t\tcase PLAYER_SONIC_A\n#platform: USE_ORIGINS\n\t\tcase PLAYER_AMY_A\n#endplatform\n"


def build_level_select(t):
    # Origins crashes if told a character ID it doesn't know: tell it Sonic, then keep playing the extra
    # (an extra picked in Origins' character select keeps playing in the level select)
    t = patch(t,
        "\t\t\tCallNativeFunction2(NotifyCallback, NOTIFY_PLAYER_SET, stage.playerListPos)\n",
        "\t\t\ttemp3 = stage.playerListPos // [NoSwap] never send Origins an extra's ID\n"
        "\t\t\tif stage.playerListPos > PLAYER_AMY_TAILS // (the level select may not load the player script's aliases)\n"
        "\t\t\t\tstage.playerListPos = PLAYER_SONIC\n"
        "\t\t\tend if\n"
        "\t\t\tCallNativeFunction2(NotifyCallback, NOTIFY_PLAYER_SET, stage.playerListPos)\n"
        "\t\t\tstage.playerListPos = temp3\n",
        "level select guard")
    # Testing aid: hold Y while starting Final Zone (entry 18) to go straight to the ending (presentation stage 1)
    return patch(t,
        "\t\t\tLoadStage()\n\n\t\t\tSetScreenFade(0x00, 0x00, 0x00, 0xFF)\n",
        "\t\t\tif object.currentSelection == 18 // [NoSwap] testing: Y held on Final Zone goes to the ending\n"
        "\t\t\t\tif keyDown[1].buttonY == true\n"
        "\t\t\t\t\tstage.activeList = PRESENTATION_STAGE\n"
        "\t\t\t\t\tstage.listPos = 1\n"
        "\t\t\t\tend if\n"
        "\t\t\tend if\n"
        "\t\t\tLoadStage()\n\n\t\t\tSetScreenFade(0x00, 0x00, 0x00, 0xFF)\n",
        "ending shortcut")


def build_zone_setup(t):
    # Demo and credits replays are recorded per character; extras replay Sonic's inputs
    return extras_take_case_at(t, ATTRACT_SWITCH, "attract replays")


def build_continue_setup(t):
    # Where the character lands on the continue screen; without a case the target is left unset
    t = extras_take_case_at(t,
        "\t\tswitch stage.playerListPos\n\t\tcase PLAYER_SONIC_A\n\t\tcase PLAYER_SONIC_TAILS_A",
        "continue landing")
    return extras_take_case_at(t,
        "\tswitch stage.playerListPos\n\tcase PLAYER_SONIC_A\n\tcase PLAYER_SONIC_TAILS_A",
        "continue position")


def build_continue(t):
    # Foot-tapping icons are defined per character; a missing case would shift later frames. The extra's
    # icons are on the Special/Objects_NoSwap.gif copy.
    return use_sheet_copy(mini_icons(t), "Special/Objects.gif")


def build_ending_pose(t):
    # Ending poses step through Sonic's frame numbers for extras; frames 0-9 are the extra's art (the fixed boxes on
    # the Ending/Objects_NoSwap copy its package ships: its ~10 poses, around the game frames it keeps: KEEP_FRAMES)
    t = extras_as_sonic_in_sonic_switches(t, 9, "ending pose")
    start = t.index("\t// 0 - Sonic Idle Frame\n")
    end = t.index("\t// 10 - \"Sonic the Hedgehog\"\n")
    sonic = [line[1:] if line.startswith("\t") else line for line in t[start:end].rstrip("\n").split("\n")]
    extra = [ui().frame(k, f"{n} - {k}") for n, k in enumerate(ENDING_KEYS)]
    t = t[:start] + "\n".join(extra_block("\t", extra, sonic, "the extra's poses take Sonic's frames 0-9")) + "\n\n" + t[end:]
    return use_sheet_copy(t, "Ending/Objects.gif")


def build_ending_control(t):
    return extras_as_sonic_in_sonic_switches(t, 2, "ending control")


def build_title_logo(t):
    # The title stage doesn't load the player script; the title character is Origins' (object.character). Without
    # Sonic's case, the emblem animation never runs and "Press Start" never appears: an extra takes Sonic's.
    anchor = "#platform: USE_ORIGINS\n\ttemp.titleCharacter = object.character\n#endplatform\n"
    return patch(t, anchor, anchor +
        f"\tif temp.titleCharacter >= {EXTRA_MIN_ID} // [NoSwap] extras use Sonic's title screen, like Amy\n"
        "\t\ttemp.titleCharacter = PLAYER_SONIC_A\n"
        "\tend if\n",
        "title emblem")


# Y on a card in Origins' character select opens the level select as that character (the DLL confirms the
# card and flips the flag, a magic number while the select is open: see CD_SHOT_MAGIC in the DLL)
Y_FLAG = "NoSwap_yLevelSelect"
Y_MAGIC = ["{v} = 0x4E53 // [NoSwap] the magic number 0x4E53593F: Y in the character select sets it to 1",
           "{v} <<= 16", "{v} += 0x593F"]


def build_title_start(t):
    t = patch(t, "private alias 5 : START_NOTIFYCALLBACK\n",
              "private alias 5 : START_NOTIFYCALLBACK\n\n"
              f"private value {Y_FLAG} = 0 // [NoSwap] 1: Y picked the character, open the level select\n", "y flag")
    t = patch(t, "\tcase START_NOTIFYCALLBACK\n\t\tgame.continueFlag = false\n",
              "\tcase START_NOTIFYCALLBACK\n\t\tgame.continueFlag = false\n"
              + "".join(f"\t\t{l.format(v=Y_FLAG)}\n" for l in Y_MAGIC), "y flag set")
    t = patch(t, "\t\t\tobject.timer = 0\n\t\t\tStopMusic()\n\t\telse\n\t\t\tif game.callbackResult == 0\n",
              "\t\t\tobject.timer = 0\n\t\t\tStopMusic()\n"
              f"\t\t\tif {Y_FLAG} == 1 // [NoSwap] Y on the card: this character's level select, without saving\n"
              "\t\t\t\tgame.continueFlag = false\n"
              "\t\t\t\toptions.gameMode = 0\n"
              "\t\t\t\tobject.state = START_STARTLVLSEL\n"
              "\t\t\tend if\n"
              f"\t\t\t{Y_FLAG} = 0\n"
              "\t\telse\n\t\t\tif game.callbackResult == 0\n"
              f"\t\t\t\t{Y_FLAG} = 0\n", "y level select")
    return t


# The whole-bank palette loads after which the extra's own colours are written again (noswap_common.WATER_FUNCTION)
WATER_LOADS = [("LZ_WaterPal.act", 1), ("SBZ3_WaterPal.act", 1), ("ElectricFlash.act", 2)]


def build_lz_setup(t):
    # Underwater (and SBZ3) palettes are whole-bank loads that would blank extras' own colour slots
    return water_colours_after_loads(t, WATER_LOADS, 3, "LZ setup")


def water_function(t):
    return water_colours_function(t, WATER_LOADS, gameconfig_palette(REPO / "extracted/Sonic1/Data/Game/GameConfig.bin"),
                                  REPO / "extracted/Sonic1/Data/Palettes")


BUILDERS = {
    "Players/PlayerObject.txt": lambda t: water_function(abilities.apply_player(build_player_object(t), "Sonic1u")),
    "LZ/Water.txt": lambda t: knux_like(abilities.apply_water(t)),
    "GHZ/BreakWall.txt": lambda t: knux_like(t, walls=True),  # (and extras that break walls: breaks_walls)
    "SLZ/BreakWall.txt": lambda t: knux_like(t, walls=True),  # (and extras that break walls: breaks_walls)
    "Mission/MissionWater.txt": knux_like,
    "LZ/LZSetup.txt": build_lz_setup,
    "Global/HUD.txt": build_hud,
    "Global/ActFinish.txt": build_act_finish,
    "Global/Monitor.txt": build_monitor,
    "Global/Ring.txt": abilities.apply_ring,  # magnetic extras pull rings in
    "Global/BrokenMonitor.txt": build_broken_monitor,
    "Global/SignPost.txt": build_sign_post,
    "Global/Goggles.txt": build_goggles,
    "Special/PlayerObject.txt": build_special_player,
    "Special/SpecialFinish.txt": build_special_finish,
    "Special/1UP.txt": build_special_1up,
    "GHZ/GHZSetup.txt": build_zone_setup,
    "MZ/MZSetup.txt": lambda t: abilities.apply_fire_tiles(build_zone_setup(t)),  # (lava tiles: fire_immune extras)
    "SYZ/SYZSetup.txt": build_zone_setup,
    "Mission/SignPost2.txt": build_mission_sign_post,
    "Continue/ContinueSetup.txt": build_continue_setup,
    "Continue/Continue.txt": build_continue,
    "Ending/EndingPose.txt": build_ending_pose,
    "Ending/EndingControl.txt": build_ending_control,
    "Title/Logo.txt": build_title_logo,
    "LevelSelect/MenuControl.txt": build_level_select,
    "Title/Start.txt": build_title_start,
}
# Extras' shots (tools/shots_v4.py): every script with a player loop hitting badniks, monitors or bosses gets a copy
# of it for the shots' group, and TailsObject.txt is the shot object while an extra plays
shots_v4.add_builders(BUILDERS, BASE)
# Heavy's full charge: enemies and bosses can't hurt him (noswap_common.juggernaut; after the shots' copies)
add_juggernaut_builders(BUILDERS, BASE, "Sonic1u")
__import__("psycho_grab").add_builders(BUILDERS, BASE, "Sonic1u")  # (Silver's Psychokinesis: the grabbable badniks)


# Scripts earlier builds wrote that the game's own versions now replace (extras save like the vanilla
# characters since they're real kinds in Origins' character select; the title picker is gone)
RETIRED = ["Global/DeathEvent.txt", "SBZ/Eggmobile.txt", "SBZ/PushButton.txt",
           "LZ/SBZ3Exit.txt"]


def main():
    if os.environ.get("NOSWAP_SCRIPTS_OUT"):  # just the player script, into a package (tools/build_packages.py)
        build_scripts({"Players/PlayerObject.txt": BUILDERS["Players/PlayerObject.txt"]}, BASE,
                      Path(os.environ["NOSWAP_SCRIPTS_OUT"]))
        return
    extras.stash_all_player_art()  # (sheet2ani's player .ani and sheets: packages ship them, NoSwap doesn't)
    for rel in RETIRED:
        (OUT / rel).unlink(missing_ok=True)
    (SPRITES_OUT / "Title" / "Title_NoSwap.gif").unlink(missing_ok=True)
    for sheet in UI_SHEETS:  # NoSwap's own copies: the boxes empty (the packages' have the art)
        (SPRITES_OUT / sheet).unlink(missing_ok=True)  # (never ship a modified game sheet under its own name)
    ui().write(SPRITES_OUT)
    special_placeholders()
    for rel, build in BUILDERS.items():
        src = BASE / rel
        raw = src.read_bytes().decode("utf-8")
        crlf = "\r\n" in raw
        text = raw.replace("\r\n", "\n")
        text = finish_script(build(text))
        if crlf:
            text = text.replace("\n", "\r\n")
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(text.encode("utf-8"))
        print(f"built {rel}")


if __name__ == "__main__":
    main()
