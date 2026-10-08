# character.json: one file per character

A character's whole definition in plain data, in its art folder (`testmods/<id>/character.json`). A creator can edit it by
hand and a GUI can edit it without running Python. `tools/character_json.py` turns it into what the build pipeline
reads today. The first character converted is Bean (`testmods/bean/character.json`). His outputs for all four Origins
games and Mania are byte-identical to the hand-written version (`make_configs.legacy.py` and the old `extras.py` /
`abilities.py` entries).

Two general rules:
- **Comments:** any key that starts with `_` is a comment, and the loader drops it.
- **Fixed-point numbers:** anywhere a number goes, you may write a hex string such as `"0x30000"` or `"-0x20000"`. Use this for 16.16 fixed-point speeds, where `0x10000` is 1 px per frame.

## Fields

| key | meaning | today feeds |
|---|---|---|
| `format` | `"noswap-character/1"` | (checked) |
| `id` | must equal the folder name (the package folder) | extras `art` |
| `key` | the permanent key, `<creator>.<character>` (e.g. `someone.newchar`); left out, `noswap.<id>`. Saves, picks and the build numbers hang on it: never change it once released | extras `key`, registry |
| `name` | the in-game name (results, HUD tag), in capitals | extras `name` |
| `full_name` | a human-readable name | (informational) |
| `credits.short` | the line under the Origins card (keep it to about 32 characters) | extras `credit_short` |
| `credits.full` | the full credit, embedded in the configs | sheet2ani `credit` |
| `credits.artists`, `url`, `terms` | where the sheet comes from and its terms, verbatim | (informational; SOURCE.txt and the README still hold the prose) |
| `sheet.file` | the sprite sheet, relative to the folder | sheet2ani `source` |
| `sheet.background` | colours treated as empty | sheet2ani `background` |
| `sheet.feet_y`, `sheet.angled_halves` | where the feet sit; whether walk and run lists are upright frames followed by 45° frames | sheet2ani |
| `base` | `sonic`, `tails` or `knuckles`: the moveset, physics and animation list he plays on | extras `base`, template .ani |
| `flags` | `super` (Sonic's own Super palette), `drop_dash`, `roll`, `no_roll`, `private`, `crossover` | extras |
| `card` | `null` (the card is the Stopped frame at 8x), `{"scale": 4}` (the Stopped frame at 4x: a character taller than about 64 px doesn't fit the 536-px cell at 8x; Axel) or `{sheet, rect, scale, background, pivot?, baseline?}` | extras `card` |
| `games` | `sonic1`, `sonic2`, `soniccd`, `s3k`, `mania` | `mania` decides whether build_mania_art builds the character; the Origins builds always make all four games |
| `palette.own` | `{slot: "#rrggbb"}`: the character's own colours, in free global slots (74 and up) | sheet2ani `palette`, extras `palette` |
| `palette.shared` | `{"#rrggbb": slot}`: sheet colours that already match one of the base character's slots | sheet2ani `colours` |
| `palette.other_colours` | `"nearest"`: any other sheet colour goes to its nearest listed colour. `"guess"`: only the listed colours are mapped, and sheet2ani picks the nearest of slots 1-15 and the listed slots for the rest (Fang) | sheet2ani `colours` |
| `palette.strict` | stop the build if any frame has an unlisted colour | (build check) |
| `frames` | `{NAME: [x, y, w, h]}`: named cells on the sheet | (referenced below) |
| `animations` | `{base animation name: {frames: [NAME...], anchor?, align?, loop?, rot?, speed?, hitbox?, hold?}}` | sheet2ani `animations` |
| `animations_sonic2` | animations only on Sonic 2's list; CD and S3&K are built from the Sonic 2 config | sheet2ani (Sonic 2) |
| `ability_animations` | NoSwap's own slots: `{"41": {name, frames, ...}}`. 41 is the jump ability, 42 hover, 43 / 44 the Y move on the ground / in the air (a melee without 44 gets 43's frames there), 45 / 46 aimed moves, 47 / 48 glide up / down or cling, 49 roll | sheet2ani `appended_animations` |
| `special_stage` | Sonic 1's special stage animations (left out: a fallback, see below) | sheet2ani `extra_anis` |
| `ball` | the generic spin ball for some animations (see below) | generic_ball, sheet2ani |
| `s3k_victory` | the S3&K act clear: `{frames, pose?}` | sheet2ani `s3k_victory` |
| `snowboard` | S3&K Ice Cap 1's snowboard intro (Sonic-based): `{"ground": [...], "air": [...], "sidewind": [...]}`, poses stood on the official board, each spread over the game's frames (5, 3, 7). Any left out: ducking (last Looking Down frame), the spring pose (Bouncing), the twirl (Twirl H, between two ducking frames). `"offset"` on a frame moves it on its board | build_s3k_snowboard.py (the Sonic 2 config's `snowboard`) |
| `charge_palettes` | a charge shot's flash (and Pulseman's charged Voltteccer glow): `{"charge1" | "charge2a" | "charge2b": {slot: "#rrggbb"}}`, his own slots shown in those colours while it flashes (a runtime palette effect) | the Sonic 2 config's `charge_palettes` (abilities.charge_palettes) |
| `ui` | `life_icon`, `life_name`, `monitor_1up`, `sign_face` (a whole sign, or `{"head": ...}` on the official board: below), `mini_1`, `mini_2` | sheet2ani `ui` |
| `ending` | Sonic 1 ending poses: `end_idle`, `end_pose_1..3`, `good_1..6` | sheet2ani `ui` |
| `abilities` | the moves list and their numbers, with the same names as tools/abilities.py's docstring | ABILITIES entry; S3K / Mania JSON |

A palette that lists too few colours (an empty `own` with `other_colours` "nearest" draws every colour as the one
listed colour: a black silhouette) is an error in `noswap check` ("the game colours collapse"). The editor's Palette tab
has **Fill from sheet**: it proposes an own slot for every colour on the frames (exact colours only; a colour equal to
one of the base's slots 1-15 is shared; a cell-box colour gets none and goes to `sheet.background`), and when there are more colours than free slots it lists them with their
pixel counts for you to choose what each merges into. Nothing is merged without your choice.

How frames are written:
- **Animation frames:** a frame name, a raw rect, or `{"frame": NAME, "flip": true}`. Any sheet2ani frame dict (`rotate`, `circle`, `layers`, ...) also passes through.
- **Leaving out a neighbour's pixels:** `{"frame": NAME, "drop": [[x, y, w, h], ...]}` clears those sheet rects from the
  cut (a crop: a neighbouring sprite poking into the frame's box, as `noswap detect`'s boxes can overlap by a pixel or two).
- **Moving one use of a frame:** `{"frame": NAME, "offset": [dx, dy]}` (px; +x right, +y down). It moves that frame
  entry only (the same frame elsewhere keeps its place), after all the automatic placement: the anchor (feet / center),
  `anchor_box`, `align`, and the ground line the balls (Jumping, Spin Dash, Rolling) and the special stage ball are put
  on. Last, so `align` can't undo it; a `dy` on a ball moves it off its ground line. On a mirrored or turned frame, dx / dy
  are in the frame as drawn (as the game shows it facing right, which is what the editor's preview shows). Every build
  honours it: Sonic 1 / 2 / CD (sheet2ani.build_anims), S3&K and Mania (build_s3k_art; Mania builds through it), the
  editor's preview and `noswap preview`. The pixels are cut once whatever the offset (sheet2ani.frame_key leaves it out).
  The editor writes it when you drag a frame in the Animations preview; `[0, 0]` goes back to the plain name.
- **UI and ending elements:** `{"frame": NAME}` or `{"rect": [x, y, w, h]}`, plus `trim` and `remap`. `"remap": "+128"` moves colours 1-15 to 129-143, the UI sheets' palette row.
- **The HUD name tag (`ui.life_name`) is typed:** `{"text": "MICKEY"}`, or leave `life_name` out for the character's
  `name`. It is drawn in the HUD's own letters (tools/hud_font.py, Rayan C.'s Sonic 1 font: A-Z, 0-9, space and
  `· . , : ; ! ?`), exactly as the make_configs.py characters' `hud_font.tag(...)`, so S1/S2's Display, S3&K's HUD and
  every other consumer get it from the UI sheet as before. It must fit the 72 x 7 px room every package keeps for it
  (noswap_common.UI_RESERVE; Q , ; reach an 8th row): `noswap check` reports a tag that's too long or a letter the font
  doesn't have. `"pixel_colours"` changes its two colours (`{"f": letter, "1": shadow}`). A drawn tag is still a
  `frame` / `rect` ("use my own graphic" in the editor).
- **The signpost face (`ui.sign_face`):** either a whole sign drawn on your sheet, or a head that the build puts on the
  game's own signpost board (Sonic 1's Items2 Eggman board, cleared; `tools/sign_face.py` `board_face`, as the
  hand-made Big, Chaos, Jet... have). S1, S2 and CD (Items2), S3&K (the signpost's spin frames, `SignPost_Extra`) and
  Mania (its 40x24 face area on Mania's own board) all take it from the same UI sheet frame.
  - `{"head": FRAME_or_rect, "scale": "auto"}`: a head on the official board. The head is trimmed to its drawing
    (`"trim": false` keeps the rect), enlarged nearest-neighbour by `scale` (the user's signpost exception to the
    faithful-art rule: non-integer is allowed here only) and trimmed at the top / sides to the 40x24 face area (the chin
    stays). `"auto"` (the default) fills the 24-px height: 24 / height to 0.1, between 1 and 1.5, and no wider than 40 px
    if 1x fits (`sign_face.auto_scale`; the hand-picked boards agree for most: Mega Man 1.4, Marine 1.3, Mephiles and
    Emerl 1.1, Big 1.0). A number sets it (1 to 2). `"flip": true` mirrors the head left-right (a sheet drawn facing
    left, so the sign faces the way he does in game; Pulseman, Axel).
  - `{"frame": NAME}` / `{"rect": [...]}`: a whole 48x32 sign you drew (Bean's `GOAL_SIGN`), used exactly as drawn. If
    its drawing is smaller than 44x28 it is clearly a head, not a sign, and it goes on the official board as a head
    ("detected"; `noswap check` notes it). A frame with `remap`, `scale` or `"own": true` is always used as drawn
    (`"own": true` with a small drawing is a check warning: it floats with no board).
  - Left out: the top half of the Stopped frame's drawing (at most 24 rows) on the official board, `scale` auto (a
    check note says so; pick the head yourself for a better crop).
  - The editor's HUD tab has the switch ("Head on the official sign (automatic)" / "My own full sign graphic"), the
    head picker, the scale slider with "auto" and a live preview of the board as the game shows it.
- **Renamed names still load:** the Y attack that isn't a projectile was called `popgun` before 2026-10; it's `melee`
  now, and its fields too (`popgun_reach` is `melee_reach`, `popgun_cooldown` `melee_cooldown`...). An older file's
  names are migrated as it loads (tools/character_json.py `RENAMED` / `migrate_abilities`): it builds the same, `noswap
  check -v` notes each one ("renamed: popgun_reach is now melee_reach"), and the editor renames them on opening, so its
  Save writes the new names. Packages built with the old names keep working too (the Mania mod accepts the old move
  name; the S3&K fields never carried it).
- **The act results name** (S1/S2 title-card letters) is always the character's `name` in the games' own letters (A-Z
  and space, at most 192 px): `noswap check` reports a name they can't spell.

## Own sounds (`sounds`)

A character can ship its own sound files and play them for any move in **every game** (S3&K and Mania first; Sonic 1,
Sonic 2 and Sonic CD play the same move's own sound, below)
(tools/own_sounds.py):

```json
"sounds": {"grand_upper": "sfx/GrandUpper.wav"},
"abilities": {"melee_run": {"sfx_s3k": "own:grand_upper", "...": "..."}, "...": "..."}
```

- `sounds`: a name (lower-case letters, digits, `_`, up to 24) -> a file in the character's folder, in any format ffmpeg
  reads, up to 10 s. The build converts it to the engines' format (16-bit PCM, mono, 44.1 kHz).
- Any S3&K sound field (`*_sfx_s3k`, a `sfx_s3k` inside an object such as `melee_nuke`, `melee_run`, `melee_up` or
  `ninja_kariu`, a shot's `"s3k": {"sound": ...}`) takes `"own:<name>"` as well as the game's files
  (`"Global/Release.wav"`); Mania uses the same fields. In the editor, those fields offer the character's own names.
- The build writes them as `NoSwap/<id>/<name>.wav` (a Data/SoundFX path):
  - S3&K: in the package at `Sonic3ku/Data/SoundFX/NoSwap/<id>/`. Origins plays S3&K's sounds from its own CRI banks,
    never from files, so the DLL plays these itself (winmm, at the system volume; a new own sound cuts one still
    playing; the game's sounds go on).
  - Mania: `mods/NoSwapMania/Data/SoundFX/NoSwap/<id>/`, loaded at startup by `Data/Game/Game.xml` (a generated
    block). A separate download (crossover) ships its sounds and its own `Data/Game/Game.xml` in its mod.
- A character still written in Python (a make_configs.py one) puts the same `"sounds"` in its tools/abilities.py entry
  (Mario's fireball).
- `noswap check` reports a missing or unreadable file, a bad name, an `own:` name that isn't declared, and an `own:` in
  a field that isn't S3&K's.
- **Sonic 1, Sonic 2 and Sonic CD** play the same own sound for the same move, with nothing more to write: an
  `own:` in an S3&K field stands in for its Sonic 1/2 and CD counterparts, which keep the game's sound as the fallback
  (`melee_sfx` / `melee_sfx_cd` beside `melee_sfx_s3k`, `sfx` / `sfx_cd` beside `sfx_s3k`, a shot's `"v4"` / `"cd"`
  `"sound"` beside its `"s3k"` one; melee_run / melee_up's `sfx_s3k` replaces the melee's sound when that pose starts). A
  field with no Sonic 1/2 or CD counterpart keeps the game's sound there. At most 8 own sounds (the first 8 by name) play
  there.
  - How: Origins plays those games' sounds from its CRI banks too, so the DLL plays the package's S3&K copy (no other
    files ship). The player script asks through a global no Origins script of that game uses (Sonic 1/2
    `game.callbackParam2`, Sonic CD `Leaderboard.Offset`): it writes a number at startup that the DLL finds and answers
    when every file the package's noswap_character.json `"own_sounds"` lists is there; a move's sound then sets a bit
    the DLL plays and clears. No answer (a missing file, an older DLL): the move plays the game's sound, as before.
  - Only the player scripts of characters with own sounds change; everyone else's are untouched.

## Fallback frames

An animation the base character has frames for and yours leaves out borrows a similar one you did draw, so the game
never shows nothing there. `tools/anim_fallbacks.py` holds an ordered chain per Sonic 1 / Sonic 2 animation name; the
first animation in the chain that has your own frames is used. Some of them:

| missing | uses the first of |
|---|---|
| Pushing | Walking, Stopped |
| Breathing | Bouncing, Jumping |
| Hanging / Clinging On | each other, Bouncing, Stopped |
| Fan Rotate, Corkscrew H, Twirl H | Twirl H / Corkscrew H, Walking |
| Flailing 1 / 2 / 3 | the other Flailings, Hurt |
| Water Slide | Sliding, Looking Down, Stopped |
| Grabbed | Hurt |
| Super Transform | Continue Up, Looking Up, Stopped |
| Continue / Continue Up | Waiting, Bored!, Stopped / Looking Up, Bouncing, Stopped |
| Spin Dash | Rolling (ability slot 49), Jumping |
| Super Peel Out | Running, Walking |
| Sonic 1's Special Stage | Jumping (centred), Rolling, Spin Dash |

The chains follow what the hand-made characters reuse when their sheets lack a pose (25 use Hurt for Grabbed, 21
Bouncing for Hanging, 29 Running for Super Peel Out...). The plans' S3&K / Mania names have their Sonic 1 / 2
equivalents here: Air Walk is Bouncing, Victory is Continue Up, Bored 1 is Waiting, Ducking is Looking Down.

- **What is copied:** the source's frames (with their offsets), its `anchor` and `align`. The speed, loop, rotation
  and hitbox stay the base's own for that animation. A chain only names animations you drew yourself (never another
  fallback), and every chain ends in a pose everyone has.
- **Where:** at config time (`character_json.config`), into the Sonic 1 and Sonic 2 configs, so every game gets it:
  Sonic CD (`cd_config.py`'s own stand-ins for its 3D Ramps and so on), S3&K and Mania (`build_s3k_art.FROM_S2` maps
  their names onto the filled Sonic 2 set) are all built from those configs.
- **Opting out:** `"Pushing": null` in `animations` (or `animations_sonic2`, `special_stage`) leaves it deliberately
  empty in Sonic 1, 2 and CD. S3&K and Mania never leave a slot empty: there it shows the standing frame.
- **The check** notes each fallback ("Pushing uses Walking"). It warns only when nothing in the chain is there.
- **The editor** shows a missing slot as "uses Walking (fallback)" with those frames greyed out. **Make my own** copies
  them in for you to edit.
- Only character.json characters get fallbacks. The old make_configs.py characters are unchanged.

## The generic spin ball (`ball`)

A sheet with no spin ball can use the generic one: Sonic Mania's plain spin ball (SEGA's frames,
`testmods/_shared/mania_ball.png`), mapped by index to five of your own colours. It is built exactly as Bomb's and
Chaos's are (`tools/generic_ball.py`): its frames go in a strip under a working copy of your sheet
(`build/<id>_ball.png`; the sheet itself is untouched), each of its 2 frames shown twice, S3&K's own frame counts
(Jump 8, Spindash 10), CD's names, and Mania through the S3&K build.

```json
"ball": {"size": "medium", "colours": "auto", "use_for": ["Spin Dash"]}
```

- `size`: `small` (24 px, Bomb's), `medium` (30 px, the ball as ripped; the default) or `large` (40 px, Big's). The other
  sizes are nearest-neighbour resizes of the same pixels (the approved exception).
- `colours`: `"auto"` (the default) picks them from your palette: your most used colour (near-whites left out) is the
  body; its darkest, most used and lightest shades are dark / mid / light; the outline is the next darker shade of
  that hue you have (`generic_ball.outline_for`; the dark shade when there is none, never black unless the body is);
  the shine is your lightest colour. A grey or black body takes your greyish colours for the lit side. Or give them:
  `{"outline", "dark", "mid", "light", "shine"}` as `"#rrggbb"`. dark, mid and light are required; a left-out outline
  is `outline_for(dark)` and a left-out shine your lightest colour. Use your palette's own colours: any other is drawn
  as the nearest one (the check warns).
- `use_for`: any of `Spin Dash` (the default), `Jumping`, `Rolling`, `Special Stage`.
  - `Jumping` makes the ball your jump, and the jump is your attack, so the attack looks like a spin ball. It also
    makes the ball the Sonic 2, CD and S3&K special stages' runner.
  - `Rolling` puts the ball in ability slot 49 and turns `flags.roll` on: rolling shows the ball while the jump keeps
    your own pose, and the Sonic 2, CD and S3&K special stages use it.
  - `Special Stage` is Sonic 1's special stage only. Without `Jumping` or `Rolling`, the other games' special stages
    show your Jumping frames.
  - The ball replaces your own frames in the animations it is used for.
- **The check** validates it: size, names and colours against the schema, colours outside your palette, a ball for
  Spin Dash / Rolling with `no_roll`, and what auto picked.
- **No stomp (abilities `no_stomp`):** the jump isn't an attack and the slide is (docs/abilities.md, No Stomp). Give
  `Jumping` your own jump pose (not the ball), a slide pose as `ability_animations` `"49": {"name": "Rolling", ...}`
  with `flags.roll` true (rolling and the Spin Dash's release show it), a low pose for `Spin Dash` (the charge), and keep
  the ball for `Special Stage` only: the Sonic 2, CD and S3&K special stages then show your jump pose. Joe Musashi, Axel
  and Gilius are examples. The check warns about a ball jump or roll, or no slide at all.
- **The editor's Ball panel** (Animations tab) has the size buttons, the colours picked from your palette, a live
  preview in the game's colours and the `use_for` checkboxes. The slots it fills say "generic ball".
- **Public split:** `testmods/_shared/mania_ball.png` is outside git (testmods/ is gitignored), so a public toolset
  must ship it, or extract it from the user's own Mania data (Sonic1.gif (153,81) and (186,81)), with the toolset.

## Wiring: nothing to register (toolset step 4)

A folder with a `character.json` is all a build needs. No central list is edited:
- **Found by itself:** `character_json.folders()` finds every `testmods/*/character.json`, plus the folders in
  `$NOSWAP_CHARACTER_DIRS` (`os.pathsep`-separated: a character folder, or a folder of them). `tools/extras.py` adds each
  to EXTRAS (`extras_entry`), `tools/abilities.py` adds its moves (`abilities_entry`) under its build ID, and
  `tools/build_mania_art.py` builds it for Mania when `games.mania` is true.
- **Numbered by key:** `tools/registry.py` keeps `data/registry.json`, key -> n. The build ID is 6 + n, the art files
  are `Extra<n>...`, and Mania's save select sorts by n. Today's 43 characters are frozen at the numbers their old
  place in EXTRAS gave them. A new key gets the highest number ever given + 1, written to the file on the first build
  (or `check`), and is never reused. `python3 tools/registry.py` lists it. `--forget KEY` removes a key that was never
  released (a test).
- **No clashes between strangers:** the numbers are build-time only, local to one build tree. The games number installed
  packages themselves: the S3&K DLL gives Origins kinds by key (`roster.json`), and Mania stores save-slot picks by
  package folder. Only the key must be unique.
- **Known clash (Mania): the folder name must be unique too.** Mania saves the picked character by package folder name
  (`id`), not by key, and when two installed mods ship the same folder name the first in the loader's priority order
  wins and the other is silently hidden. Two strangers' "bliver" folders collide even with different keys. Pick a
  distinctive `id` (e.g. `<creator>-<character>`). Changing Mania to store keys would break existing Mania saves, so
  this is left as is. Planned: detect duplicate folders at startup and show a clear "conflicting characters
  installed" message instead of hiding one.
- **Release:** `make_release.py` takes the title from `full_name` when CHARACTERS has no entry. Such a character is a
  separate download, never in the all-in-one. Its README section in `mods/NoSwap/README.md` is still written by hand.
- `make_configs.py` shims (Bean, Espio, Vector, Fang) are optional. `noswap build` writes the configs itself when
  there is none.

## Tools

- `docs/character.schema.json`: the file's JSON Schema.
- `tools/noswap.py check | preview | build | convert`: see docs/toolset-cli.md.
- Espio, Vector and Fang were converted with `noswap convert --wire` and are wired the same way as Bean.
- `sheet.angled_halves` may be left out, which means false; the config then has no such key, as the old ones didn't.

## Not in the file yet (still Python or central)

- **Per-character Python tricks** that other characters use: generated or composited frames (Tails Doll's layered tails, Emerl's copy heads, decheese), `card` crops from build intermediates, and MANIA_OVERRIDES. (The generic ball is in now: `ball`.)
- **The prose:** SOURCE.txt and the README credits.
