"""Argument parsing and the four commands' entry points."""
import argparse
import os
import sys
from pathlib import Path

from .model import CharacterError, resolve_folder

OK, FAILED, USAGE, BUILD_FAILED = 0, 1, 2, 3


def cmd_check(args):
    from . import check
    status = OK
    for arg in args.folders:
        try:
            folder = resolve_folder(arg)
        except CharacterError as e:
            print(f"error: {e}", file=sys.stderr)
            status = USAGE
            continue
        ch, report = check.run(folder)
        kind = f" ({'character.json' if ch.kind == 'json' else 'make_configs.py'})" if ch else ""
        errors, warnings = report.count("error"), report.count("warning")
        verdict = "FAILED" if errors or (args.strict and warnings) else "ok"
        print(f"{folder.name}{kind}: {verdict}: {errors} error(s), {warnings} warning(s), {report.count('note')} note(s)")
        report.print(sys.stdout, verbose=args.verbose)
        if verdict == "FAILED":
            status = max(status, FAILED)
    return status


def cmd_preview(args):
    from . import preview
    try:
        folder = resolve_folder(args.folder)
        paths = preview.run(folder, anim=args.anim, out=args.out, scale=args.scale, raw=args.raw)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return FAILED
    for p in paths:
        print("wrote", p)
    return OK


def cmd_build(args):
    from . import build
    try:
        folder = resolve_folder(args.folder)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE
    return build.run(folder, games=args.games, check_first=not args.no_check, dry_run=args.dry_run, lock=args.lock)


def cmd_convert(args):
    from . import convert
    try:
        folder = resolve_folder(args.folder)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE
    return convert.run(folder, wire_it=args.wire, force=args.force, unwire_it=args.unwire)


def cmd_abilities(args):
    from . import abilities_cmd
    return abilities_cmd.run(args.name, as_json=args.json, game=args.game)


def cmd_deploy(args):
    from . import kit
    if kit.active() and not (args.show or args.set_origins is not None or args.set_mania is not None):
        from . import kit_deploy
        return kit_deploy.run(origins=args.origins, mania=args.mania, dry_run=args.dry_run, character=args.character,
                              force=args.force)
    from . import deploy
    return deploy.run(origins=args.origins, mania=args.mania, dry_run=args.dry_run, character=args.character,
                      force=args.force, lock=args.lock, set_origins=args.set_origins, set_mania=args.set_mania,
                      show_only=args.show)


def cmd_detect(args):
    from . import detect
    try:
        folder = resolve_folder(args.folder)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return USAGE
    region = None
    if args.region:
        try:
            region = [int(v) for v in args.region.split(",")]
            assert len(region) == 4
        except (ValueError, AssertionError):
            print("error: --region is x,y,w,h", file=sys.stderr)
            return USAGE
    try:
        return detect.run(folder, merge=args.merge, min_size=args.min_size, as_json=args.json, show_all=args.all,
                          region=region)
    except CharacterError as e:
        print(f"error: {e}", file=sys.stderr)
        return FAILED


def cmd_setup(args):
    from . import kit
    if not args.origins and not args.mania:
        st = kit.status()
        print(f"kit data folder: {st['root']}")
        print(f"Origins: {'ready' if st['ready_origins'] else 'not set up'} ({st['origins'] or 'found: ' + str(st['found']['origins'])})")
        print(f"Mania: {'ready' if st['ready_mania'] else 'not set up'} ({st['mania'] or 'found: ' + str(st['found']['mania'])})")
        print(f"for NoSwap core {st['core'].get('origins', {}).get('version', '?')} / "
              f"NoSwap Mania {st['core'].get('mania', {}).get('version', '?')}")
        return OK if st["ready_origins"] or st["ready_mania"] else FAILED
    try:
        kit.setup(origins=args.origins, mania=args.mania, log=lambda m: print(m, flush=True))
    except kit.SetupError as e:
        print(f"error: {e}", file=sys.stderr)
        return FAILED
    return OK


def cmd_ui(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from noswap_ui.server import run
    return run(args.folder, browser=args.browser, port=args.port, lock=args.lock, no_open=args.no_open)


def parser():
    p = argparse.ArgumentParser(
        prog="noswap",
        description="The NoSwap character tool: check, preview, build and convert characters, and list the "
                    "abilities (docs/toolset-cli.md, docs/abilities.md). "
                    "<folder> is a path or a folder name under testmods/. `deploy` copies the built mods into the games.",
        epilog="Exit codes: 0 fine, 1 the character has errors (or a conversion isn't identical), 2 bad usage, "
               "3 a build step failed.")
    sub = p.add_subparsers(dest="command", required=True, metavar="command")

    c = sub.add_parser("check", help="validate a character (schema, frames, animations, palette, abilities, credits)",
                       description="Validate a character: its character.json against docs/character.schema.json, every "
                                   "frame inside the sheet and not empty, every animation's frames defined, the palette's "
                                   "fit in each game (Origins S1/S2/CD/S3&K and Mania), the moves and their fields, and "
                                   "the sheet's credits and terms. An old make_configs.py character is checked from the "
                                   "configs it last wrote.")
    c.add_argument("folders", nargs="+", metavar="folder")
    c.add_argument("-v", "--verbose", action="store_true", help="also show notes (sizes, slots, registration)")
    c.add_argument("--strict", action="store_true", help="fail on warnings too")
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("preview", help="render frames and animation strips as PNGs, labelled, at 3x",
                       description="Render a character's frames and animations as labelled PNGs (no game needed): "
                                   "<id>-animations.png (one row per animation, frames placed on the ground line as the "
                                   "game places them) and <id>-frames.png (every named frame), in the game's colours.")
    v.add_argument("folder")
    v.add_argument("--anim", help="only this animation (a name such as Walking, or an ability slot such as 41)")
    v.add_argument("--out", help="output file (with --anim) or directory (default: <temp dir>/noswap-preview/<id>/)")
    v.add_argument("--scale", type=int, default=3, help="enlargement (default 3)")
    v.add_argument("--raw", action="store_true", help="the sheet's own colours instead of the game palette's")
    v.set_defaults(func=cmd_preview)

    b = sub.add_parser("build", help="build a character for Origins and/or Mania",
                       description="Build a character: its art (tools/build_art.py, which runs its make_configs.py or "
                                   "reads its character.json), then every Origins game script and package "
                                   "(tools/build_all.sh), under the build lock; and its Mania package "
                                   "(tools/build_mania_art.py). Runs `check` first. It never deploys to the game.")
    b.add_argument("folder")
    b.add_argument("--games", default="s1,s2,cd,s3k,mania",
                   help="comma list of s1, s2, cd, s3k, mania (default all). The Origins games are always built "
                        "together: any of s1/s2/cd/s3k builds all four")
    b.add_argument("--no-check", action="store_true", help="skip the check")
    b.add_argument("--dry-run", action="store_true", help="print the steps without running them")
    b.add_argument("--lock", default=os.environ.get("NOSWAP_BUILD_LOCK"),
                   help="the lock file Origins builds take (default $NOSWAP_BUILD_LOCK, else <temp dir>/noswap-build.lock)")
    b.set_defaults(func=cmd_build)

    a = sub.add_parser("abilities", help="list the moves a character can have, or describe one",
                       description="The ability registry (docs/abilities.md): every move, its fields, the animation "
                                   "slots it draws, the games it works in and the rules on combining moves. With a "
                                   "name, that move in full.")
    a.add_argument("name", nargs="?", help="a move's id or name (e.g. jet_dash, \"Jet Dash\")")
    a.add_argument("--game", choices=["s1", "s2", "cd", "s3k", "mania"], help="only the moves that work in this game")
    a.add_argument("--json", action="store_true", help="print the registry entry (or all of it) as JSON")
    a.set_defaults(func=cmd_abilities)

    d = sub.add_parser("deploy", help="copy the built mods into Origins and/or the Mania decomp (deploy.sh, deploy_mania.sh)",
                       description="Deploy what's built in mods/: Origins gets every mod folder but NoSwapMania mirrored "
                                   "into HedgeModManager's mods folder (the game's own logs, cache/ and NoSwapS3K.ini "
                                   "are kept); Mania gets <run>/mods/NoSwapMania symlinked to the repo's and "
                                   "NoSwapMania=y in modconfig.ini. Both by default. The folders come from your settings "
                                   "file (--show says where, and what was detected). A running game is reported: "
                                   "restart it, the DLL and scripts load at startup.")
    d.add_argument("--origins", action="store_true", help="deploy to Origins (default: both)")
    d.add_argument("--mania", action="store_true", help="deploy to the Mania decomp (default: both)")
    d.add_argument("--dry-run", action="store_true", help="say what would change; write nothing")
    d.add_argument("--character", metavar="folder",
                   help="only this character's package (not yet: comes with step 5; --dry-run shows the plan)")
    d.add_argument("--force", action="store_true", help="deploy even if the folder doesn't look like the game's")
    d.add_argument("--show", action="store_true", help="show the folders (set and detected) and whether a game runs")
    d.add_argument("--set-origins", metavar="DIR", help="save Origins' mods folder in the settings (\"\" clears it)")
    d.add_argument("--set-mania", metavar="DIR", help="save the Mania play folder in the settings (\"\" clears it)")
    d.add_argument("--lock", default=os.environ.get("NOSWAP_BUILD_LOCK"),
                   help="the build lock a deploy waits on, so it never copies a half-built mods/ (default as build)")
    d.set_defaults(func=cmd_deploy)

    u = sub.add_parser("ui", help="the character editor: forms, the sheet, animation previews, moves, check, build",
                       description="Open the NoSwap character editor (docs/toolset-ui.md): a desktop window when "
                                   "pywebview is installed, else (or with --browser) a page in your browser served "
                                   "from 127.0.0.1 only. It deploys to the games only when you press Deploy.")
    u.add_argument("folder", nargs="?", help="a character folder to open (a path, or a name under testmods/)")
    u.add_argument("--browser", action="store_true", help="use the browser even if pywebview is installed")
    u.add_argument("--port", type=int, default=0, help="the local port (default: any free one)")
    u.add_argument("--no-open", action="store_true", help="don't open a browser; just print the address")
    u.add_argument("--lock", default=os.environ.get("NOSWAP_BUILD_LOCK"),
                   help="the build lock its Build button takes (default $NOSWAP_BUILD_LOCK, else <temp dir>/noswap-build.lock)")
    u.set_defaults(func=cmd_ui)

    s = sub.add_parser("setup", help="Creator Kit: take what the build needs from your own Origins / Mania (read only)",
                       description="The Creator Kit's first step: extract the game files the build reads from your own "
                                   "Sonic Origins (its data packs and HedgeModManager's decompiled scripts) and, "
                                   "optionally, Sonic Mania (Data.rsdk), into the kit's data folder. The games are only "
                                   "read. Without options: what's set up.")
    s.add_argument("--origins", metavar="DIR", help="Sonic Origins' folder (or its build/main/projects/exec/mods)")
    s.add_argument("--mania", metavar="DIR", help="a folder with Sonic Mania's Data.rsdk (Steam's or your decomp's)")
    s.set_defaults(func=cmd_setup)

    t = sub.add_parser("detect", help="find the sprites on a character's sheet and propose frame rectangles",
                       description="Find the sprites on the sheet (pieces of non-background pixels; small bits near a "
                                   "body join it; cell fills count as background) and print proposed frames, trimmed "
                                   "tight, in reading order, ready to paste into \"frames\". Text, lines, specks and "
                                   "pieces on existing frames are left out unless --all. Reads only: nothing is written.")
    t.add_argument("folder")
    t.add_argument("--merge", type=int, default=3, metavar="PX",
                   help="small pieces this close (px) to a bigger body join it (default 3; 0: no merging)")
    t.add_argument("--min-size", type=int, default=3, metavar="PX",
                   help="lone pieces narrower and shorter than this are specks (default 3)")
    t.add_argument("--region", metavar="X,Y,W,H", help="only look inside this rectangle")
    t.add_argument("--all", action="store_true", help="also list text, lines, specks and pieces on existing frames")
    t.add_argument("--json", action="store_true", help="print everything as JSON")
    t.set_defaults(func=cmd_detect)

    k = sub.add_parser("convert", help="turn an old make_configs.py character into a character.json, proven identical",
                       description="Write <folder>/character.json from an old-style character's make_configs.py, "
                                   "tools/extras.py and tools/abilities.py entries, then prove it: the sheet2ani configs, "
                                   "the extras entry and the abilities entry it produces must equal the old ones exactly. "
                                   "With --wire it also switches the build over (make_configs.py becomes a shim, the old "
                                   "one kept as make_configs.legacy.py; extras.py and abilities.py call the loader). "
                                   "Then rebuild and compare the outputs (docs/toolset-cli.md).")
    k.add_argument("folder")
    k.add_argument("--wire", action="store_true", help="also switch the build over to the character.json")
    k.add_argument("--force", action="store_true", help="overwrite an existing character.json")
    k.add_argument("--unwire", action="store_true",
                   help="undo --wire exactly, from its backups (<temp dir>/noswap-convert/<id>/), and remove the "
                        "character.json")
    k.set_defaults(func=cmd_convert)

    hp = sub.add_parser("help", help="this list of commands, or one command's help (help <command>)")
    hp.add_argument("topic", nargs="?", metavar="command")
    hp.set_defaults(func=lambda a: help_command([a.topic] if a.topic else []))
    return p


# The Creator Kit's wording for what the repo's help says about the repo (kit_parser)
KIT_WORDS = [("a folder name under testmods/", "a folder name in your characters folder"),
             ("a name under testmods/", "a folder name in your characters folder"),
             ("(docs/toolset-cli.md, docs/abilities.md)", "(the kit's README.md and docs/)"),
             (" (docs/toolset-cli.md)", ""), ("docs/toolset-cli.md", "the kit's README.md"),
             ("(tools/build_art.py, which runs its make_configs.py or reads its character.json), then every Origins "
              "game script and package (tools/build_all.sh), under the build lock; and its Mania package "
              "(tools/build_mania_art.py)", "and its packages for every Origins game and for Mania"),
             ("<temp dir>/noswap-preview/<id>/", "previews/<id>/ in the kit's data folder")]
KIT_DEPLOY = ("Install the characters you built (output/<id>/) into the games, each as its own mod NoSwap-<Name> "
              "beside the NoSwap core: Origins into HedgeModManager's mods folder (the Sonic Origins you set up), Mania "
              "into the decompilation's mods folder (enabled in modconfig.ini). Both by default. The folders: the "
              "Settings tab, or --set-origins / --set-mania (the game's folder is enough), --show to see them. A game "
              "running from that folder is reported: restart it, mods load at startup.")
KIT_CONVERT = ("For NoSwap's own older characters (a make_configs.py instead of a character.json): writes the "
               "character.json and proves it builds the same. Kit characters never need it.")


def kit_parser(p):
    """The parser as the Creator Kit shows it: its program's name, its own words for the repo's paths."""
    p.prog = "NoSwapCreator"
    p.epilog = (p.epilog or "") + " `NoSwapCreator help <command>` for one command in full; no command opens the editor."

    def fix(text):
        for a, b in KIT_WORDS:
            text = text.replace(a, b) if text else text
        return text
    p.description = fix(p.description)
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    for choice in sub._choices_actions:
        choice.help = fix(choice.help)
    for name, sp in sub.choices.items():
        sp.prog = f"NoSwapCreator {name}"
        sp.description = KIT_DEPLOY if name == "deploy" else KIT_CONVERT if name == "convert" else fix(sp.description)
        for a in sp._actions:
            a.help = fix(a.help)
        if name == "deploy":
            for a in sp._actions:
                if a.dest == "character":
                    a.help = "only this character (a folder name in your characters folder)"
                elif a.dest == "set_origins":
                    a.help = "save where Origins installs: the game's folder or its mods folder (\"\" goes back to Set up's)"
                elif a.dest == "set_mania":
                    a.help = "save the Mania decompilation's play folder (\"\" goes back to Set up's)"
    for a in sub._choices_actions:
        if a.dest == "deploy":
            a.help = "install the characters you built into Origins and/or Mania, each as its own mod"
        elif a.dest == "convert":
            a.help = "NoSwap's own older characters into a character.json (kit characters never need it)"
        elif a.dest == "setup":
            a.help = "first step: take what the build needs from your own Origins / Mania (read only)"
    return p


def help_command(argv):
    """`help [command]`: the command list, or one command's help."""
    p = parser()
    if os.environ.get("NOSWAP_KIT"):
        kit_parser(p)
    if argv:
        sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
        if argv[0] in sub.choices:
            sub.choices[argv[0]].print_help()
            return OK
        print(f"no command {argv[0]!r}: {', '.join(sub.choices)}", file=sys.stderr)
        return USAGE
    p.print_help()
    return OK


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["help"]:
        return help_command(argv[1:])
    kit_mode = bool(os.environ.get("NOSWAP_KIT"))
    if kit_mode and argv[:1] == ["ui"] and len(argv) == 2 and argv[1] in ("-h", "--help") \
            and [a for a in sys.argv[1:] if a != "--data"][:1] in (["-h"], ["--help"]):
        return help_command([])  # (the kit's program turned a bare --help into `ui --help`: show every command)
    p = parser()
    if kit_mode:
        kit_parser(p)
    args = p.parse_args(argv)
    # Only a real build's own steps register a new character's number (build._run clears this for them)
    os.environ["NOSWAP_REGISTRY_READONLY"] = "1"
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
