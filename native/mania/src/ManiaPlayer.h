// Sonic Mania Plus's Player object, as the RSDKv5 decompilation declares it (SonicMania/Objects/Global/Player.h, Plus
// build: MANIA_USE_PLUS, GAME_VERSION VER_106, RETRO_REVISION 3), for a mod built against RSDKv5-GameAPI, which has no
// object headers. Copied field for field (TABLE / STATIC initialisers dropped); the layout is checked against the
// decompilation's own header by native/mania/check_layout.sh (the offsets asserted at the end).
#ifndef MANIA_PLAYER_H
#define MANIA_PLAYER_H

#include "GameAPI/Game.h"

#include <stddef.h>

#define PLAYER_PALETTE_INDEX_SONIC  (64)
#define PLAYER_PRIMARY_COLOR_COUNT (6)

typedef enum {
    ANI_IDLE, ANI_BORED_1, ANI_BORED_2, ANI_LOOK_UP, ANI_CROUCH, ANI_WALK, ANI_AIR_WALK, ANI_JOG, ANI_RUN, ANI_DASH,
    ANI_JUMP, ANI_SPRING_TWIRL, ANI_SPRING_DIAGONAL, ANI_SKID, ANI_SKID_TURN, ANI_SPINDASH, ANI_ABILITY_0, ANI_PUSH,
    ANI_HURT, ANI_DIE, ANI_DROWN, ANI_BALANCE_1, ANI_BALANCE_2, ANI_SPRING_CS, ANI_STAND_CS, ANI_FAN, ANI_VICTORY,
    ANI_OUTTA_HERE, ANI_HANG, ANI_HANG_MOVE, ANI_POLE_SWING_V, ANI_POLE_SWING_H, ANI_SHAFT_SWING, ANI_TURNTABLE,
    ANI_TWISTER, ANI_SPIRAL_RUN, ANI_STICK, ANI_PULLEY_HOLD, ANI_SHIMMY_IDLE, ANI_SHIMMY_MOVE, ANI_BUBBLE, ANI_BREATHE,
    ANI_RIDE, ANI_CLING, ANI_BUNGEE, ANI_TWIST_RUN, ANI_FLUME, ANI_TRANSFORM, ANI_ABILITY_1, ANI_ABILITY_2,
    ANI_ABILITY_3, ANI_ABILITY_4, ANI_ABILITY_5, ANI_ABILITY_6, ANI_ABILITY_7,
    ANI_MANIA_COUNT, // (55: ANI_ABILITY_7 is only in Mighty/Ray-style sheets, NOT in Sonic.bin)
} PlayerAnimationIDs;

// Sonic.bin (the template tools/build_mania_art.py fills) has 54 animations, 0..53 (ANI_ABILITY_6 = Swim Tired is its
// last), so NoSwap's ability animations start at 54 = ANI_ABILITY_7, NOT at ANI_MANIA_COUNT (55).
#define ANI_SONIC_COUNT (54)

typedef enum {
    SUPERSTATE_NONE,
    SUPERSTATE_FADEIN,
    SUPERSTATE_SUPER,
    SUPERSTATE_FADEOUT,
    SUPERSTATE_DONE,
} SuperStates;

typedef struct ObjectPlayer ObjectPlayer;
typedef struct EntityPlayer EntityPlayer;

struct ObjectPlayer {
    RSDK_OBJECT
    int32 sonicPhysicsTable[64];
    int32 tailsPhysicsTable[64];
    int32 knuxPhysicsTable[64];
    int32 mightyPhysicsTable[64];
    int32 rayPhysicsTable[64];
    color superPalette_Sonic[18];
    color superPalette_Tails[18];
    color superPalette_Knux[18];
    color superPalette_Mighty[18];
    color superPalette_Ray[18];
    color superPalette_Sonic_HCZ[18];
    color superPalette_Tails_HCZ[18];
    color superPalette_Knux_HCZ[18];
    color superPalette_Mighty_HCZ[18];
    color superPalette_Ray_HCZ[18];
    color superPalette_Sonic_CPZ[18];
    color superPalette_Tails_CPZ[18];
    color superPalette_Knux_CPZ[18];
    color superPalette_Mighty_CPZ[18];
    color superPalette_Ray_CPZ[18];
    bool32 cantSwap;
    int32 playerCount;
    uint16 upState;
    uint16 downState;
    uint16 leftState;
    uint16 rightState;
    uint16 jumpPressState;
    uint16 jumpHoldState;
    int32 nextLeaderPosID;
    int32 lastLeaderPosID;
    Vector2 leaderPositionBuffer[16];
    Vector2 targetLeaderPosition;
    int32 autoJumpTimer;
    int32 respawnTimer;
    int32 aiInputSwapTimer;
    bool32 disableP2KeyCheck;
    int32 rings;
    int32 ringExtraLife;
    int32 powerups;
    int32 savedLives;
    int32 savedScore;
    int32 savedScore1UP;
    uint16 sonicFrames;
    uint16 superFrames;
    uint16 tailsFrames;
    uint16 tailsTailsFrames;
    uint16 knuxFrames;
    uint16 mightyFrames;
    uint16 rayFrames;
    uint16 sfxJump;
    uint16 sfxRoll;
    uint16 sfxCharge;
    uint16 sfxRelease;
    uint16 sfxPeelCharge;
    uint16 sfxPeelRelease;
    uint16 sfxDropdash;
    uint16 sfxLoseRings;
    uint16 sfxHurt;
    uint16 sfxPimPom;
    uint16 sfxSkidding;
    uint16 sfxGrab;
    uint16 sfxFlying;
    bool32 playingFlySfx;
    uint16 sfxTired;
    bool32 playingTiredSfx;
    uint16 sfxLand;
    uint16 sfxSlide;
    uint16 sfxOuttahere;
    uint16 sfxTransform2;
    uint16 sfxSwap;
    uint16 sfxSwapFail;
    uint16 sfxMightyDeflect;
    uint16 sfxMightyDrill;
    uint16 sfxMightyLand;
    uint16 sfxMightyUnspin;
    int32 raySwoopTimer;
    int32 rayDiveTimer;
    bool32 gotHit[PLAYER_COUNT];
    StateMachine(configureGhostCB);
    bool32 (*canSuperCB)(bool32 isHUD);
    int32 superDashCooldown;
};

// Entity Class
struct EntityPlayer {
    RSDK_ENTITY
    StateMachine(state);
    StateMachine(nextAirState);
    StateMachine(nextGroundState);
    void *camera; // EntityCamera *
    Animator animator;
    Animator tailAnimator;
    int32 minJogVelocity;
    int32 minRunVelocity;
    int32 minDashVelocity;
    int32 unused; // the only used variable in the player struct, I cant find a ref to it anywhere so...
    int32 tailRotation;
    int32 tailDirection;
    uint16 aniFrames;
    uint16 tailFrames;
    uint16 animationReserve; // what anim to return to after SpringTwirl/SpringDiagonal has finished and the player is falling downwards
    uint16 playerID;
    Hitbox *outerbox;
    Hitbox *innerbox;
    int32 characterID;
    int32 rings;
    int32 ringExtraLife;
    int32 shield;
    int32 lives;
    int32 score;
    int32 score1UP;
    bool32 hyperRing;
    int32 timer;
    int32 outtaHereTimer;
    int32 abilityTimer;
    int32 spindashCharge;
    int32 abilityValue;
    int32 drownTimer;
    int32 invincibleTimer;
    int32 speedShoesTimer;
    int32 blinkTimer;
    int32 scrollDelay;
    int32 skidding;
    int32 pushing;
    int32 underwater;     // 0 = not in water, 1 = in palette water, else water entityID
    bool32 groundedStore; // prev frame's onGround value
    bool32 invertGravity;
    bool32 isChibi;
    bool32 isTransforming;
    int32 superState;
    int32 superRingLossTimer;
    int32 superBlendAmount;
    int32 superBlendState;
    bool32 sidekick;
    int32 scoreBonus;
    int32 jumpOffset;
    int32 collisionFlagH;
    int32 collisionFlagV;
    int32 topSpeed;
    int32 acceleration;
    int32 deceleration;
    int32 airAcceleration;
    int32 airDeceleration;
    int32 skidSpeed;
    int32 rollingFriction;
    int32 rollingDeceleration;
    int32 gravityStrength;
    int32 abilitySpeed;
    int32 jumpStrength;
    int32 jumpCap;
    int32 flailing;
    int32 sensorX[5];
    int32 sensorY;
    Vector2 moveLayerPosition;
    StateMachine(stateInputReplay);
    StateMachine(stateInput);
    int32 controllerID;
    int32 controlLock;
    bool32 up;
    bool32 down;
    bool32 left;
    bool32 right;
    bool32 jumpPress;
    bool32 jumpHold;
    bool32 applyJumpCap;
    int32 jumpAbilityState;
    StateMachine(stateAbility);
    StateMachine(statePeelout);
    int32 flyCarryTimer;
    Vector2 flyCarrySidekickPos;
    Vector2 flyCarryLeaderPos;
    uint8 deathType;
    bool32 forceRespawn;
    bool32 isGhost;
    int32 abilityValues[8];
    void *abilityPtrs[8];
    int32 uncurlTimer;
};

// The decomp's EntityBreakableWall (SonicMania/Objects/Common/BreakableWall.h: ManiaWalls.h reads its state and hitbox)
typedef struct {
    RSDK_ENTITY
    void (*state)(void);
    void (*stateDraw)(void);
    uint8 type;
    bool32 onlyKnux;
    bool32 onlyMighty;
    int32 priority;
    Vector2 size;
    uint16 tileInfo;
    uint16 targetLayer;
    int32 timer;
    Vector2 tilePos;
    int32 tileRotation;
    int32 gravityStrength;
    Hitbox hitbox;
} EntityBreakableWall;

// Offsets in the decompilation's Plus build (x86-64), from native/mania/check_layout.sh
#define PLAYER_ASSERT(type, field, off) _Static_assert(offsetof(type, field) == (off), #type "." #field " moved")

_Static_assert(sizeof(ObjectPlayer) == 2688, "ObjectPlayer size");
_Static_assert(sizeof(EntityPlayer) == 672, "EntityPlayer size");
PLAYER_ASSERT(ObjectPlayer, sonicPhysicsTable, 4);
PLAYER_ASSERT(ObjectPlayer, superPalette_Sonic, 1284);
PLAYER_ASSERT(ObjectPlayer, superPalette_Sonic_HCZ, 1644);
PLAYER_ASSERT(ObjectPlayer, superPalette_Sonic_CPZ, 2004);
PLAYER_ASSERT(ObjectPlayer, sonicFrames, 2568);
PLAYER_ASSERT(ObjectPlayer, superFrames, 2570);
PLAYER_ASSERT(ObjectPlayer, superDashCooldown, 2680);
PLAYER_ASSERT(EntityPlayer, state, 96);
PLAYER_ASSERT(EntityPlayer, animator, 128);
PLAYER_ASSERT(EntityPlayer, aniFrames, 216);
PLAYER_ASSERT(EntityPlayer, characterID, 240);
PLAYER_ASSERT(EntityPlayer, drownTimer, 292);
PLAYER_ASSERT(EntityPlayer, underwater, 320);
PLAYER_ASSERT(EntityPlayer, superState, 340);
PLAYER_ASSERT(EntityPlayer, sidekick, 356);
PLAYER_ASSERT(EntityPlayer, topSpeed, 376);
PLAYER_ASSERT(EntityPlayer, jumpCap, 420);
PLAYER_ASSERT(EntityPlayer, stateInput, 472);
PLAYER_ASSERT(EntityPlayer, controllerID, 480);
PLAYER_ASSERT(EntityPlayer, jumpPress, 504);
PLAYER_ASSERT(EntityPlayer, jumpHold, 508);
PLAYER_ASSERT(EntityPlayer, jumpAbilityState, 516);
PLAYER_ASSERT(EntityPlayer, stateAbility, 520);
PLAYER_ASSERT(EntityPlayer, abilityValues, 568);
PLAYER_ASSERT(EntityPlayer, uncurlTimer, 664);
_Static_assert(offsetof(GlobalVariables, playerID) == 4, "globals.playerID");
_Static_assert(offsetof(GlobalVariables, medalMods) == 266420, "globals.medalMods");
_Static_assert(sizeof(GlobalVariables) == 4462500, "GlobalVariables size");

#endif // MANIA_PLAYER_H
