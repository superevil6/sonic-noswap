# Sonic CD (Origins) character-dependency map for NoSwap

Source: `.../exec/SonicCDu/Scripts/` (591 files, CRLF, Retro Engine **v3** dialect). Line numbers are 1-based in the
original files (CRLF stripping does not change them). "ID 7" = first extra (`PLAYER_EXTRA1_A`); 8/9 behave the same.

Method: every `#platform` block was resolved the way the v3 compiler does it (a non-matching `#platform:` line skips
everything up to the *next* `#endplatform`; there is no real nesting). Compiled on Origins (assumed):
`Use_Origins`, `Standard` (proof: `Player_ProcessUpdate` only calls `ProcessPlayerControl()` inside
`#platform: Standard`, PlayerObject.txt:526-550; the `Mobile` copy is at :688) and unconditional code.
Not compiled: `Use_Standalone`, `Mobile`, `Use_Haptics` (Select/Start comments say "Not present in Origins"),
`Use_Decomp` (only the community decomp engine defines it), `Editor`, `DUMMY`. `SW_Rendering`/`HW_Rendering` are
unknown but irrelevant here (only R5 glow palettes). Only 13 of the 317 `PlayerListPos` lines sit in skipped blocks:
Monitor:248, LoadSaveMenu:817/872/994 (Mobile), PlayerObject:1435/3295/3333/4777, R3/ScoreChute:240,
R8/FadeScreen:171/257, R8/ShrinkGrowLaser:152, Special/StageFinish:211 (all Standalone) - not listed below.

Legend for treatments (S1/S2 vocabulary, plus CD-specific ones):
- **add case** = make the extra take an existing branch (usually Sonic's) of a switch/if chain
- **own startup case** = extra needs its own block (LoadAnimation, abilities)
- **sheet** = per-character `LoadSpriteSheet` chain with no default. Missing => the object's `SpriteFrame`s are cut
  from whatever sheet the object type had (sheet 0) => garbage graphics. Fix: add
  `if Stage.PlayerListPos >= 7  LoadSpriteSheet(<Sonic's sheet, or the extra's own copy>)`
- **frame block** = per-character `SpriteFrame` block. Missing => those frames don't exist (drawing them reads
  foreign frame data) and every later frame index **shifts down**
- **save: full / gameover / complete** = NoSwap save-call kinds (CD has no "lives" writes, see section H)
- **hide notify** = skip a progress `EngineCallback(NOTIFY_...)` while an extra plays
- **guard notify** = stand in as Sonic (PLP=0) while Origins' UI answers a notify, restore afterwards
- **alias** = the file needs `#alias 7 : PLAYER_EXTRA1_A` (v3 aliases are per file - there is no `public alias`)
- **fine** = no change needed; **design** = behaviour choice, no crash either way

---------------------------------------------------------------------------------------------------------------

## 1. Character IDs in CD

**Two independent sets of names:**

| Name | Where | Value | Notes |
|---|---|---|---|
| `PLAYER_SONIC`, `PLAYER_TAILS`, `PLAYER_KNUCKLES`, `PLAYER_AMY` | **GameConfig.bin global variables** (vars #212-215 of 226, 1-based) | 0, 1, 2, **5** | Visible in *every* script of every stage (globals don't depend on StageConfig byte 0). They are *variables*, not constants: they work in `if` but **cannot be `case` labels** (see the comment at TailsObject.txt:13 about `ANI_*` globals) |
| `PLAYER_SONIC_A`, `PLAYER_TAILS_A`, `PLAYER_KNUCKLES_A`, `PLAYER_AMY_A` | per-script `#alias` (105 files declare some of them, e.g. PlayerObject.txt:71-74) | 0, 1, 2, 5 | Only `_A` names can be `case` labels |
| `PLAYER_NONE` / `PLAYER_BACK` | LoadSaveMenu.txt:105/108 only | -1 / 2 | menu-local (unused object) |

- There are **no combo IDs** in CD (no sidekick: no `PLAYER_SONIC_TAILS` etc.). IDs 3, 4, 6 are unused. Keep the
  extras on **7, 8, 9** for consistency with S1/S2 and their save records.
- GameConfig player-name list: `SONIC, TAILS, KNUCKLES, AMY` (4 entries; Amy is list index 3 but ID 5), so, as in S1,
  `Stage.PlayerListPos` is not an index into that list and nothing bounds-checks it.
- Other GameConfig facts: 33 global objects (Player Object first, then Stage Setup, HUD, ActFinish, Death Event,
  Tails Object, Pause Menu, Ring, ..., Debug Mode = Global/TouchControls.txt), 226 global vars, SFX 35, stage lists:
  0 = presentation (13: Title, Menu, TAttack, Secrets x3, DAgdn, Help, Credits x3, Upsell, Help), 1 = regular (124:
  R11A..R83D = 0-69, then ANR11A..ANR82D = 70-123, which no script references), 2 = "SS1-8" (**named
  SPECIAL_STAGE but Origins uses list 3 for them**, see Select.txt:327-337), 3 = R21A/missions/boss rush.
- Regular-stage index layout: `listPos = round*10 + act*4 + period` (A present, B past, C good future, D bad future;
  act 3 only C/D at +8/+9). `ListPos % 10 >> 2 == 1` is the "act 2" test used by save/continue code.
- Recommendation: **don't touch GameConfig.bin**. Use literal numbers (`>= 7`) or a per-file
  `#alias 7 : PLAYER_EXTRA1_A` (+8/+9). Adding GameConfig globals would require shipping a modified GameConfig.bin
  that Origins' native side also reads (it looks up `game.*` / `NOTIFY_*` variables).

## 2. The v3 dialect (vs the v4 dialect used for S1/S2)

| Concept | v3 (CD) | v4 (S1/S2) |
|---|---|---|
| Alias | `#alias 0 : PLAYER_SONIC_A` (PlayerObject.txt:71), `#alias Player.Value0 : Player.Rings` (:6), `#alias Object[24].PropertyValue : HUD.CurrentTimePeriod` (StageSetup.txt:9). **Always file-local** (every file re-declares its own `PLAYER_*_A`) and must precede use | `public alias` / `private alias` |
| Function | `#function Player_BadnikBreak` forward decl (PlayerObject.txt:162) + `function Player_BadnikBreak` ... `end function` (:246-388). **Function names/IDs are global per stage**: later scripts call earlier ones without declaring them, e.g. `CallFunction(Player_Hit)` in R8/BossWing.txt:163, `Player.State = Player_State_Air_NoDropDash` in TouchControls.txt:124 | `public function`, `reserve function`, `private function` |
| Events | `sub ObjectMain` / `sub ObjectPlayerInteraction` (StageSetup.txt:278) / `sub ObjectDraw` / `sub ObjectStartup` / `sub RSDKDraw|RSDKLoad|RSDKEdit` ... `end sub` | `event ObjectUpdate` ... `end event` |
| Switch | `switch Stage.PlayerListPos` / `case PLAYER_SONIC_A` / `default` (PlayerObject.txt:4899) / `break` / `end switch` (PlayerObject.txt:1357-1426). Cases must be constants/aliases | same, lowercase |
| If | `if X == Y` / `else` / `end if` (also accepts `endif`, TimeWarp.txt:72). One comparison per `if`; compound conditions via `CheckEqual/CheckNotEqual/CheckGreater/CheckLower` + `CheckResult`: `CheckEqual(Player.Animation, ANI_JUMPING)` / `TempValue0 = CheckResult` / `TempValue0 \|= CheckResult` (PlayerObject.txt:247-251) | same |
| Loop | `while ArrayPos0 < 1056` ... `loop` (PlayerObject.txt:4715-4721) | `while`/`loop`, `foreach` |
| Platform | `#platform: Use_Origins` ... `#endplatform` (Title-case tokens, often with trailing comments; one file uses `#platform:\tUse_Standalone`, Start.txt:326). "Nested" blocks (Start.txt:486-492) are not real nesting | `#platform: USE_ORIGINS` |
| Variables | `TempValue0-7`, `ArrayPos0-1` (only two), `CheckResult`, `Object.Value0-7`, `Player.Value0-15` (separate player struct: `Player.XPos`, `Player.State`, ...), `SaveRAM[0-8191]`, `Stage.*`, `Screen.*`, GameConfig globals by name (`Options.GameMode`, `game.callbackParam0`, `Warp.XPos`, ...). Relative objects `Object[+1]` (Start.txt:293), `Object[-2]` (R7/MetalSonic.txt:385) | `temp0-7`, `arrayPos0-7`, `object.value0-47`, `player[n].x` |
| Script-level / global variables | **None.** No `public value`, no `private value`, no tables (`GetTableValue` doesn't exist). Only GameConfig globals (need GameConfig.bin), object values, and SaveRAM | `public/private value`, `public/private table` |
| Native calls | `EngineCallback(NOTIFY_X)` - one argument; parameters go in the globals `game.callbackParam0-3` set beforehand, answers come back in `game.callbackResult` (Select.txt:431-432, 453-456) | `CallNativeFunction2(NotifyCallback, NOTIFY_X, param)` |
| Palettes | `LoadPalette(file, bank, dstIndex, srcStart, srcEnd)` (R3/PaletteAni_A.txt:38, srcEnd exclusive), `CopyPalette(src, dst)` (whole bank), `RotatePalette`, `SetActivePalette`. **No `SetPaletteEntry`** | `SetPaletteEntry` exists |
| Operators | `+= -= *= /= %= &= \|= <<= >>= ++ --`, `FlipSign()`, `GetBit/SetBit` | same |

Implications for the build script: every `noswap_common` snippet written for v4 (`public function`,
`stage.playerListPos`, `temp0`, `arrayPos1`, `CallNativeFunction2(NotifyCallback, ...)`, `SetPaletteEntry`) needs a
v3 port: `function`/`#function`, `Stage.PlayerListPos`, `TempValue0`, `ArrayPos1`, `game.callbackParam0 = X` +
`EngineCallback(X)`, `LoadPalette("....act", ...)`. Helper functions put in Players/PlayerObject.txt are callable from
every script of a global-loading stage (PlayerObject is compiled first); non-global stages (Title, SS1-8) need local
copies.

## 3. Stages that do NOT load global objects (StageConfig byte 0 == 0)

Verified for v3: every `Stages/*/StageConfig.bin` (170) parses exactly to EOF as `[u8 loadGlobals][96 bytes =
32-colour stage palette][u8 n][n names][n script paths][u8 sfx][sfx paths]`, so byte 0 is "load global objects" as in
v4.

| Stage | Scripts | Character code | Needs extras work? |
|---|---|---|---|
| **Title** | Title/Sega, Sonic, Logo, Background, Clouds, Start, CWLogo, LiteRibbon, Select | Sonic.txt:16 `#alias 0 : PLAYER_SONIC_A`, :52 resets PLP; Start.txt:430-431 (globals); Select.txt:105 alias, :241/:275 save record | **Yes** - picker + extras' save screen (section 5). Local alias + local helper code |
| **SS1-SS8** | Special/SpecialSetup, HUD, TitleCards/SS_TitleCard, UFO, UFONode, UFOPowerUp, Sonic, TouchControls, PauseMenu, SmokePuff, WaterSplash, Ring, Dust, TimeStone, StageFinish, BGEffects_Sn (+HWBackG_S1/S6, Global/AttractMode on SS1/SS6) | Special/Sonic.txt:113-114 aliases; StageFinish.txt:50-51; PauseMenu.txt:92-93 | **Yes** (section D). No PlayerObject here, so no shared helpers; SS reserved slots: 0,2 (SSSonic),3,4 (HUD),9,23,25,30,31 |
| **Menu** | Menu/BGAnimation, MenuHeading, MenuControl, MenuButton, MenuWindow, LoadSaveMenu, OptionsMenu(+C/H), ExtrasMenu, AboutMenu(+F), SoundMenu, DemoMenu | LoadSaveMenu (unused on Origins), ExtrasMenu.txt:468-474 forces Sonic | No |
| **TAttack** | TAttack/* | MenuControl.txt:322 forces `PLAYER_SONIC_A`, :1188-1192 NOTIFY_PLAYER_SET 0 | No |
| **Secrets** | StageSelect, SoundTest, SecretImages(2), MessageText, TailsUnlock | SoundTest.txt:310 sets Tails for a secret picture | No |
| **DAgdn**, **Help**, **Upsell** | DA Garden / help / store | none (DA Garden is entered via ExtrasMenu which forces Sonic) | No |

Everything else (all R*/ANR*/MR*/BR*/DM* stages, R21A and **Credits**) loads the global list and therefore
PlayerObject.txt.

## 4. Free storage for ability state (Q3)

**Player.Value0-15: none is free.** All 16 are aliased in PlayerObject.txt:6-24 and used on Origins:

| Value | Alias | Used by |
|---|---|---|
| 0 | Rings | 12 files (Ring, LoseRing, HUD, ActFinish, StageSetup warp restore :369, TimeWarp, ...) |
| 1 | AbilityTimer | PlayerObject (jump abilities) |
| 2 | RollAnimationSpeed | PlayerObject, R3/R5 TubeSwitch write 240 |
| 3 | SpeedShoesTimer | PlayerObject, BrokenMonitor |
| 4 | InvincibleTimer | 46 files; TitleCards R*_TitleCard.txt:88 write 8000 on warp arrival |
| 5 | BlinkTimer | 14 files |
| 6 | MinRollSpeed | 11 files, StageSetup warp restore |
| 7 | AnimationReserve | springs, R8 platforms |
| 8 | ScrollDelay | S2-spindash camera lag (PlayerObject:789-794) |
| 9 | JumpOffset | camera offset while rolling |
| 10-12 | JumpAbility / ActionPeelout / ActionSpindash | function pointers |
| 13 | ForceGrounded | S2 spindash (PlayerObject:1762-1765, 2029) |
| 14 | DropDashCharge | PlayerObject + R4/AirBubble |
| 15 | FlightVelocity | Tails; **cleared every frame** unless `Player.State == Player_State_Fly` (PlayerObject:796-803) |

`Object[0].ValueN` is not free either: ActFinish.txt:27 and TitleCards `R*_TitleCard.txt:16` alias `Object[0].Value0`
/ `.Value4` as Player.Rings / Player.InvincibleTimer (so they very likely *are* the player values), the dying player's
slot 0 becomes a Death Event (PlayerObject:2635, uses Value1-3) and debug mode reuses slot 0 (TouchControls aliases
Value0-6).

**Recommended: an unused reserved entity slot.** Scene objects start at slot 32; scripts only ever touch reserved
slots 0, 1 (Tails' tails; WarpSonic afterimages use `Object[1].Value0-7`), 2 (shield/WarpSonic), 3 (warp star),
9 (pause), 15, 19, 20 (title card), 21, 23 (stage setup), 24 (HUD), 25 (debug/touch), 26 (object score), 29, 30.
Relative indexing from low slots is only `Object[+1]`/`Object[+2]` from the player and `Object[-2]` from slot 2.
=> **`Object[5..8]` (also 10-14, 16-18, 22, 27, 28, 31) are never touched**: 8 values each, type stays Blank Object so
no code runs on them. Lifetime: one stage (the engine clears entities on every LoadStage, and TimeWarp.txt:115-119
resets all 1184 slots before a time jump). Clear it yourself in `Player_Setup_Startup`. In SS1-8, slot 4 is the HUD;
5-8 are free there too. Every file that uses it needs its own alias line, e.g. `#alias Object[5].Value0 : NoSwap.State`.

**Cross-stage state** (picker choice, active save slot): `Stage.PlayerListPos` itself survives stage loads (see 6).
For anything else, GameConfig globals that no script uses: `Leaderboard.Offset` (0 uses anywhere),
`Options.HapticsMenu` (only in a skipped Mobile block, MenuButton.txt:530). They survive LoadStage; whether Origins
resets them on `Engine.State = RESET_GAME` or re-boot is untested. `SaveRAM` in memory is **not** a safe scratchpad:
PlayerObject.txt:4705-4709 calls `ReadSaveRAM()` at every stage start (except attract/stage-select), so only values
written with `WriteSaveRAM()` survive (same as the S1 finding).

## 5. Title screen / menu flow on Origins and where the picker goes (Q4)

Stage "Title" (presentation list 0). Origins jumps straight in (`game.titleMode = SKIP_LOGOS`, Sega.txt:53-57).

1. **Title/Sega.txt** `SEGA_SETUP` (43-105): `ReadSaveRAM()`, `Options.Soundtrack = SaveRAM[38]`, skips logos when
   Origins asks or when returning from a menu (`game.mainMenuMode != 0`).
2. **Title/Sonic.txt** :43-56: after the fade-in **`Stage.PlayerListPos = PLAYER_SONIC_A`** (:52),
   `LampPost.Check = 0`, music. => **every title visit resets the character to Sonic** (attract demos therefore always
   run as Sonic; Start.txt:427-433 additionally maps Amy -> Sonic).
3. **Title/Start.txt** (object type "Start"): startup sends `game.callbackParam0 = false` +
   `EngineCallback(NOTIFY_LEVEL_SELECT_MENU)` (505-508), loads Title/Title.gif (shared with Sega, Sonic, Logo,
   Background, LiteRibbon). `START_SETUP` (260-322): "PRESS BUTTON" flashes; **B -> `NOTIFY_BACK_TO_MAINMENU`**
   (265-267); Start/A/`input.pressButton` -> `START_GOTO_MENU` and spawns **Select** in `Object[+1]` (292-297);
   1550 idle frames -> `START_GOTO_DEMO` (361-439). Left/Right are unused here (`TouchStart_HandleCheatCodes` is never
   called).
4. **Title/Select.txt** (Origins-only object, all code unconditional). Carousel of
   GAME START / (CONTINUE, disabled) / TIME ATTACK / SETTINGS / SOUNDTRACK / EXTRAS / EXIT, **Left/Right** moves
   (`SELECT_MAIN` 132-227), Start/A/C confirms (190-212), B returns to Start (214-220). States 0-17 are used.
   - GAME START -> `SELECT_CHARSELECT` (451-459): `game.continueFlag = false`, `game.callbackResult = -1`,
     `game.callbackParam0 = 0`, **`EngineCallback(NOTIFY_CHARACTER_SELECT)`** -> Origins' own character + save-slot
     UI -> `SELECT_RECIEVERESULT` (461-486) waits:
     `callbackResult == 0` -> back to `SELECT_MAIN`; `> 0` and `continueFlag` -> `SELECT_FADEOUT_E` ->
     `Engine.State = RESET_GAME` (Origins continues the save natively); `> 0` new game -> `ReadSaveRAM()` (the
     chosen character's array) -> fade -> `SELECT_GAMESTART` (239-265): writes a fresh record at SaveRAM[0..7]
     (PLP, 3, 0, 0, 0, 0, 50000, 0), `WriteSaveRAM()`, `LoadVideo("Opening")` -> `SELECT_CONTINUE` (267-387): reads
     the record back (`Options.GameMode = MODE_SAVEGAME`, `Options.SaveSlot = 0`, `ListPos--`, special-stage
     handling for >= 80, Good_Future bits), `game.callbackParam0 = 0` + `EngineCallback(NOTIFY_SAVESLOT_SELECT)`,
     `LoadStage()`.
   - EXTRAS -> `SELECT_EXTRAS` (428-442) - note the game's own trick: `game.callbackParam0 = PLAYER_SONIC_A` +
     `EngineCallback(NOTIFY_PLAYER_SET)` "Force Sonic's SaveRAM Data to load" - exactly what NoSwap needs.
   - Art: Title/Select.gif (512x256) is loaded **only by Select**; frames 0-17 used, comment at 697-698 says almost half
     the sheet is unused -> room for picker icons / save-screen art (ship it extended under the original name - no
     other object loads it, so no sprite-memory duplication).

**Picker hook (recommended): inside Select**, on the GAME START entry, **Up/Down** cycles
Sonic-&-co (vanilla) -> extra 1 -> 2 -> 3 (Left/Right already move the carousel). `Object.Value4` of Select is unused
(Select aliases Value0-3, 5-7) -> picker state for this visit; remember the last pick across title visits in a global
(`Leaderboard.Offset`) because Sonic.txt:52 resets PLP and Select is re-created each time. Draw the icon/name in
`ObjectDraw` (572-625) when `DisplaySelection == SELECTION_GAMESTART`. **Do not write Stage.PlayerListPos until the
game starts** (otherwise attract demos run as the extra).

Alternative: Start's `START_SETUP` Left/Right like S1 ("while PRESS BUTTON flashes") - but Start draws from
Title/Title.gif, which six title objects share.

**Extras' save screen:** at the confirm (202-204) branch to new states (18+) instead of `SELECT_CHARSELECT`:
`NOSWAP_SAVESELECT` (Select draws 3 slots per extra from records at SaveRAM[1024+] after
`game.callbackParam0 = 0` / `EngineCallback(NOTIFY_PLAYER_SET)` / `ReadSaveRAM()`; B -> `SELECT_MAIN`) ->
`NOSWAP_START`: set `Stage.PlayerListPos = 7..9`, `Options.GameMode = MODE_NOSAVE` (0), write the active-slot note
(`SaveRAM[1023]`) + `WriteSaveRAM()`, then either a new game (copy `SELECT_GAMESTART`'s globals: lives 3, score 0,
ScoreBonus 50000, `LoadVideo("Opening")`) or a continue (copy `SELECT_CONTINUE` 267-387 verbatim, reading the NoSwap
record instead of SaveRAM[0], **without** `NOTIFY_SAVESLOT_SELECT`) and `LoadStage()`. `MODE_NOSAVE` only disables
the game's own `MODE_SAVEGAME` writes (ActFinish 491/624, DeathEvent 123, StageFinish 533/706, R8/FadeScreen 127
leaderboard); special rings still work (`SpecialRing.txt:309` blocks only modes > SAVEGAME).

Menu/LoadSaveMenu.txt (39 PLP lines) is the 2011 4-slot save/character menu. On Origins it is **dead**: only
`MAINMENUMODE_CHARASELECT` opens it (MenuButton.txt:1096-1110) and no script sets that mode (the decompiler comment at
:785 says so too). It draws the slot's character icon **by ID** (`TempValue0 = PlayerListPos; <<= 1; += 4`,
:256-263), so ID 7 would draw frame 18. Useful only as a reference for slot drawing/continue logic.

Other menus that reach gameplay force Sonic: ExtrasMenu.txt:468-474 (DA Garden / sound test / **stage select**),
TAttack/MenuControl.txt:322 and :1188-1192. Missions/Boss Rush are booted natively by Origins.

## 6. Time travel (Q5)

- Trigger: TimeWarp object (Global/TimeWarp.txt). At the end of the warp run: `Warp.*` globals capture position,
  speeds, `Player.State` (Static/SpinningTop/WaterCurrent -> Air), animation, frame, angle (51-78);
  `StageSetup_SaveStageState` (:105, StageSetup.txt:92-137) stores per-object flags in **SaveRAM[7168..8191]**
  (in memory, no WriteSaveRAM); **all 1184 entities are reset** (115-119); the cutscene spawns **Warp Sonic**
  (158-160) and sends `game.callbackParam0 = period` + `EngineCallback(NOTIFY_FUTURE_PAST)` (174-177).
- `TIMEWARP_TRAVEL` (209-279): `Stage.ListPos` +1 (past), +2 (good future), +3 (bad future), or back (-1/-2/-3; in
  missions bad future -2), `NOTIFY_STATS_PARAM_1`, `NOTIFY_GOTO_FUTURE_PAST` (param = new period), `LoadStage()`, then
  `Warp.Timer = 205` so PlayerObject keeps the Mini state (PlayerObject.txt:4697-4703).
- New stage: PlayerObject `ObjectStartup` (`ReadSaveRAM()` :4707, spawn, `Player_Setup_Startup` - LoadAnimation and
  abilities are re-applied from `Stage.PlayerListPos`), then StageSetup `ObjectStartup` restores the `Warp.*` values
  and Rings (356-377) and `StageSetup_LoadStageState`; TitleCard gives 8000 invincibility (R1_TitleCard.txt:88).
- **Nothing in the chain writes `Stage.PlayerListPos`**, so the extra survives time travel, act changes, special
  stages, deaths and checkpoints. The only PLP writers on Origins are: Title/Sonic.txt:52 (reset to Sonic),
  Start.txt:431 (Amy->Sonic in demos), Select.txt:275 (continue), ExtrasMenu.txt:473, TAttack/MenuControl.txt:322,
  Secrets/SoundTest.txt:310 (+ Origins natively after NOTIFY_CHARACTER_SELECT).
- `Warp.State` stores a PlayerObject function ID; NoSwap ability states defined in PlayerObject have stable IDs
  across stages (same global compile order), so warping mid-ability is safe. Per-stage ability scratch
  (`Object[5]`) is wiped - re-init on startup.
- Open question worth one test: the 7168-8191 time-travel state survives the `ReadSaveRAM()` at PlayerObject:4707
  only if Origins' ReadSaveRAM doesn't overwrite that range (break a monitor, time-travel, come back). Keep NoSwap
  data out of 7168-8191 regardless.
- Warp Sonic's art is a per-character frame block (WarpSonic.txt:167-203): **extras need a case** or the cutscene
  draws nothing/garbage (row in section B).

---------------------------------------------------------------------------------------------------------------

## A. Player objects

### Players/PlayerObject.txt (global object 0)
| Line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| 70-74 | `#alias 5 : PLAYER_AMY_A` | no alias | **alias** (+ NoSwap aliases: save base/slots, scratch slot) |
| 162 | `#function Player_BadnikBreak` (first function => **function ID 0**) | see 4521 | info |
| 354 | `if Stage.PlayerListPos == PLAYER_SONIC` -> `KILL_ENEMY_ATTR_SPINDASH` stat | - | fine |
| 815 | `if Stage.PlayerListPos == PLAYER_TAILS_A` (roll anim speed 120) | - | fine |
| 1357-1426 | `switch Stage.PlayerListPos` / `case PLAYER_SONIC_A` / `case PLAYER_TAILS_A` (idle: stopped/waiting) ... `case PLAYER_KNUCKLES_A` ... `case PLAYER_AMY_A` (Player_State_Ground, Origins block) | no idle/wait animation: standing still keeps the last walking frame | **add case** to the Sonic/Tails group (anchor `\t\t\t\tswitch Stage.PlayerListPos\n\t\t\t\tcase PLAYER_SONIC_A\n\t\t\t\tcase PLAYER_TAILS_A`). "I'm outta here" stays Sonic-only (:1366) |
| 1638, 1716, 1829 | `if Stage.PlayerListPos == PLAYER_TAILS` (drop dash / JumpAbility gating) | takes the non-Tails path (JumpAbility called while `YVelocity >= JumpCap` and `ANI_JUMPING`) | fine |
| 1739, 1851 | `if Stage.PlayerListPos == PLAYER_AMY` -> `Player_Action_HammerDash` else `Player_Action_Spindash_S2` on a charged drop-dash landing | never charged (see 3381) | fine |
| 3250-3272 | `Player_SetJumpOffset`: `if ... == PLAYER_SONIC  Player.JumpOffset = -5` ... AMY -4 (Origins block) | JumpOffset stays 0 (reset by ResetObjectEntity) -> rolling/jumping sprite offset & camera 5px off | **add case** (-5, or the extra's own) |
| 3307-3328 | `switch Stage.PlayerListPos` / `case PLAYER_SONIC_A` / `LoadAnimation("MiniSonic.Ani")` ... (R8 shrink laser) | keeps full-size sprites while `Mini_PlayerFlag` shrinks the rest | **design**: add `LoadAnimation("MiniExtra1.ani")` case **and** the matching restore at 3347-3364, or neither (placeholder: neither) |
| 3347-3364 | `if Stage.PlayerListPos == PLAYER_SONIC  LoadAnimation("Sonic.Ani")` ... (size restore) | - | pair with 3307 |
| 3368 | `CallFunction(Player_SetJumpOffset)` | - | covered by 3250 |
| 3376-3417 | `Player_HandleDropDash`: charge only for PLAYER_SONIC / PLAYER_AMY, Tails cancels | `DropDashCharge = -1` -> **no drop dash** | fine (matches Metal's approved "no drop dash"); add to the Sonic test if an extra should drop-dash |
| 4346 | `if Stage.PlayerListPos == PLAYER_KNUCKLES` (MMZ3 roof) | - | fine |
| 4467-4503 | `if Mini_PlayerFlag == false` / `if Stage.PlayerListPos == PLAYER_SONIC  LoadAnimation("Sonic.Ani")` ... else Mini* | **no animation file -> invisible player / garbage** | **own startup case**: `if Stage.PlayerListPos >= 7` -> `LoadAnimation("Extra1.ani")` (mini: MiniExtra1 or Extra1) |
| 4521-4561 | `if Stage.PlayerListPos == PLAYER_SONIC  Player.JumpAbility = Player_State_Static` / `Player.ActionPeelout = Player_Action_Peelout_S2|CD` / `Player.ActionSpindash = ...` (TAILS/KNUX/AMY blocks) | **JumpAbility/ActionPeelout/ActionSpindash stay 0 => `CallFunction(0)` = `Player_BadnikBreak` with the player as `Object`: jumping (`ANI_JUMPING`) turns the player entity into a flower** (1718/1724/1899/1932) | **own startup case (critical)**: copy Sonic's block (Static or the extra's ability function; Peelout/Spindash S2 vs CD by `Options.OriginalControls`), `JumpStrength` override like Knuckles at 4543, clear the NoSwap scratch slot, `LoadPalette` the extra's colours (section I) |
| 4565-4573 | `GetAnimationByName(ANI_SPINNING_TOP, "Spinning Top")` ... `"3D Ramp 1"`-`"3D Ramp 7"`, `"Size Change"` | these ANI_* are looked up **by name** in the loaded .ani | Extra1.ani must contain those names (section I) |
| 4589 | `if Stage.PlayerListPos != PLAYER_SONIC_A  Object[+1].Type = Blank` (debug) | - | fine |
| 4705-4709 | `if Options.StageSelectFlag == false  ReadSaveRAM()` | reloads the current Origins character's array every stage | info (NoSwap writes must `WriteSaveRAM()` at once) |
| 4735 | `if Object[ArrayPos1].PropertyValue == Stage.PlayerListPos` (character spawn points) | never matches -> standard spawn (PropertyValue 0) | fine |
| 4767-4771 | `if TempValue7 > 0 ... CallFunction(Player_Setup_Startup) end if #endplatform` | - | current smoke-test anchor (build_soniccd.py) |
| (new) | - | - | **add the v3 NoSwap save/helper functions** (declare with `#function`), e.g. before `function Player_BadnikBreak` (:246) with `#function` lines after :243 |

Callbacks in this file: `NOTIFY_KILL_ENEMY` 361, `NOTIFY_STATS_CHARA_ACTION2` 442/3426/3561/3725/4382 (Knux/Amy
moves), `NOTIFY_STATS_CHARA_ACTION` 1308 (Tails flight), `NOTIFY_DEATH_EVENT` 2585/2713, `NOTIFY_STAGE_RETRY` 2660
(only `game.oneStageFlag`), `CALLBACK_PAUSE_REQUESTED` 542 (Standard: Origins' native pause) - all fine.

### Players/TailsObject.txt
| 203-206 | `if Stage.PlayerListPos == PLAYER_TAILS_A  LoadSpriteSheet("Players/Tails1.gif")` / `Object[1].Type = TypeName[Tails Object]` | - | fine (slot 1 stays blank for extras) |

---------------------------------------------------------------------------------------------------------------

## B. Global objects

The per-character art in CD is **per sheet, same coordinates**: `Global/Items2.gif` vs `Items2_t/_k/_a.gif`
(256x256, differences inside x 4-111, y 132-245: signpost face at 34,132, flip frames, etc.) and `Global/Display.gif`
vs `Display_t/_k/_a.gif` (256x274, differences y 189-273: life icons 187,189/204,189/237,223, "SONIC GOT" name at
0,206, game-over text, title-card bits; Knuckles uses the extra rows 257+). So an extra needs **one copy of each
sheet** (`Items2_x1.gif`, `Display_x1.gif`, or Sonic's as placeholder) and one extra `if` per chain. Origins already
loads Display.gif *and* Display_k.gif in Knuckles' stages (many level objects load Display.gif unconditionally for
editor icons), so an extra's copy costs the same sprite memory as playing Knuckles.

| File:line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| ActFinish.txt:157 | `Object.RingBonus = Player.Rings` | - | fine |
| ActFinish.txt:200-211 | `EngineCallback(NOTIFY_STATS_ENEMY)` / `(NOTIFY_STATS_RING)` / **`EngineCallback(NOTIFY_ACT_FINISH)`** / Knux-only `NOTIFY_STATS_SAVE_FUTURE` | credits the act to Origins' current character (Sonic) | **hide notify** (ACT_FINISH; stats optional) |
| ActFinish.txt:310, 329 | `if Stage.PlayerListPos == PLAYER_SONIC_A` -> `SetAchievement(2, 100)` | no achievement | fine |
| ActFinish.txt:395-406, 797-803 | `if game.oneStageFlag != false` ... `NOTIFY_STAGE_RETRY` / `ACTFINISH_HOLDOVERRESTART` waits | only in My Data & Rankings replays | fine (unreachable for extras) |
| ActFinish.txt:491-516 | `if Options.GameMode == MODE_SAVEGAME` / `ArrayPos1 = Options.SaveSlot` / `ArrayPos1 <<= 3` / `SaveRAM[ArrayPos1] = Stage.PlayerListPos` ... `SaveRAM[ArrayPos1] += 81` ... `WriteSaveRAM()` (special ring at act end) | skipped (NOSAVE) | **save: full, variant "+81"** (next zone saved as a pending special stage) |
| ActFinish.txt:624-648 | same record, `SaveRAM[ArrayPos1]++` (normal act end) | skipped | **save: full** |
| ActFinish.txt:660 | `if Stage.PlayerListPos == PLAYER_SONIC` -> `SetLeaderboard` (time attack) | - | fine |
| ActFinish.txt:839-842 | Knuckles "KNUCKLES" name draw | - | fine |
| ActFinish.txt:894-909 | `if Stage.PlayerListPos == PLAYER_SONIC_A  LoadSpriteSheet("Global/Display.gif")` ... `_t` / `_k` / `_a` | **results screen drawn from the wrong sheet** | **sheet** (Display.gif placeholder; own: Display_x with the name at 0,206 136x16 and "<NAME> MADE A GOOD" at 0,240) |
| ActFinish.txt:912-918, 971-983 | `if ... == PLAYER_KNUCKLES` frame 0 / 20-22 `else` Sonic's | uses Sonic's layout | fine (no shift) |
| AttractMode.txt:154-167 | Display sheet chain (REGULAR_STAGE only) | object never draws | **sheet** (safety; only reachable in demos) |
| BlueShield.txt:55-68 | Items2 sheet chain | shield frames garbage | **sheet** |
| BrokenMonitor.txt:107-111 | `if ... == PLAYER_SONIC_A  PlaySfx(SFX_G_1UP)` else `SFX_G_ACHIEVEMENT` | plays the non-Sonic 1UP jingle | fine (optional add case) |
| BrokenMonitor.txt:122 | Sonic-only `SetAchievement(4, 100)` | - | fine |
| BrokenMonitor.txt:99, 183, 205 | `NOTIFY_ADD_COIN` (coin mode) | - | fine |
| DeathEvent.txt:115-133 | `if Object.State == DEATHEVENT_GAMEOVER` ... `if Options.GameMode == MODE_SAVEGAME` / `ArrayPos1++` / `if SaveRAM[ArrayPos1] < 3  SaveRAM[ArrayPos1] = 3` / `WriteSaveRAM()`; then title screen | skipped | **save: gameover** |
| DeathEvent.txt:136-139 | `EngineCallback(NOTIFY_TIME_OVER)` | - | fine |
| DeathEvent.txt:184-194, 282-299 | oneStageFlag `NOTIFY_STAGE_RETRY` + wait | unreachable | fine |
| DeathEvent.txt:353-366 | Display sheet chain ("GAME/TIME OVER") | garbage text | **sheet** |
| Explosion.txt:27-39 | Items2 sheet chain | garbage explosions | **sheet** |
| FadeMusic.txt:26 | `NOTIFY_DEBUGPRINT` | - | fine |
| GoalPost.txt:41 | Sonic-only achievement | - | fine |
| GoalPost.txt:60-72 | Items2 sheet chain | garbage goal post | **sheet** |
| HUD.txt:199 | `NOTIFY_FUTURE_PAST` (coin mode) | - | fine |
| HUD.txt:411-423 | `if Stage.PlayerListPos == PLAYER_SONIC_A  LoadSpriteSheet("Global/Display.gif")` ... `Display_K.gif` / `Display_A.gif` (then the Origins `Object[24].DrawFunction` setup at 425-429 inside the same block) | **whole HUD garbage** | **sheet** (insert after the Amy `end if`, before `if Engine.DeviceType`). Life icon frames 17-20 read Display coordinates, not the ID: no ID mapping needed |
| LampPost.txt:86 | `EngineCallback(NOTIFY_TOUCH_CHECKPOINT)` | - | optional hide |
| LoseRing.txt:107, 123 | coin / Sonic-only achievement | - | fine |
| Monitor.txt:98-114 | Knux glide / Amy hammer also break monitors | - | fine (an extra attack anim can reuse ANI_HAMMER_JUMP/DASH slots, see I) |
| Monitor.txt:279-295 | `if ... PropertyValue == SCREEN_SONIC` -> TAILS/KNUCKLES/AMY 1UP screens | extras keep the Sonic 1UP icon | fine; own art = new SCREEN value/frame #11 on Items.gif (Monitor 199-221) + BrokenMonitor frame #11 (281-316) + its switch 171-213 |
| MSProjector.txt:104-110, 129-133, 136 | Amy hammer / Amy stats / Sonic achievement | - | fine |
| PauseMenu.txt:873-881 | `if Stage.PlayerListPos != PLAYER_TAILS_A` Sonic mini frames else Tails | Sonic frames | fine (script pause only with DevMenuFlag) |
| RedSpring.txt:59, 107; YellowSpring.txt:58, 106, 269, 338, 407 | `if ... == PLAYER_KNUCKLES` + `Player_State_LedgePullUp` | - | fine |
| Ring.txt:50, 58, 74 | coin / 1UP sfx / achievement | - | fine |
| SignPost.txt:66 | `EngineCallback(NOTIFY_TOUCH_SIGNPOST)` | - | **hide notify** |
| SignPost.txt:249-263 | `if ... == PLAYER_SONIC_A  LoadSpriteSheet("Global/Items2.gif")` ... `Items2_K.gif` / `Items2_A.gif` (uppercase here only) | **sign post garbage** | **sheet**; own face: frame #5 `SpriteFrame(-24, -44, 48, 32, 34, 132)` region on Items2_x (and flip frames 1,183 / 25,150 / 1,216) |
| SmokePuff.txt:28-40 | Items2 sheet chain (`_K`/`_A` uppercase) | garbage smoke | **sheet** |
| SpecialRing.txt:204-216 | Items2 sheet chain (Origins block runs to 236) | garbage giant ring | **sheet** |
| StageSetup.txt:207, 216-220 | coin / `if ... == PLAYER_SONIC_A  PlaySfx(SFX_G_1UP)` | non-Sonic jingle | fine |
| StageSetup.txt:92-188, 356-390 | time-travel state in SaveRAM[7168-8191]; cleared at 379-383 when not warping | - | info (keep NoSwap out of 7168+) |
| TimeWarp.txt:89 | Sonic-only achievement | - | fine |
| TimeWarp.txt:176, 269, 271 | `NOTIFY_FUTURE_PAST`, `NOTIFY_STATS_PARAM_1`, `NOTIFY_GOTO_FUTURE_PAST` (period only) | - | fine |
| TouchControls.txt:114 | debug exit: `if ... == PLAYER_TAILS_A  Object[+1].Type = Tails Object` | - | fine |
| Transporter.txt:104, 136 | Amy hammer / Sonic achievement | - | fine |
| **WarpSonic.txt:167-203** | `if Stage.PlayerListPos == PLAYER_SONIC_A  LoadSpriteSheet("Global/Items3.gif")` + frames #0-4 ... Tails2 / KTE5 / Amy3 blocks | **time-warp cutscene character has no frames (draws garbage/nothing)** | **frame block** (placeholder: Sonic's Items3 block; own: 5 "bouncing" frames on the extra's player sheet, e.g. `Players/Extra1_3.gif`) |

---------------------------------------------------------------------------------------------------------------

## C. Title cards and flower pods

| File:line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| TitleCards/R1,R3,R4,R5,R6,R7,R8_TitleCard.txt:217-230 | `if Stage.PlayerListPos == PLAYER_SONIC_A  LoadSpriteSheet("Global/Display.gif")` ... `_k` / `_a` (7 files, identical text) | **title card garbage** | **sheet** x7 (patch_n expected 7) |
| TitleCards/R2_TitleCard.txt:207-220 | same | only used by R21A (D.D. mission) | mission only |
| TitleCards/R9_TitleCard.txt:207-211 | `if ... == PLAYER_SONIC_A` Display else `Display_t` | not in any StageConfig | none |
| TitleCards/R*_TitleCard.txt:16, 88 | `#alias Object[0].Value4 : Player.InvincibleTimer` / `= 8000` on warp arrival | - | info |
| FlowerPod/PodSeed.txt:69-82 | Items2 sheet chain | garbage seeds (R1/R3-R7 act 3) | **sheet** |
| FlowerPod/R1,R3,R4,R5,R6,R7_FlowerPod.txt:~200-213 | `if ... == PLAYER_KNUCKLES` / `PLAYER_AMY` (glide/hammer hits) | - | fine |
| FlowerPod/R*_FlowerPod.txt:235-246 | `EngineCallback(NOTIFY_BOSS_END)` | - | optional hide |
| FlowerPod/R7_FlowerPod.txt:266-271 | `if ... == PLAYER_SONIC_A` -> remove the flower pod (not in time attack) | extras keep the pod, like Tails/Knux/Amy | fine / design |

---------------------------------------------------------------------------------------------------------------

## D. Special stage (SS1-8, no global objects)

| File:line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| Special/Sonic.txt:113-114 | `#alias 0 : PLAYER_SONIC_A` / `#alias 1 : PLAYER_TAILS_A` | - | **alias** (local) |
| Special/Sonic.txt:434, 564 | `EngineCallback(CALLBACK_PAUSE_REQUESTED)` (Standard) | native pause | fine (test the pause UI with an extra) |
| Special/Sonic.txt:1787-1800 | `if ... == PLAYER_SONIC_A  LoadSpriteSheet("Special/Sonic.gif")` ... `Special/Knuckles.gif` / `Special/Amy.gif` | **player drawn from the wrong sheet** | **sheet** (placeholder Special/Sonic.gif; own `Special/Extra1.gif` in Special/Sonic.gif's layout) |
| **Special/Sonic.txt:1919-1937** | frames 46-47 (braking) `if ... == PLAYER_SONIC_A  SpriteFrame(-21, -48, 42, 48, 135, 410)` ... per character | **frames 48+ (fan, falling, ...) shift down by 2 -> wrong animations** | **frame block: add case** (anchor on the Sonic `if` + first SpriteFrame; Knux/Amy blocks are byte-identical to Sonic's) |
| Special/Sonic.txt:1951 | `if Stage.PlayerListPos != PLAYER_TAILS_A` (Sonic falling frames) | Sonic's | fine |
| Special/StageFinish.txt:50-51 | aliases | - | **alias** |
| Special/StageFinish.txt:168, 484 | Sonic-only achievement / 1UP sfx | - | fine |
| Special/StageFinish.txt:474, 587, 760 | `NOTIFY_ADD_COIN`, `NOTIFY_STATS_RING`, `NOTIFY_STATS_PARAM_2` | - | fine |
| Special/StageFinish.txt:533-567 | `if Options.GameMode == MODE_SAVEGAME` ... `SaveRAM[ArrayPos1] = Stage.PlayerListPos` ... `SaveRAM[ArrayPos1]++` ... `WriteSaveRAM()` (STAGEFINISH_LOADNORMAL; [7] not written) | skipped | **save: full** |
| **Special/StageFinish.txt:677-699, 701-734** | `STAGEFINISH_CHECKRETRYCOND`: `game.callbackResult = -1` ... `EngineCallback(NOTIFY_SPECIAL_RETRY)` -> `STAGEFINISH_SAVE`: `if game.callbackResult >= false` ... record save ... `WriteSaveRAM()` | Origins' retry/result UI with an unknown ID (S1/S2: blank or garbage screen) | **guard notify** (PLP=0 before 694, restore inside the `>= false` branch at 702; all 8 StageFinish values are aliased - stash in a global such as `Leaderboard.Offset` or `Object[5].Value0`) + **save: full** (706-734) |
| **Special/StageFinish.txt:1092-1111** | frames 27-28 "small foot-tapping player icons" per character | **frames 29-35 (coin icon, x1, sparkles, "COIN") shift down by 2**; continues drawn with frames 27/28 (:952-964) show the coin icon | **frame block: add case** (placeholder Sonic's 169,24 / 186,24; own art needs all 5 language copies of Special/ScoreScreen*.gif) |
| Special/PauseMenu.txt:1202-1233 | frames 0-2 mini character per ID | frames 3+ shift (script pause only with DevMenuFlag) | **frame block: add case** (low priority) |
| Special/TimeStone.txt:67 | `EngineCallback(NOTIFY_TOUCH_EMERALD)` | may credit a time stone to Origins' Sonic | open question (as S2 D7) |
| Global/AttractMode.txt (SS1/SS6) | `Stage.ActiveList != REGULAR_STAGE` branch loads Special/Objects.gif | - | fine |

---------------------------------------------------------------------------------------------------------------

## E. Zone-specific

| File:line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| R1/Amy.txt:548-553 | `if Stage.PlayerListPos != PLAYER_SONIC_A  Object[ArrayPos0].Type = TypeName[Blank Object]` (Amy NPC, PPZ1) | no Amy (as for Tails/Knux/Amy) | fine / design (make extras "Sonic" here to get the story NPC) |
| R3/Amy.txt:271 | Amy NPC only for Sonic (CCZ) | no Amy | fine / design |
| R7/Amy1.txt:150 | Amy (kidnap scene) only for Sonic | no Amy | fine / design |
| R8/Amy.txt:115 | `if ... == PLAYER_SONIC_A  DrawSpriteFX(...)` (MMZ3 ending Amy) | not drawn | fine / design |
| R1/TunnelPath.txt:735-752 | per-character sheet + frame #0 (the character-shaped wall hole) | **frame #0 missing** | **frame block** (placeholder Sonic's `R1/Objects.gif` 34,175 32x32; own: a silhouette on a sheet copy) |
| R3/ScoreChute.txt:249-277 | `if Stage.PlayerListPos == PLAYER_SONIC  LoadSpriteSheet("R3/Objects.gif")` + frames #0-2 ... (globals, Origins block) | **frames #0-2 missing** | **frame block** (placeholder Sonic's) |
| R6/IceBlock.txt:244-279 | per-character sheet + frames #0-4 (character frozen in ice) | **frames missing** | **frame block** (placeholder Sonic's `R6/Objects.gif`) |
| R5/BossExplosion.txt:42-55 | Items2 sheet chain | garbage | **sheet** |
| R4/GrabPole.txt:40-44 | `if ... == PLAYER_SONIC_A  Player.XPos += 0x140000` else `0x100000` | Tails' hand offset | fine (optional add case) |
| R1/Boss_Bumper:82, Boss_Face:658/666/685, BreakWall:50/53, Ramp3D:377, TubeSwitch:42; R3/Flipper:102/183, TubeSwitch:46; R4/BossBubble2:62/70, Eggman1:427/433/462, Eggman2:694/700/735, Water:161; R5/BossPlatform:1016, BreakWall:87/90, TubeSwitch:47; R6/EggmanMobile:417/425, EggmanStatue:127/141/146, R6BounceFloor:38, TubeSwitch:50; R7/TubeSwitch:36; R8/EggMobile:1699/1708 | Knuckles/Amy-only abilities (glide, climb, hammer) | - | fine |
| R6/AngelRing.txt:62; R7/MetalSonic.txt:391; R8/EggMobile.txt:1346 | Sonic-only `SetAchievement` | - | fine |
| R7/InvisibleBarrier.txt:41 | Sonic-only loop that does nothing | - | fine |
| R7/MetalSonic.txt:531 | `LoadAnimation("MetalSonic.Ani")` (the race boss) | - | **name clash**: never name an extra's file `MetalSonic.ani` - use Extra1.ani |
| Boss notifies | `NOTIFY_KILL_BOSS` R1/Boss_Face:806, R3/BossBody:320, R4/Eggman2:717, R5/BossPlatform:859, R6/EggmanMobile:455, R7/VerticalDoor:58, R8/EggMobile:1782; `NOTIFY_BOSS_END` R1/Boss_Face:809, R3/BossBody:323, R4/Eggman2:720, R5/BossPlatform:863, R6/EggmanMobile:458, R7/Amy1:64, R7/MetalSonic:336, R8/FadeScreen:77, FlowerPods | - | optional hide (S1 test: crediting is not triggered by these kinds of notifies) |
| R4/BGEffectsA1:147, A2:153, B:144, B2:152, C:145, C2:152, D:144, D2:152 | `LoadPalette("R4?_WaterPal.act", 7, 0, 0, 256)` (full underwater bank) | extras' custom colours revert underwater | **palette**: re-apply the extra's colours to bank 7 right after (8 files) |

---------------------------------------------------------------------------------------------------------------

## F. Ending / credits

### R8/FadeScreen.txt (MMZ3 after the boss; FADESCREEN_AMY state 69-268)
| Line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| 77 | `EngineCallback(NOTIFY_BOSS_END)` | - | optional hide |
| 83-92 | oneStageFlag: `NOTIFY_ACT_FINISH` + `NOTIFY_STAGE_RETRY` | unreachable | fine |
| 125-167 | `EngineCallback(CALLBACK_FINISHGAME_NOTIFY)` ... stats ... **`EngineCallback(NOTIFY_ACT_FINISH)`** (150) ... `NOTIFY_GOOD_ENDING` (162/165) | Origins plays the ending/credits natively for its current character (Sonic) | **hide notify** (ACT_FINISH 150); keep GOOD_ENDING (drives the movie) |
| 217-239 | `if SaveRAM[36] == false` (Tails unlock) ... `Stage.ListPos = STAGE_P_TITLE` / **`Engine.State = ENGINE_WAIT`** | control returns to Origins | **save: complete** here (before 217): vanilla CD has **no** "completed" marker in the slot record, so NoSwap must define one (e.g. record[3] = a sentinel) |
| 222-224 | `SaveRAM[36] = true` / `WriteSaveRAM()` (non-classic) | writes Sonic's array (loaded) | fine |
| 250-251 | `NOTIFY_STATS_MOVIE` | - | fine |

### Credits (global=1)
| Credits/CreditsControl.txt:136, 277 | `NOTIFY_STATS_MOVIE` / `LoadSpriteSheet("Global/Display.gif")` unconditional | - | fine |

---------------------------------------------------------------------------------------------------------------

## G. Title / menus

| File:line | Quote | ID 7 result | Treatment |
|---|---|---|---|
| Title/Sonic.txt:52 | `Stage.PlayerListPos = PLAYER_SONIC_A // PLAYER_SONIC in origins` | resets any extra on every title visit | fine (keep; picker remembers its choice elsewhere) |
| Title/Start.txt:265-267 | B -> `EngineCallback(NOTIFY_BACK_TO_MAINMENU)` | - | fine |
| Title/Start.txt:292-297 | spawns `TypeName[Select]` in `Object[+1]` | - | picker lives in Select |
| Title/Start.txt:427-433 | demo: `if Stage.PlayerListPos == PLAYER_AMY  Stage.PlayerListPos = PLAYER_SONIC` | unreachable if the picker doesn't write PLP early | fine |
| Title/Start.txt:505-508 | `game.callbackParam0 = false` / `EngineCallback(NOTIFY_LEVEL_SELECT_MENU)` | - | fine |
| Title/Select.txt:105 | `#alias 0 : PLAYER_SONIC_A` | - | **alias** |
| Title/Select.txt:110-130 | `SELECT_INIT` | - | init picker from the remembered global |
| Title/Select.txt:132-227 | `SELECT_MAIN` (Left/Right carousel, confirm 202-212) | - | **picker** (Up/Down on GAME START) + branch to NoSwap states on confirm |
| Title/Select.txt:239-265, 267-387 | `SELECT_GAMESTART` / `SELECT_CONTINUE` (vanilla record write/read, `NOTIFY_SAVESLOT_SELECT` 382-383) | - | template for NoSwap new game / continue |
| Title/Select.txt:428-442 | `game.callbackParam0 = PLAYER_SONIC_A` / `EngineCallback(NOTIFY_PLAYER_SET)` (Extras) | - | template for "switch to Sonic's save" |
| Title/Select.txt:451-486 | `NOTIFY_CHARACTER_SELECT` + wait on `game.callbackResult` | - | **picker branch**: extras never call it |
| Title/Select.txt:572-625, 628-699 | draw / `LoadSpriteSheet("Title/Select.gif")` frames 0-17 | - | picker + save-screen art appended as frames 18+ |
| Title/Sega.txt:46-48 | `ReadSaveRAM()` / `Options.Soundtrack = SaveRAM[38]` | - | fine |
| Menu/LoadSaveMenu.txt (39 lines) | 2011 save menu | dead on Origins | none |
| Menu/ExtrasMenu.txt:468-474 | `NOTIFY_LEVEL_SELECT_MENU` / `game.callbackParam0 = 0` / `NOTIFY_PLAYER_SET` / `Stage.PlayerListPos = PLAYER_SONIC` | extras become Sonic in DA Garden / sound test / stage select | fine (README: "Level select: extras play as Sonic") |
| TAttack/MenuControl.txt:316-328, 1186-1193 | time attack forces Sonic + NOTIFY_PLAYER_SET 0 | - | fine |
| Secrets/SoundTest.txt:310 | `Stage.PlayerListPos = PLAYER_TAILS_A` (secret picture) | - | fine |

### Missions (out of scope, as in S1/S2)
Mission/SignPost2.txt:270-281 and SignPostM094.txt:196-207 (unconditional Items2 chains with the global names),
`NOTIFY_TOUCH_SIGNPOST` Mission/FallSignPost:196, SignPost2:75, SignPostM094:51. Missions/Boss Rush are launched by
Origins with its own character; worth one test that Origins sets PLP itself after an extra was played.

---------------------------------------------------------------------------------------------------------------

## H. Save format (CD on Origins)

- One array per Origins character (8192 ints); `ReadSaveRAM()` loads the current character's array
  (PlayerObject:4707 on every stage start, Sega:46, Select:469, ...). Switch to Sonic's array with
  `game.callbackParam0 = 0` / `EngineCallback(NOTIFY_PLAYER_SET)` / `ReadSaveRAM()` (the game does exactly this in
  Select.txt:431-432). Every NOTIFY_PLAYER_SET in CD passes 0: Select:432, ExtrasMenu:472, TAttack/MenuControl:1192 -
  **no existing site can leak an extra's ID** (unlike S2's LevelSelect/MenuControl:610). NoSwap must also only ever
  send 0.
- Game record at `Options.SaveSlot << 3` (Origins always uses slot 0, Select.txt:271), 8 values:
  `[0]` PlayerListPos, `[1]` lives, `[2]` score, `[3]` **next stage listPos + 1** (0 = empty; **+81** = pending
  special stage, ActFinish:502; continue does `ListPos--` and treats `>= 80` as "special stage, NextZone =
  ListPos - 80", Select:308-358), `[4]` TimeStones (bits), `[5]` SpecialStage.ListPos, `[6]` ScoreBonus,
  `[7]` `(MetalSonic_List << 16) + Good_Future_List` (StageFinish's writes leave [7] alone).
- Fixed indices: 32-35 options (32 flag, 33 BGM vol, 34 SFX vol, 35 controls), 36 Tails unlocked, 38 soundtrack,
  39 time-attack zones unlocked, 40 haptics, 48+ time-attack records (`48 + round*18 + zone*6`, 7 rounds -> up to
  ~173; SRecords at +49), **7168-8191 time-travel object state** (StageSetup). Standalone used 4 slots at 0-31.
  => **SAVE_BASE 1024 and NOSWAP_ACTIVE_SLOT 1023 are free in CD too.**
- Save sites (all gated on `Options.GameMode == MODE_SAVEGAME`, so extras in MODE_NOSAVE skip them):
  ActFinish 491-516 (full, +81), ActFinish 624-648 (full, +1), Special/StageFinish 533-567 (full), 706-734
  (full), DeathEvent 123-132 (gameover: lives >= 3). **No "lives" writes** (unlike S1/S2) and **no completion
  write** - add NoSwap "complete" at R8/FadeScreen (section F). Title/Select 240-258 is the vanilla new-game write.
- The v4 `insert_save_calls` detector won't match (different record order, `Options.SaveSlot`/`SaveRAM` names,
  "+81" variant); write a CD-specific one that expects exactly: ActFinish 2 (one of them "+81"), StageFinish 2,
  DeathEvent 1.

## I. Native callbacks (all `EngineCallback(NOTIFY_*)`, IDs from GameConfig)

None sends `Stage.PlayerListPos` as a parameter (all `game.callbackParam*` assignments checked). The danger is
Origins reading PLP itself while its UI is up (S1/S2 SPECIAL_RETRY finding).

| ID | Name | Active sites | Waits on callbackResult / Origins UI? | Treatment |
|---|---|---|---|---|
| 128 | DEATH_EVENT | PlayerObject 2585, 2713 | no | fine |
| 129 | TOUCH_SIGNPOST | SignPost 66 (missions: FallSignPost 196, SignPost2 75, SignPostM094 51) | no | hide (S1/S2 parity) |
| 130 | HUD_ENABLE | - | - | unused |
| 131 | ADD_COIN | BrokenMonitor 99/183/205, LoseRing 107, Ring 50, StageSetup 207, StageFinish 474 | no | fine (coin mode) |
| 132 | KILL_ENEMY | PlayerObject 361 | no | fine |
| 133 | SAVESLOT_SELECT | Select 383 (LoadSaveMenu 787/1074 dead) | no | extras skip it |
| 134 | FUTURE_PAST | HUD 199 (coin mode), TimeWarp 176 | no | fine |
| 135 | GOTO_FUTURE_PAST | TimeWarp 271 | no | fine |
| 136 | BOSS_END | 14 sites (section E) | no | optional hide |
| 137 | SPECIAL_END | - | - | unused |
| 138 | DEBUGPRINT | FadeMusic 26 | no | fine |
| 139 | KILL_BOSS | 7 sites (section E) | no | optional hide |
| 140 | TOUCH_EMERALD | Special/TimeStone 67 | no | open question |
| 141-146 | STATS_ENEMY / CHARA_ACTION / RING / MOVIE / PARAM_1 / PARAM_2 | ActFinish 200/204, DeathEvent 262/265/268, R8/FadeScreen 137/140/143/148/251, PlayerObject 1308, StageFinish 587/760, TimeWarp 269, Credits 136 | no | fine |
| 147 | **CHARACTER_SELECT** | Select 456 | **yes** (461-486) - Origins' character/save UI | picker bypasses it for extras |
| 148 | **SPECIAL_RETRY** | Special/StageFinish 694 | **yes** (702) - result/retry UI | **guard notify** |
| 149 | TOUCH_CHECKPOINT | LampPost 86 | no | optional hide |
| 150 | ACT_FINISH | ActFinish 207, R8/FadeScreen 150 (85 oneStage) | no | **hide** |
| 151 | 1P_VS_SELECT | - | - | unused |
| 153 | STAGE_RETRY | ActFinish 402, DeathEvent 192, PlayerObject 2660, R8/FadeScreen 90 | yes, but only with `game.oneStageFlag` (My Data & Rankings) | unreachable for extras |
| 154 | SOUND_TRACK | SoundMenu 234 | - | fine |
| 155 | GOOD_ENDING | R8/FadeScreen 162, 165 | - (ending handed to Origins via ENGINE_WAIT) | fine |
| 156 | BACK_TO_MAINMENU | Start 266 | leaves the game | fine |
| 157 | LEVEL_SELECT_MENU | Start 507, ExtrasMenu 470, TAttack 1189 | no | fine |
| 158 | **PLAYER_SET** | Select 432, ExtrasMenu 472, TAttack 1192 (all param 0) | no | fine; **never send 7-9** (crash, S1 test) |
| 159 | EXTRAS_MODE | ExtrasMenu 751, 809 | - | fine |
| 160 | SPIN_DASH_TYPE | OptionsMenu 526 | - | fine |
| 161 | TIME_OVER | DeathEvent 138 | no | fine |
| 162 | TIMEATTACK_MODE | TAttack 318, 991 | - | fine |
| 163 | STATS_BREAK_OBJECT | MSProjector 132, R6/EggmanStatue 144/149 | no | fine |
| 164 | STATS_SAVE_FUTURE | ActFinish 210 (Knuckles only) | no | fine |
| 165 | STATS_CHARA_ACTION2 | PlayerObject 442/3426/3561/3725/4382 (Knux/Amy) | no | fine |
| - | CALLBACK_PAUSE_REQUESTED (13) | PlayerObject 542, Special/Sonic 434/564 | native pause menu | test with an extra |

## J. Animation, sprite and palette notes

- **.ani format** is the same as S1/S2 (tools/sheet2ani.py `read_ani` parses CD's files). CD Sonic.ani has **45**
  animations: 0 Stopped ... 32 Ledge Pull Up (fixed `ANI_*` IDs from GameConfig: STOPPED 0 ... LAUNCHER 28,
  GLIDING_DROP 29, GLIDING_STOP 30, CLIMBING 31, LEDGEPULLUP 32), 33-35 Corkscrew H/V, Finish Pose, **36 "Spinning
  Top", 37-43 "3D Ramp 1-7", 44 "Size Change"** (looked up by name, PlayerObject:4565-4573). Extras' .ani must use
  **CD's Sonic.ani as template**, not S1/S2's (the S1/S2 appended slots 41/42 are 3D Ramp 5/6 here).
- Fixed high IDs: `ANI_HAMMER_JUMP` 45, `ANI_HAMMER_DASH` 46, `ANI_GLIDING` 48. These count as attacks in
  Player_BadnikBreak (PlayerObject:249-261; 45/46 always, 48/30 always), Transporter/MSProjector (48 always, 45/46
  Amy only) and Monitor (Knux/Amy only). An extra's appended attack animation placed at **45** breaks badniks for
  free; put non-attacking appended animations at **49+** (47 is free too).
- Player sheets: Sonic uses Players/Sonic1-4.gif; MiniSonic.ani reuses Sonic1-3. Avoid the name MetalSonic.ani
  (R7 race boss).
- Per-character art is by **sheet copy at the same coordinates** (section B). Sheets that need an extra's copy:
  Global/Display (HUD, results, title cards, game over), Global/Items2 (sign post, explosions, smoke, shield,
  goal post, special ring, pod seeds, boss explosion), Special/<char>.gif, plus frame blocks in WarpSonic,
  R1/TunnelPath, R3/ScoreChute, R6/IceBlock, Special/StageFinish (ScoreScreen x5 languages), Special/PauseMenu.
- **Palette:** player colours live in the global master palette (Data/Palettes/MasterPalette.act, entries 0-95;
  stage palette 96-127, tiles 128-255). Sonic uses 0-15/31, Tails adds 21/29/43/44/58, **Knuckles 70-75, Amy 65-91**.
  In-game sheets leave only **53 and 92-95** unused (the S1/S2 slots 74-80 / 81-95 for Fang/Big collide with
  Knuckles/Amy art here). While an extra plays, Knuckles'/Amy's entries (64-91) are only used by Knux/Amy-only art
  (Display_k/_a, Items2_k/_a, Items monitor icons 9/10, ScoreScreen icons, R3/Objects3) and can be overwritten.
  v3 has no `SetPaletteEntry`: ship an .act and `LoadPalette("NoSwap_Extra1.act", 0, 65, 0, n)` in
  Player_Setup_Startup (runs before stage objects' `CopyPalette(0, n)` palette-cycle setups, e.g.
  R3/PaletteAni_A:28-32), and re-apply to bank 7 after the R4 water palettes (section E). Menus/TA load full bank-0
  palettes, so the engine must be restoring the master palette per stage - re-apply on every stage start.

---------------------------------------------------------------------------------------------------------------

## K. Counts per treatment (Origins-relevant, main game)

| Treatment | Count | Sites |
|---|---|---|
| own startup case | 1 (2 blocks) | PlayerObject 4467-4503 (LoadAnimation), 4521-4561 (abilities) |
| add case (behaviour) | 3 (+1 pair) | PlayerObject 1357 (idle), 3250 (jump offset); Special/StageFinish guard restore; [design pair 3307/3347 mini] |
| sheet (LoadSpriteSheet chain) | 20 | ActFinish 894, AttractMode 154, BlueShield 55, DeathEvent 353, Explosion 27, GoalPost 60, HUD 411, SignPost 249, SmokePuff 28, SpecialRing 204, PodSeed 69, R5/BossExplosion 42, Special/Sonic 1787, TitleCards R1/R3-R8 x7 |
| frame block | 8 | WarpSonic 167, R1/TunnelPath 735, R3/ScoreChute 249, R6/IceBlock 244 (missing frames); Special/Sonic 1919, Special/StageFinish 1092, Special/PauseMenu 1202 (shifting) |
| map ID (ID used as frame) | 0 active | only the dead LoadSaveMenu:256 |
| save sites | 5 blocks / 3 files + 1 new | ActFinish full(+81), full(+1); StageFinish full x2; DeathEvent gameover; new "complete" at R8/FadeScreen |
| hide notify | 3 required (+optional) | ActFinish 207, SignPost 66, R8/FadeScreen 150; optional BOSS_END x14, KILL_BOSS x7, TOUCH_CHECKPOINT, TOUCH_EMERALD |
| guard notify | 1 | Special/StageFinish 694/702 (SPECIAL_RETRY) |
| picker / save screen | 1 file | Title/Select (states 18+, frames 18+ on Select.gif) |
| palette | 1 + 8 | PlayerObject startup; R4 BGEffects x8 (bank 7) |
| alias additions | ~every patched file | v3 has no public alias (or use literal 7/8/9) |
| fine as is | ~70 | Knux/Amy ability checks, Sonic-only achievements/jingles, Tails-only paths, forced-Sonic menus, story NPCs (design) |

Critical if left unpatched: PlayerObject startup (invisible + **jump turns the player into a flower via
CallFunction(0)**), HUD / SignPost / ActFinish / TitleCards / DeathEvent sheets (garbage UI), Special/Sonic sheet +
frame block, Special/StageFinish frame block + SPECIAL_RETRY guard, WarpSonic (time-travel cutscene).

---------------------------------------------------------------------------------------------------------------

## L. Suggested build order / risks

1. **Port the helpers to v3 first** (noswap_common is v4-only): v3 alias block, `add_case`/`patch_n` that understand
   `#platform: Use_Origins` Title-case and CRLF, a CD `insert_save_calls` (section H), `hide_progress_from_origins` and
   `guard_special_retry` that match `EngineCallback(NOTIFY_...)`. Keep the smoke test until the next item works.
2. **PlayerObject**: alias block, own startup case (Extra1.ani from CD Sonic.ani template, abilities, palette
   `LoadPalette`), idle case, jump offset, clear `Object[5]` scratch. Test in R11A with placeholder = Sonic's art.
3. **Sheet chains** (20 sites) with Sonic's sheets as placeholder, then WarpSonic + the three zone frame blocks. Test
   a time warp (R11A past sign) and PPZ tunnel/CCZ chute/WWZ ice.
4. **Special stage**: Special/Sonic sheet + frame block, StageFinish frame block + SPECIAL_RETRY guard. Test getting
   and missing a time stone (the retry UI is the S1/S2 blank-screen trap).
5. **Title/Select picker + extras' save screen**, NoSwap save calls (ActFinish x2, StageFinish x2, DeathEvent,
   R8/FadeScreen complete), hide notifies.
6. Art: Display_x / Items2_x / Special/ExtraN / Warp frames / Select.gif frames; palettes (.act) incl. R4 water.

Risks / open questions:
- **Platform tokens** are inferred (Standard active, Mobile/Haptics/Decomp not). A one-line marker test in a
  `Standard` block would settle it; `Standard` must be active or no player input would work.
- **CallFunction(0)** for unset ability pointers is the CD analogue of S2's garbage physics table - the startup case
  must set all three pointers for every extra.
- **Palette space**: only 5 free global entries; extras must borrow Knuckles'/Amy's 64-91 (or Sonic's 0-15). If the
  engine does *not* reload the master palette per stage, Knuckles/Amy would show an extra's colours after switching
  back - test Knuckles right after an extra.
- **ReadSaveRAM every stage** (PlayerObject:4707): NoSwap records must be written with WriteSaveRAM immediately;
  verify that time-travel state (7168+) survives it, which also tells whether in-memory SaveRAM survives.
- **No completion marker** in CD's record: define one for the extras' save screen.
- **Native UIs**: CHARACTER_SELECT (bypassed), SPECIAL_RETRY (guarded), native pause (untested with ID 7-9).
  Missions/Boss Rush after playing an extra: confirm Origins resets PLP.
- **GameConfig globals as NoSwap state** (`Leaderboard.Offset`) are unused by scripts but untested against Origins'
  native side / RESET_GAME.
- Story NPCs (Amy in PPZ/CCZ/SSZ/MMZ) are Sonic-only; extras behave like Tails/Knuckles/Amy unless treated as Sonic
  (design).
