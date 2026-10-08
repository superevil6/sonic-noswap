#include "pch.h"
#include <HiteModLoader.h>
#include <Helpers.h>
#include "SigScan.h"
#include "Game.h"

struct VectorInt
{
    int* start;
    int* end;
};

// Too lazy to sig scan these
ObjectZone** Zone = (ObjectZone**)0x143DB5CE0;
ControllerState* controllers = (ControllerState*)0x143729A90;
SceneInfo* sceneInfo = (SceneInfo*)0x143DB14E0;
GlobalVariables* globals = (GlobalVariables*)0x144000210;
const char** CurrentStateName = (const char**)0x142E8C1D0; // Not important
FunctionTable* RSDK;
ObjectPlayer* Player;

HOOK(ObjectPlayer*, __fastcall, Player_StaticLoad, SigPlayer_StaticLoad(), ObjectPlayer* playerVars)
{
    Player = playerVars;
    return originalPlayer_StaticLoad(playerVars);
}

HOOK(void, __fastcall, Player_State_KnuxGlideLeft, SigPlayer_State_KnuxGlideLeft(), EntityPlayer* _this)
{
    originalPlayer_State_KnuxGlideLeft(_this);

    if (_this->position.x <= (*Zone)->playerBoundsL[_this->playerID] + 0x100000 && !_this->jumpHold)
    {
        _this->direction = 0;
    }
}

HOOK(void, __fastcall, sub_1401EA5E0, Sigsub_1401EA5E0(), EntityPlayer* player)
{
    if (player->onGround && player->chargeTimer >= 19 && player->jumpHold)
    {
        auto Camera_ShakeScreen = (void(__fastcall*)(int32 screen, int32 shakeX, int32 shakeY, int32 a4, int32 a5))(SigCamera_ShakeScreen());
        if (player->superState == SUPERSTATE_SUPER && player->camera)
            Camera_ShakeScreen(player->camera->screenID, 0, 6, 1, 1);
    }

    originalsub_1401EA5E0(player);
}

HOOK(bool *, __fastcall, sub_1403A2550, Sigsub_1403A2550(), uint32 deviceID)
{
    auto inputs = originalsub_1403A2550(deviceID);
    bool mirror = ((bool(__fastcall*)())(SigIsMirrorMode()))();

    if (deviceID == 0)
    {
        controllers[0].keyUp.press    = inputs[0];
        controllers[0].keyDown.press  = inputs[1];
        controllers[0].keyLeft.press  = inputs[2];
        controllers[0].keyRight.press = inputs[3];
        controllers[0].keyA.press     = inputs[4];
        controllers[0].keyB.press     = inputs[5];
        controllers[0].keyC.press     = inputs[6];
        controllers[0].keyStart.press = inputs[20];
    
        controllers[1].keyUp.press     = inputs[10] | inputs[0];
        controllers[1].keyDown.press   = inputs[11] | inputs[1];
        controllers[1].keyLeft.press   = inputs[12] | inputs[2];
        controllers[1].keyRight.press  = inputs[13] | inputs[3];
        controllers[1].keyA.press      = inputs[14];
        controllers[1].keyB.press      = inputs[15];
        controllers[1].keyC.press      = inputs[16];
        controllers[1].keyX.press      = inputs[17];
        controllers[1].keyY.press      = inputs[18];
        controllers[1].keyZ.press      = inputs[19];
        controllers[1].keyStart.press  = inputs[20];
        controllers[1].keySelect.press = inputs[21];

        if (mirror)
        {
            bool buffer = controllers[1].keyLeft.press;
            controllers[1].keyLeft.press = controllers[1].keyRight.press;
            controllers[1].keyRight.press = buffer;
        }

        // TODO: Not sure what this does, but from what it looks,
        //  it may only affect v4 and v3
        //sub_140101BC0(21);
    }

    // Intentionally fail if id is 0
    if (deviceID == 0)
        return nullptr;
    return inputs;
}

HOOK(void, __fastcall, ActClear_Create, SigActClear_Create(), EntityActClear* self)
{
    originalActClear_Create(self);

    self->coolBonus = 0;
    self->timeBonus = 100;
    switch (sceneInfo->minutes)
    {
    case 0:
        self->timeBonus = 50000;
        break;
    case 1:
        self->timeBonus = sceneInfo->seconds < 30 ? 10000 : 5000;
        break;
    case 2:
        self->timeBonus = sceneInfo->seconds < 30 ? 4000 : 3000;
        break;
    case 3:
        self->timeBonus = sceneInfo->seconds < 30 ? 1000 : 100;
        break;
    case 9:
        if (!sceneInfo->debugMode &&
            globals->gameMode < MODE_TIMEATTACK &&
            sceneInfo->seconds == 59)
        {
            if (!(globals->medalMods & 0x20))
                self->timeBonus = 100000;
        }
        break;
    default:
        break;
    }
}

HOOK(int, __fastcall, sub_140302180, Sigsub_140302180(), int index)
{
    originalsub_140302180(index);

    char* globals_ptr = *(char**)0x144000210;
    bool hasPlus = *(bool32*)(globals_ptr + 0x4C350C);
    bool isAnniversary = *(bool32*)(globals_ptr + 0x4C3510);
    auto vec = (VectorInt*)0x143FB9F88;
    
    if (hasPlus && isAnniversary)
    {
        vec->end = vec->start + 4;
        vec->start[0] = 0;
        vec->start[1] = 1;
        vec->start[2] = 3;
        vec->start[3] = 2;
    }
    else
    {
        vec->end = vec->start + 3;
        vec->start[0] = 0;
        vec->start[1] = 1;
        vec->start[2] = 2;
    }

    return vec->start[index];
}

HOOK(void, __fastcall, S3K_CompElement_Draw, SigS3K_CompElement_Draw(), __int64 a1)
{
    char* globals_ptr = *(char**)0x144000210;
    bool* hasPlus = (bool*)(globals_ptr + 0x4C350C);
    bool* isAnniversary = (bool*)(globals_ptr + 0x4C3510);
    bool temp = *hasPlus;

    // Reuse hasPlus
    *hasPlus = (temp && *isAnniversary);
    originalS3K_CompElement_Draw(a1);
    *hasPlus = temp;
}

HOOK(void, __fastcall, S3K_CompElement_State_Carousel, SigS3K_CompElement_State_Carousel(), __int64 a1)
{
    char* globals_ptr = *(char**)0x144000210;
    bool* hasPlus = (bool*)(globals_ptr + 0x4C350C);
    bool* isAnniversary = (bool*)(globals_ptr + 0x4C3510);
    bool temp = *hasPlus;

    // Reuse hasPlus
    *hasPlus = (temp && *isAnniversary);
    originalS3K_CompElement_State_Carousel(a1);
    *hasPlus = temp;
}

HOOK(void, __fastcall, S3K_CompElement_Create, SigS3K_CompElement_Create(), __int64 a1)
{
    char* globals_ptr = *(char**)0x144000210;
    bool* hasPlus = (bool*)(globals_ptr + 0x4C350C);
    bool* isAnniversary = (bool*)(globals_ptr + 0x4C3510);
    bool temp = *hasPlus;

    // Reuse hasPlus
    *hasPlus = (temp && *isAnniversary);
    originalS3K_CompElement_Create(a1);
    *hasPlus = temp;
}

HOOK(void, __fastcall, LevelSelect_State_Navigate, SigLevelSelect_State_Navigate(), __int64 a1)
{
    char* globals_ptr = *(char**)0x144000210;
    bool* hasPlus = (bool*)(globals_ptr + 0x4C350C);
    bool* isAnniversary = (bool*)(globals_ptr + 0x4C3510);
    bool temp = *hasPlus;

    // Reuse hasPlus
    *hasPlus = (temp && *isAnniversary);
    originalLevelSelect_State_Navigate(a1);
    *hasPlus = temp;
}


HOOK(void, __fastcall, Player_State_HammerDash, SigPlayer_State_HammerDash(), EntityPlayer* self)
{
    originalPlayer_State_HammerDash(self);
    if (self->onGround)
    {
        ((void(__fastcall*)(EntityPlayer*))(SigPlayer_HandleGroundRotation()))(self);
    }
}

HOOK(void, __fastcall, Player_StageLoad, SigPlayer_StageLoad(), EntityPlayer* self)
{
    
    auto globals = *(GlobalVariables**)0x144000210;
    // Disable barrel hotline
    globals->secrets &= ~SECRET_BARRELHOTLINE;

    // Enable barrel hotline
    if (!globals->playMode)
        globals->secrets |= SECRET_BARRELHOTLINE;
    
    originalPlayer_StageLoad(self);
}

HOOK(void, __fastcall, LinkGameLogicDLL, SigLinkGameLogicDLL(), void* info)
{
    originalLinkGameLogicDLL(info);

    RSDK = *(FunctionTable**)0x142E70150;
}

HOOK(void, __fastcall, NotifyCallback, SigNotifyCallback(), NotifyCallbackInfo* callbackInfo)
{
    switch (callbackInfo->callback)
    {
    case CALLBACK_COPYPALETTE:
    {
        auto legacyPalette = (uint16*)0x14292EF70;
        memcpy(&legacyPalette[callbackInfo->param2], &legacyPalette[callbackInfo->param1], callbackInfo->param3 * sizeof(uint16));
    }
    break;
    default:
        originalNotifyCallback(callbackInfo);
        break;
    }
}

extern "C" __declspec(dllexport) void PostInit()
{
    // Install hooks
    INSTALL_HOOK(Player_StaticLoad);
    INSTALL_HOOK(Player_State_KnuxGlideLeft);
    INSTALL_HOOK(sub_1401EA5E0); 
    INSTALL_HOOK(sub_1403A2550);
    INSTALL_HOOK(ActClear_Create);
    INSTALL_HOOK(sub_140302180);
    INSTALL_HOOK(S3K_CompElement_Draw);
    INSTALL_HOOK(S3K_CompElement_State_Carousel);
    INSTALL_HOOK(S3K_CompElement_Create);
    INSTALL_HOOK(LevelSelect_State_Navigate);
    INSTALL_HOOK(Player_State_HammerDash);
    INSTALL_HOOK(NotifyCallback);
    INSTALL_HOOK(Player_StageLoad);
    //INSTALL_HOOK(Player_State_Roll);
    //INSTALL_HOOK(LinkGameLogicDLL);

    WRITE_MEMORY(0x1400ADD3B, 0x90, 0x90);


    // Fix SpecialClear
    for (int i = 0; i < 2; ++i)
        WRITE_MEMORY(((intptr_t)SigSpecialClear_State_FigureOutWhatToDoNext_D0() + 14 * i), 0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90, 0x90);
    // Fix Amy's jumpOffset
    WRITE_MEMORY(((char*)SigPlayer_Create_266() + 8), 0x04);
    // Change the screenshake to only work on Y for the Drop Dash
    WRITE_MEMORY(((char*)SigPlayer_State_DropDash() + 0xA6), 0x41, 0xB8, 0x06, 0x00, 0x00, 0x00, 0x31, 0xD2, 0xC7, 0x44, 0x24, 0x20, 0x01, 0x00, 0x00, 0x00, 0x45, 0x8D, 0x48, 0xFB);

}

extern "C" __declspec(dllexport) void Init(ModInfo* modInfo)
{
    // Scan signatures
    SigPlayer_State_KnuxGlideLeft();
    Sigsub_1401EA5E0();
    SigCamera_ShakeScreen();
    Sigsub_1403A2550();
    SigIsMirrorMode();
    SigSpecialClear_State_FigureOutWhatToDoNext_D0();
    SigPlayer_Create_266();
    SigActClear_Create();
    Sigsub_140302180();
    SigS3K_CompElement_Draw();
    SigS3K_CompElement_State_Carousel();
    SigS3K_CompElement_Create();
    SigLevelSelect_State_Navigate();
    SigPlayer_State_HammerDash();
    SigPlayer_State_Roll();
    SigPlayer_State_Air();
    SigLinkGameLogicDLL();
    SigPlayer_StaticLoad();
    SigShield_State_Insta();
    SigPlayer_State_DropDash();
    SigPlayer_HandleGroundRotation();
    SigNotifyCallback();
    SigCopyPalette();
    SigPlayer_StageLoad();

    // Check signatures
    if (!SigValid)
    {
        MessageBoxA(nullptr, InvalidSig, "", NULL);
        MessageBoxW(nullptr, L"Signature Scan Failed!\n\nThis usually means there is a conflict or the mod is running on an incompatible game version.", L"Scan Error", MB_ICONERROR);
        return;
    }
}