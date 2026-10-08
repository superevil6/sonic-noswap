// The file side of Origins' select cards (MenuCards.h): writing the planned card writes into a menu archive on disk.
// Windows only, no logging (each failure says why), so a small test program can build it with MinGW and run it under
// Wine (the scratch harness that proved the in-place fill equal to the cache copy).
//
// Two ways (NoSwapS3K.cpp SetUpMenuCards):
// - in place (FillCardsInPlace): NoSwap's own archive in its mod folder is rewritten, which HedgeModManager's loader
//   serves to the game whatever file function the game opens it with (mod.ini IncludeDir0="."). On native Windows the
//   game's menu archives never came through NoSwap's CreateFileW / CreateFileA hook (1.0.0: no "served raw/ui..." line,
//   blank cards), so this is the way that works everywhere.
// - a copy (CardPatchCopy into NoSwap's cache folder, served by the file hook): the fallback when the mod folder can't
//   be written. It works under Wine; on native Windows it may not.
// Both write the same bytes: the archive as shipped with every card write (MenuCards.h PlanCardWrites) over it.
#pragma once

#include <windows.h>
#include <cstdio>
#include <string>
#include <vector>

#include "MenuCards.h"

inline bool FileSizeAndTime(const std::wstring& path, uint64_t& size, uint64_t& time) {
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &a) || (a.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
        return false;
    size = (uint64_t)a.nFileSizeHigh << 32 | a.nFileSizeLow;
    time = (uint64_t)a.ftLastWriteTime.dwHighDateTime << 32 | a.ftLastWriteTime.dwLowDateTime;
    return true;
}

// Reads the given byte ranges of an open file and compares them with the writes
inline bool WritesInFile(FILE* f, const std::vector<CardWrite>& writes) {
    std::string got;
    for (auto& w : writes) {
        got.resize(w.bytes.size());
        if (_fseeki64(f, (long long)w.at, SEEK_SET) != 0 || fread(&got[0], 1, got.size(), f) != got.size()
            || got != w.bytes)
            return false;
    }
    return true;
}

// The archive at `path` is the one the descriptor describes: its size and every literal run's block header (hundreds of
// anchors spread over the file). `size` gets its size.
inline bool CardFileIsDescribed(const CardArchive& ar, const std::wstring& path, uint64_t& size, std::string& why) {
    uint64_t time;
    if (!FileSizeAndTime(path, size, time))
        return why = ar.path + ": not there", false;
    FILE* f = _wfopen(path.c_str(), L"rb");
    if (!f)
        return why = ar.path + ": can't be read", false;
    bool good = CheckCardRuns(ar, size, [&](uint64_t at, size_t n, std::string& out) {
        out.resize(n);
        return _fseeki64(f, (long long)at, SEEK_SET) == 0 && fread(&out[0], 1, n, f) == n;
    }, why);
    fclose(f);
    if (!good && why.empty())
        why = ar.path + ": reading it failed";
    return good;
}

// `src` (checked against the descriptor) with `writes` over it, as `dest` (may be `src` itself): written to
// `dest`.noswap-new beside it, read back, then moved over `dest` (MOVEFILE_REPLACE_EXISTING). Nothing at `dest` changes
// unless every step worked. -> false with `why`.
inline bool CardPatchCopy(const CardArchive& ar, const std::vector<CardWrite>& writes, const std::wstring& src,
                          const std::wstring& dest, std::string& why) {
    uint64_t size, csize, ctime;
    if (!CardFileIsDescribed(ar, src, size, why))
        return false;
    std::wstring tmp = dest + L".noswap-new";
    SetFileAttributesW(tmp.c_str(), FILE_ATTRIBUTE_NORMAL);
    DeleteFileW(tmp.c_str());
    if (!CopyFileW(src.c_str(), tmp.c_str(), FALSE))
        return why = "copying it failed (error " + std::to_string(GetLastError()) + ")", false;
    SetFileAttributesW(tmp.c_str(), FILE_ATTRIBUTE_NORMAL);  // (a read-only source makes a read-only copy)
    FILE* f = _wfopen(tmp.c_str(), L"r+b");
    bool good = f != nullptr;
    for (size_t i = 0; good && i < writes.size(); i++)
        good = _fseeki64(f, (long long)writes[i].at, SEEK_SET) == 0
               && fwrite(writes[i].bytes.data(), 1, writes[i].bytes.size(), f) == writes[i].bytes.size();
    if (f)
        good = (fclose(f) == 0) && good;
    if (!good) {
        why = "writing it failed";
    } else {  // (self-check: the copy reads back with every write, at the size described)
        f = _wfopen(tmp.c_str(), L"rb");
        good = f && WritesInFile(f, writes);
        if (f)
            fclose(f);
        good = good && FileSizeAndTime(tmp, csize, ctime) && csize == size;
        if (!good)
            why = "it doesn't read back as written";
    }
    if (good) {
        DWORD attrs = GetFileAttributesW(dest.c_str());  // (a read-only target can't be replaced)
        if (attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_READONLY))
            SetFileAttributesW(dest.c_str(), attrs & ~FILE_ATTRIBUTE_READONLY);
        if (!MoveFileExW(tmp.c_str(), dest.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
            good = false, why = "moving it in place failed (error " + std::to_string(GetLastError()) + ")";
    }
    if (!good)
        DeleteFileW(tmp.c_str());
    return good;
}

enum CardFill { CARD_FILL_FAILED, CARD_FILL_SAME, CARD_FILL_WRITTEN };

// NoSwap's own archive at `path`, every card write put in place: nothing written when the file already holds every
// write (each start rewrites every slot, a card or a full blank, so this is only true when nothing changed), never
// touched when it isn't the archive the descriptor describes (another version, damaged).
inline CardFill FillCardsInPlace(const CardArchive& ar, const std::vector<CardWrite>& writes, const std::wstring& path,
                                 std::string& why) {
    uint64_t size;
    if (!CardFileIsDescribed(ar, path, size, why))
        return CARD_FILL_FAILED;
    FILE* f = _wfopen(path.c_str(), L"rb");
    bool same = f && WritesInFile(f, writes);
    if (f)
        fclose(f);
    if (same)
        return CARD_FILL_SAME;
    return CardPatchCopy(ar, writes, path, path, why) ? CARD_FILL_WRITTEN : CARD_FILL_FAILED;
}
