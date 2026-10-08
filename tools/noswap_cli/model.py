"""One view of a character for the `noswap` commands, whichever way it's defined:

- "json": a character.json (docs/character-json.md), read as tools/character_json.py reads it;
- "legacy": an old-style make_configs.py character, read from the sheet2ani configs its make_configs.py wrote
  (<stem>.json for Sonic 1, <stem>_s2.json for Sonic 2) plus its tools/extras.py and tools/abilities.py entries.

Frames are kept as sheet2ani specs (a rect [x, y, w, h], or a dict: {"rect", "flip", "rotate", ...} or {"layers"}), so
everything downstream (checks, previews) sees exactly what the build cuts.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
TOOLS = REPO / "tools"
TESTMODS = Path(os.environ.get("NOSWAP_TESTMODS") or REPO / "testmods")  # (the Creator Kit: its characters folder)
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import character_json  # noqa: E402

UI_KEYS = ("life_icon", "life_name", "monitor_1up", "sign_face", "mini_1", "mini_2")
ENDING_KEYS = ("end_idle", "end_pose_1", "end_pose_2", "end_pose_3", *(f"good_{n}" for n in range(1, 7)))


class CharacterError(Exception):
    """The folder isn't a character the tools can read (the message says why and what to do)."""


def resolve_folder(arg):
    """A character folder from a command-line argument: a path, or a bare name under testmods/."""
    p = Path(arg).expanduser()
    if p.is_dir():
        return p.resolve()
    if "/" not in str(arg) and (TESTMODS / arg).is_dir():
        return (TESTMODS / arg).resolve()
    raise CharacterError(f"{arg}: no such character folder (give a path, or a folder name under {TESTMODS})")


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def frame_rects(spec):
    """Every sheet rect a frame spec reads (a layered frame has several)."""
    if isinstance(spec, list):
        return [spec]
    if isinstance(spec, dict):
        if "layers" in spec:
            return [l["rect"] for l in spec["layers"]]
        if "rect" in spec:
            return [spec["rect"]]
    return []


def frame_label(spec, names):
    """A short label for a frame spec: its name if it's a named rect, else its rect."""
    if isinstance(spec, dict):
        base = frame_label(spec.get("rect"), names) if "rect" in spec else "layered"
        opts = [k for k in ("flip", "rotate", "circle") if spec.get(k)]
        if isinstance(spec.get("offset"), list) and any(spec["offset"]):
            opts.append("offset %s,%s" % tuple(spec["offset"][:2]))
        return base + ("(" + ",".join(opts) + ")" if opts else "")
    return names.get(tuple(spec), "[%d,%d,%d,%d]" % tuple(spec)) if spec else "?"


class Character:
    """kind, folder, id, name, base, sheet (Path), background (["#rrggbb"]), feet_y, frames ({name: rect}, json only),
    anims {"Sonic1": {name: anim}, "Sonic2": {...}} (frames resolved to specs), ability_anims {slot: anim},
    special_stage {name: anim}, s3k_victory, ui {key: element}, ending {key: element}, own ({slot: "#rrggbb"}),
    colours ({"#rrggbb": slot}: the explicit map), other_colours, strict, abilities (the ABILITIES entry), credits,
    games, flags, card, extra (its tools/extras.py entry, or None), raw (the character.json as written, json only),
    refs (json only: every frame name reference, [(where, name)]), renamed (older names migrated as it loaded)."""

    def __init__(self, folder):
        self.folder = folder
        self.id = folder.name
        self.extra = None
        self.refs = []
        self.renamed = []  # [(old, new)]: older move / field names the load migrated (character_json.RENAMED)
        self.raw = None
        self.frames = {}
        self.snowboard = {}  # (S3&K Ice Cap snowboard poses: {"ground" / "air" / "sidewind": [specs]})

    @property
    def frame_names(self):
        return {tuple(r): n for n, r in self.frames.items()}

    def colour_map(self):
        """sheet colour (rgb) -> slot, as the build maps it (other_colours "nearest" fills in every sheet colour)."""
        return {_hex(c): s for c, s in self.colours.items()}

    def used_specs(self):
        """[(where, spec)] for every frame the player sprites use."""
        out = []
        for game, anims in self.anims.items():
            for name, a in anims.items():
                out += [(f"{game} {name}", f) for f in a["frames"]]
        for slot, a in self.ability_anims.items():
            out += [(f"ability {slot} {a.get('name', '')}", f) for f in a["frames"]]
        for name, a in self.special_stage.items():
            out += [(f"special stage {name}", f) for f in a["frames"]]
        if self.s3k_victory:
            out += [("s3k_victory", f) for f in self.s3k_victory["frames"]]
        for key, frames in (self.snowboard or {}).items():
            out += [(f"snowboard {key}", f) for f in frames]
        return out

    def anchors(self):
        """{json key of a frame spec: set of anchors it's drawn with ("feet" / "center")}."""
        out = {}
        groups = [a for anims in self.anims.values() for a in anims.values()]
        groups += list(self.ability_anims.values()) + list(self.special_stage.values())
        for a in groups:
            for f in a.get("frames", []):
                out.setdefault(json.dumps(f, sort_keys=True), set()).add(a.get("anchor", "feet"))
        return out

    def registered(self):
        """Its tools/extras.py entry (None: not registered yet)."""
        try:
            from extras import EXTRAS
        except SystemExit as e:  # (extras.py reads every character.json: a broken one stops the import)
            raise CharacterError(f"tools/extras.py could not load: {e}")
        return next((e for e in EXTRAS if Path(e["art"]).resolve() == self.folder), None)


# ---------------------------------------------------------------- character.json

def _resolve(c, ref, where, refs):
    """A frame reference -> a sheet2ani frame spec, as character_json._frame does (names recorded for the checks)."""
    frames = c.get("frames", {})
    if isinstance(ref, str):
        refs.append((where, ref))
        return frames.get(ref)
    if isinstance(ref, dict) and "frame" in ref:
        refs.append((where, ref["frame"]))
        r = frames.get(ref["frame"])
        return {"rect": r, **{k: v for k, v in ref.items() if k != "frame"}} if r else None
    return ref


def _anims(c, section, refs, prefix):
    out = {}
    for name, a in c.get(section, {}).items():
        if not isinstance(a, dict):
            continue
        frames = [_resolve(c, f, f"{prefix}{name}", refs) for f in a.get("frames", [])]
        out[name] = {**a, "frames": [f for f in frames if f is not None]}
    return out


def _elements(c, section, refs):
    out = {}
    for key, e in c.get(section, {}).items():
        if not isinstance(e, dict):
            continue
        e = dict(e)
        if isinstance(e.get("head"), str):  # (ui sign_face: a head on the official board, character_json.sign_face_plan)
            refs.append((f"{section} {key} head", e["head"]))
        if "frame" in e:
            refs.append((f"{section} {key}", e["frame"]))
            r = c.get("frames", {}).get(e.pop("frame"))
            if r is None:
                continue
            e["rect"] = r
        if isinstance(e.get("remap"), str):
            e["remap"] = character_json._remap(e["remap"])
        out[key] = e
    return out


def load_json(folder):
    path = folder / character_json.FILE
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise CharacterError(f"{path}: not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})")
    c = character_json._clean(raw)
    ch = Character(folder)
    ch.kind = "json"
    ch.raw = raw
    ch.frames = {k: v for k, v in c.get("frames", {}).items() if isinstance(v, list)}
    ch.name = c.get("name", "?")
    ch.base = c.get("base", "sonic")
    sheet = c.get("sheet", {})
    ch.sheet = folder / sheet.get("file", "?")
    ch.background = sheet.get("background", [])
    ch.feet_y = sheet.get("feet_y", 20)
    refs = ch.refs
    s1 = _anims(c, "animations", refs, "animations ")
    s2 = dict(s1)
    s2.update(_anims(c, "animations_sonic2", refs, "animations_sonic2 "))
    ch.anims = {"Sonic1": s1, "Sonic2": s2}
    ch.ability_anims = _anims(c, "ability_animations", refs, "ability_animations ")
    ch.special_stage = _anims(c, "special_stage", refs, "special_stage ")
    v = c.get("s3k_victory")
    ch.s3k_victory = None
    if isinstance(v, dict):
        frames = [_resolve(c, f, "s3k_victory", refs) for f in v.get("frames", [])]
        ch.s3k_victory = {**v, "frames": [f for f in frames if f is not None]}
    ch.snowboard = {}
    for key, frames in (c.get("snowboard") or {}).items():
        if isinstance(frames, list):
            frames = [_resolve(c, f, f"snowboard {key}", refs) for f in frames]
            ch.snowboard[key] = [f for f in frames if f is not None]
    ui = dict(c.get("ui") or {})
    if "life_name" not in ui and isinstance(c.get("name"), str):  # (character_json._elements: his name, typed)
        ui["life_name"] = {"text": c["name"], "default": True}
    ch.ui = _elements({**c, "ui": ui}, "ui", refs)
    ch.ending = _elements(c, "ending", refs)
    p = c.get("palette", {})
    ch.own = {int(s): col.lower() for s, col in p.get("own", {}).items() if str(s).isdigit()}
    ch.colours = {**{k.lower(): v for k, v in p.get("shared", {}).items()}, **{col: s for s, col in ch.own.items()}}
    ch.other_colours = p.get("other_colours", "nearest")
    ch.strict = bool(p.get("strict"))
    ch.abilities = c.get("abilities", {"abilities": []})
    ch.renamed = character_json.migrate_abilities(ch.abilities)  # (older names: popgun_reach -> melee_reach)
    ch.credits = c.get("credits", {})
    ch.games = c.get("games", {})
    ch.flags = c.get("flags", {})
    ch.card = c.get("card")
    ch.cleaned = c
    return ch


# ---------------------------------------------------------------- legacy (make_configs.py)

def load_legacy(folder):
    s2 = sorted(p for p in folder.glob("*_s2.json"))
    if not s2:
        raise CharacterError(
            f"{folder}: no character.json and no sheet2ani configs (<id>.json / <id>_s2.json). Run its make_configs.py "
            f"(or `noswap build {folder.name}`) first, or write a character.json (docs/character-json.md).")
    stem = s2[0].name[:-len("_s2.json")]
    cfg2 = json.loads(s2[0].read_text())
    p1 = folder / f"{stem}.json"
    cfg1 = json.loads(p1.read_text()) if p1.exists() else cfg2
    ch = Character(folder)
    ch.kind = "legacy"
    ch.configs = {"Sonic1": cfg1, "Sonic2": cfg2}
    ch.extra = ch.registered()
    ch.name = ch.extra["name"] if ch.extra else "?"
    ch.base = ch.extra["base"] if ch.extra else "sonic"
    ch.sheet = folder / cfg2["source"]
    ch.background = cfg2["background"]
    ch.feet_y = cfg2.get("feet_y", 20)
    ch.anims = {"Sonic1": cfg1["animations"], "Sonic2": cfg2["animations"]}
    ch.ability_anims = cfg2.get("appended_animations", {})
    ch.special_stage = {}
    for x in cfg1.get("extra_anis", []):
        ch.special_stage.update(x.get("animations", {}))
    ch.s3k_victory = cfg2.get("s3k_victory")
    ch.snowboard = cfg2.get("snowboard") or {}
    ch.ui, ch.ending = {}, {}
    uis = cfg1.get("ui", [])
    for ui in uis if isinstance(uis, list) else [uis]:
        target = ch.ending if ui.get("name", "").endswith("_Ending") else ch.ui
        target.update(ui.get("elements", {}))
    ch.own = {int(s): col.lower() for s, col in cfg2.get("palette", {}).items()}
    ch.colours = {k.lower(): v for k, v in cfg2.get("colours", {}).items()}
    ch.other_colours = "explicit"
    ch.strict = False
    try:
        import abilities as ab
        ch.abilities = ab.ABILITIES.get(ch.extra["id"], {"abilities": []}) if ch.extra else {"abilities": []}
    except SystemExit as e:
        raise CharacterError(f"tools/abilities.py could not load: {e}")
    src = folder / "SOURCE.txt"
    ch.credits = {"full": cfg2.get("credit", ""), "short": (ch.extra or {}).get("credit_short", ""),
                  "terms": src.read_text() if src.exists() else ""}
    try:
        from build_mania_art import MANIA_ENABLED
        ch.games = {"mania": ch.id in MANIA_ENABLED}
    except Exception:  # (the Mania build needs the extracted Mania data; without it, unknown)
        ch.games = {}
    ch.flags = {k: (ch.extra or {}).get(k, False) for k in character_json.FLAGS}
    ch.card = (ch.extra or {}).get("card")
    # name the distinct rects in first-use order, for labels
    for _, spec in ch.used_specs() + [(k, e) for k, e in {**ch.ui, **ch.ending}.items()]:
        for r in frame_rects(spec if not isinstance(spec, dict) or "rect" in spec or "layers" in spec else None):
            if r and tuple(r) not in ch.frame_names:
                ch.frames[f"#{len(ch.frames) + 1}"] = r
    return ch


def load(folder):
    folder = Path(folder).resolve()
    if (folder / character_json.FILE).exists():
        ch = load_json(folder)
        try:
            ch.extra = ch.registered()
        except CharacterError:
            ch.extra = None
        return ch
    if (folder / "make_configs.py").exists() or list(folder.glob("*_s2.json")):
        return load_legacy(folder)
    raise CharacterError(f"{folder}: neither a character.json nor a make_configs.py here (docs/character-json.md)")
