<!-- Markdown copy of docs/origins-character-select.wiki, the source of the HedgeDocs page https://hedgedocs.com/index.php/Sonic_Origins_Character_Select (CC BY-SA 4.0). The wikitext is the reference; this copy was converted by a script. -->

# Sonic Origins: Character Select

> This research was done with heavy AI assistance (Claude), directed and tested in game by Superevil for the NoSwap mod. It is shared freely for anyone to use.
>
> All addresses are for the **Steam** release, **Steam build ID 12197262** (the executable's version resource reads **2.0.2.2667**). The build ID is the one the research was done against. The file version was read from the same installed executable; the DLL itself never checks it.
>
> Addresses are build-specific. Never trust an address blindly: before patching, compare the first bytes of every function it hooks with the bytes found in this build (listed in [Re-finding the functions](#re-finding-the-functions)) and leave the game alone on any mismatch. After a game update, search the executable for those byte patterns to find the new addresses.


**Sonic Origins**' character select for the classic games is a popup window drawn by the Hedgehog Engine side of the game, not by the Retro Engine (RSDK) games themselves. This page documents how it works internally (the data tables, the functions that fill it, the save records behind it and the menu archives that draw it) and [how to add new character cards](#adding-cards) to it.

Everything here applies to **Sonic 1, Sonic 2 and Sonic CD**. Sonic 3 & Knuckles picks its character on its own save screen and is left out.

## Overview

After a mode is picked in the main menu, each classic game's title screen opens the popup `UICharacterSelectWindow`. It shows up to **7 cards** (casts `obj_btn_1` to `obj_btn_7`), one per playable **kind**.

A **kind** is a byte that is the classic game's own character ID. The picked kind reaches the Sonic 1, Sonic 2 and Sonic CD scripts unchanged as `stage.playerListPos`:

| Kind | Character |
|---|---|
| 0 | Sonic |
| 1 | Tails |
| 2 | Knuckles |
| 3 | Sonic + Tails |
| 4 | Knuckles + Tails |
| 5 | Amy |
| 6 | Amy + Tails |

In the games' own data these match the GameConfig constants (Sonic 1: `PLAYER_SONIC` = 0, `TAILS` = 1, `KNUCKLES` = 2, `SONIC_TAILS` = 3, `AMY` = 5, `AMY_TAILS` = 6; ID 4 is unused in Sonic 1). The Retro Engine never bounds-checks `stage.playerListPos`, so every per-character behaviour is decided by the scripts.

Games are numbered in RSDK order everywhere below: **0** Sonic 1, **1** Sonic 2, **2** Sonic 3 & Knuckles, **3** Sonic CD. Modes are numbered 0 to 3.

The image base is fixed at `0x140000000`, and the executable has no relocations, so the addresses below are the same every run.

## Data tables

### The kind table

At `0x140D586A0`: 7 entries of 24 bytes (one per kind 0 to 6), each three pointers to C strings:

| Offset | Type | Meaning |
|---|---|---|
| 0x00 | `const char*` | SurfRide animation (pattern) that shows the card's picture: `PRM_chara_<kind+1>` |
| 0x08 | `const char*` | Text key of the card's first name line (`MAINMENU_character_name_*`) |
| 0x10 | `const char*` | Text key of the card's second name line |

The second line is only shown for the "+ Tails" kinds. That test is `KindHasTails(kind)` at `0x140331060`. The vanilla name keys in `text_menu_<language>.pac` are `MAINMENU_character_name_sonic`, `_tails`, `_knuckles` and `_amy`.

The table ends exactly where Sonic 1's row table begins (`0x140D586A0 + 7 × 24 = 0x140D58748`), so it cannot be grown in place.

### The row tables

Each game has a table of **7 rows of 7 bytes**. Each row lists the kinds to show, in card order. `0xFF` marks an unused card. The unlock state and Origins Plus pick which row is used.

| Address | Game | Notes |
|---|---|---|
| `0x140D58748` | Sonic 1 | Rows 4 to 6 (Plus): `0 1 2 5` |
| `0x140D58780` | Sonic 2 | Plus row: `0 1 2 5 3 4 6` |
| `0x140D587B8` | Sonic CD |  |
| `0x140D587F0`, `0x140D58828`, `0x140D58860` | Not identified | Three more tables with the same 0x38 spacing |

Sonic 1's 49 bytes in this build, row by row:

```
row 0: 00 01 02 FF FF FF FF
row 1: 00 01 02 FF FF FF FF
row 2: 00 FF FF FF FF FF FF
row 3: 00 01 02 FF FF FF FF
row 4: 00 01 02 05 FF FF FF
row 5: 00 01 02 05 FF FF FF
row 6: 00 01 02 05 FF FF FF
```

Which unlock state selects rows 0 to 3 was not worked out.

The row picker is the function at `0x1403E0D80`, `const uint8* RowPicker(uint8 game, uint8 mode, uint8 a, uint8 b)`. It returns a pointer to the chosen 7-byte row, which it indexes with an `imul 7`. The meaning of `a` and `b` was not identified. Rows are 7 wide in code, which matches the 7 card casts.

### Special values

- `0xFF` in a row is an empty card. That is why the highest usable kind is 254.
- **Kind 3 fallback:** `KindAllowedInGame(kind, game)` at `0x140331080` starts with `cmp cl, 6 / ja`, so it rejects every kind above 6. A rejected kind is replaced with **3** (Sonic & Tails) before the game starts. Any new kind needs this check to let it through.
- **"kind ≤ 6" checks:** the popup's build function calls a shared helper at `0x140331220` to test that a kind is in range. Other 7-value enums (the MapArea enum, for one) use the same helper, so only the popup's own call sites may be redirected, never the helper itself.

## The functions

### Building the popup

The popup's build function is `0x1403E0030` (vtable slot 6 of `UICharacterSelectWindow`). It fills an array of **16-byte card entries** at window `+0x2B0` (count at `+0x2B8`), one per card:

| Offset | Meaning |
|---|---|
| 0x00 | Kind |
| 0x01 | Zone of the save |
| 0x02 to 0x0C | Mission data (not decoded) |
| 0x0D | Flags: bit 1 = has a save, bit 0 = cleared |

The card loop is at about `0x1403E09D0`, inside the build function. For each entry it finds the cast `obj_btn_%d` in the layout and plays the kind's pattern from the kind table. It then plays `PRM_save_icon_on` or `PRM_save_icon_off` and sets the name text casts `sysf_btn_name_1` and `sysf_btn_name_2`.

These are the build function's references that matter when adding kinds (offsets from `0x1403E0030`):

| Offset | Instruction | Target |
|---|---|---|
| +0x78, +0x183, +0x1EE, +0x9AC, +0xB3E | `call` | "kind ≤ 6" helper `0x140331220` |
| +0xA01, +0xA9B, +0xB0B | `lea r64, [rip+disp32]` | Kind table `0x140D586A0` |
| +0xAB1 | `call` | `KindHasTails` `0x140331060` |

A seventh "kind ≤ 6" call is in another of the popup's functions, at `0x1403E0F10 + 0x47`.

Seen in testing (by temporarily editing Sonic 1's row bytes): the window shows 5, 6 or 7 cards and re-centres and resizes itself automatically. A duplicated kind works as a card (it highlights, shows its save and launches). The window's layer has animations `PRM_btn_2` to `PRM_btn_7`, which are probably what lays out each card count (unconfirmed).

### Window and cursor structures

Known fields of `UICharacterSelectWindow`:
- `+0x251` and `+0x250`: the two bytes the popup passes to the save views as their `a` and `b` arguments (probably mode and game);
- `+0x264`: handle of its cursor controller;
- `+0x2A8`: layer `lay`;
- `+0x2B0` and `+0x2B8`: the card entries and their count.

Its cursor controller is a `ui::MenuItemContainer`:
- `+0x250` and `+0x258`: the "cursor moved" delegates and their count. Element 0 is the popup's: vtable `0x140D58B78`, popup pointer at `+0x8`, handler `0x1403E10A0` at `+0x10`. This is a reliable way to tell the character select's container apart from every other menu list.
- `+0x290`: the "decide" delegates, fired by `FireDelegates(ctrl, ctrl+0x290, index)` at `0x1403BF8D0`;
- `+0x2EC`: current index;
- `+0x2F0` and `+0x2F8`: items (`MenuItem*`, with the card's cast at item `+0x18`);
- `+0x318`: flags, where bit 2 means input is enabled.

The popup keeps nothing per card beyond the entries: OK and the save line read entry *n* by the cursor index.

### Paging (NextEnabledIndex / PrevEnabledIndex)

The cursor moves through `NextEnabledIndex` (`0x1403BFBB0`) and `PrevEnabledIndex` (`0x1403BFC40`), both `int (MenuItemContainer* ctrl, int index)`. `MenuItemContainer::Update` is at `0x1403C0810`.

The popup has only 7 card slots, so a longer list needs a sliding window of 7. Moving right from the last card, or left from the first, scrolls the list by one (wrapping at the ends) and refills the 7 cards in place with the game's own calls:

1. Copy each card's 16-byte entry into window `+0x2B0`.
1. `PlayAnim(card, pattern, 0)` (`0x140481C20`) with the kind's picture pattern, then with `PRM_save_icon_on` or `_off`.
1. Get the layout component: `GetComponent(window, 0x142882E30)` (`0x1405C6FD0`).
1. Find each name text: `FindChild(component, "obj_btn_N", "sysf_btn_name_1")` (`0x14047F760`), and the same for `_2`.
1. Set each name: `SetTextKey(textCast, key)` (`0x140483330`), with `""` to hide a line.
1. Redraw the save line under the cards: `UpdateSaveInfo(window, index)` (`0x1403E1140`).

The cursor index is returned unchanged, so the cursor stays where it is while the cards change. A hook on the build function (`0x1403E0030`) resets the page and records each kind's entry when the popup opens.

### Other helpers

| Address | Name (unofficial) | Notes |
|---|---|---|
| `0x1405C6420` | ResolveHandle | Handle to object |
| `0x14047F7A0` | FindCast(component, name) |  |
| `0x142882E78` | (text cast class) | Compared against a cast's class chain before `SetTextKey`, as `UpdateSaveInfo` does at `0x1403E11C5` |
| `0x140454170` | PlaySfx(out, window, sound) | Playing sound 0 after a page refill works as the cursor sound (assumed) |
| `0x140483A00` | SetCropIndex(layer, cast, index) | Sets an image cast's crop |

### Launch: how a kind reaches the game

When a card is picked, its kind is stored as the "last kind" for (mode, game) and the game starts with it. Testing shows the kind arrives in Sonic 1, Sonic 2 and Sonic CD as `stage.playerListPos` unchanged (kinds 7 and up launch correctly once `KindAllowedInGame` lets them through). The exact native code that writes `playerListPos` was not traced. The research notes place the kind 3 replacement in `RetroEngineBase::Setup` (unconfirmed by name).

The launch paths that read the last kind (all calls to `GetLastKind`, below):
- `0x1403546D9`: the menu scene's launch state (function `0x140354080`). A kind that the row check `RowHasKind(game, mode, kind, a, b)` (`0x1403E0FA0`, called at `0x140354705`) rejects becomes Sonic, or Sonic & Tails in Sonic 2.
- `0x14033A422`: the game scene's setup from a queued start request (function `0x14033A070`). It stores the kind at `+0xC9` and then opens the 16-byte save view with it. A pick in the popup can reach the game this way too, so a mod that changes the kind must handle both paths.

### Saves: SlotIndex and the save views

Origins keeps its classic-game saves as records per (mode, game, kind) slot. Every record lookup goes through `SlotIndex(mode, game, kind)` at `0x14045DA50`. Its tables are indexed `[game * 7 + kind]` (74 slots). It has **no slot for kinds 7 and up**: callers then get a null record and crash.

Records are reached through four **views**, each `View(this, out, a, b, kind)`, which fill `out = {vtable, record*, owner}`:

| Address | Record size | Contents |
|---|---|---|
| `0x140459B60` | 0x10 | Byte 0 is 1 when there is a save, byte 1 is the zone, and bit 25 of the u32 at +4 means cleared |
| `0x140459420` | 0xA0 | Sonic 1 keeps its classic save here (the first 0xA0 bytes of the engine save data) |
| `0x140459360` | 0x8000 | The classic game's save RAM (not used by Sonic 1) |
| `0x14045A190` | 0x10001 | Not decoded |

Origins keeps a separate, complete save RAM array per character. Entering a classic game loads the last-played character's array.

### The CONTINUE head (main menu)

The main menu's CONTINUE button shows the head of the character last played in that (mode, game). Origins stores one "last kind" per (mode 0 to 3, game) in its save:

- `GetLastKind(save, mode, game)` at `0x14045A110` (it reads save bytes `+0x06`, `+0x0A`, `+0x12` or `+0x0E`);
- `SetLastKind(save, mode, game, kind)` at `0x14045CB50`.

The main menu reads it at `0x1403E509D`, in its fill function `0x1403E4F10`, which builds the table of the buttons' kinds. The CONTINUE button reads it at `0x1403E92AD`, in `0x1403E8FC0`, to find the kind whose save must exist (`0x1403E70D0`). The launch reads above use it too.

The head is drawn by `SetIconChara(menu, layer, kind)` at `0x1403E7830`, called at `0x1403E8436` (the main menu's fill) and `0x1403E94D3` (after a pick in the select). It rejects kinds above 6. It reads a crop table at `0x140D59518`, whose kind 0 entry is `00 00 00 00 FF FF FF FF`: crop 0 on cast `pattern_chara_1` and none (−1) on `pattern_chara_2`. It then calls `SetCropIndex`. The layout of the remaining entries is assumed from that first one.

The head texture is `menu_main_menu_icon_chara_s.dds` in `ui_mainmenu.pac` (block `.004`). It is BC7, 480×96, holding 4 cells of 120×96 (Sonic, Tails, Knuckles, Amy), and is drawn at 4 texels per pixel. The scene is `menu_main_menu_island.swif`, which is in each of the 12 language archives `ui_mainmenu_<language>.pac` (de, en, es, fr, it, ja, ko, pl, pt, ru, zh, zhs). Its layer `ref_icon_chara` has the casts `pattern_chara_1` and `_2` and the animations `PRM_chara_1` and `_2`.

The CONTINUE button is greyed out in Classic mode even in the vanilla game (that mode has no resume).

## The menu archives

### Which archive the popup uses

The scene `menu_main_menu_chara_select` exists in two archives under `image/x64/raw/ui/`:
- `ui_gamestage.pac`: **the popup over the classic games' title screens loads this one**. Editing only `ui_mainmenu.pac` changes nothing in the popup.
- `ui_mainmenu.pac`: the main menu's own copy of the same scene.

In both, the scene file (`.swif`) is in the root, while the textures (`menu_main_menu_chara_select_chara_sonic.dds`, `_tails`, `_knuckles`, `_amy`, `_tails_parts`, `_btn_bg`, `_icon_save`) are in a dependency block: `.000` in `ui_gamestage.pac`, `.004` in `ui_mainmenu.pac`.

### PACx v403 (split) layout

Origins' `.pac` files are a **PACx v4.03** outer archive around **PACx v4.02** inner archives.

**Outer (PACx403)**: a 0x30-byte header (signature `PACx`, `403`, `L`), with the fields used here:

| Offset | Meaning |
|---|---|
| 0x0C | File size |
| 0x10 | Root offset |
| 0x14 | Root compressed size |
| 0x18 | Root uncompressed size |
| 0x24 | Size of the root chunk table, padded to 8 |
| 0x30 | Root chunk table: `u32 count`, then `{u32 compressed, u32 uncompressed}` per chunk |

After the table come the dependency **blocks** (`.pac.000`, `.pac.001`, ...), each starting on a 16-byte boundary. The root follows them, and the file is padded to 16. Every block and the root are split into **64 KB pieces**, each compressed on its own as an **LZ4 block** (a chunk whose compressed and uncompressed sizes are equal is stored raw).

**Root (PACx402)**: a 0x30-byte header whose sizes at 0x10 to 0x24 are, in order, the node trees, the dependency section, the data entries, the string table, the file data and the offset table (0x0C is the total size).
- **Dependency section**: `u64 count`, `u64 → entries`. Each 0x20-byte entry holds `u64 → name`, `u32 compressed size`, `u32 size`, `u32 offset of the block in the outer file`, `u32 chunk count` and `u64 → chunk table` (`{u32 compressed, u32 size}` per chunk). **Each block's chunk table lives in the root**, so a block that grows needs more table entries in the root.
- **Data entries** (0x30 bytes): `u32 uid`, `u32 size`, `u64 0`, `u64 → data`, `u64 0`, `u64 → extension`, `u64 flags`. A file stored in a block is listed in the root with flags 1 and data pointer 0, and the block (itself a PACx402 archive, without a dependency section) holds its data.
- **Names** are radix trees of fragments, as documented by HedgeLib's PACx v4 code. Each node is 0x28 bytes: `u64 → fragment`, `u64 → data`, `u64 → child indices`, `i32 parent`, `i32 global index`, `i32 data index`, `u16 child count`, `u8 has data`, `u8 full path size`.
- **Offset table**: the position of every pointer, as deltas >> 2 in 1, 2 or 4 bytes (top bits `01`, `10` or `11`), padded with zeros to 8. With it, bytes can be inserted anywhere and every pointer fixed up.

Rebuilding an archive with nothing changed reproduces the original byte for byte, provided unchanged 64 KB chunks are written back as their original compressed bytes.

### The scene: main_menu_chara_select

`menu_main_menu_chara_select.swif` is a SurfRide **SWIF** file (the "version 5" layout used by Origins; structures as in DeaTh-G's surfboard templates). All pointers are u64 absolute file offsets, 8-aligned, and listed in the `SOF0` chunk. Relevant layers:

- `lay`: the window. Its card casts are `obj_btn_1` to `obj_btn_7` (each inside `lay_btn_N`). The save line under the cards is `null_save_stage` with the text `sysf_save_stage`.
- `ref_btn`: the card template that every `obj_btn_N` instances. It holds the picture groups `null_char_1` to `null_char_7` (one per kind, for example `null_char_1` containing `sonic_1`), the name texts `sysf_btn_name_1` and `_2`, and the save icon. Its animations are the shared states (`in`, `loop`, `out`, `over`, `loop_act`, `go_away`, `press`), then `PRM_chara_1` to `PRM_chara_7`, `PRM_save_icon_on` and `PRM_save_icon_off`.

**How a card's picture works:** `PRM_chara_<kind+1>` only switches the `Display` of the groups `null_char_1` to `_7` (and of `sysf_btn_name_2`). The shared state animations key the groups' sprite frames, but never touch a group they don't know. A new group's `Display` and crop index therefore stay as its pattern set them.

The card pictures are BC7 textures. `menu_main_menu_chara_select_chara_sonic.dds` is 2640×1320 (BC7, DXGI format 98, one mip). The `.swif` declares textures at **half** their DDS size (1320×660 here), and crops are stored as normalised `(left, top, right, bottom)` floats.

### Text keys

Names come from `image/x64/raw/text/text_menu_<language>.pac`. These are small PACx403 archives whose content is all in the root, holding a **cnvrs-text** file (BINA 2.1):
- root: `u8 version (6)`, `u8 languages (1)`, `u16 entry count`, `u32 0`, `u64 → entries`, `u64 → language name`, `u64 0`;
- entries (0x30 bytes each, **sorted by id**): `u64 id`, `u64 → key`, `u64 → attributes`, `u64 → UTF-16 text`, `u64 length`, `u64 0`;
- the id is a hash of the key, `h = h * 127 + byte` (mod 2<sup>32</sup>), and the game looks keys up by id.

## Adding cards

This approach is confirmed working in game. It has two halves: **archive edits** made once at build time, and **runtime patches** from a mod DLL (loaded by HiteModLoader through HedgeModManager; hooks via MinHook or similar).

### Archive edits (64 generic card slots)

Instead of one picture group per new character, which would need a hide track per group in every animation, the scene gets **one generic group whose crop index picks the picture**. The steps below are done in both `ui_gamestage.pac` and `ui_mainmenu.pac`.

1. **Texture:** append rows of cells (for example 64 cells of 440×536 DDS pixels, filled with transparent BC7 blocks) below `menu_main_menu_chara_select_chara_sonic.dds` in its dependency block. Update the DDS height, the file's size in the block and in the root's entry, and the block's chunk table in the root.
1. **Crops:** in the `.swif`'s texture list, rescale that texture's existing crops to the taller texture (the same pixels). Add one crop per cell, and set the texture's declared height (half the DDS height) and crop count.
1. **Casts** (layer `ref_btn`): add a group `null_char_extra` as the next sibling of the game's last `null_char_N`. Give it a child image cast `chara_extra`, copied from Sonic's `sonic_1` but with the cell's size and **one crop reference per slot** (`{u16 texture list, u16 texture, u16 crop}`, crop index 0 = slot 1).
1. **Animations** (layer `ref_btn`): for each slot *s*, add `PRM_extra_<s>` and `PRM_extra_<s>_2`, copied from `PRM_chara_1`'s header. Each has constant keys at frame 0: `Display = 0` on `null_char_1` to `_7`, `Display = 1` on `null_char_extra`, **`CropIndex0 = s − 1`** on `chara_extra`, and `Display` of `sysf_btn_name_2` set to 1 only in the `_2` variant.
1. **Hide the new group in the game's patterns:** add `Display = 0` on `null_char_extra` to each of `PRM_chara_1` to `_7`.
1. **Text:** in every `text_menu_<language>.pac`, add the keys `MAINMENU_character_name_extra<s>_1` and `_2` for each slot, with room for 31 UTF-16 units each. Re-sort the entries by id and check that no two keys share a hash.

All edits are **append-only**: new structures go after the last chunk (before `SOF0`), existing pointer fields are repointed at them, and the new pointers are added to `SOF0`. Nothing existing moves. Done this way, the archives rebuild byte-identically when no slots are added.

The same idea gives the CONTINUE head its new characters. In `ui_mainmenu.pac`, append 120×96 cells below `menu_main_menu_icon_chara_s.dds`. In each language's `menu_main_menu_island.swif`, rescale the four existing crops and add one crop per cell (crop `4 + slot − 1`). Then give both `pattern_chara_1` and `_2` a crop reference for every crop.

**Filling slots without rebuilding:** store the 64 KB chunks that hold the cells and name texts as **LZ4 blocks of literals only**, so those bytes sit in the file uncompressed. A descriptor (`raw/ui/cards.json`) records where those runs, each slot's cell rows and each name's text and length are. At startup the DLL writes each installed character's picture and name into a cached copy of each archive and serves the copies. The game archives are never modified.

### Runtime patches

1. **Kind table:** copy the 7 vanilla entries into memory allocated within ±2 GB of the executable, so rip-relative references reach it. Add one entry per new kind (7 and up), with the pattern `PRM_extra_<slot>` (or `_2`) and the name keys `MAINMENU_character_name_extra<slot>_1` and `_2`. Repoint the three `lea`s in the build function at the copy.
1. **Range checks:** redirect the six "kind ≤ 6" call sites (five in the build function, one at `0x1403E0F10 + 0x47`) to a stub returning "kind ≤ highest kind" (`cmp cl, imm8 / setbe al / ret`).
1. **Second name line:** redirect the `KindHasTails` call at build `+0xAB1` so new kinds can show two lines.
1. **Rows:** hook `RowPicker` (`0x1403E0D80`) and return your own 7-byte row with the new kinds included. Skip game 2 (S3&K).
1. **Launch:** hook `KindAllowedInGame` (`0x140331080`) to accept the new kinds outside S3&K. Without this, they start as Sonic & Tails.
1. **Saves:** hook `SlotIndex` (`0x14045DA50`) to give new kinds Sonic's slot, so callers get a valid record and don't crash. Then wrap the four views so a new kind's record pointer is swapped for a buffer of your own after the original fills `out`. Origins' own save file is never written with a new kind.
1. **Last kind:** hook `SetLastKind` (`0x14045CB50`) so it never stores a kind above 6 in Origins' save (store 0 instead), and remember the real one yourself.
1. **More than 7 cards:** hook `NextEnabledIndex` and `PrevEnabledIndex` as described in [Paging](#paging-nextenabledindex--prevenabledindex), plus the build function to reset the page.
1. **CONTINUE head (optional):** redirect the four `GetLastKind` call sites (`0x1403E509D`, `0x1403E92AD`, `0x1403546D9`, `0x14033A422`) to return your remembered kind when Origins says 0. Let it through the row check at `0x140354705`. Wrap the two `SetIconChara` calls (`0x1403E8436`, `0x1403E94D3`): draw Sonic's head, then `SetCropIndex(layer, "pattern_chara_1", 4 + slot − 1)`.

Patch only after checking every function's first bytes and every call site's `E8 rel32` target. If anything differs, patch nothing.

### Re-finding the functions

These are the exact bytes to compare before hooking (at the start of each function, unless noted). Search the executable for them after an update.

| Address | Function | Bytes |
|---|---|---|
| `0x1403E0D80` | RowPicker | `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18 57 41 56 41 57 48 83 EC 20` |
| `0x14045DA50` | SlotIndex | `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18 57 48 83 EC 20 0F B6 E9` |
| `0x14045CB50` | SetLastKind | `44 0F BE D2 4C 8B D9 84 D2 74 3C` |
| `0x140331080` | KindAllowedInGame | `80 F9 06 77 2A 0F BE D2 85 D2 74 1C` |
| `0x1403BFBB0` | NextEnabledIndex | `48 89 5C 24 08 48 89 7C 24 10 4C 8B 99 F8 02 00 00 45 33 C9` |
| `0x1403BFC40` | PrevEnabledIndex | `48 89 5C 24 08 48 89 7C 24 10 4C 8B 99 F8 02 00 00 45 33 C0` |
| `0x1403C0810` | MenuItemContainer::Update | `48 89 5C 24 20 57 48 83 EC 40 8B 81 18 03 00 00` |
| `0x1403E0030` | Popup build (vtable slot 6) | `48 89 54 24 10 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 78 F2 FF` |
| `0x140459B60`, `0x14045A190` | Save views (0x10, 0x10001) | `48 89 5C 24 08 48 89 74 24 10 57 48 83 EC 20 41 0F B6 C0 48 8B DA` |
| `0x140459420`, `0x140459360` | Save views (0xA0, 0x8000) | `48 89 5C 24 08 57 48 83 EC 20 41 0F B6 C0 48 8B DA` |
| `0x14045A110` | GetLastKind | `48 0F BE C2 4C 8B C9 83 F8 07 77 4B` |
| `0x1403E0FA0` | RowHasKind | `40 53 48 83 EC 20 41 0F B6 C1 41 0F B6 D8` |
| `0x1403E7830` | SetIconChara | `48 85 D2 0F 84 8D 00 00 00 48 89 5C 24 08 57 48 83 EC 20 41 0F B6 C8` |
| `0x140483A00` | SetCropIndex | `40 53 48 83 EC 20 41 8B D8 E8` |
| `0x1403E1140` | UpdateSaveInfo | `40 55 53 41 57 48 8D AC 24 40 FF FF FF 48 81 EC C0 01 00 00 8B DA` |
| `0x140D59518` | Head crop table (data) | `00 00 00 00 FF FF FF FF` |
| `0x140D58748` | Sonic 1 row table (data) | The 49 bytes listed in [The row tables](#the-row-tables) |

The call sites are checked as an `E8` opcode whose `rel32` lands on the expected function. The `lea` sites are checked as `48/4C 8D` with a rip-relative ModRM whose target is the kind table.

## Saves and pitfalls

- **Per-character records:** give each new character its own record buffers for all four views, kept in a file of your own (for example under `%APPDATA%\SEGA\SonicOrigins\`), never in Origins' save.
- **CONTINUE loaded the wrong character before per-kind saves:** while new kinds shared Sonic's record, "continue" on an extra's card restored whichever character was stored in Sonic's shared record (picking Metal Sonic loaded Big). New games were fine. Separate records fixed it.
- **Kinds 4 and 6 in Sonic 1:** putting Sonic 2's full row (`0 1 2 5 3 4 6`) into Sonic 1's table crashed when the popup opened. Sonic 1 appears to have no setup for kind 4 or 6 (kind 3 works in Sonic 1: picture, name and launch as Sonic & Tails).
- **The 7-card window:** the layout has exactly 7 card casts and the rows are 7 wide in code, so more characters need paging (above), not wider rows.
- **Kinds 7 and up with no save slot:** `SlotIndex` returns no slot, and callers crash on the null record. Map them to a vanilla slot first, then swap the record.
- **Never send a new kind to Origins:** the scripts' `NOTIFY_PLAYER_SET` callback with an unknown ID (7) crashes the game. With an extra's ID in `stage.playerListPos`, `NOTIFY_SPECIAL_RETRY` (special stage results in Sonic 1 and 2) left the results screen blank or showing garbage. Report the character as Sonic for these calls.
- **Which archive:** edits to `ui_mainmenu.pac` alone don't show in the popup. Use `ui_gamestage.pac`.

## Credits and references

- **NoSwap** (source to be published). The references for everything above are its tools and DLL headers:
   - `tools/origins_pacx.py`: split PACx403/402 reader and writer, with pointer relocation;
   - `tools/origins_pac.py`: small unsplit archives and LZ4;
   - `tools/surfride.py`: SWIF reader and append-only editor;
   - `tools/bc7.py`: exact solid-block BC7;
   - `tools/cnvrs_text.py`: cnvrs-text;
   - `tools/origins_cards.py` and `tools/build_origins_menu.py`: the card slots;
   - `native/src/NoSwapS3K.cpp`, `native/src/MenuCards.h` and `native/src/Roster.h`: the hooks, card writing and kind registry.
- **HedgeLib** by Radfordhound: the PACx v4 layout (node trees, data entries).
- **HedgeArcPack** (HedgeLib): the standard tool for these archives.
- **HedgeModManager** and **HiteModLoader** (hedge-dev): loading code and file mods into Origins.
- **DeaTh-G's surfboard templates**: the SurfRide SWIF structures.
- **The RSDK decompilation projects** by Rubberduckycooly and chuliRMG (RSDKv3, RSDKv4 and RSDKv5(U); original Retro Engine by Christian Whitehead / Evening Star), and the script decompilations: character IDs and engine behaviour on the classic-game side.
- **Origins Ultrafix**: its `Ultrafix3kFixes` headers were the reference for RSDK and S3&K types and some fixed addresses.
- **MinHook** by Tsuda Kageyu: function hooking.

