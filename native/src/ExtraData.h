// Each extra's own S3&K data, read from its package's noswap_character.json (docs/plan-b-modular-characters.md step 3b
// item 7; the file is written by tools/build_packages.py). Plain C++ (no Windows headers), so a test can build it too.
//
// The file (only what this reads; anything else is ignored):
//   {"key": "noswap.charmy", "base": "tails",                  sonic / tails / knuckles: whose code runs underneath
//    "palette": {"74": "#6C0090", ...},                         its own colours: bank 0 slot -> colour, in this order
//    "roll": false, "no_roll": false,                           its own rolling curl; never rolls
//    "credit_short": "Sprites: Akimaca",                        optional: its sprite credit in Origins' select
//    "s3k": {"anim_base": 84,                                   where its own ability animations start in Extra.bin
//            "special_palette": {"216": "#FFFFFF", ...},        the Blue Spheres ball's colours
//            "abilities": {"hover": true, "hoverFrames": 60, "tipX": [..], "shotSound": null, ...}}}
//                                                               by ExtraAbilities' field names (extras_gen.h)
// Numbers may be written as JSON numbers (negative too) or as strings ("0x6000", "-12"); colours as "#RRGGBB",
// "0xRRGGBB" or a number.
#pragma once

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

#include "extras_gen.h"  // ExtraAbilities, EXTRA_ABILITY_FIELDS (tools/gen_s3k_header.py)

// ---------------------------------------------------------------- a small JSON reader
struct Json {
    enum Type { Null, Bool, Number, String, Array, Object } type = Null;
    bool b = false;
    double num = 0;
    long long integer = 0;  // exact, when the number has no fraction or exponent
    bool isInteger = false;
    std::string str;
    std::vector<Json> items;                           // Array
    std::vector<std::pair<std::string, Json>> fields;  // Object, in the file's order

    const Json* Get(const char* key) const {
        if (type != Object)
            return nullptr;
        for (auto& f : fields)
            if (f.first == key)
                return &f.second;
        return nullptr;
    }
};

class JsonParser {
public:
    // Parses the whole text (one value, whitespace around it); on failure returns false with a message
    static bool Parse(const std::string& text, Json& out, std::string& error) {
        JsonParser p(text);
        p.SkipSpace();
        if (p.pos + 3 <= text.size() && (unsigned char)text[p.pos] == 0xEF && (unsigned char)text[p.pos + 1] == 0xBB
            && (unsigned char)text[p.pos + 2] == 0xBF)
            p.pos += 3;  // a UTF-8 byte order mark
        if (!p.Value(out, 0))
            return error = p.error, false;
        p.SkipSpace();
        if (p.pos != text.size())
            return error = p.Where("text after the value"), false;
        return true;
    }

private:
    const std::string& s;
    size_t pos = 0;
    std::string error;

    explicit JsonParser(const std::string& text) : s(text) {}

    std::string Where(const char* what) {
        size_t line = 1, col = 1;
        for (size_t i = 0; i < pos && i < s.size(); i++)
            s[i] == '\n' ? (line++, col = 1) : col++;
        return std::string(what) + " at line " + std::to_string(line) + ", column " + std::to_string(col);
    }
    bool Fail(const char* what) {
        if (error.empty())
            error = Where(what);
        return false;
    }
    void SkipSpace() {
        while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\t' || s[pos] == '\n' || s[pos] == '\r'))
            pos++;
    }
    bool Literal(const char* word) {
        size_t n = strlen(word);
        if (s.compare(pos, n, word) != 0)
            return false;
        pos += n;
        return true;
    }
    bool Value(Json& v, int depth) {
        if (depth > 64)
            return Fail("nested too deeply");
        SkipSpace();
        if (pos >= s.size())
            return Fail("unexpected end");
        char c = s[pos];
        if (c == '{')
            return ObjectValue(v, depth);
        if (c == '[')
            return ArrayValue(v, depth);
        if (c == '"') {
            v.type = Json::String;
            return StringValue(v.str);
        }
        if (Literal("true"))
            return v.type = Json::Bool, v.b = true, true;
        if (Literal("false"))
            return v.type = Json::Bool, v.b = false, true;
        if (Literal("null"))
            return v.type = Json::Null, true;
        if (c == '-' || (c >= '0' && c <= '9'))
            return NumberValue(v);
        return Fail("unexpected character");
    }
    bool ObjectValue(Json& v, int depth) {
        v.type = Json::Object;
        pos++;  // {
        SkipSpace();
        if (pos < s.size() && s[pos] == '}')
            return pos++, true;
        for (;;) {
            SkipSpace();
            if (pos >= s.size() || s[pos] != '"')
                return Fail("expected a key");
            std::string key;
            if (!StringValue(key))
                return false;
            SkipSpace();
            if (pos >= s.size() || s[pos] != ':')
                return Fail("expected ':'");
            pos++;
            v.fields.emplace_back(key, Json());
            if (!Value(v.fields.back().second, depth + 1))
                return false;
            SkipSpace();
            if (pos < s.size() && s[pos] == ',') {
                pos++;
                continue;
            }
            if (pos < s.size() && s[pos] == '}')
                return pos++, true;
            return Fail("expected ',' or '}'");
        }
    }
    bool ArrayValue(Json& v, int depth) {
        v.type = Json::Array;
        pos++;  // [
        SkipSpace();
        if (pos < s.size() && s[pos] == ']')
            return pos++, true;
        for (;;) {
            v.items.emplace_back();
            if (!Value(v.items.back(), depth + 1))
                return false;
            SkipSpace();
            if (pos < s.size() && s[pos] == ',') {
                pos++;
                continue;
            }
            if (pos < s.size() && s[pos] == ']')
                return pos++, true;
            return Fail("expected ',' or ']'");
        }
    }
    static void Utf8(std::string& out, unsigned long cp) {
        if (cp < 0x80) {
            out += (char)cp;
        } else if (cp < 0x800) {
            out += (char)(0xC0 | (cp >> 6));
            out += (char)(0x80 | (cp & 0x3F));
        } else if (cp < 0x10000) {
            out += (char)(0xE0 | (cp >> 12));
            out += (char)(0x80 | ((cp >> 6) & 0x3F));
            out += (char)(0x80 | (cp & 0x3F));
        } else {
            out += (char)(0xF0 | (cp >> 18));
            out += (char)(0x80 | ((cp >> 12) & 0x3F));
            out += (char)(0x80 | ((cp >> 6) & 0x3F));
            out += (char)(0x80 | (cp & 0x3F));
        }
    }
    bool Hex4(unsigned long& cp) {
        if (pos + 4 > s.size())
            return Fail("short \\u escape");
        cp = 0;
        for (int i = 0; i < 4; i++) {
            char h = s[pos++];
            int d = h >= '0' && h <= '9' ? h - '0' : h >= 'a' && h <= 'f' ? h - 'a' + 10 : h >= 'A' && h <= 'F' ? h - 'A' + 10 : -1;
            if (d < 0)
                return Fail("bad \\u escape");
            cp = cp * 16 + d;
        }
        return true;
    }
    bool StringValue(std::string& out) {
        pos++;  // "
        while (pos < s.size()) {
            char c = s[pos++];
            if (c == '"')
                return true;
            if ((unsigned char)c < 0x20)
                return Fail("control character in a string");
            if (c != '\\') {
                out += c;
                continue;
            }
            if (pos >= s.size())
                break;
            char e = s[pos++];
            switch (e) {
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'n': out += '\n'; break;
                case 'r': out += '\r'; break;
                case 't': out += '\t'; break;
                case 'u': {
                    unsigned long cp;
                    if (!Hex4(cp))
                        return false;
                    if (cp >= 0xD800 && cp < 0xDC00) {  // a surrogate pair
                        unsigned long low;
                        if (pos + 2 > s.size() || s[pos] != '\\' || s[pos + 1] != 'u')
                            return Fail("lone surrogate");
                        pos += 2;
                        if (!Hex4(low) || low < 0xDC00 || low > 0xDFFF)
                            return Fail("bad surrogate pair");
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00);
                    }
                    Utf8(out, cp);
                    break;
                }
                default: return Fail("bad escape");
            }
        }
        return Fail("unterminated string");
    }
    bool NumberValue(Json& v) {
        size_t start = pos;
        if (s[pos] == '-')
            pos++;
        if (pos >= s.size() || !(s[pos] >= '0' && s[pos] <= '9'))
            return Fail("bad number");
        if (s[pos] == '0')
            pos++;
        else
            while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9')
                pos++;
        bool integer = true;
        if (pos < s.size() && s[pos] == '.') {
            integer = false;
            pos++;
            if (pos >= s.size() || !(s[pos] >= '0' && s[pos] <= '9'))
                return Fail("bad number");
            while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9')
                pos++;
        }
        if (pos < s.size() && (s[pos] == 'e' || s[pos] == 'E')) {
            integer = false;
            pos++;
            if (pos < s.size() && (s[pos] == '+' || s[pos] == '-'))
                pos++;
            if (pos >= s.size() || !(s[pos] >= '0' && s[pos] <= '9'))
                return Fail("bad number");
            while (pos < s.size() && s[pos] >= '0' && s[pos] <= '9')
                pos++;
        }
        std::string text = s.substr(start, pos - start);
        v.type = Json::Number;
        v.num = strtod(text.c_str(), nullptr);
        v.isInteger = integer && text.size() < 19;  // (fits a long long exactly)
        v.integer = v.isInteger ? strtoll(text.c_str(), nullptr, 10) : (long long)v.num;
        return true;
    }
};

// ---------------------------------------------------------------- the extra's shot (a real projectile)
// "s3k": {"shot": {...}} (gen_s3k_header.s3k_json, from abilities.py "shot_s3k"): Y throws a projectile, the game's own
// SuperHammer object (Amy's thrown hammer) with the package's art (3K_Players/Shot.bin: animation 0, hitbox 0 per
// frame) and this motion. Speeds in 1/65536 px per frame, offsets and radius in px. No "shot": no projectile.
// drop: falls with `gravity` (at most maxFall), no bounce: gone on the floor (Flicky's Animal Drop)
// dip: thrown down (startVY > 0) with a negative `gravity` pulling it up: it dips, levels out and rises; gone at a wall,
// floor or ceiling as a drop is, without its landing puff (Mephiles' crystal)
// ground: runs along the floor at `speed`, gripped to it (slopes too); no floor to grip (a ledge's end) or a wall: gone.
// Thrown two at once, one each way, by the Hammer Drop's landing ("input" "slam": Bark's shockwaves), never with Y
enum ShotMotion { SHOT_NONE = 0, SHOT_BOUNCE = 1, SHOT_STRAIGHT = 2, SHOT_BOOMERANG = 3, SHOT_HOMING = 4, SHOT_DROP = 5,
                  SHOT_DIP = 6, SHOT_GROUND = 7 };
struct ShotData {
    int motion = SHOT_NONE;
    int speed = 0x40000;    // forward speed (the player's own forward speed is added)
    int startVY = 0;        // vertical speed when thrown (down: positive)
    int gravity = 0;        // added to the vertical speed each frame (bounce, drop; negative for a dip)
    int bounce = 0;         // vertical speed after touching a floor (bounce: negative, up)
    int maxFall = 0x80000;  // fall speed cap
    int lifetime = 180;     // frames before it vanishes
    int maxAlive = 1;       // at most this many out at once
    int cooldown = 0;       // frames between throws
    int pose = 0;           // frames the throwing pose shows (the last frame of its shot animation)
    int x = 0, y = 0;       // where it starts, px from the player's centre (x: forward)
    int radius = 8;         // its size for terrain: floor below, wall ahead, ceiling above
    bool aim = false;       // aimed with the d-pad as Y is pressed (ground: back/up/forward and between; air: all 8;
                            // nothing held: forward), `speed` along the aim (diagonals: the same speed overall)
    bool aimDown = true;    // "aim_down": false: down never aims, in the air too (Big's cast: 5 directions everywhere)
    bool autofire = false;  // "autofire": thrown every `cooldown` frames while Y is held, not only on a press (Ray Poward's
                            // run-and-gun)
    bool aimPose = false;   // "aim_pose" (an aimed shot): the pose shows its aim's frame of the shot animation (0 level, 1
                            // forward-up, 2 up, 3 forward-down, 4 down), not the last (Ray Poward's aim poses)
    bool poseAlways = false;  // "pose_always": the pose shows at any speed on the ground (not rolling) and in the air in
                              // place of whatever showed, the jump ball too (Big's cast); what showed comes back after
    // boomerang: out ahead at `speed` (plus her own forward speed, live), slowing by `decel` per frame; when it stops it
    // homes back on her (a target speed of 1/8 of the gap per axis, at most returnSpeed, reached at returnAccel per
    // frame, plus her own velocity) and is gone within catchRadius px of her. No terrain: it passes through walls
    int decel = 0x4000, returnSpeed = 0xA0000, returnAccel = 0x4000, catchRadius = 16;
    // homing (Cream's Cheese): out ahead at `speed`; each frame it steers at the nearest live badnik on screen (the ones
    // that checked player 1 through Player_CheckBadnikTouch since its last update): per axis a target speed of 1/4 of
    // the gap, at most seekSpeed, reached at seekAccel per frame. No target for seekFrames frames in a row, or its first
    // hit: it comes back as a boomerang does (returnSpeed, returnAccel, catchRadius), hitting nothing more. Gone: the
    // cooldown starts then. No terrain
    int seekSpeed = 0x58000, seekAccel = 0x8000, seekFrames = 20;
    // "up": {...} (an unaimed bounce / straight shot): thrown with up held, it takes these instead (Bean's high throw);
    // upPose: the shot animation's frame its pose shows (-1: the last, as a normal throw)
    bool hasUp = false;
    int upSpeed = 0, upStartVY = 0, upPose = -1;
    // "ground": {...}: thrown standing on the ground, it takes these instead (Flicky's toss: from his middle, forward)
    bool hasGround = false;
    int groundX = 0, groundY = 0, groundSpeed = 0, groundStartVY = 0;
    bool cycle = false;     // each throw shows the next frame of the art, held (Flicky's critters): no animation
    bool carry = true;      // "carry": false: an unaimed shot's own speed alone, not the player's forward speed added (Jet's
                            // Tornado Trap, a slow whirlwind left behind as he runs on)
    bool aimFrames = false; // "aim_frames" (an aimed shot): its art frame is its aim's, held: 0 level, 1 forward-up, 2 up,
                            // 3 forward-down, 4 down; drawn mirrored when it flies left (Fang's cork)
    bool downOnly = false;  // "input": "down": thrown with DOWN + Y (crouching, or down held in the air), and Y alone is
                            // the melee (Mecha Sonic's spike ball and Jet Boost); down + Y in the jump ball throws, not
                            // transforms
    bool bothWays = false;  // "both_ways": each Y throw is a pair, one each way (mirror images, his own speed added to
                            // neither): Mephiles' Crystal Shot. maxAlive 2 or more
    bool onSlam = false;    // "input": "slam": thrown by the Hammer Drop's landing, two at once (one each way), not with Y
                            // (Y stays the melee: Bark's shockwaves and Bear Rush)
    bool onGrab = false;    // "input": "grab": thrown by Psychokinesis (PsychoGrab.h) with a caught badnik's likeness, not
                            // with Y (Y stays the melee when nothing is caught: Silver's Psychic Wave)
    bool onCharge = false;  // "input": "charge" (a second shot): Y held charges it; letting go once it has been held
                            // chargeFull frames throws it (Mega Man's Charge Shot; its flash from chargeStart frames)
    int chargeStart = 30, chargeFull = 72;
    bool chargeWait = false;  // "charge_wait": the charge can't be full while the (shared) cooldown runs: it holds one frame
                              // short until it's over, so full charges are at least the cooldown apart (Omega's Flame Blast)
    bool pierce = false;    // "pierce": a hit doesn't end it, it flies on through (Mega Man's Charge Shot)
    bool upOnly = false;    // "input": "up": thrown with UP + Y (in the air up and a side held is the whip's instead, with
                            // the melee's whip poses), and Y alone is the melee (John Morris' sub-weapons and whip)
    int rings = 0;          // "rings": each throw costs this many rings; fewer: no throw ("rings are hearts": John's)
    bool terrain = true;    // "terrain": false: walls, floors and ceilings don't end it (John's axe)
    int burnAnim = -1;      // "burn_anim" (a drop): landing, it stays there burning in this Shot.bin animation for
    int burnLifetime = 0;   // "burn_lifetime" frames, hurting whatever touches it (John's Holy Water); -1: gone on the floor
    std::string sound;      // S3&K sound file (Data/SoundFX), empty: none
};

// ---------------------------------------------------------------- the extra's data
struct ExtraData {
    bool loaded = false;  // from a package (false: none installed, or its file wasn't usable)
    std::string key, name;
    std::string creditShort;  // "credit_short": its sprite credit under Origins' select cards ("": none)
    std::vector<std::string> ownSounds;  // "own_sounds": its own sounds Sonic 1/2/CD ask for by number, in order
                                         // ("NoSwap/<id>/<name>.wav", Data/SoundFX paths; tools/own_sounds.py)
    int base = 0;         // 0 Sonic, 1 Tails, 2 Knuckles
    int animBase = 77;    // its own ability animations' first ID (build_s3k_art.py)
    bool roll = false, noRoll = false;
    std::vector<PaletteColour> palette, specialPalette;
    std::vector<PaletteColour> chargePalettes[3];  // "s3k.charge_palettes": a charge shot's flash colours (charge1, charge2a,
                                                   // charge2b: Mega Man's), bank 0 slot -> colour
    ExtraAbilities abilities{};
    ShotData shot;                      // its projectile (shot.motion SHOT_NONE: none)
    ShotData shot2;                     // a second one, thrown with down + Y ("s3k.shot2": Robotnik's Bomb Drop; its
                                        // downOnly set; shot then takes Y alone). Shot.bin's animation 1
    std::vector<ShotData> swapShots;    // "s3k.swap_shots" (monitor_swap: John's sub-weapons): the one thrown is the one at
                                        // the swap index (tools/monitor_swap.py; Shot.bin's animation k is entry k's)
    std::vector<std::string> warnings;  // what the loader fixed or ignored

    ExtraData() { SetDefaults(); }
    void SetDefaults();
};

enum ExtraFieldType { FT_bool, FT_int, FT_str };
struct ExtraField {
    const char* name;
    size_t offset;
    ExtraFieldType type;
    int count;
};
#define EXTRA_FIELD_ENTRY(type, name, count, def) {#name, offsetof(ExtraAbilities, name), FT_##type, count},
static const ExtraField EXTRA_FIELDS[] = {EXTRA_ABILITY_FIELDS(EXTRA_FIELD_ENTRY)};
#undef EXTRA_FIELD_ENTRY
constexpr size_t EXTRA_FIELD_COUNT = sizeof(EXTRA_FIELDS) / sizeof(EXTRA_FIELDS[0]);

template <class T, class V>
inline void ExtraSetDefault(T& field, V value) { field = value; }
template <class V, size_t N>
inline void ExtraSetDefault(int (&field)[N], V value) {
    for (int& x : field)
        x = value;
}
inline void ExtraData::SetDefaults() {  // (extras_gen.h's defaults: an extra with no moves)
#define EXTRA_FIELD_DEFAULT(type, name, count, def) ExtraSetDefault(abilities.name, def);
    EXTRA_ABILITY_FIELDS(EXTRA_FIELD_DEFAULT)
#undef EXTRA_FIELD_DEFAULT
}

// A number from a JSON number or a string ("0x6000", "-12", "#6C0090")
inline bool JsonInt(const Json* v, long long& out) {
    if (!v)
        return false;
    if (v->type == Json::Number) {
        out = v->isInteger ? v->integer : (long long)(v->num < 0 ? v->num - 0.5 : v->num + 0.5);
        return true;
    }
    if (v->type != Json::String || v->str.empty())
        return false;
    const char* t = v->str.c_str();
    int base = 10;
    bool negative = *t == '-';
    if (negative)
        t++;
    if (*t == '#') {
        t++, base = 16;
    } else if (t[0] == '0' && (t[1] == 'x' || t[1] == 'X')) {
        t += 2, base = 16;
    }
    if (!*t)
        return false;
    char* end = nullptr;
    long long n = strtoll(t, &end, base);
    if (*end)
        return false;
    out = negative ? -n : n;
    return true;
}

inline bool ReadPalette(const Json* v, const char* what, std::vector<PaletteColour>& out, std::vector<std::string>& warn) {
    out.clear();
    if (!v || v->type == Json::Null)
        return true;
    if (v->type != Json::Object)
        return warn.push_back(std::string(what) + ": not an object"), false;
    for (auto& f : v->fields) {
        Json key;
        key.type = Json::String, key.str = f.first;
        long long slot, rgb;
        if (!JsonInt(&key, slot) || slot < 0 || slot > 255 || !JsonInt(&f.second, rgb) || rgb < 0 || rgb > 0xFFFFFF) {
            warn.push_back(std::string(what) + ": bad entry \"" + f.first + "\", left out");
            continue;
        }
        out.push_back({(unsigned char)slot, (unsigned int)rgb});
    }
    return true;
}

// "s3k.shot" (ShotData above); absent or null: no projectile. A bad field keeps its default (warned); an unknown motion
// means no projectile.
inline void ReadShot(const Json* v, ShotData& out, std::vector<std::string>& warn) {
    out = ShotData();
    if (!v || v->type == Json::Null)
        return;
    if (v->type != Json::Object)
        return warn.push_back("s3k.shot: not an object, no shot");
    const Json* m = v->Get("motion");
    static const char* const NAMES[] = {"none", "bounce", "straight", "boomerang", "homing", "drop", "dip", "ground"};
    int motion = -1;
    for (int i = 0; i < 8; i++)
        if (m && m->type == Json::String && m->str == NAMES[i])
            motion = i;
    if (motion < 0)
        return warn.push_back("s3k.shot.motion: not bounce / straight / boomerang / homing / drop / dip / ground, no shot");
    const struct { const char* name; int* at; long long lo, hi; } INTS[] = {
        {"speed", &out.speed, 0, 0x200000}, {"start_vy", &out.startVY, -0x200000, 0x200000},
        {"gravity", &out.gravity, -0x20000, 0x20000}, {"bounce", &out.bounce, -0x200000, 0},
        {"max_fall", &out.maxFall, 0, 0x200000}, {"lifetime", &out.lifetime, 1, 3600},
        {"max_alive", &out.maxAlive, 1, 8}, {"cooldown", &out.cooldown, 0, 600}, {"pose", &out.pose, 0, 120},
        {"x", &out.x, -64, 64}, {"y", &out.y, -64, 64}, {"radius", &out.radius, 1, 32},
        {"decel", &out.decel, 1, 0x100000}, {"return_speed", &out.returnSpeed, 0x1000, 0x200000},
        {"return_accel", &out.returnAccel, 1, 0x100000}, {"catch", &out.catchRadius, 1, 64},
        {"seek_speed", &out.seekSpeed, 0x1000, 0x200000}, {"seek_accel", &out.seekAccel, 1, 0x100000},
        {"seek_frames", &out.seekFrames, 1, 600}, {"charge_start", &out.chargeStart, 1, 3600},
        {"charge_full", &out.chargeFull, 1, 3600}, {"rings", &out.rings, 0, 99}, {"burn_anim", &out.burnAnim, 0, 63},
        {"burn_lifetime", &out.burnLifetime, 1, 3600}};
    for (auto& f : INTS) {
        const Json* n = v->Get(f.name);
        long long x;
        if (!n)
            continue;
        if (JsonInt(n, x) && x >= f.lo && x <= f.hi)
            *f.at = (int)x;
        else
            warn.push_back(std::string("s3k.shot.") + f.name + ": wrong type or out of range, default kept");
    }
    const Json* up = v->Get("up");
    if (up && up->type == Json::Object) {
        out.hasUp = true;
        out.upSpeed = out.speed;
        out.upStartVY = out.startVY;
        const struct { const char* name; int* at; long long lo, hi; } UPS[] = {
            {"speed", &out.upSpeed, 0, 0x200000}, {"start_vy", &out.upStartVY, -0x200000, 0x200000},
            {"pose_frame", &out.upPose, 0, 255}};
        for (auto& f : UPS) {
            const Json* n = up->Get(f.name);
            long long x;
            if (!n)
                continue;
            if (JsonInt(n, x) && x >= f.lo && x <= f.hi)
                *f.at = (int)x;
            else
                warn.push_back(std::string("s3k.shot.up.") + f.name + ": wrong type or out of range, default kept");
        }
    } else if (up && up->type != Json::Null)
        warn.push_back("s3k.shot.up: not an object, ignored");
    const Json* gr = v->Get("ground");
    if (gr && gr->type == Json::Object) {
        out.hasGround = true;
        out.groundX = out.x;
        out.groundY = out.y;
        out.groundSpeed = out.speed;
        out.groundStartVY = out.startVY;
        const struct { const char* name; int* at; long long lo, hi; } GROUNDS[] = {
            {"x", &out.groundX, -64, 64}, {"y", &out.groundY, -64, 64}, {"speed", &out.groundSpeed, 0, 0x200000},
            {"start_vy", &out.groundStartVY, -0x200000, 0x200000}};
        for (auto& f : GROUNDS) {
            const Json* n = gr->Get(f.name);
            long long x;
            if (!n)
                continue;
            if (JsonInt(n, x) && x >= f.lo && x <= f.hi)
                *f.at = (int)x;
            else
                warn.push_back(std::string("s3k.shot.ground.") + f.name + ": wrong type or out of range, default kept");
        }
    } else if (gr && gr->type != Json::Null)
        warn.push_back("s3k.shot.ground: not an object, ignored");
    const Json* ca = v->Get("carry");
    if (ca && ca->type == Json::Bool)
        out.carry = ca->b;
    else if (ca && ca->type != Json::Null)
        warn.push_back("s3k.shot.carry: not true / false, the player's speed added");
    const Json* cy = v->Get("cycle");
    if (cy && cy->type == Json::Bool)
        out.cycle = cy->b;
    else if (cy && cy->type != Json::Null)
        warn.push_back("s3k.shot.cycle: not true / false, not cycled");
    const Json* af = v->Get("aim_frames");
    if (af && af->type == Json::Bool)
        out.aimFrames = af->b;
    else if (af && af->type != Json::Null)
        warn.push_back("s3k.shot.aim_frames: not true / false, animated");
    const Json* bw = v->Get("both_ways");
    if (bw && bw->type == Json::Bool)
        out.bothWays = bw->b;
    else if (bw && bw->type != Json::Null)
        warn.push_back("s3k.shot.both_ways: not true / false, one way");
    const Json* in = v->Get("input");
    if (in && in->type == Json::String
        && (in->str == "down" || in->str == "y" || in->str == "slam" || in->str == "charge" || in->str == "up"
            || in->str == "grab")) {
        out.downOnly = in->str == "down";
        out.onSlam = in->str == "slam";
        out.onGrab = in->str == "grab";
        out.onCharge = in->str == "charge";
        out.upOnly = in->str == "up";
    } else if (in && in->type != Json::Null)
        warn.push_back("s3k.shot.input: not \"down\" / \"y\" / \"slam\" / \"charge\" / \"up\" / \"grab\", thrown with Y");
    const Json* te = v->Get("terrain");
    if (te && te->type == Json::Bool)
        out.terrain = te->b;
    else if (te && te->type != Json::Null)
        warn.push_back("s3k.shot.terrain: not true / false, walls and floors end it");
    const Json* cw = v->Get("charge_wait");
    if (cw && cw->type == Json::Bool)
        out.chargeWait = cw->b;
    else if (cw && cw->type != Json::Null)
        warn.push_back("s3k.shot.charge_wait: not true / false, full whatever the cooldown");
    const Json* pi = v->Get("pierce");
    if (pi && pi->type == Json::Bool)
        out.pierce = pi->b;
    else if (pi && pi->type != Json::Null)
        warn.push_back("s3k.shot.pierce: not true / false, gone at its first hit");
    const Json* a = v->Get("aim");
    if (a && a->type == Json::Bool)
        out.aim = a->b;
    else if (a && a->type != Json::Null)
        warn.push_back("s3k.shot.aim: not true / false, not aimed");
    const Json* ad = v->Get("aim_down");
    if (ad && ad->type == Json::Bool)
        out.aimDown = ad->b;
    else if (ad && ad->type != Json::Null)
        warn.push_back("s3k.shot.aim_down: not true / false, down aims in the air");
    const Json* afi = v->Get("autofire");
    if (afi && afi->type == Json::Bool)
        out.autofire = afi->b;
    else if (afi && afi->type != Json::Null)
        warn.push_back("s3k.shot.autofire: not true / false, thrown on a press");
    const Json* ap = v->Get("aim_pose");
    if (ap && ap->type == Json::Bool)
        out.aimPose = ap->b;
    else if (ap && ap->type != Json::Null)
        warn.push_back("s3k.shot.aim_pose: not true / false, the pose's last frame");
    const Json* pa = v->Get("pose_always");
    if (pa && pa->type == Json::Bool)
        out.poseAlways = pa->b;
    else if (pa && pa->type != Json::Null)
        warn.push_back("s3k.shot.pose_always: not true / false, the pose only standing or in the jump");
    const Json* s = v->Get("sound");
    if (s && s->type == Json::String)
        out.sound = s->str;
    else if (s && s->type != Json::Null)
        warn.push_back("s3k.shot.sound: not a string, none");
    out.motion = motion;
}

// Reads one noswap_character.json. Returns false (with `error`) if it can't be used at all; smaller problems (a bad
// field, an unknown one) go in data.warnings and the field keeps its default.
inline bool LoadExtraData(const std::string& text, ExtraData& data, std::string& error) {
    data = ExtraData();
    Json root;
    if (!JsonParser::Parse(text, root, error))
        return false;
    if (root.type != Json::Object)
        return error = "not a JSON object", false;
    const Json* key = root.Get("key");
    if (!key || key->type != Json::String || key->str.empty())
        return error = "no \"key\"", false;
    data.key = key->str;
    if (const Json* n = root.Get("name"))
        if (n->type == Json::String)
            data.name = n->str;
    if (const Json* c = root.Get("credit_short"))
        if (c->type == Json::String)
            data.creditShort = c->str;
    if (const Json* own = root.Get("own_sounds"))  // (read before "s3k": Sonic 1/2/CD need them without it)
        if (own->type == Json::Array && own->items.size() <= 8)
            for (const Json& s : own->items)
                if (s.type == Json::String && s.str.compare(0, 7, "NoSwap/") == 0 && s.str.size() < 64
                    && s.str.find("..") == std::string::npos)
                    data.ownSounds.push_back(s.str);
                else
                    data.ownSounds.push_back("");  // (unusable: that sound's number stays silent, its place kept)
    const Json* s3k = root.Get("s3k");
    if (!s3k || s3k->type != Json::Object)
        return error = "no \"s3k\" data (a package built before S3&K's data moved to packages?)", false;
    std::vector<std::string>& warn = data.warnings;

    const Json* base = root.Get("base");
    if (base && base->type == Json::String) {
        if (base->str == "sonic")
            data.base = 0;
        else if (base->str == "tails")
            data.base = 1;
        else if (base->str == "knuckles")
            data.base = 2;
        else
            warn.push_back("base \"" + base->str + "\" unknown: sonic");
    } else {
        warn.push_back("no base: sonic");
    }
    static const int ANIM_BASE_OF[] = {77, 84, 78};  // (build_s3k_art.py: after the base file's own animations)
    long long n;
    data.animBase = ANIM_BASE_OF[data.base];
    if (JsonInt(s3k->Get("anim_base"), n) && n >= 0 && n < 1000)
        data.animBase = (int)n;
    else
        warn.push_back("no s3k.anim_base: its base's");
    for (auto flag : {std::make_pair("roll", &data.roll), std::make_pair("no_roll", &data.noRoll)}) {
        const Json* f = root.Get(flag.first);
        if (f && f->type == Json::Bool)
            *flag.second = f->b;
        else if (f && f->type != Json::Null)
            warn.push_back(std::string(flag.first) + ": not true / false");
    }
    ReadPalette(root.Get("palette"), "palette", data.palette, warn);
    ReadPalette(s3k->Get("special_palette"), "s3k.special_palette", data.specialPalette, warn);
    ReadShot(s3k->Get("shot"), data.shot, warn);
    ReadShot(s3k->Get("shot2"), data.shot2, warn);
    if (const Json* sw = s3k->Get("swap_shots")) {  // (monitor_swap's shots: John's sub-weapons; none: an empty list)
        if (sw->type == Json::Array && sw->items.size() <= 8) {
            for (const Json& item : sw->items) {
                ShotData s;
                ReadShot(&item, s, warn);
                if (s.motion == SHOT_NONE || s.motion == SHOT_HOMING || s.motion == SHOT_GROUND || s.aim) {
                    warn.push_back("s3k.swap_shots: an entry isn't a plain shot (none, homing, ground or aimed): no swap shots");
                    data.swapShots.clear();
                    break;
                }
                data.swapShots.push_back(s);
            }
        } else if (sw->type != Json::Null)
            warn.push_back("s3k.swap_shots: not a list of at most 8 shots, ignored");
    }
    if (const Json* cp = s3k->Get("charge_palettes")) {
        if (cp->type == Json::Array && cp->items.size() == 3)
            for (int k = 0; k < 3; k++)
                ReadPalette(&cp->items[k], "s3k.charge_palettes", data.chargePalettes[k], warn);
        else if (cp->type != Json::Null)
            warn.push_back("s3k.charge_palettes: not a list of 3 palettes, no flash");
    }
    if (data.shot.motion != SHOT_NONE && (data.shot.motion == SHOT_GROUND) != data.shot.onSlam) {
        warn.push_back("s3k.shot: a \"ground\" shot goes with \"input\" \"slam\" and only it: no shot");
        data.shot = ShotData();
    }
    if (data.shot2.motion != SHOT_NONE && (!(data.shot2.downOnly || data.shot2.onCharge) || data.shot.motion == SHOT_NONE
                                           || data.shot.downOnly
                                           || data.shot2.aim || data.shot2.motion == SHOT_BOOMERANG
                                           || data.shot2.motion == SHOT_HOMING)) {
        warn.push_back("s3k.shot2: needs \"input\" \"down\" or \"charge\", a \"shot\" on Y alone, and no aim or boomerang: "
                       "no second shot");
        data.shot2 = ShotData();
    }

    const Json* ab = s3k->Get("abilities");
    if (!ab || ab->type != Json::Object) {
        warn.push_back("no s3k.abilities: no moves");
        return data.loaded = true, true;
    }
    int missing = 0;
    for (const ExtraField& f : EXTRA_FIELDS) {
        const Json* v = ab->Get(f.name);
        char* at = (char*)&data.abilities + f.offset;
        if (!v) {
            missing++;
            continue;
        }
        bool ok = true;
        if (f.type == FT_bool) {
            ok = v->type == Json::Bool;
            if (ok)
                *(bool*)at = v->b;
        } else if (f.type == FT_int && f.count == 1) {
            ok = JsonInt(v, n) && n >= INT32_MIN && n <= INT32_MAX;
            if (ok)
                *(int*)at = (int)n;
        } else if (f.type == FT_int) {  // an array: up to count numbers, the rest 0
            ok = v->type == Json::Array && (int)v->items.size() <= f.count;
            for (size_t i = 0; ok && i < v->items.size(); i++)
                ok = JsonInt(&v->items[i], n) && n >= INT32_MIN && n <= INT32_MAX;
            if (ok)
                for (int i = 0; i < f.count; i++)
                    ((int*)at)[i] = i < (int)v->items.size() ? (int)(JsonInt(&v->items[i], n), n) : 0;
        } else {  // a string, or null for none (kept for good: the DLL never unloads a package)
            ok = v->type == Json::String || v->type == Json::Null;
            if (ok && v->type == Json::String) {
                char* copy = new char[v->str.size() + 1];
                memcpy(copy, v->str.c_str(), v->str.size() + 1);
                *(const char**)at = copy;
            } else if (ok) {
                *(const char**)at = nullptr;
            }
        }
        if (!ok)
            warn.push_back(std::string("s3k.abilities.") + f.name + ": wrong type or out of range, default kept");
    }
    if (missing)
        warn.push_back(std::to_string(missing) + " of the DLL's ability fields not in the file: their defaults");
    for (auto& field : ab->fields) {
        bool known = false;
        for (const ExtraField& f : EXTRA_FIELDS)
            known |= field.first == f.name;
        if (!known)
            warn.push_back("s3k.abilities." + field.first + ": this DLL has no such field (a newer move?), ignored");
    }
    // Numbers the move code divides by or indexes with
    ExtraAbilities& a = data.abilities;
    for (int* t : {&a.shotTicks, &a.blastTicks, &a.spiritTicks, &a.snapFrames})
        if (*t < 1) {
            warn.push_back("a tick / frame count below 1: 1");
            *t = 1;
        }
    if (a.grappleFrames < 0 || a.grappleFrames > 8) {
        warn.push_back("grappleFrames out of 0-8: clamped");
        a.grappleFrames = a.grappleFrames < 0 ? 0 : 8;
    }
    data.loaded = true;
    return true;
}

// ---------------------------------------------------------------- the save screen picture
// A package's 3K_Players/MenuPicture.bin (extras.S3K_MENU_PICTURE, a v5 "SPR" sprite file: "SPR\0", u32 frame count,
// u8 sheet count, then each sheet as u8 length incl. NUL + name) names exactly one sheet, 3K_Players/MenuPicture.gif.
// The DLL gives each extra's picture its own numbered name for the session: this is that .bin with its sheet renamed
// to `sheet` (3K_Players/MenuPicture<j>.gif), everything after the name byte for byte the same. False (and why) if the
// file isn't that shape.
static bool RenameMenuSheet(const std::string& in, const std::string& sheet, std::string& out, std::string& why) {
    static const char EXPECTED[] = "3K_Players/MenuPicture.gif";
    if (in.size() < 10 || in.compare(0, 4, std::string("SPR\0", 4)) != 0) {
        why = "not a v5 sprite file";
        return false;
    }
    if ((unsigned char)in[8] != 1) {
        why = "it must name exactly one sheet";
        return false;
    }
    size_t len = (unsigned char)in[9];
    if (len == 0 || 10 + len > in.size() || in[9 + len] != '\0') {
        why = "its sheet name is cut short";
        return false;
    }
    std::string old = in.substr(10, len - 1);
    bool same = old.size() == sizeof(EXPECTED) - 1;
    for (size_t i = 0; same && i < old.size(); i++)  // (names ignore case in the engine)
        same = tolower((unsigned char)old[i]) == tolower((unsigned char)EXPECTED[i]);
    if (!same) {
        why = "it names " + old + ", not " + EXPECTED;
        return false;
    }
    if (sheet.empty() || sheet.size() + 1 > 255) {
        why = "bad new sheet name";
        return false;
    }
    out = in.substr(0, 9);
    out += (char)(sheet.size() + 1);
    out += sheet;
    out += '\0';
    out += in.substr(10 + len);
    return true;
}
