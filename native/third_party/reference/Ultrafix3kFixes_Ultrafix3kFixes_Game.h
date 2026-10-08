#pragma once

// RSDK Macros
#define RETRO_REV02 1
#define RETRO_REV0U 1
#define TO_FIXED(x)   ((x) << 16)
#define RETRO_HASH_MD5(name) uint32 name[4]

// RSDK Primitive Types
typedef int int32;
typedef int uint32;
typedef short int16;
typedef unsigned short uint16;
typedef unsigned char uint8;
typedef int bool32;


typedef char int8;
typedef uint32 color;

// Others
typedef enum
{
    SUPERSTATE_NONE,
    SUPERSTATE_FADEIN,
    SUPERSTATE_SUPER,
    SUPERSTATE_FADEOUT,
    SUPERSTATE_DONE,
} SuperStates;

enum CharacterIDs
{
    ID_NONE = 0x0,
    ID_SONIC = 0x1,
    ID_TAILS = 0x2,
    ID_KNUCKLES = 0x4,
    ID_AMY = 0x8,
};

enum GameModes
{
    MODE_NOSAVE = 0x0,
    MODE_SAVEGAME = 0x1,
    MODE_TIMEATTACK = 0x2
};

enum VariableTypes : uint8
{
    VAR_UINT8 = 0x0,
    VAR_UINT16 = 0x1,
    VAR_UINT32 = 0x2,
    VAR_INT8 = 0x3,
    VAR_INT16 = 0x4,
    VAR_INT32 = 0x5,
    VAR_ENUM = 0x6,
    VAR_BOOL = 0x7,
    VAR_STRING = 0x8,
    VAR_VECTOR2 = 0x9,
    VAR_FLOAT = 0xA,
    VAR_COLOR = 0xB,
};


// RSDKv5 Structures
struct Animator
{
    void* frames;
    int32 frameID;
    int16 animationID;
    int16 prevAnimationID;
    int16 speed;
    int16 timer;
    int16 frameDuration;
    int16 frameCount;
    uint8 loopIndex;
    uint8 rotationStyle;
};

struct Vector2
{
    int32 x;
    int32 y;
};

struct __declspec(align(8)) StateMachine
{
    void(__fastcall* state)();
    int timer;
    char field_C;
    char field_D;
    char field_E;
    char priority;
};

struct Entity
{
    void* vfTable;
    Vector2 position;
    Vector2 scale;
    Vector2 velocity;
    Vector2 updateRange;
    int32 angle;
    int32 alpha;
    int32 rotation;
    int32 groundVel;
    int32 zdepth;
    uint16 group;
    uint16 classID;
    bool32 inRange;
    bool32 isPermanent;
    bool32 tileCollisions;
    bool32 interaction;
    bool32 onGround;
    uint8 active;
    uint8 filter;
    uint8 direction;
    uint8 drawGroup;
    uint8 collisionLayers;
    uint8 collisionPlane;
    uint8 collisionMode;
    uint8 drawFX;
    uint8 inkEffect;
    uint8 visible;
    uint8 onScreen;
};

struct EntityCamera : Entity
{
    StateMachine state;
    Entity* target;
    int32 screenID;
    Vector2 center;
    Vector2 targetMoveVel;
    Vector2 lastPos;
    Vector2 shakePos;
    Vector2 lookPos;
    Vector2 offset;
    bool32 disableYOffset;
    int32 centerY;
    int32 adjustY;
    int32 lerpPercent;
    int32 lerpSpeed;
    int32 lerpType;
    Vector2 endLerpPos;
    Vector2 startLerpPos;
    Vector2 boundsOffset;
    int32 boundsL;
    int32 boundsR;
    int32 boundsT;
    int32 boundsB;
};

struct EntityPlayer : Entity
{
    char padding0[144];
    StateMachine state;
    StateMachine nextAirState;
    StateMachine nextGroundState;
    char padding1[16];
    EntityCamera* camera;
    Animator animator;
    Animator tailAnimator;
    char padding2[30];
    uint16 playerID;
    char padding3[16];
    int32 characterID;
    int32 rings;
    int32 ringExtraLife;
    int32 shield;
    char padding4[60];
    int32 superState;
    char padding5[168];
    int32 controllerID;
    int32 controlLock;
    bool32 up;
    bool32 down;
    bool32 left;
    bool32 right;
    bool32 jumpPress;
    bool32 jumpHold;
    char padding6[4];
    int32 jumpAbilityState;
    char padding7[234];
    int32 chargeTimer;
};

struct ObjectZone
{
    char padding0[336];
    int32 cameraBoundsL[4];
    int32 cameraBoundsR[4];
    int32 cameraBoundsT[4];
    int32 cameraBoundsB[4];
    int32 playerBoundsL[4];
    int32 playerBoundsR[4];
    int32 playerBoundsT[4];
};

struct InputState
{
    bool32 down;
    bool32 press;
    int32 keyMap;
};

struct ControllerState
{
    InputState keyUp;
    InputState keyDown;
    InputState keyLeft;
    InputState keyRight;
    InputState keyA;
    InputState keyB;
    InputState keyC;
    InputState keyX;
    InputState keyY;
    InputState keyZ;
    InputState keyStart;
    InputState keySelect;
};

struct SceneListInfo
{
    RETRO_HASH_MD5(hash);
    char name[0x20];
    uint16 sceneOffsetStart;
    uint16 sceneOffsetEnd;
    uint8 sceneCount;
};

struct SceneListEntry
{
    RETRO_HASH_MD5(hash);
    char name[0x20];
    char folder[0x10];
    char id[0x08];
};


struct SceneInfo
{
    Entity* entity;
    SceneListEntry* listData;
    SceneListInfo* listCategory;
    int32 timeCounter;
    int32 currentDrawGroup;
    int32 currentScreenID;
    uint16 listPos;
    uint16 entitySlot;
    uint16 createSlot;
    uint16 classCount;
    bool32 inEditor;
    bool32 effectGizmo;
    bool32 debugMode;
    bool32 useGlobalObjects;
    bool32 timeEnabled;
    uint8 activeCategory;
    uint8 categoryCount;
    uint8 state;
#if RETRO_REV02
    uint8 filter;
#endif
    uint8 milliseconds;
    uint8 seconds;
    uint8 minutes;
};

struct EntityActClear
{
    Entity entity;
    StateMachine(state);
    int32 timer;
    int32 stageFinishTimer;
    int32 timeBonus;
    int32 ringBonus;
    int32 coolBonus;
    int32 totalScore;
    int32 time;
    int32 newRecordTimer;
    bool32 achievedRank;
    bool32 isNewRecord;
    bool32 showCoolBonus;
    Vector2 playerNamePos;
    Vector2 gotThroughPos;
    Vector2 timeBonusPos;
    Vector2 ringBonusPos;
    Vector2 coolBonusPos;
    Vector2 totalScorePos;
    EntityPlayer* targetPlayer;
    // ...
};

struct EntityShield : Entity
{
    Entity entity;
    EntityPlayer* player;
    StateMachine state;
    int32 type;
    int32 timer;
    int32 frameFlags;
    bool32 forceVisible;
    Animator shieldAnimator;
    Animator fxAnimator;
};

typedef enum {
    ACTIVE_NEVER,
    ACTIVE_ALWAYS,
    ACTIVE_NORMAL,
    ACTIVE_PAUSED,
    ACTIVE_BOUNDS,
    ACTIVE_XBOUNDS,
    ACTIVE_YBOUNDS,
    ACTIVE_RBOUNDS,

    // Not really even a real active value, but some objects set their active states to this so here it is I suppose
    ACTIVE_DISABLED = 0xFF,
} ActiveFlags;

typedef enum {
    BOOT_PLAYMODE_CLASSIC = 0,
    BOOT_PLAYMODE_ANNIVERSARY = 1,
    BOOT_PLAYMODE_BOSSRUSH = 2,
    BOOT_PLAYMODE_MIRRORING = 3,
    BOOT_PLAYMODE_MISSION = 4,
    BOOT_PLAYMODE_STORY = 5,
} PlayModes;

typedef enum {
    MEDAL_DEBUGMODE   = 1 << 0,
    MEDAL_ANDKNUCKLES = 1 << 1,
    MEDAL_PEELOUT     = 1 << 2,
    MEDAL_INSTASHIELD = 1 << 3,
    MEDAL_NODROPDASH  = 1 << 4,
    MEDAL_NOTIMEOVER  = 1 << 5,
    MEDAL_NOLIVES     = 1 << 6,
} MedalMods;

typedef enum {
    SECRET_RICKYMODE        = 1 << 0,
    SECRET_SUPERDASH        = 1 << 1,
    SECRET_BARRELHOTLINE    = 1 << 2, // unused in normal gameplay
    SECRET_NORMALPHYSICS_2P = 1 << 3,
    SECRET_REGIONSWAP       = 1 << 4,
    SECRET_CAMERATRACKING   = 1 << 5,
    SECRET_PENPENMODE       = 1 << 6,
    SECRET_RANDOMITEMS      = 1 << 7,
    SECRET_BLUESHIELDMODE   = 1 << 8,
    SECRET_UNKNOWN          = 1 << 9, // unused in normal gameplay
    SECRET_BANANAMODE       = 1 << 10,
    SECRET_NOITEMS          = 1 << 11,
    SECRET_HIDDENCREDITS    = 1 << 12,
} GameCheats;

typedef enum {
    SHIELD_NONE,
    SHIELD_BLUE,
    SHIELD_BUBBLE,
    SHIELD_FIRE,
    SHIELD_LIGHTNING,
} ShieldTypes;

typedef enum {
    ENGINESTATE_LOAD,
    ENGINESTATE_REGULAR,
    ENGINESTATE_PAUSED,
    ENGINESTATE_FROZEN,
    ENGINESTATE_STEPOVER = 4,
    ENGINESTATE_DEVMENU  = 8,
    ENGINESTATE_VIDEOPLAYBACK,
    ENGINESTATE_SHOWIMAGE,
    ENGINESTATE_ERRORMSG,
    ENGINESTATE_ERRORMSG_FATAL,
    ENGINESTATE_NONE,
} EngineStates;

enum RetroEngineCallbacks : int32 {
    CALLBACK_DISPLAYLOGOS = 0,
    CALLBACK_PRESS_START = 1,
    CALLBACK_TIMEATTACK_NOTIFY_ENTER = 2,
    CALLBACK_TIMEATTACK_NOTIFY_EXIT = 3,
    CALLBACK_FINISHGAME_NOTIFY = 4,
    CALLBACK_RETURNSTORE_SELECTED = 5,
    CALLBACK_RESTART_SELECTED = 6,
    CALLBACK_EXIT_SELECTED = 7,
    CALLBACK_BUY_FULL_GAME_SELECTED = 8,
    CALLBACK_TERMS_SELECTED = 9,
    CALLBACK_PRIVACY_SELECTED = 10,
    CALLBACK_TRIAL_ENDED = 11,
    CALLBACK_SETTINGS_SELECTED = 12,
    CALLBACK_PAUSE_REQUESTED = 13,
    CALLBACK_FULL_VERSION_ONLY = 14,
    CALLBACK_STAFF_CREDITS = 15,
    CALLBACK_MOREGAMES = 16,
    CALLBACK_SHOWREMOVEADS = 20,
    CALLBACK_AGEGATE = 100,

    // Sonic Origins Notify Callbacks
    NOTIFY_DEATH_EVENT = 128,
    NOTIFY_TOUCH_SIGNPOST = 129,
    NOTIFY_HUD_ENABLE = 130,
    NOTIFY_ADD_COIN = 131,
    NOTIFY_KILL_ENEMY = 132,
    NOTIFY_SAVESLOT_SELECT = 133,
    NOTIFY_FUTURE_PAST = 134,
    NOTIFY_GOTO_FUTURE_PAST = 135,
    NOTIFY_BOSS_END = 136,
    NOTIFY_SPECIAL_END = 137,
    NOTIFY_DEBUGPRINT = 138,
    NOTIFY_KILL_BOSS = 139,
    NOTIFY_TOUCH_EMERALD = 140,
    NOTIFY_STATS_ENEMY = 141,
    NOTIFY_STATS_CHARA_ACTION = 142,
    NOTIFY_STATS_RING = 143,
    NOTIFY_STATS_MOVIE = 144,
    NOTIFY_STATS_PARAM_1 = 145,
    NOTIFY_STATS_PARAM_2 = 146,
    NOTIFY_CHARACTER_SELECT = 147,
    NOTIFY_SPECIAL_RETRY = 148,
    NOTIFY_TOUCH_CHECKPOINT = 149,
    NOTIFY_ACT_FINISH = 150,
    NOTIFY_1P_VS_SELECT = 151,
    NOTIFY_CONTROLLER_SUPPORT = 152,
    NOTIFY_STAGE_RETRY = 153,
    NOTIFY_SOUND_TRACK = 154,
    NOTIFY_GOOD_ENDING = 155,
    NOTIFY_BACK_TO_MAINMENU = 156,
    NOTIFY_LEVEL_SELECT_MENU = 157,
    NOTIFY_PLAYER_SET = 158,
    NOTIFY_EXTRAS_MODE = 159,
    NOTIFY_SPIN_DASH_TYPE = 160,
    NOTIFY_TIME_OVER = 161,
    NOTIFY_TIMEATTACK_MODE = 162,
    NOTIFY_STATS_BREAK_OBJECT = 163,
    NOTIFY_STATS_SAVE_FUTURE = 164,
    NOTIFY_STATS_CHARA_ACTION2 = 165,

    // Sega Forever stuff
    CALLBACK_SHOWMENU_2 = 997,
    CALLBACK_SHOWHELPCENTER = 998,
    CALLBACK_CHANGEADSTYPE = 999,
    CALLBACK_NONE_1000 = 1000,
    CALLBACK_NONE_1001 = 1001,
    CALLBACK_NONE_1006 = 1002,
    CALLBACK_ONSHOWINTERSTITIAL = 1003,
    CALLBACK_ONSHOWBANNER = 1004,
    CALLBACK_ONSHOWBANNER_PAUSESTART = 1005,
    CALLBACK_ONHIDEBANNER = 1006,
    CALLBACK_REMOVEADSBUTTON_FADEOUT = 1007,
    CALLBACK_REMOVEADSBUTTON_FADEIN = 1008,
    CALLBACK_ONSHOWINTERSTITIAL_2 = 1009,
    CALLBACK_ONSHOWINTERSTITIAL_3 = 1010,
    CALLBACK_ONSHOWINTERSTITIAL_4 = 1011,
    CALLBACK_ONVISIBLEGRIDBTN_1 = 1012,
    CALLBACK_ONVISIBLEGRIDBTN_0 = 1013,
    CALLBACK_ONSHOWINTERSTITIAL_PAUSEDURATION = 1014,
    CALLBACK_SHOWCOUNTDOWNMENU = 1015,
    CALLBACK_ONVISIBLEMAINMENU_1 = 1016,
    CALLBACK_ONVISIBLEMAINMENU_0 = 1017,
    CALLBACK_ONSHOWREWARDADS = 1018,
    CALLBACK_ONSHOWBANNER_2 = 1019,
    CALLBACK_ONSHOWINTERSTITIAL_5 = 1020,

    // Custom
    CALLBACK_COPYPALETTE = 2000,
};

struct Matrix
{
  int32 values[4][4];
};

struct String
{
  uint16 *chars;
  uint16 length;
  uint16 size;
};

typedef enum {
    SCOPE_NONE,
    SCOPE_GLOBAL,
    SCOPE_STAGE,
} Scopes;

typedef enum {
    GAME_S1 = 0,
    GAME_CD = 1,
    GAME_S2 = 2,
    GAME_SM = 3,
    GAME_S3K = 4,
    GAME_S3 = 5,
    GAME_SK = 6,
} GameTypes;

typedef enum { FLIP_NONE, FLIP_X, FLIP_Y, FLIP_XY } FlipFlags;

struct GlobalVariables
{
    GameModes gameMode;
    CharacterIDs playerID;
    int specialCleared;
    int specialRingID;
    int blueSpheresID;
    int blueSpheresInit;
    int atlEnabled;
    int atlEntityCount;
    int atlEntitySlot[288];
    void* atlEntityData[288][276];
    int saveLoaded;
    int saveRAM[7168];
    int saveSlotID;
    int noSaveSlot[256];
    int menuParam[16384];
    int itemMode;
    int suppressTitlecard;
    int suppressAutoMusic;
    int competitionSession[16384];
    int medalMods;
    uint8 gapC2CB8[0x400734];
    bool32 vapeMode;
    int32 secrets;
    int32 field_447BF4;
    bool32 soundTestEnabled;
    bool32 superMusicEnabled;
    GameTypes playerSpriteStyle;
    GameTypes gameSpriteStyle;
    GameTypes ostStyle;
    GameTypes starpostStyle;
    uint8 gap4C340C[0xC4];
    bool32 disableLives;
    bool32 mirrorMode;
    bool32 useManiaBehavior;
    int32 coinCount;
    uint8 gap4C34DC[0x28];
    bool32 hasPlusDLC;
    int32 playMode;
    int32 callbackParam0;
    int32 callbackParam1;
    int32 callbackParam2;
    int32 callbackParam3;
    bool32 hudEnable;
    bool32 useCoins;
    uint8 gap4C352C[0x60];
    bool32 waitSSRetry;
};

struct Hitbox
{
    int16 left;
    int16 top;
    int16 right;
    int16 bottom;
};

struct GameSpriteFrame
{
    int16 sprX;
    int16 sprY;
    int16 width;
    int16 height;
    int16 pivotX;
    int16 pivotY;
    uint16 duration;
    uint16 unicodeChar;
    uint8 sheetID;
};

struct SpriteFrame
{
    GameSpriteFrame frame;
    Hitbox hitboxes[8];
};

struct ScreenInfo
{
    uint16 frameBuffer[307200];
    Vector2 position;
    Vector2 size;
    Vector2 center;
    int32 pitch;
    int32 clipBound_X1;
    int32 clipBound_Y1;
    int32 clipBound_X2;
    int32 clipBound_Y2;
    int32 waterDrawPos;
};

struct FunctionTable
{
    // Registration
#if RETRO_REV0U
    void (*RegisterGlobalVariables)(void** globals, int32 size, void (*initCB)(void* globals));
    void (*RegisterObject)(void** staticVars, const char* name, uint32 entityClassSize, uint32 staticClassSize, void (*update)(void),
        void (*lateUpdate)(void), void (*staticUpdate)(void), void (*draw)(void), void (*create)(void*), void (*stageLoad)(void),
        void (*editorDraw)(void), void (*editorLoad)(void), void (*serialize)(void), void (*staticLoad)(void* staticVars));
#else
    void (*RegisterGlobalVariables)(void** globals, int32 size);
    void (*RegisterObject)(void** staticVars, const char* name, uint32 entityClassSize, uint32 staticClassSize, void (*update)(void),
        void (*lateUpdate)(void), void (*staticUpdate)(void), void (*draw)(void), void (*create)(void*), void (*stageLoad)(void),
        void (*editorDraw)(void), void (*editorLoad)(void), void (*serialize)(void));
#endif
#if RETRO_REV02
    void (*RegisterStaticVariables)(void** varClass, const char* name, uint32 classSize);
#endif

    // Entities & Objects
    bool32(*GetActiveEntities)(uint16 group, void** entity);
    bool32(*GetAllEntities)(uint16 classID, void** entity);
    void (*BreakForeachLoop)(void);
    void (*SetEditableVar)(uint8 type, const char* name, uint8 classID, int32 offset);
    void* (*GetEntity)(uint16 slot);
    int32(*GetEntitySlot)(void* entity);
    int32(*GetEntityCount)(uint16 classID, bool32 isActive);
    int32(*GetDrawListRefSlot)(uint8 drawGroup, uint16 listPos);
    void* (*GetDrawListRef)(uint8 drawGroup, uint16 listPos);
    void (*ResetEntity)(void* entity, uint16 classID, void* data);
    void (*ResetEntitySlot)(uint16 slot, uint16 classID, void* data);
    Entity* (*CreateEntity)(uint16 classID, void* data, int32 x, int32 y);
    void (*CopyEntity)(void* destEntity, void* srcEntity, bool32 clearSrcEntity);
    bool32(*CheckOnScreen)(void* entity, Vector2* range);
    bool32(*CheckPosOnScreen)(Vector2* position, Vector2* range);
    void (*AddDrawListRef)(uint8 drawGroup, uint16 entitySlot);
    void (*SwapDrawListEntries)(uint8 drawGroup, uint16 slot1, uint16 slot2, uint16 count);
    void (*SetDrawGroupProperties)(uint8 drawGroup, bool32 sorted, void (*hookCB)(void));

    // Scene Management
    void (*SetScene)(const char* categoryName, const char* sceneName);
    void (*SetEngineState)(uint8 state);
#if RETRO_REV02
    void (*ForceHardReset)(bool32 shouldHardReset);
#endif
    bool32(*CheckValidScene)(void);
    bool32(*CheckSceneFolder)(const char* folderName);
    void (*LoadScene)(void);
    int32(*FindObject)(const char* name);

    // Cameras
    void (*ClearCameras)(void);
    void (*AddCamera)(Vector2* targetPos, int32 offsetX, int32 offsetY, bool32 worldRelative);

    // API (Rev01 only)
#if !RETRO_REV02
    void* (*GetAPIFunction)(const char* funcName);
#endif

    // Window/Video Settings
    int32(*GetVideoSetting)(int32 id);
    void (*SetVideoSetting)(int32 id, int32 value);
    void (*UpdateWindow)(void);

    // Math
    int32(*Sin1024)(int32 angle);
    int32(*Cos1024)(int32 angle);
    int32(*Tan1024)(int32 angle);
    int32(*ASin1024)(int32 angle);
    int32(*ACos1024)(int32 angle);
    int32(*Sin512)(int32 angle);
    int32(*Cos512)(int32 angle);
    int32(*Tan512)(int32 angle);
    int32(*ASin512)(int32 angle);
    int32(*ACos512)(int32 angle);
    int32(*Sin256)(int32 angle);
    int32(*Cos256)(int32 angle);
    int32(*Tan256)(int32 angle);
    int32(*ASin256)(int32 angle);
    int32(*ACos256)(int32 angle);
    int32(*Rand)(int32 min, int32 max);
    int32(*RandSeeded)(int32 min, int32 max, int32* seed);
    void (*SetRandSeed)(int32 seed);
    uint8(*ATan2)(int32 x, int32 y);

    // Matrices
    void (*SetIdentityMatrix)(Matrix* matrix);
    void (*MatrixMultiply)(Matrix* dest, Matrix* matrixA, Matrix* matrixB);
    void (*MatrixTranslateXYZ)(Matrix* matrix, int32 x, int32 y, int32 z, bool32 setIdentity);
    void (*MatrixScaleXYZ)(Matrix* matrix, int32 x, int32 y, int32 z);
    void (*MatrixRotateX)(Matrix* matrix, int16 angle);
    void (*MatrixRotateY)(Matrix* matrix, int16 angle);
    void (*MatrixRotateZ)(Matrix* matrix, int16 angle);
    void (*MatrixRotateXYZ)(Matrix* matrix, int16 x, int16 y, int16 z);
    void (*MatrixInverse)(Matrix* dest, Matrix* matrix);
    void (*MatrixCopy)(Matrix* matDest, Matrix* matSrc);

    // Strings
    void (*InitString)(String* string, const char* text, uint32 textLength);
    void (*CopyString)(String* dst, String* src);
    void (*SetString)(String* string, const char* text);
    void (*AppendString)(String* string, String* appendString);
    void (*AppendText)(String* string, const char* appendText);
    void (*LoadStringList)(String* stringList, const char* filePath, uint32 charSize);
    bool32(*SplitStringList)(String* splitStrings, String* stringList, int32 startStringID, int32 stringCount);
    void (*GetCString)(char* destChars, String* string);
    bool32(*CompareStrings)(String* string1, String* string2, bool32 exactMatch);

    // Screens & Displays
    void (*GetDisplayInfo)(int32* displayID, int32* width, int32* height, int32* refreshRate, char* text);
    void (*GetWindowSize)(int32* width, int32* height);
    int32(*SetScreenSize)(uint8 screenID, uint16 width, uint16 height);
    void (*SetClipBounds)(uint8 screenID, int32 x1, int32 y1, int32 x2, int32 y2);
#if RETRO_REV02
    void (*SetScreenVertices)(uint8 startVert2P_S1, uint8 startVert2P_S2, uint8 startVert3P_S1, uint8 startVert3P_S2, uint8 startVert3P_S3);
#endif

    // Spritesheets
    uint16(*LoadSpriteSheet)(const char* filePath, uint8 scope);

    // Palettes & Colors
#if RETRO_REV02
    void (*SetTintLookupTable)(uint16* lookupTable);
#else
    uint16* (*GetTintLookupTable)(void);
#endif
    void (*SetPaletteMask)(color maskColor);
    void (*SetPaletteEntry)(uint8 bankID, uint8 index, uint32 color);
    color(*GetPaletteEntry)(uint8 bankID, uint8 index);
    void (*SetActivePalette)(uint8 newActiveBank, int32 startLine, int32 endLine);
    void (*CopyPalette)(uint8 sourceBank, uint8 srcBankStart, uint8 destinationBank, uint8 destBankStart, uint8 count);
#if RETRO_REV02
    void (*LoadPalette)(uint8 bankID, const char* path, uint16 disabledRows);
#endif
    void (*RotatePalette)(uint8 bankID, uint8 startIndex, uint8 endIndex, bool32 right);
    void (*SetLimitedFade)(uint8 destBankID, uint8 srcBankA, uint8 srcBankB, int16 blendAmount, int32 startIndex, int32 endIndex);
#if RETRO_REV02
    void (*BlendColors)(uint8 destBankID, color* srcColorsA, color* srcColorsB, int32 blendAmount, int32 startIndex, int32 count);
#endif

    // Drawing
    void (*DrawRect)(int32 x, int32 y, int32 width, int32 height, uint32 color, int32 alpha, int32 inkEffect, bool32 screenRelative);
    void (*DrawLine)(int32 x1, int32 y1, int32 x2, int32 y2, uint32 color, int32 alpha, int32 inkEffect, bool32 screenRelative);
    void (*DrawCircle)(int32 x, int32 y, int32 radius, uint32 color, int32 alpha, int32 inkEffect, bool32 screenRelative);
    void (*DrawCircleOutline)(int32 x, int32 y, int32 innerRadius, int32 outerRadius, uint32 color, int32 alpha, int32 inkEffect,
        bool32 screenRelative);
    void (*DrawFace)(Vector2* vertices, int32 vertCount, int32 r, int32 g, int32 b, int32 alpha, int32 inkEffect);
    void (*DrawBlendedFace)(Vector2* vertices, color* vertColors, int32 vertCount, int32 alpha, int32 inkEffect);
    void (*DrawSprite)(Animator* animator, Vector2* position, bool32 screenRelative);
    void (*DrawDeformedSprite)(uint16 sheetID, int32 inkEffect, bool32 screenRelative);
    void (*DrawText)(Animator* animator, Vector2* position, String* string, int32 endFrame, int32 textLength, int32 align, int32 spacing,
        void* unused, Vector2* charOffsets, bool32 screenRelative);
    void (*DrawTile)(uint16* tiles, int32 countX, int32 countY, Vector2* position, Vector2* offset, bool32 screenRelative);
    void (*CopyTile)(uint16 dest, uint16 src, uint16 count);
    void (*DrawAniTiles)(uint16 sheetID, uint16 tileIndex, uint16 srcX, uint16 srcY, uint16 width, uint16 height);
#if RETRO_REV0U
    void (*DrawDynamicAniTiles)(Animator* animator, uint16 tileIndex);
#endif
    void (*FillScreen)(uint32 color, int32 alphaR, int32 alphaG, int32 alphaB);

    // Meshes & 3D Scenes
    uint16(*LoadMesh)(const char* filename, uint8 scope);
    uint16(*Create3DScene)(const char* identifier, uint16 faceCount, uint8 scope);
    void (*Prepare3DScene)(uint16 sceneIndex);
    void (*SetDiffuseColor)(uint16 sceneIndex, uint8 x, uint8 y, uint8 z);
    void (*SetDiffuseIntensity)(uint16 sceneIndex, uint8 x, uint8 y, uint8 z);
    void (*SetSpecularIntensity)(uint16 sceneIndex, uint8 x, uint8 y, uint8 z);
    void (*AddModelTo3DScene)(uint16 modelFrames, uint16 sceneIndex, uint8 drawMode, Matrix* matWorld, Matrix* matView, color color);
    void (*SetModelAnimation)(uint16 modelFrames, Animator* animator, int16 speed, uint8 loopIndex, bool32 forceApply, int16 frameID);
    void (*AddMeshFrameTo3DScene)(uint16 modelFrames, uint16 sceneIndex, Animator* animator, uint8 drawMode, Matrix* matWorld, Matrix* matView,
        color color);
    void (*Draw3DScene)(uint16 sceneIndex);

    // Sprite Animations & Frames
    uint16(*LoadSpriteAnimation)(const char* filePath, uint8 scope);
    uint16(*CreateSpriteAnimation)(const char* filePath, uint32 frameCount, uint32 listCount, uint8 scope);
    void (*SetSpriteAnimation)(uint16 aniFrames, uint16 listID, Animator* animator, bool32 forceApply, int32 frameID);
    void (*EditSpriteAnimation)(uint16 aniFrames, uint16 listID, const char* name, int32 frameOffset, uint16 frameCount, int16 speed, uint8 loopIndex,
        uint8 rotationStyle);
    void (*SetSpriteString)(uint16 aniFrames, uint16 listID, String* string);
    uint16(*FindSpriteAnimation)(uint16 aniFrames, const char* name);
    SpriteFrame* (*GetFrame)(uint16 aniFrames, uint16 listID, int32 frameID);
    Hitbox* (*GetHitbox)(Animator* animator, uint8 hitboxID);
    int16(*GetFrameID)(Animator* animator);
    int32(*GetStringWidth)(uint16 aniFrames, uint16 listID, String* string, int32 startIndex, int32 length, int32 spacing);
    void (*ProcessAnimation)(Animator* animator);

    // Tile Layers
    uint16(*GetTileLayerID)(const char* name);
    void* (*GetTileLayer)(uint16 layerID);
    void (*GetLayerSize)(uint16 layer, Vector2* size, bool32 usePixelUnits);
    uint16(*GetTile)(uint16 layer, int32 x, int32 y);
    void (*SetTile)(uint16 layer, int32 x, int32 y, uint16 tile);
    void (*CopyTileLayer)(uint16 dstLayerID, int32 dstStartX, int32 dstStartY, uint16 srcLayerID, int32 srcStartX, int32 srcStartY, int32 countX,
        int32 countY);
    void (*ProcessParallax)(void* tileLayer);
    void* (*GetScanlines)(void);

    // Object & Tile Collisions
    bool32(*CheckObjectCollisionTouchBox)(void* thisEntity, Hitbox* thisHitbox, void* otherEntity, Hitbox* otherHitbox);
    bool32(*CheckObjectCollisionTouchCircle)(void* thisEntity, int32 thisRadius, void* otherEntity, int32 otherRadius);
    uint8(*CheckObjectCollisionBox)(void* thisEntity, Hitbox* thisHitbox, void* otherEntity, Hitbox* otherHitbox, bool32 setPos);
    bool32(*CheckObjectCollisionPlatform)(void* thisEntity, Hitbox* thisHitbox, void* otherEntity, Hitbox* otherHitbox, bool32 setPos);
    bool32(*ObjectTileCollision)(void* entity, uint16 collisionLayers, uint8 collisionMode, uint8 collisionPlane, int32 xOffset, int32 yOffset,
        bool32 setPos);
    bool32(*ObjectTileGrip)(void* entity, uint16 collisionLayers, uint8 collisionMode, uint8 collisionPlane, int32 xOffset, int32 yOffset,
        int32 tolerance);
    void (*ProcessObjectMovement)(void* entity, Hitbox* outer, Hitbox* inner);
#if RETRO_REV0U
    void (*SetupCollisionConfig)(int32 minDistance, uint8 lowTolerance, uint8 highTolerance, uint8 floorAngleTolerance, uint8 wallAngleTolerance,
        uint8 roofAngleTolerance);
    void (*SetPathGripSensors)(void* sensors); // expects 5 sensors
    void (*FindFloorPosition)(void* sensor);
    void (*FindLWallPosition)(void* sensor);
    void (*FindRoofPosition)(void* sensor);
    void (*FindRWallPosition)(void* sensor);
    void (*FloorCollision)(void* sensor);
    void (*LWallCollision)(void* sensor);
    void (*RoofCollision)(void* sensor);
    void (*RWallCollision)(void* sensor);
#endif
    int32(*GetTileAngle)(uint16 tile, uint8 cPlane, uint8 cMode);
    void (*SetTileAngle)(uint16 tile, uint8 cPlane, uint8 cMode, uint8 angle);
    uint8(*GetTileFlags)(uint16 tile, uint8 cPlane);
    void (*SetTileFlags)(uint16 tile, uint8 cPlane, uint8 flag);
#if RETRO_REV0U
    void (*CopyCollisionMask)(uint16 dst, uint16 src, uint8 cPlane, uint8 cMode);
    void (*GetCollisionInfo)(void** masks, void** tileInfo);
#endif

    // Audio
    uint16(*GetSfx)(const char* path);
    int32(*PlaySfx)(uint16 sfx, int32 loopPoint, int32 priority);
    void (*StopSfx)(uint16 sfx);
    int32(*PlayStream)(const char* filename, uint32 channel, uint32 startPos, uint32 loopPoint, bool32 loadASync);
    void (*SetChannelAttributes)(uint8 channel, float volume, float pan, float speed);
    void (*StopChannel)(uint32 channel);
    void (*PauseChannel)(uint32 channel);
    void (*ResumeChannel)(uint32 channel);
    bool32(*IsSfxPlaying)(uint16 sfx);
    bool32(*ChannelActive)(uint32 channel);
    uint32(*GetChannelPos)(uint32 channel);

    // Videos & "HD Images"
    bool32(*LoadVideo)(const char* filename, double startDelay, bool32(*skipCallback)(void));
    bool32(*LoadImage)(const char* filename, double displayLength, double fadeSpeed, bool32(*skipCallback)(void));

    // Input
#if RETRO_REV02
    uint32(*GetInputDeviceID)(uint8 inputSlot);
    uint32(*GetFilteredInputDeviceID)(bool32 confirmOnly, bool32 unassignedOnly, uint32 maxInactiveTimer);
    int32(*GetInputDeviceType)(uint32 deviceID);
    bool32(*IsInputDeviceAssigned)(uint32 deviceID);
    int32(*GetInputDeviceUnknown)(uint32 deviceID);
    int32(*InputDeviceUnknown1)(uint32 deviceID, int32 unknown1, int32 unknown2);
    int32(*InputDeviceUnknown2)(uint32 deviceID, int32 unknown1, int32 unknown2);
    int32(*GetInputSlotUnknown)(uint8 inputSlot);
    int32(*InputSlotUnknown1)(uint8 inputSlot, int32 unknown1, int32 unknown2);
    int32(*InputSlotUnknown2)(uint8 inputSlot, int32 unknown1, int32 unknown2);
    void (*AssignInputSlotToDevice)(uint8 inputSlot, uint32 deviceID);
    bool32(*IsInputSlotAssigned)(uint8 inputSlot);
    void (*ResetInputSlotAssignments)(void);
#endif
#if !RETRO_REV02
    void (*GetUnknownInputValue)(int32 inputSlot, int32 type, int32* value);
#endif

    // User File Management
    bool32(*LoadUserFile)(const char* fileName, void* buffer, uint32 size); // load user file from exe dir
    bool32(*SaveUserFile)(const char* fileName, void* buffer, uint32 size); // save user file to exe dir

    // Printing (Rev02)
#if RETRO_REV02
    void (*PrintLog)(int32 mode, const char* message, ...);
    void (*PrintText)(int32 mode, const char* message);
    void (*PrintString)(int32 mode, String* message);
    void (*PrintUInt32)(int32 mode, const char* message, uint32 i);
    void (*PrintInt32)(int32 mode, const char* message, int32 i);
    void (*PrintFloat)(int32 mode, const char* message, float f);
    void (*PrintVector2)(int32 mode, const char* message, Vector2 vec);
    void (*PrintHitbox)(int32 mode, const char* message, Hitbox hitbox);
#endif

    // Editor
    void (*SetActiveVariable)(int32 classID, const char* name);
    void (*AddVarEnumValue)(const char* name);

    // Printing (Rev01)
#if !RETRO_REV02
    void (*PrintMessage)(void* message, uint8 type);
#endif

    // Debugging
#if RETRO_REV02
    void (*ClearViewableVariables)(void);
    void (*AddViewableVariable)(const char* name, void* value, int32 type, int32 min, int32 max);
#endif

#if RETRO_REV0U
    // Origins Extras
    void (*NotifyCallback)(int32 callbackID, int32 param1, int32 param2, int32 param3);
    void (*SetGameFinished)(void);
#endif
#if RETRO_REV0U
    void (*StopAllSfx)(void);
#endif

};

struct ObjectPlayer
{
    char padding0[0x1174];
    int32 playerCount;
};

struct NotifyCallbackInfo
{
    RetroEngineCallbacks callback;
    int32 param1;
    int32 param2;
    int32 param3;
    int32 param4;
    int32 param5;
};
