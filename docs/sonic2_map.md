# Sonic 2 (Origins) character-dependency map for NoSwap

Source: `.../exec/Sonic2u/Scripts/` (CRLF). Only `USE_ORIGINS` / unconditional code considered; `USE_STANDALONE`-only
hits (41 of the playerListPos lines, e.g. HUD:191, Monitor:139/166, ConfigScreen:251-529, EndSetup:191/246/404/435,
PlayerObject:5776, SpecialSetup:219, Special/HUD:103/116/184, Checkpoint:163) are listed nowhere below because they are
not compiled for Origins.

Line numbers are 1-based in the original files. "ID 7" = `PLAYER_EXTRA1_A`.

Legend for treatments (Sonic 1 vocabulary):
- **add case** = add `case PLAYER_EXTRA1_A` to the Sonic case of that switch
- **frame block** = per-character `SpriteFrame` block; missing case => later frame indices shift or frames are missing
- **map ID** = ID used as a sprite-frame number; map ID>=7 to own frames (or to Sonic's as placeholder)
- **save: full / lives / gameover / complete** = `insert_save_calls` kinds
- **hide notify** = `hide_progress_from_origins`
- **alias** = public/private `PLAYER_EXTRA1_A` alias needed
- **fine** = no change needed
- **VS** = 2P VS only, out of scope

---------------------------------------------------------------------------------------------------------------

## 0. Stages that do NOT load global objects (StageConfig byte 0 == 0)

Parsed from `extracted/Sonic2/Data/Stages/*/StageConfig.bin`. Every other stage (Zone01-12, ZoneM, Continue, Ending,
all BR*/Mission_*/DLC_* stages) has global=1 and thus Players/PlayerObject.txt (GameConfig global list includes
Players/PlayerObject.txt, TailsObject, Player2Object, and all Global/*.txt).

| Stage | Scripts | Private/public character aliases present | Needs EXTRA1 alias? |
|---|---|---|---|
| **Title** | Title/Sega, STScreen, STLogo, KLogo, TinkleStars, ShootingStar, Start | Sega.txt:55 (`private alias 2 : PLAYER_KNUCKLES_A`); STLogo.txt:38-41 (0,3,5,6); Start.txt:31-33 (3,5,6) | **Start.txt yes** (picker + save screen). STLogo only if you patch its Amy->Sonic switch (not needed). Sega no. |
| **Special** | Special/SpecialSetup, Halfpipe, Background, PlayerObject, HUD, Ring, Bomb, ..., SpecialFinish, Checkpoint2PVS | **SpecialSetup.txt:77-83 `public alias 0..6 : PLAYER_*_A`** (S2 differs from S1: the aliases live in SpecialSetup, not Special/PlayerObject) | **Yes: add `public alias 7 : PLAYER_EXTRA1_A` in SpecialSetup.txt** (public, so PlayerObject/HUD/Checkpoint/SpecialFinish of the stage see it). SpecialSetup is the first script in the list so the public alias is visible to all later ones. |
| **LSelect** | LevelSelect/*, 2PVS/* | ConfigScreen.txt:64-70 (0..6) | Only if ConfigScreen gets an extras entry (design item D3). MenuControl needs a guard, not an alias (can compare `>= 7` numerically or add a private alias). |
| **Credits** | Credits/CreditsControl, CreditsEggman, CreditsLogo, DeathEggFall, DeathEggRobot | CreditsEggman.txt:17 (`private alias 2 : PLAYER_KNUCKLES_A`) | No (only a Knuckles check). |

Note: Continue and Ending DO load global objects in S2 (unlike what one might assume), so they see the public alias
from Players/PlayerObject.txt.

---------------------------------------------------------------------------------------------------------------

## A. Player objects

### Players/PlayerObject.txt
| Line | Quote | ID 7 breaks | Treatment |
|---|---|---|---|
| 96-102 | `public alias 6 : PLAYER_AMY_TAILS_A` | no alias | **alias**: same `EXTRA_ALIAS` block as S1 (public 7 + NOSWAP save aliases) |
| 157 | `private alias object.propertyValue : player.character` | - | info: character lives in propertyValue; `ResetObjectEntity(SLOT_PLAYER1, Player Object, 0, ...)` at 5801 sets it to 0 (Sonic) before the startup switch |
| 565 | `if stage.playerListPos == PLAYER_AMY` (HandleAmyHitbox) | - | fine (Amy-only) |
| 923 | `switch stage.playerListPos` (Player_UpdatePhysicsState) | falls through -> `temp0` keeps whatever was in it -> GetTableValue reads a garbage table -> broken speed/jump | **add case** (anchor identical to S1: `public function Player_UpdatePhysicsState\n\tswitch...\n\tcase PLAYER_SONIC_A\n\tcase PLAYER_SONIC_TAILS_A` - S2 has 4 comment lines between function and switch, so anchor on the switch lines only) |
| 1002 | `switch stage.playerListPos` (Player_HandleSuperForm) | no super palette cycling | **add case** (Sonic's super palette, as S1). See design D1 |
| 1039-1040 | `if stage.playerListPos == PLAYER_SONIC_A` / `LoadAnimation("Sonic.ani") // Restore the normal Sonic sprites` | nothing (extra never swapped to SuperSonic.ani) | fine as long as extras don't get a super .ani; if they do (D1), add `else if >= EXTRA1: LoadAnimation("Extra1.ani")` |
| 1081, 1160, 1232 | `if stage.playerListPos == PLAYER_AMY` (CheckHit / BadnikBreak) | - | fine (Amy-only) |
| 1872 | `if player.character == PLAYER_TAILS_A` (roll anim speed) | - | fine |
| 2487-2488 | `if stage.playerListPos == PLAYER_SONIC_A` / `LoadAnimation("SuperSonic.ani")` (Player_TryTransform) | extra transforms (TryTransform reachable via DblJumpSonic's Y-button check at 2563-2575) but keeps its normal sprites; only the palette changes | **design D1** (fine as placeholder) |
| 2827-2829 | `switch player.character` / `case PLAYER_SONIC_A` / `CheckEqual(player.character, PLAYER_SONIC_A) // A bit redundant...` (Player_HandleDropDash) | no Drop Dash charge (temp7 never set to 1) | **patch exactly like S1 "drop dash"** (same anchor text, indentation 5 tabs) |
| 2961 | `switch player.character` (Player_State_Ground idle/balance) | no idle/wait/balancing animations when standing still | **add case** (S1 "balancing"-style; S2 anchor: `\t\t\t\tswitch player.character\n\t\t\t\tcase PLAYER_SONIC_A\n\t\t\t\t\tif Player_superState == SUPERSTATE_SUPER`) |
| 3445 | `switch player.character` / `CallFunction(Player_Action_Spindash) // Good ol' Sonic Team programming` (State_Air drop-dash release) | full charge, landing does nothing (state not changed to spindash) | **add case** - same anchor as S1 "drop dash release", expected count 2 (3445 + 3558) |
| 3558 | same (Player_State_RollJump) | same | (covered by the 2-count patch above) |
| 5783-5798 | `switch stage.playerListPos` / `case PLAYER_SONIC_TAILS_A ... stage.playerListPos = PLAYER_SONIC; stage.player2Enabled = true` | nothing (7 isn't converted) | fine. **Design D2** (Extra & Tails) - player2Enabled is the only thing that makes a sidekick |
| 5823-5880 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `LoadAnimation("SuperSonic.ani")` / `LoadAnimation("Sonic.ani")` ... `player[SLOT_PLAYER1].character = PLAYER_SONIC_A` | no animation loaded (invisible), no jumpAbility (no insta-shield/double jump/transform), no super palette init, ANI_PEELOUT unset | **own startup case** (same as S1 "startup": `LoadAnimation("Extra1.ani")`, `CallFunction(Player_HandleSuperPalette_Sonic)`, `character = PLAYER_EXTRA1_A`, `jumpOffset = -5`, `jumpAbility = Player_Action_DblJumpSonic`, `ANI_PEELOUT = ANI_RUNNING`). Insert after Amy's `break` (5878). NB: Extra1.ani must follow **S2's Sonic.ani** animation list (S2 has ANI_SUPER_TRANSFORM, ANI_CONTINUE, ANI_CONTINUE_UP, ANI_FANROTATE, ANI_FLAILING1-3, ...). |
| (new) | - | - | **add `SAVE_FUNCTIONS`** before `public function Player_HandleAmyHitbox` (559), S2-adapted (see section I) |

Alternative worth considering: set `player[SLOT_PLAYER1].character = PLAYER_SONIC_A` for extras (identity via
`stage.playerListPos` only). Then 2827/2961/3445/3558, SignPost:145 and TitleCard:80 need no patch at all. S1 used
`character = PLAYER_EXTRA1_A`; keeping that for consistency means the four player.character patches above.

### Players/TailsObject.txt
| 414-417 | `if stage.playerListPos == PLAYER_TAILS_A` / `LoadAnimation("Tails.ani")` | - | fine |

### Players/Player2Object.txt (sidekick Tails / VS P2)
| 817, 887 | `if player.character == PLAYER_TAILS_A` | - | fine |
| 1091-1125 | `switch vs.player2Type` + LoadAnimation Sonic/Tails/Knuckles/Amy | - | **VS** |
| 1132-1141 | `if stage.player2Enabled == true` / `LoadAnimation("Tails.ani")` / `character = PLAYER_TAILS_A` | - | fine; sidekick is always Tails and follows P1 regardless of P1's ID (design D2) |

---------------------------------------------------------------------------------------------------------------

## B. Global objects

### Global/HUD.txt
| 213-225 | `temp0 = stage.playerListPos` ... `if temp0 == PLAYER_AMY temp0 = 40 temp1 = 41 else temp0 += 15; temp1 = temp0 + 6` (HUD_Draw_Standard, Origins) | icon = frame 22 (Tails/Miles name tag), name = frame 28 (small digit 4) | **map ID**: after `temp0 = stage.playerListPos` add `if temp0 >= PLAYER_EXTRA1_A temp0 += 20` -> icon 42+, name 48+ (icon+6 arithmetic kept). Append frames after #41: 42 extra1 icon, 43-47 reserved icons, 48 extra1 name; use `Display_NoSwap.gif` (use_sheet_copy "Global/Display.gif", 1 load in ObjectStartup) |
| 313-331 | same, HUD_Draw_Mobile (Origins block, never shown) | same | map ID (same patch). Note: exact line `temp0 = stage.playerListPos` appears **3 times** (191 is USE_STANDALONE) - patch all 3 (harmless) or expect 3 |
| 215 | `temp0 = vs.player2Type` | - | VS |

### Global/TitleCard.txt
| 80-89 | `temp0 = player[0].character` / `if temp0 == PLAYER_KNUCKLES` (green BG) | - | fine |

### Global/Monitor.txt
| 137-149 | `if stage.playerListPos != PLAYER_AMY temp0 += stage.playerListPos else temp0 = 19` (Monitor_DebugDraw) | only reachable if the debug list has a 1UP entry (it doesn't for extras); would draw frame 14 (Eggman) | map ID (`< PLAYER_EXTRA1_A` guard as S1 "monitor debug icon"; S2 anchor differs: has an `else temp0 = 19` branch) |
| 164-176 | same (Monitor_DebugSpawn) | would spawn monitor type 12 (Eggman) | same |
| 253 | `if player[currentPlayer].character == PLAYER_SONIC_A // only let Sonic have access to the elemental shields` | - | VS (inside `options.vsMode == true`) |
| 400-420 | `if stage.playerListPos != temp1 temp2 = false` (debug list: 1UP entry only for 0/1/2) | extras get no 1UP entry (same as Amy) | fine; optionally offer Sonic's 1UP like S1 "monitor debug list" |
| 429-453 | `if stage.playerListPos == PLAYER_TAILS_A` / KNUCKLES / AMY -> convert MONITOR_1UP_SONIC | extras keep MONITOR_1UP_SONIC (Sonic head) | fine as placeholder; own art: wrap frame #7 (`SpriteFrame(-8, -9, 16, 14, 18, 96)  // 7 - MONITOR_1UP_SONIC`, inside `if game.coinMode == false`) in `if >= EXTRA1` + `Items_NoSwap.gif` (S1 `monitor_1up_icon`) |

### Global/BrokenMonitor.txt
| 428 | `SpriteFrame(-8, -9, 16, 14, 18, 96)  // 5 - MONITOR_1UP_SONIC` | Sonic icon rises from broken 1UP | own art: same 1UP wrap + Items_NoSwap (S1 `build_broken_monitor`) |

### Global/SignPost.txt
| 530-560 | `switch stage.playerListPos // Has Sonic Team never heard of a default case?` / `case PLAYER_SONIC_A` ... `case PLAYER_KNUCKLES_TAILS_A` (frames #1-#8) | **no frames 1-8 at all -> signpost invisible / undefined frames** | **frame block: add case** (to the Sonic group; S1 put an own block with frame 5 = extra face) |
| 145-163 | `switch player[0].character` / `EditFrame(5, -24, -16, 48, 32, 34, 1)` (face when touched) | falls through -> frame 5 stays whatever startup defined (Sonic's face if case added above) | own art: `case PLAYER_EXTRA1_A: EditFrame(5, ..., x, y)` pointing at the extra face on `Items2_NoSwap.gif`, or define it in the startup block and skip here |
| 187 | `CallNativeFunction2(NotifyCallback, NOTIFY_TOUCH_SIGNPOST, 0)` | credits act to Origins' current character | **hide notify** (1) |
| 335 | `switch player[currentPlayer].character` | - | VS |
| 525 | `LoadSpriteSheet("Global/Items2.gif")` | - | use_sheet_copy expected=**1** (S1 had 2) |

### Global/ActFinish.txt
| 130-154 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `case PLAYER_SONIC_TAILS_A` / `case PLAYER_AMY_A` (perfect-bonus ring count) | temp0 not reset -> perfect bonus awarded/denied at random | **add case** |
| 183 | `CallNativeFunction2(NotifyCallback, NOTIFY_ACT_FINISH, 0)` | credits act to Origins save | **hide notify** (1) |
| 343-356 | `if options.gameMode == MODE_NOSAVE` / `ReadSaveRAM()` / `saveRAM[46] = true // "unlockedHPZ"` / `WriteSaveRAM()` | extras play in NOSAVE: after beating MCZ2->... this sets the HPZ flag in whatever Origins save is loaded (Sonic's, after NoSwap_BeginSave) | fine (harmless; note it) |
| 358-401 | `if options.gameMode == MODE_SAVEGAME` / `arrayPos1 = options.saveSlot` / `arrayPos1 <<= 3` ... `saveRAM[arrayPos1] = specialStage.listPos` / `WriteSaveRAM()` | extras never enter it (NOSAVE) | **save: full** (`insert_save_calls(t, ["full"])`); inner Origins switch 366-378 (`PLAYER_SONIC_TAILS` etc. when player2Enabled) is why the NoSwap record should also store player2Enabled (D2) |
| 559-591 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `case PLAYER_SONIC_TAILS_A` / `SpriteFrame(-64, 0, 72, 16, 1, 222) // 0 - "SONIC"` / `// 1 - "GOT"` | **frames 0-1 missing -> every later frame shifts by 2** (THROUGH/ACT/numbers/bonus text all wrong) | **frame block: add case** (placeholder "SONIC GOT"); own name: own case with the extra's name frame on `Display_NoSwap.gif` (S2 draws name via frame 0, not via ID - no ID mapping needed) |
| 617-644 | `switch stage.playerListPos` / `// 24 - Sonic continue frame 1` / `// 25` | frames 24-25 missing -> coin frames 26-30 shift to 24-28, continue icon wrong | **frame block: add case** (placeholder Sonic; own: mini icons on Display_NoSwap) |
| 556 | `LoadSpriteSheet("Global/Display.gif")` | - | use_sheet_copy expected=1 if own art |

### Global/DeathEvent.txt
| 167-180 | `if options.gameMode == MODE_SAVEGAME` ... `saveRAM[arrayPos1] = 50000` / `WriteSaveRAM()` | - | **save: gameover** |
| 196-202 | `saveRAM[arrayPos1] = player.lives` / `WriteSaveRAM()` | - | **save: lives** |
| 262-268 | same (Origins retry path) | - | **save: lives** |
| 275-281 | same | - | **save: lives** -> `insert_save_calls(t, ["gameover","lives","lives","lives"])` identical to S1 |

### Global/DebugMode.txt
| 292 | `if stage.playerListPos == PLAYER_TAILS_A object.type = TypeName[Tails Object]` | - | fine (extras return to Player Object) |

---------------------------------------------------------------------------------------------------------------

## C. Special stage (stage does not load PlayerObject; aliases are in SpecialSetup)

### Special/SpecialSetup.txt
| 77-83 | `public alias 6 : PLAYER_AMY_TAILS_A` | no alias | **alias** (public 7) |
| 182-197 | `switch stage.playerListPos` / S&T/K&T/A&T -> base + player2Enabled | - | fine |
| 287-295 | `if stage.playerListPos == PLAYER_KNUCKLES_A` ring table Knux else Sonic | - | fine (Sonic's ring requirements) |

### Special/PlayerObject.txt (sprite frames, no LoadAnimation in S2)
| 1070-1092 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `player[2].xBoundsR = 88` / `player[2].frameOffset = 0` | **xBoundsR = 0 -> halfpipe bounds/groundPos broken (player pinned at centre / wrong physics), frameOffset 0** | **add case** (placeholder: Sonic 88/0). Own art: append 16 frames (8 run + 8 jump) after Amy's (current last frame = 79) -> `frameOffset = 80` on `Special/Objects_NoSwap.gif` (use_sheet_copy "Special/Objects.gif", 1 load) |
| 1127-1149 | `switch vs.player2Type` | - | VS |
| 1165-1182 | sidekick Tails (frameOffset 16) | - | fine |

### Special/HUD.txt
| 33-41 | `if object.character != PLAYER_AMY object.frame = object.character; object.frame += 12 else object.frame = 15` | frame 19 doesn't exist (last is 15) -> ring label not drawn / undefined | **map ID**: `>= EXTRA1 -> 12` (Sonic Rings) placeholder, or new frame 16 "EXTRA RINGS" on Objects_NoSwap |
| 94, 188 | `object.character = stage.playerListPos` | (feeds the above) | covered by the HUD_GetCharacterFrame patch |
| 215 | `object.character = vs.player2Type` | - | VS |

### Special/Checkpoint.txt
| 166-171 | `if stage.playerListPos >= PLAYER_AMY object.emblemFrame = 7 else object.emblemFrame = 4 + playerListPos` | **extras show Amy's emblem** | **map ID**: `>= EXTRA1 -> 4` (Sonic emblem) placeholder, or new frame 8 own emblem (96x48) on Objects_NoSwap |

### Special/Checkpoint2PVS.txt
| 177 | `object.emblemFrame += stage.playerListPos` | - | VS |

### Special/SpecialFinish.txt
| 268-287 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `case PLAYER_KNUCKLES_A` / `object.state = SPECIALFINISH_WINSHOWREWARD` (only when emeralds == 0x7F) | **SOFTLOCK: state never advances after the 7th emerald** | **add case** (to Sonic: show "can be Super" reward) |
| 549-568 | `switch stage.playerListPos` / `DrawSpriteScreenXY(20, temp7, 161)` ("SONIC RINGS") | label not drawn | **add case** (placeholder Sonic, or own label frame #44 appended) |
| 653-680 | `switch stage.playerListPos` "[Player] GOT A" #24-25 | **frame block**: missing -> #26+ shift by 2 | **frame block: add case** |
| 685-712 | "[Player] HAS ALL THE" #27-28 | shift | **frame block: add case** |
| 717-749 | "NOW [Player] CAN" #30-32 | shift | **frame block: add case** |
| 759-787 | "SUPER/HYPER [Player]" #34-35 | shift | **frame block: add case** |
| 790-817 | "NOW [Player]" #36-37 | shift | **frame block: add case** (5 blocks; S1 helper `patch_n(SONIC_SWITCH...)` won't match because these switches have only `case PLAYER_SONIC_A` (no S&T line) - anchor on `switch stage.playerListPos\n\tcase PLAYER_SONIC_A\n\t\tSpriteFrame(` and expect 5) |
| 617 | `LoadSpriteSheet("Special/Objects.gif")` | - | sheet copy if own name text |
| (none) | no save blocks in S2 SpecialFinish (S1 had 3) | - | - |
| ChaosEmerald.txt:230 | `CallNativeFunction2(NotifyCallback, NOTIFY_TOUCH_EMERALD, 0)` | unknown: Origins may record the emerald in the current Origins character's save/stats | **open question** - consider hiding like ACT_FINISH (S1 didn't) |

---------------------------------------------------------------------------------------------------------------

## D. Title / menus / level select / 2P VS

### Title/Start.txt (Title stage, global=0)
| 31-33 | `private alias 3 : PLAYER_SONIC_TAILS_A` / 5 / 6 | no alias | **alias** (private 7 + NOSWAP picker/save aliases, as S1) |
| 199-234 | START_ATTRACTMODE: `switch stage.playerListPos case PLAYER_AMY_A stage.playerListPos = PLAYER_SONIC ...` | a remembered extra (7) goes into the EHZ/CPZ/ARZ/CNZ demo -> attract table unset (see G) | either add `case PLAYER_EXTRA1_A: stage.playerListPos = PLAYER_SONIC` here, or add case to the 4 zone-setup attract switches (S1 did the latter). Doing it here loses the "remember extra" value (S1 re-derived noswapChoice from playerListPos at title startup) - prefer zone setups |
| 240-291 | START_ORIGINSMENU / START_FLASHOPTION (1 PLAYER / 2 PLAYER VS menu in-script) | - | **picker goes here** (left/right while `menuSelection == MENU_1PLAYER`); S2 flow differs from S1: AWAITACTION -> FLASHPRESSBUTTON -> ORIGINSMENU -> FLASHOPTION -> 1PSENDCALLBACK |
| 293-298 | `CallNativeFunction2(NotifyCallback, NOTIFY_CHARACTER_SELECT, 0)` | - | **picker branch**: extras skip it -> `NOTIFY_PLAYER_SET, PLAYER_SONIC` + `ReadSaveRAM()` -> own save-select state (S1 `START_NOSWAP_SAVESELECT`/`CONTINUE`; new state IDs 11/12 since 0-10 are used) |
| 303 | `if stage.playerListPos > PLAYER_SONIC_TAILS_A // Not really sure...` -> `NOTIFY_1P_VS_SELECT` | only after Origins' select (which overwrote playerListPos) | fine |
| 314-347 | START_ORIGINSSTARTGAME: `stage.activeList = REGULAR_STAGE` / `stage.listPos = 0` (1P) | - | **picker apply** (same as S1 "title picker apply", guard `menuSelection == MENU_1PLAYER`); game.continueFlag path -> RESET_GAME is Origins' continue, extras use own continue state |
| 424-446 | `LoadSpriteSheet("Title/Title.gif")`; frames #0-#5 (#5 = Sonic icon cursor at 104,370) | - | Title_NoSwap.gif + appended picker frames (#6+) |

### Title/STLogo.txt (private aliases 38-41)
| 266-274 | `switch stage.playerListPos case PLAYER_AMY_A stage.playerListPos = PLAYER_SONIC_A` | 7 untouched; nothing else in STLogo reads the ID | fine (no emblem switch like S1 Logo.txt) |

### Title/Sega.txt (private alias 55)
| 250 | `if stage.playerListPos == PLAYER_KNUCKLES_A` -> K Logo | - | fine |

### LevelSelect/MenuControl.txt (LSelect, global=0)
| 610 | `CallNativeFunction4(NotifyCallback, NOTIFY_PLAYER_SET, stage.playerListPos, stage.player2Enabled, 0)` | **if playerListPos is still 7 (returning to title as an extra, then level select via stageSelectFlag) Origins is told ID 7 -> crash (per S1 test 2026-09-25)** | **guard**: pass PLAYER_SONIC when `>= 7` (or keep the extra and pass Sonic). Design D3 |
| 244, 586 | `saveRAM[46] = true` / `if saveRAM[46] == true` (HPZ unlock) | - | fine |

### LevelSelect/ConfigScreen.txt (private aliases 64-70)
| 84-125 | `ConfigScreen_SetPlayer`: `switch object.playerID` -> `stage.playerListPos = PLAYER_SONIC` ... (7 entries) | extras can't be chosen; playerID isn't initialised from playerListPos, so an extra stays active until left/right is pressed | **design D3** (add CONFIGSCREEN_PLAYER_X1 entry + private alias + icon frame after #31 and before the shield frames -> shield frames #32-35 shift; they are drawn by fixed index in the Origins block 831-850, so append instead) |
| 768-808 | `switch object.playerID` draw icons | - | D3 |

### 2P VS (all out of scope)
2PVSMenu2.txt:377-378, 2PVSMenu3.txt:162-165/285/303, 2PVSMenu4.txt:180-183 (set playerListPos from the VS menu, overwriting any extra), VSGame.txt:290 (`switch player[currentPlayer].character`), ActResults/SSResultSingle saveRAM writes (VS results), ZoneButton.txt:65, Checkpoint2PVS:177, Special/HUD:215, Special/PlayerObject:1127, Player2Object:1091, Monitor:253, SignPost:335, Mission/SignPost2:319 -> **VS**. Note Player_UpdatePhysicsState uses P1's ID for P2 too (existing bug).

---------------------------------------------------------------------------------------------------------------

## E. Continue (stage loads globals)

### Continue/Continue.txt
| 126-157 | `switch stage.playerListPos` / `// #12 -> #13 - Sonic foot tapping` | frames 12-13 missing (they're the last frames) -> icons invisible | **frame block: add case** (placeholder Sonic; own: mini icons on `Continue/Objects_NoSwap.gif`, 1 load at 105) |

### Continue/ContinueSetup.txt
| 206-230 | `switch stage.playerListPos` / `player[0].ypos = 0xAC0000` | ypos not set -> player at y=0 (top of screen) | **add case** |
| 257-277 | `switch stage.playerListPos` (P2 Tails offset/animation) | P2 animation stays ANI_FANROTATE, no offset | **add case** (only matters with a sidekick) |
| 233 etc. | `player[0].animation = ANI_CONTINUE` / ANI_CONTINUE_UP | Extra1.ani needs these S2 animation slots | note |

---------------------------------------------------------------------------------------------------------------

## F. Ending / credits (Ending loads globals; Credits doesn't)

### Ending/EndSetup.txt
| 169-184 | `CheckEqual(stage.playerListPos, PLAYER_TAILS_A)` ... `PLAYER_AMY` / `PLAYER_AMY_TAILS` -> good ending unless Tails/Amy | extras with 7 emeralds go Super in the ending | **design D1/D4** (fine as is if extras can be super) |
| 209-238 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `player[0].animation = ANI_RUNNING` / `LoadAnimation("SuperSonic.ani")` | extra descends Super with whatever animation it had (no ANI_RUNNING) | **design D4**: own case `ANI_RUNNING` (+ optional Extra1Super.ani); adding to Sonic's case would turn the extra into Super Sonic sprites |
| 266-279 | `switch stage.playerListPos` (non-Sonic chars skip the pictures, fall from sky) | falls through = **Sonic's path** (4 story pictures) | fine - the pictures (523-526) show animals/Tails/Tornado, no Sonic |
| 414-421 | same, Tornado timer 488 vs 2608 | falls through = Sonic timing | fine |
| 442-454 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `case PLAYER_KNUCKLES_A` ... `object[33].ypos += 4` | Tornado 4px too high (Tails offset) | **add case** |

### Ending/Tornado.txt (frames defined unconditionally 926-1050 -> no shifting; switches choose frames)
| 272, 521 | `if stage.playerListPos == PLAYER_TAILS_A` (Sonic pilots / big frame 49) | - | fine (Tails pilots for extra) |
| 309 | Tails super palette | - | fine |
| 322, 326 | Knuckles glide drop | - | fine |
| 335 | Amy y offset | - | fine |
| 359-367 | non-Sonic chars `ANI_STOPPED` when super | falls through = Sonic (keeps running pose on wing) | fine |
| 396-411 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `if specialStage.emeralds >= 0x7F object.superSonic.state = SUPERSONIC_MEETTORNADO` | super extra never does the fly-by | **design D4** |
| 431-448 | `switch` -> `player[0].visible = false` (Sonic only if not super; others always) | **player never hidden -> extra hangs in the sky while the Tornado flies into the background** | **add case** (to Sonic's if Super fly-by is used, else to the "others" group when super) |
| 456-470, 534-548 | Sonic-only super fly-by timers | - | design D4 (together with 396) |
| 475-501 | `switch stage.playerListPos` / `GetTableValue(object.tornadoFrame, ..., Tornado_ZoomoutSprites_Sonic)` | **tornadoFrame never updated -> Tornado sprite frozen at frame 4 region/stale while it moves** | **add case** (placeholder: Sonic tables -> Sonic as passenger frames 19-23 / SS frames 12-16) |
| 764-797 | `switch stage.playerListPos` / `DrawSpriteXY(24, temp0, temp1)` (pose 1) | no pose drawn | **add case** (placeholder Sonic 24) |
| 807-840 | pose 2 (#25) | no pose | **add case** |
| 866-901 | final pose (#26) | no pose | **add case** |
| 923 | `LoadSpriteSheet("Ending/Objects.gif")` | - | own art: Ending/Objects_NoSwap, swap frames 19-23 (passenger), 24-26 (poses) [and 43-48 super fly-by, 50 big Tornado w/ passenger?] under `if >= EXTRA1` like S1 `build_ending_pose` |

### Ending/Bird.txt
| 43 | `if stage.playerListPos == PLAYER_TAILS_A object.frame = 4` | - | fine |

### Credits/CreditsEggman.txt (Credits, global=0, private alias 17)
| 140 | `if stage.playerListPos != PLAYER_KNUCKLES_A` (Knux stinger) | - | fine |

---------------------------------------------------------------------------------------------------------------

## G. Zone-specific

| File:line | Quote | ID 7 | Treatment |
|---|---|---|---|
| EHZ/EHZSetup.txt:759 | `switch stage.playerListPos` / `case PLAYER_SONIC_A` / `#platform: USE_ORIGINS` / `case PLAYER_AMY_A // Amy isn't even able...` (attract) | Player_attractTable unset -> garbage demo | **add case** (S1 `ATTRACT_SWITCH`-style; S2 anchor has a trailing comment on the Amy line) |
| CPZ/CPZSetup.txt:1084 | same | same | **add case** |
| ARZ/ARZSetup.txt:1035 | same | same | **add case** |
| CNZ/CNZSetup.txt:908 | same | same | **add case** |
| EHZ/EHZSetup.txt:693-701 | `if options.gameMode == MODE_SAVEGAME` / `arrayPos1 += 4` / `if saveRAM[arrayPos1] < 20` (achievement read) | extras take the NOSAVE branch (achievement granted) | fine; **do not run insert_save_calls on EHZSetup** (it has no write -> "unrecognised save block") |
| ARZ/Water.txt:656, CPZ/Water.txt:644, HPZ/Water.txt:578 | `if stage.playerListPos == PLAYER_KNUCKLES_A` jumpStrength underwater | - | fine |
| OOZ/OOZSetup.txt:186, 392; MBZ/MBZSetup.txt:179 | Knuckles oil idle | - | fine |
| HPZ/BreakWall.txt:85, 99 | `player[currentPlayer].character == PLAYER_KNUCKLES` / `playerListPos == PLAYER_AMY` | - | fine |
| MPZ/EggmanBalloon.txt:192 | `if stage.playerListPos == PLAYER_AMY` | - | fine |
| CNZ/SlotDisplay.txt:258 | `switch stage.playerListPos` / `case PLAYER_KNUCKLES_A` (Sonic slot faces -> Knux/Amy) | extras see Sonic faces | fine (optional own face via sheetX table like Amy's) |
| OOZ/CheckeredBall.txt:1333 | `LoadAnimation("WreckingBallJr.ani")` | - | unrelated |
| MCZ/HPZTrigger.txt:99 | `CallNativeFunction2(NotifyCallback, NOTIFY_ACT_FINISH, 1)` (skip to HPZ, `game.stageskipped = true`) | credits to Origins save | **hide notify** |
| SCZ/SCZSetup.txt:195 | `CallNativeFunction2(NotifyCallback, NOTIFY_ACT_FINISH, 0)` (TOWINGFORTRESS) | same | **hide notify** |
| SCZ/SCZSetup.txt:221-265 | `if options.gameMode == MODE_SAVEGAME` / `arrayPos1 = options.saveSlot` ... `saveRAM[arrayPos1] = specialStage.listPos` / `WriteSaveRAM()` | - | **save: full** |
| SCZ/SCZSetup.txt:296 | `NOTIFY_ACT_FINISH, 0` | same | **hide notify** (SCZSetup total 2) |
| SCZ/Tornado.txt:260, 306 | `if stage.playerListPos == PLAYER_TAILS_A` (Sonic pilots / y shift) | - | fine (Tails pilots, extra rides like Sonic) |
| WFZ/Tornado.txt:185, 591 | Tails checks | - | fine |
| WFZ/Tornado.txt:463-511 | `if options.gameMode == MODE_SAVEGAME` ... full record / `WriteSaveRAM()` | - | **save: full** |
| WFZ/Tornado.txt:540 | `NOTIFY_ACT_FINISH, 0` | - | **hide notify** |
| WFZ/EggmanLaser.txt:358 | `NOTIFY_ACT_FINISH, 0` (boss killed) | - | **hide notify** |
| DEZ/DeathEggRobot.txt:1267 | `NOTIFY_ACT_FINISH, 0` | - | **hide notify** |
| DEZ/DeathEggRobot.txt:1286-1293 | `arrayPos1 += 4` / `saveRAM[arrayPos1] = 22` / `WriteSaveRAM()` | - | **save: complete** - S1's detector looks for `"= 20"`; S2 writes **22** -> change detector (and NoSwap_SaveComplete value) to 22 |

---------------------------------------------------------------------------------------------------------------

## H. Missions (S1 picker is disabled in Missions; all fine if S2 does the same)

| Mission/SignPost2.txt:458 | `switch stage.playerListPos` (no Amy case even) frames #1-8 | invisible sign | frame block: add case (only if extras can play missions) |
| Mission/SignPost2.txt:148 | `switch player[0].character` EditFrame | - | same |
| Mission/SignPost2.txt:185 | `NOTIFY_TOUCH_SIGNPOST` | - | hide notify (optional) |
| Mission/SCZMSetup.txt:241 | `NOTIFY_TOUCH_SIGNPOST` (mission results popup) | - | leave (mission HUD relies on it) |
| Mission/SuperSonic.txt:116-119 | `if stage.playerListPos == PLAYER_SONIC_A LoadAnimation("SuperSonic.ani")` | - | fine / D1 |
| Mission/Water.txt:585 | Knuckles | - | fine |
| Mission/SignPost2.txt:319 | VS | - | VS |

---------------------------------------------------------------------------------------------------------------

## I. Save-format notes for the S2 NoSwap_* routines

- Record = 8 values at `saveSlot << 3`: [0] character (Origins writes PLAYER_SONIC_TAILS/KNUCKLES_TAILS/AMY_TAILS when
  player2Enabled), [1] lives, [2] score, [3] scoreBonus, [4] next stage listPos+1 (ActFinish keeps the max; SCZ/WFZ
  overwrite), [5] emeralds, [6] specialStage.listPos. Completed = [4] = **22** (DEZ). EHZ achievement reads [4] < 20.
- Game uses saveRAM[0..31] (4 slots), 39/40 (virtual D-pad), 46 (HPZ unlock) -> SAVE_BASE 1024 is free, as in S1.
- NoSwap record should also store player2Enabled (D2), e.g. in [7] or as a flag bit in [0].
- Save sites in S2: ActFinish full, SCZSetup full, WFZ/Tornado full, DEZ/DeathEggRobot complete, DeathEvent
  gameover+lives x3. No save in Special/SpecialFinish (unlike S1).
- Continue flow: Origins' continue returns via `game.continueFlag` -> `engine.state = RESET_GAME` (Start.txt:317); the
  extras' continue must use its own state as in S1.

---------------------------------------------------------------------------------------------------------------

## J. Design-decision items (no direct S1 equivalent)

**D1 - Super Sonic.** S2 Origins lets any character with `jumpAbility = Player_Action_DblJumpSonic` transform with the
Y button (PlayerObject:2563-2577, emeralds 0x7F + 50 rings). For extras: palette via HandleSuperForm (1002) - add case
(uses Sonic's palette rotation on the extra's palette slots, which may look wrong if the extra's colours don't sit in
Sonic's indices). Sprites: TryTransform (2487) and Mission/SuperSonic (116) load SuperSonic.ani only for ID 0;
HandleSuperForm fade-out (1039) restores Sonic.ani only for ID 0. Options: (a) no sprite change (placeholder, zero
patches), (b) `Extra1Super.ani` loaded at 2487 and Extra1.ani restored at 1039 (two small patches + art),
(c) disable transform for extras (give them a copy of DblJumpSonic without the Y check). Also ObjectStartup preloads
SuperSonic.ani before Sonic.ani (5825) to register its sheets - an Extra1Super.ani would need the same preload.

**D2 - Sidekick Tails ("Extra & Tails").** Origins' character select has S&T / K&T / A&T (IDs 3/4/6) which
PlayerObject:5783 converts to base ID + `player2Enabled = true`; Player2Object then spawns Tails, who follows P1
regardless of P1's ID. S1 forced `player2Enabled = false` for extras. In S2 a sidekick is the default experience;
decide whether the picker offers "Extra alone / Extra & Tails" (set player2Enabled accordingly; no new IDs needed), and
store the flag in the NoSwap save record. ContinueSetup:257 and EndSetup/Tornado handle P2 via the base-ID switches
(add case covers them). Special stage sidekick (Special/PlayerObject:1165) is ID-independent.

**D3 - Level select / ConfigScreen.** LSelect doesn't load globals. MenuControl:610 sends NOTIFY_PLAYER_SET with the
raw ID -> must be guarded (crash risk). ConfigScreen has its own 7-entry player cycle with private aliases; decide
whether to add extras there (needs private alias, a CONFIGSCREEN_PLAYER_X1 id, icon frame appended after the shield
frames, and draw case) or just map an extra to Sonic when entering level select.

**D4 - Ending Tornado / Super ending.** Ending/Tornado.txt bakes the passenger into the zoom-out Tornado frames
(19-23 Sonic passenger, 27-31 Sonic pilot for Tails' ending, 35-39 Knux) and pose frames (24-26 Sonic, 32-34 Tails,
40-42 Knux, 65-67 Amy), plus a separate Super Sonic fly-by (43-48, SUPERSONIC_* states only for ID 0/3). Minimum: add
the extra to the Sonic cases at 442 (EndSetup), 431, 475, 764, 807, 866 (Tornado) -> Sonic art as placeholder. Own
art: a sheet copy swapping 19-26 (and 43-48 if super fly-by is kept) like S1 EndingPose. With 7 emeralds the extra
goes Super in EndSetup (209): decide between Super fly-by (add to 396/456/534 + Sonic's super art or own), or treating
the extra like Knuckles/Amy when super (hidden at 431, poses drawn). EndSetup:209's Sonic case loads SuperSonic.ani -
don't add the extra there blindly.

**D5 - SCZ / WFZ Tornado cutscenes.** Tails pilots for every non-Tails character (SCZ/Tornado:260, WFZ/Tornado:591),
so extras work unchanged (they stand on the wing with their own sprites). No patch needed; only the save/notify sites
in SCZSetup/WFZ Tornado/EggmanLaser.

**D6 - Title flow.** S2's Origins title has its own in-script 1P / 2P VS menu (Start.txt states 5-10) before
NOTIFY_CHARACTER_SELECT, unlike S1's single PRESS START -> callback. Picker placement: on the "1 PLAYER" line in
START_ORIGINSMENU (Sonic icon frame #5 is already drawn there). STLogo has no character-dependent emblem (unlike S1
Logo.txt), so no title-emblem patch is needed.

**D7 - NOTIFY_TOUCH_EMERALD** (Special/ChaosEmerald:230) and NOTIFY_SPECIAL_RETRY (SpecialFinish:157): possibly
credit Origins' per-character progress; S1 left them alone. Worth testing.

---------------------------------------------------------------------------------------------------------------

## K. Counts per treatment (Origins-relevant, main game, excluding VS/Missions)

| Treatment | Count | Sites |
|---|---|---|
| add case to a behaviour/draw switch | 22 | PlayerObject 923, 1002, 2961, 3445, 3558 (+2827 drop-dash rewrite); ActFinish 130; SpecialFinish 268, 549; Special/PlayerObject 1070; ContinueSetup 206, 257; EndSetup 442; Tornado 431, 475, 764, 807, 866; EHZ/CPZ/ARZ/CNZ attract x4 |
| own startup case (LoadAnimation Extra1.ani) | 1 | PlayerObject 5823 |
| per-character SpriteFrame block (frames shift/missing) | 9 | ActFinish 559, 617; SignPost 530; SpecialFinish 653, 685, 717, 759, 790; Continue 126 |
| map ID used as frame | 5 | HUD 213, 313; Monitor 145, 172 (debug); Special/HUD 36 (+feeds 94/188); Special/Checkpoint 166 |
| own-art hooks (sheet copies, optional) | 7 | Monitor 1UP #7, BrokenMonitor 1UP #5, SignPost face 145, Special player frames, SpecialFinish names, Continue icons, Ending/Tornado frames |
| save sites | 8 blocks / 5 files | ActFinish full; SCZSetup full; WFZ/Tornado full; DEZ/DeathEggRobot complete(22); DeathEvent gameover, lives x3 |
| hide notify (ACT_FINISH / TOUCH_SIGNPOST) | 8 | ActFinish 183; SignPost 187; SCZSetup 195, 296; WFZ/Tornado 540; WFZ/EggmanLaser 358; DEZ/DeathEggRobot 1267; MCZ/HPZTrigger 99 |
| NOTIFY_PLAYER_SET guard | 1 | LevelSelect/MenuControl 610 |
| NOTIFY_CHARACTER_SELECT (picker branch) | 1 | Title/Start 296 |
| alias additions | 3 | PlayerObject (public), Special/SpecialSetup (public), Title/Start (private) [+ConfigScreen if D3] |
| fine as is | ~45 | Amy/Tails/Knuckles-only checks, S&T converters, water/oil, BreakWall, Balloon, Slot, SCZ/WFZ Tornado pilot, EndSetup 266/414, Bird, CreditsEggman, STLogo, Sega, TitleCard, DebugMode, TailsObject, EHZ save read, HPZ unlock |
| design decisions | 7 | D1-D7 above |
| 2P VS (out of scope) | ~20 | listed in section D |
| Missions (optional) | 6 | section H |

Critical (crash/softlock/invisible) if left unpatched: PlayerObject startup 5823 (invisible), physics 923,
SignPost 530 (invisible sign), ActFinish 559 (all results frames shifted), SpecialFinish 268 (softlock at 7th
emerald) + its 5 frame blocks, Special/PlayerObject 1070 (xBounds 0), ContinueSetup 206, MenuControl 610 (Origins
crash), Tornado 475/431.
