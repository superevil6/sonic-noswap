#!/usr/bin/env python3
"""Build an extra's Mania HUD and screen art (NoSwapMania), next to its other package files:

    mods/NoSwapMania/Data/Sprites/NoSwap/<folder>/
        Hud.bin / Hud.gif   0 "Life Icon"      the HUD's life icon (in place of Global/HUD.bin "Life Icons" 0)
                            1 "Player Name"    the act clear name ("<NAME> GOT THROUGH": HUD.bin "Player Name" 0)
                            2 "Continue Icon"  the continue icon
                            3 "Sign Face"      the end-of-act signpost's face (in place of Global/SignPost.bin
                                               "Sonic"): Mania's own board with the extra's Origins sign face in its
                                               panel (sign_face; its colours "sign_colors" in the JSON)
                            "Item Icon"        the 1-up monitor's icon (its life icon, centred; ManiaSweep.h)
        Results.bin         a copy of Special/Results.bin (the UFO results) with its name in the host's messages
        TVVan.bin           a copy of SPZ1/TVVan.bin whose "TV <host>" balls are the extra's spin ball
        CutsceneCPZ.bin     a copy of Players/CutsceneCPZ.bin (Chemical Plant 1's intro) whose Sonic / Tails /
                            Knuckles animations show the extra's Look Up, with their own timings (build_cutscene_cpz)
        Continue.bin        a copy of Players/Continue.bin whose Sonic animations (Idle 0, React 1, Icon 11 frame 0)
                            show the extra: its own Bored 1 / Victory frames from Player.gif (Idle where it has none),
                            its continue icon; the other characters' stay the game's
        SpecialBS.bin       the Blue Spheres runner (SpecialBS/Sonic.bin's Idle, Run, Jump, Bounce): the extra's own
                            spin ball (its Jump frames from Player.gif, in turn), as the S3&K pipeline's 3K_Special/
                            Extra.bin (its sheet has no back views)

Usage: build_mania_hud.py --build <folder> ...   (build_mania_art.py runs it for every extra it builds)
       build_mania_hud.py <preview.png> [NAME ...]  (a look at the letters, or at names set in them)

The mod (native/mania/src/ManiaHud.h) loads them by these names from the package folder; without them it shows Sonic's.

Colours: the icons are the save select's own pictures (Save.gif, in the menu palette's free slots, exact colours): the
mod writes the extra's "save_colors" into those slots only while it draws them. The continue and Blue Spheres frames
are its player sprites (the Mania runtime palette), whose colours the mod writes in those scenes. The name is in the
global palette's blues (SONIC's slots); the JSON's "name_colors" (ui_accent.mania_name, its S3&K accent as a ramp) go in
those slots only while it draws, as Tails' and Knuckles' names are drawn in their own slots.

The name: Mania's own letters, all in SONIC's blue (the extra plays as Sonic, as the S&K pipeline's names are all
blue): SONIC's own (Global/HUD.bin "Player Name"); then the results' white words' (GOT THROUGH, GAME OVER, TIME OVER:
the same rounded, 3D-sided font); then the credits' white headings (UI/CreditsText.bin "Heading 0", A-Z in that same
font) for the rest. Recoloured to the blue by role (SCHEMES: a palette mapping, as Mania's own names differ only in
colour); no pixel drawn. Spaced as SONIC is (word()), ending where SONIC's does.
"""
import functools
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ani_v5
from gifio import save_sheet

MANIA = Path(__import__("os").environ.get("NOSWAP_MANIA_DATA") or Path.home() / "Code" / "mania" / "extracted" / "Data") / "Sprites"
HUD = ani_v5.read_bin(MANIA / "Global" / "HUD.bin")
DISPLAY = Image.open(MANIA / "Global" / "Display.gif")

# Each name word's colours by role (darkest shadow first), and SONIC's blue for each role. A role: a 3D side / drop
# shadow (a, b, c), the face (body), its lit rim and its brightest highlight.
BLUE = {"a": 2, "b": 3, "c": 4, "lower": 5, "body": 6, "rim": 7, "hi": 11, "top": 40}
SCHEMES = {
    "blue": {2: "a", 3: "b", 4: "c", 5: "lower", 6: "body", 7: "rim", 11: "hi", 40: "top"},
    "white": {34: "a", 35: "b", 36: "c", 37: "hi", 39: "rim", 41: "body"},
    # the credits' white headings (UI/CreditsText.bin "Heading 0"): the same letters as GAME OVER's, pixel for pixel,
    # with 135 for the white words' 39 (the rim) and a 40 top highlight
    "credits": {34: "a", 35: "b", 36: "c", 37: "hi", 135: "rim", 41: "body", 40: "top"},
}
FACE = {BLUE["lower"], BLUE["body"], BLUE["rim"], BLUE["hi"], BLUE["top"]}


def frame_image(anim, k):
    f = next(a for a in HUD["anims"] if a["name"] == anim)["frames"][k]
    return DISPLAY.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))


def recolour(img, scheme):
    m = {i: BLUE[role] for i, role in SCHEMES[scheme].items()}
    return img.point(lambda i: m.get(i, 0) if i else 0)


def split(word_img, text, scheme):
    """A word's letters in the blue: SONIC's are apart (empty columns between them); the others touch, so
    build_s3k_hud.letters splits them at the face's column runs, and only each letter's own parts are kept (own_part)."""
    if scheme == "blue":
        a = np.array(word_img)
        runs, x = [], 0
        while x < a.shape[1]:
            if a[:, x].any():
                start = x
                while x < a.shape[1] and a[:, x].any():
                    x += 1
                runs.append((start, x))
            x += 1
        if len(runs) != len(text):
            sys.exit(f"{text}: {len(runs)} letters found")
        return {c: recolour(word_img.crop((x0, 0, x1, a.shape[0])), scheme) for c, (x0, x1) in zip(text, runs)}
    import build_s3k_hud
    face = {i for i, role in SCHEMES[scheme].items() if role not in ("a", "b", "c")}
    return {c: own_part(recolour(g, scheme)) for c, g in build_s3k_hud.letters(word_img, text, face).items()}


def own_part(img):
    """Only the letter's own pixels: its 4-connected parts that have some face in them (a neighbour's shadow that
    letters() kept near this letter is dropped), cropped to them."""
    a = np.array(img)
    keep = np.zeros(a.shape, bool)
    seen = np.zeros(a.shape, bool)
    h, w = a.shape
    for y0 in range(h):
        for x0 in range(w):
            if not a[y0, x0] or seen[y0, x0]:
                continue
            part, todo = [], [(y0, x0)]
            seen[y0, x0] = True
            while todo:
                y, x = todo.pop()
                part.append((y, x))
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < h and 0 <= nx < w and a[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        todo.append((ny, nx))
            if any(a[p] in FACE for p in part):
                for p in part:
                    keep[p] = True
    a[~keep] = 0
    xs = np.nonzero(a.any(0))[0]
    return to_img(a[:, xs.min():xs.max() + 1])


def to_img(a):
    img = Image.fromarray(np.asarray(a, np.uint8), "P")
    img.putpalette(DISPLAY.getpalette())
    return img


def arr(img):
    return np.array(img).astype(np.uint8)


def paste(dst, src, x, y=0):
    """src's non-transparent pixels over dst at (x, y)"""
    h, w = src.shape
    region = dst[y:y + h, x:x + w]
    np.copyto(region, src, where=src > 0)


CREDITS = ani_v5.read_bin(MANIA / "UI" / "CreditsText.bin")
CREDITS_SHEET = Image.open(MANIA / "UI" / "CreditsText.gif")


def credits_letter(c):
    """A letter of the credits' white headings ("Heading 0": A-Z in order), in the blue."""
    a = next(x for x in CREDITS["anims"] if x["name"] == "Heading 0")
    f = a["frames"][ord(c) - ord("A")]
    return own_part(recolour(CREDITS_SHEET.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])), "credits"))


@functools.lru_cache(None)
def glyphs():
    """Every letter A-Z, in the blue: SONIC's own first; then the results' white words' (GOT THROUGH, GAME OVER,
    TIME OVER: SONIC's rounded style); then the credits' white headings for the rest (B D F J K L P Q W X Y Z: the
    same font as GAME OVER's, so K, L and Y come from there rather than KNUCKLES / MIGHTY's squarer style). Only
    the game's own pixels, recoloured by role (SCHEMES); nothing drawn."""
    out = {}
    for c, g in split(frame_image("Player Name", 0), "SONIC", "blue").items():
        out.setdefault(c, g)
    for anim, k, text in (("Got Through", 0, "GOT"), ("Got Through", 1, "THROUGH")):
        for c, g in split(frame_image(anim, k), text, "white").items():
            out.setdefault(c, g)
    for anim, word in (("Game Over", "GAMEOVER"), ("Time Over", "TIMEOVER")):  # (one frame per letter)
        for k, c in enumerate(word):
            out.setdefault(c, own_part(recolour(frame_image(anim, k), "white")))
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if c not in out:
            out[c] = credits_letter(c)
    return out


GAP = 2     # empty columns between letters (SONIC's own: each letter's shadow, then 2 clear columns, then the next)
SPACE = 8   # a space: this many more


def word(text, g):
    """The name in the blue letters, set as SONIC is (GAP clear columns between letters)."""
    parts, x = [], 0
    for c in text.upper():
        if c == " ":
            x += SPACE
            continue
        if c not in g:
            sys.exit(f"{text}: no letter {c!r} in the Mania name font")
        a = arr(g[c])
        parts.append((a, x))
        x += a.shape[1] + GAP
    out = np.zeros((18, x - GAP), np.uint8)
    for a, px in parts:
        paste(out, a[:18], px)
    return out


def preview(images, path, scale=4):
    w = sum(i.width + 2 for i in images)
    h = max(i.height for i in images)
    sheet = Image.new("P", (w, h), 0)
    sheet.putpalette(DISPLAY.getpalette())
    x = 0
    for i in images:
        sheet.paste(i, (x, 0))
        x += i.width + 2
    sheet.convert("RGB").resize((w * scale, h * scale), Image.NEAREST).save(path)


# ------------------------------------------------------------------------------------------------ the package files
HUD_FILE, CONTINUE_FILE, SPECIAL_FILE = "Hud.bin", "Continue.bin", "SpecialBS.bin"  # (ManiaHud.h loads these names)
ANI_JUMP = 10  # (Mania's Sonic.bin list)


def _pow2(n):
    return 1 << max(0, n - 1).bit_length()


# The signpost face. Mania's boards (Global/SignPost.bin "Sonic"... on Global/Objects2.gif) are 48x30: a grey frame
# (rows 0-2 and 27-29, columns 0-3 and 44-47) round a 40x24 panel at 4,3. Origins' sign face (the S1/S2 UI sheet's
# "sign_face", 48x32, what S3&K's SignPost_Extra shows too) has its face in a 40x24 area at 4,5 (tools/sign_face.py),
# the same size: so the extra's face area goes on Mania's own board, exactly (crop and position only). The board is
# Eggman's (the only face that leaves the frame clean but for his moustache tips, which give way to the frame's own
# columns from a clean row of it).
SIGN_W, SIGN_H = 48, 30
PANEL = (4, 3)            # Mania's panel, 40x24
ORIGINS_FACE = (4, 5, 40, 24)  # in the Origins sign_face
SIGN_ANIM = "Sonic"       # SignPost.bin's animation the extra's face stands in for (its frame count and timing)
FRAME_GREYS = set(range(32, 42))  # the frame's colours (global slots)


@functools.lru_cache(None)
def mania_board():
    """Mania's empty board (global slot numbers; the panel left 0), and SignPost.bin's Sonic animation."""
    sign = ani_v5.read_bin(MANIA / "Global" / "SignPost.bin")
    sheet = np.array(Image.open(MANIA / sign["sheets"][0]))
    egg = next(a for a in sign["anims"] if a["name"] == "Eggman")["frames"][0]
    board = sheet[egg["y"]:egg["y"] + egg["h"], egg["x"]:egg["x"] + egg["w"]].copy()
    if board.shape != (SIGN_H, SIGN_W):
        sys.exit(f"SignPost.bin's Eggman board is {board.shape[1]}x{board.shape[0]}, not {SIGN_W}x{SIGN_H}")
    clean = 5  # (a row whose side columns are all frame)
    for r in range(PANEL[1], PANEL[1] + 24):
        for c0 in (0, SIGN_W - PANEL[0]):
            if not set(board[r, c0:c0 + PANEL[0]].tolist()) <= FRAME_GREYS:
                board[r, c0:c0 + PANEL[0]] = board[clean, c0:c0 + PANEL[0]]
    board[PANEL[1]:PANEL[1] + 24, PANEL[0]:PANEL[0] + 40] = 0
    return board, next(a for a in sign["anims"] if a["name"] == SIGN_ANIM)


def sign_face(e):
    """The extra's Mania signpost face: Mania's board with its Origins face in the panel. Returns (pixels, colours):
    the face's pixels are SAVE_SLOTS numbers (its colours, exact, in that order; ManiaHud.h writes them there only while
    the signpost draws), the frame's the global slots it is drawn with in Mania."""
    import build_mania_art as mania
    from extras import ui_manifest
    if "sign_face_source" in e:  # (a Mania-only package's official face: its sheet and frame, tools/mania_v5_art.py)
        sheet, (x, y, w, h) = e["sign_face_source"]
    else:
        m = ui_manifest(e, "ui")
        if "sign_face" not in m["frames"]:
            return None, []
        sheet, (x, y, w, h) = m["sheet"], m["frames"]["sign_face"]
    ui = Image.open(sheet)
    fx, fy, fw, fh = ORIGINS_FACE
    idx = np.array(ui)[y + fy:y + fy + fh, x + fx:x + fx + fw]
    pal = ui.getpalette()
    rgb = [(pal[3 * i] << 16) | (pal[3 * i + 1] << 8) | pal[3 * i + 2] for i in range(len(pal) // 3)]
    # (UI art's slots 128+ are its slots 0-127 in the player's palette line, #FF00FF on the sheet: build_s3k_hud's
    # remap_to_display reads them as i - 128 too; e.g. Metal Sonic's and Fang's heads)
    rgb = [rgb[i - 128] if i >= 128 and rgb[i] == 0xFF00FF else c for i, c in enumerate(rgb)]
    count = {}
    for i in idx.ravel().tolist():
        count[rgb[i]] = count.get(rgb[i], 0) + 1
    colours = sorted(count, key=lambda c: -count[c])
    if len(colours) > len(mania.SAVE_SLOTS):
        sys.exit(f"{e['art'].name}: its sign face has {len(colours)} colours, more than the {len(mania.SAVE_SLOTS)} slots")
    slot = {c: mania.SAVE_SLOTS[k] for k, c in enumerate(colours)}
    board, _ = mania_board()
    out = board.copy()
    out[PANEL[1]:PANEL[1] + fh, PANEL[0]:PANEL[0] + fw] = np.vectorize(lambda i: slot[rgb[i]])(idx)
    return out, ["#%06X" % c for c in colours]


def sign_anim(sign_y, host="Sonic"):
    """Hud.bin's 3 "Sign Face": as many frames as SignPost.bin's animation of the extra's host (Sonic; Tails' and
    Knuckles' have 11: the signpost's face animator keeps its own frame number and timing; ManiaHud.h only points it at
    these frames while drawing), all the board at 1,sign_y on Hud.gif, with Sonic's board's pivot."""
    _, sonic = mania_board()
    if host != SIGN_ANIM:
        sonic = next(a for a in ani_v5.read_bin(MANIA / "Global" / "SignPost.bin")["anims"] if a["name"] == host)
    frames = [dict(f, sheet=0, x=1, y=sign_y, w=SIGN_W, h=SIGN_H, boxes=[]) for f in sonic["frames"]]
    return dict(name="Sign Face", speed=sonic["speed"], loop=sonic["loop"], rot=0, frames=frames)


def build(e, out_dir, palette):
    """Hud.bin / Hud.gif, Continue.bin and SpecialBS.bin for one extra (see the module docstring); needs its Player.bin
    and its save select pictures (build_mania_art.build_player, build_save_select)."""
    import build_mania_art as mania
    folder = e["art"].name
    name = word(e["name"], glyphs())
    sign, sign_colours = sign_face(e)
    sign_y = name.shape[0] + 3  # (the sign board below the name)
    width = _pow2(max(name.shape[1], SIGN_W) + 2)
    height = _pow2(sign_y + SIGN_H + 1 if sign is not None else name.shape[0] + 2)
    canvas = np.zeros((height, width), np.uint8)
    paste(canvas, name, 1, 1)
    if sign is not None:
        canvas[sign_y:sign_y + SIGN_H, 1:1 + SIGN_W] = sign
    img = to_img(canvas)  # (Display.gif's palette: the global colours the name and frame are in)
    gif_pal = img.getpalette()
    for k, c in enumerate(sign_colours):  # (only for a look at the GIF: the game draws with its own palette)
        gif_pal[3 * mania.SAVE_SLOTS[k]:3 * mania.SAVE_SLOTS[k] + 3] = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    img.putpalette(gif_pal)
    sheet_rel = f"{mania.PKG_SPRITES}/{folder}/Hud.gif"
    save_sheet(img, out_dir / "Hud.gif")

    # the icons: the save select's own pictures (Save.gif, in the menu's free slots; ManiaHud.h writes the extra's
    # "save_colors" there while it draws them, so they show in their exact colours anywhere)
    save = ani_v5.read_bin(out_dir / "SaveSelect.bin")
    life_f, cont_f = save["anims"][3]["frames"][0], save["anims"][21]["frames"][0]
    save_rel = save["sheets"][life_f["sheet"]]
    if save["sheets"][cont_f["sheet"]] != save_rel or not save_rel.endswith("/Save.gif"):
        sys.exit(f"{folder}: SaveSelect.bin's life / continue icons aren't on its Save.gif")
    lw, lh, cw, ch = life_f["w"], life_f["h"], cont_f["w"], cont_f["h"]
    nw = name.shape[1]
    # the life icon where Sonic's head is in HUD.bin's frame (18x17 at 0,-17: his head over columns 0-16, rows to -2);
    # the name ending where SONIC's does (px -92 + 74 wide: 18 left of the position, then "GOT" as usual)
    sonic_name = next(a for a in HUD["anims"] if a["name"] == "Player Name")["frames"][0]
    name_end = sonic_name["px"] + sonic_name["w"]
    pic = lambda f, px, py: dict(f, sheet=1, duration=0, px=px, py=py, boxes=[])
    ani_v5.write_bin(out_dir / HUD_FILE, dict(sheets=[sheet_rel, save_rel], hitboxes=[], anims=[
        dict(name="Life Icon", speed=0, loop=0, rot=0, frames=[pic(life_f, 9 - (lw + 1) // 2, -1 - lh)]),
        dict(name="Player Name", speed=0, loop=0, rot=0, frames=[
            dict(sheet=0, duration=0, char=0, x=1, y=1, w=nw, h=name.shape[0], px=name_end - nw, py=sonic_name["py"],
                 boxes=[])]),
        dict(name="Continue Icon", speed=0, loop=0, rot=0, frames=[pic(cont_f, -(cw // 2), 12 - ch)]),
    ] + ([sign_anim(sign_y, {"tails": "Tails", "knuckles": "Knuckles"}.get(e.get("base"), SIGN_ANIM))] if sign is not None else [])
      # (the 1-up monitor's icon: its life icon centred as ItemBox.bin's "Powerups" are (16x16 at -8,-8), as many
      # frames as that animation, so the monitor's own frame number picks it whatever it is; ManiaSweep.h finds it by
      # name)
      + [dict(name=ITEM_ICON_ANIM, speed=0, loop=0, rot=0,
              frames=[pic(life_f, -(lw // 2), -(lh // 2)) for _ in range(ITEMBOX_POWERUPS)])]))
    # its sign face's colours, in SAVE_SLOTS' order (ManiaHud.h writes them while the signpost draws)
    json_path = out_dir / "noswap_character.json"
    data = json.loads(json_path.read_text())
    data["mania"]["sign_colors"] = sign_colours
    # its act clear / UFO results name's colours (ui_accent.mania_name: its S3&K accent as a ramp, for SONIC's letter
    # slots; ManiaHud.h writes them only while the name draws); none: the name stays in Sonic's blue
    import ui_accent
    name_colours = ui_accent.mania_name(e)
    if name_colours:
        data["mania"]["name_colors"] = name_colours
    else:
        data["mania"].pop("name_colors", None)
    json_path.write_text(json.dumps(data, indent=1) + "\n")

    player = ani_v5.read_bin(out_dir / "Player.bin")
    named = {a["name"]: a for a in player["anims"]}

    # Continue.bin: the game's, Sonic's animations swapped (its sheets first, then the player's and Hud.gif)
    cont_bin = ani_v5.read_bin(MANIA / "Players" / "Continue.bin")
    base = len(cont_bin["sheets"])
    cont_bin["sheets"] += player["sheets"] + [save_rel]
    save_sheet_id = len(cont_bin["sheets"]) - 1

    def from_player(anim_name, fallback):
        a = named.get(anim_name) if named.get(anim_name, {}).get("frames") else named[fallback]
        frames = [dict(f, sheet=f["sheet"] + base, boxes=[f["boxes"][0] if f["boxes"] else (0, 0, 0, 0)]) for f in a["frames"]]
        return dict(a, frames=frames)
    # (a package with its own continue poses names them: mania_only "continue", Amy's S3&K ones)
    idle_name, react_name = e.get("continue_anims") or ("Bored 1", "Victory")
    idle, react = from_player(idle_name, "Idle"), from_player(react_name, "Idle")
    # (its host's animations: Sonic's 0-1 and icon frame 0, Tails' 2-3 / 1, Knuckles' 4-5 / 2: extras.py "base")
    host = {"sonic": 0, "tails": 1, "knuckles": 2}.get(e.get("base", "sonic"), 0)
    cont_bin["anims"][2 * host] = dict(idle, name=cont_bin["anims"][2 * host]["name"])
    cont_bin["anims"][2 * host + 1] = dict(react, name=cont_bin["anims"][2 * host + 1]["name"])
    icon = cont_bin["anims"][11]["frames"][host]
    icon.update(sheet=save_sheet_id, x=cont_f["x"], y=cont_f["y"], w=cw, h=ch, px=-(cw // 2), py=icon["py"] + icon["h"] - ch)
    ani_v5.write_bin(out_dir / CONTINUE_FILE, cont_bin)

    # SpecialBS.bin: the Blue Spheres runner's animations, all the extra's spin ball (its jump frames, in turn)
    tpl = ani_v5.read_bin(MANIA / "SpecialBS" / "Sonic.bin")
    balls, seen = [], set()
    for f in player["anims"][ANI_JUMP]["frames"]:
        k = (f["sheet"], f["x"], f["y"], f["w"], f["h"])
        if k not in seen:
            seen.add(k)
            balls.append(f)
    feet = tpl["anims"][0]["frames"][0]["py"] + tpl["anims"][0]["frames"][0]["h"]  # (Idle and Run stand on it)
    jump_bottom = tpl["anims"][2]["frames"][0]["py"] + tpl["anims"][2]["frames"][0]["h"]
    anims = []
    for a in tpl["anims"]:
        frames = []
        for k, tf in enumerate(a["frames"]):
            b = balls[k % len(balls)]
            bottom = jump_bottom if a["name"] in ("Jump", "Bounce") else feet
            frames.append(dict(tf, sheet=b["sheet"], x=b["x"], y=b["y"], w=b["w"], h=b["h"], px=-(b["w"] // 2),
                               py=bottom - b["h"], boxes=[]))
        anims.append(dict(a, frames=frames))
    ani_v5.write_bin(out_dir / SPECIAL_FILE, dict(sheets=list(player["sheets"]), hitboxes=tpl["hitboxes"], anims=anims))
    cpz = build_cutscene_cpz(player, out_dir)
    build_results(sheet_rel, nw, host, out_dir)
    build_tv_van(player, balls, host, out_dir)
    print(f"  {HUD_FILE}: life icon {lw}x{lh}, name \"{e['name']}\" {nw} px, continue icon {cw}x{ch}"
          + (f", sign face ({len(sign_colours)} colours)" if sign is not None else ", NO sign face") + "; "
          f"{CONTINUE_FILE} (idle {idle['name']}, react {react['name']}); {SPECIAL_FILE} ({len(balls)} ball frames); "
          f"{CUTSCENE_CPZ_FILE} ({cpz}); {RESULTS_FILE}; {TV_VAN_FILE}")


# ------------------------------------------------------------------------------------------------ ManiaSweep.h's files
ITEM_ICON_ANIM = "Item Icon"
ITEMBOX_POWERUPS = 18  # (Global/ItemBox.bin "Powerups": the 1-ups are frames 7 Sonic, 8 Tails, 9 Knuckles)

# The UFO results (SpecialClear): Special/Results.bin's "<Host> UI" animation holds every word of its messages, the
# player's name among them in SONIC's blue (frames 1, 4 and 8: the same pixels, palette indices and font as HUD.bin's
# "Player Name", so the extra's Hud.gif name is right there too) and, in the all-emeralds message, in the results'
# yellow (frame 13). The package's copy: the host's name frames show the extra's name, the rest the game's.
#   1 "<NAME> GOT A" / 4 "<NAME> GOT ALL": the name ends where the host's does (GOT A / GOT ALL stay put, as act clear);
#   8 "NOW <NAME> CAN" (7, 8, 9) and 13 "BE SUPER <NAME>" (10, 11, 13): set as the game sets them (the same gaps
#     between words), each line centred where the host's was. Frame 13 is the blue name: the results' yellow letters
#     are a different style (only SONIC TAILS KNUCKLES SUPER HYPER exist), so there is no yellow name to set.
RESULTS_FILE = "Results.bin"
RESULTS_HOST_ANIMS = ("Sonic UI", "Tails UI", "Knux UI")


def build_results(hud_rel, name_w, host, out_dir):
    res = ani_v5.read_bin(MANIA / "Special" / RESULTS_FILE)
    sheet = len(res["sheets"])
    res["sheets"].append(hud_rel)
    fr = next(a for a in res["anims"] if a["name"] == RESULTS_HOST_ANIMS[host])["frames"]
    name = lambda f, px: f.update(sheet=sheet, x=1, y=1, w=name_w, h=18, px=px)
    for k in (1, 4):
        name(fr[k], fr[k]["px"] + fr[k]["w"] - name_w)

    def line(first, mid, last, name_k):
        """Words first..last (name_k the name) set with their own gaps, the line centred where it was."""
        words = [fr[k] for k in (first, mid, last)]
        gaps = [words[i + 1]["px"] - words[i]["px"] - words[i]["w"] for i in (0, 1)]
        centre = (words[0]["px"] + words[2]["px"] + words[2]["w"]) / 2
        widths = [name_w if k == name_k else fr[k]["w"] for k in (first, mid, last)]
        x = round(centre - (sum(widths) + sum(gaps)) / 2)
        name(fr[name_k], 0)
        for i, w in enumerate(words):
            w["px"] = x
            x += widths[i] + (gaps[i] if i < 2 else 0)
    line(7, 8, 9, 8)
    line(10, 11, 13, 13)
    ani_v5.write_bin(out_dir / RESULTS_FILE, res)


# Studiopolis' TV van (TVVan, "exit TV"): the player comes out of the TV as a ball spinning toward the screen ("TV
# Sonic" / "TV Tails" / "TV Knux"). The package's copy: its host's animation shows the extra's own spin ball (its Jump frames
# in turn, centred as the game's), with the game's frame counts and timings.
TV_VAN_FILE = "TVVan.bin"
TV_VAN_ANIMS = ("TV Sonic", "TV Tails", "TV Knux")


def build_tv_van(player, balls, host, out_dir):
    src = MANIA / "SPZ1" / TV_VAN_FILE
    if not src.exists():
        sys.exit(f"{src} is missing (rsdk5_extract.py ... Data/Sprites/SPZ1/TVVan.bin)")
    tv = ani_v5.read_bin(src)
    base = len(tv["sheets"])
    tv["sheets"] += player["sheets"]
    for a in tv["anims"]:
        if a["name"] == TV_VAN_ANIMS[host]:  # (the host's only: a vanilla player 2 keeps its own)
            for k, f in enumerate(a["frames"]):
                b = balls[k % len(balls)]
                f.update(sheet=b["sheet"] + base, x=b["x"], y=b["y"], w=b["w"], h=b["h"], px=-(b["w"] // 2), py=-(b["h"] // 2))
    ani_v5.write_bin(out_dir / TV_VAN_FILE, tv)


# Chemical Plant 1's intro (CPZ1Intro_Cutscene_PlayerChemicalReact): player 1 is set to Players/CutsceneCPZ.bin's
# animation for its character (Sonic 0, Tails 1, Knuckles 2: the extra is hosted on one of them) and the step ends when
# that animation reaches its last frame (Sonic's: timer 30 on it). The package's copy keeps every one of those
# animations' frame counts, timings and boxes, so the cutscene runs exactly as it does, and shows the extra doing what
# Mania's own fallback does (pre-Plus Tails, and player 2): its Look Up, played as Player_State_LookUp plays it (from
# frame 0 at the animation's speed) and held on frame 5. ManiaHud.h points CPZ1Intro->playerFrames at it.
CUTSCENE_CPZ_FILE = "CutsceneCPZ.bin"
CUTSCENE_CPZ_HOSTS = ("Sonic", "Tails", "Knux")
LOOK_UP_HOLD = 5  # (Player_State_LookUp: speed 0 once frameID is 5)


def build_cutscene_cpz(player, out_dir):
    cut = ani_v5.read_bin(MANIA / "Players" / CUTSCENE_CPZ_FILE)
    look = next((a for a in player["anims"] if a["name"] == "Look Up" and len(a["frames"]) > LOOK_UP_HOLD), None)
    if look is None:
        (out_dir / CUTSCENE_CPZ_FILE).unlink(missing_ok=True)
        return "no Look Up: left the game's"
    base = len(cut["sheets"])
    cut["sheets"] += player["sheets"]
    # the Look Up frame shown at each game frame (the engine adds the speed to the timer each frame and moves on once it
    # passes the frame's duration)
    shown, k, timer = [], 0, 0
    speed = max(1, look["speed"])
    for _ in range(4096):
        shown.append(k)
        timer += speed
        while k < LOOK_UP_HOLD and timer > look["frames"][k]["duration"]:  # (RSDK ProcessAnimation)
            timer -= look["frames"][k]["duration"]
            k += 1
    for a in cut["anims"]:
        if a["name"] not in CUTSCENE_CPZ_HOSTS:
            continue
        t = 0
        for f in a["frames"]:
            src = look["frames"][shown[min(t, len(shown) - 1)]]
            f.update(sheet=src["sheet"] + base, x=src["x"], y=src["y"], w=src["w"], h=src["h"], px=src["px"], py=src["py"])
            t += max(0, f["duration"]) // max(1, a["speed"])
    ani_v5.write_bin(out_dir / CUTSCENE_CPZ_FILE, cut)
    return "its Look Up"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--build":
        import build_mania_art as mania
        for folder in sys.argv[2:]:
            ex = mania.extra_of(folder)
            print(f"{folder}:")
            build(ex, mania.PACKAGES / folder, mania.mania_palette(ex))
        sys.exit(0)
    g = glyphs()
    if len(sys.argv) > 2:
        preview([to_img(word(t, g)) for t in sys.argv[2:]], sys.argv[1], 3)
    else:
        preview([g[c] for c in sorted(g)], sys.argv[1])
