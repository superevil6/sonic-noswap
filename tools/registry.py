#!/usr/bin/env python3
"""NoSwap's character registry (data/registry.json): every character's permanent build numbers, by key.

A character is known by its key, "<creator>.<character>" (NoSwap's own are "noswap.<art folder>"; a character.json
gives it as "key"). The registry gives each key a number n, once and for good:
  - its build ID is 6 + n (alias PLAYER_EXTRA<n>_A): a row number inside its own package's S1/S2/CD scripts;
  - its art files are Extra<n>.ani, Extra<n>_<k>.gif...;
  - the Mania save select sorts packages by it ("order").
Numbers are build-time only and local to one build tree: the games number installed packages themselves, by key (the
S3&K DLL's roster.json gives Origins kinds; Mania stores its save slots' picks by package folder), so two strangers'
characters with the same n never clash in a player's game. Keys must be unique; numbers just must not move.

Rules (saves never break):
  - today's characters keep the numbers their place in tools/extras.py gave them (frozen in the file, 1..43);
  - a key the file doesn't know gets the highest number ever given + 1 and is written to the file at once;
  - a number is never reused: a character that's gone stays in the file (move it to "retired" by hand if wanted).

Usage: registry.py                 (list the registry)
       registry.py --forget KEY    (remove a key that was never released, e.g. a test character; its number may be
                                    given again. Never do this to a released character.)
"""
import os
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILE = REPO / "data" / "registry.json"
FORMAT = "noswap-registry/1"
KEY = re.compile(r"^[a-z0-9][a-z0-9_-]*\.[a-z0-9][a-z0-9_.-]*$")
NOTE = ("NoSwap's character build numbers, by key (tools/registry.py). n gives the build ID (6 + n), the art's "
        "Extra<n> file names and the Mania save select order. Given once, never changed or reused: don't edit by hand.")


def valid_key(key):
    return bool(KEY.match(key or ""))


def load():
    if not FILE.exists():
        return {"format": FORMAT, "note": NOTE, "characters": {}, "retired": {}}
    data = json.loads(FILE.read_text())
    if data.get("format") != FORMAT:
        raise SystemExit(f"{FILE}: \"format\" must be \"{FORMAT}\"")
    data.setdefault("retired", {})
    return data


def save(data):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=1) + "\n")


def _highest(data):
    return max([v["n"] for v in data["characters"].values()] + [v["n"] for v in data["retired"].values()] + [0])


def check(data):
    seen = {}
    for key, v in list(data["characters"].items()) + list(data["retired"].items()):
        if not valid_key(key):
            raise SystemExit(f"{FILE}: {key!r} isn't a key (<creator>.<character>, lower case)")
        if v["n"] in seen:
            raise SystemExit(f"{FILE}: {key} and {seen[v['n']]} both have number {v['n']}")
        seen[v["n"]] = key


def numbers(wanted):
    """{key: n} for `wanted` [(key, folder)]: each key's registered number; keys the file doesn't know get new ones
    (in the order given) and the file is written. Stops on a key given twice or a malformed key. With
    $NOSWAP_REGISTRY_READONLY set (noswap check / preview / ui / dry runs) new keys get provisional numbers and nothing is
    written: only a real build registers a character."""
    readonly = bool(os.environ.get("NOSWAP_REGISTRY_READONLY"))
    data = load()
    check(data)
    keys = [k for k, _ in wanted]
    for k in keys:
        if not valid_key(k):
            raise SystemExit(f"character key {k!r}: it must be <creator>.<character> in lower case letters, digits, "
                             "'-' and '_' (e.g. \"noswap.bean\", \"someone.newchar\")")
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        raise SystemExit(f"two characters have the same key: {dup} (give one a different \"key\" in its character.json)")
    changed = False
    for key, folder in wanted:
        if key in data["retired"]:
            raise SystemExit(f"{key} is retired in {FILE}: give the character a new key")
        if key not in data["characters"]:
            data["characters"][key] = {"n": _highest(data) + 1, "folder": folder}
            if readonly:
                continue
            print(f"registry: new character {key} (folder {folder}): number {data['characters'][key]['n']}, "
                  f"build ID {6 + data['characters'][key]['n']}", file=sys.stderr)
            changed = True
    if changed:
        save(data)
    return {k: data["characters"][k]["n"] for k in keys}


def forget(key):
    data = load()
    if key not in data["characters"]:
        raise SystemExit(f"{key} isn't in {FILE}")
    del data["characters"][key]
    save(data)
    print(f"forgot {key}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--forget"] and len(sys.argv) == 3:
        forget(sys.argv[2])
    elif len(sys.argv) == 1:
        for k, v in sorted(load()["characters"].items(), key=lambda kv: kv[1]["n"]):
            print(f"{v['n']:4} {6 + v['n']:4}  {k}  ({v['folder']})")
    else:
        sys.exit(__doc__)
