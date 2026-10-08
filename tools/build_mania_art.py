#!/usr/bin/env python3
"""Build NoSwapMania's character packages (the Sonic Mania decompilation mod): one folder per Mania-enabled extra,

    mods/NoSwapMania/Data/Sprites/NoSwap/<folder>/
        noswap_character.json   who it is and its Mania data (mania_json below): the mod scans these at startup
        Player.bin / .gif       its player sprites, on Mania's Sonic.bin animation list (+ its ability animations)
        SaveSelect.bin, Save.gif  its save select pictures (portrait, its shadow, life and continue icons)
    mods/NoSwapMania/Data/Sprites/NoSwap/SaveSelectAtlas.bin / .gif: all their save select pictures on one sheet
        (build_save_atlas: the menu's sheets are limited; a package's own pair is the fallback for packages outside it)

Usage: build_mania_art.py [folder ...]      (default: every extra in MANIA_ENABLED)

Why under Data/Sprites: the decomp's mod loader serves a mod's files by their path inside the mod folder, and the game
only asks for sprites as "Data/Sprites/<name>"; so a package must live there for its .bin files to load (and their
sheets name themselves "NoSwap/<folder>/..."). A package is still one self-contained folder: drop it in, or leave it out.

Sprites: Mania's player files follow the same animation list as Origins' S3&K (built on Mania's engine), so this reuses
build_s3k_art.build() as it is, pointed at Mania's own template (Players/Sonic.bin: 54 animations, mapped BY NAME, with
its frame counts, timings, hitboxes and draw codes) instead of 3K_Players. Its fallbacks all apply; MANIA_FROM_S2 adds
the names only Mania has. Frames stay exact pixels (faithful art rule). The ability animations come after Mania's 54,
at 54 + build_s3k_art.ABILITY_SLOTS (slot 41 at 54, 42 at 55...), as in S3&K ("anim_base" in the JSON).

Colours: Mania draws sprites with the stage palette. Slots 1-63 are the game's global colours (GameConfig.bin bank 0; no
stage overrides rows 0-7 of bank 0); the extra's own colours go in OWN_SLOTS: Sonic's six (64-69) and the global rows'
unused (magenta) slots 86-90, 111 and 127, which no sprite of the game draws with. A colour the global palette already has
exactly needs no slot; the rest take OWN_SLOTS by how common they are on the sheet; any beyond (none so far) would go to
the nearest global colour, the approved colour exception (reported). The mod writes them at stage load, and their water /
other banks' versions (see "host_tint").

Shots: an extra with a projectile (abilities.py "shot" / "shot2", S3&K's numbers: abilities.shot(i, "s3k")) gets Shot.bin /
Shot.gif (build_shot: build_s3k_shot's recipes, the same frames and per-frame hitboxes, drawn in the Mania runtime palette
above: exact where the colour is there, the nearest otherwise, reported) and "shot" / "shot2" in its JSON (the numbers
without the art; S3&K sound files Mania lacks swapped by MANIA_SFX). The mod's shot object plays animation 0 (shot2: 1).

Abilities: the SAME field names and values as the S3&K DLL's (gen_s3k_header.ability_fields, from abilities.py), only
the ones not at their default; the mod reads the ones it has modules for and skips (logs) the rest.
"""
import json
import shutil
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import abilities as ab
import ani_v5
import build_s3k_art as s3k
import character_json
from extras import EXTRAS, ui_manifest
from mania_only import MANIA_ONLY, mania_only  # (Mania-only characters: never in extras.py, so never in Origins)
from gen_s3k_header import DEFAULT_OF, ability_fields
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
MANIA = Path(__import__("os").environ.get("NOSWAP_MANIA_DATA") or Path.home() / "Code" / "mania" / "extracted" / "Data")  # tools/rsdk5_extract.py output (Mania Plus Data.rsdk)
MOD = REPO / "mods" / "NoSwapMania"
PACKAGES = MOD / "Data" / "Sprites" / "NoSwap"  # (see the docstring: the mod scans its sub-folders)
PKG_SPRITES = "NoSwap"  # the same folder as the game names it (relative to Data/Sprites)

# The extras NoSwapMania builds, by art folder; the save select cycles them in tools/extras.py's order. Not Mighty or Ray
# (Mania has the real ones). Built on Sonic, Tails or Knuckles (extras.py "base": HOST_FILE).
MANIA_ENABLED = ["metal-sonic", "espio", "fang", "mario", "gamma", "bomb",
                 "shadow", "blaze", "vector", "mecha-sonic", "sally", "emerl", "big", "bark",
                 "omega", "marine", "mephiles", "silver",
                 # the Sonic-hosted batch (2026-10-01; their moves: native/mania/src/ManiaBatch.h)
                 "robotnik", "max", "tikal", "trip", "jet", "chaos", "tails-doll", "heavy", "honey",
                 # hosted on Tails (his flight) and Knuckles (his glide and climb), 2026-10-01: native/mania/src/ManiaHost.h
                 "cream", "charmy", "flicky", "rouge",
                 # the guest batch (2026-10-01: Sticks and the crossovers on Sonic; native/mania/src/ManiaGuest.h)
                 "sticks", "megaman", "ray-poward", "sparkster",
                 # the crossovers with moves of their own (2026-10-01; native/mania/src/ManiaCross.h)
                 "ristar", "headdy", "john-morris", "ecco"]
if __import__("os").environ.get("NOSWAP_KIT"):  # (the Creator Kit: only the creator's own characters, tools/extras.py)
    MANIA_ENABLED = []  # (only character.json ones, by their own "games": {"mania": true})
# ... plus every character defined by a character.json with "games": {"mania": true} (tools/character_json.py: Bean)
MANIA_ENABLED += [f for f in character_json.mania_folders() if f not in MANIA_ENABLED]
# ... and the Mania-only ones (tools/mania_only.py: Amy), built from their own official sprite files (tools/mania_v5_art.py)
MANIA_ALL = MANIA_ENABLED + ([] if __import__("os").environ.get("NOSWAP_KIT") else [e["art"].name for e in MANIA_ONLY])

# Per-extra settings where the generic rule isn't enough.
#   palette:   slot -> colour, exactly (instead of the generic allocation)
#   host_tint: own slots among 64-69 whose water / other-bank versions are the stage's own Sonic colours there (a ramp
#              that follows Sonic's, Metal's blues); the others get a tinted version of their own colour (the mod)
MANIA_OVERRIDES = {
    # Metal: his four blues and the two light greys in Sonic's slots, exactly (his dark grey #484848 goes to the nearest
    # global colour, #383040; his whites, reds, yellow and skin to the global ones)
    "metal-sonic": {
        "palette": {64: "#242490", 65: "#4848b4", 66: "#6c6cd8", 67: "#9090fc", 68: "#b4b4b4", 69: "#909090"},
        "host_tint": [64, 65, 66, 67],
    },
    # Rouge: her wing greys #909090 / #484848 go to Origins' shared grey slots 8 / 9 (rouge_s2.json "colours"), so the
    # generic allocation (her own slots only) left them out and they fell to the nearest global colours (#80a0b0,
    # #383040: 4768 + 2389 px). Her sheet's yellow #fcfc00 is on none of her frames, so all 13 colours fit, exactly
    # (the generic slots for the other 11, the greys in 111 and 127).
    "rouge": {
        "palette": {64: "#fcfcfc", 65: "#b4b4b4", 66: "#fc9048", 67: "#b44800", 68: "#900090", 69: "#fc00fc",
                    86: "#480048", 87: "#6c0000", 88: "#6cb4d8", 89: "#90d8fc", 90: "#246c90",
                    111: "#909090", 127: "#484848"},
    },
}
if __import__("os").environ.get("NOSWAP_KIT"):  # (the Creator Kit: NoSwap's own characters' settings, by folder)
    MANIA_OVERRIDES.clear()
PORTRAIT_SCALE = 3  # the save select portrait: the life icon, pixel-exact 3x

PLAYER_SLOT = 64  # Sonic's first own colour (Player.h PLAYER_PALETTE_INDEX_SONIC)
OWN_SLOTS = [64, 65, 66, 67, 68, 69, 86, 87, 88, 89, 90, 111, 127]
# Save select pictures: the extra's colours go in these slots of the menu palette, which no UISaveSlot sprite uses
# (UI/SaveSelectEN.gif, Zones.gif and every Text*.gif leave 142-160 and 190-197 empty), in this order (the mod's
# SAVE_SLOTS, the same list); the mod writes them only while it draws that slot, then puts the menu's own back.
SAVE_SLOTS = list(range(142, 161)) + list(range(190, 198))
SAVE_SHADOW = 213  # the silhouette colour of SaveSelect's "Player Shadows"
ANI_SONIC_COUNT = 54
# Hosting (extras.py "base"): the extra plays on that character's ID with its moves (Tails' flight, Knuckles' glide and
# climb), so its sprites follow that character's Mania file: Players/<file>.bin (Tails' and Knuckles' have 55 animations,
# their own from 48 on: Fly... / Glide...). Its colours stay in Sonic's slots and the rest of OWN_SLOTS (the mod writes
# them; the host's own slots 70-75 / 80-85 aren't used), so the palette side is the same for every host.
HOST_FILE = {"sonic": "Sonic", "tails": "Tails", "knuckles": "Knux"}


def host_template(e):
    """Mania's player file for the extra's host (its animation list)."""
    return ani_v5.read_bin(MANIA / "Sprites" / "Players" / f"{HOST_FILE[e['base']]}.bin")


def anim_base(e):
    """The extra's first ability animation: after its host file's own."""
    return len(host_template(e)["anims"])

# Animations only Mania's list has (build_s3k_art.FROM_S2 has the rest): -> the extra's Sonic 2 animation
MANIA_FROM_S2 = {
    "Air Walk": ["Walking"],  # running off a ledge / springs up (Mania's own mid-air walk)
    "Fly": ["Super Peel Out", "Running"],  # Sonic.bin's list 48 (ANI_PEELOUT): the Peel Out, the Dash with the medal
    "Hang": ["Bouncing"],
    "Turntable": ["Walking"],
    "Bungee": ["Bouncing"],
    "Outta Here": ["Waiting", "Stopped"],
    "Ledge Pullup": ["Ledge Pull Up"],  # Knux.bin's (S3&K's "Ledge Pull Up"): extras built on Knuckles
}


# Copy heads (abilities.py copy_heads: Emerl's head per Copycat move): build_s3k_art.COPY_HEADS_S3K names S3&K's list (with
# its "Angled" ones and Fall); Mania's has none of those, so the copies are made of these instead (Mania's Sonic.bin
# names: "Air Walk" is Mania's fall, "Fly" its Peel Out; "shot" the copy flash, ability slot 43). The mod finds the set
# from the JSON's "copy_heads" (offset, this list's length, how many sets) and shows the active move's copy in place of
# the game's, only while drawing (NoSwapMania.c CopyHeadDraw)
COPY_HEADS_MANIA = ["Idle", "Bored 1", "Walk", "Air Walk", "Jog", "Run", "Dash", "Fly", "shot"]


# S3&K sound files a shot names that Mania's Data.rsdk doesn't have -> Mania's own (the rest are the same files)
# (Stage/Explosion2.wav, the bosses' blast, isn't a global sound: the mod's Data/Game/Game.xml loads it for every stage)
MANIA_SFX = {"Global/HammerThrow.wav": "Global/InstaShield.wav", "Global/Explosion.wav": "Stage/Explosion2.wav"}
SHOT_FILE = "Shot.bin"  # (in the package folder; its sheet Shot.gif beside it)


def extra_of(folder):
    e = next((e for e in EXTRAS if e["art"].name == folder), None) or mania_only(folder)
    if not e:
        sys.exit(f"{folder}: no such extra in tools/extras.py")
    return e


def global_palette():
    """Bank 0 of Mania's global palette (GameConfig.bin, RSDK::LoadGameConfig): slot -> RGB."""
    d = (MANIA / "Game" / "GameConfig.bin").read_bytes()
    p = 4

    def skip_string():
        nonlocal p
        p += 1 + d[p]
    for _ in range(3):  # title, subtitle, version
        skip_string()
    p += 1 + 2  # active category, starting scene
    count = d[p]
    p += 1
    for _ in range(count):
        skip_string()
    colours = {}
    for bank in range(8):
        mask = struct.unpack_from("<H", d, p)[0]
        p += 2
        for r in range(16):
            if mask >> r & 1:
                for c in range(16):
                    if bank == 0:
                        colours[r * 16 + c] = tuple(d[p + c * 3:p + c * 3 + 3])
                p += 48
    return colours


def hexrgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def s2_config(e):
    return next(e["art"].glob("*_s2.json"))


def mania_palette(e):
    """{slot: "#rrggbb"}: the extra's own colours in OWN_SLOTS (see the module docstring)."""
    over = MANIA_OVERRIDES.get(e["art"].name, {})
    if "palette" in over:
        return {int(s): c.lower() for s, c in over["palette"].items()}
    glob = {c for i, c in global_palette().items() if 0 < i < PLAYER_SLOT}
    own = [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in e["palette"].values()]
    need = [c for c in own if c not in glob]
    cfg_path = s2_config(e)
    sheet = Image.open(cfg_path.parent / json.loads(cfg_path.read_text())["source"]).convert("RGB")
    count = {c: n for n, c in sheet.getcolors(1 << 24)}
    need.sort(key=lambda c: -count.get(c, 0))
    if len(need) > len(OWN_SLOTS):
        print(f"  {e['art'].name}: {len(need) - len(OWN_SLOTS)} rarest colour(s) go to the nearest global colour: "
              + ", ".join("#%02x%02x%02x" % c for c in need[len(OWN_SLOTS):]))
    return {s: "#%02x%02x%02x" % c for s, c in zip(OWN_SLOTS, need)}


def template_sheet(path, own):
    """A stand-in for 3K_Players/Sonic.gif: the runtime palette (the global colours 1-63, the extra's own in its slots),
    with one pixel of each slot a sprite may use, so build_s3k_art matches colours against exactly those."""
    glob = global_palette()
    pal = [0] * 768
    slots = []
    for i in range(1, PLAYER_SLOT):
        c = glob.get(i)
        if c is None or c == (255, 0, 255):  # (0 and magenta: transparent / unused)
            continue
        pal[3 * i:3 * i + 3] = c
        slots.append(i)
    for s, c in own.items():
        pal[3 * s:3 * s + 3] = hexrgb(c)
        slots.append(s)
    img = Image.new("P", (len(slots), 1), 0)
    img.putpalette(pal)
    for x, s in enumerate(slots):
        img.putpixel((x, 0), s)
    save_sheet(img, path)  # (optimize off: PIL would renumber the slots)


# Look Up and Crouch play there and back (Player.c Player_State_LookUp / _Crouch): pressed, from frame 1 up to the hold
# frame (5 / 4), where the state stops the animation (speed 0); let go, it plays on at speed 64 / 128 through the rest and
# loops to frame 0, and only on frame 0 does the state give up for Player_State_Ground (which then shows Idle). Sonic's
# frame 0 is his standing frame and his last ones the way back down, so his pose ends as the button is let go. Spread
# over all the frames, an extra's (usually one) Looking Up frame stayed up through the way back and on frame 0 (about a
# quarter second after letting go; a half after a tap). name -> (frames leading in, hold frame): frame 0 and a missing way
# back are the extra's Idle frame; its own lead-in frames (all but the last Looking Up / Down one) lead in and, reversed,
# lead back. Timings, draw codes and hitboxes stay the base's.
RETURN_TO_IDLE = {"Look Up": (2, 5), "Crouch": (1, 4)}


def return_to_idle(anim, idle, lead_in, hold):
    frames = anim["frames"]
    m = len(frames)
    pic = lambda f: (f["sheet"], f["x"], f["y"], f["w"], f["h"], f["px"], f["py"])
    own = list(dict.fromkeys(pic(f) for f in frames))  # the extra's frames, in order
    if m <= hold or len(own) >= m:
        return  # (a full set of its own, drawn the base's way: left as it is)
    trans, pose = own[:-1], own[-1]
    lead = [trans[k * len(trans) // lead_in] for k in range(lead_in)] if trans else [pose] * lead_in
    back_n = m - 1 - hold
    back = [trans[::-1][k * len(trans) // back_n] for k in range(back_n)] if trans else [pic(idle)] * back_n
    order = [pic(idle)] + lead + [pose] * (hold - lead_in) + back
    for f, p in zip(frames, order):
        f["sheet"], f["x"], f["y"], f["w"], f["h"], f["px"], f["py"] = p


def build_player(e, out_dir, palette):
    """Player.bin / .gif: the extra's sprites on Mania's Sonic.bin list. Returns the appended animations' names."""
    folder = e["art"].name
    cfg_path = s2_config(e)
    cfg = json.loads(cfg_path.read_text())
    host = HOST_FILE[e["base"]]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # (Windows: a sheet still open)
        tmp = Path(tmp)
        tpl = tmp / "template" / "3K_Players"
        tpl.mkdir(parents=True)
        shutil.copy(MANIA / "Sprites" / "Players" / f"{host}.bin", tpl / f"{host}.bin")
        template_sheet(tpl / f"{host}.gif", palette)
        cfg["source"] = str((cfg_path.parent / cfg["source"]).resolve())
        cfg["palette"] = {str(s): c for s, c in palette.items()}  # (exact own colours land in their Mania slots)
        tmp_cfg = tmp / cfg_path.name
        tmp_cfg.write_text(json.dumps(cfg))
        out = tmp / "out"
        # build_s3k_art.build() pointed at Mania: its template, its output folder, no save menu / Blue Spheres files
        saved = (s3k.S3K, s3k.FROM_S2, s3k.s3k_build, s3k.build_menu_frame, s3k.build_special, set(s3k.HANG_FROM_HANDS),
                 s3k.COPY_HEADS_S3K)
        try:
            s3k.S3K = tmp / "template"
            s3k.COPY_HEADS_S3K = COPY_HEADS_MANIA
            # (Sonic's "Fly" is his Peel Out; Tails' is his flight: build_s3k_art's own entry)
            s3k.FROM_S2 = {**s3k.FROM_S2, **{k: v for k, v in MANIA_FROM_S2.items() if not (k == "Fly" and host != "Sonic")}}
            s3k.HANG_FROM_HANDS.add("Hang")
            s3k.s3k_build = lambda _extra: out
            s3k.build_menu_frame = lambda *a: None
            s3k.build_special = lambda *a: None
            s3k.build(tmp_cfg)
        finally:
            s3k.S3K, s3k.FROM_S2, s3k.s3k_build, s3k.build_menu_frame, s3k.build_special, hang, s3k.COPY_HEADS_S3K = saved
            s3k.HANG_FROM_HANDS.clear()
            s3k.HANG_FROM_HANDS.update(hang)
        sheet = Image.open(out / "3K_Players" / "Extra.gif")
        save_sheet(sheet, out_dir / "Player.gif")
        ani = ani_v5.read_bin(out / "3K_Players" / "Extra.bin")
    ani["sheets"] = [f"{PKG_SPRITES}/{folder}/Player.gif"]
    while ani["anims"] and ani["anims"][-1]["name"] == "(unused)" and not ani["anims"][-1]["frames"]:
        ani["anims"].pop()  # (the S3&K build's slots for moves this extra doesn't have)
    for a in ani["anims"]:
        if a["name"] in RETURN_TO_IDLE:
            return_to_idle(a, ani["anims"][0]["frames"][0], *RETURN_TO_IDLE[a["name"]])
    ani_v5.write_bin(out_dir / "Player.bin", ani)
    template = host_template(e)
    names = [a["name"] for a in template["anims"]]
    assert host != "Sonic" or len(names) == ANI_SONIC_COUNT
    assert [a["name"] for a in ani["anims"][:len(names)]] == names, f"animation list doesn't match Mania's {host}.bin"
    used = sorted({i for _, i in sheet.getcolors(256)} - {0})
    extra_anims = [a["name"] if a["frames"] else "-" for a in ani["anims"][len(names):]]
    print(f"  Player.bin: {len(ani['anims'])} animations ({len(names)} Mania + {', '.join(extra_anims) or 'none'}), "
          f"sheet {sheet.width}x{sheet.height}, palette slots {used}")
    return extra_anims


def _cutout(sheet, rect, backgrounds, drop_box):
    """RGB key array (-1: transparent) of a source sheet rect, its background colours transparent; drop_box: a life icon's
    HUD box left out (build_origins_menu.icon_background: frame lines and fill flood-filled from the edges)."""
    from build_origins_menu import icon_background
    x, y, w, h = rect
    rgb = np.array(Image.open(sheet).convert("RGB"))[y:y + h, x:x + w].astype(np.int64)
    key = rgb[..., 0] << 16 | rgb[..., 1] << 8 | rgb[..., 2]
    bg = np.isin(key, [int(c.lstrip("#"), 16) for c in backgrounds])
    if drop_box:
        colours = sorted(set(key[~bg].tolist()))
        idx = np.zeros(key.shape, np.int64)
        for i, c in enumerate(colours):
            idx[key == c] = i + 1
        idx[bg] = 0
        pal = {i + 1: (c >> 16, c >> 8 & 255, c & 255) for i, c in enumerate(colours)}
        bg |= icon_background(idx, pal, neck=True)[0]
    key[bg] = -1
    return _trim(key)


def _trim(key):
    ys, xs = np.nonzero(key >= 0)
    return key[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _ui_source(e):
    """(source sheet, background colours, {element: rect}) of the extra's UI pictures: its Sonic 1 config's "ui" entry
    (sheet2ani's life icon, continue frames...), cut from the artist's sheet in its true colours. A Mania-only package
    brings its own (mania_v5_art.ui_source: official frames)."""
    if "ui_source" in e:
        return e["ui_source"]
    for cfg_path in sorted(e["art"].glob("*.json")):
        try:
            cfg = json.loads(cfg_path.read_text())
        except ValueError:
            continue
        if not isinstance(cfg, dict) or not cfg.get("ui") or "source" not in cfg:
            continue
        for ui in cfg["ui"]:
            els = ui.get("elements", {})
            if "life_icon" in els and "mini_1" in els:
                return (cfg_path.parent / cfg["source"], cfg.get("background", []),
                        {k: v["rect"] for k, v in els.items() if "rect" in v})
    sys.exit(f"{e['art'].name}: no sheet2ani config with a life icon and continue frame (\"ui\")")


def build_save_select(e, out_dir):
    """SaveSelect.bin: a copy of the game's UI/SaveSelect.bin (still drawing from the game's own sheets) whose Sonic
    frames - Players 0, Player Shadows 0, Life Icons 0, Continue Icons 0 - come from the package's Save.gif: the portrait
    (its Sonic 1 life icon without its HUD box, 3x: _ui_source), its shadow (the portrait's outline in the UI's shadow colour, the approved
    rule), the life icon and the continue icon. Returns the pictures' colours (in SAVE_SLOTS' order)."""
    folder = e["art"].name
    sheet, background, rects = _ui_source(e)
    portrait = life = _cutout(sheet, rects["life_icon"], background, True)
    cont = _cutout(sheet, rects["mini_1"], background, False)
    portrait = portrait.repeat(PORTRAIT_SCALE, 0).repeat(PORTRAIT_SCALE, 1)
    colours = sorted({c for part in (portrait, life, cont) for c in part.ravel().tolist() if c >= 0})
    if len(colours) > len(SAVE_SLOTS):
        # more colours than slots (Jet): the rarest (by pixels on these pictures) go to the nearest kept one, the approved
        # rare-shade merge (reported)
        count = {c: sum(int((part == c).sum()) for part in (portrait, life, cont)) for c in colours}
        keep = sorted(sorted(colours, key=lambda c: -count[c])[:len(SAVE_SLOTS)])
        rgb = lambda c: np.array([c >> 16, c >> 8 & 255, c & 255])
        merged = {c: min(keep, key=lambda k: int(((rgb(c) - rgb(k)) ** 2).sum())) for c in colours if c not in keep}
        total = sum(count.values())
        print(f"  {folder}: {len(merged)} rarest save select colour(s) merged into the nearest "
              f"({sum(count[c] for c in merged)} of {total} px): "
              + ", ".join("#%06x -> #%06x" % (c, k) for c, k in merged.items()))
        for part in (portrait, life, cont):
            for c, k in merged.items():
                part[part == c] = k
        colours = keep
    slot = {c: SAVE_SLOTS[i] for i, c in enumerate(colours)}

    parts = [("portrait", portrait, False), ("shadow", portrait, True), ("life", life, False), ("continue", cont, False)]
    width = sum(p.shape[1] + 1 for _, p, _ in parts) + 1
    width = 1 << (width - 1).bit_length()  # (the engine reads sheet rows as a power-of-two width: RSDK surface lineSize)
    height = max(p.shape[0] for _, p, _ in parts) + 2
    img = Image.new("P", (width, height), 0)
    pal = [255, 0, 255] + [0] * 765
    for c, i in slot.items():
        pal[3 * i:3 * i + 3] = [c >> 16, c >> 8 & 255, c & 255]
    pal[3 * SAVE_SHADOW:3 * SAVE_SHADOW + 3] = [24, 64, 96]
    img.putpalette(pal)
    rects, x = {}, 1
    for name, p, shadow in parts:
        h, w = p.shape
        for yy in range(h):
            for xx in range(w):
                if p[yy, xx] >= 0:
                    img.putpixel((x + xx, 1 + yy), SAVE_SHADOW if shadow else slot[int(p[yy, xx])])
        rects[name] = (x, 1, w, h)
        x += w + 1
    save_sheet(img, out_dir / "Save.gif")

    ani = ani_v5.read_bin(MANIA / "Sprites" / "UI" / "SaveSelect.bin")
    sheet_id = len(ani["sheets"])
    ani["sheets"].append(f"{PKG_SPRITES}/{folder}/Save.gif")

    def place(anim, name, middle):
        f = ani["anims"][anim]["frames"][0]  # (Sonic's)
        fx, fy, w, h = rects[name]
        # the new picture centred where Sonic's was (middle), or on his centre line with its bottom row on his
        cx = f["px"] + f["w"] // 2
        py = f["py"] + f["h"] // 2 - h // 2 if middle else f["py"] + f["h"] - h
        f.update(sheet=sheet_id, x=fx, y=fy, w=w, h=h, px=cx - w // 2, py=py)
    place(1, "portrait", True)
    place(2, "shadow", True)
    place(3, "life", True)
    place(21, "continue", False)
    host_frame = {"sonic": 0, "tails": 1, "knuckles": 2}[e["base"]]  # (the slot draws its host's frame: Tails 1, Knuckles 2)
    for anim in (1, 2, 3, 21):
        if host_frame:
            fr = ani["anims"][anim]["frames"]
            fr[host_frame] = dict(fr[0], boxes=fr[host_frame]["boxes"])
    ani_v5.write_bin(out_dir / "SaveSelect.bin", ani)
    print(f"  SaveSelect.bin: portrait {portrait.shape[1]}x{portrait.shape[0]}, life {life.shape[1]}x{life.shape[0]}, "
          f"continue {cont.shape[1]}x{cont.shape[0]}, {len(colours)} colours in slots {SAVE_SLOTS[0]}+")
    return ["#%06X" % c for c in colours]


# The save select atlas: every MANIA_ENABLED extra's save select pictures on ONE sheet, so the menu costs one sprite sheet
# however many extras there are. (The engine holds 64 sheets at once, RSDKv5 SURFACE_COUNT, and the menu uses ~37 of its
# own: one Save.gif per extra overflowed at 28 extras, the 28th loaded as nothing and drawing it crashed, 2026-10-01.)
# SaveSelectAtlas.bin is a copy of the game's UI/SaveSelect.bin plus, per extra, an animation "extra:<folder>" with its
# four pictures (portrait, shadow, life, continue: the frames its own SaveSelect.bin puts in Players 0, Player Shadows 0,
# Life Icons 0, Continue Icons 0), which the mod copies into those frames while it draws that extra's slot.
# Colours: each picture keeps its own pixels, which are slot numbers (SAVE_SLOTS, the extra's "save_colors" written there
# only while its slot draws), so pictures with different colours share the sheet exactly (the GIF's own palette is
# not what the engine draws with). A package outside the atlas (a third party's) still has its own SaveSelect.bin /
# Save.gif: the mod loads those lazily, a few at most.
SAVE_ATLAS = "SaveSelectAtlas"  # Data/Sprites/NoSwap/SaveSelectAtlas.bin / .gif
KIT = bool(__import__("os").environ.get("NOSWAP_KIT"))
SAVE_ATLAS_WIDTH = 1024  # (a power of two: RSDK surface lineSize)
SAVE_ATLAS_PARTS = [1, 2, 3, 21]  # SaveSelect.bin's Players, Player Shadows, Life Icons, Continue Icons


def build_save_atlas():
    """Pack the built packages' Save.gif pictures (from their SaveSelect.bin frames) into SaveSelectAtlas.gif / .bin."""
    order = [e["art"].name for e in EXTRAS]
    folders = sorted(MANIA_ALL, key=lambda f: order.index(f) if f in order else 1 << 30)
    ani = ani_v5.read_bin(MANIA / "Sprites" / "UI" / "SaveSelect.bin")
    sheet_id = len(ani["sheets"])
    ani["sheets"].append(f"{PKG_SPRITES}/{SAVE_ATLAS}.gif")
    pieces, palette = [], None  # (folder, [(frame, pixels)])
    for folder in folders:
        pkg_bin, pkg_gif = PACKAGES / folder / "SaveSelect.bin", PACKAGES / folder / "Save.gif"
        if not pkg_bin.exists() or not pkg_gif.exists():
            if KIT:  # (the Creator Kit ships no atlas: another of the creator's characters not built yet is fine)
                print(f"  ({folder}: not built for Mania yet; left out of the save select atlas)")
                continue
            sys.exit(f"{folder}: no SaveSelect.bin / Save.gif to put in the save select atlas (build it first)")
        pkg = ani_v5.read_bin(pkg_bin)
        own = pkg["sheets"].index(f"{PKG_SPRITES}/{folder}/Save.gif")
        gif = Image.open(pkg_gif)
        palette = palette or gif.getpalette()
        px = np.array(gif)
        frames = []
        for anim in SAVE_ATLAS_PARTS:
            f = dict(pkg["anims"][anim]["frames"][0])
            if f["sheet"] != own:
                sys.exit(f"{folder}: SaveSelect.bin animation {anim} frame 0 isn't on its Save.gif")
            frames.append((f, px[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]]))
        pieces.append((folder, frames))
    # shelf packing, in the save select's order, 1 px apart
    x = y = 1
    row = 0
    for _, frames in pieces:
        for f, p in frames:
            if x + f["w"] + 1 > SAVE_ATLAS_WIDTH:
                x, y, row = 1, y + row + 1, 0
            f["_at"] = (x, y)
            x += f["w"] + 1
            row = max(row, f["h"])
    height = y + row + 1
    sheet = np.zeros((height, SAVE_ATLAS_WIDTH), np.uint8)
    template = ani["anims"]
    for folder, frames in pieces:
        out = []
        for (f, p), anim in zip(frames, SAVE_ATLAS_PARTS):
            ax, ay = f.pop("_at")
            sheet[ay:ay + f["h"], ax:ax + f["w"]] = p
            f.update(sheet=sheet_id, x=ax, y=ay)
            f["boxes"] = list(template[anim]["frames"][0]["boxes"])
            out.append(f)
        ani["anims"].append(dict(name=f"extra:{folder}", speed=0, loop=0, rot=0, frames=out))
    img = Image.fromarray(sheet, "P")
    img.putpalette(palette)
    save_sheet(img, PACKAGES / f"{SAVE_ATLAS}.gif")
    ani_v5.write_bin(PACKAGES / f"{SAVE_ATLAS}.bin", ani)
    print(f"save select atlas: {len(pieces)} extras on {SAVE_ATLAS}.gif ({SAVE_ATLAS_WIDTH}x{height})")


def runtime_palette(own):
    """{slot: 0xRRGGBB}: what a sprite can draw with in Mania while the extra plays: the global colours 1-63 (not the
    unused magenta ones) and its own slots."""
    out = {i: (c[0] << 16) | (c[1] << 8) | c[2] for i, c in global_palette().items()
           if 0 < i < PLAYER_SLOT and c != (255, 0, 255)}
    out.update({s: int(c.lstrip("#"), 16) for s, c in own.items()})
    return out


def shot_json(s):
    """A shot's numbers for the mod (build_s3k_shot's art recipe left out), its sound Mania's."""
    out = {k: v for k, v in s.items() if k not in ("art", "burn")}
    if out.get("sound"):
        out["sound"] = MANIA_SFX.get(out["sound"], out["sound"])
    return out


def build_shot(e, out_dir, palette):
    """Shot.bin / Shot.gif for an extra with a shot (animation 0; a second shot's animation 1): build_s3k_shot's frames
    for its recipe (exact pixels; colours matched to the Mania runtime palette), every frame with its hitbox as both of
    the file's boxes (the mod's stand-in hits with box 0). Returns the JSON's shot fields ({} without a shot)."""
    import build_s3k_shot as shot_art
    s1, s2 = ab.shot(e["id"], "s3k"), ab.shot2(e["id"], "s3k")
    for f in ("Shot.bin", "Shot.gif"):
        (out_dir / f).unlink(missing_ok=True)
    if not s1:
        return {}
    pal = runtime_palette(palette)
    extra = dict(e, palette=pal)  # (the flame recipe matches its colours exactly against "palette")
    shots = [s1] + ([s2] if s2 else [])
    # swap shots (monitor_swap's "swap_shots": John's sub-weapons; native/mania/src/ManiaCross.h): entry k's flight is
    # animation k, a burning one's flames after all the flights (build_s3k_shot.swap_anims, the S3&K layout)
    swaps = ab.swap_shots(e.get("id"), "s3k")
    if swaps:
        shots = list(swaps) + [dict(s, art=s["burn"]["art"], cycle=False) for s in swaps if "burn" in s]
    sets = [shot_art.frames(s["art"], extra, pal) for s in shots]
    width = 2 + sum(im.width + 2 for fr in sets for im, _, _ in fr)
    w = 1 << (width - 1).bit_length()  # (the engine reads sheet rows as a power-of-two width)
    h = max(im.height for fr in sets for im, _, _ in fr) + 4
    sheet = Image.new("P", (max(w, 16), h), 0)
    raw = [0] * 768
    for slot, c in pal.items():
        raw[3 * slot:3 * slot + 3] = [c >> 16, (c >> 8) & 255, c & 255]
    sheet.putpalette(raw)
    anims, x = [], 2
    for k, (s, fr) in enumerate(zip(shots, sets)):
        art = s["art"]
        box = tuple(art.get("hitbox", [-8, -8, 8, 8]))
        boxes = [tuple(b) for b in art["hitboxes"]] if "hitboxes" in art else [box] * len(fr)
        if len(boxes) != len(fr):
            sys.exit(f"{e['name']}: shot \"hitboxes\" has {len(boxes)} boxes for {len(fr)} frames")
        specs = []
        for (im, px, py), b in zip(fr, boxes):
            sheet.paste(im, (x, 2))
            specs.append(dict(sheet=0, duration=240, char=0, x=x, y=2, w=im.width, h=im.height, px=px, py=py, boxes=[b, b]))
            x += im.width + 2
        anims.append(dict(name="Shot" if k == 0 else f"Shot {k + 1}", speed=0 if s.get("cycle") else 240 // art.get("ticks", 2),
                          loop=0, rot=0, frames=specs))
    save_sheet(sheet, out_dir / "Shot.gif")
    ani_v5.write_bin(out_dir / SHOT_FILE, dict(sheets=[f"{PKG_SPRITES}/{e['art'].name}/Shot.gif"],
                                               hitboxes=shot_art.HITBOXES, anims=anims))
    print(f"  {SHOT_FILE}: {' + '.join(str(len(fr)) for fr in sets)} frame(s), {s1['motion']}"
          + (f", shot2 {s2['motion']}" if s2 else "") + f", sheet {sheet.width}x{sheet.height}")
    out = {"shot_file": f"{PKG_SPRITES}/{e['art'].name}/{SHOT_FILE}", "shot": shot_json(s1)}
    if s2:
        out["shot2"] = shot_json(s2)
    if swaps:  # (each with its flames' animation and lifetime: gen_s3k_header.swap_json)
        from gen_s3k_header import swap_json
        out["swap_shots"] = [shot_json(swap_json(s, burn)) for s, (_, burn) in zip(swaps, shot_art.swap_anims(swaps))]
    return out


def charge_palettes(e, palette):
    """A charge shot's flash (abilities.charge_palettes: Omega's Flame Blast) in Mania's slots: per phase {slot: colour},
    each of his own colours it changes found where Mania keeps it (OWN_SLOTS); one merged into a global colour can't
    flash (reported). None without a charge shot."""
    if e.get("id") not in ab.charge_shots():
        return None
    where = {int(c.lstrip("#"), 16): s for s, c in palette.items()}
    out, lost = [], set()
    for phase in ab.charge_palettes(e["id"]):
        m = {}
        for slot, colour in phase.items():
            own = e["palette"].get(slot)
            if own in where:
                m[str(where[own])] = "#%06X" % colour
            else:
                lost.add("#%06x" % own if own is not None else f"slot {slot}")
        out.append(m)
    if lost:
        print(f"  {e['art'].name}: the charge flash can't change {', '.join(sorted(lost))} (not in its own Mania slots)")
    return out


def spark_glow(e, palette):
    """The Shine Spark's glow (abilities.py charge "spark_glow_slots" / "spark_glow_to" / "spark_glow": Heavy's) in Mania's
    slots: per level (the S3&K DLL's SparkGlow k 0-2) {slot: colour}, each glowing colour of his found where Mania keeps
    it; one merged into a global colour can't glow (reported). None without one."""
    c = ab.ABILITIES.get(e.get("id"), {})
    if not c.get("spark_speed") or not c.get("spark_glow_slots"):
        return None
    where = {int(col.lstrip("#"), 16): s for s, col in palette.items()}
    to, out, lost = c["spark_glow_to"], [], set()
    for a in c["spark_glow"]:
        m = {}
        for slot in c["spark_glow_slots"]:
            own = e["palette"].get(slot)
            if own not in where:
                lost.add(f"slot {slot}")
                continue
            m[str(where[own])] = "#%06X" % sum(((v := own >> sh & 255) + (((to >> sh & 255) - v) * a >> 8)) << sh
                                                for sh in (16, 8, 0))
        out.append(m)
    if lost:
        print(f"  {e['art'].name}: the spark glow can't change {', '.join(sorted(lost))} (not in its own Mania slots)")
    return out


def mania_json(e, palette, save_colours, extra_anims, shots=None):
    """noswap_character.json for NoSwapMania: the Origins package's identity fields (key, name, base...) and a "mania"
    section, whose "abilities" are gen_s3k_header.ability_fields (the S3&K DLL's names and values) not at their default."""
    folder = e["art"].name
    c = ab.ABILITIES.get(e.get("id"), {"abilities": []})
    fields = {name: MANIA_SFX.get(value, value) if kind == "str" else value
              for kind, name, _, value in ability_fields(c, e["name"]) if value != DEFAULT_OF[name]}
    over = MANIA_OVERRIDES.get(folder, {})
    host = over.get("host_tint", [])
    return {
        "key": e["key"],
        "folder": folder,
        "name": e["name"],
        "order": e["n"],  # (its registry number, tools/registry.py: the save select's order)
        "base": e["base"],
        "credit_short": e["credit_short"],
        "mania": {
            "player": f"{PKG_SPRITES}/{folder}/Player.bin",
            "save_select": f"{PKG_SPRITES}/{folder}/SaveSelect.bin",
            "save_colors": save_colours,  # the save select pictures' colours, in SAVE_SLOTS' order
            # the character it plays on (extras.py "base"): sonic, tails or knuckles (the mod's hosting, ManiaHost.h)
            "host": e["base"],
            "anim_base": anim_base(e),  # its first ability animation (abilities.py slot 41; 42 is anim_base + 1...)
            "ability_anims": extra_anims,
            "palette": {str(s): palette[s].upper() for s in sorted(palette)},
            # own slots (of 64-69) whose other banks' versions are the stage's Sonic colours there; the rest are tinted
            "host_tint": host,
            # own slots (of 64-69) that fade to Sonic's Super golds (extras.py "super"); the rest stay as they are
            "super_fade": host if e["super"] else [],
            # never curls into a ball (extras.py "no_roll": Gamma): no roll, no Spin Dash; down + jump is a plain jump
            "no_roll": bool(e["no_roll"]),
            # rolls in its own "Rolling" animation (extras.py "roll": its jump isn't a ball; ability slot 7, ManiaNoStomp.h)
            **({"roll": True} if e.get("roll") else {}),
            # its shots break breakable walls (abilities.py "shot_breaks_walls": Gamma, who can't roll through them)
            "shot_breaks_walls": bool(c.get("shot_breaks_walls")),
            "moves": list(c["abilities"]),  # abilities.py's list: the mod logs the ones it has no module for
            "abilities": fields,
            # its projectile(s) (abilities.py "shot" / "shot2", S3&K's numbers; build_shot), when it has one
            **(shots or {}),
            # copy heads (abilities.py copy_heads: Emerl's): set m's copy of COPY_HEADS_MANIA[k] is animation
            # offset + count * m + k (build_s3k_art: COPY_HEAD_OFFSET past the ability slots); one set per ability_cycle move
            # a charge shot's flash: per phase, Mania slot -> colour (charge_palettes), when it has one
            **({"charge_palettes": charge_palettes(e, palette)} if charge_palettes(e, palette) else {}),
            # the Shine Spark's glow: per level, Mania slot -> colour (spark_glow; Heavy's), when it has one
            **({"spark_glow": spark_glow(e, palette)} if spark_glow(e, palette) else {}),
            **({"copy_heads": {"offset": ANI_SONIC_COUNT + s3k.COPY_HEAD_OFFSET, "count": len(COPY_HEADS_MANIA),
                               "sets": len(c.get("ability_cycle", []))}} if c.get("copy_heads") else {}),
        },
        "note": "Built by tools/build_mania_art.py: this character's package for NoSwapMania (the Sonic Mania "
                "decompilation mod), which scans Data/Sprites/NoSwap/*/noswap_character.json at startup.",
    }


def build(folder):
    e = extra_of(folder)
    if e.get("source") == "v5":  # (a Mania-only package from an existing player file: tools/mania_v5_art.py)
        import mania_v5_art
        return mania_v5_art.build(e)
    print(f"{folder} ({e['name']}):")
    out_dir = PACKAGES / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    palette = mania_palette(e)
    extra_anims = build_player(e, out_dir, palette)
    save_colours = build_save_select(e, out_dir)
    shots = build_shot(e, out_dir, palette)
    data = mania_json(e, palette, save_colours, extra_anims, shots)
    (out_dir / "noswap_character.json").write_text(json.dumps(data, indent=1) + "\n")
    print(f"  noswap_character.json: palette {data['mania']['palette']}, moves {data['mania']['moves']}")
    import build_mania_hud  # (its HUD, act clear name, continue and Blue Spheres files: ManiaHud.h)
    build_mania_hud.build(e, out_dir, palette)
    import own_sounds  # (its own sounds, character.json "sounds": Data/SoundFX/NoSwap/<id>/, loaded by Game.xml)
    sounds = own_sounds.write_mania(e, MOD)
    if sounds:
        print(f"  own sounds: {', '.join(sounds)}")


if __name__ == "__main__":
    wanted = sys.argv[1:] or MANIA_ALL
    order = [e["art"].name for e in EXTRAS]
    for f in sorted(wanted, key=lambda f: order.index(f) if f in order else 1 << 30):
        build(f)
    build_save_atlas()  # (always every MANIA_ALL extra, from their built packages)
    import own_sounds  # (every package's own sounds on disk, in Game.xml's generated <soundfx> block)
    own_sounds.write_game_xml(MOD / "Data" / "Game" / "Game.xml", own_sounds.game_xml_lines(MOD))
