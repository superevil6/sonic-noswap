# Credits

**NoSwap Creator Kit:** Superevil (NoSwap), made with AI assistance (Claude).

## Built on

- **The RSDKv5 decompilation** by **Rubberduckycooly** and **chuliRMG** (and the Sonic Mania decompilation's contributors):
  the kit's reader for the games' data packs (`app/tools/rsdk5_extract.py`) is a port of its datapack reading and
  decryption; NoSwap Mania runs on the Sonic Mania decompilation.
- **RSDKv5Extract**: its list of Sonic Mania's file names, used to find the files the kit takes from your `Data.rsdk`.
- **The Retro Engine script decompilations** (the RSDKv4 / RSDKv3 Script Decompilation communities): the game scripts
  HedgeModManager installs, which the kit's build reads from your Origins folder and builds your character's scripts
  from.
- **HedgeModManager and HiteModLoader** by **hedge-dev**: how NoSwap and your characters load in Sonic Origins.

## Art the kit carries

- **"Sonic 1 Title Card / HUD / General Font (Expanded)"** by **Rayan C. (Rayan64_C)**, The Spriters Resource
  (https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/493842/): the letters for typed HUD name
  tags. Its note: "Credit on the custom sprites not required, but appreciated."

Art the kit uses but does not carry (taken from your own games at Set up): Sonic Mania's plain spin ball (the generic
`"ball"`) and the games' own HUD sheets, by SEGA / Sonic Team.

## The example

- **Bean the Dynamite** (Sonic 1 style) custom sprites by **deltaConduit**; original sprites by SEGA, Sonic Team and
  deltaConduit (https://www.spriters-resource.com/custom_edited/sonicthehedgehogcustoms/asset/263920/). The sheet isn't in
  the kit; `example/bean/character.json` is NoSwap's configuration for it.

## Programs inside

Python (PSF), Pillow, NumPy, PyInstaller; on Windows also pywebview, pythonnet, clr_loader, bottle and proxy_tools. Their
licences are in `licenses/`.

## The games

Sonic the Hedgehog, Sonic CD, Sonic the Hedgehog 2, Sonic 3 & Knuckles, Sonic Origins, Sonic Mania and their
characters (including Bean the Dynamite) © SEGA. Unofficial fan tool; not affiliated with or endorsed by SEGA.
