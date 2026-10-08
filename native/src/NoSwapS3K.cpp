// NoSwap for Sonic 3 & Knuckles (Sonic Origins): a HiteModLoader DLL.
//
// S3&K's game logic is native code in SonicOrigins.exe, so this DLL finds engine functions by byte
// signature and hooks them with MinHook.
//
// "Sonic in costume": the extra is Sonic as far as S3&K and Origins know (menus, saves, every native
// character check). This DLL swaps his art for the extra's (built by tools/build_s3k_art.py and
// build_s3k_hud.py; fixed file names, served from the extra's package), writes the extra's colours, and adds its
// moves (tools/abilities.py). Its colours and move numbers come from its package's noswap_character.json
// (ExtraData.h); only the kinds of move are compiled in. The extra is picked on the save screen (up/down on a
// slot), re-read at every stage load.
//
// Signatures and struct layouts come from thesupersonic16's DllMods (MIT), see native/fetch_deps.sh.

#include <windows.h>
#include <psapi.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <cstddef>
#include <string>
#include <vector>
#include <map>

#include "MinHook.h"
#include "../third_party/reference/Ultrafix3kFixes_Ultrafix3kFixes_Game.h"  // RSDK + S3&K structs
#include "ExtraData.h"  // each extra's colours and ability numbers, from its package (and extras_gen.h)
#include "Roster.h"     // the registry: each package key's permanent kind (roster.json)
#include "MenuCards.h"  // Origins' select cards: writing each character's into the menu archives' slots
#include "MenuCardFiles.h"  // (and into the archives on disk: in place in NoSwap's folder, or a cache copy)

// ---------------------------------------------------------------- mod loader interface
// HiteModLoader passes this to Init() (ModList is a pointer to a std::vector, kept opaque here).
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

// ---------------------------------------------------------------- logging
static FILE* g_log = nullptr;

// The folder this DLL was loaded from (the mod folder), without relying on the loader's structs
static std::string DllFolder() {
    HMODULE self = nullptr;
    GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCSTR)&DllFolder, &self);
    char path[MAX_PATH]{};
    GetModuleFileNameA(self, path, MAX_PATH);
    std::string s = path;
    return s.substr(0, s.find_last_of("\\/"));
}

// The same as a wide string, read with the wide API: GetModuleFileNameA gives the ANSI code page's bytes (or '?' for a
// character it lacks), which Widen (UTF-8) would garble, so a mod folder with a non-ASCII name lost its cache and cards
static std::wstring DllFolderW() {
    HMODULE self = nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                       (LPCWSTR)&DllFolderW, &self);
    std::wstring path(32768, L'\0');
    DWORD n = GetModuleFileNameW(self, &path[0], (DWORD)path.size());
    path.resize(n < path.size() ? n : 0);
    size_t slash = path.find_last_of(L"\\/");
    return slash == std::wstring::npos ? L"" : path.substr(0, slash);
}

// NoSwap's own folder in %LOCALAPPDATA% (created): the log and the cache go there when the mod folder can't be written
static std::wstring LocalNoSwapDir() {
    wchar_t buf[MAX_PATH * 2];
    DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH * 2);
    if (!n || n >= MAX_PATH * 2)
        return L"";
    std::wstring dir = std::wstring(buf) + L"\\NoSwap";
    CreateDirectoryW(dir.c_str(), nullptr);  // (already there: fine)
    return dir;
}

static std::wstring g_logPathW;  // where the log went ("" : nowhere)

static void Log(const char* fmt, ...) {
    if (!g_log) {
        static bool tried = false;  // (once: a folder that can't be written isn't asked again on every line)
        if (tried)
            return;
        tried = true;
        std::wstring path = DllFolderW() + L"\\NoSwapS3K.log";
        g_log = _wfopen(path.c_str(), L"w");
        if (!g_log) {  // a read-only mod folder: the log goes to %LOCALAPPDATA%\NoSwap instead
            std::wstring local = LocalNoSwapDir();
            path = local + L"\\NoSwapS3K.log";
            g_log = local.empty() ? nullptr : _wfopen(path.c_str(), L"w");
        }
        if (!g_log)
            return;
        g_logPathW = path;
    }
    va_list args;
    va_start(args, fmt);
    vfprintf(g_log, fmt, args);
    va_end(args);
    fputc('\n', g_log);
    fflush(g_log);
}

// ---------------------------------------------------------------- loud failures
// A failure the player would otherwise only see as empty cards or extras playing as Sonic: logged as "WARNING:" and
// shown once in a message box (startup's together at the end of Init; one more for a problem found while playing). The
// box runs on its own thread, so the game never waits for it, and nothing is shown when nothing failed.
// NoSwapS3K.ini [Debug] Warnings=0 keeps them in the log only.
static SRWLOCK g_warnLock = SRWLOCK_INIT;
static std::string g_warnings;   // not shown yet
static int g_warnBoxes = 0;      // shown this session (at most 2)
static bool g_warnBoxOn = true;  // [Debug] Warnings (read in Init)

static void Warn(const char* fmt, ...) {
    char buf[1024];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    Log("WARNING: %s", buf);
    AcquireSRWLockExclusive(&g_warnLock);
    if (g_warnings.size() < 4000)
        g_warnings += std::string("- ") + buf + "\n";
    ReleaseSRWLockExclusive(&g_warnLock);
}

static DWORD WINAPI WarnBoxThread(LPVOID arg) {
    std::wstring* text = (std::wstring*)arg;
    MessageBoxW(nullptr, text->c_str(), L"NoSwap: something went wrong",
                MB_OK | MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND);
    delete text;
    return 0;
}

// Shows what Warn collected (if anything, and if the box isn't turned off)
static void ShowWarnings() {
    AcquireSRWLockExclusive(&g_warnLock);
    std::string body;
    body.swap(g_warnings);
    bool show = !body.empty() && g_warnBoxes < 2;
    if (show)
        g_warnBoxes++;
    ReleaseSRWLockExclusive(&g_warnLock);
    if (!show || !g_warnBoxOn)
        return;
    std::string text = "NoSwap couldn't set everything up, so extra characters may show empty cards in the character "
                       "select or play as Sonic:\n\n" + body + "\nThe log has the details: ";
    std::wstring w(text.size() + 1, L'\0');
    w.resize(MultiByteToWideChar(CP_UTF8, 0, text.c_str(), (int)text.size(), &w[0], (int)w.size()));
    w += g_logPathW.empty() ? L"(no log could be written)" : g_logPathW;
    w += L"\n\n(NoSwapS3K.ini [Debug] Warnings=0 turns this message off.)";
    HANDLE t = CreateThread(nullptr, 0, WarnBoxThread, new std::wstring(w), 0, nullptr);
    if (t)
        CloseHandle(t);
}

// ---------------------------------------------------------------- the roster (docs/plan-b-modular-characters.md)
// Which characters exist this session, decided at startup (BuildRuntimeRoster, with the packages): every installed
// package with a kind from the registry (Roster.h: roster.json, a key's kind is given once and kept), in kind order.
// Kinds with no installed package (removed, or never seen here) aren't in it: they are skipped everywhere (menus,
// pickers, saves keep their records aside). Filled once in Init before any hook goes in, never changed after.
struct RosterEntry {
    int kind;
    std::string key;
    std::string name;    // its noswap_character.json "name" (the act results name, e.g. "METAL SONIC")
    std::wstring root;   // its package folder (with a trailing backslash)
    ExtraData data;      // its S3&K data (data.loaded false: none usable, it plays as Sonic there)
    // Its card in Origins' select (SetUpMenuCards): the slot of the menu archives holding its picture and name (0: none,
    // it shows its base's picture and no name), whether the slot has its picture (else its base's), and whether the
    // name has a second line
    int cardSlot = 0;
    bool cardPicture = false, cardTwoLines = false;
    // Its head in the main menu's CONTINUE bubble (SetUpMenuCards): the slot's head cell has its package's head
    bool headPicture = false;
    // Its sprite credit under the select's cards (SetUpMenuCards, ShowCredit): the slot's credit key has it
    bool cardCredit = false;
};
static std::vector<RosterEntry> g_roster;
static const RosterEntry* g_rosterByKind[KIND_LIMIT + 1];  // nullptr: no character offered under that kind
static int g_maxKind = FIRST_EXTRA_KIND - 1;  // the highest kind offered (6: none)

static const RosterEntry* RosterOf(int kind) {
    return kind >= FIRST_EXTRA_KIND && kind < KIND_LIMIT ? g_rosterByKind[kind] : nullptr;
}
static bool Offered(int kind) { return RosterOf(kind) != nullptr; }
// The key of an offered kind (nullptr: none offered under it)
static const char* KindKey(int kind) {
    const RosterEntry* e = RosterOf(kind);
    return e ? e->key.c_str() : nullptr;
}
static int KindOfKey(const std::string& key) {
    for (auto& e : g_roster)
        if (e.key == key)
            return e.kind;
    return -1;
}

// ---------------------------------------------------------------- signature scanning
static void* SigScan(const char* signature, const char* mask) {
    MODULEINFO info{};
    GetModuleInformation(GetCurrentProcess(), GetModuleHandleA(nullptr), &info, sizeof(info));
    const size_t length = strlen(mask);
    auto* base = (const unsigned char*)info.lpBaseOfDll;
    for (size_t i = 0; i + length <= info.SizeOfImage; i++) {
        size_t j = 0;
        while (j < length && (mask[j] == '?' || (unsigned char)signature[j] == base[i + j]))
            j++;
        if (j == length)
            return (void*)(base + i);
    }
    return nullptr;
}

// LinkGameLogicDLL(EngineInfo* info): the engine hands the game logic its function table (the first
// field of EngineInfo; the game keeps the pointer, not a copy).
static const char SIG_LINK_GAME_LOGIC[] =
    "\x48\x83\xEC\x78\x4C\x8B\x09\x4C\x8B\x05\x00\x00\x00\x00\x8B\x15\x00\x00\x00\x00\x4C\x89\x0D\x00\x00\x00\x00"
    "\x48\x8B\x41\x68\x48\x89\x05\x00\x00\x00\x00\x48\x8B";
static const char MASK_LINK_GAME_LOGIC[] = "xxxxxxxxxx????xx????xxx????xxxxxxx????xx";

// Player_State_Air: a pogo bounce puts the player back in it
static const char SIG_PLAYER_STATE_AIR[] =
    "\x48\x89\x5C\x24\x00\x48\x89\x74\x24\x00\x57\x48\x83\xEC\x30\x48\x8D\x05\x00\x00\x00\x00\x48\x8B\xF9\x48\x89\x05"
    "\x00\x00\x00\x00\x48\x8B\x05\x00\x00\x00\x00\x8B";
static const char MASK_PLAYER_STATE_AIR[] = "xxxx?xxxx?xxxxxxxx????xxxxxx????xxx????x";
static void* g_playerStateAir = nullptr;

// ---------------------------------------------------------------- engine function table
static FunctionTable* RSDK = nullptr;
static void** g_engineInfo = nullptr;
static SceneInfo* g_sceneInfo = nullptr;
static ControllerState* g_controllers = nullptr;
// Fixed addresses in SonicOrigins.exe (it always loads at 0x140000000), from Ultrafix3kFixes
static SceneInfo* const SCENE_INFO = (SceneInfo*)0x143DB14E0;
static ControllerState* const CONTROLLERS = (ControllerState*)0x143729A90;

static int g_character = 0;      // the playing extra's kind (0 = none)

// Each extra's own data (palette, base, flags, ability numbers), read at startup from its package's
// noswap_character.json (the roster entry's data). A kind with no usable package has none (loaded false): it plays as
// Sonic.
static const ExtraData g_noData;
static const ExtraData& Extra(int kind) {
    const RosterEntry* e = RosterOf(kind);
    return e ? e->data : g_noData;
}
static uint16 g_extraFrames = 0;  // the extra's animation file, once loaded

static int PickedCharacter();  // save-menu picker (below)
static void SetActiveCharacter(const char* key, const char* why);
static int KindFromSetting(const char* value);

// Which extra plays: the save menu's pick, else NoSwapS3K.ini's [Debug] Character (for testing: a package key, or an
// old extra number 1-21; empty = none)
static void ReadSettings() {
    std::string ini = DllFolder() + "\\NoSwapS3K.ini";
    int c = PickedCharacter();
    if (c < 0) {
        char value[128] = {};
        GetPrivateProfileStringA("Debug", "Character", "", value, sizeof(value), ini.c_str());
        c = KindFromSetting(value);  // testing only: the save screen picks
    }
    if (c != 0 && !Offered(c))
        c = 0;
    if (c > 0 && !Extra(c).loaded) {  // no usable package data: it plays as Sonic
        static int logged = 0;
        if (logged != c)
            Log("extra character kind %d (%s): no package data, plays as Sonic", c, KindKey(c));
        logged = c;
        c = 0;
    }
    if (c != g_character)
        Log("extra character: kind %d (%s)", c, c ? KindKey(c) : "none");
    g_character = c;
    SetActiveCharacter(c ? KindKey(c) : nullptr, "S3&K");
}

// Super: while the extra is Super its own colours glow toward SUPER_GLOW_TO by g_glow (of 256; 0: its own colours,
// exactly). SuperGlow (below) sets it every frame; the writers below apply it.
constexpr uint32 SUPER_GLOW_TO = 0xFFF0A0;  // a pale gold (as in Sonic 1 and 2: abilities.py SUPER_GLOW_TO)
static int g_glow = 0;

static uint32 Glow(uint32 c, int amount) {
    if (amount <= 0)
        return c;
    uint32 out = 0;
    for (int shift = 16; shift >= 0; shift -= 8) {
        int v = (c >> shift) & 0xFF, to = (SUPER_GLOW_TO >> shift) & 0xFF;
        v += (to - v) * amount / 256;
        out |= (uint32)v << shift;
    }
    return out;
}

// The ending and credits scenes (3K_Ending: Sonic 3's ending after Launch Base 2, S&K's, the credits) draw their own
// art in those slots (3K_Ending/Objects.gif's island, clouds and water, the Tornado: 64-86), with colours the scene
// sets itself; the extra's colours there tinted the whole picture. No extra sprite needs them in those scenes.
static bool ExtraPaletteScene() {
    bool ending = RSDK && RSDK->CheckSceneFolder("3K_Ending");
    static bool logged = false;
    if (ending != logged)
        Log(ending ? "3K_Ending: the extra's colours are left out (the scene's art uses their slots)"
                   : "the extra's colours are written again (out of 3K_Ending)");
    logged = ending;
    return !ending;
}

// The extra's own colours go in slots that only Amy uses (bank 0, 64-95: no stage writes them)
static void ApplyExtraPalette() {
    if (g_character < 1 || !ExtraPaletteScene())
        return;
    for (int i = 0; i < (int)Extra(g_character).palette.size(); i++)
        RSDK->SetPaletteEntry(0, Extra(g_character).palette[i].index, Glow(Extra(g_character).palette[i].rgb, g_glow));
}

// Underwater, S3&K draws with another palette bank: the zone's water tint of bank 0. The extra's own colours
// aren't in it (those slots hold other colours there), so tint them the same way: for each bank that differs
// from bank 0 in the player's colours (slots 2-20), fit water = a * normal + b per channel over those
// colours, and write the extra's colours through it.
static void ApplyWaterPalettes() {
    if (g_character < 1 || (int)Extra(g_character).palette.size() == 0 || !ExtraPaletteScene())
        return;
    for (int bank = 1; bank < 8; bank++) {
        double sx[3] = {}, sy[3] = {}, sxx[3] = {}, sxy[3] = {};
        int n = 0, differ = 0;
        for (int i = 2; i <= 20; i++) {
            uint32 c0 = RSDK->GetPaletteEntry(0, i), c1 = RSDK->GetPaletteEntry(bank, i);
            if (!c0 && !c1)
                continue;
            differ += c0 != c1;
            for (int ch = 0; ch < 3; ch++) {
                double x = (c0 >> (16 - 8 * ch)) & 0xFF, y = (c1 >> (16 - 8 * ch)) & 0xFF;
                sx[ch] += x, sy[ch] += y, sxx[ch] += x * x, sxy[ch] += x * y;
            }
            n++;
        }
        if (n < 4 || differ < 4)
            continue;  // not a water version of bank 0
        for (int i = 0; i < (int)Extra(g_character).palette.size(); i++) {
            uint32 c = Glow(Extra(g_character).palette[i].rgb, g_glow), out = 0;  // (glowing while Super)
            for (int ch = 0; ch < 3; ch++) {
                double d = n * sxx[ch] - sx[ch] * sx[ch];
                double a = d ? (n * sxy[ch] - sx[ch] * sy[ch]) / d : 1.0;
                double b = (sy[ch] - a * sx[ch]) / n;
                double v = a * ((c >> (16 - 8 * ch)) & 0xFF) + b;
                int iv = v < 0 ? 0 : v > 255 ? 255 : (int)(v + 0.5);
                out |= (uint32)iv << (16 - 8 * ch);
            }
            RSDK->SetPaletteEntry(bank, Extra(g_character).palette[i].index, out);
        }
    }
}

// Once a second (and on the first frame of a stage): re-apply the extra's colours if something reloaded the
// palette (act changes do), and the water versions
static void KeepExtraPalette() {
    static int frames = 0;
    if (g_character < 1 || (int)Extra(g_character).palette.size() == 0 || frames++ % 60 != 0 || g_glow > 0)
        return;  // (while the colours glow, SuperGlow writes them every frame)
    const PaletteColour& first = Extra(g_character).palette[0];
    if ((RSDK->GetPaletteEntry(0, first.index) & 0xFFFFFF) != first.rgb)
        ApplyExtraPalette();
    ApplyWaterPalettes();
}

// The Blue Spheres stage (3K_Special) takes its colours above 127 from its tile sheet, and the extra's ball
// frames there use slots it leaves empty (build_s3k_art.SPECIAL_SLOTS): write their colours into bank 0.
// Nothing in the stage writes those slots, and it draws with bank 0 (its floor animation copies rows into it).
static int g_specialExtra = 0;  // the extra whose runner file the stage loaded (0: the game's own)

static void ApplySpecialPalette() {
    for (int i = 0; i < (int)Extra(g_specialExtra).specialPalette.size(); i++)
        RSDK->SetPaletteEntry(0, Extra(g_specialExtra).specialPalette[i].index,
                              Extra(g_specialExtra).specialPalette[i].rgb);
}

// Files with Sonic's art, and what an extra loads instead: fixed names (tools/extras.py S3K_FIXED). NoSwap ships
// placeholders under them (the game's own files, and blank sheets); the playing extra's package ships its own, which the
// file hook (Hook_CreateFileW, below) serves. Its .bin files name its sheets by fixed names too (3K_Players/Extra.gif...).
struct Swap {
    const char* sonic;
    const char* extra;
};
struct BaseSwap {
    int base;  // the package's "base": 0 Sonic, 1 Tails, 2 Knuckles; -1 any
    Swap swap;
};
// The extra's art replaces its base character's files, so that character's own code runs underneath
// (Sonic's for most; Knuckles' glide and climb for Rouge; Tails' flight for Charmy, without his tails)
static const BaseSwap SWAPS[] = {
    {0, {"3K_Players/Sonic.bin", "3K_Players/Extra.bin"}},
    {0, {"3K_Players/SuperSonic.bin", "3K_Players/Extra.bin"}},
    {1, {"3K_Players/Tails.bin", "3K_Players/Extra.bin"}},
    {1, {"3K_Players/TailSprite.bin", "3K_Players/NoTail.bin"}},  // no twin tails (NoSwap's own, for every such extra)
    {2, {"3K_Players/Knux.bin", "3K_Players/Extra.bin"}},
    // the Blue Spheres runner, seen from behind: the extra's spin ball (build_s3k_art.build_special)
    {0, {"3K_Special/Sonic.bin", "3K_Special/Extra.bin"}},
    {1, {"3K_Special/Tails.bin", "3K_Special/Extra.bin"}},  // its "Tail" frames are empty
    {2, {"3K_Special/Knuckles.bin", "3K_Special/Extra.bin"}},
    {-1, {"3K_Global/HUD.bin", "3K_Global/HUD_Extra.bin"}},  // life icon, name tag, results name
    {-1, {"3K_Global/SignPost.bin", "3K_Global/SignPost_Extra.bin"}},  // the goal sign's face
    // the special stage results ("CHARMY GOT A" / "CHAOS EMERALD"...: build_s3k_hud.build_special_clear). The game
    // loads it in Hidden Palace's stage (its only SpecialClear object), so the extra's colours go in as with the others
    {-1, {"3K_HPZ/SpecialClear.bin", "3K_HPZ/SpecialClear_Extra.bin"}},
    // Ice Cap 1's snowboard intro (S3K_ICZ1Intro's stageLoad): its rider frames are Sonic and the board drawn
    // together; a Sonic-based extra plays Sonic's Ground / Air / Sidewind (3 * characterID - 2..0), so his package's
    // copy has his own poses on the official board there (build_s3k_snowboard.py). Tails and Knuckles never get it
    {0, {"3K_ICZ/Snowboard.bin", "3K_ICZ/Snowboard_Extra.bin"}},
};
static const char* const PLAYER_FILES[] = {"3K_Players/Sonic.bin", "3K_Players/Tails.bin", "3K_Players/Knux.bin"};

typedef uint16 (*LoadSpriteFn)(const char* filePath, uint8 scope);
static LoadSpriteFn g_loadSpriteAnimation = nullptr;
// ability_cycle (abilities.py: Emerl's Copycat): the active jump ability's place in the extra's cycleMoves, 0 at each
// stage load (the player's sprites load then); each melee started on Y makes the next one active (Abilities)
static int g_copy = 0;

static uint16 Hook_LoadSpriteAnimation(const char* filePath, uint8 scope) {
    bool player = false;
    // SpecialClear (the special stage results, shown in Hidden Palace's stage: the special stage's end sets the
    // scene to "Hidden Palace Zone") builds its file's path at run time from a table of zone folders, as
    // "<folder>/SpecialClear.bin" (its StageLoad in the exe; only 3K_HPZ has the file). Matched by its name alone,
    // and each path it asks for is logged once, so a test shows what the game really loaded
    if (filePath) {
        const char* slash = strrchr(filePath, '/');
        const char* name = slash ? slash + 1 : filePath;
        if (_stricmp(name, "SpecialClear.bin") == 0) {
            static std::string seen;
            if (_stricmp(seen.c_str(), filePath) != 0)
                Log("special stage results: the game loads %s (scope %d, extra kind %d)", filePath, scope, g_character);
            seen = filePath;
            filePath = "3K_HPZ/SpecialClear.bin";
        }
    }
    for (const BaseSwap& s : SWAPS)  // any swapped file can load first at a stage start (the HUD did, and got
        if (filePath && _stricmp(filePath, s.swap.sonic) == 0)  // the previous extra's name): re-read the pick
            ReadSettings();
    int base = g_character > 0 ? Extra(g_character).base : 0;
    if (filePath && _stricmp(filePath, PLAYER_FILES[base]) == 0)
        player = true;
    bool special = filePath && _strnicmp(filePath, "3K_Special/", 11) == 0;
    if (filePath && _stricmp(filePath, "3K_Special/Sonic.bin") == 0)
        g_specialExtra = 0;  // the first runner file S3K_SS_Player's stage load asks for
    bool swapped = false;
    if (g_character > 0 && filePath) {
        for (const BaseSwap& bs : SWAPS) {
            const Swap& s = bs.swap;
            if ((bs.base < 0 || bs.base == base) && _stricmp(filePath, s.sonic) == 0) {
                // (the engine keeps a file loaded under its name for its scope: a fixed name must not outlive the
                // stage, or the next extra would get this one's. Stage scope is 2)
                Log("%s -> %s (%s, scope %d%s)", filePath, s.extra, KindKey(g_character), scope,
                    scope == 2 ? "" : ": NOT the stage's, another extra could get these files");
                filePath = s.extra;
                swapped = true;
                break;
            }
        }
    }
    uint16 id = g_loadSpriteAnimation(filePath, scope);
    if (player) {
        g_extraFrames = swapped ? id : 0;
        g_copy = 0;  // (ability_cycle: the first move again)
    }
    if (swapped && special) {
        g_specialExtra = g_character;
        ApplySpecialPalette();  // sprites load while the stage loads, after its palette
    } else if (swapped) {
        ApplyExtraPalette();
    }
    return id;
}

// ---------------------------------------------------------------- abilities
// S3&K animation IDs (3K_Players/Sonic.bin) and the extras' ability animations (build_s3k_art.py)
enum { ANI_IDLE = 0, ANI_BORED_1 = 1, ANI_BORED_2 = 2, ANI_CROUCH = 4, ANI_WALK = 5, ANI_JOG = 9, ANI_RUN = 11, ANI_DASH = 13,
       ANI_JUMP = 15, ANI_HURT = 22, ANI_DIE = 23, ANI_DROWN = 24,  // (each walk / run is followed by its "Angled" one)
       ANI_PEELOUT = 75,  // Sonic.bin only (then its "Angled" one)
       ANI_TAILS_FLY = 75, ANI_TAILS_SWIM_LIFT = 82,  // Tails.bin: his flight's poses are 75-82 (Fly..Swim Lift)
       ANI_KNUX_GLIDE = 71, ANI_KNUX_GLIDE_DROP = 72,  // Knux.bin: gliding, and falling after letting go
};
// The extra's own ability animations follow its base file's (build_s3k_art.py): 77 on for Sonic's
#define ANI_EXTRA(k) (Extra(g_character).animBase + (k))
#define ANI_EXTRA_ATTACK ANI_EXTRA(0)
#define ANI_EXTRA_HOVER ANI_EXTRA(1)
#define ANI_EXTRA_SHOT ANI_EXTRA(2)
#define ANI_EXTRA_ATTACK_UP ANI_EXTRA(3)
#define ANI_EXTRA_ATTACK_DOWN ANI_EXTRA(4)
#define ANI_EXTRA_GLIDE_UP ANI_EXTRA(5)
#define ANI_EXTRA_CLING ANI_EXTRA(5)  // wall_cling (an extra without Ray's glide: its glide-up slot, S1/S2's 47)
#define ANI_EXTRA_SWIM ANI_EXTRA(5)  // water_swim's stroke (an extra without Ray's glide or wall_cling: S1/S2's 47)
#define ANI_EXTRA_SINK ANI_EXTRA(5)  // the Shadow Sink's frames (an extra without those: S1/S2's 47)
#define ANI_EXTRA_GLIDE_DOWN ANI_EXTRA(6)
#define ANI_EXTRA_ROLL ANI_EXTRA(7)  // only for extras with EXTRA_ROLL
#define ANI_EXTRA_SHOT_AIR ANI_EXTRA(8)  // only for extras whose air shot has its own frames (shotAirFrames)
#define ANI_EXTRA_SURGE_IDLE ANI_EXTRA(9)  // only for extras with a Power Surge: its idle / walk / run
#define ANI_EXTRA_SURGE_RUN ANI_EXTRA(10)
#define ANI_EXTRA_SURGE_SPRINT ANI_EXTRA(11)

struct AbilityState {
    bool ready;    // the jump ability can be used this jump
    int dash;      // Jet Dash frames left
    int hover;     // 0 no hover; 1.. hover allowed (after a dash), counting frames used + 1
    bool pogo;     // bouncing on the tail
    int umbrella;  // 1 open, 2 closed for this jump
    int floated;   // frames the umbrella has been open this jump (for floatFrames)
    int shot;      // shot frames left
    int cooldown;  // frames until the next shot (shotCooldown: Espio's Leaf Swirl)
    int leaf;      // Espio's Leaf Swirl invisibility (shotBlink): frames left of the post-hit blink it set
    int chaos;     // Chaos Control: frames left (flash, then warp); -1 after the hop, until falling
    int aim;       // aimed dash frames left
    int aimDir;    // -1 up, 0 straight, 1 down
    bool aimLeft;  // the aimed dash keeps the direction it started in
    bool aimUsed;  // aimDashY: used this airborne period
    int aimJumpState;  // aimDashY: jumpAbilityState to give back after the dash (held at 0 during it)
    bool hammer;   // Mighty's Hammer Drop in progress
    int hammerVY;  // its fall speed last frame
    // Ray's glide (Mania's Player_State_RayGlide: glideUp = rotation, angle = abilityValue,
    // lift = abilitySpeed, speedCap = abilityValues[0], swoopPower = abilityTimer)
    bool glide, glideUp, glideLeft;
    int angle, lift, speedCap, swoopPower;
    Vector2 vel;  // the glide's own velocity (the game's air state runs first and would add to it)
    bool batGlide;  // batGlide: gliding last frame
    int batVY;      // batGlide: the fall speed she glided at last frame
    bool kick, kickLeft, kickUsed;  // Screw Kick: in progress, its direction, used this airborne period
    int kickJumpState;  // jumpAbilityState to give back if the kick ends in the air (held at 0 during it)
    int bomb;  // Bomb Jump: frames left, the bomb beat then the blast (the parachute follows through `hover`)
    // Ear Grapple: 1.. the ear going out (its frame + 1), 101.. latched and reeling in (frames + 100), 201.. snapping
    // back (frames left + 200); 0 none (the Ear Copter follows through `hover`)
    int ear;
    bool earLeft;   // the direction the ear went out in
    bool earUsed;   // grappleY: the Ear Grapple was used this airborne period
    int earWait;    // grappleRefill: frames before the grab that a latch or a hit gave back can go again
    Vector2 latch;  // where it latched on
    int spirit;          // Spirit Flight: frames left, the transform then the flight (spiritFrames and under)
    Vector2 spiritVel;   // the orb's own velocity
    bool shotAir;        // the shot shown last frame was the air one (shotAirFrames)
    int chain;           // Triple Jump: the last jump's number in the chain (1-3; 4 once the third's somersault is over)
    int chainWindow;     // Triple Jump: frames left on the ground to jump again
    bool doubleJump;     // Double Jump: rising in the shell spin
    int cling;           // Wall Cling: frames on the wall (0: not clinging)
    bool clingLeft;      // the wall's side (on her left); after, the side she let go of
    int clingLock;       // frames (away from it) before she can cling to that side again
    int zip;             // Thunder Zip: frames of its pose left (the zip, then her speed along)
    int zipCarry;        // Thunder Zip: the speed she keeps after it (its sign: the zip's direction)
    bool gear;           // Extreme Gear: riding the board
    int gearVel;         // Extreme Gear: the board's velocity (its sign: the way he rides)
    int gearLift;        // Extreme Gear: lift frames left this ride
    int gearLeft;        // Extreme Gear: ride frames left (gearFrames; 0 in the data: no limit)
    int throwPose;       // shot (a real projectile, shots::Frame): frames of the throwing pose left
    bool throwAir;       // ...thrown in the air
    bool throwHigh;      // ...with up held (its pose: ShotData.upPose)
    int throwPrev;       // ShotData.poseAlways, in the air: the animation the pose shows over (back after it)
    int throwAim;        // ShotData.aimPose: the throw's aim, its pose's frame (0 level, 1 forward-up, 2 up, 3 forward-down, 4 down)
    bool puddleDrop;     // Puddle Slide: dropping in the dive
    int puddle;          // Puddle Slide: game frames of the puddle left (melting, sliding, rising)
    int sink;            // Shadow Sink: 0 ready; below 0 the cooldown; 1.. sinking, then under; SINK_RISE.. rising
    int charge;          // Charge: the ground speed it set last frame, signed by its direction (0: none)
    int chargeAnim;      // Charge: the animation it showed last frame
    void* chargeState;   // Charge: the state it started in (the plain ground one: another ends it)
    int spark;           // Shine Spark (Spark): 0 none; 1..sparkStore stored (frames left); SPARK_ACTIVE + its kind
                         // (1 up, 2 up-forward, 3 forward) + 100 going left: flying
    int spin;            // Spin Attack: frames spun (0: ready; below 0: the cooldown)
    int spinAnim;        // Spin Attack: the animation it showed last frame
    int hiKick;          // Spin-Kick High Jump: 0 none; 1.. the wind-up; HIKICK_KICK.. the kick; HIKICK_RECOVER.. the recovery
    bool hiKickUsed;     // Spin-Kick High Jump: used this airborne period
    int hiKickCool;      // Spin-Kick High Jump: frames on the ground before the next
    int swimDelay;       // Water swim: frames before the next stroke
    int warp;            // Phase Warp: frames of it left (the flicker out, gone, the flicker in)
    int warpDX, warpDY;  // Phase Warp: its direction (-1, 0, 1 each)
    int warpVX;          // Phase Warp: his speed along before it (he has it again after)
    int rocket;          // Rocket Burst: ROCKET_CHARGING + frames charging; 1.. the burst's / the spin's frames left; 0 none
    Vector2 rocketVel;   // Rocket Burst: its own velocity ({0, 0}: the Rocket Spin)
    int whipAim;         // melee_whip (John's whip): the pose picked as Y was pressed (UpThrow's notes: 0 plain,
                         // 1 crouching, 2 up-forward, 3 down); melee_run / melee_up (Axel's): 4 running, 5 up + Y
};
struct Ghost { Vector2 pos; Animator anim; uint8 direction; int32 rotation; int alpha; };
static Ghost g_ghosts[8];
static int g_ghostNext = 0;
static AbilityState g_ab{};
// Heavy's Shine Spark (Spark, below; abilities.py charge "spark_*"): g_ab.spark above this is flying (abilities.py
// SPARK_ACTIVE). The input wrapper (NoRollInput) notes a down it took at full charge (no roll: it stores the spark)
constexpr int SPARK_ACTIVE = 1000;
static bool g_sparkDown = false;
// An up + Y throw (ShotData.upOnly: John's sub-weapons): up held, but in the air up with a side held is his up-forward
// whip (shotWhip) instead. (The pad as the player's update read it)
static bool UpThrow(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    return p->up && !(air && c.shotWhip && (p->left || p->right));
}
// Spin Attack: while it lasts (g_spinWatch), the hooks on the game's badnik, boss and monitor checks (namespace shots)
// note that player 1 broke or hit something (g_spinHit): Abilities bounces her hard on her next update
static bool g_spinWatch = false, g_spinHit = false;
// Screen Nuke (abilities.py melee_nuke): frames left of its hit (the shots' Player_CheckBadnikTouch hook takes anything on
// screen as touched meanwhile), and the flash (NukeFlash: its frame, -1 none)
static int g_nuke = 0;
static int g_nukeReachX = 0, g_nukeReachY = 0;  // its box round him in px (Bomb's half-screen nuke; 0: the whole screen)
static int g_flashAt = -1;

// Power Surge: kept apart from the ability state above, which a hit clears (a surge goes on through a hit)
struct SurgeState {
    int left;          // frames left: the surge (above surgeCooldown), then its cooldown
    int variant;       // the Power Surge animation shown last frame (-1: none)
    int tick;          // its own animation clock (a frame lasts 240, as in every built animation)
    bool swapped;      // the animator holds what SurgeShow put there, until the next update puts the game's back
    bool mapped;       // ...a Power Surge animation (otherwise the game's own, reported as the jump)
    Animator real;     // the game's animator, as its update left it
    Animator shown;    // what SurgeShow put in its place
};
static SurgeState g_surge{0, -1};
// the blink timer's byte offset in EntityPlayer, -1 unknown (FindBlinkTimer). Default: +0x1CC, Mania's blinkTimer
// (found in-game there, and PLAYER_BLINK_TIMER below); the ini's BlinkOffset overrides it. Unknown until a first hit,
// a fresh install's Leaf Swirl, Shadow Sink and Phase Warp gave no protection (and Espio never turned invisible).
constexpr int BLINK_OFFSET_DEFAULT = 0x1CC;
static int g_blinkOffset = BLINK_OFFSET_DEFAULT;

// Show one of the extra's own animations. `attacking`: report the Jump animation to the game, which is
// how S3&K decides the player hurts enemies; the game then also leaves the animation alone, since it
// only switches animations when the ID changes.
static void PlayExtraAnimation(EntityPlayer* p, int anim, bool attacking, bool restart) {
    int shownID = attacking ? ANI_JUMP : anim;
    if (restart || p->animator.animationID != shownID || (attacking && p->animator.frames == nullptr))
        RSDK->SetSpriteAnimation(g_extraFrames, anim, &p->animator, true, 0);
    if (attacking)
        p->animator.animationID = ANI_JUMP;
}

static void BackToJump(EntityPlayer* p) {
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_JUMP, &p->animator, true, 0);
}

static bool g_ySuper = false;  // this frame's Y press transformed the extra (Hook_PlayerUpdate): it's no move's press
// Ray Poward's Slide (abilities.py ground_slide): the input wrapper (NoRollInput) took a crouch's jump press for it this
// update; Abilities starts the slide (PuddleSlide's ground part)
static bool g_slideStart = false;

static bool Held(EntityPlayer* p);  // (the free-state gate, below)
static void NoteHeld(const char* what, EntityPlayer* p);

static bool YPressed(EntityPlayer* p) {
    if (!g_controllers || g_ySuper)
        return false;
    int ctrl = p->controllerID;
    if (ctrl < 0 || ctrl > 4)
        ctrl = 1;
    bool press = g_controllers[ctrl].keyY.press != 0;
    if (press && Held(p)) {  // an object holds the player: not a move's press
        NoteHeld("Y press", p);
        return false;
    }
    return press;
}

static bool DownHeld(EntityPlayer* p);  // (the pad's down itself: below)

// Y held down (a move that lasts while Y is held: Heavy's Charge)
static bool YDown(EntityPlayer* p) {
    if (!g_controllers || g_ySuper)
        return false;
    int ctrl = p->controllerID;
    if (ctrl < 0 || ctrl > 4)
        ctrl = 1;
    return g_controllers[ctrl].keyY.down != 0 && !Held(p);
}

// Mania's applyJumpCap (the unnamed int between jumpHold and jumpAbilityState, the same layout as Mania): while
// set, letting go of jump caps a rise in the jump ball at jumpCap. Springs clear it; so does the Bomb Jump's blast.
static void NoJumpCap(EntityPlayer* p) {
    *(int32*)p->padding6 = false;
}

static bool Hurt(EntityPlayer* p) {
    int a = p->animator.animationID;
    return a == ANI_HURT || a == ANI_DIE || a == ANI_DROWN;
}
// ---------------------------------------------------------------- the free-state gate
// The extra's jump-press moves and Y moves only start while player 1 is in one of the game's own free states: the air
// state (Player_State_Air), the plain ground ones, or the base character's own moves (Tails' flight, Knuckles' glide
// and climb). While an object holds the player (CNZ's cannons, MHZ's poles and bars, tubes, being carried, cutscenes:
// the object's own state, or the game's static ones), a press is the object's (the cannon fires on jump) and not the
// extra's. Every Player state function of this build starts by storing its name ("State_Air"...) into one debug global
// (lea rax,[name]; ...; mov [global],rax): the states are told apart by those names, the global taken from
// Player_State_Air's own prologue at startup (StateGateSetUp). Without it the gate stays open (the old behaviour).
static bool Readable(const void* p, size_t size);  // (below)
static uintptr_t g_stateNameSlot = 0;  // the debug global Player states write their names to (0: gate off)

// The name a state function writes to `slot` (0: any slot, and *slotOut gets it), or nullptr
static const char* StateLabel(const void* fn, uintptr_t slot, uintptr_t* slotOut = nullptr) {
    const uint8* c = (const uint8*)fn;
    if (!fn || !Readable(c, 0x60))
        return nullptr;
    for (int i = 0; i < 0x40; i++) {
        if (c[i] != 0x48 || c[i + 1] != 0x8D || c[i + 2] != 0x05)  // lea rax,[rip+disp32]
            continue;
        const char* name = (const char*)(c + i + 7 + *(const int32*)(c + i + 3));
        for (int j = i + 7; j < i + 0x20; j++) {
            if (c[j] != 0x48 || c[j + 1] != 0x89 || c[j + 2] != 0x05)  // mov [rip+disp32],rax
                continue;
            uintptr_t g = (uintptr_t)(c + j + 7 + *(const int32*)(c + j + 3));
            if (slot && g != slot)
                break;
            if (!Readable(name, 32) || strncmp(name, "State_", 6) != 0)
                return nullptr;
            if (slotOut)
                *slotOut = g;
            return name;
        }
        return nullptr;
    }
    return nullptr;
}

static void StateGateSetUp() {
    uintptr_t slot = 0;
    const char* name = g_playerStateAir ? StateLabel(g_playerStateAir, 0, &slot) : nullptr;
    if (name && strcmp(name, "State_Air") == 0) {
        g_stateNameSlot = slot;
        Log("state gate: on (Player states name themselves at %p)", (void*)slot);
    } else {
        Log("state gate: OFF (Player_State_Air %p doesn't look as expected): extras' moves aren't gated", g_playerStateAir);
    }
}

enum StateKind { STATE_OPEN, STATE_AIR, STATE_GROUND, STATE_BASE_MOVE, STATE_HELD };

static StateKind KindOf(const void* fn, const char** nameOut = nullptr) {
    static struct { const void* fn; StateKind kind; const char* name; } cache[64];
    static int used = 0;
    if (nameOut)
        *nameOut = "?";
    if (!g_stateNameSlot || !fn)
        return STATE_OPEN;
    if (fn == g_playerStateAir) {
        if (nameOut)
            *nameOut = "State_Air";
        return STATE_AIR;
    }
    for (int i = 0; i < used; i++)
        if (cache[i].fn == fn) {
            if (nameOut)
                *nameOut = cache[i].name;
            return cache[i].kind;
        }
    // (only the Player object's own functions: an object's own state named like one of these isn't the player's)
    intptr_t dist = (intptr_t)fn - (intptr_t)g_playerStateAir;
    const char* name = dist > -0x40000 && dist < 0x40000 ? StateLabel(fn, g_stateNameSlot) : nullptr;
    static const char* const ground[] = {"State_Ground", "State_Roll", "State_Crouch", "State_LookUp", "State_Spindash",
                                         "State_Peelout"};
    static const char* const base[] = {"State_Fly", "State_GlideLeft", "State_GlideRight", "State_GlideDrop",
                                       "State_GlideSlide", "State_Climb", "State_LedgePullup", "State_BubbleBounce"};
    StateKind kind = STATE_HELD;
    if (name) {
        for (const char* g : ground)
            if (strcmp(name, g) == 0)
                kind = STATE_GROUND;
        for (const char* b : base)
            if (strcmp(name, b) == 0)
                kind = STATE_BASE_MOVE;
    }
    if (!name)
        name = "(not a named Player state)";
    if (used < 64)
        cache[used++] = {fn, kind, name};
    if (nameOut)
        *nameOut = name;
    return kind;
}

// Held by an object (or a cutscene): no move of the extra's starts
static bool Held(EntityPlayer* p) {
    return KindOf((const void*)p->state.state) == STATE_HELD;
}

// The melee's cost (abilities.py melee_cost: Bomb's Self-Destruct): as it ends, a normal hit on him through the exe's
// own Player_Hit (0x1401e36a0: "xor edx,edx; jmp" into the hurt body 0x1401e3360, read with objdump, never run): a
// shield lost, or the rings scattered, or at 0 rings his death, then the hurt state and its 120-frame blink. The game's
// hit checks (e.g. 0x1401dd882) skip it while he's hurt, dying or drowning, or while the invincibility timer (+0x1C4),
// the blink (+0x1CC) or +0x368 is set, set velocity.x 2 px per frame away from the hazard, then call it. Here the same,
// except the blink (his own melee_safe one isn't a guard against the cost), knocked back from the way he faces; and
// only in the game's free states (not held by an object). Off if either function's bytes differ.
constexpr uintptr_t PLAYER_HIT = 0x1401e36a0, PLAYER_HIT_BODY = 0x1401e3360;
constexpr int COST_INVINCIBLE = 0x1C4, COST_GUARD = 0x368;
typedef void (*PlayerHitFn)(EntityPlayer* player);
static void ShotCost(EntityPlayer* p, bool facingLeft) {
    static const uint8 HIT[] = {0x33, 0xd2, 0xe9, 0xb9, 0xfc, 0xff, 0xff};
    static const uint8 BODY[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24,
                                 0x18, 0x57, 0x48, 0x83, 0xec, 0x30};
    static int ok = -1;
    if (ok < 0) {
        ok = Readable((void*)PLAYER_HIT, sizeof(HIT)) && memcmp((void*)PLAYER_HIT, HIT, sizeof(HIT)) == 0
             && Readable((void*)PLAYER_HIT_BODY, sizeof(BODY)) && memcmp((void*)PLAYER_HIT_BODY, BODY, sizeof(BODY)) == 0;
        Log("melee cost: Player_Hit at %p %s", (void*)PLAYER_HIT, ok ? "checks out" : "is DIFFERENT: no cost");
    }
    if (!ok || !p)
        return;
    const char* why = Hurt(p) ? "hurt already" : Held(p) ? "held by an object"
                      : *(int32*)((char*)p + COST_INVINCIBLE) ? "invincible"
                      : *(int32*)((char*)p + COST_GUARD) ? "guarded (+0x368)" : nullptr;
    if (why) {
        Log("melee cost: none (%s)", why);
        return;
    }
    p->velocity.x = facingLeft ? 0x20000 : -0x20000;  // knocked back
    Log("melee cost: Player_Hit (rings %d)", p->rings);
    ((PlayerHitFn)PLAYER_HIT)(p);
}

// Log once per state (and kind of press) what the gate ignored: the next CNZ / MHZ test names the objects' states
static void NoteHeld(const char* what, EntityPlayer* p) {
    static struct { const void* fn; const char* what; } seen[48];
    static int used = 0;
    const void* fn = (const void*)p->state.state;
    for (int i = 0; i < used; i++)
        if (seen[i].fn == fn && seen[i].what == what)
            return;
    if (used >= 48)
        return;
    seen[used++] = {fn, what};
    const char* name;
    KindOf(fn, &name);
    Log("state gate: %s ignored in state %p %s (anim %d, onGround %d)", what, fn, name, p->animator.animationID,
        (int)p->onGround);
}

// The debug name any state function stores in the state-name slot (objects' states too: "PState_Start"), or "?"
static const char* AnyStateName(const void* fn) {
    const uint8* c = (const uint8*)fn;
    if (!fn || !g_stateNameSlot || !Readable(c, 0x60))
        return "?";
    for (int i = 0; i < 0x20; i++) {
        if (c[i] != 0x48 || c[i + 1] != 0x8D || c[i + 2] != 0x05)  // lea rax,[rip+disp32]
            continue;
        const char* name = (const char*)(c + i + 7 + *(const int32*)(c + i + 3));
        for (int j = i + 7; j < i + 0x20; j++)
            if (c[j] == 0x48 && c[j + 1] == 0x89 && c[j + 2] == 0x05  // mov [rip+disp32],rax
                && (uintptr_t)(c + j + 7 + *(const int32*)(c + j + 3)) == g_stateNameSlot)
                return Readable(name, 24) && name[0] >= 'A' && name[0] <= 'z' ? name : "?";
        return "?";
    }
    return "?";
}

// While an object holds player 1, what it's doing, rate-limited (at each new held state, then every 2 seconds; 120
// lines a session at most), so a cutscene that never lets go shows what it waits for. S&K's Sky Sanctuary (Knuckles,
// S3K_SSZKIntro): Egg Robo's claw holds him in State_Static until Mecha Sonic touches the robo
// (State_EggRobo_WaitForMecha), then "PState_Start" (0x140267fb0) sends him right on his own velocity, the glide pose
// (anim 71), with no gravity or control, until x reaches MechaSonic's sVars +0x1C + (+0x16C << 7): then the glide.
// Nothing keeps that velocity up, so anything scaling it each frame (the Bat Glide once did) stops him short for good.
static void HeldStatus(EntityPlayer* p) {
    static const void* last = nullptr;
    static int frames = 0, lines = 0;
    const void* fn = (const void*)p->state.state;
    if (fn != last) {
        last = fn;
        frames = 0;
    }
    if (frames++ % 120 != 0 || lines >= 120)
        return;
    lines++;
    const char* name = AnyStateName(fn);
    char wait[160] = "";
    // PState_Start's own check (at +0x30: mov rax,[MechaSonic sVars]; mov ecx,[rax+0x16C]; shl ecx,7; add ecx,[rax+0x1C];
    // cmp [rbx+8],ecx), read from its code so a different build just doesn't print it
    static const uint8 CHECK[] = {0x48, 0x8B, 0x05, 0, 0, 0, 0, 0x8B, 0x88, 0x6C, 0x01, 0x00, 0x00, 0xC1, 0xE1, 0x07,
                                  0x03, 0x48, 0x1C, 0x39, 0x4B, 0x08};
    const uint8* c = (const uint8*)fn;
    bool match = strcmp(name, "PState_Start") == 0 && Readable(c + 0x30, sizeof(CHECK));
    for (size_t i = 0; match && i < sizeof(CHECK); i++)
        if (!(i >= 3 && i < 7) && c[0x30 + i] != CHECK[i])
            match = false;
    if (match) {
        auto** sVars = (const uint8**)(c + 0x30 + 7 + *(const int32*)(c + 0x30 + 3));
        const uint8* s = Readable(sVars, sizeof(void*)) ? *sVars : nullptr;
        if (s && Readable(s, 0x170)) {
            int target = (*(const int32*)(s + 0x16C) << 7) + *(const int32*)(s + 0x1C);
            snprintf(wait, sizeof(wait), ": waiting for x %d >= %d (%d px to go)", p->position.x >> 16, target >> 16,
                     (target - p->position.x) >> 16);
        }
    }
    Log("held: state %p %s, anim %d frame %d/%d, pos %d,%d, vel %d,%d, onGround %d%s", fn, name,
        p->animator.animationID, p->animator.frameID, p->animator.frameCount, p->position.x >> 16,
        p->position.y >> 16, p->velocity.x, p->velocity.y, (int)p->onGround, wait);
}

// ---------------------------------------------------------------- physics
// The player's physics fields (found by their values in-game; the same layout as Sonic Mania). The game
// sets them at stage start and again for water, speed shoes and Super; whenever it does, the extra's
// multipliers go on top, once.
// A Power Surge's multipliers go on top while it lasts: the game's own value is kept (g_physicsBase), so the field is
// rescaled from it when the multiplier changes, and a value the game sets meanwhile (water, speed shoes) still counts.
struct PhysicsField {
    int offset;
    int ExtraAbilities::*multiplier;
    int ExtraAbilities::*surge;  // power_surge's multiplier for it (nullptr: none)
};
static const PhysicsField PHYSICS[] = {
    {0x220, &ExtraAbilities::topSpeed, &ExtraAbilities::surgeTopSpeed},
    {0x224, &ExtraAbilities::acceleration, &ExtraAbilities::surgeAcceleration},
    {0x228, &ExtraAbilities::acceleration, &ExtraAbilities::surgeAcceleration},
    {0x22C, &ExtraAbilities::airAcceleration, &ExtraAbilities::surgeAirAcceleration},
    {0x248, &ExtraAbilities::jump, nullptr},
};
constexpr size_t PHYSICS_COUNT = sizeof(PHYSICS) / sizeof(PHYSICS[0]);
static int g_physicsWritten[PHYSICS_COUNT], g_physicsBase[PHYSICS_COUNT], g_physicsMult[PHYSICS_COUNT];

static bool Surging(const ExtraAbilities& c) { return c.powerSurge && g_surge.left > c.surgeCooldown; }
static int NinjaJump(int m);  // (Joe Musashi's Fushin: a higher jump for a while; Ninjutsu.h)

static void ApplyPhysics(EntityPlayer* p) {
    const ExtraAbilities& c = Extra(g_character).abilities;
    static int lastCharacter = -1;
    if (g_character != lastCharacter) {  // another extra's values mean nothing now
        lastCharacter = g_character;
        for (size_t i = 0; i < PHYSICS_COUNT; i++)
            g_physicsWritten[i] = INT32_MIN;
    }
    for (size_t i = 0; i < PHYSICS_COUNT; i++) {
        int m = c.*PHYSICS[i].multiplier;
        if (m == 0)
            m = 1000;
        if (Surging(c) && PHYSICS[i].surge)
            m = (int)((long long)m * (c.*PHYSICS[i].surge) / 1000);
        if (PHYSICS[i].offset == 0x248)  // (jumpStrength: Joe's Fushin scales it while it lasts, Ninjutsu.h)
            m = NinjaJump(m);
        int* field = (int*)((char*)p + PHYSICS[i].offset);
        if (*field != g_physicsWritten[i])  // the game set a new value: scale it
            g_physicsBase[i] = *field;
        else if (m == g_physicsMult[i])
            continue;
        if (m == 1000 && *field == g_physicsBase[i]) {  // nothing to scale (as for the extras with no physics)
            g_physicsWritten[i] = *field;
            g_physicsMult[i] = m;
            continue;
        }
        *field = (int)((long long)g_physicsBase[i] * m / 1000);
        g_physicsWritten[i] = *field;
        g_physicsMult[i] = m;
    }
}

static int Gravity(EntityPlayer* p) { return *(int*)((char*)p + 0x240); }
// In the water: the player's underwater field (Mania's `underwater`, the int at +0x1DC: 0 dry, 1 the zone's water, else
// a pool's slot). Player_UpdatePhysicsState (0x1401e5670) gives the water's gravity when it isn't 0. The field itself,
// not the gravity, so a gravity something else set (or flipped: DEZ) never reads as water.
constexpr int PLAYER_UNDERWATER = 0x1DC;
static bool InWater(EntityPlayer* p) { return *(int*)((char*)p + PLAYER_UNDERWATER) != 0; }

// RSDK's trig tables: Sin256 / Cos256 over 256 steps scaled by 256, Cos512 over 512 steps scaled by 512
static int Sin256(int a) { return (int)(std::sin((a & 0xFF) / 128.0 * 3.14159265358979) * 256.0); }
static int Cos256(int a) { return (int)(std::cos((a & 0xFF) / 128.0 * 3.14159265358979) * 256.0); }
static int Cos512(int a) { return (int)(std::cos((a & 0x1FF) / 256.0 * 3.14159265358979) * 512.0); }

static void RayGlide(EntityPlayer* p, bool trigger, bool air) {
    bool water = Gravity(p) < 0x3800;
    Vector2& v = g_ab.vel;
    if (trigger) {
        bool left = p->direction & 1;
        v = p->velocity;
        int newX = v.x - (v.x >> 3);
        if (left)
            v.x = std::min(newX, water ? -0x18000 : -0x30000);
        else
            v.x = std::max(newX, water ? 0x18000 : 0x30000);
        if ((!left && p->right) || (left && p->left)) {  // holding forward: start in a dive
            g_ab.glideUp = false;
            g_ab.lift = 0;
            PlayExtraAnimation(p, ANI_EXTRA_GLIDE_DOWN, false, true);
        }
        else {
            g_ab.glideUp = true;
            v.x >>= 1;
            int speed = std::abs(v.x);
            g_ab.lift = std::min(-((speed >> 1) + (speed >> 2) + (speed >> 4)) >> (water ? 1 : 0), 0x40000);
            PlayExtraAnimation(p, ANI_EXTRA_GLIDE_UP, false, true);
        }
        v.y >>= 1;
        g_ab.angle = 0x40;
        g_ab.speedCap = std::abs(v.x);
        g_ab.swoopPower = 256;
        g_ab.glideLeft = left;
        g_ab.glide = true;
        p->velocity = v;
        return;
    }
    if (!g_ab.glide)
        return;

    if (!air) {  // landed: a slow landing gets a boost
        if (std::abs(p->groundVel) < 0x20000)
            p->groundVel <<= 1;
        g_ab.glide = false;
        return;
    }
    if (p->velocity.x == 0)  // the game stopped him at a wall
        v.x = 0;
    if (v.y < 0 && p->velocity.y == 0)  // or at a ceiling
        g_ab.lift = 0;
    p->direction = g_ab.glideLeft ? 1 : 0;  // the game's air control would turn him around

    if (g_ab.glideUp) {
        if (g_ab.angle < 0x70)
            g_ab.angle += 8;
    }
    else if (g_ab.angle > 0x10) {
        g_ab.angle -= 8;
    }

    if (g_ab.lift) {
        v.y += g_ab.lift >> (2 - (water ? 1 : 0));
        if (v.y < g_ab.lift) {
            v.y = g_ab.lift;
            g_ab.lift = 0;
        }
    }
    else {
        v.y += (Gravity(p) * Cos512(g_ab.angle)) >> 9;
    }
    if (v.y < -0x60000)
        v.y = -0x60000;
    if (g_ab.glideUp && v.y > 0x10000)
        v.y -= v.y >> 2;

    if (v.y <= 0) {
        g_ab.speedCap -= 22 * Sin256(0x50 - g_ab.angle);
        if (g_ab.speedCap < 0x40000)
            g_ab.speedCap = 0x40000;
    }
    else if (v.y > g_ab.speedCap) {
        g_ab.speedCap = v.y - (v.y >> 6);
    }

    if (v.x) {
        int push = (22 * Sin256(0x50 - g_ab.angle)) >> (water ? 1 : 0);
        if (g_ab.glideLeft) {
            v.x -= push;
            v.x = std::min(v.x, -0x10000);
            v.x = std::max(v.x, -g_ab.speedCap);
        }
        else {
            v.x += push;
            v.x = std::max(v.x, 0x10000);
            v.x = std::min(v.x, g_ab.speedCap);
        }
    }

    bool forward = g_ab.glideLeft ? p->left : p->right;
    bool back = g_ab.glideLeft ? p->right : p->left;
    if (!back || g_ab.angle != 0x10) {
        if (forward && g_ab.angle == 0x70 && g_ab.glideUp) {  // tip over into a dive
            g_ab.lift = 0;
            g_ab.glideUp = false;
            PlayExtraAnimation(p, ANI_EXTRA_GLIDE_DOWN, false, true);
        }
    }
    else if (!g_ab.glideUp) {  // back held at the bottom of a dive: swoop up
        g_ab.glideUp = true;
        if (v.y > 0x28000 || g_ab.swoopPower == 256 || (water && v.y > 0x18000)) {
            int speed = std::abs(v.x);
            g_ab.lift = -((g_ab.swoopPower * ((speed >> 1) + (speed >> 2) + (speed >> 4))) >> 8);
            if (water)
                g_ab.lift = (g_ab.lift >> 1) + (g_ab.lift >> 3);
            if (g_ab.swoopPower > 16)
                g_ab.swoopPower -= 32;  // each swoop is weaker than the last
            if (g_ab.lift < -0x60000)
                g_ab.lift = -0x60000;
        }
        PlayExtraAnimation(p, ANI_EXTRA_GLIDE_UP, false, true);
    }
    if (!g_ab.glideUp)
        PlayExtraAnimation(p, ANI_EXTRA_GLIDE_DOWN, false, false);
    else
        PlayExtraAnimation(p, ANI_EXTRA_GLIDE_UP, false, false);

    if (!p->jumpHold || std::abs(v.x) < 0x10000) {  // let go of jump, or too slow: curl up and fall
        g_ab.glide = false;
        BackToJump(p);
    }
    p->velocity = v;
}

// A bat's glide (Rouge): Knuckles' own glide, slower and sinking more gently. The game has already moved her
// by his glide's velocity this frame; take back the difference to hers. Her position only moves back along the
// path the game just checked, so it can't put her in a wall. Her sink is her own (from last frame's), like his
// rule with a lower target and a gentler pull: glideSink, glideGravity.
// Only in the player's own states: a cutscene that shows the glide pose while it moves her itself (S&K's Sky
// Sanctuary: Egg Robo drops Knuckles in "PState_Start", anim 71, on a velocity nothing keeps up, till he reaches a
// set x) would otherwise lose 30% of that velocity each frame and never get there, holding her for good.
static void BatGlide(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    bool gliding = air && p->animator.animationID == ANI_KNUX_GLIDE && !Held(p);
    if (gliding && g_ab.batGlide) {
        Vector2 v = p->velocity;
        int x = (int)((long long)v.x * c.glideSpeed / 1000);
        p->position.x -= v.x - x;
        p->velocity.x = x;
        if (v.y >= 0) {
            int y = g_ab.batVY > c.glideSink ? g_ab.batVY - 0x2000 : g_ab.batVY + c.glideGravity;
            y = std::max(0, std::min(y, v.y));  // never sinking faster than his
            p->position.y -= v.y - y;
            p->velocity.y = y;
        }
    }
    else if (g_ab.batGlide && !air) {  // landed out of the glide: slide at her speed, not his
        p->groundVel = (int)((long long)p->groundVel * c.glideSpeed / 1000);
        p->velocity.x = (int)((long long)p->velocity.x * c.glideSpeed / 1000);
    }
    g_ab.batGlide = gliding;
    g_ab.batVY = p->velocity.y;
}

// Rouge's Screw Kick: Y in mid-air, or out of Knuckles' glide, dives 45 degrees down and forward (the direction
// locked) until she lands, attacking the whole way; landing bounces her up a little. Once per airborne period.
// A spring or anything else sending her up ends it. Runs after the game's update, so the air state's gravity
// and air control come on top of the kick's speed each frame (as with the other moves here).
// kickOnJump (Mecha Sonic's Spike Ball): the jump ability starts it instead (`trigger`, once per jump), and with no
// kickBounce he just lands.
static void PlaySound(const char* path);  // (below)
static void ScrewKick(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air, bool facingLeft) {
    int a = p->animator.animationID;
    bool gliding = Extra(g_character).base == 2 && (a == ANI_KNUX_GLIDE || a == ANI_KNUX_GLIDE_DROP);
    bool airState = (void*)p->state.state == g_playerStateAir;
    bool start = c.kickOnJump ? g_playerStateAir && air && !g_ab.kick && trigger && airState && !Hurt(p)
                              : g_playerStateAir && air && !g_ab.kick && !g_ab.kickUsed && (airState || gliding) && !Hurt(p)
                                    && YPressed(p);
    if (start) {
        g_ab.kick = g_ab.kickUsed = true;
        g_ab.kickLeft = facingLeft;
        // out of the glide for good, as the glide leaves it; the jump ability used (kickOnJump)
        g_ab.kickJumpState = gliding || c.kickOnJump ? 0 : p->jumpAbilityState;
        if (gliding)
            p->state.state = (void(__fastcall*)())g_playerStateAir;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        if (c.kickSound)
            PlaySound(c.kickSound);
        Log("screw kick%s", gliding ? " (out of the glide)" : c.kickOnJump ? " (by jump)" : "");
    }
    else if (g_ab.kick && !air && c.kickBounce == 0) {  // landed, no bounce: the game lands him from the jump ball
        BackToJump(p);
        g_ab.kick = false;
        g_ab.kickUsed = true;
    }
    else if (g_ab.kick) {
        if (!air) {  // landed: a small bounce, along the ground's angle (as the Hammer Drop's)
            int a8 = p->angle & 0xFF;
            p->velocity.x = (int)(((long long)p->groundVel * Cos256(a8) + (long long)c.kickBounce * Sin256(a8)) >> 8);
            p->velocity.y = (int)(((long long)p->groundVel * Sin256(a8) - (long long)c.kickBounce * Cos256(a8)) >> 8);
            p->onGround = false;
            p->angle = 0;
            p->collisionMode = 0;  // floor
            p->state.state = (void(__fastcall*)())g_playerStateAir;
            BackToJump(p);
            g_ab.kick = false;
            g_ab.kickUsed = true;  // (landing cleared it this frame): no second kick in the bounce
        }
        else if ((void*)p->state.state != g_playerStateAir) {  // an object took over (or landed her on it)
            g_ab.kick = false;
        }
        else if (p->velocity.y <= 0x10000) {  // a spring or anything else sending her up ends it
            g_ab.kick = false;
            p->jumpAbilityState = g_ab.kickJumpState;
            BackToJump(p);
        }
        else {
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
        }
    }
    if (g_ab.kick) {
        p->jumpAbilityState = 0;  // no glide out of the kick
        p->direction = g_ab.kickLeft ? 1 : 0;
        p->velocity.x = g_ab.kickLeft ? -c.kickX : c.kickX;
        p->velocity.y = c.kickY;
    }
}

// After a Bomb Jump or an Ear Grapple, with hover: holding jump once he's falling, from the jump ball, opens the
// hover (the parachute, the Ear Copter)
static void FallingHover(EntityPlayer* p, const ExtraAbilities& c) {
    bool open = g_ab.hover > 1;
    bool falling = p->velocity.y >= 0 && p->animator.animationID == ANI_JUMP;
    if (p->jumpHold && g_ab.hover <= c.hoverFrames && (open || falling)) {
        p->velocity.y = c.hoverSink;
        PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
        g_ab.hover++;
    } else if (open) {  // let go: no more hover this jump
        BackToJump(p);
        g_ab.hover = 0;
    }
}

// Is there solid terrain (the floor or the ceiling side of a tile, on his collision plane) at this offset from him, in
// px? The engine's own ObjectTileCollision, not moving him (setPos false).
static bool TerrainAt(EntityPlayer* p, int x, int y) {
    constexpr uint8 CMODE_FLOOR = 0, CMODE_ROOF = 2;
    return RSDK->ObjectTileCollision(p, p->collisionLayers, CMODE_FLOOR, p->collisionPlane, x << 16, y << 16, false)
           || RSDK->ObjectTileCollision(p, p->collisionLayers, CMODE_ROOF, p->collisionPlane, x << 16, y << 16, false);
}

// Max's Ear Grapple, as in S1/S2 (abilities.py ear_grapple): his ear shoots out 45 degrees up and forward, a frame at a
// time (tipX / tipY: its tip per frame, from the art), and he stops falling meanwhile. A tip in solid terrain latches:
// he's reeled in toward the point (gravity off) until he's close or out of time, then let go with a small hop, still
// moving forward. With nothing there the ear snaps back. Landing, springs, hurt and the Ear Jab end it. Runs after the
// game's update, so the velocities set here move him next frame, after the air state's gravity (taken off in advance).
// Rebuilt on Ristar's Grab (StarGrab.h; the user, 2026-09-30): the ear frames' outer box used to reach out to the tip,
// and the game collides that box with the terrain, so the ear fought the pull. Now the frames have his own boxes; the
// tip hits badniks, monitors and bosses through Player_CheckBadnikTouch (EarTouch, as Ristar's hands) and snaps back;
// the pull lets go when he's close, out of time or stopped by the terrain (Ristar's test), and a slope he touches down
// on doesn't end it while the point is well above (Ristar's pull on the ground lifts him off).
static Vector2 g_earTip{};   // the ear's tip this frame, while it goes out (EarTouch)
static Vector2 g_earLast{};  // his position last frame (a pull stopped by the terrain)
static void EarGrapple(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    // grappleY (Max, the user's rework 2026-09-29): jump in mid-air opens the Ear Copter at once, and Y in mid-air starts
    // the grapple (from the jump, the Ear Copter or a fall), once per airborne period, from the air state only
    if (c.grappleY) {
        if (trigger && g_ab.ear <= 0 && c.hover) {
            g_ab.hover = 2;  // open (FallingHover keeps it open while jump is held)
            p->velocity.y = c.hoverSink;
            PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, true);
            Log("ear copter");
        }
        trigger = false;
        if (!air) {
            g_ab.earUsed = false;
            g_ab.earWait = 0;
        } else if (g_ab.earWait > 0 && g_ab.ear <= 0) {
            --g_ab.earWait;  // grappleRefill: the cooldown after a pull, once the ear's in
        }
        if (air && !g_ab.earUsed && g_ab.earWait <= 0 && g_ab.ear <= 0 && g_playerStateAir
            && (void*)p->state.state == g_playerStateAir && !Hurt(p) && YPressed(p)) {
            g_ab.earUsed = true;
            trigger = true;
        }
    }
    Vector2 last = g_earLast;
    g_earLast = p->position;
    if (!trigger && !air && g_ab.ear > 100 && g_ab.ear < 200 && p->onGround && !Hurt(p) && !Held(p)
        && g_ab.latch.y - p->position.y < -(12 << 16)) {
        int a = p->animator.animationID;  // (touched down on a slope while pulled: the game's landing poses)
        if (a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1)) {
            p->onGround = false;  // a point well above lifts him off (Ristar's PullTo)
            p->angle = 0;
            p->collisionMode = 0;
            p->state.state = (void(__fastcall*)())g_playerStateAir;
            p->velocity.x = 0;
            p->velocity.y = -0x10000;
            p->groundVel = 0;
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
            air = true;
        }
    }
    if (trigger) {
        g_ab.ear = 1;
        g_ab.earLeft = p->direction & 1;
        g_ab.hover = 0;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        Log("ear grapple");
    } else if (g_ab.ear > 0 && (!air || p->animator.animationID != ANI_JUMP || g_ab.shot > 0)) {
        if (c.grappleRefill && g_ab.ear > 100 && g_ab.ear < 200)
            g_ab.earUsed = false;  // latched: the grab's back (a spring or a hit during the pull)
        g_ab.ear = 0;  // landed, a spring, hurt, the Ear Jab (also shown as the jump): no Ear Copter this jump
    }
    if (g_ab.ear <= 0) {
        if (air && g_ab.hover > 0)
            FallingHover(p, c);
        return;
    }
    const int n = c.grappleFrames;
    const int side = g_ab.earLeft ? -1 : 1;
    p->direction = g_ab.earLeft ? 1 : 0;  // air control would turn him (and the ear) around
    int frame = 0;
    if (g_ab.ear > 200) {  // snapping back, shorter each frame
        frame = (g_ab.ear - 201) * (n / c.snapFrames);
        if (--g_ab.ear == 200) {
            g_ab.ear = 0;
            g_ab.hover = c.hover ? 1 : 0;
            BackToJump(p);
            return;
        }
    } else if (g_ab.ear > 100) {  // latched and reeling in
        int dx = (g_ab.latch.x - p->position.x) >> 16, dy = (g_ab.latch.y - p->position.y) >> 16;
        bool stopped = g_ab.ear > 102 && std::abs(p->position.x - last.x) < 0x8000
                       && std::abs(p->position.y - last.y) < 0x8000;  // stopped by the terrain (Ristar's test)
        if (g_ab.ear >= 100 + c.reelFrames || (std::abs(dx) < c.latchRange && std::abs(dy) < c.latchRange) || stopped) {
            p->velocity.x = side * c.grappleForward;  // there: a small hop, still moving forward
            p->velocity.y = -c.grappleHop;
            if (c.grappleRefill) {  // a latch gives the grab back, after the cooldown (the user, 2026-09-30)
                g_ab.earUsed = false;
                g_ab.earWait = c.grappleCooldown;
            }
            g_ab.ear = 0;
            g_ab.hover = c.hover ? 1 : 0;
            BackToJump(p);
            return;
        }
        g_ab.ear++;
        for (int k = 1; k < n; k++)  // the longest ear that doesn't reach past the latch point
            if (c.tipX[k] <= dx * side && c.tipY[k] >= dy)
                frame = k;
    } else {  // the ear going out: does its tip reach solid ground?
        frame = g_ab.ear - 1;
        int tx = side * c.tipX[frame], ty = c.tipY[frame];
        g_earTip = {p->position.x + (tx << 16), p->position.y + (ty << 16)};
        if (TerrainAt(p, tx, ty)) {
            g_ab.latch = {p->position.x + (tx << 16), p->position.y + (ty << 16)};
            g_ab.ear = 101;
            Log("ear grapple latched");
        } else {
            if (p->velocity.y > -Gravity(p))  // he stops falling
                p->velocity.y = -Gravity(p);
            if (++g_ab.ear > n)  // full reach, nothing there
                g_ab.ear = 200 + c.snapFrames;
        }
    }
    if (g_ab.ear > 100 && g_ab.ear < 200) {  // reeled in along the line to the latch point
        double dx = g_ab.latch.x - p->position.x, dy = g_ab.latch.y - p->position.y, len = std::sqrt(dx * dx + dy * dy);
        if (len > 0) {
            p->velocity.x = (int)(c.reelSpeed * dx / len);
            p->velocity.y = (int)(c.reelSpeed * dy / len) - Gravity(p);
        }
    }
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
    p->animator.frameID = frame;  // the code picks the frame
    p->animator.timer = 0;
}

// Player_CheckBadnikTouch (the shots' hook): while the Ear Grapple's ear goes out, a badnik, monitor or boss its tip
// reaches (8 px round it, in its hitbox) is touched (his attack: he's shown as the jump) and the ear snaps back
static bool EarTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox) {
    if (g_character <= 0 || !p || !e || !hitbox || g_ab.ear <= 0 || g_ab.ear >= 100 || RSDK->GetEntitySlot(p) != 0
        || !Extra(g_character).abilities.earGrapple)
        return false;
    int hx = (g_earTip.x - e->position.x) >> 16, hy = (g_earTip.y - e->position.y) >> 16;
    if (hx < hitbox->left - 8 || hx > hitbox->right + 8 || hy < hitbox->top - 8 || hy > hitbox->bottom + 8)
        return false;
    g_ab.ear = 200 + Extra(g_character).abilities.snapFrames;
    if (Extra(g_character).abilities.grappleRefill) {  // a hit gives the grab back, after the cooldown
        g_ab.earUsed = false;
        g_ab.earWait = Extra(g_character).abilities.grappleCooldown;
    }
    Log("ear grapple: the ear hit slot %d", RSDK->GetEntitySlot(e));
    return true;
}

static int Approach(int v, int target, int step) {
    return v < target ? std::min(v + step, target) : std::max(v - step, target);
}

// Tikal's Spirit Flight, as in S1/S2 (abilities.py spirit_flight): jump in mid-air turns her into a spirit orb, held
// still for the transform's frames (the code picks them), then she flies where the d-pad points (8 directions) for
// spiritFrames, the orb's own velocity easing toward it, and the orb's loop runs. It attacks (shown to the game as
// the jump). Runs after the game's update, so the velocity set here moves her next frame, after the air state's
// gravity (taken off in advance; its air control, a few percent of her speed, isn't), and the game's collision
// still stops her at walls. Landing, a hit (which clears it with everything else), a spring or an object taking
// over ends it with their speed; running out of time or jump pressed again re-forms her, not shooting up.
static void SpiritFlight(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    const int total = c.spiritTransform * c.spiritTicks + c.spiritFrames;
    Vector2& v = g_ab.spiritVel;
    if (trigger) {
        g_ab.spirit = total;
        v = {0, 0};
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        Log("spirit flight");
    } else if (g_ab.spirit > 0) {
        if (!air || p->animator.animationID != ANI_JUMP) {  // landed (the game picks her pose), a spring...
            g_ab.spirit = 0;
            return;
        }
        if (p->velocity.x == 0)  // a wall stopped her (the game's collision): the orb too
            v.x = 0;
        if (p->velocity.y == 0 && v.y < 0)  // a ceiling
            v.y = 0;
        if (--g_ab.spirit == 0 || (g_ab.spirit <= c.spiritFrames && p->jumpPress)) {  // she re-forms
            g_ab.spirit = 0;
            BackToJump(p);
            p->velocity.x = v.x;
            p->velocity.y = std::max(v.y, 0);
            return;
        }
    }
    if (g_ab.spirit <= 0)
        return;
    bool flying = g_ab.spirit <= c.spiritFrames;
    if (flying) {
        int speed = (p->left || p->right) && (p->up || p->down) ? c.spiritDiag : c.spiritSpeed;  // diagonals: the same speed overall
        v.x = Approach(v.x, p->left ? -speed : p->right ? speed : 0, c.spiritAccel);
        v.y = Approach(v.y, p->up ? -speed : p->down ? speed : 0, c.spiritAccel);
    } else {
        v = {0, 0};
    }
    p->velocity.x = v.x;
    p->velocity.y = v.y - Gravity(p);
    NoJumpCap(p);  // underwater the cap is lower than her rise
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
    if (g_ab.spirit >= c.spiritFrames) {  // the transform, then the orb's first frame; the loop runs from there
        p->animator.frameID = std::min((total - g_ab.spirit) / c.spiritTicks, c.spiritTransform);
        p->animator.timer = 0;
    }
}

// Sparkster's Rocket Burst, as in S1/S2 (abilities.py rocket_burst): the jump press in mid-air starts charging the rocket
// pack while jump is held (he drifts to a stop, falling at rocketSink at most; the attack animation's frame 0, flashing
// with frame 1 once charged: rocketCharge frames). Letting go fires it: where the d-pad points (8 ways) at rocketSpeed
// (rocketDiag per axis diagonally), gravity off, for rocketFrames, a wall or a ceiling that stopped it bouncing it off
// (a ricochet), in the Rocket Dash frame for its angle (2-6); with nothing held the Rocket Spin in place for
// rocketSpinFrames (7-10 in turn). Let go too soon, it fizzles. An attack throughout (shown to the game as the jump).
// Runs after the game's update, so the velocity set here moves him next frame (gravity taken off in advance). Landing,
// a hit (which clears it with everything else), a spring or an object taking over ends it; after the burst he falls
// with half its speed.
static const int ROCKET_CHARGING = 1000;  // (abilities.py ROCKET_CHARGING)
static void RocketBurst(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    Vector2& v = g_ab.rocketVel;
    if (trigger) {
        g_ab.rocket = ROCKET_CHARGING;
        v = {0, 0};
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        if (c.rocketChargeSound)
            PlaySound(c.rocketChargeSound);
        Log("rocket burst: charging");
    } else if (g_ab.rocket > 0) {
        if (!air || p->animator.animationID != ANI_JUMP) {  // landed (the game picks his pose), a spring...
            g_ab.rocket = 0;
            return;
        }
        if (g_ab.rocket < ROCKET_CHARGING) {
            if (v.x != 0 && p->velocity.x == 0)  // a wall stopped it (the game's collision): ricochet
                v.x = -v.x;
            if (v.y < 0 && p->velocity.y == 0)  // a ceiling
                v.y = -v.y;
            if (--g_ab.rocket == 0) {  // over: he falls from here, with half its speed
                BackToJump(p);
                p->velocity.x = v.x / 2;
                p->velocity.y = v.y / 2;
                return;
            }
        } else {
            if (g_ab.rocket < ROCKET_CHARGING + 0x4000)
                g_ab.rocket++;
            if (!p->jumpHold) {  // let go: fire
                if (g_ab.rocket < ROCKET_CHARGING + c.rocketCharge) {  // too soon: it fizzles
                    g_ab.rocket = 0;
                    BackToJump(p);
                    return;
                }
                int dx = p->left ? -1 : p->right ? 1 : 0, dy = p->up ? -1 : p->down ? 1 : 0;
                int speed = dx && dy ? c.rocketDiag : c.rocketSpeed;  // diagonals: the same speed overall
                v = {dx * speed, dy * speed};
                g_ab.rocket = std::max(1, dx || dy ? c.rocketFrames : c.rocketSpinFrames);
                if (c.rocketSound)
                    PlaySound(c.rocketSound);
                Log(dx || dy ? "rocket burst: %d, %d" : "rocket burst: spin", dx, dy);
            }
        }
    }
    if (g_ab.rocket <= 0)
        return;
    int frame = 0;
    if (g_ab.rocket >= ROCKET_CHARGING) {  // charging: drifting to a stop, falling slowly
        p->velocity.x -= p->velocity.x / 16;
        if (p->velocity.y > c.rocketSink - Gravity(p))
            p->velocity.y = c.rocketSink - Gravity(p);
        if (g_ab.rocket >= ROCKET_CHARGING + c.rocketCharge)  // charged: it flashes
            frame = (g_ab.rocket >> 2) & 1;
    } else {
        p->velocity.x = v.x;
        p->velocity.y = v.y - Gravity(p);
        NoJumpCap(p);
        if (v.x != 0)
            p->direction = v.x < 0 ? 1 : 0;
        if (v.x == 0 && v.y == 0)  // the Rocket Spin: its frames in turn
            frame = 7 + ((c.rocketSpinFrames - g_ab.rocket) / std::max(1, c.rocketSpinTicks)) % 4;
        else  // the Rocket Dash for its angle: down, down-forward, forward, up-forward, up
            frame = v.y > 0 ? (v.x ? 3 : 2) : v.y < 0 ? (v.x ? 5 : 6) : 4;
    }
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
    if (p->animator.frameCount > frame) {  // the code picks the frame
        p->animator.frameID = frame;
        p->animator.timer = 0;
    }
}

// Mario's Triple Jump, as in S1/S2 (abilities.py triple_jump): a jump within tripleWindow frames of landing from the
// last one, running (ground speed at least tripleSpeed), is the next of a chain of three. The 2nd and 3rd go higher
// (triple2 / triple3: the jump strength's multipliers) and the 3rd somersaults (the attack animation, shown to the game
// as the jump) until he starts falling; then the chain starts over. Rolling or a hit (which clears g_ab) breaks it.
// `jumped`: the game started a jump this frame (jumpAbilityState went to 1). It has already moved him by the jump's
// velocity once by then, so the extra strength goes on from the next frame, along the ground's angle as the game's
// own jump adds its strength (the angle and ground speed from before the jump: last frame's).
static void TripleJump(EntityPlayer* p, const ExtraAbilities& c, bool jumped, bool air) {
    static int lastGroundVel = 0, lastAngle = 0;
    static bool wasGrounded = false;  // last frame: on the ground, outside the air state (as RollCurl)
    bool grounded = p->onGround && (void*)p->state.state != g_playerStateAir;
    if (grounded && wasGrounded && p->animator.animationID == ANI_JUMP && g_ab.shot == 0)
        g_ab.chain = 0;  // rolling (not the Fireball, also shown as the jump): a jump out of it starts a new chain
    wasGrounded = grounded;

    if (jumped && p->animator.animationID == ANI_JUMP && p->velocity.y < 0) {  // (not a spring)
        if (std::abs(lastGroundVel) < c.tripleSpeed || g_ab.chain >= 3)
            g_ab.chain = 0;  // too slow, or after the third: a first jump
        g_ab.chain++;
        int m = g_ab.chain == 2 ? c.triple2 : g_ab.chain == 3 ? c.triple3 : 1000;
        if (m != 1000) {
            int strength = *(int*)((char*)p + 0x248);  // jumpStrength (PHYSICS)
            long long more = (long long)strength * (m - 1000) / 1000;
            int a = lastAngle & 0xFF;
            p->velocity.x += (int)((more * Sin256(a)) >> 8);
            p->velocity.y -= (int)((more * Cos256(a)) >> 8);
            Log("triple jump %d", g_ab.chain);
        }
    }

    // the chain stays open while he's in the air from a jump (the jump pose, the somersault or the Fireball, all shown
    // to the game as the jump), and for tripleWindow frames after
    if (air && p->animator.animationID == ANI_JUMP)
        g_ab.chainWindow = c.tripleWindow;
    else if (g_ab.chainWindow > 0)
        g_ab.chainWindow--;
    else
        g_ab.chain = 0;

    if (g_ab.chain == 3) {  // the third jump: the somersault until he starts falling (a spring, a hit or the Fireball end it)
        bool jumpShown = p->animator.animationID == ANI_JUMP && g_ab.shot == 0;
        if (air && p->velocity.y < 0 && jumpShown) {
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, jumped);
        } else {
            g_ab.chain = 4;
            if (air && jumpShown)
                BackToJump(p);
        }
    }
    lastGroundVel = p->groundVel;
    lastAngle = p->angle;
}

// Trip's Double Jump, as in S1/S2 (abilities.py double_jump): jump in mid-air is a second jump at doubleJumpScale of
// her jump strength, keeping her speed along, in the shell spin (shown to the game as the jump: it attacks) until she
// starts falling. Once per jump (`ready`); a wall cling gives it back. The velocity moves her next frame, after the
// air state's gravity (taken off in advance).
static void DoubleJump(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    if (trigger) {
        int strength = *(int*)((char*)p + 0x248);  // jumpStrength (PHYSICS)
        p->velocity.y = -(int)((long long)strength * c.doubleJumpScale / 1000) - Gravity(p);
        g_ab.doubleJump = true;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        Log("double jump");
    } else if (g_ab.doubleJump) {
        if (!air || p->animator.animationID != ANI_JUMP) {  // landed (the game picks her pose), a spring, a wall...
            g_ab.doubleJump = false;
        } else if (p->velocity.y >= 0) {  // falling: the jump ball again
            g_ab.doubleJump = false;
            BackToJump(p);
        } else {
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
        }
    }
}

// Chaos' Puddle Slide, as in S1/S2 (abilities.py puddle_slide): jump in mid-air drops him in the dive (an attack: the
// game sees the Jump animation); landing from it he melts into a puddle, slides and rises (the extra's slot 1, the
// frame per step from puddleFrames), at least puddleSpeed the way he faces for puddleMove steps, then slowing to a stop.
// Meanwhile nothing hurts him: the post-hit blink timer (found in-game: FindBlinkTimer) held at 3 at least, under the 4
// that makes him flicker; and Y doesn't punch (the shot's cooldown held). A jump, a roll, a crouch, a spring, a ledge or
// a hit ends it. Runs before the shot, whose cooldown it holds.
// groundStart (Ray Poward's Slide, abilities.py ground_slide): the puddle's ground part starts at once, no drop (a crouch's
// jump press, which NoRollInput took from the game's Spin Dash).
static void PuddleSlide(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air, bool groundStart = false) {
    const int steps = std::min(std::max(c.puddleSteps, 1), (int)(sizeof(c.puddleFrames) / sizeof(c.puddleFrames[0])));
    const int ticks = std::max(c.puddleTicks, 1), total = steps * ticks;
    bool landed = false;
    if (groundStart && !air && !Hurt(p)) {
        g_ab.puddleDrop = false;
        g_ab.puddle = total;
        landed = true;
        if (c.puddleSound)
            PlaySound(c.puddleSound);
        Log("slide");
    } else if (trigger) {
        if (p->velocity.y < c.puddleDrop)
            p->velocity.y = c.puddleDrop;
        g_ab.puddleDrop = true;
        g_ab.puddle = 0;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        Log("puddle drop");
    } else if (g_ab.puddleDrop) {
        if (!air) {  // landed from the drop: melt
            g_ab.puddleDrop = false;
            if (!Hurt(p)) {
                g_ab.puddle = total;
                landed = true;
                if (c.puddleSound)
                    PlaySound(c.puddleSound);
                static bool warned = false;
                if (g_blinkOffset < 0 && !warned)
                    Log("puddle slide: the blink timer isn't known yet (get hit once): he can be hurt in the puddle");
                warned = true;
            }
        } else if (p->animator.animationID != ANI_JUMP || p->velocity.y <= 0x10000) {
            g_ab.puddleDrop = false;  // a spring, a badnik bounce, a hit...
            if (p->animator.animationID == ANI_JUMP)
                BackToJump(p);
        } else {
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
        }
    }
    if (g_ab.puddle <= 0)
        return;
    int a = p->animator.animationID;
    // (the landing frame still shows the dive, reported as Jump; later a Jump there is a roll)
    if (air || Hurt(p) || (!landed && (a == ANI_JUMP || a == ANI_CROUCH))) {
        g_ab.puddle = 0;
        return;
    }
    g_ab.puddle--;
    int step = std::min((total - g_ab.puddle - 1) / ticks, steps - 1);
    PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
    p->animator.frameID = c.puddleFrames[step];  // the timer picks the frame
    p->animator.timer = 0;
    if (step < c.puddleMove) {  // melting and sliding
        int dir = (p->direction & 1) ? -1 : 1;
        p->groundVel = std::max(p->groundVel * dir, c.puddleSpeed) * dir;
    } else {  // rising: slowing to a stop
        p->groundVel -= p->groundVel >> 2;
    }
    if (g_blinkOffset >= 0) {  // nothing hurts him (without the flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    g_ab.cooldown = std::max(g_ab.cooldown, 2);  // and Y doesn't punch
    if (g_ab.puddle == 0)  // risen
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
}

// Is there a wall right beside her, on her left or right? Tested where Knuckles' glide grabs one in S1/S2 (wallX px
// out, wallY down; abilities.py WALL_X / WALL_Y), with the engine's own ObjectTileCollision, not moving her. A wall on
// her right is a tile's left side (CMODE_LWALL), as the game's own wall checks go.
static bool WallBeside(EntityPlayer* p, const ExtraAbilities& c, bool left) {
    constexpr uint8 CMODE_LWALL = 1, CMODE_RWALL = 3;
    return RSDK->ObjectTileCollision(p, p->collisionLayers, left ? CMODE_RWALL : CMODE_LWALL, p->collisionPlane,
                                     (left ? -c.wallX : c.wallX) << 16, c.wallY << 16, false);
}

// Off the wall, in the jump ball, with the Double Jump ready again; that wall locked for a moment
static void LetGoOfWall(EntityPlayer* p, const ExtraAbilities& c) {
    g_ab.cling = 0;
    g_ab.clingLock = c.clingLock;
    g_ab.ready = true;
    BackToJump(p);
}

// Trip's Wall Cling, as in S1/S2 (abilities.py wall_cling): in the air state, from a jump, a fall or the Double Jump,
// holding toward a wall right beside her grabs it. She's held there (gravity taken off in advance, the pose facing the
// wall), sliding down slowly after clingHold, for up to clingFrames; up / down climb, and climbing past the wall's top
// hops her up onto the ledge. Jump kicks off away from the wall, letting go of toward drops her. Landing, a hit (which
// clears it with everything else), a spring or an object taking over ends it. The wall she let go of takes clingLock
// frames away from it before she can grab it again.
static void WallCling(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    bool airState = g_playerStateAir && (void*)p->state.state == g_playerStateAir;
    if (!air)
        g_ab.clingLock = 0;
    else if (g_ab.clingLock > 0 && g_ab.cling == 0 && !WallBeside(p, c, g_ab.clingLeft))
        g_ab.clingLock--;  // counting down only while she's away from it

    if (g_ab.cling > 0) {
        if (!air || !airState || p->animator.animationID != ANI_EXTRA_CLING) {  // the game picks her pose
            g_ab.cling = 0;
            return;
        }
        const bool left = g_ab.clingLeft;
        g_ab.cling++;
        if (p->jumpPress) {  // a wall jump: kick off away from it
            LetGoOfWall(p, c);
            p->velocity.x = left ? c.wallJumpX : -c.wallJumpX;
            p->velocity.y = -c.wallJumpY - Gravity(p);
            p->direction = left ? 0 : 1;
            *(int32*)p->padding6 = true;  // letting go of jump cuts it short, as with a jump (NoJumpCap's field)
            Log("wall jump");
            return;
        }
        bool wall = WallBeside(p, c, left);
        if (!wall || !(left ? p->left : p->right) || g_ab.cling > c.clingFrames) {  // the wall ends, let go, out of time
            LetGoOfWall(p, c);
            if (!wall && p->up) {  // climbed to its top: a hop up onto the ledge, toward it
                p->velocity.x = left ? -c.ledgeForward : c.ledgeForward;
                p->velocity.y = -c.ledgeHop - Gravity(p);
                NoJumpCap(p);
            }
            return;
        }
        int vy = g_ab.cling > c.clingHold ? c.clingSlide : 0;  // held still, then sliding down slowly
        if (p->up)  // climbing (the game's collision stops her at a floor or a ceiling)
            vy = -c.climbSpeed;
        else if (p->down)
            vy = c.climbSpeed;
        p->velocity.x = 0;
        p->velocity.y = vy - Gravity(p);
        p->direction = left ? 1 : 0;  // facing the wall (air control would turn her)
        PlayExtraAnimation(p, ANI_EXTRA_CLING, false, false);
        return;
    }

    // grabbing a wall: pushing toward one side, not the wall she just let go of
    int anim = p->animator.animationID;
    bool pose = anim == ANI_JUMP || (anim >= ANI_WALK && anim <= ANI_DASH);  // jumping (the Double Jump too); falling (Walk..Dash)
    if (!air || !airState || !pose || p->left == p->right)
        return;
    bool left = p->left;
    if (g_ab.clingLock > 0 && left == g_ab.clingLeft)
        return;
    if (!WallBeside(p, c, left))
        return;
    g_ab.cling = 1;
    g_ab.clingLeft = left;
    g_ab.doubleJump = false;
    p->velocity.x = 0;
    p->velocity.y = -Gravity(p);
    p->direction = left ? 1 : 0;
    PlayExtraAnimation(p, ANI_EXTRA_CLING, false, true);
    Log("wall cling");
}

// A character's own sound (character.json "sounds", tools/own_sounds.py): the build writes it as "NoSwap/<id>/<name>.wav"
// and ships it in the package at Sonic3ku/Data/SoundFX/<that path>. Origins plays S3&K's sounds from its own CRI banks,
// never from files (GetSfx only finds the sounds Origins knows), so the DLL plays it itself: winmm's PlaySoundW, from
// memory, asynchronously (a new own sound cuts one still playing; the game's own sounds go on). Each file is read once
// (up to ReadWholeFile's 1 MB) and kept, as PlaySoundW plays from that memory. At the system's volume (not the game's
// sound effects slider). -> false for any other path.
static std::wstring Widen(const std::string& s);                            // (below)
static bool ReadWholeFile(const std::wstring& path, std::string& text);    // (below)
// A package's own sound file (its root + Sonic3ku\Data\SoundFX\ + path), read once and kept (PlaySoundW plays from that
// memory): -> its bytes, empty when missing or not a WAV. Under a lock: Sonic 1/2/CD's sounds come from the probe thread
// (OwnSoundMailbox), S3&K's from the game's.
static SRWLOCK g_ownFilesLock = SRWLOCK_INIT;
static const std::string& OwnSoundBytes(const std::wstring& root, const char* path) {
    static std::map<std::wstring, std::string> files;  // its file -> its bytes ("": missing)
    std::wstring file = root + L"Sonic3ku\\Data\\SoundFX\\" + Widen(path);
    for (auto& ch : file)
        if (ch == L'/')
            ch = L'\\';
    AcquireSRWLockExclusive(&g_ownFilesLock);
    auto it = files.find(file);
    if (it == files.end()) {
        std::string bytes;
        if (!ReadWholeFile(file, bytes) || bytes.size() < 44 || bytes.compare(0, 4, "RIFF") != 0)
            bytes.clear();
        Log("own sound %s: %s (%u bytes)", path, bytes.empty() ? "missing or not a WAV: silent" : "read",
            (unsigned)bytes.size());
        it = files.emplace(file, std::move(bytes)).first;  // (a std::map: the entry never moves, the reference stays good)
    }
    ReleaseSRWLockExclusive(&g_ownFilesLock);
    return it->second;
}

// Play a package's own sound (root: its folder) -> false when its file is missing or PlaySoundW isn't there
static bool PlayOwnFrom(const std::wstring& root, const char* path) {
    typedef BOOL(WINAPI * PlaySoundWFn)(LPCWSTR, HMODULE, DWORD);
    const DWORD OWN_SND_ASYNC = 0x0001, OWN_SND_NODEFAULT = 0x0002, OWN_SND_MEMORY = 0x0004;  // (mmsystem.h's SND_*)
    static PlaySoundWFn play = [] {
        HMODULE winmm = LoadLibraryW(L"winmm.dll");
        PlaySoundWFn f = winmm ? (PlaySoundWFn)GetProcAddress(winmm, "PlaySoundW") : nullptr;
        if (!f)
            Log("own sounds: winmm's PlaySoundW not found: they stay silent");
        return f;
    }();
    const std::string& bytes = OwnSoundBytes(root, path);
    if (bytes.empty() || !play)
        return false;
    play((LPCWSTR)bytes.data(), nullptr, OWN_SND_MEMORY | OWN_SND_ASYNC | OWN_SND_NODEFAULT);
    return true;
}

static bool PlayOwnSound(const char* path) {
    if (strncmp(path, "NoSwap/", 7) != 0)
        return false;
    if (const RosterEntry* e = RosterOf(g_character))
        PlayOwnFrom(e->root, path);
    return true;
}

// One of the game's sounds, by its file (Data/SoundFX), or the character's own (PlayOwnSound)
static void PlaySound(const char* path) {
    if (!path || PlayOwnSound(path))
        return;
    uint16 id = RSDK->GetSfx(path);
    if (id != (uint16)-1)
        RSDK->PlaySfx(id, 0, 0xFF);
}

// Thunder Zip, as in S1/S2 (abilities.py thunder_zip): jump in mid-air, once per jump, is a blink-dash forward in
// a flash. zipFrames at zipSpeed, level and locked to its direction, then her forward speed along (at least zipCarry)
// with gravity back; the pose (an attack, shown to the game as the jump) lasts zipPose frames in all. Runs after the
// game's update, so the velocity set here moves her next frame (the air state's gravity taken off in advance), and the
// game's collision stops her at a wall. Landing, a spring or a hit ends it.
static void ThunderZip(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    if (trigger) {
        bool left = p->direction & 1;
        int forward = std::max(left ? -p->velocity.x : p->velocity.x, c.zipCarry);
        g_ab.zip = c.zipPose;
        g_ab.zipCarry = left ? -forward : forward;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        PlaySound("Global/LightningJump.wav");
        Log("thunder zip");
    } else if (g_ab.zip > 0 && (!air || p->animator.animationID != ANI_JUMP)) {
        g_ab.zip = 0;  // landed (the game picks her pose), a spring...
    }
    if (g_ab.zip <= 0)
        return;
    const int after = c.zipPose - c.zipFrames;
    const bool left = g_ab.zipCarry < 0;
    if (g_ab.zip > after) {  // the zip
        p->velocity.x = left ? -c.zipSpeed : c.zipSpeed;
        p->velocity.y = -Gravity(p);
        p->direction = left ? 1 : 0;
    } else if (g_ab.zip == after) {  // out of it: her speed along, falling as usual
        p->velocity.x = g_ab.zipCarry;
    }
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
    if (--g_ab.zip == 0)
        BackToJump(p);
}

// Jet's Extreme Gear, as in S1/S2 (abilities.py extreme_gear): jump in mid-air, once per jump, snaps him onto his board (an
// attack, shown to the game as the jump: it rams badniks) to surf a fast, shallow glide while jump is held. At least
// gearSpeed forward from the press (kept if he's faster), up to gearTop with forward held; back brakes, and at gearTurn he
// carves round to ride the other way (back up to gearSpeed). Sinking at gearSink at most; up held lifts him, for
// gearLiftFrames per ride. A ride lasts gearFrames at most (when set), then ends as letting go of jump does. Runs after the game's update: velocity.y is what he moved by this frame, and the velocity set
// here moves him next frame, after the air state's gravity (taken off in advance; its air control, a few percent of his
// speed, isn't). The game's collision stops him at a wall, which knocks him off. Letting go of jump, a spring, the shot, a
// hit (which clears it with everything else) or an object taking over ends it; landing too, running on at the board's
// speed, Sonic Riders style.
static void ExtremeGear(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    if (trigger) {
        bool left = p->direction & 1;
        int forward = std::max(left ? -p->velocity.x : p->velocity.x, c.gearSpeed);
        g_ab.gear = true;
        g_ab.gearVel = left ? -forward : forward;
        g_ab.gearLift = c.gearLiftFrames;
        g_ab.gearLeft = c.gearFrames;
        p->velocity.x = g_ab.gearVel;
        p->velocity.y = (p->velocity.y > 0 ? 0 : p->velocity.y / 2) - Gravity(p);  // onto the board: no fall, half a rise
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        if (c.gearSound)
            PlaySound(c.gearSound);
        Log("extreme gear");
        return;
    }
    if (!g_ab.gear)
        return;
    if (!air) {  // landed (the game picks his pose): running on at the board's speed
        p->groundVel = g_ab.gearVel;
        g_ab.gear = false;
        return;
    }
    if (p->animator.animationID != ANI_JUMP || g_ab.shot > 0 || (void*)p->state.state != g_playerStateAir) {
        g_ab.gear = false;  // a spring, the shot, an object took over
        return;
    }
    if (!p->jumpHold || p->velocity.x == 0 || (c.gearFrames > 0 && g_ab.gearLeft <= 0)) {
        g_ab.gear = false;  // let go, a wall, or the ride's time up (gearFrames): off the board, in the jump ball
        BackToJump(p);
        return;
    }
    g_ab.gearLeft--;
    bool left = g_ab.gearVel < 0;
    int s = std::abs(g_ab.gearVel);
    bool forward = left ? p->left : p->right, back = left ? p->right : p->left;
    if (back) {  // braking; slow enough, he carves round to ride the other way
        s -= c.gearBrake;
        if (s <= c.gearTurn) {
            s = c.gearTurn;
            left = !left;
        }
    } else if (s < c.gearSpeed) {  // back up to cruising speed
        s = std::min(s + c.gearRecover, c.gearSpeed);
    } else if (forward && s < c.gearTop) {  // speeding up (a faster start is kept)
        s = std::min(s + c.gearAccel, c.gearTop);
    }
    g_ab.gearVel = left ? -s : s;
    p->direction = left ? 1 : 0;
    p->velocity.x = g_ab.gearVel;
    int vy = p->velocity.y;
    if (p->up && g_ab.gearLift > 0) {  // the nose tilts up: a little lift
        g_ab.gearLift--;
        vy = vy > -c.gearRise ? std::max(vy - c.gearLift, -c.gearRise) : vy + Gravity(p);
    } else {  // sinking slowly
        vy = std::min(vy + Gravity(p), c.gearSink);
    }
    p->velocity.y = vy - Gravity(p);
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
}

// Power Surge, as in S1/S2 (abilities.py power_surge): Y, on the ground or in the air, overcharges her for
// surgeFrames (the surge multipliers on her physics: ApplyPhysics), then surgeCooldown frames before the next.
// Dying ends it.
static void PowerSurge(EntityPlayer* p, const ExtraAbilities& c) {
    int a = p->animator.animationID;
    if (a == ANI_DIE || a == ANI_DROWN)
        g_surge.left = 0;
    if (g_surge.left > 0 && --g_surge.left == c.surgeCooldown)
        Log("power surge over");
    if (g_surge.left == 0 && g_controllers && YPressed(p) && !Hurt(p)) {
        g_surge.left = c.surgeFrames + c.surgeCooldown;
        PlaySound("Global/LightningShield.wav");
        Log("power surge");
    }
}

// While a Power Surge lasts, everything she touches is hit: after her update the animator is reported to the game as
// the jump (as the attacks are, PlayExtraAnimation), so the badniks, monitors and bosses updating after her count it as
// an attack. Her idle / walk / run are shown as the Power Surge ones (their own clock, at the game's animation speed;
// turned like the game's). The game's own animator is kept aside and put back before her next update (SurgeRestore),
// so the game never sees any of it: it picks its animations by comparing frames and IDs, which this would upset.
static void SurgeShow(EntityPlayer* p, const ExtraAbilities& c) {
    const Animator& real = p->animator;
    if (!Surging(c) || Hurt(p) || real.animationID == ANI_JUMP || !real.frames) {  // (the jump already attacks)
        g_surge.variant = -1;
        return;
    }
    int variant = -1;
    switch (real.animationID) {
        case ANI_IDLE: case ANI_BORED_1: case ANI_BORED_2:
            variant = ANI_EXTRA_SURGE_IDLE;
            break;
        case ANI_WALK: case ANI_WALK + 1: case ANI_JOG: case ANI_JOG + 1:  // (+ 1: the "Angled" ones)
            variant = ANI_EXTRA_SURGE_RUN;
            break;
        case ANI_RUN: case ANI_RUN + 1: case ANI_DASH: case ANI_DASH + 1:
            variant = ANI_EXTRA_SURGE_SPRINT;
            break;
        case ANI_PEELOUT: case ANI_PEELOUT + 1:  // (Sonic's file only)
            if (Extra(g_character).base == 0)
                variant = ANI_EXTRA_SURGE_SPRINT;
            break;
    }
    Animator shown = real;
    if (variant >= 0) {
        if (variant != g_surge.variant)
            g_surge.tick = 0;
        RSDK->SetSpriteAnimation(g_extraFrames, variant, &shown, true, 0);
        int count = shown.frameCount, loop = shown.loopIndex < count ? shown.loopIndex : 0;
        g_surge.tick += real.speed > 0 && real.animationID != ANI_IDLE ? real.speed : shown.speed;
        int frame = g_surge.tick / 240;
        if (count > 0 && frame >= count) {
            frame = loop + (frame - loop) % (count - loop);
            g_surge.tick = frame * 240 + g_surge.tick % 240;
        }
        if (count > 0)
            RSDK->SetSpriteAnimation(g_extraFrames, variant, &shown, true, frame);
        shown.rotationStyle = real.rotationStyle;
        shown.prevAnimationID = real.prevAnimationID;
    }
    g_surge.variant = variant;
    g_surge.real = real;
    shown.animationID = ANI_JUMP;
    p->animator = shown;
    g_surge.shown = shown;
    g_surge.mapped = variant >= 0;
    g_surge.swapped = true;
}

// Copy heads (abilities.py copy_heads: Emerl's head per Copycat move). After his update, the idle, bored, walk / fall /
// jog / run / dash / peel out (and their "Angled" ones) and the copy flash (the extra's shot) are drawn from the active
// move's copy of that animation (build_s3k_art.py COPY_HEADS_S3K: the same frames, timing and boxes, another head): only
// the animator's frame list is swapped, and put back before his next update, unless something has set an animation of
// its own since (as SurgeRestore). The game never sees it.
struct CopyHeadState {
    bool swapped;
    void* real;   // the game's frame list
    void* shown;  // the copy's
};
static CopyHeadState g_heads{false, nullptr, nullptr};
constexpr int COPY_HEAD_OFFSET = 12, COPY_HEAD_ANIMS = 15;  // (build_s3k_art.py COPY_HEAD_OFFSET, COPY_HEADS_S3K)

static void CopyHeadShow(EntityPlayer* p, const ExtraAbilities& c) {
    Animator& a = p->animator;
    int id = a.animationID, k = -1;
    if (c.copyHeads <= 0 || !a.frames)
        return;
    if (id == ANI_IDLE || id == ANI_BORED_1)
        k = id;  // 0, 1
    else if (id >= ANI_WALK && id <= ANI_DASH + 1)
        k = 2 + id - ANI_WALK;  // 2-11: Walk, Fall, Jog, Run, Dash and their Angled ones
    else if (id == ANI_PEELOUT || id == ANI_PEELOUT + 1)
        k = 12 + id - ANI_PEELOUT;
    else if (id == ANI_EXTRA_SHOT)
        k = 14;
    if (k < 0)
        return;
    Animator copy{};
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_EXTRA(COPY_HEAD_OFFSET + COPY_HEAD_ANIMS * (g_copy % c.copyHeads) + k),
                             &copy, true, 0);
    if (!copy.frames || copy.frameCount != a.frameCount)  // (an older package without the copies: his own)
        return;
    g_heads = {true, a.frames, copy.frames};
    a.frames = copy.frames;
}

static void CopyHeadRestore(EntityPlayer* p) {
    if (!g_heads.swapped)
        return;
    g_heads.swapped = false;
    if (p->animator.frames == g_heads.shown)
        p->animator.frames = g_heads.real;
}

// Before her update: the game's animator back, unless something (a spring, a pole...) has set one of its own since. If
// the game animates in its late update, that went to the shown one: the game's own catches up here.
static void SurgeRestore(EntityPlayer* p) {
    if (!g_surge.swapped)
        return;
    g_surge.swapped = false;
    Animator& a = p->animator;
    if (a.frames != g_surge.shown.frames || a.animationID != ANI_JUMP)
        return;
    if (!g_surge.mapped) {  // the game's own frames: keep their progress
        a.animationID = g_surge.real.animationID;
        return;
    }
    Animator real = g_surge.real;
    if (a.frameID != g_surge.shown.frameID || a.timer != g_surge.shown.timer)
        RSDK->ProcessAnimation(&real);
    a = real;
}

// Magnetic, as in S1/S2 (abilities.py magnetic): S3&K's rings only follow a lightning shield, so the pull is
// done here, with the same numbers. A placed ring (not moving: lost rings fly out and aren't pulled) within 64 px of her
// box starts drifting to her, the lightning shield's way, and keeps at it (its entity is remembered while it's active);
// the ring itself collects on touch as always.
// Charge (Heavy's; abilities.py charge, S1/S2's charge_after): Y held on the ground, from standing, walking or running,
// pushes him the way he faced when it started, harder the faster he goes (chargeAccel plus chargeGain / 1024 of his speed
// a frame, up to chargeTop), far past his top speed. Let go, he coasts, losing chargeFriction a frame (chargeBrake
// holding back), until he's back at his top speed (the game's field, times his physics: ApplyPhysics): then the game's
// again. An attack throughout (shown to the game as the jump, as the other moves). A wall that stops him (his speed
// under half of what it set, from 2 px per frame up), leaving the ground (a jump keeps the speed), another state (a
// roll, a spring...) or a hit end it. Frames: running (the attack slot), past his top speed the dash flash (the shot
// slot), coasting the slide (the hover slot); one per chargeStride px he covers, forward either way he runs.
// Holding back brakes it (Y held or not: chargeBrake a frame) down to a full stop, never past it: then it's over, he
// stands, and Y must be let go and pressed again for a new one (g_chargeWait).
static bool g_chargeWait = false;
static void Charge(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    bool held = YDown(p);
    if (g_chargeWait) {
        if (held && g_ab.charge == 0)
            return;
        g_chargeWait = false;
    }
    int top = *(int*)((char*)p + 0x220);
    auto end = [&] {
        if (g_ab.charge && !air && p->animator.animationID == ANI_JUMP)  // (ours still showing: the game's run back)
            RSDK->SetSpriteAnimation(g_extraFrames, std::abs(p->groundVel) >= top ? ANI_RUN : ANI_WALK, &p->animator, true, 0);
        g_ab.charge = 0;
        g_ab.chargeAnim = -1;
    };
    if (g_ab.charge == 0) {
        if (air || !held || Hurt(p) || p->down || p->animator.animationID == ANI_JUMP || !p->state.state
            || g_ab.spark != 0)
            return;  // (only from standing, walking or running: not rolling, crouching, in the jump; nor with a Shine
                     // Spark stored or flying)
        g_ab.chargeState = (void*)p->state.state;
        int dir = (p->direction & 1) ? -1 : 1;
        g_ab.charge = dir * std::max({1, dir * p->groundVel, c.chargeShove});  // (the shove: chargeShove at least)
        g_ab.chargeAnim = -1;
        Log("charge");
    }
    if (air || Hurt(p) || (void*)p->state.state != g_ab.chargeState)
        return end();
    int dir = g_ab.charge < 0 ? -1 : 1;
    int v = std::abs(g_ab.charge);
    if (v >= 0x20000 && 2 * dir * p->groundVel < v)  // a wall stopped him
        return end();
    bool brake = dir > 0 ? p->left : p->right;
    if (brake) {
        held = false;  // (the slide's pose)
        v -= c.chargeBrake;
        if (v <= 0) {  // a full stop (never past it into reverse): over, standing
            g_ab.charge = 0;
            g_ab.chargeAnim = -1;
            g_chargeWait = true;
            p->groundVel = 0;
            p->velocity.x = 0;
            RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
            Log("charge: braked to a stop");
            return;
        }
    } else if (held) {
        v = std::min(c.chargeTop, v + c.chargeAccel + (int)((long long)v * c.chargeGain >> 10));
    } else {
        v -= c.chargeFriction;
        if (v <= top)
            return end();
    }
    g_ab.charge = dir * v;
    p->groundVel = dir * v;
    p->direction = dir < 0 ? 1 : 0;
    int anim = !held ? ANI_EXTRA_HOVER : v > top ? ANI_EXTRA_SHOT : ANI_EXTRA_ATTACK;
    PlayExtraAnimation(p, anim, true, anim != g_ab.chargeAnim);
    g_ab.chargeAnim = anim;
    int count = p->animator.frameCount;
    if (count > 0) {
        int f = ((p->position.x >> 16) / std::max(1, c.chargeStride)) % count;
        p->animator.frameID = dir < 0 ? count - 1 - f : f;
    }
    p->animator.timer = 0;
}

// Shine Spark (Heavy's charge; abilities.py "spark_*", S1/S2's spark_after / spark_air), after Charge. At full charge (past
// his top speed, on the ground) down stores it (the input wrapper took the down, so no roll: g_sparkDown): the charge
// ends, he skids to a stop (sparkSkid a frame for sparkSkidFrames) and glows (SparkGlow) for sparkStore frames, walking
// and jumping as usual; a hit loses it (g_ab is cleared). A jump press while it's stored (on the ground: the game's jump
// has just happened; in the air state) launches it the way the d-pad says: a side held forward that way (with up,
// up-forward), else straight up; at sparkSpeed (the diagonal sparkDiag per axis), no gravity (the air state's taken off
// in advance, as the Thunder Zip's; its drag too), no control (the input wrapper clears the pad), until the terrain stops
// him (his speed along the flight under half of it: a wall, a ceiling; up and up-forward, landing), a spring or an object
// (another animation or state) or a hit. Forward it runs along the ground if he's on it. Meanwhile he's an attack (shown
// to the game as the jump) and enemies can't hurt him (jugg::Juggernaut). Poses: the attack-up slot (his SPRING pose)
// up and up-forward, the shot slot (the charge's dash frames, one per chargeStride px) forward.
constexpr int ANI_FALL = 7, ANI_SKID = 18;  // (3K_Players/Sonic.bin, as every extra's file)
static void SparkVelocity(EntityPlayer* p, const ExtraAbilities& c, int kind, int dir, bool air) {
    int vx = kind == 1 ? 0 : dir * (kind == 2 ? c.sparkDiag : c.sparkSpeed);
    int vy = kind == 1 ? -c.sparkSpeed : kind == 2 ? -c.sparkDiag : 0;
    if (!air) {
        p->groundVel = vx;  // (forward along the ground)
        return;
    }
    vy -= Gravity(p);  // (the air state adds it back)
    if (vy > -0x40000 && vy < 0)  // (and takes 1/32 of the speed along off while rising that slowly: added in advance)
        vx = (int)((long long)vx * 32 / 31);
    p->velocity.x = vx;
    p->velocity.y = vy;
}

static void Spark(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    bool down = g_sparkDown;
    g_sparkDown = false;
    if (c.sparkSpeed <= 0)
        return;
    if (g_ab.spark > SPARK_ACTIVE) {  // flying
        int k = g_ab.spark - SPARK_ACTIVE, kind = k % 100, dir = k >= 100 ? -1 : 1;
        int a = p->animator.animationID;
        bool ours = a == ANI_JUMP || (a >= ANI_WALK && a <= ANI_DASH + 1);  // (shown as the jump; the ground state may
                                                                             // put its own run in along the ground)
        bool go = ours && !Held(p) && (!air || (void*)p->state.state == g_playerStateAir || !g_playerStateAir);
        bool stop = false;
        if (go) {
            int along = dir * (air ? p->velocity.x : p->groundVel);
            if (!air)
                stop = kind != 3 || along < c.sparkSpeed / 2;  // landed (or on a ceiling); forward, a wall
            else if (kind == 1)
                stop = p->velocity.y > -c.sparkSpeed / 2;  // a ceiling
            else if (kind == 2)
                stop = p->velocity.y > -c.sparkDiag / 2 || along < c.sparkDiag / 2;
            else
                stop = along < c.sparkSpeed / 2;  // a wall
        }
        if (!go || stop) {
            g_ab.spark = 0;
            if (stop) {  // the terrain stopped him: he drops from there
                if (air) {
                    p->velocity.x = 0;
                    if (p->velocity.y < 0)
                        p->velocity.y = 0;
                }
                p->groundVel = 0;
                RSDK->SetSpriteAnimation(g_extraFrames, air ? ANI_FALL : ANI_WALK, &p->animator, true, 0);
            }
            Log("shine spark: %s", stop ? "stopped by the terrain" : "taken over");
            return;
        }
        p->direction = dir < 0 ? 1 : 0;
        SparkVelocity(p, c, kind, dir, air);
        int anim = kind == 3 ? ANI_EXTRA_SHOT : ANI_EXTRA_ATTACK_UP;
        PlayExtraAnimation(p, anim, true, false);
        int count = p->animator.frameCount;
        if (kind == 3 && count > 0) {
            int f = ((p->position.x >> 16) / std::max(1, c.chargeStride)) % count;
            p->animator.frameID = dir < 0 ? count - 1 - f : f;
        }
        p->animator.timer = 0;
        return;
    }
    if (g_ab.spark > 0) {  // stored
        g_ab.spark--;
        if (g_ab.spark > c.sparkStore - c.sparkSkidFrames && !air && p->groundVel != 0) {  // just stored: the skid
            int v = std::max(0, std::abs(p->groundVel) - c.sparkSkid);
            p->groundVel = p->groundVel < 0 ? -v : v;
            if (v > 0 && p->animator.animationID != ANI_SKID)
                RSDK->SetSpriteAnimation(g_extraFrames, ANI_SKID, &p->animator, false, 0);
        }
        bool free = air ? (void*)p->state.state == g_playerStateAir || !g_playerStateAir : true;
        if (g_ab.spark > 0 && p->jumpPress && free && !Held(p) && !Hurt(p)) {  // launch
            int kind = 1, dir = (p->direction & 1) ? -1 : 1;
            if (p->left || p->right) {
                kind = p->up ? 2 : 3;
                dir = p->left ? -1 : 1;
            }
            g_ab.spark = SPARK_ACTIVE + kind + (dir < 0 ? 100 : 0);
            g_ab.charge = 0;
            p->direction = dir < 0 ? 1 : 0;
            if (!air) {  // (no jump happened: into the air from here)
                p->onGround = false;
                p->angle = 0;
                p->collisionMode = 0;  // (the floor's)
            }
            if (g_playerStateAir)
                p->state.state = (void(__fastcall*)())g_playerStateAir;
            p->jumpAbilityState = 0;
            NoJumpCap(p);
            SparkVelocity(p, c, kind, dir, true);
            PlayExtraAnimation(p, kind == 3 ? ANI_EXTRA_SHOT : ANI_EXTRA_ATTACK_UP, true, true);
            if (c.sparkSound)
                PlaySound(c.sparkSound);
            Log("shine spark: launched (%s)", kind == 1 ? "up" : kind == 2 ? "up-forward" : "forward");
        }
        return;
    }
    int top = *(int*)((char*)p + 0x220);
    if (down && !air && g_ab.charge != 0 && std::abs(g_ab.charge) > top && !Hurt(p)) {  // storing
        g_ab.charge = 0;
        g_ab.chargeAnim = -1;
        g_ab.spark = c.sparkStore;
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_SKID, &p->animator, true, 0);
        if (c.sparkStoreSound)
            PlaySound(c.sparkStoreSound);
        Log("shine spark: stored");
    }
}

// Spin Attack (Honey's; abilities.py spin_attack, S1/S2's spin_after / spin_before): Y, standing, walking, running or in
// the air (the jump ball: Y transforms first when Super is possible, SuperPress), starts her whirl; it lasts while Y is
// held, spinFrames at most, then spinCooldown. An attack throughout (shown to the game as the jump), its frames by its own
// clock (the attack slot in the air, the shot slot on the ground), and floaty in the air: spinGravity / 256 of the
// gravity. Whatever it breaks or hits (the badnik, boss and monitor hooks: g_spinHit) bounces her hard on her next
// update: up at spinBounce, and on the ground away from the way she faces at spinBounceX, into the air state.
static void SpinAttack(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    static void* groundState = nullptr;  // the plain ground state (seen while she stands, walks or runs)
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1);
    if (!air && plain && p->state.state && g_ab.spin <= 0)
        groundState = (void*)p->state.state;
    bool inState = air ? (void*)p->state.state == g_playerStateAir && g_playerStateAir
                       : groundState && (void*)p->state.state == groundState;
    if (g_ab.spin < 0)
        g_ab.spin++;
    if (g_ab.spin == 0 && YPressed(p) && !Hurt(p) && (air ? inState : plain)) {
        g_ab.spin = 1;
        g_ab.spinAnim = -1;
        g_spinHit = false;
        if (c.spinSound)
            PlaySound(c.spinSound);
        Log("spin attack");
    }
    if (g_ab.spin <= 0) {
        g_spinWatch = false;
        return;
    }
    if (!YDown(p) || g_ab.spin > c.spinFrames || Hurt(p) || !inState) {  // let go, too long or out of it: over
        g_ab.spin = -c.spinCooldown;
        g_spinWatch = g_spinHit = false;
        if (!Hurt(p) && p->animator.animationID == ANI_JUMP) {  // (ours still showing)
            if (air)
                BackToJump(p);
            else
                RSDK->SetSpriteAnimation(g_extraFrames, ANI_WALK, &p->animator, true, 0);
        }
        return;
    }
    if (g_spinHit) {  // a hard bounce off what she hit
        g_spinHit = false;
        p->velocity.y = -c.spinBounce;
        NoJumpCap(p);
        if (!air && g_playerStateAir) {  // on the ground: up and away, a pinball
            int away = (p->direction & 1) ? c.spinBounceX : -c.spinBounceX;
            p->velocity.x = away;
            p->groundVel = away;
            p->onGround = false;
            p->angle = 0;
            p->collisionMode = 0;  // floor
            p->state.state = (void(__fastcall*)())g_playerStateAir;
            air = true;
        }
        Log("spin attack: bounce");
    } else if (air) {  // floaty: part of this frame's gravity taken back
        p->velocity.y -= (int)((long long)Gravity(p) * (256 - c.spinGravity) >> 8);
    }
    int anim = air ? ANI_EXTRA_ATTACK : ANI_EXTRA_SHOT;
    PlayExtraAnimation(p, anim, true, anim != g_ab.spinAnim);
    g_ab.spinAnim = anim;
    int count = p->animator.frameCount;
    if (count > 0)
        p->animator.frameID = (g_ab.spin / std::max(1, c.spinTicks)) % count;
    p->animator.timer = 0;
    g_ab.spin++;
    g_spinWatch = true;
    // The lean (a draw effect, abilities.py spin_lean / spin_lean_max, as S1/S2 / CD draw it): her spin frames (rotation
    // style full in her .bin, "s3k_rot") drawn turned toward her travel, by her speed, eased in over the first 8 frames
    // and out over the last 8. The game only draws with the rotation; after the spin it eases it back itself.
    constexpr int SPIN_LEAN = 5, SPIN_LEAN_MAX = 32;
    int v = air ? p->velocity.x : p->groundVel;
    int lean = std::clamp((int)((long long)v * SPIN_LEAN / 0x10000), -SPIN_LEAN_MAX, SPIN_LEAN_MAX);
    int ease = std::min(g_ab.spin - 1, 8);
    if (g_ab.spin > c.spinFrames - 7)
        ease = c.spinFrames + 1 - g_ab.spin;
    lean = lean * std::max(ease, 0) / 8;
    p->rotation = ((air ? 0 : p->angle << 1) + lean) & 0x1FF;
}

// Sally's Spin-Kick High Jump (abilities.py high_kick, the same phases as S1/S2's NoSwap_hiKick): Y on the ground (the
// plain ground state) or in the air state starts it, once per airborne period, or after highKickCooldown frames on the
// ground. A wind-up held still (the hover slot, frame 0: not an attack), then straight up at highKickRise in the kick's
// frames (the shot slot, an attack: reported as the jump), then at the top highKickRecover frames of the recovery pose
// (hover slot frame 1: not an attack), then she falls in the jump ball with her jump ability ready. A hit, a roll, an
// object taking over or landing ends it. Started during the Flying Kick Dive, it ends the dive (as in S1/S2 and CD).
constexpr int HIKICK_KICK = 1000, HIKICK_RECOVER = 2000;  // (abilities.py HIGH_KICK_KICK / HIGH_KICK_RECOVER)
static void HighKick(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    static void* groundState = nullptr;  // the plain ground state (seen while she stands, walks or runs)
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || (a >= ANI_WALK && a <= ANI_DASH + 1);
    if (!air && plain && p->state.state && g_ab.hiKick == 0)
        groundState = (void*)p->state.state;
    bool airState = g_playerStateAir && (void*)p->state.state == g_playerStateAir;
    bool inState = air ? airState : groundState && (void*)p->state.state == groundState;
    if (!air && g_ab.hiKick == 0) {
        g_ab.hiKickUsed = false;
        if (g_ab.hiKickCool > 0)
            g_ab.hiKickCool--;
    }
    if (g_ab.hiKick == 0 && !Hurt(p) && (air ? airState && !g_ab.hiKickUsed : plain && inState && g_ab.hiKickCool == 0)
        && YPressed(p)) {
        g_ab.hiKick = 1;
        g_ab.hiKickUsed = true;
        g_ab.kick = false;  // (out of the Flying Kick Dive)
        Log("high kick");
    }
    if (g_ab.hiKick == 0)
        return;
    g_ab.ready = false;  // (no jump ability during it)
    if (Hurt(p) || !inState || (g_ab.hiKick >= HIKICK_KICK && !air)) {  // over
        g_ab.hiKick = 0;
        g_ab.hiKickCool = c.highKickCooldown;
        if (!Hurt(p)) {
            if (air)
                BackToJump(p);
            else
                RSDK->SetSpriteAnimation(g_extraFrames, ANI_WALK, &p->animator, true, 0);
        }
        return;
    }
    if (g_ab.hiKick < HIKICK_KICK) {  // the wind-up: held still
        p->velocity.x = 0;
        p->groundVel = 0;
        if (air)
            p->velocity.y = 0;
        PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
        p->animator.frameID = 0;
        if (++g_ab.hiKick > c.highKickWindup) {  // launch, straight up
            if (!air) {
                p->onGround = false;
                p->angle = 0;
                p->collisionMode = 0;  // floor
                p->state.state = (void(__fastcall*)())g_playerStateAir;
            }
            p->velocity.y = -c.highKickRise;
            p->jumpAbilityState = 0;
            NoJumpCap(p);  // as after a spring: letting go of jump doesn't cut it short
            if (c.highKickSound)
                PlaySound(c.highKickSound);
            g_ab.hiKick = HIKICK_KICK;
        }
    } else {
        if (g_ab.hiKick < HIKICK_RECOVER) {  // the kick, rising
            p->velocity.x = 0;
            p->groundVel = 0;
            PlayExtraAnimation(p, ANI_EXTRA_SHOT, true, g_ab.hiKick == HIKICK_KICK);
            int count = p->animator.frameCount;
            if (count > 0)
                p->animator.frameID = (g_ab.hiKick - HIKICK_KICK) / std::max(1, c.highKickTicks) % count;
            g_ab.hiKick++;
            if (p->velocity.y >= 0)  // the top: the recovery
                g_ab.hiKick = HIKICK_RECOVER;
        }
        if (g_ab.hiKick >= HIKICK_RECOVER) {  // the recovery (normal air control)
            PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
            p->animator.frameID = 1;
            if (++g_ab.hiKick > HIKICK_RECOVER + c.highKickRecover) {  // then she falls as from a jump
                g_ab.hiKick = 0;
                g_ab.hiKickCool = c.highKickCooldown;
                BackToJump(p);
                g_ab.ready = true;  // her jump ability: once, as in any jump
            }
        }
    }
    p->animator.timer = 0;
}

// Tails Doll's Phase Warp, as in S1/S2 (abilities.py phase_warp): the jump press, once per jump. He flickers out
// (warpVanish frames), is gone (warpGone), flickers back in (warpAppear), held still and untouchable (the blink timer
// at 3: no flicker of its own; his visibility does the hiding); as he goes he moves up to warpRange px where the d-pad
// points (8 ways, nothing held: ahead), 8 px a step (abilities.WARP_STEP: warpRange / 8 steps), stopping before the first step where a point of his body
// (abilities.WARP_POINTS) is in solid terrain (TerrainAt: floors and ceilings). Then his speed along from before, and he
// falls from there. The flicker is the attack animation (slot 41). Landing, a hit, a spring or the melee ends it.
// Runs after the game's update: the velocities set here move him next frame, after the air state's gravity (taken off
// in advance).
// Mephiles' Shadow Sink (abilities.py sink, the same phases as S1/S2's NoSwap_sink): down + Y on the ground (standing,
// walking, crouching or in the throw pose; not rolling, hurt or held by an object) and he sinks: sinkFrames (extra slot 5)
// forward, sinkTicks game frames each; then under, sinkUnder's frames in turn (sinkUnderTicks each) for sinkMax frames at
// most; then he rises (sinkFrames backward). Letting go of down or Y rises at once, from the frame he's at. Throughout he
// doesn't move (speed 0; the input wrapper, NoRollInput, clears his input) and nothing hurts him (the post-hit blink timer
// held at 3, under the flicker's 4: known once he's been hit, FindBlinkTimer). Leaving the ground, a hit that gets through
// or an object taking over ends it. Then sinkCooldown frames before the next.
constexpr int SINK_RISE = 1000;  // (abilities.py SINK_RISE)
static void Sink(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    const int steps = std::clamp(c.sinkSteps, 1, (int)(sizeof(c.sinkFrames) / sizeof(c.sinkFrames[0])));
    const int under = std::clamp(c.sinkUnderCount, 1, (int)(sizeof(c.sinkUnder) / sizeof(c.sinkUnder[0])));
    const int ticks = std::max(c.sinkTicks, 1), uticks = std::max(c.sinkUnderTicks, 1), d = steps * ticks;
    if (g_ab.sink < 0)
        g_ab.sink++;
    int a = p->animator.animationID;
    bool plain = a == ANI_IDLE || a == ANI_BORED_1 || a == ANI_BORED_2 || a == ANI_CROUCH
                 || (a >= ANI_WALK && a <= ANI_DASH + 1) || a == ANI_EXTRA_SHOT;
    if (g_ab.sink == 0 && !air && plain && !Hurt(p) && !Held(p) && DownHeld(p) && YPressed(p)) {
        g_ab.sink = 1;
        if (c.sinkSound)
            PlaySound(c.sinkSound);
        static bool warned = false;
        if (g_blinkOffset < 0 && !warned)
            Log("shadow sink: the blink timer isn't known yet (get hit once): he can be hurt while sunk");
        warned = true;
        Log("shadow sink");
    }
    if (g_ab.sink <= 0)
        return;
    if (air || Hurt(p) || Held(p)) {  // the ground gave way, a hit that got through, an object: over
        g_ab.sink = -c.sinkCooldown;
        if (p->animator.animationID == ANI_EXTRA_SINK)
            RSDK->SetSpriteAnimation(g_extraFrames, air ? ANI_WALK : ANI_IDLE, &p->animator, true, 0);
        Log("shadow sink: ended");
        return;
    }
    p->groundVel = 0;
    p->velocity.x = 0;
    p->velocity.y = 0;
    g_ab.throwPose = 0;  // (no throw pose over it)
    if (g_blinkOffset >= 0) {  // nothing hurts him (without the flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    if (g_ab.sink < SINK_RISE && !(DownHeld(p) && YDown(p)))  // let go: he rises, from where he is
        g_ab.sink = SINK_RISE + std::min(g_ab.sink, d);
    int frame;
    if (g_ab.sink <= d) {  // sinking
        frame = c.sinkFrames[std::min((g_ab.sink - 1) / ticks, steps - 1)];
        g_ab.sink++;
    } else if (g_ab.sink < SINK_RISE) {  // under
        frame = c.sinkUnder[((g_ab.sink - d - 1) / uticks) % under];
        if (++g_ab.sink > d + c.sinkMax)  // time's up: he rises
            g_ab.sink = SINK_RISE + d;
    } else {  // rising: the sink's frames backward
        frame = c.sinkFrames[std::clamp((g_ab.sink - SINK_RISE - 1) / ticks, 0, steps - 1)];
        g_ab.sink--;
    }
    PlayExtraAnimation(p, ANI_EXTRA_SINK, false, false);
    p->animator.frameID = frame;  // the timer picks the frame
    p->animator.timer = 0;
    if (g_ab.sink == SINK_RISE) {  // risen
        g_ab.sink = -c.sinkCooldown;
        RSDK->SetSpriteAnimation(g_extraFrames, ANI_IDLE, &p->animator, true, 0);
    }
}

// The floating lean (abilities.py float_lean: Mephiles; S1/S2's float_lean_draw): his walk / run (and jog, dash, fall,
// the peel out, and their "Angled" ones: full rotation in his Extra.bin, build_s3k_art.py) drawn turned toward his
// travel by his speed alone (ground speed; in the air his x speed), floatLeanMax at most, instead of the slope's rotation
// (he floats). The game only draws with the rotation, and eases it back itself in the air.
static void FloatLean(EntityPlayer* p, const ExtraAbilities& c) {
    int a = p->animator.animationID;
    bool peelout = Extra(g_character).base == 0 && (a == ANI_PEELOUT || a == ANI_PEELOUT + 1);  // (Sonic.bin's)
    if (!(a >= ANI_WALK && a <= ANI_DASH + 1) && !peelout)
        return;
    int v = p->onGround ? p->groundVel : p->velocity.x;
    int lean = std::clamp((int)((long long)v * c.floatLean / 0x10000), -c.floatLeanMax, c.floatLeanMax);
    p->rotation = lean & 0x1FF;
}

static void PhaseWarp(EntityPlayer* p, const ExtraAbilities& c, bool trigger, bool air) {
    static bool hidden = false;  // his visibility is ours (put back when it ends, however it ends)
    const int appear = c.warpAppear, gone = c.warpGone, total = c.warpVanish + gone + appear;
    if (trigger) {
        int dx = p->right ? 1 : p->left ? -1 : 0, dy = p->up ? -1 : p->down ? 1 : 0;
        if (!dx && !dy)
            dx = (p->direction & 1) ? -1 : 1;
        g_ab.warp = total;
        g_ab.warpDX = dx;
        g_ab.warpDY = dy;
        g_ab.warpVX = p->velocity.x;
        PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        if (c.warpSound)
            PlaySound(c.warpSound);
        Log("phase warp (%d, %d)", dx, dy);
    } else if (g_ab.warp > 0 && (!air || Hurt(p) || p->animator.animationID != ANI_JUMP)) {
        g_ab.warp = 0;  // landed, a hit, a spring, the melee...
    }
    if (g_ab.warp <= 0) {
        if (hidden)
            p->visible = true;
        hidden = false;
        return;
    }
    p->velocity.x = 0;  // held still
    p->velocity.y = -Gravity(p);
    if (g_ab.warp == gone + appear) {  // gone: to the destination, the last clear step along the way
        static const int POINTS[][2] = {{0, 0}, {0, -13}, {0, 13}, {-8, 0}, {8, 0}};  // (abilities.WARP_POINTS)
        const bool diag = g_ab.warpDX && g_ab.warpDY;
        const int step = 8 << 16, axis = diag ? (int)((int64_t)step * 46341 >> 16) : step, steps = c.warpRange / 8;
        int ox = 0, oy = 0, k = 0;
        for (; k < steps; k++) {
            int nx = ox + g_ab.warpDX * axis, ny = oy + g_ab.warpDY * axis;
            bool blocked = false;
            for (auto& pt : POINTS)
                blocked = blocked || TerrainAt(p, (nx >> 16) + pt[0], (ny >> 16) + pt[1]);
            if (blocked)
                break;
            ox = nx;
            oy = ny;
        }
        p->position.x += ox;
        p->position.y += oy;
        Log("phase warp: %d of %d steps (%d, %d px)", k, steps, ox >> 16, oy >> 16);
    }
    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
    bool out = g_ab.warp <= gone + appear && g_ab.warp > appear;
    p->visible = !out && (g_ab.warp & 1);  // gone, or a flicker every other frame
    hidden = true;
    if (g_blinkOffset >= 0) {  // untouchable (without the blink's own flicker)
        int& blink = *(int*)((char*)p + g_blinkOffset);
        if (blink < 3)
            blink = 3;
    }
    if (--g_ab.warp == 0) {  // back: his speed along, falling from here
        p->velocity.x = g_ab.warpVX;
        p->velocity.y = 0;
        p->visible = true;
        hidden = false;
        BackToJump(p);
    }
}

// The Screen Nuke's flash (abilities.py melee_nuke): every palette bank darkened by the flash's darkness per frame, then
// put back. Each entry is kept as the game last wrote it (an entry changed since our last write is the game's new colour:
// palette cycles, a stage's own palette loads), and only entries still holding our darkened colour are put back.
// What we wrote is READ BACK: the engine keeps its palette as RGB565, so GetPaletteEntry never returns the 24-bit colour
// set; compared with the value set, every darkened entry looked like "the game's new colour", was kept as the colour to
// restore, darkened again next frame, and the "restore" put back black (the permanently black screen).
// Its own copy of the flash (taken at the start), so nothing about the character can cut it; ticked on player 1's every
// update before any early return; a nuke during a flash doesn't restart or stack it; the stage load restores at once; and
// a safety net: whenever no flash runs but entries still hold our darkened colours, they're put back.
static uint32 g_flashSaved[8][256], g_flashWritten[8][256];
static bool g_flashDirty = false;  // entries may hold our darkened colours
static int g_flashLen = 0;
static uint8 g_flashTable[64];

static void FlashRestore(const char* why) {
    int back = 0;
    for (int bank = 0; bank < 8; bank++)
        for (int i = 0; i < 256; i++) {
            uint32 now = RSDK->GetPaletteEntry(bank, i) & 0xFFFFFF;
            if (now == g_flashWritten[bank][i] && now != g_flashSaved[bank][i]) {
                RSDK->SetPaletteEntry(bank, i, g_flashSaved[bank][i]);
                back++;
            }
            g_flashWritten[bank][i] = RSDK->GetPaletteEntry(bank, i) & 0xFFFFFF;
        }
    if (g_flashDirty || g_flashAt >= 0)
        Log("screen nuke: flash over (%s): %d palette entries put back", why, back);
    g_flashDirty = false;
    g_flashAt = -1;
}

static void NukeFlashStart(const ExtraAbilities& c) {
    if (g_flashAt >= 0 || g_flashDirty)  // one already running: no restart, no stacking
        return;
    g_flashLen = std::clamp(std::min(c.nukeFlashCount, (int)(sizeof(c.nukeFlash) / sizeof(c.nukeFlash[0]))), 0,
                            (int)sizeof(g_flashTable));
    for (int k = 0; k < g_flashLen; k++)
        g_flashTable[k] = (uint8)std::clamp(c.nukeFlash[k], 0, 255);
    for (int bank = 0; bank < 8; bank++)
        for (int i = 0; i < 256; i++)
            g_flashSaved[bank][i] = g_flashWritten[bank][i] = RSDK->GetPaletteEntry(bank, i) & 0xFFFFFF;
    g_flashAt = 0;
}

static void NukeFlash() {
    if (g_flashAt < 0 || g_flashAt >= g_flashLen) {
        if (g_flashAt >= 0 || g_flashDirty)  // the end (and the safety net)
            FlashRestore(g_flashAt >= 0 ? "its end" : "safety net");
        return;
    }
    g_flashDirty = true;
    int keep = 255 - g_flashTable[g_flashAt];
    for (int bank = 0; bank < 8; bank++)
        for (int i = 0; i < 256; i++) {
            uint32 now = RSDK->GetPaletteEntry(bank, i) & 0xFFFFFF;
            if (now != g_flashWritten[bank][i])
                g_flashSaved[bank][i] = now;  // the game's colour
            uint32 in = g_flashSaved[bank][i];
            uint32 out = (((in >> 16 & 0xFF) * keep / 255) << 16) | (((in >> 8 & 0xFF) * keep / 255) << 8)
                         | ((in & 0xFF) * keep / 255);
            if (out != now) {
                RSDK->SetPaletteEntry(bank, i, out);
                now = RSDK->GetPaletteEntry(bank, i) & 0xFFFFFF;  // (as the engine keeps it: RGB565)
            }
            g_flashWritten[bank][i] = now;
        }
    g_flashAt++;
}

static void Magnetic(EntityPlayer* p) {
    static Entity* pulled[64];
    static int pulledCount = 0;
    Entity* now[64];
    int nowCount = 0;
    uint16 ring = (uint16)RSDK->FindObject("Ring");  // (per stage: the class list is the stage's)
    if (!ring) {
        pulledCount = 0;
        return;
    }
    Entity* e = nullptr;
    while (RSDK->GetActiveEntities(ring, (void**)&e)) {
        int dx = (p->position.x - e->position.x) >> 16, dy = (p->position.y - e->position.y) >> 16;
        bool attracted = std::find(pulled, pulled + pulledCount, e) != pulled + pulledCount;
        if (!attracted) {
            if (e->velocity.x || e->velocity.y || std::abs(dx) > 64 + 10 || std::abs(dy) > 64 + 20 || nowCount == 64)
                continue;
        } else if (nowCount == 64) {
            continue;
        }
        now[nowCount++] = e;
        e->velocity.x += dx >= 0 ? (e->velocity.x < 0 ? 0xC000 : 0x3000) : (e->velocity.x > 0 ? -0xC000 : -0x3000);
        e->velocity.y += dy >= 0 ? (e->velocity.y < 0 ? 0xC000 : 0x3000) : (e->velocity.y > 0 ? -0xC000 : -0x3000);
        e->position.x += e->velocity.x;
        e->position.y += e->velocity.y;
    }
    std::copy(now, now + nowCount, pulled);
    pulledCount = nowCount;
}

static bool Readable(const void* p, size_t size);  // (below)

// ---------------------------------------------------------------- shots: real projectiles (Amy's SuperHammer, reused)
// Origins' S3&K has one player projectile: SuperHammer, Amy's thrown hammer, a global object (in every stage's list).
// Every enemy already checks it, through four shared functions, but only for a player whose characterID is 8 (Amy):
//   Player_CheckBadnikTouch(player, entity, hitbox)  0x1401dffe0  Amy: true if a hammer touches the entity
//                                                                  (SuperHammer_CheckHit, which lists the entity's slot)
//   Player_CheckBadnikBreak(player, entity, destroy) 0x1401dd0d0  Amy: an entity a hammer has hit (SuperHammer_AlreadyHit)
//   Player_CheckBossHit(player, entity)              0x1401dad10  counts as attacked (no bounce for the player)
//   ItemBox_CheckHit(itembox)                        0x1401d3730  its per-character switch: Amy's case checks hammers
// (Breakable walls, rocks, ice and the like check hammers for anyone.) An extra with a shot (package "s3k.shot",
// ExtraData.h ShotData) throws a SuperHammer of its own on Y (CreateEntity, as the hammer's own static update does for
// Amy), with its package's art (3K_Players/Shot.bin: its stage load is wrapped) and our motion (its update is wrapped
// for our shots: bounce along floors...). The four functions are hooked: for player 1 while the extra's shot is out, the
// touch also counts a shot touching (the call Amy's code makes), and the other three run with characterID 8 whenever
// Amy's code would take its hammer path, so the game does exactly what it does for Amy's hammer (explosion, animal and
// score; the monitor's item to the player; the boss's own hit and flash). Addresses and layouts: this build's exe
// (research notes: scratchpad shots/s3k.md); each hooked or called function's first bytes are checked at startup, and
// on any mismatch the shot system stays off (the game as before; the extra's other moves still work).
// A charge shot (ShotData.onCharge, "s3k.shot2" "input" "charge": Mega Man's Charge Shot): frames Y has been held (0 at
// a stage load; shots::Frame counts it, ChargeFlash shows it)
static int g_busterCharge = 0;

// Heavy's full charge (Juggernaut, below): what each object class of this stage has been seen doing with the players,
// from the shots' hooks: JUGG_TOUCH Player_CheckBadnikTouch, JUGG_BADNIK Player_CheckBadnikBreak, JUGG_BOSS
// Player_CheckBossHit (the entity's classID; cleared at each stage load: class IDs are the stage's own)
namespace jugg {
enum : uint8 { JUGG_TOUCH = 1, JUGG_BADNIK = 2, JUGG_BOSS = 4, JUGG_NAMED = 0x40, JUGG_HAZARD = 0x80 };
static uint8 g_class[1024] = {};
static void Note(Entity* e, uint8 kind) {
    if (e && e->classID < 1024)
        g_class[e->classID] |= kind;
}
}  // namespace jugg

static Entity* CurrentEntity(int* slotOut);  // (below)
static bool StarTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox);  // (Ristar: StarGrab.h)
static bool HeadTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox);  // (Headdy: HeadThrow.h)
static bool AnchorTouch(EntityPlayer* p, Entity* e, Hitbox* hitbox);  // (Marine: AnchorThrow.h)
namespace jugg {
static bool Enemy(Entity* e);  // (below: an enemy's class, not a hazard's)
}
namespace psycho {  // (Silver's Psychokinesis: PsychoGrab.h)
static bool Touch(EntityPlayer* p, Entity* e);
static bool Breaks(EntityPlayer* p, Entity* e, bool32 destroy, bool32* result);
static bool Refuses(EntityPlayer* p, Entity* e);
static bool Draw(Entity* shot);
static void Animate(Entity* shot);
static void Reset();
static void DrawCarried();
}
namespace afterImage {  // (afterimages: Ghost.h)
static void Clear();
}

namespace treasure {  // (Rouge's Treasure Sense marker, in the icon pass: TreasureSense.h)
static bool Pass();
static void Draw();
}  // namespace treasure
namespace ninja {  // (Joe Musashi's Ninjutsu: a broken monitor stores a magic, its icon in the icon pass; Ninjutsu.h)
static bool On();
static bool Pass();
static void Draw();
static void MonitorBroke();
static void Reset();
static void Carry();
}  // namespace ninja
namespace nights {  // (NiGHTS' flight meter in the icon pass, his Paraloop's touch, his Drill Dash: NightsFlight.h)
static bool Pass();
static void Draw();
static bool LoopTouch(EntityPlayer* p, Entity* e);
static bool Drilling();
static void Reset();
}  // namespace nights
namespace volt {  // (Pulseman's Voltteccer: Voltteccer.h)
static void Reset();
}  // namespace volt
namespace pots {  // (Gilius' pot magic: broken monitors fill his pots, up + Y the Earthquake; PotMagic.h)
static bool On();
static bool Pass();
static void Draw();
static void DrawRocks();
static void MonitorBroke();
static void Reset();
static void Carry();
}  // namespace pots
static bool ActTransitionLoad();  // (globals->atlEnabled: a seamless act transition's scene load; below, by GLOBALS)

namespace shots {
constexpr uintptr_t TOUCH = 0x1401dffe0, BREAK = 0x1401dd0d0, BOSS_HIT = 0x1401dad10, ITEMBOX_CHECK = 0x1401d3730,
                    HAMMER_CHECK_HIT = 0x14009d600, HAMMER_ALREADY_HIT = 0x14009d950;
struct Prologue {
    const char* name;
    uintptr_t at;
    uint8 bytes[32];
    size_t size;
};
static const Prologue PROLOGUES[] = {
    {"Player_CheckBadnikTouch", TOUCH, {0x48, 0x89, 0x5c, 0x24, 0x10, 0x4c, 0x89, 0x44, 0x24, 0x18, 0x55, 0x56, 0x57, 0x41,
     0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8b, 0xec, 0x48, 0x83, 0xec, 0x50, 0x83, 0xb9, 0xa8, 0x01}, 32},
    {"Player_CheckBadnikBreak", BREAK, {0x44, 0x89, 0x44, 0x24, 0x18, 0x48, 0x89, 0x4c, 0x24, 0x08, 0x55, 0x53, 0x56, 0x57,
     0x41, 0x54}, 16},
    {"Player_CheckBossHit", BOSS_HIT, {0x48, 0x89, 0x4c, 0x24, 0x08, 0x53, 0x55, 0x57, 0x41, 0x55, 0x41, 0x56, 0x48, 0x83,
     0xec, 0x70}, 16},
    {"ItemBox_CheckHit", ITEMBOX_CHECK, {0x40, 0x55, 0x41, 0x56, 0x48, 0x8b, 0xec, 0x48, 0x83, 0xec, 0x68, 0x48, 0x8b, 0x05,
     0x16, 0x22}, 16},
    {"SuperHammer_CheckHit", HAMMER_CHECK_HIT, {0x48, 0x89, 0x5c, 0x24, 0x18, 0x55, 0x56, 0x41, 0x56, 0x48, 0x83, 0xec,
     0x40, 0x48, 0x8b, 0x05}, 16},
    {"SuperHammer_AlreadyHit", HAMMER_ALREADY_HIT, {0x40, 0x53, 0x48, 0x83, 0xec, 0x40, 0x48, 0x8b, 0x05, 0x73, 0x03, 0x82,
     0x02, 0x0f, 0xb7, 0xd9}, 16},
};
// SuperHammer's layout (entity 0xE0 bytes, static 0x14; checked at its registration)
constexpr int ENTITY_SIZE = 0xE0, STATIC_SIZE = 0x14;
constexpr int E_STATE = 0x60, E_ANIMATOR = 0x70, E_GRAVITY = 0x94, E_HIT_COUNT = 0xD8;  // (state: unused by the game's)
constexpr int S_CLASS = 0x0, S_FRAMES = 0x4;
constexpr int ID_AMY_CHARACTER = 8;
constexpr int RINGS = 0xD0;  // the player's ring count (PLAYER_RINGS, below): a swap shot's cost ("rings")
constexpr int BURNING = 2;   // a swap shot's Phase while its flames burn where it landed (ShotData.burnAnim)
static_assert(offsetof(Entity, velocity) == 0x18 && offsetof(Entity, classID) == 0x3E && offsetof(Entity, direction) == 0x56
              && offsetof(Entity, collisionLayers) == 0x58 && offsetof(Entity, updateRange) == 0x20
              && offsetof(EntityPlayer, characterID) == 0x1A8, "the S3&K entity layout");
enum { CMODE_FLOOR = 0, CMODE_LWALL = 1, CMODE_ROOF = 2, CMODE_RWALL = 3 };

typedef bool32 (*TouchFn)(EntityPlayer* player, Entity* entity, Hitbox* hitbox);
typedef bool32 (*BreakFn)(EntityPlayer* player, Entity* entity, bool32 destroy);
typedef bool32 (*BossHitFn)(EntityPlayer* player, Entity* entity);
typedef uintptr_t (*ItemBoxCheckFn)(Entity* itembox);
typedef bool (*HammerCheckHitFn)(Entity* entity, Hitbox* hitbox, Entity** hammer);
typedef bool (*HammerAlreadyHitFn)(uint16 slot);
static TouchFn g_touch = nullptr;
static BreakFn g_break = nullptr;
static BossHitFn g_bossHit = nullptr;
static ItemBoxCheckFn g_itemBoxCheck = nullptr;
static const HammerCheckHitFn HammerCheckHit = (HammerCheckHitFn)HAMMER_CHECK_HIT;
static const HammerAlreadyHitFn HammerAlreadyHit = (HammerAlreadyHitFn)HAMMER_ALREADY_HIT;

static bool g_on = false;           // prologues matched and hooks in (SetUp)
static void** g_static = nullptr;   // SuperHammer's static variables (its registration; *g_static once allocated)
static void (*g_stageLoad)(void) = nullptr;
static void (*g_update)(void) = nullptr;
static uint16 g_frames = 0xFFFF;    // our art this stage (3K_Players/Shot.bin), 0xFFFF: none
static int g_cooldown = 0;
static bool g_high = false;         // the last throw was with up held (ShotData "up")
static int g_aimK = 0;              // the last aimed throw's aim (0 level, 1 forward-up, 2 up, 3 forward-down, 4 down)
static int g_next = 0;              // a cycle shot (ShotData.cycle): the art frame the next throw takes
static std::vector<std::pair<void**, std::string>> g_objectNames;  // every registered object (for the log)

// SuperHammer entities of ours are marked in their state machine (which the game's never runs): state = this
// function, timer = the shot's age in frames. A second shot's (ExtraData.shot2, down + Y: Robotnik's Bomb Drop) are
// marked with Marker2 (a body of its own, so the compiler never folds the two into one address)
static void __fastcall Marker() {}
static volatile int g_marker2;
static void __fastcall Marker2() { g_marker2 = 2; }

// monitor_swap (tools/monitor_swap.py; John Morris' sub-weapons, then Headdy's heads): the extra's swap index, 0 at each
// stage load; every item monitor that breaks while it plays (Hook_ItemBoxCheck) moves it on to the next of its
// swapCount entries. With swap shots (ExtraData.swapShots) the shot thrown is the one at the index.
static int g_swap = 0;
static int SwapIndex() { return g_swap; }
static const std::vector<ShotData>& Swaps() { return Extra(g_character).swapShots; }
static bool HasSwaps() { return !Swaps().empty(); }

static const ShotData& Data() { return HasSwaps() ? Swaps()[g_swap % Swaps().size()] : Extra(g_character).shot; }
static const ShotData& Data2() { return Extra(g_character).shot2; }
static bool HasSecond() { return Data2().motion != SHOT_NONE; }
static bool Active() { return g_on && g_character > 0 && Data().motion != SHOT_NONE; }
static uint8* Static() { return g_static && *g_static ? (uint8*)*g_static : nullptr; }
static uint16 ClassID() { return Static() ? *(uint16*)(Static() + S_CLASS) : 0; }
static StateMachine* StateOf(Entity* e) { return (StateMachine*)((uint8*)e + E_STATE); }
static Animator* AnimatorOf(Entity* e) { return (Animator*)((uint8*)e + E_ANIMATOR); }
static int32& HitCount(Entity* e) { return *(int32*)((uint8*)e + E_HIT_COUNT); }
static bool Second(Entity* e) { return (void*)StateOf(e)->state == (void*)Marker2; }
static bool Ours(Entity* e) {
    return e && ClassID() && e->classID == ClassID()
           && ((void*)StateOf(e)->state == (void*)Marker || (void*)StateOf(e)->state == (void*)Marker2);
}
// Our shots out now (their entities, checked each time: the engine clears a slot when it's reset); which: 0 all, 1 the
// first shot's, 2 the second's. g_outSwap: a swap shot's entry (the one thrown, whatever the index is now)
static Entity* g_out[8];
static int g_outSwap[8];
static const ShotData& DataOf(Entity* e) {
    if (Second(e))
        return Data2();
    if (HasSwaps())
        for (int k = 0; k < 8; k++)
            if (g_out[k] == e)
                return Swaps()[g_outSwap[k] % Swaps().size()];
    return Data();
}
static int OutCount(int which = 0) {
    int n = 0;
    for (Entity*& e : g_out) {
        if (e && !Ours(e))
            e = nullptr;
        n += e != nullptr && (which == 0 || Second(e) == (which == 2));
    }
    return n;
}
static int OutCountSwap(int entry) {  // (swap shots: only that entry's, as each has its own maxAlive)
    int n = 0;
    for (int k = 0; k < 8; k++)
        n += g_out[k] && Ours(g_out[k]) && g_outSwap[k] == entry;
    return n;
}

static const char* ClassName(uint16 classID) {
    for (auto& o : g_objectNames)
        if (o.first && *o.first && Readable(*o.first, 2) && *(uint16*)*o.first == classID)
            return o.second.c_str();
    return "?";
}
static bool Budget(int& n, int max = 40) { return n++ < max; }

// A homing shot (ShotData.motion SHOT_HOMING: Cream's Cheese) coming back (its phase, in the SuperHammer's gravity
// field as a boomerang's, not 0) hits nothing more
static int32& Phase(Entity* e) { return *(int32*)((uint8*)e + E_GRAVITY); }
static bool Returning(Entity* e) { return DataOf(e).motion == SHOT_HOMING && Phase(e) != 0; }
static bool AnyHitting() {
    for (Entity* e : g_out)
        if (e && Ours(e) && !Returning(e))
            return true;
    return false;
}

// Player 1, if it's the extra with a shot and one of its shots is out (and can hit)
static bool ShotPlayer(EntityPlayer* p) {
    return Active() && p && RSDK->GetEntitySlot(p) == 0 && OutCount() > 0 && AnyHitting();
}

// A homing shot's target search (HomingUpdate): while one seeks (g_seek.on, from where it is: g_seek.fromX / Y), every
// badnik checking player 1 through Player_CheckBadnikTouch (Hook_Touch) that's on screen is a target; the nearest (px
// across + down) is kept. The shot reads and resets it in its own update, so it holds a whole frame's worth.
static struct {
    bool on = false;
    int32 fromX = 0, fromY = 0;
    int64_t best = -1;  // -1: none
    int32 x = 0, y = 0;
} g_seek;
static void Seek(EntityPlayer* p, Entity* e) {
    if (!g_seek.on || !e || !p || !Active() || Data().motion != SHOT_HOMING || RSDK->GetEntitySlot(p) != 0 || Ours(e))
        return;
    Vector2 range = {0, 0};
    if (!RSDK->CheckOnScreen(e, &range))
        return;
    int64_t dx = (int64_t)e->position.x - g_seek.fromX, dy = (int64_t)e->position.y - g_seek.fromY;
    int64_t d = (dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy);
    if (g_seek.best < 0 || d < g_seek.best) {
        g_seek.best = d;
        g_seek.x = e->position.x;
        g_seek.y = e->position.y;
    }
}

template <class Call>
static auto AsAmy(EntityPlayer* p, Call call) {
    int32 id = p->characterID;
    p->characterID = ID_AMY_CHARACTER;
    auto r = call();
    if (p->characterID == ID_AMY_CHARACTER)
        p->characterID = id;
    return r;
}

// A touch made by our reach, not by the player's body (a shot, the Screen Nuke, Headdy's head, Marine's anchor, Max's
// ear). Many objects check a hitbox only to hurt whoever touches it. This build's exe does
// "if (Player_CheckBadnikTouch(player, self, &hitbox)) Player_Hurt(player, self)" at 0x1400a0c82 and 0x14021a3d2,
// and does the same with Player_FireHurt at 0x14028f377. So a shot touching a spiky part (MGZ's spiky badniks) hurt
// its owner; Amy's own hammer does the same in the game. The touch is remembered (the entity and the object
// updating), and a hurt from that entity during that same update is refused (ReachHurt, from the hurt hooks)
static struct {
    Entity* e = nullptr;
    Entity* self = nullptr;
} g_reach;
static Entity* Updating() {
    int slot = 0;
    return RSDK ? CurrentEntity(&slot) : nullptr;
}
static bool32 Reached(EntityPlayer* p, Entity* e, Hitbox* hitbox) {  // (true; remembered if his body isn't touching)
    if (!g_touch(p, e, hitbox)) {
        g_reach.e = e;
        g_reach.self = Updating();
    }
    return true;
}
static bool ReachHurt(EntityPlayer* p, Entity* e, const char* via) {  // true: refused
    if (!p || !e || e != g_reach.e || !RSDK || RSDK->GetEntitySlot(p) != 0 || Updating() != g_reach.self)
        return false;
    static int logs = 0;
    if (Budget(logs))
        Log("reach: %s from %s (slot %d) refused (a shot or reach touched it, not him)", via, ClassName(e->classID),
            RSDK->GetEntitySlot(e));
    return true;
}

static bool32 Hook_Touch(EntityPlayer* p, Entity* e, Hitbox* hitbox) {
    jugg::Note(e, jugg::JUGG_TOUCH);
    g_reach.e = nullptr;  // (each check starts afresh: a hurt right after it follows only this one)
    if (psycho::Touch(p, e))  // (Silver's Psychokinesis caught it: touched, so its own code breaks it; PsychoGrab.h)
        return true;
    if (StarTouch(p, e, hitbox))  // (Ristar's hands caught it: yanked in, not touched yet; StarGrab.h)
        return false;
    if (HeadTouch(p, e, hitbox))  // (Headdy's thrown head reached it: touched, his attack; HeadThrow.h)
        return Reached(p, e, hitbox);
    if (AnchorTouch(p, e, hitbox))  // (Marine's anchor reached it: touched, her attack; AnchorThrow.h)
        return Reached(p, e, hitbox);
    if (EarTouch(p, e, hitbox))  // (Max's ear reached it: touched, his attack; the ear snaps back)
        return Reached(p, e, hitbox);
    if (nights::LoopTouch(p, e))  // (inside NiGHTS' Paraloop: touched, his attack; NightsFlight.h)
        return Reached(p, e, hitbox);
    if (g_seek.on)  // (a homing shot seeking: this badnik is a target)
        Seek(p, e);
    bool32 r = g_touch(p, e, hitbox);
    if (!r && e && g_nuke > 0 && g_character > 0 && p && RSDK->GetEntitySlot(p) == 0) {
        // Tails Doll's Screen Nuke (abilities.py melee_nuke): anything on screen (16 px past its edges) is touched; the
        // game's own code then takes it as his attack (badniks, monitors, bosses). Bomb's (nukeReachX / Y): anything
        // whose position is in the box round him
        Vector2 range = {16 << 16, 16 << 16};
        int64_t dx = ((int64_t)e->position.x - p->position.x) >> 16, dy = ((int64_t)e->position.y - p->position.y) >> 16;
        bool reached = g_nukeReachX > 0 ? dx >= -g_nukeReachX && dx <= g_nukeReachX && dy >= -g_nukeReachY
                                              && dy <= g_nukeReachY
                                        : (bool)RSDK->CheckOnScreen(e, &range);
        if (reached) {
            static int logs = 0;
            if (Budget(logs))
                Log("nuke: touches %s (slot %d)", ClassName(e->classID), RSDK->GetEntitySlot(e));
            g_reach.e = e;  // (his body isn't touching it: g_touch said no)
            g_reach.self = Updating();
            return true;
        }
    }
    if (r || !e || !hitbox || !ShotPlayer(p) || !HammerCheckHit(e, hitbox, nullptr))
        return r;
    static int logs = 0;
    if (Budget(logs))
        Log("shot: touches %s (slot %d): Player_CheckBadnikTouch true", ClassName(e->classID), RSDK->GetEntitySlot(e));
    g_reach.e = e;  // (the shot's touch, not his body's: g_touch said no)
    g_reach.self = Updating();
    return true;
}

// no_stomp (abilities.py; the user, 2026-10-02: Joe Musashi, Ray Poward, Mega Man, Axel, Gilius): his jump isn't an
// attack, his roll / Slide is. Around the game's Player_CheckBadnikBreak (badniks), _CheckBossHit and ItemBox_CheckHit
// (Hook_Break, Hook_BossHit, Hook_ItemBoxCheck), player 1's animation ID is shown to it as the game decides by it, then put
// back (unless the call set one of its own: a hurt):
//   - a badnik, while he's in the air in his own jump pose (the Jump animation's frames: not one of his moves shown as the
//     jump) and not Super: ANI_FALL, not an attack, so the game hurts him as walking into it does (shields, invincibility
//     (its timer counts anyway) and the post-hit blink protect as ever). Bosses and monitors still take the jump;
//   - the Slide (ground_slide: g_ab.puddle running, on the ground): ANI_JUMP, an attack, for badniks, bosses and monitors.
// The roll is the game's own (shown in his "Rolling" slide pose: RollCurl), an attack already. Walls: AsKnuckles.
namespace stomp {
static bool On(EntityPlayer* p) {
    return p && g_character > 0 && g_extraFrames && RSDK && Extra(g_character).abilities.noStomp && RSDK->GetEntitySlot(p) == 0;
}
static const void* JumpFrames() {  // (the Jump animation's frames in his file)
    Animator a = {};
    RSDK->SetSpriteAnimation(g_extraFrames, ANI_JUMP, &a, true, 0);
    return (const void*)a.frames;
}
static bool JumpPose(EntityPlayer* p) {
    return !p->onGround && p->animator.animationID == ANI_JUMP && p->superState == 0
           && (const void*)p->animator.frames == JumpFrames();
}
static bool Sliding(EntityPlayer* p) {
    return Extra(g_character).abilities.groundSlide && g_ab.puddle > 0 && p->onGround && !Hurt(p);
}
// Walls break for the Slide and the roll as for Knuckles (AsKnuckles)
static bool Breaks(EntityPlayer* p) {
    return On(p) && !Hurt(p) && (Sliding(p) || (p->onGround && p->animator.animationID == ANI_JUMP));
}
template <typename Call>
static auto Around(EntityPlayer* p, bool badnik, Call call) -> decltype(call()) {
    int shown = -1, saved = 0;
    if (On(p)) {
        if (Sliding(p) && p->animator.animationID != ANI_JUMP)
            shown = ANI_JUMP;
        else if (badnik && JumpPose(p))
            shown = ANI_FALL;
    }
    if (shown >= 0) {
        saved = p->animator.animationID;
        p->animator.animationID = shown;
    }
    auto r = call();
    if (shown >= 0 && p->animator.animationID == shown)
        p->animator.animationID = saved;
    return r;
}
}  // namespace stomp

static bool32 BreakInner(EntityPlayer* p, Entity* e, bool32 destroy);
static bool32 Hook_Break(EntityPlayer* p, Entity* e, bool32 destroy) {
    return stomp::Around(p, true, [&] { return BreakInner(p, e, destroy); });
}

static bool32 BreakInner(EntityPlayer* p, Entity* e, bool32 destroy) {
    jugg::Note(e, jugg::JUGG_BADNIK);
    bool32 caught = false;
    if (psycho::Breaks(p, e, destroy, &caught))  // (Psychokinesis: broken as his attack; PsychoGrab.h)
        return caught;
    if (!e || !ShotPlayer(p) || !HammerAlreadyHit((uint16)RSDK->GetEntitySlot(e))) {
        bool32 broke = g_break(p, e, destroy);
        if (broke && g_spinWatch && p && RSDK->GetEntitySlot(p) == 0)  // (a Spin Attack broke it: her bounce)
            g_spinHit = true;
        return broke;
    }
    bool32 r = AsAmy(p, [&] { return g_break(p, e, destroy); });
    static int logs = 0;
    if (Budget(logs))
        Log("shot: Player_CheckBadnikBreak on %s (as Amy's hammer): %s", ClassName(e->classID), r ? "broken" : "not broken");
    return r;
}

static bool32 BossHitInner(EntityPlayer* p, Entity* e);
static bool32 Hook_BossHit(EntityPlayer* p, Entity* e) {
    return stomp::Around(p, false, [&] { return BossHitInner(p, e); });  // (no_stomp's Slide hits bosses)
}

static bool32 BossHitInner(EntityPlayer* p, Entity* e) {
    jugg::Note(e, jugg::JUGG_BOSS);
    if (psycho::Refuses(p, e))  // (Psychokinesis caught a boss: refused, no hit; PsychoGrab.h)
        return false;
    if (!e || !ShotPlayer(p) || !HammerAlreadyHit((uint16)RSDK->GetEntitySlot(e))) {
        bool32 hit = g_bossHit(p, e);
        if (hit && g_spinWatch && p && RSDK->GetEntitySlot(p) == 0)  // (a Spin Attack hit it: her bounce)
            g_spinHit = true;
        return hit;
    }
    bool32 r = AsAmy(p, [&] { return g_bossHit(p, e); });
    static int logs = 0;
    if (Budget(logs))
        Log("shot: Player_CheckBossHit on %s (as Amy's hammer): %s", ClassName(e->classID), r ? "hit" : "no hit");
    return r;
}

static uintptr_t ItemBoxCheck(Entity* box);

// monitor_swap: a monitor this call broke (its state changed, and it isn't a bump from below: that sets its velocity to
// -0x20000 and its falling state, as Mania's ItemBox_CheckHit does) moves the swap index on, while an extra with a swap
// list plays (whatever broke it: the player, the whip, a shot)
static uintptr_t Hook_ItemBoxCheck(Entity* box) {
    int count = g_character > 0 ? Extra(g_character).abilities.swapCount : 0;
    bool ninjutsu = ninja::On() || pots::On();  // (Joe's Ninjutsu: a broken monitor stores a magic, Ninjutsu.h; Gilius' pots, PotMagic.h)
    void* was = box && (count > 0 || ninjutsu) ? (void*)StateOf(box)->state : nullptr;
    EntityPlayer* p1 = RSDK ? (EntityPlayer*)RSDK->GetEntity(0) : nullptr;
    uintptr_t r = stomp::Around(p1, false, [&] { return ItemBoxCheck(box); });  // (no_stomp's Slide breaks monitors)
    if (box && ninjutsu && (void*)StateOf(box)->state != was && box->velocity.y != -0x20000) {
        ninja::MonitorBroke();
        pots::MonitorBroke();
    }
    if (box && count > 0 && (void*)StateOf(box)->state != was && box->velocity.y != -0x20000) {
        g_swap = (g_swap + 1) % count;
        const char* sound = Extra(g_character).abilities.swapSound;
        if (sound)
            PlaySound(sound);
        Log("monitor swap: the monitor at slot %d broke: entry %d of %d", RSDK->GetEntitySlot(box), g_swap + 1, count);
    }
    return r;
}

static uintptr_t ItemBoxCheck(Entity* box) {
    EntityPlayer* p = Active() && RSDK ? (EntityPlayer*)RSDK->GetEntity(0) : nullptr;
    if (!box || !ShotPlayer(p)) {
        if (!box || !g_spinWatch)
            return g_itemBoxCheck(box);
        void* was = (void*)StateOf(box)->state;  // (a Spin Attack broke it: her bounce)
        uintptr_t r = g_itemBoxCheck(box);
        if ((void*)StateOf(box)->state != was)
            g_spinHit = true;
        return r;
    }
    void* before = (void*)StateOf(box)->state;  // (its state machine, as every S3&K object's: the box's state changes when it breaks)
    uintptr_t r = AsAmy(p, [&] { return g_itemBoxCheck(box); });
    static int logs = 0;
    if ((void*)StateOf(box)->state != before && Budget(logs))
        Log("shot: ItemBox_CheckHit (as Amy's hammer): the monitor at slot %d broke", RSDK->GetEntitySlot(box));
    return r;
}

// SuperHammer's stage load, wrapped: after the game's (Amy's art for Amy, the throw sound), our art while an extra with
// a shot plays (the engine keeps it for the stage: stage scope)
static void Hook_StageLoad() {
    g_stageLoad();
    memset(jugg::g_class, 0, sizeof(jugg::g_class));  // (this stage's classes: Juggernaut)
    if (g_flashAt >= 0 || g_flashDirty)  // a Screen Nuke's flash cut by a stage change (death, next act): put back now
        ::FlashRestore("stage load");
    g_frames = 0xFFFF;
    g_cooldown = 0;
    g_busterCharge = 0;
    g_seek.on = false;
    // What a monitor gave him (John's sub-weapon, Joe's magic, Gilius' pots) is carried through a seamless act
    // transition (the game stores the player for it: globals->atlEnabled, still set while the new act's objects load);
    // any other stage load (a death, a new game, the level select) starts afresh, as before
    if (ActTransitionLoad()) {
        ninja::Carry();  // (Joe's held magic kept, a cast in progress dropped: Ninjutsu.h)
        pots::Carry();  // (Gilius' pots kept, a quake in progress dropped: PotMagic.h)
        if (g_character > 0)
            Log("shot: stage load: an act transition: sub-weapon %d, held items carried over", g_swap);
    } else {
        g_swap = 0;  // (monitor_swap: the first entry at each stage's start)
        ninja::Reset();  // (Joe's Ninjutsu: nothing held at each stage's start, Ninjutsu.h)
        pots::Reset();  // (Gilius' pots: none at each stage's start, PotMagic.h)
    }
    psycho::Reset();  // (a likeness is the last stage's sprites: gone)
    nights::Reset();  // (NiGHTS' flight, meter and loop: each stage starts afresh; NightsFlight.h)
    volt::Reset();  // (Pulseman's charge and ball: each stage starts afresh; Voltteccer.h)
    afterImage::Clear();
    for (Entity*& e : g_out)
        e = nullptr;
    if (!Active() || !Static())
        return;
    g_frames = RSDK->LoadSpriteAnimation("3K_Players/Shot.bin", SCOPE_STAGE);
    uint16 amy = *(uint16*)(Static() + S_FRAMES);
    if (g_frames != 0xFFFF)
        *(uint16*)(Static() + S_FRAMES) = g_frames;
    Log("shot: stage load: SuperHammer class %d (FindObject %d), its art %d (was %d), %s (%s, kind %d)", ClassID(),
        RSDK->FindObject("SuperHammer"), g_frames, amy,
        g_frames == 0xFFFF ? "3K_Players/Shot.bin NOT loaded: no shots" : "3K_Players/Shot.bin", KindKey(g_character),
        g_character);
}

// monitor_swap's HUD icon (tools/monitor_swap.py "swap_icon": John Morris' sub-weapon): the HUD's draw, wrapped: after
// the game's HUD, a translucent black box at the top middle of the screen and in it the current entry's shot art
// (Shot.bin's animation g_swap, frame 0: its flight's first frame), screen relative, while the extra plays and neither
// the title card nor the act results are up. The box: the largest entry's frame plus ICON_PAD_X / ICON_PAD_Y, ICON_TOP
// from the top (monitor_swap.py ICON_*, the same numbers as Sonic 1/2 and CD). The screen's centre from the engine's
// ScreenInfo (the EngineInfo that LinkGameLogicDLL got: its pointer checked by its size / centre values, never
// written); none found: no icon.
constexpr int ICON_TOP = 8, ICON_PAD_X = 4, ICON_PAD_Y = 3, ICON_ALPHA = 160, ICON_INK_ALPHA = 2;
// The screen: the engine's ScreenInfo (RSDKv5U's RSDKScreenInfo: a 1280x240 16-bit frame buffer, then position, size and
// center, in px), through the game's own copy of EngineInfo's screenInfo pointer (LinkGameLogicDLL at 0x1400ad750 stores
// EngineInfo+0x60 at 0x142e70190; its sceneInfo, +0x20, at 0x142e70188, checked against SCENE_INFO). Camera's "center"
// is not the screen's: it's the camera's world position (AddCamera's target), so the icon and the marker never drew
// (the user, 2026-09-30). Checked every call: a size that isn't a plausible screen, or a centre that isn't half of it:
// nothing drawn.
struct ScreenView {
    int32 left, top, w, h;
};
static bool Screen(ScreenView* v) {
    auto** scene = (SceneInfo**)0x142e70188;
    auto** screen = (uint8**)0x142e70190;
    if (!Readable(scene, 8) || *scene != SCENE_INFO || !Readable(screen, 8) || !*screen)
        return false;
    const uint8* at = *screen + 1280 * 240 * 2;
    if (!Readable(at, 6 * sizeof(int32)))
        return false;
    const int32* f = (const int32*)at;  // position x, y; size x, y; center x, y
    if (f[2] < 256 || f[2] > 1280 || f[3] < 200 || f[3] > 240 || f[4] != f[2] / 2 || f[5] != f[3] / 2)
        return false;
    *v = {f[0], f[1], f[2], f[3]};
    return true;
}
static bool ScreenCentreX(int32* cx) {
    ScreenView v{};
    if (!Screen(&v))
        return false;
    *cx = v.w / 2;
    return true;
}

static bool Showing(const char* object) {  // an entity of that object is active (the title card, the results)
    int32 id = RSDK->FindObject(object);
    return id > 0 && RSDK->GetEntityCount((uint16)id, true) > 0;
}

typedef void (*IconDrawFn)(void);
static void IconNote(int why, const char* what) {  // (each reason the icon isn't drawn, logged once)
    static unsigned noted = 0;
    if (!(noted & (1u << why))) {
        noted |= 1u << why;
        Log("swap icon: not drawn: %s", what);
    }
}

// (Since 2026-10-02 the fallback only: HudPass below draws them from a draw-group hook.) Drawn from the Player's own
// draw, in an extra pass: Hook_PlayerUpdate adds player 1 to ICON_GROUP (the HUD's draw
// group) each frame, and PlayerDraw draws only the icon there. (It was drawn from the S3&K HUD object's draw, but
// Origins draws its own HUD and keeps that object hidden: the icon showed only while the game's HUD slid in for the
// Angel Island miniboss, then flew off with it; the user, 2026-09-29.)
constexpr uint8 ICON_GROUP = 14;
static void DrawIcon() {
    static bool first = true;
    if (first) {
        first = false;
        Log("swap icon: the icon pass runs");
    }
    if (g_character <= 0 || !RSDK)
        return;
    if (!g_on) return IconNote(0, "the shot system is off");
    if (g_frames == 0xFFFF) return IconNote(1, "no shot frames loaded");
    if (!HasSwaps()) return IconNote(2, "the extra has no monitor_swap list");
    const ExtraAbilities& c = Extra(g_character).abilities;
    int32 cx = 0;
    if (!c.swapIcon) return IconNote(3, "swapIcon off");
    if (Showing("TitleCard") || Showing("ActClear")) return IconNote(4, "title card / results up (normal)");
    if (!ScreenCentreX(&cx)) return IconNote(5, "no screen info");
    int n = (int)Swaps().size(), w = 0, h = 0;
    for (int k = 0; k < n; k++) {
        SpriteFrame* f = RSDK->GetFrame(g_frames, k, 0);
        if (f) {
            w = std::max(w, (int)f->frame.width);
            h = std::max(h, (int)f->frame.height);
        }
    }
    if (!w || !h) return IconNote(6, "its frames have no size");
    static bool drawn = false;
    if (!drawn) {
        drawn = true;
        Log("swap icon: drawing at x %d (frames %dx%d)", cx, w, h);
    }
    int bw = w + 2 * ICON_PAD_X, bh = h + 2 * ICON_PAD_Y;
    Entity* self = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (!self || !Readable(self, sizeof(Entity)))
        return;
    uint8 fx = self->drawFX, ink = self->inkEffect, dir = self->direction;  // (DrawSprite draws with the HUD's own)
    self->drawFX = 0;
    self->inkEffect = 0;
    self->direction = 0;
    RSDK->DrawRect(cx - bw / 2, ICON_TOP, bw, bh, 0x000000, ICON_ALPHA, ICON_INK_ALPHA, true);
    Animator icon{};
    RSDK->SetSpriteAnimation(g_frames, (uint16)(g_swap % n), &icon, true, 0);
    Vector2 pos = {cx << 16, (ICON_TOP + bh / 2) << 16};
    RSDK->DrawSprite(&icon, &pos, true);
    self->drawFX = fx;
    self->inkEffect = ink;
    self->direction = dir;
}

static void DrawHudPieces() {  // (the HUD pass's pieces: HudPass, or the old icon pass)
    DrawIcon();
    treasure::Draw();  // (Rouge's Treasure Sense marker: TreasureSense.h)
    ninja::Draw();  // (Joe's held Ninjutsu magic: Ninjutsu.h)
    nights::Draw();  // (NiGHTS' flight meter: NightsFlight.h)
    pots::Draw();  // (Gilius' pots: PotMagic.h)
}

static int g_hudOk = -1;  // the HUD pass (below): -1 not checked yet, 0 off (the old icon pass), 1 on
static IconDrawFn g_playerDraw = nullptr;
static void PlayerDraw() {  // the Player's draw: in the old icon pass (player 1 in ICON_GROUP; HudPass off), only the icon
    if (g_hudOk == 0 && Readable(SCENE_INFO, sizeof(SceneInfo)) && SCENE_INFO->currentDrawGroup == ICON_GROUP
        && SCENE_INFO->entitySlot == 0 && SCENE_INFO->entity && SCENE_INFO->entity->drawGroup != ICON_GROUP) {
        DrawHudPieces();
        return;
    }
    g_playerDraw();
    if (Readable(SCENE_INFO, sizeof(SceneInfo)) && SCENE_INFO->entitySlot == 0)
        pots::DrawRocks();  // (Gilius' Earthquake boulders, after him: PotMagic.h)
    if (Readable(SCENE_INFO, sizeof(SceneInfo)) && SCENE_INFO->entitySlot == 0)
        psycho::DrawCarried();  // (Silver carrying a caught badnik's likeness: in front of him, PsychoGrab.h)
}

static IconDrawFn PlayerIconWrap(IconDrawFn draw) {
    if (draw != (IconDrawFn)PlayerDraw)
        g_playerDraw = draw;
    return PlayerDraw;
}

// The HUD pass (the user, 2026-10-02: "Joe's box has a tendency to disappear in S3K"). The pieces above (John's
// sub-weapon, Joe's magic, Gilius' pots, NiGHTS' meter, Rouge's marker) were drawn from player 1's own draw, queued
// once more in ICON_GROUP; but the engine draws an entity only while it's visible, so they went with him: every
// other 4 frames of the blink after a hit, and whenever the game hides him (tubes, cannons, cutscenes), or when his
// update didn't queue him. Now they're drawn from the engine's draw-group hook (SetDrawGroupProperties' hookCB, the way
// the game's own water drops its palette for the HUD), with no entity: the hook of HUD_GROUP, the last group, runs
// after everything in the HUD's group and before that group's own entities (the pause menu, the fades). From this
// build's exe (objdump, never run): SetDrawGroupProperties (0x1400e60c0) stores sorted at +0x1298 and hookCB at +0x1290
// of drawGroups[group] (0x12a8 bytes each, the lea in its code), and the scene draw (0x1400e6249) calls a group's
// hookCB before its entities. A hook the game set there is kept and called first (chained); the code checked once,
// any mismatch: the old icon pass (QueueIcon queues player 1 in ICON_GROUP again).
constexpr uint8 HUD_GROUP = 15;
constexpr uintptr_t SET_DRAW_GROUP = 0x1400e60c0;
constexpr size_t DRAW_GROUP_SIZE = 0x12a8, DRAW_GROUP_HOOK = 0x1290;
static IconDrawFn g_gameHudHook = nullptr;  // (the game's own hook on HUD_GROUP, chained)
static IconDrawFn* HudHookField() {
    static IconDrawFn* field = nullptr;
    if (g_hudOk < 0) {
        static const uint8 CODE[] = {0x80, 0xf9, 0x10, 0x73, 0x20, 0x0f, 0xb6, 0xc1, 0x48, 0x69, 0xc8, 0xa8, 0x12, 0x00,
                                     0x00, 0x48, 0x8d, 0x05};
        static const uint8 STORES[] = {0x89, 0x94, 0x01, 0x98, 0x12, 0x00, 0x00, 0x4c, 0x89, 0x84, 0x01, 0x90, 0x12, 0x00, 0x00};
        const uint8* c = (const uint8*)SET_DRAW_GROUP;
        g_hudOk = 0;
        if (Readable(c, 0x30) && !memcmp(c, CODE, sizeof(CODE)) && !memcmp(c + 0x16, STORES, sizeof(STORES))) {
            uint8* groups = (uint8*)(c + 0x16) + *(const int32*)(c + 0x12);  // (the lea: rip-relative)
            field = (IconDrawFn*)(groups + HUD_GROUP * DRAW_GROUP_SIZE + DRAW_GROUP_HOOK);
            g_hudOk = Readable(field, sizeof(*field)) ? 1 : 0;
            Log("HUD pass: draw groups at %p, group %d's hook %s", (void*)groups, HUD_GROUP,
                g_hudOk ? "used" : "NOT readable: the old icon pass");
        } else {
            Log("HUD pass: SetDrawGroupProperties at %p is DIFFERENT: the old icon pass", (void*)c);
        }
    }
    return g_hudOk == 1 ? field : nullptr;
}

static bool HudWanted() {
    return g_character > 0 && RSDK
        && (Extra(g_character).abilities.swapIcon || treasure::Pass() || ninja::Pass() || nights::Pass() || pots::Pass());
}

static void HudPass() {
    if (g_gameHudHook)
        g_gameHudHook();
    if (!HudWanted() || !Readable(SCENE_INFO, sizeof(SceneInfo)))
        return;
    auto* p = (Entity*)RSDK->GetEntity(0);  // (player 1 a Player: a stage, not the blue spheres or a menu)
    int32 playerClass = RSDK->FindObject("Player");
    if (!p || !Readable(p, sizeof(Entity)) || playerClass <= 0 || p->classID != playerClass)
        return;
    static Entity plain;  // (no entity: the draws' "current entity" is a blank one, then put back)
    memset(&plain, 0, sizeof(plain));
    plain.visible = true;
    Entity* was = SCENE_INFO->entity;
    uint16 wasSlot = SCENE_INFO->entitySlot;
    SCENE_INFO->entity = &plain;
    DrawHudPieces();
    SCENE_INFO->entity = was;
    SCENE_INFO->entitySlot = wasSlot;
}

// Each frame after player 1's update while an extra plays: the HUD pass's hook in place (a scene load or the game's own
// SetDrawGroupProperties can take it out: what's there then is the game's, kept and chained); the old icon pass if the
// hook isn't known
static void QueueIcon() {
    if (g_character <= 0 || !RSDK)
        return;
    if (IconDrawFn* field = HudHookField()) {
        if (*field != HudPass) {
            g_gameHudHook = *field;
            *field = HudPass;
            static int logs = 0;
            if (Budget(logs, 20))
                Log("HUD pass: hook set on group %d (the game's there: %p)", HUD_GROUP, (void*)g_gameHudHook);
        }
        return;
    }
    if (HudWanted())
        RSDK->AddDrawListRef(ICON_GROUP, 0);
}

static void Destroy(Entity* e, const char* why) {
    static int logs = 0;
    if (Budget(logs, 60))
        Log("shot: gone at %d,%d after %d frames (%s)", e->position.x >> 16, e->position.y >> 16, StateOf(e)->timer, why);
    RSDK->ResetEntity(e, 0, nullptr);  // (as the game's own update does: a blank entity)
}

// A dropped animal's landing puff (motion "drop", Flicky): S3&K's Explosion, made the way Player_CheckBadnikBreak makes
// a badnik's (0x1401dd62f: CreateEntity(Explosion, data 1, x, y), then Global/Destroy.wav). From the exe: its create
// (0x1401cb970) stores the data as its type (+0x84) and plays animation <type> for types 0-6; its update's default
// path (types 0-4, 0x1401cc57d) and its late update (type 6, 0x1401cbc9c) hurt players (Player_FireHurt) only when its
// +0xAC field is set, which only the game's own spawner (0x1401cb740) sets; CreateEntity zeroes the entity, so ours is
// harmless. The class is found by name and the code checked once; any mismatch: no puff.
constexpr uintptr_t EXPLOSION_CREATE = 0x1401cb970, EXPLOSION_STATIC = 0x143db55d0;
constexpr int EXPLOSION_TYPE_BADNIK = 1;
static int g_puffOk = -1;  // -1 not checked yet, 0 off, 1 on
static void Puff(Entity* shot) {
    struct Check {
        uintptr_t at;
        uint8 bytes[12];
        size_t size;
    };
    static const Check CHECKS[] = {
        {0x1401cba19, {0x88, 0x93, 0x84, 0x00, 0x00, 0x00}, 6},  // create: type = data
        {0x1401cba25, {0x80, 0xfa, 0x07, 0x73}, 4},  // (types 0-6: animation <type>)
        {0x1401cc57d, {0x83, 0xbb, 0xac, 0x00, 0x00, 0x00, 0x00, 0x0f, 0x84}, 9},  // update: hurt only if +0xAC
        {0x1401cbc9c, {0x83, 0xbb, 0xac, 0x00, 0x00, 0x00, 0x00, 0x0f, 0x84}, 9},  // late update: likewise
        {0x1401dd62f, {0xbb, 0x01, 0x00, 0x00, 0x00, 0x45, 0x8b, 0x46, 0x08, 0x8b, 0xd3}, 11},  // badnik break: type 1
    };
    uint16 cls = RSDK->FindObject("Explosion");
    if (!cls)  // (not in this stage's list: no puff here)
        return;
    if (g_puffOk < 0) {
        bool ok = true;
        for (const Check& c : CHECKS)
            ok = ok && Readable((void*)c.at, c.size) && memcmp((void*)c.at, c.bytes, c.size) == 0;
        // its registration's static: the class the name gave (and its create where it's registered)
        void** st = (void**)EXPLOSION_STATIC;
        ok = ok && Readable(st, 8) && *st && Readable(*st, 2) && *(uint16*)*st == cls
             && Readable((void*)EXPLOSION_CREATE, 4) && memcmp((void*)EXPLOSION_CREATE, "\x40\x53\x48\x83", 4) == 0;
        g_puffOk = ok;
        Log("shot: drop puff: %s", ok ? "on, S3&K's Explosion type 1 (the badnik puff: no hurt, +0xAC left 0)"
                                        : "off (Explosion not found or its code differs)");
    }
    if (g_puffOk != 1)
        return;
    Entity* x = RSDK->CreateEntity(cls, (void*)(intptr_t)EXPLOSION_TYPE_BADNIK, shot->position.x, shot->position.y);
    if (x && x->classID == cls)
        PlaySound("Global/Destroy.wav");
}

// A boomerang's flight (ShotUpdate, after the hit and lifetime checks; ShotData's notes): out ahead, slowing, then back
// to player 1 wherever she is now, caught (gone) within catchRadius. No terrain. Its phase is in the SuperHammer's
// gravity field (ours: 0 out, 1 coming back). It stops at its first hit like the others (HitCount, before this), so the
// SuperHammer's hit list never carries an enemy from the way out into the way back.
static void BoomerangUpdate(Entity* e, const ShotData& s) {
    EntityPlayer* p = (EntityPlayer*)RSDK->GetEntity(0);
    if (!p)
        return Destroy(e, "no player");
    int32& phase = *(int32*)((uint8*)e + E_GRAVITY);
    int dir = (e->direction & 1) ? -1 : 1;
    if (phase == 0) {  // out: her own forward speed along (so she doesn't run into it), its own slowing down
        e->position.x += e->velocity.x + dir * std::max(0, dir * p->velocity.x);
        e->velocity.x -= dir * s.decel;
        if (dir * e->velocity.x <= 0) {
            e->velocity.x = 0;
            phase = 1;
        }
    } else {  // back: toward her hand (s.y below her centre), plus her own velocity, so running doesn't outpace it
        auto home = [&](int32& v, int gap) {
            int target = std::clamp(gap / 8, -s.returnSpeed, s.returnSpeed);
            v += std::clamp(target - v, -s.returnAccel, s.returnAccel);
        };
        home(e->velocity.x, p->position.x - e->position.x);
        home(e->velocity.y, p->position.y + (s.y << 16) - e->position.y);
        e->position.x += e->velocity.x + p->velocity.x;
        e->position.y += e->velocity.y + p->velocity.y;
        int catchAt = s.catchRadius << 16;
        if (std::abs(p->position.x - e->position.x) < catchAt
            && std::abs(p->position.y + (s.y << 16) - e->position.y) < catchAt)
            return Destroy(e, "caught");
    }
    if (!RSDK->CheckOnScreen(e, &e->updateRange))
        return Destroy(e, "offscreen");
    RSDK->ProcessAnimation(AnimatorOf(e));
}

// A homing shot's flight (ShotUpdate, after the lifetime check; ShotData's notes: Cream's Cheese). Seeking (phase 0):
// at the nearest target the badniks reported since its last update (g_seek), or straight on (plus her forward speed
// along) with none; seekFrames of those in a row (g_idle) or its first hit (HitCount: the SuperHammer's hit list) and it
// comes back (phase 1), hitting nothing more (AnyHitting), as a boomerang does. Gone (caught, offscreen, lifetime in
// ShotUpdate): the cooldown starts then. No terrain. Drawn facing the way it flies.
static int g_idle[8];
static void HomingGone(Entity* e, const ShotData& s, const char* why) {
    g_seek.on = false;
    g_cooldown = s.cooldown;
    Destroy(e, why);
}
static void HomingUpdate(Entity* e, const ShotData& s) {
    EntityPlayer* p = (EntityPlayer*)RSDK->GetEntity(0);
    if (!p)
        return HomingGone(e, s, "no player");
    int k = 0;
    while (k < 8 && g_out[k] != e)
        k++;
    int& idle = g_idle[k < 8 ? k : 0];
    int32& phase = Phase(e);
    auto steer = [](int32& v, int gap, int div, int top, int acc) {
        int target = std::clamp(gap / div, -top, top);
        v += std::clamp(target - v, -acc, acc);
    };
    if (phase == 0 && HitCount(e) > 0)
        phase = 1;  // (its first hit: back to her)
    if (phase == 0) {
        if (g_seek.best >= 0) {  // a target: steer at it
            idle = 0;
            steer(e->velocity.x, g_seek.x - e->position.x, 4, s.seekSpeed, s.seekAccel);
            steer(e->velocity.y, g_seek.y - e->position.y, 4, s.seekSpeed, s.seekAccel);
            e->position.x += e->velocity.x;
            e->position.y += e->velocity.y;
        } else {  // none: straight on, her forward speed along
            int along = (e->velocity.x > 0 && p->velocity.x > 0) || (e->velocity.x < 0 && p->velocity.x < 0) ? p->velocity.x : 0;
            e->position.x += e->velocity.x + along;
            e->position.y += e->velocity.y;
            if (++idle >= s.seekFrames)
                phase = 1;  // (its speed kept: it swings round)
        }
    } else {  // back: toward her hand (s.y below her centre), plus her own velocity
        steer(e->velocity.x, p->position.x - e->position.x, 8, s.returnSpeed, s.returnAccel);
        steer(e->velocity.y, p->position.y + (s.y << 16) - e->position.y, 8, s.returnSpeed, s.returnAccel);
        e->position.x += e->velocity.x + p->velocity.x;
        e->position.y += e->velocity.y + p->velocity.y;
        int catchAt = s.catchRadius << 16;
        if (std::abs(p->position.x - e->position.x) < catchAt
            && std::abs(p->position.y + (s.y << 16) - e->position.y) < catchAt)
            return HomingGone(e, s, "caught");
    }
    g_seek.on = phase == 0;  // (the next search, from where it is now)
    g_seek.best = -1;
    g_seek.fromX = e->position.x;
    g_seek.fromY = e->position.y;
    if (!RSDK->CheckOnScreen(e, &e->updateRange))
        return HomingGone(e, s, "offscreen");
    if (e->velocity.x > 0x4000)
        e->direction = 0;
    else if (e->velocity.x < -0x4000)
        e->direction = 1;
    RSDK->ProcessAnimation(AnimatorOf(e));
}

// Our shot's update (the game's SuperHammer update for anything else): its motion, terrain, lifetime
static void ShotUpdate(Entity* e) {
    const ShotData& s = DataOf(e);
    if (HitCount(e) > 0 && s.pierce)  // ("pierce": it flies on; its hit list, which the game fills anew, starts over: one
        HitCount(e) = 0;              // frame's touches at most, so a boss it passes isn't hit again once it's gone by)
    if (HitCount(e) > 0 && s.motion != SHOT_HOMING)  // (a homing shot comes back after its hit: HomingUpdate)
        return Destroy(e, "hit something");
    if (s.motion == SHOT_NONE)
        return Destroy(e, "no shot now");
    if (++StateOf(e)->timer > s.lifetime)
        return s.motion == SHOT_HOMING ? HomingGone(e, s, "lifetime") : Destroy(e, "lifetime");
    if (Phase(e) == BURNING) {  // (a swap shot's flames, burning where it landed: ShotData.burnAnim, John's Holy Water)
        if (!RSDK->CheckOnScreen(e, &e->updateRange))
            return Destroy(e, "offscreen (burning)");
        RSDK->ProcessAnimation(AnimatorOf(e));
        return;
    }
    if (s.motion == SHOT_BOOMERANG)
        return BoomerangUpdate(e, s);
    if (s.motion == SHOT_HOMING)
        return HomingUpdate(e, s);
    uint16 layers = e->collisionLayers;
    uint8 plane = e->collisionPlane;
    int r = s.radius << 16;
    if (s.motion == SHOT_BOUNCE || s.motion == SHOT_DROP || s.motion == SHOT_DIP)  // (a dip's gravity pulls it up)
        e->velocity.y = std::min(e->velocity.y + s.gravity, s.maxFall);
    // ahead: a wall (a tile solid from the sides at its leading edge, above its middle so a floor or a gentle slope
    // isn't one; either wall mode, whichever face the point is past: platforms solid only from the top don't count)
    e->position.x += e->velocity.x;
    int ahead = e->velocity.x < 0 ? -r - 0x10000 : r + 0x10000;
    if (s.terrain && e->velocity.x  // ("terrain" false: nothing solid ends it, John's axe)
        && (RSDK->ObjectTileCollision(e, layers, CMODE_LWALL, plane, ahead, -r / 2, false)
            || RSDK->ObjectTileCollision(e, layers, CMODE_RWALL, plane, ahead, -r / 2, false)))
        return Destroy(e, "wall");
    e->position.y += e->velocity.y;
    if (!s.terrain) {
    } else if (s.motion == SHOT_GROUND) {  // along the floor, gripped to it (slopes too); none within 14 px: a ledge's end
        if (!RSDK->ObjectTileGrip(e, layers, CMODE_FLOOR, plane, 0, r, 14))
            return Destroy(e, "ledge");
    } else if (s.motion == SHOT_BOUNCE) {
        if (e->velocity.y >= 0 && RSDK->ObjectTileCollision(e, layers, CMODE_FLOOR, plane, 0, r, true))
            e->velocity.y = s.bounce;  // (on the floor: set there)
        else if (e->velocity.y < 0 && RSDK->ObjectTileCollision(e, layers, CMODE_ROOF, plane, 0, -r, true))
            e->velocity.y = 0;
    } else if (e->velocity.y > 0) {  // (straight aimed down, a drop: a floor below its leading edge ends it; up: a ceiling)
        if (RSDK->ObjectTileCollision(e, layers, CMODE_FLOOR, plane, 0, r + 0x10000, false)) {
            if (s.motion == SHOT_DROP && s.burnAnim >= 0) {  // landed: it bursts into its flames there, for burnLifetime
                e->velocity.x = 0;
                e->velocity.y = 0;
                Phase(e) = BURNING;
                StateOf(e)->timer = std::max(0, s.lifetime - s.burnLifetime);
                RSDK->SetSpriteAnimation(g_frames, s.burnAnim, AnimatorOf(e), true, 0);
                return;
            }
            if (s.motion == SHOT_DROP)
                Puff(e);
            return Destroy(e, "floor");
        }
    } else if (e->velocity.y < 0) {
        if (RSDK->ObjectTileCollision(e, layers, CMODE_ROOF, plane, 0, -r - 0x10000, false))
            return Destroy(e, "ceiling");
    }
    if (!RSDK->CheckOnScreen(e, &e->updateRange))
        return Destroy(e, "offscreen");
    if (!s.cycle && !s.aimFrames)  // (a cycle or aim_frames shot keeps the frame its throw picked)
        RSDK->ProcessAnimation(AnimatorOf(e));
}

static void Hook_Update() {
    Entity* e = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (Ours(e)) {
        ShotUpdate(e);
        if (Ours(e))
            psycho::Animate(e);  // (a thrown badnik's likeness keeps its own animation)
    } else {
        g_update();
    }
}

// SuperHammer's draw, wrapped: a shot carrying a caught badnik's likeness draws that (Psychokinesis: PsychoGrab.h)
static void (*g_draw)(void) = nullptr;
static void Hook_Draw() {
    Entity* e = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    if (Ours(e) && psycho::Draw(e))
        return;
    g_draw();
}

// Throw one (Abilities, on Y): false if it can't now. An aimed shot (ShotData.aim) goes where the d-pad points as Y is
// pressed: x from left / right, y from up (and down in the air: on the ground it's crouching), nothing held: forward;
// holding a side turns him to it first when `turn` (standing or in the air). Diagonals: the same speed overall.
// which 2: the second shot (Data2, Shot.bin's animation 1, marked Marker2)
static Entity* g_lastThrown = nullptr;  // (the last Throw's entity: Psychokinesis gives it its likeness)
static bool Throw(EntityPlayer* p, bool turn, int which = 1, int forceDir = 0) {
    const ShotData& s = which == 2 ? Data2() : Data();
    static int logs = 0;
    uint16 cls = ClassID();
    bool swap = which == 1 && HasSwaps();  // (a swap shot: the current entry's, counted apart)
    if (!cls || g_frames == 0xFFFF || (swap ? OutCountSwap(g_swap) : OutCount(HasSecond() ? which : 0)) >= s.maxAlive)
        return false;
    int32& rings = *(int32*)((uint8*)p + RINGS);
    if (s.rings > 0 && rings < s.rings)  // ("rings": each throw costs them; fewer, no throw and no sound: John's)
        return false;
    int slot = -1;
    for (int i = 0; i < 8; i++)
        if (!g_out[i]) {
            slot = i;
            break;
        }
    if (slot < 0)
        return false;
    g_high = false;
    bool left = p->direction & 1;
    int dir = left ? -1 : 1;
    if (forceDir) {  // (a slam's: one each way, at its own speed alone)
        dir = forceDir;
        left = dir < 0;
    }
    int ax = dir, ay = 0;  // the aim (unaimed: forward)
    if (s.aim) {
        ax = p->right ? 1 : p->left ? -1 : 0;
        ay = p->up ? -1 : p->down && !p->onGround && s.aimDown ? 1 : 0;  // (aimDown false: 5 directions in the air too)
        if (!ax && !ay)
            ax = dir;
        if (ax && turn) {
            p->direction = ax < 0 ? 1 : 0;
            left = ax < 0;
            dir = ax;
        }
    }
    g_aimK = ay == 0 ? 0 : (ay < 0 ? 1 : 3) + (ax == 0 ? 1 : 0);  // (ShotData.aimPose: the pose's frame)
    int step = s.x << 16;  // (aimed: s.x px out along the aim, from s.y px below his centre)
    bool ground = s.hasGround && p->onGround && !s.aim;  // (thrown standing on the ground: ShotData "ground")
    int sx = ground ? s.groundX : s.x, sy = ground ? s.groundY : s.y;
    Entity* e = s.aim ? RSDK->CreateEntity(cls, p, p->position.x + ax * step, p->position.y + (s.y << 16) + ay * step)
                      : RSDK->CreateEntity(cls, p, p->position.x + dir * (sx << 16), p->position.y + (sy << 16));
    if (!e || e->classID != cls) {
        if (Budget(logs))
            Log("shot: CreateEntity(SuperHammer %d) failed", cls);
        return false;
    }
    // (the game's create has set it up as Amy's hammer, thrown by p: active, visible, draw group, flip drawing; now ours)
    RSDK->SetSpriteAnimation(g_frames, which == 2 ? 1 : swap ? g_swap % (int)Swaps().size() : 0, AnimatorOf(e), true, 0);
    g_outSwap[slot] = swap ? g_swap : 0;
    if (s.rings > 0)
        rings -= s.rings;
    if (s.aim) {
        int axis = ax && ay ? (int)((int64_t)s.speed * 46341 >> 16) : s.speed;  // (a diagonal: speed / sqrt 2 per axis)
        int along = std::max(0, ax * p->velocity.x);  // (his own speed along its x, so he doesn't run into it)
        e->velocity.x = ax * (axis + along);
        e->velocity.y = ay * axis;
    } else if (s.motion == SHOT_BOOMERANG || s.motion == SHOT_HOMING) {  // (its own speed alone: BoomerangUpdate /
                                                                          // HomingUpdate add hers, live)
        e->velocity.x = dir * s.speed;
        e->velocity.y = 0;
        if (s.motion == SHOT_HOMING) {  // (seeking, no target yet: the badniks report from now on)
            g_idle[slot] = 0;
            g_seek.on = true;
            g_seek.best = -1;
            g_seek.fromX = e->position.x;
            g_seek.fromY = e->position.y;
        }
    } else {
        int forward = forceDir || !s.carry ? 0 : std::max(0, dir * p->velocity.x);  // (his own speed forward along, so he doesn't run
                                                                          // into it)
        g_high = s.hasUp && p->up;  // up held: the up throw's own numbers (ShotData "up": Bean's high throw)
        e->velocity.x = dir * ((g_high ? s.upSpeed : ground ? s.groundSpeed : s.speed) + forward);
        e->velocity.y = s.motion == SHOT_BOUNCE ? (g_high ? s.upStartVY : ground ? s.groundStartVY : s.startVY)
                                                : ground ? s.groundStartVY : s.startVY;
    }
    if (s.cycle) {  // each throw the next frame of the art, held (ShotUpdate doesn't animate it)
        Animator* a = AnimatorOf(e);
        int count = a->frameCount > 0 ? a->frameCount : 1;
        g_next %= count;
        a->frameID = g_next++;
        a->timer = 0;
    }
    if (s.aim && s.aimFrames) {  // its aim's frame, held: 0 level, 1 forward-up, 2 up, 3 forward-down, 4 down
        Animator* a = AnimatorOf(e);
        int k = ay == 0 ? 0 : (ay < 0 ? 1 : 3) + (ax == 0 ? 1 : 0);
        a->frameID = a->frameCount > k ? k : 0;
        a->timer = 0;
        if (ax)  // (drawn the way it flies, even thrown backwards on the run)
            left = ax < 0;
    }
    *(int32*)((uint8*)e + E_GRAVITY) = 0;  // (ours: ShotUpdate; a boomerang's phase, 0: out)
    e->direction = left ? 1 : 0;
    e->collisionLayers = p->collisionLayers;
    e->collisionPlane = p->collisionPlane;
    HitCount(e) = 0;
    StateOf(e)->state = which == 2 ? Marker2 : Marker;
    StateOf(e)->timer = 0;
    g_out[slot] = e;
    g_lastThrown = e;
    g_cooldown = s.cooldown;
    if (!s.sound.empty())
        PlaySound(s.sound.c_str());
    if (Budget(logs))
        Log("shot: thrown (slot %d, %d out) at %d,%d, velocity %d,%d, layers %d plane %d%s", RSDK->GetEntitySlot(e),
            OutCount(), e->position.x >> 16, e->position.y >> 16, e->velocity.x, e->velocity.y, p->collisionLayers, p->collisionPlane,
            g_high ? ", up throw" : "");
    return true;
}

// Y's throw: one, or with "both_ways" (Mephiles' Crystal Shot) a pair, forward and back, each at its own speed alone
static bool ThrowY(EntityPlayer* p, bool turn) {
    if (!Data().bothWays)
        return Throw(p, turn);
    int dir = p->direction & 1 ? -1 : 1;
    if (!Throw(p, false, 1, dir))
        return false;
    Throw(p, false, 1, -dir);
    return true;
}

// ShotData.poseAlways (Big's cast): the throw pose shows whatever he's doing. On the ground at any speed (the game
// picks his walk / run each frame and this goes over it; he keeps moving), ended by a jump, a roll (ANI_JUMP on the
// ground), a hit, an object holding him, or a ledge (then the fall's walk). In the air over whatever shows until its
// frames run out, landing, a hit or an object: in place of the jump ball it's an attack, shown to the game as the jump
// (as the other poses: the jump's move stays ready); over anything else it's itself. Anything else giving him an
// animation meanwhile (a move's, a spring's) is what comes back after it (throwPrev), as the jump ball does.
static void PoseAlways(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    const ShotData& s = Data();
    const bool first = g_ab.throwPose == s.pose;
    const int id = p->animator.animationID;
    auto showFrame = [&]() {
        int count = p->animator.frameCount;
        if (count > 0)
            p->animator.frameID = count - 1;
        p->animator.timer = 0;
    };
    if (!g_ab.throwAir) {
        if (air || Hurt(p) || Held(p) || id == ANI_JUMP) {  // a jump or a roll, a hit, an object, a ledge
            g_ab.throwPose = 0;
            if (air && id == ANI_EXTRA_SHOT)  // (off a ledge: the fall's walk)
                RSDK->SetSpriteAnimation(g_extraFrames, ANI_WALK, &p->animator, true, 0);
            return;
        }
        PlayExtraAnimation(p, ANI_EXTRA_SHOT, false, first);
        showFrame();
        if (--g_ab.throwPose == 0)
            RSDK->SetSpriteAnimation(g_extraFrames, p->groundVel != 0 ? ANI_WALK : ANI_IDLE, &p->animator, true, 0);
        return;
    }
    if (!air || Hurt(p) || Held(p)) {  // landing, a hit, an object: the game's
        g_ab.throwPose = 0;
        return;
    }
    const int anim = c.shotAirFrames > 0 ? ANI_EXTRA_SHOT_AIR : ANI_EXTRA_SHOT;
    const bool ours = !first && (id == anim || (g_ab.throwPrev == ANI_JUMP && id == ANI_JUMP));
    if (!first && !ours)
        g_ab.throwPrev = id;  // something else gave him an animation: that comes back after
    if (--g_ab.throwPose == 0) {  // over: what it replaced
        if (g_ab.throwPrev == ANI_JUMP)
            BackToJump(p);
        else
            RSDK->SetSpriteAnimation(g_extraFrames, g_ab.throwPrev, &p->animator, true, 0);
        return;
    }
    PlayExtraAnimation(p, anim, g_ab.throwPrev == ANI_JUMP, !ours);
    showFrame();
}

// Y: throw; the pose shows the shot animation's last frame (the throw) for `pose` frames, standing or in the air (in
// the air as an attack, shown to the game as the jump, as the other air moves; standing still as itself)
static void Frame(EntityPlayer* p, const ExtraAbilities& c, bool air) {
    const ShotData& s = Data();
    if (s.onSlam || s.onGrab)  // (thrown by the Hammer Drop's landing: Slam, or by Psychokinesis; Y is the melee's)
        return;
    if (g_cooldown > 0)
        g_cooldown--;
    bool standing = !air && std::abs(p->groundVel) < 0x10000;
    // ("input" "down": down + Y, crouching or in the air; "autofire": Y held, one every cooldown frames)
    bool press = (s.autofire ? YDown(p) : YPressed(p)) && (!s.downOnly || p->down)
                 && (!s.upOnly || UpThrow(p, c, air));  // ("input" "up": up + Y, John's sub-weapons)
    if (c.sink && (g_ab.sink > 0 || (!air && DownHeld(p))))  // (down + Y on the ground: the Shadow Sink's, even while
        press = false;                                        // it cools down; none while he's sunk)
    if (HasSecond() && Data2().onCharge) {  // a charge shot: Y held charges; letting go of a full one throws it
        const ShotData& s2 = Data2();
        bool fire = false;
        if (YDown(p)) {
            g_busterCharge = std::min(g_busterCharge + 1, 0x7FFF);
            if (s2.chargeWait && g_cooldown > 0 && g_busterCharge >= s2.chargeFull)
                g_busterCharge = s2.chargeFull - 1;  // ("charge_wait": not full until the cooldown is over)
        } else {
            fire = g_busterCharge >= s2.chargeFull;
            g_busterCharge = 0;
        }
        if (Hurt(p))
            g_busterCharge = 0, fire = false;
        if (fire && Throw(p, air || standing, 2) && s2.pose > 0 && (air || standing) && !s.poseAlways) {
            g_ab.throwPose = s2.pose;  // (the first shot's pose)
            g_ab.throwAir = air;
            g_ab.throwHigh = false;
            g_ab.throwAim = -1;
            g_ab.pogo = false;
        }
    } else if (HasSecond() && p->down) {  // down + Y: the second shot's (no throw pose), the cooldown shared
        if (g_cooldown == 0 && press && !Hurt(p))
            Throw(p, air || standing, 2);
        press = false;
    }
    // ("pose_always": the pose at any speed too, not rolling: the roll goes on)
    bool posing = (air || standing || (s.poseAlways && p->animator.animationID != ANI_JUMP))
                  && g_ab.rocket == 0;  // (Sparkster's Rocket Burst: the shot goes, its pose doesn't take the animator)
    if (g_cooldown == 0 && press && !Hurt(p) && ThrowY(p, air || standing) && s.pose > 0 && posing) {
        if (s.poseAlways && air && !(g_ab.throwPose > 0 && g_ab.throwAir))  // (a pose still showing: what it replaced)
            g_ab.throwPrev = p->animator.animationID;
        g_ab.throwPose = s.pose;
        g_ab.throwAir = air;
        g_ab.throwHigh = g_high;
        g_ab.throwAim = g_aimK;
        g_ab.pogo = false;
    }
    if (g_ab.throwPose <= 0)
        return;
    if (s.poseAlways)
        return PoseAlways(p, c, air);
    bool keep = air ? g_ab.throwAir && p->animator.animationID == ANI_JUMP && !Hurt(p)
                    : !g_ab.throwAir && standing && !Hurt(p);
    int anim = air && c.shotAirFrames > 0 ? ANI_EXTRA_SHOT_AIR : ANI_EXTRA_SHOT;
    if (keep) {
        PlayExtraAnimation(p, anim, air, g_ab.throwPose == s.pose);
        int count = p->animator.frameCount;
        if (count > 0)
            p->animator.frameID = s.aimPose ? std::min(std::max(g_ab.throwAim, 0), count - 1)  // (its aim's frame)
                                  : g_ab.throwHigh && s.upPose >= 0 && s.upPose < count ? s.upPose : count - 1;
        p->animator.timer = 0;
    }
    if (!keep || --g_ab.throwPose == 0) {
        g_ab.throwPose = 0;
        if (keep)
            RSDK->SetSpriteAnimation(g_extraFrames, air ? ANI_JUMP : ANI_IDLE, &p->animator, true, 0);
    }
}

// The Hammer Drop landed (Abilities): a slam shot ("input" "slam": Bark's shockwaves) goes out, one each way
static void Slam(EntityPlayer* p) {
    if (!Active() || !Data().onSlam)
        return;
    bool a = Throw(p, false, 1, -1), b = Throw(p, false, 1, 1);
    Log("slam: shockwaves %s / %s", a ? "left" : "-", b ? "right" : "-");
}

// At startup (before the game runs): check the prologues, hook the four functions; any failure leaves it all off
static void SetUp() {
    for (const Prologue& pr : PROLOGUES) {
        bool ok = Readable((void*)pr.at, pr.size) && memcmp((void*)pr.at, pr.bytes, pr.size) == 0;
        Log("shot: %s at %p: %s", pr.name, (void*)pr.at, ok ? "as expected" : "DIFFERENT (another game build?)");
        if (!ok) {
            Log("shot: off (the game plays as before; extras' shots do nothing)");
            return;
        }
    }
    struct { uintptr_t at; void* hook; void** original; } HOOKS[] = {
        {TOUCH, (void*)Hook_Touch, (void**)&g_touch}, {BREAK, (void*)Hook_Break, (void**)&g_break},
        {BOSS_HIT, (void*)Hook_BossHit, (void**)&g_bossHit}, {ITEMBOX_CHECK, (void*)Hook_ItemBoxCheck, (void**)&g_itemBoxCheck}};
    for (auto& h : HOOKS)
        if (MH_CreateHook((void*)h.at, h.hook, h.original) != MH_OK) {
            Log("shot: hooking %p failed: off", (void*)h.at);
            for (auto& u : HOOKS)
                MH_RemoveHook((void*)u.at);
            return;
        }
    for (auto& h : HOOKS)
        if (MH_EnableHook((void*)h.at) != MH_OK) {
            Log("shot: enabling the hook at %p failed: off", (void*)h.at);
            for (auto& u : HOOKS) {
                MH_DisableHook((void*)u.at);
                MH_RemoveHook((void*)u.at);
            }
            return;
        }
    g_on = true;
    Log("shot: on (4 hooks in; they act only while an extra with a shot plays and has one out)");
}

// SuperHammer's registration (Hook_RegisterObject): its statics, and our stage load and update around the game's
static void Register(void** staticVars, uint32 entitySize, uint32 staticSize, void (*&update)(void),
                     void (*&stageLoad)(void), void (*&draw)(void)) {
    if (!g_on)
        return;  // (off: SuperHammer left as it is)
    if ((int)entitySize != ENTITY_SIZE || (int)staticSize != STATIC_SIZE || !update || !stageLoad) {
        Log("shot: SuperHammer registers as %d / %d bytes (expected %d / %d): off", entitySize, staticSize, ENTITY_SIZE,
            STATIC_SIZE);
        g_on = false;
        return;
    }
    g_static = staticVars;
    if (update != Hook_Update) {
        g_update = update;
        update = Hook_Update;
    }
    if (stageLoad != Hook_StageLoad) {
        g_stageLoad = stageLoad;
        stageLoad = Hook_StageLoad;
    }
    if (draw && draw != Hook_Draw) {
        g_draw = draw;
        draw = Hook_Draw;
    }
    Log("shot: SuperHammer registered (statics at %p), its stage load, update and draw wrapped", (void*)staticVars);
}
}  // namespace shots

#include "StarGrab.h"  // Ristar's Grab, hang and Meteor Strike (tools/star_grab.py)
#include "HeadThrow.h"  // Headdy's Head Throw (tools/head_throw.py)
#include "AnchorThrow.h"  // Marine's Anchor Throw (tools/anchor_throw.py)
#include "WaterWalk.h"  // water walk: Marine's sea legs (tools/water_walk.py)
#include "TreasureSense.h"  // Rouge's Treasure Sense and Jewel Thief (tools/treasure_sense.py)
#include "Ninjutsu.h"  // Joe Musashi's Ninjutsu (tools/ninjutsu.py)
#include "PsychoGrab.h"  // Silver's Psychokinesis (abilities.py psycho_grab)
#include "EccoSwim.h"  // Ecco's free swim (abilities.py free_swim)
#include "NightsFlight.h"  // NiGHTS' free flight, Drill Dash and Paraloop (abilities.py free_flight)
#include "Voltteccer.h"  // Pulseman's Voltteccer (abilities.py voltteccer)
#include "PotMagic.h"  // Gilius' pot magic (tools/pot_magic.py)
#include "Ghost.h"

static void Abilities(EntityPlayer* p) {
    const ExtraAbilities& surgeOf = Extra(g_character).abilities;
    if (surgeOf.powerSurge)  // (before the physics: they follow it)
        PowerSurge(p, surgeOf);
    ApplyPhysics(p);
    const ExtraAbilities& c = Extra(g_character).abilities;
    bool air = !p->onGround;
    bool facingLeft = p->direction & 1;

    // jumpAbilityState goes to 1 when the player jumps; Sonic's own mid-air moves (insta-shield, drop
    // dash, shield moves) then take it further when jump is pressed again (verified in-game). For extras,
    // their own move replaces those: take the 1 and hand the game a 0.
    bool justJumped = false;
    // An object holding the player (the free-state gate): whatever move was going on ends, as a hit ends it, and the
    // jump's move is gone (so no press in there starts one). A 1 an object gives jumpAbilityState waits for the air
    // state (only Player_State_Air acts on it), as the game's own jump abilities do.
    bool held = Held(p);
    static bool wasHeld = false;
    if (held && !wasHeld) {
        int cooldown = g_ab.cooldown;
        g_ab = AbilityState{};
        g_ab.umbrella = 2;
        g_ab.cooldown = cooldown;
        NoteHeld("held (the extra's moves ended)", p);
    }
    wasHeld = held;
    if (held) {
        g_ab.ready = false;
        HeldStatus(p);
    }
    // extras built on Tails or Knuckles keep their base's own moves (flight; glide and climb)
    if (p->jumpAbilityState == 1 && Extra(g_character).base == 0 && !held) {
        g_ab.ready = true;
        justJumped = true;  // the press that started this jump isn't the second press
        p->jumpAbilityState = 0;
    }
    // Only a jump in progress counts: standing on bridges, rocks and other objects can read as "in the
    // air" here (the game settles object floors after the player's update), but not as the jump ball
    if (p->animator.animationID != ANI_JUMP)
        g_ab.ready = false;
    static bool wasAir = false;
    bool pressedInAir = air && wasAir && p->jumpPress && !justJumped;
    wasAir = air;
    if (!air) {
        g_ab.ready = false;
        g_ab.dash = 0;
        g_ab.bomb = 0;
        g_ab.hover = 0;
        g_ab.ear = 0;
        g_ab.umbrella = 0;
        g_ab.chaos = 0;
        g_ab.aimUsed = false;
        g_ab.kickUsed = false;
        g_ab.spirit = 0;
        g_ab.rocket = 0;
    }
    if (Hurt(p)) {
        g_ab.hammer = false;
        g_ab.glide = false;
    }
    if (Hurt(p)) {
        g_ab = AbilityState{};
        g_ab.umbrella = 2;
    }

    // the jump's move starts only from the air state itself (Mania's jump abilities run from Player_State_Air)
    bool freeAir = !g_stateNameSlot || (void*)p->state.state == g_playerStateAir;
    // Water swim (Big; abilities.py water_swim): underwater (gravity under 0x3800), a jump press in mid-air, in the jump
    // or a stroke, is a swim stroke instead of the jump's move (which it ends for this jump: no parasol underwater): up
    // at swimStroke (a faster rise is kept; letting go of jump doesn't cut it short), at most one every swimDelay frames,
    // as often as he likes. Only from the air state itself (the free-state gate), as the jump's moves.
    if (c.waterSwim) {
        if (g_ab.swimDelay > 0)
            g_ab.swimDelay--;
        int anim = p->animator.animationID;
        if (air && Gravity(p) < 0x3800 && pressedInAir && freeAir && !held && (anim == ANI_JUMP || anim == ANI_EXTRA_SWIM)) {
            g_ab.ready = false;
            if (g_ab.swimDelay == 0) {
                g_ab.swimDelay = c.swimDelay;
                if (p->velocity.y > -c.swimStroke)
                    p->velocity.y = -c.swimStroke;
                NoJumpCap(p);
                PlayExtraAnimation(p, ANI_EXTRA_SWIM, false, true);
            }
        }
    }
    if (g_ab.ready && pressedInAir && !freeAir)
        NoteHeld("jump press", p);
    bool trigger = g_ab.ready && pressedInAir && freeAir;
    if (trigger)
        g_ab.ready = false;

    // ability_cycle: only the active move's jump press starts it (the others' code runs on, with their own state)
    int copyMove = c.cycleCount > 0 ? c.cycleMoves[g_copy % std::min(c.cycleCount, 4)] : 0;
    auto moveTrigger = [&](int move) { return trigger && (copyMove == 0 || copyMove == move); };
    const bool trigDouble = moveTrigger(1), trigKick = moveTrigger(2), trigDash = moveTrigger(3), trigFloat = moveTrigger(4);

    if (c.tripleJump)  // (no mid-air move: the Triple Jump is in the jump itself)
        TripleJump(p, c, justJumped, air);

    // Jet Dash, then hover while jump is still held
    if (c.jetDash) {
        if (trigDash) {
            g_ab.dash = c.dashFrames;
            g_ab.hover = 0;
        }
        if (g_ab.dash > 0) {
            int speed = p->velocity.x < 0 ? -p->velocity.x : p->velocity.x;
            if (speed < c.dashSpeed)
                speed = c.dashSpeed;
            p->velocity.x = facingLeft ? -speed : speed;
            p->velocity.y = 0;
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, trigDash);
            if (--g_ab.dash == 0) {
                BackToJump(p);
                g_ab.hover = c.hover ? 1 : 0;
            }
        } else if (air && g_ab.hover > 0) {
            if (p->jumpHold && g_ab.hover <= c.hoverFrames) {
                p->velocity.y = c.hoverSink;
                PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
                g_ab.hover++;
            } else {
                if (g_ab.hover > 1)
                    BackToJump(p);
                g_ab.hover = 0;
            }
        }
    }

    // Rocket Ride (Robotnik; abilities.py rocket_ride, the fields keep its Bomb Jump names): bombFrames riding a rocket,
    // at least rideSpeed along (whichever way he's going) and rising at rideRise, an attack; a wall (his speed along
    // under half of rideSpeed) blows it up at once. Then the blast launches him up with half his speed along, hitting all
    // around him (the blast frames' hitbox, build_s3k_art.py). Then the parachute: holding jump once he's falling. As in
    // S1/S2, `bomb` counts down before each frame is shown. (Without rideSpeed: the old bomb beat, hanging still.)
    if (c.bombJump) {
        if (trigger) {
            g_ab.bomb = c.bombFrames + c.blastFrames + 1;
            g_ab.hover = 0;
            if (c.rideSpeed > 0) {
                int dir = facingLeft ? -1 : 1;
                p->velocity.x = dir * std::max(dir * p->velocity.x, c.rideSpeed);
                if (c.rideSound)
                    PlaySound(c.rideSound);
            } else {
                p->velocity.x /= 2;
            }
        }
        if (g_ab.bomb > 0 && p->animator.animationID != ANI_JUMP) {  // a spring or an object took over
            g_ab.bomb = 0;  // (and no parachute this jump)
        }
        else if (g_ab.bomb > 0) {
            if (c.rideSpeed > 0 && !trigger && g_ab.bomb > c.blastFrames + 1
                && std::abs(p->velocity.x) < c.rideSpeed / 2)  // a wall stopped the rocket: it blows up now
                g_ab.bomb = c.blastFrames + 1;
            if (--g_ab.bomb == 0) {  // the blast is over
                BackToJump(p);
                g_ab.hover = c.hover ? 1 : 0;
            } else {
                bool blast = g_ab.bomb <= c.blastFrames;
                if (g_ab.bomb == c.blastFrames) {
                    p->velocity.y = -c.bombLaunch;
                    if (c.rideSpeed > 0)
                        p->velocity.x /= 2;
                    NoJumpCap(p);  // as after a spring: letting go of jump doesn't cut the launch short
                    if (c.blastSound)
                        PlaySound(c.blastSound);
                    Log("rocket ride: blast");
                } else if (!blast && c.rideSpeed > 0) {  // riding: full speed along, whatever air drag does
                    int dir = p->velocity.x < 0 ? -1 : 1;
                    p->velocity.x = dir * std::max(dir * p->velocity.x, c.rideSpeed);
                    p->velocity.y = -c.rideRise;
                } else if (!blast) {
                    p->velocity.y = 0;
                }
                PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, trigger);
                p->animator.frameID = blast ? 1 + (c.blastFrames - g_ab.bomb) / c.blastTicks : 0;  // the timer picks the frame
                p->animator.timer = 0;
            }
        } else if (air && g_ab.hover > 0) {
            FallingHover(p, c);
        }
    }

    if (c.earGrapple)
        EarGrapple(p, c, trigger, air);
    if (c.spiritFlight)
        SpiritFlight(p, c, trigger, air);
    if (c.rocketBurst)
        RocketBurst(p, c, trigger, air);
    if (c.doubleJump)
        DoubleJump(p, c, trigDouble, air);
    if (c.puddleSlide || c.groundSlide) {
        bool start = c.groundSlide && g_slideStart;  // (Ray Poward's Slide: NoRollInput took the crouch's jump press)
        g_slideStart = false;
        PuddleSlide(p, c, trigger && c.puddleSlide, air, start);
    }
    if (c.wallCling)
        WallCling(p, c, air);
    if (c.thunderZip)
        ThunderZip(p, c, trigger, air);
    if (c.extremeGear)
        ExtremeGear(p, c, trigger, air);
    if (c.magnetic && !Hurt(p))
        Magnetic(p);
    if (c.charge)
        Charge(p, c, air);
    if (c.charge)
        Spark(p, c, air);  // (its Shine Spark: after the charge, which it ends as it's stored)
    if (c.spinAttack)
        SpinAttack(p, c, air);
    else
        g_spinWatch = false;
    if (c.highKick)
        HighKick(p, c, air);
    if (c.sink)
        Sink(p, c, air);
    if (c.phaseWarp)
        PhaseWarp(p, c, trigger, air);
    if (c.starGrab)
        StarGrab(p, c, air);
    if (c.headThrow)
        HeadThrow(p, c, air);
    if (c.anchorThrow)
        AnchorThrow(p, c, air);
    if (c.freeSwim)
        swim::Update(p, c, air);  // (Ecco's free swim, charge ram and leap: EccoSwim.h)
    if (c.freeFlight)
        nights::Update(p, c, air);  // (NiGHTS' free flight, Drill Dash and Paraloop: NightsFlight.h)
    if (c.voltteccer)
        volt::Update(p, c, air);  // (Pulseman's Voltteccer: Voltteccer.h)

    // Chaos Control: a flash (frozen in place), a quick warp forward, then a hop
    if (c.chaosControl) {
        if (trigger) {
            g_ab.chaos = c.chaosFreeze + c.chaosWarp;
            afterImage::Clear();
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        }
        if (g_ab.chaos > 0) {
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
            p->velocity.y = 0;
            int speed = g_ab.chaos > c.chaosWarp ? 0 : c.chaosSpeed;
            p->velocity.x = facingLeft ? -speed : speed;
            if (--g_ab.chaos == 0) {
                g_ab.chaos = -1;
                p->velocity.y = -c.chaosPop;
            }
            if (speed > 0)  // (the warp: a trail of afterimages behind him; Ghost.h)
                afterImage::Record(p);
        } else if (g_ab.chaos < 0) {
            if (air && p->velocity.y < 0)
                PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
            else {
                g_ab.chaos = 0;
                if (air)
                    BackToJump(p);
            }
        }
    }

    // Aimed dash (Blaze's Burst Dash): straight, or 45 degrees up / down if up / down is held when it starts.
    // aimDashY (Charmy's Stinger): Y starts it instead, once per airborne period, from the air state or Tails'
    // flight. It takes him out of the flight for good (jumpAbilityState 0, as the flight itself leaves it),
    // and holds off the flight while it lasts.
    if (c.aimDash) {
        bool start = trigger;
        if (c.aimDashY) {
            int a = p->animator.animationID;
            bool flying = Extra(g_character).base == 1 && a >= ANI_TAILS_FLY && a <= ANI_TAILS_SWIM_LIFT;
            bool airState = (void*)p->state.state == g_playerStateAir;
            start = g_playerStateAir && air && !g_ab.aimUsed && g_ab.aim == 0 && (airState || flying) && !Hurt(p)
                    && YPressed(p);
            if (start) {
                g_ab.aimUsed = true;
                g_ab.aimJumpState = flying ? 0 : p->jumpAbilityState;
                p->jumpAbilityState = 0;
                if (flying)
                    p->state.state = (void(__fastcall*)())g_playerStateAir;
                Log("stinger%s", flying ? " (out of flight)" : "");
            }
        }
        if (start) {
            g_ab.aim = c.dashFrames;
            g_ab.aimDir = p->up ? -1 : p->down ? 1 : 0;
            g_ab.aimLeft = facingLeft;
        }
        if (g_ab.aim > 0) {
            int anim = g_ab.aimDir < 0 ? ANI_EXTRA_ATTACK_UP : g_ab.aimDir > 0 ? ANI_EXTRA_ATTACK_DOWN : ANI_EXTRA_ATTACK;
            PlayExtraAnimation(p, anim, true, start);
            facingLeft = g_ab.aimLeft;  // turning around mid-dash doesn't redirect it
            p->direction = facingLeft ? 1 : 0;
            if (g_ab.aimDir == 0) {
                int speed = p->velocity.x < 0 ? -p->velocity.x : p->velocity.x;
                if (speed < c.dashSpeed)
                    speed = c.dashSpeed;
                p->velocity.x = facingLeft ? -speed : speed;
                p->velocity.y = 0;
            } else if (g_ab.aimDir < 0) {  // up: 45 degrees, or as configured (Vector: straight up)
                p->velocity.x = facingLeft ? -c.upX : c.upX;
                p->velocity.y = -c.upY;
            } else {
                p->velocity.x = facingLeft ? -c.diagX : c.diagX;
                p->velocity.y = c.diagY;
            }
            if (--g_ab.aim == 0 || !air) {
                g_ab.aim = 0;
                if (air)
                    BackToJump(p);
                if (air && c.aimDashY)
                    p->jumpAbilityState = g_ab.aimJumpState;
            }
        }
    }

    // Mighty's Hammer Drop (Mania Plus: Player_JumpAbility_Mighty, Player_State_MightyHammerDrop). The game's
    // air state keeps running during the drop (gravity and air control, as Mania's drop state does).
    if (c.hammerDrop) {
        bool water = Gravity(p) < 0x3800;
        if (trigger) {
            p->velocity.x >>= 1;
            p->velocity.y = water ? 0x80000 : 0xC0000;
            g_ab.hammer = true;
            PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
        }
        else if (g_ab.hammer) {
            if (!air && g_playerStateAir) {  // landed: bounce up in the ball, along the ground's angle
                int dropForce = Gravity(p) + (water ? 0x10000 : 0x20000);
                int groundVel = p->groundVel - (p->groundVel >> 2);
                int a = p->angle & 0xFF;
                p->velocity.x = (int)(((long long)groundVel * Cos256(a) + (long long)dropForce * Sin256(a)) >> 8);
                p->velocity.y = (int)(((long long)groundVel * Sin256(a) - (long long)dropForce * Cos256(a)) >> 8);
                p->onGround = false;
                p->angle = 0;  // as Mania does: a bounce off a slope with a tilted collision mode sank into it
                p->collisionMode = 0;  // floor
                p->state.state = (void(__fastcall*)())g_playerStateAir;
                // (no screen shake here: writing the camera's shake from the reference layout sent the screen
                // bouncing and the view underground in testing)
                shots::Slam(p);  // (a slam shot: before the bounce moves him, from where he landed)
                BackToJump(p);
                g_ab.hammer = false;
            }
            else if (p->velocity.y < 0 && std::abs(p->velocity.y + g_ab.hammerVY + Gravity(p)) <= 0x100) {
                // a badnik (which updates after the player) bounced him with Sonic's rule, -(speed + 2 gravity),
                // and this frame's gravity followed: Mania's Mighty plows on through instead, 1 px per frame slower
                p->velocity.y = g_ab.hammerVY - 0x10000 + Gravity(p);
                PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
            }
            else if (p->velocity.y <= 0x10000) {  // a spring or anything else sending him up ends it
                g_ab.hammer = false;
                BackToJump(p);
            }
            else {
                PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
            }
        }
    }

    g_ab.hammerVY = p->velocity.y;

    // Ray's glide (Mania Plus: Player_JumpAbility_Ray, Player_State_RayGlide). Hold forward to dive; let go
    // (or hold back) to swoop up, each swoop weaker than the last. Ends when jump is let go or he slows down.
    if (c.rayGlide)
        RayGlide(p, trigger, air);

    if (c.batGlide)
        BatGlide(p, c, air);
    if (c.screwKick)
        ScrewKick(p, c, trigKick, air, facingLeft);

    // Umbrella (Big) / psychic float (Silver): float down while jump is held, once per jump, for at most
    // floatFrames if set
    if (c.umbrella) {
        if (trigFloat) {
            g_ab.umbrella = 1;
            g_ab.floated = 0;
        }
        if (g_ab.umbrella == 1) {
            bool timeLeft = c.floatFrames == 0 || g_ab.floated++ < c.floatFrames;
            if (air && p->jumpHold && timeLeft) {
                if (p->velocity.y > c.umbrellaSink)
                    p->velocity.y = c.umbrellaSink;
                if (c.umbrellaAttack)  // Espio's Whirlwind: the float on the attack animation
                    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
                else
                    PlayExtraAnimation(p, ANI_EXTRA_HOVER, false, false);
            } else {
                g_ab.umbrella = 2;
                if (air)
                    BackToJump(p);
            }
        }
    }

    // Pogo: bounce on every landing while jump is held
    if (c.pogo) {
        if (trigger)
            g_ab.pogo = true;
        if (g_ab.pogo) {
            if (!air) {
                if (p->jumpHold && g_playerStateAir) {
                    p->velocity.y = -c.pogoSpeed;
                    p->onGround = false;
                    p->state.state = (void(__fastcall*)())g_playerStateAir;
                    PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, true);
                } else {
                    g_ab.pogo = false;
                }
            } else {
                PlayExtraAnimation(p, ANI_EXTRA_ATTACK, true, false);
            }
        }
    }

    // Shot (Fang's cork gun, Big's fishing line) on Y. The shot frames' hitbox reaches out to the cork/lure.
    // With shotAirFrames (Tikal's punch) the air shot has its own frames and reach: the timer runs for the longer
    // one, and a pose ends when its frames run out. shotStop: she stands still for it on the ground.
    // An extra with a real projectile (its package's "s3k.shot": Mario's fireball) throws that instead (shots::Frame);
    // if the shot system is off, its melee stays. A shot thrown with down + Y ("input" "down": Mecha's spike ball) keeps
    // the melee on Y alone (his Jet Boost).
    // ability_cycle: the attack moves share the attack animation; its frame is the active move's (its place in the cycle)
    if (c.cycleCount > 0 && (g_ab.dash > 0 || g_ab.doubleJump || g_ab.kick)) {
        p->animator.frameID = g_copy % std::min(c.cycleCount, 4);
        p->animator.timer = 0;
    }

    psycho::Update(p, c, air);  // (Silver's Psychokinesis: Y catches a badnik first, else the melee's Psychic Wave)
    bool downShot = shots::Active() && (shots::Data().downOnly || shots::Data().onSlam || shots::Data().onGrab  // (Y alone stays the melee;
                                        || shots::Data().upOnly);  // an up + Y shot's too: John's whip)
    if (shots::Active() && g_controllers)
        shots::Frame(p, c, air);
    if ((!shots::Active() || downShot) && c.shot && g_controllers) {
        const int total = std::max({c.shotFrames, c.shotAirFrames, c.meleeRunFrames, c.meleeUpFrames});
        if (g_ab.cooldown > 0)
            g_ab.cooldown--;
        // Espio's Leaf Swirl invisibility (shotBlink, set as the swirl ends): the post-hit blink, so nothing hurts him,
        // and shown as S1/S2's blink shows it (PlayerObject: hidden while the timer's bit 2 is set). Driven here too, so
        // he flickers whatever S3&K's own blink drawing does outside its hurt state; a hit or the timer's end: back.
        if (g_ab.leaf > 0) {
            int blink = g_blinkOffset >= 0 ? *(int*)((char*)p + g_blinkOffset) : 0;
            if (--g_ab.leaf == 0 || blink <= 0 || Hurt(p)) {
                g_ab.leaf = 0;
                p->visible = true;
            } else {
                p->visible = !(blink & 4);
            }
        }
        if (g_ab.shot == 0 && g_ab.cooldown == 0 && g_ab.spirit == 0 && psycho::WaveY(p) && !Hurt(p)  // (the orb already attacks;
                                                                                    // Psychokinesis first, PsychoGrab.h)
            && !(c.sink && (g_ab.sink > 0 || (!air && DownHeld(p))))  // (down + Y on the ground: the Shadow Sink's)
            && !(downShot && shots::Data().downOnly && p->down)  // (down + Y: the shot's)
            && !(downShot && shots::Data().upOnly && UpThrow(p, c, air))) {  // (up + Y: the shot's, John's sub-weapons)
            g_ab.shot = total;
            // melee_whip (John's): the pose by the d-pad as Y is pressed: 1 crouching (down on the ground), 2 up-forward
            // (up and a side in the air: UpThrow left it to the whip), 3 down (in the air); 0 the plain ones
            g_ab.whipAim = !c.shotWhip ? 0 : !air ? (p->down ? 1 : 0) : p->down ? 3 : p->up ? 2 : 0;
            // melee_run / melee_up (Axel's Grand Upper and Dragon Wing; abilities.py VARIANT_POSES): on the ground, up
            // held with meleeUpRings rings (taken; fewer: the plain melee) is 5, else running (at least meleeRunSpeed
            // either way) 4
            if (!air && (c.meleeUp || c.meleeRunSpeed > 0)) {
                int32& rings = *(int32*)((uint8*)p + shots::RINGS);
                if (c.meleeUp && p->up && rings >= c.meleeUpRings) {
                    rings -= c.meleeUpRings;
                    g_ab.whipAim = 5;
                } else if (c.meleeRunSpeed > 0 && std::abs(p->groundVel) >= c.meleeRunSpeed) {
                    g_ab.whipAim = 4;
                }
            }
            g_ab.cooldown = c.shotCooldown;
            g_ab.pogo = false;
            // (melee_run / melee_up's own sound, if it has one, else the melee's)
            const char* sound = g_ab.whipAim == 5 && c.meleeUpSound    ? c.meleeUpSound
                                : g_ab.whipAim == 4 && c.meleeRunSound ? c.meleeRunSound
                                                                       : c.shotSound;
            if (sound)  // (Jet's Tornado: a whoosh)
                PlaySound(sound);
            Log("shot");
            if (c.cycleCount > 0) {  // ability_cycle: the melee's pose is the switch; the next move is active
                g_copy = (g_copy + 1) % std::min(c.cycleCount, 4);
                if (air) {  // the move going on or used this jump ends; an unused jump keeps its press for the new one
                    g_ab.dash = 0;
                    g_ab.doubleJump = false;
                    g_ab.kick = false;
                    if (g_ab.umbrella == 1)
                        g_ab.umbrella = 2;
                }
                Log("copycat: move %d of %d", g_copy + 1, c.cycleCount);
            }
        }
        if (g_ab.shot > 0) {
            bool airShot = air && c.shotAirFrames > 0;
            int frames = (airShot ? c.shotAirFrames : c.shotFrames) / c.shotTicks;
            int anim = airShot ? ANI_EXTRA_SHOT_AIR : ANI_EXTRA_SHOT;
            if (c.shotWhip) {  // (John's whip poses: crouching on the ground, up-forward or down in the air; the same
                               // frame count as the plain ones, abilities.py melee_whip)
                if (!air && g_ab.whipAim == 1)
                    anim = ANI_EXTRA_ATTACK;
                else if (air && g_ab.whipAim == 2)
                    anim = ANI_EXTRA_ATTACK_UP;
                else if (air && g_ab.whipAim == 3)
                    anim = ANI_EXTRA_ATTACK_DOWN;
            }
            bool runPose = g_ab.whipAim == 4 && c.meleeRunFrames > 0, upPose = g_ab.whipAim == 5 && c.meleeUpFrames > 0;
            if (runPose || upPose) {  // (melee_run / melee_up: their own frames, on the ground and in the air alike)
                airShot = false;
                anim = runPose ? ANI_EXTRA_ATTACK_UP : ANI_EXTRA_ATTACK_DOWN;
                frames = (runPose ? c.meleeRunFrames : c.meleeUpFrames) / c.shotTicks;
            }
            static int shown = -1;  // (the pose shown last frame: another one starts from its own first frame)
            PlayExtraAnimation(p, anim, true, g_ab.shot == total || airShot != g_ab.shotAir || anim != shown);
            shown = anim;
            g_ab.shotAir = airShot;
            p->animator.frameID = std::min((total - g_ab.shot) / c.shotTicks, frames - 1);  // the timer picks the frame
            p->animator.timer = 0;
            if (c.shotStop && !air && !runPose) {
                p->groundVel = 0;
                p->velocity.x = 0;
            }
            if (runPose && c.meleeRunBoost > 0) {  // melee_run's boost: at least meleeRunBoost the way he faces
                int dir = facingLeft ? -1 : 1;
                int& v = air ? p->velocity.x : p->groundVel;
                v = std::max(v * dir, c.meleeRunBoost) * dir;
            }
            if (c.shotBoost > 0) {  // a burst of speed (Mecha's Jet Boost): at least shotBoost the way he faces
                int dir = facingLeft ? -1 : 1;
                int& v = air ? p->velocity.x : p->groundVel;
                v = std::max(v * dir, c.shotBoost) * dir;
                if (air)
                    p->velocity.y = 0;  // level in the air
            }
            if (c.shotHang && air) {  // hanging still in the air (Tails Doll's Screen Nuke; 0, not against the gravity:
                p->velocity.x = 0;    // a monitor breaks for a jump that isn't rising)
                p->velocity.y = 0;
            }
            if (c.nukeAt >= 0 && total - g_ab.shot == c.nukeAt) {  // the nuke (melee_nuke): its hit and its flash
                g_nuke = c.nukeHit;  // (counted down at each update's start: the targets update after him, this frame too)
                g_nukeReachX = c.nukeReachX;
                g_nukeReachY = c.nukeReachY;
                if (c.nukeFlashCount > 0)  // (Bomb's has no flash)
                    NukeFlashStart(c);
                if (c.nukeSound)
                    PlaySound(c.nukeSound);
                Log("screen nuke");
            }
            if (c.shotSafe && g_blinkOffset >= 0) {  // nothing hurts him meanwhile (Bomb's Self-Destruct; no flicker)
                int& blink = *(int*)((char*)p + g_blinkOffset);
                if (blink < 3)
                    blink = 3;
            }
            if (--g_ab.shot == 0 || (total - g_ab.shot) / c.shotTicks >= frames) {
                g_ab.shot = 0;
                RSDK->SetSpriteAnimation(g_extraFrames, air ? ANI_JUMP : ANI_IDLE, &p->animator, true, 0);
                if (c.shotBlink && g_blinkOffset >= 0) {  // Espio's Leaf Swirl: invisible, like after a hit
                    *(int*)((char*)p + g_blinkOffset) = c.shotBlink;
                    g_ab.leaf = c.shotBlink;
                    Log("leaf swirl: invisible for %d frames", c.shotBlink);
                }
                if (c.shotCost)  // Bomb's Self-Destruct: it costs him a normal hit
                    ShotCost(p, facingLeft);
            }
        }
    }
}

// ---------------------------------------------------------------- Player update hook
// RegisterObject is how the game hands the engine its objects: wrapping Player's update function
// gives us a hook every frame for every player, without another signature.
typedef void (*UpdateFn)(void* self);
static UpdateFn g_playerUpdate = nullptr;

static bool Readable(const void* p, size_t size) {
    MEMORY_BASIC_INFORMATION mbi{};
    if (!p || !VirtualQuery(p, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT)
        return false;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
        return false;
    return (const char*)p + size <= (const char*)mbi.BaseAddress + mbi.RegionSize;
}

// The entity being updated: SceneInfo's current entity (the fixed address from Ultrafix3kFixes). Origins
// doesn't pass it as an argument. Checked against the engine's own slot lookup.
static Entity* CurrentEntity(int* slotOut) {
    if (!Readable(SCENE_INFO, sizeof(SceneInfo)))
        return nullptr;
    Entity* e = SCENE_INFO->entity;
    if (!e || !Readable(e, sizeof(Entity)))
        return nullptr;
    int slot = RSDK->GetEntitySlot(e);
    if (slot != SCENE_INFO->entitySlot)
        return nullptr;
    if (!g_sceneInfo) {
        g_sceneInfo = SCENE_INFO;
        g_controllers = CONTROLLERS;
        Log("SceneInfo at %p checks out; controllers at %p", (void*)SCENE_INFO, (void*)CONTROLLERS);
    }
    *slotOut = slot;
    return e;
}

// ---------------------------------------------------------------- the blink timer (after-hit invulnerability)
// Not named in the reference structs: it's one of the unnamed ints between shield and superState (where Mania
// keeps its timers). Found by watching them after a hit: the blink timer jumps up and counts down by exactly 1
// per frame. Remembered in NoSwapS3K.ini [Debug] BlinkOffset.
static std::string IniPath();

static void FindBlinkTimer(EntityPlayer* p) {
    constexpr int FIRST = offsetof(EntityPlayer, shield) + 4, LAST = offsetof(EntityPlayer, superState);
    constexpr int COUNT = (LAST - FIRST) / 4;
    static int last[COUNT], run[COUNT], start[COUNT], watch = 0;
    if (g_blinkOffset >= 0)
        return;
    if (Hurt(p) && p->animator.animationID == ANI_HURT)
        watch = 400;  // watch for a while after a hit
    if (watch <= 0)
        return;
    watch--;
    for (int k = 0; k < COUNT; k++) {
        int v = *(int*)((char*)p + FIRST + 4 * k);
        if (v == last[k] - 1 && v > 0) {
            if (run[k]++ == 0)
                start[k] = last[k];
        }
        else {
            run[k] = 0;
        }
        last[k] = v;
        if (run[k] >= 40 && start[k] >= 60 && start[k] <= 200) {
            g_blinkOffset = FIRST + 4 * k;
            Log("blink timer found at +0x%X (counted down from %d)", g_blinkOffset, start[k]);
            char value[16];
            snprintf(value, sizeof(value), "%d", g_blinkOffset);
            WritePrivateProfileStringA("Debug", "BlinkOffset", value, IniPath().c_str());
            return;
        }
    }
}

static int g_playerUpdateLogs = 0;

// Rolling, for extras whose jump isn't a ball (extras.py "roll": Mario's is a fist-up leap): on the ground they
// curl up in their own "Rolling" animation. S3&K rolls in the Jump animation, so the curl is shown the way the
// attacking abilities are (PlayExtraAnimation): the game still sees ANI_JUMP (the roll hurts enemies) and leaves
// the frames alone, since it only switches animations when the ID changes. In the air the jump pose comes back.
// Rolling = on the ground in the Jump animation outside the air state, when the last frame was on the ground
// outside the air state too (a landing from a jump is one frame of Jump on the ground, before the ground state
// picks the walk).
static void RollCurl(EntityPlayer* p) {
    static void* curl = nullptr;       // the curl's frames, while shown
    static bool wasGrounded = false;   // last frame: on the ground, outside the air state
    if (curl && p->animator.frames != curl)
        curl = nullptr;  // something else took over (a spring, a hit, another animation)
    bool grounded = p->onGround && (void*)p->state.state != g_playerStateAir;
    // (a shot on the ground is shown as the jump too: not a roll)
    bool rolling = grounded && wasGrounded && p->animator.animationID == ANI_JUMP && g_ab.shot == 0;
    wasGrounded = grounded;
    if (rolling && !curl) {
        PlayExtraAnimation(p, ANI_EXTRA_ROLL, true, true);
        curl = p->animator.frames;
    } else if (curl && !p->onGround && p->animator.animationID == ANI_JUMP) {
        BackToJump(p);  // a jump out of the roll, or rolling off a ledge: the jump pose
        curl = nullptr;
    }
}

// No rolling, for extras that never curl into a ball (extras.py "no_roll": Gamma). S3&K starts a roll from its
// ground state when down is held while moving, and a Spin Dash from its crouch when jump is pressed (Mania's
// Player_State_Ground / Player_State_Crouch, the same code). So for the extra's update, its input function
// (stateInput: the StateMachine right before controllerID, as in Mania's layout) is wrapped: after it reads the
// pad, down is let go of while moving on the ground (no roll), and in a crouch when jump is pressed (the crouch
// then stands him up and jumps: a plain jump, no Spin Dash). Crouching still works; objects that force a roll
// (tubes) still do. His jump is still the game's jump, so it still attacks.
static void(__fastcall* g_realInput)() = nullptr;

static void __fastcall NoRollInput() {
    g_realInput();
    int slot = -1;
    auto* p = (EntityPlayer*)CurrentEntity(&slot);
    if (!p || slot != 0)
        return;
    const ExtraAbilities& c = Extra(g_character).abilities;
    if (c.sink && g_ab.sink > 0) {  // the Shadow Sink: no input at all while it lasts (Sink reads the pad itself)
        p->up = p->down = p->left = p->right = false;
        p->jumpPress = p->jumpHold = false;
        return;
    }
    if (c.charge && c.sparkSpeed > 0) {  // Heavy's Shine Spark (Spark)
        if (g_ab.spark > SPARK_ACTIVE) {  // flying: no control (and no jump out of a run along the ground)
            p->up = p->down = p->left = p->right = false;
            p->jumpPress = false;
            return;
        }
        int top = *(int*)((char*)p + 0x220);
        bool full = g_ab.charge != 0 && std::abs(g_ab.charge) > top;  // (the charge past his top speed, last frame)
        if (p->onGround && p->down && (full || g_ab.spark > 0)) {
            if (p->groundVel != 0) {  // no roll: at full charge down stores the spark (Spark), and none while it's stored
                g_sparkDown = full;
                p->down = false;
            } else if (p->jumpPress && g_ab.spark > 0) {
                p->down = false;  // a crouch's jump with one stored: a plain jump (then the launch), not a Spin Dash
            }
        }
    }
    if (!p->onGround)
        return;
    if (!c.groundSlide && !Extra(g_character).noRoll)  // (wrapped for the sink alone)
        return;
    if (c.groundSlide) {  // (an extra with the Slide, abilities.py ground_slide: Ray Poward, Mega Man)
        // down + jump from a crouch, or with slideRunning (Mega Man) out of a run too: the Slide, not a Spin Dash or
        // a jump. Checked before "no_roll" (Mega Man has both: its crouch rule used to turn his slide into a jump)
        bool crouch = p->animator.animationID == ANI_CROUCH;
        bool running = c.slideRunning && p->down && p->groundVel != 0 && g_ab.puddle == 0;
        if ((crouch || running) && p->jumpPress && !Hurt(p)) {
            p->down = false;  // (the crouch stands him up; no roll, and no jump)
            p->jumpPress = false;
            g_slideStart = true;
            return;
        }
        if (g_ab.puddle > 0 && p->groundVel != 0) {
            p->down = false;  // no roll out of the slide
            return;
        }
        if (!Extra(g_character).noRoll)
            return;
    }
    if (p->animator.animationID == ANI_CROUCH) {
        if (p->jumpPress)
            p->down = false;
    }
    else if (p->groundVel != 0) {
        p->down = false;
    }
}

static bool InGameCode(const void* fn) {
    static MODULEINFO info{};
    if (!info.SizeOfImage)
        GetModuleInformation(GetCurrentProcess(), GetModuleHandleA(nullptr), &info, sizeof(info));
    auto* base = (const char*)info.lpBaseOfDll;
    return (const char*)fn >= base && (const char*)fn < base + info.SizeOfImage;
}

// The input function a cutscene stores to give back later (the StateMachine at +0x378; Hook_PlayerUpdate)
constexpr int PLAYER_SAVED_INPUT = 0x378;

// Put NoRollInput in the player's stateInput for this update; returns it (to put the game's back), or null
static StateMachine* WrapInput(EntityPlayer* p) {
    auto* input = (StateMachine*)((char*)&p->controllerID - sizeof(StateMachine));
    void* fn = (void*)input->state;
    if (!fn || fn == (void*)NoRollInput)
        return nullptr;
    if (!InGameCode(fn)) {
        static bool logged = false;
        if (!logged)
            Log("no_roll: stateInput %p isn't game code: rolling not blocked", fn);
        logged = true;
        return nullptr;
    }
    if (g_realInput != input->state)
        Log("no_roll: wrapping the player's input function %p", fn);
    g_realInput = input->state;
    input->state = NoRollInput;
    return input;
}

// [Debug] Cheats=1: F7 (read on the key thread) asks for 100 rings and all 7 Chaos Emeralds, given here on the game's
// own thread (CheatEmeralds is below, with the globals)
static volatile LONG g_cheatRings = 0;
static void CheatEmeralds();
// The ring count in Origins' S3&K player entity (found with F6: 3 -> 8 after collecting 5 rings). The reference
// struct's `rings` (+0x1AC) is another field in this build.
constexpr int PLAYER_RINGS = 0xD0;
static_assert(shots::RINGS == PLAYER_RINGS, "the shots' ring count is the player's");

// Never drowning (abilities.py no_breathing: Metal, Gamma, Mecha Sonic, Chaos). The drown timer is the entity's int at
// +0x1C0 (Mania's drownTimer, the int before invincibleTimer +0x1C4 and blinkTimer +0x1CC): the Water object's update adds
// 1 to it each frame underwater (0x1401bab74) and plays the warning chimes, the countdown numbers and the drowning music
// at fixed values of it (120 frames and up), and a bubble shield holds it at 0. Holding it at 0 after every player
// update keeps it under 2, so none of that ever starts (the bubble shield's rule, without the shield).
constexpr int PLAYER_DROWN_TIMER = 0x1C0;
static void NoBreathing(EntityPlayer* p) {
    *(int32*)((uint8*)p + PLAYER_DROWN_TIMER) = 0;
}
// [Debug] Cheats=1, F6 (temporary): snapshots player 1's entity and logs the ints that changed since the last press
// (collect a few rings between two presses to find the ring count)
static volatile LONG g_playerProbe = 0;
static void PlayerProbe(const uint8* p) {
    constexpr size_t SIZE = 0x600;
    static std::vector<int> last;
    std::vector<int> now((const int*)p, (const int*)(p + SIZE));
    if (last.size() != now.size()) {
        last = now;
        Log("F6: player snapshot taken, collect a few rings and press again");
        return;
    }
    int shown = 0;
    for (size_t i = 0; i < now.size(); i++)
        if (now[i] != last[i] && shown < 60) {
            Log("F6: player +0x%zx: %d -> %d", i * 4, last[i], now[i]);
            shown++;
        }
    Log("F6: %d player ints shown (rings in the reference layout at +0x%zx)", shown, offsetof(EntityPlayer, rings));
    last = now;
}

// ---------------------------------------------------------------- Super, for every extra
// Origins' S3&K transforms on Y in mid-air, in the jump ball: in the base character's jump ability, which (as in Mania
// Plus's Player_JumpAbility_Sonic) only acts while jumpAbilityState is 1. Abilities() takes that 1 from extras built
// on Sonic (their own move replaces his), so the game never saw their Y. Before the game's update, a Y press in the
// jump ball, with the extra's move still unused this jump and no jump press, hands the 1 back: the game's own code then
// checks the emeralds and rings and transforms (its Super sparkles, music, palette, Super physics, which
// ApplyPhysics scales like any other values). If it doesn't transform, Abilities takes the 1 again, and Y is the
// extra's own move as before. Extras built on Tails or Knuckles keep their 1, so their base's own code already
// transforms. Either way, a Y press that transformed (superState went from 0) isn't also a Y move's (g_ySuper).
static bool JumpPressed(EntityPlayer* p) {
    int ctrl = p->controllerID;
    if (ctrl < 0 || ctrl > 4)
        ctrl = 1;
    const ControllerState& k = g_controllers[ctrl];
    return k.keyA.press || k.keyB.press || k.keyC.press || k.keyX.press;
}

static bool DownHeld(EntityPlayer* p) {  // (before the game's update: the pad itself, as YPressed)
    int ctrl = p->controllerID;
    if (ctrl < 0 || ctrl > 4)
        ctrl = 1;
    return g_controllers[ctrl].keyDown.down != 0;
}

static void SuperPress(EntityPlayer* p) {
    if (Extra(g_character).base != 0 || !g_ab.ready || p->superState != 0 || p->onGround
        || p->animator.animationID != ANI_JUMP || p->jumpAbilityState != 0 || !g_controllers)
        return;
    if (!YPressed(p) || JumpPressed(p))
        return;
    if (shots::Active() && (shots::Data().downOnly || (shots::HasSecond() && shots::Data2().downOnly)) && DownHeld(p))
        return;  // down + Y throws the extra's shot instead ("input" "down": Mecha's spike ball; shot2: Robotnik's bomb)
    p->jumpAbilityState = 1;
    Log("super: Y in the jump ball (%d rings): the game's jump ability gets it", *(int32*)((uint8*)p + PLAYER_RINGS));
}

// The extra's own colours glow while it's Super (superState 1 or 2: Mania's FADEIN, the transformation, and SUPER),
// pulsing toward SUPER_GLOW_TO as Super Sonic's palette cycles (96-176 of 256 over 40 frames), fading in over 24
// frames and out once Super ends (FADEOUT, DONE) at 4 per frame; back to 0 (superState 0), its exact colours are
// written once more. Water banks glow too: ApplyWaterPalettes tints the glowing colours. Extras without colours of
// their own (Metal Sonic) look like Sonic's, so the game's own Super palette does it for them.
static void SuperGlow(EntityPlayer* p) {
    static int phase = 0;
    if ((int)Extra(g_character).palette.size() == 0) {
        g_glow = 0;
        return;
    }
    int s = p->superState, next = 0;
    if (s == 1 || s == 2) {
        phase = (phase + 1) % 40;
        int target = 96 + 4 * (phase < 20 ? phase : 40 - phase);
        next = g_glow < target ? std::min(target, g_glow + 4) : std::max(target, g_glow - 4);
    } else if (s != 0) {
        next = std::max(0, g_glow - 4);
    }
    if (next == 0)
        phase = 0;
    if (next == g_glow && next == 0)
        return;
    if ((next > 0) != (g_glow > 0))
        Log("super glow %s (superState %d)", next > 0 ? "on" : "off", s);
    g_glow = next;
    ApplyExtraPalette();
    ApplyWaterPalettes();
}

// A charge shot's flash (a runtime palette effect, the art untouched): while Y has been held chargeStart frames or
// more, the extra's own colours show the charge palettes ("s3k.charge_palettes", from its sheet): charge1 every other 4
// frames until the charge is full (chargeFull), then charge2a, charge2b and its own in turn, 2 frames each. Written each
// frame it shows (after SuperGlow and KeepExtraPalette); its own colours back once it's over. Bank 0 (underwater banks
// keep its own)
static void ChargeFlash() {
    static bool shown = false;
    const ExtraData& x = Extra(g_character);
    const ShotData& s2 = x.shot2;
    int phase = -1;
    if (s2.onCharge && g_busterCharge >= s2.chargeStart) {
        if (g_busterCharge < s2.chargeFull)
            phase = (g_busterCharge >> 2) & 1 ? 0 : -1;
        else
            phase = (g_busterCharge >> 1) % 3 < 2 ? (g_busterCharge >> 1) % 3 + 1 : -1;
    }
    if (phase < 0 || (int)x.chargePalettes[phase].size() == 0) {
        if (shown)
            ApplyExtraPalette();
        shown = false;
        return;
    }
    if (!ExtraPaletteScene())
        return;
    if (shown)
        ApplyExtraPalette();  // (the colours a phase doesn't change: its own)
    for (const PaletteColour& c : x.chargePalettes[phase])
        RSDK->SetPaletteEntry(0, c.index, c.rgb);
    shown = true;
}

// The Shine Spark's glow (a runtime palette effect, the art untouched; abilities.py spark_glow_draw's): while one is
// stored or flying, the extra's greys (sparkGlowCount slots from sparkGlowFirst) move toward sparkGlowTo by sparkGlow[k]
// / 256: stored, k pulses 0 1 2 1 (4 frames each; 2 in its last second), flying 2. Bank 0; its own colours back once over
static void SparkGlow() {
    static bool shown = false;
    const ExtraAbilities& c = Extra(g_character).abilities;
    int k = -1;
    if (c.sparkSpeed > 0 && g_ab.spark > 0) {
        if (g_ab.spark > SPARK_ACTIVE)
            k = 2;
        else {
            k = (g_ab.spark > 60 ? g_ab.spark >> 2 : g_ab.spark >> 1) & 3;
            if (k == 3)
                k = 1;
        }
    }
    if (k < 0) {
        if (shown)
            ApplyExtraPalette();
        shown = false;
        return;
    }
    if (!ExtraPaletteScene())
        return;
    int a = c.sparkGlow[k];
    for (const PaletteColour& pc : Extra(g_character).palette) {
        if (pc.index < c.sparkGlowFirst || pc.index >= c.sparkGlowFirst + c.sparkGlowCount)
            continue;
        uint32 base = Glow(pc.rgb, g_glow), out = 0;
        for (int sh = 16; sh >= 0; sh -= 8) {
            int v = (base >> sh) & 0xFF, to = (c.sparkGlowTo >> sh) & 0xFF;
            out |= (uint32)(v + ((to - v) * a >> 8)) << sh;
        }
        RSDK->SetPaletteEntry(0, pc.index, out);
    }
    shown = true;
}

static void Hook_PlayerUpdate(void* arg) {
    int slot = -1;
    StateMachine* input = nullptr;
    Entity* before = CurrentEntity(&slot);
    if (before && slot == 0 && g_character > 0 && g_extraFrames
        && (Extra(g_character).noRoll || Extra(g_character).abilities.groundSlide  // (no roll; or the Slide's input;
            || Extra(g_character).abilities.sparkSpeed > 0  // or the Shine Spark's: down stores it, no control flying;
            || Extra(g_character).abilities.sink))  // or no input while he's sunk: the Shadow Sink)
        input = WrapInput((EntityPlayer*)before);
    if (before && slot == 0 && g_character > 0 && g_extraFrames)
        SurgeRestore((EntityPlayer*)before);  // the game's own animator back, before it runs (SurgeShow)
    if (before && slot == 0 && g_character > 0 && g_extraFrames)
        CopyHeadRestore((EntityPlayer*)before);  // ...and its own frame list (CopyHeadShow)
    int superBefore = -1;  // player 1's superState before the game's update (-1: not the extra)
    if (before && slot == 0 && g_character > 0 && g_extraFrames) {
        superBefore = ((EntityPlayer*)before)->superState;
        SuperPress((EntityPlayer*)before);
    }
    g_playerUpdate(arg);
    if (input && input->state == NoRollInput)  // (unless the update gave him another input: a cutscene's)
        input->state = g_realInput;
    if (input) {  // a cutscene that took his input during the update kept the wrapper as the one to give back: the game's
        // (0x1401e4250 stores stateInput at +0x378 and puts the no-input one in; 0x1401e46c0 copies it back. Stored as
        // NoRollInput, it came back as a dead pad once g_realInput was the no-input one: ICZ1's snowboard crash left
        // Ecco jumping forever on a stuck jump press, 2026-10-01)
        auto* saved = (StateMachine*)((char*)before + PLAYER_SAVED_INPUT);
        if (saved->state == NoRollInput)
            saved->state = g_realInput;
    }
    slot = -1;
    Entity* self = CurrentEntity(&slot);
    if (!self)
        return;
    if (g_playerUpdateLogs < 4) {
        g_playerUpdateLogs++;
        Log("Player update: entity %p slot %d (argument %p)", (void*)self, slot, arg);
    }
    if (slot == 0 && InterlockedExchange(&g_playerProbe, 0))
        PlayerProbe((const uint8*)self);
    if (slot == 0 && InterlockedExchange(&g_cheatRings, 0)) {  // any character, extra or not
        int32& rings = *(int32*)((uint8*)self + PLAYER_RINGS);
        if (rings < 100)
            rings = 100;
        CheatEmeralds();
    }
    if (slot == 0 && (g_character < 1 || !g_extraFrames))
        NukeFlash();  // (the Screen Nuke's flash ends even when the extra is gone: its own copy of the flash)
    if (g_character < 1 || !g_extraFrames || slot != 0)  // player 1 only: the extra always plays alone
        return;
    auto* pl = (EntityPlayer*)self;
    shots::QueueIcon();  // (monitor_swap's icon: drawn in an extra pass of his draw, shots::PlayerDraw)
    static int lastSuper = -1;
    if (pl->superState != lastSuper) {
        Log("superState %d -> %d", lastSuper, pl->superState);
        lastSuper = pl->superState;
    }
    FindBlinkTimer(pl);
    KeepExtraPalette();
    g_ySuper = superBefore == 0 && pl->superState != 0 && pl == (EntityPlayer*)before;  // Y transformed this frame
    SuperGlow(pl);
    if (g_nuke > 0)
        g_nuke--;
    if (ninja::Press(pl))  // (Joe's up + Y cast, first: the press is the cast's, no shuriken with it; Ninjutsu.h)
        g_ySuper = true;
    if (pots::Press(pl))  // (Gilius' up + Y Earthquake, first: the press is the cast's, no chop with it; PotMagic.h)
        g_ySuper = true;
    Abilities(pl);
    ninja::Update(pl);  // (the cast pose, Mijin's cost, Fushin's count: after the moves, Ninjutsu.h)
    pots::Update(pl);  // (Gilius' Earthquake: its waves, boulders and pose, after the moves; PotMagic.h)
    treasure::Update(pl);  // (Rouge's Treasure Sense: Y on the ground; after the moves, TreasureSense.h)
    if (Extra(g_character).abilities.floatLean)  // (after every move: the animation they left)
        FloatLean(pl, Extra(g_character).abilities);
    ChargeFlash();  // (after SuperGlow and the charge's count this frame)
    SparkGlow();  // (after SuperGlow and the Shine Spark's count this frame)
    NukeFlash();  // (after KeepExtraPalette and a nuke's start: its colours darkened too, from this frame)
    g_ySuper = false;
    if (Extra(g_character).roll)
        RollCurl(pl);
    if (Extra(g_character).abilities.waterWalk)  // (after every move: where they left her)
        WaterWalk(pl);
    if (Extra(g_character).abilities.noBreathing)
        NoBreathing(pl);
    if (Extra(g_character).abilities.powerSurge)  // last: what the game's update left is kept aside
        SurgeShow(pl, Extra(g_character).abilities);
    if (Extra(g_character).abilities.copyHeads > 0)  // (after every move: the animation they left)
        CopyHeadShow(pl, Extra(g_character).abilities);
    afterImage::Fade();  // (any move's afterimages fade out: Ghost.h)
}

// ---------------------------------------------------------------- save-menu picker
// S3&K's data select (S3K_SaveSlot, one entity per slot) lets up/down cycle a slot's character through
// 6 values (verified in-game): 0 Sonic & Tails, 1 Knuckles, 2 Tails, 3 Sonic, 4 Amy, 5 Amy & Tails. The
// extras are added where that cycle wraps around; while one is shown, the slot really holds 3 (Sonic
// alone: the extra plays as Sonic in costume) and its character sprite shows the extra's own art.
// Picks are remembered per save slot in NoSwapS3K.ini [Slots] and applied when that slot is played.
constexpr int SAVESLOT_CHARACTER = 0x176;  // uint8: the 6 values above
constexpr int SAVESLOT_NUMBER = 0x16D;     // uint8: save slot, 0-based (0xFF = No Save)
constexpr int SAVESLOT_ANIMATOR = 0xB0;    // Animator: the character sprite (frames 0-3 of SaveMenu.bin "Player")
constexpr int SAVEMENU_SELECTED = 0xCC;    // int32: the selected slot's entity slot
constexpr int CHARACTER_COUNT = 6, CHARACTER_SONIC = 3;
// the save slot's character while it shows an extra: its base (Sonic alone, Tails alone, Knuckles)
static int SlotCharacter(int extra) {
    static const int CHARACTER_OF_BASE[] = {CHARACTER_SONIC, 2, 1};
    return CHARACTER_OF_BASE[Extra(extra).base];
}
constexpr int SAVEMENU_PLAYER_ANIM = 4;    // SaveMenu.bin "Player": the characters' standing frames
static bool g_slotShowsExtra[0x1000];      // per entity slot: its character sprite points at an extra's art
static int g_slotPicture[0x1000];          // per entity slot: the picture it last showed (j + 1, sprite id), for the log
// Per extra: its save screen picture's number for this session + 1 (0: none; SetUpMenuPictures, with the packages).
// Several slots show at once and the engine keeps a loaded file under its name for the whole menu visit, so each
// extra gets its own name, 3K_Players/MenuPicture<j>.bin, which the file hook serves from its package; it never
// changes while the game runs, so a name the engine kept always holds the right extra.
static int g_menuPicture[KIND_LIMIT + 1];  // by kind
static GlobalVariables** const GLOBALS = (GlobalVariables**)0x144000210;  // from Ultrafix3kFixes

// This scene load is a seamless act transition's (shots::Hook_StageLoad): globals->atlEnabled, which the game's
// Zone_StoreEntities sets (0x14020080c: with atlEntityCount, just before the load) and its reload clears from a state,
// after the stage loads (0x1401fc79d); a death's or a menu's load: 0 (this build's exe, objdump, never run)
static bool ActTransitionLoad() {
    GlobalVariables* g = Readable(GLOBALS, sizeof(void*)) ? *GLOBALS : nullptr;
    return g && Readable(g, offsetof(GlobalVariables, atlEntityCount)) && g->atlEnabled != 0;
}

// The save block in use: 256 ints per save slot in saveRAM, or noSaveSlot when not saving (the level select), as in
// Mania's SaveGame_GetSaveRAM. The Chaos Emeralds are int 52 of it, one bit each (found with the F6 probe: the
// sound test's emerald code set noSaveSlot[52] from 0 to 0x7F)
constexpr int SAVE_EMERALDS = 52;
static void CheatEmeralds() {
    GlobalVariables* g = Readable(GLOBALS, sizeof(void*)) ? *GLOBALS : nullptr;
    if (!g || !Readable(g, sizeof(GlobalVariables))) {
        Log("F7: 100 rings (globals not readable: no emeralds)");
        return;
    }
    int slot = g->saveSlotID;
    int* block = slot >= 0 && slot < 8 ? &g->saveRAM[0x100 * slot] : g->noSaveSlot;
    block[SAVE_EMERALDS] |= 0x7F;
    Log("F7: 100 rings, emeralds %#x (save slot %d)", block[SAVE_EMERALDS], slot);
}

static int g_slotExtra[256];      // per save slot number: the extra shown there (0 none), this menu visit
static bool g_slotLoaded[256];    // g_slotExtra[n] read from the ini yet
static int g_menuSelectedEntity = -1;
static bool g_launching = false;  // the level select is being started from the save menu
static int g_menuPick = -1;       // the extra of the slot selected when the menu was left (-1: not from the menu)

static std::string IniPath() {
    return DllFolder() + "\\NoSwapS3K.ini";
}

static int SlotKey(int number) {
    return number == 0xFF ? -1 : number;  // -1 = No Save
}

// A character named in the ini ([Slots], [Debug] Character): its package key, or a number from an older ini, an
// extra number 1-21 as numbered before the registry (the legacy order, Roster.h). The kind it's offered under (0: none,
// not installed, or unknown)
static int KindFromSetting(const char* value) {
    if (!value || !*value)
        return 0;
    if (value[0] >= '0' && value[0] <= '9') {
        int n = atoi(value);
        return n >= 1 && n <= LEGACY_COUNT && Offered(FIRST_EXTRA_KIND - 1 + n) ? FIRST_EXTRA_KIND - 1 + n : 0;
    }
    int kind = KindOfKey(value);
    return kind > 0 ? kind : 0;
}

// [Slots] holds each save slot's extra by its permanent name (its package key; empty = none). An older ini's numbers
// are the legacy extra numbers; a name not installed reads as none, and stays in the ini till that slot's pick changes.
static int SavedExtra(int number) {
    char key[16], value[256] = {};
    snprintf(key, sizeof(key), "%d", SlotKey(number));
    GetPrivateProfileStringA("Slots", key, "", value, sizeof(value), IniPath().c_str());
    return KindFromSetting(value);
}

static void SaveExtra(int number, int extra) {
    char key[16];
    snprintf(key, sizeof(key), "%d", SlotKey(number));
    const char* name = KindKey(extra);
    WritePrivateProfileStringA("Slots", key, name ? name : "", IniPath().c_str());
}

// The save screen's cycle through the offered extras, in kind order: the one after / before `kind` (0: past the end)
static int NextExtra(int kind, int dir) {
    if (g_roster.empty())
        return 0;
    if (kind == 0)
        return dir > 0 ? g_roster.front().kind : g_roster.back().kind;
    for (size_t i = 0; i < g_roster.size(); i++)
        if (g_roster[i].kind == kind) {
            long j = (long)i + dir;
            return j >= 0 && j < (long)g_roster.size() ? g_roster[j].kind : 0;
        }
    return 0;
}

// The extra for the stage now starting: the slot picked in the menu, else the saved pick for the save
// slot being played (saveSlotID), else -1
static int PickedCharacter() {
    if (g_menuPick >= 0)
        return g_menuPick;
    GlobalVariables* g = Readable(GLOBALS, sizeof(void*)) ? *GLOBALS : nullptr;
    if (g && Readable(&g->saveSlotID, sizeof(int))) {
        static int logged = -2;
        if (g->saveSlotID != logged) {
            logged = g->saveSlotID;
            Log("globals saveSlotID %d", g->saveSlotID);
        }
    }
    return -1;
}

typedef void (*UpdateFn2)(void* self);
static UpdateFn2 g_saveSlotUpdate = nullptr, g_saveMenuUpdate = nullptr;

static void Hook_SaveMenuUpdate(void* arg) {
    g_launching = false;
    g_saveMenuUpdate(arg);
    int slot = -1;
    auto* self = (uint8*)CurrentEntity(&slot);
    if (self)
        g_menuSelectedEntity = *(int32*)(self + SAVEMENU_SELECTED);
}

static void Hook_SaveSlotUpdate(void* arg) {
    int slot = -1;
    auto* self = (uint8*)CurrentEntity(&slot);
    uint8 before = self ? self[SAVESLOT_CHARACTER] : 0;
    g_saveSlotUpdate(arg);
    if (!self)
        return;
    int number = self[SAVESLOT_NUMBER];
    if (!g_slotLoaded[number]) {
        g_slotLoaded[number] = true;
        g_slotExtra[number] = SavedExtra(number);
        if (g_slotExtra[number])
            self[SAVESLOT_CHARACTER] = SlotCharacter(g_slotExtra[number]);
    }
    uint8 after = self[SAVESLOT_CHARACTER];
    int& extra = g_slotExtra[number];
    if (after != before) {
        // The game's own list isn't always the same length (Classic mode has no Amy): a step of one is a
        // move, anything bigger is the list wrapping around, which is where the extras go
        int step = (int)after - (int)before;
        bool forward = step == 1 || step < -1;
        bool backward = step == -1 || step > 1;
        bool wrapped = step < -1 || step > 1;
        static uint8 lastCharacter[256];  // per slot: the last character of the game's list, learned from a wrap
        if (extra == 0) {
            if (forward && wrapped) {
                lastCharacter[number] = before;
                extra = NextExtra(0, 1);  // past the last character: the first extra (none offered: stays 0)
            } else if (backward && wrapped) {
                lastCharacter[number] = after;
                extra = NextExtra(0, -1);  // before the first character: the last extra
            }
            if (extra)
                self[SAVESLOT_CHARACTER] = SlotCharacter(extra);
        } else {
            int dir = forward ? 1 : backward ? -1 : 0;
            int next = dir ? NextExtra(extra, dir) : extra;
            if (next == 0 && dir > 0) {
                extra = 0;
                self[SAVESLOT_CHARACTER] = 0;
            } else if (next == 0) {
                extra = 0;
                self[SAVESLOT_CHARACTER] = lastCharacter[number] ? lastCharacter[number] : CHARACTER_COUNT - 1;
            } else {
                extra = next;
                self[SAVESLOT_CHARACTER] = SlotCharacter(extra);
            }
        }
        SaveExtra(number, extra);
        Log("save slot %d: character %d, extra kind %d (%s)", SlotKey(number), self[SAVESLOT_CHARACTER], extra,
            extra ? KindKey(extra) : "none");
    }
    if (slot == g_menuSelectedEntity)
        g_menuPick = extra;
    // Y on a slot showing an extra: S3&K's level select as that extra (pick Sonic there; handy for
    // testing, like the other games' up-on-the-save-screen)
    // Y: Select never reaches the game in Origins, and B is the menu's back (a button test, 2026-09-25)
    bool select = false;
    for (int c = 0; g_controllers && c <= 4; c++)  // (0 isn't always "any controller" here)
        select |= g_controllers[c].keyY.press != 0;
    if (slot == g_menuSelectedEntity && extra && !g_launching && select) {
        g_launching = true;
        Log("level select as extra kind %d (%s)", extra, KindKey(extra));
        // the level select starts on the current player choice: the extra's base alone (not Sonic &
        // Tails, so no Tails follows the extra around)
        GlobalVariables* g = Readable(GLOBALS, sizeof(void*)) ? *GLOBALS : nullptr;
        static const CharacterIDs PLAYER_OF_BASE[] = {ID_SONIC, ID_TAILS, ID_KNUCKLES};  // the extra's base, alone
        if (g && Readable(&g->playerID, sizeof(g->playerID)))
            g->playerID = PLAYER_OF_BASE[Extra(extra).base];
        RSDK->SetScene("Presentation & Menus", "Level Select");
        RSDK->LoadScene();
    }
    // The game only ever changes the frame number of the slot's character sprite, never its file: point
    // it at the extra's art while an extra shows, and back at the menu's own art afterwards
    auto* animator = (Animator*)(self + SAVESLOT_ANIMATOR);
    int picture = Offered(extra) ? g_menuPicture[extra] : 0;  // (none: the menu's own art)
    if (picture) {
        char file[64];
        // a menu-only copy of the extra's standing frame in the menu's own colours (build_s3k_art.py, in its
        // package): the menu uses the palette slots extras' own colours live in during play
        snprintf(file, sizeof(file), "3K_Players/MenuPicture%d.bin", picture - 1);
        uint16 frames = g_loadSpriteAnimation(file, 2);  // (the real loader: no swapping for these)
        RSDK->SetSpriteAnimation(frames, 0, animator, true, 0);
        g_slotShowsExtra[slot & 0xFFF] = true;
        if (g_slotPicture[slot & 0xFFF] != (picture << 16 | frames)) {  // (logged again when it's loaded anew)
            g_slotPicture[slot & 0xFFF] = picture << 16 | frames;
            Log("save slot %d shows extra kind %d (%s): %s, sprite %u", SlotKey(number), extra, KindKey(extra), file,
                (unsigned)frames);
        }
    } else if (g_slotShowsExtra[slot & 0xFFF]) {
        g_slotShowsExtra[slot & 0xFFF] = false;
        g_slotPicture[slot & 0xFFF] = 0;
        int frame = animator->frameID;
        uint16 menu = g_loadSpriteAnimation("3K_Menu/SaveMenu.bin", 2);
        RSDK->SetSpriteAnimation(menu, SAVEMENU_PLAYER_ANIM, animator, true, frame);
    }
}

typedef void (*RegisterObjectFn)(void** staticVars, const char* name, uint32 entityClassSize, uint32 staticClassSize,
                                 void (*update)(void), void (*lateUpdate)(void), void (*staticUpdate)(void),
                                 void (*draw)(void), void (*create)(void*), void (*stageLoad)(void),
                                 void (*editorDraw)(void), void (*editorLoad)(void), void (*serialize)(void),
                                 void (*staticLoad)(void*));
static RegisterObjectFn g_registerObject = nullptr;

// Ice Cap's snowboard intro (S3K_ICZ1Intro) runs as it is: a Sonic-based extra rides it with his own poses on the
// official board (3K_ICZ/Snowboard.bin swapped, see SWAPS). Skipping it the Tails-alone way didn't take in game and
// risked side effects (the user, 2026-10-01).

// Knuckles-only barriers: an extra whose package says so ("breaksWalls": abilities.py breaks_walls; Heavy, Vector,
// Omega) is shown Knuckles' character ID while such an object updates, the same way, so it breaks for him as it does
// for Knuckles walking into it; the real ID is put back straight after. Player 1 only; the story (globals->playerID)
// is never touched. From this build's exe (objdump, never run): each one's check reads the touching player's
// characterID (+0x1A8) against 4 inside the update it registers (the class table's +0x10, a thunk to the body):
//   BreakableWall  its onlyKnux walls (every zone: its state functions, run by its update's state machine)
//   AIZRockPile    Angel Island 2's rock piles: onlyKnux at 0x14026d9ae, in the update body 0x14026d910 itself
//   RockPile       Lava Reef's: 0x140161c3c, in a state (0x140161b40) its update 0x140161fa0 runs
//   IceColumn      Ice Cap 1's ice columns (knuxOnly): 0x1402243fe, in 0x1402241d0, called by its update 0x140225900
// The three new ones are wrapped only when their update is that thunk and the check's bytes are there (KnuxWrap).
static UpdateFn g_breakableWallUpdate = nullptr, g_aizRockPileUpdate = nullptr, g_rockPileUpdate = nullptr,
                g_iceColumnUpdate = nullptr;
template <typename Call>
static void AsKnuckles(Call call) {
    EntityPlayer* p = g_character > 0 && RSDK && (Extra(g_character).abilities.breaksWalls || swim::Ramming() || nights::Drilling()
                                                   || shots::stomp::Breaks((EntityPlayer*)RSDK->GetEntity(0)))
                          ? (EntityPlayer*)RSDK->GetEntity(0) : nullptr;  // (Ecco's charge ram breaks them too: EccoSwim.h; NiGHTS' Drill Dash: NightsFlight.h; no_stomp's Slide and roll: stomp::Breaks)
    int32 id = p ? p->characterID : 0;
    if (p && id == ID_SONIC)
        p->characterID = ID_KNUCKLES;
    call();
    if (p && id == ID_SONIC && p->characterID == ID_KNUCKLES)
        p->characterID = id;
}
static void Hook_BreakableWallUpdate(void* arg) { AsKnuckles([&] { g_breakableWallUpdate(arg); }); }
static void Hook_AizRockPileUpdate(void* arg) { AsKnuckles([&] { g_aizRockPileUpdate(arg); }); }
static void Hook_RockPileUpdate(void* arg) { AsKnuckles([&] { g_rockPileUpdate(arg); }); }
static void Hook_IceColumnUpdate(void* arg) { AsKnuckles([&] { g_iceColumnUpdate(arg); }); }
#include "SpinStandIn.h"  // (Spin Dash-only gimmicks for extras without one: dash wheels, Spin Dash lifts)
struct KnuxWrap {
    const char* name;
    uintptr_t thunk;     // its registered update (mov rcx, [sceneInfo]; mov rcx, [rcx]; jmp body)
    uintptr_t check;     // the characterID read in there
    uint8 bytes[8];
    size_t n;
    UpdateFn* original;
    void (*hook)(void*);
};
static const KnuxWrap KNUX_WRAPS[] = {
    {"AIZRockPile", 0x14026cd20, 0x14026d9ae, {0x41, 0x8b, 0x86, 0xa8, 0x01, 0x00, 0x00}, 7, &g_aizRockPileUpdate,
     Hook_AizRockPileUpdate},  // mov eax, [r14+0x1a8]
    {"RockPile", 0x140160bc0, 0x140161c3c, {0x41, 0x8b, 0x81, 0xa8, 0x01, 0x00, 0x00}, 7, &g_rockPileUpdate,
     Hook_RockPileUpdate},  // mov eax, [r9+0x1a8]
    {"IceColumn", 0x140223f40, 0x1402243fe, {0x83, 0xbb, 0xa8, 0x01, 0x00, 0x00, 0x04}, 7, &g_iceColumnUpdate,
     Hook_IceColumnUpdate},  // cmp dword [rbx+0x1a8], 4
};

// Heavy's Juggernaut (abilities.py charge; S1/S2 noswap_common.juggernaut, CD build_soniccd.cd_juggernaut): while his
// charge is past his top speed (the fist's flash, or coasting that fast), enemies can't hurt him; hazards still do.
// From this build's exe (objdump, never run), S3&K hurts a player through these, each "player, entity" (the one that
// hurts), checking the invincibility and blink timers itself, then the hurt body (0x1401e3360):
//   Player_Hurt           0x1401de910  119 calls: badniks, bosses and hazards alike (Platform's spikes, SpikeFlail...)
//   Player_ProjectileHurt 0x1401de0f0  11: badniks' shots (Tulippon, Togemane, Ponpon, Pointer...), its shield deflection
//   Player_LightningHurt  0x1401dd040  7: bosses (BarrierEggman, RedEye...) and hazards (Laser, Lightning)
//   Player_FireHurt       0x1401dd960  (hooked for fire immunity: Hook_FireHurt asks here too)
// So the hurt is refused only when the entity's class is an enemy's: one this stage has seen checking a player through
// Player_CheckBadnikTouch / _CheckBadnikBreak / _CheckBossHit (the shots' hooks, jugg::Note: badniks and bosses do,
// Spikes and most hazards don't), and not a named hazard (JUGG_HAZARDS, in case one uses those checks). A badnik's own
// spiky part (a class seen breaking through Player_CheckBadnikBreak, not a boss) breaks as if he'd hit it (the game's
// own Player_CheckBadnikBreak: his charge shows the jump, an attack); a shot or a boss's part is just harmless.
// Bosses take his hits anyway (Player_CheckBossHit: an attack). Each function's first bytes are checked first.
namespace jugg {
constexpr uintptr_t PLAYER_HURT = 0x1401de910, PROJECTILE_HURT = 0x1401de0f0, LIGHTNING_HURT = 0x1401dd040;
static const uint8 PLAYER_HURT_BYTES[] = {0x48, 0x83, 0xec, 0x28, 0x48, 0x8b, 0x81, 0xf0, 0x00, 0x00, 0x00, 0x4c, 0x8b,
                                          0xc1};
static const uint8 PROJECTILE_HURT_BYTES[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10, 0x48, 0x89,
                                              0x74, 0x24, 0x18, 0x57};
static const uint8 LIGHTNING_HURT_BYTES[] = {0x48, 0x83, 0xec, 0x28, 0x80, 0xb9, 0xe8, 0x00, 0x00, 0x00, 0x04, 0x4c,
                                             0x8b, 0xc1, 0x74, 0x6d};
constexpr int PLAYER_TOP_SPEED = 0x220;  // (Charge's "top")
// Hazards that might check a player the badniks' way: never spared
static const char* const JUGG_HAZARDS[] = {
    "Spikes", "SpikeFlail", "SpikeColumn", "SpikeCrusher", "OrbitingSpikeball", "SpikeballLauncher",
    "HangConveyorSpikeball", "MagSpikeBall", "Stalactite", "IceHazard", "Mine", "BreakableIce", "Laser", "ScanLaser",
    "Lightning", "Poison", "Platform", "LowerPlatform", "MagPlatform", "Turbine", "FrostBlower", "BuckwildBall",
    "Propeller", "SpinCupSwing", "BobbingLog", "BallShooter", "FireballLauncher", "Flamethrower", "LBZFlamethrower",
    "LavaFall", "FlameSpring", "BurningLog", "RisingLava", "InvisibleBlock", "Explosion", "S3K_AIZBombing", "Debris",
    "ItemBox", "CompItem", "ConvItem", "CircleBumper", "WallBumper", "Gachapon", "Halogen", "Cyclone", "DoorTrigger",
    "Crane", "Conveyor"};
typedef bool32 (*HurtFn)(EntityPlayer* player, Entity* entity);
static HurtFn g_playerHurt = nullptr, g_projectileHurt = nullptr, g_lightningHurt = nullptr;

// Player 1 as Heavy with his charge past his top speed, still in the state it started in, on the ground; or his
// Shine Spark flying (anywhere)
static bool Juggernaut(EntityPlayer* p) {
    if (p && g_character > 0 && RSDK && g_ab.spark > SPARK_ACTIVE && RSDK->GetEntitySlot(p) == 0 && !Hurt(p))
        return true;  // (his Shine Spark, flying: Spark)
    if (!p || g_character <= 0 || !RSDK || !Extra(g_character).abilities.charge || g_ab.charge == 0 || !p->onGround
        || RSDK->GetEntitySlot(p) != 0 || (void*)p->state.state != g_ab.chargeState || Hurt(p))
        return false;
    return std::abs(g_ab.charge) > *(int*)((char*)p + PLAYER_TOP_SPEED);
}

static bool Enemy(Entity* e) {
    if (!e || !Readable(e, sizeof(Entity)) || e->classID >= 1024)
        return false;
    uint8& k = g_class[e->classID];
    if (!(k & (JUGG_TOUCH | JUGG_BADNIK | JUGG_BOSS)))
        return false;
    if (!(k & JUGG_NAMED)) {  // (its name, once a stage)
        k |= JUGG_NAMED;
        const char* name = shots::ClassName(e->classID);
        for (const char* h : JUGG_HAZARDS)
            if (strcmp(name, h) == 0)
                k |= JUGG_HAZARD;
    }
    return !(k & JUGG_HAZARD);
}

// true: the hurt is refused (and a badnik's spiky part broken, when `breaks`)
static bool Spares(EntityPlayer* p, Entity* e, const char* via, bool breaks) {
    if (!Juggernaut(p) || !Enemy(e))
        return false;
    uint8 k = g_class[e->classID];
    bool broke = false;
    if (breaks && (k & JUGG_BADNIK) && !(k & JUGG_BOSS) && shots::g_break)
        broke = shots::g_break(p, e, true);
    static int logs = 0;
    if (logs++ < 60)
        Log("juggernaut: %s from %s (slot %d) refused%s", via, shots::ClassName(e->classID), RSDK->GetEntitySlot(e),
            broke ? ": it broke" : "");
    return true;
}

static bool32 Hook_PlayerHurt(EntityPlayer* p, Entity* e) {  // (Psychokinesis caught something that hurts instead: refused)
    return psycho::Refuses(p, e) || shots::ReachHurt(p, e, "Player_Hurt") || Spares(p, e, "Player_Hurt", true)
               ? false
               : g_playerHurt(p, e);
}
static bool32 Hook_ProjectileHurt(EntityPlayer* p, Entity* e) {
    return psycho::Refuses(p, e) || shots::ReachHurt(p, e, "Player_ProjectileHurt")
                   || Spares(p, e, "Player_ProjectileHurt", false)
               ? false
               : g_projectileHurt(p, e);
}
static bool32 Hook_LightningHurt(EntityPlayer* p, Entity* e) {
    return psycho::Refuses(p, e) || shots::ReachHurt(p, e, "Player_LightningHurt")
                   || Spares(p, e, "Player_LightningHurt", false)
               ? false
               : g_lightningHurt(p, e);
}

static void SetUp() {
    if (!shots::g_on) {
        Log("juggernaut: off (it needs the shots' hooks: Heavy's full charge is hurt by enemies as before)");
        return;
    }
    struct { const char* name; uintptr_t at; const uint8* bytes; size_t n; void* hook; void** original; } HOOKS[] = {
        {"Player_Hurt", PLAYER_HURT, PLAYER_HURT_BYTES, sizeof(PLAYER_HURT_BYTES), (void*)Hook_PlayerHurt,
         (void**)&g_playerHurt},
        {"Player_ProjectileHurt", PROJECTILE_HURT, PROJECTILE_HURT_BYTES, sizeof(PROJECTILE_HURT_BYTES),
         (void*)Hook_ProjectileHurt, (void**)&g_projectileHurt},
        {"Player_LightningHurt", LIGHTNING_HURT, LIGHTNING_HURT_BYTES, sizeof(LIGHTNING_HURT_BYTES),
         (void*)Hook_LightningHurt, (void**)&g_lightningHurt}};
    for (auto& h : HOOKS) {
        bool ok = Readable((void*)h.at, h.n) && memcmp((void*)h.at, h.bytes, h.n) == 0;
        if (ok && MH_CreateHook((void*)h.at, h.hook, h.original) == MH_OK && MH_EnableHook((void*)h.at) == MH_OK)
            Log("juggernaut: %s hooked", h.name);
        else
            Log("juggernaut: %s at %p %s: not hooked (it hurts Heavy as before)", h.name, (void*)h.at,
                ok ? "couldn't be hooked" : "is DIFFERENT (another game build?)");
    }
}
}  // namespace jugg

// Fire immunity (abilities.py fire_immune: Blaze): the fire shield's immunity, all the time, and nothing else of it.
// S3&K asks about fire in two ways (this build's exe, read with objdump, never run):
// - Player_FireHurt (0x1401dd960, Mania's Player_ElementHurt with the fire shield folded in: "shield byte +0xE8 != 3,
//   then Player_Hurt"), called by FlameSpring, Flamethrower, LavaFall, BurningLog, FireballLauncher, FinalFireball,
//   LBZFlamethrower, FireBreath, FlameMobile, HeyHo, S3K_AIZBombing, DrillMobile, BeamRocket, JetMobile and Explosion.
//   It's hooked: for the fire-immune extra it hurts nobody (returns false, as with the shield).
// - The same test written out in RisingLava's static update (Lava Reef's rising lava), S3K_LRZSetup's static update
//   (Lava Reef's lava floor tiles), Conveyor's update (its hurting kind) and InvisibleBlock's update (its Flame kind:
//   most of Lava Reef's lava, see Hook_InvisibleBlockUpdate). Those run with player 1's shield byte
//   reading 3 (the fire shield: the lava is solid underfoot, as with the shield), put back straight after. Nothing else in
//   those three reads the shield. Other shield tests (fire-dash rock breaking, badniks' projectile deflection) are left
//   alone: they aren't hazards.
constexpr int PLAYER_SHIELD = 0xE8;  // uint8: 0 none, 1 blue, 2 bubble, 3 fire, 4 lightning (the Water object's tests)
static_assert(SHIELD_FIRE == 3, "the fire shield's number");  // (the reference header's ShieldTypes)
constexpr uintptr_t FIRE_HURT = 0x1401dd960;
static const uint8 FIRE_HURT_BYTES[] = {0x48, 0x83, 0xec, 0x28, 0x80, 0xb9, 0xe8, 0x00, 0x00, 0x00, 0x03, 0x4c, 0x8b, 0xc1,
                                        0x74, 0x6d};
typedef bool32 (*FireHurtFn)(EntityPlayer* player, Entity* entity);
static FireHurtFn g_fireHurt = nullptr;

static EntityPlayer* FireImmunePlayer() {
    return g_character > 0 && RSDK && Extra(g_character).abilities.fireImmune ? (EntityPlayer*)RSDK->GetEntity(0) : nullptr;
}

// The log: at most one line a second per source (and 100 in all per source), so a test shows it working
struct FireLog {
    ULONGLONG last = 0;
    int count = 0;
    bool Due() {
        ULONGLONG now = GetTickCount64();
        if (count >= 100 || (last && now - last < 1000))
            return false;
        last = now;
        count++;
        return true;
    }
};

static bool32 Hook_FireHurt(EntityPlayer* player, Entity* entity) {
    if (jugg::Spares(player, entity, "Player_FireHurt", false))  // (Heavy's full charge: a boss's or badnik's fire)
        return false;
    if (shots::ReachHurt(player, entity, "Player_FireHurt"))  // (a shot touched its fire, not him: shots::g_reach)
        return false;
    if (player && player == FireImmunePlayer()) {
        static FireLog log;
        if (log.Due()) {
            int slot = 0;
            Entity* self = CurrentEntity(&slot);
            Log("fire immunity: prevented fire damage (Player_FireHurt from %s)",
                self ? shots::ClassName(self->classID) : "?");
        }
        return false;
    }
    return g_fireHurt(player, entity);
}

template <typename Call>
static void AsFireShield(Call call) {
    EntityPlayer* p = FireImmunePlayer();
    uint8* shield = p ? (uint8*)p + PLAYER_SHIELD : nullptr;
    uint8 real = shield ? *shield : 0;
    if (shield)
        *shield = SHIELD_FIRE;
    call();
    if (shield && *shield == SHIELD_FIRE)
        *shield = real;
}
// The whole-stage lava (their lava tests are inline): a line now and then while the extra is in such a stage, so the
// log shows the wrapper live (these can't tell us whether she was actually on the lava)
static void LavaLog(FireLog& log, const char* what) {
    if (FireImmunePlayer() && log.Due() && log.count % 30 == 1)
        Log("fire immunity: %s runs with player 1 reading the fire shield (its lava can't hurt her)", what);
}
typedef void (*StaticUpdateFn)(void);
static StaticUpdateFn g_risingLavaStatic = nullptr, g_lrzSetupStatic = nullptr;
static UpdateFn g_conveyorUpdate = nullptr;
static void Hook_RisingLavaStatic() {
    static FireLog log;
    LavaLog(log, "RisingLava (static update)");
    AsFireShield([] { g_risingLavaStatic(); });
}
static void Hook_LrzSetupStatic() {
    static FireLog log;
    LavaLog(log, "S3K_LRZSetup (static update: the lava floor tiles)");
    AsFireShield([] { g_lrzSetupStatic(); });
}
static void Hook_ConveyorUpdate(void* arg) { AsFireShield([&] { g_conveyorUpdate(arg); }); }

// InvisibleBlock (the exe's 0x1401d13f0, its update): solid, and with hurtType 1-4 it hurts whoever touches it
// (Player_Hurt 0x1401e36a0, not Player_FireHurt) unless the shield byte matches: 2 bubble, 3 fire (hurtType 3 "Flame"),
// 4 lightning. Lava Reef 1 and 2 are floored with Flame blocks (3K_LRZ1: 23, 3K_LRZ2 and M3K_LRZ2: 4; read from the
// scene files), which is why the lava still hurt. A Flame block's update runs with player 1 reading the fire shield,
// as the others above (solid underfoot, no hurt); other kinds (the Death Egg's Thunder, spikes' Kill) are left alone.
constexpr int INVISIBLEBLOCK_HURT_TYPE = 0x80;   // uint8 (movzx [rdi+0x80], switch 1..5)
constexpr int INVISIBLEBLOCK_HITBOX = 0x78;      // Hitbox (its Player_CheckCollisionBox argument)
constexpr uint8 HURT_FLAME = 3;
constexpr int PLAYER_INVINCIBLE_TIMER = 0x1C4, PLAYER_BLINK_TIMER = 0x1CC;
static UpdateFn g_invisibleBlockUpdate = nullptr;
// Only this build's code: its update thunk (entity = sceneInfo->entity, jump to 0x1401d13f0), and in there the reads
// this relies on (hurtType +0x80, the Flame kind's fire shield test, the hitbox +0x78)
static bool InvisibleBlockMatches(void* update) {
    static const uint8 THUNK[] = {0x48, 0x8b, 0x0d, 0xd1, 0xf3, 0xc9, 0x02, 0x48, 0x8b, 0x09, 0xe9, 0x31, 0x06, 0x00, 0x00};
    static const uint8 HURT_TYPE[] = {0x0f, 0xb6, 0x8f, 0x80, 0x00, 0x00, 0x00};  // movzx ecx, byte [rdi+0x80]
    static const uint8 FLAME[] = {0x80, 0xbb, 0xe8, 0x00, 0x00, 0x00, 0x03};      // cmp byte [rbx+0xe8], 3
    static const uint8 HITBOX[] = {0x4c, 0x8d, 0x47, 0x78};                        // lea r8, [rdi+0x78]
    struct { uintptr_t at; const uint8* bytes; size_t n; } checks[] = {
        {0x1401d0db0, THUNK, sizeof(THUNK)}, {0x1401d1666, HURT_TYPE, sizeof(HURT_TYPE)},
        {0x1401d1697, FLAME, sizeof(FLAME)}, {0x1401d1506, HITBOX, sizeof(HITBOX)}};
    if ((uintptr_t)update != 0x1401d0db0)
        return false;
    for (auto& c : checks)
        if (!Readable((void*)c.at, c.n) || memcmp((void*)c.at, c.bytes, c.n) != 0)
            return false;
    return true;
}
static void Hook_InvisibleBlockUpdate(void* arg) {
    int slot = 0;
    Entity* e = FireImmunePlayer() ? CurrentEntity(&slot) : nullptr;
    if (!e || !Readable((uint8*)e + INVISIBLEBLOCK_HURT_TYPE, 1)
        || *((uint8*)e + INVISIBLEBLOCK_HURT_TYPE) != HURT_FLAME) {
        g_invisibleBlockUpdate(arg);
        return;
    }
    // For the log: is player 1 touching it (its box against a rough player box, a pixel apart), and could she be hurt?
    EntityPlayer* p = FireImmunePlayer();
    const Hitbox* hb = (const Hitbox*)((uint8*)e + INVISIBLEBLOCK_HITBOX);
    int32 bx = e->position.x >> 16, by = e->position.y >> 16, px = p->position.x >> 16, py = p->position.y >> 16;
    bool touching = px + 10 >= bx + hb->left - 1 && px - 10 <= bx + hb->right + 1 && py + 20 >= by + hb->top - 1
                    && py - 20 <= by + hb->bottom + 1;
    bool hurtable = *(int32*)((uint8*)p + PLAYER_INVINCIBLE_TIMER) == 0 && *(int32*)((uint8*)p + PLAYER_BLINK_TIMER) == 0
                    && *((uint8*)p + PLAYER_SHIELD) != SHIELD_FIRE;
    AsFireShield([&] { g_invisibleBlockUpdate(arg); });
    static FireLog log;
    if (touching && hurtable && log.Due())
        Log("fire immunity: prevented lava damage (InvisibleBlock slot %d, hurtType Flame, at %d,%d)", slot, bx, by);
}

static void SetUpFireImmunity() {
    bool ok = Readable((void*)FIRE_HURT, sizeof(FIRE_HURT_BYTES))
              && memcmp((void*)FIRE_HURT, FIRE_HURT_BYTES, sizeof(FIRE_HURT_BYTES)) == 0;
    if (ok && MH_CreateHook((void*)FIRE_HURT, (void*)Hook_FireHurt, (void**)&g_fireHurt) == MH_OK
        && MH_EnableHook((void*)FIRE_HURT) == MH_OK)
        Log("fire immunity: Player_FireHurt hooked");
    else
        Log("fire immunity: Player_FireHurt at %p %s: not hooked (fire hazards hurt everyone)", (void*)FIRE_HURT,
            ok ? "couldn't be hooked" : "is DIFFERENT (another game build?)");
}

// The Blue Spheres runner's draw: its colours again, just before it's drawn (the engine draws straight into
// the frame with the palette as it is then), in case anything rewrote them since the stage loaded
typedef void (*DrawFn)(void);
static DrawFn g_ssPlayerDraw = nullptr;
static void Hook_SSPlayerDraw() {
    if (g_specialExtra > 0)
        ApplySpecialPalette();
    g_ssPlayerDraw();
}

// ---------------------------------------------------------------- act results accent (tools/ui_accent.py)
// S3&K's act results (ActClear, "SONIC GOT THROUGH ACT 1") draw the name in the results font, whose body is bank 0
// slots 2, 3, 4 (Sonic's blues: light, main, dark; Tails' oranges 8-9 outline it), and a streak beside BONUS and
// TOTAL. From the exe: ActClear's draw (thunk 0x1401bb3f0, body 0x1401bbaa0) picks the streaks by the character ID
// (+0x1A8) of its player (ActClear +0xC8), in three places: HUD.bin "HUD Elements" 8 / 9 (Sonic, in slots 2-4),
// 21 / 24 (Tails: 8, 9, 11), 22 / 25 (Knuckles: 18-20), 23 / 26 (Amy: 75-77). No palette changes: each character's
// frames are drawn in its own slots (Player_StageLoad's table at 0x140b939a0), and KNUCKLES' name has its own reds.
// An extra's name (HUD_Extra.bin) uses slots 2-4 as well, so it showed Sonic's blue. While ActClear draws, the
// extra's package "ui_accent" (three shades, light to dark) goes in slots 2-4 (bank 0; bank 1, the water version,
// through the same tint), and a Tails- or Knuckles-based extra is shown Sonic's ID (the same way) so its streaks
// are Sonic's frames in those slots too. All is put back straight after the draw: the engine draws into the frame
// with the palette as it is then (Player_Draw's own save / set / restore of slots 0-31 relies on that).
// Off when the draw isn't this build's (the thunk and the three reads are checked), and for extras without an accent.
// Not the special stage results (SpecialClear): its font's slots (130-132) are also the blue emerald's.
static bool ReadWholeFile(const std::wstring& path, std::string& text);  // (below)
namespace accent {
constexpr uintptr_t DRAW_THUNK = 0x1401bb3f0, PLAYER_LOAD = 0x1401bbb2a;
constexpr uintptr_t ID_READS[] = {0x1401bbdbf, 0x1401bbf75, 0x1401bc2fd};
constexpr int PLAYER_FIELD = 0xC8;  // ActClear's player pointer
constexpr int SLOT = 2, SHADES = 3;  // slots 2-4
static_assert(offsetof(EntityPlayer, characterID) == 0x1A8, "the character ID ActClear's draw reads");

static DrawFn g_draw = nullptr;

struct Shades {
    bool read = false;
    bool ok = false;
    uint32 rgb[SHADES] = {};
};
static Shades g_shades[KIND_LIMIT + 1];

// The kind's "ui_accent" from its package's noswap_character.json, read once (ok false: none, or unusable)
static const Shades& Of(int kind) {
    Shades& s = g_shades[kind & KIND_LIMIT];
    if (s.read)
        return s;
    s.read = true;
    const RosterEntry* e = RosterOf(kind);
    std::string text, error;
    Json root;
    if (!e || !ReadWholeFile(e->root + L"noswap_character.json", text) || !JsonParser::Parse(text, root, error)) {
        Log("results accent: kind %d: its noswap_character.json unreadable (%s): Sonic's blue", kind, error.c_str());
        return s;
    }
    const Json* a = root.Get("ui_accent");
    if (!a || a->type != Json::Array || a->items.size() != SHADES) {
        Log("results accent: kind %d (%s): no ui_accent of %d shades: Sonic's blue", kind, KindKey(kind), SHADES);
        return s;
    }
    for (int i = 0; i < SHADES; i++) {
        long long c = 0;
        if (!JsonInt(&a->items[i], c) || c < 0 || c > 0xFFFFFF) {
            Log("results accent: kind %d (%s): ui_accent[%d] isn't a colour: Sonic's blue", kind, KindKey(kind), i);
            return s;
        }
        s.rgb[i] = (uint32)c;
    }
    s.ok = true;
    Log("results accent: kind %d (%s): %06X %06X %06X", kind, KindKey(kind), s.rgb[0], s.rgb[1], s.rgb[2]);
    return s;
}

// A colour through bank 1's water tint of bank 0 (a per-channel line fitted over the player slots 2-20, as
// ApplyWaterPalettes does); the colour itself when bank 1 isn't a tinted bank 0 there
static uint32 Water(uint32 c) {
    double sx[3] = {}, sy[3] = {}, sxx[3] = {}, sxy[3] = {};
    int n = 0, differ = 0;
    for (int i = 2; i <= 20; i++) {
        uint32 c0 = (uint32)RSDK->GetPaletteEntry(0, i) & 0xFFFFFF, c1 = (uint32)RSDK->GetPaletteEntry(1, i) & 0xFFFFFF;
        if (!c0 && !c1)
            continue;
        differ += c0 != c1;
        for (int ch = 0; ch < 3; ch++) {
            double x = (c0 >> (16 - 8 * ch)) & 0xFF, y = (c1 >> (16 - 8 * ch)) & 0xFF;
            sx[ch] += x, sy[ch] += y, sxx[ch] += x * x, sxy[ch] += x * y;
        }
        n++;
    }
    if (n < 4 || differ < 4)
        return c;
    uint32 out = 0;
    for (int ch = 0; ch < 3; ch++) {
        double d = n * sxx[ch] - sx[ch] * sx[ch];
        double a = d ? (n * sxy[ch] - sx[ch] * sy[ch]) / d : 1.0;
        double v = a * ((c >> (16 - 8 * ch)) & 0xFF) + (sy[ch] - a * sx[ch]) / n;
        out |= (uint32)(v < 0 ? 0 : v > 255 ? 255 : (int)(v + 0.5)) << (16 - 8 * ch);
    }
    return out;
}

static void Hook_Draw() {
    const Shades* s = g_character > 0 && RSDK ? &Of(g_character) : nullptr;
    if (!s || !s->ok) {
        g_draw();
        return;
    }
    // its player, when it's the extra's base (Tails / Knuckles): shown Sonic's ID for the streaks' frames
    Entity* self = Readable(SCENE_INFO, sizeof(SceneInfo)) ? SCENE_INFO->entity : nullptr;
    EntityPlayer* p = self && Readable(self, PLAYER_FIELD + sizeof(void*)) ? *(EntityPlayer**)((uint8*)self + PLAYER_FIELD)
                                                                           : nullptr;
    int base = Extra(g_character).base;
    int32 id = p && Readable(p, sizeof(EntityPlayer)) ? p->characterID : 0;
    bool asSonic = (base == 1 && id == ID_TAILS) || (base == 2 && id == ID_KNUCKLES);
    uint32 saved[2][SHADES], water[SHADES];
    for (int i = 0; i < SHADES; i++) {
        saved[0][i] = (uint32)RSDK->GetPaletteEntry(0, SLOT + i);
        saved[1][i] = (uint32)RSDK->GetPaletteEntry(1, SLOT + i);
        water[i] = Water(s->rgb[i]);  // (before any slot changes: the fit reads slots 2-20)
    }
    for (int i = 0; i < SHADES; i++) {
        RSDK->SetPaletteEntry(0, SLOT + i, s->rgb[i]);
        RSDK->SetPaletteEntry(1, SLOT + i, water[i]);
    }
    if (asSonic)
        p->characterID = ID_SONIC;
    g_draw();
    if (asSonic && p->characterID == ID_SONIC)
        p->characterID = id;
    for (int i = 0; i < SHADES; i++) {
        RSDK->SetPaletteEntry(0, SLOT + i, saved[0][i]);
        RSDK->SetPaletteEntry(1, SLOT + i, saved[1][i]);
    }
}

// ActClear's registered draw: wrapped when it's this build's, else left alone
static DrawFn Wrap(DrawFn draw) {
    static const uint8 THUNK[] = {0x48, 0x8b, 0x0d, 0x91, 0x4d, 0xcb, 0x02, 0x48, 0x8b, 0x09, 0xe9, 0xa1, 0x06, 0x00, 0x00};
    static const uint8 LOAD[] = {0x4c, 0x8b, 0xa9, 0xc8, 0x00, 0x00, 0x00};              // mov r13, [rcx+0xC8]
    static const uint8 READ[] = {0x41, 0x8b, 0x85, 0xa8, 0x01, 0x00, 0x00, 0x83, 0xf8, 0x02};  // mov eax, [r13+0x1A8]; cmp 2
    bool ok = (uintptr_t)draw == DRAW_THUNK && Readable((void*)DRAW_THUNK, sizeof(THUNK))
              && !memcmp((void*)DRAW_THUNK, THUNK, sizeof(THUNK)) && Readable((void*)PLAYER_LOAD, sizeof(LOAD))
              && !memcmp((void*)PLAYER_LOAD, LOAD, sizeof(LOAD));
    for (uintptr_t at : ID_READS)
        ok = ok && Readable((void*)at, sizeof(READ)) && !memcmp((void*)at, READ, sizeof(READ));
    if (!ok) {
        Log("results accent: ActClear's draw at %p is DIFFERENT (another game build?): not wrapped (Sonic's blue)",
            (void*)draw);
        return draw;
    }
    if (draw != (DrawFn)Hook_Draw)
        g_draw = draw;
    return Hook_Draw;
}
}  // namespace accent

static void Hook_RegisterObject(void** staticVars, const char* name, uint32 entityClassSize, uint32 staticClassSize,
                                void (*update)(void), void (*lateUpdate)(void), void (*staticUpdate)(void),
                                void (*draw)(void), void (*create)(void*), void (*stageLoad)(void),
                                void (*editorDraw)(void), void (*editorLoad)(void), void (*serialize)(void),
                                void (*staticLoad)(void*)) {
    if (name) {  // (every object's name by its statics, for the shot log; a relaunch registers the same ones again)
        bool known = false;
        for (auto& o : shots::g_objectNames)
            known |= o.first == staticVars;
        if (!known)
            shots::g_objectNames.push_back({staticVars, name});
    }
    if (name && strcmp(name, "SuperHammer") == 0)
        shots::Register(staticVars, entityClassSize, staticClassSize, update, stageLoad, draw);
    if (name && strcmp(name, "Water") == 0)  // (water walk reads its level: WaterWalk.h)
        g_waterStatics = staticVars;
    if (name && strcmp(name, "S3K_SaveSlot") == 0 && update) {
        g_saveSlotUpdate = (UpdateFn2)update;
        update = (void (*)(void))Hook_SaveSlotUpdate;
        memset(g_slotLoaded, 0, sizeof(g_slotLoaded));
        memset(g_slotShowsExtra, 0, sizeof(g_slotShowsExtra));
        memset(g_slotPicture, 0, sizeof(g_slotPicture));
    }
    if (name && strcmp(name, "S3K_SaveMenu") == 0 && update) {
        g_saveMenuUpdate = (UpdateFn2)update;
        update = (void (*)(void))Hook_SaveMenuUpdate;
    }
    if (name && strcmp(name, "BreakableWall") == 0 && update) {
        g_breakableWallUpdate = (UpdateFn)update;
        update = (void (*)(void))Hook_BreakableWallUpdate;
        Log("wrapped BreakableWall update (extras that break walls, as Knuckles)");
    }
    spin::Wrap(name, update);  // (DashWheel, DashLift: SpinStandIn.h)
    for (const KnuxWrap& w : KNUX_WRAPS) {  // (the other Knuckles-only barriers: rock piles, ice columns)
        if (!name || strcmp(name, w.name) != 0 || !update)
            continue;
        static const uint8 THUNK[] = {0x48, 0x8b, 0x0d};  // mov rcx, [rip+...] (then mov rcx, [rcx]; jmp)
        bool ok = (uintptr_t)update == w.thunk && Readable((void*)w.thunk, 11)
                  && memcmp((void*)w.thunk, THUNK, sizeof(THUNK)) == 0 && ((uint8*)w.thunk)[10] == 0xe9
                  && Readable((void*)w.check, w.n) && memcmp((void*)w.check, w.bytes, w.n) == 0;
        if (ok) {
            *w.original = (UpdateFn)update;
            update = (void (*)(void))w.hook;
            Log("wrapped %s update (extras that break walls, as Knuckles)", w.name);
        } else {
            Log("%s update at %p is DIFFERENT (another game build?): not wrapped (Knuckles only, as before)", w.name,
                (void*)update);
        }
    }
    if (name && strcmp(name, "RisingLava") == 0 && staticUpdate) {  // (fire immunity: AsFireShield)
        g_risingLavaStatic = staticUpdate;
        staticUpdate = Hook_RisingLavaStatic;
    }
    if (name && strcmp(name, "S3K_LRZSetup") == 0 && staticUpdate) {
        g_lrzSetupStatic = staticUpdate;
        staticUpdate = Hook_LrzSetupStatic;
    }
    if (name && strcmp(name, "Conveyor") == 0 && update) {
        g_conveyorUpdate = (UpdateFn)update;
        update = (void (*)(void))Hook_ConveyorUpdate;
    }
    if (name && strcmp(name, "InvisibleBlock") == 0 && update) {  // (fire immunity: its Flame kind, LRZ's lava)
        if (InvisibleBlockMatches((void*)update)) {
            g_invisibleBlockUpdate = (UpdateFn)update;
            update = (void (*)(void))Hook_InvisibleBlockUpdate;
            Log("wrapped InvisibleBlock update (fire immunity: Flame blocks, Lava Reef's lava)");
        } else {
            Log("InvisibleBlock update at %p is DIFFERENT (another game build?): not wrapped (its lava hurts everyone)",
                (void*)update);
        }
    }
    if (name && strcmp(name, "S3K_SS_Player") == 0 && draw) {
        g_ssPlayerDraw = draw;
        draw = Hook_SSPlayerDraw;
    }
    if (name && strcmp(name, "ActClear") == 0 && draw)  // (the extra's results accent)
        draw = accent::Wrap(draw);

    if (name && strcmp(name, "Player") == 0 && update) {
        g_playerUpdate = (UpdateFn)update;
        update = (void (*)(void))Hook_PlayerUpdate;
        Log("wrapped Player update");
    }
    if (name && strcmp(name, "Player") == 0 && draw)  // (Ristar's arms and hands: StarGrab.h; afterimages: Ghost.h)
        draw = shots::PlayerIconWrap(anchor::Wrap(head::Wrap(star::Wrap(afterImage::Wrap(draw)))));  // (and Headdy's thrown head: HeadThrow.h;
                                                                      // monitor_swap's icon pass: shots::PlayerDraw)
    g_registerObject(staticVars, name, entityClassSize, staticClassSize, update, lateUpdate, staticUpdate, draw, create,
                     stageLoad, editorDraw, editorLoad, serialize, staticLoad);
}

// ---------------------------------------------------------------- linking
static void PatchTableEntry(size_t offset, void* hook, void** original) {
    void** entry = (void**)((char*)RSDK + offset);
    if (*entry == hook)
        return;  // already patched (the game links again when S3&K is restarted)
    DWORD old;
    VirtualProtect(entry, sizeof(void*), PAGE_READWRITE, &old);
    *original = *entry;
    *entry = hook;
    VirtualProtect(entry, sizeof(void*), old, &old);
}

typedef void (*LinkGameLogicFn)(void* info);
static LinkGameLogicFn g_linkGameLogic = nullptr;

static void Hook_LinkGameLogicDLL(void* info) {
    g_engineInfo = (void**)info;
    RSDK = *(FunctionTable**)info;
    g_sceneInfo = nullptr;
    // A new S3&K session (the log shows one link per start, before the save menu): no pick carried over from the
    // last one, so Origins' Blue Spheres mode, which never shows the save menu, plays the game's own characters
    g_menuPick = -1;
    g_specialExtra = 0;
    Log("LinkGameLogicDLL: function table at %p", (void*)RSDK);
    PatchTableEntry(offsetof(FunctionTable, LoadSpriteAnimation), (void*)Hook_LoadSpriteAnimation,
                    (void**)&g_loadSpriteAnimation);
    PatchTableEntry(offsetof(FunctionTable, RegisterObject), (void*)Hook_RegisterObject, (void**)&g_registerObject);
    g_linkGameLogic(info);
}

// ---------------------------------------------------------------- sprite memory probe (debug)
// Press F8 in any game: finds the Retro Engine's table of loaded sprite sheets by searching memory for a
// sheet name every S1/S2 stage loads, and logs each sheet with its size and place in sprite memory.
// Read-only: it never writes to the game.
static bool ReadMem(const void* at, void* out, size_t size) {
    SIZE_T got = 0;
    return ReadProcessMemory(GetCurrentProcess(), at, out, size, &got) && got == size;
}

// The engine's sheet table (found by the first probes): 84-byte entries of name[64], width, height,
// widthShift, depth, dataPosition (offset into one block of sprite memory; sheets are packed end to end).
struct LegacySurface {
    char name[0x40];
    int32_t width, height, widthShift, depth, dataPosition;
};
static_assert(sizeof(LegacySurface) == 0x54, "LegacySurface layout");

static bool PlausibleSurface(const LegacySurface& s) {
    return s.width > 0 && s.width <= 2048 && s.height > 0 && s.height <= 4096 && s.dataPosition >= 0
           && (1 << s.widthShift) == s.width;
}

// Log the table around a matching entry at `hit` (the table's start isn't known, so scan both ways)
static const char* LogSurfaceTable(const char* hit) {
    const char* first = hit;
    LegacySurface s{};
    for (int k = 0; k < 64; k++) {  // back to the first entry
        if (!ReadMem(first - sizeof(LegacySurface), &s, sizeof(s)) || !(PlausibleSurface(s) || !s.name[0]))
            break;
        first -= sizeof(LegacySurface);
    }
    long long end = 0;
    int listed = 0;
    for (int k = 0; k < 128; k++) {
        if (!ReadMem(first + k * sizeof(LegacySurface), &s, sizeof(s)))
            break;
        if (!s.name[0] || !PlausibleSurface(s)) {
            if (s.name[0] || s.width)
                break;  // past the table
            continue;  // an empty slot
        }
        s.name[sizeof(s.name) - 1] = 0;
        long long top = (long long)s.dataPosition + (long long)s.width * s.height;
        Log("  [%2d] %-36s %4dx%-4d at %8d .. %8lld", k, s.name, s.width, s.height, s.dataPosition, top);
        if (top > end)
            end = top;
        listed++;
    }
    Log("  %d sheet(s), sprite memory used up to %lld bytes (table at %p)", listed, end, (void*)first);
    return first;
}

// Debugging: every probe_*.bin in the mod folder is a strip of sheet pixels; F8 also searches memory for each and
// logs where it is (is a sheet's image in the game's sprite memory, as the file has it?)
static void ProbePatterns() {
    // probe_dump.txt ("<hex address> <size>"): also save that much memory to probe_dump.bin
    if (FILE* d = fopen((DllFolder() + "\\probe_dump.txt").c_str(), "r")) {
        unsigned long long addr = 0;
        unsigned size = 0;
        if (fscanf(d, "%llx %u", &addr, &size) == 2 && size <= (16u << 20)) {
            std::vector<char> mem(size);
            bool ok = ReadMem((const void*)addr, mem.data(), size);
            if (FILE* o = ok ? fopen((DllFolder() + "\\probe_dump.bin").c_str(), "wb") : nullptr) {
                fwrite(mem.data(), 1, size, o);
                fclose(o);
            }
            Log("  dump of %u bytes at %llx: %s", size, addr, ok ? "saved to probe_dump.bin" : "not readable");
        }
        fclose(d);
    }
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA((DllFolder() + "\\probe_*.bin").c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE)
        return;
    do {
        std::string path = DllFolder() + "\\" + fd.cFileName;
        FILE* f = fopen(path.c_str(), "rb");
        if (!f)
            continue;
        std::vector<char> pat(4096);
        pat.resize(fread(pat.data(), 1, pat.size(), f));
        fclose(f);
        if (pat.size() < 16)
            continue;
        int hits = 0;
        std::vector<char> buf;
        MEMORY_BASIC_INFORMATION mbi{};
        for (char* at = (char*)0x10000; VirtualQuery(at, &mbi, sizeof(mbi)); at = (char*)mbi.BaseAddress + mbi.RegionSize) {
            bool readable = mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
                            && (mbi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ
                                               | PAGE_EXECUTE_READWRITE));
            if (!readable || mbi.RegionSize > (256u << 20))
                continue;
            buf.resize(mbi.RegionSize);
            if (!ReadMem(mbi.BaseAddress, buf.data(), mbi.RegionSize))
                continue;
            for (size_t i = 0; i + pat.size() <= buf.size(); i++)
                if (buf[i] == pat[0] && memcmp(&buf[i], pat.data(), pat.size()) == 0) {
                    if (hits < 8)
                        Log("  pattern %s at %p", fd.cFileName, (void*)((char*)mbi.BaseAddress + i));
                    hits++;
                }
        }
        Log("  pattern %s (%zu bytes): %d hit(s)", fd.cFileName, pat.size(), hits);
    } while (FindNextFileA(h, &fd));
    FindClose(h);
}

static void ProbeSpriteMemory() {
    // Sheets every stage loads, to find the table by. (An extra in Sonic CD loads its own Display copy, so Display
    // alone found nothing there.)
    static const char* const needles[] = {"Global/Display.gif", "Global/Items3.gif", "Global/Items2.gif"};
    Log("---- sprite memory probe");
    int tables = 0;
    std::vector<const char*> seen;  // tables already logged (found by another needle)
    std::vector<char> buf;
    MEMORY_BASIC_INFORMATION mbi{};
    for (char* at = (char*)0x10000; VirtualQuery(at, &mbi, sizeof(mbi)); at = (char*)mbi.BaseAddress + mbi.RegionSize) {
        bool readable = mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
                        && (mbi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ
                                           | PAGE_EXECUTE_READWRITE));
        if (!readable || mbi.RegionSize > (256u << 20))
            continue;
        buf.resize(mbi.RegionSize);
        if (!ReadMem(mbi.BaseAddress, buf.data(), mbi.RegionSize))
            continue;
        for (size_t i = 0; i + sizeof(LegacySurface) <= buf.size(); i++) {
            bool match = false;
            for (const char* needle : needles) {
                size_t len = strlen(needle);
                if (memcmp(&buf[i], needle, len) == 0 && buf[i + len] == 0)
                    match = true;
            }
            if (!match)
                continue;
            LegacySurface s;
            memcpy(&s, &buf[i], sizeof(s));
            if (!PlausibleSurface(s))
                continue;  // just the text somewhere, not a table entry
            const char* at = (const char*)mbi.BaseAddress + i;
            bool known = false;
            for (const char* t : seen)
                if (at >= t && at < t + 128 * sizeof(LegacySurface))
                    known = true;
            if (known)
                continue;
            seen.push_back(LogSurfaceTable(at));
            tables++;
        }
    }
    Log("---- probe done: %d table(s)", tables);
    ProbePatterns();
}

// ---------------------------------------------------------------- Sonic CD's shot button (Y)
// CD's scripts only see A/B/C (all jump) and Start. While an extra with a Y move plays, CD's script keeps the
// magic number CD_SHOT_MAGIC in the global game.callbackParam3 (build_soniccd.py); on a Y press, find that
// global in the game's own data (once) and swap the number for 1, which the script takes as "fire".
constexpr int32_t CD_SHOT_MAGIC = 0x4E53593F;
static int32_t* g_cdShot = nullptr;

// A player script with a move held on Y (build_soniccd.Y_REARM_HOLD: Heavy's Charge) keeps CD_HOLD_MAGIC there instead:
// a press still writes 1, and while Y stays down each poll writes 2 (the script counts it as held for a few frames).
constexpr int32_t CD_HOLD_MAGIC = 0x4E53593E;

static int32_t* FindCdShotGlobal(bool hold = false) {
    HMODULE exe = GetModuleHandleA(nullptr);
    std::vector<int32_t> buf;
    MEMORY_BASIC_INFORMATION mbi{};
    for (char* at = (char*)exe; VirtualQuery(at, &mbi, sizeof(mbi)) && mbi.AllocationBase == exe;
         at = (char*)mbi.BaseAddress + mbi.RegionSize) {
        bool writable = mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
                        && (mbi.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE));
        if (!writable)
            continue;
        buf.resize(mbi.RegionSize / 4);
        if (!ReadMem(mbi.BaseAddress, buf.data(), buf.size() * 4))
            continue;
        for (size_t i = 0; i < buf.size(); i++)
            if (buf[i] == CD_SHOT_MAGIC || (hold && buf[i] == CD_HOLD_MAGIC))
                return (int32_t*)mbi.BaseAddress + i;
    }
    return nullptr;
}

static void CdShotButton() {
    static bool wasDown = false;
    static DWORD lastSearch = 0;
    bool down = false;
    if (Readable(CONTROLLERS, sizeof(ControllerState) * 5))
        for (int c = 0; c <= 4; c++)
            down |= CONTROLLERS[c].keyY.down != 0;
    bool pressed = down && !wasDown;
    wasDown = down;
    if (!down)
        return;
    int32_t value = 0;
    if (!g_cdShot || !ReadMem(g_cdShot, &value, 4)
        || (value != CD_SHOT_MAGIC && value != CD_HOLD_MAGIC && value != 1 && value != 2)) {
        if (!pressed || GetTickCount() - lastSearch < 3000)  // not in CD (or no extra with a shot): don't search on
            return;                                           // every press (and only on a press)
        lastSearch = GetTickCount();
        g_cdShot = FindCdShotGlobal(true);
        Log("CD shot button: magic %s", g_cdShot ? "found" : "not found (not in CD?)");
        if (!g_cdShot)
            return;
    }
    if (!ReadMem(g_cdShot, &value, 4))
        return;
    if (pressed && (value == CD_SHOT_MAGIC || value == CD_HOLD_MAGIC))
        *g_cdShot = 1;
    else if (value == CD_HOLD_MAGIC)  // (held, and the script asked: CD_HOLD_MAGIC)
        *g_cdShot = 2;
}

// [Debug] Cheats=1, F6 (temporary): where does S3&K keep the emeralds? Each press snapshots the game's globals and
// logs what changed since the last press, keeping to values that look like an emerald count or mask.
static void EmeraldProbe() {
    static std::vector<int> last;
    GlobalVariables* g = Readable(GLOBALS, sizeof(void*)) ? *GLOBALS : nullptr;
    size_t n = (offsetof(GlobalVariables, waitSSRetry) + 4) / 4;
    if (!g || !Readable(g, n * 4)) {
        Log("F6: globals not readable");
        return;
    }
    std::vector<int> now((int*)g, (int*)g + n);
    if (last.size() != n) {
        last = now;
        Log("F6: snapshot taken (%zu ints), press again after changing the emeralds", n);
        return;
    }
    int changed = 0, shown = 0;
    for (size_t i = 0; i < n; i++) {
        if (now[i] == last[i])
            continue;
        changed++;
        unsigned a = (unsigned)last[i], b = (unsigned)now[i];
        int pa = __builtin_popcount(a), pb = __builtin_popcount(b);
        bool looks = (b <= 14 && a <= 14) || (b < 0x10000 && a < 0x10000 && pb != pa && pb <= 14);
        if (looks && shown < 300) {
            shown++;
            Log("F6: +0x%zx: %d (0x%x) -> %d (0x%x)", i * 4, last[i], a, now[i], b);
        }
    }
    Log("F6: %d ints changed, %d shown", changed, shown);
    last = now;
}

static bool g_extraSavesReady = false;  // extras' save views are hooked: the thread below keeps their file
static void WriteExtraSavesIfChanged();

static void OwnSoundMailbox();  // (below: Sonic 1/2/CD's own sounds)

static DWORD WINAPI ProbeThread(LPVOID) {
    // NoSwapS3K.ini [Debug] ProbeSeconds=N also probes every N seconds, in case the key doesn't get through
    int every = GetPrivateProfileIntA("Debug", "ProbeSeconds", 0, (DllFolder() + "\\NoSwapS3K.ini").c_str());
    Log("sprite memory probe ready: press F8%s", every > 0 ? " (and every few seconds, [Debug] ProbeSeconds)" : "");
    bool wasDown = false;
    bool cheats = GetPrivateProfileIntA("Debug", "Cheats", 0, (DllFolder() + "\\NoSwapS3K.ini").c_str()) != 0, f7Was = false;
    if (cheats)
        Log("cheats on: F7 gives 100 rings and the 7 Chaos Emeralds");
    DWORD last = GetTickCount();
    for (;;) {
        Sleep(10);
        CdShotButton();
        OwnSoundMailbox();
        static DWORD lastSave = GetTickCount();
        if (g_extraSavesReady && GetTickCount() - lastSave >= 2000) {
            lastSave = GetTickCount();
            WriteExtraSavesIfChanged();
        }
        if (every > 0 && GetTickCount() - last >= (DWORD)every * 1000) {
            last = GetTickCount();
            Log("timed probe");
            ProbeSpriteMemory();
        }
        // the key's held-down bit: Wine doesn't set the "pressed since last call" bit reliably
        bool down = (GetAsyncKeyState(VK_F8) & 0x8000) != 0;
        if (down && !wasDown) {
            Log("F8 pressed");
            ProbeSpriteMemory();
        }
        wasDown = down;
        bool f7 = cheats && (GetAsyncKeyState(VK_F7) & 0x8000) != 0;
        if (f7 && !f7Was)
            InterlockedExchange(&g_cheatRings, 1);
        f7Was = f7;
        static bool f6Was = false;
        bool f6 = cheats && (GetAsyncKeyState(VK_F6) & 0x8000) != 0;
        if (f6 && !f6Was)
            InterlockedExchange(&g_playerProbe, 1);
        f6Was = f6;
    }
}

// ---------------------------------------------------------------- Origins character select (experiment)
// Origins' character select popup (UICharacterSelectWindow) lists "character kinds" 0-6 (Sonic, Tails,
// Knuckles, Sonic+Tails, Knuckles+Tails, Amy, Amy+Tails; picture PRM_chara_<kind+1>) from per-game
// tables of 7-byte rows, one row per unlock state (0xFF = unused). Sonic 1's table is at 0x140D58748.
// [Debug] MenuTest gives Sonic 1's Plus rows (4-6) a test row: 1 = Sonic 2's full row, all 7 kinds
// (crashed on opening the popup), 2 = the usual four plus Sonic again (a 5th card, known kinds only),
// 3 = four cards with Sonic+Tails in Amy's place (works), 4 and 5 = six and seven cards of known kinds
// (how many card slots the layout has). Only done if the table
// holds what this game build had.
static void MenuTest(int n) {
    auto* s1 = (uint8*)0x140D58748;
    static const uint8 expected[49] = {
        0, 1, 2, 255, 255, 255, 255,  0, 1, 2, 255, 255, 255, 255,  0, 255, 255, 255, 255, 255, 255,
        0, 1, 2, 255, 255, 255, 255,  0, 1, 2, 5, 255, 255, 255,  0, 1, 2, 5, 255, 255, 255,
        0, 1, 2, 5, 255, 255, 255};
    static const uint8 rows[5][7] = {
        {0, 1, 2, 5, 3, 4, 6}, {0, 1, 2, 5, 0, 255, 255}, {0, 1, 2, 3, 255, 255, 255},
        {0, 1, 2, 5, 0, 1, 255}, {0, 1, 2, 5, 0, 1, 2}};
    if (n < 1 || n > 5 || !Readable(s1, 49) || memcmp(s1, expected, 49) != 0) {
        Log("menu test: Sonic 1's character table isn't what was found, left alone");
        return;
    }
    DWORD old;
    VirtualProtect(s1, 49, PAGE_READWRITE, &old);
    for (int row = 4; row < 7; row++)
        memcpy(s1 + 7 * row, rows[n - 1], 7);
    VirtualProtect(s1, 49, old, &old);
    Log("menu test %d: Sonic 1's character select row changed", n);
}

// ---------------------------------------------------------------- Origins character select: real kinds
// Origins' character select popup offers "kinds" 0-6, which are the classic games' character IDs
// (0 Sonic, 1 Tails, 2 Knuckles, 3 Sonic+Tails, 4 Knuckles+Tails, 5 Amy, 6 Amy+Tails); Sonic 1, 2 and CD
// get the picked kind as their playerListPos. Extras are kinds 7 on, from the runtime roster (the registry, Roster.h:
// each installed package's permanent kind; up to 254):
// - the popup's rows (0x1403E0D80 RowPicker) get the offered extras' kinds appended;
// - its kind table (picture pattern + name text keys, 0x140D586A0, 7 entries) is replaced by a copy with an entry up
//   to the highest kind offered, and its "kind <= 6" checks (calls to a shared 0x140331220, which other 7-value enums
//   also use, so only these call sites) go to a "kind <= that highest kind" stub;
// - saves: every save record lookup goes through SlotIndex(mode, game, kind) (0x14045DA50), which has
//   no slot for kinds >= 7 (callers then crash on a null record): extras use Sonic's slot for now;
//   SetLastKind (0x14045CB50) never stores an extra's kind in Origins' save;
// - launch: KindAllowedInGame (0x140331080) would turn a rejected kind into Sonic & Tails.
// Addresses are for Steam build 12197262; every patch site is checked byte for byte first.
// On by default; NoSwapS3K.ini [Menu] RealKinds=0 turns it off.

struct KindEntry {
    const char* pattern;  // SurfRide pattern of the card picture, e.g. "PRM_chara_1"
    const char* name1;    // text keys of the card's name lines
    const char* name2;
};
static KindEntry* g_kinds = nullptr;  // in memory within +-2 GB of the exe (rip-relative references)
static uint8 g_rows[4][7];            // per game (RSDK order: S1, S2, S3K, CD), rows handed to the menu
static uint8 g_master[7 + KIND_LIMIT];    // the game's full list of kinds, in card order
static int g_masterCount = 0;
static int g_pageStart = 0;                // index in g_master of the first card
static uint8 g_entryFor[KIND_LIMIT + 1][16]; // each kind's entry, as the build filled it (or a copy)

typedef const uint8* (*RowPickerFn)(uint8 game, uint8 mode, uint8 a, uint8 b);
static RowPickerFn g_rowPicker = nullptr;
static void BuildMaster(const uint8* row);
static const uint8* Hook_RowPicker(uint8 game, uint8 mode, uint8 a, uint8 b) {
    const uint8* row = g_rowPicker(game, mode, a, b);
    if (!row || game == 2)  // S1, S2 and CD (RSDK order: 0 S1, 1 S2, 2 S3&K, 3 CD); S3&K has its own picker
        return row;
    BuildMaster(row);  // the full list; the popup gets its first 7 (paging shows the rest)
    uint8* out = g_rows[game];
    memset(out, 0xFF, 7);
    memcpy(out, g_master, g_masterCount < 7 ? g_masterCount : 7);
    return out;
}

typedef uint8 (*SlotIndexFn)(uint8 mode, uint8 game, uint8 kind);
static SlotIndexFn g_slotIndex = nullptr;
static uint8 Hook_SlotIndex(uint8 mode, uint8 game, uint8 kind) {
    return g_slotIndex(mode, game, kind >= FIRST_EXTRA_KIND ? 0 : kind);  // (any extra kind: Sonic's slot)
}

typedef void (*SetLastKindFn)(void* save, uint8 mode, uint8 game, uint8 kind);
static SetLastKindFn g_setLastKind = nullptr;
static void SetActiveCharacter(const char* key, const char* why);
static void RecordLastExtra(uint8 mode, uint8 game, uint8 kind);
static void Hook_SetLastKind(void* save, uint8 mode, uint8 game, uint8 kind) {
    if (game != 2) {  // (S3&K picks on its own save screen: ReadSettings)
        SetActiveCharacter(KindKey(kind), "character select");
        RecordLastExtra(mode, game, kind);  // (the CONTINUE bubble: below)
    }
    g_setLastKind(save, mode, game, kind >= FIRST_EXTRA_KIND ? 0 : kind);
}

typedef bool (*KindAllowedFn)(uint8 kind, uint8 game);
static KindAllowedFn g_kindAllowed = nullptr;
static bool Hook_KindAllowed(uint8 kind, uint8 game) {
    if (kind >= FIRST_EXTRA_KIND)
        return Offered(kind) && game != 2;  // not in S3&K (it picks characters on its own save screen)
    return g_kindAllowed(kind, game);
}

// Whether a card shows its second name line: vanilla only for "+Tails" kinds (KindHasTails, 0x140331060);
// for extras, when its card has its own picture and a two-word name ("METAL" / "SONIC": SetUpMenuCards)
typedef bool (*KindHasTailsFn)(uint8 kind);
static const KindHasTailsFn KindHasTails = (KindHasTailsFn)0x140331060;
static bool CardHasSecondLine(uint8 kind) {
    if (kind >= FIRST_EXTRA_KIND) {
        const RosterEntry* e = RosterOf(kind);
        return e && e->cardSlot && e->cardPicture && e->cardTwoLines;
    }
    return KindHasTails(kind);
}

// ---- extras' own saves. Origins keeps its saves as records per (mode, game, kind) slot, reached through
// four "views" View(this, out, a, b, kind) -> out = {vtable, record*, owner}: 16-byte records (0x140459B60:
// byte 0 = 1 when there's a save, byte 1 = zone, u32 at 4 bit 25 = cleared), 0xA0-byte (0x140459420),
// 0x8000-byte (0x140459360: the classic game's save RAM) and 0x10001-byte (0x14045A190). Kinds 7+ have no
// slot (SlotIndex gives them Sonic's, above), so each view is wrapped: after the original fills `out`, an
// extra's record pointer is swapped for a buffer of ours. The buffers live in their own file,
// %APPDATA%\SEGA\SonicOrigins\NoSwap\extras.sav: Origins' save file is never touched.
constexpr int SAVE_VIEWS = 4;
static const uint32 VIEW_SIZE[SAVE_VIEWS] = {0x10, 0xA0, 0x8000, 0x10001};
struct ExtraRecordBuf {
    std::vector<uint8> data, saved;  // live record, and what's in the file
};
static std::map<uint32, ExtraRecordBuf> g_extraSaves;  // key: view, a, b, kind (a byte each)
static CRITICAL_SECTION g_extraSavesLock;

static uint32 RecordKey(int view, uint8 a, uint8 b, uint8 kind) {
    return (uint32)view << 24 | (uint32)a << 16 | (uint32)b << 8 | kind;
}

static uint8* ExtraRecord(int view, uint8 a, uint8 b, uint8 kind) {
    EnterCriticalSection(&g_extraSavesLock);
    ExtraRecordBuf& r = g_extraSaves[RecordKey(view, a, b, kind)];
    if (r.data.empty())
        r.data.assign(VIEW_SIZE[view], 0);  // a new record: no save yet
    LeaveCriticalSection(&g_extraSavesLock);
    return r.data.data();
}

static std::string ExtraSavePath() {
    const char* appData = getenv("APPDATA");
    return std::string(appData ? appData : ".") + "\\SEGA\\SonicOrigins\\NoSwap\\extras.sav";
}

// The extras' permanent names (package keys): the file stores records under them, never under kinds (KindKey /
// KindOfKey: the roster). A record whose extra isn't installed is kept as it is (g_orphans) and written back, so it's
// there again if that extra returns.
struct OrphanRecord {
    uint8 view, a, b;
    std::string key;
    std::vector<uint8> data;
};
static std::vector<OrphanRecord> g_orphans;

// The extra each (mode, game) was last played with (the main menu's CONTINUE bubble, below): the extra's key under
// (mode << 8 | game), kept whether or not that extra is installed. In the file as records of view LAST_EXTRA_VIEW (a =
// mode, b = game, no data), written after all the others (an older DLL stops reading at the first one: it loses only
// these).
constexpr uint8 LAST_EXTRA_VIEW = 0x80;
static std::map<uint16_t, std::string> g_lastExtra;
static bool g_lastExtraDirty = false;

// File version 2: "NSWS" u32 2, u32 count, then per record: u8 view, u8 a, u8 b, u8 name length, name, u32 size,
// data. Version 1 (records keyed by kind, before 2026-09-26) is read with the numbering it was written with (the
// legacy kinds 7-27, Roster.h), kept as extras.sav.v1.bak and rewritten as version 2.
static void LoadExtraSaves() {
    FILE* f = fopen(ExtraSavePath().c_str(), "rb");
    if (!f)
        return;
    char magic[4];
    uint32 version = 0, count = 0;
    bool migrate = false;
    if (fread(magic, 1, 4, f) == 4 && !memcmp(magic, "NSWS", 4) && fread(&version, 4, 1, f) == 1
        && (version == 1 || version == 2) && fread(&count, 4, 1, f) == 1) {
        for (uint32 i = 0; i < count; i++) {
            uint8 view, a, b;
            std::string key;
            uint32 size;
            if (version == 1) {
                uint32 k;
                if (fread(&k, 4, 1, f) != 1)
                    break;
                view = (uint8)(k >> 24), a = (uint8)(k >> 16), b = (uint8)(k >> 8);
                key = LegacyKey((uint8)k) ? LegacyKey((uint8)k) : "";
            } else {
                uint8 hdr[4];
                if (fread(hdr, 1, 4, f) != 4)
                    break;
                view = hdr[0], a = hdr[1], b = hdr[2];
                key.resize(hdr[3]);
                if (hdr[3] && fread(&key[0], 1, hdr[3], f) != hdr[3])
                    break;
            }
            if (fread(&size, 4, 1, f) != 1)
                break;
            if (version == 2 && view == LAST_EXTRA_VIEW && size == 0) {
                if (!key.empty())
                    g_lastExtra[(uint16_t)(a << 8 | b)] = key;
                continue;
            }
            if (view >= SAVE_VIEWS || size != VIEW_SIZE[view])
                break;
            std::vector<uint8> data(size);
            if (fread(data.data(), 1, size, f) != size)
                break;
            int kind = KindOfKey(key);
            if (kind < 0) {
                g_orphans.push_back({view, a, b, key, std::move(data)});
                continue;
            }
            ExtraRecordBuf& r = g_extraSaves[RecordKey(view, a, b, (uint8)kind)];
            r.data = std::move(data);
            if (version == 2)
                r.saved = r.data;  // (version 1: left unsaved, so the next write converts the file)
        }
        migrate = version == 1;
    }
    fclose(f);
    if (migrate)
        CopyFileA(ExtraSavePath().c_str(), (ExtraSavePath() + ".v1.bak").c_str(), TRUE);
    Log("extras' saves: %u record(s) loaded (%u kept aside for extras not installed, %u last-played extras) from %s%s",
        (unsigned)g_extraSaves.size(), (unsigned)g_orphans.size(), (unsigned)g_lastExtra.size(), ExtraSavePath().c_str(),
        migrate ? " (version 1: converting to names, old file kept as .v1.bak)" : "");
}

// From the background thread: write the file when a record changed (write a new file, then swap it in)
static void WriteExtraSavesIfChanged() {
    EnterCriticalSection(&g_extraSavesLock);
    bool changed = g_lastExtraDirty;
    for (auto& [key, r] : g_extraSaves)
        changed |= r.data != r.saved;
    if (changed) {
        std::string path = ExtraSavePath(), dir = path.substr(0, path.find_last_of('\\'));
        CreateDirectoryA(dir.substr(0, dir.find_last_of('\\')).c_str(), nullptr);
        CreateDirectoryA(dir.c_str(), nullptr);
        std::string tmp = path + ".new";
        if (FILE* f = fopen(tmp.c_str(), "wb")) {
            uint32 version = 2, count = 0;
            for (auto& [key, r] : g_extraSaves)
                count += KindKey((uint8)key) != nullptr;
            count += (uint32)g_orphans.size() + (uint32)g_lastExtra.size();
            fwrite("NSWS", 1, 4, f), fwrite(&version, 4, 1, f), fwrite(&count, 4, 1, f);
            auto put = [f](uint8 view, uint8 a, uint8 b, const std::string& name, const std::vector<uint8>& data) {
                uint8 hdr[4] = {view, a, b, (uint8)name.size()};
                uint32 size = (uint32)data.size();
                fwrite(hdr, 1, 4, f), fwrite(name.data(), 1, name.size(), f);
                fwrite(&size, 4, 1, f), fwrite(data.data(), 1, size, f);
            };
            for (auto& [key, r] : g_extraSaves)
                if (const char* name = KindKey((uint8)key))
                    put((uint8)(key >> 24), (uint8)(key >> 16), (uint8)(key >> 8), name, r.data);
            for (auto& o : g_orphans)
                put(o.view, o.a, o.b, o.key, o.data);
            for (auto& [where, name] : g_lastExtra)  // (last: see LAST_EXTRA_VIEW)
                put(LAST_EXTRA_VIEW, (uint8)(where >> 8), (uint8)where, name, {});
            bool ok = fclose(f) == 0;
            if (ok && MoveFileExA(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING)) {
                for (auto& [key, r] : g_extraSaves)
                    r.saved = r.data;
                g_lastExtraDirty = false;
                Log("extras' saves written");
            }
        }
    }
    LeaveCriticalSection(&g_extraSavesLock);
}

typedef void* (*SaveViewFn)(void* self, void* out, uint8 a, uint8 b, uint8 kind);
static SaveViewFn g_views[SAVE_VIEWS];
template <int View>
static void* Hook_SaveView(void* self, void* out, uint8 a, uint8 b, uint8 kind) {
    void* result = g_views[View](self, out, a, b, kind);
    void** record = (void**)((uint8*)out + 8);
    if (Offered(kind) && *record)
        *record = ExtraRecord(View, a, b, kind);
    return result;
}

// A card entry (the popup's 16 bytes) for an extra, from its own 16-byte record
static void ExtraEntry(uint8* entry, uint8 a, uint8 b, uint8 kind) {
    const uint8* rec = ExtraRecord(0, a, b, kind);
    memset(entry, 0, 16);
    entry[0] = kind;
    if (rec[0] == 1) {
        entry[1] = rec[1];
        entry[0xD] = 2 | ((*(const uint32*)(rec + 4) >> 25) & 1);
    }
}

// ---- the main menu's CONTINUE bubble. Origins keeps one "last kind" per (mode 0-3, game in RSDK order: 0 S1, 1 S2,
// 2 S3&K, 3 CD) in its save: GetLastKind(save, mode, game) 0x14045A110, SetLastKind 0x14045CB50 (hooked above: it
// never stores an extra, Origins' save only holds vanilla kinds). The main menu reads it
// - at 0x1403E509D (its fill, 0x1403E4F10: into its table of the bubbles' kinds, which SetIconChara draws),
// - at 0x1403E92AD (CONTINUE, 0x1403E8FC0: the kind whose save must exist, 0x1403E70D0),
// - at 0x1403546D9 (the menu scene's launch state, 0x140354080: the kind the game starts with; a kind its row check
//   0x1403E0FA0, called at 0x140354705, rejects becomes Sonic, or Sonic & Tails in Sonic 2).
// So the extra each (mode, game) was last played with is remembered here (g_lastExtra, by its key, in extras.sav), and
// those three reads say the extra when Origins says Sonic (0); the row check lets an offered extra through at that one
// call. SetIconChara (0x1403E7830) rejects kinds above 6, so its two calls (0x1403E8436: the fill's bubbles;
// 0x1403E94D3: after a pick in the select) go through Hook_IconChara: Sonic's setup, then the extra's head cell
// (SetUpMenuCards: head crop g_headFirstCrop + slot - 1 of pattern_chara_1; Sonic's head when there's none).
// S3&K (game 2) is left alone: it picks characters on its own save screen, and Origins' kind for it must stay vanilla
// (KindAllowedInGame turns anything else into Sonic & Tails).
static int g_headFirstCrop = 0;  // the head crop of card slot 1 (0: the menu archives have no head cells)
static bool RedirectCall(uintptr_t site, uintptr_t from, uintptr_t to);

static void RecordLastExtra(uint8 mode, uint8 game, uint8 kind) {
    if (mode > 3 || game == 2)
        return;
    const char* key = kind >= FIRST_EXTRA_KIND ? KindKey(kind) : nullptr;
    uint16_t where = (uint16_t)(mode << 8 | game);
    EnterCriticalSection(&g_extraSavesLock);
    auto it = g_lastExtra.find(where);
    bool change = key ? it == g_lastExtra.end() || it->second != key : it != g_lastExtra.end();
    if (change) {
        if (key)
            g_lastExtra[where] = key;
        else
            g_lastExtra.erase(where);
        g_lastExtraDirty = true;
    }
    LeaveCriticalSection(&g_extraSavesLock);
    if (change)
        Log("continue bubble: mode %d game %d last played by %s", mode, game, key ? key : "a vanilla character");
}

// The extra (mode, game) was last played with, if it's installed (0: none)
static int LastExtraKind(uint8 mode, uint8 game) {
    if (mode > 3 || game == 2)
        return 0;
    EnterCriticalSection(&g_extraSavesLock);
    auto it = g_lastExtra.find((uint16_t)(mode << 8 | game));
    int kind = it == g_lastExtra.end() ? -1 : KindOfKey(it->second);
    LeaveCriticalSection(&g_extraSavesLock);
    return kind >= FIRST_EXTRA_KIND && Offered(kind) ? kind : 0;
}

// A log line per distinct event, at most `cap` per source
struct MenuLog {
    int count = 0;
    uint32 last = 0xFFFFFFFF;
    bool Due(uint32 what, int cap = 60) {
        if (what == last || count >= cap)
            return false;
        last = what;
        return ++count, true;
    }
};

typedef uint8 (*GetLastKindFn)(void* save, uint8 mode, uint8 game);
static const GetLastKindFn GetLastKind = (GetLastKindFn)0x14045A110;
static uint8 LastKindAt(int site, void* save, uint8 mode, uint8 game) {
    static const char* const SITE[] = {"bubble fill", "CONTINUE check", "launch", "game scene"};
    static MenuLog logs[4];
    uint8 kind = GetLastKind(save, mode, game);
    int extra = kind == 0 ? LastExtraKind(mode, game) : 0;
    if (extra && logs[site].Due((uint32)extra << 16 | mode << 8 | game))
        Log("continue bubble: %s (mode %d, game %d): Origins says Sonic, the last played is %s (kind %d)", SITE[site],
            mode, game, KindKey(extra), extra);
    return extra ? (uint8)extra : kind;
}
static uint8 Hook_LastKindFill(void* save, uint8 mode, uint8 game) { return LastKindAt(0, save, mode, game); }
static uint8 Hook_LastKindCheck(void* save, uint8 mode, uint8 game) { return LastKindAt(1, save, mode, game); }
static uint8 Hook_LastKindLaunch(void* save, uint8 mode, uint8 game) {
    uint8 kind = LastKindAt(2, save, mode, game);
    if (game < 4 && game != 2) {  // (S1, S2, CD: the character select does the same when a card is picked)
        static MenuLog log;
        if (log.Due((uint32)kind << 16 | mode << 8 | game, 200))
            Log("continue bubble: the game starts (mode %d, game %d) with kind %d%s%s", mode, game, kind,
                kind >= FIRST_EXTRA_KIND ? ", " : "", kind >= FIRST_EXTRA_KIND ? KindKey(kind) : "");
        SetActiveCharacter(kind >= FIRST_EXTRA_KIND ? KindKey(kind) : nullptr, "continue");
    }
    return kind;
}

// The fourth read, at 0x14033A422 in the game scene's setup from a queued start request (0x14033A070: the kind into
// its +0xC9, then the 16-byte save view with it). The menu launch above isn't the only way into a game: a pick in the
// popup that Origins then starts through this request (seen 2026-09-28: Sonic 1 after a CONTINUE, Cream picked in the
// popup, played as Sonic with Cream's package active and her script loaded) read Origins' own last kind, which is never
// an extra (Hook_SetLastKind stores Sonic), so the extra started as Sonic. Same rule as the others: the extra last
// picked for (mode, game) when Origins says Sonic, and nothing else.
static uint8 Hook_LastKindScene(void* save, uint8 mode, uint8 game) {
    uint8 kind = LastKindAt(3, save, mode, game);
    if (kind >= FIRST_EXTRA_KIND && game < 4 && game != 2)
        SetActiveCharacter(KindKey(kind), "game scene");
    return kind;
}

typedef bool (*RowHasKindFn)(uint8 game, uint8 mode, uint8 kind, uint8 a, uint8 b);
static const RowHasKindFn RowHasKind = (RowHasKindFn)0x1403E0FA0;
static bool Hook_LaunchRowHasKind(uint8 game, uint8 mode, uint8 kind, uint8 a, uint8 b) {
    if (kind >= FIRST_EXTRA_KIND && game != 2 && Offered(kind))
        return true;  // (the popup's first page may not show it: the row the check reads is that page)
    return RowHasKind(game, mode, kind, a, b);
}

typedef void (*SetIconCharaFn)(void* menu, void* layer, uint8 kind);
typedef void (*SetCropIndexFn)(void* layer, const char* cast, int index);
static const SetIconCharaFn SetIconChara = (SetIconCharaFn)0x1403E7830;
static const SetCropIndexFn SetCropIndex = (SetCropIndexFn)0x140483A00;
static void Hook_IconChara(void* menu, void* layer, uint8 kind) {
    if (kind < FIRST_EXTRA_KIND || kind >= KIND_LIMIT) {
        SetIconChara(menu, layer, kind);
        return;
    }
    SetIconChara(menu, layer, 0);  // (Sonic's: PRM_chara_1, one head, crop 0)
    const RosterEntry* e = RosterOf(kind);
    int crop = 0;
    if (layer && e && g_headFirstCrop && e->cardSlot && e->headPicture) {
        crop = g_headFirstCrop + e->cardSlot - 1;
        SetCropIndex(layer, "pattern_chara_1", crop);
    }
    static MenuLog log;
    if (log.Due((uint32)kind << 16 | (uint32)crop, 200))
        Log("continue bubble: head of kind %d (%s): %s", kind, e ? e->key.c_str() : "not installed",
            crop ? ("head crop " + std::to_string(crop) + " (card slot " + std::to_string(e->cardSlot) + ")").c_str()
                 : "Sonic's head (no head cell for it)");
}

// The calls above, redirected through jump stubs in memory near the exe (`stubs`: 16 bytes each). Every call site and
// the functions called are checked first; any mismatch and nothing is patched.
static void SetUpContinueBubble(uint8* stubs) {
    struct Site {
        uintptr_t at, calls;
        void* hook;
    };
    const Site sites[] = {
        {0x1403E509D, (uintptr_t)GetLastKind, (void*)Hook_LastKindFill},
        {0x1403E92AD, (uintptr_t)GetLastKind, (void*)Hook_LastKindCheck},
        {0x1403546D9, (uintptr_t)GetLastKind, (void*)Hook_LastKindLaunch},
        {0x14033A422, (uintptr_t)GetLastKind, (void*)Hook_LastKindScene},
        {0x140354705, (uintptr_t)RowHasKind, (void*)Hook_LaunchRowHasKind},
        {0x1403E8436, (uintptr_t)SetIconChara, (void*)Hook_IconChara},
        {0x1403E94D3, (uintptr_t)SetIconChara, (void*)Hook_IconChara},
    };
    static const uint8 getLastKind[] = {0x48, 0x0F, 0xBE, 0xC2, 0x4C, 0x8B, 0xC9, 0x83, 0xF8, 0x07, 0x77, 0x4B};
    static const uint8 rowHasKind[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x41, 0x0F, 0xB6, 0xC1, 0x41, 0x0F, 0xB6, 0xD8};
    static const uint8 setIconChara[] = {0x48, 0x85, 0xD2, 0x0F, 0x84, 0x8D, 0x00, 0x00, 0x00, 0x48, 0x89, 0x5C, 0x24,
                                         0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x41, 0x0F, 0xB6, 0xC8};
    static const uint8 setCropIndex[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x41, 0x8B, 0xD8, 0xE8};
    // (and the crop table SetIconChara reads: kind 0 is Sonic's head, crop 0 of pattern_chara_1, none of _2)
    static const uint8 cropTable0[] = {0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0xFF};
    const char* bad = nullptr;
    if (memcmp((void*)GetLastKind, getLastKind, sizeof(getLastKind)) != 0)
        bad = "GetLastKind 0x14045A110";
    else if (memcmp((void*)RowHasKind, rowHasKind, sizeof(rowHasKind)) != 0)
        bad = "the row check 0x1403E0FA0";
    else if (memcmp((void*)SetIconChara, setIconChara, sizeof(setIconChara)) != 0)
        bad = "SetIconChara 0x1403E7830";
    else if (memcmp((void*)SetCropIndex, setCropIndex, sizeof(setCropIndex)) != 0)
        bad = "SetCropIndex 0x140483A00";
    else if (memcmp((void*)0x140D59518, cropTable0, sizeof(cropTable0)) != 0)
        bad = "the head crop table 0x140D59518";
    for (auto& s : sites)
        if (!bad && (*(uint8*)s.at != 0xE8 || s.at + 5 + *(int32_t*)(s.at + 1) != s.calls)) {
            static char where[64];
            snprintf(where, sizeof(where), "the call at %#llx", (unsigned long long)s.at);
            bad = where;
        }
    if (bad) {
        Log("continue bubble: %s isn't what was found: left alone (extras' bubbles show Sonic, CONTINUE starts Sonic)", bad);
        return;
    }
    int ok = 0, n = 0;
    for (auto& s : sites) {
        uint8* stub = stubs + 16 * n++;
        stub[0] = 0x48, stub[1] = 0xB8;  // mov rax, imm64 / jmp rax
        memcpy(stub + 2, &s.hook, 8);
        stub[10] = 0xFF, stub[11] = 0xE0;
        ok += RedirectCall(s.at, s.calls, (uintptr_t)stub);
    }
    Log("continue bubble: %d of %d calls redirected (%u last-played extras on record)", ok, n,
        (unsigned)g_lastExtra.size());
}

// ---- paging: the popup has 7 card slots (obj_btn_1-7), so it shows a window of 7 onto the game's full
// list (vanilla kinds + extras). Moving right from the last card scrolls the list by one (from the end:
// back to the start), left from the first likewise; the cards are refilled in place with the game's own
// calls. The popup keeps nothing per card: OK and the save line read the entries (window+0x2B0, 16 bytes
// each: kind, zone, mission data, flags with bit 1 = has save) by index.
// Popup (UICharacterSelectWindow): +0x264 handle of its cursor controller, +0x2A8 layer "lay",
// +0x2B0/+0x2B8 entries and count. Cursor controller (ui::MenuItemContainer): +0x250 "cursor moved"
// delegates (element 0 = the popup's: vtable 0x140D58B78, popup at +8, handler 0x1403E10A0 at +0x10),
// +0x2EC current index, +0x2F0/+0x2F8 items (MenuItem*, card at +0x18).

typedef void* (*ResolveHandleFn)(void* handle);
typedef void (*PlayAnimFn)(void* cast, const char* name, int start);
typedef void* (*FindChildFn)(void* comp, const char* cast, const char* child);
typedef void (*SetTextKeyFn)(void* textCast, const char* key);
typedef void* (*GetComponentFn)(void* object, void* cls);
typedef void (*UpdateSaveInfoFn)(void* window, uint32 index);
typedef void (*PlaySfxFn)(uint32* out, void* window, int sound);
static const ResolveHandleFn ResolveHandle = (ResolveHandleFn)0x1405C6420;
static const PlayAnimFn PlayAnim = (PlayAnimFn)0x140481C20;
static const FindChildFn FindChild = (FindChildFn)0x14047F760;
static const SetTextKeyFn SetTextKey = (SetTextKeyFn)0x140483330;
static const GetComponentFn GetComponent = (GetComponentFn)0x1405C6FD0;
static const UpdateSaveInfoFn UpdateSaveInfo = (UpdateSaveInfoFn)0x1403E1140;
static const PlaySfxFn PlaySfx = (PlaySfxFn)0x140454170;
static void* const LAYOUT_COMPONENT = (void*)0x142882E30;

static uint8*& Entries(void* window) { return *(uint8**)((uint8*)window + 0x2B0); }
static uint64_t& EntryCount(void* window) { return *(uint64_t*)((uint8*)window + 0x2B8); }

// The popup that owns this cursor controller, or null for every other menu
static void* PopupOf(void* ctrl) {
    uint8* list = *(uint8**)((uint8*)ctrl + 0x250);
    uint64_t n = *(uint64_t*)((uint8*)ctrl + 0x258);
    if (!n || !list || *(void**)list != (void*)0x140D58B78 || *(void**)(list + 0x10) != (void*)0x1403E10A0)
        return nullptr;
    return *(void**)(list + 8);
}

// The game's own kinds for this row, then every offered extra (kind order: kinds with no package are skipped)
static void BuildMaster(const uint8* row) {
    g_masterCount = 0;
    for (int k = 0; k < 7; k++)
        if (row[k] != 0xFF)
            g_master[g_masterCount++] = row[k];
    for (auto& e : g_roster)
        g_master[g_masterCount++] = (uint8)e.kind;
}

static void Refill(void* window, void* ctrl) {
    uint8* entries = Entries(window);
    uint64_t count = EntryCount(window);
    void* comp = GetComponent(window, LAYOUT_COMPONENT);
    void** items = *(void***)((uint8*)ctrl + 0x2F0);
    for (uint64_t i = 0; i < count; i++) {
        uint8 kind = g_master[g_pageStart + i];
        memcpy(entries + 16 * i, g_entryFor[kind], 16);
        void* card = *(void**)((uint8*)items[i] + 0x18);
        PlayAnim(card, g_kinds[kind].pattern, 0);
        PlayAnim(card, entries[16 * i + 0xD] & 2 ? "PRM_save_icon_on" : "PRM_save_icon_off", 0);
        char name[16];
        snprintf(name, sizeof(name), "obj_btn_%d", (int)i + 1);
        if (void* t = FindChild(comp, name, "sysf_btn_name_1"))
            SetTextKey(t, g_kinds[kind].name1);
        if (void* t = FindChild(comp, name, "sysf_btn_name_2"))
            SetTextKey(t, CardHasSecondLine(kind) ? g_kinds[kind].name2 : "");
    }
    UpdateSaveInfo(window, *(uint32*)((uint8*)ctrl + 0x2EC));
    uint32 sound = 0;
    PlaySfx(&sound, window, 0);
}

typedef int (*StepIndexFn)(void* ctrl, int index);
static StepIndexFn g_nextIndex = nullptr, g_prevIndex = nullptr;
static int Step(void* ctrl, int index, int dir, StepIndexFn original) {
    void* window = PopupOf(ctrl);
    if (!window || g_masterCount <= (int)EntryCount(window))
        return original(ctrl, index);
    int count = (int)EntryCount(window);
    if (dir > 0 && index == count - 1) {
        bool atEnd = g_pageStart + count >= g_masterCount;
        g_pageStart = atEnd ? 0 : g_pageStart + 1;
        Refill(window, ctrl);
        return atEnd ? 0 : index;  // same index: the cursor stays, SetCursor does nothing
    }
    if (dir < 0 && index == 0) {
        bool atStart = g_pageStart == 0;
        g_pageStart = atStart ? g_masterCount - count : g_pageStart - 1;
        Refill(window, ctrl);
        return atStart ? count - 1 : 0;
    }
    return original(ctrl, index);
}
static int Hook_NextIndex(void* ctrl, int index) { return Step(ctrl, index, 1, g_nextIndex); }
static int Hook_PrevIndex(void* ctrl, int index) { return Step(ctrl, index, -1, g_prevIndex); }

// Y on a card: that character's level select. The title scripts (S1, S2, CD) hold CD_SHOT_MAGIC in a
// variable while the select is open; Y sets it to 1 and confirms the card like OK does
// (MenuItemContainer's decide: FireDelegates(ctrl, ctrl+0x290, index), 0x1403BF8D0), so the script
// opens the level select instead of the save.
typedef void (*MenuUpdateFn)(void* ctrl, float dt);
typedef void (*FireDelegatesFn)(void* ctrl, void* list, uint32 index);
static MenuUpdateFn g_menuUpdate = nullptr;
static const FireDelegatesFn FireDelegates = (FireDelegatesFn)0x1403BF8D0;
static int32_t* FindCdShotGlobal(bool hold);
// Gamepad Y straight from XInput: Origins' menus run outside the Retro Engine games, so the RSDK controller state
// (CONTROLLERS, S3&K's) doesn't update there and never saw the press
struct PadState { DWORD packet; WORD buttons; BYTE lt, rt; SHORT lx, ly, rx, ry; };
typedef DWORD(WINAPI* XInputGetStateFn)(DWORD user, PadState* state);
static bool PadY() {
    static XInputGetStateFn get = [] {
        for (const char* dll : {"xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"})
            if (HMODULE m = LoadLibraryA(dll))
                if (auto f = (XInputGetStateFn)GetProcAddress(m, "XInputGetState"))
                    return f;
        Log("character select: no XInput, Y only from the games' own input");
        return (XInputGetStateFn) nullptr;
    }();
    constexpr WORD XINPUT_Y = 0x8000;
    PadState st{};
    for (DWORD u = 0; get && u < 4; u++)
        if (get(u, &st) == 0 && (st.buttons & XINPUT_Y))
            return true;
    return false;
}
static void Hook_MenuUpdate(void* ctrl, float dt) {
    if (!PopupOf(ctrl)) {  // (only the character select's card list watches Y: every menu's lists pass through here)
        g_menuUpdate(ctrl, dt);
        return;
    }
    static bool wasDown = false;
    bool down = PadY();
    if (Readable(CONTROLLERS, sizeof(ControllerState) * 5))
        for (int c = 0; c <= 4; c++)
            down |= CONTROLLERS[c].keyY.down != 0;
    bool pressed = down && !wasDown;
    wasDown = down;
    bool inputOn = (*((uint8*)ctrl + 0x318) & 4) != 0;
    if (pressed && !inputOn)
        Log("character select: Y while its input is off");
    if (pressed && inputOn) {
        if (int32_t* flag = FindCdShotGlobal()) {
            *flag = 1;
            Log("character select: Y on card %u, level select", *(uint32*)((uint8*)ctrl + 0x2EC));
            FireDelegates(ctrl, (uint8*)ctrl + 0x290, *(uint32*)((uint8*)ctrl + 0x2EC));
            return;
        }
        Log("character select: Y, but the title script's flag wasn't found");
    }
    g_menuUpdate(ctrl, dt);
}

// The popup's build (vtable slot 6): back to the first page, and keep each kind's entry
typedef uint64_t (*BuildFn)(void* window, void* arg);
static BuildFn g_build = nullptr;
static uint64_t Hook_Build(void* window, void* arg) {
    g_pageStart = 0;
    uint64_t result = g_build(window, arg);
    uint8* entries = Entries(window);
    uint64_t count = EntryCount(window);
    for (uint64_t i = 0; i < count; i++)
        memcpy(g_entryFor[entries[16 * i]], entries + 16 * i, 16);
    uint8 a = *((uint8*)window + 0x251), b = *((uint8*)window + 0x250);  // the views' mode/game arguments
    for (auto& e : g_roster) {
        bool shown = false;
        for (uint64_t i = 0; i < count; i++)
            shown |= entries[16 * i] == e.kind;
        if (!shown)  // off the first page: from the extra's own save record
            ExtraEntry(g_entryFor[e.kind], a, b, (uint8)e.kind);
    }
    return result;
}

// The sprite credit box (tools/build_origins_menu.py edit_credit: a text cast of NoSwap's own in the popup's scene,
// under the zone-name bar, with no text as shipped). Whenever the popup shows the highlighted card's save line
// (UpdateSaveInfo: on opening, on every cursor move, and after Refill), the box's text key is set to that card's credit
// key (CardCreditKey(slot): its package's "credit_short", written in by SetUpMenuCards), or "" (nothing shown) for the
// game's own characters and extras without one. Nothing is touched unless the scene has the box and it's a text cast
// (the check UpdateSaveInfo makes before its own SetTextKey, 0x1403E11C5).
typedef void* (*FindCastFn)(void* comp, const char* cast);
typedef void* (*CastClassFn)(void* cast);
static const FindCastFn FindCast = (FindCastFn)0x14047F7A0;
static void* const TEXT_CAST_CLASS = (void*)0x142882E78;
static UpdateSaveInfoFn g_updateSaveInfo = nullptr;
static std::string g_creditCast;  // the box's cast name (SetUpMenuCards, from the descriptor; "": credits off)
static char g_creditKeys[KIND_LIMIT][48];  // per kind, the credit key last given (the game may keep the pointer)
static void ShowCredit(void* window, uint32 index) {
    if (g_creditCast.empty() || !Entries(window) || index >= EntryCount(window))
        return;
    void* comp = GetComponent(window, LAYOUT_COMPONENT);
    void* cast = comp ? FindCast(comp, g_creditCast.c_str()) : nullptr;
    if (!cast)
        return;
    void* cls = (*(CastClassFn**)cast)[1](cast);
    while (cls && cls != TEXT_CAST_CLASS)
        cls = *(void**)cls;
    if (!cls)
        return;
    uint8 kind = Entries(window)[16 * index];
    const char* key = "";
    const RosterEntry* e = RosterOf(kind);
    if (e && e->cardSlot && e->cardCredit) {
        snprintf(g_creditKeys[kind], sizeof(g_creditKeys[kind]), "%s", CardCreditKey(e->cardSlot).c_str());
        key = g_creditKeys[kind];
    }
    SetTextKey(cast, key);
}
static void Hook_UpdateSaveInfo(void* window, uint32 index) {
    g_updateSaveInfo(window, index);
    ShowCredit(window, index);
}

// Memory for code and data the exe reaches with rip-relative 32-bit offsets
static uint8* AllocNearExe(size_t size) {
    for (uintptr_t at = 0x15C000000; at < 0x1B0000000; at += 0x10000)
        if (void* p = VirtualAlloc((void*)at, size, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE))
            return (uint8*)p;
    return nullptr;
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

// A `call rel32` at `site` that calls `from`: make it call `to`
static bool RedirectCall(uintptr_t site, uintptr_t from, uintptr_t to) {
    if (*(uint8*)site != 0xE8 || site + 5 + *(int32_t*)(site + 1) != from)
        return false;
    int32_t rel = (int32_t)(to - (site + 5));
    return PatchBytes(site + 1, &rel, 4);
}

// A `lea r64, [rip+disp32]` at `site` that loads `from`: make it load `to`
static bool RedirectLea(uintptr_t site, uintptr_t from, uintptr_t to) {
    auto* b = (uint8*)site;
    if ((b[0] & 0xFB) != 0x48 || b[1] != 0x8D || (b[2] & 0xC7) != 0x05 || site + 7 + *(int32_t*)(site + 3) != from)
        return false;
    int32_t disp = (int32_t)(to - (site + 7));
    return PatchBytes(site + 3, &disp, 4);
}

static bool HookAt(uintptr_t at, const uint8* expect, size_t size, void* hook, void** original) {
    if (memcmp((void*)at, expect, size) != 0)
        return false;
    return MH_CreateHook((void*)at, hook, original) == MH_OK && MH_EnableHook((void*)at) == MH_OK;
}

static void SetUpCreditBox() {
    static const uint8 updateSaveInfo[] = {0x40, 0x55, 0x53, 0x41, 0x57, 0x48, 0x8D, 0xAC, 0x24, 0x40, 0xFF, 0xFF,
                                           0xFF, 0x48, 0x81, 0xEC, 0xC0, 0x01, 0x00, 0x00, 0x8B, 0xDA};
    if (g_creditCast.empty()) {
        Log("sprite credits: off (no credit box in NoSwap's menu archives)");
        return;
    }
    bool hooked = HookAt(0x1403E1140, updateSaveInfo, sizeof(updateSaveInfo), (void*)Hook_UpdateSaveInfo,
                         (void**)&g_updateSaveInfo);
    Log("sprite credits: hook %s", hooked ? "installed" : "FAILED (the box stays empty)");
}

static void SetUpRealKinds() {
    const uintptr_t IS_KIND_7 = 0x140331220, KIND_TABLE = 0x140D586A0, WINDOW_BUILD = 0x1403E0030,
                    SHOULD_SHOW = 0x1403E0F10;
    // the kind table: an entry for every kind up to the highest offered (at most 254: 0x100 + 255 * 24 bytes)
    int kinds = g_maxKind + 1;
    uint8* nearMem = AllocNearExe(0x2000);
    if (!nearMem) {
        Log("real kinds: no memory near the exe");
        Warn("The character select couldn't be extended (no memory near the game): no extra characters in it.");
        return;
    }
    static_assert(0x100 + KIND_LIMIT * sizeof(KindEntry) <= 0x2000, "kind table past the near memory");
    // "kind <= the highest kind offered": cmp cl,imm8 / setbe al / ret (kinds are bytes; 6 with no extras)
    const uint8 stub[] = {0x80, 0xF9, (uint8)g_maxKind, 0x0F, 0x96, 0xC0, 0xC3};
    memcpy(nearMem, stub, sizeof(stub));
    g_kinds = (KindEntry*)(nearMem + 0x100);
    memcpy(g_kinds, (void*)KIND_TABLE, 7 * sizeof(KindEntry));
    // Each extra's card: its slot in the menu archives (SetUpMenuCards: pattern CardPattern(slot, lines), name keys
    // CardNameKey(slot, 1 / 2)); its base character's picture when its slot has no picture of its own; its base's
    // picture and no name with no slot. A kind with no package isn't offered: its entry is Sonic's, never shown.
    static char keys[KIND_LIMIT][2][48], patterns[KIND_LIMIT][24];
    static char blank[] = "";
    int fallbacks = 0;
    for (int k = FIRST_EXTRA_KIND; k < kinds; k++) {
        const RosterEntry* e = RosterOf(k);
        if (e && e->cardSlot) {
            for (int line = 0; line < 2; line++)
                snprintf(keys[k][line], sizeof(keys[k][line]), "%s", CardNameKey(e->cardSlot, line + 1).c_str());
            snprintf(patterns[k], sizeof(patterns[k]), "%s", CardPattern(e->cardSlot, e->cardTwoLines ? 2 : 1).c_str());
            g_kinds[k] = {e->cardPicture ? patterns[k] : g_kinds[e->data.base].pattern, keys[k][0], keys[k][1]};
            if (!e->cardPicture)
                fallbacks++;
        } else if (e) {
            g_kinds[k] = {g_kinds[e->data.base].pattern, blank, blank};  // (base 0-2: Sonic, Tails, Knuckles)
            fallbacks++;
            Log("real kinds: kind %d (%s) has no card: its base's picture, no name", k, e->key.c_str());
        } else {
            g_kinds[k] = g_kinds[0];
        }
    }
    Log("real kinds: kind table 0-%d (%d offered extras, %d showing their base's picture)", g_maxKind,
        (int)g_roster.size(), fallbacks);

    // The popup's own checks and table references (offsets into the window build function)
    int ok = 0, total = 0;
    for (uintptr_t off : {0x78, 0x183, 0x1EE, 0x9AC, 0xB3E})
        ok += RedirectCall(WINDOW_BUILD + off, IS_KIND_7, (uintptr_t)nearMem), total++;
    ok += RedirectCall(SHOULD_SHOW + 0x47, IS_KIND_7, (uintptr_t)nearMem), total++;
    for (uintptr_t off : {0xA01, 0xA9B, 0xB0B})
        ok += RedirectLea(WINDOW_BUILD + off, KIND_TABLE, (uintptr_t)g_kinds), total++;
    // the second name line: a near jump to CardHasSecondLine (mov rax, imm64 / jmp rax)
    uint8* jump = nearMem + 0x40;
    jump[0] = 0x48, jump[1] = 0xB8;
    *(uint64_t*)(jump + 2) = (uint64_t)(uintptr_t)&CardHasSecondLine;
    jump[10] = 0xFF, jump[11] = 0xE0;
    ok += RedirectCall(WINDOW_BUILD + 0xAB1, (uintptr_t)KindHasTails, (uintptr_t)jump), total++;
    Log("real kinds: %d of %d menu patches applied", ok, total);
    if (ok != total) {
        Warn("The character select's code isn't what NoSwap knows (%d of %d checks passed: another game version, or "
             "another mod changed it): no extra characters in it.", ok, total);
        return;  // a different game build: leave the rest alone
    }

    MH_STATUS mh = MH_Initialize();
    if (mh != MH_OK && mh != MH_ERROR_ALREADY_INITIALIZED) {
        Warn("MinHook couldn't start (%d): no extra characters in the character select.", (int)mh);
        return;
    }
    static const uint8 rowPicker[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89,
                                      0x74, 0x24, 0x18, 0x57, 0x41, 0x56, 0x41, 0x57, 0x48, 0x83, 0xEC, 0x20};
    static const uint8 slotIndex[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89,
                                      0x74, 0x24, 0x18, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x0F, 0xB6, 0xE9};
    static const uint8 setLastKind[] = {0x44, 0x0F, 0xBE, 0xD2, 0x4C, 0x8B, 0xD9, 0x84, 0xD2, 0x74, 0x3C};
    static const uint8 kindAllowed[] = {0x80, 0xF9, 0x06, 0x77, 0x2A, 0x0F, 0xBE, 0xD2, 0x85, 0xD2, 0x74, 0x1C};
    InitializeCriticalSection(&g_extraSavesLock);  // (before SetLastKind's hook: it records the last-played extra)
    LoadExtraSaves();
    bool hooked = HookAt(0x1403E0D80, rowPicker, sizeof(rowPicker), (void*)Hook_RowPicker, (void**)&g_rowPicker)
                  && HookAt(0x14045DA50, slotIndex, sizeof(slotIndex), (void*)Hook_SlotIndex, (void**)&g_slotIndex)
                  && HookAt(0x14045CB50, setLastKind, sizeof(setLastKind), (void*)Hook_SetLastKind,
                            (void**)&g_setLastKind)
                  && HookAt(0x140331080, kindAllowed, sizeof(kindAllowed), (void*)Hook_KindAllowed,
                            (void**)&g_kindAllowed);
    static const uint8 nextIndex[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x7C, 0x24, 0x10, 0x4C, 0x8B,
                                      0x99, 0xF8, 0x02, 0x00, 0x00, 0x45, 0x33, 0xC9};
    static const uint8 prevIndex[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x7C, 0x24, 0x10, 0x4C, 0x8B,
                                      0x99, 0xF8, 0x02, 0x00, 0x00, 0x45, 0x33, 0xC0};
    static const uint8 menuUpdate[] = {0x48, 0x89, 0x5C, 0x24, 0x20, 0x57, 0x48, 0x83, 0xEC, 0x40, 0x8B, 0x81,
                                       0x18, 0x03, 0x00, 0x00};
    static const uint8 build[] = {0x48, 0x89, 0x54, 0x24, 0x10, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55,
                                  0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0xAC, 0x24, 0x78, 0xF2, 0xFF};
    static const uint8 view16[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x74, 0x24, 0x10, 0x57, 0x48, 0x83,
                                   0xEC, 0x20, 0x41, 0x0F, 0xB6, 0xC0, 0x48, 0x8B, 0xDA};
    static const uint8 view8k[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x41, 0x0F, 0xB6,
                                   0xC0, 0x48, 0x8B, 0xDA};
    const uintptr_t VIEW_AT[SAVE_VIEWS] = {0x140459B60, 0x140459420, 0x140459360, 0x14045A190};
    void* const VIEW_HOOK[SAVE_VIEWS] = {(void*)Hook_SaveView<0>, (void*)Hook_SaveView<1>, (void*)Hook_SaveView<2>,
                                         (void*)Hook_SaveView<3>};
    for (int v = 0; v < SAVE_VIEWS; v++) {
        bool shortForm = v == 1 || v == 2;  // 0x140459420 and 0x140459360 save one register fewer
        hooked = hooked && HookAt(VIEW_AT[v], shortForm ? view8k : view16, shortForm ? sizeof(view8k) : sizeof(view16),
                                  VIEW_HOOK[v], (void**)&g_views[v]);
    }
    g_extraSavesReady = hooked;
    hooked = hooked
             && HookAt(0x1403BFBB0, nextIndex, sizeof(nextIndex), (void*)Hook_NextIndex, (void**)&g_nextIndex)
             && HookAt(0x1403BFC40, prevIndex, sizeof(prevIndex), (void*)Hook_PrevIndex, (void**)&g_prevIndex)
             && HookAt(0x1403C0810, menuUpdate, sizeof(menuUpdate), (void*)Hook_MenuUpdate, (void**)&g_menuUpdate)
             && HookAt(WINDOW_BUILD, build, sizeof(build), (void*)Hook_Build, (void**)&g_build);
    Log("real kinds: hooks %s", hooked ? "installed" : "FAILED");
    if (!hooked)
        Warn("The character select's hooks couldn't go in (another game version, or another mod hooks the same "
             "functions): the extra characters' cards and saves may not work.");
    static_assert(0x100 + KIND_LIMIT * sizeof(KindEntry) <= 0x1C00, "kind table past the stubs");
    if (hooked)
        SetUpContinueBubble(nearMem + 0x1C00);  // (7 stubs of 16 bytes; room for 64)
    if (hooked)
        SetUpCreditBox();
}

// ---------------------------------------------------------------- entry points
BOOL WINAPI DllMain(HINSTANCE, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH)
        Log("NoSwapS3K.dll attached");
    return TRUE;
}

// ---------------------------------------------------------------- character packages (docs/plan-b-modular-characters.md)
// A package is a folder with a noswap_character.json ({"key": "noswap.gamma", ...}) and that character's files, laid
// out like NoSwap's own (Sonic1u/Data/...). Packages live in NoSwap's characters/ folder or are mods of their own
// (any enabled mod with the file at its root). While a character is active, every file the game opens from NoSwap's
// folder is served from its package instead when the package has one: the hook on CreateFileW below (HiteModLoader's
// own AddInclude / GetRedirectedPath did nothing when called from Init).
struct Package {
    std::string key;
    std::wstring root;  // with a trailing backslash
    ExtraData data;     // its S3&K data (data.loaded false: none usable)
    std::string error;  // why not
};
static std::vector<Package> g_packages;           // filled once in Init, never changed after
static const Package* volatile g_active = nullptr;  // the active character's package (nullptr: none)
static std::wstring g_modDirW;                    // NoSwap's folder: lower case, backslashes, no drive, trailing '\\'
static std::wstring g_modsRootW;                  // the folder holding it (the mods folder), in the same form
static std::wstring g_cacheDirW;  // NoSwap's cache folder, with a trailing backslash (SetUpPackages: the mod folder's
                                  // cache\, or %LOCALAPPDATA%\NoSwap\cache\ when that can't be written)

static std::wstring NormW(std::wstring p) {
    for (auto& c : p) {
        if (c == L'/')
            c = L'\\';
        c = towlower(c);
    }
    return p;
}
static std::wstring Widen(const std::string& s) {
    wchar_t w[1024];
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, w, 1024);
    return w;
}
static std::string Narrow(const std::wstring& w) {
    char buf[1024];
    WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, buf, sizeof(buf), nullptr, nullptr);
    return buf;
}

static bool ReadWholeFile(const std::wstring& path, std::string& text) {
    FILE* f = _wfopen(path.c_str(), L"rb");
    if (!f)
        return false;
    text.clear();
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0 && text.size() < (1u << 20))
        text.append(buf, n);
    fclose(f);
    return true;
}

// A folder with a noswap_character.json: read all of it (ExtraData.h) for its key and its S3&K data
static void AddPackage(const std::wstring& dir) {
    std::wstring root = dir;
    if (root.back() != L'\\' && root.back() != L'/')
        root += L'\\';
    std::string text;
    if (!ReadWholeFile(root + L"noswap_character.json", text))
        return;
    Package pkg;
    pkg.root = root;
    LoadExtraData(text, pkg.data, pkg.error);
    pkg.key = pkg.data.key;
    if (pkg.key.empty()) {
        Log("packages: %snoswap_character.json unusable (%s), left out", Narrow(root).c_str(), pkg.error.c_str());
        return;
    }
    for (auto& p : g_packages)
        if (p.key == pkg.key) {
            Log("packages: %s found twice, the first one is used", pkg.key.c_str());
            return;
        }
    Log("packages: %s at %s", pkg.key.c_str(), Narrow(root).c_str());
    for (auto& w : pkg.data.warnings)  // (what its data lacked or had too much of)
        Log("packages:   %s: %s", pkg.key.c_str(), w.c_str());
    g_packages.push_back(std::move(pkg));
}

static std::string RegistryPath() {
    const char* appData = getenv("APPDATA");
    return std::string(appData ? appData : ".") + "\\SEGA\\SonicOrigins\\NoSwap\\roster.json";
}

// The roster: every installed package's kind from the registry file (Roster.h), new keys numbered and the file
// written back (a new file, then swapped in); each entry logged with its package and S3&K data.
static void BuildRuntimeRoster() {
    static const char* const BASE_NAMES[] = {"sonic", "tails", "knuckles"};
    std::string path = RegistryPath();
    Registry loaded;
    bool haveFile = false;
    std::vector<std::string> notes;
    std::string text, why;
    if (ReadWholeFile(Widen(path), text)) {
        if (ParseRegistry(text, loaded, notes, why)) {
            haveFile = true;
        } else {
            std::string aside = path + ".unreadable";
            MoveFileExA(path.c_str(), aside.c_str(), MOVEFILE_REPLACE_EXISTING);
            Log("roster: %s can't be read (%s): set aside as %s; starting again from NoSwap's own 21 kinds",
                path.c_str(), why.c_str(), aside.c_str());
        }
    }
    for (auto& n : notes)
        Log("roster: %s: %s", path.c_str(), n.c_str());
    std::vector<std::string> installed;
    for (auto& p : g_packages)
        installed.push_back(p.key);
    RosterResult r = BuildRoster(haveFile ? &loaded : nullptr, installed);
    for (auto& l : r.log)
        Log("roster: %s", l.c_str());
    if (r.changed || !notes.empty()) {
        std::string dir = path.substr(0, path.find_last_of('\\'));
        CreateDirectoryA(dir.substr(0, dir.find_last_of('\\')).c_str(), nullptr);
        CreateDirectoryA(dir.c_str(), nullptr);
        std::string tmp = path + ".new", body = RegistryText(r.registry);
        FILE* f = fopen(tmp.c_str(), "wb");
        bool ok = f && fwrite(body.data(), 1, body.size(), f) == body.size();
        if (f)
            ok &= fclose(f) == 0;
        ok = ok && MoveFileExA(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING);
        Log("roster: %s %s (%u kinds)", path.c_str(), ok ? "written" : "NOT written (kinds this session only)",
            (unsigned)r.registry.kinds.size());
    }
    g_roster.clear();
    g_roster.reserve(r.offered.size());  // (g_rosterByKind points into it: no reallocation after)
    for (auto& [kind, key] : r.offered) {
        const Package* pkg = nullptr;
        for (auto& p : g_packages)
            if (p.key == key)
                pkg = &p;
        g_roster.push_back({kind, key, pkg->data.name, pkg->root, pkg->data});
    }
    memset(g_rosterByKind, 0, sizeof(g_rosterByKind));
    g_maxKind = FIRST_EXTRA_KIND - 1;
    int withData = 0;
    for (auto& e : g_roster) {
        g_rosterByKind[e.kind] = &e;
        g_maxKind = std::max(g_maxKind, e.kind);
        const ExtraData& d = e.data;
        Log("roster: kind %d -> %s -> %s", e.kind, e.key.c_str(), Narrow(e.root).c_str());
        if (!d.loaded) {
            Log("package data: kind %d %s: its noswap_character.json has no usable S3&K data, plays as Sonic in S3&K",
                e.kind, e.key.c_str());
            continue;
        }
        withData++;
        std::string moves;
        for (const ExtraField& f : EXTRA_FIELDS)
            if (f.type == FT_bool && *(const bool*)((const char*)&d.abilities + f.offset))
                moves += std::string(moves.empty() ? "" : " ") + f.name;
        Log("package data: kind %d %s: base %s, own colours %u, Blue Spheres colours %u, ability animations "
            "from %d%s%s; %s", e.kind, d.key.c_str(), BASE_NAMES[d.base], (unsigned)d.palette.size(),
            (unsigned)d.specialPalette.size(), d.animBase, d.roll ? ", own roll" : "", d.noRoll ? ", never rolls" : "",
            moves.empty() ? "no moves of its own" : moves.c_str());
    }
    for (auto& k : r.registry.kinds)
        if (!Offered(k.second))
            Log("roster: kind %d %s: reserved, not installed (not offered; its saves are kept)", k.second,
                k.first.c_str());
    Log("roster: %u characters offered, kinds %d-%d (%d with S3&K data); registry %u kinds, highest %d of %d", 
        (unsigned)g_roster.size(), g_roster.empty() ? 0 : g_roster.front().kind, g_maxKind, withData,
        (unsigned)r.registry.kinds.size(), r.registry.Highest(), KIND_LIMIT - 1);
}
// Every subfolder of <dir>\characters\ that holds a package
static void AddCharactersFolder(const std::wstring& dir) {
    std::wstring chars = dir;
    if (!chars.empty() && chars.back() != L'\\' && chars.back() != L'/')
        chars += L'\\';
    chars += L"characters\\";
    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW((chars + L"*").c_str(), &fd);
    if (h != INVALID_HANDLE_VALUE) {
        do
            if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && fd.cFileName[0] != L'.')
                AddPackage(chars + fd.cFileName);
        while (FindNextFileW(h, &fd));
        FindClose(h);
    }
}
// A folder's full path, backslashes, no trailing slash (to compare two folders)
static std::wstring FolderKey(const std::wstring& dir) {
    wchar_t full[1024];
    DWORD n = GetFullPathNameW(dir.c_str(), 1024, full, nullptr);
    std::wstring s = n && n < 1024 ? full : dir;
    for (auto& c : s)
        if (c == L'/')
            c = L'\\';
    while (!s.empty() && s.back() == L'\\')
        s.pop_back();
    return s;
}
static void FindPackages(ModInfo* modInfo) {
    std::wstring own = DllFolderW();
    AddCharactersFolder(own);
    // the enabled mods (ModList: a std::vector<Mod*>*, read as its begin / end pointers)
    if (modInfo && modInfo->ModList && Readable(modInfo->ModList, 2 * sizeof(void*))) {
        Mod** begin = ((Mod***)modInfo->ModList)[0];
        Mod** end = ((Mod***)modInfo->ModList)[1];
        for (Mod** m = begin; m && m < end && m < begin + 256; m++)
            if (Readable(m, sizeof(Mod*)) && *m && Readable(*m, sizeof(Mod)) && (*m)->Path) {
                std::wstring path = Widen((*m)->Path);
                AddPackage(path);
                // a pack mod (e.g. NoSwap-Extras): its characters\<folder>\ packages (NoSwap's own: done above)
                if (_wcsicmp(FolderKey(path).c_str(), FolderKey(own).c_str()) != 0)
                    AddCharactersFolder(path);
            }
    }
    Log("packages: %u found", (unsigned)g_packages.size());
    BuildRuntimeRoster();
}

// Make the package with this key active (nullptr / "": none)
static void SetActiveCharacter(const char* key, const char* why) {
    const Package* found = nullptr;
    for (auto& p : g_packages)
        if (key && p.key == key)
            found = &p;
    if (found != g_active)
        Log("active character: %s (%s)%s", key && *key ? key : "none", why,
            key && *key && !found ? ", no package installed: NoSwap's own files" : "");
    g_active = found;
}

// ---------------------------------------------------------------- own sounds in Sonic 1, Sonic 2 and Sonic CD
// Origins plays those games' sounds from its CRI banks, so a package's own sound (character.json "sounds") is played here,
// asked for through a mailbox (tools/own_sounds.py): one global variable no Origins script of that game uses (S1/S2
// game.callbackParam2, CD Leaderboard.Offset). The player script writes OWN_IDLE there at startup; while the active
// package lists own sounds ("own_sounds", in order), this finds that number in the game's memory (as FindCdShotGlobal)
// and answers OWN_READY when every listed file is there. A move's sound then sets bit k (0-7) of the READY value; this
// plays the package's sound k and clears the bit. Without the answer the script plays the move's game sound instead.
// Polled every 10 ms (ProbeThread); a search for an asking mailbox every 2 s (a new game's) while such a package is active.
constexpr int32_t OWN_IDLE = 0x4E534F00, OWN_READY = 0x4D520000;
static int32_t* FindExeInt(int32_t value) {
    HMODULE exe = GetModuleHandleA(nullptr);
    std::vector<int32_t> buf;
    MEMORY_BASIC_INFORMATION mbi{};
    for (char* at = (char*)exe; VirtualQuery(at, &mbi, sizeof(mbi)) && mbi.AllocationBase == exe;
         at = (char*)mbi.BaseAddress + mbi.RegionSize) {
        bool writable = mbi.State == MEM_COMMIT && !(mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
                        && (mbi.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE));
        if (!writable)
            continue;
        buf.resize(mbi.RegionSize / 4);
        if (!ReadMem(mbi.BaseAddress, buf.data(), buf.size() * 4))
            continue;
        for (size_t i = 0; i < buf.size(); i++)
            if (buf[i] == value)
                return (int32_t*)mbi.BaseAddress + i;
    }
    return nullptr;
}
static void OwnSoundMailbox() {
    static const Package* forPkg = nullptr;
    static bool ok = false;      // every listed file of forPkg is there
    static int32_t* box = nullptr;
    static DWORD lastSearch = 0;
    const Package* p = g_active;
    bool want = p && !p->data.ownSounds.empty();
    int32_t v = 0;
    if (p != forPkg) {  // another character: its own files, and the mailbox told again
        forPkg = p;
        ok = want;
        for (size_t k = 0; want && k < p->data.ownSounds.size(); k++)
            ok = ok && !p->data.ownSounds[k].empty() && !OwnSoundBytes(p->root, p->data.ownSounds[k].c_str()).empty();
        if (want)
            Log("own sounds (Sonic 1/2/CD): %s: %u listed, %s", p->key.c_str(), (unsigned)p->data.ownSounds.size(),
                ok ? "all there" : "one missing or unusable: the moves keep the games' sounds");
        if (box && ReadMem(box, &v, 4) && (v & 0xFFFF0000) == OWN_READY)
            InterlockedCompareExchange((volatile LONG*)box, ok ? OWN_READY : OWN_IDLE, v);
    }
    if (!want)
        return;
    if (box && ReadMem(box, &v, 4)) {
        if (v == OWN_IDLE && ok)
            InterlockedCompareExchange((volatile LONG*)box, OWN_READY, OWN_IDLE);
        else if ((v & 0xFFFF0000) == OWN_READY && (v & 0xFF)
                 && InterlockedCompareExchange((volatile LONG*)box, v & ~0xFF, v) == v)
            for (size_t k = 0; k < 8; k++)
                if ((v & (1 << k)) && k < p->data.ownSounds.size() && ok)
                    PlayOwnFrom(p->root, p->data.ownSounds[k].c_str());
    }
    if (GetTickCount() - lastSearch >= 2000) {
        lastSearch = GetTickCount();
        if (int32_t* found = FindExeInt(OWN_IDLE)) {
            if (found != box)
                Log("own sounds (Sonic 1/2/CD): mailbox at %p", (void*)found);
            box = found;
            if (ok)
                InterlockedCompareExchange((volatile LONG*)box, OWN_READY, OWN_IDLE);
        }
    }
}

// Files served by name whoever is active: NoSwap's path (relative to its folder, NormW form) -> the file served
// instead: the S3&K save screen's pictures (SetUpMenuPictures) and Origins' menu archives with the cards written in
// (SetUpMenuCards). Filled in SetUpPackages before the file hook goes in and never changed after, so the hook reads it
// without a lock.
static std::map<std::wstring, std::wstring> g_pathMap;
static std::vector<std::wstring> g_cardArchives;  // the menu archives with card slots (NormW, relative): another mod's
                                                  // mustn't win (g_watched)

// The S3&K save screen's pictures (extras.S3K_MENU_PICTURE). The data select shows several slots at once, each maybe
// a different extra, and the engine keeps a loaded sprite file and sheet under its name for the whole menu visit (so
// one name per slot would keep showing the first extra it held). So every extra whose package has a picture gets its
// own numbered name for this session, 3K_Players/MenuPicture<j>.bin / .gif (NoSwap ships placeholders for j below
// MENU_PICTURE_COUNT; the redirect only serves names NoSwap ships), fixed until the game closes: the .gif is served
// from the package, the .bin from a copy in NoSwap's cache folder with its sheet renamed to MenuPicture<j>.gif
// (RenameMenuSheet, ExtraData.h).
static void SetUpMenuPictures() {
    const std::wstring MENU = L"Sonic3ku\\Data\\Sprites\\3K_Players\\MenuPicture";
    std::wstring mod = DllFolderW() + L"\\";
    std::wstring cache = g_cacheDirW;
    for (int j = 0; j < MENU_PICTURE_COUNT; j++)  // an earlier session's, which may have been another extra's
        DeleteFileW((cache + L"MenuPicture" + std::to_wstring(j) + L".bin").c_str());
    int next = 0;
    for (auto& e : g_roster) {
        std::string in, out, why;
        std::wstring gif = e.root + MENU + L".gif";
        if (!ReadWholeFile(e.root + MENU + L".bin", in) || GetFileAttributesW(gif.c_str()) == INVALID_FILE_ATTRIBUTES) {
            Log("save screen picture: kind %d %s: its package has none (the menu shows its base there)", e.kind,
                e.key.c_str());
            continue;
        }
        if (next >= MENU_PICTURE_COUNT) {
            Log("save screen picture: kind %d %s: NoSwap ships only %d picture names, all taken", e.kind, e.key.c_str(),
                MENU_PICTURE_COUNT);
            continue;
        }
        char sheet[64];
        snprintf(sheet, sizeof(sheet), "3K_Players/MenuPicture%d.gif", next);
        if (!RenameMenuSheet(in, sheet, out, why)) {
            Log("save screen picture: kind %d %s: its MenuPicture.bin is unusable (%s)", e.kind, e.key.c_str(),
                why.c_str());
            continue;
        }
        std::wstring j = std::to_wstring(next), cached = cache + L"MenuPicture" + j + L".bin";
        FILE* f = _wfopen(cached.c_str(), L"wb");
        bool written = f && fwrite(out.data(), 1, out.size(), f) == out.size();
        if (f)
            written &= fclose(f) == 0;
        std::string back;
        if (!written || !ReadWholeFile(cached, back) || back != out) {  // (self-check: the copy reads back the same)
            Log("save screen picture: kind %d %s: writing %s failed", e.kind, e.key.c_str(), Narrow(cached).c_str());
            continue;
        }
        bool shipped = GetFileAttributesW((mod + MENU + j + L".bin").c_str()) != INVALID_FILE_ATTRIBUTES
                       && GetFileAttributesW((mod + MENU + j + L".gif").c_str()) != INVALID_FILE_ATTRIBUTES;
        g_pathMap[NormW(MENU + j + L".bin")] = cached;
        g_pathMap[NormW(MENU + j + L".gif")] = gif;
        g_menuPicture[e.kind] = next + 1;
        Log("save screen picture: kind %d %s -> 3K_Players/MenuPicture%d.bin / .gif (%u bytes, sheet %s)%s", e.kind,
            e.key.c_str(), next, (unsigned)out.size(), sheet,
            shipped ? "" : ", but NoSwap's placeholder for that name is missing: it won't be served");
        next++;
    }
    Log("save screen pictures: %d of %u extras have theirs from their packages", next, (unsigned)g_roster.size());
}

// Origins' select cards (docs/plan-b-modular-characters.md, phase B; MenuCards.h). NoSwap's menu archives
// (raw/ui/ui_gamestage.pac and ui_mainmenu.pac: pictures; raw/text/text_menu_*.pac: names) have generic card slots, and
// ship with the first 21 characters' cards written in (slot = kind - 6). At startup each offered character gets a slot
// (AssignCardSlots) and each archive is rewritten IN PLACE in NoSwap's own folder with every slot rewritten: the
// character's picture (its package's ui/card_picture.dds) and name, or blank (MenuCardFiles.h FillCardsInPlace: checked
// against the descriptor first, written to a temporary file beside it and moved over, nothing written when it already
// holds every slot). The mod loader serves them like any other NoSwap file. (Until 1.0.1 they were only copied to the
// cache folder and served by the file hook, which on native Windows never saw the game open them: blank cards.) Only
// when an archive can't be written in place is it copied to NoSwap's cache folder with the same writes and served from
// there (g_pathMap); a copy is only rewritten when its source or its cards changed (a stamp file beside it). If that
// fails too, every extra keeps what NoSwap's own archives give it.
static std::string ReadAll(const std::wstring& path, bool& ok) {  // (ReadWholeFile stops at 1 MB)
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
// (FileSizeAndTime, WritesInFile: MenuCardFiles.h)
// One archive: its cached copy with the writes, made (or found up to date). -> the copy's path, "" on failure (logged).
static std::wstring CardArchiveCopy(const CardArchive& ar, const std::vector<CardWrite>& writes, const std::wstring& mod,
                                    const std::wstring& cache) {
    std::wstring rel = Widen(ar.path), flat = rel;
    for (auto& c : rel)
        if (c == L'/')
            c = L'\\';
    for (auto& c : flat)
        if (c == L'/' || c == L'\\')
            c = L'_';
    std::wstring src = mod + rel, cached = cache + L"menu_" + flat, stampPath = cached + L".stamp";
    const char* name = ar.path.c_str();
    uint64_t size, time;
    if (!FileSizeAndTime(src, size, time)) {
        Log("menu cards: %s: NoSwap's own file isn't there", name);
        return L"";
    }
    uint64_t h = CardHash(CARD_HASH_START, &size, 8);
    h = CardHash(h, &time, 8);
    for (auto& w : writes) {
        uint64_t n = w.bytes.size();
        h = CardHash(CardHash(CardHash(h, &w.at, 8), &n, 8), w.bytes.data(), w.bytes.size());
    }
    char stamp[64];
    snprintf(stamp, sizeof(stamp), "noswap menu cards 1 %016llx\n", (unsigned long long)h);
    bool ok;
    uint64_t csize, ctime;
    if (ReadAll(stampPath, ok) == stamp && ok && FileSizeAndTime(cached, csize, ctime) && csize == size) {
        FILE* f = _wfopen(cached.c_str(), L"rb");
        bool same = f && WritesInFile(f, writes);
        if (f)
            fclose(f);
        if (same) {
            Log("menu cards: %s: the cached copy is up to date", name);
            return cached;
        }
    }
    DeleteFileW(stampPath.c_str());
    std::string why;
    if (!CardPatchCopy(ar, writes, src, cached, why)) {
        Log("menu cards: %s: %s", name, why.c_str());
        return L"";
    }
    std::wstring stampTmp = stampPath + L".new";
    FILE* s = _wfopen(stampTmp.c_str(), L"wb");
    bool stamped = s && fwrite(stamp, 1, strlen(stamp), s) == strlen(stamp);
    if (s)
        stamped = (fclose(s) == 0) && stamped;
    if (!stamped || !MoveFileExW(stampTmp.c_str(), stampPath.c_str(), MOVEFILE_REPLACE_EXISTING))
        DeleteFileW(stampTmp.c_str());  // (no stamp: rewritten next time, nothing worse)
    Log("menu cards: %s: written to %s (%u writes)", name, Narrow(cached).c_str(), (unsigned)writes.size());
    return cached;
}
static void SetUpMenuCards() {
    std::wstring mod = DllFolderW() + L"\\", cache = g_cacheDirW;
    // the main menu's CONTINUE bubble heads: shipped when the descriptor has them and every language's main menu scene
    // (with the head crops) is NoSwap's, as built (Hook_IconChara sets those crops only then)
    int headCrop = 0;
    auto fallback = [&headCrop](const char* why) {
        Log("menu cards: %s: NoSwap's own menu archives are served (the first 21 characters' cards as shipped; any other "
            "shows its base's picture and no name)", why);
        // (a release ships every card slot blank: the copies made here are the only cards there are)
        Warn("The character select cards couldn't be prepared (%s), so the extra characters' cards are empty.", why);
        for (auto& e : g_roster)
            if (LegacyKind(e.key) == e.kind) {
                e.cardSlot = e.kind - FIRST_EXTRA_KIND + 1;
                e.cardPicture = true;
                e.cardTwoLines = e.name.find(' ') != std::string::npos;
                e.headPicture = headCrop != 0;  // (shipped with their heads too)
                e.cardCredit = !g_creditCast.empty();  // (and their credits, when the descriptor has them)
            } else {
                e.cardSlot = 0, e.cardPicture = e.cardTwoLines = e.headPicture = e.cardCredit = false;
            }
        g_headFirstCrop = headCrop;
    };
    std::string text, why;
    CardLayout layout;
    bool ok;
    text = ReadAll(mod + L"raw\\ui\\noswap_cards.json", ok);
    if (!ok) {
        fallback("no raw/ui/noswap_cards.json (build tools/build_origins_menu.py)");
        return;
    }
    if (!ParseCardLayout(text, layout, why)) {
        fallback(("raw/ui/noswap_cards.json unusable (" + why + ")").c_str());
        return;
    }
    // the sprite credit box (descriptor version 3): its text keys are in the text archives as built
    g_creditCast = layout.creditUnits ? layout.creditCast : "";
    Log("menu cards: sprite credits %s", g_creditCast.empty() ? "off (the descriptor has none)"
                                                                : ("on (box " + g_creditCast + ")").c_str());
    if (layout.headW) {
        bool cells = false, scenes = !layout.headScenes.empty();
        for (const CardArchive& ar : layout.archives)
            cells |= !ar.headCells.empty();
        for (const CardScene& sc : layout.headScenes) {
            std::wstring path = mod + Widen(sc.path);
            for (auto& ch : path)
                if (ch == L'/')
                    ch = L'\\';
            uint64_t size, time;
            if (!FileSizeAndTime(path, size, time) || size != sc.size) {
                Log("menu cards: CONTINUE bubble heads off: %s isn't NoSwap's as built", sc.path.c_str());
                scenes = false;
            }
        }
        headCrop = cells && scenes ? layout.headFirstCrop : 0;
        Log("menu cards: CONTINUE bubble heads %s (%u languages' main menu scenes, head crops from %d)",
            headCrop ? "on" : "off", (unsigned)layout.headScenes.size(), layout.headFirstCrop);
    } else {
        Log("menu cards: raw/ui/noswap_cards.json has no CONTINUE bubble heads: extras' bubbles show Sonic's head");
    }
    std::vector<int> kinds;
    for (auto& e : g_roster)
        kinds.push_back(e.kind);
    std::map<int, int> slots = AssignCardSlots(kinds, layout.slots);
    std::vector<Card> cards(layout.slots);
    int pictures = 0, placed = 0;
    for (auto& e : g_roster) {
        e.cardSlot = slots[e.kind];
        e.cardPicture = e.cardTwoLines = false;
        if (!e.cardSlot) {
            Log("menu cards: kind %d %s: all %d card slots are taken: its base's picture, no name", e.kind, e.key.c_str(),
                layout.slots);
            continue;
        }
        placed++;
        Card& c = cards[e.cardSlot - 1];
        c.used = true;
        std::string note, dds, pwhy;
        CardNameLines(e.name, layout.nameUnits, c.lines, note);
        e.cardTwoLines = !c.lines[1].empty();
        e.cardCredit = false;
        if (layout.creditUnits && !e.data.creditShort.empty()) {
            bool cut, bad;
            c.credit = CardUtf16(e.data.creditShort, layout.creditUnits, cut, bad);
            e.cardCredit = true;
            if (cut || bad)
                note += std::string(note.empty() ? "" : "; ") + "credit " + (cut ? "cut short" : "isn't all UTF-8");
        }
        std::wstring pic = e.root + Widen(layout.picture);
        for (auto& ch : pic)
            if (ch == L'/')
                ch = L'\\';
        dds = ReadAll(pic, ok);
        if (!ok)
            pwhy = "its package has no " + layout.picture;
        else if (ReadCardPicture(dds, layout, c.picture, pwhy))
            e.cardPicture = true, pictures++;
        std::string hwhy = "none in this build";
        e.headPicture = false;
        if (layout.headW) {
            std::wstring head = e.root + Widen(layout.headPicture);
            for (auto& ch : head)
                if (ch == L'/')
                    ch = L'\\';
            dds = ReadAll(head, ok);
            if (!ok)
                hwhy = "its package has no " + layout.headPicture;
            else if (ReadCardPicture(dds, layout, c.head, hwhy, true))
                e.headPicture = true;
        }
        Log("menu cards: kind %d %s -> slot %d, name \"%s\", credit \"%s\"%s%s, %s%s, %s%s", e.kind, e.key.c_str(),
            e.cardSlot, e.name.c_str(), e.data.creditShort.c_str(), note.empty() ? "" : " (",
            note.empty() ? "" : (note + ")").c_str(),
            e.cardPicture ? "its picture " : "its base's picture: ",
            e.cardPicture ? (std::to_string(c.picture.w) + "x" + std::to_string(c.picture.h)).c_str() : pwhy.c_str(),
            e.headPicture ? "its head " : "Sonic's head: ",
            e.headPicture ? (std::to_string(c.head.w) + "x" + std::to_string(c.head.h)).c_str() : hwhy.c_str());
    }
    std::vector<std::vector<CardWrite>> planned(layout.archives.size());  // (every archive planned before any is written)
    for (size_t i = 0; i < layout.archives.size(); i++)
        if (!PlanCardWrites(layout, layout.archives[i], cards, planned[i], why)) {
            fallback(why.c_str());
            return;
        }
    // Each archive filled in place in NoSwap's own folder, which the mod loader serves (MenuCardFiles.h: on native
    // Windows the file hook never sees the game open them); a copy in the cache, served by the file hook, only when that
    // fails (a read-only mod folder)
    std::vector<std::pair<std::wstring, std::wstring>> served;
    std::vector<std::string> notInPlace;
    int filled = 0, same = 0;
    for (size_t i = 0; i < layout.archives.size(); i++) {
        const CardArchive& ar = layout.archives[i];
        const std::vector<CardWrite>& writes = planned[i];
        std::wstring own = mod + Widen(ar.path);
        for (auto& ch : own)
            if (ch == L'/')
                ch = L'\\';
        g_cardArchives.push_back(NormW(Widen(ar.path)));
        std::string fwhy;
        switch (FillCardsInPlace(ar, writes, own, fwhy)) {
        case CARD_FILL_WRITTEN:
            Log("menu cards: filled in place: %s (%u writes)", ar.path.c_str(), (unsigned)writes.size());
            filled++;
            continue;
        case CARD_FILL_SAME:
            Log("menu cards: filled in place: %s (already up to date, nothing written)", ar.path.c_str());
            same++;
            continue;
        case CARD_FILL_FAILED:
            break;
        }
        Log("menu cards: %s: can't be filled in place (%s): a copy in the cache instead", ar.path.c_str(), fwhy.c_str());
        notInPlace.push_back(ar.path);
        std::wstring copy = CardArchiveCopy(ar, writes, mod, cache);
        if (copy.empty()) {
            fallback((ar.path + " couldn't be written").c_str());
            return;
        }
        served.push_back({NormW(Widen(ar.path)), copy});
    }
    for (auto& [rel, copy] : served)
        g_pathMap[rel] = copy;
    g_headFirstCrop = headCrop;
    Log("menu cards: %d of %u offered characters have a card slot (%d with their own picture); %d archives filled in "
        "place (%d already up to date), %u served from the cache", placed, (unsigned)g_roster.size(), pictures,
        filled + same, same, (unsigned)served.size());
    if (!notInPlace.empty())
        Warn("NoSwap couldn't write its menu archives in its own mod folder (%s%s; see NoSwapS3K.log): it serves copies "
             "from %s instead, which may not reach the game on Windows, so the extra characters' cards may be empty. "
             "Make the mod folder writable (e.g. not read-only, not blocked by antivirus) and start the game again.",
             notInPlace[0].c_str(), notInPlace.size() > 1 ? (" and " + std::to_string(notInPlace.size() - 1) + " more").c_str() : "",
             Narrow(cache).c_str());
}

// A package script naming the active extra's kind (ACTIVE_KIND_TOKEN, Roster.h SubstituteActiveKind; docs/plan-b-
// modular-characters.md "Special stage retry") is served as a copy in NoSwap's cache folder with the kind written in:
// cache\kind<k>_<its path, '\' -> '_'>, rewritten (to a temporary name, then moved over) only when its content would
// change. Only .txt files are looked at, only the active package's, and only when the game opens one.
enum ActiveKindResult { AK_PLAIN, AK_SERVED, AK_FAILED };
static ActiveKindResult ActiveKindCopy(const Package* active, const std::wstring& rel, const std::wstring& file,
                                       std::wstring& served) {
    size_t dot = rel.find_last_of(L'.');
    if (dot == std::wstring::npos || NormW(rel.substr(dot)) != L".txt")
        return AK_PLAIN;
    std::string in, out;
    if (!ReadWholeFile(file, in))
        return AK_PLAIN;  // (the game's own open reports it)
    int kind = KindOfKey(active->key), count = 0;
    bool ok = SubstituteActiveKind(in, kind, out, count);
    if (count == 0 && ok)
        return AK_PLAIN;
    static int logged = 0;
    bool log = logged++ < 500;
    if (!ok || in.size() >= (1u << 20)) {  // (ReadWholeFile stops at 1 MB)
        if (log)
            Log("package %s: %s names %s, but %s: NoSwap's own file served instead", active->key.c_str(),
                Narrow(rel).c_str(), ACTIVE_KIND_TOKEN, !ok ? "the character has no kind" : "it's too big to rewrite");
        return AK_FAILED;
    }
    std::wstring flat = rel;
    for (auto& c : flat)
        if (c == L'\\' || c == L'/')
            c = L'_';
    std::wstring cached = g_cacheDirW + L"kind" + std::to_wstring(kind) + L"_" + flat;
    std::string have;
    bool written = false;
    if (!ReadWholeFile(cached, have) || have != out) {
        // (the folder may have gone since startup: a deploy while the game ran deleted it, and Blaze's special stage
        // fell back to NoSwap's own script, as Sonic)
        CreateDirectoryW(g_cacheDirW.substr(0, g_cacheDirW.find_last_not_of(L"\\/") + 1).c_str(), nullptr);
        std::wstring tmp = cached + L"." + std::to_wstring(GetCurrentThreadId()) + L".new";
        FILE* f = _wfopen(tmp.c_str(), L"wb");
        bool good = f && fwrite(out.data(), 1, out.size(), f) == out.size();
        if (f)
            good &= fclose(f) == 0;
        good = good && MoveFileExW(tmp.c_str(), cached.c_str(), MOVEFILE_REPLACE_EXISTING);
        if (!good)
            DeleteFileW(tmp.c_str());
        if (!good || !ReadWholeFile(cached, have) || have != out) {  // (self-check: the copy reads back the same)
            if (log)
                Log("package %s: writing %s for %s failed: NoSwap's own file served instead", active->key.c_str(),
                    Narrow(cached).c_str(), Narrow(rel).c_str());
            return AK_FAILED;
        }
        written = true;
    }
    if (log)
        Log("package %s: served %s with kind %d (%d x %s, %s %s)", active->key.c_str(), Narrow(rel).c_str(), kind,
            count, ACTIVE_KIND_TOKEN, written ? "written to" : "already in", Narrow(cached).c_str());
    served = cached;
    return AK_SERVED;
}

typedef HANDLE(WINAPI* CreateFileWFn)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef HANDLE(WINAPI* CreateFileAFn)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
static CreateFileWFn g_createFileW = nullptr;
static CreateFileAFn g_createFileA = nullptr;

// What the game should open instead of `name` (nullptr: `name` itself). `api` names the hooked function, for the log.
static const wchar_t* RedirectName(const wchar_t* name, DWORD access, std::wstring& buf, const char* api) {
    const Package* active = g_active;
    if (!(active || !g_pathMap.empty()) || !name || (access & GENERIC_WRITE))
        return nullptr;
    std::wstring n = NormW(name);
    size_t at = n.find(g_modDirW);
    if (at == std::wstring::npos)
        return nullptr;
    std::wstring rel = std::wstring(name).substr(at + g_modDirW.size());
    while (!rel.empty() && (rel[0] == L'.' || rel[0] == L'\\' || rel[0] == L'/'))
        rel.erase(0, 1);  // (".\\Sonic1u\\..." as the game asks)
    static volatile LONG seenA = 0, seenW = 0;  // (which function the game opens NoSwap's files with: Windows' own
    if (InterlockedIncrement(api[0] == 'A' ? &seenA : &seenW) <= 3)  // CreateFileA doesn't go through CreateFileW)
        Log("file hook: the game opens %s through CreateFile%s", Narrow(rel).c_str(), api);
    auto mapped = g_pathMap.find(NormW(rel));
    if (mapped != g_pathMap.end()) {  // (served whoever is active)
        static int logged = 0;
        if (logged++ < 200)
            Log("served %s <- %s", Narrow(rel).c_str(), Narrow(mapped->second).c_str());
        return mapped->second.c_str();
    }
    if (!active)
        return nullptr;
    std::wstring alt = active->root + rel;
    if (GetFileAttributesW(alt.c_str()) == INVALID_FILE_ATTRIBUTES)
        return nullptr;
    std::wstring served;
    switch (ActiveKindCopy(active, rel, alt, served)) {
    case AK_SERVED:
        buf = served;
        return buf.c_str();
    case AK_FAILED:  // (never the word itself: the script wouldn't compile)
        return nullptr;
    case AK_PLAIN:
        break;
    }
    static int logged = 0;
    if (logged++ < 200)
        Log("package %s: %s", active->key.c_str(), Narrow(rel).c_str());
    buf = alt;
    return buf.c_str();
}

// Another mod's copy of a file NoSwap needs to win (its menu archives, its player scripts): opened from another folder of
// the mods folder, the extras get empty cards or play as Sonic. Reported once (the log and the message box).
static std::vector<std::wstring> g_watched;        // NormW paths relative to a mod folder (SetUpPackages)
static std::vector<std::wstring> g_packageRootsN;  // the packages' folders, NormW without the drive (the DLL reads them)
static volatile LONG g_conflictReported = 0;
static void CheckConflict(const wchar_t* name) {
    if (g_conflictReported || g_watched.empty() || g_modsRootW.empty() || !name)
        return;
    std::wstring n = NormW(name);
    size_t r = n.find(g_modsRootW);
    if (r == std::wstring::npos || n.find(g_modDirW) != std::wstring::npos)
        return;
    for (auto& root : g_packageRootsN)
        if (n.find(root) != std::wstring::npos)
            return;
    for (auto& w : g_watched)
        if (n.size() > w.size() && n.compare(n.size() - w.size(), w.size(), w) == 0 && n[n.size() - w.size() - 1] == L'\\') {
            if (InterlockedExchange(&g_conflictReported, 1))
                return;
            std::wstring other = n.substr(r + g_modsRootW.size());
            other = other.substr(0, other.find(L'\\'));
            bool ultrafix = other.find(L"ultrafix") != std::wstring::npos;
            Warn("The game loaded %s from the mod folder \"%s\", not NoSwap's: that mod is above NoSwap in "
                 "HedgeModManager, so the extras show empty cards and play as Sonic. %s",
                 Narrow(w).c_str(), Narrow(other).c_str(),
                 ultrafix ? "NoSwap isn't compatible with Sonic Origins Ultrafix yet: disable Ultrafix to play NoSwap."
                          : "Move NoSwap above it, or disable it.");
            ShowWarnings();
            return;
        }
}

static HANDLE WINAPI Hook_CreateFileW(LPCWSTR name, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                      DWORD flags, HANDLE tmpl) {
    std::wstring buf;
    if (const wchar_t* to = RedirectName(name, access, buf, "W"))
        return g_createFileW(to, access, share, sa, disp, flags, tmpl);
    HANDLE h = g_createFileW(name, access, share, sa, disp, flags, tmpl);
    if (h != INVALID_HANDLE_VALUE && !g_conflictReported && !(access & GENERIC_WRITE)) {
        DWORD error = GetLastError();  // (kept for the caller: OPEN_ALWAYS sets it on success)
        CheckConflict(name);
        SetLastError(error);
    }
    return h;
}
// Windows' own CreateFileA (since Windows 8) converts the name and opens the file without going through CreateFileW
// (Wine's calls CreateFileW), so a game opening NoSwap's files this way bypassed the hook above on Windows only
static HANDLE WINAPI Hook_CreateFileA(LPCSTR name, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                      DWORD flags, HANDLE tmpl) {
    if (name && !(access & GENERIC_WRITE)) {
        UINT cp = AreFileApisANSI() ? CP_ACP : CP_OEMCP;
        int len = MultiByteToWideChar(cp, 0, name, -1, nullptr, 0);
        if (len > 0) {
            std::wstring w(len, L'\0');
            MultiByteToWideChar(cp, 0, name, -1, &w[0], len);
            w.resize(len - 1);
            std::wstring buf;
            if (const wchar_t* to = RedirectName(w.c_str(), access, buf, "A"))
                return g_createFileW(to, access, share, sa, disp, flags, tmpl);
            HANDLE h = g_createFileA(name, access, share, sa, disp, flags, tmpl);
            if (h != INVALID_HANDLE_VALUE && !g_conflictReported) {
                DWORD error = GetLastError();
                CheckConflict(w.c_str());
                SetLastError(error);
            }
            return h;
        }
    }
    return g_createFileA(name, access, share, sa, disp, flags, tmpl);
}

// A folder (with a trailing backslash) a file can be made in
static bool CanWriteIn(const std::wstring& dir) {
    CreateDirectoryW(dir.substr(0, dir.size() - 1).c_str(), nullptr);  // (already there: fine)
    HANDLE h = CreateFileW((dir + L"noswap_write_test.tmp").c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                           FILE_ATTRIBUTE_TEMPORARY | FILE_FLAG_DELETE_ON_CLOSE, nullptr);
    if (h == INVALID_HANDLE_VALUE)
        return false;
    CloseHandle(h);
    return true;
}

// The enabled mods (ModList: a std::vector<Mod*>*, read as its begin / end pointers, as FindPackages)
template <typename Fn> static void ForEachMod(ModInfo* modInfo, Fn fn) {
    if (!modInfo || !modInfo->ModList || !Readable(modInfo->ModList, 2 * sizeof(void*)))
        return;
    Mod** begin = ((Mod***)modInfo->ModList)[0];
    Mod** end = ((Mod***)modInfo->ModList)[1];
    for (Mod** m = begin; m && m < end && m < begin + 256; m++)
        if (Readable(m, sizeof(Mod*)) && *m && Readable(*m, sizeof(Mod)) && (*m)->Path)
            fn(**m);
}

// At startup: every other enabled mod (not NoSwap, not a package) with one of the watched files in its include folders
// (its mod.ini). Which one wins depends on the order in HedgeModManager, so only Ultrafix (which conflicts either way:
// memory notes, its scripts and NoSwap's don't mix) is a warning here; CheckConflict reports any that actually wins.
static void FindConflictingMods(ModInfo* modInfo) {
    std::wstring own = FolderKey(DllFolderW());
    ForEachMod(modInfo, [&](const Mod& mod) {
        std::wstring dir = FolderKey(Widen(mod.Path));
        if (_wcsicmp(dir.c_str(), own.c_str()) == 0)
            return;
        std::wstring dirN = NormW(dir) + L"\\";
        for (auto& p : g_packages)  // (a package, or a pack of them)
            if (NormW(p.root).find(dirN) == 0)
                return;
        std::wstring ini = dir + L"\\mod.ini";
        int count = GetPrivateProfileIntW(L"Main", L"IncludeDirCount", 0, ini.c_str());
        std::vector<std::string> found;
        for (int i = 0; i < count && i < 64; i++) {
            wchar_t buf[512] = {};
            GetPrivateProfileStringW(L"Main", (L"IncludeDir" + std::to_wstring(i)).c_str(), L"", buf, 512, ini.c_str());
            std::wstring inc = buf;  // (".\\ModConfig\\MenuChars\\s1\\": no doubled separators)
            while (!inc.empty() && (inc.back() == L'\\' || inc.back() == L'/'))
                inc.pop_back();
            std::wstring base = inc.empty() || inc == L"." ? dir + L"\\" : dir + L"\\" + inc + L"\\";
            for (auto& w : g_watched)
                if (GetFileAttributesW((base + w).c_str()) != INVALID_FILE_ATTRIBUTES) {
                    std::string f = Narrow(w);
                    if (std::find(found.begin(), found.end(), f) == found.end())
                        found.push_back(f);
                }
        }
        if (found.empty())
            return;
        std::string name = mod.Name ? mod.Name : Narrow(dir);
        std::string lower = name + " " + Narrow(dir);
        for (auto& c : lower)
            c = (char)tolower((unsigned char)c);
        std::string list;
        for (size_t i = 0; i < found.size() && i < 3; i++)
            list += (i ? ", " : "") + found[i];
        if (found.size() > 3)
            list += " and " + std::to_string(found.size() - 3) + " more";
        if (lower.find("ultrafix") != std::string::npos)
            Warn("Sonic Origins Ultrafix is enabled (\"%s\"). NoSwap isn't compatible with it yet: its menu archives and "
                 "player scripts replace NoSwap's (%s), so the extras show empty cards and play as Sonic, or the game "
                 "stops with a script error. Disable Ultrafix to play NoSwap.", name.c_str(), list.c_str());
        else
            Log("packages: the enabled mod \"%s\" also has %s: if it's above NoSwap in HedgeModManager, its files win "
                "and the extras show empty cards or play as Sonic", name.c_str(), list.c_str());
    });
}

static void SetUpPackages(ModInfo* modInfo) {
    if (!modInfo || !modInfo->CurrentMod) {
        Log("packages: no mod info");
        Warn("The mod loader gave NoSwap no information about its own folder (an old or unusual HedgeModManager / "
             "HiteModLoader?), so no characters were loaded.");
        return;
    }
    g_modDirW = NormW(Widen(modInfo->CurrentMod->Path));
    if (!g_modDirW.empty() && g_modDirW.back() != L'\\')
        g_modDirW += L'\\';
    size_t colon = g_modDirW.find(L':');  // "Z:/var/..." -> the part after the drive, whatever form the game uses
    if (colon != std::wstring::npos)
        g_modDirW = g_modDirW.substr(colon + 1);
    size_t up = g_modDirW.find_last_of(L'\\', g_modDirW.size() >= 2 ? g_modDirW.size() - 2 : 0);
    g_modsRootW = up != std::wstring::npos && up > 2 ? g_modDirW.substr(0, up + 1) : L"";  // (too short: not checked)
    Log("packages: NoSwap's folder as the game names it: ...%s (mods folder ...%s)", Narrow(g_modDirW).c_str(),
        Narrow(g_modsRootW).c_str());
    FindPackages(modInfo);
    if (g_packages.empty()) {
        Warn("No NoSwap characters were found. Enable the character mods (\"NoSwap: <name>\") in HedgeModManager next "
             "to NoSwap, or install the all-in-one download.");
        return;  // (no hook needed)
    }
    for (auto& p : g_packages) {
        std::wstring r = NormW(p.root);
        size_t c = r.find(L':');
        g_packageRootsN.push_back(c != std::wstring::npos ? r.substr(c + 1) : r);
    }
    g_cacheDirW = DllFolderW() + L"\\cache\\";
    if (!CanWriteIn(g_cacheDirW)) {
        DWORD error = GetLastError();
        std::wstring local = LocalNoSwapDir();
        std::wstring alt = local.empty() ? L"" : local + L"\\cache\\";
        if (!alt.empty() && CanWriteIn(alt)) {
            Log("packages: NoSwap's folder can't be written (error %lu): its cache is %s instead", error,
                Narrow(alt).c_str());
            g_cacheDirW = alt;
        } else {
            Warn("Neither NoSwap's mod folder nor %%LOCALAPPDATA%%\\NoSwap can be written (error %lu): a read-only "
                 "folder, a full disk, or antivirus blocking it.", error);
        }
    }
    WIN32_FIND_DATAW fd;  // an earlier session's scripts with a kind written in (ActiveKindCopy)
    HANDLE old = FindFirstFileW((g_cacheDirW + L"kind*_*").c_str(), &fd);
    if (old != INVALID_HANDLE_VALUE) {
        do
            DeleteFileW((g_cacheDirW + fd.cFileName).c_str());
        while (FindNextFileW(old, &fd));
        FindClose(old);
    }
    SetUpMenuPictures();  // (before the hook goes in: g_pathMap never changes after)
    SetUpMenuCards();
    // the files another mod mustn't win: the menu archives (with the cards) and the player scripts
    for (const wchar_t* w : {L"raw\\ui\\ui_gamestage.pac", L"raw\\ui\\ui_mainmenu.pac",
                             L"sonic1u\\data\\scripts\\players\\playerobject.txt",
                             L"sonic2u\\data\\scripts\\players\\playerobject.txt",
                             L"soniccdu\\data\\scripts\\players\\playerobject.txt"})
        g_watched.push_back(w);
    for (auto& [rel, copy] : g_pathMap)
        if (rel.compare(0, 4, L"raw\\") == 0 && std::find(g_watched.begin(), g_watched.end(), rel) == g_watched.end())
            g_watched.push_back(rel);
    for (auto& rel : g_cardArchives)  // (filled in place: not in g_pathMap)
        if (std::find(g_watched.begin(), g_watched.end(), rel) == g_watched.end())
            g_watched.push_back(rel);
    FindConflictingMods(modInfo);
    MH_STATUS mh = MH_Initialize();
    HMODULE kb = GetModuleHandleA("kernelbase.dll"), k32 = GetModuleHandleA("kernel32.dll");
    void* target = kb ? (void*)GetProcAddress(kb, "CreateFileW") : nullptr;
    if (!target)
        target = (void*)GetProcAddress(k32, "CreateFileW");
    bool ok = (mh == MH_OK || mh == MH_ERROR_ALREADY_INITIALIZED) && target
              && MH_CreateHook(target, (void*)Hook_CreateFileW, (void**)&g_createFileW) == MH_OK
              && MH_EnableHook(target) == MH_OK;
    Log("packages: file hook %s", ok ? "in" : "FAILED");
    if (!ok) {
        Warn("NoSwap couldn't hook the game's file loading (MinHook %d), so the extras' cards and files can't be "
             "served: they show empty cards and play as Sonic.", (int)mh);
        return;
    }
    void* targetA = kb ? (void*)GetProcAddress(kb, "CreateFileA") : nullptr;
    if (!targetA)
        targetA = (void*)GetProcAddress(k32, "CreateFileA");
    bool okA = targetA && MH_CreateHook(targetA, (void*)Hook_CreateFileA, (void**)&g_createFileA) == MH_OK
               && MH_EnableHook(targetA) == MH_OK;
    Log("packages: file hook (CreateFileA) %s", okA ? "in" : "FAILED (files opened that way aren't served)");
}

// (The SONIC MANIA button in the main menu is its own mod since 2026-10-01: Mania Lock-On, native/lockon/. NoSwap's
// menu archives still carry its layout patterns and text, tools/build_origins_menu.py LAUNCHER_*; NoSwap hooks none of
// its functions.)

static void InitAll(ModInfo* modInfo);
extern "C" __declspec(dllexport) void Init(ModInfo* modInfo) {
    g_warnBoxOn = GetPrivateProfileIntW(L"Debug", L"Warnings", 1, (DllFolderW() + L"\\NoSwapS3K.ini").c_str()) != 0;
    InitAll(modInfo);
    ShowWarnings();  // (nothing when nothing failed)
}
static void InitAll(ModInfo* modInfo) {
    Log("NoSwapS3K loaded (mod folder: %s)", modInfo && modInfo->CurrentMod ? modInfo->CurrentMod->Path : "?");
    SetUpPackages(modInfo);
    ReadSettings();
    g_blinkOffset = GetPrivateProfileIntA("Debug", "BlinkOffset", BLINK_OFFSET_DEFAULT, IniPath().c_str());
    if (g_blinkOffset >= 0)
        Log("blink timer at +0x%X", g_blinkOffset);
    CreateThread(nullptr, 0, ProbeThread, nullptr, 0, nullptr);
    if (int n = GetPrivateProfileIntA("Debug", "MenuTest", 0, IniPath().c_str()))
        MenuTest(n);
    if (GetPrivateProfileIntA("Menu", "RealKinds", 1, IniPath().c_str()))
        SetUpRealKinds();

    void* link = SigScan(SIG_LINK_GAME_LOGIC, MASK_LINK_GAME_LOGIC);
    g_playerStateAir = SigScan(SIG_PLAYER_STATE_AIR, MASK_PLAYER_STATE_AIR);
    Log("signatures: LinkGameLogicDLL %p, Player_State_Air %p", link, g_playerStateAir);
    StateGateSetUp();
    if (!link) {
        Warn("Sonic 3 & Knuckles' game code wasn't found (another game version, or another mod, e.g. Ultrafix, hooked "
             "it first): extras in Sonic 3 & Knuckles play as Sonic.");
        return;
    }
    MH_STATUS mh = MH_Initialize();  // already done if the character select hooks went in first
    if (mh != MH_OK && mh != MH_ERROR_ALREADY_INITIALIZED) {
        Log("MinHook failed to initialise");
        Warn("MinHook couldn't start (%d): extras in Sonic 3 & Knuckles play as Sonic.", (int)mh);
        return;
    }
    if (MH_CreateHook(link, (void*)Hook_LinkGameLogicDLL, (void**)&g_linkGameLogic) != MH_OK
        || MH_EnableHook(link) != MH_OK) {
        Log("hooking LinkGameLogicDLL failed");
        Warn("Sonic 3 & Knuckles' game code couldn't be hooked: extras in Sonic 3 & Knuckles play as Sonic.");
        return;
    }
    Log("hooks installed");
    shots::SetUp();  // (before S3&K links: SuperHammer's registration needs to know)
    SetUpFireImmunity();
    jugg::SetUp();  // (after the shots' SetUp: it needs their hooks)
    treasure::SetUp();  // (Rouge's Jewel Thief: ItemBox's powerup, TreasureSense.h)
}
