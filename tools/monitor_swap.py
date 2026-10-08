"""Monitor swap (abilities.py "monitor_swap"): a generic, per-player index that every item monitor the extra breaks moves
on to the next entry of its list, in all four games. What an entry *means* is up to the move reading the index: John
Morris' sub-weapons ("swap_shots": each entry names one of his shot configs, with its own motion and art; abilities.py
swap_shot_*), and next Dynamite Headdy's head power-ups (each entry a head variant).

Config (an extra's ABILITIES entry):
  "abilities": [..., "monitor_swap"],
  "monitor_swap": ["axe", "cross", "holy_water"],   the entries, in order; the first at each stage's start (a death or the
                                                    next act starts over too; so does CD's time travel)
  "swap_sfx": "Menu Select", "swap_sfx_s3k": "Global/Grab.wav", "swap_sfx_cd": "SFX_G_SELECT"   its sound (each optional)

The index, per engine (0 .. len - 1; after the last, the first again):
  Sonic 1/2  VALUE (NoSwap_swap, a player-script value; packed into a Player_unusedValue slot: noswap_common.PACKED_VALUES).
             v4_after(i), in the extra's NoSwap_AfterUpdate, finds each Broken Monitor it hasn't seen yet (the game turns
             a monitor into one when it breaks, whoever or whatever broke it: the player, his whip, a shot) and marks it
             (its MARK value, which no monitor script uses): one step per monitor. Self-contained: no shared script
             changes.
  Sonic CD   Object[CD_SLOT].Value2 (a reserved entity slot nothing else touches: docs/soniccd_map.md section 4). The
             shared Global/Monitor.txt counts every break in Object[CD_SLOT].Value0 (cd_monitor: after each "turn into a
             Broken Monitor" line, the player's and the shots'); cd_after(i) steps the index when the count moved
             (Object[CD_SLOT].Value1: the count it has seen). The engine clears the slot at each stage load.
  S3&K       the DLL's g_swap (native/src/NoSwapS3K.cpp, namespace shots): Hook_ItemBoxCheck steps it when a monitor's
             state changes in ItemBox_CheckHit (it broke) while this extra plays; 0 at each stage load. Its JSON fields:
             "swapCount" (the list's length) and "swapSound" (gen_s3k_header.py).

The HUD icon ("swap_icon": True, an extra with swap_shots): the current entry's shot art (its flight's first frame, the
pixels the shot itself draws) at the top middle of the screen, over a translucent black box (Castlevania's sub-weapon
box), in the HUD's layer, while that extra plays a normal stage (not while a title card or the act results are up, not
in special stages: their player scripts / the Blue Spheres runner are other objects). It follows the index at once.
  Sonic 1/2  the player script: its ObjectStartup (for that extra) loads the extra's first player sheet (shots_v4.SHEET,
             where the swap shots' frames are: shots_v4.SWAP_BOXES) and adds one SpriteFrame per entry (the Player
             Object type has no script frames of its own); NoSwap_AfterUpdate lists the player in draw layer 6 (the
             HUD's) as well as StageSetup's own listing (ICON_VALUE: 2 two listings to come, 1 only ours: he's hidden);
             its ObjectDraw's HUD-layer pass draws the box and the icon (DrawRect, DrawSpriteScreenXY) instead of him.
  Sonic CD   the same, with the player's own animation (shots_v3.swap_anims: entry k's flight, frame 0) drawn at the
             screen's centre (DrawPlayerAnimation, his place / animation put back after); the listing's state in
             Object[CD_SLOT].Value3.
  S3&K       the DLL wraps the HUD object's draw (NoSwapS3K.cpp shots::IconDraw): after the HUD, Shot.bin's animation
             g_swap frame 0 and the box, screen relative (ExtraData "swapIcon").
  Sizes: ICON_TOP px from the top, the box ICON_PAD_X / ICON_PAD_Y px round the largest entry's frame, ICON_ALPHA.

Reusing it for another move: read the index where the move starts (S1/S2 VALUE, CD cd_index(), S3&K shots::SwapIndex()),
and pick that entry's numbers / art. John's shots do it through abilities.swap_shots (S1/S2: one throw block per entry,
gated on the index; CD likewise; S3&K: ExtraData.swapShots[g_swap]).
"""
import sys

VALUE = "NoSwap_swap"  # Sonic 1/2 (packed: noswap_common.PACKED_VALUES)
MARK = "value30"  # Sonic 1/2: a Broken Monitor this has counted (no monitor script uses value30)
CD_SLOT = 12  # Sonic CD: Object[12].Value0 the breaks counted, Value1 the ones seen, Value2 the index


def ab():
    import abilities
    return abilities


def ids():
    return ab().with_ability("monitor_swap")


def entries(i):
    c = ab().ABILITIES[i]
    e = c.get("monitor_swap")
    if not isinstance(e, list) or not e or len(set(e)) != len(e):
        sys.exit(f"monitor_swap: extra {i}: \"monitor_swap\" must be a list of distinct entry names")
    if len(e) > 8:
        sys.exit(f"monitor_swap: extra {i}: at most 8 entries")
    return e


def count(i):
    return len(entries(i))


def icon(i):
    """The extra shows its current entry's icon at the top of the screen ("swap_icon": True; needs swap_shots, whose
    art the icon is)."""
    c = ab().ABILITIES.get(i, {})
    if not c.get("swap_icon"):
        return False
    if not ab().has(i, "monitor_swap") or not c.get("swap_shots"):
        sys.exit(f"monitor_swap: extra {i}: \"swap_icon\" needs \"monitor_swap\" with \"swap_shots\" (the icons are their art)")
    return True


def icon_frames(i, engine):
    """[(width, height, pivot x, pivot y)] of each entry's icon: its swap shot's first flight frame (as it's cut for the
    shot: build_s3k_shot.frames, the same pixels every engine pastes)."""
    import build_s3k_shot
    import extras
    e = next(x for x in extras.EXTRAS if x["id"] == i)
    out = []
    for s in ab().swap_shots(i, engine):
        im, px, py = build_s3k_shot.frames(s["art"], e)[0]
        out.append((im.width, im.height, px, py))
    return out


def icon_box(i, engine):
    """(width, height, centre y) of the icon's box: round the largest entry's frame."""
    f = icon_frames(i, engine)
    w = max(x[0] for x in f) + 2 * ICON_PAD_X
    h = max(x[1] for x in f) + 2 * ICON_PAD_Y
    return w, h, ICON_TOP + h // 2


# ---------------------------------------------------------------- Sonic 1/2
ICON_VALUE = "NoSwap_swapIcon"  # Sonic 1/2 (packed: noswap_common.PACKED_VALUES): the HUD icon's listings this frame
ICON_TOP, ICON_PAD_X, ICON_PAD_Y, ICON_ALPHA = 8, 4, 3, 160  # the icon's box: its top, padding round the art, opacity
V4_VALUES = f"""public value {VALUE} = 0 // monitor_swap: the entry the extra's broken monitors have moved it on to (tools/monitor_swap.py)
public value {ICON_VALUE} = 0 // monitor_swap's HUD icon (swap_icon): 2 / 1 listed this frame (tools/monitor_swap.py)
"""


def v4_after(i):
    """In the extra's NoSwap_AfterUpdate: every Broken Monitor not yet counted moves the index on (and is marked)."""
    n = count(i)
    sfx = ab().ABILITIES[i].get("swap_sfx")
    return f"""foreach (TypeName[Broken Monitor], arrayPos0, ACTIVE_ENTITIES) // monitor_swap (tools/monitor_swap.py): each monitor broken
	if object[arrayPos0].{MARK} == 0
		object[arrayPos0].{MARK} = 1
		{VALUE}++
		if {VALUE} >= {n}
			{VALUE} = 0
		end if
""" + (f"\t\tPlaySfx(SfxName[{sfx}], false)\n" if sfx else "") + """	end if
next
""" + (v4_icon_after() if icon(i) else "")


def v4_icon_after():
    """In the extra's NoSwap_AfterUpdate (swap_icon): unless a title card (slot 11) or the act results (slot 30) are up,
    or there's no HUD (slot 9), the player is listed in draw layer 6 (the HUD's) too: his ObjectDraw there draws the
    icon. ICON_VALUE 2: StageSetup lists him as well (he's visible: it only lists a visible player), first; 1: ours only."""
    return v4_hud_listing(ICON_VALUE, "swap_icon (tools/monitor_swap.py): the sub-weapon's icon, drawn in the HUD's layer "
                                      "(ObjectDraw)")


def v4_hud_listing(value, comment):
    """The HUD-layer pass's listing (Sonic 1/2), for any extra's screen-space drawing (swap_icon's icon; Rouge's Treasure
    Sense marker, tools/treasure_sense.py): `value` (a packed player-script value) 2 / 1 as v4_icon_after says, 0 unlisted."""
    return f"""{value} = 0 // {comment}
if object[11].type != TypeName[Title Card] // (SLOT_TITLECARD)
	if object[30].type != TypeName[Act Finish] // (SLOT_ACTFINISH)
		if object[9].type == TypeName[HUD] // (SLOT_HUD)
			{value} = 1
			if object.visible == true
				{value} = 2
			end if
			AddDrawListEntityRef(6, object.entityPos)
		end if
	end if
end if
"""


def v4_hud_pass(t, alias, value, draw, comment, tag):
    """The player script's ObjectDraw with the HUD-layer pass (Sonic 1/2): on the listing v4_hud_listing(value) made,
    `draw` (lines at one tab) runs instead of his own draw; StageSetup's listing (first) draws him as usual. The whole
    draw is skipped on that pass (temp7: `draw` mustn't change it)."""
    start = t.index("event ObjectDraw\n")
    end = t.index("end event\n", start)
    if t.count("event ObjectDraw\n") != 1:
        sys.exit(f"{tag}: expected one ObjectDraw")
    body = t[start + len("event ObjectDraw\n"):end]
    head = f"""	temp7 = false // [NoSwap] {comment}
	if stage.playerListPos == {alias}
		if {value} == 2 // StageSetup's listing (first): him; ours (the HUD's layer) next
			{value} = 3
		else
			if {value} > 0 // ours (3), or ours only (1: he's hidden)
				{value} = 0
				temp7 = true
""" + "".join("\t\t\t\t" + l + "\n" if l.strip() else "\n" for l in draw.rstrip("\n").split("\n")) + """			end if
		end if
	end if
	if temp7 == false
"""
    body = "".join("\t" + l if l.strip() else l for l in body.splitlines(True))
    return t[:start] + "event ObjectDraw\n" + head + body + "\tend if\n" + t[end:]


def v4_patch(t):
    """The S1/S2 player script (after every other module's patches): each swap_icon extra's icon frames (ObjectStartup)
    and its HUD-layer draw (ObjectDraw: the whole draw is skipped on that pass)."""
    import shots_v4
    for i in ids():
        if not icon(i):
            continue
        a = ab().ALIAS_OF[i]
        start = t.index("event ObjectStartup\n")
        end = t.index("end event\n", start)
        if t.count("event ObjectStartup\n") != 1 or "SpriteFrame(" in t[start:end]:
            sys.exit("monitor_swap: the player script's ObjectStartup has script frames (the icons expect to be 0 and up)")
        frames = []
        for k, ((w, h, px, py), (s, base, _, _)) in enumerate(zip(icon_frames(i, "v4"), ab().swap_layout(i))):
            x, y, bw, bh = shots_v4.SWAP_BOXES[base - shots_v4.SWAP_FRAME]
            frames.append(f"\t\tSpriteFrame({px}, {py}, {w}, {h}, {x + bw // 2 + px}, {y + bh // 2 + py}) // {k}: "
                          f"{entries(i)[k]}'s icon (its first flight frame)\n")
        t = t.replace("event ObjectStartup\n", "event ObjectStartup\n"
                      f"\tif stage.playerListPos == {a} // [NoSwap] swap_icon (tools/monitor_swap.py): the sub-weapon "
                      "icons, the swap shots' own frames on his first player sheet\n"
                      f'\t\tLoadSpriteSheet("{shots_v4.SHEET}")\n' + "".join(frames) + "\tend if\n", 1)
        bw, bh, cy = icon_box(i, "v4")
        t = v4_hud_pass(t, a, ICON_VALUE, f"""temp0 = screen.xcenter
temp0 -= {bw // 2}
DrawRect(temp0, {ICON_TOP}, {bw}, {bh}, 0, 0, 0, {ICON_ALPHA})
DrawSpriteScreenXY({VALUE}, screen.xcenter, {cy})""", "swap_icon (tools/monitor_swap.py): his HUD-layer listing draws the icon, "
                        "not him", "monitor_swap")
    return t


# ---------------------------------------------------------------- Sonic CD
def cd_index():
    return f"Object[{CD_SLOT}].Value2"


def cd_monitor(t):
    """Global/Monitor.txt (shared): count every break (the player's and, after shots_v3.monitor, a shot's)."""
    line = "Object.Type = TypeName[Broken Monitor]"
    lines = t.split("\n")
    n = 0
    for k in reversed(range(len(lines))):
        if lines[k].strip() == line:
            ind = lines[k][:len(lines[k]) - len(lines[k].lstrip("\t"))]
            lines[k + 1:k + 1] = [f"{ind}Object[{CD_SLOT}].Value0++ // [NoSwap] a monitor broke: monitor_swap counts it "
                                  "(tools/monitor_swap.py)"]
            n += 1
    if n < 2:
        sys.exit(f"monitor_swap: CD Monitor.txt: {n} breaks found (expected the player's and a shot's)")
    return "\n".join(lines)


def cd_after(i):
    """In the extra's CD NoSwap_AfterUpdate block: a break counted since last frame moves the index on."""
    n = count(i)
    sfx = ab().ABILITIES[i].get("swap_sfx_cd")
    s = f"Object[{CD_SLOT}]"
    return ([f"if {s}.Value0 != {s}.Value1 // monitor_swap (tools/monitor_swap.py): a monitor broke",
             f"\t{s}.Value1 = {s}.Value0", f"\t{s}.Value2++", f"\tif {s}.Value2 >= {n}", f"\t\t{s}.Value2 = 0", "\tend if"]
            + ([f"\tPlaySfx({sfx}, false)"] if sfx else []) + ["end if"] + (cd_icon_after() if icon(i) else []))


def cd_icon_after():
    """In the extra's CD NoSwap_AfterUpdate block (swap_icon): as v4_icon_after (the title card in slot 20, the results
    in 30, the HUD in 24), the state in Object[CD_SLOT].Value3."""
    return cd_hud_listing(f"Object[{CD_SLOT}].Value3", "swap_icon (tools/monitor_swap.py): the sub-weapon's icon, drawn in "
                          "the HUD's layer (ObjectDraw)")


def cd_hud_listing(s, comment):
    """The HUD-layer pass's listing in CD (cd_icon_after's, for any extra's screen-space drawing: Rouge's Treasure Sense
    marker, tools/treasure_sense.py): `s` a free reserved-slot value (2 / 1 as in v4_hud_listing)."""
    return [f"{s} = 0 // {comment}",
            "if Object[20].Type != TypeName[Title Card]", "\tif Object[30].Type != TypeName[ActFinish]",
            "\t\tif Object[24].Type == TypeName[HUD]", f"\t\t\t{s} = 1", "\t\t\tif Player.Visible == true",
            f"\t\t\t\t{s} = 2", "\t\t\tend if", "\t\t\tSetDrawListEntityRef(Object.EntityNo, 6, Screen[6].DrawListSize)",
            "\t\t\tScreen[6].DrawListSize++", "\t\tend if", "\tend if", "end if"]


def cd_patch(t):
    """The CD player script (after every other module's patches): each swap_icon extra's HUD-layer draw (sub ObjectDraw:
    the whole draw is skipped on that pass): the box, and the current entry's flight animation, frame 0, drawn as him at
    the screen's centre (his animation, frame, place, facing, rotation and visibility put back after)."""
    import shots_v3
    for i in ids():
        if not icon(i):
            continue
        a = ab().ALIAS_OF[i]
        s = f"Object[{CD_SLOT}].Value3"
        bw, bh, cy = icon_box(i, "cd")
        draw = f"""TempValue0 = Screen.CenterX
				TempValue0 -= {bw // 2}
				DrawRect(TempValue0, {ICON_TOP}, {bw}, {bh}, 0, 0, 0, {ICON_ALPHA})
				TempValue0 = Player.Animation
				TempValue1 = Player.Frame
				TempValue2 = Player.XPos
				TempValue3 = Player.YPos
				TempValue4 = Player.Direction
				TempValue5 = Player.Rotation
				TempValue6 = Player.Visible
				Player.Animation = Object[{CD_SLOT}].Value2 // the entry's flight (shots_v3.swap_anims)
				Player.Animation *= 2
				Player.Animation += {shots_v3.ANI_SWAP}
				Player.Frame = 0
				Player.Direction = 0
				Player.Rotation = 0
				Player.Visible = true
				Player.XPos = Screen.XOffset
				Player.XPos += Screen.CenterX
				Player.XPos *= 65536
				Player.YPos = Screen.YOffset
				Player.YPos += {cy}
				Player.YPos *= 65536
				DrawPlayerAnimation()
				Player.Animation = TempValue0
				Player.Frame = TempValue1
				Player.XPos = TempValue2
				Player.YPos = TempValue3
				Player.Direction = TempValue4
				Player.Rotation = TempValue5
				Player.Visible = TempValue6"""
        draw = "\n".join(l[4:] if l.startswith("\t" * 4) else l for l in draw.split("\n"))
        t = cd_hud_pass(t, a, s, draw, "swap_icon (tools/monitor_swap.py): his HUD-layer listing draws the icon, not him",
                        "monitor_swap")
    return t


def cd_hud_pass(t, alias, s, draw, comment, tag):
    """CD's sub ObjectDraw with the HUD-layer pass (v4_hud_pass's): `draw` (TempValue7 left alone) instead of his draw on
    the listing cd_hud_listing(s) made."""
    if t.count("sub ObjectDraw\n") != 1:
        sys.exit(f"{tag}: expected one CD sub ObjectDraw")
    start = t.index("sub ObjectDraw\n")
    end = t.index("end sub\n", start)
    body = t[start + len("sub ObjectDraw\n"):end]
    head = f"""	TempValue7 = false // [NoSwap] {comment}
	if Stage.PlayerListPos == {alias}
		if {s} == 2 // the engine's listing (first): him; ours (the HUD's layer) next
			{s} = 3
		else
			if {s} > 0 // ours (3), or 1: he's hidden
				{s} = 0
				TempValue7 = true
""" + "".join("\t\t\t\t" + l + "\n" if l.strip() else "\n" for l in draw.rstrip("\n").split("\n")) + """			end if
		end if
	end if
	if TempValue7 == false
"""
    body = "".join("\t" + l if l.strip() else l for l in body.splitlines(True))
    return t[:start] + "sub ObjectDraw\n" + head + body + "\tend if\n" + t[end:]
