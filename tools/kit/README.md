# NoSwap Creator Kit {VERSION} (preview)

Make your own playable character for **NoSwap**, from your own sprite sheet, and build it for **Sonic Origins**
(Sonic 1, Sonic CD, Sonic 2, Sonic 3 & Knuckles) and **Sonic Mania** (the decompilation). It's the same editor and the
same build the NoSwap characters are made with, packed as a program: no Python, no repository, nothing else to install.

This is a **preview**: it works, but expect rough edges. It is the same tool in both NoSwap Sonic Hacking Contest entries
(Origins and Mania).

**It contains no game files.** The first time, the kit reads what its build needs from *your own* copies of the games
(Set up, below) into its data folder. Your games are only read, never changed.

## What you need

- **Windows 10 or 11** (64-bit), or **Linux** (x86-64).
- **Sonic Origins** (Steam) with [HedgeModManager](https://github.com/hedge-dev/HedgeModManager) 8 or newer and the
  **NoSwap core mod, version {CORE}**, installed and enabled. Start the game once with NoSwap enabled: HedgeModManager
  then puts the decompiled game scripts in the game folder, which the kit's build reads.
- Optional, for Mania: **Sonic Mania Plus** (its `Data.rsdk`), the **Sonic Mania decompilation**, and the
  **NoSwap Mania mod, version {MANIA}**.
- A sprite sheet you're allowed to use: your own art, or a sheet whose artist allows it. Credit them, and follow their terms.

Characters you build are for the NoSwap core {CORE} (Origins) and NoSwap Mania {MANIA}. When NoSwap updates, get the
matching kit and press Build again: your `character.json` carries over as it is.

## Getting started

1. **Unzip** the whole kit folder anywhere, and start it:
   - **Windows:** `NoSwapCreator.exe`. The editor opens in its own window (it uses Microsoft Edge WebView2, which
     Windows 11 and an up-to-date Windows 10 have; without it, the editor opens in your web browser instead). Windows
     may warn about an unknown program the first time ("More info", "Run anyway"): the kit isn't signed. A console
     window shows what it's doing; closing it closes the editor.
   - **Linux:** `./NoSwapCreator.sh` (or `./NoSwapCreator`). The editor opens in your web browser; stop it with Ctrl+C
     in the terminal.
   - Either: `NoSwapCreator --browser` opens it in your browser; `--no-open` only prints the address.
2. **Set up** (Settings tab, first time only and after a game update): pick Sonic Origins' folder (the game's own
   folder, with `image/` and `build/` in it; usually found by itself, Steam libraries on other drives too) and, if you
   have it, a folder with Sonic Mania's `Data.rsdk`, then press **Set up**. It takes about ten seconds. That's the only
   folder setting: Deploy installs into the mods folder of the same Sonic Origins.

   ![Set up](screenshots/settings-setup.png)

3. **Make a character:** first look at `docs/roster.md`, the characters NoSwap already has, and pick a different one
   (or at least a different name). **New…** and pick your sprite sheet: the kit makes a folder for it with a copy of
   the sheet and a `character.json` in your characters folder (in the data folder: "Where things are", below). Or start
   from the example (below).
4. **Draw it in:**
   - **Sheet & frames:** *Detect frames* finds the sprites on the sheet; name the ones you use. Move, resize and fit
     boxes by hand where needed. If the sheet draws a box around each sprite, the box colour goes into the sheet's
     background (accepting detected frames does it).

     ![Sheet & frames](screenshots/sheet.png)

   - **Animations:** put frames in each animation (walk, run, jump...), with the onion skin and a live preview.

     ![Animations](screenshots/animations.png)

   - **Abilities:** pick moves from NoSwap's list (`docs/abilities.md`: what each does, its fields and which games have
     it). On a Tails or Knuckles base the jump button stays their flight or glide, so moves started by pressing jump
     again need base Sonic (`docs/character-json.md` explains).

     ![Abilities](screenshots/abilities.png)

   - **Palette:** *Fill from sheet* gives each of your colours a slot.
   - **HUD & ending:** life icon, name tag, 1-UP monitor, signpost face, the two small foot-tapping icons (`mini_1`,
     `mini_2`: the continue screen) and Sonic 1's ending poses. `docs/character-json.md` shows where each one appears.
   - The **Check** panel on the right lists what's missing or wrong, with the fix.
5. **Build** (Build & deploy tab): tick the games, press **Build**. It checks the character, then builds it for every
   Origins game, and for Mania if your `character.json` enables it. What to install lands in
   `output/<your character>/` in the data folder: a mod folder and a zip for each game.

   ![Build](screenshots/build.png)

6. **Deploy** installs the character into your games, each as its own mod beside the NoSwap core: into the mods folder
   of the Sonic Origins you set up (enable it in HedgeModManager), and into the Sonic Mania decompilation's mods folder
   (enabled for you). Nothing else to set; the Settings tab can point Deploy somewhere else. Restart the game if it was
   running. Pick your character on Origins' character select (or Mania's save select).

## Sharing your character

The zips in `output/<your character>/` are ready to share: `NoSwap-<Name>-Origins-{CORE}.zip` installs like any NoSwap
character (HedgeModManager's install, or copy the folder into the mods folder), next to the NoSwap core {CORE};
`NoSwap-<Name>-Mania-{MANIA}.zip` goes into the decompilation's mods folder next to NoSwap Mania {MANIA}. Each has a README
with the sprite credit from your `character.json`.

- **Credit the sprite artist** (`credits` in `character.json`) and follow the sheet's terms. If the terms say "no edits",
  only crop: the check warns about flips, turns and layered frames.
- A character's key (`"key": "<you>.<character>"`, e.g. `"someone.knuckles-classic"`) is what saves and picks are stored
  under: choose it once and never change it after you share.
- Like every NoSwap character, the package holds copies of a few of the games' HUD sheets with your art in its boxes.
  NoSwap is a non-commercial fan mod: keep your character free.

## The example: Bean the Dynamite

`example/bean/character.json` is NoSwap's own Bean, complete: frames, animations, moves, HUD and ending. His sheet isn't
in the kit (its artist's terms are credit, no edits; get it from its page): see `example/bean/README.md`. Copy the `bean`
folder into your characters folder, add the sheet, then Open it in the editor. Bean is NoSwap's: make your own
character with its own name and key rather than sharing a copy of him.

## The command line

The program is also the command line: `NoSwapCreator <command>` (Windows: `NoSwapCreator.exe <command>`, from the
kit's folder). `NoSwapCreator help` lists the commands, `NoSwapCreator help <command>` explains one.

```
NoSwapCreator setup --origins "<Sonic Origins folder>" --mania "<folder with Data.rsdk>"
NoSwapCreator setup                      # what's set up
NoSwapCreator detect <character>         # find the sprites on the sheet: frame rectangles to paste
NoSwapCreator check <character>          # validate (-v: notes too)
NoSwapCreator preview <character>        # PNG previews of every animation (into previews/ in the data folder)
NoSwapCreator build <character>          # build (--games s1,s2,cd,s3k,mania)
NoSwapCreator deploy [--character <character>] [--origins] [--mania] [--dry-run]
NoSwapCreator deploy --show              # where Deploy installs, and why
NoSwapCreator abilities [move]           # the move list, or one move in full
NoSwapCreator ui [<character>]           # the editor (the same as starting the program)
NoSwapCreator --data <folder> ...        # another data folder
```

`<character>` is a folder name in your characters folder, or a path. `detect` only reads: it prints the frames it finds
(and the cell-box colour to add to the background, if the sheet has boxes) for you to paste into `"frames"`. There's
also `convert`, which turns NoSwap's own older characters (made with Python scripts) into a `character.json`: kit
characters never need it.

## Guides

- `docs/character-json.md`: the character file, field by field.
- `docs/abilities.md`: every move: what it does, its fields, the animation slots to draw, and which games have it.
- `docs/toolset-ui.md`: the editor, tab by tab.
- `docs/roster.md`: the characters NoSwap already has.

## Limits (preview)

- New moves are NoSwap core work: the kit offers the moves NoSwap has (all of them, flagged per game).
- A few things NoSwap's own characters do aren't in `character.json` yet (layered frames, hand-drawn card pictures,
  game-specific animations).
- Your character's HUD art must fit NoSwap's boxes (the check and the build say so if not): life icon 16x16, 1-UP
  monitor 16x14, signpost face up to 48x32, name tag 72x7.
- On Linux the editor runs in your browser (no window of its own).
- Sonic Mania needs Set up with Sonic Mania's data; without it, build for Origins only (untick Mania). The generic spin
  ball (`"ball"`) also needs it.

## Where things are

- **The kit folder:** the program and its tools (`app/`). Replace it whole to update.
- **The data folder:** `Documents\NoSwap Creator Kit` (Windows); `~/Documents/NoSwap Creator Kit` (Linux), or
  `~/NoSwap Creator Kit` when there is no `~/Documents`. The first run prints where it is, and `NoSwapCreator setup`
  says it again. `--data <folder>` or the `NOSWAP_KIT_DATA` environment variable picks another place. In it:
  - `characters/`: your characters, one folder each;
  - `output/`: what Build makes to install and share;
  - `previews/`: what `preview` draws; `backups/`: the editor's backups and unsaved edits;
  - the kit's working files: the game files from Set up (`extracted/`), the build's work folder (`mods/`), and a copy
    of the kit's tools.
- **Settings:** Set up's game folders are in the data folder (`kit-setup.json`). Only if you point Deploy somewhere
  else: `%APPDATA%\noswap\settings.json` (Windows), `~/.config/noswap/settings.json` (Linux).

To uninstall, delete the kit folder and the data folder (keep `characters/` if you want your work).

## Credits and licence

See `CREDITS.md` and `LICENSE.txt`. Sonic the Hedgehog, Sonic Origins and Sonic Mania © SEGA. This is an unofficial
fan tool, not affiliated with or endorsed by SEGA. It was made with AI assistance (Claude), disclosed as in NoSwap's
contest entries.
