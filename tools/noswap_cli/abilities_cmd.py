"""`noswap abilities [name]`: the ability registry (tools/abilities_registry.py) in a terminal."""
import difflib
import json
import os
import textwrap

WIDTH = 100


def command():
    """The program's own name: the Creator Kit's (NOSWAP_KIT) or the repo's."""
    return "NoSwapCreator" if os.environ.get("NOSWAP_KIT") else "noswap"


def _wrap(text, indent="  "):
    return "\n".join(textwrap.wrap(text, WIDTH, initial_indent=indent, subsequent_indent=indent))


def _games_mark(e, reg):
    marks = []
    for g in reg.GAMES:
        s = e["games"][g]["support"]
        marks.append(reg.GAME_SHORT[g] if s == "yes" else (reg.GAME_SHORT[g].lower() + "~" if s == "partial" else "--"))
    return " ".join(f"{m:3}" for m in marks)


def listing(reg, game=None):
    data = reg.build()
    rows = sorted(data["abilities"].values(), key=lambda e: ({"move": 0, "passive": 1, "setting": 2}[e["kind"]], e["id"]))
    if game:
        rows = [e for e in rows if e["games"][game]["support"] != "no"]
    out = [f"{'id':16}{'name':22}{'kind':9}{'games':21}input",
           f"{'':16}{'':22}{'':9}{'  '.join(reg.GAME_SHORT[g] for g in reg.GAMES):21}"]
    for e in rows:
        out.append(f"{e['id']:16}{e['name'][:21]:22}{e['kind']:9}{_games_mark(e, reg):21}{e['input']}")
    out += ["", "Games: S1 Sonic 1, S2 Sonic 2, CD Sonic CD, 3K Sonic 3&K, MA Sonic Mania; '~' partial, '--' not there yet.",
            "Moves and passives go in \"abilities\"; settings are fields you set. `" + command() + " abilities <id>` for one in full;",
            "docs/abilities.md has them all."]
    return "\n".join(out)


def describe(e, reg):
    data = reg.build()
    out = [f"{e['name']} ({e['id']}): {e['kind']}, {e['input']}", "", _wrap(e["description"] or "(no description yet)"),
           ""]
    out.append("Games:")
    for g in reg.GAMES:
        d = e["games"][g]
        out.append(f"  {reg.GAME_NAMES[g]:12}{d['support']:8}{d.get('note') or d['how']}")
    if e["used_by"]:
        out += ["", "Used by: " + ", ".join(u["name"].title() for u in e["used_by"])]
    if e["needs"]:
        out += ["", "Needs:"] + [_wrap(n, "  - ") for n in e["needs"]]
    if e["fields"]:
        out += ["", "Fields:"]
        for f, d in e["fields"].items():
            dv = "no default: set it" if d["no_default"] else ("" if d["default"] is None else
                                                   f"left out: {json.dumps(d['default'])}")
            ex = f"e.g. {d['example_text']}" if d.get("example_text") else ""
            out.append(f"  {f} ({d['unit']}{'; ' + d['range'] if d.get('range') else ''})"
                       f"{'  ' + dv if dv else ''}{'  ' + ex if ex else ''}")
            out.append(_wrap(d["what"], "      "))
    if e["slots"]:
        out += ["", "Animation slots (ability_animations):"]
        for s, d in e["slots"].items():
            pg = d["per_game"]
            out.append(f"  {s}{'' if d['required'] else ' (optional)'}: {d['what']}  "
                       f"[CD {pg['cd'] or 'not drawn'}, S3&K {pg['s3k'] or 'not drawn'}]")
    rules = [r for r in data["rules"] if r["id"] in e["rules"]]
    if rules:
        out += ["", "Combining:"]
        for r in rules:
            out.append(_wrap(f"[{r['level']}] {r['text']}", "  "))
    if e["example"]:
        out += ["", f"Example (from {e['example_from'].title()}):",
                textwrap.indent(json.dumps(e["example"], indent=1), "  ")]
    units = sorted({d["unit"] for d in e["fields"].values()})
    if units:
        out += ["", "Units:"] + [_wrap(f"{u}: {reg.UNITS.get(u, u)}", "  ") for u in units]
    return "\n".join(out)


def run(name=None, as_json=False, game=None):
    import abilities_registry as reg
    if not name:
        print(json.dumps(reg.build(), indent=1, default=str) if as_json else listing(reg, game))
        return 0
    e = reg.lookup(name)
    if e is None:
        names = list(reg.build()["abilities"])
        near = difflib.get_close_matches(name.lower(), names, n=3)
        print(f"no ability {name!r}{' (did you mean ' + ' / '.join(near) + '?)' if near else ''}; "
              f"`{command()} abilities` lists them")
        return 2
    print(json.dumps(e, indent=1, default=str) if as_json else describe(e, reg))
    return 0
