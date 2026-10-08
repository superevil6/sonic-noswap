"""Characters that exist ONLY in the Sonic Mania port (NoSwapMania), never in Origins.

tools/extras.py's EXTRAS is the Origins roster: every Origins builder (build_all.sh, build_packages.py, the S1/S2/CD/S3K
pipelines, the menu, make_release.py) reads it, so a character in it lands in Origins builds. A Mania-only character is
defined HERE instead, and only tools/build_mania_art.py (and build_mania_hud.py through it) reads this list: nothing on
the Origins side imports this module, so nothing here can reach an Origins build.

Each entry has the fields build_mania_art.py reads from an EXTRAS entry ("art" only for its folder name, "name", "key",
"n" = the save select order, "base", "super", "no_roll", "credit_short") plus "source", which says where its art comes
from instead of a sheet2ani config:
    "v5": an existing RSDKv5 player file (an S3&K-layout .bin + its sheet) mapped onto Mania's list by animation name
          (build_mania_art.build_v5_player), its UI pictures cut from official sprite files ("ui").

Amy Rose (the user, 2026-10-01): Mania has no Amy, Origins Plus has the real one, so she is Mania-only. Her art is
Origins Plus' own (SEGA): 3K_Players/Amy.bin / .gif, her HUD life icon, results continue icon and signpost face, read
from the extracted S3&K data (extracted/Sonic3K). Her moves are Origins' (native/mania/src/ManiaAmy.h).
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
S3K_SPRITES = REPO / "extracted" / "Sonic3K" / "Data" / "Sprites"

MANIA_ONLY = [
    {
        "art": Path("amy"),  # (only its name is used: the package folder, Data/Sprites/NoSwap/amy)
        "name": "AMY",
        "key": "noswap.amy",
        "n": 0,  # the save select: right after Mania's own five, before NoSwap's extras
        "base": "sonic",
        "super": False,  # (her own colours glow when Super: Origins has no Super Amy palette in its data files)
        "no_roll": False,
        "drop_dash": False,
        "credit_short": "Origins Plus",
        # her results name's colours in Mania (ui_accent.mania_name): her own pinks from her palette, light to dark
        # (Origins Plus' S3&K results draw AMY in pink)
        "ui_accent": ["#FCB4FC", "#FC6CFC", "#B44890"],
        "mania_only": True,
        "source": "v5",
        "v5": {
            "bin": S3K_SPRITES / "3K_Players" / "Amy.bin",
            "gif": S3K_SPRITES / "3K_Players" / "Amy.gif",
            # Mania's animation (Players/Sonic.bin) -> hers, by name, where they differ or hers is empty. Names not
            # listed take her animation of the same name.
            "map": {
                "Air Walk": "Fall",
                "Spring Twirl": "Spring CS",
                "Skid Turn": "Skid",
                "Dropdash": "Jump",
                "Hang": "HangGimmick",
                "Stick": "Idle",
                "Bubble": "Breathe",
                "Ride": "Idle",
                "Bungee": "HangGimmick",
                "Fly": "Dash",
            },
            # her own moves' animations, after Mania's 54 (anim_base + 0..3; "Hammer" is the thrown hammer, SuperHammer's)
            "abilities": ["Hammer Jump", "Hammer Dash", "Hammer Throw", "Hammer"],
            # the continue screen (Players/Continue.bin's idle / react): her own S3&K continue poses
            "continue": ("Continue", "Continue Up"),
            # "<name> Reach" copies (after the continue poses) of these, with box 0 = the frame's AttackBox (box 2): Mania's
            # attack check reads box 0 only, so the mod stands her in with these for the hammer's reach (ManiaAmy.h)
            "reach": ["Hammer Jump", "Hammer Dash"],
        },
        # her thrown hammer (Origins' SuperHammer, Amy's: exe disassembly, scratchpad amy/STATUS.md 4): a plain arc through
        # everything, gone offscreen or after a hit. Y is ManiaAmy.h's (the Super gate, the pose): never the generic throw
        "shot": {"motion": "bounce", "terrain": False, "speed": 0x28E00, "start_vy": -0x56A00, "gravity": 0x3800,
                 "max_fall": 0x200000, "carry": True, "cooldown": 6, "max_alive": 8, "lifetime": 600, "x": 8, "y": -8,
                 "sound": "Global/HammerThrow.wav"},  # (Origins' own: tools/origins_sfx.py, loaded by Data/Game/Game.xml)
        # her moves' numbers (the JSON's "amy" section; ManiaAmy.h has the same defaults): Origins' (0x10000 = 1 px/frame)
        "moves": {"chargeFrames": 20, "dashSpeed": 0x60000, "dashFrames": 60, "throwPose": 13, "jumpOffset": 2,
                  "sensorY": 17},
        # official UI pictures: (sprite file, animation, frame) in extracted/Sonic3K/Data/Sprites
        "ui": {
            "life_icon": ("3K_Global/HUD.bin", "Life Icons", 3),         # her HUD head (16x16, its box dropped)
            "continue_icon": ("3K_HPZ/SpecialClear.bin", "Continue Amy", 0),  # the results' continue icon
            "sign_face": ("3K_Global/SignPost.bin", "Amy", 0),           # her S3&K signpost face (48x32)
        },
    },
]


def mania_only(folder):
    return next((e for e in MANIA_ONLY if e["art"].name == folder), None)
