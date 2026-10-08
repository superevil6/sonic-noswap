#!/usr/bin/env python3
"""Rebuild extras' art for every game, from their sheets.

Usage: build_art.py <extra number or art folder name> ...   (e.g. build_art.py 6 silver; no arguments = all)

For each extra: its make_configs.py (the Sonic 1 and Sonic 2 configs), cd_config.py (the CD config, from the
Sonic 2 one), sheet2ani.py on all three, and build_s3k_art.py (Sonic 3 & Knuckles, from the Sonic 2 config).
The game scripts don't need rebuilding for art alone; run the game builds when abilities change.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from extras import EXTRAS, stash_player_art, stash_special_ani  # noqa: E402


def run(*args):
    result = subprocess.run([sys.executable, *map(str, args)], cwd=REPO, capture_output=True, text=True)
    if result.returncode:
        sys.exit(f"{' '.join(map(str, args))} failed:\n{result.stdout}{result.stderr}")


def build(extra):
    art = extra["art"]
    if (art / "make_configs.py").exists():  # (Metal's configs are written by hand)
        run(art / "make_configs.py")
    s2 = [p for p in art.glob("*_s2.json")]
    if len(s2) != 1:
        sys.exit(f"{art.name}: expected one Sonic 2 config, found {len(s2)}")
    run(REPO / "tools" / "cd_config.py", s2[0])
    stem = s2[0].name[:-len("_s2.json")]
    for config in (art / f"{stem}.json", s2[0]):  # (numbers are by place in EXTRAS: see extras.private_extras)
        name = json.loads(config.read_text())["name"]
        if name != extra["file"]:
            sys.exit(f"{config}: its name is {name}, but this extra is {extra['file']} (extra {extra['n']})")
    for config in (art / f"{stem}.json", s2[0], art / f"{stem}_cd.json"):
        run(REPO / "tools" / "sheet2ani.py", config)
    stash_special_ani(extra)  # (the Sonic 1 special stage .ani: its package ships it, NoSwap doesn't)
    stash_player_art(extra)  # (its S1/S2/CD player .ani and sheets: its package ships them under fixed names)
    run(REPO / "tools" / "build_s3k_art.py", s2[0])
    print(f"extra {extra['n']} ({art.name}): art rebuilt for all four games")


def main():
    picks = sys.argv[1:]
    for e in EXTRAS:
        if not picks or str(e["n"]) in picks or e["art"].name in picks:
            build(e)


if __name__ == "__main__":
    main()
