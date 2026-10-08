"""Pulseman's Voltteccer (abilities.py "voltteccer"), for Sonic 1/2 (Retro Engine v4 player script; abilities.py calls
v4_patch) and Sonic CD (build_soniccd.py calls cd_patch). The S3&K DLL's is native/src/Voltteccer.h, Mania's
native/mania/src/ManiaVoltteccer.h: the same rules and numbers (s3k_fields below feeds both).

The design (the user's, approved 2026-10-02):
- The charge: running on the ground (the plain ground state, his ground speed at least volt_run) for volt_charge frames
  in a row charges him (slower, or off the ground, before that: it starts over). Charged, he shows it: a palette flash
  (his reds in his own electric blues, the art's "charge_palettes" charge1, every other 4 frames: a runtime effect, the
  art untouched) and, in Sonic 1/2, the lightning shield's sparks every 16 frames (the game's own Lightning Spark); a
  sound as it's ready. He keeps it while he keeps moving: slower than volt_keep on the ground, or a hit, loses it.
- The launch: a jump press while charged (on the ground: the game's jump has just happened, it's turned into the
  launch; in mid-air, after a spring or a fall off a ledge, any jump press) turns him into the Voltteccer: the electric
  ball (slot 41: frames 0-3 its crackling loop, volt_ticks game frames each; 4-5 the small ball, as it starts and in its
  last frames) flying up-forward (45 degrees, the way he's going) at volt_speed, gravity off, for volt_frames.
- Rebounds: a wall reverses its speed across, a ceiling (or the stage's top edge) or a floor its speed up or down: the
  speed is kept (a reflection). Something that bounces him (a badnik he breaks, a boss, a bumper) reverses that axis too.
- Throughout it's an attack (the attack slot: badniks, monitors and bosses are hit, as by his jump) and nothing hurts
  him (the post-hit blink's rule, held without its flicker). At the end he pops back out into his jump ball with half
  its speed. A spring, an object taking him, a hit or death (any animation but the ball's) ends it at once, with their
  speed and pose. The game's own collision moves him all the while, so he never goes into a wall.
- No other mid-air move: the jump ability is none of Sonic's (the press only starts the launch when charged).

State (S1/S2 / CD):
  player.noswapAbility / NoSwap.Ability         the ball: frames left (0 / -1 none)
  NoSwap_glideVX, NoSwap_glideVY / NoSwap.RocketVX, NoSwap.RocketVY   its velocity (16.16)
  NoSwap_voltCharge / Object[5].Value5          the charge: 0..volt_charge-1 running; VOLT_FULL.. charged (counts
                                                on, wrapping, for the flash and sparks)
(S1/S2's NoSwap_voltCharge is packed into a Player_unusedValue: noswap_common.PACKED_VALUES.)
"""
import re
import sys

VOLT_FULL = 1000  # NoSwap_voltCharge from here on: charged (VOLT_FULL + its clock, 0..VOLT_CLOCK-1)
VOLT_CLOCK = 64
LOOP_FRAMES = 4  # slot 41: the ball's loop (0-3), then the small ball (4-5)
SMALL = 4
START_SMALL = 6  # game frames the small ball shows as it starts
END_SMALL = 24  # ...and in its last frames (it's about to end)
DIAG = 46341  # 1/sqrt(2) in 16.16 (abilities.DIAG)
V4 = {"ball": "ANI_NOSWAP_ATTACK", "blink": 3}
CD = {"ball": "ANI_NOSWAP_ATTACK", "blink": 2}
# the charge's sound (when it's ready) and the launch's, per engine (cfg overrides)
DEFAULTS = dict(volt_run=0x50000, volt_charge=75, volt_keep=0x20000, volt_speed=0x60000, volt_frames=180, volt_ticks=3,
                volt_sfx="Lightning Jump", volt_sfx_s3k="Global/LightningJump.wav", volt_sfx_cd="SFX_G_RELEASE",
                volt_ready_sfx="Lightning Shield", volt_ready_sfx_s3k="Global/LightningShield.wav",
                volt_ready_sfx_cd="SFX_G_SHIELD")
ALONGSIDE = ("voltteccer", "melee", "magnetic", "no_breathing", "fire_immune", "physics")  # (and a shot / shot2 on Y)
TOP_EDGE = 16  # px below the stage's top edge: its ceiling (as Heavy's Shine Spark: S1/S2/CD let a player rise past it)


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("voltteccer")


def cfg(i):
    """The extra's numbers, with their defaults (the S3&K DLL's and Mania's: s3k_fields)."""
    c = ab().ABILITIES[i]
    out = {k: c.get(k, v) for k, v in DEFAULTS.items()}
    clash = [a for a in c["abilities"] if a not in ALONGSIDE]
    if clash or c.get("ability_cycle"):
        sys.exit(f"voltteccer: extra {i}: the Voltteccer takes the jump ability, its state (noswapAbility, "
                 f"NoSwap_glideVX / VY) and slot 41 for itself: only {', '.join(ALONGSIDE)} alongside it "
                 f"({clash or 'ability_cycle'})")
    if not 0 < out["volt_charge"] < VOLT_FULL or out["volt_frames"] <= START_SMALL + END_SMALL:
        sys.exit(f"voltteccer: extra {i}: volt_charge 1-{VOLT_FULL - 1}, volt_frames over {START_SMALL + END_SMALL}")
    return out


def glow(i):
    """The charged flash's colours: {slot: 0xRRGGBB}, the art's charge_palettes charge1 (abilities.charge_palettes)."""
    return ab().charge_palettes(i)[0]


def ind(text, depth):
    t = "\t" * depth
    return "".join(t + l + "\n" if l.strip() else "\n" for l in text.rstrip("\n").split("\n"))


# ---------------------------------------------------------------- the update (after the player has moved)
def update_body(i, eng):
    """NoSwap_Volt<i>, every frame after the player has moved (S1/S2 NoSwap_AfterUpdate, CD likewise)."""
    c = cfg(i)
    total, ticks = c["volt_frames"], max(1, c["volt_ticks"])
    v4 = eng is V4
    sfx = f"PlaySfx(SfxName[{c['volt_sfx']}], false)" if v4 else f"PlaySfx({c['volt_sfx_cd']}, false)"
    ready = f"PlaySfx(SfxName[{c['volt_ready_sfx']}], false)" if v4 else f"PlaySfx({c['volt_ready_sfx_cd']}, false)"
    sparks = "".join(f"CreateTempObject(TypeName[Lightning Spark], 0, player.xpos, player.ypos)\n"
                     f"object[tempObjectPos].xvel = {x}0x20000\nobject[tempObjectPos].yvel = {y}0x20000\n"
                     for x, y in (("-", "-"), ("", "-"), ("-", ""), ("", ""))) if v4 else ""
    spark_lines = (f"""temp0 = NoSwap_voltCharge // charged: the lightning shield's sparks fly off him every 16 frames
temp0 &= 15
if temp0 == 0
{ind(sparks, 1)}end if
""" if v4 else "")
    states = ("CheckEqual(player.state, Player_State_Air)\ntemp0 |= checkResult\n"
              "CheckEqual(player.state, Player_State_Air_NoDropDash)\ntemp0 |= checkResult\n"
              "CheckEqual(player.state, Player_State_RollJump)\ntemp0 |= checkResult\n")
    return f"""if player.noswapAbility > 0 // the Voltteccer (tools/voltteccer.py): the ball
	if player.animation != {eng['ball']}
		player.noswapAbility = -1 // a spring, an object, a hit, death: over (their speed and pose stay)
	else
		if player.gravity == GRAVITY_GROUND // a floor: it rebounds up (the speed kept)
			if NoSwap_glideVY > 0
				FlipSign(NoSwap_glideVY)
			end if
			player.gravity = GRAVITY_AIR
			player.state = Player_State_Air
			player.angle = 0
			player.collisionMode = CMODE_FLOOR
			player.xvel = NoSwap_glideVX
			player.speed = NoSwap_glideVX
			player.yvel = NoSwap_glideVY
		else
			if NoSwap_glideVX != 0
				if player.xvel == 0 // a wall: it rebounds
					FlipSign(NoSwap_glideVX)
				end if
			end if
			if NoSwap_glideVY < 0
				temp0 = stage.curYBoundary1 // a ceiling, or the stage's top edge (the player could rise past it)
				temp0 += {TOP_EDGE}
				temp0 <<= 16
				if player.yvel == 0
					FlipSign(NoSwap_glideVY)
				else
					if player.ypos < temp0
						FlipSign(NoSwap_glideVY)
					end if
				end if
			end if
		end if
		player.noswapAbility--
		if player.noswapAbility == 0 // over: he pops back out into his jump ball, with half its speed
			player.noswapAbility = -1
			player.animation = ANI_JUMPING
			player.xvel = NoSwap_glideVX
			player.xvel /= 2
			player.speed = player.xvel
			player.yvel = NoSwap_glideVY
			player.yvel /= 2
		else
			if NoSwap_glideVX < 0
				player.direction = FACING_LEFT
			end if
			if NoSwap_glideVX > 0
				player.direction = FACING_RIGHT
			end if
			temp0 = {total} // the frame: the small ball as it starts and in its last frames, else the loop
			temp0 -= player.noswapAbility
			temp1 = false
			if temp0 < {START_SMALL}
				temp1 = true
			end if
			if player.noswapAbility <= {END_SMALL}
				temp1 = true
			end if
			if temp1 == true
				temp0 >>= 2
				temp0 &= 1
				temp0 += {SMALL}
			else
				temp0 /= {ticks}
				temp0 %= {LOOP_FRAMES}
			end if
			player.prevAnimation = player.animation // (the code picks the frame)
			player.frame = temp0
			player.animationTimer = 0
			if player.blinkTimer < {eng['blink']} // nothing hurts him (no flicker)
				player.blinkTimer = {eng['blink']}
			end if
		end if
	end if
end if
temp0 = false // the charge: running on the ground, fast enough
if player.gravity == GRAVITY_GROUND
	if player.state == Player_State_Ground
		temp1 = player.speed
		if temp1 < 0
			FlipSign(temp1)
		end if
		if temp1 >= {c['volt_run']:#x}
			temp0 = true
		end if
	end if
end if
temp2 = false // a hit, death: the charge is lost
if player.animation == ANI_HURT
	temp2 = true
end if
if player.animation == ANI_DYING
	temp2 = true
end if
if player.noswapAbility > 0
	temp2 = true
end if
if temp2 == true
	NoSwap_voltCharge = 0
else
	if NoSwap_voltCharge < {VOLT_FULL}
		if temp0 == true
			NoSwap_voltCharge++
			if NoSwap_voltCharge >= {c['volt_charge']} // charged
				NoSwap_voltCharge = {VOLT_FULL}
				{ready}
			end if
		else
			NoSwap_voltCharge = 0
		end if
	else
		NoSwap_voltCharge++ // charged: its clock (the flash, the sparks)
		if NoSwap_voltCharge >= {VOLT_FULL + VOLT_CLOCK}
			NoSwap_voltCharge = {VOLT_FULL}
		end if
		if player.gravity == GRAVITY_GROUND // slowing down loses it
			temp1 = player.speed
			if temp1 < 0
				FlipSign(temp1)
			end if
			if temp1 < {c['volt_keep']:#x}
				NoSwap_voltCharge = 0
			end if
		end if
	end if
end if
if NoSwap_voltCharge >= {VOLT_FULL}
{ind(spark_lines, 1)}	if player.jumpPress == true // the launch: a jump press while charged (the game's jump just happened, or in mid-air)
		temp0 = false
{ind(states, 2)}		if temp0 == true
			NoSwap_voltCharge = 0
			player.noswapAbility = {total}
			temp1 = 1 // the way he's going (or faces)
			if player.direction == FACING_LEFT
				temp1 = -1
			end if
			if player.xvel > 0
				temp1 = 1
			end if
			if player.xvel < 0
				temp1 = -1
			end if
			NoSwap_glideVX = {c['volt_speed'] * DIAG >> 16:#x}
			NoSwap_glideVX *= temp1
			NoSwap_glideVY = -{c['volt_speed'] * DIAG >> 16:#x}
			player.state = Player_State_Air
			player.gravity = GRAVITY_AIR
			player.angle = 0
			player.collisionMode = CMODE_FLOOR
			player.xvel = NoSwap_glideVX
			player.speed = NoSwap_glideVX
			player.yvel = NoSwap_glideVY
			player.animation = {eng['ball']}
			player.prevAnimation = player.animation
			player.frame = {SMALL}
			player.animationTimer = 0
			{sfx}
		end if
	end if
end if
"""


def velocity_body(i, eng):
    """NoSwap_VoltVel<i>: in the air state, after its gravity and air control, before he moves: the ball's velocity (its
    own; an axis something bounced him along, a badnik he broke, a boss, a bumper, reversed first)."""
    return f"""if player.noswapAbility > 0 // the Voltteccer (tools/voltteccer.py): its velocity, no gravity, no control
	if player.animation == {eng['ball']}
		if NoSwap_glideVX > 0 // something bounced him back: that way now
			if player.xvel < 0
				FlipSign(NoSwap_glideVX)
			end if
		else
			if player.xvel > 0
				FlipSign(NoSwap_glideVX)
			end if
		end if
		if NoSwap_glideVY > 0
			if player.yvel < 0
				FlipSign(NoSwap_glideVY)
			end if
		end if
		player.xvel = NoSwap_glideVX
		player.speed = NoSwap_glideVX
		player.yvel = NoSwap_glideVY
		player.timer = 0 // (no jump cap)
	end if
end if
"""


# ---------------------------------------------------------------- Sonic 1/2
def glow_functions(i):
    """Before / after his draw: the charged flash (charge1, every other 4 frames of the charge's clock), his own colours
    back from the Super glow's copy (banks 6 / 7) after (as abilities.charge_flash_draw)."""
    pal = glow(i)
    slots = sorted(pal)
    lo, n = slots[0], slots[-1] - slots[0] + 1
    sets = "".join(f"\t\tSetPaletteEntry(0, {s}, {rgb:#08x})\n\t\tSetPaletteEntry(1, {s}, {rgb:#08x})\n"
                   for s, rgb in sorted(pal.items()))
    return f"""// [NoSwap] Pulseman's charged Voltteccer flash (tools/voltteccer.py): before his draw
public function NoSwap_VoltGlow{i}
	if NoSwap_voltCharge >= {VOLT_FULL}
		temp0 = NoSwap_voltCharge
		temp0 >>= 2
		temp0 &= 1
		if temp0 == 1
{sets}		end if
	end if
end function


// after his draw: his colours back (the Super glow's copy)
public function NoSwap_VoltUnglow{i}
	if NoSwap_voltCharge >= {VOLT_FULL}
		CopyPalette(6, {lo}, 0, {lo}, {n})
		CopyPalette(7, {lo}, 1, {lo}, {n})
	end if
end function


"""


def v4_functions(i):
    return (f"// [NoSwap] Pulseman's Voltteccer (tools/voltteccer.py; the S3&K DLL's native/src/Voltteccer.h)\n"
            f"public function NoSwap_Volt{i}\n{ind(update_body(i, V4), 1)}end function\n\n\n"
            f"// [NoSwap] the Voltteccer's velocity, after the air state's gravity and air control (tools/voltteccer.py)\n"
            f"public function NoSwap_VoltVel{i}\n{ind(velocity_body(i, V4), 1)}end function\n\n\n"
            f"// [NoSwap] Pulseman's jump ability: nothing of Sonic's (a jump press while charged is the Voltteccer's: "
            f"NoSwap_Volt{i})\npublic function NoSwap_VoltJump{i}\n\tif player.jumpPress == true\n"
            "\t\tplayer.jumpAbilityState = 2\n\tend if\nend function\n\n\n" + glow_functions(i))


def _insert_in_function(t, head, after_line, text, what):
    """`text` right after `after_line` (or the head when None) in the function starting at `head`."""
    if t.count(head) != 1:
        sys.exit(f"voltteccer: {what}: {head.strip()!r} isn't there once")
    start = t.index(head) + len(head)
    if after_line:
        end = t.index("end function\n", start)
        at = t.find(after_line, start, end)
        if at < 0:
            sys.exit(f"voltteccer: {what}: {after_line.strip()!r} isn't in {head.strip()!r}")
        start = at + len(after_line)
    return t[:start] + text + t[start:]


def v4_patch(t, game=None):
    """The S1/S2 player script (after every other module's patches): his value (packed: noswap_common.PACKED_VALUES),
    his functions, the calls in NoSwap_AirAbilities (the velocity) and NoSwap_AfterUpdate (the rest), his jump ability
    (none of Sonic's), the charged flash around his draw, reserve lines."""
    from extras import EXTRAS, startup_case
    for i in ids():
        a = ab().ALIAS_OF[i]
        anchor = "public value Player_superState"
        if t.count(anchor) != 1:
            sys.exit("voltteccer: Player_superState isn't there once")
        t = t.replace(anchor, "// [NoSwap] Pulseman's Voltteccer charge (tools/voltteccer.py; packed: noswap_common."
                      "PACKED_VALUES)\nprivate value NoSwap_voltCharge = 0\n\n" + anchor, 1)
        head = "public function Player_HandleAmyHitbox\n"
        if t.count(head) != 1:
            sys.exit("voltteccer: Player_HandleAmyHitbox isn't there once")
        t = t.replace(head, v4_functions(i) + head)
        t = _insert_in_function(t, "public function NoSwap_AirAbilities\n", "\tCallFunction(NoSwap_TrySuper)\n",
                                f"\tif stage.playerListPos == {a} // [NoSwap] the Voltteccer's velocity (tools/voltteccer.py)\n"
                                f"\t\tCallFunction(NoSwap_VoltVel{i})\n\tend if\n", "air")
        t = _insert_in_function(t, "public function NoSwap_AfterUpdate\n", None,
                                f"\tif stage.playerListPos == {a} // [NoSwap] the Voltteccer (tools/voltteccer.py)\n"
                                f"\t\tCallFunction(NoSwap_Volt{i})\n\tend if\n", "after")
        extra = next(e for e in EXTRAS if e["id"] == i)
        case = t.index(startup_case(extra))
        line = t.find("= Player_Action_DblJumpSonic", case)
        if line < 0 or line > t.index("break", case):
            sys.exit("voltteccer: his startup case has no jump ability line (another jump ability took it?)")
        t = t[:line] + f"= NoSwap_VoltJump{i} // [NoSwap] voltteccer" + t[line + len("= Player_Action_DblJumpSonic"):]
        start = t.index("event ObjectDraw\n")
        end = t.index("end event\n", start)
        draw = t[start:end]
        if draw.count("\tDrawObjectAnimation()\n") != 1:
            sys.exit("voltteccer: expected 1 DrawObjectAnimation in ObjectDraw")
        pick = f"\tif stage.playerListPos == {a} // [NoSwap] the charged Voltteccer's flash\n\t\tCallFunction(NoSwap_VoltGlow{i})\n\tend if\n"
        back = f"\tif stage.playerListPos == {a} // [NoSwap] his colours back\n\t\tCallFunction(NoSwap_VoltUnglow{i})\n\tend if\n"
        draw = draw.replace("\tDrawObjectAnimation()\n", pick + "\tDrawObjectAnimation()\n" + back)
        t = t[:start] + draw + t[end:]
        anchor = "reserve function Player_ProcessUpdate\n"
        if t.count(anchor) != 1:
            sys.exit("voltteccer: the script's reserve block isn't there once")
        t = t.replace(anchor, "".join(f"reserve function {n}{i}\n" for n in
                                      ("NoSwap_Volt", "NoSwap_VoltVel", "NoSwap_VoltJump", "NoSwap_VoltGlow",
                                       "NoSwap_VoltUnglow")) + anchor)
    return t


# ---------------------------------------------------------------- S3&K and Mania (the package's numbers)
def s3k_fields(c):
    """The fields the DLL (native/src/Voltteccer.h) and the Mania mod (ManiaVoltteccer.h) read:
    gen_s3k_header.ability_fields appends them (OPTIONAL_FIELDS: only a voltteccer extra's package has them)."""
    on = "voltteccer" in c.get("abilities", [])
    get = lambda k: c.get(k, DEFAULTS[k]) if on else (None if isinstance(DEFAULTS[k], str) else 0)
    B, I, S = "bool", "int", "str"
    speed = get("volt_speed")
    return [
        # Pulseman's Voltteccer (tools/voltteccer.py): the run that charges it (speed, frames) and keeps it (speed); the
        # ball's speed overall (voltDiag per axis), frames, ticks per loop frame; its launch and charged sounds
        (B, "voltteccer", 1, on), (I, "voltRun", 1, get("volt_run")), (I, "voltCharge", 1, get("volt_charge")),
        (I, "voltKeep", 1, get("volt_keep")), (I, "voltSpeed", 1, speed),
        (I, "voltDiag", 1, speed * DIAG >> 16 if on else 0), (I, "voltFrames", 1, get("volt_frames")),
        (I, "voltTicks", 1, get("volt_ticks")), (S, "voltSound", 1, get("volt_sfx_s3k")),
        (S, "voltReadySound", 1, get("volt_ready_sfx_s3k")),
    ]


S3K_FIELD_NAMES = {name for _, name, _, _ in s3k_fields({"abilities": []})}


# ---------------------------------------------------------------- Sonic CD
CD_STORE = 6  # Object[6]: a reserved entity slot no script touches (docs/soniccd_map.md section 4): Value0 the charge,
# Value1 / Value2 the ball's velocity, Value3 its frames left (not NoSwap.Ability: NoSwap_AfterUpdate clears that on
# every landing, and the ball lands on every floor it rebounds off)
CD_NAMES = [("player.noswapAbility", f"Object[{CD_STORE}].Value3"), ("NoSwap_voltCharge", f"Object[{CD_STORE}].Value0"),
            ("NoSwap_glideVX", f"Object[{CD_STORE}].Value1"), ("NoSwap_glideVY", f"Object[{CD_STORE}].Value2"),
            ("player.animationTimer", "Player.AnimationTimer"), ("player.prevAnimation", "Player.PrevAnimation"),
            ("player.animation", "Player.Animation"), ("player.collisionMode", "Player.CollisionMode"),
            ("player.blinkTimer", "Player.BlinkTimer"), ("player.jumpPress", "Player.JumpPress"),
            ("player.direction", "Player.Direction"), ("player.gravity", "Player.Gravity"), ("player.state", "Player.State"),
            ("player.angle", "Player.Angle"), ("player.speed", "Player.Speed"), ("player.xvel", "Player.XVelocity"),
            ("player.yvel", "Player.YVelocity"), ("player.ypos", "Player.YPos"), ("player.frame", "Player.Frame"),
            ("stage.curYBoundary1", "Stage.YBoundary1"), ("checkResult", "CheckResult")]


def to_v3(text):
    out = []
    for line in text.split("\n"):
        for a, b in CD_NAMES:
            line = line.replace(a, b)
        out.append(re.sub(r"\btemp(\d)\b", r"TempValue\1", line))
    text = "\n".join(out)
    for bad in ("player.", "temp", "NoSwap_", "SfxName", "stage.", "object["):
        if re.search(rf"^[^/]*{re.escape(bad)}", text, re.M):
            sys.exit(f"voltteccer: the CD code still has {bad!r}")
    return text


def cd_velocity_body():
    """Before the air state runs (CD's NoSwap_AirAbilities): the ball's velocity, the state's gravity and rising drag
    taken off in advance (as build_soniccd.rocket_air); an axis something bounced him along reversed first."""
    s = CD_STORE
    return f"""if Object[{s}].Value3 > 0 // the Voltteccer (tools/voltteccer.py): its velocity, no gravity, no control
	if Player.Animation == ANI_NOSWAP_ATTACK
		if Object[{s}].Value1 > 0 // something bounced him back: that way now
			if Player.Speed < 0
				FlipSign(Object[{s}].Value1)
			end if
		else
			if Player.Speed > 0
				FlipSign(Object[{s}].Value1)
			end if
		end if
		if Object[{s}].Value2 > 0
			if Player.YVelocity < 0
				FlipSign(Object[{s}].Value2)
			end if
		end if
		Player.Left = false
		Player.Right = false
		Player.Timer = 0 // (no jump cap)
		Player.Speed = Object[{s}].Value1
		Player.YVelocity = Object[{s}].Value2
		Player.YVelocity -= Player.GravityStrength // (the air state adds it back)
		if Player.YVelocity > -0x40000 // (and its drag, rising: 1/32 of the speed)
			if Player.YVelocity < 0
				TempValue3 = Player.Speed
				TempValue3 >>= 5
				Player.Speed += TempValue3
			end if
		end if
	end if
end if
"""


def _dedent(text):
    """One tab off every line (the CD flash's lines, re-indented where each draw is)."""
    return "".join(l[1:] + "\n" for l in text.rstrip("\n").split("\n"))


def cd_patch(t):
    """The CD player script (build_soniccd.build_player_object, last): his functions, the calls in NoSwap_AfterUpdate
    and NoSwap_AirAbilities, the ball as an attack (Player_BadnikBreak for badniks, NoSwap_SurgeMonitor for monitors,
    NoSwap_ShotAttack for bosses: as NiGHTS' Drill Dash), and the charged flash around his draw (his own .act's charge1
    block, as build_soniccd.cd_charge_flash). No lightning sparks (CD has no such object)."""
    bc = sys.modules.get("build_soniccd") or __import__("build_soniccd")
    s = CD_STORE
    for i in ids():
        a = ab().ALIAS_OF[i]
        e = next(x for x in bc.EXTRAS if x["id"] == i)
        fns = (f"// [NoSwap] Pulseman's Voltteccer (tools/voltteccer.py; the S3&K DLL's native/src/Voltteccer.h)\n"
               f"function NoSwap_Volt{i}\n{ind(to_v3(update_body(i, CD)), 1)}end function\n\n\n"
               f"// [NoSwap] the Voltteccer's velocity, before the air state runs (tools/voltteccer.py)\n"
               f"function NoSwap_VoltVel{i}\n{ind(cd_velocity_body(), 1)}end function\n\n\n")
        decls = f"#function NoSwap_Volt{i}\n#function NoSwap_VoltVel{i}\n"
        for anchor, new in (("#function Player_ForceGrip\n", "#function Player_ForceGrip\n" + decls),
                            ("\nfunction Player_BadnikBreak\n", "\n" + fns + "function Player_BadnikBreak\n")):
            if t.count(anchor) != 1:
                sys.exit(f"voltteccer: CD anchor {anchor.strip()!r} isn't there once")
            t = t.replace(anchor, new)
        t = _insert_in_function(t, "\nfunction NoSwap_AfterUpdate\n", None,
                                f"\tif Stage.PlayerListPos == {a} // [NoSwap] the Voltteccer (tools/voltteccer.py)\n"
                                f"\t\tCallFunction(NoSwap_Volt{i})\n\tend if\n", "CD after")
        t = _insert_in_function(t, "\nfunction NoSwap_AirAbilities\n", None,
                                f"\tif Stage.PlayerListPos == {a} // [NoSwap] the Voltteccer's velocity (tools/voltteccer.py)\n"
                                f"\t\tCallFunction(NoSwap_VoltVel{i})\n\tend if\n", "CD air")
        ball = (f"if Stage.PlayerListPos == {a} // [NoSwap] Pulseman's Voltteccer: an attack (tools/voltteccer.py)\n"
                f"\tif Object[{s}].Value3 > 0\n\t\tif Player.Animation == ANI_NOSWAP_ATTACK\n\t\t\tCheckResult = true\n"
                "\t\tend if\n\tend if\nend if\n")
        anchor = "\t// you're invincible to badniks during the warping run\n\tif Warp.Timer > 0\n\t\tTempValue0 |= true\n\tend if\n"
        if t.count(anchor) != 1:
            sys.exit("voltteccer: CD's Player_BadnikBreak changed")
        t = t.replace(anchor, anchor + ind(ball.replace("CheckResult = true", "TempValue0 |= true"), 1))
        head = "\nfunction NoSwap_SurgeMonitor\n"
        if t.count(head) != 1:
            sys.exit("voltteccer: CD's NoSwap_SurgeMonitor isn't there once")
        t = t.replace(head, head + ind(ball, 1))
        head = "\nfunction NoSwap_ShotAttack\n"
        if t.count(head) != 1:
            sys.exit("voltteccer: CD's NoSwap_ShotAttack isn't there once")
        t = t.replace(head, head + "\tif Object[10].Value4 == false // (the player's own touch, not a shot's)\n"
                      + ind(ball, 2) + "\tend if\n")
        lo, hi = min(e["palette"]), max(e["palette"]) + 1
        glow_on = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] the charged Voltteccer's flash (tools/voltteccer.py)\n"
                   f"\t\tif Object[{s}].Value0 >= {VOLT_FULL}\n\t\t\tTempValue0 = Object[{s}].Value0\n"
                   "\t\t\tTempValue0 >>= 2\n\t\t\tTempValue0 &= 1\n\t\t\tif TempValue0 == 1\n"
                   f'\t\t\t\tLoadPalette("{bc.OWN_ACT}", 0, {lo}, {bc.CHARGE_ACT}, {bc.CHARGE_ACT + hi - lo})\n'
                   "\t\t\tend if\n\t\tend if\n\tend if\n")
        glow_off = (f"\tif Stage.PlayerListPos == {a} // [NoSwap] his own colours back\n"
                    f"\t\tif Object[{s}].Value0 >= {VOLT_FULL}\n"
                    f'\t\t\tLoadPalette("{bc.OWN_ACT}", 0, {lo}, {lo}, {hi})\n\t\tend if\n\tend if\n')
        start = t.index("sub ObjectDraw\n")
        end = t.index("end sub\n", start)
        draw = t[start:end]
        # every player draw in it (another extra's move may have wrapped the plain one in an if: Headdy's, Marine's);
        # the flash checks it's him
        draw, n = re.subn(r"^(\t+)DrawPlayerAnimation\(\)\n",
                          lambda m: ind(_dedent(glow_on), len(m.group(1))) + m.group(0)
                          + ind(_dedent(glow_off), len(m.group(1))), draw, flags=re.M)
        if n < 1:
            sys.exit("voltteccer: no DrawPlayerAnimation in CD's ObjectDraw")
        t = t[:start] + draw + t[end:]
    return t
