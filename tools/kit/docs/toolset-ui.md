# The character editor

The kit's editor makes or edits a character without touching JSON: it writes your `character.json`
(`docs/character-json.md`) and runs the same check, preview and build as the command line. It copies into your games
only when you press **Deploy**.

## Starting it

- **Windows:** `NoSwapCreator.exe`. It opens in its own window (Microsoft Edge WebView2), or in your web browser when
  WebView2 isn't there.
- **Linux:** `./NoSwapCreator.sh`. It opens in your web browser; stop it with Ctrl+C in the terminal.
- `NoSwapCreator --browser` always uses the browser, `--no-open` only prints the address, `--port N` picks the port.
  `NoSwapCreator ui <character>` opens that character straight away.

In the browser the page is served from `127.0.0.1` only (your own computer), and a random token in its address guards
it from other web pages.

**Blank page, or Open... does nothing?** The page's scripts were blocked. Content blockers (uBlock Origin, NoScript and
the like) can block scripts on 127.0.0.1: allow scripts there, or use another browser. The page shows "Starting the
editor..." until its scripts run.

Unsaved edits are never lost when you quit: they're written to `backups/<id>/` in the kit's data folder, and the
terminal says where. The first save in a session also keeps a copy of the file as it was there.

## The screens

The top bar opens a character (**Open...**), makes one from a sprite sheet (**New...**: the sheet is copied into the new
folder), **Save**s (Ctrl+S) and **Revert**s. The dot next to the name means unsaved changes. Alt+1 ... Alt+8 switch tabs.

- **Character:** the key, name and base, the credits and the sheet's terms, the sheet's settings (background colours,
  ground line), physics (sliders: multipliers on Sonic's), the games and the flags. Each field's hint says what it does.
- **Sheet & frames:** the sheet with every frame's box (blue: used, grey: unused, red: empty or outside the sheet).
  Click one to edit it: x, y, w, h, the part the build keeps after trimming (dotted), the ground line, a preview in the
  game's colours, and where it's used. Drag a frame to move it, drag an edge to resize it, arrows nudge (shift+arrows
  resize), **F** fits the box to the drawing, **[ ]** go to the previous / next frame. **Draw frame (R)**: drag around a
  sprite; the box is fitted to it and named FRAME<n> for you to rename (every use follows the rename). Alt-click reads a
  colour. **Detect frames (D)** finds the sprites for you (below).
- **Animations:** every animation on the base character's lists (with a red "empty" where the game would show nothing),
  the move slots, Sonic 1's special stage and the S3&K act clear. Frames are thumbnails: reorder, mirror, remove, add.
  The preview plays the animation with each frame placed as the game places it, at the game's speed or one you pick,
  with onion skin and frame stepping (space, arrow keys), in the game's colours or the sheet's. **Moving a frame:** drag
  the sprite in the preview, or click the preview and use the arrow keys (shift: 8 px); "move all frames together"
  shifts the whole animation. The **Ball** panel sets up the generic spin ball.
- **Abilities:** his moves (`docs/abilities.md`): description, per-game badges (S1 S2 CD 3K MA: green works, amber
  partly, grey not there yet), the fields with their units (speeds show px a frame), the animation slots each move draws
  and whether they have frames, and the rules on combining moves. **Add a move...** opens a picker: search, filter, and
  see what adding a move would clash with before adding it (for example a jump-button move on a Tails or Knuckles base).
  Adding fills in only the fields the move needs, with values known to work. Per-frame fields (the melee's reach) are
  edited on the frames: the hit-box panel, below.
- **Palette:** his own colours in slots 74-95, the colours shared with the base, and every colour his frames use with
  what the game draws it as. **Fill from sheet...** proposes a slot for every colour, most pixels first, and shows it
  before anything changes; when there are more colours than free slots, you pick what each extra one merges into
  (exact colours only: nothing is recoloured behind your back). Cell-box colours are left out and moved to the
  background. A red banner says so when the game colours collapse into a silhouette.
- **HUD & ending:** the six HUD pieces and Sonic 1's ending poses, each a frame or a rect, with previews and size hints
  (`docs/character-json.md` says where each one shows). The name tag is typed, with a live preview and an "N px of 72"
  counter.
- **Build & deploy:**
  - **Build:** tick the games and press Build. It checks the character first, then builds every Origins game, and Mania
    if it's enabled. What to install goes to `output/<id>/` in the kit's data folder: a mod folder and a zip per game.
    "dry run" only lists the steps. It builds the saved file.
  - **Deploy:** installs what Build made into your games, each character as its own mod (`NoSwap-<Name>`) beside the
    NoSwap core: enable it in HedgeModManager for Origins; for Mania it's enabled in `mods/modconfig.ini` for you.
    **Build & deploy** does both, and deploys only if the build succeeded. A game running from that folder is shown
    with a "restart the game" note (mods load at startup).
- **Settings:**
  - **Set up** (first time, and after a game update): Sonic Origins' folder and, optionally, a folder with Sonic Mania's
    `Data.rsdk`. The kit reads the game files its build needs from them. Your games are only read.
  - **Where Deploy installs:** nothing to set. Origins installs into the mods folder of the Sonic Origins you set up
    (`<Sonic Origins>/build/main/projects/exec/mods`); Mania into the Sonic Mania folder you set up, when that's the
    decompilation's play folder (with RSDKv5U and `Data.rsdk`). Save a folder only to install somewhere else (for
    Origins, the game's own folder is enough); **Use detected** goes back. Steam libraries on other drives are found too.

The **Check** panel on the right runs the check after each save, or with **Run**; each finding links to the place it's
about. ⇥ folds it away.

### Detect frames

**Detect frames (D)** on the Sheet tab finds the sprites and shows them as dashed proposals, each trimmed tight to its
drawing, named ROW<row>_<n> in reading order. Nothing changes until you accept.

- Small bits near a body (sparks, sweat drops, a detached hand) join it within the **merge** distance. Text, lines and
  specks are hidden (tick "text, lines, specks" to see them), and so are proposals over frames you already have.
- **Cell boxes:** a box colour drawn around the sprites is found and counted as background (its swatch says "a
  cell-box fill"). Accepting frames also saves it in `sheet.background`, or press **Add the box colour to the
  background**: otherwise the game would draw the box behind every frame.
- Drag on an empty part of the sheet to look only inside that area (Esc or **Whole sheet** goes back). Alt-click a
  colour to treat it as background too (**Add to the sheet's background** saves it).
- Click a proposal to select it (shift-click adds, ctrl+A all); double-click accepts one. **Accept selected** (Enter),
  **Accept all**, **Reject** (Delete), **Split** (S: a box cut into its separate pieces) and **Merge** (M: one box around
  the selected ones). **names**: a prefix such as WALK names them WALK1, WALK2, ...
- **Remove the N just added** takes the last batch back out.

### The hit-box panel

A move with per-frame reach (the melee on Y: slot 43 on the ground, 44 in the air; the Ear Grapple's tip, slot 41) shows
its hit box drawn on each frame, with a switch between **On the ground** and **In the air**.

- The frame is shown as the game places it, facing right; pick which game's rules to show with **as in** (Sonic CD uses
  his body box and is shown for information only).
- **Drag** the yellow handles: the front edge (reach), the top and the bottom.
- **Fit to sprite** / **Fit all frames** put the box on the drawing; **Same box on all frames** copies this frame's box;
  **Copy ground → air** / **Copy air → ground** copy frame by frame.
- Every frame of the move hits, and the box always reaches back to 10 px behind his centre: for a frame that shouldn't
  reach out, pull its front edge back to his body.
- **Play the move** plays it at game speed with the box flashing while it hits. **Advanced** has the numbers in words.

## Saving

Save changes as little of the file's text as it can: a hand-laid-out file keeps its layout, comments (`_` keys) and key
order. If the file changed on disk since you opened it (another editor), Save asks before overwriting.

## Not done yet

- A custom select card (`card`) and a shot's art are edited as JSON for now.
- Frames made from several pieces (`layers`) show and preview but can't be made in the editor.
- No undo beyond Revert (the backups folder keeps each session's first version).
- Frames can't be dragged from the sheet into an animation yet: pick them from the list, or use the "+ NAME" button,
  which adds the frame selected on the Sheet tab.
