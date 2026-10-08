// Origins' character select cards from the installed packages (docs/plan-b-modular-characters.md, phase B).
// Plain C++ (no Windows headers), so a test can build it natively; the DLL does the file work around it.
//
// tools/build_origins_menu.py builds NoSwap's menu archives once with generic card slots 1..slots (tools/
// origins_cards.py):
// - a picture cell per slot (BC7 blocks below the select's Sonic texture), shown by the animation CardPattern(s, lines);
// - two name text keys per slot, CardNameKey(s, 1 / 2), each with room for nameUnits UTF-16 units.
// The chunks holding them are LZ4 blocks of literals only, so the bytes sit in the file as they are. Its descriptor
// (raw/ui/noswap_cards.json) says, per archive, where those literal runs are in the file ([stream offset, file offset,
// length]) and where each slot's cell rows and name texts / lengths are in the stream. At startup the DLL copies each
// archive to its cache folder, writes every offered character's card into its slot (PlanCardWrites; every other slot
// blank) and serves the copies. The Python mirror is origins_cards.plan (the two are proved equal).
//
// A package's card picture (its "ui/card_picture.dds", the descriptor's "picture"): a BC7 DDS (DX10 header, format 98,
// one mip), at most the cell's size, sides multiples of 4, placed bottom-centre in the cell. Its name: its
// noswap_character.json "name", split at the first space into the card's two lines.
//
// Descriptor version 2 adds the main menu's CONTINUE bubble heads (origins_cards.HEAD_*): "head" {cell [w, h],
// picture ("ui/menu_head.dds"), first_crop, scenes [{path, size}]} and, in the archive holding the head texture,
// "head_cells" / "head_pitch". A slot's head cell holds its character's head (a BC7 DDS at most the head cell's size,
// sides multiples of 4) in the middle; the scene archives (every language's main menu scene) are shipped as they are,
// with the head crops first_crop + slot - 1.
//
// Descriptor version 3 adds the sprite credit lines: "credit" {units, key (CardCreditKey(1)), cast (the select scene's
// credit text box)} and, in each text archive, "credits": per slot, (text, u64 length) offsets of CardCreditKey(slot),
// with room for `units` UTF-16 units. A card's credit is its package's noswap_character.json "credit_short". The DLL
// sets the box's text key to the highlighted card's credit key (Hook_UpdateSaveInfo), "" for any other card.
#pragma once

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <map>
#include <string>
#include <vector>

#include "ExtraData.h"  // JsonParser, JsonInt

constexpr int CARD_BLOCK = 16;  // bytes per BC7 block (4x4 pixels)

inline std::string CardPattern(int slot, int lines) {
    char buf[40];
    snprintf(buf, sizeof(buf), lines == 2 ? "PRM_noswap_%d_2" : "PRM_noswap_%d", slot);
    return buf;
}
inline std::string CardCreditKey(int slot) {
    char buf[64];
    snprintf(buf, sizeof(buf), "MAINMENU_character_credit_noswap%d", slot);
    return buf;
}
inline std::string CardNameKey(int slot, int line) {
    char buf[64];
    snprintf(buf, sizeof(buf), "MAINMENU_character_name_noswap%d_%d", slot, line);
    return buf;
}

struct CardRun {
    uint64_t stream, file, length;
};
struct CardArchive {
    std::string path;  // relative to NoSwap's folder, '/' separated ("raw/ui/ui_gamestage.pac")
    uint64_t size = 0;
    std::vector<CardRun> runs;  // literal-only chunks, in stream order
    uint64_t pitch = 0;         // pictures: bytes per row of blocks
    std::vector<uint64_t> cells;                          // pictures: each slot's top-left block (stream offset)
    std::vector<std::pair<uint64_t, uint64_t>> names;     // names: per slot, line 1 then 2: (text, u64 length) offsets
    std::vector<std::pair<uint64_t, uint64_t>> credits;   // credits (version 3): per slot, (text, u64 length) offsets
    uint64_t headPitch = 0;              // heads: bytes per row of blocks of the head texture
    std::vector<uint64_t> headCells;     // heads: each slot's head cell's top-left block (stream offset)
};
struct CardScene {
    std::string path;  // relative to NoSwap's folder, '/' separated
    uint64_t size = 0;
};
struct CardLayout {
    int slots = 0, cellW = 0, cellH = 0, nameUnits = 0;
    std::string picture;  // a package's card picture file, relative to its folder ("ui/card_picture.dds")
    std::string blank;    // the transparent BC7 block (16 bytes)
    std::vector<CardArchive> archives;
    // the CONTINUE bubble heads (version 2; headW 0: none)
    int headW = 0, headH = 0, headFirstCrop = 0;
    std::string headPicture;  // a package's head file, relative to its folder ("ui/menu_head.dds")
    std::vector<CardScene> headScenes;
    // the sprite credit lines (version 3; creditUnits 0: none)
    int creditUnits = 0;
    std::string creditCast;  // the select scene's credit text box
};

// ---------------------------------------------------------------- the descriptor
inline bool CardU64(const Json* v, uint64_t& out) {
    long long n;
    if (!JsonInt(v, n) || n < 0)
        return false;
    out = (uint64_t)n;
    return true;
}

inline bool ParseCardLayout(const std::string& text, CardLayout& layout, std::string& why) {
    layout = CardLayout();
    Json root;
    if (!JsonParser::Parse(text, root, why))
        return false;
    long long n;
    if (root.type != Json::Object || !JsonInt(root.Get("version"), n) || n < 1 || n > 3)
        return why = "not a version 1, 2 or 3 card descriptor", false;
    const bool v2 = n >= 2, v3 = n >= 3;
    const Json* cell = root.Get("cell");
    long long slots, w, h, units;
    if (!JsonInt(root.Get("slots"), slots) || slots < 1 || slots > 254 || !cell || cell->type != Json::Array
        || cell->items.size() != 2 || !JsonInt(&cell->items[0], w) || !JsonInt(&cell->items[1], h) || w < 4 || h < 4
        || w % 4 || h % 4 || w > 4096 || h > 4096 || !JsonInt(root.Get("name_units"), units) || units < 1 || units > 255)
        return why = "bad slots / cell / name_units", false;
    layout.slots = (int)slots, layout.cellW = (int)w, layout.cellH = (int)h, layout.nameUnits = (int)units;
    const Json* pic = root.Get("picture");
    const Json* blank = root.Get("blank_block");
    if (!pic || pic->type != Json::String || pic->str.empty() || pic->str.find("..") != std::string::npos || !blank
        || blank->type != Json::String || blank->str.size() != 2 * CARD_BLOCK)
        return why = "bad picture / blank_block", false;
    layout.picture = pic->str;
    for (size_t i = 0; i < CARD_BLOCK; i++) {
        unsigned v;
        if (sscanf(blank->str.c_str() + 2 * i, "%2x", &v) != 1)
            return why = "bad blank_block", false;
        layout.blank += (char)v;
    }
    // the names the archives were built with must be the ones this DLL asks for
    const Json* patterns = root.Get("patterns");
    const Json* keys = root.Get("name_keys");
    if (!patterns || patterns->type != Json::Array || patterns->items.size() != 2 || !keys
        || keys->type != Json::Array || keys->items.size() != 2 || patterns->items[0].str != CardPattern(1, 1)
        || patterns->items[1].str != CardPattern(1, 2) || keys->items[0].str != CardNameKey(1, 1)
        || keys->items[1].str != CardNameKey(1, 2))
        return why = "its patterns / name keys aren't this DLL's (" + CardPattern(1, 1) + ", " + CardNameKey(1, 1) + ")",
               false;
    auto safePath = [](const Json* p) {
        return p && p->type == Json::String && !p->str.empty() && p->str.find("..") == std::string::npos
               && p->str[0] != '/' && p->str[0] != '\\' && p->str.find(':') == std::string::npos;
    };
    if (const Json* head = v2 ? root.Get("head") : nullptr) {
        const Json* hc = head->Get("cell");
        const Json* hp = head->Get("picture");
        const Json* scenes = head->Get("scenes");
        long long hw, hh, first;
        if (head->type != Json::Object || !hc || hc->type != Json::Array || hc->items.size() != 2
            || !JsonInt(&hc->items[0], hw) || !JsonInt(&hc->items[1], hh) || hw < 4 || hh < 4 || hw % 4 || hh % 4
            || hw > 4096 || hh > 4096 || !JsonInt(head->Get("first_crop"), first) || first < 1 || first > 1000
            || !hp || hp->type != Json::String || hp->str.empty() || hp->str.find("..") != std::string::npos || !scenes
            || scenes->type != Json::Array)
            return why = "bad head", false;
        layout.headW = (int)hw, layout.headH = (int)hh, layout.headFirstCrop = (int)first, layout.headPicture = hp->str;
        for (const Json& sc : scenes->items) {
            CardScene scene;
            if (sc.type != Json::Object || !safePath(sc.Get("path")) || !CardU64(sc.Get("size"), scene.size))
                return why = "bad head scene", false;
            scene.path = sc.Get("path")->str;
            layout.headScenes.push_back(scene);
        }
    }
    if (const Json* credit = v3 ? root.Get("credit") : nullptr) {
        const Json* key = credit->Get("key");
        const Json* cast = credit->Get("cast");
        long long cu;
        if (credit->type != Json::Object || !JsonInt(credit->Get("units"), cu) || cu < 1 || cu > 255 || !key
            || key->type != Json::String || key->str != CardCreditKey(1) || !cast || cast->type != Json::String
            || cast->str.empty() || cast->str.size() > 60)
            return why = "bad credit (or its key isn't this DLL's " + CardCreditKey(1) + ")", false;
        layout.creditUnits = (int)cu, layout.creditCast = cast->str;
    }
    const Json* archives = root.Get("archives");
    if (!archives || archives->type != Json::Array || archives->items.empty())
        return why = "no archives", false;
    for (const Json& a : archives->items) {
        CardArchive ar;
        const Json* path = a.Get("path");
        if (!path || path->type != Json::String || path->str.empty() || path->str.find("..") != std::string::npos
            || path->str[0] == '/' || path->str[0] == '\\' || path->str.find(':') != std::string::npos)
            return why = "an archive with a bad path", false;
        ar.path = path->str;
        const Json* runs = a.Get("runs");
        if (!CardU64(a.Get("size"), ar.size) || !runs || runs->type != Json::Array || runs->items.empty())
            return why = ar.path + ": bad size / runs", false;
        uint64_t lastStream = 0, lastFile = 0;
        for (const Json& r : runs->items) {
            CardRun run;
            if (r.type != Json::Array || r.items.size() != 3 || !CardU64(&r.items[0], run.stream)
                || !CardU64(&r.items[1], run.file) || !CardU64(&r.items[2], run.length) || run.length == 0
                || run.file + run.length > ar.size || run.stream < lastStream || run.file < lastFile)
                return why = ar.path + ": bad run", false;
            lastStream = run.stream + run.length, lastFile = run.file + run.length;
            ar.runs.push_back(run);
        }
        const Json* cells = a.Get("cells");
        const Json* names = a.Get("names");
        const Json* heads = a.Get("head_cells");
        const Json* credits = a.Get("credits");
        if (credits) {
            if (!layout.creditUnits || credits->type != Json::Array || (int)credits->items.size() != layout.slots)
                return why = ar.path + ": bad credits", false;
            for (const Json& p : credits->items) {
                uint64_t t, l;
                if (p.type != Json::Array || p.items.size() != 2 || !CardU64(&p.items[0], t) || !CardU64(&p.items[1], l))
                    return why = ar.path + ": bad credit entry", false;
                ar.credits.push_back({t, l});
            }
        }
        if (!cells && !names)
            return why = ar.path + ": neither cells nor names", false;
        if (heads) {
            if (!layout.headW || heads->type != Json::Array || (int)heads->items.size() != layout.slots
                || !CardU64(a.Get("head_pitch"), ar.headPitch)
                || ar.headPitch < (uint64_t)(layout.headW / 4 * CARD_BLOCK))
                return why = ar.path + ": bad head_cells / head_pitch", false;
            for (const Json& c : heads->items) {
                uint64_t at;
                if (!CardU64(&c, at))
                    return why = ar.path + ": bad head cell", false;
                ar.headCells.push_back(at);
            }
        }
        if (cells) {
            if (cells->type != Json::Array || (int)cells->items.size() != layout.slots || !CardU64(a.Get("pitch"), ar.pitch)
                || ar.pitch < (uint64_t)(layout.cellW / 4 * CARD_BLOCK))
                return why = ar.path + ": bad cells / pitch", false;
            for (const Json& c : cells->items) {
                uint64_t at;
                if (!CardU64(&c, at))
                    return why = ar.path + ": bad cell", false;
                ar.cells.push_back(at);
            }
        }
        if (names) {
            if (names->type != Json::Array || (int)names->items.size() != 2 * layout.slots)
                return why = ar.path + ": bad names", false;
            for (const Json& p : names->items) {
                uint64_t t, l;
                if (p.type != Json::Array || p.items.size() != 2 || !CardU64(&p.items[0], t) || !CardU64(&p.items[1], l))
                    return why = ar.path + ": bad name entry", false;
                ar.names.push_back({t, l});
            }
        }
        layout.archives.push_back(std::move(ar));
    }
    return true;
}

// ---------------------------------------------------------------- a card
struct CardPicture {
    int w = 0, h = 0;    // 0: none
    std::string blocks;  // (w / 4) x (h / 4) BC7 blocks, row by row
};
struct Card {
    bool used = false;
    CardPicture picture;
    CardPicture head;      // its CONTINUE bubble head (w 0: none, the cell is blank)
    std::string lines[2];  // UTF-16LE, at most nameUnits units each
    std::string credit;    // UTF-16LE, at most creditUnits units ("": none)
};

// A card picture (or, with `head`, a CONTINUE bubble head: at most the head cell's size)
inline bool ReadCardPicture(const std::string& dds, const CardLayout& layout, CardPicture& out, std::string& why,
                            bool head = false) {
    const int maxW = head ? layout.headW : layout.cellW, maxH = head ? layout.headH : layout.cellH;
    out = CardPicture();
    auto u32 = [&](size_t at) {
        uint32_t v;
        memcpy(&v, dds.data() + at, 4);
        return v;
    };
    if (dds.size() < 148 || dds.compare(0, 4, "DDS ") != 0 || dds.compare(84, 4, "DX10") != 0)
        return why = "not a DDS file with a DX10 header", false;
    uint32_t h = u32(12), w = u32(16), mips = u32(28), format = u32(128);
    if (format != 98 || mips > 1)
        return why = "format " + std::to_string(format) + ", " + std::to_string(mips) + " mips: expected BC7 (98), one mip",
               false;
    if (w == 0 || h == 0 || w > (uint32_t)maxW || h > (uint32_t)maxH || w % 4 || h % 4)
        return why = std::to_string(w) + "x" + std::to_string(h) + ": must be at most " + std::to_string(maxW) + "x"
                     + std::to_string(maxH) + ", sides multiples of 4",
               false;
    size_t n = (size_t)(w / 4) * (h / 4) * CARD_BLOCK;
    if (dds.size() != 148 + n)
        return why = std::to_string(dds.size()) + " bytes, expected " + std::to_string(148 + n), false;
    out.w = (int)w, out.h = (int)h, out.blocks = dds.substr(148);
    return true;
}

// UTF-8 text as UTF-16LE cut to `units` units; `cut` / `bad` say whether it was cut short or had bytes that aren't
// UTF-8 (read as '?')
inline std::string CardUtf16(const std::string& s, int units, bool& cut, bool& bad) {
    std::string out;
    int count = 0;
    cut = bad = false;
    for (size_t i = 0; i < s.size();) {
        unsigned char c = (unsigned char)s[i];
        uint32_t cp;
        int len = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 0;
        if (len == 0 || i + len > s.size()) {
            cp = '?', len = 1, bad = true;
        } else {
            cp = len == 1 ? c : c & (0x7F >> len);
            for (int k = 1; k < len; k++) {
                unsigned char d = (unsigned char)s[i + k];
                if ((d >> 6) != 2) {
                    cp = '?', len = 1, bad = true;
                    break;
                }
                cp = cp << 6 | (d & 0x3F);
            }
        }
        i += len;
        int need = cp >= 0x10000 ? 2 : 1;
        if (count + need > units) {
            cut = true;
            break;
        }
        auto put = [&](uint32_t u) { out += (char)(u & 0xFF), out += (char)(u >> 8); };
        if (need == 2) {
            put(0xD800 + ((cp - 0x10000) >> 10)), put(0xDC00 + ((cp - 0x10000) & 0x3FF));
        } else {
            put(cp);
        }
        count += need;
    }
    return out;
}

// A name as the card's two lines (split at the first space), UTF-16LE, each cut to `units` units. `note` says what was
// changed (cut short, or bytes that aren't UTF-8, read as '?').
inline void CardNameLines(const std::string& name, int units, std::string lines[2], std::string& note) {
    note.clear();
    size_t space = name.find(' ');
    std::string parts[2] = {name.substr(0, space), space == std::string::npos ? "" : name.substr(space + 1)};
    for (int l = 0; l < 2; l++) {
        bool cut, bad;
        lines[l] = CardUtf16(parts[l], units, cut, bad);
        if (cut)
            note += std::string(note.empty() ? "" : "; ") + "line " + std::to_string(l + 1) + " cut to "
                    + std::to_string(units) + " characters";
        if (bad)
            note += std::string(note.empty() ? "" : "; ") + "line " + std::to_string(l + 1) + " isn't all UTF-8";
    }
}

// Slots for the offered kinds (ascending): kind - 6 when that slot exists (the first characters keep the slots the
// archives ship them in), else the lowest free one; none (0) past the last slot.
inline std::map<int, int> AssignCardSlots(const std::vector<int>& kinds, int slots) {
    std::map<int, int> out;
    std::vector<bool> used(slots + 1, false);
    for (int k : kinds)
        if (k - 6 >= 1 && k - 6 <= slots)
            out[k] = k - 6, used[k - 6] = true;
    int next = 1;
    for (int k : kinds) {
        if (out.count(k))
            continue;
        while (next <= slots && used[next])
            next++;
        out[k] = next <= slots ? next : 0;
        if (next <= slots)
            used[next] = true;
    }
    return out;
}

// ---------------------------------------------------------------- the writes
struct CardWrite {
    uint64_t at;  // file offset
    std::string bytes;
};

// The LZ4 block header of a block holding n bytes as literals only
inline std::string CardLiteralHeader(uint64_t n) {
    if (n < 15)
        return std::string(1, (char)(n << 4));
    std::string h(1, (char)0xF0);
    n -= 15;
    h.append((size_t)(n / 255), (char)0xFF);
    h += (char)(n % 255);
    return h;
}

// `data` at stream offset `at`, through the literal runs, as file writes; false if a byte isn't in a run
inline bool CardToFile(const CardArchive& ar, uint64_t at, const std::string& data, std::vector<CardWrite>& out) {
    uint64_t end = at + data.size(), covered = 0;
    for (const CardRun& r : ar.runs) {
        uint64_t lo = std::max(at, r.stream), hi = std::min(end, r.stream + r.length);
        if (lo < hi) {
            out.push_back({r.file + lo - r.stream, data.substr((size_t)(lo - at), (size_t)(hi - lo))});
            covered += hi - lo;
        }
    }
    return covered == data.size();
}

// Every write that puts `cards` (index slot - 1; unused ones blank) into one archive
inline bool PlanCardWrites(const CardLayout& layout, const CardArchive& ar, const std::vector<Card>& cards,
                           std::vector<CardWrite>& out, std::string& why) {
    out.clear();
    if ((int)cards.size() != layout.slots)
        return why = "wrong number of cards", false;
    int bw = layout.cellW / 4, bh = layout.cellH / 4;
    std::string blankRow;
    for (int i = 0; i < bw; i++)
        blankRow += layout.blank;
    for (size_t i = 0; i < ar.cells.size(); i++) {
        const Card& c = cards[i];
        const CardPicture* p = c.used && c.picture.w ? &c.picture : nullptr;
        int cw = p ? p->w / 4 : 0, ch = p ? p->h / 4 : 0, x0 = (bw - cw) / 2, y0 = bh - ch;
        for (int r = 0; r < bh; r++) {
            std::string row = blankRow;
            if (p && r >= y0)
                row.replace((size_t)x0 * CARD_BLOCK, (size_t)cw * CARD_BLOCK,
                            p->blocks.substr((size_t)(r - y0) * cw * CARD_BLOCK, (size_t)cw * CARD_BLOCK));
            if (!CardToFile(ar, ar.cells[i] + (uint64_t)r * ar.pitch, row, out))
                return why = ar.path + ": slot " + std::to_string(i + 1) + "'s cell isn't all in literal runs", false;
        }
    }
    // the CONTINUE bubble heads: in the middle of their cells
    int hbw = layout.headW / 4, hbh = layout.headH / 4;
    std::string blankHeadRow;
    for (int i = 0; i < hbw; i++)
        blankHeadRow += layout.blank;
    for (size_t i = 0; i < ar.headCells.size(); i++) {
        const Card& c = cards[i];
        const CardPicture* p = c.used && c.head.w ? &c.head : nullptr;
        int cw = p ? p->w / 4 : 0, ch = p ? p->h / 4 : 0, x0 = (hbw - cw) / 2, y0 = (hbh - ch) / 2;
        for (int r = 0; r < hbh; r++) {
            std::string row = blankHeadRow;
            if (p && r >= y0 && r < y0 + ch)
                row.replace((size_t)x0 * CARD_BLOCK, (size_t)cw * CARD_BLOCK,
                            p->blocks.substr((size_t)(r - y0) * cw * CARD_BLOCK, (size_t)cw * CARD_BLOCK));
            if (!CardToFile(ar, ar.headCells[i] + (uint64_t)r * ar.headPitch, row, out))
                return why = ar.path + ": slot " + std::to_string(i + 1) + "'s head cell isn't all in literal runs", false;
        }
    }
    for (size_t i = 0; i < ar.names.size(); i++) {
        const Card& c = cards[i / 2];
        std::string text = c.used ? c.lines[i % 2] : "";
        uint64_t units = text.size() / 2;
        if (units > (uint64_t)layout.nameUnits)
            return why = "a name line longer than the room", false;
        text.resize((size_t)(layout.nameUnits + 1) * 2, '\0');
        std::string length((const char*)&units, 8);  // (little-endian, as the targets are)
        if (!CardToFile(ar, ar.names[i].first, text, out) || !CardToFile(ar, ar.names[i].second, length, out))
            return why = ar.path + ": slot " + std::to_string(i / 2 + 1) + "'s name isn't all in literal runs", false;
    }
    for (size_t i = 0; i < ar.credits.size(); i++) {
        const Card& c = cards[i];
        std::string text = c.used ? c.credit : "";
        uint64_t units = text.size() / 2;
        if (units > (uint64_t)layout.creditUnits)
            return why = "a credit longer than the room", false;
        text.resize((size_t)(layout.creditUnits + 1) * 2, '\0');
        std::string length((const char*)&units, 8);
        if (!CardToFile(ar, ar.credits[i].first, text, out) || !CardToFile(ar, ar.credits[i].second, length, out))
            return why = ar.path + ": slot " + std::to_string(i + 1) + "'s credit isn't all in literal runs", false;
    }
    return true;
}

// The archive file is the one described: `read(at, n, out)` reads its bytes. Its size, and every literal run's header.
inline bool CheckCardRuns(const CardArchive& ar, uint64_t fileSize,
                          const std::function<bool(uint64_t, size_t, std::string&)>& read, std::string& why) {
    if (fileSize != ar.size)
        return why = ar.path + ": " + std::to_string(fileSize) + " bytes, the descriptor says " + std::to_string(ar.size),
               false;
    for (const CardRun& r : ar.runs) {
        std::string want = CardLiteralHeader(r.length), got;
        if (r.file < want.size() || !read(r.file - want.size(), want.size(), got) || got != want)
            return why = ar.path + ": no literal block header before file offset " + std::to_string(r.file), false;
    }
    return true;
}

// FNV-1a 64 over bytes (the cache copies' stamp)
inline uint64_t CardHash(uint64_t h, const void* data, size_t n) {
    const unsigned char* p = (const unsigned char*)data;
    for (size_t i = 0; i < n; i++)
        h = (h ^ p[i]) * 0x100000001B3ull;
    return h;
}
constexpr uint64_t CARD_HASH_START = 0xCBF29CE484222325ull;
