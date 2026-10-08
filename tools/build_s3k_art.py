#!/usr/bin/env python3
"""Build an extra's Sonic 3 & Knuckles sprites (v5 .bin + sheet) from its Sonic 2 sheet2ani config.

Usage: build_s3k_art.py <extra s2 config.json> ...

S3&K's player animations follow Sonic Mania's list (3K_Players/Sonic.bin is the template): each of
them gets the extra's own art for it when the config has some under the S3&K name (its "s3k_animations":
Mania-style sheets have Jog, Dash, pole swings, Transform...; an "Angled" variant uses the flat one), and the
extra's closest Sonic 2 animation otherwise. Animations S3&K has and the extra doesn't (barrels,
cylinders...) get its standing frame, so it never turns invisible; the ones the base leaves empty (or draws as
nothing) stay so, since the game's code relies on that. "Angled" variants (pre-rotated slope poses in S3&K)
reuse the flat poses. Every animation the base has keeps exactly its frame count, loop, speed and per-frame timing, draw-order code and hitboxes (the game's code counts and picks
frames); the extra's own frames are fitted into them. Colours are matched to S3&K's player palette slots.
The NoSwap DLL loads the result instead of 3K_Players/Sonic.bin while the extra is picked (or instead of
Knux.bin / Tails.bin for extras built on Knuckles or Tails, extras.py "base"), and 3K_Special/Extra.bin
(the Blue Spheres runner, as the extra's spin ball) instead of the base's runner file there.

Output: the extra's files go under the fixed names (extras.S3K_FIXED: 3K_Players/Extra.bin / .gif, 3K_Special/
Extra.bin and NoSwap_Extra.gif), and its save screen picture under extras.S3K_MENU_PICTURE (3K_Players/MenuPicture.bin
/ .gif), in extras.s3k_build(extra), outside the mod; build_packages.py copies them into its package. Only the shared
NoTail.bin goes in NoSwap's own folder.
"""
import json
import statistics
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import abilities as ab
import ani_v5
import sheet2ani
from extras import EXTRAS, S3K_FIXED, S3K_MENU_PICTURE, S3K_MENU_PICTURES, menu_picture, s3k_build
from gifio import save_sheet

REPO = Path(__file__).resolve().parent.parent
S3K = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"
OUT = REPO / "mods" / "NoSwap" / "Sonic3ku" / "Data" / "Sprites"

# S3&K animation -> the extra's Sonic 2 animation (first one that exists)
FROM_S2 = {
    "Idle": ["Stopped"], "Bored 1": ["Waiting", "Bored!"], "Bored 2": ["Bored!", "Waiting"],
    "Look Up": ["Looking Up"], "Crouch": ["Looking Down"],
    **{n: ["Walking"] for n in ("Walk", "Walk Angled", "Fall", "Fall Angled", "Jog", "Jog Angled")},
    **{n: ["Running"] for n in ("Run", "Run Angled", "Dash", "Dash Angled", "Peelout", "Peelout Angled")},
    "Jump": ["Jumping"], "Dropdash": ["Jumping"], "Transform": ["Jumping"],
    "Spring Twirl": ["Twirl H", "Bouncing"], "Spring Diagonal": ["Bouncing"], "Hang Twirl": ["Twirl H", "Bouncing"],
    "Skid": ["Skidding"], "Skid Turn": ["Skidding"], "Spindash": ["Spin Dash"], "Push": ["Pushing"],
    "Hurt": ["Hurt"], "Die": ["Dying"], "Drown": ["Drowning"],
    "Balance 1": ["Flailing 1"], "Balance 2": ["Flailing 2"], "Tremble": ["Flailing 3", "Flailing 1"],
    "Fan": ["Fan Rotate"], "Breathe": ["Breathing"], "Bubble": ["Breathing"],
    # hanging by the hands (vines, ropes, handles): the extras' arms-up spring pose (their "Hanging"
    # frames are Sonic 1's horizontal pole poses)
    **{n: ["Bouncing"] for n in ("Hang Move", "HangGimmick", "Pulley Hold", "HangBackwards", "HangPlayer",
                                  "Pole Swing V", "Pole Swing H", "Shaft Swing", "Shimmy Idle", "Shimmy Move",
                                  "RappelDown", "RappelBarSwing", "HorizontalBarHang", "SpinHandle")},
    "Cling": ["Clinging On"], "Flume": ["Water Slide"], "Slope Slide": ["Water Slide"],
    # Sonic's somersault seen from every angle, the frame picked by the game per angle (Angel Island's hollow
    # tree runs him up its trunk in it, turned on his side): the extras have no somersault, so they run
    # (Spring CS / Spring CS Rev: see CORKSCREWS)
    "Stand CS": ["Walking"], "Spring CS": ["Running", "Walking"], "Spring CS Rev": ["Running", "Walking"],
    "Continue": ["Continue"], "Continue Up": ["Continue Up"], "Twister": ["Twirl H", "Walking"],
    "Spiral Run": ["Walking"], "TwistRun": ["Running"], "CylinderWalkOuter": ["Walking"],
    "CylinderWalkInner": ["Walking"], "Grabbed": ["Grabbed"],
    # Knuckles' own (3K_Players/Knux.bin), for extras built on him
    "Ledge Pull Up": ["Ledge Pull Up"], "Glide": ["Gliding"], "Glide Drop": ["Gliding Drop"],
    "Glide Land": ["Gliding Stop"], "Glide Slide": ["Gliding Stop"],
    "Climb Idle": ["Climbing"], "Climb Up": ["Climbing"], "Climb Down": ["Climbing"],
    # Tails' own (3K_Players/Tails.bin), for extras built on him
    "Fly": ["Flying"], "Fly Tired": ["Flying Tired", "Flying"], "Fly Lift": ["Fly Lift Up", "Flying"],
    "Fly Lift Down": ["Fly Lift Down", "Flying"], "Fly Lift Tired": ["Fly Lift Tired", "Flying Tired", "Flying"],
    "Swim": ["Swimming", "Flying"], "Swim Tired": ["Swimming Tired", "Flying Tired", "Flying"],
    "Swim Lift": ["Swim Lift", "Swimming", "Flying"],
    "DashAngled1": ["Running"], "DashAngled2": ["Running"], "DashVertical": ["Running"],
    "CylinderSpin": ["Jumping"], "RappelDownLegBent": ["Bouncing"],
}
# Hanging by the hands (the arms-up stand-in above): hands where the base's are, not feet on his feet line
HANG_FROM_HANDS = {"Hang Move", "HangGimmick", "Pulley Hold", "HangBackwards", "HangPlayer", "Shimmy Idle",
                   "Shimmy Move", "RappelDown", "RappelBarSwing", "HorizontalBarHang", "SpinHandle"}
# Swinging round a bar or pole (Mushroom Hill's GymBar and others): the stand-in turns to hold on from the
# side of the bar the base's frame is on (an extra's own swing frames, drawn round the bar, are only placed)
SWINGS = {"Pole Swing V", "Pole Swing H", "Shaft Swing"}
# Running round a trunk (Angel Island's hollow tree: the exe's Cylinder object, its "Tree" type, State_Tree at
# 0x14019d160). Each frame it sets Spring CS, draws the player turned a quarter turn (drawFX rotate, rotation
# 0x80: lying on his side, running up the screen) and picks the frame itself from the angle round the trunk:
# frameID = (count * angle / 1024 + count / 8 + count / 2) % count. Sonic's 12 frames are a roll round his long
# axis: upright on the right half of the trunk, upside down (feet always on the bark) on the left half. The extras
# get their run cycle the same way: the frames on the right half upright, the ones on the left half mirrored top
# to bottom, the cycle stepping on with the angle (legs moving as they go round). Spring CS Rev is the same set
# backwards, as the base's. An extra with a real rotation set of its own under "Spring CS" in its s3k_animations
# uses it as it is with "s3k_corkscrew": "own" in its config; "s3k_corkscrew": "<Sonic 2 animation>" picks
# other frames for the run (default its Running, else its Walking).
CORKSCREWS = {"Spring CS", "Spring CS Rev"}
# Knuckles' glide landings: his belly slide and getting up stand on the ground line in S3&K (Knux.bin: every frame's
# bottom at +20), but Sonic 2 draws the slide 7 px higher (Gliding Stop's bottom at +13: its smaller sliding box), so
# the extras' frames, placed like Sonic 2's, floated above the ground (Rouge, the user, 2026-09-30). Each frame's bottom
# goes on the base frame's bottom.
GLIDE_LANDINGS = {"Glide Land", "Glide Slide"}


def corkscrew_order(frames, m, reverse):
    """The extra's run `frames` over the base's `m` Spring CS frames: [(frame, upside down)], see CORKSCREWS."""
    n = len(frames)
    order = [(frames[k % n], (k - m // 2 - m // 8) % m * 2 >= m) for k in range(m)]
    return order[::-1] if reverse else order
# Balls that roll on the ground: their bottom on the ground line of the box the frame uses (sheet2ani.GROUNDED_BALLS)
GROUNDED_BALLS = {"Jump", "Spindash", "Dropdash"}
# The largest player sheet the game loads itself (Amy.gif, Knux.gif: 512x1024)
MAX_SHEET_HEIGHT = 1024
# The base character's S3&K file (extras.py "base"): the extra's art replaces it, so the base's own
# code (Knuckles' glide and climb, Tails' flight) runs with the extra's animations
BASE_FILE = {"sonic": "Sonic", "knuckles": "Knux", "tails": "Tails"}
# Ability animations go after the base file's own (77 for Sonic, 78 Knuckles, 84 Tails): S1/S2 slot ->
# offset (attack, hover/umbrella, shot, the aim dash's up / down attacks, and the glide's up / down poses)
ABILITY_SLOTS = {"41": 0, "42": 1, "43": 2, "45": 3, "46": 4, "47": 5, "48": 6}
# Only for extras that have it (the others' files stay as they were): the own rolling curl (extras.py "roll"),
# which the DLL shows instead of the jump while rolling on the ground (S3&K rolls in its "Jump" animation)
ROLL_SLOT, ROLL_OFFSET = "49", 7
# Likewise only for extras whose air shot has its own frames and reach (abilities.py melee_air_reach: Tikal's
# air punch); the others show the ground shot in the air
AIR_SHOT_SLOT, AIR_SHOT_OFFSET = "44", 8
# melee_whip's poses (abilities.py: John's whip crouching, up-forward, down): their slots, whose outer boxes are the
# pose's reach per frame (the DLL shows them as his melee, by the d-pad)
WHIP_SLOTS = {"41": "crouch", "45": "up", "46": "down"}
# And for extras with a Power Surge (abilities.py power_surge): its idle / walk / run, which the DLL shows in place of
# the game's while a surge lasts
SURGE_SLOTS = {"50": 9, "51": 10, "52": 11}
# And for extras with copy heads (Emerl's: his config's "copy_heads", abilities.py copy_heads): per Copycat move, a copy
# of these with that move's head on every frame (its "swap" table), from offset COPY_HEAD_OFFSET on, COPY_HEADS_S3K
# animations a move ("shot": the ability shot, offset 2: his copy flash). The DLL shows the active move's copy in place of
# the game's (NoSwapS3K.cpp CopyHeadShow: the IDs 0, 1 and 5-14 in turn, then the Peelout pair and the shot, in this order)
COPY_HEAD_OFFSET = 12
COPY_HEADS_S3K = ["Idle", "Bored 1", "Walk", "Walk Angled", "Fall", "Fall Angled", "Jog", "Jog Angled", "Run",
                  "Run Angled", "Dash", "Dash Angled", "Peelout", "Peelout Angled", "shot"]


def victory_order(frames, pose, t):
    """The extra's act clear celebration (`frames`: its build-up, then from `pose` on the pose it holds or loops) fitted
    to the base's Victory `t`, which is a short build-up, then a pose held (Sonic's frame 1 lasts 6 times the rest) and
    looped from its loop frame (Sonic 6 frames, loop 2: a small wiggle; Knuckles 6, loop 5; Tails 2, loop 1: the last
    frame held). The build-up goes in the base's short leading frames (spread, if it has more frames than those), the
    pose in the rest: the held lead-in frames get its first frame, the loop all of its frames in order, spread (a
    2-frame wave over Sonic's 4 loop frames: 2 frames each), so the last frame the game holds is always a pose."""
    m = len(t["frames"])
    lead_in = t["loop"] if 0 < t["loop"] < m else m - 1
    build_up, poses = frames[:pose], frames[pose:] or frames[-1:]
    short = min(tf["duration"] for tf in t["frames"])
    slots = next((k for k in range(lead_in) if t["frames"][k]["duration"] > short), lead_in)  # the short leading frames
    order = []
    for k in range(lead_in):
        if build_up and k < slots and (len(build_up) > slots or k < len(build_up)):
            order.append(build_up[k * len(build_up) // slots] if len(build_up) > slots else build_up[k])
        else:
            order.append(poses[0])
    return order + [poses[j * len(poses) // (m - lead_in)] for j in range(m - lead_in)]


def build(cfg_path):
    cfg_path = Path(cfg_path)
    cfg = json.loads(cfg_path.read_text())
    name = cfg["name"]
    src = Image.open(cfg_path.parent / cfg["source"]).convert("RGBA")
    background = {sheet2ani.hexrgb(c) for c in cfg["background"]}
    extra = next(e for e in EXTRAS if e["file"] == name)
    base = BASE_FILE[extra["base"]]
    tpl_img = Image.open(S3K / "3K_Players" / f"{base}.gif")
    tpl_pal = tpl_img.getpalette()
    rgb = lambda i: tuple(tpl_pal[3 * i:3 * i + 3])
    template = ani_v5.read_bin(S3K / "3K_Players" / f"{base}.bin")
    # the base character's colours: the palette slots its own sprite uses (Sonic 2-16, Knuckles 5-20...)
    PLAYER_SLOTS = sorted(i for _, i in tpl_img.getcolors(256) if i not in (0, 255))

    # Colours: the extra's own palette slots stay (the DLL loads its colours); everything else is
    # matched to the nearest of Sonic's S3&K colours by RGB
    own = {sheet2ani.hexrgb(c): int(s) for s, c in cfg.get("palette", {}).items()}
    colours = {}

    def index_of(c):
        if c in own:
            return own[c]
        if c not in colours:
            colours[c] = min(PLAYER_SLOTS, key=lambda i: sum((a - b) ** 2 for a, b in zip(c, rgb(i))))
        return colours[c]

    cut = {}

    def frame_image(fr):
        key = sheet2ani.frame_key(fr)
        if key not in cut:
            if isinstance(fr, dict) and "layers" in fr:
                img, mask, anchor = sheet2ani.cut_layered(src, fr, background)
            elif isinstance(fr, dict):
                img, mask, anchor = sheet2ani.cut_spec(src, fr, background)
            else:
                img, mask = sheet2ani.cut_frame(src, fr, background)
                anchor = None
            out = Image.new("P", img.size, 0)
            for y in range(img.height):
                for x in range(img.width):
                    if mask.getpixel((x, y)):
                        out.putpixel((x, y), index_of(img.getpixel((x, y))[:3]))
            cut[key] = (out, anchor or (0, 0, img.width, img.height))
        return cut[key]

    anims_s2 = cfg["animations"]
    own_s3k = cfg.get("s3k_animations", {})  # the extra's own art under S3&K names (sheet2ani ignores the key)

    def own_name(name):
        """The extra's own S3&K animation for the base's `name` (an "Angled" one uses the flat one), or None."""
        flat = name[:-len(" Angled")] if name.endswith(" Angled") else name
        return next((n for n in (name, flat) if n in own_s3k), None)

    def rotation(style):
        """S3&K's walk / run use style 5, static frames: tilted at 45 degrees by showing the next ("Angled")
        animation's frames, turned in quarter turns beyond that. Extras with real tilted art (Knuckles-style
        sheets, split into those Angled animations) keep it; the rest turn their upright frames in 45-degree
        steps (style 2), as in Sonic 1 and 2, instead of not turning at all. An extra with the floating lean
        (abilities.py float_lean: Mephiles) gets full rotation (style 1) there: the DLL draws them turned by the lean
        alone (NoSwapS3K.cpp FloatLean)."""
        if style != 5:
            return style
        if ab.ABILITIES.get(extra["id"], {}).get("float_lean"):
            return 1
        return 5 if knuckles_layout else 2
    # walk / run drawn upright then pre-rotated 45 degrees: an extra built on Knuckles (extras.py "base"), whose
    # template is laid out so, or one whose sheet is ("angled_halves" in its config: Trip). Without the split, the
    # 45-degree half played in the middle of the flat walk (Trip tilted every few steps).
    knuckles_layout = "Knuckles.ani" in cfg["template_ani"] or cfg.get("angled_halves", False)

    def turned(key, quarter):
        """The frame cut `key`, turned `quarter` quarter turns anticlockwise (a new cut)."""
        if not quarter:
            return key
        new = f"{key}@{quarter * 90}"
        if new not in cut:
            img, _ = cut[key]
            img = img.transpose([None, Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270][quarter])
            cut[new] = (img, (0, 0, img.width, img.height))
        return new

    def flipped(key):
        """The frame cut `key`, mirrored top to bottom (a new cut)."""
        new = f"{key}@flip"
        if new not in cut:
            img, _ = cut[key]
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            cut[new] = (img, (0, 0, img.width, img.height))
        return new

    def hang(f, tf, swing):
        """Put an arms-up stand-in (`f`) where the base's own frame (`tf`) has its hands: its top on the
        frame's top, centred on it. Swinging round a bar (`swing`, the bar at the player's position), it
        turns to hold on from the side the base's frame is on: hanging under the bar, upside down over it,
        or on its side left / right of a pole."""
        cx, cy = tf["px"] + tf["w"] / 2, tf["py"] + tf["h"] / 2
        side = 0
        if swing:
            if tf["w"] > tf["h"]:
                side = 1 if cx >= 0 else 3  # body right of the pole: hands to the left (a quarter turn)
            elif cy < 0:
                side = 2  # over the bar: upside down, hands at the bottom
        key = turned(f["img"], side)
        img = cut[key][0]
        if side == 0:
            px, py = round(cx - img.width / 2), tf["py"]
        elif side == 2:
            px, py = round(cx - img.width / 2), tf["py"] + tf["h"] - img.height
        elif side == 1:
            px, py = tf["px"], round(cy - img.height / 2)
        else:
            px, py = tf["px"] + tf["w"] - img.width, round(cy - img.height / 2)
        return dict(f, img=key, px=px, py=py)

    def grip(f, tf, swing):
        """Place the extra's own hanging / swinging frame (`f`, drawn holding on: not turned) with its hands
        where the base's frame (`tf`) has them. Hanging: its top on the frame's top, centred on it. Swinging
        round a bar (the bar at the player's position; the sheets don't mark it): on each axis the bar keeps
        its distance from the edge of the base's frame it's in the outer third of (the hands: under, over or
        beside the bar), or the frames are centred on each other when it's in the middle third."""
        img = cut[f["img"]][0]

        def axis(p, size, own):
            if swing and -p < size / 3:
                return p
            if swing and -p > 2 * size / 3:
                return p + size - own
            return round(p + (size - own) / 2)
        px = axis(tf["px"], tf["w"], img.width)
        py = axis(tf["py"], tf["h"], img.height) if swing else tf["py"]
        return dict(f, px=px, py=py)

    anims = []
    natural = {}  # the extra's own frames, before fitting them to the base's frame count
    # the base's feet line: the bottom of its standing box (Sonic and Knuckles 20, Tails 16)
    feet_y = next(a for a in template["anims"] if a["name"] == "Idle")["frames"][0]["boxes"][0][3]

    def offset(frames):
        """Each frame's own "offset" (sheet2ani.frame_offset, carried as "off"), last: after the anchor, align, the
        fitting to the base's frames (hands on the bar, glide landings) and the ball's ground line, as in Sonic 1/2."""
        for f in frames:
            dx, dy = f.pop("off", (0, 0))
            f["px"] += dx
            f["py"] += dy

    def on_ground(frames):
        """A ball (GROUNDED_BALLS) on the ground line of the outer box the game collides with (after fitting, so it's
        the base's box for each frame): the frames move up or down together until the lowest pixel of any is on the
        row above it (sheet2ani.put_on_ground). Centred, a small ball floated and a big one sank."""
        # (measured on the extra's own frames, each once, as in Sonic 1 and 2: fitted to the base's count, some repeat)
        own = list({f["img"]: f for f in reversed(frames)}.values())[::-1]
        shift = sheet2ani.ground_shift(own, [cut[f["img"]][0] for f in own], [f["boxes"][0][3] for f in own])
        for f in frames:
            f["py"] -= shift
    # The act clear's celebration (its "s3k_victory": {"frames": [build-up..., pose...], "pose": index of the first pose
    # frame, default the last}): see victory_order
    victory = cfg.get("s3k_victory")
    for t in template["anims"]:
        own_anim = own_name(t["name"])
        corkscrew = t["name"] in CORKSCREWS and cfg.get("s3k_corkscrew") != "own"
        if t["name"] == "Victory" and victory:
            own_anim, source = "Victory", victory
        elif corkscrew:  # the run, turned per angle round the trunk (CORKSCREWS), even over an own Spring CS
            own_anim = None
            pick = [cfg["s3k_corkscrew"]] if cfg.get("s3k_corkscrew") else FROM_S2[t["name"]]
            source = next((anims_s2[n] for n in pick if n in anims_s2), None)
        else:
            source = own_s3k[own_anim] if own_anim else next((anims_s2[n] for n in FROM_S2.get(t["name"], []) if n in anims_s2), None)
        if source is None:
            source = anims_s2["Stopped"]  # never invisible
        tf = t["frames"][0] if t["frames"] else None
        frames = []
        source_frames = source["frames"]
        if knuckles_layout and source in (anims_s2.get("Walking"), anims_s2.get("Running")):
            # Knuckles-style walk / run: upright frames, then the same pre-drawn at 45 degrees, which is
            # exactly S3&K's separate "Angled" animations
            half = len(source_frames) // 2
            if half:  # (a single frame can't be halved: it stands for both, upright and angled)
                source_frames = source_frames[half:] if t["name"].endswith("Angled") else source_frames[:half]
        for fr in source_frames:
            img, (ax, ay, aw, ah) = frame_image(fr)
            if source.get("anchor", "feet") == "feet":
                px, py = -(ax + aw // 2), feet_y - (ay + ah)
            else:
                px, py = -(ax + aw // 2), -(ay + ah // 2)
            frames.append(dict(img=sheet2ani.frame_key(fr), px=px, py=py,
                               duration=tf["duration"] if tf else 8, char=0,
                               boxes=tf["boxes"] if tf else [(-10, -20, 10, 20), (-8, -16, 8, 16)],
                               off=sheet2ani.frame_offset(fr)))
        if source.get("align") and len(frames) > 1:  # keep the body put (sheet2ani.align_x)
            xs = sheet2ani.align_x([cut[f["img"]][0] for f in frames], [(f["px"], f["py"]) for f in frames])
            for f, px in zip(frames, xs):
                f["px"] = px
        natural[t["name"]] = frames
        if t["frames"] and own_anim and source.get("own_count") and len(frames) > len(t["frames"]):
            # The extra's own frame count ("own_count" in its s3k_animations: only where the game never counts the
            # frames, e.g. Tails' 1-frame Fly, animated by the speed his flight state sets each frame): the base's
            # last frame's timing, code and hitboxes for the added ones. With a lead-in before the loop (Sonic's Dash:
            # loop 1), room for the lead-in too, so the loop holds the whole cycle (Shadow's 12-frame skate at top speed)
            lead = t["loop"] if 0 < t["loop"] < len(t["frames"]) else 0
            t = dict(t, frames=t["frames"] + [t["frames"][-1]] * (len(frames) + lead - len(t["frames"])))
        if t["frames"]:
            # Exactly the base's frames: the game's code counts them, waits for given frame numbers and picks
            # frames itself (a swing bar lets go after a lap of its frames, the hollow tree picks one per
            # angle, bored timers reset on a frame number), so every frame keeps the base's timing, character
            # code (draw order round a bar) and hitboxes; only the picture is the extra's. Its own frames are
            # spread over them in order, or looped when there are far more to fill (a long bored animation).
            n, m = len(frames), len(t["frames"])
            cyclic = t["speed"] and m > 2 * n
            # A lead-in made of the loop's own frames (Sonic's Dash: its last run frame, then the 4-frame run looping
            # from frame 1): the extra's whole cycle goes in the loop, the lead-in takes its last frames. Spread over
            # all the frames instead, the loop got an uneven, out-of-order part of the cycle (Jet's top-speed run
            # flickered between two poses).
            lead = t["loop"] if 0 < t["loop"] < m else 0
            rect = lambda tf: (tf["x"], tf["y"], tf["w"], tf["h"])
            upside_down = [False] * m
            if t["name"] == "Victory" and victory:
                order = victory_order(frames, victory.get("pose", n - 1), t)
            elif corkscrew:
                order, upside_down = zip(*corkscrew_order(frames, m, t["name"].endswith("Rev")))
            elif lead and not cyclic and all(rect(a) in {rect(b) for b in t["frames"][lead:]} for a in t["frames"][:lead]):
                order = [frames[(n - lead + k) % n] for k in range(lead)] + \
                        [frames[j * n // (m - lead)] for j in range(m - lead)]
            else:
                order = [frames[k % n] if cyclic else frames[k * n // m] for k in range(m)]
            fitted = []
            for k, tf in enumerate(t["frames"]):
                f = dict(order[k], duration=tf["duration"], char=tf["char"], boxes=[tuple(b) for b in tf["boxes"]])
                if upside_down[k]:  # mirrored top to bottom about the player's centre (feet on the bark: CORKSCREWS)
                    f = dict(f, img=flipped(f["img"]), py=-(f["py"] + cut[f["img"]][0].height))
                if (t["name"] in HANG_FROM_HANDS or t["name"] in SWINGS) and own_anim:
                    f = grip(f, tf, t["name"] in SWINGS)
                elif t["name"] in HANG_FROM_HANDS or t["name"] in SWINGS:
                    f = hang(f, tf, t["name"] in SWINGS)
                elif t["name"] in GLIDE_LANDINGS and not own_anim and tf["h"]:
                    f = dict(f, py=tf["py"] + tf["h"] - cut[f["img"]][0].height)
                if not tf["w"] or not tf["h"]:
                    f["blank"] = True  # drawn as nothing by the base (Sonic's "Climbing"): nothing for the extra too
                fitted.append(f)
            frames = fitted
            if own_anim and source.get("own_count") and source.get("hold", 1) > 1:
                # sheet2ani's "hold" (each pose shown N times: an animation whose speed the flight code sets, Cream's
                # flap) as N times the duration: the same pace as Sonic 1/2's copies (S3&K's speed and duration are
                # in the same 240-a-frame units), without padding the frame list
                frames = [dict(f, duration=f["duration"] * source["hold"]) for f in frames]
            if t["name"] in GROUNDED_BALLS:
                on_ground([f for f in frames if not f.get("blank")])
            offset(frames)
        else:
            # The base leaves it empty (Sonic's Spring Twirl, Skid Turn, Outta Here, Stick, Bubble, Ride, Bungee...;
            # Knuckles' Jog and Dash too): so does the extra. The engine points an empty animation at the next one's
            # frames with a frame count of 0, and the game's code relies on that: setting one while the next plays is
            # a no-op (the ID stays), "last frame" checks never pass, and objects show the next one's pose (Sonic's
            # springs show Spring Diagonal through Spring Twirl). Given frames of their own, the extras broke objects
            # the base works with.
            frames = []
        anims.append(dict(name=t["name"], speed=t["speed"] or 0, loop=t["loop"] if t["loop"] < len(frames) else 0,
                          rot=rotation(t["rot"]), frames=frames))

    # Ability animations: the NoSwap DLL plays these (see native/src/NoSwapS3K.cpp)
    extra_id = next(e["id"] for e in EXTRAS if e["file"] == name)
    reach = ab.ABILITIES.get(extra_id, {}).get("melee_reach")
    radial = ab.ABILITIES.get(extra_id, {}).get("melee_radial", False)
    blast = ab.ABILITIES[extra_id].get("blast_radius") if ab.has(extra_id, "rocket_ride") else None
    spin = ab.has(extra_id, "spin_attack")
    air_reach = ab.ABILITIES.get(extra_id, {}).get("melee_air_reach")
    whip = ab.ABILITIES.get(extra_id, {}).get("melee_whip")  # (John's whip poses: slots 41, 45, 46; WHIP_SLOTS)
    # (melee_run / melee_up: Axel's Grand Upper and Dragon Wing, slots 45 / 46; abilities.py VARIANT_POSES)
    variant = {str(slot): ab.ABILITIES.get(extra_id, {}).get(k) for k, (_, _, slot) in ab.VARIANT_POSES.items()}
    # the shot box's top / bottom per frame (default -20 / 20): Tikal's uppercut, Gamma's thin beam
    band = {k: ab.ABILITIES.get(extra_id, {}).get(k)
            for k in ("melee_top", "melee_bottom", "melee_air_top", "melee_air_bottom")}

    def edge(key, k, default):
        v = band[key]
        return v[min(k, len(v) - 1)] if v else default
    jump = next(a for a in template["anims"] if a["name"] == "Jump")["frames"][0]
    first = len(template["anims"])
    slots = dict(ABILITY_SLOTS)
    if extra["roll"]:
        if cfg.get("appended_animations", {}).get(ROLL_SLOT, {}).get("name") != "Rolling":
            sys.exit(f"{name}: extras.py \"roll\" needs a \"Rolling\" animation in slot {ROLL_SLOT}")
        slots[ROLL_SLOT] = ROLL_OFFSET
    if air_reach:
        if not cfg.get("appended_animations", {}).get(AIR_SHOT_SLOT):
            sys.exit(f"{name}: melee_air_reach needs the air shot's animation in slot {AIR_SHOT_SLOT}")
        slots[AIR_SHOT_SLOT] = AIR_SHOT_OFFSET
    if ab.has(extra_id, "power_surge"):
        if any(not cfg.get("appended_animations", {}).get(s) for s in SURGE_SLOTS):
            sys.exit(f"{name}: power_surge needs its idle / walk / run in slots {', '.join(SURGE_SLOTS)}")
        slots.update(SURGE_SLOTS)
    idle = next(a for a in template["anims"] if a["name"] == "Idle")["frames"][0]
    for slot, target in sorted(((s, first + o) for s, o in slots.items()), key=lambda s: s[1]):
        spec = cfg.get("appended_animations", {}).get(slot)
        while len(anims) < target:
            anims.append(dict(name="(unused)", speed=0, loop=0, rot=0, frames=[]))
        if not spec:
            anims.append(dict(name="(unused)", speed=0, loop=0, rot=0, frames=[]))
            continue
        frames = []
        for k, fr in enumerate(spec["frames"]):
            img, (ax, ay, aw, ah) = frame_image(fr)
            if spec.get("anchor", "feet") == "feet":
                px, py = -(ax + aw // 2), feet_y - (ay + ah)
            else:
                px, py = -(ax + aw // 2), -(ay + ah // 2)
            # (standing and running poses: the standing boxes)
            # ("s3k_boxes": "idle": a pose on the ground in the standing boxes, Mega Man's Slide)
            boxes = [tuple(b) for b in (idle if slot in SURGE_SLOTS or spec.get("s3k_boxes") == "idle" else jump)["boxes"]]
            if slot == "43" and reach:  # the shot: the outer box reaches out to the cork / lure
                r = max(10, reach[min(k, len(reach) - 1)])
                boxes[0] = ((-r, -r, r, r) if radial  # radial: all around (Silver)
                            else (-10, edge("melee_top", k, -20), r, edge("melee_bottom", k, 20)))
            if whip and slot in WHIP_SLOTS:  # melee_whip (John's): the whip pose's own reach and box, per frame
                w = whip[WHIP_SLOTS[slot]]
                boxes[0] = (-10, w["top"][min(k, len(w["top"]) - 1)], max(10, w["reach"][min(k, len(w["reach"]) - 1)]),
                            w["bottom"][min(k, len(w["bottom"]) - 1)])
            if variant.get(slot):  # melee_run / melee_up: the pose's own reach and box per frame ("radial": all round)
                v = variant[slot]
                at = lambda key, d: v[key][min(k, len(v[key]) - 1)] if key in v else d
                r = max(10, at("reach", 10))
                boxes[0] = ((-r, -r, r, r) if slot == "46" and v.get("radial")
                            else (-10, at("top", -20), r, at("bottom", 20)))
            if slot == AIR_SHOT_SLOT:  # the air shot's own reach, and how far up it goes (Tikal's uppercut)
                r = max(10, air_reach[min(k, len(air_reach) - 1)])
                boxes[0] = (-10, edge("melee_air_top", k, -20), r, edge("melee_air_bottom", k, 20))
            if slot == "41" and blast and k > 0:  # the Rocket Ride's blast frames (after the ride): all around him
                boxes[0] = (-blast, -blast, blast, blast)
            # (the Ear Grapple's frames keep his own boxes: the game collides the outer box with the terrain, so an
            # outer box out to the ear's tip fought the pull; the tip hits things through the DLL's EarTouch now: the
            # user, 2026-09-30)
            if spin and slot in ("41", "43"):  # the Spin Attack (Honey's turn on the spot, standing poses): on the
                if slot == "43":  # ground in the standing boxes, so the game doesn't move her to a shorter box's ground
                    boxes = [tuple(b) for b in idle["boxes"]]
                if spec.get("anchor", "feet") == "feet":  # her feet on the ground line of the box the game collides with
                    py = boxes[0][3] - (ay + ah)
            frames.append(dict(img=sheet2ani.frame_key(fr), px=px, py=py, duration=240,  # v5: a frame lasts until the timer (speed per tick) passes 240
                               char=0, boxes=boxes, off=sheet2ani.frame_offset(fr)))
        if spec.get("align") and len(frames) > 1:
            xs = sheet2ani.align_x([cut[f["img"]][0] for f in frames], [(f["px"], f["py"]) for f in frames])
            for f, px in zip(frames, xs):
                f["px"] = px
        if slot == ROLL_SLOT:  # the own rolling curl: on the ground line of its (jump) boxes
            on_ground(frames)
        offset(frames)
        # (its "s3k_rot": a rotation style for S3&K too, 1 full: Honey's spin, drawn leaning by the DLL; "rot" stays
        # Sonic 1/2 / CD only, as before)
        anims.append(dict(name=spec["name"], speed=spec.get("speed", 60), loop=spec.get("loop", 0),
                          rot=spec.get("s3k_rot", 0), frames=frames))

    heads = cfg.get("copy_heads")
    if heads:  # the copy heads (COPY_HEADS_S3K): copies with each frame's picture swapped, the same timing and boxes
        if extra["base"] != "sonic" or not ab.ABILITIES.get(extra_id, {}).get("copy_heads"):
            sys.exit(f"{name}: copy_heads needs a Sonic-based extra with abilities.py copy_heads")
        while len(anims) < first + COPY_HEAD_OFFSET:
            anims.append(dict(name="(unused)", speed=0, loop=0, rot=0, frames=[]))
        by_name = {a["name"]: a for a in anims[:first]}
        for m, swap in enumerate(heads["swap"]):
            for n in COPY_HEADS_S3K:
                a = anims[first + ABILITY_SLOTS["43"]] if n == "shot" else by_name[n]
                frames = []
                for f in a["frames"]:
                    key = f["img"] if isinstance(f["img"], str) else json.dumps(list(f["img"]))
                    new = swap.get(key)
                    if new is None:
                        frames.append(dict(f))
                        continue
                    (_, (oax, oay, _, _)), (_, (nax, nay, _, _)) = cut[f["img"]], frame_image(new)
                    frames.append(dict(f, img=sheet2ani.frame_key(new), px=f["px"] - (nax - oax),
                                       py=f["py"] - (nay - oay)))
                anims.append(dict(a, name=f"{a['name']} (head {m + 1})", frames=frames))

    # One sheet (S3&K's own player sheet is a single 512-wide image)
    keys = list(cut)
    placed = {}
    x, y, shelf = 1, 1, 0
    for k in sorted(keys, key=lambda k: -cut[k][0].height):
        img = cut[k][0]
        if x + img.width + 1 > 512:
            x, y, shelf = 1, y + shelf + 1, 0
        placed[k] = (x, y)
        x += img.width + 1
        shelf = max(shelf, img.height)
    height = y + shelf + 1
    if height > MAX_SHEET_HEIGHT:
        sys.exit(f"{name}: S3&K sheet 512x{height}, more than the game's own largest (512x{MAX_SHEET_HEIGHT})")
    sheet = Image.new("P", (512, height), 0)
    pal = list(tpl_pal) + [0] * (768 - len(tpl_pal))
    for s, c in cfg.get("palette", {}).items():
        pal[3 * int(s):3 * int(s) + 3] = sheet2ani.hexrgb(c)
    sheet.putpalette(pal)
    for k, (px, py) in placed.items():
        sheet.paste(cut[k][0], (px, py))
    sheet_rel = "3K_Players/Extra.gif"  # (fixed names: extras.S3K_FIXED)
    own = s3k_build(extra)
    (own / "3K_Players").mkdir(parents=True, exist_ok=True)
    save_sheet(sheet, own / sheet_rel)

    for a in anims:
        for f in a["frames"]:
            img = cut[f["img"]][0]
            f.update(sheet=0, x=placed[f["img"]][0], y=placed[f["img"]][1], w=img.width, h=img.height)
            if f.pop("blank", False):
                f.update(x=0, y=0, w=0, h=0, px=0, py=0)
            del f["img"]
    ani_v5.write_bin(own / "3K_Players" / "Extra.bin",
                     dict(sheets=[sheet_rel], hitboxes=["Outer Box", "Inner Box"], anims=anims))
    print(f"{extra['art'].name} Extra.bin ({name}): {sum(len(a['frames']) for a in anims)} frames, sheet 512x{height}")
    build_menu_frame(extra, sheet, anims[0]["frames"][0])
    curl = extra["roll"] and not __import__("extras").no_stomp(extra)  # (no_stomp: "Rolling" is his slide, not a ball)
    ball = "Rolling" if curl else "Jump"  # the spin ball (extras.ball_animation)
    if curl:
        ball_frames = next(a for a in anims if a["name"] == ball)["frames"]
    else:  # the jump's own frames, not the base's count of them
        ball_frames = [dict(f, x=placed[f["img"]][0], y=placed[f["img"]][1], w=cut[f["img"]][0].width,
                            h=cut[f["img"]][0].height) for f in natural["Jump"]]
        offset(ball_frames)
    build_special(extra, sheet, ball_frames)


def menu_palette():
    """Bank 0 colours the data select (stage 3K_Menu) loads: slot -> RGB. The menu uses the slots the
    extras' own colours live in during play (64-95: Amy's), so its art must stick to these."""
    import struct
    d = (S3K.parent / "Stages" / "3K_Menu" / "StageConfig.bin").read_bytes()
    p = 5
    n = d[p]
    p += 1
    for _ in range(n):
        p += 1 + d[p]
    colours = {}
    for bank in range(8):
        mask = struct.unpack_from("<H", d, p)[0]
        p += 2
        for r in range(16):
            if mask & (1 << r):
                for i in range(16):
                    if bank == 0:
                        colours[r * 16 + i] = tuple(d[p + i * 3:p + i * 3 + 3])
                p += 48
    return {i: c for i, c in colours.items() if c != (255, 0, 255) and i != 0}


def build_menu_frame(extra, sheet, frame):
    """The extra's standing frame for the save menu (extras.S3K_MENU_PICTURE: 3K_Players/MenuPicture.bin / .gif, in
    s3k_build(extra)), recoloured to the nearest of the menu's own colours."""
    pal = sheet.getpalette()
    menu = menu_palette()
    img = sheet.crop((frame["x"], frame["y"], frame["x"] + frame["w"], frame["y"] + frame["h"]))
    lut = {}
    for _, i in img.getcolors(256):
        if i:
            c = tuple(pal[3 * i:3 * i + 3])
            lut[i] = min(menu, key=lambda k: sum((a - b) ** 2 for a, b in zip(c, menu[k])))
    img = img.point(lambda i: lut.get(i, 0))
    out = Image.new("P", (img.width + 2, img.height + 2), 0)
    full = [0] * 768
    for k, c in menu.items():
        full[3 * k:3 * k + 3] = c
    out.putpalette(full)
    out.paste(img, (1, 1))
    bin_rel, rel = S3K_MENU_PICTURE  # (the DLL renames the sheet per session: extras.S3K_MENU_PICTURE)
    own = s3k_build(extra)
    (own / "3K_Players").mkdir(parents=True, exist_ok=True)
    save_sheet(out, own / rel)
    f = dict(frame, sheet=0, x=1, y=1)
    # the save menu only sets the frame number, per the slot's character (Sonic's slot is 0, but extras
    # built on Tails or Knuckles sit in theirs): the same picture in every frame
    ani_v5.write_bin(own / bin_rel,
                     dict(sheets=[rel], hitboxes=["Outer Box", "Inner Box"],
                          anims=[dict(name="Idle", speed=0, loop=0, rot=0, frames=[dict(f) for _ in range(8)])]))


# The Blue Spheres stage's runner files (S3K_SS_Player loads all of them), per extras.py "base"
SPECIAL_FILE = {"sonic": "Sonic", "knuckles": "Knuckles", "tails": "Tails"}
# Bank 0 slots the extras' special-stage colours go in. The stage's colours above 127 come from its
# Stages/3K_Special/16x16Tiles.gif (the engine fills palette rows no config sets from it), where these are
# unused (magenta); no sheet the stage draws (3K_Special, 3K_Global, Global) uses them, and its own palette
# code only writes 128-162 and 208-211. The NoSwap DLL writes the colours (from the package's noswap_character.json:
# gen_s3k_header.s3k_json).
# 191 is the one other unused slot there; it comes last, so only a ball with 24 colours reaches it.
SPECIAL_SLOTS = list(range(216, 224)) + list(range(240, 255)) + [191]


def pow2(n):
    return 1 << max(0, n - 1).bit_length()


# The stage's own palette slots above 127 that nothing rewrites while it runs (its palette code writes 128-162 and
# 208-211; the runners' colours are in 163-207): a ball with more colours than SPECIAL_SLOTS draws the colours the
# stage already has (the same RGB) with the stage's own slots, so only the rest need SPECIAL_SLOTS (Gamma's jump
# pose has 31 colours; 10 of them are the stage's).
STAGE_STATIC_SLOTS = [s for s in range(163, 256) if not 208 <= s <= 211 and s not in SPECIAL_SLOTS]


def stage_colour_slots(used, pal):
    """Sheet index -> a stage slot holding exactly its colour (STAGE_STATIC_SLOTS), for the indices that have one."""
    tiles = Image.open(S3K.parent / "Stages" / "3K_Special" / "16x16Tiles.gif").getpalette()
    have = {}
    for s in STAGE_STATIC_SLOTS:
        have.setdefault(tuple(tiles[3 * s:3 * s + 3]), s)
    have.pop((255, 0, 255), None)  # magenta: unused
    return {i: have[tuple(pal[3 * i:3 * i + 3])] for i in used if tuple(pal[3 * i:3 * i + 3]) in have}


def build_special(extra, sheet, jump):
    """3K_Special/Extra.bin for the Blue Spheres stage, which shows the player from behind: the extras'
    sheets have no back views, so they roll through as their own spin ball (their S3&K jump frames, or their
    own rolling curl for extras whose jump isn't a ball, unchanged), as in the Sonic 2 and CD special stages. Every animation of the base's runner file keeps
    its name, frame count and timing; Tails' separate "Tail" gets empty frames (no twin tails). The ball's
    colours move to SPECIAL_SLOTS (same RGB; a ball with more colours than those uses the stage's own slots for
    the colours it has: stage_colour_slots), on a small sheet only the extra's special stage loads."""
    name, own = extra["file"], s3k_build(extra)
    tpl = ani_v5.read_bin(S3K / "3K_Special" / f"{SPECIAL_FILE[extra['base']]}.bin")
    pal = sheet.getpalette()
    crops, rects, x = {}, [], 1  # (0, 0) stays transparent: the empty frames
    for f in jump:
        key = (f["x"], f["y"], f["w"], f["h"])
        if key not in crops:
            crops[key] = (sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])), x)
            x += f["w"] + 1
        box = crops[key][0].getbbox()
        rects.append((crops[key][1], 1, f["w"], f["h"], box[3] if box else f["h"]))
    used = sorted({i for img, _ in crops.values() for _, i in img.getcolors(256)} - {0})
    slot = {}
    if len(used) > len(SPECIAL_SLOTS):  # (only then, so the balls that fit stay as they were built)
        slot = stage_colour_slots(used, pal)
    rest = [i for i in used if i not in slot]
    if len(rest) > len(SPECIAL_SLOTS):
        sys.exit(f"{name}: {len(rest)} ball colours the stage doesn't have, it has room for {len(SPECIAL_SLOTS)}")
    slot.update(zip(rest, SPECIAL_SLOTS))
    # the engine keeps sheets at power-of-two sizes (see build_sonic2.special_ball)
    out = Image.new("P", (pow2(x), pow2(max(img.height for img, _ in crops.values()) + 2)), 0)
    out_pal = Image.open(S3K / "3K_Special" / "Objects.gif").getpalette()  # the stage's colours, for viewing
    for i, s in slot.items():
        out_pal[3 * s:3 * s + 3] = pal[3 * i:3 * i + 3]
    out.putpalette(out_pal)
    for img, px in crops.values():
        out.paste(img.point(lambda i: slot.get(i, 0)), (px, 1))
    sheet_rel = "3K_Special/NoSwap_Extra.gif"  # (fixed names: extras.S3K_FIXED)
    (own / "3K_Special").mkdir(parents=True, exist_ok=True)
    save_sheet(out, own / sheet_rel)

    idle = tpl["anims"][0]["frames"][0]
    feet = idle["py"] + idle["h"]  # the runner's feet (Idle and Run stand on the same line)
    ball = next(a for a in tpl["anims"] if a["name"] == "Jump")["frames"][0]
    middle = ball["py"] + ball["h"] // 2  # the centre of the runner's own jump ball
    # the jump and bounce balls sit on one line, whatever their size: where a Sonic-sized (30 px) ball centred on
    # the runner's own ends, so the 30 px balls stay put and smaller ones don't float (nor bigger ones sink)
    # (sheet2ani.put_on_ground: the frames move together, by their median bottom)
    lift = statistics.median_low([(middle - h // 2 + b) - (middle + 15) for _, _, _, h, b in rects])
    anims = []
    for a in tpl["anims"]:
        frames = []
        for k, tf in enumerate(a["frames"]):
            f = dict(tf, sheet=0)
            if a["name"] == "Tail":
                f.update(x=0, y=0, w=1, h=1, px=0, py=0)
            else:
                bx, by, w, h, _ = rects[k % len(rects)]  # spinning through the frames
                py = middle - h // 2 - lift if a["name"] in ("Jump", "Bounce") else feet - h
                f.update(x=bx, y=by, w=w, h=h, px=-(w // 2), py=py)
            frames.append(f)
        anims.append(dict(a, frames=frames))
    ani_v5.write_bin(own / "3K_Special" / "Extra.bin", dict(sheets=[sheet_rel], hitboxes=tpl["hitboxes"], anims=anims))


def special_colours(extra):
    """The extra's special-stage colours, slot -> RGB (0xRRGGBB), from its built sheet: what the DLL writes (its
    package's noswap_character.json, gen_s3k_header.s3k_json)."""
    path = s3k_build(extra) / "3K_Special" / "NoSwap_Extra.gif"
    if not path.exists():
        return {}
    img = Image.open(path)
    pal = img.getpalette()
    return {i: (pal[3 * i] << 16) | (pal[3 * i + 1] << 8) | pal[3 * i + 2]
            for _, i in img.getcolors(256) if i in SPECIAL_SLOTS}


def build_no_tail():
    """3K_Players/NoTail.bin: Tails' tail sprite file with every frame a single transparent pixel. The
    DLL loads it instead of TailSprite.bin for extras built on Tails (Charmy has no twin tails)."""
    tails = ani_v5.read_bin(S3K / "3K_Players" / "TailSprite.bin")
    sheet = Image.new("P", (4, 4), 0)
    sheet.putpalette(Image.open(S3K / tails["sheets"][0]).getpalette())
    (OUT / "3K_Players").mkdir(parents=True, exist_ok=True)  # (the Creator Kit's fresh work tree has no such folder yet)
    save_sheet(sheet, OUT / "3K_Players" / "NoTail.gif")
    tails["sheets"] = ["3K_Players/NoTail.gif"]
    for a in tails["anims"]:
        for f in a["frames"]:
            f.update(sheet=0, x=0, y=0, w=1, h=1)
    ani_v5.write_bin(OUT / "3K_Players" / "NoTail.bin", tails)


# NoSwap's placeholders for the fixed names (extras.S3K_FIXED): the game's own file for each .bin (an extra whose package
# lacks one gets Sonic's, or the game's HUD / signpost / runner), and a blank 4x4 sheet in the colours of the game's
# sheet it stands for (only there so that each package's own sheet of that name can be served: the redirect only serves
# names NoSwap ships)
PLACEHOLDERS = {"3K_Players/Extra.bin": "3K_Players/Sonic.bin", "3K_Players/Extra.gif": "3K_Players/Sonic.gif",
                "3K_Special/Extra.bin": "3K_Special/Sonic.bin", "3K_Special/NoSwap_Extra.gif": "3K_Special/Objects.gif",
                "3K_Global/HUD_Extra.bin": "3K_Global/HUD.bin", "3K_Global/HUD_Extra.gif": "3K_Global/Display.gif",
                "3K_Global/SignPost_Extra.bin": "3K_Global/SignPost.bin",
                "3K_Global/SignPost_Extra.gif": "3K_Global/Objects2.gif",
                "3K_HPZ/SpecialClear_Extra.bin": "3K_HPZ/SpecialClear.bin",
                "3K_HPZ/SpecialClear_Extra.gif": "3K_HPZ/Objects.gif"}


def write_placeholders(out=OUT):
    assert sorted(PLACEHOLDERS) == sorted(S3K_FIXED)
    for rel, game in PLACEHOLDERS.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".bin"):
            (out / rel).write_bytes((S3K / game).read_bytes())
        else:
            sheet = Image.new("P", (4, 4), 0)
            sheet.putpalette(Image.open(S3K / game).getpalette())
            save_sheet(sheet, out / rel)


def write_menu_placeholders(out=OUT):
    """NoSwap's numbered save screen picture names (extras.menu_picture): a .bin naming its own blank 4x4 sheet in the
    menu's colours, the same picture in all 8 frames. Only there so the DLL can serve each extra's picture under them
    (the redirect only serves names NoSwap ships); the DLL never loads one it hasn't given an extra."""
    menu = menu_palette()
    full = [0] * 768
    for k, c in menu.items():
        full[3 * k:3 * k + 3] = c
    for j in range(S3K_MENU_PICTURES):
        bin_rel, rel = menu_picture(j)
        sheet = Image.new("P", (4, 4), 0)
        sheet.putpalette(full)
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        save_sheet(sheet, out / rel)
        f = dict(sheet=0, duration=0, char=0, x=0, y=0, w=1, h=1, px=0, py=0, boxes=[(0, 0, 0, 0)] * 2)
        ani_v5.write_bin(out / bin_rel, dict(sheets=[rel], hitboxes=["Outer Box", "Inner Box"],
                                             anims=[dict(name="Idle", speed=0, loop=0, rot=0,
                                                         frames=[dict(f) for _ in range(8)])]))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(p)
    if any(e["base"] == "tails" for e in EXTRAS):
        build_no_tail()
