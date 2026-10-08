# Installing NoSwap: Extra Characters

NoSwap comes in pieces: the **core** (required) and **one mod per character**. Grab the core, then whichever
characters you want. You can add or remove characters any time.

## What you need

- Sonic Origins on PC (Steam).
- [HedgeModManager](https://github.com/hedge-dev/HedgeModManager) 8 or newer, set up for Sonic Origins.
- Tested with Sonic Origins Plus.
- **Not compatible with Sonic Origins Ultrafix (yet).** Both mods replace many of the same game scripts, so running them together crashes. Disable Ultrafix while playing NoSwap. Other mods that replace the player, enemy or monitor scripts may clash the same way.

## Install

1. **The core first.** In HedgeModManager, install `NoSwap-<version>.zip` (or unzip it into the game's `mods`
   folder, so you get `mods/NoSwap/mod.ini`).
2. **Then any characters.** Install each `NoSwap-<Name>-<version>.zip` the same way (for example
   `mods/NoSwap-MetalSonic/`).
3. In HedgeModManager, tick **NoSwap** and every character you want, then click **Save & Play**.

Keep the core and all characters on the **same version**. When you update the core, update your characters too.

A character on its own does nothing: it only shows up when the NoSwap core is enabled too.

## Playing

- **Sonic 1, Sonic 2 and Sonic CD:** your characters are in Origins' own character select, after Sonic, Tails,
  Knuckles and Amy. Scroll right past the last card to see them all. Pick one to play, or press **Y** on a card
  to start that character in the level select.
- **Sonic 3 & Knuckles:** on the game's save screen, press **up/down** on a save slot to pick its character.

Each character's moves are in the README inside its mod folder.

## Saves

Origins' own save file is never changed. NoSwap keeps its own:

- `%APPDATA%\SEGA\SonicOrigins\NoSwap\extras.sav`: the extra characters' saves and progress.
- `%APPDATA%\SEGA\SonicOrigins\NoSwap\roster.json`: which menu slot each character has.
- `mods\NoSwap\NoSwapS3K.ini`: your settings and which character each Sonic 3 & Knuckles save slot uses. When you
  update the core by hand, keep this file.

## Removing a character

Untick it in HedgeModManager (or delete its `NoSwap-<Name>` folder) and start the game. Its card simply goes away.

Its saves are **kept aside, not deleted**: reinstall the character later and its progress comes back. Everyone
else keeps their saves and their menu slots.

## Uninstalling NoSwap

Untick (or delete) the core and every NoSwap character. Your Origins saves are untouched. If you want NoSwap's
saves gone too, delete the `%APPDATA%\SEGA\SonicOrigins\NoSwap` folder, but only if you're sure.

## If something looks wrong

- Other mods that change the same game scripts or Origins' menu files may clash with NoSwap. Try NoSwap on its own.
- The first start after adding or removing characters takes a little longer: NoSwap rebuilds its menu copies
  (about 120 MB in `mods\NoSwap\cache`). That folder is safe to delete; it's rebuilt at the next start.
