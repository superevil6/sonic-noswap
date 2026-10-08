#!/usr/bin/env python3
"""noswap: the NoSwap character tool (docs/toolset-cli.md).

    noswap.py check   <folder>              validate a character (character.json or an old make_configs.py one)
    noswap.py preview <folder> [--anim NAME] [--out FILE]   render its frames and animations as PNGs (no game needed)
    noswap.py build   <folder> [--games s1,s2,cd,s3k,mania]  build it for Origins and/or Mania
    noswap.py convert <folder>              turn an old make_configs.py character into a character.json, proven identical
    noswap.py deploy [--origins] [--mania] [--dry-run]   copy the built mods into the games (folders: --show)
    noswap.py ui [folder]                   the character editor (a window, or the browser): docs/toolset-ui.md

<folder> is a path, or a folder name under testmods/. Works from any directory. Run `noswap.py <command> -h` for more.
Exit codes: 0 fine, 1 the character has errors (or a conversion isn't identical), 2 bad usage, 3 a build step failed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from noswap_cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
