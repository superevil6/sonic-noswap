#!/usr/bin/env python3
"""Build the Sonic CD part of the NoSwap mod.

Same approach as build_sonic1.py: reads the community-decompiled Origins scripts installed next to
SonicOrigins.exe (Retro Engine v3 dialect for CD), applies anchored edits and writes the changed
scripts into mods/NoSwap/SonicCDu/Data/Scripts/. docs/soniccd_map.md lists the character-dependent sites.

Character packages (docs/plan-b-modular-characters.md step 3b item 6): NoSwap's shared scripts treat any
Stage.PlayerListPos >= 7 as "the extra" and load fixed file names (Global/Display_x.gif, Global/Items2_x.gif, the
NoSwap_Extra*.act palettes), which NoSwap ships as placeholders and each package supplies; what the shared scripts ask
of the extra's moves (Monitor, Ring, R4/Water) is a function its player script defines. tools/build_packages.py builds
the player scripts (NOSWAP_KEEP: NoSwap's own without any extra's moves, each package's with its own) and each
package's files (package_files: its copies of Special/Sonic.txt and Global/WarpSonic.txt, sheets and palettes).
Run build_packages.py after this: the player script this writes has every extra's moves.
"""
import os
import re
import sys
from pathlib import Path

from noswap_common import *  # noqa: F401,F403 - shared patch helpers
import extras
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
GAME_EXEC = Path(os.environ.get(
    "ORIGINS_EXEC",
    str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec",
))
BASE = GAME_EXEC / "SonicCDu" / "Scripts"
OUT = REPO / "mods" / "NoSwap" / "SonicCDu" / "Data" / "Scripts"
PACKAGES = REPO / "mods" / "NoSwap" / "characters"

# The extras whose own moves this player script build has (NOSWAP_KEEP: tools/build_packages.py builds NoSwap's own
# player script with none and each package's with only its own; unset: every extra's, the full build). Only the
# abilities (abilities.ABILITIES, which NOSWAP_KEEP filters) and the extras.py "roll" / "no_roll" rules follow it; every
# variant keeps each extra's basic startup (animation file, Sonic's moves, jump offset, idle), as in Sonic 1 / 2.
_KEPT = kept_extras()
OWN_EXTRAS = EXTRAS if _KEPT is None else _KEPT


# ---------------------------------------------------------------- v3 helpers
# CD's scripts use the v3 dialect: aliases are per file (no public alias), `if` compares one value,
# functions are declared with #function. See docs/soniccd_map.md section 2.

def v3_aliases():
    return "".join(f"#alias {e['id']}\t:\t{e['alias']} // [NoSwap]\n" for e in EXTRAS)


def add_aliases(t, name):
    """Declare the extras' IDs after the file's own Amy alias."""
    anchor = "#alias 5\t:\tPLAYER_AMY_A\n"
    return patch(t, anchor, anchor + v3_aliases(), f"{name} aliases")


def per_extra(indent, body):
    """One `if Stage.PlayerListPos == <extra>` block per extra, with body(extra) lines."""
    out = []
    for e in EXTRAS:
        out.append(f"{indent}if Stage.PlayerListPos == {e['alias']} // [NoSwap]")
        out += [f"{indent}\t{l}" for l in body(e)]
        out.append(f"{indent}end if")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- palettes
# Extras with colours of their own (Fang, Big) use the same palette slots as in S1/S2 (74-95). In CD those are
# Knuckles'/Amy's colours, which nothing else on screen uses while an extra plays. v3 scripts can't set single palette
# entries, so each package ships its colours as a palette file, under fixed names NoSwap ships placeholders for
# (docs/plan-b-modular-characters.md step 3b item 6):
# - OWN_ACT, loaded over its colour slots at stage start (its player script) and in the special stage (its
#   Special/Sonic.txt);
# - "NoSwap_Extra_<file>" for each underwater palette R4's BGEffects load into a whole bank: the game's file with the
#   extra's colours (tinted the same way) over its colour slots. NoSwap's shared BGEffects load it into the same bank,
#   whole, right after the game's for any extra; NoSwap's placeholder is the game's file unchanged.
PALETTES_IN = REPO / "extracted" / "SonicCD" / "Data" / "Palettes"
PALETTES_OUT = REPO / "mods" / "NoSwap" / "SonicCDu" / "Data" / "Palettes"
OWN_ACT = "NoSwap_Extra.act"
BANK_LOAD = re.compile(r'\s*LoadPalette\("([^"]+)", (\d+), 0, 0, 256\)')


def act_bytes(colours):
    data = bytearray(768)
    for i, c in colours.items():
        data[3 * i:3 * i + 3] = bytes(((c >> 16) & 255, (c >> 8) & 255, c & 255))
    return bytes(data)


def load_palette_line(e, bank, act):
    lo, hi = min(e["palette"]), max(e["palette"]) + 1
    return f'LoadPalette("{act}", {bank}, {lo}, {lo}, {hi}) // [NoSwap] own colours'


def own_palette_lines(e):
    """The extra's own colours over its slots in bank 0 (only in its own package's scripts: NOSWAP_KEEP)."""
    if not e["palette"] or e not in OWN_EXTRAS:
        return []
    return [load_palette_line(e, 0, OWN_ACT)]


def water_loads():
    """[(file, bank)] of the whole-bank palette loads (other than bank 0) in the scripts extra_water_palettes patches."""
    out = []
    for rel in WATER_SCRIPTS:
        for l in (BASE / rel).read_text(errors="ignore").replace("\r", "").split("\n"):
            m = BANK_LOAD.match(l)
            if m and m.group(2) != "0" and (m.group(1), int(m.group(2))) not in out:
                out.append((m.group(1), int(m.group(2))))
    return out


def water_palette(e, file):
    """The package's copy of an underwater palette file: the game's, with the extra's colours (tinted like the rest)
    over its colour slots (min to max, as the old per-extra load wrote them: slots in between with no colour of its
    own are black there too)."""
    master = act_palette(PALETTES_IN / "MasterPalette.act")
    tinted = act_palette(PALETTES_IN / file)
    lo, hi = min(e["palette"]), max(e["palette"]) + 1
    data = bytearray((PALETTES_IN / file).read_bytes())
    data[3 * lo:3 * hi] = act_bytes(tinted_palette(e, master[:64], tinted[:64]))[3 * lo:3 * hi]
    return bytes(data)


def extra_water_palettes(t, expected, name):
    """After each whole-bank load of an underwater palette, any extra's copy of it (its package's: water_palette)."""
    lines = t.split("\n")
    hits = []
    for i, l in enumerate(lines):
        m = BANK_LOAD.match(l)
        if m and m.group(2) != "0":
            hits.append((i, m.group(1), int(m.group(2))))
    if len(hits) != expected:
        sys.exit(f"{name}: found {len(hits)} bank loads (expected {expected})")
    for i, file, bank in reversed(hits):
        ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i + 1:i + 1] = [f"{ind}if Stage.PlayerListPos >= {EXTRA_ID} // [NoSwap] the extra's colours in it too "
                              "(its package's copy)",
                              f'{ind}\tLoadPalette("NoSwap_Extra_{file}", {bank}, 0, 0, 256)', f"{ind}end if"]
    return "\n".join(lines)


def package_palettes(e, palettes_out):
    """A package's palette files (none for an extra without colours of its own: NoSwap's placeholders then give
    exactly the game's)."""
    if not e["palette"]:
        return
    palettes_out.mkdir(parents=True, exist_ok=True)
    colours = dict(e["palette"])
    if e["id"] in ab.sparks():  # (the Shine Spark's glow: its amounts' colours, cd_spark_glow)
        if e["id"] in ab.charge_shots():
            sys.exit(f"extra {e['id']}: the Shine Spark's glow and a charge shot's flash share OWN_ACT's blocks")
        for k, pal in enumerate(ab.spark_glow_colours(e["id"])):
            lo = min(pal)
            for slot, rgb in pal.items():
                colours[SPARK_ACT + SPARK_STRIDE * k + slot - lo] = rgb
    if e["id"] in ab.charge_shots():  # (a charge shot's flash: its phases' colours, cd_charge_flash)
        lo, hi = min(e["palette"]), max(e["palette"]) + 1
        for k, phase in enumerate(ab.charge_palettes(e["id"])):
            for slot in range(lo, hi):
                colours[CHARGE_ACT + 32 * k + slot - lo] = phase.get(slot, e["palette"].get(slot, 0))
    (palettes_out / OWN_ACT).write_bytes(act_bytes(colours))
    for file, _ in water_loads():
        (palettes_out / f"NoSwap_Extra_{file}").write_bytes(water_palette(e, file))


def palette_placeholders():
    """NoSwap's own: OWN_ACT (never loaded by NoSwap's own scripts) and the game's underwater palettes unchanged; no
    per-extra files any more."""
    PALETTES_OUT.mkdir(parents=True, exist_ok=True)
    for old in PALETTES_OUT.glob("NoSwap_Extra*.act"):
        old.unlink()
    (PALETTES_OUT / OWN_ACT).write_bytes(bytes(768))
    for file, _ in water_loads():
        (PALETTES_OUT / f"NoSwap_Extra_{file}").write_bytes((PALETTES_IN / file).read_bytes())


# ---------------------------------------------------------------- player

# TEMPORARY, until CD has its picker: play every Sonic game as this extra ID (None = off). Saving is
# switched off so a test run can't write the extra into Sonic's own save.
TEST_AS = None


def build_player_object(t):
    t = add_aliases(t, "player")
    if TEST_AS:
        anchor = "sub ObjectStartup\n#platform: Use_Origins\n"
        t = patch(t, anchor, anchor +
                  "\tif Stage.PlayerListPos == PLAYER_SONIC_A // [NoSwap] TEST HOOK: Sonic plays as an extra\n"
                  f"\t\tStage.PlayerListPos = {TEST_AS}\n"
                  "\tend if\n"
                  f"\tif Stage.PlayerListPos == {TEST_AS}\n"
                  "\t\tOptions.GameMode = 0 // no saving\n"
                  "\tend if\n", "test hook")

    # Animation files (the shrunk "mini" form in Metallic Madness uses the full-size file for now)
    anchor = '\t\tif Stage.PlayerListPos == PLAYER_AMY\n\t\t\tLoadAnimation("Amy.Ani")\n\t\tend if\n'
    t = patch(t, anchor, anchor + "\n" + per_extra("\t\t", lambda e: [f'LoadAnimation("{extras.PLAYER_ANI}")']
                                                    + own_palette_lines(e)) + "\n", "animation file")
    anchor = ('\t\tif Stage.PlayerListPos == PLAYER_AMY\n\t\t\tLoadAnimation("MiniAmy.Ani")\n'
              '\t\t\tObject[1].Type = TypeName[Blank Object]\n\t\tend if\n')
    t = patch(t, anchor, anchor + "\n" + per_extra("\t\t", lambda e: [
        f'LoadAnimation("{extras.PLAYER_ANI}") // [NoSwap] no shrunk art yet', "Object[1].Type = TypeName[Blank Object]"]
        + own_palette_lines(e)) + "\n",
              "mini animation file")

    # Moves: Sonic's, with CD's own or the S2-style peel out and spin dash per the controls option.
    # Every extra must set all three pointers: CallFunction(0) would run Player_BadnikBreak on the player.
    anchor = ("\tif Stage.PlayerListPos == PLAYER_AMY\n\t\tPlayer.JumpAbility = Player_Action_DblJumpAmy\n"
              "\t\tPlayer.ActionPeelout = Player_Action_Jump\n")
    i = t.index(anchor)
    j = t.index("\tend if\n\n\tCallFunction(Player_SetJumpOffset)", i) + len("\tend if\n")
    moves = per_extra("\t", lambda e: [
        "Player.JumpAbility = Player_State_Static",
        "if Options.OriginalControls == false",
        "\tPlayer.ActionPeelout = Player_Action_Peelout_S2",
        "\tPlayer.ActionSpindash = Player_Action_Spindash_S2",
        "else",
        "\tPlayer.ActionPeelout = Player_Action_Peelout_CD",
        "\tPlayer.ActionSpindash = Player_Action_Spindash_CD",
        "end if",
    ] + ([  # extras.py "no_roll": down + jump out of a crouch is a plain jump (cd_no_roll)
        "if Options.AttractMode == false",
        "\tPlayer.ActionSpindash = Player_Action_Jump // [NoSwap] extras.py \"no_roll\": no Spin Dash",
        "end if",
    ] if e["no_roll"] and e in OWN_EXTRAS else []) + ([  # abilities.py ground_slide: down + jump is the slide
        "if Options.AttractMode == false",
        f"\tPlayer.ActionSpindash = NoSwap_GroundSlide{e['id']} // [NoSwap] abilities.py ground_slide: the Slide",
        "end if",
    ] if ab.has(e["id"], "ground_slide") and e in OWN_EXTRAS else []))
    t = t[:j] + "\n" + moves + t[j:]

    # Idle and waiting animations: Sonic's rules
    t = add_case_after(t, "\t\t\t\tswitch Stage.PlayerListPos\n\t\t\t\tcase PLAYER_SONIC_A\n\t\t\t\tcase PLAYER_TAILS_A\n",
                       "idle animation")

    # Jump offset: Sonic's
    anchor = "\t\tif Stage.PlayerListPos == PLAYER_AMY\n\t\t\tPlayer.JumpOffset = -4\n\t\tend if\n"
    t = patch(t, anchor, anchor + "\n" + per_extra("\t\t", lambda e: [
        f"Player.JumpOffset = {-1 if e['base'] == 'tails' else -5}"]).rstrip("\n") + "\n", "jump offset")
    return __import__("voltteccer").cd_patch(__import__("pot_magic").cd_patch(__import__("ninjutsu").cd_patch(__import__("free_flight").cd_patch(__import__("free_swim").cd_patch(__import__("treasure_sense").cd_patch(__import__("monitor_swap").cd_patch(__import__("water_walk").cd_patch(__import__("anchor_throw").cd_patch(__import__("head_throw").cd_patch(__import__("star_grab").cd_patch(cd_ear_touch(no_empty_functions(cd_spark_glow(cd_charge_flash(cd_spin_lean(cd_float_lean(cd_touch_attacks(cd_no_stomp(cd_copy_heads(cd_surge(cd_no_roll(cd_roll(apply_cd_abilities(t))))))))))))))))))))))))  # (free_swim: Ecco, tools/free_swim.py; free_flight: NiGHTS, tools/free_flight.py) (ninjutsu: Joe Musashi, tools/ninjutsu.py) (pot_magic: Gilius, tools/pot_magic.py) (voltteccer: Pulseman, tools/voltteccer.py)


NO_OP = "TempValue0 = TempValue0 // [NoSwap] (nothing to do for this build's extras: a statement, as every vanilla function has)"


def no_empty_functions(t):
    """A player script built without some extras' moves (NOSWAP_KEEP) can have functions with nothing in them, which the
    vanilla CD scripts never have (only empty subs): give each a no-op statement rather than rely on v3 compiling one."""
    return re.sub(r"^(function \w+\n)((?:[ \t]*(?://[^\n]*)?\n)*)(end function)",
                  lambda m: m.group(1) + m.group(2) + "\t" + NO_OP + "\n" + m.group(3), t, flags=re.M)


ANI_ROLL_CD = 50  # an extra's own rolling curl (extras.py "roll"; cd_config.py moves it from S1/S2's 49)
ROLL_FRAME_CD = "Object[5].YPos"  # NoSwap.RollFrame (cd_roll; slot 5's XPos is water_walk's mark, the values the moves')


def cd_roll(t):
    """extras.py "roll": rolling on the ground shows the extra's own curl instead of its jump, only while
    animating and drawing (as abilities.apply_roll does in S1/S2): the rest of the game sees ANI_JUMPING."""
    rollers = [e for e in OWN_EXTRAS if e["roll"]]
    if not rollers:
        return t
    body = []
    for e in rollers:
        ani = extras.player_ani(e, "SonicCDu")
        names = [a["name"] for a in ani["anims"]]
        if len(names) <= ANI_ROLL_CD or names[ANI_ROLL_CD] != "Rolling":
            sys.exit(f"{e['file']}.ani (CD): extras.py \"roll\" needs a \"Rolling\" animation in slot {ANI_ROLL_CD}")
        jump_frames = len(ani["anims"][names.index("Jumping")]["frames"])
        body += [f"if Stage.PlayerListPos == {e['alias']}",
                 "\tif Player.Animation == ANI_JUMPING",
                 "\t\tTempValue0 = false"]
        body += [l for s in ("Roll", "TubeRoll")
                 for l in (f"\t\tCheckEqual(Player.State, Player_State_{s})", "\t\tTempValue0 |= CheckResult")]
        body += ["\t\tif TempValue0 == true",
                 "\t\t\tPlayer.Animation = ANI_NOSWAP_ROLL",
                 "\t\t\tif Player.PrevAnimation == ANI_JUMPING // still rolling: keep the curl's frame",
                 "\t\t\t\tPlayer.PrevAnimation = ANI_NOSWAP_ROLL",
                 "\t\t\t\tPlayer.Frame = NoSwap.RollFrame",
                 "\t\t\tend if",
                 "\t\telse",
                 f"\t\t\tif Player.Frame >= {jump_frames} // just out of the curl: back to a jump frame",
                 "\t\t\t\tPlayer.Frame = 0",
                 "\t\t\tend if",
                 "\t\tend if",
                 "\tend if",
                 "end if"]
    functions = ("// [NoSwap] extras.py \"roll\": the extra's own rolling curl, only while animating and drawing\n"
                 "function NoSwap_RollIn\n" + "".join(f"\t{l}\n" for l in body) + "end function\n\n\n"
                 "function NoSwap_RollOut\n"
                 "\tif Player.Animation == ANI_NOSWAP_ROLL\n"
                 "\t\tPlayer.Animation = ANI_JUMPING\n"
                 "\t\tPlayer.PrevAnimation = ANI_JUMPING\n"
                 "\t\tNoSwap.RollFrame = Player.Frame // the curl's frame kept aside (as abilities.apply_roll): the jump may\n"
                 "\t\tPlayer.Frame = 0 // have fewer frames, and the game reads the frame's hitbox (a curl frame past the jump's shook him)\n"
                 "\tend if\n"
                 "end function\n\n\n")
    t = patch(t, "#alias 49 : ANI_NOSWAP_GLIDE_DOWN // [NoSwap]\n",
              "#alias 49 : ANI_NOSWAP_GLIDE_DOWN // [NoSwap]\n"
              f"#alias {ANI_ROLL_CD} : ANI_NOSWAP_ROLL // [NoSwap] extras.py \"roll\": the extra's own rolling curl\n"
              f"#alias {ROLL_FRAME_CD} : NoSwap.RollFrame // [NoSwap] the curl's frame while the game sees the jump "
              "(NoSwap_RollOut; reserved slot 5's YPos: nothing else uses it)\n",
              "roll alias")
    t = patch(t, "#function Player_ForceGrip\n",
              "#function Player_ForceGrip\n#function NoSwap_RollIn\n#function NoSwap_RollOut\n", "roll declarations")
    t = patch(t, "\nfunction Player_BadnikBreak\n", "\n" + functions + "function Player_BadnikBreak\n", "roll functions")
    start = t.index("sub ObjectMain\n")
    end = t.index("end sub\n", start)
    main = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_RollIn) // [NoSwap] an extra's own rolling curl\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_RollOut)\n"), t[start:end])
    if main.count("CallFunction(NoSwap_RollIn)") != 2:
        sys.exit("roll: expected 2 ProcessAnimation calls in ObjectMain")
    t = t[:start] + main + t[end:]
    return patch(t, "\tDrawPlayerAnimation()\nend sub\n",
                 "\tCallFunction(NoSwap_RollIn) // [NoSwap] an extra's own rolling curl\n"
                 "\tDrawPlayerAnimation()\n\tCallFunction(NoSwap_RollOut)\nend sub\n", "roll draw")


def cd_no_roll(t):
    """extras.py "no_roll" (Gamma never curls into a ball), as abilities.apply_no_roll does in S1/S2: down while
    moving doesn't roll (the ground state's and the 3D ramps' roll starts are skipped for them: NoSwap_RollAllowed),
    and their spin dash action is a plain jump (build_player_object). Crouching still works; objects that force a
    roll (tubes) still do. The attract mode keeps Sonic's rolls."""
    extras = [e for e in OWN_EXTRAS if e["no_roll"]]
    slides = [e for e in OWN_EXTRAS if ab.has(e["id"], "ground_slide")]  # (no roll out of the Slide: NoSwap.Slide running)
    sparks = [e for e in OWN_EXTRAS if e["id"] in ab.sparks()]  # (the Shine Spark: down at full charge stores it)
    if not extras and not slides and not sparks:
        return t
    body = ["CheckResult = true", "if Options.AttractMode == false"]
    for e in extras:
        body += [f"\tif Stage.PlayerListPos == {e['alias']}", "\t\tCheckResult = false", "\tend if"]
    for e in slides:
        body += [f"\tif Stage.PlayerListPos == {e['alias']} // abilities.py ground_slide: not mid-slide",
                 "\t\tif NoSwap.Slide > 0", "\t\t\tCheckResult = false", "\t\tend if", "\tend if"]
    for e in sparks:
        body += [f"\tif Stage.PlayerListPos == {e['alias']} // abilities.py charge's Shine Spark: down stores it, no roll",
                 f"\t\tif Object[5].PropertyValue >= {CD_JUGGERNAUT} // (at full charge: charge_after's mark)",
                 "\t\t\tCheckResult = false", "\t\tend if",
                 "\t\tif NoSwap.Spark > 0 // (stored, or flying)", "\t\t\tCheckResult = false", "\t\tend if", "\tend if"]
    body += ["end if"]
    functions = ("// [NoSwap] extras.py \"no_roll\": CheckResult false for extras that never roll (build_soniccd.py cd_no_roll)\n"
                 "function NoSwap_RollAllowed\n" + "".join(f"\t{l}\n" for l in body) + "end function\n\n\n")
    t = patch(t, "#function Player_ForceGrip\n", "#function Player_ForceGrip\n#function NoSwap_RollAllowed\n",
              "no-roll declaration")
    t = patch(t, "\nfunction Player_BadnikBreak\n", "\n" + functions + "function Player_BadnikBreak\n", "no-roll function")
    guard = ["CallFunction(NoSwap_RollAllowed) // [NoSwap] extras.py \"no_roll\": down doesn't roll them",
             "if CheckResult == true"]
    for fn in ("function Player_State_Ground", "function Player_State_Ramp3D"):
        t = guard_blocks(t, fn, r"\t+Player\.State\s*= Player_State_Roll$", guard, ["end if"], 2, "no roll")
    # slide_running (abilities.slide_running_function's CD twin: Mega Man slides out of a run): the ground state's jump
    # press, with down held and no slide running, starts the slide instead of the jump
    runs = [e for e in slides if cfg(e["id"]).get("slide_running")]
    if runs:
        fn = t.index("\nfunction Player_State_Ground\n")
        end = t.index("\nend function", fn)
        jump = "\t\tif Player.JumpPress == true\n\t\t\tCallFunction(Player_Action_Jump)\n\t\telse\n"
        if t[fn:end].count(jump) != 1:
            sys.exit("slide_running: CD's ground state jump press isn't there once")
        i0 = t.index(jump, fn)
        cases = "".join(f"\t\t\tif Stage.PlayerListPos == {e['alias']} // [NoSwap] slide_running: down + jump slides out of a run\n"
                        "\t\t\t\tif Player.Down == true\n\t\t\t\t\tif NoSwap.Slide == 0\n"
                        f"\t\t\t\t\t\tCallFunction(NoSwap_GroundSlide{e['id']})\n\t\t\t\t\t\tCheckResult = true\n"
                        "\t\t\t\t\tend if\n\t\t\t\tend if\n\t\t\tend if\n" for e in runs)
        t = (t[:i0] + "\t\tif Player.JumpPress == true\n\t\t\tCheckResult = false\n" + cases
             + "\t\t\tif CheckResult == false\n\t\t\t\tCallFunction(Player_Action_Jump)\n\t\t\tend if\n\t\telse\n"
             + t[i0 + len(jump):])
    return t


def add_case_after(t, anchor, name):
    """Add every extra's case label after the last line of `anchor` (a switch's first cases)."""
    last = anchor.rstrip("\n").split("\n")[-1]
    ind = last[: len(last) - len(last.lstrip("\t"))]
    labels = "".join(f"{ind}case {e['alias']} // [NoSwap] behaves like Sonic\n" for e in EXTRAS)
    return patch(t, anchor, anchor + labels, name)


# ---------------------------------------------------------------- abilities (CD port of tools/abilities.py)
# Same moves and numbers as in S1/S2 (abilities.ABILITIES), rewritten for v3. Differences:
# - No free player value and no script values in v3: ability state lives in reserved entity slot 5,
#   which no script uses (cleared on every stage load; reset again at each extra's startup).
# - CD's scripts only see buttons A/B/C (all jump), so shots (Fang's cork gun, Big's fishing line) are
#   fired with look up + jump, Sonic's peel-out input (Tails/Knuckles/Amy just jump there).
# - Attack animations use CD's Amy hammer slots 45/46, which enemies already count as attacks.
# - Shot reach: v3 has no hitbox override, and a wider animation hitbox would also hit walls. Instead,
#   while a shot is out, enemies widen their own box toward the player (enemy_reach below).
import abilities as ab
__import__("own_sounds").mark_classic(ab.ABILITIES, extras.EXTRAS)  # (own sounds: their Sonic 1/2/CD fields marked, tools/own_sounds.py)
import shots_v3


def cd_melee(i):
    """The melee in CD: an extra with a real shot (abilities.py "shot", tools/shots_v3.py) throws that instead (its
    melee frames are only the throw pose)."""
    return ab.has(i, "melee") and (not ab.shot(i, "cd") or ab.down_shot(i)  # (a down + Y shot keeps Y's melee,
                                    or ab.slam_shot(i)  # and a slam's isn't thrown with Y at all,
                                    or ab.up_shot(i))  # nor an up + Y one: John's whip)


# A down + Y shot's cooldown (abilities.down_shot: Mecha's spike ball): the melee has NoSwap.ShotCooldown's value
# (NoSwap.Shot), so it counts in one of its own, which none of the extra's other moves may use
DOWN_SHOT_COOLDOWN = "Object[5].Value6"
VALUE6_MOVES = ("ray_glide", "aim_dash", "ear_grapple", "triple_jump", "wall_cling", "power_surge")


def cd_shot(i):
    """The extra's CD shot (abilities.shot), checked against what the CD port does; None without one."""
    s = ab.shot(i, "cd")
    if s:
        if s["motion"] not in ab.SHOT_MOTIONS:
            sys.exit(f"shot: extra {i}: motion {s['motion']!r} (Sonic CD: {', '.join(ab.SHOT_MOTIONS)})")
        if s.get("cycle") and (ab.has(i, "ray_glide") or ab.has(i, "puddle_slide") or ab.has(i, "ear_grapple")
                               or ab.has(i, "power_surge") or ab.has(i, "wall_cling") or ab.has(i, "spirit_flight")
                               or ab.has(i, "triple_jump") or ab.has(i, "melee")):
            sys.exit(f"shot: extra {i}: a cycle shot's NoSwap.ShotNext (Object[5].Value4) is another move's value")
        if s["motion"] == "boomerang" and s.get("aim"):
            sys.exit(f"shot: extra {i}: a boomerang isn't aimed")
        ab.check_homing(i, s)
        if ab.has(i, "ray_glide"):  # (NoSwap.ShotPose shares Object[5].Value7 with NoSwap.GlideCap)
            sys.exit(f"shot: extra {i} has ray_glide, whose value the shot's shares")
    return s


def cd_shot2(i):
    """The extra's second CD shot (abilities.shot2: down + Y, Robotnik's Bomb Drop), checked; None without one."""
    s = ab.shot2(i, "cd")
    if s:
        ab.check_shot2(i, "cd")
        cd_shot(i)
    return s


ANI_SURGE_CD = {"idle": 51, "run": 52, "sprint": 53}  # cd_config.py moves them from S1/S2's 50-52
STATE_ALIASES = (
    "#alias Object[5].Value0 : NoSwap.Ability // [NoSwap] Jet Dash: >0 frames left, <0 hover used; umbrella: 1 open, 2 closed\n"
    "#alias Object[5].Value1 : NoSwap.Pogo // [NoSwap] true while pogo bouncing\n"
    "#alias Object[5].Value2 : NoSwap.Shot // [NoSwap] game frames left in the current shot\n"
    "#alias Object[5].Value2 : NoSwap.ShotCooldown // [NoSwap] a real shot (tools/shots_v3.py): frames before the next throw\n"
    "#alias Object[5].Value7 : NoSwap.ShotPose // [NoSwap] its throw pose's frames left (not Ray's)\n"
    "#alias Object[5].Value3 : NoSwap.Reach // [NoSwap] shot reach in px while the shot is out, read by enemies\n"
    "#alias Object[5].Value4 : NoSwap.GlideVX // [NoSwap] Ray's glide: its own velocity (Ability holds its angle)\n"
    "#alias Object[5].Value4 : NoSwap.Cooldown // [NoSwap] Espio's Leaf Swirl: frames until the next (not Ray's)\n"
    "#alias Object[5].Value5 : NoSwap.GlideVY // [NoSwap]\n"
    "#alias Object[5].Value6 : NoSwap.GlideLift // [NoSwap] a swoop's upward push\n"
    "#alias Object[5].Value6 : NoSwap.Flown // [NoSwap] Charmy's Stinger took him out of his flight (not Ray's)\n"
    "#alias Object[5].Value7 : NoSwap.GlideCap // [NoSwap] speed cap\n"
    "#alias Object[5].Value4 : NoSwap.GrappleX // [NoSwap] Max's Ear Grapple: where the ear latched on (not Ray's)\n"
    "#alias Object[5].Value5 : NoSwap.GrappleY // [NoSwap]\n"
    "#alias Object[5].Value6 : NoSwap.GrappleDir // [NoSwap] the direction the ear went out in (not Ray's)\n"
    "#alias Object[5].Value4 : NoSwap.SpiritVX // [NoSwap] Tikal's Spirit Flight: the orb's own velocity (not Ray's)\n"
    "#alias Object[5].Value5 : NoSwap.SpiritVY // [NoSwap]\n"
    "#alias Object[5].Value4 : NoSwap.JumpChain // [NoSwap] Mario's Triple Jump: the last jump's number (4: the third's flip over)\n"
    "#alias Object[5].Value5 : NoSwap.JumpWindow // [NoSwap] frames left on the ground to jump again\n"
    "#alias Object[5].Value6 : NoSwap.JumpSave // [NoSwap] his jump strength, while Player_Action_Jump uses a higher one\n"
    "#alias Object[5].Value4 : NoSwap.Cling // [NoSwap] Trip's Wall Cling: frames on the wall (0: not clinging)\n"
    "#alias Object[5].Value5 : NoSwap.ClingDir // [NoSwap] the wall's side (FACING_RIGHT: on her right), after: the one let go of\n"
    "#alias Object[5].Value6 : NoSwap.ClingLock // [NoSwap] frames (away from it) before she can cling to that side again\n"
    "#alias 45 : ANI_NOSWAP_ATTACK // [NoSwap]\n#alias 46 : ANI_NOSWAP_SHOT // [NoSwap]\n#alias 47 : ANI_NOSWAP_HOVER // [NoSwap]\n"
    "#alias 48 : ANI_NOSWAP_GLIDE_UP // [NoSwap] Ray's glide poses\n#alias 49 : ANI_NOSWAP_GLIDE_DOWN // [NoSwap]\n"
    "#alias 48 : ANI_NOSWAP_CLING // [NoSwap] Trip's Wall Cling (S1/S2's 47)\n"
    "#alias 7 : SFX_G_RELEASE // [NoSwap]\n#alias 24 : SFX_G_FLYING // [NoSwap]\n#alias 22 : SFX_G_EXPLOSION // [NoSwap]\n"
    "#alias 34 : SFX_G_GRAB // [NoSwap]\n"
    "#alias Object[5].Value4 : NoSwap.Surge // [NoSwap] Power Surge: frames left, the surge then its cooldown\n"
    "#alias Object[5].Value5 : NoSwap.ZipCarry // [NoSwap] her Thunder Zip: the speed she keeps after it (signed)\n"
    "#alias Object[5].Value6 : NoSwap.SurgeTop // [NoSwap] her top speed before the surge (to put back after it)\n"
    f"#alias {ANI_SURGE_CD['idle']} : ANI_NOSWAP_SURGE_IDLE // [NoSwap] the Power Surge idle / walk / run (S1/S2's 50-52)\n"
    f"#alias {ANI_SURGE_CD['run']} : ANI_NOSWAP_SURGE_RUN // [NoSwap]\n"
    f"#alias {ANI_SURGE_CD['sprint']} : ANI_NOSWAP_SURGE_SPRINT // [NoSwap]\n"
    "#alias 10 : SFX_G_SHIELD // [NoSwap] the shield monitor's sound (Power Surge)\n"
)
# Only declared when an extra has the move (so the other packages' scripts don't change)
PUDDLE_ALIAS = "#alias Object[5].Value5 : NoSwap.Puddle // [NoSwap] Chaos' Puddle Slide: its game frames left on the ground\n"
SLIDE_ALIAS = ("#alias Object[5].Value1 : NoSwap.Slide // [NoSwap] Ray Poward's Slide (abilities.py ground_slide): its game "
               "frames left (NoSwap.Pogo's value: never with the pogo)\n")
SHOT_NEXT_ALIAS = ("#alias Object[5].Value4 : NoSwap.ShotNext // [NoSwap] a cycle shot (Flicky's critters): the frame the "
                   "next throw takes\n")
SPARK_ALIAS = ("#alias Object[5].Value5 : NoSwap.Spark // [NoSwap] Heavy's Shine Spark: 0 none; 1.. stored (frames left); "
               "1000 + its kind (+ 100 left): flying (abilities.py SPARK_ACTIVE)\n"
               "#alias 48 : ANI_NOSWAP_SPARK // [NoSwap] its pose up / up-forward (S1/S2's 45; cd_config.py: from 47)\n")
CHARGE_ALIAS = ("#alias Object[5].Value4 : NoSwap.Charge // [NoSwap] Heavy's Charge: the speed it set last frame, signed "
                "by its direction (0: none)\n")
BUSTER_ALIAS = ("#alias Object[5].Value4 : NoSwap.BusterCharge // [NoSwap] a charge shot (shot2 \"input\" \"charge\": Mega "
                "Man's Charge Shot): frames Y has been held\n")
Y_HELD_ALIAS = ("#alias Object[5].Value6 : NoSwap.YHeld // [NoSwap] a move held on Y (Y_HOLD): frames Y still counts as "
                "held since the DLL last said so\n")
SPIN_ALIAS = ("#alias Object[5].Value4 : NoSwap.Spin // [NoSwap] Honey's Spin Attack: frames spun (0: ready; below 0: "
              "the cooldown)\n"
              "#alias Object[5].Value5 : NoSwap.SpinVY // [NoSwap] her vertical speed at the end of her last update\n")
HIGH_KICK_ALIAS = ("#alias Object[5].Value4 : NoSwap.HiKick // [NoSwap] Sally's Spin-Kick High Jump: 0 none; 1.. the wind-up; "
                   "1000.. the kick; 2000.. the recovery\n"
                   "#alias Object[5].Value5 : NoSwap.HiKickUsed // [NoSwap] used this airborne period\n"
                   "#alias Object[5].Value6 : NoSwap.HiKickCool // [NoSwap] frames on the ground before the next\n")
WARP_ALIAS = ("#alias Object[5].Value5 : NoSwap.WarpDir // [NoSwap] Tails Doll's Phase Warp: its direction, (x + 1) + 3 * (y + 1)\n"
              "#alias Object[5].Value6 : NoSwap.WarpVX // [NoSwap] his speed along before it (he has it again after)\n")
WARP_MOVES = ("ray_glide", "wall_cling", "puddle_slide", "spin_attack", "high_kick", "thunder_zip", "power_surge",
              "water_swim", "aim_dash", "ear_grapple", "triple_jump", "spirit_flight", "charge")  # (Value5 / Value6 users)
SWIM_B_ALIAS = ("#alias Object[5].Value6 : NoSwap.SwimB // [NoSwap] Chaos' water swim: frames before the next stroke "
                "(his Puddle Slide has Value5)\n")
SWIM_ALIAS = ("#alias Object[5].Value5 : NoSwap.Swim // [NoSwap] Big's water swim: frames before the next stroke\n"
              "#alias 48 : ANI_NOSWAP_SWIM // [NoSwap] its stroke (S1/S2's 47)\n")
SINK_ALIAS = ("#alias Object[5].Value4 : NoSwap.Sink // [NoSwap] Mephiles' Shadow Sink (abilities.py sink): 0 ready; below 0 "
              "the cooldown; 1.. sinking, then under; 1000.. rising\n"
              "#alias 48 : ANI_NOSWAP_SINK // [NoSwap] its frames (S1/S2's 47)\n")
# (Object[5].Value4's other users: an extra with the sink has none of them, sink_after checks)
SINK_VALUE4_MOVES = ("ray_glide", "ear_grapple", "spirit_flight", "triple_jump", "wall_cling", "power_surge", "charge",
                     "spin_attack", "high_kick", "water_swim", "puddle_slide", "phase_warp")
CYCLE_ALIAS = ("#alias Object[5].Value4 : NoSwap.CopyMove // [NoSwap] ability_cycle (Emerl's Copycat): the active jump "
               "ability's place in the cycle\n")
# Moves held on Y (Heavy's Charge): the player script keeps CD_HOLD_MAGIC (0x4E53593E) in game.callbackParam3 instead of
# Y_REARM's number; the DLL then writes 1 on a Y press and 2 while Y stays down (NoSwapS3K.cpp CdShotButton). Its thread
# polls every 10 ms or so, a frame lasts 16.7: Y counts as held for Y_HOLD_FRAMES frames after it last said so.
Y_REARM_HOLD = [
    "game.callbackParam3 = 0x4E53 // the hold magic number 0x4E53593E, for the DLL to find (a Y press: 1; Y down: 2)",
    "game.callbackParam3 <<= 16",
    "game.callbackParam3 += 0x593E",
]
Y_HOLD_FRAMES = 3


def hold_moves(i):
    return ab.has(i, "charge") or ab.has(i, "spin_attack") or i in ab.charge_shots() or ab.has(i, "sink")


SPIN_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump"]


def spin_after(i):
    """Honey's Spin Attack in CD (abilities.spin_after): Y (a press, from the DLL) starts it in SPIN_STATES; it goes on
    while Y is held (NoSwap.YHeld), spin_frames at most, then spin_cooldown. Floaty in the air (part of the gravity taken
    back); an attack throughout (45 in the air, 46 on the ground: CD's Amy hammer slots, and cd_touch_attacks)."""
    c = cfg(i)
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = extras.player_ani(e, "SonicCDu")["anims"]
    n = len(anims[45]["frames"]) if len(anims) > 46 else 0
    if not n or len(anims[46]["frames"]) != n:
        sys.exit(f"spin_attack: extra {i} needs its CD spin in 45 (air) and 46 (ground) (cd_config)")
    states = [x for st in SPIN_STATES for x in (f"CheckEqual(Player.State, {st})", "TempValue0 |= CheckResult")]
    return y_hold_lines() + ["TempValue0 = false // Spin Attack (build_soniccd.spin_after): a state it can be in"] + states + [
        "if Player.Animation == ANI_HURT", "\tTempValue0 = false", "end if",
        "if NoSwap.Spin < 0 // the cooldown", "\tNoSwap.Spin++", "end if",
        "if NoSwap.Spin == 0", "\tif game.callbackParam3 == 1 // a Y press, from the DLL", "\t\tif TempValue0 == true",
        "\t\t\tNoSwap.Spin = 1", f"\t\t\tPlaySfx({c['spin_sfx_cd']}, false)", "\t\tend if", "\tend if", "end if",
        "if NoSwap.Spin > 0",
        "\tif NoSwap.YHeld == 0 // let go, too long or out of it: over", "\t\tTempValue0 = false", "\tend if",
        f"\tif NoSwap.Spin > {c['spin_frames']}", "\t\tTempValue0 = false", "\tend if",
        "\tif TempValue0 == false", f"\t\tNoSwap.Spin = -{c['spin_cooldown']}",
        "\t\tif Player.Gravity == GRAVITY_AIR", "\t\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING", "\t\t\tend if", "\t\telse", "\t\t\tif Player.Animation == ANI_NOSWAP_SHOT",
        "\t\t\t\tPlayer.Animation = ANI_WALKING", "\t\t\tend if", "\t\tend if",
        "\telse",
        "\t\tTempValue1 = NoSwap.Spin // its frame, by its own clock", f"\t\tTempValue1 /= {c['spin_ticks']}",
        f"\t\tTempValue1 %= {n}", "\t\tNoSwap.Spin++",
        "\t\tif Player.Gravity == GRAVITY_AIR",
        "\t\t\tTempValue2 = Player.GravityStrength // floaty: part of this frame's gravity taken back",
        f"\t\t\tTempValue2 *= {256 - c['spin_gravity']}", "\t\t\tTempValue2 >>= 8", "\t\t\tPlayer.YVelocity -= TempValue2",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_ATTACK",
        "\t\telse", "\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT", "\t\tend if",
        "\t\tPlayer.Frame = TempValue1", "\t\tPlayer.PrevAnimation = Player.Animation // (the frame is picked here)",
        "\t\tPlayer.AnimationTimer = 0",
        "\tend if",
        "end if",
        "NoSwap.SpinVY = Player.YVelocity // (spin_before: what the game's objects do to it)",
    ] + Y_REARM_HOLD


def spin_before(i):
    """Honey's Spin Attack at the start of her update in CD (abilities.spin_before): a badnik she broke bounced her as CD's
    Player_BadnikBreak does (-v falling, v + 0.75 px otherwise), a monitor as its own code does (-v, at least 2 px up):
    then the hard bounce, up, and away on the ground."""
    c = cfg(i)
    return ["if NoSwap.Spin > 0 // Spin Attack: did the game bounce her off something? (build_soniccd.spin_before)",
            "\tif Player.YVelocity != NoSwap.SpinVY // (something changed it since her last update)",
            "\t\tTempValue0 = false",
            "\t\tTempValue1 = NoSwap.SpinVY", "\t\tFlipSign(TempValue1)",
            "\t\tif Player.YVelocity == TempValue1 // a badnik she fell on, a monitor", "\t\t\tTempValue0 = true", "\t\tend if",
            "\t\tTempValue1 = NoSwap.SpinVY", "\t\tTempValue1 += 0xC000",
            "\t\tif Player.YVelocity == TempValue1 // a badnik, going up or on the ground", "\t\t\tTempValue0 = true",
            "\t\tend if",
            "\t\tif Player.YVelocity == -0x20000 // a monitor, from a slow fall or the ground", "\t\t\tTempValue0 = true",
            "\t\tend if",
            "\t\tif TempValue0 == true // a hard bounce",
            f"\t\t\tPlayer.YVelocity = -{c['spin_bounce']:#x}",
            "\t\t\tPlayer.Timer = 0 // (as after a spring: letting go of jump doesn't cut it short)",
            "\t\t\tif Player.Gravity == GRAVITY_GROUND // on the ground: up and away, a pinball",
            f"\t\t\t\tTempValue1 = -{c['spin_bounce_x']:#x}", "\t\t\t\tif Player.Direction == FACING_LEFT",
            "\t\t\t\t\tFlipSign(TempValue1)", "\t\t\t\tend if",
            "\t\t\t\tPlayer.Speed = TempValue1", "\t\t\t\tPlayer.XVelocity = TempValue1",
            "\t\t\t\tPlayer.Gravity = GRAVITY_AIR", "\t\t\t\tPlayer.State = Player_State_Air", "\t\t\t\tPlayer.Angle = 0",
            "\t\t\t\tPlayer.CollisionMode = CMODE_FLOOR",
            "\t\t\tend if",
            "\t\t\tNoSwap.SpinVY = Player.YVelocity",
            "\t\tend if",
            "\tend if",
            "end if"]


def high_kick_after(i):
    """Sally's Spin-Kick High Jump in CD (abilities.high_kick_after, the same phases in NoSwap.HiKick): Y (a press, from
    the DLL: Y_REARM) in abilities.HIGH_KICK_STATES starts it; the wind-up and the recovery in 47 (frames 0 / 1, not
    attacks), the kick in 46 (an attack: CD's Amy hammer slot)."""
    c = cfg(i)
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = extras.player_ani(e, "SonicCDu")["anims"]
    n = len(anims[46]["frames"]) if len(anims) > 47 else 0
    if not n or len(anims[47]["frames"]) != 2:
        sys.exit(f"high_kick: extra {i} needs its CD kick in 46 and the wind-up / recovery in 47 (cd_config)")
    shared = [m for m in ("ray_glide", "aim_dash", "ear_grapple", "spirit_flight", "triple_jump", "wall_cling",
                          "power_surge", "thunder_zip", "puddle_slide", "charge", "spin_attack") if ab.has(i, m)]
    if shared or c.get("melee_cooldown"):  # (HIGH_KICK_ALIAS: Object[5].Value4-6 are theirs too)
        sys.exit(f"high_kick: extra {i}: its CD values (Object[5].Value4-6) are also {shared or 'the melee cooldown'}'s")
    k, r = ab.HIGH_KICK_KICK, ab.HIGH_KICK_RECOVER
    states = [x for st in ab.HIGH_KICK_STATES for x in (f"CheckEqual(Player.State, {st})", "TempValue0 |= CheckResult")]
    return ["TempValue0 = false // Spin-Kick High Jump (build_soniccd.high_kick_after): a state it can be in"] + states + [
        "if Player.Animation == ANI_HURT", "\tTempValue0 = false", "end if",
        "if Player.Gravity == GRAVITY_GROUND", "\tif NoSwap.HiKick == 0 // (not in its wind-up)",
        "\t\tNoSwap.HiKickUsed = false", "\t\tif NoSwap.HiKickCool > 0", "\t\t\tNoSwap.HiKickCool--", "\t\tend if",
        "\tend if", "end if",
        "if NoSwap.HiKick == 0", "\tif game.callbackParam3 == 1 // a Y press, from the DLL", "\t\tif TempValue0 == true",
        "\t\t\tTempValue1 = true", "\t\t\tif Player.Gravity == GRAVITY_GROUND", "\t\t\t\tif NoSwap.HiKickCool > 0",
        "\t\t\t\t\tTempValue1 = false", "\t\t\t\tend if", "\t\t\telse", "\t\t\t\tif NoSwap.HiKickUsed == true",
        "\t\t\t\t\tTempValue1 = false", "\t\t\t\tend if", "\t\t\tend if",
        "\t\t\tif TempValue1 == true", "\t\t\t\tNoSwap.HiKick = 1", "\t\t\t\tNoSwap.HiKickUsed = true", "\t\t\tend if",
        "\t\tend if", "\tend if", "end if",
        "if NoSwap.HiKick > 0",
        f"\tif NoSwap.HiKick >= {k} // launched: landing ends it too", "\t\tif Player.Gravity == GRAVITY_GROUND",
        "\t\t\tTempValue0 = false", "\t\tend if", "\tend if",
        "\tif TempValue0 == false // hurt, rolling, an object took over, landed: over",
        "\t\tif Player.Animation != ANI_HURT", "\t\t\tif Player.Gravity == GRAVITY_AIR",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING", "\t\t\telse", "\t\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\t\tend if", "\t\tend if",
        "\t\tNoSwap.HiKick = 0", f"\t\tNoSwap.HiKickCool = {c['high_kick_cooldown']}", "\tend if",
        "end if",
        "if NoSwap.HiKick > 0",
        f"\tif NoSwap.HiKick < {k} // the wind-up: held still",
        "\t\tPlayer.Speed = 0", "\t\tPlayer.XVelocity = 0", "\t\tif Player.Gravity == GRAVITY_AIR",
        "\t\t\tPlayer.YVelocity = 0", "\t\tend if",
        "\t\tPlayer.Animation = ANI_NOSWAP_HOVER", "\t\tPlayer.Frame = 0", "\t\tNoSwap.HiKick++",
        f"\t\tif NoSwap.HiKick > {c['high_kick_windup']} // launch, straight up",
        "\t\t\tif Player.Gravity == GRAVITY_GROUND", "\t\t\t\tPlayer.Gravity = GRAVITY_AIR",
        "\t\t\t\tPlayer.State = Player_State_Air", "\t\t\t\tPlayer.Angle = 0", "\t\t\t\tPlayer.CollisionMode = CMODE_FLOOR",
        "\t\t\tend if",
        f"\t\t\tPlayer.YVelocity = -{c['high_kick_rise']:#x}",
        "\t\t\tPlayer.Timer = 0 // (as after a spring: letting go of jump doesn't cut it short)",
        f"\t\t\tPlaySfx({c['high_kick_sfx_cd']}, false)", f"\t\t\tNoSwap.HiKick = {k}",
        "\t\tend if",
        "\telse",
        f"\t\tif NoSwap.HiKick < {r} // the kick, rising",
        "\t\t\tPlayer.Speed = 0", "\t\t\tPlayer.XVelocity = 0",
        "\t\t\tTempValue1 = NoSwap.HiKick // its frame, by its own clock", f"\t\t\tTempValue1 -= {k}",
        f"\t\t\tTempValue1 /= {c['high_kick_ticks']}", f"\t\t\tTempValue1 %= {n}",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT", "\t\t\tPlayer.Frame = TempValue1", "\t\t\tNoSwap.HiKick++",
        f"\t\t\tif Player.YVelocity >= 0 // the top: the recovery", f"\t\t\t\tNoSwap.HiKick = {r}", "\t\t\tend if",
        "\t\tend if",
        f"\t\tif NoSwap.HiKick >= {r} // the recovery",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_HOVER", "\t\t\tPlayer.Frame = 1", "\t\t\tNoSwap.HiKick++",
        f"\t\t\tif NoSwap.HiKick > {r + c['high_kick_recover']} // then she falls as from a jump",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING", "\t\t\t\tPlayer.Frame = 0", "\t\t\t\tNoSwap.HiKick = 0",
        f"\t\t\t\tNoSwap.HiKickCool = {c['high_kick_cooldown']}", "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "\tPlayer.PrevAnimation = Player.Animation // (the frame is picked here)", "\tPlayer.AnimationTimer = 0",
        "end if",
    ] + Y_REARM


def y_hold_lines():
    """NoSwap.YHeld: Y_HOLD_FRAMES while the DLL says Y is down (1: pressed, 2: held), counting down after."""
    return ["if game.callbackParam3 == 1 // Y down, from the DLL (Y_REARM_HOLD)", f"\tNoSwap.YHeld = {Y_HOLD_FRAMES}",
            "end if", "if game.callbackParam3 == 2", f"\tNoSwap.YHeld = {Y_HOLD_FRAMES}", "else",
            "\tif game.callbackParam3 != 1", "\t\tif NoSwap.YHeld > 0", "\t\t\tNoSwap.YHeld--", "\t\tend if", "\tend if",
            "end if"]


def cd_charge_lines(i):
    """A charge shot in CD (abilities.charge_trigger's): NoSwap.YHeld from the DLL (Y_REARM_HOLD, y_hold_lines);
    NoSwap.BusterCharge counts the frames Y is held; letting go of a full charge throws the second shot (its throw
    lines with that as their trigger, whatever the cooldown; its pose the first shot's, shown by the first's lines);
    letting go sooner or a hit ends the charge."""
    s = cd_shot2(i)
    lines = shots_v3.after_lines(s, ab.shot_pose_frame(i, "SonicCDu", 46, "melee_reach"), [], which=2, two=True,
                                 down2=False)
    trigger = ["if game.callbackParam3 == 1 // Y, from the DLL", "\tTempValue0 = false"]
    cool = ["\tif NoSwap.ShotCooldown > 0", "\t\tTempValue0 = false", "\tend if"]
    at = [k for k in range(len(lines)) if lines[k:k + 2] == trigger]
    ct = [k for k in range(len(lines)) if lines[k:k + 3] == cool]
    if len(at) != 1 or len(ct) != 1 or any("TempValue7" in l for l in lines):
        sys.exit(f"shot2: extra {i}: the CD charge shot's trigger isn't the throw's code it replaces")
    del lines[ct[0]:ct[0] + 3]
    lines[at[0]] = "if TempValue7 == true // (a full charge let go of)"
    show = [k for k, l in enumerate(lines) if l.startswith("if NoSwap.ShotPose > 0")]
    if show:  # (the first shot's lines show the pose)
        lines = lines[:show[0]]
    return y_hold_lines() + [
        "TempValue7 = false // Charge Shot (build_soniccd.cd_charge_lines): Y held charges; let go of a full charge, it fires",
        "if NoSwap.YHeld > 0", "\tif NoSwap.BusterCharge < 0x7FFF", "\t\tNoSwap.BusterCharge++", "\tend if",
        *(["\tif NoSwap.ShotCooldown > 0 // (\"charge_wait\": not full until the cooldown is over)",
           f"\t\tif NoSwap.BusterCharge >= {s['charge_full']}", f"\t\t\tNoSwap.BusterCharge = {s['charge_full'] - 1}",
           "\t\tend if", "\tend if"] if s.get("charge_wait") else []),
        "else", f"\tif NoSwap.BusterCharge >= {s['charge_full']}", "\t\tTempValue7 = true", "\tend if",
        "\tNoSwap.BusterCharge = 0", "end if",
        "if Player.Animation == ANI_HURT", "\tNoSwap.BusterCharge = 0", "\tTempValue7 = false", "end if"] + lines


# The charge flash's colours in OWN_ACT, past the player's own slots: block k (charge1, charge2a, charge2b) at
# CHARGE_ACT + k * 32, the extra's own slots from its first with the phase's colours (package_palettes)
CHARGE_ACT = 160
# The Shine Spark's glow (abilities.py charge "spark_*"): SPARK_ACT + k * SPARK_STRIDE, its greys (spark_glow_slots) in
# amount k's colours (abilities.spark_glow_colours; package_palettes, cd_spark_glow). Its own blocks, as an extra with a
# charge shot has CHARGE_ACT's (checked: not both)
SPARK_ACT, SPARK_STRIDE = 160, 8


def cd_charge_flash(t):
    """A charge shot's flash in CD (abilities.charge_flash_draw's phases; a runtime palette effect): CD's scripts can't set
    one colour, so the phase's colours are loaded from OWN_ACT (its blocks at CHARGE_ACT, package_palettes) over his
    own slots in bank 0 right before DrawPlayerAnimation, and his own loaded back right after (only for his drawing;
    the underwater bank keeps his own)."""
    ids = [i for i in ab.charge_shots() if next(e for e in EXTRAS if e["id"] == i) in OWN_EXTRAS]
    if not ids:
        return t
    before, after = [], []
    for i in ids:
        e = next(x for x in EXTRAS if x["id"] == i)
        s = cd_shot2(i)
        lo, hi = min(e["palette"]), max(e["palette"]) + 1
        before += per_extra_id("\t", i, [
            "TempValue0 = -1 // [NoSwap] the Charge Shot's flash (build_soniccd.cd_charge_flash): the phase",
            f"if NoSwap.BusterCharge >= {s['charge_start']}", f"\tif NoSwap.BusterCharge < {s['charge_full']}",
            "\t\tTempValue1 = NoSwap.BusterCharge", "\t\tTempValue1 >>= 2", "\t\tTempValue1 &= 1",
            "\t\tif TempValue1 == 1", "\t\t\tTempValue0 = 0", "\t\tend if", "\telse",
            "\t\tTempValue1 = NoSwap.BusterCharge", "\t\tTempValue1 >>= 1", "\t\tTempValue1 %= 3",
            "\t\tif TempValue1 < 2", "\t\t\tTempValue0 = TempValue1", "\t\t\tTempValue0++", "\t\tend if", "\tend if",
            "end if"] + [x for k in range(3) for x in (
                f"if TempValue0 == {k}",
                f'\tLoadPalette("{OWN_ACT}", 0, {lo}, {CHARGE_ACT + 32 * k}, {CHARGE_ACT + 32 * k + hi - lo})', "end if")])
        after += per_extra_id("\t", i, [
            f"if NoSwap.BusterCharge >= {s['charge_start']} // his own colours back",
            f'\tLoadPalette("{OWN_ACT}", 0, {lo}, {lo}, {hi})', "end if"])
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("charge flash: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n", "".join(before) + "\tDrawPlayerAnimation()\n" + "".join(after))
    return t[:start] + draw + t[end:]


def cd_charge_frames(i):
    """The charge's running frames in CD (ANI_NOSWAP_ATTACK, 45; as many past its top speed in 46, its coast in 47)."""
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = extras.player_ani(e, "SonicCDu")["anims"]
    n = len(anims[45]["frames"]) if len(anims) > 47 else 0
    if not n or len(anims[46]["frames"]) != n or not anims[47]["frames"]:
        sys.exit(f"charge: extra {i} needs its CD running frames in 45, as many in 46 and its coast in 47 (cd_config)")
    return n


def charge_after(i):
    """Heavy's Charge in CD (abilities.charge_after): Y held on the ground in the plain ground state pushes him the way he
    faced, harder the faster he goes; let go, he coasts down to his top speed. CD's ground movement never clips the speed,
    so his top speed stays as it is. An attack throughout (cd_touch_attacks)."""
    c = cfg(i)
    n = cd_charge_frames(i)
    if ab.has(i, "fire_immune"):
        sys.exit(f"extra {i}: charge's juggernaut mark and fire_immune share Object[5].PropertyValue in Sonic CD")
    base = CD_BREAKS_WALLS if ab.has(i, "breaks_walls") else 0  # (its startup's mark, cd_break_walls)
    # (NoSwap.YHeld below 0: braked to a full stop, Y not let go since; a press, or Y_HOLD_FRAMES without it, clears it)
    hold = ["if NoSwap.YHeld < 0 // braked to a stop: no new charge till Y is let go and pressed again",
            "\tif game.callbackParam3 == 1", f"\t\tNoSwap.YHeld = {Y_HOLD_FRAMES}", "\telse",
            "\t\tif game.callbackParam3 == 2", f"\t\t\tNoSwap.YHeld = -{Y_HOLD_FRAMES}", "\t\telse",
            "\t\t\tNoSwap.YHeld++", "\t\tend if", "\tend if", "else"] + ["\t" + x for x in y_hold_lines()] + ["end if"]
    return hold + [
        f"Object[5].PropertyValue = {base} // (not past his top speed: CD_JUGGERNAUT's mark off, cd_juggernaut)",
        "TempValue0 = false // Charge (build_soniccd.charge_after): on the ground, in the plain ground state",
        "if Player.Gravity == GRAVITY_GROUND", "\tif Player.State == Player_State_Ground",
        "\t\tif Player.Animation != ANI_HURT", "\t\t\tTempValue0 = true", "\t\tend if", "\tend if", "end if",
    ] + (["if NoSwap.Spark > 0 // (a Shine Spark stored or flying: no charge meanwhile)", "\tTempValue0 = false", "end if"]
         if i in ab.sparks() else []) + [
        "if TempValue0 == false",
        "\tNoSwap.Charge = 0 // off the ground (a jump keeps his speed), rolling, hurt: over",
        "else",
        "\tTempValue1 = false // pushing", "\tif NoSwap.YHeld > 0", "\t\tTempValue1 = true", "\tend if",
        "\tif NoSwap.Charge == 0", "\t\tif TempValue1 == true // it starts: the way he faces, from his speed that way, with a shove (charge_shove)",
        "\t\t\tTempValue2 = Player.Speed", "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue2)",
        "\t\t\tend if", f"\t\t\tif TempValue2 < {c['charge_shove']:#x}", f"\t\t\t\tTempValue2 = {c['charge_shove']:#x}",
        "\t\t\tend if",
        "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue2)", "\t\t\tend if",
        "\t\t\tNoSwap.Charge = TempValue2",
        "\t\t\tPlayer.Speed = TempValue2 // (the shove moves him now: from a standstill, the wall check saw 0 and ended it)",
        "\t\tend if", "\tend if",
        "\tif NoSwap.Charge != 0",
        "\t\tTempValue2 = NoSwap.Charge // its speed (TempValue3: its direction, 1 right / -1 left)",
        "\t\tTempValue3 = 1", "\t\tif TempValue2 < 0", "\t\t\tFlipSign(TempValue2)", "\t\t\tTempValue3 = -1", "\t\tend if",
        "\t\tTempValue4 = Player.Speed // his speed along it now: under half of last frame's, a wall stopped him",
        "\t\tTempValue4 *= TempValue3", "\t\tTempValue4 <<= 1",
        "\t\tif TempValue2 >= 0x20000", "\t\t\tif TempValue4 < TempValue2", "\t\t\t\tTempValue2 = 0", "\t\t\tend if",
        "\t\tend if",
        f"\t\tTempValue5 = 0 // holding back brakes (Y held or not): charge_brake a frame, down to a full stop, which ends it",
        "\t\tif TempValue3 > 0", "\t\t\tif Player.Left == true", f"\t\t\t\tTempValue5 = {c['charge_brake']:#x}",
        "\t\t\tend if", "\t\telse", "\t\t\tif Player.Right == true", f"\t\t\t\tTempValue5 = {c['charge_brake']:#x}",
        "\t\t\tend if", "\t\tend if",
        "\t\tif TempValue2 > 0",
        "\t\t\tif TempValue5 > 0", "\t\t\t\tTempValue1 = false // (the slide's pose)", "\t\t\t\tTempValue2 -= TempValue5",
        "\t\t\t\tif TempValue2 <= 0 // stopped: never past zero into reverse", "\t\t\t\t\tTempValue2 = -1",
        "\t\t\t\tend if", "\t\t\telse",
        "\t\t\tif TempValue1 == true // pushing: harder the faster he goes",
        "\t\t\t\tTempValue5 = TempValue2", f"\t\t\t\tTempValue5 *= {c['charge_gain']}", "\t\t\t\tTempValue5 >>= 10",
        f"\t\t\t\tTempValue5 += {c['charge_accel']:#x}", "\t\t\t\tTempValue2 += TempValue5",
        f"\t\t\t\tif TempValue2 > {c['charge_top']:#x}", f"\t\t\t\t\tTempValue2 = {c['charge_top']:#x}", "\t\t\t\tend if",
        "\t\t\telse // coasting: hard to stop",
        f"\t\t\t\tTempValue2 -= {c['charge_friction']:#x}",
        "\t\t\t\tif TempValue2 <= Player.TopSpeed // back to his own top speed: the game's again",
        "\t\t\t\t\tTempValue2 = 0", "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tif TempValue2 == -1 // braked to a full stop: over, standing (Y must be let go and pressed again)",
        "\t\t\tPlayer.Speed = 0", "\t\t\tPlayer.XVelocity = 0", "\t\t\tPlayer.Animation = ANI_STOPPED",
        "\t\t\tPlayer.Frame = 0", f"\t\t\tNoSwap.YHeld = -{Y_HOLD_FRAMES}", "\t\t\tTempValue2 = 0",
        "\t\tend if",
        "\t\tif TempValue2 == 0", "\t\t\tNoSwap.Charge = 0", "\t\telse",
        "\t\t\tTempValue6 = TempValue2 // (its speed)",
        "\t\t\tif TempValue6 > Player.TopSpeed // past his top speed: enemies can't hurt him (cd_juggernaut)",
        f"\t\t\t\tObject[5].PropertyValue = {base + CD_JUGGERNAUT}", "\t\t\tend if",
        "\t\t\tTempValue2 *= TempValue3", "\t\t\tNoSwap.Charge = TempValue2", "\t\t\tPlayer.Speed = TempValue2",
        "\t\t\tif TempValue3 > 0", "\t\t\t\tPlayer.Direction = FACING_RIGHT", "\t\t\telse",
        "\t\t\t\tPlayer.Direction = FACING_LEFT", "\t\t\tend if",
        "\t\t\tif TempValue1 == true",
        "\t\t\t\tPlayer.Animation = ANI_NOSWAP_ATTACK // running",
        "\t\t\t\tif TempValue6 > Player.TopSpeed", "\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT // past his top speed: "
        "the dash flash", "\t\t\t\tend if",
        f"\t\t\t\tTempValue5 = Player.XPos // one frame per {c['charge_stride']} px he covers (forward, either way)",
        "\t\t\t\tTempValue5 >>= 16", f"\t\t\t\tTempValue5 /= {c['charge_stride']}", f"\t\t\t\tTempValue5 %= {n}",
        "\t\t\t\tif TempValue3 < 0", "\t\t\t\t\tFlipSign(TempValue5)", f"\t\t\t\t\tTempValue5 += {n - 1}",
        "\t\t\t\tend if", "\t\t\t\tPlayer.Frame = TempValue5",
        "\t\t\telse", "\t\t\t\tPlayer.Animation = ANI_NOSWAP_HOVER // coasting: the slide", "\t\t\t\tPlayer.Frame = 0",
        "\t\t\tend if",
        "\t\t\tPlayer.PrevAnimation = Player.Animation // (the frame is picked here)", "\t\t\tPlayer.AnimationTimer = 0",
        "\t\tend if",
        "\tend if",
        "end if",
    ] + Y_REARM_HOLD


SPARK_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
                "Player_State_Roll", "Player_State_LookUp", "Player_State_Crouch", "Player_State_Spindash_S2",
                "Player_State_Spindash_CD", "Player_State_Peelout_S2", "Player_State_Peelout_CD"]  # (a launch from these)


def spark_kind_lines(ind=""):
    """TempValue0: the flying Shine Spark's kind (1 up, 2 up-forward, 3 forward); TempValue1 its way (1 / -1)."""
    return [f"{ind}TempValue0 = NoSwap.Spark", f"{ind}TempValue0 -= {ab.SPARK_ACTIVE}", f"{ind}TempValue1 = 1",
            f"{ind}if TempValue0 > 100", f"{ind}\tTempValue0 -= 100", f"{ind}\tTempValue1 = -1", f"{ind}end if"]


def spark_air_cd(i):
    """The Shine Spark's flight in CD (abilities.spark_air), in NoSwap_AirAbilities: before the air state runs, so its
    air control is kept out (left / right cleared after they're read), the jump's cap too (Player.Timer 0), and its
    gravity and drag are taken off in advance (extreme_gear_air's way): he moves at the flight's velocity. Only while
    its pose shows (a spring or a hit that took over is left alone: spark_after_cd ends it)."""
    return [f"if NoSwap.Spark > {ab.SPARK_ACTIVE} // Shine Spark (build_soniccd.spark_air_cd): its flight",
            "\tTempValue2 = false", "\tCheckEqual(Player.Animation, ANI_NOSWAP_SPARK)", "\tTempValue2 |= CheckResult",
            "\tCheckEqual(Player.Animation, ANI_NOSWAP_SHOT)", "\tTempValue2 |= CheckResult",
            "\tif TempValue2 == true"] + spark_kind_lines("\t\t") \
        + ab.spark_velocity(i, "TempValue0", "TempValue1", "TempValue2", "TempValue3", "\t\t") + [
            "\t\tPlayer.Left = false // no air control", "\t\tPlayer.Right = false", "\t\tPlayer.Timer = 0 // (no jump cap)",
            "\t\tTempValue3 -= Player.GravityStrength // (the air state adds it back)",
            "\t\tif TempValue3 > -0x40000 // the air state's drag, rising slowly: 1/32 of the speed (added in advance)",
            "\t\t\tif TempValue3 < 0", "\t\t\t\tTempValue4 = TempValue2", "\t\t\t\tTempValue4 >>= 5",
            "\t\t\t\tTempValue2 += TempValue4", "\t\t\tend if", "\t\tend if",
            "\t\tPlayer.Speed = TempValue2", "\t\tPlayer.XVelocity = TempValue2", "\t\tPlayer.YVelocity = TempValue3",
            "\tend if", "end if"]


def spark_after_cd(i):
    """The charge's Shine Spark in CD (abilities.spark_after's rules), after the player has moved and after charge_after
    (which has set Object[5].PropertyValue's juggernaut mark for this frame). NoSwap.Spark as S1/S2's NoSwap_spark.
    Flying he's a touch attack (touch_attack_lines) and enemies can't hurt him (the CD_JUGGERNAUT mark)."""
    c = cfg(i)
    s, d, stride = c["spark_speed"], ab.spark_diag(i), c["charge_stride"]
    n = cd_charge_frames(i)
    base = CD_BREAKS_WALLS if ab.has(i, "breaks_walls") else 0
    states = [x for st in SPARK_STATES for x in (f"\t\t\t\tCheckEqual(Player.State, {st})", "\t\t\t\tTempValue0 |= CheckResult")]
    return [f"if NoSwap.Spark > {ab.SPARK_ACTIVE} // Shine Spark (build_soniccd.spark_after_cd): flying"] \
        + spark_kind_lines("\t") + [
        "\tTempValue2 = true // still flying?", "\tTempValue3 = false // the terrain stopped it?",
        "\tTempValue4 = false", "\tCheckEqual(Player.Animation, ANI_NOSWAP_SPARK)", "\tTempValue4 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_NOSWAP_SHOT)", "\tTempValue4 |= CheckResult",
        "\tCheckEqual(Player.State, Player_State_Air)", "\tTempValue5 = CheckResult",
        "\tCheckEqual(Player.State, Player_State_Ground)", "\tTempValue5 |= CheckResult", "\tTempValue4 &= TempValue5",
        "\tif TempValue4 == false // a spring, a hit, an object took over", "\t\tTempValue2 = false",
        "\telse",
        "\t\tTempValue4 = Player.XVelocity // his speed along the flight",
        "\t\tif Player.Gravity == GRAVITY_GROUND", "\t\t\tTempValue4 = Player.Speed", "\t\tend if",
        "\t\tTempValue4 *= TempValue1",
        "\t\tif Player.Gravity == GRAVITY_GROUND",
        "\t\t\tif TempValue0 == 3 // forward, running along the ground: a wall stops it",
        f"\t\t\t\tif TempValue4 < {s // 2:#x}", "\t\t\t\t\tTempValue3 = true", "\t\t\t\tend if",
        "\t\t\telse", "\t\t\t\tTempValue3 = true // landed (or on a ceiling)", "\t\t\tend if",
        "\t\telse",
        "\t\t\tif TempValue0 != 3 // up or up-forward: the stage's top edge is his ceiling (S3&K's engine stops him there;",
        "\t\t\t\t// CD lets him rise past it into the sky for good, the user, 2026-09-30)",
        "\t\t\t\tTempValue6 = Stage.YBoundary1", "\t\t\t\tTempValue6 += 16", "\t\t\t\tTempValue6 <<= 16",
        "\t\t\t\tif Player.YPos < TempValue6", "\t\t\t\t\tTempValue3 = true", "\t\t\t\tend if", "\t\t\tend if",
        "\t\t\tif TempValue0 == 1 // up: a ceiling", f"\t\t\t\tif Player.YVelocity > -{s // 2:#x}",
        "\t\t\t\t\tTempValue3 = true", "\t\t\t\tend if", "\t\t\tend if",
        "\t\t\tif TempValue0 == 2 // up-forward: a ceiling or a wall", f"\t\t\t\tif Player.YVelocity > -{d // 2:#x}",
        "\t\t\t\t\tTempValue3 = true", "\t\t\t\tend if", f"\t\t\t\tif TempValue4 < {d // 2:#x}", "\t\t\t\t\tTempValue3 = true",
        "\t\t\t\tend if", "\t\t\tend if",
        "\t\t\tif TempValue0 == 3 // forward: a wall", f"\t\t\t\tif TempValue4 < {s // 2:#x}", "\t\t\t\t\tTempValue3 = true",
        "\t\t\t\tend if", "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "\tif TempValue3 == true // the terrain stopped him: he drops from there", "\t\tTempValue2 = false",
        "\t\tif Player.Gravity == GRAVITY_AIR", "\t\t\tPlayer.XVelocity = 0", "\t\t\tif Player.YVelocity < 0",
        "\t\t\t\tPlayer.YVelocity = 0", "\t\t\tend if", "\t\tend if", "\t\tPlayer.Speed = 0",
        "\t\tPlayer.Animation = ANI_WALKING", "\tend if",
        "\tif TempValue2 == false", "\t\tNoSwap.Spark = 0",
        "\telse",
        f"\t\tObject[5].PropertyValue = {base + CD_JUGGERNAUT} // enemies can't hurt him (cd_juggernaut)",
        "\t\tPlayer.Direction = FACING_RIGHT", "\t\tif TempValue1 < 0", "\t\t\tPlayer.Direction = FACING_LEFT", "\t\tend if",
        f"\t\tif TempValue0 == 3 // forward: the charge's dash frames, one per {stride} px",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT", "\t\t\tTempValue6 = Player.XPos", "\t\t\tTempValue6 >>= 16",
        f"\t\t\tTempValue6 /= {stride}", f"\t\t\tTempValue6 %= {n}", "\t\t\tif TempValue1 < 0", "\t\t\t\tFlipSign(TempValue6)",
        f"\t\t\t\tTempValue6 += {n - 1}", "\t\t\tend if", "\t\t\tPlayer.Frame = TempValue6",
        "\t\t\tif Player.Gravity == GRAVITY_GROUND // along the ground: its speed", f"\t\t\t\tPlayer.Speed = {s:#x}",
        "\t\t\t\tPlayer.Speed *= TempValue1", "\t\t\tend if",
        "\t\telse", "\t\t\tPlayer.Animation = ANI_NOSWAP_SPARK // up, up-forward: fists up", "\t\t\tPlayer.Frame = 0",
        "\t\tend if",
        "\t\tPlayer.PrevAnimation = Player.Animation", "\t\tPlayer.AnimationTimer = 0",
        "\tend if",
        "end if",
        "if NoSwap.Spark > 0",
        f"\tif NoSwap.Spark <= {c['spark_store']} // stored: glowing", "\t\tNoSwap.Spark--",
        "\t\tif Player.Animation == ANI_HURT // a hit: it's gone", "\t\t\tNoSwap.Spark = 0", "\t\tend if",
        f"\t\tif NoSwap.Spark > {c['spark_store'] - c['spark_skid_frames']} // just stored: he skids to a stop",
        "\t\t\tif Player.Gravity == GRAVITY_GROUND", "\t\t\t\tif Player.State == Player_State_Ground",
        "\t\t\t\t\tif Player.Speed != 0", "\t\t\t\t\t\tTempValue0 = Player.Speed", "\t\t\t\t\t\tif TempValue0 < 0",
        "\t\t\t\t\t\t\tFlipSign(TempValue0)", "\t\t\t\t\t\tend if", f"\t\t\t\t\t\tTempValue0 -= {c['spark_skid']:#x}",
        "\t\t\t\t\t\tif TempValue0 < 0", "\t\t\t\t\t\t\tTempValue0 = 0", "\t\t\t\t\t\tend if",
        "\t\t\t\t\t\tif Player.Speed < 0", "\t\t\t\t\t\t\tFlipSign(TempValue0)", "\t\t\t\t\t\tend if",
        "\t\t\t\t\t\tPlayer.Speed = TempValue0", "\t\t\t\t\t\tPlayer.Animation = ANI_SKIDDING", "\t\t\t\t\tend if",
        "\t\t\t\tend if", "\t\t\tend if", "\t\tend if",
        "\t\tif NoSwap.Spark > 0", "\t\t\tif Player.JumpPress == true // launch: the way the d-pad says",
        "\t\t\t\tTempValue0 = false"] + states + [
        "\t\t\t\tif Player.Animation == ANI_HURT", "\t\t\t\t\tTempValue0 = false", "\t\t\t\tend if",
        "\t\t\t\tif TempValue0 == true",
        "\t\t\t\t\tTempValue0 = 1 // straight up", "\t\t\t\t\tTempValue1 = 1",
        "\t\t\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\t\t\tTempValue1 = -1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif Player.Left == true", "\t\t\t\t\t\tTempValue0 = 3", "\t\t\t\t\t\tTempValue1 = -1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif Player.Right == true", "\t\t\t\t\t\tTempValue0 = 3", "\t\t\t\t\t\tTempValue1 = 1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif TempValue0 == 3", "\t\t\t\t\t\tif Player.Up == true", "\t\t\t\t\t\t\tTempValue0 = 2 // up-forward",
        "\t\t\t\t\t\tend if", "\t\t\t\t\tend if",
        "\t\t\t\t\tNoSwap.Spark = TempValue0", f"\t\t\t\t\tNoSwap.Spark += {ab.SPARK_ACTIVE}",
        "\t\t\t\t\tPlayer.Direction = FACING_RIGHT", "\t\t\t\t\tif TempValue1 < 0", "\t\t\t\t\t\tNoSwap.Spark += 100",
        "\t\t\t\t\t\tPlayer.Direction = FACING_LEFT", "\t\t\t\t\tend if",
        "\t\t\t\t\tPlayer.State = Player_State_Air // into the air, gravity off (spark_air_cd)",
        "\t\t\t\t\tPlayer.Gravity = GRAVITY_AIR", "\t\t\t\t\tPlayer.Angle = 0", "\t\t\t\t\tPlayer.CollisionMode = CMODE_FLOOR",
        ] + ab.spark_velocity(i, "TempValue0", "TempValue1", "Player.XVelocity", "Player.YVelocity", "\t\t\t\t\t") + [
        "\t\t\t\t\tPlayer.Speed = Player.XVelocity",
        "\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_SPARK", "\t\t\t\t\tif TempValue0 == 3", "\t\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_SHOT",
        "\t\t\t\t\tend if", "\t\t\t\t\tPlayer.PrevAnimation = Player.Animation", "\t\t\t\t\tPlayer.Frame = 0",
        "\t\t\t\t\tPlayer.AnimationTimer = 0",
        f"\t\t\t\t\tObject[5].PropertyValue = {base + CD_JUGGERNAUT}",
        f"\t\t\t\t\tPlaySfx({c['spark_sfx_cd']}, false)",
        "\t\t\t\tend if", "\t\t\tend if", "\t\tend if",
        "\tend if",
        "end if",
        f"if Object[5].PropertyValue >= {CD_JUGGERNAUT} // storing: down at full charge, on the ground",
        "\tif NoSwap.Charge != 0", "\t\tif Player.Down == true", "\t\t\tif Player.Gravity == GRAVITY_GROUND",
        "\t\t\t\tif NoSwap.Spark == 0", "\t\t\t\t\tNoSwap.Charge = 0", f"\t\t\t\t\tNoSwap.Spark = {c['spark_store']}",
        "\t\t\t\t\tPlayer.Animation = ANI_SKIDDING", f"\t\t\t\t\tPlaySfx({c['spark_store_sfx_cd']}, false)",
        "\t\t\t\tend if", "\t\t\tend if", "\t\tend if", "\tend if", "end if",
    ]


def cd_spark_glow(t):
    """The Shine Spark's glow in CD (abilities.spark_glow_draw's; a runtime palette effect), cd_charge_flash's way: the
    amount's colours (spark_glow_colours) are loaded from OWN_ACT (its blocks at SPARK_ACT, package_palettes) over his
    greys in bank 0 right before DrawPlayerAnimation, and his own loaded back right after."""
    ids = [i for i in ab.sparks() if next(e for e in EXTRAS if e["id"] == i) in OWN_EXTRAS]
    if not ids:
        return t
    before, after = [], []
    for i in ids:
        slots = ab.ABILITIES[i]["spark_glow_slots"]
        lo, hi = min(slots), max(slots) + 1
        before += per_extra_id("\t", i, ["// [NoSwap] the Shine Spark's glow (build_soniccd.cd_spark_glow)"]
                               + ab.spark_phase("TempValue0", ab.SPARK_ACTIVE, "NoSwap.Spark") + [x for k in range(3) for x in (
                                   f"if TempValue0 == {k}",
                                   f'\tLoadPalette("{OWN_ACT}", 0, {lo}, {SPARK_ACT + SPARK_STRIDE * k}, '
                                   f'{SPARK_ACT + SPARK_STRIDE * k + hi - lo})', "end if")])
        after += per_extra_id("\t", i, ["if NoSwap.Spark > 0 // his own colours back",
                                        f'\tLoadPalette("{OWN_ACT}", 0, {lo}, {lo}, {hi})', "end if"])
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("spark glow: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n", "".join(before) + "\tDrawPlayerAnimation()\n" + "".join(after))
    return t[:start] + draw + t[end:]


def touch_attack(i):
    """A move that makes everything the extra touches count as attacked (CD: badniks, monitors, bosses;
    cd_touch_attacks): its condition, or None. (A charge's Shine Spark, flying, too: touch_attack_lines.)"""
    if ab.has(i, "charge"):
        return "NoSwap.Charge != 0"
    if ab.has(i, "spin_attack"):
        return "NoSwap.Spin > 0"
    if ab.has(i, "no_stomp") and ab.has(i, "ground_slide"):  # (no_stomp: his Slide is an attack)
        return "NoSwap.Slide > 0"
    return None


def touch_attack_lines(check_var, comment):
    """Lines `check_var |= true` / `= true` while an extra's touch attack lasts (touch_attack), per extra."""
    out = []
    for e in EXTRAS:
        cond = touch_attack(e["id"]) if e["id"] in ab.ABILITIES else None
        if cond:
            spark = [f"\tif NoSwap.Spark > {ab.SPARK_ACTIVE} // (its Shine Spark, flying)", f"\t\t{check_var}",
                     "\tend if"] if e["id"] in ab.sparks() else []
            out += [f"if Stage.PlayerListPos == {e['alias']} // {comment}", f"\tif {cond}",
                    f"\t\t{check_var}", "\tend if"] + spark + ["end if"]
    return out


def cd_touch_attacks(t):
    """Badniks break at the touch of an extra whose touch attack lasts (Heavy's Charge): Player_BadnikBreak, which every
    badnik calls. (Monitors: NoSwap_SurgeMonitor; bosses: NoSwap_ShotAttack.) Only in a build with such an extra."""
    lines = touch_attack_lines("TempValue0 |= true", "[NoSwap] its move hits whatever it touches")
    if not lines:
        return t
    anchor = "\t// you're invincible to badniks during the warping run\n\tif Warp.Timer > 0\n\t\tTempValue0 |= true\n\tend if\n\n"
    return patch(t, anchor, anchor + "".join(f"\t{l}\n" for l in lines) + "\n", "touch attack badniks")


def cd_no_stomp(t):
    """abilities.py no_stomp (the user, 2026-10-02): Player_BadnikBreak (every badnik's) doesn't count the extra's jump
    as an attack: in the air in ANI_JUMPING (his jump pose; his moves have their own attack animations, 45 / 46), the
    badnik hurts him as walking into it does. Checked before the invincibility monitor's test and a shot's, which still
    count (Sonic CD has no Super). Bosses and monitors keep their own tests (they still take the jump). His Slide's
    attack is touch_attack's. Only in a build with such an extra."""
    ids = [i for i in ab.with_ability("no_stomp") if any(e["id"] == i for e in OWN_EXTRAS)]
    if not ids:
        return t
    head = "\nfunction Player_BadnikBreak\n"
    if t.count(head) != 1:
        sys.exit("no_stomp: CD's Player_BadnikBreak isn't there once")
    start = t.index(head)
    anchor = "\tCheckEqual(Player.Animation, ANI_GLIDING_STOP)\n\tTempValue0 |= CheckResult\n#endplatform\n"
    at = t.find(anchor, start)
    if at < 0 or at > t.index("\nend function", start):
        sys.exit("no_stomp: CD's Player_BadnikBreak changed")
    add = "".join(f"\tif Stage.PlayerListPos == {e['alias']} // [NoSwap] abilities.py no_stomp: his jump isn't an attack\n"
                  "\t\tif Player.Gravity == GRAVITY_AIR\n\t\t\tif Player.Animation == ANI_JUMPING\n\t\t\t\tTempValue0 = false\n"
                  "\t\t\tend if\n\t\tend if\n\tend if\n" for e in OWN_EXTRAS if e["id"] in ids)
    at += len(anchor)
    return t[:at] + add + t[at:]


def cd_no_stomp_slide(i):
    """no_stomp with ground_slide in CD: while the Slide lasts, walls break as for Knuckles (Object[5].PropertyValue
    CD_BREAKS_WALLS, cd_break_walls' test; 0 again after it). Badniks, monitors and bosses: touch_attack."""
    return ["if NoSwap.Slide > 0 // no_stomp: the Slide breaks walls (cd_break_walls)",
            f"\tObject[5].PropertyValue = {CD_BREAKS_WALLS}", "else", "\tObject[5].PropertyValue = 0", "end if"]


RADIAL = 1000  # SHOT_OUT values above this reach all around the player (value - RADIAL px): Silver's sphere
SHOT_OUT = {7: None, 8: 56, 9: 72, 10: 60, 11: None, 12: RADIAL + 28, 17: 12, 19: 60, 21: 74}  # reach while the cork / lure is out (px from the player's centre)
SHOT_OUT[22] = 11  # Tikal's punch: her fist, 21 px out at full reach, is 11 past her own box (10 px each side)
# Mario's Fireball flies ahead of him: a reach per frame, the fireball's leading edge past his own box (10 px each side)
# (a player script build with only some extras' moves, NOSWAP_KEEP, has only theirs: build_player_object needs no reach)
SHOT_OUT[23] = [max(0, r - 10) for r in ab.ABILITIES[23]["melee_reach"]] if cd_melee(23) else None
# Gamma's Arm Cannon likewise: the beam's leading edge per frame (v3 can't make the box thin: enemies widen theirs
# sideways only, so the beam reaches as tall as his own box)
SHOT_OUT[26] = [max(0, r - 10) for r in ab.ABILITIES[26]["melee_reach"]] if cd_melee(26) else None  # (a real shot: none)
# Jet's Tornado: the whirlwind's leading edge on every frame, the first and last too (a dict: frame -> reach; his swing
# reaches past his box from the start, and the last frame is the whirlwind at full size)
SHOT_OUT[27] = ({k: max(0, r - 10) for k, r in enumerate(ab.ABILITIES[27]["melee_reach"])}
                if 27 in ab.ABILITIES and cd_melee(27) else None)  # (his Tornado Trap is a real shot now: none)
# Chaos' Stretch Punch: the fist's reach on every frame (a dict, as Jet's), past his own box; his wind-up (14 px) none
SHOT_OUT[30] = ({k: r - 10 if r >= 20 else 0 for k, r in enumerate(ab.ABILITIES[30]["melee_reach"])}
                if cd_melee(30) else None)
# Tails Doll's Screen Nuke: no reach past his own box (the nuke hits through its own object: abilities.py melee_nuke,
# nuke_spawn_cd)
SHOT_OUT[32] = None
# Bark's Bear Rush: no reach past his own box (melee_boost: his body attacks, as Mecha's Jet Boost)
SHOT_OUT[34] = None
# Bomb's Self-Destruct: no reach past his own box (since the user's rework, 2026-09-28, a half-screen nuke hits through
# its own object, as Tails Doll's: abilities.py melee_nuke, nuke_spawn_cd)
SHOT_OUT[36] = None
# Honey's Claw Swipe: her claws reach 18 px (the swipes) to 24 (the lunge's box): CD gets 12 past her box on the lunge
# frames, a reach the enemies' scripts already have (Espio's), so they don't change
SHOT_OUT[37] = {k: 12 if r > 20 else 0 for k, r in enumerate(ab.ABILITIES[37]["melee_reach"])} if cd_melee(37) else None
# John Morris' whip (looked up by his art folder): out on its extended frames, 53 px from his centre, 43 past his box: CD
# gets 48, a reach the enemies' scripts already have (Chaos'), so they don't change. CD has his standing / air whip only
# (no crouching or aimed poses: its one throw slot, 46)
_JOHN = next((e["id"] for e in EXTRAS if e["art"].name == "john-morris"), None)  # (None: the Creator Kit, no John)
if _JOHN is None and not ab.KIT:
    sys.exit("build_soniccd.py: no extra in testmods/john-morris")
if _JOHN is not None:
    SHOT_OUT[_JOHN] = ({k: 48 if r > 20 else 0 for k, r in enumerate(ab.ABILITIES[_JOHN]["melee_reach"])}
                       if cd_melee(_JOHN) else None)
# Gilius' axe chop (looked up by his art folder): the axe head 34 / 25 px out on the forward and down frames, 24 / 15
# past his box: CD gets 12 there, a reach the enemies' scripts already have (Espio's), so they don't change (before:
# none, his body only)
_GILIUS = next((e["id"] for e in EXTRAS if e["art"].name == "gilius"), None)
if _GILIUS is not None and cd_melee(_GILIUS):
    SHOT_OUT[_GILIUS] = {k: 12 if r - 10 >= 12 else 0 for k, r in enumerate(ab.ABILITIES[_GILIUS]["melee_reach"])}
# Robotnik's Rocket Ride: while its blast lasts, the same all-around reach (Reach isn't only for shots)
BLAST_OUT = {i: RADIAL + ab.ABILITIES[i]["blast_radius"] for i in ab.ABILITIES if ab.has(i, "rocket_ride")}


# melee_run / melee_up (abilities.py VARIANT_POSES: Axel's Grand Upper and Dragon Wing). CD has one melee animation (46),
# so their frames follow the plain melee's there (cd_config.py "cd_melee_variants"), and NoSwap.MeleePose (VARIANT_ALIAS)
# says which part shows: 0 the plain melee, 1 the running one, 2 up + Y. Their reach is CD's: the enemies' own box grows
# toward him (enemy_reach), by a reach the shared enemy scripts already have (VARIANT_REACHES: each frame's reach past his
# box rounded DOWN to one of them, all round him for a "radial" pose), so adding such a character changes no shared script
VARIANT_ALIAS = ("#alias Object[5].Value5 : NoSwap.MeleePose // [NoSwap] melee_run / melee_up: the melee's pose (0 plain, "
                 "1 running, 2 up + Y)\n")
VALUE5_MOVES = ("wall_cling", "ray_glide", "ear_grapple", "high_kick", "triple_jump", "puddle_slide", "rocket_burst",
                "charge", "spin_attack", "spirit_flight", "water_swim", "phase_warp", "thunder_zip")
# (the fixed ones: SHOT_OUT's plain numbers, in every build's enemy scripts; the ones computed from the other extras'
# moves exist only in a build that has those extras, and a character package is built with its own moves alone)
_REACHES = {v for v in SHOT_OUT.values() if isinstance(v, int) and not isinstance(v, bool)}
VARIANT_REACHES = sorted(r for r in _REACHES if r < RADIAL)  # (ahead of him)
VARIANT_RADIAL_REACHES = sorted(r - RADIAL for r in _REACHES if RADIAL < r < 2 * RADIAL)  # (all round him)


def cd_variants(i):
    """The extra's CD melee has melee_run / melee_up poses (abilities.check_variants' rules)."""
    c = ab.ABILITIES.get(i, {})
    if not (cd_melee(i) and any(c.get(k) for k in ab.VARIANT_POSES)):
        return False
    ab.check_variants(i)
    clash = [m for m in VALUE5_MOVES if ab.has(i, m)]
    if clash:
        sys.exit(f"melee_run / melee_up: extra {i}: NoSwap.MeleePose (Object[5].Value5) is {', '.join(clash)}'s too")
    return True


def cd_snap(reach, radial):
    """A pose frame's reach (px from his centre) as CD's: past his own box (10 px), rounded down to a reach the enemy
    scripts have (VARIANT_REACHES / VARIANT_RADIAL_REACHES: RADIAL + it); 0 for none."""
    have = VARIANT_RADIAL_REACHES if radial else VARIANT_REACHES
    r = max((v for v in have if v <= reach - 10), default=0)
    return RADIAL + r if radial and r else r


def cd_variant_layout(i):
    """[(reach list, {frame: CD reach})] for the poses in CD's order (plain, melee_run, melee_up: the frames' order in
    animation 46); a pose's frames start where the previous ones' end."""
    c = ab.ABILITIES[i]
    out = [(c["melee_reach"], {k: cd_snap(r, bool(c.get("melee_radial"))) for k, r in enumerate(c["melee_reach"])})]
    for k in ab.VARIANT_POSES:
        v = c.get(k)
        if v:
            out.append((v["reach"], {f: cd_snap(r, k == "melee_up" and bool(v.get("radial")))
                                     for f, r in enumerate(v["reach"])}))
    return [(r, {f: x for f, x in o.items() if x}) for r, o in out]


def cd_variant_start(i):
    """NoSwap_Shot<i>: the pose as the melee starts: on the ground, up held with melee_up's rings (taken; fewer: the
    plain melee) 2, else running (at least melee_run's speed either way) 1, else 0."""
    c = ab.ABILITIES[i]
    lines = ["NoSwap.MeleePose = 0 // melee_run / melee_up: the pose (build_soniccd.cd_variant_start)",
             "if Player.Gravity == GRAVITY_GROUND"]
    if c.get("melee_up"):
        rings = c["melee_up"].get("rings", 0)
        lines += ["\tif Player.Up == true",
                  f"\t\tif Player.Rings >= {rings} // (fewer rings: the plain melee)",
                  f"\t\t\tPlayer.Rings -= {rings}", "\t\t\tNoSwap.MeleePose = 2", "\t\tend if", "\tend if"]
    if c.get("melee_run"):
        lines += ["\tif NoSwap.MeleePose == 0", "\t\tTempValue1 = Player.Speed", "\t\tif TempValue1 < 0",
                  "\t\t\tFlipSign(TempValue1)", "\t\tend if", f"\t\tif TempValue1 >= {c['melee_run']['speed']:#x} // running",
                  "\t\t\tNoSwap.MeleePose = 1", "\t\tend if", "\tend if"]
    lines += ["end if"]
    return "".join("\n\t\t" + l for l in lines)


def cd_melee_sfx(i):
    """The melee's sound as it starts (NoSwap_Shot<i>): SFX_G_RELEASE, or melee_run / melee_up's own sound (tools/
    own_sounds.py) when that pose starts (NoSwap.MeleePose 1 / 2)."""
    import own_sounds
    lines = ["PlaySfx(SFX_G_RELEASE, false)"]
    for n, k in ((1, "melee_run"), (2, "melee_up")):
        own = own_sounds.variant_mark(i, ab.ABILITIES[i], k) if cd_variants(i) else ""
        if own:
            lines = [f"if NoSwap.MeleePose == {n} // ({k}'s own sound)", f"\tPlaySfx(SFX_G_RELEASE{own}, false)",
                     "else"] + ["\t" + l for l in lines] + ["end if"]
    return "\n\t\t".join(lines)


def cd_variant_lines(i, total):
    """The melee's frame, reach and the run's boost each frame, for an extra with melee_run / melee_up (in place of the
    plain melee's lines): its pose's frames (animation 46 from where that pose's start), ending when they run out."""
    c = ab.ABILITIES[i]
    ticks = c["melee_ticks"]
    poses = cd_variant_layout(i)
    which = [0] + [n for n, k in ((1, "melee_run"), (2, "melee_up")) if c.get(k)]
    out = ["\t\tPlayer.Animation = ANI_NOSWAP_SHOT",
           f"\t\tTempValue0 = {total}", "\t\tTempValue0 -= NoSwap.Shot", f"\t\tTempValue0 /= {ticks}",
           "\t\tNoSwap.Reach = 0", "\t\tTempValue1 = 0 // the pose's first frame in animation 46"]
    start = 0
    for n, (reach, cd) in zip(which, poses):
        frames = len(reach)
        out += [f"\t\tif NoSwap.MeleePose == {n}",
                f"\t\t\tif TempValue0 >= {frames} // its frames are all shown: the last one, and done",
                f"\t\t\t\tTempValue0 = {frames - 1}", "\t\t\t\tNoSwap.Shot = 1", "\t\t\tend if"]
        if cd:
            out += ["\t\t\tswitch TempValue0 // its reach, frame by frame"]
            out += [l for k, r in sorted(cd.items()) for l in (f"\t\t\tcase {k}", f"\t\t\t\tNoSwap.Reach = {r}",
                                                                 "\t\t\t\tbreak")]
            out += ["\t\t\tend switch"]
        if start:
            out += [f"\t\t\tTempValue1 = {start}"]
        if n == 1 and c["melee_run"].get("boost"):
            boost = c["melee_run"]["boost"]
            out += ["\t\t\tTempValue2 = Player.Speed // the run's boost (melee_run \"boost\"), the way he faces",
                    "\t\t\tif Player.Gravity == GRAVITY_AIR", "\t\t\t\tTempValue2 = Player.XVelocity", "\t\t\tend if",
                    "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue2)", "\t\t\tend if",
                    f"\t\t\tif TempValue2 < {boost:#x}", f"\t\t\t\tTempValue2 = {boost:#x}", "\t\t\tend if",
                    "\t\t\tif Player.Direction == FACING_LEFT", "\t\t\t\tFlipSign(TempValue2)", "\t\t\tend if",
                    "\t\t\tPlayer.Speed = TempValue2", "\t\t\tif Player.Gravity == GRAVITY_AIR",
                    "\t\t\t\tPlayer.XVelocity = TempValue2", "\t\t\tend if"]
        out += ["\t\tend if"]
        start += frames
    out += ["\t\tTempValue0 += TempValue1", "\t\tPlayer.Frame = TempValue0 // the timer picks the frame",
            "\t\tPlayer.AnimationTimer = 0"]
    return out
# (Max's Ear Grapple had a reach here, DIAG + x * 1000 + y: the enemies' box grew toward him by the ear's tip for the
# whole move. Since 2026-09-30 its tip is tested in NoSwap_ShotTouch instead: cd_ear_touch.)
DIAG = 100000
GRAPPLE_OUT = {}


def cfg(i):
    return ab.ABILITIES[i]


def swim_var(i):
    """water_swim's value: NoSwap.Swim (Object[5].Value5), or NoSwap.SwimB (Value6) for an extra whose Puddle Slide has
    Value5 (Chaos)."""
    if ab.has(i, "puddle_slide"):
        if any(ab.has(i, m) for m in VALUE6_MOVES) or ab.down_shot(i) or hold_moves(i):
            sys.exit(f"water_swim: extra {i}: NoSwap.SwimB (Object[5].Value6) is another of its moves'")
        return "NoSwap.SwimB"
    return "NoSwap.Swim"


def swim_air(i):
    """water_swim (abilities.py): underwater (Player.GravityStrength 0x1000, set by R4/Water), a jump press in mid-air in
    the jump or a stroke is a stroke: up at swim_stroke, at most one every swim_delay frames. It closes the jump ability
    for this jump (NoSwap.Ability 2: the umbrella's "closed"), and the stroke's animation isn't the jump's, so the press
    never reaches it. In NoSwap_AirAbilities, before the state runs."""
    c = cfg(i)
    var = swim_var(i)
    if ab.has(i, "ray_glide") or ab.has(i, "wall_cling") or (var == "NoSwap.Swim" and ab.has(i, "puddle_slide")) \
            or ab.has(i, "spin_attack") or ab.has(i, "high_kick") or ab.has(i, "thunder_zip") or ab.has(i, "power_surge"):
        sys.exit(f"water_swim: extra {i}: {var} / slot 48 are another of its moves'")
    return [(f"if {var} > 0"
            + " // water_swim: frames before the next stroke (build_soniccd.swim_air)"), f"\t{var}--", "end if",
            "if Player.GravityStrength == 0x1000 // underwater (R4/Water sets it)",
            "\tif Player.JumpPress == true",
            "\t\tTempValue0 = false",
            "\t\tif Player.Animation == ANI_JUMPING", "\t\t\tTempValue0 = true", "\t\tend if",
            "\t\tif Player.Animation == ANI_NOSWAP_SWIM", "\t\t\tTempValue0 = true", "\t\tend if",
            "\t\tif TempValue0 == true",
            "\t\t\tNoSwap.Ability = 2 // no parasol this jump",
            f"\t\t\tif {var} == 0 // a stroke",
            f"\t\t\t\t{var} = {c['swim_delay']}",
            f"\t\t\t\tif Player.YVelocity > -{c['swim_stroke']:#x}",
            f"\t\t\t\t\tPlayer.YVelocity = -{c['swim_stroke']:#x}",
            "\t\t\t\tend if",
            "\t\t\t\tPlayer.Timer = 0 // (as after a spring: letting go of jump doesn't cut it short)",
            "\t\t\t\tPlayer.Animation = ANI_NOSWAP_SWIM",
            "\t\t\t\tPlayer.Frame = 0",
            "\t\t\t\tPlayer.AnimationTimer = 0",
            "\t\t\tend if",
            "\t\tend if",
            "\tend if",
            "end if"]


def jump_ability_name(i):
    names = {"jet_dash": "JetDash", "rocket_ride": "RocketRide", "ear_grapple": "EarGrapple", "pogo": "Pogo", "umbrella": "Umbrella", "chaos_control": "ChaosControl",
             "hammer_drop": "HammerDrop", "ray_glide": "RayGlide",
             "aim_dash": "AimDash", "spirit_flight": "SpiritFlight", "double_jump": "DoubleJump",
             "thunder_zip": "ThunderZip", "extreme_gear": "ExtremeGear", "screw_kick": "ScrewKick",
             "puddle_slide": "PuddleSlide", "phase_warp": "PhaseWarp", "rocket_burst": "RocketBurst"}
    base = next(e["base"] for e in EXTRAS if e["id"] == i)
    own = {"tails": "Player_Action_DblJumpTails", "knuckles": "Player_Action_DblJumpKnux"}.get(base, "Player_State_Static")
    if i not in ab.ABILITIES:  # (not this build's: NOSWAP_KEEP)
        return own
    if ab.cycle(i):  # several jump abilities: the active one's (cd_functions' NoSwap_Copycat<i>)
        return f"NoSwap_Copycat{i}"
    return next((f"NoSwap_{names[a]}{i}" for a in cfg(i)["abilities"]
                 if a in names and not (a == "aim_dash" and cfg(i).get("aim_dash_y"))
                 and not (a == "screw_kick" and not cfg(i).get("kick_jump"))), own)


# Mighty's Hammer Drop landing (Mania Plus's Player_State_MightyHammerDrop): bounce up in the ball along
# the ground's angle, with 3/4 of the ground speed
HAMMER_AFTER = """if NoSwap.Ability == 1
	if Player.Gravity == GRAVITY_GROUND
		if Player.Animation == ANI_NOSWAP_ATTACK
			TempValue0 = 0x23800 // gravity + 2 px per frame
			TempValue1 = Player.Speed
			TempValue2 = TempValue1
			TempValue2 >>= 2
			TempValue1 -= TempValue2
			Sin256(TempValue3, Player.Angle)
			Cos256(TempValue4, Player.Angle)
			TempValue5 = TempValue1 // x: (ground speed * cos + bounce * sin) >> 8
			TempValue5 *= TempValue4
			TempValue2 = TempValue0
			TempValue2 *= TempValue3
			TempValue5 += TempValue2
			TempValue5 >>= 8
			TempValue2 = TempValue1 // y: (ground speed * sin - bounce * cos) >> 8
			TempValue2 *= TempValue3
			TempValue4 *= TempValue0
			TempValue2 -= TempValue4
			TempValue2 >>= 8
			CallFunction(Player_Action_Jump) // (uses TempValue0, 6 and 7)
			if Player.Gravity == GRAVITY_AIR
				Player.XVelocity = TempValue5
				Player.YVelocity = TempValue2
				Player.Animation = ANI_JUMPING
			end if
		end if
		NoSwap.Ability = -1
	end if
end if
""".rstrip("\n").split("\n")

# Ray's glide, one frame (Mania Plus's Player_State_RayGlide), run after the engine has moved him: the glide
# keeps its own velocity (the engine adds gravity and air control), and walls, ceilings and landing end
# or trim it. No water variant in CD.
RAY_AFTER = """if NoSwap.Ability > 0
	TempValue0 = false
	CheckEqual(Player.Animation, ANI_NOSWAP_GLIDE_UP)
	TempValue0 |= CheckResult
	CheckEqual(Player.Animation, ANI_NOSWAP_GLIDE_DOWN)
	TempValue0 |= CheckResult
	if TempValue0 == false
		NoSwap.Ability = -1 // hurt, springs...
	end if
end if
if NoSwap.Ability > 0
	if Player.Gravity == GRAVITY_GROUND
		TempValue0 = Player.Speed // a slow landing gets a boost
		if TempValue0 < 0
			FlipSign(TempValue0)
		end if
		if TempValue0 < 0x20000
			Player.Speed <<= 1
		end if
		NoSwap.Ability = -1
		Player.Animation = ANI_WALKING
	else
		if Player.XVelocity == 0 // a wall
			NoSwap.GlideVX = 0
		end if
		TempValue7 = NoSwap.Shot // unpack: up, left, power
		TempValue5 = TempValue7
		TempValue5 &= 1
		TempValue6 = TempValue7
		TempValue6 >>= 1
		TempValue6 &= 1
		TempValue7 >>= 2
		if TempValue6 == 1
			Player.Direction = FACING_LEFT
		else
			Player.Direction = FACING_RIGHT
		end if

		if TempValue5 == 1
			if NoSwap.Ability < 0x70
				NoSwap.Ability += 8
			end if
		else
			if NoSwap.Ability > 0x10
				NoSwap.Ability -= 8
			end if
		end if

		if NoSwap.GlideLift != 0
			TempValue0 = NoSwap.GlideLift
			TempValue0 >>= 2
			NoSwap.GlideVY += TempValue0
			if NoSwap.GlideVY < NoSwap.GlideLift
				NoSwap.GlideVY = NoSwap.GlideLift
				NoSwap.GlideLift = 0
			end if
		else
			Cos(TempValue0, NoSwap.Ability)
			TempValue0 *= 0x3800
			TempValue0 >>= 9
			NoSwap.GlideVY += TempValue0
		end if
		if NoSwap.GlideVY < -0x60000
			NoSwap.GlideVY = -0x60000
		end if
		if TempValue5 == 1
			if NoSwap.GlideVY > 0x10000
				TempValue0 = NoSwap.GlideVY
				TempValue0 >>= 2
				NoSwap.GlideVY -= TempValue0
			end if
		end if

		TempValue1 = 0x50
		TempValue1 -= NoSwap.Ability
		TempValue1 &= 0xFF
		Sin256(TempValue2, TempValue1)
		TempValue2 *= 22
		if NoSwap.GlideVY <= 0
			NoSwap.GlideCap -= TempValue2
			if NoSwap.GlideCap < 0x40000
				NoSwap.GlideCap = 0x40000
			end if
		else
			if NoSwap.GlideVY > NoSwap.GlideCap
				TempValue0 = NoSwap.GlideVY
				TempValue0 >>= 6
				NoSwap.GlideCap = NoSwap.GlideVY
				NoSwap.GlideCap -= TempValue0
			end if
		end if

		if NoSwap.GlideVX != 0
			if TempValue6 == 1
				NoSwap.GlideVX -= TempValue2
				if NoSwap.GlideVX > -0x10000
					NoSwap.GlideVX = -0x10000
				end if
				TempValue0 = NoSwap.GlideCap
				FlipSign(TempValue0)
				if NoSwap.GlideVX < TempValue0
					NoSwap.GlideVX = TempValue0
				end if
			else
				NoSwap.GlideVX += TempValue2
				if NoSwap.GlideVX < 0x10000
					NoSwap.GlideVX = 0x10000
				end if
				if NoSwap.GlideVX > NoSwap.GlideCap
					NoSwap.GlideVX = NoSwap.GlideCap
				end if
			end if
		end if

		if TempValue6 == 1 // forward / back
			TempValue3 = Player.Left
			TempValue4 = Player.Right
		else
			TempValue3 = Player.Right
			TempValue4 = Player.Left
		end if
		TempValue0 = true
		if TempValue4 == true
			if NoSwap.Ability == 0x10
				TempValue0 = false
			end if
		end if
		if TempValue0 == true
			if TempValue3 == true // forward at the top of a swoop: tip over into a dive
				if NoSwap.Ability == 0x70
					if TempValue5 == 1
						NoSwap.GlideLift = 0
						TempValue5 = 0
					end if
				end if
			end if
		else
			if TempValue5 == 0 // back at the bottom of a dive: swoop up
				TempValue5 = 1
				TempValue0 = false
				if NoSwap.GlideVY > 0x28000
					TempValue0 = true
				end if
				if TempValue7 == 256
					TempValue0 = true
				end if
				if TempValue0 == true
					TempValue1 = NoSwap.GlideVX
					if TempValue1 < 0
						FlipSign(TempValue1)
					end if
					TempValue2 = TempValue1
					TempValue2 >>= 1
					TempValue3 = TempValue1
					TempValue3 >>= 2
					TempValue2 += TempValue3
					TempValue3 = TempValue1
					TempValue3 >>= 4
					TempValue2 += TempValue3
					TempValue2 *= TempValue7
					TempValue2 >>= 8
					FlipSign(TempValue2)
					NoSwap.GlideLift = TempValue2
					if TempValue7 > 16 // each swoop is weaker than the last
						TempValue7 -= 32
					end if
					if NoSwap.GlideLift < -0x60000
						NoSwap.GlideLift = -0x60000
					end if
				end if
			end if
		end if

		if TempValue5 == 1
			Player.Animation = ANI_NOSWAP_GLIDE_UP
		else
			Player.Animation = ANI_NOSWAP_GLIDE_DOWN
		end if
		Player.XVelocity = NoSwap.GlideVX
		Player.YVelocity = NoSwap.GlideVY
		Player.Speed = NoSwap.GlideVX
		TempValue7 <<= 2 // pack
		TempValue6 <<= 1
		TempValue7 |= TempValue6
		TempValue7 |= TempValue5
		NoSwap.Shot = TempValue7
		TempValue0 = NoSwap.GlideVX
		if TempValue0 < 0
			FlipSign(TempValue0)
		end if
		TempValue1 = false
		if Player.JumpHold == false
			TempValue1 = true
		end if
		if TempValue0 < 0x10000
			TempValue1 = true
		end if
		if TempValue1 == true // let go of jump, or too slow: curl up and fall
			NoSwap.Ability = -1
			NoSwap.Shot = 0
			Player.Animation = ANI_JUMPING
		end if
	end if
end if
if NoSwap.Ability < 0
	NoSwap.Shot = 0
end if
""".rstrip("\n").split("\n")


def aim_dash_start(i):
    """Starts an aimed dash (Ability: frames + 100 up / + 200 down, + 1000 if started facing left)."""
    return [
        f"NoSwap.Ability = {cfg(i)['dash_frames']}",
        "if Player.Up == true", "\tNoSwap.Ability += 100", "end if",
        "if Player.Down == true", "\tNoSwap.Ability += 200", "end if",
        "if Player.Direction == FACING_LEFT", "\tNoSwap.Ability += 1000", "end if",
        "Player.Animation = ANI_NOSWAP_ATTACK",
        "PlaySfx(SFX_G_RELEASE, false)",
    ]


def screw_kick_after(i):
    """Rouge's Screw Kick (abilities.py screw_kick) after the player has moved: landing bounces her up a little;
    the facing is put back (the air state's air control turns her around). Ability: 1 kicking right, 2 left, -1 used."""
    landing = [
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK // landed from the kick: a small bounce",
        "\t\t\tCallFunction(Player_Action_Jump) // (uses TempValue0, 6 and 7)",
        "\t\t\tif Player.Gravity == GRAVITY_AIR",
        f"\t\t\t\tPlayer.YVelocity = -{cfg(i)['kick_bounce']:#x}",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tNoSwap.Ability = -1 // no second kick in the bounce",
    ] if cfg(i)["kick_bounce"] else [  # (kick_bounce 0: he just lands; the ground state picks his pose from his speed)
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK // landed from the kick",
        "\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\tend if",
        "\t\tNoSwap.Ability = -1",
    ]
    return [
        "if NoSwap.Ability > 0",
        "\tif Player.Gravity == GRAVITY_GROUND",
    ] + landing + [
        "\telse",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK // the kick keeps its direction",
        "\t\t\tPlayer.Direction = FACING_RIGHT",
        "\t\t\tif NoSwap.Ability == 2",
        "\t\t\t\tPlayer.Direction = FACING_LEFT",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def screw_kick_go(i):
    """The kick's launch (Ability 1 kicking right, 2 left), its speed, pose and sound."""
    c = cfg(i)
    return [
        "NoSwap.Ability = 1",
        f"Player.XVelocity = {c['kick_x']:#x}",
        "if Player.Direction == FACING_LEFT",
        "\tNoSwap.Ability = 2",
        "\tFlipSign(Player.XVelocity)",
        "end if",
        "Player.Speed = Player.XVelocity",
        f"Player.YVelocity = {c['kick_y']:#x}",
        "Player.Animation = ANI_NOSWAP_ATTACK",
        "PlaySfx(SFX_G_RELEASE, false)",
    ]


def screw_kick_start(i):
    """Y in mid-air (from the DLL) starts the Screw Kick, once per airborne period, from the air states or out of
    Knuckles' glide (for good: the glide doesn't come back this jump)."""
    c = cfg(i)
    return [
        "if Player.Gravity == GRAVITY_AIR",
        "\tif game.callbackParam3 == 1 // Y, from the DLL",
        "\t\tif NoSwap.Ability == 0",
        "\t\t\tTempValue0 = false // in the air",
        "\t\t\tTempValue1 = false // gliding",
    ] + [l for s in ("Air", "Air_NoDropDash", "RollJump")
         for l in (f"\t\t\tCheckEqual(Player.State, Player_State_{s})", "\t\t\tTempValue0 |= CheckResult")] + [
        l for s in ("GlideLeft", "GlideRight", "GlideDrop", "GlideLeftNoGrip", "GlideRightNoGrip")
        for l in (f"\t\t\tCheckEqual(Player.State, Player_State_{s})", "\t\t\tTempValue1 |= CheckResult")] + [
        "\t\t\tTempValue0 |= TempValue1",
        "\t\t\tif Player.Animation == ANI_HURT",
        "\t\t\t\tTempValue0 = false",
        "\t\t\tend if",
        "\t\t\tif TempValue0 == true",
        "\t\t\t\tif TempValue1 == true",
        "\t\t\t\t\tPlayer.State = Player_State_Air",
        "\t\t\t\tend if",
    ] + ["\t\t\t\t" + l for l in screw_kick_go(i)] + [
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ] + Y_REARM


def cd_bat_glide(t):
    """bat_glide (abilities.py): Knuckles' glide states (left, right and CD's no-grip pair), slower and sinking
    more gently for these extras."""
    ids = [i for i in ab.ABILITIES if ab.has(i, "bat_glide")]
    ind = "\t\t\t"
    for i in ids:
        c, alias = cfg(i), next(e["alias"] for e in EXTRAS if e["id"] == i)
        sink = (f"{ind}if Player.YVelocity > 0x8000\n{ind}\tPlayer.YVelocity -= 0x2000\n{ind}else\n"
                f"{ind}\tPlayer.YVelocity += 0x2000\n{ind}end if\n")
        t = patch_n(t, sink, f"{ind}if Stage.PlayerListPos == {alias} // [NoSwap] a bat's glide sinks more gently\n"
                    f"{ind}\tif Player.YVelocity > {c['glide_sink']:#x}\n{ind}\t\tPlayer.YVelocity -= 0x2000\n{ind}\telse\n"
                    f"{ind}\t\tPlayer.YVelocity += {c['glide_gravity']:#x}\n{ind}\tend if\n{ind}else\n"
                    + "".join(f"\t{l}\n" for l in sink.rstrip("\n").split("\n")) + f"{ind}end if\n", "bat glide sink", 4)
        speed = rf"{ind}Cos\(Player\.XVelocity, Player\.Timer\)\n{ind}Player\.XVelocity +\*= Player\.Speed\n{ind}Player\.XVelocity >>= 9\n"
        t, n = re.subn(speed, lambda m: m.group(0) + f"{ind}if Stage.PlayerListPos == {alias} // [NoSwap] a bat's glide: "
                       f"slower, {c['glide_speed']} of Knuckles' speed\n{ind}\tPlayer.XVelocity *= {round(c['glide_speed'] * 256)}\n"
                       f"{ind}\tPlayer.XVelocity >>= 8\n{ind}end if\n", t)
        if n != 4:  # (one of the four has a double space)
            sys.exit(f"patch 'bat glide speed': found {n} times (expected 4)")
    return t


def falling_hover(i):
    """After a rocket_ride or ear_grapple (Ability < 0), with hover: holding jump once he's falling, from the jump
    ball, opens the hover (the parachute, the Ear Copter). The lines after "else" in NoSwap_AirAbilities."""
    c = cfg(i)
    hover_end = -(c["hover_frames"] + 1) if ab.has(i, "hover") else -1
    body = ["\tif NoSwap.Ability < 0", "\t\tTempValue0 = false"]
    if ab.has(i, "hover"):
        body += ["\t\tif Player.JumpHold == true", f"\t\t\tif NoSwap.Ability > {hover_end}", "\t\t\t\tTempValue0 = true",
                 "\t\t\tend if", "\t\tend if",
                 "\t\tif Player.Animation != ANI_NOSWAP_HOVER", "\t\t\tif Player.YVelocity < 0", "\t\t\t\tTempValue0 = false",
                 "\t\t\tend if", "\t\t\tif Player.Animation != ANI_JUMPING", "\t\t\t\tTempValue0 = false", "\t\t\tend if",
                 "\t\tend if"]
    return body + [
        "\t\tif TempValue0 == true",
        "\t\t\tif Player.Animation != ANI_NOSWAP_HOVER", "\t\t\t\tPlaySfx(SFX_G_FLYING, false)", "\t\t\tend if",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_HOVER",
        f"\t\t\tPlayer.YVelocity = {c.get('hover_sink', 0):#x}",
        "\t\t\tNoSwap.Ability--",
        "\t\telse",
        "\t\t\tif Player.Animation == ANI_NOSWAP_HOVER",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING",
        f"\t\t\t\tNoSwap.Ability = {hover_end}",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
    ]


def grapple_air(i):
    """Max's Ear Grapple (abilities.py ear_grapple) before the player moves: latched, he's reeled toward the latch
    point (gravity off); while the ear goes out he stops falling; then the Ear Copter, once he's falling."""
    speed = cfg(i)["reel_speed"] >> 8
    return [
        "if NoSwap.Ability > 0",
        "\tif Player.Animation == ANI_NOSWAP_ATTACK // (anything else ends it in NoSwap_AfterUpdate)",
        "\t\tPlayer.Direction = NoSwap.GrappleDir // air control would turn him (and the ear) around",
        "\t\tif NoSwap.Ability < 100",
        "\t\t\tif Player.YVelocity > 0 // the ear going out: he stops falling",
        "\t\t\t\tPlayer.YVelocity = 0",
        "\t\t\tend if",
        "\t\telse",
        "\t\t\tif NoSwap.Ability < 200 // latched: reeled in along the line to the latch point",
        "\t\t\t\tTempValue0 = NoSwap.GrappleX",
        "\t\t\t\tTempValue0 -= Player.XPos",
        "\t\t\t\tTempValue1 = NoSwap.GrappleY",
        "\t\t\t\tTempValue1 -= Player.YPos",
        "\t\t\t\tATan2(TempValue2, TempValue0, TempValue1)",
        "\t\t\t\tCos256(Player.XVelocity, TempValue2)",
        f"\t\t\t\tPlayer.XVelocity *= {speed:#x}",
        "\t\t\t\tSin256(Player.YVelocity, TempValue2)",
        f"\t\t\t\tPlayer.YVelocity *= {speed:#x}",
        "\t\t\t\tPlayer.Speed = Player.XVelocity",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "else",
    ] + falling_hover(i) + ["end if"]


def grapple_wait(c):
    """grapple_refill's cooldown in frames (0 without it: GrappleX -1, the old "used" mark, is all it tests)."""
    return c.get("grapple_cooldown", 0) if c.get("grapple_refill") else 0


def grapple_y_start(i):
    """grapple_y (abilities.py grapple_y_after): Y in mid-air (from the DLL) starts the Ear Grapple, from the jump, the
    Ear Copter or a fall, once per airborne period. Its "used" mark is NoSwap.GrappleX = -1 (only read while latched,
    and a latch point is never at -1): set as the ear goes out and again as the latch lets go; 0 on the ground.
    grapple_refill (the user, 2026-09-30): a latch or a badnik hit gives the grab back after grapple_cooldown frames,
    counted in GrappleX from -(cooldown + 1) up to -1, which is 0 (ready) at once; a miss leaves -1."""
    c = cfg(i)
    wait = -(grapple_wait(c) + 1)
    return [
        "if Player.Gravity == GRAVITY_GROUND",
        "\tNoSwap.GrappleX = 0",
        "else",
    ] + ([
        "\tif NoSwap.Ability <= 0 // grapple_refill: the cooldown after a pull, once the ear's in",
        "\t\tif NoSwap.GrappleX < -1",
        f"\t\t\tif NoSwap.GrappleX >= {wait}",
        "\t\t\t\tNoSwap.GrappleX++",
        "\t\t\t\tif NoSwap.GrappleX == -1",
        "\t\t\t\t\tNoSwap.GrappleX = 0",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
    ] if c.get("grapple_refill") else []) + [
        "\tif game.callbackParam3 == 1 // Y, from the DLL",
        "\t\tif NoSwap.Ability <= 0",
        "\t\t\tTempValue0 = true // used (-1) or waiting (grapple_refill) this airborne period?",
        "\t\t\tif NoSwap.GrappleX < 0",
        f"\t\t\t\tif NoSwap.GrappleX >= {wait}",
        "\t\t\t\t\tTempValue0 = false",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tif TempValue0 == true",
        "\t\t\t\tTempValue0 = false",
        "\t\t\t\tCheckEqual(Player.State, Player_State_Air)",
        "\t\t\t\tTempValue0 |= CheckResult",
        "\t\t\t\tCheckEqual(Player.State, Player_State_Air_NoDropDash)",
        "\t\t\t\tTempValue0 |= CheckResult",
        "\t\t\t\tif Player.Animation == ANI_HURT",
        "\t\t\t\t\tTempValue0 = false",
        "\t\t\t\tend if",
        "\t\t\t\tif TempValue0 == true",
        "\t\t\t\t\tNoSwap.GrappleX = -1",
        "\t\t\t\t\tNoSwap.Ability = 1",
        "\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_ATTACK",
        "\t\t\t\t\tNoSwap.GrappleDir = Player.Direction",
        "\t\t\t\t\tPlaySfx(SFX_G_RELEASE, false)",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ] + Y_REARM


def grapple_after(i):
    """Max's Ear Grapple after the player has moved, as in S1/S2 (abilities.py ear_grapple_after): landing, hits and
    springs end it; the ear grows a frame and its tip is tested against the terrain (on a stand-in position in
    Object.XPos / YPos, as the game's own jump does); latched, he's let go once close, out of time or stopped by the
    terrain (Ristar's test, tools/star_grab.py), and a slope he touches down on doesn't end it while the point is well
    above; the frame follows the ear. While it goes out its tip's place is in NoSwap.GrappleX / GrappleY, where
    badniks, monitors and bosses test it (NoSwap_ShotTouch: cd_ear_touch; no NoSwap.Reach any more: the user,
    2026-09-30); every other way out of it in the air puts back grapple_y's "used" mark (GrappleX -1)."""
    c = cfg(i)
    n = len(c["grapple_tip"])
    hover_end = -(c["hover_frames"] + 1) if ab.has(i, "hover") else -1
    r = c["latch_range"]
    test = lambda side: ["\t\tCheckResult = false", "\t\tObject.XPos = Player.XPos", "\t\tObject.YPos = Player.YPos",
                         f"\t\tObjectTileCollision({side}, TempValue1, TempValue2, Player.CollisionPlane)"]
    used = (lambda ind: [f"{ind}NoSwap.GrappleX = -1 // grapple_y: used this airborne period"]
            if c.get("grapple_y") else [])
    chain = c.get("grapple_y") and c.get("grapple_refill")  # a latch or a hit gives the grab back (grapple_y_start)
    wait = -(grapple_wait(c) + 1)
    ended = (["\t\tif Player.Gravity != GRAVITY_GROUND"] + used("\t\t\t") + ["\t\tend if"] if not chain else [
        "\t\tif Player.Gravity != GRAVITY_GROUND // grapple_refill: going out, used; latched, given back",
        "\t\t\tif NoSwap.Ability < 100",
        "\t\t\t\tNoSwap.GrappleX = -1",
        "\t\t\telse",
        "\t\t\t\tif NoSwap.Ability < 200",
        "\t\t\t\t\tNoSwap.GrappleX = 0",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if"])
    return [
        "if NoSwap.Ability > 100",
        "\tif NoSwap.Ability < 200 // pulled in, but he touched down (a slope): a point well above lifts him off",
        "\t\tif Player.Gravity == GRAVITY_GROUND",
        "\t\t\tCheckEqual(Player.State, Player_State_Ground)",
        "\t\t\tif CheckResult == true",
        "\t\t\t\tTempValue0 = NoSwap.GrappleY",
        "\t\t\t\tTempValue0 -= Player.YPos",
        "\t\t\t\tTempValue0 >>= 16",
        "\t\t\t\tif TempValue0 < -12",
        "\t\t\t\t\tPlayer.State = Player_State_Air",
        "\t\t\t\t\tPlayer.Gravity = GRAVITY_AIR",
        "\t\t\t\t\tPlayer.YVelocity = -0x10000",
        "\t\t\t\t\tPlayer.XVelocity = 0",
        "\t\t\t\t\tPlayer.Speed = 0",
        "\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_ATTACK",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
        "if NoSwap.Ability > 0",
        "\tTempValue0 = false",
        "\tif Player.Gravity == GRAVITY_GROUND // landed: the ear's gone",
        "\t\tTempValue0 = true",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\tend if",
        "\tend if",
        "\tif Player.Animation != ANI_NOSWAP_ATTACK // hurt, a spring, the Ear Jab...",
        "\t\tTempValue0 = true",
        "\tend if",
        "\tif TempValue0 == true",
    ] + (ended if c.get("grapple_y") else []) + [
        f"\t\tNoSwap.Ability = {hover_end} // no Ear Copter this jump",
        "\tend if",
        "end if",
        "TempValue4 = 0 // the ear's frame",
        "if NoSwap.Ability > 200 // snapping back, shorter each frame",
        "\tTempValue4 = NoSwap.Ability",
        "\tTempValue4 -= 201",
        f"\tTempValue4 *= {n // c['snap_frames']}",
        "\tNoSwap.Ability--",
        "\tif NoSwap.Ability == 200",
        "\t\tNoSwap.Ability = -1 // the Ear Copter may follow",
        "\t\tPlayer.Animation = ANI_JUMPING",
        "\tend if",
        "end if",
        "if NoSwap.Ability > 100",
        "\tif NoSwap.Ability < 200 // latched and reeling in",
        "\t\tTempValue5 = NoSwap.GrappleX // how far the latch point is, in px (forward)",
        "\t\tTempValue5 -= Player.XPos",
        "\t\tTempValue5 >>= 16",
        "\t\tif NoSwap.GrappleDir == FACING_LEFT",
        "\t\t\tFlipSign(TempValue5)",
        "\t\tend if",
        "\t\tTempValue6 = NoSwap.GrappleY",
        "\t\tTempValue6 -= Player.YPos",
        "\t\tTempValue6 >>= 16",
        "\t\tTempValue0 = false // let go?",
        f"\t\tif NoSwap.Ability >= {100 + c['reel_frames']}",
        "\t\t\tTempValue0 = true",
        "\t\tend if",
        "\t\tif NoSwap.Ability > 102",
        "\t\t\tif Player.XVelocity == 0",
        "\t\t\t\tif Player.YVelocity == 0 // stopped by the terrain (Ristar's test)",
        "\t\t\t\t\tTempValue0 = true",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tTempValue3 = TempValue5",
        "\t\tif TempValue3 < 0",
        "\t\t\tFlipSign(TempValue3)",
        "\t\tend if",
        f"\t\tif TempValue3 < {r}",
        "\t\t\tTempValue3 = TempValue6",
        "\t\t\tif TempValue3 < 0",
        "\t\t\t\tFlipSign(TempValue3)",
        "\t\t\tend if",
        f"\t\t\tif TempValue3 < {r}",
        "\t\t\t\tTempValue0 = true",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tif TempValue0 == true // there: a small hop, still moving forward",
        f"\t\t\tPlayer.YVelocity = -{c['grapple_hop']:#x}",
        f"\t\t\tPlayer.XVelocity = {c['grapple_forward']:#x}",
        "\t\t\tif NoSwap.GrappleDir == FACING_LEFT",
        "\t\t\t\tFlipSign(Player.XVelocity)",
        "\t\t\tend if",
        "\t\t\tPlayer.Speed = Player.XVelocity",
    ] + ([f"\t\t\tNoSwap.GrappleX = {wait} // grapple_refill: the grab's back after the cooldown"] if chain
         else used("\t\t\t")) + [
        "\t\t\tNoSwap.Ability = -1 // the Ear Copter may follow",
        "\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\telse",
        "\t\t\tNoSwap.Ability++",
        "\t\t\tTempValue3 = 1 // the longest ear that doesn't reach past the latch point",
        f"\t\t\twhile TempValue3 < {n}",
        "\t\t\t\tTempValue7 = TempValue4",
        "\t\t\t\tTempValue4 = TempValue3",
        f"\t\t\t\tCallFunction(NoSwap_GrappleTip{i})",
        "\t\t\t\tTempValue4 = TempValue7",
        "\t\t\t\tif NoSwap.GrappleDir == FACING_LEFT // (forward distances here)",
        "\t\t\t\t\tFlipSign(TempValue1)",
        "\t\t\t\tend if",
        "\t\t\t\tif TempValue1 <= TempValue5",
        "\t\t\t\t\tif TempValue2 >= TempValue6",
        "\t\t\t\t\t\tTempValue4 = TempValue3",
        "\t\t\t\t\tend if",
        "\t\t\t\tend if",
        "\t\t\t\tTempValue3++",
        "\t\t\tloop",
        "\t\tend if",
        "\tend if",
        "end if",
        "if NoSwap.Ability > 0",
        "\tif NoSwap.Ability < 100 // the ear going out: does its tip reach solid ground (floor or ceiling side)?",
        "\t\tTempValue4 = NoSwap.Ability",
        "\t\tTempValue4--",
        f"\t\tCallFunction(NoSwap_GrappleTip{i})",
        "\t\tTempValue6 = Object.XPos",
        "\t\tTempValue7 = Object.YPos",
    ] + test("CSIDE_FLOOR") + [
        "\t\tTempValue3 = CheckResult",
        "\t\tif TempValue3 == false",
    ] + ["\t" + l for l in test("CSIDE_ROOF")] + [
        "\t\t\tTempValue3 = CheckResult",
        "\t\tend if",
        "\t\tObject.XPos = TempValue6",
        "\t\tObject.YPos = TempValue7",
        "\t\tTempValue1 <<= 16 // the tip's place: badniks, monitors and bosses test it (cd_ear_touch)",
        "\t\tTempValue2 <<= 16",
        "\t\tNoSwap.GrappleX = Player.XPos",
        "\t\tNoSwap.GrappleX += TempValue1",
        "\t\tNoSwap.GrappleY = Player.YPos",
        "\t\tNoSwap.GrappleY += TempValue2",
        "\t\tif TempValue3 == true // latched there",
        "\t\t\tNoSwap.Ability = 101",
        "\t\t\tPlaySfx(SFX_G_GRAB, false)",
        "\t\telse",
        "\t\t\tNoSwap.Ability++",
        f"\t\t\tif NoSwap.Ability > {n} // full reach, nothing there",
        f"\t\t\t\tNoSwap.Ability = {200 + c['snap_frames']}",
    ] + used("\t\t\t\t") + [
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
        "if Player.Animation == ANI_NOSWAP_ATTACK // the ear's frame",
        "\tPlayer.Frame = TempValue4",
        "\tPlayer.AnimationTimer = 0",
        "end if",
    ]


def cd_ear_touch(t):
    """NoSwap_ShotTouch's Ear Grapple part (Object: the badnik, monitor or boss; Object[10].Value0-3 its box, 16.16 from
    it): while the ear goes out, its tip (8 px round NoSwap.GrappleX / GrappleY) inside the box hits it as a shot does
    (CheckResult, SHOT_HIT: the target's own code takes it as an attack), and the ear snaps back (as Headdy's head:
    tools/head_throw.py cd_touch). Only TempValue0 (NoSwap_ShotTouch saved it)."""
    head = "\nfunction NoSwap_ShotTouch\n\tObject[11].Value0 = TempValue0\n\tObject[11].Value1 = ArrayPos0\n\tCheckResult = false\n"
    for i in ab.with_ability("ear_grapple"):
        if t.count(head) != 1:
            sys.exit("ear_grapple: CD's NoSwap_ShotTouch changed")
        t = t.replace(head, head + f"""	if Stage.PlayerListPos == {ab.ALIAS_OF[i]} // [NoSwap] the Ear Grapple's ear hits it (build_soniccd.py cd_ear_touch)
		if NoSwap.Ability > 0
			if NoSwap.Ability < 100
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
								CheckResult = true
								{shots_v3.SHOT_HIT} = true
								NoSwap.Ability = {200 + ab.ABILITIES[i]['snap_frames']}
""" + ((f"								NoSwap.GrappleX = {-(grapple_wait(ab.ABILITIES[i]) + 1)} // grapple_refill: a hit"
        " gives the grab back after the cooldown\n" if ab.ABILITIES[i].get("grapple_refill") else
        "								NoSwap.GrappleX = -1 // grapple_y: used this airborne period\n")
       if ab.ABILITIES[i].get("grapple_y") else "") + """							end if
						end if
					end if
				end if
			end if
		end if
	end if
""")
    return t


def spirit_approach(v, target, accel):
    """Lines moving `v` toward `target` by `accel` per frame, without overshooting."""
    return [f"if {v} < {target}", f"\t{v} += {accel:#x}", f"\tif {v} > {target}", f"\t\t{v} = {target}", "\tend if",
            "else", f"\t{v} -= {accel:#x}", f"\tif {v} < {target}", f"\t\t{v} = {target}", "\tend if", "end if"]


def spirit_air(i):
    """Tikal's Spirit Flight (abilities.py spirit_flight) before the player's state runs: held still while she
    transforms, then the orb's own velocity eases toward the d-pad's direction. The air state runs next, so its
    air control is kept out (left / right cleared: the flight sets her facing), and its drag and gravity are
    taken off in advance: she moves at the orb's velocity, and the game's collision still stops her at walls."""
    c = cfg(i)
    return [
        "if NoSwap.Ability > 0",
        "\tif Player.Animation != ANI_NOSWAP_ATTACK",
        "\t\tNoSwap.Ability = -1 // hurt, a spring...: the flight's over, their speed stays",
        "\telse",
        "\t\tNoSwap.Ability--",
        "\t\tTempValue0 = false // re-form?",
        "\t\tTempValue1 = 0 // the d-pad's velocity",
        "\t\tTempValue2 = 0",
        f"\t\tif NoSwap.Ability <= {c['spirit_frames']} // flying (not the transform)",
        "\t\t\tif Player.JumpPress == true",
        "\t\t\t\tTempValue0 = true",
        "\t\t\tend if",
        "\t\t\tif NoSwap.Ability == 0",
        "\t\t\t\tTempValue0 = true",
        "\t\t\tend if",
        f"\t\t\tTempValue3 = {c['spirit_speed']:#x}",
        "\t\t\tTempValue4 = Player.Left",
        "\t\t\tTempValue4 |= Player.Right",
        "\t\t\tif TempValue4 == true // diagonals: the same speed overall",
        "\t\t\t\tTempValue4 = Player.Up",
        "\t\t\t\tTempValue4 |= Player.Down",
        "\t\t\t\tif TempValue4 == true",
        f"\t\t\t\t\tTempValue3 = {c['spirit_diag']:#x}",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tif Player.Left == true",
        "\t\t\t\tTempValue1 = TempValue3",
        "\t\t\t\tFlipSign(TempValue1)",
        "\t\t\t\tPlayer.Direction = FACING_LEFT",
        "\t\t\tend if",
        "\t\t\tif Player.Right == true",
        "\t\t\t\tTempValue1 = TempValue3",
        "\t\t\t\tPlayer.Direction = FACING_RIGHT",
        "\t\t\tend if",
        "\t\t\tif Player.Up == true",
        "\t\t\t\tTempValue2 = TempValue3",
        "\t\t\t\tFlipSign(TempValue2)",
        "\t\t\tend if",
        "\t\t\tif Player.Down == true",
        "\t\t\t\tTempValue2 = TempValue3",
        "\t\t\tend if",
    ] + ["\t\t\t" + l for l in spirit_approach("NoSwap.SpiritVX", "TempValue1", c["spirit_accel"])
         + spirit_approach("NoSwap.SpiritVY", "TempValue2", c["spirit_accel"])] + [
        "\t\telse",
        "\t\t\tNoSwap.SpiritVX = 0",
        "\t\t\tNoSwap.SpiritVY = 0",
        "\t\tend if",
        "\t\tif TempValue0 == true // she re-forms, keeping her speed, but not shooting up",
        "\t\t\tNoSwap.Ability = -1",
        "\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\tif NoSwap.SpiritVY < 0",
        "\t\t\t\tNoSwap.SpiritVY = 0",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tPlayer.Left = false // no air control",
        "\t\tPlayer.Right = false",
        "\t\tPlayer.Timer = 0 // no jump cap (underwater it's lower than her rise)",
        "\t\tPlayer.Speed = NoSwap.SpiritVX",
        "\t\tPlayer.YVelocity = NoSwap.SpiritVY",
        "\t\tPlayer.YVelocity -= Player.GravityStrength // (the air state adds it back)",
        "\t\tif Player.YVelocity > -0x40000 // the air state's drag, rising: 1/32 of the speed",
        "\t\t\tif Player.YVelocity < 0",
        "\t\t\t\tTempValue3 = Player.Speed",
        "\t\t\t\tTempValue3 >>= 5",
        "\t\t\t\tPlayer.Speed += TempValue3",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def spirit_after(i):
    """Tikal's Spirit Flight after the player has moved, as in S1/S2 (abilities.py spirit_flight_after): landing ends
    it; a wall or ceiling stops the orb's own velocity along it; the timer picks the transform's frames, then
    starts the orb's loop."""
    c = cfg(i)
    n, ticks, total = c["spirit_transform"], c["spirit_ticks"], ab.spirit_total(i)
    return [
        "if NoSwap.Ability > 0",
        "\tif Player.Gravity == GRAVITY_GROUND // landed: she re-forms",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\tend if",
        "\t\tNoSwap.Ability = -1",
        "\telse",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\t\tif Player.XVelocity == 0 // a wall",
        "\t\t\t\tNoSwap.SpiritVX = 0",
        "\t\t\tend if",
        "\t\t\tif Player.YVelocity == 0 // a ceiling",
        "\t\t\t\tNoSwap.SpiritVY = 0",
        "\t\t\tend if",
        f"\t\t\tif NoSwap.Ability >= {c['spirit_frames']}",
        f"\t\t\t\tTempValue0 = {total} // the transform's frame",
        "\t\t\t\tTempValue0 -= NoSwap.Ability",
    ] + ([f"\t\t\t\tTempValue0 /= {ticks}"] if ticks > 1 else []) + [
        f"\t\t\t\tif TempValue0 > {n} // (the flight's first frame: the orb)",
        f"\t\t\t\t\tTempValue0 = {n}",
        "\t\t\t\tend if",
        "\t\t\t\tPlayer.Frame = TempValue0",
        "\t\t\t\tPlayer.AnimationTimer = 0",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


ROCKET_ALIAS = ("#alias Object[5].Value4 : NoSwap.RocketVX // [NoSwap] Sparkster's Rocket Burst: its own velocity (0, 0: "
                "the Rocket Spin)\n"
                "#alias Object[5].Value5 : NoSwap.RocketVY // [NoSwap]\n")


def rocket_air(i):
    """Sparkster's Rocket Burst (abilities.py rocket_burst) before the player's state runs, as in S1/S2
    (abilities.rocket_burst_air). Charging (Ability ROCKET_CHARGING + frames): no air control, drifting to a stop, falling
    at rocket_sink at most; letting go of jump fires it (or fizzles, too soon). The burst / spin: the air state's air
    control kept out (left / right cleared), its drag and gravity taken off in advance, so he moves at the burst's own
    velocity, and the game's collision still stops him at walls (rocket_after bounces him off them)."""
    c = cfg(i)
    k = ab.ROCKET_CHARGING
    return [
        "if NoSwap.Ability > 0 // Rocket Burst (build_soniccd.rocket_air)",
        "\tif Player.Animation != ANI_NOSWAP_ATTACK",
        "\t\tNoSwap.Ability = -1 // hurt, a spring...: over, their speed stays",
        "\telse",
        f"\t\tif NoSwap.Ability >= {k} // charging",
        f"\t\t\tif NoSwap.Ability < {k + 0x4000}", "\t\t\t\tNoSwap.Ability++", "\t\t\tend if",
        "\t\t\tTempValue0 = Player.Speed // drifting to a stop", "\t\t\tTempValue0 /= 16", "\t\t\tPlayer.Speed -= TempValue0",
        f"\t\t\tTempValue0 = {c['rocket_sink']:#x} // falling at rocket_sink at most (the air state adds gravity)",
        "\t\t\tTempValue0 -= Player.GravityStrength",
        "\t\t\tif Player.YVelocity > TempValue0", "\t\t\t\tPlayer.YVelocity = TempValue0", "\t\t\tend if",
        "\t\t\tif Player.JumpHold == false // let go: fire",
        f"\t\t\t\tif NoSwap.Ability < {k + c['rocket_charge']}",
        "\t\t\t\t\tNoSwap.Ability = -1 // too soon: it fizzles", "\t\t\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\t\telse",
        "\t\t\t\t\tTempValue0 = 0 // the d-pad's direction", "\t\t\t\t\tTempValue1 = 0",
        "\t\t\t\t\tif Player.Left == true", "\t\t\t\t\t\tTempValue0 = -1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif Player.Right == true", "\t\t\t\t\t\tTempValue0 = 1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif Player.Up == true", "\t\t\t\t\t\tTempValue1 = -1", "\t\t\t\t\tend if",
        "\t\t\t\t\tif Player.Down == true", "\t\t\t\t\t\tTempValue1 = 1", "\t\t\t\t\tend if",
        f"\t\t\t\t\tTempValue2 = {c['rocket_speed']:#x}",
        "\t\t\t\t\tif TempValue0 != 0", "\t\t\t\t\t\tif TempValue1 != 0 // diagonals: the same speed overall",
        f"\t\t\t\t\t\t\tTempValue2 = {c['rocket_diag']:#x}", "\t\t\t\t\t\tend if", "\t\t\t\t\tend if",
        "\t\t\t\t\tNoSwap.RocketVX = TempValue0", "\t\t\t\t\tNoSwap.RocketVX *= TempValue2",
        "\t\t\t\t\tNoSwap.RocketVY = TempValue1", "\t\t\t\t\tNoSwap.RocketVY *= TempValue2",
        f"\t\t\t\t\tNoSwap.Ability = {c['rocket_frames'] + 1} // (counted down below, this frame too)",
        "\t\t\t\t\tif TempValue0 == 0", "\t\t\t\t\t\tif TempValue1 == 0 // nothing held: the Rocket Spin, in place",
        f"\t\t\t\t\t\t\tNoSwap.Ability = {c['rocket_spin_frames'] + 1}", "\t\t\t\t\t\tend if", "\t\t\t\t\tend if",
        "\t\t\t\t\tif TempValue0 < 0", "\t\t\t\t\t\tPlayer.Direction = FACING_LEFT", "\t\t\t\t\tend if",
        "\t\t\t\t\tif TempValue0 > 0", "\t\t\t\t\t\tPlayer.Direction = FACING_RIGHT", "\t\t\t\t\tend if",
        f"\t\t\t\t\tPlaySfx({c['rocket_sfx_cd']}, false)",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tPlayer.Left = false // no air control",
        "\t\t\tPlayer.Right = false",
        "\t\tend if",
        "\t\tif NoSwap.Ability > 0",
        f"\t\t\tif NoSwap.Ability < {k} // the burst / the spin",
        "\t\t\t\tNoSwap.Ability--",
        "\t\t\t\tif NoSwap.Ability == 0 // over: he falls from here, keeping half its speed",
        "\t\t\t\t\tNoSwap.Ability = -1", "\t\t\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\t\t\tPlayer.Speed = NoSwap.RocketVX", "\t\t\t\t\tPlayer.Speed /= 2",
        "\t\t\t\t\tPlayer.YVelocity = NoSwap.RocketVY", "\t\t\t\t\tPlayer.YVelocity /= 2",
        "\t\t\t\telse",
        "\t\t\t\t\tPlayer.Left = false // no air control", "\t\t\t\t\tPlayer.Right = false",
        "\t\t\t\t\tPlayer.Timer = 0 // no jump cap",
        "\t\t\t\t\tPlayer.Speed = NoSwap.RocketVX",
        "\t\t\t\t\tPlayer.YVelocity = NoSwap.RocketVY",
        "\t\t\t\t\tPlayer.YVelocity -= Player.GravityStrength // (the air state adds it back)",
        "\t\t\t\t\tif Player.YVelocity > -0x40000 // the air state's drag, rising: 1/32 of the speed",
        "\t\t\t\t\t\tif Player.YVelocity < 0", "\t\t\t\t\t\t\tTempValue3 = Player.Speed", "\t\t\t\t\t\t\tTempValue3 >>= 5",
        "\t\t\t\t\t\t\tPlayer.Speed += TempValue3", "\t\t\t\t\t\tend if", "\t\t\t\t\tend if",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def rocket_after(i):
    """Sparkster's Rocket Burst after the player has moved, as in S1/S2 (abilities.rocket_burst_after): landing ends it; a
    wall or a ceiling that stopped the burst bounces it off (a ricochet); the code picks the frame (45: CD's slot 41)."""
    c = cfg(i)
    k, fr = ab.ROCKET_CHARGING, ab.ROCKET_FRAMES
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = extras.player_ani(e, "SonicCDu")["anims"]
    if len(anims) <= 45 or len(anims[45]["frames"]) != ab.ROCKET_ART:
        sys.exit(f"rocket_burst: extra {i} needs its {ab.ROCKET_ART} Rocket Burst frames in CD's 45 (cd_config)")
    return [
        "if NoSwap.Ability > 0 // Rocket Burst (build_soniccd.rocket_after)",
        "\tif Player.Gravity == GRAVITY_GROUND // landed: over",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK", "\t\t\tPlayer.Animation = ANI_WALKING", "\t\tend if",
        "\t\tNoSwap.Ability = -1",
        "\telse",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        f"\t\t\tif NoSwap.Ability >= {k}",
        f"\t\t\t\tTempValue0 = {fr['charge']}",
        f"\t\t\t\tif NoSwap.Ability >= {k + c['rocket_charge']} // charged: it flashes",
        "\t\t\t\t\tTempValue1 = NoSwap.Ability", "\t\t\t\t\tTempValue1 >>= 2", "\t\t\t\t\tTempValue1 &= 1",
        "\t\t\t\t\tTempValue0 += TempValue1",
        "\t\t\t\tend if",
        "\t\t\telse",
        "\t\t\t\tif NoSwap.RocketVX != 0", "\t\t\t\t\tif Player.XVelocity == 0 // a wall: ricochet",
        "\t\t\t\t\t\tFlipSign(NoSwap.RocketVX)", "\t\t\t\t\tend if", "\t\t\t\tend if",
        "\t\t\t\tif NoSwap.RocketVY < 0", "\t\t\t\t\tif Player.YVelocity == 0 // a ceiling: ricochet",
        "\t\t\t\t\t\tFlipSign(NoSwap.RocketVY)", "\t\t\t\t\tend if", "\t\t\t\tend if",
        "\t\t\t\tif NoSwap.RocketVX < 0", "\t\t\t\t\tPlayer.Direction = FACING_LEFT", "\t\t\t\tend if",
        "\t\t\t\tif NoSwap.RocketVX > 0", "\t\t\t\t\tPlayer.Direction = FACING_RIGHT", "\t\t\t\tend if",
        f"\t\t\t\tTempValue0 = {fr['fwd']}",
        "\t\t\t\tif NoSwap.RocketVY > 0", f"\t\t\t\t\tTempValue0 = {fr['down_fwd']}",
        "\t\t\t\t\tif NoSwap.RocketVX == 0", f"\t\t\t\t\t\tTempValue0 = {fr['down']}", "\t\t\t\t\tend if", "\t\t\t\tend if",
        "\t\t\t\tif NoSwap.RocketVY < 0", f"\t\t\t\t\tTempValue0 = {fr['up_fwd']}",
        "\t\t\t\t\tif NoSwap.RocketVX == 0", f"\t\t\t\t\t\tTempValue0 = {fr['up']}", "\t\t\t\t\tend if", "\t\t\t\tend if",
        "\t\t\t\tif NoSwap.RocketVX == 0", "\t\t\t\t\tif NoSwap.RocketVY == 0 // the Rocket Spin: its frames in turn",
        f"\t\t\t\t\t\tTempValue0 = {c['rocket_spin_frames']}", "\t\t\t\t\t\tTempValue0 -= NoSwap.Ability",
        f"\t\t\t\t\t\tTempValue0 /= {c['rocket_spin_ticks']}", f"\t\t\t\t\t\tTempValue0 &= {ab.ROCKET_SPIN_FRAMES - 1}",
        f"\t\t\t\t\t\tTempValue0 += {fr['spin']}", "\t\t\t\t\tend if", "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tPlayer.Frame = TempValue0",
        "\t\t\tPlayer.PrevAnimation = Player.Animation // (the frame is picked here)",
        "\t\t\tPlayer.AnimationTimer = 0",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def let_go_of_wall(i):
    """Off the wall, in the jump ball, with the Double Jump ready again; that wall locked for a moment."""
    return ["NoSwap.Cling = 0", f"NoSwap.ClingLock = {cfg(i)['cling_lock']}", "Player.Animation = ANI_JUMPING",
            "NoSwap.Ability = 0 // the Double Jump ready again"]


def wall_cling_air(i):
    """Trip's Wall Cling (abilities.py wall_cling) before the player's state runs: on the wall she's held there, slides
    or climbs; jump kicks off it, letting go of toward or running out of time drops her. The air state runs next, so
    its air control is kept out (left / right cleared: she faces the wall) and its gravity taken off in advance. Off
    it, in an air state, pushing toward a wall right beside her from a jump, a fall or a Double Jump grabs it."""
    c = cfg(i)
    return [
        "if NoSwap.Cling > 0",
        "\tif Player.Animation != ANI_NOSWAP_CLING",
        "\t\tNoSwap.Cling = 0 // hurt, a spring...: she lets go, their speed stays",
        "\telse",
        "\t\tNoSwap.Cling++",
        "\t\tif NoSwap.ClingDir == FACING_RIGHT // still holding toward the wall?",
        "\t\t\tTempValue0 = Player.Right",
        "\t\telse",
        "\t\t\tTempValue0 = Player.Left",
        "\t\tend if",
        "\t\tPlayer.Left = false // no air control",
        "\t\tPlayer.Right = false",
        "\t\tPlayer.Direction = NoSwap.ClingDir // facing the wall",
        "\t\tPlayer.Speed = 0",
        "\t\tif Player.JumpPress == true // a wall jump: kick off away from it",
        f"\t\t\tPlayer.Speed = -{c['wall_jump_x']:#x}",
        "\t\t\tPlayer.Direction = FACING_LEFT",
        "\t\t\tif NoSwap.ClingDir == FACING_LEFT",
        "\t\t\t\tFlipSign(Player.Speed)",
        "\t\t\t\tPlayer.Direction = FACING_RIGHT",
        "\t\t\tend if",
        f"\t\t\tPlayer.YVelocity = -{c['wall_jump_y']:#x}",
        "\t\t\tPlayer.Timer = 1 // letting go of jump cuts it short, as with a jump",
        "\t\t\tTempValue0 = 2",
        "\t\t\tPlaySfx(SFX_G_JUMP, false)",
        "\t\telse",
        f"\t\t\tif NoSwap.Cling > {c['cling_frames']}",
        "\t\t\t\tTempValue0 = false // out of time",
        "\t\t\tend if",
        "\t\t\tPlayer.YVelocity = 0 // held still, then sliding down slowly",
        f"\t\t\tif NoSwap.Cling > {c['cling_hold']}",
        f"\t\t\t\tPlayer.YVelocity = {c['cling_slide']:#x}",
        "\t\t\tend if",
        "\t\t\tif Player.Up == true // climbing (the game's collision stops her at a floor or a ceiling)",
        f"\t\t\t\tPlayer.YVelocity = -{c['climb_speed']:#x}",
        "\t\t\tend if",
        "\t\t\tif Player.Down == true",
        f"\t\t\t\tPlayer.YVelocity = {c['climb_speed']:#x}",
        "\t\t\tend if",
        "\t\t\tPlayer.YVelocity -= Player.GravityStrength // (the air state adds it back)",
        "\t\tend if",
        "\t\tPlayer.XVelocity = Player.Speed",
        "\t\tif TempValue0 != true // off the wall (a wall jump, let go, out of time)",
    ] + ["\t\t\t" + l for l in let_go_of_wall(i)] + [
        "\t\tend if",
        "\tend if",
        "else",
        "\tTempValue0 = -1 // the side she's pushing toward",
        "\tif Player.Right == true",
        "\t\tTempValue0 = FACING_RIGHT",
        "\tend if",
        "\tif Player.Left == true",
        "\t\tTempValue0 = FACING_LEFT",
        "\tend if",
        "\tif NoSwap.ClingLock > 0",
        "\t\tif TempValue0 == NoSwap.ClingDir",
        "\t\t\tTempValue0 = -1 // the wall she just let go of",
        "\t\tend if",
        "\tend if",
        "\tTempValue1 = false // in an air state",
        "\tCheckEqual(Player.State, Player_State_Air)",
        "\tTempValue1 |= CheckResult",
        "\tCheckEqual(Player.State, Player_State_Air_NoDropDash)",
        "\tTempValue1 |= CheckResult",
        "\tCheckEqual(Player.State, Player_State_RollJump)",
        "\tTempValue1 |= CheckResult",
        "\tTempValue2 = false // jumping, falling, or in the Double Jump",
        "\tCheckEqual(Player.Animation, ANI_JUMPING)",
        "\tTempValue2 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_NOSWAP_ATTACK)",
        "\tTempValue2 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_WALKING)",
        "\tTempValue2 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_RUNNING)",
        "\tTempValue2 |= CheckResult",
        "\tTempValue1 &= TempValue2",
        "\tif TempValue0 < 0",
        "\t\tTempValue1 = false",
        "\tend if",
        "\tif TempValue1 == true",
        f"\t\tCallFunction(NoSwap_WallBeside{i})",
        "\t\tif TempValue1 == true // she grabs the wall",
        "\t\t\tNoSwap.Cling = 1",
        "\t\t\tNoSwap.ClingDir = TempValue0",
        "\t\t\tPlayer.State = Player_State_Air // (out of a roll jump too: air control after a wall jump)",
        "\t\t\tPlayer.Animation = ANI_NOSWAP_CLING",
        "\t\t\tPlayer.Direction = TempValue0",
        "\t\t\tPlayer.Left = false",
        "\t\t\tPlayer.Right = false",
        "\t\t\tPlayer.Speed = 0",
        "\t\t\tPlayer.XVelocity = 0",
        "\t\t\tPlayer.YVelocity = 0",
        "\t\t\tPlayer.YVelocity -= Player.GravityStrength // (the air state adds it back)",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


# The Double Jump's spin after the player has moved (abilities.py double_jump_after): an extra with a Double Jump or a
# Wall Cling (Trip, Bean's Leap; Sticks' cling had it from when the two came together), before wall_cling_after
DOUBLE_JUMP_AFTER = [
    "if Player.Animation == ANI_NOSWAP_ATTACK // the Double Jump's shell spin",
    "\tif Player.Gravity == GRAVITY_GROUND",
    "\t\tPlayer.Animation = ANI_WALKING",
    "\telse",
    "\t\tif Player.YVelocity >= 0",
    "\t\t\tPlayer.Animation = ANI_JUMPING // falling: the jump ball again",
    "\t\tend if",
    "\tend if",
    "end if",
]


def wall_cling_after(i):
    """Trip's Double Jump and Wall Cling after the player has moved, as in S1/S2 (abilities.py double_jump_after,
    wall_cling_after): the shell spin lasts while she rises; landing, a hit or a spring ends the cling; the wall ending
    beside her lets go (climbing up, with a hop up onto the ledge); the lock on the wall she let go of counts down
    while she's away from it."""
    c = cfg(i)
    return [
        "if NoSwap.Cling > 0",
        "\tif Player.Gravity == GRAVITY_GROUND // landed (climbing down to the floor, too)",
        "\t\tNoSwap.Cling = 0",
        "\t\tif Player.Animation == ANI_NOSWAP_CLING",
        "\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\tend if",
        "\telse",
        "\t\tif Player.Animation != ANI_NOSWAP_CLING",
        "\t\t\tNoSwap.Cling = 0 // hurt, a spring, an object...",
        "\t\telse",
        "\t\t\tTempValue0 = NoSwap.ClingDir",
        f"\t\t\tCallFunction(NoSwap_WallBeside{i})",
        "\t\t\tif TempValue1 == false // the wall ends",
        "\t\t\t\tif Player.Up == true // climbed to its top: a hop up onto the ledge, toward it",
        f"\t\t\t\t\tPlayer.YVelocity = -{c['ledge_hop']:#x}",
        f"\t\t\t\t\tPlayer.Speed = {c['ledge_forward']:#x}",
        "\t\t\t\t\tif NoSwap.ClingDir == FACING_LEFT",
        "\t\t\t\t\t\tFlipSign(Player.Speed)",
        "\t\t\t\t\tend if",
        "\t\t\t\t\tPlayer.XVelocity = Player.Speed",
        "\t\t\t\t\tPlayer.Timer = 0 // (letting go of jump doesn't cut it short)",
        "\t\t\t\tend if",
    ] + ["\t\t\t\t" + l for l in let_go_of_wall(i)] + [
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
        "if Player.Gravity == GRAVITY_GROUND",
        "\tNoSwap.ClingLock = 0",
        "else",
        "\tif NoSwap.ClingLock > 0 // counting down only while she's away from the wall she let go of",
        "\t\tif NoSwap.Cling == 0",
        "\t\t\tTempValue0 = NoSwap.ClingDir",
        f"\t\t\tCallFunction(NoSwap_WallBeside{i})",
        "\t\t\tif TempValue1 == false",
        "\t\t\t\tNoSwap.ClingLock--",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def indented(lines, depth):
    return "".join("\t" * depth + l + "\n" for l in lines)


# The Y button: CD's scripts only see A/B/C (all jump) and Start. The NoSwap DLL reads the real controller
# and passes Y on through game.callbackParam3 (unused by CD's scripts): the script keeps a magic number there
# (built at runtime, so it exists nowhere else in memory for the DLL's search to find), and the DLL swaps it
# for 1 on a Y press. Y_REARM puts the magic number back after each frame's check.
Y_REARM = [
    "game.callbackParam3 = 0x4E53 // the magic number 0x4E53593F, for the DLL to find",
    "game.callbackParam3 <<= 16",
    "game.callbackParam3 += 0x593F",
]


def triple_jump_start(i):
    """Mario's Triple Jump (abilities.py triple_jump), in Player_Action_Jump once the jump is sure: the jump's number in
    the chain, and for the 2nd and 3rd a higher jump strength, until NoSwap_JumpEnd puts his own back."""
    c = cfg(i)
    return [
        "NoSwap.JumpSave = Player.JumpStrength",
        "TempValue0 = Player.Speed // running?",
        "if TempValue0 < 0",
        "\tFlipSign(TempValue0)",
        "end if",
        f"if TempValue0 < {c['triple_speed']:#x}",
        "\tNoSwap.JumpChain = 0 // too slow: a first jump",
        "end if",
        "if NoSwap.JumpChain >= 3",
        "\tNoSwap.JumpChain = 0 // after the third: a first jump again",
        "end if",
        "NoSwap.JumpChain++",
        "if NoSwap.JumpChain == 2",
        f"\tPlayer.JumpStrength *= {ab.triple_jump_scale(i, 2)} // x{c['triple_jumps'][0]}",
        "\tPlayer.JumpStrength >>= 8",
        "end if",
        "if NoSwap.JumpChain == 3",
        f"\tPlayer.JumpStrength *= {ab.triple_jump_scale(i, 3)} // x{c['triple_jumps'][1]}",
        "\tPlayer.JumpStrength >>= 8",
        "end if",
    ]


def triple_jump_after(i):
    """After the player has moved (as abilities.triple_jump_after): the chain stays open while he's in the air from a
    jump and for triple_window frames on the ground after; rolling or a hit breaks it. The 3rd jump somersaults until
    he starts falling."""
    return [
        "if Player.Animation == ANI_HURT",
        "\tNoSwap.JumpChain = 0",
        "end if",
        "TempValue0 = false // in the air from a jump (the jump pose, the somersault, the Fireball)?",
        "if Player.Gravity == GRAVITY_AIR",
        "\tCheckEqual(Player.Animation, ANI_JUMPING)",
        "\tTempValue0 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_NOSWAP_ATTACK)",
        "\tTempValue0 |= CheckResult",
        "\tCheckEqual(Player.Animation, ANI_NOSWAP_SHOT)",
        "\tTempValue0 |= CheckResult",
        "end if",
        "if TempValue0 == true",
        f"\tNoSwap.JumpWindow = {cfg(i)['triple_window']}",
        "else",
        "\tif NoSwap.JumpWindow > 0",
        "\t\tNoSwap.JumpWindow--",
        "\telse",
        "\t\tNoSwap.JumpChain = 0 // too long since the last jump",
        "\tend if",
        "end if",
        "CheckEqual(Player.State, Player_State_Roll)",
        "TempValue0 = CheckResult",
        "CheckEqual(Player.State, Player_State_TubeRoll)",
        "TempValue0 |= CheckResult",
        "if TempValue0 == true",
        "\tNoSwap.JumpChain = 0 // rolling: a jump out of it starts a new chain",
        "end if",
        "if NoSwap.JumpChain == 3 // the third jump: the somersault until he starts falling",
        "\tTempValue0 = false",
        "\tif Player.Gravity == GRAVITY_AIR",
        "\t\tif Player.YVelocity < 0",
        "\t\t\tCheckEqual(Player.Animation, ANI_JUMPING)",
        "\t\t\tTempValue0 |= CheckResult",
        "\t\t\tCheckEqual(Player.Animation, ANI_NOSWAP_ATTACK)",
        "\t\t\tTempValue0 |= CheckResult",
        "\t\tend if",
        "\tend if",
        "\tif TempValue0 == true",
        "\t\tPlayer.Animation = ANI_NOSWAP_ATTACK",
        "\telse",
        "\t\tNoSwap.JumpChain = 4 // falling, landed, or something else took over (a spring, a hit, the Fireball)",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\t\tif Player.Gravity == GRAVITY_AIR",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\telse",
        "\t\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def thunder_zip_air(i):
    """The zip, as in S1/S2 (abilities.thunder_zip_air): zip_frames level at zip_speed in its direction (the game's
    collision still stops her at a wall), then her speed along once, with gravity back."""
    c = cfg(i)
    after = c["zip_pose"] - c["zip_frames"]
    return [
        "if NoSwap.Ability > 0",
        "\tif Player.Animation == ANI_NOSWAP_ATTACK",
        f"\t\tif NoSwap.Ability > {after} // the zip",
        f"\t\t\tPlayer.XVelocity = {c['zip_speed']:#x}",
        "\t\t\tPlayer.Direction = FACING_RIGHT",
        "\t\t\tif NoSwap.ZipCarry < 0",
        "\t\t\t\tFlipSign(Player.XVelocity)",
        "\t\t\t\tPlayer.Direction = FACING_LEFT",
        "\t\t\tend if",
        "\t\t\tPlayer.YVelocity = 0",
        "\t\tend if",
        f"\t\tif NoSwap.Ability == {after} // out of it: her speed along, falling as usual",
        "\t\t\tPlayer.XVelocity = NoSwap.ZipCarry",
        "\t\tend if",
        "\t\tPlayer.Speed = Player.XVelocity",
        "\t\tNoSwap.Ability--",
        "\t\tif NoSwap.Ability == 0",
        "\t\t\tNoSwap.Ability = -1",
        "\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\tend if",
        "\telse",
        "\t\tNoSwap.Ability = -1 // hurt, a spring...: over for this jump",
        "\tend if",
        "end if",
    ]


def extreme_gear_air(i):
    """Jet's Extreme Gear ride, as in S1/S2 (abilities.extreme_gear_air), before the player's state runs: the air state
    comes next, so its air control is kept out (left / right cleared after they're read here), and its gravity and
    drag are taken off in advance: he moves at the board's velocity and the sink (or the lift) set here. The game's
    collision still stops him at walls (NoSwap_AfterUpdate). Ability: 1 riding, -1 used; GlideVX: the board's velocity
    (its sign: the way he rides); GlideLift: lift frames left; GlideVY: ride frames left (gear_frames: then it ends as
    letting go of jump does)."""
    c = cfg(i)
    return [
        "if NoSwap.Ability == 1",
        "\tif Player.Animation != ANI_NOSWAP_ATTACK",
        "\t\tNoSwap.Ability = -1 // hurt, a spring, the shot...: off the board",
        "\telse",
        "\t\tTempValue0 = Player.JumpHold",
        "\t\tif NoSwap.GlideVY <= 0 // gear_frames up: as if he'd let go",
        "\t\t\tTempValue0 = false",
        "\t\tend if",
        "\t\tif TempValue0 == false",
        "\t\t\tNoSwap.Ability = -1 // let go: off the board, in the jump ball",
        "\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\telse",
        "\t\t\tNoSwap.GlideVY--",
        "\t\t\tTempValue0 = NoSwap.GlideVX // the board's speed, forward",
        "\t\t\tTempValue1 = Player.Right // forward / back",
        "\t\t\tTempValue2 = Player.Left",
        "\t\t\tif TempValue0 < 0",
        "\t\t\t\tFlipSign(TempValue0)",
        "\t\t\t\tTempValue1 = Player.Left",
        "\t\t\t\tTempValue2 = Player.Right",
        "\t\t\tend if",
        "\t\t\tif TempValue2 == true // back: braking; slow enough, he carves round to ride the other way",
        f"\t\t\t\tTempValue0 -= {c['gear_brake']:#x}",
        f"\t\t\t\tif TempValue0 <= {c['gear_turn']:#x}",
        f"\t\t\t\t\tTempValue0 = {c['gear_turn']:#x}",
        "\t\t\t\t\tFlipSign(NoSwap.GlideVX)",
        "\t\t\t\tend if",
        "\t\t\telse",
        f"\t\t\t\tif TempValue0 < {c['gear_speed']:#x} // back up to cruising speed",
        f"\t\t\t\t\tTempValue0 += {c['gear_recover']:#x}",
        f"\t\t\t\t\tif TempValue0 > {c['gear_speed']:#x}",
        f"\t\t\t\t\t\tTempValue0 = {c['gear_speed']:#x}",
        "\t\t\t\t\tend if",
        "\t\t\t\telse",
        "\t\t\t\t\tif TempValue1 == true // forward: speeding up (a faster start is kept)",
        f"\t\t\t\t\t\tif TempValue0 < {c['gear_top']:#x}",
        f"\t\t\t\t\t\t\tTempValue0 += {c['gear_accel']:#x}",
        f"\t\t\t\t\t\t\tif TempValue0 > {c['gear_top']:#x}",
        f"\t\t\t\t\t\t\t\tTempValue0 = {c['gear_top']:#x}",
        "\t\t\t\t\t\t\tend if",
        "\t\t\t\t\t\tend if",
        "\t\t\t\t\tend if",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tif NoSwap.GlideVX < 0",
        "\t\t\t\tFlipSign(TempValue0)",
        "\t\t\t\tPlayer.Direction = FACING_LEFT",
        "\t\t\telse",
        "\t\t\t\tPlayer.Direction = FACING_RIGHT",
        "\t\t\tend if",
        "\t\t\tNoSwap.GlideVX = TempValue0",
        "\t\t\tTempValue1 = false // lifting?",
        "\t\t\tif Player.Up == true",
        "\t\t\t\tif NoSwap.GlideLift > 0",
        "\t\t\t\t\tTempValue1 = true",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tTempValue2 = Player.YVelocity // the fall speed he'll move at, before the air state adds gravity",
        "\t\t\tTempValue2 += Player.GravityStrength",
        "\t\t\tif TempValue1 == true // up: the nose tilts up, a little lift (gear_lift_frames per ride)",
        "\t\t\t\tNoSwap.GlideLift--",
        f"\t\t\t\tif Player.YVelocity > -{c['gear_rise']:#x}",
        "\t\t\t\t\tTempValue2 = Player.YVelocity",
        f"\t\t\t\t\tTempValue2 -= {c['gear_lift']:#x}",
        f"\t\t\t\t\tif TempValue2 < -{c['gear_rise']:#x}",
        f"\t\t\t\t\t\tTempValue2 = -{c['gear_rise']:#x}",
        "\t\t\t\t\tend if",
        "\t\t\t\tend if",
        "\t\t\telse",
        f"\t\t\t\tif TempValue2 > {c['gear_sink']:#x} // sinking slowly",
        f"\t\t\t\t\tTempValue2 = {c['gear_sink']:#x}",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tPlayer.Left = false // no air control",
        "\t\t\tPlayer.Right = false",
        "\t\t\tPlayer.Speed = NoSwap.GlideVX",
        "\t\t\tPlayer.YVelocity = TempValue2",
        "\t\t\tPlayer.YVelocity -= Player.GravityStrength // (the air state adds it back)",
        "\t\t\tif Player.YVelocity > -0x40000 // the air state's drag, rising: 1/32 of the speed",
        "\t\t\t\tif Player.YVelocity < 0",
        "\t\t\t\t\tTempValue3 = Player.Speed",
        "\t\t\t\t\tTempValue3 >>= 5",
        "\t\t\t\t\tPlayer.Speed += TempValue3",
        "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def extreme_gear_after(i):
    """After the player has moved, as in S1/S2 (abilities.extreme_gear_after): landing ends the ride, running on at the
    board's speed; a wall knocks him off."""
    return [
        "if NoSwap.Ability == 1",
        "\tif Player.Animation == ANI_NOSWAP_ATTACK",
        "\t\tif Player.Gravity == GRAVITY_GROUND // landed, Sonic Riders style: running on at the board's speed",
        "\t\t\tPlayer.Speed = NoSwap.GlideVX",
        "\t\t\tPlayer.Animation = ANI_WALKING",
        "\t\t\tNoSwap.Ability = -1",
        "\t\telse",
        "\t\t\tif Player.XVelocity == 0 // a wall: off the board",
        "\t\t\t\tNoSwap.Ability = -1",
        "\t\t\t\tPlayer.Animation = ANI_JUMPING",
        "\t\t\tend if",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def surge_scale(key, i, back=False):
    """Lines scaling Player.<key> by the surge multiplier for its physics column (as a fraction; `back` undoes it)."""
    from fractions import Fraction
    col = {"TopSpeed": "top_speed", "Acceleration": "acceleration", "Deceleration": "acceleration",
           "AirAcceleration": "air_acceleration"}[key]
    f = Fraction(cfg(i)["surge_physics"].get(col, 1.0)).limit_denominator(100)
    num, den = (f.denominator, f.numerator) if back else (f.numerator, f.denominator)
    return [] if f == 1 else [f"Player.{key} *= {num}", f"Player.{key} /= {den}"]


def power_surge_after(i):
    """Power Surge, as in S1/S2 (abilities.power_surge_after): Y (from the DLL) starts it, her speeds go up for
    surge_frames (on top of whatever they are: water, speed shoes), then the cooldown. Her top speed before it is kept,
    and put back at the end with the rest undone, unless the game has set its own since (speed shoes, leaving water)."""
    c = cfg(i)
    cool = c["surge_cooldown"]
    keys = ("TopSpeed", "Acceleration", "Deceleration", "AirAcceleration")
    return [
        "if NoSwap.Surge > 0 // Power Surge: its frames, then the cooldown",
        "\tNoSwap.Surge--",
        f"\tif NoSwap.Surge == {cool} // over: her own speeds again",
        "\t\tTempValue0 = NoSwap.SurgeTop // (the top speed the surge set)",
    ] + ["\t\t" + l.replace("Player.TopSpeed", "TempValue0") for l in surge_scale("TopSpeed", i)] + [
        "\t\tif Player.TopSpeed == TempValue0",
        "\t\t\tPlayer.TopSpeed = NoSwap.SurgeTop",
    ] + ["\t\t\t" + l for k in keys[1:] for l in surge_scale(k, i, back=True)] + [
        "\t\tend if",
        "\tend if",
        "end if",
        "if game.callbackParam3 == 1 // Y, from the DLL",
        "\tif NoSwap.Surge == 0",
        "\t\tTempValue0 = true",
        "\t\tif Player.Animation == ANI_HURT",
        "\t\t\tTempValue0 = false",
        "\t\tend if",
        "\t\tif Player.Animation == ANI_DYING",
        "\t\t\tTempValue0 = false",
        "\t\tend if",
        "\t\tif TempValue0 == true",
        f"\t\t\tNoSwap.Surge = {c['surge_frames'] + cool}",
        "\t\t\tNoSwap.SurgeTop = Player.TopSpeed",
    ] + ["\t\t\t" + l for k in keys for l in surge_scale(k, i)] + [
        "\t\t\tPlaySfx(SFX_G_SHIELD, false)",
        "\t\tend if",
        "\tend if",
        "end if",
    ] + Y_REARM


def cd_surge(t):
    """power_surge in the player object: while a surge lasts, badniks break on touch (Player_BadnikBreak, which every
    badnik calls), and her idle / walk / run show as the Power Surge ones, only while animating and drawing (as
    cd_roll; abilities.surge_in_out)."""
    ids = [i for i in ab.ABILITIES if ab.has(i, "power_surge")]
    if not ids:
        return t
    alias = lambda i: next(e["alias"] for e in EXTRAS if e["id"] == i)
    zap = "".join(f"\tif Stage.PlayerListPos == {alias(i)} // [NoSwap] Power Surge: she zaps whatever she touches\n"
                  f"\t\tif NoSwap.Surge > {cfg(i)['surge_cooldown']}\n\t\t\tTempValue0 |= true\n\t\tend if\n\tend if\n\n"
                  for i in ids)
    anchor = "\t// you're invincible to badniks during the warping run\n\tif Warp.Timer > 0\n\t\tTempValue0 |= true\n\tend if\n\n"
    t = patch(t, anchor, anchor + zap, "surge badniks")
    # (only for them: SurgeFrom shares its value with the other extras' shots)
    body = []
    for i in ids:
        body += [f"if Stage.PlayerListPos == {alias(i)}", "\tNoSwap.SurgeFrom = -1",
                 f"\tif NoSwap.Surge > {cfg(i)['surge_cooldown']}",
                 "\t\tNoSwap.SurgeFrom = Player.Animation",
                 *[x for ani, surge in [("ANI_STOPPED", "IDLE"), ("ANI_WAITING", "IDLE"), ("ANI_BORED", "IDLE"),
                                        ("ANI_WALKING", "RUN"), ("ANI_RUNNING", "SPRINT"), ("ANI_PEELOUT", "SPRINT")]
                   for x in (f"\t\tif NoSwap.SurgeFrom == {ani}", f"\t\t\tPlayer.Animation = ANI_NOSWAP_SURGE_{surge}",
                             "\t\tend if")],
                 # (ifs, not a switch: the ANI_ names aren't constants here, and a case needs one)
                 "\t\tif Player.Animation == NoSwap.SurgeFrom // nothing to show in its place",
                 "\t\t\tNoSwap.SurgeFrom = -1",
                 "\t\telse",
                 "\t\t\tif Player.PrevAnimation == NoSwap.SurgeFrom // still the same: keep the Power Surge one's frame",
                 "\t\t\t\tPlayer.PrevAnimation = Player.Animation",
                 "\t\t\tend if",
                 "\t\tend if",
                 "\tend if", "end if"]
    out = []
    for i in ids:
        out += [f"if Stage.PlayerListPos == {alias(i)}", "\tif NoSwap.SurgeFrom >= 0", "\t\tPlayer.Animation = NoSwap.SurgeFrom",
                "\t\tPlayer.PrevAnimation = NoSwap.SurgeFrom", "\t\tNoSwap.SurgeFrom = -1", "\tend if", "end if"]
    functions = ("// [NoSwap] power_surge: the Power Surge idle / walk / run in place of the game's, only while animating and drawing\n"
                 "function NoSwap_SurgeIn\n" + "".join(f"\t{l}\n" for l in body) + "end function\n\n\n"
                 "function NoSwap_SurgeOut\n" + "".join(f"\t{l}\n" for l in out) + "end function\n\n\n")
    # the game's animation, while a Power Surge one is shown (-1: none): an object value no script uses between them
    t = patch(t, "#alias 5\t:\tPLAYER_AMY_A\n", "#alias 5\t:\tPLAYER_AMY_A\n"
              "#alias Object[5].Value2 : NoSwap.SurgeFrom // [NoSwap] Power Surge: the game's animation while one is shown (-1: none)\n",
              "surge alias")
    t = patch(t, "#function Player_ForceGrip\n",
              "#function Player_ForceGrip\n#function NoSwap_SurgeIn\n#function NoSwap_SurgeOut\n", "surge declarations")
    t = patch(t, "\nfunction Player_BadnikBreak\n", "\n" + functions + "function Player_BadnikBreak\n", "surge functions")
    start = t.index("sub ObjectMain\n")
    end = t.index("end sub\n", start)
    main = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_SurgeIn) // [NoSwap] Power Surge animations\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_SurgeOut)\n"), t[start:end])
    if main.count("CallFunction(NoSwap_SurgeIn)") != 2:
        sys.exit("power_surge: expected 2 ProcessAnimation calls in ObjectMain")
    t = t[:start] + main + t[end:]
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("power_surge: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n", "\tCallFunction(NoSwap_SurgeIn) // [NoSwap] Power Surge animations\n"
                        "\tDrawPlayerAnimation()\n\tCallFunction(NoSwap_SurgeOut)\n")
    return t[:start] + draw + t[end:]


def cd_copy_heads(t):
    """copy_heads (Emerl's), as abilities.copy_head_in_out: the active move's head set (its idle, stance, walk, run, peel
    out and copy flash: slots abilities.COPY_HEAD_SLOT + 1 on, cd_config.py) shown in place of the game's own, only while
    animating and drawing. The set's air switch isn't used here (CD shows the ground one: slot 46)."""
    ids = ab.copy_head_extras()
    if not ids:
        return t
    alias = lambda i: next(e["alias"] for e in EXTRAS if e["id"] == i)
    anims = [{"ANI_NOSWAP_MELEE": "46", "ANI_NOSWAP_MELEE_AIR": None}.get(a, a) for a in ab.COPY_HEAD_ANIMS]
    body_in, body_out = [], []
    for i in ids:
        head_in, head_out = ab.copy_head_lines(i, anims, ab.COPY_HEAD_SLOT + 1, "NoSwap.CopyMove", "Player.Animation",
                                               "Player.PrevAnimation")
        body_in += [f"if Stage.PlayerListPos == {alias(i)}", *["\t" + l for l in head_in], "end if"]
        body_out += [f"if Stage.PlayerListPos == {alias(i)}", *["\t" + l for l in head_out], "end if"]
    functions = (v3_function("NoSwap_CopyHeadIn", "copy_heads: the active move's head set in place of the game's "
                             "animation, only while animating and drawing", body_in)
                 + v3_function("NoSwap_CopyHeadOut", "copy_heads: the game's own animation back", body_out))
    t = patch(t, "#function Player_ForceGrip\n",
              "#function Player_ForceGrip\n#function NoSwap_CopyHeadIn\n#function NoSwap_CopyHeadOut\n",
              "copy head declarations")
    t = patch(t, "\nfunction Player_BadnikBreak\n", "\n" + functions + "function Player_BadnikBreak\n", "copy head functions")
    start = t.index("sub ObjectMain\n")
    end = t.index("end sub\n", start)
    main = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_CopyHeadIn) // [NoSwap] copy heads\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_CopyHeadOut)\n"), t[start:end])
    if main.count("CallFunction(NoSwap_CopyHeadIn)") != 2:
        sys.exit("copy_heads: expected 2 ProcessAnimation calls in ObjectMain")
    t = t[:start] + main + t[end:]
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("copy_heads: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n", "\tCallFunction(NoSwap_CopyHeadIn) // [NoSwap] copy heads\n"
                        "\tDrawPlayerAnimation()\n\tCallFunction(NoSwap_CopyHeadOut)\n")
    return t[:start] + draw + t[end:]


# ---------------------------------------------------------------- what shared scripts ask the player script
# v3 has no public values, but a stage compiles every script's functions into one list (the player script, global
# object 0, first), so a shared script can call a function the player script defines (docs/plan-b-modular-characters.md
# step 3b item 6). The ability checks in Monitor, Ring and R4/Water are such calls: each package's player script has
# only its own extra's part, NoSwap's own none (then they do nothing, as they did for every other character). The
# functions run as the calling object (Object.* is the monitor / ring / water) and only use names every script knows.
WATER_CREATEBUBBLE_1 = int(re.search(r"^#alias (\d+)\s*:\s*WATER_CREATEBUBBLE_1\s*$",
                                     (BASE / "R4" / "Water.txt").read_text(errors="ignore").replace("\r", ""), re.M).group(1))
SHARED_FUNCTIONS = ("NoSwap_SurgeMonitor", "NoSwap_RingMagnet", "NoSwap_NoBreathing")  # (and NoSwap_ShellSpikes)


def v3_function(name, comment, body):
    return f"// [NoSwap] {comment}\nfunction {name}\n" + "".join(f"\t{l}\n" for l in body) + "end function\n\n\n"


def cd_shared_functions():
    alias = lambda i: next(e["alias"] for e in EXTRAS if e["id"] == i)
    surge = []
    for i in ab.with_ability("power_surge"):
        surge += [f"if Stage.PlayerListPos == {alias(i)} // Power Surge: she zaps whatever she touches",
                  f"\tif Object[5].Value4 > {cfg(i)['surge_cooldown']} // (NoSwap.Surge)", "\t\tCheckResult = true",
                  "\tend if", "end if"]
    pull = []
    for axis in ("X", "Y"):
        v = "Object.Value0" if axis == "X" else "Object.Value1"
        pull += [f"if Object.{axis}Pos > Player.{axis}Pos",
                 f"\tif {v} > 0", f"\t\t{v} -= 0xC000", "\telse", f"\t\t{v} -= 0x3000", "\tend if",
                 "else",
                 f"\tif {v} < 0", f"\t\t{v} += 0xC000", "\telse", f"\t\t{v} += 0x3000", "\tend if",
                 "end if"]
    pull += ["Object.XPos += Object.Value0", "Object.YPos += Object.Value1"]
    magnet = []
    for i in ab.with_ability("magnetic"):
        magnet += [f"if Stage.PlayerListPos == {alias(i)} // magnetic: rings drift to her (abilities.py magnetic)",
                   "\tif Object.State == 0",
                   "\t\tPlayerObjectCollision(C_TOUCH, -64, -64, 64, 64)",
                   "\t\tif CheckResult == true",
                   "\t\t\tObject.State = 1",
                   "\t\t\tObject.Value0 = 0",
                   "\t\t\tObject.Value1 = 0",
                   "\t\tend if",
                   "\tend if",
                   "\tif Object.State == 1"] + [f"\t\t{l}" for l in pull] + ["\tend if", "end if"]
    air = []
    for i in ab.with_ability("no_breathing"):
        air += [f"if Stage.PlayerListPos == {alias(i)} // this extra doesn't breathe",
                "\tPlayer.AirTimer = 1",
                f"\tObject.State = {WATER_CREATEBUBBLE_1} // (R4/Water.txt's WATER_CREATEBUBBLE_1: the water object calls this)",
                "end if"]
    surge += touch_attack_lines("CheckResult = true", "its move breaks what it touches (Heavy's Charge)")
    return (v3_function("NoSwap_SurgeMonitor", "Global/Monitor.txt asks: CheckResult true when the extra's touch "
                        "breaks the monitor (Power Surge)", surge)
            + v3_function("NoSwap_RingMagnet", "Global/Ring.txt asks, for each ring on the player's plane: CD has no "
                          "lightning shield, so for magnetic extras a ring within 64 px starts drifting to her, with "
                          "S1/S2's lightning-shield pull (the ring's Object.State 1; its velocity in Value0 / 1, cleared "
                          "when it's collected: the sparkle counts its frames in Value0)", magnet)
            + v3_function("NoSwap_NoBreathing", "R4/Water.txt asks, underwater: extras that don't breathe (Metal) keep "
                          "the air countdown at its start", air))


def cd_spin_lean(t):
    """spin_attack's lean in CD (abilities.spin_lean_lines): the player's rotation turned by it around
    DrawPlayerAnimation only, put back right after (the game never sees it). The spin's animations (45 / 46) are drawn
    with full rotation ("rot" 1)."""
    spins = [i for i in ab.ABILITIES if ab.has(i, "spin_attack")]
    if not spins:
        return t
    body = "".join(per_extra_id("\t", i, ab.spin_lean_lines(i, v3=True)) for i in spins)
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("spin lean: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n",
                        "\tTempValue6 = 0 // [NoSwap] Spin Attack lean\n" + body + "\tTempValue7 = Player.Rotation\n"
                        "\tif TempValue6 != 0\n\t\tPlayer.Rotation += TempValue6\n\t\tPlayer.Rotation &= 511\n\tend if\n"
                        "\tDrawPlayerAnimation()\n\tPlayer.Rotation = TempValue7\n")
    return t[:start] + draw + t[end:]


def cd_float_lean(t):
    """float_lean in CD (abilities.float_lean_draw's): around DrawPlayerAnimation only, the walk / run / peel out drawn
    turned by the lean alone (no slope rotation: he floats), put back right after. TempValue4 / TempValue5 only
    (cd_spin_lean's TempValue6 / 7 live across the draw)."""
    ids = ab.float_lean_extras()
    if not ids:
        return t
    body = ""
    for i in ids:
        c = ab.ABILITIES[i]
        m = c.get("float_lean_max", 32)
        body += per_extra_id("\t", i, [
            "TempValue5 = false // [NoSwap] floating lean (build_soniccd.cd_float_lean)",
            "if Player.Animation == ANI_WALKING", "\tTempValue5 = true", "end if",
            "if Player.Animation == ANI_RUNNING", "\tTempValue5 = true", "end if",
            "if Player.Animation == ANI_PEELOUT", "\tTempValue5 = true", "end if",
            "if TempValue5 == true",
            "\tif Player.Gravity == GRAVITY_GROUND", "\t\tTempValue5 = Player.Speed", "\telse",
            "\t\tTempValue5 = Player.XVelocity", "\tend if",
            f"\tTempValue5 *= {c['float_lean']}", "\tTempValue5 /= 0x10000",
            f"\tif TempValue5 > {m}", f"\t\tTempValue5 = {m}", "\tend if",
            f"\tif TempValue5 < -{m}", f"\t\tTempValue5 = -{m}", "\tend if",
            "\tTempValue5 &= 511", "\tPlayer.Rotation = TempValue5 // the lean alone: no slope rotation",
            "end if"])
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    draw = t[start:end]
    if draw.count("\tDrawPlayerAnimation()\n") != 1:
        sys.exit("float lean: expected 1 DrawPlayerAnimation in ObjectDraw")
    draw = draw.replace("\tDrawPlayerAnimation()\n", "\tTempValue4 = Player.Rotation\n" + body
                        + "\tDrawPlayerAnimation()\n\tPlayer.Rotation = TempValue4\n")
    return t[:start] + draw + t[end:]


def sink_after(i):
    """Mephiles' Shadow Sink in CD (abilities.sink_after, the same phases in NoSwap.Sink): down + Y (a press, from the
    DLL; Y held: NoSwap.YHeld, the shot rearming with Y_REARM_HOLD) on the ground, standing, walking or crouching; held in
    the game's static state; InvincibleTimer (the post-hit one, no blink in CD) at 3 at least; slot 48's frames picked by
    the timer. Down + Y's press on the ground is taken here, so the shot below never throws on it."""
    c = cfg(i)
    shared = [m for m in SINK_VALUE4_MOVES if ab.has(i, m)]
    if shared or c.get("melee_cooldown") or ab.cycle(i) or i in ab.charge_shots() \
            or (cd_shot(i) and cd_shot(i).get("cycle")):
        sys.exit(f"sink: extra {i}: its CD value (Object[5].Value4) is also {shared or 'another move'}'s")
    frames, ticks, under, uticks, most, cool, d = ab.sink_numbers(i)
    r = ab.SINK_RISE

    def pick(ind, table):  # Player.Frame = table[TempValue1]
        out = [f"{ind}switch TempValue1"]
        for f in sorted(set(table)):
            out += [f"{ind}case {k}" for k, v in enumerate(table) if v == f] + [f"{ind}\tPlayer.Frame = {f}",
                                                                              f"{ind}\tbreak"]
        return out + [f"{ind}end switch"]
    return y_hold_lines() + [
        "if NoSwap.Sink < 0 // Shadow Sink (build_soniccd.sink_after): the cooldown", "\tNoSwap.Sink++", "end if",
        "if Player.Gravity == GRAVITY_GROUND", "\tif Player.Down == true",
        "\t\tif game.callbackParam3 == 1 // down + Y on the ground: the sink's press, never the shot's",
        "\t\t\tif NoSwap.Sink == 0",
        "\t\t\t\tTempValue0 = false // standing, walking or crouching (not rolling)",
        "\t\t\t\tCheckEqual(Player.State, Player_State_Ground)", "\t\t\t\tTempValue0 |= CheckResult",
        "\t\t\t\tCheckEqual(Player.State, Player_State_Crouch)", "\t\t\t\tTempValue0 |= CheckResult",
        "\t\t\t\tif Player.Animation == ANI_HURT", "\t\t\t\t\tTempValue0 = false", "\t\t\t\tend if",
        "\t\t\t\tif TempValue0 == true", "\t\t\t\t\tNoSwap.Sink = 1",
        "\t\t\t\t\tPlayer.State = Player_State_Static // no input, no movement, until he's risen",
        f"\t\t\t\t\tPlaySfx({c['sink_sfx_cd']}, false)", "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\t\tgame.callbackParam3 = 0 // (taken)",
        "\t\tend if", "\tend if", "end if",
        "if NoSwap.Sink > 0",
        "\tTempValue0 = true",
        "\tif Player.State != Player_State_Static // a spring, an object, a hit that got through, death: over",
        "\t\tTempValue0 = false", "\tend if",
        "\tif Player.Gravity != GRAVITY_GROUND // the ground gave way",
        "\t\tif Player.State == Player_State_Static", "\t\t\tPlayer.State = Player_State_Air",
        "\t\t\tPlayer.Animation = ANI_WALKING", "\t\tend if",
        "\t\tTempValue0 = false", "\tend if",
        "\tif TempValue0 == false", f"\t\tNoSwap.Sink = -{cool}",
        "\t\tif Player.Animation == ANI_NOSWAP_SINK", "\t\t\tPlayer.Animation = ANI_WALKING", "\t\tend if",
        "\telse",
        "\t\tPlayer.Speed = 0", "\t\tPlayer.XVelocity = 0", "\t\tPlayer.YVelocity = 0",
        "\t\tif Player.InvincibleTimer < 3 // nothing hurts him (the post-hit timer; no BlinkTimer: no flicker)",
        "\t\t\tPlayer.InvincibleTimer = 3", "\t\tend if",
    ] + (["\t\tNoSwap.ShotPose = 0 // (no throw pose over it)"] if cd_shot(i) else []) + [
        f"\t\tif NoSwap.Sink < {r}",
        "\t\t\tTempValue1 = true // both still held?",
        "\t\t\tif NoSwap.YHeld == 0", "\t\t\t\tTempValue1 = false", "\t\t\tend if",
        "\t\t\tif Player.Down == false", "\t\t\t\tTempValue1 = false", "\t\t\tend if",
        "\t\t\tif TempValue1 == false // let go: he rises, from where he is",
        f"\t\t\t\tif NoSwap.Sink > {d}", f"\t\t\t\t\tNoSwap.Sink = {r + d}", "\t\t\t\telse",
        f"\t\t\t\t\tNoSwap.Sink += {r}", "\t\t\t\tend if",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tPlayer.Animation = ANI_NOSWAP_SINK",
        f"\t\tif NoSwap.Sink <= {d} // sinking",
        "\t\t\tTempValue1 = NoSwap.Sink", "\t\t\tTempValue1--", f"\t\t\tTempValue1 /= {ticks}",
    ] + pick("\t\t\t", frames) + [
        "\t\t\tNoSwap.Sink++",
        "\t\telse",
        f"\t\t\tif NoSwap.Sink < {r} // under",
        "\t\t\t\tTempValue1 = NoSwap.Sink", f"\t\t\t\tTempValue1 -= {d + 1}", f"\t\t\t\tTempValue1 /= {uticks}",
        f"\t\t\t\tTempValue1 %= {len(under)}",
    ] + pick("\t\t\t\t", under) + [
        "\t\t\t\tNoSwap.Sink++",
        f"\t\t\t\tif NoSwap.Sink > {d + most} // time's up: he rises", f"\t\t\t\t\tNoSwap.Sink = {r + d}",
        "\t\t\t\tend if",
        "\t\t\telse // rising: the sink's frames backward",
        "\t\t\t\tTempValue1 = NoSwap.Sink", f"\t\t\t\tTempValue1 -= {r + 1}", f"\t\t\t\tTempValue1 /= {ticks}",
    ] + pick("\t\t\t\t", frames) + [
        "\t\t\t\tNoSwap.Sink--",
        "\t\t\tend if",
        "\t\tend if",
        "\t\tPlayer.PrevAnimation = Player.Animation // the timer picks the frame",
        "\t\tPlayer.AnimationTimer = 0",
        f"\t\tif NoSwap.Sink == {r} // risen",
        f"\t\t\tNoSwap.Sink = -{cool}", "\t\t\tPlayer.State = Player_State_Ground", "\t\t\tPlayer.Animation = ANI_STOPPED",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def cd_surge_monitor(t):
    """Monitors: a Power Surge breaks them on touch (the Amy hammer check's place): the player script's
    NoSwap_SurgeMonitor."""
    anchor = ("\t\t\tif Stage.PlayerListPos == PLAYER_AMY\n\t\t\t\tif Player.Animation == ANI_HAMMER_JUMP\n"
              "\t\t\t\t\tCheckResult = true\n\t\t\t\tend if\n\t\t\t\tif Player.Animation == ANI_HAMMER_DASH\n"
              "\t\t\t\t\tCheckResult = true\n\t\t\t\tend if\n\t\t\tend if\n")
    return patch(t, anchor, anchor + "\t\t\tCallFunction(NoSwap_SurgeMonitor) // [NoSwap] the extra's touch breaks it too "
                 "(Power Surge; its player script's)\n", "surge monitor")


def cd_magnet_ring(t):
    """Rings: magnetic extras pull them in (the player script's NoSwap_RingMagnet); a collected ring's pull is cleared."""
    anchor = "\t\tif Player.CollisionPlane == Object.DrawingPlane\n\n"
    t = patch(t, anchor, anchor + "\t\t\tCallFunction(NoSwap_RingMagnet) // [NoSwap] a magnetic extra pulls it in "
              "(its player script's)\n\n", "magnet pull")
    anchor = "\t\t\t\tObject.Type = TypeName[Ring Sparkle]\n"
    return patch(t, anchor, anchor + "\t\t\t\tObject.State = 0 // [NoSwap] (a magnetic extra's pull)\n"
                 "\t\t\t\tObject.Value0 = 0\n\t\t\t\tObject.Value1 = 0\n", "magnet collect")


def cd_cycle_gate(i, move, lines):
    """ability_cycle (abilities.cycle_gate): `lines` run only while `move` is the extra's active one."""
    moves = ab.cycle(i)
    if move not in moves or not lines:
        return lines
    return ([f"if NoSwap.CopyMove == {moves.index(move)} // ability_cycle: only while {move} is the active move"]
            + ["\t" + l if l else l for l in lines] + ["end if"])


def cd_cycle_next(i):
    """ability_cycle (abilities.cycle_next), in NoSwap_Shot<i> as the melee starts: the next move is active; in the air the
    move used this jump ends."""
    n = len(ab.cycle(i))
    return ("" if not n else "\n\t\tNoSwap.CopyMove++ // ability_cycle: the next move\n"
            f"\t\tif NoSwap.CopyMove >= {n}\n\t\t\tNoSwap.CopyMove = 0\n\t\tend if\n"
            "\t\tif Player.Gravity == GRAVITY_AIR\n\t\t\tif NoSwap.Ability != 0\n"
            "\t\t\t\tNoSwap.Ability = -1 // the move used this jump ends\n\t\t\tend if\n\t\tend if")


def cd_functions():
    out = ["// [NoSwap] Ability moves for extra characters (generated by tools/build_soniccd.py)\n"]
    triples = [i for i in ab.ABILITIES if ab.has(i, "triple_jump")]
    if triples:
        out.append("// Runs in Player_Action_Jump once a jump is sure: a jump that's part of a chain (a higher jump strength)\n"
                   "function NoSwap_JumpStart\n" + "".join(per_extra_id("\t", i, triple_jump_start(i)) for i in triples)
                   + "end function\n\n\n"
                   "// ...and after it has used the strength: his own back\n"
                   "function NoSwap_JumpEnd\n" + "".join(per_extra_id("\t", i, ["Player.JumpStrength = NoSwap.JumpSave"])
                                                         for i in triples)
                   + "end function\n\n\n")
    for i in ab.ABILITIES:
        c = cfg(i)
        if ab.has(i, "jet_dash"):
            out.append(f"""function NoSwap_JetDashSpeed{i}
	TempValue0 = Player.XVelocity
	if Player.Direction != FACING_RIGHT
		FlipSign(TempValue0)
	end if
	if TempValue0 < {c['dash_speed']:#x}
		TempValue0 = {c['dash_speed']:#x}
	end if
	Player.XVelocity = TempValue0
	if Player.Direction != FACING_RIGHT
		FlipSign(Player.XVelocity)
	end if
	Player.Speed = Player.XVelocity
end function


// Jet Dash: jump in mid-air
function NoSwap_JetDash{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {c['dash_frames']}
			Player.Animation = ANI_NOSWAP_ATTACK
			Player.YVelocity = 0
			CallFunction(NoSwap_JetDashSpeed{i})
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "ear_grapple"):
            tips = "".join(f"\tcase {k}\n\t\tTempValue1 = {x}\n\t\tTempValue2 = {y}\n\t\tbreak\n"
                           for k, (x, y) in enumerate(c["grapple_tip"]))
            start = (f"""			NoSwap.Ability = -1 // grapple_y: the Ear Copter opens at once (NoSwap_AirAbilities keeps it open)
			Player.Animation = ANI_NOSWAP_HOVER
			Player.YVelocity = {c.get('hover_sink', 0):#x}
			PlaySfx(SFX_G_FLYING, false)
""" if c.get("grapple_y") else """			NoSwap.Ability = 1
			Player.Animation = ANI_NOSWAP_ATTACK
			NoSwap.GrappleDir = Player.Direction
			PlaySfx(SFX_G_RELEASE, false)
""")
            out.append(f"""// Ear Grapple: jump in mid-air (with grapple_y: Y in mid-air, NoSwap_AfterUpdate, and jump opens the Ear
// Copter). The reel and the Ear Copter are in NoSwap_AirAbilities, the ear itself in NoSwap_AfterUpdate (abilities.py
// ear_grapple). Ability: 1-{len(c['grapple_tip'])} the ear going out (its frame + 1), 101+ latched and reeling in
// (frames + 100), 201+ snapping back (frames left + 200)
function NoSwap_EarGrapple{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
{start}		end if
	end if
end function


// The ear's tip in frame TempValue4, px from his centre: TempValue1 (mirrored facing left), TempValue2
function NoSwap_GrappleTip{i}
	switch TempValue4
{tips}	end switch
	if NoSwap.GrappleDir == FACING_LEFT
		FlipSign(TempValue1)
	end if
end function


""")
        if ab.has(i, "rocket_ride"):
            out.append(f"""// Rocket Ride: jump in mid-air: he rides a rocket ahead, then it blows up and launches him (in
// NoSwap_AirAbilities; the frames and the blast's reach in NoSwap_AfterUpdate; tools/abilities.py rocket_ride)
function NoSwap_RocketRide{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {c['ride_frames'] + c['blast_frames']}
			Player.Animation = ANI_NOSWAP_ATTACK
			TempValue0 = Player.XVelocity // at least ride_speed the way he faces (his own speed, if faster)
			if Player.Direction == FACING_LEFT
				FlipSign(TempValue0)
			end if
			if TempValue0 < {c['ride_speed']:#x}
				TempValue0 = {c['ride_speed']:#x}
			end if
			if Player.Direction == FACING_LEFT
				FlipSign(TempValue0)
			end if
			Player.XVelocity = TempValue0
			Player.Speed = Player.XVelocity
			Player.YVelocity = -{c['ride_rise']:#x}
			PlaySfx({c['ride_sfx_cd']}, false)
		end if
	end if
end function


""")
        if ab.has(i, "pogo"):
            out.append(f"""// Pogo: jump in mid-air; bounces on landing are in NoSwap_AfterUpdate
function NoSwap_Pogo{i}
	if Player.JumpPress == true
		Player.Animation = ANI_NOSWAP_ATTACK
		NoSwap.Pogo = true
	end if
end function


""")
        if ab.has(i, "umbrella"):
            out.append(f"""// Umbrella: jump in mid-air, float down while jump is held (once per jump)
function NoSwap_Umbrella{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {ab.umbrella_open(i)}
			Player.Animation = {ab.umbrella_anim(i)}
		end if
	end if
end function


""")
        if ab.has(i, "chaos_control"):
            out.append(f"""// Chaos Control: jump in mid-air: a flash, a warp dash, a hop (in NoSwap_AirAbilities)
function NoSwap_ChaosControl{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {c['chaos_freeze'] + c['chaos_warp']}
			Player.Animation = ANI_NOSWAP_ATTACK
			Player.XVelocity = 0
			Player.YVelocity = 0
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "aim_dash") and not c.get("aim_dash_y"):
            out.append(f"""// Burst Dash: jump in mid-air; up or down held aims it 45 degrees (Ability: frames + 100 up / + 200 down,
// + 1000 if started facing left: the dash keeps its direction)
function NoSwap_AimDash{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
{indented(aim_dash_start(i), 3)}		end if
	end if
end function


""")
        if ab.has(i, "hammer_drop"):
            out.append(f"""// Hammer Drop (Mania Plus): jump in mid-air to drop fast; the landing bounce is in NoSwap_AfterUpdate
function NoSwap_HammerDrop{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = 1
			Player.XVelocity >>= 1
			Player.YVelocity = 0xC0000
			Player.Animation = ANI_NOSWAP_ATTACK
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "ray_glide"):
            out.append(f"""// Glide (Mania Plus): jump in mid-air to fly; the flight is in NoSwap_AfterUpdate. While gliding,
// Ability holds the glide's angle (0x10-0x70) and Shot packs swooping up (1), facing left (2) and the
// swoop power (x4). Holding forward starts in a dive, otherwise in a swoop up.
function NoSwap_RayGlide{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			TempValue0 = Player.XVelocity
			TempValue1 = TempValue0
			TempValue1 >>= 3
			TempValue0 -= TempValue1
			TempValue2 = 0 // flags
			if Player.Direction == FACING_LEFT
				TempValue2 = 2
				if TempValue0 > -0x30000
					TempValue0 = -0x30000
				end if
				TempValue3 = Player.Left
			else
				if TempValue0 < 0x30000
					TempValue0 = 0x30000
				end if
				TempValue3 = Player.Right
			end if
			NoSwap.GlideLift = 0
			if TempValue3 == false // not holding forward: swoop up
				TempValue2 |= 1
				TempValue0 >>= 1
				TempValue1 = TempValue0
				if TempValue1 < 0
					FlipSign(TempValue1)
				end if
				TempValue3 = TempValue1
				TempValue3 >>= 1
				TempValue4 = TempValue1
				TempValue4 >>= 2
				TempValue3 += TempValue4
				TempValue4 = TempValue1
				TempValue4 >>= 4
				TempValue3 += TempValue4
				FlipSign(TempValue3)
				NoSwap.GlideLift = TempValue3
			end if
			TempValue2 += 1024 // swoop power 256
			NoSwap.Shot = TempValue2
			Player.XVelocity = TempValue0
			Player.YVelocity >>= 1
			NoSwap.GlideVX = Player.XVelocity
			NoSwap.GlideVY = Player.YVelocity
			NoSwap.GlideCap = TempValue0
			if NoSwap.GlideCap < 0
				FlipSign(NoSwap.GlideCap)
			end if
			NoSwap.Ability = 0x40
			Player.Animation = ANI_NOSWAP_GLIDE_DOWN
			TempValue0 = NoSwap.Shot
			TempValue0 &= 1
			if TempValue0 == 1
				Player.Animation = ANI_NOSWAP_GLIDE_UP
			end if
		end if
	end if
end function


""")
        if ab.has(i, "spirit_flight"):
            out.append(f"""// Spirit Flight: jump in mid-air to turn into a spirit orb and fly where the d-pad points (in
// NoSwap_AirAbilities; the transform's frames in NoSwap_AfterUpdate). Ability: game frames left, the transform
// then the flight ({c['spirit_frames']} and under); -1 used (abilities.py spirit_flight)
function NoSwap_SpiritFlight{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {ab.spirit_total(i)}
			Player.Animation = ANI_NOSWAP_ATTACK
			Player.Speed = 0 // held still while she transforms
			Player.XVelocity = 0
			Player.YVelocity = 0
			NoSwap.SpiritVX = 0
			NoSwap.SpiritVY = 0
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "rocket_burst"):
            out.append(f"""// Rocket Burst: jump in mid-air and keep holding it to charge the rocket pack; letting go fires it (in
// NoSwap_AirAbilities; the frames in NoSwap_AfterUpdate). Ability: {ab.ROCKET_CHARGING} + frames charging, 1.. the burst's
// or the spin's frames left, -1 used (abilities.py rocket_burst)
function NoSwap_RocketBurst{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {ab.ROCKET_CHARGING}
			Player.Animation = ANI_NOSWAP_ATTACK
			NoSwap.RocketVX = 0
			NoSwap.RocketVY = 0
		end if
	end if
end function


""")
        if ab.has(i, "double_jump"):
            out.append(f"""// Double Jump: jump in mid-air: a second jump, keeping her speed along, in the shell spin (an attack) until she
// starts falling (NoSwap_AfterUpdate; abilities.py double_jump). Ability: 1 used, until she lands
function NoSwap_DoubleJump{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = 1
			TempValue0 = Player.JumpStrength
			TempValue0 *= {ab.double_jump_scale(i)} // x{c['double_jump']}
			TempValue0 >>= 8
			FlipSign(TempValue0)
			Player.YVelocity = TempValue0
			Player.Animation = ANI_NOSWAP_ATTACK
			PlaySfx(SFX_G_JUMP, false)
		end if
	end if
end function


""")
        if ab.has(i, "thunder_zip"):
            out.append(f"""// Thunder Zip: jump in mid-air: a blink-dash forward in a flash (an attack; the zip is in NoSwap_AirAbilities,
// abilities.py thunder_zip). Ability: frames of the pose left; ZipCarry: her forward speed, or zip_carry if that's
// faster, signed for the zip's direction
function NoSwap_ThunderZip{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {c['zip_pose']}
			Player.Animation = ANI_NOSWAP_ATTACK
			TempValue0 = Player.XVelocity
			if Player.Direction != FACING_RIGHT
				FlipSign(TempValue0)
			end if
			if TempValue0 < {c['zip_carry']:#x}
				TempValue0 = {c['zip_carry']:#x}
			end if
			if Player.Direction != FACING_RIGHT
				FlipSign(TempValue0)
			end if
			NoSwap.ZipCarry = TempValue0
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "extreme_gear"):
            out.append(f"""// Extreme Gear: jump in mid-air to snap onto his board (an attack: it rams badniks) and surf while jump is
// held (in NoSwap_AirAbilities; landing and walls in NoSwap_AfterUpdate; abilities.py extreme_gear). Ability: 1 riding,
// -1 used; GlideVX: the board's velocity, at least gear_speed forward (more if he's faster); GlideLift: lift frames left;
// GlideVY: ride frames left (gear_frames)
function NoSwap_ExtremeGear{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = 1
			Player.Animation = ANI_NOSWAP_ATTACK
			TempValue0 = Player.XVelocity
			if Player.Direction != FACING_RIGHT
				FlipSign(TempValue0)
			end if
			if TempValue0 < {c['gear_speed']:#x}
				TempValue0 = {c['gear_speed']:#x}
			end if
			if Player.Direction != FACING_RIGHT
				FlipSign(TempValue0)
			end if
			NoSwap.GlideVX = TempValue0
			Player.XVelocity = TempValue0
			Player.Speed = TempValue0
			if Player.YVelocity > 0 // onto the board: no falling, half a rise
				Player.YVelocity = 0
			else
				Player.YVelocity >>= 1
			end if
			NoSwap.GlideLift = {c['gear_lift_frames']}
			NoSwap.GlideVY = {c['gear_frames']} // the ride's length at most
			PlaySfx(SFX_G_RELEASE, false)
		end if
	end if
end function


""")
        if ab.has(i, "wall_cling"):
            out.append(f"""// Wall Cling: is there a wall right beside her on side TempValue0 (FACING_RIGHT: her right)? TempValue1: the
// answer. Tested where Knuckles' glide grabs a wall, on a stand-in position in Object.XPos / YPos, as the glide does.
function NoSwap_WallBeside{i}
	TempValue6 = Object.XPos
	TempValue7 = Object.YPos
	Object.XPos = Player.XPos
	Object.YPos = Player.YPos
	CheckResult = false
	if TempValue0 == FACING_RIGHT
		ObjectTileCollision(CSIDE_LWALL, {ab.WALL_X}, {ab.WALL_Y}, Player.CollisionPlane)
	else
		ObjectTileCollision(CSIDE_RWALL, -{ab.WALL_X}, {ab.WALL_Y}, Player.CollisionPlane)
	end if
	TempValue1 = CheckResult
	Object.XPos = TempValue6
	Object.YPos = TempValue7
end function


""")
        if ab.has(i, "screw_kick") and c.get("kick_jump"):  # Mecha's Spike Ball: the kick started by jump
            out.append(f"""// Spike Ball: jump in mid-air, once per jump (a Screw Kick started by jump; abilities.py kick_jump)
function NoSwap_ScrewKick{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
""" + "".join(f"\t\t\t{l}\n" for l in screw_kick_go(i)) + """		end if
	end if
end function


""")
        if ab.has(i, "puddle_slide"):
            out.append(f"""// Puddle Slide: jump in mid-air: a drop in the dive (an attack); landing from it, the puddle (NoSwap_AfterUpdate;
// abilities.py puddle_slide). Ability: 1 dropping
function NoSwap_PuddleSlide{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = 1
			if Player.YVelocity < {c['puddle_drop']:#x}
				Player.YVelocity = {c['puddle_drop']:#x}
			end if
			Player.Animation = ANI_NOSWAP_ATTACK
		end if
	end if
end function


""")
        if ab.has(i, "ground_slide"):
            if ab.has(i, "pogo") or ab.has(i, "puddle_slide"):
                sys.exit(f"ground_slide: extra {i}: NoSwap.Slide is NoSwap.Pogo's value, and the Puddle Slide's code is its own")
            out.append(f"""// Ground Slide: down + jump on the ground, instead of the Spin Dash (its ActionSpindash; abilities.py
// ground_slide): the slide (NoSwap_AfterUpdate, puddle_after's ground part)
function NoSwap_GroundSlide{i}
	Player.State = Player_State_Ground
	Player.Timer = 0
	NoSwap.Slide = {c['puddle_ticks'] * len(c['puddle_frames'])}
	PlaySfx({c['puddle_sfx_cd']}, false)
end function


""")
        if ab.has(i, "phase_warp"):
            out.append(phase_warp_functions(i))
        if cd_melee(i):
            ticks = c["melee_ticks"]
            total = ticks * len(c["melee_reach"])
            if cd_variants(i):  # (melee_run / melee_up: the longest pose's)
                total = ticks * max(len(r) for r, _ in cd_variant_layout(i))
            cooldown = c.get("melee_cooldown", 0)  # Espio's Leaf Swirl: a wait before the next one
            cd_ready = "\n\t\tif NoSwap.Cooldown == 0" if cooldown else ""
            cd_fire = f"\n\t\tNoSwap.Cooldown = {cooldown}" if cooldown else ""
            cd_ready_end = "\n\t\tend if" if cooldown else ""
            out.append(f"""// Shot: look up + jump (the peel-out input)
function NoSwap_Shot{i}
	if NoSwap.Shot == 0{cd_ready}
		NoSwap.Shot = {total}{cd_fire}{cd_variant_start(i) if cd_variants(i) else ""}
		{cd_melee_sfx(i)}{cd_ready_end}{cd_cycle_next(i)}
	end if
end function


""")
        if ab.cycle(i):
            calls = "".join(f"\tif NoSwap.CopyMove == {k}\n\t\tCallFunction(NoSwap_{ab.CYCLE_MOVES[m][0]}{i})\n\tend if\n"
                            for k, m in enumerate(ab.cycle(i)))
            out.append(f"// ability_cycle: the jump ability, the active move's (NoSwap.CopyMove: Y picks the next)\n"
                       f"function NoSwap_Copycat{i}\n{calls}end function\n\n\n")
    # Every frame in the air, before the player's state runs
    air = []
    for i in ab.ABILITIES:
        c = cfg(i)
        body = []
        if ab.has(i, "water_swim"):  # (before the jump ability's own air code)
            body += swim_air(i)
        n0 = len(body)
        if ab.has(i, "jet_dash"):
            hover_end = -(c["hover_frames"] + 1) if ab.has(i, "hover") else -1
            body += [
                "if NoSwap.Ability > 0",
                "\tif Player.Animation == ANI_NOSWAP_ATTACK",
                "\t\tPlayer.YVelocity = 0",
                f"\t\tCallFunction(NoSwap_JetDashSpeed{i})",
                "\t\tNoSwap.Ability--",
                "\t\tif NoSwap.Ability == 0",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\telse",
                f"\t\tNoSwap.Ability = {hover_end}",
                "\tend if",
                "else",
                "\tif NoSwap.Ability < 0",
                "\t\tTempValue0 = false",
            ]
            if ab.has(i, "hover"):
                body += ["\t\tif Player.JumpHold == true", f"\t\t\tif NoSwap.Ability > {hover_end}", "\t\t\t\tTempValue0 = true",
                         "\t\t\tend if", "\t\tend if"]
            body += [
                "\t\tif Player.Animation == ANI_HURT", "\t\t\tTempValue0 = false", "\t\tend if",
                "\t\tif TempValue0 == true",
                "\t\t\tif Player.Animation != ANI_NOSWAP_HOVER", "\t\t\t\tPlaySfx(SFX_G_FLYING, false)", "\t\t\tend if",
                "\t\t\tPlayer.Animation = ANI_NOSWAP_HOVER",
                f"\t\t\tPlayer.YVelocity = {c.get('hover_sink', 0):#x}",
                "\t\t\tNoSwap.Ability--",
                "\t\telse",
                "\t\t\tif Player.Animation == ANI_NOSWAP_HOVER",
                "\t\t\t\tPlayer.Animation = ANI_JUMPING",
                f"\t\t\t\tNoSwap.Ability = {hover_end}",
                "\t\t\tend if",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
            body[n0:] = cd_cycle_gate(i, "jet_dash", body[n0:])
        if ab.has(i, "rocket_ride"):  # (abilities.py rocket_ride_air: the same ride, blast and parachute)
            hover_end = -(c["hover_frames"] + 1) if ab.has(i, "hover") else -1
            blast, speed = c["blast_frames"], c["ride_speed"]
            body += [
                "if NoSwap.Ability > 0",
                "\tif Player.Animation == ANI_NOSWAP_ATTACK",
                f"\t\tif NoSwap.Ability > {blast} // riding the rocket",
                "\t\t\tTempValue0 = Player.XVelocity // his speed along, whichever way",
                "\t\t\tTempValue1 = false",
                "\t\t\tif TempValue0 < 0",
                "\t\t\t\tFlipSign(TempValue0)",
                "\t\t\t\tTempValue1 = true",
                "\t\t\tend if",
                f"\t\t\tif TempValue0 < {speed // 2:#x} // a wall stopped him: it blows up now",
                f"\t\t\t\tNoSwap.Ability = {blast + 1}",
                "\t\t\telse",
                f"\t\t\t\tif TempValue0 < {speed:#x} // full speed for the whole ride",
                f"\t\t\t\t\tTempValue0 = {speed:#x}",
                "\t\t\t\tend if",
                "\t\t\t\tif TempValue1 == true",
                "\t\t\t\t\tFlipSign(TempValue0)",
                "\t\t\t\tend if",
                "\t\t\t\tPlayer.XVelocity = TempValue0",
                f"\t\t\t\tPlayer.YVelocity = -{c['ride_rise']:#x}",
                "\t\t\tend if",
                "\t\tend if",
                "\t\tNoSwap.Ability--",
                f"\t\tif NoSwap.Ability == {blast} // the blast",
                f"\t\t\tPlayer.YVelocity = -{c['blast_launch']:#x}",
                "\t\t\tPlayer.XVelocity >>= 1",
                "\t\t\tPlayer.Speed = Player.XVelocity",
                "\t\t\tPlayer.Timer = 0 // as after a spring: letting go of jump doesn't cut the launch short",
                "\t\t\tPlaySfx(SFX_G_EXPLOSION, false)",
                "\t\tend if",
                "\t\tif NoSwap.Ability == 0",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\telse",
                f"\t\tNoSwap.Ability = {hover_end}",
                "\tend if",
                "else",
            ] + falling_hover(i) + ["end if"]
        if ab.has(i, "ear_grapple"):
            body += grapple_air(i)
        if ab.has(i, "umbrella"):
            sink = c["umbrella_sink"]
            n0 = len(body)
            body += [
                f"if NoSwap.Ability {ab.umbrella_is_open(i)}",
                f"\tif Player.Animation != {ab.umbrella_anim(i)}",
                "\t\tNoSwap.Ability = 2",
                "\telse",
                "\t\tif Player.JumpHold == true",
                f"\t\t\tif Player.YVelocity > {sink:#x}",
                f"\t\t\t\tPlayer.YVelocity = {sink:#x}",
                "\t\t\tend if",
            ] + ([
                "\t\t\tNoSwap.Ability--",
                "\t\t\tif NoSwap.Ability == 2 // out of time",
                "\t\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\t\tend if",
            ] if c.get("float_frames") else []) + [
                "\t\telse",
                "\t\t\tNoSwap.Ability = 2",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
            body[n0:] = cd_cycle_gate(i, "umbrella", body[n0:])
        if ab.has(i, "chaos_control"):
            body += [
                "if NoSwap.Ability > 0",
                "\tif Player.Animation == ANI_NOSWAP_ATTACK",
                "\t\tPlayer.YVelocity = 0",
                f"\t\tif NoSwap.Ability > {c['chaos_warp']}",
                "\t\t\tPlayer.XVelocity = 0 // the flash",
                "\t\telse",
                f"\t\t\tPlayer.XVelocity = {c['chaos_speed']:#x} // the warp",
                "\t\t\tif Player.Direction != FACING_RIGHT",
                "\t\t\t\tFlipSign(Player.XVelocity)",
                "\t\t\tend if",
                "\t\tend if",
                "\t\tPlayer.Speed = Player.XVelocity",
                "\t\tNoSwap.Ability--",
                "\t\tif NoSwap.Ability == 0",
                "\t\t\tNoSwap.Ability = -1",
                f"\t\t\tPlayer.YVelocity = -{c['chaos_pop']:#x} // the hop",
                "\t\tend if",
                "\telse",
                "\t\tNoSwap.Ability = -1",
                "\tend if",
                "else",
                "\tif NoSwap.Ability < 0",
                "\t\tif Player.Animation == ANI_NOSWAP_ATTACK",
                "\t\t\tif Player.YVelocity >= 0",
                "\t\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\t\tend if",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
        if ab.has(i, "hammer_drop"):
            body += [
                "if NoSwap.Ability == 1",
                "\tif Player.Animation != ANI_NOSWAP_ATTACK",
                "\t\tNoSwap.Ability = -1",
                "\telse",
                "\t\tif Player.YVelocity <= 0x10000 // a spring or anything else sending him up ends it",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
        if ab.has(i, "puddle_slide"):
            body += [
                "if NoSwap.Ability == 1",
                "\tif Player.Animation != ANI_NOSWAP_ATTACK",
                "\t\tNoSwap.Ability = -1 // hurt...",
                "\telse",
                "\t\tif Player.YVelocity <= 0x10000 // a spring, a badnik bounce or anything else sending him up ends it",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
        if ab.has(i, "aim_dash"):
            body += [
                "if NoSwap.Ability > 0",
                "\tif Player.Animation == ANI_NOSWAP_ATTACK",
                "\t\tTempValue2 = NoSwap.Ability // without the facing",
                "\t\tTempValue2 %= 1000",
                "\t\tif TempValue2 > 200",
                f"\t\t\tPlayer.XVelocity = {c['diag_x']:#x}",
                f"\t\t\tPlayer.YVelocity = {c['diag_y']:#x}",
                "\t\telse",
                "\t\t\tif TempValue2 > 100",
                f"\t\t\t\tPlayer.XVelocity = {c.get('up_x', c['diag_x']):#x}",
                f"\t\t\t\tPlayer.YVelocity = -{c.get('up_y', c['diag_y']):#x}",
                "\t\t\telse",
                "\t\t\t\tTempValue1 = Player.XVelocity",
                "\t\t\t\tif TempValue1 < 0",
                "\t\t\t\t\tFlipSign(TempValue1)",
                "\t\t\t\tend if",
                f"\t\t\t\tif TempValue1 < {c['dash_speed']:#x}",
                f"\t\t\t\t\tTempValue1 = {c['dash_speed']:#x}",
                "\t\t\t\tend if",
                "\t\t\t\tPlayer.XVelocity = TempValue1",
                "\t\t\t\tPlayer.YVelocity = 0",
                "\t\t\tend if",
                "\t\tend if",
                "\t\tif NoSwap.Ability > 1000 // locked to the direction it started in",
                "\t\t\tFlipSign(Player.XVelocity)",
                "\t\t\tPlayer.Direction = FACING_LEFT",
                "\t\telse",
                "\t\t\tPlayer.Direction = FACING_RIGHT",
                "\t\tend if",
                "\t\tPlayer.Speed = Player.XVelocity",
                "\t\tNoSwap.Ability--",
                "\t\tTempValue1 = NoSwap.Ability",
                "\t\tTempValue1 %= 100",
                "\t\tif TempValue1 == 0",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\tend if",
                "\telse",
                "\t\tNoSwap.Ability = -1",
                "\tend if",
                "end if",
            ]
            if c.get("aim_dash_y"):
                body += ["if NoSwap.Flown == true // the Stinger ended his flight: it doesn't start again this jump",
                         "\tPlayer.JumpPress = false", "end if"]
        if ab.has(i, "screw_kick"):
            n0 = len(body)
            body += [
                "if NoSwap.Ability > 0",
                "\tif Player.Animation != ANI_NOSWAP_ATTACK",
                "\t\tNoSwap.Ability = -1 // hurt...",
                "\telse",
                "\t\tif Player.YVelocity <= 0x10000 // a spring or anything else sending her up ends it",
                "\t\t\tNoSwap.Ability = -1",
                "\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\telse",
                f"\t\t\tPlayer.XVelocity = {c['kick_x']:#x}",
                "\t\t\tPlayer.Direction = FACING_RIGHT",
                "\t\t\tif NoSwap.Ability == 2",
                "\t\t\t\tFlipSign(Player.XVelocity)",
                "\t\t\t\tPlayer.Direction = FACING_LEFT",
                "\t\t\tend if",
                "\t\t\tPlayer.Speed = Player.XVelocity",
                f"\t\t\tPlayer.YVelocity = {c['kick_y']:#x}",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
            body[n0:] = cd_cycle_gate(i, "screw_kick", body[n0:])
        if ab.has(i, "spirit_flight"):
            body += spirit_air(i)
        if ab.has(i, "rocket_burst"):
            body += rocket_air(i)
        if ab.has(i, "wall_cling"):
            body += wall_cling_air(i)
        if ab.has(i, "thunder_zip"):
            body += thunder_zip_air(i)
        if ab.has(i, "extreme_gear"):
            body += extreme_gear_air(i)
        if ab.has(i, "phase_warp"):
            body += phase_warp_air(i)
        if i in ab.sparks():  # the charge's Shine Spark: its flight
            body += spark_air_cd(i)
        if body:
            air.append((i, body))
    out.append("// [NoSwap] Every frame in the air, before the player's state runs\nfunction NoSwap_AirAbilities\n")
    out += [per_extra_id("\t", i, body) for i, body in air]
    out.append("end function\n\n\n")

    # Every frame after the player has moved and landed
    after = []
    for i in ab.ABILITIES:
        c = cfg(i)
        body = []
        if ab.has(i, "triple_jump"):
            body += triple_jump_after(i)
        if ab.has(i, "hammer_drop"):  # before the fresh-jump reset below (a slam shot goes out as he lands)
            k = HAMMER_AFTER.index("\t\tif Player.Animation == ANI_NOSWAP_ATTACK") + 1
            body += HAMMER_AFTER[:k] + (slam_spawn_cd(i) if ab.slam_shot(i) else []) + HAMMER_AFTER[k:]
        if ab.has(i, "puddle_slide"):  # before the fresh-jump reset below, and the melee
            body += puddle_after(i)
        if ab.has(i, "ground_slide"):  # (Ray Poward's Slide: the puddle's ground part)
            body += puddle_after(i, ground=True)
            if ab.has(i, "no_stomp"):
                body += cd_no_stomp_slide(i)
        if ab.has(i, "ray_glide"):
            body += RAY_AFTER
        if ab.has(i, "screw_kick"):
            body += cd_cycle_gate(i, "screw_kick", screw_kick_after(i))
        if ab.has(i, "rocket_ride"):  # the timer picks the frame (the rocket, then the blasts); the blast reaches all around
            blast = c["blast_frames"]
            body += [
                "NoSwap.Reach = 0",
                "if NoSwap.Ability > 0",
                "\tif Player.Animation == ANI_NOSWAP_ATTACK",
                "\t\tTempValue0 = 0 // the rocket",
                f"\t\tif NoSwap.Ability <= {blast}",
                f"\t\t\tNoSwap.Reach = {BLAST_OUT[i]}",
                f"\t\t\tTempValue0 = {blast}",
                "\t\t\tTempValue0 -= NoSwap.Ability",
                f"\t\t\tTempValue0 /= {c['blast_ticks']}",
                "\t\t\tTempValue0++",
                "\t\tend if",
                "\t\tPlayer.Frame = TempValue0",
                "\t\tPlayer.AnimationTimer = 0",
                "\tend if",
                "end if",
            ]
        if c.get("grapple_y"):  # before grapple_after, which tests the ear's first frame
            body += grapple_y_start(i)
        if ab.has(i, "ear_grapple"):  # before the fresh-jump reset below
            body += grapple_after(i)
        if ab.has(i, "spirit_flight"):  # before the fresh-jump reset below
            body += spirit_after(i)
        if ab.has(i, "rocket_burst"):  # before the fresh-jump reset below
            body += rocket_after(i)
        if ab.has(i, "extreme_gear"):  # before the fresh-jump reset below
            body += extreme_gear_after(i)
        if ab.has(i, "double_jump") or ab.has(i, "wall_cling"):  # (the Double Jump's spin)
            body += cd_cycle_gate(i, "double_jump", DOUBLE_JUMP_AFTER)
        if ab.has(i, "wall_cling"):
            body += wall_cling_after(i)
        body += ["if Player.Gravity == GRAVITY_GROUND", "\tif NoSwap.Pogo == false", "\t\tNoSwap.Ability = 0 // a fresh jump", "\tend if", "end if"]
        if c.get("aim_dash_y"):
            # Y in mid-air (from the DLL; there's no look up + jump in the air) starts the aimed dash, once per
            # airborne period. Out of Tails' flight it's for good: NoSwap_AirAbilities then eats jump presses,
            # so the flight doesn't start again this jump.
            body += [
                "if Player.Gravity == GRAVITY_GROUND",
                "\tNoSwap.Flown = false",
                "else",
                "\tif game.callbackParam3 == 1 // Y, from the DLL",
                "\t\tif NoSwap.Ability == 0",
                "\t\t\tTempValue0 = false",
                "\t\t\tCheckEqual(Player.State, Player_State_Air)",
                "\t\t\tTempValue0 |= CheckResult",
                "\t\t\tCheckEqual(Player.State, Player_State_Air_NoDropDash)",
                "\t\t\tTempValue0 |= CheckResult",
                "\t\t\tCheckEqual(Player.State, Player_State_Fly)",
                "\t\t\tTempValue0 |= CheckResult",
                "\t\t\tif Player.Animation == ANI_HURT",
                "\t\t\t\tTempValue0 = false",
                "\t\t\tend if",
                "\t\t\tif TempValue0 == true",
                "\t\t\t\tif Player.State == Player_State_Fly",
                "\t\t\t\t\tPlayer.State = Player_State_Air",
                "\t\t\t\t\tNoSwap.Flown = true",
                "\t\t\t\tend if",
            ] + ["\t\t\t\t" + l for l in aim_dash_start(i)] + [
                "\t\t\tend if",
                "\t\tend if",
                "\tend if",
                "end if",
            ] + Y_REARM
        if ab.has(i, "screw_kick") and not c.get("kick_jump"):  # after the fresh-jump reset: ready again once landed
            body += screw_kick_start(i)
        if ab.has(i, "pogo"):
            body += [
                "if NoSwap.Pogo == true",
                "\tif Player.Animation != ANI_NOSWAP_ATTACK",
                "\t\tNoSwap.Pogo = false // hurt, springs, a shot...: the pogo ends",
                "\telse",
                "\t\tif Player.Gravity == GRAVITY_GROUND",
                "\t\t\tif Player.JumpHold == true",
                "\t\t\t\tCallFunction(Player_Action_Jump)",
                "\t\t\t\tif Player.Gravity == GRAVITY_AIR",
                f"\t\t\t\t\tPlayer.YVelocity = -{c['pogo_speed']:#x}",
                "\t\t\t\t\tPlayer.Animation = ANI_NOSWAP_ATTACK",
                "\t\t\t\t\tPlayer.Frame = 0 // squash, then stretch",
                "\t\t\t\t\tPlayer.AnimationTimer = 0",
                "\t\t\t\telse",
                "\t\t\t\t\tNoSwap.Pogo = false",
                "\t\t\t\tend if",
                "\t\t\telse",
                "\t\t\t\tNoSwap.Pogo = false",
                "\t\t\t\tPlayer.Animation = ANI_WALKING",
                "\t\t\tend if",
                "\t\tend if",
                "\tend if",
                "end if",
            ]
        if ab.has(i, "charge"):  # Heavy's Charge, held on Y (Y_REARM_HOLD)
            body += charge_after(i)
            if i in ab.sparks():  # its Shine Spark (after the charge: storing reads its juggernaut mark)
                body += spark_after_cd(i)
        if ab.has(i, "spin_attack"):  # Honey's Spin Attack, held on Y (Y_REARM_HOLD)
            body += spin_after(i)
        if ab.has(i, "high_kick"):  # Sally's Spin-Kick High Jump, on a Y press (Y_REARM)
            body += high_kick_after(i)
        if ab.has(i, "phase_warp"):  # Tails Doll's Phase Warp: untouchable, gone or flickering
            body += phase_warp_after(i)
        if ab.has(i, "sink"):  # Mephiles' Shadow Sink, down + Y held (before the shot: it takes down + Y's press)
            body += sink_after(i)
        if cd_shot(i) and ab.down_shot(i):  # down + Y throws it; Y alone is the melee below (which rearms Y)
            if any(ab.has(i, m) for m in VALUE6_MOVES):
                sys.exit(f"shot: extra {i}: a down + Y shot's cooldown ({DOWN_SHOT_COOLDOWN}) is another move's value")
            body += shots_v3.after_lines(cd_shot(i), ab.shot_pose_frame(i, "SonicCDu", 46, "melee_reach"), [],
                                         DOWN_SHOT_COOLDOWN)
        elif cd_shot2(i) and i in ab.charge_shots():  # a charge shot (Mega Man's): Y held charges, letting go fires it;
            # Y alone throws the first as usual (Y_REARM_HOLD: the DLL says when Y is down, cd_charge_lines)
            body += cd_charge_lines(i)
            body += shots_v3.after_lines(cd_shot(i), ab.shot_pose_frame(i, "SonicCDu", 46, "melee_reach"), Y_REARM_HOLD,
                                         two=True, down2=False)
        elif cd_shot2(i):  # two shots: down + Y throws the second ("shot2"), first (Y_REARM ends the first's lines)
            body += shots_v3.after_lines(cd_shot2(i), -1, [], which=2, two=True)
            body += shots_v3.after_lines(cd_shot(i), ab.shot_pose_frame(i, "SonicCDu", 46, "melee_reach"), Y_REARM,
                                         two=True)
        elif ab.swap_shots(i, "cd"):  # swap shots (monitor_swap: John's sub-weapons), up + Y: the current one's; Y alone
            # is the melee below (which rearms Y). Their cooldown is DOWN_SHOT_COOLDOWN's (NoSwap.ShotCooldown is the
            # melee's NoSwap.Shot)
            if any(ab.has(i, m) for m in VALUE6_MOVES):
                sys.exit(f"swap_shots: extra {i}: their cooldown ({DOWN_SHOT_COOLDOWN}) is another move's value")
            import monitor_swap
            body += monitor_swap.cd_after(i)
            body += [f"if {DOWN_SHOT_COOLDOWN} > 0 // swap shots' cooldown (tools/monitor_swap.py)",
                     f"\t{DOWN_SHOT_COOLDOWN}--", "end if"]
            for k, s in enumerate(ab.swap_shots(i, "cd")):
                fly, burn = shots_v3.swap_anims(k)
                body += [f"if {monitor_swap.cd_index()} == {k} // monitor_swap entry {k}: {ab.monitor_entry(i, k)}"]
                body += ["\t" + l for l in shots_v3.after_lines(s, -1, [], DOWN_SHOT_COOLDOWN, which=2, two=True,
                                                               anims=(fly, burn) if "burn" in s else (fly,))]
                body += ["end if"]
        elif cd_shot(i) and not ab.slam_shot(i):  # a real shot (tools/shots_v3.py), thrown with Y; the melee's last frame is the throw pose
            body += shots_v3.after_lines(cd_shot(i), ab.shot_pose_frame(i, "SonicCDu", 46, "melee_reach"),
                                         Y_REARM_HOLD if cd_shot(i).get("autofire") or ab.has(i, "sink")
                                         else Y_REARM)  # ("autofire", the sink: Y held)
        if cd_melee(i):
            ticks = c["melee_ticks"]
            frames = len(c["melee_reach"])
            total = ticks * frames
            if cd_variants(i):  # (melee_run / melee_up: the longest pose's)
                total = ticks * max(len(r) for r, _ in cd_variant_layout(i))
            if c.get("melee_cooldown"):
                body += ["if NoSwap.Cooldown > 0", "\tNoSwap.Cooldown--", "end if"]
            # The shot button: Y from the DLL (Y_REARM). Look up + jump, the peel-out input, still works.
            body += [
                "if game.callbackParam3 == 1 // Y, from the DLL",
                "\tTempValue0 = true",
                "\tif Player.Animation == ANI_HURT",
                "\t\tTempValue0 = false",
                "\tend if",
                "\tif Player.Animation == ANI_DYING",
                "\t\tTempValue0 = false",
                "\tend if",
            ] + ([
                "\tif Player.Animation == ANI_NOSWAP_ATTACK // not out of the Spirit Flight (the orb already attacks)",
                "\t\tTempValue0 = false",
                "\tend if",
            ] if ab.has(i, "spirit_flight") else []) + ([
                "\tif Player.Down == true // down + Y throws its shot (shot \"input\" \"down\"), above",
                "\t\tTempValue0 = false",
                "\tend if",
            ] if ab.down_shot(i) and cd_shot(i) else []) + ([
                "\tif Player.Up == true // up + Y throws its shot (shot \"input\" \"up\": John's sub-weapon), above",
                "\t\tTempValue0 = false",
                "\tend if",
            ] if ab.up_shot(i) and cd_shot(i) else []) + [
                "\tif TempValue0 == true",
                f"\t\tCallFunction(NoSwap_Shot{i})",
                "\tend if",
                "end if",
            ] + Y_REARM
            body += [
                "if NoSwap.Shot > 0",
                "\tCheckEqual(Player.Animation, ANI_HURT)",
                "\tTempValue0 = CheckResult",
                "\tCheckEqual(Player.Animation, ANI_DYING)",
                "\tTempValue0 |= CheckResult",
                "\tCheckEqual(Player.Animation, ANI_DROWNING)",
                "\tTempValue0 |= CheckResult",
                "\tif TempValue0 == true",
                "\t\tNoSwap.Shot = 0",
                "\telse",
            ] + ([
                "\t\tif Player.Gravity == GRAVITY_GROUND // standing still for it (melee_stop: Tikal's punch, Mario's Fireball)",
                "\t\t\tPlayer.Speed = 0",
                "\t\t\tPlayer.XVelocity = 0",
                "\t\tend if",
            ] if c.get("melee_stop") else []) + ([
                "\t\tTempValue1 = Player.Speed // a burst of speed (melee_boost: Mecha's Jet Boost), the way he faces",
                "\t\tif Player.Gravity == GRAVITY_AIR",
                "\t\t\tTempValue1 = Player.XVelocity",
                "\t\t\tPlayer.YVelocity = 0 // level in the air",
                "\t\tend if",
                "\t\tif Player.Direction == FACING_LEFT",
                "\t\t\tFlipSign(TempValue1)",
                "\t\tend if",
                f"\t\tif TempValue1 < {c['melee_boost']:#x}",
                f"\t\t\tTempValue1 = {c['melee_boost']:#x}",
                "\t\tend if",
                "\t\tif Player.Direction == FACING_LEFT",
                "\t\t\tFlipSign(TempValue1)",
                "\t\tend if",
                "\t\tPlayer.Speed = TempValue1",
                "\t\tif Player.Gravity == GRAVITY_AIR",
                "\t\t\tPlayer.XVelocity = TempValue1",
                "\t\tend if",
            ] if c.get("melee_boost") else []) + [
            ] + ([
                "\t\tif Player.InvincibleTimer < 3 // nothing hurts him during it (melee_safe; no BlinkTimer: no flicker)",
                "\t\t\tPlayer.InvincibleTimer = 3",
                "\t\tend if",
            ] if c.get("melee_safe") else []) + ([
                "\t\tif Player.Gravity == GRAVITY_AIR // hanging still in the air for it (melee_hang; the state's gravity next frame cancelled)",
                "\t\t\tPlayer.XVelocity = 0",
                "\t\t\tPlayer.Speed = 0",
                "\t\t\tPlayer.YVelocity = 0",
                "\t\t\tPlayer.YVelocity -= Player.GravityStrength",
                "\t\tend if",
            ] if c.get("melee_hang") else []) + (cd_variant_lines(i, total) if cd_variants(i) else [
                "\t\tPlayer.Animation = ANI_NOSWAP_SHOT",
                f"\t\tTempValue0 = {total}",
                "\t\tTempValue0 -= NoSwap.Shot",
                f"\t\tTempValue0 /= {ticks}",
                "\t\tPlayer.Frame = TempValue0 // the timer picks the frame",
                "\t\tPlayer.AnimationTimer = 0",
                "\t\tNoSwap.Reach = 0",
            ] + (["\t\tswitch TempValue0 // the fireball's leading edge, frame by frame"]
                 + [l for k, r in ([(k, r) for k, r in SHOT_OUT[i].items() if r] if isinstance(SHOT_OUT[i], dict)
                                   else enumerate(SHOT_OUT[i][1:-1], 1))
                    for l in (f"\t\tcase {k}", f"\t\t\tNoSwap.Reach = {r}", "\t\t\tbreak")]
                 + ["\t\tend switch"] if isinstance(SHOT_OUT.get(i), (list, dict))
                 else [] if not SHOT_OUT.get(i) else [  # (no reach past his own box: melee_boost, his body attacks)
                "\t\tif TempValue0 > 0 // the cork / lure is out between the first and last frame",
                f"\t\t\tif TempValue0 < {frames - 1}",
                f"\t\t\t\tNoSwap.Reach = {SHOT_OUT[i]}",
                "\t\t\tend if",
                "\t\tend if",
            ])) + [
                "\t\tNoSwap.Shot--",
            ] + (nuke_spawn_cd(i) if ab.nuke(i) else []) + [
                "\t\tif NoSwap.Shot == 0",
            ] + ([f"\t\t\tPlayer.BlinkTimer = {c['melee_blink']} // invisible: the post-hit blink, so nothing hurts him"]
                 if c.get("melee_blink") else []) + [
                "\t\t\tif Player.Gravity == GRAVITY_GROUND",
                "\t\t\t\tPlayer.Animation = ANI_STOPPED",
                "\t\t\telse",
                "\t\t\t\tPlayer.Animation = ANI_JUMPING",
                "\t\t\tend if",
            ] + (melee_cost_cd() if c.get("melee_cost") else []) + [
                "\t\tend if",
                "\tend if",
                "end if",
                "if NoSwap.Shot == 0",
                "\tNoSwap.Reach = 0",
                "end if",
            ]
        if ab.has(i, "psycho_grab"):  # Silver's Psychokinesis (tools/psycho_grab.py): its lines first; the melee's Y gated
            body = __import__("psycho_grab").cd_gate(i, body)
        if ab.has(i, "power_surge"):
            body += power_surge_after(i)
        if ab.cycle(i):  # slot 45 (S1/S2's 41, the attack moves') shows the active move's frame, its place in the cycle
            body += ["if Player.Animation == ANI_NOSWAP_ATTACK // ability_cycle: the active move's frame",
                     "\tPlayer.Frame = NoSwap.CopyMove", "\tPlayer.AnimationTimer = 0", "end if"]
        if ab.has(i, "ear_grapple"):  # (the ear's tip is tested in NoSwap_ShotTouch now: cd_ear_touch)
            if not ab.v4_melee(i) and not cd_shot(i):  # (no shot to clear it)
                body += ["NoSwap.Reach = 0"]
        after.append((i, body))
    out.append("// [NoSwap] Every frame after the player has moved and landed\nfunction NoSwap_AfterUpdate\n")
    out += [per_extra_id("\t", i, body) for i, body in after]
    out.append("end function\n\n\n")
    return "".join(out)


def warp_check(i):
    """Tails Doll's Phase Warp keeps its direction and speed in Object[5].Value5 / Value6 (WARP_ALIAS)."""
    shared = [m for m in WARP_MOVES if ab.has(i, m)] + (["a down + Y shot"] if ab.down_shot(i) else [])
    if shared or hold_moves(i):
        sys.exit(f"phase_warp: extra {i}: its CD values (Object[5].Value5 / Value6) are also {shared or 'a held move'}'s")


def phase_warp_functions(i):
    """Phase Warp, as in S1/S2 (abilities.phase_warp_function): the press (the jump ability) and the destination search
    (NoSwap_WarpTo, from phase_warp_air). The search tests on a stand-in position in Object.XPos / YPos, as the Wall
    Cling does (ObjectTileCollision moves the object it tests), and puts it back after."""
    warp_check(i)
    c = cfg(i)
    straight, diag = ab.warp_steps(i)
    tests = "".join(f"""		Object.XPos = TempValue0
		Object.XPos += TempValue4
		Object.YPos = TempValue1
		Object.YPos += TempValue5
		ObjectTileCollision(CSIDE_FLOOR, {x}, {y}, Player.CollisionPlane)
		if CheckResult == true
			TempValue3 = true
		end if
""" for x, y in ab.WARP_POINTS)
    return f"""// Phase Warp: jump in mid-air, once per jump: he flickers out, is gone, flickers back in up to {c['warp_range']} px away where
// the d-pad points (NoSwap_AirAbilities, NoSwap_AfterUpdate; abilities.py phase_warp). Ability: frames of it left
function NoSwap_PhaseWarp{i}
	if Player.JumpPress == true
		if NoSwap.Ability == 0
			NoSwap.Ability = {ab.warp_total(i)}
			TempValue0 = 1 // x + 1
			if Player.Left == true
				TempValue0 = 0
			end if
			if Player.Right == true
				TempValue0 = 2
			end if
			TempValue1 = 1 // y + 1
			if Player.Up == true
				TempValue1 = 0
			end if
			if Player.Down == true
				TempValue1 = 2
			end if
			if TempValue0 == 1
				if TempValue1 == 1 // nothing held: ahead
					TempValue0 = 2
					if Player.Direction == FACING_LEFT
						TempValue0 = 0
					end if
				end if
			end if
			TempValue1 *= 3
			TempValue0 += TempValue1
			NoSwap.WarpDir = TempValue0
			NoSwap.WarpVX = Player.XVelocity
			Player.Animation = ANI_NOSWAP_ATTACK
			PlaySfx({c['warp_sfx_cd']}, false)
		end if
	end if
end function


// Phase Warp: along its direction, {ab.warp_count(i)} steps of {ab.WARP_STEP} px at most, stopping before the first where a point of
// his body is in solid terrain; he ends at the last clear one
function NoSwap_WarpTo{i}
	TempValue6 = Object.XPos // (the stand-in's own position, put back after)
	TempValue7 = Object.YPos
	TempValue4 = NoSwap.WarpDir
	TempValue5 = TempValue4
	TempValue5 /= 3
	TempValue5-- // y: -1, 0, 1
	TempValue4 %= 3
	TempValue4-- // x
	TempValue3 = {straight:#x}
	if TempValue4 != 0
		if TempValue5 != 0 // a diagonal: the same length overall
			TempValue3 = {diag:#x}
		end if
	end if
	TempValue4 *= TempValue3
	TempValue5 *= TempValue3
	TempValue0 = Player.XPos // the last clear spot
	TempValue1 = Player.YPos
	TempValue2 = 0
	while TempValue2 < {ab.warp_count(i)}
		TempValue3 = false // the next step blocked?
{tests}		if TempValue3 == true
			TempValue2 = {ab.warp_count(i)} // stop before it
		else
			TempValue0 += TempValue4
			TempValue1 += TempValue5
			TempValue2++
		end if
	loop
	Player.XPos = TempValue0
	Player.YPos = TempValue1
	Object.XPos = TempValue6
	Object.YPos = TempValue7
end function


"""


def phase_warp_air(i):
    """Before the state runs (its gravity cancelled in advance): held still, gone at the start of warp_gone (to the
    destination), and at the end his speed along from before, falling from there (abilities.phase_warp_air)."""
    c = cfg(i)
    at = c["warp_gone"] + c["warp_appear"]
    return ["if NoSwap.Ability > 0 // Phase Warp (build_soniccd.phase_warp_air)",
            "\tif Player.Animation == ANI_NOSWAP_ATTACK",
            "\t\tPlayer.XVelocity = 0 // held still",
            "\t\tPlayer.Speed = 0",
            "\t\tPlayer.YVelocity = 0",
            "\t\tPlayer.YVelocity -= Player.GravityStrength",
            f"\t\tif NoSwap.Ability == {at} // gone: to the destination",
            f"\t\t\tCallFunction(NoSwap_WarpTo{i})",
            "\t\tend if",
            "\t\tNoSwap.Ability--",
            "\t\tif NoSwap.Ability == 0 // back: his speed along, falling from here",
            "\t\t\tNoSwap.Ability = -1",
            "\t\t\tPlayer.Animation = ANI_JUMPING",
            "\t\t\tPlayer.XVelocity = NoSwap.WarpVX",
            "\t\t\tPlayer.Speed = NoSwap.WarpVX",
            "\t\t\tPlayer.YVelocity = 0",
            "\t\t\tPlayer.Visible = true",
            "\t\tend if",
            "\telse",
            "\t\tNoSwap.Ability = -1 // a spring, the melee...: over for this jump",
            "\t\tPlayer.Visible = true",
            "\tend if",
            "end if"]


def phase_warp_after(i):
    """After the update: untouchable (the post-hit timer at 3, no BlinkTimer: no flicker of its own), gone while
    warp_gone lasts, flickering while he goes and comes back (abilities.phase_warp_after). Landing ends it."""
    c = cfg(i)
    at = c["warp_gone"] + c["warp_appear"]
    return ["if NoSwap.Ability > 0 // Phase Warp: untouchable, gone or flickering (build_soniccd.phase_warp_after)",
            "\tif Player.Gravity == GRAVITY_GROUND",
            "\t\tNoSwap.Ability = -1",
            "\t\tPlayer.Visible = true",
            "\telse",
            "\t\tif Player.InvincibleTimer < 3",
            "\t\t\tPlayer.InvincibleTimer = 3",
            "\t\tend if",
            "\t\tTempValue0 = NoSwap.Ability",
            "\t\tTempValue0 &= 1",
            "\t\tPlayer.Visible = TempValue0 // (a flicker: every other frame)",
            f"\t\tif NoSwap.Ability <= {at}",
            f"\t\t\tif NoSwap.Ability > {c['warp_appear']}",
            "\t\t\t\tPlayer.Visible = false // gone",
            "\t\t\tend if",
            "\t\tend if",
            "\tend if",
            "end if"]


def melee_cost_cd():
    """melee_cost, CD (abilities.py MELEE_COST): the end of the move hurts him as Player_Hit would (an invincibility
    star still keeps him; his own melee_safe InvincibleTimer doesn't): the game's own Player_State_GotHit next frame
    (rings, shield or death), knocked back from the way he faces. Only in the game's free states."""
    states = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
              "Player_State_Roll", "Player_State_LookUp", "Player_State_Crouch"]
    return (["\t\t\tTempValue0 = false // the cost (melee_cost: Bomb's Self-Destruct hurts him, a normal hit)"]
            + [l for s in states for l in (f"\t\t\tCheckEqual(Player.State, {s})", "\t\t\tTempValue0 |= CheckResult")]
            + ["\t\t\tArrayPos0 = Player.EntityNo",
               "\t\t\tArrayPos0 += 2",
               "\t\t\tif Object[ArrayPos0].Type == TypeName[Invincibility] // (a star: no hit, as Player_Hit)",
               "\t\t\t\tTempValue0 = false",
               "\t\t\tend if",
               "\t\t\tif TempValue0 == true",
               "\t\t\t\tPlayer.InvincibleTimer = 0 // (his melee_safe guard isn't one against it)",
               "\t\t\t\tPlayer.State = Player_State_GotHit // the game's own hurt: rings, shield or death",
               "\t\t\t\tif Player.Direction == FACING_RIGHT // knocked back",
               "\t\t\t\t\tPlayer.Speed = -0x20000",
               "\t\t\t\telse",
               "\t\t\t\t\tPlayer.Speed = 0x20000",
               "\t\t\t\tend if",
               "\t\t\tend if"])


def nuke_spawn_cd(i):
    """melee_nuke, CD (abilities.nuke_spawn): on the move's frame `at` its object in the first shot slot
    (tools/shots_v3.py: a Tails Object, Value7 1 marking it a nuke), which draws the flash (TailsObject.txt:
    SetScreenFade by its Value6) and hits all round him (nuke_update_cd). The extra has no other shots."""
    n = ab.nuke(i)
    slot = shots_v3.SLOTS[0]
    return [f"\t\tif NoSwap.Shot == {ab.nuke_left(i)} // the nuke (melee_nuke: build_soniccd.nuke_spawn_cd): its flash and its hit",
            f"\t\t\tResetObjectEntity({slot}, TypeName[Tails Object], 0, Player.XPos, Player.YPos)",
            f"\t\t\tObject[{slot}].State = {shots_v3.LIVE}",
            f"\t\t\tObject[{slot}].Priority = PRIORITY_ACTIVE",
            f"\t\t\tObject[{slot}].DrawOrder = 6 // (the top layer: the fade goes over everything)",
            f"\t\t\tObject[{slot}].Value2 = 0",
            f"\t\t\tObject[{slot}].Value3 = {n['reach_cd'] << 16:#x}",
            f"\t\t\tObject[{slot}].Value4 = Player.CollisionPlane",
            f"\t\t\tObject[{slot}].Value6 = -1 // (nothing drawn until its update gives the fade)",
            f"\t\t\tObject[{slot}].Value7 = 1 // a nuke: NoSwap_ShotTouch leaves it, TailsObject.txt draws its fade",
            f"\t\t\tPlaySfx({n['sfx_cd']}, false)",
            "\t\tend if"]


def nuke_update_cd(i):
    """The nuke's own update (Object: it; abilities.nuke_update_body): on the player all its life, the flash's darkness
    per frame in Value6 (-1: nothing drawn), and LIVE for its first `hit` frames (the targets' NoSwap_ShotTouch tests it,
    a square reach_cd round him, and leaves it)."""
    n = ab.nuke(i)
    flash = [f"\t\tcase {k + 1}\n\t\t\tObject.Value6 = {a if a else -1}\n\t\t\tbreak" for k, a in enumerate(n["flash"])]
    return (["Object.Value2++ // its age (melee_nuke: build_soniccd.nuke_update_cd)",
             "Object.XPos = Player.XPos",
             "Object.YPos = Player.YPos",
             f"if Object.Value2 > {max(len(n['flash']), n['hit'])}",
             "\tObject.Type = TypeName[Blank Object]",
             "else"]
            + (["\tswitch Object.Value2 // the flash's darkness"] + "\n".join(flash).split("\n") + ["\tend switch"]
               if flash else [])  # (no "flash": Bomb's nuke, the hit alone; Value6 stays -1, nothing drawn)
            + [f"\tif Object.Value2 <= {n['hit']}",
               f"\t\tObject.State = {shots_v3.LIVE} // its hit",
               "\telse",
               "\t\tObject.State = 0 // (over: the targets' tests pass it by)",
               "\tend if",
               "end if"])


def slam_spawn_cd(i):
    """CD, shot "input" "slam" (Bark's shockwaves; abilities.slam_spawn): as the Hammer Drop lands, two shots, one each
    way, x px out and y px below his centre, in the first two shot slots (tools/shots_v3.py; the extra has no other
    shots), set up as shots_v3.after_lines does; their reach (Value3) the art's hitbox."""
    s = cd_shot(i)
    reach = s.get("art", {}).get("hitbox", [0, 0, s["radius"], 0])[2]
    out = ["\t\t\t// the slam's shockwaves (shot \"input\" \"slam\": build_soniccd.slam_spawn_cd): one each way"]
    for slot, sign in zip(shots_v3.SLOTS, (-1, 1)):
        out += [f"\t\t\tTempValue3 = {sign * (s['x'] << 16):#x}", "\t\t\tTempValue3 += Player.XPos",
                "\t\t\tTempValue4 = Player.YPos", f"\t\t\tTempValue4 += {s['y'] << 16:#x}",
                f"\t\t\tResetObjectEntity({slot}, TypeName[Tails Object], 0, TempValue3, TempValue4)",
                f"\t\t\tObject[{slot}].State = {shots_v3.LIVE}",
                f"\t\t\tObject[{slot}].Priority = PRIORITY_ACTIVE",
                f"\t\t\tObject[{slot}].DrawOrder = Player.DrawOrder",
                f"\t\t\tObject[{slot}].Direction = {'FACING_LEFT' if sign < 0 else 'FACING_RIGHT'}",
                f"\t\t\tObject[{slot}].Value0 = {sign * s['speed']:#x}",
                f"\t\t\tObject[{slot}].Value1 = 0",
                f"\t\t\tObject[{slot}].Value2 = 0",
                f"\t\t\tObject[{slot}].Value3 = {reach << 16:#x}",
                f"\t\t\tObject[{slot}].Value4 = Player.CollisionPlane",
                f"\t\t\tObject[{slot}].Animation = {shots_v3.ANI_SHOT}",
                f"\t\t\tObject[{slot}].Frame = 0",
                f"\t\t\tObject[{slot}].AnimationTimer = 0"]
    return out


def puddle_after(i, ground=False):
    """Chaos' Puddle Slide after the player has moved, as in S1/S2 (abilities.py puddle_slide_after): landing from the
    drop starts the puddle (NoSwap.Puddle: its game frames left); then each frame on the ground the timer picks the frame
    (slot 47), sets his speed and holds off hits (InvincibleTimer, the post-hit one, at 3 at least, with no blink) and
    the Stretch Punch (NoSwap.Cooldown). ground: abilities.py ground_slide's (Ray Poward's Slide): NoSwap.Slide, started by
    its ActionSpindash (NoSwap_GroundSlide), no drop, and Y stays free (NoSwap.Cooldown is the wall cling's value there)."""
    c = cfg(i)
    frames, ticks = c["puddle_frames"], c["puddle_ticks"]
    total = ticks * len(frames)
    if ground:
        out = puddle_after(i)
        out = out[out.index("if NoSwap.Puddle > 0"):]
        out = [l for l in out if l != "\t\tNoSwap.Cooldown = 2 // and Y doesn't punch"]
        return [l.replace("NoSwap.Puddle", "NoSwap.Slide") for l in out]
    steps = []  # a switch on the step: its frame
    for f in sorted(set(frames)):
        steps += [f"\t\tcase {k}" for k, v in enumerate(frames) if v == f] + [f"\t\t\tPlayer.Frame = {f}", "\t\t\tbreak"]
    return [
        "if NoSwap.Ability == 1",
        "\tif Player.Gravity == GRAVITY_GROUND",
        "\t\tNoSwap.Ability = -1",
        "\t\tif Player.Animation == ANI_NOSWAP_ATTACK // landed from the drop: melt",
        f"\t\t\tNoSwap.Puddle = {total}",
        f"\t\t\tPlaySfx({c['puddle_sfx_cd']}, false)",
        "\t\tend if",
        "\tend if",
        "end if",
        "if NoSwap.Puddle > 0",
        "\tTempValue0 = false // still on the ground in a ground state (landing: the air state, until next frame)",
        "\tif Player.Gravity == GRAVITY_GROUND",
        "\t\tCheckEqual(Player.State, Player_State_Ground)",
        "\t\tTempValue0 |= CheckResult",
        "\t\tCheckEqual(Player.State, Player_State_Air)",
        "\t\tTempValue0 |= CheckResult",
        "\t\tCheckEqual(Player.State, Player_State_Air_NoDropDash)",
        "\t\tTempValue0 |= CheckResult",
        "\tend if",
        "\tif Player.Animation == ANI_HURT",
        "\t\tTempValue0 = false",
        "\tend if",
        "\tif TempValue0 == false // a jump, a roll, a spring, a ledge, a hit...: over",
        "\t\tNoSwap.Puddle = 0",
        "\telse",
        "\t\tNoSwap.Puddle--",
        f"\t\tTempValue1 = {total} // the step",
        "\t\tTempValue1 -= NoSwap.Puddle",
        "\t\tTempValue1--",
        f"\t\tTempValue1 /= {ticks}",
        "\t\tPlayer.Animation = ANI_NOSWAP_HOVER",
        "\t\tswitch TempValue1 // the timer picks the frame",
    ] + steps + [
        "\t\tend switch",
        "\t\tPlayer.AnimationTimer = 0",
        "\t\tTempValue2 = Player.Speed",
        f"\t\tif TempValue1 < {c['puddle_move']} // melting and sliding: at least puddle_speed the way he faces",
        "\t\t\tif Player.Direction == FACING_LEFT",
        "\t\t\t\tFlipSign(TempValue2)",
        "\t\t\tend if",
        f"\t\t\tif TempValue2 < {c['puddle_speed']:#x}",
        f"\t\t\t\tTempValue2 = {c['puddle_speed']:#x}",
        "\t\t\tend if",
        "\t\t\tif Player.Direction == FACING_LEFT",
        "\t\t\t\tFlipSign(TempValue2)",
        "\t\t\tend if",
        "\t\t\tPlayer.Speed = TempValue2",
        "\t\telse // rising: slowing to a stop",
        "\t\t\tTempValue2 >>= 2",
        "\t\t\tPlayer.Speed -= TempValue2",
        "\t\tend if",
        "\t\tif Player.InvincibleTimer < 3 // nothing hurts him (the post-hit timer; no BlinkTimer: no flicker)",
        "\t\t\tPlayer.InvincibleTimer = 3",
        "\t\tend if",
        "\t\tNoSwap.Cooldown = 2 // and Y doesn't punch",
        "\t\tif NoSwap.Puddle == 0 // risen",
        "\t\t\tPlayer.Animation = ANI_STOPPED",
        "\t\tend if",
        "\tend if",
        "end if",
    ]


def per_extra_id(indent, i, body):
    alias = next(e["alias"] for e in EXTRAS if e["id"] == i)
    return "\n".join([f"{indent}if Stage.PlayerListPos == {alias}"] + [f"{indent}\t{l}" for l in body]
                     + [f"{indent}end if", ""]) + "\n"


def cd_physics_lines(i):
    """Sonic's CD values scaled by the extra's physics multipliers (abilities.ABILITIES)."""
    if not ab.has(i, "physics"):
        return []
    m = cfg(i)["physics"]
    base = {"TopSpeed": (0x60000, "top_speed"), "Acceleration": (0xC00, "acceleration"),
            "Deceleration": (0xC00, "acceleration"), "AirAcceleration": (0x1800, "air_acceleration"),
            "JumpStrength": (0x68000, "jump")}
    return [f"Player.{k} = {int(v * m.get(key, 1.0)):#x} // [NoSwap] own physics" for k, (v, key) in base.items()
            if key in m]


def cd_shell_spikes():
    """Mania Plus's spike rule for spike_shell extras (Mighty): curled up (jump ball, spin dash, Hammer Drop),
    spikes don't hurt; he's knocked up and back and blinks. Called by the spike objects before their hit;
    the answer is in Object[5].Value7 (true: the shell took it)."""
    ids = [i for i in ab.ABILITIES if ab.has(i, "spike_shell")]
    lines = ["// [NoSwap] spike_shell (Mania Plus): spikes don't hurt a curled-up Mighty", "function NoSwap_ShellSpikes",
             "\tObject[5].Value7 = false"]
    for i in ids:
        alias = next(e["alias"] for e in EXTRAS if e["id"] == i)
        lines += [f"\tif Stage.PlayerListPos == {alias}", "\t\tif Player.BlinkTimer == 0",
                  "\t\t\tif Player.InvincibleTimer == 0",
                  "\t\t\t\tif Player.Animation == ANI_JUMPING", "\t\t\t\t\tObject[5].Value7 = true", "\t\t\t\tend if",
                  "\t\t\t\tif Player.Animation == ANI_SPINDASH", "\t\t\t\t\tObject[5].Value7 = true", "\t\t\t\tend if",
                  "\t\t\t\tif Player.Animation == ANI_NOSWAP_ATTACK", "\t\t\t\t\tObject[5].Value7 = true", "\t\t\t\tend if",
                  "\t\t\tend if", "\t\tend if", "\tend if"]
    lines += ["\tif Object[5].Value7 == true",
              "\t\tPlayer.YVelocity = -0x48000",
              "\t\tPlayer.XVelocity = -0x28000",
              "\t\tif Player.Direction == FACING_LEFT",
              "\t\t\tPlayer.XVelocity = 0x28000",
              "\t\tend if",
              "\t\tPlayer.Speed = Player.XVelocity",
              "\t\tPlayer.Gravity = GRAVITY_AIR",
              "\t\tPlayer.State = Player_State_Air",
              "\t\tPlayer.Animation = ANI_BOUNCING",
              "\t\tPlayer.BlinkTimer = 121",
              "\t\tNoSwap.Ability = -1",
              "\tend if",
              "end function", "", ""]
    return "\n".join(lines) + "\n"


def shell_spikes_object(t):
    """Spike objects: a curled-up Mighty's shell takes the hit (cd_shell_spikes)."""
    if not any(ab.has(i, "spike_shell") for i in ab.ABILITIES):
        return t
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == "Player.State = Player_State_GotHit"]
    if not hits:
        sys.exit("spike shell: no spike hit found")
    for i in reversed(hits):
        ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i:i + 1] = [f"{ind}CallFunction(NoSwap_ShellSpikes) // [NoSwap] a curled-up Mighty's shell takes spikes",
                          f"{ind}if Object[5].Value7 == false", f"{ind}\tPlayer.State = Player_State_GotHit", f"{ind}end if"]
    return "\n".join(lines)


def apply_cd_abilities(t):
    t = cd_bat_glide(t)
    t = patch(t, "#alias 5\t:\tPLAYER_AMY_A\n", "#alias 5\t:\tPLAYER_AMY_A\n" + STATE_ALIASES
              + (PUDDLE_ALIAS if ab.with_ability("puddle_slide") else "")
              + (VARIANT_ALIAS if any(cd_variants(i) for i in ab.ABILITIES) else "")
              + (SLIDE_ALIAS if ab.with_ability("ground_slide") else "")
              + (SHOT_NEXT_ALIAS if any(cd_shot(i) and cd_shot(i).get("cycle") for i in ab.ABILITIES) else "")
              + (CHARGE_ALIAS if ab.with_ability("charge") else "")
              + (SPARK_ALIAS if ab.sparks() else "")
              + (SPIN_ALIAS if ab.with_ability("spin_attack") else "")
              + (HIGH_KICK_ALIAS if ab.with_ability("high_kick") else "")
              + (CYCLE_ALIAS if ab.cycle_extras() else "")
              + (SWIM_ALIAS if ab.with_ability("water_swim") else "")
              + (SWIM_B_ALIAS if any(ab.has(i, "puddle_slide") for i in ab.with_ability("water_swim")) else "")
              + (WARP_ALIAS if ab.with_ability("phase_warp") else "")
              + (ROCKET_ALIAS if ab.with_ability("rocket_burst") else "")
              + (SINK_ALIAS if ab.with_ability("sink") else "")
              + (Y_HELD_ALIAS if any(hold_moves(i) for i in ab.ABILITIES) else "")
              + (BUSTER_ALIAS if ab.charge_shots() else ""),
              "ability aliases")
    nukes = [i for i in ab.ABILITIES if cd_melee(i) and ab.nuke(i)]  # (Tails Doll's Screen Nuke: nuke_update_cd)
    functions = cd_functions() + cd_shell_spikes() + cd_shared_functions() + shots_v3.player_functions(
        [per_extra_id("\t", i, shots_v3.swap_update_body(ab.swap_shots(i, "cd")) if ab.swap_shots(i, "cd")
                      else __import__("ninjutsu").cd_update_dispatch(i, shots_v3.update_body(cd_shot(i), cd_shot2(i))))
         for i in ab.ABILITIES if cd_shot(i)]  # (Joe's Ninjutsu blasts: tools/ninjutsu.py)
        + [per_extra_id("\t", i, nuke_update_cd(i)) for i in nukes]
        + [per_extra_id("\t", i, __import__("psycho_grab").cd_shot_update(i))  # (Psychokinesis' thrower)
           for i in ab.with_ability("psycho_grab") if not cd_shot(i)]
        + [per_extra_id("\t", i, __import__("pot_magic").cd_update(i))  # (Gilius' Earthquake: tools/pot_magic.py)
           for i in ab.with_ability("pot_magic") if not cd_shot(i)],
        touch_attack_lines("CheckResult = true", "its move hits what it touches (Heavy's Charge)"), keep_nukes=bool(nukes) or bool(ab.with_ability("ninjutsu")) or bool(ab.with_ability("pot_magic")),
        pierce=any((cd_shot2(i) or {}).get("pierce") for i in ab.ABILITIES) or bool(ab.with_ability("psycho_grab"))
        or any(s.get("pierce") and s["motion"] != "boomerang" for i in ab.ABILITIES for s in ab.swap_shots(i, "cd")),
        pierce6=any(s.get("pierce") and s["motion"] == "boomerang" for i in ab.ABILITIES for s in ab.swap_shots(i, "cd")),
        homing=any(cd_shot(i) and cd_shot(i)["motion"] == "homing" for i in ab.ABILITIES))
    decls = "".join(f"#function {n}\n" for n in re.findall(r"^function (NoSwap_\w+)", functions, re.M))
    t = patch(t, "#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls, "ability declarations")
    t = patch(t, "\nfunction Player_BadnikBreak\n", "\n" + functions + "function Player_BadnikBreak\n", "ability functions")
    # Hammer Drop through badniks: keep falling, 1 px per frame slower, instead of bouncing (Mania Plus)
    drops = [e["alias"] for e in EXTRAS if ab.has(e["id"], "hammer_drop")]
    checks = "".join(f"\t\t\tif Stage.PlayerListPos == {a}\n\t\t\t\tif Player.Animation == ANI_NOSWAP_ATTACK\n"
                     "\t\t\t\t\tTempValue0 = true\n\t\t\t\tend if\n\t\t\tend if\n" for a in drops)
    t = patch(t, "\t\tif Player.YVelocity > 0\n\t\t\tFlipSign(Player.YVelocity)\n\t\telse\n\t\t\tPlayer.YVelocity += 0xC000\n",
              "\t\tif Player.YVelocity > 0\n\t\t\tTempValue0 = false // [NoSwap] a Hammer Drop plows through (Mania Plus)\n"
              + checks + "\t\t\tif TempValue0 == true\n\t\t\t\tPlayer.YVelocity -= 0x10000\n\t\t\telse\n"
              "\t\t\t\tFlipSign(Player.YVelocity)\n\t\t\tend if\n\t\telse\n\t\t\tPlayer.YVelocity += 0xC000\n", "hammer drop badniks")
    t = shots_v3.player_script(t)  # extras' shots: Player_BadnikBreak takes their hits (tools/shots_v3.py)
    # Start of the update (spin_attack: whether the game bounced her off something), only in a build with such an extra
    spins = [i for i in ab.ABILITIES if ab.has(i, "spin_attack")]
    if spins:
        t = patch(t, "sub ObjectMain\n", "sub ObjectMain\n\tif Stage.PlayerListPos >= 7 // [NoSwap] ability moves (the start "
                  "of the update)\n" + "".join(per_extra_id("\t\t", i, spin_before(i)) for i in spins) + "\tend if\n",
                  "before hook")
    # Startup: each extra's jump ability, shot, physics, and a clean ability state
    for e in EXTRAS:
        i = e["id"]
        block = f"\tif Stage.PlayerListPos == {e['alias']} // [NoSwap]\n\t\tPlayer.JumpAbility = Player_State_Static\n"
        new = f"\tif Stage.PlayerListPos == {e['alias']} // [NoSwap]\n\t\tPlayer.JumpAbility = {jump_ability_name(i)}\n"
        new += "\t\tObject[5].Value0 = 0\n\t\tObject[5].Value1 = 0\n\t\tObject[5].Value2 = 0\n\t\tObject[5].Value3 = 0\n"
        if ab.has(i, "psycho_grab"):  # (its own slot's values: tools/psycho_grab.py)
            new += __import__("psycho_grab").cd_startup()
        if ab.has(i, "puddle_slide"):  # (its own value: NoSwap.Puddle, PUDDLE_ALIAS)
            new += "\t\tNoSwap.Puddle = 0\n"
        if cd_shot(i) and cd_shot(i).get("cycle"):  # (its own value: NoSwap.ShotNext, SHOT_NEXT_ALIAS)
            new += "\t\tNoSwap.ShotNext = 0\n"
        if ab.has(i, "charge"):  # (its own values: CHARGE_ALIAS, Y_HELD_ALIAS)
            new += "\t\tNoSwap.Charge = 0\n"
            if i in ab.sparks():  # (its own value: SPARK_ALIAS)
                new += "\t\tNoSwap.Spark = 0\n"
        if ab.has(i, "spin_attack"):
            new += "\t\tNoSwap.Spin = 0\n\t\tNoSwap.SpinVY = 0\n"
        if ab.has(i, "high_kick"):  # (its own values: HIGH_KICK_ALIAS)
            new += "\t\tNoSwap.HiKick = 0\n\t\tNoSwap.HiKickUsed = 0\n\t\tNoSwap.HiKickCool = 0\n"
        if ab.has(i, "water_swim"):  # (its own value: SWIM_ALIAS)
            new += f"\t\t{swim_var(i)} = 0\n"
        if ab.has(i, "sink"):  # (its own value: SINK_ALIAS)
            new += "\t\tNoSwap.Sink = 0\n"
        if hold_moves(i):
            new += "\t\tNoSwap.YHeld = 0\n"
        if i in ab.charge_shots():  # (its own value: BUSTER_ALIAS)
            new += "\t\tNoSwap.BusterCharge = 0\n"
        if ab.cycle(i):  # (its own value: CYCLE_ALIAS; the melee cooldown's, which it can't have: abilities.cycle)
            new += "\t\tNoSwap.CopyMove = 0 // ability_cycle: the first move at each stage load\n"
        if ab.has(i, "breaks_walls"):  # (only such an extra's startup sets it: the other packages don't change)
            new += f"\t\tObject[5].PropertyValue = {CD_BREAKS_WALLS} // breaks walls like Knuckles (cd_break_walls)\n"
        if ab.has(i, "no_stomp") and ab.has(i, "ground_slide"):  # (its Slide sets it while it slides: cd_no_stomp_slide)
            if ab.has(i, "breaks_walls") or ab.has(i, "fire_immune") or ab.has(i, "charge"):
                sys.exit(f"extra {i}: no_stomp's Slide uses Object[5].PropertyValue in Sonic CD (breaks_walls, fire_immune, charge)")
            new += "\t\tObject[5].PropertyValue = 0 // no_stomp: the Slide's wall breaking off (cd_no_stomp_slide)\n"
        if ab.has(i, "fire_immune"):  # (the same byte: one or the other)
            if ab.has(i, "breaks_walls"):
                sys.exit(f"extra {i}: breaks_walls and fire_immune share Object[5].PropertyValue in Sonic CD")
            new += f"\t\tObject[5].PropertyValue = {CD_FIRE_IMMUNE} // fire never hurts this extra (cd_fire_hit)\n"
        new += "".join(f"\t\t{l}\n" for l in cd_physics_lines(i))
        t = patch(t, block, new, f"startup abilities {i}")
        base = e["base"]
        if base != "sonic":  # built on Tails / Knuckles: their CD moves (flight; glide and climb), no peel out
            s = t.index(new)
            j = t.index("\tend if\n", t.index("\t\tend if\n", s) + 1)
            seg = t[s:j]
            seg = seg.replace("Player.ActionPeelout = Player_Action_Peelout_S2", "Player.ActionPeelout = Player_Action_Jump")
            seg = seg.replace("Player.ActionPeelout = Player_Action_Peelout_CD", "Player.ActionPeelout = Player_Action_Jump")
            if base == "knuckles":
                seg = seg.replace(new, new + "\t\tPlayer.JumpStrength = 0x60000 // Knuckles' lower jump\n", 1)
            t = t[:s] + seg + t[j:]
        if cd_melee(i):  # look up + jump fires instead of the peel out
            s = t.index(new)
            j = t.index("\tend if\n", t.index("\t\tend if\n", s) + 1)
            seg = t[s:j]
            for old in ("Player_Action_Peelout_S2", "Player_Action_Peelout_CD", "Player_Action_Jump"):
                seg = seg.replace(f"Player.ActionPeelout = {old}", f"Player.ActionPeelout = NoSwap_Shot{i}")
            t = t[:s] + seg + t[j:]
    # Triple Jump: Player_Action_Jump uses a higher jump strength for a chain's 2nd and 3rd jumps
    if any(ab.has(i, "triple_jump") for i in ab.ABILITIES):
        anchor = "\t\tPlayer.AbilityTimer = 8\n\n\t\tSin256(Player.XVelocity, Player.Angle)\n"
        t = patch(t, anchor, anchor.replace("\n\n", "\n\t\tif Stage.PlayerListPos >= 7 // [NoSwap] a Triple Jump's 2nd and 3rd jumps are higher\n"
                                                 "\t\t\tCallFunction(NoSwap_JumpStart)\n\t\tend if\n\n"), "triple jump start")
        anchor = "\t\tPlayer.YVelocity >>= 8\n\n\t\tPlayer.Speed\t\t = Player.XVelocity\n"
        t = patch(t, anchor, anchor.replace("\n\n", "\n\t\tif Stage.PlayerListPos >= 7 // [NoSwap] (his own jump strength back)\n"
                                                 "\t\t\tCallFunction(NoSwap_JumpEnd)\n\t\tend if\n\n"), "triple jump end")
    # Hooks: air abilities before the state, the rest after landing
    anchor = "\t\t// Handle Player\n\t\tCallFunction(Player_ProcessUpdate)\n\t\tCallFunction(Player.State)\n"
    t = patch(t, anchor, "\t\t// Handle Player\n\t\tCallFunction(Player_ProcessUpdate)\n"
              "\t\tif Stage.PlayerListPos >= 7 // [NoSwap] ability moves\n"
              "\t\t\tif Player.Gravity == GRAVITY_AIR\n\t\t\t\tCallFunction(NoSwap_AirAbilities)\n\t\t\tend if\n\t\tend if\n"
              "\t\tCallFunction(Player.State)\n", "air hook")
    anchor = ("\t\t\t\t\tPlayer.iYPos\t\t+= Player.JumpOffset\n\t\t\t\tend if\n\t\t\tend if\n\t\tend if\n\tend if\nend sub\n")
    t = patch(t, anchor, anchor.replace("\t\tend if\n\tend if\nend sub\n",
              "\t\tend if\n\t\tif Stage.PlayerListPos >= 7 // [NoSwap] ability moves\n\t\t\tCallFunction(NoSwap_AfterUpdate)\n"
              "\t\tend if\n\tend if\nend sub\n"), "after hook")
    # ObjectMain has a second copy of the player update for when debug mode is available (Stage.DebugMode:
    # on after the stage select), which the hooks above miss: extras' moves and shots stopped working there
    anchor = "\t\t\t// Handle Player\n\t\t\tCallFunction(Player_ProcessUpdate)\n\t\t\tCallFunction(Player.State)\n"
    t = patch(t, anchor, "\t\t\t// Handle Player\n\t\t\tCallFunction(Player_ProcessUpdate)\n"
              "\t\t\tif Stage.PlayerListPos >= 7 // [NoSwap] ability moves (the debug-mode copy)\n"
              "\t\t\t\tif Player.Gravity == GRAVITY_AIR\n\t\t\t\t\tCallFunction(NoSwap_AirAbilities)\n\t\t\t\tend if\n\t\t\tend if\n"
              "\t\t\tCallFunction(Player.State)\n", "air hook (debug copy)")
    anchor = ("\t\t\t\t\t\tPlayer.iYPos\t\t+= Player.JumpOffset\n\t\t\t\t\tend if\n\t\t\t\tend if\n\t\t\tend if\n\t\tend if\n\telse\n")
    return patch(t, anchor, anchor.replace("\t\t\tend if\n\t\tend if\n\telse\n",
                 "\t\t\tend if\n\t\t\tif Stage.PlayerListPos >= 7 // [NoSwap] ability moves (the debug-mode copy)\n"
                 "\t\t\t\tCallFunction(NoSwap_AfterUpdate)\n\t\t\tend if\n\t\tend if\n\telse\n"), "after hook (debug copy)")


def enemy_reach(t, name):
    """While an extra's shot is out, enemies widen their own box toward the player by the shot's reach."""
    shots = [r for v in SHOT_OUT.values()  # (a list: per frame, but the first and last; a dict: frame -> reach)
             for r in (v[1:-1] if isinstance(v, list) else v.values() if isinstance(v, dict) else [v])]
    shots += [r for i in ab.ABILITIES if cd_variants(i) for _, out in cd_variant_layout(i) for r in out.values()]
    reaches = sorted({r for r in shots + list(BLAST_OUT.values()) + list(GRAPPLE_OUT.values()) if r})
    lines = t.split("\n")
    active = origins_lines(lines)
    count = 0
    for i in reversed(range(len(lines))):
        m = re.match(r"^(\t*)PlayerObjectCollision\(C_ENEMY, (-?\d+), (-?\d+), (-?\d+), (-?\d+)\)\s*$", lines[i])
        if not m or not active[i]:
            continue
        ind, l, tp, r, b = m.group(1), *map(int, m.group(2, 3, 4, 5))
        new = [f"{ind}if Object[5].Value3 == 0 // [NoSwap] an extra's shot reaches further"]
        new.append(f"{ind}\t{lines[i].strip()}")
        new.append(f"{ind}else")
        for k, reach in enumerate(reaches):
            if reach > DIAG:  # the Ear Grapple: toward the player's side and downward
                dx, dy = divmod(reach - DIAG, 1000)
                new.append(f"{ind}\tif Object[5].Value3 == {reach}")
                new.append(f"{ind}\t\tif Player.Direction == 0")
                new.append(f"{ind}\t\t\tPlayerObjectCollision(C_ENEMY, {l - dx}, {tp}, {r}, {b + dy})")
                new.append(f"{ind}\t\telse")
                new.append(f"{ind}\t\t\tPlayerObjectCollision(C_ENEMY, {l}, {tp}, {r + dx}, {b + dy})")
                new.append(f"{ind}\t\tend if")
                new.append(f"{ind}\tend if")
                continue
            if reach > RADIAL:  # an area attack: the box grows on every side
                d = reach - RADIAL
                new.append(f"{ind}\tif Object[5].Value3 == {reach}")
                new.append(f"{ind}\t\tPlayerObjectCollision(C_ENEMY, {l - d}, {tp - d}, {r + d}, {b + d})")
                new.append(f"{ind}\tend if")
                continue
            new.append(f"{ind}\tif Object[5].Value3 == {reach}")
            new.append(f"{ind}\t\tif Player.Direction == 0 // facing right: reach toward the enemy's left side")
            new.append(f"{ind}\t\t\tPlayerObjectCollision(C_ENEMY, {l - reach}, {tp}, {r}, {b})")
            new.append(f"{ind}\t\telse")
            new.append(f"{ind}\t\t\tPlayerObjectCollision(C_ENEMY, {l}, {tp}, {r + reach}, {b})")
            new.append(f"{ind}\t\tend if")
            new.append(f"{ind}\tend if")
        new.append(f"{ind}end if")
        lines[i:i + 1] = new
        count += 1
    return "\n".join(lines), count


# ---------------------------------------------------------------- per-character sheets and frame blocks

ORIGINS_PLATFORMS = {"Use_Origins", "Standard"}  # compiled on Origins (docs/soniccd_map.md, top)


def origins_lines(lines):
    """Which lines the v3 compiler keeps on Origins: a `#platform:` line for another platform skips
    everything up to the next `#endplatform` (there is no real nesting)."""
    keep, skipping = [], False
    for line in lines:
        s = line.strip()
        if s.startswith("#platform:"):
            token = s[len("#platform:"):].split("//")[0].strip()
            skipping = token not in ORIGINS_PLATFORMS
        elif s.startswith("#endplatform"):
            skipping = False
        keep.append(not skipping)
    return keep


SONIC_IF = re.compile(r"^(\t*)if Stage\.PlayerListPos == PLAYER_SONIC(?:_A)?\b.*$")


def copy_sonic_blocks(t, expected, name, own=None, extra=None):
    """Most CD objects pick art with one `if` per character (a sheet, sometimes with its frames), with no fallback.
    After each such Sonic block, add one block for any extra (`Stage.PlayerListPos >= 7`): own(extra,
    sonic_block_lines) if that returns lines, else a copy of Sonic's. NoSwap's shared scripts are built with extra=None
    (own then gives the generic art: fixed sheet names every package supplies, or Sonic's); a package's own copy of a
    script with its extra (tools/build_packages.py). Only one of the blocks runs, so frame numbers don't shift."""
    lines = t.split("\n")
    active = origins_lines(lines)
    found = []
    for i, line in enumerate(lines):
        m = SONIC_IF.match(line)
        if not m or not active[i]:
            continue
        ind = m.group(1)
        j, has_else = i + 1, False
        while not (lines[j].startswith(ind + "end if") and not lines[j].startswith(ind + "\t")):
            has_else |= lines[j].startswith(ind + "else")
            j += 1
        body = lines[i + 1:j]
        if any("LoadSpriteSheet" in l or "SpriteFrame" in l for l in body):
            if has_else:
                sys.exit(f"{name}: Sonic art block at line {i + 1} has an else")
            found.append((i, j, ind, body))
    if len(found) != expected:
        sys.exit(f"{name}: found {len(found)} Sonic art blocks (expected {expected})")
    who = extra["name"].title() if extra else "any extra"
    for i, j, ind, body in reversed(found):
        inner = own(extra, body) if own else None
        inner = [ind + "\t" + l for l in inner] if inner else body
        lines[j + 1:j + 1] = [f"{ind}if Stage.PlayerListPos >= {EXTRA_ID} // [NoSwap] {who}"] + inner + [f"{ind}end if"]
    return "\n".join(lines)


EXTRA_ID = 7  # any character ID from here up is an extra (CD's own are 0, 1, 2 and 5)


def ani_frames(extra, anim, count=None):
    """(sheet, x, y, w, h, pivot x, pivot y) of an animation in the extra's CD .ani, repeated to `count`."""
    ani = extras.player_ani(extra, "SonicCDu", fixed=True)  # (its package's: the sheets under their fixed names)
    a = next(x for x in ani["anims"] if x["name"] == anim)
    frames = [(ani["sheets"][f["sheet"]], f["x"], f["y"], f["w"], f["h"], f["px"], f["py"]) for f in a["frames"]]
    if count:
        frames = (frames * count)[:count]
    return frames


def own_frames(anim, count):
    """Block body drawing `count` frames of the extra's own animation (all from one of its sheets); for NoSwap's
    shared copy (no extra), Sonic's."""
    def body(e, _sonic):
        if e is None:
            return None
        frames = ani_frames(e, anim, count)
        sheet = frames[0][0]
        frames = [f if f[0] == sheet else frames[0] for f in frames]  # an object can only use one sheet
        return [f'LoadSpriteSheet("{sheet}")'] + [f"SpriteFrame({px}, {py}, {w}, {h}, {x}, {y})"
                                                   for _, x, y, w, h, px, py in frames]
    return body


# ---------------------------------------------------------------- each extra's HUD / item sheets
# CD picks per-character art by whole-sheet copies at the same coordinates (Display_k.gif, Items2_k.gif...).
# Each extra gets its own copies of Sonic's: life icon at 187,189, signpost face at 34,132, and results
# text laid out like Knuckles' (his name is too long for "SONIC GOT" as well): "<NAME> GOT" and "<NAME>"
# in the spare rows at 35,257, with the "MADE A GOOD" line taken from Knuckles' sheet (name blanked).
# The results name in fixed boxes (docs/plan-b-modular-characters.md step 3b item 6): frames NoSwap's ActFinish draws for
# any extra, from its package's Display_x.gif. (pivot x, width, sheet x, sheet y), 16 high. "<NAME> GOT" is centred on
# x 68 like Knuckles' "KNUCKLES GOT" (frame 0): each extra's art sits in the box where its old frame's pivot put it, so
# every pixel lands where it did; up to 220 px wide. "<NAME>" (frame 22, "... FUTURE IN <NAME>") ends at x 48, the
# left part of the same art, in its own box in rows added below the game's sheet (up to 256 px).
NAME_GOT_BOX = (-42, 221, 35, 257)
NAME_BOX = (-208, 256, 0, 274)
DISPLAY_X_HEIGHT = 290  # Display.gif's 274 rows and NAME_BOX's 16


# CD's results font, letter by letter: (sheet, x, y, width), all 16 high. Cut from GAME TIME OVER,
# SONIC GOT, FUTURE IN, MADE A GOOD and Knuckles' "KNUCKLES GOT" (for L). Letters CD never draws are
# made from others: B from R's top half and D's bottom half, W from an upside-down M, P from R without its leg, J from U
# without the top of its left stem, X and Y drawn in the font's style, Z from an N on its side.
CD_LETTERS = {
    "A": ("Display.gif", 16, 189, 14), "C": ("Display.gif", 56, 206, 16), "D": ("Display.gif", 240, 240, 15),
    "E": ("Display.gif", 50, 189, 13), "F": ("Display.gif", 0, 223, 15), "G": ("Display.gif", 1, 189, 13),
    "I": ("Display.gif", 50, 206, 5), "L": ("Display_k.gif", 116, 257, 12), "M": ("Display.gif", 32, 189, 16),
    "N": ("Display.gif", 33, 206, 15), "O": ("Display.gif", 224, 240, 15), "R": ("Display.gif", 170, 189, 13),
    "S": ("Display_k.gif", 146, 257, 16), "T": ("Display.gif", 66, 189, 13), "H": ("Display.gif", 153, 206, 15),
    "V": ("Display.gif", 140, 189, 14), "U": ("Display.gif", 16, 223, 16), "K": ("Display_k.gif", 100, 257, 15),
}


def cd_letter(c):
    from PIL import Image
    if c == "W":
        return cd_letter("M").transpose(Image.FLIP_TOP_BOTTOM)
    if c == "Z":
        n = cd_letter("N").transpose(Image.ROTATE_90)
        return n.crop(n.getbbox()) if n.getbbox() else n
    if c == "P":  # R without its leg: the bowl, then only the stem (and its shadow column)
        img = cd_letter("R").copy()
        for y in range(11, 16):
            for x in range(5, img.width):
                img.putpixel((x, y), 0)
        return img
    if c == "J":  # U without the top of its left stem: the hook
        img = cd_letter("U").copy()
        for y in range(1, 7):
            for x in range(5):
                img.putpixel((x, y), 0)
        return img
    if c in ("Y", "X"):  # drawn in the font's own style (body 6, shadow 1 right and below, like T and I)
        body = {"Y": ["####....####", "####....####", "####....####", ".####..####.", "..########..",
                      "...######...", "....####....", "....####....", "....####....", "....####....",
                      "....####....", "....####....", "....####...."],
                "X": ["####....####", "####....####", ".####..####.", "..########..", "...######...",
                      "....####....", "....####....", "...######...", "..########..", ".####..####.",
                      "####....####", "####....####", "####....####"]}[c]
        img = Image.new("P", (13, 16), 0)
        img.putpalette(cd_letter("I").getpalette())
        for y, row in enumerate(body):
            for x, ch in enumerate(row):
                if ch == "#":
                    img.putpixel((x, y + 1), 6)
        for y in range(15):
            for x in range(12):
                if img.getpixel((x, y)) == 6:
                    for dx, dy in ((1, 0), (0, 1)):
                        if img.getpixel((x + dx, y + dy)) == 0:
                            img.putpixel((x + dx, y + dy), 1)
        return img
    if c == "B":
        r, d = cd_letter("R"), cd_letter("D")
        img = Image.new("P", (max(r.width, d.width), 16), 0)
        img.paste(r.crop((0, 0, r.width, 8)), (0, 0))
        img.paste(d.crop((0, 8, d.width, 16)), (0, 8))
        return img
    if c not in CD_LETTERS:
        sys.exit(f"CD results font has no letter {c!r}: add it to CD_LETTERS")
    sheet, x, y, w = CD_LETTERS[c]
    return Image.open(SPRITES_IN / "Global" / sheet).crop((x, y, x + w, y + 16))


def cd_word(text, space=8):
    from PIL import Image
    letters = [None if c == " " else cd_letter(c) for c in text]
    width = sum(space if l is None else l.width + 1 for l in letters) - 1
    img = Image.new("P", (width, 16), 0)
    x = 0
    for l in letters:
        if l is None:
            x += space
            continue
        img.paste(l, (x, 0))
        x += l.width + 1
    return img


EXTRA_SHEETS = {"Global/Display.gif": "Global/Display_x.gif", "Global/Items2.gif": "Global/Items2_x.gif"}
RETIRED_SHEETS = [f"Global/{s}_x{e['n']}.gif" for s in ("Display", "Items2") for e in EXTRAS]  # (before the packages)


def extra_sheets(e=None):
    """{sheet name: image} of CD's per-extra copies of Display.gif and Items2.gif (whole-sheet copies at the game's
    coordinates, as CD does for its own characters: Display_k.gif, Items2_k.gif...). An extra's: its life icon at
    187,189, its signpost face at 34,132, and results text laid out like Knuckles' (his name is too long for "SONIC
    GOT" as well): "<NAME> GOT" and "<NAME>" in the NAME_GOT_BOX / NAME_BOX boxes, with the "MADE A GOOD" line taken
    from Knuckles' sheet (name blanked). e=None: NoSwap's placeholders, Sonic's art with empty name boxes (NoSwap's
    own scripts load them for an extra whose package isn't installed)."""
    from PIL import Image
    display = Image.open(SPRITES_IN / "Global" / "Display.gif")
    knux = Image.open(SPRITES_IN / "Global" / "Display_k.gif")
    items2 = Image.open(SPRITES_IN / "Global" / "Items2.gif")
    d = Image.new("P", (display.width, DISPLAY_X_HEIGHT), 0)
    d.putpalette(display.getpalette())
    d.paste(display, (0, 0))
    d.paste(knux.crop((0, 240, 256, 256)), (0, 240))  # "      MADE A GOOD"
    d.paste(0, (NAME_GOT_BOX[2], NAME_GOT_BOX[3], 256, 274))
    i2 = items2.copy()
    if e:
        manifest = ui_manifest(e, "ui")
        ui = Image.open(manifest["sheet"])
        cut = lambda key: ui.crop((manifest["frames"][key][0], manifest["frames"][key][1],
                                   manifest["frames"][key][0] + manifest["frames"][key][2],
                                   manifest["frames"][key][1] + manifest["frames"][key][3]))
        s1_style = lambda img: img.point(lambda i: i - 128 if i >= 128 else i)  # CD uses the plain slots
        d.paste(s1_style(cut("life_icon")), (187, 189))
        got = cd_word(e["name"] + " GOT")
        n = cd_word(e["name"]).width
        pivot, width, x, y = NAME_GOT_BOX
        at = x + (68 - got.width // 2) - pivot  # (its old frame: SpriteFrame(68 - w / 2, 0, w, 16, ...))
        if at < x or at + got.width > x + width:
            sys.exit(f"{e['name']}: results name too wide ({got.width} px)")
        d.paste(got, (at, y))
        pivot, width, x, y = NAME_BOX
        at = x + (48 - n) - pivot  # (its old frame: SpriteFrame(48 - n, 0, n, 16, ...), the art's first n columns)
        if at < x:
            sys.exit(f"{e['name']}: results name too wide ({n} px)")
        d.paste(got.crop((0, 0, n, 16)), (at, y))
        i2.paste(s1_style(cut("sign_face")), (34, 132))
    return {"Global/Display_x.gif": d, "Global/Items2_x.gif": i2}


def write_extra_sheets(sprites_out, e=None):
    for rel, img in extra_sheets(e).items():
        (sprites_out / rel).parent.mkdir(parents=True, exist_ok=True)
        save_sheet(img, sprites_out / rel)


def own_sheets(e, body):
    """A Sonic sheet block for any extra: the fixed-name Display/Items2 copies (the package's), anything else unchanged."""
    out = []
    for l in body:
        for sheet, copy in EXTRA_SHEETS.items():
            l = l.replace(f'"{sheet}"', f'"{copy}"')
        out.append(l.strip())
    return out


SHEET_CHAINS = {  # file -> Sonic art blocks in it (docs/soniccd_map.md sections B-E); extras copy Sonic's
    "Global/ActFinish.txt": 1, "Global/AttractMode.txt": 1, "Global/BlueShield.txt": 1, "Global/DeathEvent.txt": 1,
    "Global/Explosion.txt": 1, "Global/GoalPost.txt": 1, "Global/HUD.txt": 1, "Global/SignPost.txt": 1,
    "Global/SmokePuff.txt": 1, "Global/SpecialRing.txt": 1, "FlowerPod/PodSeed.txt": 1, "R5/BossExplosion.txt": 1,
    "R1/TunnelPath.txt": 1, "R3/ScoreChute.txt": 1, "R6/IceBlock.txt": 1,
    **{f"TitleCards/R{n}_TitleCard.txt": 1 for n in (1, 3, 4, 5, 6, 7, 8)},
}


def build_act_finish(t):
    t = copy_sonic_blocks(t, 1, "act finish sheet", own=own_sheets)
    # Results text for extras, laid out like Knuckles', from the fixed boxes (extra_sheets)
    frame = lambda box, comment: "SpriteFrame({}, 0, {}, 16, {}, {}) // {}".format(*box, comment)
    def for_extras(lines):
        return [f"\tif Stage.PlayerListPos >= {EXTRA_ID} // [NoSwap] extras: their own name (their package's "
                "Display_x.gif), laid out like Knuckles'"] + ["\t\t" + l for l in lines]
    head = "\tif Stage.PlayerListPos == PLAYER_KNUCKLES\n\t\t// 0 - \"KNUCKLES GOT\"\n"
    i = t.index(head)
    j = t.index("\tend if\n", i) + len("\tend if\n")
    got = for_extras([frame(NAME_GOT_BOX, "0 - \"<NAME> GOT\"")])
    t = t[:i] + "\n".join(got) + "\n\telse\n" + "".join("\t" + l + "\n" for l in t[i:j].rstrip("\n").split("\n")) + "\tend if\n" + t[j:]
    head = "\tif Stage.PlayerListPos == PLAYER_KNUCKLES\n\t\t// 20 - \"         MADE A GOOD\"\n"
    i = t.index(head)
    j = t.index("\tend if\n", i) + len("\tend if\n")
    good = for_extras(["SpriteFrame(-41, 0, 256, 16, 0, 240) // 20 - \"      MADE A GOOD\"",
                       "SpriteFrame(-12, 0, 136, 16, 0, 223) // 21 - \"FUTURE IN\"",
                       frame(NAME_BOX, "22 - \"<NAME>\"")])
    t = t[:i] + "\n".join(good) + "\n\telse\n" + "".join("\t" + l + "\n" for l in t[i:j].rstrip("\n").split("\n")) + "\tend if\n" + t[j:]
    anchor = "\t\tif Stage.PlayerListPos == PLAYER_KNUCKLES\n\t\t\t// \"KNUCKLES\"\n\t\t\tDrawSpriteScreenXY(22, Object.XPos, 65)\n\t\tend if\n"
    t = patch(t, anchor, anchor + f"\t\tif Stage.PlayerListPos >= {EXTRA_ID} // [NoSwap] the extra's name\n"
              "\t\t\tDrawSpriteScreenXY(22, Object.XPos, 65)\n\t\tend if\n", "good future name")
    return t


# ---------------------------------------------------------------- special stage

# The special stage results' continues row (Special/StageFinish.txt frames 27-28, "Small Foot-Tapping Player Icons",
# drawn once per continue): the extra's own foot-tapping minis (its "ui" manifest's mini_1 / mini_2, the ones Sonic 1 and
# 2's continue screens show), in fixed boxes on copies of the results sheet, one per language (noswap_common.UiSheets:
# "Special/ScoreScreen*_NoSwap.gif", the game's sheet with the boxes below it). NoSwap ships them with the boxes empty,
# each package with its own art. Only StageFinish loads the copies (Special/PauseMenu keeps the game's sheets).
SCORE_SHEETS = [f"Special/ScoreScreen{lang}.gif" for lang in ("", "_FR", "_IT", "_DE", "_ES")]
MINI_KEYS = ["mini_1", "mini_2"]


def mini_art(key, extra):
    """The extra's foot-tapping mini (CD uses the plain palette slots: its Sonic 1-style 128+ slots move down)."""
    from PIL import Image
    manifest = ui_manifest(extra, "ui")
    x, y, w, h = manifest["frames"][key]
    return Image.open(manifest["sheet"]).crop((x, y, x + w, y + h)).point(lambda i: i - 128 if i >= 128 else i)


def mini_pivot(key, img):
    """Centred on Sonic's 16x23 mini (drawn from its top left), its feet where his are."""
    w, h = img.size
    return 8 - w // 2, 23 - h


_SCORE_UI = None


def score_ui():
    global _SCORE_UI
    if _SCORE_UI is None:
        _SCORE_UI = UiSheets(SPRITES_IN, {s: MINI_KEYS for s in SCORE_SHEETS}, mini_art, mini_pivot)
        sizes = {_SCORE_UI.size[s] for s in SCORE_SHEETS}
        if len(sizes) != 1:  # (one set of frames serves every language: the boxes must be in the same places)
            sys.exit(f"special results sheets differ in size: {sizes}")
    return _SCORE_UI


def use_sheet_copies_v3(t, sheets, name):
    """v3 use_sheet_copy: in ObjectStartup, each LoadSpriteSheet of one of `sheets` loads its copy while an extra plays."""
    start = t.index("sub ObjectStartup")
    end = t.index("end sub", start)
    lines = t[start:end].split("\n")
    hits = [i for i, l in enumerate(lines) for s in sheets if l.strip() == f'LoadSpriteSheet("{s}")']
    if len(hits) != len(sheets):
        sys.exit(f"{name}: found {len(hits)} of the {len(sheets)} sheet loads in ObjectStartup")
    for i in reversed(hits):
        ind = line_indent(lines[i])
        sheet = lines[i].strip()[len('LoadSpriteSheet("'):-2]
        lines[i:i + 1] = [f"{ind}if Stage.PlayerListPos >= {EXTRA_ID} // [NoSwap] same sheet plus the extra's art "
                          "(its package's copy)",
                          f'{ind}\tLoadSpriteSheet("{copy_name(sheet)}")', f"{ind}else", f"{ind}\t{lines[i].strip()}",
                          f"{ind}end if"]
    return t[:start] + "\n".join(lines) + t[end:]


def build_stage_finish(t):
    t = copy_sonic_blocks(t, 1, "special results icons", own=lambda e, body: [
        "// its own foot-tapping minis (its package's Special/ScoreScreen*_NoSwap.gif)",
        score_ui().frame("mini_1", "27"), score_ui().frame("mini_2", "28")])
    t = use_sheet_copies_v3(t, SCORE_SHEETS, "special results sheets")
    # Origins' result/retry screen reads the character itself and can't handle an extra's ID
    # (blank results in S1/S2): stand in as Sonic until it answers. Reserved slot 5 is free here.
    anchor = "\t\tEngineCallback(NOTIFY_SPECIAL_RETRY)\n"
    t = patch(t, anchor,
              "\t\tObject[5].Value0 = 0 // [NoSwap] Origins can't handle an extra's ID here: stand in as Sonic\n"
              "\t\tif Stage.PlayerListPos >= 7\n"
              "\t\t\tObject[5].Value0 = Stage.PlayerListPos\n"
              "\t\t\tStage.PlayerListPos = 0\n"
              "\t\tend if\n" + anchor, "special retry guard")
    anchor = "\tcase STAGEFINISH_SAVE\n\t\tif game.callbackResult >= false\n"
    return patch(t, anchor, anchor +
                 "\t\t\tif Object[5].Value0 > 0 // [NoSwap] back to the extra\n"
                 "\t\t\t\tStage.PlayerListPos = Object[5].Value0\n"
                 "\t\t\tend if\n", "special retry restore")


# ---------------------------------------------------------------- sprites

SPRITES_IN = REPO / "extracted" / "SonicCD" / "Data" / "Sprites"
SPRITES_OUT = REPO / "mods" / "NoSwap" / "SonicCDu" / "Data" / "Sprites"


def build_select(t):
    """Y on a card in Origins' character select opens the stage select as that character: the DLL confirms
    the card and flips game.callbackParam3 (the magic number while the select is open: CD_SHOT_MAGIC)."""
    t = patch(t, "\t\tEngineCallback(NOTIFY_CHARACTER_SELECT)\n\t\t\n\t\tObject.State = SELECT_RECIEVERESULT\n",
              "\t\tgame.callbackParam3 = 0x4E53 // [NoSwap] the magic number 0x4E53593F: Y in the character select sets it to 1\n"
              "\t\tgame.callbackParam3 <<= 16\n\t\tgame.callbackParam3 += 0x593F\n"
              "\t\tEngineCallback(NOTIFY_CHARACTER_SELECT)\n\t\t\n\t\tObject.State = SELECT_RECIEVERESULT\n", "y flag set")
    anchor = "\tcase SELECT_RECIEVERESULT\n\t\tif game.callbackResult > 0\n"
    t = patch(t, anchor, anchor +
              "\t\t\tif game.callbackParam3 == 1 // [NoSwap] Y on the card: this character's stage select, without saving\n"
              "\t\t\t\tgame.callbackParam3 = 0\n"
              "\t\t\t\tStopMusic()\n"
              "\t\t\t\tgame.callbackParam0 = true\n"
              "\t\t\t\tEngineCallback(NOTIFY_LEVEL_SELECT_MENU)\n"
              "\t\t\t\tOptions.GameMode = 0\n"
              "\t\t\t\tStage.ActiveList = PRESENTATION_STAGE\n"
              "\t\t\t\tStage.ListPos = 3 // the stage select\n"
              "\t\t\t\tLoadStage()\n"
              "\t\t\tend if\n"
              "\t\t\tgame.callbackParam3 = 0\n", "y stage select")
    return patch(t, "\t\t\tif game.callbackResult == 0\n\t\t\t\t// Go back to the Selection phase\n",
                 "\t\t\tif game.callbackResult == 0\n\t\t\t\tgame.callbackParam3 = 0 // [NoSwap]\n\t\t\t\t// Go back to the Selection phase\n",
                 "y flag reset")


SS_FRAMES = 91  # Special/Sonic.txt's frames: 0 shadow, 1-80 animations, 81-90 the Time Stone grab


SPECIAL_BALL = "Special/NoSwap_Extra.gif"  # a package's spin-ball sheet (NoSwap ships a blank placeholder)


def build_special_player(t, extra=None):
    """The special stage shows the player from behind, and the extras' sheets have no back views. They roll through it
    instead: every frame after the shadow is their own spin ball (their CD "Jumping" frames, or their own "Rolling" curl
    if their jump isn't a ball; unchanged, in order, so each animation spins it), on a small sheet of their own,
    SPECIAL_BALL. That's each package's own copy of this script (extra); NoSwap's own (extra=None) shows an extra as
    Sonic (its package isn't installed), as Sonic 1 / 2's do."""
    t = copy_sonic_blocks(t, 2, "special player", extra=extra,
                          own=lambda e, body: special_ball_load(e) if e and "LoadSpriteSheet" in body[0] else None)
    start = t.index("\t// Player Frames\n")
    end = t.index("\nend sub", start)
    # as written: one braking pair per character (3 vanilla, any extra's, 1 runs) and the fall twice (Tails' own)
    if t[start:end].count("SpriteFrame(") != SS_FRAMES + 2 * (3 + 1) + 18:
        sys.exit("special player: frame count changed")
    if extra is None:
        return t
    frames = special_ball(extra)[1]
    return (t[:start] + f"\tif Stage.PlayerListPos < {EXTRA_ID} // [NoSwap] the extra: its own frames below\n"
            + t[start:end] + "\n\telse\n" + "".join(f"\t\t{l}\n" for l in frames) + "\tend if" + t[end:])


def special_ball_load(e):
    return [f'LoadSpriteSheet("{SPECIAL_BALL}")'] + own_palette_lines(e)


def special_ball(e):
    """(sheet image, frames) of the extra's spin ball."""
    from PIL import Image
    ani = extras.player_ani(e, "SonicCDu")
    jump = next(a for a in ani["anims"] if a["name"] == ball_animation(e))
    sheets = [Image.open(extras.player_sheet_path(e, "SonicCDu", s)) for s in ani["sheets"]]
    shadow = Image.open(SPRITES_IN / "Special/Sonic.gif").crop((210, 377, 250, 385))  # SEGA's shadow
    crops, rects, x = {}, [], 42
    for f in jump["frames"]:
        key = (f["sheet"], f["x"], f["y"], f["w"], f["h"])
        if key not in crops:
            crops[key] = (sheets[f["sheet"]].crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])), x)
            x += f["w"] + 1
        rects.append((crops[key][1], 1, f["w"], f["h"]))
    # the engine keeps sheets at power-of-two sizes (its row stride is a shift): any other width
    # scrambles the picture (seen in Sonic 2's special stage, 2026-09-26)
    pow2 = lambda n: 1 << max(0, n - 1).bit_length()
    out = Image.new("P", (pow2(x), pow2(max(10, max(c.height for c, _ in crops.values()) + 2))), 0)
    out.putpalette(sheets[0].getpalette())
    out.paste(shadow, (1, 1))
    for img, px in crops.values():
        out.paste(img, (px, 1))
    frames = ["SpriteFrame(-20, -4, 40, 8, 1, 1) // shadow"]
    for i in range(1, SS_FRAMES):  # the ball stands on the floor, like Sonic's feet
        bx, by, w, h = rects[(i - 1) % len(rects)]
        frames.append(f"SpriteFrame({-(w // 2)}, {-h}, {w}, {h}, {bx}, {by})")
    return out, frames


def warp(extra=None):
    """The time-warp cutscene bounces the character: an extra shows its own spring frames (from its own player sheet)
    in its package's copy; NoSwap's own shows Sonic's."""
    return lambda t: copy_sonic_blocks(t, 1, "warp", own=own_frames("Bouncing", 5), extra=extra)


# ---------------------------------------------------------------- character packages (tools/build_packages.py)
PACKAGE_SCRIPTS = {"Special/Sonic.txt": lambda e: lambda t: build_special_player(t, e), "Global/WarpSonic.txt": warp}


def package_files(e, game_dir):
    """A character package's own CD files, besides its player script: its copies of the scripts that draw it from
    its own sheets (PACKAGE_SCRIPTS), its palette files, its spin-ball sheet and its Display_x / Items2_x copies."""
    build_scripts({rel: make(e) for rel, make in PACKAGE_SCRIPTS.items()}, BASE, game_dir / "Data" / "Scripts")
    package_palettes(e, game_dir / "Data" / "Palettes")
    out = game_dir / "Data" / "Sprites" / SPECIAL_BALL
    out.parent.mkdir(parents=True, exist_ok=True)
    save_sheet(special_ball(e)[0], out)
    write_extra_sheets(game_dir / "Data" / "Sprites", e)
    score_ui().write(game_dir / "Data" / "Sprites", e)  # its continue minis on the results sheets


def placeholders():
    """NoSwap's own copies of the files each package supplies (the DLL only serves a package's file for a name NoSwap
    ships), and no per-extra copies any more."""
    from PIL import Image
    write_extra_sheets(SPRITES_OUT)
    score_ui().write(SPRITES_OUT)  # (the boxes empty)
    blank = Image.new("P", (16, 16), 0)
    blank.putpalette([0] * 768)
    save_sheet(blank, SPRITES_OUT / SPECIAL_BALL)
    for rel in RETIRED_SHEETS + [f"Special/NoSwap_{e['file']}.gif" for e in EXTRAS]:
        (SPRITES_OUT / rel).unlink(missing_ok=True)
    palette_placeholders()


WATER_SCRIPTS = [f"R4/BGEffects{v}.txt" for v in ("A1", "A2", "B", "B2", "C", "C2", "D", "D2")]
BUILDERS = {
    "Title/Select.txt": build_select,
    **{rel: (lambda rel: lambda t: extra_water_palettes(t, 1, rel))(rel) for rel in WATER_SCRIPTS},
    # Special stage (doesn't load the global objects): extras roll through it as their spin ball
    "Special/Sonic.txt": build_special_player,
    "Special/StageFinish.txt": build_stage_finish,
    "Special/PauseMenu.txt": lambda t: copy_sonic_blocks(t, 1, "special pause"),
    "Players/PlayerObject.txt": build_player_object,
    **{f: (lambda n, f: lambda t: copy_sonic_blocks(t, n, f, own=own_sheets))(n, f) for f, n in SHEET_CHAINS.items()},
    "Global/ActFinish.txt": build_act_finish,
    "Global/SignPost.txt": lambda t: copy_sonic_blocks(t, 1, "signpost", own=own_sheets),
    "Global/DeathEvent.txt": lambda t: copy_sonic_blocks(t, 1, "death event", own=own_sheets),
    "Global/WarpSonic.txt": warp(),
}


def build_water(t):
    """Extras that don't breathe (Metal) keep the air countdown at its start while underwater: the player script's
    NoSwap_NoBreathing."""
    anchor = "\telse\n\t\tif Player.AirTimer == 0\n\t\t\tObject.State = WATER_CREATEBUBBLE_1\n\t\tend if\n"
    t = patch(t, anchor, anchor + "\t\tCallFunction(NoSwap_NoBreathing) // [NoSwap] extras that don't breathe "
              "(its player script's)\n", "no breathing")
    return __import__("water_walk").cd_water_mark(t)  # (water walk: the water's here this frame)


def add_enemy_reach(builders):
    """Every enemy script (PlayerObjectCollision(C_ENEMY, ...)) learns about shot reach."""
    for path in sorted(BASE.rglob("*.txt")):
        rel = str(path.relative_to(BASE))
        if not re.search(r"PlayerObjectCollision\(C_ENEMY, -?\d+, -?\d+, -?\d+, -?\d+\)", path.read_text(errors="ignore")):
            continue  # (one Missions-only enemy computes its box: it keeps its normal range)
        inner = builders.get(rel, lambda t: t)

        def build(t, inner=inner, rel=rel):
            t, n = enemy_reach(inner(t), rel)
            if n == 0:
                sys.exit(f"{rel}: no C_ENEMY collision with plain numbers")
            return t
        builders[rel] = build
    return builders


# Walls Knuckles breaks by walking into them (R1 and R5's BreakWall; S1/S2: noswap_common.knux_like's walls copy): an
# extra with abilities.py breaks_walls (Heavy) too. v3 has no shared value, so its player script marks reserved slot 5's
# PropertyValue (a byte nothing else uses) at startup; entities are cleared when a stage loads, before startups run.
CD_BREAKS_WALLS = 1
CD_JUGGERNAUT = 4  # added to it while Heavy's charge is past his top speed (charge_after; cd_juggernaut)
CD_WALL_SCRIPTS = ["R1/BreakWall.txt", "R5/BreakWall.txt"]


def cd_break_walls(t, name):
    m = re.search(r"^(\t*)if Stage\.PlayerListPos == PLAYER_KNUCKLES\n\1\tCheckResult = true\n\1end if\n", t, re.M)
    if not m or t.count("if Stage.PlayerListPos == PLAYER_KNUCKLES\n") != 1:
        sys.exit(f"{name}: expected one Knuckles check setting CheckResult")
    ind = m.group(1)
    add = (f"{ind}if Stage.PlayerListPos >= 7 // [NoSwap] an extra that breaks walls like Knuckles (abilities.py breaks_walls)\n"
           f"{ind}\tif Object[5].PropertyValue == {CD_BREAKS_WALLS} // (its player script sets it at startup)\n"
           f"{ind}\t\tCheckResult = true\n{ind}\tend if\n"
           f"{ind}\tif Object[5].PropertyValue == {CD_BREAKS_WALLS + CD_JUGGERNAUT} // (and at full charge: cd_juggernaut)\n"
           f"{ind}\t\tCheckResult = true\n{ind}\tend if\n{ind}end if\n")
    return t[:m.end()] + add + t[m.end():]


for _rel in CD_WALL_SCRIPTS:
    BUILDERS[_rel] = (lambda rel: lambda t: cd_break_walls(t, rel))(_rel)


# Fire hazards (Sonic CD has no fire shield, so no fire test of its own): R3's piston fireballs and R8's Big Bomb fireballs
# don't hurt an extra with abilities.py fire_immune (Blaze), whose player script marks reserved slot 5's PropertyValue 2
# at startup (cd_break_walls' byte: an extra has one or the other).
CD_FIRE_IMMUNE = 2
CD_FIRE_SCRIPTS = ["R3/Fireball.txt", "R8/BBFireball.txt"]


def cd_fire_hit(t, name):
    m = re.search(r"^(\t*)CallFunction\(Player_Hit\)\n", t, re.M)
    if not m or t.count("CallFunction(Player_Hit)") != 1:
        sys.exit(f"{name}: expected one Player_Hit call")
    ind = m.group(1)
    new = (f"{ind}if Stage.PlayerListPos >= 7 // [NoSwap] fire never hurts an extra with abilities.py fire_immune (Blaze)\n"
           f"{ind}\tif Object[5].PropertyValue != {CD_FIRE_IMMUNE} // (its player script sets it at startup)\n"
           f"{ind}\t\tCallFunction(Player_Hit)\n{ind}\tend if\n{ind}else\n{ind}\tCallFunction(Player_Hit)\n{ind}end if\n")
    return t[:m.start()] + new + t[m.end():]


for _rel in CD_FIRE_SCRIPTS:
    BUILDERS[_rel] = (lambda rel: lambda t: cd_fire_hit(t, rel))(_rel)
BUILDERS["R4/Water.txt"] = build_water
BUILDERS["Global/Monitor.txt"] = cd_surge_monitor  # (and monitor_swap's count: after the shots' builders, below)
BUILDERS["Global/Ring.txt"] = cd_magnet_ring
BUILDERS["Global/Spikes.txt"] = shell_spikes_object
BUILDERS["Global/MovingSpikes.txt"] = shell_spikes_object
add_enemy_reach(BUILDERS)
shots_v3.add_builders(BUILDERS)  # (after enemy_reach: extras' shots, tools/shots_v3.py)


# Heavy's full charge (abilities.py charge, "Juggernaut"): while it's past his top speed his player script adds
# CD_JUGGERNAUT to reserved slot 5's PropertyValue, and the enemies' and bosses' scripts (never hazards) don't hurt him:
# each Player_Hit call is skipped then, and a hurt written out (the bosses' Player.State = Player_State_GotHit) has its
# enclosing block skipped. Bosses take his hits already (his charge is a touch attack: cd_touch_attacks, NoSwap_ShotAttack)
CD_JUGGERNAUT_SCRIPTS = [
    "R1/Bullet.txt", "R1/Boss_Foot.txt", "R1/Boss_Face.txt", "R1/Boss_Leg.txt", "R3/Bomb.txt", "R3/Blade.txt",
    "R4/SkimmerBullet.txt", "R4/TagaSpike.txt", "R4/BossBullet.txt", "R4/Eggman1.txt", "R4/Eggman2.txt",
    "R5/NoroNoro.txt", "R5/BossBomb.txt", "R5/BossSpikes.txt", "R5/Kemusi.txt", "R5/SBullet.txt", "R6/BossSpike.txt",
    "R6/PohBeeBullet.txt", "R6/Bomb.txt", "R6/EggmanMobile.txt", "R6/Minomusi.txt", "R7/Eggman.txt",
    "R7/KabasiraShot.txt", "R7/Hotaru.txt", "R7/MetalSonic.txt", "R8/HotaruLaser.txt", "R8/BossWing.txt",
    "R8/PohBee.txt", "R8/MechaBu.txt", "R8/EggMobile.txt", "Mission/MechaBu2.txt", "Mission/PohBee3.txt",
    "Mission/Bomb2.txt", "Mission/Minomusi2.txt", "Mission/Kemusi2.txt", "Mission/Boss_Foot2.txt",
    "Mission/Boss_Leg2.txt", "Mission/Boss_Face2.txt"]


def cd_juggernaut(t, name):
    """One enemy / boss script: no hurt from it while Heavy's charge is past his top speed (see above)."""
    tag = f"[NoSwap] Heavy's full charge (Object[5].PropertyValue {CD_JUGGERNAUT} and up): enemies can't hurt him"
    guard = f"if Object[5].PropertyValue < {CD_JUGGERNAUT} // {tag}"
    lines = t.split("\n")
    n = 0

    def depth(l):
        return len(l) - len(l.lstrip("\t"))

    def code(l):  # (not blank, not a comment or a #platform line)
        return l.strip() and not l.strip().startswith(("//", "#"))
    for k in reversed(range(len(lines))):
        if lines[k].strip() != "Player.State = Player_State_GotHit":
            continue
        d = depth(lines[k]) - 1  # the block holding it: its opener (an if or an else) and its end
        o = next(i for i in range(k - 1, -1, -1) if code(lines[i]) and depth(lines[i]) <= d)
        if depth(lines[o]) != d or not (lines[o].strip().startswith("if ") or lines[o].strip() == "else"):
            sys.exit(f"{name}: a written-out hurt's block doesn't open with an if or an else: look at it")
        e = next(i for i in range(k + 1, len(lines)) if code(lines[i]) and depth(lines[i]) <= d)
        if depth(lines[e]) != d or lines[e].strip() not in ("end if", "else"):
            sys.exit(f"{name}: a written-out hurt's block doesn't end with an end if or an else: look at it")
        ind = "\t" * d
        body = [("\t" + l if l.strip() and not l.startswith("#") else l) for l in lines[o + 1:e]]
        lines[o + 1:e] = [f"{ind}\t{guard}"] + body + [f"{ind}\tend if"]
        n += 1
    out = []
    for l in lines:
        if l.strip() == "CallFunction(Player_Hit)":
            ind = l[:depth(l)]
            out += [f"{ind}{guard}", f"{ind}\tCallFunction(Player_Hit)", f"{ind}end if"]
            n += 1
        else:
            out.append(l)
    if not n:
        sys.exit(f"{name}: no hurt found (cd_juggernaut)")
    return "\n".join(out)


if ab.with_ability("charge"):
    for _rel in CD_JUGGERNAUT_SCRIPTS:
        BUILDERS[_rel] = __import__("shots_v4").compose(BUILDERS.get(_rel),
                                                         (lambda rel: lambda t: cd_juggernaut(t, rel))(_rel))
BUILDERS["Global/Monitor.txt"] = __import__("shots_v4").compose(  # monitor_swap counts every break (tools/monitor_swap.py)
    BUILDERS["Global/Monitor.txt"], __import__("monitor_swap").cd_monitor)
__import__("psycho_grab").cd_add_builders(BUILDERS, BASE)  # (Silver's Psychokinesis: the grabbable badniks, after the rest)
BUILDERS["Global/BrokenMonitor.txt"] = __import__("shots_v4").compose(  # jewel_thief: Rouge's 20 rings (tools/treasure_sense.py)
    BUILDERS.get("Global/BrokenMonitor.txt"), __import__("treasure_sense").cd_broken_monitor)


# Scripts earlier builds wrote that the game's own versions now replace (extras save like the vanilla
# characters since they're real kinds in Origins' character select; the picker in Select is gone)
RETIRED = ["R8/FadeScreen.txt"]


if __name__ == "__main__":
    if os.environ.get("NOSWAP_SCRIPTS_OUT"):  # just the player script, into a package (tools/build_packages.py)
        build_scripts({"Players/PlayerObject.txt": build_player_object}, BASE, Path(os.environ["NOSWAP_SCRIPTS_OUT"]))
        sys.exit()
    extras.stash_all_player_art()  # (sheet2ani's player .ani and sheets: packages ship them, NoSwap doesn't)
    for rel in RETIRED:
        (OUT / rel).unlink(missing_ok=True)
    (SPRITES_OUT / "Title" / "Select_NoSwap.gif").unlink(missing_ok=True)
    placeholders()
    build_scripts(BUILDERS, BASE, OUT)
