# character.json: your character, field by field

Each character is one folder in your characters folder (`<data folder>/characters/<id>/`, see the README's "Where
things are") holding its sprite sheet and a `character.json`. The editor writes the file for you; this page explains
what is in it, for when you want to know what a field does or edit it by hand.

Two general rules:
- **Comments:** any key that starts with `_` is a comment. The build ignores it.
- **Fixed-point numbers:** anywhere a number goes, you may write a hex string such as `"0x30000"` or `"-0x20000"`. Speeds
  are 16.16 fixed point: `0x10000` is 1 px per frame.

`NoSwapCreator check <character>` (or the editor's Check panel) validates everything below and says how to fix each
problem.

## Before you start: names, key and id

- **Pick a character NoSwap doesn't have yet**, or at least a different name: `docs/roster.md` lists the characters
  NoSwap already ships. Two characters with the same name in someone's game are confusing.
- **`key`** is your character's permanent identity: `<you>.<character>` in lower case, e.g. `"someone.metal-tails"`. Saves
  and character picks are stored under it. Choose it once and never change it after you share the character.
- **`id`** is the folder's name, lower case letters, digits and `-`. It must be unique too: Sonic Mania stores the picked
  character by this folder name, and when two installed characters have the same folder, only one of them shows. Make
  it distinctive, e.g. `someone-metal-tails` rather than `tails`.

## Fields

| key | what it is |
|---|---|
| `format` | always `"noswap-character/1"` |
| `id` | the folder's name (above) |
| `key` | the permanent key (above) |
| `name` | the in-game name, in capitals (the act results, the HUD name tag) |
| `full_name` | the readable name, used in your mod's title and README |
| `credits.short` | the line under the Origins select card (about 32 characters at most) |
| `credits.full` | the full credit for the sprite artist |
| `credits.artists`, `credits.url`, `credits.terms` | who drew the sheet, where it's from, and its terms word for word. They go into your mod's README |
| `sheet.file` | the sprite sheet, in this folder |
| `sheet.background` | the sheet's empty colours: its background, **and the colour of any boxes drawn around the sprites** (below) |
| `sheet.feet_y` | how far below a frame's centre his feet are (the editor's ground line) |
| `sheet.angled_halves` | `true` when the walk and run lists are upright frames followed by the same frames turned 45° |
| `base` | `"sonic"`, `"tails"` or `"knuckles"`: the physics, animation list and jump-button move he plays with (below) |
| `flags` | `super`: his Super form uses Sonic's Super palette; `drop_dash`: Sonic's drop dash; `roll`: rolling shows his own Rolling animation (slot 49) instead of the jump's; `no_roll`: no rolling at all. (`private` and `crossover` are NoSwap's own release switches: leave them `false`) |
| `card` | the Origins select card: `null` uses his Stopped frame at 8x |
| `games` | `sonic1`, `sonic2`, `soniccd`, `s3k`, `mania`: `mania: false` leaves Mania out; the Origins games are always built together |
| `palette.own` | `{slot: "#rrggbb"}`: his own colours, in slots 74-95 |
| `palette.shared` | `{"#rrggbb": slot}`: sheet colours that are exactly one of the base character's colours (slots 1-15) |
| `palette.other_colours` | `"nearest"`: any colour not listed is drawn as the nearest listed one; `"guess"`: the nearest of slots 1-15 and the listed ones |
| `palette.strict` | `true` stops the build if a frame has a colour that isn't listed (for sheets whose terms say "do not edit") |
| `frames` | `{NAME: [x, y, w, h]}`: named rectangles on the sheet |
| `animations` | `{animation: {frames: [NAME, ...], anchor?, align?, loop?, rot?, speed?, hitbox?, hold?}}`: the base character's animations (Sonic 1's list) |
| `animations_sonic2` | the animations only Sonic 2's list has (Sonic CD and S3&K are built from the Sonic 2 set) |
| `ability_animations` | the move slots: `{"41": {name, frames, ...}}`. 41 the jump ability, 42 hover, 43 / 44 the Y move on the ground / in the air, 45 / 46 aimed moves, 47 / 48 glide up / down or cling, 49 roll. Each move says which slots it draws (`docs/abilities.md`) |
| `special_stage` | Sonic 1's special stage animations (left out: a fallback, below) |
| `ball` | the generic spin ball (below) |
| `s3k_victory` | the S3&K act clear pose: `{frames, pose?}` |
| `snowboard` | S3&K Ice Cap's snowboard intro (Sonic-based characters): `{"ground": [...], "air": [...], "sidewind": [...]}` |
| `ui` | the HUD pieces: `life_icon`, `life_name`, `monitor_1up`, `sign_face`, `mini_1`, `mini_2` (below) |
| `ending` | Sonic 1's ending: `end_idle`, `end_pose_1..3`, `good_1..6` (below) |
| `abilities` | his moves and their numbers: `{"abilities": [move, ...], field: value, ...}` (`docs/abilities.md`) |

### Writing frames

- **In an animation:** a frame name, a raw `[x, y, w, h]`, or `{"frame": NAME, "flip": true}` (mirrored). Frames may
  also be turned (`"rotate"`).
- **Moving one use of a frame:** `{"frame": NAME, "offset": [dx, dy]}` (px; +x right, +y down). It moves that one use,
  after all the automatic placement (the feet on the ground line, the balls centred), in every game. The editor writes
  it when you drag a frame in the Animations preview.
- **HUD and ending pieces:** `{"frame": NAME}` or `{"rect": [x, y, w, h]}`, plus `"trim": false` (keep the empty edges)
  and `"remap": "+128"` (below).

## Cell boxes on the sheet

Many sheets draw a coloured box around each sprite. That box colour is **not** part of the character: put it in
`sheet.background` next to the sheet's background colour, e.g. `"background": ["#25661a", "#0d4807"]`. Otherwise the
game draws a box behind every frame.

- **Detect frames** finds such boxes ("cell fills") and puts their colour in the background when you accept frames (or
  press *Add the box colour to the background*). `NoSwapCreator detect` prints the line to paste.
- **Fill from sheet** never gives a box colour a palette slot, and its Apply moves it to the background.
- **Check** warns when a colour that fills boxes behind the frames is in the palette or is drawn.

## The base character, and moves on the jump button

`base` decides which of Origins' characters yours plays as underneath:

| base | physics | on the jump button in mid-air |
|---|---|---|
| `sonic` | Sonic's | Sonic's own moves (insta-shield, drop dash...), or **your jump ability** |
| `tails` | Sonic's | **Tails' flight**, always (his tails aren't drawn: your Flying frames are) |
| `knuckles` | Knuckles' (a lower jump) | **Knuckles' glide and climb**, always |

A Tails or Knuckles base keeps its flight or glide on the jump button, so **a move that starts by pressing jump again in
mid-air (a jump ability: jet_dash, double_jump, hammer_drop, ray_glide...) needs base `sonic`**. With a Tails or
Knuckles base, Check stops with the rule `base-keeps-jump`, and the editor's move picker says so before you add one.
Moves started with **Y** work with any base, and so do ground moves and settings. `aim_dash` with `aim_dash_y` is the
way to have both: Y fires the dash, jump keeps Tails' flight (NoSwap's Charmy). `docs/abilities.md` lists which moves
are on the jump button.

Every move's page in `docs/abilities.md` (or `NoSwapCreator abilities <move>`) says what it does, its fields, the
animation slots it draws, which games have it, and what it can't be combined with.

## The palette

His colours must be listed, or the game draws them as the nearest listed colour. The editor's **Fill from sheet**
(Palette tab) does it: every colour on his frames gets one of his own slots (74-95), or the base character's slot when
it is exactly the same colour. Nothing is ever recoloured: when there are more colours than free slots, it lists them
with their pixel counts and you choose what each one merges into. Check reports an error when his colours collapse
into a few (he'd be a flat silhouette in game). Sonic Mania has 13 free slots: past that, the rarest colours there use
the nearest Mania colour.

## HUD and ending pieces

| piece | where it shows | size |
|---|---|---|
| `life_icon` | the lives counter (all games), and Mania's save select | 16x16 |
| `life_name` | the name next to the lives icon | 72x7 |
| `monitor_1up` | the 1-UP monitor's picture | 16x14 |
| `sign_face` | the end-of-act signpost (below) | head up to 40x24, or a whole 48x32 sign |
| `mini_1`, `mini_2` | the small foot-tapping icon: the continue screen and the continues on results screens (below) | about 16x23, like Sonic's |
| `end_idle`, `end_pose_1..3` | Sonic 1's ending: standing, then the small, medium and large poses | as drawn |
| `good_1..6` | Sonic 1's good ending: six frames of him | as drawn |

**`mini_1` and `mini_2`** are two frames of a small standing figure, shown one after the other so he taps his foot.
They appear on the continue screen (Sonic 1 and 2), as one icon per continue earned on the results screens (Sonic 1's
special stage, Sonic 2's acts, Sonic CD's special stage), and Mania's save select shows `mini_1` for a file's continues.
Crop two standing frames of about 16x23 px (a head-and-shoulders crop works too).

![Where mini_1 and mini_2 show](../screenshots/mini-icons.png)

**`"remap": "+128"`** moves his base colours (slots 1-15) to slots 129-143. The sheets the mini icons and Sonic 1's
ending are drawn from keep the player's colours there, so:

| use `"remap": "+128"` on | don't use it on |
|---|---|
| `mini_1`, `mini_2`, `end_idle`, `end_pose_1..3`, `good_1..6` | `life_icon`, `life_name`, `monitor_1up`, `sign_face` |

His own colours (slots 74-95) aren't affected either way.

**The name tag (`life_name`) is typed:** `{"text": "METAL TAILS"}` (or left out: his `name`). It's drawn in the HUD's own
letters (Rayan C.'s Sonic 1 font: A-Z, 0-9, space and `· . , : ; ! ?`) and must fit 72x7 px: Check says when it's too
long. A drawn tag is a `frame` / `rect` instead ("use my own graphic" in the editor).

**The signpost (`sign_face`):**
- `{"head": FRAME_or_rect, "scale": "auto"}`: his head on the game's own signpost board. It's trimmed to the drawing,
  enlarged nearest-neighbour by `scale` ("auto" fills the 24-px height, 1 to 1.5x; or a number from 1 to 2) and cut at
  the top and sides to the 40x24 face area.
- `{"frame": NAME}` / `{"rect": [...]}`: a whole 48x32 sign you drew, used as drawn.
- Left out: the top of his Stopped frame on the official board (Check notes it; pick the head yourself for a better crop).

**The act results name** (Sonic 1 and 2's title-card letters) is always his `name`: A-Z and space, at most 192 px.

## Fallback frames

An animation you leave out borrows a similar one you did draw, so the game never shows nothing. Some of them:

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

Check notes each fallback ("Pushing uses Walking"). The editor shows a missing animation as "uses Walking (fallback)";
**Make my own** copies the frames in for you to change. `"Pushing": null` leaves one deliberately empty in Sonic 1, 2
and CD (S3&K and Mania show the standing frame there).

## The generic spin ball (`ball`)

A sheet with no spin ball can use a generic one: Sonic Mania's plain spin ball in five of his colours. It's cut from your
own Sonic Mania data at Set up, so it needs Set up with Mania.

```json
"ball": {"size": "medium", "colours": "auto", "use_for": ["Spin Dash"]}
```

- `size`: `small` (24 px), `medium` (30 px) or `large` (40 px).
- `colours`: `"auto"` picks them from his palette, or `{"outline", "dark", "mid", "light", "shine"}` as `"#rrggbb"`
  (dark, mid and light required). Use his palette's own colours.
- `use_for`: any of `Spin Dash` (the default), `Jumping` (the ball is his jump, and the special stages' runner),
  `Rolling` (slot 49: rolling shows the ball while the jump keeps his own pose) and `Special Stage` (Sonic 1's).
- The editor's Ball panel (Animations tab) has all of it with a live preview.

## Sharing and updating

What Build makes in `output/<id>/` is ready to share (the README says how). When NoSwap updates, get the matching kit
and Build again: `character.json` carries over as it is.

## Not in the file yet

- Frames made from several pieces of the sheet (`layers`) show and preview, but the editor can't make them.
- A hand-drawn select card (`card`) is written by hand: `{sheet, rect, scale, background, pivot?, baseline?}`.
- New moves are NoSwap core work: the kit offers the moves NoSwap has.
