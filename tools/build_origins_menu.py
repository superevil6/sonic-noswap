#!/usr/bin/env python3
"""Build Origins' character select archives with generic card slots (docs/plan-b-modular-characters.md, phase B).

Writes, from the game's own files:
- mods/NoSwap/raw/ui/ui_gamestage.pac (the popup shown over the classic games' title screens loads this one's scene)
  and ui_mainmenu.pac (the main menu's copy of the same scene), each with origins_cards.SLOTS card slots:
  - pictures: SLOTS cells (origins_cards.CELL_W x CELL_H) appended below menu_main_menu_chara_select_chara_sonic.dds
    (BC7, in the archive's dependency block), a crop for each;
  - in the scene menu_main_menu_chara_select.swif, layer ref_btn (the card template every obj_btn_<i> instances): ONE
    generic picture group null_char_noswap holding an image cast chara_noswap with one crop reference per slot, and per
    slot s two animations, origins_cards.pattern(s, 1 / 2): hide the game's seven groups (null_char_1..7), show the
    generic group, set its crop index to s's cell (CropIndex0), and show the second name line or not
    (sysf_btn_name_2). The game's PRM_chara_1..7 also hide the generic group. This is one group and 2 x SLOTS short
    animations, where a group per card would need a hide track per group in every animation (N^2).
- in ui_mainmenu.pac, the main menu's CONTINUE bubble heads (origins_cards.HEAD_*): SLOTS cells (HEAD_W x HEAD_H) below
  the game's four heads in menu_main_menu_icon_chara_s.dds (the same block as the card texture), and in each
  mods/NoSwap/raw/ui/ui_mainmenu_<language>.pac the scene menu_main_menu_island.swif with that texture's crops: the
  game's four rescaled to the taller texture (same pixels), then one per head cell (HEAD_FIRST_CROP + slot - 1), each
  a crop reference of both head casts pattern_chara_1 / _2. The DLL sets that crop for an extra's bubble
  (Hook_IconChara) and writes each package's head (origins_cards.HEAD_PICTURE) into its slot's cell like the cards.
  - in the same scene, layer lay (the popup window), ONE new text box origins_cards.CREDIT_CAST for the highlighted
    card's sprite credit (edit_credit): a copy of the zone-name text sysf_save_stage (its colour) with the card names'
    smaller font style (Font_2_24, centred, compressed to fit), CREDIT_BOX, centred under the zone-name bar, after the
    window's last child. It has no text of its own: the DLL (Hook_UpdateSaveInfo) sets its text key to the highlighted
    card's credit key, or "" (nothing shown) for the game's own characters, so without the DLL it stays empty.
  - in the same main menu scene, layer lay: the SONIC MANIA button's two layout patterns (edit_launcher,
    LAUNCHER_LAYOUT; played by Mania Lock-On's DLL, native/lockon/src/Launcher.h), and in every text archive below its
    three text keys (LAUNCHER_TEXT). They do nothing without Lock-On; with it, these archives are the ones it uses
    (tools/build_lockon_menu.py makes its own copies of only these edits for when NoSwap isn't installed).
- mods/NoSwap/raw/text/text_menu_<language>.pac: two name keys per slot (origins_cards.name_key), each with room for
  origins_cards.NAME_UNITS UTF-16 units, and a credit key per slot (origins_cards.credit_key, CREDIT_UNITS units) (text
  and length rewritten in place).
- mods/NoSwap/raw/ui/noswap_cards.json (origins_cards.DESCRIPTOR): for each archive, its size, the literal LZ4 runs
  (stream offset, file offset, length) of the chunks the DLL may overwrite, and where each slot's cell rows / name texts
  and lengths are. The chunks holding cells and names are LZ4 blocks of literals only (origins_cards.lz4_literal).

The archives ship with the first 21 characters' cards written in (slot s = kind 6 + s, from their packages'
origins_cards.PICTURE and names: the same step the DLL does at startup, origins_cards.apply), so without the DLL's
runtime copies (or if writing them fails) the select looks as it did before phase B. Build the packages first
(tools/build_packages.py writes each package's card picture).

How the card works (from the game's data): PRM_chara_<kind+1> only switches the Display of the groups null_char_1..7
(+ sysf_btn_name_2); the sprite frames of each group are keyed by the shared state animations (in, loop, over, press,
...), which never key the generic group, so the group's Display and crop index stay as its pattern set them.

Formats: origins_pacx.py (archive, pointer relocation, literal chunks), surfride.py (.swif), bc7.py (exact solid-block
BC7), cnvrs_text.py (text). Everything else in the archives is copied unchanged (unchanged 64 KB chunks byte for byte).

Usage: build_origins_menu.py [--preview DIR]
"""
import argparse
import io
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import bc7  # noqa: E402
import cnvrs_text  # noqa: E402
import origins_cards as oc  # noqa: E402
import origins_pac  # noqa: E402
import origins_pacx as pacx  # noqa: E402
import surfride  # noqa: E402
from extras import EXTRAS, player_ani, player_sheet_path, ui_manifest  # noqa: E402
from noswap_common import gameconfig_palette  # noqa: E402

GAME = Path(os.environ.get("ORIGINS_GAME", str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins"))
RAW_IN = GAME / "image" / "x64" / "raw"
MOD = REPO / "mods" / "NoSwap"
PACKAGES = MOD / "characters"
GAMECONFIG = REPO / "extracted" / "Sonic1" / "Data" / "Game" / "GameConfig.bin"
LEGACY = 21  # the first 21 characters (Roster.h LEGACY_KEYS): kinds 7-27, shipped written in at slots 1-21

SCENE = "menu_main_menu_chara_select"
HOST = "menu_main_menu_chara_select_chara_sonic"  # the texture that gets the new rows
LAYER = "ref_btn"
TEMPLATE_NULL = "null_char_1"  # Sonic's group and image cast: the new ones copy their settings
TEMPLATE_IMAGE = "sonic_1"
GROUP, IMAGE_CAST = "null_char_noswap", "chara_noswap"
NAME_LINE_2 = "sysf_btn_name_2"
# The main menu's CONTINUE bubble heads (origins_cards.HEAD_*): the texture in ui_mainmenu.pac, the scene in each
# ui_mainmenu_<language>.pac
HEAD_HOST = "menu_main_menu_icon_chara_s"
HEAD_SCENE = "menu_main_menu_island"
HEAD_CASTS = ("pattern_chara_1", "pattern_chara_2")
HEAD_ARCHIVE = "raw/ui/ui_mainmenu.pac"
# The SONIC MANIA button (Mania Lock-On's native/lockon/src/Launcher.h; tools/build_lockon_menu.py reuses
# edit_launcher / check_launcher for Lock-On's own archives): the DLL puts it in the Museum / My Data / Options / DLC island's
# empty 4th button (obj_btn_l_4, inside lay_btn_l_4) and, after the game's own PRM_btn_museum, plays one of these two
# layout patterns on the island scene's layer "lay" (edit_launcher; constant keys at frame 0, like the game's PRM_btn_*):
# - LAUNCHER_PATTERN when the DLC button is hidden (Origins Plus owned): the 4th button shown under OPTIONS, spaced
#   like the Mission island's (a big button, then a small one: the Mania button is a small PRM_sub one).
# - LAUNCHER_PATTERN_DLC when the DLC button shows (no Plus): the column tightened and the DLC button moved down so the
#   4th button fits between OPTIONS and DLC. y is up; the button layers sit 10 px lower (their parent null_btn_l), the
#   DLC button's don't. Heights from the textures' opaque areas: a big button's plate 100 (the Museum one 166 with its
#   progress bar under it), a small one's 68, the DLC plate 104 with Amy and Knuckles 88 above its centre; the
#   description bar starts at y -396.
# Without the DLL (or with the launcher off / the decomp not found) neither is played: the island is the game's.
LAUNCHER_LAYER = "lay"
LAUNCHER_PATTERN, LAUNCHER_PATTERN_DLC = "PRM_btn_museum_mania", "PRM_btn_museum_mania_dlc"
LAUNCHER_LAYOUT = {  # pattern -> {cast: [(curve, value)]}
    LAUNCHER_PATTERN: {"lay_btn_l_1": [("Ty", 141.0)], "lay_btn_l_2": [("Ty", -22.0)], "lay_btn_l_3": [("Ty", -135.0)],
                       "lay_btn_l_4": [("Ty", -248.0), ("Display", 1)], "lay_btn_dlc": [("Ty", -268.0)]},
    LAUNCHER_PATTERN_DLC: {"lay_btn_l_1": [("Ty", 156.0)], "lay_btn_l_2": [("Ty", 12.0)], "lay_btn_l_3": [("Ty", -98.0)],
                           "lay_btn_l_4": [("Ty", -195.0), ("Display", 1)], "lay_btn_dlc": [("Ty", -318.0)]},
}
LAUNCHER_TEMPLATE = "PRM_btn_museum"  # (the new patterns copy its animation header)
# Its text keys, in every language's text_menu_<language>.pac (English everywhere for now). The description key is
# "MAINMENU_text_" + the island's unused description slot, which the DLL points at "mania" (or "mania_missing").
LAUNCHER_TEXT = {
    "MAINMENU_island_mania": "SONIC MANIA",
    "MAINMENU_text_mania": "Play Sonic Mania (decompilation) with NoSwap's characters",
    "MAINMENU_text_mania_missing": "Sonic Mania decompilation not found (see NoSwapS3K.ini [Mania])",
}
# The credit text box (edit_credit): in layer "lay", a child of the window group, after its last child
CREDIT_LAYER, CREDIT_PARENT = "lay", "null_window_all"
CREDIT_COPY = "sysf_save_stage"  # the zone-name text: node, image data and cell (its dark blue) copied
CREDIT_STYLE = "sysf_btn_name_1"  # the card name: its user data (FONT_STYLE Font_2_24, centred, compressed to fit)
# Centre and size in the popup's coordinates (y up; 1920x1080 scene centred on 0, 0). The zone-name bar (null_save_stage
# at -369, -187: its plate x -338..412, y -217..-157, its text centred on x 41) sits under the cards; the window's white
# panel ends at y -310 (SIZE_REF_* 620 px high, centred). The box is centred on the zone text's x, 33 px under the bar.
CREDIT_POS = (41.0, -250.0)
CREDIT_BOX = (700.0, 34.0)
DISPLAY, CROP_INDEX0 = 10, 17  # track curve types
TRACK_BOOL, TRACK_INT = 0x30, 0x20  # track flags: bool / int value, constant (as the game's)
DDS_HEADER = 148


# ---------------------------------------------------------------- art
def extra_frame(e, anim="Stopped", frame=0):
    """(RGBA array, frame dict) of an extra's Sonic 1 frame, in its true colours (index 0 transparent)."""
    ani = player_ani(e, "Sonic1u")  # (kept with its art: its package ships it as extras.PLAYER_ANI)
    a = next(x for x in ani["anims"] if x["name"] == anim)
    f = a["frames"][frame]
    sheet = Image.open(player_sheet_path(e, "Sonic1u", ani["sheets"][f["sheet"]]))
    assert sheet.mode == "P", f"{ani['sheets'][f['sheet']]}: expected an indexed sheet"
    idx = np.array(sheet)[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]]
    pal = {i: c for i, c in enumerate(gameconfig_palette(GAMECONFIG))}
    pal.update({i: ((c >> 16) & 255, (c >> 8) & 255, c & 255) for i, c in e["palette"].items()})
    used = set(np.unique(idx).tolist()) - {0}
    missing = sorted(used - set(pal))
    assert not missing, f"{e['file']}: palette indices {missing} have no colour"
    lut = np.zeros((256, 4), np.uint8)
    for i, c in pal.items():
        lut[i] = (*c, 255)
    lut[0] = 0
    return lut[idx], f


def icon_background(idx, pal, neck=False):
    """(mask of pixels to drop, notes) for a life icon drawn in a HUD box, so its head stands alone in the menu bubble:
    - the box's 1 px frame lines: top and bottom rows each one colour, the same (and the side columns, if they are too);
    - the box's fill: flood-filled (4-connected) from the icon's edges through pixels of the fill colour, so the same
      colour inside the head (eye whites, gloves, muzzles) stays. The fill colour: the edges' commonest colour when
      it is at least half of them, else, in a framed box, the colour of most of its corners.
    Colours are compared as RGB (two palette slots can hold the same colour). Nothing is recoloured: pixels are only
    left out.
    neck: the box's bottom edge cuts through the head (its neck / muzzle), so a run of the fill colour on the bottom
    edge with head pixels on both sides is the head's own colour (e.g. Blaze's white muzzle and eye whites, the same
    white as her box), not a way in for the flood (Mania's save select portraits: tools/build_mania_art.py)."""
    from collections import deque
    key = np.array([[-1 if v == 0 else pal[int(v)][0] << 16 | pal[int(v)][1] << 8 | pal[int(v)][2] for v in row]
                    for row in idx])
    gone, notes = np.zeros(idx.shape, bool), []
    if len(set(key[0])) == 1 and len(set(key[-1])) == 1 and key[0, 0] == key[-1, 0] != -1:
        gone[0] = gone[-1] = True
        notes.append("frame rows")
        if len(set(key[1:-1, 0])) == 1 and len(set(key[1:-1, -1])) == 1 and key[1, 0] == key[1, -1] == key[0, 0]:
            gone[:, 0] = gone[:, -1] = True
            notes.append("frame columns")
    ys, xs = np.nonzero(~gone)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    edge = [(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if y in (y0, y1) or x in (x0, x1)]
    v, c = np.unique([key[q] for q in edge], return_counts=True)
    bg = v[c.argmax()]
    fill = bg != -1 and c.max() * 2 >= len(edge)
    if notes and not fill:
        cv, cc = np.unique([key[q] for q in ((y0, x0), (y0, x1), (y1, x0), (y1, x1))], return_counts=True)
        bg = cv[cc.argmax()]
        fill = bg != -1 and cc.max() >= 2
    if fill:
        seeds = [q for q in edge if key[q] == bg]
        if neck:
            row = [key[y1, x] if not gone[y1, x] else bg for x in range(x0, x1 + 1)]
            inner, x = set(), 0
            while x < len(row):
                if row[x] != bg:
                    x += 1
                    continue
                end = x
                while end < len(row) and row[end] == bg:
                    end += 1
                if x > 0 and end < len(row):  # (head pixels on both sides)
                    inner.update((y1, x0 + i) for i in range(x, end))
                x = end
            seeds = [q for q in seeds if q not in inner or q[1] in (x0, x1)]
            if inner:
                notes.append(f"neck {len(inner)} px")
        todo = deque(seeds)
        seen = set(todo)
        while todo:
            y, x = todo.popleft()
            gone[y, x] = True
            for n in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if y0 <= n[0] <= y1 and x0 <= n[1] <= x1 and n not in seen and key[n] == bg:
                    seen.add(n)
                    todo.append(n)
        notes.append(f"background #{bg:06x}")
    return gone, notes


def head_picture(e):
    """The extra's CONTINUE bubble head file (origins_cards.HEAD_PICTURE): its 16x16 life icon (its UI manifest's
    "life_icon", Sonic 1 colours as its card: GameConfig palette and its own, index 0 transparent) without its HUD
    box's frame and fill (icon_background), enlarged origins_cards.HEAD_SCALE times. Only the menu head: the HUD keeps
    its box."""
    manifest = ui_manifest(e, "ui")
    x, y, w, h = manifest["frames"]["life_icon"]
    sheet = Image.open(manifest["sheet"])
    assert sheet.mode == "P", f"{manifest['sheet']}: expected an indexed sheet"
    idx = np.array(sheet)[y:y + h, x:x + w]
    pal = {i: c for i, c in enumerate(gameconfig_palette(GAMECONFIG))}
    pal.update({i: ((c >> 16) & 255, (c >> 8) & 255, c & 255) for i, c in e["palette"].items()})
    missing = sorted(set(np.unique(idx).tolist()) - {0} - set(pal))
    assert not missing, f"{e['file']}: life icon palette indices {missing} have no colour"
    lut = np.zeros((256, 4), np.uint8)
    for i, c in pal.items():
        lut[i] = (*c, 255)
    lut[0] = 0
    rgba = lut[idx]
    rgba[icon_background(idx, pal, neck=True)[0]] = 0  # (neck: a head whose white runs to the box edge keeps it: Blaze, 2026-09-29)
    return oc.head_dds(rgba)


def card_picture(e):
    """The extra's card picture file (origins_cards.PICTURE): its Sonic 1 "Stopped" frame 0, 8x (build_packages.py), or
    its own picture (extras.py "card": a crop of a sheet, enlarged `scale` times)."""
    if e.get("card") and "rect" not in e["card"]:  # (character.json "card" {"scale": n}: the Stopped frame, n times:
        return oc.card_dds(*extra_frame(e), scale=e["card"]["scale"])  # a tall character's 8x is taller than the cell)
    if e.get("card"):
        return own_card(e["card"])
    return oc.card_dds(*extra_frame(e))


def own_card(card):
    """extras.py "card" {"sheet", "rect" [x, y, w, h], "scale", "background"}: the crop as-is, its background colour
    transparent, enlarged `scale` times (nearest: pixel-exact), centred in a CELL_W-wide picture on 4x4 blocks, its bottom
    BASELINE px above the picture's bottom, like the others. The BC7 encoder takes solid 4x4 blocks only, so the scale
    must be a multiple of 4 (8x, the other cards', is too tall for a 96-px drawing: 768 > CELL_H).
    Optional: "pivot" (x in the crop): that column on the cell's centre line, as the other cards place their frame's
    pivot, and whatever runs past the cell's sides cut off at its edges (as Tails' tails on his card: Big's tail);
    "baseline": his feet that many px above the bottom instead of BASELINE (a drawing a little too tall for the cell)."""
    scale = card["scale"]
    if scale % 4:
        raise SystemExit(f"card {card['sheet']}: scale {scale} isn't a multiple of 4 (BC7 solid blocks)")
    x, y, w, h = card["rect"]
    rgb = np.array(Image.open(card["sheet"]).convert("RGB"))[y:y + h, x:x + w]
    bg = tuple(int(card["background"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    rgba = np.dstack([rgb, np.where((rgb == bg).all(axis=2), 0, 255).astype(np.uint8)])
    rgba[rgba[..., 3] == 0] = 0
    big = rgba.repeat(scale, 0).repeat(scale, 1)
    if "pivot" in card or "baseline" in card:
        baseline = card.get("baseline", oc.BASELINE)
        pic_h = big.shape[0] + baseline
        pic_h += -pic_h % 4
        left = oc.CELL_W // 2 - card.get("pivot", w // 2) * scale  # (a multiple of 4: scale is)
        if pic_h > oc.CELL_H:
            raise SystemExit(f"card {card['sheet']}: {pic_h} px high doesn't fit a {oc.CELL_H}-px cell")
        pic = np.zeros((pic_h, oc.CELL_W, 4), np.uint8)
        top = pic_h - baseline - big.shape[0]
        a, b = max(0, -left), min(big.shape[1], oc.CELL_W - left)  # (the columns inside the cell)
        pic[top:top + big.shape[0], left + a:left + b] = big[:, a:b]
        return oc.dds_bc7(oc.CELL_W, pic_h, bc7.encode_image(pic))
    pic_h = big.shape[0] + oc.BASELINE
    pic_h += -pic_h % 4
    left = (oc.CELL_W - big.shape[1]) // 2 // 4 * 4
    if big.shape[1] > oc.CELL_W or pic_h > oc.CELL_H:
        raise SystemExit(f"card {card['sheet']}: {big.shape[1]}x{pic_h} doesn't fit a {oc.CELL_W}x{oc.CELL_H} cell")
    pic = np.zeros((pic_h, oc.CELL_W, 4), np.uint8)
    top = pic_h - oc.BASELINE - big.shape[0]
    pic[top:top + big.shape[0], left:left + big.shape[1]] = big
    return oc.dds_bc7(oc.CELL_W, pic_h, bc7.encode_image(pic))


# ---------------------------------------------------------------- .swif edits
def _layer(parsed, name):
    return next(l for l in parsed["all_layers"].values() if l["name"] == name)


def _all_ids(parsed):
    ids = set()
    for l in parsed["all_layers"].values():
        ids.add(l["id"])
        ids |= {c["id"] for c in l["casts"]} | {a["id"] for a in l["anims"]}
    for tl in parsed["project"]["texlists"]:
        ids |= {t["id"] for t in tl["textures"]}
    for sc in parsed["project"]["scenes"]:
        ids.add(sc["id"])
    return ids


NODE, CELL, IMAGE, ANIM, MOTION = 0x28, 0x40, 0x58, 0x30, 0x10


def edit_swif(swif, host_old_h, host_new_h, new_cells):
    """new_cells: [(x, y, w, h)] in DDS pixels of the host texture, one per slot (slot s = new_cells[s - 1])."""
    P = surfride.check(swif)
    ed = surfride.Editor(swif)
    b = ed.b

    # -- crops of the host texture: old ones rescaled to the taller texture, then the new cells
    tl = P["project"]["texlists"][0]
    tex_index, tex = next((i, t) for i, t in enumerate(tl["textures"]) if t["file"] == HOST)
    tex_w = tex["w"] * 2  # the .swif declares half the DDS size
    crops = [(l, t * host_old_h / host_new_h, r, bt * host_old_h / host_new_h) for l, t, r, bt in tex["crops"]]
    first_new_crop = len(crops)
    crops += [(x / tex_w, y / host_new_h, (x + w) / tex_w, (y + h) / host_new_h) for x, y, w, h in new_cells]
    crop_at = ed.alloc(b"".join(struct.pack("<4f", *c) for c in crops))
    ed.pack("<HH", tex["at"] + 0x14, tex["w"], host_new_h // 2)
    ed.pack("<I", tex["at"] + 0x1C, len(crops))
    ed.set_ptr(tex["at"] + 0x20, crop_at)

    # -- casts: the generic group and its image cast, after the game's last group
    L = _layer(P, LAYER)
    casts = L["casts"]
    by_name = {c["name"]: i for i, c in enumerate(casts)}
    assert GROUP not in by_name, "the scene already has NoSwap's group"
    t_null, t_img = casts[by_name[TEMPLATE_NULL]], casts[by_name[TEMPLATE_IMAGE]]
    last_group = max((i for i, c in enumerate(casts) if c["name"].startswith("null_char_") and c["sibling"] == -1),
                     key=lambda i: int(casts[i]["name"][10:]))
    next_id = max(_all_ids(P)) + 1
    n_old = len(casts)
    i_null, i_img = n_old, n_old + 1
    null_id, img_id = next_id, next_id + 1
    next_id += 2

    nodes = bytearray(b[L["nodes_at"]:L["nodes_at"] + NODE * n_old])
    cells = bytearray(b[L["cells_at"]:L["cells_at"] + CELL * n_old])
    # image cast data: Sonic's, with the cell's size and one crop reference per slot (crop index 0 = slot 1)
    cast = ed.alloc(bytes(b[t_img["image"]["at"]:t_img["image"]["at"] + IMAGE]))
    ed.pack("<4f", cast + 4, oc.CELL_W / 2, oc.CELL_H / 2, oc.CELL_W / 4, oc.CELL_H / 4)  # size, pivot (centre)
    ed.pack("<hhhh", cast + 0x24, 0, -1, len(new_cells), 0)  # crop 0, no crop 1, SLOTS crop refs, 0 crop-1 refs
    refs = ed.alloc(b"".join(struct.pack("<HHH", 0, tex_index, first_new_crop + j) for j in range(len(new_cells))), 8)
    for f, v in ((0x30, refs), (0x38, 0), (0x40, 0), (0x48, 0), (0x50, 0)):
        ed.set_ptr(cast + f, v)
    for i, name, cid, data, child, template in ((i_null, GROUP, null_id, 0, i_img, t_null),
                                                (i_img, IMAGE_CAST, img_id, cast, -1, t_img)):
        nodes += b[template["at"]:template["at"] + NODE]
        cells += b[L["cells_at"] + CELL * by_name[template["name"]]:][:CELL]
        nat = NODE * i
        struct.pack_into("<IxxxxQhh", nodes, nat + 8, cid, data, child, -1)
        struct.pack_into("<I", nodes, nat + 0xC, template["flags"])
        struct.pack_into("<Q", nodes, nat + 0x20, 0)
        struct.pack_into("<Q", nodes, nat, ed.string(name))
    struct.pack_into("<h", nodes, NODE * last_group + 0x1A, i_null)  # (a sibling of the game's last group)
    # the picture's bottom stays where Sonic's is: a taller cell moves its centre up (y is up)
    ty = struct.unpack_from("<f", cells, CELL * i_img + 0x14)[0]
    struct.pack_into("<f", cells, CELL * i_img + 0x14, ty + (oc.CELL_H / 2 - oc.CELL_W / 2) / 2)
    nodes_at = ed.alloc(bytes(nodes))
    for i in range(len(nodes) // NODE):
        for f in (0, 0x10, 0x20):
            v = struct.unpack_from("<Q", ed.b, nodes_at + NODE * i + f)[0]
            ed.set_ptr(nodes_at + NODE * i + f, v)
    cells_at = ed.alloc(bytes(cells))

    # -- animations
    def track(kind, flags, value):
        key = ed.alloc(struct.pack("<iB3x" if kind == DISPLAY else "<ii", 0, value), 8)
        t = ed.alloc(struct.pack("<HhIIIQ", kind, 1, flags, 0, 0, 0), 8)
        ed.set_ptr(t + 0x10, key)
        return t

    def motions(entries):
        """entries: [(cast id, curve type, flags, value)], one track per cast -> pointer to a new motion array"""
        tracks = [track(k, f, v) for _, k, f, v in entries]
        at = ed.alloc(bytes(MOTION * len(entries)))
        for m, ((cid, *_), t) in enumerate(zip(entries, tracks)):
            ed.pack("<Hh4x", at + MOTION * m, cid, 1)
            ed.set_ptr(at + MOTION * m + 8, t)
        return at

    anims = L["anims"]
    groups = {c["name"]: c["id"] for c in casts if c["name"].startswith("null_char_")}
    old_groups = [groups[f"null_char_{g}"] for g in range(1, 8)]
    line2 = casts[by_name[NAME_LINE_2]]["id"]
    new = [(s, lines) for s in range(1, len(new_cells) + 1) for lines in (1, 2)]
    anim_at = ed.alloc(b"".join(b[a["at"]:a["at"] + ANIM] for a in anims) + bytes(ANIM * len(new)))
    for m, a in enumerate(anims):
        at = anim_at + ANIM * m
        for f in (0, 0x18, 0x20):
            ed.set_ptr(at + f, struct.unpack_from("<Q", ed.b, at + f)[0])
        if a["name"].startswith("PRM_chara_"):  # the game's picture animations: also hide the generic group
            n = len(a["motions"])
            arr = ed.alloc(bytes(b[a["motions_at"]:a["motions_at"] + MOTION * n]) + bytes(MOTION))
            for q in range(n):
                ed.set_ptr(arr + MOTION * q + 8, struct.unpack_from("<Q", ed.b, arr + MOTION * q + 8)[0])
            ed.pack("<Hh4x", arr + MOTION * n, null_id, 1)
            ed.set_ptr(arr + MOTION * n + 8, track(DISPLAY, TRACK_BOOL, 0))
            ed.pack("<i", at + 0xC, n + 1)
            ed.set_ptr(at + 0x18, arr)
    template_anim = next(a for a in anims if a["name"] == "PRM_chara_1")
    for j, (s, lines) in enumerate(new):
        at = anim_at + ANIM * (len(anims) + j)
        ed.b[at:at + ANIM] = b[template_anim["at"]:template_anim["at"] + ANIM]
        entries = [(g, DISPLAY, TRACK_BOOL, 0) for g in old_groups]
        entries += [(null_id, DISPLAY, TRACK_BOOL, 1), (img_id, CROP_INDEX0, TRACK_INT, s - 1),
                    (line2, DISPLAY, TRACK_BOOL, int(lines == 2))]
        ed.set_ptr(at, ed.string(oc.pattern(s, lines)))
        ed.pack("<Ii", at + 8, next_id, len(entries))
        next_id += 1
        ed.set_ptr(at + 0x18, motions(entries))
        ed.set_ptr(at + 0x20, 0)

    # -- the layer
    ed.pack("<I", L["at"] + 0x10, len(nodes) // NODE)
    ed.set_ptr(L["at"] + 0x18, nodes_at)
    ed.set_ptr(L["at"] + 0x20, cells_at)
    ed.pack("<I", L["at"] + 0x28, len(anims) + len(new))
    ed.set_ptr(L["at"] + 0x30, anim_at)
    out = ed.build()
    surfride.check(out)
    return out


def edit_credit(swif):
    """The select scene with the credit text box origins_cards.CREDIT_CAST added to layer CREDIT_LAYER (see the module
    docstring): a new node (a copy of CREDIT_COPY's, with CREDIT_STYLE's user data), its own image data (CREDIT_COPY's,
    CREDIT_BOX in size, pivot in the middle) and cell (CREDIT_COPY's colour, at CREDIT_POS), the new last sibling of
    CREDIT_PARENT's children. No animation keys it: it's shown with the window (the window group's fades)."""
    P = surfride.check(swif)
    ed = surfride.Editor(swif)
    b = ed.b
    L = _layer(P, CREDIT_LAYER)
    casts = L["casts"]
    by_name = {c["name"]: i for i, c in enumerate(casts)}
    assert oc.CREDIT_CAST not in by_name, "the scene already has NoSwap's credit box"
    style = next((c for l in P["all_layers"].values() for c in l["casts"] if c["name"] == CREDIT_STYLE), None)
    copy = casts[by_name[CREDIT_COPY]]
    assert style and copy["type"] == "image" and style["type"] == "image"
    parent = by_name[CREDIT_PARENT]
    last = casts[parent]["child"]
    assert last != -1
    while casts[last]["sibling"] != -1:
        last = casts[last]["sibling"]
    n_old = len(casts)
    new_id = max(_all_ids(P)) + 1
    nodes = bytearray(b[L["nodes_at"]:L["nodes_at"] + NODE * n_old])
    cells = bytearray(b[L["cells_at"]:L["cells_at"] + CELL * n_old])
    # image data: the zone text's, a smaller box, pivot in the middle; its pointers (crop refs) as they are
    img = ed.alloc(bytes(b[copy["image"]["at"]:copy["image"]["at"] + IMAGE]))
    ed.pack("<4f", img + 4, *CREDIT_BOX, CREDIT_BOX[0] / 2, CREDIT_BOX[1] / 2)
    for f in (0x30, 0x38, 0x40, 0x48, 0x50):
        ed.set_ptr(img + f, struct.unpack_from("<Q", ed.b, img + f)[0])
    node = bytearray(b[copy["at"]:copy["at"] + NODE])
    struct.pack_into("<I", node, 8, new_id)
    struct.pack_into("<Q", node, 0x10, img)
    struct.pack_into("<hh", node, 0x18, -1, -1)
    struct.pack_into("<Q", node, 0x20, struct.unpack_from("<Q", b, style["at"] + 0x20)[0])  # (the name's user data)
    struct.pack_into("<Q", node, 0, ed.string(oc.CREDIT_CAST))
    nodes += node
    struct.pack_into("<h", nodes, NODE * last + 0x1A, n_old)
    cell = bytearray(b[L["cells_at"] + CELL * by_name[CREDIT_COPY]:][:CELL])
    struct.pack_into("<ff", cell, 0x10, *CREDIT_POS)
    cells += cell
    nodes_at = ed.alloc(bytes(nodes))
    for i in range(n_old + 1):
        for f in (0, 0x10, 0x20):
            ed.set_ptr(nodes_at + NODE * i + f, struct.unpack_from("<Q", ed.b, nodes_at + NODE * i + f)[0])
    cells_at = ed.alloc(bytes(cells))
    ed.pack("<I", L["at"] + 0x10, n_old + 1)
    ed.set_ptr(L["at"] + 0x18, nodes_at)
    ed.set_ptr(L["at"] + 0x20, cells_at)
    out = ed.build()
    surfride.check(out)
    return out


def edit_island(swif, old_h, new_h, head_cells):
    """The main menu scene with the CONTINUE bubble's head texture HEAD_HOST grown from old_h to new_h DDS pixels high:
    its crops rescaled in place (the game's heads show the same pixels), a crop per head cell after them
    (origins_cards.HEAD_FIRST_CROP + slot - 1), and both head casts (HEAD_CASTS) given a crop reference per crop."""
    P = surfride.check(swif)
    ed = surfride.Editor(swif)
    hits = [(tli, ti, t) for tli, tl in enumerate(P["project"]["texlists"]) for ti, t in enumerate(tl["textures"])
            if t["file"] == HEAD_HOST]
    assert len(hits) == 1, f"{HEAD_SCENE}: {len(hits)} textures {HEAD_HOST}"
    tli, ti, tex = hits[0]
    assert tex["h"] * 2 == old_h and len(tex["crops"]) == oc.HEAD_FIRST_CROP, (tex["h"], tex["crops"])
    tex_w = tex["w"] * 2
    old = [(l, t * old_h / new_h, r, b * old_h / new_h) for l, t, r, b in tex["crops"]]
    for j, c in enumerate(old):  # (the old array, in place: unused after, but the same numbers)
        ed.pack("<4f", tex["crops_at"] + 16 * j, *c)
    crops = old + [(x / tex_w, y / new_h, (x + w) / tex_w, (y + h) / new_h) for x, y, w, h in head_cells]
    crop_at = ed.alloc(b"".join(struct.pack("<4f", *c) for c in crops))
    ed.pack("<HH", tex["at"] + 0x14, tex["w"], new_h // 2)
    ed.pack("<I", tex["at"] + 0x1C, len(crops))
    ed.set_ptr(tex["at"] + 0x20, crop_at)
    found = set()
    for L in P["all_layers"].values():
        for c in L["casts"]:
            if c["name"] not in HEAD_CASTS or "image" not in c:
                continue
            img = c["image"]
            assert img["cropref0"] == [(tli, ti, j) for j in range(oc.HEAD_FIRST_CROP)], (c["name"], img["cropref0"])
            refs = ed.alloc(b"".join(struct.pack("<HHH", tli, ti, j) for j in range(len(crops))), 8)
            ed.pack("<h", img["at"] + 0x28, len(crops))
            ed.set_ptr(img["at"] + 0x30, refs)
            found.add(c["name"])
    assert found == set(HEAD_CASTS), f"{HEAD_SCENE}: head casts found: {sorted(found)}"
    out = ed.build()
    surfride.check(out)
    return out


CURVE_TYPE = {"Ty": 1, "Display": DISPLAY}
TRACK_FLOAT = 0x11  # float value, linear (as the game's Ty keys)


def edit_launcher(swif):
    """The main menu scene with the SONIC MANIA button's two layout patterns (LAUNCHER_LAYOUT) added to layer
    LAUNCHER_LAYER after its animations: each a copy of LAUNCHER_TEMPLATE's header with its own name and id, one motion
    per cast and one constant track (frame 0) per curve. Nothing else changes."""
    P = surfride.check(swif)
    ed = surfride.Editor(swif)
    b = ed.b
    L = _layer(P, LAUNCHER_LAYER)
    ids = {c["name"]: c["id"] for c in L["casts"]}
    anims = L["anims"]
    names = {a["name"] for a in anims}
    assert not names & set(LAUNCHER_LAYOUT), "the scene already has the launcher patterns"
    template = next(a for a in anims if a["name"] == LAUNCHER_TEMPLATE)
    next_id = max(_all_ids(P)) + 1

    def motions(layout):
        """-> pointer to a motion array: per cast, its tracks (contiguous), each one key at frame 0"""
        at = ed.alloc(bytes(MOTION * len(layout)))
        for m, (cast, curves) in enumerate(layout.items()):
            tracks = ed.alloc(bytes(24 * len(curves)), 8)
            for t, (curve, value) in enumerate(curves):
                if curve == "Display":
                    key, flags = ed.alloc(struct.pack("<iB3x", 0, value), 8), TRACK_BOOL
                else:
                    key, flags = ed.alloc(struct.pack("<if", 0, value), 8), TRACK_FLOAT
                ed.pack("<HhIII", tracks + 24 * t, CURVE_TYPE[curve], 1, flags, 0, 0)
                ed.set_ptr(tracks + 24 * t + 16, key)
            ed.pack("<Hh4x", at + MOTION * m, ids[cast], len(curves))
            ed.set_ptr(at + MOTION * m + 8, tracks)
        return at

    anim_at = ed.alloc(b"".join(b[a["at"]:a["at"] + ANIM] for a in anims) + bytes(ANIM * len(LAUNCHER_LAYOUT)))
    for m in range(len(anims)):
        at = anim_at + ANIM * m
        for f in (0, 0x18, 0x20):
            ed.set_ptr(at + f, struct.unpack_from("<Q", ed.b, at + f)[0])
    for j, (name, layout) in enumerate(LAUNCHER_LAYOUT.items()):
        at = anim_at + ANIM * (len(anims) + j)
        ed.b[at:at + ANIM] = b[template["at"]:template["at"] + ANIM]
        ed.set_ptr(at, ed.string(name))
        ed.pack("<Ii", at + 8, next_id, len(layout))
        next_id += 1
        ed.set_ptr(at + 0x18, motions(layout))
        ed.set_ptr(at + 0x20, 0)
    ed.pack("<I", L["at"] + 0x28, len(anims) + len(LAUNCHER_LAYOUT))
    ed.set_ptr(L["at"] + 0x30, anim_at)
    out = ed.build()
    surfride.check(out)
    return out


def check_launcher(P, G):
    """The built scene's layer LAUNCHER_LAYER: the game's animations as they were (by name, end and keys), then the two
    launcher patterns with exactly LAUNCHER_LAYOUT's keys."""
    L, GL = _layer(P, LAUNCHER_LAYER), _layer(G, LAUNCHER_LAYER)
    ids = {c["id"]: c["name"] for c in L["casts"]}
    strip = lambda a: (a["name"], a["end"], [(m["cast"], [(t["type"], t["flags"], t["keys"]) for t in m["tracks"]])
                                            for m in a["motions"]])
    assert [strip(a) for a in L["anims"][:len(GL["anims"])]] == [strip(a) for a in GL["anims"]], "a game animation changed"
    new = L["anims"][len(GL["anims"]):]
    assert [a["name"] for a in new] == list(LAUNCHER_LAYOUT), [a["name"] for a in new]
    for a in new:
        got = {ids[m["cast"]]: [(t["type"], t["keys"][0][1]) for t in m["tracks"]] for m in a["motions"]}
        assert all(len(t["keys"]) == 1 and t["keys"][0][0] == 0 for m in a["motions"] for t in m["tracks"])
        assert got == LAUNCHER_LAYOUT[a["name"]], (a["name"], got)


def build_scene(rel, old_h, new_h, head_cells):
    """A ui_mainmenu_<language>.pac with its main menu scene edited (edit_island, edit_launcher); everything else as
    the game's."""
    outer = pacx.Outer((RAW_IN / rel[len("raw/"):]).read_bytes())
    s = pacx.find(outer.root, HEAD_SCENE, "swif")
    swif = outer.root[s["data"]:s["data"] + s["size"]]
    outer.root = pacx.replace_file(outer.root, HEAD_SCENE, "swif",
                                   edit_launcher(edit_island(swif, old_h, new_h, head_cells)))
    return outer.build()


def verify_scene(data, rel, old_h, new_h, head_cells):
    """Re-read a built language archive: the same blocks as the game's, the scene's head crops (the game's four on the
    same pixels, then one per head cell) and both casts' references."""
    game = pacx.Outer((RAW_IN / rel[len("raw/"):]).read_bytes())
    outer = pacx.Outer(data)
    assert outer.build() == data, f"{rel}: doesn't re-read to itself"
    assert outer.blocks == game.blocks, f"{rel}: a block changed"
    assert [e["name"] for e in pacx.entries(outer.root)] == [e["name"] for e in pacx.entries(game.root)]
    for e in pacx.entries(game.root):
        if e["data"] and not (e["name"] == HEAD_SCENE and e["ext"] == "swif"):
            f = pacx.find(outer.root, e["name"], e["ext"])
            assert outer.root[f["data"]:f["data"] + f["size"]] == game.root[e["data"]:e["data"] + e["size"]], e["name"]
    s = pacx.find(outer.root, HEAD_SCENE, "swif")
    P = surfride.check(outer.root[s["data"]:s["data"] + s["size"]])
    g = pacx.find(game.root, HEAD_SCENE, "swif")
    G = surfride.parse(game.root[g["data"]:g["data"] + g["size"]])
    tex = next(t for tl in P["project"]["texlists"] for t in tl["textures"] if t["file"] == HEAD_HOST)
    gtex = next(t for tl in G["project"]["texlists"] for t in tl["textures"] if t["file"] == HEAD_HOST)
    tex_w = tex["w"] * 2
    assert tex["h"] * 2 == new_h and len(tex["crops"]) == oc.HEAD_FIRST_CROP + oc.SLOTS
    box = lambda c, h: tuple(round(v) for v in (c[0] * tex_w, c[1] * h, c[2] * tex_w, c[3] * h))
    for j, c in enumerate(gtex["crops"]):  # the game's heads: the same pixel boxes
        assert box(tex["crops"][j], new_h) == box(c, old_h), (rel, j, tex["crops"][j], c)
    for j, (x, y, w, h) in enumerate(head_cells):
        assert box(tex["crops"][oc.HEAD_FIRST_CROP + j], new_h) == (x, y, x + w, y + h), (rel, j)
    for L in P["all_layers"].values():
        for c in L["casts"]:
            if c["name"] in HEAD_CASTS:
                refs = c["image"]["cropref0"]
                assert len(refs) == oc.HEAD_FIRST_CROP + oc.SLOTS and [r[2] for r in refs] == list(range(len(refs)))
    check_launcher(P, G)
    return tex["crops"]


# ---------------------------------------------------------------- the picture archives
def block_of(outer, name, ext):
    for bname, blk in outer.blocks.items():
        if any(e["name"] == name and e["ext"] == ext and e["data"] for e in pacx.entries(blk)):
            return bname
    raise KeyError(name)


def build_ui(rel):
    """-> (archive bytes with every slot blank, its descriptor entry, info for the checks)"""
    outer = pacx.Outer((RAW_IN / rel[len("raw/"):]).read_bytes())
    bname = block_of(outer, HOST, "dds")
    blk = outer.blocks[bname]
    e = pacx.find(blk, HOST, "dds")
    dds = blk[e["data"]:e["data"] + e["size"]]
    w, h, _, _ = bc7.dds_info(dds)
    per_row = w // oc.CELL_W
    rows = math.ceil(oc.SLOTS / per_row)
    cells = [((j % per_row) * oc.CELL_W, h + (j // per_row) * oc.CELL_H, oc.CELL_W, oc.CELL_H) for j in range(oc.SLOTS)]
    new_h = h + rows * oc.CELL_H
    blank_rows = oc.blank_block() * ((w // 4) * (rows * oc.CELL_H // 4))
    new_dds = bc7.dds_append_rows(dds, blank_rows, rows * oc.CELL_H)
    outer.blocks[bname] = pacx.replace_file(blk, HOST, "dds", new_dds)
    outer.root = pacx.set_size(outer.root, HOST, "dds", len(new_dds))
    s = pacx.find(outer.root, SCENE, "swif")
    swif = outer.root[s["data"]:s["data"] + s["size"]]
    outer.root = pacx.replace_file(outer.root, SCENE, "swif", edit_credit(edit_swif(swif, h, new_h, cells)))
    head = None
    if rel == HEAD_ARCHIVE:  # the CONTINUE bubble heads: a cell per slot below the game's four
        if block_of(outer, HEAD_HOST, "dds") != bname:
            sys.exit(f"{rel}: {HEAD_HOST} isn't in {HOST}'s block (the descriptor's runs are per block)")
        blk = outer.blocks[bname]
        he = pacx.find(blk, HEAD_HOST, "dds")
        head_dds = blk[he["data"]:he["data"] + he["size"]]
        hw, hh, _, _ = bc7.dds_info(head_dds)
        h_per_row = hw // oc.HEAD_W
        h_rows = math.ceil(oc.SLOTS / h_per_row)
        head_cells = [((j % h_per_row) * oc.HEAD_W, hh + (j // h_per_row) * oc.HEAD_H, oc.HEAD_W, oc.HEAD_H)
                      for j in range(oc.SLOTS)]
        new_head = bc7.dds_append_rows(head_dds, oc.blank_block() * ((hw // 4) * (h_rows * oc.HEAD_H // 4)),
                                       h_rows * oc.HEAD_H)
        outer.blocks[bname] = pacx.replace_file(blk, HEAD_HOST, "dds", new_head)
        outer.root = pacx.set_size(outer.root, HEAD_HOST, "dds", len(new_head))
        head = dict(orig=head_dds, w=hw, old_h=hh, new_h=hh + h_rows * oc.HEAD_H, cells=head_cells, size=len(new_head),
                    pitch=(hw // 4) * oc.BLOCK)
    at = pacx.find(outer.blocks[bname], HOST, "dds")["data"]
    pixels = at + DDS_HEADER
    pitch = (w // 4) * oc.BLOCK
    literal = [(pixels + (h // 4) * pitch, at + len(new_dds))]
    if head:
        hat = pacx.find(outer.blocks[bname], HEAD_HOST, "dds")["data"]
        head["pixels"] = hat + DDS_HEADER
        literal.append((head["pixels"] + (head["old_h"] // 4) * head["pitch"], hat + head["size"]))
    data = outer.build({bname: literal})
    file_at, chunks = outer.layout[bname]
    runs = oc.literal_runs(chunks, file_at)
    desc = {"path": rel, "size": len(data), "runs": runs, "pitch": pitch,
            "cells": [pixels + (y // 4) * pitch + (x // 4) * oc.BLOCK for x, y, _, _ in cells]}
    if head:
        desc["head_pitch"] = head["pitch"]
        desc["head_cells"] = [head["pixels"] + (y // 4) * head["pitch"] + (x // 4) * oc.BLOCK
                              for x, y, _, _ in head["cells"]]
    return data, desc, dict(block=bname, old_h=h, new_h=new_h, cells=cells, head=head)


# ---------------------------------------------------------------- the text archives
def build_text(rel):
    """-> (archive bytes with every name blank, its descriptor entry)"""
    header, inner = origins_pac.read_outer((RAW_IN / rel[len("raw/"):]).read_bytes())
    doc = cnvrs_text.parse(origins_pac.last_file(inner))
    if cnvrs_text.build(doc) != origins_pac.last_file(inner):
        sys.exit(f"{rel}: can't reproduce the game's file, not touching it")
    keys = {e["key"] for e in doc["entries"]}
    room = " " * oc.NAME_UNITS  # (the room each name line gets; emptied below)
    for s in range(1, oc.SLOTS + 1):
        for line in (1, 2):
            key = oc.name_key(s, line)
            if key in keys:
                sys.exit(f"{rel}: {key} already exists")
            doc["entries"].append({"key": key, "text": room})
    for s in range(1, oc.SLOTS + 1):
        key = oc.credit_key(s)
        if key in keys:
            sys.exit(f"{rel}: {key} already exists")
        doc["entries"].append({"key": key, "text": " " * oc.CREDIT_UNITS})
    for key, text in LAUNCHER_TEXT.items():  # (the SONIC MANIA button's label and descriptions)
        if key in keys:
            sys.exit(f"{rel}: {key} already exists")
        doc["entries"].append({"key": key, "text": text})
    ids = [cnvrs_text.key_hash(e["key"]) for e in doc["entries"]]
    if len(set(ids)) != len(ids):
        sys.exit(f"{rel}: two text keys with the same hash")
    inner = origins_pac.replace_last_file(inner, cnvrs_text.build(doc))
    data = origins_pac.write_outer(header, inner, literal=True)
    root_at = struct.unpack_from("<I", data, 0x10)[0]
    pieces = [inner[k:k + origins_pac.CHUNK] for k in range(0, len(inner), origins_pac.CHUNK)]
    runs = oc.literal_runs([(oc.lz4_literal(p), p) for p in pieces], root_at)
    _, file_at, _ = max(origins_pac.inner_files(inner), key=lambda f: f[1])
    where = cnvrs_text.entry_positions(origins_pac.last_file(inner))
    names = []
    for s in range(1, oc.SLOTS + 1):
        for line in (1, 2):
            text_at, length_at = where[oc.name_key(s, line)]
            names.append((file_at + text_at, file_at + length_at))
    credits = []
    for s in range(1, oc.SLOTS + 1):
        text_at, length_at = where[oc.credit_key(s)]
        credits.append((file_at + text_at, file_at + length_at))
    return data, {"path": rel, "size": len(data), "runs": runs, "names": names, "credits": credits}


# ---------------------------------------------------------------- the first 21 cards, written in
def legacy_cards():
    """{slot: card} of the first 21 characters (kinds 7-27 -> slots 1-21), from their packages as the DLL reads them."""
    cards = {}
    for e in [e for e in EXTRAS if e["n"] <= LEGACY]:  # (a retired number among them: its slot stays blank)
        pkg = PACKAGES / e["art"].name
        pic = pkg / oc.PICTURE
        if not pic.exists():
            sys.exit(f"{pic.relative_to(REPO)} is missing: run tools/build_packages.py first")
        name = json.loads((pkg / "noswap_character.json").read_text())["name"]
        head = pkg / oc.HEAD_PICTURE
        if not head.exists():
            sys.exit(f"{head.relative_to(REPO)} is missing: run tools/build_packages.py first")
        info = json.loads((pkg / "noswap_character.json").read_text())
        cards[e["n"]] = dict(picture=oc.read_card(pic.read_bytes()), lines=oc.name_lines(name),
                             head=oc.read_head(head.read_bytes()), credit=info.get("credit_short", ""))
    return cards


# ---------------------------------------------------------------- checks
def verify_ui(data, desc, info, cards, preview=None):
    """Re-read a built picture archive: archive and .swif pointer models, patterns, each slot's cell pixels."""
    outer = pacx.Outer(data)
    assert outer.build() == data, "archive doesn't re-read to itself"
    for buf in [outer.root] + list(outer.blocks.values()):
        end = pacx.sections(buf)["offsets"][0]
        for p in pacx.read_offsets(buf):
            v = struct.unpack_from("<Q", buf, p)[0]
            assert 0 < v < end, f"PAC pointer at {p:#x} -> {v:#x}"
    oc.check_runs(data, desc)
    s = pacx.find(outer.root, SCENE, "swif")
    P = surfride.check(outer.root[s["data"]:s["data"] + s["size"]])
    blk = outer.blocks[info["block"]]
    e = pacx.find(blk, HOST, "dds")
    assert pacx.find(outer.root, HOST, "dds")["size"] == e["size"]
    img = Image.open(io.BytesIO(blk[e["data"]:e["data"] + e["size"]]))
    img.load()
    px = np.array(img.convert("RGBA"))
    assert px.shape[0] == info["new_h"]
    tl = P["project"]["texlists"][0]
    tex = next(t for t in tl["textures"] if t["file"] == HOST)
    assert (tex["w"] * 2, tex["h"] * 2) == (px.shape[1], px.shape[0])
    L = _layer(P, LAYER)
    ids = {c["id"]: c["name"] for c in L["casts"]}
    anims = {a["name"]: a for a in L["anims"]}
    groups = [n for n in ids.values() if n.startswith("null_char_")]
    check_credit(P)
    img_cast = next(c for c in L["casts"] if c["name"] == IMAGE_CAST)
    refs = img_cast["image"]["cropref0"]
    assert len(refs) == oc.SLOTS
    for g in range(1, 8):
        shown = {ids[m["cast"]]: m["tracks"][0]["keys"][0][1] for m in anims[f"PRM_chara_{g}"]["motions"]}
        assert [n for n in groups if shown.get(n)] == [f"null_char_{g}"] and shown[GROUP] == 0, f"PRM_chara_{g}"
    for s in range(1, oc.SLOTS + 1):
        for lines in (1, 2):
            a = anims[oc.pattern(s, lines)]
            got = {(ids[m["cast"]], m["tracks"][0]["type"]): m["tracks"][0]["keys"][0][1] for m in a["motions"]}
            assert all(len(m["tracks"]) == 1 for m in a["motions"])
            assert [n for n in groups if got.get((n, "Display"))] == [GROUP], a["name"]
            assert set(n for n, t in got if t == "Display") >= set(groups)
            assert got[(IMAGE_CAST, "CropIndex0")] == s - 1 and got[(NAME_LINE_2, "Display")] == int(lines == 2)
        x, y, w, h = info["cells"][s - 1]
        tli, ti, ci = refs[s - 1]
        l, t, r, bt = P["project"]["texlists"][tli]["textures"][ti]["crops"][ci]
        box = tuple(round(v) for v in (l * px.shape[1], t * px.shape[0], r * px.shape[1], bt * px.shape[0]))
        assert box == (x, y, x + w, y + h), (box, (x, y, w, h))
        want = expected_cell(cards.get(s))
        got_px = px[y:y + h, x:x + w].copy()
        got_px[got_px[..., 3] == 0] = 0
        assert (got_px == want).all(), f"slot {s}: the cell doesn't decode to its card"
    head = info["head"]
    if head:  # the CONTINUE bubble heads: the game's four unchanged, each slot's cell its head
        he = pacx.find(blk, HEAD_HOST, "dds")
        assert pacx.find(outer.root, HEAD_HOST, "dds")["size"] == he["size"] == head["size"]
        hpx = decode(blk[he["data"]:he["data"] + he["size"]])
        assert hpx.shape[:2] == (head["new_h"], head["w"])
        assert (hpx[:head["old_h"]] == decode(head["orig"])).all(), "the game's heads changed"
        for s in range(1, oc.SLOTS + 1):
            x, y, w, h = head["cells"][s - 1]
            got_px = hpx[y:y + h, x:x + w].copy()
            got_px[got_px[..., 3] == 0] = 0
            want = expected_head(cards.get(s, {}).get("head"))
            assert (got_px == want).all(), f"slot {s}: the head cell doesn't decode to its head"
    if preview:
        Path(preview).mkdir(parents=True, exist_ok=True)
        bg = Image.new("RGBA", img.size, (70, 70, 110, 255))
        bg.alpha_composite(img.convert("RGBA"))
        bg.convert("RGB").resize((img.width // 4, img.height // 4), Image.NEAREST).save(
            Path(preview) / f"{Path(desc['path']).stem}_{HOST}.png")


def check_credit(P):
    """The credit box: one, in CREDIT_LAYER under CREDIT_PARENT (its last child), CREDIT_COPY's node flags and colour,
    CREDIT_STYLE's user data, at CREDIT_POS, CREDIT_BOX in size; the layer's other casts as the game's (by name)."""
    L = _layer(P, CREDIT_LAYER)
    casts = L["casts"]
    hits = [i for l in P["all_layers"].values() for i, c in enumerate(l["casts"]) if c["name"] == oc.CREDIT_CAST]
    assert len(hits) == 1, f"{len(hits)} credit boxes"
    i = next(j for j, c in enumerate(casts) if c["name"] == oc.CREDIT_CAST)
    box, copy = casts[i], next(c for c in casts if c["name"] == CREDIT_COPY)
    style = next(c for l in P["all_layers"].values() for c in l["casts"] if c["name"] == CREDIT_STYLE)
    kids, k = [], casts[next(j for j, c in enumerate(casts) if c["name"] == CREDIT_PARENT)]["child"]
    while k != -1:
        kids.append(k)
        k = casts[k]["sibling"]
    assert kids[-1] == i and box["child"] == -1, "credit box not the window's last child"
    assert box["flags"] == copy["flags"] and box["ud"] == style["ud"], (box["flags"], box["ud"])
    assert box["image"]["size"] == CREDIT_BOX and box["image"]["cropref0"] == copy["image"]["cropref0"]
    assert box["trs"]["t"][:2] == CREDIT_POS and box["trs"]["mat"] == copy["trs"]["mat"] and box["trs"]["display"] == 1
    assert not any(m["cast"] == box["id"] for a in L["anims"] for m in a["motions"])


def decode(dds):
    img = Image.open(io.BytesIO(dds))
    img.load()
    return np.array(img.convert("RGBA"))


def expected_head(head):
    """The RGBA pixels a slot's head cell must decode to: the head in the middle, transparent (all 0) around it."""
    cell = np.zeros((oc.HEAD_H, oc.HEAD_W, 4), np.uint8)
    if head:
        w, h, blocks = head
        pic = decode(oc.dds_bc7(w, h, blocks))
        pic[pic[..., 3] == 0] = 0
        x0, y0 = ((oc.HEAD_W // 4 - w // 4) // 2) * 4, ((oc.HEAD_H // 4 - h // 4) // 2) * 4
        cell[y0:y0 + h, x0:x0 + w] = pic
    return cell


def expected_cell(card):
    """The RGBA pixels a slot's cell must decode to: the card bottom-centre, transparent (all 0) around it."""
    cell = np.zeros((oc.CELL_H, oc.CELL_W, 4), np.uint8)
    if card:
        w, h, blocks = card["picture"]
        pic = np.array(Image.open(io.BytesIO(oc.dds_bc7(w, h, blocks))).convert("RGBA"))
        pic[pic[..., 3] == 0] = 0
        x0 = ((oc.CELL_W // 4 - w // 4) // 2) * 4
        cell[oc.CELL_H - h:, x0:x0 + w] = pic
    return cell


def verify_text(data, desc, cards):
    oc.check_runs(data, desc)
    _, inner = origins_pac.read_outer(data)
    doc = cnvrs_text.parse(origins_pac.last_file(inner))
    texts = {e["key"]: e["text"] for e in doc["entries"]}
    for s in range(1, oc.SLOTS + 1):
        for line in (1, 2):
            want = cards[s]["lines"][line - 1] if s in cards else ""
            assert texts[oc.name_key(s, line)] == want, (desc["path"], s, line)
        want = cards[s].get("credit", "")[:oc.CREDIT_UNITS] if s in cards else ""
        assert texts[oc.credit_key(s)] == want, (desc["path"], s, "credit")
    for key, text in LAUNCHER_TEXT.items():
        assert texts[key] == text, (desc["path"], key)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--preview", help="write preview PNGs of the card texture here")
    args = ap.parse_args()
    cards = legacy_cards()
    archives, outputs = [], []
    head = None
    for rel in oc.PICTURE_ARCHIVES:
        blank, desc, info = build_ui(rel)
        verify_ui(blank, desc, info, {})
        data = oc.apply(blank, desc, cards)
        verify_ui(data, desc, info, cards, args.preview)
        archives.append(desc)
        outputs.append((rel, data))
        print(f"{rel}: {len(data):,} bytes; {oc.SLOTS} card slots in {HOST} ({info['old_h']} -> {info['new_h']} px "
              f"high, cells {oc.CELL_W}x{oc.CELL_H}), {len(desc['runs'])} literal chunks")
        if info["head"]:
            head = info["head"]
            print(f"{rel}: {oc.SLOTS} CONTINUE bubble head cells in {HEAD_HOST} ({head['old_h']} -> {head['new_h']} "
                  f"px high, cells {oc.HEAD_W}x{oc.HEAD_H}, crops {oc.HEAD_FIRST_CROP}-{oc.HEAD_FIRST_CROP + oc.SLOTS - 1})")
    if not head:
        sys.exit(f"no archive holds {HEAD_HOST}")
    scenes = []
    for path in sorted((RAW_IN / "ui").glob("ui_mainmenu_*.pac")):
        if path.stem.startswith("ui_mainmenu_pkg_"):
            continue  # (package art, no scene)
        rel = f"raw/ui/{path.name}"
        data = build_scene(rel, head["old_h"], head["new_h"], head["cells"])
        verify_scene(data, rel, head["old_h"], head["new_h"], head["cells"])
        scenes.append({"path": rel, "size": len(data)})
        outputs.append((rel, data))
    print(f"raw/ui: {len(scenes)} languages' {HEAD_SCENE}.swif with {oc.HEAD_FIRST_CROP + oc.SLOTS} head crops on "
          f"{', '.join(HEAD_CASTS)} ({', '.join(Path(sc['path']).stem[len('ui_mainmenu_'):] for sc in scenes)})")
    for path in sorted((RAW_IN / "text").glob("text_menu_*.pac")):
        rel = f"raw/text/{path.name}"
        blank, desc = build_text(rel)
        data = oc.apply(blank, desc, {})  # (the room the build left, emptied)
        blank = data
        verify_text(blank, desc, {})
        data = oc.apply(blank, desc, cards)
        verify_text(data, desc, cards)
        archives.append(desc)
        outputs.append((rel, data))
    print(f"raw/text: {len(outputs) - len(oc.PICTURE_ARCHIVES) - len(scenes)} languages, {2 * oc.SLOTS} name keys each "
          f"({oc.NAME_UNITS} UTF-16 units of room per line), {oc.SLOTS} credit keys ({oc.CREDIT_UNITS} units)")
    for rel, data in outputs:
        (MOD / rel).parent.mkdir(parents=True, exist_ok=True)
        (MOD / rel).write_bytes(data)
    descriptor = {
        "version": oc.DESCRIPTOR_VERSION,
        "note": "Written by tools/build_origins_menu.py with the archives it describes: where the NoSwap DLL writes each "
                "character's card (docs/plan-b-modular-characters.md, phase B) and CONTINUE bubble head (head_cells; "
                "the scenes showing them are shipped as they are). Runs: [stream offset, file offset, length] of LZ4 "
                "literal-only chunks.",
        "slots": oc.SLOTS, "cell": [oc.CELL_W, oc.CELL_H], "name_units": oc.NAME_UNITS, "picture": oc.PICTURE,
        "blank_block": oc.blank_block().hex(), "patterns": [oc.pattern(1, 1), oc.pattern(1, 2)],
        "name_keys": [oc.name_key(1, 1), oc.name_key(1, 2)],
        "credit": {"units": oc.CREDIT_UNITS, "key": oc.credit_key(1), "cast": oc.CREDIT_CAST},
        "head": {"cell": [oc.HEAD_W, oc.HEAD_H], "picture": oc.HEAD_PICTURE, "first_crop": oc.HEAD_FIRST_CROP,
                 "scenes": scenes},
        # the SONIC MANIA button's patterns (in every scene above) and text keys: Mania Lock-On uses NoSwap's archives
        # for its button only when these are here (native/lockon/src/MenuFiles.h IsCarrier)
        "mania_launcher": {"patterns": [LAUNCHER_PATTERN, LAUNCHER_PATTERN_DLC], "keys": list(LAUNCHER_TEXT)},
        "archives": archives}
    (MOD / oc.DESCRIPTOR).write_text(json.dumps(descriptor, separators=(",", ":")) + "\n")
    print(f"{oc.DESCRIPTOR}: {len(archives)} archives; the first {len(cards)} characters' cards written in")


if __name__ == "__main__":
    main()
