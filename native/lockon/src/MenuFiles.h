// The menu archives the SONIC MANIA button needs: the island scene with its two layout patterns (in every
// raw\ui\ui_mainmenu_<language>.pac) and its text keys (in every raw\text\text_menu_<language>.pac). Included by
// ManiaLockOn.cpp.
//
// Two places have them:
// - NoSwap's own menu archives (tools/build_origins_menu.py adds the patterns and keys to every archive it builds and
//   names them under "mania_launcher" in its raw\ui\noswap_cards.json): a "carrier". With NoSwap installed the loader
//   serves its archives, and Lock-On leaves them alone.
// - Lock-On's own: for each archive no other mod replaces, Sync() rebuilds it from the game's own copy and the
//   mod's patch (patches\raw\...\<archive>.mlp, tools/build_lockon_menu.py: the game's size and CRC-32 are checked,
//   and the result's) into the mod's own raw\ folder, which the loader lays over the game's (mod.ini IncludeDir0=".").
//   A stamp in cache\ (the game file's and the patch's size and time) skips the rebuild next time. Lock-On's copy is
//   deleted whenever another mod has the archive (so the loader can never pick it over NoSwap's, whatever the mod
//   order), when the game's copy changed and the patch no longer fits (a game update), or when it is stale and the
//   button is off.
// An archive another mod replaces without the patterns (not a carrier) turns the button off.
//
// Watch() then checks what the game really opens (a hook on CreateFileW that only looks, never redirects): a menu
// archive opened from the game's own folder (Lock-On's copy not picked up) or from a mod that isn't a carrier turns
// the button off from the next menu build (Ready() false), so the table slot never shows a button the layout can't.
#pragma once

namespace menu_files {

struct OtherMod {
    std::wstring path;  // as the loader gives it
    std::wstring norm;  // NormW, no drive, trailing '\' (for finding it inside a full path)
    std::string name;
    std::vector<std::wstring> includes;  // its include folders (mod.ini [Main] IncludeDir<k>), with a trailing '\'
    int carrier = -1;                    // its raw\ui\noswap_cards.json names the button's patterns (-1: not read yet)
};
static std::vector<OtherMod> g_mods;  // the other enabled mods (SetMods, before anything else here)
static std::wstring g_ourNorm;        // our folder as OtherMod::norm
static std::string g_patternDlc;      // a pattern the carrier's descriptor must name (Launcher.h PATTERN_DLC)
static bool g_synced = false;

// ---------------------------------------------------------------- the mods
static std::wstring NormNoDrive(std::wstring p) {
    p = NormW(p);
    size_t colon = p.find(L':');  // ("Z:/var/..." -> the part after the drive, whatever form the game uses)
    if (colon != std::wstring::npos)
        p = p.substr(colon + 1);
    while (p.rfind(L".\\", 0) == 0)
        p.erase(0, 2);
    if (!p.empty() && p.back() != L'\\')
        p += L'\\';
    return p;
}

static CRITICAL_SECTION g_whyLock;  // (Seen's reason, below)

static void SetMods(ModInfo* modInfo) {
    InitializeCriticalSection(&g_whyLock);
    g_ourNorm = NormNoDrive(OurFolder());
    if (!modInfo || !modInfo->ModList || !Readable(modInfo->ModList, 2 * sizeof(void*)))
        return;
    Mod** begin = ((Mod***)modInfo->ModList)[0];
    Mod** end = ((Mod***)modInfo->ModList)[1];
    for (Mod** m = begin; m && m < end && m < begin + 256; m++) {
        if (!Readable(m, sizeof(Mod*)) || !*m || !Readable(*m, sizeof(Mod)) || !(*m)->Path || *m == modInfo->CurrentMod)
            continue;
        OtherMod o;
        o.path = Widen((*m)->Path);
        while (!o.path.empty() && (o.path.back() == L'\\' || o.path.back() == L'/'))
            o.path.pop_back();
        o.norm = NormNoDrive(o.path);
        if (o.norm == g_ourNorm)
            continue;
        o.name = (*m)->Name && Readable((*m)->Name, 1) ? (*m)->Name : Narrow(o.path);
        std::wstring ini = o.path + L"\\mod.ini";
        int count = GetPrivateProfileIntW(L"Main", L"IncludeDirCount", 0, ini.c_str());  // (as the loader reads it)
        for (int k = 0; k < count && k < 64; k++) {
            wchar_t dir[512]{};
            GetPrivateProfileStringW(L"Main", (L"IncludeDir" + std::to_wstring(k)).c_str(), L"", dir, 512, ini.c_str());
            std::wstring d = dir;
            for (auto& c : d)
                if (c == L'/')
                    c = L'\\';
            while (!d.empty() && (d.back() == L'\\' || d.back() == L' '))
                d.pop_back();
            o.includes.push_back(o.path + L"\\" + (d.empty() || d == L"." ? L"" : d + L"\\"));
        }
        g_mods.push_back(o);
    }
}

// The mod's menu archives carry the button (NoSwap's descriptor names the patterns)
static bool IsCarrier(OtherMod& o) {
    if (o.carrier < 0) {
        o.carrier = 0;
        for (auto& inc : o.includes) {
            bool ok;
            std::string text = ReadAll(inc + L"raw\\ui\\noswap_cards.json", ok);
            if (ok && text.find("\"mania_launcher\"") != std::string::npos && !g_patternDlc.empty()
                && text.find(g_patternDlc) != std::string::npos)
                o.carrier = 1;
        }
    }
    return o.carrier == 1;
}

// ---------------------------------------------------------------- the patches (tools/build_lockon_menu.py PATCH)
static uint32_t Crc32(const uint8_t* p, size_t n) {
    static uint32_t table[256];
    static bool made = false;
    if (!made) {
        for (uint32_t i = 0; i < 256; i++) {
            uint32_t c = i;
            for (int k = 0; k < 8; k++)
                c = c & 1 ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            table[i] = c;
        }
        made = true;
    }
    uint32_t c = 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++)
        c = table[(c ^ p[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

template <typename T> static bool Take(const std::string& b, size_t& at, T& v) {
    if (at + sizeof(T) > b.size())
        return false;
    memcpy(&v, b.data() + at, sizeof(T));
    at += sizeof(T);
    return true;
}

// The game's archive + the patch -> the archive with the button's data (false and why: not this game's file, ...)
static bool ApplyPatch(const std::string& src, const std::string& patch, std::string& out, std::string& why) {
    size_t at = 4;
    uint32_t version, srcCrc, outCrc, count;
    uint64_t srcSize, outSize;
    if (patch.size() < 4 || memcmp(patch.data(), "MLOP", 4) != 0 || !Take(patch, at, version) || version != 1
        || !Take(patch, at, srcSize) || !Take(patch, at, srcCrc) || !Take(patch, at, outSize) || !Take(patch, at, outCrc)
        || !Take(patch, at, count) || outSize > (512u << 20))
        return why = "not a Lock-On patch (or a newer one)", false;
    if (src.size() != srcSize || Crc32((const uint8_t*)src.data(), src.size()) != srcCrc)
        return why = "the game's file isn't the one the patch was made for (another game version?)", false;
    out.clear();
    out.reserve(outSize);
    for (uint32_t i = 0; i < count; i++) {
        uint8_t kind;
        uint32_t n;
        if (!Take(patch, at, kind))
            return why = "the patch is cut short", false;
        if (kind == 0) {
            uint64_t off;
            if (!Take(patch, at, off) || !Take(patch, at, n) || off > src.size() || n > src.size() - off)
                return why = "the patch is damaged", false;
            out.append(src, off, n);
        } else if (kind == 1) {
            if (!Take(patch, at, n) || n > patch.size() - at)
                return why = "the patch is damaged", false;
            out.append(patch, at, n);
            at += n;
        } else {
            return why = "the patch is damaged", false;
        }
        if (out.size() > outSize)
            return why = "the patch is damaged", false;
    }
    if (at != patch.size() || out.size() != outSize || Crc32((const uint8_t*)out.data(), out.size()) != outCrc)
        return why = "the result doesn't check out", false;
    return true;
}

static bool SizeAndTime(const std::wstring& path, uint64_t& size, uint64_t& time) {
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &a) || (a.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
        return false;
    size = ((uint64_t)a.nFileSizeHigh << 32) | a.nFileSizeLow;
    time = ((uint64_t)a.ftLastWriteTime.dwHighDateTime << 32) | a.ftLastWriteTime.dwLowDateTime;
    return true;
}

static std::string StampOf(const std::wstring& game, const std::wstring& patch) {
    uint64_t gs, gt, ps, pt;
    if (!SizeAndTime(game, gs, gt) || !SizeAndTime(patch, ps, pt))
        return "";
    char buf[160];
    snprintf(buf, sizeof(buf), "lockon-menu 1 %llu %llu %llu %llu", (unsigned long long)gs, (unsigned long long)gt,
             (unsigned long long)ps, (unsigned long long)pt);
    return buf;
}

static bool WriteFileAtomically(const std::wstring& path, const std::string& data) {
    std::wstring tmp = path + L".tmp";
    FILE* f = _wfopen(tmp.c_str(), L"wb");
    if (!f)
        return false;
    bool good = fwrite(data.data(), 1, data.size(), f) == data.size();
    good = fclose(f) == 0 && good;
    good = good && MoveFileExW(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING);
    if (!good)
        DeleteFileW(tmp.c_str());
    return good;
}

static void Remove(const std::wstring& copy, const std::wstring& stamp, const char* why) {
    bool had = GetFileAttributesW(copy.c_str()) != INVALID_FILE_ATTRIBUTES;
    DeleteFileW(copy.c_str());
    DeleteFileW(stamp.c_str());
    if (had)
        Log("menu: %s removed (%s)", Narrow(copy.substr(OurFolder().size() + 1)).c_str(), why);
}

// The game's folder (the exe is in <game>\build\main\projects\exec), with a trailing '\'
static std::wstring GameRaw() {
    wchar_t exe[MAX_PATH]{};
    GetModuleFileNameW(nullptr, exe, MAX_PATH);
    std::wstring p = exe;
    for (int up = 0; up < 5; up++) {  // (the exe's name, then exec, projects, main, build)
        size_t slash = p.find_last_of(L"\\/");
        if (slash == std::wstring::npos)
            return L"";
        p.resize(slash);
    }
    return p + L"\\image\\x64\\raw\\";
}

// Every archive the button needs: Lock-On's copy made or kept where no other mod has it (`make` false: only the
// clean-up, never a new copy). -> true when every archive the game has is ours or a carrier's.
static bool Sync(bool make, const char* patternDlc) {
    g_synced = true;
    if (patternDlc)
        g_patternDlc = patternDlc;
    std::wstring ours = OurFolder() + L"\\", raw = GameRaw();
    CreateDirectoryW((ours + L"cache").c_str(), nullptr);
    int scenes = 0, texts = 0;
    bool bad = false;
    for (const wchar_t* sub : {L"ui", L"text"}) {
        std::wstring patches = ours + L"patches\\raw\\" + sub + L"\\";
        WIN32_FIND_DATAW fd;
        HANDLE h = FindFirstFileW((patches + L"*.mlp").c_str(), &fd);
        if (h == INVALID_HANDLE_VALUE)
            continue;
        do {
            std::wstring file = fd.cFileName;
            file.resize(file.size() - 4);  // (the archive's name)
            std::wstring rel = std::wstring(L"raw\\") + sub + L"\\" + file;
            std::wstring copy = ours + rel, stamp = ours + L"cache\\" + file + L".stamp", game = raw + sub + L"\\" + file;
            std::wstring patch = patches + fd.cFileName;
            std::string name = Narrow(rel);
            std::vector<OtherMod*> providers;
            for (auto& o : g_mods)
                for (auto& inc : o.includes)
                    if (GetFileAttributesW((inc + rel).c_str()) != INVALID_FILE_ATTRIBUTES) {
                        providers.push_back(&o);
                        break;
                    }
            if (!providers.empty()) {
                Remove(copy, stamp, "another mod has it");
                for (OtherMod* o : providers) {
                    bool carrier = !g_patternDlc.empty() && IsCarrier(*o);
                    if (make)
                        Log("menu: %s comes from %s (%s)", name.c_str(), o->name.c_str(),
                            carrier ? "with the button's patterns: fine" : "WITHOUT the button's patterns");
                    bad = bad || !carrier;
                }
                (sub[0] == L'u' ? scenes : texts)++;
                continue;
            }
            uint64_t size, time;
            if (!SizeAndTime(game, size, time)) {  // (a language the game doesn't have)
                Remove(copy, stamp, "the game has no such file");
                continue;
            }
            std::string want = StampOf(game, patch);
            bool ok;
            std::string have = ReadAll(stamp, ok);
            uint64_t copySize, copyTime;
            if (!want.empty() && ok && have == want && SizeAndTime(copy, copySize, copyTime)) {
                (sub[0] == L'u' ? scenes : texts)++;
                continue;
            }
            if (!make) {
                Remove(copy, stamp, "out of date, and the button is off");
                continue;
            }
            bool okSrc, okPatch;
            std::string src = ReadAll(game, okSrc), pat = ReadAll(patch, okPatch), out, why;
            if (!okSrc || !okPatch) {
                why = !okSrc ? "the game's file couldn't be read" : "the patch couldn't be read";
            } else if (ApplyPatch(src, pat, out, why)) {
                CreateDirectoryW((ours + L"raw").c_str(), nullptr);
                CreateDirectoryW((ours + L"raw\\" + sub).c_str(), nullptr);
                if (WriteFileAtomically(copy, out) && WriteFileAtomically(stamp, want)) {
                    Log("menu: %s made from the game's (%u bytes)", name.c_str(), (unsigned)out.size());
                    (sub[0] == L'u' ? scenes : texts)++;
                    continue;
                }
                why = "writing it failed";
            }
            Log("menu: %s: %s", name.c_str(), why.c_str());
            Remove(copy, stamp, "not usable");
            bad = true;
        } while (FindNextFileW(h, &fd));
        FindClose(h);
    }
    if (!make)
        return false;
    if (bad || !scenes || !texts) {
        Log("menu: off (%s): no SONIC MANIA button",
            bad ? "a menu archive without the button's patterns, see above"
                : "no menu archives: the mod's patches\\ folder is missing");
        return false;
    }
    Log("menu: %d scene and %d text archives ready", scenes, texts);
    return true;
}

static bool Synced() { return g_synced; }

// ---------------------------------------------------------------- what the game opens
static volatile LONG g_sceneBad = 0, g_textBad = 0;  // the last one of each the game opened can't show the button
static std::string g_why;

static bool Ready() { return !g_sceneBad && !g_textBad; }
static std::string WhyNotReady() {
    EnterCriticalSection(&g_whyLock);
    std::string why = g_why;
    LeaveCriticalSection(&g_whyLock);
    return "no SONIC MANIA button: " + why;
}

// 1 a scene archive (ui_mainmenu_<language>.pac, not ui_mainmenu_pkg_*), 2 a text archive (text_menu_<language>.pac)
// (by file name: NoSwap's cache copies are named menu_raw_text_text_menu_<language>.pac)
static int Kind(const std::wstring& n) {
    size_t slash = n.find_last_of(L'\\');
    std::wstring file = slash == std::wstring::npos ? n : n.substr(slash + 1);
    if (file.size() < 5 || file.compare(file.size() - 4, 4, L".pac") != 0)
        return 0;
    size_t at = file.rfind(L"ui_mainmenu_");
    if (at != std::wstring::npos && file.compare(at, 16, L"ui_mainmenu_pkg_") != 0 && file.size() > at + 16)
        return 1;
    at = file.rfind(L"text_menu_");
    return at != std::wstring::npos && file.size() > at + 14 ? 2 : 0;
}

typedef HANDLE(WINAPI* CreateFileWFn)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
static CreateFileWFn g_createFileW = nullptr;

static void Seen(int kind, const wchar_t* name) {
    std::wstring n = NormW(name);
    const char* verdict = nullptr;
    std::string from;
    bool fine = false;
    if (n.find(g_ourNorm) != std::wstring::npos) {
        fine = true, from = "Mania Lock-On";
    } else {
        for (auto& o : g_mods)
            if (n.find(o.norm) != std::wstring::npos) {
                from = o.name;
                fine = IsCarrier(o);
                verdict = fine ? nullptr : "it has no SONIC MANIA patterns";
                break;
            }
        if (from.empty())
            from = "the game's own folder", verdict = "Lock-On's copy wasn't used: quit and start the game again";
    }
    volatile LONG* bad = kind == 1 ? &g_sceneBad : &g_textBad;
    LONG was = InterlockedExchange(bad, fine ? 0 : 1);
    if (!fine) {
        EnterCriticalSection(&g_whyLock);
        g_why = Narrow(n.substr(n.find_last_of(L'\\') + 1)) + " opened from " + from + " (" + verdict + ")";
        LeaveCriticalSection(&g_whyLock);
    }
    static volatile LONG logged = 0;
    if (InterlockedIncrement(&logged) <= 40 || was != (fine ? 0 : 1))
        Log("menu: the game opened %s from %s%s", Narrow(n.substr(n.find_last_of(L'\\') + 1)).c_str(), from.c_str(),
            fine ? "" : (std::string(": ") + verdict).c_str());
}

static HANDLE WINAPI Hook_CreateFileW(LPCWSTR name, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                      DWORD flags, HANDLE tmpl) {
    if (name && !(access & GENERIC_WRITE)) {
        size_t len = wcslen(name);  // (cheap test first: every file the game opens comes through here)
        if (len > 4 && towlower(name[len - 1]) == L'c' && towlower(name[len - 2]) == L'a'
            && towlower(name[len - 3]) == L'p' && name[len - 4] == L'.') {
            int kind = Kind(NormW(name));
            if (kind) {
                HANDLE h = g_createFileW(name, access, share, sa, disp, flags, tmpl);
                if (h != INVALID_HANDLE_VALUE)
                    Seen(kind, name);
                return h;
            }
        }
    }
    return g_createFileW(name, access, share, sa, disp, flags, tmpl);
}

static void Watch() {
    void* target = (void*)GetProcAddress(GetModuleHandleA("kernelbase.dll"), "CreateFileW");
    if (!target)
        target = (void*)GetProcAddress(GetModuleHandleA("kernel32.dll"), "CreateFileW");
    bool ok = target && MH_CreateHook(target, (void*)Hook_CreateFileW, (void**)&g_createFileW) == MH_OK
              && MH_EnableHook(target) == MH_OK;
    Log("menu: %s", ok ? "watching which menu archives the game opens"
                       : "the file watch couldn't go in (the button relies on the archives found at startup)");
}

}  // namespace menu_files
