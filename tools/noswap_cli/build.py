"""`noswap build <folder>`: build one character with the existing pipeline, in the right order.

Origins (any of s1, s2, cd, s3k: the pipeline always makes all four games together):
  1. a character.json without a make_configs.py shim: tools/character_json.py writes its sheet2ani configs;
  2. tools/build_art.py <folder>: its art for all four games (runs its make_configs.py, cd_config.py, sheet2ani.py,
     build_s3k_art.py);
  3. tools/build_all.sh: every game's scripts, the packages (his among them), the menu archives and the S3&K DLL.
  Steps 2-3 hold the build lock (flock on --lock / $NOSWAP_BUILD_LOCK), so two builds never interleave. Set
  NOSWAP_LOCK_HELD=1 when the caller already holds it.
Mania: tools/build_mania_art.py <folder> (his package in mods/NoSwapMania), if he's Mania-enabled.

It never deploys to the game: copying mods/NoSwap into Origins stays a separate, deliberate step.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .model import REPO, CharacterError, load

GAMES = ("s1", "s2", "cd", "s3k", "mania")
ORIGINS = {"s1", "s2", "cd", "s3k"}
OK, FAILED, USAGE, BUILD_FAILED = 0, 1, 2, 3


def _run(cmd, dry_run):
    shown = " ".join(str(c) for c in cmd)
    print(f"$ {shown}", flush=True)
    if dry_run:
        return True
    t = time.time()
    env = {k: v for k, v in os.environ.items() if k != "NOSWAP_REGISTRY_READONLY"}  # a real build registers
    result = subprocess.run([str(c) for c in cmd], cwd=REPO, env=env)
    if result.returncode:
        print(f"noswap build: step failed (exit {result.returncode}): {shown}", file=sys.stderr)
        return False
    print(f"  ({time.time() - t:.0f} s)", flush=True)
    return True


def _lock_file(fd, wait):
    """An exclusive lock on an open file: flock (POSIX) or msvcrt.locking (Windows). False: held elsewhere (wait=False)."""
    try:
        import fcntl
    except ImportError:  # (Windows)
        import msvcrt
        while True:
            try:
                fd.seek(0)
                msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                if not wait:
                    return False
                time.sleep(0.5)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        return True
    except BlockingIOError:
        return False


def _unlock_file(fd):
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)
    except ImportError:
        import msvcrt
        fd.seek(0)
        msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)


class Lock:
    def __init__(self, path):
        path = path or os.environ.get("NOSWAP_BUILD_LOCK")
        self.path = Path(path) if path else Path(tempfile.gettempdir()) / "noswap-build.lock"
        self.fd = None

    def __enter__(self):
        if os.environ.get("NOSWAP_LOCK_HELD") == "1":
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = open(self.path, "a+")
        if not _lock_file(self.fd, wait=False):
            print(f"waiting for the build lock ({self.path}): another build is running ...", flush=True)
            _lock_file(self.fd, wait=True)
        return self

    def __exit__(self, *exc):
        if self.fd:
            _unlock_file(self.fd)
            self.fd.close()


# The Creator Kit's build (tools/noswap_cli/kit.py), in place of tools/build_all.sh: the same Python steps, without the
# parts that are NoSwap's own (the S3&K DLL, Origins' menu archives, Mania Lock-On: the released core has them)
KIT_STEPS = ["refresh_characters.py", "build_sonic1.py", "build_sonic2.py", "build_soniccd.py", "build_s3k_hud.py",
             "build_packages.py"]


def run(folder, games="s1,s2,cd,s3k,mania", check_first=True, dry_run=False, lock=None):
    wanted = {g.strip().lower() for g in games.split(",") if g.strip()}
    bad = wanted - set(GAMES)
    if bad:
        print(f"error: unknown game(s) {', '.join(sorted(bad))}: use {', '.join(GAMES)}", file=sys.stderr)
        return USAGE
    try:
        ch = load(folder)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return FAILED
    if check_first:
        from . import check
        _, report = check.run(folder)
        if report.count("error"):
            print(f"{ch.id}: the check found {report.count('error')} error(s); not building (--no-check to build anyway):")
            report.print(sys.stdout)
            return FAILED
    py = sys.executable
    from . import kit
    if kit.active():  # (the Creator Kit: the game files come from Set up)
        st = kit.status()
        need = [g for g, ok, on in (("Sonic Origins", st["ready_origins"], wanted & ORIGINS),
                                    ("Sonic Mania", st["ready_mania"], "mania" in wanted)) if on and not ok]
        if need:
            print(f"error: {' and '.join(need)} isn't set up: run Set up first (the editor's Settings tab, or "
                  "`setup --origins DIR --mania DIR`), or leave that game out", file=sys.stderr)
            return USAGE
    if wanted & ORIGINS:
        if ch.extra is None:
            where = ("in the kit's characters folder (one folder each, with its character.json)" if kit.active()
                     else "as testmods/*/character.json or in $NOSWAP_CHARACTER_DIRS")
            print(f"error: the Origins build didn't find {ch.id}. Characters are found {where} "
                  f"(`check -v {ch.id}` shows the details).", file=sys.stderr)
            return FAILED
        if wanted & ORIGINS != ORIGINS:
            print("note: the Origins games are built together; building all four (s1, s2, cd, s3k)")
        if ch.kind == "json" and not (ch.folder / "make_configs.py").exists():
            if not _run([py, REPO / "tools" / "character_json.py", ch.folder], dry_run):
                return BUILD_FAILED
        from . import kit
        if kit.active():
            steps = [[py, REPO / "tools" / "build_art.py", ch.id]] + [[py, REPO / "tools" / s] for s in KIT_STEPS]
        else:
            steps = [[py, REPO / "tools" / "build_art.py", ch.id], ["bash", REPO / "tools" / "build_all.sh"]]
        with Lock(lock):
            for cmd in steps:
                if not _run(cmd, dry_run):
                    return BUILD_FAILED
        print(f"{ch.id}: Origins {'would be ' if dry_run else ''}built (mods/NoSwap; his package: "
              f"mods/NoSwap/characters/{ch.id}). Not deployed.")
    if "mania" in wanted:
        try:
            from build_mania_art import MANIA_ALL
        except Exception as e:
            print(f"Mania: can't load tools/build_mania_art.py ({e}); skipped", file=sys.stderr)
            return BUILD_FAILED
        if ch.id not in MANIA_ALL:
            print(f"Mania: {ch.id} isn't Mania-enabled (character.json \"games\": {{\"mania\": true}}, or "
                  "build_mania_art.py's MANIA_ENABLED); skipped")
        elif not _run([py, REPO / "tools" / "build_mania_art.py", ch.id], dry_run):
            return BUILD_FAILED
        else:
            print(f"{ch.id}: Mania {'would be ' if dry_run else ''}built (mods/NoSwapMania/Data/Sprites/NoSwap/{ch.id}).")
    from . import kit
    if kit.active() and not dry_run:  # (the kit: the installable mods, checked against the core they're for)
        from build_mania_art import MANIA_ALL
        made = [g for g in ("origins", "mania") if (g == "origins" and wanted & ORIGINS)
                or (g == "mania" and "mania" in wanted and ch.id in MANIA_ALL)]
        problems = kit.export(ch.folder, made)
        if problems:
            for pr in problems:
                print(f"error: {pr}", file=sys.stderr)
            print(f"{ch.id}: built, but it doesn't fit the NoSwap core this kit is for (see above): not exported "
                  "for install", file=sys.stderr)
            return BUILD_FAILED
        print(f"{ch.id}: ready to install: {kit.layout()['output'] / ch.id} (Deploy copies it into your games)")
    return OK
