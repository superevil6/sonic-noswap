"""A small JSON Schema validator: the subset docs/character.schema.json uses (draft 2020-12 keywords type, const, enum,
required, properties, patternProperties, additionalProperties, items, min/maxItems, min/maxLength, pattern,
minimum/maximum, multipleOf, minProperties, anyOf, allOf, $ref to #/$defs). No third-party package needed; if
`jsonschema` is installed, the same file works with it too."""
import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "character.schema.json"

TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _path(p):
    return "".join(f"[{x}]" if isinstance(x, int) else f".{x}" for x in p).lstrip(".") or "(top level)"


def validate(value, schema=None):
    """[(path, message)] for every way `value` breaks the schema (empty: valid)."""
    root = schema or load_schema()
    errors = []

    def ref(s):
        while "$ref" in s:
            name = s["$ref"].split("/")[-1]
            s = {**root["$defs"][name], **{k: v for k, v in s.items() if k != "$ref"}}
        return s

    def check(v, s, p, out):
        s = ref(s)
        if "const" in s and v != s["const"]:
            out.append((p, f"must be {json.dumps(s['const'])}"))
        if "enum" in s and v not in s["enum"]:
            out.append((p, f"must be one of {', '.join(json.dumps(x) for x in s['enum'])} (is {json.dumps(v)})"))
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(TYPES[t](v) for t in types):
                out.append((p, f"must be {' or '.join(types)} (is {type(v).__name__}: {json.dumps(v)[:40]})"))
                return
        for sub in s.get("allOf", []):
            check(v, sub, p, out)
        if "anyOf" in s:
            tries = []
            for sub in s["anyOf"]:
                e = []
                check(v, sub, p, e)
                if not e:
                    break
                tries.append(e)
            else:
                best = min(tries, key=len)  # the closest alternative's complaints
                out.extend(best if len(best) <= 3 else [(p, "doesn't match any allowed form: " + "; ".join(m for _, m in best[:3]))])
        if isinstance(v, str):
            if len(v) < s.get("minLength", 0):
                out.append((p, f"must not be empty" if s["minLength"] == 1 else f"must be at least {s['minLength']} characters"))
            if "maxLength" in s and len(v) > s["maxLength"]:
                out.append((p, f"is {len(v)} characters; at most {s['maxLength']}"))
            if "pattern" in s and not re.search(s["pattern"], v):
                out.append((p, f"{json.dumps(v)} doesn't match the pattern {s['pattern']}"))
        if TYPES["number"](v):
            if "minimum" in s and v < s["minimum"]:
                out.append((p, f"must be at least {s['minimum']} (is {v})"))
            if "maximum" in s and v > s["maximum"]:
                out.append((p, f"must be at most {s['maximum']} (is {v})"))
            if "multipleOf" in s and v % s["multipleOf"]:
                out.append((p, f"must be a multiple of {s['multipleOf']} (is {v})"))
        if isinstance(v, list):
            if len(v) < s.get("minItems", 0):
                out.append((p, f"needs at least {s['minItems']} items (has {len(v)})"))
            if "maxItems" in s and len(v) > s["maxItems"]:
                out.append((p, f"has {len(v)} items; at most {s['maxItems']}"))
            if "items" in s:
                for i, x in enumerate(v):
                    check(x, s["items"], p + [i], out)
        if isinstance(v, dict):
            for k in s.get("required", []):
                if k not in v:
                    out.append((p, f"is missing \"{k}\""))
            if len(v) < s.get("minProperties", 0):
                out.append((p, f"needs at least {s['minProperties']} entries"))
            props = s.get("properties", {})
            pats = s.get("patternProperties", {})
            for k, x in v.items():
                matched = False
                if k in props:
                    check(x, props[k], p + [k], out)
                    matched = True
                for pat, sub in pats.items():
                    if re.search(pat, k):
                        check(x, sub, p + [k], out)
                        matched = True
                if not matched and s.get("additionalProperties") is False:
                    known = [n for n in props]
                    shapes = [pat for pat in pats if pat != "^_"]
                    out.append((p + [k], "is not a known key" + (f" (known: {', '.join(known)})" if known else
                                                                  f" (keys here must match {' or '.join(shapes)})" if shapes else "")))
    check(value, root, [], errors)
    return [(_path(p), m) for p, m in errors]
