#!/usr/bin/env python3
"""The ability registry: every move a NoSwap character can have, for creators and for `noswap check`.

    python3 tools/abilities_registry.py --write    regenerate docs/abilities.json and docs/abilities.md
    python3 tools/abilities_registry.py --check    every move and field described; the generated files up to date

Two halves:
- the words (names, descriptions, what each field means, which slots to draw) are hand-written in
  tools/abilities_text.py: edit them there;
- everything else is read from the pipeline itself, so it can't drift:
  - the moves: tools/abilities.py's docstring list plus every name a character uses (noswap_cli.abilities_info);
  - the fields' types and example values: the existing characters' ABILITIES entries;
  - defaults: the `.get("field", default)` calls in the builders (gen_s3k_header.py first);
  - per-game support: Sonic 1/2 and CD from the code that generates them (tools/abilities.py, build_soniccd.py and the
    move's own module), S3&K from the fields the move sets (gen_s3k_header.ability_fields) and whether the DLL
    (native/src) reads them, Mania from the mod's MOVES_DONE list (native/mania/src/NoSwapMania.c) or its code reading
    those fields;
  - per-game animation slots: cd_config.ABILITY_SLOTS and build_s3k_art.py's slot tables;
  - the rules on combining moves (RULES below), each one a check the builders make (a build that would stop) or a
    combination that silently doesn't work.

Read-only over the pipeline: it never writes anything but docs/abilities.json and docs/abilities.md.
"""
import ast
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

JSON_OUT = REPO / "docs" / "abilities.json"
MD_OUT = REPO / "docs" / "abilities.md"
GAMES = ["s1", "s2", "cd", "s3k", "mania"]
GAME_NAMES = {"s1": "Sonic 1", "s2": "Sonic 2", "cd": "Sonic CD", "s3k": "Sonic 3&K", "mania": "Sonic Mania"}
GAME_SHORT = {"s1": "S1", "s2": "S2", "cd": "CD", "s3k": "3K", "mania": "MA"}

UNITS = {
    "frames": "game frames (60 a second)",
    "ticks": "game frames per animation frame",
    "speed": "px per frame in 16.16 fixed point: 0x10000 (65536) is 1 px a frame; write it as a hex string such as "
             "\"0x60000\" (6 px a frame) or a plain number",
    "accel": "px per frame gained or lost each frame, 16.16 fixed point: 0x1000 is 1/16 px a frame",
    "px": "pixels",
    "mult": "a multiplier: 1.0 is unchanged",
    "bool": "true or false",
    "count": "a whole number",
    "deg": "degrees per frame",
    "list": "a list",
    "frame list": "a list of animation frame numbers (0 is the slot's first frame)",
    "px list": "a list of pixel distances, one per animation frame",
    "object": "a JSON object (see its description and the example)",
    "sound": "a sound name",
}

# Per-frame lists: one value per frame of an ability animation slot (S1/S2 numbers; the frames as built, "hold"
# included). {field: (slot, group)}: the fields of a group are read together and must be the same length (the build
# stops otherwise: tools/abilities.py melee_tables), and `noswap check` wants each as long as its slot's frames.
# Without melee_air_reach the air move is the ground one, so melee_air_top / melee_air_bottom go with it.
#
# PER_FRAME_GROUPS describes each group's shape for the character editor's hit-box panel (tools/noswap_ui/web/js/
# hitbox.js draws it on the frames and drags its edges), so a new group needs only an entry here:
#   move: the move whose card shows it; slot: its animation slot; label: the panel's switch;
#   shape "box": fields {"reach", "top", "bottom"} (px from his centre facing right; defaults: a field left out);
#     behind: the box's back edge (fixed, not a field); min_reach: {engine: the least reach that engine uses};
#     radial: the option that turns it into a square all round him (reach on every side; top / bottom unused);
#     same_as: the group the game uses while `fields.reach` is left out (the air move is then the ground one);
#   shape "point": fields {"point"}: one [x, y] per frame;
#   ticks_field / ticks: game frames per frame of the move (the preview's timing).
# The geometry is the games' own (tools/abilities.py melee_function: S1/S2 player.hitbox* = -10, top, reach, bottom,
# mirrored facing left; tools/build_s3k_art.py: S3&K's and Mania's pose frames' box 0 = -10, top, max(10, reach),
# bottom; Sonic CD doesn't read it: backend.per_frame_info).
PER_FRAME_GROUPS = {
    "melee ground": dict(move="melee", slot="43", label="On the ground", shape="box",
                         fields={"reach": "melee_reach", "top": "melee_top", "bottom": "melee_bottom"},
                         defaults={"top": -20, "bottom": 20}, behind=-10, min_reach={"s3k": 10, "mania": 10},
                         radial="melee_radial", ticks_field="melee_ticks"),
    "melee air": dict(move="melee", slot="44", label="In the air", shape="box",
                      fields={"reach": "melee_air_reach", "top": "melee_air_top", "bottom": "melee_air_bottom"},
                      defaults={"top": -20, "bottom": 20}, behind=-10, min_reach={"s3k": 10, "mania": 10},
                      radial="melee_radial", ticks_field="melee_ticks", same_as="melee ground"),
    "ear grapple": dict(move="ear_grapple", slot="41", label="The ear's tip", shape="point",
                        fields={"point": "grapple_tip"}, ticks=1, max_frames=8),
}
PER_FRAME = {f: (g["slot"], name) for name, g in PER_FRAME_GROUPS.items() for f in g["fields"].values()}

# Settings the builders read through a helper rather than by the field's name: {id: [regexes of the helper's use]}
HELPERS = {"ability_cycle": [r"\bab\.cycle\("]}

# Where the S1/S2 and CD code lives, beyond tools/abilities.py and build_soniccd.py (the moves with a module of their own)
V4_FILES = ["abilities.py", "noswap_common.py", "build_sonic1.py", "build_sonic2.py", "shots_v4.py"]
CD_FILES = ["build_soniccd.py", "cd_config.py", "shots_v3.py"]


# ----------------------------------------------------------------------------------------------------------- reading


@lru_cache(None)
def _text():
    import abilities_text
    return abilities_text


@lru_cache(None)
def _ab():
    import abilities
    return abilities


@lru_cache(None)
def _src(name):
    p = TOOLS / name
    return p.read_text() if p.exists() else ""


@lru_cache(None)
def _code(name):
    """A tool file's source without its module docstring (the docstring lists every move, so it proves nothing)."""
    s = _src(name)
    try:
        doc = ast.get_docstring(ast.parse(s), clean=False)
    except SyntaxError:
        return s
    return s.replace(doc, "", 1) if doc else s


@lru_cache(None)
def _consts(name):
    """{NAME: value} of a tool file's top-level literal assignments (tuples, lists, dicts of literals)."""
    out = {}
    for node in ast.parse(_src(name)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return out


@lru_cache(None)
def air_moves():
    """The jump abilities tools/abilities.py's functions() maps to air code (its air_of): one per character runs."""
    m = re.search(r"air_of = (\{.*?\})\n", _src("abilities.py"), re.S)
    return sorted(re.findall(r'"(\w+)":', m.group(1))) if m else []


@lru_cache(None)
def mania_done():
    """native/mania/src/NoSwapMania.c MOVES_DONE: the moves the Mania mod has a module for."""
    s = (REPO / "native" / "mania" / "src" / "NoSwapMania.c").read_text(errors="replace")
    m = re.search(r"MOVES_DONE\[\]\s*=\s*\{(.*?)\};", s, re.S)
    return set(re.findall(r'"(\w+)"', m.group(1))) if m else set()


@lru_cache(None)
def defaults():
    """{field: default} from `.get("field", <literal>)` in the builders (gen_s3k_header.py first: what a package gets),
    and the fields the code indexes directly (`c["field"]`: needed whenever the move is on): {field: "required"}."""
    found, required = {}, set()
    for name in ["gen_s3k_header.py", "abilities.py", "build_soniccd.py", "shots_v4.py", "shots_v3.py",
                 "star_grab.py", "head_throw.py", "anchor_throw.py", "water_walk.py", "treasure_sense.py",
                 "monitor_swap.py", "psycho_grab.py", "free_swim.py", "ninjutsu.py", "free_flight.py", "voltteccer.py", "pot_magic.py"]:
        src = _src(name)
        if not src:
            continue
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call) and len(node.args) == 2 and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str) and (
                    (isinstance(node.func, ast.Attribute) and node.func.attr == "get")
                    or (isinstance(node.func, ast.Name) and node.func.id == "get")):
                try:
                    v = ast.literal_eval(node.args[1])
                except ValueError:
                    continue
                found.setdefault(node.args[0].value, v)
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                    and isinstance(node.slice.value, str):
                required.add(node.slice.value)
    return found, required


@lru_cache(None)
def _native_src(sub):
    root = REPO / sub
    return "\n".join(p.read_text(errors="replace") for pat in ("*.h", "*.c", "*.cpp") for p in sorted(root.glob(pat)))


@lru_cache(None)
def native_reads(sub, field):
    """Whether native code under `sub` reads a field: a member access (`c.pogoSpeed`, `e->ab.batGlide`,
    `&ExtraAbilities::topSpeed`) or a JSON lookup by name (`Json_Get(ab, "cycleMoves")`). Plain words don't count (the
    comments are full of move names)."""
    f = re.escape(field)
    return re.search(r"(?:\.|->|::)\s*%s\b|\"%s\"" % (f, f), _native_src(sub)) is not None


@lru_cache(None)
def _own_ids():
    """NoSwap's own characters (key noswap.*): the examples, types and "used by" lists come from them only, never from
    a creator's character in progress in the same tree (its entry may be half done)."""
    import extras
    return {e["id"] for e in extras.EXTRAS if str(e.get("key", "noswap.")).startswith("noswap.")}


def _users():
    """{move or field: [(extra id, name, base)]} over the existing characters, in extras.py's order."""
    ab = _ab()
    import extras
    out = {}
    for e in extras.EXTRAS:
        c = ab.ABILITIES.get(e["id"])
        if not c or e["id"] not in _own_ids():
            continue
        for k in list(c.get("abilities", [])) + [k for k in c if k != "abilities" and not k.startswith("_")]:
            who = out.setdefault(k, [])
            if not who or who[-1][0] != e["id"]:  # (a move that's also a field name: once per character)
                who.append((e["id"], e.get("name") or e["art"].name, e.get("base", "sonic")))
    return out


def _field_types():
    ab = _ab()
    seen = {}
    for i, c in ab.ABILITIES.items():
        if i not in _own_ids():
            continue
        for k, v in c.items():
            seen.setdefault(k, set()).add({"tuple": "list", "dict": "object", "NoneType": "null"}.get(
                type(v).__name__, type(v).__name__))
    return seen


# ----------------------------------------------------------------------------------------------------------- per game


def _s3k_fields(entry_with, entry_without):
    """The S3&K fields the difference between two entries changes (gen_s3k_header.ability_fields)."""
    import gen_s3k_header as g
    try:
        a = {n: v for _, n, _, v in g.ability_fields(entry_with, "registry")}
        b = {n: v for _, n, _, v in g.ability_fields(entry_without, "registry")}
    except (SystemExit, Exception):
        return []
    return [n for n in a if a[n] != b.get(n)]


def _home_file(mid):
    """A move's own module (tools/<name>.py), if its docstring line or its name points to one."""
    if (TOOLS / f"{mid}.py").exists() and mid not in ("abilities",):
        return f"{mid}.py"
    doc = _ab().__doc__ or ""
    m = re.search(rf"^  {mid}\s(.*?)(?=^  \w|\Z)", doc, re.S | re.M)
    for f in re.findall(r"tools/(\w+)\.py", m.group(1) if m else ""):
        if (TOOLS / f"{f}.py").exists():
            return f"{f}.py"
    return None


def _quoted(name, files):
    q = re.compile(r"""["']%s["']""" % re.escape(name))
    return [f for f in files if q.search(_code(f))]


def game_support(mid, kind, fields, example):
    """{game: {"support": "yes" | "partial" | "no", "how": the evidence}} for one registry entry."""
    out = {}
    home = _home_file(mid)
    names = [mid] if kind != "setting" else list(fields)
    # Sonic 1 / 2 (one RSDKv4 player script for both)
    v4 = [f for n in names for f in _quoted(n, V4_FILES)]
    if home and re.search(r"^def v4_", _src(home), re.M):
        v4.append(home)
    v4 = sorted(set(v4))
    for g in ("s1", "s2"):
        out[g] = {"support": "yes" if v4 else "no",
                  "how": f"generated by {', '.join('tools/' + f for f in v4)}" if v4
                  else "no Sonic 1/2 code reads it"}
    # Sonic CD
    cd = sorted({f for n in names for f in _quoted(n, CD_FILES)}
                | {f for f in CD_FILES for h in HELPERS.get(mid, ()) if re.search(h, _code(f))})
    if home and re.search(r"^def cd_", _src(home), re.M):
        cd = sorted(set(cd) | {home})
    out["cd"] = {"support": "yes" if cd else "no",
                 "how": f"generated by {', '.join('tools/' + f for f in cd)}" if cd else "no Sonic CD code reads it"}
    # S3&K: the fields the move sets, read by the DLL
    entry = dict(example or {"abilities": [mid] if kind != "setting" else []})  # (no character uses it: the move alone)
    without = {k: v for k, v in entry.items() if k not in fields}
    if kind != "setting":
        without["abilities"] = [a for a in entry.get("abilities", []) if a != mid]
        without.pop("ability_cycle", None) if mid in entry.get("ability_cycle", []) else None
    s3k = _s3k_fields(entry, without)
    read = [n for n in s3k if native_reads("native/src", n)]
    if mid == "shot":
        s3k = ["shot"]
        read = ["ReadShot"] if re.search(r"\bReadShot\(", _native_src("native/src")) else []
    out["s3k"] = {"support": "yes" if read else "no",
                  "how": f"the DLL reads {', '.join(read[:6])}{' ...' if len(read) > 6 else ''}" if read
                  else ("no S3&K field for it (gen_s3k_header.ability_fields)" if not s3k
                        else f"no DLL code reads {', '.join(s3k)}")}
    # Mania: its MOVES_DONE list for moves; the fields it reads for the rest
    mread = [n for n in s3k if native_reads("native/mania/src", n)]
    if mid == "shot":
        mread = ["ReadShot"] if re.search(r"\bReadShot\(", _native_src("native/mania/src")) else []
    if mid in mania_done():
        out["mania"] = {"support": "yes", "how": "in the Mania mod's MOVES_DONE (native/mania/src/NoSwapMania.c)"}
    elif mread and (kind == "setting" or len(mread) == len(s3k)):
        unread = [n for n in s3k if n not in mread and mid != "shot"]
        out["mania"] = {"support": "yes", "how": f"the Mania mod reads {', '.join(mread[:6])}"
                                                 f"{' ...' if len(mread) > 6 else ''}"
                                                 + (f" (not {', '.join(unread)})" if unread else "")}
    else:
        out["mania"] = {"support": "no", "how": "the Mania mod has no code for it yet"
                        + (f" (reads none of {', '.join(s3k[:6])})" if s3k else "")}
    for g, note in (_text().ABILITIES.get(mid, {}).get("game_notes") or {}).items():
        if g in out and out[g]["support"] == "yes" and note.startswith("partial"):
            out[g]["support"] = "partial"
        if g in out:
            out[g]["note"] = note
    return out


def slot_numbers(slot):
    """{game: the slot's number there} (None: not drawn there), from the build's own tables."""
    cd = _consts("cd_config.py").get("ABILITY_SLOTS", {})
    s3 = _consts("build_s3k_art.py")
    s3k = dict(s3.get("ABILITY_SLOTS", {}))
    s3k.update(s3.get("SURGE_SLOTS", {}))
    if "ROLL_SLOT" in s3:
        s3k[s3["ROLL_SLOT"]] = s3.get("ROLL_OFFSET")
    if "AIR_SHOT_SLOT" in s3:
        s3k[s3["AIR_SHOT_SLOT"]] = s3.get("AIR_SHOT_OFFSET")
    k = s3k.get(slot)
    return {"s1": slot, "s2": slot, "cd": cd.get(slot), "s3k": None if k is None else f"extra {k}",
            "mania": None if k is None else f"extra {k} (S3&K's layout)"}


# ----------------------------------------------------------------------------------------------------------- rules


def _has(e, m):
    return m in e.get("abilities", [])


def _jump_moves(e):
    cycle = set(e.get("ability_cycle", []))
    return [m for m in e.get("abilities", []) if m in air_moves() and m not in cycle]


@lru_cache(None)
def jump_button_moves():
    """The moves tools/abilities.py's apply_player makes the jump ability itself (the second jump press runs them, in
    place of Sonic's): its `for a, name in ((...))` list."""
    m = re.search(r'ability = next\(\(f"NoSwap_\{name\}".*?for a, name in \((.*?)\)\s*\n', _src("abilities.py"), re.S)
    return tuple(re.findall(r'\("(\w+)", "\w+"\)', m.group(1))) if m else ()


def _on_jump_button(e):
    """The moves this entry runs on the second jump press (aim_dash with aim_dash_y and screw_kick without kick_jump
    start with Y instead; ability_cycle moves are all on jump)."""
    return [m for m in e.get("abilities", []) if m in jump_button_moves()
            and not (m == "aim_dash" and e.get("aim_dash_y")) and not (m == "screw_kick" and not e.get("kick_jump"))] \
        + (["ability_cycle"] if e.get("ability_cycle") else [])


def _only(e, mid, allowed):
    bad = [a for a in e.get("abilities", []) if a not in allowed]
    return (bad + (["a \"shot\""] if e.get("shot") else []) + (["melee_reach"] if e.get("melee_reach") else [])) \
        if _has(e, mid) else []


def _cd_list(name):
    return _consts("build_soniccd.py").get(name, ())


# Each rule: id, the moves it's about, games, level ("error": the build stops; "warning": it builds but doesn't work as
# meant), the text, where the code checks it, and test(entry, base) -> what breaks it ([] / None / False: fine).
RULES = [
    dict(id="one-air-move", moves=["(air moves)"], games=["s1", "s2"], level="warning",
         text="The mid-air moves listed under the table (most jump abilities, plus wall_cling and screw_kick) share "
              "one slot for their mid-air code: Sonic 1/2 keep only the last one in the list, and no character has "
              "tried two in the other games. Use ability_cycle to switch between several jump abilities. "
              "double_jump, water_swim and hover aren't in that slot.",
         source="tools/abilities.py functions(): one air function per character (air_of)",
         test=lambda e, b: _jump_moves(e) if len(_jump_moves(e)) > 1 else []),
    dict(id="hover-needs", moves=["hover"], games=GAMES, level="warning",
         text="hover only follows jet_dash, rocket_ride or ear_grapple; on its own it does nothing.",
         source="tools/abilities.py jet_dash_air, falling_hover_users",
         test=lambda e, b: _has(e, "hover") and not any(_has(e, m) for m in ("jet_dash", "rocket_ride", "ear_grapple"))),
    dict(id="star-grab-alone", moves=["star_grab"], games=["s1", "s2", "cd"], level="error",
         text="star_grab takes the jump-ability state and slots 41-43 for itself: only physics alongside it, and no "
              "shot or melee.",
         source="tools/star_grab.py check", test=lambda e, b: _only(e, "star_grab", ("star_grab", "physics"))),
    dict(id="head-throw-alone", moves=["head_throw"], games=["s1", "s2", "cd"], level="error",
         text="head_throw takes the jump-ability state and slots 41-43 for itself: only physics alongside it, and no "
              "shot or melee.",
         source="tools/head_throw.py check", test=lambda e, b: _only(e, "head_throw", ("head_throw", "physics"))),
    dict(id="anchor-throw-alone", moves=["anchor_throw"], games=["s1", "s2", "cd"], level="error",
         text="anchor_throw takes the jump-ability state and slots 41 / 43: only water_walk, no_breathing and physics "
              "alongside it, and no shot or melee.",
         source="tools/anchor_throw.py check",
         test=lambda e, b: _only(e, "anchor_throw", ("anchor_throw", "water_walk", "no_breathing", "physics"))),
    dict(id="free-swim-alone", moves=["free_swim"], games=["s1", "s2", "cd"], level="error",
         text="free_swim takes the jump-ability state and slots 41-43: only no_breathing and physics alongside it, no "
              "shot or melee, and swim_dirs 8.",
         source="tools/free_swim.py check",
         test=lambda e, b: _only(e, "free_swim", ("free_swim", "no_breathing", "physics"))
         + (["swim_dirs"] if _has(e, "free_swim") and e.get("swim_dirs", 8) != 8 else [])),
    dict(id="free-flight-alone", moves=["free_flight"], games=["s1", "s2", "cd"], level="error",
         text="free_flight takes the jump-ability state and slots 41-42: only no_breathing and physics alongside it, no "
              "shot or melee, and loop_points 6 to 12.",
         source="tools/free_flight.py cfg",
         test=lambda e, b: _only(e, "free_flight", ("free_flight", "no_breathing", "physics"))
         + (["loop_points"] if _has(e, "free_flight") and not 6 <= e.get("loop_points", 12) <= 12 else [])),
    dict(id="voltteccer-jump", moves=["voltteccer"], games=["s1", "s2", "cd"], level="error",
         text="voltteccer takes the jump ability, its state and slot 41: alongside it only melee, magnetic, "
              "no_breathing, fire_immune and physics (a shot / shot2 on Y is fine), no ability_cycle, and the art's "
              "charge_palettes for its charged flash.",
         source="tools/voltteccer.py cfg",
         test=lambda e, b: [a for a in e.get("abilities", []) if _has(e, "voltteccer") and a not in (
             "voltteccer", "melee", "magnetic", "no_breathing", "fire_immune", "physics")]
         + (["ability_cycle"] if _has(e, "voltteccer") and e.get("ability_cycle") else [])),
    dict(id="water-swim-slot-47", moves=["water_swim", "ray_glide", "wall_cling"], games=["s1", "s2"], level="error",
         text="water_swim draws its stroke in slot 47, which ray_glide and wall_cling use too.",
         source="tools/abilities.py water_swim_air",
         test=lambda e, b: _has(e, "water_swim") and [m for m in ("ray_glide", "wall_cling") if _has(e, m)]),
    dict(id="water-swim-cd", moves=["water_swim", "spin_attack", "high_kick", "thunder_zip", "power_surge"],
         games=["cd"], level="error",
         text="In Sonic CD water_swim's timer and slot are shared with spin_attack, high_kick, thunder_zip and "
              "power_surge (and with puddle_slide plus a dash-type move).",
         source="tools/build_soniccd.py water_swim / swim_var",
         test=lambda e, b: _has(e, "water_swim") and (
             [m for m in ("spin_attack", "high_kick", "thunder_zip", "power_surge") if _has(e, m)]
             or ([m for m in _cd_list("VALUE6_MOVES") if _has(e, m)] if _has(e, "puddle_slide") else []))),
    dict(id="sink-cd", moves=["sink"], games=["cd"], level="error",
         text="In Sonic CD the Shadow Sink's timer is shared with many moves: sink can't be combined with "
              + ", ".join(_cd_list("SINK_VALUE4_MOVES")) + ", melee_cooldown or ability_cycle.",
         source="tools/build_soniccd.py sink (SINK_VALUE4_MOVES)",
         test=lambda e, b: _has(e, "sink") and (
             [m for m in _cd_list("SINK_VALUE4_MOVES") if _has(e, m)]
             + (["melee_cooldown"] if e.get("melee_cooldown") else [])
             + (["ability_cycle"] if e.get("ability_cycle") else []))),
    dict(id="phase-warp-cd", moves=["phase_warp"], games=["cd"], level="error",
         text="In Sonic CD the Phase Warp's direction and speed share values with "
              + ", ".join(_cd_list("WARP_MOVES")) + " (and a down + Y shot).",
         source="tools/build_soniccd.py warp_check (WARP_MOVES)",
         test=lambda e, b: _has(e, "phase_warp") and [m for m in _cd_list("WARP_MOVES") if _has(e, m)]),
    dict(id="high-kick-cd", moves=["high_kick"], games=["cd"], level="error",
         text="In Sonic CD high_kick's values are shared with ray_glide, aim_dash, ear_grapple, spirit_flight, "
              "triple_jump, wall_cling, power_surge, thunder_zip, puddle_slide, charge, spin_attack and "
              "melee_cooldown.",
         source="tools/build_soniccd.py high_kick",
         test=lambda e, b: _has(e, "high_kick") and (
             [m for m in ("ray_glide", "aim_dash", "ear_grapple", "spirit_flight", "triple_jump", "wall_cling",
                          "power_surge", "thunder_zip", "puddle_slide", "charge", "spin_attack") if _has(e, m)]
             + (["melee_cooldown"] if e.get("melee_cooldown") else []))),
    dict(id="ground-slide-cd", moves=["ground_slide", "pogo", "puddle_slide"], games=["cd"], level="error",
         text="In Sonic CD ground_slide shares its value with pogo, and puddle_slide has its own slide code.",
         source="tools/build_soniccd.py (ground_slide)",
         test=lambda e, b: _has(e, "ground_slide") and [m for m in ("pogo", "puddle_slide") if _has(e, m)]),
    dict(id="no-stomp-cd", moves=["no_stomp", "ground_slide", "breaks_walls", "fire_immune", "charge"], games=["cd"],
         level="error",
         text="In Sonic CD no_stomp's Slide (with ground_slide) breaks walls through the byte fire_immune, breaks_walls and "
              "charge's juggernaut mark use.",
         source="tools/build_soniccd.py (startup abilities: no_stomp)",
         test=lambda e, b: _has(e, "no_stomp") and _has(e, "ground_slide")
         and [m for m in ("breaks_walls", "fire_immune", "charge") if _has(e, m)]),
    dict(id="no-stomp-surge", moves=["no_stomp", "ground_slide", "power_surge", "charge"], games=["s1", "s2"],
         level="error",
         text="In Sonic 1/2 no_stomp's Slide (with ground_slide) breaks monitors through NoSwap_flags' surging bit, which "
              "power_surge and charge use.",
         source="tools/abilities.py no_stomp_slide_after",
         test=lambda e, b: _has(e, "no_stomp") and _has(e, "ground_slide")
         and [m for m in ("power_surge", "charge") if _has(e, m)]),
    dict(id="fire-immune-cd", moves=["fire_immune", "breaks_walls", "charge"], games=["cd"], level="error",
         text="In Sonic CD fire_immune shares one byte with breaks_walls and with charge's juggernaut mark.",
         source="tools/build_soniccd.py (startup abilities, cd_charge)",
         test=lambda e, b: _has(e, "fire_immune") and [m for m in ("breaks_walls", "charge") if _has(e, m)]),
    dict(id="shot-ray-glide-cd", moves=["shot", "ray_glide"], games=["cd"], level="error",
         text="In Sonic CD a shot's pose shares its value with ray_glide.",
         source="tools/build_soniccd.py cd_shot",
         test=lambda e, b: bool(e.get("shot")) and _has(e, "ray_glide")),
    dict(id="puddle-slide-melee", moves=["puddle_slide", "melee"], games=["s1", "s2"], level="error",
         text="With puddle_slide, the melee needs melee_cooldown (the slide holds Y off through it).",
         source="tools/abilities.py puddle_slide_function",
         test=lambda e, b: _has(e, "puddle_slide") and _has(e, "melee") and not e.get("melee_cooldown")),
    dict(id="ability-cycle", moves=["ability_cycle"], games=["s1", "s2", "cd", "s3k"], level="error",
         text="ability_cycle: 2 to 4 different moves of double_jump, screw_kick, jet_dash, umbrella, each also in "
              "\"abilities\"; the melee on Y with no melee_cooldown; no hover, no umbrella_attack; screw_kick "
              "only with kick_jump.",
         source="tools/abilities.py cycle",
         test=lambda e, b: (lambda c: c and (
             [m for m in c if m not in _ab().CYCLE_MOVES or not _has(e, m)]
             + (["2-4 moves"] if not 2 <= len(c) <= 4 or len(set(c)) != len(c) else [])
             + (["melee"] if not _has(e, "melee") else [])
             + [k for k in ("melee_cooldown", "umbrella_attack") if e.get(k)]
             + (["hover"] if _has(e, "hover") else [])
             + (["kick_jump"] if "screw_kick" in c and not e.get("kick_jump") else [])))(e.get("ability_cycle", []))),
    dict(id="swap-shots", moves=["monitor_swap"], games=["s1", "s2", "cd", "s3k"], level="error",
         text="swap_shots needs monitor_swap and no \"shot\" / \"shot2\" of its own; swap_icon needs swap_shots; "
              "monitor_swap is a list of at most 8 different names.",
         source="tools/abilities.py check_swap_shots, tools/monitor_swap.py",
         test=lambda e, b: (["swap_shots without monitor_swap"] if e.get("swap_shots") and not e.get("monitor_swap")
                            else []) + (["swap_shots with shot / shot2"] if e.get("swap_shots") and (
                                e.get("shot") or e.get("shot2")) else [])
         + (["swap_icon without swap_shots"] if e.get("swap_icon") and not e.get("swap_shots") else [])
         + (["monitor_swap list"] if e.get("monitor_swap") is not None and (
             not isinstance(e["monitor_swap"], list) or len(set(e["monitor_swap"])) != len(e["monitor_swap"])
             or len(e["monitor_swap"]) > 8) else [])),
    dict(id="shot2-needs-shot", moves=["shot"], games=["s1", "s2", "cd", "s3k"], level="error",
         text="shot2 needs a \"shot\" thrown with Y alone (no \"input\").",
         source="tools/abilities.py check_shot2",
         test=lambda e, b: bool(e.get("shot2")) and (not isinstance(e.get("shot"), dict) or "input" in e["shot"])),
    dict(id="shot-input-melee", moves=["shot", "melee"], games=["s1", "s2"], level="error",
         text="A shot with \"input\" \"down\" or \"up\" needs the melee (Y alone stays the melee); \"slam\" needs "
              "hammer_drop.",
         source="tools/abilities.py check_shot",
         test=lambda e, b: isinstance(e.get("shot"), dict) and (
             (e["shot"].get("input") in ("down", "up") and not _has(e, "melee"))
             or (e["shot"].get("input") == "slam" and not _has(e, "hammer_drop")))),
    dict(id="bat-glide-base", moves=["bat_glide"], games=GAMES, level="warning",
         text="bat_glide changes Knuckles' own glide: it needs base \"knuckles\".",
         source="tools/abilities.py (bat_glide patches the Knuckles glide states)",
         test=lambda e, b: _has(e, "bat_glide") and b not in (None, "knuckles")),
    dict(id="base-keeps-jump", moves=["(jump-button moves)"], games=GAMES, level="error",
         text="A character built on Tails or Knuckles keeps the base's own move on the jump button: Tails' flight, or "
              "Knuckles' glide and climb. A move started by pressing jump again in mid-air can't replace it (Sonic 1, "
              "2 and CD's build stops; S3&K never starts it). Use base \"sonic\" for such a move, or a "
              "move started with Y (aim_dash with aim_dash_y, Charmy's way, keeps the flight on jump); moves on Y, "
              "the ground and settings work with any base.",
         source="tools/abilities.py apply_base_characters; native/src/NoSwapS3K.cpp (base != 0: no ready jump)",
         test=lambda e, b: _on_jump_button(e) if b in ("tails", "knuckles") else []),
    dict(id="needs-melee", moves=["psycho_grab", "melee_whip"], games=GAMES, level="warning",
         text="psycho_grab and melee_whip are parts of the melee (Y): they need \"melee\" in the list.",
         source="tools/psycho_grab.py, tools/abilities.py whips",
         test=lambda e, b: [] if _has(e, "melee") else (
             [m for m in ("psycho_grab",) if _has(e, m)] + (["melee_whip"] if "melee_whip" in e else []))),
    dict(id="melee-variants", moves=["melee_run", "melee_up"], games=GAMES, level="error",
         text="melee_run and melee_up are poses of the melee (Y): they need \"melee\", their frames are slots 45 / 46 "
              "(not with aim_dash, melee_whip, charge, psycho_grab, star_grab, head_throw, rocket_burst, free_flight or "
              "free_swim), and the melee must be a move of its own (no shot on Y alone, melee_nuke, melee_cost or "
              "ability_cycle). Sonic CD keeps the pose in Object[5].Value5: not with wall_cling, ray_glide, "
              "ear_grapple, high_kick, triple_jump, puddle_slide, rocket_burst, charge, spin_attack, spirit_flight, "
              "water_swim, phase_warp or thunder_zip.",
         source="tools/abilities.py check_variants; tools/build_soniccd.py cd_variants",
         test=lambda e, b: [] if not (e.get("melee_run") or e.get("melee_up")) else (
             ([] if _has(e, "melee") else ["melee missing"])
             + [m for m in ("aim_dash", "melee_whip", "charge", "psycho_grab", "star_grab", "head_throw", "rocket_burst",
                            "free_flight", "free_swim", "wall_cling", "ray_glide", "ear_grapple", "high_kick",
                            "triple_jump", "puddle_slide", "spin_attack", "spirit_flight", "water_swim", "phase_warp",
                            "thunder_zip") if _has(e, m) or m in e]
             + [k for k in ("melee_nuke", "melee_cost", "ability_cycle") if e.get(k)]
             + (["a shot on Y"] if isinstance(e.get("shot"), dict) and e["shot"].get("input", "y") == "y" else []))),
]


def check_rules(entry, base=None):
    """[(rule, what breaks it)] for one ABILITIES-style entry."""
    out = []
    for r in RULES:
        try:
            bad = r["test"](entry, base)
        except Exception as ex:  # (a malformed entry: report it rather than crash)
            bad = [f"(couldn't test: {ex!r})"]
        if bad:
            out.append((r, bad if isinstance(bad, list) else []))
    return out


# ----------------------------------------------------------------------------------------------------------- building


def _sound_fields(base, known):
    return [base + suffix for suffix in ("", "_cd", "_s3k") if base + suffix in known or suffix == ""]


# The Creator Kit (tools/make_kit.py) has neither NoSwap's own characters (the examples, types and "used by" lists) nor
# the native code (per-game support): it reads the registry as built from the repo it was packed from
KIT_SNAPSHOT = REPO / "data" / "kit" / "abilities_registry.pickle"


@lru_cache(None)
def build():
    """The registry: {"format", "units", "games", "abilities": {id: entry}, "rules": [...]}."""
    import os
    if os.environ.get("NOSWAP_KIT") and KIT_SNAPSHOT.is_file():
        import pickle
        return pickle.loads(KIT_SNAPSHOT.read_bytes())
    from noswap_cli import abilities_info as ai
    text = _text()
    ab = _ab()
    users = _users()
    types = _field_types()
    known_fields = set(ai.fields()) | set(types)
    dflt, required = defaults()
    ids = sorted(set(ai.modules()) | set(text.ABILITIES))
    entries = {}
    for mid in ids:
        t = text.ABILITIES.get(mid, {})
        kind = t.get("kind", "move")
        fields = dict(t.get("fields", {}))
        sound_of = {}
        for base_name, what in (t.get("sounds") or {}).items():
            for f in _sound_fields(base_name, known_fields):
                sound_of[f] = (base_name, what)
        all_fields = list(fields) + [f for f in sound_of if f not in fields]
        # an example: the first character with it, his whole entry (it's what proves the move works)
        who = users.get(mid) or next((users[f] for f in fields if f in users), [])
        example_entry = ab.ABILITIES[who[0][0]] if who else None
        fdocs = {}
        for f in all_fields:
            if f in fields:
                spec = fields[f]
                unit, what = spec[0], spec[1]
                rng = spec[2] if len(spec) > 2 else None
            else:
                b, what0 = sound_of[f]
                suffix = f[len(b):]
                unit, what, rng = "sound", f"The sound of {what0}. " + text.SOUNDS[suffix], None
            ex = next((ab.ABILITIES[u[0]][f] for u in users.get(f, []) if f in ab.ABILITIES[u[0]]), None)
            fdocs[f] = {
                "unit": unit, "unit_text": UNITS.get(unit, unit), "what": what,
                **({"range": rng} if rng else {}),
                "type": sorted(types.get(f, [])) or None,
                "default": dflt.get(f) if f in dflt else None,
                "no_default": f in required and f not in dflt,
                "example": _jsonable(ex), "example_text": _plain(ex, unit),
                **({"per_frame": PER_FRAME[f][0], "per_frame_group": PER_FRAME[f][1]} if f in PER_FRAME else {}),
            }
        slots = {s: {"what": w, "required": True, "per_game": slot_numbers(s)} for s, w in (t.get("slots") or {}).items()}
        slots.update({s: {"what": w, "required": False, "per_game": slot_numbers(s)}
                      for s, w in (t.get("optional_slots") or {}).items()})
        example = None
        if example_entry:
            keep = set(all_fields) | ({"melee"} if mid in ("shot",) else set())
            example = {"abilities": [mid]} if kind != "setting" else {}
            example.update({k: _jsonable(v, hexify=fdocs.get(k, {}).get("unit") in ("speed", "accel"))
                            for k, v in example_entry.items() if k in keep})
        entries[mid] = {
            "id": mid, "name": t.get("name", mid), "kind": kind, "input": t.get("input", ""),
            "description": t.get("description", ""),
            "described": bool(t),
            "fields": fdocs,
            "slots": slots,
            "needs": list(t.get("needs", [])),
            "games": game_support(mid, kind, all_fields, example_entry),
            "used_by": [{"name": n, "base": b} for _, n, b in who],
            "example": example,
            "example_from": who[0][1] if who else None,
            "rules": [r["id"] for r in RULES if mid in r["moves"] or (mid in air_moves() and "(air moves)" in r["moves"])
                      or (mid in jump_button_moves() and "(jump-button moves)" in r["moves"])],
        }
    rules = [{k: v for k, v in r.items() if k != "test"} for r in RULES]
    return {"format": "noswap-abilities/1", "generated_by": "tools/abilities_registry.py (words: tools/abilities_text.py)",
            "units": UNITS, "games": GAME_NAMES, "air_moves": air_moves(),
            "jump_button_moves": list(jump_button_moves()), "abilities": entries, "rules": rules}


# keys inside a "shot" (and the like) that hold 16.16 speeds: written as hex in the examples
SPEED_KEYS = {"speed", "start_vy", "gravity", "bounce", "max_fall", "decel", "return_speed", "return_accel",
              "seek_speed", "seek_accel", "top_speed"}


def _jsonable(v, hexify=False):
    if isinstance(v, tuple):
        v = list(v)
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x, hexify=k in SPEED_KEYS and isinstance(x, int) and abs(x) >= 0x1000)
                for k, x in v.items()}
    if hexify and isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 0x100:
        return ("-" if v < 0 else "") + f"0x{abs(v):X}"
    return v


def _plain(v, unit):
    """An example value in plain words."""
    if v is None:
        return None
    if unit in ("speed", "accel") and isinstance(v, int) and not isinstance(v, bool):
        px = v / 0x10000
        return f"{'-' if v < 0 else ''}0x{abs(v):X} ({px:g} px a frame{' each frame' if unit == 'accel' else ''})"
    if unit == "frames" and isinstance(v, int):
        return f"{v} ({v / 60:.2g} s)" if v >= 30 else str(v)
    if isinstance(v, (dict, list, tuple)):
        s = json.dumps(_jsonable(v))
        return s if len(s) <= 80 else s[:77] + "..."
    return json.dumps(v)


def field_owners():
    """{field: [registry ids that read it]}."""
    out = {}
    for mid, e in build()["abilities"].items():
        for f in e["fields"]:
            out.setdefault(f, []).append(mid)
    return out


def lookup(name):
    reg = build()["abilities"]
    if name in reg:
        return reg[name]
    low = name.lower().replace("-", "_").replace(" ", "_")
    for e in reg.values():
        if low in (e["id"], e["name"].lower().replace(" ", "_")):
            return e
    return None


# ----------------------------------------------------------------------------------------------------------- output


def _support_mark(g):
    return {"yes": "yes", "partial": "partial", "no": "-"}[g["support"]]


def markdown():
    reg = build()
    A = reg["abilities"]
    order = [k for k in ("move", "passive", "setting")]
    out = ["# Ability catalogue",
           "",
           "Every move a NoSwap character can have, with its numbers, the animation slots it draws and the games it "
           "works in. Generated by `python3 tools/abilities_registry.py --write`; don't edit this file. The words are "
           "in `tools/abilities_text.py`; everything else (games, defaults, examples, rules) is read from the build "
           "code. `python3 tools/noswap.py abilities [name]` shows the same in a terminal, and `noswap check` uses it.",
           "",
           "How to use one: put its id in your `character.json`'s `\"abilities\"` list and set its fields next to the "
           "list. Draw the slots it needs in `ability_animations`. **Settings** don't go in the list: set their fields. "
           "Speeds are 16.16 fixed point (`\"0x10000\"` is 1 px a frame) and times are game frames (60 a second). "
           "In the field tables, **if left out** is the value the build uses when the field is missing (usually 0: "
           "off), and **set it** means the build has no fallback and reads the field directly.",
           "",
           "Game support: **yes** works there, **partial** works with the limits noted, **-** not there yet (the move is "
           "skipped in that game; adding it is core work, not character work).",
           "",
           "| id | name | kind | input | " + " | ".join(GAME_SHORT[g] for g in GAMES) + " |",
           "|---|---|---|---|" + "---|" * len(GAMES)]
    for kind in order:
        for mid, e in sorted(A.items(), key=lambda kv: kv[1]["name"]):
            if e["kind"] == kind:
                out.append(f"| [`{mid}`](#{mid.replace('_', '-')}) | {e['name']} | {kind} | {e['input']} | "
                           + " | ".join(_support_mark(e["games"][g]) for g in GAMES) + " |")
    out += ["", "## Combining moves", "",
            "Some moves can't go together. **error**: the build stops (the Origins build makes all four games at once, "
            "so a rule checked in one game stops them all). **warning**: it builds, but one of them won't work as "
            "meant. The games column says where the code checks it.", "",
            "| rule | games | level | what |", "|---|---|---|---|"]
    for r in reg["rules"]:
        out.append(f"| `{r['id']}` | {', '.join(GAME_SHORT[g] for g in r['games'])} | {r['level']} | {r['text']} |")
    out += ["", f"The mid-air moves of `one-air-move` (one per character, unless `ability_cycle`): "
                f"{', '.join('`' + m + '`' for m in reg['air_moves'])}.", ""]
    if reg.get("jump_button_moves"):
        out += ["**Tails or Knuckles as the base:** the jump button keeps Tails' flight or Knuckles' glide and climb "
                "(`base-keeps-jump`), so the moves started by pressing jump again in mid-air need base `sonic`: "
                f"{', '.join('`' + m + '`' for m in reg['jump_button_moves'])} (`aim_dash` with `aim_dash_y` and "
                "`screw_kick` without `kick_jump` start with Y, so they're fine). Everything else works with any base.", ""]
    titles = {"move": "Moves", "passive": "Passives", "setting": "Settings"}
    for kind in order:
        out += [f"## {titles[kind]}", ""]
        for mid, e in sorted(A.items(), key=lambda kv: kv[1]["name"]):
            if e["kind"] != kind:
                continue
            out += [f"### {e['name']}", "", f"<a id=\"{mid.replace('_', '-')}\"></a>`{mid}` · {e['input']}", "",
                    e["description"] or "*(no description yet: add one in tools/abilities_text.py)*", ""]
            games = "; ".join(f"{GAME_NAMES[g]}: {e['games'][g]['support']}"
                              + (f" ({e['games'][g]['note']})" if e["games"][g].get("note") else "") for g in GAMES)
            out += [f"**Games:** {games}.", ""]
            if e["used_by"]:
                out += [f"**Used by:** {', '.join(u['name'].title() for u in e['used_by'])}.", ""]
            if e["needs"]:
                out += [f"**Needs:** {'; '.join(e['needs'])}.", ""]
            if e["fields"]:
                out += ["| field | unit | what it does | if left out | example |", "|---|---|---|---|---|"]
                for f, d in e["fields"].items():
                    dv = "set it" if d["no_default"] else ("-" if d["default"] is None else
                                                           f"`{json.dumps(_jsonable(d['default']))}`")
                    what = d["what"] + (f" ({d['range']})" if d.get("range") else "")
                    out.append(f"| `{f}` | {d['unit']} | {what} | {dv} | {d['example_text'] or ''} |")
                out.append("")
            if e["slots"]:
                out += ["| slot | draw | " + " | ".join(GAME_SHORT[g] for g in ("cd", "s3k")) + " |", "|---|---|---|---|"]
                for s, d in e["slots"].items():
                    pg = d["per_game"]
                    out.append(f"| {s}{'' if d['required'] else ' (optional)'} | {d['what']} | "
                               f"{pg['cd'] or 'not drawn'} | {pg['s3k'] or 'not drawn'} |")
                out.append("")
            if e["rules"]:
                out += [f"**Rules:** {', '.join('`' + r + '`' for r in e['rules'])}.", ""]
            if e["example"]:
                out += [f"Example (from {e['example_from'].title()}):", "", "```json",
                        json.dumps(e["example"], indent=1), "```", ""]
    out += ["## Units", ""] + [f"- **{k}**: {v}" for k, v in UNITS.items()] + [""]
    return "\n".join(out)


def as_json():
    return json.dumps(build(), indent=1, default=str) + "\n"


def coverage():
    """Problems with the registry itself: moves or fields nobody described."""
    from noswap_cli import abilities_info as ai
    reg = build()["abilities"]
    problems = [f"move {m}: no words in tools/abilities_text.py" for m, e in reg.items() if not e["described"]]
    owned = set(field_owners())
    for f in sorted(_field_types()):
        if f != "abilities" and not f.startswith("_") and f not in owned and f not in reg:
            problems.append(f"field {f}: an existing character sets it, but no registry entry lists it")
    return problems


def main(argv):
    if "--write" in argv:
        JSON_OUT.write_text(as_json())
        MD_OUT.write_text(markdown())
        print("wrote", JSON_OUT, "and", MD_OUT)
    if "--check" in argv or not argv:
        problems = coverage()
        for p in problems:
            print("registry:", p)
        stale = [p.name for p, s in ((JSON_OUT, as_json()), (MD_OUT, markdown())) if not p.exists() or p.read_text() != s]
        for s in stale:
            print(f"registry: docs/{s} is out of date: run tools/abilities_registry.py --write")
        reg = build()["abilities"]
        print(f"{len(reg)} entries ({sum(e['kind'] != 'setting' for e in reg.values())} moves and passives), "
              f"{len(RULES)} rules, {len(problems)} problem(s)")
        return 1 if problems or stale else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
