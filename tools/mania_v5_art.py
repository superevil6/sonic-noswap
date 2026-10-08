#!/usr/bin/env python3
"""Build a Mania-only package whose art is an existing RSDKv5 player file (tools/mania_only.py "source": "v5"; Amy:
Origins Plus' 3K_Players/Amy.bin / .gif), for NoSwapMania. build_mania_art.build() hands such packages here; the
package's files and JSON are the same as every other extra's (build_mania_art's docstring), so the mod needs nothing
special to load it.

Player.bin: Mania's Players/Sonic.bin list (54 animations), each taken BY NAME from the source file (mania_only "map"
where the names differ or the source's is empty), its frames, timings and boxes as the source has them (Origins' S3&K
runs on Mania's engine, so its player animations already play right there), except where Mania's player code counts
frames (Player.c), which follows Mania's template:
  - Walk / Air Walk / Jog: Mania switches Jog -> Walk only on Jog's frame 9 (into Walk's frame 9), so a cycle shorter
    than 10 frames is repeated (same frames, same timings: an 8-frame cycle twice);
  - Look Up / Crouch: held on frame 5 / 4 and played back to frame 0 (build_mania_art.RETURN_TO_IDLE), on the template's
    frame counts and timings with the source's frames.
Then the source's own move animations (mania_only "abilities": anim_base + 0, 1...) and its continue poses.
Pixels are copied exactly; colours: an exact Mania global colour (1-63) where there is one, else an own slot
(V5_OWN_SLOTS, by how common the colour is on its frames), else the nearest of those (reported: the approved rare-shade
merge).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import ani_v5
import build_mania_art as mania
from gifio import save_sheet

# The extra's own slots: build_mania_art.OWN_SLOTS, then Mighty's (96-101) and Ray's (113-118) six: Mania only writes
# those for a Mighty or Ray player (Player_StageLoad / their Super palettes), and the extra plays as Sonic, whose
# partner can only be Tails (70-75), so in a stage they are free. (The mod: OWN_MAX.)
V5_OWN_SLOTS = mania.OWN_SLOTS + list(range(96, 102)) + list(range(113, 119))
S3K_SPRITES = mania.REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"
REPEAT_TO = {"Walk": 10, "Air Walk": 10, "Jog": 10,  # (Player.c: Jog frame 9 -> Walk frame 9)
             "Dash": 5}  # (Player_Create with the Peel Out medal mod copies Fly's frames 0-3 over Dash's 1-4: see build_player)


def _key(rgb):
    return rgb[0] << 16 | rgb[1] << 8 | rgb[2]


def source(e):
    v5 = e["v5"]
    ani = ani_v5.read_bin(v5["bin"])
    gif = Image.open(v5["gif"])
    return ani, np.array(gif), gif.getpalette()


def picked(e, ani):
    """The source animations the package uses, by Mania name (and its abilities / continue names)."""
    v5 = e["v5"]
    by_name = {a["name"]: a for a in ani["anims"]}
    names = [a["name"] for a in mania.host_template(e)["anims"]]
    out = {}
    for n in names:
        src = v5["map"].get(n, n)
        a = by_name.get(src)
        if a is None or not a["frames"]:
            a = by_name.get(n) if by_name.get(n, {}).get("frames") else None
        out[n] = a
    extra = list(v5["abilities"]) + list(v5.get("continue", ()))
    for n in extra:
        if not by_name.get(n, {}).get("frames"):
            sys.exit(f"{e['art'].name}: the source has no \"{n}\" animation")
        out[n] = by_name[n]
    return out, extra


def palette(e):
    """{source palette index: Mania slot} and {own slot: "#rrggbb"}; reports merges."""
    ani, px, pal = source(e)
    chosen, _ = picked(e, ani)
    mask = np.zeros(px.shape, bool)
    for a in chosen.values():
        for f in (a or {"frames": []})["frames"]:
            mask[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]] = True
    counts = np.bincount(px[mask].ravel(), minlength=256)
    rgb = {i: tuple(pal[3 * i:3 * i + 3]) for i in range(len(pal) // 3)}
    glob = {}
    for i, c in mania.global_palette().items():
        if 0 < i < mania.PLAYER_SLOT and c != (255, 0, 255):
            glob.setdefault(c, i)
    used = [i for i in range(1, 256) if counts[i]]
    slot_of, own = {0: 0}, {}
    need = {}
    for i in used:
        if rgb[i] in glob:
            slot_of[i] = glob[rgb[i]]
        else:
            need.setdefault(rgb[i], []).append(i)
    order = sorted(need, key=lambda c: -sum(counts[i] for i in need[c]))
    for c, s in zip(order, V5_OWN_SLOTS):
        own[s] = c
        for i in need[c]:
            slot_of[i] = s
    merged = order[len(V5_OWN_SLOTS):]
    if merged:
        avail = {**{s: c for c, s in glob.items()}, **own}
        total = int(counts[1:].sum())
        lines = []
        for c in merged:
            s = min(avail, key=lambda s: sum((a - b) ** 2 for a, b in zip(avail[s], c)))
            n = sum(int(counts[i]) for i in need[c])
            for i in need[c]:
                slot_of[i] = s
            lines.append("#%02x%02x%02x -> #%02x%02x%02x (%d px)" % (*c, *avail[s], n))
        print(f"  {e['art'].name}: {len(merged)} rarest colour(s) of {total} px merged into the nearest: " + ", ".join(lines))
    return slot_of, {s: "#%02x%02x%02x" % c for s, c in own.items()}


def _frames(a):
    return [dict(f, sheet=0) for f in a["frames"]]


def build_player(e, out_dir, slot_of, own):
    """Player.bin / Player.gif (see the module docstring). Returns the appended animations' names."""
    folder = e["art"].name
    ani, px, _ = source(e)
    chosen, extra = picked(e, ani)
    template = mania.host_template(e)
    anims = []
    for t in template["anims"]:
        n = t["name"]
        a = chosen[n]
        if a is None:
            anims.append(dict(t, frames=[]) if not t["frames"] else dict(t, frames=_frames(chosen["Idle"])))
            if t["frames"]:
                print(f"  {n}: none in the source: its Idle")
            continue
        frames = _frames(a)
        out = dict(name=n, speed=a["speed"], loop=a["loop"], rot=a["rot"], frames=frames)
        if n in REPEAT_TO and len(frames) < REPEAT_TO[n]:
            reps = -(-REPEAT_TO[n] // len(frames))
            out["frames"] = [dict(f) for _ in range(reps) for f in frames]
        if n in mania.RETURN_TO_IDLE:
            # the template's frame count and timings, the source's pictures spread over them, then played back
            m = len(t["frames"])
            spread = [frames[k * len(frames) // m] for k in range(m)]
            out = dict(t, frames=[dict(tf, sheet=0, x=s["x"], y=s["y"], w=s["w"], h=s["h"], px=s["px"], py=s["py"],
                                       boxes=s["boxes"]) for tf, s in zip(t["frames"], spread)])
            idle = _frames(chosen["Idle"])[0]
            mania.return_to_idle(out, idle, *mania.RETURN_TO_IDLE[n])
        anims.append(out)
    for n in extra:
        a = chosen[n]
        anims.append(dict(name=n, speed=a["speed"], loop=a["loop"], rot=a["rot"], frames=_frames(a)))
    # Mania's Peel Out (the medal mod / level select's "max control" cheat: Player_Create) copies Fly's (ANI_PEELOUT) frames
    # 0-3 over Dash's 1-4, unchecked: Fly is Dash one frame on, so that copy changes nothing (she has no Peel Out)
    by = {a["name"]: a for a in anims}
    if "Fly" in by and "Dash" in by and len(by["Dash"]["frames"]) >= 5:
        d = by["Dash"]
        by["Fly"].update(speed=d["speed"], loop=d["loop"], rot=d["rot"], frames=[dict(f) for f in d["frames"][1:] + d["frames"][:1]])
    for n in e["v5"].get("reach", []):  # (the same frames, box 0 = the AttackBox: the mod's hammer reach, ManiaAmy.h)
        a = chosen[n]
        frames = [dict(f, boxes=[f["boxes"][2], f["boxes"][1], f["boxes"][2]]) for f in _frames(a)]
        anims.append(dict(name=f"{n} Reach", speed=a["speed"], loop=a["loop"], rot=a["rot"], frames=frames))

    # the sheet: the source's pixels in Mania's slots (only the frames used; the rest of the sheet left empty)
    mask = np.zeros(px.shape, bool)
    for a in anims:
        for f in a["frames"]:
            mask[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]] = True
    lut = np.zeros(256, np.uint8)
    for i, s in slot_of.items():
        lut[i] = s
    out_px = np.where(mask, lut[px], 0).astype(np.uint8)
    img = Image.fromarray(out_px, "P")
    view = [0] * 768
    for s, c in mania.runtime_palette(own).items():
        view[3 * s:3 * s + 3] = [c >> 16, c >> 8 & 255, c & 255]
    view[0:3] = [255, 0, 255]
    img.putpalette(view)
    save_sheet(img, out_dir / "Player.gif")
    ani_v5.write_bin(out_dir / "Player.bin", dict(sheets=[f"{mania.PKG_SPRITES}/{folder}/Player.gif"],
                                                  hitboxes=ani["hitboxes"], anims=anims))
    used = sorted(set(np.unique(out_px).tolist()) - {0})
    print(f"  Player.bin: {len(anims)} animations ({len(template['anims'])} Mania + {', '.join(extra)}), "
          f"sheet {img.width}x{img.height}, palette slots {used}")
    return extra


def _ui_frame(spec):
    """(sheet path, (x, y, w, h)) of an official UI frame: (sprite file, animation, frame)."""
    path, anim, k = spec
    a = ani_v5.read_bin(S3K_SPRITES / path)
    f = next(x for x in a["anims"] if x["name"] == anim)["frames"][k]
    return S3K_SPRITES / a["sheets"][f["sheet"]], (f["x"], f["y"], f["w"], f["h"])


def ui_source(e):
    """build_mania_art._ui_source's (sheet, background colours, rects) from the official frames (one sheet for both)."""
    life_sheet, life = _ui_frame(e["ui"]["life_icon"])
    cont_sheet, cont = _ui_frame(e["ui"]["continue_icon"])
    if life_sheet != cont_sheet:
        sys.exit(f"{e['art'].name}: the life and continue icons are on different sheets")
    pal = Image.open(life_sheet).getpalette()
    return life_sheet, ["#%02x%02x%02x" % tuple(pal[0:3])], {"life_icon": life, "mini_1": cont}


def build_shot(e, out_dir, own):
    """Shot.bin / Shot.gif: the source's thrown hammer (mania_only abilities' last: "Hammer"), as the shot object's
    animation 0, exact pixels on Player.gif's slots (its own sheet: the shot object loads its file alone)."""
    folder = e["art"].name
    ani = ani_v5.read_bin(out_dir / "Player.bin")
    a = next(x for x in ani["anims"] if x["name"] == e["v5"]["abilities"][-1])
    sheet = np.array(Image.open(out_dir / "Player.gif"))
    gif = Image.open(out_dir / "Player.gif")
    frames, x, h = [], 2, max(f["h"] for f in a["frames"]) + 4
    pieces = []
    for f in a["frames"]:
        pieces.append((x, sheet[f["y"]:f["y"] + f["h"], f["x"]:f["x"] + f["w"]]))
        box = f["boxes"][0]
        frames.append(dict(f, sheet=0, x=x, y=2, boxes=[box, box]))
        x += f["w"] + 2
    w = 1 << (x - 1).bit_length()
    canvas = np.zeros((h, max(w, 16)), np.uint8)
    for (px0, p), f in zip(pieces, frames):
        canvas[2:2 + f["h"], px0:px0 + f["w"]] = p
    img = Image.fromarray(canvas, "P")
    img.putpalette(gif.getpalette())
    save_sheet(img, out_dir / "Shot.gif")
    ani_v5.write_bin(out_dir / mania.SHOT_FILE, dict(sheets=[f"{mania.PKG_SPRITES}/{folder}/Shot.gif"],
                                                     hitboxes=["Hitbox", "Hitbox"],
                                                     anims=[dict(a, name="Shot", frames=frames)]))
    print(f"  {mania.SHOT_FILE}: {len(frames)} frame(s) (her thrown hammer), sheet {img.width}x{img.height}")


def build(e):
    folder = e["art"].name
    print(f"{folder} ({e['name']}, Mania only, from {e['v5']['bin'].relative_to(mania.REPO)}):")
    out_dir = mania.PACKAGES / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    slot_of, own = palette(e)
    extra_anims = build_player(e, out_dir, slot_of, own)
    e = dict(e, ui_source=ui_source(e))
    save_colours = mania.build_save_select(e, out_dir)
    build_shot(e, out_dir, own)
    # (the shot's numbers as mania_only.py has them: her own sounds, no MANIA_SFX stand-in)
    shots = {"shot_file": f"{mania.PKG_SPRITES}/{folder}/{mania.SHOT_FILE}", "shot": dict(e["shot"])} if e.get("shot") else None
    data = mania.mania_json(e, own, save_colours, extra_anims, shots)
    data["mania_only"] = True
    data["mania"]["amy"] = e.get("moves", {})  # (her moves' numbers: native/mania/src/ManiaAmy.h)
    (out_dir / "noswap_character.json").write_text(json.dumps(data, indent=1) + "\n")
    print(f"  noswap_character.json: palette {data['mania']['palette']}")
    import build_mania_hud
    sign_sheet, sign_rect = _ui_frame(e["ui"]["sign_face"])
    e = dict(e, sign_face_source=(sign_sheet, sign_rect), continue_anims=e["v5"].get("continue"))
    build_mania_hud.build(e, out_dir, own)
