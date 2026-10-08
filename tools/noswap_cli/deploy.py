"""`noswap deploy`: copy the built mods into the games (what tools/deploy.sh and tools/deploy_mania.sh do).

Origins: every folder in mods/ except NoSwapMania is mirrored into HedgeModManager's mods folder (the game's
build/main/projects/exec/mods), like deploy.sh's `rsync -a --delete --exclude '*.log' --exclude 'NoSwapS3K.ini'
--exclude 'cache/'`: changed files are copied (size or time differ), files that aren't in the build any more are
removed, and the game's own files are kept (logs, the DLL's cache/ folder, and the player's NoSwapS3K.ini, which is
installed only when it's missing).
Mania: <run>/mods/NoSwapMania becomes a symlink to the repo's mods/NoSwapMania (so later builds are live at the next
start), and <run>/mods/modconfig.ini gets NoSwapMania=y (other mods' lines are left alone), like deploy_mania.sh.

Where to: the user's settings file (settings_path(): ~/.config/noswap/settings.json, %APPDATA%\\noswap\\settings.json,
~/Library/Application Support/noswap/settings.json; $NOSWAP_SETTINGS overrides it), never the repo. Unset, Origins is
found through Steam (libraryfolders.vdf, appmanifest_1794960.acf), else deploy.sh's default; Mania is ~/Code/mania/run
(the decomp's play folder), else Steam's Sonic Mania folder if it holds a decomp build.

Both games read the DLL / the mod at startup: a running game is reported (deploy still goes ahead) with "restart it".
"""
import fnmatch
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from .model import REPO

MODS = REPO / "mods"
MANIA_MOD = "NoSwapMania"
ORIGINS_APP, MANIA_APP = "1794960", "584400"
ORIGINS_EXEC = Path("build/main/projects/exec")
# deploy.sh's default
DEPLOY_SH_DEFAULT = str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins/build/main/projects/exec/mods"
MANIA_DEFAULT = Path.home() / "Code" / "mania" / "run"
# rsync's --exclude list in deploy.sh: kept in the game's folder, never copied over nor removed
KEEP_FILES = ("*.log", "NoSwapS3K.ini")
KEEP_DIRS = ("cache",)
KEYS = {"origins": "origins_mods", "mania": "mania_run"}
OK, FAILED, USAGE, DEPLOY_FAILED = 0, 1, 2, 3
RESTART = "restart the game: the DLL / scripts load at startup"


# ------------------------------------------------------------------ settings

def settings_path():
    if os.environ.get("NOSWAP_SETTINGS"):
        return Path(os.environ["NOSWAP_SETTINGS"])
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "noswap" / "settings.json"


def load_settings():
    try:
        data = json.loads(settings_path().read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(**changes):
    """Set (a path) or clear (None / "") settings: {origins_mods, mania_run}. Returns the new settings."""
    data = load_settings()
    for k, v in changes.items():
        if v is None or str(v).strip() == "":
            data.pop(k, None)
        else:
            data[k] = str(Path(os.path.expanduser(str(v).strip())))
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, p)
    return data


# ------------------------------------------------------------------ finding the games

def _vdf_values(text, key):
    return [v.replace("\\\\", "\\") for v in re.findall(r'"%s"\s+"((?:[^"\\]|\\.)*)"' % re.escape(key), text)]


def steam_libraries():
    """Every Steam library folder listed by the Steam installs this machine has (libraryfolders.vdf)."""
    roots = []
    if sys.platform == "win32":
        try:
            import winreg
            for hive, sub, name in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                    (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Valve\Steam", "InstallPath"),
                                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Valve\Steam", "InstallPath")):
                try:
                    with winreg.OpenKey(hive, sub) as k:
                        roots.append(Path(winreg.QueryValueEx(k, name)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        roots.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    elif sys.platform == "darwin":
        roots.append(Path.home() / "Library" / "Application Support" / "Steam")
    else:
        h = Path.home()
        roots += [h / ".steam" / "steam", h / ".local" / "share" / "Steam", h / ".steam" / "root",
                  h / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
                  h / "snap" / "steam" / "common" / ".local" / "share" / "Steam"]
    libs, seen = [], set()

    def add(p):
        try:
            key = os.path.realpath(p)
        except OSError:
            return
        if key not in seen and Path(p).is_dir():
            seen.add(key)
            libs.append(Path(p))

    for r in roots:
        add(r)
        try:
            text = (r / "steamapps" / "libraryfolders.vdf").read_text(errors="replace")
        except OSError:
            continue
        for p in _vdf_values(text, "path"):
            add(Path(p))
    return libs


def steam_app_folder(app, default_dir):
    """<library>/steamapps/common/<installdir> of the first library with appmanifest_<app>.acf, else None."""
    for lib in steam_libraries():
        acf = lib / "steamapps" / f"appmanifest_{app}.acf"
        try:
            text = acf.read_text(errors="replace")
        except OSError:
            continue
        dirs = _vdf_values(text, "installdir")
        return lib / "steamapps" / "common" / (dirs[0] if dirs else default_dir)
    return None


def origins_mods(path):
    """Origins' mods folder from what was given: the mods folder itself, the game's folder (the one with build/ and
    image/ in it), or its exec folder (the one with SonicOrigins.exe): one setting is enough."""
    p = Path(os.path.expanduser(str(path).strip()))
    if (p / ORIGINS_EXEC).is_dir():
        return p / ORIGINS_EXEC / "mods"
    if (p / "SonicOrigins.exe").exists() and p.name != "mods":
        return p / "mods"
    return p


def check_origins(path):
    """Is `path` Origins' mods folder (HedgeModManager's)? The game's folder also works (origins_mods). {ok, problems,
    notes}"""
    if not str(path or "").strip():
        return {"ok": False, "problems": ["not set"], "notes": []}
    p = origins_mods(path)
    problems, notes = [], []
    if str(p) != str(Path(os.path.expanduser(str(path).strip()))):
        notes.append(f"the game's mods folder: {p}")
    exe = p.parent / "SonicOrigins.exe"
    if not p.is_dir():
        problems.append("no such folder" + (" (the game is there: start HedgeModManager once to make it)"
                                            if exe.exists() else ""))
        return {"ok": False, "problems": problems, "notes": notes}
    db = p / "ModsDB.ini"
    if not exe.exists() and not db.exists():
        problems.append("not Origins' mods folder: no SonicOrigins.exe next to it, no ModsDB.ini in it "
                        "(it's <Sonic Origins>/build/main/projects/exec/mods)")
    if exe.exists():
        notes.append("SonicOrigins.exe next to it")
        if not (p.parent / "dinput8.dll").exists():
            notes.append("no dinput8.dll: HedgeModManager's mod loader isn't installed yet")
    if db.exists():
        text = db.read_text(errors="replace")
        guid = re.search(r'^([0-9a-fA-F-]+)="[^"\n]*[\\/]NoSwap[\\/]mod\.ini"', text, re.M)
        if not guid:
            notes.append("ModsDB.ini: the NoSwap core isn't listed yet (install it, then tick it in HedgeModManager)")
        elif re.search(r'^ActiveMod\d+="?%s' % re.escape(guid.group(1)), text, re.M):
            notes.append("ModsDB.ini: the NoSwap core is enabled in HedgeModManager")
        else:
            notes.append("ModsDB.ini: the NoSwap core is listed but not enabled in HedgeModManager")
    else:
        notes.append("no ModsDB.ini (HedgeModManager hasn't saved a mod list here yet)")
    if not any((d / "NoSwapS3K.dll").is_file() for d in p.iterdir() if d.is_dir()):
        notes.append("no NoSwapS3K.dll in any mod here: the NoSwap core isn't (fully) installed in this folder")
    return {"ok": not problems, "problems": problems, "notes": notes}


DECOMP_EXES = ("RSDKv5U", "RSDKv5", "RSDKv5U.exe", "RSDKv5.exe")


def check_mania(path):
    """Is `path` a Sonic Mania decomp play folder (its engine and game data)? {ok, problems, notes}"""
    p = Path(path)
    problems, notes = [], []
    if not str(path).strip() or not p.is_dir():
        return {"ok": False, "problems": ["no such folder" if str(path).strip() else "not set"], "notes": notes}
    exe = next((n for n in DECOMP_EXES if (p / n).exists()), None)
    if exe:
        notes.append(f"{exe} (the decompilation)")
    elif (p / "SonicMania.exe").exists():
        problems.append("only Steam's SonicMania.exe here: the mod needs the decompilation (RSDKv5U)")
    else:
        problems.append("no RSDKv5U (the decompilation's engine)")
    if (p / "Data.rsdk").exists() or (p / "Data").is_dir():
        notes.append("game data (Data.rsdk or Data/)")
    else:
        problems.append("no Data.rsdk or Data folder (the game's data)")
    if not any((p / n).exists() for n in ("libGame.so", "Game.dll", "libGame.dylib")):
        notes.append("no libGame.so / Game.dll seen (the game logic; Settings.ini may name another)")
    if (p / "mods" / MANIA_MOD).is_symlink():
        notes.append(f"mods/{MANIA_MOD} -> {os.readlink(p / 'mods' / MANIA_MOD)}")
    return {"ok": not problems, "problems": problems, "notes": notes}


def targets():
    """Where each game deploys to: {origins|mania: {path, source, ok, problems, notes, candidates}}."""
    s = load_settings()
    out = {}
    in_kit = bool(os.environ.get("NOSWAP_KIT"))
    setup = _kit_setup() if in_kit else {}
    # Origins
    cands = []
    if setup.get("origins"):  # (the Creator Kit: the game Set up read is where its mods go, unless set otherwise)
        cands.append({"path": str(origins_mods(setup["origins"])), "source": "the Sonic Origins you set up"})
    steam = steam_app_folder(ORIGINS_APP, "SonicOrigins")
    if steam:
        cands.append({"path": str(steam / ORIGINS_EXEC / "mods"), "source": "Steam (app 1794960)"})
    if not in_kit:
        cands.append({"path": DEPLOY_SH_DEFAULT, "source": "tools/deploy.sh's default"})
    if not cands:
        cands.append({"path": "", "source": "not found: set up Sonic Origins (Settings tab, or the setup command)"})
    setting = s.get(KEYS["origins"])
    out["origins"] = _pick(str(origins_mods(setting)) if setting else None, cands, check_origins)
    # Mania
    cands = [] if in_kit else [{"path": str(MANIA_DEFAULT), "source": "the decomp play folder (~/Code/mania/run)"}]
    if setup.get("mania"):
        cands.append({"path": setup["mania"], "source": "the Sonic Mania folder you set up"})
    steam = steam_app_folder(MANIA_APP, "Sonic Mania")
    if steam:
        cands.append({"path": str(steam), "source": "Steam (app 584400), if it holds a decomp build"})
    if not cands:
        cands.append({"path": "", "source": "not found: set the decompilation's play folder"})
    out["mania"] = _pick(s.get(KEYS["mania"]), cands, check_mania)
    return out


def _kit_setup():
    """The Creator Kit's Set up state (kit-setup.json: the game folders it read), {} outside the kit."""
    try:
        from . import kit
        return kit.load_state()
    except Exception:
        return {}


def _pick(setting, cands, check):
    seen, uniq = set(), []
    for c in cands:
        if c["path"] not in seen:
            seen.add(c["path"])
            uniq.append(dict(c, **check(c["path"])))
    if setting:
        chosen = dict(path=setting, source="settings", **check(setting))
    else:
        chosen = next((c for c in uniq if c["ok"]), None) or dict(uniq[0])
        chosen = dict(chosen, source=chosen["source"] + " (detected)")
    chosen["candidates"] = uniq
    chosen["exists"] = Path(chosen["path"]).is_dir()
    return chosen


# ------------------------------------------------------------------ is the game running?

def running():
    """Running Origins / Mania decomp processes: [{game, pid, name}] (Linux /proc, Wine/Proton included; Windows
    tasklist; elsewhere ps)."""
    found = []

    def classify(name):
        base = re.split(r"[\\/]", name.strip())[-1].lower()
        if base in ("sonicorigins.exe", "sonicorigins.ex"):  # (/proc comm is cut to 15 characters)
            return "origins"
        if base in {n.lower() for n in DECOMP_EXES}:
            return "mania"
        return None

    if sys.platform.startswith("linux") and Path("/proc").is_dir():
        me = os.getpid()
        for d in Path("/proc").iterdir():
            if not d.name.isdigit() or int(d.name) == me:
                continue
            try:
                argv0 = (d / "cmdline").read_bytes().split(b"\0")[0].decode(errors="replace")
                comm = (d / "comm").read_text().strip()
            except OSError:
                continue
            game = classify(argv0) or classify(comm)
            if game:
                try:  # (where it runs from: Proton / Wine and the decomp start in the game's folder)
                    folder = os.path.realpath(d / "cwd")
                except OSError:
                    folder = None
                found.append({"game": game, "pid": int(d.name), "name": re.split(r"[\\/]", argv0)[-1] or comm,
                              "folder": folder})
        return found
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10).stdout
            rows = [(r[0], r[1]) for r in (re.findall(r'"([^"]*)"', line) for line in out.splitlines()) if len(r) > 1]
        else:
            out = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True, timeout=10).stdout
            rows = [(p[1], p[0]) for p in (line.strip().split(None, 1) for line in out.splitlines()) if len(p) == 2]
    except (OSError, subprocess.SubprocessError):
        return found
    for name, pid in rows:
        game = classify(name)
        if game:
            found.append({"game": game, "pid": int(pid) if str(pid).isdigit() else pid, "name": name})
    return found


def game_folder(game, target):
    """The folder the game runs from, for a deploy target: Origins' exec folder (its mods folder's parent), Mania's
    play folder."""
    if not target:
        return None
    t = origins_mods(target).parent if game == "origins" else Path(target)
    try:
        return os.path.realpath(t)
    except OSError:
        return str(t)


def running_at(procs, game, target):
    """The running processes of `game` that a deploy to `target` affects: those started from that game folder (one
    whose folder isn't known counts: it can't be ruled out)."""
    where = game_folder(game, target)
    return [p for p in procs if p["game"] == game and (not p.get("folder") or not where or p["folder"] == where)]


# ------------------------------------------------------------------ Origins: the rsync, in Python

def _kept(name, is_dir):
    return (is_dir and name in KEEP_DIRS) or (not is_dir and any(fnmatch.fnmatchcase(name, g) for g in KEEP_FILES))


def _remove(p, dry, log):
    log.append(("delete", p))
    if dry:
        return
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


def mirror(src, dst, dry=False, log=None):
    """rsync -a --delete --exclude '*.log' --exclude 'NoSwapS3K.ini' --exclude 'cache/' src/ dst/:
    -> [(action, path)] (copy, delete, mkdir, link)."""
    log = [] if log is None else log
    src, dst = Path(src), Path(dst)
    if dst.is_symlink() or (dst.exists() and not dst.is_dir()):
        _remove(dst, dry, log)
    if not dst.is_dir():
        log.append(("mkdir", dst))
        if not dry:
            dst.mkdir()
    names = set()
    for s in sorted(src.iterdir()):
        is_dir = s.is_dir() and not s.is_symlink()
        if _kept(s.name, is_dir):
            continue
        names.add(s.name)
        d = dst / s.name
        if s.is_symlink():
            target = os.readlink(s)
            if d.is_symlink() and os.readlink(d) == target:
                continue
            if d.exists() or d.is_symlink():
                _remove(d, dry, log)
            log.append(("link", d))
            if not dry:
                os.symlink(target, d)
        elif is_dir:
            if (d.exists() or d.is_symlink()) and (d.is_symlink() or not d.is_dir()):
                _remove(d, dry, log)
            mirror(s, d, dry, log)
        else:
            st = s.stat()
            if d.is_symlink() or d.is_dir():
                _remove(d, dry, log)
            try:
                dt = d.stat()
            except FileNotFoundError:
                dt = None
            if dt is None or dt.st_size != st.st_size or int(dt.st_mtime) != int(st.st_mtime):
                log.append(("copy", d))
                if not dry:
                    shutil.copy2(s, d)
            elif stat.S_IMODE(dt.st_mode) != stat.S_IMODE(st.st_mode) and not dry:
                os.chmod(d, stat.S_IMODE(st.st_mode))
    if dst.is_dir():
        for d in sorted(dst.iterdir()):
            is_dir = d.is_dir() and not d.is_symlink()
            if d.name not in names and not _kept(d.name, is_dir):
                _remove(d, dry, log)
    if not dry:
        shutil.copystat(src, dst)  # (rsync -a keeps the folders' times and modes too)
    return log


def deploy_origins(target, dry=False, character=None):
    target = Path(target)
    if not target.is_dir():
        print(f"Origins: {target} doesn't exist: set the mods folder (noswap deploy --set-origins DIR, or the "
              "editor's Settings tab)", file=sys.stderr)
        return FAILED
    mods = [m for m in sorted(MODS.iterdir()) if m.is_dir() and m.name != MANIA_MOD]
    if not mods:
        print(f"Origins: nothing built in {MODS}: build first", file=sys.stderr)
        return FAILED
    for mod in mods:
        dst = target / mod.name
        log = mirror(mod, dst, dry)
        ini = mod / "NoSwapS3K.ini"
        if ini.is_file() and not (dst / "NoSwapS3K.ini").is_file():
            log.append(("copy", dst / "NoSwapS3K.ini"))
            if not dry:
                shutil.copy(ini, dst / "NoSwapS3K.ini")  # (deploy.sh: plain cp, the time is now)
        counts = {a: sum(1 for x, _ in log if x == a) for a in ("copy", "delete", "mkdir", "link")}
        words = {"copy": "file(s) to copy" if dry else "file(s) copied", "delete": "to remove" if dry else "removed",
                 "mkdir": "new folder(s)", "link": "link(s)"}
        what = ", ".join(f"{n} {words[a]}" for a, n in counts.items() if n) or "up to date"
        print(f"{'would deploy' if dry else 'deployed'} {mod.name} -> {dst} ({what})", flush=True)
        if dry:
            for a, p in log[:40]:
                print(f"  {a:6} {p.relative_to(target)}")
            if len(log) > 40:
                print(f"  ... and {len(log) - 40} more")
    return OK


# ------------------------------------------------------------------ Mania: the symlink and modconfig.ini

def enable_line(text):
    """modconfig.ini with NoSwapMania=y, as deploy_mania.sh's sed does it (None: the file doesn't exist)."""
    line = f"{MANIA_MOD}=y"
    if text is None:
        return f"[Mods]\n{line}\n"
    lines = text.split("\n")
    if any(ln.startswith(f"{MANIA_MOD}=") for ln in lines):
        return "\n".join(line if ln.startswith(f"{MANIA_MOD}=") else ln for ln in lines)
    if any(ln.startswith("[Mods]") for ln in lines):
        out = []
        for ln in lines:
            out.append(ln)
            if ln.startswith("[Mods]"):
                out.append(line)
        return "\n".join(out)
    return text + f"[Mods]\n{line}\n"


def deploy_mania(run, dry=False):
    run = Path(run)
    src = MODS / MANIA_MOD
    lib = src / (f"{MANIA_MOD}.dll" if sys.platform == "win32" else f"{MANIA_MOD}.so")
    if not lib.is_file():
        print(f"Mania: mods/{MANIA_MOD}/{lib.name} missing: run native/mania/build.sh first", file=sys.stderr)
        return FAILED
    if not list((src / "Data" / "Sprites" / "NoSwap").glob("*/noswap_character.json")):
        print("Mania: no character packages: run tools/build_mania_art.py first", file=sys.stderr)
        return FAILED
    if not run.is_dir():
        print(f"Mania: {run} doesn't exist: set the play folder (noswap deploy --set-mania DIR, or the editor's "
              "Settings tab)", file=sys.stderr)
        return FAILED
    link = run / "mods" / MANIA_MOD
    if (link.exists() or link.is_symlink()) and not link.is_symlink():
        print(f"Mania: {link} exists and isn't our symlink: not touching it", file=sys.stderr)
        return FAILED
    cfg = run / "mods" / "modconfig.ini"
    old = cfg.read_text(newline="") if cfg.is_file() else None  # (keeps \r\n as sed does)
    new = enable_line(old)
    if dry:
        now = os.readlink(link) if link.is_symlink() else None
        print(f"would deploy: {link} -> {src}" + ("" if now is None else
              (" (already)" if now == str(src) else f" (now -> {now})")))
        print(f"would {'leave' if new == old else ('write' if old is None else 'edit')} {cfg}: {MANIA_MOD}=y")
        return OK
    (run / "mods").mkdir(exist_ok=True)
    if link.is_symlink():
        link.unlink()
    os.symlink(src, link, target_is_directory=True)
    if new != old:
        cfg.write_text(new, newline="")
    print(f"deployed: {link} -> mods/{MANIA_MOD}, enabled in {cfg}", flush=True)
    return OK


# ------------------------------------------------------------------ the command

def show(t=None, procs=None):
    t = t or targets()
    print(f"settings: {settings_path()}{'' if settings_path().exists() else ' (not made yet: using the detected folders)'}")
    for game, title in (("origins", "Origins mods"), ("mania", "Mania run")):
        x = t[game]
        print(f"{title}: {x['path']}  [{x['source']}; {'ok' if x['ok'] else 'NOT OK'}]")
        for p in x["problems"]:
            print(f"    problem: {p}")
        for n in x["notes"]:
            print(f"    {n}")
        for c in x["candidates"]:
            if c["path"] != x["path"]:
                print(f"    also: {c['path']} [{c['source']}; {'ok' if c['ok'] else 'no: ' + '; '.join(c['problems'])}]")
    procs = running() if procs is None else procs
    def where(p):
        hit = running_at([p], p["game"], t[p["game"]]["path"])
        return "" if hit else f", from {p['folder']}: not the folder above"
    print("running: " + (", ".join(f"{p['name']} (pid {p['pid']}{where(p)})" for p in procs) or "neither game"))


def run(origins=False, mania=False, dry_run=False, character=None, force=False, lock=None,
        set_origins=None, set_mania=None, show_only=False):
    if set_origins is not None or set_mania is not None:
        changes = {}
        if set_origins is not None:
            changes[KEYS["origins"]] = set_origins
        if set_mania is not None:
            changes[KEYS["mania"]] = set_mania
        save_settings(**changes)
        print(f"saved {settings_path()}")
        show()
        return OK
    if show_only:
        show()
        return OK
    if not origins and not mania:
        origins = mania = True
    if character:
        return _character(character, origins, mania, dry_run)
    t = targets()
    status = OK
    procs = running()
    from .build import Lock
    import contextlib
    # (a real deploy waits for a running build, so it never copies a half-built mods/)
    with (contextlib.nullcontext() if dry_run else Lock(lock)):
        for game, fn in (("origins", deploy_origins), ("mania", deploy_mania)):
            if not (origins if game == "origins" else mania):
                continue
            x = t[game]
            print(f"{'Origins' if game == 'origins' else 'Mania'}: {x['path']} ({x['source']})", flush=True)
            if not x["ok"]:
                print(f"  {'warning' if force else 'error'}: {'; '.join(x['problems'])}", file=sys.stderr)
                if not force:
                    print("  not deployed (fix the folder in the settings, or --force)", file=sys.stderr)
                    status = max(status, FAILED)
                    continue
            try:
                status = max(status, fn(x["path"], dry_run))
            except OSError as e:
                print(f"  deploy failed: {e}", file=sys.stderr)
                status = max(status, DEPLOY_FAILED)
    games = {"origins"} if origins and not mania else {"mania"} if mania and not origins else {"origins", "mania"}
    for game, title in (("origins", "Sonic Origins"), ("mania", "Sonic Mania (the decomp)")):
        hit = running_at(procs, game, t[game]["path"]) if game in games else []
        if hit:
            names = ", ".join(f"{p['name']}, pid {p['pid']}" for p in hit)
            print(f"warning: {title} is running ({names}): {RESTART}", flush=True)
    return status


def _character(folder, origins, mania, dry_run):
    """--character: deploy one character's package only. Designed, not built: it waits for step 5 (the public /
    private split), when each character becomes its own mod. The plan: Origins mirrors mods/NoSwap/characters/<id>/
    (after step 5: that character's own mod folder) into the game, leaving the core alone; Mania needs no copy (the
    mod folder is a symlink, the package is live), only the core's symlink and modconfig line. Today a package's
    S1/S2/CD scripts come from the core build they were made with, so a package alone can mismatch the core in the
    game: deploy everything instead."""
    from .model import CharacterError, resolve_folder
    try:
        cid = resolve_folder(folder).name
    except CharacterError:
        cid = Path(folder).name
    pkg = MODS / "NoSwap" / "characters" / cid
    t = targets()
    print(f"--character {cid}: not available yet (it comes with step 5, when each character is its own mod).")
    if origins:
        print(f"  Origins would mirror {pkg}{'' if pkg.is_dir() else ' (not built)'} -> "
              f"{Path(t['origins']['path']) / 'NoSwap' / 'characters' / cid}")
    if mania:
        mp = MODS / MANIA_MOD / "Data" / "Sprites" / "NoSwap" / cid
        print(f"  Mania: nothing to copy: {mp} is live through the symlink{'' if mp.is_dir() else ' (not built yet)'}")
    print("  For now deploy everything: noswap deploy" + (" --dry-run" if dry_run else ""))
    return OK if dry_run else USAGE
