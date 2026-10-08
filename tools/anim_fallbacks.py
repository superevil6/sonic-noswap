"""Fallback frames for a character.json character: an animation the character gives no frames for borrows a similar
one they do have, instead of the game showing nothing there (docs/character-json.md, "Fallback frames").

Each base animation (Sonic 1 / Sonic 2's names, which every other game is built from) has an ordered chain of
candidates; the first one the character has frames for is used. The fallback copies the source's frames and its
anchor (and "align"); the target keeps its own speed, loop, rotation and hitbox from the base's template. Chains only
name animations the character drew themselves (own frames), so a fallback never borrows another fallback, and every
chain ends in a pose everyone has (Stopped, Walking, Hurt, Jumping).

Where the other games differ, their own builders already map onto these names: Sonic CD (tools/cd_config.py
RENAMED / STAND_INS: 3D Ramps, Spinning Top...) and S3&K / Mania (tools/build_s3k_art.py FROM_S2, build_mania_art's
Air Walk) read the Sonic 2 config, so they get the filled-in set too. ("Air Walk", "Victory", "Bored 1", "Ducking" and
"Rolling" in the plans are S3&K / Mania names: on Sonic 1 / 2's lists their closest are Bouncing, Continue Up, Waiting,
Looking Down and NoSwap's ability slot 49 "Rolling".)

Opting out: `"Pushing": null` in the character's animations means "deliberately empty": no fallback.

The chains follow what the hand-made characters (make_configs.py) reuse when their sheets lack a pose: e.g. 15 use
their Waiting for Bored!, 21 Bouncing for Hanging, 22 Hanging = Clinging On, 25 Hurt for Grabbed, 29 Running for Super
Peel Out, 41 Corkscrew H = Twirl H, 14 Dying = Drowning, 10 Bouncing for Breathing, 18 Stopped for Super Transform.

Only character.json characters get fallbacks (tools/character_json.py, at config time); the make_configs.py ones are
untouched.
"""

# animation -> candidates, first that the character has frames for. "Rolling" is ability slot 49 (its own curl).
FALLBACKS = {
    # standing about
    "Waiting": ["Bored!", "Stopped"],
    "Bored!": ["Waiting", "Stopped"],
    "Looking Up": ["Continue Up", "Stopped"],
    "Looking Down": ["Spin Dash", "Stopped"],
    "Skidding": ["Looking Down", "Stopped"],
    "Super Transform": ["Continue Up", "Looking Up", "Stopped"],  # (S3&K / Mania's Victory: Continue Up, arms up)
    "Continue": ["Waiting", "Bored!", "Stopped"],
    "Continue Up": ["Looking Up", "Bouncing", "Stopped"],
    # on the move
    "Walking": ["Running", "Stopped"],
    "Running": ["Walking", "Stopped"],
    "Super Peel Out": ["Running", "Walking"],
    "Pushing": ["Walking", "Stopped"],
    "Fan Rotate": ["Twirl H", "Corkscrew H", "Walking"],
    "Corkscrew H": ["Twirl H", "Walking"],
    "Twirl H": ["Corkscrew H", "Walking"],
    "Water Slide": ["Sliding", "Looking Down", "Stopped"],
    "Sliding": ["Water Slide", "Looking Down", "Stopped"],
    # balls
    "Jumping": ["Rolling", "Spin Dash"],
    "Spin Dash": ["Rolling", "Jumping"],
    # in the air, hanging on
    "Bouncing": ["Continue Up", "Hanging", "Jumping"],
    "Breathing": ["Bouncing", "Jumping"],  # (Mania's Air Walk is Bouncing's place here)
    "Hanging": ["Clinging On", "Bouncing", "Stopped"],
    "Clinging On": ["Hanging", "Bouncing", "Stopped"],
    "Flailing 1": ["Flailing 2", "Flailing 3", "Hurt"],
    "Flailing 2": ["Flailing 1", "Flailing 3", "Hurt"],
    "Flailing 3": ["Flailing 2", "Flailing 1", "Hurt"],
    # hit
    "Hurt": ["Grabbed", "Dying", "Stopped"],
    "Grabbed": ["Hurt"],
    "Grabbing": ["Grabbed", "Hurt"],
    "Dying": ["Drowning", "Hurt"],
    "Drowning": ["Dying", "Hurt"],
    # Tails' own (a Tails-based character)
    "Flying": ["Fly Lift Up", "Swimming", "Bouncing"],
    "Flying Tired": ["Fly Lift Tired", "Swimming Tired", "Flying", "Bouncing"],
    "Swimming": ["Swim Lift", "Flying", "Bouncing"],
    "Swimming Tired": ["Flying Tired", "Swimming", "Flying", "Bouncing"],
    "Fly Lift Up": ["Flying", "Bouncing"],
    "Fly Lift Down": ["Flying", "Bouncing"],
    "Fly Lift Tired": ["Flying Tired", "Flying", "Bouncing"],
    "Swim Lift": ["Swimming", "Flying", "Bouncing"],
    # Knuckles' own (a Knuckles-based character)
    "Gliding": ["Bouncing", "Jumping"],
    "Gliding Drop": ["Jumping"],
    "Gliding Stop": ["Looking Down", "Stopped"],
    "Dropping": ["Gliding Drop", "Jumping"],
    "Climbing": ["Clinging On", "Hanging", "Stopped"],
    "Ledge Pull Up": ["Climbing", "Clinging On", "Stopped"],
}
# Sonic 1's special stage (its own SonicSS.ani): the ball, centred. The whole source is copied (its speed too), as the
# special stage always did with Jumping.
SPECIAL_FALLBACKS = {"Special Stage": ["Jumping", "Rolling", "Spin Dash"]}
# what a fallback copies from its source
COPIED = ("anchor", "align")


def has_frames(a):
    return isinstance(a, dict) and bool(a.get("frames"))


def pool(*sections, appended=None):
    """The animations a fallback may borrow: every given one with frames (later sections win), plus ability slot 49
    as "Rolling"."""
    out = {}
    for sec in sections:
        out.update({k: v for k, v in (sec or {}).items() if has_frames(v)})
    roll = (appended or {}).get("49")
    if has_frames(roll) and "Rolling" not in out:
        out["Rolling"] = roll
    return out


def source(name, have, table=FALLBACKS):
    """The first candidate of name's chain that is in `have`, or None."""
    return next((s for s in table.get(name, ()) if s in have), None)


def fill(animations, needed, have, empty=(), table=FALLBACKS):
    """Fallbacks for the `needed` names (the base's filled list) that `animations` has no frames for.
    Returns (fallbacks {name: spec}, used {name: source}, unresolved [name]). `empty`: names opted out (null)."""
    out, used, lost = {}, {}, []
    for name in needed:
        if has_frames(animations.get(name)) or name in empty:
            continue
        src = source(name, have, table)
        if src is None:
            lost.append(name)
            continue
        a = have[src]
        spec = {"frames": list(a["frames"])}
        spec.update({k: a[k] for k in COPIED if k in a})
        out[name], used[name] = spec, src
    return out, used, lost


def fill_special(special, have, empty=()):
    """Sonic 1's special stage: (fallbacks, used, unresolved), the source copied whole and centred."""
    out, used, lost = {}, {}, []
    for name, chain in SPECIAL_FALLBACKS.items():
        if has_frames(special.get(name)) or name in empty:
            continue
        src = next((s for s in chain if s in have), None)
        if src is None:
            lost.append(name)
            continue
        out[name], used[name] = dict(have[src], anchor="center"), src
    return out, used, lost


def opted_out(raw_section):
    """Names set to null (deliberately empty) in a raw character.json section."""
    return {k for k, v in (raw_section or {}).items() if v is None and not k.startswith("_")}


def plan(c, filled):
    """What the fallbacks come to for a cleaned character.json `c` (frames may be unresolved names: only "has frames"
    counts), without building: for the check and the editor. filled: {"Sonic1": [...], "Sonic2": [...]}, the base's
    filled lists (noswap_cli.templates). The generic ball ("ball" use_for) counts as frames where it goes.
    -> {"Sonic1": {"used": {name: source}, "lost": [...], "empty": [...]}, "Sonic2": {...},
        "special": {"used": {...}, "lost": [...], "empty": [...]}, "ball": [the animations the ball fills]}"""
    import generic_ball
    anims = lambda sec: {k: v for k, v in (c.get(sec) or {}).items() if isinstance(v, dict) and not k.startswith("_")}
    ball = c.get("ball") if isinstance(c.get("ball"), dict) else None
    use = list(ball.get("use_for", generic_ball.DEFAULT_USE_FOR)) if ball else []
    standin = {"frames": ["(generic ball)"], "anchor": "center"}
    appended = anims("ability_animations")
    if "Rolling" in use:
        appended["49"] = standin
    out = {"ball": use}
    s1_final = None
    for game in ("Sonic1", "Sonic2"):
        a = anims("animations")
        empty = opted_out(c.get("animations"))
        if game == "Sonic2":
            a.update(anims("animations_sonic2"))
            empty |= opted_out(c.get("animations_sonic2"))
            empty -= {n for n, v in a.items() if has_frames(v)}
        a.update({n: standin for n in ("Jumping", "Spin Dash") if n in use})
        have = pool(anims("animations"), anims("animations_sonic2"), a, appended=appended)
        made, used, lost = fill(a, filled[game], have, empty)
        out[game] = {"used": used, "lost": lost, "empty": sorted(empty)}
        if game == "Sonic1":
            s1_final = {**a, **made}
    special = anims("special_stage")
    if "Special Stage" in use:
        special["Special Stage"] = standin
    empty = opted_out(c.get("special_stage"))
    _, used, lost = fill_special(special, {n: v for n, v in s1_final.items() if has_frames(v)}, empty)
    out["special"] = {"used": used, "lost": lost, "empty": sorted(empty)}
    return out
