#!/usr/bin/env python3
"""The S3&K DLL's character data (docs/plan-b-modular-characters.md step 3b item 7).

Each extra's own data (palette, special-stage palette, base, animation base, roll flags, every ability number) goes
in its package's noswap_character.json (s3k_json below, written by build_packages.py); the DLL reads it at startup
(native/src/ExtraData.h). What stays compiled in is global: native/build/extras_gen.h, written here, has

- the ExtraAbilities struct the move code uses, and EXTRA_ABILITY_FIELDS (the same fields as an X-macro: type, name,
  count, default), from which the DLL's JSON loader builds its field table: a new *kind* of move still needs a DLL build,
  its numbers don't;
- nothing about which extras exist or their numbers: the DLL numbers installed packages at runtime from its registry
  (native/src/Roster.h, roster.json). Roster.h's LEGACY_KEYS freeze today's first 21 keys at kinds 7-27 (the prebuilt
  menu archives' order); check_legacy_keys() stops the build if tools/extras.py's first 21 ever differ from them.

Field names in the JSON are the struct's. Physics, glideSpeed, triple2 / triple3, doubleJumpScale and the surge's are
multipliers in 1/1000; the sounds are files in Data/SoundFX (null: none).
"""
import re
from pathlib import Path

from extras import ACTIVE_KIND_TOKEN, EXTRAS, S3K_MENU_PICTURES
import abilities as ab

GRAPPLE_MAX = 8  # Ear Grapple frames (grapple_tip) the struct has room for
PUDDLE_MAX = 40  # Puddle Slide steps (puddle_frames) the struct has room for
FLASH_MAX = 32  # Screen Nuke flash frames (melee_nuke "flash") the struct has room for
CYCLE_MAX = 4  # ability_cycle moves the struct has room for
SINK_MAX = 16  # Shadow Sink frames (sink_frames) the struct has room for
SINK_UNDER_MAX = 8  # ...and its frames while under (sink_under)
HEAD_VARIANT_MAX = 8  # Head Throw head variants the struct has room for (head_throw.VARIANT_MAX)
BASES = {"sonic": (0, 77), "tails": (1, 84), "knuckles": (2, 78)}  # (base, first ability animation: build_s3k_art.py)


def ability_fields(c, who="?"):
    """[(type, name, count, value)] for one abilities.py entry, in the struct's order. type: bool, int, str."""
    tips = c.get("grapple_tip", [])
    if len(tips) > GRAPPLE_MAX:
        raise SystemExit(f"{who}: more than {GRAPPLE_MAX} Ear Grapple frames")
    puddle = c.get("puddle_frames", [])
    if len(puddle) > PUDDLE_MAX:
        raise SystemExit(f"{who}: more than {PUDDLE_MAX} Puddle Slide steps")
    nuke = c.get("melee_nuke") or {}
    if len(nuke.get("flash", [])) > FLASH_MAX:
        raise SystemExit(f"{who}: more than {FLASH_MAX} Screen Nuke flash frames")
    sink, under = c.get("sink_frames", []), c.get("sink_under", [])
    if len(sink) > SINK_MAX or len(under) > SINK_UNDER_MAX:
        raise SystemExit(f"{who}: more than {SINK_MAX} Shadow Sink frames or {SINK_UNDER_MAX} under")
    triple = c.get("triple_jumps", [1.0, 1.0])
    if len(triple) != 2:
        raise SystemExit(f"{who}: triple_jumps needs 2 multipliers")
    has = lambda a: a in c["abilities"]
    get = c.get
    run, up = c.get("melee_run") or {}, c.get("melee_up") or {}
    mult = lambda v: round(1000 * v)
    phys = lambda k: mult(get("physics", {}).get(k, 1.0))
    surge = lambda k: mult(get("surge_physics", {}).get(k, 1.0))
    B, I, S = "bool", "int", "str"
    return [
        (B, "jetDash", 1, has("jet_dash")), (B, "hover", 1, has("hover")), (B, "pogo", 1, has("pogo")),
        (B, "umbrella", 1, has("umbrella")), (B, "shot", 1, has("melee")),
        (I, "dashFrames", 1, get("dash_frames", 0)), (I, "dashSpeed", 1, get("dash_speed", 0)),
        (I, "hoverFrames", 1, get("hover_frames", 0)), (I, "hoverSink", 1, get("hover_sink", 0)),
        (I, "pogoSpeed", 1, get("pogo_speed", 0)), (I, "umbrellaSink", 1, get("umbrella_sink", 0)),
        (I, "shotFrames", 1, get("melee_ticks", 0) * len(get("melee_reach", []))),
        (I, "shotTicks", 1, get("melee_ticks", 1)),
        (B, "chaosControl", 1, has("chaos_control")), (B, "aimDash", 1, has("aim_dash")),
        (I, "chaosFreeze", 1, get("chaos_freeze", 0)), (I, "chaosWarp", 1, get("chaos_warp", 0)),
        (I, "chaosSpeed", 1, get("chaos_speed", 0)), (I, "chaosPop", 1, get("chaos_pop", 0)),
        (I, "diagX", 1, get("diag_x", 0)), (I, "diagY", 1, get("diag_y", 0)), (I, "floatFrames", 1, get("float_frames", 0)),
        (B, "hammerDrop", 1, has("hammer_drop")), (B, "rayGlide", 1, has("ray_glide")),
        (B, "umbrellaAttack", 1, bool(get("umbrella_attack"))),
        (I, "upX", 1, get("up_x", get("diag_x", 0))), (I, "upY", 1, get("up_y", get("diag_y", 0))),
        (I, "shotBlink", 1, get("melee_blink", 0)), (I, "shotCooldown", 1, get("melee_cooldown", 0)),
        (I, "topSpeed", 1, phys("top_speed")), (I, "acceleration", 1, phys("acceleration")),
        (I, "airAcceleration", 1, phys("air_acceleration")), (I, "jump", 1, phys("jump")),
        (B, "aimDashY", 1, bool(get("aim_dash_y"))),
        (B, "batGlide", 1, has("bat_glide")), (B, "screwKick", 1, has("screw_kick")),
        (I, "glideSpeed", 1, mult(get("glide_speed", 1.0))), (I, "glideSink", 1, get("glide_sink", 0)),
        (I, "glideGravity", 1, get("glide_gravity", 0)), (I, "kickX", 1, get("kick_x", 0)),
        (I, "kickY", 1, get("kick_y", 0)), (I, "kickBounce", 1, get("kick_bounce", 0)),
        # (the Rocket Ride, abilities.py rocket_ride: its fields keep the names of the Bomb Jump it replaced; bombFrames is
        # the ride's frames, bombLaunch the blast's launch)
        (B, "bombJump", 1, has("rocket_ride")),
        (I, "bombFrames", 1, get("ride_frames", 0)), (I, "blastFrames", 1, get("blast_frames", 0)),
        (I, "blastTicks", 1, get("blast_ticks", 1)), (I, "bombLaunch", 1, get("blast_launch", 0)),
        (B, "earGrapple", 1, has("ear_grapple")), (B, "grappleY", 1, bool(get("grapple_y"))),
        (I, "grappleFrames", 1, len(tips)), (I, "reelSpeed", 1, get("reel_speed", 0)),
        (I, "reelFrames", 1, get("reel_frames", 0)), (I, "latchRange", 1, get("latch_range", 0)),
        (I, "grappleHop", 1, get("grapple_hop", 0)), (I, "grappleForward", 1, get("grapple_forward", 0)),
        (I, "snapFrames", 1, get("snap_frames", 1)),
        (I, "tipX", GRAPPLE_MAX, [x for x, _ in tips]), (I, "tipY", GRAPPLE_MAX, [y for _, y in tips]),
        (B, "spiritFlight", 1, has("spirit_flight")), (B, "shotStop", 1, bool(get("melee_stop"))),
        (I, "spiritTransform", 1, get("spirit_transform", 0)), (I, "spiritTicks", 1, get("spirit_ticks", 1)),
        (I, "spiritFrames", 1, get("spirit_frames", 0)), (I, "spiritSpeed", 1, get("spirit_speed", 0)),
        (I, "spiritDiag", 1, get("spirit_diag", 0)), (I, "spiritAccel", 1, get("spirit_accel", 0)),
        (I, "shotAirFrames", 1, get("melee_ticks", 0) * len(get("melee_air_reach", []))),
        (B, "tripleJump", 1, has("triple_jump")),
        (I, "tripleWindow", 1, get("triple_window", 0)), (I, "tripleSpeed", 1, get("triple_speed", 0)),
        (I, "triple2", 1, mult(triple[0])), (I, "triple3", 1, mult(triple[1])),
        (B, "doubleJump", 1, has("double_jump")), (B, "wallCling", 1, has("wall_cling")),
        (I, "doubleJumpScale", 1, mult(get("double_jump", 1.0))), (I, "clingFrames", 1, get("cling_frames", 0)),
        (I, "clingHold", 1, get("cling_hold", 0)), (I, "clingSlide", 1, get("cling_slide", 0)),
        (I, "climbSpeed", 1, get("climb_speed", 0)), (I, "wallJumpX", 1, get("wall_jump_x", 0)),
        (I, "wallJumpY", 1, get("wall_jump_y", 0)), (I, "clingLock", 1, get("cling_lock", 0)),
        (I, "ledgeHop", 1, get("ledge_hop", 0)), (I, "ledgeForward", 1, get("ledge_forward", 0)),
        (I, "wallX", 1, ab.WALL_X), (I, "wallY", 1, ab.WALL_Y),
        (B, "thunderZip", 1, has("thunder_zip")), (B, "powerSurge", 1, has("power_surge")),
        (B, "magnetic", 1, has("magnetic")),
        (I, "zipFrames", 1, get("zip_frames", 0)), (I, "zipPose", 1, get("zip_pose", 0)),
        (I, "zipSpeed", 1, get("zip_speed", 0)), (I, "zipCarry", 1, get("zip_carry", 0)),
        (I, "surgeFrames", 1, get("surge_frames", 0)), (I, "surgeCooldown", 1, get("surge_cooldown", 0)),
        (I, "surgeTopSpeed", 1, surge("top_speed")), (I, "surgeAcceleration", 1, surge("acceleration")),
        (I, "surgeAirAcceleration", 1, surge("air_acceleration")),
        (B, "extremeGear", 1, has("extreme_gear")),
        *[(I, name, 1, get(key, 0)) for name, key in (
            ("gearSpeed", "gear_speed"), ("gearTop", "gear_top"), ("gearAccel", "gear_accel"),
            ("gearRecover", "gear_recover"), ("gearBrake", "gear_brake"), ("gearTurn", "gear_turn"),
            ("gearSink", "gear_sink"), ("gearLift", "gear_lift"), ("gearRise", "gear_rise"))],
        (I, "gearLiftFrames", 1, get("gear_lift_frames", 0)), (I, "gearFrames", 1, get("gear_frames", 0)),
        # S3&K's own sound files (only where set: the other extras' shots stay silent there)
        (S, "gearSound", 1, get("gear_sfx_s3k")), (S, "shotSound", 1, get("melee_sfx_s3k")),
        # the Screw Kick started by jump (kick_jump: Mecha Sonic's Spike Ball) and its sound; the shot as a burst of speed
        # (melee_boost: his Jet Boost)
        (B, "kickOnJump", 1, bool(get("kick_jump"))), (S, "kickSound", 1, get("kick_sfx_s3k")),
        (I, "shotBoost", 1, get("melee_boost", 0)),
        # Chaos' Puddle Slide (abilities.py puddle_slide): the drop, then the puddle's steps (puddleFrames: slot 1's frame
        # per step of puddleTicks game frames), at least puddleSpeed for puddleMove steps, and its sound
        (B, "puddleSlide", 1, has("puddle_slide")), (I, "puddleDrop", 1, get("puddle_drop", 0)),
        (I, "puddleSpeed", 1, get("puddle_speed", 0)), (I, "puddleTicks", 1, get("puddle_ticks", 1)),
        (I, "puddleMove", 1, get("puddle_move", 0)), (I, "puddleSteps", 1, len(puddle)),
        (I, "puddleFrames", PUDDLE_MAX, puddle), (S, "puddleSound", 1, get("puddle_sfx_s3k")),
        # breaks walls like Knuckles (abilities.py breaks_walls: Heavy; the DLL shows BreakableWall Knuckles' ID), and
        # nothing hurts him during the melee (melee_safe: Bomb's Self-Destruct)
        (B, "breaksWalls", 1, has("breaks_walls")), (B, "shotSafe", 1, bool(get("melee_safe"))),
        # Heavy's Charge (abilities.py charge): held on Y on the ground
        (B, "charge", 1, has("charge")), (I, "chargeAccel", 1, get("charge_accel", 0)),
        (I, "chargeGain", 1, get("charge_gain", 0)), (I, "chargeTop", 1, get("charge_top", 0)),
        (I, "chargeFriction", 1, get("charge_friction", 0)), (I, "chargeBrake", 1, get("charge_brake", 0)),
        (I, "chargeStride", 1, get("charge_stride", 1)), (I, "chargeShove", 1, get("charge_shove", 0)),
        # its Shine Spark (the charge's "spark_*": abilities.py spark_after; the DLL's Spark): stored frames, the flight's
        # speed (and its diagonal per axis), the stop's skid, the glow (its greys' first slot and count, the colour they
        # move toward and the 3 amounts, of 256) and its sounds (stored, launched)
        (I, "sparkStore", 1, get("spark_store", 0) if get("spark_speed") else 0), (I, "sparkSpeed", 1, get("spark_speed", 0)),
        (I, "sparkDiag", 1, ab.spark_diag_of(c)), (I, "sparkSkid", 1, get("spark_skid", 0)),
        (I, "sparkSkidFrames", 1, get("spark_skid_frames", 0)),
        (I, "sparkGlowFirst", 1, min(get("spark_glow_slots", [0]))),
        (I, "sparkGlowCount", 1, len(get("spark_glow_slots", []))),
        (I, "sparkGlowTo", 1, get("spark_glow_to", 0)), (I, "sparkGlow", 3, get("spark_glow", [0, 0, 0])),
        (S, "sparkStoreSound", 1, get("spark_store_sfx_s3k")), (S, "sparkSound", 1, get("spark_sfx_s3k")),
        # Honey's Spin Attack (abilities.py spin_attack): held on Y, on the ground or in the air
        (B, "spinAttack", 1, has("spin_attack")), (I, "spinFrames", 1, get("spin_frames", 0)),
        (I, "spinCooldown", 1, get("spin_cooldown", 0)), (I, "spinTicks", 1, get("spin_ticks", 1)),
        (I, "spinGravity", 1, get("spin_gravity", 256)), (I, "spinBounce", 1, get("spin_bounce", 0)),
        (I, "spinBounceX", 1, get("spin_bounce_x", 0)), (S, "spinSound", 1, get("spin_sfx_s3k")),
        # never drowns (abilities.py no_breathing: Metal, Gamma, Mecha Sonic, Chaos; the DLL holds the drown timer at 0)
        (B, "noBreathing", 1, has("no_breathing")),
        # fire never hurts her (abilities.py fire_immune: Blaze; the DLL's Player_FireHurt hook and AsFireShield)
        (B, "fireImmune", 1, has("fire_immune")),
        # the Rocket Ride's ride (abilities.py rocket_ride: Robotnik's): at least rideSpeed along, rising at rideRise, and
        # its sounds (the ride's, the blast's)
        (I, "rideSpeed", 1, get("ride_speed", 0)), (I, "rideRise", 1, get("ride_rise", 0)),
        (S, "rideSound", 1, get("ride_sfx_s3k")), (S, "blastSound", 1, get("blast_sfx_s3k")),
        # Sally's Spin-Kick High Jump (abilities.py high_kick): Y on the ground or in the air
        (B, "highKick", 1, has("high_kick")), (I, "highKickWindup", 1, get("high_kick_windup", 0)),
        (I, "highKickRise", 1, get("high_kick_rise", 0)), (I, "highKickTicks", 1, get("high_kick_ticks", 1)),
        (I, "highKickRecover", 1, get("high_kick_recover", 0)), (I, "highKickCooldown", 1, get("high_kick_cooldown", 0)),
        (S, "highKickSound", 1, get("high_kick_sfx_s3k")),
        # several jump abilities, one active at a time, Y picking the next (abilities.py ability_cycle: Emerl's Copycat):
        # how many, and each one's code (abilities.CYCLE_MOVES: 1 double jump, 2 Screw Kick by jump, 3 Jet Dash, 4 umbrella)
        (I, "cycleCount", 1, len(get("ability_cycle", []))),
        (I, "cycleMoves", CYCLE_MAX, cycle_codes(get("ability_cycle", []))),
        # a head set per cycle move (abilities.py copy_heads: Emerl's; build_s3k_art.py COPY_HEADS_S3K): how many (0 none)
        (I, "copyHeads", 1, len(get("ability_cycle", [])) if get("copy_heads") else 0),
        # Big's water swim (abilities.py water_swim): underwater, the mid-air jump press is a stroke
        (B, "waterSwim", 1, has("water_swim")), (I, "swimStroke", 1, get("swim_stroke", 0)),
        (I, "swimDelay", 1, get("swim_delay", 0)),
        # Tails Doll's Phase Warp (abilities.py phase_warp): the jump press blinks him up to warpRange px where the d-pad
        # points, the flicker out, the time gone and the flicker in (frames), and its sound
        (B, "phaseWarp", 1, has("phase_warp")), (I, "warpRange", 1, get("warp_range", 0)),
        (I, "warpVanish", 1, get("warp_vanish", 0)), (I, "warpGone", 1, get("warp_gone", 0)),
        (I, "warpAppear", 1, get("warp_appear", 0)), (S, "warpSound", 1, get("warp_sfx_s3k")),
        # the melee hanging still in the air (melee_hang), and his Screen Nuke (melee_nuke): at nukeAt game frames into
        # the move, the flash (nukeFlash: the palette's darkness per frame, 0-255, nukeFlashCount of them) and nukeHit
        # frames of everything on screen hit; its sound
        (B, "shotHang", 1, bool(get("melee_hang"))),
        (I, "nukeAt", 1, nuke.get("at", -1) * get("melee_ticks", 1) if nuke else -1),
        (I, "nukeHit", 1, nuke.get("hit", 0)), (I, "nukeFlashCount", 1, len(nuke.get("flash", []))),
        (I, "nukeFlash", FLASH_MAX, nuke.get("flash", [])), (S, "nukeSound", 1, nuke.get("sfx_s3k")),
        # the nuke's reach (Bomb's half-screen nuke: a box nukeReachX px either side of him, nukeReachY above and below;
        # 0: anything on screen, Tails Doll's), and the melee's cost (melee_cost: its end hurts him, a normal hit)
        (I, "nukeReachX", 1, nuke.get("reach_x", 0) if nuke.get("box") else 0),
        (I, "nukeReachY", 1, nuke.get("reach_y", 0) if nuke.get("box") else 0),
        (B, "shotCost", 1, bool(get("melee_cost"))),
        # Ray Poward's Slide (abilities.py ground_slide): down + jump on the ground starts the Puddle Slide's ground part at
        # once (its puddle* numbers above), instead of the Spin Dash
        (B, "groundSlide", 1, has("ground_slide")), (B, "slideRunning", 1, bool(get("slide_running"))),
        # Sparkster's Rocket Burst (abilities.py rocket_burst): jump held in mid-air charges, letting go fires it 8 ways
        # (nothing held: the Rocket Spin), ricocheting off walls and ceilings
        (B, "rocketBurst", 1, has("rocket_burst")), (I, "rocketCharge", 1, get("rocket_charge", 0)),
        (I, "rocketFrames", 1, get("rocket_frames", 0)), (I, "rocketSpeed", 1, get("rocket_speed", 0)),
        (I, "rocketDiag", 1, get("rocket_diag", 0)), (I, "rocketSink", 1, get("rocket_sink", 0)),
        (I, "rocketSpinFrames", 1, get("rocket_spin_frames", 0)), (I, "rocketSpinTicks", 1, get("rocket_spin_ticks", 1)),
        (S, "rocketChargeSound", 1, get("rocket_charge_sfx_s3k")), (S, "rocketSound", 1, get("rocket_sfx_s3k")),
        # Ristar's Grab, hang and Meteor Strike (tools/star_grab.py; the pull uses reelSpeed / reelFrames / latchRange,
        # the climb climbSpeed)
        (B, "starGrab", 1, has("star_grab")), (I, "grabStep", 1, get("grab_step", 0)),
        (I, "grabFrames", 1, get("grab_frames", 0)), (I, "retractFrames", 1, get("retract_frames", 1)),
        (I, "yankSpeed", 1, get("yank_speed", 0)), (I, "yankFrames", 1, get("yank_frames", 0)),
        (I, "yankRange", 1, get("yank_range", 0)), (I, "bounceY", 1, get("bounce_y", 0)),
        (I, "bounceX", 1, get("bounce_x", 0)), (I, "hangHop", 1, get("hang_hop", 0)),
        (I, "hangPush", 1, get("hang_push", 0)), (I, "windupShow", 1, get("windup_show", 0)),
        (I, "windupFull", 1, get("windup_full", 0)), (I, "meteorSpeed", 1, get("meteor_speed", 0)),
        (I, "meteorFrames", 1, get("meteor_frames", 0)), (S, "grabSound", 1, get("grab_sfx_s3k")),
        (S, "latchSound", 1, get("latch_sfx_s3k")), (S, "meteorSound", 1, get("meteor_sfx_s3k")),
        # Headdy's Head Throw (tools/head_throw.py): per head variant (index 0 his own; the monitor_swap module picks
        # one: the DLL's head::g_variant) its step (px a frame) and frames out; how many variants; the throw's sound
        (B, "headThrow", 1, has("head_throw")), (I, "headVariants", 1, len(get("head_variants", []))),
        (I, "headStep", HEAD_VARIANT_MAX, head_numbers(get("head_variants", []), "step")),
        (I, "headFrames", HEAD_VARIANT_MAX, head_numbers(get("head_variants", []), "frames")),
        (S, "headSound", 1, get("head_sfx_s3k")),
        # John Morris' whip poses (abilities.py melee_whip: crouching, up-forward and down in the air, by the d-pad as Y is
        # pressed; their reach is their frames' own boxes, build_s3k_art.py) and monitor_swap (tools/monitor_swap.py): its
        # entries' count (the shot thrown is swap_shots[its index]) and the sound of a swap
        (B, "shotWhip", 1, bool(get("melee_whip"))), (I, "swapCount", 1, len(get("monitor_swap", []))),
        (S, "swapSound", 1, get("swap_sfx_s3k")),
        # monitor_swap's HUD icon ("swap_icon": the current entry's Shot.bin frame at the top middle: shots::IconDraw)
        (B, "swapIcon", 1, bool(get("swap_icon"))),
        # the floating lean (abilities.py float_lean: Mephiles): the walk / run drawn turned toward his travel, floatLean /
        # 512 of a turn per px per frame of his speed, floatLeanMax at most, no slope rotation (0: none)
        (I, "floatLean", 1, get("float_lean", 0)), (I, "floatLeanMax", 1, get("float_lean_max", 0)),
        # Mephiles' Shadow Sink (abilities.py sink): down + Y on the ground; sinkFrames (extra slot 5's frame per step of
        # sinkTicks game frames) forward, then sinkUnder's in turn (sinkUnderTicks each) for sinkMax frames at most, then
        # sinkFrames backward; sinkCooldown frames before the next; its sound
        (B, "sink", 1, has("sink")), (I, "sinkTicks", 1, get("sink_ticks", 1)), (I, "sinkSteps", 1, len(sink)),
        (I, "sinkFrames", SINK_MAX, sink), (I, "sinkUnderCount", 1, len(under)), (I, "sinkUnder", SINK_UNDER_MAX, under),
        (I, "sinkUnderTicks", 1, get("sink_under_ticks", 1)), (I, "sinkMax", 1, get("sink_max", 0)),
        (I, "sinkCooldown", 1, get("sink_cooldown", 0)), (S, "sinkSound", 1, get("sink_sfx_s3k")),
        # Marine's Anchor Throw (tools/anchor_throw.py; the reel uses reelSpeed / reelFrames / latchRange / grappleHop /
        # grappleForward and latchSound above): the arc (speed along, rise, and the high throw's), its gravity, its frames
        # out, the way back's speed, the cooldown after, the throw's sound; and water walk (tools/water_walk.py)
        (B, "anchorThrow", 1, has("anchor_throw")), (I, "anchorSpeed", 1, get("anchor_speed", 0)),
        (I, "anchorRise", 1, get("anchor_rise", 0)), (I, "anchorHighSpeed", 1, get("anchor_high_speed", 0)),
        (I, "anchorHighRise", 1, get("anchor_high_rise", 0)), (I, "anchorGravity", 1, get("anchor_gravity", 0)),
        (I, "anchorFrames", 1, get("anchor_frames", 0)), (I, "anchorReturn", 1, get("anchor_return", 0)),
        (I, "anchorCooldown", 1, get("anchor_cooldown", 0)), (S, "anchorSound", 1, get("anchor_sfx_s3k")),
        (B, "waterWalk", 1, has("water_walk")),
        # Max's Ear Grapple chains (abilities.py grapple_refill / grapple_cooldown, the user 2026-09-30): a latch or a
        # badnik hit refills the Y grab, a miss doesn't; the next grab waits grappleCooldown frames after a pull ends
        (B, "grappleRefill", 1, bool(get("grapple_refill"))), (I, "grappleCooldown", 1, get("grapple_cooldown", 0)),
        # Rouge's Treasure Sense (tools/treasure_sense.py; native/src/TreasureSense.h): Y on the ground, the pause's frames,
        # the marker's, the cooldown's, the "no signal" sound; and Jewel Thief (10-ring monitors give 20)
        (B, "treasureSense", 1, has("treasure_sense")), (I, "sensePause", 1, get("sense_pause", 0)),
        (I, "senseShow", 1, get("sense_show", 0)), (I, "senseCooldown", 1, get("sense_cooldown", 0)),
        (S, "senseSound", 1, get("sense_sfx_s3k")), (B, "jewelThief", 1, has("jewel_thief")),
        # Silver's Psychokinesis (abilities.py psycho_grab; native/src/PsychoGrab.h): Y catches the nearest badnik in reach
        # (psychoReach px ahead, psychoBehind behind, psychoHeight above / below), held psychoHold frames (the pose's frames
        # psychoTicks each), then thrown as his shot ("input" "grab"), drawn as the badnik was
        (B, "psychoGrab", 1, has("psycho_grab")), (I, "psychoReach", 1, get("psycho_reach", 0)),
        (I, "psychoBehind", 1, get("psycho_behind", 0)), (I, "psychoHeight", 1, get("psycho_height", 0)),
        (I, "psychoHold", 1, get("psycho_hold", 0)), (I, "psychoThrow", 1, get("psycho_throw", 0)),
        (I, "psychoTicks", 1, get("psycho_ticks", 0)),
        (S, "psychoSound", 1, get("psycho_sfx_s3k")),
        # Ecco's free swim (abilities.py free_swim; native/src/EccoSwim.h): underwater he swims anywhere (top speed, build-up,
        # drain, turn in degrees a frame), drawn from slot 41 (swimDirs directions x swimCycle frames, swimTicks each); Y the
        # charge ram (ramFrames at ramSpeed, then ramCooldown; slot 42, swimDirs x ramCycle); out of the surface, the leap
        # (slot 43: leapFrames, leapTicks each)
        (B, "freeSwim", 1, has("free_swim")), (I, "swimSpeed", 1, get("swim_speed", 0)),
        (I, "swimAccel", 1, get("swim_accel", 0)), (I, "swimDrag", 1, get("swim_drag", 0)),
        (I, "swimTurn", 1, get("swim_turn", 0)), (I, "swimDirs", 1, get("swim_dirs", 0)),
        (I, "swimCycle", 1, get("swim_cycle", 0)), (I, "swimTicks", 1, get("swim_ticks", 0)),
        (I, "ramFrames", 1, get("ram_frames", 0)), (I, "ramSpeed", 1, get("ram_speed", 0)),
        (I, "ramCooldown", 1, get("ram_cooldown", 0)), (I, "ramCycle", 1, get("ram_cycle", 0)),
        (S, "ramSound", 1, get("ram_sfx_s3k")), (I, "leapFrames", 1, get("leap_frames", 0)),
        (I, "leapTicks", 1, get("leap_ticks", 0)),
        # NiGHTS' free flight, Drill Dash and Paraloop (abilities.py free_flight; native/src/NightsFlight.h; tools/
        # free_flight.py's defaults): the flight (top speed, build-up, drain, turn in degrees a frame), the meter (frames;
        # drained a frame, refilled a frame on the ground, per ring), the empty float's fall, the underwater swim cycle
        # (slot 42's frames from 8, ticks each); Y the Drill Dash (frames, speed, rest, its cost of the meter; slot 41); the
        # Paraloop (samples kept, frames between them, px to close, the least size, frames of its hit)
        *[(I, name, 1, (get(key, d) if has("free_flight") else 0)) for name, key, d in (
            ("flySpeed", "fly_speed", 0x50000), ("flyAccel", "fly_accel", 0x3000), ("flyDrag", "fly_drag", 0x1800),
            ("flyTurn", "fly_turn", 8), ("flyMeter", "fly_meter", 360), ("flyDrain", "fly_drain", 1),
            ("flyRefill", "fly_refill", 6), ("flyRing", "fly_ring", 60), ("flySink", "fly_sink", 0x10000),
            ("flySwimFrames", "fly_swim_frames", 10), ("flySwimTicks", "fly_swim_ticks", 4),
            ("drillFrames", "drill_frames", 20), ("drillSpeed", "drill_speed", 0xA0000),
            ("drillCooldown", "drill_cooldown", 20), ("drillCost", "drill_cost", 30), ("loopPoints", "loop_points", 12),
            ("loopEvery", "loop_every", 5), ("loopClose", "loop_close", 24), ("loopMin", "loop_min", 40),
            ("loopHit", "loop_hit", 3))],
        (B, "freeFlight", 1, has("free_flight")), (S, "drillSound", 1, get("drill_sfx_s3k")),
        # the melee's running and up + Y poses (abilities.py melee_run / melee_up: Axel's Grand Upper and Dragon Wing;
        # slots 45 / 46, their reach in their frames' boxes, build_s3k_art.py): the least ground speed that counts as
        # running, the boost then, its game frames; up + Y's ring cost (fewer: the plain melee) and its game frames
        (I, "meleeRunSpeed", 1, run.get("speed", 0)), (I, "meleeRunBoost", 1, run.get("boost", 0)),
        (I, "meleeRunFrames", 1, get("melee_ticks", 0) * len(run.get("reach", []))),
        (B, "meleeUp", 1, bool(up)), (I, "meleeUpRings", 1, up.get("rings", 0)),
        (I, "meleeUpFrames", 1, get("melee_ticks", 0) * len(up.get("reach", []))),
        # their own sounds (melee_run / melee_up "sfx_s3k"; null: the melee's, shotSound)
        (S, "meleeRunSound", 1, run.get("sfx_s3k")), (S, "meleeUpSound", 1, up.get("sfx_s3k")),
        # no_stomp (abilities.py; the user, 2026-10-02): his jump isn't an attack (badniks hurt him), his roll / Slide is
        # (the DLL's NoStomp*: native/src/NoSwapS3K.cpp)
        (B, "noStomp", 1, has("no_stomp")),
    ] + __import__("ninjutsu").s3k_fields(c) \
        + __import__("voltteccer").s3k_fields(c) \
        + __import__("pot_magic").s3k_fields(c)  # (Gilius' pot magic: tools/pot_magic.py, native/src/PotMagic.h)
        # (Joe Musashi's Ninjutsu: tools/ninjutsu.py, native/src/Ninjutsu.h; Pulseman's Voltteccer: tools/voltteccer.py, native/src/Voltteccer.h)


def head_numbers(variants, key):
    if len(variants) > HEAD_VARIANT_MAX:
        raise SystemExit(f"head_variants: more than {HEAD_VARIANT_MAX}")
    return [v[key] for v in variants] + [0] * (HEAD_VARIANT_MAX - len(variants))


def cycle_codes(moves):
    if len(moves) > CYCLE_MAX:
        raise SystemExit(f"ability_cycle: more than {CYCLE_MAX} moves")
    return [ab.CYCLE_MOVES[m][1] for m in moves] + [0] * (CYCLE_MAX - len(moves))


# Fields added after the first 23 characters' packages were made: written into a package's noswap_character.json only
# when not their default, so a new kind of move doesn't rewrite every other package's file (the DLL gives a field a file
# lacks its default: ExtraData.h). docs/plan-b-modular-characters.md "Pipeline follow-ups" 2.
OPTIONAL_FIELDS = {"puddleSlide", "puddleDrop", "puddleSpeed", "puddleTicks", "puddleMove", "puddleSteps", "puddleFrames",
                   "puddleSound", "breaksWalls", "shotSafe", "grappleY", "slideRunning",
                   "charge", "chargeAccel", "chargeGain", "chargeTop", "chargeFriction", "chargeBrake", "chargeStride", "chargeShove",
                   "sparkStore", "sparkSpeed", "sparkDiag", "sparkSkid", "sparkSkidFrames", "sparkGlowFirst",
                   "sparkGlowCount", "sparkGlowTo", "sparkGlow", "sparkStoreSound", "sparkSound",
                   "spinAttack", "spinFrames", "spinCooldown", "spinTicks", "spinGravity", "spinBounce", "spinBounceX",
                   "spinSound", "noBreathing", "fireImmune", "rideSpeed", "rideRise", "rideSound", "blastSound",
                   "highKick", "highKickWindup", "highKickRise", "highKickTicks", "highKickRecover", "highKickCooldown",
                   "highKickSound", "cycleCount", "cycleMoves", "copyHeads", "waterSwim", "swimStroke", "swimDelay",
                   "phaseWarp", "warpRange", "warpVanish", "warpGone", "warpAppear", "warpSound", "shotHang", "nukeAt",
                   "nukeHit", "nukeFlashCount", "nukeFlash", "nukeSound", "nukeReachX", "nukeReachY", "shotCost", "gearFrames", "groundSlide",
                   "rocketBurst", "rocketCharge", "rocketFrames", "rocketSpeed", "rocketDiag", "rocketSink",
                   "rocketSpinFrames", "rocketSpinTicks", "rocketChargeSound", "rocketSound",
                   "starGrab", "grabStep", "grabFrames", "retractFrames", "yankSpeed", "yankFrames", "yankRange", "bounceY",
                   "bounceX", "hangHop", "hangPush", "windupShow", "windupFull", "meteorSpeed", "meteorFrames", "grabSound",
                   "latchSound", "meteorSound", "headThrow", "headVariants", "headStep", "headFrames", "headSound",
                   "shotWhip", "swapCount", "swapSound", "swapIcon",
                   "floatLean", "floatLeanMax", "sink", "sinkTicks", "sinkSteps", "sinkFrames", "sinkUnderCount", "sinkUnder",
                   "sinkUnderTicks", "sinkMax", "sinkCooldown", "sinkSound",
                   "anchorThrow", "anchorSpeed", "anchorRise", "anchorHighSpeed", "anchorHighRise", "anchorGravity",
                   "anchorFrames", "anchorReturn", "anchorCooldown", "anchorSound", "waterWalk",
                   "grappleRefill", "grappleCooldown",
                   "treasureSense", "sensePause", "senseShow", "senseCooldown", "senseSound", "jewelThief",
                   "psychoGrab", "psychoReach", "psychoBehind", "psychoHeight", "psychoHold", "psychoThrow", "psychoTicks", "psychoSound",
                   "freeSwim", "swimSpeed", "swimAccel", "swimDrag", "swimTurn", "swimDirs", "swimCycle", "swimTicks",
                   "ramFrames", "ramSpeed", "ramCooldown", "ramCycle", "ramSound", "leapFrames", "leapTicks",
                   "freeFlight", "flySpeed", "flyAccel", "flyDrag", "flyTurn", "flyMeter", "flyDrain", "flyRefill", "flyRing",
                   "flySink", "flySwimFrames", "flySwimTicks", "drillFrames", "drillSpeed", "drillCooldown", "drillCost",
                   "drillSound", "loopPoints", "loopEvery", "loopClose", "loopMin", "loopHit"}
OPTIONAL_FIELDS |= {"meleeRunSpeed", "meleeRunBoost", "meleeRunFrames", "meleeUp", "meleeUpRings", "meleeUpFrames"}
OPTIONAL_FIELDS |= {"noStomp"}  # (no_stomp: only its packages have it)
OPTIONAL_FIELDS |= {"meleeRunSound", "meleeUpSound"}  # (melee_run / melee_up's own sounds: only where set)
OPTIONAL_FIELDS |= __import__("ninjutsu").S3K_FIELD_NAMES  # (Joe Musashi's Ninjutsu: only his package has them)
OPTIONAL_FIELDS |= __import__("pot_magic").S3K_FIELD_NAMES  # (Gilius' pot magic: only his package has them)
OPTIONAL_FIELDS |= __import__("voltteccer").S3K_FIELD_NAMES  # (Pulseman's Voltteccer: only his package has them)


NO_ABILITIES = {"abilities": []}
DEFAULTS = ability_fields(NO_ABILITIES)  # an extra with no moves: the loader's default for a field a package lacks
DEFAULT_OF = {name: value for _, name, _, value in DEFAULTS}


def s3k_json(e):
    """What the DLL needs of this extra in S3&K, for its package's noswap_character.json ("s3k"; the palette, base and
    roll flags are the character's own and go at the top level: build_packages.py)."""
    from build_s3k_art import special_colours  # (reads the extra's built Blue Spheres sheet)
    c = ab.ABILITIES.get(e["id"], NO_ABILITIES)
    return {
        "anim_base": BASES[e["base"]][1],  # where its own ability animations start in its 3K_Players/Extra.bin
        "special_palette": palette_json(special_colours(e)),  # the Blue Spheres ball's colours (bank 0 slot: RGB)
        "abilities": {name: value for _, name, _, value in ability_fields(c, e["name"])
                      if name not in OPTIONAL_FIELDS or value != DEFAULT_OF[name]},
        # its projectile (abilities.py "shot", S3&K's numbers: abilities.shot; the DLL's ShotData: ExtraData.h ReadShot),
        # without its art's recipe (build_s3k_shot.py); null: none
        "shot": ({k: v for k, v in ab.shot(e["id"], "s3k").items() if k not in ("art", "burn")} if ab.shot(e["id"], "s3k")
                 else None),
        # its second projectile (abilities.py "shot2": thrown with down + Y, Robotnik's Bomb Drop; only when it has one,
        # so the other packages' files don't change)
        **({"shot2": {k: v for k, v in ab.shot2(e["id"], "s3k").items() if k != "art"}} if ab.shot2(e["id"], "s3k")
           else {}),
        # its swap shots (monitor_swap's "swap_shots": John's sub-weapons; the DLL throws swap_shots[its swap index]), each
        # with its flames' animation in Shot.bin and their lifetime ("burn": build_s3k_shot.swap_anims); only when it has
        # them. Its "shot" above is the first of them.
        **({"swap_shots": [swap_json(s, burn) for s, (_, burn) in
                           zip(ab.swap_shots(e["id"], "s3k"), swap_anims(ab.swap_shots(e["id"], "s3k")))]}
           if ab.swap_shots(e["id"], "s3k") else {}),
        # a charge shot's flash colours (shot2 "input" "charge": Mega Man's; abilities.charge_palettes), only then
        **({"charge_palettes": [palette_json(p) for p in ab.charge_palettes(e["id"])]}
           if e["id"] in ab.charge_shots() else {}),
    }


def swap_anims(shots):
    from build_s3k_shot import swap_anims as anims
    return anims(shots)


def swap_json(s, burn_anim):
    """One swap shot for the DLL (ExtraData.h ReadShot): its numbers without its art; a burning one's flames as their
    animation in Shot.bin and their lifetime."""
    out = {k: v for k, v in s.items() if k not in ("art", "burn")}
    if "burn" in s:
        out.update(burn_anim=burn_anim, burn_lifetime=s["burn"]["lifetime"])
    return out


def palette_json(colours):
    """slot -> 0xRRGGBB as {"74": "#6C0090", ...}, in slot order (the DLL keeps the order)."""
    return {str(i): f"#{c:06X}" for i, c in sorted(colours.items())}


def c_default(t, count, value):
    if t == "str":
        return "nullptr"
    if count > 1:  # arrays: zeros
        assert not any(value), "array defaults are zeros"
        return "0"
    return ("true" if value else "false") if t == "bool" else str(value)


def check_legacy_keys():
    """Roster.h's LEGACY_KEYS (kinds 7-27, frozen) must be tools/extras.py's first 21 keys, in order: the menu archives
    (build_origins_menu.py) ship the first 21 characters' cards at slots 1-21 in extras.py's order (kind 6 + slot)."""
    header = (Path(__file__).resolve().parent.parent / "native" / "src" / "Roster.h").read_text()
    block = header[header.index("LEGACY_KEYS[] = {"):]
    legacy = re.findall(r'"([^"]+)"', block[:block.index("};")])
    # (a retired key in data/registry.json keeps its kind reserved with no character: e.g. "noswap.r25__")
    retired = set(__import__("registry").load()["retired"])
    legacy = [k for k in legacy if k not in retired]
    keys = [e["key"] for e in EXTRAS]
    if keys[:len(legacy)] != legacy:
        raise SystemExit(f"tools/extras.py's first {len(legacy)} keys differ from native/src/Roster.h LEGACY_KEYS: the "
                         "menu archives and the registry's frozen kinds 7-27 would disagree. New characters go after "
                         "them (and get their kinds at runtime).")


def main():
    check_legacy_keys()
    out = ["// Generated by tools/gen_s3k_header.py - don't edit. Only what is global lives here: each extra's own data",
           "// (palette, base, flags, ability numbers) comes from its package's noswap_character.json at startup",
           "// (native/src/ExtraData.h).", "#pragma once", "",
           "struct PaletteColour { unsigned char index; unsigned int rgb; };", "",
           "// (Which extras exist, and their kinds, is decided at runtime: native/src/Roster.h.)", "",
           "// The save screen's numbered picture names NoSwap ships (3K_Players/MenuPicture<j>.bin / .gif, j below this):",
           "// how many extras can have a save screen picture (extras.S3K_MENU_PICTURES)",
           f"static const int MENU_PICTURE_COUNT = {S3K_MENU_PICTURES};", "",
           "// The word a package script writes for the active extra's kind; the file hook serves such a script with the",
           "// kind in its place (extras.ACTIVE_KIND_TOKEN; ExtraData.h SubstituteActiveKind)",
           f'static const char ACTIVE_KIND_TOKEN[] = "{ACTIVE_KIND_TOKEN}";', "",
           "// Abilities: which moves, and their numbers (tools/abilities.py via gen_s3k_header.ability_fields). Physics,",
           "// glideSpeed, triple2 / triple3, doubleJumpScale and the surge's: multipliers in 1/1000; the sounds: files in",
           "// Data/SoundFX (nullptr: none). X(type, name, count, default); a field a package lacks gets its default.",
           "#define EXTRA_ABILITY_FIELDS(X) \\"]
    for t, name, count, value in DEFAULTS:
        default = c_default(t, count, value)
        out.append(f"    X({t}, {name}, {count}, {default}) \\")
    out.append("")
    ctype = {"bool": "bool", "int": "int", "str": "const char*"}
    out.append("struct ExtraAbilities {")
    for t, name, count, _ in DEFAULTS:
        out.append(f"    {ctype[t]} {name}{f'[{count}]' if count > 1 else ''};")
    out.append("};")
    path = Path(__file__).resolve().parent.parent / "native" / "build" / "extras_gen.h"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
