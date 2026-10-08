# Notice

NoSwap: Extra Characters. Copyright (c) 2026 Superevil (https://github.com/superevil6/sonic-noswap).

## What licence covers what

| Part | Licence |
|---|---|
| Everything not listed below: `tools/`, `docs/`, `data/`, `native/src/`, `native/lockon/`, `native/*.sh`, `testmods/` configs and notes, `mods/` hand-written files | [CC BY-NC-SA 4.0](LICENSE) |
| `native/mania/` and `tools/rsdk5_extract.py` | CC BY-NC-SA 4.0 **and** the Sonic Mania / RSDKv5 decompilation licences ([native/mania/LICENSE-DECOMP.md](native/mania/LICENSE-DECOMP.md)) |
| `native/third_party/minhook/` | BSD 2-Clause ([its LICENSE.txt](native/third_party/minhook/LICENSE.txt)), (c) Tsuda Kageyu and contributors |
| `native/third_party/HiteModLoader/` | MIT ([its LICENSE.md](native/third_party/HiteModLoader/LICENSE.md)), hedge-dev |
| `native/third_party/reference/` | MIT ([its LICENSE](native/third_party/reference/LICENSE)), (c) SuperSonic16 (thesupersonic16/DllMods) |
| `docs/origins-character-select.wiki` / `.md` | Also published on HedgeDocs under CC BY-SA 4.0 |

`native/third_party/` is vendored so the repository builds as is; `native/fetch_deps.sh` fetches the same files again.
Not included: the Sonic Mania decompilation's `Player.c` / `Player.h` (kept only as a local reading reference; get them
from the decompilation itself) and RSDKv5-GameAPI (point `GAMEAPI_DIR` at your own checkout).

## Attribution

When you share NoSwap or something made from it, credit "NoSwap by Superevil" with a link to this repository, keep
this notice and the licence files, and keep the artists' credits (CREDITS.md) for any character you ship.

## Not covered: game files, sprites and sounds

This repository contains no game files. Sonic the Hedgehog, Sonic Origins, Sonic Mania and their characters, art,
sounds and data are (c) SEGA; the build reads them from your own copies and never redistributes them. The guest
characters belong to their owners (CREDITS.md).

The sprite sheets and sounds characters are built from belong to their artists and rippers, under each sheet's own
terms (each character's `SOURCE.txt`). They are not in this repository and are not covered by its licence.

The "non-commercial" terms apply to everything here: NoSwap must never be sold or used to make money.
