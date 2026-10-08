#!/usr/bin/env python3
"""Pull sound effects out of Sonic Origins' own sound banks into the Mania mod (the user, 2026-10-01: Amy's hammer
sounds, "We're pulling over graphics so I think it's fair game").

Origins plays the classic games' sounds through CRI ADX2 banks (image/x64/raw/sound/STH3_sfx.acb for S3&K: HCA streams
named like "SFX_Plus_AM1_Hammer-Jump"), not from the .rsdk data packs. vgmstream-cli (installed by the user) decodes
them; ffmpeg converts to Mania's own sound format (16-bit PCM, mono, 44.1 kHz, as Data/SoundFX/Global/Jump.wav is).

    python3 tools/origins_sfx.py            (every entry of SOUNDS)
Output: mods/NoSwapMania/Data/SoundFX/<path> (the mod loader serves them as Data/SoundFX/<path>).
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ORIGINS = Path(os.environ.get("ORIGINS_DIR", str(Path.home()) + "/.local/share/Steam/steamapps/common/SonicOrigins"))
BANKS = ORIGINS / "image" / "x64" / "raw" / "sound"
OUT = REPO / "mods" / "NoSwapMania" / "Data" / "SoundFX"

# Mania path (as Origins names it in its code) -> (bank, stream name in the bank)
SOUNDS = {
    "Global/HammerJump.wav": ("STH3_sfx.acb", "SFX_Plus_AM1_Hammer-Jump"),
    "Global/HammerDash.wav": ("STH3_sfx.acb", "SFX_Plus_AM2_Hammer-Attack"),
    "Global/HammerHit.wav": ("STH3_sfx.acb", "SFX_Plus_AM3_Hammer-Hit"),
    "Global/HammerThrow.wav": ("STH3_sfx.acb", "SFX_Plus_AM4_Hammer-Throw"),
}


def stream_index(bank, name):
    """The 1-based stream number of `name` in a bank (vgmstream-cli -m per stream)."""
    head = subprocess.run(["vgmstream-cli", "-m", str(bank)], capture_output=True, text=True).stdout
    count = int(next(l.split(":")[1] for l in head.splitlines() if l.startswith("stream count")))
    for i in range(1, count + 1):
        meta = subprocess.run(["vgmstream-cli", "-m", "-s", str(i), str(bank)], capture_output=True, text=True).stdout
        if any(l.startswith("stream name:") and l.split(":", 1)[1].strip() == name for l in meta.splitlines()):
            return i
    sys.exit(f"{bank.name}: no stream {name!r}")


def main():
    for path, (bank_name, stream) in SOUNDS.items():
        bank = BANKS / bank_name
        i = stream_index(bank, stream)
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.wav"
            subprocess.run(["vgmstream-cli", "-s", str(i), "-o", str(raw), str(bank)], check=True, capture_output=True)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-ac", "1", "-ar", "44100", "-c:a",
                            "pcm_s16le", str(dest)], check=True)
        print(f"{path} <- {bank_name} #{i} {stream}")


if __name__ == "__main__":
    main()
