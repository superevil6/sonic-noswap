#!/usr/bin/env python3
"""Pack the NoSwap Creator Kit (preview): the character editor and the build as programs, with no repo, no Python
install and no file of SEGA's (tools/noswap_cli/kit.py says how the kit works).

    make_kit.py stage                  kit/build/app/: the tools the kit copies into its data folder, plus data/kit/
                                       (the game files' names, a registry, the core manifest from mods/)
    make_kit.py exe --linux|--windows  the program (PyInstaller, one folder) into kit/build/exe-<os>/
                                       --linux: with --python PY (a venv with pyinstaller, pillow, numpy)
                                       --windows: under Wine, with --wine-python 'C:\\Python313\\python.exe' and
                                       $WINEPREFIX (pyinstaller, pillow, numpy, pywebview installed in it)
    make_kit.py pack                   kit/NoSwap-CreatorKit-<version>-<os>.zip for each built program, after a leak check
    make_kit.py all --python PY --wine-python EXE    all of it
    --core-version V   pin the kit's packages to core V (Origins and Mania), e.g. make_release's --version; give
                       it to stage and pack alike

It never runs make_release.py nor the build: mods/ must hold a finished build (the core the kit's packages are for).
Output: kit/ (git-ignored).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
OUT = REPO / "kit"
BUILD = OUT / "build"
APP = BUILD / "app"
SRC = REPO / "tools" / "kit"  # the kit's own files: its program's entry, README, licence, credits, example
NAME = "NoSwap-CreatorKit"
EXE = "NoSwapCreator"
# Names the kit must never contain (local-only characters, besides extras.py "private" ones), from the environment:
# NOSWAP_PRIVATE_WORDS="name1 name2"
PRIVATE_WORDS = tuple(os.environ.get("NOSWAP_PRIVATE_WORDS", "").lower().split())


def fail(msg):
    sys.exit(f"make_kit: {msg}")


CORE_VERSION = None  # (--core-version: the release's version, when mods/ holds a dev build's mod.ini)


def versions():
    if CORE_VERSION:
        return {"origins": CORE_VERSION, "mania": CORE_VERSION}

    def ini(p, pat):
        m = re.search(pat, p.read_text(), re.M)
        return m.group(1) if m else "0.0.0"
    return {"origins": ini(REPO / "mods" / "NoSwap" / "mod.ini", r'^Version="?([^"\r\n]*)"?'),
            "mania": ini(REPO / "mods" / "NoSwapMania" / "mod.ini", r'^Version=([^\r\n]*)')}


# ---------------------------------------------------------------- stage

def names(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())


def core_manifest():
    """What a package must fit in the NoSwap core this kit is for (kit.verify_package): the core's file names, the
    package-only names, and the names its player scripts must declare (those the core's shared scripts use)."""
    import origins_cards
    from extras import S3K_MENU_PICTURE
    from build_packages import declared, v3_code, v3_functions
    mod = REPO / "mods" / "NoSwap"
    pkgs = sorted(d for d in (mod / "characters").iterdir() if (d / "noswap_character.json").is_file())
    if not pkgs:
        fail("mods/NoSwap has no built packages: build first")
    core_files = sorted(p.relative_to(mod).as_posix().lower() for p in mod.rglob("*") if p.is_file()
                        and p.relative_to(mod).parts[0] not in ("characters", "cache"))
    needs = {}
    player = "Players/PlayerObject.txt"
    for game in ("Sonic1u", "Sonic2u"):
        scripts = mod / game / "Data" / "Scripts"
        shared = "".join(p.read_text(errors="ignore") for p in scripts.rglob("*.txt")
                         if p.relative_to(scripts).as_posix() not in (player, "Special/PlayerObject.txt"))
        variants = [scripts / player] + [d / game / "Data" / "Scripts" / player for d in pkgs]
        common = set.intersection(*(declared(v.read_text(errors="ignore")) for v in variants))
        used = {n for n in common if n.startswith(("NoSwap", "ANI_NOSWAP")) and re.search(rf"\b{n}\b", shared)}
        called = set(re.findall(r"CallFunction\((NoSwap\w+)\)", shared)) - set(
            re.findall(r"^public function (\w+)", shared, re.M))
        needs[game] = sorted(used | called)
    game = "SonicCDu"
    scripts = mod / game / "Data" / "Scripts"
    variants = [scripts / player] + [d / game / "Data" / "Scripts" / player for d in pkgs]
    common = set.intersection(*(v3_functions(v.read_text(errors="ignore")) for v in variants))
    import generic_extra
    others = [p for p in scripts.rglob("*.txt") if p.relative_to(scripts).as_posix() != player]
    others += list((generic_extra.GAME_EXEC / game / "Scripts").rglob("*.txt"))
    text = "\n".join(v3_code(p.read_text(errors="ignore")) for p in others)
    needs[game] = sorted(f for f in common if re.search(rf"\b{f}\b", text))
    v = versions()
    return {"format": "noswap-kit-core/1",
            "note": "The NoSwap core this kit's packages are built for (tools/make_kit.py, from the build it was packed "
                    "from): packages need the released core / Mania mod of these versions.",
            "origins": {"version": v["origins"], "core_files": core_files,
                        "package_only": ["noswap_character.json", origins_cards.PICTURE, origins_cards.HEAD_PICTURE]
                        + [f"Sonic3ku/Data/Sprites/{r}" for r in S3K_MENU_PICTURE],
                        "player_needs": needs},
            "mania": {"version": v["mania"]}}


def ui_layout():
    """The core's S1/S2/CD UI sheet boxes (noswap_common.UiSheets: the union over NoSwap's characters, which its shared
    scripts draw): the kit lays its characters' art out in these, never in its own."""
    import build_sonic1
    import build_sonic2
    import build_soniccd
    out = {}
    for ui in (build_sonic1.ui(), build_sonic2.ui(), build_soniccd.score_ui()):
        out[ui.layout_key()] = {"box": {k: list(v) for k, v in ui.box.items()},
                                "size": {k: list(v) for k, v in ui.size.items()}}
    return out


# NoSwap's own characters' tables in the kit's copy of the tools: emptied (the kit builds only the creator's characters,
# and ignores them anyway: NOSWAP_KIT in extras.py, abilities.py, build_mania_art.py); they hold NoSwap's private notes
EMPTIED = {"extras.py": {"EXTRAS": "[]", "CREDIT_SHORT": "{}", "UI_ACCENT": "{}"},
           "abilities.py": {"ABILITIES": "{}"},
           "build_mania_art.py": {"MANIA_ENABLED": "[]", "MANIA_OVERRIDES": "{}"}}
# This machine's default game folder in the tools (the kit always sets its own: kit.env())
MACHINE_GAME = str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins"
NEUTRAL_GAME = "C:/Program Files (x86)/Steam/steamapps/common/SonicOrigins"
# Comments naming a private character, reworded (the words only; never code)
PRIVATE_PHRASES = []  # (regex, replacement) pairs for comments naming a private character: reworded, never code


def scrub_app():
    """The kit's copy of the tools without NoSwap's own character tables (EMPTIED), private names, or this machine's
    paths. Checked by the leak check."""
    import ast
    for name, names in EMPTIED.items():
        f = APP / "tools" / name
        src = f.read_text()
        lines = src.split("\n")
        spans = []
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) in names:
                spans.append((node.lineno, node.end_lineno, node.targets[0].id))
        if {n for _, _, n in spans} != set(names):
            fail(f"{name}: expected assignments {sorted(names)}, found {[n for _, _, n in spans]}")
        for a, b, n in sorted(spans, reverse=True):
            lines[a - 1:b] = [f"{n} = {names[n]}  # (the Creator Kit: NoSwap's own characters' entries aren't in the kit)"]
        out = "\n".join(lines)
        ast.parse(out)
        f.write_text(out)
    priv = private_names()
    for f in APP.rglob("*"):
        if not f.is_file() or f.suffix not in (".py", ".js", ".md", ".json", ".html", ".txt"):
            continue
        text = f.read_text(errors="ignore")
        new = text.replace(MACHINE_GAME, NEUTRAL_GAME).replace("tools/deploy.sh's default", "Steam's usual folder")
        for pat, rep in PRIVATE_PHRASES:
            new = re.sub(pat, rep, new)
        if f.suffix == ".py":
            new = _strip_private_comments(new, priv)
        if f.suffix == ".py":
            try:
                ast.parse(new)
            except SyntaxError as e:
                fail(f"scrub_app broke {f.relative_to(APP)}: {e}")
        if new != text:
            f.write_text(new)


def _private_re(priv):
    words = sorted({w.lower() for w in priv} | set(PRIVATE_WORDS))
    if not words:
        return re.compile(r"(?!x)x")  # (nothing private: matches nothing)
    return re.compile(r"(?<![Pp]ower )(?<!\.)\b(%s)\b" % "|".join(re.escape(w) for w in words), re.I)


def _strip_private_comments(src, priv):
    """Python source with every comment that names a private character cut off (comments only: tokenize's)."""
    import io
    import tokenize
    hit = _private_re(priv)
    cuts = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT and hit.search(tok.string):
            cuts[tok.start[0]] = tok.start[1]
    if not cuts:
        return src
    lines = src.split("\n")
    for ln, col in cuts.items():
        lines[ln - 1] = lines[ln - 1][:col].rstrip()
    return "\n".join(lines)


def private_names():
    import extras
    out = set()
    for e in extras.private_extras():
        out |= {e["name"].lower(), e["art"].name.lower(), e["key"].split(".")[-1].lower()}
    return out


def scrub_registry(reg):
    """The ability registry without NoSwap's private characters (never released: their names stay out of the kit)."""
    import copy
    reg = copy.deepcopy(reg)
    priv = private_names()
    for e in reg["abilities"].values():
        e["used_by"] = [u for u in e["used_by"] if u["name"].lower() not in priv]
        if (e.get("example_from") or "").lower() in priv:
            e["example_from"] = "a NoSwap character"
        for k in ("description", "input"):
            if isinstance(e.get(k), str):
                e[k] = re.sub(r"\s*\((?:%s)\)" % "|".join(re.escape(p) for p in priv), "", e[k], flags=re.I)
    return reg


KIT_DOCS = SRC / "docs"  # the kit's own guides (character-json.md, toolset-ui.md): written for the kit, not the repo
# Generated text that names the repo's tools, as the kit says it
KIT_ABILITIES_INTRO = [
    (re.compile(r" Generated by `python3 tools/abilities_registry.py --write`.*?`noswap check` uses it\."),
     " `NoSwapCreator abilities [move]` shows the same in a terminal, and `NoSwapCreator check` uses it."),
    (re.compile(r"\*\(no description yet: add one in tools/abilities_text.py\)\*"), "*(no description yet)*")]
# Words a doc the kit ships must not have (the repo's layout and tools: leak_check)
REPO_WORDS = re.compile(r"testmods|tools/noswap\.py|registry\.py|pywebview|make_release|toolset-cli\.md|python3 |"
                        r"build_all\.sh|extras\.py|make_configs")


def kit_abilities_doc(text):
    """docs/abilities.md as the kit ships it: its commands, no repo paths."""
    for pat, rep in KIT_ABILITIES_INTRO:
        text = pat.sub(rep, text)
    text = re.sub(r"(?:a |his own |Emerl's )?make_configs\.py(?: character)?", "NoSwap's own build scripts", text)
    return text.replace("python3 tools/noswap.py ", "NoSwapCreator ")


def roster():
    """docs/roster.md: the characters NoSwap ships (names only; never the private ones), so creators pick their own."""
    import extras
    import make_release
    priv = private_names()
    names = []
    for e in extras.EXTRAS:
        if e["private"]:
            continue
        folder = e["art"].name
        title = (make_release.CHARACTERS.get(folder) or (None,))[0]
        if not title:
            try:
                title = json.loads((e["art"] / "character.json").read_text()).get("full_name")
            except (OSError, ValueError):
                title = None
        title = title or e["name"].title()
        if {title.lower(), folder.lower(), e["name"].lower()} & priv:
            continue
        names.append(title)
    names = sorted(set(names), key=str.lower)
    lines = ["# Characters NoSwap already has", "",
             f"NoSwap has these {len(names)} characters, in its release or as their own downloads (besides Origins' "
             "own Sonic, Tails, Knuckles and Amy). Pick a character that isn't here, or at least give yours its own name, key and folder "
             "id (`docs/character-json.md`, \"Before you start\"), so players can tell them apart and both can be "
             "installed. NoSwap's own keys all start with `noswap.`; yours start with your name.", ""]
    lines += [f"- {n}" for n in names] + [""]
    return "\n".join(lines)


def kit_schema(text):
    """docs/character.schema.json as the kit ships it: the editor shows its descriptions as hints (no repo paths)."""
    doc = json.loads(text)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "description" and isinstance(v, str):
                    v = re.sub(r" \((?:[^()]*\b(?:tools|data)/[^()]*)\)", "", v)
                    v = v.replace("tools/abilities.py's docstring lists them", "docs/abilities.md lists them")
                    o[k] = v.replace("`noswap check`", "Check")
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(doc)
    return json.dumps(doc, indent=1) + "\n"


def example_bean():
    """testmods/bean/character.json as the kit's example: the sheet beside it (Bean.png, not shipped: its page is in the
    example's README), a key of its own."""
    text = (REPO / "testmods" / "bean" / "character.json").read_text()
    text = text.replace('"../Bean.png"', '"Bean.png"').replace(
        '"relative to this folder (testmods/Bean.png, 693x529)"',
        '"in this folder (693x529; not in the kit: download it, example/bean/README.md)"')
    doc = json.loads(text)
    if doc.get("key"):
        fail("testmods/bean/character.json has a key now: update example_bean()")
    text = text.replace('"format": "noswap-character/1",', '"format": "noswap-character/1",\n  "key": "example.bean",', 1)
    doc = json.loads(text)
    assert doc["key"] == "example.bean" and "../" not in text and "testmods" not in text, "example_bean: check the text"
    return text


def kit_registry():
    """A registry with no names in it: every number NoSwap gave is reserved, so the creator's characters get numbers
    after them (hard-coded build IDs in the tools never meet theirs)."""
    import registry
    data = registry.load()
    top = max([v["n"] for v in data["characters"].values()] + [v["n"] for v in data["retired"].values()])
    return {"format": registry.FORMAT, "note": registry.NOTE, "characters": {},
            "retired": {"noswap.reserved": {"n": top, "folder": "", "note": "NoSwap's own numbers 1.." + str(top)}}}


def stage():
    from noswap_cli import kit
    if APP.exists():
        shutil.rmtree(APP)
    for item in kit.APP_ITEMS:
        if item in ("data/kit", "docs/roster.md"):  # (made below)
            continue
        s, d = REPO / item, APP / item
        if s.is_dir():
            shutil.copytree(s, d, ignore=shutil.ignore_patterns(*kit.APP_SKIP, "kit"))
        elif s.is_file():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
        else:
            fail(f"{item} is missing")
    scrub_app()
    dk = APP / "data" / "kit"
    dk.mkdir(parents=True)
    for folder in kit.ORIGINS_PACKS:
        src = REPO / "extracted" / folder
        if not src.is_dir():
            fail(f"extracted/{folder} is missing")
        (dk / f"names-{folder}.txt").write_text("\n".join(names(src)) + "\n")
    mania = Path(os.environ.get("NOSWAP_MANIA_DATA") or Path.home() / "Code" / "mania" / "extracted" / "Data").parent
    (dk / "names-Mania.txt").write_text("\n".join(names(mania)) + "\n")
    # the ability registry first: importing the Sonic 1/2 builders (core_manifest, ui_layout) marks own sounds in
    # abilities.ABILITIES in place (own_sounds.mark_classic), which the registry's examples would show
    import pickle
    import abilities_registry
    if abilities_registry.main(["--check"]) not in (0, None):
        fail("tools/abilities_registry.py --check fails: regenerate docs/abilities.* first")
    reg = scrub_registry(abilities_registry.build())
    (dk / "registry.json").write_text(json.dumps(kit_registry(), indent=1) + "\n")
    (dk / "core.json").write_text(json.dumps(core_manifest(), indent=1) + "\n")
    (dk / "ui_layout.json").write_text(json.dumps(ui_layout(), indent=1) + "\n")
    abilities_registry.build = lambda: reg  # (the kit's docs from the scrubbed registry)
    (dk / "abilities_registry.pickle").write_bytes(pickle.dumps(reg))
    (APP / "docs" / "abilities.json").write_text(abilities_registry.as_json())
    (APP / "docs" / "abilities.md").write_text(kit_abilities_doc(abilities_registry.markdown()))
    for f in ("character-json.md", "toolset-ui.md"):
        shutil.copy2(KIT_DOCS / f, APP / "docs" / f)
    (APP / "docs" / "roster.md").write_text(roster())
    schema = APP / "docs" / "character.schema.json"
    schema.write_text(kit_schema(schema.read_text()))
    from noswap_cli import abilities_info
    priv = private_names()
    (dk / "native_words.json").write_text(json.dumps({sub: sorted(w for w in abilities_info.native_words(sub)
                                                                  if w.lower() not in priv)
                                                      for sub in ("native/src", "native/mania/src")}) + "\n")
    print(f"staged {APP.relative_to(REPO)}: {sum(1 for p in APP.rglob('*') if p.is_file())} files, "
          f"{human(size_of(APP))}; for NoSwap {versions()}")


# ---------------------------------------------------------------- the program

def exe(target, python=None, wine_python=None):
    entry = SRC / "noswap_kit.py"
    work = BUILD / f"pyi-{target}"
    dist = BUILD / f"exe-{target}"
    if dist.exists():
        shutil.rmtree(dist)
    args = ["--noconfirm", "--clean", "--onedir", "--name", EXE, "--distpath", None, "--workpath", None,
            "--specpath", None, "--paths", str(SRC)]
    excludes = ["tkinter", "unittest", "pydoc_data", "test", "lib2to3", "matplotlib", "scipy", "PyQt5", "PyQt6",
                "PySide2", "PySide6", "gi"]
    for x in excludes:
        args += ["--exclude-module", x]
    if target == "linux":
        if not python:
            fail("--linux needs --python (a venv's python with pyinstaller, pillow and numpy)")
        args[args.index("--distpath") + 1] = str(dist)
        args[args.index("--workpath") + 1] = str(work)
        args[args.index("--specpath") + 1] = str(work)
        args += ["--exclude-module", "webview"]  # (Linux: the browser; pywebview's GUI toolkits are too big to bundle)
        cmd = [python, "-m", "PyInstaller", *args, str(entry)]
        env = dict(os.environ)
    else:
        if not wine_python:
            fail("--windows needs --wine-python (Windows Python's python.exe in $WINEPREFIX)")
        def win(p):
            return "Z:" + str(p).replace("/", "\\")
        args[args.index("--distpath") + 1] = win(dist)
        args[args.index("--workpath") + 1] = win(work)
        args[args.index("--specpath") + 1] = win(work)
        args[args.index("--paths") + 1] = win(SRC)
        args += ["--hidden-import", "webview", "--collect-all", "webview", "--hidden-import", "clr_loader",
                 "--hidden-import", "pythonnet"]
        cmd = ["wine", wine_python, "-m", "PyInstaller", *args, win(entry)]
        env = dict(os.environ, WINEDEBUG="-all")
    print("$ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-4000:], r.stderr[-6000:])
        fail(f"PyInstaller ({target}) failed")
    print(f"{dist.relative_to(REPO)}: {human(size_of(dist))}")
    licenses(target, python, wine_python)


LICENSED = ("pillow", "numpy", "pyinstaller", "pywebview", "pythonnet", "clr_loader", "bottle", "proxy_tools")


def licenses(target, python=None, wine_python=None):
    """The third-party licence texts (Python's, and each bundled package's from its dist-info) into
    kit/build/licenses-<target>/."""
    out = BUILD / f"licenses-{target}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if target == "linux":
        code = "import sys, sysconfig; print(sysconfig.get_paths()['purelib']); print(sys.base_prefix)"
        site, base = subprocess.run([python, "-c", code], capture_output=True, text=True).stdout.split()[:2]
        site, pylic = Path(site), [Path(base) / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" / "LICENSE.txt",
                                   Path("/usr/share/licenses/python/LICENSE")]
        pylic += list(Path(base).glob("lib/python3*/LICENSE.txt"))
    else:
        prefix = Path(os.environ.get("WINEPREFIX", "")) / "drive_c" / wine_python.split(":", 1)[1].replace("\\", "/").lstrip("/")
        base = prefix.parent
        site, pylic = base / "Lib" / "site-packages", [base / "LICENSE.txt"]
    py = next((p for p in pylic if p.is_file()), None)
    if py:
        shutil.copy2(py, out / "Python-LICENSE.txt")
    else:
        print(f"warning ({target}): Python's LICENSE.txt not found")
    for name in LICENSED:
        for di in site.glob("*.dist-info"):
            if di.name.lower().replace("-", "_").startswith(name.replace("-", "_") + "_"):
                files = [f for f in di.rglob("*") if f.is_file() and re.match(r"(LICEN[CS]E|COPYING|NOTICE)", f.name, re.I)]
                for f in files:
                    shutil.copy2(f, out / f"{name}-{f.name}")
                if not files:  # (its metadata's licence, e.g. proxy_tools: MIT)
                    meta = (di / "METADATA").read_text(errors="ignore") if (di / "METADATA").is_file() else ""
                    lic = re.search(r"^License: (.+)$", meta, re.M)
                    home = re.search(r"^Home-page: (.+)$", meta, re.M)
                    if not lic:
                        print(f"warning ({target}): no licence in {di.name}")
                        continue
                    (out / f"{name}-LICENSE.txt").write_text(
                        f"{di.name[:-len('.dist-info')]}: licensed under the {lic.group(1).strip()} licence, as its "
                        f"package metadata states" + (f" ({home.group(1).strip()})" if home else "") + ".\n")
    print(f"licences ({target}): {', '.join(sorted(p.name for p in out.iterdir()))}")


# ---------------------------------------------------------------- pack

def pack(version=None):
    if not APP.is_dir():
        fail("stage first")
    v = versions()
    version = version or f"{v['origins']}-preview"
    made = []
    for target in ("windows", "linux"):
        dist = BUILD / f"exe-{target}" / EXE
        if not dist.is_dir():
            print(f"({target}: no program built; skipped)")
            continue
        root = BUILD / f"pack-{target}" / NAME
        if root.parent.exists():
            shutil.rmtree(root.parent)
        shutil.copytree(dist, root)
        shutil.copytree(APP, root / "app")
        for f in ("README.md", "LICENSE.txt", "CREDITS.md"):
            shutil.copy2(SRC / f, root / f)
        text = (root / "README.md").read_text().replace("{VERSION}", version) \
            .replace("{CORE}", v["origins"]).replace("{MANIA}", v["mania"])
        (root / "README.md").write_text(text)
        shutil.copytree(SRC / "example", root / "example")
        (root / "example" / "bean" / "character.json").write_text(example_bean())
        if (SRC / "screenshots").is_dir():
            shutil.copytree(SRC / "screenshots", root / "screenshots")
        else:
            print("warning: no tools/kit/screenshots: the README's pictures are missing")
        lic = BUILD / f"licenses-{target}"
        if lic.is_dir():
            shutil.copytree(lic, root / "licenses")
        else:
            print(f"warning: no {lic.relative_to(REPO)}: the third-party licences are missing")
        docs = root / "docs"
        docs.mkdir()
        for f in ("character-json.md", "abilities.md", "toolset-ui.md", "roster.md"):
            shutil.copy2(APP / "docs" / f, docs / f)
        if target == "linux":
            launcher = root / "NoSwapCreator.sh"
            launcher.write_text('#!/bin/sh\n# The NoSwap Creator Kit: opens the editor in your browser.\n'
                                'cd "$(dirname "$0")" && exec ./NoSwapCreator "$@"\n')
            launcher.chmod(0o755)
        problems = leak_check(root)
        if problems:
            for pr in problems[:40]:
                print("  " + pr)
            fail(f"{target}: {len(problems)} leak(s): not zipped")
        z = OUT / f"{NAME}-{version}-{target}.zip"
        if z.exists():
            z.unlink()
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file() or p.is_symlink():
                    info = zipfile.ZipInfo.from_file(p, f"{NAME}/{p.relative_to(root).as_posix()}")
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(p, "rb") as fh:
                        zf.writestr(info, fh.read())
        with zipfile.ZipFile(z) as zf:
            if zf.testzip() is not None:
                fail(f"{z.name} doesn't read back")
        made.append(z)
        print(f"{z.relative_to(REPO)}: {human(z.stat().st_size)} ({human(size_of(root))} unpacked)")
    return made


def leak_check(root):
    """No game files (every file in extracted/ is hashed; no .rsdk/.pac; no game sheet names), no private characters,
    no paths or e-mail of this machine."""
    problems = []
    game = {}
    for p in (REPO / "extracted").rglob("*"):
        if p.is_file():
            game[hashlib.sha1(p.read_bytes()).hexdigest()] = p.relative_to(REPO).as_posix()
    mania = Path.home() / "Code" / "mania" / "extracted"
    for p in mania.rglob("*") if mania.is_dir() else []:
        if p.is_file():
            game[hashlib.sha1(p.read_bytes()).hexdigest()] = "mania:" + p.relative_to(mania).as_posix()
    home = str(Path.home())
    user = Path.home().name
    words = [_private_re(private_names())]
    own = subprocess.run(["git", "-C", str(REPO), "config", "user.email"], capture_output=True,
                         text=True).stdout.strip().lower().encode() or None
    email = re.compile(rb"[\w.+-]+@(?:proton|protonmail|gmail|outlook|hotmail)\.\w+", re.I)
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        h = hashlib.sha1(data).hexdigest()
        if h in game:
            problems.append(f"{rel}: the same file as {game[h]} (the game's)")
        if p.suffix.lower() in (".rsdk", ".pac", ".acb", ".awb", ".act", ".ani", ".bin") and "_internal" not in rel:
            problems.append(f"{rel}: a game-format file")
        if p.suffix.lower() in (".gif",) and "_internal" not in rel:
            problems.append(f"{rel}: a sprite sheet")
        if any(w.search(rel) for w in words):
            problems.append(f"{rel}: a private character's name in the path")
        if "_internal" in rel or p.suffix.lower() in (".exe", ".dll", ".so", ".pyd") or rel == EXE:
            continue
        text = data.decode("utf-8", errors="ignore")
        if home in text or f"/home/{user}" in text or "/var/mnt/" in text:
            problems.append(f"{rel}: names a path on this machine")
        if email.search(data) and not rel.startswith("licenses/"):  # (licence texts name their authors)
            problems.append(f"{rel}: an e-mail address")
        if own and own in data.lower():
            problems.append(f"{rel}: this repo's git e-mail address")
        for w in words:
            m = w.search(text)
            if m:
                problems.append(f"{rel}: names {m.group()!r}")
                break
        # the guides a creator reads (the kit's README, docs/, the example's): the kit's commands, not the repo's
        if p.suffix == ".md" and not rel.startswith(("app/", "licenses/")) and rel != "CREDITS.md":  # (credits name pywebview)
            m = REPO_WORDS.search(text)
            if m:
                problems.append(f"{rel}: a repo-only word for a kit user: {m.group()!r}")
            for link in re.findall(r"`((?:docs|example|screenshots)/[\w./-]+)`|\]\(([\w./-]+\.(?:md|png))\)", text):
                target = link[0] or link[1]
                if not ((root / target).exists() or (p.parent / target).exists()):
                    problems.append(f"{rel}: links {target}, which the kit doesn't ship")
    return problems


def size_of(p):
    return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file())


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=["stage", "exe", "pack", "all"])
    ap.add_argument("--linux", action="store_true")
    ap.add_argument("--windows", action="store_true")
    ap.add_argument("--python", help="Linux: a python with pyinstaller, pillow and numpy")
    ap.add_argument("--wine-python", help="Windows: python.exe under Wine ($WINEPREFIX)")
    ap.add_argument("--version", help="the kit's version (default: the core's, -preview)")
    ap.add_argument("--core-version", help="the core version the kit's packages are pinned to, Origins and Mania "
                    "(default: mods/NoSwap/mod.ini's and mods/NoSwapMania/mod.ini's); give make_release's --version")
    a = ap.parse_args()
    global CORE_VERSION
    CORE_VERSION = a.core_version
    if a.what in ("stage", "all"):
        stage()
    if a.what == "exe" or a.what == "all":
        targets = [t for t, on in (("linux", a.linux or (a.what == "all" and a.python)),
                                   ("windows", a.windows or (a.what == "all" and a.wine_python))) if on]
        if not targets:
            fail("exe: --linux and/or --windows")
        for t in targets:
            exe(t, a.python, a.wine_python)
    if a.what in ("pack", "all"):
        pack(a.version)


if __name__ == "__main__":
    main()
