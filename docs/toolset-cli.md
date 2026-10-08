# The `noswap` command line

`tools/noswap.py` is one command over NoSwap's Python pipeline. It checks a character, previews it, builds it and
converts old characters to `character.json` (docs/character-json.md). It works from any directory. A character is a
folder: give its path, or just its name if it's under `testmods/`.

```
python3 tools/noswap.py check   <folder>... [-v] [--strict]
python3 tools/noswap.py preview <folder> [--anim NAME] [--out FILE|DIR] [--scale 3] [--raw]
python3 tools/noswap.py detect  <folder> [--merge 3] [--min-size 3] [--region X,Y,W,H] [--all] [--json]
python3 tools/noswap.py build   <folder> [--games s1,s2,cd,s3k,mania] [--dry-run] [--no-check] [--lock FILE]
python3 tools/noswap.py convert <folder> [--wire] [--force] [--unwire]
python3 tools/noswap.py abilities [name] [--game s1|s2|cd|s3k|mania] [--json]
python3 tools/noswap.py deploy [--origins] [--mania] [--dry-run] [--show] [--set-origins DIR] [--set-mania DIR]
python3 tools/noswap.py ui [folder] [--browser]      # the character editor: docs/toolset-ui.md
```

Exit codes:

| code | meaning |
|---|---|
| 0 | fine |
| 1 | the character has errors, or a conversion isn't identical (deploy: a game's folder isn't set up) |
| 2 | bad usage (an unknown folder or game) |
| 3 | a build step failed (deploy: copying failed) |

## check

`check` validates everything it can without building. Each finding is an **error** (the build would fail or the game
would be wrong), a **warning** (it builds, but probably isn't what you meant) or a **note** (shown with `-v`). Each one
names the place and, where it can, the fix.

- **Schema:** `character.json` is validated against `docs/character.schema.json` (JSON Schema 2020-12). The tool has a
  small validator of its own, so no package is needed. Editors that understand JSON Schema can use the file too.
  The checks include:
  - the id matches the folder;
  - the flags are known and don't conflict;
  - no Origins game is switched off.
- **Frames:**
  - every rect is inside the sheet;
  - every frame name used is defined (with a "did you mean" suggestion);
  - no frame is empty (all background), since the build would stop on it;
  - every frame fits a 256x256 sheet, and its pivot fits the .ani's -128..127;
  - unused frames are listed;
  - how many sprite sheets the character takes.
- **Animations:**
  - every name is on the base character's list for Sonic 1 / Sonic 2. Sonic CD's own names (`3D Ramp 1-7`,
    `Spinning Top`, ...) are allowed in `animations_sonic2`. An unknown name would be silently ignored by the build;
  - every animation the base character has frames for is filled;
  - loop points are inside the animation;
  - ability slots are valid and named;
  - the Sonic 1 special stage and the S3&K act clear are present.
- **UI:**
  - all six HUD elements and the ending poses are present and inside the sheet;
  - the life icon is 16x16, the 1-UP monitor 16x14 and the signpost board at most 48x32;
  - the medium ending pose is at most 71 px wide.
- **Palette, per game:**
  - own slots are 74-95, the extras' free slots in Origins S1/S2/CD; S3&K's DLL writes the same slots;
  - no colour is both background and an own colour;
  - with `strict`, every frame colour has a slot;
  - every frame colour the game would draw differently (merged into a nearby colour). That's a warning when the
    sheet's terms forbid edits. The faithful art rule allows no recolours;
  - Mania: how many own colours need its 13 free slots. Past 13, the rarest go to the nearest global colour, the
    approved exception.
- **Moves**, against the ability registry (`tools/abilities_registry.py`, docs/abilities.md):
  - every move is one NoSwap has. The list is read from `tools/abilities.py`, so it never goes stale; a setting
    (`shot`, `float_lean`, ...) put in the list is flagged;
  - every field is one some code reads (a typo does nothing, so it's flagged), and belongs to a move he has;
  - field types match the other characters';
  - each move's animation slots have frames (for example, `aim_dash` needs 41, 45 and 46);
  - each move works in each game he's built for (Mania only when he's Mania-enabled); one that doesn't is a
    warning, a partial one a note;
  - the rules on combining moves (docs/abilities.md "Combining moves"): an error where the build would stop, a
    warning where a move would silently not work;
  - the S3&K field generator's limits;
  - the shot's art is inside its sheet.
- **Credits:**
  - the full credit, artists, URL and terms are present;
  - the card line fits (about 32 characters, 40 at most);
  - if the terms say "do not edit", frames that are layered, turned or mirrored are flagged.
- **Registration:** whether `tools/extras.py` knows the character, and his number, build ID and key.

Old `make_configs.py` characters get every check that applies. They're read from the configs their
`make_configs.py` last wrote (`<id>.json`, `<id>_s2.json`), plus their `extras.py` and `abilities.py` entries.

```
$ python3 tools/noswap.py check espio vector fang
$ python3 tools/noswap.py check -v bean           # with the notes
```

## abilities

`abilities` lists every move a character can have, with the games it works in; `abilities <name>` describes one in
full: what the player does, its fields (unit, value if left out, an example), the animation slots to draw (and their
numbers in CD and S3&K), the rules on combining it, and a working example from a character that has it. `--game`
lists only the moves that work in one game; `--json` prints the registry entry.

The registry is `tools/abilities_registry.py`. The words (names, descriptions, field meanings) are hand-written in
`tools/abilities_text.py`; the rest is read from the code: per-game support from the S1/S2 and CD generators, the
S3&K fields the DLL reads and the Mania mod's MOVES_DONE; defaults from the builders' `.get()` calls; examples from the
existing characters; the combining rules from the builders' own checks. `python3 tools/abilities_registry.py --write`
regenerates docs/abilities.md and docs/abilities.json; `--check` reports a move or field nobody described, or stale
docs.

```
$ python3 tools/noswap.py abilities
$ python3 tools/noswap.py abilities "rocket ride"
$ python3 tools/noswap.py abilities --game mania
```

## preview

`preview` draws a character's frames as PNGs, enlarged 3x, without the game:

- `<id>-animations.png`: one labelled row per animation. The order is Sonic 2's list, then Sonic 1-only ones, the
  ability slots, the special stage and the S3&K act clear. Each frame stands where the game puts it: on the ground
  line (green) for `feet`, or centred for `center`. The red cross is the object's position.
- `<id>-frames.png`: every named frame.

Frames are cut by the build's own code (`sheet2ani.cut_frame` / `cut_spec` / `cut_layered`). They're drawn in the
game's colours, through the same colour mapping as the build, so a merged colour shows. `--raw` shows the sheet's own
colours instead. Output goes to `<temp dir>/noswap-preview/<id>/` unless `--out` says otherwise.

```
$ python3 tools/noswap.py preview bean
$ python3 tools/noswap.py preview vector --anim Walking --out /tmp/vector-walk.png
$ python3 tools/noswap.py preview fang --anim 43          # an ability slot
```

## detect

`detect` finds the sprites on a character's sheet and proposes frame rectangles, ready to paste into `"frames"`. It only
reads: nothing is written. The editor's **Detect frames** (docs/toolset-ui.md) is the same code
(`tools/noswap_cli/detect.py`).

- The background is `sheet.background` (guessed from the sheet's corners when there's none) plus fully transparent
  pixels. A colour that makes large solid boxes with drawings inside (a sheet's cells) counts as background too.
- Each piece of the remaining pixels (8-way connected) is a candidate. A small piece joins the nearest bigger body
  within `--merge` px (default 3), never across two cells: sweat drops, sparks, a detached hand, a held item. A flat
  piece one pixel from a much bigger one (motion lines under the feet) joins it too.
- Rows of three or more small glyphs on a line are **text** (labels, titles, credits; whole words too), thin rules,
  label brackets and box outlines are **lines**, and lone pieces under `--min-size` px both ways are **tiny**. They're
  listed only with `--all` (and kept in `--json`), never silently dropped.
- Boxes are trimmed tight to the pixels and listed in reading order (rows, then left to right) as ROW<row>_<n>, never
  taking an existing frame's name. A box over an existing frame's drawn part is left out (`--all` shows which).

```
$ python3 tools/noswap.py detect bean
$ python3 tools/noswap.py detect espio --merge 5 --all
$ python3 tools/noswap.py detect my-char --region 0,0,400,120 --json
```

Measured against the hand-made frames of 14 characters (957 frames): 97% are found within 2 px; most of the rest are
deliberate part-crops (a signpost face, an ending pose with its tail tips cut) or two sprites drawn touching. Known
misses: sprites touching each other come out as one box (Split them in the editor), a body split in two by a gap wider
than `--merge` comes out as two (Merge them), and a cell colour that's almost entirely covered by its sprites isn't
found as a fill (alt-click it in the editor, or add it to `sheet.background`).

## build

`build` runs the existing pipeline in the right order:

1. **Origins** (any of s1/s2/cd/s3k: the pipeline always makes all four games together):
   - if a `character.json` has no `make_configs.py` shim, `tools/character_json.py` writes its configs;
   - then `tools/build_art.py <id>` and `tools/build_all.sh`, holding the build lock.
2. **Mania:** `tools/build_mania_art.py <id>`, if he's Mania-enabled.

It runs `check` first and stops on errors (`--no-check` skips the check). `--dry-run` prints the steps. It never
deploys to the game: that's `deploy`.

The lock is `flock` on `--lock`, or `$NOSWAP_BUILD_LOCK`, or `<temp dir>/noswap-build.lock`, so two builds never
interleave. Set `NOSWAP_LOCK_HELD=1` when the caller already holds it.

A `character.json` folder needs no registration: the build finds it and the registry (`tools/registry.py`,
`data/registry.json`) gives its key a number on first use (docs/character-json.md, "Wiring"). A folder outside
`testmods/` is found through `$NOSWAP_CHARACTER_DIRS`.

```
$ NOSWAP_BUILD_LOCK=/path/to/build.lock python3 tools/noswap.py build espio
$ python3 tools/noswap.py build espio --games mania
```

## deploy

`deploy` copies what's built in `mods/` into the games. It does exactly what `tools/deploy.sh` and
`tools/deploy_mania.sh` do, in Python, so it works the same on every system:

- **Origins** (`--origins`): every folder in `mods/` except `NoSwapMania` is mirrored into HedgeModManager's mods folder
  (`<Sonic Origins>/build/main/projects/exec/mods`), as deploy.sh's `rsync -a --delete --exclude '*.log'
  --exclude 'NoSwapS3K.ini' --exclude 'cache/'`:
  - files whose size or time differ are copied, with their times and modes;
  - files that aren't in the build any more are removed;
  - the game's own files stay: logs, the DLL's `cache/` folder, and the player's `NoSwapS3K.ini`, which is installed
    only when it's missing.
- **Mania** (`--mania`): `<run>/mods/NoSwapMania` becomes a symlink to the repo's `mods/NoSwapMania` (later builds are
  live at the next start), and `<run>/mods/modconfig.ini` gets `NoSwapMania=y`; other mods' lines are left alone. A
  real folder already at `mods/NoSwapMania` is never touched. It needs the mod built first (`native/mania/build.sh`, and
  at least one package from `tools/build_mania_art.py`).
- Neither flag: both.

`--dry-run` says what would change (for Origins, the files it would copy and remove) and writes nothing. A real deploy
waits for the build lock (`--lock`, as `build`), so it never copies a half-built `mods/`.

**Where to.** The folders are kept in a small settings file of yours, never in the repo:
`~/.config/noswap/settings.json` (`$XDG_CONFIG_HOME`), `%APPDATA%\noswap\settings.json` on Windows,
`~/Library/Application Support/noswap/settings.json` on macOS; `$NOSWAP_SETTINGS` points elsewhere.

```json
{"origins_mods": "/path/to/SonicOrigins/build/main/projects/exec/mods", "mania_run": "/home/me/Code/mania/run"}
```

`--set-origins DIR` / `--set-mania DIR` save one (`""` clears it); `--show` prints both, where each came from, whether
it looks right, the other folders detection found, and whether a game is running. Unset, they're detected:

- **Origins:** Steam's libraries (each Steam install's `steamapps/libraryfolders.vdf`; on Windows the registry's Steam
  folder too); the one with `appmanifest_1794960.acf` has the game in `steamapps/common/<installdir>`. Else
  deploy.sh's default.
- **Mania:** `~/Code/mania/run` (the decomp's play folder), else Steam's Sonic Mania folder (`appmanifest_584400.acf`)
  if it holds a decomp build (as the Mania launcher looks: Mania Lock-On, native/lockon/src/Launcher.h).

What makes a folder right:
- **Origins mods:** `SonicOrigins.exe` next to it, or HedgeModManager's `ModsDB.ini` in it. It also says whether
  HedgeModManager's loader (`dinput8.dll`) is installed, and whether `ModsDB.ini` lists NoSwap and has it enabled.
- **Mania run:** the decompilation's engine (`RSDKv5U`, `RSDKv5`, or their `.exe`; Steam's `SonicMania.exe` alone
  isn't enough) and the game's data (`Data.rsdk` or `Data/`).

A folder that doesn't look right isn't deployed to (exit 1) unless `--force`.

**A running game.** Both games load the DLL / the mod and its scripts at startup, so a deploy while one runs only
takes effect at the next start. Deploy still goes ahead, and ends with `warning: Sonic Origins is running (...):
restart the game: the DLL / scripts load at startup`. Running games are found in `/proc` on Linux (Proton/Wine
processes included: `SonicOrigins.exe`, `RSDKv5U`), with `tasklist` on Windows, `ps` elsewhere.

**One character (`--character <folder>`): designed, not built.** It waits for step 5 (the public / private split),
when each character becomes its own mod. The plan: Origins mirrors only `mods/NoSwap/characters/<id>/` (then: that
character's own mod folder) and leaves the core alone; Mania copies nothing (the package is live through the symlink).
Today a package's S1/S2/CD scripts come from the core build they were made with, so a package alone could mismatch
the core in the game. `--character X --dry-run` prints the plan; a real run refuses (exit 2).

```
$ python3 tools/noswap.py deploy --show
$ python3 tools/noswap.py deploy --dry-run
$ python3 tools/noswap.py deploy --origins
$ python3 tools/noswap.py deploy --set-mania ~/Code/mania/run
```

## convert

`convert` turns an old-style character (`make_configs.py` plus his `extras.py` and `abilities.py` entries) into a
`character.json`, and proves it before writing anything:

- `tools/character_json.py` must turn the new file back into the very same Sonic 1 and Sonic 2 sheet2ani configs (equal
  values), the same EXTRAS entry and the same ABILITIES entry;
- if the configs are equal but their JSON text differs (only key order), that's a note;
- anything `character.json` can't express stops it, with the reason. Examples: layered or generated frames, drawn UI
  art, `s3k_animations`, `ball`, `cd_animations`, `charge_palettes`, `copy_heads`.

How it writes the file:
- frames are named by first use (`WALKING1`, `RUNNING2`, ...);
- `other_colours` is `"nearest"` when his module has `KEY_COLOURS` and the rest is its nearest-colour fill, else
  `"guess"` (sheet2ani's own nearest pick);
- big round speeds are written as hex.

`--wire` switches the build over, as step 1 did for Bean:
- `make_configs.py` becomes `make_configs.legacy.py`, and a three-line shim takes its place;
- his `extras.py` entry becomes `character_json.extras_entry(...)` (and his CREDIT_SHORT line goes);
- his `abilities.py` entry becomes `character_json.abilities_entry(...)`;
- the comments of both entries move into the `character.json` (`_extras_notes`, `abilities._notes`).

Both tool files are worked out before either is written. Everything is backed up to
`<temp dir>/noswap-convert/<id>/`, and `--unwire` puts it all back exactly.

### Proving a conversion

Equal configs mean identical outputs, but the real proof is a rebuild. Do it under the build lock:

1. Build the character as he is: `build_art.py <id>`, `build_all.sh` and `build_mania_art.py <id>`.
2. Hash `mods/NoSwap`, `mods/NoSwapMania/Data/Sprites/NoSwap` and his folder's build outputs.
3. Run `convert <id> --wire`.
4. Rebuild and hash again. Every file must be identical.

Files other work changed between the two builds (the DLL, the menu archives) are explained by their sources' hashes.
The S3&K DLL is reproducible now (`native/build.sh` links with `--no-insert-timestamp`), so the same sources give the
same DLL.

Converted so far:
- **Bean** (step 1, by hand);
- **Espio, Vector and Fang** (with `convert --wire`, 2026-10-01). Their rebuilt outputs are byte-identical.

## What still keeps a character from being self-contained

- **Old-style characters** (`make_configs.py` plus hand entries in `tools/extras.py`, `tools/abilities.py`,
  `build_mania_art.py`'s MANIA_ENABLED and `make_release.py`'s CHARACTERS) stay listed until converted; their numbers
  are in the registry already (step 4).
- **Python-only features** that `character.json` can't express yet:
  - layered or generated frames (Tails Doll's tails, Emerl's copy heads, Cream's decheese);
  - `generic_ball` colours;
  - S3&K-only and CD-only animations;
  - cards cut from build intermediates;
  - MANIA_OVERRIDES.
- **Packages carry generated scripts** from the core version they were built with, so core updates mean a rebuild.
- **The repo layout:** the extracted game data in `extracted/`, the Mania data in `~/Code/mania/extracted`, and the
  testmods folder.

## The Creator Kit (`tools/make_kit.py`)

The same tools, packed as a program for outsiders: no repo, no Python, no game files
(`kit/NoSwap-CreatorKit-<version>-{windows,linux}.zip`). `tools/noswap_cli/kit.py` has the details.

- **Inputs, classified.** Shipped (ours or credited): the tools, the schema, the ability registry, Rayan C.'s HUD font,
  the game files' *names* (data/kit/names-*.txt), the core manifest. Taken from the player's own games at **Set up**
  (`setup --origins DIR --mania DIR`, or the editor's Settings tab): Origins' four data packs (tools/rsdk5_extract.py's
  reader, by name: byte-identical to `extracted/`), HedgeModManager's decompiled S1/S2/CD scripts from the Origins folder,
  Sonic Mania's `Data.rsdk` files, and Mania's spin ball (cut from its own Sonic1.gif). Never shipped: anything SEGA's.
- **Kit mode** (`NOSWAP_KIT=1`, set by the program): the data folder is laid out like the repo (`NOSWAP_KIT_DATA`,
  default Documents/NoSwap Creator Kit); characters are in its `characters/` (`NOSWAP_TESTMODS`); NoSwap's own hand-listed
  characters and their per-folder tables are left out; the build runs `build_all.sh`'s Python steps without the DLL,
  the menu archives and Lock-On; `deploy` installs each built character as its own mod (output/<id>/).
- **Core coupling (decided):** the kit is packed from the same build as the release, and its packages are for that
  core version. The tools generate a package's scripts exactly as the repo does; what depends on the whole roster is
  pinned to the core's: the S1/S2/CD UI sheet boxes (data/kit/ui_layout.json; a character whose art doesn't fit them
  is refused) and the names the core's shared scripts need from a player script (data/kit/core.json, checked on every
  build). Bean built in the kit is byte-identical to the repo's package but for his key, his build ID and the
  self-contained roll helpers in his own player scripts. When the core changes, pack a new kit with it.
- `make_kit.py stage | exe --linux --python PY | exe --windows --wine-python EXE | pack` (Windows under Wine,
  `$WINEPREFIX`); `pack` runs a leak check (no game file by hash, no private character, no path of this machine, no
  e-mail) and never runs make_release.py or the build.
