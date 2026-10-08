// Sonic Mania Plus's save slot (Mania Mode's save select), as the RSDKv5 decompilation declares it
// (SonicMania/Objects/Menu/UISaveSlot.h with GameVariables.h's MANIA_UI_ITEM_BASE, Plus build), for NoSwapMania.
// Copied field for field; checked against the decompilation's own header by native/mania/check_layout.sh.
#ifndef MANIA_MENU_H
#define MANIA_MENU_H

#include "GameAPI/Game.h"

#include <stddef.h>

#define NO_SAVE_SLOT (255)

typedef enum { UISAVESLOT_REGULAR, UISAVESLOT_NOSAVE } UISaveSlotTypes;

typedef struct {
    RSDK_OBJECT
    uint16 aniFrames;
} ObjectUISaveSlot;

typedef struct {
    // MANIA_UI_ITEM_BASE
    RSDK_ENTITY
    StateMachine(state);
    void (*processButtonCB)(void);
    bool32 (*touchCB)(void);
    void (*actionCB)(void);
    void (*selectedCB)(void);
    void (*failCB)(void);
    void (*buttonEnterCB)(void);
    void (*buttonLeaveCB)(void);
    bool32 (*checkButtonEnterCB)(void);
    bool32 (*checkSelectedCB)(void);
    int32 timer;
    Vector2 startPos;
    Entity *parent;
    Vector2 touchPosSizeS;
    Vector2 touchPosOffsetS;
    bool32 touchPressed;
    Vector2 touchPosSizeM[4];
    Vector2 touchPosOffsetM[4];
    void (*touchPosCallbacks[4])(void);
    int32 touchPosCount;
    int32 touchPosID;
    bool32 isSelected;
    bool32 disabled;
    // UISaveSlot
    bool32 isNewSave;
    StateMachine(stateInput);
    int32 listID;
    int32 frameID; // 0 Sonic & Tails, 1 Sonic, 2 Tails, 3 Knuckles, 4 Mighty, 5 Ray
    int32 saveZoneID;
    int32 saveLives;
    int32 saveContinues;
    int32 saveEmeralds;
    uint8 saveEncorePlayer;
    uint8 saveEncoreBuddy;
    uint8 saveEncoreFriends[3];
    int32 type; // UISaveSlotTypes
    int32 slotID;
    bool32 encoreMode;
    bool32 currentlySelected;
    int32 zoneIconSprX;
    int32 textBounceOffset;
    int32 buttonBounceOffset;
    int32 textBouncePos;
    int32 buttonBouncePos;
    int32 fxRadius;
    Entity *fxRuby;
    bool32 debugEncoreDraw;
    uint8 dCharPoint;
    uint8 dCharPartner;
    uint8 dCharStock1;
    uint8 dCharStock2;
    uint8 dCharStock3;
    Animator uiAnimator;
    Animator playersAnimator;
    Animator shadowsAnimator;
    Animator livesAnimator;
    Animator continuesAnimator;
    Animator emeraldsAnimator;
    Animator zoneIconAnimator;
    Animator zoneNameAnimator;
    Animator fuzzAnimator;
    Animator iconBGAnimator;
    Animator saveStatusAnimator;
    Animator numbersAnimator;
    uint16 textFrames;
} EntityUISaveSlot;

// Offsets in the decompilation's Plus build (x86-64), from native/mania/check_layout.sh
#define MENU_ASSERT(type, field, off) _Static_assert(offsetof(type, field) == (off), #type "." #field " moved")
_Static_assert(sizeof(EntityUISaveSlot) == 840, "EntityUISaveSlot size");
MENU_ASSERT(ObjectUISaveSlot, aniFrames, 4);
MENU_ASSERT(EntityUISaveSlot, parent, 192);
MENU_ASSERT(EntityUISaveSlot, isNewSave, 336);
MENU_ASSERT(EntityUISaveSlot, stateInput, 344);
MENU_ASSERT(EntityUISaveSlot, frameID, 356);
MENU_ASSERT(EntityUISaveSlot, type, 384);
MENU_ASSERT(EntityUISaveSlot, slotID, 388);
MENU_ASSERT(EntityUISaveSlot, encoreMode, 392);
MENU_ASSERT(EntityUISaveSlot, buttonBounceOffset, 408);
MENU_ASSERT(EntityUISaveSlot, uiAnimator, 448);
MENU_ASSERT(EntityUISaveSlot, zoneIconAnimator, 640);
MENU_ASSERT(EntityUISaveSlot, textFrames, 832);

#endif // MANIA_MENU_H
