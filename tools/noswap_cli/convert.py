"""`noswap convert <folder>`: an old make_configs.py character -> character.json, proven identical.

1. Runs the folder's make_configs.py config("Sonic1") / config("Sonic2") in-process (its top level runs: it's the
   character's own code, which only reads the sheet) and reads its tools/extras.py and tools/abilities.py entries.
2. Writes the same thing as a character.json: frames named by first use, the colour map split into own / shared
   colours (other_colours "nearest" when the module has KEY_COLOURS and the rest is its nearest-colour fill, else
   "guess"), the moves with their comments kept as "_notes".
3. Proves it before writing anything: tools/character_json.py must turn it back into the very same Sonic 1 and Sonic 2
   sheet2ani configs (equal, and the same JSON text), the same EXTRAS entry and the same ABILITIES entry. Anything it
   can't express (a Python trick: composited frames, generated art, extra config keys) stops the conversion.
4. --wire switches the build over: make_configs.py -> make_configs.legacy.py and a three-line shim in its place;
   tools/extras.py and tools/abilities.py call the loader for him (their comments move to the character.json).
   Every file it touches is backed up first (<temp dir>/noswap-convert/<id>/); `--unwire` puts them back exactly.
Then rebuild and compare every output (docs/toolset-cli.md, "Proving a conversion").
"""
import copy
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .model import REPO, TOOLS, CharacterError

OK, FAILED = 0, 1
STANDARD_KEYS = {"name", "credit", "source", "feet_y", "angled_halves", "background", "palette", "colours",
                 "template_ani", "template_sheet", "out_dir", "animations", "appended_animations", "extra_anis", "ui",
                 "s3k_victory", "snowboard"}
ELEMENT_KEYS = {"rect", "trim", "remap"}
FLAG_KEYS = ("super", "drop_dash", "roll", "no_roll", "private", "crossover")
SHIM = '''#!/usr/bin/env python3
"""Writes {name}'s sheet2ani configs ({stem}.json for Sonic 1, {stem}_s2.json for Sonic 2) from the character.json
(docs/character-json.md, tools/character_json.py). Everything about the character lives in character.json; this file only
keeps build_art.py's "run the folder's make_configs.py" step working. The hand-written version it replaced is
make_configs.legacy.py (byte-identical output; converted by tools/noswap.py convert).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import character_json  # noqa: E402

if __name__ == "__main__":
    character_json.write_configs(HERE)
'''


class Unsupported(Exception):
    pass


def backup_dir(cid):
    return Path(tempfile.gettempdir()) / "noswap-convert" / cid


# ---------------------------------------------------------------- reading the old character

def _module(path):
    spec = importlib.util.spec_from_file_location(f"noswap_legacy_{path.parent.name.replace('-', '_')}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _legacy(folder):
    import character_json as cj
    from extras import EXTRAS
    import abilities as ab
    extra = next((e for e in EXTRAS if Path(e["art"]).resolve() == folder), None)
    if extra is None:
        raise Unsupported(f"{folder.name} isn't in tools/extras.py")
    src = folder / "make_configs.py"
    if (folder / cj.FILE).exists() and (folder / "make_configs.legacy.py").exists():
        src = folder / "make_configs.legacy.py"
    if not src.exists():
        raise Unsupported(f"{folder.name} has no make_configs.py (its configs are written by hand)")
    mod = _module(src)
    if not hasattr(mod, "config"):
        raise Unsupported(f"{src.name} has no config(game) function")
    cfgs = {g: json.loads(json.dumps(mod.config(g))) for g in ("Sonic1", "Sonic2")}
    return mod, cfgs, extra, ab.ABILITIES.get(extra["id"])


# ---------------------------------------------------------------- building the character.json

def _hexify(v, key=""):
    """Big round ints (16.16 speeds) as hex strings, as a creator would write them; lossless (the loader reads them back)."""
    if isinstance(v, dict):
        return {k: _hexify(x, k) for k, x in v.items()}
    if isinstance(v, list):
        return [_hexify(x, key) for x in v]
    if isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 0x1000 and v % 0x400 == 0:
        return ("-0x%x" % -v) if v < 0 else ("0x%x" % v)
    return v


def _slug(name):
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_") or "FRAME"


class Namer:
    """Names each distinct rect by its first use: WALKING1, WALKING2, ... (one frame: STOPPED)."""

    def __init__(self):
        self.frames = {}  # name -> rect
        self.by_rect = {}

    def name_all(self, label, rects):
        base = _slug(label)
        new = [r for r in rects if tuple(r) not in self.by_rect]
        new = list(dict.fromkeys(tuple(r) for r in new))
        for i, r in enumerate(new, 1):
            name = base if len(new) == 1 else f"{base}{i}"
            while name in self.frames:
                name += "_"
            self.frames[name] = list(r)
            self.by_rect[r] = name

    def ref(self, spec):
        if isinstance(spec, list):
            return self.by_rect[tuple(spec)]
        if isinstance(spec, dict) and "rect" in spec and "layers" not in spec:
            return {"frame": self.by_rect[tuple(spec["rect"])], **{k: v for k, v in spec.items() if k != "rect"}}
        return spec  # (layered frames pass through as written)


def _rects_of(frames):
    return [f if isinstance(f, list) else f["rect"] for f in frames
            if isinstance(f, list) or (isinstance(f, dict) and "rect" in f and "layers" not in f)]


def _anim(namer, a):
    return {k: ([namer.ref(f) for f in v] if k == "frames" else v) for k, v in a.items()}


def _remap_out(r):
    plus = {str(i): 128 + i for i in range(1, 16)}
    return "+128" if r == plus else r


def _credits(folder, cfg, extra):
    src = folder / "SOURCE.txt"
    text = src.read_text() if src.exists() else ""
    url = re.search(r"https?://\S+", text + " " + cfg.get("credit", ""))
    quote = re.search(r"on the sheet:\s*\"([^\"]+)\"", text)
    short = extra.get("credit_short", "")
    artists = [a.strip() for a in re.split(r"\s*(?:&|,| and )\s*", short.split(":", 1)[-1]) if a.strip()] if short else []
    out = {"short": short, "full": cfg.get("credit", ""), "artists": artists, "url": url.group(0) if url else "",
           "terms": quote.group(1) if quote else ""}
    if text:
        out["_source_txt"] = "SOURCE.txt (kept in the folder) has the sheet's full story: " + " ".join(text.split())[:400]
    return out


def build_json(folder, mod, cfgs, extra, abilities):
    s1, s2 = cfgs["Sonic1"], cfgs["Sonic2"]
    extra_keys = (set(s1) | set(s2)) - STANDARD_KEYS
    if extra_keys:
        raise Unsupported(f"its configs use {sorted(extra_keys)}, which character.json can't express yet")
    for g, cfg in cfgs.items():
        if cfg["name"] != extra["file"]:
            raise Unsupported(f"its {g} config is named {cfg['name']}, but it's {extra['file']} in tools/extras.py")
    for k in ("source", "feet_y", "background", "palette", "colours", "credit"):
        if s1.get(k) != s2.get(k):
            raise Unsupported(f"its Sonic 1 and Sonic 2 configs differ in {k!r}")
    if s1["appended_animations"] != s2["appended_animations"]:
        raise Unsupported("its Sonic 1 and Sonic 2 ability animations differ")
    shared_names = [n for n in s1["animations"] if n in s2["animations"]]
    if any(s1["animations"][n] != s2["animations"][n] for n in shared_names):
        raise Unsupported("an animation differs between its Sonic 1 and Sonic 2 configs")
    only_s1 = [n for n in s1["animations"] if n not in s2["animations"]]
    if only_s1:
        raise Unsupported(f"Sonic 1-only animations ({only_s1}) can't be expressed yet")
    if list(s2["animations"])[:len(s1["animations"])] != list(s1["animations"]):
        raise Unsupported("its Sonic 2 animations aren't Sonic 1's followed by Sonic 2's own")
    ss = s1.get("extra_anis", [])
    if len(ss) > 1 or (ss and ss[0]["name"] != f"{extra['file']}SS"):
        raise Unsupported("extra .ani files other than the special stage's")
    uis = s1.get("ui", [])
    if [u.get("name") for u in uis] != [f"{extra['file']}_UI", f"{extra['file']}_Ending"]:
        raise Unsupported("its UI sheets aren't the standard two (UI and Ending)")
    for u in uis:
        for k, e in u["elements"].items():
            if set(e) - ELEMENT_KEYS:
                raise Unsupported(f"UI element {k} uses {sorted(set(e) - ELEMENT_KEYS)} (drawn or pasted art)")

    namer = Namer()
    for name, a in s2["animations"].items():
        namer.name_all(name, _rects_of(a["frames"]))
    for slot, a in s2["appended_animations"].items():
        namer.name_all(a.get("name", f"slot {slot}"), _rects_of(a["frames"]))
    for x in ss:
        for name, a in x["animations"].items():
            namer.name_all(name, _rects_of(a["frames"]))
    if s2.get("s3k_victory"):
        namer.name_all("victory", _rects_of(s2["s3k_victory"]["frames"]))
    for key, frames in (s2.get("snowboard") or {}).items():
        namer.name_all(f"snowboard_{key}", _rects_of(frames))

    # colours: own (the config's palette), shared (the rest of the key colours), and how the others were filled
    own = {s: col for s, col in s1.get("palette", {}).items()}
    colours = s1["colours"]
    key = getattr(mod, "KEY_COLOURS", None)
    if key is not None and all(colours.get(c) == s for c, s in key.items()):
        mode, keyed = "nearest", dict(key)
    else:
        mode, keyed = "guess", dict(colours)
    own_cols = {col.lower(): int(s) for s, col in own.items()}
    shared = {c: s for c, s in keyed.items() if not (c.lower() in own_cols and own_cols[c.lower()] == s)}

    c = {"format": "noswap-character/1",
         "_about": f"Converted from make_configs.py (kept as make_configs.legacy.py) by tools/noswap.py convert; "
                   f"docs/character-json.md. Keys starting with _ are comments.",
         "id": folder.name, "name": extra["name"], "full_name": extra["name"].title(),
         "credits": _credits(folder, s1, extra),
         "sheet": {"file": s1["source"], "background": s1["background"], "feet_y": s1["feet_y"]}}
    if "angled_halves" in s1:
        c["sheet"]["angled_halves"] = s1["angled_halves"]
    c["base"] = extra.get("base", "sonic")
    c["flags"] = {k: bool(extra.get(k, False)) for k in FLAG_KEYS}
    card = extra.get("card")
    if card:
        sheet = Path(card["sheet"])
        try:
            rel = str(sheet.resolve().relative_to(folder))
        except ValueError:
            import os
            rel = os.path.relpath(sheet, folder)
        c["card"] = {**card, "sheet": rel}
    else:
        c["card"] = None
    from build_mania_art import MANIA_ENABLED
    c["games"] = {"sonic1": True, "sonic2": True, "soniccd": True, "s3k": True, "mania": folder.name in MANIA_ENABLED}
    c["palette"] = {"own": own, "shared": shared, "other_colours": mode, "strict": False}
    c["frames"] = namer.frames
    c["animations"] = {n: _anim(namer, a) for n, a in s1["animations"].items()}
    c["animations_sonic2"] = {n: _anim(namer, a) for n, a in s2["animations"].items() if n not in s1["animations"]}
    c["ability_animations"] = {s: _anim(namer, a) for s, a in s2["appended_animations"].items()}
    if ss:
        c["special_stage"] = {n: _anim(namer, a) for n, a in ss[0]["animations"].items()}
    if s2.get("s3k_victory"):
        c["s3k_victory"] = _anim(namer, s2["s3k_victory"])
    if s2.get("snowboard"):
        c["snowboard"] = {k: _anim(namer, {"frames": v})["frames"] for k, v in s2["snowboard"].items()}
    for u, section in zip(uis, ("ui", "ending")):
        out = {}
        for k, e in u["elements"].items():
            r = tuple(e["rect"])
            el = {"frame": namer.by_rect[r]} if r in namer.by_rect else {"rect": e["rect"]}
            for kk, v in e.items():
                if kk != "rect":
                    el[kk] = _remap_out(v) if kk == "remap" else v
            out[k] = el
        c[section] = out
    c["abilities"] = _hexify(copy.deepcopy(abilities)) if abilities is not None else {"abilities": []}
    return c


# ---------------------------------------------------------------- proving it

def _entry_view(e):
    """The parts of an EXTRAS entry a character defines (after extras.py fills in the defaults)."""
    e = dict(e)
    if isinstance(e.get("palette"), str):
        cfg = json.loads((Path(e["art"]) / e["palette"]).read_text())
        e["palette"] = {int(s): int(col.lstrip("#"), 16) for s, col in cfg.get("palette", {}).items()}
    view = {"art": str(Path(e["art"]).resolve()), "name": e["name"], "palette": e.get("palette", {}),
            "base": e.get("base", "sonic"), "credit_short": e.get("credit_short", "")}
    for k in FLAG_KEYS:
        view[k] = bool(e.get(k, False))
    card = e.get("card")
    view["card"] = {**card, "sheet": str(Path(card["sheet"]).resolve())} if card else None
    return view


def prove(folder, c, cfgs, extra, abilities):
    """([what differs], [notes]): nothing differs if the character.json gives back exactly the old configs and entries."""
    import character_json as cj
    cleaned = cj._clean(json.loads(json.dumps(c)))
    cleaned["folder"] = folder
    problems, notes = [], []
    for g in ("Sonic1", "Sonic2"):
        got = json.loads(json.dumps(cj.config(cleaned, g)))
        if got != cfgs[g]:
            keys = sorted(k for k in set(got) | set(cfgs[g]) if got.get(k) != cfgs[g].get(k))
            problems.append(f"{g} config differs in {keys}")
        elif json.dumps(cj.config(cleaned, g), indent=1) != json.dumps(cfgs[g], indent=1):
            notes.append(f"{g} config: equal, but its JSON text differs (only the order of keys; sheet2ani reads it "
                         "the same, and the rebuild comparison proves the outputs)")
    real_load = cj.load
    cj.load = lambda f: cleaned  # (extras_entry / abilities_entry read the file; give them this one)
    try:
        new_extra = cj.extras_entry(folder)
        new_ab = cj.abilities_entry(folder)
    finally:
        cj.load = real_load
    if _entry_view(new_extra) != _entry_view(extra):
        a, b = _entry_view(new_extra), _entry_view(extra)
        problems.append(f"EXTRAS entry differs in {sorted(k for k in a if a[k] != b.get(k))}")
    if new_ab != (abilities if abilities is not None else {"abilities": []}):
        problems.append("ABILITIES entry differs")
    return problems, notes


# ---------------------------------------------------------------- wiring

def _block(lines, start, opener="{", closer="}"):
    """The index of the line closing the bracket opened on lines[start]."""
    depth = 0
    for i in range(start, len(lines)):
        code = lines[i].split("#", 1)[0]
        depth += code.count(opener) - code.count(closer)
        if depth == 0 and i >= start:
            return i
    raise Unsupported("unbalanced brackets")


def _comments(text):
    return [m.strip() for m in re.findall(r"#\s?(.*)", text) if m.strip()]


def wire(folder, c):
    """Switch the build over; returns the notes to merge into character.json (the moved comments)."""
    cid = folder.name
    bk = backup_dir(cid)
    bk.mkdir(parents=True, exist_ok=True)
    extras_py, abilities_py = TOOLS / "extras.py", TOOLS / "abilities.py"
    for p in (extras_py, abilities_py, folder / "make_configs.py"):
        shutil.copy2(p, bk / p.name)
    notes = {}
    # tools/extras.py: the entry -> character_json.extras_entry(...)
    text = (bk / "extras.py").read_text()
    lines = text.split("\n")
    art = f'"art": REPO / "testmods" / "{cid}",'
    at = [i for i, l in enumerate(lines) if l.strip() == art]
    if len(at) != 1:
        raise Unsupported(f"tools/extras.py: expected one {art} line, found {len(at)}")
    start = at[0] - 1
    if lines[start].strip() != "{":
        raise Unsupported(f"tools/extras.py: the entry for {cid} doesn't start with a lone '{{' line")
    end = _block(lines, start)
    notes["extras"] = _comments("\n".join(lines[start:end + 1]))
    indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
    new = [f"{indent}# {extra_name(c)}: everything (name, flags, palette, credit) from testmods/{cid}/character.json "
           f"(tools/character_json.py)", f'{indent}character_json.extras_entry(REPO / "testmods" / "{cid}"),']
    lines[start:end + 1] = new
    credit = [i for i, l in enumerate(lines) if re.match(rf'\s+"{re.escape(cid)}": "Sprites:', l)]
    if len(credit) == 1:
        del lines[credit[0]]
    new_extras = "\n".join(lines)
    # tools/abilities.py: ID: {...} -> ID: character_json.abilities_entry(...)
    from extras import EXTRAS
    xid = next(e["id"] for e in EXTRAS if Path(e["art"]).resolve() == folder)
    text = (bk / "abilities.py").read_text()
    lines = text.split("\n")
    at = [i for i, l in enumerate(lines) if re.match(rf"    {xid}: \{{", l)]
    if len(at) != 1:
        raise Unsupported(f"tools/abilities.py: expected one '    {xid}: {{' line, found {len(at)}")
    start = at[0]
    end = _block(lines, start)
    notes["abilities"] = _comments("\n".join(lines[start:end + 1]))
    lines[start:end + 1] = [f'    {xid}: character_json.abilities_entry(REPO / "testmods" / "{cid}"),']
    new_abilities = "\n".join(lines)
    # (both edits worked out before either file is written; re-read just before writing, so a change someone else made
    # in the meantime stops it rather than being overwritten)
    if extras_py.read_text() != (bk / "extras.py").read_text() or abilities_py.read_text() != (bk / "abilities.py").read_text():
        raise Unsupported("tools/extras.py or tools/abilities.py changed while converting: run it again")
    extras_py.write_text(new_extras)
    abilities_py.write_text(new_abilities)
    # make_configs.py -> make_configs.legacy.py, and the shim
    (folder / "make_configs.py").rename(folder / "make_configs.legacy.py")
    stem = next(folder.glob("*_s2.json")).name[:-len("_s2.json")]
    (folder / "make_configs.py").write_text(SHIM.format(name=extra_name(c), stem=stem))
    (folder / "make_configs.py").chmod(0o755)
    return notes


def extra_name(c):
    return c.get("full_name") or c["name"].title()


def unwire(folder):
    """Put back exactly what wire() changed (from its backups) and remove the character.json."""
    bk = backup_dir(folder.name)
    if not (bk / "extras.py").exists():
        raise CharacterError(f"no backups for {folder.name} in {bk}")
    shutil.copy2(bk / "extras.py", TOOLS / "extras.py")
    shutil.copy2(bk / "abilities.py", TOOLS / "abilities.py")
    shutil.copy2(bk / "make_configs.py", folder / "make_configs.py")
    for p in (folder / "make_configs.legacy.py", folder / "character.json"):
        p.unlink(missing_ok=True)


def pretty(v, indent=0, width=118):
    """JSON a person can read: short lists and small objects on one line (rects, colours, frame lists), the rest nested."""
    flat = json.dumps(v, ensure_ascii=False, separators=(", ", ": "))
    if not isinstance(v, (dict, list)) or len(flat) + indent <= width and (
            isinstance(v, list) or all(not isinstance(x, (dict, list)) or len(json.dumps(x)) < 40 for x in v.values())):
        return flat
    pad = " " * (indent + 2)
    if isinstance(v, list):
        if all(not isinstance(x, (dict, list)) or (isinstance(x, list) and len(json.dumps(x)) < 40) for x in v):
            lines, line = [], ""
            for x in v:  # (lists of names / rects: wrapped, several per line)
                item = json.dumps(x, ensure_ascii=False, separators=(", ", ": "))
                if line and len(pad) + len(line) + len(item) + 2 > width:
                    lines.append(line.rstrip())
                    line = ""
                line += item + ", "
            lines.append(line.rstrip().rstrip(","))
            return "[\n" + ",\n".join(pad + l.rstrip(",") for l in lines) + "\n" + " " * indent + "]"
        return "[\n" + ",\n".join(pad + pretty(x, indent + 2, width) for x in v) + "\n" + " " * indent + "]"
    items = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {pretty(x, indent + 2, width)}" for k, x in v.items()]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"


# ---------------------------------------------------------------- the command

def run(folder, wire_it=False, force=False, unwire_it=False):
    import character_json as cj
    if unwire_it:
        unwire(folder)
        print(f"{folder.name}: tools/extras.py, tools/abilities.py and make_configs.py put back from "
              f"{backup_dir(folder.name)}; character.json removed")
        return OK
    out = folder / cj.FILE
    if out.exists() and not force and not wire_it:
        print(f"error: {out} exists already (--force to write it again)", file=sys.stderr)
        return FAILED
    try:
        mod, cfgs, extra, abilities = _legacy(folder)
        c = build_json(folder, mod, cfgs, extra, abilities)
        problems, notes = prove(folder, c, cfgs, extra, abilities)
    except Unsupported as e:
        print(f"{folder.name}: can't convert: {e}", file=sys.stderr)
        return FAILED
    if problems:
        print(f"{folder.name}: NOT identical, nothing written:")
        for p in problems:
            print("  -", p)
        return FAILED
    print(f"{folder.name}: proven identical: the Sonic 1 and Sonic 2 sheet2ani configs, the EXTRAS entry and the "
          f"ABILITIES entry come back exactly from the character.json")
    for n in notes:
        print("  note:", n)
    if out.exists() and not force:
        print(f"error: {out} exists already (--force to write it again)", file=sys.stderr)
        return FAILED
    if wire_it:
        if (folder / "make_configs.legacy.py").exists():
            print(f"error: {folder.name} already has a make_configs.legacy.py: wired already?", file=sys.stderr)
            return FAILED
        try:
            notes = wire(folder, c)
        except Unsupported as e:
            print(f"{folder.name}: can't wire: {e} (nothing changed)", file=sys.stderr)
            return FAILED
        if notes.get("abilities"):
            c["abilities"] = {"_notes": notes["abilities"], **c["abilities"]}
        if notes.get("extras"):
            c["_extras_notes"] = notes["extras"]
    out.write_text(pretty(c) + "\n")
    print(f"wrote {out}")
    if wire_it:
        print(f"wired: make_configs.py is now a shim (the old one: make_configs.legacy.py); tools/extras.py and "
              f"tools/abilities.py call the loader. Backups: {backup_dir(folder.name)} (`noswap convert --unwire "
              f"{folder.name}` restores them). Now rebuild and compare (docs/toolset-cli.md).")
    return OK
