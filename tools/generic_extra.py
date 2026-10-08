#!/usr/bin/env python3
"""Make a player script ID-agnostic (docs/plan-b-modular-characters.md, phase A: the roster is decided at runtime).

Origins gives each installed character a kind (7, 8, ...) at startup from the DLL's registry, so a package can't know
its number when it's built. Only one extra ever plays, though, so a package's scripts only need to know "is the player
an extra" (`stage.playerListPos >= 7`), never which one. The builders still write each package's scripts for the ID it
has in tools/extras.py (its "build ID": 6 + its place there); this pass then rewrites every place that asks the kind
about that ID so that ANY kind from 7 up behaves exactly as the build ID did, and kinds 0-6 exactly as before:

- `switch stage.playerListPos` (or `player.character`) with a case for the build ID (the "row"):
      if <kind> >= 7
          <what the switch ran for the row: from its case to the break>
      else
          switch <kind>  (every case label of 7 and up taken out)
      end if
  A switch without the row's case keeps its vanilla labels (labels of 7 and up taken out: those were other extras').
- `if <kind> <op> <constant>`: kept when it already answers the same for every kind from 7 up as for the row;
  otherwise rewritten to `>= 7` / `< 7`, or, when every kind answers the same, replaced by the branch that runs.
- Where the kind is used as a row number into the script's own per-extra tables (`GetTableValue(x,
  stage.playerListPos, T)`, `tempN = stage.playerListPos`), an extra's row is the build ID: in code only an extra can
  reach the value is written in directly (`x = <T[row]>`, `tempN = <row>`); where a vanilla character can reach it too
  it becomes `if stage.playerListPos >= 7 / <that> / else / <the original> / end if`. So the build ID survives only as a
  row number inside the package's own tables, never as a kind.
- `player.character = stage.playerListPos` is kept: the character value is the real kind.

NoSwap's own player scripts (no package) use row 0: an extra with no package plays exactly as Sonic does (the shared
scripts still see an extra and use NoSwap's Sonic-looking placeholder art).

Which code "only an extra can reach" is decided from the enclosing kind tests, and for a function from every place
that names it (a call, or its name stored as a state / jump ability); a public function another script names can be
reached by anyone. Works on both dialects: RSDKv4 (Sonic 1 / 2) and v3 (Sonic CD: no tables, #alias, CamelCase).
Every line not rewritten is kept byte for byte (emit(parse(text)) == text is checked)."""
import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXTRA_MIN = 7  # the first extra kind
KIND_MAX = 255  # kinds are bytes (the DLL assigns at most 254: tools/../native/src/Roster.h KIND_LIMIT)
VANILLA = range(EXTRA_MIN)


class GenericError(Exception):
    pass


# ---------------------------------------------------------------- parsing (keeps every line as it was)
def code_of(line):
    return re.sub(r"\s+", " ", line.split("//")[0]).strip()


def low(line):
    return code_of(line).lower()


BLOCK_HEAD = re.compile(r"^(event|sub|(public |private )?function) \S+$", re.I)
BLOCK_END = {"end event", "end sub", "end function", "endevent", "endsub", "endfunction"}
IF_END = {"end if", "endif"}
SWITCH_END = {"end switch", "endswitch"}
LOOPS = {"while": {"loop"}, "foreach": {"next"}}


class Line:
    def __init__(self, text):
        self.text = text

    def lines(self):
        return [self.text]


class Label(Line):
    pass


class If:
    def __init__(self, head, then, else_line, els, end):
        self.head, self.then, self.else_line, self.els, self.end = head, then, else_line, els, end

    def lines(self):
        out = [self.head] + emit(self.then)
        if self.else_line is not None:
            out += [self.else_line] + emit(self.els)
        return out + [self.end]


class Switch:
    def __init__(self, head, items, end):
        self.head, self.items, self.end = head, items, end

    def lines(self):
        return [self.head] + emit(self.items) + [self.end]


class Loop:
    def __init__(self, head, body, end):
        self.head, self.body, self.end = head, body, end

    def lines(self):
        return [self.head] + emit(self.body) + [self.end]


class Block:
    def __init__(self, head, body, end):
        self.head, self.body, self.end = head, body, end
        self.name = code_of(head).split(" ")[-1]
        self.public = low(head).startswith("public ")
        self.event = low(head).startswith(("event", "sub"))

    def lines(self):
        return [self.head] + emit(self.body) + [self.end]


def emit(nodes):
    out = []
    for n in nodes:
        out += n.lines()
    return out


# The #platform blocks Origins compiles (as CD's proofs: scratchpad cd/project.py): Origins' own and the standard (not
# mobile) platform. Lines in any other block are kept as they are and never read as code (Origins' decompiled scripts
# put an `if` head per platform over one shared body, so only one platform's view has matching ends).
ACTIVE_PLATFORMS = {"use_origins", "standard"}


class Opaque(Line):
    """A #platform / #endplatform line, or a line in a block Origins doesn't compile: kept, never read."""


def parse(lines):
    pos = 0
    plat = [None]

    def opaque():
        """The line at pos is a directive, or inside a block Origins doesn't compile."""
        c = low(lines[pos])
        if c.startswith("#platform:"):
            plat[0] = c.split(":", 1)[1].strip()
            return True
        if c.startswith("#endplatform"):
            plat[0] = None
            return True
        return plat[0] is not None and plat[0] not in ACTIVE_PLATFORMS

    def body(ends, in_switch=False):
        nonlocal pos
        out = []
        while pos < len(lines):
            if opaque():
                out.append(Opaque(lines[pos]))
                pos += 1
                continue
            c = low(lines[pos])
            if c in ends:
                return out
            line = lines[pos]
            pos += 1
            if in_switch and (c.startswith("case ") or c == "default"):
                out.append(Label(line))
            elif c.startswith("if "):
                then = body(IF_END | {"else"})
                else_line, els = None, None
                if pos < len(lines) and low(lines[pos]) == "else":
                    else_line = lines[pos]
                    pos += 1
                    els = body(IF_END)
                out.append(If(line, then, else_line, els, take(IF_END)))
            elif c.startswith("switch "):
                items = body(SWITCH_END, in_switch=True)
                out.append(Switch(line, items, take(SWITCH_END)))
            elif c.split(" ")[0] in LOOPS or c.split("(")[0] in LOOPS:
                key = c.split(" ")[0] if c.split(" ")[0] in LOOPS else c.split("(")[0]
                b = body(LOOPS[key])
                out.append(Loop(line, b, take(LOOPS[key])))
            else:
                out.append(Line(line))
        if ends:
            raise GenericError(f"unexpected end of script (looking for {sorted(ends)})")
        return out

    def take(ends):
        nonlocal pos
        if pos >= len(lines) or low(lines[pos]) not in ends:
            raise GenericError(f"line {pos + 1}: expected {sorted(ends)}, found {lines[pos] if pos < len(lines) else 'EOF'!r}")
        pos += 1
        return lines[pos - 1]

    tops = []
    while pos < len(lines):
        if opaque():
            tops.append(Opaque(lines[pos]))
            pos += 1
            continue
        line = lines[pos]
        pos += 1
        if BLOCK_HEAD.match(code_of(line)):
            b = body(BLOCK_END)
            tops.append(Block(line, b, take(BLOCK_END)))
        else:
            tops.append(Line(line))
    return tops


def active_lines(lines):
    """[(line number, line)] of the lines Origins compiles (directives and other platforms' blocks left out)."""
    out, plat = [], None
    for n, l in enumerate(lines, 1):
        c = low(l)
        if c.startswith("#platform:"):
            plat = c.split(":", 1)[1].strip()
        elif c.startswith("#endplatform"):
            plat = None
        elif plat is None or plat in ACTIVE_PLATFORMS:
            out.append((n, l))
    return out


# ---------------------------------------------------------------- constants
def gameconfig_globals(game):
    """{lower name: value} of a game's GameConfig.bin global variables (v4: little-endian, with a palette; v3 (CD):
    big-endian, with a data folder name and no palette)."""
    folder = {"Sonic1u": "Sonic1", "Sonic2u": "Sonic2", "SonicCDu": "SonicCD"}[game]
    d = (REPO / "extracted" / folder / "Data" / "Game" / "GameConfig.bin").read_bytes()
    p = 0

    def s():
        nonlocal p
        n = d[p]
        v = d[p + 1:p + 1 + n].decode("latin1")
        p += 1 + n
        return v
    v3 = game == "SonicCDu"
    s(), s()
    if v3:
        s()
    else:
        p += 96 * 3
    n = d[p]
    p += 1
    for _ in range(2 * n):
        s()
    g = d[p]
    p += 1
    out = {}
    for _ in range(g):
        name = s()
        out[name.lower()] = struct.unpack(">i" if v3 else "<i", d[p:p + 4])[0]
        p += 4
    return out


def script_aliases(lines):
    """{lower alias name: its text value} of a script's own aliases (v4 `public|private alias V : NAME`, v3 `#alias`)."""
    out = {}
    for l in lines:
        m = re.match(r"^(?:(?:public|private) alias|#alias)\s+(\S+)\s*:\s*(\S+)", code_of(l), re.I)
        if m:
            out.setdefault(m.group(2).lower(), m.group(1))
    return out


class Consts:
    def __init__(self, aliases, globals_):
        self.aliases, self.globals = aliases, globals_

    def value(self, tok):
        tok = tok.strip()
        for _ in range(4):
            if tok.lower() in self.aliases:
                tok = self.aliases[tok.lower()]
        if tok.lower() in self.globals:
            return self.globals[tok.lower()]
        try:
            return int(tok, 0)
        except ValueError:
            return None


# ---------------------------------------------------------------- the rewrite
KIND_EXPR = [(re.compile(r"^stage\.playerlistpos$", re.I), "plp"),
             (re.compile(r"^(player|object)(\[[^\]]*\])?\.character$", re.I), "char")]
OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
       ">": lambda a, b: a > b, "<": lambda a, b: a < b}
FLIP = {"==": "==", "!=": "!=", ">=": "<=", "<=": ">=", ">": "<", "<": ">"}
PLP = r"stage\.playerlistpos"


def kind_of(expr):
    for rx, k in KIND_EXPR:
        if rx.match(expr):
            return k
    return None


def spaced(code):
    return re.sub(r"\s*(==|!=|>=|<=|(?<![<>=!])>(?!=)|(?<![<>=!])<(?!=))\s*", r" \1 ", code).strip()


def condition(head):
    """(kind, op, const text) of `if <kind expr> <op> <token>` (either way round), else None."""
    c = spaced(code_of(head))
    m = re.match(r"^if (\S+) (==|!=|>=|<=|>|<) (\S+)$", c, re.I)
    if not m:
        return None
    a, op, b = m.groups()
    if kind_of(a):
        return kind_of(a), op, b
    if kind_of(b):
        return kind_of(b), FLIP[op], a
    return None


def indent_of(line):
    return line[:len(line) - len(line.lstrip("\t "))]


def shift(nodes, by):
    """Re-indent every line of nodes by `by` tabs (negative: remove up to that many); directives stay in column 0."""
    def fix(t):
        if t.lstrip().startswith("#"):
            return t
        if by > 0:
            return "\t" * by + t if t.strip() else t
        k = 0
        while k < -by and t.startswith("\t"):
            t, k = t[1:], k + 1
        return t
    out = []
    for n in nodes:
        if isinstance(n, Label):
            out.append(Label(fix(n.text)))
        elif isinstance(n, Opaque):
            out.append(Opaque(fix(n.text)))
        elif isinstance(n, Line):
            out.append(Line(fix(n.text)))
        elif isinstance(n, If):
            out.append(If(fix(n.head), shift(n.then, by), fix(n.else_line) if n.else_line is not None else None,
                          shift(n.els, by) if n.els is not None else None, fix(n.end)))
        elif isinstance(n, Switch):
            out.append(Switch(fix(n.head), shift(n.items, by), fix(n.end)))
        elif isinstance(n, Loop):
            out.append(Loop(fix(n.head), shift(n.body, by), fix(n.end)))
    return out


def has_break(nodes):
    """A `break` inside an if / loop body (not inside a nested switch, whose own it is)."""
    for n in nodes:
        if isinstance(n, Line) and low(n.text) == "break":
            return True
        if isinstance(n, If) and (has_break(n.then) or has_break(n.els or [])):
            return True
        if isinstance(n, Loop) and has_break(n.body):
            return True
    return False


def active_only(nodes):
    """A copy of nodes without the Opaque lines (directives, other platforms' lines): Origins' code only, for code that
    is copied to a new place (always into code Origins compiles)."""
    out = []
    for n in nodes:
        if isinstance(n, Opaque):
            continue
        if isinstance(n, If):
            out.append(If(n.head, active_only(n.then), n.else_line,
                          active_only(n.els) if n.els is not None else None, n.end))
        elif isinstance(n, Switch):
            out.append(Switch(n.head, active_only(n.items), n.end))
        elif isinstance(n, Loop):
            out.append(Loop(n.head, active_only(n.body), n.end))
        else:
            out.append(n)
    return out


def opaque_only(nodes):
    """The Opaque lines among nodes, in order (what must stay when the code around them goes)."""
    out = []
    for n in nodes:
        if isinstance(n, Opaque):
            out.append(n)
        elif isinstance(n, If):
            out += opaque_only(n.then) + opaque_only(n.els or [])
        elif isinstance(n, Switch):
            out += opaque_only(n.items)
        elif isinstance(n, Loop):
            out += opaque_only(n.body)
    return out


def directives(nodes):
    return [l for l in emit(nodes) if l.lstrip().startswith("#platform") or l.lstrip().startswith("#endplatform")]


def platform_at(lines_before):
    """The #platform block open after these lines (None: none)."""
    plat = None
    for l in lines_before:
        c = code_of(l)
        if c.lower().startswith("#platform:"):
            plat = c.split(":", 1)[1].strip()
        elif c.lower().startswith("#endplatform"):
            plat = None
    return plat


class Generaliser:
    def __init__(self, text, row, game, external_refs=(), name="?", char_row="row"):
        self.name, self.row, self.game = name, row, game
        # the character value's row: the same as the kind's for a package; None for NoSwap's own (row 0), where nothing
        # sets a character of 7 or up (an extra plays as Sonic, whose startup sets Sonic's)
        self.char_row = row if char_row == "row" else char_row
        self.v3 = game == "SonicCDu"
        self.crlf = "\r\n" in text
        self.lines = text.replace("\r\n", "\n").split("\n")
        self.tops = parse(self.lines)
        if emit(self.tops) != self.lines:
            raise GenericError(f"{name}: the parser doesn't give the script back line for line")
        aliases = script_aliases(self.lines)
        if not self.v3:  # (v4 public aliases are shared by every script: the player script's, for the special stage's)
            shared = REPO / "mods" / "NoSwap" / game / "Data" / "Scripts" / "Players" / "PlayerObject.txt"
            if shared.exists():
                for k, v in script_aliases([l for l in shared.read_text(errors="ignore").split("\n")
                                            if code_of(l).lower().startswith("public alias")]).items():
                    aliases.setdefault(k, v)
        self.consts = Consts(aliases, gameconfig_globals(game))
        self.tables = self.read_tables()
        self.external = {r.lower() for r in external_refs}
        self.stats = {"switches": 0, "labels dropped": 0, "conditions": 0, "branches": 0, "rows": 0}
        self.funcs = {b.name.lower(): b for b in self.tops if isinstance(b, Block) and not b.event}

    def fail(self, what):
        raise GenericError(f"{self.name}: {what}")

    # ---- tables (v4)
    def read_tables(self):
        out, cur = {}, None
        for l in self.lines:
            c = code_of(l)
            m = re.match(r"^(public|private) table (\w+)$", c, re.I)
            if m:
                cur = (m.group(2).lower(), [])
                continue
            if cur and c.lower() == "end table":
                out[cur[0]] = cur[1]
                cur = None
                continue
            if cur and c:
                cur[1].extend(int(v.strip(), 0) for v in c.split(",") if v.strip())
        return out

    def truth(self, kind_value, op, const):
        v = self.consts.value(const)
        if v is None:
            return None
        return OPS[op](kind_value, v)

    def classes(self, op, const):
        """(truth for each vanilla kind, truth for the row, same answer for every kind from 7 up as the row?)"""
        v = self.consts.value(const)
        if v is None:
            self.fail(f"can't resolve {const!r} in a kind test")
        van = [OPS[op](k, v) for k in VANILLA]
        r = OPS[op](self.row, v)
        return van, r, all(OPS[op](k, v) == r for k in range(EXTRA_MIN, KIND_MAX + 1))

    # ---- contexts: which classes of kind ("V" vanilla, "X" an extra) can reach a spot
    def refine(self, ctx, kind, op, const, branch):
        if kind != "plp" or self.consts.value(const) is None:
            return ctx
        van, r, _ = self.classes(op, const)
        out = set()
        if "V" in ctx and any(t == branch for t in van):
            out.add("V")
        if "X" in ctx and r == branch:
            out.add("X")
        return frozenset(out)

    def switch_labels(self, sw):
        out = []
        for n in sw.items:
            if isinstance(n, Label):
                c = code_of(n.text)
                out.append(None if c.lower() == "default" else self.consts.value(c[5:]))
        return out

    def references(self, nodes, ctx, found):
        """Record (function name, ctx) for every function name used in these nodes, following kind tests."""
        for n in nodes:
            if isinstance(n, Opaque):
                continue
            if isinstance(n, Line):
                for w in re.findall(r"[A-Za-z_]\w*", code_of(n.text)):
                    if w.lower() in self.funcs:
                        found.append((w.lower(), ctx))
            elif isinstance(n, If):
                cond = condition(n.head)
                if cond:
                    self.references(n.then, self.refine(ctx, *cond, True), found)
                    self.references(n.els or [], self.refine(ctx, *cond, False), found)
                else:
                    self.references(n.then, ctx, found)
                    self.references(n.els or [], ctx, found)
            elif isinstance(n, Switch):
                k = kind_of(code_of(n.head)[7:].strip())
                if k == "plp":
                    for n2, c2 in self.switch_segments(n, ctx):
                        self.references([n2], c2, found)
                else:
                    self.references(n.items, ctx, found)
            elif isinstance(n, Loop):
                self.references([Line(n.head)], ctx, found)
                self.references(n.body, ctx, found)

    def switch_segments(self, sw, ctx):
        """Each item of a switch on the kind, with the classes that can run it (from the labels above it, as the
        rewritten switch runs: an extra from the row's label, or the default when there's none)."""
        labels = self.switch_labels(sw)
        has_row = self.row in labels
        cur, out = set(), []
        for n in sw.items:
            if isinstance(n, Label):
                c = code_of(n.text)
                if c.lower() == "default":
                    cur.add("V")
                    if not has_row:
                        cur.add("X")
                else:
                    v = self.consts.value(c[5:])
                    if v is None:
                        self.fail(f"can't resolve the label {c!r}")
                    if v == self.row:
                        cur.add("X")
                    if v < EXTRA_MIN:
                        cur.add("V")
                continue
            out.append((n, frozenset(cur & set(ctx))))
            if isinstance(n, Line) and low(n.text) == "break":
                cur = set()
        return out

    def function_contexts(self):
        ctx = {name: frozenset() for name in self.funcs}
        for name, b in self.funcs.items():  # reachable by anyone: named by another script, or by nothing here
            if b.public and name in self.external:
                ctx[name] = frozenset({"V", "X"})
        named = set()
        for b in self.tops:
            if isinstance(b, Block):
                found = []
                self.references(b.body, frozenset({"V", "X"}), found)
                named |= {f for f, _ in found if f != b.name.lower()}
        for name in self.funcs:
            if name not in named:
                ctx[name] = frozenset({"V", "X"})
        while True:
            new = dict(ctx)
            for b in self.tops:
                if not isinstance(b, Block):
                    continue
                start = frozenset({"V", "X"}) if b.event else ctx[b.name.lower()]
                if not start:
                    continue
                found = []
                self.references(b.body, start, found)
                for f, c in found:
                    new[f] = new[f] | c
            if new == ctx:
                return ctx
            ctx = new

    # ---- statements
    def statement(self, line, ctx):
        """A statement using the kind as a row number: rewritten for ctx. Returns the replacement nodes."""
        c = code_of(line.text)
        if not re.search(PLP, c, re.I):
            return [line]
        ind = indent_of(line.text)
        comment = line.text[line.text.index("//"):] if "//" in line.text else ""
        m = re.match(rf"^GetTableValue\((.+?),\s*{PLP}\s*,\s*(\w+)\)$", c, re.I)
        m2 = re.match(rf"^((?:temp|tempvalue)\d)\s*=\s*{PLP}$", c, re.I)
        if m:
            dest, table = m.group(1).strip(), m.group(2).lower()
            if table not in self.tables:
                self.fail(f"GetTableValue from {table}, which this script doesn't define")
            if self.row >= len(self.tables[table]):
                self.fail(f"{table} has no row {self.row}")
            extra = f"{dest} = {self.tables[table][self.row]}"
        elif m2:
            extra = f"{m2.group(1)} = {self.row}"
        elif re.match(rf"^(player|object)(\[[^\]]*\])?\.character\s*=\s*{PLP}$", c, re.I):
            return [line]  # the character value is the real kind
        elif re.match(rf"^{PLP}\s*=\s*(\S+)$", c, re.I):
            v = self.consts.value(c.split("=", 1)[1])
            if v is None or v >= EXTRA_MIN:
                self.fail(f"writes {c!r}")
            return [line]  # (vanilla to vanilla: the Origins S&T / Amy & Tails setup)
        else:
            if "X" in ctx:
                self.fail(f"uses the kind in {c!r}, which an extra can reach")
            return [line]
        if ctx == frozenset({"V"}) or not ctx:
            return [line]
        self.stats["rows"] += 1
        note = f" // [NoSwap] an extra: its row in this script's tables (built as {self.row})"
        if ctx == frozenset({"X"}):
            return [Line(f"{ind}{extra}{note if not comment else ' ' + comment + ' ' + note[4:]}")]
        kv = "Stage.PlayerListPos" if self.v3 else "stage.playerListPos"
        return [If(f"{ind}if {kv} >= {EXTRA_MIN}{note}", [Line(f"{ind}\t{extra}")], f"{ind}else",
                   [Line(f"{ind}\t{line.text.lstrip()}")], f"{ind}end if")]

    # ---- the walk
    def walk(self, nodes, ctx):
        out = []
        for n in nodes:
            got = None
            if isinstance(n, (Label, Opaque)):
                out.append(n)
            elif isinstance(n, Line):
                out += self.statement(n, ctx)
            elif isinstance(n, If):
                got = self.walk_if(n, ctx)
            elif isinstance(n, Switch):
                got = self.walk_switch(n, ctx)
            elif isinstance(n, Loop):
                if re.search(PLP, code_of(n.head), re.I):
                    self.fail(f"a loop on the kind: {n.head.strip()!r}")
                out.append(Loop(n.head, self.walk(n.body, ctx), n.end))
            if got is not None:
                if not got and out and blank(out[-1]):
                    # (it went entirely, another extra's `if`: so does the blank line before it, the separator the
                    # builders put between extras' blocks. A package's script stays as it was when a character is added)
                    out.pop()
                out += got
        return out

    def walk_if(self, n, ctx):
        cond = condition(n.head)
        if not cond:  # (a kind compared with something that isn't a constant passes the kind through: kept)
            return [If(n.head, self.walk(n.then, ctx), n.else_line,
                       self.walk(n.els, ctx) if n.els is not None else None, n.end)]
        kind, op, const = cond
        v = self.consts.value(const)
        if v is None:
            # compared with a variable (CD's Origins Plus spawn point: Object[..].PropertyValue): the kind passes through
            return [If(n.head, self.walk(n.then, ctx), n.else_line,
                       self.walk(n.els, ctx) if n.els is not None else None, n.end)]
        van = [OPS[op](k, v) for k in VANILLA]
        canonical = v < EXTRA_MIN or (v == EXTRA_MIN and op in (">=", "<"))
        row = self.row if kind == "plp" else self.char_row
        if row is None:  # (no character of 7 or up here: only the vanilla answers matter)
            r, same = van[0], True
            if all(t == van[0] for t in van):
                return self.branch(n, van[0], ctx, ctx)
            if not canonical:
                self.fail(f"{n.head.strip()!r}: a particular character's test with vanilla answers that differ")
            return [If(n.head, self.walk(n.then, ctx), n.else_line,
                       self.walk(n.els, ctx) if n.els is not None else None, n.end)]
        r = OPS[op](row, v)
        same = all(OPS[op](k, v) == r for k in range(EXTRA_MIN, KIND_MAX + 1))
        then_ctx, else_ctx = self.refine(ctx, kind, op, const, True), self.refine(ctx, kind, op, const, False)
        if same and canonical:  # already right for every extra (and, as before, for the vanilla kinds)
            return [If(n.head, self.walk(n.then, then_ctx), n.else_line,
                       self.walk(n.els, else_ctx) if n.els is not None else None, n.end)]
        if all(t == r for t in van):  # every kind gets the same answer: just that branch
            return self.branch(n, r, then_ctx, else_ctx)
        self.stats["conditions"] += 1
        if r and not any(van):
            head = self.kind_test(n.head, kind, ">=")
        elif not r and all(van):
            head = self.kind_test(n.head, kind, "<")
        else:  # an extra takes one branch, the vanilla kinds as before: `if >= 7 / that branch / else / the if`
            ind = indent_of(n.head)
            kv = next(t for t in re.split(r"\s+|==|!=|>=|<=|>|<", code_of(n.head)[3:]) if t and kind_of(t))
            kept = active_only(n.then if r else (n.els or []))
            x_ctx = then_ctx if r else else_ctx
            inner = If(n.head, self.walk(n.then, frozenset(then_ctx - {"X"})), n.else_line,
                       self.walk(n.els, frozenset(else_ctx - {"X"})) if n.els is not None else None, n.end)
            return [If(f"{ind}if {kv} >= {EXTRA_MIN} // [NoSwap] an extra: as the row ({row})",
                       self.walk(kept, x_ctx), f"{ind}else", shift([inner], 1), f"{ind}end if")]
        return [If(head, self.walk(n.then, then_ctx), n.else_line,
                   self.walk(n.els, else_ctx) if n.els is not None else None, n.end)]

    def branch(self, n, taken, then_ctx, else_ctx):
        """Replace an `if` every kind answers the same way by the branch that runs. Platform lines in the branch that
        goes stay where they were (before the kept code if they were in the then-branch, after it if in the else)."""
        self.stats["branches"] += 1
        if opaque_only(n.then) or opaque_only(n.els or []):
            self.stats["platform folds"] = self.stats.get("platform folds", 0) + 1
        kept = self.walk(shift(n.then if taken else (n.els or []), -1), then_ctx if taken else else_ctx)
        if taken:
            return kept + opaque_only(n.els or [])
        return opaque_only(n.then) + kept

    def kind_test(self, head, kind, op):
        c = code_of(head)
        expr = next(t for t in re.split(r"\s+|==|!=|>=|<=|>|<", c[3:]) if t and kind_of(t))
        comment = head[head.index("//"):] if "//" in head else ""
        return f"{indent_of(head)}if {expr} {op} {EXTRA_MIN}" + (f" {comment}" if comment else "")

    def walk_switch(self, n, ctx):
        expr = code_of(n.head)[7:].strip()
        kind = kind_of(expr)
        if not kind:
            return [Switch(n.head, self.walk(n.items, ctx), n.end)]
        labels = self.switch_labels(n)
        label_items = [x for x in n.items if isinstance(x, Label)]
        for v, l in zip(labels, label_items):
            if v is None and code_of(l.text).lower() != "default":
                self.fail(f"a label it can't resolve in {n.head.strip()!r}: {l.text.strip()!r}")
        row = self.row if kind == "plp" else self.char_row

        # the switch with every label of 7 and up taken out; code before the first label left can't run any more
        # (only extras' labels led there) and goes, but for blank / comment / directive lines
        stripped = [it for it, v in zip_labels(n.items, labels) if not (isinstance(it, Label) and v is not None
                                                                           and v >= EXTRA_MIN)]
        dropped = len(n.items) - len(stripped)
        stripped = drop_dead(stripped)
        self.stats["labels dropped"] += dropped
        inner_ctx = frozenset(ctx & {"V"}) if kind == "plp" else ctx
        if row is None or (kind == "plp" and "X" not in ctx):  # no extra gets here: only the labels go
            return [Switch(n.head, self.walk(stripped, inner_ctx), n.end)] if any(
                isinstance(it, Label) for it in stripped) else []

        old_start = start_index(n.items, labels, row)
        # a kind of 7 or up runs the stripped switch's default, if it has one (no label left can name it)
        new_start = start_index(stripped, [], None, default_only=True)
        want, now = run_from_items(n.items, old_start), run_from_items(stripped, new_start)
        if emit(want) == emit(now) and (old_start is None) == (new_start is None):
            return [Switch(n.head, self.walk(stripped, ctx), n.end)] if any(
                isinstance(it, Label) for it in stripped) else []
        if has_break(want):
            self.fail(f"{n.head.strip()!r}: a break inside an if in the extra's case")
        self.stats["switches"] += 1
        ind = indent_of(n.head)
        # (the copy is Origins' code only: it goes where the switch starts, which Origins compiles)
        run = self.walk(active_only(want), frozenset(ctx & {"X"}) if kind == "plp" else ctx)
        head = f"{ind}if {expr} >= {EXTRA_MIN} // [NoSwap] an extra: what this switch ran for it (as {row})"
        if not any(isinstance(it, Label) for it in stripped):
            return [If(head, run, None, None, f"{ind}end if")]
        inner = Switch(n.head, self.walk(stripped, inner_ctx), n.end)
        return [If(head, run, f"{ind}else", shift([inner], 1), f"{ind}end if")]

    # ---- whole script
    def run(self):
        fctx = self.function_contexts()
        out = []
        for t in self.tops:
            if isinstance(t, Block):
                ctx = frozenset({"V", "X"}) if t.event else fctx[t.name.lower()]
                if not ctx:
                    ctx = frozenset({"V", "X"})  # (named only from code nothing reaches: leave it general)
                out.append(Block(t.head, self.walk(t.body, ctx), t.end))
            else:
                out.append(t)
        lines = drop_unused(emit(out), self.v3)
        text = "\n".join(lines)
        check(text, self.name, self.consts)
        return text.replace("\n", "\r\n") if self.crlf else text


def blank(n):
    return type(n) is Line and n.text.strip() == ""


def drop_dead(items):
    """A switch's items without the code no label reaches any more (before the first label, or after a break until the
    next label: an extra's case whose label went). Comment and platform lines stay, and blank lines but those right after
    dropped code (another extra's case's separator: a package's script doesn't change when a character is added)."""
    out, live, dropped = [], False, False
    for it in items:
        if isinstance(it, Label):
            live = True
        elif not live and dropped and blank(it):
            continue
        elif not live and not (isinstance(it, Opaque) or (isinstance(it, Line) and code_of(it.text) == "")):
            dropped = True
            continue
        dropped = False
        out.append(it)
        if isinstance(it, Line) and not isinstance(it, Opaque) and low(it.text) == "break":
            live = False
    return out


def zip_labels(items, labels):
    """(item, its label value or None) for every item: labels in order."""
    k, out = 0, []
    for it in items:
        if isinstance(it, Label):
            out.append((it, labels[k]))
            k += 1
        else:
            out.append((it, None))
    return out


def start_index(items, labels, value, default_only=False):
    """Where a switch starts for `value`: its label, else its default (None: nothing runs)."""
    k = 0
    idx = None
    for i, it in enumerate(items):
        if isinstance(it, Label):
            if not default_only and value is not None and labels[k] == value and idx is None:
                idx = i
            k += 1
    if idx is not None:
        return idx
    for i, it in enumerate(items):
        if isinstance(it, Label) and code_of(it.text).lower() == "default":
            return i
    return None


def balanced(dirs):
    open_ = False
    for d in dirs:
        if code_of(d).lower().startswith("#platform:"):
            if open_:
                return False
            open_ = True
        else:
            if not open_:
                return False
            open_ = False
    return not open_


def run_from_items(items, i):
    run = []
    if i is None:
        return run
    for it in items[i:]:
        if isinstance(it, Label):
            continue
        if isinstance(it, Line) and low(it.text) == "break":
            break
        run.append(it)
    return run


def drop_unused(lines, v3):
    """Private NoSwap tables and v3 PLAYER_EXTRA aliases nothing names any more."""
    text_code = [code_of(l) for l in lines]
    out, skip = [], False
    for i, l in enumerate(lines):
        c = text_code[i]
        m = re.match(r"^private table (NoSwap\w+)$", c)
        if m and not any(re.search(rf"\b{m.group(1)}\b", t) for j, t in enumerate(text_code) if j != i):
            skip = True
            continue
        if skip:
            if c.lower() == "end table":
                skip = False
            continue
        m = re.match(r"^#alias \S+\s*:\s*(PLAYER_EXTRA\d+_A)$", c, re.I)
        if m and not any(re.search(rf"\b{m.group(1)}\b", t, re.I) for j, t in enumerate(text_code) if j != i):
            continue
        out.append(l)
    return out


def check(text, name, consts):
    """No test of a particular kind of 7 or up is left: case labels and kind comparisons use 0-6, or `>= 7` / `< 7`."""
    stack = []
    for n, l in active_lines(text.split("\n")):
        c = code_of(l)
        cl = c.lower()
        if cl.startswith("switch "):
            stack.append(kind_of(c[7:].strip()))
        elif cl in SWITCH_END and stack:
            stack.pop()
        elif cl.startswith("case ") and stack and stack[-1]:
            v = consts.value(c[5:])
            if v is None or v >= EXTRA_MIN:
                raise GenericError(f"{name}:{n}: case {c[5:]!r} on the kind is left")
        cond = condition(l) if cl.startswith("if ") else None
        if cond:
            _, op, const = cond
            v = consts.value(const)
            if v is None:  # (compared with a variable: the kind passes through)
                continue
            if v is None or (v >= EXTRA_MIN and not (v == EXTRA_MIN and op in (">=", "<"))):
                raise GenericError(f"{name}:{n}: {c!r} tests a particular kind")


def generalise(text, row, game, external_refs=(), name="?", char_row="row"):
    """The script with every test of the build ID made kind-free (see the module doc). Returns (text, stats)."""
    g = Generaliser(text, row, game, external_refs, name, char_row)
    return g.run(), g.stats


GAME_EXEC = Path(__import__("os").environ.get(
    "ORIGINS_EXEC", str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec"))


def external_refs(game, own_rel):
    """Every name any other script of the game names (NoSwap's shared scripts and the game's own): a public function
    in it can be called from anywhere."""
    out = set()
    for base in (REPO / "mods" / "NoSwap" / game / "Data" / "Scripts", GAME_EXEC / game / "Scripts"):
        for f in base.rglob("*.txt"):
            if f.relative_to(base).as_posix() != own_rel:
                out |= referenced_names([f.read_text(errors="ignore")])
    return out


def referenced_names(texts):
    """Every identifier the given script texts name (to find which public functions other scripts call)."""
    out = set()
    for t in texts:
        for l in t.replace("\r\n", "\n").split("\n"):
            out |= {w.lower() for w in re.findall(r"[A-Za-z_]\w*", code_of(l))}
    return out


if __name__ == "__main__":
    # tools/generic_extra.py <script> <row> <game>: print the generalised script
    src = Path(sys.argv[1]).read_bytes().decode("utf-8")
    out, stats = generalise(src, int(sys.argv[2]), sys.argv[3], name=sys.argv[1])
    sys.stdout.write(out)
    print(stats, file=sys.stderr)
