"""The NoSwap character editor's backend: one class whose public methods are the UI's API (docs/toolset-ui.md).

Every method takes and returns plain JSON data. It never reimplements the pipeline: checks come from
noswap_cli.check, frame cutting and colours from noswap_cli.preview.Cutter (sheet2ani's own cut functions), frame
placement from sheet2ani.build_anims, the moves from abilities_registry, the build from `noswap build`, and the file
is written with noswap_cli.convert.pretty (the converted characters' style).

The open character.json is held in memory as Python data in the file's own key order (comments, unknown keys and all).
The UI changes it with small edit operations ({"op": "set" | "del" | "rename", "path": [...]}) rather than sending the
whole document back, so nothing it doesn't show is ever lost or reordered.
"""
import base64
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import character_json  # noqa: E402
from noswap_cli import model  # noqa: E402
from noswap_cli.convert import pretty  # noqa: E402
from noswap_ui import jsontext  # noqa: E402
from noswap_cli.schema import load_schema  # noqa: E402
from noswap_cli.templates import TEMPLATES  # noqa: E402

GAMES = ("s1", "s2", "cd", "s3k", "mania")
SECTIONS = ("animations", "animations_sonic2", "ability_animations", "special_stage")
BACKUPS = (Path(os.environ["NOSWAP_KIT_DATA"]) / "backups" if os.environ.get("NOSWAP_KIT") and os.environ.get("NOSWAP_KIT_DATA")
           else Path(tempfile.gettempdir()) / "noswap-ui" / "backups")  # (the Creator Kit: in its data folder)
IMAGE_EXT = {".png", ".gif", ".bmp"}


class ApiError(Exception):
    """A request the UI should show as a message (not a crash)."""


def _png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _hexrgb(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _walk(doc, path, create=False):
    """The container holding path[-1]."""
    cur = doc
    for k in path[:-1]:
        if isinstance(cur, list):
            cur = cur[int(k)]
        else:
            if k not in cur:
                if not create:
                    raise ApiError(f"no {'.'.join(map(str, path))} in the file")
                cur[k] = {}
            cur = cur[k]
    return cur


class Backend:
    def __init__(self, lock=None):
        self.lock = threading.RLock()
        self.build_lock = lock or os.environ.get("NOSWAP_BUILD_LOCK")
        self.folder = None
        self.doc = None
        self.disk_text = None
        self.backed_up = False
        self.jobs = {}
        self.sheet_version = 0
        self._cutters = {}
        self._registry = None
        self.renamed = []  # [(old, new)]: older names the open file had (popgun_reach...) until Save writes new ones

    # ------------------------------------------------------------------ characters

    def characters(self):
        """Every character folder the build finds (testmods/*/character.json and $NOSWAP_CHARACTER_DIRS)."""
        out = []
        for f in character_json.folders():
            try:
                raw = json.loads((f / character_json.FILE).read_text())
            except Exception:
                raw = {}
            out.append({"folder": str(f), "id": f.name, "name": raw.get("name", "?"),
                        "full_name": raw.get("full_name", ""), "key": raw.get("key") or f"noswap.{f.name}"})
        return {"characters": out, "testmods": str(model.TESTMODS)}

    def state(self):
        return {"open": self._info() if self.doc is not None else None, "repo": str(REPO),
                "build_lock": self.build_lock or str(Path(tempfile.gettempdir()) / "noswap-build.lock"),
                "testmods": str(model.TESTMODS), "kit": self.kit_status()}

    # ------------------------------------------------------------------ the Creator Kit (tools/noswap_cli/kit.py)

    def kit_status(self):
        """The Creator Kit's setup (None: not the kit, the repo's tools)."""
        from noswap_cli import kit
        return kit.status() if kit.active() else None

    def kit_check(self, game, path):
        """Check a game folder for Set up: {ok, problems, notes}."""
        from noswap_cli import kit
        if game == "origins":
            return kit.check_origins_game(os.path.expanduser(str(path or "").strip()))
        if game == "mania":
            return kit.check_mania_game(os.path.expanduser(str(path or "").strip()))
        raise ApiError(f"no game {game!r}")

    def kit_setup(self, origins=None, mania=None):
        """Start `noswap setup` (take the game files the build needs from the player's games): {job}."""
        from noswap_cli import kit
        if not kit.active():
            raise ApiError("Set up is for the Creator Kit (the repo's tools read extracted/ directly)")
        cmd = [sys.executable, "-u", str(TOOLS / "noswap.py"), "setup"]
        if origins:
            cmd += ["--origins", os.path.expanduser(str(origins).strip())]
        if mania:
            cmd += ["--mania", os.path.expanduser(str(mania).strip())]
        if len(cmd) == 4:
            raise ApiError("give Sonic Origins' folder, Sonic Mania's, or both")
        return self._start([cmd], "setup")

    def open(self, folder):
        try:
            path = model.resolve_folder(folder)
        except model.CharacterError as e:
            raise ApiError(str(e))
        f = path / character_json.FILE
        if not f.exists():
            raise ApiError(f"{path} has no character.json. Old make_configs.py characters can be converted first: "
                           f"python3 tools/noswap.py convert {path.name}")
        text = f.read_text()
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as e:
            raise ApiError(f"{f}: not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}). Fix it in a text "
                           "editor, then open it again.")
        # older move / field names (popgun_reach -> melee_reach): renamed here, so the file shows as changed and Save
        # writes the new names in their places (the UI says so: "renamed" in _info)
        self.renamed = character_json.migrate_abilities(doc.get("abilities")) if isinstance(doc, dict) else []
        with self.lock:
            self.folder, self.doc, self.disk_text, self.backed_up = path, doc, text, False
            self._cutters.clear()
            self.sheet_version += 1
            return self._info()

    def _need(self):
        if self.doc is None:
            raise ApiError("no character is open")

    def _dirty(self):
        return self.disk_text is None or json.loads(self.disk_text) != self.doc

    def _sheet_path(self):
        return (self.folder / self.doc.get("sheet", {}).get("file", "")).resolve()

    def _info(self):
        sheet = self._sheet_path()
        size = None
        if sheet.is_file():
            from PIL import Image
            with Image.open(sheet) as im:
                size = list(im.size)
        base = self.doc.get("base", "sonic")
        base = base if base in ("sonic", "tails", "knuckles") else "sonic"
        return {"folder": str(self.folder), "id": self.folder.name, "doc": self.doc, "dirty": self._dirty(),
                "path": str(self.folder / character_json.FILE),
                "sheet": {"path": str(sheet), "exists": sheet.is_file(), "size": size, "version": self.sheet_version},
                "templates": {"Sonic1": TEMPLATES[("Sonic1", base)], "Sonic2": TEMPLATES[("Sonic2", base)]},
                "speeds": self._template_speeds(base), "fallbacks": self._fallbacks(base),
                "renamed": [{"old": o, "new": n} for o, n in self.renamed]}

    def _fallbacks(self, base):
        """tools/anim_fallbacks.plan for the open document: which missing animations borrow what, and what the
        generic ball fills (the Animations tab shows them)."""
        import anim_fallbacks
        try:
            return anim_fallbacks.plan(character_json._clean(self.doc),
                                       {g: TEMPLATES[(g, base)]["filled"] for g in ("Sonic1", "Sonic2")})
        except Exception as e:  # (a half-edited document: no fallbacks shown, never a broken editor)
            return {"error": repr(e)}

    def _template_speeds(self, base):
        """{animation name: the base's own .ani speed} (Sonic 2's list, then Sonic 1's), when the game data is there."""
        import sheet2ani
        out = {}
        for game in ("Sonic1", "Sonic2"):
            p = REPO / "extracted" / game / "Data" / "Animations" / character_json.TEMPLATE_ANI[base]
            if p.exists():
                try:
                    out.update({a["name"]: a["speed"] for a in sheet2ani.read_ani(p)["anims"]})
                except SystemExit:
                    pass
        return out

    def schema(self):
        return load_schema()

    # ------------------------------------------------------------------ editing and saving

    def edit(self, ops):
        """Apply edit operations to the open document, in order:
        {"op": "set", "path": [...], "value": v}  (creates missing objects on the way; a new key goes last)
        {"op": "del", "path": [...]}
        {"op": "rename", "path": [..., old], "to": new}  (an object key, keeping its place)"""
        self._need()
        with self.lock:
            doc = copy.deepcopy(self.doc)
            for op in ops:
                path = op.get("path") or []
                if not path:
                    raise ApiError("an edit needs a path")
                parent = _walk(doc, path, create=op["op"] == "set")
                k = path[-1]
                if op["op"] == "set":
                    if isinstance(parent, list):
                        k = int(k)
                        if k == len(parent):
                            parent.append(op["value"])
                        else:
                            parent[k] = op["value"]
                    else:
                        parent[k] = op["value"]
                elif op["op"] == "del":
                    if isinstance(parent, list):
                        del parent[int(k)]
                    else:
                        parent.pop(k, None)
                elif op["op"] == "rename":
                    to = op["to"]
                    if to in parent and to != k:
                        raise ApiError(f"{to!r} is already there")
                    items = [(to if kk == k else kk, v) for kk, v in parent.items()]
                    parent.clear()
                    parent.update(items)
                else:
                    raise ApiError(f"unknown edit {op['op']!r}")
            if any(o.get("path", [None])[0] == "sheet" for o in ops):
                self._cutters.clear()
                self.sheet_version += 1
            _keep_per_frame_in_step(self.doc, doc)
            self.doc = doc
            return self._info()

    def rename_frame(self, old, new):
        """Rename a frame and every reference to it (animations, UI, ending)."""
        self._need()
        new = new.strip()
        if not new or new.startswith("_"):
            raise ApiError("a frame name can't be empty or start with _")
        if new in self.doc.get("frames", {}):
            raise ApiError(f"there's already a frame called {new}")
        ops = [{"op": "rename", "path": ["frames", old], "to": new}]

        def fix(v, path):
            if isinstance(v, list):
                for i, x in enumerate(v):
                    if x == old:
                        ops.append({"op": "set", "path": path + [i], "value": new})
                    else:
                        fix(x, path + [i])
            elif isinstance(v, dict):
                if v.get("frame") == old:
                    ops.append({"op": "set", "path": path + ["frame"], "value": new})
                for k, x in v.items():
                    if not k.startswith("_") and isinstance(x, (list, dict)):
                        fix(x, path + [k])

        for sec in SECTIONS + ("s3k_victory", "ui", "ending"):
            if sec in self.doc:
                fix(self.doc[sec], [sec])
        return self.edit(ops)

    def text(self):
        """The file as Save would write it: the file's own text with only what changed edited (jsontext.update), or
        NoSwap's generated-file style for a new file."""
        self._need()
        return jsontext.update(self.disk_text, self.doc) if self.disk_text else pretty(self.doc) + "\n"

    def save(self, force=False):
        """Write the file, changing only the text of what changed (the file's own layout, comments, key order and
        unknown keys are kept: jsontext.update). The first save in a
        session backs up what was on disk to <temp dir>/noswap-ui/backups/<id>/."""
        self._need()
        with self.lock:
            path = self.folder / character_json.FILE
            if not self._dirty():
                return {"saved": False, "path": str(path), "message": "nothing changed", **self._info()}
            if path.exists() and self.disk_text is not None and path.read_text() != self.disk_text and not force:
                raise ApiError("character.json changed on disk since it was opened (another editor?). Revert to load "
                               "that version, or save again to overwrite it.")
            backup = None
            if not self.backed_up and path.exists():
                d = BACKUPS / self.folder.name
                d.mkdir(parents=True, exist_ok=True)
                backup = d / time.strftime("character-%Y%m%d-%H%M%S.json")
                shutil.copy2(path, backup)
                self.backed_up = True
            text = self.text()
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(text)
            tmp.replace(path)
            self.disk_text = text
            self.renamed = []  # (written with the new names now)
            self._cutters.clear()
            return {"saved": True, "path": str(path), "backup": str(backup) if backup else None, **self._info()}

    def keep_unsaved(self):
        """On quitting with unsaved edits: write them to <temp dir>/noswap-ui/backups/<id>/unsaved-*.json (never over
        the character's own file). Returns the path, or None."""
        if self.doc is None or not self._dirty():
            return None
        d = BACKUPS / self.folder.name
        d.mkdir(parents=True, exist_ok=True)
        p = d / time.strftime("unsaved-%Y%m%d-%H%M%S.json")
        p.write_text(self.text())
        return str(p)

    def revert(self):
        """Throw away unsaved edits."""
        self._need()
        return self.open(str(self.folder))

    # ------------------------------------------------------------------ check

    def check(self):
        """`noswap check` on the saved file: [{level, where, msg, fix, target}] (target: where the UI can show it)."""
        self._need()
        from noswap_cli import check
        try:
            _, report = check.run(self.folder)
        except BaseException as e:  # (a pipeline module that exits: report it, keep the server up)
            return {"items": [{"level": "error", "where": "check", "msg": f"the check stopped: {e!r}", "fix": None,
                               "target": None}], "counts": {"error": 1, "warning": 0, "note": 0}}
        items = [{"level": lv, "where": w, "msg": m, "fix": fx, "target": _target(w)} for lv, w, m, fx in report.items]
        return {"items": items, "counts": {lv: report.count(lv) for lv in ("error", "warning", "note")},
                "dirty": self._dirty()}

    # ------------------------------------------------------------------ the sheet, frames, animations

    def _character(self):
        """A model.Character for the in-memory document (what the checks and previews read)."""
        ch = model.Character(self.folder)
        raw = self.doc
        c = character_json._clean(raw)
        ch.kind, ch.raw, ch.cleaned = "json", raw, c
        ch.frames = {k: v for k, v in c.get("frames", {}).items() if isinstance(v, list) and len(v) == 4}
        ch.name, ch.base = c.get("name", "?"), c.get("base", "sonic")
        sheet = c.get("sheet", {})
        ch.sheet = self._sheet_path()
        ch.background = sheet.get("background", [])
        ch.feet_y = sheet.get("feet_y", 20)
        p = c.get("palette", {})
        ch.own = {int(s): col.lower() for s, col in p.get("own", {}).items() if str(s).isdigit()}
        ch.colours = {**{k.lower(): v for k, v in p.get("shared", {}).items()}, **{col: s for s, col in ch.own.items()}}
        ch.other_colours = p.get("other_colours", "nearest")
        return ch

    def _cutter(self, raw):
        from noswap_cli.preview import Cutter
        key = (bool(raw), json.dumps([self.doc.get("sheet"), self.doc.get("palette")], sort_keys=True))
        if key not in self._cutters:
            ch = self._character()
            if not ch.sheet.is_file():
                raise ApiError(f"the sheet {ch.sheet} doesn't exist")
            self._cutters[key] = Cutter(ch, raw)
        return self._cutters[key]

    def _spec(self, ref):
        """A frame reference (name, rect, {"frame": NAME, ...}) -> a sheet2ani spec, or None."""
        frames = self.doc.get("frames", {})
        if isinstance(ref, str):
            return frames.get(ref)
        if isinstance(ref, dict) and "frame" in ref:
            r = frames.get(ref["frame"])
            return {"rect": r, **{k: v for k, v in ref.items() if k != "frame" and not k.startswith("_")}} if r else None
        return ref

    def sheet_file(self):
        """(bytes, content type) of the sheet image (served at /sheet)."""
        self._need()
        p = self._sheet_path()
        if not p.is_file():
            raise ApiError("no sheet")
        if p.suffix.lower() == ".png":
            return p.read_bytes(), "image/png"
        from PIL import Image
        buf = io.BytesIO()
        Image.open(p).convert("RGBA").save(buf, "PNG")
        return buf.getvalue(), "image/png"

    def frames_info(self):
        """{name: {rect, trim (the drawn part, sheet coordinates), empty, used_by, anchors}} for every named frame."""
        self._need()
        import sheet2ani
        cutter = self._cutter(True)
        used = {}

        def note(ref, where, anchor):
            name = ref if isinstance(ref, str) else ref.get("frame") if isinstance(ref, dict) else None
            if name:
                u = used.setdefault(name, {"where": [], "anchors": set()})
                u["where"].append(where)
                if anchor:
                    u["anchors"].add(anchor)

        for sec in SECTIONS:
            for an, a in (self.doc.get(sec) or {}).items():
                if isinstance(a, dict) and not an.startswith("_"):
                    for f in a.get("frames", []):
                        note(f, f"{sec} {an}", a.get("anchor", "center" if sec == "special_stage" else "feet"))
        for f in (self.doc.get("s3k_victory") or {}).get("frames", []):
            note(f, "s3k_victory", "feet")
        for sec in ("ui", "ending"):
            for k, e in (self.doc.get(sec) or {}).items():
                if isinstance(e, dict) and "frame" in e:
                    note(e["frame"], f"{sec} {k}", None)
        out = {}
        W, H = cutter.src.size
        for name, rect in self.doc.get("frames", {}).items():
            if name.startswith("_") or not isinstance(rect, list) or len(rect) != 4:
                continue
            x, y, w, h = rect
            trim, empty, outside = None, False, x + w > W or y + h > H or w <= 0 or h <= 0
            if not outside:
                crop = cutter.src.crop((x, y, x + w, y + h))
                try:
                    _, mask = sheet2ani.cut_frame(cutter.src, tuple(rect), cutter.background, trim=False)
                    b = mask.getbbox()
                    trim = [x + b[0], y + b[1], b[2] - b[0], b[3] - b[1]] if b else None
                    empty = b is None
                except SystemExit:
                    empty = True
                del crop
            u = used.get(name, {"where": [], "anchors": set()})
            out[name] = {"rect": rect, "trim": trim, "empty": empty, "outside": outside, "used_by": u["where"],
                         "anchors": sorted(u["anchors"])}
        return {"frames": out, "sheet_size": [W, H]}

    def fit_rect(self, rect):
        """The rect shrunk to the drawn pixels inside it (non-background): a crop, nothing else."""
        self._need()
        import sheet2ani
        cutter = self._cutter(True)
        W, H = cutter.src.size
        x, y, w, h = [int(v) for v in rect]
        x, y = max(0, x), max(0, y)
        w, h = min(w, W - x), min(h, H - y)
        if w <= 0 or h <= 0:
            raise ApiError("that rectangle is outside the sheet")
        try:
            _, mask = sheet2ani.cut_frame(cutter.src, (x, y, w, h), cutter.background, trim=False)
        except SystemExit:
            raise ApiError("nothing drawn inside that rectangle (only background colours)")
        b = mask.getbbox()
        if not b:
            raise ApiError("nothing drawn inside that rectangle (only background colours)")
        return {"rect": [x + b[0], y + b[1], b[2] - b[0], b[3] - b[1]]}

    def detect_frames(self, merge=None, min_size=None, region=None, extra_background=None, split=None):
        """Proposed frames for the sheet (noswap_cli.detect): {proposals: [{rect, kind, confidence, parts, name,
        existing}], background, fills, ...}. split: a rect to cut into its separate pieces instead (no merging).
        extra_background: more colours to treat as background for this search only (nothing is saved)."""
        self._need()
        from noswap_cli import detect
        src = self._cutter(True).src
        bg = [c.lower() for c in (self.doc.get("sheet", {}).get("background") or [])]
        bg += [c.lower() for c in (extra_background or []) if c.lower() not in bg]
        if split:
            return {"rects": detect.split(src, split, bg or detect.guess_background(src))}
        frames = {k: v for k, v in (self.doc.get("frames") or {}).items() if not k.startswith("_")}
        existing = detect.drawn_parts(src, frames, bg or detect.guess_background(src))
        return detect.detect(src, bg or None, merge=detect.DEFAULT_MERGE if merge is None else int(merge),
                             min_size=detect.DEFAULT_MIN_SIZE if min_size is None else int(min_size),
                             region=region, existing=existing, names=frames)

    def pick_colour(self, x, y):
        """The sheet's colour at a pixel."""
        self._need()
        src = self._cutter(True).src
        r, g, b, a = src.getpixel((int(x), int(y)))
        return {"colour": _hexrgb((r, g, b)), "alpha": a}

    def frame_image(self, ref, raw=False, scale=1):
        """A frame cut as the build cuts it: {png, w, h} (in the game's colours unless raw)."""
        self._need()
        spec = self._spec(ref)
        if spec is None:
            raise ApiError(f"no frame {ref!r}")
        img, _ = self._cutter(raw).cut(spec)
        if img is None:
            raise ApiError("this frame can't be cut (empty, or outside the sheet)")
        from PIL import Image
        if scale > 1:
            img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        return {"png": _png(img), "w": img.width, "h": img.height}

    def animation(self, section, name, raw=False):
        """One animation as the game places it (sheet2ani.build_anims: feet on the ground line, or centred; align;
        hold): {frames: [{png, w, h, px, py, label}], speed, loop, feet_y, ticks}. px / py: the frame's top-left
        relative to the object's position, as in the .ani."""
        self._need()
        import sheet2ani
        if section == "s3k_victory":
            a = self.doc.get("s3k_victory") or {}
            anim = {"frames": a.get("frames", []), "anchor": "feet", "align": a.get("align", False)}
        else:
            anim = (self.doc.get(section) or {}).get(name)
        if not isinstance(anim, dict):
            raise ApiError(f"no animation {name!r} in {section}")
        cutter = self._cutter(raw)
        refs = anim.get("frames", [])
        specs = [self._spec(r) for r in refs]
        base = self.doc.get("base", "sonic")
        base = base if base in character_json.TEMPLATE_ANI else "sonic"
        game = "Sonic1" if section == "special_stage" else "Sonic2"
        tpl_path = REPO / "extracted" / game / "Data" / "Animations" / (
            "SonicSS.ani" if section == "special_stage" else character_json.TEMPLATE_ANI[base])
        template = sheet2ani.read_ani(tpl_path) if tpl_path.exists() else None
        if template is None and section != "special_stage":
            alt = REPO / "extracted" / "Sonic1" / "Data" / "Animations" / character_json.TEMPLATE_ANI[base]
            template = sheet2ani.read_ani(alt) if alt.exists() else None
        sheet_feet = self.doc.get("sheet", {}).get("feet_y", 20)
        feet_y = sheet2ani.standing_ground(template, sheet_feet) if template else sheet_feet
        hitboxes = template["hitboxes"] if template else None
        t = next((x for x in (template or {}).get("anims", []) if x["name"] == name), None) \
            if section in ("animations", "animations_sonic2", "special_stage") else None
        if t is None:
            t = dict(name=name, speed=anim.get("speed", 60), loop=anim.get("loop", 0), rot=anim.get("rot", 0),
                     frames=[dict(hitbox=anim.get("hitbox", 0))])
        cut, cuts, keys = {}, [], []
        for s in specs:
            if s is None:
                cuts.append((None, None))
                keys.append(None)
                continue
            img, anchor = cutter.cut(s)
            key = sheet2ani.frame_key(s)
            keys.append(key)
            cuts.append((img, anchor))
            if img is not None:
                cut[key] = img.getchannel("A")  # (build_anims reads sizes, bounding boxes and filled pixels)
                if isinstance(s, dict) and anchor and tuple(anchor) != (0, 0, img.width, img.height):
                    sheet2ani.ANCHORS[key] = tuple(anchor)
        good = [(i, r, s) for i, (r, s, (img, _)) in enumerate(zip(refs, specs, cuts)) if img is not None]
        frames_out = []
        speed, loop = anim.get("speed", t["speed"]), anim.get("loop", 0)
        if good:
            spec = {**anim, "frames": [s for _, _, s in good]}
            placed = {k: (0, 0, 0) for k in cut}
            try:
                built, _ = sheet2ani.build_anims(dict(anims=[t], hitboxes=hitboxes), {name: spec}, cut, placed,
                                                 feet_y, hitboxes)
            except SystemExit as e:
                raise ApiError(str(e))
            b = built[0]
            speed, loop = b["speed"], b["loop"]
            hold = max(1, int(anim.get("hold", 1)))
            rows = [(i, r, s) for i, r, s in good for _ in range(hold)]
            for f, (i, r, s) in zip(b["frames"], rows):
                img = cutter.cut(s)[0]
                # (index: the frame's place in the animation's "frames", where an offset is saved; offset: its own
                # sheet2ani.frame_offset, already in px / py; drawn / diag: _drawn, for the hit-box panel's "fit")
                frames_out.append({"png": _png(img), "w": img.width, "h": img.height, "px": f["px"], "py": f["py"],
                                   "label": _label(r), "index": i, "offset": list(sheet2ani.frame_offset(s)),
                                   **_drawn(img, f["px"], f["py"])})
        missing = [_label(r) for r, (img, _) in zip(refs, cuts) if img is None]
        return {"frames": frames_out, "speed": speed, "loop": loop, "feet_y": feet_y,
                "anchor": anim.get("anchor", "center" if section == "special_stage" else "feet"),
                "ticks": round(240 / speed) if speed else None, "missing": missing,
                "template": bool(template), "colours": "sheet" if cutter.palette is None else "game",
                "collapse": None if cutter.palette is None else self._collapse([s for _, _, s in good])}

    def ball_preview(self, size="medium", colours="auto", scale=3):
        """The generic spin ball (character.json "ball", tools/generic_ball.py) as the game draws it: {frames: [{png,
        w, h}], colours: the 5 resolved {role: "#rrggbb"}, game: {role: "#rrggbb" as the game draws it}, palette: his
        colours to pick from [{colour, slot}], size (px)}."""
        self._need()
        import generic_ball
        from PIL import Image
        c = character_json._clean(self.doc)
        c = {**c, "folder": self.folder, "ball": {"size": size, "colours": colours}}
        try:
            cols = character_json.ball_colours(c, self._cutter(True).src.convert("RGB"))
        except (KeyError, ValueError, SystemExit) as e:
            raise ApiError(f"can't pick the ball's colours: {e}")
        px = generic_ball.SIZES.get(size)
        if px is None:
            raise ApiError(f"size must be one of {', '.join(generic_ball.SIZES)}")
        cutter = self._cutter(False)
        game = dict(cols)
        if cutter.palette:  # each colour through his colour mapping to the slot the game draws
            for role, col in cols.items():
                rgb = _rgb(col)
                slot = cutter.colour_map.get(rgb)
                if slot is None and cutter.colour_map:
                    near = min(cutter.colour_map, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
                    slot = cutter.colour_map[near]
                if slot is not None:
                    game[role] = _hexrgb(cutter.palette[slot])
        frames = []
        for f in generic_ball.frames(size=px):
            img = generic_ball.coloured(f, game)
            img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
            frames.append({"png": _png(img), "w": img.width, "h": img.height})
        palette = [{"colour": col.lower(), "slot": s} for col, s in character_json.key_colours(c).items()]
        return {"frames": frames, "colours": cols, "game": game, "palette": palette, "size": px,
                "source": str(generic_ball.SOURCE), "source_exists": generic_ball.SOURCE.exists()}

    def sign_preview(self, scale=3):
        """The end-of-act signpost face as the build makes it (character_json.sign_face_plan, tools/sign_face.py):
        {mode: "head" (a head on the game's own board) | "own" (the drawing as it is) | null (none), why ("head":
        written so; "detected": a frame that is a head, not a whole sign; "default": none given, his Stopped frame's
        top), head [x, y, w, h], scale, auto, auto_scale, board {png, w, h}: the 48x32 sign S1 / S2 / CD / S3&K draw
        (Mania puts its 40x24 face area on its own board), at `scale`x, in the game's colours}."""
        self._need()
        import sign_face
        c = {**character_json._clean(self.doc), "folder": self.folder}
        cutter = self._cutter(False)
        try:
            plan = character_json.sign_face_plan(c, cutter.src)
        except (KeyError, ValueError, SystemExit) as e:
            raise ApiError(f"signpost face: {e}")
        if not plan:
            return {"mode": None}
        out = {k: v for k, v in plan.items() if k != "element"}
        if plan["mode"] == "head":
            def colour(rgb):
                if not cutter.palette or not cutter.colour_map:
                    return rgb
                slot = cutter.colour_map.get(rgb)
                if slot is None:
                    near = min(cutter.colour_map, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, rgb)))
                    slot = cutter.colour_map[near]
                return cutter.palette[slot]
            from PIL import Image
            img = sign_face.preview(cutter.src, cutter.background, plan["element"], colour)
            img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
            out["board"] = {"png": _png(img), "w": img.width, "h": img.height}
        return out

    def _collapse(self, specs):
        """How many distinct colours these frames have on the sheet and in the game: {sheet, game, bad} (bad: the game
        draws 4 or more sheet colours with 2 or fewer: a silhouette, see `noswap check`)."""
        raw, game = self._cutter(True), self._cutter(False)
        a, b = set(), set()
        for s in {json.dumps(x, sort_keys=True): x for x in specs}.values():
            for cutter, out in ((raw, a), (game, b)):
                img = cutter.cut(s)[0]
                if img is not None:
                    out.update(c for _, c in img.getcolors(1 << 16) or [] if c[3])
        return {"sheet": len(a), "game": len(b), "bad": len(a) >= 4 and len(b) <= 2}

    def sheet_colours(self):
        """Colours on the frames the character uses: [{colour, count, slot, drawn_as}] (slot: listed in the palette;
        drawn_as: the colour the game draws it as)."""
        self._need()
        ch = self._character()
        cutter = self._cutter(False)
        bg = {c.lower() for c in ch.background}
        counts = {}
        rects = set()
        for name, r in ch.frames.items():
            rects.add(tuple(r))
        W, H = cutter.src.size
        for x, y, w, h in rects:
            if x + w > W or y + h > H:
                continue
            for n, (r, g, b, a) in cutter.src.crop((x, y, x + w, y + h)).getcolors(1 << 20) or []:
                hx = _hexrgb((r, g, b))
                if a and hx not in bg:
                    counts[hx] = counts.get(hx, 0) + n
        keyed = {c: s for c, s in ch.colours.items()}
        cmap = cutter.colour_map or {}
        pal = cutter.palette
        out = []
        for col, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            slot = keyed.get(col)
            drawn_slot = cmap.get(_rgb(col))
            drawn = _hexrgb(pal[drawn_slot]) if pal and drawn_slot is not None else None
            out.append({"colour": col, "count": n, "slot": slot, "drawn_slot": drawn_slot, "drawn_as": drawn})
        base_pal = [_hexrgb(c) for c in pal[:16]] if pal else None
        return {"colours": out, "base_palette": base_pal, "background": sorted(bg)}

    def name_font(self):
        """The HUD name tag's letters (tools/hud_font.py: Rayan C.'s), for the HUD tab's live preview of a typed tag:
        {glyphs: {letter: [rows of "f" / "1" / "."]}, colours, space, room: [w, h]}. The build lays them out with
        hud_font.tag, which the page copies."""
        import hud_font
        return {"glyphs": hud_font.glyphs(), "colours": hud_font.HUD_COLOURS, "space": hud_font.SPACE,
                "room": list(hud_font.room())}

    def name_tag(self, text):
        """A typed name tag checked as the build will: {width, height, problems}."""
        import hud_font
        try:
            w, h = hud_font.size(text)
        except (KeyError, ValueError):
            w = h = None
        return {"width": w, "height": h, "problems": hud_font.problems(text)}

    def palette_fill(self):
        """A proposal for "Fill from sheet" (the Palette tab shows it before anything is applied): every colour on his
        named frames and HUD / ending rects, most pixels first, as
          kept   already in palette.own or palette.shared (left as it is);
          shared exactly one of the base character's slots 1-15 (written to palette.shared);
          own    the next free own slot, 74-95 (palette.own);
          over   no slot left: the user picks a colour to merge it into (nothing is merged without asking; the
                 nearest proposed colour is only a suggestion).
        Exact colours only: nothing is recoloured (the faithful art rule)."""
        self._need()
        from noswap_cli import check as chk
        ch = self._character()
        src = self._cutter(True).src
        bg = {c.lower() for c in ch.background}
        rects = {tuple(r) for r in ch.frames.values()}
        for sec in ("ui", "ending"):
            for e in (self.doc.get(sec) or {}).values():
                if isinstance(e, dict) and isinstance(e.get("rect"), list) and len(e["rect"]) == 4:
                    rects.add(tuple(e["rect"]))
        W, H = src.size
        from noswap_cli import detect
        # cell-box colours behind the frames are never his colours: no slot; Apply puts them in sheet.background
        boxes = detect.box_colours(src, sorted(bg), [r for r in rects if r[2] > 0 and r[3] > 0])
        counts, box_px = {}, {}
        for x, y, w, h in rects:
            if w <= 0 or h <= 0 or x + w > W or y + h > H:
                continue
            for n, (r, g, b, a) in src.crop((x, y, x + w, y + h)).getcolors(1 << 20) or []:
                col = _hexrgb((r, g, b))
                if a and col not in bg:
                    if col in boxes:
                        box_px[col] = box_px.get(col, 0) + n
                    else:
                        counts[col] = counts.get(col, 0) + n
        pal = chk._game_palette(ch)
        base = {_hexrgb(pal[s]): s for s in range(15, 0, -1)} if pal else {}  # (the lowest slot wins a tie)
        own = {int(s): c.lower() for s, c in (self.doc.get("palette", {}).get("own") or {}).items()
               if str(s).isdigit() and isinstance(c, str)}
        shared = {c.lower(): v for c, v in (self.doc.get("palette", {}).get("shared") or {}).items()
                  if not c.startswith("_")}
        own_of = {c: s for s, c in own.items()}
        free = [s for s in range(chk.OWN_FIRST, chk.OWN_LAST + 1) if s not in own]
        rows = []
        for col, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if col in own_of:
                rows.append({"colour": col, "count": n, "kind": "kept", "slot": own_of[col], "via": "own"})
            elif col in shared:
                rows.append({"colour": col, "count": n, "kind": "kept", "slot": shared[col], "via": "shared"})
            elif col in base:
                rows.append({"colour": col, "count": n, "kind": "shared", "slot": base[col]})
            elif free:
                rows.append({"colour": col, "count": n, "kind": "own", "slot": free.pop(0)})
            else:
                rows.append({"colour": col, "count": n, "kind": "over", "slot": None})
        slotted = [r for r in rows if r["slot"] is not None]
        for r in rows:
            if r["kind"] == "over" and slotted:
                rgb = _rgb(r["colour"])
                near = min(slotted, key=lambda t: sum((a - b) ** 2 for a, b in zip(rgb, _rgb(t["colour"]))))
                r["suggest"] = {"colour": near["colour"], "slot": near["slot"]}
        unused = [{"slot": s, "colour": c} for s, c in sorted(own.items()) if c not in counts]
        mania = None
        try:  # (which colours Mania's global palette has already: those need none of its 13 own slots)
            import build_mania_art as bma
            glob = {_hexrgb(c) for i, c in bma.global_palette().items() if 0 < i < bma.PLAYER_SLOT}
            for r in rows:
                r["mania_global"] = r["colour"] in glob
            mania = {"slots": chk.MANIA_OWN_SLOTS}
        except Exception:
            pass
        return {"rows": rows, "box_colours": [{"colour": c, "count": box_px.get(c, 0), "boxes": n,
                                               "listed": c in own_of or c in shared} for c, n in boxes.items()],
                "free": chk.OWN_LAST - chk.OWN_FIRST + 1 - len(own), "first": chk.OWN_FIRST,
                "last": chk.OWN_LAST, "unused_own": unused, "mania": mania, "total": sum(counts.values()),
                "base_palette": [_hexrgb(pal[s]) for s in range(16)] if pal else None,
                "mania_enabled": bool((self.doc.get("games") or {}).get("mania"))}

    # ------------------------------------------------------------------ abilities

    def registry(self):
        if self._registry is None:
            import abilities_registry as reg
            data = reg.build()
            data["per_frame_groups"] = reg.PER_FRAME_GROUPS  # (the hit-box panel's shapes: hitbox.js)
            self._registry = json.loads(json.dumps(data, default=str))
        return self._registry

    def per_frame_info(self):
        """What the hit-box panel needs beyond the registry: Sonic CD's box per frame of the Y move. CD has no hitbox
        override (tools/build_soniccd.py): the move (slot 46 there, the ground frames, in the air too) hits with the
        frames' own box (the template's hitbox table), and only the extras with a reach in build_soniccd.SHOT_OUT
        reach further (the enemies widen their box toward him: the same as his box growing ahead, or all round past
        RADIAL); melee_reach / top / bottom aren't read. {cd: {boxes: [[l, t, r, b] facing right, per frame of slot
        43], rule: "body" | "reach", id}}"""
        self._need()
        import sheet2ani
        base = self.doc.get("base", "sonic")
        base = base if base in character_json.TEMPLATE_ANI else "sonic"
        anim = (self.doc.get("ability_animations") or {}).get("43") or {}
        hb = anim.get("hitbox", 0) if isinstance(anim.get("hitbox", 0), int) else 0
        body = [-10, -20, 10, 20]
        for game in ("SonicCD", "Sonic2"):
            p = REPO / "extracted" / game / "Data" / "Animations" / character_json.TEMPLATE_ANI[base]
            if p.exists():
                t = sheet2ani.read_ani(p)["hitboxes"]
                if hb < len(t):
                    body = list(t[hb][:4])
                break
        n = self._slot_frames("43") or 0
        num, out = None, None
        try:
            import extras
            import build_soniccd as cdb
            here = self.folder.resolve()
            num = next((e["id"] for e in extras.EXTRAS if Path(e["art"]).resolve() == here), None)
            out = cdb.SHOT_OUT.get(num) if num is not None else None
            radial_from = cdb.RADIAL
        except Exception:  # (a builder that doesn't import: his own box, the rule for every new character)
            radial_from = 1000
        boxes = []
        for k in range(n):
            r = 0 if out is None else out.get(k, 0) if isinstance(out, dict) \
                else (out[k] if 0 < k < len(out) - 1 else 0) if isinstance(out, list) else (out if 0 < k < n - 1 else 0)
            l, t, rr, b = body
            if r > radial_from:
                d = r - radial_from
                boxes.append([l - d, t - d, rr + d, b + d])
            else:
                boxes.append([l, t, rr + r, b])
        return {"cd": {"boxes": boxes, "rule": "reach" if out else "body", "id": num}}

    def ability_rules(self, add=None, remove=None):
        """The rules on combining moves this character breaks now, and with `add` added (or `remove` removed):
        {now: [...], then: [...], new: [...]}."""
        self._need()
        import abilities_registry as reg
        entry = character_json._clean(self.doc.get("abilities") or {"abilities": []})
        base = self.doc.get("base", "sonic")
        then = copy.deepcopy(entry)
        moves = then.setdefault("abilities", [])
        if add:
            kind = self.registry()["abilities"].get(add, {}).get("kind")
            if kind == "setting":
                ex = self.registry()["abilities"][add].get("example") or {}
                then.update(character_json._clean(ex))
            elif add not in moves:
                moves.append(add)
        if remove and remove in moves:
            moves.remove(remove)

        def rules(e):
            return [{"id": r["id"], "level": r["level"], "text": r["text"], "bad": [str(b) for b in bad]}
                    for r, bad in reg.check_rules(e, base)]
        now, after = rules(entry), rules(then)
        ids = {r["id"] for r in now}
        return {"now": now, "then": after, "new": [r for r in after if r["id"] not in ids]}

    def add_ability(self, mid):
        """Add a move (or a setting) with only the fields it needs to work: the values of the character the registry
        takes its example from (the move's own minimal entry, so they're known to work), plus any field the builders
        can't do without. Every option starts off (left out: its default), even when the example character has it on:
        the creator switches options on in the Abilities tab. Per-frame lists (melee_reach...) are sized to the slot's
        frames now, the last value repeated. Fields already set are kept."""
        self._need()
        e = self.registry()["abilities"].get(mid)
        if e is None:
            raise ApiError(f"no ability {mid!r}")
        ab = self.doc.get("abilities") or {}
        ops = []
        if "abilities" not in self.doc:
            ops.append({"op": "set", "path": ["abilities"], "value": {"abilities": []}})
        moves = list(ab.get("abilities", []))
        if e["kind"] != "setting" and mid not in moves:
            ops.append({"op": "set", "path": ["abilities", "abilities"], "value": moves + [mid]})
        for f, v in self._starting_fields(e).items():
            if f in ab:
                continue
            ops.append({"op": "set", "path": ["abilities", f], "value": v})
        return self.edit(ops)

    def _starting_fields(self, e):
        """{field: value} add_ability writes for registry entry `e` (see there)."""
        example = e.get("example") or {}
        out = {}
        for f, d in e["fields"].items():
            if f in example:
                v = example[f]
                if d.get("unit") == "bool" and v is True:
                    continue  # (an option the example character has on: off to start with)
            elif d.get("no_default"):
                v = d.get("example") if d.get("example") is not None else d.get("default")
            else:
                continue  # (an option: left out means its default, off)
            if v is None:
                continue
            if d.get("per_frame") and isinstance(v, list):
                n = self._slot_frames(d["per_frame"])
                if n and v:
                    v = (v + [v[-1]] * n)[:n]
            if d.get("unit") in ("speed", "accel") and isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 0x100:
                v = ("-" if v < 0 else "") + f"0x{abs(v):X}"
            out[f] = v
        return out

    def starting_fields(self, mid):
        """What add_ability would write for `mid` (the picker shows it)."""
        self._need()
        e = self.registry()["abilities"].get(mid)
        if e is None:
            raise ApiError(f"no ability {mid!r}")
        return self._starting_fields(e)

    def _slot_frames(self, slot, doc=None):
        """How many frames an ability slot has as built (its frames times "hold"), or None when it has none."""
        a = ((doc if doc is not None else self.doc).get("ability_animations") or {}).get(str(slot))
        if not isinstance(a, dict) or not a.get("frames"):
            return None
        hold = a.get("hold", 1)
        return len(a["frames"]) * (hold if isinstance(hold, int) and hold > 1 else 1)

    def remove_ability(self, mid):
        """Take a move out of the list, and drop the fields only it reads."""
        self._need()
        reg = self.registry()["abilities"]
        e = reg.get(mid)
        ab = self.doc.get("abilities") or {}
        moves = list(ab.get("abilities", []))
        ops = []
        if mid in moves:
            moves.remove(mid)
            ops.append({"op": "set", "path": ["abilities", "abilities"], "value": moves})
        if e:
            for f in e["fields"]:
                still = [m for m in moves if f in reg.get(m, {}).get("fields", {})]
                if f in ab and not still:
                    ops.append({"op": "del", "path": ["abilities", f]})
                    if "_" + f in ab:
                        ops.append({"op": "del", "path": ["abilities", "_" + f]})
        if not ops:
            return self._info()
        return self.edit(ops)

    # ------------------------------------------------------------------ files and new characters

    def ls(self, path=None, images=True):
        """A folder's subfolders and image files (the UI's file picker in browser mode)."""
        p = Path(path).expanduser() if path else (self.folder or model.TESTMODS)
        if p.is_file():
            p = p.parent
        if not p.is_dir():
            raise ApiError(f"{p} isn't a folder")
        dirs, files = [], []
        try:
            for c in sorted(p.iterdir(), key=lambda c: c.name.lower()):
                if c.name.startswith("."):
                    continue
                if c.is_dir():
                    dirs.append({"name": c.name, "path": str(c), "character": (c / character_json.FILE).exists()})
                elif not images or c.suffix.lower() in IMAGE_EXT:
                    files.append({"name": c.name, "path": str(c)})
        except PermissionError:
            raise ApiError(f"can't read {p}")
        return {"path": str(p.resolve()), "parent": str(p.resolve().parent), "dirs": dirs, "files": files}

    def new_character(self, sheet, parent, id, key, name, full_name="", artists="", base="sonic"):
        """Make a new character folder from a sprite sheet: <parent>/<id>/ with a copy of the sheet (unchanged) and a
        character.json from tools/noswap_ui/new_character.json. Then open it: `check` lists what's left to fill."""
        import re
        from PIL import Image
        sheet = Path(sheet).expanduser()
        if not sheet.is_file():
            raise ApiError(f"{sheet}: no such image")
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", id or ""):
            raise ApiError("the id is lower case letters, digits and '-' (it's the folder's name), e.g. \"someone-newchar\"")
        if not character_json.KEY.match(key or ""):
            raise ApiError("the key is <creator>.<character> in lower case, e.g. \"someone.newchar\"")
        name = (name or "").strip().upper()
        if not re.match(r"^[A-Z0-9 .!?'-]{1,16}$", name):
            raise ApiError("the in-game name is 1-16 capitals, digits, spaces or . ! ? ' -")
        if base not in character_json.TEMPLATE_ANI:
            raise ApiError("base is sonic, tails or knuckles")
        parent = Path(parent).expanduser() if parent else model.TESTMODS
        folder = parent / id
        if folder.exists():
            raise ApiError(f"{folder} already exists")
        with Image.open(sheet) as im:
            src = im.convert("RGBA")
        corners = [src.getpixel(p) for p in ((0, 0), (src.width - 1, 0), (0, src.height - 1),
                                             (src.width - 1, src.height - 1))]
        bg = []
        for r, g, b, a in corners:
            if a and _hexrgb((r, g, b)) not in bg:
                bg.append(_hexrgb((r, g, b)))
        doc = json.loads((Path(__file__).parent / "new_character.json").read_text())
        artist_list = [a.strip() for a in (artists or "").split(",") if a.strip()]
        doc["id"], doc["key"], doc["name"] = id, key, name
        doc["full_name"] = full_name or name.title()
        doc["base"] = base
        doc["credits"]["artists"] = artist_list
        if artist_list:
            doc["credits"]["short"] = ("Sprites: " + ", ".join(artist_list))[:40]
            doc["credits"]["full"] = f"{doc['full_name']} sprites by {', '.join(artist_list)}"
        # the copy gets a plain file name (no spaces or brackets: safer in every tool); its pixels are untouched
        safe = (re.sub(r"[^A-Za-z0-9._-]+", "-", sheet.stem).strip("-.") or id) + sheet.suffix.lower()
        doc["sheet"]["file"] = safe
        if safe != sheet.name:
            doc["sheet"]["_file"] = f"a copy of {sheet.name}, renamed"
        doc["sheet"]["background"] = bg or ["#ff00ff"]
        folder.mkdir(parents=True)
        shutil.copy2(sheet, folder / safe)
        (folder / character_json.FILE).write_text(pretty(doc) + "\n")
        return self.open(str(folder))

    # ------------------------------------------------------------------ build

    def _env(self):
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        if self.folder is not None:
            try:
                self.folder.relative_to(model.TESTMODS)
            except ValueError:  # (a folder outside testmods/ is found through $NOSWAP_CHARACTER_DIRS)
                dirs = [d for d in env.get("NOSWAP_CHARACTER_DIRS", "").split(os.pathsep) if d]
                env["NOSWAP_CHARACTER_DIRS"] = os.pathsep.join(dirs + [str(self.folder)])
        return env

    def _start(self, steps, kind):
        """Run the commands one after another in the background, stopping at the first that fails: {job}."""
        steps = [[str(c) for c in cmd] for cmd in steps]
        shown = " && ".join(" ".join(cmd[0:1] + cmd[2:]) for cmd in steps)
        job = {"id": str(len(self.jobs) + 1), "cmd": shown, "kind": kind, "lines": [], "done": False, "code": None,
               "step": 0, "steps": len(steps), "started": time.time(),
               "dirty": self._dirty() if self.doc is not None else False, "proc": None, "stopped": False}
        env = self._env()

        def pump():
            code = 0
            for i, cmd in enumerate(steps):
                if job["stopped"]:
                    break
                job["step"] = i
                if i:
                    job["lines"].append("")
                proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, bufsize=1)
                job["proc"] = proc
                for line in proc.stdout:
                    job["lines"].append(line.rstrip("\n"))
                code = proc.wait()
                if code:
                    if i + 1 < len(steps):  # (never deploy after a failed build)
                        job["lines"].append(f"(stopped: that step failed with exit {code}; the rest didn't run)")
                    break
            job["code"] = code if not job["stopped"] or code else -15
            job["done"] = True

        threading.Thread(target=pump, daemon=True).start()
        self.jobs[job["id"]] = job
        return {"job": job["id"], "cmd": job["cmd"], "dirty": job["dirty"]}

    def _build_cmd(self, games, dry_run):
        cmd = [sys.executable, "-u", str(TOOLS / "noswap.py"), "build", str(self.folder), "--games", ",".join(games)]
        if dry_run:
            cmd.append("--dry-run")
        if self.build_lock:
            cmd += ["--lock", self.build_lock]
        return cmd

    def _deploy_cmd(self, targets, dry_run):
        targets = [t for t in targets if t in ("origins", "mania")]
        if not targets:
            raise ApiError("pick Origins, Mania or both")
        cmd = [sys.executable, "-u", str(TOOLS / "noswap.py"), "deploy"] + [f"--{t}" for t in targets]
        from noswap_cli import kit
        if kit.active() and self.folder is not None:  # (the kit installs the open character's mods)
            cmd += ["--character", str(self.folder)]
        if dry_run:
            cmd.append("--dry-run")
        if self.build_lock:
            cmd += ["--lock", self.build_lock]
        return cmd

    def build(self, games, dry_run=True):
        """Start `noswap build` for the open character (saved file) in the background: {job}. Never deploys."""
        self._need()
        games = [g for g in games if g in GAMES]
        if not games:
            raise ApiError("pick at least one game")
        return self._start([self._build_cmd(games, dry_run)], "build")

    # ------------------------------------------------------------------ deploy

    def deploy_settings(self):
        """Where `noswap deploy` copies to: the settings file, each game's folder (set or detected, checked), the
        other folders detection found, and which games are running."""
        from noswap_cli import deploy
        t = deploy.targets()
        procs = deploy.running()  # (only a game running from a folder Deploy installs into needs a restart)
        running = [p for g in ("origins", "mania") for p in deploy.running_at(procs, g, t[g]["path"])]
        return {"file": str(deploy.settings_path()), "file_exists": deploy.settings_path().exists(),
                "targets": t, "running": running, "restart": deploy.RESTART,
                "kit": self.kit_status()}

    def check_folder(self, game, path):
        """Check a folder before it's saved: {ok, problems, notes}."""
        from noswap_cli import deploy
        if game not in ("origins", "mania"):
            raise ApiError(f"no game {game!r}")
        path = os.path.expanduser(str(path).strip())
        if not path:
            return {"ok": False, "problems": ["empty: saving clears the setting (detection then picks)"], "notes": []}
        return (deploy.check_origins if game == "origins" else deploy.check_mania)(path)

    def set_deploy_settings(self, origins=None, mania=None):
        """Save the folders (a path sets one, "" clears it back to detection, None leaves it)."""
        from noswap_cli import deploy
        changes = {}
        if origins is not None:
            changes[deploy.KEYS["origins"]] = origins
        if mania is not None:
            changes[deploy.KEYS["mania"]] = mania
        deploy.save_settings(**changes)
        return self.deploy_settings()

    def deploy(self, targets, dry_run=False):
        """Start `noswap deploy` (Origins and/or Mania) in the background: {job}."""
        return self._start([self._deploy_cmd(targets, dry_run)], "deploy")

    def build_deploy(self, targets, dry_run=False):
        """Build the open character for those games, then deploy them, only if the build succeeded: {job}."""
        self._need()
        cmd = self._deploy_cmd(targets, dry_run)
        games = (["s1", "s2", "cd", "s3k"] if "origins" in targets else []) + (["mania"] if "mania" in targets else [])
        return self._start([self._build_cmd(games, dry_run), cmd], "build+deploy")

    def build_log(self, job, since=0):
        j = self.jobs.get(str(job))
        if not j:
            raise ApiError(f"no build {job}")
        return {"lines": j["lines"][since:], "next": len(j["lines"]), "done": j["done"], "code": j["code"],
                "seconds": round(time.time() - j["started"]), "kind": j["kind"], "step": j["step"],
                "steps": j["steps"]}

    def build_stop(self, job):
        j = self.jobs.get(str(job))
        if j and not j["done"]:
            j["stopped"] = True
            if j["proc"]:
                j["proc"].terminate()
        return {"stopped": True}


def _keep_per_frame_in_step(old, new):
    """Per-frame lists (abilities_registry.PER_FRAME: melee_reach, melee_top...) follow their slot's frames: a frame
    removed takes its value with it, a frame added copies its neighbour's (the last value at the end), frames moved
    move their values. Only a list that was in step (one value per frame) is changed; one that wasn't is left for
    `noswap check` and the Abilities tab to point out."""
    from abilities_registry import PER_FRAME
    ab = new.get("abilities")
    if not isinstance(ab, dict):
        return

    def frames(doc, slot):
        a = (doc.get("ability_animations") or {}).get(slot)
        if not isinstance(a, dict) or not isinstance(a.get("frames"), list):
            return [], 1
        hold = a.get("hold", 1)
        return [json.dumps(f, sort_keys=True) for f in a["frames"]], hold if isinstance(hold, int) and hold > 1 else 1

    for slot in sorted({s for s, _ in PER_FRAME.values()}):
        (o, oh), (n, nh) = frames(old, slot), frames(new, slot)
        if (o, oh) == (n, nh) or not n:
            continue
        for field, (s_, _) in PER_FRAME.items():
            v = ab.get(field)
            if s_ != slot or not isinstance(v, list) or not v or len(v) != len(o) * oh:
                continue
            if oh == 1 and nh == 1 and len(n) == len(o) - 1:  # one removed
                i = next((k for k in range(len(n)) if n[k] != o[k]), len(n))
                v = v[:i] + v[i + 1:]
            elif oh == 1 and nh == 1 and len(n) == len(o) + 1:  # one added
                i = next((k for k in range(len(o)) if n[k] != o[k]), len(o))
                v = v[:i] + [v[i - 1] if i else v[0]] + v[i:]
            elif oh == 1 and nh == 1 and sorted(n) == sorted(o):  # reordered
                pool = {}
                for k, f in enumerate(o):
                    pool.setdefault(f, []).append(k)
                v = [v[pool[f].pop(0)] for f in n]
            else:  # (anything else: grow or shrink at the end)
                want = len(n) * nh
                v = (v + [v[-1]] * want)[:want]
            ab[field] = v


def _drawn(img, px, py):
    """A placed frame's drawn pixels relative to the object's position (the hit-box panel's "fit to sprite"):
    drawn [left, top, right, bottom] (edges: right / bottom are one past the last opaque pixel), and diag [x, y], the
    opaque pixel furthest up and forward (largest x - y: the Ear Grapple's tip)."""
    a = img.getchannel("A")
    b = a.getbbox()
    if not b:
        return {"drawn": None, "diag": None}
    w = img.width
    best, at = None, None
    data = a.getdata()
    for k, v in enumerate(data):
        if v:
            x, y = k % w, k // w
            if best is None or x - y > best:
                best, at = x - y, (x, y)
    return {"drawn": [px + b[0], py + b[1], px + b[2], py + b[3]], "diag": [px + at[0], py + at[1]]}


def _label(ref):
    if isinstance(ref, str):
        return ref
    if isinstance(ref, dict):
        opts = [k for k in ("flip", "rotate", "circle") if ref.get(k)]
        base = ref.get("frame") or ("layered" if "layers" in ref else "rect")
        return base + (" (" + ", ".join(opts) + ")" if opts else "")
    return "[" + ",".join(map(str, ref)) + "]"


def _target(where):
    """Where in the UI a check finding points: {tab, ...}."""
    w = where or ""
    parts = w.split(" ", 1)
    head, rest = parts[0], parts[1] if len(parts) > 1 else ""
    if head == "character.json":
        seg = rest.split(".")[0].split("[")[0]
        return _target(seg + (" " + ".".join(rest.split(".")[1:]) if "." in rest else "")) or {"tab": "character"}
    if head == "frames":
        return {"tab": "sheet", "frame": rest or None}
    if head in ("animations", "animations_sonic2", "special_stage", "ability_animations"):
        return {"tab": "anims", "section": head, "anim": rest or None}
    if head in ("Sonic1", "Sonic2"):
        if rest.startswith("animations"):
            return {"tab": "anims"}
        return {"tab": "anims", "section": "animations", "anim": rest}
    if head == "ability":
        return {"tab": "anims", "section": "ability_animations", "anim": rest.split(" ")[0]}
    if w.startswith("special stage"):
        return {"tab": "anims", "section": "special_stage", "anim": w[len("special stage "):] or None}
    if head == "s3k_victory":
        return {"tab": "anims", "section": "s3k_victory"}
    if head in ("ui", "ending"):
        return {"tab": "hud", "element": rest or None}
    if head.startswith("palette") or w.startswith("Mania palette"):
        return {"tab": "palette"}
    if head == "abilities" or head == "flags" and rest == "roll":
        move = rest.split(" ")[0] if rest and not rest.startswith("rule") else None
        return {"tab": "abilities", "move": move}
    if w in ("Sonic 1", "Sonic 2", "Sonic CD", "Sonic 3&K", "Sonic Mania", "S3&K"):
        return {"tab": "abilities"}
    if head.startswith("credits"):
        return {"tab": "character", "field": head}
    if head.startswith("sheet"):
        return {"tab": "character", "field": head}
    if head in ("id", "key", "name", "full_name", "base", "flags", "games", "card", "card.sheet", "format"):
        return {"tab": "character", "field": head}
    return None
