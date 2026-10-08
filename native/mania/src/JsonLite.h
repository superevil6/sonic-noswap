// JsonLite: a small JSON reader for NoSwapMania's character files (noswap_character.json). Header-only C: parse a whole
// file into a tree, look values up by key, free it. Numbers are kept as doubles (the files' are integers well inside
// 2^53); strings are UTF-8 with the usual escapes (\uXXXX below 0x80 kept, others become '?': names are ASCII).
// A malformed file gives NULL (and its line in *errorLine), never a crash.
#ifndef JSON_LITE_H
#define JSON_LITE_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum { JSON_NULL, JSON_BOOL, JSON_NUMBER, JSON_STRING, JSON_ARRAY, JSON_OBJECT } JsonType;

typedef struct JsonNode JsonNode;
struct JsonNode {
    JsonType type;
    char *key;        // (in an object: this member's name)
    char *string;     // JSON_STRING
    double number;    // JSON_NUMBER, JSON_BOOL (0 / 1)
    JsonNode *child;  // JSON_ARRAY / JSON_OBJECT: the first element or member
    JsonNode *next;   // the next element or member
    int count;        // JSON_ARRAY / JSON_OBJECT: how many
};

typedef struct {
    const char *at, *end;
    int line, depth, failed;
} JsonParser;

static void Json_Free(JsonNode *node)
{
    while (node) {
        JsonNode *next = node->next;
        Json_Free(node->child);
        free(node->key);
        free(node->string);
        free(node);
        node = next;
    }
}

static void Json_Skip(JsonParser *p)
{
    while (p->at < p->end && (*p->at == ' ' || *p->at == '\t' || *p->at == '\r' || *p->at == '\n')) {
        if (*p->at == '\n')
            ++p->line;
        ++p->at;
    }
}

static char *Json_ReadString(JsonParser *p)
{
    if (p->at >= p->end || *p->at != '"') {
        p->failed = 1;
        return NULL;
    }
    ++p->at;
    size_t cap = 32, len = 0;
    char *out = (char *)malloc(cap);
    while (out && p->at < p->end && *p->at != '"') {
        char c = *p->at++;
        if (c == '\\' && p->at < p->end) {
            char e = *p->at++;
            switch (e) {
                case 'n': c = '\n'; break;
                case 't': c = '\t'; break;
                case 'r': c = '\r'; break;
                case 'b': c = '\b'; break;
                case 'f': c = '\f'; break;
                case 'u': {
                    unsigned v = 0;
                    for (int i = 0; i < 4 && p->at < p->end; ++i, ++p->at) {
                        char h = *p->at;
                        v = v * 16 + (unsigned)(h >= '0' && h <= '9' ? h - '0' : h >= 'a' && h <= 'f' ? h - 'a' + 10 : h >= 'A' && h <= 'F' ? h - 'A' + 10 : 0);
                    }
                    c = v < 0x80 ? (char)v : '?';
                    break;
                }
                default: c = e; break; // (\" \\ \/)
            }
        }
        if (len + 2 > cap) {
            char *grown = (char *)realloc(out, cap *= 2);
            if (!grown) {
                free(out);
                out = NULL;
                break;
            }
            out = grown;
        }
        out[len++] = c;
    }
    if (!out || p->at >= p->end) {
        free(out);
        p->failed = 1;
        return NULL;
    }
    ++p->at; // (the closing quote)
    out[len] = 0;
    return out;
}

static JsonNode *Json_ReadValue(JsonParser *p);

static JsonNode *Json_ReadList(JsonParser *p, int object)
{
    JsonNode *node = (JsonNode *)calloc(1, sizeof(JsonNode)), **tail;
    if (!node) {
        p->failed = 1;
        return NULL;
    }
    node->type = object ? JSON_OBJECT : JSON_ARRAY;
    tail       = &node->child;
    ++p->at; // ('{' or '[')
    Json_Skip(p);
    if (p->at < p->end && *p->at == (object ? '}' : ']')) {
        ++p->at;
        return node;
    }
    while (!p->failed) {
        char *key = NULL;
        if (object) {
            Json_Skip(p);
            key = Json_ReadString(p);
            Json_Skip(p);
            if (!key || p->at >= p->end || *p->at != ':') {
                free(key);
                p->failed = 1;
                break;
            }
            ++p->at;
        }
        JsonNode *value = Json_ReadValue(p);
        if (!value) {
            free(key);
            break;
        }
        value->key = key;
        *tail      = value;
        tail       = &value->next;
        node->count++;
        Json_Skip(p);
        if (p->at < p->end && *p->at == ',') {
            ++p->at;
            continue;
        }
        if (p->at < p->end && *p->at == (object ? '}' : ']')) {
            ++p->at;
            return node;
        }
        p->failed = 1;
    }
    Json_Free(node);
    return NULL;
}

static JsonNode *Json_ReadValue(JsonParser *p)
{
    Json_Skip(p);
    if (p->at >= p->end || ++p->depth > 64) {
        p->failed = 1;
        return NULL;
    }
    JsonNode *node = NULL;
    char c         = *p->at;
    if (c == '{' || c == '[') {
        node = Json_ReadList(p, c == '{');
    }
    else if (c == '"') {
        char *s = Json_ReadString(p);
        if (s && (node = (JsonNode *)calloc(1, sizeof(JsonNode)))) {
            node->type   = JSON_STRING;
            node->string = s;
        }
        else {
            free(s);
        }
    }
    else {
        static const struct { const char *word; JsonType type; double value; } words[] = {
            { "true", JSON_BOOL, 1 }, { "false", JSON_BOOL, 0 }, { "null", JSON_NULL, 0 }
        };
        for (int i = 0; i < 3 && !node; ++i) {
            size_t n = strlen(words[i].word);
            if ((size_t)(p->end - p->at) >= n && memcmp(p->at, words[i].word, n) == 0) {
                p->at += n;
                if ((node = (JsonNode *)calloc(1, sizeof(JsonNode)))) {
                    node->type   = words[i].type;
                    node->number = words[i].value;
                }
            }
        }
        if (!node && (c == '-' || (c >= '0' && c <= '9'))) {
            char buf[64];
            size_t n = 0;
            while (p->at < p->end && n < sizeof(buf) - 1 && strchr("+-0123456789.eE", *p->at)) buf[n++] = *p->at++;
            buf[n] = 0;
            if ((node = (JsonNode *)calloc(1, sizeof(JsonNode)))) {
                node->type   = JSON_NUMBER;
                node->number = strtod(buf, NULL);
            }
        }
    }
    if (!node)
        p->failed = 1;
    --p->depth;
    return node;
}

// The whole text; NULL on an error (its line in *errorLine, if given)
static JsonNode *Json_Parse(const char *text, size_t length, int *errorLine)
{
    JsonParser p = { text, text + length, 1, 0, 0 };
    JsonNode *root = Json_ReadValue(&p);
    Json_Skip(&p);
    if (root && (p.failed || p.at != p.end)) {
        Json_Free(root);
        root = NULL;
    }
    if (!root && errorLine)
        *errorLine = p.line;
    return root;
}

// A file (NULL: can't be read or isn't JSON)
static JsonNode *Json_ParseFile(const char *path, int *errorLine)
{
    if (errorLine)
        *errorLine = 0;
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    JsonNode *root = NULL;
    char *text     = size >= 0 && size < (1 << 24) ? (char *)malloc((size_t)size + 1) : NULL;
    if (text && fread(text, 1, (size_t)size, f) == (size_t)size)
        root = Json_Parse(text, (size_t)size, errorLine);
    free(text);
    fclose(f);
    return root;
}

static JsonNode *Json_Get(const JsonNode *object, const char *key)
{
    if (!object || object->type != JSON_OBJECT)
        return NULL;
    for (JsonNode *n = object->child; n; n = n->next)
        if (n->key && strcmp(n->key, key) == 0)
            return n;
    return NULL;
}

static int Json_Int(const JsonNode *node, int fallback)
{
    return node && (node->type == JSON_NUMBER || node->type == JSON_BOOL) ? (int)node->number : fallback;
}

static const char *Json_String(const JsonNode *node, const char *fallback)
{
    return node && node->type == JSON_STRING ? node->string : fallback;
}

// "#RRGGBB" -> 0xRRGGBB (-1: not a colour)
static int Json_Colour(const JsonNode *node)
{
    const char *s = Json_String(node, NULL);
    if (!s || s[0] != '#' || strlen(s) != 7)
        return -1;
    char *end = NULL;
    long v    = strtol(s + 1, &end, 16);
    return end && *end == 0 ? (int)v : -1;
}

#endif
