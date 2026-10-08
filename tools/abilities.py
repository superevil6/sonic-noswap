"""Ability modules for extra characters, shared by the Sonic 1 and Sonic 2 builds.

Both games run the same Retro Engine v4 player script (Sonic 2's descends from Sonic 1's), so an
ability is written once here and patched into each game's Players/PlayerObject.txt.

Each extra lists its abilities in ABILITIES below (keyed by character ID). Available modules:
  jet_dash      press jump in mid-air: a horizontal burst of speed that attacks (anim slot 41)
  hover         keep holding jump after the dash: hover briefly, slowly sinking (anim slot 42); after a
                rocket_ride or ear_grapple, once he's falling
  rocket_ride   press jump in mid-air, once per jump: ride_frames on a rocket, at least ride_speed forward (his own
                speed kept if faster) and rising at ride_rise, an attack; then it explodes: the blast launches him up
                at blast_launch with half his speed along (not cut short by letting go of jump) and hits all around
                him (blast_radius) for blast_frames. A wall (his speed along falls under half of ride_speed) blows it
                up at once; a hit or a spring ends it with no blast. The code picks the frames (anim slot 41: the
                ride, then one blast frame per blast_ticks). Robotnik's (it was his Bomb Jump)
  ear_grapple   press jump in mid-air: an ear shoots out 45 degrees up and forward, growing a frame at a time
                (grapple_tip: its tip per frame, from the art). A tip in solid terrain latches: he's reeled in
                to it, then let go with a hop. Enemies and monitors the ear reaches are hit; with nothing
                there it snaps back. Once per jump (anim slot 41: the code picks the frames). With grapple_y it's
                started by Y in mid-air instead, once per airborne period, and a jump press in mid-air opens the
                hover (the Ear Copter) at once (Max's, the user's rework 2026-09-29). With grapple_refill a latch
                or a badnik the ear hits gives the grab back (a miss doesn't), grapple_cooldown frames after the pull
  pogo          press jump in mid-air: bounce on the tail, again on every landing while jump is held;
                attacks like a jump (anim slot 41)
  umbrella      press jump in mid-air: open an umbrella and drift down while jump is held (anim slot 42;
                slot 41, an attack, with umbrella_attack: Espio's Whirlwind)
  chaos_control press jump in mid-air: a flash (frozen), a quick warp dash, then a hop; attacks (anim slot 41)
  aim_dash      press jump in mid-air: a dash, straight or 45 degrees up/down if up/down is held when it
                starts (up_x / up_y override the up direction: Vector dashes straight up); attacks
                (anim slots 41 straight, 45 up, 46 down). With aim_dash_y it's started by Y instead, once
                per airborne period, and the jump ability stays the base character's (Charmy's Stinger)
  hammer_drop   Mighty's, from Mania Plus: press jump in mid-air to drop at 12 px per frame (8 underwater)
                with half the horizontal speed; landing bounces him up in his ball (anim slot 41 falling)
  ray_glide     Ray's, from Mania Plus: press jump in mid-air to fly; hold forward to dive, let go to swoop
                up (each swoop weaker than the last); ends on releasing jump or slowing down
                (anim slots 42 level, 47 up, 48 down)
  spike_shell   Mighty's, from Mania Plus: curled up (jump, Spin Dash, Hammer Drop), spikes don't hurt him;
                he's knocked up and back instead and blinks for a while
  melee         (optional melee_safe: nothing hurts him during the move, the post-hit blink's rule without the flicker)
  melee         (optional melee_hang: in the air he hangs still during the move, no speed and no fall)
  melee         (optional melee_cost: when the move ends it hurts him as a normal hit, through the game's own hurt: Sonic
                1/2 and CD Player_State_GotHit, S3&K the DLL calling the exe's Player_Hit; rings scattered, or a shield
                lost, and at 0 rings he dies. His own blink (melee_safe's) doesn't stop it; an invincibility star does, as
                with any hit; only in the game's free states. Bomb's Self-Destruct)
  melee         (optional melee_nuke {at, hit, reach_x, reach_y, reach_cd, flash, sfx...}: at the move's frame `at` the
                screen flashes black (a runtime fade: "flash", its darkness 0-255 per game frame; S1/S2 and CD SetScreenFade
                drawn by the nuke's object, S3&K the DLL darkening the palette banks) and for `hit` game frames everything
                on screen is hit: S1/S2 an invisible Tails Object in the shots' group (tools/shots_v4.py) with a box of
                reach_x x reach_y round him, CD one in a shot slot (tools/shots_v3.py) with a square reach_cd, S3&K the
                DLL's Player_CheckBadnikTouch hook for anything on screen; the game's own hit code does the rest. Tails
                Doll's Screen Nuke)
  melee         (optional melee_cooldown and melee_blink: after the move, the post-hit blink for that
                many frames, i.e. Espio's Leaf Swirl invisibility)
  melee         Y's attack that isn't a projectile: a hit a short way ahead (Tikal's punch), which hits enemies
                and monitors (anim slots 43, 44; the reach per frame is configured below). With
                melee_radial the reach is all around him instead (Silver's psychic sphere). With
                melee_air_reach the air move has its own frames and reach (and optionally melee_air_top: how far
                up the box reaches per frame); melee_stop: she stands still for it on the ground (Tikal's punch).
                melee_top / melee_bottom (and melee_air_bottom): the box's top / bottom per frame, px from his
                centre (default -20 / 20), for a thin beam (Gamma's Arm Cannon)
  spirit_flight press jump in mid-air: turn into a spirit orb (held still for the transform frames), then fly
                where the d-pad points (8 directions, gravity off) for spirit_frames; attacks. Ends on landing,
                a hit, a spring, running out of time or pressing jump again (anim slot 41: the transform, then
                the orb's loop)
  triple_jump   Super Mario 64's: a jump within triple_window frames of landing from the last one, while running
                (ground speed at least triple_speed), is the next of a chain of three: the 2nd and 3rd are higher
                (triple_jumps: their jump strength multipliers), and the 3rd somersaults (anim slot 41) until he
                starts falling. Then the chain starts over; rolling or a hit breaks it. No mid-air move
  screw_kick    Y in mid-air (also out of a glide): dive 45 degrees down and forward until landing, attacking,
                then a small bounce; once per airborne period (anim slot 41: Rouge's)
  double_jump   press jump in mid-air: a second jump (double_jump: its strength, a multiplier of the jump's), spinning
                (anim slot 41, an attack) until she starts falling; once per airborne period, and again after a wall_cling
  wall_cling    in the air, holding toward a wall right beside her (a tile at the point Knuckles' glide grabs): she
                clings (anim slot 47, drawn on a wall to her right), gravity off, for up to cling_frames, sliding down
                slowly after cling_hold. Up / down climb (climbing past the top hops her up onto the ledge); jump kicks off
                away from the wall; letting go of toward drops her. cling_lock frames away from a wall before she can
                cling to that side again. Landing, a hit or a spring ends it
  bat_glide     for an extra built on Knuckles: his glide, slower (glide_speed) and sinking more gently
                (glide_sink, glide_gravity): a patch in his glide states, not a module of its own
  thunder_zip   press jump in mid-air: a blink-dash forward in a flash, zip_frames at zip_speed (the game's collision
                stops it at walls), vertical speed 0, then her forward speed along (at least zip_carry) and normal
                gravity; attacks for zip_pose frames (anim slot 41); once per jump
  power_surge   Y, on the ground or in the air: surge_frames of an overcharge (surge_physics: multipliers on top of her
                own), her idle / walk / run shown as Power Surge ones (anim slots 50-52, only while animating and
                drawing), and everything she touches is hit, as if she were attacking (enemies, monitors, bosses; spikes
                and projectiles still hurt her). Then surge_cooldown frames before the next one
  extreme_gear  Sonic Riders' air surf: press jump in mid-air, once per jump, to snap onto a hoverboard (anim slot 41, an
                attack: the board rams badniks; its frames: the board out, then the ride's loop) and surf a fast, shallow
                glide while jump is held: at least gear_speed forward from the press (kept if faster), speeding up by
                gear_accel per frame to gear_top with forward held; back brakes by gear_brake per frame, and at gear_turn
                he carves round to ride the other way (back up to gear_speed by gear_recover per frame). Sinking at
                gear_sink at most; up held lifts him (gear_lift per frame, rising at gear_rise at most) for
                gear_lift_frames per ride. Letting go of jump, gear_frames of riding (a ride's length at most: it ends
                as letting go does), a wall, a hit, a spring or the melee ends it; landing too, running at the board's
                speed
  puddle_slide  press jump in mid-air: drop (at least puddle_drop, anim slot 41, an attack); landing from it, melt into a
                puddle and slide along the ground, then rise back up (anim slot 42; puddle_frames: its frame per step of
                puddle_ticks game frames): at least puddle_speed the way he faces for puddle_move steps, then slowing to
                a stop. Nothing hurts him meanwhile (the post-hit blink's rule, without the flicker), and Y doesn't
                punch (needs melee_cooldown). A jump, roll, spring, ledge or hit ends it. Once per jump (Chaos)
  ground_slide  down + jump on the ground (a crouch's jump, where the Spin Dash was: his spindash action): a slide along the
                ground, Chaos' Puddle Slide's ground part started at once (the puddle_* numbers, slot 42, nothing hurts him
                meanwhile), and no roll out of it (NoSwap_RollAllowed). A jump, spring, ledge or hit ends it (Ray Poward's)
  no_stomp      the jump isn't an attack: in the air in his jump pose a badnik hurts him as walking into it does (shields,
                invincibility and Super still protect; bosses and monitors still take the jump). His slide is the attack:
                the roll and the Spin Dash's release shown in his "Rolling" slide pose (extras.py "roll", slot 49) break
                badniks and walls as rolling does; with ground_slide, the Slide breaks badniks, monitors and walls too, and
                hits bosses (S1/S2: Player_BadnikBreak / Player_CheckHit, NoSwap_flags' surging and breaks_walls bits while
                it slides; CD: build_soniccd.cd_no_stomp, touch_attack, Object[5].PropertyValue; S3&K: the DLL's
                NoStomp* around Player_CheckBadnikBreak / _CheckBossHit / ItemBox_CheckHit, walls AsKnuckles; Mania:
                native/mania/src/ManiaNoStomp.h). Joe Musashi, Ray Poward, Mega Man, Axel, Gilius (the user, 2026-10-02)
  spin_attack   Y on the ground or in the air: a whirl while Y is held (spin_frames at most, then spin_cooldown), an
                attack; floaty in the air (gravity at spin_gravity / 256), and anything it breaks or hits bounces her
                hard: up at spin_bounce, and away at spin_bounce_x on the ground (anim slots 41 in the air, 43 on the
                ground; one frame per spin_ticks). Honey's
  charge        Y held on the ground: a shove to charge_shove at once, then a locked-direction push far past his top
                speed (charge_accel plus charge_gain / 1024 of his speed a frame, up to charge_top), and while it's past
                his top speed enemies can't hurt him (hazards still do: noswap_common.juggernaut, build_soniccd.
                cd_juggernaut, the DLL's jugg hooks); let go, he coasts, losing charge_friction a
                frame until he's back at his top speed; holding back (Y or not) brakes, charge_brake a frame, to a
                full stop that ends it (he stands; Y let go and pressed again for a new one). An attack throughout; a wall that
                stops him, a jump (keeping the speed), a ledge, a roll or a hit end it (anim slots 41 running, 43 past
                his top speed, 44 coasting; one frame per charge_stride px). With "spark_*" numbers, its Shine Spark:
                down past his top speed stores it (a glow, spark_store frames), jump launches it up / up-forward /
                forward at spark_speed until the terrain stops him (slot 45; spark_after, spark_air). Heavy's
  high_kick     Y on the ground or in the air: a wind-up (high_kick_windup frames, held still, not an attack: anim slot 42
                frame 0), then she's launched straight up at high_kick_rise (higher than her jump; her speed along held at
                0, and letting go of jump doesn't cut it short), an attack in the kick's frames (slot 43, one per
                high_kick_ticks, in turn) while she rises; at the top, high_kick_recover frames of a recovery pose (slot 42
                frame 1, not an attack, normal air control), then she falls as from a jump (in the jump ball, her jump
                ability ready). Once per airborne period if started in the air; after it, high_kick_cooldown frames on the
                ground before the next. A hit, a roll or an object taking over ends it. Sally's Spin-Kick High Jump
  water_swim    underwater, a jump press in mid-air (in the jump or a stroke) is a swim stroke instead of the jump ability:
                up at swim_stroke (a faster rise is kept; letting go of jump doesn't cut it short), at most one every
                swim_delay frames, unlimited (anim slot 47 "Swim", not an attack; CD 48, S3&K extra 5). It takes the
                jump ability for the rest of that jump. Underwater: S1/S2 player.gravityStrength 0x1000, CD
                Player.GravityStrength 0x1000 (the Water scripts set them), S3&K gravity under 0x3800 (the DLL). Big's
  phase_warp    press jump in mid-air, once per jump: he flickers out (warp_vanish frames), is gone (warp_gone) and flickers
                back in (warp_appear), held still and untouchable throughout (the post-hit blink's rule; hidden by his
                visibility, not the blink); as he goes he moves up to warp_range px where the d-pad points (8 ways, nothing
                held: ahead), 8 px at a time (the diagonal's share per axis), stopping before the first step where a point
                of his body (the centre, 13 px up / down, 8 px either side) is in solid terrain: never into or through it
                (S1/S2 / CD ObjectTileCollision on floors, S3&K floors and ceilings). Then his speed along from before, and
                he falls from there (anim slot 41 for the flicker, an attack). Tails Doll's
  rocket_burst  press jump in mid-air, once per jump, and keep holding it to charge a rocket pack (drifting, falling at
                rocket_sink at most; slot 41 frame 0, flashing with frame 1 once charged: rocket_charge frames); let go to
                fire: where the d-pad points (8 ways) at rocket_speed (rocket_diag per axis diagonally), gravity off, for
                rocket_frames, bouncing off walls and ceilings (a ricochet: that axis reversed), in the Rocket Dash frame for
                its angle (2-6); with nothing held, the Rocket Spin in place for rocket_spin_frames (7-10, one per
                rocket_spin_ticks). An attack throughout (the charge too); let go too soon, it fizzles. Landing, a hit or a
                spring ends it; after the burst he falls with half its speed. Sparkster's
  sink          down + Y on the ground (standing, walking or crouching; not rolling or hurt): he sinks into the ground
                (anim slot 47, CD 48, S3&K extra 5: sink_frames, one per sink_ticks game frames), stays under
                (sink_under's frames in turn, sink_under_ticks each) for sink_max frames at most, then rises (sink_frames
                backward); letting go of down or Y rises at once, from the frame he's at. Throughout he doesn't move
                (speed 0, no input: S1/S2 / CD Player_State_Static, S3&K his input cleared) and nothing hurts him (the
                post-hit blink's rule without the flicker); a spring, an object or a hit that gets through ends it. Then
                sink_cooldown frames before the next. Down + Y on the ground never throws the shot. Mephiles' Shadow Sink
  magnetic      always on: rings within 64 px are pulled in, as by the lightning shield (the Ring scripts)
  no_breathing  never drowns: skips the air countdown in every water script (S3&K: the DLL keeps the player's drown timer,
                +0x1C0, at 0 each frame, so the warning chimes, the countdown numbers and music never start)
  breaks_walls  breaks walls like Knuckles, by walking into them (S1/S2: NoSwap_flags bit 5, the BreakWall scripts'
                Knuckles branch copied for it, noswap_common.knux_like; CD: Object[5].PropertyValue 1, set at startup,
                build_soniccd.cd_break_walls; S3&K: the DLL shows the BreakableWall, AIZRockPile, RockPile and IceColumn
                objects Knuckles' character ID while they update: AsKnuckles)
  fire_immune   fire never hurts, as if the fire shield were always on (only its immunity): S1/S2's Player_FireHit (every
                fire hazard calls it) skips the extra, and the lava tiles' own shield tests (S1 MZSetup, S2 MBZSetup:
                apply_fire_tiles) read NoSwap_flags bit 6; CD (no fire shield): R3's and R8's fireballs skip Player_Hit
                when Object[5].PropertyValue is 2 (build_soniccd.cd_fire_hit); S3&K: the DLL's Player_FireHurt hook and
                AsFireShield wrappers
  star_grab     Ristar's: Y stretches his arms out 8 ways (a badnik caught: yanked in to headbutt it; a wall or ceiling:
                pulled in to hang, climb, and wind up the Meteor Strike on held jump). All in tools/star_grab.py (S1/S2 and
                CD code, the numbers; the DLL's native/src/StarGrab.h)
  head_throw    Dynamite Headdy's: Y throws his head 8 ways, out and straight back, hitting enemies, monitors and bosses
                ("head_variants": the power-up heads, index 0 his own). All in tools/head_throw.py (S1/S2 and CD code;
                the DLL's native/src/HeadThrow.h)
  anchor_throw  Marine's: Y throws an anchor in an arc on a chain (the chain drawn at runtime; up + Y higher), hitting enemies,
                monitors and bosses; a wall or ceiling it bites into reels her in (Max's reel), a floor or its range sends
                it back. All in tools/anchor_throw.py (S1/S2 and CD code; the DLL's native/src/AnchorThrow.h)
  water_walk    the water's surface is ground for her above water (stand, run, roll, jump on it); down dives through it,
                and she only lands on it from above. All in tools/water_walk.py (the DLL's native/src/WaterWalk.h)
  treasure_sense Rouge's: Y on the ground, a short listening pause, then a blinking ring at the screen's edge toward the
                nearest treasure (faster the closer it is; S1 / CD the giant ring, else monitors; S2 monitors; S3&K hidden
                giant rings), drawn in monitor_swap's HUD-layer pass. All in tools/treasure_sense.py (S1/S2 and CD code;
                the DLL's native/src/TreasureSense.h)
  jewel_thief   Rouge's: 10-ring monitors give her 20 (S1/S2/CD BrokenMonitor's NoSwap_RingMonitor; the DLL's ItemBox
                powerup hook). tools/treasure_sense.py
  melee_whip    (the melee's) John Morris' whip poses by the d-pad as Y is pressed: {"crouch" (on the ground, crouching:
                slot 41), "up" (in the air, up and a side held: slot 45), "down" (in the air, down held: slot 46)}, each
                {"reach", "top", "bottom"} per frame, as melee_reach / melee_top / melee_bottom (S1/S2: NoSwap_whipAim
                and the NoSwap_MeleePose rows 2-4; the DLL: the same animations; CD: the standing / air whip only)
  melee_run     (the melee's) a running pose: Y while running on the ground (at least its "speed") shows slot 45 with
                its own "reach" / "top" / "bottom" per frame, held at least its "boost" the way he faces (Axel's Grand
                Upper). S1/S2: NoSwap_whipAim 4, NoSwap_MeleePose row 5; CD: after the melee's frames in 46; the DLL /
                Mania: meleeRun*. Rules: check_variants
  melee_up      (the melee's) an up + Y pose on the ground: slot 46, its own reach ("radial": all round him), costing
                "rings" as it starts (fewer: the plain melee; Axel's Dragon Wing). S1/S2: NoSwap_whipAim 5, row 6
  monitor_swap  every item monitor the extra breaks (by any means) moves an index on through its "monitor_swap" list
                (tools/monitor_swap.py, all four games); "swap_shots" {entry: shot config}: the shot thrown is the current
                entry's (John Morris' sub-weapons: swap_shots below)
  ninjutsu      Joe Musashi's: an item monitor broken stores one magic (random among the "ninjutsu" list, at most one
                held, shown in monitor_swap's HUD icon box with the game's own monitor art); up + Y casts it: Ikazuchi (the
                lightning shield; CD the blue one), Kariu (a screen nuke with its flash), Fushin (a higher jump for a
                while), Mijin (Bomb's half-screen blast, then a normal hit on him). All in tools/ninjutsu.py (S1/S2 and CD
                code; the DLL's native/src/Ninjutsu.h, Mania's native/mania/src/ManiaNinjutsu.h)
  pot_magic     Gilius Thunderhead's: every item monitor broken adds a magic pot (up to "pots_max", shown in the HUD
                icon box, a picture each); up + Y spends them all on the Earthquake: a shake, a flash, boulders, and
                waves of hits on everything in a box round him, wider and more waves with more pots. All in
                tools/pot_magic.py (S1/S2 and CD code; the DLL's native/src/PotMagic.h, Mania's
                native/mania/src/ManiaPotMagic.h)
  physics       multipliers applied to Sonic's physics table (top speed, acceleration, ...)
  float_lean    (a number, not a module: set it to use it) a draw effect: the walk and run (and S3&K's jog, dash, peel out
                and their angled ones) are drawn turned toward his travel, float_lean / 512 of a turn per px per frame of
                his speed (ground speed; in the air his x speed), float_lean_max at most, and without the slope's rotation
                (a floating character). The animations need full rotation ("rot" 1; S3&K: build_s3k_art.py gives the
                walk / run full rotation for such an extra). Mephiles'

"ability_cycle": [moves] (Emerl's Copycat): several jump abilities, one active at a time. The jump ability is the active
one's (NoSwap_Copycat<i>; S1/S2 NoSwap_copyMove, CD NoSwap.CopyMove, S3&K the DLL's g_copy: its place in the list, 0
at each stage load); each Y press that starts the melee (its pose is the switch pose, slots 43 / 44) makes the next one
active, and in the air ends the move used this jump (noswapAbility -1: nothing more this jump; a jump whose move wasn't
used yet can use the new one). Each move's air and after-update code runs only while it's the active one. The attack
moves share slot 41: its frame k is the cycle's move k (the code picks it, speed 0). CYCLE_MOVES are the ones supported.
"copy_heads": true (with an ability_cycle): a head set per move (Emerl's: testmods/emerl/make_configs.py add_copy_heads),
slots COPY_HEAD_SLOT + COPY_HEAD_STRIDE * move + place in COPY_HEAD_ANIMS (idle, stance, walk, run, peel out, the switch
poses); the active move's copy is shown in place of the game's own only while animating and drawing (copy_head_in_out;
CD build_soniccd.cd_copy_heads, one slot on; S3&K the DLL's CopyHeadShow, build_s3k_art.py COPY_HEADS_S3K).

The engine only takes so much script code per stage: a module several extras have (melee, umbrella, aim_dash, the
hover after rocket_ride / ear_grapple) is one shared function reading the playing extra's numbers from tables
(extra_table), not a copy per extra. A module only one extra has keeps its numbers in its code.
"""
import os
import re
import sys

from noswap_common import FLAG_BITS, flag_test, free_temp, guard_blocks, kept_extras, line_indent, patch, patch_n
from extras import EXTRAS, REPO, player_ani, startup_case
import character_json  # (characters defined by a character.json: docs/character-json.md)

KIT = bool(os.environ.get("NOSWAP_KIT"))  # the Creator Kit: NoSwap's own characters aren't there (tools/extras.py)


def _id_of(folder):
    """The build ID of NoSwap's character in testmods/<folder> (entries below keyed by it). In the Creator Kit he isn't
    there: a placeholder key, dropped after the table (only the creator's characters are built)."""
    i = next((e["id"] for e in EXTRAS if e["art"].name == folder), None)
    if i is None:
        if not KIT:
            raise SystemExit(f"abilities.py: no extra in testmods/{folder}")
        return f"absent:{folder}"
    return i


def _json_entry(folder):
    """character_json.abilities_entry for NoSwap's own testmods/<folder> (absent in the Creator Kit: nothing)."""
    if KIT and not (REPO / "testmods" / folder / character_json.FILE).exists():
        return {"abilities": []}
    return character_json.abilities_entry(REPO / "testmods" / folder)

# Animation slots for ability moves, after the base characters' 39 (Amy's hammer uses 39-40)
ANI_ATTACK = 41  # an extra's attacking move (Jet Dash, Pogo); enemies treat it like rolling
ANI_HOVER = 42
ANI_MELEE = 43  # on the ground; the .ani frames draw the cork flying out
ANI_MELEE_AIR = 44
ANI_ATTACK_UP = 45  # aim_dash up / down (extras without these moves don't have the slots)
ANI_ATTACK_DOWN = 46
ANI_GLIDE_UP = 47  # ray_glide's up / down poses (not attacks; slot 42 is the level glide)
ANI_GLIDE_DOWN = 48
ANI_CLING = 47  # wall_cling (an extra without ray_glide: its glide-up slot)
ANI_ROLL = 49  # an extra's own rolling curl (extras.py "roll"), shown instead of its jump while rolling
ANI_SURGE = {"idle": 50, "run": 51, "sprint": 52}  # power_surge's idle / walk / run (shown in place of the game's)
ATTACK_ANIMS = ["ANI_NOSWAP_ATTACK", "ANI_NOSWAP_MELEE", "ANI_NOSWAP_MELEE_AIR", "ANI_NOSWAP_ATTACK_UP",
                "ANI_NOSWAP_ATTACK_DOWN"]

ABILITIES = {
    7: {  # extra 1: Metal Sonic
        "abilities": ["jet_dash", "hover", "no_breathing", "physics"],
        # 20 frames at a fixed 6 px per frame from the first frame, like a homing attack
        # (or his current speed, if he's already going faster). 24 frames at 12 px was too strong.
        "dash_frames": 20, "dash_speed": 0x60000,
        "hover_frames": 60, "hover_sink": 0x4000,
        # heavier than Sonic: faster top speed, slower to accelerate. Jump stays Sonic's: at 0.92 he
        # couldn't clear a jump in Hill Top Zone 2.
        "physics": {"top_speed": 1.1, "acceleration": 0.8, "air_acceleration": 0.85},
    },
    8: _json_entry("fang"),
    9: {  # extra 3: Big (testmods/big/make_configs.py: DBurraki's sheet, 2026-09-28)
        # water_swim first: underwater his mid-air jump press is a swim stroke; out of water, the parasol
        "abilities": ["water_swim", "umbrella", "melee", "physics"],
        "umbrella_sink": 0xC000,  # fall speed under the umbrella (Sonic falls up to 16 px per frame)
        # Water swim (the user's design, 2026-09-28): underwater, each jump press in mid-air (in the jump or a stroke) is
        # a stroke: up at 3 px per frame (a faster rise is kept), at most one every 14 frames, as often as he likes
        # (slot 47 "Swim": arms and legs paddling; not an attack). Letting go of jump doesn't cut a stroke short.
        "swim_stroke": 0x30000, "swim_delay": 14,
        # (The melee numbers are only the Fishing Cast's pose, slots 43 / 44: the rod swung back, then the line up over
        # his head; the pose is their last frame. And S3&K's fallback melee if its shot system is off, which reaches no
        # further than his body.) He plants his feet to cast on the ground; in the air he keeps his speed
        "melee_sfx": "Release", "melee_sfx_s3k": "Global/Release.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        "melee_stop": True,
        # Fishing Cast (the user's design, 2026-09-28): a real projectile in all four games, motion "straight" and aimed
        # with the d-pad as Y is pressed, Gamma's, but 5 directions on the ground AND in the air ("aim_down": false: down
        # never aims): back, back-up, up, forward-up, forward; nothing held: the way he faces. 6 px per frame (diagonals
        # the same overall), no gravity, a short cast: 20 frames (about 120 px); gone at a wall, floor or ceiling it flies
        # into, offscreen or at its first hit. One out at a time, 2 s (120 frames) apart. It starts 24 px out along the aim
        # from 12 px above his centre. The pose shows 12 frames, over whatever he's doing ("pose_always", the user's call,
        # 2026-09-28: running, he runs on in it; in the air it replaces the jump ball too, then what showed comes back;
        # rolling on the ground, no pose). Art: the sheet's loose lures (the green and gold lure at
        # the line's end, 5x6 / 6x5, drawn at three angles in the attacks and fishing sections: "drawings", cut exactly),
        # tumbling, a frame every 4 game frames; hitbox 16x16 (the lure is tiny). Sound: the Release whoosh
        "shot": {
            "motion": "straight", "aim": True, "aim_down": False, "speed": 0x60000, "lifetime": 20, "max_alive": 1,
            "cooldown": 120, "pose": 12, "x": 24, "y": -12, "radius": 4,
            "pose_always": True,
            "art": {"sheet": "../Big2.png", "drawings": [[734, 419, 5, 6], [220, 628, 5, 6], [30, 640, 6, 5]],
                    "own_slots": True, "ticks": 4, "hitbox": [-8, -8, 8, 8]},
            "s3k": {"sound": "Global/Release.wav"},
            "v4": {"sound": "Release"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # heavy: slow to get going, lower top speed, but a big jump
        "physics": {"top_speed": 0.85, "acceleration": 0.7, "air_acceleration": 0.8, "jump": 1.08},
    },
    10: {  # extra 4: Shadow (Chaos Control is the user's idea; numbers from testmods/shadow's proposal)
        "abilities": ["chaos_control", "melee", "physics"],
        "chaos_freeze": 6, "chaos_warp": 12, "chaos_speed": 0x50000, "chaos_pop": 0x48000,
        # Chaos Spear throw pose (slots 43 / 44, CD 46: the wind-up, then the throw, arm out; his config's spear()). Only
        # the pose (its last frame) and S3&K's fallback melee if its shot system is off, which reaches no further than
        # his body
        "melee_sfx": "Lightning Jump",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        # Chaos Spear (a real projectile in all four games, motion "straight": Gamma's, not aimed): a bolt the way he
        # faces, level, 8 px per frame, no gravity; gone at a wall, after 40 frames, offscreen or at its first hit; 2 out
        # at once, 2 s (120 frames) apart (the user: he levelled bosses too fast). It starts 16 px ahead of him, 4 px above his centre (his hand). He keeps his speed
        # (no stop). The throw pose for 10 frames. Art: a loose jet-flame streak from his own sheet (ShadowMegamix.png,
        # 359,178 15x9: a red and yellow zigzag, his own colours), cut exactly and mirrored with him; hitbox 14x14 (Sonic 1/2 take a square).
        # Sound: the Lightning Shield's jump spark (S3&K, S1/S2); Sonic CD has none: the shield monitor's
        "shot": {
            "motion": "straight", "speed": 0x80000, "lifetime": 40, "max_alive": 2, "cooldown": 120,
            "pose": 10, "x": 16, "y": -4, "radius": 5,
            "art": {"sheet": "../ShadowMegamix.png", "drawing": [359, 178, 15, 9], "turns": ["none"], "ticks": 2,
                    "hitbox": [-7, -7, 7, 7]},
            "s3k": {"sound": "Global/LightningJump.wav"},
            "v4": {"sound": "Lightning Jump"},
            "cd": {"sound": "SFX_G_SHIELD"},
        },
        "physics": {"top_speed": 1.05, "acceleration": 0.95},
    },
    12: {  # extra 6: Silver (psychic float and wave: numbers from testmods/silver's proposal)
        "abilities": ["umbrella", "melee", "physics", "psycho_grab"],
        "umbrella_sink": 0x6000,  # half Big's: a slow psychic float
        "float_frames": 120,  # at most 2 seconds per jump, so it isn't flight
        "melee_sfx": "Insta Shield",
        # Psychic Wave: hand out, then the sheet's psychic sphere swells around him (55 x 47): the
        # hit area is the sphere, all around him (the user asked to see the attack's range)
        "melee_reach": [10, 28, 28, 28, 28, 28, 28, 28],
        "melee_radial": True,
        "melee_ticks": 3,
        "physics": {"top_speed": 0.95, "acceleration": 0.95, "jump": 1.02},
        # Psychokinesis (the user's design, 2026-09-30; S3&K first: native/src/PsychoGrab.h): Y with a badnik in reach
        # (psycho_reach px ahead, psycho_behind behind, psycho_height above or below; the nearest on screen) catches it
        # instead of the Psychic Wave: it's destroyed as a hit would (points, animal, explosion), he stops for psycho_hold
        # frames (slot 45: his hand out, the orb forming), then carries its likeness beside his hand as he plays on
        # (the user: "hold onto it until the Y button is clicked again"); Y again: psycho_throw frames of the pose, then
        # it's thrown forward as a shot (below) drawn as the badnik was. A hit or a stage change loses it. Bosses, their
        # parts and hazards can't be caught (the object's own code decides: a catch that isn't a badnik's break is
        # refused, nothing hurts him); nothing in reach: the Psychic Wave as before
        "psycho_reach": 112, "psycho_behind": 16, "psycho_height": 64, "psycho_hold": 12, "psycho_throw": 6,
        "psycho_ticks": 3,
        "psycho_sfx_s3k": "Global/Charge.wav",
        # the thrown badnik: straight ahead at 8 px per frame through everything it meets (pierce), until a wall, the
        # screen's edge or 1.5 s; its art (never seen while a likeness is drawn): the orb in his hand from his sheet
        "shot": {
            "engines": ["s3k"],  # (Sonic 1/2 and CD later: psycho_grab there is the next step)
            "motion": "straight", "input": "grab", "speed": 0x80000, "lifetime": 90, "max_alive": 1, "cooldown": 0,
            "pose": 0, "x": 16, "y": -4, "radius": 12, "pierce": True, "carry": False,
            "art": {"sheet": "111917.png", "drawing": [641, 185, 14, 16], "crop": True, "turns": ["none"],
                    "hitbox": [-14, -14, 14, 14]},
            "s3k": {"sound": "Global/Release.wav"},
        },
    },
    13: {  # extra 7: Mighty, as in Mania Plus (Player_JumpAbility_Mighty / Player_State_MightyHammerDrop)
        "abilities": ["hammer_drop", "spike_shell"],
    },
    14: {  # extra 8: Ray, as in Mania Plus (Player_JumpAbility_Ray / Player_State_RayGlide)
        "abilities": ["ray_glide"],
    },
    15: {  # extra 9: Rouge. Knuckles' own glide and climb (extras.py "base": "knuckles"), made a bat's; Y in the air: the
        # Screw Kick; Y on the ground: Treasure Sense; passive: Jewel Thief (both tools/treasure_sense.py, all four games)
        "abilities": ["bat_glide", "screw_kick", "treasure_sense", "jewel_thief"],
        # Treasure Sense (the user's lean first version, 2026-09-30): Y on the ground, she stops to listen (her own "Looking
        # Up" pose) for sense_pause frames, then for sense_show frames (2.5 s) the game's ring blinks at the screen's edge
        # toward the nearest treasure (on it when it's on screen), faster the closer it is (32 frames far, 4 very close).
        # Treasure: S1 the end-of-act giant ring, else a monitor; S2 a monitor; CD the big ring, else a monitor; S3&K the
        # hidden giant rings. Nothing there: a soft "no signal" sound. Then sense_cooldown frames (1 s)
        "sense_pause": 20, "sense_show": 150, "sense_cooldown": 60,
        "sense_sfx": "Menu Back", "sense_sfx_cd": 23, "sense_sfx_s3k": "Global/MenuBleep.wav",  # (CD 23: SFX_G_MENUBUTTON)
        # Jewel Thief: a 10-ring monitor gives her 20 (no other monitor changes)
        # A bat's glide: slower than Knuckles', sinking more gently, so it goes further but slower
        "glide_speed": 0.7,  # of Knuckles' glide speed at every moment (its start, build-up and cap)
        "glide_sink": 0x4000,  # the fall speed it settles at (Knuckles': 0x8000)
        "glide_gravity": 0x1000,  # its pull down to that speed (Knuckles': 0x2000; a faster fall still brakes at 0x2000)
        # Screw Kick: Y in mid-air or out of a glide, with the sheet's "SPIN" frames (the leg out): a dive 45 degrees
        # down and forward until she lands, then a small bounce
        "kick_x": 0x60000, "kick_y": 0x60000, "kick_bounce": 0x40000,
        "kick_sfx": "Insta Shield",
    },
    16: {  # extra 10: Charmy. Tails' own flight (extras.py "base": "tails"); Y in mid-air: the Stinger, a dart
        # aimed like Blaze's Burst Dash, with the sheet's "DASH" frames
        "abilities": ["aim_dash"],
        "aim_dash_y": True,  # started by Y (NoSwap_AfterUpdate), not jump: jump stays Tails' flight
        "dash_frames": 14, "dash_speed": 0x70000,
        "diag_x": 0x50000, "diag_y": 0x50000,
    },
    18: _json_entry("vector"),
    19: {  # extra 13: Cream. Tails' own flight (extras.py "base": "tails") and Cheese on Y (Advance 2's Chao Attack)
        "abilities": ["melee"],
        # Chao Attack throw pose (slots 43 / 44, CD 46: wind-up, swing, her arm out with Cheese gone; her config's
        # CHAO_THROW). Only the pose (its last frame) and S3&K's fallback melee if its shot system is off, which reaches
        # no further than her arm
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10, 16, 20],
        "melee_ticks": 4,
        # Cheese (a real projectile in all four games, motion "homing": abilities.homing_update_body for S1/S2,
        # shots_v3.homing_body for CD, the DLL's HomingUpdate for S3&K). Launched level ahead the way she faces, 16 px
        # out, 4 px above her centre, at 5 px per frame. Each frame it steers at the nearest live badnik or boss on screen
        # (the enemies report themselves: S1/S2 their shot loop copies, CD NoSwap_ShotTouch, S3&K Player_CheckBadnikTouch):
        # per axis a target speed of 1/4 of the gap, at most 5.5 px per frame, reached at 1/2 px per frame (so it arcs,
        # it doesn't snap). No target for 20 frames in a row (about 100 px ahead): it turns back. Its first hit (the
        # normal shot system: badnik, boss, monitor) sends it back too, hitting nothing more: it homes on her (the
        # boomerang's return: 1/8 of the gap, at most 6 px per frame, reached at 3/8 px per frame, plus her own velocity)
        # and is gone within 16 px of her. It flies through terrain; gone after 3 s or offscreen. One out at a time; 30
        # frames after it's back (or gone) before the next. Drawn facing the way it flies. The throw pose (the slots' last
        # frame) for 12 frames. Art: his two flying frames on her sheet (row 5, by her flight frames: 18x25 and 19x25,
        # cut as drawn), 4 game frames each; hitbox 20x20. Sound: the Insta Shield whoosh (S3&K, S1/S2), the spin dash
        # release (CD)
        "shot": {
            "motion": "homing", "speed": 0x50000, "seek_speed": 0x58000, "seek_accel": 0x8000, "seek_frames": 20,
            "return_speed": 0x60000, "return_accel": 0x6000, "catch": 16, "lifetime": 180, "max_alive": 1,
            "cooldown": 30, "pose": 12, "x": 16, "y": -4, "radius": 10,
            "art": {"sheet": "Cream.png", "drawings": [[158, 257, 18, 25], [199, 257, 19, 25]], "ticks": 4,
                    "hitbox": [-10, -10, 10, 10],
                    # (her frames no longer carry Cheese, make_configs.decheese: his cyans are on no player frame, so
                    # S1/S2/CD draw him with all her own slots)
                    "own_slots": True},
            "s3k": {"sound": "Global/InstaShield.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
    },
    20: {  # extra 14: Dr. Robotnik (testmods/robotnik/make_configs.py; the user's picks, 2026-09-27): a Rocket Ride as
        # the jump ability, the sheet's parachute, the Egg Claw on Y and a Bomb Drop on down + Y; the generic ball
        "abilities": ["rocket_ride", "hover", "melee", "physics"],
        # Rocket Ride (slot 41: KNUX CHAOTIX's rocket pack, then the Chaotix blasts): 30 frames (0.5 s) at 7 px per frame
        # forward at least, rising at 0.375 px per frame (about level once gravity has its say), an attack; then it
        # explodes: a launch a bit stronger than his jump (Sonic's 0x68000) with half his speed along, hitting everything
        # within 32 px for 12 frames (3 blast frames of 4). A wall blows it up early; a hit or a spring ends it quietly
        "ride_frames": 30, "ride_speed": 0x70000, "ride_rise": 0x6000,
        "ride_sfx": "Fire Dash", "ride_sfx_s3k": "Global/FireDash.wav", "ride_sfx_cd": "SFX_G_RELEASE",
        "blast_frames": 12, "blast_ticks": 4, "blast_launch": 0x70000, "blast_radius": 32,
        "blast_sfx": "Explosion", "blast_sfx_s3k": "Global/Explosion.wav",
        "hover_frames": 90, "hover_sink": 0x6000,  # a long, lazy parachute drift (after the pop too)
        # Egg Claw throw pose (slots 43 / 44, CD 46: finger up, then pointing ahead; his config's THROW). Only the pose
        # (its last frame) and S3&K's fallback melee if its shot system is off, which reaches no further than his body.
        # He stops to throw on the ground
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        "melee_stop": True,
        # Egg Claw (a real projectile in all four games, motion "boomerang": Sticks' numbers): Y throws CD's giant glove
        # (the CD row's separate glove drawing, 170: cut without its arm, "crop" with the arm's reds as background),
        # level ahead 20 px out, 8 px above his centre, at 8 px per frame plus his own forward speed, slowing by 1/4 px
        # per frame, then homing back on him and caught within 16 px. It flies through terrain; gone at its first hit,
        # after 2.5 s or offscreen. One out at a time. Spun a quarter turn every 2 game frames. The throw pose (the
        # slots' last frame) for 12 frames. Hitbox 28x28. Sound: Amy's hammer throw (S3&K), the Insta Shield whoosh
        # (S1/S2), Amy's hammer dash (CD)
        "shot": {
            "motion": "boomerang", "speed": 0x80000, "decel": 0x4000, "return_speed": 0xA0000,
            "return_accel": 0x4000, "catch": 16, "lifetime": 150, "max_alive": 1, "cooldown": 8, "pose": 12,
            "x": 20, "y": -8, "radius": 13,
            "art": {"sheet": "Robotnik.png", "drawing": [428, 471, 25, 28], "crop": True,
                    "background": ["#91f257", "#fc0000", "#900000"],
                    "turns": ["none", "rot270", "rot180", "rot90"], "ticks": 2, "hitbox": [-14, -14, 14, 14]},
            "s3k": {"sound": "Global/HammerThrow.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_HAMMERDASH"},
        },
        # Bomb Drop (a second real projectile, "shot2", thrown with DOWN + Y: crouching, or holding down in the air; in
        # the jump ball down + Y drops it rather than transforming): motion "bounce", as Mario's fireball and Bean's
        # bomb. Let go of 12 px ahead of him at his centre, 2 px per frame ahead plus his own forward speed, falling with
        # Mario's gravity and bouncing along the floor at 3 px per frame up (about 20 px high); gone at a wall, after 2 s,
        # offscreen or at its first hit. 2 out at once, 12 frames apart (the claw's cooldown and this one's are shared).
        # No throw pose. Art: EXTRAS' black "16t" weight (box 218), only its head: "crop" of its box with the handle's
        # pixels below it left out ("exclude"), tumbling a quarter turn every 4 game frames; hitbox 24x24, radius 11.
        # Sound: the Release whoosh
        "shot2": {
            "motion": "bounce", "input": "down", "speed": 0x20000, "start_vy": 0, "gravity": 0x3800,
            "bounce": -0x30000, "max_fall": 0x60000, "lifetime": 120, "max_alive": 2, "cooldown": 12, "pose": 0,
            "x": 12, "y": 0, "radius": 11,
            "art": {"sheet": "Robotnik.png", "drawing": [61, 717, 25, 22], "crop": True, "background": ["#91f257"],
                    "exclude": [[77, 735, 1, 1], [76, 736, 3, 3]],
                    "turns": ["none", "rot270", "rot180", "rot90"], "ticks": 4, "hitbox": [-12, -12, 12, 12]},
            "s3k": {"sound": "Global/Release.wav"},
            "v4": {"sound": "Release"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # heavy and slow to get going; jump left at Sonic's (Metal's lesson from Hill Top Zone 2)
        "physics": {"top_speed": 0.9, "acceleration": 0.75, "air_acceleration": 0.8},
    },
    21: {  # extra 15: Max the Rabbit (Akimaca's sheet: the "Grab" ear and "Flying" helicopter ears)
        # The user's rework (2026-09-29): the Ear Grapple moved to Y (grapple_y), the Ear Copter is the jump ability, and
        # the Ear Boomerang is gone
        "abilities": ["ear_grapple", "hover", "physics"],
        # Ear Grapple: the ear's tip per frame, px from his centre facing right (testmods/max/make_configs.py
        # GRAPPLE_TIP: the sheet's diagonal "Grab" ear, 8 frames out to about 83 px)
        "grapple_tip": [(4, -19), (11, -26), (17, -32), (24, -39), (31, -46), (37, -52), (44, -59), (51, -66)],
        "grapple_sfx": "Insta Shield", "latch_sfx": "Catch",
        # started by Y in mid-air, once per airborne period (from the jump, the Ear Copter or a fall); the jump ability
        # is the Ear Copter instead: a press in mid-air opens it at once
        "grapple_y": True,
        # chains (the user, 2026-09-30: "sequence breaking is fine, and encouraged"): a latch (or a badnik the ear hits)
        # refills the Y grab, a miss doesn't; after a pull (or the hit's snap back) the next grab waits 15 frames
        "grapple_refill": True, "grapple_cooldown": 15,
        # latched: reeled in at 8 px per frame until within 16 px (his body stops against a wall about 12 px
        # short of a point inside it) or 20 frames, then let go with a hop, still moving forward
        "reel_speed": 0x80000, "reel_frames": 20, "latch_range": 16, "grapple_hop": 0x30000,
        "grapple_forward": 0x20000,
        "snap_frames": 4,  # nothing hit: the ear snaps back in 4 frames
        "hover_frames": 90, "hover_sink": 0x4000,  # Ear Copter
        "physics": {"jump": 1.08, "acceleration": 1.05, "air_acceleration": 1.05},  # a springy rabbit
    },
    17: _json_entry("espio"),
    11: {  # extra 5: Blaze (the aimable Burst Dash is the user's idea). Fire never hurts her (fire_immune, the user's pick
        # 2026-09-27: the fire shield's immunity, always)
        "abilities": ["aim_dash", "physics", "fire_immune"],
        "dash_frames": 16, "dash_speed": 0x70000,
        "diag_x": 0x4F000, "diag_y": 0x4F000,  # 45 degrees at about the same speed
        "physics": {"top_speed": 1.05, "acceleration": 1.05},
    },
    22: {  # extra 16: Tikal (SunnyVies' sheet: testmods/tikal/make_configs.py). Sonic Adventure's spirit orb, and a punch
        "abilities": ["spirit_flight", "melee"],
        # Spirit Flight: the art's 10 transform frames (its loop point, SPIRIT_LOOP), 1 game frame each and held
        # still; then 1.5 s of flight where the d-pad points, 4 px per frame (2.83 on each axis diagonally),
        # easing toward it by 0x4000 per frame so the orb floats
        "spirit_transform": 10, "spirit_ticks": 1, "spirit_frames": 90,
        "spirit_speed": 0x40000, "spirit_diag": 0x2D413, "spirit_accel": 0x4000,
        "spirit_sfx": "Transform",
        # (The melee numbers are only the Spirit Orb's throw pose, slots 43 / 44: the "Punching" row's wind-up, jab and
        # full reach, her arm thrust out (her config's THROW); the pose is their last frame. And S3&K's fallback melee if
        # its shot system is off, which reaches no further than her fist.) She stops to cast on the ground (melee_stop);
        # in the air she keeps her speed
        "melee_sfx": "Insta Shield",
        "melee_reach": [12, 15, 21],
        "melee_ticks": 3,
        "melee_stop": True,
        # Spirit Orb (the user's design, 2026-09-28; it replaced her Punch): a real projectile in all four games, motion
        # "straight": level ahead the way she faces (not aimed), 4 px per frame plus her own forward speed, no gravity;
        # gone at a wall, after 50 frames (about 200 px), offscreen or at its first hit. 2 out at once, 45 frames apart.
        # It starts 24 px ahead of her centre at her fist's height. The pose shows 12 frames. Art: the glowing orb of her
        # Spirit Flight (the "Spirit Transform" row's last four orbs, 659-662 in her config: 16x16 each, cut exactly,
        # without the sparks they trail below, which would hang under a level shot), every 3 game frames in turn; exact in
        # her own palette slots in every engine ("own_slots"). Hitbox 14x14. Sound: Amy's hammer throw (S3&K), the Insta
        # Shield whoosh (S1/S2), Amy's hammer dash (CD), as Mephiles' orb
        "shot": {
            "motion": "straight", "speed": 0x40000, "lifetime": 50, "max_alive": 2, "cooldown": 45,
            "pose": 12, "x": 24, "y": 0, "radius": 7,
            "art": {"sheet": "Tikal.png", "background": ["#ffffff"], "own_slots": True, "ticks": 3,
                    "drawings": [[483, 1068, 16, 16], [503, 1068, 16, 16], [523, 1068, 16, 16], [544, 1068, 16, 16]],
                    "hitbox": [-7, -7, 7, 7]},
            "s3k": {"sound": "Global/HammerThrow.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_HAMMERDASH"},
        },
    },
    23: {  # extra 17: Mario (testmods/mario/make_configs.py). Super Mario 64's Triple Jump, and a Fireball on Y; rolls
        # with his own curl (extras.py "roll")
        "abilities": ["triple_jump", "melee"],
        # Triple Jump: jumping again within 10 frames of landing, running at 2 px per frame or more, is the next jump of
        # the chain: the 2nd at 1.2x his jump, the 3rd at 1.45x with the somersault
        "triple_window": 10, "triple_speed": 0x20000, "triple_jumps": [1.2, 1.45],
        # Fireball: the S3&K flame's leading edge per frame, px ahead of his centre (FIREBALL_REACH: wind-up, the burst
        # at his fist, four flight frames, follow-through), the same on the ground and in the air (FIREBALL_REACH_AIR,
        # his own air pose). He stops to throw on the ground (melee_stop)
        "melee_sfx": "Fire Dash",  # the S3&K flame's own sound
        "melee_reach": [13, 28, 38, 53, 62, 77, 13],
        "melee_air_reach": [13, 28, 38, 53, 62, 77, 13],
        "melee_ticks": 3,
        "melee_stop": True,
        # A real projectile instead of the melee, in S3&K (the DLL's shot, gen_s3k_header.s3k_json "shot") and in
        # Sonic 1/2 (tools/shots_v4.py) and Sonic CD (tools/shots_v3.py); there the melee's frames above are only its
        # throw pose.
        # Super Mario Bros.' fireball: 4 px per frame ahead of him, bouncing along the floor, gone at a wall, after 1.5 s,
        # offscreen or at its first hit; 2 out at once. Art: the S3&K flame's drawings 2 and 3 at half size, as in his
        # S1/S2 throw (build_s3k_shot.py; S1/S2: shots_v4.place_art); hitbox 16x16 round its head. He shows the
        # throw's last frame for 10 frames (standing or in the air). "s3k" / "v4": what differs per engine (shot())
        "shot": {
            "motion": "bounce", "speed": 0x40000, "start_vy": 0x20000, "gravity": 0x3800, "bounce": -0x38000,
            "max_fall": 0x60000, "lifetime": 90, "max_alive": 2, "cooldown": 8, "pose": 10, "x": 14, "y": 0,
            "radius": 8,
            "art": {"flame": [2, 3], "shrink": 2, "ticks": 2, "hitbox": [-8, -8, 8, 8]},
            "s3k": {"sound": "own:fireball"},  # (his own sound, "sounds" below; in every game: "v4" / "cd" below are the fallback)
            "v4": {"sound": "Fire Dash"},  # (the game's SfxName)
            "cd": {"sound": "SFX_G_RELEASE"},  # (Sonic CD: a global SFX alias; CD has no fire sound)
        },
        # his own sounds (tools/own_sounds.py: a name -> a file in testmods/mario/; "own:<name>" in an S3&K sound field):
        # the fireball's, the user's clip (testmods/mario/sfx/SOURCE.txt)
        "sounds": {"fireball": "sfx/Fireball.wav"},
    },
    24: {  # extra 18: Trip (testmods/trip/make_configs.py). Sonic Superstars' double jump, and her wall cling and climb
        "abilities": ["double_jump", "wall_cling"],
        # Double Jump: 0.85x her jump, from wherever she is in the jump, in the shell spin (her "Double Jump" frames)
        "double_jump": 0.85,
        # Wall Cling: 1.5 s on a wall at most, held still for the first 0.5 s, then sliding down at 0.5 px per frame;
        # climbing at 1 px per frame. The wall jump: 4 px per frame away, 6 up (Sonic's jump is 6.5). A wall she let go
        # of takes 10 frames away from it before she can cling to it again
        "cling_frames": 90, "cling_hold": 30, "cling_slide": 0x8000, "climb_speed": 0x10000,
        "wall_jump_x": 0x40000, "wall_jump_y": 0x60000, "cling_lock": 10,
        "ledge_hop": 0x40000, "ledge_forward": 0x20000,  # up onto the ledge: about 36 px up, moving toward it
    },
    26: {  # extra 20: E-102 Gamma (testmods/gamma/make_configs.py). Never rolls (extras.py "no_roll"). A tank: a jet
        # hover, an aimed Arm Cannon bolt on Y ("shot" below), and heavy physics. A robot: he never drowns (no_breathing)
        "abilities": ["umbrella", "melee", "physics", "no_breathing"],
        # Hover: jump in mid-air fires his jets (slot 42: hover mode on the jet pad, not an attack); while jump is held
        # he sinks at 0.25 px per frame (Metal's hover sink) with normal air control, for up to 2 s per jump. Letting go
        # ends it for that jump (Silver's float, with his own art)
        "umbrella_sink": 0x4000, "float_frames": 120,
        # (The melee numbers below were his old beam's. With the real shot below they're only the throw pose's slots 43 /
        # 44 (the pose is their last frame, as the .ani has it) and S3&K's fallback melee if its shot system is off.)
        # Arm Cannon: aim, flash, the beam grows, holds, fades, arm down. Its leading edge per frame, px ahead of his
        # centre (BEAM_REACH / BEAM_REACH_AIR in his config; 10, his own box, where there's no beam). The box starts at
        # the beam (13 px circles: BEAM_Y -33 on the ground, BEAM_Y_AIR -25 in the air, px from his centre; his cannon is
        # at shoulder height) and reaches down to his feet: a band round the beam alone passed over ground badniks and
        # monitors (the user wants a shot that hits them); his body box (-20 / 20) on the frames without a beam.
        # He stops to fire on the ground (melee_stop); in the air he keeps his speed. One shot at a time
        "melee_sfx": "Lightning Jump",  # an electric zap for the laser
        "melee_reach": [10, 10, 65, 89, 113, 113, 110, 10],
        "melee_top": [-20, -20, -39, -39, -39, -39, -39, -20],
        "melee_bottom": [20, 20, 20, 20, 20, 20, 20, 20],
        "melee_air_reach": [10, 10, 67, 91, 115, 115, 112, 10],
        "melee_air_top": [-20, -20, -31, -31, -31, -31, -31, -20],
        "melee_air_bottom": [20, 20, 20, 20, 20, 20, 20, 20],
        "melee_ticks": 4,
        "melee_stop": True,
        # Arm Cannon bolt (the user's design, 2026-09-27): a real projectile in all four games, aimed with the d-pad as
        # Y is pressed ("aim": on the ground back / back-up / up / forward-up / forward, in the air all 8; nothing held:
        # the way he faces; holding back turns him first when he's standing or in the air). Motion "straight": 8 px per
        # frame, diagonals normalised (the same 8 px overall, 5.66 per axis), no gravity; gone at a wall, floor or
        # ceiling it flies into, after 40 frames, offscreen or at its first hit; 3 out at once, 8 frames apart. It starts
        # 16 px out along the aim from 8 px above his centre (the cannon arm). Art: the S3&K Lightning Shield's spark at
        # half size (build_s3k_shot.py "spark": the star, the star, then the small spark; 2 game frames each), in the
        # colours the game's own player art uses in each engine; hitbox 12x12. Sound: the Lightning Shield's jump spark
        # (S3&K, S1/S2); Sonic CD has none: the shield monitor's
        "shot": {
            "motion": "straight", "aim": True, "speed": 0x80000, "lifetime": 40, "max_alive": 3, "cooldown": 8,
            "pose": 10, "x": 16, "y": -8, "radius": 6,
            "art": {"spark": [0, 0, 1], "shrink": 2, "ticks": 2, "hitbox": [-6, -6, 6, 6]},
            "s3k": {"sound": "Global/LightningJump.wav"},
            "v4": {"sound": "Lightning Jump"},
            "cd": {"sound": "SFX_G_SHIELD"},
        },
        # heavy, like Big and Robotnik: slow to get going, a lower top speed and a slightly lower jump
        "physics": {"top_speed": 0.9, "acceleration": 0.75, "air_acceleration": 0.8, "jump": 0.95},
        # His shots break breakable walls (the user, 2026-09-29: he can't roll, so Mania's Press Garden walls stopped him).
        # Data only for now: the Mania mod acts on it (native/mania/src/ManiaWalls.h: what a rolling Sonic breaks); Origins
        # doesn't read it yet
        "shot_breaks_walls": True,
    },
    27: {  # extra 21: Jet the Hawk (testmods/jet/make_configs.py). Balance doesn't matter (the user): a racer. His
        # Extreme Gear as the jump ability (Sonic Riders' air surf) and the Tornado Trap on Y (a projectile)
        "abilities": ["extreme_gear", "melee", "physics"],
        # Extreme Gear (slot 41: the board out, then the ride looping at frame 4, GEAR_LOOP). The board rams badniks
        # (slot 41 is an attack, Sonic Riders style). At least 6 px per frame forward from the press (more if he's
        # faster), up to 10 with forward held (1/32 px per frame more each frame); back brakes 1/8 px per frame down to
        # 2 px, where he carves round and rides the other way, back up to 6 at 1/8 px per frame. Sinking at 0.5 px per
        # frame at most; up held lifts him (1/6 px per frame up, rising at 1.5 at most) for 45 frames per ride. A ride
        # lasts 210 frames (3.5 seconds) at most, then ends as letting go of jump does (the user: overpowered on flat
        # levels, 2026-09-29)
        "gear_speed": 0x60000, "gear_top": 0xA0000, "gear_accel": 0x800, "gear_recover": 0x2000,
        "gear_brake": 0x2000, "gear_turn": 0x20000,
        "gear_sink": 0x8000, "gear_lift": 0x2800, "gear_rise": 0x18000, "gear_lift_frames": 45, "gear_frames": 210,
        "gear_sfx": "Release", "gear_sfx_s3k": "Global/Release.wav",
        # (The melee numbers are only the Tornado Trap's throw pose, slots 43 / 44: fist out, twisting round, spinning in
        # his own swoosh (his config's THROW); the pose is their last frame. And S3&K's fallback melee if its shot system
        # is off, which reaches no further than his body.) He stops for it on the ground; in the air he keeps his speed
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",  # a whoosh
        "melee_reach": [15, 15, 28],
        "melee_ticks": 3,
        "melee_stop": True,
        # Tornado Trap (the user's design, 2026-09-28; it replaced his melee Tornado): a real projectile in all four games,
        # motion "straight": a whirlwind that drifts level ahead the way he faces at 1 px per frame, his own speed NOT
        # added ("carry" false: thrown on the run, it's left behind as a trap), no gravity; gone at a wall, after 2 s (120
        # frames), offscreen or at its first hit (anything that touches it). One out at a time, 90 frames apart. It
        # starts 32 px ahead of his centre, level with it. The pose shows 12 frames. Art: the sheet's own SPARE PARTS
        # whirlwinds, the ones his old Tornado swing was composed from (the big crescent swirl, 843 in his config, and the
        # thin-arc swirl with its long streak, 847 + 856 as drawn together in one box), each cut exactly, and each mirrored
        # too ("flip_x"): the four in turn every 4 game frames, so it spins; in his own palette slots ("own_slots": the
        # swirls' three colours are his exactly). Hitbox 32x32 (Sonic 1/2 need a square). Sound: the Insta Shield whoosh
        # (S3&K, S1/S2), the Release whoosh (CD)
        "shot": {
            "motion": "straight", "carry": False, "speed": 0x10000, "lifetime": 120, "max_alive": 1, "cooldown": 90,
            "pose": 12, "x": 32, "y": 0, "radius": 16,
            "art": {"sheet": "Jet.png", "background": ["#ffffff"], "crop": True, "own_slots": True, "ticks": 4,
                    "drawings": [[56, 1740, 33, 39], [97, 1741, 37, 38], [56, 1740, 33, 39, "flip_x"],
                                 [97, 1741, 37, 38, "flip_x"]],
                    "hitbox": [-16, -16, 16, 16]},
            "s3k": {"sound": "Global/InstaShield.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # a racer: a higher top speed and quicker to get going
        "physics": {"top_speed": 1.15, "acceleration": 1.1, "air_acceleration": 1.1},
    },
    28: {  # extra 22: Mecha Sonic (testmods/mecha-sonic/make_configs.py). Moves chosen by the user's kid: his Sonic &
        # Knuckles boss attack as the jump ability, and an afterburner burst on Y. A robot: he never drowns (no_breathing)
        "abilities": ["screw_kick", "melee", "no_breathing"],
        # Spike Ball: Rouge's Screw Kick started by jump instead of Y (kick_jump), in his spike ball (slot 41): a slam
        # 45 degrees down and forward at 7 px per frame on each axis until he lands (no bounce: kick_bounce 0, he
        # just lands). An attack: a badnik or monitor he hits bounces him off like a jump, which ends it. Once per jump
        "kick_jump": True,
        "kick_x": 0x70000, "kick_y": 0x70000, "kick_bounce": 0,
        "kick_sfx": "Fire Dash", "kick_sfx_s3k": "Global/Release.wav",
        # Jet Boost: the melee's timing, frames and cooldown with no shot: melee_boost makes it a burst of speed. For
        # its 18 frames (6 frames of 3) he goes at least 8 px per frame the way he faces, on the ground or level in the
        # air, attacking (his body: the box reaches his front, BOOST_REACH). Then 45 frames before the next one
        "melee_sfx": "Fire Dash", "melee_sfx_s3k": "Global/Release.wav",
        "melee_reach": [20] * 6,
        "melee_top": [-24] * 6, "melee_bottom": [20] * 6,
        "melee_ticks": 3,
        "melee_boost": 0x80000,
        "melee_cooldown": 45,
        # Spike Ball shot (the user's kid's pick, 2026-09-27): DOWN + Y (crouching, or holding down in the air; "input":
        # "down") throws a spiked ball, a real projectile in all four games; Y without down stays the Jet Boost, and in
        # the jump ball down + Y throws instead of transforming (plain Y still transforms when Super is possible).
        # Motion "bounce", as Mario's fireball: 4 px per frame ahead of him plus his own forward speed, bouncing along
        # the floor at 4 px per frame up (about 36 px high) with Mario's gravity; gone at a wall, after 2 s, offscreen or
        # at its first hit; 2 out at once, 12 frames apart. It starts 28 px ahead of him, 4 px above his centre (clear of
        # his body: the ball is 48 px). Art: his own in-game spike ball, the three frames of his curled spin (28, 26, 27
        # on MechaSonic.png, cut exactly as drawn, each in a 48 px box on its baseline so they line up), cycled every 3
        # game frames: the spikes turn; mirrored when thrown left. Hitbox 36x36 (the ball, most of its spikes); radius 23
        # for the floor (its half height). No throw pose (the sheet has none). Sound: the spin dash release
        "shot": {
            "motion": "bounce", "input": "down", "speed": 0x40000, "start_vy": 0x10000, "gravity": 0x3800,
            "bounce": -0x40000, "max_fall": 0x60000, "lifetime": 120, "max_alive": 2, "cooldown": 12, "pose": 0,
            "x": 28, "y": -4, "radius": 23,
            "art": {"sheet": "../MechaSonic.png", "background": ["#ffffff"], "ticks": 3, "hitbox": [-18, -18, 18, 18],
                    "drawings": [[289, 64, 48, 48], [342, 64, 48, 48], [395, 64, 48, 48]]},
            "s3k": {"sound": "Global/Release.wav"},
            "v4": {"sound": "Release"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
    },
    29: {  # extra 23: Sticks the Badger (testmods/sticks/make_configs.py; PRIVATE, see extras.py). The user's picks:
        # Trip's wall cling and climb as the jump ability, Tails' ball in her colours, and a boomerang on Y. Her art is
        # enlarged 1.2x (her config's SCALE, the user's exception for her): the reach, the shot's start and size below
        # are for the enlarged frames
        "abilities": ["wall_cling", "melee"],
        # Wall Cling: Trip's numbers (1.5 s on a wall at most, held for 0.5 s, then sliding at 0.5 px per frame; climbing
        # at 1 px per frame; the wall jump 4 px per frame away, 6 up; 10 frames before the same wall again)
        "cling_frames": 90, "cling_hold": 30, "cling_slide": 0x8000, "climb_speed": 0x10000,
        "wall_jump_x": 0x40000, "wall_jump_y": 0x60000, "cling_lock": 10,
        "ledge_hop": 0x40000, "ledge_forward": 0x20000,
        # Boomerang throw pose (slots 43 / 44, CD 46: held back, let go, arm out; her config's THROW). Its leading edge
        # per frame, px ahead of her centre (1.2x the drawn 10, 28, 16), and 4 game frames each. She stops to throw on the
        # ground. (The boomerang itself is the "shot" below: these are only its throw pose, and S3&K's fallback melee if
        # its shot system is off.)
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",  # a whoosh
        "melee_reach": [12, 34, 19],
        "melee_ticks": 4,
        "melee_stop": True,
        # Boomerang (a real projectile in all four games, motion "boomerang": the DLL's BoomerangUpdate, S1/S2
        # boomerang_update_body, CD shots_v3.boomerang_body). Thrown level ahead the way she faces, 17 px out, 5 px above
        # her centre (her hand, 1.2x the drawn 14 and 4): 8 px per frame plus her own forward speed, slowing by 1/4 px
        # per frame, so it stops about 145 px ahead of her (32 frames); then it homes back on her hand wherever she is (1/8 of the gap per frame, at most
        # 10 px, reached at 1/4 px per frame, plus her own velocity) and is caught within 16 px (about 1.1 s in all
        # standing still). It flies through terrain; gone at its first hit (not piercing: the S1/S2 and CD hit code
        # remove a shot at its first hit, and in S3&K a live SuperHammer keeps what it touched in its hit list, which
        # the game reads as the hammer still hitting it), after 2.5 s or offscreen. One out at a time. The throw pose
        # (the slots' last frame) for 12 frames. Art: the crescent tip of her brown staff (Sticks2.png: the hooked end
        # above her head in a pole swing, 25x19 at 491,1255, cut out as-is: "crop"; the sheet's black flying pieces are
        # motion streaks, which read as a black frame in game), enlarged 1.2x like her (30x23), spun a quarter turn
        # clockwise every 2 game frames; hitbox 26x26. Sound: Amy's hammer throw in S3&K, the Insta Shield whoosh in
        # S1/S2, Amy's hammer dash in CD
        "shot": {
            "motion": "boomerang", "speed": 0x80000, "decel": 0x4000, "return_speed": 0xA0000,
            "return_accel": 0x4000, "catch": 16, "lifetime": 150, "max_alive": 1, "cooldown": 8, "pose": 12,
            "x": 17, "y": -5, "radius": 13,
            "art": {"sheet": "../Sticks2.png", "drawing": [491, 1255, 25, 19], "crop": True, "scale": 1.2,
                    "turns": ["none", "rot270", "rot180", "rot90"], "ticks": 2, "hitbox": [-13, -13, 13, 13]},
            "s3k": {"sound": "Global/HammerThrow.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_HAMMERDASH"},
        },
    },
    30: {  # extra 24: Chaos (Chaos 0; testmods/chaos/make_configs.py). The user's picks: a Puddle Slide as the jump
        # ability, his own puddle as his ball, a Stretch Punch on Y and no drowning (Metal's no_breathing). His art is
        # enlarged 1.1x (his config's SCALE, the user's exception for him): the reach below is for the enlarged frames
        # water_swim first (the user, 2026-09-28): underwater his mid-air jump press is Big's swim stroke; out of water,
        # the Puddle Slide
        "abilities": ["water_swim", "puddle_slide", "melee", "no_breathing"],
        # Water swim: Big's numbers. Underwater each jump press in mid-air (in the jump or a stroke) is a stroke: up at 3 px
        # per frame (a faster rise is kept), at most one every 14 frames, as often as he likes (slot 47 "Swim": his RUN
        # frames, every other one, his limbs paddling; not an attack)
        "swim_stroke": 0x30000, "swim_delay": 14,
        # Puddle Slide: jump in mid-air drops him at 8 px per frame at least (in the dive, slot 41: an attack, like the
        # Hammer Drop). Landing from it, he melts into a puddle and slides along the ground, then rises back up (slot 42:
        # the rise's 8 frames, R1-R8; puddle_frames picks one per step of puddle_ticks game frames): melting (R8 down to
        # R1), sliding on the flat puddle R1 (held: R2 shows his head's tip), rising (R2 up to R8). For the first puddle_move steps he goes at
        # least puddle_speed the way he faces (5 px per frame: 46 frames, about 0.75 s, melting and sliding), then slows
        # to a stop as he rises (a quarter of his speed off each frame). The whole time (62 frames) nothing hurts him:
        # the post-hit blink's rule, held at 3 each frame so he doesn't flicker. A jump, a roll, a spring, a ledge or a
        # hit (from what the blink can't stop) ends it; so does Y (no Stretch Punch meanwhile)
        "puddle_drop": 0x80000, "puddle_speed": 0x50000, "puddle_ticks": 2, "puddle_move": 23,
        "puddle_frames": [7, 6, 5, 4, 3, 2, 1, 0] + [0] * 15 + [1, 2, 3, 4, 5, 6, 7, 7],
        "puddle_sfx": "Bubble Bounce", "puddle_sfx_s3k": "Global/BubbleBounce.wav", "puddle_sfx_cd": "SFX_G_SLIDE",
        # Stretch Punch (slots 43 / 44, CD 46): wind-up, the arm stretching out (A2-A3), held, and back (his config's
        # PUNCH; not A4, which lacks his brain). The fist's reach per frame, px ahead of his centre (the ATACK frames' 14,
        # 53 and 77 px, 1.1x), 3 game frames each. He stops to punch on the ground. melee_cooldown 18 is the move's own length (no wait after it): it's
        # there so the Puddle Slide can hold Y off through NoSwap_cooldown
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",  # a whoosh
        "melee_reach": [15, 58, 85, 85, 58, 15],
        "melee_ticks": 3,
        "melee_stop": True,
        "melee_cooldown": 18,
    },
    31: {  # extra 25: Flicky (testmods/flicky/make_configs.py). The user's picks: Tails' own flight as the jump ability
        # (extras.py "base": "tails"), his own Spinball, and a silly Animal Drop on Y (2026-09-27, replacing Dash n Dive)
        "abilities": [],
        # Animal Drop (a real projectile in all four games, motion "drop"): Y drops one of the little animals of the sheet's
        # "Boredom Bonus" row from just below him (12 px under his centre), falling with Mario's gravity (0.22 px per frame
        # more each frame, at most 8), carrying his own forward speed along (shot speed 0: his speed alone; nothing when
        # he's still: straight down). No bounce: gone on the floor, at a wall, after 2 s or offscreen; any badnik, monitor
        # or boss it lands on is hit like a jumping player (the badnik explodes as usual). 3 out at once, 10 frames apart.
        # Standing, jumping or flying ("from_flight": Tails' flight state too; his flight goes on). In the jump ball Y
        # still transforms first when Super is possible. Each throw is the next critter ("cycle": a frame per throw, held):
        # the chicken, squirrel, penguin, pig, rabbit and seal, cut as drawn (loose drawings: "drawings" boxes on the
        # sheet, its green box as background; all six are exactly in his own colours). Sonic 1/2 have room for 4 frames
        # (shots_v4.FRAMES): the first four there. No throw pose (his sheet has none). Hitbox 20x20 (the critters are
        # 12-13 px wide, 18-24 tall; radius 10 for the floor). Sound: the Release whoosh (S3&K, S1/S2, CD)
        "shot": {
            "motion": "drop", "speed": 0, "start_vy": 0x10000, "gravity": 0x3800, "max_fall": 0x80000, "lifetime": 120,
            "max_alive": 3, "cooldown": 10, "pose": 0, "x": 0, "y": 12, "radius": 10, "cycle": True, "from_flight": True,
            # thrown standing on the ground: tossed forward from his middle instead (1 px per frame plus his speed, 3 up),
            # landing about 30 px ahead of him
            "ground": {"x": 8, "y": -4, "speed": 0x10000, "start_vy": -0x30000},
            "art": {"sheet": "../Flicky.png", "background": ["#4bb98d"], "hitbox": [-10, -10, 10, 10],
                    "drawings": [[149, 358, 12, 21], [162, 356, 13, 23], [176, 358, 12, 21], [204, 358, 12, 21],
                                 [189, 355, 13, 24], [217, 361, 13, 18]]},
            "s3k": {"sound": "Global/Release.wav"},
            "v4": {"sound": "Release"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
    },
    32: {  # extra 26: Tails Doll (testmods/tails-doll/make_configs.py). The user's rework (2026-09-28): built on Sonic now
        # (no Tails flight), a Phase Warp as the jump ability, a Screen Nuke on Y, his own ROLL ball
        "abilities": ["phase_warp", "melee"],
        # Phase Warp: jump in mid-air, once per jump: he flickers out (4 frames, slot 41: the SPIN row), is gone for 4
        # frames and flickers back in (4), held still, untouchable throughout; while gone he moves up to 96 px (6 tiles)
        # where the d-pad points (8 ways; nothing held: ahead), a step of 8 px at a time, stopping before the first step
        # where his body would be in solid terrain (no passing through walls or floors). Then his speed along from before
        # the warp, falling from there
        "warp_range": 96, "warp_vanish": 4, "warp_gone": 4, "warp_appear": 4,
        "warp_sfx": "Insta Shield", "warp_sfx_s3k": "Global/InstaShield.wav", "warp_sfx_cd": "SFX_G_RELEASE",
        # Screen Nuke (slots 43 / 44, CD 46): arms spread (ENDING(SMALL)'s last), then the dark CONTINUE form, its head open
        # on the pulsing red core (the sheet's most dramatic frames), 10 frames of 4 game frames. At frame 4 (the core at
        # its brightest) the nuke: the screen flashes black (a runtime fade, "flash": its darkness per game frame, 0-255)
        # and for "hit" game frames every enemy, monitor and boss on screen is hit, as by his attack ("reach": px round
        # him; S3&K: on screen). Nothing hurts him meanwhile (melee_safe); he stands still for it on the ground and
        # hangs still in the air (melee_hang). 10 s (600 frames) from one nuke to the next
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",  # a whoosh
        "melee_reach": [10] * 10,
        "melee_ticks": 4,
        "melee_stop": True,
        "melee_safe": True,
        "melee_hang": True,
        "melee_cooldown": 600,
        "melee_nuke": {"at": 4, "hit": 8, "reach_x": 212, "reach_y": 128, "reach_cd": 200,
                        "flash": [64, 128, 192] + [255] * 7 + [240, 220, 200, 180, 160, 140, 120, 100, 80, 60, 40, 20],
                        "sfx": "Explosion", "sfx_s3k": "Global/Explosion.wav", "sfx_cd": "SFX_G_EXPLOSION"},
    },
    # extra 27: Bean the Dynamite. His moves (Leap, Bomb Throw) and their numbers are in testmods/bean/character.json
    33: _json_entry("bean"),
    34: {  # extra 28: Bark the Polar Bear (testmods/bark/make_configs.py). The user's picks: Slam Ground (Mighty's Hammer
        # Drop) as the jump ability with shockwaves (2026-09-28), a Bear Rush on Y (replacing the Double Kick), heavy physics
        # and his own SPIN ball
        "abilities": ["hammer_drop", "melee", "physics"],
        # Slam Ground: Mighty's Hammer Drop as it is (12 px per frame down, 8 underwater, half his speed along; landing
        # bounces him up in his ball), in SLAM GROUND (RIGHT) 1-2 (slot 41: his stance, then the fist raised, held)
        # Bear Rush (slots 43 / 44, CD 46): a shoulder charge, his RUN frames twice (8 frames of 3: 24 game frames, 0.4 s):
        # Mecha Sonic's Jet Boost (melee_boost), at least 8 px per frame the way he faces, on the ground or level in the
        # air, an attack; the box his body to 20 px ahead. Then 1 s (60 frames) from one rush to the next
        "melee_sfx": "Release", "melee_sfx_s3k": "Global/Release.wav",
        "melee_reach": [20] * 8,
        "melee_top": [-24] * 8, "melee_bottom": [20] * 8,
        "melee_ticks": 3,
        "melee_boost": 0x80000,
        "melee_cooldown": 60,
        # Slam shockwaves (the user's design, 2026-09-28): a real projectile in all four games, motion "ground" (new),
        # "input" "slam": not thrown with Y; the Slam Ground's landing sends out two, one each way, 16 px out from him, their
        # centre 8 px above the floor under his feet. Each runs along the floor at 4 px per frame, following it up and down
        # slopes (gripped to it, as a walking badnik is), for 30 frames (about 120 px); gone at a wall, a ledge's end (no
        # floor to grip), offscreen or its first hit. Art: the games' own Spin Dash dust (S3&K's "Spin Dash 1" drawings
        # 3-6, the cloud swelling; his sheet has no dust or impact), its foot on the floor, mirrored running left; colours
        # the nearest of the engine's player colours (white and greys). Hitbox 32x32 round its centre (up to 24 px above
        # the floor). Sound: the landing's own (Mighty's Hammer Drop hit)
        "shot": {
            "motion": "ground", "input": "slam", "speed": 0x40000, "lifetime": 30, "max_alive": 2, "cooldown": 0,
            "pose": 0, "x": 16, "y": 12, "radius": 8,
            "art": {"dust": [3, 4, 5, 6], "mirror": True, "floor": 8, "ticks": 3, "hitbox": [-16, -16, 16, 16]},
            "s3k": {"sound": None},
            "v4": {"sound": None},
            "cd": {"sound": None},
        },
        # heavy, as Gamma: slow to get going, a lower top speed and a slightly lower jump
        "physics": {"top_speed": 0.9, "acceleration": 0.75, "air_acceleration": 0.8, "jump": 0.95},
    },
    35: {  # extra 29: Heavy (testmods/heavy/make_configs.py). The user's picks: a Charge on Y (2026-09-27, replacing the
        # Dash), no jump ability, heavy physics, Sonic's ball in his colours, and he breaks walls like Knuckles
        "abilities": ["charge", "physics", "breaks_walls"],
        # Charge: while Y is held on the ground he locks the way he faces and pushes, a little harder the faster he goes:
        # each frame charge_accel (0.023 px per frame) plus charge_gain / 1024 of his speed (1/64), up to charge_top (13
        # px per frame): about 2 px per frame after 0.9 s, past his top speed (5.4) after 1.65 s, 13 after 2.45 s. The
        # start is heavy, the end unstoppable. Letting go of Y ends the push but not the charge: he coasts, losing only
        # charge_friction a frame (0.02 px: about 6.5 s from full speed; his normal friction is 0.035) or charge_brake
        # holding back (0.047: about 2.7 s), until he's back at his own top speed, then plays on normally. The whole
        # time he's an attack (badniks, monitors, bosses) and still breaks walls; a wall that stops him (his speed
        # falls under half of what it was, from 2 px per frame up) ends it, and so do a jump (he keeps his speed, as
        # any jump), a ledge, a roll or a hit. Frames: his running frames (slot 41; the timer-free stride: one frame
        # per charge_stride px travelled), with the sheet's DASH flash in front once he's past his top speed (slot 43),
        # and his SLIDE pose while he coasts (slot 44; CD's 47 from slot 42, S3&K's hover slot 42)
        "charge_accel": 0x600, "charge_gain": 16, "charge_top": 0xD0000, "charge_friction": 0x500,
        "charge_brake": 0xC00, "charge_stride": 10,
        # Juggernaut rework (the user, 2026-09-30): Y shoves him to charge_shove at once (4 px per frame, most of his
        # 5.4 top speed; the rest of the push as above: past his top speed after about 0.25 s, 13 px after about 1 s,
        # was 1.65 s and 2.45 s), and while the charge is past his top speed (the fist's flash, coasting too) enemies
        # can't hurt him: spiky badniks, badniks' shots and bosses' parts are harmless (some spiky badniks break), and
        # bosses take his hits. Hazards (spikes, crushers, lava, lasers, pits) hurt as ever. S1/S2: NoSwap_flags bit 7
        # and noswap_common.juggernaut; CD: build_soniccd.cd_juggernaut; S3&K: the DLL's Juggernaut hooks
        "charge_shove": 0x40000,
        # Shine Spark (the user's design, 2026-09-30, Super Metroid's; the charge's "spark_*" numbers: spark_after /
        # spark_air, build_soniccd.spark_after_cd / spark_air_cd, the DLL's Spark): at full charge (past his top speed, on
        # the ground) DOWN stores it: he skids to a stop (spark_skid a frame, for up to spark_skid_frames) and glows
        # white-hot (his greys, spark_glow_slots, pulse toward spark_glow_to by spark_glow / 256: a runtime palette
        # effect, the art untouched) for spark_store frames (4 s), walking and jumping as usual (no charge, no roll); the
        # time runs out (or a hit): it's gone. JUMP while glowing (on the ground or in the air) launches him the way the
        # d-pad says: straight up (nothing, or up), up-forward (up + a side) or forward (a side alone), at spark_speed (12
        # px per frame; the diagonal 8.5 per axis), no gravity, no control, until the terrain stops him (a wall, a
        # ceiling, the floor: then he drops), a spring or a hit. Meanwhile he's an attack and enemies can't hurt him
        # (the Juggernaut's rule; hazards still do) and he breaks walls. Pose: his SPRING/JUMP pose (fists up) up and
        # up-forward (slot 45, CD 48 from slot 47, S3&K's attack-up slot), the charge's dash frames forward. Sounds: the
        # charge sound as it's stored, the release as he launches. His jump stays as low as it is (the user)
        "spark_store": 240, "spark_speed": 0xC0000, "spark_skid": 0xC000, "spark_skid_frames": 30,
        "spark_glow_slots": [74, 75, 76, 77], "spark_glow_to": 0xFFF8E0, "spark_glow": [80, 144, 208],
        "spark_store_sfx": "Charge", "spark_sfx": "Release",
        "spark_store_sfx_s3k": "Global/Charge.wav", "spark_sfx_s3k": "Global/Release.wav",
        "spark_store_sfx_cd": "SFX_G_CHARGE", "spark_sfx_cd": "SFX_G_RELEASE",
        # heavy, as Gamma: slow to get going, a lower top speed and a slightly lower jump
        "physics": {"top_speed": 0.9, "acceleration": 0.75, "air_acceleration": 0.8, "jump": 0.95},
    },
    36: {  # extra 30: Bomb (testmods/bomb/make_configs.py). The user's picks: a Self-Destruct on Y, a Hop (Trip's
        # double jump) as the jump ability, Sonic's ball in his colours (his Labyrinth spin isn't a ball)
        "abilities": ["double_jump", "melee"],
        # Hop: a second jump at 0.85x his jump, from wherever he is in the jump, in his SPRING/JUMP pose (slot 41, an
        # attack like Trip's shell spin) until he starts falling. Once per jump
        "double_jump": 0.85,
        # Self-Destruct (slots 43 / 44, CD 46): DETONATING 1-3, then EXPLOSION 1-5 (4x, up to 152 px across) and back 4-1
        # as he reforms; 4 game frames each (48 in all). The user's rework (2026-09-28): a HALF-SCREEN NUKE, Tails Doll's
        # Screen Nuke (melee_nuke) without its black flash: from the blast's first frame (3) for 20 game frames (to its
        # peak) everything in a box 128 px either side of him and 96 above and below (256 x 192, about half the 424 x 240
        # screen; CD a square 112 each way: its shot test is square) is hit, as by his attack. Nothing hurts him during it
        # (melee_safe); then the COST (melee_cost): a normal hit through the game's own hurt (rings scattered, a shield
        # lost instead, at 0 rings he dies: a kamikaze, the user's choice). He stands still for it on the ground, and keeps
        # his speed in the air. 1 s (60 frames) from one to the next. A pop as he starts to detonate (CD's is always the
        # release sound), the explosion as the nuke goes off
        "melee_sfx": "Release", "melee_sfx_s3k": "Global/Release.wav",
        "melee_reach": [10] * 12,
        "melee_ticks": 4,
        "melee_stop": True,
        "melee_safe": True,
        "melee_cost": True,
        "melee_cooldown": 60,
        # ("box": S3&K hits that box too, not the whole screen as Tails Doll's)
        "melee_nuke": {"at": 3, "hit": 20, "reach_x": 128, "reach_y": 96, "reach_cd": 112, "box": True, "flash": [],
                        "sfx": "Explosion", "sfx_s3k": "Global/Explosion.wav", "sfx_cd": "SFX_G_EXPLOSION"},
    },
    37: {  # extra 31: Honey the Cat (testmods/honey/make_configs.py). The user's picks: a Spin Attack on Y (2026-09-27,
        # replacing her Claw Swipe and Ray's glide), her own ball
        "abilities": ["spin_attack"],
        # Spin Attack: Y, on the ground or in the air (in the jump ball Y transforms first when Super is possible), starts
        # her whirl (the sheet's dark curled spin frames: slot 41 in the air, centred; slot 43 on the ground, on her feet;
        # CD 45 / 46), one frame per spin_ticks game frames. It lasts while Y is held, spin_frames at most (1.67 s), then
        # spin_cooldown frames (0.5 s) before the next. On the ground she keeps moving as she was (no stop); a jump out of
        # it goes on spinning. While it lasts she's an attack (badniks, monitors, bosses) and in the air she's floaty:
        # gravity pulls her at spin_gravity / 256 of its strength (half). Whatever she breaks or hits bounces her hard: up
        # at spin_bounce (5.5 px per frame, floaty: about 140 px high), and on the ground away from where she faces at
        # spin_bounce_x (3 px per frame), a pinball rebound (S1/S2 / CD: told from the bounce the game's own code gave her,
        # at the start of her next update; S3&K: the DLL's badnik, monitor and boss hooks)
        # (spin_ticks 2: a 10-frame turn; 3 looked awkward, the user 2026-09-27.) The lean (a runtime draw effect, no new
        # pixels): while she spins her frames are drawn turned toward her travel, spin_lean / 512 of a turn per px per
        # frame of her speed (ground speed; in the air her x speed), spin_lean_max at most (32: 22.5 degrees, reached at
        # about 6.4 px per frame), eased in over her first 8 spin frames and out over the last 8 of spin_frames. The
        # spin's animations are drawn with full rotation for it ("rot" 1 in make_configs.py); collision is unchanged.
        # S3&K's DLL has the same numbers (NoSwapS3K.cpp SPIN_LEAN)
        "spin_frames": 100, "spin_cooldown": 30, "spin_ticks": 2, "spin_gravity": 128,
        "spin_lean": 5, "spin_lean_max": 32,
        "spin_bounce": 0x58000, "spin_bounce_x": 0x30000,
        "spin_sfx": "Insta Shield", "spin_sfx_s3k": "Global/InstaShield.wav", "spin_sfx_cd": "SFX_G_RELEASE",
    },
    38: {  # extra 32: E-123 Omega (testmods/omega/make_configs.py). The user's picks: a Flame Shot on Y (tap: a small
        # flame; hold: the charged, piercing Flame Blast, 2026-09-29), a
        # Jet Hover as the jump ability, heavy physics, breaking walls and no drowning. He never rolls (extras.py
        # "no_roll", as Gamma): his jump is his fall pose
        "abilities": ["umbrella", "melee", "physics", "no_breathing", "breaks_walls"],
        # Jet Hover: Gamma's hover. Jump in mid-air fires his jets (slot 42: his fall pose with the sheet's jet flames under
        # his feet, not an attack); while jump is held he sinks at 0.25 px per frame with normal air control, for up to
        # 2 s per jump. Letting go ends it for that jump
        "umbrella_sink": 0x4000, "float_frames": 120,
        # (The melee numbers are only the Flame Shot's pose, slots 43 / 44: the gun out, then firing; the pose is their
        # last frame. And S3&K's fallback melee if its shot system is off, which reaches no further than his body.) He
        # plants his feet to fire on the ground; in the air he keeps his speed
        "melee_sfx": "Fire Dash", "melee_sfx_s3k": "Global/FireDash.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        "melee_stop": True,
        # Flame Shot, reworked (the user's design, 2026-09-29, on Mega Man's Buster / Charge Shot mechanic): TAP Y fires a
        # small flame, HOLD Y charges the big Flame Blast. Pressing Y fires the small one at once (as Mega Man 4 on: letting
        # go of a charge that isn't full fires nothing more, the press already fired)
        # Small flame (a real projectile in all four games, motion "straight"): level ahead the way he faces, 7 px per
        # frame plus his own forward speed, no gravity; gone at a wall, after 14 frames (about 100 px: it fizzles out,
        # 2026-09-29, the user: "even smaller", reach "a good compromise"), offscreen or at its first hit. One out at a
        # time, 60 frames (1 s) apart. It starts 34 px ahead of him at his gun's height. The firing pose shows for 12
        # frames (standing: he plants his feet; in the air he keeps his speed). Art: the sheet's own small flame burst
        # (AIM ATTACK SFX, its first frame: 20x20, cut exactly, no scaling), flickering with its upside-down mirror image
        # every 3 game frames, in his own palette slots ("own_slots": its white, yellow, orange and red go to the nearest
        # slot, as the jet flames' same colours already do). Hitbox 12x12 (the burst's solid core). Sound: the fire dash
        # (S3&K, S1/S2); Sonic CD has none: the Release whoosh
        "shot": {
            "motion": "straight", "speed": 0x70000, "lifetime": 14, "max_alive": 1, "cooldown": 60,
            "pose": 12, "x": 34, "y": 0, "radius": 6,
            "art": {"sheet": "../Omega.png", "drawings": [[13, 3764, 20, 20], [13, 3764, 20, 20, "flip_y"]], "crop": True,
                    "own_slots": True, "ticks": 3, "hitbox": [-6, -6, 6, 6]},
            "s3k": {"sound": "Global/FireDash.wav"},
            "v4": {"sound": "Fire Dash"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # Flame Blast (the charge shot: "shot2", "input" "charge", Mega Man's Charge Shot): holding Y charges (he can walk
        # meanwhile); from 30 frames (0.5 s) he flashes red-orange (his metal greys and pink highlight in his own reds,
        # oranges and flame yellows: the art config's charge_palettes, a runtime palette effect, the art untouched):
        # charge1 every other 4 frames; at 90 frames (1.5 s) the charge is full: charge2a, charge2b and his own in turn, 2
        # frames each. Letting go of a full charge fires the big flame ball (the old Flame Shot, unchanged in art and
        # size): level ahead, 6 px per frame plus his forward speed, PIERCING ("pierce": badniks, monitors and bosses are
        # hit once each and it flies on); gone at a wall, after 60 frames (360 px) or offscreen. One out at a time. After
        # it the (shared) cooldown is 180 frames (3 s): no small flame meanwhile, and with "charge_wait" the charge holds
        # a frame short of full until the cooldown is over, so blasts are at least 3 s apart. A hit loses the charge. It
        # starts 40 px ahead of him at his gun's height; the firing pose shows with it. Art: the sheet's own flame-shot
        # fireball (SHOT ATTACK SFX, the first row's third and fourth frames, each cut to the ball and a little of its
        # flame: 56x45 and 56x46, a crop), every 3 game frames in turn, exact in his own slots. Hitbox 44x44. Sound: the
        # fire dash (S3&K, S1/S2); Sonic CD: the Release whoosh
        "shot2": {
            "motion": "straight", "input": "charge", "pierce": True, "charge_start": 30, "charge_full": 90,
            "charge_wait": True,
            "speed": 0x60000, "lifetime": 60, "max_alive": 1, "cooldown": 180, "pose": 12, "x": 40, "y": 0, "radius": 20,
            "art": {"sheet": "../Omega.png", "drawings": [[161, 4482, 56, 45], [242, 4482, 56, 46]], "crop": True,
                    "own_slots": True, "ticks": 3, "hitbox": [-22, -22, 22, 22]},
            "s3k": {"sound": "Global/FireDash.wav"},
            "v4": {"sound": "Fire Dash"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # heavy, as Gamma: slow to get going, a lower top speed and a slightly lower jump
        "physics": {"top_speed": 0.9, "acceleration": 0.75, "air_acceleration": 0.8, "jump": 0.95},
    },
    39: {  # extra 33: Sally Acorn (testmods/sally/make_configs.py). The user's picks: a Spin-Kick High Jump on Y (a new
        # move, high_kick), a Flying Kick Dive as the jump ability (Mecha Sonic's Spike Ball with her frames), her own
        # ball and Spin Dash
        "abilities": ["screw_kick", "high_kick"],
        # Flying Kick Dive: jump in mid-air dives her 45 degrees down and forward at 6 px per frame on each axis (Mecha's
        # is 7), in her flying kick (slot 41, an attack), until she lands (no bounce). Not a double jump. Once per jump
        "kick_jump": True,
        "kick_x": 0x60000, "kick_y": 0x60000, "kick_bounce": 0,
        "kick_sfx": "Insta Shield", "kick_sfx_s3k": "Global/InstaShield.wav",
        # Spin-Kick High Jump (the user's design, 2026-09-28; good for floating bosses): Y on the ground or in the air. A
        # 12-frame wind-up held still (crouched: not an attack), then straight up at 8 px per frame (her jump is 6.5:
        # about 146 px against her jump's 97, 1.5x), somersaulting in the blue swirl (5 frames, 3 game frames each), an
        # attack while she rises; at the top 14 frames coming upright (not an attack), then she falls in her ball, her
        # Flying Kick ready. Once per airborne period in the air; after one, 45 frames on the ground before the next
        "high_kick_windup": 12, "high_kick_rise": 0x80000, "high_kick_ticks": 3, "high_kick_recover": 14,
        "high_kick_cooldown": 45,
        "high_kick_sfx": "Insta Shield", "high_kick_sfx_s3k": "Global/InstaShield.wav", "high_kick_sfx_cd": "SFX_G_RELEASE",
    },
    40: {  # extra 34: Marine the Raccoon (testmods/marine/make_configs.py). The user's rework (2026-09-29): the Anchor Throw
        # on Y (replacing her Electric Blast), sea legs (water walk) and no drowning; no jump ability; her own ball
        "abilities": ["anchor_throw", "water_walk", "no_breathing"],
        # Anchor Throw (tools/anchor_throw.py, all four games): Y throws the anchor (the user's own drawing, slot 43) forward
        # in an arc on a chain drawn at runtime: 3 px a frame along, up at 3.5 px a frame, falling back at 0.156 px per
        # frame per frame (about 40 px high at the top, back at her hand's height about 140 px ahead); up + Y throws it
        # higher (2 px along, 5.5 up: about 95 px high). 48 frames out at most. It hits enemies, monitors and bosses (a
        # badnik hit sends it back). Biting into a wall or a ceiling (the tile's wall / ceiling solidity 12 px past its
        # centre, so a jump-through platform never catches it) it reels her in at 8 px a frame (Max's reel) until she's
        # within 24 px, stopped by the terrain or 30 frames on, then a small hop toward it (3 px up, 1 along). Landing on
        # a floor or at its range it's pulled back to her hand at 6 px a frame, the chain retracting, and gone; 20 frames
        # later she can throw again (one out at a time). Meanwhile she holds her throwing pose (slot 41, an attack): still
        # on the ground, falling as usual in the air
        "anchor_speed": 0x30000, "anchor_rise": 0x38000, "anchor_high_speed": 0x20000, "anchor_high_rise": 0x58000,
        "anchor_gravity": 0x2800, "anchor_frames": 48, "anchor_return": 0x60000, "anchor_cooldown": 20,
        "reel_speed": 0x80000, "reel_frames": 30, "latch_range": 24, "grapple_hop": 0x30000, "grapple_forward": 0x10000,
        "anchor_sfx": "Insta Shield", "anchor_sfx_s3k": "Global/InstaShield.wav", "anchor_sfx_cd": "SFX_G_RELEASE",
        "latch_sfx": "Catch", "latch_sfx_s3k": "Global/Grab.wav", "latch_sfx_cd": "SFX_G_GRAB",
        # Water walk (tools/water_walk.py): above water the surface is ground for her (stand, walk, run, roll, jump); down
        # held dives through it; she lands on it from above only (coming up from under it she jumps out and lands on it);
        # rising or bobbing water carries her, unless a ceiling is in the way (then she's left to sink). Underwater she
        # swims as usual and never drowns (no_breathing)
    },
    41: {  # extra 35: Mephiles the Dark (testmods/mephiles/make_configs.py). The user's picks: a very short Float as the jump
        # ability, a parabolic Crystal Shot on Y (a projectile that dips down, then arcs up once and is gone), the generic
        # ball in his blues. The rework (the user, 2026-09-29): he floats everywhere (his floating idle is his stand, walk,
        # run and top speed, leaning forward with his speed: float_lean), the Crystal Shot is twice the size and flies
        # through terrain, and down + Y is the Shadow Sink
        "abilities": ["umbrella", "melee", "sink"],
        # Float: jump in mid-air and he floats (slot 42: his full-speed run's frame, F1_11 flying flat, the user's pick
        # 2026-09-29; not an attack), sinking at 0.25 px per frame while jump is held, for half a second at most (Silver's
        # float, much shorter). Letting go ends it for that jump
        "umbrella_sink": 0x4000, "float_frames": 30,
        # Floating lean (float_lean, a draw effect like Honey's spin_lean): his walk, run and top speed (all his floating
        # idle's frames, drawn with full rotation) are drawn turned toward his travel, float_lean / 512 of a turn per px per
        # frame of his speed (ground speed; in the air his x speed), float_lean_max at most (32: 22.5 degrees, reached at
        # about 6.4 px per frame, his top speed). Upright when still. No slope rotation: he floats, so only the lean shows
        # on slopes too. S3&K's DLL reads the same numbers (NoSwapS3K.cpp FloatLean)
        "float_lean": 5, "float_lean_max": 32,
        # Shadow Sink (sink; the user's design 2026-09-29): down + Y on the ground (standing, walking or crouching, not
        # rolling or hurt) and he sinks into a dark pool: slot 47's frames 0-9 (the sheet's RISE1-3 then MELT1-7) forward,
        # sink_ticks game frames each (30 frames); then he's under, the purple smoke specks (frames 8 / 9, sink_under_ticks
        # each) for sink_max frames at most (2 s); then he rises (the sink's frames backward). Releasing down or Y rises at
        # once (from the frame he's at). Throughout he doesn't move (speed 0, no input: S1/S2 / CD the game's static
        # state, S3&K his input cleared) and nothing hurts him (the post-hit blink's rule without the flicker, as the
        # Puddle Slide). A hit that gets through anyway (a crush, a pit), a spring or an object taking over ends it. Then
        # sink_cooldown frames (1 s) before the next. Y alone still throws the Crystal Shot (down + Y on the ground never
        # does). Sound: Chaos' puddle's
        "sink_frames": list(range(10)), "sink_ticks": 3, "sink_under": [8, 9], "sink_under_ticks": 6,
        "sink_max": 120, "sink_cooldown": 60,
        "sink_sfx": "Bubble Bounce", "sink_sfx_s3k": "Global/BubbleBounce.wav", "sink_sfx_cd": "SFX_G_SLIDE",
        # (The melee numbers are only the Crystal Shot's throw pose, slots 43 / 44: his hand drawn back, then the palm
        # thrust out, floating; the pose is their last frame. And S3&K's fallback melee if its shot system is off, which
        # reaches no further than his body.) He stops to throw on the ground; in the air he keeps his speed
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        "melee_stop": True,
        # Crystal Shot (the user's design, 2026-09-28; both ways 2026-09-29; 2x and through terrain in the rework): a real
        # projectile in all four games, motion "dip": each Y throws a PAIR ("both_ways"), one each way, mirror images (the
        # second on his other side, moving and drawn the other way), each at 4 px per frame alone (his own speed added to
        # neither, "carry" false, so the two are symmetric), starting DOWN at 2 px per frame with a constant upward pull of
        # 1/8 px per frame each frame, so it dips 16 px (its lowest point 16 frames out, about 64 px away), levels out and
        # arcs up, ending 48 px above where it started after its 48-frame life (about 190 px away). Each starts 24 px out
        # from him (clear of his body at its new size) and 12 px above his centre (his hand). Walls, floors and ceilings
        # don't stop it ("terrain" false: it flies through them); gone after its life, offscreen or at its first hit. One
        # pair out at a time (max_alive 2), 2 s (120 frames) apart. The throw pose for 12 frames. Art: the sheet's own dark
        # orb (SFX section: the upright three turning, narrow, round, round, and back; 15x15 boxes, every 4 game frames),
        # enlarged exactly 2x nearest-neighbour ("scale" 2: 30x30, the faithful-art rule's integer enlargement), exact in
        # his own palette slots in every engine ("own_slots"); hitbox doubled to match, 28x28 (radius 12). Sound: Amy's
        # hammer throw (S3&K), the Insta Shield whoosh (S1/S2), Amy's hammer dash (CD)
        "shot": {
            "motion": "dip", "speed": 0x40000, "start_vy": 0x20000, "gravity": -0x2000, "max_fall": 0x80000,
            "lifetime": 48, "max_alive": 2, "cooldown": 120, "pose": 12, "x": 24, "y": -12, "radius": 12,
            "both_ways": True, "carry": False, "terrain": False,
            "art": {"sheet": "../Mephiles.png", "background": ["#09c2ff"], "own_slots": True, "ticks": 4, "scale": 2,
                    "drawings": [[18, 503, 15, 15], [32, 503, 15, 15], [47, 503, 15, 15], [32, 503, 15, 15]],
                    "hitbox": [-14, -14, 14, 14]},
            "s3k": {"sound": "Global/HammerThrow.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_HAMMERDASH"},
        },
    },
    42: {  # extra 36: Emerl, "Copycat" (testmods/emerl/make_configs.py). The user's design: four jump abilities, and Y
        # cycles which one is active (ability_cycle), with his copy flash; the generic ball in his golds
        "abilities": ["double_jump", "screw_kick", "jet_dash", "umbrella", "melee"],
        # In this order; the first at each stage load. Each Y press shows his copy flash (the melee's pose below) and
        # makes the next one active; the active one is what jump in mid-air does (from the normal air state only)
        "ability_cycle": ["double_jump", "screw_kick", "jet_dash", "umbrella"],
        # A head of his own per move (the user, 2026-09-29): the sheet's four loose variant heads, one per move in this
        # order (testmods/emerl/copy_heads.py MOVE_HEADS), on his idle, stance, walk, run and copy flash (the active
        # move's set shown in place of the game's: copy_head_in_out), and on each move's own pose
        "copy_heads": True,
        # Double Jump: Trip's, a second jump at 0.85x his jump, in his flying leap turned 45 degrees to point up (slot 41
        # frame 0, an attack; the user's pick, 2026-09-29) until he starts falling. Once per jump
        "double_jump": 0.85,
        # Dive: Mecha Sonic's Spike Ball angle (Sally's numbers): a kick 45 degrees down and forward at 6 px per frame on
        # each axis, in his dive kick (slot 41 frame 1, an attack), until he lands (no bounce)
        "kick_jump": True,
        "kick_x": 0x60000, "kick_y": 0x60000, "kick_bounce": 0,
        "kick_sfx": "Insta Shield", "kick_sfx_s3k": "Global/InstaShield.wav",
        # Air Dash: Metal Sonic's Jet Dash (6 px per frame, or his speed if faster, level for 20 frames), in his flying
        # leap (slot 41 frame 2, an attack). No hover after it
        "dash_frames": 20, "dash_speed": 0x60000,
        # Float: hold jump to sink at 0.25 px per frame (Metal's hover sink), facing us (slot 42), for up to 1 s per jump
        "umbrella_sink": 0x4000, "float_frames": 60,
        # Copy switch (Y): the melee with no shot: his red eye flash (slots 43 / 44: R5_1, R5_2, R5_1; 4 game frames each,
        # 12 in all; the box his own body, 10 px ahead, as the other poses), on the ground or in the air, without stopping
        "melee_sfx": "Lightning Jump", "melee_sfx_s3k": "Global/LightningJump.wav",
        "melee_reach": [10, 10, 10],
        "melee_ticks": 4,
    },
    # Mega Man (testmods/megaman/make_configs.py; a CROSSOVER extra, extras.py "crossover"). Keyed by his extras.py place,
    # looked up. The user's picks (2026-09-29): the Mega Buster on Y, the Charge Shot on holding Y, the Slide on down +
    # jump, no mid-air move, never a ball (extras.py "no_roll")
    _id_of("megaman"): {
        "abilities": ["ground_slide", "melee", "no_stomp"],  # (no_stomp: the user, 2026-10-02: his jump isn't an attack, his Slide is)
        "slide_running": True,  # down + jump slides out of a run too, as in Mega Man 3 (the user, 2026-09-29)
        # Slide (ground_slide, Ray Poward's: down + jump on the ground, from a crouch, where the Spin Dash was): Mega Man
        # 3's slide, forward at 5 px per frame at least for 20 frames, then 4 frames slowing to a stop (0.4 s), in the
        # Slide frames (slot 42: puddle_frames picks one per step of 2 game frames: SL2 with its speed lines first, then
        # SL1 / SL3, SLEND getting up at the end). Sonic 1/2: slot 42's frames use the .ani's low hitbox (3: top 2 px
        # above his centre), so he slides under low gaps. ground_slide's rules: nothing hurts him meanwhile, a jump, a
        # spring, a ledge or a hit ends it, no roll out of it, and he can fire during it
        "puddle_speed": 0x50000, "puddle_ticks": 2, "puddle_move": 10, "puddle_frames": [1, 1, 0, 0, 2, 2, 0, 0, 2, 2, 3, 3],
        "puddle_sfx": "Sliding", "puddle_sfx_s3k": "Global/Release.wav", "puddle_sfx_cd": "SFX_G_SLIDE",
        # (The melee numbers are only the Mega Buster's pose, slots 43 / 44: the arm coming up, then the buster out; in
        # the air Fire Jump's; the pose is their last frame. And S3&K's fallback melee if its shot system is off, which
        # reaches no further than his body.) He doesn't stop to fire (Mega Man shoots on the run); the pose shows standing
        # or in the air
        "melee_sfx": "Lightning Jump", "melee_sfx_s3k": "Global/LightningJump.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        # Mega Buster (the user's design, 2026-09-29): a real projectile in all four games, motion "straight": level
        # ahead the way he faces, 8 px per frame plus his own forward speed, no gravity; gone at a wall, after 40 frames,
        # offscreen or at its first hit. 3 out at once, 8 frames apart. It starts 16 px ahead of his centre, 2 px up (the
        # buster). The sheet has no loose pellet (its muzzle flash is part of the Fire frames), so the art is Gamma's: the
        # S3&K Lightning Shield's spark at half size (build_s3k_shot.py "spark"), 2 game frames each; hitbox 12x12. Sound:
        # the Lightning Shield's jump spark (S3&K, S1/S2); Sonic CD has none: the shield monitor's
        "shot": {
            "motion": "straight", "speed": 0x80000, "lifetime": 40, "max_alive": 3, "cooldown": 8,
            "pose": 10, "x": 16, "y": -2, "radius": 6,
            "art": {"spark": [0, 0, 1], "shrink": 2, "ticks": 2, "hitbox": [-6, -6, 6, 6]},
            "s3k": {"sound": "own:buster"},  # (his own sound, "sounds" below; in every game: "v4" / "cd" below are the fallback)
            "v4": {"sound": "Lightning Jump"},
            "cd": {"sound": "SFX_G_SHIELD"},
        },
        # Charge Shot (the user's design, 2026-09-29; a second real projectile, "shot2", "input" "charge"): holding Y
        # charges (from the press, which fired a Buster shot); from 30 frames (0.5 s) he flashes the sheet's Mega Buster
        # charge palettes (charge1 every other 4 frames; at 72 frames, 1.2 s, the charge is full: charge2a, charge2b and
        # his own in turn, 2 frames each: a runtime palette effect, the art untouched). Letting go of a full charge fires
        # it (sooner: nothing, the charge is lost; a hit loses it too): level ahead, 8 px per frame plus his own forward
        # speed, passing through what it hits ("pierce": badniks, monitors and bosses are hit and it flies on); gone at a
        # wall, after 50 frames (400 px) or offscreen. One out at a time. It starts 20 px ahead of his centre, 2 px up. The
        # Buster's pose shows with it. Art: the sheet's own teleport drops (Teleport TP2 / TP3, the light-blue energy he
        # beams in as), turned a quarter (rot90: the round end leads, the point trails), every 4 game frames in turn,
        # exact in his own palette slots; hitbox 24x24. Sound: the Spin Dash release (S3&K, S1/S2, CD)
        "shot2": {
            "motion": "straight", "input": "charge", "pierce": True, "charge_start": 30, "charge_full": 72,
            "speed": 0x80000, "lifetime": 50, "max_alive": 1, "cooldown": 8, "pose": 10, "x": 20, "y": -2, "radius": 12,
            "art": {"sheet": "MegaMan.png", "background": ["#841584", "#640664", "#470047"],
                    "drawings": [[71, 46, 16, 40, "rot90"], [117, 54, 25, 32, "rot90"]], "own_slots": True, "ticks": 4,
                    "hitbox": [-12, -12, 12, 12]},
            "s3k": {"sound": "own:charged_buster"},  # (his own: the full charge's, the only level)
            "v4": {"sound": "Release"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
        # his own sounds (tools/own_sounds.py; testmods/megaman/sfx/SOURCE.txt): the Mega Buster's and the charged shot's
        "sounds": {"buster": "sfx/Buster.wav", "charged_buster": "sfx/ChargedBuster.wav"},
    },
    # Ray Poward (Contra: Hard Corps; testmods/ray-poward/make_configs.py; a CROSSOVER extra, extras.py "crossover"; not
    # Ray the Flying Squirrel, extra 8). Keyed by his extras.py place, looked up. The user's design (2026-09-29): run-and-gun
    # on Y (aimed, autofire), his somersault as the jump and roll, a Slide on down + jump instead of the Spin Dash, the
    # wall cling, no mid-air move; normal hits
    **{_id_of("ray-poward"): {
        "abilities": ["wall_cling", "ground_slide", "melee", "no_stomp"],  # (no_stomp: the user, 2026-10-02: his somersault
        # isn't an attack; the roll shows his slide pose and his Slide breaks badniks, monitors and walls)
        # Wall Cling (Climbing): Trip's and Sticks' numbers (1.5 s on a wall at most, held for 0.5 s, then sliding at 0.5 px
        # per frame; climbing at 1 px per frame; the wall jump 4 px per frame away, 6 up; 10 frames before the same wall
        # again), in his Climbing frames (slot 47)
        "cling_frames": 90, "cling_hold": 30, "cling_slide": 0x8000, "climb_speed": 0x10000,
        "wall_jump_x": 0x40000, "wall_jump_y": 0x60000, "cling_lock": 10,
        "ledge_hop": 0x40000, "ledge_forward": 0x20000,
        # Slide (ground_slide: Hard Corps' slide): down + jump on the ground (from a crouch, where the Spin Dash was)
        # slides him forward at 6 px per frame at least for 20 frames, then 4 frames slowing to a stop (0.4 s), in the
        # Duck/Slide frames (slot 42: puddle_frames picks one per step of puddle_ticks game frames: 0 the slide, 2
        # kneeling at the end). The whole time nothing hurts him (the post-hit blink's rule, held at 3 each frame so he
        # doesn't flicker: Chaos' Puddle Slide's ground part). A jump, a spring, a ledge or a hit ends it; he can't roll
        # out of it. He can fire during it
        "puddle_speed": 0x60000, "puddle_ticks": 2, "puddle_move": 10, "puddle_frames": [0] * 10 + [2, 2],
        "puddle_sfx": "Sliding", "puddle_sfx_s3k": "Global/Release.wav", "puddle_sfx_cd": "SFX_G_SLIDE",
        # (The melee numbers are only the run-and-gun's aim poses, slots 43 / 44: one frame per aim, the shot's
        # "aim_pose" picks its aim's; and S3&K's fallback melee if its shot system is off, which reaches no further than
        # his body.) He doesn't stop to fire; the pose shows standing or in his somersault
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10] * 5,
        "melee_air_reach": [10] * 5,  # (S3&K: the air poses are slot 44's, centred as the somersault is)
        "melee_ticks": 4,
        # Run-and-gun (the user's design, 2026-09-29): weapon A's standard shot, a real projectile in all four games,
        # motion "straight", aimed with the d-pad (Fang's cork gun / Gamma's arm cannon: back, back-up, up, forward-up,
        # forward on the ground, all 8 in the air; nothing held: the way he faces). HOLD Y for autofire ("autofire": one
        # every cooldown frames while Y is down). 8 px per frame (diagonals the same overall) plus his own speed that way,
        # no gravity; gone at a wall, floor or ceiling it flies into, after 40 frames (320 px), offscreen or at its first
        # hit. 4 out at once, 8 frames apart. It starts 20 px out along the aim from 7 px above his centre (the gun's
        # muzzle, standing). The aim pose ("aim_pose": slot 43 / 44's frame k for aim k: 0 level, 1 forward-up, 2 up, 3
        # forward-down, 4 down) for 10 frames. Art: the sheet's own weapon A bullet (6x6, cut exactly; its muzzle flash
        # isn't used), in his own palette slots; hitbox 12x12 (twice the bullet: Sonic 1/2 need a square). Sound: the
        # Insta Shield whoosh (S3&K, S1/S2), the Release whoosh (CD)
        "shot": {
            "motion": "straight", "aim": True, "autofire": True, "aim_pose": True, "speed": 0x80000, "lifetime": 40,
            "max_alive": 4, "cooldown": 8, "pose": 10, "x": 20, "y": -7, "radius": 3,
            "art": {"sheet": "../ray-contra/RayContra.png", "drawings": [[122, 324, 6, 6]], "crop": True,
                    "background": ["#00ff00"], "own_slots": True, "ticks": 4, "hitbox": [-6, -6, 6, 6]},
            "s3k": {"sound": "Global/InstaShield.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
    }},
    # Sparkster (Rocket Knight Adventures; testmods/sparkster/make_configs.py; a separate download, extras.py "crossover").
    # Keyed by his extras.py place, looked up. The user's design (2026-09-29): the Sword Slash with its energy wave on Y,
    # the Rocket Burst (charge on held jump in mid-air, 8 ways, ricocheting) and the Rocket Spin; no pole hang; never a
    # ball (extras.py "no_roll")
    **{_id_of("sparkster"): {
        "abilities": ["rocket_burst", "melee"],
        # Rocket Burst (rocket_burst): press jump in mid-air and keep holding it to charge (he drifts to a stop and falls
        # at 1 px per frame at most, braced: CROUCH1); from 20 frames (1/3 s) it's charged and he flashes (the Backfire
        # frame every other 4 frames). Letting go fires it where the d-pad points, 8 ways, at 8 px per frame (5.66 per
        # axis diagonally), gravity off, for 36 frames (0.6 s, about 290 px), in the sheet's Rocket Dash frame for its
        # angle; walls and ceilings bounce it off (a ricochet). With no direction held, the Rocket Spin: the Spin Attack's
        # frames in place for 32 frames (2 game frames each). Both attack (the charge too); let go before 1/3 s, it
        # fizzles. Landing, a hit or a spring ends it; after the burst he falls with half its speed. Once per jump. Sounds:
        # the Spin Dash's charge and release
        "rocket_charge": 20, "rocket_frames": 36, "rocket_speed": 0x80000, "rocket_diag": 0x5A827,
        "rocket_sink": 0x10000, "rocket_spin_frames": 32, "rocket_spin_ticks": 2,
        "rocket_charge_sfx": "Charge", "rocket_sfx": "Release",
        "rocket_charge_sfx_s3k": "Global/Charge.wav", "rocket_sfx_s3k": "Global/Release.wav", "rocket_sfx_cd": "SFX_G_RELEASE",
        # (The melee numbers are only the Sword Slash's pose, slots 43 / 44: the Slash on the ground, the Fly Slash in the
        # air; the pose is their last frame, the swing's full swoosh. And S3&K's fallback melee if its shot system is off,
        # which reaches no further than his body.) He doesn't stop to slash
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10, 10],
        "melee_ticks": 4,
        # Sword Slash (the user's design, 2026-09-29): the sword's energy wave, a real projectile in all four games, motion
        # "straight": level ahead the way he faces, 6 px per frame plus his own forward speed, no gravity; gone at a wall,
        # after 30 frames (about 180 px), offscreen or at its first hit. 2 out at once, 12 frames apart. It starts 18 px
        # ahead of his centre, 4 px up (the sword). The swing's pose (slots 43 / 44's last frame) for 12 frames. Art: the
        # sheet's own Projectile frames (the spinning crescent: its four 32x24 cells as drawn, the last two the sheet's
        # reused frames; "crop", since the first touches the section's label), every 3 game frames in turn, exact in his
        # own palette slots; hitbox 20x20. Sound: the Insta Shield whoosh (S3&K, S1/S2), the Release whoosh (CD)
        "shot": {
            "motion": "straight", "speed": 0x60000, "lifetime": 30, "max_alive": 2, "cooldown": 12,
            "pose": 12, "x": 18, "y": -4, "radius": 10,
            "art": {"sheet": "Sparkster.png",
                    "background": ["#83c3cf", "#5e9da9", "#1a7c8f", "#0e5a69", "#3629a0", "#230e64", "#13053e"],
                    "drawings": [[292, 304, 32, 24], [325, 304, 32, 24], [358, 304, 32, 24], [391, 304, 32, 24]],
                    "crop": True, "own_slots": True, "ticks": 3, "hitbox": [-10, -10, 10, 10]},
            "s3k": {"sound": "Global/InstaShield.wav"},
            "v4": {"sound": "Insta Shield"},
            "cd": {"sound": "SFX_G_RELEASE"},
        },
    }},
    # Ristar (testmods/ristar/make_configs.py; a separate download, extras.py "crossover"). Keyed by his extras.py place,
    # looked up. The user's design (2026-09-29), all in tools/star_grab.py: the Grab on Y (aimed 8 ways, the arms drawn at
    # runtime; a badnik caught: yanked in to headbutt it; a wall or ceiling caught: pulled in to hang there), the Meteor
    # Strike from a hang (hold jump 1 s, let go), his own Spin/Roll as his ball, no other mid-air move
    **{_id_of("ristar"): {
        "abilities": ["star_grab"],
        # the arms: out 10 px a frame for 8 frames (80 px), back in 4
        "grab_step": 10, "grab_frames": 8, "retract_frames": 4,
        # terrain caught: pulled in at 8 px a frame until within 20 px of the point, stopped by the terrain, or 20 frames
        "reel_speed": 0x80000, "reel_frames": 20, "latch_range": 20,
        # a badnik caught: yanked in at 10 px a frame until within 16 px (or 16 frames), then a bounce off it: up 4 px a
        # frame, back 2
        "yank_speed": 0xA0000, "yank_frames": 16, "yank_range": 16, "bounce_y": 0x40000, "bounce_x": 0x20000,
        # hanging: climbing / moving along at 1 px a frame; letting go: a hop up 4 px a frame (off a wall, 2 away from it)
        "climb_speed": 0x10000, "hang_hop": 0x40000, "hang_push": 0x20000,
        # the Meteor Strike: jump held 12 frames shows the wind-up, 60 (1 s) launches it on letting go: 10 px a frame for
        # 60 frames
        "windup_show": 12, "windup_full": 60, "meteor_speed": 0xA0000, "meteor_frames": 60,
        "grab_sfx": "Insta Shield", "latch_sfx": "Catch", "meteor_sfx": "Release",
        "grab_sfx_s3k": "Global/InstaShield.wav", "latch_sfx_s3k": "Global/Grab.wav", "meteor_sfx_s3k": "Global/Release.wav",
        "grab_sfx_cd": "SFX_G_RELEASE", "latch_sfx_cd": "SFX_G_GRAB", "meteor_sfx_cd": "SFX_G_RELEASE",
    }},
    # Dynamite Headdy (testmods/headdy/make_configs.py; a separate download, extras.py "crossover"). Keyed by his extras.py
    # place, looked up. The user's design (2026-09-29), all in tools/head_throw.py: the Head Throw on Y (aimed 8 ways,
    # out and back, his body headless meanwhile; it hits enemies, monitors and bosses). No mid-air move; never a ball
    # (extras.py "no_roll")
    **{_id_of("headdy"): {
        "abilities": ["head_throw"],
        # the head variants (his power-up heads; the shared monitor_swap module will pick the index): each one's head
        # flies out step px a frame for frames frames and back as fast. Index 0, his own head: 10 px x 8 frames = 80 px.
        # Its art: slot 43's frames index * head_throw.HEAD_FRAMES and up (make_configs.py HEAD_VARIANTS / BUILT_VARIANTS)
        "head_variants": [{"name": "normal", "step": 10, "frames": 8}],
        "head_sfx": "Insta Shield", "head_sfx_s3k": "Global/InstaShield.wav", "head_sfx_cd": "SFX_G_RELEASE",
    }},
    # John Morris (Castlevania: Bloodlines; testmods/john-morris/make_configs.py; a separate download, extras.py
    # "crossover"). Keyed by his extras.py place, looked up. The user's design (2026-09-29): the whip on Y (aimed up-forward
    # or down in the air, low when crouching), the sub-weapon on up + Y (a ring each: "rings are hearts"), monitors
    # swapping the sub-weapon (monitor_swap), his own jump pose (extras.py "no_roll"), no whip upgrades, no whip swing
    **{_id_of("john-morris"): {
        "abilities": ["melee", "monitor_swap"],
        # The whip (the melee, the LV1 leather whip baked onto his attack frames: slots 43 standing / 44 in the air, the
        # melee_whip poses 41 crouching, 45 up-forward and 46 down in the air). 7 frames of 3 game frames (0.35 s): the
        # wind-up (4: the whip swinging back and over, his body's box only), then the whip out (3), reaching 53 px ahead of
        # his centre (52 crouching), 39 ahead and 50 up diagonally, 44 straight down (testmods/john-morris/make_configs.py
        # reach_report). He stands still for it on the ground. Up + Y is the sub-weapon's, not the whip's (in the air, up
        # with left or right held is the up-forward whip). Sound: the Insta Shield whoosh (S3&K, S1/S2), Release (CD)
        "melee_sfx": "Insta Shield", "melee_sfx_s3k": "Global/InstaShield.wav",
        "melee_reach": [10, 10, 10, 10, 53, 53, 53],
        "melee_air_reach": [10, 10, 10, 10, 53, 53, 53],
        "melee_ticks": 3,
        "melee_stop": True,
        "melee_whip": {
            "crouch": {"reach": [10, 10, 10, 10, 52, 52, 52], "top": [-12] * 7, "bottom": [20] * 7},
            "up": {"reach": [10, 10, 10, 10, 39, 39, 39], "top": [-20, -20, -20, -20, -50, -50, -50], "bottom": [20] * 7},
            "down": {"reach": [10] * 7, "top": [-20] * 7, "bottom": [20, 20, 20, 20, 44, 44, 44]},
        },
        # Sub-weapons (monitor_swap: the entry at the extra's swap index, "swap_shots" by name; the first at each stage's
        # start; every item monitor he breaks, by any means, makes the next one his, with a sound). Up + Y throws the
        # current one: a real projectile in all four games, "input" "up", costing "rings" rings (none: no throw, no sound).
        # Art: Items.png's sub-weapons, cut as drawn (quarter turns only), his own colours (the sheet's are the same Genesis
        # colours, converted a shade differently: build_s3k_shot takes the nearest, within 5 of 255 per channel).
        "monitor_swap": ["axe", "cross", "holy_water"],
        "swap_icon": True,  # (the current sub-weapon at the top middle of the screen, in a dark box: tools/monitor_swap.py)
        "swap_sfx": "Menu Select", "swap_sfx_s3k": "Global/Grab.wav", "swap_sfx_cd": "SFX_G_SELECT",
        "swap_shots": {
            # Axe: lobbed up and forward (6 px per frame up, 2 ahead plus his forward speed), falling with Mario's gravity
            # through everything ("terrain" false: walls, floors and ceilings don't stop it) and through what it hits
            # ("pierce"); gone after 2 s or once it falls offscreen. 2 out at once, 20 frames apart. From 16 px above his
            # centre. Art: the big thrown axe (its upright and level drawings, each also turned half round: a full turn in
            # 4 frames of 3 game frames); hitbox 24x24. Sound: Amy's hammer throw / the Insta Shield whoosh / hammer dash
            "axe": {
                "motion": "drop", "input": "up", "rings": 1, "terrain": False, "pierce": True,
                "speed": 0x20000, "start_vy": -0x60000, "gravity": 0x3800, "max_fall": 0x80000, "lifetime": 120,
                "max_alive": 2, "cooldown": 20, "pose": 0, "x": 8, "y": -16, "radius": 12,
                "art": {"sheet": "Items.png", "background": ["#bafeca"],
                        "drawings": [[105, 128, 20, 32], [136, 139, 32, 20, "rot180"], [105, 128, 20, 32, "rot180"],
                                     [136, 139, 32, 20]], "ticks": 3, "hitbox": [-12, -12, 12, 12]},
                "s3k": {"sound": "Global/HammerThrow.wav"},
                "v4": {"sound": "Insta Shield"},
                "cd": {"sound": "SFX_G_HAMMERDASH"},
            },
            # Cross (Bloodlines' own cross, its boomerang): Sticks' boomerang flight (out at 8 px per frame, slowing by 1/4
            # px per frame, then homing back and caught within 16 px), through what it hits both ways ("pierce"); no
            # terrain. Gone when caught, after 2.5 s or offscreen. 2 out at once, 20 frames apart. From 16 px ahead, 8 px
            # above his centre. Art: its four red spinning drawings, 2 game frames each; hitbox 20x20
            "cross": {
                "motion": "boomerang", "input": "up", "rings": 1, "pierce": True,
                "speed": 0x80000, "decel": 0x4000, "return_speed": 0xA0000, "return_accel": 0x4000, "catch": 16,
                "lifetime": 150, "max_alive": 2, "cooldown": 20, "pose": 0, "x": 16, "y": -8, "radius": 10,
                "art": {"sheet": "Items.png", "background": ["#bafeca"],
                        "drawings": [[33, 100, 13, 20], [56, 102, 18, 18], [90, 107, 20, 13], [125, 102, 18, 18]],
                        "ticks": 2, "hitbox": [-10, -10, 10, 10]},
                "s3k": {"sound": "Global/HammerThrow.wav"},
                "v4": {"sound": "Insta Shield"},
                "cd": {"sound": "SFX_G_HAMMERDASH"},
            },
            # Holy Water: the vial tossed short and low (1.5 px per frame ahead plus his forward speed, 2 up, Mario's
            # gravity); on the floor it bursts into blue flames ("burn": its own frames, held there for 60 frames, 1 s,
            # hurting whatever touches them: "pierce"). A wall ends the vial. 2 out at once, 20 frames apart. From 12 px
            # ahead, 4 px above his centre. Art: the tossed vial; the flames the wide and the tall blue flame, 4 game frames
            # each; hitboxes 12x12 (vial), 24x24 (flames). Sound: the Release whoosh
            "holy_water": {
                "motion": "drop", "input": "up", "rings": 1, "pierce": True,
                "speed": 0x18000, "start_vy": -0x20000, "gravity": 0x3800, "max_fall": 0x80000, "lifetime": 90,
                "max_alive": 2, "cooldown": 20, "pose": 0, "x": 12, "y": -4, "radius": 8,
                "art": {"sheet": "Items.png", "background": ["#bafeca"], "drawings": [[33, 73, 14, 14]], "ticks": 4,
                        "hitbox": [-6, -6, 6, 6]},
                "burn": {"lifetime": 60,
                         "art": {"sheet": "Items.png", "background": ["#bafeca"],
                                 "drawings": [[81, 72, 29, 16], [120, 66, 16, 22]], "ticks": 4,
                                 "hitbox": [-12, -12, 12, 12]}},
                "s3k": {"sound": "Global/Release.wav"},
                "v4": {"sound": "Release"},
                "cd": {"sound": "SFX_G_RELEASE"},
            },
        },
    }},
    # Ecco the Dolphin (Ecco: The Tides of Time; testmods/ecco/make_configs.py; a separate download, extras.py
    # "crossover"). Keyed by his extras.py place, looked up. The user's design (2026-09-30, "painful but beatable"): on
    # land he flops on his side, slow, with a small hop and no ball (extras.py "no_roll"), but can always finish a stage;
    # he never drowns. The free swim in water is added separately (art: his slots 41 Swim, 42 Charge, 43 Leap).
    **{_id_of("ecco"): {
        "abilities": ["no_breathing", "physics", "free_swim"],
        # Free swim (S3&K first: native/src/EccoSwim.h; Sonic 1/2 and CD later): underwater the d-pad steers him anywhere,
        # turning 8 degrees a frame toward it, building 0.25 px per frame each frame to 8 px per frame (faster than anyone),
        # gliding to a stop (0.125 a frame) with nothing held. Slot 41: 8 directions x 6 frames (4 game frames each at full
        # speed, slower when slow). Y: the charge ram, 20 frames at 12 px per frame along his heading, an attack (slot 42:
        # 8 x 8, the blur last), then 30 frames' rest. Out of the surface going up: the leap (slot 43: the 8-frame
        # somersault, 4 game frames each)
        "swim_speed": 0x80000, "swim_accel": 0x4000, "swim_drag": 0x2000, "swim_turn": 8, "swim_dirs": 8,
        "swim_cycle": 6, "swim_ticks": 4, "ram_frames": 20, "ram_speed": 0xC0000, "ram_cooldown": 30, "ram_cycle": 8,
        "ram_sfx_s3k": "Global/Release.wav", "leap_frames": 8, "leap_ticks": 4,
        # Land: top speed 0.45 (2.7 px a frame for Sonic's 6), acceleration 0.45 (about 2.5 s from a standstill to that),
        # air acceleration 0.6 (the hop still carries him forward over a gap). Jump 0.85: 5.5 px a frame, rising about
        # 70 px (Sonic about 97, Knuckles about 82), so it clears the usual 2-3 block (32-48 px) steps with room to
        # spare. Springs set the speed themselves, so they launch him as anyone. From a standstill he walks up slopes
        # to about 10 degrees (Sonic about 22); steeper ones he hops up.
        "physics": {"top_speed": 0.45, "acceleration": 0.45, "air_acceleration": 0.6, "jump": 0.85},
    }},
}

if KIT:  # (the Creator Kit: the entries above are NoSwap's own characters, none of them there; only the creator's below)
    ABILITIES.clear()
# Characters defined by a character.json bring their own moves (character_json.abilities_entry), under the build ID the
# registry gives their key (tools/registry.py): they need no entry above.
for _e in EXTRAS:
    if _e["id"] not in ABILITIES and character_json.has_json(_e["art"]):
        ABILITIES[_e["id"]] = character_json.abilities_entry(_e["art"])

# Own sounds (tools/own_sounds.py) of the entries above: an entry's "sounds" ({name: file in its art folder}) moves to
# OWN_SOUNDS[id], and its S3&K sound fields' "own:<name>" become their Data/SoundFX paths (a character.json's are
# resolved as it loads: character_json.abilities_entry)
OWN_SOUNDS = {}
for _i, _c in list(ABILITIES.items()):
    if isinstance(_c, dict) and _c.get("sounds"):
        import own_sounds as _own
        _art = next(e["art"] for e in EXTRAS if e["id"] == _i)
        OWN_SOUNDS[_i] = {k: _art / v for k, v in _c.pop("sounds").items()}
        ABILITIES[_i] = _own.resolve(_c, _art.name, set(OWN_SOUNDS[_i]))

# Debugging: NOSWAP_DROP=22,23 builds without those extras' moves (they play as their base), to bisect a problem
# NOSWAP_KEEP=26 builds with only those extras' moves ("none": no extra's), for character packages
# (tools/build_packages.py)
_keep = __import__("os").environ.get("NOSWAP_KEEP")
if _keep is not None:
    _ids = {int(x) for x in _keep.split(",") if x.strip() and x.strip() != "none"}
    for _i in list(ABILITIES):
        if _i not in _ids:
            ABILITIES.pop(_i)
# (NOSWAP_DROP=25:magnetic leaves out one module of one extra)
for _i in __import__("os").environ.get("NOSWAP_DROP", "").split(","):
    if ":" in _i:
        _n, _m = _i.split(":")
        if int(_n) in ABILITIES:
            ABILITIES[int(_n)]["abilities"] = [a for a in ABILITIES[int(_n)]["abilities"]
                                         if a != character_json.renamed(_m.strip())]  # (25:popgun still works)
    elif _i.strip():
        ABILITIES.pop(int(_i), None)

PHYSICS_COLUMNS = ["top_speed", "acceleration", "air_acceleration", "air_deceleration",
                   "skid_speed", "rolling_friction", "jump", "jump_cap"]

ALIAS_OF = {e["id"]: e["alias"] for e in EXTRAS}


def has(extra_id, ability):
    return ability in ABILITIES.get(extra_id, {}).get("abilities", [])


def with_ability(ability):
    return [i for i in ABILITIES if has(i, ability)]


def shot(i, engine):
    """The extra's projectile ("shot") for an engine ("s3k", "v4": Sonic 1/2, or "cd"), its per-engine numbers applied; None
    without one. An extra with swap shots (monitor_swap: John's sub-weapons) has its first one here (swap_shots: all)."""
    c = ABILITIES.get(i, {}).get("shot")
    if not c and ABILITIES.get(i, {}).get("swap_shots"):
        return swap_shots(i, engine)[0]
    if not c or engine not in c.get("engines", ("s3k", "v4", "cd")):  # ("engines": only these games have it yet)
        return None
    out = {k: v for k, v in c.items() if k not in ("s3k", "v4", "cd", "engines")}
    out.update(c.get(engine, {}))
    return out


def swap_shots(i, engine):
    """monitor_swap's shots ("swap_shots", John Morris' sub-weapons): one shot config per entry of the extra's
    "monitor_swap" list, in its order, each with its per-engine numbers applied (as shot()); [] without. The one thrown is
    the entry at the extra's swap index (tools/monitor_swap.py). Rules: check_swap_shots."""
    c = ABILITIES.get(i, {})
    if not c.get("swap_shots"):
        return []
    import monitor_swap
    out = []
    for name in monitor_swap.entries(i):
        if name not in c["swap_shots"]:
            sys.exit(f"swap_shots: extra {i}: no shot for monitor_swap entry {name!r}")
        s = c["swap_shots"][name]
        d = {k: v for k, v in s.items() if k not in ("s3k", "v4", "cd")}
        d.update(s.get(engine, {}))
        if "burn" in d:  # (its flames' art and numbers, per engine too)
            d["burn"] = dict(d["burn"])
        out.append(d)
    return out


def check_swap_shots(i):
    """swap_shots' rules: no "shot" / "shot2" beside them, has(i, "monitor_swap"), each a plain shot check_shot accepts
    (thrown with Y, or "input" "up": up + Y, Y alone being the melee), none homing, aimed, cycled or charged. "burn"
    ({lifetime, art}: on the floor it stays and burns for lifetime frames, its own frames): a drop's. "terrain" false
    (no walls, floors or ceilings end it): a drop, bounce or straight shot's. "rings": rings each throw costs (fewer: no
    throw)."""
    c = ABILITIES[i]
    if c.get("shot") or c.get("shot2") or not has(i, "monitor_swap"):
        sys.exit(f"swap_shots: extra {i}: needs \"monitor_swap\" and no \"shot\" / \"shot2\"")
    for s in swap_shots(i, "v4"):
        if s["motion"] in ("homing", "ground") or any(s.get(k) for k in ("aim", "cycle", "up", "ground", "autofire",
                                                                          "both_ways", "pose_always")):
            sys.exit(f"swap_shots: extra {i}: a plain shot (not homing / ground, no aim, cycle, up, ground, autofire, "
                     "both_ways or pose_always)")
        if s.get("input", "y") not in ("y", "up") or (s.get("input") == "up" and not has(i, "melee")):
            sys.exit(f"swap_shots: extra {i}: \"input\" \"up\" (Y alone is the melee: needs one) or left out")
        if "burn" in s and (s["motion"] != "drop" or set(s["burn"]) - {"lifetime", "art"} or "art" not in s["burn"]):
            sys.exit(f"swap_shots: extra {i}: \"burn\" {{lifetime, art}} is a drop's")
        if s.get("terrain", True) is False and s["motion"] not in ("drop", "bounce", "straight"):
            sys.exit(f"swap_shots: extra {i}: \"terrain\" false is a drop / bounce / straight shot's")
        if "burn" in s and s.get("terrain", True) is False:
            sys.exit(f"swap_shots: extra {i}: a burning shot needs the floor (\"terrain\")")
        if not 0 <= s.get("rings", 0) <= 99:
            sys.exit(f"swap_shots: extra {i}: \"rings\" 0-99")


def up_shot(i):
    """The extra's shot is thrown with UP + Y (shot "input" "up": John's sub-weapons); Y alone stays its melee (the whip). In
    the air, up with left or right held is the melee's up-forward whip instead (melee_whip "up")."""
    s = shot(i, "v4")
    return bool(s) and s.get("input") == "up"


def whips():
    """Extras whose melee has whip poses (melee_whip: John's). Only a build with one has their tables and code."""
    return [i for i in ABILITIES if v4_melee(i) and ABILITIES[i].get("melee_whip")]


WHIP_POSES = ("crouch", "up", "down")  # melee_whip's poses: NoSwap_whipAim 1-3, NoSwap_MeleePose rows 2-4, slots 41 / 45 / 46

# melee_run / melee_up (Axel's Grand Upper and Dragon Wing): two more ground poses of the melee, picked as Y is pressed:
# melee_run when he's running (on the ground, at least its "speed" either way), melee_up with up held (standing or
# looking up) when he has its "rings" (taken then; fewer: the plain melee). Each has its own frames (slots 45 / 46) and
# reach / top / bottom per frame; melee_run's "boost" holds him at least that fast the way he faces while it lasts (in
# place of melee_stop), melee_up's "radial" reaches all around him. Sonic 1/2: NoSwap_whipAim 4 / 5 (the whip's value:
# never both) and NoSwap_MeleePose rows 5 / 6.
VARIANT_POSES = {"melee_run": (4, 5, 45), "melee_up": (5, 6, 46)}  # option -> (NoSwap_whipAim, row, ability slot)
VARIANT_SLOT_MOVES = ("aim_dash", "melee_whip", "charge", "psycho_grab", "star_grab", "head_throw", "rocket_burst",
                      "free_flight", "free_swim")  # (moves whose own frames are slots 45 / 46, or that take Y themselves)


def variants():
    """Extras whose melee has a running or an up + Y pose (melee_run / melee_up: Axel's). Only a build with one has
    their tables and code, so the other extras' scripts are unchanged."""
    return [i for i in ABILITIES if v4_melee(i) and any(ABILITIES[i].get(k) for k in VARIANT_POSES)]


def check_variants(i):
    """melee_run / melee_up's rules (every engine): the melee's, with no move of their slots (45 / 46), a melee of its
    own on Y (no shot on Y alone, no nuke or cost: those are the whole move's), and per-frame lists of one length."""
    c = ABILITIES[i]
    for k in VARIANT_POSES:
        v = c.get(k)
        if not v:
            continue
        if not has(i, "melee"):
            sys.exit(f"{k}: extra {i}: a part of the melee (\"melee\" in its list)")
        clash = [m for m in VARIANT_SLOT_MOVES if has(i, m) or c.get(m)]
        if clash or c.get("melee_nuke") or c.get("melee_cost") or cycle(i) or (shot(i, "v4") and not v4_melee(i)):
            sys.exit(f"{k}: extra {i}: its frames are slots 45 / 46 and it's a melee of its own on Y: not with "
                     f"{', '.join(clash) or 'a shot on Y, melee_nuke, melee_cost or ability_cycle'}")
        if not v.get("reach") or len({len(v.get(f, v["reach"])) for f in ("reach", "top", "bottom")}) != 1:
            sys.exit(f"{k}: extra {i}: \"reach\" (and \"top\" / \"bottom\", if given) per frame, of one length")
        extra = set(v) - {"reach", "top", "bottom", "sfx_s3k"} - ({"speed", "boost"} if k == "melee_run" else {"rings", "radial"})
        if extra:
            sys.exit(f"{k}: extra {i}: unknown {', '.join(sorted(extra))}")
        if k == "melee_run" and not v.get("speed", 0) > 0:
            sys.exit(f"melee_run: extra {i}: \"speed\" (the least ground speed that counts as running) above 0")
        if k == "melee_up" and not 0 <= v.get("rings", 0) <= 99:
            sys.exit(f"melee_up: extra {i}: \"rings\" 0-99")


def variant_poses(i):
    """[(row, (reach, top, bottom))] of melee_run / melee_up (rows 5 / 6 of NoSwap_MeleePose); [] without."""
    out = []
    for k, (_, row, _) in VARIANT_POSES.items():
        v = ABILITIES[i].get(k)
        if v:
            check_variants(i)
            n = len(v["reach"])
            out.append((row, (v["reach"], v.get("top", [-20] * n), v.get("bottom", [20] * n))))
    return out


# melee_run / melee_up, Sonic 1/2: up + Y may start the melee looking up (Player_State_LookUp) for an extra with
# melee_up (NoSwap_MeleeUpRings 0 or more; -1: none)
VARIANT_STATES = """			GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeUpRings)
			if temp1 >= 0 // (melee_up: looking up too)
				CheckEqual(player.state, Player_State_LookUp)
				temp0 |= checkResult
			end if
"""
# ... the pose picked as Y is pressed: 5 up + Y (with its rings: taken), else 4 running, else 0 the plain one
VARIANT_START = """				GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeVariant)
				if temp1 == true // melee_run / melee_up: the pose by how he is as Y is pressed (tools/abilities.py VARIANT_START)
					NoSwap_whipAim = 0
					if player.gravity == GRAVITY_GROUND
						if player.up == true
							GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeUpRings)
							if temp1 >= 0
								if player.rings >= temp1 // (fewer rings: the plain melee)
									player.rings -= temp1
									NoSwap_whipAim = 5
								end if
							end if
						end if
						if NoSwap_whipAim == 0
							GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeRun)
							if temp1 > 0
								temp2 = player.speed
								if temp2 < 0
									FlipSign(temp2)
								end if
								if temp2 >= temp1 // running
									NoSwap_whipAim = 4
								end if
							end if
						end if
					end if
				end if
"""
# ... its frames (rows 5 / 6) on the ground and in the air alike (Grand Upper off a ledge goes on), and the run's boost:
# at least that fast the way he faces (melee_stop's standing still above is undone)
VARIANT_POSE = """			GetTableValue(temp6, stage.playerListPos, NoSwap_MeleeVariant)
			if temp6 == true
				if NoSwap_whipAim == 4 // melee_run: its frames, and its boost
					player.animation = ANI_NOSWAP_ATTACK_UP
					temp3 = stage.playerListPos
					temp3 += ROW5
					GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeRunBoost)
					if temp1 > 0
						if player.gravity == GRAVITY_GROUND
							temp2 = player.speed
						else
							temp2 = player.xvel
						end if
						if player.direction == FACING_LEFT
							FlipSign(temp2)
						end if
						if temp2 < temp1
							temp2 = temp1
						end if
						if player.direction == FACING_LEFT
							FlipSign(temp2)
						end if
						if player.gravity == GRAVITY_GROUND
							player.speed = temp2
						else
							player.xvel = temp2
						end if
					end if
				end if
				if NoSwap_whipAim == 5 // melee_up: its frames
					player.animation = ANI_NOSWAP_ATTACK_DOWN
					temp3 = stage.playerListPos
					temp3 += ROW6
				end if
			end if
"""
# ... and melee_up's reach all around him ("radial"), in place of the extra's NoSwap_MeleeRadial
VARIANT_RADIAL = """			GetTableValue(temp0, stage.playerListPos, NoSwap_MeleeVariant)
			if temp0 == true // (temp0 is free here; temp2 still holds the pose's frame count)
				if NoSwap_whipAim == 5
					GetTableValue(temp6, stage.playerListPos, NoSwap_MeleeUpRadial)
				end if
			end if
"""


def shot2(i, engine):
    """The extra's second projectile ("shot2": thrown with DOWN + Y while "shot" takes Y alone; Robotnik's Bomb Drop) for
    an engine, as shot(); None without one. The engines tell the two apart per shot (S1/S2: its frames are TailsObject
    frames shots_v4.ROW2_FRAME and up; CD: its animation shots_v3.ANI_SHOT2; S3&K: the DLL's marker)."""
    c = ABILITIES.get(i, {}).get("shot2")
    if not c:
        return None
    out = {k: v for k, v in c.items() if k not in ("s3k", "v4", "cd")}
    out.update(c.get(engine, {}))
    return out


def check_shot2(i, engine="v4"):
    """shot2's rules (every engine): "input" "down", the extra's "shot" thrown with Y alone (not "down", no melee on Y
    then), and a plain bounce / straight / drop shot: not aimed, no "up", "ground" or "cycle", no throw pose."""
    s, s1 = shot2(i, engine), shot(i, engine)
    if not s1 or s1.get("input", "y") != "y":
        sys.exit(f"shot2: extra {i}: needs a \"shot\" thrown with Y alone (its \"input\" left out)")
    if s.get("input") not in ("down", "charge"):
        sys.exit(f"shot2: extra {i}: \"input\" must be \"down\" (down + Y throws it; Y alone throws \"shot\") or "
                 "\"charge\" (Y held, then let go of a full charge)")
    if s["motion"] not in ("bounce", "straight", "drop") or any(s.get(k) for k in ("aim", "up", "ground", "cycle")) \
            or (s.get("pose") and s["input"] != "charge"):
        sys.exit(f"shot2: extra {i}: a bounce / straight / drop shot, without aim, up, ground, cycle or pose (a charge "
                 "shot may have a pose: the first shot's)")
    if s["input"] == "charge" and not (0 < s.get("charge_start", 0) < s.get("charge_full", 0)):
        sys.exit(f"shot2: extra {i}: a charge shot needs charge_start (its flash starts) < charge_full (it's ready)")
    return s


def charge_shots():
    """Extras whose second shot is a charge shot (shot2 "input" "charge": Mega Man's Charge Shot)."""
    return [i for i in ABILITIES if (shot2(i, "v4") or {}).get("input") == "charge"]


def charge_palettes(i):
    """A charge shot's flash colours, from the extra's Sonic 2 art config ("charge_palettes", its make_configs.py):
    [{own slot: 0xRRGGBB}] for the phases charge1, charge2a, charge2b."""
    import json
    e = next(x for x in EXTRAS if x["id"] == i)
    cfg = json.loads(next(e["art"].glob("*_s2.json")).read_text())
    pals = cfg.get("charge_palettes")
    if not pals:
        sys.exit(f"shot2: extra {i}: a charge shot's flash needs \"charge_palettes\" in its art config")
    return [{int(s): int(c.lstrip("#"), 16) for s, c in pals[k].items()} for k in ("charge1", "charge2a", "charge2b")]


DIAG = 46341  # 1/sqrt(2) in 16.16: an aimed shot's diagonal speed per axis (the same speed overall)


def down_shot(i):
    """The extra's shot is thrown with DOWN + Y (shot "input": "down": Mecha Sonic's spike ball); Y without down stays
    its melee (the Jet Boost), and down + Y in the jump ball throws rather than transforms."""
    s = ABILITIES.get(i, {}).get("shot")
    return bool(s) and s.get("input") == "down"


def shot_diag(s):
    return s["speed"] * DIAG >> 16


def shot_pose_frame(i, game, slot, reach_key):
    """The throw pose's frame (the shot's pose shows one): the last frame of animation `slot` in the extra's built
    player .ani for `game` (extras.player_ani), or without one, of its melee reach list (reach_key). -1: no pose."""
    e = next((x for x in EXTRAS if x["id"] == i), None)
    try:
        anims = player_ani(e, game)["anims"] if e else []
    except SystemExit:
        anims = []
    if slot < len(anims) and anims[slot]["frames"]:
        return len(anims[slot]["frames"]) - 1
    c = ABILITIES[i]
    return len(c.get(reach_key, c.get("melee_reach", []))) - 1


def v4_melee(i):
    """Sonic 1/2's melee: an extra with a real shot throws that instead (its melee frames are the throw pose)."""
    return has(i, "melee") and (not shot(i, "v4") or down_shot(i) or slam_shot(i) or up_shot(i))  # (a down + Y shot
    # keeps plain Y's melee; a slam's isn't thrown with Y at all; nor an up + Y one: John's whip)


def slam_shot(i):
    """The extra's shot is thrown by its Hammer Drop's landing, two at once (shot "input": "slam": Bark's shockwaves), not
    with Y: Y stays the melee."""
    s = ABILITIES.get(i, {}).get("shot")
    return bool(s) and s.get("input") == "slam"


ALIASES = f"""
// [NoSwap] Ability modules (tools/abilities.py). Only names other scripts read are public: the engine's public
// alias table is small (all scripts share it; overflowing it broke Sonic 2's player script)
private alias object.value15 : player.noswapAbility // Jet Dash: >0 dash frames left; <0 hover frames used; 0 fresh jump
public alias {ANI_ATTACK} : ANI_NOSWAP_ATTACK
private alias {ANI_HOVER} : ANI_NOSWAP_HOVER
public alias {ANI_MELEE} : ANI_NOSWAP_MELEE
public alias {ANI_MELEE_AIR} : ANI_NOSWAP_MELEE_AIR
public alias {ANI_ATTACK_UP} : ANI_NOSWAP_ATTACK_UP
public alias {ANI_ATTACK_DOWN} : ANI_NOSWAP_ATTACK_DOWN
private alias {ANI_GLIDE_UP} : ANI_NOSWAP_GLIDE_UP
private alias {ANI_GLIDE_DOWN} : ANI_NOSWAP_GLIDE_DOWN
private alias {ANI_CLING} : ANI_NOSWAP_CLING
private alias {ANI_SURGE['idle']} : ANI_NOSWAP_SURGE_IDLE
private alias {ANI_SURGE['run']} : ANI_NOSWAP_SURGE_RUN
private alias {ANI_SURGE['sprint']} : ANI_NOSWAP_SURGE_SPRINT
"""

# Extras always play alone, so single-player ability state can live in script values
VALUES = """
// [NoSwap] Ability state (extras always play alone)
public value NoSwap_pogo = 0 // true while pogo bouncing
public value NoSwap_melee = 0 // game frames left in the current shot
// Ray's glide (Mania's Player_State_RayGlide), and Tikal's Spirit Flight: its own velocity, since the air state
// adds gravity first
public value NoSwap_glideVX = 0
public value NoSwap_glideVY = 0
public value NoSwap_glideLeft = 0 // the direction it started in
public value NoSwap_glideUp = 0 // true: swooping up
public value NoSwap_glideAngle = 0 // 0x10 (diving) to 0x70 (climbing)
public value NoSwap_glideLift = 0 // a swoop's upward push
public value NoSwap_glideCap = 0 // speed cap
public value NoSwap_glidePower = 0 // 256, less after each swoop
public value NoSwap_plow = 0 // a Hammer Drop plows through badniks instead of bouncing off them
public value NoSwap_shellSafe = 0 // spike_shell: true when the shell took this spike hit
public value NoSwap_cooldown = 0 // frames until a melee with melee_cooldown can fire again
public value NoSwap_flags = 0 // what the shared scripts need to know about the playing extra: noswap_common.FLAG_BITS
public value NoSwap_grappleX = 0 // ear_grapple: where the ear latched on
public value NoSwap_grappleY = 0
public value NoSwap_grappleDir = 0 // the direction the ear went out in
public value NoSwap_grappleUsed = false // grapple_y: the Ear Grapple was used this airborne period
public value NoSwap_jumpChain = 0 // triple_jump: the last jump's number in the chain (1-3; 4 once the third's flip is over)
public value NoSwap_jumpWindow = 0 // triple_jump: frames left on the ground to jump again
public value NoSwap_cling = 0 // wall_cling: frames on the wall (0: not clinging)
public value NoSwap_clingDir = 0 // the wall's side (FACING_RIGHT: on her right); after, the side she let go of
public value NoSwap_clingLock = 0 // frames (away from it) before she can cling to that side again
public value NoSwap_shotCooldown = 0 // shot: frames before the next throw
public value NoSwap_shotPose = 0 // shot: throw pose frames left (> 0 standing, < 0 in the air)
"""
# Always declared (private: the shared scripts read NoSwap_flags' surging bit instead)
SURGE_SHARED = """public value NoSwap_surge = 0 // power_surge: frames left, the surge (above surge_cooldown), then its cooldown
"""
# Only declared when an extra has the move
SURGE_VALUES = """public value NoSwap_surgeFrom = 0 // the game's animation while a Power Surge one is shown in its place (-1: none;
// NoSwap_SurgeIn sets it every frame before anything reads it)
"""
ZIP_VALUES = """public value NoSwap_zipCarry = 0 // thunder_zip: the speed she keeps after the zip (its sign: the zip's direction)
"""
PUDDLE_VALUES = """public value NoSwap_puddle = 0 // puddle_slide: game frames left of the puddle (melting, sliding, rising)
"""
SHOT_NEXT_VALUES = """public value NoSwap_shotNext = 0 // a "cycle" shot: the frame the next throw takes (Flicky's critters)
"""
POGO_SHOT_VALUES = """public value NoSwap_pogoShotCooldown = 0 // shot: frames before the next throw, for an extra with the pogo
"""  # (NoSwap_shotCooldown shares its value with NoSwap_pogo: PACKED_VALUES; Fang's cork gun, shot_cooldown_name)
BUSTER_VALUES = """private value NoSwap_busterCharge = 0 // a charge shot (shot2 "input" "charge"): frames Y has been held
"""  # (packed: noswap_common.PACKED_VALUES)
CHARGE_VALUES = """public value NoSwap_charge = 0 // charge: the speed it set last frame, signed by its direction (0: none)
"""
SPARK_VALUES = """public value NoSwap_spark = 0 // the charge's Shine Spark: 0 none; 1..spark_store stored (frames left); SPARK_ACTIVE +
// its kind (1 up, 2 up-forward, 3 forward), + 100 going left: flying
"""  # (packed: noswap_common.PACKED_VALUES)
SPARK_ACTIVE = 1000  # NoSwap_spark (S1/S2), NoSwap.Spark (CD), g_ab.spark (the DLL's SPARK_ACTIVE): above this, flying


def sparks():
    """Extras with the charge's Shine Spark (its "spark_*" numbers: Heavy's)."""
    out = [i for i in with_ability("charge") if ABILITIES[i].get("spark_speed")]
    for i in out:
        c = ABILITIES[i]
        if not 0 < c["spark_store"] < SPARK_ACTIVE or c["spark_skid_frames"] >= c["spark_store"] \
                or len(c["spark_glow"]) != 3:
            sys.exit(f"spark: extra {i}: spark_store 1-{SPARK_ACTIVE - 1}, spark_skid_frames under it, 3 spark_glow amounts")
    return out


def spark_diag(i):
    return spark_diag_of(ABILITIES[i])


def spark_diag_of(c):
    """The Shine Spark's up-forward speed per axis (the same speed overall; 0 without one)."""
    return c.get("spark_speed", 0) * DIAG >> 16


def spark_glow_colours(i):
    """The Shine Spark's glow (a runtime palette effect): [{slot: 0xRRGGBB}] for its 3 amounts (spark_glow, of 256),
    each of spark_glow_slots moved from the extra's own colour toward spark_glow_to."""
    c = ABILITIES[i]
    e = next(x for x in EXTRAS if x["id"] == i)
    out = []
    for a in c["spark_glow"]:
        pal = {}
        for s in c["spark_glow_slots"]:
            rgb = e["palette"][s]
            pal[s] = sum(((((rgb >> sh) & 0xFF) + ((((c["spark_glow_to"] >> sh) & 0xFF) - ((rgb >> sh) & 0xFF)) * a >> 8))
                          << sh) for sh in (16, 8, 0))
        out.append(pal)
    return out


def spark_phase(v, active, cond):
    """Script lines setting `v` to the glow's amount (0-2; -1 none) from the spark value `cond` (S1/S2 NoSwap_spark, CD
    NoSwap.Spark): stored, it pulses 0 1 2 1 (4 game frames each; 2 in its last second); flying, the brightest."""
    return [f"{v} = -1", f"if {cond} > 0", f"\tif {cond} > {active}", f"\t\t{v} = 2 // flying: white-hot", "\telse",
            f"\t\t{v} = {cond} // stored: pulsing (faster in its last second)",
            f"\t\tif {cond} > 60", f"\t\t\t{v} >>= 2", "\t\telse", f"\t\t\t{v} >>= 1", "\t\tend if", f"\t\t{v} &= 3",
            f"\t\tif {v} == 3", f"\t\t\t{v} = 1", "\t\tend if", "\tend if", "end if"]
SPIN_VALUES = """public value NoSwap_spin = 0 // spin_attack: frames spun (0: ready; below 0: the cooldown)
public value NoSwap_spinVY = 0 // spin_attack: her vertical speed at the end of her last update
"""
CYCLE_VALUES = """public value NoSwap_copyMove = 0 // ability_cycle: the active jump ability's place in the extra's cycle
"""
SWIM_VALUES = """public value NoSwap_swim = 0 // water_swim: frames before the next stroke
private alias 47 : ANI_NOSWAP_SWIM // water_swim's stroke (an extra without ray_glide / wall_cling: their slot)
"""
HIGH_KICK_VALUES = """public value NoSwap_hiKick = 0 // high_kick: 0 none; 1.. the wind-up; 1000.. the kick; 2000.. the recovery
public value NoSwap_hiKickUsed = 0 // high_kick: used this airborne period
public value NoSwap_hiKickCool = 0 // high_kick: frames on the ground before the next
"""
WARP_VALUES = """public value NoSwap_warpDir = 0 // phase_warp: its direction, (x + 1) + 3 * (y + 1) (x, y: -1, 0 or 1)
public value NoSwap_warpVX = 0 // phase_warp: his speed along before it (he has it again after)
"""
WARP_POINTS = [(0, 0), (0, -13), (0, 13), (-8, 0), (8, 0)]  # phase_warp: his body's points kept out of solid terrain
WARP_STEP = 8  # phase_warp: a path step, px (warp_range / WARP_STEP steps: warp_count)


def cycle_shots():
    return [i for i in ABILITIES if shot(i, "v4") and shot(i, "v4").get("cycle")]


# ability_cycle's moves, their jump functions (S1/S2) and their codes for the S3&K DLL (its cycleMoves)
CYCLE_MOVES = {"double_jump": ("DoubleJump", 1), "screw_kick": ("ScrewKick", 2), "jet_dash": ("JetDash", 3),
               "umbrella": ("Umbrella", 4)}


def cycle(i):
    """The extra's ability_cycle (its jump abilities in turn), checked; [] without one."""
    c = ABILITIES.get(i, {})
    moves = c.get("ability_cycle", [])
    if moves:
        bad = [m for m in moves if m not in CYCLE_MOVES or not has(i, m)]
        if bad or len(set(moves)) != len(moves) or not 2 <= len(moves) <= 4:
            sys.exit(f"ability_cycle: extra {i}: 2-4 different moves of {', '.join(CYCLE_MOVES)} it has ({bad})")
        if not v4_melee(i) or c.get("melee_cooldown") or c.get("hover") or c.get("umbrella_attack") \
                or ("screw_kick" in moves and not c.get("kick_jump")):
            sys.exit(f"ability_cycle: extra {i}: needs the melee on Y (its pose: the switch; no melee_cooldown), a "
                     "kick_jump Screw Kick, no hover and no umbrella_attack")
    return moves


def cycle_extras():
    return [i for i in ABILITIES if ABILITIES[i].get("ability_cycle")]


def cycle_gate(i, move, body):
    """`body` (a move's air or after-update code) run only while `move` is the extra's active one (ability_cycle)."""
    moves = cycle(i)
    if move not in moves or not body:
        return body
    return (f"if NoSwap_copyMove == {moves.index(move)} // ability_cycle: only while {move} is the active move\n"
            + "".join(f"\t{l}\n" if l else "\n" for l in body.rstrip("\n").split("\n")) + "end if\n")


def cycle_function(i):
    """ability_cycle: the extra's jump ability, the active move's."""
    calls = "".join(f"\tif NoSwap_copyMove == {k}\n\t\tCallFunction(NoSwap_{CYCLE_MOVES[m][0]}"
                    f"{'' if m in SHARED_JUMPS else i})\n\tend if\n" for k, m in enumerate(cycle(i)))
    return (f"// ability_cycle: the jump ability of {ALIAS_OF[i]}, its active move's (NoSwap_copyMove: Y picks the next)\n"
            f"public function NoSwap_Copycat{i}\n{calls}end function\n\n\n")


def cycle_next(i):
    """ability_cycle: a Y press started the melee (its pose is the switch): the next move is active. In the air the
    move used this jump ends (noswapAbility -1); a jump whose move wasn't used yet (0) can use the new one."""
    return (f"NoSwap_copyMove++ // ability_cycle: the next move\nif NoSwap_copyMove >= {len(cycle(i))}\n"
            "\tNoSwap_copyMove = 0\nend if\nif player.gravity == GRAVITY_AIR\n\tif player.noswapAbility != 0\n"
            "\t\tplayer.noswapAbility = -1 // the move used this jump ends\n\tend if\nend if\n")


def cycle_frame(i):
    """ability_cycle: slot 41 (the attack moves') shows the active move's frame, its place in the cycle."""
    return ("if player.animation == ANI_NOSWAP_ATTACK // ability_cycle: slot 41's frame is the active move's\n"
            "\tplayer.prevAnimation = player.animation // (the code picks the frame, not the animation speed)\n"
            "\tplayer.frame = NoSwap_copyMove\n\tplayer.animationTimer = 0\nend if\n")


def switch_by_extra(bodies, indent="\t"):
    """`switch stage.playerListPos` with one case per extra that has a body (id -> script lines)."""
    if not bodies:
        return ""
    out = [f"{indent}switch stage.playerListPos"]
    for i, body in bodies.items():
        out.append(f"{indent}case {ALIAS_OF[i]}")
        out += [f"{indent}\t{l}" if l else "" for l in body.strip("\n").split("\n")]
        out.append(f"{indent}\tbreak")
        out.append("")
    out.append(f"{indent}end switch")
    return "\n".join(out) + "\n"


def extra_table(name, values, comment, default=0, rows=1):
    """A private table of one number per extra (values: id -> number), indexed by stage.playerListPos itself (the
    base characters' entries 0-6 are padding), so a shared module reads its extra's number with one GetTableValue.
    Modules copied into every extra's case made the player script too big for the engine (2026-09-26: "Operand
    not found: PLAYER_AMY" loading any stage), so a module used by several extras is one shared function reading
    its numbers from tables like these. rows=2: a second row for the air move (index + ROW)."""
    width = max(values) + 1 if rows == 1 else ROW
    flat = [values.get((i, r) if rows > 1 else i, default) for r in range(rows) for i in range(width)]
    return f"// {comment}\nprivate table {name}\n" + table_rows(flat) + "end table\n\n"


def table_rows(values, per_line=16):
    """Table data lines, `per_line` numbers each (lines end without a comma, as in the game's own tables)."""
    return "".join("\t" + ", ".join(map(str, values[k:k + per_line])) + "\n" for k in range(0, len(values), per_line))


ROW = max(ABILITIES, default=0) + 1  # a second row's offset in extra_table(rows=2): past the highest extra ID


def jet_dash_function(i):
    cfg = ABILITIES[i]
    return f"""// Jet Dash speed: the dash speed in the facing direction, or the current speed if that's faster
public function NoSwap_JetDashSpeed{i}
	temp0 = player.xvel
	if player.direction != FACING_RIGHT
		FlipSign(temp0)
	end if
	if temp0 < {cfg['dash_speed']:#x}
		temp0 = {cfg['dash_speed']:#x}
	end if
	player.xvel = temp0
	if player.direction != FACING_RIGHT
		FlipSign(player.xvel)
	end if
end function


// Jet Dash: the jump ability of {ALIAS_OF[i]}. (Y transforms first: NoSwap_TrySuper.)
public function NoSwap_JetDash{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {cfg['dash_frames']}
			player.animation = ANI_NOSWAP_ATTACK
			player.yvel = 0
			CallFunction(NoSwap_JetDashSpeed{i})
			PlaySfx(SfxName[Fire Dash], false)
		end if
	end if
end function


"""


def jet_dash_air(i):
    """Keeps a Jet Dash going, then (with hover) lets the player hover while jump is held."""
    cfg = ABILITIES[i]
    hover = has(i, "hover")
    hover_end = -(cfg["hover_frames"] + 1) if hover else -1
    return f"""if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK
		player.yvel = 0
		CallFunction(NoSwap_JetDashSpeed{i}) // full speed for the whole dash, whatever air drag does
		player.noswapAbility--
		if player.noswapAbility == 0
			player.noswapAbility = -1 // dash over: hover may follow
			player.animation = ANI_JUMPING
		end if
	else
		player.noswapAbility = {hover_end} // interrupted (hurt, spring...): no hover this jump
	end if
else
	if player.noswapAbility < 0
		temp0 = false
""" + (f"""		if player.jumpHold == true
			if player.noswapAbility > {hover_end}
				temp0 = true
			end if
		end if
""" if hover else "") + f"""		if player.animation == ANI_HURT
			temp0 = false
		end if
		if player.animation == ANI_BOUNCING
			temp0 = false
		end if
		if temp0 == true
			if player.animation != ANI_NOSWAP_HOVER
				PlaySfx(SfxName[Flying], false)
			end if
			player.animation = ANI_NOSWAP_HOVER
			player.yvel = {cfg.get('hover_sink', 0)}
			player.noswapAbility--
		else
			if player.animation == ANI_NOSWAP_HOVER
				player.animation = ANI_JUMPING
				player.noswapAbility = {hover_end} // let go: no more hover this jump
			end if
		end if
	end if
end if
"""


def rocket_ride_function(i):
    c = ABILITIES[i]
    return f"""// Rocket Ride: the jump ability of {ALIAS_OF[i]}. The ride, the blast and the parachute are in
// NoSwap_AirAbilities; the frames and the blast's reach in NoSwap_AfterUpdate (tools/abilities.py rocket_ride).
public function NoSwap_RocketRide{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {c['ride_frames'] + c['blast_frames']} // frames left: the ride, then the blast
			player.animation = ANI_NOSWAP_ATTACK
			temp0 = player.xvel // at least ride_speed the way he faces (his own speed, if faster)
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			if temp0 < {c['ride_speed']:#x}
				temp0 = {c['ride_speed']:#x}
			end if
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			player.xvel = temp0
			player.speed = player.xvel
			player.yvel = -{c['ride_rise']:#x}
			PlaySfx(SfxName[{c['ride_sfx']}], false)
		end if
	end if
end function


"""


def falling_hover(i, name):
    """After a rocket_ride or ear_grapple (noswapAbility < 0): with hover, holding jump once he's falling, from the jump
    ball, opens the hover (`name`: the parachute, the Ear Copter). The line after "else" in NoSwap_AirAbilities."""
    return f"\tCallFunction(NoSwap_FallingHover) // the {name}\n"


def falling_hover_users():
    return [i for i in ABILITIES if has(i, "rocket_ride") or has(i, "ear_grapple")]


def falling_hover_function():
    """falling_hover, one function for every extra with it. Its numbers: NoSwap_HoverEnd (noswapAbility once the hover
    is used up: -(hover_frames + 1), or -1 without hover, so it never opens) and NoSwap_HoverSink."""
    ids = falling_hover_users()
    if not ids:
        return ""
    return (extra_table("NoSwap_HoverEnd", {i: -(ABILITIES[i]["hover_frames"] + 1) if has(i, "hover") else -1 for i in ids},
                        "falling_hover: noswapAbility once the hover is used up (-1: no hover)")
            + extra_table("NoSwap_HoverSink", {i: ABILITIES[i].get("hover_sink", 0) for i in ids},
                          "falling_hover: the fall speed while hovering")
            + """// Hover after a Bomb Jump or an Ear Grapple (tools/abilities.py falling_hover_function): holding jump once he's
// falling, from the jump ball, opens it; letting go closes it for the rest of the jump
public function NoSwap_FallingHover
	if player.noswapAbility < 0
		temp0 = false
		GetTableValue(temp1, stage.playerListPos, NoSwap_HoverEnd)
		if player.jumpHold == true
			if player.noswapAbility > temp1
				temp0 = true
			end if
		end if
		if player.animation != ANI_NOSWAP_HOVER // it opens once he's falling (after the launch's rise)
			if player.yvel < 0
				temp0 = false
			end if
			if player.animation != ANI_JUMPING
				temp0 = false
			end if
		end if
		if player.animation == ANI_HURT
			temp0 = false
		end if
		if temp0 == true
			if player.animation != ANI_NOSWAP_HOVER
				PlaySfx(SfxName[Flying], false)
			end if
			player.animation = ANI_NOSWAP_HOVER
			GetTableValue(player.yvel, stage.playerListPos, NoSwap_HoverSink)
			player.noswapAbility--
		else
			if player.animation == ANI_NOSWAP_HOVER
				player.animation = ANI_JUMPING
				player.noswapAbility = temp1 // let go: no more hover this jump
			end if
		end if
	end if
end function


""")


def rocket_ride_air(i):
    """The ride (at least ride_speed along, whichever way he's going, rising at ride_rise; a wall, his speed along under
    half of ride_speed, blows it up at once), the blast's launch, then (with hover) the parachute: holding jump once
    he's falling, from the jump ball."""
    c = ABILITIES[i]
    blast = c["blast_frames"]
    hover_end = -(c["hover_frames"] + 1) if has(i, "hover") else -1
    return f"""if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK
		if player.noswapAbility > {blast} // riding the rocket
			temp0 = player.xvel // his speed along, whichever way (a boss's knock-back rides the other way)
			temp1 = false
			if temp0 < 0
				FlipSign(temp0)
				temp1 = true
			end if
			if temp0 < {c['ride_speed'] // 2:#x} // a wall stopped him: it blows up now
				player.noswapAbility = {blast + 1}
			else
				if temp0 < {c['ride_speed']:#x} // full speed for the whole ride, whatever air drag does
					temp0 = {c['ride_speed']:#x}
				end if
				if temp1 == true
					FlipSign(temp0)
				end if
				player.xvel = temp0
				player.yvel = -{c['ride_rise']:#x}
			end if
		end if
		player.noswapAbility--
		if player.noswapAbility == {blast} // the blast
			player.yvel = -{c['blast_launch']:#x}
			player.xvel >>= 1
			player.speed = player.xvel
			player.timer = 0 // as after a spring: letting go of jump doesn't cut the launch short
			PlaySfx(SfxName[{c['blast_sfx']}], false)
		end if
		if player.noswapAbility == 0
			player.noswapAbility = -1 // launched: the parachute may follow
			player.animation = ANI_JUMPING
		end if
	else
		player.noswapAbility = {hover_end} // interrupted (hurt, spring...): no parachute this jump
	end if
else
""" + falling_hover(i, "parachute") + """end if
"""


def rocket_ride_after(i):
    """After the player has moved: the timer picks the Rocket Ride's frame (the rocket, then the blasts), and during
    the blast the hitbox (only used by enemies and monitors) reaches all around him, like Silver's sphere."""
    c = ABILITIES[i]
    blast, r = c["blast_frames"], c["blast_radius"]
    return f"""temp1 = false // blasting
if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK
		player.prevAnimation = ANI_NOSWAP_ATTACK // the timer picks the frame, not the animation speed
		temp0 = 0 // the rocket
		if player.noswapAbility <= {blast}
			temp1 = true
			temp0 = {blast}
			temp0 -= player.noswapAbility
			temp0 /= {c['blast_ticks']}
			temp0++
		end if
		player.frame = temp0
		player.animationTimer = 0
	end if
end if
if temp1 == true
	player.hitboxTop = -{r}
	player.hitboxBottom = {r}
	player.hitboxLeft = -{r}
	player.hitboxRight = {r}
else
	player.hitboxTop = C_BOX
	player.hitboxBottom = C_BOX
	player.hitboxLeft = C_BOX
	player.hitboxRight = C_BOX
end if
"""


def ear_grapple_function(i):
    c = ABILITIES[i]
    if c.get("grapple_y"):  # the jump ability is the Ear Copter; Y starts the grapple (grapple_y_after)
        return f"""// Ear Copter: the jump ability of {ALIAS_OF[i]} (grapple_y). A press in mid-air opens it at once;
// NoSwap_FallingHover keeps it open while jump is held. The Ear Grapple is on Y (NoSwap_AfterUpdate)
public function NoSwap_EarGrapple{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.noswapAbility = -1
			player.animation = ANI_NOSWAP_HOVER
			player.yvel = {c.get('hover_sink', 0):#x}
			PlaySfx(SfxName[Flying], false)
		end if
	end if
end function


"""
    return f"""// Ear Grapple: the jump ability of {ALIAS_OF[i]}. The reel and the Ear
// Copter are in NoSwap_AirAbilities; the ear itself (its reach, the terrain test, frames and hits) in
// NoSwap_AfterUpdate. noswapAbility: 1-{len(c['grapple_tip'])} the ear going out (its frame + 1), 101+ latched and
// reeling in (frames + 100), 201+ snapping back (frames left + 200)
public function NoSwap_EarGrapple{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = 1
			player.animation = ANI_NOSWAP_ATTACK
			NoSwap_grappleDir = player.direction
			PlaySfx(SfxName[{c['grapple_sfx']}], false)
		end if
	end if
end function


"""


def ear_grapple_air(i):
    """Before the player moves: latched, he's reeled toward the latch point (gravity off); while the ear goes out
    he stops falling; then (with hover) the Ear Copter, holding jump once he's falling."""
    c = ABILITIES[i]
    return f"""if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK // (anything else ends it in NoSwap_AfterUpdate)
		player.direction = NoSwap_grappleDir // air control would turn him (and the ear) around
		if player.noswapAbility < 100
			if player.yvel > 0 // the ear going out: he stops falling
				player.yvel = 0
			end if
		else
			if player.noswapAbility < 200 // latched: reeled in along the line to the latch point
				temp0 = NoSwap_grappleX
				temp0 -= player.xpos
				temp1 = NoSwap_grappleY
				temp1 -= player.ypos
				ATan2(temp2, temp0, temp1)
				Cos256(player.xvel, temp2)
				player.xvel *= {c['reel_speed'] >> 8:#x}
				Sin256(player.yvel, temp2)
				player.yvel *= {c['reel_speed'] >> 8:#x}
				player.speed = player.xvel // (Ristar's pull: tools/star_grab.py v4_air)
			end if
		end if
	end if
else
""" + falling_hover(i, "Ear Copter") + """end if
"""


def grapple_y_after(i):
    """grapple_y: Y in mid-air starts the Ear Grapple (from the jump, the Ear Copter or a fall), once per airborne
    period (NoSwap_grappleUsed, cleared on landing). Before ear_grapple_after, which tests the ear's first frame."""
    c = ABILITIES[i]
    # grapple_refill: below 0 it's the cooldown after a pull (frames left, negated), counted once the ear's in
    cool = """	if NoSwap_grappleUsed < 0
		if player.noswapAbility <= 0
			NoSwap_grappleUsed++
		end if
	end if
""" if c.get("grapple_refill") else ""
    return f"""if player.gravity == GRAVITY_GROUND
	NoSwap_grappleUsed = false
else
{cool}	if keyPress[1].buttonY != false
		if NoSwap_grappleUsed == false
			if player.noswapAbility <= 0
				temp0 = false
				CheckEqual(player.state, Player_State_Air)
				temp0 |= checkResult
				CheckEqual(player.state, Player_State_Air_NoDropDash)
				temp0 |= checkResult
				CheckEqual(player.state, Player_State_RollJump)
				temp0 |= checkResult
				if player.animation == ANI_HURT
					temp0 = false
				end if
				if temp0 == true
					NoSwap_grappleUsed = true
					player.noswapAbility = 1
					player.animation = ANI_NOSWAP_ATTACK
					NoSwap_grappleDir = player.direction
					PlaySfx(SfxName[{c['grapple_sfx']}], false)
				end if
			end if
		end if
	end if
end if
"""


def ear_grapple_after(i):
    """After the player has moved (and after the melee, whose hitbox this overrides while the ear is out): the ear
    grows a frame, and its tip is tested against the terrain on his collision plane (ObjectTileCollision moves
    the object it tests, so his position is put back after each test). The frame follows the ear's length.
    Rebuilt on Ristar's Grab (tools/star_grab.py; the user, 2026-09-30: the ear stretched his hitbox for the whole move
    and it fought the pull): only while the ear goes out does the hitbox (only enemies, monitors and bosses use it)
    reach to the tip, as Ristar's hands'; latched or snapping back he has his own. The pull lets go when he's close,
    out of time or stopped by the terrain (Ristar's test), and a slope he touches down on doesn't end it while the
    point is well above (Ristar's pull on the ground). A badnik the ear breaks sends it back (ear_grapple_patch)."""
    c = ABILITIES[i]
    n = len(c["grapple_tip"])
    hover_end = -(c["hover_frames"] + 1) if has(i, "hover") else -1
    r = c["latch_range"]

    def tip(depth):  # the tip of frame temp4, from his centre: temp1 (mirrored facing left), temp2
        return "".join("\t" * depth + l + "\n" for l in [
            f"GetTableValue(temp1, temp4, NoSwap_GrappleTipX{i})", "if NoSwap_grappleDir == FACING_LEFT",
            "\tFlipSign(temp1)", "end if", f"GetTableValue(temp2, temp4, NoSwap_GrappleTipY{i})"])
    chain = c.get("grapple_y") and c.get("grapple_refill")  # a latch refills the Y grab, after a cooldown
    refill = "\t\t\tNoSwap_grappleUsed = false // grapple_refill: a latch gives the grab back\n" if chain else ""
    cool = (f"\t\t\tNoSwap_grappleUsed = -{c.get('grapple_cooldown', 0)} // grapple_refill: the next grab waits\n"
            if chain and c.get("grapple_cooldown") else "")
    reset = "" if v4_melee(i) else """player.hitboxTop = C_BOX
player.hitboxBottom = C_BOX
player.hitboxLeft = C_BOX
player.hitboxRight = C_BOX
"""
    return f"""if player.noswapAbility > 100
	if player.noswapAbility < 200 // pulled in, but he touched down (a slope): a point well above lifts him off
		if player.gravity == GRAVITY_GROUND
			CheckEqual(player.state, Player_State_Ground)
			if checkResult == true
				temp0 = NoSwap_grappleY
				temp0 -= player.ypos
				temp0 >>= 16
				if temp0 < -12
					player.state = Player_State_Air
					player.gravity = GRAVITY_AIR
					player.yvel = -0x10000
					player.xvel = 0
					player.speed = 0
					player.animation = ANI_NOSWAP_ATTACK
				end if
			end if
		end if
	end if
end if
if player.noswapAbility > 0
	temp0 = false
	if player.gravity == GRAVITY_GROUND // landed: the ear's gone
		temp0 = true
		if player.animation == ANI_NOSWAP_ATTACK
			player.animation = ANI_WALKING
		end if
	end if
	if player.animation != ANI_NOSWAP_ATTACK // hurt, a spring, the Ear Jab...
		temp0 = true
	end if
	if temp0 == true
		player.noswapAbility = {hover_end} // no Ear Copter this jump
	end if
end if
temp4 = 0 // the ear's frame
if player.noswapAbility > 200 // snapping back, shorter each frame
	temp4 = player.noswapAbility
	temp4 -= 201
	temp4 *= {n // c['snap_frames']}
	player.noswapAbility--
	if player.noswapAbility == 200
		player.noswapAbility = -1 // the Ear Copter may follow
		player.animation = ANI_JUMPING
	end if
end if
if player.noswapAbility > 100
	if player.noswapAbility < 200 // latched and reeling in
		temp1 = NoSwap_grappleX // how far the latch point is, in px
		temp1 -= player.xpos
		temp1 >>= 16
		if NoSwap_grappleDir == FACING_LEFT
			FlipSign(temp1)
		end if
		temp2 = NoSwap_grappleY
		temp2 -= player.ypos
		temp2 >>= 16
		temp0 = false // let go?
		if player.noswapAbility >= {100 + c['reel_frames']}
			temp0 = true
		end if
		if player.noswapAbility > 102
			if player.xvel == 0
				if player.yvel == 0 // stopped by the terrain (Ristar's test)
					temp0 = true
				end if
			end if
		end if
		temp3 = temp1
		if temp3 < 0
			FlipSign(temp3)
		end if
		if temp3 < {r}
			temp3 = temp2
			if temp3 < 0
				FlipSign(temp3)
			end if
			if temp3 < {r}
				temp0 = true
			end if
		end if
		if temp0 == true // there: a small hop, still moving forward
			player.yvel = -{c['grapple_hop']:#x}
			player.xvel = {c['grapple_forward']:#x}
			if NoSwap_grappleDir == FACING_LEFT
				FlipSign(player.xvel)
			end if
			player.speed = player.xvel
{cool}			player.noswapAbility = -1 // the Ear Copter may follow
			player.animation = ANI_JUMPING
		else
			player.noswapAbility++
			temp3 = 1 // the longest ear that doesn't reach past the latch point
			while temp3 < {n}
				GetTableValue(temp5, temp3, NoSwap_GrappleTipX{i})
				GetTableValue(temp6, temp3, NoSwap_GrappleTipY{i})
				if temp5 <= temp1
					if temp6 >= temp2
						temp4 = temp3
					end if
				end if
				temp3++
			loop
		end if
	end if
end if
if player.noswapAbility > 0
	if player.noswapAbility < 100 // the ear going out: does its tip reach solid ground (floor or ceiling side)?
		temp4 = player.noswapAbility
		temp4--
{tip(2)}		temp6 = player.xpos
		temp7 = player.ypos
		ObjectTileCollision(CSIDE_FLOOR, temp1, temp2, player.collisionPlane)
		temp3 = checkResult
		player.xpos = temp6
		player.ypos = temp7
		if temp3 == false
			ObjectTileCollision(CSIDE_ROOF, temp1, temp2, player.collisionPlane)
			temp3 = checkResult
			player.xpos = temp6
			player.ypos = temp7
		end if
		if temp3 == true // latched
			temp1 <<= 16
			temp2 <<= 16
			NoSwap_grappleX = player.xpos
			NoSwap_grappleX += temp1
			NoSwap_grappleY = player.ypos
			NoSwap_grappleY += temp2
			player.noswapAbility = 101
{refill}			PlaySfx(SfxName[{c['latch_sfx']}], false)
		else
			player.noswapAbility++
			if player.noswapAbility > {n} // full reach, nothing there
				player.noswapAbility = {200 + c['snap_frames']}
			end if
		end if
	end if
end if
if player.animation == ANI_NOSWAP_ATTACK // the ear's frame
	player.prevAnimation = ANI_NOSWAP_ATTACK // the timer picks the frame, not the animation speed
	player.frame = temp4
	player.animationTimer = 0
end if
{reset}temp0 = false
if player.noswapAbility > 0
	if player.noswapAbility < 100
		temp0 = true
	end if
end if
if temp0 == true // the ear going out: the hitbox out to its tip, as Ristar's hands'
{tip(1)}	temp2 -= 8
	player.hitboxTop = temp2
	player.hitboxBottom = 20
	if NoSwap_grappleDir == FACING_LEFT
		temp1 -= 8
		player.hitboxLeft = temp1
		player.hitboxRight = 10
	else
		temp1 += 8
		player.hitboxLeft = -10
		player.hitboxRight = temp1
	end if
end if
"""


def ear_grapple_patch(t):
    """Player_BadnikBreak: a badnik the Ear Grapple's ear breaks while it goes out (his hitbox reaches to its tip then,
    as Ristar's hands') sends the ear back (the user, 2026-09-30); the game breaks it as before."""
    head = "public function Player_BadnikBreak\n"
    for i in with_ability("ear_grapple"):
        if t.count(head) != 1:
            sys.exit("ear_grapple: Player_BadnikBreak isn't there once")
        t = t.replace(head, head + f"""	if stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] the Ear Grapple's ear hit it: it snaps back
		if player[currentPlayer].noswapAbility > 0
			if player[currentPlayer].noswapAbility < 100
				player[currentPlayer].noswapAbility = {200 + ABILITIES[i]['snap_frames']}
""" + (f"""				NoSwap_grappleUsed = {-ABILITIES[i].get('grapple_cooldown', 0)} // grapple_refill: a hit gives the grab back
""" if ABILITIES[i].get("grapple_y") and ABILITIES[i].get("grapple_refill") else "") + """			end if
		end if
	end if
""")
    return t


def umbrella_function():
    """Umbrella's jump ability, shared by every extra with it (its numbers: umbrella_tables)."""
    return """// Umbrella: the jump ability of the extras with it (tools/abilities.py). Floating is in NoSwap_UmbrellaAir.
// noswapAbility: open (1, or with a time limit, frames left + 2: NoSwap_UmbrellaOpen), 2 closed for the rest of this jump
public function NoSwap_Umbrella
	if player.jumpPress == true
		player.jumpAbilityState = 2
		GetTableValue(player.noswapAbility, stage.playerListPos, NoSwap_UmbrellaOpen)
		GetTableValue(player.animation, stage.playerListPos, NoSwap_UmbrellaAnim)
	end if
end function


"""


def umbrella_tables():
    ids = with_ability("umbrella")
    return (extra_table("NoSwap_UmbrellaOpen", {i: umbrella_open(i) for i in ids},
                        "umbrella: noswapAbility when it opens (1, or with float_frames, frames left + 2)")
            + extra_table("NoSwap_UmbrellaAnim", {i: ANI_ATTACK if ABILITIES[i].get("umbrella_attack") else ANI_HOVER
                                                  for i in ids},
                          f"umbrella: the float's animation ({ANI_HOVER}, or {ANI_ATTACK} with umbrella_attack: Espio's Whirlwind)")
            + extra_table("NoSwap_UmbrellaSink", {i: ABILITIES[i]['umbrella_sink'] for i in ids},
                          "umbrella_sink: the fall speed under it"))


def umbrella_open(i):
    """noswapAbility while the umbrella is open: 1, or with a time limit (float_frames), frames left + 2."""
    cap = ABILITIES[i].get("float_frames")
    return cap + 2 if cap else 1


def umbrella_anim(i):
    """The float's animation: the hover slot, or the attack slot (umbrella_attack: Espio's Whirlwind)."""
    return "ANI_NOSWAP_ATTACK" if ABILITIES[i].get("umbrella_attack") else "ANI_NOSWAP_HOVER"


def umbrella_is_open(i):
    return "> 2" if ABILITIES[i].get("float_frames") else "== 1"


def water_swim_air(i):
    """water_swim (the module's notes), in NoSwap_AirAbilities, before the jump ability check: a press it takes never
    reaches the jump ability (the stroke's animation isn't the jump's, and jumpAbilityState 2 ends it for this jump)."""
    c = ABILITIES[i]
    if has(i, "ray_glide") or has(i, "wall_cling"):
        sys.exit(f"water_swim: extra {i}: its slot 47 is ray_glide's / wall_cling's")
    return f"""if NoSwap_swim > 0 // water_swim: frames before the next stroke (tools/abilities.py water_swim_air)
	NoSwap_swim--
end if
if player.gravityStrength == 0x1000 // underwater (the player update sets it below the water line)
	if player.jumpPress == true
		temp0 = false
		if player.animation == ANI_JUMPING
			temp0 = true
		end if
		if player.animation == ANI_NOSWAP_SWIM
			temp0 = true
		end if
		if temp0 == true
			player.jumpAbilityState = 2 // no parasol this jump
			if NoSwap_swim == 0 // a stroke
				NoSwap_swim = {c['swim_delay']}
				if player.yvel > -{c['swim_stroke']}
					player.yvel = -{c['swim_stroke']}
				end if
				player.timer = 0 // (as after a spring: letting go of jump doesn't cut it short)
				player.animation = ANI_NOSWAP_SWIM
				player.frame = 0
				player.animationTimer = 0
			end if
		end if
	end if
end if
"""


def umbrella_air(i):
    return "CallFunction(NoSwap_UmbrellaAir)\n"


def umbrella_air_function():
    """Floating under the umbrella while jump is held, for every extra with it. It's open while noswapAbility is 1 (no
    time limit) or over 2 (float_frames: frames left + 2); an extra only ever has one of the two (umbrella_open)."""
    return """// Umbrella: floating while jump is held (tools/abilities.py umbrella_air_function), for every extra with it
public function NoSwap_UmbrellaAir
	temp0 = false // open?
	if player.noswapAbility == 1
		temp0 = true
	end if
	if player.noswapAbility > 2
		temp0 = true
	end if
	if temp0 == true
		GetTableValue(temp1, stage.playerListPos, NoSwap_UmbrellaAnim)
		if player.animation != temp1
			player.noswapAbility = 2 // hurt, springs...: the umbrella closes
		else
			if player.jumpHold == true
				GetTableValue(temp1, stage.playerListPos, NoSwap_UmbrellaSink)
				if player.yvel > temp1
					player.yvel = temp1
				end if
				if player.noswapAbility > 2 // float_frames: counting down
					player.noswapAbility--
					if player.noswapAbility == 2 // out of time
						player.animation = ANI_JUMPING
					end if
				end if
			else
				player.noswapAbility = 2
				player.animation = ANI_JUMPING
			end if
		end if
	end if
end function


"""


def chaos_control_function(i):
    c = ABILITIES[i]
    return f"""// Chaos Control: the jump ability of {ALIAS_OF[i]}. The flash, warp and hop are in NoSwap_AirAbilities.
public function NoSwap_ChaosControl{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {c['chaos_freeze'] + c['chaos_warp']}
			player.animation = ANI_NOSWAP_ATTACK
			player.xvel = 0
			player.yvel = 0
			PlaySfx(SfxName[Insta Shield], false)
		end if
	end if
end function


"""


def chaos_control_air(i):
    c = ABILITIES[i]
    return f"""if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK
		player.yvel = 0
		if player.noswapAbility > {c['chaos_warp']}
			player.xvel = 0 // the flash
		else
			player.xvel = {c['chaos_speed']:#x} // the warp
			if player.direction != FACING_RIGHT
				FlipSign(player.xvel)
			end if
		end if
		player.noswapAbility--
		if player.noswapAbility == 0
			player.noswapAbility = -1
			player.yvel = -{c['chaos_pop']:#x} // the hop
		end if
	else
		player.noswapAbility = -1
	end if
else
	if player.noswapAbility < 0
		if player.animation == ANI_NOSWAP_ATTACK
			if player.yvel >= 0
				player.animation = ANI_JUMPING
			end if
		end if
	end if
end if
"""


def aim_dash_start(i, depth):
    """Starts an aimed dash (NoSwap_AimDashStart, shared)."""
    return "\t" * depth + "CallFunction(NoSwap_AimDashStart)\n"


def aim_dash_functions():
    """The aimed dash's start (from the jump ability, or from Y with aim_dash_y), the jump ability and the dash itself,
    one of each for every extra with it (its numbers: aim_dash_tables)."""
    return """// Burst Dash start (tools/abilities.py aim_dash_functions): noswapAbility is frames left + 100 (up) or + 200
// (down), + 1000 if it started facing left (the dash keeps that direction: turning around mid-dash doesn't redirect it)
public function NoSwap_AimDashStart
	GetTableValue(player.noswapAbility, stage.playerListPos, NoSwap_DashFrames)
	player.animation = ANI_NOSWAP_ATTACK
	if player.up == true
		player.noswapAbility += 100
		player.animation = ANI_NOSWAP_ATTACK_UP
	end if
	if player.down == true
		player.noswapAbility += 200
		player.animation = ANI_NOSWAP_ATTACK_DOWN
	end if
	if player.direction == FACING_LEFT
		player.noswapAbility += 1000
	end if
	PlaySfx(SfxName[Fire Dash], false)
end function


// Burst Dash: the jump ability of the extras with it (but aim_dash_y's). Holding up or down when it starts aims it
// 45 degrees
public function NoSwap_AimDash
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			CallFunction(NoSwap_AimDashStart)
		end if
	end if
end function


// Burst Dash: the dash itself, in NoSwap_AirAbilities
public function NoSwap_AimDashAir
	if player.noswapAbility > 0
		temp0 = false
		CheckEqual(player.animation, ANI_NOSWAP_ATTACK)
		temp0 |= checkResult
		CheckEqual(player.animation, ANI_NOSWAP_ATTACK_UP)
		temp0 |= checkResult
		CheckEqual(player.animation, ANI_NOSWAP_ATTACK_DOWN)
		temp0 |= checkResult
		if temp0 == true
			temp2 = player.noswapAbility // without the facing
			temp2 %= 1000
			if temp2 > 200
				GetTableValue(player.xvel, stage.playerListPos, NoSwap_DashDiagX)
				GetTableValue(player.yvel, stage.playerListPos, NoSwap_DashDiagY)
			else
				if temp2 > 100
					GetTableValue(player.xvel, stage.playerListPos, NoSwap_DashUpX)
					GetTableValue(player.yvel, stage.playerListPos, NoSwap_DashUpY)
				else
					temp1 = player.xvel // straight: at least the dash speed
					if temp1 < 0
						FlipSign(temp1)
					end if
					GetTableValue(temp3, stage.playerListPos, NoSwap_DashSpeed)
					if temp1 < temp3
						temp1 = temp3
					end if
					player.xvel = temp1
					player.yvel = 0
				end if
			end if
			if player.noswapAbility > 1000 // locked to the direction it started in
				FlipSign(player.xvel)
				player.direction = FACING_LEFT
			else
				player.direction = FACING_RIGHT
			end if
			player.noswapAbility--
			temp1 = player.noswapAbility
			temp1 %= 100
			if temp1 == 0
				player.noswapAbility = -1
				player.animation = ANI_JUMPING
			end if
		else
			player.noswapAbility = -1
		end if
	end if
end function


"""


def aim_dash_tables():
    ids = with_ability("aim_dash")
    c = lambda i: ABILITIES[i]
    return (extra_table("NoSwap_DashFrames", {i: c(i)["dash_frames"] for i in ids}, "aim_dash: the dash's frames")
            + extra_table("NoSwap_DashSpeed", {i: c(i)["dash_speed"] for i in ids}, "aim_dash: straight, at least")
            + extra_table("NoSwap_DashDiagX", {i: c(i)["diag_x"] for i in ids}, "aim_dash: down (x)")
            + extra_table("NoSwap_DashDiagY", {i: c(i)["diag_y"] for i in ids}, "aim_dash: down (y)")
            + extra_table("NoSwap_DashUpX", {i: c(i).get("up_x", c(i)["diag_x"]) for i in ids},
                          "aim_dash: up (x; up_x, or diag_x)")
            + extra_table("NoSwap_DashUpY", {i: -c(i).get("up_y", c(i)["diag_y"]) for i in ids},
                          "aim_dash: up (y, upward; up_y, or diag_y)"))


def aim_dash_y_after(i):
    """aim_dash_y: Y in mid-air starts the dash (Charmy's Stinger), once per airborne period; the jump
    ability stays the base character's. From Tails' flight it drops him into the air state for good: no
    second flight this jump (the flight's own rules)."""
    return f"""if player.gravity == GRAVITY_GROUND
	player.noswapAbility = 0 // landed: the dash is over, and ready again
else
	if keyPress[1].buttonY != false
		if player.noswapAbility == 0
			temp0 = false
			CheckEqual(player.state, Player_State_Air)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_Air_NoDropDash)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_RollJump)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_Fly)
			temp0 |= checkResult
			if player.animation == ANI_HURT
				temp0 = false
			end if
			if temp0 == true
				if player.state == Player_State_Fly // out of the flight, which doesn't come back this jump
					player.state = Player_State_Air
					player.jumpAbilityState = 2
				end if
{aim_dash_start(i, 4)}			end if
		end if
	end if
end if
"""


def aim_dash_air(i):
    return "CallFunction(NoSwap_AimDashAir)\n"


def hammer_drop_function(i):
    return f"""// Hammer Drop: the jump ability of {ALIAS_OF[i]} (Mania Plus's Player_JumpAbility_Mighty). The landing
// bounce is in NoSwap_AfterUpdate.
public function NoSwap_HammerDrop{i}
	if player.jumpPress == true
		player.jumpAbilityState = 2
		player.xvel >>= 1
		if player.gravityStrength == 0x1000 // underwater
			player.yvel = 0x80000
		else
			player.yvel = 0xC0000
		end if
		player.animation = ANI_NOSWAP_ATTACK
		player.noswapAbility = 1
		PlaySfx(SfxName[Release], false)
	end if
end function


"""


def hammer_drop_air(i):
    return """if player.noswapAbility == 1
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt...
	else
		if player.yvel <= 0x10000 // a spring or anything else sending him up ends it
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
		end if
	end if
end if
"""


def slam_spawn(i):
    """Sonic 1/2, shot "input" "slam" (Bark's shockwaves): as the Hammer Drop lands, two shots, one each way (temp6 -1,
    then 1), x px out and y px below his centre, set up as shot_after's (tools/shots_v4.py)."""
    import shots_v4
    s = check_shot(i)
    return f"""			temp6 = -1 // the slam's shockwaves (shot "input" "slam": tools/abilities.py slam_spawn): one each way
			while temp6 < 2
				temp2 = {s['x'] << 16}
				temp2 *= temp6
				temp2 += player.xpos
				temp3 = player.ypos
				temp3 += {s['y'] << 16}
				CreateTempObject(TypeName[Tails Object], player.collisionPlane, temp2, temp3)
				arrayPos0 = object[tempObjectPos].entityPos
				if object[arrayPos0].type == TypeName[Tails Object] // (made)
					object[arrayPos0].groupID = {shots_v4.GROUP} // the shots' group: the enemies' shot loops
					object[arrayPos0].state = {shots_v4.LIVE}
					object[arrayPos0].priority = PRIORITY_ACTIVE
					object[arrayPos0].interaction = true
					object[arrayPos0].drawOrder = player.sortedDrawOrder
					object[arrayPos0].direction = FACING_RIGHT
					if temp6 < 0
						object[arrayPos0].direction = FACING_LEFT
					end if
					temp4 = {s['speed']}
					temp4 *= temp6
					object[arrayPos0].xvel = temp4
					object[arrayPos0].yvel = 0
					object[arrayPos0].value0 = 0
					object[arrayPos0].frame = {shot_frame_base(i)}
					object[arrayPos0].animationTimer = 0
				end if
				temp6 += 2
			loop
"""


def hammer_drop_after(i):
    """Runs after the player has moved: landing from the drop bounces him up in his ball, along the
    ground's angle (Mania Plus's Player_State_MightyHammerDrop). A slam shot (Bark's shockwaves) goes out as he lands."""
    return """if player.noswapAbility == 1
	if player.gravity == GRAVITY_GROUND
		if player.animation == ANI_NOSWAP_ATTACK
			temp0 = player.gravityStrength // the bounce
			if player.gravityStrength == 0x1000
				temp0 += 0x10000
			else
				temp0 += 0x20000
			end if
			temp1 = player.speed // keeps 3/4 of its ground speed
			temp2 = temp1
			temp2 >>= 2
			temp1 -= temp2
			Sin256(temp3, player.angle)
			Cos256(temp4, player.angle)
			temp5 = temp1 // x: (ground speed * cos + bounce * sin) >> 8
			temp5 *= temp4
			temp2 = temp0
			temp2 *= temp3
			temp5 += temp2
			temp5 >>= 8
			temp2 = temp1 // y: (ground speed * sin - bounce * cos) >> 8
			temp2 *= temp3
			temp4 *= temp0
			temp2 -= temp4
			temp2 >>= 8
			CallFunction(Player_Action_Jump) // (uses temp0, temp1, temp6 and temp7)
			if player.gravity == GRAVITY_AIR // no roof in the way
				player.iypos += player.jumpOffset // the jump shifts for a jump ball, which this isn't yet
				player.xvel = temp5
				player.yvel = temp2
				player.jumpAbilityState = 2 // no second drop in the bounce
				player.animation = ANI_JUMPING
				screen.shakeY = 4
				PlaySfx(SfxName[HammerHit], false)
			end if
		end if
		player.noswapAbility = -1
	end if
end if
""".replace("\t\tif player.animation == ANI_NOSWAP_ATTACK\n",
            "\t\tif player.animation == ANI_NOSWAP_ATTACK\n" + (slam_spawn(i) if slam_shot(i) else ""), 1)


def ray_glide_function(i):
    return f"""// Glide: the jump ability of {ALIAS_OF[i]} (Mania Plus's Player_JumpAbility_Ray). Holding forward starts
// in a dive, otherwise in a swoop up. The flight is in NoSwap_AirAbilities.
public function NoSwap_RayGlide{i}
	if player.jumpPress == true
		player.jumpAbilityState = 2
		temp0 = player.xvel // keep 7/8 of the speed, at least 3 px per frame (1.5 underwater)
		temp1 = temp0
		temp1 >>= 3
		temp0 -= temp1
		temp1 = 0x30000
		if player.gravityStrength == 0x1000
			temp1 = 0x18000
		end if
		if player.direction == FACING_LEFT
			FlipSign(temp1)
			if temp0 > temp1
				temp0 = temp1
			end if
		else
			if temp0 < temp1
				temp0 = temp1
			end if
		end if
		NoSwap_glideLeft = player.direction
		temp2 = false // holding forward?
		if player.direction == FACING_LEFT
			temp2 = player.left
		else
			temp2 = player.right
		end if
		if temp2 == true
			NoSwap_glideUp = false
			NoSwap_glideLift = 0
			player.animation = ANI_NOSWAP_GLIDE_DOWN
		else
			NoSwap_glideUp = true
			temp0 >>= 1
			temp1 = temp0
			if temp1 < 0
				FlipSign(temp1)
			end if
			temp2 = temp1
			temp2 >>= 1
			temp3 = temp1
			temp3 >>= 2
			temp2 += temp3
			temp3 = temp1
			temp3 >>= 4
			temp2 += temp3
			FlipSign(temp2)
			if player.gravityStrength == 0x1000
				temp2 >>= 1
			end if
			NoSwap_glideLift = temp2
			player.animation = ANI_NOSWAP_GLIDE_UP
		end if
		player.xvel = temp0
		player.yvel >>= 1
		NoSwap_glideVX = player.xvel
		NoSwap_glideVY = player.yvel
		NoSwap_glideAngle = 0x40
		NoSwap_glideCap = temp0
		if NoSwap_glideCap < 0
			FlipSign(NoSwap_glideCap)
		end if
		NoSwap_glidePower = 256
		player.noswapAbility = 1
	end if
end function


"""


def ray_glide_air(i):
    """Mania Plus's Player_State_RayGlide, one frame. Runs after the air state's gravity and air control,
    which it overrides with the glide's own velocity."""
    return """if player.noswapAbility == 1
	temp0 = false
	CheckEqual(player.animation, ANI_NOSWAP_GLIDE_UP)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_GLIDE_DOWN)
	temp0 |= checkResult
	if temp0 == false
		player.noswapAbility = -1 // hurt, springs...
	else
		player.direction = NoSwap_glideLeft // air control would turn him around
		temp7 = 0 // 1 underwater
		if player.gravityStrength == 0x1000
			temp7 = 1
		end if

		if NoSwap_glideUp == true
			if NoSwap_glideAngle < 0x70
				NoSwap_glideAngle += 8
			end if
		else
			if NoSwap_glideAngle > 0x10
				NoSwap_glideAngle -= 8
			end if
		end if

		if NoSwap_glideLift != 0
			temp0 = NoSwap_glideLift
			temp1 = 2
			temp1 -= temp7
			temp0 >>= temp1
			NoSwap_glideVY += temp0
			if NoSwap_glideVY < NoSwap_glideLift
				NoSwap_glideVY = NoSwap_glideLift
				NoSwap_glideLift = 0
			end if
		else
			Cos(temp0, NoSwap_glideAngle)
			temp0 *= player.gravityStrength
			temp0 >>= 9
			NoSwap_glideVY += temp0
		end if
		if NoSwap_glideVY < -0x60000
			NoSwap_glideVY = -0x60000
		end if
		if NoSwap_glideUp == true
			if NoSwap_glideVY > 0x10000
				temp0 = NoSwap_glideVY
				temp0 >>= 2
				NoSwap_glideVY -= temp0
			end if
		end if

		temp1 = 0x50 // 22 * Sin256(0x50 - angle): how hard the angle pushes
		temp1 -= NoSwap_glideAngle
		temp1 &= 0xFF
		Sin256(temp2, temp1)
		temp2 *= 22
		if NoSwap_glideVY <= 0
			NoSwap_glideCap -= temp2
			if NoSwap_glideCap < 0x40000
				NoSwap_glideCap = 0x40000
			end if
		else
			if NoSwap_glideVY > NoSwap_glideCap
				temp0 = NoSwap_glideVY
				temp0 >>= 6
				NoSwap_glideCap = NoSwap_glideVY
				NoSwap_glideCap -= temp0
			end if
		end if

		if NoSwap_glideVX != 0
			temp2 >>= temp7
			if NoSwap_glideLeft == FACING_LEFT
				NoSwap_glideVX -= temp2
				if NoSwap_glideVX > -0x10000
					NoSwap_glideVX = -0x10000
				end if
				temp0 = NoSwap_glideCap
				FlipSign(temp0)
				if NoSwap_glideVX < temp0
					NoSwap_glideVX = temp0
				end if
			else
				NoSwap_glideVX += temp2
				if NoSwap_glideVX < 0x10000
					NoSwap_glideVX = 0x10000
				end if
				if NoSwap_glideVX > NoSwap_glideCap
					NoSwap_glideVX = NoSwap_glideCap
				end if
			end if
		end if

		if NoSwap_glideLeft == FACING_LEFT // forward / back
			temp3 = player.left
			temp4 = player.right
		else
			temp3 = player.right
			temp4 = player.left
		end if
		temp5 = true // Mania: "!back || angle != 0x10"
		if temp4 == true
			if NoSwap_glideAngle == 0x10
				temp5 = false
			end if
		end if
		if temp5 == true
			if temp3 == true // forward at the top of a swoop: tip over into a dive
				if NoSwap_glideAngle == 0x70
					if NoSwap_glideUp == true
						NoSwap_glideLift = 0
						NoSwap_glideUp = false
					end if
				end if
			end if
		else
			if NoSwap_glideUp == false // back at the bottom of a dive: swoop up
				NoSwap_glideUp = true
				temp0 = false
				if NoSwap_glideVY > 0x28000
					temp0 = true
				end if
				if NoSwap_glidePower == 256
					temp0 = true
				end if
				if temp7 == 1
					if NoSwap_glideVY > 0x18000
						temp0 = true
					end if
				end if
				if temp0 == true
					temp1 = NoSwap_glideVX
					if temp1 < 0
						FlipSign(temp1)
					end if
					temp2 = temp1
					temp2 >>= 1
					temp3 = temp1
					temp3 >>= 2
					temp2 += temp3
					temp3 = temp1
					temp3 >>= 4
					temp2 += temp3
					temp2 *= NoSwap_glidePower
					temp2 >>= 8
					FlipSign(temp2)
					if temp7 == 1
						temp3 = temp2
						temp3 >>= 3
						temp2 >>= 1
						temp2 += temp3
					end if
					NoSwap_glideLift = temp2
					if NoSwap_glidePower > 16 // each swoop is weaker than the last
						NoSwap_glidePower -= 32
					end if
					if NoSwap_glideLift < -0x60000
						NoSwap_glideLift = -0x60000
					end if
				end if
			end if
		end if
		if NoSwap_glideUp == true
			player.animation = ANI_NOSWAP_GLIDE_UP
		else
			player.animation = ANI_NOSWAP_GLIDE_DOWN
		end if

		player.xvel = NoSwap_glideVX
		player.yvel = NoSwap_glideVY
		temp0 = NoSwap_glideVX
		if temp0 < 0
			FlipSign(temp0)
		end if
		temp1 = false
		if player.jumpHold == false
			temp1 = true
		end if
		if temp0 < 0x10000
			temp1 = true
		end if
		if temp1 == true // let go of jump, or too slow: curl up and fall
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
		end if
	end if
end if
"""


def ray_glide_after(i):
    """After the player has moved: walls and ceilings stop the glide's own velocity; landing ends it."""
    return """if player.noswapAbility == 1
	if player.gravity == GRAVITY_GROUND
		temp0 = player.speed // a slow landing gets a boost
		if temp0 < 0
			FlipSign(temp0)
		end if
		if temp0 < 0x20000
			player.speed <<= 1
		end if
		player.noswapAbility = -1
		player.animation = ANI_WALKING
	else
		if player.xvel == 0 // a wall
			NoSwap_glideVX = 0
		end if
		if NoSwap_glideVY < 0
			if player.yvel == 0 // a ceiling
				NoSwap_glideLift = 0
			end if
		end if
	end if
end if
"""


def spirit_total(i):
    """noswapAbility when the Spirit Flight starts: the transform's game frames, then the flight's."""
    c = ABILITIES[i]
    return c["spirit_transform"] * c["spirit_ticks"] + c["spirit_frames"]


def spirit_flight_function(i):
    c = ABILITIES[i]
    return f"""// Spirit Flight: the jump ability of {ALIAS_OF[i]}. She turns into a spirit orb and flies where the d-pad points
// (in NoSwap_AirAbilities; the transform's frames in NoSwap_AfterUpdate). noswapAbility: game frames left, the
// transform then the flight ({c['spirit_frames']} and under); -1 used
public function NoSwap_SpiritFlight{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {spirit_total(i)}
			player.animation = ANI_NOSWAP_ATTACK
			player.xvel = 0 // held still while she transforms
			player.speed = 0
			player.yvel = 0
			NoSwap_glideVX = 0
			NoSwap_glideVY = 0
			PlaySfx(SfxName[{c['spirit_sfx']}], false)
		end if
	end if
end function


"""


def spirit_approach(v, target, accel):
    """Lines moving `v` toward `target` by `accel` per frame, without overshooting."""
    return f"""if {v} < {target}
	{v} += {accel:#x}
	if {v} > {target}
		{v} = {target}
	end if
else
	{v} -= {accel:#x}
	if {v} < {target}
		{v} = {target}
	end if
end if"""


def spirit_flight_air(i):
    """After the air state's gravity and air control: held still while she transforms, then the orb's own velocity
    eases toward the d-pad's direction (it replaces the game's, so gravity is off). The game still moves her, so
    walls, ceilings and floors stop her as usual. Time running out or jump pressed again re-forms her, with no
    upward speed kept; anything else changing her animation (a hit, a spring) ends it with its own speed."""
    c = ABILITIES[i]
    ind = lambda s, d: "".join("\t" * d + l + "\n" for l in s.split("\n"))
    return f"""if player.noswapAbility > 0
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt, a spring...: the flight's over, their speed stays
	else
		player.noswapAbility--
		temp0 = false // re-form?
		temp1 = 0 // the d-pad's velocity
		temp2 = 0
		if player.noswapAbility <= {c['spirit_frames']} // flying (not the transform)
			if player.jumpPress == true
				temp0 = true
			end if
			if player.noswapAbility == 0
				temp0 = true
			end if
			temp3 = {c['spirit_speed']:#x}
			temp4 = player.left
			temp4 |= player.right
			if temp4 == true // diagonals: the same speed overall
				temp4 = player.up
				temp4 |= player.down
				if temp4 == true
					temp3 = {c['spirit_diag']:#x}
				end if
			end if
			if player.left == true
				temp1 = temp3
				FlipSign(temp1)
			end if
			if player.right == true
				temp1 = temp3
			end if
			if player.up == true
				temp2 = temp3
				FlipSign(temp2)
			end if
			if player.down == true
				temp2 = temp3
			end if
{ind(spirit_approach("NoSwap_glideVX", "temp1", c["spirit_accel"]), 3)}{ind(spirit_approach("NoSwap_glideVY", "temp2", c["spirit_accel"]), 3)}		else
			NoSwap_glideVX = 0
			NoSwap_glideVY = 0
		end if
		player.xvel = NoSwap_glideVX
		player.speed = NoSwap_glideVX
		player.yvel = NoSwap_glideVY
		if temp0 == true // she re-forms, keeping her speed, but not shooting up
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
			if player.yvel < 0
				player.yvel = 0
			end if
		end if
	end if
end if
"""


def spirit_flight_after(i):
    """After the player has moved: landing ends the flight; a wall or ceiling stops the orb's own velocity along it;
    the timer picks the transform's frames, then starts the orb's loop (the animation runs it from there)."""
    c = ABILITIES[i]
    n, ticks, total = c["spirit_transform"], c["spirit_ticks"], spirit_total(i)
    per_tick = f"\n\t\t\t\ttemp0 /= {ticks}" if ticks > 1 else ""
    return f"""if player.noswapAbility > 0
	if player.gravity == GRAVITY_GROUND // landed: she re-forms
		if player.animation == ANI_NOSWAP_ATTACK
			player.animation = ANI_WALKING
		end if
		player.noswapAbility = -1
	else
		if player.animation == ANI_NOSWAP_ATTACK
			if player.xvel == 0 // a wall
				NoSwap_glideVX = 0
			end if
			if player.yvel == 0 // a ceiling
				NoSwap_glideVY = 0
			end if
			if player.noswapAbility >= {c['spirit_frames']}
				player.prevAnimation = ANI_NOSWAP_ATTACK // the timer picks the frame, not the animation speed
				temp0 = {total} // the transform's frame
				temp0 -= player.noswapAbility{per_tick}
				if temp0 > {n} // (the flight's first frame: the orb)
					temp0 = {n}
				end if
				player.frame = temp0
				player.animationTimer = 0
			end if
		end if
	end if
end if
"""


# rocket_burst (Sparkster's): noswapAbility ROCKET_CHARGING + n while charging (n frames held), 1.. the burst's or the
# spin's frames left (the spin: NoSwap_glideVX / VY both 0), -1 used. Slot 41's frames, picked by the code:
ROCKET_CHARGING = 1000
ROCKET_FRAMES = {"charge": 0, "flash": 1, "down": 2, "down_fwd": 3, "fwd": 4, "up_fwd": 5, "up": 6, "spin": 7}
ROCKET_SPIN_FRAMES = 4  # the spin's frames (slot 41's 7-10)
ROCKET_ART = ROCKET_FRAMES["spin"] + ROCKET_SPIN_FRAMES  # slot 41's frame count


def rocket_burst_function(i):
    c = ABILITIES[i]
    return f"""// Rocket Burst: the jump ability of {ALIAS_OF[i]} (tools/abilities.py rocket_burst). Pressing jump in mid-air starts
// charging the rocket pack; letting go of jump fires it (NoSwap_AirAbilities, NoSwap_AfterUpdate). noswapAbility:
// {ROCKET_CHARGING} + frames charging; 1.. the burst's / the spin's frames left; -1 used
public function NoSwap_RocketBurst{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {ROCKET_CHARGING}
			player.animation = ANI_NOSWAP_ATTACK
			NoSwap_glideVX = 0
			NoSwap_glideVY = 0
			PlaySfx(SfxName[{c['rocket_charge_sfx']}], false)
		end if
	end if
end function


"""


def rocket_burst_air(i):
    """After the air state's gravity and air control. Charging: he drifts, falling at rocket_sink at most, until jump is
    let go of: before rocket_charge frames it fizzles; after, the burst goes where the d-pad points (8 ways, at
    rocket_speed, rocket_diag per axis on a diagonal) for rocket_frames, or with nothing held the Rocket Spin in place
    for rocket_spin_frames. The burst's own velocity replaces the game's (gravity off); the game still moves him, so
    walls and ceilings stop him (rocket_burst_after bounces him off them). A hit, a spring (anything changing his
    animation) ends it with their speed."""
    c = ABILITIES[i]
    return f"""if player.noswapAbility > 0 // Rocket Burst (tools/abilities.py rocket_burst_air)
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt, a spring...: over, their speed stays
	else
		if player.noswapAbility >= {ROCKET_CHARGING} // charging
			if player.noswapAbility < {ROCKET_CHARGING + 0x4000}
				player.noswapAbility++
			end if
			if player.yvel > {c['rocket_sink']:#x}
				player.yvel = {c['rocket_sink']:#x}
			end if
			temp0 = player.xvel // drifting to a stop
			temp0 /= 16
			player.xvel -= temp0
			player.speed = player.xvel
			if player.jumpHold == false // let go: fire
				if player.noswapAbility < {ROCKET_CHARGING + c['rocket_charge']}
					player.noswapAbility = -1 // too soon: it fizzles
					player.animation = ANI_JUMPING
				else
					temp0 = 0 // the d-pad's direction
					temp1 = 0
					if player.left == true
						temp0 = -1
					end if
					if player.right == true
						temp0 = 1
					end if
					if player.up == true
						temp1 = -1
					end if
					if player.down == true
						temp1 = 1
					end if
					temp2 = {c['rocket_speed']:#x}
					if temp0 != 0
						if temp1 != 0 // diagonals: the same speed overall
							temp2 = {c['rocket_diag']:#x}
						end if
					end if
					NoSwap_glideVX = temp0
					NoSwap_glideVX *= temp2
					NoSwap_glideVY = temp1
					NoSwap_glideVY *= temp2
					player.noswapAbility = {c['rocket_frames']}
					if temp0 == 0
						if temp1 == 0 // nothing held: the Rocket Spin, in place
							player.noswapAbility = {c['rocket_spin_frames']}
						end if
					end if
					if temp0 < 0
						player.direction = FACING_LEFT
					end if
					if temp0 > 0
						player.direction = FACING_RIGHT
					end if
					player.xvel = NoSwap_glideVX
					player.speed = NoSwap_glideVX
					player.yvel = NoSwap_glideVY
					PlaySfx(SfxName[{c['rocket_sfx']}], false)
				end if
			end if
		else
			player.noswapAbility--
			player.xvel = NoSwap_glideVX
			player.speed = NoSwap_glideVX
			player.yvel = NoSwap_glideVY
			if player.noswapAbility == 0 // over: he falls from here, keeping half his speed
				player.noswapAbility = -1
				player.animation = ANI_JUMPING
				player.xvel /= 2
				player.speed = player.xvel
				player.yvel /= 2
			end if
		end if
	end if
end if
"""


def rocket_burst_after(i):
    """After the player has moved: landing ends it; a wall or a ceiling that stopped the burst bounces it off (its
    velocity along that axis reversed: a ricochet), and he faces the way it goes; the code picks slot 41's frame (the
    charge and its flash, the Rocket Dash for the burst's angle, the Spin Attack's frames in turn)."""
    c = ABILITIES[i]
    fr = ROCKET_FRAMES
    ticks = c["rocket_spin_ticks"]
    return f"""if player.noswapAbility > 0 // Rocket Burst (tools/abilities.py rocket_burst_after)
	if player.gravity == GRAVITY_GROUND // landed: over
		if player.animation == ANI_NOSWAP_ATTACK
			player.animation = ANI_WALKING
		end if
		player.noswapAbility = -1
	else
		if player.animation == ANI_NOSWAP_ATTACK
			if player.noswapAbility >= {ROCKET_CHARGING}
				temp0 = {fr['charge']}
				if player.noswapAbility >= {ROCKET_CHARGING + c['rocket_charge']} // charged: it flashes
					temp1 = player.noswapAbility
					temp1 >>= 2
					temp1 &= 1
					temp0 += temp1
				end if
			else
				if NoSwap_glideVX != 0
					if player.xvel == 0 // a wall: ricochet
						FlipSign(NoSwap_glideVX)
					end if
				end if
				if NoSwap_glideVY < 0
					if player.yvel == 0 // a ceiling: ricochet
						FlipSign(NoSwap_glideVY)
					end if
				end if
				if NoSwap_glideVX < 0
					player.direction = FACING_LEFT
				end if
				if NoSwap_glideVX > 0
					player.direction = FACING_RIGHT
				end if
				temp0 = {fr['fwd']}
				if NoSwap_glideVY > 0
					temp0 = {fr['down_fwd']}
					if NoSwap_glideVX == 0
						temp0 = {fr['down']}
					end if
				end if
				if NoSwap_glideVY < 0
					temp0 = {fr['up_fwd']}
					if NoSwap_glideVX == 0
						temp0 = {fr['up']}
					end if
				end if
				if NoSwap_glideVX == 0
					if NoSwap_glideVY == 0 // the Rocket Spin: its frames in turn
						temp0 = {c['rocket_spin_frames']}
						temp0 -= player.noswapAbility
						temp0 /= {ticks}
						temp0 &= {ROCKET_SPIN_FRAMES - 1}
						temp0 += {fr['spin']}
					end if
				end if
			end if
			player.prevAnimation = ANI_NOSWAP_ATTACK // the code picks the frame, not the animation speed
			player.frame = temp0
			player.animationTimer = 0
		end if
	end if
end if
"""


def check_rocket_art(extra, game):
    """rocket_burst picks slot 41's frames itself: it needs all of them (ROCKET_FRAMES, then the spin's)."""
    ani = player_ani(extra, game)
    a = ani["anims"][ANI_ATTACK] if len(ani["anims"]) > ANI_ATTACK else None
    if not a or len(a["frames"]) != ROCKET_ART:
        sys.exit(f"{extra['file']}.ani ({game}): rocket_burst needs {ROCKET_ART} frames in slot {ANI_ATTACK}")


def screw_kick_start(i):
    """The Screw Kick's start by Y (screw_kick_function), from NoSwap_AirAbilities and NoSwap_AfterUpdate. A kick started
    by jump (kick_jump: Mecha Sonic's Spike Ball) is the jump ability instead (NoSwap_ScrewKick<i>): nothing here."""
    return "" if ABILITIES[i].get("kick_jump") else f"CallFunction(NoSwap_ScrewKickStart{i})\n"


def screw_kick_go(i, depth):
    """The kick's launch: noswapAbility 1 (kicking right) or 2 (left), its speed, pose and sound."""
    c = ABILITIES[i]
    return "".join("\t" * depth + l + "\n" for l in f"""player.noswapAbility = 1
player.xvel = {c['kick_x']:#x}
if player.direction == FACING_LEFT
	player.noswapAbility = 2
	FlipSign(player.xvel)
end if
player.yvel = {c['kick_y']:#x}
player.animation = ANI_NOSWAP_ATTACK
PlaySfx(SfxName[{c['kick_sfx']}], false)""".split("\n"))


def screw_kick_function(i):
    """Y in mid-air (the air states, or out of Knuckles' glide) starts the Screw Kick, once per airborne period.
    noswapAbility: 1 kicking right, 2 kicking left (the kick keeps its direction), -1 used. A function: both the air
    states (NoSwap_AirAbilities) and the glide (NoSwap_AfterUpdate) start it."""
    c = ABILITIES[i]
    if c.get("kick_jump"):  # started by jump: the jump ability, once per jump (the air states call it until it's used)
        return (f"// Spike Ball: the jump ability of {ALIAS_OF[i]}, a Screw Kick started by jump (tools/abilities.py "
                f"screw_kick_function)\npublic function NoSwap_ScrewKick{i}\n\tif player.jumpPress == true\n"
                "\t\tif player.noswapAbility == 0\n\t\t\tplayer.jumpAbilityState = 2\n" + screw_kick_go(i, 3)
                + "\t\tend if\n\tend if\nend function\n\n\n")
    body = f"""if player.noswapAbility == 0
	if keyPress[1].buttonY != false
		temp0 = false // in the air
		temp1 = false // gliding
		CheckEqual(player.state, Player_State_Air)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Air_NoDropDash)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_RollJump)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_GlideLeft)
		temp1 |= checkResult
		CheckEqual(player.state, Player_State_GlideRight)
		temp1 |= checkResult
		CheckEqual(player.state, Player_State_GlideDrop)
		temp1 |= checkResult
		temp0 |= temp1
		if player.animation == ANI_HURT
			temp0 = false
		end if
		if temp0 == true
			if temp1 == true // out of the glide, which doesn't come back this jump
				player.state = Player_State_Air
				player.jumpAbilityState = 2
			end if
{screw_kick_go(i, 3)}		end if
	end if
end if"""
    return (f"// Screw Kick: Y in mid-air or out of a glide starts it ({ALIAS_OF[i]}; tools/abilities.py screw_kick_function)\n"
            f"public function NoSwap_ScrewKickStart{i}\n" + "".join(f"\t{l}\n" if l else "\n" for l in body.split("\n"))
            + "end function\n\n\n")


def screw_kick_air(i):
    """Keeps the kick diving, direction locked. Started here, before the air state's jump ability (Knuckles' transforms
    on Y), but after NoSwap_TrySuper: Y transforms when it can, and kicks otherwise."""
    c = ABILITIES[i]
    return f"""if player.noswapAbility > 0
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt...
	else
		if player.yvel <= 0x10000 // a spring or anything else sending her up ends it
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
		else
			player.xvel = {c['kick_x']:#x}
			player.direction = FACING_RIGHT
			if player.noswapAbility == 2
				FlipSign(player.xvel)
				player.direction = FACING_LEFT
			end if
			player.yvel = {c['kick_y']:#x}
		end if
	end if
end if
""" + screw_kick_start(i)


def screw_kick_after(i):
    """After the player has moved: landing from the kick bounces her up a little; landing makes it ready again.
    Out of a glide, the kick starts here (the glide states don't run NoSwap_AirAbilities)."""
    if ABILITIES[i]["kick_bounce"]:
        landing = f"""		if player.animation == ANI_NOSWAP_ATTACK // landed from the kick: a small bounce
			CallFunction(Player_Action_Jump) // (uses temp0, temp1, temp6 and temp7)
			if player.gravity == GRAVITY_AIR // no roof in the way
				player.iypos += player.jumpOffset // the jump shifts for a jump ball, which this isn't yet
				player.yvel = -{ABILITIES[i]['kick_bounce']:#x}
			end if
		end if
		player.noswapAbility = -1 // no second kick in the bounce
"""
    else:  # (kick_bounce 0: he just lands, and the ground state picks his pose from his speed)
        landing = """		if player.animation == ANI_NOSWAP_ATTACK // landed from the kick
			player.animation = ANI_WALKING
		end if
		player.noswapAbility = -1
"""
    start = screw_kick_start(i)
    return """if player.noswapAbility > 0
	if player.gravity == GRAVITY_GROUND
""" + landing + """	end if
end if
if player.gravity == GRAVITY_GROUND
	player.noswapAbility = 0 // landed: ready again
""" + ("else\n" + "".join(f"\t{l}\n" if l else "\n" for l in start.rstrip("\n").split("\n")) if start else "") + """end if
"""


def triple_jump_scale(i, k):
    """The k-th jump's strength multiplier (k = 2, 3), in 1/256."""
    return round(ABILITIES[i]["triple_jumps"][k - 2] * 256)


def triple_jump_function(i):
    return f"""// Triple Jump: {ALIAS_OF[i]} has no mid-air move (the Triple Jump is in the jump itself: NoSwap_JumpStart, and the
// somersault in NoSwap_AfterUpdate). Y is his Fireball (unless it transforms: NoSwap_TrySuper).
public function NoSwap_TripleJump{i}
	if player.jumpPress == true
		player.jumpAbilityState = 2 // nothing more this jump
	end if
end function


"""


def triple_jump_start(i):
    """In Player_Action_Jump, once the jump is sure (no roof): the jump's number in the chain, and for the 2nd and 3rd
    a higher jump. temp1 is its strength (the jump strength plus a frame of gravity); temp0 is free there."""
    c = ABILITIES[i]
    return f"""temp0 = player.speed // running?
if temp0 < 0
	FlipSign(temp0)
end if
if temp0 < {c['triple_speed']:#x}
	NoSwap_jumpChain = 0 // too slow: a first jump
end if
if NoSwap_jumpChain >= 3
	NoSwap_jumpChain = 0 // after the third: a first jump again
end if
NoSwap_jumpChain++
if NoSwap_jumpChain > 1 // the 2nd and 3rd go higher
	temp0 = player.jumpStrength
	if NoSwap_jumpChain == 2
		temp0 *= {triple_jump_scale(i, 2)} // x{c['triple_jumps'][0]}
	else
		temp0 *= {triple_jump_scale(i, 3)} // x{c['triple_jumps'][1]}
	end if
	temp0 >>= 8
	temp1 = temp0
	temp1 += player.gravityStrength
end if
"""


def triple_jump_after(i, roll_states):
    """After the player has moved: the chain stays open while he's in the air from a jump and for triple_window frames
    on the ground after; rolling or a hit breaks it. The 3rd jump somersaults until he starts falling."""
    rolling = "".join(f"CheckEqual(player.state, {s})\ntemp0 |= checkResult\n" for s in roll_states)
    return f"""if player.animation == ANI_HURT
	NoSwap_jumpChain = 0
end if
temp0 = false // in the air from a jump (the jump pose, the somersault, the Fireball)?
if player.gravity == GRAVITY_AIR
	CheckEqual(player.animation, ANI_JUMPING)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_ATTACK)
	temp0 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_MELEE_AIR)
	temp0 |= checkResult
end if
if temp0 == true
	NoSwap_jumpWindow = {ABILITIES[i]['triple_window']}
else
	if NoSwap_jumpWindow > 0
		NoSwap_jumpWindow--
	else
		NoSwap_jumpChain = 0 // too long since the last jump
	end if
end if
temp0 = false
{rolling}if temp0 == true
	NoSwap_jumpChain = 0 // rolling: a jump out of it starts a new chain
end if
if NoSwap_jumpChain == 3 // the third jump: the somersault until he starts falling
	temp0 = false
	if player.gravity == GRAVITY_AIR
		if player.yvel < 0
			CheckEqual(player.animation, ANI_JUMPING)
			temp0 |= checkResult
			CheckEqual(player.animation, ANI_NOSWAP_ATTACK)
			temp0 |= checkResult
		end if
	end if
	if temp0 == true
		player.animation = ANI_NOSWAP_ATTACK
	else
		NoSwap_jumpChain = 4 // falling, landed, or something else took over (a spring, a hit, the Fireball)
		if player.animation == ANI_NOSWAP_ATTACK
			if player.gravity == GRAVITY_AIR
				player.animation = ANI_JUMPING
			else
				player.animation = ANI_WALKING
			end if
		end if
	end if
end if
"""


def double_jump_scale(i):
    """double_jump's strength multiplier, in 1/256."""
    return round(ABILITIES[i]["double_jump"] * 256)


def double_jump_function(i):
    c = ABILITIES[i]
    return f"""// Double Jump: the jump ability of {ALIAS_OF[i]}. A second jump, keeping her speed along, in the shell spin (an attack)
// until she starts falling (NoSwap_AfterUpdate)
public function NoSwap_DoubleJump{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = 1
			temp0 = player.jumpStrength
			temp0 *= {double_jump_scale(i)} // x{c['double_jump']}
			temp0 >>= 8
			FlipSign(temp0)
			player.yvel = temp0
			player.animation = ANI_NOSWAP_ATTACK
			PlaySfx(SfxName[Jump], false)
		end if
	end if
end function


"""


def puddle_total(i):
    """The Puddle Slide's game frames on the ground (melting, sliding, rising)."""
    c = ABILITIES[i]
    return c["puddle_ticks"] * len(c["puddle_frames"])


def puddle_slide_function(i):
    c = ABILITIES[i]
    if has(i, "melee") and not c.get("melee_cooldown"):
        sys.exit(f"puddle_slide: extra {i}'s melee needs melee_cooldown (the slide holds Y off through it)")
    return f"""// Puddle Slide: the jump ability of {ALIAS_OF[i]}. A drop in the dive (an attack); landing from it, the puddle
// (NoSwap_AfterUpdate). player.noswapAbility 1: dropping
public function NoSwap_PuddleSlide{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = 1
			if player.yvel < {c['puddle_drop']:#x}
				player.yvel = {c['puddle_drop']:#x}
			end if
			player.animation = ANI_NOSWAP_ATTACK
		end if
	end if
end function


// the Puddle Slide's frame (of slot 42) per step
private table NoSwap_PuddleFrames{i}
	{", ".join(map(str, c['puddle_frames']))}
end table


"""


def puddle_slide_air(i):
    """The drop, in the air: a hit or a spring ends it."""
    return """if player.noswapAbility == 1
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt...
	else
		if player.yvel <= 0x10000 // a spring, a badnik bounce or anything else sending him up ends it
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
		end if
	end if
end if
"""


def puddle_slide_after(i, ground=False):
    """After the player has moved: landing from the drop starts the puddle (NoSwap_puddle: its game frames left); then
    each frame on the ground the timer picks the frame, sets his speed and holds the blink. Before the melee's code, so
    NoSwap_cooldown holds Y off the same frame. ground: ground_slide's (its spindash action starts it: no drop, and Y
    stays free)."""
    c = ABILITIES[i]
    total, ticks = puddle_total(i), c["puddle_ticks"]
    out = f"""if player.noswapAbility == 1
	if player.gravity == GRAVITY_GROUND
		player.noswapAbility = -1
		if player.animation == ANI_NOSWAP_ATTACK // landed from the drop: melt
			NoSwap_puddle = {total}
			PlaySfx(SfxName[{c['puddle_sfx']}], false)
		end if
	end if
end if
if NoSwap_puddle > 0
	temp0 = false // still on the ground in a ground state (landing: the air state, until next frame)
	if player.gravity == GRAVITY_GROUND
		CheckEqual(player.state, Player_State_Ground)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Air)
		temp0 |= checkResult
		CheckEqual(player.state, Player_State_Air_NoDropDash)
		temp0 |= checkResult
	end if
	if player.animation == ANI_HURT
		temp0 = false
	end if
	if temp0 == false // a jump, a roll, a spring, a ledge, a hit...: over
		NoSwap_puddle = 0
	else
		NoSwap_puddle--
		temp1 = {total} // the step
		temp1 -= NoSwap_puddle
		temp1--
		temp1 /= {ticks}
		GetTableValue(temp2, temp1, NoSwap_PuddleFrames{i})
		player.animation = ANI_NOSWAP_HOVER
		player.prevAnimation = player.animation // the timer picks the frame
		player.frame = temp2
		player.animationTimer = 0
		temp2 = player.speed
		if temp1 < {c['puddle_move']} // melting and sliding: at least puddle_speed the way he faces
			if player.direction == FACING_LEFT
				FlipSign(temp2)
			end if
			if temp2 < {c['puddle_speed']:#x}
				temp2 = {c['puddle_speed']:#x}
			end if
			if player.direction == FACING_LEFT
				FlipSign(temp2)
			end if
			player.speed = temp2
		else // rising: slowing to a stop
			temp2 >>= 2
			player.speed -= temp2
		end if
		if player.blinkTimer < 3 // nothing hurts him (the post-hit blink's rule; under 4, so he doesn't flicker)
			player.blinkTimer = 3
		end if
		NoSwap_cooldown = 2 // and Y doesn't punch
		if NoSwap_puddle == 0 // risen (the blink runs out in 3 frames)
			player.animation = ANI_STOPPED
		end if
	end if
end if
"""
    if ground:  # (ground_slide: started by its spindash action, not a drop's landing; Y stays free, the shot fires)
        head = out[:out.index("if NoSwap_puddle > 0\n")]
        out = out[len(head):].replace("\t\tNoSwap_cooldown = 2 // and Y doesn't punch\n", "")
    return out


def ground_slide_function(i):
    """ground_slide: the extra's spindash action (a crouch's jump press): the slide starts (NoSwap_AfterUpdate runs it,
    puddle_slide_after's ground part), standing him up in the ground state."""
    c = ABILITIES[i]
    return f"""// Ground Slide: down + jump on the ground for {ALIAS_OF[i]}, instead of the Spin Dash (its spindash action)
public function NoSwap_GroundSlide{i}
	player.state = Player_State_Ground
	player.timer = 0
	NoSwap_puddle = {puddle_total(i)}
	PlaySfx(SfxName[{c['puddle_sfx']}], false)
end function


// the slide's frame (of slot 42) per step
private table NoSwap_PuddleFrames{i}
	{", ".join(map(str, c['puddle_frames']))}
end table


"""


def slide_running_extras():
    """ground_slide with "slide_running": down + jump slides out of a run too, not only out of a crouch."""
    return [i for i in with_ability("ground_slide") if ABILITIES[i].get("slide_running")]


def slide_running_function():
    """slide_running (Mega Man: Mega Man 3 slides straight out of a run; the user, 2026-09-29): called by the ground
    state's jump press (apply_ground_slide patches it in), checkResult true when it started the slide instead: down
    held, on the ground state, not sliding already. A crouch's jump press is the spindash action's, as before."""
    ids = slide_running_extras()
    if not ids:
        return ""
    cases = "".join(f"\t\tif stage.playerListPos == {ALIAS_OF[i]}\n\t\t\tCallFunction(NoSwap_GroundSlide{i})\n"
                    f"\t\t\tcheckResult = true\n\t\tend if\n" for i in ids)
    return ("// Slide out of a run (tools/abilities.py slide_running_function): checkResult true when the jump press\n"
            "// started the slide instead of the jump\n"
            "public function NoSwap_SlideRun\n\tcheckResult = false\n"
            "\tif player.down == true\n\t\tif NoSwap_puddle == 0\n" +
            "".join("\t" + l + "\n" for l in cases.rstrip("\n").split("\n")) +
            "\t\tend if\n\tend if\nend function\n\n\n")


def apply_ground_slide(t):
    """ground_slide: each such extra's spindash action is its slide (as apply_no_roll's plain jump, in its startup case),
    and it can't roll while sliding (NoSwap_RollAllowed, apply_no_roll's, says no while NoSwap_puddle runs)."""
    ids = with_ability("ground_slide")
    if not ids:
        return t
    if slide_running_extras():  # the ground state's jump press: the slide instead, for them, with down held
        fn = t.index("public function Player_State_Ground\n")
        end = t.index("\nend function", fn)
        jump = "\t\tif player.jumpPress == true\n\t\t\tCallFunction(Player_Action_Jump)\n\t\telse\n"
        if t[fn:end].count(jump) != 1:
            sys.exit("slide_running: the ground state's jump press isn't there once")
        i0 = t.index(jump, fn)
        t = (t[:i0] + "\t\tif player.jumpPress == true\n"
             "\t\t\tcheckResult = false\n"
             "\t\t\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] slide_running: down + jump slides out of a run\n"
             "\t\t\t\tCallFunction(NoSwap_SlideRun)\n"
             "\t\t\tend if\n"
             "\t\t\tif checkResult == false\n\t\t\t\tCallFunction(Player_Action_Jump)\n\t\t\tend if\n"
             "\t\telse\n" + t[i0 + len(jump):])
    spindash = next(f for f in ("actionSpindash", "spindashFunction") if f"player.{f}" in t)
    head = "public function NoSwap_RollAllowed\n\tcheckResult = true\n"
    if t.count(head) != 1:
        sys.exit("ground_slide: NoSwap_RollAllowed (apply_no_roll's) isn't there once")
    for i in ids:
        e = next(x for x in EXTRAS if x["id"] == i)
        case = t.index(startup_case(e))
        end = t.index("break", case)
        t = (t[:end] + "if options.attractMode == false // [NoSwap] abilities.py ground_slide: down + jump is the slide\n"
             f"\t\t\t\tplayer[SLOT_PLAYER1].{spindash} = NoSwap_GroundSlide{i}\n"
             "\t\t\tend if\n\t\t\t" + t[end:])
        t = t.replace(head, head + f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] ground_slide: no roll out of the slide\n"
                      "\t\tif NoSwap_puddle > 0\n\t\t\tcheckResult = false\n\t\tend if\n\tend if\n")
    return t


def no_stomp_slide_after(i):
    """no_stomp with ground_slide (Mega Man, Ray Poward): while the Slide lasts, monitors break at his touch (NoSwap_flags'
    surging bit, the Monitor scripts' Power Surge test) and walls break as for Knuckles (its breaks_walls bit, the
    BreakWall scripts' copy of his branch); both off again after it. (Badniks and bosses: apply_no_stomp.)"""
    if has(i, "power_surge") or has(i, "charge"):
        sys.exit(f"no_stomp: extra {i}'s Slide sets NoSwap_flags' surging bit, which power_surge / charge use")
    keep = has(i, "breaks_walls")  # (always on for him: left alone)
    surging, walls = FLAG_BITS["surging"], FLAG_BITS["breaks_walls"]
    return (f"if NoSwap_puddle > 0 // no_stomp: the Slide breaks monitors (NoSwap_flags bit {surging}) and walls (bit {walls})\n"
            f"\tSetBit(NoSwap_flags, {surging}, true)\n"
            + ("" if keep else f"\tSetBit(NoSwap_flags, {walls}, true)\n") +
            "else\n"
            f"\tSetBit(NoSwap_flags, {surging}, false)\n"
            + ("" if keep else f"\tSetBit(NoSwap_flags, {walls}, false)\n") +
            "end if\n")


def apply_no_stomp(t):
    """no_stomp (the user, 2026-10-02): Player_BadnikBreak (every badnik's) doesn't count the extra's jump as an attack:
    in the air in ANI_JUMPING (his jump pose; his moves have their own attack animations), not invincible and not Super,
    the badnik hurts him as walking into it does. Bosses (Player_CheckHit) and monitors (their own scripts) still take the
    jump. With ground_slide, the Slide (NoSwap_puddle running) counts as an attack in both functions. Only in a build
    with such an extra."""
    ids = with_ability("no_stomp")
    if not ids:
        return t
    anchor = "\tCheckNotEqual(player[currentPlayer].invincibleTimer, 0)\n\ttemp0 |= checkResult\n"
    for fn, stomp in (("Player_BadnikBreak", True), ("Player_CheckHit", False)):
        head = f"public function {fn}\n"
        if t.count(head) != 1:
            sys.exit(f"no_stomp: {fn} isn't there once")
        start = t.index(head)
        at = t.find(anchor, start)
        if at < 0 or at > t.index("\nend function", start):
            sys.exit(f"no_stomp: {fn}'s invincibility check isn't there")
        add = ""
        for i in ids:
            body = ""
            if stomp:
                body += ("\t\t\tif player[currentPlayer].gravity == GRAVITY_AIR // his jump isn't an attack (a badnik hurts him)\n"
                         "\t\t\t\tif player[currentPlayer].animation == ANI_JUMPING\n"
                         "\t\t\t\t\tif player[currentPlayer].invincibleTimer == 0\n"
                         "\t\t\t\t\t\tif Player_superState != SUPERSTATE_SUPER\n"
                         "\t\t\t\t\t\t\ttemp0 = false\n"
                         "\t\t\t\t\t\tend if\n\t\t\t\t\tend if\n\t\t\t\tend if\n\t\t\tend if\n")
            if has(i, "ground_slide"):
                body += ("\t\t\tif NoSwap_puddle > 0 // his Slide is an attack\n"
                         "\t\t\t\ttemp0 = true\n"
                         "\t\t\tend if\n")
            if body:
                add += (f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] abilities.py no_stomp\n"
                        "\t\tif player[currentPlayer].isSidekick == false\n" + body + "\t\tend if\n\tend if\n")
        if add:
            t = t[:at + len(anchor)] + add + t[at + len(anchor):]
    return t


def double_jump_after(i):
    """After the player has moved: the shell spin lasts while she rises."""
    return """if player.animation == ANI_NOSWAP_ATTACK // the Double Jump's shell spin
	if player.gravity == GRAVITY_GROUND
		player.animation = ANI_WALKING
	else
		if player.yvel >= 0
			player.animation = ANI_JUMPING // falling: the jump ball again
		end if
	end if
end if
"""



def thunder_zip_function(i):
    c = ABILITIES[i]
    return f"""// Thunder Zip: the jump ability of {ALIAS_OF[i]}. A blink-dash forward in a flash (an attack); the zip itself is in
// NoSwap_AirAbilities. NoSwap_zipCarry: her forward speed, or zip_carry if that's faster, signed for the zip's direction
public function NoSwap_ThunderZip{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {c['zip_pose']}
			player.animation = ANI_NOSWAP_ATTACK
			temp0 = player.xvel
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			if temp0 < {c['zip_carry']:#x}
				temp0 = {c['zip_carry']:#x}
			end if
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			NoSwap_zipCarry = temp0
			PlaySfx(SfxName[{c['zip_sfx']}], false)
		end if
	end if
end function


"""


def thunder_zip_air(i):
    """The zip (zip_frames at zip_speed, level, locked to its direction; the game's collision still stops her at a
    wall), then her speed along once, with gravity back; the pose lasts zip_pose frames in all."""
    c = ABILITIES[i]
    after = c["zip_pose"] - c["zip_frames"]
    return f"""if player.noswapAbility > 0
	if player.animation == ANI_NOSWAP_ATTACK
		if player.noswapAbility > {after} // the zip
			player.xvel = {c['zip_speed']:#x}
			player.direction = FACING_RIGHT
			if NoSwap_zipCarry < 0
				FlipSign(player.xvel)
				player.direction = FACING_LEFT
			end if
			player.yvel = 0
		end if
		if player.noswapAbility == {after} // out of it: her speed along, falling as usual
			player.xvel = NoSwap_zipCarry
		end if
		player.noswapAbility--
		if player.noswapAbility == 0
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
		end if
	else
		player.noswapAbility = -1 // hurt, a spring...: over for this jump
	end if
end if
"""


def warp_total(i):
    c = ABILITIES[i]
    return c["warp_vanish"] + c["warp_gone"] + c["warp_appear"]


def warp_count(i):
    """phase_warp: the path's steps (WARP_STEP px each)."""
    r = ABILITIES[i]["warp_range"]
    if r <= 0 or r % WARP_STEP:
        sys.exit(f"phase_warp: extra {i}: warp_range is a whole number of {WARP_STEP} px steps")
    return r // WARP_STEP


def warp_steps(i):
    """phase_warp: a path step, 16.16 per axis: straight, and on a diagonal (the same length overall)."""
    step = WARP_STEP << 16
    return step, step * DIAG >> 16


def phase_warp_function(i):
    """The jump ability (the press) and the destination search (NoSwap_WarpTo, called by phase_warp_air as he goes)."""
    c = ABILITIES[i]
    straight, diag = warp_steps(i)
    tests = "".join(f"""		player.xpos = temp0
		player.ypos = temp1
		ObjectTileCollision(CSIDE_FLOOR, {x}, {y}, player.collisionPlane)
		if checkResult == true
			temp3 = true
		end if
""" for x, y in WARP_POINTS)
    return f"""// Phase Warp: the jump ability of {ALIAS_OF[i]} (tools/abilities.py phase_warp). He flickers out, is gone, flickers back
// in (NoSwap_AirAbilities, NoSwap_AfterUpdate). noswapAbility: frames of the warp left; NoSwap_warpDir: where it goes
public function NoSwap_PhaseWarp{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = {warp_total(i)}
			temp0 = 1 // x + 1
			if player.left == true
				temp0 = 0
			end if
			if player.right == true
				temp0 = 2
			end if
			temp1 = 1 // y + 1
			if player.up == true
				temp1 = 0
			end if
			if player.down == true
				temp1 = 2
			end if
			if temp0 == 1
				if temp1 == 1 // nothing held: ahead
					temp0 = 2
					if player.direction == FACING_LEFT
						temp0 = 0
					end if
				end if
			end if
			temp1 *= 3
			temp0 += temp1
			NoSwap_warpDir = temp0
			NoSwap_warpVX = player.xvel
			player.animation = ANI_NOSWAP_ATTACK
			PlaySfx(SfxName[{c['warp_sfx']}], false)
		end if
	end if
end function


// Phase Warp: the move itself. Along the warp's direction, {warp_count(i)} steps of {WARP_STEP} px at most, stopping
// before the first where a point of his body is in solid terrain; he ends at the last clear one. (ObjectTileCollision
// moves the object it tests: each test starts from the step's spot.)
public function NoSwap_WarpTo{i}
	temp4 = NoSwap_warpDir
	temp5 = temp4
	temp5 /= 3
	temp5-- // y: -1, 0, 1
	temp4 %= 3
	temp4-- // x
	temp3 = {straight}
	if temp4 != 0
		if temp5 != 0 // a diagonal: the same length overall
			temp3 = {diag}
		end if
	end if
	temp4 *= temp3
	temp5 *= temp3
	temp6 = player.xpos // the last clear spot
	temp7 = player.ypos
	temp2 = 0
	while temp2 < {warp_count(i)}
		temp0 = temp6 // the next step's spot
		temp0 += temp4
		temp1 = temp7
		temp1 += temp5
		temp3 = false // blocked?
{tests}		if temp3 == true
			temp2 = {warp_count(i)} // stop before it
		else
			temp6 = temp0
			temp7 = temp1
			temp2++
		end if
	loop
	player.xpos = temp6
	player.ypos = temp7
end function


"""


def phase_warp_air(i):
    """Before the state moves him (after its gravity): held still, gone at the start of warp_gone (to the
    destination), and at the end his speed along from before, falling from there."""
    c = ABILITIES[i]
    at = c["warp_gone"] + c["warp_appear"]
    return f"""if player.noswapAbility > 0 // Phase Warp (tools/abilities.py phase_warp_air)
	if player.animation == ANI_NOSWAP_ATTACK
		player.xvel = 0 // held still (the state has added its gravity already)
		player.yvel = 0
		if player.noswapAbility == {at} // gone: to the destination
			CallFunction(NoSwap_WarpTo{i})
		end if
		player.noswapAbility--
		if player.noswapAbility == 0 // back: his speed along, falling from here
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
			player.xvel = NoSwap_warpVX
			player.yvel = 0
			player.visible = true
		end if
	else
		player.noswapAbility = -1 // a spring, the melee...: over for this jump
		player.visible = true
	end if
end if
"""


def phase_warp_after(i):
    """After the update (the post-hit blink has set his visibility): untouchable (the blink's rule, at 3: no flicker of
    its own), gone while warp_gone lasts, flickering (every other frame) while he goes and comes back. Landing ends it."""
    c = ABILITIES[i]
    at = c["warp_gone"] + c["warp_appear"]
    return f"""if player.noswapAbility > 0 // Phase Warp: untouchable, gone or flickering (tools/abilities.py phase_warp_after)
	if player.gravity == GRAVITY_GROUND
		player.noswapAbility = -1
		player.visible = true
	else
		if player.blinkTimer < 3
			player.blinkTimer = 3
		end if
		temp0 = player.noswapAbility
		temp0 &= 1
		player.visible = temp0 // (a flicker: every other frame)
		if player.noswapAbility <= {at}
			if player.noswapAbility > {c['warp_appear']}
				player.visible = false // gone
			end if
		end if
	end if
end if
"""


def extreme_gear_function(i):
    c = ABILITIES[i]
    return f"""// Extreme Gear: the jump ability of {ALIAS_OF[i]} (Sonic Riders' air surf). He snaps onto his board (an attack: it rams
// badniks) and surfs while jump is held (NoSwap_AirAbilities; landing and walls in NoSwap_AfterUpdate). noswapAbility: 1
// riding, -1 used. NoSwap_glideVX: the board's velocity (its sign: the way he rides); NoSwap_glideLift: lift frames left;
// NoSwap_glideVY: ride frames left (gear_frames)
public function NoSwap_ExtremeGear{i}
	if player.jumpPress == true
		if player.noswapAbility == 0
			player.jumpAbilityState = 2
			player.noswapAbility = 1
			player.animation = ANI_NOSWAP_ATTACK
			temp0 = player.xvel // his forward speed, at least gear_speed
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			if temp0 < {c['gear_speed']:#x}
				temp0 = {c['gear_speed']:#x}
			end if
			if player.direction != FACING_RIGHT
				FlipSign(temp0)
			end if
			NoSwap_glideVX = temp0
			player.xvel = temp0
			player.speed = temp0
			if player.yvel > 0 // onto the board: no falling, half a rise
				player.yvel = 0
			else
				player.yvel >>= 1
			end if
			NoSwap_glideLift = {c['gear_lift_frames']}
			NoSwap_glideVY = {c['gear_frames']} // the ride's length at most
			PlaySfx(SfxName[{c['gear_sfx']}], false)
		end if
	end if
end function


"""


def extreme_gear_air(i):
    """One frame of the ride, after the air state's gravity and air control (it overrides both): the board's speed
    (forward speeds it up, back brakes and carves round), his facing, and the sink or the lift."""
    c = ABILITIES[i]
    return f"""if player.noswapAbility == 1
	if player.animation != ANI_NOSWAP_ATTACK
		player.noswapAbility = -1 // hurt, a spring, the melee...: off the board
	else
		temp0 = player.jumpHold
		if NoSwap_glideVY <= 0 // gear_frames up: as if he'd let go
			temp0 = false
		end if
		if temp0 == false
			player.noswapAbility = -1 // let go: off the board, in the jump ball
			player.animation = ANI_JUMPING
		else
			NoSwap_glideVY--
			temp0 = NoSwap_glideVX // the board's speed, forward
			temp1 = player.right // forward / back
			temp2 = player.left
			if temp0 < 0
				FlipSign(temp0)
				temp1 = player.left
				temp2 = player.right
			end if
			if temp2 == true // back: braking; slow enough, he carves round to ride the other way
				temp0 -= {c['gear_brake']:#x}
				if temp0 <= {c['gear_turn']:#x}
					temp0 = {c['gear_turn']:#x}
					FlipSign(NoSwap_glideVX)
				end if
			else
				if temp0 < {c['gear_speed']:#x} // back up to cruising speed
					temp0 += {c['gear_recover']:#x}
					if temp0 > {c['gear_speed']:#x}
						temp0 = {c['gear_speed']:#x}
					end if
				else
					if temp1 == true // forward: speeding up (a faster start is kept)
						if temp0 < {c['gear_top']:#x}
							temp0 += {c['gear_accel']:#x}
							if temp0 > {c['gear_top']:#x}
								temp0 = {c['gear_top']:#x}
							end if
						end if
					end if
				end if
			end if
			if NoSwap_glideVX < 0
				FlipSign(temp0)
				player.direction = FACING_LEFT
			else
				player.direction = FACING_RIGHT
			end if
			NoSwap_glideVX = temp0
			player.xvel = temp0
			player.speed = temp0

			temp1 = false // lifting?
			if player.up == true
				if NoSwap_glideLift > 0
					temp1 = true
				end if
			end if
			if temp1 == true // up: the nose tilts up, a little lift (gear_lift_frames per ride)
				NoSwap_glideLift--
				if player.yvel > -{c['gear_rise']:#x}
					player.yvel -= player.gravityStrength // (this frame's gravity back off)
					player.yvel -= {c['gear_lift']:#x}
					if player.yvel < -{c['gear_rise']:#x}
						player.yvel = -{c['gear_rise']:#x}
					end if
				end if
			else
				if player.yvel > {c['gear_sink']:#x} // sinking slowly
					player.yvel = {c['gear_sink']:#x}
				end if
			end if
		end if
	end if
end if
"""


def extreme_gear_after(i):
    """After the player has moved: landing ends the ride, running on at the board's speed; a wall knocks him off."""
    return """if player.noswapAbility == 1
	if player.animation == ANI_NOSWAP_ATTACK
		if player.gravity == GRAVITY_GROUND // landed, Sonic Riders style: running on at the board's speed
			player.speed = NoSwap_glideVX
			player.animation = ANI_WALKING
			player.noswapAbility = -1
		else
			if player.xvel == 0 // a wall: off the board
				player.noswapAbility = -1
				player.animation = ANI_JUMPING
			end if
		end if
	end if
end if
"""


def charge_after(i):
    """charge (Heavy's): Y held on the ground in the plain ground state pushes him the way he faced when it started,
    harder the faster he goes; let go, he coasts with little friction down to his own top speed. NoSwap_charge: the
    speed it set last frame, signed by the direction (0: none). His physics values are the game's own each frame of it
    (Player_UpdatePhysicsState), then his top speed is raised to the charge's so the speed cap option doesn't clip it;
    they're put back when it ends. The frame follows the distance he covers (charge_stride px each), shown as the melee
    shows its frames (the game's own animation is replaced after it has animated)."""
    c = ABILITIES[i]
    stride = c["charge_stride"]
    n = charge_frames(i, "Sonic2u")
    return f"""SetBit(NoSwap_flags, {FLAG_BITS['juggernaut']}, false) // NoSwap_flags' juggernaut bit (value 128): set below while the charge is past his top speed
temp0 = false // Charge (tools/abilities.py charge_after): on the ground, in the plain ground state
if player.gravity == GRAVITY_GROUND
	if player.state == Player_State_Ground
		if player.animation != ANI_HURT
			temp0 = true
		end if
	end if
end if
{"if NoSwap_spark > 0 // (a Shine Spark stored or flying: no charge meanwhile)" + chr(10) + chr(9) + "temp0 = false" + chr(10) + "end if" + chr(10) if i in sparks() else ""}if temp0 == false
	if NoSwap_charge != 0 // off the ground (a jump keeps his speed), rolling, hurt: over
		NoSwap_charge = 0
		currentPlayer = player.entityPos
		CallFunction(Player_UpdatePhysicsState) // his own top speed back
	end if
else
	temp1 = keyDown[1].buttonY // pushing
	if NoSwap_charge == 1 // braked to a full stop (1: that mark): no new charge till Y is let go and pressed again
		if temp1 == false
			NoSwap_charge = 0
		end if
		temp1 = false
	end if
	if NoSwap_charge == 0
		if temp1 == true // it starts: the way he faces, from his speed that way, with a shove (charge_shove at least)
			temp2 = player.speed
			if player.direction == FACING_LEFT
				FlipSign(temp2)
			end if
			if temp2 < {c['charge_shove']}
				temp2 = {c['charge_shove']}
			end if
			if player.direction == FACING_LEFT
				FlipSign(temp2)
			end if
			NoSwap_charge = temp2
			player.speed = temp2 // (the shove moves him now: from a standstill, the wall check below saw his old speed, 0, and
			// ended every charge on its first frame, the user, 2026-09-30)
		end if
	end if
	temp2 = NoSwap_charge // (the stop's mark: not a charge)
	if temp2 == 1
		temp2 = 0
	end if
	if temp2 != 0
		temp2 = NoSwap_charge // its speed (temp3: its direction, 1 right / -1 left)
		temp3 = 1
		if temp2 < 0
			FlipSign(temp2)
			temp3 = -1
		end if
		temp4 = player.speed // his speed along it now: under half of last frame's, a wall stopped him
		temp4 *= temp3
		temp4 <<= 1
		if temp2 >= 0x20000
			if temp4 < temp2
				temp2 = 0
			end if
		end if
		temp6 = temp2 // (Player_UpdatePhysicsState uses temp0-temp4: temp2 came back 0, which ended every charge at once; the user
		// found it in Sonic 2, 2026-09-30)
		temp7 = temp3
		temp5 = temp1
		currentPlayer = player.entityPos
		CallFunction(Player_UpdatePhysicsState) // (his own values, this frame)
		temp1 = temp5
		temp2 = temp6
		temp3 = temp7
		temp5 = player.topSpeed
		temp6 = 0 // holding back brakes (Y held or not): charge_brake a frame, down to a full stop, which ends it
		if temp3 > 0
			if player.left == true
				temp6 = {c['charge_brake']}
			end if
		else
			if player.right == true
				temp6 = {c['charge_brake']}
			end if
		end if
		if temp2 > 0
			if temp6 > 0
				temp1 = false // (the slide's pose)
				temp2 -= temp6
				if temp2 <= 1 // stopped: never past zero into reverse
					temp2 = -1
				end if
			else
			if temp1 == true // pushing: harder the faster he goes
				temp6 = temp2
				temp6 *= {c['charge_gain']}
				temp6 >>= 10
				temp6 += {c['charge_accel']}
				temp2 += temp6
				if temp2 > {c['charge_top']}
					temp2 = {c['charge_top']}
				end if
			else // coasting: hard to stop
				temp2 -= {c['charge_friction']}
				if temp2 <= temp5 // back to his own top speed: the game's again
					temp2 = 0
				end if
			end if
			end if
		end if
		if temp2 == -1 // braked to a full stop: over, standing (Y must be pressed again)
			NoSwap_charge = 1
			player.speed = 0
			player.xvel = 0
			player.skidding = 0
			player.animation = ANI_STOPPED
			player.frame = 0
			temp2 = 0
		end if
		if temp2 == 0
			if NoSwap_charge != 1
				NoSwap_charge = 0
			end if
		else
			temp7 = temp2 // (its speed)
			if temp7 > temp5 // past his top speed: enemies can't hurt him (noswap_common.juggernaut: the enemies' scripts)
				SetBit(NoSwap_flags, {FLAG_BITS['juggernaut']}, true)
			end if
			if temp2 > player.topSpeed // (the speed cap option clips the ground speed at the top speed)
				player.topSpeed = temp2
			end if
			temp2 *= temp3
			NoSwap_charge = temp2
			player.speed = temp2
			if temp3 > 0
				player.direction = FACING_RIGHT
			else
				player.direction = FACING_LEFT
			end if
			player.skidding = 0
			if temp1 == true
				player.animation = ANI_NOSWAP_ATTACK // running
				if temp7 > temp5
					player.animation = ANI_NOSWAP_MELEE // past his top speed: the dash flash
				end if
				temp6 = player.xpos // one frame per {stride} px he covers (forward, either way he runs)
				temp6 >>= 16
				temp6 /= {stride}
				temp6 %= {n}
				if temp3 < 0
					FlipSign(temp6)
					temp6 += {n - 1}
				end if
				player.frame = temp6
			else
				player.animation = ANI_NOSWAP_MELEE_AIR // coasting: the slide
				player.frame = 0
			end if
			player.prevAnimation = player.animation // (the frame is picked here, not by the animation's speed)
			player.animationTimer = 0
		end if
	end if
end if
"""


# The Shine Spark can be launched from these (after the game's update: a ground jump has made it the air state, a
# crouch's jump the Spin Dash's)
SPARK_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
                "Player_State_Roll", "Player_State_LookUp", "Player_State_Crouch", "Player_State_Spindash"]


def spark_velocity(i, kind_var, dir_var, xvel, yvel, ind=""):
    """Lines setting xvel / yvel to the Shine Spark's flight (kind_var 1 up, 2 up-forward, 3 forward; dir_var 1 / -1)."""
    s, d = ABILITIES[i]["spark_speed"], spark_diag(i)
    return [f"{ind}if {kind_var} == 1 // straight up", f"{ind}\t{xvel} = 0", f"{ind}\t{yvel} = -{s:#x}", f"{ind}end if",
            f"{ind}if {kind_var} == 2 // up-forward (the same speed overall)", f"{ind}\t{xvel} = {d:#x}",
            f"{ind}\t{xvel} *= {dir_var}", f"{ind}\t{yvel} = -{d:#x}", f"{ind}end if",
            f"{ind}if {kind_var} == 3 // forward", f"{ind}\t{xvel} = {s:#x}", f"{ind}\t{xvel} *= {dir_var}",
            f"{ind}\t{yvel} = 0", f"{ind}end if"]


def spark_air(i):
    """The Shine Spark's flight in S1/S2, in NoSwap_AirAbilities (after the air state's gravity and air control, before
    the move): its own velocity, every frame. Only while its pose shows (a spring or a hit that took over is left
    alone: spark_after ends it)."""
    lines = spark_velocity(i, "temp0", "temp1", "player.xvel", "player.yvel", "\t\t")
    return f"""if NoSwap_spark > {SPARK_ACTIVE} // Shine Spark (tools/abilities.py spark_air): its flight, no gravity, no control
	temp2 = false
	CheckEqual(player.animation, ANI_NOSWAP_ATTACK_UP)
	temp2 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_MELEE)
	temp2 |= checkResult
	if temp2 == true
		temp0 = NoSwap_spark // its kind, and its way (temp1)
		temp0 -= {SPARK_ACTIVE}
		temp1 = 1
		if temp0 > 100
			temp0 -= 100
			temp1 = -1
		end if
""" + "\n".join(lines) + """
		player.speed = player.xvel
	end if
end if
"""


def spark_after(i):
    """The charge's Shine Spark in S1/S2 (Heavy's; the module's notes at his entry), after the player has moved (and
    after charge_after, which has set the juggernaut bit for this frame). NoSwap_spark: 0 none; 1..spark_store stored,
    frames left; above SPARK_ACTIVE flying (+ its kind 1 up, 2 up-forward, 3 forward, + 100 going left).
    - Flying: the terrain stops it (his speed along the flight under half of it: a wall, a ceiling; up or up-forward,
      landing), so do a spring or a hit (another animation) or an object's state; then he drops (the terrain's stop: no
      speed left). Forward, it runs along the ground if he's on it (his speed set here, his top speed raised as the
      charge's). Meanwhile enemies can't hurt him (the juggernaut bit) and his pose shows (slot 45 up / up-forward, the
      charge's dash frames forward, one per charge_stride px).
    - Storing: at full charge on the ground (the juggernaut bit, set by the charge this frame), down (the roll is kept
      off: spark_no_roll) ends the charge and stores the spark; he skids to a stop.
    - Stored: it counts down (a hit loses it); a jump press (whatever the game made of it: a jump, a Spin Dash) launches
      it, the way the d-pad says: a side held forward that way (with up, up-forward), else straight up."""
    c = ABILITIES[i]
    s, d, stride = c["spark_speed"], spark_diag(i), c["charge_stride"]
    n = charge_frames(i, "Sonic2u")
    jugg = FLAG_BITS["juggernaut"]
    states = "".join(f"\t\t\tCheckEqual(player.state, {st})\n\t\t\ttemp0 |= checkResult\n" for st in SPARK_STATES)
    return f"""if NoSwap_spark > {SPARK_ACTIVE} // Shine Spark (tools/abilities.py spark_after): flying
	temp0 = NoSwap_spark // its kind (1 up, 2 up-forward, 3 forward), and its way (temp1: 1 right, -1 left)
	temp0 -= {SPARK_ACTIVE}
	temp1 = 1
	if temp0 > 100
		temp0 -= 100
		temp1 = -1
	end if
	temp2 = true // still flying?
	temp3 = false // the terrain stopped it?
	temp4 = false
	CheckEqual(player.animation, ANI_NOSWAP_ATTACK_UP)
	temp4 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_MELEE)
	temp4 |= checkResult
	CheckEqual(player.state, Player_State_Air)
	temp5 = checkResult
	CheckEqual(player.state, Player_State_Ground)
	temp5 |= checkResult
	temp4 &= temp5
	if temp4 == false // a spring, a hit, an object took over
		temp2 = false
	else
		temp4 = player.xvel // his speed along the flight
		if player.gravity == GRAVITY_GROUND
			temp4 = player.speed
		end if
		temp4 *= temp1
		if player.gravity == GRAVITY_GROUND
			if temp0 == 3 // forward, running along the ground: a wall stops it
				if temp4 < {s // 2:#x}
					temp3 = true
				end if
			else
				temp3 = true // landed (or on a ceiling)
			end if
		else
			if temp0 != 3 // up or up-forward: the stage's top edge is his ceiling (as S3&K's, whose engine stops him there;
				// Sonic 1 and 2 let a player rise past it, and he flew off into the sky for good, the user, 2026-09-30).
				// The same line Tails' flight stops at
				temp6 = stage.curYBoundary1
				temp6 += 16
				temp6 <<= 16
				if player.ypos < temp6
					temp3 = true
				end if
			end if
			if temp0 == 1 // up: a ceiling
				if player.yvel > -{s // 2:#x}
					temp3 = true
				end if
			end if
			if temp0 == 2 // up-forward: a ceiling or a wall
				if player.yvel > -{d // 2:#x}
					temp3 = true
				end if
				if temp4 < {d // 2:#x}
					temp3 = true
				end if
			end if
			if temp0 == 3 // forward: a wall
				if temp4 < {s // 2:#x}
					temp3 = true
				end if
			end if
		end if
	end if
	if temp3 == true // the terrain stopped him: he drops from there
		temp2 = false
		if player.gravity == GRAVITY_AIR
			player.xvel = 0
			if player.yvel < 0
				player.yvel = 0
			end if
		end if
		player.speed = 0
		player.animation = ANI_WALKING
	end if
	if temp2 == false
		NoSwap_spark = 0
		currentPlayer = player.entityPos
		CallFunction(Player_UpdatePhysicsState) // his own top speed back
	else
		SetBit(NoSwap_flags, {jugg}, true) // enemies can't hurt him (noswap_common.juggernaut)
		player.direction = FACING_RIGHT
		if temp1 < 0
			player.direction = FACING_LEFT
		end if
		if temp0 == 3 // forward: the charge's dash frames, one per {stride} px
			player.animation = ANI_NOSWAP_MELEE
			temp6 = player.xpos
			temp6 >>= 16
			temp6 /= {stride}
			temp6 %= {n}
			if temp1 < 0
				FlipSign(temp6)
				temp6 += {n - 1}
			end if
			player.frame = temp6
			if player.gravity == GRAVITY_GROUND // along the ground: its speed (above his top speed)
				player.speed = {s:#x}
				player.speed *= temp1
				if player.topSpeed < {s:#x}
					player.topSpeed = {s:#x}
				end if
			end if
		else
			player.animation = ANI_NOSWAP_ATTACK_UP // up, up-forward: fists up
			player.frame = 0
		end if
		player.prevAnimation = player.animation
		player.animationTimer = 0
	end if
end if
if NoSwap_spark > 0
	if NoSwap_spark <= {c['spark_store']} // stored: glowing
		NoSwap_spark--
		if player.animation == ANI_HURT // a hit: it's gone
			NoSwap_spark = 0
		end if
		if NoSwap_spark > {c['spark_store'] - c['spark_skid_frames']} // just stored: he skids to a stop
			if player.gravity == GRAVITY_GROUND
				if player.state == Player_State_Ground
					if player.speed != 0
						temp0 = player.speed
						if temp0 < 0
							FlipSign(temp0)
						end if
						temp0 -= {c['spark_skid']:#x}
						if temp0 < 0
							temp0 = 0
						end if
						if player.speed < 0
							FlipSign(temp0)
						end if
						player.speed = temp0
						player.animation = ANI_SKIDDING
					end if
				end if
			end if
		end if
		if NoSwap_spark > 0
			if player.jumpPress == true // launch: the way the d-pad says
				temp0 = false
{states}				if player.animation == ANI_HURT
					temp0 = false
				end if
				if temp0 == true
					temp0 = 1 // straight up
					temp1 = 1
					if player.direction == FACING_LEFT
						temp1 = -1
					end if
					if player.left == true
						temp0 = 3
						temp1 = -1
					end if
					if player.right == true
						temp0 = 3
						temp1 = 1
					end if
					if temp0 == 3
						if player.up == true
							temp0 = 2 // up-forward
						end if
					end if
					NoSwap_spark = temp0
					NoSwap_spark += {SPARK_ACTIVE}
					player.direction = FACING_RIGHT
					if temp1 < 0
						NoSwap_spark += 100
						player.direction = FACING_LEFT
					end if
					player.state = Player_State_Air // into the air, gravity off (spark_air)
					player.gravity = GRAVITY_AIR
					player.angle = 0
					player.collisionMode = CMODE_FLOOR
					player.controlLock = 0
""" + "\n".join(spark_velocity(i, "temp0", "temp1", "player.xvel", "player.yvel", "\t\t\t\t\t")) + f"""
					player.speed = player.xvel
					player.animation = ANI_NOSWAP_ATTACK_UP
					if temp0 == 3
						player.animation = ANI_NOSWAP_MELEE
					end if
					player.prevAnimation = player.animation
					player.frame = 0
					player.animationTimer = 0
					SetBit(NoSwap_flags, {jugg}, true)
					PlaySfx(SfxName[{c['spark_sfx']}], false)
				end if
			end if
		end if
	end if
end if
GetBit(temp0, NoSwap_flags, {jugg}) // storing: down at full charge, on the ground
if temp0 == true
	if NoSwap_charge != 0
		if player.down == true
			if player.gravity == GRAVITY_GROUND
				if NoSwap_spark == 0
					NoSwap_charge = 0
					currentPlayer = player.entityPos
					CallFunction(Player_UpdatePhysicsState) // his own top speed back
					NoSwap_spark = {c['spark_store']}
					player.animation = ANI_SKIDDING
					PlaySfx(SfxName[{c['spark_store_sfx']}], false)
				end if
			end if
		end if
	end if
end if
"""


def spark_no_roll(t):
    """The Shine Spark (spark_after): no roll at full charge (down stores it instead) nor while one is stored or flying.
    NoSwap_RollAllowed (apply_no_roll's, which the ground state's roll starts ask) says no then, for these extras. No temp
    values: the ground state's live across the call (the juggernaut bit is NoSwap_flags' top one: 128 and up)."""
    ids = sparks()
    if not ids:
        return t
    head = "public function NoSwap_RollAllowed\n\tcheckResult = true\n"
    if t.count(head) != 1:
        sys.exit("spark: NoSwap_RollAllowed (apply_no_roll's) isn't there once")
    if FLAG_BITS["juggernaut"] != 7 or max(FLAG_BITS.values()) != 7:
        sys.exit("spark: NoSwap_RollAllowed tests the juggernaut bit as NoSwap_flags >= 128 (bit 7, the top one)")
    for i in ids:
        t = t.replace(head, head + f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] the Shine Spark: down stores it\n"
                      "\t\tif NoSwap_flags >= 128 // (at full charge: the juggernaut bit)\n\t\t\tcheckResult = false\n"
                      "\t\tend if\n\t\tif NoSwap_spark > 0 // (stored, or flying)\n\t\t\tcheckResult = false\n"
                      "\t\tend if\n\tend if\n")
    return t


def spark_glow_draw(t):
    """The Shine Spark's glow in Sonic 1/2 (a runtime palette effect, the art untouched), as charge_flash_draw's flash:
    while one is stored or flying, his greys (spark_glow_slots) are drawn in its colours (spark_glow_colours; the amount:
    spark_phase), written into banks 0 and 1 right before DrawObjectAnimation and put back from the Super glow's copy
    (banks 6 and 7) right after. Only temp0-temp3."""
    ids = sparks()
    if not ids:
        return t
    fns, pick = "", ""
    for i in ids:
        if next(e for e in EXTRAS if e["id"] == i)["super"]:
            sys.exit(f"spark: extra {i}: the glow puts his colours back from the Super glow's copy (\"super\" False)")
        slots = ABILITIES[i]["spark_glow_slots"]
        lo, n = min(slots), max(slots) - min(slots) + 1
        sets = "".join(f"\tif temp0 == {k}\n" + "".join(
            f"\t\tSetPaletteEntry(0, {slot}, {rgb:#08x})\n\t\tSetPaletteEntry(1, {slot}, {rgb:#08x})\n"
            for slot, rgb in sorted(pal.items())) + "\tend if\n" for k, pal in enumerate(spark_glow_colours(i)))
        phase = "".join(f"\t{l}\n" for l in spark_phase("temp0", SPARK_ACTIVE, "NoSwap_spark"))
        fns += f"""// [NoSwap] {ALIAS_OF[i]}'s Shine Spark glow (tools/abilities.py spark_glow_draw): before his draw, its colours
public function NoSwap_SparkGlow{i}
{phase}{sets}end function


// after his draw: his colours back (the Super glow's copy)
public function NoSwap_SparkUnglow{i}
	if NoSwap_spark > 0
		CopyPalette(6, {lo}, 0, {lo}, {n})
		CopyPalette(7, {lo}, 1, {lo}, {n})
	end if
end function


"""
        pick += (f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] the Shine Spark's glow\n"
                 f"\t\tCallFunction(NoSwap_SparkGlow{i})\n\tend if\n")
    t = patch(t, "public function Player_HandleAmyHitbox\n", fns + "public function Player_HandleAmyHitbox\n",
              "spark glow functions")
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    draw = t[start:end]
    if draw.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("spark glow: expected 1 DrawObjectAnimation in ObjectDraw")
    after = pick.replace("NoSwap_SparkGlow", "NoSwap_SparkUnglow").replace("the Shine Spark's glow", "his colours back")
    draw = draw.replace("\tDrawObjectAnimation()\n", pick + "\tDrawObjectAnimation()\n" + after)
    return t[:start] + draw + t[end:]


SPIN_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump"]


def spin_frames(i, game):
    """The spin's frames (anim slot 41, in the air; slot 43, on the ground, as many)."""
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = player_ani(e, game)["anims"]
    n = len(anims[ANI_ATTACK]["frames"]) if len(anims) > ANI_MELEE else 0
    if not n or len(anims[ANI_MELEE]["frames"]) != n:
        sys.exit(f"spin_attack: extra {i} needs its spin in slot {ANI_ATTACK} (air) and {ANI_MELEE} (ground) ({game})")
    return n


def spin_after(i):
    """spin_attack (Honey's), after the player has moved. NoSwap_spin: 0 ready; 1.. spinning (frames so far); below 0
    the cooldown. Y (a press, from the states SPIN_STATES; NoSwap_TrySuper had Y first in the jump ball) starts it; it
    goes on while Y is held, spin_frames at most, in those states. In the air gravity is partly taken back (after the
    move: the next frame's fall is the lighter one). The frame is picked by its own clock. NoSwap_spinVY keeps the
    vertical speed it left, for spin_before to tell a bounce the game gave her."""
    c = ABILITIES[i]
    n = spin_frames(i, "Sonic2u")
    states = "".join(f"CheckEqual(player.state, {st})\ntemp0 |= checkResult\n" for st in SPIN_STATES)
    return f"""temp0 = false // Spin Attack (tools/abilities.py spin_after): a state it can be in
{states}if player.animation == ANI_HURT
	temp0 = false
end if
if NoSwap_spin < 0 // the cooldown
	NoSwap_spin++
end if
if NoSwap_spin == 0
	if keyPress[1].buttonY != false
		if temp0 == true
			NoSwap_spin = 1
			PlaySfx(SfxName[{c['spin_sfx']}], false)
		end if
	end if
end if
if NoSwap_spin > 0
	if keyDown[1].buttonY == false // let go, too long or out of it: over
		temp0 = false
	end if
	if NoSwap_spin > {c['spin_frames']}
		temp0 = false
	end if
	if temp0 == false
		NoSwap_spin = -{c['spin_cooldown']}
		if player.gravity == GRAVITY_AIR
			if player.animation == ANI_NOSWAP_ATTACK
				player.animation = ANI_JUMPING
			end if
		else
			if player.animation == ANI_NOSWAP_MELEE
				player.animation = ANI_WALKING
			end if
		end if
	else
		temp1 = NoSwap_spin // its frame, by its own clock
		temp1 /= {c['spin_ticks']}
		temp1 %= {n}
		NoSwap_spin++
		if player.gravity == GRAVITY_AIR
			temp2 = player.gravityStrength // floaty: part of this frame's gravity taken back
			temp2 *= {256 - c['spin_gravity']}
			temp2 >>= 8
			player.yvel -= temp2
			player.animation = ANI_NOSWAP_ATTACK
		else
			player.animation = ANI_NOSWAP_MELEE
		end if
		player.frame = temp1
		player.prevAnimation = player.animation // (the frame is picked here)
		player.animationTimer = 0
	end if
end if
NoSwap_spinVY = player.yvel // (spin_before: what the game's objects do to it)
"""


def spin_lean_lines(i, v3=False):
    """spin_attack's lean (a draw effect): the lines setting temp6 (v3: TempValue6) to how far her spin frames are drawn
    turned (512 a turn; positive clockwise: moving right leans her top to the right), 0 when she isn't spinning. Uses
    temp1 too. From spin_lean / spin_lean_max, eased in over the spin's first 8 frames and out over the last 8."""
    c = ABILITIES[i]
    if v3:
        n = dict(t6="TempValue6", t1="TempValue1", spin="NoSwap.Spin", anim="Player.Animation", grav="Player.Gravity",
                 speed="Player.Speed", xvel="Player.XVelocity", air="ANI_NOSWAP_ATTACK", ground="ANI_NOSWAP_SHOT",
                 check="CheckEqual", result="CheckResult")
    else:
        n = dict(t6="temp6", t1="temp1", spin="NoSwap_spin", anim="player.animation", grav="player.gravity",
                 speed="player.speed", xvel="player.xvel", air="ANI_NOSWAP_ATTACK", ground="ANI_NOSWAP_MELEE",
                 check="CheckEqual", result="checkResult")
    m = c["spin_lean_max"]
    return f"""{n['t6']} = 0 // Spin Attack lean (tools/abilities.py spin_lean_lines): only while drawing
{n['t1']} = false
if {n['spin']} > 0
	{n['check']}({n['anim']}, {n['air']})
	{n['t1']} |= {n['result']}
	{n['check']}({n['anim']}, {n['ground']})
	{n['t1']} |= {n['result']}
end if
if {n['t1']} == true
	if {n['grav']} == GRAVITY_GROUND
		{n['t6']} = {n['speed']}
	else
		{n['t6']} = {n['xvel']}
	end if
	{n['t6']} *= {c['spin_lean']}
	{n['t6']} /= 0x10000
	if {n['t6']} > {m}
		{n['t6']} = {m}
	end if
	if {n['t6']} < -{m}
		{n['t6']} = -{m}
	end if
	{n['t1']} = {n['spin']} // eased in over the first 8 frames, out over the last 8
	{n['t1']} -= 1
	if {n['t1']} > 8
		{n['t1']} = 8
	end if
	if {n['spin']} > {c['spin_frames'] - 7}
		{n['t1']} = {c['spin_frames'] + 1}
		{n['t1']} -= {n['spin']}
	end if
	if {n['t1']} < 0
		{n['t1']} = 0
	end if
	{n['t6']} *= {n['t1']}
	{n['t6']} /= 8
end if
""".rstrip("\n").split("\n")


def spin_lean_draw(t):
    """spin_attack's lean in Sonic 1/2: the player's rotation turned by it around DrawObjectAnimation only (put back
    right after: the game never sees it). Her spin's animations are drawn with full rotation ("rot" 1)."""
    spins = with_ability("spin_attack")
    if not spins:
        return t
    body = ""
    for i in spins:
        body += f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] Spin Attack lean\n" \
            + "".join(f"\t\t{l}\n" for l in spin_lean_lines(i)) + "\tend if\n"
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    draw = t[start:end]
    if draw.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("spin lean: expected 1 DrawObjectAnimation in ObjectDraw")
    draw = draw.replace("\tDrawObjectAnimation()\n",
                        "\ttemp6 = 0\n" + body + "\ttemp7 = player.rotation\n\tif temp6 != 0\n"
                        "\t\tplayer.rotation += temp6\n\t\tplayer.rotation &= 511\n\tend if\n"
                        "\tDrawObjectAnimation()\n\tplayer.rotation = temp7\n")
    return t[:start] + draw + t[end:]


def float_lean_extras():
    """Extras with the floating lean (float_lean: Mephiles)."""
    return [i for i in ABILITIES if ABILITIES[i].get("float_lean")]


def float_lean_draw(t):
    """float_lean in Sonic 1/2 (a draw effect): around DrawObjectAnimation only, the walk / run (ANI_PEELOUT is
    ANI_RUNNING for extras: extra_startup) are drawn turned by the lean alone, float_lean / 512 of a turn per px per frame
    of his speed (ground speed; in the air his x speed; positive clockwise, so moving right leans his top to the right),
    float_lean_max at most, instead of the slope's rotation (he floats); put back right after, so the game never sees it.
    Only temp4 / temp5 (charge_flash_draw's temp0-temp3 and spin_lean_draw's temp6 / temp7 live across the draw)."""
    ids = float_lean_extras()
    if not ids:
        return t
    body = ""
    for i in ids:
        c = ABILITIES[i]
        m = c.get("float_lean_max", 32)
        body += f"""	if stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] floating lean (tools/abilities.py float_lean_draw)
		temp5 = false
		if player.animation == ANI_WALKING
			temp5 = true
		end if
		if player.animation == ANI_RUNNING
			temp5 = true
		end if
		if temp5 == true
			if player.gravity == GRAVITY_GROUND
				temp5 = player.speed
			else
				temp5 = player.xvel
			end if
			temp5 *= {c['float_lean']}
			temp5 /= 0x10000
			if temp5 > {m}
				temp5 = {m}
			end if
			if temp5 < -{m}
				temp5 = -{m}
			end if
			temp5 &= 511
			player.rotation = temp5 // the lean alone: no slope rotation
		end if
	end if
"""
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    draw = t[start:end]
    if draw.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("float lean: expected 1 DrawObjectAnimation in ObjectDraw")
    draw = draw.replace("\tDrawObjectAnimation()\n",
                        "\ttemp4 = player.rotation\n" + body + "\tDrawObjectAnimation()\n\tplayer.rotation = temp4\n")
    return t[:start] + draw + t[end:]


SINK_RISE = 1000  # sink: NoSwap_sink from here on is the rise (SINK_RISE + the sink's step it's back at)
SINK_VALUES = """private value NoSwap_sink = 0 // sink: 0 ready; below 0 the cooldown; 1.. sinking, then under; 1000.. rising
private alias 47 : ANI_NOSWAP_SINK // sink's frames (an extra without ray_glide / wall_cling / water_swim: their slot)
"""  # (packed: noswap_common.PACKED_VALUES)
SINK_SLOT = 47  # (CD 48, S3&K extra 5)


def sink_numbers(i):
    """sink's numbers, checked: (frames, ticks, under frames, under ticks, sink_max, cooldown, D: the sink's game frames).
    The slot-47 frames it names must exist in each game's built player .ani."""
    c = ABILITIES[i]
    frames, ticks = c["sink_frames"], c.get("sink_ticks", 1)
    under, uticks = c["sink_under"], c.get("sink_under_ticks", 1)
    d = ticks * len(frames)
    if not frames or not under or ticks < 1 or uticks < 1 or c["sink_max"] < 1 or d + c["sink_max"] >= SINK_RISE \
            or c.get("sink_cooldown", 0) < 1:
        sys.exit(f"sink: extra {i}: needs sink_frames, sink_under (frames), ticks of 1+, sink_max 1+ (with the sink's "
                 f"frames, under {SINK_RISE}) and a sink_cooldown")
    if any(has(i, m) for m in ("ray_glide", "wall_cling", "water_swim")):
        sys.exit(f"sink: extra {i}: its slot {SINK_SLOT} is also ray_glide's / wall_cling's / water_swim's")
    e = next(x for x in EXTRAS if x["id"] == i)
    for game in ("Sonic1u", "Sonic2u", "SonicCDu"):
        slot = SINK_SLOT + (1 if game == "SonicCDu" else 0)
        anims = player_ani(e, game)["anims"]
        n = len(anims[slot]["frames"]) if len(anims) > slot else 0
        if max(frames + under) >= n:
            sys.exit(f"sink: extra {i}: its sink frames go up to {max(frames + under)}, its slot {slot} has {n} ({game})")
    return frames, ticks, under, uticks, c["sink_max"], c["sink_cooldown"], d


def sink_function(i):
    """sink's frame tables (NoSwap_AfterUpdate's sink_after reads them)."""
    frames, _, under, _, _, _, _ = sink_numbers(i)
    return (f"// the Shadow Sink's frames (of slot {SINK_SLOT}) per step, sinking (and rising: backward)\n"
            f"private table NoSwap_SinkFrames{i}\n\t{', '.join(map(str, frames))}\nend table\n\n"
            f"// ...and while under, in turn\nprivate table NoSwap_SinkUnder{i}\n\t{', '.join(map(str, under))}\nend table\n\n\n")


def sink_after(i):
    """sink (the module's notes at the top), after the player has moved, before the shot (which down + Y on the ground
    never throws: shot_after). NoSwap_sink: 0 ready; below 0 the cooldown (counting up); 1..D sinking (D = its game
    frames), D+1..D+sink_max under, SINK_RISE + k rising (k: the sink's game frame it's back at, counting down). He's
    held in the game's static state (no input, no movement); letting go of down or Y rises from where he is."""
    c = ABILITIES[i]
    frames, ticks, under, uticks, most, cool, d = sink_numbers(i)
    r = SINK_RISE
    s = shot(i, "v4")
    pose = "\t\tNoSwap_shotPose = 0 // (no throw pose over it)\n" if s and s.get("pose") else ""
    return f"""if NoSwap_sink < 0 // Shadow Sink (tools/abilities.py sink_after): the cooldown
	NoSwap_sink++
end if
if NoSwap_sink == 0
	if keyPress[1].buttonY != false
		if player.down == true
			if player.gravity == GRAVITY_GROUND
				temp0 = false // standing, walking or crouching (not rolling)
				CheckEqual(player.state, Player_State_Ground)
				temp0 |= checkResult
				CheckEqual(player.state, Player_State_Crouch)
				temp0 |= checkResult
				if player.animation == ANI_HURT
					temp0 = false
				end if
				if temp0 == true
					NoSwap_sink = 1
					player.state = Player_State_Static // no input, no movement, until he's risen
					PlaySfx(SfxName[{c['sink_sfx']}], false)
				end if
			end if
		end if
	end if
end if
if NoSwap_sink > 0
	temp0 = true
	if player.state != Player_State_Static // a spring, an object, a hit that got through, death: over
		temp0 = false
	end if
	if player.gravity != GRAVITY_GROUND // the ground gave way
		if player.state == Player_State_Static
			player.state = Player_State_Air
			player.animation = ANI_WALKING
		end if
		temp0 = false
	end if
	if temp0 == false
		NoSwap_sink = -{cool}
		if player.animation == ANI_NOSWAP_SINK
			player.animation = ANI_WALKING
		end if
	else
		player.speed = 0
		player.xvel = 0
		player.yvel = 0
		if player.blinkTimer < 3 // nothing hurts him (the post-hit blink's rule; under 4, so he doesn't flicker)
			player.blinkTimer = 3
		end if
{pose}		if NoSwap_sink < {r}
			temp1 = keyDown[1].buttonY // both still held?
			if player.down == false
				temp1 = false
			end if
			if temp1 == false // let go: he rises, from where he is
				if NoSwap_sink > {d}
					NoSwap_sink = {r + d}
				else
					NoSwap_sink += {r}
				end if
			end if
		end if
		if NoSwap_sink <= {d} // sinking
			temp1 = NoSwap_sink
			temp1--
			temp1 /= {ticks}
			GetTableValue(temp2, temp1, NoSwap_SinkFrames{i})
			NoSwap_sink++
		else
			if NoSwap_sink < {r} // under
				temp1 = NoSwap_sink
				temp1 -= {d + 1}
				temp1 /= {uticks}
				temp1 %= {len(under)}
				GetTableValue(temp2, temp1, NoSwap_SinkUnder{i})
				NoSwap_sink++
				if NoSwap_sink > {d + most} // time's up: he rises
					NoSwap_sink = {r + d}
				end if
			else // rising: the sink's frames backward
				temp1 = NoSwap_sink
				temp1 -= {r + 1}
				temp1 /= {ticks}
				GetTableValue(temp2, temp1, NoSwap_SinkFrames{i})
				NoSwap_sink--
			end if
		end if
		player.animation = ANI_NOSWAP_SINK
		player.prevAnimation = ANI_NOSWAP_SINK // the timer picks the frame
		player.frame = temp2
		player.animationTimer = 0
		if NoSwap_sink == {r} // risen (the blink runs out in 3 frames)
			NoSwap_sink = -{cool}
			player.state = Player_State_Ground
			player.animation = ANI_STOPPED
		end if
	end if
end if
"""


def spin_before(i):
    """spin_attack, at the start of the player's update (before the state): while she spins, a badnik, monitor or boss
    that bounced her off itself left her vertical speed as the game's own code does it (from NoSwap_spinVY, what it was
    at the end of her last update): -(v + 2 gravity) off its top (a badnik she falls on, a monitor), v + 1 px going up
    or on the ground (a badnik), v - 1 px from below (a badnik), -v (a boss). Then the hard bounce: spin_bounce up, and
    on the ground spin_bounce_x away from the way she faces, into the air (a pinball)."""
    c = ABILITIES[i]
    return f"""if NoSwap_spin > 0 // Spin Attack: did the game bounce her off something? (tools/abilities.py spin_before)
	if player.yvel != NoSwap_spinVY // (something changed it since her last update)
		temp0 = false
		temp1 = player.gravityStrength
		temp1 <<= 1
		temp1 += NoSwap_spinVY
		FlipSign(temp1)
		if player.yvel == temp1 // off its top: a badnik she fell on, a monitor
			temp0 = true
		end if
		temp1 = NoSwap_spinVY
		temp1 += 0x10000
		if player.yvel == temp1 // a badnik, going up or on the ground
			temp0 = true
		end if
		temp1 -= 0x20000
		if player.yvel == temp1 // a badnik, from below it
			temp0 = true
		end if
		temp1 = NoSwap_spinVY
		FlipSign(temp1)
		if player.yvel == temp1 // a boss
			temp0 = true
		end if
		if temp0 == true // a hard bounce
			player.yvel = -{c['spin_bounce']}
			player.timer = 0 // (as after a spring: letting go of jump doesn't cut it short)
			if player.gravity == GRAVITY_GROUND // on the ground: up and away, a pinball
				temp1 = -{c['spin_bounce_x']}
				if player.direction == FACING_LEFT
					FlipSign(temp1)
				end if
				player.speed = temp1
				player.xvel = temp1
				player.gravity = GRAVITY_AIR
				player.state = Player_State_Air
				player.angle = 0
				player.collisionMode = CMODE_FLOOR
			end if
			NoSwap_spinVY = player.yvel
		end if
	end if
end if
"""


HIGH_KICK_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump"]
HIGH_KICK_KICK, HIGH_KICK_RECOVER = 1000, 2000  # NoSwap_hiKick's phases (the wind-up counts from 1)


def high_kick_frames(i, game):
    """The kick's frames (anim slot 43); slot 42 must hold the wind-up and the recovery (2 frames)."""
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = player_ani(e, game)["anims"]
    n = len(anims[ANI_MELEE]["frames"]) if len(anims) > ANI_MELEE else 0
    if not n or len(anims[ANI_HOVER]["frames"]) != 2:
        sys.exit(f"high_kick: extra {i} needs its kick in slot {ANI_MELEE} and the wind-up / recovery in {ANI_HOVER} ({game})")
    return n


def high_kick_after(i):
    """high_kick (Sally's Spin-Kick High Jump), after the player has moved (the module's notes at the top). NoSwap_hiKick:
    0 none; 1.. the wind-up (frames so far); HIGH_KICK_KICK.. the kick (frames so far); HIGH_KICK_RECOVER.. the recovery.
    Y (a press, from HIGH_KICK_STATES; NoSwap_TrySuper had Y first in the jump ball) starts it."""
    c = ABILITIES[i]
    n = high_kick_frames(i, "Sonic2u")
    k, r = HIGH_KICK_KICK, HIGH_KICK_RECOVER
    states = "".join(f"CheckEqual(player.state, {st})\ntemp0 |= checkResult\n" for st in HIGH_KICK_STATES)
    return f"""temp0 = false // Spin-Kick High Jump (tools/abilities.py high_kick_after): a state it can be in
{states}if player.animation == ANI_HURT
	temp0 = false
end if
if player.gravity == GRAVITY_GROUND
	if NoSwap_hiKick == 0 // (not in its wind-up)
		NoSwap_hiKickUsed = false
		if NoSwap_hiKickCool > 0
			NoSwap_hiKickCool--
		end if
	end if
end if
if NoSwap_hiKick == 0
	if keyPress[1].buttonY != false
		if temp0 == true
			temp1 = true
			if player.gravity == GRAVITY_GROUND
				if NoSwap_hiKickCool > 0
					temp1 = false
				end if
			else
				if NoSwap_hiKickUsed == true
					temp1 = false
				end if
			end if
			if temp1 == true
				NoSwap_hiKick = 1
				NoSwap_hiKickUsed = true
			end if
		end if
	end if
end if
if NoSwap_hiKick > 0
	if NoSwap_hiKick >= {k} // launched: landing ends it too
		if player.gravity == GRAVITY_GROUND
			temp0 = false
		end if
	end if
	if temp0 == false // hurt, rolling, an object took over, landed: over
		if player.animation != ANI_HURT
			if player.gravity == GRAVITY_AIR
				player.animation = ANI_JUMPING
			else
				player.animation = ANI_WALKING
			end if
		end if
		NoSwap_hiKick = 0
		NoSwap_hiKickCool = {c['high_kick_cooldown']}
	end if
end if
if NoSwap_hiKick > 0
	if NoSwap_hiKick < {k} // the wind-up: held still
		player.speed = 0
		player.xvel = 0
		if player.gravity == GRAVITY_AIR
			player.yvel = 0
		end if
		player.animation = ANI_NOSWAP_HOVER
		player.frame = 0
		NoSwap_hiKick++
		if NoSwap_hiKick > {c['high_kick_windup']} // launch, straight up
			if player.gravity == GRAVITY_GROUND
				player.gravity = GRAVITY_AIR
				player.state = Player_State_Air
				player.angle = 0
				player.collisionMode = CMODE_FLOOR
			end if
			player.yvel = -{c['high_kick_rise']:#x}
			player.timer = 0 // (as after a spring: letting go of jump doesn't cut it short)
			player.jumpAbilityState = 0
			PlaySfx(SfxName[{c['high_kick_sfx']}], false)
			NoSwap_hiKick = {k}
		end if
	else
		if NoSwap_hiKick < {r} // the kick, rising
			player.speed = 0
			player.xvel = 0
			temp1 = NoSwap_hiKick // its frame, by its own clock
			temp1 -= {k}
			temp1 /= {c['high_kick_ticks']}
			temp1 %= {n}
			player.animation = ANI_NOSWAP_MELEE
			player.frame = temp1
			NoSwap_hiKick++
			if player.yvel >= 0 // the top: the recovery
				NoSwap_hiKick = {r}
			end if
		end if
		if NoSwap_hiKick >= {r} // the recovery
			player.animation = ANI_NOSWAP_HOVER
			player.frame = 1
			NoSwap_hiKick++
			if NoSwap_hiKick > {r + c['high_kick_recover']} // then she falls as from a jump
				player.animation = ANI_JUMPING
				player.frame = 0
				player.jumpAbilityState = 1 // (her jump ability: once per jump, as ever)
				NoSwap_hiKick = 0
				NoSwap_hiKickCool = {c['high_kick_cooldown']}
			end if
		end if
	end if
	player.prevAnimation = player.animation // (the frame is picked here)
	player.animationTimer = 0
end if
"""


def charge_frames(i, game):
    """The charge's running frames (anim slot 41 of the extra's built player .ani; its slot 43, the dash flash, has as
    many: checked)."""
    e = next(x for x in EXTRAS if x["id"] == i)
    anims = player_ani(e, game)["anims"]
    n = len(anims[ANI_ATTACK]["frames"]) if len(anims) > ANI_MELEE_AIR else 0
    if not n or len(anims[ANI_MELEE]["frames"]) != n or not anims[ANI_MELEE_AIR]["frames"]:
        sys.exit(f"charge: extra {i} needs its running frames in slot {ANI_ATTACK}, as many past its top speed in slot "
                 f"{ANI_MELEE} and its coasting pose in slot {ANI_MELEE_AIR} ({game})")
    return n


def surge_active(i):
    """The script test for a Power Surge in progress (NoSwap_surge counts the surge down, then the cooldown)."""
    return f"NoSwap_surge > {ABILITIES[i]['surge_cooldown']}"


def power_surge_after(i):
    """After the player has moved: Y starts a Power Surge (from the states a shot can start in), which swaps her
    physics table (Player_UpdatePhysicsState's case for her) for surge_frames, then the cooldown runs."""
    c = ABILITIES[i]
    states = "".join(f"\t\tCheckEqual(player.state, {s})\n\t\ttemp0 |= checkResult\n"
                     for s in ("Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash",
                               "Player_State_RollJump", "Player_State_Roll"))
    return f"""if NoSwap_surge > 0 // Power Surge: its frames, then the cooldown
	NoSwap_surge--
	if NoSwap_surge == {c['surge_cooldown']} // over: her own physics again
		currentPlayer = player.entityPos
		CallFunction(Player_UpdatePhysicsState)
	end if
	if NoSwap_surge > {c['surge_cooldown']} // overcharged: the lightning shield's sparks fly off her every 16 frames
		temp0 = NoSwap_surge
		temp0 &= 15
		if temp0 == 0
{SURGE_SPARKS}		end if
	end if
end if
if NoSwap_surge == 0
	if keyPress[1].buttonY != false
		temp0 = false
{states}		if player.animation == ANI_HURT
			temp0 = false
		end if
		if player.animation == ANI_DYING
			temp0 = false
		end if
		if temp0 == true
			NoSwap_surge = {c['surge_frames'] + c['surge_cooldown']}
			currentPlayer = player.entityPos
			CallFunction(Player_UpdatePhysicsState)
			PlaySfx(SfxName[{c['surge_sfx']}], false)
{SURGE_SPARKS}
		end if
	end if
end if
SetBit(NoSwap_flags, {FLAG_BITS['surging']}, false) // NoSwap_flags' surging bit (value 16), for the shared scripts (Monitor)
if NoSwap_surge > {c['surge_cooldown']}
	SetBit(NoSwap_flags, {FLAG_BITS['surging']}, true)
end if
"""

# Power Surge's sparks: the game's own Lightning Spark object, four flying out diagonally as the lightning shield's
# double jump makes them (Sonic 1 and 2 only: CD has no such object). Indented for the surge code above.
SURGE_SPARKS = "".join(f"\t\t\tCreateTempObject(TypeName[Lightning Spark], 0, player.xpos, player.ypos)\n"
                       f"\t\t\tobject[tempObjectPos].xvel = {x}0x20000\n\t\t\tobject[tempObjectPos].yvel = {y}0x20000\n"
                       for x, y in (("-", "-"), ("", "-"), ("-", ""), ("", "")))


WALL_X, WALL_Y = 12, -2  # where Knuckles' glide tests for a wall: 12 px out (the collision box's edge is 10), 2 up


def wall_beside_function(i):
    return f"""// Wall Cling: is there a wall right beside {ALIAS_OF[i]} on side temp0 (FACING_RIGHT: her right)? temp1: the answer.
// Tested where Knuckles' glide grabs a wall. ObjectTileCollision moves the object it tests, so her position is put back.
public function NoSwap_WallBeside{i}
	temp6 = player.xpos
	temp7 = player.ypos
	if temp0 == FACING_RIGHT
		ObjectTileCollision(CSIDE_LWALL, {WALL_X}, {WALL_Y}, player.collisionPlane)
	else
		ObjectTileCollision(CSIDE_RWALL, -{WALL_X}, {WALL_Y}, player.collisionPlane)
	end if
	temp1 = checkResult
	player.xpos = temp6
	player.ypos = temp7
end function


"""


def let_go_of_wall(i, depth):
    """Lines: off the wall, in the jump ball, with the double jump ready again; that wall locked for a moment."""
    return "".join("\t" * depth + l + "\n" for l in [
        "NoSwap_cling = 0", f"NoSwap_clingLock = {ABILITIES[i]['cling_lock']}", "player.animation = ANI_JUMPING",
        "player.jumpAbilityState = 1 // the Double Jump ready again", "player.noswapAbility = 0"])


def wall_cling_air(i):
    """Before the player moves (after the air state's gravity and air control, whose results this replaces): on the
    wall she's held there, slides or climbs; jump kicks off it, letting go of toward or running out of time drops
    her. Off it, pushing toward a wall right beside her, from a jump, a fall or a Double Jump, grabs it."""
    c = ABILITIES[i]
    return f"""if NoSwap_cling > 0
	if player.animation != ANI_NOSWAP_CLING
		NoSwap_cling = 0 // hurt, a spring...: she lets go, their speed stays
	else
		NoSwap_cling++
		if NoSwap_clingDir == FACING_RIGHT // still holding toward the wall?
			temp0 = player.right
		else
			temp0 = player.left
		end if
		player.direction = NoSwap_clingDir // facing the wall (air control would turn her)
		player.speed = 0
		player.xvel = 0
		if player.jumpPress == true // a wall jump: kick off away from it
			player.speed = -{c['wall_jump_x']:#x}
			player.direction = FACING_LEFT
			if NoSwap_clingDir == FACING_LEFT
				FlipSign(player.speed)
				player.direction = FACING_RIGHT
			end if
			player.xvel = player.speed
			player.yvel = -{c['wall_jump_y']:#x}
			player.timer = 1 // letting go of jump cuts it short, as with a jump
			temp0 = 2
			PlaySfx(SfxName[Jump], false)
		else
			if NoSwap_cling > {c['cling_frames']}
				temp0 = false // out of time
			end if
			player.yvel = 0 // held still, then sliding down slowly
			if NoSwap_cling > {c['cling_hold']}
				player.yvel = {c['cling_slide']:#x}
			end if
			if player.up == true // climbing (the game's collision stops her at a floor or a ceiling)
				player.yvel = -{c['climb_speed']:#x}
			end if
			if player.down == true
				player.yvel = {c['climb_speed']:#x}
			end if
		end if
		if temp0 != true // off the wall (a wall jump, let go, out of time)
{let_go_of_wall(i, 3)}		end if
	end if
else
	temp0 = -1 // the side she's pushing toward
	if player.right == true
		temp0 = FACING_RIGHT
	end if
	if player.left == true
		temp0 = FACING_LEFT
	end if
	if NoSwap_clingLock > 0
		if temp0 == NoSwap_clingDir
			temp0 = -1 // the wall she just let go of
		end if
	end if
	temp1 = false // jumping, falling, or in the Double Jump
	CheckEqual(player.animation, ANI_JUMPING)
	temp1 |= checkResult
	CheckEqual(player.animation, ANI_NOSWAP_ATTACK)
	temp1 |= checkResult
	CheckEqual(player.animation, ANI_WALKING)
	temp1 |= checkResult
	CheckEqual(player.animation, ANI_RUNNING)
	temp1 |= checkResult
	if temp0 < 0
		temp1 = false
	end if
	if temp1 == true
		CallFunction(NoSwap_WallBeside{i})
		if temp1 == true // she grabs the wall
			NoSwap_cling = 1
			NoSwap_clingDir = temp0
			player.state = Player_State_Air // (out of a roll jump too: air control after a wall jump)
			player.animation = ANI_NOSWAP_CLING
			player.direction = temp0
			player.speed = 0
			player.xvel = 0
			player.yvel = 0
		end if
	end if
end if
"""


def wall_cling_after(i):
    """After the player has moved: landing ends the cling, and so does anything taking over her animation (a hit, a
    spring, an object). The wall ending beside her (climbed or slid past it) lets go; climbing up, with a hop up onto
    the ledge. The lock on the wall she let go of counts down while she's away from it."""
    c = ABILITIES[i]
    return f"""if NoSwap_cling > 0
	if player.gravity == GRAVITY_GROUND // landed (climbing down to the floor, too)
		NoSwap_cling = 0
		if player.animation == ANI_NOSWAP_CLING
			player.animation = ANI_WALKING
		end if
	else
		if player.animation != ANI_NOSWAP_CLING
			NoSwap_cling = 0 // hurt, a spring, an object...
		else
			temp0 = NoSwap_clingDir
			CallFunction(NoSwap_WallBeside{i})
			if temp1 == false // the wall ends
				if player.up == true // climbed to its top: a hop up onto the ledge, toward it
					player.yvel = -{c['ledge_hop']:#x}
					player.speed = {c['ledge_forward']:#x}
					if NoSwap_clingDir == FACING_LEFT
						FlipSign(player.speed)
					end if
					player.xvel = player.speed
					player.timer = 0 // (letting go of jump doesn't cut it short)
				end if
{let_go_of_wall(i, 4)}			end if
		end if
	end if
end if
if player.gravity == GRAVITY_GROUND
	NoSwap_clingLock = 0
else
	if NoSwap_clingLock > 0 // counting down only while she's away from the wall she let go of
		if NoSwap_cling == 0
			temp0 = NoSwap_clingDir
			CallFunction(NoSwap_WallBeside{i})
			if temp1 == false
				NoSwap_clingLock--
			end if
		end if
	end if
end if
"""


def pogo_function(i):
    return f"""// Pogo: the jump ability of {ALIAS_OF[i]}. Bounces on landing are in NoSwap_AfterUpdate.
public function NoSwap_Pogo{i}
	if player.jumpPress == true
		player.jumpAbilityState = 2
		player.animation = ANI_NOSWAP_ATTACK
		NoSwap_pogo = true
	end if
end function


"""


def pogo_after(i):
    """Runs after the player has moved: a pogo landing launches the next bounce while jump is held."""
    speed = ABILITIES[i]["pogo_speed"]
    return f"""if NoSwap_pogo == true
	if player.animation != ANI_NOSWAP_ATTACK
		NoSwap_pogo = false // hurt, springs, a shot... anything else ends the pogo
	else
		if player.gravity == GRAVITY_GROUND
			if player.jumpHold == true
				CallFunction(Player_Action_Jump)
				if player.gravity == GRAVITY_AIR // no roof in the way
					player.iypos += player.jumpOffset // the jump shifts for a jump ball, which this isn't
					player.yvel = -0x{speed:X}
					player.jumpAbilityState = 2
					player.animation = ANI_NOSWAP_ATTACK
					player.prevAnimation = ANI_NOSWAP_ATTACK
					player.frame = 0 // squash, then stretch
					player.animationTimer = 0
				else
					NoSwap_pogo = false
				end if
			else
				NoSwap_pogo = false
				player.animation = ANI_WALKING
			end if
		end if
	end if
end if
"""


def melee_after(i):
    """Y starts the melee: NoSwap_MeleeMove (shared by every extra with the move) sets temp7 when the move starts, and
    the extra's own sound is played here, as the game's scripts play sounds (they never keep SfxName[...] in a
    variable)."""
    nxt = "".join(f"\t{l}\n" for l in cycle_next(i).rstrip("\n").split("\n")) if cycle(i) else ""
    sfx = f"\tPlaySfx(SfxName[{ABILITIES[i]['melee_sfx']}], false)\n"
    import own_sounds  # (melee_run / melee_up with an own sound: theirs when that pose starts, NoSwap_whipAim 4 / 5)
    for k, (aim, _, _) in VARIANT_POSES.items():
        own = own_sounds.variant_mark(i, ABILITIES[i], k)
        if own:
            plain = own_sounds.strip(ABILITIES[i]['melee_sfx'])
            sfx = (f"\tif NoSwap_whipAim == {aim} // ({k}'s own sound)\n\t\tPlaySfx(SfxName[{plain}{own}], false)\n"
                   f"\telse\n" + "".join("\t" + l + "\n" for l in sfx.rstrip("\n").split("\n")) + "\tend if\n")
    return ("temp7 = false\nCallFunction(NoSwap_MeleeMove)\n"
            f"if temp7 == true // a shot started\n{sfx}{nxt}end if\n"
            + (nuke_spawn(i) if nuke(i) else ""))


def nuke(i):
    """The extra's melee_nuke (its Screen Nuke: the module's notes), checked; None without one."""
    n = ABILITIES.get(i, {}).get("melee_nuke")
    if n:
        c = ABILITIES[i]
        if not has(i, "melee") or shot(i, "v4") or shot2(i, "v4") or "melee_air_reach" in c or cycle(i):
            sys.exit(f"melee_nuke: extra {i}: a melee of its own (no shot, no own air pose, no ability_cycle)")
        if not 0 <= n["at"] < len(c["melee_reach"]) or n["hit"] < 1 or (n["flash"] and n["hit"] > len(n["flash"])):
            sys.exit(f"melee_nuke: extra {i}: \"at\" is a frame of the move, \"hit\" 1 to the flash's length (no "
                     f"flash: any length)")
        if any(not 0 <= a <= 255 for a in n["flash"]):
            sys.exit(f"melee_nuke: extra {i}: the flash's darkness is 0-255")
    return n


def nuke_left(i):
    """NoSwap_melee (frames of the move left, after this frame's count) on the nuke's frame."""
    c = ABILITIES[i]
    return c["melee_ticks"] * len(c["melee_reach"]) - 1 - nuke(i)["at"] * c["melee_ticks"]


def nuke_spawn(i):
    """melee_nuke, Sonic 1/2: on the move's frame `at` its object (a Tails Object, as the shots: tools/shots_v4.py), which
    draws the flash (TailsObject.txt: SetScreenFade by its value36) and hits all round him (nuke_update_body)."""
    import shots_v4
    n = nuke(i)
    return f"""if NoSwap_melee == {nuke_left(i)} // the nuke (melee_nuke: tools/abilities.py nuke_spawn): its flash and its hit
	CreateTempObject(TypeName[Tails Object], 0, player.xpos, player.ypos)
	arrayPos0 = object[tempObjectPos].entityPos
	if object[arrayPos0].type == TypeName[Tails Object] // (made)
		object[arrayPos0].state = {shots_v4.LIVE}
		object[arrayPos0].priority = PRIORITY_ACTIVE
		object[arrayPos0].interaction = true
		object[arrayPos0].drawOrder = 6 // (the top layer: the fade goes over everything)
		object[arrayPos0].value0 = 0
		object[arrayPos0].value36 = -1 // (nothing drawn until its update gives the fade)
		PlaySfx(SfxName[{n['sfx']}], false)
	end if
end if
"""


def nuke_update_body(i):
    """The nuke's own update (object: it): on player 1 all its life, the flash's darkness per frame in value36 (drawn by
    TailsObject.txt; -1: nothing), and for its first `hit` frames in the shots' group, looking like a jumping player to the
    enemies' shot loops with a box reach_x x reach_y round him (a hit marks a shot spent: the nuke goes on, LIVE again)."""
    import shots_v4
    n = nuke(i)
    # (no "flash": Bomb's nuke, the hit alone; value36 stays -1, nothing drawn)
    flash = f"""	temp0 = object.value0
	temp0--
	GetTableValue(object.value36, temp0, NoSwap_NukeFlash{i})
	if object.value36 == 0
		object.value36 = -1 // (nothing to draw)
	end if
""" if n["flash"] else ""
    return f"""object.value0++ // its age (melee_nuke: tools/abilities.py nuke_update_body)
object.xpos = object[0].xpos
object.ypos = object[0].ypos
if object.value0 > {max(len(n['flash']), n['hit'])}
	object.type = TypeName[Blank Object]
else
{flash}	if object.value0 <= {n['hit']}
		object.groupID = {shots_v4.GROUP} // the shots' group: the enemies' shot loops
		object.state = {shots_v4.LIVE}
		CallFunction(NoSwap_ShotLooks)
	else
		object.groupID = TypeName[Tails Object] // (out of it: its hit is over)
	end if
end if
"""


def nuke_looks(i):
    """What the enemies' shot loops read of the nuke (as shot_looks): a jumping player 1 with a box reach_x x reach_y round
    him (value38-41: top, bottom, left, right; S2's Masher and Coconuts read them as left, right, top, bottom: a box
    reach_y wide and reach_x tall there)."""
    n = nuke(i)
    return f"""object.animation = ANI_JUMPING
object.gravity = GRAVITY_GROUND
object.value16 = false // isSidekick
object.value19 = object[0].value19 // badnikBonus
object.value38 = -{n['reach_y']} // hitbox top, bottom, left, right
object.value39 = {n['reach_y']}
object.value40 = -{n['reach_x']}
object.value41 = {n['reach_x']}
"""


def nuke_tables():
    return "".join(f"// melee_nuke: the flash's darkness per frame of the nuke (0-255, SetScreenFade's alpha)\n"
                   f"private table NoSwap_NukeFlash{i}\n" + table_rows(nuke(i)["flash"]) + "end table\n\n"
                   for i in ABILITIES if v4_melee(i) and nuke(i) and nuke(i)["flash"])


def melee_poses(i):
    """The melee's two poses (ground, air), each (reach, top, bottom) per frame. Without melee_air_reach the air move
    is the ground one (its frames and box); without melee_top / melee_bottom the box reaches from 20 px above his
    centre to 20 px below (with melee_air_reach, the air move has its own melee_air_top / melee_air_bottom)."""
    c = ABILITIES[i]
    reach = c["melee_reach"]
    ground = (reach, c.get("melee_top", [-20] * len(reach)), c.get("melee_bottom", [20] * len(reach)))
    if "melee_air_reach" not in c:
        return ground, ground
    air = c["melee_air_reach"]
    return ground, (air, c.get("melee_air_top", [-20] * len(air)), c.get("melee_air_bottom", [20] * len(air)))


def melee_tables():
    """The melee's numbers for NoSwap_MeleeMove. NoSwap_MeleePoses holds each pose once: its frame count n, then n
    reaches, n tops and n bottoms; NoSwap_MeleePose is where the extra's ground pose starts (its air pose's: + ROW)."""
    ids = [i for i in ABILITIES if v4_melee(i)]
    data, at, starts = [], {}, {}
    for i in ids:
        for row, pose in list(enumerate(melee_poses(i) + whip_poses(i))) + variant_poses(i):  # (melee_whip: rows 2-4;
            # melee_run / melee_up: rows 5 / 6)
            if len({len(p) for p in pose}) != 1:
                sys.exit(f"melee: extra {i}'s reach / top / bottom lengths differ")
            key = repr(pose)
            if key not in starts:
                starts[key] = len(data)
                data += [len(pose[0])] + [v for p in pose for v in p]
            at[(i, row)] = starts[key]
    c = lambda i: ABILITIES[i]
    total = {i: c(i)["melee_ticks"] * max(len(p[0]) for p in melee_poses(i) + tuple(v for _, v in variant_poses(i)))
             for i in ids}
    return (extra_table("NoSwap_MeleeTicks", {i: c(i)["melee_ticks"] for i in ids},
                        "melee: game frames per frame of the move")
            + extra_table("NoSwap_MeleeTotal", total, "melee: the move's game frames (its longer pose)")
            + extra_table("NoSwap_MeleeCooldown", {i: c(i).get("melee_cooldown", 0) for i in ids},
                          "melee_cooldown: frames before the next (0: none; Espio's Leaf Swirl)")
            + extra_table("NoSwap_MeleeBlink", {i: c(i).get("melee_blink", 0) for i in ids},
                          "melee_blink: the post-hit blink after the move (0: none; Leaf Swirl's invisibility)")
            + extra_table("NoSwap_MeleeBusy", {i: int(has(i, "spirit_flight")) for i in ids},
                          "true: not out of the Spirit Flight (the orb already attacks)")
            + extra_table("NoSwap_MeleeStop", {i: int(bool(c(i).get("melee_stop"))) for i in ids},
                          "melee_stop: stands still for it on the ground (Tikal's punch, Mario's Fireball)")
            + extra_table("NoSwap_MeleeRadial", {i: int(bool(c(i).get("melee_radial"))) for i in ids},
                          "melee_radial: the reach is all around him (Silver's psychic sphere)")
            + (extra_table("NoSwap_MeleeBoost", {i: c(i).get("melee_boost", 0) for i in ids},
                           "melee_boost: a burst of speed instead of a shot, at least this fast (0: none; Mecha's Jet Boost)")
               if boosts() else "")
            + (extra_table("NoSwap_MeleeSafe", {i: int(bool(c(i).get("melee_safe"))) for i in ids},
                           "melee_safe: nothing hurts him during the move (Bomb's Self-Destruct)")
               if safes() else "")
            + (extra_table("NoSwap_MeleeCost", {i: int(bool(c(i).get("melee_cost"))) for i in ids},
                           "melee_cost: the move ends in a normal hit on him (Bomb's Self-Destruct)")
               if costs() else "")
            + (extra_table("NoSwap_MeleeHang", {i: int(bool(c(i).get("melee_hang"))) for i in ids},
                           "melee_hang: in the air he hangs still during the move (Tails Doll's Screen Nuke)")
               if hangs() else "")
            + (extra_table("NoSwap_MeleeWhip", {i: int(i in whips()) for i in ids},
                           "melee_whip: the whip's poses by the d-pad (crouching, up-forward, down: John's)")
               if whips() else "")
            + (extra_table("NoSwap_MeleeVariant", {i: int(i in variants()) for i in ids},
                           "melee_run / melee_up: the melee has a running or an up + Y pose (Axel's)")
               + extra_table("NoSwap_MeleeRun", {i: (c(i).get("melee_run") or {}).get("speed", 0) for i in ids},
                             "melee_run: the least ground speed that counts as running (0: none)")
               + extra_table("NoSwap_MeleeRunBoost", {i: (c(i).get("melee_run") or {}).get("boost", 0) for i in ids},
                             "melee_run: at least this fast the way he faces while it lasts (0: none)")
               + extra_table("NoSwap_MeleeUpRings", {i: c(i)["melee_up"].get("rings", 0) if c(i).get("melee_up")
                                                     else -1 for i in ids},
                             "melee_up: the rings up + Y takes (fewer: the plain melee; -1: no up + Y pose)", default=-1)
               + extra_table("NoSwap_MeleeUpRadial", {i: int(bool((c(i).get("melee_up") or {}).get("radial")))
                                                      for i in ids},
                             "melee_up: its reach goes all around him")
               if variants() else "")
            + extra_table("NoSwap_MeleePose", at, "where the extra's ground / air pose starts in NoSwap_MeleePoses"
                          + (" (melee_whip: crouching, up-forward, down: + 2, 3, 4 ROW)" if whips() else "")
                          + (" (melee_run / melee_up: + 5, 6 ROW)" if variants() else ""),
                          rows=7 if variants() else 5 if whips() else 2)
            + "// melee poses: frames n, then n reaches (px ahead of his centre), n box tops, n box bottoms\n"
            + "private table NoSwap_MeleePoses\n" + table_rows(data) + "end table\n\n")


def down_shots():
    """Extras whose shot is thrown with DOWN + Y (shot "input": "down": Mecha's spike ball). Only a build with one has the
    code that tells the two apart, so the other extras' scripts are unchanged."""
    return [i for i in ABILITIES if down_shot(i)]


def super_down():
    """NoSwap_TrySuper: down + Y in the jump ball throws the down + Y shot instead of transforming (down_shots)."""
    return "".join(f"\t\tif stage.playerListPos == {ALIAS_OF[i]} // down + Y throws its shot instead (shot \"input\" \"down\")\n"
                   "\t\t\tif player.down == true\n\t\t\t\ttemp0 = false\n\t\t\tend if\n\t\tend if\n"
                   for i in down_shots() + [i for i in ABILITIES if shot2(i, "v4") and not down_shot(i)])  # (and shot2's)


def whip_poses(i):
    """melee_whip's poses (crouching, up-forward, down), each (reach, top, bottom) per frame; () without."""
    w = ABILITIES[i].get("melee_whip")
    if not w:
        return ()
    if set(w) != set(WHIP_POSES):
        sys.exit(f"melee_whip: extra {i}: its poses are {', '.join(WHIP_POSES)}")
    return tuple((w[k]["reach"], w[k]["top"], w[k]["bottom"]) for k in WHIP_POSES)


def melee_up():
    """NoSwap_MeleeMove: with up held, Y is the up + Y shot's, not the melee's (up_shot: John's sub-weapons); in the air
    up with left or right held stays the melee's (the up-forward whip, melee_whip)."""
    return "".join(f"""			if stage.playerListPos == {ALIAS_OF[i]} // up + Y throws its shot (shot "input" "up")
				if player.up == true
					temp1 = true
					if player.gravity == GRAVITY_AIR // (up and a side in the air: the up-forward whip)
						if player.left == true
							temp1 = false
						end if
						if player.right == true
							temp1 = false
						end if
					end if
					if temp1 == true
						temp0 = false
					end if
				end if
			end if
""" for i in ABILITIES if v4_melee(i) and up_shot(i))


# melee_whip (John's): the pose picked as Y is pressed (NoSwap_whipAim 1 crouching, 2 up-forward, 3 down in the air; 0
# the plain ground / air ones), its row of NoSwap_MeleePose (+ 2-4 ROW) and animation shown while it lasts. Gated by the
# extra's NoSwap_MeleeWhip, as NoSwap_whipAim shares its value with other extras' moves (noswap_common.PACKED_VALUES)
WHIP_STATES = """			GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeWhip)
			if temp1 == true // (melee_whip: crouching too)
				CheckEqual(player.state, Player_State_Crouch)
				temp0 |= checkResult
			end if
"""
WHIP_START = """				GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeWhip)
				if temp1 == true // melee_whip: its pose by the d-pad (tools/abilities.py WHIP_START)
					NoSwap_whipAim = 0
					if player.gravity == GRAVITY_GROUND
						if player.state == Player_State_Crouch
							NoSwap_whipAim = 1
						end if
					else
						if player.down == true
							NoSwap_whipAim = 3
						else
							if player.up == true // (with a side held: melee_up)
								NoSwap_whipAim = 2
							end if
						end if
					end if
				end if
"""
WHIP_GROUND = f"""				GetTableValue(temp6, stage.playerListPos, NoSwap_MeleeWhip)
				if temp6 == true
					if NoSwap_whipAim == 1 // melee_whip: crouching
						player.animation = ANI_NOSWAP_ATTACK
						temp3 += {2 * ROW}
					end if
				end if
"""
WHIP_AIR = f"""				GetTableValue(temp6, stage.playerListPos, NoSwap_MeleeWhip)
				if temp6 == true
					if NoSwap_whipAim == 2 // melee_whip: up-forward
						player.animation = ANI_NOSWAP_ATTACK_UP
						temp3 += {2 * ROW}
					end if
					if NoSwap_whipAim == 3 // down
						player.animation = ANI_NOSWAP_ATTACK_DOWN
						temp3 += {3 * ROW}
					end if
				end if
"""
WHIP_VALUES = """public value NoSwap_whipAim = 0 // melee_whip: the whip's pose (1 crouching, 2 up-forward, 3 down; 0 the plain ones)
"""


def melee_down():
    """NoSwap_MeleeMove: with down held, Y is the down + Y shot's, not the melee's (down_shots)."""
    return "".join(f"\t\t\tif stage.playerListPos == {ALIAS_OF[i]} // down + Y throws its shot (shot \"input\" \"down\")\n"
                   "\t\t\t\tif player.down == true\n\t\t\t\t\ttemp0 = false\n\t\t\t\tend if\n\t\t\tend if\n"
                   for i in down_shots())


def boosts():
    """Extras whose melee is a burst of speed (melee_boost: Mecha Sonic's Jet Boost). Only a build with one has its
    table and code, so the other extras' scripts are unchanged."""
    return [i for i in ABILITIES if v4_melee(i) and ABILITIES[i].get("melee_boost")]


def safes():
    """Extras that nothing hurts during their melee (melee_safe: Bomb's Self-Destruct). Only a build with one has its
    table and code, so the other extras' scripts are unchanged."""
    return [i for i in ABILITIES if v4_melee(i) and ABILITIES[i].get("melee_safe")]


def costs():
    """Extras whose melee ends in a normal hit on themselves (melee_cost: Bomb's Self-Destruct). Only a build with one
    has its table and code."""
    return [i for i in ABILITIES if v4_melee(i) and ABILITIES[i].get("melee_cost")]


def hangs():
    """Extras that hang still in the air during their melee (melee_hang: Tails Doll's Screen Nuke). Only a build with one
    has its table and code."""
    return [i for i in ABILITIES if v4_melee(i) and ABILITIES[i].get("melee_hang")]


MELEE_HANG = """				GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeHang)
				if temp1 == true // hanging still in the air for it (melee_hang; the state's gravity next frame cancelled)
					player.xvel = 0
					player.yvel = player.gravityStrength
					FlipSign(player.yvel)
				end if
"""


MELEE_SAFE = """			GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeSafe)
			if temp1 == true // nothing hurts him during it (melee_safe: the post-hit blink's rule; under 4: no flicker)
				if player.blinkTimer < 3
					player.blinkTimer = 3
				end if
			end if
"""


# melee_cost: the end of the move hurts him as Player_Hit would (an invincibility star still keeps him; his own
# melee_safe blink doesn't): the game's own Player_State_GotHit next frame (rings, shield or death), knocked back from
# the way he faces. Only in the game's free states (not held by an object)
MELEE_COST = """				GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeCost)
				if temp1 == true // the cost (melee_cost: Bomb's Self-Destruct hurts him, a normal hit)
					temp1 = false
					CheckEqual(player.state, Player_State_Ground)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_Air)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_Air_NoDropDash)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_RollJump)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_Roll)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_LookUp)
					temp1 |= checkResult
					CheckEqual(player.state, Player_State_Crouch)
					temp1 |= checkResult
					if player.invincibleTimer != 0 // (an invincibility star: no hit, as Player_Hit)
						temp1 = false
					end if
					if temp1 == true
						player.blinkTimer = 0 // (his melee_safe blink isn't a guard against it)
						player.state = Player_State_GotHit // the game's own hurt: rings, shield or death
						if player.direction == FACING_RIGHT // knocked back
							player.speed = -0x20000
						else
							player.speed = 0x20000
						end if
					end if
				end if
"""


MELEE_BOOST = """			GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeBoost)
			if temp1 > 0 // a burst of speed (melee_boost: Mecha's Jet Boost): at least that fast the way he faces
				if player.gravity == GRAVITY_GROUND
					temp2 = player.speed
				else
					temp2 = player.xvel
					player.yvel = 0 // level in the air
				end if
				if player.direction == FACING_LEFT
					FlipSign(temp2)
				end if
				if temp2 < temp1
					temp2 = temp1
				end if
				if player.direction == FACING_LEFT
					FlipSign(temp2)
				end if
				if player.gravity == GRAVITY_GROUND
					player.speed = temp2
				else
					player.xvel = temp2
				end if
			end if
"""


def melee_function():
    """Y starts the melee (Y's attack that isn't a projectile). Its frames are driven from its timer, and while it's
    out the hitbox (only used by enemies and monitors) reaches out to it, like Amy's hammer. Each pose (ground, air) has its own frames, reach and
    box; the timer runs for the longer of the two and a pose ends when its frames run out. One function for every extra
    with the move: the numbers are in the tables of melee_tables, the sound in temp7 (set by NoSwap_AfterUpdate)."""
    return f"""// Melee: Y's attack (tools/abilities.py melee_function), for every extra with the move. Its numbers are the
// extra's in the NoSwap_Melee* tables (indexed by stage.playerListPos); temp7 = true: a shot started
public function NoSwap_MeleeMove
	GetTableValue(temp3, stage.playerListPos, NoSwap_MeleeCooldown)
	if temp3 > 0 // Leaf Swirl's cooldown
		if NoSwap_cooldown > 0
			NoSwap_cooldown--
		end if
	end if
	if NoSwap_melee == 0
{__import__("psycho_grab").melee_gate() if with_ability("psycho_grab") else "		if keyPress[1].buttonY != false" + chr(10)}			temp0 = false
			CheckEqual(player.state, Player_State_Ground)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_Air)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_Air_NoDropDash)
			temp0 |= checkResult
			CheckEqual(player.state, Player_State_RollJump)
			temp0 |= checkResult
{WHIP_STATES if whips() else ""}{VARIANT_STATES if variants() else ""}			if player.animation == ANI_HURT
				temp0 = false
			end if
			if temp3 > 0 // still cooling down
				if NoSwap_cooldown > 0
					temp0 = false
				end if
			end if
			GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeBusy)
			if temp1 == true
				if player.animation == ANI_NOSWAP_ATTACK // not out of the Spirit Flight (the orb already attacks)
					temp0 = false
				end if
			end if
{melee_down()}{melee_up()}			if temp0 == true
				GetTableValue(NoSwap_melee, stage.playerListPos, NoSwap_MeleeTotal)
{WHIP_START if whips() else ""}{VARIANT_START if variants() else ""}				NoSwap_pogo = false
				if temp3 > 0
					NoSwap_cooldown = temp3
				end if
				temp7 = true // (the caller plays the extra's sound)
			end if
		end if
	end if

	if NoSwap_melee > 0
		CheckEqual(player.animation, ANI_HURT)
		temp0 = checkResult
		CheckEqual(player.animation, ANI_DYING)
		temp0 |= checkResult
		CheckEqual(player.animation, ANI_DROWNING)
		temp0 |= checkResult
		if temp0 == true
			NoSwap_melee = 0
		else
{MELEE_BOOST if boosts() else ""}{MELEE_SAFE if safes() else ""}			temp3 = stage.playerListPos // the pose: its row in NoSwap_MeleePose
			if player.gravity == GRAVITY_GROUND
				player.animation = ANI_NOSWAP_MELEE
				GetTableValue(temp1, stage.playerListPos, NoSwap_MeleeStop)
				if temp1 == true // standing still for it (melee_stop: Tikal's punch, Mario's Fireball)
					player.speed = 0
					player.xvel = 0
				end if
{WHIP_GROUND if whips() else ""}			else
				player.animation = ANI_NOSWAP_MELEE_AIR
				temp3 += {ROW}
{WHIP_AIR if whips() else ""}{MELEE_HANG if hangs() else ""}			end if
{VARIANT_POSE.replace("ROW5", str(5 * ROW)).replace("ROW6", str(6 * ROW)) if variants() else ""}			GetTableValue(temp6, temp3, NoSwap_MeleePose)
			GetTableValue(temp2, temp6, NoSwap_MeleePoses) // the pose's frames
			player.prevAnimation = player.animation // the timer picks the frame, not the animation speed
			GetTableValue(temp0, stage.playerListPos, NoSwap_MeleeTotal)
			temp0 -= NoSwap_melee
			GetTableValue(temp3, stage.playerListPos, NoSwap_MeleeTicks)
			temp0 /= temp3
			if temp0 >= temp2 // (landed from the longer air move)
				temp0 = temp2
				temp0--
			end if
			player.frame = temp0
			player.animationTimer = 0
			temp6 += temp0 // the frame's reach, box top and box bottom
			temp6++
			GetTableValue(temp1, temp6, NoSwap_MeleePoses)
			temp6 += temp2
			GetTableValue(temp4, temp6, NoSwap_MeleePoses)
			temp6 += temp2
			GetTableValue(temp5, temp6, NoSwap_MeleePoses)
			GetTableValue(temp6, stage.playerListPos, NoSwap_MeleeRadial)
{VARIANT_RADIAL if variants() else ""}			if temp6 == true // an area attack (Silver's psychic sphere): the same reach all around
				player.hitboxRight = temp1
				player.hitboxBottom = temp1
				FlipSign(temp1)
				player.hitboxLeft = temp1
				player.hitboxTop = temp1
			else // a shot: the box reaches out ahead to the cork / lure
				player.hitboxTop = temp4
				player.hitboxBottom = temp5
				if player.direction == FACING_RIGHT
					player.hitboxLeft = -10
					player.hitboxRight = temp1
				else
					FlipSign(temp1)
					player.hitboxLeft = temp1
					player.hitboxRight = 10
				end if
			end if
			NoSwap_melee--
			GetTableValue(temp0, stage.playerListPos, NoSwap_MeleeTotal) // the pose's frames are all shown: done
			temp0 -= NoSwap_melee
			temp0 /= temp3
			if temp0 >= temp2
				NoSwap_melee = 0
			end if
			if NoSwap_melee == 0
				GetTableValue(temp3, stage.playerListPos, NoSwap_MeleeBlink)
				if temp3 > 0 // invisible: the post-hit blink, so nothing hurts him
					player.blinkTimer = temp3
				end if
				if player.gravity != GRAVITY_GROUND
					player.animation = ANI_JUMPING
				end if
{MELEE_COST if costs() else ""}			end if
		end if
	end if
	if NoSwap_melee == 0
		player.hitboxTop = C_BOX
		player.hitboxBottom = C_BOX
		player.hitboxLeft = C_BOX
		player.hitboxRight = C_BOX
	end if
end function


"""

# ---------------------------------------------------------------- shot (Sonic 1/2)
# A real projectile ("shot": Mario's fireball), the Sonic 1/2 side of the S3&K DLL's: the object, its group and what the
# game's enemies, monitors and bosses do with it are in tools/shots_v4.py. The player script throws it (shot_after, in
# NoSwap_AfterUpdate: Y, after NoSwap_TrySuper had its chance in the air) and moves it (NoSwap_ShotUpdate, called by
# the shot's own update, so `object` is the shot there). Only an extra with a shot has any of this code; every player
# script has NoSwap_ShotUpdate (TailsObject.txt calls it), a stub that removes the object where the extra has none.
SHOT_STATES = ["Player_State_Ground", "Player_State_Air", "Player_State_Air_NoDropDash", "Player_State_RollJump",
               "Player_State_Roll"]


SHOT_MOTIONS = ("bounce", "straight", "boomerang", "drop", "dip", "ground", "homing")  # (drop: falls with gravity, gone on the floor: Flicky's;
# dip: thrown down (start_vy > 0) with an upward pull (gravity < 0): it dips, levels out and rises, gone at a wall, floor
# or ceiling, after its lifetime or offscreen, as a drop without the landing puff: Mephiles' crystal)


def shot_frame_base(i, which=1):
    """Sonic 1/2: the TailsObject.txt frame the shot's first frame is (0, or shots_v4.FRAMES when its frames are drawn in
    the strip's big boxes: shots_v4.big). which 2: the second shot's ("shot2", the strip's second row: shots_v4.ROW2_FRAME,
    + shots_v4.FRAMES in its big boxes)."""
    import build_s3k_shot
    import shots_v4
    s = shot(i, "v4") if which == 1 else shot2(i, "v4")
    e = next(x for x in EXTRAS if x["id"] == i)
    frames = build_s3k_shot.frames(s["art"], e, build_s3k_shot.base_slots(e))[:shot_frame_count(s, "v4")]
    return (shots_v4.FRAMES if shots_v4.big(frames) else 0) + (shots_v4.ROW2_FRAME if which == 2 else 0)


def shot_frame_count(s, engine):
    """A shot's frames in an engine: its art's, but at most shots_v4.FRAMES in Sonic 1/2 (the strip's boxes; a "cycle"
    shot takes the first ones there). Art "two_rows": up to twice that, the rest in the strip's second row's small boxes
    (TailsObject frames straight after the big boxes': big art first, no second shot; shots_v4.place_art checks)."""
    import build_s3k_shot
    n = build_s3k_shot.frame_count(s.get("art", {}))
    if engine == "v4":
        import shots_v4
        n = min(n, shots_v4.FRAMES * (2 if s.get("art", {}).get("two_rows") else 1))
    return n


def check_shot(i):
    s = shot(i, "v4")
    if s["motion"] not in SHOT_MOTIONS:
        sys.exit(f"shot: extra {i}: motion {s['motion']!r} (Sonic 1/2: {', '.join(SHOT_MOTIONS)})")
    if s["motion"] in ("drop", "dip") and (s.get("aim") or s.get("up")):
        sys.exit(f"shot: extra {i}: a drop or dip isn't aimed and has no up throw")
    if s["motion"] == "dip" and not (s.get("start_vy", 0) > 0 and s.get("gravity", 0) < 0 and "max_fall" in s):
        sys.exit(f"shot: extra {i}: a dip is thrown down (start_vy > 0) with an upward pull (gravity < 0), and has max_fall")
    if set(s.get("ground", {})) - {"x", "y", "speed", "start_vy"} or (s.get("ground") and (s.get("aim") or s.get("up")
                                                                                          or s["motion"] == "boomerang")):
        sys.exit(f"shot: extra {i}: \"ground\" (thrown standing: x, y, speed, start_vy) is for an unaimed bounce / straight"
                 " / drop shot without \"up\"")
    if s["motion"] == "boomerang" and s.get("aim"):
        sys.exit(f"shot: extra {i}: a boomerang isn't aimed")
    check_homing(i, s)
    if "aim_down" in s and not s.get("aim"):
        sys.exit(f"shot: extra {i}: \"aim_down\" is for an aimed shot")
    if s.get("input") == "slam" and (s["motion"] != "ground" or not has(i, "hammer_drop") or shot2(i, "v4") or s.get("aim")
                                     or s.get("cycle") or s.get("pose")):
        sys.exit(f"shot: extra {i}: \"input\" \"slam\" (thrown by the Hammer Drop's landing, two at once) is for a \"ground\""
                 " shot of an extra with hammer_drop: no second shot, aim, cycle or pose")
    if s["motion"] == "ground" and s.get("input") != "slam":
        sys.exit(f"shot: extra {i}: a \"ground\" shot is thrown by the Hammer Drop's landing (\"input\" \"slam\")")
    if s.get("input", "y") not in ("y", "down", "slam", "up") or (s.get("input") in ("down", "up") and (
            s.get("aim") or not has(i, "melee"))):
        sys.exit(f"shot: extra {i}: \"input\" is \"down\" (down + Y throws; Y alone stays the melee, so it needs one; not "
                 "aimed: down would aim), \"up\" (likewise with up: John's sub-weapons) or left out (Y throws)")
    if ABILITIES[i].get("swap_shots"):
        check_swap_shots(i)
    if s.get("up") and (s.get("aim") or s["motion"] == "boomerang"):
        sys.exit(f"shot: extra {i}: \"up\" (the up-held throw's numbers) is for an unaimed bounce or straight shot")
    if set(s.get("up", {})) - {"speed", "start_vy", "pose_frame"}:
        sys.exit(f"shot: extra {i}: \"up\" takes speed, start_vy and pose_frame")
    if s.get("pose_always") not in (None, True, False) or (s.get("pose_always") and (s.get("up") or not s.get("pose"))):
        sys.exit(f"shot: extra {i}: \"pose_always\" (true: the throw pose at any speed and over the jump ball) needs a "
                 "pose, and no \"up\"")
    if s.get("aim_frames") and (not s.get("aim") or s.get("cycle") or shot_frame_count(s, "v4") < 5 or shot2(i, "v4")):
        sys.exit(f"shot: extra {i}: \"aim_frames\" (a frame per aim: level, forward-up, up, forward-down, down) is for an "
                 "aimed shot with 5+ frames, not a cycle one, and no second shot")
    if has(i, "ray_glide"):  # (NoSwap_shotPose shares its value with NoSwap_glideCap: PACKED_VALUES)
        sys.exit(f"shot: extra {i} has ray_glide, whose values the shot's share")
    check_both_ways(i, s)
    if s.get("autofire") not in (None, True, False) or (s.get("autofire") and (s.get("input", "y") != "y" or shot2(i, "v4"))):
        sys.exit(f"shot: extra {i}: \"autofire\" (true: thrown every cooldown frames while Y is held) is for a shot thrown "
                 "by Y alone, with no second shot")
    if s.get("aim_pose") and (not s.get("aim") or s.get("up") or s.get("pose_always") or not s.get("pose")
                              or s.get("pose", 0) >= UP_POSE):
        sys.exit(f"shot: extra {i}: \"aim_pose\" (the pose's frame is its aim's: 0 level, 1 forward-up, 2 up, 3 "
                 f"forward-down, 4 down) is for an aimed shot with a pose under {UP_POSE} frames, no \"up\" or pose_always")
    return s


def check_both_ways(i, s):
    """Shot "both_ways" (Mephiles' Crystal Shot): each throw is a pair, one each way, mirror images (the second on his
    other side, moving the other way, drawn flipped), his forward speed added to neither ("carry" false). Both come out
    together, so max_alive is at least 2. For an unaimed straight / bounce / drop / dip shot thrown by Y, nothing else."""
    if not s.get("both_ways"):
        return
    if (s["motion"] not in ("straight", "bounce", "drop", "dip") or s.get("aim") or s.get("up") or s.get("ground")
            or s.get("cycle") or s.get("input", "y") != "y" or s.get("carry") is not False or s["max_alive"] < 2):
        sys.exit(f"shot: extra {i}: \"both_ways\" is for an unaimed straight / bounce / drop / dip shot thrown by Y, with "
                 "\"carry\" false and max_alive 2 or more (no up, ground or cycle)")


def shot_update_body(i):
    """The shot's own update (object: the shot). Spent (an enemy's shot loop marked it: tools/shots_v4.py), too old, at
    a wall or offscreen: gone. Otherwise it moves, bounces off floors (motion "bounce"), animates, and shows the enemies
    what a jumping player 1 would (their loops read it as a player). With a second shot ("shot2"), its frame tells
    which one it is (the second's are shots_v4.ROW2_FRAME and up)."""
    import shots_v4
    if swap_shots(i, "v4"):  # (John's sub-weapons: each entry's own update, told by its frames)
        return swap_dispatch(i, lambda s, base, burn: one_shot_update_body(i, s, base, burn, swap=True))
    body = one_shot_update_body(i, check_shot(i), shot_frame_base(i))
    if not shot2(i, "v4"):
        return body
    body2 = one_shot_update_body(i, check_shot2(i), shot_frame_base(i, 2))
    ind = lambda b: "".join(f"\t{l}\n" if l else "\n" for l in b.rstrip("\n").split("\n"))
    return (f"if object.frame >= {shots_v4.ROW2_FRAME} // the second shot (\"shot2\": its frames are the strip's second row)\n"
            + ind(body2) + "else\n" + ind(body) + "end if\n")


def swap_layout(i):
    """Sonic 1/2: where each swap shot's frames are (monitor_swap's entries, in order): [(shot, base, burn_base, end)],
    TailsObject frames base.. its flight, burn_base.. a burning one's flames (None without), up to end, consecutive from
    shots_v4.SWAP_FRAME (shots_v4.place_swap_art pastes them in that order)."""
    import build_s3k_shot
    import shots_v4
    check_shot(i)
    out, at = [], shots_v4.SWAP_FRAME
    for s in swap_shots(i, "v4"):
        base = at
        at += build_s3k_shot.frame_count(s.get("art", {}))
        burn = None
        if "burn" in s:
            burn = at
            at += build_s3k_shot.frame_count(s["burn"]["art"])
        out.append((s, base, burn, at))
    if at > shots_v4.SWAP_FRAME + len(shots_v4.SWAP_BOXES):
        sys.exit(f"swap_shots: extra {i}: {at - shots_v4.SWAP_FRAME} frames, Sonic 1/2 have {len(shots_v4.SWAP_BOXES)}")
    return out


def swap_dispatch(i, make):
    """Code for each swap shot (make(shot, base, burn_base) -> its lines), told apart by its frame (swap_layout); the
    frame is read once first (temp7), as the code may change it."""
    ind = lambda b: "".join(f"\t\t{l}\n" if l else "\n" for l in b.rstrip("\n").split("\n"))
    out = "temp7 = object.frame // a swap shot: its entry, by its frames (tools/abilities.py swap_layout)\n"
    for k, (s, base, burn, end) in enumerate(swap_layout(i)):
        out += (f"if temp7 >= {base} // monitor_swap entry {k}: {monitor_entry(i, k)}\n\tif temp7 < {end}\n"
                + ind(make(s, base, burn)) + "\tend if\nend if\n")
    return out


def monitor_entry(i, k):
    import monitor_swap
    return monitor_swap.entries(i)[k]


HOMING_KEYS =("seek_speed", "seek_accel", "seek_frames", "return_speed", "return_accel", "catch")


def check_homing(i, s):
    """Motion "homing" (Cream's Cheese; every engine): its own numbers, and none of the throw variants. Its shots are
    the extra's only ones (no second shot, no slam), so the engines can tell a homing shot by the build alone."""
    if s["motion"] != "homing":
        return
    if any(k not in s for k in HOMING_KEYS) or any(s.get(k) for k in ("aim", "up", "ground", "cycle", "aim_frames",
                                                                       "pose_always")) \
            or s.get("input", "y") != "y" or shot2(i, "v4") or s["max_alive"] != 1:
        sys.exit(f"shot: extra {i}: a homing shot needs {', '.join(HOMING_KEYS)}, is thrown with Y alone, one at a "
                 "time, and has no aim, up, ground, cycle, aim_frames, pose_always or second shot")


def one_shot_update_body(i, s, base, burn_base=None, swap=False):
    """shot_update_body for one shot `s`, its frames from TailsObject frame `base`. swap: a swap shot's (swap_layout: its
    frames anywhere in the swap boxes; burn_base: a burning one's flames')."""
    import shots_v4
    art = s.get("art", {})
    r, ticks, count = s["radius"], art.get("ticks", 2), shot_frame_count(s, "v4")
    if base and (s["motion"] in ("boomerang", "homing") or s.get("cycle")) and not (swap and s["motion"] == "boomerang"):
        sys.exit(f"shot: extra {i}: a boomerang, homing or cycle shot drawn in shots_v4's big boxes isn't supported")
    if s["motion"] == "boomerang":
        return pierce_body(boomerang_update_body(s, ticks, count, base), s)
    if s["motion"] == "homing":
        return homing_update_body(i, s, ticks, count)
    bounce = s["motion"] == "bounce"
    pull = f"+= {s.get('gravity', 0)}" if s.get("gravity", 0) >= 0 else f"-= {-s['gravity']}"  # (a dip's pulls up)
    fall = (f"\t\tobject.yvel {pull}\n\t\tif object.yvel > {s['max_fall']}\n"
            f"\t\t\tobject.yvel = {s['max_fall']}\n\t\tend if\n") if s["motion"] in ("bounce", "drop", "dip") else ""
    floor = (f"""			if object.yvel >= 0 // bouncing along the floor
				ObjectTileCollision(CSIDE_FLOOR, 0, {r}, object.propertyValue)
				if checkResult == true
					object.yvel = {s['bounce']}
				end if
			else
				ObjectTileCollision(CSIDE_ROOF, 0, {-r}, object.propertyValue)
				if checkResult == true
					object.yvel = 0
				end if
			end if
""") if bounce else ""
    rest = f"""			if object.outOfBounds == true
				object.type = TypeName[Blank Object]
			else
""" + ("""				object.frame = object.value12 // (cycle: its own critter, picked when thrown)
""" if s.get("cycle") else """				object.frame = object.value12 // (aim_frames: its aim's frame, picked when thrown)
""" if s.get("aim_frames") else f"""				object.animationTimer++
				if object.animationTimer >= {ticks * count}
					object.animationTimer = 0
				end if
				object.frame = object.animationTimer
				object.frame /= {ticks}
""" + (f"""				object.frame += {base} // (its frames are shots_v4's big boxes)
""" if base else "")) + """				CallFunction(NoSwap_ShotLooks)
			end if
"""
    if s["motion"] == "ground":  # along the floor, gripped to it (as a walking badnik); no floor to grip: a ledge's end, gone
        rest = f"""			ObjectTileGrip(CSIDE_FLOOR, 0, {r}, object.propertyValue)
			if checkResult == false // off a ledge's end
				object.type = TypeName[Blank Object]
			else
""" + "".join("\t" + l + "\n" for l in rest.rstrip("\n").split("\n")) + "\t\t\tend if\n"
    elif s.get("terrain", True) is False:  # (swap shot "terrain" false: floors and ceilings don't end it: John's axe)
        pass
    elif not bounce:  # straight / drop / dip: gone at a floor below / a ceiling above, moving that way (aimed up or down)
        rest = (f"""			checkResult = false // a floor or a ceiling ahead (its leading edge)
			if object.yvel > 0
				ObjectTileCollision(CSIDE_FLOOR, 0, {r + 1}, object.propertyValue)
			end if
			if object.yvel < 0
				ObjectTileCollision(CSIDE_ROOF, 0, {-(r + 1)}, object.propertyValue)
			end if
			if checkResult == true
""" + ("""				if object.yvel > 0 // a drop landed: the game's own explosion puff there, as a badnik's bomb makes
					CreateTempObject(TypeName[Explosion], 0, object.xpos, object.ypos)
					object[tempObjectPos].drawOrder = object.drawOrder
				end if
""" if s["motion"] == "drop" and "burn" not in s else "") + (f"""				if object.yvel > 0 // landed: it bursts into its flames there (swap shot "burn": John's Holy Water)
					object.xvel = 0
					object.yvel = 0
					object.value0 = {s['lifetime'] - s['burn']['lifetime'] if 'burn' in s else 0} // (its flames' frames: the burn's lifetime)
					object.frame = {burn_base}
					object.animationTimer = 0
					CallFunction(NoSwap_ShotLooks)
				else
					object.type = TypeName[Blank Object]
				end if
""" if "burn" in s else """				object.type = TypeName[Blank Object]
""") + """			else
""" + "".join("\t" + l + "\n" for l in rest.rstrip("\n").split("\n")) + "\t\t\tend if\n")
    walls = "" if s.get("terrain", True) is False else f"""		if object.xvel > 0
			ObjectTileCollision(CSIDE_LWALL, {r + 1}, {-(r // 2)}, object.propertyValue)
		end if
		if object.xvel < 0
			ObjectTileCollision(CSIDE_RWALL, {-(r + 1)}, {-(r // 2)}, object.propertyValue)
		end if
"""  # (swap shot "terrain" false: no wall ends it either)
    body = f"""if object.state != {shots_v4.LIVE} // spent: it hit something (tools/shots_v4.py)
	object.type = TypeName[Blank Object]
else
	object.value0++ // its age
	if object.value0 > {s['lifetime']}
		object.type = TypeName[Blank Object]
	else
{fall}		object.xpos += object.xvel
		checkResult = false // a wall ahead (its leading edge, above its middle: not a floor or a slope)
{walls}		if checkResult == true
			object.type = TypeName[Blank Object]
		else
			object.ypos += object.yvel
{floor}{rest}		end if
	end if
end if
"""
    body = pierce_body(body, s)  # (shot "pierce": a hit doesn't spend it, it flies on: Mega Man's Charge Shot)
    if "burn" in s:  # (swap shot "burn": its flames, burning where it landed, before anything else)
        ind = lambda b: "".join(f"\t{l}\n" if l else "\n" for l in b.rstrip("\n").split("\n"))
        body = (f"if object.frame >= {burn_base} // burning (swap shot \"burn\": John's Holy Water's flames)\n"
                + ind(burn_body(s, burn_base)) + "else\n" + ind(body) + "end if\n")
    return v4_probe_sounds(body) if os.environ.get("NOSWAP_SHOT_PROBE") else body


def pierce_body(body, s):
    """Shot "pierce" (a hit doesn't spend it, it flies on: Mega Man's Charge Shot, John's sub-weapons): its update's first
    test (spent: gone) becomes "spent: live again"."""
    import shots_v4
    if not s.get("pierce"):
        return body
    head = "\tobject.type = TypeName[Blank Object] // (spent)\nelse\n"
    if "\tobject.type = TypeName[Blank Object]\nelse\n" not in body:
        sys.exit("shot: \"pierce\": its update's first test isn't the one it changes")
    body = body.replace("\tobject.type = TypeName[Blank Object]\nelse\n", head, 1)
    return body.replace(head, f"\tobject.state = {shots_v4.LIVE} // shot \"pierce\": it flies on through what it hit\n"
                        f"end if\nif object.state == {shots_v4.LIVE}\n", 1)


def burn_body(s, burn_base):
    """A burning swap shot's own update (object: the shot, landed: swap shot "burn", John's Holy Water): it stays where it
    landed, its flames' frames in turn, hurting whatever touches them (a hit doesn't end them), until its age passes its
    lifetime (set at the landing to leave the burn's lifetime)."""
    import build_s3k_shot
    import shots_v4
    art = s["burn"]["art"]
    ticks, count = art.get("ticks", 2), build_s3k_shot.frame_count(art)
    return f"""if object.state != {shots_v4.LIVE} // (a hit doesn't end the flames: they burn on)
	object.state = {shots_v4.LIVE}
end if
object.value0++ // its age
if object.value0 > {s['lifetime']}
	object.type = TypeName[Blank Object]
else
	object.animationTimer++
	if object.animationTimer >= {ticks * count}
		object.animationTimer = 0
	end if
	object.frame = object.animationTimer
	object.frame /= {ticks}
	object.frame += {burn_base}
	CallFunction(NoSwap_ShotLooks)
end if
"""


def boomerang_update_body(s, ticks, count, base=0):
    """A boomerang's own update (object: the shot; shot_update_body's for motion "boomerang"): spent (its first hit) or
    too old: gone. Out (value1 0): ahead at its own speed (xvel) plus player 1's forward speed, slowing by decel per
    frame; stopped, it comes back (value1 1), homing on her hand (y px below her centre) wherever she is now: per axis a
    target speed of 1/8 of the gap, at most return_speed, reached at return_accel per frame, plus her own velocity.
    Within catch px of her it's caught: gone. No terrain (it flies through walls); offscreen: gone. (The DLL's
    BoomerangUpdate, NoSwapS3K.cpp; Sonic CD's: shots_v3.boomerang_body.)"""
    import shots_v4
    rmax, racc, catch = s["return_speed"], s["return_accel"], s["catch"] << 16
    frame_base = f"\t\t\t\tobject.frame += {base} // (a swap shot's: its frames in the swap boxes)\n" if base else ""

    def offset(var, px):  # (her hand: y px below her centre; a negative one as a subtraction)
        return "" if not px else f"\t\t\t{var} {'+=' if px > 0 else '-='} {abs(px) << 16}\n"

    def home(axis, dy=0):
        return f"""			temp0 = object[0].{axis}pos // {axis}: the gap to her, /8, at most return_speed
{offset("temp0", dy)}			temp0 -= object.{axis}pos
			temp0 /= 8
			if temp0 > {rmax}
				temp0 = {rmax}
			end if
			if temp0 < -{rmax}
				temp0 = -{rmax}
			end if
			temp0 -= object.{axis}vel // toward it at most return_accel this frame
			if temp0 > {racc}
				temp0 = {racc}
			end if
			if temp0 < -{racc}
				temp0 = -{racc}
			end if
			object.{axis}vel += temp0
			object.{axis}pos += object.{axis}vel
			object.{axis}pos += object[0].{axis}vel // (plus her own velocity: running doesn't outpace it)
"""
    body = f"""if object.state != {shots_v4.LIVE} // spent: it hit something (tools/shots_v4.py)
	object.type = TypeName[Blank Object]
else
	object.value0++ // its age
	if object.value0 > {s['lifetime']}
		object.type = TypeName[Blank Object]
	else
		if object.value1 == 0 // a boomerang flying out (tools/abilities.py boomerang_update_body)
			temp0 = object[0].xvel // her own forward speed along (so she doesn't run into it)
			if object.direction == FACING_LEFT
				FlipSign(temp0)
			end if
			if temp0 < 0
				temp0 = 0
			end if
			if object.direction == FACING_LEFT
				FlipSign(temp0)
			end if
			temp0 += object.xvel
			object.xpos += temp0
			temp1 = false // slowing down; stopped: it comes back
			if object.direction == FACING_LEFT
				object.xvel += {s['decel']}
				if object.xvel > -1
					temp1 = true
				end if
			else
				object.xvel -= {s['decel']}
				if object.xvel < 1
					temp1 = true
				end if
			end if
			if temp1 == true
				object.xvel = 0
				object.yvel = 0
				object.value1 = 1
			end if
		else // coming back, homing on her hand
{home("x")}{home("y", s["y"])}			temp0 = object[0].xpos // within catch px of her hand: caught
			temp0 -= object.xpos
			if temp0 < 0
				FlipSign(temp0)
			end if
			temp1 = object[0].ypos
{offset("temp1", s["y"])}			temp1 -= object.ypos
			if temp1 < 0
				FlipSign(temp1)
			end if
			if temp0 < {catch}
				if temp1 < {catch}
					object.value1 = 2
				end if
			end if
		end if
		if object.value1 == 2
			object.type = TypeName[Blank Object]
		else
			if object.outOfBounds == true
				object.type = TypeName[Blank Object]
			else
				object.animationTimer++
				if object.animationTimer >= {ticks * count}
					object.animationTimer = 0
				end if
				object.frame = object.animationTimer
				object.frame /= {ticks}
{frame_base}				CallFunction(NoSwap_ShotLooks)
			end if
		end if
	end if
end if
"""
    return v4_probe_sounds(body, ["Hurt", "Menu Back", "Release", "Lose Rings"]) if os.environ.get(
        "NOSWAP_SHOT_PROBE") else body


def homing_update_body(i, s, ticks, count):
    """A homing shot's own update (object: the shot; shot_update_body's for motion "homing": Cream's Cheese). Seeking
    (value1 0, its search on: value43 1): the nearest live target on screen the enemies reported since its last update
    (tools/shots_v4.py NoSwap_ShotSeek: value44 its distance, px, SEEK_NONE none; value45 / 46 where it is) is steered
    at: per axis a target speed of 1/4 of the gap, at most seek_speed, reached at seek_accel per frame. None: straight
    on (plus her forward speed along, as a boomerang's way out); seek_frames of those in a row (value12 counts): it
    turns back. A hit (an enemy's shot loop marked it spent: state not LIVE) turns it back too; coming back (value1 1)
    it's out of the shots' group (no more hits) and flies as a boomerang does (boomerang_update_body's return), caught
    within catch px of her. Gone (caught, too old, offscreen): the cooldown starts then. No terrain. Drawn facing the
    way it flies. (The DLL's HomingUpdate, NoSwapS3K.cpp; Sonic CD's: shots_v3.homing_body.)"""
    import shots_v4
    smax, sacc, rmax, racc = s["seek_speed"], s["seek_accel"], s["return_speed"], s["return_accel"]
    catch, none, cool = s["catch"] << 16, shots_v4.SEEK_NONE, shot_cooldown_name(i)

    def clamp(var, lim, ind):
        return (f"{ind}if {var} > {lim}\n{ind}\t{var} = {lim}\n{ind}end if\n"
                f"{ind}if {var} < -{lim}\n{ind}\t{var} = -{lim}\n{ind}end if\n")

    def steer(axis, target, div, top, acc, dy=0, ind="\t\t"):
        off = "" if not dy else f"{ind}temp0 {'+=' if dy > 0 else '-='} {abs(dy) << 16}\n"
        return (f"{ind}temp0 = {target} // {axis}: the gap, /{div}, at most {top:#x}, reached at {acc:#x} a frame\n{off}"
                f"{ind}temp0 -= object.{axis}pos\n{ind}temp0 /= {div}\n" + clamp("temp0", top, ind)
                + f"{ind}temp0 -= object.{axis}vel\n" + clamp("temp0", acc, ind)
                + f"{ind}object.{axis}vel += temp0\n{ind}object.{axis}pos += object.{axis}vel\n")

    back = f"""object.value1 = 1 // coming back: no more hits (out of the shots' group), its search off
object.value43 = 0
object.groupID = TypeName[Tails Object] // (its speed kept: it swings round)
"""
    ind = lambda text, n: "".join("\t" * n + l + "\n" for l in text.rstrip("\n").split("\n"))
    body = f"""if object.value1 == 0 // seeking (tools/abilities.py homing_update_body)
	if object.state != {shots_v4.LIVE} // it hit something (an enemy's shot loop marked it spent): back to her
		object.state = {shots_v4.LIVE}
{ind(back, 2)}	end if
end if
object.value0++ // its age
if object.value0 > {s['lifetime']}
	object.value1 = 2
end if
if object.value1 == 0
	if object.value44 < {none} // a target (the nearest the enemies reported): steer at it
		object.value12 = 0
{steer("x", "object.value45", 4, smax, sacc)}{steer("y", "object.value46", 4, smax, sacc)}	else // none: straight on (her forward speed along), then back
		object.value12++
		temp0 = object[0].xvel
		if object.xvel > 0
			if temp0 < 0
				temp0 = 0
			end if
		else
			if temp0 > 0
				temp0 = 0
			end if
		end if
		temp0 += object.xvel
		object.xpos += temp0
		object.ypos += object.yvel
		if object.value12 >= {s['seek_frames']}
{ind(back, 3)}		end if
	end if
	object.value44 = {none} // (the next search)
else
	if object.value1 == 1 // coming back, homing on her hand
{steer("x", "object[0].xpos", 8, rmax, racc, ind=chr(9) * 2)}		object.xpos += object[0].xvel // (plus her own velocity: running doesn't outpace it)
{steer("y", "object[0].ypos", 8, rmax, racc, s["y"], chr(9) * 2)}		object.ypos += object[0].yvel
		temp0 = object[0].xpos // within catch px of her hand: caught
		temp0 -= object.xpos
		if temp0 < 0
			FlipSign(temp0)
		end if
		temp1 = object[0].ypos
{"" if not s["y"] else chr(9) * 2 + f"temp1 {'+=' if s['y'] > 0 else '-='} {abs(s['y']) << 16}" + chr(10)}		temp1 -= object.ypos
		if temp1 < 0
			FlipSign(temp1)
		end if
		if temp0 < {catch}
			if temp1 < {catch}
				object.value1 = 2
			end if
		end if
	end if
end if
if object.outOfBounds == true
	object.value1 = 2
end if
if object.value1 == 2 // gone (caught, too old or offscreen): the next throw after the cooldown
	{cool} = {s['cooldown']}
	object.value43 = 0
	object.type = TypeName[Blank Object]
else
	if object.xvel > 0x4000 // drawn facing the way it flies
		object.direction = FACING_RIGHT
	end if
	if object.xvel < -0x4000
		object.direction = FACING_LEFT
	end if
	object.animationTimer++
	if object.animationTimer >= {ticks * count}
		object.animationTimer = 0
	end if
	object.frame = object.animationTimer
	object.frame /= {ticks}
	CallFunction(NoSwap_ShotLooks)
end if
"""
    return v4_probe_sounds(body, ["Release"]) if os.environ.get("NOSWAP_SHOT_PROBE") else body


def v4_probe_sounds(body, ends=None):
    """NOSWAP_SHOT_PROBE=1 (a diagnostic build): each way the shot ends plays its own sound, and its first update the
    Charge sound. Spent: Hurt; lifetime: Menu Back; wall: Skidding; offscreen: Lose Rings (a boomerang: `ends`, its
    caught one Release)."""
    if ends is None:
        ends = ["Hurt", "Menu Back", "Skidding", "Lose Rings"]  # (the Blank Object lines, in order)
        if body.count("object.type = TypeName[Blank Object]") == 5:  # (straight: its floor / ceiling, before offscreen)
            ends.insert(3, "Skidding")
    sounds = iter(ends)
    out = []
    for line in body.split("\n"):
        out.append(line)
        if line.strip() == "object.type = TypeName[Blank Object]":
            out.append(line.replace("object.type = TypeName[Blank Object]",
                                    f"PlaySfx(SfxName[{next(sounds)}], false) // [probe]"))
        elif line.strip() == "object.value0++ // its age":
            ind = line[:len(line) - len(line.lstrip())]
            out += [f"{ind}if object.value0 == 1 // [probe] its first update", f"{ind}\tPlaySfx(SfxName[Charge], false)",
                    f"{ind}end if"]
    return "\n".join(out)


def shot_looks(i):
    """What the enemies' shot loops read of it, as of a player: jumping (so it attacks), on the ground (so monitors
    break), not a sidekick, player 1's badnik chain (the score BadnikBreak gives is player 1's), and its hitbox (a second
    shot's, "shot2", its own: told by its frame, as in shot_update_body)."""
    if swap_shots(i, "v4"):  # (John's sub-weapons: each entry's own box, a burning one's flames theirs)
        def looks_of(s, base, burn):
            flight = one_shot_looks(i, s)
            if burn is None:
                return flight
            flames = one_shot_looks(i, dict(s, art=s["burn"]["art"]))
            ind = lambda b: "".join(f"\t{l}\n" if l else "\n" for l in b.rstrip("\n").split("\n"))
            return f"if object.frame >= {burn} // (its flames)\n" + ind(flames) + "else\n" + ind(flight) + "end if\n"
        return swap_dispatch(i, looks_of)
    looks = one_shot_looks(i, shot(i, "v4"))
    if not shot2(i, "v4"):
        return looks
    import shots_v4
    ind = lambda b: "".join(f"\t{l}\n" if l else "\n" for l in b.rstrip("\n").split("\n"))
    return (f"if object.frame >= {shots_v4.ROW2_FRAME} // the second shot (\"shot2\")\n"
            + ind(one_shot_looks(i, shot2(i, "v4"))) + "else\n" + ind(looks) + "end if\n")


def one_shot_looks(i, s):
    r = s["radius"]
    art = s.get("art", {})
    boxes = art.get("hitboxes", [art.get("hitbox", [-r, -r, r, r])])
    for left, top, right, bottom in boxes:
        if (left, right) != (top, bottom) or left != -right:
            # (two of the games' scripts, S2's Masher and Coconuts, alias value38-41 as left, right, top, bottom instead of
            # top, bottom, left, right: only a box the same both ways reads right in both)
            sys.exit(f"shot: extra {i}'s hitbox {[left, top, right, bottom]} must be square round its centre (Sonic 1/2)")
    left, top, right, bottom = boxes[0]
    per_frame = ""
    if "hitboxes" in art:  # a box per frame (build_s3k_shot.py "hitboxes"): the one of the frame it shows
        if shot2(i, "v4") or s.get("cycle") or len(boxes) != shot_frame_count(s, "v4"):
            sys.exit(f"shot: extra {i}: \"hitboxes\" needs one box per Sonic 1/2 frame, and no second or cycle shot")
        base = shot_frame_base(i)
        per_frame = "".join(f"if object.frame == {base + k} // (its box shrinks with its art: \"hitboxes\")\n"
                            f"\tobject.value38 = {t}\n\tobject.value39 = {b}\n\tobject.value40 = {l}\n"
                            f"\tobject.value41 = {rr}\nend if\n" for k, (l, t, rr, b) in enumerate(boxes) if k)
    return f"""object.animation = ANI_JUMPING
object.gravity = GRAVITY_GROUND
object.value16 = false // isSidekick
object.value19 = object[0].value19 // badnikBonus
object.value38 = {top} // hitbox top, bottom, left, right
object.value39 = {bottom}
if object.direction == FACING_RIGHT
	object.value40 = {left}
	object.value41 = {right}
else
	object.value40 = {-right}
	object.value41 = {-left}
end if
""" + per_frame


def shot_update_function():
    nukes = [i for i in ABILITIES if v4_melee(i) and nuke(i)]  # (the Screen Nuke's object: melee_nuke)
    psycho = [i for i in with_ability("psycho_grab") if not shot(i, "v4")]  # (Psychokinesis' thrower: tools/psycho_grab.py)
    flights = [i for i in with_ability("free_flight") if not shot(i, "v4")]  # (NiGHTS' Paraloop hits: tools/free_flight.py)
    quakes = [i for i in with_ability("pot_magic") if not shot(i, "v4")]  # (Gilius' Earthquake: tools/pot_magic.py)
    ids = [i for i in ABILITIES if shot(i, "v4") or i in nukes or i in psycho or i in flights or i in quakes]
    pg = __import__("psycho_grab")
    ff = __import__("free_flight")
    looks = switch_by_extra({i: nuke_looks(i) if i in nukes else pg.looks(i) if i in psycho
                             else ff.hit_looks(i) if i in flights
                             else __import__("pot_magic").v4_looks(i) if i in quakes else shot_looks(i) for i in ids})
    body = switch_by_extra({i: nuke_update_body(i) if i in nukes
                            else one_shot_update_body(i, pg.thrown_shot(i), 0) if i in psycho
                            else ff.hit_update_body(i) if i in flights
                            else __import__("pot_magic").v4_update(i) if i in quakes
                            else __import__("ninjutsu").v4_update_dispatch(i, shot_update_body(i))  # (Joe's blasts)
                            for i in ids})
    return (nuke_tables() + ("// Shot: its looks to the enemies (object: the shot; tools/abilities.py shot_looks)\n"
             "public function NoSwap_ShotLooks\n" + looks + "end function\n\n\n" if ids else "")
            + "// Shot: the shot's own update (object: the shot), from TailsObject.txt (tools/shots_v4.py). An extra without\n"
            "// a shot never makes one: this removes any\n"
            "public function NoSwap_ShotUpdate\n"
            + ("" if ids else "\tobject.type = TypeName[Blank Object]\n") + body + "end function\n\n\n")


def aim_start(s):
    """An aimed shot (shot "aim"), Sonic 1/2: the d-pad as Y is pressed picks its direction (temp5: x, -1 left / 1
    right; temp6: y, -1 up / 1 down; down only in the air: on the ground it's crouching), nothing held: the way he
    faces. Holding left or right turns him that way first when he's standing or in the air. temp2 / temp3: where it
    starts, x px out along the aim from y px below his centre."""
    step = s["x"] << 16
    down = ("""				else
					if player.down == true
						if player.gravity == GRAVITY_AIR // (on the ground, down is crouching)
							temp6 = 1
						end if
					end if
""" if s.get("aim_down", True) else "")  # ("aim_down" false: down never aims, 5 directions in the air too)
    return f"""				temp5 = 0 // the aim (tools/abilities.py aim_start): x -1 left / 1 right, y -1 up / 1 down
				temp6 = 0
				if player.left == true
					temp5 = -1
				end if
				if player.right == true
					temp5 = 1
				end if
				if player.up == true
					temp6 = -1
{down}				end if
				if temp5 == 0
					if temp6 == 0 // nothing held: the way he faces
						temp5 = 1
						if player.direction == FACING_LEFT
							temp5 = -1
						end if
					end if
				end if
				if temp5 != 0 // holding a side: he turns to it first, standing or in the air
					temp4 = player.speed
					if temp4 < 0
						FlipSign(temp4)
					end if
					if player.gravity == GRAVITY_AIR
						temp4 = 0
					end if
					if temp4 < 0x10000
						if temp5 < 0
							player.direction = FACING_LEFT
						else
							player.direction = FACING_RIGHT
						end if
					end if
				end if
				temp2 = temp5
				temp2 *= {step}
				temp2 += player.xpos
				temp3 = temp6
				temp3 *= {step}
				temp3 += player.ypos
				temp3 += {s['y'] << 16}
"""


def aim_velocity(s):
    """An aimed shot's velocity (aim_start's temp5 / temp6): speed along an axis, shot_diag per axis on a diagonal;
    his own speed that way is added to x, so he doesn't run into it."""
    return f"""					temp4 = {s['speed']} // its speed per axis (tools/abilities.py aim_velocity)
					if temp5 != 0
						if temp6 != 0 // a diagonal: the same speed overall
							temp4 = {shot_diag(s)}
						end if
					end if
					temp7 = player.xvel // his own speed along its x (so he doesn't run into it)
					temp7 *= temp5
					if temp7 < 0
						temp7 = 0
					end if
					temp7 += temp4
					temp7 *= temp5
					object[arrayPos0].xvel = temp7
					temp7 = temp4
					temp7 *= temp6
					object[arrayPos0].yvel = temp7
"""


UP_POSE = 256  # a throw pose's count after an up throw is offset by this (NoSwap_shotPose: pose + UP_POSE .. UP_POSE + 1)


def shot_up_pose(i, s, ground, air):
    """The pose frame after an up throw (shot "up" "pose_frame", default the last), checked against both pose slots."""
    k = s["up"].get("pose_frame", ground)
    if not 0 <= k <= min(ground, air) or s.get("pose", 0) >= UP_POSE:
        sys.exit(f"shot: extra {i}: up pose_frame {k} isn't a frame of both throw slots (0-{min(ground, air)}), "
                 f"or its pose is {UP_POSE}+ frames")
    return k


def shot_ground_start(s):
    """Sonic 1/2: thrown standing on the ground, the shot starts at shot "ground"'s x / y instead (Flicky's drop: a
    little toss from his middle rather than from under his feet)."""
    g = s.get("ground", {})
    if "x" not in g and "y" not in g:
        return ""
    return f"""				if player.gravity == GRAVITY_GROUND // (on the ground: shot "ground"'s start)
					temp2 = {g.get('x', s['x']) << 16}
					if player.direction == FACING_LEFT
						FlipSign(temp2)
					end if
					temp2 += player.xpos
					temp3 = player.ypos
					temp3 += {g.get('y', s['y']) << 16}
				end if
"""


def shot_ground_vy(s):
    g = s.get("ground", {})
    if "start_vy" not in g:
        return ""
    return f"""					if player.gravity == GRAVITY_GROUND // (on the ground: shot "ground"'s toss)
						object[arrayPos0].yvel = {g['start_vy']}
					end if
"""


def shot_cycle(s, base=0):
    """A "cycle" shot: each throw is the next frame of its art (NoSwap_shotNext), held for its life (object.value12,
    a tail value no player code reads). An "aim_frames" one: its aim's frame (aim_start's temp5 / temp6: 0 level,
    1 forward-up, 2 up, 3 forward-down, 4 down), held, drawn facing the way it flies."""
    if s.get("aim_frames"):
        import shots_v4
        return """					temp4 = 0 // (aim_frames: its aim's frame)
					if temp6 != 0
						temp4 = 3
						if temp6 < 0
							temp4 = 1
						end if
						if temp5 == 0
							temp4++
						end if
					end if
""" + (f"""					temp4 += {base} // (its frames are shots_v4's big boxes)
""" if base else "") + (f"""					if temp4 >= {base + shots_v4.FRAMES} // (past the strip's first row: art "two_rows", its second row)
						temp4 += {shots_v4.ROW2_FRAME - shots_v4.FRAMES - base}
					end if
""" if shot_frame_count(s, "v4") > shots_v4.FRAMES else "") + """					object[arrayPos0].value12 = temp4
					object[arrayPos0].frame = temp4
					if temp5 < 0 // (drawn the way it flies)
						object[arrayPos0].direction = FACING_LEFT
					end if
					if temp5 > 0
						object[arrayPos0].direction = FACING_RIGHT
					end if
"""
    if not s.get("cycle"):
        return ""
    count = shot_frame_count(s, "v4")
    return f"""					object[arrayPos0].value12 = NoSwap_shotNext // (cycle: this throw's frame)
					object[arrayPos0].frame = NoSwap_shotNext
					NoSwap_shotNext++
					if NoSwap_shotNext >= {count}
						NoSwap_shotNext = 0
					end if
"""


def shot_up_speed(s):
    """Sonic 1/2: the shot's own forward speed added to his (temp4), the up throw's with up held (shot "up"), or shot
    "ground"'s standing on the ground."""
    up = s.get("up", {})
    g = s.get("ground", {})
    if "speed" in g and "speed" not in up:
        return f"""					temp5 = {s['speed']}
					if player.gravity == GRAVITY_GROUND // (on the ground: shot "ground"'s speed)
						temp5 = {g['speed']}
					end if
					temp4 += temp5
"""
    if "speed" not in up:
        return f"\t\t\t\t\ttemp4 += {s['speed']}\n"
    return f"""					temp5 = {s['speed']}
					if player.up == true // up held: the up throw's own speed (shot "up")
						temp5 = {up['speed']}
					end if
					temp4 += temp5
"""


def shot_up_vy(s):
    up = s.get("up", {})
    if "start_vy" not in up or s["motion"] != "bounce":
        return ""
    return f"""					if player.up == true // up held: thrown higher (shot "up")
						object[arrayPos0].yvel = {up['start_vy']}
					end if
"""


def shot_up_pose_set(up_pose, pose, depth):
    """After an up throw the pose's count is offset by UP_POSE (so the pose shows the up throw's frame)."""
    if up_pose is None:
        return ""
    t = "\t" * depth
    value = pose + UP_POSE if pose > 0 else pose - UP_POSE
    return f"{t}if player.up == true // (the up throw's pose)\n{t}\tNoSwap_shotPose = {value}\n{t}end if\n"


def shot_up_pose_show(up_pose, sign):
    if up_pose is None:
        return ""
    test = f"NoSwap_shotPose > {UP_POSE}" if sign > 0 else f"NoSwap_shotPose < -{UP_POSE}"
    return f"\t\tif {test} // after an up throw: its own pose frame\n\t\t\tplayer.frame = {up_pose}\n\t\tend if\n"


def shot_up_pose_end(up_pose, sign):
    if up_pose is None:
        return ""
    return f"\t\tif NoSwap_shotPose == {sign * UP_POSE}\n\t\t\tNoSwap_shotPose = 0\n\t\tend if\n"


def shot_aim_pose(i, out, pose):
    """Shot "aim_pose" (Ray Poward's run-and-gun): the pose shows its aim's frame of the pose slots (0 level, 1 forward-up,
    2 up, 3 forward-down, 4 down; aim_start's temp5 / temp6), not the last: NoSwap_shotPose = +/-(frames left + UP_POSE *
    that frame), as the up throw's offset (check_shot: no "up" with it)."""
    sets = [f"\t\t\t\t\t\t\tNoSwap_shotPose = {pose}\n", f"\t\t\t\t\t\tNoSwap_shotPose = -{pose} // (in the air)\n"]
    if any(out.count(x) != 1 for x in sets):
        sys.exit(f"shot: extra {i}: \"aim_pose\": the pose's code isn't the one it changes")
    k = f"""					temp7 = 0 // (shot "aim_pose": its aim's pose frame, 0 level, 1 forward-up, 2 up, 3 forward-down, 4 down)
					if temp6 != 0
						temp7 = 3
						if temp6 < 0
							temp7 = 1
						end if
						if temp5 == 0
							temp7++
						end if
					end if
					temp7 *= {UP_POSE}
					temp7 += {pose}
"""
    at = out.index("\t\t\t\t\tif player.gravity == GRAVITY_GROUND\n\t\t\t\t\t\ttemp4 = player.speed\n")
    out = out[:at] + k + out[at:]
    out = out.replace(sets[0], "\t\t\t\t\t\t\tNoSwap_shotPose = temp7\n")
    out = out.replace(sets[1], "\t\t\t\t\t\tFlipSign(temp7) // (in the air)\n\t\t\t\t\t\tNoSwap_shotPose = temp7\n")
    shows = [("\t\tplayer.animation = ANI_NOSWAP_MELEE\n\t\tplayer.prevAnimation = ANI_NOSWAP_MELEE\n\t\tplayer.frame = ",
              "\t\tNoSwap_shotPose--\n", "", "\t\tif NoSwap_shotPose == 0\n\t\t\tplayer.animation = ANI_STOPPED\n"),
             ("\t\tplayer.animation = ANI_NOSWAP_MELEE_AIR\n\t\tplayer.prevAnimation = ANI_NOSWAP_MELEE_AIR\n\t\tplayer.frame = ",
              "\t\tNoSwap_shotPose++\n", "\t\tFlipSign(temp2)\n", "\t\tif NoSwap_shotPose == 0\n\t\t\tplayer.animation = ANI_JUMPING\n")]
    for frame, step, flip, end in shows:
        a = out.index(frame)
        b = out.index("\n", a + len(frame))
        out = out[:a] + frame + "temp2 // (shot \"aim_pose\": its aim's frame)\n" + out[b + 1:]
        out = out.replace(frame, "\t\ttemp2 = NoSwap_shotPose\n" + flip + f"\t\ttemp2 /= {UP_POSE}\n" + frame, 1)
        if out.count(step + end) != 1:
            sys.exit(f"shot: extra {i}: \"aim_pose\": the pose's countdown isn't the one it changes")
        out = out.replace(step + end, step + "\t\ttemp2 = NoSwap_shotPose // (its frames left: the offset aside)\n" + flip
                          + f"\t\ttemp2 %= {UP_POSE}\n\t\tif temp2 == 0\n\t\t\tNoSwap_shotPose = 0\n\t\tend if\n" + end)
    return out


POSE_PREV = 512  # shot "pose_always", in the air: NoSwap_shotPose = -(frames left + POSE_PREV * the animation it replaced)


def shot_pose_always_set(pose):
    """Shot "pose_always" (Big's cast): the throw pose shows whatever he's doing. On the ground at any speed (he keeps
    moving: the pose replaces the walk / run frames), except rolling (the roll goes on, no pose); in the air in place of
    whatever shows (the jump ball too: he's no attack then), which comes back when the pose ends: NoSwap_shotPose =
    -(frames left + POSE_PREV * that animation; shot_pose_always_show keeps it up to date)."""
    return f"""					if player.gravity == GRAVITY_GROUND
						if player.state != Player_State_Roll // (rolling: no pose, the roll goes on)
							NoSwap_shotPose = {pose}
						end if
					else
						temp4 = 0
						if NoSwap_shotPose < 0 // (a pose still showing: what it replaced)
							temp4 = NoSwap_shotPose
							FlipSign(temp4)
							temp4 /= {POSE_PREV}
						end if
						if player.animation != ANI_NOSWAP_MELEE_AIR
							temp4 = player.animation
						end if
						temp4 *= {POSE_PREV}
						temp4 += {pose}
						FlipSign(temp4)
						NoSwap_shotPose = temp4
					end if
"""


def shot_pose_always_show(ground, air):
    """Shot "pose_always": the pose's frames (see shot_pose_always_set). On the ground the game picks his animation
    each frame and this puts the pose over it; off a ledge it ends in the fall pose. In the air it goes over anything
    (a move's pose, a spring's) until its frames run out, a hit or landing; the last animation anything else gave him
    comes back after it."""
    return f"""if NoSwap_shotPose > 0 // the throw pose on the ground (shot "pose_always": at any speed; not rolling)
	temp1 = false
	if player.gravity == GRAVITY_GROUND
		if player.animation != ANI_HURT
			temp1 = true
		end if
		if player.state == Player_State_Roll
			temp1 = false
		end if
	end if
	if temp1 == true
		player.animation = ANI_NOSWAP_MELEE
		player.prevAnimation = ANI_NOSWAP_MELEE
		player.frame = {ground}
		player.animationTimer = 0
		NoSwap_shotPose--
		if NoSwap_shotPose == 0
			player.animation = ANI_STOPPED
			if player.speed != 0
				player.animation = ANI_WALKING
			end if
		end if
	else
		NoSwap_shotPose = 0
		if player.animation == ANI_NOSWAP_MELEE // (off a ledge: the fall pose)
			player.animation = ANI_WALKING
		end if
	end if
end if
if NoSwap_shotPose < 0 // the throw pose in the air (shot "pose_always": over whatever shows)
	temp1 = false
	if player.gravity == GRAVITY_AIR
		if player.animation != ANI_HURT
			temp1 = true
		end if
	end if
	if temp1 == true
		temp0 = NoSwap_shotPose
		FlipSign(temp0)
		temp1 = temp0
		temp1 %= {POSE_PREV} // frames left
		temp0 /= {POSE_PREV} // what it replaced
		if player.animation != ANI_NOSWAP_MELEE_AIR // (something else gave him an animation: that comes back after)
			temp0 = player.animation
		end if
		temp1--
		if temp1 == 0 // the pose is over: what it replaced (the jump ball, a fall, a spring...)
			player.animation = temp0
			NoSwap_shotPose = 0
		else
			player.animation = ANI_NOSWAP_MELEE_AIR
			player.prevAnimation = ANI_NOSWAP_MELEE_AIR
			player.frame = {air}
			player.animationTimer = 0
			temp0 *= {POSE_PREV}
			temp0 += temp1
			FlipSign(temp0)
			NoSwap_shotPose = temp0
		end if
	else
		NoSwap_shotPose = 0
	end if
end if
"""


def shot_cooldown_name(i):
    """The value an extra's Sonic 1/2 shot cooldown lives in: NoSwap_shotCooldown, or NoSwap_pogoShotCooldown for an extra
    with the pogo (NoSwap_pogo shares NoSwap_shotCooldown's value: PACKED_VALUES; Fang's cork gun)."""
    return "NoSwap_pogoShotCooldown" if has(i, "pogo") else "NoSwap_shotCooldown"


def swap_shot_after(i):
    """In NoSwap_AfterUpdate, for an extra with swap shots (monitor_swap's "swap_shots": John's sub-weapons): the shared
    cooldown counted down once, then each entry's throw (shot_after's, variant), only while it's the current one
    (monitor_swap.VALUE)."""
    import monitor_swap
    cool = shot_cooldown_name(i)
    out = f"if {cool} > 0 // Shot (tools/abilities.py swap_shot_after: the current swap shot's)\n\t{cool}--\nend if\n"
    for k, (s, base, burn, end) in enumerate(swap_layout(i)):
        block = shot_after(i, variant=(k, s, base, end))
        out += (f"if {monitor_swap.VALUE} == {k} // monitor_swap entry {k}: {monitor_entry(i, k)}\n"
                + "".join(f"\t{l}\n" if l else "\n" for l in block.rstrip("\n").split("\n")) + "end if\n")
    return out


def shot_after(i, which=1, variant=None):
    """In NoSwap_AfterUpdate: Y throws a shot (NoSwap_TrySuper, in the air states earlier this frame, turned Y into the
    transformation when it could: the state isn't one of SHOT_STATES then), at most max_alive out and cooldown frames
    apart; then the throw pose (the melee slots' last frames) for `pose` frames, standing or in the air. which 2: the
    second shot ("shot2", down + Y; after the first's block, sharing its cooldown; its shots told by their frames).
    variant: (k, shot, base, end): one of the extra's swap shots (swap_shot_after: John's sub-weapons), its frames base..end
    (swap_layout), counted by them; its cooldown counted down by swap_shot_after."""
    import shots_v4
    if variant is None and which == 1 and swap_shots(i, "v4"):
        return swap_shot_after(i)
    s = variant[1] if variant else check_shot(i) if which == 1 else check_shot2(i)
    two = bool(shot2(i, "v4"))  # (a second shot: each counts only its own, and Y with down held is the second's)
    aim = bool(s.get("aim"))
    up = s.get("up")  # the throw with up held: its own speed / start_vy, and its pose's frame (shot_up)
    down = s.get("input") == "down"  # (down + Y throws; Y alone is the melee: Mecha's spike ball)
    up_in = s.get("input") == "up"  # (up + Y throws; Y alone is the melee: John's sub-weapons)
    states = "".join(f"\t\tCheckEqual(player.state, {st})\n\t\ttemp0 |= checkResult\n"
                     for st in SHOT_STATES + (["Player_State_LookUp"] if aim or up or up_in else [])  # (aimed / up: standing)
                     + (["Player_State_Crouch"] if down else [])  # (down + Y: crouching)
                     + (["Player_State_Fly"] if s.get("from_flight") else []))  # (Tails' flight: Flicky's drop)
    if down:
        states += "\t\tif player.down == false // (shot \"input\" \"down\": Y alone is the melee)\n\t\t\ttemp0 = false\n\t\tend if\n"
    elif two and shot2(i, "v4").get("input") == "down":
        states += "\t\tif player.down == true // (down + Y throws the second shot, \"shot2\")\n\t\t\ttemp0 = false\n\t\tend if\n"
    if up_in:  # (up + Y; in the air up with a side is the melee's up-forward whip: melee_up)
        states += """		if player.up == false // (shot "input" "up": Y alone is the melee)
			temp0 = false
		end if
		if player.gravity == GRAVITY_AIR // (up and a side in the air: the up-forward whip, melee_up)
			if player.left == true
				temp0 = false
			end if
			if player.right == true
				temp0 = false
			end if
		end if
"""
    if has(i, "sink"):  # (down + Y on the ground is the Shadow Sink's, even while it cools down)
        states += "\t\tif player.gravity == GRAVITY_GROUND // (down + Y on the ground: the sink's, sink_after)\n" \
                  "\t\t\tif player.down == true\n\t\t\t\ttemp0 = false\n\t\t\tend if\n\t\tend if\n"
    if s.get("rings"):  # (swap shot "rings": each throw costs that many; fewer: no throw)
        states += f"\t\tif player.rings < {s['rings']} // (a throw costs {s['rings']} ring(s): \"rings are hearts\")\n" \
                  "\t\t\ttemp0 = false\n\t\tend if\n"
    base = variant[2] if variant else shot_frame_base(i, which)  # (Sonic 1/2's big boxes: shots_v4)
    ground = shot_pose_frame(i, "Sonic2u", ANI_MELEE, "melee_reach")
    air = shot_pose_frame(i, "Sonic2u", ANI_MELEE_AIR, "melee_air_reach")
    pose = s.get("pose", 0) if ground >= 0 else 0
    up_pose = shot_up_pose(i, s, ground, air) if up and pose else None
    own = (f"""				if object[arrayPos0].frame {'>=' if which == 2 else '<'} {shots_v4.ROW2_FRAME} // (only this shot's: its frames)
					temp1++
				end if
""" if two else "\t\t\t\t\ttemp1++\n")
    if two:
        own = "".join("\t" + l + "\n" for l in own.rstrip("\n").split("\n"))
    if variant:  # (a swap shot: only this entry's, by its frames)
        own = f"""					if object[arrayPos0].frame >= {variant[2]} // (only this swap shot's: its frames)
						if object[arrayPos0].frame < {variant[3]}
							temp1++
						end if
					end if
"""
    cool = shot_cooldown_name(i)
    out = ("" if which == 2 or variant else f"""if {cool} > 0 // Shot (tools/abilities.py shot_after)
	{cool}--
end if
""") + f"""if keyPress[1].buttonY != false
	if {cool} == 0
		temp0 = false
{states}		if player.animation == ANI_HURT
			temp0 = false
		end if
		if temp0 == true
			temp1 = 0 // shots out
			foreach (TypeName[Tails Object], arrayPos0, ALL_ENTITIES)
				if object[arrayPos0].state == {shots_v4.LIVE}
{own}				end if
			next
			if temp1 < {s['max_alive']}
{aim_start(s) if aim else f'''				temp2 = {s['x'] << 16}
				if player.direction == FACING_LEFT
					FlipSign(temp2)
				end if
				temp2 += player.xpos
				temp3 = player.ypos
				temp3 += {s['y'] << 16}
{shot_ground_start(s)}'''}				CreateTempObject(TypeName[Tails Object], player.collisionPlane, temp2, temp3)
				arrayPos0 = object[tempObjectPos].entityPos
				if object[arrayPos0].type == TypeName[Tails Object] // (made)
					object[arrayPos0].groupID = {shots_v4.GROUP} // the shots' group: the enemies' shot loops (tools/shots_v4.py)
					object[arrayPos0].state = {shots_v4.LIVE}
					object[arrayPos0].priority = PRIORITY_ACTIVE
					object[arrayPos0].interaction = true
					object[arrayPos0].drawOrder = player.sortedDrawOrder // (as the game's own dust: player.drawOrder isn't a layer the engine draws, StageSetup lists the players itself)
					object[arrayPos0].direction = player.direction
{aim_velocity(s) if aim else f'''					temp4 = player.xvel // its speed, plus his own forward (so he doesn't run into it)
					if player.direction == FACING_LEFT
						FlipSign(temp4)
					end if
					if temp4 < 0
						temp4 = 0
					end if
{shot_up_speed(s)}					if player.direction == FACING_LEFT
						FlipSign(temp4)
					end if
					object[arrayPos0].xvel = temp4
					object[arrayPos0].yvel = {s['start_vy'] if s['motion'] in ('bounce', 'drop', 'dip') else 0}
{shot_up_vy(s)}{shot_ground_vy(s)}''' if s['motion'] not in ('boomerang', 'homing') else f'''					temp4 = {s['speed']} // a boomerang: its own speed (its update adds hers, live)
					if player.direction == FACING_LEFT
						FlipSign(temp4)
					end if
					object[arrayPos0].xvel = temp4
					object[arrayPos0].yvel = 0
					object[arrayPos0].value1 = 0 // flying out
''' + ('' if s['motion'] != 'homing' else f'''					object[arrayPos0].value12 = 0 // a homing shot: no target yet, its search on (homing_update_body)
					object[arrayPos0].value43 = 1
					object[arrayPos0].value44 = {shots_v4.SEEK_NONE}
''')}					object[arrayPos0].value0 = 0
					object[arrayPos0].frame = {base}
					object[arrayPos0].animationTimer = 0
{shot_cycle(s, base)}					{cool} = {s['cooldown']}
					PlaySfx(SfxName[{s['sound']}], false)
""" + (f"""					player.rings -= {s['rings']} // (swap shot "rings": its cost)
""" if s.get("rings") else "")
    if s.get("carry") is False:  # (shot "carry" false: its own speed alone, his forward speed not added: Jet's Tornado Trap)
        carry = ("\t\t\t\t\ttemp4 = player.xvel // its speed, plus his own forward (so he doesn't run into it)\n"
                 "\t\t\t\t\tif player.direction == FACING_LEFT\n\t\t\t\t\t\tFlipSign(temp4)\n\t\t\t\t\tend if\n"
                 "\t\t\t\t\tif temp4 < 0\n\t\t\t\t\t\ttemp4 = 0\n\t\t\t\t\tend if\n")
        if aim or s["motion"] in ("boomerang", "homing") or out.count(carry) != 1:
            sys.exit(f"shot: extra {i}: \"carry\" false is for an unaimed bounce / straight / drop / dip shot")
        out = out.replace(carry, "\t\t\t\t\ttemp4 = 0 // (shot \"carry\" false: its own speed alone)\n")
    if s.get("both_ways"):  # (shot "both_ways": its mirror image thrown with it, the other way: check_both_ways)
        start = out.index(f"\t\t\t\ttemp2 = {s['x'] << 16}\n")
        block = out[start:out.index(f"\t\t\t\t\t{cool} = {s['cooldown']}\n", start)]
        facing = "\t\t\t\t\tobject[arrayPos0].direction = player.direction\n"
        if block.count(facing) != 1 or block.count("player.direction == FACING_LEFT") != 2:
            sys.exit(f"shot: extra {i}: \"both_ways\": the throw's code isn't the one it mirrors")
        mirror = block.replace("player.direction == FACING_LEFT", "player.direction == FACING_RIGHT").replace(
            facing, "\t\t\t\t\tobject[arrayPos0].direction = FACING_LEFT // (the other way)\n"
                    "\t\t\t\t\tif player.direction == FACING_LEFT\n"
                    "\t\t\t\t\t\tobject[arrayPos0].direction = FACING_RIGHT\n\t\t\t\t\tend if\n")
        out += "\t\t\t\t\t// shot \"both_ways\": the second, his other side, the other way\n" + \
            "".join("\t" + l + "\n" for l in mirror.rstrip("\n").split("\n")) + "\t\t\t\t\tend if\n"
    if pose and s.get("pose_always"):
        out += shot_pose_always_set(pose)
    elif pose:
        out += f"""					if player.gravity == GRAVITY_GROUND
						temp4 = player.speed
						if temp4 < 0
							FlipSign(temp4)
						end if
						if temp4 < 0x10000 // standing: the throw pose
							NoSwap_shotPose = {pose}
{shot_up_pose_set(up_pose, pose, 7)}						end if
					else
						NoSwap_shotPose = -{pose} // (in the air)
{shot_up_pose_set(up_pose, -pose, 6)}					end if
"""
    out += "\t\t\t\tend if\n\t\t\tend if\n\t\tend if\n\tend if\nend if\n"
    if s.get("autofire"):  # (shot "autofire": Y held throws one every cooldown frames)
        press = "if keyPress[1].buttonY != false\n"
        if out.count(press) != 1:
            sys.exit(f"shot: extra {i}: \"autofire\": the throw's Y test isn't there once")
        out = out.replace(press, "if keyDown[1].buttonY != false // (shot \"autofire\": held, one every cooldown frames)\n")
    if pose and s.get("pose_always"):
        out += shot_pose_always_show(ground, air)
    elif pose:
        out += f"""if NoSwap_shotPose > 0 // the throw pose, standing: the throw's last frame
	temp0 = player.speed
	if temp0 < 0
		FlipSign(temp0)
	end if
	temp1 = false
	if player.gravity == GRAVITY_GROUND
		if temp0 < 0x10000
			if player.animation != ANI_HURT
				temp1 = true
			end if
		end if
	end if
	if temp1 == true
		player.animation = ANI_NOSWAP_MELEE
		player.prevAnimation = ANI_NOSWAP_MELEE
		player.frame = {ground}
{shot_up_pose_show(up_pose, 1)}		player.animationTimer = 0
		NoSwap_shotPose--
{shot_up_pose_end(up_pose, 1)}		if NoSwap_shotPose == 0
			player.animation = ANI_STOPPED
		end if
	else
		NoSwap_shotPose = 0
	end if
end if
if NoSwap_shotPose < 0 // the throw pose in the air (while he's in his jump)
	temp1 = false
	if player.gravity == GRAVITY_AIR
		if player.animation == ANI_JUMPING
			temp1 = true
		end if
		if player.animation == ANI_NOSWAP_MELEE_AIR
			temp1 = true
		end if
	end if
	if temp1 == true
		player.animation = ANI_NOSWAP_MELEE_AIR
		player.prevAnimation = ANI_NOSWAP_MELEE_AIR
		player.frame = {air}
{shot_up_pose_show(up_pose, -1)}		player.animationTimer = 0
		NoSwap_shotPose++
{shot_up_pose_end(up_pose, -1)}		if NoSwap_shotPose == 0
			player.animation = ANI_JUMPING
		end if
	else
		NoSwap_shotPose = 0
	end if
end if
"""
    if pose and s.get("aim_pose"):
        out = shot_aim_pose(i, out, pose)
    if which == 2 and s.get("input") == "charge":
        out = charge_trigger(i, s, out, cool)
    return out


def charge_trigger(i, s, out, cool):
    """shot2 "input" "charge" (Mega Man's Charge Shot): Y held counts NoSwap_busterCharge up (from its first frame; the
    press itself threw the first shot); letting go of a full charge (charge_full frames) throws the second shot, whatever
    the cooldown (with "charge_wait" the charge holds a frame short of full while the cooldown runs: full charges are
    at least the cooldown apart, Omega's); letting go sooner, or a hit, just ends the charge. Its pose is the first shot's, set here and shown by
    the first shot's code (so it's counted down once a frame). Its flash: charge_flash_draw."""
    head = f"if keyPress[1].buttonY != false\n\tif {cool} == 0\n"
    if out.count(head) != 1 or "temp7" in out:
        sys.exit(f"shot2: extra {i}: the charge shot's trigger isn't the throw's code it replaces")
    show = out.find("if NoSwap_shotPose > 0 // the throw pose, standing")
    if show >= 0:  # (the first shot's code shows the pose)
        out = out[:show]
    wait = (f"\tif {cool} > 0 // (\"charge_wait\": not full until the cooldown is over)\n"
            f"\t\tif NoSwap_busterCharge >= {s['charge_full']}\n\t\t\tNoSwap_busterCharge = {s['charge_full'] - 1}\n"
            "\t\tend if\n\tend if\n") if s.get("charge_wait") else ""
    prelude = f"""temp7 = false // Charge Shot (tools/abilities.py charge_trigger): Y held charges; let go of a full charge, it fires
if keyDown[1].buttonY != false
	if NoSwap_busterCharge < 0x7FFF
		NoSwap_busterCharge++
	end if
{wait}else
	if NoSwap_busterCharge >= {s['charge_full']}
		temp7 = true
	end if
	NoSwap_busterCharge = 0
end if
if player.animation == ANI_HURT
	NoSwap_busterCharge = 0
	temp7 = false
end if
"""
    return prelude + out.replace(head, "if temp7 == true // (a full charge let go of)\n\tif temp7 == true\n")


def charge_flash_draw(t):
    """A charge shot's flash in Sonic 1/2 (a runtime palette effect, the art untouched): while Y has been held charge_start
    frames or more, his own colours are drawn in the sheet's charge palettes: charge1 every other 4 frames until the
    charge is full, then charge2a, charge2b and his own in turn, 2 frames each. Only for his own drawing: the colours
    are written into palette banks 0 and 1 right before DrawObjectAnimation and put back from the Super glow's copy
    (banks 6 and 7, NoSwap_SuperGlow: every extra without Sonic's own Super palette keeps it each frame) right after.
    Only temp0-temp3 are used (spin_lean_draw's temp6 / temp7 live across the draw)."""
    ids = charge_shots()
    if not ids:
        return t
    fns = ""
    pick = ""
    for i in ids:
        if next(e for e in EXTRAS if e["id"] == i)["super"]:
            sys.exit(f"shot2: extra {i}: the charge flash puts his colours back from the Super glow's copy (\"super\" False)")
        s = shot2(i, "v4")
        pals = charge_palettes(i)
        slots = sorted({k for p in pals for k in p})
        lo, n = slots[0], slots[-1] - slots[0] + 1
        sets = ""
        for k, pal in enumerate(pals):
            sets += f"\tif temp0 == {k}\n" + "".join(
                f"\t\tSetPaletteEntry(0, {slot}, {rgb:#08x})\n\t\tSetPaletteEntry(1, {slot}, {rgb:#08x})\n"
                for slot, rgb in sorted(pal.items())) + "\tend if\n"
        fns += f"""// [NoSwap] {ALIAS_OF[i]}'s Charge Shot flash (tools/abilities.py charge_flash_draw): before his draw, the phase's colours
public function NoSwap_ChargeFlash{i}
	temp0 = -1
	if NoSwap_busterCharge >= {s['charge_start']}
		if NoSwap_busterCharge < {s['charge_full']}
			temp1 = NoSwap_busterCharge
			temp1 >>= 2
			temp1 &= 1
			if temp1 == 1
				temp0 = 0
			end if
		else
			temp1 = NoSwap_busterCharge
			temp1 >>= 1
			temp1 %= 3
			if temp1 < 2
				temp0 = temp1
				temp0++
			end if
		end if
	end if
{sets}end function


// after his draw: his colours back (the Super glow's copy)
public function NoSwap_ChargeUnflash{i}
	if NoSwap_busterCharge >= {s['charge_start']}
		CopyPalette(6, {lo}, 0, {lo}, {n})
		CopyPalette(7, {lo}, 1, {lo}, {n})
	end if
end function


"""
        pick += (f"\tif stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] the Charge Shot's flash\n"
                 f"\t\tCallFunction(NoSwap_ChargeFlash{i})\n\tend if\n")
    t = patch(t, "public function Player_HandleAmyHitbox\n", fns + "public function Player_HandleAmyHitbox\n",
              "charge flash functions")
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    draw = t[start:end]
    if draw.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("charge flash: expected 1 DrawObjectAnimation in ObjectDraw")
    after = pick.replace("NoSwap_ChargeFlash", "NoSwap_ChargeUnflash").replace("the Charge Shot's flash", "his colours back")
    draw = draw.replace("\tDrawObjectAnimation()\n", pick + "\tDrawObjectAnimation()\n" + after)
    return t[:start] + draw + t[end:]


# ---------------------------------------------------------------- Super, for every extra
# Origins' Sonic 1 and 2 transform on Y in mid-air (keyPress[1].buttonY, checked in each base character's jump
# ability: all 7 emeralds, specialStage.emeralds == 0x7F, 50+ rings, not already Super, no act finish). An extra's own
# jump ability (and its Y moves) replaced that check, so NoSwap_TrySuper does it for every extra, first thing in the
# air states (NoSwap_AirAbilities, which runs before the jump ability and the Y moves): with the conditions met, Y
# transforms (Player_TryTransform: the game's Super Spark trail, music, Super physics rows); otherwise Y and jump do
# the extra's own moves. Its checks are the game's own for Sonic (the jump ability's: in the jump ball, the jump
# ability unused).
#
# The look: an extra keeps its own sprites, and its colours glow (extras.py "super": True, Metal Sonic, keeps Sonic's
# Super palette instead). While Super, NoSwap_SuperGlow blends its own palette slots (NoSwap_PaletteSlot on) and
# Sonic's blues (2-5, which some extras' art shares) toward SUPER_GLOW_TO, by an amount that pulses on Super Sonic's
# own timer (Player_superBlendClr: 0-24 fading in, 24-60 cycling, back to 0 fading out). Both the normal and the
# underwater bank (0 and 1) glow. Their colours are copied into banks 6 and 7 (which neither game uses) every frame
# while not Super, glowed from there, and copied back exactly when the fade-out ends; the stage start rewrites them
# anyway (extra_startup, the water setups). The water flash (bank 2, Labyrinth's lightning) doesn't glow.
SUPER_GLOW_TO = 0xFFF0A0  # a pale gold
# the glow (of 256) per step of Player_superBlendClr (steps of 4): fading in over steps 0-6, then pulsing on 6-15
SUPER_GLOW_AMOUNT = [0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 160, 144, 128, 112]
SUPER_GLOW_SLOTS = (2, 6)  # Sonic's blues (first, past the last), glowed too: some extras' art uses them


def super_glow_colour():
    """NoSwap_GlowColour: temp3 (0xRRGGBB) moved toward SUPER_GLOW_TO by temp1 (of 256), one channel at a time.
    Each channel's change is added to the colour in place (it stays within 0-255), so only temp4 and temp7 are used."""
    out = ["public function NoSwap_GlowColour", "\ttemp7 = temp3"]
    for shift in (16, 8, 0):
        target = (SUPER_GLOW_TO >> shift) & 0xFF
        out += ["\ttemp4 = temp3"] + ([f"\ttemp4 >>= {shift}"] if shift else []) + [
            "\ttemp4 &= 0xFF", "\tFlipSign(temp4)", f"\ttemp4 += {target}", "\ttemp4 *= temp1", "\ttemp4 >>= 8"] \
            + ([f"\ttemp4 <<= {shift}"] if shift else []) + ["\ttemp7 += temp4"]
    return "\n".join(out + ["\ttemp3 = temp7", "end function", "", "", ""])


def super_functions():
    lo, hi = SUPER_GLOW_SLOTS
    return f"""// [NoSwap] Super for every extra (tools/abilities.py, "Super, for every extra"): Y in mid-air transforms first when
// the game would let Sonic (his jump ability's checks); otherwise the extra's own moves have Y and jump
public function NoSwap_TrySuper
	if keyPress[1].buttonY != false
		temp0 = false
		if player.yvel >= player.jumpCap // the jump ability's own conditions: a jump, in the jump ball, the ability unused
			if player.animation == ANI_JUMPING
				if player.jumpAbilityState == 1
					temp0 = true
				end if
			end if
		end if
		CheckEqual(specialStage.emeralds, 0x7F) // all 7 emeralds (a bit each)
		temp0 &= checkResult
		CheckGreater(player.rings, 49)
		temp0 &= checkResult
		CheckNotEqual(Player_superState, SUPERSTATE_SUPER)
		temp0 &= checkResult
		CheckNotEqual(object[SLOT_ACTFINISH].type, TypeName[Act Finish])
		temp0 &= checkResult
{super_down()}		if temp0 == true
			currentPlayer = player.entityPos
			CallFunction(Player_TryTransform) // (the state is Player_State_Transform now: no Y move this frame)
			CallNativeFunction4(NotifyCallback, NOTIFY_STATS_CHARA_ACTION, 1, 0, 0) // as Sonic's does
		end if
	end if
end function


// Super glow: how far toward the glow colour, per step of Player_superBlendClr (steps of 4)
private table NoSwap_SuperGlowAmount
{table_rows(SUPER_GLOW_AMOUNT).rstrip(chr(10))}
end table


{super_glow_colour()}// Palette slots temp0 up to (not including) temp2, in banks 0 and 1. temp1: 0 copy them into banks 6 and 7, 1 copy them
// back, 2 glow them from the copy (by NoSwap_SuperGlowAmount for Player_superBlendClr)
public function NoSwap_GlowSlots
	temp3 = temp2
	temp3 -= temp0
	if temp1 == 0
		CopyPalette(0, temp0, 6, temp0, temp3)
		CopyPalette(1, temp0, 7, temp0, temp3)
	end if
	if temp1 == 1
		CopyPalette(6, temp0, 0, temp0, temp3)
		CopyPalette(7, temp0, 1, temp0, temp3)
	end if
	if temp1 == 2
		temp1 = Player_superBlendClr
		temp1 >>= 2
		GetTableValue(temp1, temp1, NoSwap_SuperGlowAmount)
		while temp0 < temp2
			GetPaletteEntry(6, temp0, temp3)
			CallFunction(NoSwap_GlowColour)
			SetPaletteEntry(0, temp0, temp3)
			GetPaletteEntry(7, temp0, temp3)
			CallFunction(NoSwap_GlowColour)
			SetPaletteEntry(1, temp0, temp3)
			temp0++
		loop
	end if
end function


// Super for extras: their colours (Sonic's blues {lo}-{hi - 1}, and their own slots) glow while Super, on Super Sonic's timer
// (Player_HandleSuperPalette_Sonic's). Not Super: a copy of them is kept to glow from and to put back exactly.
// Called every frame from Player_HandleSuperForm (every extra but those with Sonic's own Super palette)
public function NoSwap_SuperGlow
	temp5 = 0 // not Super: keep a copy
	if Player_superState != SUPERSTATE_NONE
		temp5 = 2 // glow
		if Player_superState == SUPERSTATE_SUPER
			Player_superBlendTimer++
			if Player_superBlendTimer >= 4
				Player_superBlendTimer = 0
				Player_superBlendClr += 4
				if Player_superBlendClr >= 64
					Player_superBlendClr = 24
				end if
			end if
		else // fading out
			Player_superBlendTimer++
			if Player_superBlendTimer >= 8
				Player_superBlendTimer = 0
				Player_superBlendClr -= 4
				if Player_superBlendClr <= 0
					Player_superBlendClr = 0
					Player_superState = SUPERSTATE_NONE
					temp5 = 1 // over: the colours back, exactly as they were
				end if
				if Player_superBlendClr >= 24
					Player_superBlendClr = 24
				end if
			end if
		end if
	end if
	temp0 = {lo}
	temp2 = {hi}
	temp1 = temp5
	CallFunction(NoSwap_GlowSlots)
	GetTableValue(temp0, stage.playerListPos, NoSwap_PaletteAt) // its own slots: how many
	temp2 = stage.playerListPos
	temp2++
	GetTableValue(temp2, temp2, NoSwap_PaletteAt)
	temp2 -= temp0
	if temp2 > 0
		GetTableValue(temp0, stage.playerListPos, NoSwap_PaletteSlot)
		temp2 += temp0
		temp1 = temp5
		CallFunction(NoSwap_GlowSlots)
	end if
end function


"""


def super_glow_hook(t):
    """Player_HandleSuperForm: every extra but those with Sonic's own Super palette (extras.py "super": the game
    scripts' builders put only those in its Sonic case) runs NoSwap_SuperGlow every frame."""
    own = [e for e in EXTRAS if e["super"]]
    ind = "\t\t"
    opens = "".join(f"{ind}{chr(9) * k}if stage.playerListPos != {e['alias']} // (Sonic's own Super palette, below)\n"
                    for k, e in enumerate(own))
    closes = "".join(f"{ind}{chr(9) * k}end if\n" for k in reversed(range(len(own))))
    call = f"{ind}{chr(9) * len(own)}CallFunction(NoSwap_SuperGlow)\n"
    return patch(t, "public function Player_HandleSuperForm\n",
                 "public function Player_HandleSuperForm\n"
                 "\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] Super for extras: their colours glow (NoSwap_SuperGlow)\n"
                 + opens + call + closes + "\tend if\n\n", "super glow hook")


SHARED_JUMPS = {"umbrella", "aim_dash"}  # jump abilities that are one function for every extra with them


def functions(t):
    """The ability functions, for the player script `t` (for which roll states it has)."""
    roll_states = [s for s in ROLL_STATES + ["Player_State_CorkscrewRoll"] if f"public function {s}\n" in t]
    out = ["// [NoSwap] Ability modules for extra characters (generated by tools/abilities.py)\n", super_functions()]
    # Modules several extras have: one function each, reading the extra's numbers from tables (extra_table)
    if any(v4_melee(i) for i in ABILITIES):
        out.append(melee_tables() + "\n" + melee_function())
    out.append(shot_update_function())
    if with_ability("umbrella"):
        out.append(umbrella_tables() + "\n" + umbrella_function() + umbrella_air_function())
    if with_ability("aim_dash"):
        out.append(aim_dash_tables() + "\n" + aim_dash_functions())
    out.append(falling_hover_function())
    for i in with_ability("star_grab"):  # (Ristar: tools/star_grab.py)
        out.append(__import__("star_grab").v4_functions(i))
    for i in with_ability("head_throw"):  # (Headdy: tools/head_throw.py)
        out.append(__import__("head_throw").v4_functions(i))
    for i in with_ability("anchor_throw"):  # (Marine: tools/anchor_throw.py)
        out.append(__import__("anchor_throw").v4_functions(i))
    for i in with_ability("free_swim"):  # (Ecco: tools/free_swim.py)
        out.append(__import__("free_swim").v4_functions(i))
    for i in with_ability("free_flight"):  # (NiGHTS: tools/free_flight.py)
        out.append(__import__("free_flight").v4_functions(i))
    for i in ABILITIES:
        if has(i, "ear_grapple"):
            tips = ABILITIES[i]["grapple_tip"]
            for axis, k in (("X", 0), ("Y", 1)):
                out.append(f"private table NoSwap_GrappleTip{axis}{i}\n\t"
                           + ", ".join(str(tp[k]) for tp in tips) + "\nend table\n\n\n")
            out.append(ear_grapple_function(i))
        if has(i, "jet_dash"):
            out.append(jet_dash_function(i))
        if has(i, "rocket_ride"):
            out.append(rocket_ride_function(i))
        if has(i, "pogo"):
            out.append(pogo_function(i))
        if has(i, "chaos_control"):
            out.append(chaos_control_function(i))
        if has(i, "screw_kick"):
            out.append(screw_kick_function(i))
        if has(i, "hammer_drop"):
            out.append(hammer_drop_function(i))
        if has(i, "ray_glide"):
            out.append(ray_glide_function(i))
        if has(i, "spirit_flight"):
            out.append(spirit_flight_function(i))
        if has(i, "rocket_burst"):
            out.append(rocket_burst_function(i))
        if has(i, "triple_jump"):
            out.append(triple_jump_function(i))
        if has(i, "double_jump"):
            out.append(double_jump_function(i))
        if has(i, "wall_cling"):
            out.append(wall_beside_function(i))
        if has(i, "thunder_zip"):
            out.append(thunder_zip_function(i))
        if has(i, "extreme_gear"):
            out.append(extreme_gear_function(i))
        if has(i, "puddle_slide"):
            out.append(puddle_slide_function(i))
        if has(i, "ground_slide"):
            out.append(ground_slide_function(i))
        if has(i, "sink"):
            out.append(sink_function(i))
        if has(i, "phase_warp"):
            out.append(phase_warp_function(i))
        if cycle(i):
            out.append(cycle_function(i))

    out.append(slide_running_function())
    air_of = {"jet_dash": jet_dash_air, "umbrella": umbrella_air, "chaos_control": chaos_control_air,
              "aim_dash": aim_dash_air, "hammer_drop": hammer_drop_air, "ray_glide": ray_glide_air,
              "screw_kick": screw_kick_air, "rocket_ride": rocket_ride_air, "ear_grapple": ear_grapple_air,
              "spirit_flight": spirit_flight_air, "wall_cling": wall_cling_air, "thunder_zip": thunder_zip_air,
              "extreme_gear": extreme_gear_air, "puddle_slide": puddle_slide_air, "phase_warp": phase_warp_air,
              "rocket_burst": rocket_burst_air}
    air = {i: air_of[a](i) for i in ABILITIES for a in ABILITIES[i]["abilities"] if a in air_of}
    for i in with_ability("star_grab"):  # (Ristar: tools/star_grab.py)
        air[i] = __import__("star_grab").v4_air(i)
    for i in with_ability("anchor_throw"):  # (Marine: tools/anchor_throw.py)
        air[i] = air.get(i, "") + __import__("anchor_throw").v4_air(i)
    for i in with_ability("free_swim"):  # (Ecco: tools/free_swim.py; his velocity, after the air state's gravity)
        air[i] = air.get(i, "") + __import__("free_swim").v4_air(i)
    for i in with_ability("free_flight"):  # (NiGHTS: tools/free_flight.py; his velocity, after the air state's gravity)
        air[i] = air.get(i, "") + __import__("free_flight").v4_air(i)
    for i in cycle_extras():  # (several jump abilities: each one's code, while it's the active one)
        air[i] = "".join(cycle_gate(i, a, air_of[a](i)) for a in ABILITIES[i]["abilities"] if a in air_of)
    for i in with_ability("water_swim"):  # (before the jump ability's own air code)
        if cycle(i):
            sys.exit(f"water_swim: extra {i} has an ability_cycle")
        air[i] = water_swim_air(i) + air.get(i, "")
    for i in sparks():  # (the charge's Shine Spark: its flight)
        air[i] = air.get(i, "") + spark_air(i)
    out.append("// Runs every frame in the air, before the jump ability check. Super first: Y transforms when it can\n"
               "public function NoSwap_AirAbilities\n\tCallFunction(NoSwap_TrySuper)\n" + switch_by_extra(air)
               + "end function\n\n\n")

    starts = {i: triple_jump_start(i) for i in with_ability("triple_jump")}
    if starts:
        out.append("// Runs in Player_Action_Jump once a jump is sure: a jump that's part of a chain (temp1: its strength)\n"
                   "public function NoSwap_JumpStart\n" + switch_by_extra(starts) + "end function\n\n\n")

    after = {}
    for i in ABILITIES:
        body = (puddle_slide_after(i) if has(i, "puddle_slide") else "") \
            + (puddle_slide_after(i, ground=True) if has(i, "ground_slide") else "") \
            + (no_stomp_slide_after(i) if has(i, "ground_slide") and has(i, "no_stomp") else "") \
            + (phase_warp_after(i) if has(i, "phase_warp") else "") \
            + (pogo_after(i) if has(i, "pogo") else "") \
            + (triple_jump_after(i, roll_states) if has(i, "triple_jump") else "") \
            + (spirit_flight_after(i) if has(i, "spirit_flight") else "") \
            + (rocket_burst_after(i) if has(i, "rocket_burst") else "") \
            + (extreme_gear_after(i) if has(i, "extreme_gear") else "") \
            + (sink_after(i) if has(i, "sink") else "") \
            + (melee_after(i) if v4_melee(i) else "") + (shot_after(i) if shot(i, "v4") and not slam_shot(i) else "") \
            + (shot_after(i, 2) if shot2(i, "v4") else "") \
            + (hammer_drop_after(i) if has(i, "hammer_drop") else "") + (ray_glide_after(i) if has(i, "ray_glide") else "") \
            + (aim_dash_y_after(i) if ABILITIES[i].get("aim_dash_y") else "") \
            + (cycle_gate(i, "screw_kick", screw_kick_after(i)) if has(i, "screw_kick") else "") \
            + (rocket_ride_after(i) if has(i, "rocket_ride") else "") \
            + (grapple_y_after(i) if ABILITIES[i].get("grapple_y") else "") \
            + (ear_grapple_after(i) if has(i, "ear_grapple") else "") \
            + (cycle_gate(i, "double_jump", double_jump_after(i)) if has(i, "double_jump") else "") \
            + (wall_cling_after(i) if has(i, "wall_cling") else "") \
            + (power_surge_after(i) if has(i, "power_surge") else "") \
            + (charge_after(i) if has(i, "charge") else "") \
            + (spark_after(i) if i in sparks() else "") \
            + (spin_after(i) if has(i, "spin_attack") else "") \
            + (high_kick_after(i) if has(i, "high_kick") else "") \
            + (cycle_frame(i) if cycle(i) else "")
        if body:
            after[i] = body
    for i in with_ability("star_grab"):  # (Ristar: tools/star_grab.py)
        after[i] = after.get(i, "") + __import__("star_grab").v4_after(i)
    for i in with_ability("head_throw"):  # (Headdy: tools/head_throw.py)
        after[i] = after.get(i, "") + __import__("head_throw").v4_after(i)
    for i in with_ability("anchor_throw"):  # (Marine: tools/anchor_throw.py)
        after[i] = after.get(i, "") + __import__("anchor_throw").v4_after(i)
    for i in with_ability("water_walk"):  # (Marine: tools/water_walk.py; last, after every move has moved her)
        after[i] = after.get(i, "") + __import__("water_walk").v4_after(i, t)
    for i in with_ability("monitor_swap"):  # (John's sub-weapons: tools/monitor_swap.py, before his throw reads it)
        after[i] = __import__("monitor_swap").v4_after(i) + after.get(i, "")
    for i in with_ability("psycho_grab"):  # (Silver: tools/psycho_grab.py, before the melee: Y is its first)
        after[i] = __import__("psycho_grab").v4_after(i) + after.get(i, "")
    for i in with_ability("treasure_sense"):  # (Rouge: tools/treasure_sense.py; after her moves: the pause holds her)
        after[i] = after.get(i, "") + __import__("treasure_sense").v4_after(i)
    for i in with_ability("free_swim"):  # (Ecco: tools/free_swim.py)
        after[i] = after.get(i, "") + __import__("free_swim").v4_after(i)
    for i in with_ability("free_flight"):  # (NiGHTS: tools/free_flight.py)
        after[i] = after.get(i, "") + __import__("free_flight").v4_after(i)
    for i in with_ability("ninjutsu"):  # (Joe Musashi: tools/ninjutsu.py; first: up + Y is the cast's, not the shuriken's;
        # the pose last, after his moves)
        after[i] = __import__("ninjutsu").v4_after(i) + after.get(i, "") + __import__("ninjutsu").v4_after_pose(i)
    for i in with_ability("pot_magic"):  # (Gilius: tools/pot_magic.py; first: up + Y is the cast's, not the chop's;
        # the pose last, after his moves)
        after[i] = __import__("pot_magic").v4_after(i) + after.get(i, "") + __import__("pot_magic").v4_after_pose(i)
    out.append("// Runs at the end of every update, after the player has moved\n"
               "public function NoSwap_AfterUpdate\n" + switch_by_extra(after) + "end function\n\n\n")
    before = {i: spin_before(i) for i in with_ability("spin_attack")}
    if before:  # (only in a build with such an extra: apply_player hooks it in)
        out.append("// Runs at the start of every update, before the state (tools/abilities.py spin_before)\n"
                   "public function NoSwap_BeforeUpdate\n" + switch_by_extra(before) + "end function\n\n\n")
    return "".join(out)


def shell_spikes_function():
    """Mania Plus's Player_CheckMightyUnspin for spikes: curled up, the shell takes the hit."""
    ids = with_ability("spike_shell")
    if not ids:
        return ""
    # no temp variables: the spike scripts calling Player_SpikeHit use them
    cases = "".join(f"\tif stage.playerListPos == {ALIAS_OF[i]}\n\t\tNoSwap_shellSafe = 2\n\tend if\n" for i in ids)
    return f"""// [NoSwap] spike_shell: spikes don't hurt a curled-up Mighty (Mania Plus); he's knocked up and back
public function NoSwap_ShellSpikes
	NoSwap_shellSafe = false
	if options.attractMode == false // demos and credits: as Sonic
{cases}	end if
	if NoSwap_shellSafe == 2 // an extra with the shell
		NoSwap_shellSafe = false
		if player[currentPlayer].blinkTimer == 0
			if player[currentPlayer].invincibleTimer == 0
				if player[currentPlayer].animation == ANI_JUMPING
					NoSwap_shellSafe = true
				end if
				if player[currentPlayer].animation == ANI_SPINDASH
					NoSwap_shellSafe = true
				end if
				if player[currentPlayer].animation == ANI_NOSWAP_ATTACK
					NoSwap_shellSafe = true
				end if
			end if
		end if
	end if
	if NoSwap_shellSafe == true
		player[currentPlayer].yvel = -0x48000
		player[currentPlayer].xvel = -0x28000
		if player[currentPlayer].direction == FACING_LEFT
			player[currentPlayer].xvel = 0x28000
		end if
		if player[currentPlayer].gravityStrength == 0x1000 // underwater
			player[currentPlayer].xvel >>= 1
			player[currentPlayer].yvel = -0x24000
		end if
		player[currentPlayer].speed = player[currentPlayer].xvel
		player[currentPlayer].gravity = GRAVITY_AIR
		player[currentPlayer].state = Player_State_Air
		player[currentPlayer].animation = ANI_BOUNCING
		player[currentPlayer].blinkTimer = 121
		player[currentPlayer].noswapAbility = -1
		PlaySfx(SfxName[Bubble Bounce], false)
	end if
end function


"""


def physics_table(t, extra_id, mult=None, name=None, what=None):
    """A copy of Sonic's physics table scaled by the extra's multipliers (or `mult`, as table `name`)."""
    m = re.search(r"private table Player_SonicPhysicsTable\n(.*?)end table\n", t, re.S)
    if not m:
        sys.exit("physics: Player_SonicPhysicsTable not found")
    mult = mult or ABILITIES[extra_id]["physics"]
    rows = []
    for line in m.group(1).strip("\n").split("\n"):
        values, _, comment = line.partition("//")
        nums = [int(v.strip(), 16) if not v.strip().startswith("-") else -int(v.strip()[1:], 16)
                for v in values.split(",")]
        scaled = [int(n * mult.get(PHYSICS_COLUMNS[i], 1.0)) for i, n in enumerate(nums)]
        rows.append("\t" + ", ".join(("-" if n < 0 else "") + f"0x{abs(n):X}" for n in scaled)
                    + (f" //{comment}" if comment else ""))
    return (f"// [NoSwap] Extra {extra_id - 6}'s {what or 'physics'}: Sonic's table scaled by {mult}\n"
            f"private table {name or f'Player_NoSwapPhysicsTable{extra_id}'}\n" + "\n".join(rows) + "\nend table\n\n")


def surge_physics(i):
    """power_surge's multipliers, on top of the extra's own physics."""
    own, surge = ABILITIES[i].get("physics", {}) if has(i, "physics") else {}, ABILITIES[i]["surge_physics"]
    return {k: round(own.get(k, 1.0) * surge.get(k, 1.0), 4) for k in PHYSICS_COLUMNS
            if k in own or k in surge}


def surge_physics_case(t, extra):
    """power_surge: the extra's case in Player_UpdatePhysicsState picks the surge table while a surge lasts (its own
    table, or Sonic's, otherwise)."""
    i = extra["id"]
    t = patch(t, "private table Player_TailsPhysicsTable\n",
              physics_table(t, i, surge_physics(i), f"Player_NoSwapSurgeTable{i}", "Power Surge physics")
              + "private table Player_TailsPhysicsTable\n", "surge physics table")
    fn = t.index("public function Player_UpdatePhysicsState")
    sw = t.index("switch stage.playerListPos", fn)
    end = t.index("end switch", sw)
    body = t[sw:end]
    own = f"Player_NoSwapPhysicsTable{i}" if has(i, "physics") else "Player_SonicPhysicsTable"
    case = (f"case {extra['alias']} // [NoSwap] own physics (ability module)\n\t\ttemp0 = {own}\n\t\tbreak\n")
    if has(i, "physics"):
        if case not in body:
            sys.exit(f"power_surge: no physics case for {extra['alias']}")
    else:
        body = re.sub(rf"\n\t*case {extra['alias']} // \[NoSwap\] placeholder: behaves like Sonic", "", body, count=1)
        body = body.replace("case PLAYER_SONIC_A", case + "\n\tcase PLAYER_SONIC_A", 1)
    body = body.replace(case, case.replace("\t\tbreak\n", f"\t\tif {surge_active(i)} // Power Surge: overcharged\n"
                                           f"\t\t\ttemp0 = Player_NoSwapSurgeTable{i}\n\t\tend if\n\t\tbreak\n"), 1)
    return t[:sw] + body + t[end:]


def surge_in_out(t):
    """power_surge: while a surge lasts, her idle / walk / run show as the Power Surge ones, only while animating and
    drawing (NoSwap_SurgeIn before ProcessAnimation / DrawObjectAnimation, NoSwap_SurgeOut after, as apply_roll
    does): the rest of the game keeps seeing its own animation. The engine keeps a Power Surge animation's frame
    while the game's stays the same (prevAnimation), and a frame past the end of the game's one when the surge ends
    goes back to its loop point at the next ProcessAnimation, before anything is drawn."""
    ids = with_ability("power_surge")
    if not ids:
        return t
    # Plain ifs on the game's animation, not a switch: the ANI_ names are GameConfig global variables in Sonic 1 and 2,
    # and a case needs a constant (a `switch player.animation` here broke the whole compile, reported as "Operand not
    # found: PLAYER_AMY", line 131, in every stage)
    pick = "".join(f"\t\t\tif NoSwap_surgeFrom == {ani}\n\t\t\t\tplayer.animation = {surge}\n\t\t\tend if\n"
                   for ani, surge in [("ANI_STOPPED", "ANI_NOSWAP_SURGE_IDLE"), ("ANI_WAITING", "ANI_NOSWAP_SURGE_IDLE"),
                                      ("ANI_BORED", "ANI_NOSWAP_SURGE_IDLE"), ("ANI_WALKING", "ANI_NOSWAP_SURGE_RUN"),
                                      ("ANI_RUNNING", "ANI_NOSWAP_SURGE_SPRINT"),
                                      ("ANI_PEELOUT", "ANI_NOSWAP_SURGE_SPRINT")])
    cases = "".join(f"\tif stage.playerListPos == {ALIAS_OF[i]}\n\t\tif {surge_active(i)}\n"
                    "\t\t\tNoSwap_surgeFrom = player.animation\n" + pick + "\t\tend if\n\tend if\n" for i in ids)
    functions = (
        "// [NoSwap] power_surge: while a surge lasts, the Power Surge idle / walk / run are shown in place of the game's,\n"
        "// only while animating and drawing (tools/abilities.py surge_in_out); the rest of the game sees its own\n"
        "public function NoSwap_SurgeIn\n"
        "\tNoSwap_surgeFrom = -1\n" + cases +
        "\tif NoSwap_surgeFrom >= 0\n"
        "\t\tif player.animation == NoSwap_surgeFrom // nothing to show in its place\n"
        "\t\t\tNoSwap_surgeFrom = -1\n"
        "\t\telse\n"
        "\t\t\tif player.prevAnimation == NoSwap_surgeFrom // still the same: keep the Power Surge one's frame\n"
        "\t\t\t\tplayer.prevAnimation = player.animation\n"
        "\t\t\tend if\n"
        "\t\tend if\n"
        "\tend if\n"
        "end function\n\n\n"
        "public function NoSwap_SurgeOut\n"
        "\tif NoSwap_surgeFrom >= 0\n"
        "\t\tplayer.animation = NoSwap_surgeFrom\n"
        "\t\tplayer.prevAnimation = NoSwap_surgeFrom\n"
        "\t\tNoSwap_surgeFrom = -1\n"
        "\tend if\n"
        "end function\n\n\n")
    t = patch(t, "public function Player_HandleAmyHitbox\n", functions + "public function Player_HandleAmyHitbox\n",
              "surge functions")
    start = t.index("event ObjectUpdate\n")
    end = t.index("end event\n", start)
    body = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_SurgeIn) // [NoSwap] Power Surge animations\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_SurgeOut)\n"), t[start:end])
    if body.count("CallFunction(NoSwap_SurgeIn)") != 2:
        sys.exit("power_surge: expected 2 ProcessAnimation calls in ObjectUpdate")
    t = t[:start] + body + t[end:]
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    body = t[start:end]
    if body.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("power_surge: expected 1 DrawObjectAnimation in ObjectDraw")
    body = body.replace("\tDrawObjectAnimation()\n", "\tCallFunction(NoSwap_SurgeIn) // [NoSwap] Power Surge animations\n"
                        "\tDrawObjectAnimation()\n\tCallFunction(NoSwap_SurgeOut)\n")
    return t[:start] + body + t[end:]


COPY_HEAD_SLOT, COPY_HEAD_STRIDE = 53, 7  # copy_heads: the sets' first slot and slots a set (CD one on: cd_config.py)
# copy_heads: the game's animations a set has, in its order (Sonic 1/2 names; CD's switch is its slot 46, no air one)
COPY_HEAD_ANIMS = ["ANI_STOPPED", "ANI_WAITING", "ANI_WALKING", "ANI_RUNNING", "ANI_PEELOUT", "ANI_NOSWAP_MELEE",
                   "ANI_NOSWAP_MELEE_AIR"]


def copy_head_extras():
    """Extras with copy heads ("copy_heads": Emerl): a head per ability_cycle move, checked."""
    ids = [i for i in ABILITIES if ABILITIES[i].get("copy_heads")]
    for i in ids:
        if not cycle(i) or has(i, "power_surge"):
            sys.exit(f"copy_heads: extra {i}: needs an ability_cycle (a head set per move) and no power_surge")
    return ids


def copy_head_lines(i, anims, first, move, animation="player.animation", prev="player.prevAnimation"):
    """copy_heads' In / Out bodies for one extra (Sonic 1/2 and CD alike: `anims` the game's animations by place in the
    set, None where the game has none; `move` the active move's value). In: the game's animation, when a set has it,
    becomes the active move's copy (first + stride * move + its place), its frame kept while the game's stays the
    same. Out: back to the game's, worked out from the copy's slot (no value to keep it in; no temp either: the draw
    effects keep theirs across DrawObjectAnimation). The ifs go from the last place down, so an animation just put
    back is never taken for a later place (the game's IDs there are all 5 or more, or the place's own)."""
    n = len(cycle(i))
    top = first + COPY_HEAD_STRIDE * n
    head_in, head_out = [], []
    for k, ani in enumerate(anims):
        if ani is None:
            continue
        head_in += [f"if {prev} == {ani}", f"\t{prev} = {first + k} // (still the same: keep the copy's frame)", "end if",
                    f"if {animation} == {ani}", f"\t{animation} = {first + k}", "end if"]
    for m in range(1, n):
        head_in += [f"if {move} >= {m} // the active move's set", *[
            l for v in (animation, prev) for l in (f"\tif {v} >= {first}", f"\t\tif {v} < {top}",
                                                  f"\t\t\t{v} += {COPY_HEAD_STRIDE}", "\t\tend if", "\tend if")],
                    "end if"]
    head_out = [f"if {animation} >= {first}", f"\tif {animation} < {top}", f"\t\t{animation} -= {first}",
                f"\t\t{animation} %= {COPY_HEAD_STRIDE}"]
    for k in reversed(range(len(anims))):
        if anims[k] is not None and anims[k] != str(k):
            head_out += [f"\t\tif {animation} == {k}", f"\t\t\t{animation} = {anims[k]}", "\t\tend if"]
    head_out += [f"\t\t{prev} = {animation}", "\tend if", "end if"]
    return head_in, head_out


def copy_head_in_out(t):
    """copy_heads in Sonic 1/2: the active move's head set (its idle, stance, walk, run and copy flash: slots
    COPY_HEAD_SLOT on, testmods/emerl/make_configs.py) shown in place of the game's own, only while animating and drawing
    (NoSwap_CopyHeadIn before ProcessAnimation / DrawObjectAnimation, NoSwap_CopyHeadOut after, as surge_in_out): the
    rest of the game keeps seeing its own animation. (ANI_PEELOUT is ANI_RUNNING for extras: not looked at.)"""
    ids = copy_head_extras()
    if not ids:
        return t
    anims = [a if a != "ANI_PEELOUT" else None for a in COPY_HEAD_ANIMS]
    body_in, body_out = "", ""
    for i in ids:
        head_in, head_out = copy_head_lines(i, anims, COPY_HEAD_SLOT, "NoSwap_copyMove")
        gate = f"\tif stage.playerListPos == {ALIAS_OF[i]}\n"
        body_in += gate + "".join(f"\t\t{l}\n" for l in head_in) + "\tend if\n"
        body_out += gate + "".join(f"\t\t{l}\n" for l in head_out) + "\tend if\n"
    functions = ("// [NoSwap] copy_heads: the active move's head set in place of the game's animation, only while animating\n"
                 "// and drawing (tools/abilities.py copy_head_in_out); the rest of the game sees its own\n"
                 "public function NoSwap_CopyHeadIn\n" + body_in + "end function\n\n\n"
                 "public function NoSwap_CopyHeadOut\n" + body_out + "end function\n\n\n")
    t = patch(t, "public function Player_HandleAmyHitbox\n", functions + "public function Player_HandleAmyHitbox\n",
              "copy head functions")
    start = t.index("event ObjectUpdate\n")
    end = t.index("end event\n", start)
    body = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_CopyHeadIn) // [NoSwap] copy heads\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_CopyHeadOut)\n"), t[start:end])
    if body.count("CallFunction(NoSwap_CopyHeadIn)") != 2:
        sys.exit("copy_heads: expected 2 ProcessAnimation calls in ObjectUpdate")
    t = t[:start] + body + t[end:]
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    body = t[start:end]
    if body.count("\tDrawObjectAnimation()\n") != 1:
        sys.exit("copy_heads: expected 1 DrawObjectAnimation in ObjectDraw")
    body = body.replace("\tDrawObjectAnimation()\n", "\tCallFunction(NoSwap_CopyHeadIn) // [NoSwap] copy heads\n"
                        "\tDrawObjectAnimation()\n\tCallFunction(NoSwap_CopyHeadOut)\n")
    return t[:start] + body + t[end:]


def apply_player(t, game):
    """Patch a game's Players/PlayerObject.txt (after the game's own NoSwap build). game: "Sonic1u" or "Sonic2u"."""
    t = patch(t, "private alias object.value16 : player.isSidekick",
              ALIASES.strip("\n") + "\nprivate alias object.value16 : player.isSidekick", "ability aliases")
    values = VALUES.lstrip("\n") + SURGE_SHARED + (SURGE_VALUES if with_ability("power_surge") else "") \
        + (ZIP_VALUES if with_ability("thunder_zip") else "") + (PUDDLE_VALUES if with_ability("puddle_slide") or with_ability("ground_slide") else "") \
        + (SHOT_NEXT_VALUES if cycle_shots() else "") + (CHARGE_VALUES if with_ability("charge") else "") \
        + (SPARK_VALUES if sparks() else "") \
        + (SPIN_VALUES if with_ability("spin_attack") else "") \
        + (HIGH_KICK_VALUES if with_ability("high_kick") else "") + (CYCLE_VALUES if cycle_extras() else "") \
        + (SWIM_VALUES if with_ability("water_swim") else "") + (WARP_VALUES if with_ability("phase_warp") else "") \
        + (SINK_VALUES if with_ability("sink") else "") \
        + (POGO_SHOT_VALUES if any(shot(i, "v4") for i in with_ability("pogo")) else "") \
        + (BUSTER_VALUES if charge_shots() else "") + (WHIP_VALUES if whips() or variants() else "") \
        + (__import__("monitor_swap").V4_VALUES if with_ability("monitor_swap") else "")
    t = patch(t, "public value Player_superState", values + "\npublic value Player_superState", "ability values")
    t = patch(t, "public function Player_HandleAmyHitbox\n",
              functions(t) + shell_spikes_function() + "public function Player_HandleAmyHitbox\n", "ability functions")

    # spike_shell: the spike hit goes to the shell first (every spike calls Player_SpikeHit)
    if with_ability("spike_shell"):
        start = t.index("public function Player_SpikeHit\n")
        end = t.index("end function", start)
        body = t[start:end]
        anchor = "\t\tif player[currentPlayer].invincibleTimer == 0\n"
        if body.count(anchor) != 1 or not body.endswith("\tend if\n"):
            sys.exit("spike_shell: Player_SpikeHit changed")
        body = body.replace(anchor, "\t\tCallFunction(NoSwap_ShellSpikes) // [NoSwap] a curled-up Mighty's shell takes spikes\n"
                                    "\t\tif NoSwap_shellSafe == false\n" + anchor)
        body = body[:-len("\tend if\n")] + "\t\tend if\n\tend if\n"
        t = t[:start] + body + t[end:]

    # fire_immune: Player_FireHit (every fire hazard's hurt: lava, fireballs, flamethrowers) hurts nobody playing such an
    # extra, as a fire shield. Only in a build with one, so the other packages' scripts don't change. (No temp: the
    # function's callers may keep theirs across the call.)
    immune = with_ability("fire_immune")
    if immune:
        head = "public function Player_FireHit\n"
        start = t.index(head)
        end = t.index("end function\n", start)
        body = t[start + len(head):end]
        if not body.startswith("\tif player[currentPlayer].shield != SHIELD_FIRE\n") or not body.endswith("\tend if\n"):
            sys.exit("fire_immune: Player_FireHit changed")
        for i in immune:
            body = "".join("\t" + l if l.strip() else l for l in body.splitlines(keepends=True))
            body = (f"\tif stage.playerListPos != {ALIAS_OF[i]} // [NoSwap] fire_immune: fire never hurts this extra (a fire "
                    "shield's immunity, always)\n" + body + "\tend if\n")
        t = t[:start] + head + body + t[end:]

    # Hammer Drop through badniks: keep falling (1 px per frame slower) instead of bouncing off, as in Mania
    drops = with_ability("hammer_drop")
    if drops:
        checks = "".join(f"\t\t\tif stage.playerListPos == {ALIAS_OF[i]}\n"
                         "\t\t\t\tif player[currentPlayer].animation == ANI_NOSWAP_ATTACK\n"
                         "\t\t\t\t\tNoSwap_plow = true\n\t\t\t\tend if\n\t\t\tend if\n" for i in drops)
        t = patch(t, "\t\t\tif player[currentPlayer].ypos >= object.ypos\n\t\t\t\tplayer[currentPlayer].yvel -= 0x10000\n",
                  "\t\t\tNoSwap_plow = false // [NoSwap] a Hammer Drop plows through (Mania Plus)\n"
                  "\t\t\tif player[currentPlayer].ypos >= object.ypos\n\t\t\t\tNoSwap_plow = true\n\t\t\tend if\n"
                  + checks +
                  "\t\t\tif NoSwap_plow == true\n\t\t\t\tplayer[currentPlayer].yvel -= 0x10000\n", "hammer drop badniks")

    t = bat_glide(t)

    # triple_jump: Player_Action_Jump asks, once the jump is sure, whether it's the next of a chain (a higher jump)
    if with_ability("triple_jump"):
        t = patch(t, "\t\ttemp1 = player.jumpStrength\n\t\ttemp1 += player.gravityStrength\n",
                  "\t\ttemp1 = player.jumpStrength\n\t\ttemp1 += player.gravityStrength\n"
                  "\t\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] a Triple Jump's 2nd and 3rd jumps are higher\n"
                  "\t\t\tif options.attractMode == false // demos and credits: as Sonic\n"
                  "\t\t\t\tCallFunction(NoSwap_JumpStart)\n"
                  "\t\t\tend if\n"
                  "\t\tend if\n", "triple jump start")

    # Every new jump starts fresh
    t = patch_n(t, "player.jumpAbilityState = 1\n",
                "player.jumpAbilityState = 1\n" + "\t\tplayer.noswapAbility = 0 // [NoSwap] ability state per jump\n", "ability reset", 2)
    # Fix the indentation of that inserted line to match each site
    t = re.sub(r"(\n(\t+)player\.jumpAbilityState = 1\n)\t\tplayer\.noswapAbility",
               lambda m: m.group(1) + m.group(2) + "player.noswapAbility", t)

    # Air states: run the ability update every frame for extras, just before the Drop Dash check
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == "CallFunction(Player_HandleDropDash)"]
    if len(hits) != 2:
        sys.exit(f"ability air hook: found {len(hits)} Drop Dash calls (expected 2)")
    for i in reversed(hits):
        at = i - 1  # the enclosing "if player.yvel >= player.jumpCap"
        ind = lines[at][: len(lines[at]) - len(lines[at].lstrip("\t"))]
        lines[at:at] = [f"{ind}if stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] ability moves",
                        f"{ind}\tif options.attractMode == false // demos and credits replay Sonic's inputs: play as Sonic",
                        f"{ind}\t\tCallFunction(NoSwap_AirAbilities)", f"{ind}\tend if", f"{ind}end if"]
    t = "\n".join(lines)

    # Start of the update (spin_attack: whether the game bounced her off something), only in a build with such an extra
    if with_ability("spin_attack"):
        t = patch(t, "event ObjectUpdate\n#platform: USE_ORIGINS\n\tcurrentPlayer = player.entityPos\n#endplatform\n",
                  "event ObjectUpdate\n#platform: USE_ORIGINS\n\tcurrentPlayer = player.entityPos\n#endplatform\n"
                  "\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] ability moves (the start of the update)\n"
                  "\t\tif options.attractMode == false // demos and credits: as Sonic\n"
                  "\t\t\tCallFunction(NoSwap_BeforeUpdate)\n"
                  "\t\tend if\n"
                  "\tend if\n", "ability before-update hook")

    # End of the update (after movement and Amy's hitbox): landings, shots and hitboxes
    t = patch(t, "\tCallFunction(Player_HandleAmyHitbox)\n#endplatform\nend event\n",
              "\tCallFunction(Player_HandleAmyHitbox)\n"
              "\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] ability moves\n"
              "\t\tif options.attractMode == false // demos and credits: as Sonic\n"
              "\t\t\tCallFunction(NoSwap_AfterUpdate)\n"
              "\t\tend if\n"
              "\t\tif player.gravity == GRAVITY_GROUND // the engine only tilts the base characters' sprites\n"
              "\t\t\tplayer.rotation = player.angle\n"
              "\t\t\tplayer.rotation <<= 1\n"
              "\t\tend if\n"
              "\tend if\n"
              "#endplatform\nend event\n", "ability after-update hook")

    # Enemies and bosses: an extra's attack animations count as attacking, like Amy's hammer
    checks = "".join(f"\t\t\tCheckEqual(player[currentPlayer].animation, {a})\n\t\t\ttemp0 |= checkResult\n"
                     for a in ATTACK_ANIMS)
    t = patch_n(t, "\t// Amy's trusty Pico Pico Hammer can bash through anything!\n",
                "\tif stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] an extra's attack moves (Jet Dash, Pogo, Melee)\n"
                "\t\tif player[currentPlayer].isSidekick == false\n"
                + checks + surge_checks("\t\t\t") +
                "\t\tend if\n"
                "\tend if\n\n"
                "\t// Amy's trusty Pico Pico Hammer can bash through anything!\n",
                "ability attack check", 2)

    for extra in EXTRAS:
        i = extra["id"]
        if i not in ABILITIES:
            continue
        if has(i, "spirit_flight"):
            check_spirit_art(extra, game)
        if has(i, "rocket_burst"):
            check_rocket_art(extra, game)
        case = t.index(startup_case(extra))  # the extra's startup case
        line = t.index("= Player_Action_DblJumpSonic", case)
        # Jump ability
        ability = next((f"NoSwap_{name}" + ("" if a in SHARED_JUMPS else str(i)) for a, name in (("jet_dash", "JetDash"), ("rocket_ride", "RocketRide"), ("ear_grapple", "EarGrapple"), ("pogo", "Pogo"),
                        ("umbrella", "Umbrella"), ("chaos_control", "ChaosControl"), ("aim_dash", "AimDash"),
                        ("hammer_drop", "HammerDrop"), ("ray_glide", "RayGlide"), ("spirit_flight", "SpiritFlight"),
                        ("triple_jump", "TripleJump"), ("double_jump", "DoubleJump"), ("thunder_zip", "ThunderZip"),
                        ("extreme_gear", "ExtremeGear"), ("screw_kick", "ScrewKick"), ("puddle_slide", "PuddleSlide"),
                        ("phase_warp", "PhaseWarp"), ("rocket_burst", "RocketBurst"))
                        if has(i, a) and not (a == "aim_dash" and ABILITIES[i].get("aim_dash_y"))
                        and not (a == "screw_kick" and not ABILITIES[i].get("kick_jump"))), None)
        if cycle(i):  # (several: the active one's)
            ability = f"NoSwap_Copycat{i}"
        if ability:
            t = t[:line] + f"= {ability} // [NoSwap] ability module" + t[line + len("= Player_Action_DblJumpSonic"):]
        # Physics: own table and own case in the physics switch
        if has(i, "physics"):
            t = patch(t, "private table Player_TailsPhysicsTable\n",
                      physics_table(t, i) + "private table Player_TailsPhysicsTable\n", "physics table")
            fn = t.index("public function Player_UpdatePhysicsState")
            sw = t.index("switch stage.playerListPos", fn)
            end = t.index("end switch", sw)
            body = t[sw:end]
            body = re.sub(rf"\n\t*case {extra['alias']} // \[NoSwap\] placeholder: behaves like Sonic", "", body, count=1)
            body = body.replace("case PLAYER_SONIC_A",
                                f"case {extra['alias']} // [NoSwap] own physics (ability module)\n"
                                f"\t\ttemp0 = Player_NoSwapPhysicsTable{i}\n\t\tbreak\n\n\tcase PLAYER_SONIC_A", 1)
            t = t[:sw] + body + t[end:]
        if has(i, "power_surge"):
            t = surge_physics_case(t, extra)
    t = super_glow_hook(t)
    return __import__("pot_magic").v4_patch(__import__("voltteccer").v4_patch(__import__("ninjutsu").v4_patch(__import__("free_flight").v4_patch(__import__("free_swim").v4_patch(__import__("treasure_sense").v4_patch(__import__("monitor_swap").v4_patch(__import__("anchor_throw").v4_patch(__import__("head_throw").v4_patch(__import__("star_grab").v4_patch(ear_grapple_patch(spark_glow_draw(charge_flash_draw(spin_lean_draw(float_lean_draw(copy_head_in_out(surge_in_out(apply_no_stomp(apply_ground_slide(spark_no_roll(apply_no_roll(apply_roll(extra_startup(replays_as_sonic(apply_base_characters(t))), game)))))))))))))))), game)), game), game), game), game)  # (free_swim: Ecco, tools/free_swim.py; free_flight: NiGHTS, tools/free_flight.py) (ninjutsu: Joe Musashi, tools/ninjutsu.py) (voltteccer: Pulseman, tools/voltteccer.py) (pot_magic: Gilius, tools/pot_magic.py)


ROLL_STATES = ["Player_State_Roll", "Player_State_TubeRoll"]  # rolling on the ground (in ANI_JUMPING)


def roll_jump_frames(extra, game):
    """Frames in the extra's "Jumping" animation (its built .ani), for the check after a roll."""
    ani = player_ani(extra, game)
    names = [a["name"] for a in ani["anims"]]
    if len(names) <= ANI_ROLL or names[ANI_ROLL] != "Rolling":
        sys.exit(f"{extra['file']}.ani ({game}): extras.py \"roll\" needs a \"Rolling\" animation in slot {ANI_ROLL}")
    return len(ani["anims"][names.index("Jumping")]["frames"])


def check_spirit_art(extra, game):
    """The Spirit Flight picks the transform's frames itself and then lets the orb's loop run: the built slot 41
    has to loop right after the transform (spirit_transform frames)."""
    ani = player_ani(extra, game)
    n = ABILITIES[extra["id"]]["spirit_transform"]
    a = ani["anims"][ANI_ATTACK] if len(ani["anims"]) > ANI_ATTACK else None
    if not a or a["loop"] != n or len(a["frames"]) <= n:
        sys.exit(f"{extra['file']}.ani ({game}): spirit_flight needs slot {ANI_ATTACK} to loop at frame {n}, after the transform")


def apply_roll(t, game):
    """extras.py "roll": rolling on the ground shows the extra's own curl (ANI_NOSWAP_ROLL) instead of its jump
    (Mario's is a fist-up leap). The swap is only for animating and drawing: NoSwap_RollIn switches to the curl
    right before ProcessAnimation / DrawObjectAnimation and NoSwap_RollOut switches back, so everything else
    (enemies, monitors, the camera, landing) keeps seeing ANI_JUMPING. A jump in the air keeps the jump pose."""
    rollers = [e for e in EXTRAS if e["roll"]]
    if not rollers:
        return t
    states = [s for s in ROLL_STATES if f"public function {s}\n" in t]
    checks = "".join(f"\t\t\tCheckEqual(player.state, {s})\n\t\t\ttemp0 |= checkResult\n" for s in states)
    cases = ""
    for e in rollers:
        cases += (f"\tcase {e['alias']}\n"
                  "\t\tif player.animation == ANI_JUMPING\n"
                  "\t\t\ttemp0 = false\n" + checks +
                  "\t\t\tif temp0 == true\n"
                  "\t\t\t\tplayer.animation = ANI_NOSWAP_ROLL\n"
                  "\t\t\t\tif player.prevAnimation == ANI_JUMPING // still rolling: keep the curl's frame\n"
                  "\t\t\t\t\tplayer.prevAnimation = ANI_NOSWAP_ROLL\n"
                  "\t\t\t\t\tplayer.frame = NoSwap_rollFrame\n"
                  "\t\t\t\tend if\n"
                  "\t\t\telse\n"
                  f"\t\t\t\tif player.frame >= {roll_jump_frames(e, game)} // just out of the curl: back to a jump frame\n"
                  "\t\t\t\t\tplayer.frame = 0\n"
                  "\t\t\t\tend if\n"
                  "\t\t\tend if\n"
                  "\t\tend if\n"
                  "\t\tbreak\n")
    functions = (
        "// [NoSwap] extras.py \"roll\": rolling on the ground shows the extra's own curl instead of its jump, only\n"
        "// while animating and drawing (tools/abilities.py apply_roll); the rest of the game sees ANI_JUMPING\n"
        "public function NoSwap_RollIn\n"
        "\tswitch stage.playerListPos\n" + cases + "\tend switch\n"
        "end function\n\n\n"
        "public function NoSwap_RollOut\n"
        "\tif player.animation == ANI_NOSWAP_ROLL\n"
        "\t\tplayer.animation = ANI_JUMPING\n"
        "\t\tplayer.prevAnimation = ANI_JUMPING\n"
        "\t\tNoSwap_rollFrame = player.frame // the curl's frame is kept aside: the jump may have fewer frames, and the\n"
        "\t\tplayer.frame = 0 // game reads the frame's hitbox (a curl frame past the jump's shook him, and the camera)\n"
        "\tend if\n"
        "end function\n\n\n")
    t = patch(t, f"private alias {ANI_GLIDE_DOWN} : ANI_NOSWAP_GLIDE_DOWN\n",
              f"private alias {ANI_GLIDE_DOWN} : ANI_NOSWAP_GLIDE_DOWN\n"
              f"private alias {ANI_ROLL} : ANI_NOSWAP_ROLL // extras.py \"roll\": the extra's own rolling curl\n", "roll alias")
    a = "private alias object.value15 : player.noswapAbility"
    t = t.replace(a, "private value NoSwap_rollFrame = 0 // the curl's frame while the game sees the jump (NoSwap_RollOut)\n"
                  + a, 1) if t.count(a) == 1 else sys.exit("roll: the noswapAbility alias isn't there once")
    t = patch(t, "public function Player_HandleAmyHitbox\n", functions + "public function Player_HandleAmyHitbox\n",
              "roll functions")
    # ObjectUpdate's ProcessAnimation calls (the normal and the debug-mode copy), and the draw
    start = t.index("event ObjectUpdate\n")
    end = t.index("end event\n", start)
    body = re.sub(r"\n(\t+)ProcessAnimation\(\)\n",
                  lambda m: (f"\n{m.group(1)}CallFunction(NoSwap_RollIn) // [NoSwap] an extra's own rolling curl\n"
                             f"{m.group(1)}ProcessAnimation()\n{m.group(1)}CallFunction(NoSwap_RollOut)\n"), t[start:end])
    if body.count("CallFunction(NoSwap_RollIn)") != 2:
        sys.exit("roll: expected 2 ProcessAnimation calls in ObjectUpdate")
    t = t[:start] + body + t[end:]
    return patch(t, "\tDrawObjectAnimation()\nend event\n",
                 "\tCallFunction(NoSwap_RollIn) // [NoSwap] an extra's own rolling curl\n"
                 "\tDrawObjectAnimation()\n\tCallFunction(NoSwap_RollOut)\nend event\n", "roll draw")


def apply_no_roll(t):
    """extras.py "no_roll" (Gamma never curls into a ball): down while moving on the ground doesn't roll (the ground
    state's two roll starts are skipped for them: NoSwap_RollAllowed), and down + jump out of a crouch is a plain jump
    (their spin dash action is Player_Action_Jump, as in Sonic 1 with the Spin Dash option off). Crouching still
    works; objects that force a roll (tubes) still do. Demos and credits replay Sonic's inputs, so there they roll
    and Spin Dash like him (replays_as_sonic)."""
    extras = [e for e in EXTRAS if e["no_roll"]]
    if not extras:
        return t
    spindash = next(f for f in ("actionSpindash", "spindashFunction") if f"player.{f}" in t)
    for e in extras:
        case = t.index(startup_case(e))
        end = t.index("break", case)
        t = (t[:end] + "if options.attractMode == false // [NoSwap] extras.py \"no_roll\": down + jump is a plain jump\n"
             f"\t\t\t\tplayer[SLOT_PLAYER1].{spindash} = Player_Action_Jump\n"
             "\t\t\tend if\n\t\t\t" + t[end:])
    cases = "".join(f"\t\tcase {e['alias']}\n" for e in extras)
    functions = (
        "// [NoSwap] extras.py \"no_roll\": checkResult false for extras that never roll (tools/abilities.py apply_no_roll);\n"
        "// demos and credits replay Sonic's inputs, so there everyone rolls\n"
        "public function NoSwap_RollAllowed\n"
        "\tcheckResult = true\n"
        "\tif options.attractMode == false\n"
        "\t\tswitch player.character\n" + cases +
        "\t\t\tcheckResult = false\n"
        "\t\t\tbreak\n"
        "\t\tend switch\n"
        "\tend if\n"
        "end function\n\n\n")
    t = patch(t, "public function Player_HandleAmyHitbox\n", functions + "public function Player_HandleAmyHitbox\n",
              "no-roll function")
    return guard_blocks(t, "public function Player_State_Ground", r"\t+player\.state = Player_State_Roll$",
                        ["CallFunction(NoSwap_RollAllowed) // [NoSwap] extras.py \"no_roll\": down doesn't roll them",
                         "if checkResult == true"], ["end if"], 2, "no roll")


def bat_glide_branches(ids, body, orig, ind):
    """`orig` (lines at indent `ind`), or for the extras in `ids`, their own `body(i)` lines instead."""
    if not ids:
        return orig
    i = ids[0]
    rest = bat_glide_branches(ids[1:], body, orig, ind)
    return (f"{ind}if stage.playerListPos == {ALIAS_OF[i]} // [NoSwap] a bat's glide (abilities.py bat_glide)\n"
            + "".join(f"{ind}\t{l}\n" for l in body(i))
            + (f"{ind}else\n" + "".join(f"\t{l}\n" for l in rest.rstrip("\n").split("\n")) if rest else "")
            + f"{ind}end if\n")


def bat_glide(t):
    """bat_glide: Knuckles' glide states (left and right), slower and sinking more gently for these extras. The
    speed scales his glide's x velocity (worked out from its speed each frame); the sink replaces his."""
    ids = with_ability("bat_glide")
    if not ids:
        return t
    ind = "\t\t\t"
    sink = (f"{ind}if player.yvel > 0x8000\n{ind}\tplayer.yvel -= 0x2000\n{ind}else\n"
            f"{ind}\tplayer.yvel += 0x2000\n{ind}end if\n")
    t = patch_n(t, sink, bat_glide_branches(ids, lambda i: [
        f"if player.yvel > {ABILITIES[i]['glide_sink']:#x} // sinks more gently",
        "\tplayer.yvel -= 0x2000", "else", f"\tplayer.yvel += {ABILITIES[i]['glide_gravity']:#x}", "end if"],
        sink, ind), "bat glide sink", 2)
    speed = f"{ind}Cos(player.xvel, player.timer)\n{ind}player.xvel *= player.speed\n{ind}player.xvel >>= 9\n"
    return patch_n(t, speed, speed + bat_glide_branches(ids, lambda i: [
        f"player.xvel *= {round(ABILITIES[i]['glide_speed'] * 256)} // slower: {ABILITIES[i]['glide_speed']} of Knuckles' speed",
        "player.xvel >>= 8"], "", ind), "bat glide speed", 2)


BASE_MOVES = {  # extras.py "base" -> (jump ability, jump offset, or None: Sonic's -5): the base character's own code
    "knuckles": ("Player_Action_DblJumpKnux // [NoSwap] Knuckles' glide and climb", None),
    "tails": ("Player_Action_DblJumpTails // [NoSwap] Tails' flight (as a plain Player Object: no tails drawn)", "-1"),
}


def replays_as_sonic(t):
    """Demos and credits replay Sonic's recorded inputs (options.attractMode): an extra plays them with
    Sonic's jump ability, physics and no ability modules, or it desyncs (Metal Sonic died in the Sonic 1
    credits' Scrap Brain run and the replay looped, 2026-09-25). It still looks like itself."""
    # (the startup part: extra_startup)
    fn = t.index("public function Player_UpdatePhysicsState")
    sw_end = t.index("\tend switch\n", fn) + len("\tend switch\n")
    return (t[:sw_end] + "\tif options.attractMode == true // [NoSwap] replays: extras use Sonic's physics\n"
            "\t\tif stage.playerListPos >= PLAYER_EXTRA1_A\n\t\t\ttemp0 = Player_SonicPhysicsTable\n\t\tend if\n\tend if\n"
            + t[sw_end:])


def extra_flags(extra):
    """The extra's NoSwap_flags at startup (noswap_common.FLAG_BITS): its base character (extras.py "base") and the
    abilities the shared scripts carry out (only those this build keeps: NOSWAP_KEEP)."""
    bits = {"knux": extra["base"] == "knuckles", "tails": extra["base"] == "tails",
            "magnetic": has(extra["id"], "magnetic"), "no_breathing": has(extra["id"], "no_breathing"),
            "breaks_walls": has(extra["id"], "breaks_walls"), "fire_immune": has(extra["id"], "fire_immune")}
    return sum(1 << FLAG_BITS[k] for k, on in bits.items() if on)


def extra_startup(t):
    """ObjectStartup: what every extra's startup case would repeat, once after the switch (each case only loads its
    animation file and sets its jump ability, and no_roll lines): Sonic's Super palette (his colours at rest), the extra's own
    colours (from tables: NoSwap_Palette holds this build's extras', NoSwap_PaletteAt where each starts), its character ID,
    jump offset (its base character's) and the Peelout off. Then demos and credits, which replay Sonic's recorded
    inputs (options.attractMode), get Sonic's jump ability, or they desync (Metal Sonic died in the Sonic 1 credits'
    Scrap Brain run and the replay looped, 2026-09-25); it still looks like itself."""
    start = t.index("event ObjectStartup\n")
    last = max(t.index(startup_case(e), start) for e in EXTRAS)
    at = t.index("\t\tend switch\n", last) + len("\t\tend switch\n")
    # Only this build's extras' rows (NOSWAP_KEEP: a package's own, none for NoSwap's own; every extra's in the full
    # build), so adding a character leaves every other package's tables as they were. Rows are still build IDs (the
    # kind-free pass turns them into the package's own row); rows no extra of this build has are 0 (vanilla: none).
    kept = kept_extras()
    mine = EXTRAS if kept is None else kept
    colours, first, begins = [], {}, {}
    for e in mine:
        pal = e["palette"]
        begins[e["id"]] = len(colours)
        if pal:
            first[e["id"]] = min(pal)
            colours += [pal.get(k, -1) for k in range(min(pal), max(pal) + 1)]  # (-1: a slot it leaves alone)
    ids = [e["id"] for e in mine] or [6]  # (none: the vanilla rows alone, 0-6, and 7 for the loop's end)
    begins[max(ids) + 1] = len(colours)
    offsets = {e["id"]: int(BASE_MOVES.get(e["base"], (None, None))[1] or -5) for e in mine} or {max(ids): 0}
    flags = {e["id"]: extra_flags(e) for e in mine} or {max(ids): 0}
    first = first or {max(ids): 0}  # (no colours: never read, but a table the kind-free pass can take the row from)
    colours = colours or [-1]  # (no colours: never read; the engine gets no empty table)
    tables = (extra_table("NoSwap_PaletteAt", begins, "extra_startup: where each extra's colours start in NoSwap_Palette "
                          "(the next one's start: where they end)")
              + extra_table("NoSwap_PaletteSlot", first, "extra_startup: the palette slot of each extra's first colour")
              + "// extra_startup: every extra's own colours, one per palette slot from its first (-1: left alone)\n"
              + "private table NoSwap_Palette\n" + table_rows(colours) + "end table\n\n"
              + extra_table("NoSwap_JumpOffset", offsets, "extra_startup: the jump offset (its base character's)")
              + extra_table("NoSwap_ExtraFlags", flags, "extra_startup: each extra's NoSwap_flags (noswap_common.FLAG_BITS; "
                            "the surging bit is set while it lasts)") + "\n")
    # (only in a build with such an extra, so the other packages' scripts don't change)
    walls_off = (f"\t\t\t\tSetBit(NoSwap_flags, {FLAG_BITS['breaks_walls']}, false) // nor breaking walls like him\n"
                 if any(has(e["id"], "breaks_walls") for e in mine) else "")
    copy_reset = ("\t\t\tNoSwap_copyMove = 0 // ability_cycle: its first move at each stage load\n"
                  if cycle_extras() else "")
    copy_reset += ("\t\t\tplayer[SLOT_PLAYER1].tailFrame = 0 // Psychokinesis' state and timer (tools/psycho_grab.py)\n"
                   "\t\t\tplayer[SLOT_PLAYER1].tailAnim = 0\n" if with_ability("psycho_grab") else "")
    block = f"""
		if stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] every extra's setup (its own case: animation file, jump ability)
			CallFunction(Player_HandleSuperPalette_Sonic)
			GetTableValue(temp0, stage.playerListPos, NoSwap_PaletteAt) // its own colours
			temp1 = stage.playerListPos
			temp1++
			GetTableValue(temp4, temp1, NoSwap_PaletteAt)
			GetTableValue(temp2, stage.playerListPos, NoSwap_PaletteSlot)
			while temp0 < temp4
				GetTableValue(temp3, temp0, NoSwap_Palette)
				if temp3 >= 0
					SetPaletteEntry(0, temp2, temp3)
				end if
				temp0++
				temp2++
			loop
			player[SLOT_PLAYER1].character = stage.playerListPos
			GetTableValue(player[SLOT_PLAYER1].jumpOffset, stage.playerListPos, NoSwap_JumpOffset)
			GetTableValue(NoSwap_flags, stage.playerListPos, NoSwap_ExtraFlags) // for the shared scripts
{copy_reset}			ANI_PEELOUT = ANI_RUNNING
			if options.attractMode == true // replays are Sonic's inputs: play them as Sonic
				player[SLOT_PLAYER1].jumpAbility = Player_Action_DblJumpSonic
				player[SLOT_PLAYER1].jumpOffset = -5
				SetBit(NoSwap_flags, {FLAG_BITS['knux']}, false) // not Knuckles- or Tails-like either
				SetBit(NoSwap_flags, {FLAG_BITS['tails']}, false)
{walls_off}			end if
		end if
"""
    t = t[:at] + block + t[at:]
    # (before the ability functions: NoSwap_SuperGlow reads them too)
    head = "// [NoSwap] Ability modules for extra characters (generated by tools/abilities.py)\n"
    return patch(t, head, tables + head, "extra startup tables")


def apply_base_characters(t):
    """Extras built on Knuckles or Tails (extras.py "base") get that character's jump ability instead of
    Sonic's. Knuckles-based ones also take his physics case; extra_startup sets NoSwap_flags' Knuckles bit, which the
    stage scripts' Knuckles checks look at (noswap_common.knux_like)."""
    for e in (e for e in EXTRAS if e["base"] in BASE_MOVES):
        ability = BASE_MOVES[e["base"]][0]
        case = t.index(startup_case(e))
        end = t.index("break", case)
        body = t[case:end]
        body = re.sub(r"= Player_Action_DblJumpSonic", "= " + ability, body, count=1)
        if ability.split()[0] not in body:
            sys.exit(f"base character: no jump ability line for {e['alias']}")
        t = t[:case] + body + t[end:]
        if e["base"] == "knuckles":  # physics: Knuckles' case (Tails' table is the same as Sonic's)
            fn = t.index("public function Player_UpdatePhysicsState")
            sw_end = t.index("end switch", fn)
            section = re.sub(rf"\n\t*case {e['alias']} // \[NoSwap\] placeholder: behaves like Sonic", "", t[fn:sw_end], count=1)
            section = section.replace("\tcase PLAYER_KNUCKLES_A\n",
                                      f"\tcase {e['alias']} // [NoSwap] Knuckles' physics\n\tcase PLAYER_KNUCKLES_A\n", 1)
            t = t[:fn] + section + t[sw_end:]
    return t


def surge_checks(ind, tag=""):
    """power_surge: `temp0 = true` while a surge lasts (everything she touches counts as attacked)."""
    return "".join(f"{ind}if stage.playerListPos == {ALIAS_OF[i]} // {tag}Power Surge: she zaps whatever she touches\n"
                   f"{ind}\tif {surge_active(i)}\n{ind}\t\ttemp0 = true\n{ind}\tend if\n{ind}end if\n"
                   for i in with_ability("power_surge"))


def apply_monitor(t):
    """Monitors: an extra's attack animations break them, like Amy's hammer; so does a Power Surge (NoSwap_flags'
    surging bit: GetBit writes checkResult, as the CheckEquals around it do)."""
    checks = "".join(f"\t\t\tCheckEqual(player[currentPlayer].animation, {a}) // [NoSwap] extras' attack moves\n"
                     "\t\t\ttemp0 |= checkResult\n" for a in ATTACK_ANIMS)
    checks += (f"\t\t\tGetBit(checkResult, NoSwap_flags, {FLAG_BITS['surging']}) // [NoSwap] NoSwap_flags bit "
               f"{FLAG_BITS['surging']} (value {1 << FLAG_BITS['surging']}): a Power Surge zaps whatever she touches\n"
               "\t\t\ttemp0 |= checkResult\n")
    anchor = "\t\t\tCheckEqual(player[currentPlayer].animation, ANI_HAMMER_DASH)\n\t\t\ttemp0 |= checkResult\n"
    return patch(t, anchor, anchor + checks, "monitor attack moves")


def apply_ring(t):
    """Rings: magnetic extras (NoSwap_flags) pull them in without a shield, with the lightning shield's own attraction
    (a ring within 64 px starts drifting to the player, and stays attracted while the player has the shield)."""
    lines = t.split("\n")
    for test, hold in (("if player[currentPlayer].shield == SHIELD_LIGHTNING", "SHIELD_LIGHTNING"),
                       ("if player[arrayPos0].shield != SHIELD_LIGHTNING", None)):
        hits = [k for k, l in enumerate(lines) if l.strip() == test]
        if len(hits) != 1:
            sys.exit(f"ring: found {len(hits)} of \"{test}\" (expected 1)")
        k = hits[0]
        ind = lines[k][: len(lines[k]) - len(lines[k].lstrip("\t"))]
        who = test.split(".shield")[0].split()[1]
        tmp = free_temp(lines, k, "ring")  # set here and read by the test just below, nothing else
        new = flag_test(ind, "magnetic", tmp, "magnetic: rings are pulled in without a shield")
        new += [f"{ind}\t{tmp} = SHIELD_LIGHTNING", f"{ind}else", f"{ind}\t{tmp} = {who}.shield", f"{ind}end if",
                f"{ind}if {tmp} {'==' if hold else '!='} SHIELD_LIGHTNING"]
        lines[k:k + 1] = new
    return "\n".join(lines)


def apply_fire_tiles(t):
    """Lava tiles that test the fire shield themselves instead of calling Player_FireHit (S1 MZSetup, S2 MBZSetup): an
    extra that fire never hurts (NoSwap_flags' fire_immune bit) is spared too, as with the shield."""
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == "if player[currentPlayer].shield != SHIELD_FIRE"]
    if len(hits) != 1:
        sys.exit(f"fire tiles: found {len(hits)} fire-shield tests (expected 1)")
    i = hits[0]
    ind = line_indent(lines[i])
    j = i + 1
    while not (lines[j].strip() == "end if" and line_indent(lines[j]) == ind):
        j += 1
    scratch = free_temp(lines, i, "fire tiles")
    lines[i:j + 1] = (flag_test(ind, "fire_immune", scratch, "fire never hurts this extra (Blaze)", value="false")
                      + [f"\t{l}" for l in lines[i:j + 1]] + [f"{ind}end if"])
    return "\n".join(lines)


def apply_water(t):
    """Water scripts: extras that don't breathe (NoSwap_flags) skip the whole air countdown (like a bubble shield)."""
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == "if player[currentPlayer].shield != SHIELD_BUBBLE"]
    if len(hits) != 1:
        sys.exit(f"water: found {len(hits)} bubble-shield blocks (expected 1)")
    i = hits[0]
    ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
    j = i + 1
    while not (lines[j].strip() == "end if" and lines[j].startswith(ind + "end if")
               and len(lines[j]) - len(lines[j].lstrip("\t")) == len(ind)):
        j += 1
    inner = [f"\t{l}" for l in lines[i + 1:j]]
    scratch = free_temp(lines, i, "water")
    opens = flag_test(ind + "\t", "no_breathing", scratch, "doesn't breathe (Metal Sonic)", value="false")
    lines[i + 1:j] = opens + inner + [f"{ind}\tend if"]
    return "\n".join(lines)
