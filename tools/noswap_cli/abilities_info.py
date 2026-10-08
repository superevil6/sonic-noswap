"""What the pipeline knows about moves, read from the code itself (no list to keep in step by hand):

- module names: tools/abilities.py's docstring (its "Available modules" list) plus every name a character uses;
- field names: every key some character's ABILITIES entry has, plus every key the builders read with .get("...");
- field types: the Python types those keys have across the existing characters;
- per-game support: the S3&K field names (gen_s3k_header.ability_fields) and whether native/src (the S3&K DLL) and
  native/mania/src (the Mania mod) have code that reads them.
"""
import re
from functools import lru_cache

from .model import REPO, TOOLS

# The ability animation slots each move draws (tools/abilities.py's docstring; 41 attack, 42 hover, 43 / 44 the Y move,
# 45 / 46 aimed up / down, 47 / 48 glide up / down or cling, 49 roll, 50-52 Power Surge)
SLOTS = {
    "jet_dash": ["41"], "hover": ["42"], "pogo": ["41"], "umbrella": ["42"], "chaos_control": ["41"],
    "aim_dash": ["41", "45", "46"], "hammer_drop": ["41"], "ray_glide": ["42", "47", "48"], "melee": ["43"],
    "spirit_flight": ["41"], "triple_jump": ["41"], "screw_kick": ["41"], "double_jump": ["41"], "wall_cling": ["47"],
    "thunder_zip": ["41"], "power_surge": ["50", "51", "52"], "extreme_gear": ["41"], "puddle_slide": ["41", "42"],
    "ground_slide": ["42"], "rocket_ride": ["41"], "ear_grapple": ["41"], "phase_warp": ["41"], "rocket_burst": ["41"],
    "spin_attack": ["41", "43"], "charge": ["41", "43", "44"], "high_kick": ["42", "43"],
    "ninjutsu": ["42", "48"],  # (Joe Musashi's: the cast pose, Mijin's; tools/ninjutsu.py)
    "pot_magic": ["42", "45", "46", "47", "48"],  # (Gilius': the cast pose, the boulders, bursts, the pot; tools/pot_magic.py)
}
SLOT_MEANING = {"41": "the jump ability (an attack)", "42": "hover / glide", "43": "the Y move on the ground",
                "44": "the Y move in the air", "45": "aimed up", "46": "aimed down", "47": "glide up / cling / swim",
                "48": "glide down", "49": "rolling", "50": "Power Surge idle", "51": "Power Surge walk",
                "52": "Power Surge run"}
TOOL_FILES = ["abilities.py", "gen_s3k_header.py", "build_soniccd.py", "build_s3k_art.py", "build_mania_art.py",
              "shots_v3.py", "shots_v4.py", "build_s3k_shot.py", "star_grab.py", "head_throw.py", "anchor_throw.py",
              "water_walk.py", "treasure_sense.py", "monitor_swap.py", "psycho_grab.py", "free_swim.py", "free_flight.py", "voltteccer.py", "ninjutsu.py", "pot_magic.py", "fire_dash.py",
              "surfride.py", "noswap_common.py"]


@lru_cache(None)
def abilities_module():
    import abilities
    return abilities


@lru_cache(None)
def modules():
    ab = abilities_module()
    names = set(re.findall(r"^  (\w+)\s", ab.__doc__, re.M))
    for e in ab.ABILITIES.values():
        names |= set(e.get("abilities", []))
        names |= set(e.get("ability_cycle", []))
    return names


@lru_cache(None)
def fields():
    """{field: set of type names seen} for every known ABILITIES key."""
    ab = abilities_module()
    seen = {}
    for e in ab.ABILITIES.values():
        for k, v in e.items():
            seen.setdefault(k, set()).add(type(v).__name__)
    for f in TOOL_FILES:
        p = TOOLS / f
        if p.exists():
            for k in re.findall(r"""\.get\(\s*["'](\w+)["']""", p.read_text()):
                seen.setdefault(k, set())
    return seen


@lru_cache(None)
def native_words(sub):
    import os
    snap = REPO / "data" / "kit" / "native_words.json"  # (the Creator Kit: no native code; tools/make_kit.py's list)
    if os.environ.get("NOSWAP_KIT") and snap.is_file():
        import json
        return set(json.loads(snap.read_text()).get(sub, []))
    words = set()
    root = REPO / sub
    for p in list(root.glob("*.h")) + list(root.glob("*.c")) + list(root.glob("*.cpp")):
        words |= set(re.findall(r"\b\w+\b", p.read_text(errors="replace")))
    return words


def s3k_fields(entry, who):
    """[(name, value, default)] of the S3&K fields this entry sets away from their defaults, or raises SystemExit (the
    generator's own limit errors)."""
    import gen_s3k_header as g
    defaults = {name: value for _, name, _, value in g.DEFAULTS}
    return [(name, value, defaults.get(name)) for _, name, _, value in g.ability_fields(entry, who)
            if value != defaults.get(name)]
