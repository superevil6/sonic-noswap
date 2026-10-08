"""The creator-facing words for every NoSwap ability: names, descriptions, what each field means. EDIT THIS FILE to change
what docs/abilities.md and `noswap abilities` say.

Everything that can be read from the code is NOT here: which games have each ability, the fields' types, defaults and
example values, the characters that use it, the per-game animation slot numbers and the rules on combining moves. Those
come from tools/abilities_registry.py, which reads the pipeline. After editing, run
    python3 tools/abilities_registry.py --write
to regenerate docs/abilities.json and docs/abilities.md (and `--check` to see that every field is described).

Per ability:
  name         the display name
  kind         "move" (goes in the "abilities" list), "passive" (also in the list, always on), "setting" (NOT in the list:
               a field you set, which changes another move or the drawing)
  input        how the player starts it, in a few words
  description  one paragraph: what the player does and sees
  fields       {field: (unit, what it does[, range])}. Units (abilities_registry.UNITS explains them): frames, ticks,
               speed, accel, px, mult, bool, count, deg, list, frame list, px list, object, sound (see SOUNDS)
  sounds       {base: what it plays on}: the registry adds <base>, <base>_cd and <base>_s3k
  slots        {slot: what to draw there} (character.json ability_animations numbering; the build renumbers per game)
  optional_slots  slots it uses when present
  needs        plain-English requirements (base character, other fields)
  game_notes   {game: note} where a game's version differs or is partial; "partial: ..." marks it partial
"""

SOUNDS = {
    "": "Sonic 1 / Sonic 2: the game's sound name (e.g. \"Insta Shield\", \"Release\", \"Fire Dash\")",
    "_cd": "Sonic CD: a global sound alias (e.g. \"SFX_G_RELEASE\") or its number",
    "_s3k": "S3&K (and Mania): a sound file in the game's data (e.g. \"Global/Release.wav\"), or \"own:<name>\" for one of "
            "the character's own sounds (character.json \"sounds\"); left out, the move is silent there",
}

ABILITIES = {
    # ------------------------------------------------------------------------------------------------- jump abilities
    "jet_dash": dict(
        name="Jet Dash", kind="move", input="jump in mid-air",
        description="Press jump again in mid-air and the character blasts forward in a straight, level line, like a "
                    "homing attack with nothing to home on. The dash pose is an attack, so badniks and monitors in the "
                    "way break. If he's already moving faster than the dash, he keeps his own speed. Pair it with "
                    "Hover to let him drift down after the dash (Metal Sonic).",
        fields={"dash_frames": ("frames", "How long the dash lasts."),
                "dash_speed": ("speed", "The dash's speed, forward, level.")},
        slots={"41": "the dash pose (an attack)"},
    ),
    "hover": dict(
        name="Hover", kind="move", input="keep holding jump after another move",
        description="An add-on to Jet Dash, Rocket Ride or Ear Grapple: after that move, keeping jump held lets the "
                    "character hover, sinking slowly, for a limited time (Metal Sonic's hover, Robotnik's parachute, "
                    "Max's Ear Copter). On its own it does nothing.",
        fields={"hover_frames": ("frames", "How long the hover can last per jump."),
                "hover_sink": ("speed", "How fast he sinks while hovering.")},
        slots={"42": "the hover pose (not an attack)"},
        needs=["one of jet_dash, rocket_ride or ear_grapple"],
    ),
    "pogo": dict(
        name="Pogo Bounce", kind="move", input="jump in mid-air",
        description="Press jump in mid-air to bounce on a tail (or spring, or stick): every landing bounces him up "
                    "again for as long as jump is held. It attacks like a normal jump (Fang's tail bounce).",
        fields={"pogo_speed": ("speed", "The launch speed of each bounce (Sonic's jump is 0x68000).")},
        slots={"41": "the bounce pose"},
    ),
    "umbrella": dict(
        name="Float", kind="move", input="jump in mid-air, then hold it",
        description="Press jump in mid-air to open an umbrella, a jet pack or a psychic float, and drift down slowly "
                    "while jump stays held. Letting go closes it for the rest of that jump. Big's parasol, Silver's "
                    "float, Gamma's and Omega's jet hover and Mephiles' float all use this. With umbrella_attack it "
                    "becomes an attack that hits all around him (Espio's Whirlwind).",
        fields={"umbrella_sink": ("speed", "The fall speed while floating (Sonic can fall at up to 16 px a frame)."),
                "float_frames": ("frames", "How long the float can last per jump; 0 or left out: as long as jump is "
                                           "held."),
                "umbrella_attack": ("bool", "Make the float an attack that hits all around him, drawn from slot 41 "
                                            "instead of 42 (Espio's Whirlwind).")},
        slots={"42": "the floating pose (not an attack)"},
        optional_slots={"41": "with umbrella_attack: the whirling attack pose, used instead of 42"},
    ),
    "chaos_control": dict(
        name="Chaos Control", kind="move", input="jump in mid-air",
        description="Press jump in mid-air: the character freezes in a flash, warps forward in a quick dash, then pops "
                    "up with a little hop. The whole thing is an attack (Shadow's Chaos Control).",
        fields={"chaos_freeze": ("frames", "How long he hangs frozen in the flash before warping."),
                "chaos_warp": ("frames", "How long the warp dash lasts."),
                "chaos_speed": ("speed", "The warp dash's speed."),
                "chaos_pop": ("speed", "The upward speed of the hop at the end.")},
        slots={"41": "the flash / warp pose (an attack)"},
    ),
    "aim_dash": dict(
        name="Aimed Dash", kind="move", input="jump in mid-air (or Y with aim_dash_y)",
        description="Press jump in mid-air to dash: straight ahead, or at 45 degrees up or down if up or down is held "
                    "as it starts. It's an attack. Blaze's Burst Dash; Vector's version dashes straight up instead of "
                    "diagonally (up_x 0). With aim_dash_y it's started by Y instead, once per airborne period, and the "
                    "jump button keeps the base character's own move (Charmy's Stinger, with Tails' flight on jump).",
        fields={"dash_frames": ("frames", "How long the dash lasts."),
                "dash_speed": ("speed", "The straight dash's speed."),
                "diag_x": ("speed", "The diagonal dash's speed along (about dash_speed x 0.7 keeps the same speed)."),
                "diag_y": ("speed", "The diagonal dash's speed up / down."),
                "up_x": ("speed", "Override the UP dash's speed along (0: straight up). Defaults to diag_x."),
                "up_y": ("speed", "Override the UP dash's upward speed. Defaults to diag_y."),
                "aim_dash_y": ("bool", "Start the dash with Y in mid-air instead of jump.")},
        slots={"41": "dashing straight (an attack)", "45": "dashing up", "46": "dashing down"},
        game_notes={"cd": "Sonic CD has no up / down dash poses: slot 41 shows for all three directions"},
    ),
    "hammer_drop": dict(
        name="Hammer Drop", kind="move", input="jump in mid-air",
        description="Mighty's move from Sonic Mania Plus: press jump in mid-air to plunge straight down at high speed "
                    "(slower underwater), keeping half the sideways speed. Landing bounces him back up in his ball. "
                    "The numbers are Mania's own; there is nothing to tune. Bark uses it as his Slam Ground, with "
                    "shockwave projectiles (a \"shot\" with \"input\": \"slam\").",
        fields={},
        slots={"41": "the falling pose (an attack)"},
    ),
    "ray_glide": dict(
        name="Ray's Glide", kind="move", input="jump in mid-air, then hold it",
        description="Ray's flight from Sonic Mania Plus: press jump in mid-air to glide. Holding forward dives, letting "
                    "go swoops back up (each swoop a little weaker than the last). It ends when jump is released or he "
                    "slows down too much. Mania's own numbers; nothing to tune.",
        fields={},
        slots={"42": "gliding level", "47": "swooping up", "48": "diving down"},
    ),
    "rocket_ride": dict(
        name="Rocket Ride", kind="move", input="jump in mid-air, once per jump",
        description="Press jump in mid-air to ride a rocket forward, rising a little, as an attack. When the ride ends "
                    "it explodes: the blast launches him upward and hits everything around him. Running into a wall "
                    "blows it up early; getting hit or touching a spring ends it with no blast. Robotnik's move "
                    "(pair with Hover for his parachute afterwards).",
        fields={"ride_frames": ("frames", "How long the ride lasts."),
                "ride_speed": ("speed", "His minimum forward speed on the rocket (he keeps his own if faster)."),
                "ride_rise": ("speed", "How fast the rocket climbs."),
                "blast_launch": ("speed", "How hard the blast launches him upward."),
                "blast_radius": ("px", "How far around him the blast hits."),
                "blast_frames": ("frames", "How long the blast keeps hitting."),
                "blast_ticks": ("ticks", "How long each blast frame shows.")},
        sounds={"ride_sfx": "the rocket starting", "blast_sfx": "the explosion"},
        slots={"41": "the ride frames, then one frame per blast step (the code picks them)"},
    ),
    "ear_grapple": dict(
        name="Ear Grapple", kind="move", input="jump in mid-air (or Y with grapple_y)",
        description="An ear (or a hook) shoots out diagonally up and forward, a frame at a time. If its tip hits solid "
                    "ground it latches on and reels the character in, then lets go with a hop. Enemies and monitors it "
                    "touches are hit; if it reaches nothing it snaps back. Max's move. With grapple_y it's on Y instead "
                    "and the jump button opens the Hover at once (the Ear Copter); with grapple_refill a successful "
                    "latch or hit gives the grab back for chaining.",
        fields={"grapple_tip": ("list", "The ear's tip for each frame of slot 41, as [x, y] px from his centre facing "
                                        "right. This is how the code knows where the ear reaches.", "up to 8 frames"),
                "reel_speed": ("speed", "How fast he's reeled in to the latch point."),
                "reel_frames": ("frames", "The longest the reel can take."),
                "latch_range": ("px", "The reel stops this close to the latch point."),
                "grapple_hop": ("speed", "The upward speed of the hop when he lets go."),
                "grapple_forward": ("speed", "The forward speed of that hop."),
                "snap_frames": ("frames", "How fast the ear snaps back after a miss."),
                "grapple_y": ("bool", "Start the grapple with Y in mid-air (once per airborne period) instead of jump; "
                                      "jump then opens the Hover."),
                "grapple_refill": ("bool", "A latch or a badnik hit gives the Y grab back (a miss doesn't)."),
                "grapple_cooldown": ("frames", "With grapple_refill: the wait after a pull before the next grab.")},
        sounds={"grapple_sfx": "the ear shooting out", "latch_sfx": "the ear latching on"},
        slots={"41": "the ear growing out, one frame per grapple_tip entry (the code picks them)"},
    ),
    "spirit_flight": dict(
        name="Spirit Flight", kind="move", input="jump in mid-air",
        description="Press jump in mid-air: the character transforms into a glowing orb (held still for the "
                    "transformation), then flies wherever the d-pad points, 8 ways, with gravity off, for a limited "
                    "time. The orb is an attack. Landing, getting hit, a spring, running out of time or pressing jump "
                    "again ends it (Tikal).",
        fields={"spirit_transform": ("count", "How many frames of slot 41 are the transformation (the rest loop as "
                                              "the orb)."),
                "spirit_ticks": ("ticks", "How long each transformation frame shows."),
                "spirit_frames": ("frames", "How long the flight lasts."),
                "spirit_speed": ("speed", "The flying speed straight."),
                "spirit_diag": ("speed", "The flying speed per axis diagonally (about spirit_speed x 0.707)."),
                "spirit_accel": ("accel", "How quickly the orb eases toward that speed (lower floats more).")},
        sounds={"spirit_sfx": "the transformation"},
        slots={"41": "the transformation frames, then the orb's loop"},
    ),
    "triple_jump": dict(
        name="Triple Jump", kind="move", input="jump again right after landing, while running",
        description="Super Mario 64's triple jump: jumping again just after landing, while running fast enough, is the "
                    "next jump of a chain of three. The second and third jumps go higher, and the third is a "
                    "somersault. Rolling or getting hit breaks the chain. There is no mid-air move.",
        fields={"triple_window": ("frames", "How soon after landing the next jump must come."),
                "triple_speed": ("speed", "The ground speed he needs for the chain to continue."),
                "triple_jumps": ("list", "Two multipliers: the 2nd and 3rd jump's strength (1.0 = his normal jump).",
                                 "exactly 2 numbers")},
        slots={"41": "the third jump's somersault"},
    ),
    "screw_kick": dict(
        name="Screw Kick", kind="move", input="Y in mid-air (or jump with kick_jump)",
        description="A dive kick 45 degrees down and forward until landing, attacking all the way, then a small "
                    "bounce. Once per airborne period. Rouge does it on Y (also out of her glide). With kick_jump it's "
                    "the jump-button move instead: Mecha Sonic's Spike Ball and Sally's Flying Kick Dive.",
        fields={"kick_x": ("speed", "The dive's forward speed."),
                "kick_y": ("speed", "The dive's downward speed."),
                "kick_bounce": ("speed", "The bounce up on landing (0: he just lands)."),
                "kick_jump": ("bool", "Start the kick with jump in mid-air instead of Y.")},
        sounds={"kick_sfx": "the kick starting"},
        slots={"41": "the kick pose (an attack)"},
    ),
    "double_jump": dict(
        name="Double Jump", kind="move", input="jump in mid-air",
        description="A second jump in mid-air, spinning (an attack) until the character starts falling. Once per "
                    "airborne period, and again after a Wall Cling (Trip, Bean, Bomb).",
        fields={"double_jump": ("mult", "Its strength compared to the normal jump (0.85 is a little lower).")},
        slots={"41": "the second jump's spin (an attack)"},
    ),
    "wall_cling": dict(
        name="Wall Cling", kind="move", input="in the air, hold toward a wall",
        description="Holding toward a wall in mid-air makes the character cling to it, gravity off, for a while, then "
                    "slide down slowly. Up and down climb; climbing past the top hops onto the ledge. Jump kicks off "
                    "away from the wall; letting go of the direction drops off (Trip, Sticks, Ray Poward).",
        fields={"cling_frames": ("frames", "The longest she can stay on a wall."),
                "cling_hold": ("frames", "How long she holds still before starting to slide."),
                "cling_slide": ("speed", "How fast she slides down after that."),
                "climb_speed": ("speed", "Climbing speed up or down."),
                "wall_jump_x": ("speed", "The wall jump's speed away from the wall."),
                "wall_jump_y": ("speed", "The wall jump's upward speed."),
                "cling_lock": ("frames", "After letting go, how long before she can cling to that side again."),
                "ledge_hop": ("speed", "The upward speed of the hop onto a ledge at the top."),
                "ledge_forward": ("speed", "The forward speed of that hop.")},
        slots={"47": "clinging, drawn on a wall to her right"},
    ),
    "bat_glide": dict(
        name="Bat Glide", kind="move", input="Knuckles' glide",
        description="For a character built on Knuckles: his glide, made slower and floatier (a bat's wings). It's a "
                    "change to Knuckles' own glide and climb, not a new move (Rouge).",
        fields={"glide_speed": ("mult", "Glide speed compared to Knuckles' at every moment (0.7 = 70%)."),
                "glide_sink": ("speed", "The fall speed the glide settles at (Knuckles': 0x8000)."),
                "glide_gravity": ("accel", "How hard it pulls down toward that speed (Knuckles': 0x2000).")},
        needs=["base \"knuckles\""],
    ),
    "thunder_zip": dict(
        name="Thunder Zip", kind="move", input="jump in mid-air, once per jump",
        description="A lightning blink-dash: press jump in mid-air and the character zips forward in a flash, very "
                    "fast for a few frames (walls still stop her), then keeps a good forward speed with normal "
                    "gravity. The zip pose is an attack.",
        fields={"zip_frames": ("frames", "How long the zip itself lasts."),
                "zip_speed": ("speed", "The zip's speed."),
                "zip_carry": ("speed", "The forward speed she keeps afterwards, at least."),
                "zip_pose": ("frames", "How long the attacking zip pose shows in all.")},
        sounds={"zip_sfx": "the zip"},
        slots={"41": "the zip pose (an attack)"},
    ),
    "extreme_gear": dict(
        name="Extreme Gear", kind="move", input="jump in mid-air, then hold it",
        description="Sonic Riders' air surf: press jump in mid-air to snap onto a hoverboard and surf a fast, shallow "
                    "glide while jump is held. Forward speeds up, back brakes and carves round, up lifts him for a "
                    "while. The board rams badniks. Letting go, a wall, a hit, a spring or the ride's time limit ends "
                    "it; landing keeps him running at the board's speed (Jet).",
        fields={"gear_speed": ("speed", "The starting speed (he keeps his own if faster)."),
                "gear_top": ("speed", "The top speed with forward held."),
                "gear_accel": ("accel", "Speed gained each frame with forward held."),
                "gear_brake": ("accel", "Speed lost each frame with back held."),
                "gear_turn": ("speed", "Braking down to this speed carves him round to ride the other way."),
                "gear_recover": ("accel", "Speed regained each frame after turning, back up to gear_speed."),
                "gear_sink": ("speed", "The fastest he sinks while riding."),
                "gear_lift": ("accel", "Upward push each frame while up is held."),
                "gear_rise": ("speed", "The fastest he can rise."),
                "gear_lift_frames": ("frames", "How long up can lift him per ride."),
                "gear_frames": ("frames", "The longest a ride can last.")},
        sounds={"gear_sfx": "the board snapping on"},
        slots={"41": "the board coming out, then the ride's loop (an attack)"},
    ),
    "puddle_slide": dict(
        name="Puddle Slide", kind="move", input="jump in mid-air",
        description="Press jump in mid-air to drop fast (an attack). On landing the character melts into a puddle, "
                    "slides along the ground, then rises back up. Nothing hurts him while he's a puddle. A jump, a "
                    "roll, a spring, a ledge or a hit ends it (Chaos).",
        fields={"puddle_drop": ("speed", "The drop's speed, at least."),
                "puddle_frames": ("frame list", "Slot 42's frame for each step of the melt-slide-rise, in order.",
                                  "up to 40 steps"),
                "puddle_ticks": ("ticks", "How long each step lasts."),
                "puddle_speed": ("speed", "The slide's speed, at least, for the first puddle_move steps."),
                "puddle_move": ("count", "How many steps he keeps sliding before slowing to a stop.")},
        sounds={"puddle_sfx": "the melt / slide"},
        slots={"41": "the drop (an attack)", "42": "the puddle's melt, slide and rise frames"},
        needs=["with melee: melee_cooldown set (the slide holds Y off through it)"],
    ),
    "phase_warp": dict(
        name="Phase Warp", kind="move", input="jump in mid-air, once per jump",
        description="Press jump in mid-air: the character flickers out, vanishes and flickers back in up to a few "
                    "tiles away in the direction the d-pad points (8 ways; nothing held: ahead), never into or "
                    "through walls. He's untouchable throughout, then falls from there keeping his speed (Tails "
                    "Doll).",
        fields={"warp_range": ("px", "The farthest he warps.", "a multiple of 8"),
                "warp_vanish": ("frames", "How long the flicker out takes."),
                "warp_gone": ("frames", "How long he's gone."),
                "warp_appear": ("frames", "How long the flicker in takes.")},
        sounds={"warp_sfx": "the warp"},
        slots={"41": "the flicker pose (an attack)"},
    ),
    "rocket_burst": dict(
        name="Rocket Burst", kind="move", input="hold jump in mid-air, let go",
        description="Press jump in mid-air and keep holding it to charge a rocket pack, drifting down slowly. Let go "
                    "once it's charged to blast off where the d-pad points (8 ways), ricocheting off walls and "
                    "ceilings. With no direction held he does a Rocket Spin in place instead. It all attacks, the "
                    "charge too; letting go too early fizzles (Sparkster).",
        fields={"rocket_charge": ("frames", "How long jump must be held for a full charge."),
                "rocket_frames": ("frames", "How long the burst flies."),
                "rocket_speed": ("speed", "The burst's speed straight."),
                "rocket_diag": ("speed", "Its speed per axis diagonally (about rocket_speed x 0.707)."),
                "rocket_sink": ("speed", "The fastest he falls while charging."),
                "rocket_spin_frames": ("frames", "How long the Rocket Spin lasts."),
                "rocket_spin_ticks": ("ticks", "How long each spin frame shows.")},
        sounds={"rocket_charge_sfx": "the charge", "rocket_sfx": "the launch"},
        slots={"41": "11 frames: 0 charging, 1 the charged flash, 2-6 flying down, down-forward, forward, "
                     "up-forward, up; 7-10 the Rocket Spin"},
    ),
    # ------------------------------------------------------------------------------------------------- Y moves
    "melee": dict(
        name="Melee (Y attack)", kind="move", input="Y",
        description="The general Y-button move. On its own it's a short-range attack in front of the character, with "
                    "its reach set frame by frame (Fang's cork, Tikal's punch, Chaos' stretch punch). Add a \"shot\" "
                    "and Y throws a real projectile instead, the melee frames becoming the throw pose. Its options "
                    "turn it into many other moves: an all-round psychic wave (melee_radial), a burst of speed "
                    "(melee_boost: Mecha Sonic's Jet Boost), invisibility afterwards (melee_blink: Espio), a screen "
                    "nuke (melee_nuke: Tails Doll), a self-destruct that costs a hit (melee_cost: Bomb). Called \"popgun\" "
                    "before 2026-10: older files' popgun names still load (docs/character-json.md).",
        fields={"melee_reach": ("px list", "For each frame of slots 43 / 44: how far ahead of his centre the hit "
                                            "reaches (10 is about his own body). Its length is the move's frame "
                                            "count."),
                "melee_ticks": ("ticks", "How long each frame lasts."),
                "melee_stop": ("bool", "He stands still for it on the ground (in the air he keeps his speed)."),
                "melee_top": ("px list", "Per frame: the hit box's top, px from his centre (default -20)."),
                "melee_bottom": ("px list", "Per frame: the hit box's bottom, px from his centre (default 20)."),
                "melee_air_reach": ("px list", "A separate reach for the air version (slot 44), per frame."),
                "melee_air_top": ("px list", "The air version's box top per frame."),
                "melee_air_bottom": ("px list", "The air version's box bottom per frame."),
                "melee_radial": ("bool", "The reach goes all around him instead of only ahead (Silver's Psychic "
                                          "Wave)."),
                "melee_cooldown": ("frames", "The wait after the move before Y works again."),
                "melee_blink": ("frames", "After the move, the post-hit blink for this long: he can't be hurt "
                                           "(Espio's Leaf Swirl invisibility)."),
                "melee_boost": ("speed", "Turn the move into a burst of speed: at least this fast the way he faces, "
                                          "attacking (Mecha Sonic's Jet Boost, Bark's Bear Rush)."),
                "melee_safe": ("bool", "Nothing hurts him while the move lasts."),
                "melee_hang": ("bool", "In the air he hangs still during the move."),
                "melee_cost": ("bool", "When the move ends it hurts him like a normal hit (rings scattered; at 0 "
                                        "rings he dies). Bomb's Self-Destruct."),
                "melee_nuke": ("object", "A screen nuke during the move: {\"at\": frame it goes off, \"hit\": frames "
                                          "everything is hit, \"reach_x\" / \"reach_y\": the box round him in S1/S2, "
                                          "\"reach_cd\": CD's square reach, \"box\": S3&K uses the box too (else the "
                                          "whole screen), \"flash\": darkness 0-255 per frame (up to 32), \"sfx\", "
                                          "\"sfx_s3k\", \"sfx_cd\"}.")},
        sounds={"melee_sfx": "the move starting"},
        slots={"43": "the move on the ground"},
        optional_slots={"44": "the move in the air (with melee_air_reach it has its own frames)"},
    ),
    "shot": dict(
        name="Projectile (shot)", kind="setting", input="Y (or down + Y, up + Y, a charge, a landing)",
        description="A real projectile, thrown by the Y move: bullets, boomerangs, bouncing bombs, homing helpers, "
                    "falling critters, shockwaves. With \"melee\" in the abilities list its frames become the throw "
                    "pose. \"motion\" picks how it flies (bounce, straight, boomerang, drop, dip, ground, "
                    "homing), and its art is cut from your own sheet. \"shot2\" adds a second projectile on down + Y or "
                    "on a held charge (Robotnik's Bomb Drop, Mega Man's Charge Shot). Copy a character's whole \"shot\" "
                    "block as a starting point: every key is shown in the example.",
        fields={"shot": ("object", "The projectile: motion, speed, lifetime, max_alive, cooldown, pose, x, y, radius, "
                                   "art {sheet, drawing(s), ticks, hitbox, ...}, and per-game \"s3k\" / \"v4\" / \"cd\" "
                                   "overrides such as their \"sound\"."),
                "shot2": ("object", "A second projectile, with \"input\" \"down\" (down + Y) or \"charge\" (hold Y); "
                                    "needs a \"shot\" on Y alone."),
                "shot_breaks_walls": ("bool", "The shots break breakable walls (Mania only so far).")},
        needs=["\"input\" \"down\" or \"up\": \"melee\" too (Y alone stays the melee); with no melee, Y alone "
               "throws it (Flicky)", "\"input\" \"slam\": hammer_drop (thrown by its landing)"],
        game_notes={"s1": "Sonic 1/2 have room for 4 art frames (8 with \"two_rows\")",
                    "s2": "Sonic 1/2 have room for 4 art frames (8 with \"two_rows\")",
                    "mania": "shot_breaks_walls is read only by the Mania mod"},
    ),
    "melee_whip": dict(
        name="Whip Poses", kind="setting", input="Y with the d-pad",
        description="For a whip-like Y move: extra poses picked by the d-pad as Y is pressed: crouching, up-forward in "
                    "the air, and straight down in the air, each with its own reach box per frame (John Morris).",
        fields={"melee_whip": ("object", "{\"crouch\": {...}, \"up\": {...}, \"down\": {...}}, each {\"reach\", "
                                          "\"top\", \"bottom\"}: per-frame lists like melee_reach / melee_top / "
                                          "melee_bottom.")},
        slots={"41": "the crouching whip", "45": "the up-forward whip in the air", "46": "the downward whip in the air"},
        needs=["melee"],
        game_notes={"cd": "Sonic CD has only the standing and air whip (the melee itself), not these extra poses"},
    ),
    "melee_run": dict(
        name="Running Attack", kind="setting", input="Y while running",
        description="A second melee pose for Y pressed while running on the ground: its own frames and reach per "
                    "frame, and a boost that holds him at least that fast the way he faces while it lasts (Axel's "
                    "Grand Upper: a short dash ending in an uppercut). Y standing stays the plain melee.",
        fields={"melee_run": ("object", "{\"speed\": the least ground speed (either way) that counts as running, "
                                        "\"boost\": at least this fast while it lasts (0: none), \"reach\", \"top\", "
                                        "\"bottom\": per-frame lists like melee_reach / melee_top / melee_bottom, "
                                        "\"sfx_s3k\": its own S3&K / Mania sound (else melee_sfx_s3k's; \"own:<name>\" "
                                        "for one of the character's own sounds)}.")},
        slots={"45": "the running attack"},
        needs=["melee"],
        game_notes={"cd": "Sonic CD shows its frames after the melee's own (one melee animation there); its reach is "
                          "rounded down to a reach the enemy scripts already have"},
    ),
    "melee_up": dict(
        name="Up + Y Attack", kind="setting", input="up + Y on the ground",
        description="A second melee pose for up + Y on the ground (standing or looking up): its own frames and reach "
                    "per frame, all around him with \"radial\", and an optional cost in rings, taken as it starts "
                    "(with fewer rings, up + Y is the plain melee). Axel's Dragon Wing. In the air, Y is the Super "
                    "transformation first, as always.",
        fields={"melee_up": ("object", "{\"rings\": the rings it costs (0: free; fewer: the plain melee), \"radial\": "
                                       "true for a reach all around him, \"reach\", \"top\", \"bottom\": per-frame "
                                       "lists like melee_reach / melee_top / melee_bottom, \"sfx_s3k\": its own "
                                       "S3&K / Mania sound (else melee_sfx_s3k's; \"own:<name>\" for one of the "
                                       "character's own sounds)}.")},
        slots={"46": "the up + Y attack"},
        needs=["melee"],
        game_notes={"cd": "Sonic CD shows its frames after the melee's own (one melee animation there); its reach is "
                          "rounded down to a reach the enemy scripts already have; look up + jump (CD's melee input) "
                          "does it too"},
    ),
    "power_surge": dict(
        name="Power Surge", kind="move", input="Y",
        description="Y overcharges the character for a few seconds: faster, with her idle, walk and run swapped for "
                    "glowing Power Surge ones, and everything she touches is hit as if she were attacking (spikes "
                    "and projectiles still hurt). Then a cooldown before the next one.",
        fields={"surge_frames": ("frames", "How long the surge lasts."),
                "surge_cooldown": ("frames", "The wait after it before the next."),
                "surge_physics": ("object", "Multipliers during the surge, on top of her own physics: "
                                            "{\"top_speed\", \"acceleration\", \"air_acceleration\"}.")},
        sounds={"surge_sfx": "the surge starting"},
        slots={"50": "the surge idle", "51": "the surge walk", "52": "the surge run"},
    ),
    "spin_attack": dict(
        name="Spin Attack", kind="move", input="hold Y",
        description="Y on the ground or in the air starts a whirl that lasts while Y is held. It's an attack, floaty "
                    "in the air, and anything it hits bounces the character hard, pinball style. The spin leans with "
                    "her speed (Honey).",
        fields={"spin_frames": ("frames", "The longest a spin can last."),
                "spin_cooldown": ("frames", "The wait after it before the next."),
                "spin_ticks": ("ticks", "How long each spin frame shows."),
                "spin_gravity": ("count", "Gravity while spinning in the air, out of 256 (128 = half)."),
                "spin_bounce": ("speed", "The upward bounce off whatever she hits."),
                "spin_bounce_x": ("speed", "On the ground, the bounce away from what she hit."),
                "spin_lean": ("count", "How far the spin leans with her speed: 1/512 of a turn per px a frame."),
                "spin_lean_max": ("count", "The most it leans, in 1/512 turns (32 = 22.5 degrees).")},
        sounds={"spin_sfx": "the spin starting"},
        slots={"41": "the spin in the air (centred)", "43": "the spin on the ground (on her feet)"},
    ),
    "charge": dict(
        name="Charge", kind="move", input="hold Y on the ground",
        description="Hold Y on the ground: a shove, then a locked-direction push that builds far past his top speed. "
                    "Past his top speed enemies can't hurt him (hazards still do). Let go and he coasts back down; "
                    "holding back brakes to a stop. An attack the whole time, and a wall that stops him ends it. With "
                    "the spark_* numbers he also gets a Shine Spark: press down at full charge to store it (he glows), "
                    "then jump to launch up, up-forward or forward until something stops him (Heavy).",
        fields={"charge_shove": ("speed", "The speed Y shoves him to at once."),
                "charge_accel": ("accel", "The push added each frame..."),
                "charge_gain": ("count", "...plus this many 1024ths of his current speed each frame."),
                "charge_top": ("speed", "The charge's top speed."),
                "charge_friction": ("accel", "Speed lost each frame while coasting."),
                "charge_brake": ("accel", "Speed lost each frame holding back."),
                "charge_stride": ("px", "One running frame per this many px travelled."),
                "spark_store": ("frames", "Shine Spark: how long a stored spark lasts."),
                "spark_speed": ("speed", "Shine Spark: the launch speed."),
                "spark_skid": ("accel", "Shine Spark: the skid's braking each frame as he stores it."),
                "spark_skid_frames": ("frames", "Shine Spark: the longest the skid lasts."),
                "spark_glow_slots": ("list", "Shine Spark: his palette slots that glow."),
                "spark_glow_to": ("count", "Shine Spark: the colour they glow toward, as 0xRRGGBB."),
                "spark_glow": ("list", "Shine Spark: three glow amounts out of 256.")},
        sounds={"spark_store_sfx": "storing the Shine Spark", "spark_sfx": "launching it"},
        slots={"41": "running (one frame per charge_stride px)", "42": "coasting (Sonic CD and S3&K draw it from here)",
               "43": "past his top speed", "44": "coasting (Sonic 1/2)"},
        optional_slots={"45": "the Shine Spark launching up / up-forward",
                        "47": "the same Shine Spark pose for Sonic CD"},
    ),
    "high_kick": dict(
        name="Spin-Kick High Jump", kind="move", input="Y",
        description="Y on the ground or in the air: a short wind-up held still, then she's launched straight up, much "
                    "higher than a jump, somersaulting as an attack. At the top a recovery pose, then she falls as "
                    "from a jump with her jump ability ready. Once per airborne period in the air (Sally).",
        fields={"high_kick_windup": ("frames", "The wind-up before the launch."),
                "high_kick_rise": ("speed", "The launch speed upward."),
                "high_kick_ticks": ("ticks", "How long each kick frame shows."),
                "high_kick_recover": ("frames", "How long the recovery pose shows at the top."),
                "high_kick_cooldown": ("frames", "On the ground, the wait before the next.")},
        sounds={"high_kick_sfx": "the launch"},
        slots={"42": "2 frames: the wind-up and the recovery", "43": "the kick's somersault (an attack)"},
    ),
    "sink": dict(
        name="Shadow Sink", kind="move", input="down + Y on the ground",
        description="Down + Y on the ground: the character sinks into the ground, stays under for a while, then rises "
                    "back up. He doesn't move and nothing hurts him meanwhile; letting go of down or Y rises at once "
                    "(Mephiles).",
        fields={"sink_frames": ("frame list", "Slot 47's frames for sinking, in order (rising plays them backward).",
                                "up to 16"),
                "sink_ticks": ("ticks", "How long each sinking frame shows."),
                "sink_under": ("frame list", "Slot 47's frames while under, in turn.", "up to 8"),
                "sink_under_ticks": ("ticks", "How long each 'under' frame shows."),
                "sink_max": ("frames", "The longest he stays under."),
                "sink_cooldown": ("frames", "The wait after it before the next.")},
        sounds={"sink_sfx": "the sink"},
        slots={"47": "the sinking frames and the 'under' frames"},
    ),
    "ground_slide": dict(
        name="Slide", kind="move", input="down + jump on the ground",
        description="Down + jump on the ground (where the Spin Dash was) is a fast slide along the ground. Nothing "
                    "hurts him meanwhile, and he can't roll out of it. A jump, a spring, a ledge or a hit ends it (Ray "
                    "Poward, Mega Man). It uses the Puddle Slide's numbers.",
        fields={"puddle_frames": ("frame list", "Slot 42's frame for each step of the slide, in order.", "up to 40"),
                "puddle_ticks": ("ticks", "How long each step lasts."),
                "puddle_speed": ("speed", "The slide's speed, at least, for the first puddle_move steps."),
                "puddle_move": ("count", "How many steps he slides before slowing to a stop."),
                "slide_running": ("bool", "Down + jump slides out of a run too (Mega Man 3).")},
        sounds={"puddle_sfx": "the slide"},
        slots={"42": "the slide frames"},
    ),
    "star_grab": dict(
        name="Star Grab", kind="move", input="Y (aimed 8 ways)",
        description="Ristar's moves: Y stretches his arms out in any of 8 directions. A badnik caught: he's yanked in "
                    "to headbutt it and bounces off. A wall or ceiling caught: he's pulled in to hang there, climb, "
                    "and wind up a Meteor Strike by holding jump. Monitors and bosses the hands touch are hit. The "
                    "arms are drawn by the game as lines.",
        fields={"grab_step": ("px", "How far the arms stretch each frame."),
                "grab_frames": ("frames", "How long they stretch out."),
                "retract_frames": ("frames", "How long they take to come back."),
                "reel_speed": ("speed", "How fast he's pulled to a wall or ceiling."),
                "reel_frames": ("frames", "The longest that pull takes."),
                "latch_range": ("px", "The pull stops this close."),
                "yank_speed": ("speed", "How fast he's yanked to a caught badnik."),
                "yank_frames": ("frames", "The longest the yank takes."),
                "yank_range": ("px", "The yank stops this close."),
                "bounce_x": ("speed", "The bounce back off a badnik."),
                "bounce_y": ("speed", "The bounce up off a badnik."),
                "climb_speed": ("speed", "Climbing / moving along while hanging."),
                "hang_hop": ("speed", "The hop up when he lets go."),
                "hang_push": ("speed", "The push away from a wall when he lets go."),
                "windup_show": ("frames", "Jump held this long shows the Meteor Strike wind-up."),
                "windup_full": ("frames", "Jump held this long launches it on letting go."),
                "meteor_speed": ("speed", "The Meteor Strike's speed."),
                "meteor_frames": ("frames", "How long it flies.")},
        sounds={"grab_sfx": "the arms shooting out", "latch_sfx": "catching a wall", "meteor_sfx": "the Meteor Strike"},
        slots={"41": "the reaching, pulled, headbutt and Meteor Strike bodies",
               "42": "hanging: wall frames, ceiling frames, the wind-up", "43": "the loose hands"},
    ),
    "head_throw": dict(
        name="Head Throw", kind="move", input="Y (aimed 8 ways)",
        description="Dynamite Headdy's attack: Y throws his head out in any of 8 directions and it flies straight "
                    "back, hitting enemies, monitors and bosses on the way. His body stands headless meanwhile. A "
                    "badnik hit or a wall sends it back at once.",
        fields={"head_variants": ("list", "The heads: [{\"name\", \"step\" (px a frame), \"frames\" (frames out)}]; "
                                          "index 0 is his own head.", "1 to 8")},
        sounds={"head_sfx": "the throw"},
        slots={"41": "the headless throwing bodies (ground 0-4, air 5-9)", "43": "the flying head (out 0-4, back 5-9)"},
        game_notes={"mania": "partial: only his own head (index 0)"},
    ),
    "anchor_throw": dict(
        name="Anchor Throw", kind="move", input="Y (up + Y throws higher)",
        description="Y throws an anchor on a chain in an arc (up + Y throws it higher). It hits enemies, monitors and "
                    "bosses. If it bites into a wall or ceiling, it reels the character in to it; a floor or the end "
                    "of its range sends it back. The chain is drawn by the game (Marine).",
        fields={"anchor_speed": ("speed", "The throw's speed forward."),
                "anchor_rise": ("speed", "The throw's speed upward."),
                "anchor_high_speed": ("speed", "Up + Y: speed forward."),
                "anchor_high_rise": ("speed", "Up + Y: speed upward."),
                "anchor_gravity": ("accel", "How fast the arc falls back."),
                "anchor_frames": ("frames", "The longest it flies out."),
                "anchor_return": ("speed", "How fast it's pulled back."),
                "anchor_cooldown": ("frames", "The wait after it's back."),
                "reel_speed": ("speed", "How fast she's reeled in to a latch."),
                "reel_frames": ("frames", "The longest the reel takes."),
                "latch_range": ("px", "The reel stops this close."),
                "grapple_hop": ("speed", "The hop up at the end of the reel."),
                "grapple_forward": ("speed", "The hop's forward speed.")},
        sounds={"anchor_sfx": "the throw", "latch_sfx": "the anchor biting in"},
        slots={"41": "the throwing pose (an attack)", "43": "the anchor: flukes forward, up, down"},
    ),
    "treasure_sense": dict(
        name="Treasure Sense", kind="move", input="Y on the ground",
        description="Y on the ground: the character stops to listen, then a blinking ring at the screen's edge points "
                    "toward the nearest treasure (a giant ring or a monitor, depending on the game), blinking faster "
                    "the closer it is. Nothing nearby: a soft 'no signal' sound (Rouge).",
        fields={"sense_pause": ("frames", "How long she listens first (in her Looking Up pose)."),
                "sense_show": ("frames", "How long the marker shows."),
                "sense_cooldown": ("frames", "The wait after it before the next.")},
        sounds={"sense_sfx": "'no signal'"},
    ),
    "psycho_grab": dict(
        name="Psychokinesis", kind="move", input="Y with a badnik in reach",
        description="Y with a badnik in reach catches it (it's destroyed as a hit would) and the character carries its "
                    "likeness beside his hand; Y again throws it straight ahead through everything. Bosses and hazards "
                    "can't be caught. Nothing in reach: the normal Y move (Silver's Psychic Wave). The throw is his "
                    "\"shot\" with \"input\": \"grab\".",
        fields={"psycho_reach": ("px", "How far ahead it can catch."),
                "psycho_behind": ("px", "How far behind."),
                "psycho_height": ("px", "How far above or below."),
                "psycho_hold": ("frames", "How long the catch pose holds."),
                "psycho_throw": ("frames", "How long the throw pose shows."),
                "psycho_ticks": ("ticks", "How long each pose frame shows.")},
        sounds={"psycho_sfx": "the catch"},
        slots={"45": "the catch pose (hand out, the orb forming)"},
        needs=["melee (the Y move when nothing is in reach)", "a \"shot\" with \"input\": \"grab\""],
    ),
    "free_swim": dict(
        name="Free Swim", kind="move", input="the d-pad underwater; Y to ram",
        description="Underwater the character swims anywhere: he turns toward the d-pad and builds speed, gliding to "
                    "a stop with nothing held. Y is a charging ram (an attack). Leaving the water going up is a leap. "
                    "Ecco's move, drawn facing 8 directions so he's never flipped.",
        fields={"swim_speed": ("speed", "Top swimming speed."),
                "swim_accel": ("accel", "Speed gained each frame."),
                "swim_drag": ("accel", "Speed lost each frame with nothing held."),
                "swim_turn": ("deg", "How fast he turns toward the d-pad."),
                "swim_dirs": ("count", "Directions drawn.", "8"),
                "swim_cycle": ("count", "Frames per direction in slot 41."),
                "swim_ticks": ("ticks", "Game frames per swim frame at full speed (slower when slow)."),
                "ram_frames": ("frames", "How long the ram lasts."),
                "ram_speed": ("speed", "The ram's speed."),
                "ram_cooldown": ("frames", "The rest after a ram."),
                "ram_cycle": ("count", "Frames per direction in slot 42."),
                "leap_frames": ("count", "Frames of the leap in slot 43."),
                "leap_ticks": ("ticks", "How long each leap frame shows.")},
        sounds={"ram_sfx": "the ram"},
        slots={"41": "swimming: 8 directions x swim_cycle frames", "42": "the ram: 8 directions x ram_cycle frames",
               "43": "the leap"},
    ),
    "free_flight": dict(
        name="Free Flight", kind="move", input="jump (or Y) in mid-air; the d-pad steers; Y to drill; jump to let go",
        description="NiGHTS' flight: a jump press in mid-air (from a jump, a spring or a fall) or Y starts it, and the "
                    "d-pad steers him anywhere, turning toward it and building speed (he hangs in the air with "
                    "nothing held). A flight meter drains while he flies (not underwater), refills on the ground and "
                    "gets more with every ring; empty, he floats down. It's drawn at the top of the screen. Y in "
                    "flight is the Drill Dash (an attack, costing some meter). Flying a closed loop round enemies is "
                    "the Paraloop: everything inside the loop is hit. Underwater, flying level, he swims.",
        fields={"fly_speed": ("speed", "Top flying speed."),
                "fly_accel": ("accel", "Speed gained each frame the d-pad is held."),
                "fly_drag": ("accel", "Speed lost each frame with nothing held."),
                "fly_turn": ("deg", "How fast he turns toward the d-pad."),
                "fly_meter": ("frames", "The full meter: frames of flight."),
                "fly_drain": ("count", "Meter used each frame in flight."),
                "fly_refill": ("count", "Meter regained each frame on the ground."),
                "fly_ring": ("count", "Meter each ring adds."),
                "fly_sink": ("speed", "The fastest he falls once the meter is empty."),
                "fly_swim_frames": ("count", "Swim frames in slot 42, from frame 8."),
                "fly_swim_ticks": ("ticks", "Game frames per swim frame at full speed (slower when slow)."),
                "drill_frames": ("frames", "How long the Drill Dash lasts."),
                "drill_speed": ("speed", "The Drill Dash's speed."),
                "drill_cooldown": ("frames", "The rest after a Drill Dash."),
                "drill_cost": ("count", "Meter a Drill Dash uses."),
                "loop_points": ("count", "Path samples kept for the Paraloop.", "6 to 12"),
                "loop_every": ("frames", "Frames between path samples."),
                "loop_close": ("px", "How near his own path he must come back to close a loop."),
                "loop_min": ("px", "The smallest loop (width and height) that counts."),
                "loop_hit": ("frames", "How long a closed loop hits what's inside.")},
        sounds={"drill_sfx": "the Drill Dash"},
        slots={"41": "the Drill Dash: 4 frames", "42": "flight: 8 headings (0 right, counterclockwise), then the "
                                                      "swim cycle"},
    ),
    "voltteccer": dict(
        name="Voltteccer", kind="move", input="run to charge, then jump",
        description="Pulseman's Voltteccer: running fast on the ground for a moment charges him (a sound, and his colours "
                    "flash: the art's charge_palettes charge1). While charged, a jump press (on the ground or in mid-air) "
                    "turns him into an electric ball that flies off up-forward, gravity off, rebounding off walls, floors, "
                    "ceilings and anything that bounces him, an attack the whole time and untouchable, for a few seconds; "
                    "then he pops back out into his jump. Slowing down or a hit loses the charge. It takes the jump "
                    "ability: no other mid-air move alongside it.",
        fields={"volt_run": ("speed", "The ground speed that charges it."),
                "volt_charge": ("frames", "How long he must run that fast."),
                "volt_keep": ("speed", "Slower than this on the ground loses the charge."),
                "volt_speed": ("speed", "The ball's speed (diagonally, the same overall)."),
                "volt_frames": ("frames", "How long the ball lasts."),
                "volt_ticks": ("ticks", "Game frames per frame of the ball's loop.")},
        sounds={"volt_sfx": "the launch", "volt_ready_sfx": "the charge is ready"},
        slots={"41": "the ball: frames 0-3 its loop, 4-5 a smaller ball (as it starts and ends)"},
    ),
    "monitor_swap": dict(
        name="Monitor Swap", kind="move", input="breaking item monitors",
        description="Every item monitor the character breaks (by any means) moves him on to the next entry of a list, "
                    "looping. What an entry means is up to the move reading it: John Morris' sub-weapons, each its own "
                    "projectile in \"swap_shots\", thrown with up + Y and shown in a HUD icon.",
        fields={"monitor_swap": ("list", "The entry names, in order; the first at each stage's start.", "up to 8"),
                "swap_shots": ("object", "{entry name: a shot}: the projectile for each entry (\"input\": \"up\", "
                                         "\"rings\": the ring cost per throw)."),
                "swap_icon": ("bool", "Show the current entry's art at the top of the screen.")},
        sounds={"swap_sfx": "a swap"},
        needs=["swap_shots needs no \"shot\" / \"shot2\" of its own", "swap_icon needs swap_shots"],
    ),
    "ninjutsu": dict(
        name="Ninjutsu", kind="move", input="up + Y, after breaking a monitor",
        description="Breaking an item monitor (any way) stores one magic, picked at random from the \"ninjutsu\" list, "
                    "if none is held: at most one, kept until it's used (or the stage restarts). Its icon (the game's "
                    "own monitor art) shows at the top of the screen. Up + Y casts it (Y alone stays the Y move): "
                    "Ikazuchi gives a lightning shield (Sonic CD: the blue shield), Kariu hits everything on screen "
                    "with a dark flash, Fushin makes the jump higher for a while, and Mijin blows up everything around "
                    "him and then hurts him like a normal hit (Joe Musashi).",
        fields={"ninjutsu": ("list", "The magics a monitor can store, picked at random: any of \"ikazuchi\", "
                                     "\"kariu\", \"fushin\", \"mijin\"."),
                "ninja_cast": ("frames", "How long the cast pose lasts (slot 42); at most 63."),
                "ninja_cast_ticks": ("ticks", "How long each frame of the cast pose shows."),
                "ninja_mijin": ("frames", "How long Mijin's pose lasts (slot 48) before its cost; at most 63."),
                "ninja_mijin_ticks": ("ticks", "How long each frame of Mijin's pose shows."),
                "ninja_fushin": ("frames", "How long Fushin's higher jump lasts."),
                "ninja_fushin_jump": ("mult", "Fushin's jump strength compared to the normal jump."),
                "ninja_kariu": ("object", "Kariu's screen hit: {\"hit\": frames everything is hit, \"reach_x\" / "
                                          "\"reach_y\": the box round him in S1/S2 (px), \"reach_cd\": CD's square "
                                          "reach, \"flash\": darkness 0-255 per frame, \"sfx\", \"sfx_s3k\", "
                                          "\"sfx_cd\"} (S3&K and Mania: the whole screen)."),
                "ninja_mijin_blast": ("object", "Mijin's blast: {\"hit\", \"reach_x\", \"reach_y\", \"reach_cd\", "
                                                "the sounds}, no flash (Bomb's Self-Destruct).")},
        sounds={"ninja_sfx": "a magic stored", "ninja_cast_sfx": "the cast"},
        slots={"42": "the cast pose", "48": "Mijin's pose (he blows up)"},
        needs=["melee (Y alone; with a \"shot\" it's the projectile)", "not with monitor_swap"],
    ),
    "pot_magic": dict(
        name="Pot Magic", kind="move", input="up + Y, after breaking monitors",
        description="Every item monitor broken (any way) adds a magic pot, up to \"pots_max\", kept until used (or the "
                    "stage restarts); the pots show at the top of the screen, a picture each (slot 48). Up + Y spends "
                    "them all on the Earthquake (Y alone stays the Y move): the screen shakes (not in S3&K), a dark "
                    "flash, boulders fall and burst where they land (slots 45-47; not in Sonic CD), and everything in "
                    "a box round him is hit in waves. More pots: a wider box, more boulders, more waves (Gilius).",
        fields={"pots_max": ("count", "The most pots he can hold (1-7)."),
                "pots_levels": ("list", "One entry per pot count (1 pot, 2 pots...): {\"reach_x\" / \"reach_y\": the "
                                        "box round him in px (both 0: the whole screen), \"reach_cd\": Sonic CD's square "
                                        "reach, \"pulses\": waves of hits (a boss takes one hit per wave), \"rocks\": "
                                        "boulders per wave (0-8)}."),
                "pots_cast": ("frames", "How long the cast pose lasts (slot 42); at most 63."),
                "pots_cast_ticks": ("ticks", "How long each frame of the cast pose shows."),
                "pots_hit": ("frames", "How long each wave hits."),
                "pots_gap": ("frames", "The time from one wave to the next."),
                "pots_first": ("frames", "The time from the cast to the first wave's hit (the boulders' fall)."),
                "pots_shake": ("frames", "How long the screen shakes."),
                "pots_flash": ("list", "The flash: darkness 0-255 per frame (up to 32).")},
        sounds={"pots_sfx": "a pot added", "pots_cast_sfx": "the cast", "pots_quake_sfx": "the quake"},
        slots={"42": "the cast pose", "45": "the boulders (big, small)", "46": "a big boulder's burst (5 frames)",
               "47": "a small boulder's burst (5 frames)", "48": "a pot's picture (16x16)"},
        needs=["melee (Y alone)", "not with monitor_swap or ninjutsu"],
    ),
    "water_swim": dict(
        name="Swim Stroke", kind="move", input="jump in mid-air, underwater",
        description="Underwater, every jump press in mid-air is a swim stroke upward instead of the jump ability, as "
                    "often as the player likes (with a short delay between strokes). Out of water the normal jump "
                    "ability works (Big, Chaos).",
        fields={"swim_stroke": ("speed", "Each stroke's upward speed (a faster rise is kept)."),
                "swim_delay": ("frames", "The least time between strokes.")},
        slots={"47": "the stroke (not an attack)"},
    ),
    # ------------------------------------------------------------------------------------------------- passives
    "spike_shell": dict(
        name="Spike Shell", kind="passive", input="always on",
        description="Mighty's shell from Sonic Mania Plus: while curled up (jumping, spin dashing, Hammer Drop) spikes "
                    "don't hurt him; he's knocked up and back and blinks instead.",
        fields={},
    ),
    "magnetic": dict(
        name="Ring Magnet", kind="passive", input="always on",
        description="Rings nearby are pulled in, as by the lightning shield, all the time.",
        fields={},
    ),
    "no_breathing": dict(
        name="No Breathing", kind="passive", input="always on",
        description="The character never drowns: no air countdown, warning chimes or drowning music (robots, Chaos, "
                    "Marine, Ecco).",
        fields={},
    ),
    "breaks_walls": dict(
        name="Wall Breaker", kind="passive", input="always on",
        description="Breaks breakable walls like Knuckles, just by walking into them (Vector, Heavy, Omega).",
        fields={},
    ),
    "no_stomp": dict(
        name="No Stomp (Slide)", kind="passive", input="always on; down while running slides",
        description="The jump isn't an attack: he jumps in his own jump pose, and jumping into a badnik hurts him as "
                    "walking into it does (a shield, invincibility or Super still protects; bosses and monitors still "
                    "take the jump). His slide is the attack instead: rolling (down while running) and the Spin Dash's "
                    "release show his slide pose and break badniks and breakable walls as rolling does; with "
                    "ground_slide, that Slide breaks badniks, monitors and walls too, and hits bosses. In S3&K and "
                    "Mania the slides break walls as Knuckles does (Knuckles-only walls too). Joe Musashi, Ray Poward, "
                    "Mega Man, Axel, Gilius. Sonic 2, CD and S3&K's special stages show his jump pose (no ball).",
        fields={},
        optional_slots={"49": "the slide pose shown while rolling (flags \"roll\"); without it a roll shows his jump pose"},
        needs=["his own jump pose for \"Jumping\" (not the ball)",
               "a slide: a \"Rolling\" slide pose in slot 49 with flags \"roll\", or ground_slide (or both)"],
        game_notes={"cd": "with ground_slide, the Slide breaks walls through Object[5].PropertyValue: not with "
                          "breaks_walls, fire_immune or charge"},
    ),
    "fire_immune": dict(
        name="Fireproof", kind="passive", input="always on",
        description="Fire never hurts, as if the fire shield's protection were always on (Blaze).",
        fields={},
    ),
    "jewel_thief": dict(
        name="Jewel Thief", kind="passive", input="always on",
        description="10-ring monitors give 20 rings (Rouge).",
        fields={},
    ),
    "water_walk": dict(
        name="Water Walk", kind="passive", input="always on; down dives",
        description="Above water, the surface is solid ground: the character stands, runs, rolls and jumps on it. "
                    "Holding down dives through; she only lands on it from above (Marine).",
        fields={},
        game_notes={"mania": "partial: the stage's main water only, not separate pools (CPZ, HCZ)"},
    ),
    "physics": dict(
        name="Physics", kind="passive", input="always on",
        description="Changes the character's running and jumping: multipliers on Sonic's physics (1.0 = Sonic's). "
                    "Heavy characters get a lower top speed and slower acceleration; racers the opposite. Keep the "
                    "jump at 1.0 or above unless you've tested the levels: a lower jump can make some gaps impossible.",
        fields={"physics": ("object", "{\"top_speed\", \"acceleration\", \"air_acceleration\", \"jump\"}: multipliers "
                                      "(1.0 = Sonic's). Sonic 1/2 also take \"air_deceleration\", \"skid_speed\", "
                                      "\"rolling_friction\", \"jump_cap\".")},
    ),
    # ------------------------------------------------------------------------------------------------- settings
    "float_lean": dict(
        name="Floating Lean", kind="setting", input="(a drawing effect)",
        description="A drawing effect for a floating character: his walk and run are drawn tilted toward his travel, "
                    "more the faster he goes, and without the slope's rotation (Mephiles). The animations need full "
                    "rotation (\"rot\": 1).",
        fields={"float_lean": ("count", "How much he tilts: 1/512 of a turn per px a frame of speed."),
                "float_lean_max": ("count", "The most he tilts, in 1/512 turns (32 = 22.5 degrees).")},
    ),
    "ability_cycle": dict(
        name="Copycat Cycle", kind="setting", input="Y switches",
        description="Several jump abilities on one character, one active at a time: each Y press switches to the next "
                    "(with the melee's pose as the switch flash). Emerl's Copycat. Only double_jump, screw_kick "
                    "(with kick_jump), jet_dash and umbrella can be cycled.",
        fields={"ability_cycle": ("list", "The jump abilities in turn (each must also be in \"abilities\").",
                                  "2 to 4 of double_jump, screw_kick, jet_dash, umbrella"),
                "copy_heads": ("bool", "A head set per move. Python-only for now (Emerl's make_configs.py): a "
                                       "character.json can't make the heads yet.")},
        needs=["melee on Y, without melee_cooldown", "no hover and no umbrella_attack",
               "screw_kick only with kick_jump"],
        game_notes={"mania": "the head sets come from their own \"copy_heads\" data (ManiaMore.h), built from a "
                             "make_configs.py character"},
    ),
}
