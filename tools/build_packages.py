#!/usr/bin/env python3
"""Build the character packages (docs/plan-b-modular-characters.md): per-character player scripts (step 3a) and UI
sheets (step 3b item 3).

For Sonic 1 and Sonic 2:
- NoSwap's own Players/PlayerObject.txt is rebuilt with no extra's moves (NOSWAP_KEEP=none);
- each extra gets mods/NoSwap/characters/<art folder>/<game>/Data/Scripts/Players/PlayerObject.txt with only its own
  moves. The DLL serves it while that extra plays (its CreateFileW hook), so the game never compiles anyone else's.
- each extra gets its own copies of the S1/S2 UI sheets ("<name>_NoSwap.gif": HUD, act results, monitor, signpost,
  continue, S1 ending), the same size and layout as NoSwap's (which have empty boxes), with its art in the fixed boxes
  the shared scripts draw (noswap_common.UiSheets; package_sprites in each game's builder).
- each extra gets its own Special/PlayerObject.txt (step 3b item 4) with only its own special stage case, and the art
  it loads under fixed names NoSwap ships placeholders for (package_special in each game's builder).
Each package also gets its noswap_character.json (the DLL finds packages by it).

For Sonic CD (docs/plan-b-modular-characters.md step 3b item 6), the same player script split: NoSwap's own
SonicCDu/Data/Scripts/Players/PlayerObject.txt without any extra's moves, each package's with only its own
(build_soniccd.py with NOSWAP_KEEP). Each package also gets its own copies of the CD scripts that draw it from its own
sheets (the special stage's Special/Sonic.txt, the time warp's Global/WarpSonic.txt) and its CD sheets under the fixed
names NoSwap ships placeholders for (Display_x.gif, Items2_x.gif, Special/NoSwap_Extra.gif): build_soniccd.package_files.

For Sonic 3 & Knuckles (docs/plan-b-modular-characters.md step 3b item 7), the DLL plays the extra itself: each
package's noswap_character.json carries everything it needs of that extra (its palette, base and roll flags, and under
"s3k" its Blue Spheres colours, where its ability animations start and every ability number: gen_s3k_header.s3k_json),
and the package ships its S3&K files under the fixed names the DLL loads (extras.S3K_FIXED: 3K_Players/Extra.bin...),
copied from where build_s3k_art.py / build_s3k_hud.py write them (extras.s3k_build). NoSwap ships placeholders under
those names (build_s3k_art.write_placeholders) and no longer ships any extra's own copies. The save screen shows several
extras at once, so each package ships its picture under one name (extras.S3K_MENU_PICTURE: 3K_Players/MenuPicture.bin,
naming MenuPicture.gif), and NoSwap ships numbered placeholders (3K_Players/MenuPicture<j>.bin / .gif,
build_s3k_art.write_menu_placeholders) the DLL gives each extra's picture for the session.

For Sonic 1, Sonic 2 and Sonic CD (docs/plan-b-modular-characters.md step 4), each package's main player animation
under fixed names: Animations/NoSwapExtra.ani naming Sprites/Players/NoSwapExtra_1..k.gif (extras.PLAYER_ANI,
extras.player_sheet), from sheet2ani's numbered Extra<n>.ani / Extra<n>_<k>.gif kept with its art (extras.player_build).
NoSwap ships placeholders under those names (the game's Sonic.ani, extras.PLAYER_SHEETS blank sheets) and no extra's
numbered files (build_player_art). check_counterparts then checks that every package file has a NoSwap file of the same
name (the DLL serves nothing else) and that nothing shipped names an extra's numbered player files.

Run after build_sonic1.py / build_sonic2.py / build_soniccd.py (they build everything else, with every extra's moves).
Checks that every player script declares whatever the shared scripts use of it (a Monitor reading NoSwap_flags would
otherwise fail to compile; in CD, a shared script calling a function the player script defines).
"""
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import extras  # noqa: E402
from extras import EXTRAS, S3K_FIXED, S3K_MENU_PICTURE, s3k_build  # noqa: E402
import ani_v5  # noqa: E402
import origins_cards  # noqa: E402
import generic_extra  # noqa: E402

GAMES = [("Sonic1u", "build_sonic1.py"), ("Sonic2u", "build_sonic2.py")]
PACKAGES = REPO / "mods" / "NoSwap" / "characters"
PLAYER = "Players/PlayerObject.txt"
DECL = re.compile(r"^(?:public|private) (?:value|alias \S+ :|function|table) ?(\w+)", re.M)


def build_player(game, script, keep, out_dir):
    env = dict(os.environ, NOSWAP_KEEP=keep, NOSWAP_SCRIPTS_OUT=str(out_dir))
    result = subprocess.run([sys.executable, str(REPO / "tools" / script)], cwd=REPO, env=env,
                            capture_output=True, text=True)
    if result.returncode:
        sys.exit(f"{game} player script (keep {keep}) failed:\n{result.stdout}{result.stderr}")
    make_kind_free(game, out_dir / PLAYER, PLAYER, 0 if keep == "none" else int(keep))


GENERIC_STATS = {}


def make_kind_free(game, path, rel, row):
    """Rewrite a freshly built script so it works under any kind number (tools/generic_extra.py, phase A): a package's
    with its build ID as its row, NoSwap's own (row 0) so that an extra without a package plays as Sonic. Only ever on a
    file its builder has just written (a second pass would treat the first one's `>= 7` tests as Sonic's)."""
    text = path.read_bytes().decode("utf-8")
    try:
        out, stats = generic_extra.generalise(text, row, game, external_refs(game, rel), str(path.relative_to(REPO)),
                                              "row" if row else None)
    except generic_extra.GenericError as e:
        sys.exit(f"kind-free rewrite: {e}")
    path.write_bytes(out.encode("utf-8"))
    for k, v in stats.items():
        GENERIC_STATS[k] = GENERIC_STATS.get(k, 0) + v
    GENERIC_STATS["scripts"] = GENERIC_STATS.get("scripts", 0) + 1


# Origins' "retry the special stage" reloads the stage with stage.playerListPos as Sonic: Origins only knows the vanilla
# kinds (SpecialFinish stands an extra in as Sonic, PLAYER_SONIC_A = 0, for its NOTIFY_SPECIAL_RETRY, and nothing on the
# retry puts it back). A package's S1/S2 special stage player script is served only while its extra is active, so at the
# start of its ObjectStartup (before anything else in the stage reads the kind; S2's SpecialSetup runs first but treats
# Sonic and an extra alike) it puts back the active extra's kind: the DLL writes it in for ACTIVE_KIND_TOKEN when it
# serves the file. Only for 0, the stand-in: a level select started from an extra's card can switch to another vanilla
# character while the extra's package stays active, and Tails, Knuckles, Amy or Sonic & Tails stay themselves.
RETRY_KIND = ("\tif stage.playerListPos == 0 // [NoSwap] Origins' special stage retry reloads an extra as Sonic: this extra"
              " again (the DLL writes its kind in)\r\n"
              f"\t\tstage.playerListPos = {extras.ACTIVE_KIND_TOKEN}\r\n"
              "\tend if\r\n")
# Sonic CD's special stage (v3: its StageFinish sets Stage.PlayerListPos = 0 before the retry callback, the same way)
RETRY_KIND_CD = ("\tif Stage.PlayerListPos == 0 // [NoSwap] Origins' special stage retry reloads an extra as Sonic: this"
                 " extra again (the DLL writes its kind in)\r\n"
                 f"\t\tStage.PlayerListPos = {extras.ACTIVE_KIND_TOKEN}\r\n"
                 "\tend if\r\n")
# each package file that gets the retry lines: (the event they start, the lines)
ACTIVE_KIND_LINES = {"Sonic1u/Data/Scripts/Special/PlayerObject.txt": ("event ObjectStartup\r\n", RETRY_KIND),
                     "Sonic2u/Data/Scripts/Special/PlayerObject.txt": ("event ObjectStartup\r\n", RETRY_KIND),
                     "SonicCDu/Data/Scripts/Special/Sonic.txt": ("sub ObjectStartup\r\n", RETRY_KIND_CD)}
ACTIVE_KIND_FILES = list(ACTIVE_KIND_LINES)


def add_retry_kind(path, rel):
    """The retry lines (ACTIVE_KIND_LINES[rel]) at the start of a package's special stage script's ObjectStartup
    (after make_kind_free)."""
    head, lines = ACTIVE_KIND_LINES[rel]
    text = path.read_bytes().decode("utf-8")
    if text.count(head) != 1 or extras.ACTIVE_KIND_TOKEN.lower() in text.lower():
        sys.exit(f"{path.relative_to(REPO)}: expected one {head.strip()!r} and no {extras.ACTIVE_KIND_TOKEN}")
    path.write_bytes(text.replace(head, head + lines).encode("utf-8"))


def check_active_kind():
    """ACTIVE_KIND_TOKEN is only where it's meant to be (each package's ACTIVE_KIND_FILES, once, as RETRY_KIND wrote it;
    never in NoSwap's own files, which the DLL serves untouched), and nothing else any script, NoSwap's, a package's or
    the game's, or a GameConfig global, is named the same ignoring case (the engine's names ignore case)."""
    token = extras.ACTIVE_KIND_TOKEN
    word = re.compile(r"[A-Za-z_]\w*")
    mods = REPO / "mods" / "NoSwap"
    found = {}
    for f in mods.rglob("*"):
        if f.is_file() and f.suffix.lower() in (".txt", ".json", ".ini", ".md"):
            n = f.read_bytes().decode("utf-8", errors="ignore").lower().count(token.lower())
            if n:
                found[f.relative_to(mods).as_posix()] = n
    expected = {f"characters/{e['art'].name}/{rel}": 1 for e in EXTRAS for rel in ACTIVE_KIND_FILES}
    if found != expected:
        wrong = sorted(set(found.items()) ^ set(expected.items()))
        sys.exit(f"{token} is not exactly where it should be: {wrong[:10]}")
    for rel in expected:
        if ACTIVE_KIND_LINES[rel.split("/", 2)[2]][1] not in (mods / rel).read_bytes().decode("utf-8"):
            sys.exit(f"{rel}: {token} isn't in the retry lines")
    names = set()
    for base in [mods / g / "Data" / "Scripts" for g in extras.PLAYER_GAMES] + \
            [generic_extra.GAME_EXEC / g / "Scripts" for g in extras.PLAYER_GAMES] + [PACKAGES]:
        for f in base.rglob("*.txt"):
            for l in f.read_text(errors="ignore").split("\n"):
                names |= set(word.findall(l.split("//")[0]))
    for g in extras.PLAYER_GAMES:
        names |= set(generic_extra.gameconfig_globals(g))
    clash = sorted(n for n in names if n.lower() == token.lower() and n != token)
    if clash:
        sys.exit(f"{token}: other names match it ignoring case: {clash}")
    print(f"{token}: in {len(found)} package scripts (each package's {' and '.join(ACTIVE_KIND_FILES)}), never in "
          f"NoSwap's own; no other of {len(names)} script and GameConfig names matches it")


_EXTERNAL = {}


def external_refs(game, rel):
    if (game, rel) not in _EXTERNAL:
        _EXTERNAL[(game, rel)] = generic_extra.external_refs(game, rel)
    return _EXTERNAL[(game, rel)]


def check_kind_free():
    """No script NoSwap or a package ships tests a particular kind of 7 or up (case labels and kind comparisons use the
    vanilla kinds, or `>= 7` / `< 7`): the DLL numbers characters at runtime (docs/plan-b-modular-characters.md)."""
    files = [f for game in ("Sonic1u", "Sonic2u", "SonicCDu")
             for f in (REPO / "mods" / "NoSwap" / game / "Data" / "Scripts").rglob("*.txt")]
    files += list(PACKAGES.glob("*/*/Data/Scripts/**/*.txt"))
    for f in files:
        game = next(g for g in ("Sonic1u", "Sonic2u", "SonicCDu") if g in f.parts)
        text = f.read_bytes().decode("utf-8", errors="ignore").replace("\r\n", "\n")
        consts = generic_extra.Consts(generic_extra.script_aliases(text.split("\n")),
                                      generic_extra.gameconfig_globals(game))
        shared = REPO / "mods" / "NoSwap" / game / "Data" / "Scripts" / PLAYER
        if game != "SonicCDu":
            for k, v in generic_extra.script_aliases([l for l in shared.read_text(errors="ignore").split("\n")
                                                      if l.strip().lower().startswith("public alias")]).items():
                consts.aliases.setdefault(k, v)
        try:
            generic_extra.check(text, str(f.relative_to(REPO)), consts)
        except generic_extra.GenericError as e:
            sys.exit(f"kind test left: {e}")
    print(f"all {len(files)} S1/S2/CD scripts (NoSwap's and the packages') are kind-free: made so "
          f"{GENERIC_STATS.get('scripts', 0)} of them ({GENERIC_STATS})")


def declared(text):
    names = set(DECL.findall(text))
    names |= set(re.findall(r"^public alias \S+ : (\w+)", text, re.M))
    names |= set(re.findall(r"^(?:public|private) value (\w+)", text, re.M))
    return names


def v3_code(text):
    return "\n".join(l.split("//")[0] for l in text.replace("\r\n", "\n").split("\n"))


def v3_functions(text):
    return set(re.findall(r"^function (\w+)", text, re.M))


def build_cd():
    """Sonic CD's player scripts. v3 has no public values or aliases (aliases are per file): what other scripts use of
    the player script is its functions (a stage compiles every script's functions into one list, the player script
    first), so every variant must define every player function any other script names."""
    game, script = "SonicCDu", "build_soniccd.py"
    builder = importlib.import_module(script[:-len(".py")])
    scripts = REPO / "mods" / "NoSwap" / game / "Data" / "Scripts"
    for e in EXTRAS:  # its copies of the scripts that draw it from its own sheets, and its sheets (build_soniccd.py)
        builder.package_files(e, PACKAGES / e["art"].name / game)
        for rel in builder.PACKAGE_SCRIPTS:
            make_kind_free(game, PACKAGES / e["art"].name / game / "Data" / "Scripts" / rel, rel, e["id"])
            if f"{game}/Data/Scripts/{rel}" in ACTIVE_KIND_LINES:
                add_retry_kind(PACKAGES / e["art"].name / game / "Data" / "Scripts" / rel, f"{game}/Data/Scripts/{rel}")
    print(f"{game}: {len(EXTRAS)} packages' scripts ({', '.join(builder.PACKAGE_SCRIPTS)}) and sheets "
          f"({', '.join(builder.EXTRA_SHEETS.values())}, {builder.SPECIAL_BALL})")
    full = v3_functions((scripts / PLAYER).read_text(errors="ignore"))
    others = {p.relative_to(builder.BASE).as_posix(): p for p in builder.BASE.rglob("*.txt")}  # the game's...
    others.update({p.relative_to(scripts).as_posix(): p for p in scripts.rglob("*.txt")})  # ...or NoSwap's
    others.pop(PLAYER)
    others.update({f"{pkg.name}:{p.relative_to(pkg / game / 'Data' / 'Scripts').as_posix()}": p  # packages' copies
                   for pkg in PACKAGES.iterdir() for p in (pkg / game / "Data" / "Scripts").rglob("*.txt")
                   if p.relative_to(pkg / game / "Data" / "Scripts").as_posix() != PLAYER})
    needed = {}
    for rel, p in others.items():
        text = v3_code(p.read_text(errors="ignore"))
        for f in full - v3_functions(text):
            if re.search(rf"\b{f}\b", text):
                needed.setdefault(f, set()).add(rel)
    build_player(game, script, "none", scripts)
    variants = {"NoSwap's own": scripts / PLAYER}
    for e in EXTRAS:
        out = PACKAGES / e["art"].name / game / "Data" / "Scripts"
        build_player(game, script, str(e["id"]), out)
        variants[e["art"].name] = out / PLAYER
    for who, path in variants.items():
        missing = set(needed) - v3_functions(path.read_text(errors="ignore"))
        if missing:
            sys.exit(f"{game}: {who}'s player script lacks {sorted(missing)}, which "
                     f"{sorted(set().union(*(needed[m] for m in missing)))[:5]} use")
    ours = sorted(f for f in needed if f.startswith("NoSwap"))
    print(f"{game}: NoSwap's player script without moves, {len(EXTRAS)} packages' own (shared names checked: "
          f"{len(needed)} player functions other scripts use, NoSwap's: {ours})")


S3K = REPO / "mods" / "NoSwap" / "Sonic3ku" / "Data" / "Sprites"
S3K_GAME = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"


def build_s3k():
    """Sonic 3 & Knuckles: NoSwap's placeholders under the fixed names, and each package's own files under them."""
    import build_s3k_art
    build_s3k_art.write_placeholders(S3K)
    build_s3k_art.write_menu_placeholders(S3K)
    game_sheets = {p.relative_to(S3K_GAME).as_posix().lower() for p in S3K_GAME.rglob("*.gif")}  # (names ignore case)
    for e in EXTRAS:
        own, out = s3k_build(e), PACKAGES / e["art"].name / "Sonic3ku" / "Data" / "Sprites"
        missing = [rel for rel in S3K_FIXED + S3K_MENU_PICTURE if not (own / rel).exists()]
        if missing:
            sys.exit(f"{e['art'].name}: no {missing[0]} in {own}: run tools/build_art.py {e['art'].name} (its S3&K "
                     "player, Blue Spheres and save screen files) and tools/build_s3k_hud.py (HUD and signpost)")
        for rel in S3K_FIXED:
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            (out / rel).write_bytes((own / rel).read_bytes())
            if rel.endswith(".bin"):  # every sheet it names must be the game's or one of the fixed names
                for sheet in ani_v5.read_bin(out / rel)["sheets"]:
                    if sheet not in S3K_FIXED and sheet.lower() not in game_sheets:
                        sys.exit(f"{e['art'].name}: its {rel} names {sheet}, neither a fixed name nor the game's")
        for rel in S3K_MENU_PICTURE:  # the save screen picture: the DLL renames exactly this sheet name
            (out / rel).write_bytes((own / rel).read_bytes())
        if ani_v5.read_bin(out / S3K_MENU_PICTURE[0])["sheets"] != [S3K_MENU_PICTURE[1]]:
            sys.exit(f"{e['art'].name}: its {S3K_MENU_PICTURE[0]} must name {S3K_MENU_PICTURE[1]} alone")
        # NoSwap's old per-extra copies (before the packages), should any be left
        f = e["file"]
        for old in (f"3K_Players/Menu{f}.bin", f"3K_Players/Menu{f}.gif",  # (the save screen picture's)
                    f"3K_Players/{f}.bin", f"3K_Players/{f}.gif", f"3K_Special/{f}.bin", f"3K_Special/NoSwap_{f}.gif",
                    f"3K_Global/HUD_{f}.bin", f"3K_Global/HUD_{f}.gif", f"3K_Global/SignPost_{f}.bin",
                    f"3K_Global/SignPost_{f}.gif"):
            (S3K / old).unlink(missing_ok=True)
    print(f"Sonic3ku: NoSwap's placeholders and {len(EXTRAS)} packages' own files ({', '.join(S3K_FIXED + S3K_MENU_PICTURE)})")
    # Ice Cap 1's snowboard intro: the extra's own poses on the official board (build_s3k_snowboard.py), only in the
    # packages of Sonic-based extras (the DLL swaps 3K_ICZ/Snowboard.bin for them alone); NoSwap's placeholder
    import build_s3k_snowboard
    build_s3k_snowboard.write_placeholder(S3K)
    boards = build_s3k_snowboard.sonic_based()
    for e in boards:
        build_s3k_snowboard.build(e, PACKAGES / e["art"].name / "Sonic3ku" / "Data" / "Sprites")
    print(f"Sonic3ku: {len(boards)} packages' snowboard ({build_s3k_snowboard.FIXED_BIN})")
    # The shot (abilities.py "shot": a real projectile, the DLL's): its art under 3K_Players/Shot.bin / .gif, only in
    # the packages of extras that have one; NoSwap's placeholder under those names (build_s3k_shot.py)
    import abilities
    import build_s3k_shot
    build_s3k_shot.write_placeholder(S3K)
    shots = []
    for e in EXTRAS:
        out = PACKAGES / e["art"].name / "Sonic3ku" / "Data" / "Sprites"
        shot = abilities.shot(e["id"], "s3k")
        if shot:
            n = build_s3k_shot.build(e, shot, out, abilities.shot2(e["id"], "s3k"),  # (a second shot: animation 1)
                                     swaps=abilities.swap_shots(e["id"], "s3k"))  # (swap shots: one animation each)
            shots.append(f"{e['art'].name} ({n} frames)")
        else:
            for rel in build_s3k_shot.SHOT:
                (out / rel).unlink(missing_ok=True)
    print(f"Sonic3ku: shots {', '.join(shots) or 'none'} ({', '.join(build_s3k_shot.SHOT)})")
    # its own sounds (character.json "sounds", tools/own_sounds.py): Sonic3ku/Data/SoundFX/NoSwap/<id>/<name>.wav, only
    # in the packages of characters that have some; the DLL reads and plays them itself (no NoSwap counterpart)
    import own_sounds
    sounds = []
    for e in EXTRAS:
        names = own_sounds.write_s3k(e, PACKAGES / e["art"].name)
        if names:
            sounds.append(f"{e['art'].name} ({len(names)})")
    print(f"Sonic3ku: own sounds {', '.join(sounds) or 'none'}")


def character_json(e):
    """Its noswap_character.json: the key the DLL finds it by, and what the S3&K DLL needs of it (the DLL's ExtraData.h
    reads it: the palette's slots and "#RRGGBB" colours, base "sonic" / "tails" / "knuckles", and under "s3k" the
    ability numbers by the DLL's field names, gen_s3k_header.py)."""
    from gen_s3k_header import palette_json, s3k_json
    own = __import__("own_sounds").classic_paths(e)
    out = {
        "key": e["key"], "name": e["name"], "base": e["base"],
        # its row in its own scripts' tables (tools/generic_extra.py): the ID it was built as, NOT its kind (the DLL
        # gives every character its kind at runtime, from its key: roster.json)
        "build_id": e["id"],
        "palette": palette_json(e["palette"]),  # its own colours: palette slot -> colour (S3&K: bank 0)
        "roll": e["roll"],  # its own rolling curl, shown instead of the jump while rolling
        "no_roll": e["no_roll"],  # never rolls or Spin Dashes
        "s3k": s3k_json(e),
        # its sprite credit under the cards in Origins' select (extras.CREDIT_SHORT; "": none, the box stays empty)
        "credit_short": e.get("credit_short", ""),
        # S3&K act results: its name's and the streaks' three shades, light to dark (tools/ui_accent.py; the DLL's
        # namespace accent); null: Sonic's blue
        "ui_accent": __import__("ui_accent").accent(e),
        "note": "Built by tools/build_packages.py: this character's own files, served by the NoSwap DLL while it "
                "plays, and its data for the DLL."}
    if own:  # its own sounds Sonic 1/2/CD ask the DLL for by number, in this order (tools/own_sounds.py; none: no key)
        out["own_sounds"] = own
    return out


GAME_DATA = {"Sonic1u": "Sonic1", "Sonic2u": "Sonic2", "SonicCDu": "SonicCD"}  # extracted/<game>/Data


def build_player_art():
    """Sonic 1, Sonic 2 and Sonic CD: each package's main player animation under the fixed names (extras.PLAYER_ANI
    naming extras.player_sheet(1..k)), from where sheet2ani's numbered copies are kept (extras.player_build), and
    NoSwap's placeholders under those names: the game's own Sonic.ani (never loaded by NoSwap's own scripts, where an
    extra plays as Sonic) and extras.PLAYER_SHEETS blank sheets. NoSwap ships no extra's numbered Extra<n>.ani /
    Extra<n>_<k>.gif any more (docs/plan-b-modular-characters.md step 4)."""
    import shutil
    import sheet2ani
    from PIL import Image
    from gifio import save_sheet
    blank = Image.new("P", (16, 16), 0)
    blank.putpalette([0] * 768)
    most = {}
    for game in extras.PLAYER_GAMES:
        data = REPO / "mods" / "NoSwap" / game / "Data"
        for e in EXTRAS:  # (sheet2ani writes them here; build_art.py and the game builds move them out)
            if (data / "Animations" / f"{e['file']}.ani").exists() or extras.numbered_sheets(data / "Sprites" / "Players", e):
                sys.exit(f"{game}: {e['file']}.ani or its sheets are still in NoSwap's folder: run tools/build_art.py "
                         f"{e['art'].name} (or the {game} build), which keeps them with its art")
        shutil.copyfile(REPO / "extracted" / GAME_DATA[game] / "Data" / "Animations" / "Sonic.ani",
                        data / "Animations" / extras.PLAYER_ANI)
        for k in range(1, extras.PLAYER_SHEETS + 1):
            save_sheet(blank, data / "Sprites" / extras.player_sheet(k))
        for e in EXTRAS:
            own, pkg = extras.player_ani_path(e, game), PACKAGES / e["art"].name / game / "Data"
            raw = own.read_bytes()
            ani = extras.player_ani(e, game)
            names = ani["sheets"]
            if len(names) > extras.PLAYER_SHEETS:
                sys.exit(f"{e['art'].name}: its {game} {own.name} names {len(names)} sheets; NoSwap ships "
                         f"{extras.PLAYER_SHEETS} (extras.PLAYER_SHEETS)")
            (pkg / "Animations").mkdir(parents=True, exist_ok=True)
            (pkg / "Sprites" / "Players").mkdir(parents=True, exist_ok=True)
            sheet2ani.write_ani(pkg / "Animations" / extras.PLAYER_ANI, dict(ani, sheets=names))
            if (pkg / "Animations" / extras.PLAYER_ANI).read_bytes() != raw:  # (read_ani / write_ani round trip)
                sys.exit(f"{own}: doesn't read back byte for byte")
            sheet2ani.write_ani(pkg / "Animations" / extras.PLAYER_ANI, extras.player_ani(e, game, fixed=True))
            for k in range(1, extras.PLAYER_SHEETS + 1):
                (pkg / "Sprites" / extras.player_sheet(k)).unlink(missing_ok=True)
            for k, sheet in enumerate(names, 1):
                shutil.copyfile(extras.player_build(e, game) / "Sprites" / sheet, pkg / "Sprites" / extras.player_sheet(k))
            most[game] = max(most.get(game, 0), len(names))
    print(f"player art: {len(EXTRAS)} packages' {extras.PLAYER_ANI} and sheets (most per game: {most}; NoSwap's "
          f"placeholders: the game's Sonic.ani and {extras.PLAYER_SHEETS} blank sheets)")


def build_cards():
    """Origins' character select: each package's card picture (origins_cards.PICTURE, docs/plan-b-modular-characters.md
    phase B): its Sonic 1 "Stopped" frame 0 enlarged 8x, as a BC7 DDS the DLL writes into a card slot of its copy of the
    menu archives at startup. Its card name is its noswap_character.json "name" (two lines, split at the first space).
    NoSwap ships no file of that name: the DLL reads it from the package, it never serves it."""
    from build_origins_menu import card_picture, head_picture
    for e in EXTRAS:
        out = PACKAGES / e["art"].name / origins_cards.PICTURE
        out.parent.mkdir(parents=True, exist_ok=True)
        data = card_picture(e)
        origins_cards.read_card(data)  # (the DLL's checks)
        out.write_bytes(data)
        # its main menu CONTINUE bubble head: its life icon, enlarged origins_cards.HEAD_SCALE times
        data = head_picture(e)
        origins_cards.read_head(data)
        (PACKAGES / e["art"].name / origins_cards.HEAD_PICTURE).write_bytes(data)
    print(f"cards: {len(EXTRAS)} packages' {origins_cards.PICTURE} ({origins_cards.CELL_W} px wide, at most "
          f"{origins_cards.CELL_H} high) and {origins_cards.HEAD_PICTURE} (life icon x{origins_cards.HEAD_SCALE})")


NUMBERED = re.compile(rb"Extra\d+(?:SS)?(?:\.ani|_\d+\.gif)", re.I)
OWN_SOUNDS = "Sonic3ku/Data/SoundFX/NoSwap/"  # (a package's own sounds: the DLL reads them itself, tools/own_sounds.py)


def check_counterparts():
    """The DLL serves a package's file only for a name NoSwap ships (its CreateFileW hook redirects opens of NoSwap's
    files): every file a package has (but its noswap_character.json, S3&K save screen picture and card picture) needs a NoSwap file at the same path. And nothing
    NoSwap or a package ships names an extra's numbered player files (Extra<n>.ani, Extra<n>_<k>.gif): a new package
    has no such file in NoSwap to be served under."""
    root = REPO / "mods" / "NoSwap"
    ours = {p.relative_to(root).as_posix().lower() for p in root.rglob("*") if p.is_file()
            and p.relative_to(root).parts[0] != "characters"}
    # (its S3&K save screen picture is served under the numbered names the DLL gives it: extras.S3K_MENU_PICTURE)
    # (and its Origins card picture, which the DLL writes into its copy of the menu archives: origins_cards.PICTURE)
    special = {"noswap_character.json", origins_cards.PICTURE, origins_cards.HEAD_PICTURE} | {f"Sonic3ku/Data/Sprites/{rel}" for rel in S3K_MENU_PICTURE}
    count = 0
    for pkg in PACKAGES.iterdir():
        for p in pkg.rglob("*"):
            rel = p.relative_to(pkg).as_posix()
            if not p.is_file() or rel in special or rel.startswith(OWN_SOUNDS):
                continue
            if rel.lower() not in ours:
                sys.exit(f"{pkg.name}: {rel} has no NoSwap file of that name: the DLL would never serve it")
            count += 1
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".txt", ".ani", ".bin") and "cache" not in p.relative_to(root).parts:
            hit = NUMBERED.search(p.read_bytes())
            if hit:
                sys.exit(f"{p.relative_to(REPO)} names {hit.group().decode()}: an extra's numbered file (fixed names only)")
        elif p.is_file() and NUMBERED.fullmatch(p.name.encode()) and "characters" not in p.relative_to(root).parts:
            sys.exit(f"{p.relative_to(REPO)}: NoSwap ships no extra's numbered player files any more")
    print(f"counterparts: all {count} package files have a NoSwap file of the same name; nothing names an extra's "
          "numbered player files")


def main():
    extras.stash_all_player_art()  # (should any be left in the mod's folders)
    for e in EXTRAS:
        pkg = PACKAGES / e["art"].name
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "noswap_character.json").write_text(json.dumps(character_json(e), indent=2) + "\n")
    for game, script in GAMES:
        scripts = REPO / "mods" / "NoSwap" / game / "Data" / "Scripts"
        full = (scripts / PLAYER).read_text(errors="ignore")
        shared = "".join(p.read_text(errors="ignore") for p in scripts.rglob("*.txt")
                         if p.relative_to(scripts).as_posix() not in (PLAYER, "Special/PlayerObject.txt"))
        # what the shared scripts use of the player script's own names
        needed = {n for n in declared(full) if n.startswith(("NoSwap", "ANI_NOSWAP")) and re.search(rf"\b{n}\b", shared)}
        # and the player script functions they call (NoSwap_WaterColours), which must be public in every player script
        called = set(re.findall(r"CallFunction\((NoSwap\w+)\)", shared))
        called -= set(re.findall(r"^public function (\w+)", shared, re.M))  # (a shared script's own: TailsObject.txt's
        # NoSwap_ShotSeek, tools/shots_v4.py)
        build_player(game, script, "none", scripts)
        variants = {"NoSwap's own": scripts / PLAYER}
        for e in EXTRAS:
            out = PACKAGES / e["art"].name / game / "Data" / "Scripts"
            build_player(game, script, str(e["id"]), out)
            variants[e["art"].name] = out / PLAYER
        for who, path in variants.items():
            text = path.read_text(errors="ignore")
            missing = (needed - declared(text)) | (called - set(re.findall(r"^public function (\w+)", text, re.M)))
            if missing:
                sys.exit(f"{game}: {who}'s player script lacks {sorted(missing)}, which the shared scripts use")
        print(f"{game}: NoSwap's player script without moves, {len(EXTRAS)} packages' own (shared names checked: "
              f"{sorted(needed | called)})")
        builder = importlib.import_module(script[:-len(".py")])
        for e in EXTRAS:
            builder.package_sprites(e, PACKAGES / e["art"].name / game / "Data" / "Sprites")
        print(f"{game}: {len(EXTRAS)} packages' UI sheets ({', '.join(builder.copy_name(s) for s in builder.UI_SHEETS)})")
        special = "Special/PlayerObject.txt"
        for e in EXTRAS:
            builder.package_special(e, PACKAGES / e["art"].name / game)
            make_kind_free(game, PACKAGES / e["art"].name / game / "Data" / "Scripts" / special, special, e["id"])
            add_retry_kind(PACKAGES / e["art"].name / game / "Data" / "Scripts" / special, f"{game}/Data/Scripts/{special}")
        # NoSwap's own, rebuilt here from the game's so it's made kind-free exactly once (row 0: an extra plays as Sonic)
        builder.build_scripts({special: builder.BUILDERS[special]}, builder.BASE, scripts)
        make_kind_free(game, scripts / special, special, 0)
        print(f"{game}: {len(EXTRAS)} packages' special stage player scripts and art")
    build_player_art()
    build_v4_shots()
    build_cd_shots()
    __import__("pot_magic").build_art(EXTRAS, PACKAGES)  # (Gilius' Earthquake art in his S1/S2 strip: tools/pot_magic.py)
    build_cards()
    check_sheet_rows()
    build_cd()
    check_kind_free()
    check_active_kind()
    build_s3k()
    check_counterparts()


def build_v4_shots():
    """Sonic 1 / Sonic 2 shots (abilities.py "shot", tools/shots_v4.py): each package with a shot gets the shot's frames
    (the S3&K recipe's, build_s3k_shot.flame_frames) in the reserved strip of its own first player sheet (shots_v4.SHEET,
    after build_player_art, which writes it afresh): no new sheet. NoSwap's old separate sheet (Players/NoSwapShot.gif)
    is no longer shipped."""
    import abilities
    import build_s3k_shot
    import shots_v4
    made = []
    for game, _ in GAMES:
        old = "Players/NoSwapShot.gif"  # (the separate sheet before 2026-09-27: drew nothing in Sonic 1)
        (REPO / "mods" / "NoSwap" / game / "Data" / "Sprites" / old).unlink(missing_ok=True)
        for e in EXTRAS:
            (PACKAGES / e["art"].name / game / "Data" / "Sprites" / old).unlink(missing_ok=True)
            s = abilities.shot(e["id"], "v4")
            if not s:
                continue
            sheet = PACKAGES / e["art"].name / game / "Data" / "Sprites" / shots_v4.SHEET
            if abilities.swap_shots(e["id"], "v4"):  # (swap shots, John's sub-weapons: every entry's frames, in turn, in
                # the swap boxes: abilities.swap_layout; the colours his own slots, the nearest where not exact)
                from PIL import Image
                slots = {}
                for other in sorted(sheet.parent.glob("NoSwapExtra_*.gif")):
                    slots.update(build_s3k_shot.sheet_slots(Image.open(other)))
                frames = []
                for sw, _, burn, _ in abilities.swap_layout(e["id"]):
                    frames += build_s3k_shot.frames(sw["art"], e, slots)
                    if burn is not None:
                        frames += build_s3k_shot.frames(sw["burn"]["art"], e, slots)
                shots_v4.place_swap_art(frames, sheet)
                made.append(f"{game} {e['art'].name} (swap shots)")
                continue
            # (a spark's colours: the slots the package's own sheet uses, valid in that game; a flame's: its own slots)
            from PIL import Image
            # (at most the strip's boxes: a cycle shot takes its first frames here, abilities.shot_frame_count)
            s2 = abilities.shot2(e["id"], "v4")  # (a second shot: its frames in the strip's second row)
            slots = {}  # (the colours any of its player sheets uses: one palette, as CD's shots_v3.place_art; Mecha's
            # spike ball has a colour his first sheet doesn't use)
            for other in sorted(sheet.parent.glob("NoSwapExtra_*.gif")):
                slots.update(build_s3k_shot.sheet_slots(Image.open(other)))
            if s["art"].get("own_slots") or (s2 or {}).get("art", {}).get("own_slots"):
                slots.update(build_s3k_shot.own_palette(e))  # (the recipe's "own_slots": all its own colours)
            shots_v4.place_art(build_s3k_shot.frames(s["art"], e, slots)[:abilities.shot_frame_count(s, "v4")], sheet,
                               build_s3k_shot.frames(s2["art"], e, slots)[:abilities.shot_frame_count(s2, "v4")]
                               if s2 else None, held=bool(s.get("aim_frames")))
            made.append(f"{game} {e['art'].name}")
    print(f"Sonic1u/Sonic2u: shot frames in the reserved strip of {shots_v4.SHEET}: {', '.join(made) or 'no package'}")


def build_cd_shots():
    """Sonic CD shots (abilities.py "shot", tools/shots_v3.py): each package with one gets the shot's frames on a free
    spot of its own CD player sheet, as animation shots_v3.ANI_SHOT of its NoSwapExtra.ani (after build_player_art,
    which writes both afresh). No new file: NoSwap's TailsObject.txt draws the shot from the player's own animation."""
    import abilities
    import shots_v3
    made = []
    for e in EXTRAS:
        s = abilities.shot(e["id"], "cd")
        if s and abilities.swap_shots(e["id"], "cd"):  # (swap shots, John's sub-weapons: animations shots_v3.swap_anims)
            where = shots_v3.place_swap_art(e, abilities.swap_shots(e["id"], "cd"),
                                            PACKAGES / e["art"].name / "SonicCDu" / "Data")
            made.append(f"{e['art'].name} ({where})")
        elif s:
            where = shots_v3.place_art(e, s, PACKAGES / e["art"].name / "SonicCDu" / "Data",
                                       abilities.shot2(e["id"], "cd"))  # (a second shot: animation ANI_SHOT2)
            made.append(f"{e['art'].name} ({where})")
    print(f"SonicCDu: shot frames in the player art (animation {shots_v3.ANI_SHOT}): {', '.join(made) or 'no package'}")


def check_sheet_rows():
    """Every S1/S2 sheet NoSwap or a package ships fits what the engine (RSDKv4) draws: a frame reaching past a sheet's
    first 512 rows draws nothing (2026-09-26: the S1 ending poses at rows 513+ vanished). Widths: powers of two, <= 512."""
    from PIL import Image
    from noswap_common import SHEET_ROWS
    dirs = [REPO / "mods" / "NoSwap" / game / "Data" / "Sprites" for game, _ in GAMES]
    dirs += [PACKAGES / e["art"].name / game / "Data" / "Sprites" for e in EXTRAS for game, _ in GAMES]
    sheets = [p for d in dirs if d.exists() for p in d.rglob("*.gif")]
    for p in sheets:
        w, h = Image.open(p).size
        if h > SHEET_ROWS or w > 512 or w & (w - 1):
            sys.exit(f"{p.relative_to(REPO)} is {w}x{h}: S1/S2 draw only {SHEET_ROWS} rows (widths: powers of two, "
                     "at most 512)")
    print(f"Sonic1u/Sonic2u: {len(sheets)} shipped sheets, all at most {SHEET_ROWS} rows and 512 wide")


if __name__ == "__main__":
    main()
