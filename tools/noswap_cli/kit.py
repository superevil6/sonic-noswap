"""The NoSwap Creator Kit (tools/make_kit.py packs it): the editor and the build, without the repo.

The kit is the editor's program plus a copy of NoSwap's own tools (tools/, the schema, the ability list, the
registry, Rayan C.'s HUD font). Nothing in it is SEGA's: every game file the build reads is taken from the player's own
games at "Set up" (setup()), into the kit's data folder, which is laid out like the repo so the same tools run there:

    <data>/                       data_root(): $NOSWAP_KIT_DATA, else Documents/NoSwap Creator Kit (Windows),
                                  ~/Documents/NoSwap Creator Kit or ~/NoSwap Creator Kit (Linux)
        characters/               the creator's characters (one folder each, with its character.json)
        output/<id>/              what a build makes to install: origins/NoSwap-<Name>/, mania/NoSwap-<Name>/, zips
        tools/ docs/ data/ ...    the kit's copy of NoSwap's tools (sync_app(): refreshed when the kit changes)
        extracted/                from the player's games (setup()): Sonic1, Sonic2, SonicCD, Sonic3K (Origins' data
                                  packs), OriginsScripts/<game>u/Scripts (HedgeModManager's decompiled scripts in the
                                  Origins folder), Mania/Data (Sonic Mania's Data.rsdk)
        testmods/_shared/         mania_ball.png, cut from the player's Mania data (the generic spin ball)
        mods/                     the build's working tree (internal: never installed as it is)

Core coupling: a package's S1/S2/CD player scripts are generated from NoSwap's scripts of the kit's version, so the
kit's version IS the core's: packages it builds need the released NoSwap core (Origins) / NoSwap Mania mod of that same
version (data/kit/core.json, written by make_kit.py from the build it was packed from). Each build is checked against
that core's manifest (verify_package): every file the package ships has a file of the same name in the core (the DLL
serves only those) and its player scripts declare every name the core's shared scripts use of them.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ENV = "NOSWAP_KIT"
ORIGINS_PACKS = {"Sonic1": "Sonic1u", "Sonic2": "Sonic2u", "SonicCD": "SonicCDu", "Sonic3K": "Sonic3ku"}
SCRIPT_GAMES = ("Sonic1u", "Sonic2u", "SonicCDu")
EXEC = Path("build") / "main" / "projects" / "exec"
RETRO = Path("image") / "x64" / "raw" / "retro"
# What the kit copies from its bundle into the data folder (relative paths; folders whole)
APP_ITEMS = ["tools", "docs/character.schema.json", "docs/abilities.json", "docs/abilities.md",
             "docs/character-json.md", "docs/toolset-ui.md", "docs/roster.md",
             "data/kit", "testmods/_fonts/Sonic1_Fonts_RayanC.png", "testmods/_fonts/SOURCE.txt"]
APP_SKIP = {"__pycache__", "make_release.py", "make_kit.py", "deploy.sh", "deploy_mania.sh", "build_all.sh",
            "gen_mania_psycho.py", "origins_sfx.py", "build_lockon_menu.py"}
# The generic spin ball's two frames in Sonic Mania's Data/Sprites/Players/Sonic1.gif (testmods/_shared/SOURCE.txt)
BALL_RECTS = ((153, 81, 32, 32), (186, 81, 32, 32))


def active():
    return bool(os.environ.get(ENV))


def frozen():
    return bool(getattr(sys, "frozen", False))


def default_root():
    home = Path.home()
    if sys.platform == "win32":
        docs = _windows_documents() or home / "Documents"
        return docs / "NoSwap Creator Kit"
    docs = home / "Documents"
    return (docs if docs.is_dir() else home) / "NoSwap Creator Kit"


def _windows_documents():
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:  # CSIDL_PERSONAL
            return Path(buf.value)
    except Exception:
        pass
    return None


def data_root():
    return Path(os.environ.get("NOSWAP_KIT_DATA") or default_root())


def layout(root=None):
    root = Path(root or data_root())
    ex = root / "extracted"
    return {"root": root, "characters": root / "characters", "output": root / "output", "tools": root / "tools",
            "extracted": ex, "scripts": ex / "OriginsScripts", "mania": ex / "Mania" / "Data",
            "ball": root / "testmods" / "_shared" / "mania_ball.png", "state": root / "kit-setup.json",
            "core": root / "data" / "kit" / "core.json", "registry": root / "data" / "registry.json"}


def env(root=None):
    """The environment the kit's tools run in (every subprocess inherits it)."""
    p = layout(root)
    return {ENV: "1", "NOSWAP_KIT_DATA": str(p["root"]), "NOSWAP_TESTMODS": str(p["characters"]),
            "ORIGINS_EXEC": str(p["scripts"]), "NOSWAP_MANIA_DATA": str(p["mania"]),
            "NOSWAP_BUILD_LOCK": str(p["root"] / "build.lock")}


# ------------------------------------------------------------------ the kit's copy of the tools

def _stamp(src):
    h = hashlib.sha1()
    for item in APP_ITEMS:
        base = src / item
        files = [base] if base.is_file() else sorted(f for f in base.rglob("*") if f.is_file()) if base.is_dir() else []
        for f in files:
            if APP_SKIP & set(f.relative_to(src).parts):
                continue
            h.update(f.relative_to(src).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def sync_app(src, root=None):
    """Copy the kit's tools from its bundle (src: a folder laid out like the repo) into the data folder, when they
    differ from what's there. The creator's own files (characters/, output/, extracted/, the registry) are never
    touched. -> True if it copied."""
    p = layout(root)
    src = Path(src)
    stamp = _stamp(src)
    mark = p["root"] / "tools" / ".kit-stamp"
    if mark.is_file() and mark.read_text().strip() == stamp:
        return False
    if (p["root"] / "tools").is_dir():
        shutil.rmtree(p["root"] / "tools")
    for item in APP_ITEMS:
        s, d = src / item, p["root"] / item
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*APP_SKIP))
        elif s.is_file():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
    if not p["registry"].exists():  # (the creator's registry: their keys' numbers, kept for good)
        shutil.copy2(src / "data" / "kit" / "registry.json", p["registry"])
    for k in ("characters", "output"):
        p[k].mkdir(parents=True, exist_ok=True)
    mark.write_text(stamp + "\n")
    return True


# ------------------------------------------------------------------ set up: the player's own game files

def find_origins():
    """Origins' game folder from Steam (None: not found)."""
    from .deploy import steam_app_folder, ORIGINS_APP
    f = steam_app_folder(ORIGINS_APP, "SonicOrigins")
    return f if f and (f / RETRO).is_dir() else None


def find_mania():
    """A folder with Sonic Mania's Data.rsdk: the configured Mania run folder, Steam's Sonic Mania (None: not found)."""
    from .deploy import steam_app_folder, MANIA_APP, load_settings, KEYS
    for f in (load_settings().get(KEYS["mania"]), steam_app_folder(MANIA_APP, "Sonic Mania")):
        if f and (Path(f) / "Data.rsdk").is_file():
            return Path(f)
    return None


def origins_root(path):
    """The Origins game folder from what the user picked: the game folder, its exec folder or its mods folder."""
    p = Path(path).expanduser()
    for c in (p, *p.parents):
        if (c / RETRO / "Sonic1u.rsdk").is_file():
            return c
    return None


def check_origins_game(path):
    root = origins_root(path) if path else None
    problems, notes = [], []
    if not root:
        problems.append("not Sonic Origins' folder: no image/x64/raw/retro/Sonic1u.rsdk in it or above it")
        return {"ok": False, "root": None, "problems": problems, "notes": notes}
    notes.append(f"Sonic Origins: {root}")
    missing = [g for g in SCRIPT_GAMES if not (root / EXEC / g / "Scripts").is_dir()]
    if missing:
        problems.append("no decompiled scripts in " + str(root / EXEC) + f" ({', '.join(missing)}/Scripts): install "
                        "HedgeModManager for Sonic Origins and the NoSwap mod, enable NoSwap and start the game once "
                        "(the loader puts the community's decompiled scripts there)")
    else:
        notes.append("HedgeModManager's decompiled scripts are there")
    return {"ok": not problems, "root": str(root), "problems": problems, "notes": notes}


def mania_rsdk(path):
    p = Path(path).expanduser()
    for c in (p / "Data.rsdk", p):
        if c.is_file() and c.name.lower().endswith(".rsdk"):
            return c
    return None


def check_mania_game(path):
    if not path:
        return {"ok": False, "rsdk": None, "problems": ["not set (Mania is optional)"], "notes": []}
    r = mania_rsdk(path)
    if not r:
        return {"ok": False, "rsdk": None, "notes": [],
                "problems": ["no Data.rsdk here: pick Sonic Mania's folder (Steam's, or your decompilation's play "
                             "folder with Data.rsdk in it)"]}
    return {"ok": True, "rsdk": str(r), "problems": [], "notes": [f"Sonic Mania data: {r}"]}


def _names(item):
    return [n for n in (Path(__file__).resolve().parent.parent.parent / "data" / "kit" / f"names-{item}.txt")
            .read_text().splitlines() if n.strip()]


def _extract(pack, names, out, log):
    """rsdk5_extract.py's reader, by name: -> how many of `names` were found."""
    import rsdk5_extract as rx
    data = Path(pack).read_bytes()
    index = rx.read_index(data)
    found = 0
    for name in names:
        d = hashlib.md5(name.lower().encode()).digest()
        entry = index.get(d) or index.get(rx.swapped(d))
        if not entry:
            continue
        offset, size, enc = entry
        blob = data[offset:offset + size]
        if enc:
            blob = rx.decrypt(blob, name, size)
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        found += 1
    return found


def setup(origins=None, mania=None, root=None, log=print):
    """Take what the build needs from the player's own games into the data folder. origins: the Origins folder (or its
    exec/mods folder); mania: a folder with Sonic Mania's Data.rsdk (optional). Reads the games only. -> state dict."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    p = layout(root)
    state = load_state(root)
    if origins:
        c = check_origins_game(origins)
        if not c["ok"]:
            raise SetupError("Origins: " + "; ".join(c["problems"]))
        groot = Path(c["root"])
        for folder, pack in ORIGINS_PACKS.items():
            names = _names(folder)
            out = p["extracted"] / folder
            if out.exists():
                shutil.rmtree(out)
            log(f"Origins: extracting {pack}.rsdk ({len(names)} files) ...")
            n = _extract(groot / RETRO / f"{pack}.rsdk", names, out, log)
            if n < len(names):
                raise SetupError(f"Origins: only {n} of {len(names)} files found in {pack}.rsdk (a different game "
                                 "version? The kit was made for Origins as of 2026)")
        for g in SCRIPT_GAMES:
            out = p["scripts"] / g / "Scripts"
            if out.exists():
                shutil.rmtree(out)
            shutil.copytree(groot / EXEC / g / "Scripts", out)
            log(f"Origins: copied the decompiled {g} scripts ({sum(1 for _ in out.rglob('*.txt'))} files)")
        state["origins"] = str(groot)
        save_state(state, root)  # (kept even if Mania's part fails)
    if mania:
        c = check_mania_game(mania)
        if not c["ok"]:
            raise SetupError("Mania: " + "; ".join(c["problems"]))
        names = _names("Mania")
        out = p["mania"].parent
        if out.exists():
            shutil.rmtree(out)
        log(f"Mania: extracting Data.rsdk ({len(names)} files) ...")
        n = _extract(c["rsdk"], names, out, log)
        if n < len(names):
            raise SetupError(f"Mania: only {n} of {len(names)} files found in {c['rsdk']} (Sonic Mania Plus 1.06 "
                             "data is expected)")
        cut_ball(p["mania"] / "Sprites" / "Players" / "Sonic1.gif", p["ball"])
        log("Mania: cut the generic spin ball from Sonic Mania's own Sonic1.gif")
        state["mania"] = str(Path(c["rsdk"]).parent)
    save_state(state, root)
    log("set up: " + ", ".join(k for k in ("origins", "mania") if state.get(k)))
    return status(root)


def cut_ball(sheet, out):
    from PIL import Image
    src = Image.open(sheet)
    img = Image.new("P", (64, 32), 0)
    img.putpalette(src.getpalette())
    for k, (x, y, w, h) in enumerate(BALL_RECTS):
        img.paste(src.crop((x, y, x + w, y + h)), (32 * k, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, transparency=0)


class SetupError(Exception):
    pass


def load_state(root=None):
    try:
        return json.loads(layout(root)["state"].read_text())
    except (OSError, ValueError):
        return {}


def save_state(state, root=None):
    f = layout(root)["state"]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=1) + "\n")


def status(root=None):
    """What's set up: {root, origins, mania, ready_origins, ready_mania, core, characters, output, found}."""
    p = layout(root)
    st = load_state(root)
    ready_o = all((p["extracted"] / f / "Data").is_dir() for f in ORIGINS_PACKS) and \
        all((p["scripts"] / g / "Scripts").is_dir() for g in SCRIPT_GAMES)
    ready_m = (p["mania"] / "Sprites" / "Players" / "Sonic.bin").is_file() and p["ball"].is_file()
    try:
        core = json.loads(p["core"].read_text())
    except (OSError, ValueError):
        core = {}
    found_o, found_m = find_origins(), find_mania()
    return {"root": str(p["root"]), "origins": st.get("origins"), "mania": st.get("mania"),
            "ready_origins": ready_o, "ready_mania": ready_m, "core": core,
            "characters": str(p["characters"]), "output": str(p["output"]),
            "found": {"origins": str(found_o) if found_o else None, "mania": str(found_m) if found_m else None}}


# ------------------------------------------------------------------ after a build: the installable mods

def mod_folder_name(name):
    """ "METAL SONIC" -> "NoSwap-MetalSonic" (make_release.folder_name)"""
    return "NoSwap-" + "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", name) if w)


def _core():
    p = layout()
    return json.loads(p["core"].read_text())


def verify_package(pkg, manifest):
    """The package against the released core it's for (data/kit/core.json): every file it ships has a NoSwap file of
    that name (the DLL serves only those), and its player scripts declare what the core's shared scripts use of them.
    -> [problem]"""
    problems = []
    special = set(manifest["package_only"])
    core_files = set(manifest["core_files"])
    for f in sorted(pkg.rglob("*")):
        rel = f.relative_to(pkg).as_posix()
        if f.is_file() and rel not in special and rel.lower() not in core_files:
            problems.append(f"{rel}: the NoSwap core {manifest['version']} has no file of that name (the DLL would never "
                            "serve it)")
    decl = re.compile(r"^(?:public|private) (?:value|alias \S+ :|function|table) ?(\w+)", re.M)
    for game, names in manifest["player_needs"].items():
        f = pkg / game / "Data" / "Scripts" / "Players" / "PlayerObject.txt"
        if not f.is_file():
            problems.append(f"{game}: no player script")
            continue
        text = f.read_text(errors="ignore")
        if game == "SonicCDu":
            have = set(re.findall(r"^function (\w+)", text, re.M))
        else:
            have = set(decl.findall(text)) | set(re.findall(r"^public alias \S+ : (\w+)", text, re.M))
        missing = sorted(set(names) - have)
        if missing:
            problems.append(f"{game}: its player script lacks {missing[:6]}, which the core's shared scripts use")
    return problems


def export(folder, games=("origins", "mania"), log=print):
    """Turn a built character into installable mods under output/<id>/: origins/NoSwap-<Name>/ (its package at the mod
    root, with a mod.ini, as make_release.py packs a character) and mania/NoSwap-<Name>/ (Data/Sprites/NoSwap/<id>/ with
    a mod.ini), each also zipped. Checks the Origins package against the core it's for. -> [problems]"""
    from .model import REPO, load
    ch = load(folder)
    p = layout()
    core = _core()
    doc = json.loads((ch.folder / "character.json").read_text())
    title = doc.get("full_name") or ch.name.title()
    credit = (doc.get("credits") or {})
    out = p["output"] / ch.id
    problems = []
    made = []
    if "origins" in games:
        pkg = REPO / "mods" / "NoSwap" / "characters" / ch.id
        if not (pkg / "noswap_character.json").is_file():
            return [f"Origins: {ch.id} isn't built"]
        problems += verify_package(pkg, core["origins"])
        if problems:
            return problems
        pj = json.loads((pkg / "noswap_character.json").read_text())
        d = out / "origins" / mod_folder_name(pj["name"])
        if d.parent.exists():
            shutil.rmtree(d.parent)
        shutil.copytree(pkg, d)
        (d / "mod.ini").write_text(origins_ini(title, core["origins"]["version"], doc))
        (d / "README.md").write_text(readme(title, doc, core, "origins"))
        made.append(_zip(d, out / f"{d.name}-Origins-{core['origins']['version']}.zip"))
    if "mania" in games:
        pkg = REPO / "mods" / "NoSwapMania" / "Data" / "Sprites" / "NoSwap" / ch.id
        if not (pkg / "noswap_character.json").is_file():
            problems.append(f"Mania: {ch.id} isn't built for Mania")
        else:
            pj = json.loads((pkg / "noswap_character.json").read_text())
            d = out / "mania" / mod_folder_name(pj.get("name") or ch.name)
            if d.parent.exists():
                shutil.rmtree(d.parent)
            shutil.copytree(pkg, d / "Data" / "Sprites" / "NoSwap" / ch.id)
            (d / "mod.ini").write_text(mania_ini(title, core["mania"]["version"], doc))
            (d / "README.md").write_text(readme(title, doc, core, "mania"))
            made.append(_zip(d, out / f"{d.name}-Mania-{core['mania']['version']}.zip"))
    for z in made:
        log(f"made {z}")
    return problems


def _credit_line(doc):
    c = doc.get("credits") or {}
    who = c.get("artists") or c.get("full") or ""
    if isinstance(who, list):
        who = ", ".join(who)
    return who


def origins_ini(title, version, doc):
    author = (doc.get("key") or "").split(".")[0] or "unknown"
    return f"""[Desc]
Title="NoSwap: {title}"
Description="{title} for NoSwap. Requires the NoSwap mod (the core), installed, enabled and version {version}."
Version="{version}"
Author="{author}"

[Main]
; A NoSwap character package, made with the NoSwap Creator Kit. The NoSwap DLL (in the NoSwap core mod) finds this
; folder in the mod loader's list of enabled mods (it has a noswap_character.json at its root) and reads its files
; itself. It must NOT be an include dir. HiteModLoader parses counts as plain integers.
IncludeDirCount=0
DependsCount=0
SaveFile=""
"""


def mania_ini(title, version, doc):
    author = (doc.get("key") or "").split(".")[0] or "unknown"
    return (f"Name=NoSwap: {title}\nDescription={title} for NoSwap Mania. Requires the NoSwap Mania mod "
            f"(version {version}), enabled.\nAuthor={author}\nVersion={version}\nTargetVersion=5\n")


def readme(title, doc, core, game):
    c = doc.get("credits") or {}
    full = c.get("full") or _credit_line(doc)
    lines = [f"# NoSwap: {title}", "",
             f"{title} as an extra playable character for NoSwap, made with the NoSwap Creator Kit.", ""]
    if game == "origins":
        lines += [f"**Needs the NoSwap core mod for Sonic Origins, version {core['origins']['version']}**, installed and "
                  "enabled in HedgeModManager. Install this folder as its own mod (copy it into Origins' mods folder, "
                  "or install the zip with HedgeModManager) and enable it.", ""]
    else:
        lines += [f"**Needs the NoSwap Mania mod, version {core['mania']['version']}**, in the Sonic Mania "
                  "decompilation's mods folder, enabled. Copy this folder into the same mods folder and enable it "
                  "(mods/modconfig.ini).", ""]
    lines += ["## Sprite credits", "", full or "(none given)"]
    if c.get("url"):
        lines += ["", f"Sheet: {c['url']}"]
    if c.get("terms"):
        lines += ["", f"Terms: {c['terms']}"]
    lines += ["", "Sonic the Hedgehog and Sonic Origins / Sonic Mania © SEGA. This is an unofficial fan mod, not "
              "affiliated with or endorsed by SEGA.", ""]
    return "\n".join(lines)


def _zip(d, z):
    z.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(d.rglob("*")):
            if f.is_file():
                zf.write(f, f"{d.name}/{f.relative_to(d).as_posix()}")
    return z
