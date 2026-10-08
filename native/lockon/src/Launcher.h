// The SONIC MANIA button in Origins' main menu: it starts the Windows build of the Sonic Mania decompilation (the
// player's own copy), minimises Origins while it runs and restores it when it exits. Included by ManiaLockOn.cpp after
// the menu helpers (ResolveHandle, PlayAnim, FindChild, SetTextKey, GetComponent, PlaySfx, HookAt, Log, the config ...)
// and MenuFiles.h (the menu archives with the button's patterns and text). Until 2026-10-01 this was part of NoSwap's
// S3&K DLL (native/src/ManiaLauncher.h).
//
// The main menu (research: the main menu's island object m; the game build these addresses are for: Steam 12197262):
// - m+0x250 the menu variant (0: the normal one), m+0x25C the island (5: Museum / My Data / Options / DLC), m+0x278
//   the island scene's layer "lay", m+0x2E0 the handle of its button list (ui::MenuItemContainer: +0x2EC the cursor,
//   +0x2F8 the button count).
// - Island 5's buttons are the table at 0x140D59618, 4 bytes each {flag, kind, sub, sub}: Museum (8), My Data (9),
//   Options (10), two EMPTY slots, DLC (11). The button goes in the first empty slot (index 3, cast obj_btn_l_4) with
//   kind 12 (Game Gear's: a plain small button, PRM_sub, nothing special in the build or highlight code). Kind 12 is
//   shown only with the Game Gear DLC (BuildItems 0x1403E828C), so it is enabled again after every build.
// - Its label: SetItemLabel (0x1403E8BB0) gives it Game Gear's; Hook_SetItemLabel then sets MAINMENU_island_mania.
// - Its description: "MAINMENU_text_" + island 5's string slot 0x12 (0x140D594E0, "" in the game: kind 12's slot,
//   unused on island 5) -> pointed at "mania" (MAINMENU_text_mania).
// - Its layout (tools/build_origins_menu.py LAUNCHER_LAYOUT, in NoSwap's archives and in Lock-On's own,
//   tools/build_lockon_menu.py): the game plays PRM_btn_museum (4th button hidden); after
//   the build Hook_BuildItems plays PRM_btn_museum_mania, or PRM_btn_museum_mania_dlc when the DLC button shows (no
//   Origins Plus: GetItemKind(5, 5) isn't 0xFF), which tightens the column so the 4th button fits above DLC.
// - Picking it: OnDecide (0x1403E8840) on island 5, cursor 3 -> Launch() instead of the game's (which would hand an
//   unknown kind to the main menu sequence and hang it).
// - The table entry is written before every build (Hook_BuildItems): the button, or the game's empty slot when the
//   menu archives the game actually opened don't carry the button's patterns (MenuFiles.h Ready()).
// - While Mania runs every input query of the game's input manager (0x1403DD4D0 axis, 0x1403DD650 / 6C0 / 730 / 7A0
//   button states) answers "nothing", so the menu ignores the pad (XInput reaches a minimised window too). Released
//   half a second after Mania exits (the button that quit it isn't read as a press).
//
// Where the decomp is (FindMania, every step logged in ManiaLockOn.log):
// 1. the mod's configuration (HedgeModManager's Configure: ManiaLockOn.ini [Main] Path=, its folder or its exe; a
//    Windows path, or a Unix one under Wine/Proton);
// 2. if that's empty: an older NoSwap's NoSwapS3K.ini [Mania] Path= (where the button used to be set up);
// 3. Steam's libraries: under Wine/Proton, from Proton's environment (STEAM_COMPAT_CLIENT_INSTALL_PATH,
//    STEAM_COMPAT_LIBRARY_PATHS, STEAM_COMPAT_INSTALL_PATH) and the usual Linux Steam folders under $HOME, each Unix
//    path turned into a Windows one by Wine's wine_get_dos_file_name (else "Z:" + the path); on Windows, the registry's
//    Steam folder. Each library's steamapps/libraryfolders.vdf adds the others; the one with appmanifest_584400.acf
//    (Sonic Mania) has the game in steamapps/common/<its installdir>.
// A folder counts only with a decomp exe (RSDKv5U.exe or RSDKv5.exe, never Steam's SonicMania.exe), its game logic
// (Settings.ini [Game] gameLogic, default Game, + .dll) and Data.rsdk (or a Data folder). Not found (or the config's
// Enabled off, or menu archives without the button's patterns, or a different game build): no button at all, the
// island is the game's.
#pragma once

#include <cwctype>

namespace mania_launcher {

// ---------------------------------------------------------------- the game
constexpr uintptr_t ITEM_SLOT = 0x140D59624;    // island 5's button 3 {flag, kind, sub, sub}
constexpr uintptr_t TEXT_SLOT = 0x140D594E0;    // island 5's description string slot 0x12 (a char*)
constexpr uintptr_t EMPTY_TEXT = 0x140AAE2E0;   // what it points at in the game ("")
constexpr uintptr_t BUILD_ITEMS = 0x1403E8050, SET_ITEM_LABEL = 0x1403E8BB0, ON_DECIDE = 0x1403E8840;
constexpr uintptr_t GET_ITEM_KIND = 0x1403E6CA0, ENABLE_ITEM = 0x1403C0170;
constexpr uintptr_t INPUT_AXIS = 0x1403DD4D0;
constexpr uintptr_t INPUT_BITS[] = {0x1403DD650, 0x1403DD6C0, 0x1403DD730, 0x1403DD7A0};
constexpr uint8 ISLAND = 5, BUTTON = 3, HOST_KIND = 12, DLC_BUTTON = 5, NO_KIND = 0xFF;
static const char* const LABEL_KEY = "MAINMENU_island_mania";
static const char* const PATTERN = "PRM_btn_museum_mania";
static const char* const PATTERN_DLC = "PRM_btn_museum_mania_dlc";
static char g_textSlot[] = "mania";  // -> MAINMENU_text_mania (the game keeps the pointer: static)

typedef void (*BuildItemsFn)(void* menu, uint8 island, uint32 cursor);
typedef void (*SetItemLabelFn)(void* menu, uint8 kind, uint32 index);
typedef void (*OnDecideFn)(void* menu, uint8 playSound);
typedef uint8 (*GetItemKindFn)(void* menu, uint8 island, uint32 index);
typedef void (*EnableItemFn)(void* container, uint32 index, bool enable);
typedef bool (*InputBitFn)(void* input, uint32 action, int32 player);
typedef float (*InputAxisFn)(void* input, uint32 action, int32 player);
static const GetItemKindFn GetItemKind = (GetItemKindFn)GET_ITEM_KIND;
static const EnableItemFn EnableItem = (EnableItemFn)ENABLE_ITEM;

static BuildItemsFn g_buildItems = nullptr;
static SetItemLabelFn g_setItemLabel = nullptr;
static OnDecideFn g_onDecide = nullptr;
static InputBitFn g_inputBit[4] = {};
static InputAxisFn g_inputAxis = nullptr;

// ---------------------------------------------------------------- state
static std::wstring g_folder, g_exe;           // the decomp (FindMania)
static volatile LONG g_blockInput = 0;         // 1 while Mania runs (and half a second after)
static HANDLE g_process = nullptr;             // Mania, while it runs (the watcher closes it)
static DWORD g_processId = 0;
static CRITICAL_SECTION g_lock;
static std::vector<HWND> g_minimised;          // Origins' windows we minimised

static uint8 Island(void* m) { return *((uint8*)m + 0x25C); }
static uint8 Variant(void* m) { return *((uint8*)m + 0x250); }
static void* Container(void* m) { return ResolveHandle((uint8*)m + 0x2E0); }
static bool IsOurIsland(void* m) { return Variant(m) == 0 && Island(m) == ISLAND; }

// ---------------------------------------------------------------- finding the decomp
static bool Exists(const std::wstring& p) { return GetFileAttributesW(p.c_str()) != INVALID_FILE_ATTRIBUTES; }
static bool IsDir(const std::wstring& p) {
    DWORD a = GetFileAttributesW(p.c_str());
    return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_DIRECTORY);
}
static std::wstring Trimmed(std::wstring s) {
    while (!s.empty() && (s.back() == L'\\' || s.back() == L'/' || s.back() == L' ' || s.back() == L'"'))
        s.pop_back();
    while (!s.empty() && (s[0] == L' ' || s[0] == L'"'))
        s.erase(0, 1);
    return s;
}
static std::wstring Lower(std::wstring s) {
    for (auto& c : s)
        c = (wchar_t)towlower(c);
    return s;
}
static std::string ReadText(const std::wstring& path) {
    HANDLE h = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, 0,
                           nullptr);
    if (h == INVALID_HANDLE_VALUE)
        return "";
    std::string out;
    char buf[8192];
    DWORD got;
    while (ReadFile(h, buf, sizeof(buf), &got, nullptr) && got && out.size() < (4u << 20))
        out.append(buf, got);
    CloseHandle(h);
    return out;
}

static bool OnWine() {
    static int wine = -1;
    if (wine < 0)
        wine = GetProcAddress(GetModuleHandleA("ntdll.dll"), "wine_get_version") != nullptr;
    return wine == 1;
}

// A Unix path ("/home/...") as Windows sees it under Wine: wine_get_dos_file_name, else Z: (Wine's / drive)
static std::wstring FromUnix(const std::string& unixPath) {
    typedef WCHAR*(CDECL * DosNameFn)(const char*);
    static DosNameFn dosName = (DosNameFn)GetProcAddress(GetModuleHandleA("kernel32.dll"), "wine_get_dos_file_name");
    if (dosName) {
        if (WCHAR* w = dosName(unixPath.c_str())) {
            std::wstring out = w;
            HeapFree(GetProcessHeap(), 0, w);
            return out;
        }
    }
    std::wstring out = L"Z:" + Widen(unixPath);
    for (auto& c : out)
        if (c == L'/')
            c = L'\\';
    return out;
}

// A path from a setting or a Steam file: a Unix one (starts with '/') converted under Wine; '/' -> '\'
static std::wstring AsWindowsPath(const std::string& p) {
    if (OnWine() && !p.empty() && p[0] == '/')
        return FromUnix(p);
    std::wstring w = Widen(p);
    for (auto& c : w)
        if (c == L'/')
            c = L'\\';
    return w;
}

static std::string Env(const char* name) {
    char buf[4096];
    DWORD n = GetEnvironmentVariableA(name, buf, sizeof(buf));
    return n && n < sizeof(buf) ? std::string(buf, n) : std::string();
}

// Every quoted value of `key` in a Valve KeyValues file (libraryfolders.vdf "path", an .acf's "installdir"), unescaped
static std::vector<std::string> VdfValues(const std::string& text, const std::string& key) {
    std::vector<std::string> out;
    std::string quoted = "\"" + key + "\"";
    for (size_t at = text.find(quoted); at != std::string::npos; at = text.find(quoted, at + 1)) {
        size_t open = text.find('"', at + quoted.size());
        size_t eol = text.find('\n', at);
        if (open == std::string::npos || (eol != std::string::npos && open > eol))
            continue;
        std::string v;
        size_t i = open + 1;
        for (; i < text.size() && text[i] != '"'; i++) {
            if (text[i] == '\\' && i + 1 < text.size())
                i++;
            v += text[i];
        }
        if (i < text.size())
            out.push_back(v);
    }
    return out;
}

// The decomp's game logic DLL name (Settings.ini [Game] gameLogic, default "Game"), with ".dll"
static std::wstring LogicDll(const std::wstring& folder) {
    wchar_t buf[260];
    GetPrivateProfileStringW(L"Game", L"gameLogic", L"Game", buf, 260, (folder + L"\\Settings.ini").c_str());
    std::wstring name = Trimmed(buf);
    if (name.empty())
        name = L"Game";
    if (Lower(name).size() < 4 || Lower(name).substr(Lower(name).size() - 4) != L".dll")
        name += L".dll";
    return name;
}

// `folder` holds a Windows decomp build: -> its exe in g_exe-to-be (`exe`), or why not
static bool IsDecompFolder(const std::wstring& folder, std::wstring& exe, std::string& why) {
    if (!IsDir(folder))
        return why = "no such folder", false;
    exe.clear();
    for (const wchar_t* name : {L"RSDKv5U.exe", L"RSDKv5.exe"})
        if (Exists(folder + L"\\" + name)) {
            exe = folder + L"\\" + name;
            break;
        }
    if (exe.empty())
        return why = Exists(folder + L"\\SonicMania.exe")
                         ? "only Steam's SonicMania.exe there (not the decompilation: RSDKv5U.exe is needed)"
                         : "no RSDKv5U.exe / RSDKv5.exe",
               false;
    std::wstring logic = LogicDll(folder);
    if (!Exists(folder + L"\\" + logic))
        return why = "no " + Narrow(logic) + " (the decompilation's game logic)", false;
    if (!Exists(folder + L"\\Data.rsdk") && !IsDir(folder + L"\\Data"))
        return why = "no Data.rsdk", false;
    return true;
}

static bool TryFolder(const std::wstring& folder, const char* from) {
    std::wstring exe;
    std::string why;
    if (!IsDecompFolder(folder, exe, why)) {
        Log("mania launcher: %s: %s: %s", from, Narrow(folder).c_str(), why.c_str());
        return false;
    }
    g_folder = folder, g_exe = exe;
    Log("mania launcher: %s: found %s", from, Narrow(exe).c_str());
    return true;
}

// The Steam library folders to look in (Windows paths), each "<library>" (its steamapps inside)
static std::vector<std::wstring> SteamLibraries() {
    std::vector<std::wstring> roots, libraries;  // roots: Steam installs / libraries whose libraryfolders.vdf to read
    auto add = [](std::vector<std::wstring>& list, std::wstring p) {
        p = Trimmed(p);
        if (p.size() > 10 && Lower(p).substr(p.size() - 10) == L"\\steamapps")
            p.resize(p.size() - 10);  // (the library itself)
        if (p.empty())
            return;
        for (auto& q : list)
            if (Lower(q) == Lower(p))
                return;
        list.push_back(p);
    };
    if (OnWine()) {
        std::string client = Env("STEAM_COMPAT_CLIENT_INSTALL_PATH");
        if (!client.empty())
            add(roots, FromUnix(client));
        std::string libs = Env("STEAM_COMPAT_LIBRARY_PATHS");
        for (size_t at = 0; at <= libs.size();) {
            size_t end = libs.find(':', at);
            if (end == std::string::npos)
                end = libs.size();
            if (end > at)
                add(roots, FromUnix(libs.substr(at, end - at)));
            at = end + 1;
        }
        std::string install = Env("STEAM_COMPAT_INSTALL_PATH");  // (<library>/steamapps/common/<Origins>)
        size_t cut = install.rfind("/steamapps/");
        if (cut != std::string::npos)
            add(roots, FromUnix(install.substr(0, cut)));
        std::string home = Env("HOME");
        if (home.empty()) {
            std::string wineHome = Env("WINEHOMEDIR");  // ("\??\Z:\home\me": a Windows path already)
            if (wineHome.rfind("\\??\\", 0) == 0)
                wineHome = wineHome.substr(4);
            if (!wineHome.empty())
                for (const char* sub : {"\\.local\\share\\Steam", "\\.steam\\steam", "\\.steam\\root",
                                        "\\.var\\app\\com.valvesoftware.Steam\\.local\\share\\Steam"})
                    add(roots, Widen(wineHome + sub));
        } else {
            for (const char* sub : {"/.local/share/Steam", "/.steam/steam", "/.steam/root",
                                    "/.var/app/com.valvesoftware.Steam/.local/share/Steam"})
                add(roots, FromUnix(home + sub));
        }
    }
    for (HKEY hive : {HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE}) {
        for (auto [key, value] : {std::pair<const wchar_t*, const wchar_t*>{L"Software\\Valve\\Steam", L"SteamPath"},
                                  {L"Software\\WOW6432Node\\Valve\\Steam", L"InstallPath"},
                                  {L"Software\\Valve\\Steam", L"InstallPath"}}) {
            wchar_t buf[MAX_PATH];
            DWORD size = sizeof(buf);
            if (RegGetValueW(hive, key, value, RRF_RT_REG_SZ, nullptr, buf, &size) == ERROR_SUCCESS) {
                std::wstring p = buf;
                for (auto& c : p)
                    if (c == L'/')
                        c = L'\\';
                add(roots, p);
            }
        }
    }
    for (auto& root : roots) {
        add(libraries, root);
        std::string vdf = ReadText(root + L"\\steamapps\\libraryfolders.vdf");
        auto paths = VdfValues(vdf, "path");
        Log("mania launcher: Steam folder %s: %s", Narrow(root).c_str(),
            vdf.empty() ? "no steamapps\\libraryfolders.vdf" : (std::to_string(paths.size()) + " libraries listed").c_str());
        for (auto& p : paths)
            add(libraries, AsWindowsPath(p));
    }
    return libraries;
}

// A path from a setting (`from`: where it came from, for the log): the decomp's folder or its exe
static bool TrySetting(const std::string& setting, const char* from) {
    std::wstring path = Trimmed(AsWindowsPath(setting));
    if (path.empty())
        return false;
    if (Lower(path).size() > 4 && Lower(path).substr(path.size() - 4) == L".exe") {
        size_t slash = path.find_last_of(L"\\/");
        std::wstring name = Lower(slash == std::wstring::npos ? path : path.substr(slash + 1));
        if (name == L"sonicmania.exe")
            Log("mania launcher: %s is Steam's SonicMania.exe, not the decompilation: using its folder", from);
        else if (Exists(path) && slash != std::wstring::npos) {
            std::wstring exe;
            std::string why;
            if (IsDecompFolder(path.substr(0, slash), exe, why) || why.rfind("no RSDKv5", 0) == 0) {
                g_folder = path.substr(0, slash), g_exe = path;
                Log("mania launcher: %s: using %s", from, Narrow(path).c_str());
                return true;
            }
            Log("mania launcher: %s: %s: %s", from, Narrow(path).c_str(), why.c_str());
        }
        if (slash != std::wstring::npos)
            path = path.substr(0, slash);
    }
    return TryFolder(path, from);
}

static bool FindMania() {
    // 1. the configuration; 2. an older NoSwap's [Mania] Path, only while the configuration has none
    if (!g_config.path.empty()) {
        if (TrySetting(g_config.path, "the configured Path"))
            return true;
    } else if (!g_legacyPath.empty()) {
        Log("mania launcher: no Path configured: trying NoSwap's old setting (%s [Mania] Path)", g_legacyIni.c_str());
        if (TrySetting(g_legacyPath, "NoSwapS3K.ini [Mania] Path"))
            return true;
    } else {
        Log("mania launcher: no Path configured: looking in Steam's libraries%s", OnWine() ? " (Wine/Proton)" : "");
    }
    // 3. Steam's libraries
    for (auto& lib : SteamLibraries()) {
        std::wstring apps = lib + L"\\steamapps";
        std::string acf = ReadText(apps + L"\\appmanifest_584400.acf");
        if (acf.empty())
            continue;
        auto dirs = VdfValues(acf, "installdir");
        std::wstring folder = apps + L"\\common\\" + (dirs.empty() ? L"Sonic Mania" : Widen(dirs[0]));
        if (TryFolder(folder, "Steam's Sonic Mania"))
            return true;
    }
    Log("mania launcher: the Sonic Mania decompilation wasn't found: no SONIC MANIA button. Put its Windows build "
        "(RSDKv5U.exe, Game.dll) in the Sonic Mania folder, or set its folder in HedgeModManager (Mania Lock-On, "
        "Configure: Path)");
    return false;
}

// ---------------------------------------------------------------- launching
struct WindowSearch {
    DWORD pid;
    std::vector<HWND> found;
};
static BOOL CALLBACK CollectWindow(HWND w, LPARAM arg) {
    auto* s = (WindowSearch*)arg;
    DWORD pid = 0;
    GetWindowThreadProcessId(w, &pid);
    if (pid == s->pid && IsWindowVisible(w) && !GetWindow(w, GW_OWNER))
        s->found.push_back(w);
    return TRUE;
}
static std::vector<HWND> TopWindows(DWORD pid) {
    WindowSearch s{pid, {}};
    EnumWindows(CollectWindow, (LPARAM)&s);
    return s.found;
}

static DWORD WINAPI Watch(LPVOID) {
    HANDLE process = g_process;
    WaitForInputIdle(process, 5000);  // (Mania's window up before ours goes: no desktop flash in between)
    std::vector<HWND> mine = TopWindows(GetCurrentProcessId());
    for (HWND w : mine)
        ShowWindowAsync(w, SW_MINIMIZE);
    EnterCriticalSection(&g_lock);
    g_minimised = mine;
    LeaveCriticalSection(&g_lock);
    Log("mania launcher: Origins minimised (%d windows); waiting for Sonic Mania to exit", (int)mine.size());
    WaitForSingleObject(process, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(process, &code);
    Log("mania launcher: Sonic Mania exited (code %lu): restoring Origins", (unsigned long)code);
    EnterCriticalSection(&g_lock);
    mine = g_minimised;
    g_minimised.clear();
    g_process = nullptr, g_processId = 0;
    LeaveCriticalSection(&g_lock);
    CloseHandle(process);
    for (HWND w : mine)
        if (IsWindow(w))
            ShowWindowAsync(w, SW_RESTORE);
    if (!mine.empty() && IsWindow(mine[0]))
        SetForegroundWindow(mine[0]);
    Sleep(500);  // (the button that quit Mania, still down, isn't a press in the menu)
    InterlockedExchange(&g_blockInput, 0);
    return 0;
}

static void Launch(void* menu) {
    uint32 sound[4]{};
    EnterCriticalSection(&g_lock);
    DWORD running = g_process ? g_processId : 0;
    LeaveCriticalSection(&g_lock);
    if (running) {  // (already running: show it)
        std::vector<HWND> wins = TopWindows(running);
        if (!wins.empty())
            SetForegroundWindow(wins[0]);
        Log("mania launcher: Sonic Mania is already running: brought to the front");
        return;
    }
    std::wstring cmd = L"\"" + g_exe + L"\"";
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(g_exe.c_str(), &cmd[0], nullptr, nullptr, FALSE, 0, nullptr, g_folder.c_str(), &si, &pi)) {
        Log("mania launcher: starting %s failed (error %lu)", Narrow(g_exe).c_str(), (unsigned long)GetLastError());
        PlaySfx(sound, menu, 2);  // (cancel)
        return;
    }
    Log("mania launcher: started %s (process %lu, in %s)", Narrow(g_exe).c_str(), (unsigned long)pi.dwProcessId,
        Narrow(g_folder).c_str());
    PlaySfx(sound, menu, 1);  // (OK)
    CloseHandle(pi.hThread);
    InterlockedExchange(&g_blockInput, 1);
    EnterCriticalSection(&g_lock);
    g_process = pi.hProcess, g_processId = pi.dwProcessId;
    LeaveCriticalSection(&g_lock);
    if (HANDLE t = CreateThread(nullptr, 0, Watch, nullptr, 0, nullptr))
        CloseHandle(t);
}

// ---------------------------------------------------------------- the hooks
static const uint8 ITEM_BUTTON[] = {0x01, HOST_KIND, 0xFF, 0xFF}, ITEM_EMPTY[] = {0x00, 0xFF, 0xFF, 0xFF};
static int g_itemShown = -1;  // what the table slot holds (1 the button, 0 the game's empty slot, -1 not written yet)

// The table slot: the button only while the menu archives the game opened carry its patterns (MenuFiles.h)
static void WriteItemSlot() {
    int want = menu_files::Ready() ? 1 : 0;
    if (want == g_itemShown)
        return;
    if (!PatchBytes(ITEM_SLOT, want ? ITEM_BUTTON : ITEM_EMPTY, 4)) {
        Log("mania launcher: patching island 5's table failed");
        return;
    }
    if (g_itemShown == 1 || !want)
        Log("mania launcher: %s", want ? "SONIC MANIA button back" : menu_files::WhyNotReady().c_str());
    g_itemShown = want;
}

static void Hook_BuildItems(void* menu, uint8 island, uint32 cursor) {
    WriteItemSlot();
    g_buildItems(menu, island, cursor);
    if (island != ISLAND || !IsOurIsland(menu) || GetItemKind(menu, ISLAND, BUTTON) != HOST_KIND)
        return;
    void* container = Container(menu);
    if (container && *(uint64_t*)((uint8*)container + 0x2F8) > BUTTON)
        EnableItem(container, BUTTON, true);  // (kind 12 is hidden without the Game Gear DLC)
    bool dlc = GetItemKind(menu, ISLAND, DLC_BUTTON) != NO_KIND;
    if (void* lay = *(void**)((uint8*)menu + 0x278))
        PlayAnim(lay, dlc ? PATTERN_DLC : PATTERN, 0);
    static int logged = 0;
    if (logged++ < 4)
        Log("mania launcher: island 5 built: SONIC MANIA button shown (%s)", dlc ? "DLC button shown too" : "no DLC button");
}

static void Hook_SetItemLabel(void* menu, uint8 kind, uint32 index) {
    g_setItemLabel(menu, kind, index);
    if (kind != HOST_KIND || index != BUTTON || !IsOurIsland(menu))
        return;
    void* comp = GetComponent(menu, LAYOUT_COMPONENT);
    if (!comp)
        return;
    for (const char* child : {"sysf_btn_name", "sysf_btn_name_black"}) {
        void* cast = FindChild(comp, "obj_btn_l_4", child);
        if (!cast)
            continue;
        void* cls = (*(CastClassFn**)cast)[1](cast);
        while (cls && cls != TEXT_CAST_CLASS)
            cls = *(void**)cls;
        if (cls)
            SetTextKey(cast, LABEL_KEY);
    }
}

static void Hook_OnDecide(void* menu, uint8 playSound) {
    if (IsOurIsland(menu)) {
        void* container = Container(menu);
        if (container && *(int32*)((uint8*)container + 0x2EC) == BUTTON
            && GetItemKind(menu, ISLAND, BUTTON) == HOST_KIND) {
            if (g_itemShown == 1)
                Launch(menu);  // (instead of the game's: the menu stays as it is)
            return;  // (never the game's own for this slot: an unknown kind hangs the menu sequence)
        }
    }
    g_onDecide(menu, playSound);
}

template <int N>
static bool Hook_InputBit(void* input, uint32 action, int32 player) {
    return g_blockInput ? false : g_inputBit[N](input, action, player);
}
static float Hook_InputAxis(void* input, uint32 action, int32 player) {
    return g_blockInput ? 0.0f : g_inputAxis(input, action, player);
}

// -> true when the button went in
static bool SetUp() {
    InitializeCriticalSection(&g_lock);
    if (!g_config.enabled) {
        Log("mania launcher: off (Enabled is off in the configuration)");
        return false;
    }
    if (!FindMania())
        return false;
    // the game's code and data, as researched (a different build: no button)
    static const uint8 build[] = {0x40, 0x53, 0x55, 0x56, 0x57, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x83, 0xEC, 0x30,
                                  0x48, 0x8B, 0xB9, 0x78, 0x02, 0x00, 0x00};
    static const uint8 label[] = {0x48, 0x89, 0x5C, 0x24, 0x10, 0x48, 0x89, 0x6C, 0x24, 0x18, 0x48, 0x89, 0x74, 0x24,
                                  0x20, 0x57, 0x48, 0x81, 0xEC, 0xC0, 0x00, 0x00, 0x00};
    static const uint8 decide[] = {0x40, 0x53, 0x56, 0x41, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x48, 0x8B, 0xD9, 0x44, 0x0F,
                                   0xB6, 0xFA};
    static const uint8 kind[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24,
                                 0x18, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x80, 0xB9, 0x50, 0x02};
    static const uint8 enable[] = {0x48, 0x89, 0x5C, 0x24, 0x10, 0x48, 0x89, 0x6C, 0x24, 0x18, 0x48, 0x89, 0x7C, 0x24,
                                   0x20, 0x41, 0x56, 0x48, 0x83, 0xEC, 0x20, 0x44, 0x8B, 0xF2};
    static const uint8 input[] = {0x44, 0x8B, 0xD2, 0x4C, 0x3B, 0x91, 0x18, 0x10, 0x00, 0x00};
    static const uint8 itemsBefore[] = {0x01, 0x0A, 0xFF, 0xFF, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0xFF, 0xFF,
                                        0x01, 0x0B, 0xFF, 0xFF};  // (Options, the two empty slots, DLC)
    bool same = memcmp((void*)GET_ITEM_KIND, kind, sizeof(kind)) == 0
                && memcmp((void*)ENABLE_ITEM, enable, sizeof(enable)) == 0
                && memcmp((void*)(ITEM_SLOT - 4), itemsBefore, sizeof(itemsBefore)) == 0
                && *(uintptr_t*)TEXT_SLOT == EMPTY_TEXT;
    for (uintptr_t at : INPUT_BITS)
        same = same && memcmp((void*)at, input, sizeof(input)) == 0;
    same = same && memcmp((void*)INPUT_AXIS, input, sizeof(input)) == 0;
    if (!same) {
        Log("mania launcher: off (the main menu's code or tables aren't the researched build's, or another mod (an "
            "older NoSwap with its own SONIC MANIA button?) changed them first)");
        return false;
    }
    // the menu archives with the button's patterns and text (ours made from the game's, or NoSwap's)
    if (!menu_files::Sync(true, PATTERN_DLC))
        return false;
    MH_STATUS mh = MH_Initialize();
    if (mh != MH_OK && mh != MH_ERROR_ALREADY_INITIALIZED) {
        Log("mania launcher: off (MinHook failed to initialise)");
        return false;
    }
    // input first (nothing visible yet if a later step fails), then the button's hooks, then the table entry
    int ok = 0;
    for (int i = 0; i < 4; i++) {
        static void* const hooks[] = {(void*)Hook_InputBit<0>, (void*)Hook_InputBit<1>, (void*)Hook_InputBit<2>,
                                      (void*)Hook_InputBit<3>};
        ok += HookAt(INPUT_BITS[i], input, sizeof(input), hooks[i], (void**)&g_inputBit[i]);
    }
    ok += HookAt(INPUT_AXIS, input, sizeof(input), (void*)Hook_InputAxis, (void**)&g_inputAxis);
    ok += HookAt(BUILD_ITEMS, build, sizeof(build), (void*)Hook_BuildItems, (void**)&g_buildItems);
    ok += HookAt(SET_ITEM_LABEL, label, sizeof(label), (void*)Hook_SetItemLabel, (void**)&g_setItemLabel);
    ok += HookAt(ON_DECIDE, decide, sizeof(decide), (void*)Hook_OnDecide, (void**)&g_onDecide);
    if (ok != 8) {
        Log("mania launcher: only %d of 8 hooks went in: no button", ok);
        for (uintptr_t at : {BUILD_ITEMS, SET_ITEM_LABEL, ON_DECIDE})
            MH_DisableHook((void*)at);  // (the button's never appears; the input ones only act while Mania runs)
        return false;
    }
    menu_files::Watch();  // (which archives the game really opens: the button only with ours or NoSwap's)
    uintptr_t text = (uintptr_t)g_textSlot;
    if (!PatchBytes(TEXT_SLOT, &text, sizeof(text))) {
        Log("mania launcher: patching island 5's tables failed: no button");
        return false;
    }
    WriteItemSlot();
    if (g_itemShown != 1)
        return false;
    Log("mania launcher: SONIC MANIA button in island 5 (Museum / My Data / Options / DLC), slot %d", BUTTON + 1);
    return true;
}

}  // namespace mania_launcher
