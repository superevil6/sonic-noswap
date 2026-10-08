#!/usr/bin/env python3
"""A character's own sounds (character.json "sounds"; docs/character-json.md "Own sounds").

A character folder can ship sound files of its own and point any move's S3&K / Mania sound at them:

    "sounds": {"grand_upper": "sfx/GrandUpper.wav"},          (a name -> a file in the character's folder)
    "abilities": {..., "melee_sfx_s3k": "own:grand_upper"}     (any S3&K sound field: "own:<name>")

Every field that takes an S3&K sound file (a *_sfx_s3k field, a "sfx_s3k" inside an object such as melee_nuke or
melee_run, a shot's "s3k" "sound") takes "own:<name>" too; the others keep their meaning (the game's sound files). The
same move plays it in Sonic 1, Sonic 2 and Sonic CD too, where its own fields (the games' sound names) stay the fallback
(the DLL plays the file there as well: "Sonic 1, Sonic 2 and Sonic CD" below).

The build:
- resolve(): "own:<name>" becomes "NoSwap/<id>/<name>.wav", a path under Data/SoundFX (character_json.abilities_entry,
  so S3&K's and Mania's package data both get it);
- convert(): each file in the engines' format (16-bit PCM, mono, 44.1 kHz, as tools/origins_sfx.py writes; ffmpeg);
- S3&K (tools/build_packages.py write_s3k): the package's Sonic3ku/Data/SoundFX/NoSwap/<id>/<name>.wav. Origins plays
  S3&K's own sounds from its CRI banks, never from files, so the DLL plays these itself (NoSwapS3K.cpp PlayOwnSound);
- Mania (tools/build_mania_art.py write_mania): mods/NoSwapMania/Data/SoundFX/NoSwap/<id>/<name>.wav, loaded at startup
  by Data/Game/Game.xml's <sounds> (write_game_xml: a generated block); a crossover's separate mod gets its own files
  and Game.xml (tools/make_release.py pack_mania).
- Sonic 1/2/CD (mark_classic, own_sound_calls): the builders mark the paired fields and finish_script turns each marked
  PlaySfx into a call through the mailbox; the package's noswap_character.json lists the files (classic_paths).
- check(): `noswap check` (tools/noswap_cli/check.py) reports a missing or unreadable file, a bad name, an "own:" name
  the character doesn't declare, and an "own:" in a field that isn't S3&K's.
"""
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PREFIX = "own:"
NAME = re.compile(r"^[a-z0-9_]{1,24}$")
SFX_DIR = "NoSwap"  # (under Data/SoundFX)
PATH_MAX = 63  # the Mania mod's sound fields are char[64] (NoSwapMania.c)
SECONDS_MAX = 10.0
BYTES_MAX = 1 << 20  # the DLL reads up to 1 MB of a file (NoSwapS3K.cpp ReadWholeFile): about 11 s
GAME_XML_BEGIN = "<!-- NoSwap packages' own sounds (character.json \"sounds\"): written by tools/build_mania_art.py, don't edit -->"
GAME_XML_END = "<!-- end of the packages' own sounds -->"


def declared(c):
    """{name: source path} of a loaded character.json (character_json.load: its "folder" set)."""
    folder = Path(c["folder"])
    return {k: folder / v for k, v in (c.get("sounds") or {}).items() if not k.startswith("_")}


def sfx_path(cid, name):
    """The path an own sound is played by (relative to Data/SoundFX)."""
    return f"{SFX_DIR}/{cid}/{name}.wav"


def _sound_field(path):
    """Whether a field (its key path) takes an S3&K sound: *_sfx_s3k / "sfx_s3k" anywhere, or a shot's s3k "sound"."""
    key = path[-1] if path else ""
    return isinstance(key, str) and (key.endswith("sfx_s3k") or (key == "sound" and len(path) > 1 and path[-2] == "s3k"))


def uses(entry, path=()):
    """[(key path, name)] for every "own:<name>" in an abilities entry."""
    out = []
    if isinstance(entry, dict):
        for k, v in entry.items():
            out += uses(v, path + (k,))
    elif isinstance(entry, list):
        for i, v in enumerate(entry):
            out += uses(v, path + (i,))
    elif isinstance(entry, str) and entry.startswith(PREFIX):
        out.append((path, entry[len(PREFIX):]))
    return out


def resolve(entry, cid, names):
    """A copy of an abilities entry with each "own:<name>" turned into its Data/SoundFX path (unknown names: stop)."""
    if isinstance(entry, dict):
        return {k: resolve(v, cid, names) for k, v in entry.items()}
    if isinstance(entry, list):
        return [resolve(v, cid, names) for v in entry]
    if isinstance(entry, str) and entry.startswith(PREFIX):
        name = entry[len(PREFIX):]
        if name not in names:
            raise SystemExit(f"{cid}: \"{entry}\": no sound \"{name}\" in its character.json \"sounds\"")
        return sfx_path(cid, name)
    return entry


def convert(src, dst):
    """src (any format ffmpeg reads) -> dst as 16-bit PCM mono 44.1 kHz WAV, bit-exact (no encoder tag), written only
    when the bytes change. -> True if written."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map_metadata", "-1", "-fflags", "+bitexact",
                        "-flags:a", "+bitexact", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(out)], check=True)
        data = out.read_bytes()
    if dst.exists() and dst.read_bytes() == data:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return True


def write_sounds(cid, have, data_dir):
    """Write a character's own sounds ({name: source file}) under <data_dir>/SoundFX/NoSwap/<cid>/ (other files there
    removed; none: the folder removed when empty). -> [file names]."""
    out = Path(data_dir) / "SoundFX" / SFX_DIR / cid
    if out.exists():
        for p in out.iterdir():
            if p.is_file() and p.stem not in have:
                p.unlink()
    if not have:
        if out.exists() and not any(out.iterdir()):
            out.rmdir()
        return []
    for name, src in have.items():
        if not src.is_file():
            raise SystemExit(f"{cid}: sound \"{name}\": {src} doesn't exist")
        convert(src, out / f"{name}.wav")
    return sorted(f"{n}.wav" for n in have)


def of_extra(e):
    """(cid, {name: source file}) of a tools/extras.py entry: its character.json "sounds", or its tools/abilities.py
    entry's (abilities.OWN_SOUNDS, a make_configs.py character's)."""
    import character_json
    art = Path(e["art"])
    if character_json.has_json(art):
        return art.name, declared(character_json.load(art))
    import abilities
    return art.name, dict(abilities.OWN_SOUNDS.get(e["id"], {}))


def write_s3k(e, package):
    """S3&K: a package's own sounds at <package>/Sonic3ku/Data/SoundFX/NoSwap/<id>/ (the DLL plays them)."""
    cid, have = of_extra(e)
    return write_sounds(cid, have, Path(package) / "Sonic3ku" / "Data")


def write_mania(e, mod):
    """Mania: a package's own sounds at <mod>/Data/SoundFX/NoSwap/<id>/ (Game.xml loads them: write_game_xml)."""
    cid, have = of_extra(e)
    return write_sounds(cid, have, Path(mod) / "Data")


def game_xml_lines(mod, folders=None):
    """The <soundfx> lines for the own sounds found under <mod>/Data/SoundFX/NoSwap/ (only those folders', if given)."""
    root = Path(mod) / "Data" / "SoundFX" / SFX_DIR
    files = sorted(p for p in root.glob("*/*.wav") if folders is None or p.parent.name in folders) if root.exists() else []
    return [f'        <soundfx path="{SFX_DIR}/{p.parent.name}/{p.name}" maxConcurrentPlays="1"/>' for p in files]


def write_game_xml(xml_path, lines):
    """Put `lines` in Game.xml's generated block inside <sounds> (block removed when there are none). -> the new text."""
    xml_path = Path(xml_path)
    text = xml_path.read_text() if xml_path.exists() else "<?xml version=\"1.0\"?>\n<game>\n</game>\n"
    text = re.sub(r"\n[ \t]*" + re.escape(GAME_XML_BEGIN) + r".*?" + re.escape(GAME_XML_END), "", text, flags=re.S)
    if lines:
        block = "\n        " + GAME_XML_BEGIN + "\n" + "\n".join(lines) + "\n        " + GAME_XML_END
        if "</sounds>" in text:
            text = text.replace("\n    </sounds>", block + "\n    </sounds>", 1)
        else:
            text = text.replace("</game>", "    <sounds>" + block + "\n    </sounds>\n</game>", 1)
    if not xml_path.exists() or xml_path.read_text() != text:
        xml_path.parent.mkdir(parents=True, exist_ok=True)
        xml_path.write_text(text)
    return text


def _probe(path):
    """(seconds, error): ffprobe's reading of a sound file."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return None, "ffprobe isn't installed (ffmpeg's): the file can't be checked"
    if r.returncode != 0:
        return None, (r.stderr.strip().splitlines() or ["unreadable"])[-1]
    try:
        return float(json.loads(r.stdout)["format"]["duration"]), None
    except (KeyError, ValueError, TypeError):
        return None, "no audio in it"


def check(c, report):
    """`noswap check`: c the cleaned character.json (its "folder" set); report has .error / .warn / .note."""
    sounds = c.get("sounds") or {}
    if not isinstance(sounds, dict):
        report.error("sounds", "must be an object: {\"name\": \"file in the folder\"}")
        return
    cid = c.get("id", "")
    folder = Path(c["folder"])
    names = {k for k in sounds if not k.startswith("_")}
    if names and shutil.which("ffmpeg") is None:
        report.warn("sounds", "ffmpeg isn't installed: the build can't convert the sound files")
    for name in sorted(names):
        where = f"sounds.{name}"
        if not NAME.match(name):
            report.error(where, "a sound's name is lower-case letters, digits and _ (up to 24)", "e.g. \"grand_upper\"")
            continue
        if len(sfx_path(cid, name)) > PATH_MAX:
            report.error(where, f"{sfx_path(cid, name)} is longer than {PATH_MAX} characters (Mania's limit)",
                         "use a shorter name")
        src = sounds[name]
        if not isinstance(src, str) or not src:
            report.error(where, "give the sound file's path in the character's folder", "e.g. \"sfx/GrandUpper.wav\"")
            continue
        p = folder / src
        if not p.is_file():
            report.error(where, f"{src} doesn't exist in {folder}")
            continue
        seconds, err = _probe(p)
        if err:
            report.error(where, f"{src}: {err}", "use a WAV, OGG, MP3 or FLAC file ffmpeg can read")
        elif seconds is not None and seconds > SECONDS_MAX:
            report.error(where, f"{src} is {seconds:.1f} s long; own sounds are up to {SECONDS_MAX:.0f} s",
                         "trim it (the S3&K DLL reads 1 MB of a sound at most)")
    used = uses(c.get("abilities") or {})
    for path, name in used:
        where = "abilities " + ".".join(str(k) for k in path)
        if not _sound_field(path):
            report.error(where, f"\"own:{name}\": own sounds go in S3&K sound fields only (*_sfx_s3k, a shot's s3k sound)",
                         "Sonic 1 / Sonic 2 / Sonic CD fields take the game's sound names (the S3&K field's own sound plays there too)")
        elif name not in names:
            report.error(where, f"\"own:{name}\": no sound \"{name}\" in \"sounds\"",
                         f"add \"sounds\": {{\"{name}\": \"sfx/<file>.wav\"}} or pick one of {sorted(names) or 'none'}")
    if len(names) > CLASSIC_MAX:
        report.note("sounds", f"Sonic 1/2/CD play the first {CLASSIC_MAX} by name only: "
                    f"{', '.join(sorted(names)[CLASSIC_MAX:])} keep the game's sound there")
    unused = names - {n for _, n in used}
    if unused:
        report.note("sounds", f"not used by any move: {', '.join(sorted(unused))} (still shipped)")


# ---------------------------------------------------------------- Sonic 1, Sonic 2 and Sonic CD
# Origins plays these games' sounds from its CRI banks too, so there the DLL plays an own sound as well (the package's
# S3&K copy, Sonic3ku/Data/SoundFX/NoSwap/<id>/<name>.wav: no other files). The player script tells it through one
# global variable no Origins script of that game uses, the mailbox (V4_MAILBOX in Sonic 1/2, V3_MAILBOX in Sonic CD):
# - the player script's ObjectStartup writes IDLE (made from two halves, so the number isn't in the compiled script);
# - while the active package lists own sounds (its noswap_character.json "own_sounds", classic_paths), the DLL
#   (NoSwapS3K.cpp OwnSoundMailbox) finds that number in the game's memory and answers READY_LO when every listed file
#   is there and plays;
# - a move's sound, when READY: the script sets bit k (the sound's place in classic_names) and the DLL plays the file and
#   clears the bit. Otherwise (no answer: a file missing, an older DLL) the move's game sound plays, as before.
# Which moves: an "own:<name>" in an S3&K field stands in for the same move's Sonic 1/2 and CD fields, which keep the
# game's sound as the fallback (mark_classic): *_sfx / *_sfx_cd beside a *_sfx_s3k, "sfx" / "sfx_cd" beside "sfx_s3k",
# a shot's "v4" / "cd" "sound" beside its "s3k" one. melee_run / melee_up's "sfx_s3k" stands in for the melee's sound
# when that pose starts (variant_mark: abilities.melee_after, build_soniccd's NoSwap_Shot<i>). A field without a Sonic
# 1/2 or CD counterpart keeps the game's sound there. Characters without own sounds: nothing changes.
CLASSIC_MAX = 8  # (bits 0-7 of the mailbox)
IDLE_HI, IDLE_LO = 0x4E53, 0x4F00  # IDLE = 0x4E534F00
READY_LO, READY_HI = 0x4D520000, 0x4D52FFFF  # READY: 0x4D52 in the top half (bits 0-7: the sounds asked for)
V4_MAILBOX = "game.callbackParam2"  # (Sonic 1/2: no Origins script uses it; S1/S2 notify with their own arguments)
V3_MAILBOX = "Leaderboard.Offset"  # (Sonic CD: no Origins script uses it)
MARK = re.compile(r"@@own(\d)@@")
_INDEX = {}  # extra id -> {Data/SoundFX path: k} (mark_classic)


def classic_names(e):
    """The own sound names Sonic 1/2/CD can play, in order (the mailbox's bits): the first CLASSIC_MAX by name."""
    return sorted(of_extra(e)[1])[:CLASSIC_MAX]


def classic_paths(e):
    """noswap_character.json "own_sounds": their Data/SoundFX paths in the mailbox's order ([]: none)."""
    cid = e["art"].name
    return [sfx_path(cid, n) for n in classic_names(e)]


def mark(k):
    return f"@@own{k}@@"


def mark_classic(abilities, extras):
    """For the Sonic 1/2/CD builders (in place, before any script is made): each own S3&K sound's Sonic 1/2 and CD
    counterparts get mark(k) after the game's sound, which own_sound_calls (finish_script) turns into the mailbox call
    with that sound as the fallback."""
    for e in extras:
        c = abilities.get(e["id"])
        if not isinstance(c, dict):
            continue
        cid = e["art"].name
        index = {sfx_path(cid, n): k for k, n in enumerate(classic_names(e))}
        if index:
            _INDEX[e["id"]] = index
            _mark(c, index)


def _mark(node, index):
    def add(d, key, k):
        if isinstance(d, dict) and isinstance(d.get(key), str) and d[key] and not MARK.search(d[key]):
            d[key] += mark(k)
    if isinstance(node, dict):
        for key, v in list(node.items()):
            if isinstance(v, str) and key.endswith("sfx_s3k") and v in index:
                add(node, key[:-len("_s3k")], index[v])
                add(node, key[:-len("_s3k")] + "_cd", index[v])
            elif key == "s3k" and isinstance(v, dict) and v.get("sound") in index:
                add(node.get("v4"), "sound", index[v["sound"]])
                add(node.get("cd"), "sound", index[v["sound"]])
            if isinstance(v, (dict, list)):
                _mark(v, index)
    elif isinstance(node, list):
        for v in node:
            _mark(v, index)


def variant_mark(i, c, key):
    """mark(k) for melee_run / melee_up's own S3&K sound (`key`), "" without one."""
    v = c.get(key)
    k = _INDEX.get(i, {}).get(v.get("sfx_s3k")) if isinstance(v, dict) else None
    return "" if k is None else mark(k)


def strip(name):
    return MARK.sub("", name)


def own_sound_calls(text):
    """finish_script: each marked PlaySfx (a Sonic 1/2 or CD script) becomes the mailbox call with the game's sound as
    the fallback, and the player script's ObjectStartup writes IDLE. Text without marks is returned unchanged."""
    if "@@own" not in text:
        return text
    v3 = "#alias" in text
    box = V3_MAILBOX if v3 else V4_MAILBOX
    startup = "sub ObjectStartup\n" if v3 else "event ObjectStartup\n"
    if text.count(startup) != 1:
        raise SystemExit("own sounds: a marked sound outside a player script (no single ObjectStartup)")
    idle = [f"{box} = 0x{IDLE_HI:X} // [NoSwap] own sounds: the number 0x4E534F00, for the DLL to find and answer "
            "(tools/own_sounds.py)", f"{box} <<= 16", f"{box} += 0x{IDLE_LO:X}"]
    text = text.replace(startup, startup + "".join(f"\t{l}\n" for l in idle), 1)
    call = (r"PlaySfx\((\w+)@@own(\d)@@, false\)" if v3
            else r"PlaySfx\(SfxName\[([^\]\n]*?)@@own(\d)@@\], false\)")
    again = [f"{box} = 0x{IDLE_HI:X} // (the DLL hasn't answered: ask again)", f"{box} <<= 16", f"{box} += 0x{IDLE_LO:X}"]
    out = []
    for line in text.split("\n"):
        if "@@own" not in line:
            out.append(line)
            continue
        m = re.fullmatch(r"([ \t]*)" + call + r"(.*)", line)
        if not m or not (m.group(4).strip() == "" or m.group(4).strip().startswith("//")):
            raise SystemExit(f"own sounds: a mark this build can't turn into a call: {line.strip()}")
        ind, name, k, rest = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        fallback = f"PlaySfx({name}, false)" if v3 else f"PlaySfx(SfxName[{name}], false)"
        out += [f"{ind}if {box} >= 0x{READY_LO:X} // [NoSwap] own sound {k}: the DLL plays the package's file (tools/own_sounds.py){rest}",
                f"{ind}\tif {box} <= 0x{READY_HI:X}", f"{ind}\t\t{box} |= {1 << k}", f"{ind}\telse",
                f"{ind}\t\t{fallback}"] + [f"{ind}\t\t{l}" for l in again] + [
                f"{ind}\tend if", f"{ind}else", f"{ind}\t{fallback}"] + [f"{ind}\t{l}" for l in again] + [f"{ind}end if"]
    return "\n".join(out)
