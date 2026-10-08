# Plan B: drop-in character packages

Status: steps 1-3 and 3b are built (see each step's notes), and phase A (the roster decided at runtime, below) is
built and awaiting its in-game test. The fixed player art names for S1/S2/CD (after phase A) are built and awaiting
their in-game test. The special stage retry fix (S1/S2) is built and awaiting its in-game test. Phase B (Origins' select
cards from the packages at runtime) is built and awaiting its in-game test.

## Goal

A character is one self-contained package, added by dropping it in (or ticking it in HedgeModManager) and
identified by name. No rebuilding NoSwap, no fixed numbers anywhere a player can see or a save depends on.
Removing a character never disturbs anyone else or anyone's saves.

## What we proved

The DLL hooks Windows' `CreateFileW`. Every file the game opens from NoSwap's folder passes through it: the
Retro Engine games' scripts, animations and sheets, and Origins' own menu archives (`raw/ui/*.pac`,
`raw/text/*.pac`). The hook can hand the game a different file instead.

- Test: `active/Sonic1u/Data/Animations/Extra20.ani` (Jet's file) replaced Gamma's. Gamma played as Jet.
- It works for files that appear, change or disappear while the game is running. F9 and F10 switched Gamma
  between Jet and himself, going back to Origins' menu each time, with no restart.
- HiteModLoader's own `AddInclude` / `GetRedirectedPath` did nothing when called from `Init`, which returned
  empty for every path. So we don't depend on them.

This removes the main obstacle: which file the game gets is now decided at runtime, per character.

## The key simplification: one extra at a time

The engine only ever runs one character. Today every script carries every extra (21 `case`s, combined HUD
sheets, per-ID tables), because they all have to be built in. With runtime redirect they don't:

- **The engine side:** while an extra plays, the game sees one generic "extra" slot. The redirect serves
  *that* extra's files for it: the player script with only its moves, its animation file and sheets, its HUD,
  monitor and signpost art, its palette data.
- **The menu side:** Origins' select still lists every installed character. Each has a kind (7, 8, ...)
  assigned at startup, and the DLL maps kind to package when you pick.

Side effects: the player-script size worries go away, since each script holds one character's moves. Adding
characters costs nothing in the engine.

## A character package

A folder, either inside NoSwap (`characters/<name>/`) or its own HedgeModManager mod that NoSwap finds through
the loader's mod list:

```
noswap_character.json   name ("noswap.gamma"), display name, base (sonic/tails/knuckles), flags (no_roll, super
                        art...), palette (22 colours), ability numbers for S3&K, credits and source links
Sonic1u/...  Sonic2u/...  SonicCDu/...  Sonic3ku/...
                        that character's files, laid out as the game asks for them: its player script (S1/S2/CD),
                        animation files and sheets, HUD / monitor / signpost / continue / ending art, special stage
                        art, S3&K .bin/.gif
ui/card_picture.dds     its card picture for the Origins select (phase B; its name is the JSON's "name")
```

The Python builders produce packages. That's the same work they do now, just written per character instead
of merged. Distributed packages are prebuilt; players never run Python.

## Runtime (the DLL)

1. **Startup:** scan NoSwap's `characters/` folder and every enabled mod (loader `ModList`) for
   `noswap_character.json`, then build the roster.
2. **Numbers by name:** a registry in `%APPDATA%\SEGA\SonicOrigins\NoSwap\roster.json` gives each name a
   permanent kind. A new name gets the next free number. A removed character's number is kept and never reused,
   and its menu slot is simply left out.
3. **Saves by name:** `extras.sav` records and S3&K's slot picks store the name. A save whose character isn't
   installed is kept aside, untouched, and comes back if the character is reinstalled. This includes a one-time
   migration of today's number-keyed saves.
4. **Picking:** when you choose a card (or Y for the level select), the DLL sets the active package. From then
   on the `CreateFileW` hook serves that package's files, and NoSwap's core files for everything else.
5. **The menu:** the select's names and card pictures come from `ui_mainmenu.pac`, `ui_gamestage.pac` and the
   text pacs, which the hook can also serve. The DLL builds the roster's versions at startup (see risks).
6. **S3&K:** it already works at runtime (costume mapping in the DLL). Palette and ability numbers move from
   the compiled `extras_gen.h` to the package's JSON.

## Steps, each useful on its own

1. **Registry and saves by name** (with migration). Small and contained, and everything else relies on it.
   *Done 2026-09-26:*
   - `extras.sav` version 2 stores records under each extra's permanent key (`noswap.<art folder>`, extras.py
     `key`, `EXTRA_KEYS` in the DLL).
   - Records for absent extras are kept.
   - Version 1 files convert on load, keeping `.v1.bak`.
   - S3&K `[Slots]` picks are written as keys; old numbers are still read.
   - A permanent-number registry isn't needed yet: numbers are still assigned per build, and nothing saved
     depends on them any more. *(Built in phase A, below: roster.json.)*
2. **Redirect engine:** turn the prototype into the real thing. Package discovery, active-package switching on
   pick, and logging. Delete the F9/F10 test keys.
   *Done 2026-09-26* (the DLL's "character packages" section):
   - Packages are found in `characters/*/` and in enabled mods (loader ModList).
   - The active one is set in `SetLastKind` for S1/S2/CD (both A and Y) and from the S3&K character.
   - `Hook_CreateFileW` serves its files.
   - Tested in-game with a test Gamma package.
3. **One generic extra slot in the S1/S2/CD scripts:** the builders emit a core set of scripts with no
   per-character `case`s, plus each package's own files. Prove it with Gamma alone as a package, then move
   everyone.
4. **Per-character art:** HUD, monitor, signpost, continue, ending and special stage art become package files.
   CD already does this with its `_x<n>` copies.
   *(Done: the UI and special stage art in step 3b; the S1/S2/CD player animation and sheets under fixed names on
   2026-09-27, "Fixed player art names" below.)*
5. **S3&K from package data.**
6. **The menu at runtime:** build the roster's pacs in the DLL at startup. The fallback is a one-click "refresh
   roster" tool (the Python pac writers already exist) if the C++ port proves too heavy. *(Done differently: phase B,
   below. The archives are built once with generic card slots; the DLL only writes bytes in place.)*
7. **Packaging:** core NoSwap plus one mod per character (or one pack with all of them). Check GameBanana's
   rules for separate uploads.

## Step 3b in detail (from the 2026-09-26 survey)

Step 3a is done: each package has its own S1/S2 player script. Step 3b removes the rest of the per-character
content from NoSwap's shared files. Raw survey lists were in the session scratchpad; the summary is below.

### Two ground rules

- **Fixed file names, shipped by NoSwap as placeholders.** The redirect only sees files the mod loader already
  resolved into NoSwap's folder, so a package can't add a name NoSwap doesn't ship (like `Extra22.ani`).
  - The one generic extra uses fixed names: `Animations/NoSwapExtra.ani` and `NoSwapExtraSS.ani`,
    `Sprites/Players/NoSwapExtra_1..8.gif` (and `NoSwapExtraSS_1..2.gif`, S1's special stage), `Special/NoSwap_Extra.gif`, the `*_NoSwap.gif` UI sheets,
    `3K_Players/Extra.bin/.gif`, and so on.
  - NoSwap ships Sonic-looking or blank versions. Each package ships its own under the same names, and its
    .ani/.bin files name those same sheets.
- **Option A for IDs.** Every shared script treats `stage.playerListPos >= 7` as "the extra" and never tests a
  particular number. A switch on the character first maps any extra to its base character's ID (Sonic,
  Tails or Knuckles), so `case` labels stay constants.
  - Origins still gives each character its own kind (7, 8, ...), so saves, callbacks and the menu are unchanged.
  - The alternative, the DLL feeding the engine a fixed kind 7 for everyone, needs another hook and would
    change what Origins' own callbacks see.

### The work, in order

1. *(Items 1 and 2 done and tested in-game 2026-09-26: `NoSwap_flags`, bits 1 Knuckles-like, 2 Tails-based,
   4 magnetic, 8 no breathing, 16 surging, is set by each player script; the remap helpers are in
   noswap_common.py.)*
   **S1/S2 remaps.** Every "like Sonic" case list collapses to one generic path. These are in stage setups,
   Tornado, special-stage results, endings, continue, title and so on. Mechanical and small, and the diff shows
   exactly what changed.
2. **S1/S2 ability flags.** One public bit-field value (`NoSwap_flags`: Knuckles-like, magnetic,
   no breathing, surging) replaces `NoSwap_knuxLike` and the ID tests in Monitor, Ring and the water scripts.
   The package's player script sets it. (2026-09-27: bit 32, breaks walls like Knuckles without being built on him
   (abilities.py breaks_walls: Heavy), read by S1's GHZ / SLZ and S2's HPZ BreakWall; CD has no shared value, so such
   an extra's player script sets reserved slot 5's PropertyValue to 1 at startup for R1 / R5's BreakWall; in S3&K the
   DLL shows the BreakableWall object Knuckles' character ID, for a package with "breaksWalls".)
3. *(Done 2026-09-26, awaiting in-game test: noswap_common.UiSheets gives fixed boxes, and the pixel proof found 0
   differences in 9,269 frames. The S1 ending sheet went from 512×1626 to 512×756.)* **S1/S2 UI art.**
   - The HUD icon and name, monitor, signpost, continue, results and ending art become fixed frames on the
     `*_NoSwap.gif` sheets. Each package ships its own copies, with its art in the same boxes (padded with
     transparency, so pixel-exact).
   - Check: render every extra's frames from the old combined sheets and from its package sheets, and compare
     pixels.
   - Known bug this fixes (the user found it 2026-09-26, deliberately left until this item): S1's ending.
     `Ending/Objects_NoSwap.gif` is 512×1626, and every extra has poses below y=1024. Silver vanishes when he
     jumps toward the screen and never reappears; probably most extras do too. Either the sheet is too tall or
     it doesn't fit in sprite memory (F8 in the ending would tell). Per-package ending sheets, about 10 poses
     each, with the package's own EndingPose.txt, remove the combined sheet.
   - **512-row rule (found in-game 2026-09-26, fixed the same day, awaiting in-game test).** RSDKv4 draws only a
     sheet's first 512 rows, and an object type draws every frame from the last sheet its ObjectStartup loads. The
     512×756 ending copy (poses at rows 513+) and the 512×570 `Special/Objects_NoSwap.gif` (continue minis at row
     521) drew nothing for every extra. Now:
     - `UiSheets(keep=...)`: a game sheet with no room below gets a copy holding only the game frames its one loading
       script draws for an extra, at their own coordinates (`startup_frames` reads them from the game script by frame
       number: build_sonic1.KEEP_FRAMES), with the boxes packed around them. Ending: frame 10 (the logo) plus, should
       a player 2 Tails ever follow an extra, 20-23, 41-44; continue: frames 0-11 (text, stars, digits).
     - Sizes: `Ending/Objects_NoSwap.gif` 512×239, `Special/Objects_NoSwap.gif` 512×453. The other S1/S2 copies were
       already under 512 rows and are unchanged. CD ships nothing over 290 rows (v3 not changed).
     - UiSheets fails the build if a copy would pass 512 rows (or a width isn't a power of two); build_packages.py
       fails if any S1/S2 sheet NoSwap or a package ships is over 512 rows or 512 wide.
     - Proof (models both rules): 8,492 frames and 2.96M pixels identical to the art as item 3 placed it, 0
       failures; 546 box frames equal to the source art at its pivot; 198 copies checked (size, palette, game rects,
       no stray pixels). Before the fix, rule 1 blanked 252 extra frames (each extra's 10 ending poses and 2 continue
       minis); after, none.
4. *(Done 2026-09-26, awaiting in-game test: the proof found 0 differences in 443 frames and every script line.)*
   **S1/S2 special-stage player scripts:** each package ships its own copy, the same approach as 3a.
   - NoSwap's `Special/PlayerObject.txt` has no extra's case: without a package, an extra plays the stage as Sonic.
     A package's copy has its extra's block (what its case did) before the character switch.
   - Fixed names, placeholders in NoSwap: S1 `Animations/NoSwapExtraSS.ani` (NoSwap's is Sonic's SonicSS.ani) and
     the sheets it names, `Sprites/Players/NoSwapExtraSS_1.gif` and `_2.gif` (blank in NoSwap). These are byte
     copies of the extra's own sheets the old `Extra<n>SS.ani` used. S2 `Sprites/Special/NoSwap_Extra.gif` (the
     ball sheet, blank in NoSwap).
   - NoSwap no longer ships `Extra<n>SS.ani` or S2's `Special/NoSwap_Extra<n>.gif`. sheet2ani still writes the
     `.ani`; build_art.py / build_sonic1.py move it to the art's `build/` folder (extras.s1_special_ani), and
     build_packages.py reads it from there.
5. *(Done 2026-09-26, awaiting in-game test: the simulation matched all 252 (character, load) cases.)*
   **S1/S2 water palettes.** The ~900-line palette blocks in Labyrinth, Chemical Plant, Aquatic Ruin and
   Hidden Palace become one call to a function each package's player script defines.
   - After each whole-bank load, the setup does `temp7 = <load number>` and `CallFunction(NoSwap_WaterColours)`
     (noswap_common.WATER_FUNCTION; the loads are listed in each game builder's WATER_LOADS).
   - A package's player script writes only its own colours. NoSwap's own has an empty function, so vanilla
     characters and extras without a package get only the game's colours.
   - Every stage running these setups loads the global objects, and the player script is GameConfig object 0.
   - build_packages.py checks that every player script defines each function the shared scripts call.
5b. *(Done 2026-09-26, awaiting in-game test: the proof found 0 changed frames or pixels for every character but
   Metal, over 224 cases per game.)* **S1/S2 special-stage results (`Special/SpecialFinish.txt`),** the last per-extra
   site in the S1/S2 shared scripts.
   - The results lines that name the player (S1 "SONIC GOT THEM ALL"; S2 "SONIC GOT A", "SONIC HAS ALL THE",
     "SONIC RINGS") now show the nameless variant for any extra: `if stage.playerListPos >= 7` around the game's own
     switch (noswap_common.extras_skip_switch), instead of one case per extra. The art is the game's own
     `Special/Objects.gif`, so nothing per package is needed.
   - **Metal's decision (the user's call):** he is treated like every other extra, with no "SONIC". S1 now shows
     "GOT THEM ALL" (was "SONIC GOT THEM ALL"). S2 shows "GOT A / CHAOS EMERALD" and "HAS ALL THE / CHAOS EMERALDS",
     centred, and "RINGS" (was "SONIC ..." and "SONIC RINGS").
   - No per-extra numbers remain in any shared S1/S2 script. Every remaining test is `>= 7` or `< 7`.
6. *(Done 2026-09-26, awaiting in-game test: the proofs found 0 differences for every character, vanilla and extra.)*
   **Sonic CD.** No per-extra number or per-extra file is left in NoSwap's shared CD scripts.
   - **Player scripts (3a for CD):** build_packages.py runs build_soniccd.py with `NOSWAP_KEEP`, as for S1/S2. NoSwap's
     own `Players/PlayerObject.txt` has no extra's moves (abilities, extras.py "roll" / "no_roll", own colours); each
     package's has only its own. Every variant keeps each extra's basic startup (animation file, Sonic's moves, jump
     offset, idle case), so an extra without its package still plays, as Sonic would, in its own art. Functions
     left empty get a no-op statement: vanilla CD has empty subs but never an empty function.
   - **Sheets:** the ~20 scripts that picked `Items2_x<n>` / `Display_x<n>` (HUD, SignPost, GoalPost, SmokePuff,
     Explosion, BlueShield, SpecialRing, DeathEvent, AttractMode, PodSeed, R5/BossExplosion, the title cards,
     ActFinish) now have one `if Stage.PlayerListPos >= 7` block loading `Global/Items2_x.gif` / `Display_x.gif`.
     - The package ships its own. Its `Items2_x.gif` is byte-identical to the old `Items2_x<n>`.
     - `Display_x.gif` is the old `Display_x<n>` with the results name moved into two fixed boxes, as S1/S2's
       UiSheets do. ActFinish can then use fixed frames. "<NAME> GOT" is centred on x 68, up to 220 px. "<NAME>" goes
       in 16 rows added below (290 high); it ends at x 48, up to 256 px. Both boxes fit any name, whatever extras
       exist.
     - NoSwap's placeholders are Sonic's art with empty name boxes.
     - The per-extra copies of Sonic's blocks (R1/TunnelPath, R3/ScoreChute, R6/IceBlock, Special/StageFinish and
       PauseMenu) became one `>= 7` block.
   - **Package copies:**
     - `Special/Sonic.txt`: the spin ball on the fixed `Special/NoSwap_Extra.gif`, byte-identical to the old
       `NoSwap_Extra<n>.gif`. NoSwap's own copy shows an extra as Sonic, like S1/S2's.
     - `Global/WarpSonic.txt`: its own bounce frames from its own player sheet. NoSwap's shows Sonic's. A fixed sheet
       would have added a sheet to every stage, because WarpSonic loads at every stage start.
   - **Ability checks:** Monitor (Power Surge), Ring (magnet) and R4/Water (no breathing) call
     `NoSwap_SurgeMonitor` / `NoSwap_RingMagnet` / `NoSwap_NoBreathing`. The player script defines these, with the
     inline code they replace. In NoSwap's own they do nothing.
   - **Palettes:**
     - The package ships `Palettes/NoSwap_Extra.act` (its colours, loaded by its player script and its
       Special/Sonic.txt).
     - It also ships `NoSwap_Extra_R4{A,B,C,D}_WaterPal.act`. Each is the game's file with the extra's tinted colours
       over its slots (min to max, as the old load wrote them). The R4 BGEffects load it into the same bank, whole,
       for any extra, right after the game's load.
     - NoSwap's placeholders are 768 zero bytes and the game's water palettes unchanged. That is exact for Metal,
       who has no colours of his own and ships none. The 100 per-extra `.act` files are gone.
   - **v3 (CD) rules learned** (the S1/S2 checks' CD versions: scratchpad `cd/checks.py`):
     - CD's GameConfig.bin (v3) holds: name, data folder and description (u8-length strings; no palette, unlike
       v4), a u8 object count, the names and then the script paths, then a u8 variable count followed by
       (name, 4-byte big-endian value) pairs.
     - It has 33 global objects (the player script is object 0) and 226 global variables. `PLAYER_SONIC`, `_TAILS`,
       `_KNUCKLES` and `_AMY` are among the variables, so they can't be case labels; the `_A` aliases can. No case
       label anywhere names a global.
     - Names: nothing in vanilla shows whether v3 ignores case (no identifier appears in two cases), so we assume
       it does, as v4 does. The check finds no two NoSwap names differing only in case: aliases per file;
       functions across every player variant, every shared script and the globals.
     - v3 has no script values or tables, and aliases are per file. What scripts share:
       - functions: a stage compiles every script's functions into one list, player script first. 118 vanilla
         scripts call Player_* functions; NoSwap's Spikes already called `NoSwap_ShellSpikes`. A called function
         runs as the calling object, with the same TempValue0-7 and CheckResult.
       - reserved entity slots (`Object[5].ValueN`).
       - GameConfig globals.
     - Shared scripts get per-character behaviour by calling a player-script function, as S1/S2's
       `NoSwap_WaterColours` does. build_packages.py checks that every player variant defines every player function
       any other script names. The checks also confirm that no script of a stage without the global objects
       (Title, Menu, special stages, AttractMode) names one.
     - `SpriteFrame` takes variables (R4/SolidBarrier). So frames computed from values are possible, but unused.
   - **Proofs** (scratchpad `cd/`):
     - `proof_player.py`: each player script is partially evaluated for one character, and every sub and function
       compared. NoSwap's own matches the old full build for 0/1/2/5, and each package's for its extra: 25/25.
       There are two normalisations, both checked: `NoSwap_RollAllowed`'s leftover CheckResult is dead, and
       `NoSwap_RollOut` can't fire without an ANI_NOSWAP_ROLL.
     - `proof_scripts.py`: every other script the snapshot shipped, for 25 characters. Player functions are
       inlined, and frames are compared as rendered pictures from the sheet the object loads: 2,350 cases,
       35,822 frames, all identical.
     - `proof_palettes.py`: every run of palette loads, simulated with the files the game is served:
       250 cases, 360 runs, all identical.
     - Negative tests (another extra's package, NoSwap's own as an extra) show differences, as they should.
     - S1/S2 outputs are byte-identical, and the build is deterministic.
   - **Left, by design:**
     - NoSwap's own player script still has each extra's basic startup by ID (as S1/S2's). *(Gone in phase A: an extra
       with no package plays as Sonic.)* NoSwap still ships `Animations/Extra<n>.ani` and `Players/Extra<n>_*.gif` (as
       S1/S2 do), which packages' player scripts and WarpSonic copies name. *(Gone: fixed player art names, below.)*
     - The enemies' shot-reach tests (`Object[5].Value3 == <reach>`) list every extra's reach values. They name no
       extra, but a package with a new reach needs a NoSwap rebuild.
   - **Test in-game:**
     - HUD icon, results (incl. "<NAME> GOT" and the good-future "<NAME>"), signpost, goal post, explosions, smoke,
       shield, special ring.
     - Title cards, the time warp and the warp run, R1 tunnel, R3 score chute, R6 ice block.
     - R4 water palettes and other palette effects, the special stage (ball, colours, results, pause).
     - the Power Surge monitor zap and the ring magnet, Metal underwater, and a vanilla character.
     - CD file opens through the package redirect.
7. **S3&K.**
   - The DLL reads each package's `noswap_character.json` (palette, base, flags, move numbers) instead of the
     compiled-in `extras_gen.h` tables, and needs a real JSON reader. A brand-new *kind* of move still needs a
     DLL build.
   - The sprite swaps move to fixed names. S3&K file opens through the redirect haven't been tested yet.
   - The save screen shows several characters at once, so its pictures need slot placeholders, or copies the
     DLL caches at startup. (Done: numbered placeholders plus cached .bin copies, below.)
   - `KIND_COUNT` and the menu tables become runtime values. The near-memory layout caps this at about 160 kinds.
     *(Done in phase A, below: the near memory is now 0x2000 bytes, room for kinds up to 254.)*

   *Part 1 done 2026-09-26, awaiting in-game test (the first three points; the fourth, and the save screen, are
   part 2):*
   - **Data from packages.** build_packages.py writes into each `noswap_character.json`: `base` (sonic / tails /
     knuckles), `palette` (`{"74": "#6C0090", ...}`, slot order kept), `roll`, `no_roll`, and `s3k`: `anim_base`,
     `special_palette` (the Blue Spheres ball's colours) and `abilities` (every ExtraAbilities field by its C++ name,
     110 of them; gen_s3k_header.s3k_json).
     - The DLL reads every package's file at startup with its own JSON reader (native/src/ExtraData.h: objects,
       arrays, negative numbers, fractions, escapes incl. `\u` pairs; numbers may also be strings, `"0x6000"`,
       `"#RRGGBB"`). Extra n's data is the package whose key is `EXTRA_KEYS[n]`.
     - A field a package lacks gets the "no moves" default, an unknown one is ignored, tick counts are kept at 1 or
       more; all logged. An extra with no usable package plays as Sonic.
     - `extras_gen.h` now holds only global things: `EXTRA_COUNT` / `EXTRA_KEYS` / `EXTRA_NAMES` (the numbering, per
       build until part 2), the ExtraAbilities struct and its field list (`EXTRA_ABILITY_FIELDS`: type, name, count,
       default). No per-extra data is compiled in.
   - **Fixed names** (extras.S3K_FIXED): `3K_Players/Extra.bin/.gif`, `3K_Special/Extra.bin` + `NoSwap_Extra.gif`,
     `3K_Global/HUD_Extra.bin/.gif`, `3K_Global/SignPost_Extra.bin/.gif`.
     - build_s3k_art.py and build_s3k_hud.py write them to the art's `build/Sonic3ku/` (extras.s3k_build), and
       build_packages.py copies them into the package. It checks that every sheet a package .bin names is a fixed
       name or the game's.
     - NoSwap's placeholders (build_s3k_art.write_placeholders) are byte copies of the game's Sonic.bin, 3K_Special
       Sonic.bin, HUD.bin and SignPost.bin, plus blank 4×4 sheets. They exist only so the redirect can serve each
       package's file.
     - The 168 per-extra files are gone from NoSwap. `NoTail.bin` (shared) stays; the save screen's
       `MenuExtra<n>.bin/.gif` stayed until the save screen pictures moved to the packages (below).
   - **Proofs** (scratchpad `s3k1/`):
     - `proof_s3k_files.py`: 168 package files equal the old per-extra files, gifs byte for byte, .bins except for
       the sheet names inside.
     - `extra_data_test.cpp`: ExtraData.h built with g++, plus reader unit tests. All 21 packages' data equals the
       old compiled-in tables (the snapshot's extras_gen.h) in all 110 fields, palettes, base, anim base and roll
       flags. The struct's offsets are unchanged, and the negative test shows 420 of 420 wrong pairings differ.
     - S1/S2/CD outputs are byte-identical, and the build is deterministic.
   - **Startup log:** one `package data: extra n <key> from <folder>: base ..., own colours .., Blue Spheres colours
     .., ability animations from ..; <moves>` line per extra, then `package data: 21 of 21 extras have their data from
     their packages`. Every swap logs `3K_Players/Sonic.bin -> 3K_Players/Extra.bin (<key>, scope 2)`; `package <key>:
     Sonic3ku\...` lines show the redirect serving the file.
   - **Risk:** the engine keeps a loaded file under its name for its scope. The fixed names are only safe if these
     files load with stage scope (2), which is logged; otherwise a second extra could get the first one's art.

   *Save screen pictures done 2026-09-26, awaiting in-game test (the last per-extra-numbered S3&K files):*
   - **Why not one name per slot:** the data select shows several slots at once, and the engine keeps a loaded
     sprite file (and its sheet) under its name for the whole menu visit; there is no way to unload one. A slot name
     reused for another extra while cycling would keep showing the first one.
   - **Design:** each extra gets its own picture name for the session instead.
     - Each package ships its picture once, under `extras.S3K_MENU_PICTURE`: `3K_Players/MenuPicture.bin`, naming
       `3K_Players/MenuPicture.gif` and nothing else (build_s3k_art.build_menu_frame writes it to the art's
       `build/Sonic3ku/`; build_packages.py copies it and checks the sheet name).
     - NoSwap ships 64 numbered placeholders (`extras.S3K_MENU_PICTURES`, the DLL's `MENU_PICTURE_COUNT` via
       extras_gen.h): `3K_Players/MenuPicture<j>.bin`, each naming its own blank 4×4 `MenuPicture<j>.gif`
       (build_s3k_art.write_menu_placeholders). They exist only so the redirect can serve them.
     - At startup (SetUpMenuPictures, before the file hook goes in), every extra whose package has a picture gets
       the next free j. The DLL writes a copy of the package's .bin to NoSwap's `cache\` folder with its sheet
       renamed to `3K_Players/MenuPicture<j>.gif` (RenameMenuSheet, ExtraData.h; the rest is byte for byte the
       same). It reads the copy back to check it.
     - The file hook's new path table serves `MenuPicture<j>.bin` from that copy and `MenuPicture<j>.gif` from the
       package, whoever is active. The table is filled once before the hook goes in and never changes after, so it
       needs no lock. A name always means the same extra for the whole session, so whatever the engine kept stays
       right while cycling.
     - The save slot loads `MenuPicture<j>.bin` for its extra. An extra without a picture shows its base in the
       menu's own art.
     - The cap is 64 extras with pictures per session, logged if reached. More needs more placeholders (tiny).
       The engine's own sheet limit applies as before: cycling through every extra in one visit loads one sheet each.
   - **Removed:** NoSwap's 42 `MenuExtra<n>.bin/.gif` files. build_packages.py deletes any that are left.
     `mods/NoSwap/cache/` is gitignored; deploy.sh's `--delete` clears it, and the DLL rewrites it at every start.
   - **Proofs** (scratchpad `s3kmenu/`):
     - `proof_menu_files.py`: all 21 packages' `MenuPicture.gif` equal the old `MenuExtra<n>.gif` byte for byte.
       Their `.bin` equal the old ones byte for byte once the sheet name is put back, with the same frames and
       hitboxes. 420 of 420 wrong pairings differ. The 64 placeholders are well formed, and no `MenuExtra` is left.
     - `rename_test.cpp`: ExtraData.h's RenameMenuSheet built natively with g++. Renaming each package's .bin back to
       `MenuExtra<n>.gif` gives the old file byte for byte, and `MenuPicture<j>.gif` parses with the old frames.
       Wrong magic, two sheets, another sheet name, a cut-short file and an empty new name are all refused, and
       case is ignored.
     - Apart from the DLL, NoSwap's other 1159 files (S1/S2/CD and the rest of S3&K) are byte-identical. The art
       build's other S3&K files are unchanged, and a second build gives the same output. The DLL differs only in
       its PE timestamps.
   - **Log:** at startup there is one `save screen picture: extra n <key> -> 3K_Players/MenuPicture<j>.bin / .gif
     (.. bytes, sheet ..)` line per extra, then `save screen pictures: 21 of 21 extras have theirs from their
     packages`. In the menu, `save slot <k> shows extra n (<key>): 3K_Players/MenuPicture<j>.bin, sprite <id>` is
     logged, and each file served is logged as `save screen picture: Sonic3ku\...\MenuPicture<j>.gif <- <package
     file>`.

   *Special stage results names done 2026-09-26, awaiting in-game test:*
   - **Bug:** `3K_HPZ/SpecialClear.bin` (the "SONIC GOT A / CHAOS EMERALD" lines) was never swapped, so Charmy got
     "TAILS GOT A". Only Hidden Palace's StageConfig lists the SpecialClear object.
   - **Now:** the extra's own name, as in "CHARMY GOT A", "CHARMY GOT ALL", "NOW CHARMY CAN" / "BE SUPER CHARMY" and
     "CHARMY CAN GO TO" (build_s3k_hud.build_special_clear).
     - The name art: the game's names here are the HUD's "Player Name" art moved up 128 palette slots (checked pixel
       for pixel for SONIC, TAILS, MILES and KNUCKLES). So the extra's name is its act results name (build_s3k_hud.word,
       same letters and rules) moved up 128 slots. No new letters were needed.
     - Layout: each line keeps its base line's gaps between words. It is centred as the game centres it: the left end
       is at -(width // 2) plus the base line's own offset from that (0 for most lines, -2 for "Got All", Knuckles' +2 /
       -1). Given the base's own name, the rule rebuilds all 15 of the game's lines exactly. Tails' "MILES" frame gets
       the same name and place. Knuckles-based extras get the blue SUPER (Sonic's frame), to match their blue name.
     - Width: the widest line is "METAL SONIC CAN GO TO", 294 px (-147..147), inside 320. The game's widest is
       KNUCKLES CAN GO TO (-124..128).
     - "Continue Sonic/Tails/Knuckles" are small pictures (Display.gif), not names, and stay the game's.
   - **Files:** fixed names `3K_HPZ/SpecialClear_Extra.bin/.gif` (extras.S3K_FIXED).
     - The package .bin names the game's two sheets plus `3K_HPZ/SpecialClear_Extra.gif` (the name, 256x16).
     - NoSwap's placeholder is a byte copy of SpecialClear.bin, with a blank 4x4 sheet.
     - DLL SWAPS: `{-1, 3K_HPZ/SpecialClear.bin -> 3K_HPZ/SpecialClear_Extra.bin}`, logged with its scope like the
       others.
   - **Proofs** (scratchpad `ssresults/proof_special_clear.py`):
     - In every package, 33 of the 38 animations are byte-identical to the game's.
     - The 5 name lines keep everything but px and the name frames. Their name pixels equal the package's HUD_Extra
       name +128.
     - The placeholder equals the game file. Apart from the DLL and the new 3K_HPZ files, all of NoSwap (S1/S2/CD
       included) is byte-identical, and the art builds' earlier S3&K files are unchanged.
8. **The Origins menu** (the largest piece). *(Built: phase B, below.)*
   - Build the select screen's archives once with a fixed number of generic slots (say 64).
   - At startup, the DLL patches each installed package's pre-encoded card picture into a cached copy, and
     writes the names into the text archives.
   - Fallback: a "refresh roster" tool.

Other notes:
- Dead code to delete: the old script-save functions in noswap_common.py (`SAVE_FUNCTIONS` and friends).
- Today's 21-key order stays frozen as a legacy map, for converting old saves and old `[Slots]` numbers.

### Open questions

- ~~**The results screens:** Metal kept "SONIC" in the special-stage results.~~ Decided 2026-09-26: Metal is
  treated like every other extra, with no "SONIC" (item 5b).
- **SpriteFrames from a package function:** can a function in the player script add frames to the calling
  object? If so, UI art could come from the package without fixed boxes. Unverified.

## Phase A: the roster is decided at runtime (built 2026-09-26, awaiting in-game test)

Before this, extras were numbered at build time: extra n had kind 6 + n everywhere (the DLL's `EXTRA_COUNT` /
`EXTRA_KEYS` / `EXTRA_NAMES` from extras_gen.h, the menu tables sized by them, and each package's scripts testing its own
ID). Now the DLL decides at startup which characters exist and their kinds; nothing numbered is compiled in except the
frozen first 21 keys.

### The registry (native/src/Roster.h, plain C++)

- `%APPDATA%\SEGA\SonicOrigins\NoSwap\roster.json` (next to extras.sav): `{"version": 1, "note": ..., "kinds":
  {"noswap.metal-sonic": 7, ..., "someone.newchar": 28}}`, written by the DLL (a `.new` file swapped in).
- **Legacy kinds:** `LEGACY_KEYS` freezes today's 21 keys at kinds 7-27 in today's order, whatever the file says, so the
  prebuilt menu archives (card names `MAINMENU_character_name_noswap<n>`, pictures `PRM_chara_<k+1>`) still match.
  tools/gen_s3k_header.py stops the build if extras.py's first 21 keys ever differ. New characters go after them.
- **A new key** gets the next kind after the highest ever given (28, 29, ...), never a gap.
- **A removed key** keeps its kind in the file (reserved, never reused) and isn't offered. Its saves stay in extras.sav
  (kept aside as before) and its `[Slots]` pick stays in the ini; both come back with the package.
- **Maximum:** kinds are bytes and 0xFF marks an empty card slot in Origins' rows, so the highest kind is 254 (248
  characters ever numbered, 7-254). The near memory for the menu's kind table grew from 0x1000 to 0x2000 bytes (0x100 +
  255 x 24). A key found once all kinds are given gets none: it isn't offered, and the log says so.
- **Bad files:** one that isn't JSON or has no `"kinds"` object is renamed `roster.json.unreadable` and the registry
  starts over from the 21 legacy kinds (packages beyond them then get new numbers, in the order found; saves are by
  key, so none are lost). Bad entries (a kind outside 7-254 or not a number, a key or kind given twice, a legacy key
  moved, another key on a legacy kind) are left out one by one, logged, and the file is rewritten.

### The DLL (NoSwapS3K.cpp)

- **The runtime roster** (`BuildRuntimeRoster`, in `FindPackages`, before any hook): installed packages + registry ->
  `g_roster` (kind, key, name, package folder, S3&K data, whether its card is in the menu archives), in kind order, and
  `g_rosterByKind[kind]`. Kinds with no installed package aren't in it and are skipped everywhere.
- Everything that used `EXTRA_COUNT` / `KIND_COUNT` / `EXTRA_KEYS` / `EXTRA_NAMES` now reads the roster:
  - Origins' select: the kind table (entries up to the highest kind offered) and the "kind <= max" stub's imm8,
    `BuildMaster` (paging lists only offered extras), `Hook_Build`, the save views (`Offered(kind)`), `SlotIndex` and
    `SetLastKind` (any kind 7+ -> Sonic's slot / not stored), `KindAllowed` (offered extras only, not in S3&K),
    `CardHasSecondLine` (the package's name).
  - S3&K: `g_character` is now the extra's kind; `Extra(kind)` is its roster data (special stage palette too); the save
    screen cycles through offered extras in kind order (`NextExtra`); `[Slots]` and `[Debug] Character` take a key (an
    old number is read as the legacy extra number, 1-21); save screen pictures are given per roster entry.
  - extras.sav: records by key through the roster; version-1 files convert with the legacy numbering.
- **Cards for a kind past 27** (a package with no card in the prebuilt archives): its base character's picture and no
  name, logged. Phase B builds real cards at runtime. *(Done: phase B.)*
- **Log at startup** (NoSwapS3K.log):
  - `roster: <key>: new, kind <k>` for each newly numbered key; `roster: <path> written (<n> kinds)` when the file
    changed;
  - one `roster: kind <k> -> <key> -> <package folder>` line per offered character (with "(no card in the menu archives
    yet ...)" past 27), then its `package data: kind <k> <key>: base ...` line;
  - `roster: kind <k> <key>: reserved, not installed (not offered; its saves are kept)` for each missing one;
  - `roster: <n> characters offered, kinds 7-<max> (<m> with S3&K data); registry <r> kinds, highest <h> of 254`;
  - later: `real kinds: kind table 0-<max> (<n> offered extras, <f> with a fallback card)`, `save screen picture: kind
    <k> <key> -> ...`, `extra character: kind <k> (<key>)`, `save slot <s>: character <c>, extra kind <k> (<key>)`.

### Package scripts are kind-free (tools/generic_extra.py)

Only one extra ever plays, so a package's scripts only need "is the player an extra" (`>= 7`). The builders still write
each package for its extras.py ID (its "build ID", now `build_id` in its noswap_character.json, formerly
`character_id`); build_packages.py then rewrites every freshly built player script (S1/S2/CD `Players/PlayerObject.txt`,
S1/S2 `Special/PlayerObject.txt`, CD `Special/Sonic.txt` and `Global/WarpSonic.txt`) so that any kind from 7 up behaves
exactly as the build ID did and kinds 0-6 exactly as before:
- `switch <kind>` (`stage.playerListPos`, `player.character`) with the build ID's case -> `if <kind> >= 7` / what the
  switch ran for it (its case to the break) / `else` / the switch with every label of 7 and up taken out. Switches
  without it just lose the other extras' labels (and the code only they reached).
- `if <kind> <op> <constant>`: kept when it already answers the same for every kind from 7 up; else `>= 7` / `< 7`, or
  the branch every kind takes; or, when an extra takes one branch and the vanilla kinds differ among themselves,
  `if <kind> >= 7` / that branch / `else` / the original `if`.
- Where the kind is a row number into the package's own per-extra tables (`GetTableValue(x, stage.playerListPos, T)`,
  `tempN = stage.playerListPos`): in code only an extra reaches (from the enclosing tests, and for a function from
  every place that names it; a public function another script names counts as reachable by anyone) the value is
  written in (`x = <T[row]>`, `tempN = <row>`); elsewhere an `if >= 7 / that / else / the original`. Tables nothing
  reads any more go. So the build ID survives only as a row number inside the package's own tables, never as a kind.
- `player.character = stage.playerListPos` stays: the character value is the real kind.
- `#platform` blocks: code is read as Origins compiles it (USE_ORIGINS / Use_Origins and Standard); other platforms'
  lines are kept untouched; code copied to a new place takes only Origins' lines.
- **NoSwap's own player scripts** (no package) are rewritten with row 0: an extra with no package plays exactly as Sonic
  (the shared scripts still see an extra and use NoSwap's Sonic-looking placeholders). The per-ID basic startups (each
  extra's animation file) are gone from them. A kind with no package isn't offered anyway; this is the safety net.
- **Build checks** (build_packages.py `check_kind_free`): no script NoSwap or a package ships has a case label or kind
  comparison naming a particular kind of 7 or up (only `>= 7` / `< 7`). The existing checks pass unchanged (case labels
  not globals, no names differing only in case, every player variant defines what the shared scripts use, sheet sizes).
  The pass is only ever applied to a file its builder has just written (a second pass would read `>= 7` as Sonic's).
- Sizes: every package player script is smaller (e.g. Gamma S1 5703 -> 5522 code lines, CD 4919 -> 4416); NoSwap's own
  too (S1 5383 -> 5153).

### Proofs (scratchpad `phaseA/`)

- `proof_generic.py` with its own partial evaluator `project4.py` (independent of generic_extra.py: its own cleaner,
  parser and projector, for v4 and v3): for each of the 152 rewritten scripts, the snapshot and the build are projected
  for every (kind, player character) pair: vanilla kinds 0-6 x characters 0-6 against themselves, and extra kinds 7, 8,
  27, 28, 40, 159, 254 (and the build ID) against the snapshot run as its build ID (characters 0-6, and the extra's own
  kind as player 1). Every event and reachable function is compared statement by statement, plus every table still
  read and the alias values used. **6,496 cases, 0 differences.** NoSwap's own: any extra kind against the snapshot run
  as Sonic.
- Negative tests: Fang's old script against Jet's new one as kind 40, and NoSwap's own old player script as Gamma (26)
  against its new one, differ as they must. A deliberate one-number mutation (Gamma's melee 32 -> 33) is caught as
  kind 40 (and, correctly, not for the vanilla kinds, which can't reach it).
- `roster/roster_test.cpp` (Roster.h built natively with g++): seeding (21 legacy kinds, the file reads back, a second
  start changes nothing), discovery order, a new key (28, kept on later starts), a removed key (not offered, kind
  reserved, the next new key gets 29, restoring brings it back), corrupt files (7 kinds refused), bad entries one by one,
  the 254 limit (3 of 230 extra keys get none), quoting. 105 checks, 0 failures.
- The earlier tests still pass: `s3k1/extra_data_test` (21 of 21 packages' data equal the old tables, 420 of 420
  negative pairs differ) and `s3kmenu/rename_test`; `item45/checks.py` and `cd/checks.py` (v4 and v3 safety checks).
- Apart from the rewritten player scripts, the 21 noswap_character.json (`character_id` -> `build_id`) and the DLL, all
  of NoSwap (1375 files, S3&K and art included) is byte-identical to the snapshot, and a second build gives the same
  output.

### Test in game (all four games)

- Startup log: the roster lines above (21 offered, kinds 7-27, `roster.json written` on the first start only).
- Origins' select in S1, S2 and CD: every extra's card, name and picture as before; paging right/left through the whole
  list; continuing an extra's save; Y on a card (level select); a vanilla character.
- S3&K: the save screen cycle (up/down through every extra and back to the game's characters), saved slots keep their
  extra, Y level select, save screen pictures, Blue Spheres colours.
- Playing each game as a few extras (moves, HUD, results, special stages; Rouge/Charmy for Knuckles/Tails bases).
- Removing a package: **move** one package folder out of `mods/NoSwap/characters/` (renaming it inside still counts:
  the DLL finds any folder there with a `noswap_character.json`), restart. It is gone from Origins' select and the
  S3&K save screen; everyone else keeps their card, kind and saves; the log says `kind <k> <key>: reserved, not
  installed`. Put it back and restart: it returns under the same kind with its saves.

### Risks

- The rewritten scripts haven't run in-game yet: the proofs show they do what the old ones did, but the v4 / v3
  compilers haven't seen the new shapes (`if <kind> >= 7` around a switch, `player.character >= 7`).
- In a few NoSwap-own spots an `if` head that Origins' decompiled scripts write once per platform is wrapped for
  Origins only; the other platforms' view of those files no longer balances (never compiled by Origins).
- ~~A card for a kind past 27 shows its base's picture and a blank name (untested: the blank name keys may show as
  empty or as nothing at all).~~ Phase B gives it its own card.
- ~~A new package for S1/S2/CD can't bring its own animation file yet: the player scripts load `Extra<n>.ani` by build
  ID from NoSwap's folder, and the redirect only serves names NoSwap ships.~~ Done: fixed player art names, below.

### What phase B needs from this

- The roster: `g_roster` (kind, key, name, base, package folder, `menuPac`) is the list of cards to build; kinds past 27
  are the ones with no card yet (`real kinds: ... fallback card` in the log).
- Replace the kind table's fallback entries (`SetUpRealKinds`) with runtime-built picture patterns and name keys, and
  serve the rebuilt `ui_mainmenu.pac` / text pacs through the existing path table (`g_pathMap`).
- Then the legacy freeze (kinds 7-27 tied to the prebuilt archives) can be relaxed to "the first 21 keys keep their
  kinds" only; LEGACY_KEYS stays for converting old saves and `[Slots]` numbers.

## Fixed player art names for S1/S2/CD (built 2026-09-27, awaiting in-game test)

Before this, a package's S1/S2/CD player script loaded `Extra<n>.ani` (its build ID's number), whose sheets were
`Players/Extra<n>_<k>.gif`, all shipped by NoSwap itself; CD's WarpSonic copy loaded one of those sheets. A new package
had no such file in NoSwap for the redirect to serve under, so it couldn't bring its own animation.

- **Fixed names** (extras.py `PLAYER_ANI`, `player_sheet`, `PLAYER_SHEETS`), the same in all three games:
  `Animations/NoSwapExtra.ani`, naming `Sprites/Players/NoSwapExtra_1.gif .. _k.gif` in the order its sheets were
  listed. Each package ships its own. Today's most is 4 sheets in S1, 5 in S2 and CD; NoSwap ships 8 placeholders, so a
  new package with up to 8 needs nothing new. build_packages.py stops the build if an extra needs more.
- **NoSwap's placeholders:** a byte copy of the game's own `Sonic.ani` per game, and 8 blank 16x16 sheets
  (`gifio.save_sheet`). NoSwap's own scripts never load them: an extra without a package plays as Sonic (phase A).
- **Scripts:** a package's player script loads `NoSwapExtra.ani` (S1/S2: its startup case; CD: the normal and mini
  loads). CD's `Global/WarpSonic.txt` copy loads `Players/NoSwapExtra_<k>.gif`, the same sheet its .ani names, so it
  still adds no sheet to a stage. NoSwap's own scripts didn't change. S1/S2's startup case is now found by its `case`
  line (extras.startup_case), not by the animation name (abilities.py).
- **Build flow:** sheet2ani still writes `Extra<n>.ani` / `Extra<n>_<k>.gif` into NoSwap's game folders.
  build_art.py, and each game build at its start, move them to the art's `build/<game>/Data/` (extras.stash_player_art,
  as with the S1 special stage .ani). Everything that read them from NoSwap now reads them from there: abilities.py's
  roll and Spirit Flight checks, the S2 and CD spin balls, CD's roll and WarpSonic frames, build_sonic1's special-stage
  sheet copies and build_origins_menu.py. build_packages.py `build_player_art` writes the placeholders and each
  package's copies, and checks that the read/write round trip is byte for byte.
- **Removed from NoSwap:** 63 `Extra<n>.ani` and 146 `Extra<n>_<k>.gif`.
- **New build check** (build_packages.py `check_counterparts`):
  - every package file has a NoSwap file at the same path, except its noswap_character.json and its S3&K save screen
    picture (the DLL serves that under numbered names);
  - nothing NoSwap or a package ships names an extra's numbered `Extra<n>.ani`, `Extra<n>SS.ani` or
    `Extra<n>_<k>.gif`;
  - NoSwap ships no such file.

  All 985 package files pass.
- **Sprite caching:** the engine keeps a loaded animation and sheet under its name. The first redirect test showed that
  a changed file under the same name is read again after going back to Origins' menu (Gamma's `Extra20.ani` swapped for
  Jet's, switched with F9/F10). The S1/S2 UI sheets rely on the same thing, and the user has seen that work when
  switching extras. One extra plays per run, so no two packages' files meet in a stage.

### Proofs (scratchpad `fixedani/`, snapshot in `fixedani/before/`)

- `proof.py`, the art: all 63 (package, game) pairs pass.
  - Each package's `NoSwapExtra.ani` has the same animations, frames and hitboxes as the old `Extra<n>.ani`.
  - Written with the old sheet names, it equals the old file byte for byte (and the old one with the new names equals
    the new one).
  - All 146 sheets are byte- and pixel-identical to the old ones, and no package has a stray sheet.
  - The placeholders are the games' Sonic.ani and blank power-of-two GIF89a/0xF7 sheets with no 0x3B in their palettes.
  - All 1,260 wrong pairings (one extra's old file against another's new one) differ.
- `proof.py`, everything else: only the intended lines changed.
  - The only removals are the 209 numbered files, and the only additions the fixed-name ones.
  - 105 script lines changed (per package: S1 1, S2 1, CD player 2, WarpSonic 1), all the expected renames.
  - All 392 S3&K files and every NoSwap shared script are identical. Only the DLL's timestamps differ.
- The build checks all pass (kind-free, player functions and public names, sheet rows, counterparts), and no two
  shipped paths differ only in case. `build_art.py metal-sonic` followed by the build gives the same output, and a
  second build is identical.
- `newpackage.py`: a scratch copy of NoSwap with Gamma's package renamed `zz-newchar` (key `someone.newchar`) and Gamma
  removed.
  - All 51 of its files have NoSwap counterparts.
  - Every file its S1/S2/CD scripts load, and every sheet its .ani files name, is either its own (18, served under
    NoSwap's fixed names) or the game's own (39).
  - Nothing NoSwap ships names a numbered extra file or the character.

### Test in game

- Play several extras in S1, S2 and CD with their own sprites in stages. Include Super (Metal), roll (Mario), no roll
  (Gamma), Spirit Flight (Tikal) and the Knuckles and Tails bases (Rouge, Charmy).
- The special stages (S1's maze, S2's halfpipe ball, CD's ball), CD's time warp (WarpSonic's bounce frames) and CD's
  Metallic Madness mini form (still full size).
- Switch extras between runs through Origins' menu, starting the same zone each time, in all three games.
- Vanilla characters in all three games.
- Removing a package (move one out, restart): it isn't offered, and the others still play with their own art.
- The log: `package <key>: Sonic1u\...\Animations\NoSwapExtra.ani` and `...\Players\NoSwapExtra_1.gif` lines when a
  stage loads.

### What a brand-new package still needs from NoSwap

Its files now all have fixed names that NoSwap ships placeholders for. What still ties it to NoSwap:
- ~~**The Origins menu card:** kinds past 27 get their base's picture and no name until phase B.~~ Done (phase B): its
  `ui/card_picture.dds` and its name. Its picture must fit the 440x536 cell (Sonic 1 frames up to 55x64 at 8x).
- **Interfaces the shared scripts use:** its player scripts must define what NoSwap's shared scripts use.
  - S1/S2: the public `NoSwap_flags`, the `ANI_NOSWAP_*` aliases and `NoSwap_WaterColours`.
  - CD: `NoSwap_SurgeMonitor`, `NoSwap_RingMagnet`, `NoSwap_NoBreathing`, `NoSwap_ShellSpikes` and the Player_*
    functions.

  build_packages.py checks this for its own packages; an outside one must match.
- **Fixed boxes and limits:** its S1/S2 UI art must fit the boxes in NoSwap's `*_NoSwap.gif` copies, which are sized
  for today's extras, and CD's name boxes (220 and 256 px). It can use at most 8 player sheets (`PLAYER_SHEETS`) and 2
  S1 special stage sheets (`SS_SHEETS`).
- **CD enemy shot reach:** the enemies' `Object[5].Value3 == <reach>` tests list today's reach values. A new reach
  needs a NoSwap rebuild.
- **S3&K:** a new *kind* of move needs a DLL build (its numbers come from its JSON).
- **Tooling:** packages are still made by NoSwap's Python builders (abilities.py, sheet2ani, generic_extra.py). An
  outside author has no standalone tool yet.

## First new character: Mecha Sonic (built 2026-09-27, awaiting in-game test)

Mecha Sonic (key `noswap.mecha-sonic`, extra 22, build ID 28, kind 28 at runtime) is the first character added since the
package system. Sheet: testmods/MechaSonic.png by Domenico (testmods/mecha-sonic/SOURCE.txt); configs:
testmods/mecha-sonic/make_configs.py. Moves (the user's kid's picks): **Spike Ball** (jump in mid-air: the Screw Kick
started by jump, abilities.py `kick_jump`, no bounce) and **Jet Boost** (Y: the melee's timing, frames and cooldown as a
burst of speed, `melee_boost`, no shot).

**What adding him still needed outside his own folder (pipeline feedback):**
- **Shared lists:** his entry in tools/extras.py (after the frozen 21) and his move numbers in abilities.py `ABILITIES`
  (keyed by build ID). A package can't bring its moves' numbers yet; they live in NoSwap's tools.
- **New kinds of move are shared code:** abilities.py (`kick_jump` in screw_kick, `melee_boost` in the melee, both only
  emitted when an extra in the build has them, so other packages' scripts are unchanged), build_soniccd.py (the same two,
  the jump-ability name map, and `SHOT_OUT` made optional: a melee extra without an entry was a KeyError), and for S3&K
  gen_s3k_header.py plus the DLL (`kickOnJump`, `kickSound`, `shotBoost`; ScrewKick takes the jump trigger; the shot
  applies the boost). The DLL is rebuilt.
- **Every package's noswap_character.json changed:** the three new ability fields are written into all 22 (their
  defaults for the others), since the loader warns for any field a package lacks.
- **Every package's S1/S2 player script changed (data only):** each carries every extra's colours
  (`NoSwapTable_PaletteAt` / `NoSwapTable_Palette`, read by computed index, so the kind-free pass keeps the whole table)
  and one blank line per other extra's removed startup case; Metal's and NoSwap's own also a `NoSwapTable_PaletteSlot`
  row. Normalising those away, all other scripts are identical. Suggestion: package builds should emit only their own
  rows and drop the blank lines, so the next character leaves the others untouched.
- **Fixed UI boxes:** "MECHA SONIC" in the S1 title-card alphabet is 159 px, 1 px wider than METAL SONIC, so the S1
  act-results name box grew (ActFinish #24: 158 -> 159 wide) and the HUD name tag's box moved (x 176 -> 177) on
  `Global/Display_NoSwap.gif`: NoSwap's shared ActFinish.txt / HUD.txt and all 21 other packages' S1 Display_NoSwap.gif
  changed. Proof (scratchpad `mecha/pixelproof.py`): every SpriteFrame of every S1 script loading that sheet, drawn from
  each package's old and new sheet in pivot space: 21 packages, 1,743 frames, 466,103 pixels, 0 differences; the changed
  pixels are only in rows 257-272 (the name box). His continue icons and one good-ending pose were chosen or cropped to fit
  the existing boxes (a first try grew the continue and ending boxes).
- **Tooling:** the art build reads abilities.py (S3&K shot boxes), so the moves must be in before `build_art.py`; the
  name-tag letters and the make_configs helpers (`tag`, `all_colours`, `config`) are copied per character (two different
  "M" glyphs exist).
- **Not needed:** nothing in Roster.h (a new key gets kind 28 at runtime), no new fixed file names (2 player sheets per
  game, under the 8 placeholders), no CD enemy reach (the boost attacks with his own box), no menu pacs (his card falls
  back to Sonic's picture and a blank name until phase B).
- Apart from the above, the DLL and his new package, all of NoSwap is byte-identical to the snapshot
  (scratchpad `mecha/before/`), and a second build gives the same output.

### Pipeline follow-ups (2026-09-27, built, awaiting in-game test)

The three suggestions above. How it was measured: two copies of the repo built side by side (scratchpad
`pipeline/exp`), one with Mecha Sonic and one without (his extras.py and abilities.py entries taken out). The
difference in every other package is exactly what adding a character does to it.

**1. A package's scripts carry only its own rows. Done.**
- *Before:* 21 packages x 3 games differed. S1/S2 changed because `abilities.extra_startup` built `NoSwap_PaletteAt` /
  `NoSwap_Palette` from every extra in tools/extras.py, even for a package build (NOSWAP_KEEP). The kind-free pass
  keeps those tables whole, since the colour loop reads them by a computed index. S1/S2/CD also got one blank line per
  other extra: the separator between extras' blocks stayed behind when generic_extra.py dropped the block. That was a
  dead switch case in S1/S2, and in CD an `if Stage.PlayerListPos == PLAYER_EXTRAn_A` that no kind can take. The move
  tables (`NoSwapTable_Melee*`...) were already per package, since abilities.ABILITIES is filtered.
- *Now:*
  - `extra_startup` writes only the kept extras' rows (NoSwap's own: none, 8 zero rows for the vanilla kinds).
  - generic_extra.py drops the separator with the block. In `drop_dead`, a blank line right after dropped case code
    goes. In `walk`, an `if` or `switch` that goes entirely takes the blank line before it.
  - The same two-copy test now differs in nothing: NoSwap's shared files, sheets, noswap_character.json and all 21
    other packages are byte-identical with and without Mecha Sonic.
- *This build versus the one before:* every S1/S2/CD player script changed once, and only in blank lines and the
  palette tables. Scratchpad `pipeline/verify.py` checks all 46 S1/S2 player scripts (the packages' and NoSwap's). Each
  one's own colours and palette slot are the same, and the vanilla rows are all zero. `diff -B` of every CD script is
  empty.

**2. Move numbers in the package. Not done (a plan).** What happens today:
- Output: an extra's ABILITIES entry reaches only its own package. The two-copy test proves it: taking Mecha's entry
  out changed nobody else's files.
- The animation slots (`ANI_ATTACK` 41 ... `ANI_SURGE` 50-52) are per kind of move, not per character. They're shared
  conventions of the module code and the art configs, and they can stay global.
- Only the authoring is shared: the entry lives in tools/abilities.py, keyed by build ID.
- Why not now:
  - testmods/ (where each character's configs are) is git-ignored and holds the artists' sheets. The move numbers
    would drop out of git.
  - Moving 22 entries out of abilities.py while other agents edit it is risky, and it gains nothing in the output.
- Plan:
  1. A tracked per-character source file, e.g. `characters/<art name>/character.py`, with the extras.py fields and a
     `MOVES` dict: the ABILITIES entry, without a build ID. The folder name and committing it are the user's call.
  2. extras.py appends these after its in-file list (the first 21 keep Roster.h's frozen order). abilities.py fills
     `ABILITIES[id]` from them.
  3. Pilot with Mecha Sonic, then move the rest one at a time. Acceptance: a byte-identical build.
- Related, for data: `gen_s3k_header.s3k_json` writes every DLL ability field into every noswap_character.json. That's
  why Mecha's three new fields rewrote all 22.
  - The DLL already falls back to the default for a missing field (ExtraData.h). It only logs "N of the DLL's ability
    fields not in the file".
  - So `s3k_json` could leave out default-valued fields, and that log line could go. Both are small, but they rewrite
    every JSON once and need an S3&K in-game check of every extra's moves. Left for when native/ is quiet.
- New *kinds* of move (a new module) will always be shared code: abilities.py, build_soniccd.py and the DLL.

**3. UI boxes with room to grow. Done for the names.**
- *Before:* a UiSheets box is the union of every extra's art. So a name longer than anyone's grew the box, and moved
  the boxes packed after it. That rewrote every package's sheet and NoSwap's shared scripts: MECHA SONIC's 1 px did it.
- *Now:* `noswap_common.UI_RESERVE` gives the two name boxes fixed room around the pivot, unioned with the art:
  - `act_name`: the results name, S1/S2, 192 px to the left of the pivot (was 159 / 167).
  - `life_name`: the HUD name tag, 64 px (was 54).
  - A new name within that room changes no other package.
- *This build versus the one before:*
  - Every S1/S2 `Display_NoSwap.gif` changed once, NoSwap's and all 22 packages'. So did the 4 name frames in
    ActFinish.txt / HUD.txt: S1 #24, 47; S2 0, #43.
  - The S1 tag box moved to a second shelf (the copy is 282 rows; S2's is 331).
  - Proof (scratchpad `pipeline/pixelproof.py`): all 4,094 frames of the S1/S2 scripts that load the sheet, drawn
    from each old and new sheet in pivot space. 1,029,266 pixels, 0 differences, and the game's 256x256 part is
    unchanged.
- Left: the pose boxes (continue minis, S1/S2 ending poses, CD score minis) are still the union of the art. Their
  sheets are tight (`keep`), and a new character's poses are chosen or cropped to fit (as Mecha's were). Growing one
  still rewrites every package's copy of that sheet. This can't go away entirely: a shared script has one frame per
  element for every extra.

**Diff against the snapshot** (scratchpad `pipeline/before` versus `pipeline/after`):
- Mine: the files above.
- The other agent's: Mario's S1/S2 `NoSwapExtra_1.gif`, `NoSwapShot.gif` gone, and TailsObject.txt.
- Build noise: NoSwapS3K.dll (6 bytes, the PE timestamp and checksum; native/ untouched).
- Everything else is byte-identical, including raw/ and every S3&K file.

## Special stage retry (S1/S2, built 2026-09-27, awaiting in-game test)

**Bug (the user saw it in S1 and S2):** Origins' "retry the special stage" turned an extra into Sonic. Before its
`NOTIFY_SPECIAL_RETRY`, SpecialFinish stands an extra in as Sonic (`stage.playerListPos = PLAYER_SONIC_A`; Origins only
knows kinds 0-6) and puts the extra back only when the callback returns (`SPECIALFINISH_WAITFORCALLBACK`). A retry
reloads the special stage instead, so the extra is never put back. The DLL sees no SetLastKind on a retry, so the extra's
package stays active and its files are still served.

**Fix:**
- **Package side.** Each package's S1 and S2 `Special/PlayerObject.txt` (served only while that extra is active)
  starts its ObjectStartup with:

  ```
  if stage.playerListPos == 0 // [NoSwap] Origins' special stage retry reloads an extra as Sonic: ...
      stage.playerListPos = NoSwapActiveKind
  end if
  ```

  build_packages.py adds these lines (`RETRY_KIND`, `add_retry_kind`) after the kind-free rewrite.
  - NoSwap's own copy doesn't get them: a vanilla character, or an extra with no package, is unchanged.
  - The test is `== 0`, the stand-in, not `< 7`. A level select started from an extra's card can switch to Tails,
    Knuckles, Amy or Sonic & Tails while the extra's package stays active, and those stay themselves.
  - Nothing reads the kind before this. In S1, Player Object is the stage's first object. In S2, SpecialSetup's
    ObjectStartup runs first: its Sonic & Tails switch and its ring table (`== PLAYER_KNUCKLES_A`) treat 0 and any extra
    alike. The special stages load no global objects.
- **The kind is written in by the DLL.** Packages stay kind-free, and the stage must carry the extra's exact kind (for
  saves, extras.sav and the results). So `NoSwapActiveKind` (extras.py `ACTIVE_KIND_TOKEN`, the DLL's through
  extras_gen.h) is a word the DLL replaces.
  - When the file hook serves any active package `.txt` naming the word, it serves a copy with the word replaced by the
    active kind in decimal (`SubstituteActiveKind`, Roster.h: whole words, any case, every other byte the same).
  - The copy is `cache\kind<k>_<path with '\' -> '_'>` in NoSwap's folder. It's written to a temporary name, then moved
    over, and read back to check. It's only rewritten when its content would change.
  - Earlier sessions' copies are deleted at startup.
  - If there's no kind, the file is too big or the write fails, NoSwap's own file is served instead (the extra plays
    that stage as Sonic, logged), never the word itself.
- **After the retry, nothing else changes.** The stage's `playerListPos` is the extra again from its first frame:
  - the S2 HUD and Checkpoint read it later;
  - SpecialFinish stands in and restores again, so a second retry works the same way;
  - the results show the nameless lines (`>= 7`);
  - the save (`saveRAM[slot] = stage.playerListPos`) and the next zone (`stage.listPos = specialStage.nextZone`) get
    the extra.

  A retry that finds the stage already loaded may skip recompiling (RSDKv4 reloads the same stage folder without
  recompiling), but ObjectStartup still runs, from the copy compiled with the kind.

**Checks:**
- build_packages.py `check_active_kind`:
  - the word is in exactly the 42 package scripts, once each, as `RETRY_KIND` wrote it, and never in NoSwap's own
    files;
  - no other name in any S1/S2/CD script (NoSwap's, a package's, the game's) or GameConfig global matches it ignoring
    case (15,650 names).
  - Negative tests are refused: the word in NoSwap's own file, a case variant in Monitor.txt, an altered retry line.
- `check_kind_free` passes with the new line (`== 0` is a vanilla kind; the assignment isn't a test).
- **Script diff:** each of the 42 files gains exactly those 3 lines right after `event ObjectStartup` (CRLF). Apart
  from them and the DLL, all of NoSwap is byte-identical to the snapshot (scratchpad `retry/before/`).
- **`retry/token_test.cpp`:** SubstituteActiveKind, built with g++ against Roster.h and extras_gen.h.
  - Its cases: whole words only, any case, neighbouring punctuation, NUL bytes, no word, kinds 0-6 and 255+ refused.
  - For all 42 package scripts and every kind 7-254, the copy equals the file with that one word replaced, contains the
    retry lines, and a second pass changes nothing.
  - 31,309 checks, 0 failures. NoSwap's own script fails, as it must.

**Log:** `package <key>: served Sonic1u\Data\Scripts\Special\PlayerObject.txt with kind <k> (1 x NoSwapActiveKind,
written to|already in <cache path>)` each time the stage loads it (the first special stage and every retry). A failure
logs `... NoSwap's own file served instead`.

**Test in game (S1 and S2):**
- An extra fails a special stage and retries through Origins, twice. It stays the extra, with its art and colours, and
  the log shows the served line each time.
- A win after a retry: the results (nameless lines), then the next zone as the extra, and the save continues as the
  extra.
- A vanilla character's retry is unchanged.
- A level select from an extra's card that switches to Tails before a special stage stays Tails.

**CD (not changed; the user is still testing it):**
- CD's `Special/StageFinish.txt` has the same pattern: `Stage.PlayerListPos = 0` before `EngineCallback(NOTIFY_SPECIAL_RETRY)`,
  put back only in `STAGEFINISH_SAVE` when the callback returns. A retry would behave the same.
- The same fix fits (v3): each package ships its own `Special/Sonic.txt`. In SS1-SS8 it is the 7th object, and the six
  before it (SpecialSetup, HUD, SS_TitleCard, UFO, UFONode, UFOPowerUp) never read the kind.
- The lines would go at the start of its `sub ObjectStartup` (`if Stage.PlayerListPos == 0` /
  `Stage.PlayerListPos = NoSwapActiveKind` / `end if`). The DLL's substitution already covers any package `.txt`, and
  `check_active_kind` already reads CD's names.

**S3&K** picks its character in the DLL, not through playerListPos, so none of this applies there.

**Risks:**
- A vanilla Sonic in a package's special stage becomes the extra. That needs the extra's package still active, as after
  a level select from an extra's card switched to Sonic, or a mode that never calls SetLastKind (if one starts S1/S2
  without the select). Such a Sonic already gets the package's scripts today, playing as Sonic.
- If Origins' retry ever reloads as anything but 0, the line does nothing (the old bug, no worse).
- The v4 compiler hasn't yet seen a number where the word was. The line has the same shape as the game's own
  `stage.playerListPos = <constant>`.

## Phase B: Origins' select cards from the packages (built 2026-09-27, awaiting in-game test)

Before this, the select's card pictures and names were baked into NoSwap's menu archives for the 21 legacy kinds only
(PRM_chara_8..28, one picture group per extra, and `MAINMENU_character_name_noswap<n>`); Mecha Sonic (kind 28) got
Sonic's picture and no name.

### Design

- **Built once, with generic card slots** (tools/build_origins_menu.py, tools/origins_cards.py; `SLOTS` = 64, like the
  S3&K save screen pictures). From the game's own files it writes `raw/ui/ui_gamestage.pac` (the popup's scene),
  `raw/ui/ui_mainmenu.pac` (the main menu's copy), the 12 `raw/text/text_menu_*.pac` and the descriptor
  `raw/ui/noswap_cards.json`. build_all.sh now runs it after build_packages.py (about 25 s).
  - **Pictures:** 64 cells of 440x536 (Gamma's height, today's cell) appended below `..._chara_sonic.dds`, 6 per row, 11
    rows: the texture goes from 1320 to 7216 px high (2640 wide, BC7).
  - **One generic cast instead of a group per card:** layer ref_btn gets one group `null_char_noswap` holding one image cast
    `chara_noswap` with 64 crop references (one per cell). Slot s's pattern `PRM_noswap_<s>` (`..._<s>_2` with the second
    name line) hides the game's seven groups, shows the generic one, sets its **CropIndex0** to s - 1 and switches
    `sysf_btn_name_2`. The game's PRM_chara_1..7 get one more hide track (the generic group). That is 2 casts and 128
    animations of 10 tracks, where a group per card needed a hide track for every group in every animation (N^2; 64 slots
    would be ~9,000 motions). The game's own state animations (in, loop, over, press...) key CropIndex0 of its casts
    (e.g. sonic_1 0..3, amy_1 8..11) and never touch the generic cast, so the value a pattern sets stays, as the Display
    of the old per-extra groups did.
  - **Names:** two keys per slot, `MAINMENU_character_name_noswap<s>_1` / `_2` (the old keys for s = 1..21), each with room
    for 31 UTF-16 units (64 bytes); the text and its u64 length field are rewritten in place. Same text in every language
    (as build_origins_text.py did; that script is folded in and gone).
  - **Only fixed bytes change:** the chunks holding the cells (238 per picture archive) and the text archives' whole
    roots are stored as **LZ4 blocks of literals only** (a header depending only on the length, then the bytes as they
    are). The descriptor lists, per archive, its size, each literal run `[stream offset, file offset, length]`, the row
    pitch and each slot's first block (pictures), or each slot's text and length offsets (names).
  - **Shipped with the first 21 cards written in** (slot = kind - 6, from their packages, by the same patch step in
    Python): without the DLL's copies the select looks as before.
- **Each package ships its card:** `ui/card_picture.dds`, a BC7 DDS (DX10, format 98, one mip) at most 440x536, sides
  multiples of 4, placed bottom-centre in the cell. build_packages.py writes it (`build_cards`: its Sonic 1 "Stopped"
  frame 0 at 8x, feet 20 px above the bottom, as before). Its name: the JSON's `name`, split at the first space. Any
  BC7 encoder's output works (the DLL copies blocks). check_counterparts exempts the file (NoSwap ships no such name).
- **Startup (DLL, `SetUpMenuCards`, before the file hook; pure logic in native/src/MenuCards.h):**
  - reads the descriptor (checks its version, sizes and that its pattern / key names are the DLL's);
  - slots: kind k gets slot k - 6 while that exists, others the lowest free slot, none past 64 (`AssignCardSlots`);
  - per offered character: its picture (`ReadCardPicture`) and name lines (`CardNameLines`: UTF-8 to UTF-16, cut to 31);
  - per archive: `PlanCardWrites` (every slot written: the card, or blank), then `cache\menu_<path>`: CopyFileW to
    `.new`, check the size and every run's literal header (`CheckCardRuns`), write, read back, move over. A `.stamp`
    beside it (FNV-1a of the source's size and time and every write) lets a later start reuse the copy after checking the
    written ranges read back. Served through `g_pathMap`.
  - The kind table: pattern `PRM_noswap_<slot>[_2]` and the slot's name keys; a slot without a picture shows its base's
    picture (and one name line); no slot: base picture, no name. `CardHasSecondLine`: own picture and a second word.
  - **Any failure** (no or bad descriptor, a file that doesn't match, a write or move failing) serves nothing and falls
    back to NoSwap's shipped archives: kinds 7-27 their shipped cards, others their base's picture and no name (today's
    behaviour), logged.

### Archive format findings

- The game's own files contain LZ4 chunks bigger than their data: a scan of all 473 PACx403 archives found 582 chunks
  with compressed > uncompressed size, up to 65,794 bytes (= 65,536 + a 258-byte literal header), and 39 chunks in
  `raw/NeedleShader.pac`'s dependency block that are exactly literal-only blocks of our form. So the game reads them.
  Only one chunk in all of them has equal sizes, so raw storage (compressed == uncompressed) is not relied on.
- The DLL therefore needs no LZ4 compressor and no PAC/SurfRide/BC7 code: only byte writes at offsets the descriptor
  gives, each checked against the literal header in front of it.

### Proofs (scratchpad `phaseB/`, snapshot in `phaseB/before/`)

- `cards_test.cpp` (MenuCards.h + Roster.h with g++): descriptor refusals (version, foreign pattern names, bad cells,
  `..` and drive paths), pictures (format, size, odd heights), names (split, UTF-8 incl. a surrogate pair, cut, bad
  bytes), slots (legacy, gaps, the 64 limit), LZ4 literal headers, run checks (size, a flipped header byte), a hole in the
  runs. Then the real patch step on NoSwap's archives and packages, fresh registry (22 characters) and with Gamma
  removed: 41,694 checks, 0 failures.
- `proof.py`:
  1. the C++ writes equal the Python mirror (`origins_cards.apply`) on all 14 archives in both scenarios, byte for byte;
  2. kinds 7-27: every card picture is pixel-identical (440x536 each) to the snapshot's in both picture archives, as
     shipped, patched, and patched with Gamma removed; the same image cast size, pivot, colours and cells for picture and
     group; each old PRM_chara_<k+1> and its new pattern show exactly their own picture, with the same second line; the
     game's PRM_chara_1..7 and its own 1320 rows of pictures unchanged;
  3. names: in all 12 languages, the first 21 characters' two lines equal the snapshot's; the game's own texts unchanged;
  4. Mecha Sonic (kind 28 -> slot 22): his Sonic 1 Stopped frame 0 at 8x (41x62 -> 328x496), computed independently from
     his art; "MECHA" / "SONIC"; pattern `PRM_noswap_22_2`; slots 23-64 blank (and slot 22 blank as shipped);
  5. negative: removing Gamma changes slot 20 only; all 462 ordered pairs of the 22 cards differ. 3,156 checks.
- Review picture: `phaseB/review/cards_all.png` (the 22 cards and names as the patched archives hold them).
- The build checks pass (build_all.sh); the retry token test passes on the 44 S1/S2 package scripts. Apart from the DLL,
  the raw/ archives and the packages' new `ui/card_picture.dds`, all of NoSwap is byte-identical to the snapshot.

### Log

`menu cards: kind <k> <key> -> slot <s>, name "<name>", its picture 440x<h>` per character; per archive `written to
<cache path> (<n> writes)` or `the cached copy is up to date`; `menu cards: <n> of <m> offered characters have a card
slot (...); 14 archives served from the cache`; later `served raw\ui\ui_gamestage.pac <- ...` when the game opens one.
A failure logs why and `NoSwap's own menu archives are served (...)`.

### Test in game

- The select in S1, S2 and CD: every card (vanilla, the 21, Mecha Sonic with his picture and "MECHA" / "SONIC"), paging
  right/left through all of them, picking and Y (level select), continuing a save, names on one and two lines. The
  highlight (over / press) animations on extras' cards (the picture should stay still, as before).
- The log lines above, including `served` lines for `raw\ui\ui_gamestage.pac` and `raw\text\text_menu_<language>.pac`.
- A second start: `the cached copy is up to date` for all 14.
- Removal: move a package out (e.g. Gamma), restart: no card for him, the rest unchanged, archives rewritten. Put it back.
- Another language (the text archive of that language is served).
- The main menu (ui_mainmenu.pac's copy) still loads.

### Risks

- **CropIndex0 from a pattern animation** is new to the game's use of this layer (it used Display only). If the value
  doesn't stay, every extra's card would show slot 1's picture (Metal Sonic). The fallback would be a group per slot with
  Display tracks as before (N^2 tracks; only build_origins_menu.py changes, the DLL and descriptor don't).
- **The text archives' load time:** if the game reads `text_menu_*.pac` before the DLL's Init puts the hook in, it gets
  NoSwap's shipped copy: new characters' names blank (the 21 are shipped). The log's `served` lines show it.
- Size: the picture archives grow (ui_gamestage 11 -> 26.5 MB, ui_mainmenu 80 -> 95.6 MB) and the first start (or a
  start after a change) copies both (~120 MB) into cache/. The texture is 2640x7216 (~19 MB in video memory).
- 64 slots: a 65th offered character shows its base's picture and no name. More slots need a rebuild (and a taller
  texture: 16384 px allows about 28 rows, ~168 slots).
- ui_mainmenu's copy is patched too, though only ui_gamestage's scene was seen in use.

## Art notes (2026-09-28, built, awaiting in-game test)

- **Pipeline signpost faces fill the board.** For an extra whose sheet has no signpost, `tools/sign_face.py`'s
  `board_face(head, scale)` gives the UI "sign_face" element: a head cut from the sheet on Sonic 1's Items2 board
  (face area 40x24 at 4,5), enlarged nearest-neighbour by a per-character, non-integer `scale` (sheet2ani's UI
  "scale", applied after the crop; the user's exception to the faithful-art rule, for signpost faces only). The crop
  keeps the head's bottom rows (chin) and middle columns so the enlarged head fits the area, centred as before; any
  trim is at the top (quill, crest or ear tips). S3&K's SignPost_Extra is built from the same image
  (tools/build_s3k_hud.py, which build_all.sh doesn't run: run it after build_art.py when a sign changes).
  Scales: Chaos 1.3, Jet 1.2, Mecha Sonic 1.3, Shadow 1.2, Silver 1.3, Sticks 1.15. Big and Gamma already
  fill the area (40x24 crops) and stay at 1; extras with their sheet's own signpost art are untouched.
- **Shadow's sheet is Sonic Megamix's** (testmods/ShadowMegamix.png, AsuharaMoon; SOURCE.txt), for every build. His
  moves are unchanged; only the art is. testmods/shadow/make_configs.py writes a working copy
  (build/megamix_source.png): the sprites recoloured from the sheet's "Custom" palette to its "Original" one by
  position (four darks change; 7 stray #400000 pixels merged into #420000), and each frame cut out by its pixels into a
  strip below, so frames don't catch their neighbours' flames. There is no variant switch: Gardow's earlier sheet
  and config stay locally in testmods/shadow (make_configs_gardow.py, SOURCE_gardow.txt; testmods/ is not in git).
  To go back, copy make_configs_gardow.py over make_configs.py, restore its README credit and run
  `tools/build_art.py shadow`, `tools/build_s3k_hud.py` and `tools/build_all.sh`.

## Risks and open questions

- ~~**The runtime menu build (step 6) is the biggest piece.** Our PAC, SurfRide and BC7 code is Python and would
  need porting to C++, or the fallback tool.~~ Phase B: no port needed (generic slots, literal chunks, byte writes).
- **The `CreateFileW` hook** sees every file open in the process. It must stay fast and match only NoSwap's (and
  packages') folders. It's proven on Proton; native Windows paths need a test too.
- **Other mods that replace the same game files as NoSwap still conflict,** as they do today.
- **Base characters:** Tails- and Knuckles-based extras (Charmy, Cream, Rouge) need their base's code paths in
  the generic slot. They exist today, just keyed by ID.
- **Things that remember a character across a session** (the continue screen, endings, the S3&K save screen)
  must ask the DLL for the active package rather than a number. Worth listing them all before step 3.
