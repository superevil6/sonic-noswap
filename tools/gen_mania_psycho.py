#!/usr/bin/env python3
"""Write native/mania/src/ManiaPsychoTable.h: the badniks Silver's Psychokinesis can catch in Sonic Mania, and where
each one keeps the Animators its Draw shows (his carried / thrown likeness draws them, in that order, at its position).

The offsets come from the decompilation's own headers (compile only, nothing is run): a small C file includes the
decomp's Game.h and puts offsetof(EntityX, part) for every part in a constant table; gcc -c builds it, objcopy takes
the table out of .rodata, and this script reads it (as native/mania/check_layout.sh checks the Player's layout).

The list (the user's rule, as in Sonic 1/2, CD and S3&K): single-object badniks only. Left out: bosses and their
parts; multi-part or orbiting enemies (Caterkiller, CaterkillerJr, Fireworm, Hatterkiller, Rattlekiller, Rexon,
Orbinaut, Tubinaut, Sol, SentryBug, Kabasira, Dragonfly, Hotaru's pairs, PohBee's chain, MonkeyDude's arm,
Armadiloid's rider, FBZTrash); ones that grab the player (Grabber, Jellygnite, MegaChopper, Scarab, Toxomister's
cloud); breakables that aren't badniks (Mine, Pinata, FlowerPod, TurretSwitch, DoorTrigger, ItemBox).

Usage: gen_mania_psycho.py   (DECOMP_DIR: the decomp checkout, default ~/Code/mania/Sonic-Mania-Decompilation)
"""
import os
import struct
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DECOMP = Path(os.environ.get("DECOMP_DIR", Path.home() / "Code" / "mania" / "Sonic-Mania-Decompilation"))
OUT = REPO / "native" / "mania" / "src" / "ManiaPsychoTable.h"

# class -> its Draw's parts at its own position, in draw order ("~": drawn with INK_ALPHA, the entity's alpha). Parts
# drawn elsewhere or only now and then (dust, splashes, jets, flames, bombs, a saw on its arm) are left out.
CATCHABLE = {
    "Aquis": ["mainAnimator", "wingAnimator"],
    "BallHog": ["animator"],
    "Batbot": ["bodyAnimator"],
    "Batbrain": ["animator"],
    "Blaster": ["animator"],
    "Blastoid": ["animator"],
    "Bloominator": ["animator"],
    "Bubbler": ["bodyHitbox"],  # (the decomp's name for its body Animator)
    "Buggernaut": ["bodyAnimator", "~wingAnimator"],
    "Bumpalo": ["badnikAnimator", "huffAnimator"],
    "BuzzBomber": ["animator", "~wingAnimator", "thrustAnimator"],
    "Cactula": ["bodyBottomAnimator", "propellerAnimator", "bodyTopAnimator"],
    "Canista": ["mainAnimator", "tapeAnimator", "cannonAnimator"],
    "Chopper": ["animator"],
    "Clucker": ["animator"],
    "Crabmeat": ["animator"],
    "Dango": ["animator"],
    "FlasherMKII": ["animator"],
    "HotaruMKII": ["mainAnimator"],
    "IceBomba": ["bodyAnimator", "~wingAnimator"],
    "Jawz": ["animator"],
    "JuggleSaw": ["animator"],
    "Kanabun": ["animator"],
    "MechaBu": ["badnikAnimator", "hornAnimator"],
    "MicDrop": ["bodyAnimator"],
    "Motobug": ["animator"],
    "Newtron": ["animator"],
    "Octus": ["animator"],
    "Pointdexter": ["animator"],
    "Redz": ["animator"],
    "Rhinobot": ["bodyAnimator"],
    "RollerMKII": ["animator"],
    "Shutterbug": ["animator"],
    "Spiny": ["animator"],
    "Splats": ["mainAnimator"],
    "Stegway": ["mainAnimator", "wheelAnimator"],
    "Sweep": ["animator"],
    "Technosqueek": ["animator"],
    "TurboSpiker": ["shellAnimator", "animator"],
    "TurboTurtle": ["animator"],
    "Vultron": ["bodyAnimator"],
    "WallCrawl": ["animator"],
    "Wisp": ["bodyAnimator", "~wingAnimator"],
    "Woodrow": ["animator"],
}
PARTS_MAX = 3
DEFS = ["-DRETRO_REVISION=3", "-DRETRO_USE_MOD_LOADER=1", "-DRETRO_MOD_LOADER_VER=2", "-DGAME_VERSION=6",
        "-DGAME_INCLUDE_EDITOR=1", "-DMANIA_PREPLUS=0", "-DMANIA_FIRST_RELEASE=0"]


def main():
    fields = ["sizeof(Animator)", "sizeof(Entity)"]
    for cls, parts in CATCHABLE.items():
        assert 1 <= len(parts) <= PARTS_MAX, cls
        fields += [f"sizeof(Entity{cls})"] + [f"offsetof(Entity{cls}, {p.lstrip('~')})" for p in parts]
    src = '#include "Game.h"\n#include <stddef.h>\nconst unsigned int table[] = {\n' + ",\n".join(fields) + "\n};\n"
    with tempfile.TemporaryDirectory() as tmp:
        c, o, b = Path(tmp) / "t.c", Path(tmp) / "t.o", Path(tmp) / "t.bin"
        c.write_text(src)
        subprocess.run(["gcc", "-c", "-w", *DEFS, f"-I{DECOMP / 'SonicMania'}", f"-I{DECOMP / 'SonicMania' / 'Objects'}",
                        str(c), "-o", str(o)], check=True)
        subprocess.run(["objcopy", "-O", "binary", "-j", ".rodata", str(o), str(b)], check=True)
        data = b.read_bytes()
    values = list(struct.unpack(f"<{len(fields)}I", data[:4 * len(fields)]))
    anim_size, entity_size = values[0], values[1]
    k = 2
    rows = []
    for cls, parts in CATCHABLE.items():
        size = values[k]
        offs = values[k + 1:k + 1 + len(parts)]
        k += 1 + len(parts)
        for p, off in zip(parts, offs):
            assert entity_size <= off and off + anim_size <= size, (cls, p, off, size)
        alpha = sum(1 << i for i, p in enumerate(parts) if p.startswith("~"))
        cells = ", ".join(str(x) for x in list(offs) + [0] * (PARTS_MAX - len(parts)))
        rows.append(f'    {{ "{cls}", {len(parts)}, {{ {cells} }}, 0x{alpha:X} }}, // {", ".join(parts)}')
    OUT.write_text(f"""// GENERATED by tools/gen_mania_psycho.py from the Sonic Mania decompilation's headers: do not edit.
// The badniks Silver's Psychokinesis can catch in Mania, and the offsets of the Animators their Draw shows at their own
// position, in draw order (alpha: a bit per part drawn with INK_ALPHA). Animator size {anim_size}, Entity size {entity_size}.
#ifndef MANIA_PSYCHO_TABLE_H
#define MANIA_PSYCHO_TABLE_H

#define PSYCHO_PARTS_MAX     ({PARTS_MAX})
#define PSYCHO_ANIMATOR_SIZE ({anim_size})

typedef struct {{
    const char *name;
    uint8 count;
    uint16 offset[PSYCHO_PARTS_MAX];
    uint8 alpha;
}} PsychoClass;

static const PsychoClass PSYCHO_CLASSES[] = {{
{chr(10).join(rows)}
}};
#define PSYCHO_CLASS_COUNT (sizeof(PSYCHO_CLASSES) / sizeof(PSYCHO_CLASSES[0]))

#endif // MANIA_PSYCHO_TABLE_H
""")
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} catchable classes (Animator {anim_size} bytes)")


if __name__ == "__main__":
    main()
