"""`noswap check <folder>`: everything that can be checked about a character without building it.

Each finding is an error (the build would fail, or the game would be wrong), a warning (it builds, but probably isn't
what you want) or a note. Every message says where and, where it can, what to do about it.
"""
import difflib
import json
import re

from PIL import Image

from . import abilities_cmd
from . import abilities_info as ai
from .model import ENDING_KEYS, REPO, UI_KEYS, CharacterError, frame_label, frame_rects, load
from .schema import validate
from .templates import TEMPLATES

OWN_FIRST, OWN_LAST = 74, 95  # the extras' own global palette slots (S1/S2/CD; S3&K's DLL writes 64-95)
MANIA_OWN_SLOTS = 13  # build_mania_art.OWN_SLOTS: Sonic's 64-69 and the global palette's unused 86-90, 111, 127
CREDIT_SOFT, CREDIT_HARD = 32, 40  # origins_cards.CREDIT_UNITS is 40; keep it about 32 to fit the card
UI_SIZES = {"life_icon": (16, 16), "monitor_1up": (16, 14), "sign_face": (48, 32)}
SHEET = 256  # sheet2ani.SHEET_SIZE; frames pack with 1 px of padding
NO_EDIT = re.compile(r"do\s*n[o']?t\s+edit|no\s+edit|don.t\s+(?:edit|modify)|not\s+(?:be\s+)?(?:edited|modified)", re.I)


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, where, msg, fix=None):
        self.items.append((level, where, msg, fix))

    def error(self, where, msg, fix=None):
        self.add("error", where, msg, fix)

    def warn(self, where, msg, fix=None):
        self.add("warning", where, msg, fix)

    def note(self, where, msg, fix=None):
        self.add("note", where, msg, fix)

    def count(self, level):
        return sum(1 for i in self.items if i[0] == level)

    def print(self, out, verbose=False):
        for level in ("error", "warning", "note"):
            items = [i for i in self.items if i[0] == level]
            if not items or (level == "note" and not verbose):
                continue
            for _, where, msg, fix in items:
                print(f"  {level.upper():7} {where}: {msg}", file=out)
                if fix:
                    print(f"          fix: {fix}", file=out)


def _near(name, options):
    m = difflib.get_close_matches(name, list(options), n=3, cutoff=0.6)
    return f" (did you mean {' / '.join(repr(x) for x in m)}?)" if m else ""


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb[:3])


# ---------------------------------------------------------------- the checks

def check_schema(ch, r):
    for path, msg in validate(ch.raw):
        fix = None
        if path.startswith("palette.own."):
            fix = f"own colours go in slots {OWN_FIRST}-{OWN_LAST} (written \"74\": \"#rrggbb\")"
        r.error(f"character.json {path}", msg, fix)
    c = ch.cleaned
    if c.get("id") != ch.folder.name:
        r.error("character.json id", f"is {c.get('id')!r} but the folder is {ch.folder.name!r}",
                "rename one so they match (the id is the character's permanent key, noswap.<id>)")
    off = [g for g in ("sonic1", "sonic2", "soniccd", "s3k") if not c.get("games", {}).get(g, True)]
    if off:
        r.error("character.json games", f"leaving out an Origins game isn't supported yet ({', '.join(off)})",
                "set them to true: the Origins build always makes all four games")
    flags = c.get("flags", {})
    if flags.get("roll") and flags.get("no_roll"):
        r.error("character.json flags", "\"roll\" and \"no_roll\" can't both be true")


def check_frames(ch, r, sheet):
    """Every frame inside the sheet, not empty, small enough to pack; names defined; unused ones listed."""
    import sheet2ani
    W, H = sheet.size
    if ch.kind == "json":
        for where, name in ch.refs:
            if name not in ch.frames:
                r.error(where, f"frame {name!r} isn't defined in \"frames\"{_near(name, ch.frames)}",
                        "add it to \"frames\" as [x, y, w, h], or fix the name")
        for name, rect in ch.frames.items():
            x, y, w, h = rect
            if x + w > W or y + h > H:
                r.error(f"frames {name}", f"{rect} reaches past the sheet's edge ({W}x{H})",
                        "measure it again in your image editor (x, y of the top-left corner, then width, height)")
            elif w == 0 or h == 0:
                r.error(f"frames {name}", f"{rect} is empty (zero width or height)")
        used = {n for _, n in ch.refs}
        unused = [n for n in ch.frames if n not in used]
        if unused:
            r.note("frames", f"{len(unused)} defined but not used: {', '.join(unused[:12])}{' ...' if len(unused) > 12 else ''}")
    background = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in ch.background}
    src = sheet.convert("RGBA")
    names = ch.frame_names
    seen, sizes = {}, []
    anchors = ch.anchors()
    for where, spec in ch.used_specs():
        key = json.dumps(spec, sort_keys=True)
        if key in seen:
            continue
        seen[key] = True
        bad = [rect for rect in frame_rects(spec) if rect[0] + rect[2] > W or rect[1] + rect[3] > H]
        if bad:
            if ch.kind == "legacy":
                r.error(where, f"frame {bad[0]} reaches past the sheet's edge ({W}x{H})")
            continue
        try:
            if isinstance(spec, dict) and "layers" in spec:
                img, _, _ = sheet2ani.cut_layered(src, spec, background)
            elif isinstance(spec, dict):
                img, _, _ = sheet2ani.cut_spec(src, spec, background)
            else:
                img, _ = sheet2ani.cut_frame(src, tuple(spec), background)
        except SystemExit:
            r.error(where, f"frame {frame_label(spec, names)} is empty: only background colours inside it",
                    "check its rect, and that \"sheet.background\" doesn't list a colour the sprite uses")
            continue
        except Exception as e:  # (a malformed frame dict)
            r.error(where, f"frame {frame_label(spec, names)} can't be cut: {e}")
            continue
        w, h = img.size
        if w + 2 > SHEET or h + 2 > SHEET:
            r.error(where, f"frame {frame_label(spec, names)} is {w}x{h}: too big for a 256x256 sprite sheet "
                           "(254x254 at most)")
        elif _plain(spec) and (w // 2 > 128 or any((h - ch.feet_y if a == "feet" else h // 2) > 128
                                                   for a in anchors.get(key, ()))):
            r.error(where, f"frame {frame_label(spec, names)} is {w}x{h}: its pivot doesn't fit the .ani's -128..127",
                    "use a smaller frame, or anchor it \"center\"")
        sizes.append((w, h))
        if isinstance(spec, dict) and spec.get("anchor") is not None and spec["anchor"] not in ("feet", "center"):
            r.error(where, f"anchor {spec['anchor']!r} must be \"feet\" or \"center\"")
    if sizes:
        sheets = _pack_count(sizes)
        r.note("sprites", f"{len(sizes)} distinct frames on {sheets} 256x256 sheet(s) per game")
        if sheets > 4:
            r.warn("sprites", f"{sheets} sprite sheets: big characters cost video memory (Vector, the biggest so far, uses 3)")
    return seen


def _plain(spec):
    """A frame placed by its own box (not by an anchor_box or a layer: those pivots can't be judged from the size)."""
    return not (isinstance(spec, dict) and {"anchor_box", "layers"} & set(spec))


def _pack_count(sizes):
    """sheet2ani.pack's sheet count for these frame sizes."""
    x, y, shelf, sheet = 1, 1, 0, 0
    for w, h in sorted(sizes, key=lambda s: -s[1]):
        if x + w + 1 > SHEET:
            x, y, shelf = 1, y + shelf + 1, 0
        if y + h + 1 > SHEET:
            sheet, x, y, shelf = sheet + 1, 1, 1, 0
        x += w + 1
        shelf = max(shelf, h)
    return sheet + 1


def ball_use_for(ch):
    """The generic ball's use_for (character.json "ball"), or None."""
    b = ch.cleaned.get("ball") if ch.kind == "json" else None
    if not isinstance(b, dict):
        return None
    import generic_ball
    u = b.get("use_for", list(generic_ball.DEFAULT_USE_FOR))
    return u if isinstance(u, list) else []


def plan_ball(ch):
    """The S1/S2 animations the generic ball fills (it isn't missing there)."""
    return {n for n in ("Jumping", "Spin Dash") if n in (ball_use_for(ch) or ())}


def fallback_plan(ch):
    """tools/anim_fallbacks.plan for a character.json character (what character_json.config fills in)."""
    import anim_fallbacks as af
    base = ch.base if ch.base in ("sonic", "tails", "knuckles") else "sonic"
    return af.plan(ch.cleaned, {g: TEMPLATES[(g, base)]["filled"] for g in ("Sonic1", "Sonic2")})


def check_no_stomp(ch, r):
    """abilities "no_stomp": the jump isn't an attack, so it shouldn't look like the ball; and he needs a slide."""
    if "no_stomp" not in ((ch.abilities or {}).get("abilities") or []):
        return
    b = ch.cleaned.get("ball") if ch.kind == "json" and isinstance(ch.cleaned.get("ball"), dict) else {}
    use = b.get("use_for", []) if b else []
    flags = ch.flags or {}
    if "Jumping" in use:
        r.warn("no_stomp", "his jump is the spin ball, but with no_stomp it isn't an attack: it looks like one",
               "give \"Jumping\" his own jump pose and take Jumping out of ball use_for")
    if "Rolling" in use:
        r.warn("no_stomp", "slot 49 (his roll) is the spin ball: with no_stomp the roll is his slide",
               "draw his slide pose in ability_animations 49 (\"Rolling\") and take Rolling out of ball use_for")
    slide = "ground_slide" in (ch.abilities.get("abilities") or [])
    roll = flags.get("roll") and "49" in ch.ability_anims and "Rolling" not in use
    if not slide and not roll:
        r.warn("no_stomp", "he has no slide: no ground_slide, and no slide pose for rolling (slot 49 \"Rolling\" with "
               "flags roll)", "add one: with no_stomp his slide is his attack on the ground")
    elif flags.get("no_roll") and not slide:
        r.warn("no_stomp", "flags no_roll: he never rolls, so his only slide would be ground_slide", "add ground_slide")


def check_ball(ch, r):
    """character.json "ball": the generic spin ball (tools/generic_ball.py)."""
    b = ch.cleaned.get("ball") if ch.kind == "json" else None
    if b is None:
        return
    import generic_ball
    if not isinstance(b, dict):
        r.error("ball", "must be an object: {\"size\", \"colours\", \"use_for\"}")
        return
    # (the size, use_for's names and the colours' form are the schema's: check_schema reports them)
    use = b.get("use_for", list(generic_ball.DEFAULT_USE_FOR))
    use = [u for u in use if u in generic_ball.USE_FOR] if isinstance(use, list) else []
    flags = ch.flags or {}
    if flags.get("no_roll") and {"Spin Dash", "Rolling"} & set(use):
        r.warn("ball use_for", "he never rolls or Spin Dashes (flags no_roll): a Spin Dash / Rolling ball is never seen")
    if "Jumping" in use:
        r.note("ball use_for", "Jumping is the ball: his jump (his attack) looks like a spin ball, not his own jump pose")
    if "Rolling" in use:
        r.note("ball use_for", "Rolling is the ball: ability slot 49 (\"roll\" on: rolling shows it, and the S2 / CD / "
               "S3&K special stages use it)" + (", in place of his own slot 49 frames" if "49" in ch.ability_anims else ""))
    elif "Special Stage" in use and "Jumping" not in use:
        r.note("ball use_for", "Special Stage is only Sonic 1's: Sonic 2, CD and S3&K's special stages show his "
               f"{'Rolling' if flags.get('roll') and 'no_stomp' not in (ch.abilities or {}).get('abilities', []) else 'Jumping'} frames", "add Jumping or Rolling to use_for for a ball there too")
    for k in [k for k in use if k in ("Jumping", "Spin Dash")]:
        own = [g for g in ("Sonic1", "Sonic2") if ch.anims.get(g, {}).get(k, {}).get("frames")]
        if own:
            r.note(f"ball {k}", "his own frames there are replaced by the ball")
    cols = b.get("colours", "auto")
    if cols == "auto":
        try:
            import character_json
            c = dict(ch.cleaned, folder=ch.folder)
            got = character_json.ball_colours(c, Image.open(ch.sheet).convert("RGB"))
            r.note("ball colours", "auto: " + ", ".join(f"{k} {v}" for k, v in got.items()))
        except Exception as e:
            r.error("ball colours", f"auto couldn't pick colours: {e}", "give the five colours yourself")
    elif isinstance(cols, dict):
        have = set(ch.colours)
        for k, v in cols.items():
            if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) and v.lower() not in have:
                r.warn(f"ball colours {k}", f"{v} isn't one of his palette's colours: it's drawn as the nearest one",
                       "pick it from his palette (the editor's Ball panel does)")
    import generic_ball as gb
    if not gb.SOURCE.exists():
        r.error("ball", f"the ball's frames ({gb.SOURCE.relative_to(REPO)}) aren't there")


def check_animations(ch, r):
    base = ch.base if ch.base in ("sonic", "tails", "knuckles") else "sonic"
    s1, s2 = TEMPLATES[("Sonic1", base)], TEMPLATES[("Sonic2", base)]
    if ch.kind == "json":
        c = ch.cleaned
        if base == "knuckles" or (c.get("sheet") or {}).get("angled_halves"):
            # Knuckles' layout (build_s3k_art knuckles_layout): the walk and run are upright frames, then the same turned
            # 45 degrees (S3&K's "Angled" animations take the second half)
            for name in ("Walking", "Running"):
                a = (c.get("animations") or {}).get(name)
                n = len(a.get("frames") or []) if isinstance(a, dict) else 0
                if n % 2:
                    r.warn(f"animations {name}", f"{n} frame(s): {'Knuckles as the base' if base == 'knuckles' else 'angled_halves'}"
                           " reads the list as upright frames, then the same frames turned 45 degrees (for slopes), so it "
                           "needs an even number" + (" (a single frame stands for both)" if n == 1 else ""),
                           "list the upright frames, then the angled ones (or the upright ones again: he won't lean "
                           "on slopes)")
        import cd_config  # (Sonic CD's own names, read from the Sonic 2 section: 3D Ramp 1-7, Spinning Top, ...)
        cd_names = set(cd_config.STAND_INS) | set(cd_config.RENAMED.values())
        for name in (k for k in c.get("animations", {}) if not k.startswith("_")):
            if name in cd_names and name not in s1["all"] + s2["all"]:
                r.note(f"animations {name}", "is a Sonic CD name: only Sonic CD uses it",
                       "move it to \"animations_sonic2\" (CD is built from that section)")
            elif name not in s1["all"] and name not in s2["all"]:
                r.error(f"animations {name}", f"isn't on {base}'s animation list, so it would be silently ignored"
                        f"{_near(name, set(s1['all']) | set(s2['all']))}")
            elif name not in s1["all"]:
                r.note(f"animations {name}", "is only on Sonic 2's list (Sonic 2, CD and S3&K use it; Sonic 1 doesn't)",
                       "move it to \"animations_sonic2\" to say so")
        for name in (k for k in c.get("animations_sonic2", {}) if not k.startswith("_")):
            if name in cd_names and name not in s2["all"]:
                continue
            if name not in s2["all"]:
                r.error(f"animations_sonic2 {name}", f"isn't on {base}'s Sonic 2 list, so it would be silently ignored"
                        f"{_near(name, s2['all'])}")
    for game, tpl in (("Sonic1", s1), ("Sonic2", s2)):
        anims = ch.anims.get(game, {})
        missing = [n for n in tpl["filled"] if not anims.get(n, {}).get("frames")]
        if missing and ch.kind == "json":  # (fallback frames: tools/anim_fallbacks.py, character.json only)
            plan = fallback_plan(ch)[game]
            used, lost, empty = plan["used"], plan["lost"], set(plan["empty"])
            missing = [n for n in missing if n not in plan_ball(ch)]
            if used:
                r.note(f"{game} animations", "no frames of their own, so they use a fallback: "
                       + ", ".join(f"{n} uses {s}" for n, s in used.items()),
                       "fine as is; give one its own frames (or null for deliberately empty) to change it")
            if empty:
                r.note(f"{game} animations", f"deliberately empty (null): {', '.join(sorted(empty & set(missing)))}: "
                       "the game shows nothing there")
            missing = lost
        if missing:
            r.warn(f"{game} animations", f"no frames for {', '.join(missing)}: the game shows nothing there",
                   "give each one frames (reusing a close pose is fine: Bean's Hanging uses his pipe frames)")
        for name, a in anims.items():
            loop = a.get("loop")
            if isinstance(loop, int) and a.get("frames") and loop >= len(a["frames"]):
                r.error(f"{game} {name}", f"loop {loop} is past its last frame ({len(a['frames'])} frames; loop counts from 0)")
    for slot, a in ch.ability_anims.items():
        if not str(slot).isdigit():
            continue
        if int(slot) < 39:
            r.error(f"ability_animations {slot}", "slots below 39 are the base character's own animations",
                    "ability animations start at 41 (see docs/character-json.md)")
        elif slot not in ai.SLOT_MEANING and int(slot) < 53:
            r.note(f"ability_animations {slot}", "isn't a slot any move uses (41-52)")
        if not a.get("name"):
            r.error(f"ability_animations {slot}", "needs a \"name\"")
    ball = ch.kind == "json" and "Special Stage" in (ball_use_for(ch) or ())
    if not ch.special_stage and not ball:
        src = fallback_plan(ch)["special"]["used"].get("Special Stage") if ch.kind == "json" else None
        if src:
            r.note("special_stage", f"no Sonic 1 special stage animation: his {src} frames are used there (centred)",
                   "add {\"Special Stage\": {\"frames\": [...his ball frames...], \"anchor\": \"center\"}}")
        else:
            r.warn("special_stage", "no Sonic 1 special stage animation" + (", and nothing to fall back on"
                   if ch.kind == "json" else ": his Jumping frames are used there (centred)"),
                   "add {\"Special Stage\": {\"frames\": [...his ball frames...], \"anchor\": \"center\"}}")
    if not ch.s3k_victory:
        r.note("s3k_victory", "no S3&K act clear pose: the standing frame is used")


def check_sign_face(ch, r, sheet):
    """ui sign_face (character_json.sign_face_plan): a whole sign as drawn, or a head on the game's own board. Returns
    the plan's mode ("head" / "own"), or None when there's nothing (or it's an error)."""
    if ch.kind != "json":
        return None
    from character_json import sign_face_plan
    e = (ch.cleaned.get("ui") or {}).get("sign_face")
    if isinstance(e, dict) and (isinstance(e.get("head"), str) and e["head"] not in ch.frames or "head" in e and
                                e.get("scale", "auto") != "auto" and not isinstance(e.get("scale"), (int, float))):
        return None  # (the frame-name and schema checks report these)
    try:
        plan = sign_face_plan({**ch.cleaned, "folder": ch.folder}, sheet.convert("RGBA"))
    except (SystemExit, KeyError, ValueError, TypeError) as err:
        msg = str(err)
        for lead in (f"{ch.folder / 'character.json'}: ", "ui sign_face head: ", "ui sign_face: "):
            msg = msg[len(lead):] if msg.startswith(lead) else msg
        r.error("ui sign_face", msg, "{\"head\": FRAME} for a head on the official sign, or {\"frame\": FRAME} for a "
                "whole 48x32 sign you drew")
        return None
    if plan and plan["mode"] == "own" and isinstance(e, dict) and e.get("own") and ("frame" in e or "rect" in e):
        import sign_face
        r_ = ch.frames.get(e["frame"]) if "frame" in e else e["rect"]
        box = r_ and sign_face.drawn_box(sheet.convert("RGBA"), r_, {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
                                                                      for c in ch.background})
        if box and not sign_face.is_whole_sign(box[2], box[3]):
            r.warn("ui sign_face", f"\"own\": the {box[2]}x{box[3]} drawing is used as it is, but the signpost shows a "
                   "48x32 board there: it will float with no board round it",
                   "draw the whole sign, or drop \"own\" (or write {\"head\": ...}) to put it on the official board")
    if not plan or plan["mode"] != "head":
        return plan and plan["mode"]
    w, h = plan["head"][2:]
    how = f"enlarged {plan['scale']}x nearest-neighbour" + (" (auto)" if plan["auto"] else "") \
        if plan["scale"] != 1 else "at 1x" + (" (auto)" if plan["auto"] else "")
    if plan["why"] == "detected":
        ref = e.get("frame", e.get("rect")) if isinstance(e, dict) else None
        r.note("ui sign_face", f"{ref!r} is {w}x{h}, a head, not a whole 48x32 sign: it goes on the game's own signpost "
               f"board, {how}", f"to say so: {{\"head\": {json.dumps(ref)}}}; to use it as drawn: add \"own\": true")
    elif plan["why"] == "default":
        r.note("ui sign_face", f"none given: the top of the Stopped frame ({w}x{h}) on the game's own signpost board, {how}",
               "pick his head: \"sign_face\": {\"head\": FRAME}")
    else:
        r.note("ui sign_face", f"a {w}x{h} head on the game's own signpost board, {how}")
    if round(w * plan["scale"]) > 40 or round(h * plan["scale"]) > 24:
        r.note("ui sign_face", f"the head is {round(w * plan['scale'])}x{round(h * plan['scale'])} enlarged: the board's "
               "face area is 40x24, so its top" + (" and sides are" if round(w * plan["scale"]) > 40 else " is")
               + " trimmed (the chin stays)")
    if isinstance(e, dict) and "remap" in e and "head" in e:
        r.warn("ui sign_face", "\"remap\" is ignored for a head on the official sign (the board keeps its own colours)")
    return "head"


def check_ui(ch, r, sheet):
    W, H = sheet.size
    sign = check_sign_face(ch, r, sheet)
    for keys, section in ((UI_KEYS, "ui"), (ENDING_KEYS, "ending")):
        have = ch.ui if section == "ui" else ch.ending
        missing = [k for k in keys if k not in have and not (k == "sign_face" and sign == "head")]
        hard = [k for k in missing if not k.startswith("good_")]
        if hard:
            r.error(section, f"missing {', '.join(hard)}",
                    "every character needs its HUD art (ui) and Sonic 1 ending poses (ending): see docs/character-json.md")
        if len(hard) < len(missing):
            r.warn(section, f"no good-ending frames ({', '.join(k for k in missing if k.startswith('good_'))})",
                   "Sonic 1's good ending shows six frames of him: add good_1 ... good_6")
        for k, e in have.items():
            if "text" in e:  # a typed name tag (tools/hud_font.py)
                import hud_font
                for msg in hud_font.problems(e["text"]):
                    r.error(f"{section} {k}", msg + (" (the tag defaults to his \"name\")" if e.get("default") else ""),
                            "set ui.life_name.text to a shorter tag in capitals (the HUD & ending tab shows it), or "
                            "use your own graphic: {\"frame\": NAME}")
            if "rect" not in e:
                continue
            x, y, w, h = e["rect"]
            if x + w > W or y + h > H:
                r.error(f"{section} {k}", f"{e['rect']} reaches past the sheet's edge ({W}x{H})")
                continue
            if k in UI_SIZES and e.get("trim") is False and "base" not in e and "scale" not in e and \
                    (w > UI_SIZES[k][0] or h > UI_SIZES[k][1] or (k != "sign_face" and (w, h) != UI_SIZES[k])):
                r.warn(f"{section} {k}", f"is {w}x{h}; the game's own is {UI_SIZES[k][0]}x{UI_SIZES[k][1]}",
                       "crop it to that size (it's drawn where Sonic's would be)")
            if k == "end_pose_2" and w > 71:
                r.warn(f"{section} {k}", f"is {w} px wide; the ending sheet's medium pose box is 71",
                       "crop its edges to 71 px (as Bean's END_MEDIUM)")


def check_act_name(ch, r):
    """The S1/S2 act results spell his "name" in the games' own title-card letters (build_sonic1.ALPHABET,
    build_sonic2.S2_ALPHABET: A-Z and space), right-aligned in a 192-px room (noswap_common.UI_RESERVE act_name)."""
    try:
        from build_sonic1 import ALPHABET as S1
        from build_sonic2 import S2_ALPHABET as S2
        from noswap_common import UI_RESERVE
    except Exception:  # (no game data: can't measure)
        return
    name = ch.name if isinstance(ch.name, str) else ""
    bad = sorted({c for c in name if c != " " and c not in S1})
    if bad:
        r.error("name", f"the Sonic 1 / 2 act results spell {name!r} in the title-card letters, which have only A-Z and "
                f"space: {' '.join(repr(c) for c in bad)} can't be drawn", "use capitals and spaces only")
        return
    room = UI_RESERVE["act_name"][2] - UI_RESERVE["act_name"][0]
    for game, alphabet in (("Sonic 1", S1), ("Sonic 2", S2)):
        w = sum(9 if c == " " else alphabet[c][2] + 1 for c in name) - 1
        if w > room:
            r.error("name", f"{name!r} is {w} px wide in {game}'s act results letters; the room is {room}",
                    "a shorter name (about 12 letters)")
            return


def check_palette(ch, r, sheet):
    own = ch.own
    if ch.kind == "json" and not own and not ch.colours:
        r.warn("palette", "no colours listed: every sheet colour goes to the nearest of the base's 15")
    bad = [s for s in own if not OWN_FIRST <= s <= OWN_LAST]
    if bad:
        r.error("palette.own", f"slots {bad} are outside {OWN_FIRST}-{OWN_LAST}, the extras' free slots")
    dup = {col for col in own.values() if list(own.values()).count(col) > 1}
    if dup:
        r.warn("palette.own", f"the same colour in more than one slot: {sorted(dup)}")
    bg = {c.lower() for c in ch.background}
    clash = bg & set(own.values())
    if clash:
        r.error("palette", f"{sorted(clash)} is both a background colour and one of his own colours",
                "a background colour is never drawn: take it out of one list")
    for col, slot in ch.colours.items():
        if col not in own.values() and not (1 <= slot <= 15 or OWN_FIRST <= slot <= OWN_LAST):
            r.warn("palette.shared", f"{col} -> slot {slot}: shared colours go in the base's own slots 1-15")
    # Colours the frames use, and what the game draws them as
    src = sheet.convert("RGBA")
    background = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in bg}
    used = {}  # rgb -> [where]
    pixels = {}  # rgb -> pixel count (each rect once)
    rects = {}
    for where, spec in ch.used_specs():
        for rect in frame_rects(spec):
            rects.setdefault(tuple(rect), where)
    for k, e in {**ch.ui, **ch.ending}.items():
        if "rect" in e:
            rects.setdefault(tuple(e["rect"]), k)
    for (x, y, w, h), where in rects.items():
        for n, (R, G, B, A) in src.crop((x, y, x + w, y + h)).getcolors(1 << 20) or []:
            if A and (R, G, B) not in background:
                used.setdefault((R, G, B), []).append(where)
                pixels[(R, G, B)] = pixels.get((R, G, B), 0) + n
    keyed = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)): s for c, s in ch.colours.items()}
    _check_box_colours(ch, r, src, bg, rects, used)
    unlisted = [c for c in used if c not in keyed]
    if ch.strict and unlisted:
        r.error("palette.strict", f"{len(unlisted)} frame colour(s) have no slot of their own: "
                + ", ".join(_hex(c) for c in unlisted[:8]), "add them to palette.own (or turn strict off)")
    no_edit = bool(NO_EDIT.search(json.dumps(ch.credits)))
    pal = _game_palette(ch)
    if pal and unlisted:
        drawn = {}
        for c in unlisted:
            if ch.other_colours == "nearest" and keyed:
                near = min(keyed, key=lambda k: sum((a - b) ** 2 for a, b in zip(k, c)))
                drawn[c] = pal[keyed[near]]
            else:  # sheet2ani's own guess: the nearest of slots 1-15 and the listed ones
                cands = set(range(1, 16)) | set(keyed.values())
                drawn[c] = pal[min(cands, key=lambda i: sum((a - b) ** 2 for a, b in zip(c, pal[i])))]
        changed = {c: d for c, d in drawn.items() if max(abs(a - b) for a, b in zip(c, d)) > 4}
        _check_collapse(r, used, pixels, drawn, changed, keyed, pal)
        if changed:
            sample = ", ".join(f"{_hex(c)}->{_hex(d)} ({used[c][0]})" for c, d in list(changed.items())[:5])
            msg = f"{len(changed)} frame colour(s) drawn as a different colour: {sample}{' ...' if len(changed) > 5 else ''}"
            fix = f"give them slots of their own in palette.own ({OWN_FIRST}-{OWN_LAST})"
            if no_edit:
                r.warn("palette", msg + ". The sheet's terms forbid edits, and merging colours is a recolour", fix)
            else:
                r.note("palette", msg + " (the faithful art rule allows no recolours: check it's only labels or cameos)", fix)
    n_own = len(own)
    r.note("palette", f"Origins S1/S2/CD: {n_own} own colour(s) of {OWN_LAST - OWN_FIRST + 1} slots; "
                      f"S3&K: the same slots (the DLL writes them); {len(used)} colours on the used frames")
    if n_own > OWN_LAST - OWN_FIRST + 1:
        r.error("palette.own", f"{n_own} own colours: only {OWN_LAST - OWN_FIRST + 1} slots ({OWN_FIRST}-{OWN_LAST})")
    if ch.games.get("mania"):
        need = _mania_need(own)
        if len(need) > MANIA_OWN_SLOTS:
            r.note("Mania palette", f"{len(need)} own colours not in Mania's global palette, {MANIA_OWN_SLOTS} slots: the "
                   f"{len(need) - MANIA_OWN_SLOTS} rarest go to the nearest global colour",
                   "fewer own colours, or accept the approved Mania colour exception (it's reported at build time)")
        else:
            r.note("Mania palette", f"{len(need)} of {MANIA_OWN_SLOTS} own slots")


def _check_box_colours(ch, r, src, bg, rects, used):
    """A cell-box colour (one filling large rectangles behind his frames: detect.find_fills) that isn't background is
    drawn in game as a box behind every frame it's in."""
    from .detect import box_colours
    try:
        boxes = box_colours(src, sorted(bg), [list(rc) for rc in rects])
    except Exception:  # (a check never fails on its own helper)
        return
    listed = {c.lower() for c in ch.colours} | {c.lower() for c in ch.own.values()}
    for col, n in sorted(boxes.items()):
        rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
        if col in listed:
            r.warn("palette", f"{col} fills {n} cell box(es) behind his frames, and it's in his palette: the game would "
                   "draw a box behind each of those frames",
                   f"add {col} to \"sheet.background\" and take it out of the palette (Fill from sheet does both)")
        elif rgb in used:
            r.warn("sheet.background", f"{col} fills {n} cell box(es) behind his frames: the game would draw a box (in the "
                   "nearest listed colour) behind each of those frames",
                   f"add {col} to \"sheet.background\"")


def _check_collapse(r, used, pixels, drawn, changed, keyed, pal):
    """The game colours collapse: most of his pixels, or many distinct colours, land in a few slots (an empty
    palette.own with "nearest" draws everything in the one listed colour: a black silhouette)."""
    if len(used) < 4:
        return
    total = sum(pixels.values()) or 1
    slot_of = {c: keyed[c] for c in used if c in keyed}
    for c, d in drawn.items():
        slot_of[c] = next((s for s in sorted(set(keyed.values()) | set(range(1, 16))) if pal[s] == d), d)
    slots = set(slot_of.values())
    moved = sum(pixels.get(c, 0) for c in changed) / total
    top_slot = max(slots, key=lambda s: sum(pixels.get(c, 0) for c, t in slot_of.items() if t == s))
    top = sum(pixels.get(c, 0) for c, t in slot_of.items() if t == top_slot) / total
    fix = ("Palette tab > Fill from sheet (gives each frame colour an own slot, 74-95, or the base's slot when it's "
           "the same colour), or list his colours in palette.own yourself")
    if len(slots) <= 2 or (moved > 0.5 and len(slots) * 3 <= len(used)):
        what = f"slot {top_slot} ({_hex(pal[top_slot])})" if isinstance(top_slot, int) else _hex(top_slot)
        r.error("palette", f"the game colours collapse: his {len(used)} frame colours are drawn with only {len(slots)} "
                f"colour(s); {round(100 * moved)}% of his pixels change colour and {round(100 * top)}% are drawn as "
                f"{what}. In game he'd be a flat silhouette", fix)
    elif moved > 0.25:
        r.warn("palette", f"{round(100 * moved)}% of his pixels are drawn in a different colour (merged into the "
               f"nearest listed one): {len(used)} frame colours, {len(slots)} drawn", fix)


def _game_palette(ch):
    """The S1/S2 player palette (Sonic 1's player sheet, from the extracted game) with his own colours in: slot -> rgb."""
    tpl = REPO / "extracted" / "Sonic1" / "Data" / "Sprites" / "Players" / "Sonic1.gif"
    if not tpl.exists():
        return None
    raw = Image.open(tpl).getpalette()
    raw += [0] * (768 - len(raw))
    pal = [tuple(raw[3 * i:3 * i + 3]) for i in range(256)]
    for s, col in ch.own.items():
        if 0 <= s < 256:
            pal[s] = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
    return pal


def _mania_need(own):
    try:
        import build_mania_art as bma
        glob = {c for i, c in bma.global_palette().items() if 0 < i < bma.PLAYER_SLOT}
    except Exception:  # (no extracted Mania data: count them all)
        glob = set()
    return [c for c in own.values() if tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) not in glob]


def check_per_frame(ch, r, entry, moves, registry):
    """Per-frame lists (abilities_registry.PER_FRAME): the fields read together must be the same length (the build stops
    otherwise: tools/abilities.py melee_tables), and each one value per frame of its slot (frames times "hold")."""
    from abilities_registry import PER_FRAME
    owner = {f: m for m, e in registry.items() for f in e["fields"]}
    groups = {}
    for f, (slot, group) in PER_FRAME.items():
        v = entry.get(f)
        if v is None or owner.get(f) not in moves:
            continue
        if not isinstance(v, list):
            r.error(f"abilities {f}", f"is a {type(v).__name__}: it's a list, one value per frame of slot {slot}")
            continue
        groups.setdefault(group, []).append((f, len(v)))
        a = ch.ability_anims.get(slot) or {}
        hold = a.get("hold", 1) if isinstance(a.get("hold", 1), int) and a.get("hold", 1) > 1 else 1
        n = len(a.get("frames") or []) * hold
        if n and len(v) != n:
            r.error(f"abilities {f}", f"has {len(v)} value(s), but ability animation {slot} has {n} frame(s): it needs "
                    "one per frame", f"one value per frame (the Abilities tab keeps it in step with the animation)")
    for group, fs in groups.items():
        if len({n for _, n in fs}) > 1:
            r.error(f"abilities {fs[0][0]}", f"{group}: {', '.join(f'{f} has {n}' for f, n in fs)}: the build stops when "
                    "these lists differ in length (\"reach / top / bottom lengths differ\")",
                    "give them the same number of values: one per frame of the move")
    if entry.get("melee_air_top") is not None or entry.get("melee_air_bottom") is not None:
        if entry.get("melee_air_reach") is None and "melee" in moves:
            r.warn("abilities melee_air_top", "melee_air_top / melee_air_bottom do nothing without melee_air_reach "
                   "(the air move is then the ground one)", "add melee_air_reach, or remove them")


def check_abilities(ch, r):
    """The moves against the ability registry (tools/abilities_registry.py, docs/abilities.md): known moves, fields some
    move reads, each move's animation slots, the games it works in, and the rules on combining moves."""
    import abilities_registry as reg
    entry = ch.abilities or {}
    moves = entry.get("abilities", [])
    registry = reg.build()["abilities"]
    known = ai.modules() | {m for m, e in registry.items() if e["kind"] != "setting"}
    for m in moves:
        if m in registry and registry[m]["kind"] == "setting":
            r.warn(f"abilities {m}", "is a setting, not a move: listing it does nothing",
                   f"take it out of the list and set its fields ({', '.join(registry[m]['fields']) or m}); "
                   f"`{abilities_cmd.command()} abilities {m}` explains them")
        elif m not in known:
            r.error(f"abilities {m}", f"isn't a move NoSwap has{_near(m, known)}",
                    f"pick one from `{abilities_cmd.command()} abilities` (docs/abilities.md); new moves are core work, not character work")
    owners = reg.field_owners()
    fields = ai.fields()
    for k, v in entry.items():
        if k in ("abilities",) or k.startswith("_"):
            continue
        if k not in fields and k not in known and k not in owners:
            r.warn(f"abilities {k}", f"isn't a field any move reads, so it does nothing{_near(k, set(fields) | set(owners))}")
            continue
        mine = [o for o in owners.get(k, []) if o in moves or registry[o]["kind"] == "setting"]
        if owners.get(k) and not mine:
            r.warn(f"abilities {k}", f"belongs to {' / '.join(owners[k])}, which isn't in his abilities, so it does "
                   "nothing", f"add {owners[k][0]} to \"abilities\", or drop the field")
        types = fields.get(k, set())
        t = type(v).__name__
        if types and t not in types and not ({t} | types) <= {"int", "float"}:
            r.warn(f"abilities {k}", f"is a {t}; the other characters' are {' / '.join(sorted(types))}")
    check_per_frame(ch, r, entry, moves, registry)
    slots = set(ch.ability_anims)
    for m in moves:
        for s, d in (registry.get(m, {}).get("slots") or {}).items():
            if d["required"] and s not in slots and not (m == "umbrella" and s == "42" and "41" in slots):
                r.warn(f"abilities {m}", f"draws ability animation {s} ({d['what']}), which has no frames",
                       f"add \"{s}\": {{\"name\": ..., \"frames\": [...]}} to ability_animations")
    for k in ("melee_whip", "float_lean", "ability_cycle"):  # (settings with slots of their own)
        if entry.get(k):
            for s, d in (registry[k].get("slots") or {}).items():
                if d["required"] and s not in slots:
                    r.warn(f"abilities {k}", f"draws ability animation {s} ({d['what']}), which has no frames")
    if entry.get("umbrella_attack") and "41" not in slots:
        r.warn("abilities umbrella_attack", "draws ability animation 41, which has no frames")
    if ch.flags.get("roll") and "49" not in slots and "Rolling" not in (ball_use_for(ch) or ()):
        r.error("flags roll", "needs its rolling animation in ability_animations 49")
    # the games each move works in
    games = ["s1", "s2", "cd", "s3k"] + (["mania"] if ch.games.get("mania") else [])
    used = [m for m in moves if m in registry] + [k for k in ("shot", "melee_whip", "float_lean", "ability_cycle")
                                                  if entry.get(k)]
    for g in games:
        missing = [m for m in used if registry[m]["games"][g]["support"] == "no"]
        partial = [m for m in used if registry[m]["games"][g]["support"] == "partial"]
        if missing:
            notes = "; ".join(f"{m}: {registry[m]['games'][g]['note']}" for m in missing
                              if registry[m]["games"][g].get("note"))
            r.warn(reg.GAME_NAMES[g], f"{', '.join(missing)} {'isn' if len(missing) == 1 else 'aren'}'t in "
                   f"{reg.GAME_NAMES[g]} yet: {'it is' if len(missing) == 1 else 'they are'} skipped there"
                   + (f" ({notes})" if notes else ""),
                   "fine if that's expected; adding a move to a game is core work (docs/abilities.md)")
        for m in partial:
            r.note(reg.GAME_NAMES[g], f"{m}: {registry[m]['games'][g].get('note', 'partial')}")
    for rule, bad in reg.check_rules(entry, ch.base):
        msg = f"{rule['text']}{' (here: ' + ', '.join(map(str, bad)) + ')' if bad else ''}"
        (r.error if rule["level"] == "error" else r.warn)(f"abilities rule {rule['id']}", msg)
    try:
        changed = ai.s3k_fields(entry, ch.name)
    except SystemExit as e:
        r.error("abilities", str(e))
        changed = []
    except Exception as e:
        r.error("abilities", f"the S3&K field list can't be made from these numbers: {e!r}")
        changed = []
    s3k = ai.native_words("native/src")
    gone_s3k = [n for n, _, _ in changed if n not in s3k]
    if gone_s3k:
        r.note("S3&K", f"no DLL code reads {', '.join(gone_s3k)}")
    shot = entry.get("shot")
    if isinstance(shot, dict) and isinstance(shot.get("art"), dict) and "sheet" in shot["art"]:
        p = ch.folder / shot["art"]["sheet"]
        if not p.exists():
            r.error("abilities shot.art.sheet", f"{p} doesn't exist")
        else:
            W, H = Image.open(p).size
            for d in [shot["art"].get("drawing")] + list(shot["art"].get("drawings", [])):
                if d and (d[0] + d[2] > W or d[1] + d[3] > H):
                    r.error("abilities shot.art", f"drawing {d[:4]} reaches past {p.name}'s edge ({W}x{H})")
    if "melee" in moves and not isinstance(shot, dict) and not entry.get("melee_reach") and not entry.get("melee_radial"):
        r.warn("abilities melee", "no \"shot\" and no melee_reach: the Y move reaches nothing")


def check_sounds(ch, r):
    """Its own sounds (character.json "sounds" and the "own:<name>" sound fields: tools/own_sounds.py)."""
    if ch.kind != "json":
        return
    import own_sounds
    own_sounds.check({**ch.cleaned, "folder": ch.folder}, r)


def check_credits(ch, r):
    cr = ch.credits or {}
    if not cr.get("full", "").strip():
        r.error("credits.full", "is empty", "credit the sheet's artist(s) as the sheet asks")
    short = cr.get("short", "")
    if not short:
        r.warn("credits.short", "is empty: no credit line under the Origins card", "e.g. \"Sprites: <artist>\"")
    elif len(short) > CREDIT_HARD:
        if ch.kind != "json":  # (the schema already says so for a character.json)
            r.error("credits.short", f"is {len(short)} characters; the card has room for {CREDIT_HARD}")
    elif len(short) > CREDIT_SOFT:
        r.warn("credits.short", f"is {len(short)} characters; keep it to about {CREDIT_SOFT} so it fits the card")
    if ch.kind == "json":
        if not cr.get("terms", "").strip():
            r.warn("credits.terms", "is empty", "copy the sheet's terms of use word for word")
        if not cr.get("artists"):
            r.warn("credits.artists", "is empty")
        if not cr.get("url"):
            r.note("credits.url", "is empty: where the sheet comes from")
    elif not (ch.folder / "SOURCE.txt").exists():
        r.warn("SOURCE.txt", "missing: the sheet's source and terms aren't recorded")
    if NO_EDIT.search(json.dumps(cr)):
        edits = [(w, s) for w, s in ch.used_specs()
                 if isinstance(s, dict) and ({"layers", "rotate", "flip", "scale", "circle"} & set(s))]
        if edits:
            w, s = edits[0]
            r.warn("credits.terms", f"the sheet says not to edit it, but {len(edits)} frame(s) are put together, turned or "
                   f"mirrored (first: {w})", "use frames only as drawn (crops), or get the artist's OK")


def check_registration(ch, r):
    e = ch.extra
    if e is None:
        r.note("registration", "not in tools/extras.py yet, so the build doesn't know him",
               f"add character_json.extras_entry(REPO / \"testmods\" / \"{ch.id}\") to EXTRAS and his abilities entry "
               "to tools/abilities.py (step 4 of the toolset plan removes this step)")
    else:
        r.note("registration", f"extra {e['n']} ({e['file']}, build ID {e['id']}), key {e['key']}")
        if ch.kind == "json" and e.get("name") != ch.name:
            r.error("registration", f"tools/extras.py says {e.get('name')!r}, character.json says {ch.name!r}")
    if ch.card:
        p = (ch.folder / ch.card["sheet"]) if isinstance(ch.card.get("sheet"), str) else ch.card.get("sheet")
        if p and not p.exists():
            r.warn("card.sheet", f"{p} doesn't exist (yet): the card can't be built",
                   "a card from a build intermediate (build/...) appears after `noswap build`")


def run(folder):
    """(Character or None, Report)."""
    r = Report()
    try:
        ch = load(folder)
    except CharacterError as e:
        r.error(str(folder), str(e))
        return None, r
    if ch.kind == "json":
        check_schema(ch, r)
        for old, new in ch.renamed:
            r.note(f"abilities {new}", f"renamed: {old} is now {new}",
                   "it still works; the editor's Save writes the new name (or rename it in the file)")
    else:
        r.note("format", "an old-style make_configs.py character: checked from the configs it last wrote",
               f"`noswap convert {ch.id}` turns it into a character.json")
    if not ch.sheet.exists():
        r.error("sheet.file", f"{ch.sheet} doesn't exist")
        return ch, r
    sheet = Image.open(ch.sheet)
    checks = [lambda: check_frames(ch, r, sheet), lambda: check_animations(ch, r), lambda: check_ball(ch, r), lambda: check_no_stomp(ch, r), lambda: check_ui(ch, r, sheet), lambda: __import__("noswap_cli.ui_boxes", fromlist=["check"]).check(ch, r), lambda: check_act_name(ch, r),
              lambda: check_palette(ch, r, sheet), lambda: check_abilities(ch, r), lambda: check_credits(ch, r), lambda: check_sounds(ch, r),
              lambda: check_registration(ch, r)]
    for c in checks:
        try:
            c()
        except Exception as e:  # (one broken section shouldn't hide the others' findings)
            r.error("check", f"{c.__code__.co_names[0] if c.__code__.co_names else 'a check'} stopped: {e!r}")
    return ch, r
