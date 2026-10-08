// The character registry (docs/plan-b-modular-characters.md, phase A): every character's permanent kind, by name.
// Plain C++ (no Windows headers), so a test can build it natively.
//
// Origins' character select numbers characters by "kind" (0-6 are the game's own). NoSwap gives each installed
// character package a kind from 7 up, decided at runtime, never at build time:
// - The registry file (%APPDATA%\SEGA\SonicOrigins\NoSwap\roster.json) maps each package key to its kind for good.
// - Today's 21 characters keep kinds 7..27 in their old order (LEGACY_KEYS), whatever the file says: old saves and
//   [Slots] numbers are converted by it, and NoSwap's menu archives ship with their cards written in at slots 1-21
//   (tools/build_origins_menu.py; the DLL gives kind k slot k - 6, and falls back to these if it can't write its own).
// - A key the registry doesn't know gets the next kind after the highest ever given (never a gap left by another).
// - A key whose package is gone keeps its kind in the file (reserved, never reused) and simply isn't offered.
// - Kinds are bytes, and 0xFF marks an empty card slot in Origins' rows: the highest kind is KIND_LIMIT - 1 (254), so at
//   most 248 characters (7..254) can ever be numbered. A key beyond that gets no kind: it isn't offered (logged).
// - A file that can't be read as a registry is set aside (the caller renames it) and the registry starts over from the
//   legacy kinds: characters beyond them then get new kinds, in the order their packages are found. Saves don't depend
//   on kinds (extras.sav and S3&K's [Slots] store keys), so nothing is lost but the numbers themselves.
//
// The file:
//   {"version": 1, "note": "...", "kinds": {"noswap.metal-sonic": 7, ..., "someone.newchar": 28}}
#pragma once

#include <cstdio>
#include <string>
#include <utility>
#include <vector>

#include "ExtraData.h"  // JsonParser, JsonInt

constexpr int FIRST_EXTRA_KIND = 7;
constexpr int KIND_LIMIT = 255;  // kinds are below this (0xFF: an empty card slot in Origins' rows)

// Today's 21 characters, frozen in this order: kind 7 + i. Also the numbering version-1 extras.sav files and old
// numeric [Slots] picks were written with (extra n = LEGACY_KEYS[n - 1]). Never reorder or remove; tools/
// gen_s3k_header.py checks that tools/extras.py's first 21 keys are these.
// ("noswap.r25__": a reserved placeholder, kind 25, that no package has: that character isn't in this repository.)
static const char* const LEGACY_KEYS[] = {
    "noswap.metal-sonic", "noswap.fang", "noswap.big", "noswap.shadow", "noswap.blaze", "noswap.silver",
    "noswap.mighty", "noswap.ray", "noswap.rouge", "noswap.charmy", "noswap.espio", "noswap.vector", "noswap.cream",
    "noswap.robotnik", "noswap.max", "noswap.tikal", "noswap.mario", "noswap.trip", "noswap.r25__", "noswap.gamma",
    "noswap.jet"};
constexpr int LEGACY_COUNT = sizeof(LEGACY_KEYS) / sizeof(LEGACY_KEYS[0]);
constexpr int LEGACY_LAST_KIND = FIRST_EXTRA_KIND + LEGACY_COUNT - 1;  // 27

// The legacy kind of a key (7..27), or -1
inline int LegacyKind(const std::string& key) {
    for (int i = 0; i < LEGACY_COUNT; i++)
        if (key == LEGACY_KEYS[i])
            return FIRST_EXTRA_KIND + i;
    return -1;
}
// The key a legacy kind had (nullptr: not a legacy kind)
inline const char* LegacyKey(int kind) {
    return kind >= FIRST_EXTRA_KIND && kind <= LEGACY_LAST_KIND ? LEGACY_KEYS[kind - FIRST_EXTRA_KIND] : nullptr;
}

struct Registry {
    std::vector<std::pair<std::string, int>> kinds;  // key -> kind, in kind order

    int KindOf(const std::string& key) const {
        for (auto& k : kinds)
            if (k.first == key)
                return k.second;
        return -1;
    }
    const std::string* KeyOf(int kind) const {
        for (auto& k : kinds)
            if (k.second == kind)
                return &k.first;
        return nullptr;
    }
    int Highest() const {
        int h = FIRST_EXTRA_KIND - 1;
        for (auto& k : kinds)
            h = k.second > h ? k.second : h;
        return h;
    }
    void Add(const std::string& key, int kind) {
        auto at = kinds.begin();
        while (at != kinds.end() && at->second < kind)
            ++at;
        kinds.insert(at, {key, kind});
    }
};

// Reads a registry file. False (with why) if it isn't one at all (not JSON, or no "kinds" object): the caller sets the
// file aside. Entries that can't be used are left out, each with a note: a kind that isn't a whole number in 7..254, a
// key given twice, a kind given twice, a legacy key away from its legacy kind or another key on a legacy kind.
inline bool ParseRegistry(const std::string& text, Registry& reg, std::vector<std::string>& notes, std::string& why) {
    reg = Registry();
    Json root;
    if (!JsonParser::Parse(text, root, why))
        return false;
    const Json* kinds = root.type == Json::Object ? root.Get("kinds") : nullptr;
    if (!kinds || kinds->type != Json::Object)
        return why = "no \"kinds\" object", false;
    for (auto& f : kinds->fields) {
        long long k;
        const std::string& key = f.first;
        if (key.empty()) {
            notes.push_back("an empty key, left out");
            continue;
        }
        if (!JsonInt(&f.second, k) || k < FIRST_EXTRA_KIND || k >= KIND_LIMIT) {
            notes.push_back(key + ": not a kind from 7 to 254, left out");
            continue;
        }
        if (reg.KindOf(key) >= 0) {
            notes.push_back(key + ": listed twice, the first kept");
            continue;
        }
        int legacy = LegacyKind(key);
        if (legacy >= 0 && legacy != k) {
            notes.push_back(key + ": kind " + std::to_string(k) + " in the file, but it keeps its own, " +
                            std::to_string(legacy));
            continue;
        }
        if (legacy < 0 && k <= LEGACY_LAST_KIND) {
            notes.push_back(key + ": kind " + std::to_string(k) + " belongs to " + LegacyKey((int)k) + ", left out");
            continue;
        }
        if (const std::string* other = reg.KeyOf((int)k)) {
            notes.push_back(key + ": kind " + std::to_string(k) + " is " + *other + "'s already, left out");
            continue;
        }
        reg.Add(key, (int)k);
    }
    return true;
}

inline std::string JsonQuote(const std::string& s) {
    std::string out = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\')
            out += '\\', out += (char)c;
        else if (c < 0x20) {
            char buf[8];
            snprintf(buf, sizeof(buf), "\\u%04x", c);
            out += buf;
        } else
            out += (char)c;
    }
    return out + "\"";
}

inline std::string RegistryText(const Registry& reg) {
    std::string out =
        "{\n  \"version\": 1,\n  \"note\": \"NoSwap's character numbers (Origins' character select kinds), by package key. "
        "Written by NoSwapS3K.dll: a kind is given once and kept for good, even when its package is removed. Kinds 7-27 "
        "are NoSwap's first 21 characters and can't change.\",\n  \"kinds\": {";
    for (size_t i = 0; i < reg.kinds.size(); i++)
        out += std::string(i ? ",\n    " : "\n    ") + JsonQuote(reg.kinds[i].first) + ": " +
               std::to_string(reg.kinds[i].second);
    return out + (reg.kinds.empty() ? "}\n}\n" : "\n  }\n}\n");
}

struct RosterResult {
    Registry registry;                              // what the file should hold now
    bool changed = false;                           // write it back
    std::vector<std::pair<int, std::string>> offered;  // installed keys with a kind: (kind, key), in kind order
    std::vector<std::string> noRoom;                // installed keys that got no kind (all of 7..254 given)
    std::vector<std::string> log;                   // what happened, for the DLL's log
};

// The roster: the registry (`loaded`: the file's, or nullptr when there was none or it was set aside) completed with
// the legacy kinds and a new kind for every installed key it doesn't know yet (`installed`: keys in the order their
// packages were found, each once), and which installed keys are offered.
inline RosterResult BuildRoster(const Registry* loaded, const std::vector<std::string>& installed,
                                int limit = KIND_LIMIT) {
    RosterResult r;
    Registry& reg = r.registry;
    for (int i = 0; i < LEGACY_COUNT; i++)
        reg.Add(LEGACY_KEYS[i], FIRST_EXTRA_KIND + i);
    if (loaded) {
        for (auto& k : loaded->kinds)
            if (LegacyKind(k.first) < 0)
                reg.Add(k.first, k.second);  // (ParseRegistry already kept these off the legacy kinds and each other)
        // anything the file lacked (a legacy key), or had that isn't kept: the file gets rewritten
        r.changed = loaded->kinds.size() != reg.kinds.size();
        for (size_t i = 0; !r.changed && i < reg.kinds.size(); i++)
            r.changed = loaded->kinds[i] != reg.kinds[i];
    } else {
        r.changed = true;
    }
    for (auto& key : installed) {
        if (reg.KindOf(key) >= 0)
            continue;
        int next = reg.Highest() + 1;  // (never a kind given before, even to a package that's gone)
        if (next >= limit) {
            r.noRoom.push_back(key);
            r.log.push_back(key + ": no kind left (the highest is " + std::to_string(limit - 1) +
                            "), not offered");
            continue;
        }
        reg.Add(key, next);
        r.changed = true;
        r.log.push_back(key + ": new, kind " + std::to_string(next));
    }
    for (auto& k : reg.kinds) {
        bool here = false;
        for (auto& key : installed)
            here |= key == k.first;
        if (here)
            r.offered.push_back({k.second, k.first});
    }
    return r;
}

// ---------------------------------------------------------------- the active kind in a package script
// Package scripts are kind-free, but a few places need the active extra's own kind (docs/plan-b-modular-characters.md,
// "Special stage retry": Origins reloads the special stage as Sonic, and the package's special stage player script puts
// the extra back). Such a script names ACTIVE_KIND_TOKEN (extras_gen.h, from tools/extras.py) and the DLL's file hook
// serves a copy with it replaced by the kind. `out` is `in` with every whole-word ACTIVE_KIND_TOKEN (any case: the
// engine's names ignore case; a word is letters, digits and '_') replaced by `kind` in decimal, everything else byte for
// byte the same; `count` gets how many. False (out untouched) for a kind that isn't an extra's (7..254).
inline bool SubstituteActiveKind(const std::string& in, int kind, std::string& out, int& count) {
    count = 0;
    if (kind < FIRST_EXTRA_KIND || kind >= KIND_LIMIT)
        return false;
    auto word = [](char c) { return isalnum((unsigned char)c) || c == '_'; };
    const size_t n = sizeof(ACTIVE_KIND_TOKEN) - 1;
    const std::string number = std::to_string(kind);
    std::string text;
    text.reserve(in.size());
    size_t i = 0;
    while (i < in.size()) {
        bool match = i + n <= in.size() && (i == 0 || !word(in[i - 1])) && (i + n == in.size() || !word(in[i + n]));
        for (size_t k = 0; match && k < n; k++)
            match = tolower((unsigned char)in[i + k]) == tolower((unsigned char)ACTIVE_KIND_TOKEN[k]);
        if (match) {
            text += number;
            i += n;
            count++;
        } else {
            text += in[i++];
        }
    }
    out.swap(text);
    return true;
}
