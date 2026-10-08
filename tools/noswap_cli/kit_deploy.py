"""`noswap deploy` in the Creator Kit: install the characters a build made (output/<id>/, tools/noswap_cli/kit.py) into
the games, each as its own mod beside the released NoSwap core, never the kit's working tree.

- Origins: output/<id>/origins/NoSwap-<Name>/ is mirrored into HedgeModManager's mods folder (deploy.targets()); enable
  it in HedgeModManager (the NoSwap core mod must be installed and enabled too).
- Mania: output/<id>/mania/NoSwap-<Name>/ is mirrored into <play folder>/mods/ and enabled in mods/modconfig.ini.
"""
import sys
from pathlib import Path

from . import deploy, kit

OK, FAILED, USAGE, DEPLOY_FAILED = 0, 1, 2, 3


def _built(character):
    out = kit.layout()["output"]
    if character:
        from .model import CharacterError, resolve_folder
        try:
            cid = resolve_folder(character).name
        except CharacterError:
            cid = Path(character).name
        return [out / cid]
    return sorted(d for d in out.iterdir() if d.is_dir()) if out.is_dir() else []


def _core_installed(mods, dll):
    return any((d / dll).is_file() for d in Path(mods).iterdir() if d.is_dir()) if Path(mods).is_dir() else False


def _core_note(mods, game):
    """One line on the NoSwap core in that mods folder (the folder check's ModsDB.ini note says whether it's enabled)."""
    import re
    if game == "origins":
        if _core_installed(mods, "NoSwapS3K.dll"):
            ini = next(d for d in Path(mods).iterdir() if (d / "NoSwapS3K.dll").is_file()) / "mod.ini"
            want = kit._core()["origins"]["version"]
            m = re.search(r'^Version="?([^"\r\n]*)', ini.read_text(errors="replace"), re.M) if ini.is_file() else None
            if m and m.group(1) != want:
                return (f"  warning: the NoSwap core here is version {m.group(1)}; this kit's characters need {want} "
                        "(get the matching core, or the kit for that core)")
            return "  then enable it in HedgeModManager, beside the NoSwap core"
        if (Path(mods) / "NoSwap" / "mod.ini").is_file():
            return ("  note: this mods folder's NoSwap folder has no NoSwapS3K.dll: the NoSwap core isn't fully "
                    "installed (reinstall it: the character needs it)")
        return "  note: the NoSwap core mod isn't in this mods folder: install it too (the character needs it)"
    if _core_installed(mods, "NoSwapMania.dll") or _core_installed(mods, "NoSwapMania.so"):
        return None
    if (Path(mods) / "NoSwapMania").exists():
        return ("  note: this mods folder's NoSwapMania folder has no NoSwapMania.so / .dll: the NoSwap Mania mod isn't "
                "fully installed (reinstall it: the character needs it)")
    return "  note: the NoSwap Mania mod isn't in this mods folder: install it too (the character needs it)"


def enable(text, name):
    """modconfig.ini with <name>=y (deploy.enable_line, for any mod)."""
    line = f"{name}=y"
    if text is None:
        return f"[Mods]\n{line}\n"
    lines = text.split("\n")
    if any(ln.startswith(f"{name}=") for ln in lines):
        return "\n".join(line if ln.startswith(f"{name}=") else ln for ln in lines)
    if any(ln.startswith("[Mods]") for ln in lines):
        # at the end of [Mods], after the mods already there (the NoSwap Mania mod first: the loader's order)
        start = next(k for k, ln in enumerate(lines) if ln.startswith("[Mods]"))
        end = next((k for k in range(start + 1, len(lines)) if lines[k].startswith("[")), len(lines))
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        eol = "\r" if lines[start].endswith("\r") else ""
        return "\n".join(lines[:end] + [line + eol] + lines[end:])
    return text + f"\n[Mods]\n{line}\n"


def run(origins=False, mania=False, dry_run=False, character=None, force=False):
    if not origins and not mania:
        origins = mania = True
    chars = _built(character)
    if not chars or not any(c.is_dir() for c in chars):
        print("nothing to install: build the character first (its installable mods go to "
              f"{kit.layout()['output']})", file=sys.stderr)
        return FAILED
    t = deploy.targets()
    status = OK
    for game in ("origins", "mania"):
        if not (origins if game == "origins" else mania):
            continue
        x = t[game]
        title = "Origins" if game == "origins" else "Mania"
        mods = Path(x["path"]) if game == "origins" else Path(x["path"]) / "mods"
        print(f"{title}: {mods} ({x['source']})", flush=True)
        if not x["ok"]:
            print(f"  {'warning' if force else 'error'}: {'; '.join(x['problems'])}", file=sys.stderr)
            if not force:
                print("  not installed (set the folder in Settings, or --force)", file=sys.stderr)
                status = max(status, FAILED)
                continue
        for c in chars:
            src = sorted(p for p in (c / game).iterdir() if p.is_dir()) if (c / game).is_dir() else []
            if not src:
                print(f"  {c.name}: not built for {title}")
                continue
            for mod in src:
                try:
                    if not dry_run:
                        mods.mkdir(parents=True, exist_ok=True)
                    log = deploy.mirror(mod, mods / mod.name, dry_run)
                    n = sum(1 for a, _ in log if a == "copy")
                    print(f"  {'would install' if dry_run else 'installed'} {mod.name} ({n} file(s) "
                          f"{'to copy' if dry_run else 'copied'})", flush=True)
                    if game == "mania":
                        cfg = mods / "modconfig.ini"
                        old = cfg.read_text(newline="") if cfg.is_file() else None
                        new = enable(old, mod.name)
                        if new != old and not dry_run:
                            cfg.write_text(new, newline="")
                        print(f"  {'would enable' if dry_run else 'enabled'} it in {cfg}")
                except OSError as e:
                    print(f"  {mod.name}: install failed: {e}", file=sys.stderr)
                    status = max(status, DEPLOY_FAILED)
        note = _core_note(mods, game)
        if note:
            print(note)
    procs = deploy.running()
    for game in ("origins", "mania"):
        if not (origins if game == "origins" else mania):
            continue
        for p in deploy.running_at(procs, game, t[game]["path"]):
            print(f"warning: {p['name']} is running from that folder (pid {p['pid']}): {deploy.RESTART}")
    return status
