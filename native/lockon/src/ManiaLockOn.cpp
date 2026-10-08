// Mania Lock-On (working title): a HiteModLoader DLL for Sonic Origins that adds a SONIC MANIA button to the main
// menu (the Museum / My Data / Options island). Picking it starts the player's own Windows build of the Sonic Mania
// decompilation (RSDKv5U.exe + Game.dll), minimises Origins while it runs and brings it back when it exits.
//
// It stands alone: NoSwap isn't needed (until 2026-10-01 the button was part of NoSwap's S3&K DLL). With NoSwap
// installed both work side by side: NoSwap's menu archives already carry the button's layout and text, and Lock-On
// uses them (MenuFiles.h); NoSwap hooks none of the functions below.
//
// Configuration: HedgeModManager's Configure (ConfigSchema.json -> ManiaLockOn.ini [Main]: Enabled, Path). Every step
// is logged to ManiaLockOn.log in the mod's folder.

#include <windows.h>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwctype>
#include <string>
#include <vector>

#include "MinHook.h"

typedef uint8_t uint8;
typedef int32_t int32;
typedef uint32_t uint32;

// ---------------------------------------------------------------- mod loader interface
// HiteModLoader passes this to Init() (ModList is a pointer to a std::vector<Mod*>, kept opaque here).
struct Mod {
    const char* Name;
    const char* Path;
};
struct ModInfo {
    void* ModLoader;
    void* ModList;
    Mod* CurrentMod;
    int CurrentPlatform;
};

// ---------------------------------------------------------------- basics
static std::wstring Widen(const std::string& s) {
    wchar_t w[2048];
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, w, 2048);
    return w;
}
static std::string Narrow(const std::wstring& w) {
    char buf[2048];
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, buf, sizeof(buf), nullptr, nullptr);
    return buf;
}
static std::wstring NormW(std::wstring p) {
    for (auto& c : p) {
        if (c == L'/')
            c = L'\\';
        c = towlower(c);
    }
    return p;
}

// The folder this DLL was loaded from (the mod's folder), without a trailing backslash
static std::wstring OurFolder() {
    HMODULE self = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCWSTR)&OurFolder, &self);
    wchar_t path[MAX_PATH]{};
    GetModuleFileNameW(self, path, MAX_PATH);
    std::wstring s = path;
    return s.substr(0, s.find_last_of(L"\\/"));
}

static FILE* g_log = nullptr;
static void Log(const char* fmt, ...) {
    if (!g_log) {
        g_log = _wfopen((OurFolder() + L"\\ManiaLockOn.log").c_str(), L"w");
        if (!g_log)
            return;
    }
    va_list args;
    va_start(args, fmt);
    vfprintf(g_log, fmt, args);
    va_end(args);
    fputc('\n', g_log);
    fflush(g_log);
}

static std::string ReadAll(const std::wstring& path, bool& ok) {
    std::string out;
    ok = false;
    FILE* f = _wfopen(path.c_str(), L"rb");
    if (!f)
        return out;
    char buf[1 << 16];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0)
        out.append(buf, n);
    ok = !ferror(f);
    fclose(f);
    return out;
}

static bool Readable(const void* p, size_t size) {
    MEMORY_BASIC_INFORMATION mbi{};
    if (!p || !VirtualQuery(p, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT)
        return false;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
        return false;
    return (const char*)p + size <= (const char*)mbi.BaseAddress + mbi.RegionSize;
}

static bool PatchBytes(uintptr_t at, const void* bytes, size_t size) {
    DWORD old;
    if (!VirtualProtect((void*)at, size, PAGE_EXECUTE_READWRITE, &old))
        return false;
    memcpy((void*)at, bytes, size);
    VirtualProtect((void*)at, size, old, &old);
    FlushInstructionCache(GetCurrentProcess(), (void*)at, size);
    return true;
}

// A MinHook hook on the game's function at `at`, only when its first bytes are the game's own (`expect`): never on
// a different game build, nor on a function another mod has already hooked (its jump in the prologue)
static bool HookAt(uintptr_t at, const uint8* expect, size_t size, void* hook, void** original) {
    if (memcmp((void*)at, expect, size) != 0)
        return false;
    return MH_CreateHook((void*)at, hook, original) == MH_OK && MH_EnableHook((void*)at) == MH_OK;
}

// ---------------------------------------------------------------- the configuration
// HedgeModManager writes ManiaLockOn.ini (ConfigSchema.json "IniFile") as UTF-8: "[Main]", then Enabled=True / False
// and Path="..." (strings quoted, nothing escaped). Read here by hand: GetPrivateProfileString would read it as ANSI.
struct Config {
    bool enabled = true;
    std::string path;  // UTF-8
};
static Config g_config;
static std::string g_legacyPath, g_legacyIni;  // an older NoSwap's NoSwapS3K.ini [Mania] Path (FindLegacyPath)

static std::string Trim(std::string s) {
    while (!s.empty() && strchr(" \t\r\n", s.back()))
        s.pop_back();
    size_t i = 0;
    while (i < s.size() && strchr(" \t", s[i]))
        i++;
    s = s.substr(i);
    if (s.size() >= 2 && ((s[0] == '"' && s.back() == '"') || (s[0] == '\'' && s.back() == '\'')))
        s = s.substr(1, s.size() - 2);
    return s;
}
static std::string LowerA(std::string s) {
    for (auto& c : s)
        c = (char)tolower((unsigned char)c);
    return s;
}

static void ReadConfig() {
    std::wstring path = OurFolder() + L"\\ManiaLockOn.ini";
    bool ok;
    std::string text = ReadAll(path, ok);
    if (!ok) {
        Log("config: no ManiaLockOn.ini (not configured in HedgeModManager yet): Enabled, no Path");
        return;
    }
    if (text.rfind("\xEF\xBB\xBF", 0) == 0)
        text.erase(0, 3);
    std::string section;
    size_t at = 0;
    while (at < text.size()) {
        size_t eol = text.find('\n', at);
        std::string line = Trim(text.substr(at, eol == std::string::npos ? std::string::npos : eol - at));
        at = eol == std::string::npos ? text.size() : eol + 1;
        if (line.empty() || line[0] == ';' || line[0] == '#')
            continue;
        if (line[0] == '[') {
            section = LowerA(Trim(line.substr(1, line.find(']') - 1)));
            continue;
        }
        size_t eq = line.find('=');
        if (section != "main" || eq == std::string::npos)
            continue;
        std::string key = LowerA(Trim(line.substr(0, eq))), value = Trim(line.substr(eq + 1));
        if (key == "enabled") {
            std::string v = LowerA(value);
            g_config.enabled = !(v == "false" || v == "0" || v == "no" || v == "off");
        } else if (key == "path") {
            g_config.path = value;
        }
    }
    Log("config: Enabled=%s, Path=%s", g_config.enabled ? "true" : "false",
        g_config.path.empty() ? "(empty: found automatically)" : g_config.path.c_str());
}

// An older NoSwap set the button up in its own NoSwapS3K.ini ([Mania] Path). Used only while Lock-On's Path is
// empty, and never written back: in the enabled mods first, then in the mods folder next to ours.
static void FindLegacyPath(ModInfo* modInfo) {
    std::vector<std::wstring> folders;
    if (modInfo && modInfo->ModList && Readable(modInfo->ModList, 2 * sizeof(void*))) {
        Mod** begin = ((Mod***)modInfo->ModList)[0];
        Mod** end = ((Mod***)modInfo->ModList)[1];
        for (Mod** m = begin; m && m < end && m < begin + 256; m++)
            if (Readable(m, sizeof(Mod*)) && *m && Readable(*m, sizeof(Mod)) && (*m)->Path)
                folders.push_back(Widen((*m)->Path));
    }
    std::wstring parent = OurFolder();
    parent.resize(parent.find_last_of(L"\\/"));
    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW((parent + L"\\*").c_str(), &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do
            if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && fd.cFileName[0] != L'.')
                folders.push_back(parent + L"\\" + fd.cFileName);
        while (FindNextFileW(h, &fd));
        FindClose(h);
    }
    for (auto& f : folders) {
        std::wstring ini = f + L"\\NoSwapS3K.ini";
        if (GetFileAttributesW(ini.c_str()) == INVALID_FILE_ATTRIBUTES)
            continue;
        char value[1024]{};
        GetPrivateProfileStringA("Mania", "Path", "", value, sizeof(value), Narrow(ini).c_str());
        std::string v = Trim(value);
        if (!v.empty()) {
            g_legacyPath = v, g_legacyIni = Narrow(ini);
            return;
        }
    }
}

// An older NoSwapS3K.dll (before 2026-10-01) has its own SONIC MANIA button: its log text is in its image
static bool OldNoSwapLoaded() {
    HMODULE m = GetModuleHandleA("NoSwapS3K.dll");
    if (!m)
        return false;
    auto* dos = (IMAGE_DOS_HEADER*)m;
    auto* nt = (IMAGE_NT_HEADERS*)((uint8*)m + dos->e_lfanew);
    const uint8* base = (const uint8*)m;
    size_t size = nt->OptionalHeader.SizeOfImage;
    static const char needle[] = "mania launcher: SONIC MANIA button";
    for (size_t at = 0; at < size;) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (!VirtualQuery(base + at, &mbi, sizeof(mbi)))
            break;
        size_t regionEnd = (const uint8*)mbi.BaseAddress + mbi.RegionSize - base;
        if (regionEnd > size)
            regionEnd = size;
        if (mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) && regionEnd > at
            && regionEnd - at >= sizeof(needle) - 1) {
            for (size_t i = at; i + sizeof(needle) - 1 <= regionEnd; i++)
                if (base[i] == 'm' && memcmp(base + i, needle, sizeof(needle) - 1) == 0)
                    return true;
        }
        at = regionEnd > at ? regionEnd : at + 0x1000;
    }
    return false;
}

// ---------------------------------------------------------------- the game's menu helpers (Steam build 12197262)
typedef void* (*ResolveHandleFn)(void* handle);
typedef void (*PlayAnimFn)(void* cast, const char* name, int start);
typedef void* (*FindChildFn)(void* comp, const char* cast, const char* child);
typedef void (*SetTextKeyFn)(void* textCast, const char* key);
typedef void* (*GetComponentFn)(void* object, void* cls);
typedef void (*PlaySfxFn)(uint32* out, void* window, int sound);
typedef void* (*CastClassFn)(void* cast);
static const ResolveHandleFn ResolveHandle = (ResolveHandleFn)0x1405C6420;
static const PlayAnimFn PlayAnim = (PlayAnimFn)0x140481C20;
static const FindChildFn FindChild = (FindChildFn)0x14047F760;
static const SetTextKeyFn SetTextKey = (SetTextKeyFn)0x140483330;
static const GetComponentFn GetComponent = (GetComponentFn)0x1405C6FD0;
static const PlaySfxFn PlaySfx = (PlaySfxFn)0x140454170;
static void* const LAYOUT_COMPONENT = (void*)0x142882E30;
static void* const TEXT_CAST_CLASS = (void*)0x142882E78;

#include "MenuFiles.h"  // the menu archives with the button's patterns and text
#include "Launcher.h"   // the button itself

// ---------------------------------------------------------------- entry points
static bool g_active = false;

BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }

// For other mods (a later NoSwap, say): 1 when the SONIC MANIA button went in
extern "C" __declspec(dllexport) int ManiaLockOn_ButtonActive() { return g_active ? 1 : 0; }

extern "C" __declspec(dllexport) void Init(ModInfo* modInfo) {
    Log("Mania Lock-On loaded (mod folder: %s)", Narrow(OurFolder()).c_str());
    // (a named object other mods can look for: Lock-On is in this process)
    CreateMutexW(nullptr, FALSE, (L"Local\\ManiaLockOn." + std::to_wstring(GetCurrentProcessId())).c_str());
    ReadConfig();
    FindLegacyPath(modInfo);
    menu_files::SetMods(modInfo);
    if (OldNoSwapLoaded()) {
        Log("an older NoSwap (with its own SONIC MANIA button) is loaded: Lock-On stands down and leaves the button to "
            "it. Update NoSwap to have Lock-On's button (its settings, its Path)");
    } else {
        g_active = mania_launcher::SetUp();
    }
    if (!menu_files::Synced())  // (the button is off: only tidy Lock-On's own menu copies, never make new ones)
        menu_files::Sync(false, nullptr);
}
