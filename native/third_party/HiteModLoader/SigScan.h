#pragma once

extern bool SigValid;

// HE
extern void* SigRunCore();

// RSDK
extern void* SigEngine_LoadFile();
extern void* SigEngine_CloseFile();
extern void* SigEngine_CloseFile2();
extern void* SigEngine_HandleGameLoop();
extern void* SigNotifyCallback();

// Cri
extern void* SigCrifsiowin_CreateFile();
extern void* SigCriFsIoWin_Exists();
extern void* SigCriErr_Notify();

// Logging
extern void* SigPrint1();

// Data
extern void* SigDataHapticsv3();
extern void* SigDataHapticsv4();

extern void* SigCreateFile3();

extern void* Sigsub_140A2A988();