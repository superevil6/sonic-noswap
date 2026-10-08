#!/usr/bin/env python3
"""Pack a NoSwap release from the built mod tree (mods/NoSwap), without changing it.

Writes, under dist/ (git-ignored):
- dist/NoSwap/: the CORE mod (required): the DLL, its settings, the shared scripts and art, the menu archives
  (raw/), mod.ini, README.md and INSTALL.md. No character packages (no characters/ folder: the DLL simply finds none
  there). Release-only changes, made to the copies here and nowhere else:
  - the menu archives' card slots (pictures, CONTINUE bubble heads, the name texts in every language) are all blank.
    The build ships the first 21 characters' cards written in (build_origins_menu.py LEGACY), a private one among
    them; the DLL writes every installed character's card into its cache copies at startup anyway
    (origins_cards.apply with no cards: the same patch step, every slot blank);
  - the DLL's frozen legacy key of each private character (Roster.h LEGACY_KEYS) is overwritten, same length, with a
    placeholder key no package has (its kind stays reserved, nothing else moves);
  - comments in the shared scripts that name a private character are reworded (comments only: never code).
- dist/NoSwap-<Name>/: one mod per PUBLIC character (extras.py, "private" ones never): its package files at the mod
  root (noswap_character.json, Sonic1u/..., ui/...), a mod.ini (no include dirs: the DLL reads the files itself, the
  loader must not lay them over the game's) and a README.md with its moves and sprite credits (from NoSwap's README).
- dist/NoSwap-Extras/: the EXTRAS PACK, one mod with every public crossover (extras.py "crossover") package in
  characters/<folder>/ (the DLL scans every enabled mod's characters/ folder), a mod.ini like a character's (no include
  dirs) and a README.md with each one's moves and credits. The crossovers' own mods (above) are still made too.
- dist/zips/<mod>-<version>.zip: one zip per mod, holding its folder.
- with --all-in-one, also dist/all-in-one/NoSwap/: ONE mod with the core and every public character inside it
  (characters/<folder>/, the packages as built: the layout the DLL reads for a dev install), zipped as
  NoSwap-AllInOne-<version>.zip. The same release-only changes and leak check as the core. Crossover characters
  (extras.py "crossover": other franchises) are left out of it: they ship only as their own mods.

A leak check runs before zipping and fails the release if any private character's key, name, file names, package or
art is found in any output (see leak_check), or if a card slot in the menu archives isn't blank.

Run it after a full build, under the build lock so no build runs meanwhile:
    flock <build.lock> python3 tools/make_release.py [--version 1.0.0] [--no-zip] [--out <scratch folder>]
(--out: write everything there in place of dist/, for test runs.)
"""
import argparse
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import origins_cards as oc  # noqa: E402
from extras import EXTRAS, private_extras  # noqa: E402
import character_json  # noqa: E402

MOD = REPO / "mods" / "NoSwap"
DIST = REPO / "dist"
CONTEST_INTRO = REPO / "Contest Intro" / "raw" / "ui" / "ui_advertise.pac"  # (git-ignored; SHC's own file)
INSTALL = REPO / "docs" / "INSTALL.md"
AUTHOR = "Superevil"

# Public characters: package folder -> (title, its "### " heading in NoSwap's README, the start of its credit bullet).
# Private ones must never be listed. A character.json character needs no entry: release_info() takes its title from
# its "full_name" (the README heading the same, the credit bullet "**<full_name>**"), and since it isn't in this list
# it's a separate download, never in the all-in-one (memory crossover-characters.md: every character after the SHC
# entry). A make_configs.py character missing here stops the release (add it).
CHARACTERS = {
    "metal-sonic": ("Metal Sonic", "Metal Sonic", "**Metal Sonic**"),
    "fang": ("Fang the Sniper", "Fang the Sniper", "**Fang**"),
    "big": ("Big the Cat", "Big the Cat", "**Big the Cat** (\"Remix"),
    "shadow": ("Shadow the Hedgehog", "Shadow the Hedgehog", "**Shadow the Hedgehog**"),
    "blaze": ("Blaze the Cat", "Blaze the Cat", "**Blaze**"),
    "silver": ("Silver the Hedgehog", "Silver the Hedgehog", "**Silver:**"),
    "mighty": ("Mighty the Armadillo", "Mighty the Armadillo", "**Mighty**"),
    "ray": ("Ray the Flying Squirrel", "Ray the Flying Squirrel", "**Ray**"),
    "rouge": ("Rouge the Bat", "Rouge the Bat", "**Rouge**"),
    "charmy": ("Charmy Bee", "Charmy Bee", "**Charmy**"),
    "espio": ("Espio the Chameleon", "Espio the Chameleon", "**Espio**"),
    "vector": ("Vector the Crocodile", "Vector the Crocodile", "**Vector**"),
    "cream": ("Cream the Rabbit", "Cream the Rabbit", "**Cream & Cheese**"),
    "robotnik": ("Dr. Robotnik", "Dr. Robotnik", "**Dr. Robotnik**"),
    "max": ("Max the Rabbit", "Max the Rabbit", "**Max the Rabbit**"),
    "tikal": ("Tikal the Echidna", "Tikal the Echidna", "**Tikal**"),
    "mario": ("Mario", "Mario", "**Mario**"),
    "trip": ("Trip the Sungazer", "Trip the Sungazer", "**Trip**"),
    "gamma": ("E-102 Gamma", "E-102 Gamma", "**E-102 Gamma**"),
    "jet": ("Jet the Hawk", "Jet the Hawk", "**Jet the Hawk**"),
    "mecha-sonic": ("Mecha Sonic", "Mecha Sonic", "**Mecha Sonic**"),
    "sticks": ("Sticks the Badger", "Sticks the Badger", "**Sticks the Badger**"),
    "chaos": ("Chaos", "Chaos", "**Chaos**"),
    "flicky": ("Flicky", "Flicky", "**Flicky**"),
    "tails-doll": ("Tails Doll", "Tails Doll", "**Tails Doll**"),
    "bean": ("Bean the Dynamite", "Bean the Dynamite", "**Bean the Dynamite**"),
    "bark": ("Bark the Polar Bear", "Bark the Polar Bear", "**Bark the Polar Bear**"),
    "heavy": ("Heavy", "Heavy", "**Heavy** and **Bomb**"),
    "bomb": ("Bomb", "Bomb", "**Heavy** and **Bomb**"),
    "honey": ("Honey the Cat", "Honey the Cat", "**Honey the Cat**"),
    "omega": ("E-123 Omega", "E-123 Omega", "**E-123 Omega**"),
    "sally": ("Sally Acorn", "Sally Acorn", "**Sally Acorn**"),
    "marine": ("Marine the Raccoon", "Marine the Raccoon", "**Marine the Raccoon**"),
    "mephiles": ("Mephiles the Dark", "Mephiles the Dark", "**Mephiles the Dark**"),
    "emerl": ("Emerl", "Emerl", "**Emerl**"),
    # separate downloads only (extras.py "crossover"): never in the all-in-one
    "megaman": ("Mega Man", "Mega Man (Mega Man 7, separate download)", "**Mega Man**"),
    "ray-poward": ("Ray Poward", "Ray Poward (Contra: Hard Corps, separate download)", "**Ray Poward**"),
    "sparkster": ("Sparkster", "Sparkster (Rocket Knight Adventures, separate download)", "**Sparkster**"),
    "ristar": ("Ristar", "Ristar (Sega Genesis, separate download)", "**Ristar**"),
    "headdy": ("Headdy", "Dynamite Headdy (Sega Genesis, separate download)", "**Dynamite Headdy**"),
    "john-morris": ("John Morris", "John Morris (Castlevania: Bloodlines, separate download)", "**John Morris**"),
    "ecco": ("Ecco", "Ecco the Dolphin (Ecco: The Tides of Time, separate download)", "**Ecco the Dolphin**"),
    "nights": ("NiGHTS", "NiGHTS (NiGHTS into Dreams, separate download)", "**NiGHTS**"),
    "shinobi": ("Joe Musashi", "Joe Musashi (Shinobi III, separate download)", "**Joe Musashi**"),
    "pulseman": ("Pulseman", "Pulseman (Sega Genesis, separate download)", "**Pulseman**"),
    "axel": ("Axel Stone", "Axel Stone (Streets of Rage 2, separate download)", "**Axel Stone**"),
    "gilius": ("Gilius Thunderhead", "Gilius Thunderhead (Golden Axe, separate download)", "**Gilius Thunderhead**"),
}
# Extra notes for a character's README (credits that sit elsewhere in NoSwap's README)
EXTRA_CREDITS = {
    "mighty": "- His Hammer Drop follows Sonic Mania Plus, as documented by the Sonic Mania decompilation "
              "(Rubberduckycooly and contributors).",
    "ray": "- His glide follows Sonic Mania Plus, as documented by the Sonic Mania decompilation "
           "(Rubberduckycooly and contributors).",
}
CORE_SKIP_DIRS = {"characters", "cache", "__pycache__"}
CORE_SKIP_SUFFIXES = {".log", ".bak", ".new", ".stamp", ".pyc"}


def fail(msg):
    sys.exit(f"make_release: {msg}")


def release_info(e):
    """(title, README heading, credit bullet start) of a public extra: its CHARACTERS entry, else (a character.json
    character) from its full_name; None: neither."""
    if e["art"].name in CHARACTERS:
        return CHARACTERS[e["art"].name]
    if character_json.has_json(e["art"]):
        title = character_json.load(e["art"]).get("full_name") or e["name"].title()
        return title, title, f"**{title}**"
    return None


def in_all_in_one(e):
    """In the all-in-one: listed in CHARACTERS and not a crossover (anything newer is a separate download)."""
    return e["art"].name in CHARACTERS and not e["crossover"]


def folder_name(pkg_json_name):
    """ "METAL SONIC" -> "NoSwap-MetalSonic" """
    return "NoSwap-" + "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", pkg_json_name) if w)


def read_version():
    m = re.search(r'^Version="?([^"\r\n]*)"?', (MOD / "mod.ini").read_text(), re.M)
    return m.group(1) if m else "0.0.0"


# ---------------------------------------------------------------- NoSwap's README, cut into pieces
def readme_sections(text):
    lines = text.splitlines()
    heads = {}  # "### " heading -> its body lines
    cur = None
    for line in lines:
        if line.startswith("### "):
            cur = line[4:].strip()
            heads[cur] = []
        elif line.startswith("## "):
            cur = None
        elif cur is not None:
            heads[cur].append(line)
    credits, bullets, inside = [], [], False
    for line in lines:
        if line.startswith("**Character sprites**"):
            inside = True
            continue
        if inside and line.startswith("**") and not line.startswith("**Character"):
            break
        if inside:
            if line.startswith("- "):
                bullets.append([line])
            elif line.startswith("  ") and bullets:
                bullets[-1].append(line)
    credits = ["\n".join(b) for b in bullets]
    paras = [p.strip() for p in text.split("\n\n")]
    basics = next((p for p in paras if p.startswith("All extras keep Sonic's basic moves")), "")
    ymoves = next((p for p in paras if p.startswith("Y moves work in all four games")), "")
    superp = next((p for p in paras if p.startswith("Every extra has a Super form")), "")
    return heads, credits, basics, ymoves, superp


def character_readme(folder, title, version, readme):
    heads, credits, basics, ymoves, superp = readme
    _, heading, credit_start = release_info(next(e for e in EXTRAS if e["art"].name == folder))
    if heading not in heads:
        fail(f"NoSwap's README has no '### {heading}' section (for {folder})")
    found = [c for c in credits if c.startswith("- " + credit_start)]
    if len(found) != 1:
        fail(f"NoSwap's README credits: {len(found)} bullets start with {credit_start!r} (for {folder})")
    moves = "\n".join(heads[heading]).strip()
    extra = EXTRA_CREDITS.get(folder, "")
    owner = "Mario © Nintendo; Sonic Origins © SEGA." if folder == "mario" else f"{title} and Sonic Origins © SEGA."
    return f"""# NoSwap: {title}

{title} as an extra playable character in Sonic Origins (Sonic 1, Sonic CD, Sonic 2 and Sonic 3 & Knuckles), for
**NoSwap**. Nobody is replaced: Sonic, Tails, Knuckles and Amy are all still there.

**This needs the NoSwap core mod,** installed and enabled, and the **same version** as this one ({version}).
See INSTALL.md in the NoSwap core for how to install, pick characters and uninstall safely.

## Moves

{basics}

{moves}

{superp}

{ymoves}

## Sprite credits

{found[0]}
{extra}

## The games and characters

{owner} This is an unofficial fan mod. It isn't affiliated with or endorsed by SEGA{" or Nintendo" if folder == "mario" else ""}.
""".replace("\n\n\n", "\n\n")


def character_ini(title, version):
    return f"""[Desc]
Title="NoSwap: {title}"
Description="{title} for NoSwap. Requires the NoSwap mod (the core), installed, enabled and the same version ({version})."
Version="{version}"
Author="{AUTHOR}"

[Main]
; A NoSwap character package. The NoSwap DLL (in the NoSwap core mod) finds this folder in the mod loader's list of
; enabled mods (it has a noswap_character.json at its root) and reads its files itself. It must NOT be an include dir:
; the loader would then lay its player scripts over everyone's. HiteModLoader parses counts as plain integers.
IncludeDirCount=0
DependsCount=0
SaveFile=""
"""


EXTRAS_PACK = "NoSwap-Extras"  # (the Origins extras pack's mod folder)


def extras_pack_ini(titles, version):
    return f"""[Desc]
Title="NoSwap: Extras Pack"
Description="The {len(titles)} crossover characters for NoSwap in one mod: {', '.join(titles)}. Requires the NoSwap mod (the core), installed, enabled and the same version ({version})."
Version="{version}"
Author="{AUTHOR}"

[Main]
; NoSwap character packages, one per characters/<folder>/. The NoSwap DLL (in the NoSwap core mod) finds this mod in
; the mod loader's list of enabled mods, scans its characters folder and reads the files itself. It must NOT be an
; include dir: the loader would then lay their player scripts over everyone's. HiteModLoader parses counts as plain
; integers.
IncludeDirCount=0
DependsCount=0
SaveFile=""
"""


def extras_pack_readme(entries, version, readme):
    """entries: (folder, title) of each crossover in the pack. Each one's moves and sprite credits as its own README."""
    heads, credits, basics, ymoves, superp = readme
    lst, sections, bullets, owners = [], [], [], []
    for folder, title in entries:
        _, heading, credit_start = release_info(next(e for e in EXTRAS if e["art"].name == folder))
        if heading not in heads:
            fail(f"NoSwap's README has no '### {heading}' section (for {folder})")
        found = [c for c in credits if c.startswith("- " + credit_start)]
        if len(found) != 1:
            fail(f"NoSwap's README credits: {len(found)} bullets start with {credit_start!r} (for {folder})")
        lst.append(f"- **{title}** (characters/{folder})")
        sections.append(f"### {title}\n\n" + "\n".join(heads[heading]).strip())
        bullets.append(found[0] + ("\n" + EXTRA_CREDITS[folder] if folder in EXTRA_CREDITS else ""))
        owners.append(MANIA_OWNERS.get(folder, f"{title} © SEGA."))
    sections, bullets, owners = "\n\n".join(sections), "\n".join(bullets), " ".join(dict.fromkeys(owners))
    return f"""# NoSwap: Extras Pack

The {len(entries)} crossover characters for **NoSwap** in Sonic Origins (Sonic 1, Sonic CD, Sonic 2 and Sonic 3 &
Knuckles), in one mod. Nobody is replaced: Sonic, Tails, Knuckles and Amy are all still there.

{chr(10).join(lst)}

**This needs the NoSwap core mod,** installed and enabled, and the **same version** as this one ({version}).
See INSTALL.md in the NoSwap core for how to install, pick characters and uninstall safely. Install this pack like a
character mod. Each of these characters is also a download of its own ("NoSwap: Mega Man" and so on): use either this
pack or those, not both (with both enabled, the first one found is used and the other is left out).

## Moves

{basics}

{sections}

{superp}

{ymoves}

## Sprite credits

{bullets}

## The games and characters

{owners} Sonic the Hedgehog and Sonic Origins © SEGA. This is an unofficial fan mod. It isn't affiliated with or
endorsed by SEGA or any other rights holder named here.
""".replace("\n\n\n", "\n\n")


def core_ini(version):
    text = (MOD / "mod.ini").read_text()
    text = re.sub(r'^Description=.*$', 'Description="Adds extra playable characters to the classic games without '
                  'replacing anyone. This is the core: install the characters you want as separate NoSwap mods '
                  '(NoSwap: <name>), the same version."', text, flags=re.M)
    text = re.sub(r'^Version=.*$', f'Version="{version}"', text, flags=re.M)
    return text


def aio_ini(version):
    text = (MOD / "mod.ini").read_text()
    text = re.sub(r'^Description=.*$', 'Description="Adds 35 extra playable characters to the classic games without '
                  'replacing anyone. All-in-one: the core and every character in one mod."', text, flags=re.M)
    text = re.sub(r'^Version=.*$', f'Version="{version}"', text, flags=re.M)
    return text


AIO_NOTE = """> **This is the all-in-one edition:** the NoSwap core with every character inside it (characters/). Don't
> install it next to the separate NoSwap core or character mods: use one or the other.
"""


CORE_NOTE = """> **This is the NoSwap core.** It holds no characters by itself: each character comes as its own mod
> ("NoSwap: Metal Sonic", "NoSwap: Chaos"...). Install this core first, then any characters you like, all the same
> version. See INSTALL.md.
"""


# ---------------------------------------------------------------- release-only changes to the core copy
def blank_menu_cards(core):
    desc = oc.load_descriptor(core / oc.DESCRIPTOR)
    n = 0
    for a in desc["archives"]:
        p = core / a["path"]
        data = p.read_bytes()
        out = oc.apply(data, a, {})  # every slot blank (and checks the size and literal headers first)
        if out != data:
            p.write_bytes(out)
            n += 1
    return n, len(desc["archives"])


def patch_dll_keys(core, private):
    """Overwrite each private character's frozen key (Roster.h LEGACY_KEYS) in the DLL, same length."""
    dll = core / "NoSwapS3K.dll"
    data = bytearray(dll.read_bytes())
    notes = []
    for e in private:
        key = e["key"].encode()
        tail = len(e["art"].name)
        ph = ("r" + str(e["id"])).ljust(tail, "_")
        if len(ph) != tail:
            fail(f"no same-length placeholder for {e['key']}")
        new = ("noswap." + ph).encode()
        for enc_old, enc_new in ((key + b"\0", new + b"\0"),
                                 (e["key"].encode("utf-16-le") + b"\0\0", ("noswap." + ph).encode("utf-16-le") + b"\0\0")):
            count = data.count(enc_old)
            if count > 1:
                fail(f"{e['key']} appears {count} times in the DLL: expected at most 1 (check before patching)")
            if count:
                i = data.index(enc_old)
                data[i:i + len(enc_old)] = enc_new
                notes.append(f"{e['key']} -> noswap.{ph} at 0x{i:X}")
    dll.write_bytes(bytes(data))
    return notes


def private_name_patterns(private):
    """Regexes (bytes) for a private character's name as a word (not "Power Surge"-style move names)."""
    pats = []
    for e in private:
        for form in {e["name"], e["name"].title()}:
            w = re.escape(form.encode())
            pats.append(re.compile(rb"(?<![A-Za-z0-9_.])(?<!Power )" + w + rb"(?![A-Za-z0-9_])"))
    return pats


def reword_script_comments(core, private):
    """Comments (after '//') in the shared scripts that name a private character: reworded. Code is untouched."""
    changed = 0
    for p in core.rglob("*.txt"):
        original = p.read_bytes().decode("utf-8", errors="surrogateescape")  # (no newline translation: CRLF kept)
        lines = original.split("\n")
        out = []
        for line in lines:
            if "//" in line:
                code, comment = line.split("//", 1)
                new = comment
                for e in private:
                    for form in {e["name"], e["name"].title()}:
                        f = re.escape(form)
                        new = re.sub(rf"\s*\({f}\)", "", new)
                        new = re.sub(rf"(?<![\w.]){f}'s\s+(?=Power\b)", "the ", new)
                        new = re.sub(rf"(?<![\w.])(?<!Power ){f}'s\b", "its", new)
                        new = re.sub(rf"(?<![\w.])(?<!Power ){f}(?!\w)", "an extra", new)
                if new != comment:
                    line = code + "//" + new
                    changed += 1
            out.append(line)
        text = "\n".join(out)
        if text != original:
            p.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    return changed


# ---------------------------------------------------------------- the leak check
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leak_check(outputs, private, public_folders):
    problems = []
    keys = [e["key"] for e in private]
    folders = [e["art"].name for e in private]
    name_pats = private_name_patterns(private)
    file_pats = [re.compile(rf"Extra{e['n']}(?!\d)|_x{e['n']}(?!\d)", re.I) for e in private]
    # art: every file of a private package whose bytes no public package and no core file shares
    shared = set()
    for p in MOD.rglob("*"):
        if p.is_file() and not p.relative_to(MOD).parts[0] in ("characters", "cache"):
            shared.add(sha(p))
    for f in public_folders:
        shared |= {sha(p) for p in (MOD / "characters" / f).rglob("*") if p.is_file()}
    private_art = {}
    for f in folders:
        for p in (MOD / "characters" / f).rglob("*"):
            if p.is_file() and sha(p) not in shared:
                private_art[sha(p)] = f"characters/{f}/{p.relative_to(MOD / 'characters' / f)}"
    # the mods: exactly the core and the public characters
    want = {"NoSwap"} | {folder_name(read_json(MOD / "characters" / f / "noswap_character.json")["name"]) for f in public_folders}
    packed = {e["art"].name for e in EXTRAS if e["crossover"] and e["art"].name in public_folders}
    if packed:  # (the extras pack: every public crossover)
        want.add(EXTRAS_PACK)
    have = {d.name for d in outputs}
    if have != want:
        problems.append(f"mod folders: unexpected {sorted(have - want)}, missing {sorted(want - have)}")
    files = 0
    for d in outputs:
        pj = d / "noswap_character.json"
        if d.parent.name == "all-in-one":  # the all-in-one: exactly the public packages, in characters/
            inside = {c.name for c in (d / "characters").iterdir()} if (d / "characters").exists() else set()
            bundled = set(public_folders) - {e["art"].name for e in EXTRAS if not in_all_in_one(e)}
            if inside != bundled:
                problems.append(f"all-in-one characters/: unexpected {sorted(inside - bundled)}, "
                                f"missing {sorted(bundled - inside)}")
            for c in (d / "characters").glob("*/noswap_character.json"):
                if read_json(c)["key"] in keys:
                    problems.append(f"all-in-one: {c.parent.name} is a private package")
        elif d.name == EXTRAS_PACK:  # the extras pack: exactly the public crossovers, in characters/
            inside = {c.name for c in (d / "characters").iterdir()} if (d / "characters").exists() else set()
            if inside != packed:
                problems.append(f"{EXTRAS_PACK} characters/: unexpected {sorted(inside - packed)}, "
                                f"missing {sorted(packed - inside)}")
            if pj.exists():
                problems.append(f"{EXTRAS_PACK} has a noswap_character.json at its root")
            for c in (d / "characters").glob("*/noswap_character.json"):
                if read_json(c)["key"] in keys:
                    problems.append(f"{EXTRAS_PACK}: {c.parent.name} is a private package")
        elif d.name == "NoSwap":
            if (d / "characters").exists():
                problems.append("the core has a characters/ folder")
            if list(d.rglob("noswap_character.json")):
                problems.append("the core holds a package (noswap_character.json)")
        elif read_json(pj)["key"] in keys:
            problems.append(f"{d.name} is a private package")
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            files += 1
            rel = f"{d.name}/{p.relative_to(d).as_posix()}"
            low = [c.lower() for c in p.relative_to(d).parts]
            if any(c in folders for c in low) or any(fp.search(rel) for fp in file_pats):
                problems.append(f"{rel}: a private character's file name")
            data = p.read_bytes()
            for k in keys:
                if k.encode() in data or k.encode("utf-16-le") in data:
                    problems.append(f"{rel}: contains the key {k}")
            for pat in name_pats:
                m = pat.search(data)
                if m:
                    problems.append(f"{rel}: names a private character at byte {m.start()}: "
                                    f"{data[max(0, m.start() - 30):m.end() + 30]!r}")
            for e in private:
                for form in {e["name"], e["name"].title()}:
                    u = form.encode("utf-16-le")
                    i = data.find(u)
                    while i >= 0:
                        before = data[max(0, i - 12):i].decode("utf-16-le", "ignore")
                        after = data[i + len(u):i + len(u) + 2].decode("utf-16-le", "ignore")
                        if not before.endswith("Power ") and not (before[-1:].isalnum() or after[:1].isalnum()):
                            problems.append(f"{rel}: names a private character (UTF-16) at byte {i}")
                            break
                        i = data.find(u, i + 1)
            if private_art and sha(p) in private_art:
                problems.append(f"{rel}: byte-identical to private art {private_art[sha(p)]}")
    # the menu archives: every card slot blank
    core = DIST / "NoSwap"
    desc = oc.load_descriptor(core / oc.DESCRIPTOR)
    for a in desc["archives"]:
        data = (core / a["path"]).read_bytes()
        if oc.apply(data, a, {}) != data:
            problems.append(f"NoSwap/{a['path']}: a card slot isn't blank")
    return problems, files, len(private_art)


def read_json(p):
    import json
    return json.loads(p.read_text())


# ---------------------------------------------------------------- output
def size_of(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def zip_mod(d, version):
    stem = "NoSwap-AllInOne" if d.parent.name == "all-in-one" else d.name
    z = DIST / "zips" / f"{stem}-{version}.zip"
    z.parent.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(d.rglob("*")):
            if p.is_file():
                arc = f"{d.name}/{p.relative_to(d).as_posix()}"
                zf.write(p, arc)
                names.append(arc)
    with zipfile.ZipFile(z) as zf:
        if sorted(zf.namelist()) != sorted(names) or zf.testzip() is not None:
            fail(f"{z.name} doesn't read back")
    return z


# ---------------------------------------------------------------- Mania Lock-On (its own mod; not part of main())
LOCKON = REPO / "mods" / "ManiaLockOn"
LOCKON_FILES = ["mod.ini", "ManiaLockOn.dll", "ConfigSchema.json", "README.md"]  # (+ patches/raw/**/*.mlp)


def pack_lockon(version=None, zip_it=True):
    """Pack Mania Lock-On (mods/ManiaLockOn: the SONIC MANIA button, native/lockon/) as its own release: dist/ManiaLockOn/
    with only what the mod needs (LOCKON_FILES and its menu patches; never what its DLL writes in a game's copy: raw/,
    cache/, the log, the player's ManiaLockOn.ini) and dist/zips/ManiaLockOn-<version>.zip. No decompilation and no
    game files: the patches are differences the DLL applies to the player's own menu archives. Not run by main(): call it
    on request after a full build, under the build lock, e.g.
        flock <build.lock> python3 -c "import sys; sys.path.insert(0, 'tools'); import make_release; make_release.pack_lockon()"
    -> the folder (and the zip, unless zip_it is false)."""
    import json
    for name in LOCKON_FILES:
        if not (LOCKON / name).is_file():
            fail(f"mods/ManiaLockOn/{name} is missing: run the build first")
    json.loads((LOCKON / "ConfigSchema.json").read_text())  # (HedgeModManager's Configure needs valid JSON)
    patches = sorted((LOCKON / "patches").rglob("*.mlp"))
    if not any(p.parent.name == "ui" for p in patches) or not any(p.parent.name == "text" for p in patches):
        fail("mods/ManiaLockOn/patches has no menu patches: run the build first (tools/build_lockon_menu.py)")
    if any(p.read_bytes()[:4] != b"MLOP" for p in patches):
        fail("mods/ManiaLockOn/patches: a file that isn't a Lock-On patch")
    ini = (LOCKON / "mod.ini").read_text()
    version = version or re.search(r'^Version="?([^"\n]*)"?', ini, flags=re.M).group(1)
    out = DIST / "ManiaLockOn"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in LOCKON_FILES:
        shutil.copy2(LOCKON / name, out / name)
    (out / "mod.ini").write_text(re.sub(r'^Version=.*$', f'Version="{version}"', ini, flags=re.M))
    for p in patches:
        (out / p.relative_to(LOCKON)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out / p.relative_to(LOCKON))
    allowed = set(LOCKON_FILES) | {p.relative_to(LOCKON).as_posix() for p in patches}
    extra = [p for p in out.rglob("*") if p.is_file() and p.relative_to(out).as_posix() not in allowed]
    if extra:
        fail(f"dist/ManiaLockOn: unexpected files {extra}")
    z = zip_mod(out, version) if zip_it else None
    print(f"dist/ManiaLockOn/: {human(size_of(out))}, {len(allowed)} files"
          + (f"; {z.relative_to(REPO)}: {human(z.stat().st_size)}" if z else ""))
    return out


# ---------------------------------------------------------------- NoSwap for Sonic Mania (the decompilation mod; --mania)
# The Mania release (pack_mania; main() runs it with --mania and nothing of the Origins flow):
# - <out>/NoSwapMania/: the core mod (the code mod for both platforms, mod.ini, modSettings.ini, Data/Game/Game.xml, the
#   sounds) WITH the core roster inside it (Data/Sprites/NoSwap/<folder>/): the all-in-one. The core roster is every
#   public Mania character that isn't a crossover (extras.py "crossover"), plus the Mania-only ones (tools/mania_only.py:
#   Amy). Its save select atlas is rebuilt for the release from every PUBLIC package (core and separate downloads: a
#   separate one's pictures are then in the atlas, shown only when that package is installed; never a private one's).
#   README.md and the decompilation's license texts (LICENSES/) go with it.
# - <out>/NoSwapMania-<Name>/: one mod per crossover (separate downloads only, memory crossover-characters.md): its
#   package at Data/Sprites/NoSwap/<folder>/ (the core's DLL scans every active mod's Data/Sprites/NoSwap), a mod.ini
#   with no logic file, and a README.md with its moves and credits.
# - <out>/NoSwapMania-Extras/: the EXTRAS PACK, every crossover in one mod: their packages (Data/Sprites/NoSwap/<folder>/),
#   their own sounds (Data/SoundFX/NoSwap/<folder>/) with one Game.xml loading them all, a mod.ini with no logic file and
#   a README.md with their moves and credits. The one-character mods above are still made too.
# - <out>/zips/<mod>-<version>.zip, one per mod.
# Private characters (extras.py "private") are never packed; the Mania leak check (mania_leak_check) fails the release
# if any of their keys, names, folder names or art bytes is found in any output. No decompilation and no game files are
# shipped: players bring their own decomp and their own Sonic Mania (RSDKv5 decompilation license v2.1, memory
# mania-port.md). Default <out>: dist/mania. Test runs: --out <a scratch folder>.
MANIA_MOD = REPO / "mods" / "NoSwapMania"
MANIA_PKG_REL = Path("Data") / "Sprites" / "NoSwap"
MANIA_PACKAGES = MANIA_MOD / MANIA_PKG_REL
MANIA_CORE_FILES = ["NoSwapMania.dll", "NoSwapMania.so", "Data/Game/Game.xml"]  # (+ Data/SoundFX/**/*.wav)
MANIA_ATLAS_FILES = ["SaveSelectAtlas.bin", "SaveSelectAtlas.gif"]
MANIA_DECOMP = Path.home() / "Code" / "mania" / "Sonic-Mania-Decompilation"
MANIA_LICENSES = {  # shipped as LICENSES/<name>: the mod is built against RSDKv5-GameAPI and the decomp's structures
    "RSDKv5-Decompilation-LICENSE.md": MANIA_DECOMP / "dependencies" / "RSDKv5" / "LICENSE.md",
    "Sonic-Mania-Decompilation-LICENSE.md": MANIA_DECOMP / "LICENSE.md",
}
MANIA_TITLE = "NoSwap: Extra Characters (Sonic Mania)"
# Mania entries where release_info() doesn't fit: folder -> (title, its "### " heading in NoSwap's README, the start of its
# credit bullet there); a None heading / credit: written here (MANIA_ONLY_TEXT)
MANIA_INFO = {
    "nights": ("NiGHTS", "NiGHTS (NiGHTS into Dreams, separate download)", "**NiGHTS**"),
    "shinobi": ("Joe Musashi", "Joe Musashi (Shinobi III, separate download)", "**Joe Musashi**"),
    "pulseman": ("Pulseman", "Pulseman (Sega Genesis, separate download)", "**Pulseman**"),
    "axel": ("Axel Stone", "Axel Stone (Streets of Rage 2, separate download)", "**Axel Stone**"),
    "gilius": ("Gilius Thunderhead", "Gilius Thunderhead (Golden Axe, separate download)", "**Gilius Thunderhead**"),
    "amy": ("Amy Rose", None, None),
    "ecco": ("Ecco the Dolphin", "Ecco the Dolphin (Ecco: The Tides of Time, separate download)", "**Ecco the Dolphin**"),
    "headdy": ("Dynamite Headdy", "Dynamite Headdy (Sega Genesis, separate download)", "**Dynamite Headdy**"),
}
# Lines a character's Mania moves need beyond NoSwap's README section (folder -> markdown, put first)
MANIA_MOVES_EXTRA = {
    "ecco": "- **In water** (the main water and the pools) he swims freely: he turns toward the d-pad and builds speed, "
            "gliding to a stop with nothing held. **Y** is a charging ram that breaks enemies and, as Knuckles does, "
            "walls; leaving the water going up is a leap.",
}
MANIA_ONLY_TEXT = {
    "amy": {
        "moves": """- **Hammer Jump:** press jump again in mid-air: she swings her Piko Piko Hammer round in a spin that hits
  everything it reaches (with a shield, hold up for the shield's own move instead).
- **Hammer Dash:** hold jump in the air for a third of a second (the drop-dash charge sound), then land: she charges
  forward hammer first for up to a second, smashing what's in the way. Let go, hit a wall or a steep slope to stop.
- **Hammer Throw:** Y while Super: she throws her hammer in an arc. Super Amy glows in her own pinks.
- She has no Peel Out or drop dash: those buttons are her hammer moves.""",
        "credit": "- **Amy Rose**: Sonic Origins Plus' own Classic Amy sprites (her player sprites, HUD icon, signpost face and "
                  "results continue icon) and her four hammer sounds, by SEGA / Sonic Team, taken from the official Sonic "
                  "Origins Plus files. Mania has no Amy of its own; she's never added to Origins, where she is the Plus "
                  "DLC's. Amy Rose and Sonic Origins © SEGA.",
    },
}
# What each sheet asks of its users, verbatim (testmods/*/SOURCE.txt, testmods/*Link.txt, docs/credits-audit.md);
# characters whose sheets state no terms beyond their credits have none here
AKIMACA = "\"Original sprites by SEGA, Sonic Team & me (Akimaca). Free to use tho give credit where it's due!!!\""
MANIA_TERMS = {
    "metal-sonic": AKIMACA, "fang": AKIMACA, "espio": AKIMACA, "vector": AKIMACA,
    "max": "\"Original sprites by SEGA, Sonic Team & me (Akimaca). Design tweaks by me (Akimaca) Free to use tho give "
           "credit where it's due!!!\"",
    "heavy": "\"Original sprites by SEGA, Sonic Team & me (Akimaca). Free to use, just give credit where it's due!!!\"",
    "bomb": "\"Original sprites by SEGA, Sonic Team & me (Akimaca). Free to use, just give credit where it's due!!!\"",
    "big": "\"DO: Use this sheet as you like, but GIVE CREDIT. DO NOT: Claim this sheet as your own or otherwise steal.\"",
    "blaze": "\"ORIGINAL SPRITES BY SEGA, SONIC TEAM, MADZ (MANIAMADNEZ) AND SELPHY GEUMJA FREE TO USE, BUT REMEMBER TO GIVE "
             "CREDIT!\"",
    "rouge": "\"ORIGINAL SPRITES BY SEGA, SONIC TEAM & DELTACONDUIT FREE TO USE, BUT GIVE CREDIT. DO NOT EDIT "
             "EFFORTLESSLY.\"",
    "charmy": "\"Sprites by Casteor573. Free to use but give credit!!\"",
    "cream": "\"No permission needed, but some cred. to Sega & me would be nice.\"",
    "robotnik": "\"NO EDITS\" \"NO RECOLORS\" \"NOT FOR EXE STUFF\" \"SHEET BY DR. CHEESECRUMBZ\" \"PERMISSION? YE. "
                "CREDITS? ALSO YE.\"",
    "tikal": "\"Tikal sprites made by SunnyVies. If used, please give credit. No permission needed.\"",
    "mario": "\"MARIO (SONIC 1-STYLE) MADE BY JON GANDEE. GIVE CREDIT IF USED\"; his fireball sound (ripped by "
             "lelegofrog, The Sounds Resource): none stated (credited)",
    "jet": "\"Feel free to use this sheet in anyway. And if you use this in any manner i would appriciate if you credit "
           "me. Don't steal or claim as your own. And if you put this up on a website leave the tag and credits.\"",
    "mecha-sonic": "\"Custome Mecha Sonic sprites made by Domenico. Give credit if used. This sheet is only to be hosted "
                   "at http://www.themysticalforestzone.com/\" (the sheet itself is not included)",
    "sticks": "\"Sprite by Neo-Fire-Sonic and UberHawg. Ripped from Sonic Legends. Give Credit or else\"",
    "flicky": "\"Give Credits if Used\" \"Do Not Make This .exe Related\"",
    "bean": "\"ORIGINAL SPRITES BY SEGA, SONIC TEAM & DELTACONDUIT. FREE TO USE, BUT GIVE CREDIT. DO NOT EDIT. DON'T USE "
            "THESE SPRITES FOR EXE STUFF.\"",
    "bark": "\"ORIGINAL SPRITES BY SEGA, SONIC TEAM & DELTACONDUIT. FREE TO USE, BUT GIVE CREDIT. DO NOT EDIT. DON'T USE "
            "THESE SPRITES FOR EXE STUFF.\"",
    "honey": "\"If used, please give credit and link back to my DeviantART page - deviantart.com/xeric-studios\"",
    "omega": "\"REQUIREMENTS FOR USE: Give credit, alright?\" \"Give credit to Gussprint, and do not, I repeat, DO NOT "
             "steal and/or claim as own.\"",
    "sally": "\"Sprites made by E-122-Psi. Permission not needed but please don't steal credit.\"",
    "marine": "\"Just give credit.\"",
    "emerl": "\"Give credit please to the \"Mod.Gen Project Team\"- it's the best way to say thank you and to let people "
             "know where to find more sprites!\"",
    "megaman": "\"Please do not steal. Only for tSR.\" (the sheet itself is not included); his Mega Buster sounds (Mega Man 4, "
               "ripped by J-Sinn, The Sounds Resource): none stated (credited)",
    "ray-poward": "\"No need for credits but don't claim as your own.\"",
    "sparkster": "\"Assets (c) Konami. Original rip by Jack Rost, re-ripped by UltraHype97. Give credit if used!\"",
    "headdy": "\"Credit is optional, but don't steal. This game belongs to Treasure and Sega.\"",
    "john-morris": "\"Original assets by Konami. Orig. rip by Badbatman3, re-ripped by UltraHype97. Give credit if used!\"; "
                   "items: \"no credit needed but don't steal\"",
    "nights": "\"no credit needed\" (credited anyway)",
    "shinobi": "\"Shinobi and all sprites here are owned by Sega, so no credit needed, but do not steal or claim as your "
               "own.\"; his Ninjutsu sound (The Revenge of Shinobi, The Sounds Resource): none stated (credited)",
    "axel": "\"no credit needed but don't steal. Sprites: Sega / Ancient\" (credited anyway); his Grand Upper voice (Streets of Rage 2, "
            "ripped by Nai255, The Sounds Resource): \"No credit needed, but feedback is welcome\" (credited)",
    "pulseman": "none stated on the page (credited anyway; the sheet's own tag: \"Ripped by Jackster\")",
    "ristar": "none stated (the sheets' footers give only their credits and \"Ristar is (c) Sega\")",
    "gilius": "none stated on either page (credited anyway); his Earthquake sound (Golden Axe II, The Sounds Resource): "
              "none stated (credited)",
}
# Owners of the non-Sonic characters (for each crossover's README)
MANIA_OWNERS = {"megaman": "Mega Man © Capcom.", "ray-poward": "Contra and Ray Poward © Konami.",
                "sparkster": "Rocket Knight Adventures and Sparkster © Konami.", "ristar": "Ristar © SEGA.",
                "headdy": "Dynamite Headdy © Treasure and SEGA.", "john-morris": "Castlevania: Bloodlines and John Morris © Konami.",
                "ecco": "Ecco the Dolphin and Ecco: The Tides of Time © SEGA (developed by Novotrade).",
                "nights": "NiGHTS and NiGHTS into Dreams © SEGA / Sonic Team.",
                "shinobi": "Shinobi, Shinobi III / The Super Shinobi II and Joe Musashi © SEGA.",
                "pulseman": "Pulseman © Game Freak / SEGA.",
                "axel": "Streets of Rage and Axel Stone © SEGA.",
                "gilius": "Golden Axe, Golden Axe II and Gilius Thunderhead © SEGA.",
                "mario": "Mario © Nintendo."}


def mania_folders():
    """The Mania packages built in mods/NoSwapMania (folder names, those with a noswap_character.json)."""
    return sorted(p.parent.name for p in MANIA_PACKAGES.glob("*/noswap_character.json"))


def mania_roster():
    """(core, crossovers, left_out): the release's Mania characters as dicts {folder, title, heading, credit, key, name,
    order, crossover}, each list in the save select's order; left_out: (folder, why) for built packages not shipped."""
    from mania_only import MANIA_ONLY
    private = {e["art"].name for e in private_extras()}
    by_folder = {e["art"].name: e for e in EXTRAS}
    mania_only = {e["art"].name: e for e in MANIA_ONLY}
    core, cross, out = [], [], []
    for f in mania_folders():
        pkg = read_json(MANIA_PACKAGES / f / "noswap_character.json")
        e = by_folder.get(f) or mania_only.get(f)
        if f in private or (e and e.get("private")):
            out.append((f, "private"))
            continue
        if e is None:
            out.append((f, "not in tools/extras.py or tools/mania_only.py"))
            continue
        if f in MANIA_INFO:
            title, heading, credit = MANIA_INFO[f]
        else:
            info = release_info(e)
            if info is None:
                fail(f"Mania package {f}: no entry in CHARACTERS / MANIA_INFO and no character.json")
            title, heading, credit = info
        c = dict(folder=f, title=title, heading=heading, credit=credit, key=pkg["key"], name=pkg["name"],
                 order=pkg.get("order", 1 << 30), crossover=bool(e.get("crossover")))
        (cross if c["crossover"] else core).append(c)
    for lst in (core, cross):
        lst.sort(key=lambda c: (c["order"], c["folder"]))
    return core, cross, out


def mania_folder_name(c):
    """ "JOHN MORRIS" -> "NoSwapMania-JohnMorris" (a crossover's mod folder: the package's name, as folder_name)."""
    return "NoSwapMania-" + "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", c["name"]) if w)


def mania_version():
    m = re.search(r'^Version\s*=\s*"?([^"\r\n]*)"?', (MANIA_MOD / "mod.ini").read_text(), re.M)
    return m.group(1).strip() if m else "0.0.0"


def mania_credit(c, credits):
    """The character's sprite credit bullet (NoSwap's README, as is) plus its sheet's terms, verbatim."""
    if c["folder"] in MANIA_ONLY_TEXT:
        text = MANIA_ONLY_TEXT[c["folder"]]["credit"]
    else:
        found = [b for b in credits if b.startswith("- " + c["credit"])]
        if len(found) != 1:
            fail(f"NoSwap's README credits: {len(found)} bullets start with {c['credit']!r} (Mania: {c['folder']})")
        text = found[0]
    if c["folder"] in MANIA_TERMS:
        text += f"\n  - The sheet's terms: {MANIA_TERMS[c['folder']]}"
    return text


def mania_moves(c, heads):
    if c["folder"] in MANIA_ONLY_TEXT:
        return MANIA_ONLY_TEXT[c["folder"]]["moves"]
    if c["heading"] not in heads:
        fail(f"NoSwap's README has no '### {c['heading']}' section (Mania: {c['folder']})")
    text = "\n".join(heads[c["heading"]]).strip()
    return (MANIA_MOVES_EXTRA[c["folder"]] + "\n" + text) if c["folder"] in MANIA_MOVES_EXTRA else text


MANIA_INSTALL = """## What you need

- **Sonic Mania**, your own copy (Steam). Its `Data.rsdk` holds the game's data; nothing of the game comes with this
  mod.
- **The Sonic Mania decompilation** (RSDKv5U), which runs Mania from your own `Data.rsdk` and has the mod loader this
  mod needs. Use an official release (two downloads: the engine's `RSDKv5U.exe` from
  github.com/RSDKModding/RSDKv5-Decompilation and the game's `v5U/Game.dll` from
  github.com/RSDKModding/Sonic-Mania-Decompilation, Releases; tested with v1.1.1) or build it yourself. The official
  releases have the Plus content switched off (no Mighty, Ray or Encore): NoSwap's extras work either way; for Plus,
  build the decompilation yourself, as its README describes. It doesn't come with this mod either: bring your own. Put it in your Sonic Mania folder, next to
  `Data.rsdk` (that's where most people keep it, and where Mania Lock-On looks for it).
- Windows: `NoSwapMania.dll` is used. Linux (a native decomp build): `NoSwapMania.so`. Both are in the mod.

## Installing

1. In the folder you run the decompilation from (where `RSDKv5U.exe` / `RSDKv5U` is), open the `mods` folder (make it
   if it isn't there).
2. Copy the `NoSwapMania` folder into it: `mods/NoSwapMania/mod.ini` must be where it ends up.
3. Enable it: with the game closed, create or edit `mods/modconfig.ini` (a plain text file) so it has:

       [Mods]
       NoSwapMania=y

   (The decompilation's developer menu has a Mods screen that does the same: set `devMenu=y` under `[Game]` in
   `Settings.ini` and press Esc in game. Either way, restart the game after changing mods.)

4. **Separate characters** (the crossover downloads, "NoSwapMania-Ecco" and so on) go in `mods` the same way, next to
   `NoSwapMania`, and need enabling the same way (`NoSwapMania-Ecco=y`). They need the NoSwapMania mod enabled and the
   same version. The mod finds every enabled mod's characters by itself; the order doesn't matter.

To uninstall, disable or delete the folders. Your saves stay Mania's own: NoSwap keeps which save slot is which extra in
its own file, `NoSwapManiaSlots.ini`, next to the game's `SaveData.bin`.

## Playing as an extra character

In **Mania Mode**'s save select, on **No Save** or a new save slot, press **up/down** to cycle the characters: Sonic &
Tails, Sonic, Tails, Knuckles (and Mighty and Ray, with Plus) as usual, then the extras, then round again. The slot shows the
extra's own picture, and a numbered save remembers its extra.

- **Y** (keyboard: W by default) is each extra's attack or special move. Mid-air moves are on the jump button, as
  Sonic's drop dash is.
- **Super:** with all the Chaos Emeralds and 50 rings, jump and press Y in mid-air. Extras keep their own moves and
  sprites, with their own colours glowing.
- A test switch, in `mods/NoSwapMania/modSettings.ini`: `Character = <a character's folder name>` (for example
  `bark`) makes every Sonic that character everywhere, including the decompilation's dev menu stage select;
  `Character = menu` (the default) is the save select; `none` turns the extras off.

## Sonic Mania from Sonic Origins: Mania Lock-On

**Mania Lock-On** is a separate Sonic Origins mod (HedgeModManager) that adds a SONIC MANIA button to Origins' main menu
and starts your own copy of the decompilation from there. It works with or without NoSwap for Origins. It's its own
download; see its README.
"""

MANIA_LIMITS = """## Known issues and limits

- **Mania Mode only.** Time Attack, Competition and Encore Mode don't offer the extras.
- **Special stages:** in the UFO stages an extra is drawn as its 2D spin ball (jump frames) in place of Sonic's 3D
  model. Blue Spheres uses the extra's spin ball.
- **Scenes still showing Sonic:** the Metallic Madness shrink laser (Chibi Sonic), the Chemical Plant Act 2 Mean Bean
  boss, the Titanic Monarch Act 3 escape car, the Plus game summary icon, and Knuckles' story cutscenes for Rouge.
- **Colours:** Mania draws every sprite with its stage palette, which has room for only a few colours of a character's
  own. Where a sheet has more, its rarest shades share the nearest colour Mania has (usually a step or two apart). This
  is a palette limit, not an edit of anyone's art.
- **Other mods** that replace the Player object or the save select may not work together with NoSwap.
"""

MANIA_AI = """## How it was made

Designed, directed and tested by Superevil. The code was written with an AI coding assistant (Claude). The sprites are
not AI: every character uses sprite sheets by fan artists (Amy uses SEGA's own sprites), credited in full below. Please
check out their work!
"""

MANIA_FOUNDATIONS = """**The decompilation (not included)**

- **Sonic Mania decompilation and RSDKv5(U) decompilation:** original RSDK authors **Evening Star**; decompilation
  authors **Rubberduckycooly** and **chuliRMG**, with the decompilation's contributors. The decompilation and the
  original code are theirs and SEGA's, not ours. This mod is built against **RSDKv5-GameAPI** (RSDKModding) and the
  decompilation's object layouts, and ships none of the decompilation's code and no game files. Their licenses are in
  `LICENSES/`: non-commercial use only, credit to the authors above, no game assets. (Their rule that pre-built
  executables keep DLC off by default is for executables; this mod ships none: you bring your own build.)
- **Mighty's and Ray's moves** in NoSwap for Origins follow Sonic Mania Plus, as documented by the decompilation; in
  Mania itself Mighty and Ray are the game's own (NoSwap doesn't add them again).

**Art and sound from the games**

- Spin balls for sheets without one, the save select, HUD, act clear letters (from Mania's own credits font), signpost
  boards, monitors, flames, sparks and other effects used around the extras are Sonic Mania's or Sonic 3 & Knuckles'
  own (SEGA / Sonic Team): the small pieces the extras need, cut or recoloured for them. Amy's hammer sounds are Sonic
  Origins' (SEGA).
"""

MANIA_LEGAL = """**The games and characters**

- Sonic the Hedgehog, its characters, Sonic Mania and Sonic Origins © SEGA (Sally Acorn also Archie Comics).
- Mario © Nintendo. {others}
- This is a free, unofficial, **non-commercial** fan mod. It isn't affiliated with or endorsed by SEGA, Sonic Team or
  any other rights holder named here. Don't sell it or anything made from it.
"""


def mania_core_readme(core, cross, version, readme):
    heads, credits = readme[0], readme[1]
    core_list = "\n".join(f"- **{c['title']}**" for c in core)
    cross_list = "\n".join(f"- **{c['title']}** ({mania_folder_name(c)})" for c in cross)
    moves = "\n\n".join(f"### {c['title']}\n\n{mania_moves(c, heads)}" for c in core)
    cross_credits = "\n".join(dict.fromkeys(mania_credit(c, credits) for c in cross))
    others = " ".join(MANIA_OWNERS[c["folder"]] for c in cross if c["folder"] in MANIA_OWNERS)
    return f"""# {MANIA_TITLE}

Version {version}. NoSwap adds extra playable characters to **Sonic Mania** (the RSDKv5 decompilation) without replacing
anyone: Sonic, Tails and Knuckles (and Mighty and Ray, with Plus) are all still there, and the extras are picks on
top of them.

This is the **all-in-one** download: the NoSwap Mania mod with all {len(core)} of these characters inside it:

{core_list}

Crossover characters from other games are **separate downloads**, each its own small mod installed next to this one:

{cross_list}

Each one has their own sprites, save select picture, HUD life icon, signpost, act clear name and Super form, and most
have their own moves.

{MANIA_INSTALL}
## Moves

The moves are NoSwap's, written for Sonic Origins; in Mania they play as in Sonic 3 & Knuckles. Where a line names
Sonic 1, Sonic 2 or Sonic CD, it doesn't apply here.

{moves}

{MANIA_LIMITS}
{MANIA_AI}
## Credits

**Character sprites** (each sheet's own terms are quoted as written; the sheets themselves are not included, only the
frames cut from them, exactly as drawn)

{chr(10).join(dict.fromkeys(mania_credit(c, credits) for c in core))}

Separate downloads (their save select pictures are in this mod's picture atlas, shown only when they're installed):

{cross_credits}

{MANIA_FOUNDATIONS}
{MANIA_LEGAL.format(others=others)}
Mod by **Superevil**.
""".replace("\n\n\n", "\n\n")


def mania_cross_readme(c, version, readme):
    heads, credits = readme[0], readme[1]
    owner = MANIA_OWNERS.get(c["folder"], f"{c['title']} © SEGA.")
    return f"""# NoSwap (Sonic Mania): {c['title']}

{c['title']} as an extra playable character in **Sonic Mania** (the RSDKv5 decompilation), for **NoSwap**. A separate
download: nobody is replaced, and it isn't part of the NoSwap Mania all-in-one.

**This needs the NoSwapMania mod**, installed, enabled and the **same version** as this one ({version}).

## Installing

Copy the `{mania_folder_name(c)}` folder into the decompilation's `mods` folder, next to `NoSwapMania`, and enable it in
the **Mods** menu (or in `mods/modconfig.ini`: `{mania_folder_name(c)}=y`). Restart the game. {c['title']} then shows in
Mania Mode's save select (up/down on No Save or a new slot), after the all-in-one's characters. See NoSwapMania's
README for the rest.

## Moves

The moves are NoSwap's, written for Sonic Origins; in Mania they play as in Sonic 3 & Knuckles (a line naming another
game doesn't apply here).

{mania_moves(c, heads)}

## Sprite credits

{mania_credit(c, credits)}

{MANIA_AI.replace("## How it was made", "## How it was made").replace("(Amy uses SEGA's own sprites), ", "")}
## The games and characters

{owner} Sonic the Hedgehog and Sonic Mania © SEGA. The Sonic Mania decompilation is by Rubberduckycooly and chuliRMG
(original RSDK by Evening Star); it isn't included (see NoSwapMania's README and LICENSES). This is a free, unofficial,
non-commercial fan mod, not affiliated with or endorsed by any rights holder named here.
""".replace("\n\n\n", "\n\n")


def mania_core_ini(core, version):
    names = ", ".join(c["title"] for c in core)
    return f"""Name={MANIA_TITLE}
Description=Adds {len(core)} extra playable characters to Mania Mode without replacing anyone (all-in-one): {names}. Pick them in the save select (up/down on No Save or a new slot). Crossover characters are separate downloads. Options in modSettings.ini.
Author={AUTHOR}
Version={version}
TargetVersion=5
LogicFile=NoSwapMania
"""


def mania_cross_ini(c, version):
    return f"""Name=NoSwap (Mania): {c['title']}
Description={c['title']} for NoSwap in Sonic Mania. Needs the NoSwapMania mod enabled, the same version ({version}). A data-only mod: NoSwapMania reads its Data/Sprites/NoSwap/{c['folder']} package.
Author={AUTHOR}
Version={version}
TargetVersion=5
"""


MANIA_PACK = "NoSwapMania-Extras"  # (the Mania extras pack's mod folder)


def mania_pack_ini(cross, version):
    return f"""Name=NoSwap (Mania): Extras Pack
Description=The {len(cross)} crossover characters for NoSwap in Sonic Mania, in one mod: {', '.join(c['title'] for c in cross)}. Needs the NoSwapMania mod enabled, the same version ({version}). Data only: NoSwapMania reads its Data/Sprites/NoSwap packages.
Author={AUTHOR}
Version={version}
TargetVersion=5
"""


def mania_pack_readme(cross, version, readme):
    heads, credits = readme[0], readme[1]
    lst = "\n".join(f"- **{c['title']}**" for c in cross)
    moves = "\n\n".join(f"### {c['title']}\n\n{mania_moves(c, heads)}" for c in cross)
    creds = "\n".join(dict.fromkeys(mania_credit(c, credits) for c in cross))
    owners = " ".join(dict.fromkeys(MANIA_OWNERS.get(c["folder"], f"{c['title']} © SEGA.") for c in cross))
    return f"""# NoSwap (Sonic Mania): Extras Pack

The {len(cross)} crossover characters for **NoSwap** in **Sonic Mania** (the RSDKv5 decompilation), in one mod. Nobody
is replaced, and they aren't part of the NoSwap Mania all-in-one:

{lst}

**This needs the NoSwapMania mod**, installed, enabled and the **same version** as this one ({version}).

## Installing

Copy the `{MANIA_PACK}` folder into the decompilation's `mods` folder, next to `NoSwapMania`, and enable it in the
**Mods** menu (or in `mods/modconfig.ini`: `{MANIA_PACK}=y`). Restart the game. The characters then show in Mania
Mode's save select (up/down on No Save or a new slot), after the all-in-one's characters. See NoSwapMania's README for
the rest.

Each of these characters is also a download of its own ("NoSwapMania-MegaMan" and so on): use either this pack or
those, not both.

## Moves

The moves are NoSwap's, written for Sonic Origins; in Mania they play as in Sonic 3 & Knuckles (a line naming another
game doesn't apply here).

{moves}

## Sprite credits

(each sheet's own terms are quoted as written; the sheets themselves are not included, only the frames cut from them,
exactly as drawn)

{creds}

{MANIA_AI.replace("(Amy uses SEGA's own sprites), ", "")}
## The games and characters

{owners} Sonic the Hedgehog and Sonic Mania © SEGA. The Sonic Mania decompilation is by Rubberduckycooly and chuliRMG
(original RSDK by Evening Star); it isn't included (see NoSwapMania's README and LICENSES). This is a free, unofficial,
non-commercial fan mod, not affiliated with or endorsed by any rights holder named here.
""".replace("\n\n\n", "\n\n")


MANIA_SETTINGS = """; NoSwap (Sonic Mania): who plays.
;   menu   Mania Mode's save select: up/down on No Save or a new slot cycles the characters (the default)
;   <name> a character's package folder (e.g. bark, amy): every Sonic is that character, everywhere (a test switch)
;   none   the game as it is
Character = menu
"""


def build_mania_atlas(folders, dest):
    """The save select atlas (build_mania_art.build_save_atlas, as built) for exactly `folders`, written into dest:
    built from the packages in mods/NoSwapMania into a temporary folder, so the mod tree isn't touched."""
    import tempfile
    import build_mania_art as bm
    with tempfile.TemporaryDirectory(prefix="noswap-mania-atlas-") as tmp:
        tmp = Path(tmp)
        for f in folders:
            (tmp / f).symlink_to(MANIA_PACKAGES / f, target_is_directory=True)
        saved = bm.PACKAGES, bm.MANIA_ALL
        bm.PACKAGES, bm.MANIA_ALL = tmp, list(folders)
        try:
            bm.build_save_atlas()
        finally:
            bm.PACKAGES, bm.MANIA_ALL = saved
        dest.mkdir(parents=True, exist_ok=True)
        for name in MANIA_ATLAS_FILES:
            shutil.copy2(tmp / name, dest / name)


def mania_leak_check(core_dir, cross_dirs, core, cross, private, pack_dir=None):
    """The leak check for the Mania outputs (as leak_check does for Origins'): no private character's key, name, folder
    name, Origins file name or art bytes anywhere; exactly the expected mods and packages."""
    problems = []
    keys = [e["key"] for e in private]
    folders = [e["art"].name for e in private]
    name_pats = private_name_patterns(private)
    file_pats = [re.compile(rf"Extra{e['n']}(?!\d)|_x{e['n']}(?!\d)", re.I) for e in private]
    # private art: every file of a private package (Mania's and Origins') whose bytes no public package or core file shares
    shared = set()
    for p in MANIA_MOD.rglob("*"):
        if p.is_file() and MANIA_PKG_REL.as_posix() not in p.relative_to(MANIA_MOD).as_posix():
            shared.add(sha(p))
    for c in core + cross:
        shared |= {sha(p) for p in (MANIA_PACKAGES / c["folder"]).rglob("*") if p.is_file()}
    private_art = {}
    for f in folders:
        for root in (MANIA_PACKAGES / f, MOD / "characters" / f):
            for p in root.rglob("*") if root.exists() else []:
                if p.is_file() and sha(p) not in shared:
                    private_art[sha(p)] = p.relative_to(REPO).as_posix()
    # the mods and their packages
    want = {"NoSwapMania"} | {mania_folder_name(c) for c in cross} | ({MANIA_PACK} if cross else set())
    have = {d.name for d in [core_dir] + cross_dirs + ([pack_dir] if pack_dir else [])}
    if have != want:
        problems.append(f"mod folders: unexpected {sorted(have - want)}, missing {sorted(want - have)}")
    inside = {p.parent.name for p in (core_dir / MANIA_PKG_REL).glob("*/noswap_character.json")}
    if inside != {c["folder"] for c in core}:
        problems.append(f"NoSwapMania packages: unexpected {sorted(inside - {c['folder'] for c in core})}, "
                        f"missing {sorted({c['folder'] for c in core} - inside)}")
    for d, c in zip(cross_dirs, cross):
        got = {p.parent.name for p in d.rglob("noswap_character.json")}
        if got != {c["folder"]} or not (d / MANIA_PKG_REL / c["folder"] / "noswap_character.json").exists():
            problems.append(f"{d.name}: packages {sorted(got)}, expected only Data/Sprites/NoSwap/{c['folder']}")
        if any(d.glob("*.dll")) or any(d.glob("*.so")):
            problems.append(f"{d.name}: has a code mod (only the core has one)")
    if pack_dir:  # the extras pack: exactly the crossovers' packages, no code
        got = {p.parent.name for p in pack_dir.rglob("noswap_character.json")}
        if got != {c["folder"] for c in cross} or {p.parent.name for p in (pack_dir / MANIA_PKG_REL).glob(
                "*/noswap_character.json")} != got:
            problems.append(f"{pack_dir.name}: packages {sorted(got)}, expected Data/Sprites/NoSwap/ of "
                            f"{sorted(c['folder'] for c in cross)}")
        if any(pack_dir.glob("*.dll")) or any(pack_dir.glob("*.so")):
            problems.append(f"{pack_dir.name}: has a code mod (only the core has one)")
    public_keys = {c["key"] for c in core + cross}
    for d in [core_dir] + cross_dirs + ([pack_dir] if pack_dir else []):
        for pj in d.rglob("noswap_character.json"):
            k = read_json(pj)["key"]
            if k in keys or k not in public_keys:
                problems.append(f"{d.name}/{pj.relative_to(d)}: key {k} isn't a public release character")
    atlas = core_dir / MANIA_PKG_REL / "SaveSelectAtlas.bin"
    if atlas.exists():
        names = set(re.findall(rb"extra:([A-Za-z0-9_.-]+)", atlas.read_bytes()))
        public = {c["folder"].encode() for c in core + cross}
        if names - public or public - names:
            problems.append(f"save select atlas: unexpected {sorted(names - public)}, missing {sorted(public - names)}")
    else:
        problems.append("NoSwapMania: no SaveSelectAtlas.bin")
    files = 0
    for d in [core_dir] + cross_dirs + ([pack_dir] if pack_dir else []):
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            files += 1
            rel = f"{d.name}/{p.relative_to(d).as_posix()}"
            low = [part.lower() for part in p.relative_to(d).parts]
            if any(part in folders for part in low) or any(fp.search(rel) for fp in file_pats):
                problems.append(f"{rel}: a private character's file name")
            data = p.read_bytes()
            for k in keys:
                if k.encode() in data or k.encode("utf-16-le") in data:
                    problems.append(f"{rel}: contains the key {k}")
            for f in folders:
                if f.encode() in data:
                    problems.append(f"{rel}: contains the private folder name {f}")
            for pat in name_pats:
                m = pat.search(data)
                if m:
                    problems.append(f"{rel}: names a private character at byte {m.start()}: "
                                    f"{data[max(0, m.start() - 30):m.end() + 30]!r}")
            if sha(p) in private_art:
                problems.append(f"{rel}: byte-identical to private art {private_art[sha(p)]}")
    return problems, files, len(private_art)


def zip_dir(d, z):
    """d as <z>, holding its folder (zip_mod's layout, any output folder)."""
    z.parent.mkdir(parents=True, exist_ok=True)
    names = []
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(d.rglob("*")):
            if p.is_file():
                arc = f"{d.name}/{p.relative_to(d).as_posix()}"
                zf.write(p, arc)
                names.append(arc)
    with zipfile.ZipFile(z) as zf:
        if sorted(zf.namelist()) != sorted(names) or zf.testzip() is not None:
            fail(f"{z.name} doesn't read back")
    return z


def pack_mania(version=None, out=None, zip_it=True, contest=False, list_only=False):
    """Pack the Mania release (see the section comment above) into `out` (default dist/mania). list_only: print the
    roster and the planned mods, write nothing. -> the output folder."""
    out = Path(out) if out else DIST / "mania"
    version = version or mania_version()
    if contest:  # (the SHC intro file is Origins-only: --contest only tags the version here)
        version += "-contest"
    private = private_extras()
    core, cross, left_out = mania_roster()
    import build_mania_art as bm
    missing = [f for f in bm.MANIA_ALL if f not in mania_folders()
               and f not in {e["art"].name for e in private}]
    if missing:
        fail(f"Mania packages not built: {missing} (run tools/build_mania_art.py first)")
    print(f"NoSwap Mania {version}: core (all-in-one) {len(core)}: {', '.join(c['folder'] for c in core)}")
    print(f"  separate downloads {len(cross)}: {', '.join(mania_folder_name(c) for c in cross)}")
    if cross:
        print(f"  extras pack: {MANIA_PACK} ({len(cross)} characters)")
    print(f"  left out: {', '.join(f'{f} ({why})' for f, why in left_out) or 'none'}")
    if list_only:
        return out
    for name in ["mod.ini"] + MANIA_CORE_FILES:
        if not (MANIA_MOD / name).is_file():
            fail(f"mods/NoSwapMania/{name} is missing: run the build first")
    for name, src in MANIA_LICENSES.items():
        if not src.is_file():
            fail(f"{src} is missing (the decompilation's license, shipped as LICENSES/{name})")
    readme_text = (MOD / "README.md").read_text()
    readme = readme_sections(readme_text)

    if out.resolve() == REPO.resolve() or MOD.resolve() in out.resolve().parents or MANIA_MOD.resolve() in out.resolve().parents:
        fail(f"--out {out}: not inside the repo's mods")
    if out.exists():
        for old in list(out.glob("NoSwapMania*")) + [out / "zips"]:
            if old.is_dir():
                shutil.rmtree(old)
    out.mkdir(parents=True, exist_ok=True)

    # the core, with the core roster inside it
    core_dir = out / "NoSwapMania"
    for name in MANIA_CORE_FILES:
        (core_dir / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MANIA_MOD / name, core_dir / name)
    import own_sounds  # (packages' own sounds, Data/SoundFX/NoSwap/<folder>/: each in its own mod, with its Game.xml lines)
    own_root = MANIA_MOD / "Data" / "SoundFX" / own_sounds.SFX_DIR
    core_folders = {c["folder"] for c in core}
    for p in sorted((MANIA_MOD / "Data" / "SoundFX").rglob("*.wav")):
        if own_root in p.parents and p.parent.name not in core_folders:
            continue  # (a crossover's own sounds go in its mod; a private one's nowhere)
        (core_dir / p.relative_to(MANIA_MOD)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, core_dir / p.relative_to(MANIA_MOD))
    own_sounds.write_game_xml(core_dir / "Data" / "Game" / "Game.xml", own_sounds.game_xml_lines(MANIA_MOD, core_folders))
    for c in core:
        shutil.copytree(MANIA_PACKAGES / c["folder"], core_dir / MANIA_PKG_REL / c["folder"])
    build_mania_atlas([c["folder"] for c in core + cross], core_dir / MANIA_PKG_REL)
    (core_dir / "mod.ini").write_text(mania_core_ini(core, version))
    (core_dir / "modSettings.ini").write_text(MANIA_SETTINGS)
    (core_dir / "README.md").write_text(mania_core_readme(core, cross, version, readme))
    (core_dir / "LICENSES").mkdir()
    for name, src in MANIA_LICENSES.items():
        shutil.copy2(src, core_dir / "LICENSES" / name)

    # the crossovers, one mod each
    cross_dirs = []
    for c in cross:
        d = out / mania_folder_name(c)
        shutil.copytree(MANIA_PACKAGES / c["folder"], d / MANIA_PKG_REL / c["folder"])
        if (own_root / c["folder"]).is_dir():  # its own sounds, and its own Game.xml loading them (the decomp's loader
            # reads every active mod's Data/Game/Game.xml and finds the files in that mod)
            shutil.copytree(own_root / c["folder"], d / "Data" / "SoundFX" / own_sounds.SFX_DIR / c["folder"])
            lines = own_sounds.game_xml_lines(MANIA_MOD, {c["folder"]})
            if lines:
                own_sounds.write_game_xml(d / "Data" / "Game" / "Game.xml", lines)
        (d / "mod.ini").write_text(mania_cross_ini(c, version))
        (d / "README.md").write_text(mania_cross_readme(c, version, readme))
        cross_dirs.append(d)

    # the extras pack: every crossover in one mod (the one-character mods merged; one Game.xml for all their sounds)
    pack_dir = None
    if cross:
        pack_dir = out / MANIA_PACK
        cross_folders = {c["folder"] for c in cross}
        for c in cross:
            shutil.copytree(MANIA_PACKAGES / c["folder"], pack_dir / MANIA_PKG_REL / c["folder"])
            if (own_root / c["folder"]).is_dir():
                shutil.copytree(own_root / c["folder"], pack_dir / "Data" / "SoundFX" / own_sounds.SFX_DIR / c["folder"])
        lines = own_sounds.game_xml_lines(MANIA_MOD, cross_folders)
        if lines:
            own_sounds.write_game_xml(pack_dir / "Data" / "Game" / "Game.xml", lines)
        (pack_dir / "mod.ini").write_text(mania_pack_ini(cross, version))
        (pack_dir / "README.md").write_text(mania_pack_readme(cross, version, readme))

    problems, files, private_art = mania_leak_check(core_dir, cross_dirs, core, cross, private, pack_dir)
    print(f"Mania leak check: {1 + len(cross_dirs) + bool(pack_dir)} mods, {files} files, private characters "
          f"{', '.join(e['key'] for e in private) or 'none'} ({private_art} files of private art hashed): "
          f"{'FAILED' if problems else 'clean'}")
    if problems:
        for pr in problems[:50]:
            print("  " + pr)
        fail(f"{len(problems)} leak(s): nothing zipped")

    total = 0
    for d in [core_dir] + cross_dirs + ([pack_dir] if pack_dir else []):
        z = zip_dir(d, out / "zips" / f"{d.name}-{version}.zip") if zip_it else None
        total += z.stat().st_size if z else 0
        print(f"{d.name}/: {human(size_of(d))}, {sum(1 for p in d.rglob('*') if p.is_file())} files"
              + (f"; zips/{z.name}: {human(z.stat().st_size)}" if z else ""))
    if zip_it:
        print(f"zips: {1 + len(cross_dirs) + bool(pack_dir)}, {human(total)} in all, in {out / 'zips'}")
    return out


def main():
    global DIST  # (--out moves it)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", help="release version for every mod.ini (default: mods/NoSwap/mod.ini's)")
    ap.add_argument("--no-zip", action="store_true", help="skip the zips")
    ap.add_argument("--contest", action="store_true",
                    help="the Sonic Hacking Contest edition: the core also ships the contest's intro, raw/ui/"
                         "ui_advertise.pac from 'Contest Intro/' (git-ignored), and every version gets '-contest'")
    ap.add_argument("--all-in-one", action="store_true",
                    help="also pack one mod with the core and every public character in it (dist/all-in-one/NoSwap)")
    ap.add_argument("--mania", action="store_true",
                    help="pack the Sonic Mania release instead (pack_mania: NoSwapMania with the core roster inside, "
                         "each crossover its own mod; version default mods/NoSwapMania/mod.ini's); nothing of Origins'")
    ap.add_argument("--out", help="the output folder (default dist/, --mania dist/mania); use a scratch folder for "
                                   "test runs")
    ap.add_argument("--list", action="store_true", help="--mania: print the roster and the planned mods, write nothing")
    args = ap.parse_args()
    if args.mania:
        pack_mania(args.version, args.out, zip_it=not args.no_zip, contest=args.contest, list_only=args.list)
        return
    if args.list:  # (only --mania has a listing; never fall through to a real Origins release into dist/)
        fail("--list works with --mania only; the Origins release has no dry run (it writes dist/)")
    if args.out:  # (a test run: everything in <out> in place of dist/)
        out = Path(args.out).resolve()
        if out == REPO.resolve() or MOD.resolve() == out or MOD.resolve() in out.parents or out in MOD.resolve().parents:
            fail(f"--out {out}: not the repo, the mod or a folder holding it")
        DIST = out
    version = args.version or read_version()
    if args.contest:
        if not CONTEST_INTRO.exists():
            fail(f"--contest: {CONTEST_INTRO} is missing")
        version += "-contest"

    private = private_extras()
    public = [e for e in EXTRAS if not e["private"]]
    for e in private:
        if e["art"].name in CHARACTERS:
            fail(f"{e['art'].name} is private but listed in CHARACTERS")
    missing = [e["art"].name for e in public if release_info(e) is None]
    if missing:
        fail(f"public characters with no entry in CHARACTERS (and no character.json): {missing}")
    for e in public:
        if not (MOD / "characters" / e["art"].name / "noswap_character.json").exists():
            fail(f"no built package for {e['art'].name}: run the build first")
    if not (MOD / oc.DESCRIPTOR).exists():
        fail("no menu archives (raw/ui): run the build first")

    # a fresh dist/ (only what this script writes)
    DIST.mkdir(exist_ok=True)
    for old in list(DIST.glob("NoSwap*")) + [DIST / "zips"]:
        if old.is_dir():
            shutil.rmtree(old)
    readme_text = (MOD / "README.md").read_text()
    readme = readme_sections(readme_text)

    # the core
    core = DIST / "NoSwap"
    for p in sorted(MOD.rglob("*")):
        rel = p.relative_to(MOD)
        if rel.parts[0] in CORE_SKIP_DIRS or any(part == "__pycache__" for part in rel.parts):
            continue
        if p.is_file() and p.suffix.lower() not in CORE_SKIP_SUFFIXES:
            (core / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, core / rel)
    if args.contest:  # the contest's instructions: "insert the ui_advertise.pac file into the /raw/ui directory"
        (core / "raw" / "ui").mkdir(parents=True, exist_ok=True)
        shutil.copy2(CONTEST_INTRO, core / "raw" / "ui" / CONTEST_INTRO.name)
    (core / "mod.ini").write_text(core_ini(version))
    title_end = readme_text.index("\n") + 1
    (core / "README.md").write_text(readme_text[:title_end] + "\n" + CORE_NOTE + readme_text[title_end:])
    if INSTALL.exists():
        shutil.copy2(INSTALL, core / "INSTALL.md")
    else:
        print("warning: docs/INSTALL.md is missing: the core ships without it")
    blanked, archives = blank_menu_cards(core)
    dll_notes = patch_dll_keys(core, private)
    reworded = reword_script_comments(core, private)
    print(f"core: menu archives with card slots blanked: {blanked} of {archives} changed; "
          f"DLL keys: {'; '.join(dll_notes) or 'none to patch'}")

    # the characters
    outputs = [core]
    public_folders = []
    for e in public:
        f = e["art"].name
        src = MOD / "characters" / f
        pkg = read_json(src / "noswap_character.json")
        d = DIST / folder_name(pkg["name"])
        shutil.copytree(src, d)
        title = release_info(e)[0]
        (d / "mod.ini").write_text(character_ini(title, version))
        (d / "README.md").write_text(character_readme(f, title, version, readme))
        reworded += reword_script_comments(d, private)
        outputs.append(d)
        public_folders.append(f)

    # the extras pack: every public crossover's package (as built) in characters/<folder>/, one mod
    crossovers = [e for e in public if e["crossover"]]
    if crossovers:
        d = DIST / EXTRAS_PACK
        for e in crossovers:
            dst = d / "characters" / e["art"].name
            shutil.copytree(MOD / "characters" / e["art"].name, dst)
            reworded += reword_script_comments(dst, private)
        entries = [(e["art"].name, release_info(e)[0]) for e in crossovers]
        (d / "mod.ini").write_text(extras_pack_ini([t for _, t in entries], version))
        (d / "README.md").write_text(extras_pack_readme(entries, version, readme))
        outputs.append(d)

    if args.all_in_one:  # the core (already release-changed) plus each public package, as built, in characters/
        aio = DIST / "all-in-one" / "NoSwap"
        if aio.parent.exists():
            shutil.rmtree(aio.parent)
        shutil.copytree(core, aio)
        for e in public:
            if not in_all_in_one(e):  # (crossover and newer characters: their own download only; memory crossover-characters.md)
                continue
            dst = aio / "characters" / e["art"].name
            shutil.copytree(MOD / "characters" / e["art"].name, dst)
            reworded += reword_script_comments(dst, private)
        (aio / "mod.ini").write_text(aio_ini(version))
        (aio / "README.md").write_text(readme_text[:title_end] + "\n" + AIO_NOTE + readme_text[title_end:])
        outputs.append(aio)

    print(f"script comment lines naming a private character, reworded (core and packages): {reworded}")
    problems, files, private_art = leak_check(outputs, private, public_folders)
    print(f"leak check: {len(outputs)} mods, {files} files, private characters "
          f"{', '.join(e['key'] for e in private) or 'none'} ({private_art} files of private art hashed): "
          f"{'FAILED' if problems else 'clean'}")
    if problems:
        for pr in problems[:50]:
            print("  " + pr)
        fail(f"{len(problems)} leak(s): nothing zipped")

    total = 0
    for d in outputs:
        z = None if args.no_zip else zip_mod(d, version)
        total += z.stat().st_size if z else 0
        print(f"{d.relative_to(REPO)}/: {human(size_of(d))}, {sum(1 for p in d.rglob('*') if p.is_file())} files"
              + (f"; {z.relative_to(REPO)}: {human(z.stat().st_size)}" if z else ""))
    if not args.no_zip:
        print(f"zips: {len(outputs)}, {human(total)} in all")


if __name__ == "__main__":
    main()
