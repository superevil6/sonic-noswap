#!/usr/bin/env python3
"""Writes Fang's sheet2ani configs (fang.json for Sonic 1, fang_s2.json for Sonic 2) from the character.json
(docs/character-json.md, tools/character_json.py). Everything about the character lives in character.json; this file only
keeps build_art.py's "run the folder's make_configs.py" step working. The hand-written version it replaced is
make_configs.legacy.py (byte-identical output; converted by tools/noswap.py convert).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import character_json  # noqa: E402

if __name__ == "__main__":
    character_json.write_configs(HERE)
