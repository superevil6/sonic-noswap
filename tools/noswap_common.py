"""Helpers shared by the per-game NoSwap build scripts (build_sonic1.py, build_sonic2.py, ...).

Patching: every edit is anchored on exact text and fails loudly if the anchor moved.
Saving: extras' save routines (Retro Engine v4 script source) and helpers to wire them in.
Art: sheet-copy loading and title-screen recolouring.
"""
import re
import sys
from pathlib import Path

from extras import EXTRAS, aliases, ball_animation, case_labels, palette_lines, tinted_palette, ui_manifest


# Extras' save slots in Sonic's save array (see SAVE_FUNCTIONS); S1 itself uses entries 0-45
SAVE_BASE = 1024


SAVE_SLOTS = 3


def copy_name(sheet):
    stem, ext = sheet.rsplit(".", 1)
    return f"{stem}_NoSwap.{ext}"


def title_remap(img, src_palette, title, skip=range(208, 222)):
    """Recolour an indexed image to the nearest colours the title screen actually uses.

    `skip`: slots the title rewrites at runtime (Sonic 1's Logo.txt sets 208-221 for the title
    character), which would make the art change colour.
    """
    tpal = title.getpalette()
    used = [i for _, i in title.getcolors(256) if i != 0 and i not in skip]
    rgb = lambda pal, i: tuple(pal[3 * i:3 * i + 3])
    lut = {}
    for _, i in img.getcolors(256):
        if i == 0:
            continue
        c = rgb(src_palette, i)
        lut[i] = min(used, key=lambda j: sum((a - b) ** 2 for a, b in zip(c, rgb(tpal, j))))
    return img.point(lambda i: lut.get(i, 0))


def alphabet_name(font, alphabet, text, space=9):
    """A name image from a game's title-card letters (`alphabet`: letter -> (x, y, width), 16 high)."""
    from PIL import Image
    width = sum(space if c == " " else alphabet[c][2] + 1 for c in text) - 1
    img = Image.new("P", (width, 16), 0)
    cx = 0
    for c in text:
        if c == " ":
            cx += space
            continue
        x, y, w = alphabet[c]
        img.paste(font.crop((x, y, x + w, y + 16)), (cx, 0))
        cx += w + 1
    return img


def arrow(direction):
    """5x9 yellow arrow with a black outline, in title palette slots (154 yellow, 181 black)."""
    from PIL import Image
    img = Image.new("P", (5, 9), 0)
    for y in range(9):
        reach = 4 - abs(4 - y)  # 0..4..0
        for x in range(reach + 1):
            px = x if direction == "right" else 4 - x
            edge = x == reach or y in (0, 8)
            img.putpixel((px, y), 181 if edge else 154)
    return img


SHEET_ROWS = 512  # RSDKv4 (S1/S2) draws only a sheet's first 512 rows: a frame reaching row 512 or below draws nothing


def startup_frames(text, name):
    """The SpriteFrames a script's ObjectStartup defines before its first `if` or `switch` (Origins' platform blocks
    only), as (x, y, w, h) sheet rects in frame-number order: frames every character gets, under the same numbers."""
    text = text.replace("\r\n", "\n")
    start = text.index("event ObjectStartup")
    body = text[start:text.index("\nend event", start)]
    rects, plat = [], None
    for line in body.split("\n")[1:]:
        l = re.sub(r"//.*$", "", line).strip()
        if l.startswith("#platform:"):
            plat = l.split(":", 1)[1].strip()
        elif l == "#endplatform":
            plat = None
        elif plat not in (None, "USE_ORIGINS"):
            continue
        elif l.startswith(("if ", "switch ")):
            break
        else:
            m = re.fullmatch(r"SpriteFrame\(([^)]*)\)", l)
            if m:
                _, _, w, h, x, y = (int(v) for v in m.group(1).split(","))
                rects.append((x, y, w, h))
    if not rects:
        sys.exit(f"{name}: no unconditional SpriteFrames in ObjectStartup")
    return rects


# Room every package's UI box keeps whatever the extras' art needs, as (left, top, right, bottom) around the element's
# pivot: a box is the union of every extra's art, so without it a character with a longer name than anyone's grows the
# box, which moves it (and the boxes packed after it) on every package's sheet and in NoSwap's shared scripts
# (2026-09-27: MECHA SONIC, 1 px wider than METAL SONIC, rewrote all 21 other packages' S1 Display_NoSwap.gif). Names are
# what grow; a name within this room changes no other package. act_name: the act results name (S1 and S2 title-card
# letters, right-aligned at the pivot: 12 or so letters); life_name: the HUD name tag (9 or so letters; Rayan C.'s
# letters, tools/hud_font.py: SPARKSTER is 65 px).
UI_RESERVE = {"act_name": (-192, 0, 0, 16), "life_name": (0, 0, 72, 7)}


class UiSheets:
    """The extra's UI art on the "<name>_NoSwap.gif" sheet copies, in fixed boxes (docs/plan-b-modular-characters.md,
    step 3b item 3). An object type draws from one sheet (the last its ObjectStartup loads, for all its frames), so a
    copy is the game's sheet with boxes added: one box per UI element (life icon, name tag, 1-UP icon, ...), the same
    for every extra. Every shared script uses one fixed frame per element for "the extra"; each character package
    ships its own copies of the sheets (same names, size and layout) with its art in the boxes, and NoSwap's own copies
    have the boxes empty (transparent). The scripts load a copy only while an extra plays (use_sheet_copy): the
    vanilla characters keep the game's sheets.

    A box is the union, over every extra, of that element's art placed at its pivot (the offset its frame had when
    every extra had a frame of its own), so a frame's pivot is the box's corner and each extra's art sits in the box
    where its old pivot put it: every pixel lands where it did. Art is pasted unchanged, padded with transparency.

    The engine draws only a sheet's first 512 rows (SHEET_ROWS), so no copy may be taller. A copy is normally the whole
    game sheet with the boxes packed in rows below it. A game sheet with no room below (keep: {game sheet: [(x, y, w,
    h), ...]}) gets a copy holding only those rects of it, at their own places (the game frames the loading script
    draws for an extra: startup_frames), with the boxes packed around them; the rest of the game's art is left out.

    sheets: {game sheet: [element keys]}; art(key, extra) -> indexed image; pivot(key, image) -> (x, y) offset."""

    def __init__(self, sprites_in, sheets, art, pivot, keep=None, reserve=None):
        from PIL import Image
        self.sprites_in, self.sheets, self.keep = sprites_in, sheets, keep or {}
        reserve = UI_RESERVE if reserve is None else reserve
        self.art = {(k, e["n"]): art(k, e) for keys in sheets.values() for k in keys for e in EXTRAS}
        self.at = {kn: pivot(kn[0], img) for kn, img in self.art.items()}  # (key, n) -> the art's pivot offset
        self.box, self.size = {}, {}  # key -> (left, top, width, height, sheet x, sheet y); sheet -> (w, h)
        if self._kit_layout():
            return
        for sheet, keys in sheets.items():
            orig = Image.open(sprites_in / sheet)
            rects = {}
            for k in keys:
                spans = [(self.at[(k, e["n"])], self.art[(k, e["n"])].size) for e in EXTRAS]
                if k in reserve:  # (room kept for a longer name: UI_RESERVE)
                    rl, rt, rr, rb = reserve[k]
                    spans.append(((rl, rt), (rr - rl, rb - rt)))
                left, top = min(p[0] for p, _ in spans), min(p[1] for p, _ in spans)
                right, bottom = max(p[0] + s[0] for p, s in spans), max(p[1] + s[1] for p, s in spans)
                rects[k] = (left, top, right - left, bottom - top)
            order = sorted(keys, key=lambda k: (-rects[k][3], keys.index(k)))  # tallest first
            for k in keys:
                if rects[k][2] > orig.width:
                    sys.exit(f"UI box '{k}' ({rects[k][2]} px) is wider than {sheet}")
            if sheet in self.keep:
                kept = self.keep[sheet]
                for x, y, w, h in kept:
                    if x < 0 or y < 0 or x + w > orig.width or y + h > min(orig.height, SHEET_ROWS):
                        sys.exit(f"{sheet}: kept rect {(x, y, w, h)} is outside its first {SHEET_ROWS} rows")
                # each box at the lowest, then leftmost, free corner (1 px from anything else)
                taken = [(x, y, x + w, y + h) for x, y, w, h in kept]
                for k in order:
                    w, h = rects[k][2:]
                    xs = sorted({0} | {r[2] + 1 for r in taken})
                    ys = sorted({0} | {r[3] + 1 for r in taken})
                    spot = next(((x, y) for y in ys for x in xs
                                 if x + w <= orig.width and y + h <= SHEET_ROWS
                                 and all(x + w + 1 <= r[0] or r[2] + 1 <= x or y + h + 1 <= r[1] or r[3] + 1 <= y
                                         for r in taken)), None)
                    if spot is None:
                        sys.exit(f"{sheet}: no room for UI box '{k}' ({w}x{h}) in {SHEET_ROWS} rows")
                    self.box[k] = rects[k] + spot
                    taken.append((spot[0], spot[1], spot[0] + w, spot[1] + h))
                self.size[sheet] = (orig.width, max(r[3] for r in taken))
            else:
                # shelf-pack the boxes into rows below the game's contents (1 px apart)
                x, y, shelf = 0, orig.height + 1, 0
                for k in order:
                    w, h = rects[k][2:]
                    if x + w > orig.width:
                        x, y, shelf = 0, y + shelf + 1, 0
                    self.box[k] = rects[k] + (x, y)
                    x += w + 1
                    shelf = max(shelf, h)
                self.size[sheet] = (orig.width, y + shelf + 1)
            w, h = self.size[sheet]
            if h > SHEET_ROWS or w & (w - 1):
                sys.exit(f"{copy_name(sheet)} would be {w}x{h}: the engine draws only {SHEET_ROWS} rows (and widths "
                         "are powers of two). List the game frames its scripts draw for an extra in `keep`")

    def layout_key(self):
        return f"{Path(self.sprites_in).parent.parent.name}:{'|'.join(sorted(self.sheets))}"

    def _kit_layout(self):
        """The Creator Kit (tools/noswap_cli/kit.py): the boxes are the released core's (data/kit/ui_layout.json, from
        the build the kit was packed from: its shared scripts draw them), not the union over the kit's own characters.
        Each character's art must fit in them. -> True if used."""
        import os
        f = Path(__file__).resolve().parent.parent / "data" / "kit" / "ui_layout.json"
        if not os.environ.get("NOSWAP_KIT") or not f.is_file():
            return False
        import json
        snap = json.loads(f.read_text()).get(self.layout_key())
        if snap is None:
            sys.exit(f"the kit has no NoSwap core layout for {self.layout_key()} (data/kit/ui_layout.json)")
        self.box = {k: tuple(v) for k, v in snap["box"].items()}
        self.size = {k: tuple(v) for k, v in snap["size"].items()}
        for sheet, keys in self.sheets.items():
            for k in keys:
                left, top, bw, bh = self.box[k][:4]
                for e in EXTRAS:
                    (px, py), (w, h) = self.at[(k, e["n"])], self.art[(k, e["n"])].size
                    if px < left or py < top or px + w > left + bw or py + h > top + bh:
                        sys.exit(f"{e['art'].name}: its '{k}' art ({w}x{h} at {px},{py} from its pivot) doesn't fit "
                                 f"the NoSwap core's box for it ({bw}x{bh} at {left},{top}) on {copy_name(sheet)}: "
                                 "make it smaller (docs/character-json.md, the UI sizes)")
        return True

    def frame(self, key, comment=""):
        """The fixed SpriteFrame of an element's box."""
        left, top, w, h, x, y = self.box[key]
        return f"SpriteFrame({left}, {top}, {w}, {h}, {x}, {y})" + (f" // {comment}" if comment else "")

    def image(self, sheet, extra=None):
        """The sheet copy: the game's sheet with the boxes below, holding `extra`'s art (None: empty boxes)."""
        from PIL import Image
        orig = Image.open(self.sprites_in / sheet)
        img = Image.new("P", self.size[sheet], 0)
        img.putpalette(orig.getpalette())
        if sheet in self.keep:  # only the game's frames the loading script draws for an extra, where they were
            for x, y, w, h in self.keep[sheet]:
                img.paste(orig.crop((x, y, x + w, y + h)), (x, y))
        else:
            img.paste(orig, (0, 0))
        for k in self.sheets[sheet] if extra else ():
            left, top, _, _, x, y = self.box[k]
            px, py = self.at[(k, extra["n"])]
            img.paste(self.art[(k, extra["n"])], (x + px - left, y + py - top))
        return img

    def write(self, sprites_out, extra=None):
        """Write every sheet copy under `sprites_out` (a game's Data/Sprites folder: NoSwap's or a package's)."""
        from gifio import save_sheet
        for sheet in self.sheets:
            out = sprites_out / copy_name(sheet)
            out.parent.mkdir(parents=True, exist_ok=True)
            save_sheet(self.image(sheet, extra), out)


def extra_block(indent, lines, default=None, comment="the extra's own art, in its package's fixed boxes"):
    """`if` the playing character is an extra (any: ID 7 and up), `lines`; else `default` lines, if given."""
    out = [f"{indent}if stage.playerListPos >= {EXTRA_MIN_ID} // [NoSwap] {comment}"]
    out += [f"{indent}\t{l}" for l in lines]
    if default is not None:
        out += [f"{indent}else"] + [f"{indent}\t{l}" for l in default]
    return out + [f"{indent}end if"]


def before_sonic_switch(t, pick, total, lines, name, comment="the extra's own art, in its package's fixed boxes"):
    """extra_block(`lines`) right before a chosen `switch stage.playerListPos` whose first case is Sonic's (numbered in
    file order, `total` of them). Extras have no case in it, so for them the block's frames take the switch's place."""
    found = sonic_first_switches(t)
    if len(found) != total:
        sys.exit(f"'{name}': found {len(found)} Sonic-first switches (expected {total})")
    src = t.split("\n")
    i = found[pick]
    src[i:i] = extra_block(line_indent(src[i]), lines, comment=comment)
    return "\n".join(src)


def use_sheet_copy(t, sheet, expected=1):
    """In ObjectStartup, load the sheet copy instead of `sheet` while an extra character is playing."""
    start = t.index("event ObjectStartup")
    end = t.index("end event", start)
    body = t[start:end]
    lines = body.split("\n")
    hits = [i for i, l in enumerate(lines) if l.strip() == f'LoadSpriteSheet("{sheet}")']
    if len(hits) != expected:
        sys.exit(f"sheet copy '{sheet}': found {len(hits)} loads in ObjectStartup (expected {expected})")
    for i in reversed(hits):
        ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i:i + 1] = [
            f"{ind}if stage.playerListPos >= PLAYER_EXTRA1_A // [NoSwap] same sheet plus the extra's art (its package's copy)",
            f'{ind}\tLoadSpriteSheet("{copy_name(sheet)}")',
            f"{ind}else",
            f'{ind}\tLoadSpriteSheet("{sheet}")',
            f"{ind}end if",
        ]
    return t[:start] + "\n".join(lines) + t[end:]


# NoSwap_flags: the one public value the shared S1/S2 scripts read to learn about the playing extra (the player script
# sets it: abilities.py extra_startup, power_surge_after). One bit each; the shared scripts test a bit with
# GetBit(<scratch>, NoSwap_flags, <bit number>). Plain numbers, not aliases: public names share a small engine table.
FLAG_BITS = {
    "knux": 0,       # value 1: built on Knuckles (his wall breaking, his lower underwater jump)
    "tails": 1,      # value 2: built on Tails (nothing shared reads it yet)
    "magnetic": 2,   # value 4: pulls rings in without a shield
    "no_breathing": 3,  # value 8: never drowns (Metal Sonic)
    "surging": 4,    # value 16: a Power Surge is on: monitors break at her touch
    "breaks_walls": 5,  # value 32: breaks walls like Knuckles, not built on him (abilities.py breaks_walls: Heavy)
    "fire_immune": 6,  # value 64: fire never hurts (abilities.py fire_immune: Blaze): the lava tiles' own shield tests
    # value 128: Heavy's charge is past his top speed (abilities.py charge, set each frame): enemies can't hurt him
    # (noswap_common.juggernaut). It must stay the TOP bit: the enemy scripts test it as NoSwap_flags >= 128, which
    # needs no temp and leaves checkResult alone
    "juggernaut": 7,
}
EXTRA_MIN_ID = "PLAYER_EXTRA1_A"  # (7 once literal_extra_ids runs) any character ID from here up is an extra


def line_indent(line):
    return line[: len(line) - len(line.lstrip("\t"))]


def free_temp(lines, i, name, every=False):
    """A temp variable (temp7 down to temp0) that nothing in the event or function holding line i mentions, directly or
    through an alias, nor any function of this script it calls (followed through their calls). A scratch value set and
    read right there then can't disturb the script. Stops if that block is a function (its callers could keep a temp
    across the call) or if every temp is taken. every=True: the list of all the free ones (highest first) instead."""
    text = "\n".join(lines)
    starts = [k for k in range(i + 1) if re.match(r"(event \w+|(?:public|private) function \w+)\s*$", lines[k])]
    if not starts:
        sys.exit(f"{name}: line {i + 1} is outside any event")
    start = starts[-1]
    if not lines[start].startswith("event "):
        sys.exit(f"{name}: line {i + 1} is inside a function ({lines[start]}): pick a scratch value by hand")
    end = next(k for k in range(i, len(lines)) if re.match(r"end (event|function)", lines[k]))
    bodies, seen, todo = ["\n".join(lines[start:end])], set(), re.findall(r"CallFunction\((\w+)\)", "\n".join(lines[start:end]))
    while todo:
        fn = todo.pop()
        if fn in seen:
            continue
        seen.add(fn)
        m = re.search(rf"^(?:public|private) function {fn}\s*\n(.*?)^end function", text, flags=re.M | re.S)
        if m:
            bodies.append(m.group(1))
            todo += re.findall(r"CallFunction\((\w+)\)", m.group(1))
    body = "\n".join(bodies)
    # a water-colour call (water_colours_after_loads) sets its temp and the called function only reads it, right there:
    # that temp holds nothing afterwards, so it stays free for the code around it
    body = re.sub(rf"^[ \t]*{WATER_TEMP} = \d+ //[^\n]*\n[ \t]*CallFunction\({WATER_FUNCTION}\)[ \t]*$", "", body,
                  flags=re.M)
    aliases = re.findall(r"^(?:public|private) alias (temp\d)\s*:\s*(\S+)", text, flags=re.M)
    free = []
    for n in range(7, -1, -1):
        names = [f"temp{n}"] + [a for tmp, a in aliases if tmp == f"temp{n}"]
        if not any(re.search(rf"(?<![\w.]){re.escape(x)}(?![\w])", body) for x in names):
            free.append(f"temp{n}")
    if every:
        return free
    if not free:
        sys.exit(f"{name}: no free temp around line {i + 1}")
    return free[0]


def flag_test(ind, flag, scratch, comment, value="true"):
    """Lines opening `if <extra has NoSwap_flags bit>` (value "false": if it hasn't); the caller closes it."""
    bit = FLAG_BITS[flag]
    return [f"{ind}GetBit({scratch}, NoSwap_flags, {bit}) // [NoSwap] NoSwap_flags bit {bit} (value {1 << bit}): {comment}",
            f"{ind}if {scratch} == {value}"]


def extras_take_case(lines, i, name, target="PLAYER_SONIC_A", temp=None):
    """Line i is `switch <expr>`: the switch gets <expr> with any extra's ID (7 and up) replaced by `target`, so the
    extra takes that character's case (case labels must be constants: one per extra doesn't scale). The value goes
    through a free temp (free_temp; callers changing several switches pick each one's before changing any, since the
    scratch lines added for one would make the temp look taken for the next). Changes `lines` in place."""
    ind = line_indent(lines[i])
    m = re.match(r"switch (\S+)\s*(//.*)?$", lines[i].strip())
    if not m:
        sys.exit(f"{name}: line {i + 1} isn't a switch: {lines[i]!r}")
    temp = temp or free_temp(lines, i, name)
    who = {"PLAYER_SONIC_A": "Sonic", "PLAYER_TAILS_A": "Tails", "PLAYER_KNUCKLES_A": "Knuckles"}.get(target, target)
    lines[i:i + 1] = [
        f"{ind}{temp} = {m.group(1)} // [NoSwap] any extra (ID {EXTRA_MIN_ID} and up) takes {who}'s case",
        f"{ind}if {temp} >= {EXTRA_MIN_ID}",
        f"{ind}\t{temp} = {target}",
        f"{ind}end if",
        f"{ind}switch {temp}",
    ]


def extras_take_case_at(t, anchor, name, expected=1, target="PLAYER_SONIC_A"):
    """extras_take_case for the switch that starts each occurrence of `anchor` (text beginning with the switch line)."""
    count = t.count(anchor)
    if count != expected:
        sys.exit(f"patch '{name}': anchor found {count} times (expected {expected})")
    lines = t.split("\n")
    at, pos = [], t.find(anchor)
    while pos >= 0:
        if pos and t[pos - 1] != "\n":
            sys.exit(f"patch '{name}': the anchor must start a line")
        at.append(t.count("\n", 0, pos))
        pos = t.find(anchor, pos + 1)
    temps = {i: free_temp(lines, i, name) for i in at}
    for i in reversed(at):
        extras_take_case(lines, i, name, target, temps[i])
    return "\n".join(lines)


def extras_skip_switch(t, start, frames, comment, name):
    """The `switch` starting at offset `start` of t runs only for the game's own characters: any extra (ID
    EXTRA_MIN_ID and up) gets `frames` (lines, no indent) instead. For a switch that picks per-character art no extra
    can share (the results lines naming the player), so no case label is needed for extras."""
    lines = t.split("\n")
    i = t.count("\n", 0, start)
    if (start and t[start - 1] != "\n") or not lines[i].strip().startswith("switch "):
        sys.exit(f"{name}: offset {start} doesn't start a switch line")
    ind = line_indent(lines[i])
    end = next((k for k in range(i + 1, len(lines)) if lines[k] == f"{ind}end switch"), None)
    if end is None:
        sys.exit(f"{name}: no end switch")
    body = [("\t" + l if l.strip() and not l.startswith("#") else l) for l in lines[i:end + 1]]
    lines[i:end + 1] = ([f"{ind}if stage.playerListPos >= {EXTRA_MIN_ID} // [NoSwap] any extra: {comment}"]
                        + [f"{ind}\t{f}" for f in frames] + [f"{ind}else"] + body + [f"{ind}end if"])
    return "\n".join(lines)


def sonic_first_switches(t, expr="stage.playerListPos"):
    """Line numbers of every `switch <expr>` whose first case (past blank and comment lines) is PLAYER_SONIC_A."""
    lines = t.split("\n")
    found = []
    for i, line in enumerate(lines):
        if line.strip().split("//")[0].strip() != f"switch {expr}":
            continue
        j = i + 1
        while lines[j].strip() == "" or lines[j].strip().startswith("//"):
            j += 1
        if lines[j].strip().split("//")[0].strip() == "case PLAYER_SONIC_A":
            found.append(i)
    return found


def extras_as_sonic(t, pick, total, name, expr="stage.playerListPos"):
    """extras_take_case (Sonic's) for chosen `switch <expr>`s whose first case is Sonic's, numbered in file order:
    `total` is how many such switches the file must have, `pick` the ones to change (None: all)."""
    found = sonic_first_switches(t, expr)
    if len(found) != total:
        sys.exit(f"'{name}': found {len(found)} Sonic-first switches on {expr} (expected {total})")
    lines = t.split("\n")
    chosen = sorted(range(total) if pick is None else pick, reverse=True)
    temps = {k: free_temp(lines, found[k], name) for k in chosen}
    for k in chosen:
        extras_take_case(lines, found[k], name, temp=temps[k])
    return "\n".join(lines)


KNUX_CHECKS = ("if stage.playerListPos == PLAYER_KNUCKLES_A", "if player[currentPlayer].character == PLAYER_KNUCKLES")


def knux_like(t, walls=False):
    """Stage scripts: each Knuckles check (walls he breaks, his lower underwater jump) gets a copy of its
    Knuckles branch for extras built on Knuckles (NoSwap_flags bit 0), placed after the whole if, so it wins
    over an else branch. Checks inside USE_STANDALONE blocks are skipped (Origins doesn't compile them).
    walls=True (the breakable walls): a second copy for extras that break walls like him without being built on him
    (NoSwap_flags bit 5, abilities.py breaks_walls: Heavy)."""
    lines = t.split("\n")
    hits, platform = [], None
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("#platform:"):
            platform = s.split(":", 1)[1].strip()
        elif s == "#endplatform":
            platform = None
        elif s in KNUX_CHECKS and platform != "USE_STANDALONE":
            hits.append(i)
    if not hits:
        sys.exit("knux_like: no Knuckles check found")
    scratch = {i: free_temp(lines, i, "knux_like") for i in hits}  # (before any insertion)
    for i in reversed(hits):
        ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        j, branch_end = i + 1, None
        while not (lines[j].startswith(ind + "end if") and not lines[j].startswith(ind + "\t")):
            if lines[j] == ind + "else" and branch_end is None:
                branch_end = j
            j += 1
        body = [l for l in lines[i + 1:branch_end if branch_end is not None else j] if not l.strip().startswith("#")]

        def test(flag, comment):  # (a per-player check: player 1 only, as the game's own; a sidekick Tails isn't him)
            opening = flag_test(ind, flag, scratch[i], comment)
            if lines[i].strip() == KNUX_CHECKS[1]:
                opening[1:1] = [f"{ind}if player[currentPlayer].isSidekick == true // (player 1 only, not a sidekick)",
                                f"{ind}\t{scratch[i]} = false", f"{ind}end if"]
            return opening
        lines[j + 1:j + 1] = (test("knux", "an extra built on Knuckles") + body + [f"{ind}end if"]
                              + (test("breaks_walls", "an extra that breaks walls like Knuckles")
                                 + body + [f"{ind}end if"] if walls else []))
    return "\n".join(lines)


# Heavy's full charge (FLAG_BITS "juggernaut", set by abilities.charge_after while the charge is past his top speed):
# enemies can't hurt him. In the enemies' and bosses' own scripts (never hazards: spikes, crushers, lava, lasers...),
# each hurt call (Player_Hit, Player_ProjectileHit, Player_FireHit, Player_LightningHit) is skipped for player 1 then;
# at the JUGGERNAUT_BREAKS sites (a badnik that's only spiky in one state: the same object breaks in the other) it
# breaks it instead, through the game's own Player_BadnikBreak (his charge is an attack animation: ATTACK_ANIMS). Bosses
# take his hits already (Player_CheckHit counts attack animations). A sidekick is hurt as before.
JUGGERNAUT_SCRIPTS = {
    "Sonic1u": ["Enemies/", "Mission/BallHogBomb2.txt", "Mission/Caterkiller2.txt", "Mission/ReviveCaterkiller.txt",
                "GHZ/WreckingBall.txt", "SYZ/Eggman.txt", "MZ/BossFireball.txt", "SBZ/PlasmaBall.txt"],
    "Sonic2u": ["Enemies/", "ARZ/EggmanArrow.txt", "ARZ/EggmanHammer.txt", "CNZ/EggmanBomb.txt", "CNZ/EggmanClaw.txt",
                "CPZ/ChemicalBall.txt", "CPZ/ChemicalDrop.txt", "DEZ/DERBomb.txt", "DEZ/DERFoot.txt", "DEZ/DERHand.txt",
                "DEZ/DERLeg.txt", "DEZ/DeathEggRobot.txt", "DEZ/MechaSonic.txt", "DEZ/MechaSonicSpike.txt",
                "EHZ/EggmanDrill.txt", "HPZ/Eggman.txt", "HPZ/EggmanMine.txt", "HTZ/Eggman.txt", "HTZ/EggmanFireball1.txt",
                "HTZ/EggmanFireball2.txt", "MCZ/BossRock.txt", "MCZ/EggmanDrill.txt", "MPZ/EggmanBalloon.txt",
                "MPZ/EggmanLaser.txt", "OOZ/EggmanCannon.txt", "OOZ/EggmanFlame.txt", "OOZ/EggmanHarpoon.txt",
                "OOZ/EggmanLaser.txt", "WFZ/EggmanLaser.txt", "WFZ/EggmanPlatform.txt", "WFZ/TurretBullet.txt"],
}
# Whole scripts whose hurt calls break the badnik instead (S1's Roller, rolled up; S2's Flasher, lit up)
JUGGERNAUT_BREAKS = {"Enemies/Roller.txt", "Enemies/Flasher.txt"}
JUGGERNAUT_HURTS = ("Player_Hit", "Player_ProjectileHit", "Player_FireHit", "Player_LightningHit")


def juggernaut_scripts(base, game):
    """The scripts juggernaut patches (JUGGERNAUT_SCRIPTS, the folders' ones with a hurt call)."""
    out = []
    for entry in JUGGERNAUT_SCRIPTS[game]:
        for path in sorted(base.glob(entry + "*.txt")) if entry.endswith("/") else [base / entry]:
            text = path.read_bytes().decode("utf-8", errors="ignore")
            if any(f"CallFunction({f})" in text for f in JUGGERNAUT_HURTS) or "].state = Player_State_GotHit" in text:
                out.append(path.relative_to(base).as_posix())
            elif not entry.endswith("/"):
                sys.exit(f"juggernaut: {entry} has no hurt call")
    return out


def juggernaut(t, rel):
    """One enemy / boss script: its hurt calls skipped (or the badnik broken) during Heavy's full charge (see above)."""
    if max(FLAG_BITS.values()) != FLAG_BITS["juggernaut"] or FLAG_BITS["juggernaut"] != 7:
        sys.exit("juggernaut: NoSwap_flags >= 128 needs the juggernaut bit to be bit 7, the top one")
    tag = "[NoSwap] Heavy's full charge (NoSwap_flags bit 7): enemies can't hurt him"
    lines = t.split("\n")

    def standalone_lines():  # (Origins doesn't compile these)
        out, platform = set(), None
        for k, l in enumerate(lines):
            c = l.strip()
            if c.startswith("#platform:"):
                platform = c.split(":", 1)[1].strip()
            elif c == "#endplatform":
                platform = None
            elif platform == "USE_STANDALONE":
                out.add(k)
        return out
    standalone = standalone_lines()
    n = 0
    # a hurt written out (CPZ's boss drops): the if straight above it is wrapped in the test (last first: indices hold)
    for k in reversed(range(len(lines))):
        if lines[k].strip() != "player[currentPlayer].state = Player_State_GotHit" or k in standalone:
            continue
        ind = line_indent(lines[k])[:-1]
        if not lines[k - 1].startswith(ind + "if ") or line_indent(lines[k - 1]) != ind:
            sys.exit(f"juggernaut: {rel}: a written-out hurt not straight under an if: look at it")
        end = next(i for i in range(k + 1, len(lines)) if line_indent(lines[i]) == ind and lines[i].strip()
                   and not lines[i].lstrip().startswith("//"))
        if lines[end].strip() != "end if":
            sys.exit(f"juggernaut: {rel}: a written-out hurt's if has an else: look at it")
        lines[end + 1:end + 1] = [f"{ind}end if"]
        lines[k - 1:k - 1] = [f"{ind}if NoSwap_flags < 128 // {tag}"]
        n += 1
    standalone = standalone_lines()
    out = []
    for k, l in enumerate(lines):
        m = re.fullmatch(r"CallFunction\((\w+)\)", l.strip())
        if not m or m.group(1) not in JUGGERNAUT_HURTS or k in standalone:
            out.append(l)
            continue
        ind, c = line_indent(l), l.strip()
        other = ["\telse", "\t\tCallFunction(Player_BadnikBreak) // (it breaks instead)"] if rel in JUGGERNAUT_BREAKS else []
        out += [f"{ind}{x}" for x in [f"if NoSwap_flags < 128 // {tag}", f"\t{c}", "else",
                                      "\tif player[currentPlayer].isSidekick == true // (a sidekick is hurt as before)",
                                      f"\t\t{c}"] + other + ["\tend if", "end if"]]
        n += 1
    if not n:
        sys.exit(f"juggernaut: {rel}: no hurt call found")
    if any("isSidekick" in l for l in out) and not any(re.match(r"\s*(private|public) alias .*: player\.isSidekick\b", l)
                                                       for l in out):
        # the sidekick test's field: each script declares it itself (as the player's own: object.value16 in Sonic 1 and
        # 2), and most enemy scripts never did ("Operand not found: player.isSidekick", Sonic 1's BuzzBomberShot)
        out.insert(0, "private alias object.value16 : player.isSidekick // [NoSwap] (for Heavy's full charge)")
    return "\n".join(out)


def add_juggernaut_builders(builders, base, game):
    """juggernaut into a game builder's BUILDERS (after their own builders and the shots' copies: a copy's hurt calls
    are gone by then), only in a build with an extra that has the charge (Heavy)."""
    import abilities
    if not abilities.with_ability("charge"):
        return builders
    for rel in juggernaut_scripts(base, game):
        first = builders.get(rel)
        builders[rel] = (lambda t, rel=rel, first=first: juggernaut(first(t) if first else t, rel))
    return builders


def patch(text, anchor, replacement, name):
    count = text.count(anchor)
    if count != 1:
        sys.exit(f"patch '{name}': anchor found {count} times (expected 1)")
    return text.replace(anchor, replacement)


def patch_n(text, anchor, replacement, name, expected):
    count = text.count(anchor)
    if count != expected:
        sys.exit(f"patch '{name}': anchor found {count} times (expected {expected})")
    return text.replace(anchor, replacement)


def guard_blocks(t, function, line_re, before, after, expected, name):
    """In `function` (its header line, up to the next "end function"), wrap the innermost block holding each line
    matching `line_re` (the lines around it at its indent or deeper) between `before` and `after` (lists of lines,
    indented to the block's `if`; the block goes one tab deeper). Used by extras.py "no_roll" to keep a roll start
    from running for those extras."""
    lines = t.split("\n")
    start = lines.index(function)
    end = next(k for k in range(start, len(lines)) if lines[k].startswith("end function"))
    hits = [k for k in range(start, end) if re.match(line_re, lines[k])]
    if len(hits) != expected:
        sys.exit(f"{name}: found {len(hits)} matching lines in {function!r} (expected {expected})")

    def depth(line):
        return len(line) - len(line.lstrip("\t"))
    for k in reversed(hits):
        ind = depth(lines[k])
        s, e = k, k + 1
        while lines[s - 1].strip() == "" or depth(lines[s - 1]) >= ind:
            s -= 1
        while lines[e].strip() == "" or depth(lines[e]) >= ind:
            e += 1
        while lines[s].strip() == "":
            s += 1
        while lines[e - 1].strip() == "":
            e -= 1
        outer = "\t" * (ind - 1)
        lines[s:e] = ([outer + "\t" + l for l in before] + ["\t" + l if l.strip() else l for l in lines[s:e]]
                      + [outer + "\t" + l for l in after])
    return "\n".join(lines)


def add_case(text, anchor, name, only=None):
    """Add every extra's case label (or those passing `only`) directly after `anchor`."""
    line = anchor.split("\n")[-1]
    indent = line[: len(line) - len(line.lstrip("\t"))]
    return patch(text, anchor, anchor + "\n" + case_labels(indent, only=only).rstrip("\n"), name)


def own_cases(indent, body, comment="extra character's own art"):
    """`case` blocks for every extra, each with its own body (list of lines) and a break."""
    out = []
    for e in EXTRAS:
        out.append(f"{indent}case {e['alias']} // [NoSwap] {comment}")
        out += [f"{indent}\t{l}" for l in body(e)] + [f"{indent}\tbreak", ""]
    return out


def gameconfig_palette(path):
    """The global palette (slots 0-95) from a v4 GameConfig.bin: two strings, then 96 RGB colours."""
    d = open(path, "rb").read()
    p = 0
    for _ in range(2):
        p += 1 + d[p]
    return [tuple(d[p + i * 3:p + i * 3 + 3]) for i in range(96)]


def act_palette(path):
    d = open(path, "rb").read()
    return [tuple(d[i * 3:i * 3 + 3]) for i in range(len(d) // 3)]


# Water palettes (docs/plan-b-modular-characters.md step 3b item 5). The underwater palettes and flashes are whole-bank
# loads, which would blank the extra's own colour slots in that bank. After each one the stage setup script calls this
# public function of the player script, with which load it was (its place in the game's list of loads) in WATER_TEMP.
# Each package's player script writes its extra's colours, shifted the way that load shifts the game's; NoSwap's own
# does nothing (the vanilla characters use only the game's colours).
WATER_FUNCTION = "NoSwap_WaterColours"
WATER_TEMP = "temp7"  # free at every call site (checked by water_colours_after_loads); the function only reads it


def palette_bank_loads(t):
    """(line number, file, bank) of each LoadPalette of a whole bank other than 0."""
    hits = []
    for i, l in enumerate(t.split("\n")):
        m = re.match(r'\s*LoadPalette\("([^"]+)", (\d+), 0, 0, 256\)', l)
        if m and m.group(2) != "0":
            hits.append((i, m.group(1), int(m.group(2))))
    return hits


def water_colours_after_loads(t, loads, expected, name):
    """After each whole-bank palette load, call WATER_FUNCTION with the load's number in `loads` (the game's list of
    (file, bank)) in WATER_TEMP. Run it before other patches that take scratch temps in the same event (they can then
    take WATER_TEMP too: see free_temp), so the check proves the game's own code there never names WATER_TEMP."""
    lines = t.split("\n")
    hits = palette_bank_loads(t)
    if len(hits) != expected:
        sys.exit(f"water colours '{name}': found {len(hits)} bank loads (expected {expected})")
    for i, file, bank in hits:
        if (file, bank) not in loads:
            sys.exit(f"water colours '{name}': {file} into bank {bank} isn't in the game's list of loads")
        if WATER_TEMP not in free_temp(lines, i, name, every=True):
            sys.exit(f"water colours '{name}': {WATER_TEMP} isn't free around line {i + 1}")
    for i, file, bank in reversed(hits):
        ind = line_indent(lines[i])
        lines[i + 1:i + 1] = [
            f"{ind}{WATER_TEMP} = {loads.index((file, bank))} // [NoSwap] the extra's own colours in this palette too "
            f"(its player script's)",
            f"{ind}CallFunction({WATER_FUNCTION})"]
    return "\n".join(lines)


def kept_extras():
    """The extras whose own parts this player script build has (NOSWAP_KEEP: tools/build_packages.py). None when unset
    (the full build of every extra's moves, which build_packages.py then replaces)."""
    import os
    keep = os.environ.get("NOSWAP_KEEP")
    if keep is None:
        return None
    ids = {int(x) for x in keep.split(",") if x.strip() and x.strip() != "none"}
    return [e for e in EXTRAS if e["id"] in ids]


def water_colours(extra, loads, normal, palette_dir):
    """{load number: {slot: colour}}: the extra's own colours as each load shows them (`normal`: the game's global
    palette, RGB list, that the loads' colours are based on)."""
    out = {}
    for n, (file, _) in enumerate(loads):
        tinted = act_palette(f"{palette_dir}/{file}")
        out[n] = tinted_palette(extra, normal[:74], tinted[:74])
    return out


def water_colours_function(t, loads, normal, palette_dir):
    """The player script's WATER_FUNCTION (before its first event): the kept extra's colours for each load; nothing
    for NoSwap's own (NOSWAP_KEEP=none) or the full build (see kept_extras)."""
    kept = [e for e in (kept_extras() or []) if e["palette"]]
    if len(kept) > 1:
        sys.exit(f"{WATER_FUNCTION}: a player script with several extras' colours ({[e['n'] for e in kept]})")
    body = []
    if kept:
        e = kept[0]
        colours = water_colours(e, loads, normal, palette_dir)
        body += [f"\tif stage.playerListPos >= {EXTRA_MIN_ID}",
                 f"\t\tswitch {WATER_TEMP}"]
        for n, (file, bank) in enumerate(loads):
            body.append(f"\t\tcase {n} // {file} into bank {bank}")
            body += palette_lines(e, bank, "\t\t\t", colours[n]).rstrip("\n").split("\n")
            body.append("\t\t\tbreak")
        body += ["\t\tend switch", "\tend if"]
    text = (f"// [NoSwap] Called by the stage setups after each whole-bank palette load (underwater, flashes), with the "
            f"load's number in {WATER_TEMP}: the\n// extra's own colours in that bank too (noswap_common.WATER_FUNCTION). "
            f"Reads {WATER_TEMP} only.\npublic function {WATER_FUNCTION}\n"
            + "".join(l + "\n" for l in body) + "end function\n\n\n")
    at = t.index("\nevent ") + 1
    return t[:at] + text + t[at:]


EXTRA_ALIAS = (
    "public alias 6 : PLAYER_AMY_TAILS_A\n"
    "// [NoSwap] Extra characters get their own IDs. 4 is reserved by the game (Knuckles & Tails), so extras start at 7.\n"
    + aliases()
)


SAVE_FUNCTIONS = """// [NoSwap] Save routines for extra characters. Extras play in no-save mode as far as the game's own
// save code is concerned, and every save point calls one of these instead (see insert_save_calls).
// They only touch arrayPos1 and temp0, which the game's save code at those points overwrites anyway.
//
// Origins keeps one save per character and credits stage progress to whichever character it was
// last told is playing (NOTIFY_PLAYER_SET). The extras' records live in Sonic's save data, so each
// save switches Origins to Sonic and reloads Sonic's data before writing the record.
// KNOWN ISSUE: that also credits the extra's stage progress to Sonic's own save.
public function NoSwap_BeginSave
	CallNativeFunction2(NotifyCallback, NOTIFY_PLAYER_SET, PLAYER_SONIC)
	ReadSaveRAM()
end function


public function NoSwap_EndSave
	// Origins crashes if told an ID it doesn't know (tested 2026-09-25), so it stays on Sonic for now
	WriteSaveRAM()
end function


public function NoSwap_GetRecord
	arrayPos1 = stage.playerListPos
	arrayPos1 -= PLAYER_EXTRA1_A
	arrayPos1 *= NOSWAP_SLOTS
	arrayPos1 += saveRAM[NOSWAP_ACTIVE_SLOT]
	arrayPos1--
	arrayPos1 <<= 3
	arrayPos1 += NOSWAP_SAVE_BASE
end function


public function NoSwap_SaveProgress
	if stage.playerListPos >= PLAYER_EXTRA1_A
		CallFunction(NoSwap_BeginSave)
		if saveRAM[NOSWAP_ACTIVE_SLOT] > 0
			CallFunction(NoSwap_GetRecord)
			saveRAM[arrayPos1] = stage.playerListPos
			arrayPos1++
			saveRAM[arrayPos1] = player.lives
			arrayPos1++
			saveRAM[arrayPos1] = player.score
			arrayPos1++
			saveRAM[arrayPos1] = player.scoreBonus
			arrayPos1++
			temp0 = stage.listPos // next stage to play, +1 so that 0 means an empty slot
			temp0++
			saveRAM[arrayPos1] = temp0
			arrayPos1++
			saveRAM[arrayPos1] = specialStage.emeralds
			arrayPos1++
			saveRAM[arrayPos1] = specialStage.listPos
		end if
		CallFunction(NoSwap_EndSave)
	end if
end function


public function NoSwap_SaveLives
	if stage.playerListPos >= PLAYER_EXTRA1_A
		CallFunction(NoSwap_BeginSave)
		if saveRAM[NOSWAP_ACTIVE_SLOT] > 0
			CallFunction(NoSwap_GetRecord)
			arrayPos1++
			saveRAM[arrayPos1] = player.lives
		end if
		CallFunction(NoSwap_EndSave)
	end if
end function


public function NoSwap_SaveGameOver
	if stage.playerListPos >= PLAYER_EXTRA1_A
		CallFunction(NoSwap_BeginSave)
		if saveRAM[NOSWAP_ACTIVE_SLOT] > 0
			CallFunction(NoSwap_GetRecord)
			arrayPos1++
			if saveRAM[arrayPos1] < 3
				saveRAM[arrayPos1] = 3
			end if
			arrayPos1++
			saveRAM[arrayPos1] = 0
			arrayPos1++
			saveRAM[arrayPos1] = 50000
		end if
		CallFunction(NoSwap_EndSave)
	end if
end function


public function NoSwap_SaveComplete
	if stage.playerListPos >= PLAYER_EXTRA1_A
		CallFunction(NoSwap_BeginSave)
		if saveRAM[NOSWAP_ACTIVE_SLOT] > 0
			CallFunction(NoSwap_GetRecord)
			arrayPos1 += 4
			saveRAM[arrayPos1] = 20 // same "game completed" value the final boss writes for normal saves
		end if
		CallFunction(NoSwap_EndSave)
	end if
end function


"""


def add_save_functions(t, before, complete_value=20):
    """complete_value: what the game's final boss writes into the progress entry (S1 20, S2 22)."""
    functions = SAVE_FUNCTIONS.replace("saveRAM[arrayPos1] = 20 //", f"saveRAM[arrayPos1] = {complete_value} //")
    return patch(t, before, functions + before, "save functions")


SAVE_CALLS = {"full": "NoSwap_SaveProgress", "lives": "NoSwap_SaveLives",
              "gameover": "NoSwap_SaveGameOver", "complete": "NoSwap_SaveComplete"}


def insert_save_calls(t, expected, complete_value=20):
    """Before each block of the game's own slot-saving code, call the matching extras' save routine."""
    lines = t.split("\n")
    found = []
    i = 0
    while i < len(lines):
        l = lines[i]
        nxt = i + 1
        while nxt < len(lines) and lines[nxt].strip().startswith("//"):
            nxt += 1
        if l.strip() == "if options.gameMode == MODE_SAVEGAME" and nxt < len(lines) \
                and lines[nxt].strip() == "arrayPos1 = options.saveSlot":
            ind = l[: len(l) - len(l.lstrip("\t"))]
            j = nxt
            while not (lines[j].strip() == "end if" and lines[j][: len(lines[j]) - len(lines[j].lstrip("\t"))] == ind):
                j += 1
            body = "\n".join(lines[i:j + 1])
            if "specialStage.listPos" in body:
                kind = "full"
            elif "50000" in body:
                kind = "gameover"
            elif f"= {complete_value}" in body:
                kind = "complete"
            elif "player.lives" in body:
                kind = "lives"
            else:
                sys.exit(f"unrecognised save block: {body[:200]}")
            found.append(kind)
            lines.insert(i, f"{ind}CallFunction({SAVE_CALLS[kind]}) // [NoSwap] extras save to their own slots")
            i = j + 2
            continue
        i += 1
    if found != expected:
        sys.exit(f"save calls: found {found} (expected {expected})")
    return "\n".join(lines)


def extras_as_sonic_in_sonic_switches(t, expected, name):
    """extras_take_case (Sonic's) for every `switch stage.playerListPos` whose first cases are Sonic / Sonic & Tails."""
    lines = t.split("\n")
    hits = [i - 2 for i in range(2, len(lines))
            if lines[i].strip() == "case PLAYER_SONIC_TAILS_A"
            and lines[i - 1].strip() == "case PLAYER_SONIC_A"
            and lines[i - 2].strip() == "switch stage.playerListPos"]
    if len(hits) != expected:
        sys.exit(f"patch '{name}': found {len(hits)} Sonic switches (expected {expected})")
    temps = {i: free_temp(lines, i, name) for i in hits}
    for i in reversed(hits):
        extras_take_case(lines, i, name, temp=temps[i])
    return "\n".join(lines)


def guard_special_retry(t, value):
    """Origins' special stage result handling (NOTIFY_SPECIAL_RETRY) runs while the results screen waits
    for its answer, and it looks up the character by ID: an extra's ID left the screen blank or garbled
    (tested 2026-09-25). Present the extra as Sonic until the answer arrives, then restore it.
    `value`: a free object value of the SpecialFinish object."""
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines) if "NotifyCallback, NOTIFY_SPECIAL_RETRY" in l]
    if len(hits) != 1:
        sys.exit(f"special retry guard: found {len(hits)} notifies (expected 1)")
    i = hits[0]
    ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
    lines[i:i] = [
        f"{ind}object.{value} = 0 // [NoSwap] Origins can't handle an extra's ID here: stand in as Sonic",
        f"{ind}if stage.playerListPos >= PLAYER_EXTRA1_A",
        f"{ind}\tobject.{value} = stage.playerListPos",
        f"{ind}\tstage.playerListPos = PLAYER_SONIC_A",
        f"{ind}end if",
    ]
    case = next(k for k, l in enumerate(lines) if l.strip() == "case SPECIALFINISH_WAITFORCALLBACK")
    j = next(k for k in range(case, len(lines)) if lines[k].strip() == "if game.callbackResult >= 0")
    ind = lines[j][: len(lines[j]) - len(lines[j].lstrip("\t"))] + "\t"
    lines[j + 1:j + 1] = [
        f"{ind}if object.{value} > 0 // [NoSwap] back to the extra",
        f"{ind}\tstage.playerListPos = object.{value}",
        f"{ind}end if",
    ]
    return "\n".join(lines)


PROGRESS_NOTIFIES = ("NOTIFY_ACT_FINISH", "NOTIFY_TOUCH_SIGNPOST")


def hide_progress_from_origins(t, expected):
    """Origins credits act progress to the current character's save when it hears these messages.
    Extras keep their own saves, so while one plays the messages are skipped."""
    lines = t.split("\n")
    hits = [i for i, l in enumerate(lines)
            if l.strip().startswith("CallNativeFunction2(NotifyCallback, NOTIFY_")
            and l.strip().split(",")[1].strip() in PROGRESS_NOTIFIES]
    if len(hits) != expected:
        sys.exit(f"progress notifies: found {len(hits)} (expected {expected})")
    for i in reversed(hits):
        ind = lines[i][: len(lines[i]) - len(lines[i].lstrip("\t"))]
        lines[i:i + 1] = [
            f"{ind}if stage.playerListPos < PLAYER_EXTRA1_A // [NoSwap] don't credit an extra's progress to Origins' save",
            "\t" + lines[i],
            f"{ind}end if",
        ]
    return "\n".join(lines)


def literal_extra_ids(text):
    """Extras' IDs as plain numbers: drop the PLAYER_EXTRAn_A alias lines and write each use as its ID (6 + n).
    Sonic 1 and 2 share one small public alias table between all their scripts; with 21 extras these names
    overflowed it (the engine's "Operand not found" at the player script's first private alias). The names stay
    in the builders for readability, and extras.py still defines them."""
    text = re.sub(r"^(?:public|private) alias \d+ : PLAYER_EXTRA\d+_A[^\n]*\n", "", text, flags=re.M)
    return re.sub(r"\bPLAYER_EXTRA(\d+)_A\b", lambda m: str(6 + int(m.group(1))), text)


# NoSwap values other scripts read (Monitor, Ring, the water scripts, BreakWall...: FLAG_BITS): these stay public
SHARED_VALUES = {"NoSwap_flags"}


def private_values(text):
    """Our script values as private, but for SHARED_VALUES. Public values share a fixed table with the
    GameConfig's global variables (Sonic 1 has 199, among them Plus's PLAYER_AMY): 11 more public values in
    the player script overflowed it ("Operand not found: PLAYER_AMY" for every character)."""
    return re.sub(r"^public value (NoSwap_\w+)",
                  lambda m: m.group(0) if m.group(1) in SHARED_VALUES else f"private value {m.group(1)}", text,
                  flags=re.M)


# Our player script values packed into the vanilla player script's seven unused ones (Player_unusedValue1-7).
# Script values, public or private, share one fixed table with the GameConfig's 199 global variables; 11 more of
# ours overflowed it (every character: "Operand not found: PLAYER_AMY", a Plus global, in Player_HandleSuperForm).
# Values sharing a slot belong to different extras, and every write to them is inside that extra's own case or
# function (checked 2026-09-26), so they never meet. All start at 0, as the unused ones do.
PACKED_VALUES = {
    "Player_unusedValue1": ["NoSwap_grappleX", "NoSwap_jumpChain", "NoSwap_cling", "NoSwap_zipCarry", "NoSwap_spin",
                            "NoSwap_swim", "NoSwap_busterCharge", "NoSwap_spark",
                            "NoSwap_swimHeading", "NoSwap_flyHeading"],  # (NoSwap_swim*: Ecco's free swim, tools/free_swim.py; NoSwap_fly*: NiGHTS', tools/free_flight.py)
    "Player_unusedValue2": ["NoSwap_grappleY", "NoSwap_jumpWindow", "NoSwap_clingDir", "NoSwap_spinVY",
                            "NoSwap_swapIcon", "NoSwap_sink", "NoSwap_senseIcon", "NoSwap_swimSpeed", "NoSwap_flySpeed",
                            "NoSwap_voltCharge"],  # (NoSwap_voltCharge: Pulseman's Voltteccer, tools/voltteccer.py)
    "Player_unusedValue3": ["NoSwap_grappleDir", "NoSwap_clingLock", "NoSwap_rollFrame", "NoSwap_pogoShotCooldown",
                            "NoSwap_swap"],
    "Player_unusedValue4": ["NoSwap_plow", "NoSwap_charge", "NoSwap_whipAim", "NoSwap_swimCool", "NoSwap_ninja", "NoSwap_flyDrill", "NoSwap_pots"],
    "Player_unusedValue5": ["NoSwap_shellSafe", "NoSwap_shotNext", "NoSwap_grappleUsed", "NoSwap_swimTime", "NoSwap_ninjaTime", "NoSwap_flyMeter", "NoSwap_potsTime"],  # (NoSwap_flyMeter not in slot 3: NiGHTS rolls, NoSwap_rollFrame)
    "Player_unusedValue6": ["NoSwap_pogo", "NoSwap_shotCooldown", "NoSwap_treasure", "NoSwap_swimFrame", "NoSwap_flyFrame"],
    "Player_unusedValue7": ["NoSwap_glideCap", "NoSwap_shotPose", "NoSwap_flyIcon"],
}


def pack_values(text):
    if not re.search(r"^private value Player_unusedValue1\b", text, flags=re.M):
        return text  # (not the player script)
    for slot, names in PACKED_VALUES.items():
        for name in names:
            decl = re.compile(rf"^(?:public|private) value {name} = (-?\w+)[^\n]*\n", flags=re.M)
            m = decl.search(text)
            if not m:
                if re.search(rf"\b{name}\b", text):
                    sys.exit(f"pack_values: {name} is used but not declared")
                continue  # (a player script without that move: the special stage's)
            if m.group(1) not in ("0", "false"):
                sys.exit(f"pack_values: {name} starts at {m.group(1)}, the unused values at 0")
            text = decl.sub("", text)
            text = re.sub(rf"\b{name}\b", slot, text)
    return text


def table_names(text):
    """Our tables renamed NoSwap_X -> NoSwapTable_X (apart from functions' and values' names), and a check that no two
    names differ only in case: the engine matches names ignoring case, so CallFunction(NoSwap_Melee) went to the
    value NoSwap_melee instead, silently, and every melee extra's Y did nothing (found 2026-09-26)."""
    for name in set(re.findall(r"^(?:public|private) table (NoSwap_\w+)", text, flags=re.M)):
        text = re.sub(rf"\b{name}\b", "NoSwapTable_" + name[len("NoSwap_"):], text)
    seen = {}
    for rx in (r"^(?:public|private|reserve) function (\w+)", r"^(?:public|private) table (\w+)",
               r"^(?:public|private) value (\w+)", r"^(?:public|private) alias \S+ : (\w+)"):
        for name in re.findall(rx, text, flags=re.M):
            other = seen.setdefault(name.lower(), name)
            if other != name:
                sys.exit(f"names differing only in case (the engine ignores case): {other} / {name}")
    return text


def finish_script(text):
    """The last steps for every Sonic 1 / Sonic 2 script the builders write (and own sounds' calls in Sonic CD's too)."""
    text = __import__("own_sounds").own_sound_calls(text)  # (marked own sounds only: tools/own_sounds.py)
    if "#alias" in text:
        return text  # (Sonic CD's v3 scripts, also written by build_scripts: aliases per file, no shared tables)
    return table_names(pack_values(private_values(literal_extra_ids(text))))


def build_scripts(builders, base, out):
    """Apply each builder to its script from `base` and write the result under `out` (keeps CRLF)."""
    for rel, build in builders.items():
        raw = (base / rel).read_bytes().decode("utf-8")
        crlf = "\r\n" in raw
        text = finish_script(build(raw.replace("\r\n", "\n")))
        if crlf:
            text = text.replace("\n", "\r\n")
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(text.encode("utf-8"))
        print(f"built {rel}")
