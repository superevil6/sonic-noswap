# Mania Lock-On

A Sonic Origins mod (HedgeModManager) that adds a **SONIC MANIA** button to Origins' main menu, in the
Museum / My Data / Options island. Picking it starts your own copy of the Sonic Mania decompilation. Origins
minimises while you play, and it comes back when you quit Mania.

It works with or without NoSwap.

## What you need

- Sonic Origins (Steam) and HedgeModManager.
- **Sonic Mania**, your own copy (Steam). Its `Data.rsdk` holds the game's data.
- **A Windows build of the Sonic Mania decompilation** (RSDKv5): `RSDKv5U.exe` and `Game.dll`. Use an official
  release of the decompilation or build it yourself. Copy it into your Sonic Mania folder, next to `Data.rsdk`.

Neither the game nor the decompilation comes with this mod. The decompilation's own `Settings.ini` (Plus, window
size, mods) applies as usual.

## Install

1. Extract the `ManiaLockOn` folder into Origins' `mods` folder, or install the zip with HedgeModManager.
2. Enable **Mania Lock-On** in HedgeModManager.
3. If you use NoSwap too, keep NoSwap **above** Mania Lock-On in the mod list.

## Configure

In HedgeModManager, select Mania Lock-On and click **Configure**:

- **SONIC MANIA button**: on or off.
- **Decompilation folder**: the folder with `RSDKv5U.exe`, `Game.dll` and `Data.rsdk`. You can also give the
  full path of `RSDKv5U.exe`. On Linux (Proton) a normal Linux path works, for example `/home/you/Games/Mania`.
  Leave it empty and the mod looks in Steam's Sonic Mania folder, in every Steam library.

If neither place has the decompilation, the button stays hidden. `ManiaLockOn.log` in the mod's folder lists every
place the mod looked and why each one didn't work.

Upgrading from a NoSwap that had the button: while the folder setting is empty, the mod still reads the
`[Mania] Path` from your old `NoSwapS3K.ini`.

## How it works

- The button needs a small layout and text addition in Origins' menu archives. The mod doesn't ship the game's
  files. It ships only the differences (`patches/`). On the first start it rebuilds the archives from your own game
  files into its `raw/` folder, after checking that they match. After a game update that changes them, the button
  turns itself off until the mod is updated.
- With NoSwap installed, NoSwap's menu archives already carry the button, so Lock-On uses those.
- If another mod replaces those menu archives without the button, or the game build is a different one, the button
  stays off and the island looks as it always did.
- An older NoSwap that still has its own SONIC MANIA button wins over Lock-On. Update NoSwap to use Lock-On's
  settings.

## Credits

- **Sonic Mania decompilation (RSDKv5):** Rubberduckycooly, chuliRMG and Evening Star. This mod only starts it.
  It contains none of its code.
- **Sonic Origins and Sonic Mania:** SEGA / Sonic Team. You need your own copies.
- MinHook (Tsuda Kageyu, BSD 2-clause) for the hooks.
- Mod by Superevil.
