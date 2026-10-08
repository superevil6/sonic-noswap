# The character editor (`noswap ui`)

A desktop front end over the `noswap` tools (docs/toolset-cli.md): make or edit a character without touching JSON or a
terminal. It edits `character.json` (docs/character-json.md) and runs the same check, preview and build code as the
command line. It copies into the games only when you press **Deploy** (Build & deploy tab).

## Starting it

```
python3 tools/noswap.py ui                 # pick a character in the window
python3 tools/noswap.py ui bean            # open one (a folder name under testmods/, or a path)
python3 tools/noswap.py ui bean --browser  # in your web browser even if pywebview is installed
```

Options: `--port N` (default: any free port), `--no-open` (print the address, don't open a browser), `--lock FILE`
(the build lock the Build button takes; default `$NOSWAP_BUILD_LOCK`, else `<temp dir>/noswap-build.lock`).

It works two ways, from the same code:

- **A desktop window**, when [pywebview](https://pywebview.flowrl.com/) is installed.
- **Your browser** otherwise (or with `--browser`). The page is served from `127.0.0.1` only, and a random token in its
  address guards the API against other web pages. Stop it with Ctrl+C in the terminal.

Unsaved edits are never lost on quitting: they're written to `<temp dir>/noswap-ui/backups/<id>/unsaved-*.json`, and the
terminal says where.

### Installing pywebview (optional)

Use a virtual environment, so nothing is installed system-wide:

```
python3 -m venv ~/.venvs/noswap
~/.venvs/noswap/bin/pip install pywebview pillow
~/.venvs/noswap/bin/python tools/noswap.py ui
```

pywebview needs a GUI backend:
- **Linux, Qt** (KDE, or anywhere PyQt is easy): `~/.venvs/noswap/bin/pip install "pywebview[qt]"` (PyQt6 and
  QtWebEngine). Or make the venv with `python3 -m venv --system-site-packages ...` to reuse the system PyQt6.
- **Linux, GTK** (GNOME): `pip install "pywebview[gtk]"`; it needs the system's PyGObject and WebKitGTK
  (`python-gobject` and `webkit2gtk-4.1` on Arch). `--system-site-packages` lets the venv see PyGObject.
- **Windows** uses Edge WebView2 and **macOS** WebKit: `pip install pywebview` is enough.

The tools also need Pillow (the venv line above installs it).

**Blank page, or Open… does nothing?** The page's scripts were blocked. Content blockers (uBlock Origin, NoScript and
the like) can block scripts on 127.0.0.1: allow scripts for it there, or open the address in another browser, or use
the desktop window (pywebview), which has no add-ons. The page shows "Starting the editor…" until its scripts run.

## The screens

The top bar opens a character (**Open…**: every character the build finds, or any folder), makes one (**New…**),
**Save**s (Ctrl+S) and **Revert**s. The dot next to the name means unsaved changes. Alt+1 ... Alt+8 switch tabs.

- **Character:** identity (key, name, base), credits and the sheet's terms, the sheet's settings, physics (sliders:
  multipliers on Sonic's), the games and the flags. The forms are made from docs/character.schema.json: its
  descriptions are the hints.
- **Sheet & frames:** the sheet at a whole-number zoom with crisp pixels and every frame's rectangle (blue: used, grey:
  unused, red: empty or outside the sheet). Click one to edit it in the inspector: x, y, w, h, the drawn part the build
  keeps after trimming (dotted), the ground line and the object's position (where the game puts the frame), a preview
  in the game's colours (or the sheet's), and where it's used. Drag a frame to move it, drag an edge to resize it,
  arrows nudge (shift+arrows resize), **F** fits the box to the drawing, **[ ]** go to the previous / next frame.
  **Draw frame (R)**: drag around a sprite; the box is fitted to the drawing (a crop: nothing is redrawn) and named
  FRAME<n> for you to rename (every use follows the rename). Alt-click reads a colour.
  **Detect frames (D)** finds the sprites for you (see below).
- **Animations:** every animation on the base character's lists (with how many frames each has, and a red "empty" where
  the game would show nothing), the ability slots, the Sonic 1 special stage and the S3&K act clear. An animation's
  frames are thumbnails: reorder, mirror, remove, add. Its options (anchor, loop, speed, rotation, hold, hitbox, align)
  have the template's values as placeholders. The preview plays it with each frame placed as the build places it
  (sheet2ani.build_anims: on the ground line or centred, align, hold), at the game's speed or one you pick, with onion
  skin and frame stepping (space, arrow keys). It says whether it shows the **game colours** or the sheet's (a toggle),
  and warns when the game colours collapse into a silhouette. **Moving a frame:** drag the sprite in the preview (whole
  px at any zoom), or click the preview and use the arrow keys (shift: 8 px; `,` and `.` step frames then); the dx / dy
  boxes and Reset under it edit the same thing, and "move all frames together" shifts the whole animation. It's saved
  as that frame entry's `"offset": [dx, dy]` (docs/character-json.md), applied after the anchor, align and the balls'
  ground line; onion skin shows the previous frame to line it up against.
- **Abilities:** his moves from the ability registry (docs/abilities.md): description, per-game badges (S1 S2 CD 3K MA:
  green works, amber partly, grey not there yet), the fields with their units (speeds show px a frame), the animation
  slots each move draws and whether they have frames, and the rules on combining moves. **Add a move…** opens a picker:
  search, filter by kind or by "works in all his games", and see what adding it would clash with before adding. Adding
  fills only the fields the move needs, with the values of the one character the registry takes its example from (the
  move's own minimal entry, known to work); every option starts off (left out) and is switched on here. Removing a move
  drops the fields only it reads. Per-frame fields are edited on the frames (the **hit-box panel**, below).

- **Palette:** his own colours in slots 74-95 (colour pickers), the colours shared with the base, and a table of every
  colour his frames use with what the game draws it as (merged colours are highlighted, with a button to give one its
  own slot). **Fill from sheet…** proposes a slot for every colour on his frames, most pixels first (a base colour
  shared, the rest own slots), shows it before anything changes, warns past Mania's 13 own slots, and when there are
  more colours than free slots lists the rest with pixel counts to merge only into colours you pick (exact colours
  only: nothing is recoloured). A red banner says so when the game colours collapse.
- **HUD & ending:** the six HUD pieces and Sonic 1's ending poses, each a frame or a rect, with previews and size hints.
  The name tag is typed: a text box (his name when empty), a live preview in the HUD's letters and an "N px of 72"
  counter; "use my own graphic" switches it to a frame or rect.
- **Build & deploy:** two cards over one streamed log (with **Stop**).
  - **Build:** pick the games and run `noswap build` (the check first; Origins under the build lock; then Mania).
    "dry run" only prints the steps. It builds the saved file.
  - **Deploy to the games:** tick Sonic Origins and/or Sonic Mania (each shows its folder, a ✓ or what's wrong, and
    where the folder came from) and press **Deploy**: `noswap deploy` (docs/toolset-cli.md): Origins gets mods/NoSwap
    mirrored into HedgeModManager's mods folder, Mania gets mods/NoSwapMania symlinked and enabled. It works with no
    character open (it copies what's built). **Build & deploy** builds the open character for the ticked games
    (Origins: all four; Mania) and then deploys them, and only if the build succeeded: a failed build deploys nothing.
    "dry run" makes both only say what they'd do. A running game shows a banner, and the log ends with "restart the
    game: the DLL / scripts load at startup" (the deploy still happens).
- **Settings:** the two folders deploy uses, Origins' mods folder and the Mania decomp's play folder. Each shows the
  one in use and where it came from (set, or detected), checks what you type as you type (Origins: SonicOrigins.exe
  next to it or HedgeModManager's ModsDB.ini in it, and whether NoSwap is enabled there; Mania: RSDKv5U and
  Data.rsdk), and lists everything detection found on this machine (Steam's libraries, ~/Code/mania/run) with a
  **Use** button. **Save** keeps a folder in your settings file (`~/.config/noswap/settings.json` or the Windows / macOS
  equivalent, never the repo); **Use detected** forgets it. A running game is shown here too.

The **Check** panel on the right runs `noswap check` on the saved file after each save, or with **Run**; each
finding links to the place it's about. ⇥ folds it away.

### The hit-box panel

A move with per-frame fields (abilities_registry.PER_FRAME_GROUPS: the melee's reach / top / bottom on the ground,
slot 43, and in the air, slot 44; the Ear Grapple's tip, slot 41) shows them drawn on its frames instead of rows of
numbers. One panel per move, with a switch (**On the ground** / **In the air**).

- **The frame** is placed as the game places it (the Animations preview's placement), he faces right, and the box is
  drawn as the game computes it. Pick the game with **as in**:
  - **Sonic 1 / 2**: from 10 px behind his centre to `reach` ahead, `top` to `bottom` (px from his centre); mirrored
    when he faces left (tools/abilities.py, NoSwap_MeleeMove). melee_radial: `reach` all round him.
  - **Sonic 3&K / Mania**: the same box (it's the pose frame's box, tools/build_s3k_art.py), but a reach under 10
    counts as 10. Without melee_air_reach these games show the ground move (slot 43) in the air too.
  - **Sonic CD**: doesn't read the numbers. Its Y move (slot 46 there: the ground frames, in the air too) hits with his
    own body box (10 px either side, 20 above and below), plus a reach only for the extras build_soniccd.SHOT_OUT
    gives one. Shown for information, not editable.
- **Drag** the yellow handles: the front edge (reach), the top and the bottom; whole px, one edit when you let go. A
  point (the ear's tip) is dragged, or put where you click.
- **The strip** under it has every frame with its box, small: click one to edit it.
- **Fit to sprite** (this frame) and **Fit all frames**: the front edge on the furthest drawn pixel ahead of his
  centre, the top and bottom on the drawing's (a point: the drawn pixel furthest up and forward).
  **Same box on all frames** copies this frame's box to the rest; **Copy ground → air** / **Copy air → ground** copy
  frame by frame (a longer move repeats the last). Without melee_air_reach the air move uses the ground box, as the
  games do; dragging, fitting or copying gives it its own, and **Use the ground box** goes back.
- **No "no hit" frame**: the games count the whole move as an attack, every frame hits, and the box always reaches
  back to 10 px behind his centre. A frame that shouldn't reach out: pull its front edge back to his body.
- **Play the move** plays it at game speed (melee_ticks game frames a frame; the ear one a game frame) with the box
  flashing while it hits.
- **Advanced** has the numbers in words, still editable ("reaches 10 px ahead · from 20 px above to 20 px below his
  centre"), and the lists as saved. A list that's out of step says so there with a "Fit to N frames" button, and
  `noswap check` reports it as an error (the build would stop or cut the move short).
- The lists follow the slot's frames: removing, adding or moving a frame on the Animations tab removes, copies or
  moves its value. Saving goes through the minimal-text save; a top / bottom list that would be all its default
  stays left out.

A new per-frame group only needs an entry in PER_FRAME_GROUPS (its move, slot, shape "box" or "point", fields,
defaults, the back edge and the per-engine minimum reach, the timing field).

### Detect frames

**Detect frames (D)** on the Sheet tab finds the sprites on the sheet and shows them as dashed proposals, each box
trimmed tight to its drawing (the same boxes **F** would fit), named ROW<row>_<n> in reading order. It's the same code as
`noswap detect` (docs/toolset-cli.md): the pieces of non-background pixels, with small bits (sparks, sweat drops, a
detached hand, a held item) joined to the nearest bigger body within the **merge** distance; cell boxes in a colour of
their own count as background, so the sprite inside a box is found, not the box. Nothing on the sheet or in your frames
changes until you accept.

- Pink: a sprite; orange: a small lone piece (an effect, an icon). Proposals over a frame you already have are hidden
  ("on existing frames" shows them, labelled "= NAME"); so are text (labels, titles, credits), lines (underlines, label
  brackets, box outlines) and specks ("text, lines, specks"). The counts say how many of each are hidden.
- **merge** and **min size** re-detect as you drag them. Drag on an empty part of the sheet to look only inside that
  area (Esc or **Whole sheet** goes back). Alt-click a colour to treat it as background too (for this search; **Add to
  the sheet's background** saves it in `sheet.background`).
- Click a proposal to select it (shift-click adds, ctrl+A all), double-click accepts one. **Accept selected** (Enter),
  **Accept all**, **Reject** (Delete), **Split** (S: a box cut into its separate pieces) and **Merge** (M: one box around
  the selected ones). **names**: empty keeps ROW<row>_<n>; a prefix such as WALK names them WALK1, WALK2, ...
- Accepting adds the frames in one edit; rename them in the frame inspector as usual (every use follows). **Remove the
  N just added** takes the last batch back out (it asks first if one is used already); Revert throws away every unsaved
  edit.

## Saving

Save edits the file's own text as little as possible (tools/noswap_ui/jsontext.py): a changed value is replaced where it
stands, a new key goes after the last entry in the same layout, a removed one is cut out with its comma, a renamed key
keeps its place. So a hand-laid-out file (Bean's: several frames to a line, blank lines between sections) keeps its
layout, comments (`_` keys) and key order, and a diff shows only what changed. Anything it can't edit in place is
written in the converted characters' style (noswap_cli.convert.pretty), and the result is always re-read and compared
with what you meant before it's written.

Older names are renamed as a file opens (character_json.migrate_abilities: `popgun_reach` is now `melee_reach`...):
a message lists them, the file shows as changed, and Save writes the new names in the old ones' places.

The first save in a session copies the file as it was to `<temp dir>/noswap-ui/backups/<id>/`. If the file changed on
disk since it was opened (another editor), Save asks before overwriting.

## How it's built

- `tools/noswap_ui/backend.py`: one class, `Backend`, whose public methods are the API (open, edit, save, check,
  frames_info, fit_rect, detect_frames, frame_image, animation, sheet_colours, registry, per_frame_info, ability_rules, add_ability, remove_ability,
  new_character, ls, build, build_log, deploy_settings, check_folder, set_deploy_settings, deploy, build_deploy,
  ...). It calls the existing modules: `noswap_cli.check`, `noswap_cli.preview`
  (its Cutter: sheet2ani's own cut functions and the game's colours), `sheet2ani.build_anims` (placement),
  `abilities_registry`, `character_json`, `noswap_cli.deploy` (settings, detection, checks), and `tools/noswap.py
  build` / `deploy` (subprocesses, run one after another, stopping at the first failure) for builds and deploys.
- `tools/noswap_ui/server.py`: the HTTP server (stdlib `http.server`, 127.0.0.1 only): `POST /api/<method>` with JSON
  arguments, `GET /sheet` for the sheet image, and the static files; the pywebview window just shows that page.
- `tools/noswap_ui/web/`: the page, plain HTML, CSS and JavaScript modules (no build step, no external fonts or CDN).
- `tools/noswap_ui/new_character.json`: the template a new character starts from (Bean's layout, emptied).

Edits are sent as small operations (`{"op": "set" | "del" | "rename", "path": [...]}`) applied to the document held
in Python, so unknown keys and comments are never lost or reordered.

## Not done yet

- A custom select card (`card`) and the shot's art are edited as JSON for now; there's no shot-art picker on the sheet.
- melee_whip's poses (crouching, up-forward, down: per-frame boxes inside one object) are edited as JSON, not on the
  hit-box panel.
- Layered frames (`layers`) show and preview but can't be built in the editor.
- No undo beyond Revert (the backups folder keeps each session's first version).
- Frames can't be dragged from the sheet into an animation yet: pick them from the list, or use the "+ NAME" button,
  which adds the frame selected on the Sheet tab.
