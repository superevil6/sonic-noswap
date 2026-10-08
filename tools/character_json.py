#!/usr/bin/env python3
"""Read a character.json (docs/character-json.md) and turn it into what NoSwap's pipeline consumes today:

  - configs(folder, game): the sheet2ani config a make_configs.py writes (Sonic 1 / Sonic 2; CD's comes from the Sonic 2
    one through cd_config.py, S3&K's and Mania's from it through build_s3k_art.py / build_mania_art.py);
  - write_configs(folder): writes them (<id>.json, <id>_s2.json), as a make_configs.py does: build_art.py runs it;
  - extras_entry(folder): the character's tools/extras.py EXTRAS entry;
  - abilities_entry(folder): its tools/abilities.py ABILITIES entry;
  - folders(): every character folder (testmods/*/ and $NOSWAP_CHARACTER_DIRS): tools/extras.py adds them to EXTRAS;
  - mania_folders(): the art folders whose character.json enables Mania (tools/build_mania_art.py).

A character is known by its key, "<creator>.<character>" ("key"; NoSwap's own default to noswap.<id>), and numbered by
tools/registry.py (data/registry.json), so its folder is all a build needs: no central list to edit.

Usage: character_json.py <folder> ...   (writes each folder's sheet2ani configs; same as running its make_configs.py)

Plain data in, the same Python structures out: a character built from its character.json comes out byte-identical to the
same character written as make_configs.py + extras.py + abilities.py entries. Keys starting with "_" are comments.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anim_fallbacks  # noqa: E402
from noswap_cli.templates import TEMPLATES  # noqa: E402  (the base's animation lists, no game data needed)

REPO = Path(__file__).resolve().parent.parent
TESTMODS = Path(os.environ.get("NOSWAP_TESTMODS") or REPO / "testmods")  # (the Creator Kit: its characters folder)
FORMAT = "noswap-character/1"
FILE = "character.json"
ORIGINS_GAMES = ("sonic1", "sonic2", "soniccd", "s3k")
FLAGS = ("super", "drop_dash", "roll", "no_roll", "private", "crossover")
FLAG_DEFAULTS = {"super": False, "drop_dash": False, "roll": False, "no_roll": False, "private": False,
                 "crossover": False}
# the base character's template animation file in Sonic 1 / Sonic 2 (its animation list)
TEMPLATE_ANI = {"sonic": "Sonic.ani", "tails": "Tails.ani", "knuckles": "Knuckles.ani"}
HEX = re.compile(r"^-?0x[0-9a-fA-F]+$")
KEY = re.compile(r"^[a-z0-9][a-z0-9_-]*\.[a-z0-9][a-z0-9_.-]*$")  # (tools/registry.py's)


def _clean(v):
    """Drop "_" comment keys and turn "0x..." strings into ints, all the way down."""
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items() if not k.startswith("_")}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, str) and HEX.match(v):
        return int(v, 16)
    return v


# Renamed move and field names: (old prefix, new prefix). An older character.json's names are migrated as it loads
# (migrate_abilities; `noswap check` notes each one, and the editor's Save writes the new names). 2026-10: the Y attack
# that isn't a projectile, "popgun" and its popgun_* fields (popgun_reach...), became "melee" (melee_reach...).
RENAMED = (("popgun", "melee"),)


def renamed(name):
    """A move or field name in today's spelling (popgun_reach -> melee_reach); other names unchanged."""
    for old, new in RENAMED:
        if name == old or name.startswith(old + "_"):
            return new + name[len(old):]
        if name.startswith("_" + old):  # (a "_" comment key next to the field it explains)
            return "_" + new + name[len(old) + 1:]
    return name


def migrate_abilities(entry):
    """Rename an abilities entry's old names in place (keys keep their order; the moves list too). Returns
    [(old, new)] for each one renamed, comment keys left out. With both spellings there, the new one wins."""
    if not isinstance(entry, dict):
        return []
    done = []
    moves = entry.get("abilities")
    if isinstance(moves, list):
        for i, m in enumerate(moves):
            if isinstance(m, str) and renamed(m) != m:
                done.append((m, renamed(m)))
                moves[i] = renamed(m)
        if len(set(m for m in moves if isinstance(m, str))) != len(moves):
            entry["abilities"] = list(dict.fromkeys(moves))  # ("popgun" and "melee" both listed: once)
    if any(renamed(k) != k for k in entry):
        items = list(entry.items())
        entry.clear()
        for k, v in items:
            new = renamed(k)
            if new != k:
                if not k.startswith("_"):
                    done.append((k, new))
                if any(kk == new for kk, _ in items):  # (both spellings: the new one's value)
                    continue
            entry[new] = v
    return done


def load(folder):
    """The character.json in an art folder (a Path, or a name under testmods/), checked and cleaned."""
    folder = Path(folder) if isinstance(folder, Path) or "/" in str(folder) else TESTMODS / folder
    path = folder / FILE
    c = _clean(json.loads(path.read_text()))
    if c.get("format") != FORMAT:
        raise SystemExit(f"{path}: \"format\" must be \"{FORMAT}\"")
    if c["id"] != folder.name:
        raise SystemExit(f"{path}: id {c['id']!r} must match its folder's name ({folder.name!r})")
    if c.get("base", "sonic") not in TEMPLATE_ANI:
        raise SystemExit(f"{path}: base must be one of {', '.join(TEMPLATE_ANI)}")
    games = c.get("games", {})
    off = [g for g in ORIGINS_GAMES if not games.get(g, True)]
    if off:  # (the Origins builds make every extra for all four games)
        raise SystemExit(f"{path}: leaving out an Origins game isn't supported yet ({', '.join(off)})")
    unknown = set(c.get("flags", {})) - set(FLAGS)
    if unknown:
        raise SystemExit(f"{path}: unknown flags {sorted(unknown)}")
    c["key"] = c.get("key") or "noswap." + c["id"]
    if not KEY.match(c["key"]):
        raise SystemExit(f"{path}: key {c['key']!r} must be <creator>.<character> (lower case letters, digits, '-', '_'), "
                         "e.g. \"someone.newchar\"")
    c["folder"] = folder
    migrate_abilities(c.get("abilities"))  # (older names: popgun_reach -> melee_reach)
    return c


def has_json(folder):
    return (Path(folder) / FILE).exists()


def folders():
    """Every character folder with a character.json, in name order: testmods/*/, then each path in
    $NOSWAP_CHARACTER_DIRS (os.pathsep-separated: a character folder, or a folder of them)."""
    found = sorted(p.parent for p in TESTMODS.glob(f"*/{FILE}"))
    for d in filter(None, os.environ.get("NOSWAP_CHARACTER_DIRS", "").split(os.pathsep)):
        d = Path(d).resolve()
        found += [d] if (d / FILE).exists() else sorted(p.parent for p in d.glob(f"*/{FILE}"))
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------- frames, colours

def _frame(c, ref):
    """A frame reference -> sheet2ani's frame: a name, a rect, or {"frame": name, ...options} ({"rect": ..., ...})."""
    frames = c["frames"]
    if isinstance(ref, str):
        return frames[ref]
    if isinstance(ref, dict) and "frame" in ref:
        return {"rect": frames[ref["frame"]], **{k: v for k, v in ref.items() if k != "frame"}}
    return ref


def _anim(c, a):
    return {k: ([_frame(c, f) for f in v] if k == "frames" else v) for k, v in a.items()}


def _anims(c, section):
    """A section's animations (null ones, "deliberately empty", left out: tools/anim_fallbacks.py)."""
    return {name: _anim(c, a) for name, a in (c.get(section) or {}).items() if a is not None}


def _remap(r):
    """"+N": colours 1-15 moved up by N (a UI sheet's palette row), else an explicit {slot: slot} map."""
    if isinstance(r, str) and r.startswith("+"):
        return {str(i): int(r[1:]) + i for i in range(1, 16)}
    return r


def _element(c, e):
    if "text" in e:  # a typed name tag (ui life_name): the HUD's letters, tools/hud_font.py
        import hud_font
        bad = hud_font.problems(e["text"])
        if bad:
            raise SystemExit(f"{c['folder'] / FILE}: ui life_name: {'; '.join(bad)}")
        out = hud_font.element(e["text"], e.get("pixel_colours"))
        out.update({k: v for k, v in e.items() if k not in ("text", "pixel_colours")})
        return out
    out = {}
    if "frame" in e:
        out["rect"] = c["frames"][e["frame"]]
    for k, v in e.items():
        if k != "frame":
            out[k] = _remap(v) if k == "remap" else v
    return out


def _elements(c, section):
    els = dict(c.get(section, {}))
    if section == "ui" and "life_name" not in els:  # no name tag given: his name, typed in the HUD's letters
        els["life_name"] = {"text": c["name"]}
    for name, e in els.items():
        if "text" in e and (section, name) != ("ui", "life_name"):
            raise SystemExit(f"{c['folder'] / FILE}: {section} {name}: only ui life_name can be typed (\"text\")")
    out = {name: None if (section, name) == ("ui", "sign_face") else _element(c, e) for name, e in els.items()}
    if section == "ui":  # the signpost face: a whole sign as drawn, or a head on the game's own board (sign_face_plan)
        plan = sign_face_plan(c)
        if plan:  # (in its place in the file's order, which the UI sheet packs in; added last when left out)
            out["sign_face"] = plan["element"] if plan["mode"] == "head" else _element(c, els["sign_face"])
            out["sign_face"].pop("own", None)
    return out


def _rect(c, ref, where):
    """A frame name or a rect [x, y, w, h] -> the rect."""
    if isinstance(ref, str):
        if ref not in c.get("frames", {}):
            raise SystemExit(f"{c['folder'] / FILE}: {where}: no frame named {ref!r}")
        return list(c["frames"][ref])
    if isinstance(ref, dict):  # ({"frame": NAME, ...} / {"rect": ..., ...}: an animation frame)
        return _rect(c, ref["frame"], where) if "frame" in ref else _rect(c, ref.get("rect"), where)
    if isinstance(ref, list) and len(ref) == 4 and all(isinstance(v, int) for v in ref):
        return list(ref)
    raise SystemExit(f"{c['folder'] / FILE}: {where}: {ref!r} is neither a frame name nor [x, y, w, h]")


def sign_face_plan(c, src=None):
    """How the end-of-act signpost face (ui "sign_face") is made, for the build, `noswap check` and the editor:

      {"head": FRAME_or_rect, "scale"?: "auto" | n}   a head from the sheet on the game's own board (tools/sign_face.py
                                                       board_face; "auto", the default, sign_face.auto_scale)
      {"head": ..., "flip": true}                      ... mirrored left-right (a sheet drawn facing left)
      {"frame" | "rect": ...}                          a whole sign drawn on the sheet (48x32), used as drawn; but one
                                                       that is clearly a head (its drawing smaller than 44x28) goes on
                                                       the board as a head ("detected")
      {..., "own": true}                               as drawn, whatever its size (also: any "remap", "scale", "base")
      left out                                         the top of the Stopped frame on the board ("default")

    Returns None (nothing to show: no sign_face and no Stopped frame), {"mode": "own"}, or {"mode": "head", "why":
    "head" | "detected" | "default", "head": the head's rect (its drawn part unless "trim": false), "scale", "auto",
    "element": the sheet2ani UI element}. S1, S2, CD, S3&K and Mania all take the face from that UI element."""
    import sign_face
    e = (c.get("ui") or {}).get("sign_face")
    where = "ui sign_face"

    def sheet():
        from PIL import Image
        return src if src is not None else Image.open(c["folder"] / c["sheet"]["file"]).convert("RGBA")
    background = {_hex(b) for b in c["sheet"].get("background", [])}
    scale = "auto"
    if e is None:
        stopped = (c.get("animations") or {}).get("Stopped") or {}
        if not stopped.get("frames"):
            return None
        head = sign_face.default_head(sheet(), _rect(c, stopped["frames"][0], "animations Stopped"), background)
        if not head:
            return None
        why = "default"
    elif not isinstance(e, dict):
        raise SystemExit(f"{c['folder'] / FILE}: {where}: must be an object")
    elif "head" in e:
        r = _rect(c, e["head"], where + " head")
        head = r if e.get("trim") is False else sign_face.drawn_box(sheet(), r, background)
        if not head:
            raise SystemExit(f"{c['folder'] / FILE}: {where}: the head {e['head']!r} is empty or off the sheet")
        scale = e.get("scale", "auto")
        why = "head"
    else:
        if e.get("own") or any(k in e for k in ("text", "remap", "scale", "base", "pixels")) or \
                not ("frame" in e or "rect" in e):
            return {"mode": "own"}
        r = _rect(c, e["frame"] if "frame" in e else e["rect"], where)
        box = r if e.get("trim") is False else sign_face.drawn_box(sheet(), r, background)
        if not box or sign_face.is_whole_sign(box[2], box[3]):
            return {"mode": "own"}
        head, why = box, "detected"
    auto = scale == "auto"
    if auto:
        scale = sign_face.auto_scale(head[2], head[3])
    elif not isinstance(scale, (int, float)) or isinstance(scale, bool) or \
            not sign_face.SCALE_RANGE[0] <= scale <= sign_face.SCALE_RANGE[1]:
        raise SystemExit(f"{c['folder'] / FILE}: {where}: scale must be \"auto\" or a number from "
                         f"{sign_face.SCALE_RANGE[0]} to {sign_face.SCALE_RANGE[1]} (got {scale!r})")
    flip = isinstance(e, dict) and e.get("flip") is True
    return {"mode": "head", "why": why, "head": head, "scale": scale, "auto": auto, "flip": flip,
            "element": sign_face.board_face(head, float(scale), flip)}


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _sheet(c):
    from PIL import Image
    return Image.open(c["folder"] / c["sheet"]["file"]).convert("RGB")


def key_colours(c):
    """Sheet colour -> palette slot: the shared ones (colours the base's slots already have), then the own ones."""
    p = c["palette"]
    return {**p.get("shared", {}), **{col: int(s) for s, col in p.get("own", {}).items()}}


def all_colours(c, src):
    """key_colours, plus (other_colours "nearest") every other colour on the sheet in the slot of its nearest key colour,
    so nothing is left to sheet2ani's guess."""
    keys = {_hex(col): s for col, s in key_colours(c).items()}
    out = dict(key_colours(c))
    if c["palette"].get("other_colours", "nearest") != "nearest":
        return out
    background = c["sheet"]["background"]
    for _, rgb in src.getcolors(1 << 16):
        col = "#%02x%02x%02x" % rgb
        if col not in out and col not in background:
            near = min(keys, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
            out[col] = keys[near]
    return out


def check_colours(c, src):
    """palette "strict": every colour in a frame (and so in any UI element cut from one) has a slot of its own."""
    if not c["palette"].get("strict"):
        return
    used = set()
    for x, y, w, h in c["frames"].values():
        used |= {"#%02x%02x%02x" % rgb for _, rgb in src.crop((x, y, x + w, y + h)).getcolors(1 << 16)}
    missing = used - set(key_colours(c)) - set(c["sheet"]["background"])
    if missing:
        sys.exit(f"{c['id']}: frame colours without a slot of their own: {sorted(missing)}")


# ---------------------------------------------------------------- what the pipeline consumes

def _extra(c):
    """The character's EXTRAS entry once extras.py has numbered it (its "file", Extra<n>)."""
    from extras import EXTRAS
    for e in EXTRAS:
        if Path(e.get("art")).resolve() == Path(c["folder"]).resolve():
            return e
    raise SystemExit(f"{c['folder']}: not in tools/extras.py's EXTRAS")


def config(c, game):
    """The sheet2ani config for "Sonic1" or "Sonic2" (what make_configs.py's config(game) returns), with the generic
    ball ("ball") and the fallback frames (tools/anim_fallbacks.py) in."""
    src = _sheet(c)
    check_colours(c, src)
    file = _extra(c)["file"]
    ex = REPO / "extracted" / game
    sheet = c["sheet"]
    raw = c  # (null animations survive _clean: they're the opt-outs)
    animations = _anims(c, "animations")
    empty = anim_fallbacks.opted_out(raw.get("animations"))
    if game == "Sonic2":
        animations.update(_anims(c, "animations_sonic2"))
        empty |= anim_fallbacks.opted_out(raw.get("animations_sonic2"))
        empty -= set(animations)
    appended = _anims(c, "ability_animations")
    if "melee" in ((c.get("abilities") or {}).get("abilities") or []) and "43" in appended and "44" not in appended:
        # the melee's air pose (slot 44): S1/S2 show it for Y in the air, and an empty slot draws the NEXT animation's
        # frames (Gilius' Earthquake boulders in 45). Without one of its own, the ground pose's frames, as S3&K, CD and
        # Mania show in the air (they ignore slot 44 without melee_air_reach)
        appended["44"] = dict(appended["43"], name=appended["43"].get("name", "Melee") + " Air")
    special =_anims(c, "special_stage") if game == "Sonic1" else {}
    source = sheet["file"]
    ball = ball_parts(c, src)
    if ball:  # the generic spin ball: its frames in a strip under a working copy of the sheet (generic_ball.py)
        source, src, parts = ball
        animations.update(parts["animations"])
        appended.update(parts["appended"])
        special.update(parts["special"])
    # fallback frames: a pose he has for each the base needs and he left out (tools/anim_fallbacks.py)
    base = c.get("base", "sonic")
    have = anim_fallbacks.pool(_anims(c, "animations"), _anims(c, "animations_sonic2"), animations,
                               appended=appended)
    filled, _, _ = anim_fallbacks.fill(animations, TEMPLATES[(game, base)]["filled"], have, empty)
    animations.update(filled)
    cfg = {"name": file, "credit": c["credits"]["full"], "source": source, "feet_y": sheet["feet_y"]}
    if "angled_halves" in sheet:  # (left out when the file leaves it out: build_s3k_art's default is false)
        cfg["angled_halves"] = sheet["angled_halves"]
    cfg.update({
           "background": sheet["background"], "palette": c["palette"].get("own", {}), "colours": all_colours(c, src),
           "template_ani": str(ex / "Data/Animations" / TEMPLATE_ANI[base]),
           "template_sheet": str(ex / "Data/Sprites/Players/Sonic1.gif"),  # palette reference only
           "out_dir": str(REPO / "mods" / "NoSwap" / (game + "u")),
           "animations": animations,
           "appended_animations": appended})
    if game == "Sonic1":
        # none given: his jump ball, centred (the Sonic 1 package needs the file)
        filled, _, _ = anim_fallbacks.fill_special(special, animations, anim_fallbacks.opted_out(raw.get("special_stage")))
        special.update(filled)
        if special:
            cfg["extra_anis"] = [{"name": f"{file}SS", "template_ani": str(ex / "Data/Animations/SonicSS.ani"),
                                  "animations": special}]
        cfg["ui"] = [{"name": f"{file}_UI", "manifest": f"{file}_ui.json", "elements": _elements(c, "ui"),
                      "out": f"build/{file}_UI.gif"},
                     {"name": f"{file}_Ending", "manifest": f"{file}_ending.json", "elements": _elements(c, "ending"),
                      "out": f"build/{file}_Ending.gif"}]
    if game == "Sonic2" and c.get("s3k_victory"):  # (S3&K reads the Sonic 2 config)
        cfg["s3k_victory"] = _anim(c, c["s3k_victory"])
    if game == "Sonic2" and c.get("snowboard"):  # (S3&K's Ice Cap snowboard poses: build_s3k_snowboard.py)
        cfg["snowboard"] = {k: [_frame(c, f) for f in v] for k, v in c["snowboard"].items() if not k.startswith("_")}
    if game == "Sonic2" and c.get("charge_palettes"):  # (a charge shot's flash, {phase: {slot: colour}}: abilities.charge_palettes)
        cfg["charge_palettes"] = {k: v for k, v in c["charge_palettes"].items() if not k.startswith("_")}
    variant_slots = [slot for slot, k in (("45", "melee_run"), ("46", "melee_up")) if (c.get("abilities") or {}).get(k)]
    if game == "Sonic2" and variant_slots:  # (melee_run / melee_up's frames: CD shows them after the melee's own in its
        cfg["cd_melee_variants"] = variant_slots  # one melee animation, 46: cd_config.py; build_soniccd.cd_variants)
    if ball:
        cfg["ball"] = "generic"  # (a marker, as generic_ball.apply's; sheet2ani ignores it)
        if game == "Sonic2":  # CD's names and S3&K's frame counts (cd_config.py, build_s3k_art.py read these)
            if parts["cd"]:
                cfg["cd_animations"] = parts["cd"]
            if parts["s3k"]:
                cfg["s3k_animations"] = parts["s3k"]
    return cfg


# ---------------------------------------------------------------- the generic spin ball ("ball")

def ball_settings(c):
    """The character's "ball" with its defaults filled in: {size (px), colours ("auto" or a dict), use_for}, or None."""
    b = c.get("ball")
    if not b:
        return None
    import generic_ball
    size = b.get("size", "medium")
    if size not in generic_ball.SIZES:
        raise SystemExit(f"{c['folder'] / FILE}: ball size must be one of {', '.join(generic_ball.SIZES)}")
    use_for = b.get("use_for", list(generic_ball.DEFAULT_USE_FOR))
    bad = [u for u in use_for if u not in generic_ball.USE_FOR]
    if bad:
        raise SystemExit(f"{c['folder'] / FILE}: ball use_for: {bad} (choose from {', '.join(generic_ball.USE_FOR)})")
    return {"size": generic_ball.SIZES[size], "colours": b.get("colours", "auto"), "use_for": use_for}


def frame_counts(c, src):
    """{key colour: pixels} over the frames his animations use (each frame once; all his frames when none is used yet),
    every sheet colour counted as the key colour it's drawn as."""
    mapping = all_colours(c, src)
    by_slot = {}
    for col, s in key_colours(c).items():
        by_slot.setdefault(s, col.lower())
    names = {f if isinstance(f, str) else f.get("frame") for sec in ("animations", "animations_sonic2")
             for a in (c.get(sec) or {}).values() if isinstance(a, dict) for f in a.get("frames", [])
             if isinstance(f, (str, dict))}
    rects = [r for n, r in c["frames"].items() if n in names] or list(c["frames"].values())
    background = {col.lower() for col in c["sheet"]["background"]}
    counts = {}
    for x, y, w, h in {tuple(r) for r in rects}:
        for n, rgb in src.crop((x, y, x + w, y + h)).getcolors(1 << 16) or []:
            col = "#%02x%02x%02x" % rgb[:3]
            if col in background or col not in mapping:
                continue
            key = by_slot.get(mapping[col])
            if key:
                counts[key] = counts.get(key, 0) + n
    return counts


def ball_colours(c, src=None):
    """The ball's 5 colours, {"outline", "dark", "mid", "light", "shine"} -> "#rrggbb": given, or ("auto") picked from
    his own palette (generic_ball.auto_colours). A given set may leave out the outline (generic_ball.outline_for)."""
    import generic_ball
    b = ball_settings(c)
    palette = [col.lower() for col in key_colours(c)]
    cols = b["colours"]
    if cols == "auto":
        return generic_ball.auto_colours(frame_counts(c, src or _sheet(c)), palette)
    cols = {k: v.lower() for k, v in cols.items()}
    shine = cols.get("shine") or max(palette, key=generic_ball._luma)  # (left out: his lightest colour)
    return generic_ball.colours(cols.get("outline"), cols["dark"], cols["mid"], cols["light"], shine, palette=palette)


def ball_parts(c, src):
    """None without a "ball"; else (the working sheet's path relative to the folder, the working sheet (RGB), the
    animations to set: generic_ball.animations_for). The working sheet is build/<id>_ball.png: the sheet with the
    ball's frames underneath (generic_ball.source_with_ball; the sheet itself is untouched)."""
    b = ball_settings(c)
    if not b:
        return None
    import generic_ball
    rel = f"build/{c['id']}_ball.png"
    specs = generic_ball.source_with_ball(src, ball_colours(c, src), c["sheet"]["background"][0], c["folder"] / rel,
                                          size=b["size"])
    from PIL import Image
    return rel, Image.open(c["folder"] / rel).convert("RGB"), generic_ball.animations_for(specs, b["use_for"])


def write_configs(folder):
    """Write the folder's Sonic 1 and Sonic 2 sheet2ani configs (<id>.json, <id>_s2.json), as make_configs.py does."""
    c = load(folder)
    for game, out in (("Sonic1", f"{c['id']}.json"), ("Sonic2", f"{c['id']}_s2.json")):
        (c["folder"] / out).write_text(json.dumps(config(c, game), indent=1))
        print("wrote", out)


def extras_entry(folder):
    """The character's tools/extras.py EXTRAS entry (before extras.py fills in the defaults and numbers it)."""
    c = load(folder)
    flags = {**FLAG_DEFAULTS, **c.get("flags", {})}
    ball = c.get("ball") if isinstance(c.get("ball"), dict) else {}
    if "Rolling" in (ball.get("use_for") or ()):  # (the ball as his rolling curl: slot 49, "roll"; checked in config)
        flags["roll"] = True
    e = {"art": c["folder"], "name": c["name"], "super": flags["super"], "drop_dash": flags["drop_dash"],
         "palette": {int(s): int(col.lstrip("#"), 16) for s, col in c["palette"].get("own", {}).items()}}
    if c.get("base", "sonic") != "sonic":
        e["base"] = c["base"]
    for k in ("roll", "no_roll", "private", "crossover"):
        if flags[k]:
            e[k] = True
    if c.get("card"):  # (a crop of a sheet; or {"scale": n} alone: the Stopped frame n times, build_origins_menu.card_picture)
        e["card"] = {**c["card"], "sheet": c["folder"] / c["card"]["sheet"]} if "sheet" in c["card"] else dict(c["card"])
    e["credit_short"] = c["credits"].get("short", "")
    e["_key"] = c["key"]  # (extras.py makes it the entry's "key" and numbers it by it: tools/registry.py)
    return e


def abilities_entry(folder):
    """The character's tools/abilities.py ABILITIES entry: its moves and their numbers. Its S3&K sound fields' "own:<name>"
    (its own sounds, character.json "sounds") become their Data/SoundFX paths (tools/own_sounds.py)."""
    c = load(folder)
    entry = c.get("abilities", {"abilities": []})
    if c.get("sounds"):
        import own_sounds
        entry = own_sounds.resolve(entry, c["id"], set(own_sounds.declared(c)))
    return entry


def mania_folders():
    """Art folder names whose character.json enables Mania, in name order."""
    return sorted(f.name for f in folders() if json.loads((f / FILE).read_text()).get("games", {}).get("mania"))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    for arg in sys.argv[1:]:
        write_configs(arg)
