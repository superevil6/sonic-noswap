"""The extra characters NoSwap builds, in build order: the older make_configs.py characters listed below, plus every
folder with a character.json (found by itself: character_json.folders()). Each one's number n comes from the registry
by its key (tools/registry.py, data/registry.json; never from a place in this list). Extra n is built with ID 6 + n
(its "build ID", alias PLAYER_EXTRAn_A): only a row number inside its own package's scripts' tables. Its kind (its number in Origins' character
select, and the engine's stage.playerListPos) is given at runtime by the DLL's registry from its key (native/src/Roster.h,
roster.json), and every package script works under any kind from 7 up (tools/generic_extra.py). The first 21 keys are
frozen at kinds 7-27 (Roster.h LEGACY_KEYS, checked by gen_s3k_header.py); the registry keeps them at numbers 1-21.

Each extra's art is cut by sheet2ani.py from its config in `art` (one config per game), which also
writes the UI manifests the game builds read (Extra<n>_ui.json, and for Sonic 1 Extra<n>_ending.json).
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO / "tools") not in sys.path:  # (character_json, beside this file, wherever extras is imported from)
    sys.path.append(str(REPO / "tools"))
import character_json  # noqa: E402  (characters defined by a character.json: docs/character-json.md)
import registry  # noqa: E402  (every character's permanent numbers, by key: data/registry.json)

EXTRAS = [
    {
        "art": REPO / "testmods" / "metal-sonic",
        "name": "METAL SONIC",  # act results name, built from the title-card alphabet
        # Every extra can go Super. True: Sonic's own Super palette (Metal fits in Sonic's colours); False: the extra's
        # own colours glow instead (abilities.py "Super, for every extra"; the S3&K DLL's SuperGlow)
        "super": True,
        "drop_dash": False,
        "palette": {},  # own palette slots (index -> RGB); Metal fits in Sonic's colours
    },
    {
        "art": REPO / "testmods" / "big",
        "name": "BIG",
        "super": False,
        "drop_dash": False,
        "palette": "big.json",  # his purples, golds, greys and the lure's greens in slots 74-95 (his config's PALETTE)
        # Public: DBurraki's sheet ("Remix: Bigger, Better, Refined", with thanks to Cylent Nite) asks for credit and that
        # nobody claims it (testmods/big/SOURCE.txt, mods/NoSwap/README.md). 66 px tall, not scaled. The generic ball in
        # his purples (the sheet has none). His card: 8x as the others, the gestures' wave (WAVE1, testmods/big/
        # make_configs.py's working copy: both arms in view; "hands behind his back" read as armless, the user), its belly
        # (pivot) on the centre line, the tail and part of the near hand cut off at the card's left edge (as Tails' tails),
        # half a column of the waving fist at the right; 66 px tall, 2 over the 8x cell, so his feet are 8 px above its
        # bottom, not 20 (the user, 2026-09-28: bigger, the tail may be cut)
        "card": {"sheet": REPO / "testmods" / "big" / "build" / "source.png", "rect": [105, 374, 82, 66], "scale": 8,
                 "pivot": 54, "baseline": 8, "background": "#004040"},
    },
    {
        "art": REPO / "testmods" / "shadow",
        "name": "SHADOW",
        "super": False,
        "drop_dash": False,
        "palette": "shadow.json",  # own colours, as listed in the extra's sheet2ani config
    },
    {
        "art": REPO / "testmods" / "blaze",
        "name": "BLAZE",
        "super": False,
        "drop_dash": False,
        "palette": "blaze.json",
    },
    {
        "art": REPO / "testmods" / "silver",
        "name": "SILVER",
        "super": False,
        "drop_dash": False,
        "palette": "silver.json",
    },
    {
        "art": REPO / "testmods" / "mighty",
        "name": "MIGHTY",
        "super": False,
        "drop_dash": False,
        "palette": "mighty.json",
    },
    {
        "art": REPO / "testmods" / "ray",
        "name": "RAY",
        "super": False,
        "drop_dash": False,
        "palette": "ray.json",
    },
    {
        "art": REPO / "testmods" / "rouge",
        "name": "ROUGE",
        "super": False,
        "drop_dash": False,
        "palette": "rouge.json",
        "base": "knuckles",  # Knuckles' moveset (glide, climb), physics and wall breaking; art on his .ani layout
    },
    {
        "art": REPO / "testmods" / "charmy",
        "name": "CHARMY",
        "super": False,
        "drop_dash": False,
        "palette": "charmy.json",
        "base": "tails",  # Tails' flight (a plain Player Object, so no tails are drawn); art on his .ani layout
    },
    {
        "art": REPO / "testmods" / "cream",
        "name": "CREAM",
        "super": False,
        "drop_dash": False,
        "palette": "cream.json",
        "base": "tails",  # Tails' flight, as in Sonic Advance
        # Her card: the sheet's hands-on-hips pose (box 73, her "Bored!" frame), 8x as the others, from the Cheese-free
        # sheet (make_configs.decheese): both arms in view (the standing frame's arms fold in front and read as armless,
        # the user, 2026-09-28)
        "card": {"sheet": REPO / "testmods" / "cream" / "build" / "Cream_nocheese.png", "rect": [291, 330, 31, 46],
                 "scale": 8, "background": "#ffffff"},
    },
    {
        "art": REPO / "testmods" / "robotnik",
        "name": "ROBOTNIK",
        "super": False,
        "drop_dash": False,
        "palette": "robotnik.json",  # every colour exact in its own slot: the sheet says "NO RECOLORS"
    },
    {
        "art": REPO / "testmods" / "max",
        "name": "MAX",
        "super": False,
        "drop_dash": False,
        "palette": "max.json",
    },
    {
        "art": REPO / "testmods" / "tikal",
        "name": "TIKAL",
        "super": False,
        "drop_dash": False,
        "palette": "tikal.json",
    },
    {
        "art": REPO / "testmods" / "mario",
        "name": "MARIO",
        "super": False,
        "drop_dash": False,
        "palette": "mario.json",
        "roll": True,  # his jump is a fist-up leap, not a ball: rolling shows his own curl ("Rolling", slot 49)
    },
    {
        "art": REPO / "testmods" / "trip",
        "name": "TRIP",
        "super": False,
        "drop_dash": False,
        "palette": "trip.json",
    },
    {
        "art": REPO / "testmods" / "gamma",
        "name": "GAMMA",
        "super": False,
        "drop_dash": False,
        "palette": "gamma.json",
        # He never curls into a ball (the user's choice): no rolling and no Spin Dash, in all four games. Down
        # while moving does nothing, down + jump is a plain jump, crouching still works. His jump is his jump pose,
        # and still attacks like everyone's; special stages that show a ball use it (ball_animation).
        "no_roll": True,
    },
    {
        "art": REPO / "testmods" / "jet",
        "name": "JET",
        "super": False,
        "drop_dash": False,
        "palette": "jet.json",
    },
    {
        "art": REPO / "testmods" / "mecha-sonic",
        "name": "MECHA SONIC",
        "super": False,  # his own colours glow gold (Super Mecha Sonic is golden in Sonic & Knuckles)
        "drop_dash": False,
        "palette": "mecha.json",
    },
    {
        "art": REPO / "testmods" / "sticks",
        "name": "STICKS",
        "super": False,
        "drop_dash": False,
        "palette": "sticks.json",
        # Her jump is Tails' own ball in her colours (testmods/sticks/make_configs.py, tools/sonic_ball.py): no "roll"
        # needed. Her art is enlarged 1.2x (the user's exception to the faithful art rule, for her only).
        # Public (the user's decision, 2026-09-28): the sheet's only term is credit (README Credits).
    },
    {
        "art": REPO / "testmods" / "chaos",
        "name": "CHAOS",
        "super": False,
        "drop_dash": False,
        "palette": "chaos.json",
        # His jump is the generic spin ball in his blues (tools/generic_ball.py), and his art is enlarged 1.1x (the
        # user's exception for him). Public:
        # ssstGoldy20's sheet has no terms, credit only (testmods/chaos/SOURCE.txt, mods/NoSwap/README.md).
        # His Origins select card is his "Stopped" frame, 8x, like everyone's (the sheet's big "PIXEL ART" drawing at
        # 4x clashed with the other cards, the user said)
    },
    {
        "art": REPO / "testmods" / "flicky",
        "name": "FLICKY",
        "super": False,
        "drop_dash": False,
        "palette": "flicky.json",
        "base": "tails",  # Tails' own flight (as Cream and Charmy), with his own fly, tired and swim frames
        # Public: TheOrangePlumber's sheet asks for credit, and that he's never made Sonic.exe-related
        # (testmods/flicky/SOURCE.txt, mods/NoSwap/README.md). Drawn about 22 px tall, not enlarged (that needs the
        # user's approval). His jump is his own Spinball
    },
    {
        "art": REPO / "testmods" / "tails-doll",
        "name": "TAILS DOLL",
        "super": False,
        "drop_dash": False,
        "palette": "tailsdoll.json",
        # (built on Sonic since the user's rework, 2026-09-28: his Phase Warp and Screen Nuke replace Tails' flight)
        # Public: credit only (testmods/tails-doll/SOURCE.txt, mods/NoSwap/README.md). His tails are the sheet's own
        # separate pieces, layered behind his body frames at build time (make_configs.py). Drawn 35 px tall with his
        # antenna, not enlarged. His jump is his own ROLL ball
    },
    {
        "art": REPO / "testmods" / "bark",
        "name": "BARK",
        "super": False,
        "drop_dash": False,
        "palette": "bark.json",
        # Public: deltaConduit's sheet asks for credit, no edits and nothing .exe-related (testmods/bark/SOURCE.txt,
        # mods/NoSwap/README.md): frames are crops only, every colour exact. 52 px tall, not scaled. His jump is his own
        # SPIN ball
    },
    {
        "art": REPO / "testmods" / "heavy",
        "name": "HEAVY",
        "super": False,
        "drop_dash": False,
        "palette": "heavy.json",
        # Public: Akimaca's sheet (with Bomb's frames) asks for credit only (testmods/heavy/SOURCE.txt,
        # mods/NoSwap/README.md). Drawn facing left: cut from a mirrored copy. 31 px tall, not scaled. His jump is Sonic's
        # ball in his greys (tools/sonic_ball.py); he breaks walls like Knuckles (abilities.py breaks_walls)
    },
    {
        "art": REPO / "testmods" / "bomb",
        "name": "BOMB",
        "super": False,
        "drop_dash": False,
        "palette": "bomb.json",
        # Public: Akimaca's sheet (shared with Heavy) asks for credit only (testmods/bomb/SOURCE.txt,
        # mods/NoSwap/README.md). Drawn facing left: cut from a mirrored copy. 26 px tall, not scaled. His jump is Sonic's
        # ball in his black and red (tools/sonic_ball.py); Y: Self-Destruct (a radial melee he's safe during)
    },
    {
        "art": REPO / "testmods" / "honey",
        "name": "HONEY",
        "super": False,
        "drop_dash": False,
        "palette": "honey.json",
        # Public: Xeric's sheet asks for credit and a link to his DeviantArt page (testmods/honey/SOURCE.txt,
        # mods/NoSwap/README.md). 42 px tall, not scaled; six 1-2 px colours merged (her config's MERGED). Her own ball
    },
    {
        "art": REPO / "testmods" / "omega",
        "name": "OMEGA",
        "super": False,
        "drop_dash": False,
        "palette": "omega.json",
        # Public: Gussprint's sheet asks for credit and that nobody claims it (testmods/omega/SOURCE.txt,
        # mods/NoSwap/README.md). 45 px tall (about Big's size), not scaled. He never curls into a ball (as Gamma): his
        # jump is his fall pose, no rolling or Spin Dash
        "no_roll": True,
        # His idle frame is 56 px wide, over the 54 an 8x card picture has room for (origins_cards: 27 px each side of
        # the pivot): the card is that frame with a claw tip's column off each side (a crop), 8x
        "card": {"sheet": REPO / "testmods" / "Omega.png", "rect": [4, 4, 54, 45], "scale": 8, "background": "#ffffff"},
    },
    {
        "art": REPO / "testmods" / "sally",
        "name": "SALLY",
        "super": False,
        "drop_dash": False,
        "palette": "sally.json",
        # Public: E-122-Psi's sheet needs no permission, only credit (testmods/sally/SOURCE.txt, mods/NoSwap/README.md).
        # 42 px tall, not scaled; every colour exact. Her own ball and Spin Dash
    },
    {
        "art": REPO / "testmods" / "marine",
        "name": "MARINE",
        "super": False,
        "drop_dash": False,
        "palette": "marine.json",
        # Public: Nintendo_6444's sheet asks for credit only, to Deebs, FireX, Vol, Frario, Rathe Ethransu and him
        # (testmods/marine/SOURCE.txt, mods/NoSwap/README.md). 33 px tall, not scaled; her rarer shades merged (her
        # config's MERGED). Her own ball
    },
    {
        "art": REPO / "testmods" / "mephiles",
        "name": "MEPHILES",
        "super": False,
        "drop_dash": False,
        "palette": "mephiles.json",
        # Public: Gardow's sheet lists its credits (Gardow, Xeric, Fox Omega, Charity, Domenico) and no other terms
        # (testmods/mephiles/SOURCE.txt, mods/NoSwap/README.md). 40 px tall, not scaled; every colour exact. The generic
        # ball in his blues (the sheet has none)
    },
    {
        "art": REPO / "testmods" / "emerl",
        "name": "EMERL",
        "super": False,
        "drop_dash": False,
        "palette": "emerl.json",
        # Public: the Mod.Gen Project sheet ("Emerl by Xeric and Deebs") asks only for credit to the "Mod.Gen Project
        # Team" (testmods/emerl/SOURCE.txt, mods/NoSwap/README.md). 43 px tall, not scaled; six rare shades merged (his
        # config's MERGED). The generic ball in his golds (the sheet has none); his run has Metal Sonic's energy ball (Akimaca's sheet) behind it
    },
    {
        "art": REPO / "testmods" / "megaman",
        "name": "MEGA MAN",
        "super": False,
        "drop_dash": False,
        "palette": "megaman.json",
        # CROSSOVER (memory crossover-characters.md): Mega Man is Capcom's, so he ships only as his own download, never in
        # the all-in-one (make_release.py). Sheet: Mega Man 7 (SNES) ripped by Mister Man for The Spriters Resource
        # ("Please do not steal. Only for tSR."): credit to Mister Man and tSR (testmods/megaman/SOURCE.txt,
        # mods/NoSwap/README.md). Drawn facing left: cut from a mirrored copy. 40 px tall, not scaled. He never curls into
        # a ball (as Gamma): his jump is his Jump row's arms-up frame; down + jump is his Slide
        "no_roll": True,
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "ray-poward",  # (not Ray the Flying Squirrel, "ray": key noswap.ray-poward)
        "name": "RAY POWARD",
        "super": False,
        "drop_dash": False,
        "palette": "raypoward.json",
        # Ray Poward from Contra: Hard Corps (Sega Genesis). CROSSOVER: a separate download only, never in the all-in-one.
        # The sheet (testmods/ray-contra/RayContra.png, ripped by Eckles D. Fum with Marksiks) says "No need for credits
        # but don't claim as your own": credited anyway (testmods/ray-poward/SOURCE.txt, mods/NoSwap/README.md). 40 px
        # tall, Genesis art at 1x. His jump and roll are his own somersault (no ball); down + jump is his Slide
        # (abilities.py "slide") instead of the Spin Dash. no_stomp (the user, 2026-10-02): the somersault isn't an attack, and
        # rolling shows his slide (P1, "Rolling": "roll")
        "roll": True,
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "sparkster",
        "name": "SPARKSTER",
        "super": False,
        "drop_dash": False,
        "palette": "sparkster.json",
        # Sparkster, the Rocket Knight (Rocket Knight Adventures, Sega Genesis). A separate download only, never in the
        # all-in-one. Sheet: original rip by Jack Rost, re-ripped by UltraHype97 ("Give credit if used!"; assets (c)
        # Konami): testmods/sparkster/SOURCE.txt, mods/NoSwap/README.md. Genesis art at 1x. He never curls into a ball (as
        # Gamma): his jump is his Moving Jump's tuck. Sword Slash on Y, Rocket Burst on holding jump in mid-air
        "no_roll": True,
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "ristar",
        "name": "RISTAR",
        "super": False,
        "drop_dash": False,
        "palette": "ristar.json",
        # Ristar (Sega Genesis). A separate download only, never in the all-in-one. Sheets compiled by Drshnaps, ripped by
        # Jermungandr (The Spriters Resource; Ristar (c) Sega): testmods/ristar/SOURCE.txt, mods/NoSwap/README.md.
        # Genesis art at 1x. His jump and roll are his own Spin/Roll frames. The Grab on Y (aimed 8 ways; his arms are
        # runtime-drawn lines, as in the game), the wall / ceiling hang and the Meteor Strike: tools/star_grab.py
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "headdy",
        "name": "HEADDY",
        "super": False,
        "drop_dash": False,
        "palette": "headdy.json",
        # Dynamite Headdy (Sega Genesis, Treasure). A separate download only, never in the all-in-one. Sheet ripped by
        # Sonicfan32 ("Credit is optional, but don't steal. This game belongs to Treasure and Sega."): credited
        # (testmods/headdy/SOURCE.txt, mods/NoSwap/README.md). Genesis art at 1x; each frame is his headless body with
        # his head put on at its neck bolt, as the game builds him. He never curls into a ball: his jump is his arms-up
        # jump. The Head Throw on Y (aimed 8 ways, out and back): tools/head_throw.py
        "no_roll": True,
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "john-morris",
        "name": "JOHN MORRIS",
        "super": False,
        "drop_dash": False,
        "palette": "johnmorris.json",
        # John Morris (Castlevania: Bloodlines, Sega Genesis). A separate download only, never in the all-in-one. Sheets:
        # John by Badbatman3, re-ripped by UltraHype97 ("Give credit if used!"), and the items / sub-weapons extracted by
        # Yawackhary ("no credit needed but don't steal"; both Konami's): credited (testmods/john-morris/SOURCE.txt,
        # mods/NoSwap/README.md). Genesis art at 1x. He never curls into a ball: his jump is his own tuck. The whip on Y
        # (its LV1 leather whip pasted onto his attack frames, as the sheet assembles it), the sub-weapons on up + Y (a
        # ring each), and monitors swapping the sub-weapon (abilities.py "monitor_swap")
        "no_roll": True,
        "crossover": True,
    },
    {
        "art": REPO / "testmods" / "ecco",
        "name": "ECCO",
        "super": False,
        "drop_dash": False,
        "palette": "ecco.json",
        # Ecco the Dolphin (Ecco: The Tides of Time, Sega Genesis; Sega / Novotrade). A separate download only, never in
        # the all-in-one; not in the Mania build. Sheet ripped by arkonviox (The Spriters Resource, no terms given):
        # credited (testmods/ecco/SOURCE.txt, mods/NoSwap/README.md). Genesis art at 1x. The user's joke design
        # (2026-09-30): on land he lies on his side and flops along, painfully slow, with a small hop (no ball); in
        # water the free swim (abilities.py, the lead's). His card: the up-right swim's second frame (a leap), 8x
        "card": {"sheet": REPO / "testmods" / "ecco" / "Ecco_TidesOfTime.png", "rect": [73, 557, 48, 57], "scale": 8,
                 "background": "#00ffff"},
        "no_roll": True,
        "crossover": True,
    },
]
# Characters defined by a character.json (docs/character-json.md) have no entry above: every folder with one
# (character_json.folders(): testmods/*/ and $NOSWAP_CHARACTER_DIRS) joins EXTRAS by itself. The entries above are the
# older make_configs.py characters, until they're converted.
# The Creator Kit (NOSWAP_KIT=1, tools/make_kit.py) builds only the creator's own characters: NoSwap's hand-listed ones
# aren't in its workspace, so the entries whose folders are missing are left out (in the repo a missing one still stops
# the build later, as before).
KIT = bool(os.environ.get("NOSWAP_KIT"))
if KIT:
    EXTRAS[:] = [e for e in EXTRAS if (e["art"] / "make_configs.py").exists()]
_listed = {e["art"].resolve() for e in EXTRAS}
EXTRAS += [character_json.extras_entry(f) for f in character_json.folders() if f.resolve() not in _listed]
# Own palette colours can share slots between extras: only one plays at a time, and wherever several
# are shown together (title pickers, save screens) the art is recoloured to that screen's colours.

# Each public extra's short sprite credit, shown under the cards in Origins' character select while its card is
# highlighted (its package's noswap_character.json "credit_short"; build_origins_menu.py, the DLL's Hook_UpdateSaveInfo).
# The main artist(s) of its sheet, from mods/NoSwap/README.md's Credits (which stay the full credits), at most
# origins_cards.CREDIT_UNITS characters (keep it about 32); "et al." where the sheet credits many. By art folder.
CREDIT_SHORT = {
    "metal-sonic": "Sprites: Akimaca",
    "big": "Sprites: DBurraki",
    "shadow": "Sprites: AsuharaMoon et al.",
    "blaze": "Sprites: Madz & Selphy Geumja",
    "silver": "Sprites: Gardow et al.",
    "mighty": "Sprites: Akimaca",
    "ray": "Sprites: Akimaca",
    "rouge": "Sprites: DeltaConduit",
    "charmy": "Sprites: Casteor573",
    "cream": "Sprites: FroggyMudd",
    "robotnik": "Sprites: Dr. Cheesecrumbz",
    "max": "Sprites: Akimaca",
    "tikal": "Sprites: SunnyVies",
    "mario": "Sprites: Jon Gandee",
    "trip": "Sprites: miniluv73 & Tarkan809",
    "gamma": "Sprites: Nebula et al.",
    "jet": "Sprites: Gabriel Frag",
    "mecha-sonic": "Sprites: Domenico",
    "sticks": "Sonic Legends: Neo-Fire-Sonic & UberHawg",
    "chaos": "Sprites: ssstGoldy20",
    "flicky": "Sprites: TheOrangePlumber",
    "tails-doll": "Sprites: Nikog266 et al.",
    "bark": "Sprites: deltaConduit",
    "heavy": "Sprites: Akimaca",
    "bomb": "Sprites: Akimaca",
    "honey": "Sprites: Xeric",
    "omega": "Sprites: Gussprint",
    "sally": "Sprites: E-122-Psi",
    "marine": "Sprites: Nintendo_6444 et al.",
    "mephiles": "Sprites: Gardow et al.",
    "emerl": "Sprites: Mod.Gen Project Team",
    "ray-poward": "Sprites: Eckles D. Fum & Marksiks",
    "megaman": "Sprites: Mister Man (tSR)",
    "sparkster": "Sprites: Jack Rost & UltraHype97",
    "ristar": "Sprites: Drshnaps & Jermungandr",
    "headdy": "Sprites: Sonicfan32",
    "john-morris": "Sprites: Badbatman3 & UltraHype97",
    "ecco": "Sprites: arkonviox",
}

# S3&K act results accent (tools/ui_accent.py): the three shades, light to dark, its results name and the streaks beside
# BONUS / TOTAL are drawn in (Sonic's: "#6060E0", "#2040C0", "#202080"), in its package's "ui_accent". By art folder;
# an extra not listed gets its own main colour's shades automatically (ui_accent.automatic). Hand-set from their own
# palettes where the automatic pick reads poorly; change freely (a runtime palette effect, no art changes).
UI_ACCENT = {
    "shadow": ["#E70000", "#636363", "#212121"],    # dark grey and black, red highlight
    "big": ["#7454C2", "#490EAB", "#22064F"],       # purple
    "omega": ["#F82000", "#A81000", "#700000"],     # red
    "gamma": ["#FE0000", "#980001", "#470101"],     # red
    "silver": ["#00FFFF", "#8080A0", "#404060"],    # grey, cyan highlight
    "blaze": ["#F878F8", "#C838E8", "#8808C8"],     # lilac
    "rouge": ["#FCFCFC", "#FC00FC", "#900090"],     # white, pink
    "mephiles": ["#4080E0", "#212084", "#202040"],  # dark blue-violet
    "chaos": ["#80E8F8", "#00B8F8", "#0040E8"],     # cyan
    "bomb": ["#909090", "#484848", "#222034"],      # black
    "heavy": ["#B4B4B4", "#909090", "#484848"],     # grey
    "sally": ["#E08000", "#A02000", "#800000"],     # brown-red
    "mario": ["#FC0000", "#900000", "#480000"],     # red (the automatic pick is his brown)
    "ray-poward": ["#90D8F8", "#0090B0", "#004868"],  # his shirt's blues (the automatic pick is his olive trousers)
}

if KIT:  # (the Creator Kit: these are NoSwap's own characters' settings, by folder; a creator's folder may share a name)
    CREDIT_SHORT.clear()
    UI_ACCENT.clear()

# Numbers come from the registry (tools/registry.py, data/registry.json) by key, never from a place in this list: today's
# characters keep the numbers they had, a new key gets the next number never given, and the file keeps it for good.
for extra in EXTRAS:
    # The character's permanent name (docs/plan-b-modular-characters.md): saves and picks are stored under it, so
    # numbering can change without mixing anyone's saves up. A character.json's "key" (<creator>.<character>), else
    # noswap.<art folder>: never rename one.
    extra["_key"] = extra.get("_key") or "noswap." + extra["art"].name
CONFIGS_MISSING = []  # art folders whose configs aren't written yet (tools/write_configs.py)
_NUMBERS = registry.numbers([(e["_key"], e["art"].name) for e in EXTRAS])
EXTRAS.sort(key=lambda e: _NUMBERS[e["_key"]])
for extra in EXTRAS:
    n = _NUMBERS[extra["_key"]]
    if isinstance(extra["palette"], str) and not (extra["art"] / extra["palette"]).exists():
        # (a fresh checkout: its configs aren't written yet. tools/write_configs.py writes them first; meanwhile a
        # make_configs.py that imports this module still loads)
        CONFIGS_MISSING.append(extra["art"].name)
        extra["palette"] = {}
    if isinstance(extra["palette"], str):  # read from the extra's config: {"74": "#rrggbb", ...}
        cfg = json.loads((extra["art"] / extra["palette"]).read_text())
        extra["palette"] = {int(s): int(c.lstrip("#"), 16) for s, c in cfg.get("palette", {}).items()}
    extra.setdefault("base", "sonic")  # whose moveset the extra plays with
    extra.setdefault("roll", False)  # own rolling animation (appended slot 49), for extras whose jump isn't a ball
    extra.setdefault("no_roll", False)  # never rolls or Spin Dashes (abilities.apply_no_roll, CD, the DLL)
    extra.setdefault("private", False)  # not for release (the artist's permission is pending): private_extras()
    extra.setdefault("crossover", False)  # a separate download only, never in the all-in-one: crossovers and every extra added after the 2026 SHC entry
    extra.setdefault("credit_short", CREDIT_SHORT.get(extra["art"].name, ""))  # "": no credit line on its card
    extra.setdefault("card", None)  # own Origins card picture (a sheet crop, enlarged: build_origins_menu.own_card,
    # {"sheet", "rect" [x, y, w, h], "scale" (a multiple of 4), "background", optional "pivot" and "baseline"}); None: its "Stopped" frame, 8x
    if extra["roll"] and extra["no_roll"]:
        raise SystemExit(f"extras.py: {extra['name']} has both \"roll\" and \"no_roll\"")
    extra["n"] = n
    extra["id"] = 6 + n
    extra["alias"] = f"PLAYER_EXTRA{n}_A"
    extra["key"] = extra.pop("_key")  # (see above)
    # Extra<n>.ani, Extra<n>SS.ani, Extra<n>_<k>.gif: sheet2ani's names, kept with the art (player_build); its package
    # ships them under fixed names (PLAYER_ANI...)
    extra["file"] = f"Extra{n}"


def ui_manifest(extra, kind="ui"):
    """kind: "ui" (HUD, monitor, signpost, mini icons) or "ending" (Sonic 1 ending poses)."""
    return json.loads((extra["art"] / f"{extra['file']}_{kind}.json").read_text())


def private_extras():
    """Extras marked "private": built and played locally, never released. There's no release packaging yet;
    whatever packs a release must use this to leave them out:

    - their own files, private_outputs(extra) (globs under mods/NoSwap; .gitignore lists them too, so a commit
      can't publish their art: keep it in step);
    - everything shared that has them in it: raw/text (the card name keys MAINMENU_character_name_noswap<n>_1/_2) and
      raw/ui (the card picture cell, null_char_<7+n>) until phase B; the S1/S2/CD player scripts NoSwap ships have no
      extra's parts any more, and the DLL knows no character by name (its registry only freezes the first 21 keys).
      (Their S1/S2 UI art is in their package's own "*_NoSwap.gif" sheets; the shared copies' box sizes still count
      them.)

    Numbering (phase A, docs/plan-b-modular-characters.md): a character's kind no longer depends on this list. The
    DLL numbers installed packages at runtime by key, and a missing package is simply not offered, so leaving a
    character out of a release means not shipping its package: nobody else's number moves. What still counts her (until
    phase B builds the menu at runtime): the prebuilt menu archives (her card name keys and picture at kind 25) and the
    frozen first 21 keys (Roster.h LEGACY_KEYS: keep her entry in this list, or the build stops). Her build ID (25) is
    only a row in her own package's tables.
    Saves and picks are stored by key, so nothing needs renumbering."""
    return [e for e in EXTRAS if e["private"]]


def private_outputs(extra):
    """Globs (relative to mods/NoSwap) of the files built for this extra alone, in every game."""
    f, n = extra["file"], extra["n"]
    return [f"characters/{extra['art'].name}/**",  # its character package (tools/build_packages.py)
            # (before the fixed player art names: its S1/S2/CD player .ani and sheets, and the old S1 special stage .ani.
            # Now in its package as PLAYER_ANI and player_sheet(k), kept with its art in between: player_build)
            f"*/Data/Animations/{f}.ani", f"*/Data/Animations/{f}SS.ani",
            f"*/Data/Sprites/Players/{f}_*.gif",
            # (before the CD packages: CD's special-stage balls, S2's too; CD's own Display / Items2 copies; CD palettes.
            # Now in its package, with S2's, as Special/NoSwap_Extra.gif, Global/Display_x.gif..., NoSwap_Extra*.act)
            f"*/Data/Sprites/Special/NoSwap_{f}.gif",
            f"*/Data/Sprites/Global/*_x{n}.gif",
            f"SonicCDu/Data/Palettes/NoSwap_{f}*.act",
            # (before the S3&K save screen pictures moved to the packages: its picture. Now in its package as
            # S3K_MENU_PICTURE)
            f"Sonic3ku/Data/Sprites/3K_Players/Menu{f}.*",
            # (before the S3&K packages: its player, Blue Spheres, HUD and signpost files. Now in its package, under
            # the fixed names S3K_FIXED)
            f"Sonic3ku/Data/Sprites/3K_Players/{f}.*",
            f"Sonic3ku/Data/Sprites/3K_Special/{f}.bin", f"Sonic3ku/Data/Sprites/3K_Special/NoSwap_{f}.gif",
            f"Sonic3ku/Data/Sprites/3K_Global/HUD_{f}.*", f"Sonic3ku/Data/Sprites/3K_Global/SignPost_{f}.*"]


# S3&K's per-extra files under the fixed names the DLL loads while an extra plays (docs/plan-b-modular-characters.md
# step 3b item 7), relative to Sonic3ku/Data/Sprites. NoSwap ships placeholders (build_s3k_art.write_placeholders); each
# package ships its own, and its .bin files name its sheets by these same names.
S3K_FIXED = ["3K_Players/Extra.bin", "3K_Players/Extra.gif",  # the player (on its base's animation list)
             "3K_Special/Extra.bin", "3K_Special/NoSwap_Extra.gif",  # the Blue Spheres runner: its spin ball
             "3K_Global/HUD_Extra.bin", "3K_Global/HUD_Extra.gif",  # life icon, name tag, results name
             "3K_Global/SignPost_Extra.bin", "3K_Global/SignPost_Extra.gif",  # the goal sign's face
             "3K_HPZ/SpecialClear_Extra.bin", "3K_HPZ/SpecialClear_Extra.gif"]  # special stage results: its name


# S3&K's save screen picture (the extra's standing frame in the menu's colours: build_s3k_art.build_menu_frame). Several
# slots show at once, each maybe a different extra, and the engine keeps a loaded file under its name for the whole
# menu visit, so one fixed name can't serve them all: each package ships its picture under this one name (its .bin
# names exactly the .gif here), and at startup the DLL gives every extra with a picture its own numbered name for the
# session, 3K_Players/MenuPicture<j>.bin / .gif (j < S3K_MENU_PICTURES: menu_picture(j), placeholders NoSwap ships:
# build_s3k_art.write_menu_placeholders). It serves that .gif from the package, and that .bin from a copy it writes to
# NoSwap's cache/ folder with the sheet renamed to MenuPicture<j>.gif (docs/plan-b-modular-characters.md item 7).
S3K_MENU_PICTURE = ["3K_Players/MenuPicture.bin", "3K_Players/MenuPicture.gif"]
S3K_MENU_PICTURES = 64  # how many extras can have a save screen picture (the DLL's MENU_PICTURE_COUNT: extras_gen.h)


def menu_picture(j):
    """The numbered names (.bin, .gif) the DLL gives the j-th extra's save screen picture, relative to Sprites."""
    return [f"3K_Players/MenuPicture{j}.bin", f"3K_Players/MenuPicture{j}.gif"]


def s3k_build(extra):
    """Where build_s3k_art.py / build_s3k_hud.py write the extra's own S3&K files (S3K_FIXED, under Sonic3ku/Data/
    Sprites), with the art's other build intermediates, outside the mod: build_packages.py copies them into its
    package, with its save screen picture (S3K_MENU_PICTURE)."""
    return extra["art"] / "build" / "Sonic3ku" / "Data" / "Sprites"


def s1_special_ani(extra):
    """The extra's Sonic 1 special stage animation as sheet2ani writes it (its config's "extra_anis": Extra<n>SS.ani,
    naming the extra's Players/Extra<n>_<k>.gif sheets), kept with the art's other build intermediates, outside the
    mod: each package ships it as Animations/NoSwapExtraSS.ani (build_sonic1.package_special)."""
    return extra["art"] / "build" / f"{extra['file']}SS.ani"


def stash_special_ani(extra):
    """Move the Sonic 1 special stage .ani sheet2ani just wrote into the mod out to s1_special_ani (NoSwap doesn't ship
    it: docs/plan-b-modular-characters.md step 3b item 4). Run by build_art.py and build_sonic1.py."""
    written = REPO / "mods" / "NoSwap" / "Sonic1u" / "Data" / "Animations" / f"{extra['file']}SS.ani"
    if written.exists():
        s1_special_ani(extra).parent.mkdir(parents=True, exist_ok=True)
        written.replace(s1_special_ani(extra))


# A word a package's script writes where it needs the active extra's own kind (docs/plan-b-modular-characters.md, "Special
# stage retry"). Package scripts are kind-free (the DLL numbers characters at runtime), so the DLL's file hook serves
# any package .txt naming it as a copy with the word replaced by the active kind in decimal (native/src/ExtraData.h
# SubstituteActiveKind; the DLL gets it through extras_gen.h). A valid identifier, so the build's script checks read it
# as a name; build_packages.check_active_kind checks where it appears and that no other name matches it ignoring case.
ACTIVE_KIND_TOKEN = "NoSwapActiveKind"

# The extra's main player animation in Sonic 1, Sonic 2 and Sonic CD (docs/plan-b-modular-characters.md step 4, "fixed
# player art"): its package ships it as Animations/PLAYER_ANI, naming its sheets Sprites/player_sheet(1..), byte copies
# of the sheets sheet2ani cut (Players/Extra<n>_<k>.gif, in the order the .ani lists them). NoSwap ships placeholders under
# those names (the DLL only serves a package's file for a name NoSwap ships): the game's own Sonic.ani and PLAYER_SHEETS
# blank sheets. PLAYER_SHEETS is headroom over today's most (4 in Sonic 1, 5 in Sonic 2 and CD), so a new package with up
# to that many sheets needs nothing new from NoSwap; build_packages.py stops the build if an extra needs more.
PLAYER_GAMES = ("Sonic1u", "Sonic2u", "SonicCDu")
PLAYER_ANI = "NoSwapExtra.ani"
PLAYER_SHEETS = 8


def player_sheet(k):
    """The k-th (from 1) fixed sheet name a package's PLAYER_ANI names, relative to Data/Sprites."""
    return f"Players/NoSwapExtra_{k}.gif"


# The startup case line the S1/S2 builders write for each extra (and abilities.py finds it by): its animation load
# follows it.
STARTUP_COMMENT = "[NoSwap] extra character: Sonic's moveset with its own animation file"


def startup_case(extra):
    return f"case {extra['alias']} // {STARTUP_COMMENT}"


def player_build(extra, game):
    """Where the extra's player art for a game is kept, outside the mod: sheet2ani writes Animations/Extra<n>.ani and
    Sprites/Players/Extra<n>_<k>.gif into the mod's game folder, and stash_player_art moves them here (the .ani names the
    sheets by those numbered names). build_packages.py writes the package's fixed-name copies from here."""
    return extra["art"] / "build" / game / "Data"


def player_ani_path(extra, game):
    return player_build(extra, game) / "Animations" / f"{extra['file']}.ani"


def player_ani(extra, game, fixed=False):
    """The extra's player .ani as sheet2ani wrote it (read_ani's dict); fixed: as its package ships it, the sheets
    renamed to the fixed names (player_sheet) in the order the .ani lists them."""
    from sheet2ani import read_ani
    path = player_ani_path(extra, game)
    if not path.exists():
        raise SystemExit(f"{path} is missing: run tools/build_art.py {extra['art'].name}")
    ani = read_ani(path)
    if fixed:
        ani["sheets"] = [player_sheet(k) for k in range(1, len(ani["sheets"]) + 1)]
    return ani


def player_sheet_path(extra, game, sheet):
    """A sheet an extra's own (numbered) .ani names, e.g. "Players/Extra20_1.gif", or its fixed name
    (player_sheet(k), the k-th the .ani lists): where its file is kept (player_build)."""
    names = player_ani(extra, game)["sheets"]
    fixed = [player_sheet(k) for k in range(1, len(names) + 1)]
    if sheet in fixed:
        sheet = names[fixed.index(sheet)]
    return player_build(extra, game) / "Sprites" / sheet


def stash_player_art(extra):
    """Move the player .ani and sheets sheet2ani just wrote into the mod (S1, S2 and CD) out to player_build (NoSwap
    doesn't ship them: its package does, under the fixed names). A fresh .ani replaces the kept one and all its sheets.
    Run by build_art.py and at the start of each game build (which also moves a checkout's old copies out)."""
    for game in PLAYER_GAMES:
        mod = REPO / "mods" / "NoSwap" / game / "Data"
        ani = mod / "Animations" / f"{extra['file']}.ani"
        sheets = numbered_sheets(mod / "Sprites" / "Players", extra)
        if not ani.exists():
            if sheets:
                raise SystemExit(f"{sheets[0]} without {ani.name}: run tools/build_art.py {extra['art'].name}")
            continue
        keep = player_build(extra, game)
        (keep / "Animations").mkdir(parents=True, exist_ok=True)
        (keep / "Sprites" / "Players").mkdir(parents=True, exist_ok=True)
        for old in numbered_sheets(keep / "Sprites" / "Players", extra):
            old.unlink()
        for s in sheets:
            s.replace(keep / "Sprites" / "Players" / s.name)
        ani.replace(player_ani_path(extra, game))


def numbered_sheets(folder, extra):
    """The extra's numbered player sheets in a folder (Extra<n>_<k>.gif, not its _UI / _Ending sheets)."""
    import re
    return sorted(p for p in folder.glob(f"{extra['file']}_*.gif") if re.fullmatch(rf"{extra['file']}_\d+\.gif", p.name))


def stash_all_player_art():
    for e in EXTRAS:
        stash_player_art(e)


def ball_animation(extra):
    """The animation that shows the extra as a spin ball (special stages): its jump, or its own curl
    ("Rolling") if its jump isn't a ball (extras.py "roll"). An extra that never curls up ("no_roll": Gamma)
    has no ball at all: the stages show its jump pose. Nor does one whose roll is a slide (abilities.py "no_stomp": its
    "Rolling" is its slide pose): its jump pose too."""
    return "Rolling" if extra["roll"] and not no_stomp(extra) else "Jumping"


def no_stomp(extra):
    """abilities.py "no_stomp": the jump isn't an attack, and the roll ("roll": its "Rolling") is a slide, not a ball."""
    import abilities  # (abilities imports this module: only once both are loaded)
    return abilities.has(extra["id"], "no_stomp")


def aliases(prefix="public"):
    return "".join(f"{prefix} alias {e['id']} : {e['alias']}\n" for e in EXTRAS)


def case_labels(indent, comment="[NoSwap] placeholder: behaves like Sonic", only=None):
    """`case` lines for every extra (or those passing `only`), for fall-through into Sonic's case."""
    return "".join(f"{indent}case {e['alias']} // {comment}\n" for e in EXTRAS if only is None or only(e))


def palette_lines(extra, bank, indent, colours=None):
    """SetPaletteEntry lines writing the extra's own colours (or `colours`, index -> RGB) into a bank."""
    pal = colours if colours is not None else extra["palette"]
    return "".join(f"{indent}SetPaletteEntry({bank}, {i}, 0x{c:06X})\n" for i, c in sorted(pal.items()))


def tinted_palette(extra, normal, tinted):
    """The extra's colours as another palette file would show them (e.g. an underwater palette):
    each colour shifts like the three nearest colours in the game's normal palette do.
    `normal` and `tinted` are lists of RGB tuples for slots 0-73."""
    out = {}
    pairs = [(n, t) for n, t in zip(normal, tinted) if n != (255, 0, 255)]
    for i, c in extra["palette"].items():
        rgb = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        near = sorted(pairs, key=lambda p: sum((a - b) ** 2 for a, b in zip(rgb, p[0])))[:3]
        shifted = [min(255, max(0, rgb[k] + round(sum(t[k] - n[k] for n, t in near) / len(near))))
                   for k in range(3)]
        out[i] = (shifted[0] << 16) | (shifted[1] << 8) | shifted[2]
    return out
