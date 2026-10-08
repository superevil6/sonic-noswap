"""The NoSwap Creator Kit's program (tools/make_kit.py freezes it with PyInstaller).

    NoSwapCreator                  the character editor (a window on Windows, else your browser)
    NoSwapCreator --browser        the editor in your browser
    NoSwapCreator <command> ...    any `noswap` command: setup, check, preview, build, deploy, abilities, detect
    NoSwapCreator --data DIR ...   use another data folder (default: Documents/NoSwap Creator Kit)

It copies its tools (the "app" folder beside it) into the data folder and runs them there (tools/noswap_cli/kit.py). The
build runs the tools' scripts as separate processes of this same program: `NoSwapCreator <script.py> args` runs that
script with the bundled Python, so no Python install is needed.
"""
import os
import runpy
import sys
from pathlib import Path

import _kit_deps  # noqa: F401  (the modules the tools need, for PyInstaller to bundle)


def run_script(argv):
    """`<program> [-u] <script.py> args...`: what `python script.py args` would do."""
    if argv and argv[0] == "-u":
        argv = argv[1:]
        os.environ["PYTHONUNBUFFERED"] = "1"
        try:
            sys.stdout.reconfigure(line_buffering=True)
            sys.stderr.reconfigure(line_buffering=True)
        except AttributeError:
            pass
    script = argv[0]
    sys.argv = list(argv)
    sys.path.insert(0, str(Path(script).resolve().parent))
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(code, file=sys.stderr)
        return 1
    return 0


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "app"
    return Path(os.environ.get("NOSWAP_KIT_APP") or Path(__file__).resolve().parents[2] / "kit" / "build" / "app")


def main():
    argv = sys.argv[1:]
    if argv and (argv[0] == "-u" or argv[0].endswith(".py")):
        return run_script(argv)
    if "--data" in argv:
        i = argv.index("--data")
        if i + 1 >= len(argv):
            print("--data needs a folder", file=sys.stderr)
            return 2
        os.environ["NOSWAP_KIT_DATA"] = str(Path(argv[i + 1]).expanduser().resolve())
        del argv[i:i + 2]
    app = app_dir()
    if not (app / "tools" / "noswap_cli" / "kit.py").is_file():
        print(f"the kit's tools are missing ({app}): unpack the whole kit folder again", file=sys.stderr)
        return 2
    sys.path.insert(0, str(app / "tools"))
    from noswap_cli import kit
    root = kit.data_root()
    os.environ.update(kit.env(root))
    root.mkdir(parents=True, exist_ok=True)
    if kit.sync_app(app, root):
        print(f"NoSwap Creator Kit: tools copied into {root}", flush=True)
    sys.path.remove(str(app / "tools"))
    for m in [m for m in sys.modules if m == "noswap_cli" or m.startswith("noswap_cli.")]:
        del sys.modules[m]
    sys.path.insert(0, str(root / "tools"))
    os.chdir(root)
    if argv and argv[0] in ("-h", "--help"):
        argv = ["help"]  # (every command; `ui --help` is the editor's own)
    elif not argv or argv[0].startswith("-"):
        argv = ["ui"] + argv
    from noswap_cli.main import main as noswap_main
    return noswap_main(argv)


if __name__ == "__main__":
    sys.exit(main() or 0)
