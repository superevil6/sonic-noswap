"""`noswap ui [folder]`: the character editor, in a desktop window (pywebview) or the browser.

Both ways run the same thing: a small HTTP server on 127.0.0.1 serves tools/noswap_ui/web/ and a JSON API
(POST /api/<method>, the Backend's methods). pywebview, when it's installed, just shows that page in a window of its
own; without it (or with --browser) the default browser opens it. A random token in the page's address guards the API
against other web pages on the same machine.
"""
import inspect
import os
import json
import mimetypes
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .backend import ApiError, Backend

WEB = Path(__file__).resolve().parent / "web"
PUBLIC = {name for name, f in inspect.getmembers(Backend, inspect.isfunction) if not name.startswith("_")}
UNLOCKED = {"check", "build_log", "build_stop", "deploy_settings", "check_folder", "set_deploy_settings", "deploy",
            "kit_status", "kit_check", "kit_setup"}  # (these don't touch the open document: they run alongside edits)


def make_handler(backend, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "noswap-ui"

        def log_message(self, fmt, *args):  # (quiet: errors are reported to the page)
            pass

        def _send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, default=str).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            if url.path == "/sheet":
                if q.get("t", [""])[0] != token:
                    return self._send(403, {"error": "bad token"})
                try:
                    data, ctype = backend.sheet_file()
                except ApiError as e:
                    return self._send(404, {"error": str(e)})
                return self._send(200, data, ctype)
            name = "index.html" if url.path in ("/", "") else url.path.lstrip("/")
            p = (WEB / name).resolve()
            if WEB not in p.parents or not p.is_file():
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype.endswith("javascript"):
                ctype += "; charset=utf-8"
            self._send(200, p.read_bytes(), ctype)

        def do_POST(self):
            url = urlparse(self.path)
            if self.headers.get("X-Noswap-Token") != token:
                return self._send(403, {"error": "bad token"})
            method = url.path[len("/api/"):] if url.path.startswith("/api/") else ""
            if method not in PUBLIC:
                return self._send(404, {"error": f"no API method {method!r}"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                args = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "the request isn't JSON"})
            try:
                if method in UNLOCKED:
                    result = getattr(backend, method)(**args)
                else:
                    with backend.lock:  # (one request at a time on the open document)
                        result = getattr(backend, method)(**args)
            except ApiError as e:
                return self._send(400, {"error": str(e)})
            except TypeError as e:
                return self._send(400, {"error": f"{method}: {e}"})
            except (Exception, SystemExit) as e:  # (pipeline code that exits: show it, keep serving)
                import traceback
                traceback.print_exc()
                return self._send(500, {"error": f"{method} failed: {e!r}"})
            self._send(200, {"ok": True, "result": result})

    return Handler


def serve(backend, port=0):
    token = secrets.token_urlsafe(16)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(backend, token))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/?t={token}"


def run(folder=None, browser=False, port=0, lock=None, no_open=False):
    backend = Backend(lock=lock)
    if folder:
        try:
            backend.open(folder)
        except ApiError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    httpd, url = serve(backend, port)
    webview = None
    if not browser and not no_open:  # (--no-open: just the address, no window either)
        try:
            import webview  # pywebview
        except ImportError:
            if os.environ.get("NOSWAP_KIT"):
                print("opening the editor in your browser")
            else:
                print("pywebview isn't installed: opening the editor in your browser instead "
                      "(docs/toolset-ui.md says how to get the desktop window).")
    if webview is not None and sys.platform == "win32":  # (the window needs Edge WebView2: the old MSHTML engine can't
        try:                                                # run the editor's scripts)
            from webview.platforms import winforms
            renderer = getattr(winforms, "renderer", "?")
        except Exception as e:
            renderer = repr(e)
        if renderer != "edgechromium":
            print(f"the editor's window needs Microsoft Edge WebView2 (found: {renderer}): opening it in your browser "
                  "instead (install the WebView2 Runtime from Microsoft for the window)", flush=True)
            webview = None
    if webview is not None:
        print(f"NoSwap character editor: {url}", flush=True)
        try:
            webview.create_window("NoSwap character editor", url, width=1360, height=860, min_size=(1024, 640))
            webview.start()
        except Exception as e:  # (no usable web view here, e.g. no WebView2 runtime: the browser instead)
            print(f"the editor's window couldn't open ({e!r}): opening it in your browser instead", flush=True)
            webview = None
        else:
            httpd.shutdown()
            _quit(backend)
            return 0
    print(f"NoSwap character editor: {url}\n(Ctrl+C here to stop it)", flush=True)
    if not no_open:
        webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    httpd.shutdown()
    _quit(backend)
    return 0


def _quit(backend):
    kept = backend.keep_unsaved()
    if kept:
        print(f"Unsaved changes weren't lost: they're in {kept} (copy it over character.json to use them).")
