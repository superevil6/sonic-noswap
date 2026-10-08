#!/usr/bin/env python3
"""Make a Sonic CD sheet2ani config from an extra's Sonic 2 config.

Usage: cd_config.py <extra s2 config.json> [...]   (writes <name>_cd.json next to each)

CD's Sonic.ani (the template) differs from S1/S2's: two animations are renamed, and it has CD-only
animations the player script looks up by name (Spinning Top, 3D Ramp 1-7, Size Change). Those get the
extra's closest animation as a stand-in. CD's player palette slots 0-15 are the same as S1/S2's, so the
colour mapping carries over. Ability animations move to CD's free slots (S1/S2's 41-44 are CD's
3D Ramp 5-7 and Size Change here). A "cd_animations" key in the Sonic 2 config ({CD name: animation}) replaces
those animations in CD only (before the stand-ins copy them). Attack 41 -> 45 and the shot 43 -> 46 (CD's Amy hammer slots, which
enemies already treat as attacks), hover/umbrella 42 -> 47, the glide's up / down poses 47, 48 -> 48, 49 and an
own rolling curl (extras.py "roll") 49 -> 50, and the Power Surge idle / walk / run (abilities.py power_surge)
50-52 -> 51-53, and copy-head sets (53 on: Emerl's) one slot on. The air shot (44) isn't used in CD.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CD = REPO / "extracted" / "SonicCD" / "Data"

ABILITY_SLOTS = {"41": "45", "43": "46", "42": "47", "47": "48", "48": "49", "49": "50", "50": "51", "51": "52", "52": "53"}
COPY_HEAD_FIRST = 53  # S1/S2 slots from here on: copy-head sets, CD's one slot on (after the Power Surge's 51-53)
RENAMED = {"Flailing 1": "Flailing Left", "Flailing 2": "Flailing Right"}
STAND_INS = {  # CD-only animation -> the extra's animation to copy
    "Dropping": "Bouncing",
    "Launcher": "Running",
    "Spinning Top": "Jumping",
    **{f"3D Ramp {n}": "Running" for n in range(1, 7)},
    "3D Ramp 7": "Jumping",
    "Size Change": "Stopped",
    "Corkscrew H": "Walking",
}


def convert(path):
    cfg = json.loads(Path(path).read_text())
    anims = {RENAMED.get(k, k): v for k, v in cfg["animations"].items()}
    anims.update(cfg.pop("cd_animations", {}))  # (CD's own art for some, by CD's names: Sticks' ball is CD's Tails')
    knuckles_layout = "Knuckles.ani" in cfg["template_ani"]  # (before the template becomes CD's Sonic.ani)
    if knuckles_layout:  # Knuckles-style walk / run: upright frames, then pre-drawn
        for k in ("Walking", "Running"):  # 45-degree ones, which CD's Sonic template doesn't use
            if k in anims:
                anims[k] = dict(anims[k], frames=anims[k]["frames"][:len(anims[k]["frames"]) // 2])
    for cd_name, source in STAND_INS.items():
        if cd_name not in anims and source in anims:
            anims[cd_name] = dict(anims[source])
    # "hold" (sheet2ani) slows S1/S2 animations whose speed Sonic 1/2's script sets (Tails' flight); CD's timing differs
    anims = {k: {kk: vv for kk, vv in v.items() if kk != "hold"} for k, v in anims.items()}
    cfg.update(
        animations=anims,
        template_ani=str(CD / "Animations" / "Sonic.ani"),
        template_sheet=str(CD / "Sprites" / "Players" / "Sonic1.gif"),
        out_dir=str(REPO / "mods" / "NoSwap" / "SonicCDu"),
    )
    # ("cd_hitbox": the .ani hitbox CD uses instead of "hitbox": CD's Sonic.ani has only 3, S1/S2's a 4th, the low one
    # Mega Man's Slide takes there)
    appended = cfg.get("appended_animations", {})
    # melee_run / melee_up (abilities.py: Axel's Grand Upper and Dragon Wing, slots 45 / 46): CD has no slots for them,
    # so their frames follow the melee's own in its animation (43 -> 46, an attack there), in that order; the player
    # script shows the pose's part (build_soniccd.cd_variant_lines)
    variants = cfg.pop("cd_melee_variants", [])
    if variants:
        appended = dict(appended)
        parts = [appended["43"]] + [appended[k] for k in variants]
        if len({p.get("anchor", "feet") for p in parts}) > 1 or any(p.get("hold", 1) > 1 for p in parts):
            sys.exit(f"{path}: melee_run / melee_up's CD frames share the melee's animation: one anchor, no hold")
        # each pose aligned on its own first frame, as in its own slot elsewhere (one alignment over all of them
        # shifted the Grand Upper and the Dragon Wing sideways against the punch: sheet2ani "align" runs)
        appended["43"] = dict(appended["43"], frames=[f for p in parts for f in p["frames"]],
                              align=[[len(p["frames"]), bool(p.get("align"))] for p in parts])
        for k in variants:
            appended.pop(k)
    # copy-head sets (Emerl's, from COPY_HEAD_FIRST: testmods/emerl/make_configs.py) go one on, each unless it copies
    # an ability animation CD doesn't have (the air shot)
    dropped = {v["name"] for k, v in appended.items() if k not in ABILITY_SLOTS and int(k) < COPY_HEAD_FIRST}
    slot_of = lambda k: ABILITY_SLOTS.get(k) or (str(int(k) + 1) if int(k) >= COPY_HEAD_FIRST else None)
    cfg["appended_animations"] = {slot_of(k): (dict(v, hitbox=v["cd_hitbox"]) if "cd_hitbox" in v else v)
                                  for k, v in appended.items() if slot_of(k) and v.get("like") not in dropped}
    if knuckles_layout and "Gliding" in anims and "48" not in cfg["appended_animations"]:
        # CD's glide uses ANI_GLIDING, a fixed 48 (only Knuckles' own file has it; Sonic's ends at 44)
        cfg["appended_animations"]["48"] = dict(anims["Gliding"], name="Gliding", speed=0)  # the code picks its frame
    for key in ("extra_anis", "ui"):
        cfg.pop(key, None)
    out = Path(path).with_name(Path(path).stem.replace("_s2", "") + "_cd.json")
    out.write_text(json.dumps(cfg, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        convert(p)
