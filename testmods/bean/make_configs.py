#!/usr/bin/env python3
"""Writes Bean the Dynamite's sheet2ani configs (bean.json for Sonic 1, bean_s2.json for Sonic 2) from his character.json
(docs/character-json.md, tools/character_json.py). Everything about him lives in character.json; this file only
keeps build_art.py's "run the folder's make_configs.py" step working. The hand-written version it replaced is
make_configs.legacy.py (byte-identical output).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
import character_json  # noqa: E402

if __name__ == "__main__":
    character_json.write_configs(HERE)
