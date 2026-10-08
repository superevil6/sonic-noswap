#!/usr/bin/env python3
"""Write every character's build configs (<id>.json, <id>_s2.json) on a fresh checkout, before the first build.

The configs are generated, so they aren't in the repository: each character folder in testmods/ has a character.json
(tools/character_json.py writes its configs) or a make_configs.py (run as it is). Both read the character's sprite
sheet, so download the sheets first (testmods/SHEETS.md). tools/extras.py reads each character's palette from these
configs; until they exist it loads with empty palettes (extras.CONFIGS_MISSING), so the scripts below can import it.

Usage: write_configs.py [folder name ...]   (no names: every character folder; a folder whose sheet is missing is
                                             reported and skipped)
Then: tools/build_art.py (art for every game), then tools/build_all.sh.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TESTMODS = REPO / "testmods"


def folders(picks):
    out = []
    for d in sorted(TESTMODS.iterdir()):
        if not d.is_dir() or d.name.startswith(("_", ".")):
            continue
        if picks and d.name not in picks:
            continue
        if (d / "make_configs.py").exists() or (d / "character.json").exists():
            out.append(d)
    return out


def main():
    picks = set(sys.argv[1:])
    failed = []
    for d in folders(picks):
        if (d / "make_sheet.py").exists():  # (a working sheet put together from the downloaded ones: Gilius)
            r = subprocess.run([sys.executable, str(d / "make_sheet.py")], cwd=REPO, capture_output=True, text=True)
            if r.returncode:
                failed.append(d.name)
                print(f"{d.name}: make_sheet.py FAILED ({(r.stderr.strip().splitlines() or ['?'])[-1]})", file=sys.stderr)
                continue
        if (d / "make_configs.py").exists():
            cmd = [sys.executable, str(d / "make_configs.py")]
        else:
            cmd = [sys.executable, "-c", "import sys; sys.path.insert(0, 'tools'); import character_json; "
                   f"character_json.write_configs(__import__('pathlib').Path({str(d)!r}))"]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode:
            last = (r.stderr.strip().splitlines() or ["?"])[-1]
            failed.append(d.name)
            print(f"{d.name}: FAILED ({last})", file=sys.stderr)
        else:
            print(f"{d.name}: configs written")
    if failed:
        sys.exit(f"{len(failed)} character(s) failed: {', '.join(failed)} (is the sheet in place? see testmods/SHEETS.md)")


if __name__ == "__main__":
    main()
