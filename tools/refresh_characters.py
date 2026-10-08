#!/usr/bin/env python3
"""Bring character.json characters' configs and built art up to date before a full build (tools/build_all.sh runs it first).

A character.json edited since its configs (<id>.json, <id>_s2.json) were written, e.g. in the editor, would otherwise
build with stale configs: the game builders read those, and a changed "ball" or "flags" then stops the build halfway
("roll needs a Rolling animation"). For each such character: write its configs, then rebuild its art (build_art.py).
Up-to-date characters are left alone, so their outputs don't change.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import character_json  # noqa: E402


def stale(folder, extras):
    """The character's id when its configs or its built art (the S1 and S2 player .ani in the character's build
    folder) are missing or older than its character.json / sheet, else None."""
    c = character_json.load(folder)
    outputs = [folder / f"{c['id']}.json", folder / f"{c['id']}_s2.json"]
    extra = next((e for e in extras.EXTRAS if Path(e["art"]).resolve() == folder.resolve()), None)
    if extra:
        outputs += [extras.player_ani_path(extra, game) for game in ("Sonic1", "Sonic2")]
    if not all(p.exists() for p in outputs):
        return c["id"]
    sources = [folder / character_json.FILE, folder / c["sheet"]["file"]]
    newest = max(p.stat().st_mtime for p in sources if p.exists())
    return c["id"] if newest > min(p.stat().st_mtime for p in outputs) else None


def main():
    import extras
    for folder in character_json.folders():
        cid = stale(folder, extras)
        if not cid:
            continue
        print(f"{cid}: character.json changed since its configs: rewriting them and rebuilding its art")
        character_json.write_configs(folder)
        result = subprocess.run([sys.executable, str(REPO / "tools" / "build_art.py"), cid], cwd=REPO)
        if result.returncode:
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
